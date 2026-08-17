"""Tests for the background worker queue + non-blocking run API."""
import asyncio
import time

from fastapi.testclient import TestClient


def test_worker_runs_job_and_updates_store():
    async def _run():
        from app.services import run_store, worker

        run_store.put("w1", {"run_id": "w1", "status": "queued"})

        async def job():
            await asyncio.sleep(0.05)
            run_store.put("w1", {"run_id": "w1", "status": "passed", "n": 7})
            return {}

        await worker.start(1)
        await worker.enqueue("w1", job)
        for _ in range(200):
            rec = run_store.get("w1")
            if rec and rec.get("status") == "passed":
                break
            await asyncio.sleep(0.02)
        await worker.stop()

        rec = run_store.get("w1")
        assert rec is not None and rec["status"] == "passed"
        assert rec["n"] == 7

    asyncio.run(_run())


def test_post_run_is_nonblocking(monkeypatch):
    import app.api.routes as routes
    from app.main import app

    async def fake_run_workflow(objective, application, **kwargs):
        await asyncio.sleep(0.15)
        return {
            "run_id": kwargs.get("run_id"),
            "status": "passed",
            "final_result": {"total": 1, "passed": 1},
            "application": dict(application),
            "execution_results": [],
            "failures": [],
        }

    monkeypatch.setattr(routes, "run_workflow", fake_run_workflow)

    with TestClient(app) as client:
        r = client.post(
            "/api/v1/runs",
            json={"objective": "t", "application": {"url": "https://x.test", "name": "X"}},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "queued"
        run_id = body["run_id"]

        got = None
        for _ in range(200):
            g = client.get(f"/api/v1/runs/{run_id}")
            assert g.status_code == 200
            got = g.json()
            if got.get("status") == "passed":
                break
            time.sleep(0.02)

        assert got is not None and got["status"] == "passed"
        assert got["final_result"]["passed"] == 1
