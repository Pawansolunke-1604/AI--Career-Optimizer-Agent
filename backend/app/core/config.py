# TODO: core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Career & Resume Optimizer"
    google_api_key: str
    model_name: str = "gemini-2.5-flash"
    temperature: float = 0.0
    log_level: str = "INFO"
    max_upload_mb: int = 5
    fallback_model_name: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()