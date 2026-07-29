"""RPC-4.1/4.2: run-local inference-base resolution and durable inference writer.

Mirrors ``tests/unit/test_assertion_materialization.py``'s fixture shape
(``tmp_foundry`` + ``ingest_source`` -> ``extraction.extract_run`` ->
``claim_mapping.build_claim_ledger`` -> ``AssertionMaterializer``) to build
real, exact-passage-bound ``source_assertion`` records, then hand-appends one
``inference``-status claim (``claim_mapping.build_claim_ledger`` never emits
one itself -- synthesis is a later phase) to exercise
``services/assertion_inference.py`` against the contract freeze doc's own
worked identity/digest vectors (§15.2/§17.8).
"""

from __future__ import annotations

import pytest

from research_foundry.services import claim_mapping, extraction
from research_foundry.services.assertion_impact import AssertionImpactReconciler
from research_foundry.services.assertion_inference import (
    AssertionInferenceMaterializer,
    InferenceMaterializationConflict,
    InferenceMaterializationInterrupted,
    InferenceResolution,
    ResolvedInferenceBase,
    compute_commit_proof_digest,
    compute_inference_id,
    compute_inference_version_digest,
)
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml

_WORKSPACE = "workspace-a"


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


def _setup_run_with_two_supported_claims(
    tmp_foundry,
    run_id: str,
    *,
    workspace_id: str = _WORKSPACE,
    content_a: str = "Pediatric neutrophil counts trend lower than adult reference ranges.",
    content_b: str = "Pediatric lymphocyte counts trend higher than adult reference ranges.",
) -> None:
    """Build a run with two exact-passage ``supported`` claims, materialized.

    ``content_a``/``content_b`` default to fixed sentences; source_assertion
    identity is content-derived and workspace-agnostic (contract §15.2 item
    2's "workspace deliberately excluded" convention), so a test exercising
    cross-workspace resolution MUST vary content per workspace or two
    workspaces will mint the identical assertion_id and the "foreign" ref
    will resolve locally after all.
    """

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        "evidence-1.txt",
        run_id=run_id,
        title="First Evidence",
        sensitivity="personal",
        content=content_a,
        assertion_registry_workspace_id=workspace_id,
        paths=tmp_foundry,
    )
    ingest_source(
        "evidence-2.txt",
        run_id=run_id,
        title="Second Evidence",
        sensitivity="personal",
        content=content_b,
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


def _append_inference_claim(
    tmp_foundry,
    run_id: str,
    *,
    from_claims: list[str],
    conclusion: str = "Pediatric CBC reference intervals differ from adult intervals.",
    reasoning_summary: str | None = "Synthesized across two source assertions reporting age-stratified CBC intervals.",
) -> str:
    ledger_path = tmp_foundry.run_paths(run_id).claim_ledger
    ledger = load_yaml(ledger_path)
    claim_id = f"clm_{len(ledger['claims']) + 1:03d}"
    ledger["claims"].append(
        {
            "claim_id": claim_id,
            "text": conclusion,
            "materiality": "material",
            "claim_type": "comparative",
            "status": "inference",
            "confidence": "medium",
            "sources": [],
            "inference_basis": {"from_claims": from_claims, "reasoning_summary": reasoning_summary},
            "report_locations": [],
            "reviewer_notes": "",
        }
    )
    dump_yaml(ledger, ledger_path)
    return claim_id


def _ledger(tmp_foundry, run_id: str) -> dict:
    return load_yaml(tmp_foundry.run_paths(run_id).claim_ledger)


# ---------------------------------------------------------------------------
# RPC-4.1 -- resolve_bases: exact / missing / mixed / stale / cross-workspace
# ---------------------------------------------------------------------------


def test_resolve_bases_exact_match(tmp_foundry) -> None:
    run_id = "rf_run_inf_exact"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])
    ledger = _ledger(tmp_foundry, run_id)

    resolver = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = resolver.resolve_bases(claim_id, ledger)

    assert resolution.status == "resolved"
    assert len(resolution.bases) == 2
    assert {base.claim_id for base in resolution.bases} == {"clm_001", "clm_002"}
    for base in resolution.bases:
        assert base.assertion_id.startswith("ast_")
        assert base.assertion_version == 1


def test_resolve_bases_empty_support(tmp_foundry) -> None:
    run_id = "rf_run_inf_empty"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=[])
    ledger = _ledger(tmp_foundry, run_id)

    resolver = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = resolver.resolve_bases(claim_id, ledger)

    assert resolution.status == "skipped"
    assert resolution.skip_code == "empty_support"


def test_resolve_bases_unresolved_missing_claim(tmp_foundry) -> None:
    run_id = "rf_run_inf_missing"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_999"])
    ledger = _ledger(tmp_foundry, run_id)

    resolver = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = resolver.resolve_bases(claim_id, ledger)

    assert resolution.status == "skipped"
    assert resolution.skip_code == "unresolved_support_ref"


def test_resolve_bases_stale_support(tmp_foundry) -> None:
    run_id = "rf_run_inf_stale"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])
    ledger = _ledger(tmp_foundry, run_id)

    materializer = AssertionMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    base_claim = next(c for c in ledger["claims"] if c["claim_id"] == "clm_001")
    assertion_id = base_claim["persistent_references"]["source_assertion_id"]
    assertion_path = materializer._assertion_path(assertion_id)
    assertion = load_yaml(assertion_path)
    assertion["lifecycle_state"] = "invalidated"
    dump_yaml(assertion, assertion_path)

    resolver = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = resolver.resolve_bases(claim_id, ledger)

    assert resolution.status == "skipped"
    assert resolution.skip_code == "stale_support"


def _lifecycle_event_for(assertion: dict, event_id: str) -> dict:
    return {
        "schema_version": "1.0",
        "type": "assertion_lifecycle_event",
        "event_id": event_id,
        "sequence": 1,
        "idempotency_key": f"test:{event_id}",
        "occurred_at": "2026-07-28T16:00:00Z",
        "cause": "formal_retraction",
        "target": {
            "kind": "source_assertion",
            "id": assertion["assertion_id"],
            "version": assertion["assertion_version"],
        },
        "transition": {"from": "eligible", "to": "invalidated"},
        "authoritative_action": "block_reuse",
        "dependent_actions": [
            {"object_kind": "canonical_claim_edge", "action": "block_reuse"},
            {"object_kind": "inference", "action": "block_reuse"},
            {"object_kind": "report_revision", "action": "block_reuse"},
        ],
    }


def test_resolve_bases_rejects_a_real_p6_policy_blocked_source_assertion(tmp_foundry) -> None:
    """F19 (RPC-6.G validator, Karen K-1, HIGH): ``resolve_bases`` had the
    SAME blindness ``resolve_support``/``_recheck_transitive_support`` did --
    it only ever checked a base's raw, immutable ``lifecycle_state`` (never
    mutated by an authoritative P6 block). ``resolve_bases`` must reject a
    base whose source assertion P6 has authoritatively blocked via a REAL
    ``AssertionImpactReconciler.reconcile()`` flow (never a hand-authored
    ``lifecycle_state: blocked`` -- contrast with
    ``test_resolve_bases_stale_support`` above, which is the raw-record-
    mutation case this is symmetric to but distinct from)."""

    run_id = "rf_run_inf_f19_p6_blocked"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])
    ledger = _ledger(tmp_foundry, run_id)
    base_claim = next(c for c in ledger["claims"] if c["claim_id"] == "clm_001")
    assertion_id = base_claim["persistent_references"]["source_assertion_id"]

    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion = load_yaml(reconciler.root / "assertions" / f"{assertion_id}.yaml")
    event_id = "evt_inf_f19_p6_blocked"
    dump_yaml(_lifecycle_event_for(assertion, event_id), reconciler.event_path(event_id))
    # Nothing cites this assertion through the impact lane yet -- an
    # explicit empty manifest so the receipt completes rather than being
    # blocked on `dependency_manifest_missing` (irrelevant here: `reconcile`
    # ALWAYS writes the policy artifact before that outcome is computed).
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text('{"expected_objects": []}', encoding="utf-8")
    reconcile_result = reconciler.reconcile(assertion_id=assertion_id, event_id=event_id)
    assert reconcile_result.status == "completed"

    policy = load_yaml(reconciler.root / "lifecycle_policy" / f"{assertion_id}.yaml")
    assert policy["invalidation_state"] == "blocked"

    # The immutable record itself is untouched.
    assert load_yaml(reconciler.root / "assertions" / f"{assertion_id}.yaml")["lifecycle_state"] == "eligible"

    resolver = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = resolver.resolve_bases(claim_id, ledger)

    assert resolution.status == "skipped"
    assert resolution.skip_code == "stale_support"


def test_resolve_bases_mixed_workspace_support(tmp_foundry) -> None:
    """A base whose persistent source_assertion_id exists ONLY under a
    different workspace's registry root is distinguished from a genuinely
    unresolved reference (contract §15.1 item 3 -- ANY cross-workspace base
    makes the WHOLE candidate ineligible)."""

    run_a = "rf_run_inf_mixed_a"
    run_b = "rf_run_inf_mixed_b"
    _setup_run_with_two_supported_claims(tmp_foundry, run_a, workspace_id="workspace-a")
    _setup_run_with_two_supported_claims(
        tmp_foundry,
        run_b,
        workspace_id="workspace-b",
        content_a="Adult neutrophil counts differ from a completely separate corpus.",
        content_b="Adult lymphocyte counts differ from a completely separate corpus too.",
    )

    ledger_a = _ledger(tmp_foundry, run_a)
    ledger_b = _ledger(tmp_foundry, run_b)
    foreign_assertion_id = ledger_b["claims"][0]["persistent_references"]["source_assertion_id"]

    # Splice a foreign (workspace-b) source_assertion ref onto workspace-a's
    # own claim ledger, as if a caller mistakenly cross-referenced it.
    ledger_a["claims"][0]["persistent_references"] = {
        **ledger_a["claims"][0]["persistent_references"],
        "source_assertion_id": foreign_assertion_id,
    }
    dump_yaml(ledger_a, tmp_foundry.run_paths(run_a).claim_ledger)
    claim_id = _append_inference_claim(tmp_foundry, run_a, from_claims=["clm_001", "clm_002"])
    ledger_a = _ledger(tmp_foundry, run_a)

    resolver = AssertionInferenceMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    resolution = resolver.resolve_bases(claim_id, ledger_a)

    assert resolution.status == "skipped"
    assert resolution.skip_code == "mixed_workspace_support"


# ---------------------------------------------------------------------------
# RPC-4.2 -- durable inference writer: identity, digests, commit protocol
# ---------------------------------------------------------------------------

_CONTRACT_CONCLUSION = (
    "Pediatric reference intervals for CBC differ materially from adult "
    "intervals across all measured analytes."
)
_CONTRACT_REFS = [
    {
        "assertion_id": "ast_4444444444444444444444444444444444444444444444444444444444444444",
        "assertion_version": 1,
    },
    {
        "assertion_id": "ast_5555555555555555555555555555555555555555555555555555555555555555",
        "assertion_version": 2,
    },
]
_CONTRACT_REASONING = {
    "summary": "Synthesized across two source assertions reporting age-stratified CBC intervals.",
    "method": "comparative_synthesis",
    "producer": "agent-research-1",
}


def test_compute_inference_id_matches_contract_worked_vector() -> None:
    """Golden vector: contract freeze doc §15.2 item 2 / §18.1 fixture."""

    inference_id = compute_inference_id(_CONTRACT_CONCLUSION, _CONTRACT_REFS, _CONTRACT_REASONING)
    assert inference_id == "inf_fd3ee362717699c116ca3eb00c4daa982396789c03040212673a3e1a86464e51"


def test_compute_inference_version_digest_matches_contract_worked_vector() -> None:
    """Golden vector: contract freeze doc §15.2 item 4 (round-3 widened formula)."""

    digest = compute_inference_version_digest(
        _CONTRACT_CONCLUSION, _CONTRACT_REFS, _CONTRACT_REASONING, "active", 1
    )
    assert digest == "8e1292fe2967aae3652dbdf87e0e1522fe387c82dcc003d81b0415bfc8321c44"

    # SOL-26 tamper re-run: a version-integer-only mutation must change the digest.
    tampered = compute_inference_version_digest(
        _CONTRACT_CONCLUSION, _CONTRACT_REFS, _CONTRACT_REASONING, "active", 999
    )
    assert tampered == "befb39ce536eb80c7a85067769fcbc1c3be529516cbb231eed8644f1bf545d44"
    assert tampered != digest


def test_compute_commit_proof_digest_matches_contract_worked_vector() -> None:
    """Golden vector: contract freeze doc §17.8 item 2's seven-field digest."""

    row_sources = [
        {"source_card_id": "src_001", "evidence_id": "ev_001", "relation": "supports", "locator": "sec:2.1"},
        {"source_card_id": "src_002", "evidence_id": "ev_002", "relation": "supports", "locator": "sec:2.2"},
    ]
    digest = compute_commit_proof_digest(
        claim_id="clm_007",
        row_sources=row_sources,
        row_conclusion_text=_CONTRACT_CONCLUSION,
        target_kind="inference_record",
        target_id="inf_fd3ee362717699c116ca3eb00c4daa982396789c03040212673a3e1a86464e51",
        target_version=1,
        target_version_digest="8e1292fe2967aae3652dbdf87e0e1522fe387c82dcc003d81b0415bfc8321c44",
        support_refs_digest="fdcdb3a6c0dfaeccaf7f289c957f25953bf7786c11ecf43393dfe32e8cd140dd",
    )
    assert digest == "85a3e675772f65da81de59bdc17d2ca813f1283c3b802fc83f110fb22e46393d"

    # SOL-14/20 accepted attack: substituting an unrelated active target
    # (everything else unchanged) MUST recompute a different digest.
    substituted = compute_commit_proof_digest(
        claim_id="clm_007",
        row_sources=row_sources,
        row_conclusion_text=_CONTRACT_CONCLUSION,
        target_kind="inference_record",
        target_id="inf_0000000000000000000000000000000000000000000000000000000000000000",
        target_version=1,
        target_version_digest="0" * 64,
        support_refs_digest="0" * 64,
    )
    assert substituted == "8466e738e045fb06e2e196fa510c22564157345ac532347e2867a1a6bfcf99df"
    assert substituted != digest


def test_materialize_inference_end_to_end(tmp_foundry) -> None:
    run_id = "rf_run_inf_e2e"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])

    inferencer = AssertionInferenceMaterializer(
        workspace_id=_WORKSPACE, paths=tmp_foundry
    )
    result = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")

    assert result.status == "materialized"
    assert result.inference_id is not None
    assert result.inference_id.startswith("inf_")
    assert result.inference_version == 1
    assert result.generation_id is not None
    assert result.generation_id.startswith("clg_")

    # Durable record promoted + schema-valid.
    record_path = inferencer.root / "inferences" / f"{result.inference_id}.yaml"
    assert record_path.is_file()
    record = load_yaml(record_path)
    assert inferencer.schemas.validate(record, "inference_record").ok
    assert record["status"] == "active"
    assert record["version_digest"]

    # Generation-manifest entry recorded (§17.7a).
    manifest = load_yaml(inferencer.root / "inferences" / ".generation_manifest.yaml")
    assert any(
        entry["record_id"] == result.inference_id and entry["version"] == 1 for entry in manifest["entries"]
    )

    # claim_ledger row committed with the atomic (inference_id, inference_version) pair.
    ledger = _ledger(tmp_foundry, run_id)
    inference_claim = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
    refs = inference_claim["persistent_references"]
    assert refs["inference_id"] == result.inference_id
    assert refs["inference_version"] == 1

    # Claim-ledger generation pointer + snapshot published (§17.7 step 4).
    pointer = load_yaml(tmp_foundry.run_paths(run_id).claims / ".claim_ledger_published.yaml")
    assert pointer["generation_id"] == result.generation_id
    generation = load_yaml(
        tmp_foundry.run_paths(run_id).claims / ".claim_ledger_generations" / f"{result.generation_id}.yaml"
    )
    assert generation["run_id"] == run_id


def test_materialize_inference_is_idempotent_on_replay(tmp_foundry) -> None:
    run_id = "rf_run_inf_replay"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    first = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")
    second = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")

    assert first.status == second.status == "materialized"
    assert first.inference_id == second.inference_id
    assert first.generation_id == second.generation_id


def test_materialize_inference_replay_conflict_is_a_typed_abstain(tmp_foundry) -> None:
    """A row that already carries a DIFFERENT inference_id/version pair than
    what freshly resolving/recomputing would produce is a fail-closed
    ``replay_conflict`` abstain -- never a silent overwrite."""

    run_id = "rf_run_inf_conflict"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])

    ledger_path = tmp_foundry.run_paths(run_id).claim_ledger
    ledger = load_yaml(ledger_path)
    inference_claim = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
    inference_claim["persistent_references"] = {
        "inference_id": "inf_" + "9" * 64,
        "inference_version": 1,
    }
    dump_yaml(ledger, ledger_path)

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")

    assert result.status == "abstained"
    assert result.abstention_code == "replay_conflict"


def test_materialize_inference_ledger_write_disabled_abstains(tmp_foundry) -> None:
    run_id = "rf_run_inf_disabled"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": False}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = inferencer.materialize_inference(run_id, claim_id)

    assert result.status == "abstained"
    assert result.abstention_code == "ledger_write_disabled"
    assert not (inferencer.root / "inferences").exists()


def test_materialize_inference_run_workspace_mismatch_abstains(tmp_foundry) -> None:
    run_id = "rf_run_inf_workspace_mismatch"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])
    # SOL-14: ownership derives from run.yaml's OWN workspace_id, never the
    # caller-supplied workspace_id alone.
    _write_run_yaml(tmp_foundry, run_id, workspace_id="workspace-other")

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = inferencer.materialize_inference(run_id, claim_id)

    assert result.status == "abstained"
    assert result.abstention_code == "run_workspace_mismatch"


def test_materialize_inference_producer_omitted_when_required(tmp_foundry) -> None:
    run_id = "rf_run_inf_producer_omitted"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = inferencer.materialize_inference(run_id, claim_id, require_producer=True)

    assert result.status == "abstained"
    assert result.abstention_code == "producer_omitted"


# ---------------------------------------------------------------------------
# Crash-injection / recovery (contract §17.7 step 6 -- "kill-between-steps")
# ---------------------------------------------------------------------------


def test_interrupted_after_staging_is_quarantined_and_replay_converges(tmp_foundry) -> None:
    run_id = "rf_run_inf_crash_stage"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    with pytest.raises(InferenceMaterializationInterrupted):
        inferencer.materialize_inference(run_id, claim_id, _interrupt_after_staging=True)

    # No orphan visible as a promoted, citable record.
    assert not (inferencer.root / "inferences").glob("*.yaml") or not any(
        (inferencer.root / "inferences").glob("*.yaml")
    )
    assert any((inferencer.root / ".staging").iterdir())

    quarantined = inferencer.recover_orphaned_inferences()
    assert len(quarantined) == 1
    assert not (inferencer.root / ".staging").exists() or not any((inferencer.root / ".staging").iterdir())

    # A fresh retry (no interrupt) converges: full success from scratch.
    result = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")
    assert result.status == "materialized"


def test_interrupted_before_manifest_is_quarantined_and_replay_converges(tmp_foundry) -> None:
    run_id = "rf_run_inf_crash_manifest"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    with pytest.raises(InferenceMaterializationInterrupted):
        inferencer.materialize_inference(run_id, claim_id, _interrupt_before_manifest=True)

    # Promoted (discoverable on disk) but NOT yet manifest-referenced --
    # quarantine-eligible, never silently citable (§17.7 step 2).
    promoted = list((inferencer.root / "inferences").glob("*.yaml"))
    assert len(promoted) == 1

    quarantined = inferencer.recover_orphaned_inferences()
    assert len(quarantined) == 1
    assert not list((inferencer.root / "inferences").glob("*.yaml"))

    result = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")
    assert result.status == "materialized"


def test_conflicting_promoted_inference_record_raises(tmp_foundry) -> None:
    """A promoted record whose bytes no longer match its own content-addressed
    id is a genuine corruption conflict -- raised, never silently accepted."""

    run_id = "rf_run_inf_conflicting_record"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    first = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")
    record_path = inferencer.root / "inferences" / f"{first.inference_id}.yaml"
    tampered = load_yaml(record_path)
    tampered["conclusion"] = "Tampered conclusion text."
    dump_yaml(tampered, record_path)

    # Force the ledger row back to unset so the writer re-attempts promotion.
    ledger_path = tmp_foundry.run_paths(run_id).claim_ledger
    ledger = load_yaml(ledger_path)
    inference_claim = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
    inference_claim["persistent_references"] = None
    dump_yaml(ledger, ledger_path)

    with pytest.raises(InferenceMaterializationConflict, match="conflicting_inference_record"):
        inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")


# ---------------------------------------------------------------------------
# gpt-5.6-terra fix-cycle 2 (rpc-terra-p4-findings.md T4-2/T4-3/T4-4) --
# generation CAS, manifest-authority inversion crash boundaries, and the
# shared commit-time transitive-support recheck. T4-1 (the second write path
# no longer being public) is covered in test_assertion_materialization.py,
# where `apply_inference_reference`/`apply_canonical_claim_reference` used to
# live.
# ---------------------------------------------------------------------------


def test_materialize_inference_generation_cas_rejects_stale_expected_generation(
    tmp_foundry, monkeypatch
) -> None:
    """T4-2: the claim-ledger generation pointer captured BEFORE the lock is
    CASed against the CURRENT pointer re-read UNDER the lock -- a mismatch
    (simulated here via monkeypatch, standing in for a concurrent writer
    that advanced the generation between resolution and commit) aborts the
    write as a typed conflict, never silently overwriting using a stale
    generation."""

    run_id = "rf_run_inf_generation_cas"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])

    import research_foundry.services.assertion_inference as mod

    # No claim-ledger generation has ever been published for this fresh run
    # (the pointer file does not exist yet, so the TRUE current generation
    # is None) -- monkeypatch the caller's own "expected generation, captured
    # before the lock" to a bogus non-None value, simulating a writer whose
    # resolution is stale by the time it reaches the locked commit.
    monkeypatch.setattr(mod, "_read_claim_ledger_generation_pointer", lambda paths, run_id: "clg_" + "f" * 64)

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")

    assert result.status == "abstained"
    assert result.abstention_code == "partial_write_rejected"
    ledger = _ledger(tmp_foundry, run_id)
    row = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
    assert row.get("persistent_references") is None
    assert not (tmp_foundry.run_paths(run_id).claims / ".claim_ledger_published.yaml").exists()

    monkeypatch.undo()
    retried = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")
    assert retried.status == "materialized"


def test_commit_time_recheck_independently_catches_stale_support_resolution_missed(
    tmp_foundry, monkeypatch
) -> None:
    """T4-4: the shared, locked commit-time transitive-support recheck is
    INDEPENDENT of whatever ``resolve_bases`` reported. Here ``resolve_bases``
    is monkeypatched to (wrongly) report a resolved, eligible base set --
    standing in for any resolution-time bug or TOCTOU race -- while the real
    on-disk source assertion is ALREADY invalidated. The commit routine
    reloads and rechecks every transitively-named source assertion itself
    and abstains with the SPECIFIC ``stale_support`` code -- never the
    generic ``partial_write_rejected`` collapse this fix cycle closes."""

    run_id = "rf_run_inf_commit_time_independent_recheck"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])

    ledger = _ledger(tmp_foundry, run_id)
    base_claim_1 = next(c for c in ledger["claims"] if c["claim_id"] == "clm_001")
    base_claim_2 = next(c for c in ledger["claims"] if c["claim_id"] == "clm_002")
    assertion_id_1 = base_claim_1["persistent_references"]["source_assertion_id"]
    assertion_id_2 = base_claim_2["persistent_references"]["source_assertion_id"]

    materializer = AssertionMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion_path = materializer._assertion_path(assertion_id_1)
    assertion = load_yaml(assertion_path)
    assertion["lifecycle_state"] = "invalidated"
    dump_yaml(assertion, assertion_path)

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    monkeypatch.setattr(
        inferencer,
        "resolve_bases",
        lambda _claim_id, _ledger: InferenceResolution(
            "resolved",
            bases=(
                ResolvedInferenceBase(claim_id="clm_001", assertion_id=assertion_id_1, assertion_version=1),
                ResolvedInferenceBase(claim_id="clm_002", assertion_id=assertion_id_2, assertion_version=1),
            ),
        ),
    )

    result = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")

    assert result.status == "abstained"
    assert result.abstention_code == "stale_support"
    ledger_after = _ledger(tmp_foundry, run_id)
    row = next(c for c in ledger_after["claims"] if c["claim_id"] == claim_id)
    assert row.get("persistent_references") is None
    # No durable inference record was ever committed/referenced -- the
    # invalid write never partially lands.
    assert not (tmp_foundry.run_paths(run_id).claims / ".claim_ledger_published.yaml").exists()


def test_interrupted_after_manifest_pre_ledger_is_quarantined_and_replay_converges(tmp_foundry) -> None:
    """T4-3 NEW crash boundary (post-manifest/pre-ledger): the generation-
    manifest entry is written, but the claim-ledger reference is NOT.
    Recovery authority is the claim-ledger's CURRENT generation (T4-3's
    manifest-authority inversion) -- this record is quarantine-eligible even
    though its private per-record-kind manifest entry already exists,
    proving that manifest entry alone never grants authority."""

    run_id = "rf_run_inf_crash_manifest_pre_ledger"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    with pytest.raises(InferenceMaterializationInterrupted):
        inferencer.materialize_inference(
            run_id, claim_id, producer="agent-research-1", _interrupt_after_manifest=True
        )

    # Promoted AND the manifest entry was already written...
    assert list((inferencer.root / "inferences").glob("*.yaml"))
    manifest = load_yaml(inferencer.root / "inferences" / ".generation_manifest.yaml")
    assert manifest["entries"]
    # ...but the claim_ledger reference was never written.
    ledger = _ledger(tmp_foundry, run_id)
    row = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
    assert row.get("persistent_references") is None
    assert not (tmp_foundry.run_paths(run_id).claims / ".claim_ledger_published.yaml").exists()

    quarantined = inferencer.recover_orphaned_inferences()
    assert len(quarantined) == 1
    remaining = {path.stem for path in (inferencer.root / "inferences").glob("*.yaml")}
    assert quarantined[0] not in remaining

    result = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")
    assert result.status == "materialized"


def test_interrupted_after_ledger_pre_pointer_republishes_pointer_on_retry(tmp_foundry) -> None:
    """T4-3 NEW crash boundary (post-ledger/pre-pointer): the claim_ledger
    reference is written, but the generation pointer is NOT yet swapped. A
    retry re-publishes the pointer idempotently (contract §17.1 item 5)
    rather than double-writing the reference or leaving it unpointed."""

    run_id = "rf_run_inf_crash_ledger_pre_pointer"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    with pytest.raises(InferenceMaterializationInterrupted):
        inferencer.materialize_inference(
            run_id, claim_id, producer="agent-research-1", _interrupt_after_ledger=True
        )

    ledger = _ledger(tmp_foundry, run_id)
    row = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
    assert row["persistent_references"]["inference_id"] is not None
    assert not (tmp_foundry.run_paths(run_id).claims / ".claim_ledger_published.yaml").exists()

    result = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")

    assert result.status == "materialized"
    pointer = load_yaml(tmp_foundry.run_paths(run_id).claims / ".claim_ledger_published.yaml")
    assert pointer["generation_id"] == result.generation_id


# ---------------------------------------------------------------------------
# RPC-7.14/7.16/7.19 gap-fill (ac-evidence-map.md): the golden-vector digest
# tests above (test_compute_inference_version_digest_matches_contract_worked_
# vector) only exercise the pure formula function against fixed frozen
# inputs. RPC-7.14 (freeze doc §17.9) additionally requires proving that a
# REAL P4-written record's stored version_digest recomputes correctly from
# its OWN persisted fields AND matches its generation-manifest entry --
# i.e. the property holds for the service's own output, not merely the
# formula in isolation. RPC-7.16's claim_ledger half (atomic inference_id/
# inference_version pair, never partial) is likewise only demonstrated as a
# happy-path side effect elsewhere; this proves it holds at every crash
# checkpoint the suite already injects. RPC-7.19's "run mapping" sub-check
# (freeze doc §17.1 item 6) mirrors the existing
# test_commit_time_recheck_independently_catches_stale_support_resolution_
# missed pattern (stale ground truth diverges from what an earlier check
# saw) but targets the run-ownership recheck instead of support lifecycle.
# ---------------------------------------------------------------------------


def test_materialized_inference_version_digest_recomputes_and_matches_manifest_entry(
    tmp_foundry,
) -> None:
    """RPC-7.14: a real P4-written ``inference_record``'s ``version_digest``
    (a) recomputes to its own stored value from the record's own persisted
    fields via ``compute_inference_version_digest``, and (b) matches the
    ``version_digest`` recorded in its generation-manifest entry (§17.7a) --
    never merely "the field is present" (already covered by
    ``test_materialize_inference_end_to_end``)."""

    run_id = "rf_run_inf_digest_matches_manifest"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")
    assert result.status == "materialized"

    record = load_yaml(inferencer.root / "inferences" / f"{result.inference_id}.yaml")
    recomputed = compute_inference_version_digest(
        record["conclusion"],
        record["source_assertion_refs"],
        record["reasoning"],
        record["status"],
        record["inference_version"],
    )
    assert recomputed == record["version_digest"]

    manifest = load_yaml(inferencer.root / "inferences" / ".generation_manifest.yaml")
    entry = next(
        e
        for e in manifest["entries"]
        if e["record_id"] == result.inference_id and e["version"] == record["inference_version"]
    )
    assert entry["version_digest"] == record["version_digest"] == recomputed


def test_claim_ledger_inference_reference_pair_is_never_partial_at_any_crash_checkpoint(
    tmp_foundry,
) -> None:
    """RPC-7.16 (claim_ledger half): ``inference_id``/``inference_version``
    are a writer-level atomic pair (schema deliberately carries no
    conditional, freeze doc schemas/claim_ledger.schema.yaml). Reusing the
    suite's own crash-injection hooks, assert the pair is never observed
    with exactly one field set -- at the pre-manifest interrupt, the
    post-manifest/pre-ledger interrupt, the post-ledger/pre-pointer
    interrupt, and after final convergence."""

    def _assert_pair_atomic(tmp_foundry, run_id: str, claim_id: str) -> None:
        ledger = _ledger(tmp_foundry, run_id)
        row = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
        refs = row.get("persistent_references") or {}
        has_id = refs.get("inference_id") is not None
        has_version = refs.get("inference_version") is not None
        assert has_id == has_version, f"partial pair observed: {refs!r}"

    # Checkpoint 1: interrupted before any manifest/ledger write.
    run_id = "rf_run_inf_pair_atomic_pre_manifest"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])
    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    with pytest.raises(InferenceMaterializationInterrupted):
        inferencer.materialize_inference(
            run_id, claim_id, producer="agent-research-1", _interrupt_before_manifest=True
        )
    _assert_pair_atomic(tmp_foundry, run_id, claim_id)

    # Checkpoint 2: interrupted after manifest entry, before the ledger write.
    run_id = "rf_run_inf_pair_atomic_post_manifest"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])
    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    with pytest.raises(InferenceMaterializationInterrupted):
        inferencer.materialize_inference(
            run_id, claim_id, producer="agent-research-1", _interrupt_after_manifest=True
        )
    _assert_pair_atomic(tmp_foundry, run_id, claim_id)

    # Checkpoint 3: interrupted after the ledger write, before the pointer swap.
    run_id = "rf_run_inf_pair_atomic_post_ledger"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])
    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    with pytest.raises(InferenceMaterializationInterrupted):
        inferencer.materialize_inference(
            run_id, claim_id, producer="agent-research-1", _interrupt_after_ledger=True
        )
    # After this checkpoint the pair is expected to be FULLY set (ledger
    # write already landed) -- still validate it is not partial.
    _assert_pair_atomic(tmp_foundry, run_id, claim_id)

    # Final convergence: retry to completion, pair remains atomic (fully set).
    result = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")
    assert result.status == "materialized"
    _assert_pair_atomic(tmp_foundry, run_id, claim_id)


def test_commit_time_recheck_independently_catches_run_mapping_revoked(
    tmp_foundry, monkeypatch
) -> None:
    """RPC-7.19 (freeze doc §17.1 item 6, run-mapping sub-check): the
    locked commit-time recheck in ``_commit_persistent_reference_locked``
    reloads ``run.yaml`` and reverifies workspace ownership INDEPENDENTLY of
    ``materialize_inference``'s own earlier ownership check -- a run-mapping
    revocation that lands between the two (simulated here via a stateful
    monkeypatch on ``assertion_materialization``'s OWN ``load_yaml``
    binding, leaving ``assertion_inference``'s separate binding, and hence
    its early check, untouched) aborts the commit with
    ``run_mapping_revoked`` rather than silently completing using a
    since-revoked mapping."""

    import research_foundry.services.assertion_materialization as materialization_mod

    run_id = "rf_run_inf_run_mapping_revoked_midflight"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])
    run_yaml_path = tmp_foundry.run_paths(run_id).run_yaml

    original_load_yaml = materialization_mod.load_yaml

    def _patched_load_yaml(path):
        doc = original_load_yaml(path)
        if str(path) == str(run_yaml_path):
            # ``materialize_inference``'s OWN early ownership check (a
            # separate ``load_yaml`` binding in assertion_inference.py, left
            # untouched by this patch) already saw the TRUE, matching
            # workspace_id -- this patch only affects the SEPARATE reload
            # `_commit_persistent_reference_locked` performs under the lock,
            # simulating a run-mapping mutation that landed between the two.
            doc = dict(doc)
            doc["workspace_id"] = "workspace-other"
        return doc

    monkeypatch.setattr(materialization_mod, "load_yaml", _patched_load_yaml)

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")

    assert result.status == "abstained"
    assert result.abstention_code == "run_mapping_revoked"
    ledger = _ledger(tmp_foundry, run_id)
    row = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
    assert row.get("persistent_references") is None


def test_commit_proof_digest_substitution_rejected_on_a_live_commit_attempt(
    tmp_foundry, monkeypatch
) -> None:
    """RPC-7.13: the locked commit routine's OWN recomputation of the
    seven-field commit-proof digest (freeze doc §17.8, `assertion_
    materialization.py:1445`) rejects a live commit whose caller-supplied
    proof was forged/substituted -- never merely persisting a caller-
    supplied digest unchecked. Forged here via a stateful monkeypatch on
    ``assertion_inference``'s OWN ``compute_commit_proof_digest`` binding
    (the CALLER's copy, used only to build its outgoing claim) -- leaving
    ``assertion_materialization``'s separate binding (used for the
    INDEPENDENT recompute-and-compare at commit time) untouched, so the two
    values are guaranteed to diverge."""

    import research_foundry.services.assertion_inference as inference_mod

    run_id = "rf_run_inf_commit_proof_substitution"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])

    monkeypatch.setattr(inference_mod, "compute_commit_proof_digest", lambda **_kwargs: "0" * 64)

    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")

    assert result.status == "abstained"
    assert result.abstention_code == "partial_write_rejected"
    # The inference record itself was staged/promoted (record-before-
    # reference, precondition 1) but the reference/pointer never landed --
    # a forged commit proof aborts BEFORE the claim_ledger write.
    ledger = _ledger(tmp_foundry, run_id)
    row = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
    assert row.get("persistent_references") is None
    assert not (tmp_foundry.run_paths(run_id).claims / ".claim_ledger_published.yaml").exists()

    monkeypatch.undo()
    retried = inferencer.materialize_inference(run_id, claim_id, producer="agent-research-1")
    assert retried.status == "materialized"
