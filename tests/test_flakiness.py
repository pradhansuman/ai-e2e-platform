"""Tests for flakiness detection."""
from app.agents.flakiness import classify_flaky, detect_flakiness, flakiness_score


def test_stable_sequence_scores_zero():
    assert flakiness_score(["pass", "pass", "pass", "pass"]) == 0.0


def test_alternating_sequence_scores_high():
    seq = ["pass", "fail", "pass", "fail", "pass", "fail", "pass", "fail"]
    score = flakiness_score(seq)
    assert score > 0.5


def test_short_sequence_downweighted():
    assert flakiness_score(["pass", "fail"]) < 0.3


def test_single_run_is_not_flaky():
    assert flakiness_score(["pass"]) == 0.0


def test_classify_flaky():
    assert classify_flaky(0.8) == "flaky"
    assert classify_flaky(0.4) == "intermittent"
    assert classify_flaky(0.1) == "stable"


def test_detect_flakiness_shape():
    result = detect_flakiness([{"status": "pass"}, {"status": "fail"}])
    assert set(result) >= {"flakiness_score", "classification", "total_runs"}
