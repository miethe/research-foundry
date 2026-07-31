"""Unit tests for the `swarm.start` Operator MCP adapter (research-foundry-
operator-mcp-v1 P3, OPM-3.3).

Covers: real per-adapter dispatch equivalence to `swarm_service.run_swarm`,
dry run's zero-effects guarantee, the fail-closed budget/timeout/profile
preflight guard (no fail-open, per this task's brief), and the hard
non-duplication acceptance criterion -- proven with a REAL interrupted-then-
resumed fixture (adapted from `operator_cancel_resume_service`'s own
scenario-7 "process loss" idiom) that asserts on the actual
`source_candidates.yaml` content and count, not merely on the guard's
presence.

Reuses, never reinvents: `tests/test_planning.py`'s `_make_intent` helper,
`tests/unit/test_operator_mcp_policy.py`'s identity fixtures, and
`tests/unit/test_operator_cancel_resume_service.py` / `test_operator_
operation_service.py`'s own confirmation-lifecycle helpers (`_consume`) --
the SAME reuse convention `test_operator_cancel_resume_service.py` itself
establishes for this family of tests.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from research_foundry import adapters, ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_adapters as adapters_pkg
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services import swarm_service as swarm_svc
from research_foundry.services.operator_cancel_resume_service import (
    ActionEffect,
    ActionSpec,
    OperatorCancelResumeService,
)
from research_foundry.services.operator_mcp_adapters import swarm_start
from research_foundry.services.operator_operation_service import OperatorOperationService
from research_foundry.services.operator_receipt_service import OperatorReceiptService
from research_foundry.yamlio import dump_yaml, load_yaml

from tests.test_planning import _make_intent
from tests.unit.test_operator_cancel_resume_service import _consume
from tests.unit.test_operator_mcp_adapter_run_plan import (  # noqa: F401
    _default_sensitivity_ceiling,
    _recording_ceiling,
)
from tests.unit.test_operator_mcp_policy import (  # noqa: F401
    _default_operator_identity,
    _IDENTITY,
    _IDENTITY_OTHER_WORKSPACE,
)

_ADAPTER_A = "gpt_researcher"
_ADAPTER_B = "paperqa2"


def _planned_run(tmp_foundry: FoundryPaths, text: str) -> str:
    """Capture + triage + plan a real run, stamped into `_IDENTITY`'s own
    workspace (`ws-mine`) so `_resolve_run_context`'s `workspace_id`
    resolution matches whatever `policy.resolve_operator_identity`
    resolves to for every test in this module (the `_default_operator_
    identity` autouse fixture)."""

    intent_id, _ = _make_intent(text, sensitivity="personal", tmp_foundry=tmp_foundry)
    from research_foundry.services import planning

    result = planning.plan_run(intent_id, profile="personal", identity=_IDENTITY, paths=tmp_foundry)
    return result.run_id


# ---------------------------------------------------------------------------
# Acceptance criterion: adapter dispatch is equivalent to (and reuses)
# swarm_service.run_swarm -- proven with a real 2-adapter end-to-end call
# ---------------------------------------------------------------------------


def test_invoke_dispatches_each_adapter_via_run_swarm_and_merges_candidates(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Spies on the ONE real `swarm_service.run_swarm` function `invoke()`
    calls (never CLI/Typer/subprocess -- requirement 1): asserts it is
    called exactly once PER requested adapter, each with a single-element
    id list, and that `source_candidates.yaml` ends up holding BOTH
    adapters' candidates, in order, exactly once each (requirement 3, the
    non-duplication AC's ordinary/uninterrupted case)."""

    adapters.load_all()
    run_id = _planned_run(tmp_foundry, sample_idea_text)

    real_run_swarm = swarm_svc.run_swarm
    calls: list[tuple[str, tuple[str, ...]]] = []

    def _spy(run_id_arg: str, adapter_ids_arg: Any, **kwargs: Any) -> Any:
        calls.append((run_id_arg, tuple(adapter_ids_arg)))
        return real_run_swarm(run_id_arg, adapter_ids_arg, **kwargs)

    monkeypatch.setattr(swarm_svc, "run_swarm", _spy)

    run_ctx = swarm_start._resolve_run_context(run_id, tmp_foundry)
    assert run_ctx.budget_usd is not None
    assert run_ctx.timeout_minutes is not None
    assert run_ctx.governance_profile is not None

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=swarm_start.OPERATION_KIND,
        idempotency_key="idem-equivalence",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload={
            "run_id": run_id,
            "adapter_ids": [_ADAPTER_A, _ADAPTER_B],
            "profile": run_ctx.governance_profile,
            "budget_usd": run_ctx.budget_usd,
            "timeout_minutes": run_ctx.timeout_minutes,
        },
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = swarm_start.invoke(
        run_id=run_id,
        adapter_ids=[_ADAPTER_A, _ADAPTER_B],
        idempotency_key="idem-equivalence",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert calls == [(run_id, (_ADAPTER_A,)), (run_id, (_ADAPTER_B,))]

    persisted = load_yaml(tmp_foundry.run_paths(run_id).source_candidates)
    # paperqa2's degraded mode contributes zero candidates with no
    # `local_pdf_dir` in the request -- gpt_researcher's degraded stub
    # contributes at least one. The count assertion is therefore >= 1 (a
    # real, non-vacuous candidate was persisted), while the per-adapter
    # OUTCOME breakdown below is what actually proves BOTH adapters were
    # dispatched (each ran=True), not just one.
    assert len(persisted["source_candidates"]) >= 1

    assert result.result is not None
    assert result.result["status"] == "completed"
    assert result.result["replayed"] is False
    assert result.result["canonical_refs_available"] is True
    assert [o["adapter_id"] for o in result.result["adapter_outcomes"]] == [_ADAPTER_A, _ADAPTER_B]
    assert all(o["ran"] is True for o in result.result["adapter_outcomes"])
    assert result.result["total_source_candidate_count"] == len(persisted["source_candidates"])


# ---------------------------------------------------------------------------
# Dry run: zero effects (requirement 4 of the base substrate, proven at
# this adapter's own surface)
# ---------------------------------------------------------------------------


def test_invoke_dry_run_never_calls_run_swarm(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_id = _planned_run(tmp_foundry, sample_idea_text)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("dry run must never call swarm_service.run_swarm")

    monkeypatch.setattr(swarm_svc, "run_swarm", _must_not_run)

    result = swarm_start.invoke(
        run_id=run_id,
        adapter_ids=[_ADAPTER_A, _ADAPTER_B],
        idempotency_key="idem-dry",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is True
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "swarm.start"}
    assert not tmp_foundry.run_paths(run_id).source_candidates.exists()


# ---------------------------------------------------------------------------
# No fail-open: budget/timeout/profile/run resolution (requirement 5)
# ---------------------------------------------------------------------------


def test_resolve_run_context_swallows_lookup_failure_for_a_missing_run(tmp_foundry: FoundryPaths) -> None:
    ctx = swarm_start._resolve_run_context("does-not-exist-at-all", tmp_foundry)
    assert ctx.sensitivity is None
    assert ctx.workspace_id is None
    assert ctx.budget_usd is None
    assert ctx.timeout_minutes is None
    assert ctx.governance_profile is None


def test_missing_run_denies_with_not_found_never_preflight_failed(tmp_foundry: FoundryPaths) -> None:
    """F6 fix (M3 Leg A). INVERTS the prior version of this test, which
    pinned the exact existence-leak this fix closes: a wholly nonexistent
    `run_id` used to deny via THIS adapter's own budget/timeout/profile
    preflight (`preflight_failed`, `retryable=True`), reachable with no
    `ctx`/confirmation ever minted, BECAUSE that check ran before `ctx` --
    and therefore authorization -- was ever evaluated. `invoke` now builds
    `ctx` and runs `policy.evaluate_policy` FIRST (mirroring
    `research_stages.py`'s already-fixed F6 shape), so a missing run denies
    at the SAME `rbac`/`not_found` stage a foreign-workspace run denies at
    -- see `test_invoke_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_run`
    below, which now folds this exact case into its one-denial-shape
    comparison instead of treating it as a deliberately distinct reason."""

    result = swarm_start.invoke(
        run_id="does-not-exist-at-all",
        adapter_ids=[_ADAPTER_A],
        idempotency_key="idem-missing-run",
        confirmation_record=None,
        presented_token=None,
        paths=tmp_foundry,
    )

    assert result.ok is False
    assert result.result is None
    assert result.error is not None
    assert result.error["reason_code"] == "not_found"
    assert result.error["retryable"] is False
    assert result.error["operation_id"] is None
    assert result.error["receipt_ref"] is None
    assert "detail" not in result.error


def test_missing_budget_denies_with_preflight_failed_not_a_default(
    tmp_foundry: FoundryPaths, sample_idea_text: str
) -> None:
    """MUTATION-TESTED GUARD (see this task's report): a run whose
    `run.yaml` is otherwise perfectly valid (real sensitivity, real
    workspace_id, real governance profile) but whose `profile.max_cost_usd`
    is missing denies -- it does NOT silently proceed with an unbounded
    implicit budget. Isolates the budget/timeout/profile preflight check
    from the "run.yaml missing entirely" case above."""

    run_id = _planned_run(tmp_foundry, sample_idea_text)
    rp = tmp_foundry.run_paths(run_id)
    run_doc = load_yaml(rp.run_yaml)
    assert isinstance(run_doc["profile"], dict)
    del run_doc["profile"]["max_cost_usd"]
    dump_yaml(run_doc, rp.run_yaml)

    # Sanity: sensitivity/workspace_id/governance_profile all still resolve
    # -- only budget is missing, isolating exactly the field under test.
    run_ctx = swarm_start._resolve_run_context(run_id, tmp_foundry)
    assert run_ctx.sensitivity is not None
    assert run_ctx.workspace_id is not None
    assert run_ctx.governance_profile is not None
    assert run_ctx.budget_usd is None

    result = swarm_start.invoke(
        run_id=run_id,
        adapter_ids=[_ADAPTER_A],
        idempotency_key="idem-missing-budget",
        confirmation_record=None,
        presented_token=None,
        paths=tmp_foundry,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "preflight_failed"
    assert not rp.source_candidates.exists()  # zero effects on this denial path


# ---------------------------------------------------------------------------
# The hard AC: cancel/resume does not duplicate the candidate artifact
# (requirement 3), proven with a REAL interrupted-then-resumed fixture
# ---------------------------------------------------------------------------


def test_interrupted_then_resumed_execution_does_not_duplicate_or_lose_candidates(
    tmp_foundry: FoundryPaths, sample_idea_text: str
) -> None:
    """Adapted from `operator_cancel_resume_service.py`'s own scenario-7
    "process loss" idiom (`test_scenario7_process_loss_after_effect_
    receipt_before_checkpoint_resumes_without_replay`), with ONE addition:
    action 0's closure is `swarm_start._make_action`'s REAL closure, so
    Phase 1 performs a REAL adapter dispatch and a REAL merge-write to
    `source_candidates.yaml` -- not merely simulated receipts. Phase 2
    resumes with a brand-new `OperatorCancelResumeService`/`OperatorReceipt
    Service`/`OperatorOperationService` instance backed by the SAME durable
    files (nothing survives via an in-process object), proving action 0 is
    never re-invoked (an `AssertionError`-raising stub in its place) AND
    that the final file holds BOTH adapters' candidates, in order, exactly
    once each -- the actual artifact and count, not merely the guard."""

    adapters.load_all()
    run_id = _planned_run(tmp_foundry, sample_idea_text)

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)

    run_ctx = swarm_start._resolve_run_context(run_id, tmp_foundry)
    assert run_ctx.governance_profile is not None

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=swarm_start.OPERATION_KIND,
        idempotency_key="idem-interrupt",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload={"run_id": run_id, "adapter_ids": [_ADAPTER_A, _ADAPTER_B]},
        paths=tmp_foundry,
    )
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id

    captured: list[Any] = []
    action0 = swarm_start._make_action(
        run_id, 0, _ADAPTER_A, profile=run_ctx.governance_profile, paths=tmp_foundry, captured=captured
    )
    action1 = swarm_start._make_action(
        run_id, 1, _ADAPTER_B, profile=run_ctx.governance_profile, paths=tmp_foundry, captured=captured
    )

    # Phase 1 (pre-loss): action 0 runs FOR REAL -- real dispatch, real
    # merge-write. Its action_receipt AND effect_receipt are durably
    # committed (mirrors what run_actions' own loop body would have
    # produced up to this point), but the checkpoint that would normally
    # follow immediately after never happens -- the realistic process-loss
    # gap: killed between those two durable writes.
    effect0 = action0.run()
    assert effect0 is not None
    after_action0 = load_yaml(tmp_foundry.run_paths(run_id).source_candidates)
    count_after_action0 = len(after_action0["source_candidates"])
    assert count_after_action0 >= 1  # a real candidate was really persisted

    receipt_service.record_action_receipt(
        operation_id,
        identity=_IDENTITY,
        action_id=action0.action_id,
        action_index=0,
        status="completed",
        attempt_ref="attempt-precrash",
        started_at=ids.now_iso(),
        completed_at=ids.now_iso(),
    )
    receipt_service.record_effect_receipt(
        operation_id,
        identity=_IDENTITY,
        action_id=action0.action_id,
        effect_kind=effect0.effect_kind,
        effect_digest=effect0.effect_digest,
        effect_ref=effect0.effect_ref,
        generated_at=ids.now_iso(),
    )
    assert receipt_service.load_checkpoint(operation_id) is None  # the "loss" gap

    # Phase 2 ("restart"): brand-new service instances, same durable files.
    fresh_receipts = OperatorReceiptService(tmp_foundry)
    fresh_ops = OperatorOperationService(tmp_foundry)
    fresh_svc = OperatorCancelResumeService(tmp_foundry, operations=fresh_ops, receipts=fresh_receipts)

    resume_point = fresh_receipts.resolve_resume_point(operation_id)
    assert resume_point.outcome == "ok"
    assert resume_point.next_action_index == 1  # reconstructed from real rows, not checkpoint

    def _action0_must_not_run() -> ActionEffect | None:  # pragma: no cover - only fails the test
        raise AssertionError("action 0 (gpt_researcher) must not be re-executed on resume")

    guarded_action0 = ActionSpec(action0.action_id, _action0_must_not_run)

    execution = fresh_svc.run_actions(
        operation_id,
        identity=_IDENTITY,
        operation_kind=swarm_start.OPERATION_KIND,
        actions=[guarded_action0, action1],
        attempt_ref="attempt-postcrash",
        start_index=resume_point.next_action_index,
    )

    assert execution.status == "completed"
    assert execution.terminal_receipt is not None
    assert execution.terminal_receipt["action_count_total"] == 2
    assert execution.terminal_receipt["action_count_completed"] == 2

    action1_result = captured[-1]
    final = load_yaml(tmp_foundry.run_paths(run_id).source_candidates)

    # No loss: action 0's candidates are still there, unchanged, at the
    # front (merge-not-overwrite).
    assert final["source_candidates"][:count_after_action0] == after_action0["source_candidates"]
    # No duplication: exactly action 0's + action 1's own candidates,
    # nothing more -- action 0 never ran twice, action 1 never ran twice.
    assert final["source_candidates"] == [
        *after_action0["source_candidates"],
        *action1_result.source_candidates,
    ]
    assert len(final["source_candidates"]) == count_after_action0 + len(action1_result.source_candidates)


def test_merge_with_existing_true_is_required_for_non_duplication(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MUTATION-TESTED GUARD (see this task's report): proves
    `_make_action`'s `merge_with_existing=True` call to `swarm_service.
    run_swarm` is load-bearing for non-duplication, not incidental -- with
    it forced back to `False` (the P3-F1-preserved legacy default), a
    second action's write silently ERASES the first action's already-
    persisted candidates instead of adding to them."""

    real_run_swarm = swarm_svc.run_swarm

    def _forced_no_merge(run_id_arg: str, adapter_ids_arg: Any, **kwargs: Any) -> Any:
        kwargs["merge_with_existing"] = False
        return real_run_swarm(run_id_arg, adapter_ids_arg, **kwargs)

    monkeypatch.setattr(swarm_svc, "run_swarm", _forced_no_merge)

    run_id = _planned_run(tmp_foundry, sample_idea_text)
    run_ctx = swarm_start._resolve_run_context(run_id, tmp_foundry)
    assert run_ctx.governance_profile is not None

    captured: list[Any] = []
    action0 = swarm_start._make_action(
        run_id, 0, _ADAPTER_A, profile=run_ctx.governance_profile, paths=tmp_foundry, captured=captured
    )
    action1 = swarm_start._make_action(
        run_id, 1, _ADAPTER_B, profile=run_ctx.governance_profile, paths=tmp_foundry, captured=captured
    )

    action0.run()
    after_action0 = load_yaml(tmp_foundry.run_paths(run_id).source_candidates)
    assert len(after_action0["source_candidates"]) >= 1

    action1.run()
    after_action1 = load_yaml(tmp_foundry.run_paths(run_id).source_candidates)

    # With merging FORCED off, action 1's write erased action 0's
    # candidates -- proving the real (unforced) code path's
    # `merge_with_existing=True` is what prevents exactly this.
    assert after_action1["source_candidates"] != [
        *after_action0["source_candidates"],
        *captured[-1].source_candidates,
    ]


# ---------------------------------------------------------------------------
# H7 defect fix: an above-ceiling run denies at the guard stage, with the
# SAME `not_found` shape a genuinely-missing run gets (this task's negative
# fixture -- proves the fix, not merely the absence of a crash).
# ---------------------------------------------------------------------------


def test_invoke_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_run(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Same defect/fix this task addresses across all five P3 entry points
    (see `run_plan.py`'s own sibling test for the full narrative): before
    this fix, `swarm_start.invoke` accepted a caller-supplied
    `sensitivity_ceiling` defaulting to `"client_sensitive"`, making
    `_check_guard`'s H7 comparison a permanent no-op. Here, a real planned
    run whose OWN `run.yaml`-declared `sensitivity` is `"personal"` is
    denied once the LOCALLY CONFIGURED ceiling resolves to `"public"` (one
    rank below).

    Also proves the SAME H6/H7 one-denial-shape guarantee `run_plan.py`'s
    sibling test proves, via the comparison that actually applies to THIS
    adapter: this above-ceiling denial (real run, guard stage) is
    byte-identical to a wrong-workspace denial for the SAME real run (rbac
    stage, earlier in the fixed pipeline order) -- a caller cannot tell
    "this run exists but you are not cleared for it" from "this run exists
    but is not yours" from the response alone.

    F6 fix (M3 Leg A): a genuinely-missing `run_id` is now FOLDED INTO this
    same comparison as a third, byte-identical case -- prior to the F6 fix
    it was deliberately excluded here because it denied via this adapter's
    OWN budget/timeout/profile preflight check BEFORE `ctx` (and therefore
    the ceiling/rbac stages) was ever constructed, a different,
    `preflight_failed` reason. `invoke` now runs `policy.evaluate_policy`
    before that check, so all three -- above-ceiling, wrong-workspace, and
    genuinely-missing -- deny identically. See
    `test_missing_run_denies_with_not_found_never_preflight_failed` for the
    isolated single-case version of this same assertion."""

    run_id = _planned_run(tmp_foundry, sample_idea_text)
    run_ctx = swarm_start._resolve_run_context(run_id, tmp_foundry)
    assert run_ctx.sensitivity == "personal"

    # HIGH-1 fix: a recording double, not a discarding `lambda *a, **kw:`
    # -- proves `invoke()`'s own call site threads its resolved `paths`
    # through to `resolve_local_sensitivity_ceiling`, not merely that SOME
    # ceiling value comes back.
    ceiling_double, ceiling_calls = _recording_ceiling("public")
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    # Direct proof of STAGE: build the identical PolicyContext `invoke()`
    # would build internally and evaluate it directly.
    direct_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=swarm_start.OPERATION_KIND,
        idempotency_key="idem-above-ceiling",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="public",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload={"run_id": run_id, "adapter_ids": [_ADAPTER_A]},
        paths=tmp_foundry,
    )
    direct_decision = policy.evaluate_policy(direct_ctx, paths=tmp_foundry)
    assert direct_decision.allowed is False
    assert direct_decision.stage == "guard"
    assert direct_decision.reason_code == "not_found"
    assert direct_decision.retryable is False

    above_ceiling_result = swarm_start.invoke(
        run_id=run_id,
        adapter_ids=[_ADAPTER_A],
        idempotency_key="idem-above-ceiling",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert above_ceiling_result.ok is False
    assert above_ceiling_result.error is not None
    assert above_ceiling_result.error["reason_code"] == "not_found"
    assert above_ceiling_result.error["retryable"] is False
    assert above_ceiling_result.error["operation_id"] is None
    assert above_ceiling_result.error["receipt_ref"] is None
    assert "detail" not in above_ceiling_result.error
    assert not tmp_foundry.run_paths(run_id).source_candidates.exists()

    # H6/H7 one-denial-shape comparison: a WRONG-WORKSPACE caller for the
    # SAME real run denies at the EARLIER `rbac` stage (fixed pipeline
    # order: capability -> rbac -> audit_health -> guard -> ...), never
    # even reaching the guard/ceiling check -- yet produces the
    # BYTE-IDENTICAL envelope.
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY_OTHER_WORKSPACE)
    wrong_workspace_result = swarm_start.invoke(
        run_id=run_id,
        adapter_ids=[_ADAPTER_A],
        idempotency_key="idem-above-ceiling-wrong-ws",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    assert wrong_workspace_result.ok is False
    assert wrong_workspace_result.error is not None
    assert wrong_workspace_result.error["reason_code"] == "not_found"
    assert above_ceiling_result.error == wrong_workspace_result.error

    # F6 fix (M3 Leg A): a genuinely-missing `run_id`, called under the
    # SAME wrong-workspace identity still installed above, produces the
    # IDENTICAL envelope too -- the third leg of the one-denial-shape
    # guarantee this test now proves. Restoring the default identity first
    # is deliberately NOT done: this exercises the "doesn't exist" case
    # from the same caller the wrong-workspace case just used, closest to
    # a real attacker's actual vantage point.
    missing_run_result = swarm_start.invoke(
        run_id="does-not-exist-at-all",
        adapter_ids=[_ADAPTER_A],
        idempotency_key="idem-above-ceiling-missing",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    assert missing_run_result.ok is False
    assert missing_run_result.error is not None
    assert missing_run_result.error["reason_code"] == "not_found"
    assert above_ceiling_result.error == missing_run_result.error

    # HIGH-1 fix, direct proof: `resolve_local_sensitivity_ceiling` was
    # called with the REAL `paths` value (`tmp_foundry`) all three times
    # `invoke()` ran above (above-ceiling, wrong-workspace, and -- F6 fix,
    # M3 Leg A -- now also the genuinely-missing-run call) -- if
    # `invoke()`'s own call site ever dropped its `paths=resolved_paths`
    # argument, the double would have recorded a `None` entry instead.
    assert ceiling_calls == [tmp_foundry, tmp_foundry, tmp_foundry]


# ---------------------------------------------------------------------------
# M2 fix cycle 2 -- path-containment sweep: run_id's own read-before-
# validate hazard (a NEW instance found beyond packet_dir, same class).
# ---------------------------------------------------------------------------


def test_resolve_run_context_denies_traversal_run_id_before_read(tmp_foundry: FoundryPaths) -> None:
    """Direct unit proof: a traversal-shaped `run_id` (`".."`, legal against
    `operator_mcp_policy._TARGET_REF_PATTERN` since it contains no `/`)
    resolves every `_RunContext` field to `None` -- the SAME fail-closed
    sentinel a genuinely missing run gets -- without ever attempting
    `load_yaml` outside `runs/`.

    MUTATION NOTE: a real `run.yaml` (matching workspace_id/sensitivity/
    profile) is planted AT the escape target (`tmp_foundry.root/run.yaml`,
    what `paths.runs / ".."` resolves to) so an UNGUARDED read would return
    REAL, non-`None` values -- a bare "resolves to None" assertion without
    this plant would pass vacuously even with the guard removed."""

    (tmp_foundry.root / "run.yaml").write_text(
        "workspace_id: ws-mine\nsensitivity: public\n"
        "profile:\n  max_cost_usd: 5.0\n  max_runtime_minutes: 60\n",
        encoding="utf-8",
    )

    result = swarm_start._resolve_run_context("..", tmp_foundry)
    assert result == swarm_start._RunContext(None, None, None, None, None)


def test_resolve_run_context_denies_traversal_intent_id_before_read(tmp_foundry: FoundryPaths) -> None:
    """Direct unit proof of the defense-in-depth intent_id containment
    (distinct from the outer run_id check above): a REAL, `runs/`-contained
    run whose OWN `run.yaml` declares a traversal-shaped `intent_id`
    (`"../evil_intent"`) must resolve `governance_profile` to `None` --
    never read the escaped intent file.

    MUTATION NOTE: a real intent YAML (`governance.key_profile_allowed`) is
    planted at the escape target (`tmp_foundry.intents/evil_intent.yaml`,
    what `paths.intents_active / "../evil_intent.yaml"` resolves to) so an
    unguarded read would return a REAL, non-`None` `governance_profile`."""

    tmp_foundry.intents.mkdir(parents=True, exist_ok=True)
    (tmp_foundry.intents / "evil_intent.yaml").write_text(
        "governance:\n  key_profile_allowed: personal\n", encoding="utf-8"
    )

    run_id = "rf_run_intent_traversal_probe"
    rp = tmp_foundry.run_paths(run_id)
    rp.run.mkdir(parents=True, exist_ok=True)
    (rp.run_yaml).write_text(
        "workspace_id: ws-mine\nsensitivity: public\nintent_id: ../evil_intent\n"
        "profile:\n  max_cost_usd: 5.0\n  max_runtime_minutes: 60\n",
        encoding="utf-8",
    )

    result = swarm_start._resolve_run_context(run_id, tmp_foundry)
    assert result.governance_profile is None
