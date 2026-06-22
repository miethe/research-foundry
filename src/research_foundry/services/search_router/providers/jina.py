"""Jina Reader provider (extraction role).

Cheap URL-to-Markdown extraction via the Jina Reader endpoint
(``https://r.jina.ai/<url>``).  The Reader works *without* an API key; a key
is optional and only raises rate limits, so :meth:`available` requires only
that ``httpx`` is importable.  ``httpx`` is imported lazily inside
:meth:`_fetch`.
"""

from __future__ import annotations

import time
from typing import Any

from ..safety import scan_for_injection
from .base import (
    BaseSearchProvider,
    ExtractedDoc,
    ProviderResult,
    env_first,
    module_available,
    now_iso,
    register,
    text_sha256,
)

_READER_BASE = "https://r.jina.ai/"


class JinaProvider(BaseSearchProvider):
    """Extraction provider backed by the keyless-capable Jina Reader."""

    id = "jina"
    roles: tuple[str, ...] = ("extraction",)
    requires: tuple[str, ...] = ("httpx",)
    env_keys: tuple[str, ...] = ("RF_JINA_API_KEY", "JINA_API_KEY")

    def available(self) -> bool:
        """Jina Reader works keyless; only ``httpx`` is required."""
        return module_available("httpx")

    def _parse_extract(self, url: str, text: str) -> ExtractedDoc:
        text = text or ""
        return ExtractedDoc(
            url=url,
            markdown=text,
            content_length_chars=len(text),
            text_hash=text_sha256(text),
            fetched_at=now_iso(),
            extractor="jina",
            degraded=not text,
            risk_flags=scan_for_injection(text),
        )

    def _fetch(self, url: str, *, key: str | None) -> str:
        import httpx

        headers = {"Accept": "text/plain"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        resp = httpx.get(f"{_READER_BASE}{url}", headers=headers, timeout=30.0)
        resp.raise_for_status()
        return resp.text

    def extract(self, urls: list[str]) -> ProviderResult:
        if not self.available():
            return ProviderResult(
                provider=self.id,
                role="extraction",
                status="skipped",
                error="jina unavailable: httpx not installed",
            )
        key = env_first(*self.env_keys)
        started = time.monotonic()
        docs: list[ExtractedDoc] = []
        errors: list[str] = []
        for url in urls:
            try:
                text = self._fetch(url, key=key)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{url}: {exc}")
                docs.append(self._parse_extract(url, ""))
                continue
            docs.append(self._parse_extract(url, text))
        status = "degraded" if errors else "success"
        return ProviderResult(
            provider=self.id,
            role="extraction",
            status=status,
            docs=docs,
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
        return ProviderResult(
            provider=self.id,
            role="discovery",
            status="skipped",
            error="jina is extraction-only; use a discovery provider",
        )


register(JinaProvider())
