"""P4 assertion projection: rebuild, scope, pagination, and denial coverage."""

from __future__ import annotations

from hashlib import sha256

import pytest

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.frontmatter import dump_md, load_md
from research_foundry.services import claim_mapping, extraction
from research_foundry.services.assertion_catalog import (
    AssertionCatalog,
    AssertionCatalogUnavailable,
)
from research_foundry.services.assertion_impact import AssertionImpactReconciler
from research_foundry.services.assertion_inference import AssertionInferenceMaterializer
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.assertion_report_use import (
    ReportAssertionUseService,
    attest_verification_pass,
    build_report_ref,
)
from research_foundry.services.canonical_claim_materialization import CanonicalClaimMaterializer
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml


def _materialize(tmp_foundry, run_id: str, workspace_id: str, content: str) -> str:
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        f"{run_id}.txt",
        run_id=run_id,
        title=f"Evidence {run_id}",
        sensitivity="personal",
        content=content,
        assertion_registry_workspace_id=workspace_id,
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)
    result = AssertionMaterializer(workspace_id=workspace_id, paths=tmp_foundry).materialize_run(run_id)
    assert result.status == "materialized"
    return result.assertion_ids[0]


# ---------------------------------------------------------------------------
# RPC-5.1: activity/lineage projections (origin/run facets, search-only
# discovery, report uses, inference lineage, canonical-claim lineage)
# ---------------------------------------------------------------------------


def _setup_full_lineage(tmp_foundry, *, workspace_id: str = "workspace-a") -> dict[str, object]:
    """Build one run with two materialized source assertions, an inference
    citing both, a canonical claim citing the first assertion directly AND
    the inference indirectly, and a published report_assertion_use citing
    the first assertion directly. Mirrors the fixture shape
    ``test_assertion_inference.py``/``test_canonical_claim_materialization.py``/
    ``test_assertion_report_use.py`` each already establish.
    """

    run_id = "rf_run_p5_lineage"
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {
        "ledger_write_enabled": True,
        "canonical_claims_enabled": True,
    }
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        "evidence-1.txt", run_id=run_id, title="First Evidence", sensitivity="personal",
        content="Pediatric neutrophil counts trend lower than adult reference ranges.",
        assertion_registry_workspace_id=workspace_id, paths=tmp_foundry,
    )
    ingest_source(
        "evidence-2.txt", run_id=run_id, title="Second Evidence", sensitivity="personal",
        content="Pediatric lymphocyte counts trend higher than adult reference ranges.",
        assertion_registry_workspace_id=workspace_id, paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)
    materializer = AssertionMaterializer(workspace_id=workspace_id, paths=tmp_foundry)
    result = materializer.materialize_run(run_id)
    assert result.status == "materialized"
    assert len(result.assertion_ids) == 2
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

    ledger_path = tmp_foundry.run_paths(run_id).claim_ledger
    ledger = load_yaml(ledger_path)
    inf_claim_id = f"clm_{len(ledger['claims']) + 1:03d}"
    ledger["claims"].append(
        {
            "claim_id": inf_claim_id,
            "text": "Pediatric CBC reference intervals differ from adult intervals.",
            "materiality": "material",
            "claim_type": "comparative",
            "status": "inference",
            "confidence": "medium",
            "sources": [],
            "inference_basis": {
                "from_claims": ["clm_001", "clm_002"],
                "reasoning_summary": "Synthesized across two source assertions.",
            },
            "report_locations": [],
            "reviewer_notes": "",
        }
    )
    dump_yaml(ledger, ledger_path)
    inferencer = AssertionInferenceMaterializer(workspace_id=workspace_id, paths=tmp_foundry)
    inf_result = inferencer.materialize_inference(run_id, inf_claim_id, producer="agent-research-1")
    assert inf_result.status == "materialized"

    ledger = load_yaml(ledger_path)
    ccl_claim_id = f"clm_{len(ledger['claims']) + 1:03d}"
    ledger["claims"].append(
        {
            "claim_id": ccl_claim_id,
            "text": "Pediatric CBC reference intervals differ from adult intervals.",
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
    canonical = CanonicalClaimMaterializer(workspace_id=workspace_id, paths=tmp_foundry)
    ccl_result = canonical.publish_canonical_claim(
        run_id,
        ccl_claim_id,
        statement="Pediatric CBC reference intervals differ from adult intervals.",
        source_assertion_refs=[
            {"assertion_id": result.assertion_ids[0], "assertion_version": 1, "relation": "supports"}
        ],
        inference_refs=[
            {
                "inference_id": inf_result.inference_id,
                "inference_version": inf_result.inference_version,
                "relation": "supports",
            }
        ],
        explicit_request=True,
    )
    assert ccl_result.status == "materialized"

    report_service = ReportAssertionUseService(workspace_id=workspace_id, paths=tmp_foundry)
    # K-FINAL-1: attestation must be established through the real public
    # entry point (a genuine report file + attest_verification_pass), never
    # the module/class-private writer, so this fixture exercises the same
    # trust boundary a real caller would.
    report_path = tmp_foundry.root / "reports" / "report_p5_lineage.md"
    dump_md({"schema_version": "1.0"}, "genuine report body for P5 lineage", report_path)
    _, report_body = load_md(report_path)
    report_digest = sha256(report_body.encode("utf-8")).hexdigest()
    report_ref = build_report_ref(report_id="report_p5_lineage", report_content_digest=report_digest)
    attest_verification_pass(
        workspace_id=workspace_id,
        report_id="report_p5_lineage",
        report_content_digest=report_digest,
        verified_at="2026-07-28T12:00:00Z",
        report_path=report_path,
        paths=tmp_foundry,
    )
    outcome = report_service.prepare_report_assertion_use(
        report_ref=report_ref,
        persistent_references={"source_assertion_id": result.assertion_ids[0], "assertion_version": 1},
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome.status == "prepared"
    status, _record = report_service.publish(outcome.record)
    assert status == "published"

    return {
        "workspace_id": workspace_id,
        "assertion_ids": result.assertion_ids,
        "inference_id": inf_result.inference_id,
        "inference_version": inf_result.inference_version,
        "canonical_claim_id": ccl_result.canonical_claim_id,
        "canonical_claim_version": ccl_result.canonical_claim_version,
        "use_id": outcome.use_id,
    }


def test_packet_surfaces_direct_report_use_and_lineage(tmp_foundry) -> None:
    fixture = _setup_full_lineage(tmp_foundry)
    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("alice", fixture["workspace_id"], ("researcher",))
    catalog.rebuild(fixture["workspace_id"])

    packet = catalog.packet(fixture["assertion_ids"][0], identity=identity)
    assert packet is not None
    assert packet["report_uses"] == [fixture["use_id"]]
    assert packet["inference_lineage"] == [
        {
            "inference_id": fixture["inference_id"],
            "inference_version": fixture["inference_version"],
            "status": "active",
            "report_uses": [],
        }
    ]
    assert packet["canonical_claim_lineage"] == [
        {
            "canonical_claim_id": fixture["canonical_claim_id"],
            "canonical_claim_version": fixture["canonical_claim_version"],
            "state": "active",
            "report_uses": [],
        }
    ]
    assert packet["run_facets"] == {"rf_run_p5_lineage": None}
    assert packet["search_activity_ids"] == []

    # The second assertion feeds the canonical claim only INDIRECTLY -- the
    # claim's own direct `source_assertion_refs` names only the first
    # assertion, but its `inference_refs` cites the inference, and that
    # inference's `source_assertion_refs` names BOTH assertions. Indirect
    # lineage widens `canonical_claim_lineage` to the second assertion too
    # (never removes the direct-only distinction: `report_uses` stays [],
    # since the report-use record cited the FIRST assertion only).
    second_packet = catalog.packet(fixture["assertion_ids"][1], identity=identity)
    assert second_packet is not None
    assert second_packet["report_uses"] == []
    assert [entry["inference_id"] for entry in second_packet["inference_lineage"]] == [fixture["inference_id"]]
    assert [entry["canonical_claim_id"] for entry in second_packet["canonical_claim_lineage"]] == [
        fixture["canonical_claim_id"]
    ]


def test_lineage_endpoint_exposes_the_same_activity_and_lineage_fields(tmp_foundry) -> None:
    fixture = _setup_full_lineage(tmp_foundry)
    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("alice", fixture["workspace_id"], ("researcher",))
    catalog.rebuild(fixture["workspace_id"])

    lineage = catalog.lineage(fixture["assertion_ids"][0], identity=identity)
    assert lineage is not None
    assert lineage["report_uses"] == [fixture["use_id"]]
    assert lineage["canonical_claim_lineage"][0]["canonical_claim_id"] == fixture["canonical_claim_id"]
    assert lineage["run_facets"] == {"rf_run_p5_lineage": None}
    assert lineage["search_activity_ids"] == []
    assert catalog.lineage_read_only(fixture["assertion_ids"][0], identity=identity) == lineage


def test_denied_candidate_exposes_no_derived_lineage_values(tmp_foundry) -> None:
    """AC RPC-5 resilience: a denied candidate exposes no derived values --
    even when real inference/canonical/report-use records exist for it."""

    fixture = _setup_full_lineage(tmp_foundry)
    catalog = AssertionCatalog(tmp_foundry)
    other_identity = AuthIdentity("mallory", "workspace-other", ("viewer",))
    catalog.rebuild(fixture["workspace_id"])

    assert catalog.packet(fixture["assertion_ids"][0], identity=other_identity) is None
    assert catalog.lineage(fixture["assertion_ids"][0], identity=other_identity) is None


def test_lineage_delete_rebuild_parity_with_full_activity_and_lineage(tmp_foundry) -> None:
    fixture = _setup_full_lineage(tmp_foundry)
    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("alice", fixture["workspace_id"], ("researcher",))

    first = catalog.rebuild(fixture["workspace_id"])
    before = catalog.packet(fixture["assertion_ids"][0], identity=identity)
    first.projection_path.unlink()
    second = catalog.rebuild(fixture["workspace_id"])
    after = catalog.packet(fixture["assertion_ids"][0], identity=identity)

    assert second.catalog_generation_id == first.catalog_generation_id
    assert after == before


# ---------------------------------------------------------------------------
# F18 (RPC-6.G validator, N7) -- lineage reflects P6's effective status
# ---------------------------------------------------------------------------


def test_lineage_reflects_a_real_p6_mark_stale_effect(tmp_foundry) -> None:
    """F18: ``inference_lineage``/``canonical_claim_lineage`` project P6's
    effective-status verdict (a completed ``mark_stale`` effect receipt), not
    the raw, never-mutated ``inference_record``/``canonical_claim`` fields --
    driven through a REAL ``AssertionImpactReconciler.reconcile()`` flow,
    never a hand-authored ``status``/``state: stale``. ``lineage`` and
    ``lineage_read_only`` project the identical overridden value."""

    fixture = _setup_full_lineage(tmp_foundry)
    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("alice", fixture["workspace_id"], ("researcher",))

    reconciler = AssertionImpactReconciler(workspace_id=fixture["workspace_id"], paths=tmp_foundry)
    blocked_assertion_id = fixture["assertion_ids"][0]
    assertion = load_yaml(reconciler.root / "assertions" / f"{blocked_assertion_id}.yaml")
    event_id = "evt_f18_catalog_stale"
    dump_yaml(
        {
            "schema_version": "1.0",
            "type": "assertion_lifecycle_event",
            "event_id": event_id,
            "sequence": 1,
            "idempotency_key": f"test:{event_id}",
            "occurred_at": "2026-07-28T16:00:00Z",
            "cause": "formal_retraction",
            "target": {
                "kind": "source_assertion",
                "id": blocked_assertion_id,
                "version": assertion["assertion_version"],
            },
            "transition": {"from": "eligible", "to": "invalidated"},
            "authoritative_action": "block_reuse",
            "dependent_actions": [
                {"object_kind": "canonical_claim_edge", "action": "block_reuse"},
                {"object_kind": "inference", "action": "block_reuse"},
                {"object_kind": "report_revision", "action": "block_reuse"},
            ],
        },
        reconciler.event_path(event_id),
    )
    result = reconciler.reconcile(assertion_id=blocked_assertion_id, event_id=event_id)
    assert result.status == "completed"

    # The underlying records are untouched (N7): staleness is recorded ONLY
    # as an effect receipt, never a record mutation.
    inference_record = load_yaml(reconciler.root / "inferences" / f"{fixture['inference_id']}.yaml")
    assert inference_record["status"] == "active"
    canonical_record = load_yaml(
        reconciler.root
        / "canonical_claims"
        / fixture["canonical_claim_id"]
        / f"{fixture['canonical_claim_version']}.yaml"
    )
    assert canonical_record["state"] == "active"

    catalog.rebuild(fixture["workspace_id"])
    # The SECOND assertion feeds both the inference (direct) and the
    # canonical claim (indirect, via the inference) without itself being the
    # blocked assertion -- proving staleness propagates through the lineage
    # projection rather than merely reflecting the blocked assertion's own
    # (untouched) record.
    packet = catalog.packet(fixture["assertion_ids"][1], identity=identity)
    assert packet is not None
    inference_entry = next(
        entry for entry in packet["inference_lineage"] if entry["inference_id"] == fixture["inference_id"]
    )
    assert inference_entry["status"] == "stale"
    canonical_entry = next(
        entry
        for entry in packet["canonical_claim_lineage"]
        if entry["canonical_claim_id"] == fixture["canonical_claim_id"]
    )
    assert canonical_entry["state"] == "stale"

    lineage = catalog.lineage(fixture["assertion_ids"][1], identity=identity)
    assert lineage is not None
    assert lineage["inference_lineage"] == packet["inference_lineage"]
    assert lineage["canonical_claim_lineage"] == packet["canonical_claim_lineage"]
    assert catalog.lineage_read_only(fixture["assertion_ids"][1], identity=identity) == lineage


def test_legacy_assertion_without_provenance_has_empty_optional_lineage_fields(tmp_foundry) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_p5_legacy", "workspace-a", "No provenance lanes touch this fact at all."
    )
    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-a", ("researcher",))
    catalog.rebuild("workspace-a")

    packet = catalog.packet(assertion_id, identity=identity)
    assert packet is not None
    assert packet["report_uses"] == []
    assert packet["inference_lineage"] == []
    assert packet["canonical_claim_lineage"] == []
    assert packet["run_facets"] == {"rf_run_p5_legacy": None}
    assert packet["search_activity_ids"] == []
    lineage = catalog.lineage(assertion_id, identity=identity)
    assert lineage is not None
    assert set(lineage) == {
        "assertion_id", "assertion_version", "relationships", "run_uses", "report_uses",
        "inference_lineage", "canonical_claim_lineage", "run_facets", "search_activity_ids",
        "denial_reason",
    }


def test_projection_delete_rebuild_has_deterministic_search_parity(tmp_foundry) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_p4_rebuild", "workspace-a", "The durable P4 search fact is 42 percent."
    )
    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-a", ("researcher",))

    first = catalog.rebuild("workspace-a")
    before = catalog.search(identity=identity, query="42")
    assert before["items"][0]["assertion_id"] == assertion_id

    first.projection_path.unlink()
    second = catalog.rebuild("workspace-a")
    after = catalog.search(identity=identity, query="42")

    assert second.record_count == first.record_count == 1
    assert after == before


def test_search_scopes_before_facets_and_cursor(tmp_foundry) -> None:
    assertion_a = _materialize(
        tmp_foundry, "rf_run_p4_ws_a", "workspace-a", "Workspace A sees only its own evidence."
    )
    assertion_a_second = _materialize(
        tmp_foundry, "rf_run_p4_ws_a_second", "workspace-a", "Workspace A has a second private fact."
    )
    _materialize(tmp_foundry, "rf_run_p4_ws_b", "workspace-b", "Workspace B must remain private.")
    catalog = AssertionCatalog(tmp_foundry)
    catalog.rebuild("workspace-a")
    catalog.rebuild("workspace-b")

    result = catalog.search(
        identity=AuthIdentity("alice", "workspace-a", ("viewer",)), query="workspace", limit=1
    )

    assert len(result["items"]) == 1
    assert result["facets"] == {"lifecycle_states": ["eligible"], "access_scopes": ["personal"]}
    assert result["next_cursor"] is not None
    next_page = catalog.search(
        identity=AuthIdentity("alice", "workspace-a", ("viewer",)), query="workspace", limit=1,
        cursor=result["next_cursor"],
    )
    assert {result["items"][0]["assertion_id"], next_page["items"][0]["assertion_id"]} == {
        assertion_a, assertion_a_second,
    }
    assert next_page["next_cursor"] is None
    assert catalog.packet(assertion_a, identity=AuthIdentity("bob", "workspace-b", ("viewer",))) is None


def test_missing_rights_context_returns_typed_empty_response(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_p4_rights", "workspace-a", "Missing rights must deny discovery.")
    catalog = AssertionCatalog(tmp_foundry)
    edition_path = next((tmp_foundry.root / "assertion_ledger" / "workspaces").glob("*/sources/*/editions/*.yaml"))
    edition = load_yaml(edition_path)
    edition["metadata_extensions"].pop("allowed_use")
    dump_yaml(edition, edition_path)

    catalog.rebuild("workspace-a")
    result = catalog.search(identity=AuthIdentity("alice", "workspace-a", ("viewer",)))

    assert result == AssertionCatalog.denied_payload("rights_context_missing") or result == {
        "items": [],
        "next_cursor": None,
        "facets": {"lifecycle_states": [], "access_scopes": []},
        "denial_reason": None,
    }
    # The public response has no record-derived counts or membership hints.
    assert result["items"] == []
    assert result["facets"] == {"lifecycle_states": [], "access_scopes": []}


def test_authoritatively_blocked_assertion_is_not_a_current_catalog_result(tmp_foundry) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_p5_blocked", "workspace-a", "Invalid evidence must leave current reads."
    )
    assertion_path = next(
        (tmp_foundry.root / "assertion_ledger" / "workspaces").glob(f"*/assertions/{assertion_id}.yaml")
    )
    assertion = load_yaml(assertion_path)
    assertion["lifecycle_state"] = "blocked"
    dump_yaml(assertion, assertion_path)

    catalog = AssertionCatalog(tmp_foundry)
    catalog.rebuild("workspace-a")
    result = catalog.search(identity=AuthIdentity("alice", "workspace-a", ("viewer",)))

    assert result["items"] == []
    assert result["facets"] == {"lifecycle_states": [], "access_scopes": []}


# ---------------------------------------------------------------------------
# F19 (RPC-6.G validator, Karen K-1, HIGH) -- catalog packet reflects P6's
# effective BLOCK boundary on the assertion itself, not merely its
# dependents' staleness (F18, above).
# ---------------------------------------------------------------------------


def _lifecycle_event_for(assertion_id: str, assertion_version: int, event_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "type": "assertion_lifecycle_event",
        "event_id": event_id,
        "sequence": 1,
        "idempotency_key": f"test:{event_id}",
        "occurred_at": "2026-07-28T16:00:00Z",
        "cause": "formal_retraction",
        "target": {"kind": "source_assertion", "id": assertion_id, "version": assertion_version},
        "transition": {"from": "eligible", "to": "invalidated"},
        "authoritative_action": "block_reuse",
        "dependent_actions": [
            {"object_kind": "canonical_claim_edge", "action": "block_reuse"},
            {"object_kind": "inference", "action": "block_reuse"},
            {"object_kind": "report_revision", "action": "block_reuse"},
        ],
    }


def test_catalog_packet_reflects_a_real_p6_policy_block_on_the_assertion_itself(tmp_foundry) -> None:
    """F19: the catalog packet's own ``lifecycle_state``/
    ``freshness.lifecycle_state`` must project P6's effective block boundary
    (``lifecycle_policy/<id>.yaml``), never the immutable assertion record's
    own, never-mutated field -- driven through a REAL
    ``AssertionImpactReconciler.reconcile()`` flow, mirroring F18's
    ``test_lineage_reflects_a_real_p6_mark_stale_effect`` above but for the
    assertion's OWN authoritative state rather than its dependents'."""

    assertion_id = _materialize(
        tmp_foundry, "rf_run_p5_f19_blocked", "workspace-a", "P6 authoritatively blocks this evidence."
    )
    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-a", ("researcher",))

    reconciler = AssertionImpactReconciler(workspace_id="workspace-a", paths=tmp_foundry)
    assertion = load_yaml(reconciler.root / "assertions" / f"{assertion_id}.yaml")
    event_id = "evt_f19_catalog_blocked"
    dump_yaml(
        _lifecycle_event_for(assertion_id, assertion["assertion_version"], event_id),
        reconciler.event_path(event_id),
    )
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text('{"expected_objects": []}', encoding="utf-8")
    result = reconciler.reconcile(assertion_id=assertion_id, event_id=event_id)
    assert result.status == "completed"

    # The immutable record itself is untouched on disk (same "never
    # mutated" rule F18 pins for inference/canonical-claim staleness).
    assert load_yaml(reconciler.root / "assertions" / f"{assertion_id}.yaml")["lifecycle_state"] == "eligible"

    catalog.rebuild("workspace-a")
    packet = catalog.packet(assertion_id, identity=identity)
    assert packet is not None
    assert packet["lifecycle_state"] == "blocked"
    assert packet["freshness"]["lifecycle_state"] == "blocked"

    # And it drops out of the authorized search surface, same effect the
    # hand-authored-blocked-record test above already pins for the legacy
    # (raw-record) case.
    search_result = catalog.search(identity=identity)
    assert assertion_id not in {item["assertion_id"] for item in search_result["items"]}


def test_catalog_reflects_a_real_p6_block_without_a_manual_rebuild(tmp_foundry) -> None:
    """SOL-38 (HIGH, gate-blocking) repro: PREBUILD the catalog projection
    BEFORE the block (proving a stale projection genuinely exists on disk),
    then drive a REAL P6 block, then read WITHOUT ever calling
    ``catalog.rebuild()`` manually again. Normal (rebuild-on-miss) reads
    must show the effective blocked state; the C4/Knowledge read-only reads
    must surface ``AssertionCatalogUnavailable``/``catalog_unavailable``
    rather than the stale pre-block projection. This is the exact scenario
    the existing ``test_catalog_packet_reflects_a_real_p6_policy_block_on_the_assertion_itself``
    test above masks by rebuilding immediately after the block."""

    assertion_id = _materialize(
        tmp_foundry, "rf_run_p5_sol38_blocked", "workspace-a", "P6 authoritatively blocks this evidence too."
    )
    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-a", ("researcher",))

    # PREBUILD -- proves a real, on-disk, pre-block projection exists.
    catalog.rebuild("workspace-a")
    prebuilt_packet = catalog.packet(assertion_id, identity=identity)
    assert prebuilt_packet is not None
    assert prebuilt_packet["lifecycle_state"] == "eligible"
    assert catalog.projection_path("workspace-a").exists()

    reconciler = AssertionImpactReconciler(workspace_id="workspace-a", paths=tmp_foundry)
    assertion = load_yaml(reconciler.root / "assertions" / f"{assertion_id}.yaml")
    event_id = "evt_sol38_catalog_blocked"
    dump_yaml(
        _lifecycle_event_for(assertion_id, assertion["assertion_version"], event_id),
        reconciler.event_path(event_id),
    )
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text('{"expected_objects": []}', encoding="utf-8")
    result = reconciler.reconcile(assertion_id=assertion_id, event_id=event_id)
    assert result.status == "completed"

    # The pre-block projection file was invalidated as part of policy
    # establishment -- never left on disk trusted-unchanged.
    assert not catalog.projection_path("workspace-a").exists()

    # C4/Knowledge read-only path FIRST (before any rebuild-on-miss call
    # below could re-create the projection file): never auto-rebuilds --
    # surfaces unavailable rather than ever serving the stale pre-block
    # projection.
    read_only_catalog = AssertionCatalog(tmp_foundry)
    with pytest.raises(AssertionCatalogUnavailable):
        read_only_catalog.packet_read_only(assertion_id, identity=identity)
    read_only_search = read_only_catalog.search_read_only(identity=identity)
    assert read_only_search["denial_reason"] == "catalog_unavailable"
    assert read_only_search["items"] == []
    assert not catalog.projection_path("workspace-a").exists()  # still not rebuilt

    # Normal (rebuild-on-miss) read: transparently rebuilds and shows the
    # effective blocked state -- NO manual `catalog.rebuild()` call here.
    packet = catalog.packet(assertion_id, identity=identity)
    assert packet is not None
    assert packet["lifecycle_state"] == "blocked"
    assert packet["freshness"]["lifecycle_state"] == "blocked"
    search_result = catalog.search(identity=identity)
    assert assertion_id not in {item["assertion_id"] for item in search_result["items"]}


def test_catalog_packet_degrades_with_a_logged_warning_on_invalid_policy_file(tmp_foundry, caplog) -> None:
    """K-2 (Karen Wave-3 gate, MEDIUM): a ``lifecycle_policy/<id>.yaml`` file
    that IS PRESENT but fails to validate for this assertion is READ-path
    corruption -- the catalog rebuild degrades to the assertion's own
    recorded ``lifecycle_state`` (never a 500, V5-1) but MUST log a warning
    so the corruption is observable, unlike a silent skip."""

    assertion_id = _materialize(
        tmp_foundry, "rf_run_p5_f19_invalid_policy", "workspace-a", "Evidence with a corrupt policy file."
    )
    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-a", ("researcher",))

    reconciler = AssertionImpactReconciler(workspace_id="workspace-a", paths=tmp_foundry)
    policy_path = reconciler.policy_path(assertion_id)
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    dump_yaml({"unexpected": "shape"}, policy_path)

    with caplog.at_level("WARNING", logger="research_foundry.services.assertion_catalog"):
        catalog.rebuild("workspace-a")

    packet = catalog.packet(assertion_id, identity=identity)
    assert packet is not None
    assert packet["lifecycle_state"] == "eligible"  # degraded to the raw record's own value
    assert any(
        "lifecycle_policy" in message and "present but invalid" in message for message in caplog.messages
    )


def test_legacy_workspace_without_assertions_stays_empty_and_valid(tmp_foundry) -> None:
    catalog = AssertionCatalog(tmp_foundry)
    result = catalog.search(identity=AuthIdentity("legacy", "workspace-legacy", ("viewer",)))

    assert result == {
        "items": [],
        "next_cursor": None,
        "facets": {"lifecycle_states": [], "access_scopes": []},
        "denial_reason": None,
    }


# ---------------------------------------------------------------------------
# RF Knowledge MCP KMCP-2.3: non-rebuilding read path
# ---------------------------------------------------------------------------


def test_search_read_only_missing_projection_denies_without_rebuild(tmp_foundry) -> None:
    """Unlike ``search`` (which silently rebuilds -- see the legacy-workspace test
    above), ``search_read_only`` never writes a projection file for a workspace
    that has never been materialized."""

    from research_foundry.services.assertion_catalog import AssertionCatalogUnavailable

    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("legacy", "workspace-never-built", ("viewer",))
    projection_path = catalog.projection_path(identity.workspace_id)
    assert not projection_path.exists()

    result = catalog.search_read_only(identity=identity)

    assert result == AssertionCatalog.denied_payload("catalog_unavailable")
    assert not projection_path.exists()
    with pytest.raises(AssertionCatalogUnavailable):
        catalog._records_read_only(identity.workspace_id)


def test_packet_and_lineage_read_only_missing_projection_raise_without_rebuild(tmp_foundry) -> None:
    from research_foundry.services.assertion_catalog import AssertionCatalogUnavailable

    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("legacy", "workspace-never-built-2", ("viewer",))
    projection_path = catalog.projection_path(identity.workspace_id)

    with pytest.raises(AssertionCatalogUnavailable):
        catalog.packet_read_only("ast_does_not_exist", identity=identity)
    assert not projection_path.exists()

    with pytest.raises(AssertionCatalogUnavailable):
        catalog.lineage_read_only("ast_does_not_exist", identity=identity)
    assert not projection_path.exists()


def test_read_only_methods_match_rebuilt_methods_when_projection_exists(tmp_foundry) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_p4_readonly", "workspace-a", "The read-only seam sees 42 percent too."
    )
    catalog = AssertionCatalog(tmp_foundry)
    identity = AuthIdentity("alice", "workspace-a", ("researcher",))
    catalog.rebuild("workspace-a")

    assert catalog.search_read_only(identity=identity, query="42") == catalog.search(
        identity=identity, query="42"
    )
    assert catalog.packet_read_only(assertion_id, identity=identity) == catalog.packet(
        assertion_id, identity=identity
    )
    assert catalog.lineage_read_only(assertion_id, identity=identity) == catalog.lineage(
        assertion_id, identity=identity
    )


def test_read_only_rights_denial_matches_rebuilt_denial_shape(tmp_foundry) -> None:
    """A policy/rights denial over an ALREADY-BUILT projection returns the same
    bounded shape from both the rebuilding and non-rebuilding surfaces --
    distinguishing "denied" from "unavailable" only via reason code, never shape."""

    _materialize(tmp_foundry, "rf_run_p4_ro_rights", "workspace-a", "Missing rights must deny read-only too.")
    catalog = AssertionCatalog(tmp_foundry)
    edition_path = next((tmp_foundry.root / "assertion_ledger" / "workspaces").glob("*/sources/*/editions/*.yaml"))
    edition = load_yaml(edition_path)
    edition["metadata_extensions"].pop("allowed_use")
    dump_yaml(edition, edition_path)
    catalog.rebuild("workspace-a")

    identity = AuthIdentity("alice", "workspace-a", ("viewer",))
    assert catalog.search_read_only(identity=identity) == catalog.search(identity=identity)
    assert catalog.search_read_only(identity=identity)["denial_reason"] == "rights_context_missing"
