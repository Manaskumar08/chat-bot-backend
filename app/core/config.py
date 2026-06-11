"""
Canonical application configuration.

This module re-exports the existing settings so new code can depend on a single
config path while legacy modules continue to work.
"""

from app.models.config import DATABASE_CONFIG, Settings, get_settings

settings = get_settings()

APP_NAME = settings.APP_NAME
APP_VERSION = settings.APP_VERSION
DEBUG = settings.DEBUG
DATABASE_URL = settings.DATABASE_URL
DB_ECHO = settings.DB_ECHO
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
GROQ_API_KEY = settings.GROQ_API_KEY
GROQ_MODEL = settings.GROQ_MODEL
PIPER_EXE = settings.PIPER_EXE
PIPER_MODEL = settings.PIPER_MODEL
WHISPER_MODEL = settings.WHISPER_MODEL
UPLOADS_DIR = settings.UPLOADS_DIR
TEMP_DIR = settings.TEMP_DIR
GENERATED_AUDIO_DIR = settings.GENERATED_AUDIO_DIR
CORS_ORIGINS = settings.CORS_ORIGINS

