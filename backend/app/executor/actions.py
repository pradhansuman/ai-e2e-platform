"""Allow-listed Playwright actions.

This is the *only* place where an LLM-generated step touches the browser.
Each action receives the page and a step dict and performs one validated
operation. Anything not in ``ACTIONS`` is rejected by the executor, so the
model cannot emit arbitrary JavaScript or drive the browser outside this
contract.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

ActionFn = Callable[[Any, dict[str, Any]], Awaitable[None]]


async def _goto(page, step: dict) -> None:
    url = step.get("target") or step.get("value") or step.get("url")
    if not url:
        raise ValueError("goto step missing a target URL")
    await page.goto(str(url), wait_until="domcontentloaded")


async def _click(page, step: dict) -> None:
    locator = page.locator(step["target"])
    await locator.first.click()


async def _fill(page, step: dict) -> None:
    await page.locator(step["target"]).first.fill(str(step.get("value", "")))


async def _type(page, step: dict) -> None:
    await page.locator(step["target"]).first.type(str(step.get("value", "")))


async def _press(page, step: dict) -> None:
    await page.locator(step["target"]).first.press(step["value"])


async def _select(page, step: dict) -> None:
    await page.locator(step["target"]).first.select_option(str(step.get("value", "")))


async def _check(page, step: dict) -> None:
    await page.locator(step["target"]).first.check()


async def _uncheck(page, step: dict) -> None:
    await page.locator(step["target"]).first.uncheck()


async def _hover(page, step: dict) -> None:
    await page.locator(step["target"]).first.hover()


async def _wait_for(page, step: dict) -> None:
    await page.locator(step["target"]).first.wait_for(timeout=step.get("timeout", 10000))


async def _assert_visible(page, step: dict) -> None:
    await page.locator(step["target"]).first.wait_for(state="visible", timeout=step.get("timeout", 10000))


async def _assert_text(page, step: dict) -> None:
    text = str(step.get("value", ""))
    locator = page.locator(step["target"]) if step.get("target") else page.locator("body")
    await locator.first.wait_for(timeout=step.get("timeout", 10000))
    content = await locator.first.inner_text()
    if text not in content:
        raise AssertionError(f"Expected text '{text}' not found in element {step.get('target')}")


async def _assert_url(page, step: dict) -> None:
    expected = step.get("value", "")
    if expected and expected not in page.url:
        raise AssertionError(f"Expected URL containing '{expected}', got '{page.url}'")


async def _assert_value(page, step: dict) -> None:
    value = await page.locator(step["target"]).first.input_value()
    if value != str(step.get("value", "")):
        raise AssertionError(f"Expected value '{step.get('value')}', got '{value}'")


async def _screenshot(page, step: dict) -> None:
    from ..config import settings
    from pathlib import Path

    path = Path(settings.screenshot_dir) / f"{step.get('value', 'shot')}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    await page.screenshot(path=str(path), full_page=bool(step.get("full_page", False)))


ACTIONS: dict[str, ActionFn] = {
    "goto": _goto,
    "click": _click,
    "fill": _fill,
    "type": _type,
    "press": _press,
    "select": _select,
    "check": _check,
    "uncheck": _uncheck,
    "hover": _hover,
    "wait_for": _wait_for,
    "assert_visible": _assert_visible,
    "assert_text": _assert_text,
    "assert_url": _assert_url,
    "assert_value": _assert_value,
    "screenshot": _screenshot,
}


def is_allowed_action(action: str) -> bool:
    return action in ACTIONS
