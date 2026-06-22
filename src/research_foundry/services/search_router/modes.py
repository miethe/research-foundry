"""Search mode definitions for the Research Foundry Search Router.

Each :class:`SearchMode` captures the intent, default provider chain,
budget caps, and expected outputs for one of the 11 canonical search
modes defined in the spec §7/§12.

Usage::

    from research_foundry.services.search_router.modes import get_mode, MODES

    mode = get_mode("source_discovery")
    print(mode.provider_chain)   # ('brave', 'exa')
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchMode:
    """Immutable descriptor for a canonical search mode."""

    name: str
    purpose: str
    provider_chain: tuple[str, ...]
    budget: dict[str, int | float]
    outputs: tuple[str, ...]


# ---------------------------------------------------------------------------
# Canonical mode definitions (spec §7/§12)
# ---------------------------------------------------------------------------

MODES: dict[str, SearchMode] = {
    "cache_first": SearchMode(
        name="cache_first",
        purpose="Return results from previously stored source cards without any external query.",
        provider_chain=(),
        budget={
            "max_external_queries": 0,
            "max_urls_to_extract": 0,
            "max_crawl_pages": 0,
            "max_provider_cost_usd": 0.0,
            "max_latency_seconds": 10,
        },
        outputs=("source_cards",),
    ),
    "known_url_extract": SearchMode(
        name="known_url_extract",
        purpose=(
            "Extract full markdown content from one or more known URLs using"
            " a structured extraction provider."
        ),
        provider_chain=("jina", "firecrawl"),
        budget={
            "max_external_queries": 0,
            "max_urls_to_extract": 10,
            "max_crawl_pages": 0,
            "max_provider_cost_usd": 0.10,
            "max_latency_seconds": 60,
        },
        outputs=("extracted_markdown", "source_cards"),
    ),
    "quick_lookup": SearchMode(
        name="quick_lookup",
        purpose="Fast web search for a single factual lookup; low cost, breadth over depth.",
        provider_chain=("brave",),
        budget={
            "max_external_queries": 2,
            "max_urls_to_extract": 3,
            "max_crawl_pages": 0,
            "max_provider_cost_usd": 0.05,
            "max_latency_seconds": 30,
        },
        outputs=("source_cards", "summary"),
    ),
    "source_discovery": SearchMode(
        name="source_discovery",
        purpose=(
            "Discover broad sources on a topic using web search followed by semantic"
            " re-ranking."
        ),
        provider_chain=("brave", "exa"),
        budget={
            "max_external_queries": 4,
            "max_urls_to_extract": 8,
            "max_crawl_pages": 0,
            "max_provider_cost_usd": 0.25,
            "max_latency_seconds": 90,
        },
        outputs=("source_cards", "summary"),
    ),
    "semantic_discovery": SearchMode(
        name="semantic_discovery",
        purpose=(
            "Semantic-similarity search across web + code repositories for highly"
            " relevant sources."
        ),
        provider_chain=("exa", "github", "brave"),
        budget={
            "max_external_queries": 5,
            "max_urls_to_extract": 10,
            "max_crawl_pages": 0,
            "max_provider_cost_usd": 0.30,
            "max_latency_seconds": 120,
        },
        outputs=("source_cards", "extracted_markdown", "summary"),
    ),
    "official_source_check": SearchMode(
        name="official_source_check",
        purpose=(
            "Verify or find official/authoritative sources for a claim, preferring"
            " high-authority domains."
        ),
        provider_chain=("brave", "exa"),
        budget={
            "max_external_queries": 3,
            "max_urls_to_extract": 5,
            "max_crawl_pages": 0,
            "max_provider_cost_usd": 0.15,
            "max_latency_seconds": 60,
        },
        outputs=("source_cards", "claim_ledger"),
    ),
    "github_discovery": SearchMode(
        name="github_discovery",
        purpose="Discover relevant GitHub repositories, READMEs, and code artefacts.",
        provider_chain=("github", "exa", "brave"),
        budget={
            "max_external_queries": 4,
            "max_urls_to_extract": 6,
            "max_crawl_pages": 0,
            "max_provider_cost_usd": 0.20,
            "max_latency_seconds": 90,
        },
        outputs=("source_cards", "summary"),
    ),
    "academic_discovery": SearchMode(
        name="academic_discovery",
        purpose=(
            "Search academic databases (OpenAlex, Semantic Scholar, PubMed, arXiv)"
            " for peer-reviewed sources."
        ),
        provider_chain=(),
        budget={
            "max_external_queries": 4,
            "max_urls_to_extract": 8,
            "max_crawl_pages": 0,
            "max_provider_cost_usd": 0.10,
            "max_latency_seconds": 120,
        },
        outputs=("source_cards", "claim_ledger", "summary"),
    ),
    "docs_crawl": SearchMode(
        name="docs_crawl",
        purpose="Crawl a documentation site or set of pages for comprehensive coverage.",
        provider_chain=("firecrawl",),
        budget={
            "max_external_queries": 1,
            "max_urls_to_extract": 0,
            "max_crawl_pages": 50,
            "max_provider_cost_usd": 0.50,
            "max_latency_seconds": 300,
        },
        outputs=("extracted_markdown", "source_cards"),
    ),
    "deep_research": SearchMode(
        name="deep_research",
        purpose=(
            "Multi-stage deep research: discovery → extraction → synthesis; high"
            " cost, maximum coverage."
        ),
        provider_chain=(),
        budget={
            "max_external_queries": 10,
            "max_urls_to_extract": 20,
            "max_crawl_pages": 20,
            "max_provider_cost_usd": 2.00,
            "max_latency_seconds": 600,
        },
        outputs=("source_cards", "extracted_markdown", "claim_ledger", "summary"),
    ),
    "monitoring_delta": SearchMode(
        name="monitoring_delta",
        purpose=(
            "Lightweight recurring scout that detects new/changed sources since the"
            " last run."
        ),
        provider_chain=(),
        budget={
            "max_external_queries": 2,
            "max_urls_to_extract": 4,
            "max_crawl_pages": 0,
            "max_provider_cost_usd": 0.05,
            "max_latency_seconds": 60,
        },
        outputs=("source_cards",),
    ),
}

_VALID_NAMES = frozenset(MODES)


def get_mode(name: str) -> SearchMode:
    """Return the :class:`SearchMode` for *name*, raising :exc:`KeyError` if unknown."""
    try:
        return MODES[name]
    except KeyError:
        valid = ", ".join(sorted(_VALID_NAMES))
        raise KeyError(f"Unknown search mode {name!r}. Valid modes: {valid}") from None


__all__ = ["SearchMode", "MODES", "get_mode"]
