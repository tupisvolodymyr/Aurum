from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore": the same .env also carries POSTGRES_* vars that only
    # docker-compose interpolates (for the db service) — the app itself has
    # no use for them beyond the DATABASE_URL compose already assembles.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AURUM"
    environment: str = "development"
    debug: bool = True

    secret_key: str
    database_url: str = "sqlite+aiosqlite:///./casino.db"

    session_cookie_name: str = "session_id"
    session_ttl_seconds: int = 60 * 60 * 24 * 14  # 14 days
    csrf_cookie_name: str = "csrf_token"

    starting_balance: int = 1000  # virtual ₴ granted on signup

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
