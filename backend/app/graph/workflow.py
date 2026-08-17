"""LangGraph workflow builder (spec section 12).

Assembles the state machine: nodes, conditional edges, retry limits, and the
human-approval gate for self-healing. Also exposes a runner and an
approval-resume entry point.
"""
from __future__ import annotations

import uuid
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from ..config import settings
from . import nodes
from .state import TestState, initial_state

__all__ = ["build_workflow", "build_approval_workflow", "run_workflow"]


# --------------------------------------------------------------------------- #
# Routing functions
# --------------------------------------------------------------------------- #
def _route_after_observe(state: TestState) -> str:
    """Decide whether to validate (pass) or analyze (fail)."""
    if state.get("failures"):
        return "analyze_failure"
    return "validate"


def _route_after_analyze(state: TestState) -> str:
    """Product defects are reported; automation defects go to diagnosis/healing."""
    if state.get("failure_class") == "product_defect":
        return "report"
    if state.get("failure_class") == "automation_defect":
        return "diagnose"
    # Non-product, non-automation failures (env, timing, flaky, ...).
    if state.get("retry_count", 0) < settings.max_retries:
        return "retest"
    return "report"


def _route_after_diagnose(state: TestState) -> str:
    """Only heal automation defects, and respect the heal budget."""
    if state.get("failure_class") == "automation_defect" and state.get("heal_count", 0) < settings.max_heal_retries:
        return "repair"
    if state.get("retry_count", 0) < settings.max_retries:
        return "retest"
    return "report"


def _route_after_repair(state: TestState) -> str:
    """Human approval gate: end and await approval, or retest immediately."""
    if state.get("approval_required") and state.get("approval_decision") != "approved":
        return END
    if state.get("approval_decision") == "rejected":
        return "report"
    return "retest"


def _route_after_retest(state: TestState) -> str:
    """Loop guard: retest only while under the retry budget."""
    if state.get("retry_count", 0) >= settings.max_retries:
        return "report"
    return "execute"


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def build_workflow():
    """Assemble the main test-execution graph."""
    g = StateGraph(TestState)

    g.add_node("ingest", nodes.ingest_node)
    g.add_node("discover", nodes.discover_node)
    g.add_node("analyze_requirements", nodes.analyze_requirements_node)
    g.add_node("generate_tests", nodes.generate_tests_node)
    g.add_node("test_intelligence", nodes.test_intelligence_node)
    g.add_node("prioritize", nodes.prioritize_node)
    g.add_node("execute", nodes.execute_node)
    g.add_node("observe", nodes.observe_node)
    g.add_node("analyze_failure", nodes.analyze_failure_node)
    g.add_node("diagnose", nodes.diagnose_node)
    g.add_node("repair", nodes.repair_node)
    g.add_node("retest", nodes.retest_node)
    g.add_node("validate", nodes.validate_node)
    g.add_node("report", nodes.report_node)
    g.add_node("learn", nodes.learn_node)

    g.set_entry_point("ingest")
    g.add_edge("ingest", "discover")
    g.add_edge("discover", "analyze_requirements")
    g.add_edge("analyze_requirements", "generate_tests")
    g.add_edge("generate_tests", "test_intelligence")
    g.add_edge("test_intelligence", "prioritize")
    g.add_edge("prioritize", "execute")
    g.add_edge("execute", "observe")

    g.add_conditional_edges(
        "observe",
        _route_after_observe,
        {"analyze_failure": "analyze_failure", "validate": "validate"},
    )

    g.add_conditional_edges(
        "analyze_failure",
        _route_after_analyze,
        {"diagnose": "diagnose", "retest": "retest", "report": "report"},
    )

    g.add_conditional_edges(
        "diagnose",
        _route_after_diagnose,
        {"repair": "repair", "retest": "retest", "report": "report"},
    )

    g.add_conditional_edges(
        "repair",
        _route_after_repair,
        {"retest": "retest", "report": "report", END: END},
    )

    g.add_conditional_edges(
        "retest",
        _route_after_retest,
        {"execute": "execute", "report": "report"},
    )

    g.add_edge("validate", "report")
    g.add_edge("report", "learn")
    g.add_edge("learn", END)

    return g.compile()


def build_approval_workflow():
    """Resume graph used after a human approves/rejects a pending healing.

    Entry node ``approve`` reads ``approval_decision`` and routes to retest
    (approved) or report (rejected), reusing the same node implementations.
    """
    g = StateGraph(TestState)
    g.add_node("approve", _approve_node)
    g.add_node("retest", nodes.retest_node)
    g.add_node("execute", nodes.execute_node)
    g.add_node("observe", nodes.observe_node)
    g.add_node("analyze_failure", nodes.analyze_failure_node)
    g.add_node("diagnose", nodes.diagnose_node)
    g.add_node("repair", nodes.repair_node)
    g.add_node("validate", nodes.validate_node)
    g.add_node("report", nodes.report_node)
    g.add_node("learn", nodes.learn_node)

    g.set_entry_point("approve")

    def _route_approve(state: TestState) -> str:
        return "retest" if state.get("approval_decision") == "approved" else "report"

    g.add_conditional_edges("approve", _route_approve, {"retest": "retest", "report": "report"})
    g.add_edge("retest", "execute")
    g.add_edge("execute", "observe")
    g.add_conditional_edges(
        "observe",
        _route_after_observe,
        {"analyze_failure": "analyze_failure", "validate": "validate"},
    )
    g.add_conditional_edges(
        "analyze_failure",
        _route_after_analyze,
        {"diagnose": "diagnose", "retest": "retest", "report": "report"},
    )
    g.add_conditional_edges(
        "diagnose",
        _route_after_diagnose,
        {"repair": "repair", "retest": "retest", "report": "report"},
    )
    g.add_conditional_edges(
        "repair",
        _route_after_repair,
        {"retest": "retest", "report": "report", END: END},
    )
    g.add_edge("validate", "report")
    g.add_edge("report", "learn")
    g.add_edge("learn", END)

    return g.compile()


async def _approve_node(state: TestState) -> TestState:
    state["approval_required"] = False
    return state


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
def _build_graph(approval_resume: bool):
    return build_approval_workflow() if approval_resume else build_workflow()


async def run_workflow(
    objective: str,
    application: dict[str, Any],
    *,
    approval_resume: bool = False,
    initial: dict[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Run the graph to completion and return the final state.

    For approval resume, pass ``initial`` as the persisted state snapshot from
    the paused run (including ``approval_decision`` already set by the caller).
    """
    graph = _build_graph(approval_resume)
    if approval_resume and initial:
        state: TestState = dict(initial)
        return await graph.ainvoke(state)

    state = initial_state(objective, application, run_id or uuid.uuid4().hex)
    return await graph.ainvoke(state)
