from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class _Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_debug: bool = True
    db_url: str = "sqlite+aiosqlite:///div-history.db"


@lru_cache
def get_settings() -> _Settings:
    return _Settings()  # ty: ignore[missing-argument, unused-ignore-comment]
