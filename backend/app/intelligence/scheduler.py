"""Continuous QE scheduler (Phase 8) — the runnable closed loop.

Turns the ``ContinuousQEEngine`` decision layer into a runnable loop:

    observe -> detect risk -> select -> execute -> observe -> diagnose ->
    (report | heal -> retest -> validate) -> learn  -> (repeat)

Execution is delegated through ``on_execute`` so the loop is testable without a
browser, and can be pointed at the LangGraph ``run_workflow`` in production.
"""
from __future__ import annotations

import time
from typing import Any, Callable

from .continuous_qe import ContinuousQEEngine

ExecuteFn = Callable[[str], dict[str, Any]]


class ContinuousRunner:
    def __init__(
        self,
        engine: ContinuousQEEngine,
        *,
        on_execute: ExecuteFn | None = None,
    ) -> None:
        self.engine = engine
        self.on_execute = on_execute or (lambda test_id: {"test_id": test_id, "status": "passed"})
        self.results: list[dict[str, Any]] = []
        self._stop = False

    def run_once(
        self,
        *,
        journey_traffic: dict[str, int] | None = None,
        changed_components: list[str] | None = None,
        max_tests: int | None = None,
    ) -> dict[str, Any]:
        """One full loop tick. Returns the plan plus per-test outcomes."""
        plan = self.engine.iterate(
            journey_traffic=journey_traffic,
            changed_components=changed_components,
            max_tests=max_tests,
        )
        outcomes = [self.on_execute(t) for t in plan["selected_tests"]]
        record = {"plan": plan, "outcomes": outcomes}
        self.results.append(record)
        return record

    def run_forever(
        self,
        *,
        interval_seconds: float = 60.0,
        max_iterations: int | None = None,
        journey_traffic: dict[str, int] | None = None,
        changed_components: list[str] | None = None,
        max_tests: int | None = None,
    ) -> int:
        """Loop until stopped or ``max_iterations`` reached. Returns tick count."""
        self._stop = False
        ticks = 0
        while not self._stop:
            self.run_once(
                journey_traffic=journey_traffic,
                changed_components=changed_components,
                max_tests=max_tests,
            )
            ticks += 1
            if max_iterations is not None and ticks >= max_iterations:
                break
            if not self._stop:
                time.sleep(interval_seconds)
        return ticks

    def stop(self) -> None:
        self._stop = True
