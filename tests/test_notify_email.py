"""Testes de configuracao, mensagem, transporte e codigo de saida do script."""

from contextlib import redirect_stderr, redirect_stdout
from email import message_from_bytes
from email.policy import default
from io import StringIO
import os
from pathlib import Path
import smtplib
import subprocess
import sys
import unittest
from unittest.mock import call, patch

from scripts import notify_email as notify


BASE_ENV = {
    "NOTIFY_EMAIL": "destinatario@example.test",
    "SMTP_FROM": "jenkins@example.test",
    "SMTP_HOST": "mailhog",
    "BUILD_STATUS": "SUCCESS",
    "JOB_NAME": "chamados-ci",
    "BUILD_NUMBER": "42",
    "BUILD_URL": "http://jenkins:8080/job/chamados-ci/42/",
    "GIT_BRANCH": "origin/feature/email-notifications",
    "GIT_COMMIT": "abc123",
}


class ConfigTests(unittest.TestCase):
    def test_defaults(self):
        config = notify.SmtpConfig.from_env(BASE_ENV)
        self.assertEqual((config.host, config.port, config.timeout), ("mailhog", 1025, 10))
        self.assertEqual((config.security, config.username, config.password), ("none", "", ""))

    def test_recipient_and_sender_are_read_from_environment(self):
        config = notify.SmtpConfig.from_env({**BASE_ENV, "NOTIFY_EMAIL": " outra@example.test ",
                                            "SMTP_FROM": "ci@example.test"})
        self.assertEqual(config.recipient, "outra@example.test")
        self.assertEqual(config.sender, "ci@example.test")

    def test_required_values(self):
        for name in ("NOTIFY_EMAIL", "SMTP_FROM", "SMTP_HOST"):
            for value in (None, "", "   "):
                with self.subTest(name=name, value=value):
                    env = {**BASE_ENV, name: value} if value is not None else dict(BASE_ENV)
                    if value is None:
                        del env[name]
                    with self.assertRaisesRegex(notify.ConfigurationError, name):
                        notify.SmtpConfig.from_env(env)

    def test_rejects_invalid_or_multiple_addresses(self):
        for name in ("NOTIFY_EMAIL", "SMTP_FROM"):
            for value in ("sem-arroba", "a@", "@example.test", "a@example.test,b@example.test",
                          "a@example.test\r\nBcc: b@example.test", "A <a@example.test>"):
                with self.subTest(name=name, value=value):
                    with self.assertRaisesRegex(notify.ConfigurationError, name):
                        notify.SmtpConfig.from_env({**BASE_ENV, name: value})

    def test_rejects_invalid_ports(self):
        for value in ("0", "65536", "-1", "texto", "1.5", ""):
            with self.subTest(value=value):
                with self.assertRaisesRegex(notify.ConfigurationError, "SMTP_PORT"):
                    notify.SmtpConfig.from_env({**BASE_ENV, "SMTP_PORT": value})

    def test_rejects_invalid_timeouts(self):
        for value in ("0", "-1", "nan", "inf", "texto", ""):
            with self.subTest(value=value):
                with self.assertRaisesRegex(notify.ConfigurationError, "SMTP_TIMEOUT"):
                    notify.SmtpConfig.from_env({**BASE_ENV, "SMTP_TIMEOUT": value})

    def test_custom_transport_settings(self):
        config = notify.SmtpConfig.from_env({**BASE_ENV, "SMTP_PORT": "587", "SMTP_TIMEOUT": "2.5",
                                            "SMTP_SECURITY": " STARTTLS ",
                                            "SMTP_USERNAME": " usuario ", "SMTP_PASSWORD": " senha "})
        self.assertEqual((config.port, config.timeout, config.security), (587, 2.5, "starttls"))
        self.assertEqual((config.username, config.password), ("usuario", " senha "))
        self.assertNotIn(" senha ", repr(config))

    def test_rejects_unknown_security(self):
        with self.assertRaisesRegex(notify.ConfigurationError, "SMTP_SECURITY"):
            notify.SmtpConfig.from_env({**BASE_ENV, "SMTP_SECURITY": "invalid"})

    def test_credentials_must_be_supplied_together(self):
        for credentials in ({"SMTP_USERNAME": "user"}, {"SMTP_PASSWORD": "segredo"}):
            with self.subTest(credentials=list(credentials)):
                with self.assertRaisesRegex(notify.ConfigurationError, "juntos"):
                    notify.SmtpConfig.from_env({**BASE_ENV, **credentials})


class MessageTests(unittest.TestCase):
    def setUp(self):
        self.config = notify.SmtpConfig.from_env(BASE_ENV)

    def test_message_contains_pipeline_evidence(self):
        message = notify.build_message(self.config, BASE_ENV)
        self.assertEqual(str(message["Subject"]), "[SUCCESS] chamados-ci #42")
        self.assertEqual(str(message["To"]), BASE_ENV["NOTIFY_EMAIL"])
        self.assertEqual(str(message["From"]), BASE_ENV["SMTP_FROM"])
        self.assertIsNotNone(message["Date"])
        self.assertIsNotNone(message["Message-ID"])
        self.assertTrue(str(message["Message-ID"]).endswith("@example.test>"))
        body = message.get_content()
        for value in ("SUCCESS", "chamados-ci", "42", BASE_ENV["GIT_BRANCH"], "abc123",
                      BASE_ENV["BUILD_URL"], BASE_ENV["BUILD_URL"] + "console"):
            self.assertIn(value, body)

    def test_all_pipeline_results(self):
        for status in ("SUCCESS", "FAILURE", "UNSTABLE", "ABORTED", "NOT_BUILT", "UNKNOWN"):
            with self.subTest(status=status):
                message = notify.build_message(self.config, {**BASE_ENV, "BUILD_STATUS": status.lower()})
                self.assertIn(f"[{status}]", str(message["Subject"]))
                self.assertIn(f"Resultado do pipeline: {status}", message.get_content())

    def test_metadata_defaults_outside_jenkins(self):
        message = notify.build_message(self.config, {})
        self.assertEqual(str(message["Subject"]), "[UNKNOWN] execucao-local #local")
        self.assertIn("Branch: nao informado", message.get_content())
        self.assertIn("Commit: nao informado", message.get_content())
        self.assertIn("Execucao: nao informada", message.get_content())
        self.assertIn("Console: nao informado", message.get_content())

    def test_branch_name_takes_precedence(self):
        message = notify.build_message(self.config, {**BASE_ENV, "BRANCH_NAME": "minha-branch"})
        self.assertIn("Branch: minha-branch", message.get_content())

    def test_utf8_round_trip(self):
        env = {**BASE_ENV, "JOB_NAME": "laboratório/reparação", "GIT_BRANCH": "correção"}
        message = notify.build_message(self.config, env)
        parsed = message_from_bytes(message.as_bytes(), policy=default)
        self.assertEqual(str(parsed["Subject"]), "[SUCCESS] laboratório/reparação #42")
        self.assertIn("correção", parsed.get_content())

    def test_rejects_unknown_status(self):
        with self.assertRaisesRegex(notify.ConfigurationError, "BUILD_STATUS"):
            notify.build_message(self.config, {**BASE_ENV, "BUILD_STATUS": "INCORRETO"})

    def test_rejects_header_injection_from_metadata(self):
        for key in ("JOB_NAME", "BUILD_NUMBER"):
            for value in ("foo\rbar", "foo\nBcc: b@example.test"):
                with self.subTest(key=key, value=value):
                    with self.assertRaises(notify.ConfigurationError):
                        notify.build_message(self.config, {**BASE_ENV, key: value})


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.config = notify.SmtpConfig.from_env(BASE_ENV)
        self.message = notify.build_message(self.config, BASE_ENV)

    @patch("scripts.notify_email.smtplib.SMTP")
    def test_mailhog_transport_without_login_or_tls(self, smtp):
        client = smtp.return_value.__enter__.return_value
        client.send_message.return_value = {}
        notify.send_message(self.config, self.message)
        smtp.assert_called_once_with("mailhog", 1025, timeout=10)
        client.send_message.assert_called_once_with(self.message)
        client.login.assert_not_called()
        client.starttls.assert_not_called()

    @patch("scripts.notify_email.ssl.create_default_context")
    @patch("scripts.notify_email.smtplib.SMTP")
    def test_starttls_before_authentication(self, smtp, context):
        client = smtp.return_value.__enter__.return_value
        client.send_message.return_value = {}
        config = notify.SmtpConfig.from_env({**BASE_ENV, "SMTP_SECURITY": "starttls",
                                            "SMTP_USERNAME": "user", "SMTP_PASSWORD": "secret"})
        notify.send_message(config, self.message)
        self.assertEqual(client.method_calls, [call.ehlo(), call.starttls(context=context.return_value),
                                              call.ehlo(), call.login("user", "secret"),
                                              call.send_message(self.message)])

    @patch("scripts.notify_email.ssl.create_default_context")
    @patch("scripts.notify_email.smtplib.SMTP_SSL")
    @patch("scripts.notify_email.smtplib.SMTP")
    def test_implicit_tls(self, smtp, smtp_ssl, context):
        smtp_ssl.return_value.__enter__.return_value.send_message.return_value = {}
        config = notify.SmtpConfig.from_env({**BASE_ENV, "SMTP_SECURITY": "ssl", "SMTP_PORT": "465"})
        notify.send_message(config, self.message)
        smtp.assert_not_called()
        smtp_ssl.assert_called_once_with("mailhog", 465, timeout=10, context=context.return_value)

    @patch("scripts.notify_email.smtplib.SMTP")
    def test_rejected_recipient_is_an_error(self, smtp):
        smtp.return_value.__enter__.return_value.send_message.return_value = {
            self.config.recipient: (550, b"rejected")}
        with self.assertRaises(smtplib.SMTPRecipientsRefused):
            notify.send_message(self.config, self.message)


class MainTests(unittest.TestCase):
    def run_main(self, env):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = notify.main(env)
        return result, stdout.getvalue(), stderr.getvalue()

    @patch("scripts.notify_email.send_message")
    def test_success(self, send):
        result, stdout, stderr = self.run_main(BASE_ENV)
        self.assertEqual(result, 0)
        self.assertIn("SUCCESS", stdout)
        self.assertEqual(stderr, "")
        send.assert_called_once()

    @patch("scripts.notify_email.send_message")
    def test_failure_notification_is_a_successful_delivery(self, send):
        result, stdout, _ = self.run_main({**BASE_ENV, "BUILD_STATUS": "FAILURE"})
        self.assertEqual(result, 0)
        self.assertIn("FAILURE", stdout)
        self.assertIn("[FAILURE]", str(send.call_args.args[1]["Subject"]))

    @patch("scripts.notify_email.send_message")
    def test_bad_configuration_does_not_connect(self, send):
        result, stdout, stderr = self.run_main({})
        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("NOTIFY_EMAIL", stderr)
        send.assert_not_called()

    @patch("scripts.notify_email.send_message")
    def test_transport_errors_do_not_expose_credentials(self, send):
        errors = [ConnectionRefusedError("senha-secreta"), TimeoutError("senha-secreta"),
                  smtplib.SMTPAuthenticationError(535, b"senha-secreta"),
                  smtplib.SMTPRecipientsRefused({"x": (550, "senha-secreta")}),
                  UnicodeError("senha-secreta")]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                send.side_effect = error
                result, stdout, stderr = self.run_main({**BASE_ENV, "SMTP_PASSWORD": "senha-secreta",
                                                       "SMTP_USERNAME": "user"})
                self.assertEqual(result, 1)
                self.assertIn(type(error).__name__, stderr)
                self.assertNotIn("senha-secreta", stdout + stderr)

    @patch.dict(os.environ, BASE_ENV, clear=True)
    @patch("scripts.notify_email.send_message")
    def test_reads_process_environment(self, send):
        with redirect_stdout(StringIO()):
            self.assertEqual(notify.main(), 0)
        self.assertEqual(send.call_args.args[0].recipient, BASE_ENV["NOTIFY_EMAIL"])

    def test_cli_rejects_missing_environment(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith(("SMTP_", "NOTIFY_"))}
        completed = subprocess.run([sys.executable, "scripts/notify_email.py"],
                                   cwd=Path(__file__).resolve().parents[1], env=env,
                                   capture_output=True, text=True, timeout=10)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("NOTIFY_EMAIL", completed.stderr)


if __name__ == "__main__":
    unittest.main()
