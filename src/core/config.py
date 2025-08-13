from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SQLALCHEMY_SYNC_URL: str
    SQLALCHEMY_ASYNC_URL: str
    APP_ENV: str = "local"

    class Config:
        env_file = ".env"

settings = Settings()
