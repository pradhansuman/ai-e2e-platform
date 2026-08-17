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


def test_pipeline_detects_flaky_from_history():
    from app.graph.nodes import _detect_flaky

    state = {
        "execution_results": [
            {"test_id": "T-1", "status": s, "duration_ms": 100}
            for s in ("passed", "failed") * 4  # 8 runs, strongly alternating
        ]
    }
    rc = _detect_flaky(state, "T-1")
    assert rc is not None
    assert rc["classification"] == "flaky"
    assert "recommended_fix" in rc


def test_pipeline_flaky_needs_enough_history():
    from app.graph.nodes import _detect_flaky

    state = {"execution_results": [{"test_id": "T-1", "status": "failed", "duration_ms": 200}]}
    assert _detect_flaky(state, "T-1") is None  # too few observations
    assert _detect_flaky(state, None) is None  # no test id
