"""
Database Models
Backward compatibility module - use app.models.database instead
"""

from app.models.database import (
    Base,
    User,
    Conversation,
    Message
)

__all__ = [
    "Base",
    "User",
    "Conversation",
    "Message"
]