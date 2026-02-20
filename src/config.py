from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LOGA API
    loga_api_url: str = "https://BGR.pi-asp.de/loga3/scout/api/v1/executeScoutReportJobAndGetFile"
    loga_job_file_content: str = ""  # For onboarding (new users)
    loga_offboarding_job_file_content: str = ""  # For offboarding (exiting users)

    # SMTP (whitelisted connector, no auth)
    smtp_host: str = "bindergroesswang-at.mail.protection.outlook.com"
    smtp_port: int = 25

    # Email
    notification_email_to: str = "markus.hinkel@cwi.at"
    notification_email_bcc: str = ""
    notification_email_from: str = "onboarding@bgr.at"
    error_notification_email: str = "markus.hinkel@cwi.at"
    offboarding_email_from: str = "offboarding@bgr.at"

    # Offboarding
    offboarding_absence_notice: str = (
        "Diese Person ist nicht mehr bei unserem Unternehmen tätig. "
        "Bitte kontaktieren Sie uns bei Fragen."
    )
    disabled_users_ou: str = "OU=Disabled Users,DC=bgr,DC=at"
