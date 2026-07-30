"""Unit tests for :mod:`research_foundry.services.operator_cancel_resume_service`
(research-foundry-operator-mcp-v1 P2, OPM-2.4 -- cancel and resume state
machine).

Covers the H3 ten-scenario matrix
(`docs/project_plans/human-briefs/research-foundry-operator-mcp.md` §H3,
lines 74-83) verbatim. Scenarios 1/3/4 are OPM-2.1's own (DUR-1's CAS);
8's write-time half is OPM-2.3's own duplicate/mismatched write-time
guards -- this module owns 5, 6, 7, 9, 10, extending 8 to the RESUME path,
and wiring 2 end-to-end.

Scenario -> test mapping
-------------------------------------------------------------------------
1  exact retry before execution returns the same operation
   -> already proven by OPM-2.1's
      `test_operator_operation_service.
      test_same_confirmation_presented_twice_is_exact_replay_of_same_operation`
      and `..._fresh_confirmation_same_idempotency_key_and_digest_is_exact_replay`.
2  exact retry after completion returns the same terminal receipt
   -> `test_scenario2_exact_retry_after_completion_returns_same_terminal_receipt_end_to_end`
      (THIS file -- wires OPM-2.1's exact-replay outcome through
      `run_or_replay` end-to-end, proving zero re-execution).
3  same idempotency key with changed payload/target/policy denies
   -> already proven by OPM-2.1's
      `test_changed_manifest_same_idempotency_key_is_idempotency_conflict`.
4  expired, replayed, wrong-actor, or wrong-workspace token causes zero
   effects
   -> already proven by OPM-2.1's
      `test_expired_confirmation_denies_with_zero_manifest`,
      `test_wrong_workspace_operation_lookup_indistinguishable_from_missing`,
      and `test_operator_mcp_policy.
      test_verify_confirmation_mismatched_bound_field_denies` (parametrized
      over every bound field, including `actor.user_id`).
5  cancel before first action produces a canceled receipt with zero effects
   -> `test_scenario5_cancel_before_first_action_produces_canceled_receipt_with_zero_effects`
6  cancel during a multi-action operation stops at the next safe point
   -> `test_scenario6_cancel_during_multi_action_operation_stops_at_next_safe_point`
7  process loss after an effect receipt but before checkpoint resumes
   without replay
   -> `test_scenario7_process_loss_after_effect_receipt_before_checkpoint_resumes_without_replay`
8  truncated, extra, duplicate, reordered, or mismatched effect receipts
   deny resume (extended from OPM-2.3's write-time-only coverage)
   -> `test_scenario8_extended_corrupt_receipt_state_denies_resolve_resume_point`
      and `test_scenario8_extended_corrupt_receipt_state_denies_resume_operation`
9  policy/sensitivity change before resume requires fresh preflight and
   confirmation
   -> `test_scenario9_policy_change_before_resume_denies_via_fresh_authorization`
      and (U7, the negative case: presenting the ORIGINAL/stale
      confirmation itself must deny, not merely "a fresh one works")
      `test_scenario9_original_now_consumed_confirmation_cannot_resume`
10 non-cancelable atomic publication completes or fails without a partial
   artifact
   -> `test_scenario10_non_cancelable_atomic_publication_completes_before_cancellation_is_observed`
      and `test_scenario10_non_cancelable_action_failure_leaves_no_partial_artifact`

Plus the hard "converges with uninterrupted effects" requirement:
`test_uninterrupted_and_resumed_operations_converge_to_identical_effects_and_terminal_receipt`
runs one operation straight through and an equivalent one interrupted-then-
resumed, and asserts the canonical effects (effect_kind/effect_ref pairs,
order-preserved) and the terminal receipt (modulo the two fields that MUST
differ between any two distinct operations: `operation_id` and the
content-addressed `effect_receipt_refs` digests, which embed
`operation_id` -- `effect_digest` is a GLOBAL primary key across every
operation in `effect_receipts`, so two operations can never share one) are
IDENTICAL.

Proof requirement -- every test mutates against REAL sqlite persistence
(`tmp_foundry`, never a fake/monkeypatched store); process loss (scenario
7) is simulated by durably writing the pre-loss receipts via one service
instance, then resolving/resuming via a BRAND-NEW `OperatorReceiptService`/
`OperatorCancelResumeService` instance backed by the same files -- nothing
survives via an in-process object.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

import pytest

from research_foundry import ids
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services.operator_attempt_adapter import OperatorAttemptAdapter
from research_foundry.services.operator_cancel_resume_service import (
    ActionEffect,
    ActionSpec,
    OperatorCancelResumeService,
)
from research_foundry.services.operator_operation_service import OperatorOperationService
from research_foundry.services.operator_receipt_service import OperatorReceiptService, ReceiptOutcome

# Reuse, never reinvent (per this task's instructions and the project's own
# convention -- see `test_operator_operation_service.py`'s own docstring):
# the policy test module's identity fixtures/helpers, and OPM-2.1's own
# confirmation-lifecycle test helpers.
from tests.unit.test_operator_mcp_policy import (  # noqa: F401
    _IDENTITY,
    _IDENTITY_OTHER_WORKSPACE,
    _VIEWER_IDENTITY,
    _basic_ctx,
    _default_operator_identity,
    _run_targets,
)
from tests.unit.test_operator_operation_service import (
    _authorize,
    _load_confirmation_record,
    _mint_and_record,
    _raw_connect,
)

_MINIMAL_POLICY_SNAPSHOT = {"allowed_tools": ["search"], "data_scopes": []}


def _sha(tag: str) -> str:
    return hashlib.sha256(tag.encode("utf-8")).hexdigest()


def _consume(paths: FoundryPaths, op_service: OperatorOperationService, ctx: policy.PolicyContext):
    """Mint + record + authorize + consume in one call -- the full P1/OPM-2.1
    entry surface a real caller goes through, never a shortcut that
    fabricates an operation directly."""

    confirmation_id, token, record = _mint_and_record(op_service, ctx)
    authorization = _authorize(paths, ctx, confirmation_record=record, presented_token=token)
    return op_service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=authorization,
    )


def _action(action_id: str, executed: list[str]) -> ActionSpec:
    """A trivial action that records its own execution and produces a
    deterministic effect -- the shared building block for the scenarios
    that don't care about the effect's own content, only whether/when the
    action ran."""

    def _run() -> ActionEffect:
        executed.append(action_id)
        return ActionEffect(
            effect_kind="source_card_created",
            effect_digest=_sha(f"{action_id}-effect"),
            effect_ref=f"source_card:{action_id}",
        )

    return ActionSpec(action_id=action_id, run=_run)


def _canonical_effects(paths: FoundryPaths, operation_id: str) -> list[tuple[str, str]]:
    """The (effect_kind, effect_ref) pairs persisted for `operation_id`, in
    insertion order -- the CANONICAL, operation-id-independent content of
    its effects (excludes `effect_digest`, which is content-addressed
    against `operation_id` and therefore CANNOT be identical across two
    distinct operations -- see this file's module docstring)."""

    conn = _raw_connect(paths)
    try:
        rows = conn.execute(
            "SELECT effect_kind, effect_ref FROM effect_receipts"
            " WHERE operation_id = ? ORDER BY rowid",
            (operation_id,),
        ).fetchall()
    finally:
        conn.close()
    return [(row["effect_kind"], row["effect_ref"]) for row in rows]


# ---------------------------------------------------------------------------
# Scenario 5: cancel before first action -> canceled receipt, zero effects.
# ---------------------------------------------------------------------------


def test_scenario5_cancel_before_first_action_produces_canceled_receipt_with_zero_effects(
    tmp_foundry: FoundryPaths,
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    assert outcome.outcome == "created"
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    cancel = svc.request_cancellation(operation_id, workspace_id=workspace_id, requested_by="alice")
    assert cancel.outcome == "created"

    executed: list[str] = []
    actions = [_action("act-0", executed), _action("act-1", executed)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "canceled"
    assert execution.completed_action_count == 0
    assert executed == []  # zero effects: neither action ever ran

    receipt = execution.terminal_receipt
    assert receipt["kind"] == "terminal_receipt"
    assert receipt["status"] == "canceled"
    assert receipt["action_count_total"] == 0
    assert receipt["action_count_completed"] == 0
    assert receipt["effect_receipt_refs"] == []
    assert receipt["denial_reason_code"] is None


# ---------------------------------------------------------------------------
# Scenario 6: cancel during a multi-action operation stops at the next
# safe point.
# ---------------------------------------------------------------------------


def test_scenario6_cancel_during_multi_action_operation_stops_at_next_safe_point(
    tmp_foundry: FoundryPaths,
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    executed: list[str] = []

    def _run_act0() -> ActionEffect:
        executed.append("act-0")
        # A cancellation arrives WHILE act-0 is the current action (after
        # it has finished, before act-1 starts) -- exactly the "during a
        # multi-action operation" case.
        svc.request_cancellation(operation_id, workspace_id=workspace_id)
        return ActionEffect(
            effect_kind="source_card_created",
            effect_digest=_sha("act-0-effect"),
            effect_ref="source_card:act-0",
        )

    actions = [
        ActionSpec("act-0", _run_act0),
        _action("act-1", executed),
        _action("act-2", executed),
    ]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "canceled"
    assert executed == ["act-0"]  # act-1 / act-2 never ran
    assert execution.completed_action_count == 1

    receipt = execution.terminal_receipt
    assert receipt["action_count_total"] == 1
    assert receipt["action_count_completed"] == 1
    assert receipt["effect_receipt_refs"] == [_sha("act-0-effect")]


# ---------------------------------------------------------------------------
# Scenario 7: process loss after an effect receipt but before checkpoint
# resumes without replay.
# ---------------------------------------------------------------------------


def test_scenario7_process_loss_after_effect_receipt_before_checkpoint_resumes_without_replay(
    tmp_foundry: FoundryPaths,
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    # Phase 1 (pre-loss): action 0 ran for real -- its action_receipt AND
    # effect_receipt are durably committed (two separate, already-committed
    # SQLite transactions, exactly what `run_actions`'s own loop body
    # would have produced up to this point) -- but the checkpoint write
    # that would normally follow immediately after never happens. This is
    # the realistic process-loss gap: killed between those two durable
    # writes, not a simulated in-memory state.
    receipt_service.record_action_receipt(
        operation_id,
        workspace_id=workspace_id,
        action_id="act-0",
        action_index=0,
        status="completed",
        attempt_ref="attempt-precrash",
        started_at=ids.now_iso(),
        completed_at=ids.now_iso(),
    )
    receipt_service.record_effect_receipt(
        operation_id,
        workspace_id=workspace_id,
        action_id="act-0",
        effect_kind="source_card_created",
        effect_digest=_sha("act-0-effect"),
        effect_ref="source_card:act-0",
        generated_at=ids.now_iso(),
    )
    assert receipt_service.load_checkpoint(operation_id) is None  # the "loss" gap

    # Phase 2 ("restart"): brand-new service instances, same durable files
    # -- nothing survives via a Python object from phase 1.
    fresh_receipts = OperatorReceiptService(tmp_foundry)
    fresh_ops = OperatorOperationService(tmp_foundry)
    fresh_svc = OperatorCancelResumeService(tmp_foundry, operations=fresh_ops, receipts=fresh_receipts)

    resume_point = fresh_receipts.resolve_resume_point(operation_id)
    assert resume_point.outcome == "ok"
    assert resume_point.next_action_index == 1  # reconstructed from real rows, not checkpoint

    def _act0_must_not_run() -> ActionEffect | None:  # pragma: no cover - only fails the test
        raise AssertionError("action 0 must not be re-executed on resume (scenario 7)")

    executed: list[str] = []
    actions = [
        ActionSpec("act-0", _act0_must_not_run),
        _action("act-1", executed),
        _action("act-2", executed),
    ]

    execution = fresh_svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-postcrash",
        start_index=resume_point.next_action_index,
    )

    assert execution.status == "completed"
    assert executed == ["act-1", "act-2"]  # act-0 never replayed
    receipt = execution.terminal_receipt
    assert receipt["action_count_total"] == 3
    assert receipt["action_count_completed"] == 3
    assert len(receipt["effect_receipt_refs"]) == 3


# ---------------------------------------------------------------------------
# Scenario 8, extended to resume: corrupt receipt state denies resume.
# ---------------------------------------------------------------------------


def test_scenario8_extended_corrupt_receipt_state_denies_resolve_resume_point(
    tmp_foundry: FoundryPaths,
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    receipt_service.record_action_receipt(
        operation_id,
        workspace_id=workspace_id,
        action_id="act-0",
        action_index=0,
        status="completed",
        attempt_ref="attempt-x",
        started_at=ids.now_iso(),
        completed_at=ids.now_iso(),
    )
    # Directly corrupt persisted state via raw SQL: insert index 2,
    # skipping index 1. `record_action_receipt` NOW refuses this gap at
    # write time (U5/REGATE-BLOCK-3) -- this raw-SQL insert deliberately
    # bypasses that governed guard entirely (real, already-committed
    # persistence, never a fake) so this test can isolate
    # `resolve_resume_point`'s OWN reconciliation defense-in-depth against
    # a state that reached the table by some OTHER means (e.g. a future
    # bug, a direct DB access, a schema-compatible sibling writer).
    conn = _raw_connect(tmp_foundry)
    try:
        conn.execute(
            "INSERT INTO action_receipts"
            " (operation_id, action_id, action_index, status, attempt_ref,"
            "  started_at, completed_at, reason_code, retryable, receipt_json, created_at)"
            " VALUES (?, 'act-2', 2, 'completed', 'attempt-x', ?, ?, NULL, NULL, '{}', ?)",
            (operation_id, ids.now_iso(), ids.now_iso(), ids.now_iso()),
        )
        conn.commit()
    finally:
        conn.close()

    resume_point = receipt_service.resolve_resume_point(operation_id)
    assert resume_point.outcome == "denied"
    assert resume_point.reason_code == "internal_error"
    assert resume_point.next_action_index is None


def test_scenario8_extended_corrupt_receipt_state_denies_resume_operation(
    tmp_foundry: FoundryPaths,
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    receipt_service.record_action_receipt(
        operation_id,
        workspace_id=workspace_id,
        action_id="act-0",
        action_index=0,
        status="completed",
        attempt_ref="attempt-x",
        started_at=ids.now_iso(),
        completed_at=ids.now_iso(),
    )
    # Raw-SQL bypass of the write-time contiguity guard -- see
    # `test_scenario8_extended_corrupt_receipt_state_denies_resolve_resume_point`
    # above for why this is now necessary post-U5.
    conn = _raw_connect(tmp_foundry)
    try:
        conn.execute(
            "INSERT INTO action_receipts"
            " (operation_id, action_id, action_index, status, attempt_ref,"
            "  started_at, completed_at, reason_code, retryable, receipt_json, created_at)"
            " VALUES (?, 'act-2', 2, 'completed', 'attempt-x', ?, ?, NULL, NULL, '{}', ?)",
            (operation_id, ids.now_iso(), ids.now_iso(), ids.now_iso()),
        )
        conn.commit()
    finally:
        conn.close()

    resume_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="job.resume",
        idempotency_key="resume-corrupt",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("agent_job", operation_id),),
        resolved_target_workspaces=(_IDENTITY.workspace_id,),
    )
    resume_confirmation_id, resume_token, record = _mint_and_record(op_service, resume_ctx)
    resume_authorization = _authorize(
        tmp_foundry, resume_ctx, confirmation_record=record, presented_token=resume_token
    )
    assert resume_authorization.decision.allowed

    resume_outcome = svc.resume_operation(
        operation_id,
        identity=_IDENTITY,
        resume_ctx=resume_ctx,
        resume_confirmation_id=resume_confirmation_id,
        resume_presented_token=resume_token,
        resume_authorization=resume_authorization,
        actions=[_action("act-0", []), _action("act-1", []), _action("act-2", [])],
        operation_kind=ctx.operation_kind,
        workspace_id=workspace_id,
        attempt_adapter=attempt_adapter,
        attempt_provider="claude_agent_sdk",
        attempt_model_profile="rf_synthesize_deep",
        attempt_request_kind="research",
        attempt_policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
    )

    assert resume_outcome.outcome == "denied"
    assert resume_outcome.reason_code == "internal_error"
    assert resume_outcome.new_attempt is None

    # Zero effects from the denied resume itself: no new attempt was ever
    # linked to this operation.
    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM attempts WHERE operation_id = ?", (operation_id,)
        ).fetchone()[0]
        assert count == 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Scenario 9: policy/sensitivity change before resume requires fresh
# preflight and confirmation.
# ---------------------------------------------------------------------------


def test_scenario9_policy_change_before_resume_denies_via_fresh_authorization(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)

    # Original operation authorized under the OWNER identity.
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    # Policy/role changed since then: the operator's configured identity is
    # now VIEWER -- RBAC no longer grants `job.resume` (`_AGENT_JOB_ROLES`
    # is owner/admin only). This is scenario 9's "policy/sensitivity
    # change before resume" -- resume's OWN fresh authorization pass must
    # observe it, never the ORIGINAL operation's now-stale authorization.
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _VIEWER_IDENTITY)
    resume_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="job.resume",
        idempotency_key="resume-policy-change",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("agent_job", operation_id),),
        resolved_target_workspaces=(_VIEWER_IDENTITY.workspace_id,),
    )
    resume_confirmation_id, resume_token, record = _mint_and_record(op_service, resume_ctx)
    resume_authorization = _authorize(
        tmp_foundry, resume_ctx, confirmation_record=record, presented_token=resume_token
    )
    assert resume_authorization.decision.denied
    assert resume_authorization.decision.stage == "rbac"
    assert resume_authorization.decision.reason_code == "rbac_denied"

    resume_outcome = svc.resume_operation(
        operation_id,
        identity=_VIEWER_IDENTITY,
        resume_ctx=resume_ctx,
        resume_confirmation_id=resume_confirmation_id,
        resume_presented_token=resume_token,
        resume_authorization=resume_authorization,
        actions=[_action("act-0", [])],
        operation_kind=ctx.operation_kind,
        workspace_id=workspace_id,
        attempt_adapter=attempt_adapter,
        attempt_provider="claude_agent_sdk",
        attempt_model_profile="rf_synthesize_deep",
        attempt_request_kind="research",
        attempt_policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
    )

    assert resume_outcome.outcome == "denied"
    assert resume_outcome.reason_code == "rbac_denied"
    assert resume_outcome.new_attempt is None

    conn = _raw_connect(tmp_foundry)
    try:
        attempt_count = conn.execute(
            "SELECT COUNT(*) FROM attempts WHERE operation_id = ?", (operation_id,)
        ).fetchone()[0]
        action_count = conn.execute(
            "SELECT COUNT(*) FROM action_receipts WHERE operation_id = ?", (operation_id,)
        ).fetchone()[0]
        assert attempt_count == 0
        assert action_count == 0
    finally:
        conn.close()


def test_scenario9_original_now_consumed_confirmation_cannot_resume(
    tmp_foundry: FoundryPaths,
) -> None:
    """U7 (H3 scenario 9's negative case): "resume requires a FRESH
    confirmation" was, before this test, a property of every OTHER test's
    HARNESS (each one deliberately mints a brand-new confirmation before
    calling `resume_operation`) rather than a property the SERVICE itself
    was ever shown to enforce. This test presents the ORIGINAL operation's
    OWN, now-CONSUMED `confirmation_id`/token back to `resume_operation`
    -- DUR-1's own one-time-consumption CAS
    (`OperatorOperationService.consume_and_create_operation`) must refuse
    it, so resume denies rather than reusing stale authority.
    """

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)

    ctx = _basic_ctx(targets=_run_targets())
    original_confirmation_id, original_token, original_record = _mint_and_record(op_service, ctx)
    original_authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=original_record, presented_token=original_token
    )
    assert original_authorization.decision.allowed

    created = op_service.consume_and_create_operation(
        confirmation_id=original_confirmation_id,
        presented_token=original_token,
        ctx=ctx,
        authorization=original_authorization,
    )
    assert created.outcome == "created"
    operation_id = created.operation.operation_id
    workspace_id = created.operation.workspace_id

    # Read back the CURRENT (now "consumed") confirmation record -- what a
    # real caller re-presenting a stale confirmation would have to work
    # with, never the stale in-memory `original_record` from before
    # consumption.
    consumed_record = _load_confirmation_record(tmp_foundry, original_confirmation_id)

    resume_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="job.resume",
        idempotency_key="resume-stale-confirmation",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("agent_job", operation_id),),
        resolved_target_workspaces=(_IDENTITY.workspace_id,),
    )
    stale_authorization = _authorize(
        tmp_foundry, resume_ctx, confirmation_record=consumed_record, presented_token=original_token
    )

    resume_outcome = svc.resume_operation(
        operation_id,
        identity=_IDENTITY,
        resume_ctx=resume_ctx,
        resume_confirmation_id=original_confirmation_id,
        resume_presented_token=original_token,
        resume_authorization=stale_authorization,
        actions=[_action("act-0", [])],
        operation_kind=ctx.operation_kind,
        workspace_id=workspace_id,
        attempt_adapter=attempt_adapter,
        attempt_provider="claude_agent_sdk",
        attempt_model_profile="rf_synthesize_deep",
        attempt_request_kind="research",
        attempt_policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
    )

    assert resume_outcome.outcome == "denied"
    assert resume_outcome.new_attempt is None
    assert resume_outcome.execution is None

    # Zero effect: no NEW attempt was ever minted, and the original
    # operation's own action ledger is untouched -- the stale confirmation
    # bought the caller nothing.
    conn = _raw_connect(tmp_foundry)
    try:
        attempt_count = conn.execute(
            "SELECT COUNT(*) FROM attempts WHERE operation_id = ?", (operation_id,)
        ).fetchone()[0]
        action_count = conn.execute(
            "SELECT COUNT(*) FROM action_receipts WHERE operation_id = ?", (operation_id,)
        ).fetchone()[0]
        assert attempt_count == 0
        assert action_count == 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# R1: authorization must be bound to the operation being resumed, not
# merely self-consistent. Reproduces a defect found in a fail-open/
# layer-below sweep of `resume_operation` -- see the module-level hardening
# block above `OperatorCancelResumeService` (`_resume_ctx_binds_operation`)
# for the fix. Each test below asserts the FAILING-then-PASSING shape
# directly (assert the correct outcome against the FIXED code) plus a
# revert-detection mutation further down proves each guard actually does
# something (see `test_r1_r2_r3_revert_detection_*` at the end of this
# section).
# ---------------------------------------------------------------------------


def test_r1_valid_low_sensitivity_resume_authorization_denied_against_higher_sensitivity_operation(
    tmp_foundry: FoundryPaths,
) -> None:
    """The exact scenario from the defect report: a caller mints and fully
    clears a FRESH `job.resume` confirmation for a LOW-sensitivity
    `resume_ctx` that targets some OTHER, benign `agent_job` -- every prior
    policy stage (capability/RBAC/audit-health/guard/preflight/
    confirmation-CAS) legitimately passes FOR THAT CONTEXT. The caller then
    presents that same, fully-authorized `resume_ctx` against `operation_id`
    -- a DIFFERENT, HIGHER-sensitivity operation in the SAME workspace, real,
    a real target the low-sensitivity confirmation never actually named.

    Before the fix: `resume_operation` proceeds -- `consume_and_create_
    operation` only validates `resume_ctx` against itself, and the (then-
    discarded) `load_operation` call only proves workspace equality (which
    holds); nothing compares `resume_ctx.effective_sensitivity`/`targets`
    to the real operation's manifest. After the fix
    (`_resume_ctx_binds_operation`), this is denied `"not_found"` before
    any attempt is minted or any receipt touched."""

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)

    # The VICTIM operation: HIGHER sensitivity, same workspace as the
    # low-sensitivity resume_ctx minted below.
    victim_ctx = _basic_ctx(
        targets=_run_targets(),
        effective_sensitivity="client_sensitive",
        idempotency_key="victim-op",
    )
    victim_outcome = _consume(tmp_foundry, op_service, victim_ctx)
    assert victim_outcome.outcome == "created"
    operation_id = victim_outcome.operation.operation_id
    workspace_id = victim_outcome.operation.workspace_id

    # A fully valid, FRESH `job.resume` confirmation for a LOW-sensitivity
    # context that targets some OTHER, benign job -- never `operation_id`.
    resume_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="job.resume",
        idempotency_key="low-sensitivity-resume",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("agent_job", "aj_benign_low_sensitivity_job"),),
        resolved_target_workspaces=(_IDENTITY.workspace_id,),
    )
    resume_confirmation_id, resume_token, record = _mint_and_record(op_service, resume_ctx)
    resume_authorization = _authorize(
        tmp_foundry, resume_ctx, confirmation_record=record, presented_token=resume_token
    )
    # Every prior policy stage legitimately clears FOR THIS CONTEXT -- the
    # bug is not that authorization is broken, it's that nothing binds it
    # to the operation actually being resumed.
    assert resume_authorization.decision.allowed

    resume_outcome = svc.resume_operation(
        operation_id,
        identity=_IDENTITY,
        resume_ctx=resume_ctx,
        resume_confirmation_id=resume_confirmation_id,
        resume_presented_token=resume_token,
        resume_authorization=resume_authorization,
        actions=[_action("act-0", [])],
        operation_kind=victim_ctx.operation_kind,
        workspace_id=workspace_id,
        attempt_adapter=attempt_adapter,
        attempt_provider="claude_agent_sdk",
        attempt_model_profile="rf_synthesize_deep",
        attempt_request_kind="research",
        attempt_policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
    )

    assert resume_outcome.outcome == "denied"
    assert resume_outcome.reason_code == "not_found"
    assert resume_outcome.new_attempt is None
    assert resume_outcome.execution is None

    # Zero effects from the denied resume: no new attempt, no action
    # receipt against the victim operation.
    conn = _raw_connect(tmp_foundry)
    try:
        attempt_count = conn.execute(
            "SELECT COUNT(*) FROM attempts WHERE operation_id = ?", (operation_id,)
        ).fetchone()[0]
        action_count = conn.execute(
            "SELECT COUNT(*) FROM action_receipts WHERE operation_id = ?", (operation_id,)
        ).fetchone()[0]
        assert attempt_count == 0
        assert action_count == 0
    finally:
        conn.close()


def test_r1_resume_ctx_targeting_a_different_operation_id_in_the_same_workspace_is_denied(
    tmp_foundry: FoundryPaths,
) -> None:
    """A narrower repro of the same R1 gap, isolating the TARGET half of
    the binding check from the sensitivity half: `resume_ctx` has the SAME
    (not weaker) sensitivity as the victim operation, but its target is a
    different, real `agent_job` id -- never `operation_id`. Must still
    deny."""

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)

    victim_ctx = _basic_ctx(targets=_run_targets(), idempotency_key="victim-op-2")
    victim_outcome = _consume(tmp_foundry, op_service, victim_ctx)
    operation_id = victim_outcome.operation.operation_id
    workspace_id = victim_outcome.operation.workspace_id

    other_ctx = _basic_ctx(targets=_run_targets(), idempotency_key="other-op-2")
    other_outcome = _consume(tmp_foundry, op_service, other_ctx)
    other_operation_id = other_outcome.operation.operation_id

    resume_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="job.resume",
        idempotency_key="wrong-target-resume",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("agent_job", other_operation_id),),
        resolved_target_workspaces=(_IDENTITY.workspace_id,),
    )
    resume_confirmation_id, resume_token, record = _mint_and_record(op_service, resume_ctx)
    resume_authorization = _authorize(
        tmp_foundry, resume_ctx, confirmation_record=record, presented_token=resume_token
    )
    assert resume_authorization.decision.allowed

    resume_outcome = svc.resume_operation(
        operation_id,
        identity=_IDENTITY,
        resume_ctx=resume_ctx,
        resume_confirmation_id=resume_confirmation_id,
        resume_presented_token=resume_token,
        resume_authorization=resume_authorization,
        actions=[_action("act-0", [])],
        operation_kind=victim_ctx.operation_kind,
        workspace_id=workspace_id,
        attempt_adapter=attempt_adapter,
        attempt_provider="claude_agent_sdk",
        attempt_model_profile="rf_synthesize_deep",
        attempt_request_kind="research",
        attempt_policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
    )

    assert resume_outcome.outcome == "denied"
    assert resume_outcome.reason_code == "not_found"
    assert resume_outcome.new_attempt is None


def test_r1_resume_ctx_with_equal_or_stricter_sensitivity_and_correct_target_still_resumes(
    tmp_foundry: FoundryPaths,
) -> None:
    """R1 must not be OVER-strict: a `resume_ctx` that correctly targets
    `operation_id` and is evaluated at an EQUAL (or stricter) sensitivity
    than the operation's real, persisted sensitivity is legitimate and must
    still resume -- this is the normal, intended path every other test in
    this file already exercises (H3 scenario 9's own "fresh policy
    evaluation" guarantee), and this test pins it against a REGRESSION from
    the R1 fix itself."""

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)

    ctx = _basic_ctx(
        targets=_run_targets(), effective_sensitivity="personal", idempotency_key="stricter-op"
    )
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    # STRICTER than the operation's real "personal" -- legitimate: policy
    # now ranks it more sensitive than it was at creation.
    resume_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="job.resume",
        idempotency_key="stricter-resume",
        effective_sensitivity="work_sensitive",
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("agent_job", operation_id),),
        resolved_target_workspaces=(_IDENTITY.workspace_id,),
    )
    resume_confirmation_id, resume_token, record = _mint_and_record(op_service, resume_ctx)
    resume_authorization = _authorize(
        tmp_foundry, resume_ctx, confirmation_record=record, presented_token=resume_token
    )
    assert resume_authorization.decision.allowed

    resume_outcome = svc.resume_operation(
        operation_id,
        identity=_IDENTITY,
        resume_ctx=resume_ctx,
        resume_confirmation_id=resume_confirmation_id,
        resume_presented_token=resume_token,
        resume_authorization=resume_authorization,
        actions=[_action("act-0", [])],
        operation_kind=ctx.operation_kind,
        workspace_id=workspace_id,
        attempt_adapter=attempt_adapter,
        attempt_provider="claude_agent_sdk",
        attempt_model_profile="rf_synthesize_deep",
        attempt_request_kind="research",
        attempt_policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
    )

    assert resume_outcome.outcome == "resumed"
    assert resume_outcome.new_attempt is not None
    assert resume_outcome.execution is not None
    assert resume_outcome.execution.status == "completed"


def test_r1_correct_target_but_weaker_sensitivity_is_denied(tmp_foundry: FoundryPaths) -> None:
    """Isolates the SENSITIVITY half of `_resume_ctx_binds_operation` from
    the TARGET half: `resume_ctx` correctly targets `operation_id` (the
    target guard alone would pass this), but its `effective_sensitivity` is
    WEAKER than the operation's real, persisted sensitivity. Must still
    deny -- a revert of ONLY the sensitivity comparison (with the target
    comparison left intact) would let this one through, since the target
    matches; this test exists specifically to catch that regression, which
    `test_r1_resume_ctx_targeting_a_different_operation_id_in_the_same_
    workspace_is_denied` (wrong target, same sensitivity) and
    `test_r1_valid_low_sensitivity_resume_authorization_denied_against_
    higher_sensitivity_operation` (wrong target AND weaker sensitivity,
    conflated) do not."""

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)

    victim_ctx = _basic_ctx(
        targets=_run_targets(),
        effective_sensitivity="client_sensitive",
        idempotency_key="victim-op-3",
    )
    victim_outcome = _consume(tmp_foundry, op_service, victim_ctx)
    operation_id = victim_outcome.operation.operation_id
    workspace_id = victim_outcome.operation.workspace_id

    # Correct target (operation_id itself), but WEAKER sensitivity than the
    # victim operation's real "client_sensitive".
    resume_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="job.resume",
        idempotency_key="weaker-sensitivity-resume",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("agent_job", operation_id),),
        resolved_target_workspaces=(_IDENTITY.workspace_id,),
    )
    resume_confirmation_id, resume_token, record = _mint_and_record(op_service, resume_ctx)
    resume_authorization = _authorize(
        tmp_foundry, resume_ctx, confirmation_record=record, presented_token=resume_token
    )
    assert resume_authorization.decision.allowed

    resume_outcome = svc.resume_operation(
        operation_id,
        identity=_IDENTITY,
        resume_ctx=resume_ctx,
        resume_confirmation_id=resume_confirmation_id,
        resume_presented_token=resume_token,
        resume_authorization=resume_authorization,
        actions=[_action("act-0", [])],
        operation_kind=victim_ctx.operation_kind,
        workspace_id=workspace_id,
        attempt_adapter=attempt_adapter,
        attempt_provider="claude_agent_sdk",
        attempt_model_profile="rf_synthesize_deep",
        attempt_request_kind="research",
        attempt_policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
    )

    assert resume_outcome.outcome == "denied"
    assert resume_outcome.reason_code == "not_found"
    assert resume_outcome.new_attempt is None


# ---------------------------------------------------------------------------
# R2: `workspace_id` must be derived from the operation's real manifest,
# never trusted from the caller parameter -- it backs the workspace-scoped
# `idx_checkpoints_workspace`/`idx_terminal_receipts_workspace` indexes.
# ---------------------------------------------------------------------------


def test_r2_mismatched_caller_workspace_id_never_reaches_checkpoint_or_terminal_receipt(
    tmp_foundry: FoundryPaths,
) -> None:
    """A `resume_ctx` that correctly binds to `operation_id` (R1 passes),
    but the CALLER supplies a `workspace_id` parameter that disagrees with
    the operation's real, persisted workspace. `identity` is correctly
    scoped (same workspace as the real operation) so `load_operation`
    itself does not raise -- isolating R2 from R1.

    Before the fix: `write_checkpoint`/`finalize_terminal_receipt` persist
    rows with the WRONG (caller-supplied) `workspace_id`, denormalized
    into `idx_checkpoints_workspace`/`idx_terminal_receipts_workspace`.
    After the fix, both rows carry the operation's REAL workspace_id
    (`operation_record.workspace_id`) regardless of what the caller passed."""

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)

    ctx = _basic_ctx(targets=_run_targets(), idempotency_key="r2-real-op")
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    real_workspace_id = outcome.operation.workspace_id
    assert real_workspace_id == _IDENTITY.workspace_id

    resume_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="job.resume",
        idempotency_key="r2-resume",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("agent_job", operation_id),),
        resolved_target_workspaces=(_IDENTITY.workspace_id,),
    )
    resume_confirmation_id, resume_token, record = _mint_and_record(op_service, resume_ctx)
    resume_authorization = _authorize(
        tmp_foundry, resume_ctx, confirmation_record=record, presented_token=resume_token
    )
    assert resume_authorization.decision.allowed

    wrong_workspace_id = _IDENTITY_OTHER_WORKSPACE.workspace_id
    assert wrong_workspace_id != real_workspace_id

    resume_outcome = svc.resume_operation(
        operation_id,
        identity=_IDENTITY,
        resume_ctx=resume_ctx,
        resume_confirmation_id=resume_confirmation_id,
        resume_presented_token=resume_token,
        resume_authorization=resume_authorization,
        actions=[_action("act-0", [])],
        operation_kind=ctx.operation_kind,
        workspace_id=wrong_workspace_id,  # <-- mismatched, must be ignored
        attempt_adapter=attempt_adapter,
        attempt_provider="claude_agent_sdk",
        attempt_model_profile="rf_synthesize_deep",
        attempt_request_kind="research",
        attempt_policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
    )

    assert resume_outcome.outcome == "resumed"
    assert resume_outcome.execution is not None
    assert resume_outcome.execution.status == "completed"

    conn = _raw_connect(tmp_foundry)
    try:
        checkpoint_ws = conn.execute(
            "SELECT workspace_id FROM checkpoints WHERE operation_id = ?", (operation_id,)
        ).fetchone()[0]
        terminal_ws = conn.execute(
            "SELECT workspace_id FROM terminal_receipts WHERE operation_id = ?", (operation_id,)
        ).fetchone()[0]
        attempt_ws = conn.execute(
            "SELECT workspace_id FROM attempts WHERE operation_id = ?", (operation_id,)
        ).fetchone()[0]
    finally:
        conn.close()

    assert checkpoint_ws == real_workspace_id
    assert terminal_ws == real_workspace_id
    assert attempt_ws == real_workspace_id
    assert checkpoint_ws != wrong_workspace_id
    assert terminal_ws != wrong_workspace_id


# ---------------------------------------------------------------------------
# R3 (checklist-item-2 sibling of R2, found by enumerating this module's
# public methods): `run_or_replay` has an `operation: OperationRecord`
# parameter that ALREADY carries the authoritative workspace_id/
# operation_kind, yet threaded the separately-supplied caller parameters
# into `run_actions` instead -- the SAME unsafe behavior R2 closed in
# `resume_operation`, reachable through a second door.
# ---------------------------------------------------------------------------


def test_r3_run_or_replay_mismatched_caller_workspace_id_never_reaches_checkpoint(
    tmp_foundry: FoundryPaths,
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx = _basic_ctx(targets=_run_targets(), idempotency_key="r3-real-op")
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation = outcome.operation
    real_workspace_id = operation.workspace_id
    assert real_workspace_id == _IDENTITY.workspace_id

    wrong_workspace_id = _IDENTITY_OTHER_WORKSPACE.workspace_id
    assert wrong_workspace_id != real_workspace_id

    executed: list[str] = []
    execution = svc.run_or_replay(
        operation,
        is_replay=False,
        workspace_id=wrong_workspace_id,  # <-- mismatched, must be ignored
        operation_kind=ctx.operation_kind,
        actions=[_action("act-0", executed)],
        attempt_ref="attempt-r3",
    )

    assert execution.status == "completed"
    assert executed == ["act-0"]

    conn = _raw_connect(tmp_foundry)
    try:
        checkpoint_ws = conn.execute(
            "SELECT workspace_id FROM checkpoints WHERE operation_id = ?",
            (operation.operation_id,),
        ).fetchone()[0]
        terminal_ws = conn.execute(
            "SELECT workspace_id FROM terminal_receipts WHERE operation_id = ?",
            (operation.operation_id,),
        ).fetchone()[0]
    finally:
        conn.close()

    assert checkpoint_ws == real_workspace_id
    assert terminal_ws == real_workspace_id
    assert checkpoint_ws != wrong_workspace_id


# ---------------------------------------------------------------------------
# Scenario 10: non-cancelable atomic publication completes or fails
# without a partial artifact.
# ---------------------------------------------------------------------------


def test_scenario10_non_cancelable_atomic_publication_completes_before_cancellation_is_observed(
    tmp_foundry: FoundryPaths, tmp_path: Path
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    dest = tmp_path / "artifact.txt"
    published_content = "COMPLETE ARTIFACT CONTENT -- never partial"

    def _atomic_publish() -> ActionEffect:
        # The checkpoint must ALREADY show `non_cancelable=True` -- marked
        # BEFORE this action started, not after.
        mid_checkpoint = receipt_service.load_checkpoint(operation_id)
        assert mid_checkpoint is not None
        assert mid_checkpoint["non_cancelable"] is True

        # A cancellation request arrives WHILE this non-cancelable action
        # is in flight -- before the atomic rename below.
        svc.request_cancellation(operation_id, workspace_id=workspace_id)

        tmp = dest.with_suffix(".tmp")
        tmp.write_text(published_content, encoding="utf-8")
        os.replace(tmp, dest)  # atomic on POSIX -- readers never see a partial file
        return ActionEffect(
            effect_kind="artifact_published",
            effect_digest=_sha("publish"),
            effect_ref=f"artifact:{dest.name}",
        )

    executed: list[str] = []
    actions = [
        ActionSpec("act-publish", _atomic_publish, non_cancelable=True),
        _action("act-after", executed),
    ]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    # The non-cancelable action completed WHOLE -- the artifact exists,
    # complete, never partial.
    assert dest.exists()
    assert dest.read_text(encoding="utf-8") == published_content
    assert not dest.with_suffix(".tmp").exists()

    # But the cancellation requested DURING it was honored at the very
    # NEXT safe point.
    assert execution.status == "canceled"
    assert executed == []  # act-after never ran
    assert execution.completed_action_count == 1

    receipt = execution.terminal_receipt
    assert receipt["action_count_completed"] == 1
    assert receipt["effect_receipt_refs"] == [_sha("publish")]

    # The checkpoint's non_cancelable flag was cleared once the action
    # finished -- never left "stuck" true.
    checkpoint = receipt_service.load_checkpoint(operation_id)
    assert checkpoint["non_cancelable"] is False
    assert checkpoint["status"] == "converged"


def test_scenario10_non_cancelable_action_failure_leaves_no_partial_artifact(
    tmp_foundry: FoundryPaths, tmp_path: Path
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    dest = tmp_path / "artifact2.txt"
    call_count = 0

    def _atomic_publish_fails() -> ActionEffect:
        nonlocal call_count
        call_count += 1
        tmp = dest.with_suffix(".tmp")
        tmp.write_text("partial content that must never land at dest", encoding="utf-8")
        raise RuntimeError("simulated failure before the atomic rename")

    executed: list[str] = []
    actions = [
        ActionSpec("act-publish", _atomic_publish_fails, non_cancelable=True),
        _action("act-after", executed),
    ]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    # U8: `assert not dest.exists()` is TAUTOLOGICAL here -- this action's
    # own code never calls `os.replace(tmp, dest)` on the failure path (it
    # raises first), so `dest` can NEVER exist regardless of anything
    # `run_actions` does; the assertion cannot fail and pins nothing about
    # the SERVICE. What the service actually controls, and what this test
    # now pins instead: the failing action ran EXACTLY ONCE -- `run_actions`
    # does not silently retry a raising action on its own (retry/resume is
    # always a caller-driven decision via `start_index`, never internal).
    assert call_count == 1
    assert execution.status == "failed"
    assert executed == []  # act-after never ran

    checkpoint = receipt_service.load_checkpoint(operation_id)
    assert checkpoint["non_cancelable"] is False  # cleared even on failure
    assert checkpoint["status"] == "converged"


# ---------------------------------------------------------------------------
# Scenario 2, wired end-to-end: exact retry after completion returns the
# SAME terminal receipt, zero re-execution.
# ---------------------------------------------------------------------------


def test_scenario2_exact_retry_after_completion_returns_same_terminal_receipt_end_to_end(
    tmp_foundry: FoundryPaths,
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx = _basic_ctx(targets=_run_targets())
    confirmation_id, token, record = _mint_and_record(op_service, ctx)
    authorization = _authorize(tmp_foundry, ctx, confirmation_record=record, presented_token=token)
    first_op_outcome = op_service.consume_and_create_operation(
        confirmation_id=confirmation_id, presented_token=token, ctx=ctx, authorization=authorization
    )
    assert first_op_outcome.outcome == "created"
    operation = first_op_outcome.operation
    workspace_id = operation.workspace_id

    executed: list[str] = []
    actions = [_action("act-0", executed), _action("act-1", executed)]
    first_execution = svc.run_or_replay(
        operation,
        is_replay=False,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )
    assert first_execution.status == "completed"
    assert first_execution.replayed is False
    assert executed == ["act-0", "act-1"]

    # Exact retry: re-present the SAME (now-consumed) confirmation.
    consumed_record = _load_confirmation_record(tmp_foundry, confirmation_id)
    retry_authorization = _authorize(
        tmp_foundry, ctx, confirmation_record=consumed_record, presented_token=token
    )
    assert retry_authorization.decision.reason_code == "confirmation_replayed"
    retry_op_outcome = op_service.consume_and_create_operation(
        confirmation_id=confirmation_id,
        presented_token=token,
        ctx=ctx,
        authorization=retry_authorization,
    )
    assert retry_op_outcome.outcome == "exact_replay"
    assert retry_op_outcome.operation.operation_id == operation.operation_id

    executed.clear()
    second_execution = svc.run_or_replay(
        retry_op_outcome.operation,
        is_replay=True,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-2",
    )

    assert second_execution.replayed is True
    assert second_execution.terminal_receipt == first_execution.terminal_receipt
    assert executed == []  # zero re-execution


# ---------------------------------------------------------------------------
# The hard requirement: uninterrupted vs. interrupted-then-resumed
# operations converge to IDENTICAL canonical effects and terminal receipt.
# ---------------------------------------------------------------------------


def test_uninterrupted_and_resumed_operations_converge_to_identical_effects_and_terminal_receipt(
    tmp_foundry: FoundryPaths,
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    def _actions(executed: list[str]) -> list[ActionSpec]:
        specs = []
        for i in range(3):
            action_id = f"act-{i}"

            def _run(action_id: str = action_id) -> ActionEffect:
                executed.append(action_id)
                return ActionEffect(
                    effect_kind="source_card_created",
                    # `effect_ref` is the STABLE, operation-id-independent
                    # semantic content; `effect_digest` differs per
                    # operation only because `effect_receipts.effect_digest`
                    # is a GLOBAL primary key across every operation in the
                    # table -- two operations could never share one digest
                    # even if their content were byte-identical.
                    effect_digest=_sha(f"{action_id}-{ids.now_iso()}-{id(executed)}"),
                    effect_ref=f"source_card:{action_id}",
                )

            specs.append(ActionSpec(action_id, _run))
        return specs

    # --- Operation A: straight through, uninterrupted. ---
    ctx_a = _basic_ctx(targets=_run_targets(), idempotency_key="idem-uninterrupted")
    outcome_a = _consume(tmp_foundry, op_service, ctx_a)
    assert outcome_a.outcome == "created"
    operation_a = outcome_a.operation
    executed_a: list[str] = []
    execution_a = svc.run_actions(
        operation_a.operation_id,
        workspace_id=operation_a.workspace_id,
        operation_kind=ctx_a.operation_kind,
        actions=_actions(executed_a),
        attempt_ref="attempt-a",
    )
    assert execution_a.status == "completed"
    assert executed_a == ["act-0", "act-1", "act-2"]

    # --- Operation B: interrupted after action 0 (process loss, exactly
    # scenario 7's shape), then resumed on a FRESH service instance. ---
    ctx_b = _basic_ctx(targets=_run_targets(), idempotency_key="idem-resumed")
    outcome_b = _consume(tmp_foundry, op_service, ctx_b)
    assert outcome_b.outcome == "created"
    operation_b = outcome_b.operation
    executed_b: list[str] = []
    actions_b = _actions(executed_b)

    effect0 = actions_b[0].run()  # action 0 genuinely executes once, here
    receipt_service.record_action_receipt(
        operation_b.operation_id,
        workspace_id=operation_b.workspace_id,
        action_id=actions_b[0].action_id,
        action_index=0,
        status="completed",
        attempt_ref="attempt-b-precrash",
        started_at=ids.now_iso(),
        completed_at=ids.now_iso(),
    )
    receipt_service.record_effect_receipt(
        operation_b.operation_id,
        workspace_id=operation_b.workspace_id,
        action_id=actions_b[0].action_id,
        effect_kind=effect0.effect_kind,
        effect_digest=effect0.effect_digest,
        effect_ref=effect0.effect_ref,
        generated_at=ids.now_iso(),
    )
    # No checkpoint write -- the process-loss gap.

    fresh_receipts = OperatorReceiptService(tmp_foundry)
    fresh_ops = OperatorOperationService(tmp_foundry)
    fresh_svc = OperatorCancelResumeService(tmp_foundry, operations=fresh_ops, receipts=fresh_receipts)
    resume_point = fresh_receipts.resolve_resume_point(operation_b.operation_id)
    assert resume_point.outcome == "ok"
    assert resume_point.next_action_index == 1

    execution_b = fresh_svc.run_actions(
        operation_b.operation_id,
        workspace_id=operation_b.workspace_id,
        operation_kind=ctx_b.operation_kind,
        actions=actions_b,
        attempt_ref="attempt-b-resume",
        start_index=resume_point.next_action_index,
    )
    assert execution_b.status == "completed"
    # act-0 appears exactly once (the direct call above) -- never replayed
    # by `run_actions` itself.
    assert executed_b == ["act-0", "act-1", "act-2"]

    # --- Convergence: canonical effects and terminal receipt identical. ---
    effects_a = _canonical_effects(tmp_foundry, operation_a.operation_id)
    effects_b = _canonical_effects(tmp_foundry, operation_b.operation_id)
    assert effects_a == effects_b
    assert len(effects_a) == 3

    def _normalize_terminal(receipt: dict) -> dict:
        d = dict(receipt)
        for key in ("operation_id", "effect_receipt_refs"):
            d.pop(key, None)
        # `audit_delivery.audit_event_id` is a freshly minted UUID per
        # call (`audit_service.record_event`'s own contract) -- never
        # expected to match across two independently finalized
        # operations. `status` (`delivered`/`degraded`/`unavailable`) IS
        # part of the canonical, comparable disposition.
        audit_delivery = d.get("audit_delivery")
        if isinstance(audit_delivery, dict):
            d["audit_delivery"] = {"status": audit_delivery.get("status")}
        return d

    receipt_a = execution_a.terminal_receipt
    receipt_b = execution_b.terminal_receipt
    assert _normalize_terminal(receipt_a) == _normalize_terminal(receipt_b)
    assert len(receipt_a["effect_receipt_refs"]) == len(receipt_b["effect_receipt_refs"]) == 3

    def _normalize_checkpoint(checkpoint: dict) -> dict:
        d = dict(checkpoint)
        d.pop("operation_id", None)
        return d

    checkpoint_a = receipt_service.load_checkpoint(operation_a.operation_id)
    checkpoint_b = receipt_service.load_checkpoint(operation_b.operation_id)
    assert _normalize_checkpoint(checkpoint_a) == _normalize_checkpoint(checkpoint_b)


# ---------------------------------------------------------------------------
# request_cancellation: idempotent, durable, visible from a fresh instance.
# ---------------------------------------------------------------------------


def test_request_cancellation_is_idempotent_first_request_wins(tmp_foundry: FoundryPaths) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service)
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    first = svc.request_cancellation(operation_id, workspace_id=workspace_id, requested_by="alice")
    assert first.outcome == "created"

    second = svc.request_cancellation(operation_id, workspace_id=workspace_id, requested_by="bob")
    assert second.outcome == "exact_replay"
    assert second.requested_by == "alice"  # first request wins, never overwritten

    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM cancellation_requests WHERE operation_id = ?", (operation_id,)
        ).fetchone()[0]
        assert count == 1
    finally:
        conn.close()


def test_cancellation_requested_visible_from_a_fresh_service_instance(
    tmp_foundry: FoundryPaths,
) -> None:
    """Durability, not an in-memory flag: a cancellation persisted through
    one service instance is visible through a completely different one
    backed by the same files."""

    op_service = OperatorOperationService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service)
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    svc.request_cancellation(operation_id, workspace_id=workspace_id)

    fresh_svc = OperatorCancelResumeService(tmp_foundry)
    assert fresh_svc.cancellation_requested(operation_id) is True
    assert fresh_svc.cancellation_requested("opm_" + "0" * 64) is False


# ---------------------------------------------------------------------------
# cancellation_requests DB-level immutability (mirrors the sibling tables'
# own trigger-enforced guarantee).
# ---------------------------------------------------------------------------


def test_cancellation_requests_table_rejects_raw_update(tmp_foundry: FoundryPaths) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service)
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    svc.request_cancellation(operation_id, workspace_id=outcome.operation.workspace_id)

    conn = _raw_connect(tmp_foundry)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "UPDATE cancellation_requests SET requested_by = 'mallory' WHERE operation_id = ?",
                (operation_id,),
            )
    finally:
        conn.close()


def test_cancellation_requests_table_rejects_raw_delete(tmp_foundry: FoundryPaths) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service)
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    svc.request_cancellation(operation_id, workspace_id=outcome.operation.workspace_id)

    conn = _raw_connect(tmp_foundry)
    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM cancellation_requests WHERE operation_id = ?", (operation_id,))
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# run_actions: an action that raises stops the whole operation, records a
# failed action_receipt, and finalizes status="failed".
# ---------------------------------------------------------------------------


def test_action_that_raises_stops_the_operation_and_finalizes_failed(
    tmp_foundry: FoundryPaths,
) -> None:
    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    def _boom() -> ActionEffect | None:
        raise RuntimeError("boom")

    executed: list[str] = []
    actions = [ActionSpec("act-0", _boom), _action("act-1", executed)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "failed"
    assert executed == []
    receipt = execution.terminal_receipt
    assert receipt["status"] == "failed"
    assert receipt["denial_reason_code"] == "internal_error"
    assert receipt["action_count_completed"] == 0
    assert receipt["action_count_total"] == 1


# ---------------------------------------------------------------------------
# U3/REGATE-BLOCK-1: `run_actions` must check the outcome of EVERY
# receipt-service call it makes, not only `finalize_terminal_receipt`/the
# success-branch `record_action_receipt`/`record_effect_receipt` (what a
# prior fix wave checked). Six calls were left discarding their result:
# ALL FIVE `write_checkpoint` calls, plus the failure-branch
# `record_action_receipt`. A REAL workspace-mismatch/phantom-operation
# denial (the only way these two methods deny in this codebase today)
# never naturally occurs from inside a HEALTHY `run_actions` call -- every
# operation_id/workspace_id it uses is already proven correct upstream --
# so a black-box test cannot trigger these denials through normal
# attacker-style setup the way U1/U2's tests do. `_ReceiptsFailureInjector`
# below wraps the REAL `OperatorReceiptService` (delegating every call
# EXCEPT the one this test wants to force) so each of the six call sites
# can be exercised in isolation, one test per site, proving `run_actions`
# reacts correctly to a denial AT THAT SPECIFIC POINT regardless of why a
# real deployment might one day produce one there.
# ---------------------------------------------------------------------------


class _ReceiptsFailureInjector:
    """Wraps a REAL `OperatorReceiptService`, delegating every call except
    one that a test-supplied predicate matches -- that ONE call returns a
    governed `ReceiptOutcome("denied", "internal_error", None)` instead of
    reaching real persistence. Used ONLY to prove `run_actions` reacts
    correctly to a receipt-service denial at each of its (previously
    discarded) call sites; every call that does NOT match still goes to
    the real service, against real sqlite persistence."""

    def __init__(self, real: OperatorReceiptService) -> None:
        self._real = real
        self.deny_write_checkpoint_when = None
        self.deny_record_action_receipt_when = None
        self.deny_record_effect_receipt_when = None
        self.write_checkpoint_calls: list[dict] = []
        self.record_action_receipt_calls: list[dict] = []
        self.record_effect_receipt_calls: list[dict] = []

    def write_checkpoint(self, operation_id: str, **kwargs):  # noqa: ANN001, ANN201
        self.write_checkpoint_calls.append(dict(kwargs))
        if self.deny_write_checkpoint_when is not None and self.deny_write_checkpoint_when(kwargs):
            return ReceiptOutcome("denied", "internal_error", None)
        return self._real.write_checkpoint(operation_id, **kwargs)

    def record_action_receipt(self, operation_id: str, **kwargs):  # noqa: ANN001, ANN201
        self.record_action_receipt_calls.append(dict(kwargs))
        if (
            self.deny_record_action_receipt_when is not None
            and self.deny_record_action_receipt_when(kwargs)
        ):
            return ReceiptOutcome("denied", "internal_error", None)
        return self._real.record_action_receipt(operation_id, **kwargs)

    def record_effect_receipt(self, operation_id: str, **kwargs):  # noqa: ANN001, ANN201
        self.record_effect_receipt_calls.append(dict(kwargs))
        if (
            self.deny_record_effect_receipt_when is not None
            and self.deny_record_effect_receipt_when(kwargs)
        ):
            return ReceiptOutcome("denied", "internal_error", None)
        return self._real.record_effect_receipt(operation_id, **kwargs)

    def __getattr__(self, name: str):  # noqa: ANN001, ANN204
        return getattr(self._real, name)


def test_run_actions_denies_when_pre_action_non_cancelable_checkpoint_is_denied(
    tmp_foundry: FoundryPaths,
) -> None:
    """U3/REGATE-BLOCK-1, call site 1 of 6: the `write_checkpoint` call
    that marks a `non_cancelable` action's checkpoint BEFORE it runs (the
    scenario-10 mechanism). Before this fix, its outcome was discarded --
    the action would run regardless of whether that checkpoint was ever
    durably written."""

    op_service = OperatorOperationService(tmp_foundry)
    real_receipts = OperatorReceiptService(tmp_foundry)
    injector = _ReceiptsFailureInjector(real_receipts)
    injector.deny_write_checkpoint_when = lambda kw: kw.get("non_cancelable") is True
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=injector)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    ran = False

    def _must_not_run() -> ActionEffect | None:  # pragma: no cover - only fails the test
        nonlocal ran
        ran = True
        return None

    actions = [ActionSpec("act-0", _must_not_run, non_cancelable=True)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "denied"
    assert ran is False  # the action never ran once its own checkpoint denied
    assert real_receipts.load_terminal_receipt(operation_id) is None


def test_run_actions_denies_when_failure_branch_action_receipt_is_denied(
    tmp_foundry: FoundryPaths,
) -> None:
    """U3/REGATE-BLOCK-1, call site 2 of 6: `record_action_receipt` on the
    FAILURE branch (recording that a raising action failed). Before this
    fix, a denied failure receipt still fell through to
    `write_checkpoint`/`finalize_terminal_receipt`, which could persist a
    terminal receipt claiming `status="failed"` with NO failure receipt
    actually in the ledger (X4 in the finding's own empirical repro)."""

    op_service = OperatorOperationService(tmp_foundry)
    real_receipts = OperatorReceiptService(tmp_foundry)
    injector = _ReceiptsFailureInjector(real_receipts)
    injector.deny_record_action_receipt_when = lambda kw: kw.get("status") == "failed"
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=injector)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    def _raises() -> ActionEffect | None:
        raise RuntimeError("simulated action failure")

    actions = [ActionSpec("act-0", _raises)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "denied"
    assert execution.terminal_receipt is None
    # No checkpoint or terminal receipt was ever written for a FAILURE the
    # store itself refused to durably record.
    assert real_receipts.load_checkpoint(operation_id) is None
    assert real_receipts.load_terminal_receipt(operation_id) is None


def test_run_actions_denies_when_failure_branch_checkpoint_is_denied(
    tmp_foundry: FoundryPaths,
) -> None:
    """U3/REGATE-BLOCK-1, call site 3 of 6: `write_checkpoint` on the
    FAILURE branch (the "converged" checkpoint written right before
    `finalize_terminal_receipt(status="failed")`)."""

    op_service = OperatorOperationService(tmp_foundry)
    real_receipts = OperatorReceiptService(tmp_foundry)
    injector = _ReceiptsFailureInjector(real_receipts)
    injector.deny_write_checkpoint_when = lambda kw: kw.get("status") == "converged"
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=injector)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    def _raises() -> ActionEffect | None:
        raise RuntimeError("simulated action failure")

    actions = [ActionSpec("act-0", _raises)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "denied"
    assert execution.terminal_receipt is None
    assert real_receipts.load_terminal_receipt(operation_id) is None


def test_run_actions_denies_when_post_action_success_checkpoint_is_denied(
    tmp_foundry: FoundryPaths,
) -> None:
    """U3/REGATE-BLOCK-1, call site 4 of 6: the `write_checkpoint` call
    immediately after a SUCCESSFUL action (`status="pending"`,
    `non_cancelable=False`) -- the loop's own per-iteration progress
    checkpoint. Before this fix, `run_actions` would keep executing every
    remaining action while persisting ZERO checkpoints if this denied,
    leaving process-loss recovery entirely unrecoverable-by-checkpoint on
    an operation nothing else flagged as wrong."""

    op_service = OperatorOperationService(tmp_foundry)
    real_receipts = OperatorReceiptService(tmp_foundry)
    injector = _ReceiptsFailureInjector(real_receipts)
    injector.deny_write_checkpoint_when = (
        lambda kw: kw.get("status") == "pending" and kw.get("non_cancelable") is False
    )
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=injector)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    executed: list[str] = []
    actions = [_action("act-0", executed), _action("act-1", executed)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "denied"
    # THE actual defect this closes: act-0 already ran (its own action/
    # effect receipts ARE durably persisted -- reconciliation would find
    # them), but the operation must not silently continue to act-1 once
    # its own progress checkpoint denies.
    assert executed == ["act-0"]
    assert real_receipts.load_terminal_receipt(operation_id) is None


def test_run_actions_denies_when_completed_checkpoint_is_denied(
    tmp_foundry: FoundryPaths,
) -> None:
    """U3/REGATE-BLOCK-1, call site 5 of 6: the `write_checkpoint` call in
    the for-else "every action ran" branch (`status="converged"`, marking
    the operation fully complete) -- BEFORE `finalize_terminal_receipt` is
    even reached."""

    op_service = OperatorOperationService(tmp_foundry)
    real_receipts = OperatorReceiptService(tmp_foundry)
    injector = _ReceiptsFailureInjector(real_receipts)
    injector.deny_write_checkpoint_when = lambda kw: kw.get("status") == "converged"
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=injector)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    executed: list[str] = []
    actions = [_action("act-0", executed)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "denied"
    assert executed == ["act-0"]  # the action DID run; the operation is not "completed"
    assert real_receipts.load_terminal_receipt(operation_id) is None


def test_run_actions_denies_when_canceled_checkpoint_is_denied(
    tmp_foundry: FoundryPaths,
) -> None:
    """U3/REGATE-BLOCK-1, call site 6 of 6: the `write_checkpoint` call on
    the durable-cancellation `break` branch (`status="converged"`,
    marking the operation canceled) -- BEFORE `finalize_terminal_receipt`
    is reached."""

    op_service = OperatorOperationService(tmp_foundry)
    real_receipts = OperatorReceiptService(tmp_foundry)
    injector = _ReceiptsFailureInjector(real_receipts)
    injector.deny_write_checkpoint_when = lambda kw: kw.get("status") == "converged"
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=injector)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    cancel = svc.request_cancellation(operation_id, workspace_id=workspace_id, requested_by="alice")
    assert cancel.outcome == "created"

    executed: list[str] = []
    actions = [_action("act-0", executed), _action("act-1", executed)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "denied"
    assert executed == []  # canceled before the first action even started
    assert real_receipts.load_terminal_receipt(operation_id) is None


# ---------------------------------------------------------------------------
# K1: the P2 re-gate found that two of `run_actions`' 11 outcome-carrying
# receipt-service calls -- the SUCCESS-branch `record_action_receipt`
# (status="completed") and `record_effect_receipt` -- were checked in the
# code (both have an `if ...outcome != "created": return ExecutionOutcome(
# "denied", ...)` guard) but had NO test that could fail if either guard
# were deleted: every other test in this module either never reaches these
# two call sites with a real effect, or reaches them but never denies them.
# These two tests close that gap using the SAME real-service-wrapping
# `_ReceiptsFailureInjector` pattern as the six U3/REGATE-BLOCK-1 tests
# above, extended with `deny_record_action_receipt_when(status="completed")`
# (the hook already existed, just unused for this branch) and the NEW
# `deny_record_effect_receipt_when` hook.
# ---------------------------------------------------------------------------


def _action_no_effect(action_id: str, executed: list[str]) -> ActionSpec:
    """Like `_action` above, but produces NO effect (`run()` returns
    `None`) -- deliberately, so `run_actions` never reaches its `if effect
    is not None:` block / `record_effect_receipt` call for this action.
    Used ONLY by the two tests below to isolate the SUCCESS-branch
    `record_action_receipt` guard from its downstream sibling
    (`record_effect_receipt`'s own guard, K1's OTHER half): an earlier
    draft of this test used effect-bearing actions, and its mutation
    verification revealed that draft passed EVEN WITH the guard under test
    deleted -- `record_effect_receipt`'s OWN write-time guard (an
    action_id must reference an already-persisted action_receipt) denied
    first, at the SAME loop index, producing byte-identical `executed`/
    `status` observables regardless of whether the action_receipt guard
    itself was present. That is the exact "redundant sibling guard" trap
    this task's proof requirements warn against (see U4/U8's docstrings
    elsewhere in this file) -- effect-less actions close it: with no
    effect, the ONLY thing standing between a denied action_receipt and an
    extra action silently executing is this specific guard."""

    def _run() -> ActionEffect | None:
        executed.append(action_id)
        return None

    return ActionSpec(action_id=action_id, run=_run)


def test_run_actions_denies_when_success_branch_action_receipt_is_denied(
    tmp_foundry: FoundryPaths,
) -> None:
    """K1, guard 1 of 2: the `record_action_receipt` call on the SUCCESS
    path (`status="completed"`, immediately after `spec.run()` returns
    without raising). Before this test existed, deleting this guard's
    `if action_receipt_outcome.outcome != "created": return
    ExecutionOutcome("denied", None, idx)` check left the entire operator
    suite passing at exit 0 -- the action's own receipt-service call was
    exercised by every scenario test, but never denied, so a mutant that
    fell through to unconditionally write the post-action checkpoint (and
    let the NEXT action start) went undetected. Uses `_action_no_effect`
    (not `_action`) -- see that helper's docstring for why an
    effect-bearing action here would let `record_effect_receipt`'s own
    guard mask this one instead of proving it independently."""

    op_service = OperatorOperationService(tmp_foundry)
    real_receipts = OperatorReceiptService(tmp_foundry)
    injector = _ReceiptsFailureInjector(real_receipts)
    injector.deny_record_action_receipt_when = lambda kw: kw.get("status") == "completed"
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=injector)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    executed: list[str] = []
    actions = [_action_no_effect("act-0", executed), _action_no_effect("act-1", executed)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "denied"
    # act-0 already ran (the action callable itself returned successfully)
    # before its own action_receipt denied -- THE actual defect this
    # closes: with the guard deleted, run_actions would fall through to
    # write_checkpoint (which persists unconditionally, with no
    # cross-check against real receipts) and let act-1 start too.
    assert executed == ["act-0"]
    assert real_receipts.load_checkpoint(operation_id) is None
    assert real_receipts.load_terminal_receipt(operation_id) is None


def test_run_actions_denies_when_effect_receipt_is_denied(
    tmp_foundry: FoundryPaths,
) -> None:
    """K1, guard 2 of 2: the `record_effect_receipt` call, reached only
    when `spec.run()` returns a non-`None` `ActionEffect`. Before this test
    existed, deleting this guard's `if effect_receipt_outcome.outcome !=
    "created": return ExecutionOutcome("denied", None, idx)` check left the
    entire operator suite passing at exit 0 -- every scenario test that
    exercises an effect-bearing action does so through the REAL service
    with nothing denying it, so a mutant that fell through to
    unconditionally write the post-action checkpoint (claiming progress on
    an effect that was never durably recorded) went undetected."""

    op_service = OperatorOperationService(tmp_foundry)
    real_receipts = OperatorReceiptService(tmp_foundry)
    injector = _ReceiptsFailureInjector(real_receipts)
    injector.deny_record_effect_receipt_when = lambda kw: True
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=injector)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    executed: list[str] = []
    actions = [_action("act-0", executed), _action("act-1", executed)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "denied"
    # act-0 ran and its action_receipt WAS durably persisted (reconciliation
    # would find it) -- only the effect_receipt denied. `resolve_resume_
    # point` reads ONLY real, already-committed `action_receipts` rows (see
    # that method's own docstring), so `next_action_index == 1` here proves
    # act-0's action_receipt is durably persisted, independent of anything
    # `run_actions` itself reports.
    assert executed == ["act-0"]
    resume_point = real_receipts.resolve_resume_point(operation_id)
    assert resume_point.outcome == "ok"
    assert resume_point.next_action_index == 1
    # THE actual defect this closes: with the guard deleted, run_actions
    # would write the post-action "pending" checkpoint (claiming act-0's
    # effect is durably recorded) even though record_effect_receipt denied.
    assert real_receipts.load_checkpoint(operation_id) is None
    assert real_receipts.load_terminal_receipt(operation_id) is None


def test_run_actions_denies_start_index_exceeding_total_action_count(
    tmp_foundry: FoundryPaths,
) -> None:
    """U4/REGATE-BLOCK-1: `run_actions` refuses `start_index > len(actions)`
    on its OWN, independent of any upstream caller's bound.

    This scenario is deliberately constructed so `finalize_terminal_
    receipt`'s OWN reconciliation is NOT a redundant sibling guard here
    (an earlier draft of this test used a FRESH, zero-receipt operation --
    that is always independently caught as TRUNCATED by reconciliation
    regardless of this guard, which is the exact "passes on revert because
    a redundant sibling guard subsumes it" trap this task's proof
    requirements warn against). Instead: `total`=5 real, correctly-
    contiguous action_receipts (indices 0-4) are pre-seeded directly --
    EXACTLY matching `len(actions)` -- then `run_actions` is called with a
    caller-supplied `start_index=7` that has NOTHING to do with that real
    persisted state (never derived from `resolve_resume_point`). Without
    this guard, the loop's own `range(7, 5)` is empty, so the for-else
    branch runs unconditionally and calls `finalize_terminal_receipt(
    expected_action_count=5, status="completed")` -- reconciliation finds
    EXACTLY 5 persisted receipts, matching the declared 5, and would
    happily produce a genuine `"completed"` terminal receipt. `start_index`
    itself is never checked against reality anywhere else in this module;
    this guard is the ONLY thing standing between a caller-supplied
    `start_index` that has drifted from reality and a falsely-"completed"
    operation.
    """

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    for i in range(5):
        seeded = receipt_service.record_action_receipt(
            operation_id,
            workspace_id=workspace_id,
            action_id=f"act-{i}",
            action_index=i,
            status="completed",
            attempt_ref="attempt-pre-seed",
            started_at=ids.now_iso(),
            completed_at=ids.now_iso(),
        )
        assert seeded.outcome == "created"

    executed: list[str] = []
    actions = [_action(f"act-{i}", executed) for i in range(5)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
        start_index=7,  # > len(actions) == 5, and NOT derived from reality
    )

    assert execution.status == "denied"
    assert execution.terminal_receipt is None
    assert executed == []  # the loop body never ran at all
    assert receipt_service.load_terminal_receipt(operation_id) is None


def test_run_or_replay_calls_resolve_resume_point_with_declared_total_action_count(
    tmp_foundry: FoundryPaths,
) -> None:
    """U4/REGATE-BLOCK-1, WIRING half: isolates the specific argument
    `total_action_count=len(actions)` in `run_or_replay`'s call to
    `resolve_resume_point`, independent of `run_actions`' own NEW
    `start_index > total` guard
    (`test_run_actions_denies_start_index_exceeding_total_action_count`
    above). That guard makes the OBSERVABLE outcome of deleting this
    argument harmless (denied either way, since the EXTRA-receipt case
    still produces `start_index=7 > total=5`) -- which means an
    outcome-only test can no longer detect the deletion on its own. This
    is the EXACT redundant-sibling-guard trap this task's proof
    requirements warn against, so this test isolates the WIRING directly
    via a spy around the real receipts service: `resolve_resume_point`
    MUST be called with `total_action_count == len(actions)`, full stop,
    regardless of what any downstream guard does with the result.
    """

    op_service = OperatorOperationService(tmp_foundry)
    real_receipts = OperatorReceiptService(tmp_foundry)

    calls: list[dict] = []
    _real_resolve_resume_point = real_receipts.resolve_resume_point

    def _spy_resolve_resume_point(operation_id: str, **kwargs):  # noqa: ANN001, ANN201
        calls.append(dict(kwargs))
        return _real_resolve_resume_point(operation_id, **kwargs)

    real_receipts.resolve_resume_point = _spy_resolve_resume_point  # type: ignore[method-assign]

    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=real_receipts)
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation = outcome.operation

    executed: list[str] = []
    actions = [_action(f"act-{i}", executed) for i in range(5)]

    execution = svc.run_or_replay(
        operation,
        is_replay=False,
        workspace_id=operation.workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "completed"
    assert len(calls) == 1
    assert calls[0].get("total_action_count") == len(actions) == 5


# ---------------------------------------------------------------------------
# P2S-BLOCK-2: `run_actions` must CHECK `finalize_terminal_receipt`'s
# returned outcome, never assume it succeeded.
# ---------------------------------------------------------------------------
#
# `run_or_replay`/`resume_operation` now bound `resolve_resume_point` by
# their own declared `total_action_count` (P2S-BLOCK-2's OTHER half, in
# `operator_receipt_service.py`), which catches an EXTRA-receipt operation
# BEFORE any action is (re-)executed on THOSE two entrypoints. To exercise
# `run_actions`' OWN outcome-check independently of that earlier gate
# (never assume one guard makes a sibling redundant -- "fix the layer
# below" cuts both ways), this test calls `run_actions` DIRECTLY (the same
# pattern every other scenario test in this file already uses) and plants
# the EXTRA receipt OUT OF BAND, past the point `run_actions` itself would
# ever look for it before starting -- so reconciliation inside
# `finalize_terminal_receipt`, not `resolve_resume_point`, is what denies.


def test_p2s_block2_extra_receipt_denies_run_actions_completed_branch(
    tmp_foundry: FoundryPaths,
) -> None:
    """H3 scenario 8, EXTRA variant, exercised through `run_actions` itself
    (not `resolve_resume_point`'s own, separate EXTRA guard). Before the
    fix, `run_actions`' for-else "every action ran" branch discarded
    `finalize_terminal_receipt`'s returned `ReceiptOutcome` and
    unconditionally returned `ExecutionOutcome("completed",
    outcome.receipt, total)` -- with `outcome.receipt is None` (finalize
    denied), fabricating a `"completed"` status with NO terminal receipt at
    all. The mutation-verification step for this task reverted exactly
    this check and confirmed THIS test fails as a result.

    U5/REGATE-BLOCK-3 note: an earlier revision of this test planted the
    EXTRA ghost receipt at index 5 BEFORE any of indices 0-4 existed --
    that specific shape is now itself a GAP, refused at write time by
    `record_action_receipt`'s own contiguity guard, so it can no longer be
    used to set up this scenario. This version instead pre-seeds all 5
    real actions' receipts directly (contiguous, valid writes, 0..4), THEN
    plants the ghost at index 5 -- now correctly the next contiguous index
    -- and calls `run_actions` with `start_index=5` so its own loop body
    never runs (nothing left to execute) and falls straight to the
    for-else "every action ran" branch this test targets, where
    reconciliation discovers 6 persisted receipts against a declared total
    of 5.
    """

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    for i in range(5):
        seeded = receipt_service.record_action_receipt(
            operation_id,
            workspace_id=workspace_id,
            action_id=f"act-{i}",
            action_index=i,
            status="completed",
            attempt_ref="attempt-pre-seed",
            started_at=ids.now_iso(),
            completed_at=ids.now_iso(),
        )
        assert seeded.outcome == "created"

    # Plant an EXTRA action_receipt at index 5, OUT OF BAND -- via the
    # real, real-persistence `record_action_receipt` (never a fake), one
    # index past the 5 real actions this `run_actions` call declares. This
    # is exactly the "one out-of-turn receipt" shape the P2 security gate
    # demonstrated.
    ghost_outcome = receipt_service.record_action_receipt(
        operation_id,
        workspace_id=workspace_id,
        action_id="act-ghost",
        action_index=5,
        status="completed",
        attempt_ref="attempt-out-of-band",
        started_at=ids.now_iso(),
        completed_at=ids.now_iso(),
    )
    assert ghost_outcome.outcome == "created"

    executed: list[str] = []
    actions = [_action(f"act-{i}", executed) for i in range(5)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
        start_index=5,
    )

    # Nothing NEW executed this call (all 5 real actions' receipts were
    # already pre-seeded above; `range(5, 5)` is empty) -- but the
    # operation must NOT be reported "completed", because reconciliation
    # (6 persisted action_receipts vs 5 declared) denies.
    assert executed == []
    assert execution.status == "denied"
    assert execution.terminal_receipt is None

    # And -- the actual corruption-detection invariant -- no terminal
    # receipt was ever durably persisted for this operation.
    assert receipt_service.load_terminal_receipt(operation_id) is None


# ---------------------------------------------------------------------------
# K1 follow-on (found by THIS task's own mutation-verification sweep, not
# by the P2 re-gate): the re-gate named exactly two untested outcome-
# carrying calls (the two tests above this block). Mutating the REMAINING
# nine guards one at a time to confirm the re-gate's count found TWO MORE
# that also left the full operator suite at exit 0 when neutralized --
# `finalize_terminal_receipt`'s FAILURE-branch and CANCELED-branch denial
# checks (the `if outcome.outcome == "denied":` guards immediately before
# `return ExecutionOutcome("failed", ...)` and `return ExecutionOutcome(
# "canceled", ...)` respectively). Every existing failure/cancellation test
# reaches a finalize call that always SUCCEEDS -- nothing plants an
# out-of-band EXTRA receipt on either of those two specific branches -- so
# no test could observe the difference between "denied, reported denied"
# and "denied, reported failed/canceled anyway" on those two paths. These
# two tests close that gap the same way `test_p2s_block2_extra_receipt_
# denies_run_actions_completed_branch` above closes it for the COMPLETED
# branch: a REAL, out-of-band EXTRA action_receipt, planted via the real
# `OperatorReceiptService` (never a fake). The completed-branch test could
# plant its ghost before `run_actions` even started (nothing else races
# with the caller). The failure/canceled branches cannot: their contiguity
# write-time guard refuses a ghost at `expected_action_count` before the
# branch's OWN write to `expected_action_count - 1` exists yet. So the
# ghost must be planted MID-FLIGHT, immediately before each branch's own
# `write_checkpoint(status="converged")` call -- `_GhostAtCheckpoint`
# below is a real-service wrapper that does exactly that as a side effect,
# then delegates the checkpoint write itself to the real service
# unmodified.
# ---------------------------------------------------------------------------


class _GhostAtCheckpoint:
    """Wraps a REAL `OperatorReceiptService`. The FIRST time `write_
    checkpoint` is called with `status="converged"`, it plants one real,
    out-of-band `action_receipt` at `ghost_index` (via the wrapped real
    service) BEFORE delegating the checkpoint write itself to that same
    real service, unmodified. Every other call goes straight through.
    Used only to reproduce the EXTRA-receipt corruption shape mid-flight,
    on branches whose own write-time contiguity guard makes it impossible
    to pre-plant the ghost before `run_actions` starts (see block comment
    above)."""

    def __init__(
        self,
        real: OperatorReceiptService,
        *,
        operation_id: str,
        workspace_id: str,
        ghost_index: int,
    ) -> None:
        self._real = real
        self._operation_id = operation_id
        self._workspace_id = workspace_id
        self._ghost_index = ghost_index
        self._planted = False

    def write_checkpoint(self, operation_id: str, **kwargs):  # noqa: ANN001, ANN201
        if not self._planted and kwargs.get("status") == "converged":
            self._planted = True
            ghost = self._real.record_action_receipt(
                self._operation_id,
                workspace_id=self._workspace_id,
                action_id="act-ghost",
                action_index=self._ghost_index,
                status="completed",
                attempt_ref="attempt-out-of-band",
                started_at=ids.now_iso(),
                completed_at=ids.now_iso(),
            )
            assert ghost.outcome == "created"
        return self._real.write_checkpoint(operation_id, **kwargs)

    def __getattr__(self, name: str):  # noqa: ANN001, ANN204
        return getattr(self._real, name)


def test_p2s_block2_extra_receipt_denies_run_actions_failed_branch(
    tmp_foundry: FoundryPaths,
) -> None:
    """K1 follow-on, failure branch: a single action raises (idx=0), so
    the failure branch's own `record_action_receipt(status="failed",
    action_index=0)` and `write_checkpoint(status="converged")` both
    succeed normally -- but a real, out-of-band ghost `action_receipt` is
    planted at index=1 (one past `expected_action_count=idx+1=1`)
    immediately before that checkpoint write, so `finalize_terminal_
    receipt(expected_action_count=1, status="failed")`'s own reconciliation
    -- not any earlier guard -- is what denies."""

    op_service = OperatorOperationService(tmp_foundry)
    real_receipts = OperatorReceiptService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    injected = _GhostAtCheckpoint(
        real_receipts, operation_id=operation_id, workspace_id=workspace_id, ghost_index=1
    )
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=injected)

    def _raises() -> ActionEffect | None:
        raise RuntimeError("simulated action failure")

    actions = [ActionSpec("act-0", _raises)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "denied"
    assert execution.terminal_receipt is None
    # The FAILURE receipt and its checkpoint WERE durably persisted
    # (reconciliation would find them) -- only finalize's own reconciled
    # EXTRA check is what denies.
    assert real_receipts.load_checkpoint(operation_id)["status"] == "converged"
    assert real_receipts.load_terminal_receipt(operation_id) is None


def test_p2s_block2_extra_receipt_denies_run_actions_canceled_branch(
    tmp_foundry: FoundryPaths,
) -> None:
    """K1 follow-on, canceled branch: cancellation is requested before the
    single action ever starts, so the `break` fires at idx=0
    (`completed_action_count=0`). The canceled branch's own `write_
    checkpoint(status="converged", completed_action_count=0)` succeeds
    normally -- but a real, out-of-band ghost `action_receipt` is planted
    at index=0 (one past `expected_action_count=idx=0`) immediately before
    that checkpoint write, so `finalize_terminal_receipt(expected_
    action_count=0, status="canceled")`'s own reconciliation -- not any
    earlier guard -- is what denies."""

    op_service = OperatorOperationService(tmp_foundry)
    real_receipts = OperatorReceiptService(tmp_foundry)
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    injected = _GhostAtCheckpoint(
        real_receipts, operation_id=operation_id, workspace_id=workspace_id, ghost_index=0
    )
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=injected)

    cancel = svc.request_cancellation(operation_id, workspace_id=workspace_id, requested_by="alice")
    assert cancel.outcome == "created"

    executed: list[str] = []
    actions = [_action("act-0", executed)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "denied"
    assert execution.terminal_receipt is None
    assert executed == []  # canceled before the action ever started
    assert real_receipts.load_checkpoint(operation_id)["status"] == "converged"
    assert real_receipts.load_terminal_receipt(operation_id) is None


def test_p2s_block2_extra_receipt_denies_run_or_replay_before_any_action_executes(
    tmp_foundry: FoundryPaths,
) -> None:
    """H3 scenario 8's EXTRA variant, this time through `run_or_replay`'s
    OWN entry point -- exercises `resolve_resume_point`'s new
    `total_action_count` bound (`operator_receipt_service.py`), the OTHER
    half of the P2S-BLOCK-2 fix, independent of the `run_actions`
    outcome-check exercised by
    `test_p2s_block2_extra_receipt_denies_run_actions_completed_branch`
    above. This is the EARLIER, cheaper catch the finding's recommended
    fix (b) added: EXTRA is denied BEFORE any action is (re-)executed,
    not only once `run_actions` reaches `finalize_terminal_receipt` at
    the very end -- so `executed` below must stay EMPTY.

    Mirrors the security gate's own empirical repro almost verbatim:
    create a real operation, record 7 contiguous action_receipts against
    a 5-action operation (real persistence, `record_action_receipt`, not
    a fake), then call `run_or_replay`.
    """

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation = outcome.operation

    for i in range(7):  # EXTRA: 7 persisted, operation below only declares 5
        receipt_outcome = receipt_service.record_action_receipt(
            operation.operation_id,
            workspace_id=operation.workspace_id,
            action_id=f"act-{i}",
            action_index=i,
            status="completed",
            attempt_ref="attempt-out-of-band",
            started_at=ids.now_iso(),
            completed_at=ids.now_iso(),
        )
        assert receipt_outcome.outcome == "created"

    executed: list[str] = []
    actions = [_action(f"real-act-{i}", executed) for i in range(5)]

    execution = svc.run_or_replay(
        operation,
        is_replay=True,
        workspace_id=operation.workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "denied"
    assert execution.terminal_receipt is None
    # THE key distinction from the run_actions-level test: zero actions
    # ran at all -- caught before execution, not after.
    assert executed == []
    assert receipt_service.load_terminal_receipt(operation.operation_id) is None


# ---------------------------------------------------------------------------
# P2S-BLOCK-5: `request_cancellation` must be workspace-AUTHORIZED, not
# merely workspace-attributed -- a caller asserting the WRONG workspace_id
# for a REAL operation in a DIFFERENT workspace must be denied, never
# silently corrected and never allowed to create the (irrevocable) row.
# ---------------------------------------------------------------------------


def test_request_cancellation_cross_workspace_forgery_denies_zero_effect(
    tmp_foundry: FoundryPaths,
) -> None:
    """The exact attack the security gate demonstrated empirically:
    `request_cancellation(victim_operation_id, workspace_id="ws-attacker")`
    must now DENY -- before this fix it returned `"created"` and
    permanently, cross-workspace, canceled the victim's future execution.
    """

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    real_workspace_id = outcome.operation.workspace_id

    forged = svc.request_cancellation(
        operation_id, workspace_id="ws-attacker", requested_by="mallory"
    )
    assert forged.outcome == "denied"
    assert forged.reason_code == "not_found"
    assert forged.requested_at is None

    # ZERO effect: no cancellation_requests row at all for this operation.
    conn = _raw_connect(tmp_foundry)
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM cancellation_requests WHERE operation_id = ?",
            (operation_id,),
        ).fetchone()[0]
        assert count == 0
    finally:
        conn.close()

    # The victim operation is UNAFFECTED -- it still runs to completion,
    # not "canceled" (proves the forged request had zero real effect, not
    # merely zero row -- the actual attack scenario the gate ran).
    executed: list[str] = []
    actions = [_action("act-0", executed), _action("act-1", executed)]
    execution = svc.run_actions(
        operation_id,
        workspace_id=real_workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )
    assert execution.status == "completed"
    assert executed == ["act-0", "act-1"]

    # And a LEGITIMATE, same-workspace cancellation request still works
    # normally on a fresh operation -- the fix denies the FORGED case, not
    # cancellation in general.
    outcome2 = _consume(
        tmp_foundry,
        op_service,
        _basic_ctx(targets=_run_targets(), idempotency_key="legit-cancel"),
    )
    legit = svc.request_cancellation(
        outcome2.operation.operation_id,
        workspace_id=outcome2.operation.workspace_id,
        requested_by="alice",
    )
    assert legit.outcome == "created"


def test_request_cancellation_nonexistent_operation_denies_indistinguishably(
    tmp_foundry: FoundryPaths,
) -> None:
    """A genuinely missing `operation_id` and a wrong-workspace one
    resolve to the SAME shape (`reason_code == "not_found"`, zero
    effect) -- no existence leak."""

    op_service = OperatorOperationService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service)

    missing = svc.request_cancellation(
        "opm_" + "9" * 64, workspace_id="any-workspace", requested_by="alice"
    )
    assert missing.outcome == "denied"
    assert missing.reason_code == "not_found"


def test_cancellation_requested_scoped_read_denies_cross_workspace(
    tmp_foundry: FoundryPaths,
) -> None:
    """P2S-BLOCK-5, read-side defense in depth: `cancellation_requested`'s
    optional `workspace_id` scoping (used internally by `run_actions`)
    denies a real cancellation row when queried under the WRONG
    workspace, even though the write itself is now authorized (this
    guards a future direct caller of `cancellation_requested`, not the
    primary attack -- which the write-side fix above already closes)."""

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    created = svc.request_cancellation(operation_id, workspace_id=workspace_id)
    assert created.outcome == "created"

    assert svc.cancellation_requested(operation_id) is True  # unscoped
    assert svc.cancellation_requested(operation_id, workspace_id=workspace_id) is True
    assert svc.cancellation_requested(operation_id, workspace_id="ws-attacker") is False


# ---------------------------------------------------------------------------
# K3-NB-1 / K3-NB-2 / K3-NB-3 (Karen gate, tree `be6ba96`)
# ---------------------------------------------------------------------------


def test_run_actions_denies_negative_start_index_and_executes_nothing(
    tmp_foundry: FoundryPaths,
) -> None:
    """K3-NB-1: U4's bound was UPPER-only, delivering half the
    caller-independence its own docstring claims. `start_index=-1` on 3
    actions makes `range(-1, 3)` yield `-1` FIRST, so `actions[-1]` -- the
    LAST action -- executes out of order; `record_action_receipt`'s
    `action_index >= 0` guard then raises a raw `ValueError` out of this
    service, AFTER a real effect has already been performed and with no
    `ExecutionOutcome`, no receipt and no checkpoint to show for it.

    NOT redundant with any downstream guard, and this is why the assertion
    is on `executed`, not merely on the outcome: the pre-fix failure mode
    is precisely that a downstream guard DOES eventually object -- by
    raising -- but only after `act-2` already ran. An outcome-only
    assertion cannot tell "denied before anything ran" from "blew up after
    an effect". So this test pins the effect observable.
    """

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    executed: list[str] = []
    actions = [_action(f"act-{i}", executed) for i in range(3)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
        start_index=-1,
    )

    # Governed denial, not a raw ValueError escaping the service.
    assert execution.status == "denied"
    # THE load-bearing assertion: zero effects. Pre-fix, `executed ==
    # ["act-2"]` -- the last action ran out of order before anything
    # objected.
    assert executed == []


def test_resume_operation_calls_resolve_resume_point_with_declared_total_action_count(
    tmp_foundry: FoundryPaths,
) -> None:
    """K3-NB-2: the sibling of the wiring pinned by
    `test_run_or_replay_calls_resolve_resume_point_with_declared_total_action_count`.
    `resume_operation`'s own `total_action_count=len(actions)` argument was
    revert-undetectable -- setting it to `None` left the whole suite green,
    because `run_actions`' K3-NB-1/U4 bound makes the OBSERVABLE outcome
    identical either way. That is the redundant-sibling-guard trap, so this
    test isolates the WIRING via a spy, exactly as its sibling does.
    """

    op_service = OperatorOperationService(tmp_foundry)
    real_receipts = OperatorReceiptService(tmp_foundry)
    attempt_adapter = OperatorAttemptAdapter(tmp_foundry)

    calls: list[dict] = []
    _real_resolve_resume_point = real_receipts.resolve_resume_point

    def _spy_resolve_resume_point(operation_id: str, **kwargs):  # noqa: ANN001, ANN201
        calls.append(dict(kwargs))
        return _real_resolve_resume_point(operation_id, **kwargs)

    real_receipts.resolve_resume_point = _spy_resolve_resume_point  # type: ignore[method-assign]

    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=real_receipts)
    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    resume_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="job.resume",
        idempotency_key="resume-k3nb2",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("agent_job", operation_id),),
        resolved_target_workspaces=(_IDENTITY.workspace_id,),
    )
    resume_confirmation_id, resume_token, record = _mint_and_record(op_service, resume_ctx)
    resume_authorization = _authorize(
        tmp_foundry, resume_ctx, confirmation_record=record, presented_token=resume_token
    )

    actions = [_action(f"act-{i}", []) for i in range(3)]

    svc.resume_operation(
        operation_id,
        identity=_IDENTITY,
        resume_ctx=resume_ctx,
        resume_confirmation_id=resume_confirmation_id,
        resume_presented_token=resume_token,
        resume_authorization=resume_authorization,
        actions=actions,
        operation_kind=ctx.operation_kind,
        workspace_id=workspace_id,
        attempt_adapter=attempt_adapter,
        attempt_provider="claude_agent_sdk",
        attempt_model_profile="rf_synthesize_deep",
        attempt_request_kind="research",
        attempt_policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
    )

    assert len(calls) >= 1
    assert calls[0].get("total_action_count") == len(actions) == 3


def test_run_actions_checks_cancellation_with_the_operations_workspace_id(
    tmp_foundry: FoundryPaths,
) -> None:
    """K3-NB-3 (REGATE-NB-3, still open at `be6ba96`): `run_actions`' safe-
    point call `self.cancellation_requested(operation_id,
    workspace_id=workspace_id)` was revert-undetectable -- the parameter
    defaults to `None`, which means UNSCOPED, and dropping the kwarg left
    the suite green.

    Spies the method to pin the argument itself. An outcome-only test
    cannot detect the loss: with only one workspace in play, scoped and
    unscoped reads return the same row, so the observable is identical
    while the cross-workspace guarantee is gone.
    """

    op_service = OperatorOperationService(tmp_foundry)
    receipt_service = OperatorReceiptService(tmp_foundry)
    svc = OperatorCancelResumeService(tmp_foundry, operations=op_service, receipts=receipt_service)

    ctx = _basic_ctx(targets=_run_targets())
    outcome = _consume(tmp_foundry, op_service, ctx)
    operation_id = outcome.operation.operation_id
    workspace_id = outcome.operation.workspace_id

    calls: list[dict] = []
    _real_cancellation_requested = svc.cancellation_requested

    def _spy_cancellation_requested(op_id: str, **kwargs):  # noqa: ANN001, ANN201
        calls.append(dict(kwargs))
        return _real_cancellation_requested(op_id, **kwargs)

    svc.cancellation_requested = _spy_cancellation_requested  # type: ignore[method-assign]

    executed: list[str] = []
    actions = [_action(f"act-{i}", executed) for i in range(2)]

    execution = svc.run_actions(
        operation_id,
        workspace_id=workspace_id,
        operation_kind=ctx.operation_kind,
        actions=actions,
        attempt_ref="attempt-1",
    )

    assert execution.status == "completed"
    # One safe-point check per action, each explicitly scoped.
    assert len(calls) == len(actions)
    for call in calls:
        assert call.get("workspace_id") == workspace_id
