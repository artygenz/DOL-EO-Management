from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # Database settings
    postgres_host: str = "db"
    postgres_port: str = "5432"
    postgres_user: str = "dol_user"
    postgres_password: str = "artygenz"
    postgres_db: str = "dol_db"
    
    # Redis settings
    redis_host: str = "redis"
    redis_port: str = "6379"
    
    # OpenAI settings
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1"
    
    # App settings
    app_env: str = "local"
    secret_key: str = "your-secret-key-change-in-production"
    
    @property
    def SQLALCHEMY_SYNC_URL(self) -> str:
        return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def SQLALCHEMY_ASYNC_URL(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"
    
    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.REDIS_URL
    
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self.REDIS_URL

    class Config:
        case_sensitive = False

settings = Settings()
