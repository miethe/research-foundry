"""Substitutability search on a blocking rights-triage status (rights-entity-model-v1, P4-4).

A blocking ``clearance_status`` (``CONTRACT_RESTRICTED``, ``PERMISSION_REQUIRED``,
``PROHIBITED``, or the fail-closed ``UNKNOWN`` sentinel -- see
``schemas/rights_record.schema.yaml``'s ``rights_extension.clearance_status``
enum, mirrored on ``rights_summary.clearance_status`` in
``schemas/source_card.schema.yaml``/``schemas/source_assertion.schema.yaml``)
means the entity cannot be used as-is. :func:`assess_substitutability` is the
single entry point that decides whether a substitute-source search should run
at all, runs it against a caller-supplied corpus of existing ``source_card``
instances when it should, and always returns a well-formed
``substitutability`` block -- never a bare exception, never a silent skip.

Result shape (per the plan's P4-4 row -- exactly these four fields, no more):

- ``searched_at``: ISO-8601 timestamp of the search *attempt*, or ``None``
  when no attempt was made at all (non-blocking status -- scenario 1). A
  blocking status that triggers a search always sets this, even if the
  search itself then fails (scenario 4) -- it distinguishes "never attempted"
  from "attempted, then degraded."
- ``status``: one of :data:`STATUS_SUBSTITUTE_FOUND`,
  :data:`STATUS_NO_SUBSTITUTE_FOUND`, :data:`STATUS_NOT_SEARCHED`. Always
  present and non-null -- ``no_substitute_found`` is a positive structured
  result, not an absence (scenario 3).
- ``candidate_source_ids``: ranked list of candidate ``source_card_id`` values
  (best match first), empty unless ``status == "substitute_found"``.
- ``coverage_notes``: a short human-readable explanation of what happened
  (why no search ran, what the search found, or what failed and why) -- this
  is the structural note that stands in for a dedicated failure record
  (mirrors the ``terms_snapshot_failure`` convention established for P4-3)
  since the plan's field list here has no separate failure slot.

Corpus search
--------------
The "existing corpus" search is a minimal, real keyword-overlap search over
caller-supplied ``source_card`` Markdown files (front matter loaded via
``research_foundry.frontmatter.load_md``): each candidate's ``source.title``
and ``extracted_points[].summary`` text is tokenized and scored against the
caller's ``query_terms`` by token-intersection size. This is intentionally
simple (no external index, no embeddings) -- callers with a real topic/domain
signal (e.g. the capture pipeline's raw idea title, once a real capture-time
classifier exists per ``rights_triage.py``'s documented seam) supply it via
``query_terms``; this module does not invent one.

Never raises
------------
:func:`assess_substitutability` never propagates an exception. A failure
inside the corpus search (a bad path, an unreadable file, a malformed corpus
entry) degrades the result to ``not_searched`` plus a ``coverage_notes``
explanation -- never a silent skip and never a half-populated result.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from ..frontmatter import load_md

__all__ = [
    "STATUS_SUBSTITUTE_FOUND",
    "STATUS_NO_SUBSTITUTE_FOUND",
    "STATUS_NOT_SEARCHED",
    "BLOCKING_CLEARANCE_STATUSES",
    "SubstituteCandidate",
    "SubstitutabilityAssessment",
    "is_blocking_clearance_status",
    "find_substitute_candidates",
    "assess_substitutability",
    "not_searched_assessment",
]

STATUS_SUBSTITUTE_FOUND = "substitute_found"
STATUS_NO_SUBSTITUTE_FOUND = "no_substitute_found"
STATUS_NOT_SEARCHED = "not_searched"

# The blocking-status set named explicitly in the P4-4 plan row: three named
# clearance determinations plus the fail-closed "UNKNOWN" sentinel (the
# default emitted by every capture today per rights_triage.py -- a bare
# capture with no real classification signal is itself use-blocking until a
# real determination replaces it).
BLOCKING_CLEARANCE_STATUSES: frozenset[str] = frozenset(
    {"CONTRACT_RESTRICTED", "PERMISSION_REQUIRED", "PROHIBITED", "UNKNOWN"}
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def is_blocking_clearance_status(clearance_status: str | None) -> bool:
    """True when ``clearance_status`` is use-blocking per :data:`BLOCKING_CLEARANCE_STATUSES`."""

    return (clearance_status or "").strip().upper() in BLOCKING_CLEARANCE_STATUSES


@dataclass(frozen=True)
class SubstituteCandidate:
    """One ranked corpus match."""

    source_id: str
    score: int
    matched_terms: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubstitutabilityAssessment:
    """The ``substitutability`` result block (P4-4)."""

    searched_at: str | None
    status: str
    candidate_source_ids: list[str]
    coverage_notes: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN_RE.findall(text.lower()))


def _load_candidate_tokens(path: Path) -> tuple[str | None, set[str]]:
    """Load one corpus ``source_card`` file -> ``(source_card_id, token_set)``."""

    metadata, _body = load_md(path)
    source_id = metadata.get("source_card_id")
    tokens: set[str] = set()
    source = metadata.get("source") or {}
    title = source.get("title")
    if isinstance(title, str):
        tokens |= _tokenize(title)
    for point in metadata.get("extracted_points") or []:
        if not isinstance(point, dict):
            continue
        summary = point.get("summary")
        if isinstance(summary, str):
            tokens |= _tokenize(summary)
    return source_id, tokens


def find_substitute_candidates(
    *,
    query_terms: Sequence[str],
    corpus_paths: Iterable[Path | str],
    exclude_source_id: str | None = None,
    limit: int = 10,
) -> list[SubstituteCandidate]:
    """Rank ``corpus_paths`` (``source_card`` files) by keyword overlap with ``query_terms``.

    Returns every candidate with a non-zero overlap score, best match first
    (ties broken by ``source_id`` for deterministic ordering), capped at
    ``limit``. Never returns ``exclude_source_id`` even if it appears in the
    corpus (a source cannot substitute for itself). Raises on a structurally
    broken corpus path or file -- callers (see :func:`assess_substitutability`)
    are responsible for catching and degrading; this function's job is only
    to search, not to swallow errors.
    """

    query_tokens = {t.lower() for t in query_terms if t}
    candidates: list[SubstituteCandidate] = []
    if not query_tokens:
        return candidates

    for raw_path in corpus_paths:
        path = Path(raw_path)
        source_id, tokens = _load_candidate_tokens(path)
        if not source_id or source_id == exclude_source_id:
            continue
        matched = sorted(query_tokens & tokens)
        if not matched:
            continue
        candidates.append(SubstituteCandidate(source_id=source_id, score=len(matched), matched_terms=tuple(matched)))

    candidates.sort(key=lambda c: (-c.score, c.source_id))
    return candidates[:limit]


def not_searched_assessment(coverage_notes: str, *, searched_at: str | None = None) -> dict[str, Any]:
    """Build a well-formed ``not_searched`` result (shared shape for both the
    non-blocking short-circuit and the search-error degrade path)."""

    return SubstitutabilityAssessment(
        searched_at=searched_at,
        status=STATUS_NOT_SEARCHED,
        candidate_source_ids=[],
        coverage_notes=coverage_notes,
    ).as_dict()


def _resolve_now(now: datetime | str | None) -> str:
    if now is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(now, datetime):
        return now.isoformat()
    return now


def assess_substitutability(
    clearance_status: str | None,
    *,
    query_terms: Sequence[str] | None = None,
    corpus_paths: Iterable[Path | str] | None = None,
    exclude_source_id: str | None = None,
    limit: int = 10,
    now: datetime | str | None = None,
) -> dict[str, Any]:
    """The full ``substitutability`` assessment for one entity, never raising.

    Args:
        clearance_status: The entity's (mirror or authoritative)
            ``clearance_status``. Only a value in
            :data:`BLOCKING_CLEARANCE_STATUSES` triggers a search
            (scenario 1 otherwise).
        query_terms: Topic/domain terms describing the entity, used to match
            against the corpus. An empty/omitted sequence yields no
            candidates (nothing to search on) but is still a *performed*
            search, not scenario 1 -- see ``coverage_notes`` for the
            distinction.
        corpus_paths: ``source_card`` Markdown files making up the searchable
            corpus (e.g. every other source in the same run/workspace).
        exclude_source_id: The entity's own ``source_card_id``, excluded from
            candidate results.
        limit: Maximum ranked candidates to return.
        now: Explicit search timestamp for deterministic tests; defaults to
            the current UTC time.

    Returns:
        A JSON-safe dict with exactly the four P4-4 fields: ``searched_at``,
        ``status``, ``candidate_source_ids``, ``coverage_notes``.
    """

    if not is_blocking_clearance_status(clearance_status):
        return not_searched_assessment(
            f"clearance_status={clearance_status!r} is non-blocking; substitutability search not triggered.",
            searched_at=None,
        )

    attempted_at = _resolve_now(now)
    corpus_list = list(corpus_paths or [])

    try:
        candidates = find_substitute_candidates(
            query_terms=list(query_terms or []),
            corpus_paths=corpus_list,
            exclude_source_id=exclude_source_id,
            limit=limit,
        )
    except Exception as exc:  # noqa: BLE001 -- a search failure must degrade, never propagate or vanish
        return not_searched_assessment(
            f"substitutability search failed ({type(exc).__name__}: {exc}); degraded to not_searched.",
            searched_at=attempted_at,
        )

    if candidates:
        return SubstitutabilityAssessment(
            searched_at=attempted_at,
            status=STATUS_SUBSTITUTE_FOUND,
            candidate_source_ids=[c.source_id for c in candidates],
            coverage_notes=(
                f"clearance_status={clearance_status!r} is blocking; found {len(candidates)} ranked "
                f"candidate(s) across {len(corpus_list)} corpus source(s)."
            ),
        ).as_dict()

    return SubstitutabilityAssessment(
        searched_at=attempted_at,
        status=STATUS_NO_SUBSTITUTE_FOUND,
        candidate_source_ids=[],
        coverage_notes=(
            f"clearance_status={clearance_status!r} is blocking; searched {len(corpus_list)} corpus "
            "source(s), no substitute found."
        ),
    ).as_dict()
