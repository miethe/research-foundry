"""Phase 6 reuse, lifecycle impact, and derived-seam regressions."""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from research_foundry.assertion_identity import source_assertion_fingerprint, source_assertion_id
from research_foundry.schemas import SchemaRegistry
from research_foundry.services.assertion_impact import (
    AssertionImpactReconciler,
    ImpactInterrupted,
    ImpactOperationError,
    enumerate_impact,
    resume_impact,
)
from research_foundry.services.assertion_reuse import block_authoritative_reuse, evaluate_reuse
from research_foundry.services.catalog_service import purge_lifecycle_derived_file
from research_foundry.services.export_service import assertion_lifecycle_export_status
from research_foundry.services.run_launch import launch_run, retrieve_first_reuse_decision
from research_foundry.yamlio import dump_yaml, load_yaml


def _assertion(**overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "assertion_id": "ast_001",
        "workspace_id": "workspace-a",
        "lifecycle_state": "eligible",
        "rights_allowed": True,
        "sensitivity_allowed": True,
        "evaluation_passed": True,
        "freshness_current": True,
        "invalidation_state": "active",
        "source_edition_id": f"sed_{'a' * 64}",
        "extraction_contract": "contract-v1",
    }
    value.update(overrides)
    return value


@pytest.mark.parametrize(
    ("overrides", "action", "reason"),
    [
        ({}, "allow", "eligible"),
        ({"lifecycle_state": "stale"}, "refresh", "freshness_refresh_required"),
        ({"freshness_current": False}, "refresh", "freshness_refresh_required"),
        ({"freshness_current": None}, "deny", "freshness_context_missing"),
        ({"rights_allowed": False}, "deny", "rights_denied"),
        ({"evaluation_passed": False}, "deny", "evaluation_missing_or_failed"),
        ({"lifecycle_state": "interrupted"}, "deny", "lifecycle_unknown"),
        ({"invalidation_state": None}, "deny", "invalidation_unknown"),
        ({"invalidation_state": "reconciling"}, "deny", "invalidation_unknown"),
        ({"source_edition_id": " "}, "deny", "edition_context_invalid"),
        ({"extraction_contract": " "}, "deny", "extraction_contract_invalid"),
    ],
)
def test_reuse_policy_is_typed_and_fail_closed(
    overrides: dict[str, object], action: str, reason: str
) -> None:
    decision = evaluate_reuse(_assertion(**overrides), workspace_id="workspace-a")
    assert (decision.action, decision.reason_code) == (action, reason)


def test_retrieve_first_run_seam_requires_matching_workspace_and_contract() -> None:
    assertion = _assertion()
    assert retrieve_first_reuse_decision(assertion, workspace_id="workspace-b").reason_code == "workspace_mismatch"
    assert retrieve_first_reuse_decision(
        assertion, workspace_id="workspace-a", required_extraction_contract="contract-v2"
    ).action == "refresh"
    with pytest.raises(ValueError, match="reuse_not_eligible:workspace_mismatch"):
        launch_run(
            text="A blocked candidate must not start a run.",
            reuse_assertion=assertion,
            reuse_workspace_id="workspace-b",
        )


def test_authoritative_block_precedes_complete_fixture_impact_traversal() -> None:
    fixture = Path("tests/fixtures/assertion_ledger/phase0_propagation_expected_manifest.json")
    expected = json.loads(fixture.read_text(encoding="utf-8"))["expected_objects"]
    assert len(expected) == 120
    assertion = block_authoritative_reuse(_assertion(), event_id="evt_001")
    receipt = enumerate_impact(event_id="evt_001", assertion=assertion, dependencies=expected)
    assert receipt.status == "pending"
    assert {(item.object_id, item.action) for item in receipt.actions} == {
        (item["object_id"], item["action"]) for item in expected
    }


def _schema_assertion() -> dict[str, object]:
    assertion: dict[str, object] = {
        "schema_version": "1.0",
        "type": "source_assertion",
        "assertion_id": "",
        "assertion_version": 1,
        "source_edition_id": f"sed_{'b' * 64}",
        "passage_id": f"psg_{'c' * 64}",
        "assertion_text": "Durable, passage-bound evidence.",
        "assertion_text_sha256": sha256(b"Durable, passage-bound evidence.").hexdigest(),
        "qualifiers": {},
        "qualifier_extensions": {},
        "extraction_provenance": {
            "extractor": "deterministic-test",
            "provider": None,
            "model": None,
            "prompt_version": None,
            "schema_version": "extraction-card-fact-claim-v1",
            "code_version": None,
            "observed_at": "2026-07-14T16:00:00Z",
        },
        # rights-entity-model-v1 P1-1/P1-2: `extensions.evidence_taxonomy`
        # (evidence_item_type + judgment_basis) became a required top-level
        # sibling of `identity`/`rights_summary`/`synthesis` on
        # source_assertion.schema.yaml. Non-material (not in
        # SOURCE_ASSERTION_MATERIAL_FIELDS), so its presence does not affect
        # the fingerprint/identity below.
        "extensions": {
            "evidence_taxonomy": {
                "evidence_item_type": "observed_finding",
                "judgment_basis": "measured",
            }
        },
        "lifecycle_state": "eligible",
        "identity": {
            "algorithm": "sha256-canonical-json-v1",
            "fingerprint": "",
            "material_fields": [
                "source_edition_id",
                "passage_id",
                "assertion_text_sha256",
                "qualifiers",
                "qualifier_extensions",
            ],
        },
    }
    fingerprint = source_assertion_fingerprint(assertion)
    assertion["identity"] = {
        "algorithm": "sha256-canonical-json-v1",
        "fingerprint": fingerprint,
        "material_fields": [
            "source_edition_id",
            "passage_id",
            "assertion_text_sha256",
            "qualifiers",
            "qualifier_extensions",
        ],
    }
    assertion["assertion_id"] = source_assertion_id(assertion)
    return assertion


def _lifecycle_event(
    assertion: dict[str, object], event_id: str, *, transition_from: str = "eligible"
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "type": "assertion_lifecycle_event",
        "event_id": event_id,
        "sequence": 1,
        "idempotency_key": f"test:{event_id}",
        "occurred_at": "2026-07-14T16:00:00Z",
        "cause": "formal_retraction",
        "target": {"kind": "source_assertion", "id": assertion["assertion_id"], "version": 1},
        "transition": {"from": transition_from, "to": "invalidated"},
        "authoritative_action": "block_reuse",
        "dependent_actions": [{"object_kind": "canonical_claim_edge", "action": "block_reuse"}],
    }


def _persist_impact_inputs(
    tmp_foundry, *, event_id: str = "evt_001", transition_from: str = "eligible"
) -> tuple[AssertionImpactReconciler, str, list[dict[str, str]]]:
    workspace_id = "workspace-a"
    reconciler = AssertionImpactReconciler(workspace_id=workspace_id, paths=tmp_foundry)
    assertion = _schema_assertion()
    assertion_id = str(assertion["assertion_id"])
    assert SchemaRegistry(schemas_dir=tmp_foundry.schemas).validate(assertion, "source_assertion").ok
    dump_yaml(assertion, reconciler.root / "assertions" / f"{assertion_id}.yaml")
    dump_yaml(
        _lifecycle_event(assertion, event_id, transition_from=transition_from),
        reconciler.event_path(event_id),
    )
    fixture = Path("tests/fixtures/assertion_ledger/phase0_propagation_expected_manifest.json")
    expected = json.loads(fixture.read_text(encoding="utf-8"))["expected_objects"]
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text(json.dumps({"expected_objects": expected}), encoding="utf-8")
    projection = tmp_foundry.root / ".rf_cache" / "assertion_catalog" / f"{sha256(workspace_id.encode()).hexdigest()}.json"
    projection.parent.mkdir(parents=True, exist_ok=True)
    projection.write_text("derived", encoding="utf-8")
    return reconciler, assertion_id, expected


def test_persisted_reconciliation_blocks_before_full_manifest_and_resumes_idempotently(tmp_foundry) -> None:
    reconciler, assertion_id, expected = _persist_impact_inputs(tmp_foundry)

    with pytest.raises(ImpactInterrupted):
        reconciler.reconcile(assertion_id=assertion_id, event_id="evt_001", _interrupt_after_actions=1)

    assertion = load_yaml(reconciler.root / "assertions" / f"{assertion_id}.yaml")
    receipt = load_yaml(reconciler.receipt_path("evt_001"))
    assert assertion == _schema_assertion()
    policy = load_yaml(reconciler.policy_path(assertion_id))
    assert policy["lifecycle_state"] == "blocked"
    assert policy["invalidation_event_id"] == "evt_001"
    assert receipt["status"] == "pending"
    assert sum(action["status"] == "completed" for action in receipt["actions"]) == 1

    result = reconciler.reconcile(assertion_id=assertion_id, event_id="evt_001")
    completed = load_yaml(result.receipt_path)
    assert (result.status, result.action_count) == ("completed", 120)
    assert {(action["object_id"], action["action"]) for action in completed["actions"]} == {
        (item["object_id"], item["action"]) for item in expected
    }
    assert all(action["status"] == "completed" for action in completed["actions"])
    effect_paths = [reconciler.root / action["effect_receipt"] for action in completed["actions"]]
    assert len(set(effect_paths)) == 120
    assert all(load_yaml(path)["status"] == "recorded" for path in effect_paths)
    projection = tmp_foundry.root / ".rf_cache" / "assertion_catalog" / f"{sha256(b'workspace-a').hexdigest()}.json"
    assert not projection.exists()
    assert {action["export_status"] for action in completed["actions"] if action["object_class"] == "export"} == {"withheld"}
    assert {action["reuse_reason"] for action in completed["actions"] if action["object_class"] == "run"} == {"lifecycle_blocked"}
    assert {action["writeback_status"] for action in completed["actions"] if action["object_class"] == "mock_writeback_receipt"} == {"default_denied"}

    assert reconciler.reconcile(assertion_id=assertion_id, event_id="evt_001") == result
    assert load_yaml(result.receipt_path) == completed

    deleted_effect = reconciler.root / completed["actions"][0]["effect_receipt"]
    deleted_effect.unlink()
    with pytest.raises(ImpactOperationError, match="impact_effect_invalid"):
        reconciler.reconcile(assertion_id=assertion_id, event_id="evt_001")


def test_persisted_reconciliation_denies_out_of_order_and_malformed_manifest(tmp_foundry) -> None:
    reconciler, assertion_id, _ = _persist_impact_inputs(tmp_foundry)
    assert reconciler.reconcile(assertion_id=assertion_id, event_id="evt_001").status == "completed"
    reconciler.manifest_path("evt_002").parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path("evt_002").write_text('{"expected_objects": []}', encoding="utf-8")
    dump_yaml(_lifecycle_event(_schema_assertion(), "evt_002"), reconciler.event_path("evt_002"))
    with pytest.raises(ImpactOperationError, match="out_of_order_lifecycle_event"):
        reconciler.reconcile(assertion_id=assertion_id, event_id="evt_002")

    other = AssertionImpactReconciler(workspace_id="workspace-b", paths=tmp_foundry)
    other_assertion = _schema_assertion()
    dump_yaml(other_assertion, other.root / "assertions" / f"{other_assertion['assertion_id']}.yaml")
    dump_yaml(_lifecycle_event(other_assertion, "evt_missing"), other.event_path("evt_missing"))
    blocked = other.reconcile(assertion_id=str(other_assertion["assertion_id"]), event_id="evt_missing")
    assert blocked.status == "blocked"
    assert load_yaml(other.root / "assertions" / f"{other_assertion['assertion_id']}.yaml") == other_assertion


def test_persisted_reconciliation_rejects_malformed_lifecycle_policy(tmp_foundry) -> None:
    reconciler, assertion_id, _ = _persist_impact_inputs(tmp_foundry)
    dump_yaml(
        {
            "schema_version": "1.0",
            "type": "assertion_lifecycle_policy_state",
            "assertion_id": assertion_id,
            "assertion_version": 1,
            "lifecycle_state": "eligible",
            "invalidation_state": "blocked",
            "invalidation_event_id": "evt_001",
        },
        reconciler.policy_path(assertion_id),
    )
    with pytest.raises(ImpactOperationError, match="lifecycle_policy_invalid"):
        reconciler.reconcile(assertion_id=assertion_id, event_id="evt_001")
    assert load_yaml(reconciler.root / "assertions" / f"{assertion_id}.yaml") == _schema_assertion()


@pytest.mark.parametrize("mutation", ["truncated", "extra", "duplicate", "mismatched"])
def test_completed_receipt_requires_exact_canonical_manifest_action_set(tmp_foundry, mutation: str) -> None:
    reconciler, assertion_id, _ = _persist_impact_inputs(tmp_foundry)
    result = reconciler.reconcile(assertion_id=assertion_id, event_id="evt_001")
    receipt = load_yaml(result.receipt_path)
    actions = receipt["actions"]
    if mutation == "truncated":
        actions.pop()
    else:
        injected = deepcopy(actions[0])
        injected["status"] = "pending"
        if mutation == "extra":
            injected["object_id"] = "unexpected_object"
        elif mutation == "mismatched":
            actions[0]["object_id"] = "mismatched_object"
            actions[0]["status"] = "pending"
            actions[0].pop("effect_receipt")
            dump_yaml(receipt, result.receipt_path)
            with pytest.raises(ImpactOperationError, match="impact_receipt_action_set_invalid"):
                reconciler.reconcile(assertion_id=assertion_id, event_id="evt_001")
            return
        actions.append(injected)
    dump_yaml(receipt, result.receipt_path)
    with pytest.raises(ImpactOperationError, match="impact_receipt_action_set_invalid"):
        reconciler.reconcile(assertion_id=assertion_id, event_id="evt_001")


def test_persisted_reconciliation_rejects_transition_from_source_mismatch(tmp_foundry) -> None:
    reconciler, assertion_id, _ = _persist_impact_inputs(tmp_foundry, transition_from="stale")
    with pytest.raises(ImpactOperationError, match="lifecycle_transition_source_mismatch"):
        reconciler.reconcile(assertion_id=assertion_id, event_id="evt_001")
    assert not reconciler.policy_path(assertion_id).exists()
    assert not reconciler.receipt_path("evt_001").exists()


def test_impact_rejects_out_of_order_or_unknown_dependencies_and_resumes_idempotently() -> None:
    assertion = block_authoritative_reuse(_assertion(), event_id="evt_001")
    with pytest.raises(ValueError, match="authoritative_block_required"):
        enumerate_impact(event_id="evt_002", assertion=assertion, dependencies=[])
    blocked = enumerate_impact(
        event_id="evt_001", assertion=assertion, dependencies=[{"object_id": "x", "object_class": "unknown"}]
    )
    assert blocked.status == "blocked"
    receipt = enumerate_impact(
        event_id="evt_001",
        assertion=assertion,
        dependencies=[
            {"object_id": "run_1", "object_class": "run"},
            {"object_id": "refresh_1", "object_class": "assertion_regeneration"},
        ],
    )
    first = resume_impact(receipt, completed_object_ids=["run_1", "refresh_1"])
    assert first.status == "completed"
    assert resume_impact(first, completed_object_ids=["run_1"]) == first
    with pytest.raises(ValueError, match="out_of_order_lifecycle_event"):
        block_authoritative_reuse(assertion, event_id="evt_002")
    inconsistent = _assertion(invalidation_state="blocked", invalidation_event_id="evt_001")
    with pytest.raises(ValueError, match="lifecycle_invalidation_inconsistent"):
        block_authoritative_reuse(inconsistent, event_id="evt_001")


def test_export_and_catalog_seams_do_not_retain_invalid_current_reads(tmp_path: Path) -> None:
    derived = tmp_path / "projection.json"
    derived.write_text("derived", encoding="utf-8")
    assert not purge_lifecycle_derived_file(derived, lifecycle_state="stale")
    assert derived.exists()
    assert purge_lifecycle_derived_file(derived, lifecycle_state="blocked")
    assert not derived.exists()
    assert assertion_lifecycle_export_status("eligible") == "current"
    assert assertion_lifecycle_export_status("stale") == "stale"
    assert assertion_lifecycle_export_status("interrupted") == "withheld"
