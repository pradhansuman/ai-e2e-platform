"""Understanding Agent — the "Requirements | Risks | User Journeys" branch.

Distills the Application Knowledge Model into the three parallel artifacts the
pipeline needs before test design. Mirrors the flowchart:

    APPLICATION MODEL
    ┌──────────┼──────────┐
    Requirements  Risks  User Journeys
"""
from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from ..llm import structured_invoke
from ..schemas import Understanding
from ..security import sanitize_untrusted_content

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a test-analysis expert. Given an Application Knowledge Model,
produce three parallel artifacts:

- requirements: concrete, testable business rules the app must satisfy
  (e.g. "the login form must reject an invalid email address").
- risks: the areas most likely to fail or cause harm. Each risk must have an
  id, an area, a description, a severity (low/medium/high/critical), and an
  optional mitigation.
- user_journeys: the key end-to-end flows a user takes. Each journey must have
  an id, a name, ordered steps, and an entry_point (page/route).

Base everything strictly on the model. Do not invent features the model does
not show; mark low-confidence inferences explicitly in the description.
""",
        ),
        ("human", "Application model (JSON):\n{model}"),
    ]
)


def understand_application(application_model: dict[str, Any]) -> Understanding:
    return structured_invoke(
        _PROMPT,
        {"model": sanitize_untrusted_content(str(application_model))},
        Understanding,
    )


def fallback_understand(application_model: dict[str, Any]) -> Understanding:
    """Deterministic understanding from the crawl model (no LLM required)."""
    risks: list[dict[str, Any]] = []
    for i, r in enumerate(application_model.get("risk_areas", []) or []):
        if not isinstance(r, dict):
            r = {"description": str(r)}
        risks.append(
            {
                "risk_id": f"RISK-{i + 1:02d}",
                "area": r.get("area") or r.get("name") or "unknown",
                "description": r.get("description") or str(r),
                "severity": r.get("severity", "medium"),
                "mitigation": r.get("mitigation"),
            }
        )

    journeys: list[dict[str, Any]] = []
    workflows = application_model.get("business_workflows", []) or []
    if not workflows:
        workflows = application_model.get("auth_flows", []) or []
    for i, w in enumerate(workflows):
        if not isinstance(w, dict):
            w = {"name": str(w)}
        steps = w.get("steps", [])
        if not isinstance(steps, list):
            steps = [str(steps)] if steps else []
        journeys.append(
            {
                "journey_id": f"JOURNEY-{i + 1:02d}",
                "name": w.get("name") or f"journey-{i + 1}",
                "steps": [str(s) for s in steps],
                "entry_point": w.get("entry_point"),
            }
        )

    requirements: list[str] = []
    for p in application_model.get("pages", []) or []:
        for form in p.get("forms", []) or []:
            if isinstance(form, dict) and form.get("name"):
                requirements.append(
                    f"The form '{form['name']}' must accept valid input and submit successfully."
                )

    return Understanding(requirements=requirements, risks=risks, user_journeys=journeys)
