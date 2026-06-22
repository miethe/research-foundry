"""GitHub repository-search provider (discovery role).

Repo discovery via the GitHub Search API.  Search works unauthenticated at a
low rate limit, so :meth:`available` requires only that ``httpx`` is
importable; a token (if present) is added to raise the rate limit.  ``httpx``
is imported lazily inside :meth:`_fetch`.
"""

from __future__ import annotations

import time
from typing import Any

from .base import (
    BaseSearchProvider,
    ProviderResult,
    SearchHit,
    env_first,
    module_available,
    register,
)

_SEARCH_URL = "https://api.github.com/search/repositories"


class GitHubProvider(BaseSearchProvider):
    """Discovery provider backed by the GitHub repository search API."""

    id = "github"
    roles: tuple[str, ...] = ("discovery",)
    requires: tuple[str, ...] = ("httpx",)
    env_keys: tuple[str, ...] = ("RF_GITHUB_TOKEN", "GITHUB_TOKEN")

    def available(self) -> bool:
        """GitHub search works unauthenticated; only ``httpx`` is required."""
        return module_available("httpx")

    def _parse_search(self, payload: dict[str, Any]) -> list[SearchHit]:
        items = payload.get("items") or []
        hits: list[SearchHit] = []
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            hits.append(
                SearchHit(
                    title=item.get("full_name") or "",
                    url=item.get("html_url") or "",
                    snippet=item.get("description") or "",
                    provider="github",
                    rank=i + 1,
                    source_type="repo",
                    raw={"stars": item.get("stargazers_count")},
                )
            )
        return hits

    def _fetch(self, query: str, *, max_results: int, token: str | None) -> dict[str, Any]:
        import httpx

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        params: dict[str, str | int] = {"q": query, "per_page": max_results}
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
                error="github unavailable: httpx not installed",
            )
        token = env_first(*self.env_keys)
        started = time.monotonic()
        try:
            payload = self._fetch(query, max_results=max_results, token=token)
        except Exception as exc:  # noqa: BLE001
            return ProviderResult(
                provider=self.id,
                role="discovery",
                status="failed",
                queries_executed=1,
                latency_ms=int((time.monotonic() - started) * 1000),
                error=f"github search failed: {exc}",
            )
        hits = self._parse_search(payload)
        return ProviderResult(
            provider=self.id,
            role="discovery",
            status="success",
            hits=hits,
            queries_executed=1,
            estimated_cost_usd=0.0,
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    def extract(self, urls: list[str]) -> ProviderResult:
        return ProviderResult(
            provider=self.id,
            role=self.roles[0],
            status="skipped",
            error="github is discovery-only; use an extraction provider",
        )


register(GitHubProvider())
