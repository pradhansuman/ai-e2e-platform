"""Tests for deterministic test generation + selector derivation."""
from app.agents.generator import _selector_for, fallback_generate_tests


def test_selector_prefers_id():
    assert _selector_for({"tag": "input", "id": "user"}) == "#user"


def test_selector_name():
    assert _selector_for({"tag": "input", "name": "email"}) == 'input[name="email"]'


def test_selector_text_fallback():
    assert _selector_for({"tag": "button", "label": "🔔 Live"}) == 'button:has-text("🔔 Live")'


def test_selector_aria_label():
    assert _selector_for({"tag": "button", "aria_label": "Log Trade"}) == '[aria-label="Log Trade"]'


def test_selector_placeholder():
    assert _selector_for({"tag": "input", "placeholder": "Entry ₹"}) == 'input[placeholder="Entry ₹"]'


def test_no_selector():
    assert _selector_for({"tag": "button"}) is None


def test_fallback_generates_load_test():
    pages = [{"url": "https://x.test", "title": "X", "inputs": [], "buttons": []}]
    tests = fallback_generate_tests("https://x.test", pages)
    assert any(t["test_id"].endswith("-load") for t in tests)


def test_fallback_generates_action_test_from_text_button():
    pages = [{"url": "https://x.test", "title": "X", "inputs": [],
              "buttons": [{"tag": "button", "label": "Go", "visible": True}]}]
    tests = fallback_generate_tests("https://x.test", pages)
    assert any(t["test_id"].endswith("-action") for t in tests)
