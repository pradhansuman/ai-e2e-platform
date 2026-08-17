"""Tests for the Test Intelligence agent (coverage analysis)."""
from app.agents.intelligence import fallback_coverage


def test_coverage_matches_risk_ids():
    tests = [{"test_id": "T1", "coverage_tags": ["RISK-01"]}]
    understanding = {"risks": [{"risk_id": "RISK-01", "area": "payments"}], "user_journeys": []}
    c = fallback_coverage(tests, understanding)
    assert c.covered_risks == ["RISK-01"]
    assert c.uncovered_risks == []


def test_coverage_flags_uncovered_risks_and_journeys():
    tests = [{"test_id": "T1", "coverage_tags": []}]
    understanding = {
        "risks": [{"risk_id": "RISK-01", "area": "payments"}],
        "user_journeys": [{"journey_id": "JOURNEY-01", "name": "checkout"}],
    }
    c = fallback_coverage(tests, understanding)
    assert c.uncovered_risks == ["RISK-01"]
    assert c.uncovered_journeys == ["JOURNEY-01"]
    assert c.covered_risks == []
    assert c.covered_journeys == []


def test_coverage_empty_inputs():
    c = fallback_coverage([], {})
    assert c.covered_risks == []
    assert c.uncovered_journeys == []
