"""Client for the LOGA HR system API (P&I / pi-asp.de)."""

import base64
import csv
import io
import json
import logging

import requests

from src.config import settings
from src.models import OnboardingUser, OffboardingUser

logger = logging.getLogger(__name__)


def fetch_new_users() -> list[OnboardingUser]:
    """Fetch upcoming new employees from the LOGA Scout report API.

    Returns a list of OnboardingUser objects parsed from the LOGA CSV response.
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

    logger.debug(f"LOGA response status: {response.status_code}")
    logger.debug(f"LOGA response headers: {response.headers}")
    logger.debug(f"LOGA response text length: {len(response.text)}")
    
    if not response.text.strip():
        logger.warning("LOGA API returned empty response")
        return []
    
    # The API with outputFormat=CSV returns CSV directly (not JSON)
    content_type = response.headers.get("Content-Type", "").lower()
    
    if "octet-stream" in content_type or response.text.startswith("Kürzel"):
        # Direct CSV response
        logger.debug("Parsing direct CSV response")
        return _parse_csv_response(response.text, OnboardingUser)
    else:
        # Try JSON with base64-encoded CSV
        logger.debug("Attempting to parse JSON response")
        try:
            body = response.json()
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text (first 500 chars): {response.text[:500]}")
            raise
        
        encoded_content: str = body.get("$content", "")
        if not encoded_content:
            logger.warning("No $content field in JSON response")
            return []
        
        decoded_bytes = base64.b64decode(encoded_content)
        csv_text = decoded_bytes.decode("utf-8")
        return _parse_csv_response(csv_text, OnboardingUser)


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

    logger.debug(f"LOGA response status: {response.status_code}")
    logger.debug(f"LOGA response headers: {response.headers}")
    logger.debug(f"LOGA response text length: {len(response.text)}")
    
    if not response.text.strip():
        logger.warning("LOGA API returned empty response")
        return []
    
    # The API with outputFormat=CSV returns CSV directly (not JSON)
    content_type = response.headers.get("Content-Type", "").lower()
    
    if "octet-stream" in content_type or response.text.startswith("Kürzel"):
        # Direct CSV response
        logger.debug("Parsing direct CSV response")
        return _parse_csv_response(response.text, OffboardingUser)
    else:
        # Try JSON with base64-encoded CSV
        logger.debug("Attempting to parse JSON response")
        try:
            body = response.json()
        except ValueError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text (first 500 chars): {response.text[:500]}")
            raise
        
        encoded_content: str = body.get("$content", "")
        if not encoded_content:
            logger.warning("No $content field in JSON response")
            return []
        
        decoded_bytes = base64.b64decode(encoded_content)
        csv_text = decoded_bytes.decode("utf-8")
        return _parse_csv_response(csv_text, OffboardingUser)


def _parse_csv_response(csv_text: str, model_class) -> list:
    """Parse CSV response from LOGA API.
    
    Args:
        csv_text: The CSV content as a string
        model_class: OnboardingUser or OffboardingUser class to instantiate
    
    Returns:
        List of model instances parsed from CSV rows
    """
    csv_reader = csv.reader(io.StringIO(csv_text), delimiter=";")
    
    # Skip header row
    header = next(csv_reader, None)
    if not header:
        logger.warning("CSV response has no header")
        return []
    
    logger.debug(f"CSV header: {header}")
    
    rows = []
    for row in csv_reader:
        if row and any(row):  # Skip empty rows
            rows.append(row)
    
    logger.info("LOGA returned %d user rows from CSV", len(rows))
    
    users = [model_class.from_loga_row(row) for row in rows]
    return users
