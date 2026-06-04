"""
Database Base
Backward compatibility module - use app.models.database instead
"""

from app.models.database import Base

__all__ = ["Base"]
