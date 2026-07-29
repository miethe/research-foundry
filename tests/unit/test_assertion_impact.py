"""RPC-6.1/6.2: canonical dependent enumeration and receipt/replay integration.

Mirrors ``tests/integration/test_assertion_reuse.py``'s fixture shape for the
manifest-driven ``AssertionImpactReconciler`` flow (kept self-contained per
this repo's per-test-file convention) and
``tests/unit/test_assertion_inference.py``/``test_canonical_claim_materialization.py``'s
``ingest_source`` -> ``extraction.extract_run`` -> ``claim_mapping.build_claim_ledger``
-> ``AssertionMaterializer`` fixture shape to build REAL, authoritative
``inference_record``/``canonical_claim`` records for the new
``enumerate_canonical_dependents`` (RPC-6.1) enumeration function.

``report_assertion_use`` records are hand-written directly to disk (the
publish path does not yet resolve inference/canonical-claim persistent
references, per ``services/assertion_report_use.py``'s own module note) --
this is a legitimate way to unit-test the READ side of RPC-6.1 independent of
that separate, not-yet-wired publish seam.
"""

from __future__ import annotations

import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from research_foundry.assertion_identity import source_assertion_fingerprint, source_assertion_id
from research_foundry.schemas import SchemaRegistry
from research_foundry.services import claim_mapping, extraction
from research_foundry.services.assertion_impact import (
    _ACTIONS,
    AssertionImpactReconciler,
    ImpactInterrupted,
    ImpactOperationError,
    SOURCE_ASSERTION_BLOCKED,
    SOURCE_ASSERTION_ELIGIBLE,
    SOURCE_ASSERTION_POLICY_INVALID,
    collect_stale_object_ids,
    effective_source_assertion_lifecycle_state,
    enumerate_canonical_dependents,
    enumerate_impact,
    resume_impact,
)
from research_foundry.services.assertion_inference import AssertionInferenceMaterializer
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.assertion_registry import AssertionRegistry
from research_foundry.services.assertion_report_use import (
    build_cited_ref,
    build_report_ref,
    normalize_rights_snapshot,
    report_assertion_use_fingerprint,
)
from research_foundry.services.canonical_claim_materialization import CanonicalClaimMaterializer
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml

_WORKSPACE = "workspace-a"


# ---------------------------------------------------------------------------
# Baseline behavior pin (AC RPC-8) -- existing enumeration/resume machinery
# and its object-class vocabulary are byte-identical to before this task.
# ---------------------------------------------------------------------------


def test_lifecycle_action_vocabulary_is_unchanged_no_schema_gap() -> None:
    """F13 disposition: no lifecycle-vocabulary gap exists for RPC-6.1 -- the
    ``canonical_claim_edge``/``inference``/``report_revision`` object classes
    this task reuses were ALREADY shipped mapping to ``mark_stale`` before
    this task began. Pinning the exact dict guards against an accidental
    widening creeping in alongside the new enumeration function."""

    assert _ACTIONS == {
        "source_edition": "block_reuse",
        "passage": "block_reuse",
        "assertion_version": "block_reuse",
        "canonical_claim_edge": "mark_stale",
        "inference": "mark_stale",
        "report_revision": "mark_stale",
        "run": "mark_stale",
        "export": "mark_stale",
        "derived_cache_or_index": "purge_current_read",
        "assertion_regeneration": "regenerate",
        "mock_writeback_receipt": "queue_default_denied_reconciliation",
    }


def test_legacy_manifest_traversal_is_unaffected_by_the_new_function() -> None:
    """Pin: the pre-existing manifest-file-driven traversal (phase0 fixture,
    exactly as ``tests/integration/test_assertion_reuse.py`` already
    exercises) is untouched by adding ``enumerate_canonical_dependents``."""

    fixture = Path("tests/fixtures/assertion_ledger/phase0_propagation_expected_manifest.json")
    expected = json.loads(fixture.read_text(encoding="utf-8"))["expected_objects"]
    assert len(expected) == 120

    from research_foundry.services.assertion_reuse import block_authoritative_reuse

    assertion = {
        "assertion_id": "ast_001",
        "workspace_id": _WORKSPACE,
        "lifecycle_state": "eligible",
        "invalidation_state": "active",
    }
    blocked = block_authoritative_reuse(assertion, event_id="evt_001")
    receipt = enumerate_impact(event_id="evt_001", assertion=blocked, dependencies=expected)
    assert receipt.status == "pending"
    assert {(item.object_id, item.action) for item in receipt.actions} == {
        (item["object_id"], item["action"]) for item in expected
    }

    resumed = resume_impact(receipt, completed_object_ids=[item.object_id for item in receipt.actions])
    assert resumed.status == "completed"


# ---------------------------------------------------------------------------
# RPC-6.1 -- real canonical dependents, affected/unaffected/transitive
# ---------------------------------------------------------------------------


def _write_run_yaml(tmp_foundry, run_id: str, workspace_id: str = _WORKSPACE) -> None:
    dump_yaml(
        {
            "schema_version": 0.1,
            "type": "run",
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "workspace_id": workspace_id,
        },
        tmp_foundry.run_paths(run_id).run_yaml,
    )


def _enable_ledger(tmp_foundry) -> None:
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {
        "ledger_write_enabled": True,
        "canonical_claims_enabled": True,
    }
    dump_yaml(foundry, tmp_foundry.foundry_yaml)


def _setup_run_with_two_supported_claims(tmp_foundry, run_id: str, *, workspace_id: str = _WORKSPACE) -> None:
    _enable_ledger(tmp_foundry)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        "evidence-1.txt",
        run_id=run_id,
        title="First Evidence",
        sensitivity="personal",
        content="Pediatric neutrophil counts trend lower than adult reference ranges.",
        assertion_registry_workspace_id=workspace_id,
        paths=tmp_foundry,
    )
    ingest_source(
        "evidence-2.txt",
        run_id=run_id,
        title="Second Evidence",
        sensitivity="personal",
        content="Pediatric lymphocyte counts trend higher than adult reference ranges.",
        assertion_registry_workspace_id=workspace_id,
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)
    materializer = AssertionMaterializer(workspace_id=workspace_id, paths=tmp_foundry)
    result = materializer.materialize_run(run_id)
    assert result.status == "materialized"
    assert len(result.assertion_ids) == 2
    _write_run_yaml(tmp_foundry, run_id, workspace_id=workspace_id)


def _ledger(tmp_foundry, run_id: str) -> dict:
    return load_yaml(tmp_foundry.run_paths(run_id).claim_ledger)


def _assertion_ref(tmp_foundry, run_id: str, claim_id: str, *, relation: str = "supports") -> dict:
    row = next(c for c in _ledger(tmp_foundry, run_id)["claims"] if c["claim_id"] == claim_id)
    refs = row["persistent_references"]
    return {"assertion_id": refs["source_assertion_id"], "assertion_version": refs["assertion_version"], "relation": relation}


def _append_inference_claim(tmp_foundry, run_id: str, *, from_claims: list[str]) -> str:
    ledger_path = tmp_foundry.run_paths(run_id).claim_ledger
    ledger = load_yaml(ledger_path)
    claim_id = f"clm_{len(ledger['claims']) + 1:03d}"
    ledger["claims"].append(
        {
            "claim_id": claim_id,
            "text": f"Inference over {from_claims}.",
            "materiality": "material",
            "claim_type": "comparative",
            "status": "inference",
            "confidence": "medium",
            "sources": [],
            "inference_basis": {"from_claims": from_claims, "reasoning_summary": "Synthesized."},
            "report_locations": [],
            "reviewer_notes": "",
        }
    )
    dump_yaml(ledger, ledger_path)
    return claim_id


def _append_canonical_candidate_claim(tmp_foundry, run_id: str, *, text: str) -> str:
    ledger_path = tmp_foundry.run_paths(run_id).claim_ledger
    ledger = load_yaml(ledger_path)
    claim_id = f"clm_{len(ledger['claims']) + 1:03d}"
    ledger["claims"].append(
        {
            "claim_id": claim_id,
            "text": text,
            "materiality": "material",
            "claim_type": "comparative",
            "status": "supported",
            "confidence": "medium",
            "sources": [],
            "report_locations": [],
            "reviewer_notes": "",
        }
    )
    dump_yaml(ledger, ledger_path)
    return claim_id


def _write_report_use(
    tmp_foundry,
    *,
    workspace_id: str = _WORKSPACE,
    report_id: str,
    cited_ref: dict,
    created_at: str = "2026-07-28T00:00:00Z",
) -> str:
    """Hand-write one schema-valid ``report_assertion_use`` record to disk."""

    report_ref = build_report_ref(report_id=report_id, report_content_digest=sha256(report_id.encode()).hexdigest())
    record = {
        "schema_version": "1.0",
        "type": "report_assertion_use",
        "use_id": "placeholder",
        "workspace_id": workspace_id,
        "report_ref": report_ref,
        "cited_ref": cited_ref,
        "rights_snapshot": normalize_rights_snapshot(None),
        "created_at": created_at,
    }
    fingerprint = report_assertion_use_fingerprint(record)
    use_id = f"rau_{fingerprint}"
    record["use_id"] = use_id
    record["identity"] = {
        "algorithm": "sha256-canonical-json-v1",
        "fingerprint": fingerprint,
        "material_fields": ["workspace_id", "report_ref", "cited_ref", "rights_snapshot", "created_at"],
    }
    assert SchemaRegistry(schemas_dir=tmp_foundry.schemas).validate(record, "report_assertion_use").ok
    root = AssertionRegistry(workspace_id=workspace_id, paths=tmp_foundry).root
    dump_yaml(record, root / "report_assertion_uses" / "records" / f"{use_id}.yaml")
    return report_ref["report_revision_id"]


def test_enumerate_canonical_dependents_is_exact_including_transitive_canonical(tmp_foundry) -> None:
    run_id = "rf_run_p6_dependents"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")  # the assertion about to be blocked
    ref_b = _assertion_ref(tmp_foundry, run_id, "clm_002")  # an unrelated sibling assertion

    # Inference 1: supported ONLY by A -- directly affected.
    inf1_claim = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001"])
    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    inf1 = inferencer.materialize_inference(run_id, inf1_claim, producer="agent-research-1")
    assert inf1.status == "materialized"

    # Inference 2: supported ONLY by sibling B -- must NOT appear in any action list.
    inf2_claim = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_002"])
    inf2 = inferencer.materialize_inference(run_id, inf2_claim, producer="agent-research-1")
    assert inf2.status == "materialized"

    ccl_materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)

    # ccl_1: directly cites A via source_assertion_refs -- directly affected.
    ccl1_claim = _append_canonical_candidate_claim(tmp_foundry, run_id, text="Direct citation of A.")
    ccl1 = ccl_materializer.publish_canonical_claim(
        run_id, ccl1_claim, statement="Direct citation of A.", source_assertion_refs=[ref_a], explicit_request=True
    )
    assert ccl1.status == "materialized"

    # ccl_2: own source_assertion_refs cite ONLY sibling B, but inference_refs
    # cite inf1 (affected) -- transitively affected.
    ccl2_claim = _append_canonical_candidate_claim(tmp_foundry, run_id, text="Transitive citation via inf1.")
    ccl2 = ccl_materializer.publish_canonical_claim(
        run_id,
        ccl2_claim,
        statement="Transitive citation via inf1.",
        source_assertion_refs=[ref_b],
        inference_refs=[{"inference_id": inf1.inference_id, "inference_version": inf1.inference_version, "relation": "supports"}],
        explicit_request=True,
    )
    assert ccl2.status == "materialized"

    # ccl_3: cites ONLY sibling B, no inference_refs -- must NOT appear.
    ccl3_claim = _append_canonical_candidate_claim(tmp_foundry, run_id, text="Unrelated to A.")
    ccl3 = ccl_materializer.publish_canonical_claim(
        run_id, ccl3_claim, statement="Unrelated to A.", source_assertion_refs=[ref_b], explicit_request=True
    )
    assert ccl3.status == "materialized"

    # Report-use fixtures: affected (R1..R3) and unaffected (U1..U3).
    r1 = _write_report_use(
        tmp_foundry,
        report_id="report_p6_a1",
        cited_ref=build_cited_ref(ref_kind="source_assertion", assertion_id=ref_a["assertion_id"], assertion_version=ref_a["assertion_version"]),
    )
    r2 = _write_report_use(
        tmp_foundry,
        report_id="report_p6_a2",
        cited_ref=build_cited_ref(ref_kind="inference", inference_id=inf1.inference_id, inference_version=inf1.inference_version),
    )
    r3_first = _write_report_use(
        tmp_foundry,
        report_id="report_p6_a3",
        cited_ref=build_cited_ref(ref_kind="canonical_claim", canonical_claim_id=ccl1.canonical_claim_id, canonical_claim_version=ccl1.canonical_claim_version),
    )
    r3_second = _write_report_use(
        tmp_foundry,
        report_id="report_p6_a3",  # SAME report -- must dedupe to ONE report_revision action
        cited_ref=build_cited_ref(ref_kind="canonical_claim", canonical_claim_id=ccl2.canonical_claim_id, canonical_claim_version=ccl2.canonical_claim_version),
    )
    assert r3_first == r3_second

    u1 = _write_report_use(
        tmp_foundry,
        report_id="report_p6_u1",
        cited_ref=build_cited_ref(ref_kind="source_assertion", assertion_id=ref_b["assertion_id"], assertion_version=ref_b["assertion_version"]),
    )
    u2 = _write_report_use(
        tmp_foundry,
        report_id="report_p6_u2",
        cited_ref=build_cited_ref(ref_kind="inference", inference_id=inf2.inference_id, inference_version=inf2.inference_version),
    )
    u3 = _write_report_use(
        tmp_foundry,
        report_id="report_p6_u3",
        cited_ref=build_cited_ref(ref_kind="canonical_claim", canonical_claim_id=ccl3.canonical_claim_id, canonical_claim_version=ccl3.canonical_claim_version),
    )
    assert len({u1, u2, u3, r1, r2, r3_first}) == 6  # all six revisions are distinct handles

    dependents = enumerate_canonical_dependents(
        paths=tmp_foundry,
        workspace_id=_WORKSPACE,
        assertion_id=ref_a["assertion_id"],
        assertion_version=ref_a["assertion_version"],
    )

    by_class = {"inference": set(), "canonical_claim_edge": set(), "report_revision": set()}
    for item in dependents:
        assert item["action"] == "mark_stale"
        by_class[item["object_class"]].add(item["object_id"])

    assert by_class["inference"] == {inf1.inference_id}
    assert inf2.inference_id not in by_class["inference"]
    assert by_class["canonical_claim_edge"] == {ccl1.canonical_claim_id, ccl2.canonical_claim_id}
    assert ccl3.canonical_claim_id not in by_class["canonical_claim_edge"]
    assert by_class["report_revision"] == {r1, r2, r3_first}
    assert not by_class["report_revision"] & {u1, u2, u3}

    # No duplicate (object_id, object_class) pairs -- report_p6_a3's two uses
    # collapsed to exactly one report_revision entry.
    seen = [(item["object_id"], item["object_class"]) for item in dependents]
    assert len(seen) == len(set(seen))

    # Deterministic ordering across repeated calls (two runs -> identical output).
    again = enumerate_canonical_dependents(
        paths=tmp_foundry, workspace_id=_WORKSPACE, assertion_id=ref_a["assertion_id"], assertion_version=ref_a["assertion_version"]
    )
    assert dependents == again
    assert dependents == sorted(dependents, key=lambda item: (item["object_class"], item["object_id"]))


def test_enumerate_canonical_dependents_legacy_workspace_yields_no_actions(tmp_foundry) -> None:
    """AC RPC-8: a workspace with source assertions but no canonical
    inference/canonical-claim/report-use records yields zero dependents --
    never an error, never a fabricated action."""

    run_id = "rf_run_p6_legacy"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")

    dependents = enumerate_canonical_dependents(
        paths=tmp_foundry, workspace_id=_WORKSPACE, assertion_id=ref_a["assertion_id"], assertion_version=ref_a["assertion_version"]
    )
    assert dependents == []


def test_enumerate_canonical_dependents_rejects_invalid_input(tmp_foundry) -> None:
    with pytest.raises(ImpactOperationError, match="invalid_workspace_id"):
        enumerate_canonical_dependents(paths=tmp_foundry, workspace_id=" ", assertion_id="ast_001", assertion_version=1)
    with pytest.raises(ImpactOperationError, match="invalid_assertion_id"):
        enumerate_canonical_dependents(paths=tmp_foundry, workspace_id=_WORKSPACE, assertion_id="", assertion_version=1)
    with pytest.raises(ImpactOperationError, match="invalid_assertion_version"):
        enumerate_canonical_dependents(paths=tmp_foundry, workspace_id=_WORKSPACE, assertion_id="ast_001", assertion_version=0)


def test_enumerate_canonical_dependents_fails_closed_on_orphaned_authority_pointer(tmp_foundry) -> None:
    """A ``(record_id, version)`` reachable from the claim-ledger generation
    pointer but absent on disk is a store/authority desync -- fail closed,
    never silently skipped (mirrors :func:`enumerate_impact`'s own
    "unknown dependency" rule)."""

    run_id = "rf_run_p6_orphan"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")
    inf_claim = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001"])
    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    inf = inferencer.materialize_inference(run_id, inf_claim, producer="agent-research-1")
    assert inf.status == "materialized"

    record_path = inferencer.root / "inferences" / f"{inf.inference_id}.yaml"
    record_path.unlink()

    with pytest.raises(ImpactOperationError, match="canonical_dependents_unavailable"):
        enumerate_canonical_dependents(
            paths=tmp_foundry, workspace_id=_WORKSPACE, assertion_id=ref_a["assertion_id"], assertion_version=ref_a["assertion_version"]
        )


# ---------------------------------------------------------------------------
# RPC-6.2 -- receipt/replay integration for the new action kinds
# ---------------------------------------------------------------------------


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
        "extensions": {
            "evidence_taxonomy": {"evidence_item_type": "observed_finding", "judgment_basis": "measured"}
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


def _lifecycle_event(assertion: dict[str, object], event_id: str) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "type": "assertion_lifecycle_event",
        "event_id": event_id,
        "sequence": 1,
        "idempotency_key": f"test:{event_id}",
        "occurred_at": "2026-07-14T16:00:00Z",
        "cause": "formal_retraction",
        "target": {"kind": "source_assertion", "id": assertion["assertion_id"], "version": 1},
        "transition": {"from": "eligible", "to": "invalidated"},
        "authoritative_action": "block_reuse",
        "dependent_actions": [
            {"object_kind": "canonical_claim_edge", "action": "block_reuse"},
            {"object_kind": "inference", "action": "block_reuse"},
            {"object_kind": "report_revision", "action": "block_reuse"},
        ],
    }


_NEW_KIND_DEPENDENTS = [
    {"object_id": "inf_p6_001", "object_class": "inference", "action": "mark_stale"},
    {"object_id": "ccl_p6_001", "object_class": "canonical_claim_edge", "action": "mark_stale"},
    {"object_id": "rrv_p6_001", "object_class": "report_revision", "action": "mark_stale"},
]


def _persist_impact_inputs(tmp_foundry, *, event_id: str = "evt_001", dependents=None):
    dependents = _NEW_KIND_DEPENDENTS if dependents is None else dependents
    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion = _schema_assertion()
    assertion_id = str(assertion["assertion_id"])
    assert SchemaRegistry(schemas_dir=tmp_foundry.schemas).validate(assertion, "source_assertion").ok
    dump_yaml(assertion, reconciler.root / "assertions" / f"{assertion_id}.yaml")
    dump_yaml(_lifecycle_event(assertion, event_id), reconciler.event_path(event_id))
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text(json.dumps({"expected_objects": dependents}), encoding="utf-8")
    return reconciler, assertion_id, dependents


def test_new_action_kinds_interrupt_and_resume_exactly(tmp_foundry) -> None:
    reconciler, assertion_id, dependents = _persist_impact_inputs(tmp_foundry)

    with pytest.raises(ImpactInterrupted):
        reconciler.reconcile(assertion_id=assertion_id, event_id="evt_001", _interrupt_after_actions=1)

    receipt = load_yaml(reconciler.receipt_path("evt_001"))
    assert receipt["status"] == "pending"
    assert sum(action["status"] == "completed" for action in receipt["actions"]) == 1

    result = reconciler.reconcile(assertion_id=assertion_id, event_id="evt_001")
    completed = load_yaml(result.receipt_path)
    assert (result.status, result.action_count) == ("completed", 3)
    assert {(action["object_id"], action["object_class"], action["action"]) for action in completed["actions"]} == {
        (item["object_id"], item["object_class"], item["action"]) for item in dependents
    }
    assert all(action["status"] == "completed" for action in completed["actions"])
    # New kinds have no special _apply_action side effect keys, only the
    # generic effect-receipt bookkeeping every non-special object_class gets.
    for action in completed["actions"]:
        assert "export_status" not in action
        assert "reuse_reason" not in action
        assert "writeback_status" not in action
        effect = load_yaml(reconciler.root / action["effect_receipt"])
        assert effect["status"] == "recorded"

    # Ordering determinism -- a second identical run reproduces the SAME receipt bytes.
    assert reconciler.reconcile(assertion_id=assertion_id, event_id="evt_001") == result
    assert load_yaml(result.receipt_path) == completed


@pytest.mark.parametrize("mutation", ["truncated", "extra", "duplicate", "mismatched"])
def test_new_action_kinds_malformed_receipt_fails_closed(tmp_foundry, mutation: str) -> None:
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


def test_new_action_kinds_missing_manifest_still_blocks_no_regression(tmp_foundry) -> None:
    """AC RPC-8 / existing semantics: a missing manifest file still produces a
    typed ``blocked`` receipt, never a zero-action success, regardless of the
    new enumeration function's existence."""

    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion = _schema_assertion()
    assertion_id = str(assertion["assertion_id"])
    dump_yaml(assertion, reconciler.root / "assertions" / f"{assertion_id}.yaml")
    dump_yaml(_lifecycle_event(assertion, "evt_missing"), reconciler.event_path("evt_missing"))

    result = reconciler.reconcile(assertion_id=assertion_id, event_id="evt_missing")
    assert result.status == "blocked"
    receipt = load_yaml(result.receipt_path)
    assert receipt["reason_code"] == "dependency_manifest_missing"
    assert receipt["actions"] == []


# ---------------------------------------------------------------------------
# RPC-6.3 -- lifecycle seam: manifest authoring wired into reconcile()
# ---------------------------------------------------------------------------


def test_lifecycle_seam_wires_canonical_dependents_and_reconciles_to_stale(tmp_foundry) -> None:
    """RPC-6.3 end-to-end: a blocked source assertion's lifecycle event, with
    NO manifest pre-written anywhere, still reconciles to completion because
    ``reconcile`` now merges RPC-6.1's ``enumerate_canonical_dependents``
    output into the manifest before deriving the receipt.  Verifies the
    dependents' lane-visible staleness through THIS module's own reader
    (``validated_receipt`` -- the impact lane's reader, never the P5
    ``assertion_catalog`` projection), that unaffected siblings never appear
    anywhere, and that repeated resume is idempotent."""

    run_id = "rf_run_rpc63_seam"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")  # about to be blocked
    ref_b = _assertion_ref(tmp_foundry, run_id, "clm_002")  # unaffected sibling

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    inf1_claim = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001"])
    inf1 = inferencer.materialize_inference(run_id, inf1_claim, producer="agent-research-1")
    assert inf1.status == "materialized"
    inf2_claim = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_002"])
    inf2 = inferencer.materialize_inference(run_id, inf2_claim, producer="agent-research-1")
    assert inf2.status == "materialized"

    ccl_materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    ccl1_claim = _append_canonical_candidate_claim(tmp_foundry, run_id, text="Direct citation of A.")
    ccl1 = ccl_materializer.publish_canonical_claim(
        run_id, ccl1_claim, statement="Direct citation of A.", source_assertion_refs=[ref_a], explicit_request=True
    )
    assert ccl1.status == "materialized"
    ccl3_claim = _append_canonical_candidate_claim(tmp_foundry, run_id, text="Unrelated to A.")
    ccl3 = ccl_materializer.publish_canonical_claim(
        run_id, ccl3_claim, statement="Unrelated to A.", source_assertion_refs=[ref_b], explicit_request=True
    )
    assert ccl3.status == "materialized"

    r1 = _write_report_use(
        tmp_foundry,
        report_id="report_rpc63_a1",
        cited_ref=build_cited_ref(
            ref_kind="source_assertion", assertion_id=ref_a["assertion_id"], assertion_version=ref_a["assertion_version"]
        ),
    )
    u1 = _write_report_use(
        tmp_foundry,
        report_id="report_rpc63_u1",
        cited_ref=build_cited_ref(
            ref_kind="source_assertion", assertion_id=ref_b["assertion_id"], assertion_version=ref_b["assertion_version"]
        ),
    )

    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion = load_yaml(reconciler.root / "assertions" / f"{ref_a['assertion_id']}.yaml")
    event_id = "evt_rpc63_seam"
    dump_yaml(_lifecycle_event(assertion, event_id), reconciler.event_path(event_id))

    # Nothing authored yet -- proves the receipt is produced by the seam,
    # never by a pre-written fixture manifest.
    assert not reconciler.manifest_path(event_id).exists()

    result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)

    assert (result.status, result.action_count) == ("completed", 3)
    manifest = json.loads(reconciler.manifest_path(event_id).read_text(encoding="utf-8"))
    assert {(item["object_id"], item["object_class"]) for item in manifest["expected_objects"]} == {
        (inf1.inference_id, "inference"),
        (ccl1.canonical_claim_id, "canonical_claim_edge"),
        (r1, "report_revision"),
    }

    receipt = load_yaml(result.receipt_path)
    assert {(a["object_id"], a["object_class"], a["action"], a["status"]) for a in receipt["actions"]} == {
        (inf1.inference_id, "inference", "mark_stale", "completed"),
        (ccl1.canonical_claim_id, "canonical_claim_edge", "mark_stale", "completed"),
        (r1, "report_revision", "mark_stale", "completed"),
    }
    # Unaffected siblings never appear anywhere in the manifest or receipt.
    untouched = {inf2.inference_id, ccl3.canonical_claim_id, u1}
    assert not ({item["object_id"] for item in manifest["expected_objects"]} & untouched)
    assert not ({a["object_id"] for a in receipt["actions"]} & untouched)

    # Lane-visible staleness -- read through this module's OWN reader seam
    # (``validated_receipt``), never the P5 ``assertion_catalog`` projection.
    validated = reconciler.validated_receipt(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert validated is not None
    assert validated["status"] == "completed"
    assert {(a["object_id"], a["object_class"], a["status"]) for a in validated["actions"]} == {
        (inf1.inference_id, "inference", "completed"),
        (ccl1.canonical_claim_id, "canonical_claim_edge", "completed"),
        (r1, "report_revision", "completed"),
    }

    # Repeated resume is idempotent -- byte-identical result and receipt.
    again = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert again == result
    assert load_yaml(result.receipt_path) == receipt


def _setup_distinct_run_with_two_supported_claims(tmp_foundry, run_id: str, *, workspace_id: str) -> None:
    """Like ``_setup_run_with_two_supported_claims`` but with evidence content
    unique to ``workspace_id`` -- source-assertion/inference identity is
    content-addressed (never workspace-scoped in the id itself), so a second
    workspace fixture reusing the exact same evidence text would collide on
    the SAME ids and defeat a genuine cross-workspace isolation check."""

    _enable_ledger(tmp_foundry)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        "evidence-1.txt",
        run_id=run_id,
        title="First Evidence",
        sensitivity="personal",
        content=f"Evidence content unique to {workspace_id} run {run_id}, item one.",
        assertion_registry_workspace_id=workspace_id,
        paths=tmp_foundry,
    )
    ingest_source(
        "evidence-2.txt",
        run_id=run_id,
        title="Second Evidence",
        sensitivity="personal",
        content=f"Evidence content unique to {workspace_id} run {run_id}, item two.",
        assertion_registry_workspace_id=workspace_id,
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)
    materializer = AssertionMaterializer(workspace_id=workspace_id, paths=tmp_foundry)
    result = materializer.materialize_run(run_id)
    assert result.status == "materialized"
    assert len(result.assertion_ids) == 2
    _write_run_yaml(tmp_foundry, run_id, workspace_id=workspace_id)


def test_lifecycle_seam_touches_no_cross_workspace_data(tmp_foundry) -> None:
    """RPC-6.3: reconciling workspace-a's blocked assertion never enumerates,
    reads, or writes anything under a second workspace's registry, even when
    that workspace has its own structurally-similar inference record."""

    run_id = "rf_run_rpc63_ws_a"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")
    inf_claim = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001"])
    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    inf = inferencer.materialize_inference(run_id, inf_claim, producer="agent-research-1")
    assert inf.status == "materialized"

    other_workspace = "workspace-b"
    other_run_id = "rf_run_rpc63_ws_b"
    _setup_distinct_run_with_two_supported_claims(tmp_foundry, other_run_id, workspace_id=other_workspace)
    other_ref = _assertion_ref(tmp_foundry, other_run_id, "clm_001")
    other_inf_claim = _append_inference_claim(tmp_foundry, other_run_id, from_claims=["clm_001"])
    other_inferencer = AssertionInferenceMaterializer(workspace_id=other_workspace, paths=tmp_foundry)
    other_inf = other_inferencer.materialize_inference(other_run_id, other_inf_claim, producer="agent-research-1")
    assert other_inf.status == "materialized"
    assert other_inf.inference_id != inf.inference_id  # distinct content -> distinct ids, a real isolation check
    other_root = AssertionRegistry(workspace_id=other_workspace, paths=tmp_foundry).root
    other_snapshot_before = {
        path.relative_to(other_root) for path in other_root.rglob("*") if path.is_file()
    }

    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion = load_yaml(reconciler.root / "assertions" / f"{ref_a['assertion_id']}.yaml")
    event_id = "evt_rpc63_cross_ws"
    dump_yaml(_lifecycle_event(assertion, event_id), reconciler.event_path(event_id))

    result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert (result.status, result.action_count) == ("completed", 1)
    manifest = json.loads(reconciler.manifest_path(event_id).read_text(encoding="utf-8"))
    assert {item["object_id"] for item in manifest["expected_objects"]} == {inf.inference_id}
    assert other_inf.inference_id not in {item["object_id"] for item in manifest["expected_objects"]}
    assert other_ref["assertion_id"] != ref_a["assertion_id"]

    # workspace-b's registry gained not a single file from workspace-a's
    # reconciliation.
    other_snapshot_after = {
        path.relative_to(other_root) for path in other_root.rglob("*") if path.is_file()
    }
    assert other_snapshot_after == other_snapshot_before
    assert load_yaml(other_root / "inferences" / f"{other_inf.inference_id}.yaml")["status"] == "active"


# ---------------------------------------------------------------------------
# RPC-6.4 -- lifecycle adversarial matrix for the manifest-authoring seam
# ---------------------------------------------------------------------------


def _one_affected_inference_fixture(tmp_foundry, run_id: str):
    """Real, minimal fixture: one source assertion with exactly one affected
    (active) inference, for the merge-seam adversarial tests below."""

    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")
    inf_claim = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001"])
    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    inf = inferencer.materialize_inference(run_id, inf_claim, producer="agent-research-1")
    assert inf.status == "materialized"
    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion = load_yaml(reconciler.root / "assertions" / f"{ref_a['assertion_id']}.yaml")
    return reconciler, ref_a, inf, assertion


def test_manifest_merge_conflicting_entry_fails_closed(tmp_foundry) -> None:
    """RPC-6.4: a pre-existing manifest entry that shares a canonical
    dependent's ``(object_id, object_class)`` key but does not match it
    byte-for-byte is a genuine identity conflict -- fail closed, never a
    silent overwrite of the differing entry."""

    reconciler, ref_a, inf, assertion = _one_affected_inference_fixture(tmp_foundry, "rf_run_rpc64_conflict")
    event_id = "evt_rpc64_conflict"
    dump_yaml(_lifecycle_event(assertion, event_id), reconciler.event_path(event_id))
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text(
        json.dumps(
            {
                "expected_objects": [
                    {
                        "object_id": inf.inference_id,
                        "object_class": "inference",
                        "action": "mark_stale",
                        "unexpected_extra_field": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert result.status == "blocked"
    receipt = load_yaml(result.receipt_path)
    assert receipt["reason_code"] == "dependency_manifest_conflict"
    assert receipt["actions"] == []


def test_manifest_merge_preserves_legacy_entries(tmp_foundry) -> None:
    """RPC-6.4: a pre-existing (legacy-shaped) manifest entry that does NOT
    collide with any canonical dependent is preserved, not discarded, by the
    merge -- the seam is additive-only."""

    reconciler, ref_a, inf, assertion = _one_affected_inference_fixture(tmp_foundry, "rf_run_rpc64_legacy")
    event_id = "evt_rpc64_legacy"
    dump_yaml(_lifecycle_event(assertion, event_id), reconciler.event_path(event_id))
    legacy_entry = {"object_id": "sed_" + "a" * 64, "object_class": "source_edition", "action": "block_reuse"}
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text(
        json.dumps({"expected_objects": [legacy_entry]}), encoding="utf-8"
    )

    result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert (result.status, result.action_count) == ("completed", 2)
    manifest = json.loads(reconciler.manifest_path(event_id).read_text(encoding="utf-8"))
    assert {(item["object_id"], item["object_class"]) for item in manifest["expected_objects"]} == {
        (inf.inference_id, "inference"),
        (legacy_entry["object_id"], "source_edition"),
    }
    receipt = load_yaml(result.receipt_path)
    assert {(a["object_id"], a["object_class"]) for a in receipt["actions"]} == {
        (inf.inference_id, "inference"),
        (legacy_entry["object_id"], "source_edition"),
    }


def test_manifest_merge_malformed_existing_manifest_fails_closed(tmp_foundry) -> None:
    """RPC-6.4: a malformed pre-existing manifest (``expected_objects`` is
    not a list) is caught by the merge seam itself -- before
    ``_load_manifest`` ever runs -- with the SAME typed reason code
    ``_load_manifest``'s own malformed-manifest case already uses."""

    reconciler, ref_a, _inf, assertion = _one_affected_inference_fixture(tmp_foundry, "rf_run_rpc64_malformed")
    event_id = "evt_rpc64_malformed"
    dump_yaml(_lifecycle_event(assertion, event_id), reconciler.event_path(event_id))
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text(
        json.dumps({"expected_objects": "not-a-list"}), encoding="utf-8"
    )

    result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert result.status == "blocked"
    receipt = load_yaml(result.receipt_path)
    assert receipt["reason_code"] == "dependency_manifest_invalid"
    assert receipt["actions"] == []


def test_lifecycle_seam_repair_path_converges_after_manifest_fix(tmp_foundry) -> None:
    """RPC-6.4 repair path: a blocked receipt caused by a malformed manifest
    is NOT sticky.  Fixing the manifest on disk and calling ``reconcile``
    again re-derives the receipt and converges to completion, because a
    persisted ``blocked`` receipt (unlike ``pending``/``completed``, whose
    ``actions`` always start empty) always re-triggers ``_new_receipt``."""

    reconciler, ref_a, inf, assertion = _one_affected_inference_fixture(tmp_foundry, "rf_run_rpc64_repair")
    event_id = "evt_rpc64_repair"
    dump_yaml(_lifecycle_event(assertion, event_id), reconciler.event_path(event_id))
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text(
        json.dumps({"expected_objects": "not-a-list"}), encoding="utf-8"
    )

    blocked_result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert blocked_result.status == "blocked"
    assert load_yaml(blocked_result.receipt_path)["reason_code"] == "dependency_manifest_invalid"

    # Repair: remove the malformed manifest so the seam re-authors it fresh
    # from the still-real, still-affected canonical dependent.
    reconciler.manifest_path(event_id).unlink()

    repaired_result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert (repaired_result.status, repaired_result.action_count) == ("completed", 1)
    repaired_receipt = load_yaml(repaired_result.receipt_path)
    assert repaired_receipt.get("reason_code") is None
    assert {(a["object_id"], a["object_class"], a["status"]) for a in repaired_receipt["actions"]} == {
        (inf.inference_id, "inference", "completed")
    }

    # Converges: a further call reproduces the exact same completed receipt.
    assert reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id) == repaired_result


# ---------------------------------------------------------------------------
# F18 (RPC-6.G validator, N7) -- effective-status reader P4/P5 must consult
# ---------------------------------------------------------------------------


def test_collect_stale_object_ids_reflects_a_real_p6_mark_stale_flow(tmp_foundry) -> None:
    """F18: drives a REAL lifecycle event through ``reconcile()`` -- never a
    hand-authored ``status: stale`` -- and proves ``collect_stale_object_ids``
    (the reader P4's commit recheck and P5's catalog lineage both now
    consult) reflects exactly the completed ``mark_stale`` effects: empty
    before any impact state exists (legacy parity), excludes a still-pending
    action, and includes every object once ``reconcile`` completes -- while
    the underlying inference/canonical-claim records stay immutable on disk
    (N7)."""

    run_id = "rf_run_f18_stale_ids"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    inf1_claim = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001"])
    inf1 = inferencer.materialize_inference(run_id, inf1_claim, producer="agent-research-1")
    assert inf1.status == "materialized"

    ccl_materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    ccl1_claim = _append_canonical_candidate_claim(tmp_foundry, run_id, text="Direct citation of A.")
    ccl1 = ccl_materializer.publish_canonical_claim(
        run_id, ccl1_claim, statement="Direct citation of A.", source_assertion_refs=[ref_a], explicit_request=True
    )
    assert ccl1.status == "materialized"

    r1 = _write_report_use(
        tmp_foundry,
        report_id="report_f18_a1",
        cited_ref=build_cited_ref(
            ref_kind="source_assertion", assertion_id=ref_a["assertion_id"], assertion_version=ref_a["assertion_version"]
        ),
    )

    empty = {"inference": frozenset(), "canonical_claim_edge": frozenset(), "report_revision": frozenset()}
    assert collect_stale_object_ids(paths=tmp_foundry, workspace_id=_WORKSPACE) == empty

    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion = load_yaml(reconciler.root / "assertions" / f"{ref_a['assertion_id']}.yaml")
    event_id = "evt_f18_stale_ids"
    dump_yaml(_lifecycle_event(assertion, event_id), reconciler.event_path(event_id))

    # Interrupt after ONE of three actions. Dependents are always processed
    # in `enumerate_impact`'s (object_class, object_id, action) sort order --
    # "canonical_claim_edge" sorts before "inference"/"report_revision" -- so
    # exactly ccl1 is checkpointed as completed; inf1/r1 stay pending and
    # must NOT be reported stale yet.
    with pytest.raises(ImpactInterrupted):
        reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id, _interrupt_after_actions=1)
    partial = collect_stale_object_ids(paths=tmp_foundry, workspace_id=_WORKSPACE)
    assert partial == {
        "inference": frozenset(),
        "canonical_claim_edge": frozenset({ccl1.canonical_claim_id}),
        "report_revision": frozenset(),
    }

    result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert (result.status, result.action_count) == ("completed", 3)

    stale = collect_stale_object_ids(paths=tmp_foundry, workspace_id=_WORKSPACE)
    assert stale == {
        "inference": frozenset({inf1.inference_id}),
        "canonical_claim_edge": frozenset({ccl1.canonical_claim_id}),
        "report_revision": frozenset({r1}),
    }

    # The immutable records themselves are untouched on disk (N7): staleness
    # is visible ONLY through the effect-receipt reader, never a record flip.
    inference_record = load_yaml(reconciler.root / "inferences" / f"{inf1.inference_id}.yaml")
    assert inference_record["status"] == "active"
    canonical_record = load_yaml(
        reconciler.root / "canonical_claims" / ccl1.canonical_claim_id / f"{ccl1.canonical_claim_version}.yaml"
    )
    assert canonical_record["state"] == "active"


def test_collect_stale_object_ids_legacy_workspace_and_absent_workspace_are_empty(tmp_foundry) -> None:
    """Legacy parity: a workspace P6 has never touched, and a workspace that
    does not exist at all, both yield the same all-empty mapping -- never a
    raised error."""

    empty = {"inference": frozenset(), "canonical_claim_edge": frozenset(), "report_revision": frozenset()}
    assert collect_stale_object_ids(paths=tmp_foundry, workspace_id=_WORKSPACE) == empty
    assert collect_stale_object_ids(paths=tmp_foundry, workspace_id="workspace-never-seen") == empty
    assert collect_stale_object_ids(paths=tmp_foundry, workspace_id="  ") == empty


# ---------------------------------------------------------------------------
# F19 (RPC-6.G validator, Karen K-1, HIGH) -- effective_source_assertion_
# lifecycle_state: the ONE reader for a DIRECTLY-cited source assertion's
# authoritative block boundary, symmetric to F18's collect_stale_object_ids.
# ---------------------------------------------------------------------------


def test_effective_source_assertion_lifecycle_state_legacy_no_policy_file_is_eligible(tmp_foundry) -> None:
    """Legacy parity (AC RPC-8): a workspace/assertion P6 has never touched --
    no ``lifecycle_policy/<id>.yaml`` at all -- is ``"eligible"``, byte-
    identical to before this function existed."""

    run_id = "rf_run_f19_legacy"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")
    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assert not (reconciler.root / "lifecycle_policy" / f"{ref_a['assertion_id']}.yaml").exists()

    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_a["assertion_id"])
        == SOURCE_ASSERTION_ELIGIBLE
    )


def test_effective_source_assertion_lifecycle_state_reflects_a_real_p6_block(tmp_foundry) -> None:
    """F19: drives a REAL lifecycle event through ``reconcile()`` -- never a
    hand-authored ``lifecycle_state: blocked`` -- and proves the effective
    reader reports ``"blocked"`` even though the immutable
    ``assertions/<id>.yaml`` record's own ``lifecycle_state`` never flips
    (``AssertionImpactReconciler.reconcile``'s own "immutable source
    assertion is never overwritten" rule)."""

    run_id = "rf_run_f19_real_block"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")
    ref_b = _assertion_ref(tmp_foundry, run_id, "clm_002")

    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion = load_yaml(reconciler.root / "assertions" / f"{ref_a['assertion_id']}.yaml")
    event_id = "evt_f19_real_block"
    dump_yaml(_lifecycle_event(assertion, event_id), reconciler.event_path(event_id))
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text(json.dumps({"expected_objects": []}), encoding="utf-8")
    result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert result.status == "completed"

    # The immutable record itself is untouched -- Karen's exact repro relies
    # on a naive raw-record-only recheck seeing this and letting a new
    # citation through.
    assert load_yaml(reconciler.root / "assertions" / f"{ref_a['assertion_id']}.yaml")["lifecycle_state"] == "eligible"

    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_a["assertion_id"])
        == SOURCE_ASSERTION_BLOCKED
    )
    # An unrelated, never-blocked sibling assertion is unaffected.
    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_b["assertion_id"])
        == SOURCE_ASSERTION_ELIGIBLE
    )


def test_effective_source_assertion_lifecycle_state_present_but_invalid_policy(tmp_foundry) -> None:
    """K-2 (Karen Wave-3 gate, MEDIUM): a ``lifecycle_policy/<id>.yaml`` file
    that IS PRESENT but does not validate (malformed shape, wrong
    ``assertion_id``, or an unknown ``invalidation_state``) is reported as
    ``"policy_invalid"`` -- deliberately distinct from ``"eligible"`` so a
    caller never silently treats a corrupt authority artifact as unblocked."""

    run_id = "rf_run_f19_invalid_policy"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")
    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    policy_path = reconciler.policy_path(ref_a["assertion_id"])
    policy_path.parent.mkdir(parents=True, exist_ok=True)

    # Present, parses as YAML, but is not even shaped like a policy record.
    dump_yaml({"unexpected": "shape"}, policy_path)
    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_a["assertion_id"])
        == SOURCE_ASSERTION_POLICY_INVALID
    )

    # Present, correctly typed, but an inconsistent invalidation_state.
    dump_yaml(
        {
            "schema_version": "1.0",
            "type": "assertion_lifecycle_policy_state",
            "assertion_id": ref_a["assertion_id"],
            "assertion_version": 1,
            "lifecycle_state": "eligible",
            "invalidation_state": "unknown_state",
            "invalidation_event_id": None,
        },
        policy_path,
    )
    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_a["assertion_id"])
        == SOURCE_ASSERTION_POLICY_INVALID
    )

    # Present, unreadable YAML content entirely.
    policy_path.write_text(":\n  - not: [valid", encoding="utf-8")
    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_a["assertion_id"])
        == SOURCE_ASSERTION_POLICY_INVALID
    )


def test_effective_source_assertion_lifecycle_state_one_field_tamper_on_a_real_block_is_policy_invalid(
    tmp_foundry,
) -> None:
    """SOL-37 (CRITICAL) repro: drive a REAL P6 block via ``reconcile()``,
    then flip ONLY ``invalidation_state`` from ``"blocked"`` to ``"active"``
    on disk, leaving the REAL ``lifecycle_state: blocked`` and the REAL
    ``invalidation_event_id`` untouched. The loose 3-field active-branch
    check this closes would have read this as ``"eligible"`` -- a fully
    hardened reader must reject it as ``"policy_invalid"`` instead (never
    silently un-block)."""

    run_id = "rf_run_f19_sol37_tamper"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")

    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion = load_yaml(reconciler.root / "assertions" / f"{ref_a['assertion_id']}.yaml")
    event_id = "evt_f19_sol37_tamper"
    dump_yaml(_lifecycle_event(assertion, event_id), reconciler.event_path(event_id))
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text(json.dumps({"expected_objects": []}), encoding="utf-8")
    result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert result.status == "completed"

    policy_path = reconciler.policy_path(ref_a["assertion_id"])
    policy = load_yaml(policy_path)
    assert policy["invalidation_state"] == "blocked"
    assert policy["lifecycle_state"] == "blocked"
    real_event_id = policy["invalidation_event_id"]
    assert isinstance(real_event_id, str) and real_event_id

    tampered = dict(policy)
    tampered["invalidation_state"] = "active"  # the ONE field flipped
    # lifecycle_state and invalidation_event_id are DELIBERATELY left as the
    # real blocked values -- this is the exact attack shape.
    dump_yaml(tampered, policy_path)

    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_a["assertion_id"])
        == SOURCE_ASSERTION_POLICY_INVALID
    )


def test_effective_source_assertion_lifecycle_state_tampered_schema_version_on_active_policy_is_policy_invalid(
    tmp_foundry,
) -> None:
    """SOL-37 PARTIAL closure: the active-branch validator previously
    checked neither ``schema_version`` nor ``assertion_version`` even though
    the writer (``AssertionImpactReconciler._load_policy``'s no-path-exists
    branch) always emits both. A policy file whose ``schema_version``
    disagrees with the one value the writer ever emits must be
    ``"policy_invalid"``, never silently accepted as ``"eligible"``."""

    run_id = "rf_run_f19_sol37_schema_version_tamper"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")
    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    policy_path = reconciler.policy_path(ref_a["assertion_id"])
    policy_path.parent.mkdir(parents=True, exist_ok=True)

    dump_yaml(
        {
            "schema_version": "2.0",  # tampered: the writer only ever emits "1.0"
            "type": "assertion_lifecycle_policy_state",
            "assertion_id": ref_a["assertion_id"],
            "assertion_version": 1,
            "lifecycle_state": "eligible",
            "invalidation_state": "active",
            "invalidation_event_id": None,
        },
        policy_path,
    )
    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_a["assertion_id"])
        == SOURCE_ASSERTION_POLICY_INVALID
    )


def test_effective_source_assertion_lifecycle_state_tampered_or_missing_assertion_version_on_active_policy_is_policy_invalid(
    tmp_foundry,
) -> None:
    """SOL-37 PARTIAL closure: an ``assertion_version`` that is missing,
    non-integer, a bool, or non-positive -- never the positive-int shape the
    writer emits -- must ALSO be ``"policy_invalid"``; the active branch
    previously ignored this field entirely. A genuinely valid value is
    proven to still be accepted (control case)."""

    run_id = "rf_run_f19_sol37_assertion_version_tamper"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")
    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    policy_path = reconciler.policy_path(ref_a["assertion_id"])
    policy_path.parent.mkdir(parents=True, exist_ok=True)

    base = {
        "schema_version": "1.0",
        "type": "assertion_lifecycle_policy_state",
        "assertion_id": ref_a["assertion_id"],
        "lifecycle_state": "eligible",
        "invalidation_state": "active",
        "invalidation_event_id": None,
    }

    # Missing entirely.
    dump_yaml(dict(base), policy_path)
    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_a["assertion_id"])
        == SOURCE_ASSERTION_POLICY_INVALID
    )

    # Wrong type (string, not int).
    dump_yaml({**base, "assertion_version": "1"}, policy_path)
    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_a["assertion_id"])
        == SOURCE_ASSERTION_POLICY_INVALID
    )

    # Boolean (a bool is an int subclass in Python -- must be explicitly
    # rejected, mirroring this module's existing convention elsewhere for
    # the same field, e.g. ``block_authoritative_reuse``'s own
    # ``assertion_version`` guard).
    dump_yaml({**base, "assertion_version": True}, policy_path)
    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_a["assertion_id"])
        == SOURCE_ASSERTION_POLICY_INVALID
    )

    # Non-positive.
    dump_yaml({**base, "assertion_version": 0}, policy_path)
    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_a["assertion_id"])
        == SOURCE_ASSERTION_POLICY_INVALID
    )

    # Genuinely valid value is still accepted (proves the guard isn't
    # accidentally rejecting everything).
    dump_yaml({**base, "assertion_version": 1}, policy_path)
    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_a["assertion_id"])
        == SOURCE_ASSERTION_ELIGIBLE
    )


def test_effective_source_assertion_lifecycle_state_symlinked_policy_path_is_policy_invalid(
    tmp_foundry,
) -> None:
    """SOL-37: a non-regular (symlinked) policy path is ``policy_invalid``,
    never folded into "no policy yet" the way a genuinely-absent file is."""

    run_id = "rf_run_f19_sol37_symlink"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")
    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)

    policy_path = reconciler.policy_path(ref_a["assertion_id"])
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    outside_target = tmp_foundry.root / "outside_policy_escape_target.yaml"
    dump_yaml(
        {
            "schema_version": "1.0",
            "type": "assertion_lifecycle_policy_state",
            "assertion_id": ref_a["assertion_id"],
            "assertion_version": 1,
            "lifecycle_state": "eligible",
            "invalidation_state": "active",
            "invalidation_event_id": None,
        },
        outside_target,
    )
    policy_path.symlink_to(outside_target)
    assert policy_path.is_symlink()

    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_a["assertion_id"])
        == SOURCE_ASSERTION_POLICY_INVALID
    )


# ---------------------------------------------------------------------------
# SOL-40 (HIGH, gate-blocking) -- a failed derived-cache purge must fail
# reconcile() closed and be retried, never be permanently skipped once the
# policy already reads as blocked.
# ---------------------------------------------------------------------------


def test_reconcile_retries_a_failed_derived_cache_purge_instead_of_permanently_skipping_it(
    tmp_foundry, monkeypatch
) -> None:
    """SOL-40 repro/closure: inject a one-time ``OSError`` into
    ``purge_lifecycle_derived_file``. The FIRST ``reconcile()`` call must
    fail closed with a durable, typed blocked receipt -- never silently
    swallow the purge failure and complete while leaving a stale catalog
    projection behind. A RETRY (no injected fault) must re-attempt the
    purge -- previously the freshly-reloaded policy already equalled
    ``blocked`` so the purge was gated on the transition alone and was
    never revisited -- and this time succeed, letting reconciliation
    actually complete and the stale projection actually be removed."""

    from research_foundry.services import catalog_service
    from research_foundry.services.assertion_catalog import AssertionCatalog

    run_id = "rf_run_f19_sol40_purge_retry"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")

    catalog = AssertionCatalog(tmp_foundry)
    projection_path = catalog.projection_path(_WORKSPACE)
    projection_path.parent.mkdir(parents=True, exist_ok=True)
    projection_path.write_text("stale-projection-stub", encoding="utf-8")
    assert projection_path.exists()

    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion = load_yaml(reconciler.root / "assertions" / f"{ref_a['assertion_id']}.yaml")
    event_id = "evt_f19_sol40_purge_retry"
    dump_yaml(_lifecycle_event(assertion, event_id), reconciler.event_path(event_id))
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text(json.dumps({"expected_objects": []}), encoding="utf-8")

    real_purge = catalog_service.purge_lifecycle_derived_file
    calls = {"count": 0}

    def _flaky_purge(path, *, lifecycle_state):
        calls["count"] += 1
        if calls["count"] == 1:
            raise OSError("injected SOL-40 repro fault")
        return real_purge(path, lifecycle_state=lifecycle_state)

    monkeypatch.setattr(catalog_service, "purge_lifecycle_derived_file", _flaky_purge)

    # First call: the injected fault must fail THIS call closed, never
    # silently swallow it and complete.
    result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert result.status == "blocked"
    receipt = load_yaml(result.receipt_path)
    assert receipt["reason_code"] == "derived_cache_purge_failed"
    assert calls["count"] == 1
    # The stale projection is STILL present -- the purge genuinely failed,
    # never partially/silently applied.
    assert projection_path.exists()
    # The policy itself is durably blocked regardless (the honest, bounded
    # limitation this module already documents elsewhere: the immutable
    # source assertion's authoritative reuse boundary and the DERIVED-cache
    # invalidation are deliberately separate concerns) -- only completion
    # of reconciliation itself is gated on a successful purge.
    policy = load_yaml(reconciler.policy_path(ref_a["assertion_id"]))
    assert policy["invalidation_state"] == "blocked"
    assert (
        effective_source_assertion_lifecycle_state(root=reconciler.root, assertion_id=ref_a["assertion_id"])
        == SOURCE_ASSERTION_BLOCKED
    )

    # Retry with no injected fault: the purge is re-attempted (never
    # permanently skipped merely because the reloaded policy already reads
    # as blocked) and this time succeeds, letting reconciliation actually
    # complete.
    retry_result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert retry_result.status == "completed"
    assert calls["count"] == 2
    assert not projection_path.exists()


# ---------------------------------------------------------------------------
# K-2 (Karen Wave-3 gate, MEDIUM) -- collect_stale_object_ids split posture:
# a present-but-invalid receipt degrades+warns on read, fails closed on
# strict (commit-time) use.
# ---------------------------------------------------------------------------


def _reconcile_with_empty_manifest(tmp_foundry, *, assertion_id: str, event_id: str):
    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion = load_yaml(reconciler.root / "assertions" / f"{assertion_id}.yaml")
    dump_yaml(_lifecycle_event(assertion, event_id), reconciler.event_path(event_id))
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text(json.dumps({"expected_objects": []}), encoding="utf-8")
    result = reconciler.reconcile(assertion_id=assertion_id, event_id=event_id)
    assert result.status == "completed"
    return reconciler


def test_collect_stale_object_ids_read_path_degrades_with_a_logged_warning_on_corrupt_receipt(
    tmp_foundry, caplog
) -> None:
    """K-2: a receipt file PRESENT under ``impact_operations/`` that fails to
    validate is a DIFFERENT signal than a workspace P6 has simply never
    touched. The default (``strict=False``, read/catalog) posture degrades
    it out of the stale set exactly as before (never a 500, V5-1) but now
    MUST log a warning so the corruption is observable -- not a silent skip."""

    run_id = "rf_run_f19_k2_read"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")
    reconciler = _reconcile_with_empty_manifest(
        tmp_foundry, assertion_id=ref_a["assertion_id"], event_id="evt_f19_k2_read"
    )
    reconciler.receipt_path("evt_f19_k2_read").write_text(
        json.dumps({"not": "a-valid-receipt"}), encoding="utf-8"
    )

    with caplog.at_level("WARNING", logger="research_foundry.services.assertion_impact"):
        stale = collect_stale_object_ids(paths=tmp_foundry, workspace_id=_WORKSPACE)

    assert stale == {"inference": frozenset(), "canonical_claim_edge": frozenset(), "report_revision": frozenset()}
    assert any("degrading to non-stale for read" in message for message in caplog.messages)


def test_collect_stale_object_ids_strict_fails_closed_on_the_same_corrupt_receipt(tmp_foundry) -> None:
    """K-2: ``strict=True`` -- the COMMIT-path posture -- reverses the read
    path's degrade: the IDENTICAL corrupt receipt raises instead of being
    silently skipped."""

    run_id = "rf_run_f19_k2_strict"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")
    reconciler = _reconcile_with_empty_manifest(
        tmp_foundry, assertion_id=ref_a["assertion_id"], event_id="evt_f19_k2_strict"
    )
    reconciler.receipt_path("evt_f19_k2_strict").write_text(
        json.dumps({"not": "a-valid-receipt"}), encoding="utf-8"
    )

    with pytest.raises(ImpactOperationError, match="impact_receipt_invalid"):
        collect_stale_object_ids(paths=tmp_foundry, workspace_id=_WORKSPACE, strict=True)
