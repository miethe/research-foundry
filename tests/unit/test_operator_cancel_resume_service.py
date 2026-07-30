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
from research_foundry.services.operator_receipt_service import OperatorReceiptService

# Reuse, never reinvent (per this task's instructions and the project's own
# convention -- see `test_operator_operation_service.py`'s own docstring):
# the policy test module's identity fixtures/helpers, and OPM-2.1's own
# confirmation-lifecycle test helpers.
from tests.unit.test_operator_mcp_policy import (  # noqa: F401
    _IDENTITY,
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
        action_id="act-0",
        action_index=0,
        status="completed",
        attempt_ref="attempt-precrash",
        started_at=ids.now_iso(),
        completed_at=ids.now_iso(),
    )
    receipt_service.record_effect_receipt(
        operation_id,
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

    receipt_service.record_action_receipt(
        operation_id,
        action_id="act-0",
        action_index=0,
        status="completed",
        attempt_ref="attempt-x",
        started_at=ids.now_iso(),
        completed_at=ids.now_iso(),
    )
    # Directly corrupt persisted state via raw SQL: insert index 2,
    # skipping index 1 -- a gap this module's own write-time guards
    # (`record_action_receipt`'s PRIMARY KEY / UNIQUE constraints) only
    # ever prevent for DUPLICATE/reordered-COLLIDING indices, never for an
    # externally-inserted GAP. Mutating against real, already-committed
    # persistence, per this task's proof requirement -- never a fake.
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
        action_id="act-0",
        action_index=0,
        status="completed",
        attempt_ref="attempt-x",
        started_at=ids.now_iso(),
        completed_at=ids.now_iso(),
    )
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

    def _atomic_publish_fails() -> ActionEffect:
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

    # Never renamed into place -- no partial artifact at the real
    # destination, even though the action itself failed mid-flight.
    assert not dest.exists()
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
        action_id=actions_b[0].action_id,
        action_index=0,
        status="completed",
        attempt_ref="attempt-b-precrash",
        started_at=ids.now_iso(),
        completed_at=ids.now_iso(),
    )
    receipt_service.record_effect_receipt(
        operation_b.operation_id,
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
