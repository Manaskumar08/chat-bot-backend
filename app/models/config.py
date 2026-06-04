"""
Configuration Management
Environment variables and settings for Voice Agent application
"""

from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Application
    APP_NAME: str = "Voice Agent API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:Manas%40801@localhost:5432/voice_agent"
    )
    DB_ECHO: bool = os.getenv("DB_ECHO", "False").lower() == "true"
    
    # JWT & Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Groq API
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
    
    # Piper TTS
    PIPER_EXE: str = os.getenv("PIPER_EXE", r"C:\piper\piper.exe")
    PIPER_MODEL: str = os.getenv("PIPER_MODEL", r"C:\piper\models\en_US-lessac-medium.onnx")
    
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
