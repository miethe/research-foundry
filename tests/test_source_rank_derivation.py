"""``trust.source_rank`` deterministic derivation (source-metadata-propagation-v1, SMP-1.3/SMP-1.7).

OQ-4 resolution (recorded in
``.claude/worknotes/source-metadata-propagation/implementation-notes.md``):
``derive_source_rank`` is a pure function of ``source_type`` alone -- no
model call, network call, or wall-clock read. Covers: a known ``source_type``
maps to a known, non-``"unknown"`` rank; an unrecognized/absent ``source_type``
stays ``"unknown"`` rather than being guessed; and an end-to-end proof that
``ingest_source()`` actually wires the derivation in (not just the pure
function in isolation).
"""

from __future__ import annotations

from research_foundry.frontmatter import load_md
from research_foundry.paths import FoundryPaths
from research_foundry.services.source_cards import ingest_source
from research_foundry.services.source_rank import derive_source_rank


def test_known_source_type_maps_to_known_rank() -> None:
    """A known source_type deterministically maps to a known (non-unknown) rank."""

    assert derive_source_rank("paper") == "primary"
    assert derive_source_rank("standard") == "primary"
    assert derive_source_rank("official_doc") == "primary"
    assert derive_source_rank("repo") == "primary"
    assert derive_source_rank("news") == "secondary"
    assert derive_source_rank("blog") == "secondary"
    assert derive_source_rank("book") == "tertiary"


def test_unknown_source_type_stays_unknown() -> None:
    """A source_type the mapping cannot classify stays 'unknown' -- never guessed."""

    assert derive_source_rank("other") == "unknown"
    assert derive_source_rank("personal_note") == "unknown"
    assert derive_source_rank("internal_doc") == "unknown"
    # Not a real source_type at all -- still degrades to unknown, never raises.
    assert derive_source_rank("not_a_real_source_type") == "unknown"
    assert derive_source_rank(None) == "unknown"  # type: ignore[arg-type]


def test_derivation_is_deterministic_across_repeated_calls() -> None:
    """Same input always yields the same output (pure function, no hidden state)."""

    for _ in range(3):
        assert derive_source_rank("paper") == "primary"
        assert derive_source_rank("other") == "unknown"


def test_ingest_source_wires_derived_rank_for_known_source_type(tmp_foundry: FoundryPaths) -> None:
    """End-to-end: a card ingested with a classifiable source_type carries the
    derived rank, not the pre-change hardcoded 'unknown'."""

    run_id = "rf_run_source_rank_known"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    result = ingest_source(
        "https://example.com/paper",
        run_id=run_id,
        source_type="paper",
        content="Findings from a controlled study.",
        paths=tmp_foundry,
    )

    metadata, _ = load_md(result.path)
    assert metadata["trust"]["source_rank"] == "primary"


def test_ingest_source_leaves_rank_unknown_for_unclassifiable_source_type(
    tmp_foundry: FoundryPaths,
) -> None:
    """A source_type the deterministic mapping can't classify stays 'unknown' on
    the written card -- the derivation never silently infers a guess."""

    run_id = "rf_run_source_rank_unknown"
    tmp_foundry.run_paths(run_id).run.mkdir(parents=True, exist_ok=True)

    result = ingest_source(
        "https://example.com/note",
        run_id=run_id,
        source_type="personal_note",
        content="A quick note.",
        paths=tmp_foundry,
    )

    metadata, _ = load_md(result.path)
    assert metadata["trust"]["source_rank"] == "unknown"
