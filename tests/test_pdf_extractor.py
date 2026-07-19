"""Unit tests for the governed PDF text extractor.

Exercises ``extract_pdf`` directly (not through the CLI/pipeline), covering
the tri-state ``full_text`` / ``partial`` / ``locator_only`` vocabulary and
the "never raise" contract across missing-dependency, corrupted-input, and
no-text-layer scenarios.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from research_foundry.services.extractors import pdf_extractor
from research_foundry.services.extractors.pdf_extractor import (
    STATUS_FULL_TEXT,
    STATUS_LOCATOR_ONLY,
    extract_pdf,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "assertion_ledger" / "p2_formats"
MALFORMED_PDF_PATH = FIXTURE_DIR / "fixture.pdf"


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


def test_extract_pdf_with_text_layer_returns_full_text() -> None:
    result = extract_pdf(PDF_WITH_TEXT)

    assert result.status == STATUS_FULL_TEXT
    assert result.text
    assert "Hello Research Foundry" in result.text
    assert result.diagnostics == []


def test_extract_pdf_without_text_layer_returns_locator_only() -> None:
    result = extract_pdf(PDF_WITHOUT_TEXT)

    assert result.status == STATUS_LOCATOR_ONLY
    assert result.text is None
    assert result.diagnostics == ["no text layer"]


def test_extract_pdf_corrupted_input_returns_locator_only_without_raising() -> None:
    data = MALFORMED_PDF_PATH.read_bytes()

    result = extract_pdf(data)

    assert result.status == STATUS_LOCATOR_ONLY
    assert result.text is None
    assert result.diagnostics
    assert "corrupted PDF" in result.diagnostics[0]


def test_extract_pdf_missing_dependency_returns_locator_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pdf_extractor, "_pypdf_available", lambda: False)

    result = extract_pdf(PDF_WITH_TEXT)

    assert result.status == STATUS_LOCATOR_ONLY
    assert result.text is None
    assert result.diagnostics == ["pypdf not installed"]
