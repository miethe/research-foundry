"""P4-03: reuse-reachability fields on ``POST /api/runs``.

Covers the Phase 4 acceptance criteria (AC-5) from
``docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1/phase-3-4-forward-and-reuse.md``:

* ALLOW — an eligible, workspace-matched, in-contract assertion with
  automated reuse enabled routes through the existing
  ``assertion_reuse.evaluate_reuse`` seam and surfaces ``action: "allow"``.
* DENIED via the existing ``block_authoritative_reuse`` lifecycle path — an
  assertion invalidated through that authoritative mechanism is denied by
  ``evaluate_reuse``'s own ``lifecycle_blocked`` gate, not a new ad hoc check.
* DENIED cross-workspace — a reuse target outside the caller's workspace is
  denied by the same seam's ``workspace_mismatch`` gate.
* Fields-absent regression — omitting all four reuse fields produces a
  response byte-identical (same key set, no ``reuse_decision``) to the
  pre-Phase-4 shape; run launch performs NO reuse evaluation at all.

No new policy logic is introduced here or in the production code this test
exercises — every decision is produced by ``services/assertion_reuse.py``
(``evaluate_reuse`` / ``block_authoritative_reuse``), reached via the
pre-existing ``services/run_launch.py::retrieve_first_reuse_decision`` seam.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.frontmatter import load_md
from research_foundry.schemas import validate
from research_foundry.services import claim_mapping, export_service, extraction
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.assertion_reuse import block_authoritative_reuse
from research_foundry.services.planning import plan_run
from research_foundry.services.run_launch import launch_run
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml


def _enable_automated_reuse(tmp_foundry) -> None:
    """Flip the two controls ``automated_reuse_allowed`` requires (config.py).

    Explicit even though the distribution ``foundry.yaml`` already defaults
    all three assertion-ledger controls to ``true`` for this single-operator
    deployment (``config(assertion-ledger): enable all three local
    capabilities``) -- this test suite must not depend on that default
    remaining true.
    """

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {
        "ledger_write_enabled": True,
        "automated_reuse_enabled": True,
        "canonical_claims_enabled": False,
    }
    dump_yaml(foundry, tmp_foundry.foundry_yaml)


def _disable_automated_reuse(tmp_foundry) -> None:
    """Explicitly turn ``automated_reuse_allowed`` off regardless of default."""

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {
        "ledger_write_enabled": True,
        "automated_reuse_enabled": False,
        "canonical_claims_enabled": False,
    }
    dump_yaml(foundry, tmp_foundry.foundry_yaml)


def _client(tmp_foundry) -> TestClient:
    app = create_app(FoundryConfig(paths=tmp_foundry))
    app.dependency_overrides[get_paths] = lambda: tmp_foundry
    return TestClient(app, raise_server_exceptions=True)


def _eligible_assertion(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "assertion_id": "ast_reuse_001",
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


# ---------------------------------------------------------------------------
# Fields-absent regression
# ---------------------------------------------------------------------------


def test_reuse_fields_absent_leaves_response_shape_unchanged(tmp_foundry) -> None:
    """No reuse_* fields supplied -> identical response shape to pre-Phase-4.

    Proves the "no behavior change on omission" resilience clause by
    inspecting the actual response, not assuming it.
    """

    resp = _client(tmp_foundry).post(
        "/api/runs", json={"text": "No reuse fields supplied at all."}
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert "reuse_decision" not in body
    assert set(body.keys()) == {
        "run_id",
        "status",
        "intent_id",
        "raw_idea_id",
        "brief_path",
        "swarm_path",
        "routing_path",
        "next_step",
        "rf_schema_version",
    }


def test_reuse_ancillary_fields_without_reuse_assertion_trigger_no_evaluation(
    tmp_foundry,
) -> None:
    """``reuse_workspace_id``/``required_reuse_edition_id`` alone (no
    ``reuse_assertion``) must not trigger any reuse evaluation -- mirrors
    ``launch_run``'s own ``if reuse_assertion is not None`` guard."""

    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "Ancillary reuse fields with no assertion payload.",
            "reuse_workspace_id": "workspace-a",
            "required_reuse_edition_id": f"sed_{'a' * 64}",
        },
    )
    assert resp.status_code == 201, resp.text
    assert "reuse_decision" not in resp.json()


# ---------------------------------------------------------------------------
# ALLOW
# ---------------------------------------------------------------------------


def test_reuse_allow_scenario_routes_through_existing_evaluate_reuse_seam(
    tmp_foundry,
) -> None:
    _enable_automated_reuse(tmp_foundry)
    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "Reuse an eligible assertion for this run.",
            "reuse_assertion": _eligible_assertion(),
            "reuse_workspace_id": "workspace-a",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["reuse_decision"] == {
        "action": "allow",
        "reason_code": "eligible",
        "assertion_id": "ast_reuse_001",
    }


# ---------------------------------------------------------------------------
# DENIED
# ---------------------------------------------------------------------------


def test_reuse_denied_via_block_authoritative_reuse_path(tmp_foundry) -> None:
    """An assertion invalidated through the existing ``block_authoritative_reuse``
    lifecycle mechanism is denied by ``evaluate_reuse``'s own
    ``lifecycle_blocked`` gate -- not a new ad hoc check."""

    _enable_automated_reuse(tmp_foundry)
    blocked = block_authoritative_reuse(_eligible_assertion(), event_id="evt_001")
    assert blocked["lifecycle_state"] == "blocked"

    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "A blocked assertion must not be reused.",
            "reuse_assertion": blocked,
            "reuse_workspace_id": "workspace-a",
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == "reuse_not_eligible:lifecycle_blocked"


def test_reuse_denied_cross_workspace_target_via_existing_seam(tmp_foundry) -> None:
    """An unauthorized cross-workspace reuse target is denied via the same
    seam's ``workspace_mismatch`` check, not a new ad hoc check."""

    _enable_automated_reuse(tmp_foundry)
    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "Cross-workspace reuse must be denied.",
            "reuse_assertion": _eligible_assertion(workspace_id="workspace-a"),
            "reuse_workspace_id": "workspace-b",
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == "reuse_not_eligible:workspace_mismatch"


def test_reuse_denied_when_automated_reuse_capability_is_off(
    tmp_foundry,
) -> None:
    """With the ``automated_reuse_enabled`` control off, an otherwise
    fully-eligible assertion is still denied (fail-closed capability gate)."""

    _disable_automated_reuse(tmp_foundry)
    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "Automated reuse capability defaults to off.",
            "reuse_assertion": _eligible_assertion(),
            "reuse_workspace_id": "workspace-a",
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == "reuse_not_eligible:automated_reuse_disabled"


@pytest.mark.parametrize(
    ("reuse_workspace_id"),
    [None, "", "   "],
)
def test_reuse_denied_when_workspace_context_missing_via_resolve_or_deny(
    tmp_foundry, reuse_workspace_id: str | None
) -> None:
    """Absent/blank/whitespace-only ``reuse_workspace_id`` is denied with the
    same ``workspace_context_missing`` reason P1's shared
    ``assertion_workspace.resolve_or_deny`` gate already uses -- confirms
    P4-02's wiring routes the workspace-id normalization through that helper."""

    _enable_automated_reuse(tmp_foundry)
    resp = _client(tmp_foundry).post(
        "/api/runs",
        json={
            "text": "No usable workspace context supplied for reuse.",
            "reuse_assertion": _eligible_assertion(),
            "reuse_workspace_id": reuse_workspace_id,
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["detail"] == "reuse_not_eligible:workspace_context_missing"


# ---------------------------------------------------------------------------
# CARP-4.2: evidence-aware run planning (plan_run / launch_run, service-level)
#
# Exercised directly against the service functions (not the HTTP API): P5
# owns threading identity/policy through the API surface, so these tests
# stay below that boundary while still covering the exact AC this phase
# names ("Each question terminal; selected refs exact; legacy disabled
# behavior stable").
# ---------------------------------------------------------------------------


def _write_carp_intent(paths, *, intent_id: str, primary_questions: list[str]) -> str:
    intent = {
        "id": intent_id,
        "title": "CARP-4.2 evidence-aware planning",
        "owner": "Tester",
        "status": "active",
        "type": "research",
        "objective": "Investigate the CARP-4.2 evidence-aware planning topic.",
        "research_questions": {"primary": primary_questions},
        "governance": {
            "sensitivity": "personal",
            "key_profile_allowed": "personal",
            "requires_human_review": False,
            "allowed_writebacks": ["meatywiki_personal"],
        },
    }
    dump_yaml(intent, paths.intents_active / f"{intent_id}.yaml")
    return intent_id


def _materialize_for_plan(tmp_foundry, run_id: str, workspace_id: str, content: str) -> str:
    """Seeds one real, eligible, ``access_scope="personal"`` assertion --
    same pattern as tests/unit/test_catalog_retrieval.py's ``_materialize``."""

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    # Explicitly enable both controls ``automated_reuse_allowed`` depends on
    # (config.py: ``ledger_write_enabled AND automated_reuse_enabled``) --
    # a test asserting a CARP plan is "covered" must describe a world where
    # automated reuse is permitted. See P6 CARP-6.2 capability-gate fix.
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


def test_plan_run_disabled_retrieval_policy_is_byte_identical_snapshot(tmp_foundry) -> None:
    """Legacy snapshot (AC CARP-4 resilience clause): ``retrieval_policy``
    omitted -- the brief/routing/run.yaml shape must be exactly what it was
    before this phase, no new keys anywhere."""

    intent_id = _write_carp_intent(
        tmp_foundry,
        intent_id="intent_carp42_disabled",
        primary_questions=["What is the CARP-4.2 default behavior?"],
    )
    result = plan_run(intent_id, paths=tmp_foundry)

    brief_meta, _ = load_md(result.brief_path)
    routing = load_yaml(result.routing_path)
    run_doc = load_yaml(result.run_dir / "run.yaml")

    assert "coverage_state" not in brief_meta["questions"]["primary"][0]
    assert "residual_reason" not in brief_meta["questions"]["primary"][0]
    assert "retrieval_policy" not in routing
    assert "residual_question_ids" not in routing
    assert "evidence_plan_ref" not in run_doc
    assert not (result.run_dir / "research_evidence_plan.yaml").exists()


def test_plan_run_catalog_only_marks_each_question_terminal_with_exact_selected_refs(
    tmp_foundry,
) -> None:
    # 5 distinct non-stopword terms -- exactly fits the shared
    # ``max_pages_per_question`` budget (frozen ceiling: 5) that every
    # required term spends one sub-query against (P4 fix-cycle: a question
    # with MORE distinct terms than this budget cannot reach "covered" --
    # see test_plan_run_catalog_only_over_budget_question_never_reports_false_covered).
    covered_q = "Quantum entanglement enables secure key"
    residual_q = "This question matches nothing materialized in the catalog"
    assertion_id = _materialize_for_plan(
        tmp_foundry,
        "rf_run_carp42_seed",
        "workspace-a",
        "Quantum entanglement enables secure key distribution.",
    )
    intent_id = _write_carp_intent(
        tmp_foundry, intent_id="intent_carp42_mixed", primary_questions=[covered_q, residual_q]
    )

    result = plan_run(
        intent_id,
        paths=tmp_foundry,
        identity=AuthIdentity("alice", "workspace-a", ("researcher",)),
        retrieval_policy="catalog_only",
    )

    brief_meta, _ = load_md(result.brief_path)
    primary = brief_meta["questions"]["primary"]
    # Every question is terminal -- exactly one of covered/residual, never a
    # third/absent state.
    assert primary[0]["coverage_state"] == "covered"
    assert primary[0]["residual_reason"] is None
    assert primary[1]["coverage_state"] == "residual"
    assert primary[1]["residual_reason"] is not None

    routing = load_yaml(result.routing_path)
    assert routing["retrieval_policy"] == "catalog_only"
    # catalog_only never routes to discovery, regardless of any question's
    # own coverage_state.
    assert routing["residual_question_ids"] == []

    run_doc = load_yaml(result.run_dir / "run.yaml")
    assert run_doc["evidence_plan_ref"] == f"evp_{result.run_id}"

    plan = load_yaml(result.run_dir / "research_evidence_plan.yaml")
    vres = validate(plan, "research_evidence_plan")
    assert vres.ok, vres.errors
    covered_entry = next(q for q in plan["questions"] if q["question_id"] == primary[0]["id"])
    # Selected refs are exact: assertion_id + assertion_version, pinned.
    assert covered_entry["selected_assertion_ref"] == {"assertion_id": assertion_id, "assertion_version": 1}


def test_plan_run_catalog_only_denies_when_automated_reuse_capability_disabled(
    tmp_foundry,
) -> None:
    """P6 CARP-6.2 capability-gate fix (previously
    ``test_plan_run_catalog_only_KNOWN_GAP_ignores_automated_reuse_capability_disabled``).

    ``services/run_launch.py::retrieve_first_reuse_decision`` has always
    gated ``evaluate_reuse``'s ``allow`` on
    ``AssertionLedgerCapabilities.automated_reuse_allowed`` (line ~106:
    ``if decision.allowed and capabilities is not None and not
    capabilities.automated_reuse_allowed: return ReuseDecision("deny",
    "automated_reuse_disabled", ...)``). CARP-2.2's plan row and AC CARP-1's
    propagation_contract both name that same capability as an input the CARP
    catalog-retrieval path must also respect -- and until this fix, it did
    not (``catalog_retrieval.retrieve()`` never touched the capability).

    Fixed by threading the real resolved capability
    (``FoundryConfig.assertion_ledger_capabilities().automated_reuse_allowed``)
    through :class:`RetrievalConstraints` into ``retrieve()``, which now
    collapses every otherwise-``allow`` candidate into the SAME
    ``deny``/``automated_reuse_disabled`` reason code the ledger seam emits.
    That reuses the frozen ``reuse_denied`` residual reason (§3.2 enum is
    closed, no new member added).

    Verified fail-closed: with ``automated_reuse_enabled: false``, an
    otherwise-fully-eligible catalog candidate under ``catalog_only``
    resolves ``residual``/``reuse_denied`` and produces no
    ``selected_assertion_ref`` -- never ``covered``.
    """

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {
        "ledger_write_enabled": True,
        "automated_reuse_enabled": False,
    }
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    _materialize_for_plan(
        tmp_foundry,
        "rf_run_carp62_capability_gap",
        "workspace-a",
        "Quantum entanglement enables secure key distribution.",
    )
    # Re-disable AFTER materialization (which flips ledger_write_enabled on
    # via its own _materialize_for_plan write and drops the automated_reuse
    # control) -- the run under test must observe the capability-disabled
    # foundry.yaml, not the materialization-time one.
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {
        "ledger_write_enabled": True,
        "automated_reuse_enabled": False,
    }
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    intent_id = _write_carp_intent(
        tmp_foundry,
        intent_id="intent_carp62_capability_gap",
        primary_questions=["Quantum entanglement enables secure key"],
    )

    result = plan_run(
        intent_id,
        paths=tmp_foundry,
        identity=AuthIdentity("alice", "workspace-a", ("researcher",)),
        retrieval_policy="catalog_only",
    )

    plan = load_yaml(result.run_dir / "research_evidence_plan.yaml")
    question = plan["questions"][0]
    # Fail-closed: capability disabled ⇒ residual / reuse_denied, no selection.
    assert question["coverage_state"] == "residual"
    assert question["residual_reason"] == "reuse_denied"
    assert question["selected_assertion_ref"] is None


def test_plan_run_catalog_only_covers_when_automated_reuse_capability_enabled(
    tmp_foundry,
) -> None:
    """Positive companion to the capability-disabled case above: an otherwise-
    eligible catalog candidate under ``catalog_only`` reaches ``covered``
    when ``automated_reuse_enabled: true`` -- the enabled path is genuinely
    reachable (not vacuously closed by the fix)."""

    assertion_id = _materialize_for_plan(
        tmp_foundry,
        "rf_run_carp62_capability_ok",
        "workspace-a",
        "Quantum entanglement enables secure key distribution.",
    )
    intent_id = _write_carp_intent(
        tmp_foundry,
        intent_id="intent_carp62_capability_ok",
        primary_questions=["Quantum entanglement enables secure key"],
    )

    result = plan_run(
        intent_id,
        paths=tmp_foundry,
        identity=AuthIdentity("alice", "workspace-a", ("researcher",)),
        retrieval_policy="catalog_only",
    )

    plan = load_yaml(result.run_dir / "research_evidence_plan.yaml")
    question = plan["questions"][0]
    assert question["coverage_state"] == "covered"
    assert question["selected_assertion_ref"] == {"assertion_id": assertion_id, "assertion_version": 1}


def test_plan_run_catalog_only_over_budget_question_never_reports_false_covered(
    tmp_foundry,
) -> None:
    """P4 fix-cycle headline regression: a question with MORE distinct
    content terms than the shared ``max_pages_per_question`` budget (frozen
    ceiling: 5) must never be marked ``covered`` just because a candidate
    happens to match the first 5 of those terms in first-occurrence order.

    Before the fix, ``_lexical_terms`` silently capped ``required_terms`` at
    5 -- so this exact candidate (which matches only the question's first 5
    of 8 distinct terms) passed condition 1 (``matched_terms ==
    frozenset(required_terms)``) against the truncated 5-term set and was
    marked ``covered``. This test fails against that pre-fix behavior.

    After the fix, all 8 terms are passed through uncapped. The shared
    budget is exhausted after the first 5 required-term sub-queries, so the
    remaining 3 terms ("dioxide", "oxygen", "glucose") are never even
    queried -- the adapter's own pre-existing fail-closed mechanism
    (``pagination_limit_reached``) then correctly resolves this question
    ``residual``, not ``covered``.
    """

    over_budget_q = "Photosynthesis converts sunlight, water, and carbon dioxide into oxygen and glucose."
    _materialize_for_plan(
        tmp_foundry,
        "rf_run_carp4fix_overbudget",
        "workspace-a",
        "Photosynthesis converts sunlight and water using carbon efficiently in green leaves.",
    )
    intent_id = _write_carp_intent(
        tmp_foundry, intent_id="intent_carp4fix_overbudget", primary_questions=[over_budget_q]
    )

    result = plan_run(
        intent_id,
        paths=tmp_foundry,
        identity=AuthIdentity("alice", "workspace-a", ("researcher",)),
        retrieval_policy="catalog_only",
    )

    plan = load_yaml(result.run_dir / "research_evidence_plan.yaml")
    question = plan["questions"][0]
    assert question["required_terms"] == [
        "photosynthesis",
        "converts",
        "sunlight",
        "water",
        "carbon",
        "dioxide",
        "oxygen",
        "glucose",
    ]
    assert question["coverage_state"] == "residual"
    assert question["residual_reason"] == "pagination_limit"

    brief_meta, _ = load_md(result.brief_path)
    assert brief_meta["questions"]["primary"][0]["coverage_state"] == "residual"


def test_plan_run_default_fallback_question_terms_are_not_stopword_dominated(
    tmp_foundry,
) -> None:
    """P4 fix-cycle: ``_build_questions``'s no-``research_questions`` branch
    (``f"What does the evidence say about {objective}?"``) must derive
    ``required_terms`` from the objective's real topical words, not from the
    template's own boilerplate function words.

    Before the fix, the first five ≥3-char tokens of that exact template
    sentence are ``{what, does, the, evidence, say}`` -- the cap consumed
    every slot on template scaffolding before the objective's words were
    ever reached, so ``required_terms`` never contained the objective at
    all, and a candidate containing only that boilerplate matched condition
    1 and was marked ``covered`` regardless of topic.
    """

    _materialize_for_plan(
        tmp_foundry,
        "rf_run_carp4fix_fallback",
        "workspace-a",
        "What does the evidence say about this topic here.",
    )
    intent_id = "intent_carp4fix_fallback"
    intent = {
        "id": intent_id,
        "title": "CARP-4 fix-cycle default fallback question",
        "owner": "Tester",
        "status": "active",
        "type": "research",
        "objective": "renewable energy grid storage economics",
        "governance": {
            "sensitivity": "personal",
            "key_profile_allowed": "personal",
            "requires_human_review": False,
            "allowed_writebacks": ["meatywiki_personal"],
        },
    }
    dump_yaml(intent, tmp_foundry.intents_active / f"{intent_id}.yaml")

    result = plan_run(
        intent_id,
        paths=tmp_foundry,
        identity=AuthIdentity("alice", "workspace-a", ("researcher",)),
        retrieval_policy="catalog_only",
    )

    plan = load_yaml(result.run_dir / "research_evidence_plan.yaml")
    required_terms = plan["questions"][0]["required_terms"]

    stopwords_that_must_be_absent = {"what", "does", "the", "say", "about", "evidence"}
    assert not (stopwords_that_must_be_absent & set(required_terms))
    for topical_term in ("renewable", "energy", "grid", "storage", "economics"):
        assert topical_term in required_terms

    assert plan["questions"][0]["coverage_state"] == "residual"
    brief_meta, _ = load_md(result.brief_path)
    assert brief_meta["questions"]["primary"][0]["coverage_state"] == "residual"


def test_plan_run_stopword_only_question_never_vacuously_covers_an_unrelated_candidate(
    tmp_foundry,
) -> None:
    """P6 CARP-6.9 F1 headline regression: a question whose text is entirely
    stopwords must not derive ``required_terms == ()``, because
    ``catalog_retrieval.retrieve()``'s condition 1 treats an empty
    ``required_terms`` as vacuously true -- EVERY authorized candidate would
    report ``lexical_match=True`` regardless of topic. Before the F1 fix,
    this exact question would have silently marked an unrelated candidate
    ``covered``; after the fix, the fallback (unfiltered) token set still
    discriminates against unrelated content, so the unrelated candidate
    correctly resolves ``residual``."""

    _materialize_for_plan(
        tmp_foundry,
        "rf_run_carp69_f1_unrelated",
        "workspace-a",
        "Quantum entanglement enables secure key distribution.",
    )
    intent_id = _write_carp_intent(
        tmp_foundry,
        intent_id="intent_carp69_f1",
        primary_questions=["What is the evidence for and against this?"],
    )

    result = plan_run(
        intent_id,
        paths=tmp_foundry,
        identity=AuthIdentity("alice", "workspace-a", ("researcher",)),
        retrieval_policy="catalog_only",
    )

    plan = load_yaml(result.run_dir / "research_evidence_plan.yaml")
    question = plan["questions"][0]
    assert question["required_terms"] != []
    assert question["coverage_state"] == "residual"
    # The 7-term fallback set exceeds the shared max_pages_per_question
    # budget (frozen ceiling: 5), so this exact fixture resolves via the
    # adapter's own pre-existing pagination guard rather than a clean
    # lexical miss -- either way, never "covered" (the pre-fix fail-open
    # this regression guards against).
    assert question["residual_reason"] in ("lexical_miss", "no_candidate", "pagination_limit")
    assert question["selected_assertion_ref"] is None


def test_plan_run_catalog_then_discovery_residual_ids_populate_routing(tmp_foundry) -> None:
    intent_id = _write_carp_intent(
        tmp_foundry,
        intent_id="intent_carp42_ctd",
        primary_questions=["No catalog content matches this question at all"],
    )
    result = plan_run(
        intent_id,
        paths=tmp_foundry,
        identity=AuthIdentity("alice", "workspace-a", ("researcher",)),
        retrieval_policy="catalog_then_discovery",
    )
    brief_meta, _ = load_md(result.brief_path)
    q_id = brief_meta["questions"]["primary"][0]["id"]
    assert brief_meta["questions"]["primary"][0]["coverage_state"] == "residual"

    routing = load_yaml(result.routing_path)
    assert routing["retrieval_policy"] == "catalog_then_discovery"
    assert routing["residual_question_ids"] == [q_id]


def test_plan_run_omitted_sensitivity_threshold_never_defaults_to_allow(tmp_foundry) -> None:
    """A run whose declared sensitivity posture cannot be represented as a
    known rank (an intentionally-malformed governance.sensitivity) must
    never silently grant a ceiling -- covered would only be reachable via a
    fabricated default this function must not invent."""

    _materialize_for_plan(
        tmp_foundry, "rf_run_carp42_malformed", "workspace-a", "The malformed sensitivity fact is here."
    )
    intent_id = "intent_carp42_malformed"
    intent = {
        "id": intent_id,
        "title": "Malformed sensitivity",
        "owner": "Tester",
        "status": "active",
        "type": "research",
        "objective": "Investigate malformed sensitivity handling.",
        "research_questions": {"primary": ["The malformed sensitivity fact is here"]},
        "governance": {
            "sensitivity": "not_a_real_rank",
            "key_profile_allowed": "personal",
            "requires_human_review": False,
            "allowed_writebacks": ["meatywiki_personal"],
        },
    }
    dump_yaml(intent, tmp_foundry.intents_active / f"{intent_id}.yaml")

    result = plan_run(
        intent_id,
        paths=tmp_foundry,
        identity=AuthIdentity("alice", "workspace-a", ("researcher",)),
        retrieval_policy="catalog_only",
    )
    brief_meta, _ = load_md(result.brief_path)
    assert brief_meta["questions"]["primary"][0]["coverage_state"] == "residual"


def test_launch_run_threads_retrieval_policy_and_identity_to_plan_run(tmp_foundry) -> None:
    intent_id = _write_carp_intent(
        tmp_foundry,
        intent_id="intent_carp42_launch",
        primary_questions=["No catalog content matches this one either"],
    )
    result = launch_run(
        intent_id=intent_id,
        paths=tmp_foundry,
        identity=AuthIdentity("alice", "workspace-a", ("researcher",)),
        retrieval_policy="catalog_only",
    )
    routing = load_yaml(result.routing_path)
    assert routing["retrieval_policy"] == "catalog_only"
    run_doc = load_yaml(tmp_foundry.run_paths(result.run_id).run / "run.yaml")
    assert run_doc["evidence_plan_ref"] is not None


def test_launch_run_default_retrieval_policy_is_disabled(tmp_foundry) -> None:
    """``launch_run`` without ``retrieval_policy`` is byte-identical to
    every pre-CARP-4.2 call site (fields-absent regression, mirroring the
    HTTP-level test above but for the service function itself)."""

    intent_id = _write_carp_intent(
        tmp_foundry, intent_id="intent_carp42_launch_default", primary_questions=["Default launch behavior"]
    )
    result = launch_run(intent_id=intent_id, paths=tmp_foundry)
    routing = load_yaml(result.routing_path)
    assert "retrieval_policy" not in routing
    assert "residual_question_ids" not in routing


def test_launch_run_selected_ref_round_trips_byte_exact_through_export(tmp_foundry) -> None:
    """P6 CARP-6.6 gap fill: a genuine end-to-end round-trip through the
    real production pipeline -- ``launch_run`` -> ``plan_run`` (writes
    ``research_evidence_plan.yaml`` to disk) -> ``export_service.export_run``
    (reads that same file back) -- with NO hand-built synthetic plan fixture
    anywhere in between (unlike test_export_service.py's own retrieval
    tests, which construct a plan dict directly via ``_carp_evidence_plan``).

    Proves the CARP-owned selection-provenance carrier (carp-contract-
    freeze.md §4.1 -- ``selected_assertion_ref``/``retrieval_receipt``, the
    substitute for "RPC context" until C1 lands) survives that whole chain
    byte-exact: the same ``assertion_id``/``assertion_version`` selected
    during real catalog retrieval is what export ultimately reports."""

    assertion_id = _materialize_for_plan(
        tmp_foundry,
        "rf_run_carp66_roundtrip",
        "workspace-a",
        "Quantum entanglement enables secure key distribution end to end.",
    )
    intent_id = _write_carp_intent(
        tmp_foundry,
        intent_id="intent_carp66_roundtrip",
        # Exactly 5 distinct non-stopword terms -- fits the shared
        # max_pages_per_question budget (frozen ceiling: 5), same pattern as
        # test_plan_run_catalog_only_marks_each_question_terminal_with_exact_selected_refs.
        primary_questions=["Quantum entanglement enables secure key"],
    )

    launch_result = launch_run(
        intent_id=intent_id,
        paths=tmp_foundry,
        identity=AuthIdentity("alice", "workspace-a", ("researcher",)),
        retrieval_policy="catalog_only",
    )

    # The plan as actually persisted by the real pipeline (not a fixture).
    plan_on_disk = load_yaml(tmp_foundry.run_paths(launch_result.run_id).run / "research_evidence_plan.yaml")
    plan_question = plan_on_disk["questions"][0]
    assert plan_question["coverage_state"] == "covered"
    assert plan_question["selected_assertion_ref"] == {"assertion_id": assertion_id, "assertion_version": 1}
    plan_receipt = plan_question["retrieval_receipt"]
    assert plan_receipt is not None
    assert plan_receipt["source"] == "catalog"

    exported = export_service.export_run(tmp_foundry, launch_result.run_id)
    retrieval = exported["retrieval"]
    assert retrieval is not None
    assert retrieval["evidence_plan_ref"] == plan_on_disk["evidence_plan_id"]

    exported_selection = next(
        s for s in retrieval["selections"] if s["question_id"] == plan_question["question_id"]
    )
    # Byte-exact: the assertion_id/version export reports is the identical
    # pair the real catalog retrieval selected -- not a re-derived or
    # re-fetched value.
    assert exported_selection["assertion_id"] == plan_question["selected_assertion_ref"]["assertion_id"]
    assert exported_selection["assertion_version"] == plan_question["selected_assertion_ref"]["assertion_version"]
    assert exported_selection["coverage_state"] == "covered"
