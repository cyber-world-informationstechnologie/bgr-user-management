"""Main onboarding orchestration — replaces the Power Automate web flow.

User provisioning (mailbox, AD attributes, groups, profile folder) is done
on-premise via PowerShell (ad_client). Emails are sent via direct SMTP to
the whitelisted Exchange connector.
"""

import logging

from src.ad_client import provision_user, reconcile_user, user_exists_in_ad
from src.config import settings
from src.email_builder import EmailRow, build_onboarding_email
from src.smtp_client import send_email
from src.group_resolver import resolve_groups
from src.job_title_resolver import resolve_job_title
from src.loga_client import fetch_new_users
from src.models import OnboardingUser
from src.ou_resolver import resolve_ou

logger = logging.getLogger(__name__)


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
                    to_recipients=[settings.error_notification_email],
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

    # Step 2: Process each user
    for user in users:
        if not user.email:
            logger.warning("Skipping user with PNR %s — no email", user.pnr)
            continue

        # Check if user already exists in AD
        exists = user_exists_in_ad(user.abbreviation)
        if exists:
            logger.info("User %s already exists in AD — will reconcile attributes", user.abbreviation)

        row = _process_user(user, exists=exists)
        if row:
            email_rows.append(row)

    # Step 3: Send summary email
    if email_rows:
        html_body = build_onboarding_email(email_rows)
        bcc = [addr.strip() for addr in settings.notification_email_bcc.split(",") if addr.strip()]
        try:
            send_email(
                subject="Onboarding",
                html_body=html_body,
                to_recipients=[settings.notification_email_to],
                from_address=settings.notification_email_from,
                bcc_recipients=bcc or None,
            )
            logger.info("Summary email sent for %d user(s)", len(email_rows))
        except Exception:
            logger.exception("Failed to send onboarding summary email")
    else:
        logger.info("No new users to onboard — no summary email sent")

    logger.info("=== Onboarding run complete ===")
