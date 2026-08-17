"""Control-group baseline — compare 4 approaches on the *same* benchmark.

The whole point of a benchmark is a *control group*. A single platform's
numbers ("root-cause accuracy = 92%") are meaningless without answering
"92% compared with what?". This module runs the four approaches side by side:

  A. Human-written automation       — expert QA engineers, fully manual.
  B. Standard Playwright            — scripted E2E, no AI, manual maintenance.
  C. LLM-generated Playwright       — one-shot LLM generation, no heal loop.
  D. AI E2E Platform (this project) — closed-loop: gen + heal + flaky detect.

The platform row (D) is *measured* by the benchmark engine (real deterministic
agents). Rows A-C are *parameterized estimates* — clearly labeled — grounded in
reasonable industry assumptions. They are not measured and should be treated as
directional priors, not ground truth.

Each approach produces the same metric vector, so the AI-QE score is computed
identically for all four and is directly comparable.
"""

from __future__ import annotations

from typing import Any

from .quality import compute_ai_qe_score

# ---------------------------------------------------------------------------
# Approach profiles. The `metrics` dict mirrors the benchmark engine's output
# shape exactly, so `compute_ai_qe_score` works on any of them.
# ---------------------------------------------------------------------------

APPROACHES: dict[str, dict[str, Any]] = {
    "human": {
        "name": "Human-written automation",
        "short": "Human",
        "desc": "Expert QA engineers hand-write and maintain E2E tests.",
        "assumptions": (
            "High coverage/quality from domain expertise; no self-healing or "
            "flaky detection (everything is manual); expensive and slow."
        ),
        "metrics": {
            "requirement_coverage_pct": 94.0,
            "test_generation_accuracy_pct": 96.0,
            "defect_detection_pct": 92.0,
            "root_cause_accuracy_pct": 95.0,
            "self_healing_success_pct": 0.0,
            "false_healing_rate_pct": 0.0,
            "flaky_detection_accuracy_pct": 0.0,
            "human_intervention_pct": 100.0,
            "avg_diagnosis_time_sec": 1200.0,
            "cost_per_test_usd": 4.50,
        },
        "flaky_rate_pct": 8.0,
        "execution_time": "hours (manual triage)",
        "human_effort": "high",
    },
    "playwright": {
        "name": "Standard Playwright",
        "short": "Playwright",
        "desc": "Scripted E2E automation with no AI; maintainers fix locators.",
        "assumptions": (
            "Precise hand-written locators; no automated healing or flaky "
            "detection; medium cost; high maintenance burden."
        ),
        "metrics": {
            "requirement_coverage_pct": 90.0,
            "test_generation_accuracy_pct": 95.0,
            "defect_detection_pct": 88.0,
            "root_cause_accuracy_pct": 92.0,
            "self_healing_success_pct": 0.0,
            "false_healing_rate_pct": 0.0,
            "flaky_detection_accuracy_pct": 0.0,
            "human_intervention_pct": 90.0,
            "avg_diagnosis_time_sec": 300.0,
            "cost_per_test_usd": 1.20,
        },
        "flaky_rate_pct": 15.0,
        "execution_time": "minutes (CI)",
        "human_effort": "high (maintenance)",
    },
    "llm": {
        "name": "LLM-generated Playwright (one-shot)",
        "short": "LLM one-shot",
        "desc": "LLM generates tests once; no healing, learning, or flaky detection.",
        "assumptions": (
            "Cheap and fast but brittle locators and lower coverage; every "
            "breakage is fixed by a human."
        ),
        "metrics": {
            "requirement_coverage_pct": 80.0,
            "test_generation_accuracy_pct": 85.0,
            "defect_detection_pct": 75.0,
            "root_cause_accuracy_pct": 88.0,
            "self_healing_success_pct": 0.0,
            "false_healing_rate_pct": 0.0,
            "flaky_detection_accuracy_pct": 0.0,
            "human_intervention_pct": 60.0,
            "avg_diagnosis_time_sec": 30.0,
            "cost_per_test_usd": 0.008,
        },
        "flaky_rate_pct": 22.0,
        "execution_time": "seconds (CI)",
        "human_effort": "medium (review + fix)",
    },
    "platform": {
        "name": "AI E2E Platform (this project)",
        "short": "This platform",
        "desc": "Closed-loop: generate, execute, diagnose, heal, detect flakiness.",
        "assumptions": (
            "Metrics MEASURED by the benchmark engine (real deterministic agents, "
            "LLM generation simulated). Healing is the deterministic fallback, "
            "not the LLM heal — so self-healing is a lower bound."
        ),
        "metrics": None,  # filled from the measured benchmark run
        "flaky_rate_pct": 12.0,  # estimate: flaky detection reduces effective flakiness
        "execution_time": "seconds (CI, autonomous)",
        "human_effort": "low (autonomous healing)",
    },
}

# Column order for the comparison table.
COMPARISON_COLUMNS = [
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
]

COLUMN_LABELS = {
    "requirement_coverage_pct": "Coverage",
    "test_generation_accuracy_pct": "Test quality",
    "defect_detection_pct": "Defect detection",
    "root_cause_accuracy_pct": "Root-cause accuracy",
    "self_healing_success_pct": "Self-healing",
    "false_healing_rate_pct": "False-healing",
    "flaky_detection_accuracy_pct": "Flaky detection",
    "human_intervention_pct": "Human intervention",
    "avg_diagnosis_time_sec": "Avg diagnosis time",
    "cost_per_test_usd": "Cost / test",
}


def _fmt_metric(key: str, value: float) -> str:
    if key == "avg_diagnosis_time_sec":
        return f"{value:,.0f}s"
    if key == "cost_per_test_usd":
        return f"${value:,.3f}"
    return f"{value:.1f}%"


def build_comparison(platform_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one row per approach, each with metrics + AI-QE score."""
    rows: list[dict[str, Any]] = []
    for key, profile in APPROACHES.items():
        metrics = (
            platform_metrics if key == "platform" else dict(profile["metrics"])
        )
        score, dims = compute_ai_qe_score(metrics)
        rows.append(
            {
                "key": key,
                "name": profile["name"],
                "short": profile["short"],
                "desc": profile["desc"],
                "assumptions": profile["assumptions"],
                "flaky_rate_pct": profile["flaky_rate_pct"],
                "execution_time": profile["execution_time"],
                "human_effort": profile["human_effort"],
                "metrics": metrics,
                "ai_qe_score": score,
                "dimensions": dims,
            }
        )
    return rows


def render_comparison_markdown(rows: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append(
        "> **Measured vs estimated.** The \"This platform\" row is measured by the "
        "benchmark engine (real deterministic agents). Human / Playwright / LLM rows are "
        "parameterized estimates (directional priors, not measured ground truth). "
        "AI-QE Score uses business weights (defect detection 20%, coverage/root-cause/test-quality "
        "15% each, self-healing/reliability 10% each, flaky-detection/intervention/cost 5% each)."
    )
    lines.append("")
    header = "| Metric | " + " | ".join(
        r["short"] for r in rows
    ) + " |"
    lines.append(header)
    lines.append("|---|" + "|".join(["---"] * len(rows)) + "|")

    for key in COMPARISON_COLUMNS:
        cells = [
            _fmt_metric(key, r["metrics"][key])
            for r in rows
        ]
        lines.append(f"| {COLUMN_LABELS[key]} | " + " | ".join(cells) + " |")

    # Qualitative rows.
    lines.append(
        "| Test flakiness (rate) | "
        + " | ".join(f"{r['flaky_rate_pct']:.0f}%" for r in rows) + " |"
    )
    lines.append(
        "| Execution time | " + " | ".join(r["execution_time"] for r in rows) + " |"
    )
    lines.append(
        "| Human effort | " + " | ".join(r["human_effort"] for r in rows) + " |"
    )
    lines.append("|---|" + "|".join(["---"] * len(rows)) + "|")
    lines.append(
        "| **AI-QE Score** | "
        + " | ".join(f"**{r['ai_qe_score']:.1f}**" for r in rows) + " |"
    )
    return "\n".join(lines)


def render_comparison_text(rows: list[dict[str, Any]]) -> str:
    cols = ["Metric"] + [r["short"] for r in rows]
    width = max(24, max(len(c) for c in cols) + 2)
    lines: list[str] = []
    lines.append("".join(c.ljust(width) for c in cols))
    lines.append("-" * (width * len(cols)))
    for key in COMPARISON_COLUMNS:
        cells = [COLUMN_LABELS[key]] + [
            _fmt_metric(key, r["metrics"][key]) for r in rows
        ]
        lines.append("".join(c.ljust(width) for c in cells))
    lines.append("-" * (width * len(cols)))
    score_cells = ["AI-QE Score"] + [f"{r['ai_qe_score']:.1f}" for r in rows]
    lines.append("".join(c.ljust(width) for c in score_cells))
    return "\n".join(lines)
