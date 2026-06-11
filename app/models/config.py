"""
Configuration Management
Environment variables and settings for Voice Agent application
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

import os
from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def _parse_bool(value, default: bool) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on", "debug"}:
            return True
        if normalized in {"0", "false", "no", "n", "off", "release", "prod", "production"}:
            return False
        return default

    return bool(value)


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Application
    APP_NAME: str = "Voice Agent API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:Manas%40801@localhost:5432/voice_agent"
    )
    DB_ECHO: bool = False
    
    # JWT & Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Groq API
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")

    # Gemini API
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Piper TTS
    PIPER_EXE: str = os.getenv("PIPER_EXE", str(BASE_DIR.parent / "piper" / "piper.exe"))
    PIPER_MODEL: str = os.getenv("PIPER_MODEL", str(BASE_DIR / "voices" / "en_US-lessac-medium.onnx"))
    
    # Faster Whisper STT
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    
    # CORS
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]
    
    # Paths
    UPLOADS_DIR: str = os.getenv("UPLOADS_DIR", "uploads")
    TEMP_DIR: str = os.getenv("TEMP_DIR", "temp")
    GENERATED_AUDIO_DIR: str = os.getenv("GENERATED_AUDIO_DIR", "generated_audio")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        return _parse_bool(value, default=True)

    @field_validator("DB_ECHO", mode="before")
    @classmethod
    def parse_db_echo(cls, value):
        return _parse_bool(value, default=False)


# Database configuration dictionary
DATABASE_CONFIG = {
    "url": Settings().DATABASE_URL,
    "echo": Settings().DB_ECHO,
    "pool_size": 20,
    "max_overflow": 0,
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    
    Returns:
        Settings: Application settings
    """
    return Settings()
