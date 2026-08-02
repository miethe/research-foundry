"""Deterministic ``trust.source_rank`` derivation (source-metadata-propagation-v1, M1 / OQ-4).

OQ-4 resolution (recorded in the execution ledger,
``.claude/worknotes/source-metadata-propagation/implementation-notes.md``):
``source_rank`` derivation is a PURE FUNCTION of ``source.source_type`` — no
capture-time model call, network call, or wall-clock read is used or needed.
This keeps the derivation squarely on the write path with zero read-path
cost. (The plan's deal-killer is read-path model/network/clock use; a
write-path model call would have been *allowed*, but none turned out to be
necessary.)

``rights_summary.access_basis`` — the other candidate input OQ-4 named — is
deliberately NOT consulted here: at real capture time it is always the
``"unknown"`` sentinel (``services/rights_triage.py``'s
``_classify_capture_rights`` has no signal to determine a real access basis
yet — see that module's docstring). Folding an always-``"unknown"`` field
into this mapping today would add a never-exercised branch. Widen the
mapping in this module — not its call site — if/when a real capture-time
rights classifier makes ``access_basis`` a live signal.

The mapping below is an intentionally closed, partial classification of
``source.source_type`` into the schema's evidentiary tiers
(``primary``/``secondary``/``tertiary``/``unknown``,
``schemas/source_card.schema.yaml``). Where a ``source_type`` does not
reliably signal a rank on its own (``personal_note``, ``internal_doc``,
``other``), the result stays ``"unknown"`` — per the plan's rubric, an
undeterminable rank must never be silently inferred.
"""

from __future__ import annotations

_UNKNOWN_RANK = "unknown"

# Deterministic source_type -> trust.source_rank mapping. Keys are exact
# `source.source_type` enum values from schemas/source_card.schema.yaml
# (official_doc|paper|standard|repo|news|blog|book|personal_note|
# internal_doc|other). Any source_type absent from this table derives to
# "unknown" -- never guessed.
_SOURCE_RANK_BY_TYPE: dict[str, str] = {
    # Primary: the canonical/original artifact for its domain -- an official
    # specification, an organization's own official document, an academic
    # paper (original research/reporting), or the source-code repository
    # itself (the primary technical artifact for software topics).
    "official_doc": "primary",
    "standard": "primary",
    "paper": "primary",
    "repo": "primary",
    # Secondary: reporting or commentary derived from primary sources.
    "news": "secondary",
    "blog": "secondary",
    # Tertiary: compiled/derivative synthesis of primary+secondary material.
    "book": "tertiary",
    # personal_note / internal_doc / other are deliberately absent: source_
    # type alone gives no reliable signal for these (varies entirely by
    # author/organizational context available nowhere at ingest time) --
    # they fall through to _UNKNOWN_RANK below rather than being guessed.
}


def derive_source_rank(source_type: str | None) -> str:
    """Deterministically derive ``trust.source_rank`` from ``source_type``.

    Pure function: identical input always yields identical output, with no
    I/O and no clock read. Never raises -- an unrecognized, non-string, or
    ``None`` ``source_type`` derives to ``"unknown"`` rather than raising,
    matching this module's own rubric ("if it cannot be derived
    deterministically it stays unknown").
    """

    if not isinstance(source_type, str):
        return _UNKNOWN_RANK
    return _SOURCE_RANK_BY_TYPE.get(source_type, _UNKNOWN_RANK)


__all__ = ["derive_source_rank"]
