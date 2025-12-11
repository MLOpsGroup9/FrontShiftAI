"""Simple, defensive email notifier."""

from __future__ import annotations

import json
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent / "email_config.json"


def _load_creds(config_path: Path = CONFIG_PATH):
    # Prefer environment variables, then config file for local/dev usage.
    sender = os.getenv("EMAIL_SENDER")
    password = os.getenv("EMAIL_PASSWORD")
    receiver = os.getenv("EMAIL_RECEIVER")

    if sender and password and receiver:
        return sender, password, receiver

    if config_path.exists():
        try:
            creds = json.loads(config_path.read_text(encoding="utf-8"))
            return creds.get("sender"), creds.get("password"), creds.get("receiver")
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Failed to read email config at %s: %s", config_path, exc)

    return sender, password, receiver


def send_email(
    subject: str,
    message: str,
    *,
    sender: Optional[str] = None,
    password: Optional[str] = None,
    receiver: Optional[str] = None,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 465,
    timeout: int = 15,
) -> bool:
    """Send an email using SSL or STARTTLS. Returns True on success, False otherwise."""

    sender = sender or _load_creds()[0]
    password = password or _load_creds()[1]
    receiver = receiver or _load_creds()[2]

    if not all([sender, password, receiver]):
        logger.warning("Email credentials are missing; skipping notification.")
        return False

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    # Try SSL first; fallback to STARTTLS if using port 587.
    try:
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=timeout) as server:
                server.login(sender, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as server:
                server.starttls()
                server.login(sender, password)
                server.send_message(msg)
        logger.info("Email sent successfully to %s", receiver)
        return True
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to send email: %s", exc)
        return False


__all__ = ["send_email"]
