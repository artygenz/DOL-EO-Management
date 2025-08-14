# src/db/session.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load once at import time
DATABASE_URL = os.getenv("DATABASE_URL")  # e.g. postgresql+psycopg2://dol_user:artygenz@db:5432/dol
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set")

# Engine (sync)
_engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

# Session maker
_SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)

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