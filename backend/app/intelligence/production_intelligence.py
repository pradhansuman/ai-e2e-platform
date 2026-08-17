"""Production → test intelligence (Phase 7).

Connect production signals (logs, errors, user-journey traffic, incidents) to
test coverage so the platform can answer: *"users frequently perform this
workflow, but it has weak test coverage."*

Deterministic: ranks journeys by traffic × (1 − coverage) and emits test
suggestions for the highest-risk gaps.
"""
from __future__ import annotations

from typing import Any

from .quality_graph import QualityGraph


def detect_test_gaps(
    graph: QualityGraph, journey_traffic: dict[str, int]
) -> list[dict[str, Any]]:
    """Rank uncovered user journeys by traffic (highest risk first)."""
    gaps: list[dict[str, Any]] = []
    for journey, traffic in journey_traffic.items():
        node = graph.node(journey)
        if node is None:
            continue
        covering = graph.affected_tests(journey)
        coverage = min(1.0, len(covering) / 3.0)  # coarse: 3 tests ≈ full coverage
        risk = round(traffic * (1.0 - coverage), 2)
        gaps.append(
            {
                "journey": journey,
                "traffic": traffic,
                "covering_tests": sorted(covering),
                "coverage": round(coverage, 2),
                "risk_score": risk,
            }
        )
    return sorted(gaps, key=lambda g: (-g["risk_score"], -g["traffic"]))


def suggest_tests(gaps: list[dict[str, Any]], *, top_n: int = 5) -> list[dict[str, Any]]:
    """Generate deterministic test suggestions for the highest-risk gaps."""
    suggestions = []
    for gap in gaps[:top_n]:
        suggestions.append(
            {
                "journey": gap["journey"],
                "risk_score": gap["risk_score"],
                "reason": (
                    f"{gap['traffic']} production visits with only "
                    f"{len(gap['covering_tests'])} covering test(s)"
                ),
                "suggested_test": f"e2e_{gap['journey']}_happy_path",
            }
        )
    return suggestions


def production_risk_report(
    graph: QualityGraph, journey_traffic: dict[str, int], *, top_n: int = 5
) -> dict[str, Any]:
    """Full production-intelligence pass: gaps + suggested tests."""
    gaps = detect_test_gaps(graph, journey_traffic)
    return {
        "gaps": gaps,
        "suggested_tests": suggest_tests(gaps, top_n=top_n),
    }
