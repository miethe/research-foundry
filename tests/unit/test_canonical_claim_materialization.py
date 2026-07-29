"""RPC-4.3/4.4: explicit-request canonical-claim resolver and durable writer.

Mirrors ``tests/unit/test_assertion_inference.py``'s fixture shape
(``tmp_foundry`` + ``ingest_source`` -> ``extraction.extract_run`` ->
``claim_mapping.build_claim_ledger`` -> ``AssertionMaterializer``) to build
real, exact-passage-bound ``source_assertion`` records, then optionally layers
a real ``inference_record`` on top (via ``AssertionInferenceMaterializer``) to
exercise ``services/canonical_claim_materialization.py`` against the contract
freeze doc's own worked identity/digest vectors (§15.2/§17.8) and its full
RPC-4.4 adversarial matrix -- attacking exclusively through the public
``resolve_support``/``publish_canonical_claim`` entry points.
"""

from __future__ import annotations

import pytest

from research_foundry.services import claim_mapping, extraction
from research_foundry.services.assertion_impact import AssertionImpactReconciler
from research_foundry.services.assertion_inference import AssertionInferenceMaterializer
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.canonical_claim_materialization import (
    CanonicalClaimMaterializationConflict,
    CanonicalClaimMaterializationInterrupted,
    CanonicalClaimMaterializer,
    compute_canonical_claim_id,
    compute_canonical_claim_version_digest,
)
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


def _enable_ledger(tmp_foundry, *, canonical_claims: bool = True) -> None:
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {
        "ledger_write_enabled": True,
        "canonical_claims_enabled": canonical_claims,
    }
    dump_yaml(foundry, tmp_foundry.foundry_yaml)


def _setup_run_with_two_supported_claims(
    tmp_foundry,
    run_id: str,
    *,
    workspace_id: str = _WORKSPACE,
    canonical_claims: bool = True,
    content_a: str = "Pediatric neutrophil counts trend lower than adult reference ranges.",
    content_b: str = "Pediatric lymphocyte counts trend higher than adult reference ranges.",
) -> None:
    """Build a run with two exact-passage ``supported`` claims, materialized.

    Content-derived assertion identity is workspace-agnostic (contract §15.2
    item 2's convention) -- a test exercising cross-workspace resolution MUST
    vary content per workspace or two workspaces mint the identical
    assertion_id.
    """

    _enable_ledger(tmp_foundry, canonical_claims=canonical_claims)
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


def _append_canonical_candidate_claim(
    tmp_foundry,
    run_id: str,
    *,
    text: str = "Pediatric CBC reference intervals differ from adult intervals.",
) -> str:
    """Append a plain, no-support ``supported``-status row that a caller may
    later explicitly canonicalize (the canonical-claim publish path never
    reads this row's own ``sources``/``inference_basis`` to auto-derive
    support -- refs are always caller-named, contract §15.4)."""

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


def _append_inference_claim(tmp_foundry, run_id: str, *, from_claims: list[str]) -> str:
    ledger_path = tmp_foundry.run_paths(run_id).claim_ledger
    ledger = load_yaml(ledger_path)
    claim_id = f"clm_{len(ledger['claims']) + 1:03d}"
    ledger["claims"].append(
        {
            "claim_id": claim_id,
            "text": "Pediatric CBC reference intervals differ from adult intervals.",
            "materiality": "material",
            "claim_type": "comparative",
            "status": "inference",
            "confidence": "medium",
            "sources": [],
            "inference_basis": {
                "from_claims": from_claims,
                "reasoning_summary": "Synthesized across two source assertions reporting age-stratified CBC intervals.",
            },
            "report_locations": [],
            "reviewer_notes": "",
        }
    )
    dump_yaml(ledger, ledger_path)
    return claim_id


def _ledger(tmp_foundry, run_id: str) -> dict:
    return load_yaml(tmp_foundry.run_paths(run_id).claim_ledger)


def _assertion_ref(tmp_foundry, run_id: str, claim_id: str, *, relation: str = "supports") -> dict:
    ledger = _ledger(tmp_foundry, run_id)
    row = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
    refs = row["persistent_references"]
    return {
        "assertion_id": refs["source_assertion_id"],
        "assertion_version": refs["assertion_version"],
        "relation": relation,
    }


# ---------------------------------------------------------------------------
# Golden vectors -- contract freeze doc §15.2 item 3 / §18.1 fixture
# ---------------------------------------------------------------------------

_CONTRACT_STATEMENT = "Pediatric CBC reference intervals differ from adult intervals."
_CONTRACT_SOURCE_REFS = [
    {
        "assertion_id": "ast_4444444444444444444444444444444444444444444444444444444444444444",
        "assertion_version": 1,
        "relation": "supports",
    }
]
_CONTRACT_INFERENCE_REFS = [
    {
        "inference_id": "inf_fd3ee362717699c116ca3eb00c4daa982396789c03040212673a3e1a86464e51",
        "inference_version": 1,
        "relation": "supports",
    }
]


def test_compute_canonical_claim_id_matches_contract_worked_vector() -> None:
    """Golden vector: contract freeze doc §15.2 item 3 / §18.1 fixture."""

    canonical_claim_id = compute_canonical_claim_id(_CONTRACT_STATEMENT, _CONTRACT_SOURCE_REFS)
    assert canonical_claim_id == "ccl_47cc4458b070a6e4e0a4b1dfb52e223e896a12b994219a7921f41334c870da15"


def test_compute_canonical_claim_version_digest_matches_contract_worked_vector() -> None:
    """Golden vector: contract freeze doc §15.2 item 3 (round-3 widened formula)."""

    digest = compute_canonical_claim_version_digest(
        _CONTRACT_STATEMENT, _CONTRACT_SOURCE_REFS, _CONTRACT_INFERENCE_REFS, "active", 1
    )
    assert digest == "86d6007be832a210049f0ec44a86479b8223c7bab23363fb00631ac0d88a84e0"

    # SOL-26 tamper re-run: a version-integer-only mutation must change the digest.
    tampered = compute_canonical_claim_version_digest(
        _CONTRACT_STATEMENT, _CONTRACT_SOURCE_REFS, _CONTRACT_INFERENCE_REFS, "active", 999
    )
    assert tampered == "6096c0279b7267810a3a2bc9fa4fb17928be2dad1196b08c598cf0a7e27d4108"
    assert tampered != digest


def test_canonical_claim_id_excludes_state_and_version_fields() -> None:
    """Entity identity (§15.2 item 3) is stable across state/version changes --
    only ``version_digest`` moves when ``state`` changes."""

    id_v1 = compute_canonical_claim_id(_CONTRACT_STATEMENT, _CONTRACT_SOURCE_REFS)
    digest_active = compute_canonical_claim_version_digest(
        _CONTRACT_STATEMENT, _CONTRACT_SOURCE_REFS, None, "active", 1
    )
    digest_reviewed = compute_canonical_claim_version_digest(
        _CONTRACT_STATEMENT, _CONTRACT_SOURCE_REFS, None, "reviewed", 1
    )
    # Entity id is invariant to state; the id formula never even sees "state".
    assert id_v1 == compute_canonical_claim_id(_CONTRACT_STATEMENT, _CONTRACT_SOURCE_REFS)
    assert digest_active != digest_reviewed


# ---------------------------------------------------------------------------
# resolve_support -- explicit, no auto-derivation, full typed-skip coverage
# ---------------------------------------------------------------------------


def test_resolve_support_exact_match(tmp_foundry) -> None:
    run_id = "rf_run_ccl_exact"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = materializer.resolve_support([ref])

    assert resolution.status == "resolved"
    assert len(resolution.source_assertion_refs) == 1
    assert resolution.digest


def test_resolve_support_with_inference_refs(tmp_foundry) -> None:
    """Canonical claim citing BOTH a source assertion and a real inference
    (typed separately, never conflated -- see also the end-to-end test's own
    ``inference_refs``-vs-``source_assertion_refs`` key-separation assertion)."""

    run_id = "rf_run_ccl_with_inference"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    inf_claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])
    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    inf_result = inferencer.materialize_inference(run_id, inf_claim_id, producer="agent-research-1")
    assert inf_result.status == "materialized"

    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")
    inference_ref = {
        "inference_id": inf_result.inference_id,
        "inference_version": inf_result.inference_version,
        "relation": "supports",
    }

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = materializer.resolve_support([ref], [inference_ref])

    assert resolution.status == "resolved"
    assert len(resolution.source_assertion_refs) == 1
    assert len(resolution.inference_refs) == 1
    assert resolution.inference_refs[0]["inference_id"] == inf_result.inference_id


def test_resolve_support_empty_support(tmp_foundry) -> None:
    run_id = "rf_run_ccl_empty"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = materializer.resolve_support([], None)

    assert resolution.status == "skipped"
    assert resolution.skip_code == "empty_support"


def test_resolve_support_unresolved_support_ref(tmp_foundry) -> None:
    run_id = "rf_run_ccl_unresolved"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = materializer.resolve_support(
        [{"assertion_id": "ast_" + "0" * 64, "assertion_version": 1, "relation": "supports"}]
    )

    assert resolution.status == "skipped"
    assert resolution.skip_code == "unresolved_support_ref"


def test_resolve_support_stale_support(tmp_foundry) -> None:
    run_id = "rf_run_ccl_stale"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    materializer_p3 = AssertionMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion_path = materializer_p3._assertion_path(ref["assertion_id"])
    assertion = load_yaml(assertion_path)
    assertion["lifecycle_state"] = "invalidated"
    dump_yaml(assertion, assertion_path)

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = materializer.resolve_support([ref])

    assert resolution.status == "skipped"
    assert resolution.skip_code == "stale_support"


def test_resolve_support_mixed_workspace_support(tmp_foundry) -> None:
    run_a = "rf_run_ccl_mixed_a"
    run_b = "rf_run_ccl_mixed_b"
    _setup_run_with_two_supported_claims(tmp_foundry, run_a, workspace_id="workspace-a")
    _setup_run_with_two_supported_claims(
        tmp_foundry,
        run_b,
        workspace_id="workspace-b",
        content_a="Adult neutrophil counts differ from a completely separate corpus.",
        content_b="Adult lymphocyte counts differ from a completely separate corpus too.",
    )
    foreign_ref = _assertion_ref(tmp_foundry, run_b, "clm_001")

    materializer = CanonicalClaimMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    resolution = materializer.resolve_support([foreign_ref])

    assert resolution.status == "skipped"
    assert resolution.skip_code == "mixed_workspace_support"


def test_resolve_support_ambiguous_support(tmp_foundry) -> None:
    """Two named bases disagree on polarity (supports vs. contradicts) with
    no caller-supplied adjudication -- rejected, never auto-resolved."""

    run_id = "rf_run_ccl_ambiguous"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_supports = _assertion_ref(tmp_foundry, run_id, "clm_001", relation="supports")
    ref_contradicts = _assertion_ref(tmp_foundry, run_id, "clm_002", relation="contradicts")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = materializer.resolve_support([ref_supports, ref_contradicts])

    assert resolution.status == "skipped"
    assert resolution.skip_code == "ambiguous_support"

    # Explicit caller override resolves the ambiguity (documented escape hatch).
    resolved = materializer.resolve_support([ref_supports, ref_contradicts], allow_mixed_relations=True)
    assert resolved.status == "resolved"


def test_resolve_support_conflicting_support(tmp_foundry) -> None:
    """Every named base OPPOSES the statement -- nothing actually backs an
    'active' canonical claim, so this is rejected, distinct from ambiguous_support."""

    run_id = "rf_run_ccl_conflicting"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001", relation="contradicts")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = materializer.resolve_support([ref])

    assert resolution.status == "skipped"
    assert resolution.skip_code == "conflicting_support"


def test_resolve_support_invalid_candidate_shape(tmp_foundry) -> None:
    run_id = "rf_run_ccl_invalid_shape"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = materializer.resolve_support([{"assertion_id": "not-a-real-id"}])

    assert resolution.status == "skipped"
    assert resolution.skip_code == "invalid_canonical_claim_candidate"


# ---------------------------------------------------------------------------
# publish_canonical_claim -- end-to-end, identity/digest, durable-commit
# ---------------------------------------------------------------------------


def test_publish_canonical_claim_end_to_end(tmp_foundry) -> None:
    run_id = "rf_run_ccl_e2e"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")
    inf_claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])
    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    inf_result = inferencer.materialize_inference(run_id, inf_claim_id, producer="agent-research-1")
    inference_ref = {
        "inference_id": inf_result.inference_id,
        "inference_version": inf_result.inference_version,
        "relation": "supports",
    }

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = materializer.publish_canonical_claim(
        run_id,
        claim_id,
        statement=_CONTRACT_STATEMENT,
        source_assertion_refs=[ref],
        inference_refs=[inference_ref],
        explicit_request=True,
    )

    assert result.status == "materialized"
    assert result.canonical_claim_id is not None
    assert result.canonical_claim_id.startswith("ccl_")
    assert result.canonical_claim_version == 1
    assert result.generation_id is not None
    assert result.generation_id.startswith("clg_")

    # Durable record promoted + schema-valid, at the entity/per-version path.
    record_path = materializer.root / "canonical_claims" / result.canonical_claim_id / "1.yaml"
    assert record_path.is_file()
    record = load_yaml(record_path)
    assert materializer.schemas.validate(record, "canonical_claim").ok
    assert record["state"] == "active"
    assert record["version_digest"]

    # Inference/source separation (RPC-4.4): the record's inference support is
    # typed on its OWN key, never folded into source_assertion_refs.
    assert record["source_assertion_refs"] == [ref]
    assert record["inference_refs"] == [inference_ref]

    # Generation-manifest entry recorded (§17.7a).
    manifest = load_yaml(materializer.root / "canonical_claims" / ".generation_manifest.yaml")
    assert any(
        entry["record_id"] == result.canonical_claim_id and entry["version"] == 1
        for entry in manifest["entries"]
    )

    # claim_ledger row committed with the atomic (canonical_claim_id, canonical_claim_version) pair.
    ledger = _ledger(tmp_foundry, run_id)
    row = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
    refs = row["persistent_references"]
    assert refs["canonical_claim_id"] == result.canonical_claim_id
    assert refs["canonical_claim_version"] == 1

    # Claim-ledger generation pointer + snapshot published (§17.7 step 4).
    pointer = load_yaml(tmp_foundry.run_paths(run_id).claims / ".claim_ledger_published.yaml")
    assert pointer["generation_id"] == result.generation_id


def test_publish_canonical_claim_is_idempotent_on_replay(tmp_foundry) -> None:
    run_id = "rf_run_ccl_replay"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    first = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[ref], explicit_request=True
    )
    second = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[ref], explicit_request=True
    )

    assert first.status == second.status == "materialized"
    assert first.canonical_claim_id == second.canonical_claim_id
    assert first.generation_id == second.generation_id


def test_publish_canonical_claim_replay_conflict_is_a_typed_abstain(tmp_foundry) -> None:
    run_id = "rf_run_ccl_conflict"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    ledger_path = tmp_foundry.run_paths(run_id).claim_ledger
    ledger = load_yaml(ledger_path)
    row = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
    row["persistent_references"] = {
        "canonical_claim_id": "ccl_" + "9" * 64,
        "canonical_claim_version": 1,
    }
    dump_yaml(ledger, ledger_path)

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[ref], explicit_request=True
    )

    assert result.status == "abstained"
    assert result.abstention_code == "replay_conflict"


def test_publish_canonical_claim_implicit_merge_rejected_by_default(tmp_foundry) -> None:
    """Contract §15.4: never automatic or inferred -- the safe DEFAULT
    (``explicit_request`` omitted) is rejected before anything is even read."""

    run_id = "rf_run_ccl_implicit"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[ref]
    )

    assert result.status == "abstained"
    assert result.abstention_code == "implicit_merge_rejected"
    assert not (materializer.root / "canonical_claims").exists()
    assert not (materializer.root / ".staging").exists()


def test_publish_canonical_claim_flags_denied_canonical_claims_disabled(tmp_foundry) -> None:
    run_id = "rf_run_ccl_disabled"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id, canonical_claims=False)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[ref], explicit_request=True
    )

    assert result.status == "abstained"
    assert result.abstention_code == "canonical_claims_disabled"
    assert not (materializer.root / "canonical_claims").exists()


def test_publish_canonical_claim_ledger_write_disabled_also_denies(tmp_foundry) -> None:
    """``canonical_claims_allowed`` requires ``ledger_write_enabled`` too
    (config.py's own AND-resolution) -- flipping the base flag off denies
    canonical publication the SAME way as flipping canonical_claims_enabled
    off does."""

    run_id = "rf_run_ccl_ledger_disabled"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {
        "ledger_write_enabled": False,
        "canonical_claims_enabled": True,
    }
    dump_yaml(foundry, tmp_foundry.foundry_yaml)

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[ref], explicit_request=True
    )

    assert result.status == "abstained"
    assert result.abstention_code == "canonical_claims_disabled"


def test_publish_canonical_claim_run_workspace_mismatch_abstains(tmp_foundry) -> None:
    run_id = "rf_run_ccl_workspace_mismatch"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")
    _write_run_yaml(tmp_foundry, run_id, workspace_id="workspace-other")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[ref], explicit_request=True
    )

    assert result.status == "abstained"
    assert result.abstention_code == "run_workspace_mismatch"


def test_publish_canonical_claim_producer_omission_is_not_applicable(tmp_foundry) -> None:
    """``canonical_claim`` has no ``reasoning``/``producer`` field at all
    (§18: ``producer_omitted`` applies to inference only) -- a canonical
    publish call has no such parameter to omit in the first place."""

    run_id = "rf_run_ccl_no_producer_param"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[ref], explicit_request=True
    )

    assert result.status == "materialized"
    assert result.canonical_claim_id is not None
    record = load_yaml(materializer.root / "canonical_claims" / result.canonical_claim_id / "1.yaml")
    assert "reasoning" not in record and "producer" not in record


def test_publish_canonical_claim_empty_support_abstains(tmp_foundry) -> None:
    run_id = "rf_run_ccl_publish_empty"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[], explicit_request=True
    )

    assert result.status == "abstained"
    assert result.abstention_code == "empty_support"


def test_publish_canonical_claim_mixed_workspace_support_abstains(tmp_foundry) -> None:
    run_a = "rf_run_ccl_publish_mixed_a"
    run_b = "rf_run_ccl_publish_mixed_b"
    _setup_run_with_two_supported_claims(tmp_foundry, run_a, workspace_id="workspace-a")
    _setup_run_with_two_supported_claims(
        tmp_foundry,
        run_b,
        workspace_id="workspace-b",
        content_a="Adult neutrophil counts differ from a totally separate corpus entirely.",
        content_b="Adult lymphocyte counts differ from a totally separate corpus entirely too.",
    )
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_a)
    foreign_ref = _assertion_ref(tmp_foundry, run_b, "clm_001")

    materializer = CanonicalClaimMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    result = materializer.publish_canonical_claim(
        run_a,
        claim_id,
        statement=_CONTRACT_STATEMENT,
        source_assertion_refs=[foreign_ref],
        explicit_request=True,
    )

    assert result.status == "abstained"
    assert result.abstention_code == "mixed_workspace_support"


def test_publish_canonical_claim_ambiguous_support_abstains(tmp_foundry) -> None:
    run_id = "rf_run_ccl_publish_ambiguous"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref_supports = _assertion_ref(tmp_foundry, run_id, "clm_001", relation="supports")
    ref_contradicts = _assertion_ref(tmp_foundry, run_id, "clm_002", relation="contradicts")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = materializer.publish_canonical_claim(
        run_id,
        claim_id,
        statement=_CONTRACT_STATEMENT,
        source_assertion_refs=[ref_supports, ref_contradicts],
        explicit_request=True,
    )

    assert result.status == "abstained"
    assert result.abstention_code == "ambiguous_support"
    assert not (materializer.root / "canonical_claims").exists()


def test_publish_canonical_claim_conflicting_support_abstains(tmp_foundry) -> None:
    run_id = "rf_run_ccl_publish_conflicting"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001", relation="contradicts")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[ref], explicit_request=True
    )

    assert result.status == "abstained"
    assert result.abstention_code == "conflicting_support"


def test_publish_canonical_claim_substitution_rejected(tmp_foundry) -> None:
    """A prior candidate/base is substituted for a DIFFERENT one after
    initial resolution, before publish -- rejected, never silently published
    against a support set that no longer matches what was verified eligible."""

    run_id = "rf_run_ccl_substitution"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")
    ref_b = _assertion_ref(tmp_foundry, run_id, "clm_002")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    prior_resolution = materializer.resolve_support([ref_a])
    assert prior_resolution.status == "resolved"

    # Attacker/bug substitutes a DIFFERENT, independently-valid base before
    # the actual publish call -- both individually resolve fine, but this is
    # not the support set that was originally verified eligible.
    result = materializer.publish_canonical_claim(
        run_id,
        claim_id,
        statement=_CONTRACT_STATEMENT,
        source_assertion_refs=[ref_b],
        explicit_request=True,
        previously_resolved=prior_resolution,
    )

    assert result.status == "abstained"
    assert result.abstention_code == "substitution_rejected"
    assert not (materializer.root / "canonical_claims").exists()

    # The IDENTICAL prior resolution against the SAME refs is not a substitution.
    honest = materializer.publish_canonical_claim(
        run_id,
        claim_id,
        statement=_CONTRACT_STATEMENT,
        source_assertion_refs=[ref_a],
        explicit_request=True,
        previously_resolved=prior_resolution,
    )
    assert honest.status == "materialized"


# ---------------------------------------------------------------------------
# Crash-injection / recovery (contract §17.7 step 6 -- "kill-between-steps")
# ---------------------------------------------------------------------------


def test_interrupted_after_staging_is_quarantined_and_replay_converges(tmp_foundry) -> None:
    run_id = "rf_run_ccl_crash_stage"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    with pytest.raises(CanonicalClaimMaterializationInterrupted):
        materializer.publish_canonical_claim(
            run_id,
            claim_id,
            statement=_CONTRACT_STATEMENT,
            source_assertion_refs=[ref],
            explicit_request=True,
            _interrupt_after_staging=True,
        )

    # No orphan visible as a promoted, citable record.
    canonical_dir = materializer.root / "canonical_claims"
    assert not canonical_dir.exists() or not any(canonical_dir.rglob("*.yaml"))
    assert any((materializer.root / ".staging").iterdir())

    quarantined = materializer.recover_orphaned_canonical_claims()
    assert len(quarantined) == 1
    assert not (materializer.root / ".staging").exists() or not any(
        (materializer.root / ".staging").iterdir()
    )

    # A fresh retry (no interrupt) converges: full success from scratch, no
    # silent adoption of the quarantined orphan.
    result = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[ref], explicit_request=True
    )
    assert result.status == "materialized"


def test_interrupted_before_manifest_is_quarantined_and_replay_converges(tmp_foundry) -> None:
    run_id = "rf_run_ccl_crash_manifest"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    with pytest.raises(CanonicalClaimMaterializationInterrupted):
        materializer.publish_canonical_claim(
            run_id,
            claim_id,
            statement=_CONTRACT_STATEMENT,
            source_assertion_refs=[ref],
            explicit_request=True,
            _interrupt_before_manifest=True,
        )

    # Promoted (discoverable on disk) but NOT yet manifest-referenced --
    # quarantine-eligible, never silently citable (§17.7 step 2).
    promoted = list((materializer.root / "canonical_claims").rglob("*.yaml"))
    assert len(promoted) == 1

    quarantined = materializer.recover_orphaned_canonical_claims()
    assert len(quarantined) == 1
    assert not list((materializer.root / "canonical_claims").rglob("*.yaml"))

    result = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[ref], explicit_request=True
    )
    assert result.status == "materialized"


def test_conflicting_promoted_canonical_claim_record_raises(tmp_foundry) -> None:
    """A promoted record whose bytes no longer match its own content-addressed
    id is a genuine corruption/substitution conflict -- raised, never
    silently accepted (RPC-4.4: 'substitution ... detected via manifest')."""

    run_id = "rf_run_ccl_conflicting_record"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    first = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[ref], explicit_request=True
    )
    assert first.canonical_claim_id is not None
    record_path = materializer.root / "canonical_claims" / first.canonical_claim_id / "1.yaml"
    tampered = load_yaml(record_path)
    tampered["statement"] = "Tampered statement text."
    dump_yaml(tampered, record_path)

    # Force the ledger row back to unset so the writer re-attempts promotion.
    ledger_path = tmp_foundry.run_paths(run_id).claim_ledger
    ledger = load_yaml(ledger_path)
    row = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
    row["persistent_references"] = None
    dump_yaml(ledger, ledger_path)

    with pytest.raises(CanonicalClaimMaterializationConflict, match="conflicting_canonical_claim_record"):
        materializer.publish_canonical_claim(
            run_id,
            claim_id,
            statement=_CONTRACT_STATEMENT,
            source_assertion_refs=[ref],
            explicit_request=True,
        )


# ---------------------------------------------------------------------------
# gpt-5.6-terra fix-cycle 2 (rpc-terra-p4-findings.md T4-2/T4-3/T4-4) --
# frozen staging/quarantine paths, manifest-authority inversion crash
# boundaries, and the shared commit-time transitive-support recheck
# (canonical -> its inferences -> their OWN source_assertion_refs). T4-1 is
# covered in test_assertion_materialization.py.
# ---------------------------------------------------------------------------


def test_staging_and_quarantine_paths_match_frozen_contract_shape(tmp_foundry) -> None:
    """T4-3: canonical staging/quarantine paths previously diverged from
    contract §17.7's frozen shape (``<id>-v<version>/<version>.yaml`` staging,
    ``<id>-v<version>`` quarantine) -- fixed to ``.staging/<record_id>/<record_id>.yaml``
    and ``quarantine/<record_id>/`` respectively, matching
    ``AssertionInferenceMaterializer``'s own convention exactly."""

    run_id = "rf_run_ccl_frozen_paths"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    with pytest.raises(CanonicalClaimMaterializationInterrupted):
        materializer.publish_canonical_claim(
            run_id,
            claim_id,
            statement=_CONTRACT_STATEMENT,
            source_assertion_refs=[ref],
            explicit_request=True,
            _interrupt_after_staging=True,
        )

    canonical_claim_id = compute_canonical_claim_id(_CONTRACT_STATEMENT, [ref])
    staging_path = materializer._staging_path(canonical_claim_id, 1)
    assert staging_path == materializer.root / ".staging" / canonical_claim_id / f"{canonical_claim_id}.yaml"
    assert staging_path.is_file()

    quarantined = materializer.recover_orphaned_canonical_claims()
    assert quarantined == (canonical_claim_id,)
    quarantine_dir = materializer.root / "quarantine" / canonical_claim_id
    assert quarantine_dir.is_dir()
    assert (quarantine_dir / f"{canonical_claim_id}.yaml").is_file()


def test_interrupted_after_manifest_pre_ledger_is_quarantined_and_replay_converges(tmp_foundry) -> None:
    """T4-3 NEW crash boundary (post-manifest/pre-ledger): the generation-
    manifest entry is written, but the claim-ledger reference is NOT.
    Recovery authority is the claim-ledger's CURRENT generation -- this
    record is quarantine-eligible even though its manifest entry exists."""

    run_id = "rf_run_ccl_crash_manifest_pre_ledger"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    with pytest.raises(CanonicalClaimMaterializationInterrupted):
        materializer.publish_canonical_claim(
            run_id,
            claim_id,
            statement=_CONTRACT_STATEMENT,
            source_assertion_refs=[ref],
            explicit_request=True,
            _interrupt_after_manifest=True,
        )

    manifest = load_yaml(materializer.root / "canonical_claims" / ".generation_manifest.yaml")
    assert manifest["entries"]
    ledger = _ledger(tmp_foundry, run_id)
    row = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
    assert row.get("persistent_references") is None
    assert not (tmp_foundry.run_paths(run_id).claims / ".claim_ledger_published.yaml").exists()

    canonical_claim_id = compute_canonical_claim_id(_CONTRACT_STATEMENT, [ref])
    quarantined = materializer.recover_orphaned_canonical_claims()
    assert quarantined == (f"{canonical_claim_id}-v1",)
    assert not (materializer.root / "canonical_claims" / canonical_claim_id / "1.yaml").exists()
    assert (materializer.root / "quarantine" / canonical_claim_id / "1.yaml").is_file()

    result = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[ref], explicit_request=True
    )
    assert result.status == "materialized"


def test_interrupted_after_ledger_pre_pointer_republishes_pointer_on_retry(tmp_foundry) -> None:
    """T4-3 NEW crash boundary (post-ledger/pre-pointer): the claim_ledger
    reference is written, but the generation pointer is NOT yet swapped. A
    retry re-publishes the pointer idempotently rather than double-writing
    the reference."""

    run_id = "rf_run_ccl_crash_ledger_pre_pointer"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    with pytest.raises(CanonicalClaimMaterializationInterrupted):
        materializer.publish_canonical_claim(
            run_id,
            claim_id,
            statement=_CONTRACT_STATEMENT,
            source_assertion_refs=[ref],
            explicit_request=True,
            _interrupt_after_ledger=True,
        )

    ledger = _ledger(tmp_foundry, run_id)
    row = next(c for c in ledger["claims"] if c["claim_id"] == claim_id)
    assert row["persistent_references"]["canonical_claim_id"] is not None
    assert not (tmp_foundry.run_paths(run_id).claims / ".claim_ledger_published.yaml").exists()

    result = materializer.publish_canonical_claim(
        run_id, claim_id, statement=_CONTRACT_STATEMENT, source_assertion_refs=[ref], explicit_request=True
    )
    assert result.status == "materialized"
    pointer = load_yaml(tmp_foundry.run_paths(run_id).claims / ".claim_ledger_published.yaml")
    assert pointer["generation_id"] == result.generation_id


def test_publish_canonical_claim_transitive_inference_support_staleness_is_rejected(tmp_foundry) -> None:
    """T4-4: the shared commit-time recheck walks THROUGH a referenced
    inference to its OWN ``source_assertion_refs`` -- ``resolve_support``
    only checks the inference's immediate ``status`` (still ``active`` here),
    never its nested support, so resolution alone would let this through.
    The commit routine's transitive recheck catches it, yielding the SAME
    ``stale_support`` code the direct-source-assertion case uses."""

    run_id = "rf_run_ccl_transitive_stale"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    inf_claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001", "clm_002"])
    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    inf_result = inferencer.materialize_inference(run_id, inf_claim_id, producer="agent-research-1")
    assert inf_result.status == "materialized"
    inference_ref = {
        "inference_id": inf_result.inference_id,
        "inference_version": inf_result.inference_version,
        "relation": "supports",
    }
    # A second, UNRELATED, still-eligible source-assertion ref (canonical_claim
    # requires >=1 source_assertion_refs, contract §15.4/schema minItems: 1) --
    # only the inference ref's TRANSITIVE support is stale.
    other_ref = _assertion_ref(tmp_foundry, run_id, "clm_002")

    # Invalidate ONE of the inference's OWN source assertions -- the
    # inference_record's own `status` stays "active" (nothing marks it
    # stale automatically); only the transitive recheck notices.
    ledger = _ledger(tmp_foundry, run_id)
    base_claim = next(c for c in ledger["claims"] if c["claim_id"] == "clm_001")
    assertion_id = base_claim["persistent_references"]["source_assertion_id"]
    assertion_materializer = AssertionMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion_path = assertion_materializer._assertion_path(assertion_id)
    assertion = load_yaml(assertion_path)
    assertion["lifecycle_state"] = "invalidated"
    dump_yaml(assertion, assertion_path)

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = materializer.resolve_support([other_ref], [inference_ref])
    assert resolution.status == "resolved"  # resolution alone misses it

    result = materializer.publish_canonical_claim(
        run_id,
        claim_id,
        statement=_CONTRACT_STATEMENT,
        source_assertion_refs=[other_ref],
        inference_refs=[inference_ref],
        explicit_request=True,
    )

    assert result.status == "abstained"
    assert result.abstention_code == "stale_support"
    ledger_after = _ledger(tmp_foundry, run_id)
    row = next(c for c in ledger_after["claims"] if c["claim_id"] == claim_id)
    assert row.get("persistent_references") is None


def test_publish_canonical_claim_rejects_a_real_p6_marked_stale_inference(tmp_foundry) -> None:
    """F18 (RPC-6.G validator, N7): a NEW canonical claim citing an inference
    P6 has marked stale via a completed ``mark_stale`` effect receipt must be
    rejected at commit time -- even though the inference's own on-disk
    ``status`` field never flips (P6 records staleness ONLY as a durable
    effect receipt, never a record mutation). Driven through a REAL
    ``AssertionImpactReconciler.reconcile()`` flow, never a hand-authored
    ``status: stale`` -- the exact fixture-fidelity rule the validator
    required, since raw-status-only rechecks are precisely what missed this."""

    run_id = "rf_run_ccl_f18_p6_stale"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")
    ref_b = _assertion_ref(tmp_foundry, run_id, "clm_002")

    inf_claim_id = _append_inference_claim(tmp_foundry, run_id, from_claims=["clm_001"])
    inferencer = AssertionInferenceMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    inf_result = inferencer.materialize_inference(run_id, inf_claim_id, producer="agent-research-1")
    assert inf_result.status == "materialized"
    inference_ref = {
        "inference_id": inf_result.inference_id,
        "inference_version": inf_result.inference_version,
        "relation": "supports",
    }

    # A real P6 lifecycle event blocks ref_a's assertion -- reconcile() marks
    # inf_result stale via a COMPLETED mark_stale effect receipt (it cites
    # ref_a in its own source_assertion_refs, from `from_claims=["clm_001"]`).
    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion = load_yaml(reconciler.root / "assertions" / f"{ref_a['assertion_id']}.yaml")
    event_id = "evt_ccl_f18_p6_stale"
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
                "id": ref_a["assertion_id"],
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
    reconcile_result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert reconcile_result.status == "completed"

    inference_record = load_yaml(reconciler.root / "inferences" / f"{inf_result.inference_id}.yaml")
    assert inference_record["status"] == "active"  # N7: never mutated on disk

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    # SOL-39: resolve_support() now ALSO consults the SAME strict effective
    # stale-inference-ids the commit-time recheck below computes
    # (`collect_stale_object_ids(strict=True)`) -- resolution itself catches
    # this P6-marked-stale inference now, never merely the later commit
    # (all-writer consistency, contract §17.1 item 6).
    resolution = materializer.resolve_support([ref_b], [inference_ref])
    assert resolution.status == "skipped"
    assert resolution.skip_code == "stale_support"

    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id, text="Cites a P6-staled inference.")
    publish_result = materializer.publish_canonical_claim(
        run_id,
        claim_id,
        statement="Cites a P6-staled inference.",
        source_assertion_refs=[ref_b],
        inference_refs=[inference_ref],
        explicit_request=True,
    )

    assert publish_result.status == "abstained"
    assert publish_result.abstention_code == "stale_support"
    ledger_after = _ledger(tmp_foundry, run_id)
    row = next(c for c in ledger_after["claims"] if c["claim_id"] == claim_id)
    assert row.get("persistent_references") is None


# ---------------------------------------------------------------------------
# F19 (RPC-6.G validator, Karen K-1, HIGH) -- Karen's exact attack: a NEW
# canonical claim directly citing a P6-authoritatively-BLOCKED source
# assertion, whose immutable record never flips its own `lifecycle_state`.
# ---------------------------------------------------------------------------


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


def test_publish_canonical_claim_rejects_a_real_p6_policy_blocked_source_assertion(tmp_foundry) -> None:
    """F19 (RPC-6.G validator, Karen K-1, HIGH): Karen's exact repro -- a NEW
    canonical claim directly citing a source assertion P6 has authoritatively
    blocked (``lifecycle_policy/<id>.yaml``) must be rejected at BOTH resolve
    time and commit time, even though the assertion's own immutable
    ``assertions/<id>.yaml`` record's ``lifecycle_state`` never flips (P6's
    block boundary lives ONLY in the separate policy artifact -- the same
    "immutable record never mutated" pattern F18 already established for
    inference/canonical-claim staleness). Driven through a REAL
    ``AssertionImpactReconciler.reconcile()`` flow -- never a hand-authored
    ``lifecycle_state: blocked`` (see ``test_resolve_support_stale_support``
    above for the raw-record-mutation case this is symmetric to, but
    distinct from)."""

    run_id = "rf_run_ccl_f19_p6_blocked"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")

    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion = load_yaml(reconciler.root / "assertions" / f"{ref_a['assertion_id']}.yaml")
    event_id = "evt_ccl_f19_p6_blocked"
    dump_yaml(_lifecycle_event_for(assertion, event_id), reconciler.event_path(event_id))
    # Nothing cites ref_a yet -- an explicit empty manifest so the receipt
    # itself completes (never blocked on `dependency_manifest_missing`);
    # irrelevant to what this test checks, since `reconcile()` ALWAYS writes
    # the policy artifact BEFORE that outcome is even computed (see its own
    # "immutable source assertion is never overwritten" comment).
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text('{"expected_objects": []}', encoding="utf-8")
    reconcile_result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert reconcile_result.status == "completed"

    policy = load_yaml(reconciler.root / "lifecycle_policy" / f"{ref_a['assertion_id']}.yaml")
    assert policy["invalidation_state"] == "blocked"
    assert policy["lifecycle_state"] == "blocked"

    # The immutable record itself is untouched -- Karen's exact repro relies
    # on this: a naive raw-record-only recheck sees `lifecycle_state:
    # eligible` and lets the citation through.
    assert (
        load_yaml(reconciler.root / "assertions" / f"{ref_a['assertion_id']}.yaml")["lifecycle_state"] == "eligible"
    )

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    resolution = materializer.resolve_support([ref_a])
    assert resolution.status == "skipped"
    assert resolution.skip_code == "stale_support"

    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id, text="Directly cites a P6-blocked assertion.")
    publish_result = materializer.publish_canonical_claim(
        run_id,
        claim_id,
        statement="Directly cites a P6-blocked assertion.",
        source_assertion_refs=[ref_a],
        explicit_request=True,
    )

    assert publish_result.status == "abstained"
    assert publish_result.abstention_code == "stale_support"
    ledger_after = _ledger(tmp_foundry, run_id)
    row = next(c for c in ledger_after["claims"] if c["claim_id"] == claim_id)
    assert row.get("persistent_references") is None


def test_publish_canonical_claim_commit_path_fails_closed_on_corrupt_impact_receipt(tmp_foundry) -> None:
    """K-2 (Karen Wave-3 gate, MEDIUM): the commit-time recheck's
    ``collect_stale_object_ids(strict=True)`` call fails CLOSED when ANY
    impact-operations receipt in this workspace is present but corrupt --
    even for a NEW canonical claim citing a DIFFERENT, still-eligible
    assertion. This is a deliberately conservative, workspace-wide posture
    (governance-ledger corruption is refused rather than risking a silent
    un-stale of the exact object it concerns) -- documented design choice,
    not a narrower per-object scope."""

    run_id = "rf_run_ccl_k2_commit_strict"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    ref_a = _assertion_ref(tmp_foundry, run_id, "clm_001")
    ref_b = _assertion_ref(tmp_foundry, run_id, "clm_002")

    reconciler = AssertionImpactReconciler(workspace_id=_WORKSPACE, paths=tmp_foundry)
    assertion = load_yaml(reconciler.root / "assertions" / f"{ref_a['assertion_id']}.yaml")
    event_id = "evt_ccl_k2_commit_strict"
    dump_yaml(_lifecycle_event_for(assertion, event_id), reconciler.event_path(event_id))
    reconciler.manifest_path(event_id).parent.mkdir(parents=True, exist_ok=True)
    reconciler.manifest_path(event_id).write_text('{"expected_objects": []}', encoding="utf-8")
    result = reconciler.reconcile(assertion_id=ref_a["assertion_id"], event_id=event_id)
    assert result.status == "completed"

    # Corrupt the (now on-disk) receipt -- present, but no longer a valid
    # authoritative record.
    reconciler.receipt_path(event_id).write_text('{"not": "a-valid-receipt"}', encoding="utf-8")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    # Resolution alone still succeeds -- `resolve_support` only reads
    # `ref_b`'s own record and its policy file (both untouched); it never
    # scans `impact_operations/`.
    resolution = materializer.resolve_support([ref_b])
    assert resolution.status == "resolved"

    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id, text="Cites an unrelated, eligible assertion.")
    publish_result = materializer.publish_canonical_claim(
        run_id,
        claim_id,
        statement="Cites an unrelated, eligible assertion.",
        source_assertion_refs=[ref_b],
        explicit_request=True,
    )

    assert publish_result.status == "abstained"
    assert publish_result.abstention_code == "stale_support"
    ledger_after = _ledger(tmp_foundry, run_id)
    row = next(c for c in ledger_after["claims"] if c["claim_id"] == claim_id)
    assert row.get("persistent_references") is None


# ---------------------------------------------------------------------------
# RPC-7.15 gap-fill (ac-evidence-map.md): mirrors
# test_assertion_inference.py's
# test_materialized_inference_version_digest_recomputes_and_matches_manifest_
# entry -- the golden-vector digest tests above only exercise the pure
# formula function against fixed frozen inputs. RPC-7.15 (freeze doc §17.9)
# additionally requires proving a REAL P4-written canonical_claim record's
# stored version_digest recomputes from its own persisted fields AND
# matches its generation-manifest entry.
# ---------------------------------------------------------------------------


def test_materialized_canonical_claim_version_digest_recomputes_and_matches_manifest_entry(
    tmp_foundry,
) -> None:
    """RPC-7.15: a real P4-written ``canonical_claim`` record's
    ``version_digest`` (a) recomputes to its own stored value from the
    record's own persisted fields via
    ``compute_canonical_claim_version_digest``, and (b) matches the
    ``version_digest`` recorded in its generation-manifest entry (§17.7a)."""

    run_id = "rf_run_ccl_digest_recomputes_matches_manifest"
    _setup_run_with_two_supported_claims(tmp_foundry, run_id)
    claim_id = _append_canonical_candidate_claim(tmp_foundry, run_id)
    ref = _assertion_ref(tmp_foundry, run_id, "clm_001")

    materializer = CanonicalClaimMaterializer(workspace_id=_WORKSPACE, paths=tmp_foundry)
    result = materializer.publish_canonical_claim(
        run_id,
        claim_id,
        statement=_CONTRACT_STATEMENT,
        source_assertion_refs=[ref],
        explicit_request=True,
    )
    assert result.status == "materialized"

    record_path = materializer.root / "canonical_claims" / result.canonical_claim_id / "1.yaml"
    record = load_yaml(record_path)
    # Mirrors the production call site exactly (services/canonical_claim_
    # materialization.py's own `resolution.inference_refs or None`): an
    # absent/empty `inference_refs` key recomputes against `None`, not `[]`.
    recomputed = compute_canonical_claim_version_digest(
        record["statement"],
        record["source_assertion_refs"],
        record.get("inference_refs") or None,
        record["state"],
        record["canonical_claim_version"],
    )
    assert recomputed == record["version_digest"]

    manifest = load_yaml(materializer.root / "canonical_claims" / ".generation_manifest.yaml")
    entry = next(
        e
        for e in manifest["entries"]
        if e["record_id"] == result.canonical_claim_id
        and e["version"] == record["canonical_claim_version"]
    )
    assert entry["version_digest"] == record["version_digest"] == recomputed
