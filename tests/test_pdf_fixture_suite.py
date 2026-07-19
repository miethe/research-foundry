"""End-to-end PDF fixture suite for the ``rf fetch`` pipeline (TASK-3.5).

TASK-3.1 (``tests/test_pdf_extractor.py``) and TASK-3.2
(``tests/test_search_router_pdf_wiring.py``) cover ``extract_pdf`` and the
router's PDF-detection wiring at the unit/wiring level. This suite closes the
loop end-to-end: it drives the real ``extract_urls`` entry point (the ``rf
fetch`` pipeline) with PDF fixtures and asserts the correct
``extraction_status`` surfaces all the way through to the written source
card's frontmatter, matching the plan's AC-RFUP2-1 / AC-RFUP2-2 / AC-RFUP2-4.

OFFLINE-ONLY: ``urllib.request.urlopen`` is monkeypatched so no network call
is ever made; this mirrors the exact pattern used in
``tests/test_search_router_pdf_wiring.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from research_foundry.frontmatter import load_md
from research_foundry.paths import FoundryPaths
from research_foundry.services.extractors import pdf_extractor
from research_foundry.services.extractors.pdf_extractor import PdfExtractionResult
from research_foundry.services.search_router.router import extract_urls
from research_foundry.services.source_cards import list_source_cards

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "assertion_ledger" / "p2_formats"
MALFORMED_PDF_PATH = FIXTURE_DIR / "fixture.pdf"


# ---------------------------------------------------------------------------
# Minimal, structurally-valid single-page PDF builder (mirrors
# tests/test_pdf_extractor.py's ``_build_minimal_pdf`` / the copy in
# tests/test_search_router_pdf_wiring.py so this file stays self-contained
# rather than importing across test modules).
# ---------------------------------------------------------------------------


def _build_minimal_pdf(content_stream: str) -> bytes:
    """Hand-build a minimal, structurally-valid single-page PDF.

    Computes real byte offsets for the xref table so pypdf can parse it
    without needing a heavyweight PDF-generation dependency.
    """

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
PDF_WITHOUT_TEXT = _build_minimal_pdf("")


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


def _fake_urlopen(data: bytes) -> Any:
    def _open(url: str, timeout: int = 8) -> _FakeUrlopenCtx:
        return _FakeUrlopenCtx(data)

    return _open


def _card_extraction_status(run_id: str, paths: FoundryPaths) -> tuple[str | None, dict]:
    """Read the single source card written for ``run_id`` and return its frontmatter."""

    cards = list_source_cards(run_id, paths=paths)
    assert len(cards) == 1
    front_matter, _body = load_md(cards[0])
    return front_matter.get("extraction_status"), front_matter


# ---------------------------------------------------------------------------
# Scenario 1: extractable text layer -> full_text, not degraded
# ---------------------------------------------------------------------------


def test_pdf_with_text_layer_surfaces_full_text_end_to_end(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen(PDF_WITH_TEXT))

    result = extract_urls(
        ["https://example.com/paper.pdf"], paths=tmp_foundry, providers={}
    )

    assert result["degraded"] is False
    status, _front_matter = _card_extraction_status(result["run_id"], tmp_foundry)
    assert status == "full_text"


# ---------------------------------------------------------------------------
# Scenario 2: structurally-valid PDF with no text-showing operator (scanned /
# image-only style) -> locator_only
# ---------------------------------------------------------------------------


def test_pdf_without_text_layer_surfaces_locator_only_end_to_end(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen(PDF_WITHOUT_TEXT))

    result = extract_urls(
        ["https://example.com/scanned.pdf"], paths=tmp_foundry, providers={}
    )

    status, _front_matter = _card_extraction_status(result["run_id"], tmp_foundry)
    assert status == "locator_only"


# ---------------------------------------------------------------------------
# Scenario 3: corrupted / malformed PDF bytes -> locator_only, no exception,
# source card still written (degrade-safe contract)
# ---------------------------------------------------------------------------


def test_corrupted_pdf_surfaces_locator_only_without_raising_end_to_end(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    malformed = MALFORMED_PDF_PATH.read_bytes()
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen(malformed))

    result = extract_urls(
        ["https://example.com/corrupted.pdf"], paths=tmp_foundry, providers={}
    )

    assert len(result["source_cards"]) == 1
    status, _front_matter = _card_extraction_status(result["run_id"], tmp_foundry)
    assert status == "locator_only"


# ---------------------------------------------------------------------------
# Scenario 3b: PDF text extraction truncated by the >100KB size guard
# (``_MAX_TEXT_CHARS`` in pdf_extractor.py) -> "partial", not "full_text".
#
# Regression test for the FIX-REQUIRED validator finding on Phase 3 fix cycle
# 1: ``extract_urls``'s PDF branch previously discarded
# ``PdfExtractionResult.status`` and only forwarded ``.text`` to
# ``create_source_card``, so a truncated PDF's non-empty (but partial)
# content was mislabeled "full_text" by ``create_source_card``'s
# content-derived default. ``extract_pdf`` itself is monkeypatched to return
# a "partial" result directly (per the validator's guidance) rather than
# constructing a real >100KB PDF fixture, since the size guard is exercised
# separately in ``tests/test_pdf_extractor.py``; this test's sole purpose is
# to prove the tri-state status survives the full ``extract_urls`` pipeline.
# ---------------------------------------------------------------------------


def test_pdf_truncated_by_size_guard_surfaces_partial_end_to_end(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen(PDF_WITH_TEXT))
    monkeypatch.setattr(
        "research_foundry.services.search_router.router.extract_pdf",
        lambda data: PdfExtractionResult(
            text="x" * pdf_extractor._MAX_TEXT_CHARS,
            status=pdf_extractor.STATUS_PARTIAL,
            diagnostics=[f"text truncated to {pdf_extractor._MAX_TEXT_CHARS} characters"],
        ),
    )

    result = extract_urls(
        ["https://example.com/huge-paper.pdf"], paths=tmp_foundry, providers={}
    )

    assert result["degraded"] is False
    assert len(result["source_cards"]) == 1
    status, _front_matter = _card_extraction_status(result["run_id"], tmp_foundry)
    assert status == "partial"


# ---------------------------------------------------------------------------
# Scenario 4: missing ``pdf`` extra (pypdf not installed) -> graceful degrade
# to locator_only, no unhandled exception, through the full pipeline
# ---------------------------------------------------------------------------


def test_missing_pdf_extra_degrades_gracefully_end_to_end(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pdf_extractor, "_pypdf_available", lambda: False)
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen(PDF_WITH_TEXT))

    result = extract_urls(
        ["https://example.com/needs-pdf-extra.pdf"], paths=tmp_foundry, providers={}
    )

    assert len(result["source_cards"]) == 1
    status, _front_matter = _card_extraction_status(result["run_id"], tmp_foundry)
    assert status == "locator_only"
