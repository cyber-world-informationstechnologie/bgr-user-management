from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LOGA API
    loga_api_url: str = "https://BGR.pi-asp.de/loga3/scout/api/v1/executeScoutReportJobAndGetFile"
    loga_job_file_content: str = ""

    # Microsoft Entra ID (Azure AD)
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""

    # Email
    notification_email_to: str = "markus.hinkel@cwi.at"
    notification_email_from: str = "onboarding@bgr.at"
    error_notification_email: str = "markus.hinkel@cwi.at"

    # On-premise AD / Exchange
    profile_base_path: str = r"\\bgr\dfs\Profile"
    default_password: str = "Onboarding13IT!"

    # Dry run
    dry_run: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
