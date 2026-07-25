"""Integration tests for TASK-1.4: `_term_index` attach in
`claim_mapping.build_claim_ledger`, exercised through the real
ingest -> extract -> claim-map pipeline (mirrors
test_pipeline_ingest_extract_claims.py) so claim text and evidence_ids are
produced exactly as they would be in a live run.
"""

from __future__ import annotations

import re

from research_foundry.frontmatter import dump_md, load_md
from research_foundry.schemas import SchemaRegistry
from research_foundry.services import claim_mapping, extraction, source_cards
from research_foundry.yamlio import load_yaml

RUN_ID = "rf_run_20260724_term_index_test"


def _scaffold(paths):
    paths.run_paths(RUN_ID).ensure_scaffold()


def _registry(paths):
    return SchemaRegistry(schemas_dir=paths.schemas)


def test_populated_claims_carry_term_index(tmp_foundry, tmp_path):
    _scaffold(tmp_foundry)
    doc = tmp_path / "notes.txt"
    doc.write_text(
        "Hemoglobin below 11.0 g/dL indicates anemia in this population.\n\n"
        "The clinic schedules a routine visit next month.\n",
        encoding="utf-8",
    )
    src = source_cards.ingest_source(str(doc), run_id=RUN_ID, title="Notes", paths=tmp_foundry)
    extraction.extract_run(RUN_ID, paths=tmp_foundry)

    result = claim_mapping.build_claim_ledger(RUN_ID, paths=tmp_foundry)
    ledger = load_yaml(result.ledger_path)

    registry = _registry(tmp_foundry)
    validation = registry.validate(ledger, "claim_ledger")
    assert validation.ok, validation.errors

    by_text = {c["text"]: c for c in ledger["claims"]}
    hemoglobin_claim = by_text["Hemoglobin below 11.0 g/dL indicates anemia in this population."]
    assert hemoglobin_claim["_term_index"]["vocabulary_version"] == "pediatric-terms-v1"
    assert set(hemoglobin_claim["_term_index"]["terms"]) >= {"hemoglobin", "anemia"}
    assert hemoglobin_claim["_term_index"]["usage_roles"]["hemoglobin"] == "threshold"

    # A claim with zero vocabulary hits still passes schema validation with
    # an absent _term_index (AC-1 resilience) -- never an empty-but-present
    # block, never an error.
    background_claim = by_text["The clinic schedules a routine visit next month."]
    assert "_term_index" not in background_claim

    # Every claim in this freshly-built ledger that hit the vocabulary carries
    # a vocabulary_version stamp (success metric).
    for claim in ledger["claims"]:
        if "_term_index" in claim:
            assert claim["_term_index"]["vocabulary_version"] == "pediatric-terms-v1"

    del src  # only used to trigger ingestion; not asserted on directly


def test_no_bare_usage_role_key_anywhere(tmp_foundry, tmp_path):
    _scaffold(tmp_foundry)
    doc = tmp_path / "notes.txt"
    doc.write_text(
        "Hemoglobin below 11.0 g/dL indicates anemia in this population.\n\n"
        "Ferritin levels help confirm iron deficiency in pediatric patients.\n",
        encoding="utf-8",
    )
    source_cards.ingest_source(str(doc), run_id=RUN_ID, title="Notes", paths=tmp_foundry)
    extraction.extract_run(RUN_ID, paths=tmp_foundry)
    result = claim_mapping.build_claim_ledger(RUN_ID, paths=tmp_foundry)

    raw = result.ledger_path.read_text(encoding="utf-8")
    # A bare top-level `usage_role:` key must never appear -- only nested
    # under `_term_index.usage_roles`.
    assert not re.search(r"^\s*usage_role:", raw, re.MULTILINE)
    assert "usage_roles:" in raw


def test_missing_vocabulary_file_omits_term_index_without_error(tmp_foundry, tmp_path, monkeypatch):
    monkeypatch.setattr(claim_mapping, "load_vocabulary", lambda paths=None: None)

    _scaffold(tmp_foundry)
    doc = tmp_path / "notes.txt"
    doc.write_text(
        "Hemoglobin below 11.0 g/dL indicates anemia in this population.\n",
        encoding="utf-8",
    )
    source_cards.ingest_source(str(doc), run_id=RUN_ID, title="Notes", paths=tmp_foundry)
    extraction.extract_run(RUN_ID, paths=tmp_foundry)

    result = claim_mapping.build_claim_ledger(RUN_ID, paths=tmp_foundry)
    ledger = load_yaml(result.ledger_path)

    registry = _registry(tmp_foundry)
    assert registry.validate(ledger, "claim_ledger").ok
    for claim in ledger["claims"]:
        assert "_term_index" not in claim


def test_pediatric_cds_threshold_block_classifies_directly_from_structured_field(
    tmp_foundry, tmp_path
):
    """A term with zero numeric/comparative context in its own claim text
    still classifies `threshold` when its cited evidence point carries a
    pediatric_cds legacy threshold{value, units_ucum} block (TASK-1.3b) --
    the structured field, not regex, drives the classification -- but only
    for the term the block's own `threshold.passage_locator` text actually
    names. `cbc` also appears in this claim's text but is not named by the
    locator ("p.1: 'Hemoglobin level was assessed...'"), so it must NOT
    inherit `threshold` from this signal (defect-1b: a structured field must
    key to the term it references, not blanket-promote every term the claim
    happens to mention)."""

    _scaffold(tmp_foundry)
    doc = tmp_path / "notes.txt"
    doc.write_text(
        "Hemoglobin level was assessed as part of the CBC panel.\n",
        encoding="utf-8",
    )
    src = source_cards.ingest_source(str(doc), run_id=RUN_ID, title="Notes", paths=tmp_foundry)

    # Inject a pediatric_cds legacy threshold block onto the point this
    # paragraph produced (mirrors the pattern used by
    # tests/test_verification_pediatric_cds.py's _inject_pediatric_cds).
    rp = tmp_foundry.run_paths(RUN_ID)
    card_path = rp.sources / f"{src.source_card_id}.md"
    front, body = load_md(card_path)
    points = front["extracted_points"]
    assert points, "ingest must have produced >=1 extracted point"
    points[0]["pediatric_cds"] = {
        "population": "6-59 months",
        "assay_method": "automated_hematology_analyzer",
        "threshold": {
            "value": 11.0,
            "units_ucum": "g/dL",
            "passage_locator": "p.1: 'Hemoglobin level was assessed...'",
        },
        "lifecycle": {
            "effective": "2026-01-01",
            "retire": None,
            "guideline_version": "v1",
            "supersedes": None,
        },
        "classification": "source_supported_fact",
    }
    dump_md(front, body, card_path)

    extraction.extract_run(RUN_ID, paths=tmp_foundry)
    result = claim_mapping.build_claim_ledger(RUN_ID, paths=tmp_foundry)
    ledger = load_yaml(result.ledger_path)

    claim = next(
        c for c in ledger["claims"] if c["text"] == "Hemoglobin level was assessed as part of the CBC panel."
    )
    idx = claim["_term_index"]
    assert set(idx["terms"]) >= {"hemoglobin", "cbc"}
    # hemoglobin is named by the structured field's own passage_locator text
    # ("... 'Hemoglobin level was assessed...'"), so it inherits "threshold"
    # directly from that field even though the claim text itself has no
    # comparator/digit. cbc is NOT named by that locator text and the claim
    # text has no comparator/digit either, so it falls back to the (now
    # windowed) regex path and stays "background" -- it must not inherit
    # "threshold" just because it shares a claim with a term that was named.
    assert idx["usage_roles"]["hemoglobin"] == "threshold"
    assert idx["usage_roles"]["cbc"] == "background"
