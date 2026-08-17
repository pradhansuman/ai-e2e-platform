"""Alembic environment (async SQLAlchemy) for the ai-e2e-platform.

Resolves the database URL from ``app.config.settings`` (so it is cwd-agnostic
and honours ``.env``), then runs migrations against the same async engine the
application uses (aiosqlite in dev, asyncpg in production).
"""
from __future__ import annotations

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Make `app` importable regardless of how Alembic is invoked (CLI from the
# backend dir, or programmatically from the running application).
_BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app import models  # noqa: F401 - register all tables on Base.metadata
from app.config import settings
from app.db import Base, _resolve_db_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Resolve the URL exactly like the app does (stable SQLite path, .env aware).
config.set_main_option("sqlalchemy.url", _resolve_db_url(settings.database_url))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def _run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(_do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(_run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
