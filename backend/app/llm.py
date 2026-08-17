"""LLM factory + LangSmith tracing bootstrap + multi-provider failover.

Centralizes model construction so every agent uses a consistent model,
temperature, and tracing configuration (spec section 11 + 13).

Supported providers: OpenAI, Anthropic, OpenRouter (OpenAI-compatible,
including free-tier models), Google Gemini, and Groq.

Failover: when one provider's free tier is exhausted (HTTP 429), it is marked
exhausted and the next provider is tried automatically — so a run keeps its
LLM-powered path as long as *any* configured provider still has quota.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Any, TypeVar, get_args, get_origin, get_type_hints

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from .config import settings

_OPENROUTER_DEFAULT_HEADERS = None  # built lazily once

# Provider name -> unix timestamp until which it is treated as exhausted.
_EXHAUSTED: dict[str, float] = {}
_EXHAUSTION_COOLDOWN_S = 600  # 10 minutes


def _configure_langsmith() -> None:
    if settings.langsmith_tracing and settings.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
    if settings.langsmith_project:
        os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
    os.environ.setdefault("LANGSMITH_TRACING", str(settings.langsmith_tracing).lower())
    os.environ.setdefault("LANGSMITH_TRACING_V2", str(settings.langsmith_tracing).lower())


def _resolve_provider() -> str:
    """Resolve the effective single LLM provider from config (auto-detection)."""
    if settings.llm_provider == "openrouter":
        return "openrouter"
    if settings.llm_provider == "openai":
        return "openai"
    if settings.llm_provider == "anthropic":
        return "anthropic"
    if settings.llm_provider == "google":
        return "google"
    if settings.llm_provider == "groq":
        return "groq"
    # auto: prefer Gemini, then Groq, then OpenRouter, then Anthropic, then OpenAI.
    if settings.gemini_api_key:
        return "google"
    if settings.groq_api_key:
        return "groq"
    if settings.openrouter_api_key:
        return "openrouter"
    if settings.anthropic_api_key:
        return "anthropic"
    return "openai"


def _openrouter_headers() -> dict[str, str]:
    # OpenRouter recommends HTTP-Referer / X-Title for ranking purposes.
    return {
        "HTTP-Referer": "https://ai-e2e-platform.local",
        "X-Title": settings.app_name,
    }


def _openrouter_models() -> list[str]:
    """Ordered, de-duplicated list of OpenRouter free models to fail over to."""
    models = [settings.openrouter_model]
    for m in (settings.openrouter_fallback_models or "").split(","):
        m = m.strip()
        if m and m not in models:
            models.append(m)
    return models


def _make_openai_compat(
    model: str,
    api_key: str,
    base_url: str,
    *,
    headers: dict[str, str] | None = None,
    temperature: float | None = None,
) -> BaseChatModel:
    """Build a ChatOpenAI pointed at any OpenAI-compatible endpoint."""
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": model,
        "api_key": api_key,
        "base_url": base_url,
        "temperature": settings.llm_temperature if temperature is None else temperature,
        "max_retries": settings.llm_max_retries,
        "timeout": settings.llm_timeout,
    }
    if headers:
        kwargs["default_headers"] = headers
    return ChatOpenAI(**kwargs)


def get_llm(model: str | None = None, temperature: float | None = None) -> BaseChatModel:
    """Return a chat model for the resolved (single) provider."""
    _configure_langsmith()
    provider = _resolve_provider()

    if provider == "google":
        return _make_openai_compat(
            model or settings.gemini_model,
            settings.gemini_api_key or "",
            settings.gemini_base_url,
            temperature=temperature,
        )
    if provider == "groq":
        return _make_openai_compat(
            model or settings.groq_model,
            settings.groq_api_key or "",
            settings.groq_base_url,
            temperature=temperature,
        )
    if provider == "openrouter":
        return _make_openai_compat(
            model or settings.openrouter_model,
            settings.openrouter_api_key or "",
            settings.openrouter_base_url,
            headers=_openrouter_headers(),
            temperature=temperature,
        )

    from langchain.chat_models import init_chat_model

    return init_chat_model(
        model or settings.llm_model,
        temperature=temperature,
    )


def get_llm_candidates() -> list[tuple[str, BaseChatModel]]:
    """Ordered list of `(provider_name, llm)` candidates for failover.

    Providers with an unset key are omitted. Free providers come first; paid
    providers are last. Exhausted providers (429 within the cooldown) are
    dropped from the list.
    """
    _configure_langsmith()
    candidates: list[tuple[str, BaseChatModel]] = []

    def _add(name: str, key: str | None, build: Any) -> None:
        if not key or _is_exhausted(name):
            return
        candidates.append((name, build()))

    _add(
        "gemini",
        settings.gemini_api_key,
        lambda: _make_openai_compat(
            settings.gemini_model, settings.gemini_api_key or "", settings.gemini_base_url
        ),
    )
    _add(
        "groq",
        settings.groq_api_key,
        lambda: _make_openai_compat(
            settings.groq_model, settings.groq_api_key or "", settings.groq_base_url
        ),
    )

    # OpenRouter: one candidate per free model (model-level failover). The
    # account-level daily cap is tracked separately under the "openrouter" key.
    if settings.openrouter_api_key:
        for slug in _openrouter_models():
            name = f"openrouter:{slug}"
            if _is_exhausted("openrouter") or _is_exhausted(name):
                continue
            candidates.append(
                (
                    name,
                    _make_openai_compat(
                        slug,
                        settings.openrouter_api_key,
                        settings.openrouter_base_url,
                        headers=_openrouter_headers(),
                    ),
                )
            )

    if settings.anthropic_api_key:
        from langchain.chat_models import init_chat_model
        candidates.append(("anthropic", init_chat_model("claude-3-5-sonnet-latest")))
    if settings.openai_api_key:
        from langchain.chat_models import init_chat_model
        candidates.append(("openai", init_chat_model(settings.llm_model)))
    return candidates


def get_embeddings():
    """Return an embeddings client for the vector store."""
    from langchain_openai import OpenAIEmbeddings

    if _resolve_provider() == "google":
        return OpenAIEmbeddings(
            model="text-embedding-004",
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
        )
    if _resolve_provider() == "groq":
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
        )
    if _resolve_provider() == "openrouter":
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
    return OpenAIEmbeddings(model=settings.embedding_model)


# --------------------------------------------------------------------------- #
# Exhaustion tracking (circuit breaker)
# --------------------------------------------------------------------------- #
def _mark_exhausted(name: str) -> None:
    _EXHAUSTED[name] = time.time() + _EXHAUSTION_COOLDOWN_S


def _is_exhausted(name: str) -> bool:
    return _EXHAUSTED.get(name, 0.0) > time.time()


def is_rate_limit_error(exc: Exception) -> bool:
    """Heuristically detect an HTTP 429 / quota-exhaustion error."""
    msg = str(exc).lower()
    if any(tok in msg for tok in ("429", "rate limit", "exhausted", "quota")):
        return True
    try:
        from openai import RateLimitError

        if isinstance(exc, RateLimitError):
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def _handle_rate_limit(name: str, exc: Exception) -> None:
    """Mark the failing candidate exhausted.

    When an OpenRouter model hits the account-level daily cap, mark the whole
    ``openrouter`` group exhausted so the remaining models are skipped too.
    """
    _mark_exhausted(name)
    msg = str(exc).lower()
    if name.startswith("openrouter:") and (
        "free-models-per-day" in msg or "limit_source" in msg
    ):
        _mark_exhausted("openrouter")


# --------------------------------------------------------------------------- #
# Robust structured-output invocation (with failover)
#
# Free-tier models frequently return output wrapped in markdown fences, a bare
# JSON list instead of the requested object shape, or plain prose. This helper
# degrades gracefully per-provider: native structured output → raw JSON parse
# (fence-strip + list-wrap) → one corrective re-prompt. If a provider fails
# outright (or is rate-limited), the next candidate provider is tried.
# --------------------------------------------------------------------------- #
_ModelT = TypeVar("_ModelT", bound=BaseModel)


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def _hints(model_cls: type[_ModelT]) -> dict[str, Any]:
    try:
        return get_type_hints(model_cls)
    except Exception:  # noqa: BLE001
        return dict(getattr(model_cls, "model_fields", {}))


def _list_field(hints: dict[str, Any]) -> str | None:
    for name, ann in hints.items():
        if get_origin(ann) is list or (isinstance(ann, str) and ann.startswith(("list[", "List["))):
            return name
    return None


def _wrap_list(data: list, model_cls: type[_ModelT]) -> dict[str, Any]:
    """Wrap a bare JSON list into the model's list-typed field."""
    hints = _hints(model_cls)
    name = _list_field(hints)
    if name:
        return {name: data}
    for n in hints:
        ln = n.lower()
        if any(k in ln for k in ("list", "case", "test", "item", "step", "result", "page")):
            return {n: data}
    return {"items": data}


def _coerce_object(data: dict, model_cls: type[_ModelT]) -> dict:
    """Remap a synonym key (e.g. ``testSuite``) onto the schema's list field."""
    hints = _hints(model_cls)
    target = _list_field(hints)
    if target and target not in data:
        for k in list(data.keys()):
            if isinstance(data[k], list):
                data = dict(data)
                data[target] = data.pop(k)
                break
    return data


def _item_model(ann: Any) -> type[_ModelT] | None:
    """Return the BaseModel item type of a ``list[X]`` annotation, if any."""
    args = get_args(ann)
    if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
        return args[0]
    return None


def _coerce_types(data: Any, model_cls: type[_ModelT]) -> Any:
    """Coerce scalar/dict→list for list-typed fields, recursively."""
    if not isinstance(data, dict):
        return data
    hints = _hints(model_cls)
    for name, ann in hints.items():
        if name not in data:
            continue
        origin = get_origin(ann)
        if origin is not list:
            continue
        val = data[name]
        if not isinstance(val, list):
            data[name] = [val]
        else:
            item_cls = _item_model(ann)
            if item_cls is not None:
                data[name] = [
                    _coerce_types(v, item_cls) if isinstance(v, dict) else v
                    for v in val
                ]
    return data


def _normalize(data: Any, model_cls: type[_ModelT]) -> Any:
    if isinstance(data, list):
        return _wrap_list(data, model_cls)
    if isinstance(data, dict):
        return _coerce_object(data, model_cls)
    return data


def _raw_parse(
    prompt: ChatPromptTemplate,
    inputs: dict[str, Any],
    model_cls: type[_ModelT],
    llm: BaseChatModel,
) -> _ModelT:
    raw = (prompt | llm).invoke(inputs)
    text = raw.content if hasattr(raw, "content") else str(raw)
    if isinstance(text, list):  # multimodal content blocks
        text = "".join(str(b) for b in text)
    data = json.loads(_strip_code_fences(str(text)))
    data = _normalize(data, model_cls)
    data = _coerce_types(data, model_cls)
    return model_cls.model_validate(data)


def _attempt_with_llm(
    prompt: ChatPromptTemplate,
    inputs: dict[str, Any],
    model_cls: type[_ModelT],
    llm: BaseChatModel,
) -> _ModelT:
    """All three strategies on a single LLM; raises on total failure."""
    last_err: Exception | None = None
    # 1) Native structured output (function calling / JSON mode).
    try:
        return (prompt | llm.with_structured_output(model_cls)).invoke(inputs)
    except Exception as e:  # noqa: BLE001
        last_err = e
    # 2) Raw text → JSON parse (strip fences, wrap bare lists).
    try:
        return _raw_parse(prompt, inputs, model_cls, llm)
    except Exception as e:  # noqa: BLE001
        last_err = e
    # 3) One corrective re-prompt enforcing strict JSON.
    strict = ChatPromptTemplate.from_messages(
        list(prompt.messages)
        + [
            (
                "human",
                "Return ONLY a single valid JSON object (no markdown fences, no "
                "comments, no surrounding prose).",
            )
        ]
    )
    return _raw_parse(strict, inputs, model_cls, llm)


def structured_invoke(
    prompt: ChatPromptTemplate,
    inputs: dict[str, Any],
    model_cls: type[_ModelT],
    llm: BaseChatModel | None = None,
    llms: list[tuple[str, BaseChatModel]] | None = None,
) -> _ModelT:
    """Invoke `prompt` and parse into `model_cls`, with provider failover.

    Tries each candidate provider in order. A provider that returns a
    rate-limit/exhaustion error is marked exhausted and skipped for the rest
    of the process; a provider that returns malformed output is tried once
    more via raw/corrective parse, then skipped for the next provider.
    """
    candidates: list[tuple[str, BaseChatModel]] = (
        [("explicit", llm)] if llm is not None else (llms or get_llm_candidates())
    )
    last_err: Exception | None = None
    for name, candidate in candidates:
        if _is_exhausted(name):
            continue
        try:
            return _attempt_with_llm(prompt, inputs, model_cls, candidate)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if is_rate_limit_error(exc):
                _handle_rate_limit(name, exc)
    if last_err is not None:
        raise last_err
    raise RuntimeError("No LLM candidates available (no API keys configured)")
