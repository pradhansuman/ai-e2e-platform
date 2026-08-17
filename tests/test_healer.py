"""Tests for self-healing (deterministic fallback + controlled apply)."""
from app.agents.healer import apply_healing, heuristic_heal
from app.schemas import HealingSuggestion, LocatorCandidate

DOM = """
<div>
  <input id="user-name" name="user-name" data-testid="user-name" />
  <input id="password" name="password" />
  <button data-testid="login-button">Login</button>
</div>
"""


def test_heuristic_heal_finds_a_candidate():
    suggestion = heuristic_heal("#user-name", DOM)
    assert suggestion.selected is not None
    assert suggestion.selected.selector.startswith("[data-testid=")
    assert suggestion.confidence > 0.8


def test_heuristic_heal_no_candidates_is_safe():
    suggestion = heuristic_heal("#missing", "<div>nothing here</div>")
    assert suggestion.selected is None
    assert suggestion.confidence == 0.0


def test_apply_healing_updates_target_and_records_event():
    suggestion = HealingSuggestion(
        test_id="T1",
        original_locator="#user-name",
        candidates=[LocatorCandidate(selector="[data-testid=username]", score=0.9, reason="stable")],
        selected=LocatorCandidate(selector="[data-testid=username]", score=0.9, reason="stable"),
        confidence=0.9,
        reason="test",
    )
    test_case = {"test_id": "T1", "steps": [{"action": "fill", "target": "#user-name", "value": "x"}]}
    updated, event = apply_healing(test_case, "#user-name", suggestion)
    assert updated["steps"][0]["target"] == "[data-testid=username]"
    assert event["original_locator"] == "#user-name"
    assert event["new_locator"] == "[data-testid=username]"
    assert event["approval_status"] == "pending"
