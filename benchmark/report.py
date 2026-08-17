"""Benchmark report rendering (markdown + terminal)."""
from __future__ import annotations

from .engine import BenchResult, MUTATIONS
from .quality import compute_ai_qe_score, DIMENSION_LABELS, WEIGHTS


_METRIC_LABELS = {
    "requirement_coverage_pct": "Requirement coverage",
    "test_generation_accuracy_pct": "Test-generation accuracy",
    "defect_detection_pct": "Defect detection (mutation score)",
    "root_cause_accuracy_pct": "Root-cause accuracy",
    "self_healing_success_pct": "Self-healing success",
    "false_healing_rate_pct": "False-healing rate",
    "flaky_detection_accuracy_pct": "Flaky detection accuracy",
    "human_intervention_pct": "Human intervention",
    "avg_diagnosis_time_sec": "Avg diagnosis time",
    "cost_per_test_usd": "Cost per test",
}
_UNITS = {
    "requirement_coverage_pct": "%",
    "test_generation_accuracy_pct": "%",
    "defect_detection_pct": "%",
    "root_cause_accuracy_pct": "%",
    "self_healing_success_pct": "%",
    "false_healing_rate_pct": "%",
    "flaky_detection_accuracy_pct": "%",
    "human_intervention_pct": "%",
    "avg_diagnosis_time_sec": " sec",
    "cost_per_test_usd": "",
}


def render_text(result: BenchResult) -> str:
    lines = ["AI E2E Platform — Benchmark Results", "=" * 40]
    for key, label in _METRIC_LABELS.items():
        unit = _UNITS[key]
        if key == "cost_per_test_usd":
            lines.append(f"{label:<26} ${result.metrics[key]}")
        else:
            lines.append(f"{label:<26} {result.metrics[key]}{unit}")
    score, _dims = compute_ai_qe_score(result.metrics)
    lines.append(f"{'AI-QE Score':<26} {score}/100")
    lines.append("")
    lines.append(f"apps={result.counts['apps']}  workflows={result.counts['workflows']}  "
                 f"tests={result.counts['tests']}  requirements={result.counts['requirements']}")
    return "\n".join(lines)


def render_markdown(result: BenchResult) -> str:
    c = result.counts
    m = result.metrics
    out: list[str] = []
    out.append("# AI E2E Platform — Benchmark Report")
    out.append("")
    out.append(
        f"> Deterministic, seeded baseline (seed `{result.params.seed}`). "
        "Diagnosis / self-healing / flaky-detection numbers are measured against the "
        "**real** deterministic agents; LLM generation is simulated. Re-run with "
        "`python -m benchmark`."
    )
    out.append("")
    out.append("## Headline metrics")
    out.append("")
    out.append("| Metric | Value |")
    out.append("|---|---|")
    for key, label in _METRIC_LABELS.items():
        unit = _UNITS[key]
        if key == "cost_per_test_usd":
            out.append(f"| {label} | ${m[key]} |")
        else:
            out.append(f"| {label} | {m[key]}{unit} |")
    score, dims = compute_ai_qe_score(m)
    out.append(f"| **AI-QE Score** | **{score}/100** |")
    out.append("")
    out.append("## AI-QE Score breakdown")
    out.append("")
    out.append("| Dimension | Weight | Score (0-1) | Weighted |")
    out.append("|---|---|---|---|")
    for key, weight in WEIGHTS.items():
        out.append(
            f"| {DIMENSION_LABELS[key]} | {weight:.0%} | "
            f"{dims[key]:.3f} | {weight * dims[key]:.3f} |"
        )
    out.append("")
    out.append("## Volume")
    out.append("")
    out.append(
        f"- **{c['apps']} applications** across 6 domains "
        f"(e-commerce ×2, banking, forms/widgets, UI patterns, HR/admin)"
    )
    out.append(f"- **{c['workflows']} workflows** (user journeys)")
    out.append(f"- **{c['requirements']} ground-truth requirements**")
    out.append(f"- **{c['tests']} generated tests** "
               f"({c['accurate_tests']} with correct locators)")
    out.append(f"- **{c['failures']} failures** → {c['root_cause_correct']} correctly classified, "
               f"{c['heal_attempts']} self-healing attempts, {c['flaky_injected']} flaky tests")
    out.append("")
    out.append("## Per-application")
    out.append("")
    out.append("| App | Domain | Tests | Passed | Failed | Heals |")
    out.append("|---|---|---|---|---|---|")
    for a in result.per_app:
        out.append(
            f"| {a['name']} | {a['domain']} | {a['tests']} | "
            f"{a['passed']} | {a['failed']} | {a['heals']} |"
        )
    out.append("")
    out.append("## Cost")
    out.append("")
    out.append(f"- Total estimated LLM cost: **${c['total_cost_usd']}** "
               f"(blended ${result.params.cost_input_per_1m}/M in, "
               f"${result.params.cost_output_per_1m}/M out)")
    out.append(f"- Cost per test: **${m['cost_per_test_usd']}**")
    out.append("")
    out.append("## Mutation corpus")
    out.append("")
    out.append(
        "Ten injected mutation classes with known ground-truth labels. The "
        "mutation score measures **fault-detection power**: the fraction of "
        "injected defects the generated tests actually *catch* (fail on)."
    )
    out.append("")
    out.append("| Mutation | Class | Injected | Caught | Detection |")
    out.append("|---|---|---|---|---|")
    for key in sorted(c["mutation_breakdown"]):
        label = key.replace("_", " ").capitalize()
        cls = MUTATIONS[key]["classification"]
        injected = c["mutation_breakdown"][key]
        caught = c["mutation_caught_breakdown"].get(key, 0)
        acc = caught / injected * 100 if injected else 0.0
        out.append(f"| {label} | `{cls}` | {injected} | {caught} | {acc:.0f}% |")
    out.append("")
    out.append("## Method")
    out.append("")
    out.append(
        "Mutations are injected with known ground-truth labels, then the platform "
        "is scored on how well it recovers:"
    )
    out.append("")
    out.append(
        "1. **Product defects** (value / validation / API response / business rule / "
        "calculation change) → must be classified `product_defect` and escalated, never healed."
    )
    out.append(
        "2. **Automation defects** (broken locator, requirement change) → `automation_defect` → self-heal to the correct element."
    )
    out.append(
        "3. **Auth change** → `authentication` (security regression, not a locator fix)."
    )
    out.append(
        "4. **Timing issue** → `timing` (wait/race, not a product bug)."
    )
    out.append(
        "5. **Flaky tests** (alternating pass/fail) → detected by history scoring, not healed."
    )
    out.append("")
    return "\n".join(out)
