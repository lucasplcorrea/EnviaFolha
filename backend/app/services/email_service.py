"""Envio de e-mails transacionais com holerites anexados."""

from __future__ import annotations

import html
import os
import smtplib
import ssl
from dataclasses import asdict, dataclass
from email.message import EmailMessage
from email.utils import formataddr, make_msgid, parseaddr
from pathlib import Path
from typing import Callable, Optional

from email_validator import EmailNotValidError, validate_email

from app.core.config import settings


DEFAULT_PAYROLL_SUBJECT = "Holerite referente a {competencia}"
DEFAULT_PAYROLL_BODY = (
    "Olá, {primeiro_nome}.\n\n"
    "Segue em anexo seu holerite referente a {competencia}. "
    "Para abrir o documento, utilize os 4 primeiros dígitos do seu CPF.\n\n"
    "Em caso de dúvidas, entre em contato com o Departamento de Recursos Humanos.\n\n"
    "Atenciosamente,\nRecursos Humanos"
)


@dataclass(frozen=True)
class EmailSendResult:
    success: bool
    status: str
    message_id: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)


class EmailService:
    """Cliente SMTP isolado para facilitar testes e evitar acoplamento ao WhatsApp."""

    def __init__(self, smtp_factory: Optional[Callable] = None):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.username = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_name, self.from_address = parseaddr(settings.SMTP_FROM)
        self.security = settings.get_smtp_security()
        self.timeout = settings.SMTP_TIMEOUT_SECONDS
        self.max_attachment_size = settings.SMTP_MAX_ATTACHMENT_SIZE
        self.smtp_factory = smtp_factory

    @staticmethod
    def validate_recipient(recipient: str) -> str:
        """Valida e normaliza o endereço sem consultar DNS."""
        if not recipient or any(char in recipient for char in ('\r', '\n')):
            raise ValueError("Endereço de e-mail inválido")
        try:
            return validate_email(recipient, check_deliverability=False).normalized
        except EmailNotValidError as exc:
            raise ValueError(f"Endereço de e-mail inválido: {exc}") from exc

    def _validate_configuration(self) -> None:
        if not settings.has_smtp_configured():
            raise RuntimeError("SMTP não configurado: informe host, usuário e senha")
        if not self.from_address:
            raise RuntimeError("SMTP_FROM não contém um endereço válido")
        self.validate_recipient(self.from_address)

    def _connect(self):
        self._validate_configuration()
        context = ssl.create_default_context()

        if self.smtp_factory:
            client = self.smtp_factory(self.host, self.port, self.timeout, self.security)
        elif self.security == 'ssl':
            client = smtplib.SMTP_SSL(
                self.host,
                self.port,
                timeout=self.timeout,
                context=context,
            )
        else:
            client = smtplib.SMTP(self.host, self.port, timeout=self.timeout)

        client.ehlo()
        if self.security == 'starttls':
            client.starttls(context=context)
            client.ehlo()
        client.login(self.username, self.password)
        return client

    def test_connection(self) -> EmailSendResult:
        """Autentica no SMTP sem enviar mensagem."""
        try:
            with self._connect() as client:
                client.noop()
            return EmailSendResult(success=True, status='connected')
        except Exception as exc:
            return EmailSendResult(
                success=False,
                status='failed',
                error_message=self._safe_error(exc),
            )

    def send_payroll(
        self,
        recipient: str,
        employee_name: str,
        file_path: str,
        competence: str,
        subject_template: str = DEFAULT_PAYROLL_SUBJECT,
        body_template: str = DEFAULT_PAYROLL_BODY,
    ) -> EmailSendResult:
        """Envia um holerite e retorna aceitação pelo servidor SMTP."""
        try:
            normalized_recipient = self.validate_recipient(recipient)
            attachment = self._validate_attachment(file_path)
            first_name = (employee_name or '').strip().split(' ')[0] or 'colaborador(a)'
            replacements = {
                'nome': employee_name or 'Colaborador(a)',
                'primeiro_nome': first_name,
                'competencia': competence,
                'mes_anterior': competence,
            }
            subject = self._render(subject_template, replacements).strip()
            body = self._render(body_template, replacements).strip()
            self._reject_header_injection(subject)

            message_id = make_msgid()
            message = EmailMessage()
            message['From'] = formataddr((self.from_name, self.from_address))
            message['To'] = normalized_recipient
            message['Subject'] = subject
            message['Message-ID'] = message_id
            message.set_content(body)
            message.add_alternative(
                '<html><body><p>'
                + html.escape(body).replace('\n', '<br>')
                + '</p></body></html>',
                subtype='html',
            )
            message.add_attachment(
                attachment.read_bytes(),
                maintype='application',
                subtype='pdf',
                filename=attachment.name,
            )

            with self._connect() as client:
                refused = client.send_message(message)
            if refused:
                return EmailSendResult(
                    success=False,
                    status='failed',
                    message_id=message_id,
                    error_message="O servidor SMTP recusou o destinatário",
                )
            return EmailSendResult(
                success=True,
                status='accepted',
                message_id=message_id,
            )
        except Exception as exc:
            return EmailSendResult(
                success=False,
                status='failed',
                error_message=self._safe_error(exc),
            )

    def _validate_attachment(self, file_path: str) -> Path:
        attachment = Path(file_path)
        if not attachment.is_file():
            raise FileNotFoundError("Arquivo do holerite não encontrado")
        if attachment.suffix.lower() != '.pdf':
            raise ValueError("Somente arquivos PDF podem ser enviados")
        file_size = os.path.getsize(attachment)
        if file_size <= 0:
            raise ValueError("O PDF do holerite está vazio")
        if file_size > self.max_attachment_size:
            limit_mb = self.max_attachment_size // (1024 * 1024)
            raise ValueError(f"O PDF excede o limite de {limit_mb} MB para e-mail")
        return attachment

    @staticmethod
    def _render(template: str, replacements: dict) -> str:
        rendered = template
        for key, value in replacements.items():
            rendered = rendered.replace('{' + key + '}', str(value))
        return rendered

    @staticmethod
    def _reject_header_injection(value: str) -> None:
        if '\r' in value or '\n' in value:
            raise ValueError("Assunto do e-mail contém caracteres inválidos")

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        """Retorna erro operacional sem incluir credenciais/configuração sensível."""
        if isinstance(exc, smtplib.SMTPAuthenticationError):
            return "Falha de autenticação no servidor SMTP"
        if isinstance(exc, (TimeoutError, smtplib.SMTPServerDisconnected)):
            return "Servidor SMTP indisponível ou tempo de conexão excedido"
        if isinstance(exc, smtplib.SMTPException):
            return "O servidor SMTP rejeitou a operação"
        return str(exc)
