"""Usage limits (Phase 9): per-org / per-project quotas with enforcement."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Quota:
    """A resource quota with a windowed usage counter (resets via caller)."""

    limit: int
    used: int = 0

    @property
    def remaining(self) -> int:
        return self.limit - self.used

    def allow(self, n: int = 1) -> bool:
        return n <= self.remaining

    def consume(self, n: int = 1) -> None:
        if n > self.remaining:
            raise QuotaExceeded(self.limit, self.used, n)
        self.used += n


class QuotaExceeded(Exception):
    def __init__(self, limit: int, used: int, requested: int) -> None:
        super().__init__(f"quota exceeded: limit {limit}, used {used}, requested {requested}")
        self.limit = limit
        self.used = used
        self.requested = requested


@dataclass
class Limits:
    """Per-tenant limits for the resources the platform meters."""

    tests_per_run: int = 500
    runs_per_day: int = 50
    healing_per_run: int = 20
    storage_mb: int = 100


class UsageLimiter:
    """Tracks and enforces limits per tenant (org or project)."""

    def __init__(self, limits: Limits | None = None) -> None:
        self.limits = limits or Limits()
        self._quotas: dict[str, dict[str, Quota]] = {}
        self._meter: dict[str, dict[str, int]] = {}

    def _q(self, tenant: str, resource: str) -> Quota:
        self._quotas.setdefault(tenant, {})
        q = self._quotas[tenant].get(resource)
        if q is None:
            limit = getattr(self.limits, resource, 0)
            q = Quota(limit)
            self._quotas[tenant][resource] = q
        return q

    def check(self, tenant: str, resource: str, n: int = 1) -> bool:
        return self._q(tenant, resource).allow(n)

    def consume(self, tenant: str, resource: str, n: int = 1) -> None:
        self._q(tenant, resource).consume(n)
        self._meter.setdefault(tenant, {})
        self._meter[tenant][resource] = self._meter[tenant].get(resource, 0) + n

    def try_consume(self, tenant: str, resource: str, n: int = 1) -> bool:
        """Consume if allowed; return success (no exception)."""
        if not self.check(tenant, resource, n):
            return False
        self.consume(tenant, resource, n)
        return True

    def reset(self, tenant: str) -> None:
        self._quotas.pop(tenant, None)
        self._meter.pop(tenant, None)

    def usage(self, tenant: str) -> dict[str, int]:
        return dict(self._meter.get(tenant, {}))
