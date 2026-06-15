"""NotebookLM adapter — grounded research sourcing (spec §13.x).

NotebookLM is a Google service accessed through the ``notebooklm`` CLI binary
(``pip install notebooklm-py``). This adapter drives grounded research / Q&A for
a run's brief and emits normalized ``source_candidates`` that feed the claim ledger.

NotebookLM's synthesized answers are NEVER the Research Foundry report — they are
source-discovery artifacts that still flow through the verifier. The synthesized
answer text is stored in ``AdapterResult.artifacts['notebook_synthesis']`` as
telemetry only (non-authoritative).

Availability is detected with ``shutil.which("notebooklm")`` rather than a Python
module import, because the dependency is a CLI tool (like OpenCode, not GPT
Researcher). In degraded mode, the adapter produces deterministic, clearly-labeled
stub candidates from the brief's questions — no subprocess is spawned and no network
calls are made.

All NLM network operations are fail-soft: on any subprocess or parse error the
adapter degrades and returns ``AdapterResult(degraded=True, ...)``. The pipeline
is never allowed to raise from this module.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from ..ids import slugify, today_compact
from .base import AdapterResult, BaseAdapter, register

# ---------------------------------------------------------------------------
# Question extraction (shared with GPTResearcherAdapter)
# ---------------------------------------------------------------------------


def _questions_from_request(request: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract a flat list of ``{id, question}`` dicts from a request dict.

    Accepts either a full ``brief`` (with ``questions.primary`` / ``.secondary``)
    or a bare ``research_questions`` / ``questions`` list of strings or dicts.
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


def _project_from_request(request: dict[str, Any]) -> str | None:
    """Extract project slug from request (brief.project or top-level project)."""

    brief = request.get("brief")
    if isinstance(brief, dict):
        return brief.get("project") or None
    return request.get("project") or None


def _run_id_from_request(request: dict[str, Any]) -> str | None:
    """Extract run_id from request."""

    return request.get("run_id") or None


# ---------------------------------------------------------------------------
# CLI helpers (subprocess, fail-soft)
# ---------------------------------------------------------------------------


def _run_notebooklm(
    args: list[str],
    *,
    timeout: float = 30.0,
) -> dict[str, Any] | None:
    """Run ``notebooklm <args>`` and return parsed JSON output, or None on any error.

    Always appends ``--json`` to request machine-readable output. Never raises.
    """

    cmd = ["notebooklm", *args, "--json"]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode != 0:
            return None
        raw = (result.stdout or "").strip()
        if not raw:
            return None
        return json.loads(raw)
    except Exception:  # noqa: BLE001 — never propagate into pipeline
        return None


def _ask_notebook(notebook_id: str, question: str) -> dict[str, Any] | None:
    """Send a chat query to NotebookLM and return the JSON response, or None."""

    return _run_notebooklm(
        ["ask", question, "--notebook", notebook_id],
        timeout=60.0,
    )


def _add_research(notebook_id: str, query: str, *, mode: str = "deep") -> dict[str, Any] | None:
    """Trigger web research sourcing within a notebook; returns task info or None."""

    return _run_notebooklm(
        [
            "source", "add-research", query,
            "--mode", mode,
            "--notebook", notebook_id,
        ],
        timeout=30.0,
    )


def _get_source_fulltext(notebook_id: str, source_id: str) -> dict[str, Any] | None:
    """Retrieve indexed fulltext for a source; returns dict or None."""

    return _run_notebooklm(
        ["source", "fulltext", source_id, "--notebook", notebook_id],
        timeout=30.0,
    )


# ---------------------------------------------------------------------------
# Candidate builder
# ---------------------------------------------------------------------------


def _reference_to_candidate(
    ref: dict[str, Any],
    *,
    idx: int,
    question_id: str,
    question_text: str,
    notebook_id: str,
) -> dict[str, Any]:
    """Map a single NLM reference dict to a normalized source_candidate record.

    Mirrors the EXACT field keys used by ``GPTResearcherAdapter``.
    """

    source_id = str(ref.get("source_id") or "")
    cited_text = str(ref.get("cited_text") or "")
    citation_num = ref.get("citation_number", idx)

    # Build a stable candidate_id from date + source_id snippet + question slug
    q_slug = slugify(question_text)
    src_part = slugify(source_id)[:12] if source_id else f"ref{citation_num}"
    candidate_id = f"cand_{today_compact()}_{src_part}_{q_slug}"

    # Source title: prefer a cited text excerpt (truncated) as a descriptor
    title = (cited_text[:120] + "…") if len(cited_text) > 120 else cited_text
    if not title:
        title = f"NLM source {source_id or citation_num} for: {question_text}"

    # NLM source URLs are not directly accessible; the locator encodes
    # the notebook + source_id so the writeback layer can retrieve fulltext.
    locator: dict[str, Any] = {
        "url": None,
        "file_path": None,
        "doi": None,
        "repo": None,
        "notebook_id": notebook_id,
        "nlm_source_id": source_id or None,
    }

    return {
        "candidate_id": candidate_id,
        "title": title,
        "source_type": "notebooklm",
        "locator": locator,
        "discovered_for_question": question_id,
        "discovery_method": "notebooklm_synthesis",
        "label": f"nlm_ref_{citation_num}",
        "notes": cited_text if cited_text else "NLM grounded reference (no cited text returned).",
    }


# ---------------------------------------------------------------------------
# Main adapter
# ---------------------------------------------------------------------------


class NotebookLMAdapter(BaseAdapter):
    """Wraps the NotebookLM CLI for grounded research source discovery.

    Uses ``shutil.which("notebooklm")`` for availability detection (CLI binary,
    not a Python module). When available, the adapter resolves or creates the
    run's notebook via ``notebook_correlation.resolve_notebook``, then — for each
    question in the brief — asks NotebookLM (via ``notebooklm ask --json``) and
    maps the returned references into normalized ``source_candidates``.

    In degraded mode (no CLI, no auth, or any subprocess failure) the adapter
    returns a deterministic ``AdapterResult(degraded=True)`` with stub candidates
    derived from the brief questions. No subprocess is ever called in degraded mode.
    """

    id = "notebooklm"
    requires: tuple[str, ...] = ()  # CLI binary, not a Python import

    def available(self) -> bool:
        """True when the ``notebooklm`` CLI binary is on PATH."""

        return shutil.which("notebooklm") is not None

    def run(self, request: dict[str, Any]) -> AdapterResult:
        """Execute grounded Q&A for each brief question; return normalized candidates.

        Parameters
        ----------
        request:
            Dict with at minimum ``{"brief": {...}}`` (with
            ``questions.primary``/``secondary``) and optionally ``run_id`` and
            ``project``.

        Returns
        -------
        AdapterResult
            Always returned (never raises). ``degraded=True`` when the CLI is
            absent or when any subprocess call fails. ``artifacts['notebook_synthesis']``
            holds a JSON-encoded list of raw NLM answers (telemetry only).
        """

        if not self.available():
            return self._degraded(request)

        questions = _questions_from_request(request)
        if not questions:
            return AdapterResult(
                adapter=self.id,
                degraded=False,
                notes=["no research questions in request; returned empty candidate set"],
            )

        run_id = _run_id_from_request(request)
        project = _project_from_request(request)

        # Resolve (or create) the notebook for this run so sourcing and later
        # upload-back share the same notebook.
        notebook_id = self._resolve_notebook(run_id=run_id, project=project, request=request)
        if notebook_id is None:
            # Could not resolve a notebook — fall through to degraded.
            return self._degraded(
                request,
                note="notebooklm binary present but notebook resolution failed; degrading",
            )

        candidates: list[dict[str, Any]] = []
        synthesis_parts: list[dict[str, Any]] = []
        degrade_reasons: list[str] = []

        for idx, q in enumerate(questions, start=1):
            question_text = str(q.get("question") or "").strip()
            question_id = str(q.get("id") or f"q{idx}")
            if not question_text:
                continue

            # Ask NLM; degrade per-question on failure (don't abort all questions).
            ask_result = _ask_notebook(notebook_id, question_text)
            if ask_result is None:
                degrade_reasons.append(
                    f"notebooklm ask failed for question {question_id!r}; skipped"
                )
                # Still emit a stub candidate so downstream pipeline has coverage.
                slug = slugify(question_text)
                candidates.append(
                    {
                        "candidate_id": f"cand_{today_compact()}_{slug}",
                        "title": f"NLM discovery target (failed): {question_text}",
                        "source_type": "notebooklm",
                        "locator": {
                            "url": None,
                            "file_path": None,
                            "doi": None,
                            "repo": None,
                            "notebook_id": notebook_id,
                            "nlm_source_id": None,
                        },
                        "discovered_for_question": question_id,
                        "discovery_method": "notebooklm_synthesis",
                        "label": f"nlm_ask_failed_{idx}",
                        "notes": "notebooklm ask returned no result for this question.",
                    }
                )
                continue

            answer_text = str(ask_result.get("answer") or "")
            references: list[dict[str, Any]] = ask_result.get("references") or []

            # Record synthesis answer for telemetry (non-authoritative).
            synthesis_parts.append(
                {
                    "question_id": question_id,
                    "question": question_text,
                    "answer": answer_text,
                    "reference_count": len(references),
                }
            )

            # Map each NLM reference to a normalized candidate.
            if references:
                for ref_idx, ref in enumerate(references, start=1):
                    candidates.append(
                        _reference_to_candidate(
                            ref,
                            idx=ref_idx,
                            question_id=question_id,
                            question_text=question_text,
                            notebook_id=notebook_id,
                        )
                    )
            else:
                # No citations returned — emit one stub candidate from the answer.
                slug = slugify(question_text)
                candidates.append(
                    {
                        "candidate_id": f"cand_{today_compact()}_{slug}",
                        "title": f"NLM synthesis answer for: {question_text}",
                        "source_type": "notebooklm",
                        "locator": {
                            "url": None,
                            "file_path": None,
                            "doi": None,
                            "repo": None,
                            "notebook_id": notebook_id,
                            "nlm_source_id": None,
                        },
                        "discovered_for_question": question_id,
                        "discovery_method": "notebooklm_synthesis",
                        "label": f"nlm_synthesis_{idx}",
                        "notes": (
                            answer_text[:500] if answer_text
                            else "NLM returned no cited references for this question."
                        ),
                    }
                )

        # Build artifacts dict — synthesized answers are telemetry ONLY.
        artifacts: dict[str, str] = {}
        if synthesis_parts:
            try:
                artifacts["notebook_synthesis"] = json.dumps(
                    synthesis_parts, ensure_ascii=False, sort_keys=True
                )
            except Exception:  # noqa: BLE001
                pass

        notes: list[str] = []
        if degrade_reasons:
            notes.extend(degrade_reasons)
        if notebook_id:
            notes.append(f"notebook_id: {notebook_id}")

        degraded = bool(degrade_reasons) and not any(
            c.get("discovery_method") == "notebooklm_synthesis"
            and "failed" not in c.get("label", "")
            for c in candidates
        )

        return AdapterResult(
            adapter=self.id,
            degraded=degraded,
            source_candidates=candidates,
            artifacts=artifacts,
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_notebook(
        self,
        *,
        run_id: str | None,
        project: str | None,
        request: dict[str, Any],
    ) -> str | None:
        """Resolve (or create) the notebook for this run.

        Attempts to call ``services.notebook_correlation.resolve_notebook`` if the
        module is available; falls back to ``request.get('notebook_id')``; returns
        None on any error (never raises).

        The ``create=True`` flag tells correlation to create a new notebook when
        none is found, sharing the same notebook across sourcing and upload-back.
        """

        # Allow explicit override from the request (e.g. from CLI --notebook-id).
        explicit_id: str | None = request.get("notebook_id") or None

        try:
            from ..integrations import get_notebooklm_client  # type: ignore[attr-defined]
            from ..services.notebook_correlation import resolve_notebook

            client = get_notebooklm_client()
            result = resolve_notebook(
                run_id or "",
                project=project,
                mode=request.get("notebook_mode") or None,
                create=True,
                client=client,
                paths=request.get("paths") or None,
            )
            if isinstance(result, dict):
                return str(result.get("notebook_id") or "") or explicit_id
        except Exception:  # noqa: BLE001 — module may not be implemented yet
            pass

        return explicit_id

    def _degraded(
        self,
        request: dict[str, Any],
        *,
        note: str | None = None,
    ) -> AdapterResult:
        """Return a deterministic degraded result without any subprocess calls.

        Produces one stub candidate per question so the downstream pipeline can
        complete and tests are runnable with no ``notebooklm`` binary present.
        """

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
                    "title": f"NLM discovery target (offline): {text}",
                    "source_type": "notebooklm",
                    "locator": {
                        "url": None,
                        "file_path": None,
                        "doi": None,
                        "repo": None,
                        "notebook_id": None,
                        "nlm_source_id": None,
                    },
                    "discovered_for_question": qid,
                    "discovery_method": "notebooklm_synthesis",
                    "label": f"nlm_offline_stub_{idx}",
                    "notes": "Generated offline (notebooklm CLI not available).",
                }
            )

        notes = [
            "notebooklm unavailable: `notebooklm` not on PATH; "
            "derived source_candidates from brief questions without NLM access"
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


register(NotebookLMAdapter())

__all__ = ["NotebookLMAdapter"]
