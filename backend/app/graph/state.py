"""LangGraph state definition.

``TestState`` is the single source of truth threaded through every node in
the workflow. It mirrors the state block specified in section 12 of the
brief, plus operational fields needed for retry/healing control.
"""
from __future__ import annotations

from typing import Any, Literal, TypedDict

Status = Literal[
    "pending",
    "discovered",
    "generated",
    "running",
    "passed",
    "failed",
    "blocked",
    "awaiting_approval",
]

FailureClass = Literal[
    "product_defect",
    "automation_defect",
    "environment",
    "test_data",
    "timing",
    "network",
    "dependency",
    "authentication",
    "configuration",
    "flaky",
    "unknown",
]

Priority = Literal["P0", "P1", "P2", "P3"]


class TestState(TypedDict, total=False):
    # -- Inputs ----------------------------------------------------------
    objective: str
    application: dict[str, Any]  # url, name, auth config (masked), repo, spec
    source: Literal["url", "repo", "api_spec", "requirements"]

    # -- Discovery -------------------------------------------------------
    discovered_pages: list[dict[str, Any]]
    discovered_apis: list[dict[str, Any]]
    components: list[dict[str, Any]]
    application_model: dict[str, Any]

    # -- Requirements ----------------------------------------------------
    requirements: list[dict[str, Any]]
    requirement_gaps: list[dict[str, Any]]

    # -- Generation ------------------------------------------------------
    test_scenarios: list[dict[str, Any]]
    test_cases: list[dict[str, Any]]  # each conforms to TestCase schema

    # -- Execution -------------------------------------------------------
    execution_results: list[dict[str, Any]]
    evidence: dict[str, Any]
    step_results: list[dict[str, Any]]

    # -- Failure intelligence -------------------------------------------
    failures: list[dict[str, Any]]
    root_cause: dict[str, Any]
    failure_class: FailureClass
    confidence: float

    # -- Healing ---------------------------------------------------------
    healing_events: list[dict[str, Any]]
    approval_required: bool
    approval_decision: Literal["approved", "rejected", "pending"]

    # -- Control ---------------------------------------------------------
    retry_count: int
    heal_count: int
    status: Status
    final_result: dict[str, Any]
    run_id: str
    traces: list[dict[str, Any]]

    # -- Evaluation ------------------------------------------------------
    ai_quality: dict[str, Any]
    evaluations: list[dict[str, Any]]


def initial_state(objective: str, application: dict[str, Any], run_id: str) -> TestState:
    """Factory for a fresh workflow state."""
    return TestState(
        objective=objective,
        application=application,
        source=application.get("source", "url"),
        discovered_pages=[],
        discovered_apis=[],
        components=[],
        requirements=[],
        requirement_gaps=[],
        test_scenarios=[],
        test_cases=[],
        execution_results=[],
        step_results=[],
        evidence={},
        failures=[],
        root_cause={},
        confidence=0.0,
        healing_events=[],
        approval_required=False,
        approval_decision="pending",
        retry_count=0,
        heal_count=0,
        status="pending",
        final_result={},
        run_id=run_id,
        traces=[],
        ai_quality={},
        evaluations=[],
    )
