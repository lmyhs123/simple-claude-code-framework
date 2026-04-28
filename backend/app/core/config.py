from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Simple Claude Code Framework"
    database_url: str = "sqlite:///./data/app.db"
    upload_dir: str = "./uploads"
    model_provider: str = "mock"
    model_api_key: str = ""
    model_base_url: str = ""
    model_name: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def upload_path(self) -> Path:
        return Path(self.upload_dir)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
