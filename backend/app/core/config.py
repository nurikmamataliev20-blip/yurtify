from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ADMIN_EMAILS: str = ""
    UPLOADS_DIR: str = "uploads"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    RESET_TOKEN_EXPIRE_HOURS: int = 2

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

settings = Settings()

BACKEND_DIR = Path(__file__).resolve().parents[2]
UPLOADS_DIR = Path(settings.UPLOADS_DIR)
if not UPLOADS_DIR.is_absolute():
    UPLOADS_DIR = BACKEND_DIR / UPLOADS_DIR
