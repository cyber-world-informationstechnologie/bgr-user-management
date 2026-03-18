"""Client for the LOGA HR system API (P&I / pi-asp.de)."""

import logging

import requests

from src.config import settings
from src.models import OnboardingUser, OffboardingUser

logger = logging.getLogger(__name__)


def _fetch_loga_report(job_file_content: str) -> list[dict[str, str]]:
    """Fetch a LOGA Scout report as JSON and return a list of header-keyed dicts.

    The P&I API returns JSON with:
      - ``headers``: list of column descriptors (each has a ``fieldTitle``)
      - ``data``: list of rows (each row is a list of string values)

    We pair each row's values with the corresponding ``fieldTitle`` to produce
    a ``{fieldTitle: value}`` dict per row.
    """
    response = requests.post(
        settings.loga_api_url,
        headers={"Content-Type": "application/json"},
        json={
            "jobFileContent": job_file_content,
            "outputFormat": "JSON",
        },
        timeout=120,
    )
    response.raise_for_status()

    if not response.text.strip():
        logger.warning("LOGA API returned empty response")
        return []

    body = response.json()
    headers = body.get("headers", [])
    data = body.get("data", [])

    # Build ordered list of display titles from header metadata
    field_titles = [h["fieldTitle"] for h in headers]
    logger.debug("LOGA report columns: %s", field_titles)
    logger.info("Fetched %d rows from LOGA API", len(data))

    # Convert each row (list of values) into a {fieldTitle: value} dict.
    # Handle duplicate fieldTitles (e.g. "Kostenstelle" appears twice in
    # onboarding — once as cost-center number and once as team/partner).
    dict_rows: list[dict[str, str]] = []
    for row_values in data:
        row_dict: dict[str, str] = {}
        seen: dict[str, int] = {}
        for idx, title in enumerate(field_titles):
            val = row_values[idx] if idx < len(row_values) else ""
            val = val.strip() if isinstance(val, str) else str(val)
            count = seen.get(title, 0)
            if count > 0:
                row_dict[f"{title}#{count + 1}"] = val
            else:
                row_dict[title] = val
            seen[title] = count + 1
        dict_rows.append(row_dict)
        logger.debug("Row: %s", row_dict)

    return dict_rows


def fetch_new_users() -> list[OnboardingUser]:
    """Fetch upcoming new employees from the LOGA Scout report API."""
    logger.info("Fetching new users from LOGA API…")
    rows = _fetch_loga_report(settings.loga_onboarding_job_file_content)
    return [OnboardingUser.from_loga_row(r) for r in rows]


def fetch_exiting_users() -> list[OffboardingUser]:
    """Fetch exiting employees from the LOGA Scout report API."""
    logger.info("Fetching exiting users from LOGA API…")
    rows = _fetch_loga_report(settings.loga_offboarding_job_file_content)
    return [OffboardingUser.from_loga_row(r) for r in rows]
