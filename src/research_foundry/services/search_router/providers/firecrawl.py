"""Firecrawl provider (extraction + discovery roles).

Robust Markdown extraction (``/v1/scrape``) and SERP discovery
(``/v1/search``) via the Firecrawl API.  ``httpx`` is imported lazily inside
:meth:`_fetch_scrape` / :meth:`_fetch_search`.
"""

from __future__ import annotations

import time
from typing import Any

from ..safety import scan_for_injection
from .base import (
    BaseSearchProvider,
    ExtractedDoc,
    ProviderResult,
    SearchHit,
    env_first,
    now_iso,
    register,
    text_sha256,
)

_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"
_SEARCH_URL = "https://api.firecrawl.dev/v1/search"
_COST_PER_PAGE = 0.001  # scrape placeholder
_COST_PER_SEARCH = 0.002  # ~2 credits per 10 results placeholder


class FirecrawlProvider(BaseSearchProvider):
    """Extraction + discovery provider backed by the Firecrawl API."""

    id = "firecrawl"
    roles: tuple[str, ...] = ("extraction", "discovery")
    requires: tuple[str, ...] = ("httpx",)
    env_keys: tuple[str, ...] = ("RF_FIRECRAWL_API_KEY", "FIRECRAWL_API_KEY")

    def _parse_extract(self, url: str, payload: dict[str, Any]) -> ExtractedDoc:
        data = payload.get("data") or {}
        markdown = data.get("markdown") or "" if isinstance(data, dict) else ""
        return ExtractedDoc(
            url=url,
            markdown=markdown,
            content_length_chars=len(markdown),
            text_hash=text_sha256(markdown),
            fetched_at=now_iso(),
            extractor="firecrawl",
            degraded=not markdown,
            risk_flags=scan_for_injection(markdown),
            raw=data if isinstance(data, dict) else {},
        )

    def _parse_search(self, payload: dict[str, Any]) -> list[SearchHit]:
        results = payload.get("data") or []
        hits: list[SearchHit] = []
        for i, result in enumerate(results):
            if not isinstance(result, dict):
                continue
            hits.append(
                SearchHit(
                    title=result.get("title") or "",
                    url=result.get("url") or "",
                    snippet=result.get("description") or "",
                    provider="firecrawl",
                    rank=i + 1,
                    raw=result,
                )
            )
        return hits

    def _fetch_scrape(self, url: str, *, key: str) -> dict[str, Any]:
        import httpx

        headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
        body = {"url": url, "formats": ["markdown"]}
        resp = httpx.post(_SCRAPE_URL, json=body, headers=headers, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {}

    def _fetch_search(self, query: str, *, max_results: int, key: str) -> dict[str, Any]:
        import httpx

        headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
        body = {"query": query, "limit": max_results}
        resp = httpx.post(_SEARCH_URL, json=body, headers=headers, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        return data if isinstance(data, dict) else {}

    def extract(self, urls: list[str]) -> ProviderResult:
        if not self.available():
            return ProviderResult(
                provider=self.id,
                role="extraction",
                status="skipped",
                error="firecrawl unavailable: httpx missing or no API key set",
            )
        key = env_first(*self.env_keys) or ""
        started = time.monotonic()
        docs: list[ExtractedDoc] = []
        errors: list[str] = []
        for url in urls:
            try:
                payload = self._fetch_scrape(url, key=key)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{url}: {exc}")
                docs.append(self._parse_extract(url, {}))
                continue
            docs.append(self._parse_extract(url, payload))
        status = "degraded" if errors else "success"
        return ProviderResult(
            provider=self.id,
            role="extraction",
            status=status,
            docs=docs,
            estimated_cost_usd=_COST_PER_PAGE * len(urls),
            latency_ms=int((time.monotonic() - started) * 1000),
            error="; ".join(errors) if errors else None,
        )

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
                error="firecrawl unavailable: httpx missing or no API key set",
            )
        key = env_first(*self.env_keys) or ""
        started = time.monotonic()
        try:
            payload = self._fetch_search(query, max_results=max_results, key=key)
        except Exception as exc:  # noqa: BLE001
            return ProviderResult(
                provider=self.id,
                role="discovery",
                status="failed",
                queries_executed=1,
                latency_ms=int((time.monotonic() - started) * 1000),
                error=f"firecrawl search failed: {exc}",
            )
        hits = self._parse_search(payload)
        return ProviderResult(
            provider=self.id,
            role="discovery",
            status="success",
            hits=hits,
            queries_executed=1,
            estimated_cost_usd=_COST_PER_SEARCH,
            latency_ms=int((time.monotonic() - started) * 1000),
        )


register(FirecrawlProvider())
