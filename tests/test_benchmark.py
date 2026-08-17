"""Tests for the benchmark harness."""
from benchmark.apps import APPS, total_requirements, total_workflows
from benchmark.approaches import build_comparison, render_comparison_markdown
from benchmark.engine import Params, run_benchmark
from benchmark.quality import compute_ai_qe_score


def test_six_apps_defined():
    assert len(APPS) == 6
    assert all(a["requirements"] and a["workflows"] and a["elements"] for a in APPS)


def test_workflow_and_requirement_volume():
    assert total_workflows() >= 50
    assert total_requirements() >= 60


def test_benchmark_produces_all_metrics():
    result = run_benchmark(Params(total_tests=120, seed=1))
    expected = {
        "requirement_coverage_pct",
        "test_generation_accuracy_pct",
        "defect_detection_pct",
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
        "defect_detection_pct",
        "root_cause_accuracy_pct",
        "self_healing_success_pct",
        "false_healing_rate_pct",
        "flaky_detection_accuracy_pct",
        "human_intervention_pct",
    ):
        assert 0 <= m[key] <= 100, key
    assert m["avg_diagnosis_time_sec"] >= 0
    assert m["cost_per_test_usd"] >= 0


def test_ai_qe_score_in_range():
    m = run_benchmark(Params(total_tests=120, seed=3)).metrics
    score, dims = compute_ai_qe_score(m)
    assert 0 <= score <= 100
    # weights sum to 1
    from benchmark.quality import WEIGHTS
    assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9
    # every dimension is a 0-1 score
    assert all(0 <= v <= 1 for v in dims.values())


def test_comparison_has_four_rows_and_score():
    m = run_benchmark(Params(total_tests=120, seed=3)).metrics
    rows = build_comparison(m)
    assert len(rows) == 4
    assert {r["key"] for r in rows} == {"human", "playwright", "llm", "platform"}
    # the platform row carries the measured metrics
    platform = next(r for r in rows if r["key"] == "platform")
    assert platform["metrics"] == m
    assert all(0 <= r["ai_qe_score"] <= 100 for r in rows)
    # markdown renders without error and includes the score row
    md = render_comparison_markdown(rows)
    assert "AI-QE Score" in md


def test_mutation_breakdown_is_consistent():
    r = run_benchmark(Params(total_tests=200, seed=5))
    c = r.counts
    # breakdown sums to the injected/caught totals
    assert sum(c["mutation_breakdown"].values()) == c["mutations_injected"]
    assert sum(c["mutation_caught_breakdown"].values()) == c["mutations_caught"]
    # flaky is excluded from the mutation (fault-detection) score
    assert "flaky" not in c["mutation_breakdown"]
    assert c["mutations_injected"] > 0
    # fault-detection power is strictly between 0 and 100% (some mutations missed)
    assert 0 < c["mutations_caught"] < c["mutations_injected"]
    # defect_detection_pct == caught / injected
    expected = round(c["mutations_caught"] / c["mutations_injected"] * 100, 1)
    assert r.metrics["defect_detection_pct"] == expected
