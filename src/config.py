from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LOGA API
    loga_api_url: str = "https://BGR.pi-asp.de/loga3/scout/api/v1/executeScoutReportJobAndGetFile"
    loga_job_file_content: str = ""

    # SMTP (whitelisted connector, no auth)
    smtp_host: str = "bindergroesswang-at.mail.protection.outlook.com"
    smtp_port: int = 25

    # Email
    notification_email_to: str = "markus.hinkel@cwi.at"
    notification_email_bcc: str = ""
    notification_email_from: str = "onboarding@bgr.at"
    error_notification_email: str = "markus.hinkel@cwi.at"

    # On-premise AD / Exchange
    profile_base_path: str = r"\\bgr\dfs\Profile"
    default_password: str = "Onboarding13IT!"
    remote_routing_domain: str = "bindergroesswang-at.mail.onmicrosoft.com"

    # Dry run
    dry_run: bool = True


settings = Settings()
