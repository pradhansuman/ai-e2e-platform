"""Test Intelligence Agent — the step between test design and selection.

Analyzes the generated test suite against the application understanding
(requirements, risks, user journeys) to measure coverage, flag gaps, and
identify weak tests. Feeds risk-based selection and the learn/improve loop.
"""
from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from ..llm import structured_invoke
from ..schemas import CoverageAnalysis
from ..security import sanitize_untrusted_content

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a test-intelligence analyst. Given a generated test suite and the
application understanding (requirements, risks, user journeys), produce a
coverage analysis:

- covered_risks / uncovered_risks: the risk ids (or descriptions) that are /
  are not covered by the suite.
- covered_journeys / uncovered_journeys: the journey ids (or names) that are /
  are not covered.
- missing_tests: concrete tests that should be added to close coverage gaps.
- weak_tests: test ids that are vague, untestable, or low-value.

Be specific and reference actual ids/names from the inputs. Do not hallucinate
ids that are not present.
""",
        ),
        ("human", "Test suite:\n{tests}\n\nUnderstanding:\n{understanding}"),
    ]
)


def analyze_test_coverage(
    tests: list[dict[str, Any]], understanding: dict[str, Any]
) -> CoverageAnalysis:
    return structured_invoke(
        _PROMPT,
        {
            "tests": sanitize_untrusted_content(str(tests)),
            "understanding": sanitize_untrusted_content(str(understanding)),
        },
        CoverageAnalysis,
    )


def fallback_coverage(
    tests: list[dict[str, Any]], understanding: dict[str, Any]
) -> CoverageAnalysis:
    """Deterministic coverage: match risk/journey ids against coverage_tags."""
    tags: set[str] = set()
    for t in tests or []:
        tags.update(t.get("coverage_tags", []) or [])
        if t.get("test_id"):
            tags.add(t["test_id"])

    risks = understanding.get("risks", []) or []
    journeys = understanding.get("user_journeys", []) or []

    def risk_key(r: dict[str, Any]) -> str:
        return r.get("risk_id") or r.get("area") or str(r)

    def journey_key(j: dict[str, Any]) -> str:
        return j.get("journey_id") or j.get("name") or str(j)

    covered_risks = [risk_key(r) for r in risks if risk_key(r) in tags]
    uncovered_risks = [risk_key(r) for r in risks if risk_key(r) not in tags]
    covered_journeys = [journey_key(j) for j in journeys if journey_key(j) in tags]
    uncovered_journeys = [journey_key(j) for j in journeys if journey_key(j) not in tags]

    return CoverageAnalysis(
        covered_risks=covered_risks,
        uncovered_risks=uncovered_risks,
        covered_journeys=covered_journeys,
        uncovered_journeys=uncovered_journeys,
        missing_tests=[],
        weak_tests=[],
    )
