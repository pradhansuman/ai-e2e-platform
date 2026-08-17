"""Tests for the deterministic failure classifier (no LLM required)."""
from app.agents.analyzer import heuristic_classify


def test_timeout_classified_as_timing():
    rc = heuristic_classify({"error": "TimeoutError: locator.wait_for: Timeout 10000ms exceeded"})
    assert rc["classification"] == "timing"


def test_strict_mode_is_automation_defect():
    rc = heuristic_classify({"error": "strict mode violation: locator resolved to 2 elements"})
    assert rc["classification"] == "automation_defect"


def test_assertion_mismatch_is_product_defect():
    rc = heuristic_classify({"steps": [{"error": "Expected text 'X' not found in element"}]})
    assert rc["classification"] == "product_defect"


def test_network_error():
    rc = heuristic_classify({"error": "net::ERR_CONNECTION_REFUSED"})
    assert rc["classification"] == "network"


def test_unknown_fallback():
    rc = heuristic_classify({"error": "something entirely unexpected happened"})
    assert rc["classification"] == "unknown"
    assert rc["confidence"] < 0.3
