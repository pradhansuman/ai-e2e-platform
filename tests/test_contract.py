"""Tests for the benchmark result contract + evaluator."""
from benchmark.contract import (
    CONTRACT_VERSION,
    export_result,
    score_result,
    validate_result,
)
from benchmark.engine import Params, run_benchmark


def _valid_result(system="test-system", **metric_overrides):
    m = run_benchmark(Params(total_tests=120, seed=1)).metrics
    m.update(metric_overrides)
    return export_result(system, m, {"tests": 120})


def test_valid_result_passes_validation():
    assert validate_result(_valid_result()) == []


def test_missing_metric_is_flagged():
    r = _valid_result()
    del r["metrics"]["root_cause_accuracy_pct"]
    errs = validate_result(r)
    assert any("root_cause_accuracy_pct" in e for e in errs)


def test_wrong_version_is_flagged():
    r = _valid_result()
    r["benchmark_version"] = "0.9"
    assert any("benchmark_version" in e for e in validate_result(r))


def test_missing_system_is_flagged():
    r = _valid_result()
    del r["system"]
    assert any("system" in e for e in validate_result(r))


def test_score_result_computes_ai_qe():
    r = _valid_result()
    scored = score_result(r)
    assert scored["valid"] is True
    assert 0 <= scored["ai_qe_score"] <= 100
    assert set(scored["dimensions"])  # per-dimension scores present


def test_invalid_result_scores_to_errors():
    r = _valid_result()
    r["metrics"]["defect_detection_pct"] = "not-a-number"
    scored = score_result(r)
    assert scored["valid"] is False
    assert scored["errors"]


def test_export_roundtrips():
    r = _valid_result(system="platform")
    assert r["benchmark_version"] == CONTRACT_VERSION
    assert r["system"] == "platform"
    assert set(r["metrics"]) >= {
        "requirement_coverage_pct",
        "defect_detection_pct",
        "cost_per_test_usd",
    }
