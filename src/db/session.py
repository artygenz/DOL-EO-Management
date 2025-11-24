# src/db/session.py
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