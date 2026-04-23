"""Persistent state of users we have provisioned ourselves.

Used to distinguish between accounts that already exist in AD because we
created them in a previous run (safe to reconcile / silently skip) and
accounts that exist because someone else / something else owns the
abbreviation or email address (must trigger a conflict notification).

The store is a simple JSON file:

    {
        "users": [
            {
                "pnr": "12345",
                "abbreviation": "ABC",
                "email": "alice@bgr.at",
                "provisioned_at": "2026-01-15T08:30:00+00:00"
            },
            ...
        ]
    }
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from src.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProvisionedRecord:
    pnr: str
    abbreviation: str
    email: str
    provisioned_at: str


def _state_path() -> Path:
    return Path(settings.state_file_path).expanduser().resolve()


def _load_raw() -> dict:
    path = _state_path()
    if not path.exists():
        return {"users": []}
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or "users" not in data:
            logger.warning("State file %s has unexpected shape — ignoring", path)
            return {"users": []}
        return data
    except (OSError, json.JSONDecodeError):
        logger.exception("Failed to read state file %s — treating as empty", path)
        return {"users": []}


def load_provisioned() -> list[ProvisionedRecord]:
    """Return all records from the state file."""
    data = _load_raw()
    records: list[ProvisionedRecord] = []
    for entry in data.get("users", []):
        try:
            records.append(
                ProvisionedRecord(
                    pnr=str(entry.get("pnr", "")),
                    abbreviation=str(entry.get("abbreviation", "")).upper(),
                    email=str(entry.get("email", "")).lower(),
                    provisioned_at=str(entry.get("provisioned_at", "")),
                )
            )
        except Exception:
            logger.exception("Skipping malformed state entry: %r", entry)
    return records


def is_provisioned_by_us(*, abbreviation: str = "", email: str = "") -> bool:
    """Return True if either *abbreviation* or *email* matches a record we own."""
    abbr_norm = abbreviation.strip().upper()
    email_norm = email.strip().lower()
    if not abbr_norm and not email_norm:
        return False
    for rec in load_provisioned():
        if abbr_norm and rec.abbreviation == abbr_norm:
            return True
        if email_norm and rec.email == email_norm:
            return True
    return False


def mark_provisioned(*, pnr: str, abbreviation: str, email: str) -> None:
    """Persist that we provisioned the given user.

    Idempotent: an existing entry for the same abbreviation is replaced.
    Skipped silently in dry-run mode so we don't pollute state with
    accounts that were never actually created.
    """
    if settings.dry_run:
        logger.info(
            "[DRY RUN] Would record provisioning of %s (%s) in state file",
            abbreviation,
            email,
        )
        return

    abbr_norm = abbreviation.strip().upper()
    email_norm = email.strip().lower()

    data = _load_raw()
    users = [
        u
        for u in data.get("users", [])
        if str(u.get("abbreviation", "")).upper() != abbr_norm
    ]
    users.append(
        {
            "pnr": pnr,
            "abbreviation": abbr_norm,
            "email": email_norm,
            "provisioned_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
    data["users"] = users
    _atomic_write(data)
    logger.info("Recorded provisioning of %s (%s) in state file", abbr_norm, email_norm)


def _atomic_write(data: dict) -> None:
    """Write JSON atomically (tmp file + rename) to avoid corruption."""
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".state-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
