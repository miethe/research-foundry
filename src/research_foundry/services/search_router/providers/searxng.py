"""SearXNG (aos-web) provider — free, keyless discovery + extraction lane.

Backed by the node-local ``aos-web`` shell tool (metasearch via a local
SearXNG instance plus a readable-text page fetch). No API key, no per-query
cost. ``aos-web`` is a shell binary rather than a Python module, so this
provider overrides :meth:`available` to probe ``PATH`` with :func:`shutil.which`
instead of using the module-based default.

Everything ``aos-web fetch`` returns is UNTRUSTED WEB CONTENT: the tool wraps
it in explicit ``--- BEGIN/END UNTRUSTED WEB CONTENT ---`` fences. We strip
those fence lines, defensively re-scan the body for prompt-injection phrasings
(:func:`scan_for_injection`), and always tag the resulting doc with an
``untrusted_web_content`` risk flag so downstream synthesis agents treat it as
data, never as instructions.

Both subprocess calls run with ``check=True`` and a timeout; any failure
(missing binary, SearXNG down, malformed JSON, timeout) is caught and returned
as a ``failed``/``degraded`` :class:`ProviderResult` — this provider never
raises for operational errors.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from typing import Any

from ..safety import scan_for_injection
from .base import (
    BaseSearchProvider,
    ExtractedDoc,
    ProviderResult,
    SearchHit,
    now_iso,
    register,
    text_sha256,
)

_AOS_WEB_BIN = "aos-web"
_UNTRUSTED_FLAG = "untrusted_web_content"
_FENCE_BEGIN_PREFIX = "--- BEGIN UNTRUSTED WEB CONTENT"
_FENCE_END_PREFIX = "--- END UNTRUSTED WEB CONTENT"
_DEFAULT_MAX_CHARS = 20000
_SEARCH_TIMEOUT = 30.0
_FETCH_TIMEOUT = 45.0


class SearxngProvider(BaseSearchProvider):
    """Free/keyless discovery + extraction via the node-local aos-web/SearXNG tool."""

    id = "searxng"
    roles: tuple[str, ...] = ("discovery", "extraction")
    requires: tuple[str, ...] = ()  # shell tool, not an importable Python module
    env_keys: tuple[str, ...] = ()  # keyless — no credentials ever sent

    def available(self) -> bool:
        """True when the ``aos-web`` binary is discoverable on ``PATH``."""
        return shutil.which(_AOS_WEB_BIN) is not None

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def _parse_search(self, payload: dict[str, Any], *, max_results: int) -> list[SearchHit]:
        """Parse raw SearXNG ``--json`` output into normalized hits (pure, no I/O)."""
        results = payload.get("results") or []
        hits: list[SearchHit] = []
        for result in results:
            if not isinstance(result, dict):
                continue
            hits.append(
                SearchHit(
                    title=(result.get("title") or "").strip(),
                    url=(result.get("url") or "").strip(),
                    snippet=(result.get("content") or "").strip(),
                    provider=self.id,
                    rank=len(hits) + 1,
                    score=result.get("score"),
                    published_at=result.get("publishedDate") or None,
                    source_type=None,
                    raw=result,
                )
            )
            if len(hits) >= max_results:
                break
        return hits

    def _run_search(self, query: str, *, max_results: int) -> dict[str, Any]:
        """Invoke ``aos-web search --json`` and parse its raw SearXNG JSON."""
        proc = subprocess.run(
            [_AOS_WEB_BIN, "search", query, "--n", str(max_results), "--json"],
            capture_output=True,
            text=True,
            timeout=_SEARCH_TIMEOUT,
            check=True,
        )
        data = json.loads(proc.stdout)
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
                error="searxng unavailable: aos-web binary not found on PATH",
            )
        started = time.monotonic()
        try:
            payload = self._run_search(query, max_results=max_results)
        except Exception as exc:  # noqa: BLE001 (subprocess/JSON -> failed, never raise)
            return ProviderResult(
                provider=self.id,
                role="discovery",
                status="failed",
                queries_executed=1,
                latency_ms=int((time.monotonic() - started) * 1000),
                error=f"searxng search failed: {exc}",
            )
        hits = self._parse_search(payload, max_results=max_results)
        return ProviderResult(
            provider=self.id,
            role="discovery",
            status="success",
            hits=hits,
            queries_executed=1,
            estimated_cost_usd=0.0,
            latency_ms=int((time.monotonic() - started) * 1000),
        )

    # ------------------------------------------------------------------
    # Extraction
    # ------------------------------------------------------------------

    def _strip_fence(self, text: str) -> str:
        """Remove aos-web's BEGIN/END untrusted-content fence lines from *text*."""
        kept = [
            line
            for line in (text or "").splitlines()
            if not line.startswith(_FENCE_BEGIN_PREFIX)
            and not line.startswith(_FENCE_END_PREFIX)
        ]
        return "\n".join(kept).strip()

    def _parse_extract(self, url: str, raw_text: str) -> ExtractedDoc:
        """Strip fences, scan for injection, tag as untrusted (pure, no I/O)."""
        body = self._strip_fence(raw_text)
        risk_flags = [_UNTRUSTED_FLAG, *scan_for_injection(body)]
        return ExtractedDoc(
            url=url,
            markdown=body,
            content_length_chars=len(body),
            text_hash=text_sha256(body),
            fetched_at=now_iso(),
            extractor=self.id,
            degraded=not body,
            risk_flags=risk_flags,
        )

    def _run_fetch(self, url: str, *, max_chars: int) -> str:
        """Invoke ``aos-web fetch`` and return its fenced plaintext output."""
        proc = subprocess.run(
            [_AOS_WEB_BIN, "fetch", url, "--max-chars", str(max_chars)],
            capture_output=True,
            text=True,
            timeout=_FETCH_TIMEOUT,
            check=True,
        )
        return proc.stdout

    def extract(self, urls: list[str]) -> ProviderResult:
        if not self.available():
            return ProviderResult(
                provider=self.id,
                role="extraction",
                status="skipped",
                error="searxng unavailable: aos-web binary not found on PATH",
            )
        started = time.monotonic()
        docs: list[ExtractedDoc] = []
        errors: list[str] = []
        for url in urls:
            try:
                raw = self._run_fetch(url, max_chars=_DEFAULT_MAX_CHARS)
            except Exception as exc:  # noqa: BLE001 (subprocess -> degraded, never raise)
                errors.append(f"{url}: {exc}")
                docs.append(self._parse_extract(url, ""))
                continue
            docs.append(self._parse_extract(url, raw))
        status = "degraded" if errors else "success"
        return ProviderResult(
            provider=self.id,
            role="extraction",
            status=status,
            docs=docs,
            latency_ms=int((time.monotonic() - started) * 1000),
            error="; ".join(errors) if errors else None,
        )


register(SearxngProvider())
