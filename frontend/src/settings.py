from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class _Settings(BaseSettings):
    """Frontend application settings loaded from environment variables or .env.

    Attributes:
        api_base_url: The base URL of the FastAPI backend.
        api_timeout: Request timeout in seconds for backend calls.
        app_title: The display title shown in the Streamlit page header.
    """

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    api_base_url: str = "http://localhost:8000"
    api_timeout: float = 60.0
    app_title: str = "Dividend History Tracker"


@lru_cache
def get_settings() -> _Settings:
    """Return the cached application settings singleton.

    Returns:
        _Settings: The frontend settings instance.
    """
    return _Settings()  # ty: ignore[missing-argument, unused-ignore-comment]
