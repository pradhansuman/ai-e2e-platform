"""Pydantic schemas for structured LLM outputs and API contracts.

Using explicit schemas (rather than free text) is what turns the LLM into a
reliable component: every generated test case, root cause, and healing
suggestion conforms to a validated shape (spec sections 5, 8, 9).
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Discovery
# --------------------------------------------------------------------------- #
class DiscoveredComponent(BaseModel):
    type: Literal["form", "button", "input", "table", "modal", "link", "nav", "other"]
    selector: str
    label: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class DiscoveredPage(BaseModel):
    url: str
    title: str | None = None
    route: str | None = None
    components: list[DiscoveredComponent] = Field(default_factory=list)
    forms: list[dict[str, Any]] = Field(default_factory=list)
    links: list[dict[str, Any]] = Field(default_factory=list)


class ApplicationModel(BaseModel):
    pages: list[DiscoveredPage] = Field(default_factory=list)
    apis: list[dict[str, Any]] = Field(default_factory=list)
    auth_flows: list[dict[str, Any]] = Field(default_factory=list)
    business_workflows: list[dict[str, Any]] = Field(default_factory=list)
    risk_areas: list[dict[str, Any]] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Requirements
# --------------------------------------------------------------------------- #
class RequirementAnalysis(BaseModel):
    business_rules: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    user_journeys: list[dict[str, Any]] = Field(default_factory=list)
    gaps: list[dict[str, Any]] = Field(default_factory=list)  # missing/ambiguous/contradictory
    risky_workflows: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Understanding (Requirements / Risks / User Journeys)
# --------------------------------------------------------------------------- #
class Risk(BaseModel):
    risk_id: str
    area: str
    description: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    mitigation: str | None = None


class UserJourney(BaseModel):
    journey_id: str
    name: str
    steps: list[str] = Field(default_factory=list)
    entry_point: str | None = None


class Understanding(BaseModel):
    """The three parallel artifacts derived from the Application Model."""

    requirements: list[str] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    user_journeys: list[UserJourney] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Test intelligence / coverage
# --------------------------------------------------------------------------- #
class CoverageAnalysis(BaseModel):
    covered_risks: list[str] = Field(default_factory=list)
    uncovered_risks: list[str] = Field(default_factory=list)
    covered_journeys: list[str] = Field(default_factory=list)
    uncovered_journeys: list[str] = Field(default_factory=list)
    missing_tests: list[str] = Field(default_factory=list)
    weak_tests: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Test generation
# --------------------------------------------------------------------------- #
class TestStep(BaseModel):
    action: str
    target: str | None = None
    value: str | None = None
    expected: str | None = None


class TestCase(BaseModel):
    """The canonical test-case shape required by the spec."""

    test_id: str
    title: str
    objective: str
    preconditions: list[str] = Field(default_factory=list)
    test_data: dict[str, Any] = Field(default_factory=dict)
    steps: list[TestStep]
    expected_result: str
    risk: Literal["low", "medium", "high", "critical"] = "medium"
    priority: Literal["P0", "P1", "P2", "P3"] = "P3"
    automation_candidate: bool = True
    coverage_tags: list[str] = Field(default_factory=list)


class TestSuite(BaseModel):
    test_cases: list[TestCase]
    rationale: str | None = None


# --------------------------------------------------------------------------- #
# Execution / evidence
# --------------------------------------------------------------------------- #
class StepResult(BaseModel):
    step_index: int
    action: str
    status: Literal["passed", "failed", "skipped", "error"]
    duration_ms: int | None = None
    error: str | None = None
    screenshot: str | None = None
    dom_snapshot: str | None = None
    network_events: list[dict[str, Any]] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    test_id: str
    status: Literal["passed", "failed", "skipped", "flaky", "error"]
    duration_ms: int | None = None
    steps: list[StepResult] = Field(default_factory=list)
    evidence: dict[str, Any] = Field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Failure intelligence
# --------------------------------------------------------------------------- #
class RootCause(BaseModel):
    classification: Literal[
        "product_defect",
        "automation_defect",
        "environment",
        "test_data",
        "timing",
        "network",
        "dependency",
        "authentication",
        "configuration",
        "flaky",
        "unknown",
    ]
    root_cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    recommended_fix: str | None = None
    affected_tests: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Self-healing
# --------------------------------------------------------------------------- #
class LocatorCandidate(BaseModel):
    selector: str
    score: float = Field(ge=0.0, le=1.0)
    reason: str


class HealingSuggestion(BaseModel):
    test_id: str
    original_locator: str
    candidates: list[LocatorCandidate]
    selected: LocatorCandidate | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
class AiQualityScores(BaseModel):
    test_quality: float = 0.0
    requirement_coverage: float = 0.0
    risk_coverage: float = 0.0
    execution_accuracy: float = 0.0
    failure_diagnosis_accuracy: float = 0.0
    self_healing_accuracy: float = 0.0
    hallucination_rate: float = 0.0
