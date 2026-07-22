"""Tests for the legacy ``rights_summary`` backfill (rights-entity-model-v1, P2-5).

Covers the four required scenarios from
``docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-0-2-schema.md``
(P2-5 row):

1. Backfill on a legacy instance (no ``rights_summary`` key at all) produces
   the exact all-``"unknown"`` block, and the instance now validates against
   the schema.
2. Backfill is idempotent — running it twice doesn't change an
   already-summary-bearing instance.
3. Backfill on an instance that already has a partial/non-unknown
   ``rights_summary`` does NOT overwrite it.
4. Post-backfill, ``check_rights_divergence`` on the backfilled instance
   reports ``needs_backfill=False`` and no divergence failure (the exit-gate
   proof at unit-test granularity).
"""

from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

from research_foundry.assertion_identity import (
    SOURCE_ASSERTION_MATERIAL_FIELDS,
    source_assertion_fingerprint,
    source_assertion_id,
)
from research_foundry.frontmatter import dump_md, load_md
from research_foundry.schemas import validate
from research_foundry.services.rights_backfill import (
    ACTION_BACKFILLED,
    ACTION_SKIPPED_PRESENT,
    all_unknown_rights_summary,
    backfill_rights_summary,
)
from research_foundry.services.rights_validation import check_rights_divergence
from research_foundry.yamlio import dump_yaml, load_yaml

# --- fixture builders -------------------------------------------------------


def _write_legacy_source_card(tmp_path: Path, card_id: str) -> Path:
    """A source_card with no ``rights_summary`` key at all (pre-migration)."""

    metadata: dict[str, Any] = {
        "source_card_id": card_id,
        "type": "source_card",
        "source": {"title": "Legacy Source"},
    }
    path = tmp_path / f"{card_id}.md"
    dump_md(metadata, "# Legacy Source\n", path)
    return path


def _source_assertion_instance(assertion_id_suffix: str) -> dict[str, Any]:
    """A fully-populated, schema-valid source_assertion instance (no rights_summary)."""

    text = f"The lab reported a hemoglobin of 9.2 g/dL for cohort {assertion_id_suffix}."
    instance: dict[str, Any] = {
        "schema_version": "1.0",
        "type": "source_assertion",
        "assertion_version": 1,
        "source_edition_id": "sed_" + "e" * 64,
        "passage_id": "psg_" + "f" * 64,
        "assertion_text": text,
        "assertion_text_sha256": sha256(text.encode("utf-8")).hexdigest(),
        "qualifiers": {"population": "pediatric"},
        "qualifier_extensions": {},
        "extraction_provenance": {
            "extractor": "rights_backfill_fixture",
            "schema_version": "1.0",
            "observed_at": "2026-07-21T00:00:00Z",
        },
        "lifecycle_state": "eligible",
        "identity": {
            "algorithm": "sha256-canonical-json-v1",
            "fingerprint": "",
            "material_fields": list(SOURCE_ASSERTION_MATERIAL_FIELDS),
        },
        "extensions": {
            "evidence_taxonomy": {
                "evidence_item_type": "observed_finding",
                "judgment_basis": "measured",
            },
        },
    }
    instance["identity"]["fingerprint"] = source_assertion_fingerprint(instance)
    instance["assertion_id"] = source_assertion_id(instance)
    return instance


def _write_legacy_source_assertion(tmp_path: Path, suffix: str) -> Path:
    instance = _source_assertion_instance(suffix)
    path = tmp_path / f"ast_legacy_{suffix}.yaml"
    dump_yaml(instance, path)
    return path


# --- Scenario 1: legacy instance backfills to the exact all-unknown block --


def test_backfill_legacy_source_card_produces_exact_block_and_validates(tmp_path: Path) -> None:
    path = _write_legacy_source_card(tmp_path, "src_backfill_001")

    results = backfill_rights_summary([path])

    assert len(results) == 1
    assert results[0].action == ACTION_BACKFILLED
    assert results[0].instance_id == "src_backfill_001"

    metadata, _body = load_md(path)
    assert metadata["rights_summary"] == all_unknown_rights_summary()

    result = validate(metadata, "source_card")
    assert result.ok, f"expected backfilled source_card to validate, got: {result.errors}"


def test_backfill_legacy_source_assertion_produces_exact_block_and_validates(tmp_path: Path) -> None:
    path = _write_legacy_source_assertion(tmp_path, "002")

    results = backfill_rights_summary([path])

    assert results[0].action == ACTION_BACKFILLED
    metadata = load_yaml(path)
    assert metadata["rights_summary"] == all_unknown_rights_summary()

    result = validate(metadata, "source_assertion")
    assert result.ok, f"expected backfilled source_assertion to validate, got: {result.errors}"


# --- Scenario 2: idempotent — re-running on an already-backfilled instance -


def test_backfill_is_idempotent_on_already_backfilled_instance(tmp_path: Path) -> None:
    path = _write_legacy_source_card(tmp_path, "src_backfill_003")

    first = backfill_rights_summary([path])
    assert first[0].action == ACTION_BACKFILLED
    metadata_after_first, _ = load_md(path)

    second = backfill_rights_summary([path])
    assert second[0].action == ACTION_SKIPPED_PRESENT
    metadata_after_second, _ = load_md(path)

    assert metadata_after_first == metadata_after_second


# --- Scenario 3: an instance with a partial/real rights_summary is untouched


def test_backfill_does_not_overwrite_existing_partial_rights_summary(tmp_path: Path) -> None:
    real_summary: dict[str, Any] = {
        "mirror_of_record_id": None,
        "mirror_derived_at": None,
        "mirror_is_authoritative": False,
        "rights_record_ids": ["rr_real_001"],
        "reuse_assessment_ids": [],
        "permission_record_ids": [],
        "copyright_status": "copyrighted",
        "access_basis": "institutional_subscription",
        "restrictions": {
            "incorporation_into_other_products": "prohibited",
            "adaptation": "unknown",
            "commercial_use": "unknown",
            "redistribution": "unknown",
            "bulk_retrieval": "unknown",
            "model_training": "unknown",
        },
        "clearance_status": "UNKNOWN",
        "review_status": "unknown",
    }
    metadata: dict[str, Any] = {
        "source_card_id": "src_backfill_004",
        "type": "source_card",
        "source": {"title": "Real Rights Source"},
        "rights_summary": real_summary,
    }
    path = tmp_path / "src_backfill_004.md"
    dump_md(metadata, "# Real Rights Source\n", path)

    results = backfill_rights_summary([path])

    assert results[0].action == ACTION_SKIPPED_PRESENT
    reloaded, _ = load_md(path)
    assert reloaded["rights_summary"] == real_summary  # untouched, not clobbered


# --- dry-run does not write ---------------------------------------------


def test_backfill_dry_run_reports_without_writing(tmp_path: Path) -> None:
    path = _write_legacy_source_card(tmp_path, "src_backfill_005")

    results = backfill_rights_summary([path], dry_run=True)

    assert results[0].action == ACTION_BACKFILLED
    assert results[0].dry_run is True

    metadata, _ = load_md(path)
    assert "rights_summary" not in metadata  # nothing written


# --- Scenario 4: needs_backfill -> resolved (exit-gate proof) ---------------


def test_backfill_resolves_needs_backfill_and_no_divergence(tmp_path: Path) -> None:
    card_path = _write_legacy_source_card(tmp_path, "src_backfill_006")
    assertion_path = _write_legacy_source_assertion(tmp_path, "007")

    # Before: both need backfill.
    before = check_rights_divergence([card_path, assertion_path], as_of=date(2026, 7, 21))
    assert all(r.needs_backfill for r in before)
    assert all(r.ok for r in before)  # non-fatal even before

    backfill_rights_summary([card_path, assertion_path])

    after = check_rights_divergence([card_path, assertion_path], as_of=date(2026, 7, 21))
    for result in after:
        assert result.needs_backfill is False
        assert result.ok is True
        assert result.findings == ()
