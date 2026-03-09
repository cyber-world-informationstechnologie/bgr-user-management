from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ========== LOGA HR System ==========
    loga_api_url: str = "https://BGR.pi-asp.de/loga3/scout/api/v1/executeScoutReportJobAndGetFile"
    loga_onboarding_job_file_content: str = ""  # Onboarding report (new users)
    loga_offboarding_job_file_content: str = ""  # Offboarding report (exiting users)

    # ========== SMTP ==========
    smtp_host: str = "bindergroesswang-at.mail.protection.outlook.com"
    smtp_port: int = 25

    # ========== Onboarding Email Notifications ==========
    onboarding_notification_email_to: str = "markus.hinkel@cwi.at"
    onboarding_notification_email_bcc: str = ""
    onboarding_notification_email_from: str = "onboarding@bgr.at"

    # ========== Offboarding Email Notifications ==========
    offboarding_notification_email_to: str = "markus.hinkel@cwi.at"
    offboarding_notification_email_bcc: str = ""
    offboarding_notification_email_from: str = "offboarding@bgr.at"

    # ========== Error Notifications (comma-separated for multiple recipients) ==========
    error_notification_email: str = "markus.hinkel@cwi.at"

    # ========== Offboarding Configuration ==========
    offboarding_absence_notice: str = (
        "Diese Person ist nicht mehr bei unserem Unternehmen tätig. "
        "Bitte kontaktieren Sie uns bei Fragen."
    )
    offboarding_disabled_users_ou: str = "OU=Disabled Users,DC=bgr,DC=at"
    # ========== Exchange Online (certificate-based auth) ==========
    exo_app_id: str = ""  # Azure AD App Registration Client ID
    exo_org: str = "bindergroesswang.at"  # Exchange Online organization domain
    exo_certificate_thumbprint: str = ""  # Certificate thumbprint (LocalMachine\My)

    # ========== Active Directory & Profile Folder ==========
    profile_base_path: str = r"\\bgr\dfs\Profile"
    default_password: str = "Onboarding13IT!"
    remote_routing_domain: str = "bindergroesswang-at.mail.onmicrosoft.com"

    # ========== AAD Connect Sync / Calendar Permissions ==========
    aad_sync_wait: int = 300  # Seconds to wait for AAD Connect sync before setting calendar perms
    calendar_retry_attempts: int = 6  # Number of retry attempts for calendar permissions
    calendar_retry_interval: int = 300  # Seconds between retries

    # ========== Behavior Flags ==========
    dry_run: bool = True
    reconcile_existing: bool = False  # Re-apply AD attributes for users that already exist


settings = Settings()