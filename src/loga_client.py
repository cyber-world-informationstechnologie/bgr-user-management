"""Client for the LOGA HR system API (P&I / pi-asp.de)."""

import base64
import logging

import requests

from src.config import settings
from src.models import OnboardingUser, OffboardingUser

logger = logging.getLogger(__name__)


def fetch_new_users() -> list[OnboardingUser]:
    """Fetch upcoming new employees from the LOGA Scout report API.

    Returns a list of OnboardingUser objects parsed from the LOGA response.
    """
    logger.info("Fetching new users from LOGA API…")

    response = requests.post(
        settings.loga_api_url,
        headers={"Content-Type": "application/json"},
        json={
            "jobFileContent": settings.loga_onboarding_job_file_content,
            "outputFormat": "CSV",
        },
        timeout=120,
    )
    response.raise_for_status()

    # The API returns a JSON body with a base64-encoded '$content' field
    body = response.json()
    encoded_content: str = body.get("$content", "")

    if not encoded_content:
        # Some responses may already be plain JSON
        data_payload = body
    else:
        decoded_bytes = base64.b64decode(encoded_content)
        import json

        data_payload = json.loads(decoded_bytes)

    rows: list[list[str]] = data_payload.get("data", [])
    logger.info("LOGA returned %d user rows", len(rows))

    users = [OnboardingUser.from_loga_row(row) for row in rows]
    return users


def fetch_exiting_users() -> list[OffboardingUser]:
    """Fetch exiting employees from the LOGA Scout report API.

    Returns a list of OffboardingUser objects parsed from the LOGA response.
    Uses the offboarding-specific job file content from settings.
    """
    logger.info("Fetching exiting users from LOGA API…")

    response = requests.post(
        settings.loga_api_url,
        headers={"Content-Type": "application/json"},
        json={
            "jobFileContent": settings.loga_offboarding_job_file_content,
            "outputFormat": "CSV",
        },
        timeout=120,
    )
    response.raise_for_status()

    # The API returns a JSON body with a base64-encoded '$content' field
    body = response.json()
    encoded_content: str = body.get("$content", "")

    if not encoded_content:
        # Some responses may already be plain JSON
        data_payload = body
    else:
        decoded_bytes = base64.b64decode(encoded_content)
        import json

        data_payload = json.loads(decoded_bytes)

    rows: list[list[str]] = data_payload.get("data", [])
    logger.info("LOGA returned %d exiting user rows", len(rows))

    users = [OffboardingUser.from_loga_row(row) for row in rows]
