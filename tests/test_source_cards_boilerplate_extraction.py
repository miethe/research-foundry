"""Regression test for node_01M1WWWPMDCB1X58WRBZWFR4DC.

``_build_points`` (services/source_cards.py) used to take the first
``_MAX_POINTS`` (8) blank-line-separated paragraphs unconditionally. On
chrome-heavy academic-paper page shapes (arxiv.org/abs, aclanthology.org),
nav/breadcrumb/button-label lines ('Skip to main content', 'Search', 'Log
in', an arXiv id line) fill all 8 slots before the real Abstract paragraph
is ever reached, so the source card's ``extracted_points`` never contain the
paper's actual claims -- only page furniture.

This fixture is an OFFLINE plain-text stand-in for that page shape: 9 short,
non-sentence nav-chrome lines followed by the real abstract paragraph. No
network call is made (``content`` is passed directly to ``ingest_source``,
mirroring the pattern in ``test_source_cards_extraction_status.py``).
"""

from __future__ import annotations

from research_foundry.frontmatter import load_md
from research_foundry.paths import FoundryPaths
from research_foundry.services.source_cards import ingest_source

_NAV_CHROME_LINES = [
    "Skip to main content",
    "arXiv Home",
    "Search",
    "arxiv.org > abs > 2307.03172",
    "Submit",
    "Donate",
    "Log in",
    "Press Enter to search",
    "arXiv:2307.03172",
]

_ABSTRACT = (
    "Abstract: While recent large language models demonstrate strong "
    "performance on many benchmark tasks, they still struggle to reliably "
    "distinguish supported claims from unsupported speculation when asked "
    "to summarize source documents."
)


def _fixture_content() -> str:
    return "\n\n".join(_NAV_CHROME_LINES + [_ABSTRACT])


def test_boilerplate_heavy_page_still_extracts_real_content(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_boilerplate_extraction_test"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    result = ingest_source(
        "https://arxiv.org/abs/2307.03172",
        run_id=run_id,
        content=_fixture_content(),
        paths=tmp_foundry,
    )

    meta, _body = load_md(result.path)
    points = meta.get("extracted_points") or []
    summaries = " ".join(str(p.get("summary") or "") for p in points)
    quotes = " ".join(str(p.get("quote") or "") for p in points)

    assert "recent large language models" in summaries or "recent large language models" in quotes


def test_all_boilerplate_content_still_yields_points(tmp_foundry: FoundryPaths) -> None:
    """If every paragraph looks like chrome, ingestion must not silently drop
    to zero points -- it falls back to the unfiltered (capped) list."""

    run_id = "rf_run_all_boilerplate_test"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    result = ingest_source(
        "https://example.com/nav-only",
        run_id=run_id,
        content="\n\n".join(_NAV_CHROME_LINES),
        paths=tmp_foundry,
    )

    meta, _body = load_md(result.path)
    points = meta.get("extracted_points") or []
    assert len(points) > 0
