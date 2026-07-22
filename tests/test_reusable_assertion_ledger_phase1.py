"""P1 canonical-contract regression coverage for the Reusable Assertion Ledger."""

from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from typing import Any

from research_foundry.assertion_identity import (
    SOURCE_ASSERTION_MATERIAL_FIELDS,
    canonical_source_assertion_json,
    source_assertion_fingerprint,
    source_assertion_id,
)
from research_foundry.schemas import validate
from research_foundry.services import export_service


def _hash(char: str) -> str:
    return char * 64


def _source_assertion() -> dict[str, Any]:
    assertion: dict[str, Any] = {
        "schema_version": "1.0",
        "type": "source_assertion",
        "assertion_version": 2,
        "source_edition_id": f"sed_{_hash('b')}",
        "passage_id": f"psg_{_hash('c')}",
        "assertion_text": "The source states the measured result.",
        "assertion_text_sha256": sha256(
            b"The source states the measured result."
        ).hexdigest(),
        "qualifiers": {"population": "adults", "timeframe": "2026-Q1"},
        "qualifier_extensions": {"dose_form": "daily", "study_arm": "control"},
        "extraction_provenance": {
            "extractor": "phase1_fixture",
            "schema_version": "1.0",
            "observed_at": "2026-07-13T12:00:00Z",
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
            }
        },
        # rights-entity-model-v1 P2-2: `rights_summary` (byte-identical
        # denormalized mirror shape to source_card.schema.yaml's P2-1
        # field) — non-material, all-"unknown" default so this canonical
        # P1 identity/lifecycle fixture reflects the current schema shape
        # without asserting any rights posture.
        "rights_summary": {
            "mirror_of_record_id": None,
            "mirror_derived_at": None,
            "mirror_is_authoritative": False,
            "rights_record_ids": [],
            "reuse_assessment_ids": [],
            "permission_record_ids": [],
            "copyright_status": "unknown",
            "access_basis": "unknown",
            "restrictions": {
                "incorporation_into_other_products": "unknown",
                "adaptation": "unknown",
                "commercial_use": "unknown",
                "redistribution": "unknown",
                "bulk_retrieval": "unknown",
                "model_training": "unknown",
            },
            "clearance_status": "UNKNOWN",
            "review_status": "unknown",
        },
    }
    assertion["identity"]["fingerprint"] = source_assertion_fingerprint(assertion)
    assertion["assertion_id"] = source_assertion_id(assertion)
    return assertion


def test_p1_source_assertion_preserves_qualifier_extensions() -> None:
    assertion = _source_assertion()
    assert validate(assertion, "source_assertion").ok
    assert assertion["qualifier_extensions"] == {"dose_form": "daily", "study_arm": "control"}


def test_p1_source_assertion_identity_is_stable_for_same_payload_and_key_order() -> None:
    assertion = _source_assertion()
    reordered = deepcopy(assertion)
    reordered["qualifiers"] = {"timeframe": "2026-Q1", "population": "adults"}
    reordered["qualifier_extensions"] = {"study_arm": "control", "dose_form": "daily"}

    assert canonical_source_assertion_json(assertion) == canonical_source_assertion_json(reordered)
    assert source_assertion_fingerprint(assertion) == source_assertion_fingerprint(reordered)
    assert source_assertion_id(assertion) == source_assertion_id(reordered)
    assert validate(reordered, "source_assertion").ok


def test_p1_source_assertion_identity_changes_with_material_payload() -> None:
    assertion = _source_assertion()
    changed = deepcopy(assertion)
    changed["qualifiers"]["timeframe"] = "2026-Q2"

    assert source_assertion_fingerprint(changed) != source_assertion_fingerprint(assertion)
    assert not validate(changed, "source_assertion").ok


def test_p1_source_assertion_rejects_unbound_id_fingerprint_and_text_digest() -> None:
    assertion = _source_assertion()
    assertion["assertion_id"] = f"ast_{_hash('a')}"
    assertion["identity"]["fingerprint"] = _hash("b")
    assertion["assertion_text_sha256"] = _hash("c")

    errors = validate(assertion, "source_assertion").errors
    assert any("assertion_id" in error for error in errors)
    assert any("identity/fingerprint" in error for error in errors)
    assert any("assertion_text_sha256" in error for error in errors)


def test_p1_inference_cannot_validate_as_source_assertion() -> None:
    inference = {
        "schema_version": "1.0",
        "type": "inference_record",
        "inference_id": "inf_001",
        "inference_version": 1,
        "conclusion": "This is a derived conclusion.",
        "source_assertion_refs": [{"assertion_id": f"ast_{_hash('a')}", "assertion_version": 2}],
        "reasoning": {"summary": "Synthesized from evidence.", "method": "reviewed synthesis"},
        "status": "active",
    }
    assert validate(inference, "inference_record").ok
    assert not validate(inference, "source_assertion").ok


def test_p1_lifecycle_and_reversal_keep_immutable_assertion_versions() -> None:
    assertion = _source_assertion()
    lifecycle = {
        "schema_version": "1.0", "type": "assertion_lifecycle_event", "event_id": "evt_001",
        "sequence": 3, "idempotency_key": "formal-retraction:ast:2", "occurred_at": "2026-07-13T12:00:00Z",
        "cause": "formal_retraction",
        "target": {"kind": "source_assertion", "id": assertion["assertion_id"], "version": 2},
        "transition": {"from": "eligible", "to": "invalidated"},
        "authoritative_action": "block_reuse",
        "dependent_actions": [
            {"object_kind": "canonical_claim_edge", "action": "block_reuse"},
            {"object_kind": "export", "action": "mark_stale"},
        ],
    }
    claim: dict[str, Any] = {
        "schema_version": "1.0", "type": "canonical_claim", "canonical_claim_id": "ccl_001",
        "canonical_claim_version": 4, "state": "rolled_back", "statement": "A reversible grouped claim.",
        "source_assertion_refs": [{"assertion_id": assertion["assertion_id"], "assertion_version": 2, "relation": "supports"}],
        "replacement_claims": [{"canonical_claim_id": "ccl_002", "canonical_claim_version": 1}],
        "reversal": {
            "event_id": "evt_001", "reason": "formal retraction",
            "provenance": {"recorded_by": "reviewer_001", "recorded_at": "2026-07-13T12:00:00Z"},
            "resulting_claims": [{"canonical_claim_id": "ccl_002", "canonical_claim_version": 1}],
        },
    }
    assert validate(lifecycle, "assertion_lifecycle_event").ok
    assert validate(claim, "canonical_claim").ok


def test_p1_lifecycle_rejects_illegal_or_unblocked_invalidations() -> None:
    assertion = _source_assertion()
    event = {
        "schema_version": "1.0", "type": "assertion_lifecycle_event", "event_id": "evt_002",
        "sequence": 4, "idempotency_key": "illegal", "occurred_at": "2026-07-13T12:01:00Z",
        "cause": "manual_tombstone",
        "target": {"kind": "source_assertion", "id": assertion["assertion_id"], "version": 2},
        "transition": {"from": "tombstoned", "to": "stale"},
    }
    assert not validate(event, "assertion_lifecycle_event").ok

    event["transition"] = {"from": "eligible", "to": "invalidated"}
    assert not validate(event, "assertion_lifecycle_event").ok


def test_p1_superseded_canonical_claim_accepts_versioned_replaces_link() -> None:
    assertion = _source_assertion()
    claim = {
        "schema_version": "1.0", "type": "canonical_claim", "canonical_claim_id": "ccl_020",
        "canonical_claim_version": 3, "state": "superseded", "statement": "Superseded grouped claim.",
        "source_assertion_refs": [{"assertion_id": assertion["assertion_id"], "assertion_version": 2, "relation": "supports"}],
        "replaces": [{"canonical_claim_id": "ccl_019", "canonical_claim_version": 2}],
    }
    assert validate(claim, "canonical_claim").ok


def test_p1_canonical_split_and_rollback_require_complete_lineage() -> None:
    assertion = _source_assertion()
    claim: dict[str, Any] = {
        "schema_version": "1.0", "type": "canonical_claim", "canonical_claim_id": "ccl_010",
        "canonical_claim_version": 2, "state": "split", "statement": "Split grouped claim.",
        "source_assertion_refs": [{"assertion_id": assertion["assertion_id"], "assertion_version": 2, "relation": "supports"}],
    }
    assert not validate(claim, "canonical_claim").ok
    claim["state"] = "rolled_back"
    assert not validate(claim, "canonical_claim").ok
    claim["state"] = "split"

    claim["replacement_claims"] = [{"canonical_claim_id": "ccl_011", "canonical_claim_version": 1}]
    claim["reversal"] = {
        "event_id": "evt_010", "reason": "scope split",
        "provenance": {"recorded_by": "reviewer_001", "recorded_at": "2026-07-13T12:00:00Z"},
        "resulting_claims": [{"canonical_claim_id": "ccl_011", "canonical_claim_version": 1}],
    }
    assert validate(claim, "canonical_claim").ok

    del claim["reversal"]["provenance"]
    assert not validate(claim, "canonical_claim").ok


def test_p1_legacy_claim_ledger_remains_valid_without_persistent_references() -> None:
    legacy = {
        "id": "claim_legacy", "intent_id": "intent_demo",
        "claims": [{"claim_id": "clm_001", "text": "Legacy", "sources": []}],
    }
    assert validate(legacy, "claim_ledger").ok
    assert "persistent_references" not in legacy["claims"][0]


def test_p1_export_only_projects_explicit_persistent_references() -> None:
    legacy_claim: dict[str, object] = {"claim_id": "clm_001", "text": "Legacy", "sources": []}
    assert "persistent_references" not in export_service._build_claims({"claims": [legacy_claim]}, {}, 0)[0]

    linked_claim = deepcopy(legacy_claim)
    linked_claim["persistent_references"] = {
        "source_edition_id": f"sed_{_hash('b')}", "passage_id": f"psg_{_hash('c')}",
        "source_assertion_id": f"ast_{_hash('a')}", "assertion_version": 2,
    }
    exported = export_service._build_claims({"claims": [linked_claim]}, {}, 0)[0]
    assert exported["persistent_references"] == linked_claim["persistent_references"]
