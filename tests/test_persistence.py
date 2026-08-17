"""Tests for the durable persistence layer (round-trips through SQLite)."""
import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def test_persist_and_load_roundtrip(tmp_path):
    async def _run():
        import app.db as db
        import app.models.orm  # noqa: F401
        from app.db import Base

        url = f"sqlite+aiosqlite:///{tmp_path / 'e2e.db'}"
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)

        original = db.SessionFactory
        db.SessionFactory = factory
        try:
            from app.services.persistence import dashboard_summary, get_run, persist_run

            state = {
                "run_id": "r1",
                "status": "passed",
                "application": {"url": "https://x.test", "name": "X"},
                "final_result": {"total": 1, "passed": 1},
                "execution_results": [
                    {
                        "test_id": "T1",
                        "status": "passed",
                        "duration_ms": 5,
                        "steps": [],
                        "console_logs": [],
                        "network_events": [],
                    }
                ],
                "failures": [],
                "healing_events": [],
            }
            await persist_run(state)

            loaded = await get_run("r1")
            assert loaded is not None
            assert loaded["run_id"] == "r1"
            assert loaded["status"] == "passed"
            assert loaded["execution_results"][0]["test_id"] == "T1"

            summary = await dashboard_summary()
            assert summary["tests"]["total"] == 1
            assert summary["tests"]["passed"] == 1
            assert summary["runs"] == 1
        finally:
            db.SessionFactory = original
            await engine.dispose()

    asyncio.run(_run())


def test_persist_failure_and_healing(tmp_path):
    async def _run():
        import app.db as db
        import app.models.orm  # noqa: F401
        from app.db import Base

        url = f"sqlite+aiosqlite:///{tmp_path / 'e2e.db'}"
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)

        original = db.SessionFactory
        db.SessionFactory = factory
        try:
            from app.services.persistence import get_run, persist_run

            state = {
                "run_id": "r2",
                "status": "failed",
                "application": {"url": "https://x.test", "name": "X"},
                "final_result": {"total": 1, "passed": 0},
                "execution_results": [
                    {"test_id": "T9", "status": "failed", "duration_ms": 10,
                     "steps": [], "console_logs": [], "network_events": []}
                ],
                "failures": [
                    {
                        "failure": {"test_id": "T9", "error": "no element matching"},
                        "root_cause": {
                            "classification": "automation_defect",
                            "root_cause": "broken locator",
                            "confidence": 0.6,
                            "evidence": ["x"],
                            "recommended_fix": "heal",
                            "affected_tests": [],
                        },
                    }
                ],
                "healing_events": [
                    {
                        "test_id": "T9",
                        "original_locator": "#a",
                        "new_locator": "[id=b]",
                        "reason": "test",
                        "confidence": 0.9,
                        "evidence": [],
                        "approval_status": "pending",
                    }
                ],
            }
            await persist_run(state)
            loaded = await get_run("r2")
            assert loaded["failures"][0]["classification"] == "automation_defect"
        finally:
            db.SessionFactory = original
            await engine.dispose()

    asyncio.run(_run())


def test_get_run_missing_returns_none(tmp_path):
    async def _run():
        import app.db as db
        import app.models.orm  # noqa: F401
        from app.db import Base

        url = f"sqlite+aiosqlite:///{tmp_path / 'e2e.db'}"
        engine = create_async_engine(url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        original = db.SessionFactory
        db.SessionFactory = factory
        try:
            from app.services.persistence import get_run

            assert await get_run("does-not-exist") is None
        finally:
            db.SessionFactory = original
            await engine.dispose()

    asyncio.run(_run())
