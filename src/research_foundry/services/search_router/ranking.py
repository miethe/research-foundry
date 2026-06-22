"""Authority scoring and result ranking for the Research Foundry Search Router.

:func:`authority_score` implements the heuristic from spec §15.3:
base weight by source type, freshness bonus, and risk-flag penalties, all
clamped to [0, 1].

:func:`rank_hits` sorts a list of :class:`SearchHit` objects by a composite
key: (score desc, source-type authority desc, rank asc).
"""

from __future__ import annotations

from research_foundry.services.search_router.providers.base import SearchHit

# ---------------------------------------------------------------------------
# Spec §15.3 weights
# ---------------------------------------------------------------------------

_SOURCE_TYPE_WEIGHT: dict[str, float] = {
    "official_docs": 0.95,
    "academic_paper": 0.90,
    "standards_body": 0.90,
    "repo": 0.75,
    "reputable_news": 0.70,
    "vendor_blog": 0.65,
    "community_forum": 0.45,
    "unknown_blog": 0.30,
    # Aliases used elsewhere in the codebase / schema
    "paper": 0.90,
    "standard": 0.90,
    "news": 0.70,
    "blog": 0.50,
    "forum": 0.45,
    "vendor": 0.65,
    "unknown": 0.40,
    # source_card schema enum coverage (singular forms used by source cards)
    "official_doc": 0.95,
    "book": 0.40,
    "personal_note": 0.30,
    "internal_doc": 0.50,
}

_DEFAULT_WEIGHT: float = 0.40

# Freshness bonuses (spec §15.3)
_FRESHNESS_LESS_THAN_30: float = 0.10
_FRESHNESS_LESS_THAN_180: float = 0.05

# Risk-flag penalties (spec §15.3)
_RISK_PENALTIES: dict[str, float] = {
    "vendor_marketing": -0.05,
    "stale": -0.20,
    "extraction_low_confidence": -0.15,
    "conflicts_with_other_sources": -0.20,
    # Aliases
    "low_authority": -0.10,
    "possible_prompt_injection": -0.10,
}


def authority_score(
    source_type: str | None,
    *,
    freshness_days: int | None = None,
    risk_flags: list[str] | None = None,
) -> float:
    """Compute an authority score in [0, 1] for a source.

    Parameters
    ----------
    source_type:
        One of the canonical type strings (e.g. ``"official_docs"``).
        Unknown types receive a default weight of 0.40.
    freshness_days:
        How many days ago the source was published/last modified.
        ``None`` means age is unknown — no freshness bonus applied.
    risk_flags:
        List of risk-flag strings.  Each known flag subtracts a penalty.

    Returns
    -------
    float
        Clamped to [0.0, 1.0].
    """
    base = _SOURCE_TYPE_WEIGHT.get(source_type or "", _DEFAULT_WEIGHT)

    # Freshness bonus
    freshness_bonus: float = 0.0
    if freshness_days is not None:
        if freshness_days < 30:  # noqa: PLR2004
            freshness_bonus = _FRESHNESS_LESS_THAN_30
        elif freshness_days < 180:  # noqa: PLR2004
            freshness_bonus = _FRESHNESS_LESS_THAN_180

    # Risk penalties
    penalty: float = 0.0
    for flag in risk_flags or []:
        penalty += _RISK_PENALTIES.get(flag, 0.0)

    raw = base + freshness_bonus + penalty
    return max(0.0, min(1.0, raw))


def rank_hits(hits: list[SearchHit]) -> list[SearchHit]:
    """Return *hits* sorted by composite authority key.

    Sort order (all stable):

    1. ``score`` descending — higher explicit score first (``None`` → treated
       as 0.0 so scored hits always precede unscored ones).
    2. Source-type authority descending — ``official_docs`` before ``unknown``.
    3. ``rank`` ascending — lower provider-assigned rank is better (0 = unset,
       treated as last).
    """

    def sort_key(h: SearchHit) -> tuple[float, float, int]:
        score = h.score if h.score is not None else 0.0
        st_authority = _SOURCE_TYPE_WEIGHT.get(h.source_type or "", _DEFAULT_WEIGHT)
        raw_rank = h.rank if h.rank > 0 else 999_999
        # Negate score/authority so descending comes first with default ascending sort
        return (-score, -st_authority, raw_rank)

    return sorted(hits, key=sort_key)


__all__ = ["authority_score", "rank_hits"]
