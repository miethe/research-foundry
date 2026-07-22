"""Capture-time ``rights_summary`` emission (rights-entity-model-v1, P4-1).

Covers AC P4-A's two hard requirements:

1. Every newly ingested ``source_card`` and materialized ``source_assertion``
   carries a non-null, schema-valid ``rights_summary`` immediately after the
   creating call returns -- in the SAME call, no separate backfill sweep.
2. If the capture-time rights classifier itself raises, the capture/
   materialization pass still completes and the resulting entity still gets a
   well-formed all-"unknown" ``rights_summary`` -- never a silent absence,
   never a blocked ingest.

See ``services/rights_triage.py`` module docstring for why the emitted
``review_status`` is ``"unknown"`` rather than the PRD/plan's literal
``"agent_triage_only"``: the latter is unimplementable without violating the
``rights_summary`` link-before-assert invariant (P2-1/P2-2), since no
``rights_record`` exists yet at capture time for the mirror to link to.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from research_foundry.frontmatter import load_md
from research_foundry.services import claim_mapping, extraction
from research_foundry.services import rights_triage
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.rights_backfill import all_unknown_rights_summary
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml


def _write_source_file(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def _setup_materialized_run(tmp_foundry, run_id: str, *, content: str) -> None:
    """Ingest + extract + build the claim ledger for one run (P3 pattern)."""

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        "evidence.txt",
        run_id=run_id,
        title="Rights Capture Evidence",
        sensitivity="personal",
        content=content,
        assertion_registry_workspace_id="workspace-rights",
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)


# ---------------------------------------------------------------------------
# source_card: ingest_source() post-condition
# ---------------------------------------------------------------------------


def test_ingest_source_emits_nonnull_rights_summary_in_same_call(tmp_foundry, tmp_path: Path) -> None:
    run_id = "rf_run_p4_rights_ingest"
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    source_file = _write_source_file(tmp_path, "evidence.txt", "The measured result was 42 percent.")

    result = ingest_source(
        str(source_file),
        run_id=run_id,
        title="Rights Ingest",
        sensitivity="personal",
        source_type="other",
        paths=tmp_foundry,
    )

    metadata, _body = load_md(result.path)
    rights_summary = metadata.get("rights_summary")
    assert rights_summary is not None
    assert rights_summary == all_unknown_rights_summary()

    from research_foundry.schemas import SchemaRegistry

    schemas = SchemaRegistry(schemas_dir=tmp_foundry.schemas)
    validation = schemas.validate(metadata, "source_card")
    assert validation.ok, validation.errors


def test_ingest_source_rights_summary_survives_triage_classifier_failure(
    tmp_foundry, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Force the capture-time classifier to raise; capture must still complete
    with a well-formed all-"unknown" rights_summary -- never a blocked ingest,
    never a silent absence.
    """

    def _boom() -> dict[str, Any]:
        raise RuntimeError("simulated capture-time rights classifier failure")

    monkeypatch.setattr(rights_triage, "_classify_capture_rights", _boom)

    run_id = "rf_run_p4_rights_ingest_failure"
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    source_file = _write_source_file(tmp_path, "evidence.txt", "The measured result was 42 percent.")

    result = ingest_source(
        str(source_file),
        run_id=run_id,
        title="Rights Ingest Failure",
        sensitivity="personal",
        source_type="other",
        paths=tmp_foundry,
    )

    assert result.path.is_file()
    metadata, _body = load_md(result.path)
    rights_summary = metadata.get("rights_summary")
    assert rights_summary is not None
    # Fix-cycle 1 (karen review): the degrade is never silent -- a populated
    # rights_triage_failure record accompanies the all-"unknown" mirror. The
    # mirror fields themselves are still byte-identical to the baseline
    # all-unknown block once the failure record is excluded.
    failure = rights_summary.get("rights_triage_failure")
    assert failure is not None
    assert failure["reason"] == "classification_error"
    assert "simulated capture-time rights classifier failure" in failure["detail"]
    assert failure["attempted_at"]
    mirror_only = {k: v for k, v in rights_summary.items() if k != "rights_triage_failure"}
    assert mirror_only == all_unknown_rights_summary()

    from research_foundry.schemas import SchemaRegistry

    schemas = SchemaRegistry(schemas_dir=tmp_foundry.schemas)
    validation = schemas.validate(metadata, "source_card")
    assert validation.ok, validation.errors


# ---------------------------------------------------------------------------
# source_assertion: AssertionMaterializer._prepare_one() post-condition
# ---------------------------------------------------------------------------


def test_materialized_source_assertion_emits_nonnull_rights_summary(tmp_foundry) -> None:
    run_id = "rf_run_p4_rights_assertion"
    _setup_materialized_run(tmp_foundry, run_id, content="The measured result was 42 percent.")

    materializer = AssertionMaterializer(workspace_id="workspace-rights", paths=tmp_foundry)
    result = materializer.materialize_run(run_id)

    assert result.status == "materialized"
    assert len(result.assertion_ids) >= 1
    for assertion_id in result.assertion_ids:
        assertion = load_yaml(materializer._assertion_path(assertion_id))
        rights_summary = assertion.get("rights_summary")
        assert rights_summary is not None
        assert rights_summary == all_unknown_rights_summary()
        assert materializer.schemas.validate(assertion, "source_assertion").ok


def test_materialized_source_assertion_rights_summary_survives_triage_classifier_failure(
    tmp_foundry, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom() -> dict[str, Any]:
        raise RuntimeError("simulated capture-time rights classifier failure")

    monkeypatch.setattr(rights_triage, "_classify_capture_rights", _boom)

    run_id = "rf_run_p4_rights_assertion_failure"
    _setup_materialized_run(tmp_foundry, run_id, content="The measured result was 42 percent.")

    materializer = AssertionMaterializer(workspace_id="workspace-rights", paths=tmp_foundry)
    result = materializer.materialize_run(run_id)

    assert result.status == "materialized"
    assert len(result.assertion_ids) >= 1
    for assertion_id in result.assertion_ids:
        assertion = load_yaml(materializer._assertion_path(assertion_id))
        rights_summary = assertion.get("rights_summary")
        assert rights_summary is not None
        # Fix-cycle 1 (karen review): a populated rights_triage_failure
        # record accompanies the all-"unknown" mirror; the mirror fields
        # themselves stay byte-identical to the baseline once excluded.
        failure = rights_summary.get("rights_triage_failure")
        assert failure is not None
        assert failure["reason"] == "classification_error"
        assert failure["attempted_at"]
        mirror_only = {k: v for k, v in rights_summary.items() if k != "rights_triage_failure"}
        assert mirror_only == all_unknown_rights_summary()


# ---------------------------------------------------------------------------
# P4-4 fix-cycle 1 (karen review): substitutability wired into the real
# capture path -- a blocking triage status (today, every fresh capture, since
# the classifier always emits clearance_status "UNKNOWN") must produce a
# populated `substitutability` field in the SAME capture pass, not merely on
# a follow-up call to the standalone rights_substitutability module.
# ---------------------------------------------------------------------------


def test_ingest_source_blocking_triage_produces_populated_substitutability(
    tmp_foundry, tmp_path: Path
) -> None:
    run_id = "rf_run_p4_substitutability_ingest"
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    source_file = _write_source_file(tmp_path, "evidence.txt", "The measured result was 42 percent.")

    result = ingest_source(
        str(source_file),
        run_id=run_id,
        title="Rights Substitutability Ingest",
        sensitivity="personal",
        source_type="other",
        paths=tmp_foundry,
    )

    metadata, _body = load_md(result.path)
    assert metadata.get("rights_summary", {}).get("clearance_status") == "UNKNOWN"  # blocking today
    substitutability = metadata.get("substitutability")
    assert substitutability is not None
    assert substitutability["status"] in ("no_substitute_found", "substitute_found")
    assert substitutability["searched_at"] is not None
    assert substitutability["coverage_notes"]

    from research_foundry.schemas import SchemaRegistry

    schemas = SchemaRegistry(schemas_dir=tmp_foundry.schemas)
    validation = schemas.validate(metadata, "source_card")
    assert validation.ok, validation.errors


def test_materialized_source_assertion_blocking_triage_produces_populated_substitutability(
    tmp_foundry,
) -> None:
    run_id = "rf_run_p4_substitutability_assertion"
    _setup_materialized_run(tmp_foundry, run_id, content="The measured result was 42 percent.")

    materializer = AssertionMaterializer(workspace_id="workspace-rights", paths=tmp_foundry)
    result = materializer.materialize_run(run_id)

    assert result.status == "materialized"
    assert len(result.assertion_ids) >= 1
    for assertion_id in result.assertion_ids:
        assertion = load_yaml(materializer._assertion_path(assertion_id))
        assert assertion.get("rights_summary", {}).get("clearance_status") == "UNKNOWN"
        substitutability = assertion.get("substitutability")
        assert substitutability is not None
        assert substitutability["status"] in ("no_substitute_found", "substitute_found")
        assert substitutability["searched_at"] is not None
        assert materializer.schemas.validate(assertion, "source_assertion").ok
