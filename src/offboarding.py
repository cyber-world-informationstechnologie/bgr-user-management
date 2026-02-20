"""Main offboarding orchestration — deprovisioning users from AD and Exchange.

Offboarding runs on the day AFTER the exit_date (last work day):
  1. Exchange: Convert to shared mailbox, set up forwarding, add absence notice, remove from groups
  2. Active Directory: Disable account, move to Disabled Users OU, remove group memberships
  3. Notifications: Send summary email to stakeholders (only once, unless --resend is used)
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from src.ad_client import (
    disable_user_account,
    move_user_to_ou,
    remove_user_from_all_groups,
    setup_mailbox_forwarding,
    convert_mailbox_to_shared,
    set_mailbox_autoreply,
    remove_from_distribution_groups,
)
from src.config import settings
from src.email_builder import OffboardingEmailRow, build_offboarding_email
from src.loga_client import fetch_exiting_users
from src.models import OffboardingUser
from src.smtp_client import send_email

logger = logging.getLogger(__name__)

# File to track which offboarding emails have been sent
OFFBOARDED_USERS_FILE = Path("logs") / "offboarded_users.json"


def _get_manager_email(user: OffboardingUser) -> str | None:
    """Lookup manager email from manager abbreviation (team field).

    This is a simplified version — in production you'd query AD for the manager's details.
    """
    # TODO: Query AD to get manager's email from abbreviation
    # For now, return None — the mailbox will remain without forwarding if manager not found
    if user.manager_abbreviation:
        logger.info("Manager abbreviation for %s: %s", user.email, user.manager_abbreviation)
    return None


def _load_offboarded_users() -> dict:
    """Load the set of users who have already received offboarding emails.
    
    Returns a dict mapping email -> timestamp of when the email was sent.
    """
    if not OFFBOARDED_USERS_FILE.exists():
        return {}
    
    try:
        with open(OFFBOARDED_USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("Could not load offboarded users file: %s", e)
        return {}


def _save_offboarded_users(users: dict) -> None:
    """Save the set of users who have received offboarding emails."""
    OFFBOARDED_USERS_FILE.parent.mkdir(exist_ok=True)
    try:
        with open(OFFBOARDED_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
    except IOError as e:
        logger.error("Could not save offboarded users file: %s", e)


def _mark_user_as_offboarded(email: str) -> None:
    """Record that an offboarding email was sent for this user."""
    users = _load_offboarded_users()
    users[email] = datetime.now().isoformat()
    _save_offboarded_users(users)


def _has_offboarding_email_been_sent(email: str) -> bool:
    """Check if an offboarding email has already been sent for this user."""
    users = _load_offboarded_users()
    return email in users


def _process_user(user: OffboardingUser) -> OffboardingEmailRow | None:
    """Process a single user for offboarding.

    Steps:
    1. Set up Exchange forwarding and absence notice
    2. Convert mailbox to shared mailbox
    3. Remove from distribution groups
    4. Disable AD account and move to Disabled Users OU
    5. Remove from all groups (except Domain Users)
    6. Collect offboarding summary

    Returns an OffboardingEmailRow for the summary email, or None if skipped.
    """
    try:
        logger.info("Starting offboarding for %s (exit date: %s)", user.email, user.exit_date)

        # Exchange operations (these should be done before disabling the account)
        manager_email = _get_manager_email(user)
        
        # Convert to shared mailbox
        convert_mailbox_to_shared(user.email)
        
        # Set up auto-reply
        set_mailbox_autoreply(user.email, settings.offboarding_absence_notice)
        
        # Set up forwarding to manager (if manager is known)
        if manager_email:
            setup_mailbox_forwarding(user.email, manager_email)
        else:
            logger.warning("No manager found for %s — forwarding not configured", user.email)
        
        # Remove from distribution groups
        remove_from_distribution_groups(user.email)

        # Active Directory cleanup
        disable_user_account(user.abbreviation)
        move_user_to_ou(user.abbreviation, settings.offboarding_disabled_users_ou)
        remove_user_from_all_groups(user.abbreviation)

        logger.info("Offboarding completed for %s", user.email)

        return OffboardingEmailRow(
            exit_date=user.exit_date,
            full_name=user.full_display_name,
            email=user.email,
            abbreviation=user.abbreviation,
            phone=user.phone,
            room=user.room,
            team=user.team,
            birth_date=user.birth_date,
            kostenstelle=user.kostenstelle,
        )

    except Exception:
        logger.exception("Failed to offboard user %s", user.email)
        # Send error notification
        try:
            send_email(
                subject=f"Offboarding fehlgeschlagen: {user.email}",
                html_body=(
                    f"<p>Das automatische Offboarding des Benutzers "
                    f"<strong>{user.full_display_name}</strong> ({user.email}) "
                    f"ist fehlgeschlagen. Bitte manuell prüfen.</p>"
                ),
                to_recipients=[settings.error_notification_email],
            )
        except Exception:
            logger.exception("Failed to send error notification email")
        return None


def run_offboarding(resend: bool = False) -> None:
    """Execute the full offboarding flow.

    1. Fetch exiting users from LOGA HR system whose exit_date is today - 1 (yesterday)
    2. For each exiting user:
       a. Convert Exchange mailbox to shared mailbox
       b. Set auto-reply / out-of-office notice (no end date)
       c. Set up mail forwarding to manager (with copy to original mailbox)
       d. Remove from all email distribution groups
       e. Disable AD account
       f. Move to 'Disabled Users' OU
       g. Remove group memberships (except Domain Users)
    3. Send summary email to stakeholders (only once per user, unless resend=True)
    
    Args:
        resend: If True, resend emails even for users who have already been offboarded
    """
    logger.info("Starting offboarding process…")
    if resend:
        logger.info("RESEND MODE: Will re-process users even if emails were already sent")

    users = fetch_exiting_users()
    logger.info("Fetched %d potentially exiting users", len(users))

    # Filter to only users whose exit_date was yesterday (one day ago)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")
    exiting_today = [u for u in users if u.exit_date == yesterday]

    if not exiting_today:
        logger.info("No users to offboard today (looking for exit_date=%s)", yesterday)
        return

    logger.info("Processing %d users for offboarding (exit_date = %s)", len(exiting_today), yesterday)

    # Filter out users who have already received offboarding emails (unless resend=True)
    if not resend:
        already_offboarded = [u for u in exiting_today if _has_offboarding_email_been_sent(u.email)]
        if already_offboarded:
            logger.info(
                "Skipping %d users who have already received offboarding emails: %s",
                len(already_offboarded),
                ", ".join(u.email for u in already_offboarded),
            )
        exiting_today = [u for u in exiting_today if not _has_offboarding_email_been_sent(u.email)]
        
        if not exiting_today:
            logger.info("No new users to offboard (all have already been processed)")
            return

    # Process each user and collect email rows
    email_rows: list[OffboardingEmailRow] = []
    for user in exiting_today:
        row = _process_user(user)
        if row:
            email_rows.append(row)

    # Send summary email and mark users as offboarded
    if email_rows:
        try:
            html_body = build_offboarding_email(email_rows)
            bcc = [addr.strip() for addr in settings.offboarding_notification_email_bcc.split(",") if addr.strip()]
            send_email(
                subject=f"Offboarding Summary — {len(email_rows)} Benutzer verarbeitet",
                html_body=html_body,
                to_recipients=[settings.offboarding_notification_email_to],
                bcc_recipients=bcc or None,
                from_address=settings.offboarding_notification_email_from,
            )
            logger.info("Offboarding summary email sent to %s", settings.offboarding_notification_email_to)
            
            # Mark all successfully processed users as offboarded
            for row in email_rows:
                _mark_user_as_offboarded(row.email)
            logger.info("Marked %d users as offboarded in tracking file", len(email_rows))
        except Exception:
            logger.exception("Failed to send summary email")

    logger.info("Offboarding process completed")

