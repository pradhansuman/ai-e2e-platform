"""Reusable LangChain tools exposed to the agents.

Every tool is a single, well-scoped operation (spec section 11). Tools that
mutate state or drive the browser are gated by RBAC in the executor layer.
"""
from __future__ import annotations

from langchain_core.tools import tool

from ..config import settings
from ..security import can_execute, redact_for_llm, sanitize_untrusted_content

# Imported lazily to avoid heavy Playwright import at module load in non-browser
# contexts (e.g. unit tests).
_executor = None


def _get_executor():
    global _executor
    if _executor is None:
        from ..executor import PlaywrightExecutor

        _executor = PlaywrightExecutor(headless=settings.browser_headless)
    return _executor


def _storage():
    from ..services.storage import StorageService

    return StorageService()


@tool
def discover_application(url: str) -> dict:
    """Crawl a URL and return discovered pages, routes, links, forms, and
    interactive components. Returns a structured ApplicationModel."""
    sanitize_untrusted_content(url)
    return _get_executor().discover(url)


@tool
def inspect_page(url: str) -> dict:
    """Navigate to a single page and return its DOM structure summary."""
    return _get_executor().inspect_page(url)


@tool
def get_dom(url: str, selector: str | None = None) -> str:
    """Return the current DOM (or a scoped subtree) of a page as HTML text."""
    return _get_executor().get_dom(url, selector)


@tool
def get_network_logs(url: str) -> list[dict]:
    """Return captured network requests/responses for a page, including
    failures (4xx/5xx) and blocked resources."""
    return _get_executor().get_network_logs(url)


@tool
def execute_playwright_test(test_case: dict, app_url: str) -> dict:
    """Execute a structured test case (steps) against the application using
    Playwright. Captures screenshots, DOM snapshots, network logs, and
    step-level results. Requires ENGINEER role."""
    # RBAC is enforced at the API boundary too; this is defense in depth.
    return _get_executor().execute_test(test_case, app_url)


@tool
def capture_screenshot(url: str, full_page: bool = False) -> str:
    """Capture a screenshot of a page and return the artifact path."""
    return _get_executor().capture_screenshot(url, full_page)


@tool
def query_test_history(test_id: str | None = None, application_id: str | None = None) -> list[dict]:
    """Query historical test results to power flakiness detection and
    root-cause analysis."""
    return _storage().query_test_history(test_id=test_id, application_id=application_id)


@tool
def search_requirements(query: str) -> list[dict]:
    """Semantic search over stored requirements (vector store)."""
    return _storage().search_requirements(query)


@tool
def search_test_cases(query: str) -> list[dict]:
    """Semantic search over existing test cases (vector store)."""
    return _storage().search_test_cases(query)


@tool
def create_test_case(test_case: dict) -> str:
    """Persist a generated test case. Returns the created test_id."""
    return _storage().create_test_case(redact_for_llm(test_case))


@tool
def update_test_case(test_id: str, patch: dict) -> str:
    """Update an existing test case."""
    return _storage().update_test_case(test_id, patch)


@tool
def analyze_failure(failure: dict) -> dict:
    """Given failure evidence, classify and propose a root cause (see the
    failure-intelligence agent for the full LLM-backed analysis)."""
    from ..agents.analyzer import analyze_failure_evidence

    return analyze_failure_evidence(failure)


TOOLS = [
    discover_application,
    inspect_page,
    get_dom,
    get_network_logs,
    execute_playwright_test,
    capture_screenshot,
    query_test_history,
    search_requirements,
    search_test_cases,
    create_test_case,
    update_test_case,
    analyze_failure,
]

TOOL_MAP = {t.name: t for t in TOOLS}
