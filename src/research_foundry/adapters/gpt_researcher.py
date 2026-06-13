"""GPT Researcher adapter — research discovery (spec §13.1).

Real mode (when ``gpt_researcher`` is importable and a key is present) runs a
broad web scan and returns cited findings. GPT Researcher's output is *never*
the final Research Foundry report — it is source discovery + draft input that
still flows through the claim ledger.

Degraded (default) mode performs no network calls: it turns the research
brief's questions into deterministically-labeled ``source_candidates`` so the
pipeline can complete and is testable with no API keys.
"""

from __future__ import annotations

from typing import Any

from ..ids import slugify, today_compact
from .base import AdapterResult, BaseAdapter, register


def _questions_from_request(request: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract a flat list of ``{id, question}`` from a request dict.

    Accepts either a full ``brief`` (with ``questions.primary``/``.secondary``)
    or a bare ``research_questions``/``questions`` list of strings or dicts.
    """

    brief = request.get("brief")
    if isinstance(brief, dict):
        q = brief.get("questions")
        if isinstance(q, dict):
            ordered: list[dict[str, Any]] = []
            for bucket in ("primary", "secondary"):
                for item in q.get(bucket) or []:
                    if isinstance(item, dict):
                        ordered.append(item)
                    elif item:
                        ordered.append({"question": str(item)})
            if ordered:
                return ordered

    raw = (
        request.get("research_questions")
        or request.get("questions")
        or []
    )
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(item)
        elif item:
            out.append({"question": str(item)})
    return out


class GPTResearcherAdapter(BaseAdapter):
    """Wraps GPT Researcher for broad source discovery."""

    id = "gpt_researcher"
    requires = ("gpt_researcher",)

    def run(self, request: dict[str, Any]) -> AdapterResult:
        if not self.available():
            return self._degraded(request)
        return self._degraded(request, note="gpt_researcher present but real mode is opt-in")

    def _degraded(self, request: dict[str, Any], *, note: str | None = None) -> AdapterResult:
        questions = _questions_from_request(request)
        candidates: list[dict[str, Any]] = []
        for idx, q in enumerate(questions, start=1):
            text = str(q.get("question") or "").strip()
            qid = str(q.get("id") or f"q{idx}")
            if not text:
                continue
            slug = slugify(text)
            candidates.append(
                {
                    "candidate_id": f"cand_{today_compact()}_{slug}",
                    "title": f"Discovery target for: {text}",
                    "source_type": "other",
                    "locator": {"url": None, "file_path": None, "doi": None, "repo": None},
                    "discovered_for_question": qid,
                    "discovery_method": "degraded_stub",
                    "label": f"unverified_candidate_{idx}",
                    "notes": "Generated offline from brief question (no web scan).",
                }
            )
        notes = [
            "gpt_researcher unavailable: derived source_candidates from brief "
            "questions without network access"
        ]
        if not candidates:
            notes.append("no research questions in request; returned empty candidate set")
        if note:
            notes.append(note)
        return AdapterResult(
            adapter=self.id,
            degraded=True,
            source_candidates=candidates,
            notes=notes,
        )


register(GPTResearcherAdapter())

__all__ = ["GPTResearcherAdapter"]
