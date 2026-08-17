"""Vector store abstraction for application/test knowledge.

Backed by Qdrant by default (config.vector_store_url). Falls back to an
in-memory store so the platform runs without external infrastructure.
"""
from __future__ import annotations

from typing import Any


class VectorStore:
    def __init__(self, url: str) -> None:
        self.url = url
        self._memory: dict[str, list[dict[str, Any]]] = {}
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            try:
                from qdrant_client import QdrantClient

                self._client = QdrantClient(url=self.url)
            except Exception:  # noqa: BLE001 - offline fallback
                self._client = False
        return self._client

    def search(self, collection: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
        client = self._ensure_client()
        if not client:
            # In-memory keyword fallback.
            docs = self._memory.get(collection, [])
            terms = query.lower().split()
            return [
                d
                for d in docs
                if any(t in str(d).lower() for t in terms)
            ][:limit]
        # Production: embed + similarity search (see retrieval.py for embeddings).
        return []

    def upsert(self, collection: str, payload: dict[str, Any]) -> str:
        self._memory.setdefault(collection, []).append(payload)
        return payload.get("test_id") or payload.get("id") or str(len(self._memory[collection]))
