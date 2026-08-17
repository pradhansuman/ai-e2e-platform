"""In-process background worker queue for test-run execution.

Keeps ``POST /runs`` non-blocking: the API enqueues a job and returns the run
id immediately; worker tasks drain the queue and run the LangGraph workflow to
completion, updating durable status along the way.

Production can swap this for Celery/arq on Redis without changing the API
contract — jobs are just ``callable() -> Awaitable[state]``.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

from . import run_store

logger = logging.getLogger(__name__)

Job = Callable[[], Awaitable[dict[str, Any]]]

# Recreated on start() and cleared on stop() so the queue is always bound to
# the current event loop (asyncio.run / TestClient each use a fresh loop).
_queue: asyncio.Queue[tuple[str, Job]] | None = None
_workers: list[asyncio.Task] = []
_concurrency: int = 1


async def enqueue(run_id: str, job: Job) -> None:
    """Queue a job for background execution."""
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    await _queue.put((run_id, job))


def queue_size() -> int:
    return _queue.qsize() if _queue is not None else 0


async def start(concurrency: int | None = None) -> None:
    """Start worker tasks (idempotent)."""
    global _workers, _concurrency, _queue
    if _workers:
        return
    _concurrency = max(1, concurrency or _concurrency)
    _queue = asyncio.Queue()
    _workers = [
        asyncio.create_task(_worker(i), name=f"run-worker-{i}")
        for i in range(_concurrency)
    ]


async def stop() -> None:
    """Cancel worker tasks and wait for them to finish."""
    global _workers, _queue
    for w in _workers:
        w.cancel()
    if _workers:
        await asyncio.gather(*_workers, return_exceptions=True)
    _workers.clear()
    _queue = None


async def _set_status(run_id: str, status: str) -> None:
    run_store.set_status(run_id, status)
    try:
        from .persistence import update_run_status

        await update_run_status(run_id, status)
    except Exception:  # noqa: BLE001 - status update is best-effort
        logger.warning("could not persist status %s for run %s", status, run_id)


async def _worker(idx: int) -> None:
    while True:
        assert _queue is not None
        run_id, job = await _queue.get()
        try:
            logger.info("worker %d starting run %s", idx, run_id)
            await _set_status(run_id, "running")
            await job()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - job errors are recorded, not fatal
            logger.exception("run %s failed in worker %d", run_id, idx)
            await _set_status(run_id, "failed")
        finally:
            _queue.task_done()
