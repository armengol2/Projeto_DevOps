"""Testes opt-in contra um MailHog real. Nao apagam mensagens existentes."""

from email import message_from_string
from email.policy import default
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from urllib.request import urlopen
import uuid


@unittest.skipUnless(os.environ.get("RUN_MAILHOG_TESTS") == "1", "Ative RUN_MAILHOG_TESTS=1 com MailHog ativo")
class MailHogIntegrationTests(unittest.TestCase):
    def test_success_and_failure_are_received_by_mailhog(self):
        api = os.environ.get("MAILHOG_API_URL", "http://127.0.0.1:8025").rstrip("/")
        for status in ("SUCCESS", "FAILURE"):
            with self.subTest(status=status):
                job = f"smtp-test-{uuid.uuid4().hex}"
                # Herde o ambiente do processo para funcionar tambem no Windows,
                # mas isole quaisquer credenciais SMTP do usuario ou do Jenkins.
                env = {k: v for k, v in os.environ.items() if not k.startswith(("SMTP_", "NOTIFY_"))}
                env.update({
                    "SMTP_HOST": os.environ.get("MAILHOG_SMTP_HOST", "127.0.0.1"),
                    "SMTP_PORT": os.environ.get("MAILHOG_SMTP_PORT", "1025"),
                    "SMTP_FROM": "jenkins@example.test",
                    "NOTIFY_EMAIL": "destinatario@example.test",
                    "BUILD_STATUS": status,
                    "JOB_NAME": job,
                    "BUILD_NUMBER": "1",
                    "BUILD_URL": f"http://jenkins:8080/job/{job}/1/",
                    "GIT_COMMIT": "test-commit",
                })
                completed = subprocess.run([sys.executable, "scripts/notify_email.py"],
                                           cwd=Path(__file__).resolve().parents[1], env=env,
                                           capture_output=True, text=True, timeout=15)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                received = None
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    with urlopen(f"{api}/api/v2/messages?limit=200", timeout=5) as response:
                        items = json.load(response)["items"]
                    for item in items:
                        message = message_from_string(item["Raw"]["Data"], policy=default)
                        if str(message["Subject"]) == f"[{status}] {job} #1":
                            received = message
                            break
                    if received is not None:
                        break
                    time.sleep(0.1)
                self.assertIsNotNone(received, "A mensagem nao apareceu na API do MailHog")
                self.assertEqual(str(received["To"]), env["NOTIFY_EMAIL"])
                self.assertEqual(str(received["From"]), env["SMTP_FROM"])
                self.assertIn(f"Resultado do pipeline: {status}", received.get_content())
                self.assertIn(env["BUILD_URL"], received.get_content())
                self.assertIn("test-commit", received.get_content())


if __name__ == "__main__":
    unittest.main()
