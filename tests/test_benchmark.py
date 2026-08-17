"""Tests for the benchmark harness."""
from benchmark.apps import APPS, total_requirements, total_workflows
from benchmark.engine import Params, run_benchmark


def test_six_apps_defined():
    assert len(APPS) == 6
    assert all(a["requirements"] and a["workflows"] and a["elements"] for a in APPS)


def test_workflow_and_requirement_volume():
    assert total_workflows() >= 50
    assert total_requirements() >= 60


def test_benchmark_produces_nine_metrics():
    result = run_benchmark(Params(total_tests=120, seed=1))
    expected = {
        "requirement_coverage_pct",
        "test_generation_accuracy_pct",
        "root_cause_accuracy_pct",
        "self_healing_success_pct",
        "false_healing_rate_pct",
        "flaky_detection_accuracy_pct",
        "human_intervention_pct",
        "avg_diagnosis_time_sec",
        "cost_per_test_usd",
    }
    assert set(result.metrics) == expected
    assert result.counts["tests"] == 120


def test_benchmark_is_reproducible():
    a = run_benchmark(Params(total_tests=120, seed=7))
    b = run_benchmark(Params(total_tests=120, seed=7))
    assert a.metrics == b.metrics
    assert a.counts == b.counts


def test_metric_ranges_are_sane():
    r = run_benchmark(Params(total_tests=120, seed=3))
    m = r.metrics
    for key in (
        "requirement_coverage_pct",
        "test_generation_accuracy_pct",
        "root_cause_accuracy_pct",
        "self_healing_success_pct",
        "false_healing_rate_pct",
        "flaky_detection_accuracy_pct",
        "human_intervention_pct",
    ):
        assert 0 <= m[key] <= 100, key
    assert m["avg_diagnosis_time_sec"] >= 0
    assert m["cost_per_test_usd"] >= 0
