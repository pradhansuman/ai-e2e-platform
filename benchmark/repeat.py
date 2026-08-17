"""Repeated-run statistics (Phase 3: confidence intervals).

Runs the benchmark across multiple seeds and reports mean ± std for each metric
and the AI-QE Score, so reported numbers carry a dispersion estimate instead of
a single point estimate.

CLI:  python -m benchmark --repeat 30
"""
from __future__ import annotations

import statistics
from typing import Any

from .engine import Params, run_benchmark
from .quality import compute_ai_qe_score


def run_repeated(
    n: int = 30, *, base_seed: int = 0, **params_overrides: Any
) -> dict[str, Any]:
    """Run the benchmark ``n`` times with distinct seeds and aggregate."""
    metric_samples: dict[str, list[float]] = {}
    score_samples: list[float] = []
    for i in range(n):
        params = Params(seed=base_seed + i, **params_overrides)
        r = run_benchmark(params)
        for k, v in r.metrics.items():
            metric_samples.setdefault(k, []).append(v)
        score, _ = compute_ai_qe_score(r.metrics)
        score_samples.append(score)

    def _agg(samples: list[float]) -> dict[str, float]:
        return {
            "mean": round(statistics.mean(samples), 2),
            "stdev": round(statistics.stdev(samples), 2) if len(samples) > 1 else 0.0,
            "min": round(min(samples), 2),
            "max": round(max(samples), 2),
        }

    metrics = {k: _agg(v) for k, v in sorted(metric_samples.items())}
    return {
        "runs": n,
        "ai_qe_score": _agg(score_samples),
        "metrics": metrics,
    }


def render_text(agg: dict[str, Any]) -> str:
    lines = [f"Repeated benchmark runs (n={agg['runs']})", "=" * 40, ""]
    s = agg["ai_qe_score"]
    lines.append(
        f"AI-QE Score      mean={s['mean']:.2f}  ±{s['stdev']:.2f}  "
        f"[{s['min']:.1f}, {s['max']:.1f}]"
    )
    lines.append("")
    for key, a in agg["metrics"].items():
        lines.append(
            f"{key:<26} mean={a['mean']:.2f}  ±{a['stdev']:.2f}"
        )
    return "\n".join(lines)


def render_markdown(agg: dict[str, Any]) -> str:
    s = agg["ai_qe_score"]
    out = ["# Benchmark repeatability", ""]
    out.append(f"**AI-QE Score** (n={agg['runs']}): "
               f"**{s['mean']:.2f} ± {s['stdev']:.2f}** "
               f"[{s['min']:.1f}–{s['max']:.1f}]")
    out.append("")
    out.append("| Metric | Mean | Stdev |")
    out.append("|---|---|---|")
    for key, a in agg["metrics"].items():
        out.append(f"| {key} | {a['mean']:.2f} | {a['stdev']:.2f} |")
    return "\n".join(out)
