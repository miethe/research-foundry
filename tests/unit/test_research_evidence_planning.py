"""CARP-3 H3 fixture matrix for the evidence-plan builder (research_evidence_planning.py).

Two layers, matching the module's own split:

* Pure ``evaluate_question_coverage`` (CARP-3.1) scenarios are built directly
  from hand-constructed ``RetrievalResult``/``EvaluatedCandidate`` fixtures --
  no filesystem, no catalog, no identity. These exercise the coverage rule in
  isolation, exactly as the module's own docstring promises ("pure and
  total").
* Orchestrator ``build_evidence_plan`` (CARP-3.2) scenarios that genuinely
  need a real ledger/catalog (whole-plan denial/empty, mid-plan generation
  drift, the version-pin re-check, replay byte-equivalence, schema validity)
  use the same ``tmp_foundry`` + ``AssertionCatalog`` machinery as
  ``tests/unit/test_catalog_retrieval.py``.
"""

from __future__ import annotations

from typing import Any

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.schemas import validate
from research_foundry.services import claim_mapping, extraction
from research_foundry.services.assertion_catalog import AssertionCatalog
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.assertion_reuse import ReuseDecision
from research_foundry.services.catalog_retrieval import (
    EvaluatedCandidate,
    RetrievalConstraints,
    RetrievalReceipt,
    RetrievalResult,
    catalog_receipt,
)
from research_foundry.services.research_evidence_planning import (
    EvidencePlanLimits,
    EvidencePlanQuestion,
    EvidencePlanRequest,
    build_evidence_plan,
    evaluate_question_coverage,
    write_evidence_plan,
)
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, dumps_yaml, load_yaml

# ---------------------------------------------------------------------------
# Shared fixtures/helpers
# ---------------------------------------------------------------------------


def _materialize(tmp_foundry, run_id: str, workspace_id: str, content: str) -> str:
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    # Explicitly enable both controls ``automated_reuse_allowed`` depends on
    # (config.py: ``ledger_write_enabled AND automated_reuse_enabled``) --
    # a test asserting "covered" must describe a world where automated
    # reuse is permitted. See P6 CARP-6.2 capability-gate fix.
    foundry["foundry"]["assertion_ledger"] = {
        "ledger_write_enabled": True,
        "automated_reuse_enabled": True,
    }
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


def _identity(workspace_id: str = "workspace-a") -> AuthIdentity:
    return AuthIdentity("alice", workspace_id, ("researcher",))


def _plan_question(
    question_id: str = "q1",
    *,
    required_terms: tuple[str, ...] = (),
    required_source_types: tuple[str, ...] = (),
    required_qualifiers: dict[str, str] | None = None,
) -> EvidencePlanQuestion:
    return EvidencePlanQuestion(
        question_id=question_id,
        required_terms=required_terms,
        required_source_types=required_source_types,
        required_qualifiers=required_qualifiers or {},
    )


def _request(
    *,
    workspace_id: str = "workspace-a",
    questions: tuple[EvidencePlanQuestion, ...] = (),
    limits: EvidencePlanLimits | None = None,
) -> EvidencePlanRequest:
    return EvidencePlanRequest(
        evidence_plan_id=f"evp_{workspace_id}",
        workspace_id=workspace_id,
        retrieval_policy="catalog_only",
        questions=questions,
        generated_at="2026-07-23T00:00:00Z",
        decided_at="2026-07-23T00:00:00Z",
        # Fixture correction (P6 CARP-6.2): the ``_materialize`` helper
        # explicitly enables ``automated_reuse_enabled``, so every request
        # built through this factory describes a world where automated
        # reuse is permitted -- the capability must be passed through the
        # same way the real production call site (planning.py) does, or
        # the P6 fail-closed gate collapses every otherwise-eligible
        # candidate to residual/reuse_denied.
        constraints=RetrievalConstraints(sensitivity_threshold="personal", automated_reuse_allowed=True),
        limits=limits or EvidencePlanLimits(),
    )


def _candidate(
    assertion_id: str,
    *,
    assertion_version: int = 1,
    lifecycle_state: str = "eligible",
    lexical_match: bool = True,
    qualifiers: dict[str, Any] | None = None,
    action: str = "allow",
    reason_code: str = "eligible",
) -> EvaluatedCandidate:
    residual_reason: str | None = None
    if action == "refresh":
        residual_reason = "reuse_refresh_required"
    elif action == "deny":
        residual_reason = "lifecycle_ineligible" if reason_code in {"lifecycle_blocked", "lifecycle_unknown"} else "reuse_denied"
    return EvaluatedCandidate(
        assertion_id=assertion_id,
        assertion_version=assertion_version,
        lifecycle_state=lifecycle_state,
        lexical_match=lexical_match,
        matched_terms=(),
        qualifiers=qualifiers or {},
        reuse_decision=ReuseDecision(action=action, reason_code=reason_code, assertion_id=assertion_id),
        residual_reason=residual_reason,
        retrieval_receipt=RetrievalReceipt(
            action=action, reason_code=reason_code, assertion_id=assertion_id, assertion_version=assertion_version
        ),
    )


def _result(
    *,
    question_id: str = "q1",
    denial_reason: str | None = None,
    candidates: tuple[EvaluatedCandidate, ...] = (),
    pagination_limit_reached: bool = False,
    candidate_limit_reached: bool = False,
) -> RetrievalResult:
    return RetrievalResult(
        question_id=question_id,
        denial_reason=denial_reason,
        catalog_generation_id="gen_demo",
        candidates=candidates,
        pagination_limit_reached=pagination_limit_reached,
        candidate_limit_reached=candidate_limit_reached,
    )


# ---------------------------------------------------------------------------
# Pure CARP-3.1 scenarios -- H3 #1-#5, #7, #10-#13, #15, plus a denial/error case.
# ---------------------------------------------------------------------------


def test_h3_1_exact_match_is_covered() -> None:
    result = _result(candidates=(_candidate("ast_" + "a" * 64),))
    decision = evaluate_question_coverage(result, _plan_question())
    assert decision.coverage_state == "covered"
    assert decision.residual_reason is None
    assert decision.selected is not None
    assert decision.selected.assertion_id == "ast_" + "a" * 64


def test_h3_2_no_candidates_is_residual_no_candidate() -> None:
    result = _result(candidates=())
    decision = evaluate_question_coverage(result, _plan_question())
    assert decision.coverage_state == "residual"
    assert decision.residual_reason == "no_candidate"
    assert decision.selected is None


def test_h3_3_lexical_miss_is_residual_lexical_miss() -> None:
    result = _result(candidates=(_candidate("ast_" + "a" * 64, lexical_match=False),))
    decision = evaluate_question_coverage(result, _plan_question(required_terms=("absent",)))
    assert decision.coverage_state == "residual"
    assert decision.residual_reason == "lexical_miss"


def test_h3_4_source_type_mismatch_is_residual() -> None:
    """Documented v1 limitation (module docstring): no source_type signal is
    reachable through the adapter's packet -- a non-empty required_source_types
    is unconditionally unsatisfiable, never covered."""

    result = _result(candidates=(_candidate("ast_" + "a" * 64),))
    question = _plan_question(required_source_types=("clinical_guideline",))
    decision = evaluate_question_coverage(result, question)
    assert decision.coverage_state == "residual"
    assert decision.residual_reason == "source_type_mismatch"


def test_h3_4b_empty_required_source_types_is_vacuous_and_covers() -> None:
    result = _result(candidates=(_candidate("ast_" + "a" * 64),))
    decision = evaluate_question_coverage(result, _plan_question(required_source_types=()))
    assert decision.coverage_state == "covered"


def test_h3_5_missing_qualifier_is_residual_qualifier_missing() -> None:
    result = _result(candidates=(_candidate("ast_" + "a" * 64, qualifiers={"population": "adult"}),))
    question = _plan_question(required_qualifiers={"population": "pediatric"})
    decision = evaluate_question_coverage(result, question)
    assert decision.coverage_state == "residual"
    assert decision.residual_reason == "qualifier_missing"


def test_h3_5b_absent_qualifier_key_is_residual_qualifier_missing() -> None:
    result = _result(candidates=(_candidate("ast_" + "a" * 64, qualifiers={}),))
    question = _plan_question(required_qualifiers={"population": "pediatric"})
    decision = evaluate_question_coverage(result, question)
    assert decision.coverage_state == "residual"
    assert decision.residual_reason == "qualifier_missing"


def test_h3_5c_matching_qualifier_covers() -> None:
    result = _result(candidates=(_candidate("ast_" + "a" * 64, qualifiers={"population": "pediatric"}),))
    question = _plan_question(required_qualifiers={"population": "pediatric"})
    decision = evaluate_question_coverage(result, question)
    assert decision.coverage_state == "covered"


def test_h3_6_refresh_required_is_residual_reuse_refresh_required() -> None:
    result = _result(candidates=(_candidate("ast_" + "a" * 64, action="refresh", reason_code="freshness_refresh_required"),))
    decision = evaluate_question_coverage(result, _plan_question())
    assert decision.coverage_state == "residual"
    assert decision.residual_reason == "reuse_refresh_required"


def test_h3_7_reuse_denied_is_residual_reuse_denied() -> None:
    result = _result(candidates=(_candidate("ast_" + "a" * 64, action="deny", reason_code="sensitivity_denied"),))
    decision = evaluate_question_coverage(result, _plan_question())
    assert decision.coverage_state == "residual"
    assert decision.residual_reason == "reuse_denied"


def test_h3_8_lifecycle_ineligible_via_adapter_residual_reason() -> None:
    result = _result(candidates=(_candidate("ast_" + "a" * 64, action="deny", reason_code="lifecycle_unknown"),))
    decision = evaluate_question_coverage(result, _plan_question())
    assert decision.coverage_state == "residual"
    assert decision.residual_reason == "lifecycle_ineligible"


def test_h3_10_conflicting_packet_is_residual_contradiction_for_both() -> None:
    a = _candidate("ast_" + "a" * 64, qualifiers={"population": "pediatric"})
    b = _candidate("ast_" + "b" * 64, qualifiers={"population": "adult"})
    result = _result(candidates=(a, b))
    decision = evaluate_question_coverage(result, _plan_question())
    assert decision.coverage_state == "residual"
    assert decision.residual_reason == "contradiction"


def test_h3_11_multiple_equivalent_hits_selects_lowest_assertion_id() -> None:
    a = _candidate("ast_" + "a" * 64)
    b = _candidate("ast_" + "b" * 64)
    result = _result(candidates=(b, a))  # deliberately out of order on input
    decision = evaluate_question_coverage(result, _plan_question())
    assert decision.coverage_state == "covered"
    assert decision.residual_reason is None
    assert decision.selected is not None
    assert decision.selected.assertion_id == "ast_" + "a" * 64
    assert decision.selection_note is not None
    assert "2 equivalent" in decision.selection_note


def test_h3_12_pagination_boundary_is_residual_pagination_limit() -> None:
    result = _result(candidates=(), pagination_limit_reached=True)
    decision = evaluate_question_coverage(result, _plan_question())
    assert decision.coverage_state == "residual"
    assert decision.residual_reason == "pagination_limit"


def test_h3_12b_pagination_limit_preempts_a_per_candidate_reason() -> None:
    """An incomplete sweep means a per-candidate reason cannot be trusted --
    pagination_limit wins even when a (possibly-wrong) candidate reason exists."""

    result = _result(candidates=(_candidate("ast_" + "a" * 64, lexical_match=False),), pagination_limit_reached=True)
    decision = evaluate_question_coverage(result, _plan_question(required_terms=("absent",)))
    assert decision.residual_reason == "pagination_limit"


def test_h3_13_duplicate_candidate_is_deduped_and_covers_once() -> None:
    duplicate_a = _candidate("ast_" + "a" * 64)
    duplicate_a_again = _candidate("ast_" + "a" * 64)
    result = _result(candidates=(duplicate_a, duplicate_a_again))
    decision = evaluate_question_coverage(result, _plan_question())
    assert decision.coverage_state == "covered"
    assert decision.residual_reason is None
    assert len(decision.evaluated_candidates) == 1


def test_h3_15_candidate_limit_exceeded_is_residual_candidate_limit() -> None:
    result = _result(candidates=(_candidate("ast_" + "a" * 64, lexical_match=False),), candidate_limit_reached=True)
    decision = evaluate_question_coverage(result, _plan_question(required_terms=("absent",)))
    assert decision.coverage_state == "residual"
    assert decision.residual_reason == "candidate_limit"


def test_retrieval_denial_is_residual_evaluation_error() -> None:
    result = _result(denial_reason="invalid_page_size")
    decision = evaluate_question_coverage(result, _plan_question())
    assert decision.coverage_state == "residual"
    assert decision.residual_reason == "evaluation_error"


def test_evaluate_question_coverage_never_raises_on_a_malformed_result() -> None:
    class _Broken:
        denial_reason = None
        candidates = None  # deliberately not a sequence -- triggers an internal exception

    decision = evaluate_question_coverage(_Broken(), _plan_question())  # type: ignore[arg-type]
    assert decision.coverage_state == "residual"
    assert decision.residual_reason == "evaluation_error"


# ---------------------------------------------------------------------------
# Orchestrator CARP-3.2 scenarios that need a real catalog -- H3 #9, #14, #16, #17.
# ---------------------------------------------------------------------------


def test_h3_16_catalog_denied_marks_every_question_residual_catalog_denied(tmp_foundry) -> None:
    catalog = AssertionCatalog(tmp_foundry)  # identity=None denies before any catalog read
    request = _request(questions=(_plan_question("q1"), _plan_question("q2")))
    plan = build_evidence_plan(catalog, identity=None, request=request)

    assert plan["catalog_receipt"]["record_count"] == 0
    assert plan["catalog_receipt"]["denial_reason"] == "workspace_context_missing"
    for question in plan["questions"]:
        assert question["coverage_state"] == "residual"
        assert question["residual_reason"] == "catalog_denied"
        assert question["evaluated_candidates"] == []
    assert plan["summary"] == {"questions_total": 2}


def test_h3_17_catalog_empty_marks_every_question_residual_catalog_empty(tmp_foundry) -> None:
    catalog = AssertionCatalog(tmp_foundry)
    request = _request(workspace_id="workspace-empty", questions=(_plan_question("q1"),))
    plan = build_evidence_plan(catalog, identity=_identity("workspace-empty"), request=request)

    assert plan["catalog_receipt"]["record_count"] == 0
    assert plan["catalog_receipt"]["denial_reason"] is None
    assert plan["questions"][0]["coverage_state"] == "residual"
    assert plan["questions"][0]["residual_reason"] == "catalog_empty"
    assert plan["summary"] == {"questions_total": 1}


def test_counter_trap_catalog_empty_with_multiple_residual_questions_omits_all_six_counters_and_validates(
    tmp_foundry,
) -> None:
    """The exact trap named in the P3 brief: a catalog-empty plan carrying N
    residual questions must OMIT summary.questions_residual (and all five
    other candidate-derived counters), not report N -- verified against the
    live schema, not merely asserted against a hand-built fixture."""

    catalog = AssertionCatalog(tmp_foundry)
    request = _request(
        workspace_id="workspace-empty",
        questions=(_plan_question("q1"), _plan_question("q2"), _plan_question("q3")),
    )
    plan = build_evidence_plan(catalog, identity=_identity("workspace-empty"), request=request)

    assert plan["catalog_receipt"]["record_count"] == 0
    assert len(plan["questions"]) == 3
    for question in plan["questions"]:
        assert question["coverage_state"] == "residual"
        assert question["residual_reason"] == "catalog_empty"

    summary = plan["summary"]
    assert summary == {"questions_total": 3}
    assert "questions_residual" not in summary
    assert "questions_covered" not in summary
    assert "candidates_evaluated" not in summary
    assert "candidates_selected" not in summary
    assert "avoided_provider_calls" not in summary
    assert "residual_reason_counts" not in summary

    result = validate(plan, "research_evidence_plan")
    assert result.ok, f"expected the counter-trap catalog-empty plan to validate, got: {result.errors}"


def test_h3_8b_stale_projection_via_real_ledger_is_residual_lifecycle_ineligible(tmp_foundry, monkeypatch) -> None:
    assertion_id = _materialize(tmp_foundry, "rf_run_carp3_stale", "workspace-a", "The invalidated planning fact must deny cleanly.")
    catalog = AssertionCatalog(tmp_foundry)
    original_packet = catalog.packet

    def _patched(candidate_id: str, *, identity):
        packet = original_packet(candidate_id, identity=identity)
        if packet is not None and candidate_id == assertion_id:
            packet = dict(packet)
            packet["lifecycle_state"] = "invalidated"
        return packet

    monkeypatch.setattr(catalog, "packet", _patched)

    request = _request(questions=(_plan_question(required_terms=("invalidated",)),))
    plan = build_evidence_plan(catalog, identity=_identity(), request=request)
    question = plan["questions"][0]
    assert question["coverage_state"] == "residual"
    assert question["residual_reason"] == "lifecycle_ineligible"
    assert question["selected_assertion_ref"] is None
    assert question["retrieval_receipt"] is None


def test_h3_9_version_mismatch_between_evaluation_and_pin_recheck(tmp_foundry, monkeypatch) -> None:
    assertion_id = _materialize(tmp_foundry, "rf_run_carp3_version", "workspace-a", "The pin recheck fact drifts version soon.")
    catalog = AssertionCatalog(tmp_foundry)
    original_packet = catalog.packet
    calls = {"count": 0}

    def _patched(candidate_id: str, *, identity):
        packet = original_packet(candidate_id, identity=identity)
        if packet is not None and candidate_id == assertion_id:
            calls["count"] += 1
            if calls["count"] > 1:
                packet = dict(packet)
                packet["assertion_version"] = 999
        return packet

    monkeypatch.setattr(catalog, "packet", _patched)

    request = _request(questions=(_plan_question(required_terms=("drifts",)),))
    plan = build_evidence_plan(catalog, identity=_identity(), request=request)
    question = plan["questions"][0]
    assert question["coverage_state"] == "residual"
    assert question["residual_reason"] == "version_mismatch"
    assert question["selected_assertion_ref"] is None
    assert calls["count"] >= 2


def test_h3_1b_exact_match_against_a_real_catalog_covers_with_a_pinned_ref(tmp_foundry) -> None:
    assertion_id = _materialize(tmp_foundry, "rf_run_carp3_exact", "workspace-a", "The exact planning fact is forty two.")
    catalog = AssertionCatalog(tmp_foundry)
    request = _request(questions=(_plan_question(required_terms=("forty", "two")),))
    plan = build_evidence_plan(catalog, identity=_identity(), request=request)
    question = plan["questions"][0]
    assert question["coverage_state"] == "covered"
    assert question["residual_reason"] is None
    assert question["selected_assertion_ref"] == {"assertion_id": assertion_id, "assertion_version": 1}
    assert question["retrieval_receipt"]["source"] == "catalog"
    assert question["retrieval_receipt"]["catalog_generation_id"] == plan["catalog_receipt"]["catalog_generation_id"]
    assert plan["summary"]["questions_covered"] == 1
    assert plan["summary"]["avoided_provider_calls"] == 1


def test_summary_counters_are_derived_from_real_executed_candidate_evaluation(tmp_foundry) -> None:
    """P6 CARP-6.7 gap fill (AC CARP-6: 'authorized observed counts are real
    -- derived from executed control flow'). The existing byte-equivalence
    and schema-validity tests never check the *numeric* summary values
    against a plan with more than one real candidate for a single question
    -- this proves ``candidates_evaluated``/``candidates_selected``/
    ``avoided_provider_calls`` are counted from what the adapter actually
    found (two genuinely materialized, non-conflicting assertions -- H3 #11
    "multiple equivalent hits"), not a fixed/fabricated number that would
    happen to match a trivial single-candidate case."""

    first_id = _materialize(
        tmp_foundry, "rf_run_carp67_multi_a", "workspace-a", "The gamma finding appears in this first source."
    )
    second_id = _materialize(
        tmp_foundry, "rf_run_carp67_multi_b", "workspace-a", "The gamma finding also appears in this second source."
    )
    catalog = AssertionCatalog(tmp_foundry)
    request = _request(questions=(_plan_question("q1", required_terms=("gamma",)),))
    plan = build_evidence_plan(catalog, identity=_identity(), request=request)

    question = plan["questions"][0]
    assert question["coverage_state"] == "covered"
    # Both real candidates were evaluated -- not deduped away, not undercounted.
    assert len(question["evaluated_candidates"]) == 2
    evaluated_ids = {c["assertion_id"] for c in question["evaluated_candidates"]}
    assert evaluated_ids == {first_id, second_id}
    # Deterministic tie-break: the lower assertion_id wins selection.
    assert question["selected_assertion_ref"]["assertion_id"] == min(first_id, second_id)

    summary = plan["summary"]
    assert summary["questions_total"] == 1
    assert summary["questions_covered"] == 1
    assert summary["questions_residual"] == 0
    # candidates_evaluated counts BOTH real candidates the adapter found for
    # this one question -- not "1 per covered question", proving it is a
    # real derived count rather than a value that only happens to look
    # right in the single-candidate case every other test uses.
    assert summary["candidates_evaluated"] == 2
    assert summary["candidates_selected"] == 1
    assert summary["avoided_provider_calls"] == 1
    assert summary["residual_reason_counts"] == {}


def test_h3_14_catalog_generation_changed_mid_plan_resolves_remaining_to_evaluation_error(tmp_foundry, monkeypatch) -> None:
    _materialize(tmp_foundry, "rf_run_carp3_gen_q1", "workspace-a", "The first generation planning fact about alpha.")
    _materialize(tmp_foundry, "rf_run_carp3_gen_q2", "workspace-a", "The second generation planning fact about bravo.")
    catalog = AssertionCatalog(tmp_foundry)
    real_receipt = catalog_receipt(catalog, _identity())
    assert real_receipt.catalog_generation_id is not None

    import research_foundry.services.research_evidence_planning as planning_module

    original_peek = planning_module.peek_catalog_generation_id
    calls = {"count": 0}

    def _patched_peek(catalog_arg, workspace_id):
        calls["count"] += 1
        if calls["count"] == 1:
            return original_peek(catalog_arg, workspace_id)
        return "gen_drifted_mid_plan_sentinel"

    monkeypatch.setattr(planning_module, "peek_catalog_generation_id", _patched_peek)

    request = _request(
        questions=(
            _plan_question("q1", required_terms=("alpha",)),
            _plan_question("q2", required_terms=("bravo",)),
        )
    )
    plan = build_evidence_plan(catalog, identity=_identity(), request=request)
    q1, q2 = plan["questions"]
    assert q1["question_id"] == "q1"
    assert q1["coverage_state"] == "covered"
    assert q2["question_id"] == "q2"
    assert q2["coverage_state"] == "residual"
    assert q2["residual_reason"] == "evaluation_error"


def test_max_questions_bounds_the_plan_deterministically(tmp_foundry) -> None:
    request = _request(
        questions=(
            _plan_question("q3"),
            _plan_question("q1"),
            _plan_question("q2"),
        ),
        limits=EvidencePlanLimits(max_questions=2),
    )
    catalog = AssertionCatalog(tmp_foundry)
    plan = build_evidence_plan(catalog, identity=_identity(), request=request)
    assert [question["question_id"] for question in plan["questions"]] == ["q1", "q2"]
    assert plan["summary"]["questions_total"] == 2


# ---------------------------------------------------------------------------
# Byte-equivalent replay + schema validity.
# ---------------------------------------------------------------------------


def test_build_evidence_plan_is_byte_equivalent_on_replay(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_carp3_replay_a", "workspace-a", "The replay planning fact about gamma is covered.")
    _materialize(tmp_foundry, "rf_run_carp3_replay_b", "workspace-a", "This second fact never mentions the missing term.")
    catalog = AssertionCatalog(tmp_foundry)
    request = _request(
        questions=(
            _plan_question("q_covered", required_terms=("gamma",)),
            _plan_question("q_residual", required_terms=("absolutely-nonexistent-term",)),
        )
    )

    first = build_evidence_plan(catalog, identity=_identity(), request=request)
    second = build_evidence_plan(catalog, identity=_identity(), request=request)

    assert dumps_yaml(first) == dumps_yaml(second)
    assert first["questions"][0]["coverage_state"] == "covered"
    assert first["questions"][1]["coverage_state"] == "residual"


def test_write_evidence_plan_atomic_write_is_byte_identical_across_two_builds(tmp_foundry, tmp_path) -> None:
    _materialize(tmp_foundry, "rf_run_carp3_write_replay", "workspace-a", "The atomic write replay fact about delta.")
    catalog = AssertionCatalog(tmp_foundry)
    request = _request(questions=(_plan_question(required_terms=("delta",)),))

    plan_a = build_evidence_plan(catalog, identity=_identity(), request=request)
    plan_b = build_evidence_plan(catalog, identity=_identity(), request=request)

    path_a = write_evidence_plan(plan_a, tmp_path / "plan_a.yaml")
    path_b = write_evidence_plan(plan_b, tmp_path / "plan_b.yaml")

    assert path_a.read_bytes() == path_b.read_bytes()
    assert not any(child.name.startswith(".plan_a.yaml.") for child in tmp_path.iterdir())


def test_evidence_plan_schema_validity_mixed_covered_and_residual(tmp_foundry) -> None:
    _materialize(tmp_foundry, "rf_run_carp3_schema_a", "workspace-a", "The schema validity fact about epsilon is covered.")
    _materialize(tmp_foundry, "rf_run_carp3_schema_b", "workspace-a", "This fact never mentions the missing schema term.")
    catalog = AssertionCatalog(tmp_foundry)
    request = _request(
        questions=(
            _plan_question("q_covered", required_terms=("epsilon",)),
            _plan_question("q_residual", required_terms=("absolutely-nonexistent-schema-term",)),
        )
    )
    plan = build_evidence_plan(catalog, identity=_identity(), request=request)
    result = validate(plan, "research_evidence_plan")
    assert result.ok, f"expected built evidence plan to validate, got: {result.errors}"


def test_evidence_plan_schema_validity_catalog_denied(tmp_foundry) -> None:
    catalog = AssertionCatalog(tmp_foundry)
    request = _request(questions=(_plan_question("q1"),))
    plan = build_evidence_plan(catalog, identity=None, request=request)
    result = validate(plan, "research_evidence_plan")
    assert result.ok, f"expected denied evidence plan to validate, got: {result.errors}"
