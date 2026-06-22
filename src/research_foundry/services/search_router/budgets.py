"""Budget enforcement for the Research Foundry Search Router.

:class:`Budget` captures the hard limits for one search run (queries, URLs,
pages, cost, latency). :class:`BudgetTracker` tracks real-time consumption
and provides gate methods so the router can decide whether to continue before
each provider call.

Usage::

    from research_foundry.services.search_router.budgets import Budget, BudgetTracker

    budget = Budget(max_external_queries=3, max_provider_cost_usd=0.10)
    tracker = BudgetTracker(budget)
    if tracker.can_query():
        tracker.add_query()
    if tracker.can_extract(more=2):
        tracker.add_extract(2)
    if reason := tracker.exceeded():
        print(f"Budget exceeded: {reason}")
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Budget dataclass
# ---------------------------------------------------------------------------


@dataclass
class Budget:
    """Hard limits for a single search run.

    All limits are inclusive maximums.  Set a limit to 0 to disable the
    corresponding operation entirely (e.g. ``max_crawl_pages=0`` disables
    crawling).
    """

    max_external_queries: int = 4
    max_urls_to_extract: int = 8
    max_crawl_pages: int = 0
    max_provider_cost_usd: float = 0.25
    max_latency_seconds: int = 90

    @classmethod
    def from_request_dict(cls, request: dict[str, Any]) -> Budget:
        """Build a :class:`Budget` from a ``search_request`` budget sub-dict.

        Missing keys fall back to class defaults.
        """
        raw: dict[str, Any] = request.get("budget", {}) or {}
        return cls(
            max_external_queries=int(raw.get("max_external_queries", cls.max_external_queries)),
            max_urls_to_extract=int(raw.get("max_urls_to_extract", cls.max_urls_to_extract)),
            max_crawl_pages=int(raw.get("max_crawl_pages", cls.max_crawl_pages)),
            max_provider_cost_usd=float(
                raw.get("max_provider_cost_usd", cls.max_provider_cost_usd)
            ),
            max_latency_seconds=int(raw.get("max_latency_seconds", cls.max_latency_seconds)),
        )

    def merge_mode_defaults(self, mode_budget: dict[str, Any]) -> Budget:
        """Return a new :class:`Budget` using *mode_budget* as fallback defaults.

        Values already set on *self* take precedence; mode defaults fill gaps
        where the request did not explicitly specify a limit.
        """
        # We treat "default" Budget values as unset when they equal the
        # dataclass field defaults.  A request override is respected as-is.
        defaults = Budget()
        return Budget(
            max_external_queries=(
                self.max_external_queries
                if self.max_external_queries != defaults.max_external_queries
                else int(mode_budget.get("max_external_queries", self.max_external_queries))
            ),
            max_urls_to_extract=(
                self.max_urls_to_extract
                if self.max_urls_to_extract != defaults.max_urls_to_extract
                else int(mode_budget.get("max_urls_to_extract", self.max_urls_to_extract))
            ),
            max_crawl_pages=(
                self.max_crawl_pages
                if self.max_crawl_pages != defaults.max_crawl_pages
                else int(mode_budget.get("max_crawl_pages", self.max_crawl_pages))
            ),
            max_provider_cost_usd=(
                self.max_provider_cost_usd
                if self.max_provider_cost_usd != defaults.max_provider_cost_usd
                else float(
                    mode_budget.get("max_provider_cost_usd", self.max_provider_cost_usd)
                )
            ),
            max_latency_seconds=(
                self.max_latency_seconds
                if self.max_latency_seconds != defaults.max_latency_seconds
                else int(mode_budget.get("max_latency_seconds", self.max_latency_seconds))
            ),
        )


# ---------------------------------------------------------------------------
# BudgetTracker
# ---------------------------------------------------------------------------


@dataclass
class BudgetTracker:
    """Tracks real-time consumption against a :class:`Budget`.

    The tracker is stateful and intended for single-run lifetime.  Call
    :meth:`exceeded` to get a human-readable reason string when any limit is
    breached, or ``None`` when still within budget.
    """

    budget: Budget
    _queries: int = field(default=0, init=False, repr=False)
    _urls: int = field(default=0, init=False, repr=False)
    _cost: float = field(default=0.0, init=False, repr=False)
    _start: float = field(default_factory=time.monotonic, init=False, repr=False)

    # -- gates ---------------------------------------------------------------

    def can_query(self) -> bool:
        """True when at least one more external query is allowed."""
        return self._queries < self.budget.max_external_queries

    def can_extract(self, more: int = 1) -> bool:
        """True when *more* additional URL extractions are within budget."""
        return (self._urls + more) <= self.budget.max_urls_to_extract

    # -- accumulators --------------------------------------------------------

    def add_query(self) -> None:
        """Record one external query."""
        self._queries += 1

    def add_extract(self, n: int = 1) -> None:
        """Record *n* URL extractions."""
        self._urls += n

    def add_cost(self, usd: float) -> None:
        """Accumulate *usd* to the running cost total."""
        self._cost += usd

    # -- summary properties --------------------------------------------------

    @property
    def queries(self) -> int:
        return self._queries

    @property
    def urls(self) -> int:
        return self._urls

    @property
    def cost(self) -> float:
        return self._cost

    @property
    def elapsed_seconds(self) -> float:
        return time.monotonic() - self._start

    # -- exceeded gate -------------------------------------------------------

    def exceeded(self) -> str | None:
        """Return a reason string if any hard limit is breached, else ``None``."""
        if self._queries > self.budget.max_external_queries:
            return (
                f"query limit exceeded: {self._queries} > "
                f"{self.budget.max_external_queries}"
            )
        if self._urls > self.budget.max_urls_to_extract:
            return (
                f"url extraction limit exceeded: {self._urls} > "
                f"{self.budget.max_urls_to_extract}"
            )
        if self._cost > self.budget.max_provider_cost_usd:
            return (
                f"cost limit exceeded: ${self._cost:.4f} > "
                f"${self.budget.max_provider_cost_usd:.4f}"
            )
        if self.elapsed_seconds > self.budget.max_latency_seconds:
            return (
                f"latency limit exceeded: {self.elapsed_seconds:.1f}s > "
                f"{self.budget.max_latency_seconds}s"
            )
        return None


__all__ = ["Budget", "BudgetTracker"]
