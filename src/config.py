# src/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    RATE_LIMIT: str
    ALLOWED_IPS: List[str]
    ALLOWED_ORIGINS: List[str]
    ENVIRONMENT: str


settings = Settings()
