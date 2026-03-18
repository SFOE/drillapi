from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    TEMPLATES_DIR: Path = BASE_DIR / "drillapi/templates"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    RATE_LIMIT: str = "1000/minute"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]
    ENVIRONMENT: str = "production"


settings = Settings()
