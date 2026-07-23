"""CARP-2 privacy/integrity matrix for the governed catalog adapter (catalog_retrieval.py).

Every denial case asserts positively that candidate-derived counters/lists
are ``0``/absent -- not merely that the call didn't raise (CARP-2.3).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.services import claim_mapping, extraction
from research_foundry.services.assertion_catalog import AssertionCatalog, AssertionCatalogDenied
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.catalog_retrieval import (
    RetrievalConstraints,
    RetrievalLimits,
    RetrievalQuestion,
    catalog_receipt,
    peek_catalog_generation_id,
    retrieve,
)
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


def _assertion_path(tmp_foundry, assertion_id: str) -> Path:
    return next((tmp_foundry.root / "assertion_ledger" / "workspaces").glob(f"*/assertions/{assertion_id}.yaml"))


def _edition_path(tmp_foundry) -> Path:
    return next((tmp_foundry.root / "assertion_ledger" / "workspaces").glob("*/sources/*/editions/*.yaml"))


def _mutate_assertion(tmp_foundry, assertion_id: str, **overrides: object) -> None:
    path = _assertion_path(tmp_foundry, assertion_id)
    assertion = load_yaml(path)
    assertion.update(overrides)
    dump_yaml(assertion, path)


def _mutate_edition(tmp_foundry, **overrides: object) -> None:
    path = _edition_path(tmp_foundry)
    edition = load_yaml(path)
    edition.update(overrides)
    dump_yaml(edition, path)


def _identity(workspace_id: str = "workspace-a") -> AuthIdentity:
    return AuthIdentity("alice", workspace_id, ("researcher",))


def _question(**overrides: object) -> RetrievalQuestion:
    defaults: dict[str, object] = {"question_id": "q1"}
    defaults.update(overrides)
    return RetrievalQuestion(**defaults)  # type: ignore[arg-type]


def _assert_no_candidate_signal(result) -> None:
    assert result.candidates == ()
    assert result.catalog_generation_id is None
    assert result.pagination_limit_reached is False
    assert result.candidate_limit_reached is False


# ---------------------------------------------------------------------------
# Identity / workspace-scope denials
# ---------------------------------------------------------------------------


def test_missing_identity_denies_with_zero_candidate_signal(tmp_foundry) -> None:
    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(catalog, identity=None, question=_question())
    assert result.denial_reason == "workspace_context_missing"
    _assert_no_candidate_signal(result)


def test_identity_without_workspace_denies(tmp_foundry) -> None:
    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(catalog, identity=AuthIdentity("bob", "", ()), question=_question())
    assert result.denial_reason == "workspace_context_missing"
    _assert_no_candidate_signal(result)


def test_cross_workspace_access_never_returns_other_workspace_candidates(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_carp2_wsa", "workspace-a", "Workspace A owns this fact exclusively.")
    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(
        catalog,
        identity=_identity("workspace-b"),
        question=_question(required_terms=("exclusively",)),
    )
    assert result.denial_reason is None
    assert result.candidates == ()


# ---------------------------------------------------------------------------
# Rights denials (whole-workspace fail-closed per AssertionCatalog.search())
# ---------------------------------------------------------------------------


def test_rights_missing_denies_with_zero_candidate_signal(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_carp2_rights_missing", "workspace-a", "Missing rights must deny discovery.")
    edition_path = _edition_path(tmp_foundry)
    edition = load_yaml(edition_path)
    edition["metadata_extensions"].pop("allowed_use")
    dump_yaml(edition, edition_path)

    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(catalog, identity=_identity(), question=_question(required_terms=("rights",)))
    assert result.denial_reason == "rights_context_missing"
    _assert_no_candidate_signal(result)


def test_rights_denied_denies_with_zero_candidate_signal(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_carp2_rights_denied", "workspace-a", "Denied rights must deny discovery.")
    edition_path = _edition_path(tmp_foundry)
    edition = load_yaml(edition_path)
    edition["metadata_extensions"]["allowed_use"]["allowed_for_work_output"] = False
    dump_yaml(edition, edition_path)

    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(catalog, identity=_identity(), question=_question())
    assert result.denial_reason == "rights_denied"
    _assert_no_candidate_signal(result)


# ---------------------------------------------------------------------------
# Adapter-level limit validation
# ---------------------------------------------------------------------------


def test_invalid_page_size_denies_with_zero_candidate_signal(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_carp2_page_size", "workspace-a", "A page size of zero must deny cleanly.")
    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(
        catalog,
        identity=_identity(),
        question=_question(),
        limits=RetrievalLimits(page_size=0),
    )
    assert result.denial_reason == "invalid_page_size"
    _assert_no_candidate_signal(result)


def test_limits_are_clamped_to_frozen_ceilings(tmp_foundry) -> None:
    limits = RetrievalLimits(max_candidates_per_question=999, max_pages_per_question=999).clamped()
    assert limits.max_candidates_per_question == 50
    assert limits.max_pages_per_question == 5


# ---------------------------------------------------------------------------
# Empty projection
# ---------------------------------------------------------------------------


def test_empty_projection_is_not_a_denial_and_has_no_candidates(tmp_foundry) -> None:
    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(catalog, identity=_identity("workspace-empty"), question=_question())
    assert result.denial_reason is None
    assert result.candidates == ()


# ---------------------------------------------------------------------------
# Exact reuse/version evaluation (CARP-2.2) -- allow / refresh / deny paths
# ---------------------------------------------------------------------------


def test_eligible_candidate_is_allow_and_receipt_is_exact(tmp_foundry) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_carp2_allow", "workspace-a", "The exact reuse fact is forty two."
    )
    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(
        catalog,
        identity=_identity(),
        question=_question(required_terms=("forty", "two")),
        constraints=RetrievalConstraints(sensitivity_threshold="personal"),
    )

    assert result.denial_reason is None
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.assertion_id == assertion_id
    assert candidate.assertion_version == 1
    assert candidate.lifecycle_state == "eligible"
    assert candidate.lexical_match is True
    assert set(candidate.matched_terms) == {"forty", "two"}
    assert candidate.reuse_decision.action == "allow"
    assert candidate.reuse_decision.reason_code == "eligible"
    assert candidate.residual_reason is None
    assert candidate.retrieval_receipt.action == "allow"
    assert candidate.retrieval_receipt.assertion_id == assertion_id
    assert candidate.retrieval_receipt.assertion_version == 1
    assert candidate.retrieval_receipt.source == "catalog"
    assert candidate.retrieval_receipt.catalog_generation_id == result.catalog_generation_id
    assert result.catalog_generation_id is not None


def _patch_packet_lifecycle(monkeypatch, catalog, assertion_id: str, lifecycle_state: str) -> None:
    """Simulate condition 2's staleness scenario deterministically: the ledger
    still says ``eligible`` at search() time (so the candidate is discoverable
    at all -- AssertionCatalog.search() itself never surfaces a non-eligible
    row), but the immediate-before-selection re-read via packet() disagrees.
    This is exactly the race §3.1 condition 2 exists to defend against; a
    directly-authored non-eligible fixture would simply never reach the
    candidate set at all (search()'s own eligible-only filter), which is a
    *different*, equally fail-closed, but untestable-via-retrieve() path.
    """

    original_packet = catalog.packet

    def _patched(candidate_id: str, *, identity):
        result = original_packet(candidate_id, identity=identity)
        if result is not None and candidate_id == assertion_id:
            result = dict(result)
            result["lifecycle_state"] = lifecycle_state
        return result

    monkeypatch.setattr(catalog, "packet", _patched)


def test_stale_assertion_is_residual_reuse_refresh_required(tmp_foundry, monkeypatch) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_carp2_stale", "workspace-a", "The stale reuse fact needs refresh soon."
    )
    catalog = AssertionCatalog(tmp_foundry)
    _patch_packet_lifecycle(monkeypatch, catalog, assertion_id, "stale")

    result = retrieve(catalog, identity=_identity(), question=_question(required_terms=("refresh",)))

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.lifecycle_state == "stale"
    assert candidate.reuse_decision.action == "refresh"
    assert candidate.reuse_decision.reason_code == "freshness_refresh_required"
    assert candidate.residual_reason == "reuse_refresh_required"


def test_invalidated_assertion_is_residual_lifecycle_ineligible(tmp_foundry, monkeypatch) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_carp2_invalidated", "workspace-a", "The invalidated reuse fact must deny."
    )
    catalog = AssertionCatalog(tmp_foundry)
    _patch_packet_lifecycle(monkeypatch, catalog, assertion_id, "invalidated")

    result = retrieve(catalog, identity=_identity(), question=_question(required_terms=("invalidated",)))

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.reuse_decision.action == "deny"
    assert candidate.reuse_decision.reason_code == "lifecycle_unknown"
    assert candidate.residual_reason == "lifecycle_ineligible"


def test_tombstoned_retracted_assertion_is_residual_lifecycle_ineligible(tmp_foundry, monkeypatch) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_carp2_tombstoned", "workspace-a", "The tombstoned reuse fact must deny too."
    )
    catalog = AssertionCatalog(tmp_foundry)
    _patch_packet_lifecycle(monkeypatch, catalog, assertion_id, "tombstoned")

    result = retrieve(catalog, identity=_identity(), question=_question(required_terms=("tombstoned",)))

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.reuse_decision.action == "deny"
    assert candidate.reuse_decision.reason_code == "lifecycle_unknown"
    assert candidate.residual_reason == "lifecycle_ineligible"


def test_wrong_required_edition_is_residual_reuse_refresh_required(tmp_foundry) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_carp2_edition", "workspace-a", "The edition-pinned reuse fact is exact."
    )
    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(
        catalog,
        identity=_identity(),
        question=_question(required_terms=("exact",)),
        constraints=RetrievalConstraints(required_edition_id=f"sed_{'0' * 64}", sensitivity_threshold="personal"),
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.assertion_id == assertion_id
    assert candidate.reuse_decision.action == "refresh"
    assert candidate.reuse_decision.reason_code == "edition_refresh_required"
    assert candidate.residual_reason == "reuse_refresh_required"


def test_wrong_required_extraction_contract_is_residual_reuse_refresh_required(tmp_foundry) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_carp2_contract", "workspace-a", "The contract-pinned reuse fact is exact too."
    )
    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(
        catalog,
        identity=_identity(),
        question=_question(required_terms=("exact",)),
        constraints=RetrievalConstraints(required_extraction_contract="some-other-contract-v9", sensitivity_threshold="personal"),
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.assertion_id == assertion_id
    assert candidate.reuse_decision.action == "refresh"
    assert candidate.reuse_decision.reason_code == "extraction_refresh_required"
    assert candidate.residual_reason == "reuse_refresh_required"


# ---------------------------------------------------------------------------
# CARP-2.G -- sensitivity_allowed is its own axis, never aliased from
# rights_allowed, and never defaulted when the caller omits a threshold.
# ---------------------------------------------------------------------------


def test_client_sensitive_edition_denies_below_a_public_threshold(tmp_foundry) -> None:
    """The exploit case: an edition with access_scope=client_sensitive (and
    rights otherwise granted) must NOT reuse under a public threshold, even
    though rights_allowed is True for this same candidate."""

    assertion_id = _materialize(
        tmp_foundry, "rf_run_carp2g_exploit", "workspace-a", "The client sensitive reuse fact must deny."
    )
    _mutate_edition(tmp_foundry, access_scope="client_sensitive")

    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(
        catalog,
        identity=_identity(),
        question=_question(required_terms=("sensitive",)),
        constraints=RetrievalConstraints(sensitivity_threshold="public"),
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.assertion_id == assertion_id
    assert candidate.reuse_decision.action == "deny"
    assert candidate.reuse_decision.reason_code == "sensitivity_denied"
    assert candidate.residual_reason == "reuse_denied"


def test_public_edition_allows_under_a_public_threshold(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_carp2g_public_ok", "workspace-a", "The public reuse fact is exactly allowed.")
    _mutate_edition(tmp_foundry, access_scope="public")

    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(
        catalog,
        identity=_identity(),
        question=_question(required_terms=("exactly",)),
        constraints=RetrievalConstraints(sensitivity_threshold="public"),
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].reuse_decision.action == "allow"


def test_absent_sensitivity_threshold_omits_the_field_and_denies_fail_closed(tmp_foundry) -> None:
    """No caller ever supplied a threshold -- evaluate_reuse must deny, never
    default one in here (that would resurrect the CARP-2.G inversion one
    layer up)."""

    _materialize(tmp_foundry, "rf_run_carp2g_absent", "workspace-a", "The unthresholded reuse fact must deny.")

    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(
        catalog,
        identity=_identity(),
        question=_question(required_terms=("unthresholded",)),
        # No constraints passed at all -- RetrievalConstraints() default has
        # sensitivity_threshold=None.
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.reuse_decision.action == "deny"
    assert candidate.reuse_decision.reason_code == "sensitivity_denied"
    assert candidate.residual_reason == "reuse_denied"


@pytest.mark.parametrize(
    ("access_scope", "threshold", "expect_allowed"),
    [
        ("public", "public", True),
        ("personal", "public", False),
        ("personal", "personal", True),
        ("work_sensitive", "personal", False),
        ("client_sensitive", "work_sensitive", False),
        ("client_sensitive", "client_sensitive", True),
    ],
)
def test_sensitivity_ordinal_comparison_is_correct_at_each_boundary(
    tmp_foundry, access_scope, threshold, expect_allowed
) -> None:
    _materialize(
        tmp_foundry,
        f"rf_run_carp2g_boundary_{access_scope}_{threshold}",
        "workspace-a",
        "The boundary reuse fact tests the ordinal comparison.",
    )
    _mutate_edition(tmp_foundry, access_scope=access_scope)

    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(
        catalog,
        identity=_identity(),
        question=_question(required_terms=("boundary",)),
        constraints=RetrievalConstraints(sensitivity_threshold=threshold),
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    if expect_allowed:
        assert candidate.reuse_decision.action == "allow"
    else:
        assert candidate.reuse_decision.action == "deny"
        assert candidate.reuse_decision.reason_code == "sensitivity_denied"


@pytest.mark.parametrize("malformed_threshold", ["banana", ""])
def test_malformed_threshold_denies_fail_closed_never_a_ceiling(tmp_foundry, malformed_threshold) -> None:
    """CARP-2.G follow-up: a threshold that isn't a recognized rank must deny
    outright, not fall through to '.get(x, len(RANK))' and grant a ceiling of
    the most sensitive tier -- that would let even a client_sensitive edition
    reuse under a garbage/empty caller threshold."""

    _materialize(
        tmp_foundry,
        f"rf_run_carp2g_malformed_{malformed_threshold or 'empty'}",
        "workspace-a",
        "The malformed-threshold reuse fact must deny.",
    )
    _mutate_edition(tmp_foundry, access_scope="client_sensitive")

    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(
        catalog,
        identity=_identity(),
        question=_question(required_terms=("malformed",)),
        constraints=RetrievalConstraints(sensitivity_threshold=malformed_threshold),
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.reuse_decision.action == "deny"
    assert candidate.reuse_decision.reason_code == "sensitivity_denied"
    assert candidate.residual_reason == "reuse_denied"


def test_private_access_scope_is_rankable_and_allows_under_a_private_threshold(tmp_foundry) -> None:
    """access_scope='private' is the real most-sensitive member of the
    access_scope vocabulary (assertion_catalog.py's known-set, distinct from
    the run-sensitivity 'top_secret' vocabulary) -- it must be rankable, not
    silently absent from SENSITIVITY_RANK."""

    _materialize(
        tmp_foundry, "rf_run_carp2g_private_ok", "workspace-a", "The private reuse fact is exactly allowed."
    )
    _mutate_edition(tmp_foundry, access_scope="private")

    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(
        catalog,
        identity=_identity(),
        question=_question(required_terms=("exactly",)),
        constraints=RetrievalConstraints(sensitivity_threshold="private"),
    )

    assert len(result.candidates) == 1
    assert result.candidates[0].reuse_decision.action == "allow"


def test_private_access_scope_denies_under_a_client_sensitive_threshold(tmp_foundry) -> None:
    """private ranks above client_sensitive -- a client_sensitive threshold
    must not admit a private-scope edition."""

    _materialize(
        tmp_foundry, "rf_run_carp2g_private_denies", "workspace-a", "The private reuse fact must deny here."
    )
    _mutate_edition(tmp_foundry, access_scope="private")

    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(
        catalog,
        identity=_identity(),
        question=_question(required_terms=("here",)),
        constraints=RetrievalConstraints(sensitivity_threshold="client_sensitive"),
    )

    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.reuse_decision.action == "deny"
    assert candidate.reuse_decision.reason_code == "sensitivity_denied"


# ---------------------------------------------------------------------------
# Stale-projection cannot select a stale packet (immediate re-read wins)
# ---------------------------------------------------------------------------


def test_stale_snapshot_cannot_select_a_now_ineligible_packet(tmp_foundry) -> None:
    """An earlier "allow" decision must never leak into a later call after the
    ledger changes -- every candidate is re-evaluated fresh (via packet()),
    never from a retained/cached snapshot (CARP-2.2 condition 2)."""

    assertion_id = _materialize(
        tmp_foundry, "rf_run_carp2_projection_drift", "workspace-a", "The drifted reuse fact must fail closed."
    )
    catalog = AssertionCatalog(tmp_foundry)
    question = _question(required_terms=("drifted",))
    constraints = RetrievalConstraints(sensitivity_threshold="personal")

    before = retrieve(catalog, identity=_identity(), question=question, constraints=constraints)
    assert len(before.candidates) == 1
    assert before.candidates[0].reuse_decision.action == "allow"

    _mutate_assertion(tmp_foundry, assertion_id, lifecycle_state="blocked")

    after = retrieve(catalog, identity=_identity(), question=question, constraints=constraints)
    assert after.candidates == ()


# ---------------------------------------------------------------------------
# Packet disappearing between search and packet fetch (TOCTOU)
# ---------------------------------------------------------------------------


def test_packet_disappearing_between_search_and_fetch_is_skipped_silently(tmp_foundry, monkeypatch) -> None:
    """Simulates a genuine TOCTOU race: search() already returned this
    candidate id, but by the time the adapter calls packet() for it, the
    record is gone. AssertionCatalog itself keeps search()/packet() reading
    the same rebuilt snapshot within one call, so the race is injected
    directly at the packet() seam rather than via ledger mutation (which
    search() and packet() would observe identically here)."""

    assertion_id = _materialize(
        tmp_foundry, "rf_run_carp2_toctou", "workspace-a", "The vanishing reuse fact must not crash retrieval."
    )
    catalog = AssertionCatalog(tmp_foundry)
    original_packet = catalog.packet

    def _vanished(candidate_id: str, *, identity):
        if candidate_id == assertion_id:
            return None
        return original_packet(candidate_id, identity=identity)

    monkeypatch.setattr(catalog, "packet", _vanished)
    result = retrieve(catalog, identity=_identity(), question=_question(required_terms=("vanishing",)))
    assert result.denial_reason is None
    assert result.candidates == ()


def test_packet_denied_between_search_and_fetch_is_skipped_silently(tmp_foundry, monkeypatch) -> None:
    """Same TOCTOU race as above, but packet() raises AssertionCatalogDenied
    (rights flipped) instead of returning None -- the adapter must catch it
    per-candidate and skip, not let it propagate or deny the whole result."""

    assertion_id = _materialize(
        tmp_foundry, "rf_run_carp2_toctou_denied", "workspace-a", "The soon-denied reuse fact must not leak."
    )
    catalog = AssertionCatalog(tmp_foundry)
    original_packet = catalog.packet

    def _denies_mid_flight(candidate_id: str, *, identity):
        if candidate_id == assertion_id:
            raise AssertionCatalogDenied("rights_denied")
        return original_packet(candidate_id, identity=identity)

    monkeypatch.setattr(catalog, "packet", _denies_mid_flight)
    result = retrieve(catalog, identity=_identity(), question=_question(required_terms=("denied",)))
    assert result.denial_reason is None
    assert result.candidates == ()


# ---------------------------------------------------------------------------
# OQ-3: a denied/cross-workspace caller's evaluated_candidates is always empty
# ---------------------------------------------------------------------------


def test_oq3_denied_caller_never_receives_a_refresh_state_candidate(tmp_foundry, monkeypatch) -> None:
    assertion_id = _materialize(
        tmp_foundry, "rf_run_carp2_oq3", "workspace-a", "The refresh-eligible fact must stay hidden from denial."
    )
    catalog = AssertionCatalog(tmp_foundry)
    _patch_packet_lifecycle(monkeypatch, catalog, assertion_id, "stale")

    denied = retrieve(catalog, identity=None, question=_question(required_terms=("refresh-eligible",)))
    assert denied.candidates == ()

    cross_workspace = retrieve(
        catalog, identity=_identity("workspace-b"), question=_question(required_terms=("refresh-eligible",))
    )
    assert cross_workspace.candidates == ()

    # Sanity: the SAME candidate is genuinely refresh-eligible for the owning,
    # authorized workspace -- proving the denial above is policy-driven, not
    # an accidental "nothing exists" empty result.
    authorized = retrieve(catalog, identity=_identity("workspace-a"), question=_question(required_terms=("refresh-eligible",)))
    assert len(authorized.candidates) == 1
    assert authorized.candidates[0].reuse_decision.action == "refresh"


# ---------------------------------------------------------------------------
# Seam 1 -- catalog_generation_id
# ---------------------------------------------------------------------------


def test_catalog_generation_id_is_stable_digest_not_a_counter(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_carp2_gen_stable", "workspace-a", "The generation digest must be stable.")
    catalog = AssertionCatalog(tmp_foundry)

    first = catalog_receipt(catalog, _identity())
    second = catalog_receipt(catalog, _identity())
    assert first.catalog_generation_id is not None
    assert first.catalog_generation_id == second.catalog_generation_id

    # Never a filesystem path or something resembling a plain incrementing counter.
    assert "/" not in first.catalog_generation_id
    assert not first.catalog_generation_id.isdigit()


def test_catalog_generation_id_changes_only_when_the_corpus_changes(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_carp2_gen_a", "workspace-a", "First generation fact.")
    catalog = AssertionCatalog(tmp_foundry)
    before = catalog_receipt(catalog, _identity())

    # A no-op rebuild (unchanged corpus) must not perturb the generation id --
    # this is exactly the property a monotonic counter would violate.
    catalog.rebuild("workspace-a")
    same = catalog_receipt(catalog, _identity())
    assert same.catalog_generation_id == before.catalog_generation_id

    _materialize(tmp_foundry, "rf_run_carp2_gen_b", "workspace-a", "Second generation fact changes the corpus.")
    after = catalog_receipt(catalog, _identity())
    assert after.catalog_generation_id != before.catalog_generation_id


def test_denied_catalog_receipt_exposes_zero_candidate_signal(tmp_foundry) -> None:
    catalog = AssertionCatalog(tmp_foundry)
    receipt = catalog_receipt(catalog, None)
    assert receipt.denial_reason == "workspace_context_missing"
    assert receipt.record_count == 0
    assert receipt.catalog_generation_id is None


def test_peek_generation_id_does_not_trigger_a_rebuild(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_carp2_peek", "workspace-a", "Peeking must never rebuild the projection.")
    catalog = AssertionCatalog(tmp_foundry)
    receipt = catalog.rebuild("workspace-a")
    projection_path = catalog.projection_path("workspace-a")
    mtime_before = projection_path.stat().st_mtime_ns

    peeked = peek_catalog_generation_id(catalog, "workspace-a")
    assert peeked == receipt.catalog_generation_id
    assert projection_path.stat().st_mtime_ns == mtime_before


def test_peek_generation_id_is_none_when_no_projection_exists_yet(tmp_foundry) -> None:
    catalog = AssertionCatalog(tmp_foundry)
    assert peek_catalog_generation_id(catalog, "workspace-never-built") is None


# ---------------------------------------------------------------------------
# Seam 2 -- lexical-match evidence never exposes search_text itself
# ---------------------------------------------------------------------------


def test_lexical_miss_yields_no_candidates_for_an_absent_term(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_carp2_lexmiss", "workspace-a", "This passage never mentions the target word.")
    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(catalog, identity=_identity(), question=_question(required_terms=("absolutely-nonexistent-term",)))
    assert result.candidates == ()


def test_partial_term_match_is_not_lexical_match(tmp_foundry) -> None:
    """A candidate matching SOME but not all required terms is still surfaced
    (with matched-term evidence, for a future evidence-plan builder to
    distinguish `lexical_miss` from `no_candidate`), but is never treated as
    a full lexical match by this adapter."""

    _materialize(tmp_foundry, "rf_run_carp2_partial", "workspace-a", "The partial term match fact mentions alpha only.")
    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(
        catalog, identity=_identity(), question=_question(required_terms=("alpha", "beta-not-present"))
    )
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.lexical_match is False
    assert candidate.matched_terms == ("alpha",)


def test_matched_terms_never_carries_corpus_text_only_the_required_terms(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_carp2_evidence", "workspace-a", "The matched evidence fact is quite unique.")
    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(catalog, identity=_identity(), question=_question(required_terms=("unique",)))
    assert len(result.candidates) == 1
    candidate = result.candidates[0]
    assert candidate.matched_terms == ("unique",)
    # The candidate DTO never carries a raw search_text/corpus-text field at all.
    assert not hasattr(candidate, "search_text")


def test_shared_page_budget_is_per_question_not_per_term(tmp_foundry) -> None:
    """max_pages_per_question is a budget SHARED across every required-term
    sub-query, never multiplied by the number of terms (carp-contract-freeze.md
    §3.6 pagination-arithmetic ruling)."""

    for index in range(3):
        _materialize(
            tmp_foundry,
            f"rf_run_carp2_budget_{index}",
            "workspace-a",
            f"Shared budget fact number {index} about apples and oranges.",
        )
    catalog = AssertionCatalog(tmp_foundry)

    # 3 required terms, page_size=1, and only 2 pages of shared budget: if the
    # budget were (incorrectly) applied per-term, each of the 3 terms could
    # walk its own 2 pages (6 total) and every candidate would resolve
    # cleanly. With a correctly-shared budget of 2 pages total, at least one
    # term-sweep is truncated and the adapter must report pagination_limit_reached.
    result = retrieve(
        catalog,
        identity=_identity(),
        question=_question(required_terms=("apples", "oranges", "budget")),
        limits=RetrievalLimits(page_size=1, max_pages_per_question=2),
    )
    assert result.pagination_limit_reached is True


def test_candidate_limit_reached_is_reported_when_matches_exceed_the_cap(tmp_foundry) -> None:
    for index in range(3):
        _materialize(
            tmp_foundry,
            f"rf_run_carp2_climit_{index}",
            "workspace-a",
            f"Candidate limit fact number {index} shares the ceiling term.",
        )
    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(
        catalog,
        identity=_identity(),
        question=_question(required_terms=("ceiling",)),
        limits=RetrievalLimits(max_candidates_per_question=2),
    )
    assert len(result.candidates) == 2
    assert result.candidate_limit_reached is True


# ---------------------------------------------------------------------------
# Additive-seam regression: existing AssertionCatalog callers are unaffected
# ---------------------------------------------------------------------------


def test_seam_1_is_additive_existing_rebuild_and_search_callers_unaffected(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_carp2_additive", "workspace-a", "Additive seam regression fact for parity.")
    catalog = AssertionCatalog(tmp_foundry)
    identity = _identity()

    receipt = catalog.rebuild("workspace-a")
    assert receipt.workspace_id == "workspace-a"
    assert receipt.record_count == 1
    assert receipt.projection_path.exists()

    search_result = catalog.search(identity=identity, query="additive")
    assert search_result["denial_reason"] is None
    assert len(search_result["items"]) == 1

    packet = catalog.packet(search_result["items"][0]["assertion_id"], identity=identity)
    assert packet is not None
    assert "search_text" not in packet
    assert set(catalog.denied_payload("x")) == {"items", "next_cursor", "facets", "denial_reason"}


@pytest.mark.parametrize("required_terms", [(), ("no-projection-yet",)])
def test_retrieve_never_globs_assertion_ledger_paths(tmp_foundry, required_terms) -> None:
    """This test's own assertion is structural, not behavioral: catalog_retrieval.py
    must never itself glob a filesystem path -- every read goes through
    AssertionCatalog's public methods (search/packet/rebuild/projection_path)."""

    import inspect

    import research_foundry.services.catalog_retrieval as module

    source = inspect.getsource(module)
    assert "glob(" not in source
    assert ".rglob(" not in source

    catalog = AssertionCatalog(tmp_foundry)
    result = retrieve(catalog, identity=_identity(), question=_question(required_terms=required_terms))
    assert result.denial_reason is None
    assert result.candidates == ()
