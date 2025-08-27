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
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "dol_db"
    POSTGRES_USER: str = "dol_user"
    POSTGRES_PASSWORD: str = "artygenz"

    # --- Redis settings ---
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # --- OpenAI settings ---
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4.1"

    # --- Optional app settings (keep if you need them; they won't break Alembic) ---
    APP_ENV: str = "local"
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALG: str = "HS256"

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
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @computed_field
    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.REDIS_URL

    @computed_field
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self.REDIS_URL

settings = Settings()