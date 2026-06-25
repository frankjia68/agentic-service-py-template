from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ASPT_")

    http_host: str = "0.0.0.0"
    http_port: int = 8000
    db_connection_string: str = "sqlite+aiosqlite:///./agentic_service_py_template.db"
    db_readonly_connection_string: str | None = None
    llm_endpoint: str = "https://models.inference.ai.azure.com"
    llm_api_version: str = "2024-12-01"
    llm_model: str = "gpt-4o-mini"
    llm_api_key: SecretStr | None = None
    auth_jwt_secret: str = "dev-secret-change-in-prod"
    auth_jwt_algorithm: str = "HS256"
    api_key: str | None = None
    default_account_id: str = "1"
    default_user_id: str = "100"
