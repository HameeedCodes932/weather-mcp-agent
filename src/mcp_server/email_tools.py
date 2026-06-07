import logging
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("weather-mcp")

_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _load_env():
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))
    except ImportError:
        pass


def _get_smtp_config() -> dict:
    _load_env()
    return {
        "host": os.getenv("SMTP_HOST", "smtp-relay.brevo.com"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME"),
        "password": os.getenv("SMTP_PASSWORD"),
        "from_addr": os.getenv("SMTP_FROM", os.getenv("SMTP_USERNAME", "")),
    }


def send_email(to: str, subject: str, body: str) -> str:
    """Send an email via SMTP.

    Configure SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD in .env.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Plain text email body
    """
    try:
        cfg = _get_smtp_config()
        logger.info("SMTP config: host=%s, user=%s, from=%s", cfg["host"], cfg["username"], cfg["from_addr"])
        if not cfg["username"] or not cfg["password"]:
            return (
                "Email not configured. Set these in .env:\n"
                "  SMTP_HOST=smtp-relay.brevo.com\n"
                "  SMTP_PORT=587\n"
                "  SMTP_USERNAME=your_brevo_login\n"
                "  SMTP_PASSWORD=your_smtp_key\n"
                "  SMTP_FROM=your_sender_email\n\n"
                "Get Brevo SMTP credentials at: https://app.brevo.com/settings/keys/smtp"
            )

        msg = MIMEMultipart("alternative")
        msg["From"] = cfg["from_addr"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        context = ssl.create_default_context()
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            server.starttls(context=context)
            server.login(cfg["username"], cfg["password"])
            server.sendmail(cfg["from_addr"], to, msg.as_string())

        logger.info("Email sent to %s: %s", to, subject)
        return f"Email sent successfully to {to} with subject '{subject}'."

    except smtplib.SMTPAuthenticationError:
        return (
            "Failed to authenticate with the SMTP server. Check your username and password in .env.\n"
            "For Gmail, use an App Password: https://myaccount.google.com/apppasswords\n"
            "For Brevo, use your SMTP credentials from https://brevo.com"
        )
    except ValueError as e:
        return str(e)
    except Exception as e:
        logger.exception("Failed to send email")
        return f"Failed to send email: {e}"
