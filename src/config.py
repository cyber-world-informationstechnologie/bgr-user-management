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

    # ========== Error Notifications ==========
    error_notification_email: str = "markus.hinkel@cwi.at"

    # ========== Offboarding Configuration ==========
    offboarding_absence_notice: str = (
        "Diese Person ist nicht mehr bei unserem Unternehmen tätig. "
        "Bitte kontaktieren Sie uns bei Fragen."
    )
    offboarding_disabled_users_ou: str = "OU=Disabled Users,DC=bgr,DC=at"
    # ========== Active Directory & Profile Folder ==========
    profile_base_path: str = r"\\bgr\dfs\Profile"
    default_password: str = "Onboarding13IT!"
    remote_routing_domain: str = "bindergroesswang-at.mail.onmicrosoft.com"

    # ========== Behavior Flags ==========
    dry_run: bool = True
    reconcile_existing: bool = False  # Re-apply AD attributes for users that already exist


settings = Settings()