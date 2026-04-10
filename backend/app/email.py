from __future__ import annotations

from email.message import EmailMessage
import smtplib

from .config import Settings


def build_login_code_message(*, sender: str, recipient: str, plain_code: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = "国际遗产观察登录验证码"
    message.set_content(f"你的登录验证码是 {plain_code}。该验证码仅用于本次登录。")
    return message


def send_login_code_email(settings: Settings, recipient: str, plain_code: str) -> None:
    message = build_login_code_message(
        sender=settings.smtp_sender,
        recipient=recipient,
        plain_code=plain_code,
    )
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)
