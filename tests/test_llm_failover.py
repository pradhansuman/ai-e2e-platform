"""Tests for multi-provider LLM failover + exhaustion circuit breaker."""
from app import llm


def test_is_rate_limit_error_detects_429():
    assert llm.is_rate_limit_error(RuntimeError("Error code: 429 - Rate limit exceeded")) is True
    assert llm.is_rate_limit_error(RuntimeError("quota exhausted")) is True
    assert llm.is_rate_limit_error(RuntimeError("rate limited")) is True


def test_is_rate_limit_error_false_for_other():
    assert llm.is_rate_limit_error(ValueError("invalid json: expected '['")) is False


def test_circuit_breaker_marks_and_checks():
    llm._EXHAUSTED.clear()
    llm._mark_exhausted("gemini")
    assert llm._is_exhausted("gemini") is True
    assert llm._is_exhausted("openrouter") is False


def test_get_llm_candidates_filters_unset_and_orders(monkeypatch):
    monkeypatch.setattr(llm.settings, "gemini_api_key", "g")
    monkeypatch.setattr(llm.settings, "groq_api_key", None)
    monkeypatch.setattr(llm.settings, "openrouter_api_key", "o")
    monkeypatch.setattr(llm.settings, "anthropic_api_key", None)
    monkeypatch.setattr(llm.settings, "openai_api_key", None)
    llm._EXHAUSTED.clear()
    names = [n for n, _ in llm.get_llm_candidates()]
    assert names == ["gemini", "openrouter"]


def test_exhausted_provider_is_dropped_from_candidates(monkeypatch):
    monkeypatch.setattr(llm.settings, "gemini_api_key", "g")
    monkeypatch.setattr(llm.settings, "groq_api_key", None)
    monkeypatch.setattr(llm.settings, "openrouter_api_key", "o")
    monkeypatch.setattr(llm.settings, "anthropic_api_key", None)
    monkeypatch.setattr(llm.settings, "openai_api_key", None)
    llm._EXHAUSTED.clear()
    llm._mark_exhausted("gemini")
    names = [n for n, _ in llm.get_llm_candidates()]
    assert names == ["openrouter"]


def test_structured_invoke_fails_over_on_rate_limit(monkeypatch):
    llm._EXHAUSTED.clear()
    calls: list[str] = []

    def fake_attempt(prompt, inputs, model_cls, candidate):
        calls.append(candidate)
        if candidate == "first":
            raise RuntimeError("Error code: 429 - Rate limit exceeded")
        return "ok"

    monkeypatch.setattr(llm, "_attempt_with_llm", fake_attempt)
    result = llm.structured_invoke(
        "prompt", {}, str, llms=[("first", "first"), ("second", "second")]
    )
    assert result == "ok"
    assert calls == ["first", "second"]
    assert llm._is_exhausted("first") is True
    assert llm._is_exhausted("second") is False


def test_structured_invoke_raises_when_all_fail(monkeypatch):
    llm._EXHAUSTED.clear()

    def fake_attempt(prompt, inputs, model_cls, candidate):
        raise RuntimeError("boom")

    monkeypatch.setattr(llm, "_attempt_with_llm", fake_attempt)
    try:
        llm.structured_invoke("prompt", {}, str, llms=[("a", "a"), ("b", "b")])
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "boom" in str(e)
