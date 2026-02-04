import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # ===============================
    # WhatsApp API Configuration
    # ===============================
    WHATSAPP_TOKEN: str = os.getenv("WHATSAPP_TOKEN", "your_whatsapp_access_token")
    VERIFY_TOKEN: str = os.getenv("VERIFY_TOKEN", "your_verification_token")
    PHONE_NUMBER_ID: str = os.getenv("PHONE_NUMBER_ID", "your_phone_number_id")

    # ===============================
    # Database Configuration
    # ===============================
    # Defaults work locally; Render/Railway override via env vars
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 3306))
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")
    DB_NAME: str = os.getenv("DB_NAME", "vmc_chatbot")

    # ===============================
    # App Configuration
    # ===============================
    PORT: int = int(os.getenv("PORT", 8000))
    DEBUG: bool = os.getenv("DEBUG", "True") == "True"

    # ===============================
    # File Storage
    # ===============================
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    PDF_DIR: str = os.getenv("PDF_DIR", "pdfs")

    # ===============================
    # CORS Configuration
    # ===============================
    FRONTEND_URL: str = os.getenv(
        "FRONTEND_URL",
        "https://vmcbot.netlify.app"
    )

    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,"
        "http://localhost:3001,"
        "http://127.0.0.1:3000,"
        "http://127.0.0.1:3001,"
        "https://vmcbot.netlify.app"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()


def get_settings() -> Settings:
    """Get settings instance"""
    return settings
