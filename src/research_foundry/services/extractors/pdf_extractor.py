"""Governed PDF text extraction (optional ``pdf`` extra).

Wraps ``pypdf`` behind a lazy import so this module never fails to import
when the optional ``pdf`` extra (``pip install 'research-foundry[pdf]'``) is
not installed. Every failure mode -- missing dependency, corrupted/malformed
PDF, no extractable text layer -- degrades to ``locator_only`` rather than
raising; callers should never need to wrap :func:`extract_pdf` in a
try/except.

This module is intentionally standalone: it does not import from
``router.py`` or ``source_cards.py``. Those call sites wire it in explicitly.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field

# Cap on extracted text length (characters) to bound memory/output size for
# very large PDFs. Text beyond this is truncated and the result is marked
# "partial" rather than "full_text".
_MAX_TEXT_CHARS = 100_000

# Tri-state status vocabulary shared with the rest of the ingestion pipeline.
# Phase 3's TASK-3.3 formalizes these three string values as an enum in
# ``services/source_cards.py`` -- keep them in sync.
STATUS_FULL_TEXT = "full_text"
STATUS_PARTIAL = "partial"
STATUS_LOCATOR_ONLY = "locator_only"


@dataclass(frozen=True)
class PdfExtractionResult:
    """Outcome of attempting to extract text from a PDF's raw bytes."""

    text: str | None
    status: str  # one of STATUS_FULL_TEXT / STATUS_PARTIAL / STATUS_LOCATOR_ONLY
    diagnostics: list[str] = field(default_factory=list)


def _pypdf_available() -> bool:
    """Return True if the optional ``pypdf`` dependency can be imported.

    Isolated into its own function (rather than inlining the try/except in
    :func:`extract_pdf`) so tests can monkeypatch this seam to simulate the
    "pdf extra not installed" path without needing to actually uninstall
    pypdf from the environment.
    """

    try:
        import pypdf  # noqa: F401
    except ImportError:
        return False
    return True


def extract_pdf(data: bytes) -> PdfExtractionResult:
    """Extract text from raw PDF bytes.

    Bytes-based so both a local file path and a downloaded URL body can call
    this without duplicating file I/O.

    Never raises. Degrades to ``locator_only`` with a diagnostic message
    when: ``pypdf`` is not installed, the PDF is corrupted/malformed, or the
    PDF has no extractable text layer (e.g. scanned/image-only). Returns
    ``full_text`` when extractable text is present, or ``partial`` when that
    text exceeds the size guard and was truncated.
    """

    if not _pypdf_available():
        return PdfExtractionResult(
            text=None,
            status=STATUS_LOCATOR_ONLY,
            diagnostics=["pypdf not installed"],
        )

    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data))
        pages_text: list[str] = []
        for page in reader.pages:
            try:
                pages_text.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001  (per-page failures degrade, never raise)
                pages_text.append("")
    except Exception as exc:  # noqa: BLE001  (corrupted/malformed PDF -> locator_only, never raise)
        return PdfExtractionResult(
            text=None,
            status=STATUS_LOCATOR_ONLY,
            diagnostics=[f"corrupted PDF: {exc}"],
        )

    full_text = "\n".join(pages_text).strip()

    if not full_text:
        return PdfExtractionResult(
            text=None,
            status=STATUS_LOCATOR_ONLY,
            diagnostics=["no text layer"],
        )

    if len(full_text) > _MAX_TEXT_CHARS:
        return PdfExtractionResult(
            text=full_text[:_MAX_TEXT_CHARS],
            status=STATUS_PARTIAL,
            diagnostics=[f"text truncated to {_MAX_TEXT_CHARS} characters"],
        )

    return PdfExtractionResult(text=full_text, status=STATUS_FULL_TEXT, diagnostics=[])
