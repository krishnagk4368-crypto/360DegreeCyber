from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)
    DATABASE_URL: str = "postgresql://cyber:cyberpass@localhost:5432/cyber360"
    JWT_SECRET: str = "change-me"
    JWT_ALG: str = "HS256"
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]
    # Dev helpers
    SKIP_AUTH: bool = False
    DEV_ASSUME_TESTER_ID: int | None = None

settings = Settings()
