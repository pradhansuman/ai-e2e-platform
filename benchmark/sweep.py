"""Sensitivity sweep — how does the AI-QE score respond to assumptions?

Runs the benchmark across a grid of the two key generator-capability priors
(assertion quality = fault-detection power, and generation accuracy = locator
correctness) so the score's sensitivity to these assumptions is transparent.

Run:  PYTHONPATH=backend python -m benchmark --sweep
"""
from __future__ import annotations

from typing import Any, Iterable

from .engine import Params, run_benchmark
from .quality import compute_ai_qe_score


def run_sweep(
    seed: int = 42,
    assertion_qualities: Iterable[float] = (0.70, 0.80, 0.90),
    gen_accuracies: Iterable[float] = (0.80, 0.86, 0.92),
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for gen in gen_accuracies:
        for aq in assertion_qualities:
            params = Params(seed=seed, gen_accuracy=gen, assertion_quality=aq)
            r = run_benchmark(params)
            score, _ = compute_ai_qe_score(r.metrics)
            rows.append(
                {
                    "assertion_quality": aq,
                    "gen_accuracy": gen,
                    "defect_detection_pct": r.metrics["defect_detection_pct"],
                    "root_cause_accuracy_pct": r.metrics["root_cause_accuracy_pct"],
                    "self_healing_success_pct": r.metrics["self_healing_success_pct"],
                    "ai_qe_score": score,
                }
            )
    return rows


def _matrix(rows: list[dict[str, Any]], metric: str) -> str:
    aqs = sorted({r["assertion_quality"] for r in rows})
    gens = sorted({r["gen_accuracy"] for r in rows})
    by = {(r["assertion_quality"], r["gen_accuracy"]): r[metric] for r in rows}
    lines = [f"{metric}:"]
    header = "assertion-qty \\ gen-acc | " + " | ".join(f"{g:.2f}" for g in gens)
    lines.append(header)
    lines.append("-" * len(header))
    for aq in aqs:
        cells = [f"{by[(aq, g)]:.1f}" for g in gens]
        lines.append(f"{aq:.2f}" + " " * 12 + " | " + " | ".join(cells))
    return "\n".join(lines)


def render_text(rows: list[dict[str, Any]]) -> str:
    out = ["Sensitivity sweep (seed fixed)", "=" * 40, ""]
    for metric, label in (
        ("ai_qe_score", "AI-QE Score"),
        ("defect_detection_pct", "Defect detection %"),
        ("root_cause_accuracy_pct", "Root-cause accuracy %"),
        ("self_healing_success_pct", "Self-healing success %"),
    ):
        # _matrix uses the metric key; label it separately.
        block = _matrix(rows, metric).split("\n")
        block[0] = label
        out.extend(block)
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def render_markdown(rows: list[dict[str, Any]]) -> str:
    aqs = sorted({r["assertion_quality"] for r in rows})
    gens = sorted({r["gen_accuracy"] for r in rows})
    by = {(r["assertion_quality"], r["gen_accuracy"]): r for r in rows}

    lines = ["# Benchmark sensitivity sweep", ""]
    lines.append(
        "> How the AI-QE Score responds to the two generator-capability priors "
        "(assertion quality = fault-detection power, generation accuracy = locator "
        "correctness). Fixed seed; deterministic."
    )
    lines.append("")

    for metric, label in (
        ("ai_qe_score", "AI-QE Score"),
        ("defect_detection_pct", "Defect detection %"),
        ("root_cause_accuracy_pct", "Root-cause accuracy %"),
        ("self_healing_success_pct", "Self-healing success %"),
    ):
        lines.append(f"## {label}")
        lines.append("")
        lines.append("| assertion-qty \\ gen-acc | " + " | ".join(f"{g:.2f}" for g in gens) + " |")
        lines.append("|---|" + "|".join(["---"] * len(gens)) + "|")
        for aq in aqs:
            cells = [f"{by[(aq, g)][metric]:.1f}" for g in gens]
            lines.append(f"| {aq:.2f} | " + " | ".join(cells) + " |")
        lines.append("")
    return "\n".join(lines)
