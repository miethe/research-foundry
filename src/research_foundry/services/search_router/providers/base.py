"""Provider base contracts for the Research Foundry Search Router.

Every search/extraction provider must:

1. Implement the :class:`SearchProvider` protocol (id, roles, requires,
   env_keys, available(), search(), extract()).
2. Return a :class:`ProviderResult` — never raise for missing creds or
   network failures; instead set ``status="degraded"`` and leave hits/docs empty.
3. Be registered via :func:`register` so the router can discover all providers.

Pattern mirrors :mod:`research_foundry.adapters.base`:
:func:`module_available` is imported from there; the dataclass + registry
pattern is identical.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from research_foundry.adapters.base import module_available

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def env_first(*names: str) -> str | None:
    """Return the value of the first environment variable in *names* that is set."""
    for name in names:
        val = os.environ.get(name)
        if val:
            return val
    return None


def text_sha256(text: str) -> str:
    """Return ``'sha256:' + hexdigest`` of *text* encoded as UTF-8."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def now_iso() -> str:
    """Return the current UTC time as a timezone-aware ISO 8601 string."""
    return datetime.now(UTC).isoformat()


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SearchHit:
    """A single search result from a discovery provider."""

    title: str
    url: str
    snippet: str = ""
    provider: str = ""
    rank: int = 0
    score: float | None = None
    source_type: str | None = None
    published_at: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "snippet": self.snippet,
            "provider": self.provider,
            "rank": self.rank,
            "score": self.score,
            "source_type": self.source_type,
            "published_at": self.published_at,
        }


@dataclass
class ExtractedDoc:
    """A document extracted (markdown) from a URL by an extraction provider."""

    url: str
    markdown: str
    title: str | None = None
    content_length_chars: int = 0
    text_hash: str = ""
    fetched_at: str = ""
    extractor: str = ""
    degraded: bool = False
    risk_flags: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "content_length_chars": self.content_length_chars,
            "text_hash": self.text_hash,
            "fetched_at": self.fetched_at,
            "extractor": self.extractor,
            "degraded": self.degraded,
            "risk_flags": list(self.risk_flags),
        }


@dataclass
class ProviderResult:
    """Aggregated output from one provider invocation."""

    provider: str
    role: str  # discovery | extraction | crawl | synthesis | verification
    status: str  # success | partial | failed | skipped | degraded
    hits: list[SearchHit] = field(default_factory=list)
    docs: list[ExtractedDoc] = field(default_factory=list)
    queries_executed: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "role": self.role,
            "status": self.status,
            "queries_executed": self.queries_executed,
            "estimated_cost_usd": self.estimated_cost_usd,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "hits": [h.to_dict() for h in self.hits],
            "docs": [d.to_dict() for d in self.docs],
        }


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SearchProvider(Protocol):
    """Protocol every search/extraction provider must satisfy."""

    id: str
    roles: tuple[str, ...]
    requires: tuple[str, ...]
    env_keys: tuple[str, ...]

    def available(self) -> bool:
        """True when all required modules are importable AND at least one env key is set."""
        ...

    def search(
        self,
        query: str,
        *,
        max_results: int,
        constraints: dict[str, Any],
    ) -> ProviderResult:
        """Execute a search query and return normalized hits."""
        ...

    def extract(self, urls: list[str]) -> ProviderResult:
        """Extract markdown from one or more URLs."""
        ...


# ---------------------------------------------------------------------------
# Base implementation
# ---------------------------------------------------------------------------


class BaseSearchProvider:
    """Convenience base implementing :meth:`available` from :attr:`requires` and
    :attr:`env_keys`.

    Subclasses must override :meth:`search` and :meth:`extract`.  The default
    implementations raise :exc:`NotImplementedError` to make contract violations
    obvious during development.
    """

    id: str = "base"
    roles: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    env_keys: tuple[str, ...] = ()

    def available(self) -> bool:
        """True when every required module is importable AND ≥1 env key is set."""
        modules_ok = all(module_available(m) for m in self.requires)
        key_ok = any(env_first(k) is not None for k in self.env_keys) if self.env_keys else True
        return modules_ok and key_ok

    def search(
        self,
        query: str,
        *,
        max_results: int,
        constraints: dict[str, Any],
    ) -> ProviderResult:  # pragma: no cover
        raise NotImplementedError(f"{self.id}.search() not implemented")

    def extract(self, urls: list[str]) -> ProviderResult:  # pragma: no cover
        raise NotImplementedError(f"{self.id}.extract() not implemented")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, SearchProvider] = {}


def register(provider: SearchProvider) -> SearchProvider:
    """Register a provider instance under its ``id`` (idempotent)."""
    _REGISTRY[provider.id] = provider
    return provider


def get_provider(provider_id: str) -> SearchProvider | None:
    """Return the registered provider with *provider_id*, or ``None``."""
    return _REGISTRY.get(provider_id)


def all_providers() -> dict[str, SearchProvider]:
    """Return a shallow copy of the provider registry."""
    return dict(_REGISTRY)


__all__ = [
    "module_available",
    "env_first",
    "text_sha256",
    "now_iso",
    "SearchHit",
    "ExtractedDoc",
    "ProviderResult",
    "SearchProvider",
    "BaseSearchProvider",
    "register",
    "get_provider",
    "all_providers",
]
