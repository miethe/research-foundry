"""Cancel and resume state machine for the local-stdio Operator MCP
(research-foundry-operator-mcp-v1 P2, OPM-2.4).

This module COMPOSES the three P2 services that precede it -- it adds no
new schema authority of its own (P2-ARCH-1 is unchanged:
`operator_operation_service._ensure_schema` remains the SOLE schema/
migration authority for `paths.operator_operations_db`; this module opens
that database via that module's own `_connect`/`_ensure_schema`, DML only,
for exactly one new table, `cancellation_requests`, added additively under
schema version 3 by that module):

* `operator_operation_service.py` (OPM-2.1) -- durable operation manifests
  and the DUR-1 confirmation-consumption CAS. A RESUME is itself gated
  through this module's `consume_and_create_operation`, for the SAME
  `job.resume` operation kind every other governed request uses -- "fresh
  policy/confirmation" is not a new, parallel gate this module invents; it
  IS that gate, reused.
* `operator_receipt_service.py` (OPM-2.3) -- action/effect/checkpoint/
  terminal receipt persistence and reconciliation. This module's
  `resolve_resume_point` (added there, not here -- see that module) reads
  ONLY real, already-committed `action_receipts` rows to answer "what is
  the first incomplete action", never `checkpoint`'s own possibly-stale
  `next_action_index` and never any in-process object.
* `operator_attempt_adapter.py` (OPM-2.2) -- AgentJob-backed attempts.
  Resume creates a NEW attempt through THIS adapter (never a parallel
  attempt-minting path of its own).

H3 SCENARIO OWNERSHIP (this task, OPM-2.4): 5, 6, 7, 9, 10, and extending 8
to the RESUME path. Scenarios 1/3/4 are OPM-2.1's (DUR-1's own CAS); 2 is
wired end-to-end here via :meth:`OperatorCancelResumeService.run_or_replay`
(an operation whose confirmation is exact-replayed and which ALREADY has a
persisted terminal receipt returns that EXACT receipt, with ZERO new
action/effect receipts and ZERO re-execution -- see that method's
docstring); 8's write-time half is OPM-2.3's own duplicate/mismatched
write-time guards.

CANCELLATION IS A DURABLE FACT, NOT AN IN-MEMORY FLAG (scenario 5/6): a
`cancellation_requests` row, once written, is checked at every SAFE POINT
-- the top of each loop iteration in :meth:`run_actions`, BEFORE the next
action starts. It is never checked, and can never take effect, WHILE a
`non_cancelable` action is running (scenario 10): `run_actions` marks the
checkpoint `non_cancelable=True` before invoking such an action's `run`
callable and does not re-check cancellation until that callable has
returned (or raised) and its own action/effect receipts (or failure
receipt) have already been durably recorded -- the action always completes
or fails WHOLE; a request to cancel it merely defers to the very next safe
point, it can never truncate it.

RESUME NEVER REPLAYS A COMPLETED EFFECT (scenario 7): `run_actions` accepts
a `start_index` and begins there -- it never re-invokes `actions[i].run()`
for `i < start_index`. Combined with `resolve_resume_point` reading real
persisted rows (not checkpoint, not any surviving object), a genuine
process loss after an effect receipt but before the NEXT checkpoint write
still resumes at the correct, un-replayed index once a caller supplies
`start_index=resolve_resume_point(...).next_action_index` on a FRESH
service instance backed by the same durable files.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from research_foundry import ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services import operator_operation_service as _ops_store
from research_foundry.services.operator_attempt_adapter import (
    AttemptRecord,
    OperatorAttemptAdapter,
)
from research_foundry.services.operator_operation_service import (
    AuthorizationProof,
    OperationRecord,
    OperatorOperationService,
)
from research_foundry.services.operator_receipt_service import (
    OperatorReceiptService,
    ResumePointOutcome,
)

_logger = logging.getLogger(__name__)

__all__ = [
    "ActionEffect",
    "ActionSpec",
    "CancellationOutcome",
    "ExecutionOutcome",
    "ResumeOutcome",
    "OperatorCancelResumeService",
]


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ActionEffect:
    """The effect one :class:`ActionSpec`'s `run` callable produced --
    directly the arguments `record_effect_receipt` needs, minus
    `operation_id`/`action_id`/`generated_at` (supplied by the loop)."""

    effect_kind: str
    effect_digest: str
    effect_ref: str


@dataclass(frozen=True)
class ActionSpec:
    """One action in an operation's action manifest.

    `run` is caller-supplied and executes the action's real side effect
    (e.g. an atomic file publication) -- this module never inspects or
    interprets what it does, only WHEN it is allowed to run and how its
    outcome is reconciled into receipts. Returns an :class:`ActionEffect`
    if the action produced one, or `None` for an action with no durable
    effect of its own (e.g. a pure read/status check).

    `non_cancelable=True` marks an ATOMIC, indivisible section (OPM-OQ-4 /
    schema `checkpoint.non_cancelable`): see module docstring's "cancellation
    is a durable fact" section for the exact safe-point contract this
    controls.
    """

    action_id: str
    run: Callable[[], "ActionEffect | None"]
    non_cancelable: bool = False


@dataclass(frozen=True)
class CancellationOutcome:
    """Result of :meth:`OperatorCancelResumeService.request_cancellation`.

    `outcome` is `"created"` for the first request against `operation_id`,
    `"exact_replay"` for every subsequent one (idempotent -- first request
    wins, never a second row, never a raised exception)."""

    outcome: Literal["created", "exact_replay"]
    operation_id: str
    requested_at: str
    requested_by: str | None


@dataclass(frozen=True)
class ExecutionOutcome:
    """Result of :meth:`OperatorCancelResumeService.run_actions` (and, via
    it, :meth:`resume_operation`).

    `status` mirrors `terminal_receipt.status` for the three terminal
    dispositions (`"completed"` / `"canceled"` / `"failed"`) that always
    correspond to a persisted `terminal_receipt` (`terminal_receipt` is
    non-`None` in exactly those three cases). `"denied"` is the ONE
    exception: :meth:`run_or_replay` returns it, with `terminal_receipt is
    None`, when `resolve_resume_point` denies due to corrupt receipt state
    (scenario 8, extended to resume) -- no receipt is produced for a
    state this module refuses to interpret. `run_actions` itself never
    returns `"denied"`; a governed denial of the RESUME request's own
    fresh policy/confirmation (scenario 9) is reported by
    :class:`ResumeOutcome`, one layer up, before `run_actions` is ever
    reached.
    """

    status: Literal["completed", "canceled", "failed", "denied"]
    terminal_receipt: Mapping[str, Any] | None
    completed_action_count: int
    replayed: bool = False


@dataclass(frozen=True)
class ResumeOutcome:
    """Result of :meth:`OperatorCancelResumeService.resume_operation`.

    `outcome`:
        `"resumed"`
            The fresh `job.resume` confirmation was accepted, a NEW
            attempt was created, and execution continued from the first
            incomplete action (or finalized immediately if none remained).
        `"already_terminal"`
            The fresh `job.resume` confirmation was accepted, but
            `operation_id` already has a persisted terminal receipt --
            returned verbatim, with NO new attempt and NO re-execution.
        `"denied"`
            The fresh `job.resume` confirmation/policy check itself was
            refused (scenario 9), the original `operation_id` does not
            exist / is not in this workspace, or `resolve_resume_point`
            denied due to corrupt receipt state (scenario 8, extended).
            `reason_code` is one of `operator_mcp_policy.CLOSED_REASON_CODES`.
    """

    outcome: Literal["resumed", "already_terminal", "denied"]
    reason_code: str | None
    terminal_receipt: Mapping[str, Any] | None
    new_attempt: AttemptRecord | None = None
    execution: ExecutionOutcome | None = None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class OperatorCancelResumeService:
    """Cancel-request persistence, the safe-point execution loop, and
    fresh-authority resume (P2, OPM-2.4). See module docstring for the full
    H3 scenario mapping."""

    def __init__(
        self,
        paths: FoundryPaths,
        *,
        operations: OperatorOperationService | None = None,
        receipts: OperatorReceiptService | None = None,
    ) -> None:
        self._paths = paths
        self._operations = operations or OperatorOperationService(paths)
        self._receipts = receipts or OperatorReceiptService(paths)

    # -- cancellation request persistence (scenario 5/6) -------------------

    def request_cancellation(
        self,
        operation_id: str,
        *,
        workspace_id: str,
        requested_by: str | None = None,
    ) -> CancellationOutcome:
        """Durably persist a cancellation request for `operation_id`.

        Idempotent: a second (or Nth) call for the same `operation_id`
        returns the FIRST persisted request unchanged (`"exact_replay"`) --
        never a second row, never an exception. This is the durable fact
        :meth:`run_actions` checks at every safe point; it survives process
        loss because it lives in `paths.operator_operations_db`, not in any
        in-memory flag on this (or any) service instance.
        """

        if not isinstance(operation_id, str) or not operation_id:
            raise ValueError("request_cancellation requires a non-empty operation_id")
        if not isinstance(workspace_id, str) or not workspace_id:
            raise ValueError("request_cancellation requires a non-empty workspace_id")

        moment = ids.now_iso()
        conn = _ops_store._connect(self._paths)
        try:
            _ops_store._ensure_schema(conn)
            conn.execute("BEGIN IMMEDIATE")
            try:
                existing = conn.execute(
                    "SELECT requested_at, requested_by FROM cancellation_requests"
                    " WHERE operation_id = ?",
                    (operation_id,),
                ).fetchone()
                if existing is not None:
                    conn.execute("COMMIT")
                    return CancellationOutcome(
                        "exact_replay",
                        operation_id,
                        existing["requested_at"],
                        existing["requested_by"],
                    )
                conn.execute(
                    "INSERT INTO cancellation_requests"
                    " (operation_id, workspace_id, requested_at, requested_by)"
                    " VALUES (?, ?, ?, ?)",
                    (operation_id, workspace_id, moment, requested_by),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        finally:
            conn.close()

        return CancellationOutcome("created", operation_id, moment, requested_by)

    def cancellation_requested(self, operation_id: str) -> bool:
        """Return whether a durable cancellation request exists for
        `operation_id` -- reads real persisted state, never an in-process
        flag."""

        conn = _ops_store._connect(self._paths)
        try:
            _ops_store._ensure_schema(conn)
            row = conn.execute(
                "SELECT 1 FROM cancellation_requests WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        finally:
            conn.close()
        return row is not None

    # -- the safe-point execution loop (scenario 5/6/10) --------------------

    def run_actions(
        self,
        operation_id: str,
        *,
        workspace_id: str,
        operation_kind: str,
        actions: Sequence[ActionSpec],
        attempt_ref: str,
        start_index: int = 0,
        audit_actor_user_id: str | None = None,
    ) -> ExecutionOutcome:
        """Execute `actions[start_index:]`, checking
        :meth:`cancellation_requested` at the top of every iteration (a
        safe point) BEFORE starting the next action -- never mid-action,
        never after only part of a `non_cancelable` action has run.

        Never replays `actions[i]` for `i < start_index` -- resume support
        (scenario 7) is exactly "call this with the right `start_index`",
        computed by :meth:`~research_foundry.services.operator_receipt_service.
        OperatorReceiptService.resolve_resume_point` from REAL persisted
        receipts, not from any in-process state.

        A `non_cancelable` action's checkpoint is marked BEFORE it runs and
        cleared only after it (successfully or not) has finished and its
        own receipt has been durably recorded -- cancellation observed
        during it is deferred to the NEXT iteration's safe-point check,
        never applied mid-action (scenario 10).

        An action whose `run()` raises is recorded as a `failed`
        `action_receipt` (`reason_code="internal_error"`) and the WHOLE
        operation stops there -- no further actions run, and the terminal
        receipt is finalized `status="failed"`.

        `record_action_receipt`/`record_effect_receipt`'s own `ReceiptOutcome`
        is CHECKED, never assumed successful -- a `"denied"` outcome from
        either (a receipt-integrity violation: duplicate/reordered/
        mismatched, OPM-2.3's own write-time guards) stops the operation
        immediately with `ExecutionOutcome("denied", ...)` and writes NO
        further receipt -- `finalize_terminal_receipt` is deliberately not
        attempted here, since the `expected_action_count` this method could
        supply would only be a guess at a state already proven corrupt.
        This branch is unreachable via `run_actions`' own normal control
        flow (it only ever calls these with an index it has not itself
        already written); it protects against a `start_index` computed
        from stale/corrupt state reaching this method at all (e.g. a caller
        that bypasses `resolve_resume_point`'s own denial).
        """

        total = len(actions)
        idx = start_index
        for idx in range(start_index, total):
            if self.cancellation_requested(operation_id):
                break

            spec = actions[idx]
            started_at = ids.now_iso()
            if spec.non_cancelable:
                self._receipts.write_checkpoint(
                    operation_id,
                    workspace_id=workspace_id,
                    status="pending",
                    next_action_index=idx,
                    completed_action_count=idx,
                    total_action_count=total,
                    non_cancelable=True,
                )

            try:
                effect = spec.run()
            except Exception:
                _logger.error(
                    "operator_cancel_resume_service: action %s (index %d) raised "
                    "during execution for operation_id=%s -- recording failure and "
                    "stopping the operation",
                    spec.action_id,
                    idx,
                    operation_id,
                    exc_info=True,
                )
                self._receipts.record_action_receipt(
                    operation_id,
                    action_id=spec.action_id,
                    action_index=idx,
                    status="failed",
                    attempt_ref=attempt_ref,
                    started_at=started_at,
                    completed_at=ids.now_iso(),
                    reason_code="internal_error",
                    retryable=False,
                )
                self._receipts.write_checkpoint(
                    operation_id,
                    workspace_id=workspace_id,
                    status="converged",
                    next_action_index=None,
                    completed_action_count=idx,
                    total_action_count=total,
                    non_cancelable=False,
                )
                outcome = self._receipts.finalize_terminal_receipt(
                    operation_id,
                    workspace_id=workspace_id,
                    operation_kind=operation_kind,
                    expected_action_count=idx + 1,
                    status="failed",
                    denial_reason_code="internal_error",
                    audit_actor_user_id=audit_actor_user_id,
                )
                return ExecutionOutcome("failed", outcome.receipt, idx)

            action_receipt_outcome = self._receipts.record_action_receipt(
                operation_id,
                action_id=spec.action_id,
                action_index=idx,
                status="completed",
                attempt_ref=attempt_ref,
                started_at=started_at,
                completed_at=ids.now_iso(),
            )
            if action_receipt_outcome.outcome != "created":
                _logger.error(
                    "operator_cancel_resume_service: record_action_receipt denied "
                    "(%s) for operation_id=%s action_id=%s index=%d -- stopping "
                    "without finalizing (receipt-integrity violation on already- "
                    "corrupt/racing state)",
                    action_receipt_outcome.reason_code,
                    operation_id,
                    spec.action_id,
                    idx,
                )
                return ExecutionOutcome("denied", None, idx)

            if effect is not None:
                effect_receipt_outcome = self._receipts.record_effect_receipt(
                    operation_id,
                    action_id=spec.action_id,
                    effect_kind=effect.effect_kind,
                    effect_digest=effect.effect_digest,
                    effect_ref=effect.effect_ref,
                    generated_at=ids.now_iso(),
                )
                if effect_receipt_outcome.outcome != "created":
                    _logger.error(
                        "operator_cancel_resume_service: record_effect_receipt "
                        "denied (%s) for operation_id=%s action_id=%s index=%d -- "
                        "stopping without finalizing",
                        effect_receipt_outcome.reason_code,
                        operation_id,
                        spec.action_id,
                        idx,
                    )
                    return ExecutionOutcome("denied", None, idx)

            self._receipts.write_checkpoint(
                operation_id,
                workspace_id=workspace_id,
                status="pending",
                next_action_index=idx + 1,
                completed_action_count=idx + 1,
                total_action_count=total,
                non_cancelable=False,
            )
        else:
            # Loop completed without `break` -- every action in
            # [start_index, total) ran. `idx` here is `total - 1` (or,
            # when `start_index == total`, the loop body never ran at all
            # and `idx` still holds its initial `start_index` value -- see
            # the `total == start_index` short-circuit note below).
            self._receipts.write_checkpoint(
                operation_id,
                workspace_id=workspace_id,
                status="converged",
                next_action_index=None,
                completed_action_count=total,
                total_action_count=total,
                non_cancelable=False,
            )
            outcome = self._receipts.finalize_terminal_receipt(
                operation_id,
                workspace_id=workspace_id,
                operation_kind=operation_kind,
                expected_action_count=total,
                status="completed",
                audit_actor_user_id=audit_actor_user_id,
            )
            return ExecutionOutcome("completed", outcome.receipt, total)

        # Loop `break`-ed due to a durable cancellation request observed at
        # the safe point before `actions[idx]` -- exactly `idx` actions
        # (indices `[0, idx)`) actually ran; zero of `actions[idx:]` did.
        self._receipts.write_checkpoint(
            operation_id,
            workspace_id=workspace_id,
            status="converged",
            next_action_index=None,
            completed_action_count=idx,
            total_action_count=total,
            non_cancelable=False,
        )
        outcome = self._receipts.finalize_terminal_receipt(
            operation_id,
            workspace_id=workspace_id,
            operation_kind=operation_kind,
            expected_action_count=idx,
            status="canceled",
            audit_actor_user_id=audit_actor_user_id,
        )
        return ExecutionOutcome("canceled", outcome.receipt, idx)

    # -- exact-retry-after-completion replay (scenario 2, wired end-to-end) -

    def run_or_replay(
        self,
        operation: OperationRecord,
        *,
        is_replay: bool,
        workspace_id: str,
        operation_kind: str,
        actions: Sequence[ActionSpec],
        attempt_ref: str,
        audit_actor_user_id: str | None = None,
    ) -> ExecutionOutcome:
        """The end-to-end entry point a `job.resume`/execution adapter
        calls after `OperatorOperationService.consume_and_create_operation`
        returns.

        When `is_replay` is `True` (the confirmation-consumption outcome
        was `"exact_replay"`, i.e. the exact SAME request was retried) AND
        `operation.operation_id` already has a persisted terminal receipt,
        this returns that EXACT receipt (`replayed=True`) -- zero new
        action/effect receipts are ever recorded, and `actions` is never
        invoked. This is scenario 2 ("exact retry after completion returns
        the same terminal receipt"), wired through the FULL entry surface
        rather than only proven at `finalize_terminal_receipt`'s own,
        lower-level idempotency (OPM-2.3's `test_finalize_terminal_receipt_
        is_idempotent`, which calls that method directly with the same
        arguments -- not the same thing as a caller re-presenting a
        confirmation and expecting zero re-execution).

        Otherwise (a brand-new operation, or an exact-replay of an
        operation whose execution had not yet finalized), resumes from
        `resolve_resume_point` -- covers both a fresh `"created"` operation
        (resume point `0`) and an exact-replay of a still-in-flight one
        (resume point wherever it last left off) with the SAME, single
        code path.
        """

        if is_replay:
            existing_terminal = self._receipts.load_terminal_receipt(operation.operation_id)
            if existing_terminal is not None:
                return ExecutionOutcome(
                    existing_terminal["status"],
                    existing_terminal,
                    existing_terminal["action_count_completed"],
                    replayed=True,
                )

        resume_point = self._receipts.resolve_resume_point(operation.operation_id)
        if resume_point.outcome != "ok":
            # Corrupt receipt state (scenario 8, extended to resume) --
            # refuse to execute anything further, and produce NO receipt
            # (a `finalize_terminal_receipt` call here could only be
            # WRONG: the real persisted row count is exactly what made
            # `resolve_resume_point` deny in the first place, so no
            # `expected_action_count` this method could supply would
            # reconcile cleanly). Unreachable for a freshly-created
            # operation's first call (zero persisted rows is trivially
            # contiguous) -- reachable only via an exact-replay of an
            # operation whose receipt state was corrupted out of band.
            return ExecutionOutcome("denied", None, 0)

        return self.run_actions(
            operation.operation_id,
            workspace_id=workspace_id,
            operation_kind=operation_kind,
            actions=actions,
            attempt_ref=attempt_ref,
            start_index=resume_point.next_action_index or 0,
            audit_actor_user_id=audit_actor_user_id,
        )

    # -- resume: fresh policy/confirmation + a NEW attempt (scenario 7/9) --

    def resume_operation(
        self,
        operation_id: str,
        *,
        identity: AuthIdentity | None,
        resume_ctx: policy.PolicyContext,
        resume_confirmation_id: str,
        resume_presented_token: str,
        resume_authorization: AuthorizationProof,
        actions: Sequence[ActionSpec],
        operation_kind: str,
        workspace_id: str,
        attempt_adapter: OperatorAttemptAdapter,
        attempt_provider: str,
        attempt_model_profile: str,
        attempt_request_kind: str,
        attempt_policy_snapshot: dict[str, Any],
        audit_actor_user_id: str | None = None,
    ) -> ResumeOutcome:
        """Resume `operation_id` under FRESH policy/confirmation and a NEW
        attempt (H3 scenario 7 + 9; design constraint: "Resume requires
        fresh authority").

        `resume_ctx`/`resume_confirmation_id`/`resume_presented_token`/
        `resume_authorization` MUST be for a FRESHLY minted and presented
        confirmation -- never the original operation's now-consumed one
        (DUR-1's one-time-consumption guarantee forbids reusing it, and
        `OperatorOperationService.consume_and_create_operation` would deny
        a stale one anyway). This method gates resume through the EXACT
        SAME `authorize_operation` + confirmation-CAS pipeline every other
        governed request uses -- if policy or effective sensitivity
        changed since the original operation was created, THIS fresh
        evaluation (not the original one) decides whether resume proceeds
        (scenario 9).

        Creates a NEW attempt via `attempt_adapter.create_attempt` (OPM-2.2)
        -- never a second, parallel attempt-minting path -- linked to the
        SAME `operation_id` being resumed.
        """

        if not isinstance(operation_id, str) or not operation_id:
            raise ValueError("resume_operation requires a non-empty operation_id")

        resume_op_outcome = self._operations.consume_and_create_operation(
            confirmation_id=resume_confirmation_id,
            presented_token=resume_presented_token,
            ctx=resume_ctx,
            authorization=resume_authorization,
        )
        if resume_op_outcome.outcome not in ("created", "exact_replay"):
            return ResumeOutcome("denied", resume_op_outcome.reason_code, None)

        try:
            self._operations.load_operation(operation_id, identity=identity)
        except KeyError:
            return ResumeOutcome("denied", "not_found", None)

        existing_terminal = self._receipts.load_terminal_receipt(operation_id)
        if existing_terminal is not None:
            return ResumeOutcome("already_terminal", None, existing_terminal)

        resume_point = self._receipts.resolve_resume_point(operation_id)
        if resume_point.outcome != "ok":
            return ResumeOutcome("denied", resume_point.reason_code, None)

        new_attempt = attempt_adapter.create_attempt(
            operation_id,
            attempt_provider,
            attempt_model_profile,
            attempt_request_kind,
            attempt_policy_snapshot,
            workspace_id=workspace_id,
            identity=identity,
        )

        execution = self.run_actions(
            operation_id,
            workspace_id=workspace_id,
            operation_kind=operation_kind,
            actions=actions,
            attempt_ref=new_attempt.attempt_id,
            start_index=resume_point.next_action_index or 0,
            audit_actor_user_id=audit_actor_user_id,
        )
        return ResumeOutcome(
            "resumed",
            None,
            execution.terminal_receipt,
            new_attempt=new_attempt,
            execution=execution,
        )
