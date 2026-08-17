"""AI Test Generation Agent (spec section 5).

Generates a structured test suite covering happy paths, negative, boundary,
validation, authn/authz, session, error handling, business workflows,
API/UI integration, accessibility, security, and regression scenarios.

Every test conforms to the canonical TestCase shape (test_id, title,
objective, preconditions, test_data, steps, expected_result, risk, priority,
automation_candidate).
"""
from __future__ import annotations

from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from ..llm import structured_invoke
from ..schemas import TestSuite
from ..security import sanitize_untrusted_content

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a senior QA architect. Generate a comprehensive E2E test suite
for the described application.

Coverage requirements:
- happy paths, negative scenarios, boundary conditions, validation
- authentication, authorization, session handling, error handling
- business workflows, API/UI integration, data validation
- accessibility, security-related scenarios, performance smoke checks
- regression scenarios

Steps must use ONLY these allowed actions:
goto, click, fill, type, press, select, check, uncheck, hover, wait_for,
assert_visible, assert_text, assert_url, assert_value, screenshot.

Each step: {{action, target, value, expected}}. Targets must be CSS selectors
or role selectors (e.g. "input[name=email]", "button:has-text('Submit')").

Assign risk (low/medium/high/critical) and priority (P0-P3). Be concrete and
testable; do not generate vague steps.
""",
        ),
        (
            "human",
            "Application model:\n{application_model}\n\n"
            "Requirements analysis:\n{requirements}\n\n"
            "Existing test cases (avoid duplicates):\n{existing}",
        ),
    ]
)


def generate_tests(
    application_model: dict[str, Any],
    requirements: dict[str, Any] | None = None,
    existing: list[dict[str, Any]] | None = None,
) -> TestSuite:
    return structured_invoke(
        _PROMPT,
        {
            "application_model": sanitize_untrusted_content(str(application_model)),
            "requirements": requirements or {},
            "existing": existing or [],
        },
        TestSuite,
    )


# --------------------------------------------------------------------------- #
# Deterministic fallback (runs even when the LLM is unavailable / rate-limited)
# --------------------------------------------------------------------------- #
_TEXT_TYPES = {"text", "password", "email", "search", "tel", "url", "number", "date"}


def _css_quote(text: str) -> str:
    """Minimal escaping for use inside a :has-text() CSS selector."""
    return text.replace("\\", "").replace('"', "'").strip()[:60]


def _selector_for(el: dict[str, Any]) -> str | None:
    """Derive a Playwright selector from a discovered element.

    Preference order (stable → semantic): id, name, data-testid, aria-label,
    placeholder, then visible text.
    """
    if el.get("id"):
        return f"#{el['id']}"
    if el.get("name"):
        tag = el.get("tag") or "input"
        return f'{tag}[name="{_css_quote(el['name'])}"]'
    if el.get("data_testid"):
        return f'[data-testid="{_css_quote(el['data_testid'])}"]'
    if el.get("aria_label"):
        return f'[aria-label="{_css_quote(el['aria_label'])}"]'
    if el.get("placeholder"):
        tag = el.get("tag") or "input"
        return f'{tag}[placeholder="{_css_quote(el['placeholder'])}"]'
    label = el.get("label")
    if label:
        tag = el.get("tag") or "button"
        return f'{tag}:has-text("{_css_quote(label)}")'
    return None


def _test_value(el: dict[str, Any]) -> str:
    t = (el.get("type") or "text").lower()
    if t == "email":
        return "test@example.com"
    if t == "password":
        return "test-pass-123"
    if t == "number":
        return "42"
    if t == "date":
        return "2026-01-01"
    return "test"


def fallback_generate_tests(
    app_url: str, discovered_pages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Deterministic smoke/interaction tests derived from the crawl data.

    Used when the LLM generation fails or returns no tests, so the pipeline
    remains functional end-to-end (Correctness → Reliability ordering).
    """
    tests: list[dict[str, Any]] = []
    for i, page in enumerate(discovered_pages or []):
        url = page.get("url") or app_url
        pid = f"SMOKE-{i + 1:02d}"

        # 1) Page loads.
        tests.append(
            {
                "test_id": f"{pid}-load",
                "title": f"Page loads: {url}",
                "objective": "Verify the page loads and renders a body",
                "preconditions": [],
                "test_data": {},
                "steps": [
                    {"action": "goto", "target": url, "expected": "page loads"},
                    {"action": "assert_visible", "target": "body", "expected": "body visible"},
                ],
                "expected_result": "Page loads with a visible body",
                "risk": "medium",
                "priority": "P2",
                "automation_candidate": True,
                "coverage_tags": ["smoke"],
            }
        )

        # 2) Form fields are fillable (no submission — safe, deterministic).
        fillable = [
            el
            for el in page.get("inputs", [])
            if el.get("visible") and (el.get("type") or "text").lower() in _TEXT_TYPES
            and _selector_for(el)
        ][:5]
        if fillable:
            steps = [{"action": "goto", "target": url, "expected": "page loads"}]
            for el in fillable:
                sel = _selector_for(el)
                val = _test_value(el)
                steps.append({"action": "fill", "target": sel, "value": val, "expected": "field accepts value"})
                steps.append({"action": "assert_value", "target": sel, "value": val, "expected": "value persists"})
            tests.append(
                {
                    "test_id": f"{pid}-form",
                    "title": f"Form fields fillable on {url}",
                    "objective": "Verify form inputs accept and retain values",
                    "preconditions": [],
                    "test_data": {},
                    "steps": steps,
                    "expected_result": "All fillable inputs accept test values",
                    "risk": "high",
                    "priority": "P1",
                    "automation_candidate": True,
                    "coverage_tags": ["form", "interaction"],
                }
            )

        # 3) Primary action is visible.
        buttons = [b for b in page.get("buttons", []) if b.get("visible")]
        if buttons:
            sel = _selector_for(buttons[0])
            if sel:
                tests.append(
                    {
                        "test_id": f"{pid}-action",
                        "title": f"Primary action visible on {url}",
                        "objective": "Verify the primary action control is rendered",
                        "preconditions": [],
                        "test_data": {},
                        "steps": [
                            {"action": "goto", "target": url, "expected": "page loads"},
                            {"action": "assert_visible", "target": sel, "expected": "control visible"},
                        ],
                        "expected_result": "Primary action control is visible",
                        "risk": "medium",
                        "priority": "P2",
                        "automation_candidate": True,
                        "coverage_tags": ["smoke", "ui"],
                    }
                )

    return tests
