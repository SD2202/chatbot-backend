import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # WhatsApp API Configuration
    WHATSAPP_TOKEN: str = "your_whatsapp_access_token"
    VERIFY_TOKEN: str = "your_verification_token"
    PHONE_NUMBER_ID: str = "your_phone_number_id"
    
    # MariaDB Configuration
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "vmc_chatbot"
    
    # App Configuration
    PORT: int = 8000
    DEBUG: bool = True
    
    # File Storage
    UPLOAD_DIR: str = "uploads"
    PDF_DIR: str = "pdfs"
    
    # CORS Configuration
    FRONTEND_URL: str = "http://localhost:3000"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

def get_settings() -> Settings:
    """Get settings instance"""
    return settings
