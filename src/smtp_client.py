"""Send notification emails via direct SMTP to the whitelisted Exchange connector.

No authentication required — the server IP is whitelisted on the connector.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr

from src.config import settings

logger = logging.getLogger(__name__)


def send_email(
    *,
    subject: str,
    html_body: str,
    to_recipients: list[str],
    from_address: str | None = None,
    bcc_recipients: list[str] | None = None,
) -> None:
    """Send an HTML email via direct SMTP (port 25, no auth)."""
    raw_from = from_address or settings.onboarding_notification_email_from
    display_name, sender_addr = parseaddr(raw_from)
    sender_display = formataddr((display_name, sender_addr)) if display_name else sender_addr
    all_recipients = list(to_recipients) + (bcc_recipients or [])

    msg = MIMEMultipart("alternative")
    msg["From"] = sender_display
    msg["To"] = ", ".join(to_recipients)
    msg["Subject"] = subject
    if bcc_recipients:
        msg["Bcc"] = ", ".join(bcc_recipients)
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    if settings.dry_run:
        logger.info("[DRY RUN] Would send email '%s' to %s", subject, to_recipients)
        return

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.sendmail(sender_addr, all_recipients, msg.as_string())

    logger.info("Sent email '%s' to %s", subject, to_recipients)
