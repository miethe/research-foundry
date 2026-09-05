"""Regression tests for Campaign K M4a / gap-table row G1.

``build_claim_ledger`` (services/claim_mapping.py) used to stamp every claim's
``confidence`` with a bare passthrough default of the literal string
``"medium"`` -- it computed nothing. This is a MISSING computation being
added, not a broken one being repaired: no prior confidence value existed to
have regressed, so there is no positive control for this change and none is
claimed here.

These tests cover both cases the acceptance criteria name: a single-source
claim (no other card agrees) and a multi-source-agreement claim (an
independent second source card produced matching text), plus the ambiguous
(extraction-flagged) case the rubric also uses.
"""

from __future__ import annotations

from research_foundry.services import claim_mapping, extraction, source_cards
from research_foundry.yamlio import load_yaml

RUN_ID = "rf_run_20260905_claim_confidence_test"


def _scaffold(paths):
    paths.run_paths(RUN_ID).ensure_scaffold()


# --- unit tests: the pure rubric function, no pipeline needed -------------


def test_confidence_rubric_single_source_not_ambiguous_is_medium():
    assert (
        claim_mapping._compute_claim_confidence(agreement_count=0, ambiguous=False)
        == "medium"
    )


def test_confidence_rubric_multi_source_agreement_is_high():
    assert (
        claim_mapping._compute_claim_confidence(agreement_count=1, ambiguous=False)
        == "high"
    )
    assert (
        claim_mapping._compute_claim_confidence(agreement_count=3, ambiguous=False)
        == "high"
    )


def test_confidence_rubric_ambiguous_is_always_low():
    # Ambiguous overrides agreement in both directions -- a degraded fact
    # must never outrank a genuinely single-sourced, actually-read one.
    assert claim_mapping._compute_claim_confidence(agreement_count=0, ambiguous=True) == "low"
    assert claim_mapping._compute_claim_confidence(agreement_count=5, ambiguous=True) == "low"


def test_confidence_rubric_is_not_a_constant():
    """The defect this fixes: a bare `or "medium"` default never varies.
    Assert the rubric actually produces more than one value across the
    covered input space."""

    values = {
        claim_mapping._compute_claim_confidence(agreement_count=0, ambiguous=False),
        claim_mapping._compute_claim_confidence(agreement_count=1, ambiguous=False),
        claim_mapping._compute_claim_confidence(agreement_count=0, ambiguous=True),
    }
    assert values == {"medium", "high", "low"}


def test_extraction_flagged_ambiguous_detects_needs_content_note():
    assert claim_mapping._extraction_step_flagged_ambiguous({"notes": "flagged needs_content"})
    assert not claim_mapping._extraction_step_flagged_ambiguous({"notes": ""})
    assert not claim_mapping._extraction_step_flagged_ambiguous({})


def test_normalize_claim_text_folds_case_and_whitespace():
    assert claim_mapping._normalize_claim_text("  Foo   Bar\n") == "foo bar"
    assert claim_mapping._normalize_claim_text("Foo Bar") == claim_mapping._normalize_claim_text(
        "  foo   bar  "
    )


# --- integration tests: through the real ingest -> extract -> claim-map ---


def test_single_source_claim_is_medium_confidence(tmp_foundry, tmp_path):
    _scaffold(tmp_foundry)
    source_cards.ingest_source(
        "note.txt",
        run_id=RUN_ID,
        title="Solo note",
        content="Aspirin reduces the risk of recurrent stroke in this cohort.",
        paths=tmp_foundry,
    )
    extraction.extract_run(RUN_ID, paths=tmp_foundry)
    result = claim_mapping.build_claim_ledger(RUN_ID, paths=tmp_foundry)
    ledger = load_yaml(result.ledger_path)

    claims = [
        c
        for c in ledger["claims"]
        if c["text"] == "Aspirin reduces the risk of recurrent stroke in this cohort."
    ]
    assert len(claims) == 1
    assert claims[0]["confidence"] == "medium"


def test_cross_source_agreement_claim_is_high_confidence(tmp_foundry, tmp_path):
    _scaffold(tmp_foundry)
    shared_text = "Metformin lowers HbA1c by roughly 1 point over 6 months."
    source_cards.ingest_source(
        "note-a.txt",
        run_id=RUN_ID,
        title="Note A",
        content=shared_text,
        paths=tmp_foundry,
    )
    source_cards.ingest_source(
        "note-b.txt",
        run_id=RUN_ID,
        title="Note B",
        content=shared_text,
        paths=tmp_foundry,
    )
    extraction.extract_run(RUN_ID, paths=tmp_foundry)
    result = claim_mapping.build_claim_ledger(RUN_ID, paths=tmp_foundry)
    ledger = load_yaml(result.ledger_path)

    matching = [c for c in ledger["claims"] if c["text"] == shared_text]
    # Two independent source cards each produced the identical fact text.
    assert len(matching) == 2
    distinct_source_cards = {c["sources"][0]["source_card_id"] for c in matching}
    assert len(distinct_source_cards) == 2
    for claim in matching:
        assert claim["confidence"] == "high"


def test_degraded_content_claim_is_low_confidence(tmp_foundry, tmp_path):
    _scaffold(tmp_foundry)
    # content="" forces source_cards.ingest_source's degraded/locator-only
    # path, which extraction.py stamps `notes="flagged needs_content"` on --
    # the one deterministic ambiguity signal this rubric consumes.
    source_cards.ingest_source(
        "unreachable.txt",
        run_id=RUN_ID,
        title="Unreachable",
        content="",
        paths=tmp_foundry,
    )
    extraction.extract_run(RUN_ID, paths=tmp_foundry)
    result = claim_mapping.build_claim_ledger(RUN_ID, paths=tmp_foundry)
    ledger = load_yaml(result.ledger_path)

    assert len(ledger["claims"]) == 1
    assert ledger["claims"][0]["confidence"] == "low"


def test_ledger_schema_still_validates(tmp_foundry, tmp_path):
    """Confidence values stay inside the existing low/medium/high enum --
    the rubric was deliberately kept to 3 levels rather than widened, since
    catalog_service._CONFIDENCE_RANK only ranks those three (see
    _compute_claim_confidence's docstring)."""

    from research_foundry.schemas import SchemaRegistry

    _scaffold(tmp_foundry)
    source_cards.ingest_source(
        "note.txt",
        run_id=RUN_ID,
        title="Solo note",
        content="Aspirin reduces the risk of recurrent stroke in this cohort.",
        paths=tmp_foundry,
    )
    extraction.extract_run(RUN_ID, paths=tmp_foundry)
    result = claim_mapping.build_claim_ledger(RUN_ID, paths=tmp_foundry)
    ledger = load_yaml(result.ledger_path)

    registry = SchemaRegistry(schemas_dir=tmp_foundry.schemas)
    validation = registry.validate(ledger, "claim_ledger")
    assert validation.ok, validation.errors
