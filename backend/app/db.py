"""Async SQLAlchemy engine/session management (SQLAlchemy 2.0 style)."""
from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _resolve_db_url(url: str) -> str:
    """Resolve relative SQLite paths against the repo root so the DB file
    location is stable regardless of the CWD the server is launched from."""
    if url.startswith("sqlite") and ":///" in url:
        prefix, _, path = url.partition(":///")
        if path and not path.startswith("/"):
            return f"{prefix}:///{_REPO_ROOT / path}"
    return url


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


engine = create_async_engine(
    _resolve_db_url(settings.database_url),
    echo=False,
    pool_pre_ping=True,
    future=True,
)

SessionFactory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a scoped async session."""
    async with SessionFactory() as session:
        yield session


async def init_db() -> None:
    """Create tables for local development (Alembic is used in production)."""
    # Imported here to register models on Base.metadata before create_all.
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
