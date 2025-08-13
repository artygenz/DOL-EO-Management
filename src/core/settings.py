# src/core/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

class Settings(BaseSettings):
    # Accept unknown keys and case-insensitive env var names to avoid ValidationError
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Required DB basics (portable to cloud later) ---
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "appdb"
    POSTGRES_USER: str = "app"
    POSTGRES_PASSWORD: str = "secret"

    # --- Optional app settings (keep if you need them; they won't break Alembic) ---
    APP_ENV: str = "local"
    JWT_SECRET: str | None = None
    JWT_ALG: str = "RS256"

    # Computed URLs (do NOT put these in .env)
    @computed_field
    @property
    def SQLALCHEMY_ASYNC_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def SQLALCHEMY_SYNC_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

settings = Settings()