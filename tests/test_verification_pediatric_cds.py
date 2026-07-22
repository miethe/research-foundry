"""Unit tests for the ``pediatric_cds_schema_invalid`` hard-gate (RFUP-1 P2-002).

P2-001 authored ``schemas/pediatric_cds.schema.json`` (structural-completeness
only, per its own seam-boundary comment). This module tests P2-002's wiring of
that schema into ``verify_report``: AC-P2-4 (absence is not a violation),
AC-P2-5 (fail-closed schema-config errors vs. fail+unsupported[] block-content
errors), AC-P2-6 (zero new I/O — reuses the run's already-loaded source cards),
and AC-P2-7 (a distinguishable reason code).

The red-team fixture set (>=5 malformed cases) and the 7-verified-bundle
zero-false-positive regression are P2-003's job, not this task's — these tests
cover the check's own correctness, including a real YAML round-trip hazard
(plain ISO date scalars parsing back as ``datetime.date``, not ``str``) that
would otherwise produce false-positive schema failures.
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pytest

import test_claim_verifier as _tcv  # noqa: E402 - reuse the happy-path fixture
from research_foundry.errors import ExitCode, RFError
from research_foundry.frontmatter import dump_md, load_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import verification as verification_module
from research_foundry.services.synthesis import synthesize_report
from research_foundry.services.verification import verify_report

_TARGET_SOURCE_ID = "src_20260613_paperqa2_aaaaaaaa"


def _valid_pediatric_cds_block() -> dict:
    """A pediatric_cds block satisfying every required field on every one of
    the schema's 9 top-level sections (schemas/pediatric_cds.schema.json)."""

    return {
        "schema_version": "1.0",
        "module_id": "cbc_suite_v1",
        "evidence_role": "threshold",
        "source_status": {
            "update_checked_at": "2026-07-01",
            "correction_checked": True,
            "retraction_checked": True,
            "withdrawal_checked": True,
            "supersession_checked": True,
            "superseded_by": None,
            "foundational_exception_reason": None,
        },
        "study": {
            "design": "retrospective_cohort",
            "population": "pediatric",
            "setting": "outpatient",
            "sample_size": 512,
            "inclusion": ["age < 18"],
            "exclusion": ["known hemoglobinopathy"],
            "comparator": None,
            "outcome": "anemia detection",
            "evidence_grade": "B",
        },
        "applicability": {
            "age_min_months": 6,
            "age_max_months_exclusive": 216,
            "sex_or_physiology": "any",
            "gestational": "term",
            "ancestry_or_population": "general",
            "comorbidities": [],
            "jurisdictions": ["US"],
        },
        "laboratory": {
            "test": "CBC",
            "specimen": "whole_blood",
            "method": "automated_hematology_analyzer",
            "analyzer": "Sysmex XN-1000",
            "unit": "g/dL",
            "ucum": "g/dL",
            "reference_interval": "11.0-14.0",
            "timing": "any",
            "preanalytic_requirements": [],
        },
        "implementable_statement": {
            "kind": "threshold",
            "value_or_formula": 11.0,
            "portability": "local_lab_dependent",
            "assertion_kind": "implementation_proposed",
            "exact_passage_required": True,
        },
        "diagnostic_accuracy": {
            "sensitivity": 0.85,
            "specificity": 0.9,
            "likelihood_ratio_positive": 8.5,
            "likelihood_ratio_negative": 0.17,
            "predictive_value_positive": None,
            "predictive_value_negative": None,
            "confidence_interval": "0.80-0.90",
            "prevalence": None,
        },
        "safety": {
            "contraindications": [],
            "confounders": ["iron deficiency"],
            "false_positive_contexts": [],
            "false_negative_contexts": [],
            "dangerous_exceptions": [],
        },
        "conflict": {
            "conflicts_with_claim_ids": [],
            "conflict_summary": None,
            "safe_representation": "no_conflict",
        },
        "lifecycle": {
            "review_by": "2028-07-01",
            "surveillance_query": "pediatric anemia CBC threshold",
            "owner_role": "clinical_lead",
        },
    }


def _inject_pediatric_cds(paths: FoundryPaths, source_card_id: str, block: dict | None) -> None:
    """Rewrite an already-seeded source card's extracted_points[0] to carry
    (or, when *block* is None, omit) a pediatric_cds sub-block."""

    rp = paths.run_paths(_tcv.RUN_ID)
    path = rp.sources / f"{source_card_id}.md"
    front, body = load_md(path)
    point = {
        "evidence_id": "ev_001",
        "locator": "p.3",
        "summary": "Threshold value",
        "quote": "Hemoglobin below 11.0 g/dL indicates anemia in this population.",
    }
    if block is not None:
        point["pediatric_cds"] = block
    front["extracted_points"] = [point]
    dump_md(front, body, path)


@pytest.fixture(autouse=True)
def _clear_pediatric_cds_schema_cache():
    """Isolate the module-level lru_cache across tests that monkeypatch the
    schema path — a poisoned cache entry from one test must never leak into
    the next."""

    verification_module._load_pediatric_cds_schema.cache_clear()
    yield
    verification_module._load_pediatric_cds_schema.cache_clear()


def _seed_and_synthesize(paths: FoundryPaths) -> None:
    _tcv._seed_happy_run(paths)
    synthesize_report(_tcv.RUN_ID, paths=paths)


# --- AC-P2-4: absence is not a violation ------------------------------------


def test_pediatric_cds_block_absent_is_not_a_violation(tmp_foundry):
    _seed_and_synthesize(tmp_foundry)

    result = verify_report(_tcv.RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}

    assert by_id["pediatric_cds_schema_invalid"].status == "pass"
    assert result.passed is True
    assert result.exit_code == int(ExitCode.OK)
    assert not any("pediatric_cds" in u for u in result.unsupported)


# --- Valid block, including the YAML-date round-trip hazard -----------------


def test_valid_pediatric_cds_block_passes_despite_yaml_date_coercion(tmp_foundry):
    """A well-formed block — where a date field arrives as a native
    ``datetime.date`` object (as it would from a YAML-authored extraction
    pipeline, not a quoted string) — must not produce a false-positive schema
    failure once it round-trips through ``dump_md``/``load_md``.

    ``research_foundry.yamlio``'s dumper only force-quotes values that are
    already Python ``str`` (its custom string representer); a genuine
    ``datetime.date`` object dumps as an *unquoted* plain scalar and reloads
    via ``yaml.safe_load`` as a ``datetime.date`` again — exactly the type
    mismatch ``_json_safe`` exists to normalize before jsonschema sees it
    (the schema declares these fields as JSON Schema ``"type": "string"``).
    """

    _seed_and_synthesize(tmp_foundry)
    block = _valid_pediatric_cds_block()
    block["source_status"]["update_checked_at"] = datetime.date(2026, 7, 1)
    block["lifecycle"]["review_by"] = datetime.date(2028, 7, 1)
    _inject_pediatric_cds(tmp_foundry, _TARGET_SOURCE_ID, block)

    # Confirm the round-trip hazard is real before asserting the fix works.
    rp = tmp_foundry.run_paths(_tcv.RUN_ID)
    reloaded, _ = load_md(rp.sources / f"{_TARGET_SOURCE_ID}.md")
    coerced = reloaded["extracted_points"][0]["pediatric_cds"]["source_status"]["update_checked_at"]
    assert isinstance(coerced, datetime.date)

    result = verify_report(_tcv.RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}

    assert by_id["pediatric_cds_schema_invalid"].status == "pass", by_id["pediatric_cds_schema_invalid"]
    assert result.passed is True
    assert result.exit_code == int(ExitCode.OK)


# --- AC-P2-5/AC-P2-7: invalid block fails closed with a distinguishable code -


def test_invalid_pediatric_cds_block_missing_required_field_fails_closed(tmp_foundry):
    _seed_and_synthesize(tmp_foundry)

    block = _valid_pediatric_cds_block()
    del block["lifecycle"]["review_by"]  # nested required-field violation
    _inject_pediatric_cds(tmp_foundry, _TARGET_SOURCE_ID, block)

    result = verify_report(_tcv.RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}

    check = by_id["pediatric_cds_schema_invalid"]
    assert check.status == "fail"
    assert "review_by" in check.detail
    assert any(_TARGET_SOURCE_ID in loc for loc in check.locations)
    assert any("pediatric_cds_schema_invalid" in u for u in result.unsupported)
    assert result.passed is False
    assert result.exit_code == int(ExitCode.UNSUPPORTED)


def test_invalid_pediatric_cds_block_wrong_type_fails_closed(tmp_foundry):
    """A required field of the wrong JSON type is also caught, not just an
    outright-missing field."""

    _seed_and_synthesize(tmp_foundry)

    block = _valid_pediatric_cds_block()
    block["safety"]["contraindications"] = "not-an-array"
    _inject_pediatric_cds(tmp_foundry, _TARGET_SOURCE_ID, block)

    result = verify_report(_tcv.RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}

    assert by_id["pediatric_cds_schema_invalid"].status == "fail"
    assert result.exit_code == int(ExitCode.UNSUPPORTED)


def test_invalid_pediatric_cds_block_missing_top_level_section_fails_closed(tmp_foundry):
    """A block missing an entire required top-level section (not just a
    nested field) is caught the same way."""

    _seed_and_synthesize(tmp_foundry)

    block = _valid_pediatric_cds_block()
    del block["conflict"]
    _inject_pediatric_cds(tmp_foundry, _TARGET_SOURCE_ID, block)

    result = verify_report(_tcv.RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}

    assert by_id["pediatric_cds_schema_invalid"].status == "fail"
    assert "conflict" in by_id["pediatric_cds_schema_invalid"].detail


# --- AC-P2-5: schema *config* errors raise RFError, distinct from content ---


def test_broken_schema_file_raises_rferror(monkeypatch):
    """A missing/unreadable schema artifact is a config problem — it fails
    closed via RFError rather than silently disabling the hard-gate."""

    monkeypatch.setattr(
        verification_module,
        "_PEDIATRIC_CDS_SCHEMA_PATH",
        Path("/nonexistent/pediatric_cds.schema.json"),
    )

    with pytest.raises(RFError):
        verification_module._load_pediatric_cds_schema()


def test_broken_schema_file_raises_rferror_from_verify_report(tmp_foundry, monkeypatch):
    """The RFError propagates out of verify_report itself, even for a run
    with zero pediatric_cds blocks — confirming the schema is resolved
    unconditionally (fail-closed), not lazily only when a block is found."""

    _seed_and_synthesize(tmp_foundry)
    monkeypatch.setattr(
        verification_module,
        "_PEDIATRIC_CDS_SCHEMA_PATH",
        Path("/nonexistent/pediatric_cds.schema.json"),
    )

    with pytest.raises(RFError):
        verify_report(_tcv.RUN_ID, paths=tmp_foundry)


def test_invalid_schema_json_raises_rferror(tmp_path, monkeypatch):
    bad_schema = tmp_path / "pediatric_cds.schema.json"
    bad_schema.write_text("{not valid json", encoding="utf-8")
    monkeypatch.setattr(verification_module, "_PEDIATRIC_CDS_SCHEMA_PATH", bad_schema)

    with pytest.raises(RFError):
        verification_module._load_pediatric_cds_schema()
