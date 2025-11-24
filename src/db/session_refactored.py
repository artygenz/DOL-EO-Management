# src/db/session.py - REFACTORED VERSION
"""
Refactored database session management using centralized client hub.

This file demonstrates how to migrate from direct environment variable access
to using the centralized client hub for better debugging and management.
"""

from sqlalchemy.orm import sessionmaker
from src.core.client_hub import get_database_engine, get_database_session_maker

# Get engine and session maker from centralized client hub
_engine = get_database_engine()
_SessionLocal = get_database_session_maker()

def get_engine():
    """Return the global engine (used by Alembic, repositories, etc.)."""
    return _engine

def get_session_maker(engine=None):
    """Return a sessionmaker bound to the given engine (or the global one)."""
    if engine is None:
        return _SessionLocal
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Optional convenience if you like to import directly:
SessionLocal = _SessionLocal

def get_db():
    """Get database session generator for FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# MIGRATION NOTES:
# ================
# 
# OLD CODE REMOVED:
# - import os
# - DATABASE_URL = os.getenv("DATABASE_URL")
# - if not DATABASE_URL: raise RuntimeError("DATABASE_URL is not set")
# - _engine = create_engine(DATABASE_URL, ...)
# - _SessionLocal = sessionmaker(bind=_engine, ...)
#
# NEW CODE ADDED:
# - from src.core.client_hub import get_database_engine, get_database_session_maker
# - _engine = get_database_engine()
# - _SessionLocal = get_database_session_maker()
#
# BENEFITS:
# - Centralized database configuration
# - Automatic error handling and logging
# - Better debugging capabilities
# - Consistent connection management
# - Environment variable validation
