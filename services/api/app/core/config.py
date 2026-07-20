from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    app_cors_origins: str = "http://localhost:3000"
    repository_workspace_ttl_seconds: int = Field(default=3600, gt=0)
    repository_max_download_bytes: int = Field(default=50 * 1024 * 1024, gt=0)
    repository_max_expanded_bytes: int = Field(default=100 * 1024 * 1024, gt=0)
    repository_max_files: int = Field(default=5000, gt=0)
    repository_clone_timeout_seconds: int = Field(default=120, gt=0)
    repository_max_source_file_bytes: int = Field(default=512 * 1024, gt=0)
    repository_temp_root: str | None = None
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5.6-sol"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.app_cors_origins.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
