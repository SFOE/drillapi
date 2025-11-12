# src/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    RATE_LIMIT: str = "1000/minute"
    ALLOWED_IPS: List[str] = ["127.0.0.1"]
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]
    ENVIRONMENT: str = "production"


settings = Settings()
