"""Envia o resultado do pipeline por SMTP, sem dependencias externas."""

from dataclasses import dataclass, field
from email.headerregistry import Address
from email.errors import HeaderParseError
from email.message import EmailMessage
from email.policy import SMTP as SMTP_POLICY
from email.utils import formatdate, make_msgid
import math
import os
import smtplib
import ssl
import sys
from collections.abc import Mapping


class ConfigurationError(ValueError):
    """Configuracao ausente ou invalida; a mensagem nunca inclui credenciais."""


def required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"Defina a variavel de ambiente {name}.")
    return value


def address(value: str, name: str) -> str:
    if "\r" in value or "\n" in value:
        raise ConfigurationError(f"{name} deve conter um unico endereco de e-mail.")
    try:
        parsed = Address(addr_spec=value)
        if not parsed.username or not parsed.domain:
            raise ValueError()
    except (ValueError, HeaderParseError):
        raise ConfigurationError(f"{name} deve conter um unico endereco de e-mail.") from None
    return parsed.addr_spec


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    sender: str
    recipient: str
    security: str
    timeout: float
    username: str
    password: str = field(repr=False)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "SmtpConfig":
        recipient = address(required(env, "NOTIFY_EMAIL"), "NOTIFY_EMAIL")
        sender = address(required(env, "SMTP_FROM"), "SMTP_FROM")
        host = required(env, "SMTP_HOST")
        try:
            port = int(env.get("SMTP_PORT", "1025"))
            if not 1 <= port <= 65535:
                raise ValueError()
        except ValueError:
            raise ConfigurationError("SMTP_PORT deve ser um inteiro entre 1 e 65535.") from None
        try:
            timeout = float(env.get("SMTP_TIMEOUT", "10"))
            if not math.isfinite(timeout) or timeout <= 0:
                raise ValueError()
        except ValueError:
            raise ConfigurationError("SMTP_TIMEOUT deve ser um numero positivo e finito.") from None
        security = env.get("SMTP_SECURITY", "none").strip().lower()
        if security not in {"none", "starttls", "ssl"}:
            raise ConfigurationError("SMTP_SECURITY deve ser none, starttls ou ssl.")
        username = env.get("SMTP_USERNAME", "").strip()
        password = env.get("SMTP_PASSWORD", "")
        if bool(username) != bool(password):
            raise ConfigurationError("Defina SMTP_USERNAME e SMTP_PASSWORD juntos.")
        return cls(host, port, sender, recipient, security, timeout, username, password)


def build_message(config: SmtpConfig, env: Mapping[str, str]) -> EmailMessage:
    status = env.get("BUILD_STATUS", "UNKNOWN").strip().upper()
    if status not in {"SUCCESS", "FAILURE", "UNSTABLE", "ABORTED", "NOT_BUILT", "UNKNOWN"}:
        raise ConfigurationError("BUILD_STATUS invalido.")
    job = env.get("JOB_NAME", "execucao-local").strip()
    number = env.get("BUILD_NUMBER", "local").strip()
    if any("\r" in value or "\n" in value for value in (job, number)):
        raise ConfigurationError("JOB_NAME e BUILD_NUMBER nao podem conter quebras de linha.")
    url = env.get("BUILD_URL", "").strip()
    branch = env.get("BRANCH_NAME") or env.get("GIT_BRANCH") or "nao informado"
    commit = env.get("GIT_COMMIT") or "nao informado"
    message = EmailMessage(policy=SMTP_POLICY)
    message["From"] = config.sender
    message["To"] = config.recipient
    message["Subject"] = f"[{status}] {job} #{number}"
    message["Date"] = formatdate(usegmt=True)
    # Use o dominio do remetente, inclusive em maquinas com hostname acentuado.
    message["Message-ID"] = make_msgid(domain=Address(addr_spec=config.sender).domain.encode("idna").decode("ascii"))
    message.set_content(
        f"Resultado do pipeline: {status}\n"
        f"Job: {job}\n"
        f"Build: {number}\n"
        f"Branch: {branch}\n"
        f"Commit: {commit}\n"
        f"Execucao: {url or 'nao informada'}\n"
        f"Console: {url.rstrip('/') + '/console' if url else 'nao informado'}\n",
        charset="utf-8",
    )
    return message


def send_message(config: SmtpConfig, message: EmailMessage) -> None:
    if config.security == "ssl":
        transport = smtplib.SMTP_SSL(
            config.host, config.port, timeout=config.timeout,
            context=ssl.create_default_context(),
        )
    else:
        transport = smtplib.SMTP(config.host, config.port, timeout=config.timeout)
    with transport as client:
        if config.security == "starttls":
            client.ehlo()
            client.starttls(context=ssl.create_default_context())
            client.ehlo()
        if config.username:
            client.login(config.username, config.password)
        refused = client.send_message(message)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)


def main(env: Mapping[str, str] | None = None) -> int:
    env = os.environ if env is None else env
    try:
        config = SmtpConfig.from_env(env)
        message = build_message(config, env)
        send_message(config, message)
    except ConfigurationError as exc:
        print(f"Configuracao SMTP invalida: {exc}", file=sys.stderr)
        return 2
    except (OSError, smtplib.SMTPException, UnicodeError) as exc:
        # Respostas de servidores podem conter dados sensiveis: registre somente o tipo.
        print(f"Falha no envio SMTP ({type(exc).__name__}).", file=sys.stderr)
        return 1
    print(f"Notificacao SMTP enviada. Resultado: {env.get('BUILD_STATUS', 'UNKNOWN').strip().upper()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
