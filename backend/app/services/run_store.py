"""In-memory run store: fast-path cache for in-flight and recent runs.

The API reads from here first (so queued/running runs are visible
immediately), then falls back to the durable database for completed runs that
survived a process restart. The background worker writes final state here too.
"""
from __future__ import annotations

from typing import Any

_RUNS: dict[str, dict[str, Any]] = {}


def put(run_id: str, state: dict[str, Any]) -> None:
    _RUNS[run_id] = state


def get(run_id: str) -> dict[str, Any] | None:
    return _RUNS.get(run_id)


def set_status(run_id: str, status: str) -> None:
    rec = _RUNS.get(run_id)
    if rec is None:
        rec = {"run_id": run_id}
        _RUNS[run_id] = rec
    rec["status"] = status


def status(run_id: str) -> str:
    rec = _RUNS.get(run_id)
    return rec.get("status", "unknown") if rec else "unknown"


def values() -> list[dict[str, Any]]:
    return list(_RUNS.values())


def clear() -> None:
    _RUNS.clear()
