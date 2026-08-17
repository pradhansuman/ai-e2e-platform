"""Continuous autonomous QE loop (Phase 8).

Orchestrates the closed loop:

    OBSERVE -> DETECT RISK -> DESIGN STRATEGY -> SELECT -> GENERATE/UPDATE ->
    EXECUTE -> OBSERVE -> DIAGNOSE -> (PRODUCT BUG: report | TEST BUG: heal ->
    retest -> validate) -> LEARN.

The engine holds the knowledge graph, change stream, and production signals,
and each ``iterate`` produces a plan (risk items + selected tests) that is fed
to the existing LangGraph execution pipeline. Execution/diagnosis/healing are
delegated; this module owns the *decision* layer above them.
"""
from __future__ import annotations

from typing import Any

from .change_analysis import analyze_change, select_minimal_tests
from .production_intelligence import detect_test_gaps
from .quality_graph import QualityGraph


class ContinuousQEEngine:
    def __init__(
        self,
        graph: QualityGraph,
        *,
        path_rules: list[dict[str, str]] | None = None,
    ) -> None:
        self.graph = graph
        self.path_rules = path_rules or []
        self.production_signals: dict[str, int] = {}
        self.changed_components: list[str] = []
        self.history: list[dict[str, Any]] = []

    # -- OBSERVE ----------------------------------------------------------- #
    def observe(
        self,
        *,
        journey_traffic: dict[str, int] | None = None,
        changed_components: list[str] | None = None,
    ) -> "ContinuousQEEngine":
        """Ingest production signals and/or a change stream."""
        if journey_traffic is not None:
            self.production_signals.update(journey_traffic)
        if changed_components is not None:
            self.changed_components = list(dict.fromkeys(changed_components))
        return self

    # -- DETECT RISK ------------------------------------------------------- #
    def detect_risk(self) -> dict[str, Any]:
        """Aggregate change impact and production gaps into risk items."""
        change = analyze_change(self.graph, self.changed_components) if self.changed_components else {
            "changed_components": [], "affected_requirements": [],
            "affected_tests": [], "risk_ranked_tests": [],
        }
        gaps = detect_test_gaps(self.graph, self.production_signals)
        return {"change_impact": change, "production_gaps": gaps}

    # -- SELECT ------------------------------------------------------------ #
    def select_tests(self, *, max_tests: int | None = None) -> list[str]:
        """Minimal test set from the current risk signal (change + gaps)."""
        risk = self.detect_risk()
        tests = set(t["test"] for t in risk["change_impact"]["risk_ranked_tests"])
        # Production gaps map to suggested tests (happy-path per gap).
        for gap in risk["production_gaps"]:
            tests.add(f"e2e_{gap['journey']}_happy_path")
        ordered = [
            t["test"] for t in risk["change_impact"]["risk_ranked_tests"]
        ] + [
            f"e2e_{g['journey']}_happy_path" for g in risk["production_gaps"]
        ]
        selected = list(dict.fromkeys(ordered))  # dedupe, keep risk order
        if max_tests is not None:
            selected = selected[:max_tests]
        return selected

    # -- ITERATE ----------------------------------------------------------- #
    def iterate(
        self,
        *,
        journey_traffic: dict[str, int] | None = None,
        changed_components: list[str] | None = None,
        max_tests: int | None = None,
    ) -> dict[str, Any]:
        """One full loop tick: observe → risk → select. Returns the plan."""
        self.observe(
            journey_traffic=journey_traffic, changed_components=changed_components
        )
        risk = self.detect_risk()
        plan = {
            "stage": "planned",
            "risk": risk,
            "selected_tests": self.select_tests(max_tests=max_tests),
            "next": (
                "execute -> observe -> diagnose -> "
                "(report product bug | heal test bug -> retest -> validate) -> learn"
            ),
        }
        self.history.append(
            {
                "changed_components": list(self.changed_components),
                "production_signals": dict(self.production_signals),
                "selected_tests": plan["selected_tests"],
            }
        )
        return plan
