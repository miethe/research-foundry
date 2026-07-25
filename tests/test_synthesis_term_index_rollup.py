"""TASK-1.5: report_frontmatter `_term_index` rollup, computed at the same
write time as claim-map's own attach (OQ-E). Additive-only; both a populated
and an absent rollup must pass schema validation.
"""

from __future__ import annotations

import copy

from research_foundry.frontmatter import load_md
from research_foundry.schemas import default_registry, validate
from research_foundry.services import claim_mapping, extraction, source_cards
from research_foundry.services.synthesis import synthesize_report

RUN_ID = "rf_run_20260724_term_index_rollup_test"


def _scaffold(paths):
    paths.run_paths(RUN_ID).ensure_scaffold()


def test_rollup_present_when_a_claim_carries_term_index(tmp_foundry, tmp_path):
    _scaffold(tmp_foundry)
    doc = tmp_path / "notes.txt"
    doc.write_text(
        "Hemoglobin below 11.0 g/dL indicates anemia in this population.\n\n"
        "Ferritin levels help confirm iron deficiency in pediatric patients.\n",
        encoding="utf-8",
    )
    source_cards.ingest_source(str(doc), run_id=RUN_ID, title="Notes", paths=tmp_foundry)
    extraction.extract_run(RUN_ID, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(RUN_ID, paths=tmp_foundry)

    synth = synthesize_report(RUN_ID, paths=tmp_foundry)
    front, _body = load_md(synth.report_path)

    assert "_term_index" in front
    rollup = front["_term_index"]
    assert set(rollup["terms"]) >= {"hemoglobin", "anemia", "ferritin", "iron_deficiency"}
    assert rollup["vocabulary_version"] == "pediatric-terms-v1"
    assert default_registry().has("report_frontmatter")
    assert validate(front, "report_frontmatter").ok


def test_rollup_absent_when_no_claim_has_term_index(tmp_foundry, tmp_path, monkeypatch):
    monkeypatch.setattr(claim_mapping, "load_vocabulary", lambda paths=None: None)

    _scaffold(tmp_foundry)
    doc = tmp_path / "notes.txt"
    doc.write_text("The clinic schedules a routine visit next month.\n", encoding="utf-8")
    source_cards.ingest_source(str(doc), run_id=RUN_ID, title="Notes", paths=tmp_foundry)
    extraction.extract_run(RUN_ID, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(RUN_ID, paths=tmp_foundry)

    synth = synthesize_report(RUN_ID, paths=tmp_foundry)
    front, _body = load_md(synth.report_path)

    assert "_term_index" not in front
    assert validate(front, "report_frontmatter").ok


def test_rollup_helper_is_pure_and_deterministic():
    from research_foundry.services.term_index import report_term_index_rollup

    claims = [
        {"_term_index": {"terms": ["cbc"], "usage_roles": {"cbc": "background"}, "vocabulary_version": "v1"}},
    ]
    first = report_term_index_rollup(copy.deepcopy(claims))
    second = report_term_index_rollup(copy.deepcopy(claims))
    assert first == second
