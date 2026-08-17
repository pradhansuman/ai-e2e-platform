"""Tests for the flowchart-aligned pipeline (understanding → intelligence → learn)."""
from app.graph.nodes import _compute_quality


def test_compute_quality_metrics():
    state = {
        "execution_results": [
            {"test_id": "a", "status": "passed"},
            {"test_id": "b", "status": "failed"},
        ],
        "healing_events": [{"x": 1}],
        "coverage_analysis": {"uncovered_risks": ["r1"], "uncovered_journeys": []},
        "risks": [{"risk_id": "r1"}, {"risk_id": "r2"}],
        "user_journeys": [],
    }
    q = _compute_quality(state)
    assert q["pass_rate"] == 0.5
    assert q["healing_success"] == 1
    assert q["coverage_rate"] == 0.5
    assert q["test_count"] == 2


def test_workflow_compiles_with_flowchart_nodes():
    """Both graphs must compile (catches wiring/edge errors in the new nodes)."""
    from app.graph.workflow import build_approval_workflow, build_workflow

    g = build_workflow()
    assert g is not None
    ga = build_approval_workflow()
    assert ga is not None


def test_flowchart_nodes_are_registered():
    from app.graph.workflow import build_workflow

    g = build_workflow()
    node_names = set(g.get_graph().nodes.keys())
    for expected in (
        "ingest",
        "discover",
        "analyze_requirements",
        "generate_tests",
        "test_intelligence",
        "prioritize",
        "execute",
        "observe",
        "analyze_failure",
        "diagnose",
        "repair",
        "retest",
        "validate",
        "report",
        "learn",
    ):
        assert expected in node_names, f"missing node {expected}"


def test_prioritize_node_caps_to_max_tests(monkeypatch):
    import asyncio
    from app.graph.nodes import prioritize_node
    from app.config import settings
    monkeypatch.setattr(settings, "max_tests", 3)
    state = {"test_cases": [
        {"test_id": f"T{i}", "risk": "high", "priority": "P0"} for i in range(10)
    ]}
    out = asyncio.run(prioritize_node(state))
    assert len(out["test_cases"]) == 3
    assert [t["test_id"] for t in out["test_cases"]][:2] == ["T0", "T1"]
