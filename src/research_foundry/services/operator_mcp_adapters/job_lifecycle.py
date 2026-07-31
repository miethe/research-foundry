"""`job.status`, `job.cancel`, and `job.resume` Operator MCP adapters
(research-foundry-operator-mcp-v1 P3, OPM-3.4).

**"job" == "operator OPERATION", not an `AgentJobService` subprocess
record.** `target_kind="agent_job"` is `operator_mcp_policy`'s frozen
vocabulary term for "a governed unit of operator work" (a holdover from
before `agent_job_service.AgentJobService`'s subprocess spawn-model existed
as a separate concept) -- for all three kinds here, `target_ref` is the
`operation_id` of the target operation being polled/canceled/resumed, NEVER
a literal `AgentJobService` job id. This is proven, not assumed: see
`operator_cancel_resume_service._resume_ctx_binds_operation` (requires
`target.target_kind == "agent_job" and target.target_ref ==
operation.operation_id`) and every fixture in
`tests/unit/test_operator_cancel_resume_service.py` that builds a
`job.resume` context (`targets=(policy.TargetRef("agent_job",
operation_id),)`). Consequently this module never imports
`agent_job_service` at all -- there is structurally no way for it to reach
`AgentJobService.load_events` (unbounded full-file read) or
`list_staged_artifacts` (unbounded glob), the two defect-class examples the
P3 implementer contract calls out by name. `job.status`'s bounded read of
an in-flight operation's most-recent progress comes from
`OperatorAttemptAdapter.list_attempts_for_operation` (itself naturally
bounded by `MAX_ATTEMPTS_PER_OPERATION`, P2S-NB-9's bounded-attempts cap)
reading each attempt's own `AgentJob.status` enum value -- never its event
log.

**`job.status` bypasses `operator_mcp_adapters.base.run_pipeline`
entirely, by design.** `job.status` is the sole member of
`operator_mcp_policy.CONFIRMATION_NOT_REQUIRED_KINDS` -- "a bounded read
with no canonical effect" (P3 implementer contract). `base.run_pipeline`'s
non-dry-run path unconditionally calls
`OperatorOperationService.consume_and_create_operation`, which durably
persists an operation manifest for every kind it is asked to consume for.
Tracing that call for `job.status` empirically: `_consume_locked`
(`operator_operation_service.py:1222-1227`) does an unconditional
`SELECT record_json FROM confirmations WHERE confirmation_id = ?` BEFORE
ever consulting `ctx.operation_kind` -- for `job.status` (whose caller
correctly supplies `confirmation_record=None`/`presented_token=None`,
since `policy.verify_confirmation` short-circuits to `"accepted"` for
`CONFIRMATION_NOT_REQUIRED_KINDS` without reading either), that lookup
finds no row and returns `OperationOutcome("denied", "confirmation_missing",
None)` -- even though `authorize_operation` just returned `allowed=True`
for the exact same request one line earlier. Reaching for
`base.run_pipeline` for `job.status` would therefore ALWAYS deny with
`confirmation_missing`, and would durably persist an operation manifest
for a "kind with no canonical effect" on the one path where it doesn't.
Both are wrong for a bounded read. `invoke_status` below instead calls
`operator_operation_service.authorize_for_consumption` directly (the same
six-stage check `base.run_pipeline` uses, short-circuiting to an accepted
confirmation stage for this kind) and, on success, performs the bounded
read itself -- no manifest, no receipts, `OperatorAdapterResult.operation_id`
is always `None` for this kind (consistent with that field's own
docstring: "`None` ... for a pre-consumption denial ... and for every dry
run", extended here to "and for a kind that never consumes at all"). This
gap in `operator_operation_service`'s own `_consume_locked` (a
CONFIRMATION_NOT_REQUIRED_KINDS short-circuit exists in `policy.
verify_confirmation` but has no counterpart in `_consume_locked`'s own
confirmation-row lookup) is reported, not fixed here -- `_consume_locked`
is inside `operator_operation_service.py`, and this task's file-ownership
is scoped there to "bounded attempts only" (P2S-NB-9); widening it to a
second, unrelated fix is out of scope and risks the concurrent swarm-surface
leg's own edits to the same file.

**`job.cancel` and `job.resume` DO go through `base.run_pipeline`**,
exactly like `run_plan.py`'s worked example: build a `PolicyContext`, one
`ActionSpec`, an `action_manifest`, and a `build_result` callback, then
hand all four to `base.run_pipeline`. `job.cancel`'s action calls
`OperatorCancelResumeService.request_cancellation` (P2, OPM-2.4) against
the TARGET operation -- an idempotent, durable cancellation REQUEST (a
signal a separately-running `run_actions` loop for that operation checks
at its next safe point), not a synchronous kill.

**`job.resume`'s documented gap (NOT fixed here, same pattern as
`run_plan.py`'s own "replay result-recovery gap")**:
`OperatorCancelResumeService.resume_operation` (P2, OPM-2.4) is the
existing, tested mechanism for actually RE-EXECUTING a target operation's
remaining actions from its first incomplete index -- but it requires the
caller to supply that operation's ORIGINAL `actions: Sequence[ActionSpec]`
sequence. A generic `job.resume` adapter cannot reconstruct an arbitrary
target operation's actions from its persisted `input_payload` alone: doing
so correctly would require a cross-adapter re-dispatch registry (e.g.
`base.get_adapter(target_operation_kind)` exposing its own `actions`
sequence separately from `invoke()`, which no P3 adapter -- including
`run_plan.py` -- currently does; `invoke()` builds `actions` internally and
hands them straight to `run_pipeline`). Building that registry is a
substantially larger change than a "1 pt ... DTO adapter" task, is not
listed in this task's file ownership, and touches every other adapter
module (owned by a concurrent leg for the swarm surface). `invoke_resume`
below therefore performs the REAL, governed, bounded half of resume that
does not require it: full fresh authorization of the resume REQUEST itself
(confirmation, RBAC, workspace, sensitivity -- identical rigor to every
other governed request), an eligibility check (not already terminal, no
corrupt receipt state, via the existing `load_terminal_receipt`/
`resolve_resume_point` primitives), and provisioning of a fresh attempt via
`OperatorAttemptAdapter.create_attempt` (the SAME durable attempt-linking
mechanism `resume_operation` itself uses, and the exact call site P2S-NB-9's
bounded-attempts cap gates). It returns a bounded, HONEST result
(`"status": "resume_authorized"`, `"original_actions_reexecuted": False`)
rather than fabricating full re-execution. Wiring `job.resume` to actually
replay the target operation's original actions is flagged here as a
required P4/P5 follow-up (needs the cross-adapter action-registry seam
described above), not silently dropped.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services.operator_attempt_adapter import OperatorAttemptAdapter
from research_foundry.services.operator_cancel_resume_service import (
    ActionEffect,
    ActionSpec,
    ExecutionOutcome,
    OperatorCancelResumeService,
)
from research_foundry.services.operator_operation_service import (
    OperationStoreUnavailableError,
    OperatorOperationService,
    authorize_for_consumption,
)
from research_foundry.services.operator_receipt_service import OperatorReceiptService

from . import base

_logger = logging.getLogger(__name__)

__all__ = [
    "STATUS_OPERATION_KIND",
    "CANCEL_OPERATION_KIND",
    "RESUME_OPERATION_KIND",
    "invoke_status",
    "invoke_cancel",
    "invoke_resume",
    "JobStatusAdapter",
    "JobCancelAdapter",
    "JobResumeAdapter",
    "STATUS_ADAPTER",
    "CANCEL_ADAPTER",
    "RESUME_ADAPTER",
]

STATUS_OPERATION_KIND = "job.status"
CANCEL_OPERATION_KIND = "job.cancel"
RESUME_OPERATION_KIND = "job.resume"

#: See module docstring's opening paragraph -- `target_ref` is an
#: `operation_id`, never a literal `AgentJobService` job id.
_TARGET_KIND = "agent_job"


class _JobLifecycleActionError(RuntimeError):
    """Raised inside `job.cancel`/`job.resume`'s own `ActionSpec.run()` for
    a governed denial discovered mid-action (`request_cancellation` itself
    denied; the target operation is already terminal; or its receipt state
    is corrupt/non-contiguous). `OperatorCancelResumeService.run_actions`
    catches ANY exception raised from an action and converts it into a
    governed, bounded `ExecutionOutcome("failed", ...)` terminal receipt
    (`reason_code="internal_error"`, logged server-side with this
    exception's message; never a raw traceback reaching a caller) -- the
    SAME mechanism `run_plan.py`'s own module docstring documents
    (`NotFoundError` -> "run_or_replay's own action-failure handling turns
    into a governed 'failed' terminal outcome"). This class exists only so
    the server-side log line names the real cause distinctly from an
    unexpected internal error.
    """


def _operation_effective_sensitivity_of(manifest: Mapping[str, Any]) -> str:
    """Bounded, fail-closed extraction of a persisted operation manifest's
    OWN `effective_sensitivity` (P3 hardening pass, HIGH-2 defect fix).

    `operator_operation_service._build_operation_manifest` writes the
    ORIGINAL `ctx.effective_sensitivity` into the persisted manifest at BOTH
    a top-level `manifest["effective_sensitivity"]` field and a nested
    `manifest["operation"]["effective_sensitivity"]` duplicate
    (`operator_operation_service.py` ~:582/:594) -- this reads the
    top-level one, the SAME field `OperationRecord`'s own callers already
    treat as authoritative.

    Returns that value only when it is a `str` member of
    `policy.SENSITIVITY_LEVELS`; otherwise -- a missing/absent field, a
    non-string value, or an unknown label (a manifest this function did not
    itself produce could in principle carry any of these, e.g. K4-NB-3-style
    corruption that got past `OperationRecord.from_manifest`'s own
    subscripting) -- returns `SENSITIVITY_LEVELS[-1]` (`"client_sensitive"`,
    the STRICTEST label). This mirrors `policy.resolve_effective_
    sensitivity`'s own "unresolvable content is maximally sensitive"
    convention (`operator_mcp_policy.py`'s NEW-4 fix) -- the OPPOSITE
    fail-closed direction from `resolve_local_sensitivity_ceiling`'s own
    convention one module up (a ceiling is a GRANT of clearance and fails
    closed toward the LOOSEST-denying value; this is a DESCRIPTION of
    content risk and fails closed toward the STRICTEST-denying value).
    Never raises.
    """

    value = manifest.get("effective_sensitivity")
    if isinstance(value, str) and value in policy.SENSITIVITY_LEVELS:
        return value
    return policy.SENSITIVITY_LEVELS[-1]


def _resolve_operation_workspace(
    operation_id: str, paths: FoundryPaths
) -> tuple[str | None, str]:
    """Bounded, read-only, pre-`ctx` lookup of the target operation's
    owning workspace AND its own persisted `effective_sensitivity` -- a
    single indexed-by-primary-key SQLite row read via
    `OperatorOperationService.load_operation(identity=None)` (no workspace
    scoping applied at this unscoped read; the SAME "necessary before `ctx`
    exists" category of lookup `run_plan.py`'s own `_resolve_intent_
    sensitivity` performs, see that module's docstring's "Sensitivity
    resolution happens before authorization" section) -- required because
    both `PolicyContext.resolved_target_workspaces` AND
    `PolicyContext.effective_sensitivity` are constructor arguments, so both
    values must be known before `ctx` (and therefore identity) exists.

    Returns `(workspace_id, effective_sensitivity)`.

    **P3 hardening pass, HIGH-2 defect fix.** Previously every `invoke_*`
    call site in this module hardcoded `effective_sensitivity =
    policy.resolve_effective_sensitivity(None)` -- unconditionally the
    STRICTEST label (`"client_sensitive"`), regardless of what the TARGET
    operation actually contains, because these three kinds carry no content
    of their own to inspect. That judged a `job.status` poll of a `public`
    run identically to one of a `client_sensitive` run: under ANY locally
    configured ceiling below `client_sensitive`, 100% of `job.*` calls
    denied, with zero diagnostic signal (the denial is deliberately
    indistinguishable from `not_found`, per H6). The fix: derive the
    target's real sensitivity from its own persisted manifest (via
    `_operation_effective_sensitivity_of` above) instead of hardcoding the
    strictest possible label -- a `job.status` on a `public` operation is
    now judged against `public`, not against `client_sensitive`.

    Catches ONLY `KeyError` (`load_operation`'s own documented, exhaustive
    "genuinely missing, or -- not reachable here since `identity=None` --
    wrong workspace" contract) and returns `(None, SENSITIVITY_LEVELS[-1])`
    -- never a permissive workspace default, and the STRICTEST (not a
    permissive) sensitivity pairing for the missing case, fail-closed on
    both axes. `PolicyContext`'s own H3/H6 gate (`_check_identity_and_rbac`)
    denies on `resolved_target_workspaces` alone (via `workspace_id=None`)
    BEFORE `effective_sensitivity` is ever compared against a ceiling for a
    genuinely-missing/wrong-workspace operation, so the paired
    `SENSITIVITY_LEVELS[-1]` value is inert on that path -- present only so
    `PolicyContext.for_configured_operator` always receives a valid,
    non-`None` member of `SENSITIVITY_LEVELS` and never raises `ValueError`
    on this path.

    Deliberately does NOT catch `OperationStoreUnavailableError` -- a
    transient SQLite lock on the operations store is NOT "genuinely
    missing", and folding it into this function's `None` return would make
    it indistinguishable from a real absence, which the H3/H6 gate then
    reports as the SAME non-retryable `not_found` a permanently-missing
    operation gets. That is precisely the retry-contract defect
    `OperationStoreUnavailableError` exists to prevent (see its own
    docstring in `operator_operation_service.py`): a caller cannot tell
    "this will never exist" from "retry me" if both collapse to the same
    denial. `OperationStoreUnavailableError` is left to propagate to the
    caller; see `_resolve_operation_workspace_or_error` below, which every
    `invoke_*` function in this module calls INSTEAD of this function
    directly, specifically to convert that propagated exception into a
    bounded, retryable result rather than letting it cross this module's
    public surface raw.
    """

    try:
        record = OperatorOperationService(paths).load_operation(operation_id, identity=None)
    except KeyError:
        return None, policy.SENSITIVITY_LEVELS[-1]
    return record.workspace_id, _operation_effective_sensitivity_of(record.manifest)


def _resolve_operation_workspace_or_error(
    operation_id: str, paths: FoundryPaths, *, now: datetime | None
) -> tuple[str | None, str, base.OperatorAdapterResult | None]:
    """Thin wrapper `invoke_status`/`invoke_cancel`/`invoke_resume` ALL call
    instead of `_resolve_operation_workspace` directly -- the single place
    that converts a propagated `OperationStoreUnavailableError` into a
    bounded, retryable `internal_error` `OperatorAdapterResult`, the SAME
    shape `invoke_status`'s own `except Exception` boundary below produces
    for an in-body store failure. Centralized here (rather than duplicated
    in three `try/except` blocks) so the classification is made ONCE and
    applies identically to all three call sites -- see this module's P3
    contract report for why enumerating every call site mattered here.

    Returns `(workspace_id_or_None, effective_sensitivity, None)` on a
    normal resolution -- including a genuinely missing/wrong-workspace
    operation, which still resolves to `(None, SENSITIVITY_LEVELS[-1],
    None)` exactly as `_resolve_operation_workspace` itself documents -- or
    `(None, SENSITIVITY_LEVELS[-1], <bounded OperatorAdapterResult>)` when
    the operations store itself was unavailable, OR when the persisted
    operation record was unreadable for any OTHER reason (see the final
    `except Exception` below). Callers MUST check the third element and
    return it immediately rather than proceeding to build a `PolicyContext`
    with workspace/sensitivity values that were never actually resolved.
    (P3 hardening pass, HIGH-2 defect fix: the second element is new --
    see `_resolve_operation_workspace`'s own docstring for the full defect
    and remediation rationale; every `invoke_*` call site now uses THIS
    element instead of its own separate, hardcoded
    `policy.resolve_effective_sensitivity(None)` call.)

    Two DELIBERATELY DISTINCT bounded outcomes, never collapsed into one:
    `OperationStoreUnavailableError` (a transient SQLite lock) is
    `retryable=True` -- ask again later, it may succeed. Anything else
    (final `except Exception` -- e.g. `OperationRecord.from_manifest`'s
    bare `manifest["operation_id"]`/`manifest["workspace_id"]`
    subscripting raising `TypeError` on a corrupted, non-Mapping
    persisted manifest, K4-NB-3) is `retryable=False` -- a corrupt record
    will not fix itself on retry. Collapsing these two would repeat, one
    level up, the EXACT retry-contract mistake this task's own fix
    corrects at the `_resolve_operation_workspace` layer: two outcomes
    with opposite retry semantics reported as the same thing.

    This final `except Exception` is this module's OWN narrow, deliberate
    boundary (not a reintroduction of the blanket catch this task
    removed from `_resolve_operation_workspace` itself, which stays
    scoped to `KeyError` only) -- it exists SPECIFICALLY so that nothing
    `_resolve_operation_workspace`/`OperatorOperationService.load_operation`
    can raise ever crosses this module's public surface raw, at the one
    call site (before any `invoke_*` function's own `try:`) no other
    handler in this file covers. Logged at ERROR (a corrupt manifest is a
    real operational problem, unlike a transient lock's WARNING above),
    exception TYPE NAME only -- never `str(exc)`, matching this module's
    and `base.run_pipeline`'s own NEW-13 convention.
    """

    try:
        workspace_id, effective_sensitivity = _resolve_operation_workspace(operation_id, paths)
        return workspace_id, effective_sensitivity, None
    except OperationStoreUnavailableError as exc:
        _logger.warning(
            "operator_mcp_adapters.job_lifecycle: operations store unavailable while "
            "resolving target workspace for operation_id=%s (%s)",
            operation_id,
            type(exc).__name__,
        )
        decision = policy.PolicyDecision(False, "confirmation", "internal_error", retryable=True)
        return (
            None,
            policy.SENSITIVITY_LEVELS[-1],
            base.OperatorAdapterResult(ok=False, error=policy.build_error(decision, now=now)),
        )
    except Exception as exc:
        _logger.error(
            "operator_mcp_adapters.job_lifecycle: unexpected error resolving target "
            "workspace for operation_id=%s (%s)",
            operation_id,
            type(exc).__name__,
        )
        decision = policy.PolicyDecision(False, "confirmation", "internal_error", retryable=False)
        return (
            None,
            policy.SENSITIVITY_LEVELS[-1],
            base.OperatorAdapterResult(ok=False, error=policy.build_error(decision, now=now)),
        )


def _operation_kind_of(manifest: Mapping[str, Any]) -> Any:
    operation = manifest.get("operation")
    if isinstance(operation, Mapping):
        return operation.get("operation_kind")
    return None


# ---------------------------------------------------------------------------
# job.status -- bounded read, CONFIRMATION_NOT_REQUIRED_KINDS. See module
# docstring for why this bypasses base.run_pipeline entirely.
# ---------------------------------------------------------------------------


def invoke_status(
    *,
    operation_id: str,
    idempotency_key: str,
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
    operations: OperatorOperationService | None = None,
    receipts: OperatorReceiptService | None = None,
    attempts: OperatorAttemptAdapter | None = None,
) -> base.OperatorAdapterResult:
    """The `job.status` Operator MCP tool -- a bounded, single-record read
    of `operation_id`'s current lifecycle state.

    Deliberately accepts NO `identity`/`workspace_id`/`AuthIdentity`-shaped
    parameter anywhere -- identity is resolved structurally, exactly once,
    inside `policy.PolicyContext.for_configured_operator` (requirement 1 of
    the P3 implementer contract), the same as every other P3 adapter.

    Returns a FIXED, bounded field set (`operation_id`, `operation_kind`,
    `status`, `terminal`, plus a small number of count/id fields) -- there
    is deliberately no page-size/offset parameter anywhere in this
    function's signature or result shape, so the "no unbounded pages"
    defect class (AC OPM-3.4) cannot arise here: there are no pages.

    Also deliberately accepts NO `sensitivity_ceiling` parameter (P3
    hardening pass, H7 defect fix) -- see
    `operator_mcp_adapters.resolve_local_sensitivity_ceiling`'s own
    docstring for the full defect and remediation rationale; resolved
    structurally, the same way identity is resolved.
    """

    from . import resolve_local_sensitivity_ceiling  # lazy: see operator_mcp_adapters/__init__.py's own docstring -- avoids the circular import a module-level import back into the package would create

    resolved_paths = paths or FoundryPaths.discover()
    sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)
    owning_workspace, effective_sensitivity, store_error = _resolve_operation_workspace_or_error(
        operation_id, resolved_paths, now=now
    )
    if store_error is not None:
        return store_error

    input_payload: dict[str, Any] = {"operation_id": operation_id}

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=STATUS_OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling=sensitivity_ceiling,
        targets=(policy.TargetRef(target_kind=_TARGET_KIND, target_ref=operation_id),),
        resolved_target_workspaces=(owning_workspace,),
        input_payload=input_payload,
        paths=resolved_paths,
    )

    try:
        if dry_run:
            decision = policy.evaluate_policy(ctx, paths=resolved_paths)
            if decision.denied:
                return base.OperatorAdapterResult(ok=False, error=policy.build_error(decision, now=now))
            return base.OperatorAdapterResult(
                ok=True, result={"dry_run": True, "operation_kind": STATUS_OPERATION_KIND}
            )

        authorization = authorize_for_consumption(
            ctx,
            confirmation_record=None,
            presented_token=None,
            paths=resolved_paths,
            now=now,
        )
        decision = authorization.decision
        if not decision.allowed:
            return base.OperatorAdapterResult(ok=False, error=policy.build_error(decision, now=now))

        # ctx.identity is guaranteed non-None here -- see run_plan.py's/
        # base.py's identical assertion and rationale: a None identity
        # denies at the RBAC stage inside evaluate_policy, before
        # authorize_for_consumption could ever report `decision.allowed`.
        assert ctx.identity is not None, "invoke_status: ctx.identity must be resolved post-authorization"

        op_service = operations or OperatorOperationService(resolved_paths)
        receipt_service = receipts or OperatorReceiptService(resolved_paths)
        attempt_adapter = attempts or OperatorAttemptAdapter(resolved_paths)

        operation_record = op_service.load_operation(operation_id, identity=ctx.identity)
        operation_kind = _operation_kind_of(operation_record.manifest)

        terminal = receipt_service.load_terminal_receipt(operation_id, identity=ctx.identity)
        if terminal is not None:
            result: dict[str, Any] = {
                "operation_id": operation_id,
                "operation_kind": operation_kind,
                "status": terminal.get("status"),
                "terminal": True,
                "action_count_total": terminal.get("action_count_total"),
                "action_count_completed": terminal.get("action_count_completed"),
            }
            return base.OperatorAdapterResult(ok=True, result=result)

        # Not yet terminal -- the most recent attempt's own AgentJob.status
        # enum is the best-effort progress signal. Bounded by construction:
        # `list_attempts_for_operation` is naturally capped by
        # MAX_ATTEMPTS_PER_OPERATION (P2S-NB-9), and this reads only the
        # LATEST attempt's already-loaded `.status` field -- never
        # `load_events`/`list_staged_artifacts` (see module docstring).
        attempt_records = attempt_adapter.list_attempts_for_operation(operation_id, identity=ctx.identity)
        latest = attempt_records[-1] if attempt_records else None
        result = {
            "operation_id": operation_id,
            "operation_kind": operation_kind,
            "status": latest.job.status.value if latest is not None else "in_progress",
            "terminal": False,
            "latest_attempt_id": latest.attempt_id if latest is not None else None,
            "attempt_count": len(attempt_records),
        }
        return base.OperatorAdapterResult(ok=True, result=result)
    except KeyError:
        # Defense in depth only (mirrors base.run_pipeline's own layered
        # convention): by the time load_operation is reached,
        # resolved_target_workspaces already proved the workspace matches
        # at the RBAC stage, so this is not expected to fire in practice --
        # kept as a fail-closed backstop rather than assumed unreachable.
        decision = policy.PolicyDecision(False, "rbac", "not_found", retryable=False)
        return base.OperatorAdapterResult(ok=False, error=policy.build_error(decision, now=now))
    except Exception as exc:
        _logger.warning(
            "operator_mcp_adapters.job_lifecycle.invoke_status: internal_error (%s)",
            type(exc).__name__,
        )
        decision = policy.PolicyDecision(False, "confirmation", "internal_error", retryable=True)
        return base.OperatorAdapterResult(ok=False, error=policy.build_error(decision, now=now))


# ---------------------------------------------------------------------------
# job.cancel -- full base.run_pipeline, mirrors run_plan.py's shape.
# ---------------------------------------------------------------------------


def invoke_cancel(
    *,
    operation_id: str,
    idempotency_key: str,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
    operations: OperatorOperationService | None = None,
    cancel_resume: OperatorCancelResumeService | None = None,
) -> base.OperatorAdapterResult:
    """The `job.cancel` Operator MCP tool.

    Requests cancellation of `operation_id` (the TARGET operation) via
    `OperatorCancelResumeService.request_cancellation` -- a durable,
    idempotent REQUEST checked at the target operation's own next safe
    point (see that method's docstring), not a synchronous kill.

    Also deliberately accepts NO `sensitivity_ceiling` parameter (P3
    hardening pass, H7 defect fix) -- see
    `operator_mcp_adapters.resolve_local_sensitivity_ceiling`'s own
    docstring for the full defect and remediation rationale; resolved
    structurally, the same way identity is resolved.
    """

    from . import resolve_local_sensitivity_ceiling  # lazy: see operator_mcp_adapters/__init__.py's own docstring -- avoids the circular import a module-level import back into the package would create

    resolved_paths = paths or FoundryPaths.discover()
    sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)
    owning_workspace, effective_sensitivity, store_error = _resolve_operation_workspace_or_error(
        operation_id, resolved_paths, now=now
    )
    if store_error is not None:
        return store_error

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=CANCEL_OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling=sensitivity_ceiling,
        targets=(policy.TargetRef(target_kind=_TARGET_KIND, target_ref=operation_id),),
        resolved_target_workspaces=(owning_workspace,),
        input_payload={"operation_id": operation_id},
        paths=resolved_paths,
    )

    cancel_resume_service = cancel_resume or OperatorCancelResumeService(resolved_paths)

    def _run() -> ActionEffect:
        assert ctx.identity is not None
        outcome = cancel_resume_service.request_cancellation(
            operation_id,
            workspace_id=ctx.identity.workspace_id,
            requested_by=ctx.identity.user_id,
        )
        if outcome.outcome == "denied":
            raise _JobLifecycleActionError(
                f"job.cancel: request_cancellation denied ({outcome.reason_code}) "
                f"for target operation_id={operation_id}"
            )
        # effect_ref must match operator_mcp_receipt.schema.yaml's
        # bounded canonical-reference pattern (alnum/underscore/hyphen/
        # colon/dot only) and stay well under maxLength: 256 -- operation_id
        # is a short, already-pattern-safe canonical id.
        effect_ref = f"{CANCEL_OPERATION_KIND}:{operation_id}"
        return ActionEffect(
            effect_kind="job_cancellation_requested",
            effect_digest=hashlib.sha256(effect_ref.encode("utf-8")).hexdigest(),
            effect_ref=effect_ref,
        )

    def _build_result(execution: ExecutionOutcome) -> Mapping[str, Any]:
        return {
            "operation_id": operation_id,
            "target_operation_id": operation_id,
            "status": execution.status,
            "replayed": execution.replayed,
        }

    action_manifest: dict[str, Any] = {
        "adapter": CANCEL_OPERATION_KIND,
        "target_operation_id": operation_id,
    }

    return base.run_pipeline(
        ctx=ctx,
        confirmation_record=confirmation_record,
        presented_token=presented_token,
        action_manifest=action_manifest,
        actions=(ActionSpec(action_id="request_cancellation", run=_run),),
        build_result=_build_result,
        dry_run=dry_run,
        paths=resolved_paths,
        now=now,
        operations=operations,
        cancel_resume=cancel_resume_service,
    )


# ---------------------------------------------------------------------------
# job.resume -- full base.run_pipeline. See module docstring's "documented
# gap" section: this authorizes resume and provisions a fresh attempt; it
# does NOT re-execute the target operation's original actions.
# ---------------------------------------------------------------------------


def invoke_resume(
    *,
    operation_id: str,
    idempotency_key: str,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
    operations: OperatorOperationService | None = None,
    cancel_resume: OperatorCancelResumeService | None = None,
    receipts: OperatorReceiptService | None = None,
    attempts: OperatorAttemptAdapter | None = None,
) -> base.OperatorAdapterResult:
    """The `job.resume` Operator MCP tool. See module docstring's
    "documented gap" section for the precise, bounded scope of what this
    does and does not do.

    Also deliberately accepts NO `sensitivity_ceiling` parameter (P3
    hardening pass, H7 defect fix) -- see
    `operator_mcp_adapters.resolve_local_sensitivity_ceiling`'s own
    docstring for the full defect and remediation rationale; resolved
    structurally, the same way identity is resolved.
    """

    from . import resolve_local_sensitivity_ceiling  # lazy: see operator_mcp_adapters/__init__.py's own docstring -- avoids the circular import a module-level import back into the package would create

    resolved_paths = paths or FoundryPaths.discover()
    sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)
    owning_workspace, effective_sensitivity, store_error = _resolve_operation_workspace_or_error(
        operation_id, resolved_paths, now=now
    )
    if store_error is not None:
        return store_error

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=RESUME_OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling=sensitivity_ceiling,
        targets=(policy.TargetRef(target_kind=_TARGET_KIND, target_ref=operation_id),),
        resolved_target_workspaces=(owning_workspace,),
        input_payload={"operation_id": operation_id},
        paths=resolved_paths,
    )

    receipt_service = receipts or OperatorReceiptService(resolved_paths)
    attempt_adapter = attempts or OperatorAttemptAdapter(resolved_paths)
    op_service_for_action = operations or OperatorOperationService(resolved_paths)

    # Captures the provisioned attempt so `_build_result` can report it --
    # mirrors run_plan.py's own `captured` list pattern.
    captured: list[tuple[Any, int | None, Any]] = []

    def _run() -> ActionEffect:
        assert ctx.identity is not None

        existing_terminal = receipt_service.load_terminal_receipt(operation_id, identity=ctx.identity)
        if existing_terminal is not None:
            raise _JobLifecycleActionError(
                f"job.resume: target operation_id={operation_id} already has a "
                "terminal receipt -- nothing to resume"
            )

        resume_point = receipt_service.resolve_resume_point(operation_id, identity=ctx.identity)
        if resume_point.outcome != "ok":
            raise _JobLifecycleActionError(
                f"job.resume: resolve_resume_point denied ({resume_point.reason_code}) "
                f"for target operation_id={operation_id}"
            )

        target_operation = op_service_for_action.load_operation(operation_id, identity=ctx.identity)
        target_kind = _operation_kind_of(target_operation.manifest) or "unknown"

        # Bounded by P2S-NB-9's MAX_ATTEMPTS_PER_OPERATION cap -- raises
        # AttemptLimitExceededError (a plain RuntimeError subclass) once
        # exceeded, caught by the SAME run_actions boundary that catches
        # _JobLifecycleActionError above, converting it into the identical
        # governed "failed" outcome. Never an infinite retry, never a
        # silent success.
        new_attempt = attempt_adapter.create_attempt(
            operation_id,
            "operator_mcp",
            "n/a",
            f"resume:{target_kind}",
            {"resumed_operation_id": operation_id},
            workspace_id=ctx.identity.workspace_id,
            identity=ctx.identity,
        )
        captured.append((new_attempt, resume_point.next_action_index, target_kind))

        effect_ref = f"{RESUME_OPERATION_KIND}:{operation_id}:{new_attempt.attempt_id}"
        return ActionEffect(
            effect_kind="job_resume_attempt_created",
            effect_digest=hashlib.sha256(effect_ref.encode("utf-8")).hexdigest(),
            effect_ref=effect_ref,
        )

    def _build_result(execution: ExecutionOutcome) -> Mapping[str, Any]:
        if execution.status == "completed" and captured:
            new_attempt, next_action_index, target_kind = captured[0]
            return {
                "operation_id": operation_id,
                "target_operation_kind": target_kind,
                "status": "resume_authorized",
                "new_attempt_id": new_attempt.attempt_id,
                "resume_point_action_index": next_action_index,
                # See module docstring's "documented gap" section.
                "original_actions_reexecuted": False,
            }
        if execution.status == "completed":
            # Exact replay of an already-terminal job.resume REQUEST itself
            # (the resume request's OWN confirmation was replayed) -- the
            # action never re-ran, mirrors run_plan.py's own replay branch.
            return {"operation_id": operation_id, "status": "resume_authorized", "replayed": True}
        return {"operation_id": operation_id, "status": execution.status, "replayed": execution.replayed}

    action_manifest: dict[str, Any] = {
        "adapter": RESUME_OPERATION_KIND,
        "target_operation_id": operation_id,
    }

    return base.run_pipeline(
        ctx=ctx,
        confirmation_record=confirmation_record,
        presented_token=presented_token,
        action_manifest=action_manifest,
        actions=(ActionSpec(action_id="authorize_and_provision_resume_attempt", run=_run),),
        build_result=_build_result,
        dry_run=dry_run,
        paths=resolved_paths,
        now=now,
        operations=operations,
        cancel_resume=cancel_resume,
    )


# ---------------------------------------------------------------------------
# base.OperatorAdapter Protocol implementations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class JobStatusAdapter:
    """`base.OperatorAdapter` Protocol implementation for `job.status`."""

    operation_kind: str = STATUS_OPERATION_KIND

    def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:
        return invoke_status(**kwargs)


@dataclass(frozen=True)
class JobCancelAdapter:
    """`base.OperatorAdapter` Protocol implementation for `job.cancel`."""

    operation_kind: str = CANCEL_OPERATION_KIND

    def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:
        return invoke_cancel(**kwargs)


@dataclass(frozen=True)
class JobResumeAdapter:
    """`base.OperatorAdapter` Protocol implementation for `job.resume`."""

    operation_kind: str = RESUME_OPERATION_KIND

    def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:
        return invoke_resume(**kwargs)


STATUS_ADAPTER = JobStatusAdapter()
CANCEL_ADAPTER = JobCancelAdapter()
RESUME_ADAPTER = JobResumeAdapter()
base.register(STATUS_ADAPTER)
base.register(CANCEL_ADAPTER)
base.register(RESUME_ADAPTER)
