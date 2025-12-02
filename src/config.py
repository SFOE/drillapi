# src/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    RATE_LIMIT: str
    ALLOWED_IPS: List[str]
    ALLOWED_ORIGINS: List[str]
    ENVIRONMENT: str


# Define test variables here
class SettingsTest(BaseSettings):
    RATE_LIMIT: str = "1000/minute"
    ALLOWED_IPS: List[str] = ["0.0.0.0"]
    ALLOWED_ORIGINS: List[str] = ["0.0.0.0"]
    ENVIRONMENT: str = "TEST"


settings = Settings()
