"""FastAPI application factory."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings

_BACKEND_DIR = Path(__file__).resolve().parents[1]


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.environment in {"prod", "staging"}:
        # Production schema evolution goes through Alembic migrations.
        import asyncio

        from alembic import command
        from alembic.config import Config

        def _migrate() -> None:
            cfg = Config(str(_BACKEND_DIR / "alembic.ini"))
            command.upgrade(cfg, "head")

        await asyncio.to_thread(_migrate)
    else:
        # Dev/test: zero-infra create_all (fast; no migration files needed).
        try:
            from .db import init_db

            await init_db()
        except Exception:  # noqa: BLE001 - DB may be unavailable in dev
            pass

    # Start the background run-execution worker(s).
    from .services import worker

    await worker.start(settings.worker_concurrency)
    try:
        yield
    finally:
        await worker.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from .api.routes import api_router

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "app": settings.app_name, "env": settings.environment}

    return app


app = create_app()
