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

# Files to track offboarding progress
NOTIFICATION_SENT_FILE = Path("logs") / "offboarding_notifications_sent.json"
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


def _load_notifications_sent() -> dict:
    """Load users who have already received notification emails (exit_date = today)."""
    if not NOTIFICATION_SENT_FILE.exists():
        return {}
    try:
        with open(NOTIFICATION_SENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning("Could not load notifications sent file: %s", e)
        return {}


def _save_notifications_sent(users: dict) -> None:
    """Save users who have received notification emails."""
    NOTIFICATION_SENT_FILE.parent.mkdir(exist_ok=True)
    try:
        with open(NOTIFICATION_SENT_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
    except IOError as e:
        logger.error("Could not save notifications sent file: %s", e)


def _load_offboarded_users() -> dict:
    """Load the set of users who have completed offboarding operations (exit_date = yesterday).
    
    Returns a dict mapping email -> timestamp of when offboarding was completed.
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
    """Save the set of users who have completed offboarding operations."""
    OFFBOARDED_USERS_FILE.parent.mkdir(exist_ok=True)
    try:
        with open(OFFBOARDED_USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
    except IOError as e:
        logger.error("Could not save offboarded users file: %s", e)


def _mark_notification_sent(email: str) -> None:
    """Record that a notification email was sent for this user."""
    users = _load_notifications_sent()
    users[email] = datetime.now().isoformat()
    _save_notifications_sent(users)


def _has_notification_been_sent(email: str) -> bool:
    """Check if a notification email has already been sent for this user."""
    return email in _load_notifications_sent()


def _mark_user_as_offboarded(email: str) -> None:
    """Record that offboarding operations were completed for this user."""
    users = _load_offboarded_users()
    users[email] = datetime.now().isoformat()
    _save_offboarded_users(users)


def _has_offboarding_been_completed(email: str) -> bool:
    """Check if offboarding operations have been completed for this user."""
    return email in _load_offboarded_users()


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
            end_date=user.end_date,
            full_name=user.full_display_name,
            email=user.email,
            abbreviation=user.abbreviation,
            phone=user.phone,
            room=user.room,
            team=user.team,
            birth_date=user.birth_date,
            kostenstelle=user.kostenstelle,
            berufstraeger=user.berufstraeger,
            fte=user.umf_besetz,
            kommentar=user.kommentar,
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
    """Execute the full offboarding flow in two phases.

    **Phase 1:** Send notification email
    - Fetch ALL exiting users from LOGA API
    - Find any new users not yet notified
    - Send ONE email to recipient with all new users
    - Tracked to send only once (unless --resend is used)
    
    **Phase 2:** Execute offboarding operations
    - Fetch exiting users whose exit_date was YESTERDAY
    - Convert Exchange mailbox to shared mailbox
    - Set auto-reply / out-of-office notice
    - Set up mail forwarding to manager
    - Remove from all email distribution groups
    - Disable AD account and move to 'Disabled Users' OU
    - Remove group memberships
    
    Args:
        resend: If True, resend notifications/operations even if already completed
    """
    logger.info("Starting offboarding process…")
    if resend:
        logger.info("RESEND MODE: Will re-process users")

    users = fetch_exiting_users()
    logger.info("Fetched %d users from LOGA API", len(users))

    # Phase 1: Send notification email for any new users found
    _send_notification_on_new_users(users, resend)

    # Phase 2: Execute offboarding operations for users exiting yesterday
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")
    offboarding_users = [u for u in users if u.exit_date == yesterday]
    
    if offboarding_users:
        logger.info("Phase 2: Executing offboarding for %d users with exit_date = %s", len(offboarding_users), yesterday)
        _execute_offboarding_operations(offboarding_users, resend)
    else:
        logger.info("Phase 2: No users to offboard today (looking for exit_date=%s)", yesterday)

    logger.info("Offboarding process completed")


def _send_notification_on_new_users(users: list[OffboardingUser], resend: bool = False) -> None:
    """Phase 1: Send notification email to offboarding team when new users appear in P&I report.
    
    Sends ONE email to the OFFBOARDING TEAM with all newly detected users.
    (Does NOT notify the users themselves - only the team.)
    
    Args:
        users: List of all users from LOGA API
        resend: If True, resend even if already notified to team
    """
    # Filter out users who have already been included in a team notification (unless resend=True)
    if not resend:
        new_users = [u for u in users if not _has_notification_been_sent(u.email)]
        already_notified_to_team = [u for u in users if _has_notification_been_sent(u.email)]
        
        if already_notified_to_team:
            logger.info(
                "Skipping %d users already included in team notification: %s",
                len(already_notified_to_team),
                ", ".join(u.email for u in already_notified_to_team),
            )
    else:
        new_users = users
        logger.info("RESEND: Notifying offboarding team about all %d users", len(users))
    
    if not new_users:
        logger.info("Phase 1: No new users to report to offboarding team")
        return

    # Build a single email with all new users for the offboarding team
    logger.info("Phase 1: Sending notification email to offboarding team for %d new users", len(new_users))
    
    try:
        email_rows: list[OffboardingEmailRow] = []
        for user in new_users:
            row = OffboardingEmailRow(
                exit_date=user.exit_date,
                end_date=user.end_date,
                full_name=user.full_display_name,
                email=user.email,
                abbreviation=user.abbreviation,
                phone=user.phone,
                room=user.room,
                team=user.team,
                birth_date=user.birth_date,
                kostenstelle=user.kostenstelle,
                berufstraeger=user.berufstraeger,
                fte=user.umf_besetz,
                kommentar=user.kommentar,
            )
            email_rows.append(row)

        html_body = build_offboarding_email(email_rows)
        bcc = [addr.strip() for addr in settings.offboarding_notification_email_bcc.split(",") if addr.strip()]
        send_email(
            subject=f"Austrittsmitteilung — {len(new_users)} Benutzer erkannt",
            html_body=html_body,
            to_recipients=[settings.offboarding_notification_email_to],
            bcc_recipients=bcc or None,
            from_address=settings.offboarding_notification_email_from,
        )
        logger.info("Notification email sent to offboarding team (%s) for %d users", settings.offboarding_notification_email_to, len(new_users))
        
        # Mark all users as included in a team notification
        for user in new_users:
            _mark_notification_sent(user.email)
        logger.info("Marked %d users as included in team notification", len(new_users))
    except Exception:
        logger.exception("Failed to send notification email to offboarding team")


def _execute_offboarding_operations(users: list[OffboardingUser], resend: bool = False) -> None:
    """Phase 2: Execute offboarding operations the day after exit_date.
    
    Args:
        users: List of users with exit_date = yesterday
        resend: If True, re-execute even if already completed
    """
    # Filter out users who have already completed offboarding (unless resend=True)
    if not resend:
        already_offboarded = [u for u in users if _has_offboarding_been_completed(u.email)]
        if already_offboarded:
            logger.info(
                "Skipping %d users who have already been offboarded: %s",
                len(already_offboarded),
                ", ".join(u.email for u in already_offboarded),
            )
        users = [u for u in users if not _has_offboarding_been_completed(u.email)]
        
        if not users:
            logger.info("Phase 2: No new users to offboard")
            return

    # Process each user and collect results
    email_rows: list[OffboardingEmailRow] = []
    for user in users:
        row = _process_user(user)
        if row:
            email_rows.append(row)

    # Send summary email with operations completed
    if email_rows:
        try:
            html_body = build_offboarding_email(email_rows)
            bcc = [addr.strip() for addr in settings.offboarding_notification_email_bcc.split(",") if addr.strip()]
            send_email(
                subject=f"Offboarding abgeschlossen — {len(email_rows)} Benutzer verarbeitet",
                html_body=html_body,
                to_recipients=[settings.offboarding_notification_email_to],
                bcc_recipients=bcc or None,
                from_address=settings.offboarding_notification_email_from,
            )
            logger.info("Offboarding summary email sent to %s", settings.offboarding_notification_email_to)
            
            # Mark all successfully processed users as offboarded
            for row in email_rows:
                _mark_user_as_offboarded(row.email)
            logger.info("Marked %d users as offboarded", len(email_rows))
        except Exception:
            logger.exception("Failed to send summary email")