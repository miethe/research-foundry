"""Structured provider metadata capture at ingest (source-metadata-propagation-v1,
SMP-1.2/SMP-1.6/SMP-1.7).

Covers:

* A card ingested with structured provider metadata (``authors``/``doi``/
  ``publisher``/``version``) carries those real values instead of the
  pre-change hardcoded-empty shape (``source_cards.py:322-338`` before this
  change).
* Omitting provider metadata entirely reproduces the pre-existing empty
  shape byte-for-byte (regression guard -- every current caller of
  ``ingest_source()``/``create_source_card()`` omits these kwargs).
* Provider strings are externally controlled (search-router provider
  responses, or any other caller) -- a malformed (wrong type) or oversized
  value is REJECTED at the ingest boundary, before any file is written,
  rather than silently truncated or coerced. This is the untrusted-input
  control that escalated M1's gate to ``[security, validator]``.
"""

from __future__ import annotations

import pytest

from research_foundry.errors import SchemaError
from research_foundry.frontmatter import load_md
from research_foundry.paths import FoundryPaths
from research_foundry.services.source_cards import ingest_source

# ---------------------------------------------------------------------------
# Metadata population (SMP-1.2)
# ---------------------------------------------------------------------------


def test_ingest_source_threads_structured_provider_metadata_onto_card(
    tmp_foundry: FoundryPaths,
) -> None:
    """Real authors/DOI/publisher/version reach the written card front matter."""

    run_id = "rf_run_provider_metadata"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    result = ingest_source(
        "https://example.com/article",
        run_id=run_id,
        source_type="paper",
        content="A study of the thing.",
        authors=["Jane Doe", "John Smith"],
        doi="10.1000/xyz123",
        publisher="Acme Press",
        version="v2",
        paths=tmp_foundry,
    )

    metadata, _ = load_md(result.path)
    source = metadata["source"]
    assert source["authors"] == ["Jane Doe", "John Smith"]
    assert source["locator"]["doi"] == "10.1000/xyz123"
    assert source["publisher"] == "Acme Press"
    assert source["version"] == "v2"


def test_ingest_source_without_provider_metadata_keeps_pre_change_empty_shape(
    tmp_foundry: FoundryPaths,
) -> None:
    """Every existing caller omits the new kwargs -- the empty shape is unchanged."""

    run_id = "rf_run_no_provider_metadata"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    result = ingest_source(
        "https://example.com/plain",
        run_id=run_id,
        content="Plain content, no provider metadata.",
        paths=tmp_foundry,
    )

    metadata, _ = load_md(result.path)
    source = metadata["source"]
    assert source["authors"] == []
    assert source["locator"]["doi"] is None
    assert source["publisher"] is None
    assert source["version"] is None


# ---------------------------------------------------------------------------
# Ingest-boundary bounding + type checking (SMP-1.6, untrusted input)
# ---------------------------------------------------------------------------


def test_ingest_source_rejects_oversized_doi(tmp_foundry: FoundryPaths) -> None:
    """A DOI far longer than any real DOI must be rejected, not truncated."""

    run_id = "rf_run_oversized_doi"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    with pytest.raises(SchemaError):
        ingest_source(
            "https://example.com/bad-doi",
            run_id=run_id,
            content="text",
            doi="10.1000/" + ("x" * 300),
            paths=tmp_foundry,
        )

    # Rejected before any card reaches disk -- the malformed call leaves no trace.
    assert list(tmp_foundry.run_paths(run_id).sources.glob("*.md")) == []


def test_ingest_source_rejects_non_string_doi(tmp_foundry: FoundryPaths) -> None:
    """A DOI of the wrong type is rejected -- no implicit coercion."""

    run_id = "rf_run_malformed_doi_type"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    with pytest.raises(SchemaError):
        ingest_source(
            "https://example.com/bad-doi-type",
            run_id=run_id,
            content="text",
            doi=12345,  # type: ignore[arg-type]
            paths=tmp_foundry,
        )


def test_ingest_source_rejects_oversized_publisher(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_oversized_publisher"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    with pytest.raises(SchemaError):
        ingest_source(
            "https://example.com/bad-publisher",
            run_id=run_id,
            content="text",
            publisher="x" * 500,
            paths=tmp_foundry,
        )


def test_ingest_source_rejects_oversized_version(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_oversized_version"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    with pytest.raises(SchemaError):
        ingest_source(
            "https://example.com/bad-version",
            run_id=run_id,
            content="text",
            version="v" * 200,
            paths=tmp_foundry,
        )


def test_ingest_source_rejects_non_list_authors(tmp_foundry: FoundryPaths) -> None:
    """authors must be a list[str] -- a bare string is rejected, not iterated char-by-char."""

    run_id = "rf_run_authors_not_list"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    with pytest.raises(SchemaError):
        ingest_source(
            "https://example.com/bad-authors-type",
            run_id=run_id,
            content="text",
            authors="Jane Doe",  # type: ignore[arg-type]
            paths=tmp_foundry,
        )


def test_ingest_source_rejects_non_string_author_entry(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_authors_bad_entry"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    with pytest.raises(SchemaError):
        ingest_source(
            "https://example.com/bad-author-entry",
            run_id=run_id,
            content="text",
            authors=["Jane Doe", 42],  # type: ignore[list-item]
            paths=tmp_foundry,
        )


def test_ingest_source_rejects_oversized_author_name(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_oversized_author_name"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    with pytest.raises(SchemaError):
        ingest_source(
            "https://example.com/oversized-author",
            run_id=run_id,
            content="text",
            authors=["A" * 1000],
            paths=tmp_foundry,
        )


def test_ingest_source_rejects_too_many_authors(tmp_foundry: FoundryPaths) -> None:
    run_id = "rf_run_too_many_authors"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    with pytest.raises(SchemaError):
        ingest_source(
            "https://example.com/too-many-authors",
            run_id=run_id,
            content="text",
            authors=[f"Author {i}" for i in range(200)],
            paths=tmp_foundry,
        )


def test_ingest_source_accepts_metadata_at_the_boundary(tmp_foundry: FoundryPaths) -> None:
    """Values exactly at the length/count limits are accepted (boundary, not off-by-one)."""

    run_id = "rf_run_boundary_metadata"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    result = ingest_source(
        "https://example.com/boundary",
        run_id=run_id,
        content="text",
        authors=["A" * 300] * 64,
        doi="1" * 128,
        publisher="P" * 300,
        version="V" * 64,
        paths=tmp_foundry,
    )

    metadata, _ = load_md(result.path)
    source = metadata["source"]
    assert len(source["authors"]) == 64
    assert len(source["locator"]["doi"]) == 128
    assert len(source["publisher"]) == 300
    assert len(source["version"]) == 64
