"""Tests for the explicit ``extraction_status`` tri-state on source cards.

OFFLINE-ONLY: no network calls. Uses the shared ``tmp_foundry`` fixture (copies
canonical schemas/config) so schema validation behaves exactly as in the real
workspace. Covers the derived default (from ``degraded``/``content``), the
offline-locator-only path (mirrors ``test_ingest_source_without_content_unchanged``
in ``tests/test_search_router_router.py``), the explicit-override seam that lets
callers (e.g. a future PDF-partial extractor) pass through a real tri-state
value, and that the value round-trips through the written frontmatter.
"""

from __future__ import annotations

from research_foundry.frontmatter import load_md
from research_foundry.paths import FoundryPaths
from research_foundry.services.source_cards import ExtractionStatus, ingest_source


def test_ingest_source_with_content_is_full_text(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_fulltext"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    result = ingest_source(
        "https://example.com/a",
        run_id=run_id,
        content="real text",
        paths=tmp_foundry,
    )

    assert result.degraded is False
    assert result.extraction_status == ExtractionStatus.full_text.value


def test_ingest_source_offline_url_is_locator_only(tmp_foundry: FoundryPaths) -> None:
    """Mirrors test_ingest_source_without_content_unchanged: offline default degrades."""

    run_id = "rf_run_locatoronly"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    result = ingest_source(
        "https://example.com/y",
        run_id=run_id,
        fetch=False,
        paths=tmp_foundry,
    )

    assert result.degraded is True
    assert result.extraction_status == ExtractionStatus.locator_only.value
    assert result.path.exists()


def test_ingest_source_explicit_override_wins_over_derived_value(tmp_foundry: FoundryPaths) -> None:
    """An explicit override (e.g. future PDF-partial signal) beats the derived default."""

    run_id = "rf_run_partial_override"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    result = ingest_source(
        "https://example.com/b",
        run_id=run_id,
        content="text",
        extraction_status="partial",
        paths=tmp_foundry,
    )

    # degraded would otherwise compute False (content is truthy) — override wins.
    assert result.degraded is False
    assert result.extraction_status == ExtractionStatus.partial.value

    metadata, _ = load_md(result.path)
    assert metadata.get("extraction_status") == "partial"


def test_extraction_status_round_trips_through_written_frontmatter(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_roundtrip"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    result = ingest_source(
        "https://example.com/c",
        run_id=run_id,
        content="round trip text",
        paths=tmp_foundry,
    )

    metadata, _ = load_md(result.path)
    assert "extraction_status" in metadata
    assert metadata["extraction_status"] == ExtractionStatus.full_text.value


def test_ingest_source_unrecognized_override_falls_back_to_derived_value(
    tmp_foundry: FoundryPaths,
) -> None:
    """Fail-open: an unrecognized override value never raises; derived value wins."""

    run_id = "rf_run_bad_override"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    result = ingest_source(
        "https://example.com/d",
        run_id=run_id,
        content="text",
        extraction_status="not_a_real_status",
        paths=tmp_foundry,
    )

    assert result.extraction_status == ExtractionStatus.full_text.value
