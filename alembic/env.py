from __future__ import annotations

import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import create_engine
from sqlalchemy import pool, engine_from_config
from alembic import context

# --- Make project importable ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.core.client_hub import get_database_engine
from src.db.base import Base  # imports all models so metadata is populated
import src.models

target_metadata = Base.metadata

# Alembic Config
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)



def run_migrations_offline() -> None:
    import os
    # Use DATABASE_URL from environment variables
    url = os.getenv('DATABASE_URL')
    if not url:
        raise ValueError("DATABASE_URL environment variable is required for offline migrations")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    # Use centralized client hub for database engine
    connectable = get_database_engine()
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()