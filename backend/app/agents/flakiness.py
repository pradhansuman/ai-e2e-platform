"""Flaky Test Detection (spec section 10).

Deterministic flakiness scoring from historical execution sequences
(PASS/FAIL/PASS/FAIL patterns) plus suspected-cause inference.
"""
from __future__ import annotations

from typing import Any

_CAUSES = (
    "timing",
    "race_condition",
    "network_instability",
    "environment_instability",
    "test_data_collision",
    "external_dependency",
    "browser_issue",
    "unknown",
)


_STATUS_NORMALIZE = {
    "passed": "pass",
    "pass": "pass",
    "failed": "fail",
    "fail": "fail",
    "error": "fail",
}


def flakiness_score(sequence: list[str]) -> float:
    """Compute a 0-1 flakiness score from a pass/fail sequence.

    A perfectly stable test (all same) scores 0; a maximally alternating
    sequence scores 1. Short sequences are down-weighted to avoid overfitting
    a single flip. Accepts both ``pass/fail`` and ``passed/failed`` statuses
    (the executor emits the latter).
    """
    seq = [_STATUS_NORMALIZE.get(s.lower(), s.lower()) for s in sequence]
    seq = [s for s in seq if s in {"pass", "fail"}]
    n = len(seq)
    if n < 2:
        return 0.0

    flips = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    max_flips = n - 1
    base = flips / max_flips if max_flips else 0.0

    # Confidence weighting: longer histories are more trustworthy.
    confidence = min(1.0, n / 10.0)
    return round(base * confidence, 4)


def classify_flaky(score: float) -> str:
    if score >= 0.6:
        return "flaky"
    if score >= 0.3:
        return "intermittent"
    return "stable"


def detect_flakiness(history: list[dict[str, Any]]) -> dict[str, Any]:
    """Given a test's execution history, return score, class, and suspected cause."""
    sequence = [h.get("status", "") for h in history]
    score = flakiness_score(sequence)
    return {
        "flakiness_score": score,
        "classification": classify_flaky(score),
        "total_runs": len(sequence),
        "pass_fail_sequence": sequence,
        "suspected_cause": _suspect_cause(history, score),
    }


def _suspect_cause(history: list[dict[str, Any]], score: float) -> str:
    if score < 0.3:
        return "none"
    # Simple heuristics; richer inference is delegated to the failure agent.
    durations = [h.get("duration_ms") for h in history if isinstance(h.get("duration_ms"), int)]
    if durations and max(durations) - min(durations) > 2 * (sum(durations) / len(durations)):
        return "timing"
    return "unknown"
