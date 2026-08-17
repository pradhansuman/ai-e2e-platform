"""LLM factory + LangSmith tracing bootstrap.

Centralizes model construction so every agent uses a consistent model,
temperature, and tracing configuration (spec section 11 + 13).

Supported providers: OpenAI, Anthropic, and OpenRouter (OpenAI-compatible,
including its free-tier models).
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, TypeVar, get_args, get_origin, get_type_hints

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

from .config import settings

_OPENROUTER_DEFAULT_HEADERS = None  # built lazily once


def _configure_langsmith() -> None:
    if settings.langsmith_tracing and settings.langsmith_api_key:
        os.environ.setdefault("LANGSMITH_API_KEY", settings.langsmith_api_key)
    if settings.langsmith_project:
        os.environ.setdefault("LANGSMITH_PROJECT", settings.langsmith_project)
    os.environ.setdefault("LANGSMITH_TRACING", str(settings.langsmith_tracing).lower())
    os.environ.setdefault("LANGSMITH_TRACING_V2", str(settings.langsmith_tracing).lower())


def _resolve_provider() -> str:
    """Resolve the effective LLM provider from config (auto-detection)."""
    if settings.llm_provider == "openrouter":
        return "openrouter"
    if settings.llm_provider == "openai":
        return "openai"
    if settings.llm_provider == "anthropic":
        return "anthropic"
    if settings.llm_provider == "google":
        return "google"
    # auto: prefer Gemini, then OpenRouter, then Anthropic, then OpenAI.
    if settings.gemini_api_key:
        return "google"
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


def get_llm(model: str | None = None, temperature: float | None = None) -> BaseChatModel:
    """Return a chat model for the resolved provider."""
    _configure_langsmith()
    temp = settings.llm_temperature if temperature is None else temperature
    provider = _resolve_provider()

    if provider == "google":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model or settings.gemini_model,
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
            temperature=temp,
            max_retries=settings.llm_max_retries,
            timeout=settings.llm_timeout,
        )

    if provider == "openrouter":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model or settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=temp,
            max_retries=settings.llm_max_retries,
            timeout=settings.llm_timeout,
            default_headers=_openrouter_headers(),
        )

    from langchain.chat_models import init_chat_model

    return init_chat_model(
        model or settings.llm_model,
        temperature=temp,
    )


def get_embeddings():
    """Return an embeddings client for the vector store.

    OpenRouter also exposes embedding endpoints, so route it the same way.
    """
    from langchain_openai import OpenAIEmbeddings

    if _resolve_provider() == "google":
        return OpenAIEmbeddings(
            model="text-embedding-004",
            api_key=settings.gemini_api_key,
            base_url=settings.gemini_base_url,
        )
    if _resolve_provider() == "openrouter":
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
    return OpenAIEmbeddings(model=settings.embedding_model)


# --------------------------------------------------------------------------- #
# Robust structured-output invocation
#
# Free-tier models (e.g. OpenRouter `:free` slugs) frequently return output
# wrapped in markdown fences, a bare JSON list instead of the requested object
# shape, or plain prose when a complex Pydantic schema is requested. This helper
# degrades gracefully: native structured output → raw JSON parse (fence-strip +
# list-wrap) → one corrective re-prompt enforcing strict JSON.
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
    """Coerce scalar/dict→list for list-typed fields, recursively.

    Free-tier models often emit a bare string where a list is expected
    (e.g. ``evidence: "..."``) or a dict where a list of sub-models is expected
    (e.g. ``pages[].components: {...}``), which would otherwise fail Pydantic
    validation and force a heuristic fallback.
    """
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


def structured_invoke(
    prompt: ChatPromptTemplate,
    inputs: dict[str, Any],
    model_cls: type[_ModelT],
    llm: BaseChatModel | None = None,
) -> _ModelT:
    """Invoke `prompt` and parse into `model_cls`, robust to free-tier quirks."""
    llm = llm or get_llm()
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
