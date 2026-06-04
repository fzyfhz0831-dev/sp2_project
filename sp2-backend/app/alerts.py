from __future__ import annotations

import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

try:
    from app.pipeline_config import (
        ALERT_EMAIL,
        PIPELINE_LOG_PATH,
        SMTP_PASSWORD,
        SMTP_PORT,
        SMTP_SERVER,
        SMTP_USER,
    )
    from app.utils import setup_logger
except ImportError:
    from app.pipeline_config import ALERT_EMAIL, PIPELINE_LOG_PATH, SMTP_PASSWORD, SMTP_PORT, SMTP_SERVER, SMTP_USER
    from app.utils import setup_logger


LOGGER = setup_logger(str(PIPELINE_LOG_PATH))


def _email_is_configured() -> bool:
    """Return True only when SMTP placeholders have been replaced."""
    placeholder_values = {
        "your_email@example.com",
        "smtp.example.com",
        "your_smtp_user",
        "your_smtp_password",
        "",
    }

    return not {
        ALERT_EMAIL,
        SMTP_SERVER,
        SMTP_USER,
        SMTP_PASSWORD,
    }.intersection(placeholder_values)


def send_alert(message: str) -> None:
    """Send an alert by email, or log it when email is not configured."""
    timestamp = datetime.now(timezone.utc).isoformat()
    alert_body = f"Timestamp: {timestamp}\n\n{message}"

    # Beginner note: configure SMTP values in backend/config.py to enable email.
    # Until then, alerts are written to logs/pipeline.log so nothing crashes.
    if not _email_is_configured():
        LOGGER.warning("Alert email is not configured. Alert logged only: %s", alert_body)
        return

    email = EmailMessage()
    email["Subject"] = "SP2 Run Doctor Pipeline Alert"
    email["From"] = SMTP_USER
    email["To"] = ALERT_EMAIL
    email.set_content(alert_body)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(SMTP_USER, SMTP_PASSWORD)
            smtp.send_message(email)
        LOGGER.info("Alert email sent to %s", ALERT_EMAIL)
    except Exception as error:
        # Alerts should never break the pipeline. Log SMTP failures and move on.
        LOGGER.exception("Failed to send alert email: %s", error)
