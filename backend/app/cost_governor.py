"""Cost governor: per-engagement token meter + hard budget enforcement.

The meter is the source of truth for the live budget meter in the UI. Weave
also records cost server-side; this gives us a synchronous number to gate on.
"""
from __future__ import annotations

from . import config
from .schemas import CostReport


class BudgetExceeded(Exception):
    def __init__(self, used: int, budget: int):
        self.used = used
        self.budget = budget
        super().__init__(f"engagement token budget exceeded: {used} > {budget}")


class CostMeter:
    """Tracks tokens + approximate USD per engagement, per agent."""

    def __init__(self, budget_tokens: int | None = None):
        self.budget_tokens = budget_tokens or config.ENGAGEMENT_TOKEN_BUDGET
        self.total_tokens = 0
        self.total_usd = 0.0
        self.by_agent: dict[str, dict[str, float]] = {}
        self._listeners: list = []

    def on_update(self, callback) -> None:
        """Register a callback(CostReport) fired after each record()."""
        self._listeners.append(callback)

    def check(self) -> None:
        """Raise if we are already over budget (call before a new LLM call)."""
        if self.total_tokens >= self.budget_tokens:
            raise BudgetExceeded(self.total_tokens, self.budget_tokens)

    def record(self, agent: str, model: str, total_tokens: int) -> None:
        usd = config.usd_for(model, total_tokens)
        self.total_tokens += total_tokens
        self.total_usd = round(self.total_usd + usd, 6)
        bucket = self.by_agent.setdefault(
            agent, {"tokens": 0, "usd": 0.0, "calls": 0}
        )
        bucket["tokens"] += total_tokens
        bucket["usd"] = round(bucket["usd"] + usd, 6)
        bucket["calls"] += 1
        report = self.report()
        for cb in self._listeners:
            try:
                cb(report)
            except Exception:
                pass

    def report(self) -> CostReport:
        return CostReport(
            total_tokens=self.total_tokens,
            total_usd=self.total_usd,
            budget_tokens=self.budget_tokens,
            by_agent={k: dict(v) for k, v in self.by_agent.items()},
            over_budget=self.total_tokens >= self.budget_tokens,
        )
