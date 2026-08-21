"""Tests for the allow-listed Playwright action boundary."""
from app.executor.actions import ACTIONS, is_allowed_action
from app.executor import PlaywrightExecutor


def test_known_actions_allowed():
    for action in ["goto", "click", "fill", "assert_visible", "assert_text"]:
        assert is_allowed_action(action)


def test_unknown_actions_rejected():
    assert not is_allowed_action("eval")
    assert not is_allowed_action("execute_javascript")
    assert not is_allowed_action("rm -rf")


def test_actions_registry_covers_core_verbs():
    assert {"goto", "click", "fill", "type", "select", "check", "press"} <= set(ACTIONS)


def test_executor_restricts_navigation_to_application_origin():
    executor = PlaywrightExecutor()
    assert executor._validate_navigation("/checkout", "https://example.test") == "https://example.test/checkout"
    try:
        executor._validate_navigation("https://attacker.test", "https://example.test")
    except ValueError as exc:
        assert "application origin" in str(exc)
    else:
        raise AssertionError("cross-origin navigation was accepted")


def test_executor_sanitizes_artifact_names():
    assert "/" not in PlaywrightExecutor._artifact_name("../../run/1")
