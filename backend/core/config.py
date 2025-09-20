# backend/core/config.py
from pydantic import BaseSettings, Field, AnyUrl
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Automated OMR Evaluation System"
    DEBUG: bool = True

    # DB (MySQL)
    # Example: mysql+pymysql://user:password@localhost:3306/omr_db
    SQLALCHEMY_DATABASE_URL: str = Field(
        "mysql+pymysql://omr_user:omr_pass@localhost:3306/omr_db",
        env="DATABASE_URL",
    )

    # File storage
    BASE_DIR: Path = Path(__file__).resolve().parents[2]
    UPLOAD_DIR: Path = Field(default=BASE_DIR / "data" / "omr_samples")
    PROCESSED_DIR: Path = Field(default=BASE_DIR / "data" / "processed")
    OVERLAY_DIR: Path = Field(default=BASE_DIR / "data" / "overlays")
    ANSWER_KEYS_DIR: Path = Field(default=BASE_DIR / "data" / "answer_keys")
    RESULTS_EXPORT_DIR: Path = Field(default=BASE_DIR / "data" / "results_exports")

    # Security - JWT
    JWT_SECRET_KEY: str = Field("change-me-to-a-random-secret", env="JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day by default

    # Misc
    MAX_UPLOAD_SIZE_MB: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure directories exist
for p in (
    settings.UPLOAD_DIR,
    settings.PROCESSED_DIR,
    settings.OVERLAY_DIR,
    settings.ANSWER_KEYS_DIR,
    settings.RESULTS_EXPORT_DIR,
):
    p.mkdir(parents=True, exist_ok=True)
