import os
import smtplib
from email.message import EmailMessage


def send_password_reset_email(recipient: str, token: str) -> None:
    host = os.getenv("NEXUS_SMTP_HOST")
    sender = os.getenv("NEXUS_SMTP_FROM")
    if not host or not sender:
        if os.getenv("NEXUS_SMTP_REQUIRED", "false").lower() == "true":
            raise RuntimeError("SMTP password recovery delivery is not configured")
        return

    port = int(os.getenv("NEXUS_SMTP_PORT", "587"))
    username = os.getenv("NEXUS_SMTP_USERNAME")
    password = os.getenv("NEXUS_SMTP_PASSWORD")
    base_url = os.getenv("NEXUS_WEB_BASE_URL", "http://localhost:3000").rstrip("/")
    message = EmailMessage()
    message["Subject"] = "Reset your NEXUS password"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"Reset your NEXUS password: {base_url}/reset-password?token={token}\n\n"
        "This link expires in 30 minutes and can only be used once."
    )
    with smtplib.SMTP(host, port, timeout=10) as smtp:
        smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)


def send_email_verification_email(recipient: str, token: str) -> None:
    host = os.getenv("NEXUS_SMTP_HOST")
    sender = os.getenv("NEXUS_SMTP_FROM")
    if not host or not sender:
        if os.getenv("NEXUS_SMTP_REQUIRED", "false").lower() == "true":
            raise RuntimeError("SMTP email verification delivery is not configured")
        return
    port = int(os.getenv("NEXUS_SMTP_PORT", "587"))
    username = os.getenv("NEXUS_SMTP_USERNAME")
    password = os.getenv("NEXUS_SMTP_PASSWORD")
    base_url = os.getenv("NEXUS_WEB_BASE_URL", "http://localhost:3000").rstrip("/")
    message = EmailMessage()
    message["Subject"] = "Verify your NEXUS email"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        f"Verify your NEXUS email: {base_url}/verify-email?token={token}\n\n"
        "This link expires in 24 hours and can only be used once."
    )
    with smtplib.SMTP(host, port, timeout=10) as smtp:
        smtp.starttls()
        if username and password:
            smtp.login(username, password)
        smtp.send_message(message)
