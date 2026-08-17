"""LangGraph node implementations.

Each node is a pure-ish async function ``(TestState) -> partial TestState``.
LLM calls happen only in dedicated agent modules; nodes orchestrate, persist,
and apply control-flow (retries, approval) logic.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..agents.analyzer import analyze_failure_evidence, heuristic_classify
from ..agents.discovery import discover_application_model
from ..agents.flakiness import detect_flakiness
from ..agents.generator import fallback_generate_tests, generate_tests
from ..agents.healer import apply_healing, heuristic_heal, propose_healing
from ..agents.prioritizer import prioritize_tests
from ..agents.requirements import analyze_requirements
from ..config import settings
from ..executor import PlaywrightExecutor
from ..security import mask_secrets, sanitize_untrusted_content
from .state import TestState

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# INGEST
# --------------------------------------------------------------------------- #
async def ingest_node(state: TestState) -> TestState:
    """Normalize the input: URL / repo / spec / requirements."""
    app = dict(state.get("application", {}))
    app.setdefault("source", state.get("source", "url"))
    # Never let raw credential material flow into downstream LLM calls.
    app["credentials"] = mask_secrets(str(app.get("credentials", "")))
    state["application"] = app
    state["objective"] = state.get("objective") or f"Test application at {app.get('url')}"
    return state


# --------------------------------------------------------------------------- #
# DISCOVER
# --------------------------------------------------------------------------- #
async def discover_node(state: TestState) -> TestState:
    app = state["application"]
    url = app.get("url")
    executor = PlaywrightExecutor()
    raw = await executor.discover(url) if url else {"pages": []}

    requirements = state.get("requirements", [])
    try:
        model = await asyncio.to_thread(
            discover_application_model, url or "", raw, requirements
        )
        model_dict = model.model_dump()
    except Exception as exc:  # noqa: BLE001 - discovery must not crash the run
        logger.warning("LLM discovery failed (%s); using raw crawl data", exc)
        model_dict = {"pages": raw.get("pages", []), "apis": [], "auth_flows": [], "business_workflows": [], "risk_areas": []}

    state["discovered_pages"] = raw.get("pages", [])
    state["discovered_apis"] = model_dict.get("apis", [])
    state["components"] = raw.get("pages", [])
    state["application_model"] = model_dict
    state["status"] = "discovered"
    return state


# --------------------------------------------------------------------------- #
# ANALYZE REQUIREMENTS
# --------------------------------------------------------------------------- #
async def analyze_requirements_node(state: TestState) -> TestState:
    requirements = state.get("requirements", [])
    if not requirements:
        state["requirement_gaps"] = []
        return state
    try:
        analysis = await asyncio.to_thread(analyze_requirements, requirements)
        state["requirement_gaps"] = analysis.gaps
        # Attach enriched requirement context for the generator.
        state["_requirement_analysis"] = analysis.model_dump()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Requirement analysis failed: %s", exc)
        state["requirement_gaps"] = []
    return state


# --------------------------------------------------------------------------- #
# GENERATE TESTS
# --------------------------------------------------------------------------- #
async def generate_tests_node(state: TestState) -> TestState:
    existing = state.get("test_cases", [])
    cases: list[dict[str, Any]] = []
    try:
        suite = await asyncio.to_thread(
            generate_tests,
            application_model=state.get("application_model", {}),
            requirements=state.get("_requirement_analysis", {}),
            existing=existing,
        )
        cases = [c.model_dump() for c in suite.test_cases]
    except Exception as exc:  # noqa: BLE001 - LLM may be unavailable/rate-limited
        logger.warning("LLM test generation failed (%s); using deterministic fallback", exc)

    if not cases:
        cases = fallback_generate_tests(
            state.get("application", {}).get("url", ""),
            state.get("discovered_pages", []),
        )
        logger.info("Generated %d deterministic fallback tests", len(cases))

    state["test_scenarios"] = cases
    state["test_cases"] = cases
    state["status"] = "generated"
    return state


# --------------------------------------------------------------------------- #
# PRIORITIZE
# --------------------------------------------------------------------------- #
async def prioritize_node(state: TestState) -> TestState:
    state["test_cases"] = prioritize_tests(state.get("test_cases", []))
    return state


# --------------------------------------------------------------------------- #
# EXECUTE
# --------------------------------------------------------------------------- #
async def execute_node(state: TestState) -> TestState:
    app = state["application"]
    url = app.get("url")
    executor = PlaywrightExecutor()

    # Re-run only tests that are pending retest; otherwise run all.
    tests = state.get("test_cases", [])
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for test in tests:
        # Skip tests already passed in a previous pass unless retesting.
        if test.get("_passed") and not state.get("_force_retest"):
            results.append(test.get("_result"))
            continue
        result = await executor.execute_test(test, url)
        result["priority"] = test.get("priority")
        results.append(result)
        if result["status"] == "failed":
            failures.append(result)

    state["execution_results"] = results
    state["step_results"] = [s for r in results for s in r.get("steps", [])]
    state["failures"] = failures
    state["status"] = "running"
    return state


# --------------------------------------------------------------------------- #
# OBSERVE
# --------------------------------------------------------------------------- #
async def observe_node(state: TestState) -> TestState:
    """Aggregate evidence: screenshots, console, network, traces, timing."""
    evidence: dict[str, Any] = {
        "screenshots": [],
        "console_logs": [],
        "network_events": [],
        "total_duration_ms": 0,
    }
    for r in state.get("execution_results", []):
        evidence["screenshots"].extend(
            s.get("screenshot") for s in r.get("steps", []) if s.get("screenshot")
        )
        evidence["console_logs"].extend(r.get("console_logs", []))
        evidence["network_events"].extend(r.get("network_events", []))
        evidence["total_duration_ms"] += r.get("duration_ms", 0)
    state["evidence"] = evidence
    return state


# --------------------------------------------------------------------------- #
# ANALYZE FAILURE
# --------------------------------------------------------------------------- #
async def analyze_failure_node(state: TestState) -> TestState:
    failures = state.get("failures", [])
    if not failures:
        state["status"] = "passed"
        return state

    analyzed: list[dict[str, Any]] = []
    for failure in failures:
        try:
            rc = await asyncio.to_thread(
                analyze_failure_evidence,
                failure,
                {"evidence": state.get("evidence", {})},
            )
        except Exception as exc:  # noqa: BLE001 - LLM may be unavailable
            logger.warning("LLM failure analysis failed (%s); using heuristic", exc)
            rc = heuristic_classify(failure, {"evidence": state.get("evidence", {})})
        analyzed.append({"failure": failure, "root_cause": rc})

    # Use the highest-confidence classification as the run-level diagnosis.
    best = max(analyzed, key=lambda a: a["root_cause"].get("confidence", 0.0))
    state["root_cause"] = best["root_cause"]
    state["failure_class"] = best["root_cause"].get("classification", "unknown")
    state["confidence"] = best["root_cause"].get("confidence", 0.0)
    state["failures"] = analyzed
    state["status"] = "failed"
    return state


# --------------------------------------------------------------------------- #
# DIAGNOSE
# --------------------------------------------------------------------------- #
async def diagnose_node(state: TestState) -> TestState:
    """Produce recommended fix + affected tests (already in root_cause)."""
    rc = state.get("root_cause", {})
    if not rc.get("recommended_fix"):
        rc["recommended_fix"] = _default_fix(rc.get("classification"))
        state["root_cause"] = rc
    return state


def _default_fix(classification: str | None) -> str:
    fixes = {
        "automation_defect": "Repair the failing locator via self-healing.",
        "product_defect": "Escalate to engineering; likely application bug.",
        "timing": "Replace fixed waits with wait_for conditions.",
        "test_data": "Isolate/reset test data per run.",
        "environment": "Verify environment health and dependencies.",
        "authentication": "Refresh test credentials/session.",
        "flaky": "Quarantine and investigate instability.",
    }
    return fixes.get(classification or "", "Manual investigation required.")


# --------------------------------------------------------------------------- #
# REPAIR (self-healing)
# --------------------------------------------------------------------------- #
async def repair_node(state: TestState) -> TestState:
    if state.get("failure_class") != "automation_defect":
        return state  # only automation defects are self-healable

    failures = state.get("failures", [])
    healed = False
    for entry in failures:
        failure = entry.get("failure", {})
        broken_step = _first_failed_step(failure)
        if not broken_step:
            continue
        original = broken_step.get("target")
        if not original:
            continue
        dom = failure.get("dom_snapshot") or _dom_from_evidence(state)
        if not dom:
            continue
        try:
            suggestion = await asyncio.to_thread(
                propose_healing,
                original,
                sanitize_untrusted_content(dom),
                broken_step.get("action", ""),
            )
        except Exception as exc:  # noqa: BLE001 - LLM may be unavailable
            logger.warning("LLM healing failed (%s); using heuristic", exc)
            suggestion = heuristic_heal(original, dom)
        if not suggestion.selected:
            continue
        test_id = failure.get("test_id")
        for test in state.get("test_cases", []):
            if test.get("test_id") == test_id:
                updated, event = apply_healing(test, original, suggestion)
                test.update(updated)
                state.setdefault("healing_events", []).append(event)
                healed = True
                break

    if healed:
        state["heal_count"] = state.get("heal_count", 0) + 1
        if settings.human_approval_required and state.get("approval_decision") != "approved":
            state["approval_required"] = True
            state["status"] = "awaiting_approval"
    return state


def _first_failed_step(failure: dict[str, Any]) -> dict[str, Any] | None:
    steps = failure.get("steps", [])
    for s in steps:
        if s.get("status") in {"failed", "error"}:
            return s
    return None


def _dom_from_evidence(state: TestState) -> str:
    for r in state.get("execution_results", []):
        for s in r.get("steps", []):
            if s.get("dom_snapshot"):
                return s["dom_snapshot"]
    return ""


# --------------------------------------------------------------------------- #
# RETEST
# --------------------------------------------------------------------------- #
async def retest_node(state: TestState) -> TestState:
    state["retry_count"] = state.get("retry_count", 0) + 1
    state["_force_retest"] = True
    # Mark failed tests for re-execution.
    failed_ids = {f.get("failure", {}).get("test_id") for f in state.get("failures", [])}
    for test in state.get("test_cases", []):
        if test.get("test_id") in failed_ids:
            test["_passed"] = False
    state["failures"] = []
    return state


# --------------------------------------------------------------------------- #
# VALIDATE
# --------------------------------------------------------------------------- #
async def validate_node(state: TestState) -> TestState:
    results = state.get("execution_results", [])
    passed = sum(1 for r in results if r.get("status") == "passed")
    total = len(results) or 1
    state["status"] = "passed" if passed == len(results) else "failed"
    state["final_result"] = {
        "run_id": state.get("run_id"),
        "status": state["status"],
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": round(passed / total, 4),
        "confidence": state.get("confidence", 1.0),
        "retries": state.get("retry_count", 0),
        "healing_events": state.get("healing_events", []),
    }
    return state


# --------------------------------------------------------------------------- #
# REPORT
# --------------------------------------------------------------------------- #
async def report_node(state: TestState) -> TestState:
    # Persist results (best-effort; degrades to in-memory when no DB).
    try:
        from ..services.persistence import persist_run

        await persist_run(state)
    except Exception as exc:  # noqa: BLE001 - DB may be unavailable
        logger.debug("Skipping persistence (%s)", exc)
    state["final_result"] = state.get("final_result") or {
        "run_id": state.get("run_id"),
        "status": state.get("status", "unknown"),
        "total": len(state.get("execution_results", [])),
        "passed": sum(1 for r in state.get("execution_results", []) if r.get("status") == "passed"),
        "failed": len(state.get("failures", [])),
        "confidence": state.get("confidence", 0.0),
        "retries": state.get("retry_count", 0),
        "root_cause": state.get("root_cause", {}),
        "healing_events": state.get("healing_events", []),
    }
    return state

