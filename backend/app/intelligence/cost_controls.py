"""Cost controls + model routing (Phase 9).

Token accounting, budget enforcement, and a model-routing policy that picks the
cheapest model satisfying a task's requirements — the "cost efficiency"
dimension of the AI-QE score made operational.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ModelPricing:
    """Cost per 1M tokens (input, output) and a capability tier."""

    name: str
    input_per_1m: float
    output_per_1m: float
    tier: str = "basic"  # "basic" | "standard" | "premium"


@dataclass
class Budget:
    """A spending budget in USD with an optional hard stop."""

    limit_usd: float
    spent_usd: float = 0.0

    @property
    def remaining(self) -> float:
        return self.limit_usd - self.spent_usd

    def can_spend(self, amount: float) -> bool:
        return amount <= self.remaining

    def record(self, amount: float) -> None:
        if amount > self.remaining:
            raise BudgetExceeded(self.limit_usd, self.spent_usd, amount)
        self.spent_usd += amount


class BudgetExceeded(Exception):
    def __init__(self, limit: float, spent: float, amount: float) -> None:
        super().__init__(
            f"budget exceeded: limit ${limit:.4f}, spent ${spent:.4f}, "
            f"requested ${amount:.4f}"
        )
        self.limit = limit
        self.spent = spent
        self.amount = amount


@dataclass
class Usage:
    """Cumulative token/cost accounting."""

    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    calls: int = 0

    def record(self, model: ModelPricing, in_tokens: int, out_tokens: int) -> None:
        self.input_tokens += in_tokens
        self.output_tokens += out_tokens
        self.calls += 1
        self.cost_usd += (
            in_tokens * model.input_per_1m + out_tokens * model.output_per_1m
        ) / 1_000_000.0


class ModelRouter:
    """Routes a task to the cheapest model whose tier satisfies the task."""

    def __init__(self, models: list[ModelPricing]) -> None:
        self.models = sorted(
            models, key=lambda m: (m.input_per_1m + m.output_per_1m)
        )

    def route(self, required_tier: str = "basic") -> ModelPricing | None:
        """Return the cheapest model at or above the required tier."""
        tier_rank = {"basic": 0, "standard": 1, "premium": 2}
        want = tier_rank.get(required_tier, 0)
        for m in self.models:  # already sorted cheapest-first
            if tier_rank.get(m.tier, 0) >= want:
                return m
        return None


class CostController:
    """Combined budget + usage + routing with enforcement."""

    def __init__(
        self,
        models: list[ModelPricing],
        budget: Budget,
        *,
        require_tier: str = "basic",
    ) -> None:
        self.router = ModelRouter(models)
        self.budget = budget
        self.require_tier = require_tier
        self.usage = Usage()

    def estimate_cost(self, model: ModelPricing, in_tokens: int, out_tokens: int) -> float:
        return (
            in_tokens * model.input_per_1m + out_tokens * model.output_per_1m
        ) / 1_000_000.0

    def record(self, in_tokens: int, out_tokens: int) -> ModelPricing | None:
        """Route, charge, and record one LLM call.

        Returns the routed model, or ``None`` if no model fits the budget/tier.
        """
        model = self.router.route(self.require_tier)
        if model is None:
            return None
        cost = self.estimate_cost(model, in_tokens, out_tokens)
        if not self.budget.can_spend(cost):
            return None
        self.budget.record(cost)
        self.usage.record(model, in_tokens, out_tokens)
        return model

    def summary(self) -> dict[str, Any]:
        return {
            "spent_usd": round(self.budget.spent_usd, 4),
            "remaining_usd": round(self.budget.remaining, 4),
            "input_tokens": self.usage.input_tokens,
            "output_tokens": self.usage.output_tokens,
            "calls": self.usage.calls,
            "cost_usd": round(self.usage.cost_usd, 4),
        }
