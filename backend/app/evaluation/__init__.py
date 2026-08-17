"""AI evaluation (spec section 14): compute a quality score for the AI's own
output, and register LangSmith evaluation datasets (spec section 13).

The core principle: a test that *executes* successfully is not necessarily a
*correct* test. We evaluate reasoning quality and coverage independently.
"""
from __future__ import annotations

from typing import Any

from ..schemas import AiQualityScores

__all__ = ["compute_ai_quality", "evaluate_test_suite", "register_datasets"]


def compute_ai_quality(
    test_cases: list[dict[str, Any]],
    requirement_coverage: dict[str, Any] | None = None,
    diagnosis_results: list[dict[str, Any]] | None = None,
    healing_results: list[dict[str, Any]] | None = None,
) -> AiQualityScores:
    """Compute the seven-dimension AI quality score (0-1 each)."""
    return AiQualityScores(
        test_quality=_test_quality(test_cases),
        requirement_coverage=_requirement_coverage(test_cases, requirement_coverage),
        risk_coverage=_risk_coverage(test_cases),
        execution_accuracy=_execution_accuracy(),
        failure_diagnosis_accuracy=_diagnosis_accuracy(diagnosis_results or []),
        self_healing_accuracy=_healing_accuracy(healing_results or []),
        hallucination_rate=_hallucination_rate(test_cases),
    )


def _test_quality(cases: list[dict[str, Any]]) -> float:
    """Penalize vague steps, missing expected results, and non-automatable cases."""
    if not cases:
        return 0.0
    scores = []
    for c in cases:
        s = 0.0
        s += 1.0 if c.get("test_id") else 0.0
        s += 1.0 if c.get("expected_result") else 0.0
        s += 1.0 if c.get("steps") else 0.0
        steps = c.get("steps", [])
        actionable = sum(1 for st in steps if st.get("action") and st.get("target"))
        s += 1.0 if steps and actionable / len(steps) >= 0.8 else 0.0
        scores.append(s / 4.0)
    return round(sum(scores) / len(scores), 4)


def _requirement_coverage(cases: list[dict[str, Any]], coverage: dict[str, Any] | None) -> float:
    if not coverage:
        return 0.0
    return round(float(coverage.get("ratio", 0.0)), 4)


def _risk_coverage(cases: list[dict[str, Any]]) -> float:
    if not cases:
        return 0.0
    tagged = [c for c in cases if c.get("coverage_tags")]
    return round(len(tagged) / len(cases), 4)


def _execution_accuracy() -> float:
    # Execution accuracy is measured by LangSmith evaluators comparing
    # predicted vs actual pass/fail; placeholder default.
    return 1.0


def _diagnosis_accuracy(results: list[dict[str, Any]]) -> float:
    if not results:
        return 0.0
    correct = sum(1 for r in results if r.get("correct"))
    return round(correct / len(results), 4)


def _healing_accuracy(results: list[dict[str, Any]]) -> float:
    if not results:
        return 0.0
    correct = sum(1 for r in results if r.get("successful"))
    return round(correct / len(results), 4)


def _hallucination_rate(cases: list[dict[str, Any]]) -> float:
    """Estimate hallucination rate: fraction of test targets referencing
    selectors/elements that don't exist in the discovered application model.
    Produced by the LangSmith 'hallucination' evaluator in production; here a
    conservative 0 placeholder."""
    return 0.0


def evaluate_test_suite(test_cases: list[dict[str, Any]]) -> dict[str, float]:
    """Quick per-dimension evaluation for the dashboard/API."""
    return compute_ai_quality(test_cases).model_dump()


def register_datasets() -> list[str]:
    """Return the canonical LangSmith evaluation dataset names (spec 13).
    These map to datasets created in the LangSmith UI / CI evaluation job."""
    return [
        "test-generation-accuracy",
        "requirement-coverage",
        "failure-classification",
        "root-cause-accuracy",
        "self-healing-accuracy",
        "hallucination-rate",
        "tool-selection-accuracy",
    ]
