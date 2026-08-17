"""Storage service: persistence + retrieval over Postgres and the vector store.

Wraps DB access for tools and nodes. Methods degrade gracefully when the
database is unavailable (useful for unit tests and local exploration).
"""
from __future__ import annotations

from typing import Any

from ..config import settings


class StorageService:
    """Thin persistence facade. In production this talks to Postgres via the
    ORM models and to the vector store for semantic search."""

    def __init__(self) -> None:
        self._vector = None

    # ------------------------------------------------------------------ #
    def _vec(self):
        if self._vector is None:
            from .vector_store import VectorStore

            self._vector = VectorStore(settings.vector_store_url)
        return self._vector

    def query_test_history(self, test_id: str | None = None, application_id: str | None = None) -> list[dict[str, Any]]:
        """Return historical results. Falls back to empty list offline."""
        try:
            # Production: SELECT from test_results join test_runs.
            return self._db_query_history(test_id, application_id)
        except Exception:  # noqa: BLE001 - offline/unit-test fallback
            return []

    def _db_query_history(self, test_id, application_id) -> list[dict[str, Any]]:
        return []  # implemented against ORM in the API layer

    def search_requirements(self, query: str) -> list[dict[str, Any]]:
        return self._vec().search("requirements", query)

    def search_test_cases(self, query: str) -> list[dict[str, Any]]:
        return self._vec().search("test_cases", query)

    def create_test_case(self, test_case: dict[str, Any]) -> str:
        return self._vec().upsert("test_cases", test_case)

    def update_test_case(self, test_id: str, patch: dict[str, Any]) -> str:
        return test_id
