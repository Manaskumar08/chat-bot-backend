"""
Legacy config file - use app.models.config instead for new code
This file is kept for backward compatibility
"""

from pathlib import Path
from app.models.config import get_settings

settings = get_settings()
BASE_DIR = Path(__file__).resolve().parent.parent

# Legacy exports
GROQ_API_KEY = settings.GROQ_API_KEY
PIPER_EXE = str(BASE_DIR.parent / "piper" / "piper.exe")
PIPER_MODEL = str(BASE_DIR / "voices" / "en_US-lessac-medium.onnx")