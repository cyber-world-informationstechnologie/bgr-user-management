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
    
    Handles CSV where some rows may span multiple lines (line breaks within unquoted fields).
    A new record starts when we encounter a non-empty Kürzel (abbreviation) field.
    
    Args:
        csv_text: The CSV content as a string
        model_class: OnboardingUser or OffboardingUser class to instantiate
    
    Returns:
        List of model instances parsed from CSV rows
    """
    lines = csv_text.strip().split('\n')
    if not lines:
        logger.warning("CSV response is empty")
        return []
    
    # Parse header row
    header = lines[0].split(';')
    expected_cols = len(header)
    logger.debug(f"CSV has {expected_cols} columns")
    
    # Parse data rows, handling multi-line rows
    rows = []
    current_row = []
    
    for line_idx, line in enumerate(lines[1:], start=2):
        parts = line.split(';')
        
        # Check if this line starts a new record (non-empty Kürzel/abbreviation at field 0)
        is_new_record = parts and parts[0].strip() != ""
        
        if is_new_record and current_row:
            # We have a current row and this is a new record
            # Save the current row (trim to expected columns if it's larger)
            rows.append(current_row[:expected_cols])
            current_row = parts
        elif is_new_record:
            # New record with no current row
            current_row = parts
        else:
            # Continuation of previous row
            if current_row:
                # Handle LOGA exports that add duplicate empty fields between continuations
                # If this continuation starts with an empty field and we already have fields,
                # skip the first empty field to avoid duplication
                if parts and not parts[0].strip() and len(current_row) > 0:
                    parts = parts[1:]
                
                current_row.extend(parts)
                
                # If we've reached or exceeded the expected column count, this row is complete
                if len(current_row) >= expected_cols:
                    rows.append(current_row[:expected_cols])
                    current_row = []
            else:
                # Shouldn't happen but handle gracefully
                current_row = parts
    
    # Don't forget the last row
    if current_row:
        rows.append(current_row[:expected_cols])
    
    # Pad rows that are too short
    for row in rows:
        while len(row) < expected_cols:
            row.append('')
    
    logger.info("Parsed %d rows from CSV", len(rows))
    
    # Create model instances
    users = [model_class.from_loga_row(row) for row in rows]
    return users
