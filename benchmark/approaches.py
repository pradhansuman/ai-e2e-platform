"""Control-group baseline — compare approaches on the *same* benchmark.

The whole point of a benchmark is a *control group*. This module compares the
four approaches side by side and — critically — labels each cell **measured**,
**estimated**, or **pending** so fabricated numbers can never masquerade as
measurements:

  A. Human-written automation       — PENDING: protocol published, study not run.
  B. Standard Playwright            — PENDING: independent suite built, run pending.
  C. LLM-generated Playwright       — ESTIMATED: one-shot LLM generation, prior only.
  D. AI E2E Platform (this project) — MEASURED: real deterministic agents.

Healing is reported separately (deterministic fallback vs. Mistral LLM), because
combining them would hide the platform's actual value-add: the LLM heal.
"""

from __future__ import annotations

from typing import Any

from .quality import compute_ai_qe_score

# ---------------------------------------------------------------------------
# Approach profiles. `metrics=None` means "pending — not yet measured"; the row
# renders as "—" rather than a fabricated number.
# ---------------------------------------------------------------------------

APPROACHES: dict[str, dict[str, Any]] = {
    "human": {
        "name": "Human-written automation",
        "short": "Human",
        "measurement": "pending",
        "desc": "Expert QA engineers hand-write and maintain E2E tests.",
        "status_note": (
            "Controlled study protocol published (ai-e2e-benchmark/baselines/human). "
            "No study run yet — metrics are pending, not estimated."
        ),
        "metrics": None,
        "flaky_rate_pct": None,
        "execution_time": "—",
        "human_effort": "high",
    },
    "playwright": {
        "name": "Standard Playwright",
        "short": "Playwright",
        "measurement": "pending",
        "desc": "Scripted E2E automation with no AI; maintainers fix locators.",
        "status_note": (
            "Independent suite built (github.com/pradhansuman/ai-e2e-playwright-baseline). "
            "Not yet run against the mutation corpus — metrics are pending."
        ),
        "metrics": None,
        "flaky_rate_pct": None,
        "execution_time": "—",
        "human_effort": "high (maintenance)",
    },
    "llm": {
        "name": "LLM-generated Playwright (one-shot)",
        "short": "LLM one-shot",
        "measurement": "estimated",
        "desc": "LLM generates tests once; no healing, learning, or flaky detection.",
        "assumptions": (
            "Directional prior, NOT measured: cheap/fast but brittle locators and "
            "lower coverage; every breakage is fixed by a human."
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
        "measurement": "measured",
        "desc": "Closed-loop: generate, execute, diagnose, heal, detect flakiness.",
        "assumptions": (
            "Metrics MEASURED by the benchmark engine (real deterministic agents, "
            "LLM generation simulated). Self-healing here is the deterministic "
            "fallback; the stronger Mistral LLM heal is reported separately."
        ),
        "metrics": None,  # filled from the measured benchmark run
        "flaky_rate_pct": 12.0,
        "execution_time": "seconds (CI, autonomous)",
        "human_effort": "low (autonomous healing)",
    },
}

# ---------------------------------------------------------------------------
# Healing-mode breakdown (never combined into one number).
# ---------------------------------------------------------------------------

HEALING_MODES: list[dict[str, Any]] = [
    {
        "mode": "Deterministic fallback",
        "desc": "heuristic_heal — keyword/attribute matching, no LLM",
        "measurement": "measured",
        "success_pct": 47.3,
        "false_healing_pct": 52.7,
    },
    {
        "mode": "Mistral LLM",
        "desc": "LLM-assisted healing (live pilot, 60 tests)",
        "measurement": "measured",
        "success_pct": 83.3,
        "false_healing_pct": 0.0,
    },
]

COMBINED_POLICY = (
    "LLM-first with deterministic fallback: when an LLM provider is reachable "
    "(Mistral), healing uses the LLM (83.3% success, 0% false-heal); when all "
    "providers are exhausted or unreachable, it falls back to the deterministic "
    "healer (47.3% success, 52.7% false-heal)."
)

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

MEASUREMENT_MARK = {
    "measured": "measured",
    "estimated": "estimated",
    "pending": "pending",
}


def _fmt_metric(key: str, value: float | None) -> str:
    if value is None:
        return "—"
    if key == "avg_diagnosis_time_sec":
        return f"{value:,.0f}s"
    if key == "cost_per_test_usd":
        return f"${value:,.3f}"
    return f"{value:.1f}%"


def build_comparison(platform_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one row per approach, each with metrics + AI-QE score."""
    rows: list[dict[str, Any]] = []
    for key, profile in APPROACHES.items():
        metrics = platform_metrics if key == "platform" else profile["metrics"]
        score = None
        dims = {}
        if metrics is not None:
            score, dims = compute_ai_qe_score(metrics)
        rows.append(
            {
                "key": key,
                "name": profile["name"],
                "short": profile["short"],
                "measurement": profile["measurement"],
                "desc": profile["desc"],
                "status_note": profile.get("status_note"),
                "assumptions": profile.get("assumptions"),
                "flaky_rate_pct": profile["flaky_rate_pct"],
                "execution_time": profile["execution_time"],
                "human_effort": profile["human_effort"],
                "metrics": metrics,
                "ai_qe_score": score,
                "dimensions": dims,
            }
        )
    return rows


def _measurement_header(rows: list[dict[str, Any]]) -> str:
    return (
        "> **Measured / estimated / pending.** "
        + " · ".join(
            f"{r['short']} = {r['measurement']}" for r in rows
        )
        + ". Pending rows are not fabricated — they show “—” until an independent "
          "run fills them in."
    )


def render_comparison_markdown(rows: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    lines.append(_measurement_header(rows))
    lines.append("")
    header = "| Metric | " + " | ".join(r["short"] for r in rows) + " |"
    lines.append(header)
    lines.append("|---|" + "|".join(["---"] * len(rows)) + "|")

    for key in COMPARISON_COLUMNS:
        cells = [
            _fmt_metric(key, r["metrics"][key] if r["metrics"] else None)
            for r in rows
        ]
        lines.append(f"| {COLUMN_LABELS[key]} | " + " | ".join(cells) + " |")

    # Qualitative rows.
    lines.append(
        "| Test flakiness (rate) | "
        + " | ".join(
            f"{r['flaky_rate_pct']:.0f}%" if r["flaky_rate_pct"] is not None else "—"
            for r in rows
        ) + " |"
    )
    lines.append(
        "| Execution time | " + " | ".join(r["execution_time"] for r in rows) + " |"
    )
    lines.append(
        "| Human effort | " + " | ".join(r["human_effort"] for r in rows) + " |"
    )
    lines.append("|---|" + "|".join(["---"] * len(rows)) + "|")
    score_cells = [
        f"**{r['ai_qe_score']:.1f}**" if r["ai_qe_score"] is not None else "—"
        for r in rows
    ]
    lines.append("| **AI-QE Score** | " + " | ".join(score_cells) + " |")
    return "\n".join(lines)


def render_comparison_text(rows: list[dict[str, Any]]) -> str:
    cols = ["Metric"] + [r["short"] for r in rows]
    width = max(24, max(len(c) for c in cols) + 2)
    lines: list[str] = []
    lines.append("Measured/estimated/pending: " + " · ".join(
        f"{r['short']}={r['measurement']}" for r in rows
    ))
    lines.append("")
    lines.append("".join(c.ljust(width) for c in cols))
    lines.append("-" * (width * len(cols)))
    for key in COMPARISON_COLUMNS:
        cells = [COLUMN_LABELS[key]] + [
            _fmt_metric(key, r["metrics"][key] if r["metrics"] else None)
            for r in rows
        ]
        lines.append("".join(c.ljust(width) for c in cells))
    lines.append("-" * (width * len(cols)))
    score_cells = ["AI-QE Score"] + [
        f"{r['ai_qe_score']:.1f}" if r["ai_qe_score"] is not None else "—"
        for r in rows
    ]
    lines.append("".join(c.ljust(width) for c in score_cells))
    return "\n".join(lines)


def render_healing_markdown() -> str:
    lines = [
        "## Healing modes (reported separately)",
        "",
        "> Healing success and false-healing are **never combined** into one "
        "number, because the platform's value-add is the LLM heal.",
        "",
        "| Healing mode | Measurement | Success | False-healing |",
        "|---|---|---|---|",
    ]
    for h in HEALING_MODES:
        lines.append(
            f"| {h['mode']} | {h['measurement']} | {h['success_pct']:.1f}% | "
            f"{h['false_healing_pct']:.1f}% |"
        )
    lines.append("")
    lines.append(f"**Combined policy:** {COMBINED_POLICY}")
    return "\n".join(lines)


def render_healing_text() -> str:
    lines = ["Healing modes (reported separately)", "-" * 40]
    for h in HEALING_MODES:
        lines.append(
            f"{h['mode']:<24} {h['measurement']:<10} "
            f"success={h['success_pct']:.1f}%  false-heal={h['false_healing_pct']:.1f}%"
        )
    lines.append("")
    lines.append(f"Combined policy: {COMBINED_POLICY}")
    return "\n".join(lines)
