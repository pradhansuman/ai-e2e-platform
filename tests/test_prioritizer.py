"""Tests for the risk-based prioritization engine."""
from app.agents.prioritizer import prioritize_tests, score_test, to_priority


def test_priority_thresholds():
    assert to_priority(0.9) == "P0"
    assert to_priority(0.7) == "P1"
    assert to_priority(0.5) == "P2"
    assert to_priority(0.1) == "P3"


def test_score_respects_explicit_factors():
    test = {
        "business_impact": 1.0,
        "failure_probability": 1.0,
        "change_frequency": 1.0,
        "user_traffic": 1.0,
        "technical_complexity": 1.0,
        "historical_failures": 1.0,
    }
    assert score_test(test) == 1.0


def test_prioritize_sorts_descending():
    tests = [
        {"test_id": "low", "risk": "low"},
        {"test_id": "critical", "risk": "critical"},
        {"test_id": "high", "risk": "high"},
    ]
    out = prioritize_tests(tests)
    assert out[0]["test_id"] == "critical"
    assert out[-1]["test_id"] == "low"
    assert all("priority_score" in t for t in out)


def test_historical_failures_folded_in():
    tests = [{"test_id": "T1", "risk": "low"}]
    baseline = prioritize_tests([dict(t) for t in tests])[0]["priority_score"]
    out = prioritize_tests(tests, history={"T1": 1.0})[0]
    assert out["historical_failures"] == 1.0
    # History must be folded in and increase the risk score.
    assert out["priority_score"] > baseline
