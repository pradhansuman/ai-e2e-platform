"""Persistence layer: durable storage of runs, results, failures, healing events.

Writes go through the async SQLAlchemy ORM. Production uses PostgreSQL
(`docker compose up`); development defaults to SQLite for zero-infra runs.
Functions raise on failure; callers (nodes/routes) catch and degrade to
in-memory where appropriate.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import delete, select

from .. import db
from ..models.orm import ApiEndpoint, Application, Failure, HealingEvent, Page, TestResult, TestRun


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _app_id(url: str) -> str:
    return hashlib.md5((url or "unknown").encode()).hexdigest()[:32]


async def _ensure_application(session, app: dict[str, Any]) -> str:
    url = app.get("url") or "unknown"
    app_id = _app_id(url)
    existing = await session.get(Application, app_id)
    if existing is None:
        session.add(Application(id=app_id, name=app.get("name") or url, url=url))
    return app_id


async def persist_run(state: dict[str, Any]) -> str:
    """Persist a completed workflow state to the database."""
    run_id = state.get("run_id") or uuid.uuid4().hex
    async with db.SessionFactory() as session:
        app_id = await _ensure_application(session, state.get("application", {}))

        existing = await session.get(TestRun, run_id)
        if existing is None:
            session.add(
                TestRun(
                    id=run_id,
                    application_id=app_id,
                    run_id=run_id,
                    status=state.get("status", "unknown"),
                    trigger=state.get("trigger", "manual"),
                    summary=state.get("final_result", {}),
                )
            )
        else:
            existing.status = state.get("status", "unknown")
            existing.summary = state.get("final_result", {})
            existing.finished_at = _now()

        # Replace prior results for this run (idempotent re-persist).
        await session.execute(delete(TestResult).where(TestResult.run_id == run_id))

        result_ids: dict[str, str] = {}
        for r in state.get("execution_results", []):
            rid = uuid.uuid4().hex
            result_ids[r.get("test_id")] = rid
            session.add(
                TestResult(
                    id=rid,
                    run_id=run_id,
                    test_id=r.get("test_id"),
                    status=r.get("status"),
                    duration_ms=r.get("duration_ms"),
                    step_results=r.get("steps", []),
                    evidence={
                        "console_logs": r.get("console_logs", []),
                        "network_events": r.get("network_events", []),
                    },
                )
            )

        for f in state.get("failures", []):
            failure = (f or {}).get("failure", {}) if isinstance(f, dict) else {}
            root_cause = (f or {}).get("root_cause", {}) if isinstance(f, dict) else {}
            test_id = failure.get("test_id")
            session.add(
                Failure(
                    id=uuid.uuid4().hex,
                    result_id=result_ids.get(test_id),
                    test_id=test_id,
                    classification=root_cause.get("classification", "unknown"),
                    root_cause=root_cause.get("root_cause", ""),
                    confidence=root_cause.get("confidence", 0.0),
                    evidence=root_cause.get("evidence", []),
                    recommended_fix=root_cause.get("recommended_fix"),
                    affected_tests=root_cause.get("affected_tests", []),
                )
            )

        for h in state.get("healing_events", []):
            session.add(
                HealingEvent(
                    id=uuid.uuid4().hex,
                    test_id=h.get("test_id"),
                    original_locator=h.get("original_locator"),
                    new_locator=h.get("new_locator"),
                    reason=h.get("reason", ""),
                    confidence=h.get("confidence", 0.0),
                    evidence=h.get("evidence", []),
                    approval_status=h.get("approval_status", "pending"),
                )
            )

        await session.commit()
    return run_id


async def get_run(run_id: str) -> dict[str, Any] | None:
    """Load a run summary (durable read; survives process restarts)."""
    async with db.SessionFactory() as session:
        run = await session.get(TestRun, run_id)
        if run is None:
            return None
        results = (
            await session.execute(select(TestResult).where(TestResult.run_id == run_id))
        ).scalars().all()
        result_ids = [r.id for r in results]
        failures = []
        if result_ids:
            failures = (
                await session.execute(
                    select(Failure).where(Failure.result_id.in_(result_ids))
                )
            ).scalars().all()
        return {
            "run_id": run.run_id,
            "status": run.status,
            "trigger": run.trigger,
            "summary": run.summary,
            "execution_results": [
                {
                    "test_id": r.test_id,
                    "status": r.status,
                    "duration_ms": r.duration_ms,
                    "step_results": r.step_results,
                    "evidence": r.evidence,
                }
                for r in results
            ],
            "failures": [
                {
                    "test_id": f.test_id,
                    "classification": f.classification,
                    "root_cause": f.root_cause,
                    "confidence": f.confidence,
                }
                for f in failures
            ],
        }


async def list_run_ids() -> list[str]:
    async with db.SessionFactory() as session:
        runs = (await session.execute(select(TestRun.run_id))).scalars().all()
        return list(runs)


async def dashboard_summary() -> dict[str, Any]:
    """Aggregate metrics from the database (spec section 15)."""
    async with db.SessionFactory() as session:
        apps = len((await session.execute(select(Application.id))).scalars().all())
        pages = len((await session.execute(select(Page.id))).scalars().all())
        apis = len((await session.execute(select(ApiEndpoint.id))).scalars().all())
        runs = len((await session.execute(select(TestRun.id))).scalars().all())
        results = (await session.execute(select(TestResult))).scalars().all()
        healing = len((await session.execute(select(HealingEvent.id))).scalars().all())
        failures = len((await session.execute(select(Failure.id))).scalars().all())

        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        flaky = sum(1 for r in results if r.status == "flaky")
        total = len(results)

        return {
            "applications": apps,
            "pages": pages,
            "apis": apis,
            "tests": {"total": total, "passed": passed, "failed": failed, "flaky": flaky},
            "ai": {"healing_events": healing},
            "execution": {
                "pass_rate": round(passed / total, 4) if total else 0.0,
                "avg_duration_ms": round(sum(r.duration_ms or 0 for r in results) / total) if total else 0,
            },
            "failures": failures,
            "runs": runs,
        }


async def persist_run_pending(run_id: str, application: dict[str, Any]) -> None:
    """Record a queued run so GET /runs/{id} is durable before execution starts."""
    async with db.SessionFactory() as session:
        app_id = await _ensure_application(session, application)
        existing = await session.get(TestRun, run_id)
        if existing is None:
            session.add(
                TestRun(
                    id=run_id,
                    application_id=app_id,
                    run_id=run_id,
                    status="queued",
                    trigger="manual",
                    summary={},
                )
            )
            await session.commit()


async def update_run_status(run_id: str, status: str) -> None:
    """Update a run's status, stamping ``finished_at`` on terminal states."""
    async with db.SessionFactory() as session:
        run = await session.get(TestRun, run_id)
        if run is None:
            return
        run.status = status
        if status in {"passed", "failed", "cancelled"}:
            run.finished_at = _now()
        await session.commit()
