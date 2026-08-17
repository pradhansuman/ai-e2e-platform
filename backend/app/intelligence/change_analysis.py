"""Change-aware regression intelligence (Phase 5).

Git change -> affected components -> related requirements -> related tests ->
risk score -> minimal test set. Replaces "run all 500 tests" with "only the
tests relevant to this change".

Deterministic: maps changed file paths to logical components via prefix rules,
then traverses the quality graph for transitive impact.
"""
from __future__ import annotations

from typing import Any

from .quality_graph import QualityGraph


def map_changed_files(
    changed_files: list[str], path_rules: list[dict[str, str]]
) -> set[str]:
    """Map changed file paths to component node ids via prefix rules.

    ``path_rules`` entries look like ``{"prefix": "src/api/orders", "component":
    "api:orders"}``. A file matches the first rule whose prefix it starts with.
    """
    components: set[str] = set()
    for f in changed_files:
        for rule in path_rules:
            prefix = rule["prefix"]
            if f == prefix or f.startswith(prefix.rstrip("/") + "/"):
                components.add(rule["component"])
                break
    return components


def analyze_change(
    graph: QualityGraph, changed_components: list[str]
) -> dict[str, Any]:
    """Risk-scored impact of a set of changed components.

    Returns affected requirements, affected tests, and a risk ranking where a
    test's risk = the number of changed components that (transitively) affect it.
    """
    affected_requirements: set[str] = set()
    affected_tests: set[str] = set()
    risk_by_test: dict[str, int] = {}
    reason_by_test: dict[str, set[str]] = {}

    for comp in changed_components:
        impacted = graph.impact_of(comp)
        reqs = graph.affected_requirements(comp)
        tests = graph.affected_tests(comp)
        affected_requirements |= reqs
        affected_tests |= tests
        for t in tests:
            risk_by_test[t] = risk_by_test.get(t, 0) + 1
            reason_by_test.setdefault(t, set()).add(comp)

    ranked = sorted(risk_by_test.items(), key=lambda kv: (-kv[1], kv[0]))
    return {
        "changed_components": sorted(changed_components),
        "affected_requirements": sorted(affected_requirements),
        "affected_tests": sorted(affected_tests),
        "risk_ranked_tests": [
            {"test": t, "risk": r, "affected_by": sorted(reason_by_test[t])}
            for t, r in ranked
        ],
    }


def select_minimal_tests(
    analysis: dict[str, Any], *, max_tests: int | None = None
) -> list[str]:
    """Select the minimum test set: all risk-ranked tests, optionally capped.

    Every affected test is included (it is *relevant*); ``max_tests`` caps the
    selection to the highest-risk subset for budget-constrained CI.
    """
    ranked = analysis["risk_ranked_tests"]
    selected = [r["test"] for r in ranked]
    if max_tests is not None and max_tests < len(selected):
        selected = selected[:max_tests]
    return selected


def regression_plan(
    graph: QualityGraph,
    changed_files: list[str],
    path_rules: list[dict[str, str]],
    *,
    max_tests: int | None = None,
) -> dict[str, Any]:
    """End-to-end: files -> components -> risk -> minimal test set."""
    components = map_changed_files(changed_files, path_rules)
    analysis = analyze_change(graph, sorted(components))
    return {
        "changed_files": changed_files,
        "changed_components": sorted(components),
        **analysis,
        "selected_tests": select_minimal_tests(analysis, max_tests=max_tests),
    }
