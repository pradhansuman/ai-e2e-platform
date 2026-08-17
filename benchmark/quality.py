"""AI-QE Score — a weighted composite of the benchmark's raw metrics.

The score collapses the benchmark's raw metrics into a single 0-100 number
tracked over time, using business-weighted dimensions rather than a blind
average. Weights follow the reference weighting from the project brief:

    Defect Detection        20%
    Requirement Coverage    15%
    Root Cause Accuracy     15%
    Test Quality            15%
    Self-Healing            10%
    Reliability             10%
    Flaky Detection          5%
    Human Intervention       5%
    Cost Efficiency          5%
                           ----
                           100%

Every dimension is normalized to a 0-1 score where *higher is better*.
Dimensions whose raw metric is "lower is better" (human intervention, cost,
false-healing) are inverted.

Definitions (keep these stable so the score is comparable across runs):

  * defect_detection   — mutation score (fault-detection power): injected
                         mutations the generated tests caught / total injected.
  * requirement_coverage — fraction of ground-truth requirements covered.
  * root_cause_accuracy — correct diagnosis of deterministic failures.
  * test_quality       — generated tests whose locator+assertion is correct.
  * self_healing       — broken-locator heals that recovered the intent.
  * reliability        — 1 - false-healing rate (heals that did NOT corrupt).
  * flaky_detection    — flaky runs correctly flagged as flaky.
  * human_intervention — 1 - fraction of failures needing a human.
  * cost_efficiency    — 1 / (1 + cost_per_test_usd), a saturating inverse.
"""

from __future__ import annotations

from typing import Any

WEIGHTS: dict[str, float] = {
    "defect_detection": 0.20,
    "requirement_coverage": 0.15,
    "root_cause_accuracy": 0.15,
    "test_quality": 0.15,
    "self_healing": 0.10,
    "reliability": 0.10,
    "flaky_detection": 0.05,
    "human_intervention": 0.05,
    "cost_efficiency": 0.05,
}

# Human-readable labels for each dimension (report/table rendering).
DIMENSION_LABELS: dict[str, str] = {
    "defect_detection": "Defect Detection",
    "requirement_coverage": "Requirement Coverage",
    "root_cause_accuracy": "Root Cause Accuracy",
    "test_quality": "Test Quality",
    "self_healing": "Self-Healing",
    "reliability": "Reliability",
    "flaky_detection": "Flaky Detection",
    "human_intervention": "Human Intervention",
    "cost_efficiency": "Cost Efficiency",
}


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def dimension_scores(m: dict[str, Any]) -> dict[str, float]:
    """Map a raw metric vector to per-dimension 0-1 scores (higher = better)."""
    return {
        "defect_detection": _clamp(m["defect_detection_pct"] / 100.0),
        "requirement_coverage": _clamp(m["requirement_coverage_pct"] / 100.0),
        "root_cause_accuracy": _clamp(m["root_cause_accuracy_pct"] / 100.0),
        "test_quality": _clamp(m["test_generation_accuracy_pct"] / 100.0),
        "self_healing": _clamp(m["self_healing_success_pct"] / 100.0),
        "reliability": _clamp(1.0 - m["false_healing_rate_pct"] / 100.0),
        "flaky_detection": _clamp(m["flaky_detection_accuracy_pct"] / 100.0),
        "human_intervention": _clamp(1.0 - m["human_intervention_pct"] / 100.0),
        "cost_efficiency": _clamp(1.0 / (1.0 + m["cost_per_test_usd"])),
    }


def compute_ai_qe_score(m: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """Return (score 0-100, per-dimension 0-1 scores)."""
    dims = dimension_scores(m)
    total = sum(WEIGHTS[k] * v for k, v in dims.items())
    return round(total * 100.0, 1), dims
