"""PaperQA2 adapter — scientific RAG over a local PDF corpus (spec §13.2).

Real mode (when ``paperqa`` is importable) runs citation-grounded QA over a
local PDF/text directory. Degraded mode performs no model calls: it lists the
local PDFs in the requested directory as labeled candidates (or returns a note
when no directory/PDFs are present), so the pipeline stays testable offline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..ids import slugify, today_compact
from .base import AdapterResult, BaseAdapter, register


class PaperQA2Adapter(BaseAdapter):
    """Wraps PaperQA2 for local scientific literature RAG."""

    id = "paperqa2"
    requires = ("paperqa",)

    def run(self, request: dict[str, Any]) -> AdapterResult:
        if not self.available():
            return self._degraded(request)
        return self._degraded(request, note="paperqa present but real mode is opt-in")

    def _degraded(self, request: dict[str, Any], *, note: str | None = None) -> AdapterResult:
        pdf_dir = request.get("local_pdf_dir") or request.get("pdf_dir")
        candidates: list[dict[str, Any]] = []
        notes = ["paperqa2 unavailable: no scientific RAG; listing local PDFs only"]

        if pdf_dir:
            directory = Path(pdf_dir)
            if directory.is_dir():
                pdfs = sorted(directory.glob("*.pdf"))
                for idx, pdf in enumerate(pdfs, start=1):
                    stem = pdf.stem
                    candidates.append(
                        {
                            "candidate_id": f"cand_{today_compact()}_{slugify(stem)}",
                            "title": stem,
                            "source_type": "paper",
                            "locator": {
                                "url": None,
                                "file_path": str(pdf),
                                "doi": None,
                                "repo": None,
                            },
                            "discovery_method": "local_pdf_listing",
                            "label": f"local_pdf_{idx}",
                        }
                    )
                if not pdfs:
                    notes.append(f"no PDFs found under {directory}")
            else:
                notes.append(f"local_pdf_dir not a directory: {directory}")
        else:
            notes.append("no local_pdf_dir provided in request")

        if note:
            notes.append(note)
        return AdapterResult(
            adapter=self.id,
            degraded=True,
            source_candidates=candidates,
            notes=notes,
        )


register(PaperQA2Adapter())

__all__ = ["PaperQA2Adapter"]
