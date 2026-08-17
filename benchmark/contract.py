"""Benchmark result contract + standard evaluator (Phase 3 architecture).

A standardized submission format (``benchmark-result.json``) so the scoring
engine is agnostic to *who* generated the tests — a human, a conventional
Playwright suite, or the AI platform. The evaluator validates a submission and
computes the AI-QE Score from it, so external baselines are never conflated
with fabricated estimates: they are either submitted and measured, or marked
pending.

CLI:
    python -m benchmark.contract human/result.json playwright/result.json ...
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .quality import compute_ai_qe_score

CONTRACT_VERSION = "1.0"

REQUIRED_METRICS = (
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
)

# Whether a metric is measured directly or is a declared estimate.
ESTIMATABLE_METRICS = frozenset({
    "requirement_coverage_pct",
    "test_generation_accuracy_pct",
    "human_intervention_pct",
    "avg_diagnosis_time_sec",
    "cost_per_test_usd",
})


def validate_result(data: dict[str, Any]) -> list[str]:
    """Return a list of validation errors (empty == valid)."""
    errors: list[str] = []
    if data.get("benchmark_version") != CONTRACT_VERSION:
        errors.append(
            f"benchmark_version must be {CONTRACT_VERSION!r} (got {data.get('benchmark_version')!r})"
        )
    if not data.get("system"):
        errors.append("missing 'system' identifier")
    metrics = data.get("metrics")
    if not isinstance(metrics, dict):
        errors.append("'metrics' must be an object")
        return errors
    for key in REQUIRED_METRICS:
        if key not in metrics:
            errors.append(f"missing metric {key!r}")
        elif not isinstance(metrics[key], (int, float)):
            errors.append(f"metric {key!r} must be numeric")
    return errors


def score_result(data: dict[str, Any]) -> dict[str, Any]:
    """Validate a submission and compute its AI-QE Score (0-100)."""
    errors = validate_result(data)
    if errors:
        return {"system": data.get("system"), "valid": False, "errors": errors}
    metrics = data["metrics"]
    score, dims = compute_ai_qe_score(metrics)
    return {
        "system": data.get("system"),
        "valid": True,
        "ai_qe_score": score,
        "dimensions": dims,
        "metrics": metrics,
        "counts": data.get("counts", {}),
    }


def load_result(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text())


def export_result(
    system: str,
    metrics: dict[str, Any],
    counts: dict[str, Any] | None = None,
    *,
    benchmark_version: str = CONTRACT_VERSION,
) -> dict[str, Any]:
    """Build a benchmark-result.json submission from a platform's own metrics."""
    return {
        "benchmark_version": benchmark_version,
        "system": system,
        "metrics": dict(metrics),
        "counts": dict(counts or {}),
        "execution": {
            "environment": "deterministic-sim",
        },
    }


def compare_files(paths: list[str]) -> list[dict[str, Any]]:
    """Load + score multiple result files."""
    return [score_result(load_result(p)) for p in paths]


def render_comparison(rows: list[dict[str, Any]]) -> str:
    lines = ["System".ljust(24) + "AI-QE Score" + "  status"]
    lines.append("-" * 48)
    for r in rows:
        if r["valid"]:
            lines.append(
                r["system"].ljust(24) + f"{r['ai_qe_score']:6.1f}" + "  measured"
            )
        else:
            lines.append(
                r["system"].ljust(24) + "  n/a" + "  INVALID: " + "; ".join(r["errors"])
            )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m benchmark.contract")
    parser.add_argument("files", nargs="+", help="benchmark-result.json files to score")
    args = parser.parse_args(argv)
    rows = compare_files(args.files)
    print(render_comparison(rows))
    return 0 if all(r["valid"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
