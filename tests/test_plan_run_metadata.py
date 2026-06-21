"""Tests for Phase P3 (creation path): plan_run() populates the five new
metadata fields end-to-end when ``backlog_idea_ref`` is provided.

Covers CRE-001 (field population), CRE-002 (CLI validation path unit-tested
via service layer), and CRE-004 (end-to-end smoke test).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from research_foundry.services.backlog_metadata import (
    BacklogMetadata,
    backlog_exists,
    load_backlog_index,
    lookup_metadata,
)
from research_foundry.services.capture import capture_idea, triage_idea
from research_foundry.services.planning import plan_run
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_BACKLOG_DOC = {
    "schema_version": "0.1",
    "type": "research_idea_backlog",
    "title": "Test Backlog",
    "ideas": [
        {
            "ref": "RIB-001",
            "id": "idea_claim-segmentation-source-alignment",
            "title": "Claim segmentation and claim-to-source alignment",
            "pillar": "pillar_evidence-claim-verification",
            "status": "completed",
            "tags": ["claim-verification", "attribution", "entailment"],
            "suggested_project": "Research Foundry",
            "sensitivity": "personal",
            "links": {
                "run_id": "rf_run_20260614_claim_segmentation",
            },
        },
        {
            "ref": "RIB-002",
            "id": "idea_claim-traceability-verification-landscape",
            "title": "Claim traceability and hallucination mitigation",
            "pillar": "pillar_evidence-claim-verification",
            "status": "proposed",
            "tags": ["claim-verification", "hallucination", "rag"],
            "suggested_project": "Research Foundry",
            "sensitivity": "personal",
            "links": {
                "run_id": None,
            },
        },
        {
            # Idea with no suggested_project to cover empty linked_projects.
            "ref": "RIB-003",
            "id": "idea_no-project",
            "title": "Idea with no suggested project",
            "pillar": "pillar_governance-multi-key-safety",
            "status": "proposed",
            "tags": ["governance"],
            "suggested_project": None,
            "sensitivity": "personal",
            "links": {"run_id": None},
        },
    ],
}


@pytest.fixture
def tmp_foundry_with_backlog(tmp_foundry):
    """Extends tmp_foundry with a minimal backlog YAML so derivation works."""
    backlog_dir = tmp_foundry.root / "backlog"
    backlog_dir.mkdir(parents=True, exist_ok=True)
    dump_yaml(_BACKLOG_DOC, backlog_dir / "research_idea_backlog.yaml")
    return tmp_foundry


def _make_intent(text: str, *, tmp_foundry):
    """Capture + triage a test idea, returning intent_id."""
    cap = capture_idea(text, sensitivity="personal", paths=tmp_foundry)
    tri = triage_idea(cap.raw_idea_id, paths=tmp_foundry)
    assert tri.intent_id is not None
    return tri.intent_id


# ---------------------------------------------------------------------------
# BacklogMetadata derivation unit tests
# ---------------------------------------------------------------------------


def test_backlog_index_loads_correctly(tmp_foundry_with_backlog):
    """load_backlog_index returns all ideas keyed by ref."""
    index = load_backlog_index(tmp_foundry_with_backlog)
    assert set(index.keys()) == {"RIB-001", "RIB-002", "RIB-003"}


def test_lookup_metadata_rib001(tmp_foundry_with_backlog):
    """lookup_metadata returns correct fields for RIB-001."""
    meta = lookup_metadata("RIB-001", tmp_foundry_with_backlog)
    assert meta is not None
    assert isinstance(meta, BacklogMetadata)
    assert meta.backlog_idea_ref == "RIB-001"
    assert meta.backlog_idea_id == "idea_claim-segmentation-source-alignment"
    assert meta.category == "pillar_evidence-claim-verification"
    assert set(meta.tags) == {"claim-verification", "attribution", "entailment"}
    assert meta.linked_projects == ["Research Foundry"]


def test_lookup_metadata_no_project(tmp_foundry_with_backlog):
    """linked_projects is empty when suggested_project is null."""
    meta = lookup_metadata("RIB-003", tmp_foundry_with_backlog)
    assert meta is not None
    assert meta.linked_projects == []


def test_lookup_metadata_missing_ref(tmp_foundry_with_backlog):
    """lookup_metadata returns None for unknown refs."""
    assert lookup_metadata("RIB-999", tmp_foundry_with_backlog) is None


def test_backlog_exists_false_when_missing(tmp_foundry):
    """backlog_exists returns False when the file is absent."""
    assert not backlog_exists(tmp_foundry)


def test_backlog_exists_true_when_present(tmp_foundry_with_backlog):
    """backlog_exists returns True after the backlog is seeded."""
    assert backlog_exists(tmp_foundry_with_backlog)


def test_load_backlog_index_empty_when_file_missing(tmp_foundry):
    """load_backlog_index returns {} when there is no backlog file."""
    assert load_backlog_index(tmp_foundry) == {}


# ---------------------------------------------------------------------------
# CRE-001: plan_run() field population with backlog_idea_ref
# ---------------------------------------------------------------------------


def test_plan_run_with_backlog_idea_ref_populates_all_five_fields(
    tmp_foundry_with_backlog, sample_idea_text
):
    """plan_run(backlog_idea_ref='RIB-001') writes all 5 fields to run.yaml."""
    intent_id = _make_intent(sample_idea_text, tmp_foundry=tmp_foundry_with_backlog)
    result = plan_run(
        intent_id, backlog_idea_ref="RIB-001", paths=tmp_foundry_with_backlog
    )

    run_doc = load_yaml(result.run_dir / "run.yaml")

    # All five new metadata fields must be present and correct.
    assert run_doc["linked_projects"] == ["Research Foundry"]
    assert run_doc["category"] == "pillar_evidence-claim-verification"
    assert set(run_doc["tags"]) == {"claim-verification", "attribution", "entailment"}
    assert run_doc["backlog_idea_ref"] == "RIB-001"
    assert run_doc["backlog_idea_id"] == "idea_claim-segmentation-source-alignment"


def test_plan_run_without_backlog_ref_degrades_gracefully(
    tmp_foundry_with_backlog, sample_idea_text
):
    """plan_run() without backlog_idea_ref leaves backlog fields null/absent."""
    intent_id = _make_intent(sample_idea_text, tmp_foundry=tmp_foundry_with_backlog)
    result = plan_run(intent_id, paths=tmp_foundry_with_backlog)

    run_doc = load_yaml(result.run_dir / "run.yaml")

    # Backlog-specific fields are null.
    assert run_doc["backlog_idea_ref"] is None
    assert run_doc["backlog_idea_id"] is None
    assert run_doc["category"] is None
    # linked_projects may be non-empty (derived from effective_project) or null.
    # Key invariant: these keys exist (no KeyError).
    assert "linked_projects" in run_doc
    assert "tags" in run_doc


def test_plan_run_with_project_sets_linked_projects(
    tmp_foundry_with_backlog, sample_idea_text
):
    """Without backlog ref, linked_projects falls back to the resolved project slug."""
    intent_id = _make_intent(sample_idea_text, tmp_foundry=tmp_foundry_with_backlog)
    result = plan_run(
        intent_id, project="my-project", paths=tmp_foundry_with_backlog
    )

    run_doc = load_yaml(result.run_dir / "run.yaml")
    assert run_doc["linked_projects"] == ["my-project"]


def test_plan_run_unassigned_project_has_null_linked_projects(
    tmp_foundry, sample_idea_text
):
    """linked_projects is None when project resolves to 'unassigned'."""
    intent_id = _make_intent(sample_idea_text, tmp_foundry=tmp_foundry)
    result = plan_run(intent_id, paths=tmp_foundry)

    run_doc = load_yaml(result.run_dir / "run.yaml")
    # 'unassigned' produces null linked_projects.
    assert run_doc["linked_projects"] is None


def test_plan_run_metadata_fields_all_keys_present(
    tmp_foundry, sample_idea_text
):
    """All 5 new metadata keys are always present in run.yaml (even when null)."""
    intent_id = _make_intent(sample_idea_text, tmp_foundry=tmp_foundry)
    result = plan_run(intent_id, paths=tmp_foundry)

    run_doc = load_yaml(result.run_dir / "run.yaml")

    for key in ("linked_projects", "category", "tags", "backlog_idea_ref", "backlog_idea_id"):
        assert key in run_doc, f"Expected key '{key}' in run.yaml"


# ---------------------------------------------------------------------------
# CRE-002: capture_idea stores backlog_idea_ref in raw_idea front matter
# ---------------------------------------------------------------------------


def test_capture_idea_stores_backlog_idea_ref(tmp_foundry_with_backlog, sample_idea_text):
    """capture_idea stores backlog_idea_ref in the raw_idea front matter."""
    from research_foundry.frontmatter import load_md

    result = capture_idea(
        sample_idea_text,
        sensitivity="personal",
        backlog_idea_ref="RIB-001",
        paths=tmp_foundry_with_backlog,
    )

    meta, _ = load_md(result.path)
    assert meta["backlog_idea_ref"] == "RIB-001"


def test_capture_idea_without_backlog_ref_has_null(tmp_foundry, sample_idea_text):
    """capture_idea sets backlog_idea_ref=None when not provided."""
    from research_foundry.frontmatter import load_md

    result = capture_idea(
        sample_idea_text,
        sensitivity="personal",
        paths=tmp_foundry,
    )

    meta, _ = load_md(result.path)
    assert meta["backlog_idea_ref"] is None
