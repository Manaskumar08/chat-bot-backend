"""
Models package for Voice Agent Application
Centralized models, schemas, and configurations
"""

# Database Models
from app.models.database import (
    Base,
    User,
    Conversation,
    Message
)

# Schemas (Pydantic)
from app.models.schemas import (
    UserRegister,
    UserLogin,
    TokenResponse,
    UserResponse,
    ConversationResponse,
    MessageResponse
)

# Configuration
from app.models.config import (
    Settings,
    DATABASE_CONFIG,
    get_settings
)

# Database Session
from app.models.session import (
    engine,
    SessionLocal,
    get_db
)

# Auth Models
from app.models.auth import (
    TokenData,
    TOKEN_EXPIRE_MINUTES
)

__all__ = [
    # Database Models
    "Base",
    "User",
    "Conversation",
    "Message",
    # Schemas
    "UserRegister",
    "UserLogin",
    "TokenResponse",
    "UserResponse",
    "ConversationResponse",
    "MessageResponse",
    # Configuration
    "Settings",
    "DATABASE_CONFIG",
    "get_settings",
    # Session
    "engine",
    "SessionLocal",
    "get_db",
    # Auth
    "TokenData",
    "TOKEN_EXPIRE_MINUTES"
]
