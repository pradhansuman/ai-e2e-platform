"""Secrets management (Phase 9): scoped storage, masking, and redaction.

Never lets a secret value leak into logs or LLM prompts — the platform's
security boundary. Storage is in-memory and pluggable; the redaction/masking
primitives are the parts that must be correct and are therefore unit-tested.
"""
from __future__ import annotations

from typing import Any, Iterable

_MASK = "****"


class SecretsStore:
    """Scoped (tenant, key) → secret storage with masking + redaction."""

    def __init__(self) -> None:
        self._secrets: dict[tuple[str, str], str] = {}

    def set(self, tenant: str, key: str, value: str) -> None:
        self._secrets[(tenant, key)] = value

    def get(self, tenant: str, key: str) -> str | None:
        return self._secrets.get((tenant, key))

    def delete(self, tenant: str, key: str) -> None:
        self._secrets.pop((tenant, key), None)

    def list_keys(self, tenant: str) -> list[str]:
        return sorted(k for (t, k) in self._secrets if t == tenant)

    def all_values(self) -> list[str]:
        return list(self._secrets.values())

    @staticmethod
    def mask(value: str | None) -> str:
        return _MASK if value else ""

    def redact(self, text: str) -> str:
        """Replace every stored secret with a mask in ``text``."""
        out = text
        for value in self._secrets.values():
            if value:
                out = out.replace(value, _MASK)
        return out

    def redact_any(self, text: str, secrets: Iterable[str]) -> str:
        """Redact an arbitrary list of secrets (e.g. from a request)."""
        out = text
        for s in secrets:
            if s:
                out = out.replace(s, _MASK)
        return out
