"""Playwright execution layer.

The LLM never drives the browser directly. Instead it emits a structured
``TestCase`` (a validated plan). This layer maps each step to an allow-listed
Playwright action, executes it, and captures evidence. Unknown or unsafe
actions are rejected — this is the "Validated Tool Call" boundary in the spec.

Evidence captured per run: screenshots, DOM snapshots, console logs, network
events, execution time, and step-level results.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

from ..config import settings
from .actions import ACTIONS, is_allowed_action

__all__ = ["PlaywrightExecutor"]


class PlaywrightExecutor:
    def __init__(self, headless: bool | None = None) -> None:
        self.headless = settings.browser_headless if headless is None else headless
        self.timeout = settings.browser_timeout_ms

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    async def discover(self, url: str) -> dict[str, Any]:
        """Crawl a URL and return a structured application model."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, slow_mo=settings.browser_slow_mo)
            page = await browser.new_page()
            await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")

            result = await page.evaluate(
                """
                () => {
                  const qa = (s, root) => Array.from((root || document).querySelectorAll(s));
                  const sel = (el) => el.id ? '#' + el.id : null;
                  const grab = (el) => ({
                    tag: el.tagName.toLowerCase(),
                    selector: sel(el),
                    id: el.id || null,
                    name: el.getAttribute('name'),
                    type: el.getAttribute('type'),
                    role: el.getAttribute('role'),
                    placeholder: el.getAttribute('placeholder') || null,
                    data_testid: el.getAttribute('data-testid') || null,
                    aria_label: el.getAttribute('aria-label') || null,
                    label: el.getAttribute('aria-label') || el.textContent?.trim().slice(0, 80) || null,
                    visible: !!(el.offsetWidth || el.offsetHeight)
                  });
                  return {
                    title: document.title,
                    url: location.href,
                    links: qa('a[href]').map(grab).filter((x) => x.selector || x.label).slice(0, 200),
                    buttons: qa('button, input[type=submit], [role=button]').map(grab),
                    inputs: qa('input, select, textarea').map(grab),
                    forms: qa('form').map((f) => ({
                      id: f.id || null,
                      action: f.getAttribute('action'),
                      fields: qa('input, select, textarea', f).map(grab)
                    })),
                    tables: qa('table').length,
                    modals: qa('[role=dialog], .modal, [aria-modal=true]').length
                  };
                }
                """
            )
            await browser.close()

        return {
            "pages": [result],
            "url": url,
            "summary": {
                "links": len(result.get("links", [])),
                "buttons": len(result.get("buttons", [])),
                "inputs": len(result.get("inputs", [])),
                "forms": len(result.get("forms", [])),
                "tables": result.get("tables", 0),
                "modals": result.get("modals", 0),
            },
        }

    async def inspect_page(self, url: str) -> dict[str, Any]:
        return await self.discover(url)

    async def get_dom(self, url: str, selector: str | None = None) -> str:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, slow_mo=settings.browser_slow_mo)
            page = await browser.new_page()
            await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
            if selector:
                html = await page.locator(selector).first.inner_html()
            else:
                html = await page.content()
            await browser.close()
        return html

    async def get_network_logs(self, url: str) -> list[dict[str, Any]]:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, slow_mo=settings.browser_slow_mo)
            page = await browser.new_page()
            events: list[dict[str, Any]] = []
            page.on("response", lambda r: events.append(_response_event(r)))
            await page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
            await browser.close()
        return events

    async def capture_screenshot(self, url: str, full_page: bool = False) -> str:
        path = Path(settings.screenshot_dir) / f"{int(time.time())}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, slow_mo=settings.browser_slow_mo)
            page = await browser.new_page()
            await page.goto(url, timeout=self.timeout)
            await page.screenshot(path=str(path), full_page=full_page)
            await browser.close()
        return str(path)

    async def execute_test(self, test_case: dict[str, Any], app_url: str) -> dict[str, Any]:
        """Execute a structured test case and return step-level results + evidence."""
        started = time.time()
        steps = test_case.get("steps", [])
        step_results: list[dict[str, Any]] = []
        failures: list[dict[str, Any]] = []

        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless, slow_mo=settings.browser_slow_mo)
            context = await browser.new_context(
                viewport={"width": 1366, "height": 900}
            )
            page = await context.new_page()

            console: list[dict[str, Any]] = []
            network: list[dict[str, Any]] = []
            page.on("console", lambda m: console.append({"type": m.type, "text": m.text}))
            page.on("response", lambda r: network.append(_response_event(r)))

            for i, step in enumerate(steps):
                action = step.get("action", "")
                if not is_allowed_action(action):
                    err = f"Disallowed/unknown action '{action}' (step {i})"
                    step_results.append({"step_index": i, "action": action, "status": "error", "error": err})
                    failures.append({"step_index": i, "error": err, "kind": "automation_defect"})
                    break

                t0 = time.time()
                try:
                    await ACTIONS[action](page, step)
                    screenshot = await _screenshot(page, f"{test_case.get('test_id','t')}_s{i}")
                    step_results.append({
                        "step_index": i,
                        "action": action,
                        "target": step.get("target"),
                        "value": step.get("value"),
                        "status": "passed",
                        "duration_ms": int((time.time() - t0) * 1000),
                        "screenshot": screenshot,
                    })
                except Exception as exc:  # noqa: BLE001 - must capture any step failure
                    screenshot = await _screenshot(page, f"{test_case.get('test_id','t')}_s{i}_fail", full_page=True)
                    step_results.append({
                        "step_index": i,
                        "action": action,
                        "target": step.get("target"),
                        "value": step.get("value"),
                        "status": "failed",
                        "duration_ms": int((time.time() - t0) * 1000),
                        "error": str(exc),
                        "screenshot": screenshot,
                        "dom_snapshot": (await page.content())[:5000],
                    })
                    failures.append({"step_index": i, "action": action, "target": step.get("target"), "error": str(exc), "kind": "unknown"})
                    break

            await browser.close()

        status = "passed" if not failures else "failed"
        return {
            "test_id": test_case.get("test_id"),
            "status": status,
            "duration_ms": int((time.time() - started) * 1000),
            "steps": step_results,
            "console_logs": console,
            "network_events": network,
            "failures": failures,
        }


def _response_event(resp) -> dict[str, Any]:
    try:
        status = resp.status
    except Exception:  # noqa: BLE001
        status = None
    return {"url": resp.url, "status": status}


async def _screenshot(page, name: str, full_page: bool = False) -> str:
    path = Path(settings.screenshot_dir) / f"{name}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(path), full_page=full_page)
    return str(path)
