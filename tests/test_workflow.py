"""Tests for LangGraph state and routing (no network/LLM required)."""
from app.graph.state import initial_state
from app.graph.workflow import (
    _route_after_analyze,
    _route_after_observe,
    _route_after_repair,
)


def test_initial_state_defaults():
    state = initial_state("objective", {"url": "https://x.test"}, "run1")
    assert state["status"] == "pending"
    assert state["retry_count"] == 0
    assert state["test_cases"] == []
    assert state["run_id"] == "run1"


def test_initial_state_carries_limit_and_priority():
    state = initial_state(
        "objective", {"url": "https://x.test"}, "run1", limit=3, priority="P0"
    )
    assert state["test_budget"] == 3
    assert state["test_priority"] == "P0"


def test_prioritize_node_applies_limit_and_priority():
    import asyncio
    from app.graph.nodes import prioritize_node

    hi = {
        "business_impact": 1.0,
        "failure_probability": 1.0,
        "change_frequency": 1.0,
        "user_traffic": 1.0,
        "technical_complexity": 1.0,
        "historical_failures": 1.0,
    }  # score 1.0 -> P0
    lo = {k: 0.0 for k in hi}  # score 0.0 -> P3
    cases = [
        {"test_id": "a", **hi},
        {"test_id": "b", **hi},
        {"test_id": "c", **lo},
        {"test_id": "d", **lo},
    ]
    state = {
        "test_cases": list(cases),
        "test_budget": 2,
        "test_priority": "P0",
    }
    out = asyncio.run(prioritize_node(state))
    # P0 filter keeps only a/b; budget cap (2) leaves both.
    ids = {t["test_id"] for t in out["test_cases"]}
    assert ids == {"a", "b"}
    assert all(t["priority"] == "P0" for t in out["test_cases"])


def test_route_after_observe_pass():
    assert _route_after_observe({"failures": []}) == "validate"


def test_route_after_observe_fail():
    assert _route_after_observe({"failures": [{}]}) == "analyze_failure"


def test_route_after_analyze_product_defect():
    assert _route_after_analyze({"failure_class": "product_defect"}) == "report"


def test_route_after_analyze_automation():
    assert _route_after_analyze({"failure_class": "automation_defect", "retry_count": 0}) == "diagnose"


def test_route_after_repair_pending_approval():
    assert (
        _route_after_repair({"approval_required": True, "approval_decision": "pending"})
        == "__end__"
    )
