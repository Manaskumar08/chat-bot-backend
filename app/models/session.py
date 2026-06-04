"""
Database Session Management
SQLAlchemy engine and session configuration
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from app.models.config import get_settings, DATABASE_CONFIG
from app.models.database import Base

# Get settings
settings = get_settings()

# Create database engine
engine = create_engine(
    DATABASE_CONFIG["url"],
    echo=DATABASE_CONFIG["echo"],
    poolclass=QueuePool,
    pool_size=DATABASE_CONFIG["pool_size"],
    max_overflow=DATABASE_CONFIG["max_overflow"],
    pool_pre_ping=DATABASE_CONFIG["pool_pre_ping"],
    pool_recycle=DATABASE_CONFIG["pool_recycle"],
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


def create_all_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def drop_all_tables():
    """Drop all database tables (use with caution)"""
    Base.metadata.drop_all(bind=engine)


def get_db() -> Session:
    """
    Dependency for getting database session
    Usage in FastAPI routes:
        @app.get("/")
        def my_route(db: Session = Depends(get_db)):
            pass
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
