"""Main onboarding orchestration — replaces the Power Automate web flow.

User provisioning (mailbox, AD attributes, groups, profile folder) is done
on-premise via PowerShell (ad_client). Emails are sent via direct SMTP to
the whitelisted Exchange connector.
"""

import logging
import time

from src.ad_client import provision_user, reconcile_user, set_calendar_permissions, user_exists_in_ad
from src.config import settings
from src.email_builder import EmailRow, build_onboarding_email
from src.smtp_client import send_email
from src.group_resolver import resolve_groups
from src.job_title_resolver import resolve_job_title
from src.loga_client import fetch_new_users
from src.models import OnboardingUser
from src.ou_resolver import resolve_ou

logger = logging.getLogger(__name__)


def _set_calendar_permissions_with_retry(users: list[OnboardingUser]) -> None:
    """Wait for AAD Connect sync, then set calendar permissions with retries.

    New-RemoteMailbox creates the on-prem AD object, but the EXO mailbox only
    exists after AAD Connect syncs the user to Azure AD.  This function waits
    an initial period, then retries with a configurable interval.
    """
    logger.info(
        "Waiting %ds for AAD Connect sync before setting calendar permissions for %d user(s)…",
        settings.aad_sync_wait,
        len(users),
    )
    time.sleep(settings.aad_sync_wait)

    pending = list(users)

    for attempt in range(1, settings.calendar_retry_attempts + 1):
        still_pending: list[OnboardingUser] = []
        for user in pending:
            try:
                set_calendar_permissions(user)
                logger.info("Calendar permissions set for %s", user.abbreviation)
            except RuntimeError:
                logger.info(
                    "Calendar permissions attempt %d/%d failed for %s — will retry",
                    attempt,
                    settings.calendar_retry_attempts,
                    user.abbreviation,
                )
                still_pending.append(user)

        if not still_pending:
            logger.info("All calendar permissions set successfully")
            return

        pending = still_pending
        if attempt < settings.calendar_retry_attempts:
            logger.info(
                "Waiting %ds before retry %d/%d for %d remaining user(s)…",
                settings.calendar_retry_interval,
                attempt + 1,
                settings.calendar_retry_attempts,
                len(pending),
            )
            time.sleep(settings.calendar_retry_interval)

    # Log remaining failures
    for user in pending:
        logger.warning(
            "Calendar permissions could not be set for %s after %d attempts — AAD Connect sync may still be pending",
            user.abbreviation,
            settings.calendar_retry_attempts,
        )


def _process_user(user: OnboardingUser, *, exists: bool) -> EmailRow | None:
    """Process a single user: provision or reconcile on-premise, collect email data.

    If *exists* is True the mailbox creation is skipped and only AD attributes,
    groups and the profile folder are (re-)applied.

    Returns an EmailRow for the summary email, or None if the user was skipped.
    """
    job_title = resolve_job_title(user)
    ou = resolve_ou(user)
    groups = resolve_groups(user, ou)

    # Skip user creation for Reinigungskraft (cleaning staff)
    if not user.is_reinigungskraft:
        try:
            if exists:
                logger.info("Reconciling existing user %s", user.email)
                failed_groups = reconcile_user(
                    user,
                    job_title=job_title,
                    ou=ou,
                    groups=groups,
                )
            else:
                failed_groups = provision_user(
                    user,
                    job_title=job_title,
                    ou=ou,
                    groups=groups,
                )
            if failed_groups:
                logger.warning(
                    "User %s: failed to add to groups: %s",
                    user.email,
                    failed_groups,
                )

        except Exception:
            logger.exception("Failed to provision user %s", user.email)
            # Send error notification
            try:
                send_email(
                    subject=f"Onboarding fehlgeschlagen: {user.email}",
                    html_body=(
                        f"<p>Die automatische Erstellung des Benutzers "
                        f"<strong>{user.full_display_name}</strong> ({user.email}) "
                        f"ist fehlgeschlagen. Bitte manuell prüfen.</p>"
                    ),
                    to_recipients=[addr.strip() for addr in settings.error_notification_email.split(",") if addr.strip()],
                )
            except Exception:
                logger.exception("Failed to send error notification email")

    # Always add the user to the summary email, even Reinigungskraft
    return EmailRow(
        begin=user.begin_date,
        full_name=user.full_display_name,
        email=user.email,
        abbreviation=user.abbreviation,
        phone=user.phone,
        room=user.room,
        team=user.team,
        job_title_resolved=job_title,
        birth_date=user.birth_date,
        kostenstelle=user.kostenstelle,
        berufstraeger=user.berufstraeger,
        stundensatz=user.stundensatz,
        fte=user.umf_besetz,
    )


def run_onboarding() -> None:
    """Execute the full onboarding flow.

    1. Fetch new users from LOGA HR system
    2. For each user not yet in Entra ID:
       a. Determine job title, OU, and groups
       b. Create mailbox + AD account on-premise (skip Reinigungskraft)
       c. Set AD attributes and manager
       d. Add user to AD groups + team group
       e. Create profile folder with ACLs
       f. Collect data for summary email
    3. Send summary email if any users were processed
    """
    logger.info("=== Starting onboarding run ===")

    if settings.dry_run:
        logger.info("*** DRY RUN MODE — no changes will be made ***")

    # Step 1: Fetch users from LOGA
    users = fetch_new_users()
    if not users:
        logger.info("No new users found. Exiting.")
        return

    email_rows: list[EmailRow] = []
    newly_provisioned: list[OnboardingUser] = []

    # Step 2: Process each user
    for user in users:
        if not user.email:
            logger.warning("Skipping user with PNR %s — no email", user.pnr)
            continue

        # Check if user already exists in AD
        exists = user_exists_in_ad(user.abbreviation)
        if exists:
            if settings.reconcile_existing:
                logger.info("User %s already exists in AD — reconcile flag is set, will update attributes", user.abbreviation)
            else:
                logger.info("User %s already exists in AD — skipping (set RECONCILE_EXISTING=true to update)", user.abbreviation)
                continue

        row = _process_user(user, exists=exists)
        if row:
            email_rows.append(row)
            if not exists and not user.is_reinigungskraft:
                newly_provisioned.append(user)

    # Step 3: Set calendar permissions for newly provisioned users
    if newly_provisioned and not settings.dry_run:
        _set_calendar_permissions_with_retry(newly_provisioned)

    # Step 4: Send summary email
    if email_rows:
        html_body = build_onboarding_email(email_rows)
        bcc = [addr.strip() for addr in settings.onboarding_notification_email_bcc.split(",") if addr.strip()]
        try:
            send_email(
                subject="Onboarding",
                html_body=html_body,
                to_recipients=[settings.onboarding_notification_email_to],
                from_address=settings.onboarding_notification_email_from,
                bcc_recipients=bcc or None,
            )
            logger.info("Summary email sent for %d user(s)", len(email_rows))
        except Exception:
            logger.exception("Failed to send onboarding summary email")
    else:
        logger.info("No new users to onboard — no summary email sent")

    logger.info("=== Onboarding run complete ===")
