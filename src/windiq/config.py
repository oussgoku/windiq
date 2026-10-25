from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    windiq_api_base_url: str = "https://api.example.invalid"
    windiq_client_id: SecretStr | None = None
    windiq_client_secret: SecretStr | None = None
    ingest_interval_seconds: int = Field(default=3600, ge=60)
    ingest_stale_after_seconds: int = Field(default=9000, ge=60)


@lru_cache
def get_settings() -> Settings:
    return Settings()
