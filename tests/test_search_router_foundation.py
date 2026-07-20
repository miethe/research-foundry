"""Unit tests for the Research Foundry Search Router Wave-1 foundation.

Covers:
- canonicalize_url: tracking param removal, fragment, port, www, trailing slash
- dedupe_hits: score-wins, rank-wins, stable order
- authority_score: source-type weights, freshness bonuses, risk penalties
- Budget / BudgetTracker: limits, gates, exceeded() messages
- MODES: all canonical modes present (11 spec modes + free_discovery)
- SchemaRegistry: validates a minimal SearchRequest, a minimal SearchRun,
  and rejects a bad mode enum value.
"""

from __future__ import annotations

import pytest

from research_foundry.schemas import SchemaRegistry
from research_foundry.services.search_router.budgets import Budget, BudgetTracker
from research_foundry.services.search_router.dedupe import canonicalize_url, dedupe_hits
from research_foundry.services.search_router.modes import MODES
from research_foundry.services.search_router.providers.base import SearchHit
from research_foundry.services.search_router.ranking import authority_score, rank_hits

# ---------------------------------------------------------------------------
# canonicalize_url
# ---------------------------------------------------------------------------

_CANON_CASES: list[tuple[str, str]] = [
    # Strip UTM params
    (
        "https://example.com/page?utm_source=google&utm_medium=cpc",
        "https://example.com/page",
    ),
    # Strip fragment
    (
        "https://example.com/page#section",
        "https://example.com/page",
    ),
    # Strip default HTTPS port
    (
        "https://example.com:443/page",
        "https://example.com/page",
    ),
    # Strip default HTTP port
    (
        "http://example.com:80/page",
        "http://example.com/page",
    ),
    # Keep non-default port
    (
        "https://example.com:8443/page",
        "https://example.com:8443/page",
    ),
    # Drop www.
    (
        "https://www.example.com/page",
        "https://example.com/page",
    ),
    # Strip trailing slash (non-root)
    (
        "https://example.com/page/",
        "https://example.com/page",
    ),
    # Root slash preserved
    (
        "https://example.com/",
        "https://example.com/",
    ),
    # Strip ref param
    (
        "https://example.com/page?ref=newsletter",
        "https://example.com/page",
    ),
    # Strip fbclid
    (
        "https://example.com/page?fbclid=abc123&q=hello",
        "https://example.com/page?q=hello",
    ),
    # Lowercase scheme and host
    (
        "HTTPS://EXAMPLE.COM/Page",
        "https://example.com/Page",
    ),
    # Mixed tracking + real params
    (
        "https://example.com/search?q=python&utm_campaign=spring&sort=date",
        "https://example.com/search?q=python&sort=date",
    ),
]


@pytest.mark.parametrize("url,expected", _CANON_CASES)
def test_canonicalize_url(url: str, expected: str) -> None:
    assert canonicalize_url(url) == expected


def test_canonicalize_url_empty_string() -> None:
    assert canonicalize_url("") == ""


# ---------------------------------------------------------------------------
# dedupe_hits
# ---------------------------------------------------------------------------


def _hit(
    url: str,
    title: str = "T",
    rank: int = 0,
    score: float | None = None,
    provider: str = "test",
) -> SearchHit:
    return SearchHit(title=title, url=url, rank=rank, score=score, provider=provider)


def test_dedupe_hits_removes_duplicate_canonical_url() -> None:
    hits = [
        _hit("https://www.example.com/page"),
        _hit("https://example.com/page"),
    ]
    result = dedupe_hits(hits)
    assert len(result) == 1
    assert canonicalize_url(result[0].url) == "https://example.com/page"


def test_dedupe_hits_keeps_higher_score() -> None:
    hits = [
        _hit("https://example.com/page", score=0.5, rank=1),
        _hit("https://www.example.com/page", score=0.9, rank=2),
    ]
    result = dedupe_hits(hits)
    assert len(result) == 1
    assert result[0].score == 0.9


def test_dedupe_hits_keeps_lower_rank_when_scores_equal() -> None:
    hits = [
        _hit("https://example.com/page", rank=5, score=0.7),
        _hit("https://www.example.com/page", rank=2, score=0.7),
    ]
    result = dedupe_hits(hits)
    assert len(result) == 1
    assert result[0].rank == 2


def test_dedupe_hits_stable_order() -> None:
    hits = [
        _hit("https://a.com/"),
        _hit("https://b.com/"),
        _hit("https://a.com/"),  # duplicate
        _hit("https://c.com/"),
    ]
    result = dedupe_hits(hits)
    assert [canonicalize_url(h.url) for h in result] == [
        "https://a.com/",
        "https://b.com/",
        "https://c.com/",
    ]


def test_dedupe_hits_empty() -> None:
    assert dedupe_hits([]) == []


# ---------------------------------------------------------------------------
# authority_score
# ---------------------------------------------------------------------------


def test_authority_score_ordering() -> None:
    """Official docs > paper > repo > news > blog > forum > unknown."""
    assert authority_score("official_docs") > authority_score("academic_paper")
    assert authority_score("academic_paper") >= authority_score("repo")
    assert authority_score("repo") > authority_score("community_forum")
    assert authority_score("community_forum") > authority_score("unknown_blog")


def test_authority_score_freshness_bonus_30_days() -> None:
    base = authority_score("repo")
    fresh = authority_score("repo", freshness_days=15)
    assert fresh == pytest.approx(base + 0.10)


def test_authority_score_freshness_bonus_180_days() -> None:
    base = authority_score("repo")
    fresh = authority_score("repo", freshness_days=90)
    assert fresh == pytest.approx(base + 0.05)


def test_authority_score_no_freshness_bonus_old() -> None:
    base = authority_score("repo")
    old = authority_score("repo", freshness_days=365)
    assert old == pytest.approx(base)


def test_authority_score_risk_penalty_stale() -> None:
    base = authority_score("repo")
    stale = authority_score("repo", risk_flags=["stale"])
    assert stale == pytest.approx(base - 0.20)


def test_authority_score_risk_penalty_vendor_marketing() -> None:
    base = authority_score("vendor_blog")
    flagged = authority_score("vendor_blog", risk_flags=["vendor_marketing"])
    assert flagged == pytest.approx(base - 0.05)


def test_authority_score_clamped_to_zero() -> None:
    # Many penalties should not go negative
    score = authority_score(
        "unknown_blog",
        risk_flags=["stale", "conflicts_with_other_sources", "extraction_low_confidence"],
    )
    assert score >= 0.0


def test_authority_score_clamped_to_one() -> None:
    score = authority_score("official_docs", freshness_days=1)
    assert score <= 1.0


def test_authority_score_unknown_type_uses_default() -> None:
    score = authority_score(None)
    assert 0.0 <= score <= 1.0
    score2 = authority_score("not_a_real_type")
    assert 0.0 <= score2 <= 1.0


# ---------------------------------------------------------------------------
# rank_hits
# ---------------------------------------------------------------------------


def test_rank_hits_by_score_descending() -> None:
    hits = [
        _hit("https://a.com/", score=0.3),
        _hit("https://b.com/", score=0.9),
        _hit("https://c.com/", score=0.6),
    ]
    ranked = rank_hits(hits)
    assert [h.score for h in ranked] == [0.9, 0.6, 0.3]


def test_rank_hits_official_docs_before_unknown_on_equal_score() -> None:
    hits = [
        SearchHit(title="U", url="https://a.com/", score=0.5, source_type="unknown"),
        SearchHit(title="O", url="https://b.com/", score=0.5, source_type="official_docs"),
    ]
    ranked = rank_hits(hits)
    assert ranked[0].source_type == "official_docs"


# ---------------------------------------------------------------------------
# Budget + BudgetTracker
# ---------------------------------------------------------------------------


def test_budget_defaults() -> None:
    b = Budget()
    assert b.max_external_queries == 4
    assert b.max_urls_to_extract == 8
    assert b.max_crawl_pages == 0
    assert b.max_provider_cost_usd == 0.25
    assert b.max_latency_seconds == 90


def test_budget_from_request_dict() -> None:
    req = {"budget": {"max_external_queries": 2, "max_provider_cost_usd": 0.10}}
    b = Budget.from_request_dict(req)
    assert b.max_external_queries == 2
    assert b.max_provider_cost_usd == 0.10
    # unspecified fields fall back to defaults
    assert b.max_urls_to_extract == 8


def test_budget_from_request_dict_missing_budget_key() -> None:
    b = Budget.from_request_dict({})
    assert b == Budget()


def test_budget_tracker_can_query() -> None:
    t = BudgetTracker(Budget(max_external_queries=2))
    assert t.can_query()
    t.add_query()
    assert t.can_query()
    t.add_query()
    assert not t.can_query()


def test_budget_tracker_can_extract() -> None:
    t = BudgetTracker(Budget(max_urls_to_extract=3))
    assert t.can_extract()
    t.add_extract(2)
    assert t.can_extract(1)
    assert not t.can_extract(2)


def test_budget_tracker_exceeded_none_when_ok() -> None:
    t = BudgetTracker(Budget())
    assert t.exceeded() is None


def test_budget_tracker_exceeded_query_limit() -> None:
    t = BudgetTracker(Budget(max_external_queries=1))
    t.add_query()
    t.add_query()  # over limit
    reason = t.exceeded()
    assert reason is not None
    assert "query" in reason.lower()


def test_budget_tracker_exceeded_cost_limit() -> None:
    t = BudgetTracker(Budget(max_provider_cost_usd=0.05))
    t.add_cost(0.10)
    reason = t.exceeded()
    assert reason is not None
    assert "cost" in reason.lower()


def test_budget_tracker_exceeded_url_limit() -> None:
    t = BudgetTracker(Budget(max_urls_to_extract=2))
    t.add_extract(3)
    reason = t.exceeded()
    assert reason is not None
    assert "url" in reason or "extraction" in reason.lower()


# ---------------------------------------------------------------------------
# MODES completeness
# ---------------------------------------------------------------------------

_EXPECTED_MODES = {
    "cache_first",
    "known_url_extract",
    "quick_lookup",
    "source_discovery",
    "semantic_discovery",
    "official_source_check",
    "github_discovery",
    "academic_discovery",
    "docs_crawl",
    "deep_research",
    "monitoring_delta",
    "free_discovery",
}


def test_modes_covers_all_canonical() -> None:
    assert _EXPECTED_MODES == set(MODES.keys())


def test_modes_frozen_dataclass() -> None:
    from research_foundry.services.search_router.modes import SearchMode

    mode = MODES["source_discovery"]
    assert isinstance(mode, SearchMode)
    with pytest.raises((AttributeError, TypeError)):
        mode.name = "mutated"  # type: ignore[misc]


def test_get_mode_valid() -> None:
    from research_foundry.services.search_router.modes import get_mode

    mode = get_mode("source_discovery")
    assert mode.name == "source_discovery"
    assert "brave" in mode.provider_chain
    assert "exa" in mode.provider_chain


def test_get_mode_unknown_raises() -> None:
    from research_foundry.services.search_router.modes import get_mode

    with pytest.raises(KeyError, match="unknown_mode"):
        get_mode("unknown_mode")


# ---------------------------------------------------------------------------
# SchemaRegistry — search_request and search_run validation
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def schema_reg() -> SchemaRegistry:
    """Load schemas from the project-root schemas/ directory."""
    return SchemaRegistry(schemas_dir="schemas")


def test_schema_registry_has_search_request(schema_reg: SchemaRegistry) -> None:
    assert schema_reg.has("search_request")


def test_schema_registry_has_search_run(schema_reg: SchemaRegistry) -> None:
    assert schema_reg.has("search_run")


def test_search_request_minimal_valid(schema_reg: SchemaRegistry) -> None:
    instance = {"query": "What is Research Foundry?", "mode": "source_discovery"}
    result = schema_reg.validate(instance, "search_request")
    assert result.ok, result.errors


def test_search_request_full_valid(schema_reg: SchemaRegistry) -> None:
    instance = {
        "request_id": "req_001",
        "intent_id": "int_001",
        "query": "LLM evaluation frameworks",
        "mode": "semantic_discovery",
        "constraints": {
            "allowed_domains": ["arxiv.org"],
            "blocked_domains": ["spam.example.com"],
            "required_source_types": ["paper", "repo"],
            "max_source_age_days": 365,
            "language": "en",
            "region": None,
        },
        "budget": {
            "max_external_queries": 5,
            "max_urls_to_extract": 10,
            "max_crawl_pages": 0,
            "max_provider_cost_usd": 0.30,
            "max_latency_seconds": 120,
        },
        "output_requirements": {
            "source_cards": True,
            "claim_ledger": False,
            "extracted_markdown": True,
            "summary": True,
        },
        "approval": {"requires_human_approval": False, "reason": None},
    }
    result = schema_reg.validate(instance, "search_request")
    assert result.ok, result.errors


def test_search_request_bad_mode_rejected(schema_reg: SchemaRegistry) -> None:
    instance = {"query": "something", "mode": "not_a_valid_mode"}
    result = schema_reg.validate(instance, "search_request")
    assert not result.ok
    assert any("mode" in e.lower() or "not_a_valid_mode" in e for e in result.errors)


def test_search_request_missing_required_rejected(schema_reg: SchemaRegistry) -> None:
    instance = {"mode": "quick_lookup"}  # missing 'query'
    result = schema_reg.validate(instance, "search_request")
    assert not result.ok


def test_search_request_schema_accepts_every_canonical_mode(
    schema_reg: SchemaRegistry,
) -> None:
    """Regression guard: every MODES key must be a valid `mode` enum value.

    Prevents drift between `modes.py` (the code-level source of truth for
    canonical modes) and `search_request.schema.yaml`'s `mode` enum — a new
    mode added to one without the other silently rejects live requests
    (schema_errors populated) even though the run otherwise completes.
    """
    for mode_name in MODES:
        instance = {"query": "regression check", "mode": mode_name}
        result = schema_reg.validate(instance, "search_request")
        assert result.ok, f"mode {mode_name!r} rejected by search_request schema: {result.errors}"


def test_search_run_minimal_valid(schema_reg: SchemaRegistry) -> None:
    instance = {
        "run_id": "rf_run_abc123",
        "request": {"query": "test query", "mode": "quick_lookup"},
    }
    result = schema_reg.validate(instance, "search_run")
    assert result.ok, result.errors


def test_search_run_full_valid(schema_reg: SchemaRegistry) -> None:
    instance = {
        "run_id": "rf_run_abc123",
        "created_at": "2026-06-21T10:00:00+00:00",
        "completed_at": "2026-06-21T10:00:05+00:00",
        "request": {"query": "test query", "mode": "source_discovery"},
        "provider_chain": [
            {"provider": "brave", "role": "discovery", "status": "success"},
        ],
        "normalized_results": [
            {
                "title": "Example",
                "url": "https://example.com/",
                "snippet": "An example.",
                "provider": "brave",
                "rank": 1,
                "score": None,
            }
        ],
        "source_cards": [{"source_id": "sc_001"}],
        "metrics": {
            "queries_executed": 1,
            "urls_extracted": 1,
            "pages_crawled": 0,
            "useful_source_count": 1,
            "duplicate_rate": 0.0,
            "extraction_failure_rate": 0.0,
            "citation_coverage": None,
            "estimated_cost_usd": 0.005,
            "latency_ms": 1234,
        },
        "writebacks": {
            "ccdash_event_id": None,
            "meatywiki_page_ids": [],
            "skillmeat_candidate_ids": [],
        },
    }
    result = schema_reg.validate(instance, "search_run")
    assert result.ok, result.errors


def test_search_run_missing_required_rejected(schema_reg: SchemaRegistry) -> None:
    instance = {"request": {"query": "test", "mode": "quick_lookup"}}  # missing run_id
    result = schema_reg.validate(instance, "search_run")
    assert not result.ok
