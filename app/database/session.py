"""
Database Session
Backward compatibility module - use app.models.session instead
"""

from app.models.session import (
    engine,
    SessionLocal,
    create_all_tables,
    drop_all_tables,
    get_db
)

__all__ = [
    "engine",
    "SessionLocal",
    "create_all_tables",
    "drop_all_tables",
    "get_db"
]