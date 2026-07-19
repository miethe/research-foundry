"""Governed content extractors.

Standalone extraction helpers that operate on raw bytes and never raise --
callers (source card ingestion, search-router URL extraction) wire these in
explicitly rather than this package importing them.
"""

from __future__ import annotations

from .pdf_extractor import PdfExtractionResult, extract_pdf

__all__ = ["PdfExtractionResult", "extract_pdf"]
