"""Microsoft Graph API client for email and user existence checks.

Uses MSAL for client-credentials authentication against Entra ID.
User creation and group management happen on-premise via AD/Exchange (see ad_client.py).

Requires the following Graph API application permissions:
  - User.Read.All
  - Mail.Send
"""

import logging

import msal
import requests

from src.config import settings

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphClient:
    def __init__(self) -> None:
        self._app = msal.ConfidentialClientApplication(
            client_id=settings.azure_client_id,
            client_credential=settings.azure_client_secret,
            authority=f"https://login.microsoftonline.com/{settings.azure_tenant_id}",
        )
        self._token: str = ""

    def _ensure_token(self) -> None:
        """Acquire or refresh the access token."""
        result = self._app.acquire_token_for_client(
            scopes=["https://graph.microsoft.com/.default"]
        )
        if "access_token" not in result:
            raise RuntimeError(f"Failed to acquire Graph token: {result.get('error_description')}")
        self._token = result["access_token"]

    def _headers(self) -> dict[str, str]:
        self._ensure_token()
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    # ── User search ──────────────────────────────────────────────────

    def user_exists(self, email: str) -> bool:
        """Check if a user with the given email already exists in Entra ID."""
        if not email:
            return False

        url = f"{GRAPH_BASE}/users"
        params = {
            "$filter": f"mail eq '{email}' or userPrincipalName eq '{email}'",
            "$top": "1",
            "$select": "id,mail",
        }
        resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
        resp.raise_for_status()
        return len(resp.json().get("value", [])) > 0

    # ── Email ────────────────────────────────────────────────────────

    def send_email(
        self,
        *,
        subject: str,
        html_body: str,
        to_recipients: list[str],
        from_address: str | None = None,
        bcc_recipients: list[str] | None = None,
    ) -> None:
        """Send an email via Microsoft Graph API."""
        sender = from_address or settings.notification_email_from

        message = {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": [{"emailAddress": {"address": addr}} for addr in to_recipients],
        }
        if bcc_recipients:
            message["bccRecipients"] = [
                {"emailAddress": {"address": addr}} for addr in bcc_recipients
            ]

        payload = {"message": message, "saveToSentItems": True}

        if settings.dry_run:
            logger.info("[DRY RUN] Would send email '%s' to %s", subject, to_recipients)
            return

        url = f"{GRAPH_BASE}/users/{sender}/sendMail"
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=30)
        resp.raise_for_status()
        logger.info("Sent email '%s' to %s", subject, to_recipients)
