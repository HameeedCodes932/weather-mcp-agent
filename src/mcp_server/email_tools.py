import logging
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("weather-mcp")


def _load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass


def _get_email_config() -> tuple[str, str]:
    _load_env()
    address = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")
    if not address or not password:
        raise ValueError(
            "Gmail not configured. Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env\n"
            "Get an App Password at: https://myaccount.google.com/apppasswords"
        )
    return address, password


def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via Gmail SMTP.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Plain text email body
    """
    try:
        sender, app_password = _get_email_config()

        msg = MIMEMultipart("alternative")
        msg["From"] = sender
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls(context=context)
            server.login(sender, app_password)
            server.sendmail(sender, to, msg.as_string())

        logger.info("Email sent to %s: %s", to, subject)
        return f"Email sent successfully to {to} with subject '{subject}'."

    except smtplib.SMTPAuthenticationError:
        return (
            "Failed to authenticate with Gmail. Make sure you're using an App Password, "
            "not your regular password.\n"
            "Generate one at: https://myaccount.google.com/apppasswords\n"
            "(Requires 2-Step Verification enabled on your Google account.)"
        )
    except ValueError as e:
        return str(e)
    except Exception as e:
        logger.exception("Failed to send email")
        return f"Failed to send email: {e}"
