"""Tests for the allow-listed Playwright action boundary."""
from app.executor.actions import ACTIONS, is_allowed_action


def test_known_actions_allowed():
    for action in ["goto", "click", "fill", "assert_visible", "assert_text"]:
        assert is_allowed_action(action)


def test_unknown_actions_rejected():
    assert not is_allowed_action("eval")
    assert not is_allowed_action("execute_javascript")
    assert not is_allowed_action("rm -rf")


def test_actions_registry_covers_core_verbs():
    assert {"goto", "click", "fill", "type", "select", "check", "press"} <= set(ACTIONS)
