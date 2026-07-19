"""Tests for the PDF-aware wiring in ``extract_urls`` (TASK-3.2).

OFFLINE-ONLY: the PDF "download" is monkeypatched (no network call); the
non-PDF regression case uses the same ``FakeExtractionProvider`` pattern as
``tests/test_search_router_router.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.services.search_router.providers.base import ExtractedDoc, ProviderResult
from research_foundry.services.search_router.router import extract_urls
from research_foundry.services.source_cards import list_source_cards

# ---------------------------------------------------------------------------
# Minimal, structurally-valid single-page PDF builder (mirrors
# tests/test_pdf_extractor.py's ``_build_minimal_pdf`` so this file stays
# self-contained rather than importing across test modules).
# ---------------------------------------------------------------------------


def _build_minimal_pdf(content_stream: str) -> bytes:
    def obj(n: int, body: str) -> bytes:
        return f"{n} 0 obj\n{body}\nendobj\n".encode()

    stream_obj = (
        f"5 0 obj\n<< /Length {len(content_stream)} >>\nstream\n"
        f"{content_stream}\nendstream\nendobj\n"
    ).encode()

    objects = [
        obj(1, "<< /Type /Catalog /Pages 2 0 R >>"),
        obj(2, "<< /Type /Pages /Kids [3 0 R] /Count 1 >>"),
        obj(
            3,
            "<< /Type /Page /Parent 2 0 R "
            "/Resources << /Font << /F1 4 0 R >> >> "
            "/MediaBox [0 0 200 200] /Contents 5 0 R >>",
        ),
        obj(4, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"),
        stream_obj,
    ]

    body = b"%PDF-1.4\n"
    offsets: list[int] = []
    for o in objects:
        offsets.append(len(body))
        body += o

    n_objs = len(objects) + 1  # + object 0 (free)
    xref_offset = len(body)
    xref = "xref\n" f"0 {n_objs}\n" "0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n"
    trailer = f"trailer\n<< /Size {n_objs} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF"

    return body + xref.encode() + trailer.encode()


PDF_WITH_TEXT = _build_minimal_pdf("BT /F1 24 Tf 10 100 Td (Hello Research Foundry) Tj ET")


class _FakeUrlopenCtx:
    """Minimal context manager mimicking ``urllib.request.urlopen``'s return value."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def __enter__(self) -> "_FakeUrlopenCtx":
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def read(self) -> bytes:
        return self._data


class FakeExtractionProvider:
    """Same shape as the fake used in test_search_router_router.py."""

    id = "jina"
    roles = ("extraction",)
    requires: tuple[str, ...] = ()
    env_keys: tuple[str, ...] = ()

    def available(self) -> bool:
        return True

    def search(self, query: str, *, max_results: int, constraints: dict[str, Any]) -> ProviderResult:
        return ProviderResult(provider="jina", role="extraction", status="skipped")

    def extract(self, urls: list[str]) -> ProviderResult:
        docs = [
            ExtractedDoc(
                url=urls[0], markdown="# Extracted\n\nExtracted body content.",
                title="Doc", content_length_chars=24, extractor="jina",
            )
        ]
        return ProviderResult(
            provider="jina", role="extraction", status="success",
            docs=docs, estimated_cost_usd=0.02,
        )


# ---------------------------------------------------------------------------
# PDF URL detection + wiring
# ---------------------------------------------------------------------------


def test_pdf_url_with_text_layer_is_not_degraded(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda url, timeout=8: _FakeUrlopenCtx(PDF_WITH_TEXT),
    )

    result = extract_urls(
        ["https://example.com/paper.pdf"], paths=tmp_foundry, providers={}
    )

    assert result["degraded"] is False
    assert len(result["source_cards"]) == 1
    assert len(list_source_cards(result["run_id"], paths=tmp_foundry)) == 1


def test_pdf_url_download_failure_degrades_but_does_not_raise(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(url: str, timeout: int = 8) -> Any:
        raise OSError("network unreachable")

    monkeypatch.setattr("urllib.request.urlopen", _boom)

    result = extract_urls(
        ["https://example.com/missing.pdf"], paths=tmp_foundry, providers={}
    )

    assert result["degraded"] is True
    assert len(result["source_cards"]) == 1  # degraded card still written, no raise


def test_non_pdf_url_still_uses_extraction_provider_chain(
    tmp_foundry: FoundryPaths,
) -> None:
    result = extract_urls(
        ["https://example.com/page"],
        paths=tmp_foundry,
        providers={"jina": FakeExtractionProvider()},
    )

    assert result["degraded"] is False
    assert len(result["source_cards"]) == 1
