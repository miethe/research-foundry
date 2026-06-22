"""Brave Search API provider (discovery role).

Broad raw web discovery via the Brave Web Search API.  The HTTP client
(``httpx``) is imported lazily inside :meth:`_fetch` so the package imports
cleanly without the optional ``search`` extra installed.
"""

from __future__ import annotations

import time
from typing import Any

from .base import (
    BaseSearchProvider,
    ProviderResult,
    SearchHit,
    env_first,
    register,
)

_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_COST_PER_QUERY = 0.005


class BraveProvider(BaseSearchProvider):
    """Discovery provider backed by the Brave Web Search API."""

    id = "brave"
    roles: tuple[str, ...] = ("discovery",)
    requires: tuple[str, ...] = ("httpx",)
    env_keys: tuple[str, ...] = ("RF_BRAVE_API_KEY", "BRAVE_API_KEY")

    def _parse_search(self, payload: dict[str, Any]) -> list[SearchHit]:
        results = (payload.get("web") or {}).get("results") or []
        hits: list[SearchHit] = []
        for i, result in enumerate(results):
            if not isinstance(result, dict):
                continue
            hits.append(
                SearchHit(
                    title=result.get("title") or "",
                    url=result.get("url") or "",
                    snippet=result.get("description") or "",
                    provider="brave",
                    rank=i + 1,
                    source_type=None,
                    raw=result,
                )
            )
        return hits

    def _fetch(self, query: str, *, max_results: int, key: str) -> dict[str, Any]:
        import httpx

        headers = {
            "X-Subscription-Token": key,
            "Accept": "application/json",
        }
        params: dict[str, str | int] = {"q": query, "count": max_results}
        resp = httpx.get(_SEARCH_URL, params=params, headers=headers, timeout=20.0)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {}

    def search(
        self,
        query: str,
        *,
        max_results: int,
        constraints: dict[str, Any],
    ) -> ProviderResult:
        if not self.available():
            return ProviderResult(
                provider=self.id,
                role="discovery",
                status="skipped",
                error="brave unavailable: httpx missing or no API key set",
            )
        key = env_first(*self.env_keys) or ""
        started = time.monotonic()
        try:
            payload = self._fetch(query, max_results=max_results, key=key)
        except Exception as exc:  # noqa: BLE001 (network/runtime -> degraded, never raise)
            return ProviderResult(
                provider=self.id,
                role="discovery",
                status="failed",
                queries_executed=1,
                latency_ms=int((time.monotonic() - started) * 1000),
                error=f"brave fetch failed: {exc}",
            )
        hits = self._parse_search(payload)
        return ProviderResult(
            provider=self.id,
            role="discovery",
            status="success",
            hits=hits,
            queries_executed=1,
            estimated_cost_usd=_COST_PER_QUERY,
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    def extract(self, urls: list[str]) -> ProviderResult:
        return ProviderResult(
            provider=self.id,
            role=self.roles[0],
            status="skipped",
            error="brave is discovery-only; use an extraction provider",
        )


register(BraveProvider())
