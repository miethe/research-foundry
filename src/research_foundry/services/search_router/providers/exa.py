"""Exa semantic-search provider (discovery role).

Semantic / "find things like this" discovery via the Exa search API.
``httpx`` is imported lazily inside :meth:`_fetch`.
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

_SEARCH_URL = "https://api.exa.ai/search"
_COST_PER_QUERY = 0.007


class ExaProvider(BaseSearchProvider):
    """Discovery provider backed by the Exa semantic search API."""

    id = "exa"
    roles: tuple[str, ...] = ("discovery",)
    requires: tuple[str, ...] = ("httpx",)
    env_keys: tuple[str, ...] = ("RF_EXA_API_KEY", "EXA_API_KEY")

    def _parse_search(self, payload: dict[str, Any]) -> list[SearchHit]:
        results = payload.get("results") or []
        hits: list[SearchHit] = []
        for i, result in enumerate(results):
            if not isinstance(result, dict):
                continue
            hits.append(
                SearchHit(
                    title=result.get("title") or "",
                    url=result.get("url") or "",
                    snippet=result.get("text") or "",
                    provider="exa",
                    rank=i + 1,
                    score=result.get("score"),
                    published_at=result.get("publishedDate"),
                    raw=result,
                )
            )
        return hits

    def _fetch(self, query: str, *, max_results: int, key: str) -> dict[str, Any]:
        import httpx

        headers = {"x-api-key": key, "Accept": "application/json"}
        body = {"query": query, "numResults": max_results}
        resp = httpx.post(_SEARCH_URL, json=body, headers=headers, timeout=20.0)
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
                error="exa unavailable: httpx missing or no API key set",
            )
        key = env_first(*self.env_keys) or ""
        started = time.monotonic()
        try:
            payload = self._fetch(query, max_results=max_results, key=key)
        except Exception as exc:  # noqa: BLE001
            return ProviderResult(
                provider=self.id,
                role="discovery",
                status="failed",
                queries_executed=1,
                latency_ms=int((time.monotonic() - started) * 1000),
                error=f"exa fetch failed: {exc}",
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
            error="exa is discovery-only; use an extraction provider",
        )


register(ExaProvider())
