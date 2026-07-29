"""RPC-1.3 report-use service coverage (freeze doc §13, AC RPC-3).

Covers RPC-3.1 (immutable report-use service: prepare/validate/publish/replay)
and RPC-3.2 (the ``verify_report`` finalization seam: publish only on a
verified report revision, resilience for legacy/unresolvable persistent
refs). Source-assertion fixtures below are hand-written directly at the
``AssertionRegistry`` storage path rather than run through the full P2/P3
extraction pipeline -- :mod:`research_foundry.services.assertion_report_use`
never schema-validates the ``source_assertion`` it reads (only
``assertion_id``/``assertion_version``/``lifecycle_state``/``rights_summary``
matter to it), so a minimal, well-formed-id fixture exercises this module's
own contract without coupling these tests to extraction/claim-mapping
internals outside this task's scope.
"""

from __future__ import annotations

import copy
import threading
from hashlib import sha256
from pathlib import Path

import pytest

from research_foundry.assertion_identity import source_assertion_id
from research_foundry.frontmatter import dump_md, load_md
from research_foundry.services.assertion_impact import AssertionImpactReconciler
from research_foundry.services.assertion_registry import AssertionRegistry
from research_foundry.services.assertion_report_use import (
    REPORT_ASSERTION_USE_IDENTITY_ALGORITHM,
    REPORT_ASSERTION_USE_MATERIAL_FIELDS,
    ReportAssertionUseConflict,
    ReportAssertionUseError,
    ReportAssertionUseService,
    assert_rights_snapshot_not_promoted,
    attest_verification_pass,
    build_cited_ref,
    build_report_ref,
    fold_rights_snapshots_most_restrictive,
    normalize_rights_snapshot,
    publish_report_assertion_uses_for_report,
    report_assertion_use_fingerprint,
    report_revision_id_for_run_report,
)
from research_foundry.services.synthesis import synthesize_report
from research_foundry.services.verification import verify_report
from research_foundry.yamlio import dump_yaml, load_yaml

WORKSPACE_ID = "workspace-report-use"
RUN_ID = "rf_run_20260728_report_use_demo"
INTENT_ID = "intent_research_20260728_report_use_demo"


def _material_fields() -> dict[str, object]:
    return {
        "source_edition_id": "sed_" + "1" * 64,
        "passage_id": "psg_" + "2" * 64,
        "assertion_text_sha256": sha256(b"exact text").hexdigest(),
        "qualifiers": {},
        "qualifier_extensions": {},
    }


def _write_source_assertion(
    tmp_foundry,
    *,
    workspace_id: str = WORKSPACE_ID,
    assertion_version: int = 1,
    lifecycle_state: str = "eligible",
    rights_summary: dict | None = None,
) -> str:
    fields = _material_fields()
    assertion_id = source_assertion_id(fields)
    record = {
        "schema_version": "1.0",
        "type": "source_assertion",
        "assertion_id": assertion_id,
        "assertion_version": assertion_version,
        "lifecycle_state": lifecycle_state,
        "rights_summary": rights_summary if rights_summary is not None else {},
    }
    registry = AssertionRegistry(workspace_id=workspace_id, paths=tmp_foundry)
    path = registry.root / "assertions" / f"{assertion_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    dump_yaml(record, path)
    return assertion_id


def _report_ref(**overrides):
    defaults = {"report_id": "report_20260728_demo", "report_content_digest": "a" * 64}
    defaults.update(overrides)
    return build_report_ref(**defaults)


def _write_real_report_and_digest(
    tmp_foundry, *, name: str, body: str = "genuine report body for attestation"
) -> tuple[Path, str]:
    """Write a real front-mattered report file and return ``(path, digest)``.

    SOL-35 (reopened, re-closed): ``attest_verification_pass`` re-reads
    ``report_path`` from disk and refuses to mint an attestation unless the
    supplied ``report_content_digest`` matches those exact bytes RIGHT NOW
    -- an arbitrary hex string (as the pre-closure tests used) is no longer
    accepted. This helper writes genuine content and returns the digest
    ``attest_verification_pass`` will independently recompute, via the same
    ``load_md`` round trip it performs internally.
    """

    path = tmp_foundry.root / "reports" / name
    dump_md({"schema_version": "1.0"}, body, path)
    _, current_body = load_md(path)
    digest = sha256(current_body.encode("utf-8")).hexdigest()
    return path, digest


def _mark_report_revision_verified(
    tmp_foundry,
    service,
    *,
    report_id: str = "report_20260728_demo",
    verified_at: str = "2026-07-28T12:00:00Z",
) -> dict[str, object]:
    """Simulate the real ``verify_report`` -> ``publish_report_assertion_uses_for_report``
    trust boundary (T3-1), through the REAL public entry point.

    K-FINAL-1 (CRITICAL, empirically demonstrated): this helper used to call
    ``ReportAssertionUseService.resolve_verification_pass_created_at``
    directly -- at the time, a plain PUBLIC method, callable by any holder of
    a service instance with an arbitrary, unverified digest bound to no real
    report body. A two-call attack script confirmed that same shortcut is
    exploitable through the public API: call the (then-public) method with a
    forged digest, then ``publish_report_assertion_uses_for_report`` --
    minting a durably published record with zero report bytes ever read. The
    method is now module/class-private
    (``_resolve_verification_pass_created_at``) and this helper establishes
    attestation the ONLY way a real caller can: writes a genuine report file
    to disk and calls the public, digest-verifying
    :func:`attest_verification_pass`, exactly as ``verification.py``'s own
    call site does after a real ``verify_report`` pass. Returns the
    ``report_ref`` bound to that real file's digest -- callers MUST use this
    returned ``report_ref`` for any subsequent ``prepare_report_assertion_use``/
    ``publish`` call, since ``report_revision_id`` is derived from
    ``report_id`` + ``report_content_digest`` together."""

    report_path, digest = _write_real_report_and_digest(tmp_foundry, name=f"{report_id}.md")
    attest_verification_pass(
        workspace_id=service.workspace_id,
        report_id=report_id,
        report_content_digest=digest,
        verified_at=verified_at,
        report_path=report_path,
        paths=service.paths,
    )
    return build_report_ref(report_id=report_id, report_content_digest=digest)


# --- identity / canonicalization --------------------------------------------


def test_report_revision_id_matches_freeze_doc_worked_vector():
    report_id = "report_20260728_pediatric_cbc_reference"
    digest = "2" * 64
    assert report_revision_id_for_run_report(report_id, digest) == (
        "rrv_eecd155f212fbfdac8b698b4860aae49bfe236a1f9662895e3bea91f92873027"
    )


def test_normalize_rights_snapshot_bare_and_fully_spelled_are_identical():
    fully_spelled = {
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
        "rights_triage_failure": None,
    }
    assert normalize_rights_snapshot({}) == fully_spelled
    assert normalize_rights_snapshot(None) == fully_spelled
    assert normalize_rights_snapshot({}) == normalize_rights_snapshot(fully_spelled)


def test_build_report_ref_rejects_mismatched_revision_id():
    with pytest.raises(ReportAssertionUseError):
        build_report_ref(
            report_id="report_x",
            report_content_digest="a" * 64,
            report_revision_id="rrv_" + "0" * 64,
        )


def test_build_report_ref_computes_the_frozen_formula_when_omitted():
    ref = _report_ref()
    assert ref["report_family"] == "run_report"
    assert ref["report_draft_id"] is None
    assert ref["report_revision_id"] == report_revision_id_for_run_report(
        ref["report_id"], ref["report_content_digest"]
    )


def test_build_cited_ref_requires_matching_kind_fields_and_nulls_the_rest():
    with pytest.raises(ReportAssertionUseError):
        build_cited_ref(ref_kind="source_assertion")
    ref = build_cited_ref(
        ref_kind="source_assertion", assertion_id="ast_" + "a" * 64, assertion_version=1
    )
    assert ref["inference_id"] is None
    assert ref["inference_version"] is None
    assert ref["canonical_claim_id"] is None
    assert ref["canonical_claim_version"] is None


# --- rights-snapshot promotion guard + fold ---------------------------------


def test_rights_snapshot_promotion_is_rejected():
    source = {
        "clearance_status": "CLEARED_OPEN_LICENSE",
        "review_status": "human_reviewed",
        "rights_record_ids": ["rgt_1"],
    }
    # A verbatim copy of an already-existing source's rights posture is fine.
    assert_rights_snapshot_not_promoted(source, [source])

    # A candidate asserting a value ABSENT from every contributing source
    # must be rejected -- the no_agent_cleared_rights_value guard applied to
    # report-use construction (freeze doc §13.4/§15.3).
    promoted = dict(source)
    promoted["clearance_status"] = "CLEARED_PUBLIC_DOMAIN"
    with pytest.raises(ReportAssertionUseError):
        assert_rights_snapshot_not_promoted(promoted, [source])


def test_fold_rights_snapshots_most_restrictive_picks_the_worst_posture():
    permissive = {
        "clearance_status": "CLEARED_OPEN_LICENSE",
        "restrictions": {"commercial_use": "allowed"},
    }
    restrictive = {
        "clearance_status": "PROHIBITED",
        "restrictions": {"commercial_use": "prohibited"},
    }
    folded = fold_rights_snapshots_most_restrictive([permissive, restrictive])
    assert folded["clearance_status"] == "PROHIBITED"
    assert folded["restrictions"]["commercial_use"] == "prohibited"


# --- service: prepare / validate / publish / replay -------------------------


def test_prepare_validate_publish_and_replay(tmp_foundry):
    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE", "rights_record_ids": ["rgt_1"]},
    )
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    persistent_references = {"source_assertion_id": assertion_id, "assertion_version": 1}
    report_ref = _mark_report_revision_verified(tmp_foundry, service)

    outcome = service.prepare_report_assertion_use(
        report_ref=report_ref,
        persistent_references=persistent_references,
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome.status == "prepared"
    assert outcome.use_id.startswith("rau_")
    validation = service.validate(outcome.record)
    assert validation.ok, validation.errors

    status, record = service.publish(outcome.record)
    assert status == "published"
    assert service._use_path(outcome.use_id).exists()

    # Replay: identical inputs converge on the identical use_id and are an
    # idempotent no-op (freeze doc §13.5) -- never a second file, never a
    # conflict.
    outcome2 = service.prepare_report_assertion_use(
        report_ref=report_ref,
        persistent_references=persistent_references,
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome2.use_id == outcome.use_id
    status2, record2 = service.publish(outcome2.record)
    assert status2 == "replayed"
    assert record2 == record


def test_publish_conflict_on_corrupted_bytes_at_the_same_use_id(tmp_foundry):
    assertion_id = _write_source_assertion(tmp_foundry)
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    report_ref = _mark_report_revision_verified(tmp_foundry, service)
    outcome = service.prepare_report_assertion_use(
        report_ref=report_ref,
        persistent_references={"source_assertion_id": assertion_id, "assertion_version": 1},
        created_at="2026-07-28T12:00:00Z",
    )
    service.publish(outcome.record)

    # A forged/corrupted candidate claiming the SAME use_id with different
    # bytes must be rejected, never silently overwritten (freeze doc §13.5/
    # §13.6 example (g)).
    forged = copy.deepcopy(outcome.record)
    forged["created_at"] = "2099-01-01T00:00:00Z"
    with pytest.raises(ReportAssertionUseConflict):
        service.publish(forged)


def test_stale_assertion_version_is_a_typed_skip(tmp_foundry):
    # The stored record is at version 2; the ledger cites version 1 -- no
    # longer current.
    assertion_id = _write_source_assertion(tmp_foundry, assertion_version=2)
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    outcome = service.prepare_report_assertion_use(
        report_ref=_report_ref(),
        persistent_references={"source_assertion_id": assertion_id, "assertion_version": 1},
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome.status == "stale_persistent_reference"
    assert outcome.record is None


def test_ineligible_lifecycle_state_is_a_typed_skip(tmp_foundry):
    assertion_id = _write_source_assertion(tmp_foundry, lifecycle_state="stale")
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    outcome = service.prepare_report_assertion_use(
        report_ref=_report_ref(),
        persistent_references={"source_assertion_id": assertion_id, "assertion_version": 1},
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome.status == "stale_persistent_reference"


def test_p6_policy_blocked_assertion_is_a_typed_skip_at_prepare_and_fresh_publish(tmp_foundry) -> None:
    """SOL-36: report-use is a fourth F19 citation writer. The raw
    ``assertions/<id>.yaml`` record's ``lifecycle_state`` never flips when
    P6 authoritatively blocks a source assertion (``assertion_impact.py``'s
    own "immutable source assertion is never overwritten" rule) -- both
    prepare time (``resolve_cited_reference``) and a fresh publish
    (``_assert_fresh_write_is_grounded``) must consult
    ``effective_source_assertion_lifecycle_state`` and refuse to cite it,
    consistent with the other three writers (inference, canonical-claim,
    P4 commit recheck). Driven through a REAL
    ``AssertionImpactReconciler.reconcile()`` flow (which schema-validates
    the assertion it operates on, unlike this module's own minimal
    ``_write_source_assertion`` fixture) against a genuinely-materialized
    assertion, never a hand-authored ``lifecycle_state: blocked`` record."""

    from tests.unit.test_assertion_inference import _setup_run_with_two_supported_claims

    run_id = "rf_run_sol36_report_use_blocked"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id, workspace_id=WORKSPACE_ID)
    ledger = load_yaml(tmp_foundry.run_paths(run_id).claim_ledger)
    clm_001 = next(c for c in ledger["claims"] if c["claim_id"] == "clm_001")
    refs = clm_001["persistent_references"]
    assertion_id = refs["source_assertion_id"]
    assertion_version = refs["assertion_version"]

    reconciler = AssertionImpactReconciler(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    event_id = "evt_sol36_report_use_blocked"
    dump_yaml(
        {
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
        },
        reconciler.event_path(event_id),
    )
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text('{"expected_objects": []}', encoding="utf-8")
    result = reconciler.reconcile(assertion_id=assertion_id, event_id=event_id)
    assert result.status == "completed"

    # The immutable record itself is untouched -- a naive raw-lifecycle-state
    # recheck would still see "eligible" and let a new citation through.
    assert (
        load_yaml(reconciler.root / "assertions" / f"{assertion_id}.yaml")["lifecycle_state"]
        == "eligible"
    )

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    report_ref = _report_ref(report_id="report_sol36_blocked")

    # Prepare-time: no canonical use is ever constructed for a P6-blocked
    # assertion.
    outcome = service.prepare_report_assertion_use(
        report_ref=report_ref,
        persistent_references={"source_assertion_id": assertion_id, "assertion_version": assertion_version},
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome.status == "stale_persistent_reference"
    assert outcome.reason == "assertion_policy_blocked"
    assert outcome.record is None

    # Fresh-publish time: a hand-prepared record naming this SAME blocked
    # assertion is refused too, via _assert_fresh_write_is_grounded's re-run
    # of the SAME resolution.
    report_ref = _mark_report_revision_verified(
        tmp_foundry, service, report_id="report_sol36_blocked"
    )
    forged_cited_ref = build_cited_ref(
        ref_kind="source_assertion", assertion_id=assertion_id, assertion_version=assertion_version
    )
    forged_record = {
        "schema_version": "1.0",
        "type": "report_assertion_use",
        "workspace_id": WORKSPACE_ID,
        "report_ref": dict(report_ref),
        "cited_ref": forged_cited_ref,
        "rights_snapshot": normalize_rights_snapshot(None),
        "created_at": "2026-07-28T12:00:00Z",
    }
    fingerprint = report_assertion_use_fingerprint(forged_record)
    forged_record["use_id"] = f"rau_{fingerprint}"
    forged_record["identity"] = {
        "algorithm": REPORT_ASSERTION_USE_IDENTITY_ALGORITHM,
        "fingerprint": fingerprint,
        "material_fields": list(REPORT_ASSERTION_USE_MATERIAL_FIELDS),
    }
    with pytest.raises(ReportAssertionUseError):
        service.publish(forged_record)


def test_missing_and_unresolvable_persistent_refs_are_legacy_unresolved(tmp_foundry):
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    report_ref = _report_ref()

    # No persistent_references block at all (a legacy run-local claim).
    outcome = service.prepare_report_assertion_use(
        report_ref=report_ref, persistent_references=None, created_at="2026-07-28T12:00:00Z"
    )
    assert outcome.status == "legacy_unresolved"
    assert outcome.record is None

    # An inference/canonical-claim reference: no P4 reader exists yet in this
    # tree, so this resolves the same way absence does (AC RPC-3 resilience).
    outcome2 = service.prepare_report_assertion_use(
        report_ref=report_ref,
        persistent_references={"inference_id": "inf_legacy", "inference_version": 1},
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome2.status == "legacy_unresolved"

    # A source_assertion_id that resolves to nothing on disk.
    outcome3 = service.prepare_report_assertion_use(
        report_ref=report_ref,
        persistent_references={"source_assertion_id": "ast_" + "9" * 64, "assertion_version": 1},
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome3.status == "legacy_unresolved"


def test_publish_batch_fails_closed_without_a_workspace_id(tmp_foundry):
    result = publish_report_assertion_uses_for_report(
        workspace_id=None,
        report_id="report_x",
        report_content_digest="a" * 64,
        verification_passed_at="2026-07-28T12:00:00Z",
        claims=[],
        paths=tmp_foundry,
    )
    assert result.status == "denied"
    assert result.published == ()
    assert result.skipped == ()


def test_manifest_records_one_entry_per_published_use(tmp_foundry):
    assertion_id = _write_source_assertion(tmp_foundry)
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    report_ref = _mark_report_revision_verified(tmp_foundry, service)
    outcome = service.prepare_report_assertion_use(
        report_ref=report_ref,
        persistent_references={"source_assertion_id": assertion_id, "assertion_version": 1},
        created_at="2026-07-28T12:00:00Z",
    )
    service.publish(outcome.record)
    manifest = service.load_manifest(report_ref["report_revision_id"])
    assert len(manifest["entries"]) == 1
    assert manifest["entries"][0]["use_id"] == outcome.use_id

    # Republishing the identical record is idempotent -- no duplicate entry.
    service.publish(outcome.record)
    manifest_again = service.load_manifest(report_ref["report_revision_id"])
    assert len(manifest_again["entries"]) == 1


# --- RPC-3.3 adversarial pass: attack matrix (AC RPC-3) ---------------------


def test_replay_conflict_leaves_the_original_record_intact(tmp_foundry):
    """Attack 8: same use_id, different bytes -- fail closed, original untouched."""

    assertion_id = _write_source_assertion(tmp_foundry)
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    report_ref = _mark_report_revision_verified(tmp_foundry, service)
    outcome = service.prepare_report_assertion_use(
        report_ref=report_ref,
        persistent_references={"source_assertion_id": assertion_id, "assertion_version": 1},
        created_at="2026-07-28T12:00:00Z",
    )
    service.publish(outcome.record)
    original_bytes = service._use_path(outcome.use_id).read_bytes()

    forged = copy.deepcopy(outcome.record)
    forged["created_at"] = "2099-01-01T00:00:00Z"
    with pytest.raises(ReportAssertionUseConflict):
        service.publish(forged)

    assert service._use_path(outcome.use_id).read_bytes() == original_bytes
    assert load_yaml(service._use_path(outcome.use_id)) == outcome.record


def test_cross_workspace_cited_ref_is_legacy_unresolved_with_no_existence_leak(tmp_foundry):
    """Attack 2: a ref belonging to another workspace -- no canonical use,
    no signal distinguishing "wrong workspace" from "does not exist"."""

    foreign_assertion_id = _write_source_assertion(
        tmp_foundry,
        workspace_id="acme-corp",
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE"},
    )
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    outcome = service.prepare_report_assertion_use(
        report_ref=_report_ref(),
        persistent_references={
            "source_assertion_id": foreign_assertion_id,
            "assertion_version": 1,
        },
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome.status == "legacy_unresolved"
    assert outcome.record is None
    assert outcome.use_id is None
    # Same reason code as a genuinely nonexistent id -- no cross-workspace
    # existence leak (freeze doc §13.6 example (d)).
    same_workspace_missing = service.prepare_report_assertion_use(
        report_ref=_report_ref(),
        persistent_references={
            "source_assertion_id": "ast_" + "9" * 64,
            "assertion_version": 1,
        },
        created_at="2026-07-28T12:00:00Z",
    )
    assert same_workspace_missing.reason == "source_assertion_not_found"
    # (resolve_cited_reference doesn't distinguish "found elsewhere" from
    # "not found here" -- both paths reach _resolve_source_assertion's own
    # `not path.exists()` branch since the foreign workspace lives under a
    # different, never-probed storage root.)


def test_stale_prepared_record_fails_closed_when_republished_after_a_rights_mutation(
    tmp_foundry,
):
    """Attack 3: ledger state changes between prepare and publish.

    A candidate resolved BEFORE the mutation must never be written verbatim
    once it no longer matches the CURRENT resolvable truth -- publish()
    fails closed rather than producing a torn/mixed record. A FRESH prepare
    call after the mutation deterministically reflects the new state with
    its own, different, immutable use_id.
    """

    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE", "rights_record_ids": ["rgt_1"]},
    )
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    persistent_references = {"source_assertion_id": assertion_id, "assertion_version": 1}
    report_ref = _mark_report_revision_verified(tmp_foundry, service)

    outcome = service.prepare_report_assertion_use(
        report_ref=report_ref,
        persistent_references=persistent_references,
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome.status == "prepared"

    # The underlying source assertion is re-triaged (same version/lifecycle
    # state -- no re-extraction) to a more restrictive rights posture AFTER
    # prepare, BEFORE publish.
    _write_source_assertion(
        tmp_foundry,
        assertion_version=1,
        lifecycle_state="eligible",
        rights_summary={"clearance_status": "PROHIBITED", "rights_record_ids": ["rgt_1", "rgt_2"]},
    )

    with pytest.raises(ReportAssertionUseError):
        service.publish(outcome.record)
    assert not service._use_path(outcome.use_id).exists()

    # A fresh prepare+publish cycle against the CURRENT state succeeds and
    # mints a genuinely different, independent use_id (rights_snapshot is
    # material to identity, SOL-10) -- never silently merged into the old
    # (never-written) candidate.
    outcome_after = service.prepare_report_assertion_use(
        report_ref=report_ref,
        persistent_references=persistent_references,
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome_after.status == "prepared"
    assert outcome_after.use_id != outcome.use_id
    assert outcome_after.record["rights_snapshot"]["clearance_status"] == "PROHIBITED"
    status, _ = service.publish(outcome_after.record)
    assert status == "published"
    assert not service._use_path(outcome.use_id).exists()


def test_missing_rights_summary_normalizes_to_the_honest_all_unknown_shape(tmp_foundry):
    """Attack 4a: hidden rights -- an absent/empty rights_summary must
    round-trip to the SAME honest, all-"unknown" shape through the real
    prepare/publish path, never invented or silently upgraded."""

    assertion_id = _write_source_assertion(tmp_foundry, rights_summary={})
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    report_ref = _mark_report_revision_verified(tmp_foundry, service)
    outcome = service.prepare_report_assertion_use(
        report_ref=report_ref,
        persistent_references={"source_assertion_id": assertion_id, "assertion_version": 1},
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome.status == "prepared"
    assert outcome.record["rights_snapshot"] == normalize_rights_snapshot({})
    assert outcome.record["rights_snapshot"]["clearance_status"] == "UNKNOWN"
    validation = service.validate(outcome.record)
    assert validation.ok, validation.errors
    status, published = service.publish(outcome.record)
    assert status == "published"
    assert published["rights_snapshot"] == normalize_rights_snapshot({})


def test_publish_rejects_a_hand_crafted_record_with_upgraded_rights(tmp_foundry):
    """Attack 4b: a rights_snapshot claiming CLEARED_OPEN_LICENSE when the
    real backing source has none must be impossible through ANY public
    function -- including a direct, self-consistent ``service.publish()``
    call that bypasses ``prepare_report_assertion_use`` entirely."""

    assertion_id = _write_source_assertion(tmp_foundry, rights_summary={})
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    report_ref = _mark_report_revision_verified(tmp_foundry, service)
    cited_ref = build_cited_ref(
        ref_kind="source_assertion", assertion_id=assertion_id, assertion_version=1
    )
    forged_rights = normalize_rights_snapshot(
        {
            "clearance_status": "CLEARED_OPEN_LICENSE",
            "review_status": "human_reviewed",
            "rights_record_ids": ["rgt_forged"],
        }
    )
    record: dict[str, object] = {
        "schema_version": "1.0",
        "type": "report_assertion_use",
        "workspace_id": WORKSPACE_ID,
        "report_ref": report_ref,
        "cited_ref": cited_ref,
        "rights_snapshot": forged_rights,
        "created_at": "2026-07-28T12:00:00Z",
    }
    # An HONEST, internally self-consistent fingerprint over the DISHONEST
    # rights claim -- schema validation alone would happily accept this.
    fingerprint = report_assertion_use_fingerprint(record)
    record["use_id"] = f"rau_{fingerprint}"
    record["identity"] = {
        "algorithm": REPORT_ASSERTION_USE_IDENTITY_ALGORITHM,
        "fingerprint": fingerprint,
        "material_fields": list(REPORT_ASSERTION_USE_MATERIAL_FIELDS),
    }

    with pytest.raises(ReportAssertionUseError):
        service.publish(record)
    assert not service._use_path(record["use_id"]).exists()


# --- T3-6: fresh-path adversarial tests (rpc-terra-p3-findings.md) ----------
#
# The attacks above (test_replay_conflict_leaves_the_original_record_intact,
# test_publish_conflict_on_corrupted_bytes_at_the_same_use_id) only exercise
# publish()'s EARLY path.exists()/byte-equality branch -- a candidate whose
# use_id already has a file on disk. The tests below construct a record
# whose use_id has NEVER been written, so they exercise the NEW write-
# boundary checks (T3-1) directly. None of them monkeypatch away the checks
# under test.


def test_publish_rejects_forged_fingerprint_and_use_id_on_a_fresh_path(tmp_foundry):
    """T3-1/T3-6: mutating a material field (``created_at``) while KEEPING
    the old, now-stale ``use_id``/``identity.fingerprint`` must be rejected
    at the write boundary -- this record's use_id was never published, so
    it is a genuinely fresh write, never the replay/conflict branch."""

    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE", "rights_record_ids": ["rgt_1"]},
    )
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    outcome = service.prepare_report_assertion_use(
        report_ref=_report_ref(),
        persistent_references={"source_assertion_id": assertion_id, "assertion_version": 1},
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome.status == "prepared"

    forged = copy.deepcopy(outcome.record)
    forged["created_at"] = "2099-01-01T00:00:00Z"  # material field changes...
    # ...but use_id/identity.fingerprint are NOT recomputed -- forged["use_id"]
    # is still the OLD fingerprint, and outcome.record was never published,
    # so this is a fresh write under that (now stale) use_id.
    assert forged["use_id"] == outcome.use_id

    with pytest.raises(ReportAssertionUseError):
        service.publish(forged)
    assert not service._use_path(outcome.use_id).exists()


def test_publish_rejects_forged_report_revision_id_on_a_fresh_path(tmp_foundry):
    """T3-1/T3-6: a report_revision_id that does not match the frozen rrv_
    formula for its own bound report_id/report_content_digest must be
    rejected, even when the record's OWN fingerprint/use_id are honestly,
    self-consistently recomputed over the forged report_ref."""

    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE", "rights_record_ids": ["rgt_1"]},
    )
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    outcome = service.prepare_report_assertion_use(
        report_ref=_report_ref(),
        persistent_references={"source_assertion_id": assertion_id, "assertion_version": 1},
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome.status == "prepared"

    forged = copy.deepcopy(outcome.record)
    forged["report_ref"]["report_revision_id"] = "rrv_" + "0" * 64  # formula-invalid
    fingerprint = report_assertion_use_fingerprint(forged)
    forged["identity"]["fingerprint"] = fingerprint
    forged["use_id"] = f"rau_{fingerprint}"
    assert forged["use_id"] != outcome.use_id  # a genuinely fresh, never-written use_id

    with pytest.raises(ReportAssertionUseError):
        service.publish(forged)
    assert not service._use_path(forged["use_id"]).exists()


def test_publish_rejects_workspace_field_mismatch_on_a_fresh_path(tmp_foundry):
    """T3-1/T3-3/T3-6: a record whose OWN workspace_id field disagrees with
    the publishing service's workspace must be rejected, never written under
    the service's storage root with a different workspace's claimed
    identity."""

    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE", "rights_record_ids": ["rgt_1"]},
    )
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    outcome = service.prepare_report_assertion_use(
        report_ref=_report_ref(),
        persistent_references={"source_assertion_id": assertion_id, "assertion_version": 1},
        created_at="2026-07-28T12:00:00Z",
    )
    assert outcome.status == "prepared"

    forged = copy.deepcopy(outcome.record)
    forged["workspace_id"] = "workspace-B"
    fingerprint = report_assertion_use_fingerprint(forged)
    forged["identity"]["fingerprint"] = fingerprint
    forged["use_id"] = f"rau_{fingerprint}"
    assert forged["use_id"] != outcome.use_id

    with pytest.raises(ReportAssertionUseError):
        service.publish(forged)
    assert not service._use_path(forged["use_id"]).exists()


def test_resolve_source_assertion_rejects_symlink_escape_out_of_the_workspace_root(tmp_foundry):
    """T3-3/T3-6: a same-named assertion file replaced with a symlink
    pointing OUTSIDE this workspace's own assertion-ledger root must resolve
    exactly like "not found" -- never followed, never leaking the external
    target's existence or content."""

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    assertion_id = source_assertion_id(_material_fields())

    # An arbitrary external file this workspace has no legitimate path to --
    # a permissive rights_summary living entirely outside its own root.
    outside_target = tmp_foundry.root / "outside_workspace_escape_target.yaml"
    dump_yaml(
        {
            "schema_version": "1.0",
            "type": "source_assertion",
            "assertion_id": assertion_id,
            "assertion_version": 1,
            "lifecycle_state": "eligible",
            "rights_summary": {"clearance_status": "CLEARED_OPEN_LICENSE"},
        },
        outside_target,
    )

    assertion_path = service._assertion_path(assertion_id)
    assertion_path.parent.mkdir(parents=True, exist_ok=True)
    assertion_path.symlink_to(outside_target)
    assert assertion_path.is_symlink()

    resolution = service.resolve_cited_reference(
        {"source_assertion_id": assertion_id, "assertion_version": 1}
    )
    assert resolution.status == "legacy_unresolved"
    assert resolution.reason == "source_assertion_not_found"
    assert resolution.cited_ref is None
    assert resolution.rights_summary is None


def test_private_resolve_verification_pass_created_at_is_race_safe_across_threads(tmp_foundry):
    """T3-2/T3-6: two genuinely concurrent FIRST callers for the SAME
    report_revision_id must converge on the identical anchor value -- never
    two different ``created_at`` values for one revision.

    This whitebox test exercises the module/class-private writer
    (``_resolve_verification_pass_created_at``, K-FINAL-1) directly to probe
    its own concurrency contract -- a same-suite private-method test, not a
    shortcut for establishing attestation state (see
    ``_mark_report_revision_verified`` for that, which goes through the
    real public ``attest_verification_pass`` entry point instead)."""

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    report_ref = _report_ref()
    revision_id = report_ref["report_revision_id"]

    start = threading.Barrier(2)
    results: list[str] = []
    lock = threading.Lock()
    errors: list[BaseException] = []

    def _call(candidate: str) -> None:
        start.wait(timeout=5)
        try:
            value = service._resolve_verification_pass_created_at(revision_id, candidate)
        except BaseException as exc:  # noqa: BLE001 - captured and asserted on below
            with lock:
                errors.append(exc)
            return
        with lock:
            results.append(value)

    t1 = threading.Thread(target=_call, args=("2026-07-28T10:00:00Z",))
    t2 = threading.Thread(target=_call, args=("2026-07-28T11:00:00Z",))
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    assert not errors, errors
    assert len(results) == 2
    assert results[0] == results[1]
    assert results[0] in ("2026-07-28T10:00:00Z", "2026-07-28T11:00:00Z")

    anchor = load_yaml(service._verification_pass_path(revision_id))
    assert anchor["created_at"] == results[0]


def test_private_resolve_verification_pass_created_at_rejects_a_tampered_anchor(tmp_foundry):
    """T3-2/T3-6: a stored anchor that fails schema/revision validation on
    read (e.g. it now names a DIFFERENT report_revision_id than the file it
    was read from) is an integrity error -- never silently accepted, never
    silently replaced with a fresh value.

    Whitebox test of the private writer's own tamper-detection contract
    (K-FINAL-1) -- see the sibling race-safety test above for why calling
    the private method directly here is appropriate."""

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    report_ref = _report_ref()
    revision_id = report_ref["report_revision_id"]

    service._resolve_verification_pass_created_at(revision_id, "2026-07-28T10:00:00Z")
    anchor_path = service._verification_pass_path(revision_id)
    dump_yaml(
        {
            "schema_version": "1.0",
            "type": "report_assertion_use_verification_pass",
            "report_revision_id": "rrv_" + "9" * 64,  # tampered: wrong revision
            "created_at": "2099-01-01T00:00:00Z",
        },
        anchor_path,
    )

    with pytest.raises(ReportAssertionUseError):
        service._resolve_verification_pass_created_at(revision_id, "2026-07-28T12:00:00Z")


# --- SOL-35 (CRITICAL, reopened+re-closed): publication can never
# self-issue its own attestation, and the attestation writer itself can
# never be minted for report bytes the caller has not actually read.


def test_publish_batch_direct_call_without_verification_pass_is_denied(tmp_foundry):
    """SOL-35 repro: calling the top-level publish function directly,
    bypassing ``verify_report``/``attest_verification_pass`` entirely, must
    be denied -- it can no longer create its own verification-pass anchor
    from nothing but its own say-so."""

    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE", "rights_record_ids": ["rgt_1"]},
    )
    claims = [
        {
            "claim_id": "clm_self_attest",
            "persistent_references": {"source_assertion_id": assertion_id, "assertion_version": 1},
        }
    ]
    result = publish_report_assertion_uses_for_report(
        workspace_id=WORKSPACE_ID,
        report_id="report_20260728_no_attestation",
        report_content_digest="e" * 64,
        verification_passed_at="2026-07-28T12:00:00Z",
        claims=claims,
        paths=tmp_foundry,
    )
    assert result.status == "denied"
    assert result.reason == "verification_pass_missing"
    assert result.published == ()

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    assert not (service.root / "records").exists() or list((service.root / "records").glob("*.yaml")) == []

    report_ref = build_report_ref(
        report_id="report_20260728_no_attestation", report_content_digest="e" * 64
    )
    outcome = load_yaml(service._publication_outcome_path(report_ref["report_revision_id"]))
    assert outcome["status"] == "denied"
    assert outcome["reason"] == "verification_pass_missing"


def test_two_call_self_attestation_through_public_api_is_denied(tmp_foundry):
    """K-FINAL-1 (CRITICAL, empirically demonstrated by Karen): permanent
    regression coverage for the exact two-call self-attestation attack her
    script ran against this module's PUBLIC surface, distinct from the
    repro directly above (which never even attempts step 1 -- it calls
    ``publish_report_assertion_uses_for_report`` cold, with no attempt to
    forge an attestation first).

    The attack: (1) construct a ``ReportAssertionUseService`` directly (a
    fully public class), then call its writer method with a forged digest
    bound to no real report body -- before this fix, that writer,
    ``resolve_verification_pass_created_at``, carried NO leading underscore
    and was ordinary public API, so this call durably wrote a
    verification-pass anchor from nothing but the caller's own say-so; (2)
    call ``publish_report_assertion_uses_for_report`` for that exact
    ``(report_id, forged_digest)`` pair. Confirmed via a standalone repro
    script run against the pre-fix code: both calls succeeded end to end,
    minting a real, durably published ``report_assertion_use`` record with
    the report's actual bytes never read once, and
    ``attest_verification_pass``'s digest-possession check never entered
    the call path at all.

    After the fix, step 1 is no longer reachable through the public API at
    all -- the method is module/class-private
    (``_resolve_verification_pass_created_at``) -- so this test asserts
    both halves of the closure: the old public name no longer exists on the
    class (the exact surface Karen's script called), and, consequently, a
    caller confined to the public API gets the SAME fail-closed
    ``verification_pass_missing`` denial (zero records published) that a
    caller who never attempted step 1 at all already got."""

    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE", "rights_record_ids": ["rgt_1"]},
    )
    report_id = "report_attack_never_verified"
    forged_digest = "f" * 64
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)

    # STEP 1 of Karen's attack: the writer this line used to call, with no
    # leading underscore, is no longer public API -- attribute access
    # itself now fails, closing the exact surface the attack script used.
    assert not hasattr(service, "resolve_verification_pass_created_at")
    assert not hasattr(ReportAssertionUseService, "resolve_verification_pass_created_at")
    with pytest.raises(AttributeError):
        service.resolve_verification_pass_created_at(  # type: ignore[attr-defined]
            build_report_ref(report_id=report_id, report_content_digest=forged_digest)[
                "report_revision_id"
            ],
            "2026-07-28T00:00:00Z",
        )

    # STEP 2 of Karen's attack: since step 1 is no longer reachable through
    # the public API, no attestation was ever durably established for this
    # (report_id, forged_digest) pair -- the publish call that previously
    # completed the attack must now deny closed, exactly like a caller who
    # never attempted step 1 in the first place.
    claims = [
        {
            "claim_id": "clm_attack",
            "persistent_references": {"source_assertion_id": assertion_id, "assertion_version": 1},
        }
    ]
    result = publish_report_assertion_uses_for_report(
        workspace_id=WORKSPACE_ID,
        report_id=report_id,
        report_content_digest=forged_digest,
        verification_passed_at="2026-07-28T00:00:00Z",
        claims=claims,
        paths=tmp_foundry,
    )
    assert result.status == "denied"
    assert result.reason == "verification_pass_missing"
    assert result.published == ()
    assert not (service.root / "records").exists() or list((service.root / "records").glob("*.yaml")) == []


def test_publish_batch_succeeds_after_a_real_attest_verification_pass_call(tmp_foundry):
    """The positive case symmetric to the repro above: a real
    ``attest_verification_pass`` call -- bound to the genuine current bytes
    of a real report file -- for the exact same report revision lets
    publication proceed normally."""

    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE", "rights_record_ids": ["rgt_1"]},
    )
    claims = [
        {
            "claim_id": "clm_real_attest",
            "persistent_references": {"source_assertion_id": assertion_id, "assertion_version": 1},
        }
    ]
    report_path, digest = _write_real_report_and_digest(
        tmp_foundry, name="real_attestation.md"
    )
    attest_verification_pass(
        workspace_id=WORKSPACE_ID,
        report_id="report_20260728_real_attestation",
        report_content_digest=digest,
        verified_at="2026-07-28T12:00:00Z",
        report_path=report_path,
        paths=tmp_foundry,
    )
    result = publish_report_assertion_uses_for_report(
        workspace_id=WORKSPACE_ID,
        report_id="report_20260728_real_attestation",
        report_content_digest=digest,
        verification_passed_at="2026-07-28T12:00:00Z",
        claims=claims,
        paths=tmp_foundry,
        report_path=report_path,
    )
    assert result.status == "completed"
    assert len(result.published) == 1


def test_attest_verification_pass_rejects_a_digest_that_does_not_match_the_report_body(
    tmp_foundry,
):
    """SOL-35 REOPENED repro/closure: the historical exploit was calling the
    (formerly public) writer directly with an arbitrary, unverified digest
    bound to no real file. ``attest_verification_pass`` now re-reads
    ``report_path`` and refuses on any mismatch -- a forger without the true
    current report bytes can no longer mint an attestation."""

    report_path, _real_digest = _write_real_report_and_digest(
        tmp_foundry, name="forged_attestation.md"
    )
    with pytest.raises(ReportAssertionUseError):
        attest_verification_pass(
            workspace_id=WORKSPACE_ID,
            report_id="report_20260728_forged_attestation",
            report_content_digest="f" * 64,  # arbitrary -- does not match report_path's bytes
            verified_at="2026-07-28T12:00:00Z",
            report_path=report_path,
            paths=tmp_foundry,
        )

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    report_ref = build_report_ref(
        report_id="report_20260728_forged_attestation", report_content_digest="f" * 64
    )
    assert not service._verification_pass_path(report_ref["report_revision_id"]).exists()


def test_attest_verification_pass_rejects_an_unreadable_report_path(tmp_foundry):
    """SOL-35 REOPENED: a ``report_path`` that cannot be read at all (never
    written, or deleted) must be a hard refusal -- attestation requires
    proof of possession of the actual current report body, not merely a
    claimed digest."""

    missing_path = tmp_foundry.root / "reports" / "does-not-exist-for-attest.md"
    with pytest.raises(ReportAssertionUseError):
        attest_verification_pass(
            workspace_id=WORKSPACE_ID,
            report_id="report_20260728_unreadable_attest",
            report_content_digest="a" * 64,
            verified_at="2026-07-28T12:00:00Z",
            report_path=missing_path,
            paths=tmp_foundry,
        )


def test_publish_batch_toctou_unreadable_report_denies_the_whole_batch(tmp_foundry):
    """SOL-35 TOCTOU fail-open close: a ``report_path`` that cannot be read
    right now (deleted/corrupted between verification and publication) must
    deny the WHOLE batch -- "cannot compare" is not "matches". Previously
    ``current_digest is None`` fell through the mismatch check entirely and
    published anyway."""

    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE", "rights_record_ids": ["rgt_1"]},
    )
    claims = [
        {
            "claim_id": "clm_unreadable",
            "persistent_references": {"source_assertion_id": assertion_id, "assertion_version": 1},
        }
    ]
    # The report genuinely existed (and was attested) at verification time --
    # only publish-time re-read sees it missing, exercising the TOCTOU window
    # itself rather than the attest-time possession check (see
    # test_attest_verification_pass_rejects_an_unreadable_report_path above
    # for that separate guard).
    report_path, digest = _write_real_report_and_digest(
        tmp_foundry, name="unreadable_before_publish.md"
    )
    attest_verification_pass(
        workspace_id=WORKSPACE_ID,
        report_id="report_20260728_unreadable",
        report_content_digest=digest,
        verified_at="2026-07-28T12:00:00Z",
        report_path=report_path,
        paths=tmp_foundry,
    )
    missing_report_path = tmp_foundry.root / "reports" / "does-not-exist.md"

    result = publish_report_assertion_uses_for_report(
        workspace_id=WORKSPACE_ID,
        report_id="report_20260728_unreadable",
        report_content_digest=digest,
        verification_passed_at="2026-07-28T12:00:00Z",
        claims=claims,
        paths=tmp_foundry,
        report_path=missing_report_path,
    )
    assert result.status == "denied"
    assert result.reason == "report_body_unreadable_since_verification"
    assert result.published == ()

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    assert not (service.root / "records").exists() or list((service.root / "records").glob("*.yaml")) == []


def test_duplicate_cited_ref_in_one_report_revision_yields_exactly_one_record(tmp_foundry):
    """Attack 5: the same cited ref appearing on two claims in one report
    revision -- content-addressing collapses this to exactly one record on
    disk (freeze doc §13.1: "one record per (report revision, cited ref)
    pair"), never two, never an error."""

    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={
            "clearance_status": "CLEARED_OPEN_LICENSE",
            "rights_record_ids": ["rgt_1"],
        },
    )
    claims = [
        {
            "claim_id": "clm_a",
            "persistent_references": {
                "source_assertion_id": assertion_id,
                "assertion_version": 1,
            },
        },
        {
            "claim_id": "clm_b",
            "persistent_references": {
                "source_assertion_id": assertion_id,
                "assertion_version": 1,
            },
        },
    ]
    # SOL-35 (reopened, re-closed): the top-level publish function only
    # CONSUMES a verification-pass attestation now -- it never writes one
    # itself. Establish it first via `attest_verification_pass`, bound to a
    # real report body, exactly as `verification.py::verify_report` does
    # after its own real pass decision.
    report_path, digest = _write_real_report_and_digest(tmp_foundry, name="dup_demo.md")
    attest_verification_pass(
        workspace_id=WORKSPACE_ID,
        report_id="report_20260728_dup_demo",
        report_content_digest=digest,
        verified_at="2026-07-28T12:00:00Z",
        report_path=report_path,
        paths=tmp_foundry,
    )
    result = publish_report_assertion_uses_for_report(
        workspace_id=WORKSPACE_ID,
        report_id="report_20260728_dup_demo",
        report_content_digest=digest,
        verification_passed_at="2026-07-28T12:00:00Z",
        claims=claims,
        paths=tmp_foundry,
    )
    assert result.status == "completed"
    assert len(result.published) == 2
    assert len(set(result.published)) == 1  # both claims resolve to the SAME use_id

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    records = list((service.root / "records").glob("*.yaml"))
    assert len(records) == 1
    report_ref = build_report_ref(
        report_id="report_20260728_dup_demo", report_content_digest=digest
    )
    manifest = service.load_manifest(report_ref["report_revision_id"])
    assert len(manifest["entries"]) == 1


def test_legacy_missing_persistent_references_is_a_no_op_never_an_error(tmp_foundry):
    """Attack 6: a claim with no persistent_references produces no canonical
    use and no error out of the top-level public entry point."""

    report_path, digest = _write_real_report_and_digest(tmp_foundry, name="legacy_demo.md")
    attest_verification_pass(
        workspace_id=WORKSPACE_ID,
        report_id="report_20260728_legacy_demo",
        report_content_digest=digest,
        verified_at="2026-07-28T12:00:00Z",
        report_path=report_path,
        paths=tmp_foundry,
    )
    result = publish_report_assertion_uses_for_report(
        workspace_id=WORKSPACE_ID,
        report_id="report_20260728_legacy_demo",
        report_content_digest=digest,
        verification_passed_at="2026-07-28T12:00:00Z",
        claims=[{"claim_id": "clm_legacy"}],
        paths=tmp_foundry,
    )
    assert result.status == "completed"
    assert result.published == ()
    assert len(result.skipped) == 1
    assert result.skipped[0].claim_id == "clm_legacy"
    assert result.skipped[0].status == "legacy_unresolved"
    assert result.skipped[0].reason == "missing_persistent_references"


def test_crash_between_record_write_and_manifest_append_converges_on_retry(
    tmp_foundry, monkeypatch
):
    """Attack 7: simulate a crash after the immutable record write but
    before the manifest append -- retrying (the real recovery path) must
    converge with no duplicate record and no duplicate manifest entry, and
    the manifest must never show a phantom entry for the un-appended
    write."""

    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE", "rights_record_ids": ["rgt_1"]},
    )
    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    report_ref = _mark_report_revision_verified(tmp_foundry, service)
    outcome = service.prepare_report_assertion_use(
        report_ref=report_ref,
        persistent_references={"source_assertion_id": assertion_id, "assertion_version": 1},
        created_at="2026-07-28T12:00:00Z",
    )

    original_append = service._append_manifest_entry

    def _simulated_crash(record):
        raise RuntimeError("simulated crash before manifest append")

    monkeypatch.setattr(service, "_append_manifest_entry", _simulated_crash)
    with pytest.raises(RuntimeError):
        service.publish(outcome.record)

    # The content-addressed record itself landed durably before the crash...
    assert service._use_path(outcome.use_id).exists()
    # ...but the manifest append never ran -- no torn/phantom entry.
    manifest = service.load_manifest(report_ref["report_revision_id"])
    assert manifest["entries"] == []

    # Retry (recovery): the record already exists, so publish() takes the
    # replay branch, which retries the manifest append too.
    monkeypatch.setattr(service, "_append_manifest_entry", original_append)
    status, _ = service.publish(outcome.record)
    assert status == "replayed"
    manifest_after = service.load_manifest(report_ref["report_revision_id"])
    assert len(manifest_after["entries"]) == 1
    assert manifest_after["entries"][0]["use_id"] == outcome.use_id
    assert len(list((service.root / "records").glob("*.yaml"))) == 1


# --- integration: the verify_report finalization seam (RPC-3.2) ------------


def _write_intent(paths) -> None:
    intent = {
        "id": INTENT_ID,
        "title": "Report-use demo intent",
        "type": "research",
        "status": "active",
        "governance": {"sensitivity": "personal", "requires_human_review": False},
        "output": {"audience": "technical"},
    }
    dump_yaml(intent, paths.intents_active / f"{INTENT_ID}.yaml")


def _write_run_yaml(paths, *, workspace_id: str | None) -> None:
    rp = paths.run_paths(RUN_ID)
    rp.ensure_scaffold()
    dump_yaml({"run_id": RUN_ID, "workspace_id": workspace_id}, rp.run_yaml)


def _write_demo_source_card(paths) -> None:
    rp = paths.run_paths(RUN_ID)
    front = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": "src_20260728_demo_aaaaaaaa",
        "created_at": "2026-07-28T09:00:00Z",
        "created_by_agent": "researcher",
        "sensitivity": "personal",
        "source": {
            "title": "Demo source",
            "source_type": "paper",
            "locator": {"url": "https://example.org/demo", "file_path": None},
            "authors": ["A. Author"],
            "accessed_at": "2026-07-28T09:00:00Z",
        },
    }
    dump_md(front, "# Demo\n\nSummary of the demo source.\n", rp.sources / "src_20260728_demo_aaaaaaaa.md")


def _write_demo_ledger(paths, *, assertion_id: str) -> None:
    ledger = {
        "id": "claim_ledger_report_use_demo",
        "intent_id": INTENT_ID,
        "verification_status": "pending",
        "claims": [
            {
                "claim_id": "clm_001",
                "text": "The demo measurement was 42 percent.",
                "materiality": "material",
                "claim_type": "factual",
                "status": "supported",
                "confidence": "high",
                "sources": [
                    {
                        "source_card_id": "src_20260728_demo_aaaaaaaa",
                        "evidence_id": "ev_001",
                        "relation": "supports",
                        "locator": "p.1",
                    }
                ],
                "persistent_references": {
                    "source_assertion_id": assertion_id,
                    "assertion_version": 1,
                },
            }
        ],
    }
    rp = paths.run_paths(RUN_ID)
    rp.ensure_scaffold()
    dump_yaml(ledger, rp.claim_ledger)


def test_verify_report_pass_publishes_report_assertion_use(tmp_foundry):
    _write_intent(tmp_foundry)
    _write_run_yaml(tmp_foundry, workspace_id=WORKSPACE_ID)
    _write_demo_source_card(tmp_foundry)
    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE", "rights_record_ids": ["rgt_1"]},
    )
    _write_demo_ledger(tmp_foundry, assertion_id=assertion_id)

    synth = synthesize_report(RUN_ID, paths=tmp_foundry)
    assert "clm_001" in synth.claims_cited

    result = verify_report(RUN_ID, paths=tmp_foundry)
    assert result.passed is True

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    records_dir = service.root / "records"
    published = list(records_dir.glob("*.yaml"))
    assert len(published) == 1
    record = load_yaml(published[0])
    assert record["cited_ref"]["assertion_id"] == assertion_id
    assert record["report_ref"]["report_family"] == "run_report"
    assert service.validate(record).ok

    manifest = service.load_manifest(record["report_ref"]["report_revision_id"])
    assert len(manifest["entries"]) == 1

    # Re-verifying the SAME, unedited report body is idempotent (replay,
    # freeze doc §13.5): no second file, no conflict raised out of
    # verify_report (it is swallowed the same way any report-use failure is).
    result_again = verify_report(RUN_ID, paths=tmp_foundry)
    assert result_again.passed is True
    assert len(list(records_dir.glob("*.yaml"))) == 1


def test_verify_report_failure_publishes_nothing(tmp_foundry):
    _write_intent(tmp_foundry)
    _write_run_yaml(tmp_foundry, workspace_id=WORKSPACE_ID)
    _write_demo_source_card(tmp_foundry)
    assertion_id = _write_source_assertion(tmp_foundry)
    _write_demo_ledger(tmp_foundry, assertion_id=assertion_id)

    synth = synthesize_report(RUN_ID, paths=tmp_foundry)

    # Inject an UNTAGGED material sentence (the same proven failure fixture
    # tests/test_claim_verifier.py uses) so verification fails closed
    # (ExitCode.UNSUPPORTED) -- publication gates on a PASS (RPC-OQ-2/§13.2).
    front, body = load_md(synth.report_path)
    body = body.replace(
        "## Findings\n",
        "## Findings\n\nThe benchmark used 1,000 queries.\n",
        1,
    )
    dump_md(front, body, synth.report_path)

    result = verify_report(RUN_ID, paths=tmp_foundry)
    assert result.passed is False

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    assert not (service.root / "records").exists()


def test_verify_report_pass_without_workspace_id_publishes_nothing(tmp_foundry):
    _write_intent(tmp_foundry)
    _write_run_yaml(tmp_foundry, workspace_id=None)
    _write_demo_source_card(tmp_foundry)
    assertion_id = _write_source_assertion(tmp_foundry)
    _write_demo_ledger(tmp_foundry, assertion_id=assertion_id)

    synthesize_report(RUN_ID, paths=tmp_foundry)
    result = verify_report(RUN_ID, paths=tmp_foundry)
    assert result.passed is True

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    assert not (service.root / "records").exists()


def test_mutating_a_verified_report_body_mints_a_new_revision_and_new_uses(tmp_foundry):
    """Attack 1: mutable report substitution through the real ``verify_report``
    seam. Editing the report body after a passing verification and
    re-verifying must mint a DIFFERENT ``report_revision_id`` and publish a
    genuinely new ``report_assertion_use`` record -- the first revision's
    record must be byte-for-byte untouched."""

    _write_intent(tmp_foundry)
    _write_run_yaml(tmp_foundry, workspace_id=WORKSPACE_ID)
    _write_demo_source_card(tmp_foundry)
    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE", "rights_record_ids": ["rgt_1"]},
    )
    _write_demo_ledger(tmp_foundry, assertion_id=assertion_id)

    synth = synthesize_report(RUN_ID, paths=tmp_foundry)
    result = verify_report(RUN_ID, paths=tmp_foundry)
    assert result.passed is True

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    records_dir = service.root / "records"
    first_published = list(records_dir.glob("*.yaml"))
    assert len(first_published) == 1
    first_record = load_yaml(first_published[0])
    first_use_id = first_record["use_id"]
    first_revision_id = first_record["report_ref"]["report_revision_id"]
    first_bytes = first_published[0].read_bytes()

    # A benign, non-material edit (an HTML comment -- the verifier strips
    # comment spans, so this never becomes an untagged material sentence)
    # still changes the report's content digest.
    front, body = load_md(synth.report_path)
    body = body.rstrip("\n") + "\n\n<!-- benign editorial note -->\n"
    dump_md(front, body, synth.report_path)

    result2 = verify_report(RUN_ID, paths=tmp_foundry)
    assert result2.passed is True

    second_published = list(records_dir.glob("*.yaml"))
    assert len(second_published) == 2

    ids_on_disk = {p.stem for p in second_published}
    assert first_use_id in ids_on_disk
    new_path = next(p for p in second_published if p.stem != first_use_id)
    second_record = load_yaml(new_path)
    assert second_record["report_ref"]["report_revision_id"] != first_revision_id
    assert second_record["use_id"] != first_use_id
    # Same cited claim/assertion, only the report_ref (hence use_id) differs.
    assert second_record["cited_ref"] == first_record["cited_ref"]

    # The FIRST revision's record is completely untouched by the second pass.
    first_path = next(p for p in second_published if p.stem == first_use_id)
    assert first_path.read_bytes() == first_bytes


def test_verify_report_legacy_missing_persistent_references_still_passes(tmp_foundry):
    """Attack 6 (verify_report-level): a claim with no ``persistent_references``
    must not affect the report's own pass/fail outcome and must publish no
    canonical use -- resilience clause AC RPC-3 names verbatim."""

    _write_intent(tmp_foundry)
    _write_run_yaml(tmp_foundry, workspace_id=WORKSPACE_ID)
    _write_demo_source_card(tmp_foundry)

    rp = tmp_foundry.run_paths(RUN_ID)
    rp.ensure_scaffold()
    ledger = {
        "id": "claim_ledger_report_use_legacy_demo",
        "intent_id": INTENT_ID,
        "verification_status": "pending",
        "claims": [
            {
                "claim_id": "clm_001",
                "text": "The demo measurement was 42 percent.",
                "materiality": "material",
                "claim_type": "factual",
                "status": "supported",
                "confidence": "high",
                "sources": [
                    {
                        "source_card_id": "src_20260728_demo_aaaaaaaa",
                        "evidence_id": "ev_001",
                        "relation": "supports",
                        "locator": "p.1",
                    }
                ],
                # No persistent_references at all -- a legacy run-local claim
                # never materialized through P3/P4 (RPC-DF-1's exact case).
            }
        ],
    }
    dump_yaml(ledger, rp.claim_ledger)

    synthesize_report(RUN_ID, paths=tmp_foundry)
    result = verify_report(RUN_ID, paths=tmp_foundry)
    assert result.passed is True

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    assert not (service.root / "records").exists()


# --- T3-4/T3-5: TOCTOU close + publication-outcome marker (rpc-terra-p3) ----


def test_verify_report_toctou_skips_publication_when_body_changes_after_checks(
    tmp_foundry, monkeypatch
):
    """T3-4: the report body is rewritten AFTER verify_report's own checks
    ran against it (but before the report-use publish call re-reads it) --
    the ``verify_report`` verdict itself must be unaffected, but publication
    must be skipped entirely (freeze doc §13.5) rather than binding a use to
    a body nobody just verified. Mirrors the exact repro from
    ``.claude/worknotes/rpc-terra-p3-findings.md`` T3-4: monkeypatch
    ``_intent_requires_review`` (called immediately before the report-use
    hook) to mutate the report file on disk mid-flight."""

    _write_intent(tmp_foundry)
    _write_run_yaml(tmp_foundry, workspace_id=WORKSPACE_ID)
    _write_demo_source_card(tmp_foundry)
    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE", "rights_record_ids": ["rgt_1"]},
    )
    _write_demo_ledger(tmp_foundry, assertion_id=assertion_id)

    synth = synthesize_report(RUN_ID, paths=tmp_foundry)
    original_front, original_body = load_md(synth.report_path)
    report_id = original_front["report_id"]
    original_digest = sha256(original_body.encode("utf-8")).hexdigest()
    revision_id = report_revision_id_for_run_report(report_id, original_digest)

    from research_foundry.services import verification as verification_module

    real_intent_requires_review = verification_module._intent_requires_review

    def _mutate_then_check(ledger, paths):
        front, current = load_md(synth.report_path)
        dump_md(front, current + "\nUnverified replacement.\n", synth.report_path)
        return real_intent_requires_review(ledger, paths)

    monkeypatch.setattr(verification_module, "_intent_requires_review", _mutate_then_check)

    result = verify_report(RUN_ID, paths=tmp_foundry)
    assert result.passed is True  # the verdict was decided against the ORIGINAL body

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    records_dir = service.root / "records"
    assert not records_dir.exists() or list(records_dir.glob("*.yaml")) == []

    outcome = load_yaml(service._publication_outcome_path(revision_id))
    assert outcome["status"] == "skipped_digest_mismatch"
    assert outcome["reason"] == "report_body_changed_since_verification"


def test_verify_report_records_a_failed_outcome_when_the_hook_swallows_an_exception(
    tmp_foundry, monkeypatch
):
    """T3-5: verify_report's own broad ``except Exception: pass`` around the
    report-use hook must never make a partial/failed finalization
    completely invisible. A durable publication-outcome marker records the
    failure (status="failed", reason naming the exception) even though the
    verdict and the caller never see it -- this is what makes a
    hook-swallowed partial finalization auditable and retryable instead of
    a silent gap."""

    _write_intent(tmp_foundry)
    _write_run_yaml(tmp_foundry, workspace_id=WORKSPACE_ID)
    _write_demo_source_card(tmp_foundry)
    assertion_id = _write_source_assertion(
        tmp_foundry,
        rights_summary={"clearance_status": "CLEARED_OPEN_LICENSE", "rights_record_ids": ["rgt_1"]},
    )
    _write_demo_ledger(tmp_foundry, assertion_id=assertion_id)

    synth = synthesize_report(RUN_ID, paths=tmp_foundry)
    front, body = load_md(synth.report_path)
    report_id = front["report_id"]
    digest = sha256(body.encode("utf-8")).hexdigest()
    revision_id = report_revision_id_for_run_report(report_id, digest)

    def _boom(self, record):
        raise RuntimeError("simulated publish failure")

    monkeypatch.setattr(ReportAssertionUseService, "publish", _boom)

    result = verify_report(RUN_ID, paths=tmp_foundry)
    assert result.passed is True  # the hook swallowed the exception; verdict unaffected

    service = ReportAssertionUseService(workspace_id=WORKSPACE_ID, paths=tmp_foundry)
    outcome = load_yaml(service._publication_outcome_path(revision_id))
    assert outcome["status"] == "failed"
    assert "RuntimeError" in (outcome["reason"] or "")

    records_dir = service.root / "records"
    assert not records_dir.exists() or list(records_dir.glob("*.yaml")) == []
    assert not (service.root / "records").exists()
