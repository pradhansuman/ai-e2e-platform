"""Risk-based Test Prioritization (spec section 6).

Deterministic + explainable: each test is scored on six factors and mapped to
P0-P3. Deterministic scoring is preferred over pure LLM judgment here because
prioritization must be reproducible, auditable, and cheap to run at CI scale.
"""
from __future__ import annotations

from typing import Any

_FACTORS = (
    "business_impact",
    "failure_probability",
    "change_frequency",
    "user_traffic",
    "technical_complexity",
    "historical_failures",
)

# Default weights (sum to 1.0). Overridable per application.
DEFAULT_WEIGHTS = {
    "business_impact": 0.30,
    "failure_probability": 0.25,
    "change_frequency": 0.10,
    "user_traffic": 0.10,
    "technical_complexity": 0.10,
    "historical_failures": 0.15,
}


def _factor_value(test: dict[str, Any], factor: str) -> float:
    """Read a 0-1 factor value from a test case (or infer from its tags)."""
    explicit = test.get(factor)
    if isinstance(explicit, (int, float)):
        return float(explicit)
    # Heuristics fall back to risk tag.
    risk = str(test.get("risk", "medium")).lower()
    risk_map = {"low": 0.2, "medium": 0.5, "high": 0.8, "critical": 1.0}
    return risk_map.get(risk, 0.5)


def score_test(test: dict[str, Any], weights: dict[str, float] | None = None) -> float:
    weights = weights or DEFAULT_WEIGHTS
    return sum(_factor_value(test, f) * w for f, w in weights.items())


def to_priority(score: float) -> str:
    if score >= 0.8:
        return "P0"
    if score >= 0.6:
        return "P1"
    if score >= 0.4:
        return "P2"
    return "P3"


def prioritize_tests(
    tests: list[dict[str, Any]],
    history: dict[str, float] | None = None,
    weights: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Score, assign priority, and sort tests descending by score.

    ``history`` maps test_id -> historical failure rate (0-1), folded into the
    ``historical_failures`` factor when not already set.
    """
    history = history or {}
    prioritized: list[dict[str, Any]] = []
    for test in tests:
        t = dict(test)
        if "historical_failures" not in t and t.get("test_id") in history:
            t["historical_failures"] = history[t["test_id"]]
        score = score_test(t, weights)
        t["priority_score"] = round(score, 4)
        t["priority"] = to_priority(score)
        prioritized.append(t)
    prioritized.sort(key=lambda x: x["priority_score"], reverse=True)
    return prioritized
