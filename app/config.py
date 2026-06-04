"""
Legacy config file - use app.models.config instead for new code
This file is kept for backward compatibility
"""

from app.models.config import get_settings

settings = get_settings()

# Legacy exports
GROQ_API_KEY = settings.GROQ_API_KEY
PIPER_EXE = r"E:\Voice-Agent\piper\piper.exe"
PIPER_MODEL = r"voices\en_US-lessac-medium.onnx"