from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    log_level: str = "INFO"
    app_env: str = "dev"
    storage_root: str = "storage"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "glm-ocr"
    ollama_timeout_seconds: float = 60.0
    ollama_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
