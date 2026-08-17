"""REST API routes: applications, runs, tests, dashboard (spec section 15)."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..graph import run_workflow
from ..security import audit_event, can_execute, Principal, redact_for_llm
from ..services import run_store
from .deps import PrincipalDep

api_router = APIRouter()

# In-memory application store for the MVP; runs use run_store + durable DB.
_APPLICATIONS: dict[str, dict[str, Any]] = {}


class RunRequest(BaseModel):
    objective: str
    application: dict[str, Any] = Field(..., description="url, name, source, credentials(ref)")
    requirements: list[dict[str, Any]] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")


@api_router.post("/applications")
async def create_application(payload: dict[str, Any], principal: Principal | None = PrincipalDep):
    app_id = uuid.uuid4().hex
    # Strip secrets before storing/returning.
    _APPLICATIONS[app_id] = redact_for_llm(payload)
    audit_event("application.create", principal.user_id if principal else "anon", {"id": app_id})
    return {"id": app_id, **redact_for_llm(payload)}


@api_router.get("/applications")
async def list_applications(principal: Principal | None = PrincipalDep):
    return list(_APPLICATIONS.values())


@api_router.post("/runs")
async def create_run(req: RunRequest, principal: Principal | None = PrincipalDep):
    if not can_execute(principal, "execute_playwright_test"):
        raise HTTPException(status_code=403, detail="Insufficient role")
    run_id = uuid.uuid4().hex

    # Durable "queued" record (best-effort; DB may be unavailable in dev).
    try:
        from ..services.persistence import persist_run_pending

        await persist_run_pending(run_id, req.application)
    except Exception:  # noqa: BLE001 - degrade to in-memory only
        pass

    run_store.put(
        run_id,
        {
            "run_id": run_id,
            "status": "queued",
            "objective": req.objective,
            "application": req.application,
            "requirements": req.requirements,
        },
    )

    from ..services import worker

    async def _job() -> dict[str, Any]:
        result = await run_workflow(req.objective, req.application, run_id=run_id)
        result["application"]["requirements"] = req.requirements
        run_store.put(run_id, result)
        return result

    await worker.enqueue(run_id, _job)
    audit_event("run.create", principal.user_id if principal else "anon", {"run_id": run_id})
    return {"run_id": run_id, "status": "queued"}


@api_router.get("/runs/{run_id}")
async def get_run(run_id: str, principal: Principal | None = PrincipalDep):
    rec = run_store.get(run_id)
    if rec is not None:
        return rec
    try:
        from ..services.persistence import get_run as db_get_run

        rec = await db_get_run(run_id)
        if rec is not None:
            return rec
    except Exception:  # noqa: BLE001 - DB may be unavailable
        pass
    raise HTTPException(status_code=404, detail="Run not found")


@api_router.post("/runs/{run_id}/approve")
async def approve_run(run_id: str, req: ApprovalRequest, principal: Principal | None = PrincipalDep):
    state = run_store.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Run not found")
    state["approval_decision"] = req.decision
    result = await run_workflow(
        state.get("objective", ""),
        state.get("application", {}),
        approval_resume=True,
        initial=state,
        run_id=run_id,
    )
    run_store.put(run_id, result)
    audit_event("run.approve", principal.user_id if principal else "anon", {"run_id": run_id, "decision": req.decision})
    return {"run_id": run_id, "status": result.get("status"), "final_result": result.get("final_result", {})}


@api_router.get("/runs/{run_id}/failures")
async def get_failures(run_id: str, principal: Principal | None = PrincipalDep):
    state = run_store.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return state.get("failures", [])


@api_router.get("/dashboard/summary")
async def dashboard_summary(principal: Principal | None = PrincipalDep):
    """Aggregate metrics for the dashboard (spec section 15)."""
    try:
        from ..services.persistence import dashboard_summary as db_dashboard

        return await db_dashboard()
    except Exception:  # noqa: BLE001 - DB may be unavailable; fall back to memory
        pass

    tests = 0
    passed = 0
    failed = 0
    flaky = 0
    healing = 0
    for run in run_store.values():
        results = run.get("execution_results", [])
        tests += len(results)
        passed += sum(1 for r in results if r.get("status") == "passed")
        failed += sum(1 for r in results if r.get("status") == "failed")
        flaky += sum(1 for r in results if r.get("status") == "flaky")
        healing += len(run.get("healing_events", []))

    return {
        "applications": len(_APPLICATIONS),
        "tests": {"total": tests, "passed": passed, "failed": failed, "flaky": flaky},
        "ai": {"healing_events": healing},
        "execution": {"pass_rate": round(passed / tests, 4) if tests else 0.0},
        "runs": len(_RUNS),
    }
