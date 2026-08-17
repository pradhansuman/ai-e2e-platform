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
