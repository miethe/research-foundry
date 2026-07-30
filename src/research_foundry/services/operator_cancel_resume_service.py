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

import json
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

    `outcome`:
        `"created"`
            The first request against `operation_id` (by a caller whose
            `workspace_id` matches the operation's own).
        `"exact_replay"`
            Idempotent -- a later request against the SAME `operation_id`
            (workspace already proven to match) resolves to the FIRST
            persisted request, never a second row.
        `"denied"`
            `operation_id` does not exist, or exists in a DIFFERENT
            workspace than the caller-supplied `workspace_id` (P2S-BLOCK-5)
            -- the two cases are INDISTINGUISHABLE (`reason_code ==
            "not_found"` for both), and ZERO rows are ever written. See
            :meth:`request_cancellation`'s docstring for why this is a
            hard denial rather than "derive and proceed" (unlike
            `write_checkpoint`/`finalize_terminal_receipt`'s own
            derive-and-correct pattern): the cancellation row is
            IRREVOCABLE once created, so the write itself must be
            workspace-AUTHORIZED, not merely workspace-attributed.
    """

    outcome: Literal["created", "exact_replay", "denied"]
    operation_id: str
    requested_at: str | None
    requested_by: str | None
    reason_code: str | None = None


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
# R1/R2 hardening: binding `resume_ctx` (and the workspace/operation_kind it
# implies) to the REAL operation being resumed, as a DATA DEPENDENCY rather
# than caller convention -- mirrors `AuthorizationProof`'s own closing of F1
# in `operator_operation_service.py` (a public method reaching durable state
# whose precondition was enforced only by convention/docstring).
#
# Prior to this, `resume_operation` discarded `load_operation`'s return
# value (called only for its raise-on-missing/wrong-workspace side effect)
# and threaded `workspace_id`/`operation_kind` straight from caller
# parameters into `write_checkpoint`/`finalize_terminal_receipt`, whose
# `workspace_id` columns back `idx_checkpoints_workspace`/
# `idx_terminal_receipts_workspace`. Neither `resume_ctx`'s own
# `effective_sensitivity`/`targets` nor the caller-supplied `workspace_id`/
# `operation_kind` were ever compared to the manifest `load_operation` just
# proved exists -- so a `resume_ctx` that legitimately cleared confirmation/
# RBAC/audit-health/guard/preflight FOR ITSELF could still be presented
# against an unrelated `operation_id` in the same workspace, and a
# mismatched `workspace_id` parameter could misattribute checkpoint/
# terminal-receipt rows across workspaces. Both are now DENIED, fail-closed,
# before any attempt is minted or receipt touched.
# ---------------------------------------------------------------------------


def _sensitivity_rank(label: str) -> int:
    """Rank lookup for a `PolicyContext.effective_sensitivity`-shaped label,
    fail-closed in the SAME direction as `operator_mcp_policy`'s own
    (module-private) `_sensitivity_rank`: an unrecognized label ranks
    STRICTER than every known level (`len(SENSITIVITY_LEVELS)`), so a
    corrupt/unknown value can never compare as "not weaker" against a real
    one. This is an intentional, narrow duplicate of that helper's
    convention -- not a reach into policy's private internals -- because
    `operator_mcp_policy.SENSITIVITY_LEVELS` (the public vocabulary tuple)
    is all this module needs."""

    try:
        return policy.SENSITIVITY_LEVELS.index(label)
    except ValueError:
        return len(policy.SENSITIVITY_LEVELS)


def _resume_ctx_binds_operation(
    resume_ctx: policy.PolicyContext, operation: OperationRecord
) -> bool:
    """R1: prove `resume_ctx` -- which `consume_and_create_operation` has
    only proven SELF-consistent -- actually corresponds to `operation`, the
    operation `resume_operation` is about to resume. Both checks are
    fail-closed (a missing/unrecognized value denies, never passes):

    * `resume_ctx.effective_sensitivity` must rank AT LEAST as strict as
      `operation`'s real, persisted `effective_sensitivity` -- a caller MAY
      present a context re-evaluated at an equal or STRICTER sensitivity
      (e.g. governance now ranks the operation more sensitive than it was
      at creation, and resume's fresh authorization pass correctly reflects
      that), but never a LAXER stand-in used to sidestep a guard/preflight
      rule that applies at the operation's real sensitivity.
    * `resume_ctx.targets` must contain the `agent_job` target that IS
      `operation.operation_id` -- the binding every caller (and this
      module's own tests) already followed by convention; this makes it a
      real data dependency instead of one caller could simply omit.
    """

    manifest_sensitivity = operation.manifest.get("effective_sensitivity")
    if not isinstance(manifest_sensitivity, str) or manifest_sensitivity not in policy.SENSITIVITY_LEVELS:
        return False
    if _sensitivity_rank(resume_ctx.effective_sensitivity) < _sensitivity_rank(manifest_sensitivity):
        return False

    return any(
        target.target_kind == "agent_job" and target.target_ref == operation.operation_id
        for target in resume_ctx.targets
    )


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

        Idempotent: a second (or Nth) call for the same `operation_id` (by
        a caller whose `workspace_id` matches) returns the FIRST persisted
        request unchanged (`"exact_replay"`) -- never a second row, never
        an exception. This is the durable fact :meth:`run_actions` checks
        at every safe point; it survives process loss because it lives in
        `paths.operator_operations_db`, not in any in-memory flag on this
        (or any) service instance.

        **P2S-BLOCK-5 (workspace-AUTHORIZED write, not merely workspace-
        attributed)**: before ANY row is written, `operation_id` is loaded
        and its REAL, persisted workspace is compared against the caller-
        supplied `workspace_id` -- a mismatch (or a genuinely missing
        `operation_id`) DENIES with `reason_code == "not_found"` for BOTH
        cases (indistinguishable, no derived detail leaked), and writes
        NOTHING. This is deliberately a hard DENIAL, not the "derive the
        real value and proceed" pattern `write_checkpoint`/
        `finalize_terminal_receipt` use (P2S-BLOCK-3): those methods are
        reached only after a caller has ALREADY been authorized to execute
        the operation whose receipt they are writing, so silently
        correcting a stale/wrong parameter there is safe. Cancellation is
        different -- `operation_id` is not a secret (it appears in every
        caller-visible envelope, log line, and receipt), so ANY caller
        presenting one must be independently proven to belong to the SAME
        workspace as the operation before a durable, IRREVOCABLE stop
        request can be created for it. Without this check, any holder of
        an `operation_id` could permanently and cross-workspace
        Denial-of-Service any operation's future execution -- see the P2
        security gate's P2S-BLOCK-5 finding for the full attack.

        **Rescindability (explicit decision, not a silent gap)**:
        `cancellation_requests` rows remain IMMUTABLE and irrevocable --
        this fix is authorization on the WRITE, not a new "un-cancel"
        capability. A cancellation, once durably recorded by an actor who
        legitimately holds this operation's workspace, permanently stops
        that operation's future execution; there is no retraction path in
        this design, matching every other closed, immutable governance
        record in this module family (`terminal_receipts`, `operations`
        manifests). The severity this finding actually raised was NEVER
        "cancellation is irrevocable" (a deliberate design property) -- it
        was "cancellation is irrevocable AND anyone could trigger it for
        anyone else's operation". Closing the authorization gap is the
        complete fix; adding rescindability would be a separate, unplanned
        feature this task does not require.
        """

        if not isinstance(operation_id, str) or not operation_id:
            raise ValueError("request_cancellation requires a non-empty operation_id")
        if not isinstance(workspace_id, str) or not workspace_id:
            raise ValueError("request_cancellation requires a non-empty workspace_id")

        try:
            operation = self._operations.load_operation(operation_id)
        except KeyError:
            _logger.error(
                "operator_cancel_resume_service: request_cancellation DENIED -- "
                "operation_id=%s does not exist",
                operation_id,
            )
            return CancellationOutcome("denied", operation_id, None, None, "not_found")

        if operation.workspace_id != workspace_id:
            _logger.error(
                json.dumps(
                    {
                        "event": "workspace_scope_enforced_denial",
                        "record_type": "cancellation_request",
                        "record_id": operation_id,
                        "record_workspace_id": operation.workspace_id,
                        "identity_workspace_id": workspace_id,
                    }
                )
            )
            return CancellationOutcome("denied", operation_id, None, None, "not_found")

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

    def cancellation_requested(
        self, operation_id: str, *, workspace_id: str | None = None
    ) -> bool:
        """Return whether a durable cancellation request exists for
        `operation_id` -- reads real persisted state, never an in-process
        flag.

        `workspace_id=None` (the default) performs no scoping -- safe
        because the primary DoS vector this read could otherwise surface
        (P2S-BLOCK-5) is now closed at the WRITE side by
        :meth:`request_cancellation`'s own workspace-authorization check;
        this parameter is defense-in-depth for a caller (like
        :meth:`run_actions`, which always supplies its own already-derived
        `workspace_id`) that wants the read scoped too.
        """

        conn = _ops_store._connect(self._paths)
        try:
            _ops_store._ensure_schema(conn)
            row = conn.execute(
                "SELECT workspace_id FROM cancellation_requests WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
        finally:
            conn.close()
        if row is None:
            return False
        if workspace_id is not None and row["workspace_id"] != workspace_id:
            _logger.error(
                json.dumps(
                    {
                        "event": "workspace_scope_enforced_denial",
                        "record_type": "cancellation_request",
                        "record_id": operation_id,
                        "record_workspace_id": row["workspace_id"],
                        "identity_workspace_id": workspace_id,
                    }
                )
            )
            return False
        return True

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
            if self.cancellation_requested(operation_id, workspace_id=workspace_id):
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
                if outcome.outcome == "denied":
                    # P2S-BLOCK-2: the outcome of `finalize_terminal_receipt`
                    # is CHECKED, never assumed successful -- mirrors the
                    # `record_action_receipt`/`record_effect_receipt` guards
                    # immediately above/below. A denied finalize means
                    # reconciliation itself found corrupt receipt state (e.g.
                    # an EXTRA receipt written out of turn) -- reporting
                    # "failed" with `outcome.receipt is None` would violate
                    # `ExecutionOutcome`'s own docstring contract and (the
                    # actual defect this closes) silently claim a status the
                    # store refused to durably record.
                    _logger.error(
                        "operator_cancel_resume_service: finalize_terminal_receipt "
                        "denied (%s) for operation_id=%s while finalizing a FAILED "
                        "action at index=%d -- reconciliation found corrupt "
                        "receipt state; reporting denied, not failed",
                        outcome.reason_code,
                        operation_id,
                        idx,
                    )
                    return ExecutionOutcome("denied", None, idx)
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
            if outcome.outcome == "denied":
                # P2S-BLOCK-2 -- THE fix: this is the exact bug the security
                # gate demonstrated (H3 scenario 8's EXTRA-receipt variant --
                # an out-of-turn action_receipt written after this loop
                # already ran every action it knew about). Before this
                # check, this branch unconditionally returned
                # `ExecutionOutcome("completed", outcome.receipt, total)`
                # even when `outcome.receipt is None`, fabricating a
                # "completed" status with no terminal receipt at all and a
                # `completed_action_count` that was never reconciled.
                _logger.error(
                    "operator_cancel_resume_service: finalize_terminal_receipt "
                    "denied (%s) for operation_id=%s while finalizing a "
                    "COMPLETED operation -- reconciliation found corrupt "
                    "receipt state (e.g. EXTRA); reporting denied, not "
                    "completed",
                    outcome.reason_code,
                    operation_id,
                )
                return ExecutionOutcome("denied", None, total)
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
        if outcome.outcome == "denied":
            # P2S-BLOCK-2, canceled branch's sibling.
            _logger.error(
                "operator_cancel_resume_service: finalize_terminal_receipt "
                "denied (%s) for operation_id=%s while finalizing a "
                "CANCELED operation -- reconciliation found corrupt receipt "
                "state; reporting denied, not canceled",
                outcome.reason_code,
                operation_id,
            )
            return ExecutionOutcome("denied", None, idx)
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

        R3 (checklist-item-2 sibling of R2, found by enumerating this
        module's public methods after R2 was fixed in `resume_operation`):
        `workspace_id`/`operation_kind` are DERIVED from `operation` --
        already the AUTHORITATIVE `OperationRecord` (only constructible
        from a persisted manifest: `OperationRecord.from_manifest` or
        `OperatorOperationService.load_operation`) -- never taken from the
        separately-supplied parameters. This is a SECOND, independent
        entrypoint into the SAME `write_checkpoint`/`finalize_terminal_
        receipt` calls whose `workspace_id` columns back `idx_checkpoints_
        workspace`/`idx_terminal_receipts_workspace`; trusting the
        parameters here would reach the identical unsafe behavior R2 closed
        in `resume_operation`, just through a different door.
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

        resume_point = self._receipts.resolve_resume_point(
            operation.operation_id, total_action_count=len(actions)
        )
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
            # P2S-BLOCK-2: `total_action_count=len(actions)` (this caller's
            # own declared action count) additionally catches the EXTRA
            # corruption class HERE, before any action is (re-)executed,
            # rather than only once `run_actions` reaches
            # `finalize_terminal_receipt` at the very end.
            return ExecutionOutcome("denied", None, 0)

        resolved_workspace_id = operation.workspace_id
        resolved_operation_kind = operation.manifest["operation"]["operation_kind"]
        if workspace_id != resolved_workspace_id or operation_kind != resolved_operation_kind:
            _logger.warning(
                "operator_cancel_resume_service.run_or_replay: caller-supplied "
                "workspace_id=%r/operation_kind=%r for operation_id=%s does not match "
                "operation.workspace_id=%r/the operation's own manifest operation_kind=%r "
                "-- using the operation's own values (R3 hardening)",
                workspace_id,
                operation_kind,
                operation.operation_id,
                resolved_workspace_id,
                resolved_operation_kind,
            )

        return self.run_actions(
            operation.operation_id,
            workspace_id=resolved_workspace_id,
            operation_kind=resolved_operation_kind,
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

        R1/R2 (see the module-level hardening block above
        :class:`OperatorCancelResumeService`): `resume_ctx` is proven to
        BIND to `operation_id` (:func:`_resume_ctx_binds_operation`) before
        anything else happens -- including before `already_terminal` is
        ever revealed, closing a side channel where a caller with only a
        self-consistent-but-unbound `resume_ctx` could learn whether an
        unrelated operation had already finished. `workspace_id` and
        `operation_kind` are then DERIVED from the just-loaded manifest,
        never taken from the caller's parameters, for every downstream
        write (`attempt_adapter.create_attempt`, `run_actions`).
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
            operation_record = self._operations.load_operation(operation_id, identity=identity)
        except KeyError:
            return ResumeOutcome("denied", "not_found", None)

        if not _resume_ctx_binds_operation(resume_ctx, operation_record):
            # R1: `resume_ctx` cleared confirmation/policy for ITSELF, but
            # does not correspond to `operation_id` -- deny with the SAME
            # `"not_found"` code `load_operation` already uses for a
            # wrong-workspace lookup (H6's no-existence-leak convention): a
            # caller must never be able to distinguish "wrong operation_id"
            # / "wrong sensitivity" / "wrong target" from "operation not
            # found".
            _logger.error(
                "operator_cancel_resume_service.resume_operation: resume_ctx "
                "does not bind to operation_id=%s (resume_ctx.effective_sensitivity=%r, "
                "resume_ctx.targets=%r) -- denying (R1)",
                operation_id,
                resume_ctx.effective_sensitivity,
                [t.to_dict() for t in resume_ctx.targets],
            )
            return ResumeOutcome("denied", "not_found", None)

        # R2: derive workspace_id/operation_kind from the manifest just
        # loaded -- never trust the caller-supplied parameters, which back
        # `checkpoints`/`terminal_receipts`' own workspace-scoped indexes
        # (`idx_checkpoints_workspace`/`idx_terminal_receipts_workspace`).
        # Deriving (rather than requiring the parameters and denying on
        # mismatch) removes the fail-open entirely: no caller-suppliable
        # value can misattribute a row, because none is ever consulted for
        # that purpose again below. A mismatch is still logged -- it
        # indicates either a caller bug or a boundary probe worth knowing
        # about, even though it can no longer cause a wrong write.
        resolved_workspace_id = operation_record.workspace_id
        resolved_operation_kind = operation_record.manifest["operation"]["operation_kind"]
        if workspace_id != resolved_workspace_id or operation_kind != resolved_operation_kind:
            _logger.warning(
                "operator_cancel_resume_service.resume_operation: caller-supplied "
                "workspace_id=%r/operation_kind=%r for operation_id=%s does not match "
                "the manifest's workspace_id=%r/operation_kind=%r -- using the "
                "manifest's values (R2 hardening)",
                workspace_id,
                operation_kind,
                operation_id,
                resolved_workspace_id,
                resolved_operation_kind,
            )

        # P2S-BLOCK-3 (defense in depth, read side): `identity` is already
        # proven correct for `operation_id` by `load_operation`'s own
        # workspace scoping above -- threading it through these two reads
        # too costs nothing and means neither method depends SOLELY on
        # every OTHER caller getting this right.
        existing_terminal = self._receipts.load_terminal_receipt(operation_id, identity=identity)
        if existing_terminal is not None:
            return ResumeOutcome("already_terminal", None, existing_terminal)

        resume_point = self._receipts.resolve_resume_point(
            operation_id, identity=identity, total_action_count=len(actions)
        )
        if resume_point.outcome != "ok":
            return ResumeOutcome("denied", resume_point.reason_code, None)

        new_attempt = attempt_adapter.create_attempt(
            operation_id,
            attempt_provider,
            attempt_model_profile,
            attempt_request_kind,
            attempt_policy_snapshot,
            workspace_id=resolved_workspace_id,
            identity=identity,
        )

        execution = self.run_actions(
            operation_id,
            workspace_id=resolved_workspace_id,
            operation_kind=resolved_operation_kind,
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
