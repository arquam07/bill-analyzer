from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    log_level: str = "INFO"
    app_env: str = "dev"
    # Local storage (dev only)
    storage_root: str = "storage"
    # GCS storage (prod) — set GCS_BUCKET to switch from local disk
    gcs_bucket: str | None = None
    # Comma-separated list of allowed CORS origins
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    vertex_project: str = "bill-analyzer07"
    vertex_location: str = "asia-northeast1"
    vertex_model: str = "gemini-2.5-flash"
    vertex_timeout_seconds: float = 60.0
    google_client_id: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
