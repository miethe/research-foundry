"""Operator MCP adapter substrate (research-foundry-operator-mcp-v1 P3, OPM-3.1).

This module is the ONE seam every P3 operation-kind adapter (`run.plan`,
`swarm.start`, `job.status`, `job.cancel`, `job.resume`) builds on. It owns:

* the adapter registry (:func:`register`/:func:`get_adapter`/:func:`all_adapters`
  -- keyed by `operation_kind`, mirroring the SHAPE of the unrelated discovery-
  adapter registry in `research_foundry/adapters/base.py`, never importing
  from it: that registry is for external research tools, this one is for
  Operator MCP operation kinds, and they must stay disjoint concepts);
* the bounded result envelope every adapter returns
  (:class:`OperatorAdapterResult`);
* :func:`run_pipeline`, the ONE authorize -> consume -> execute -> bounded-
  result sequence, in the FIXED order the P3 implementer contract requires:

      resolve identity (folded into `ctx` by
      `operator_mcp_policy.PolicyContext.for_configured_operator` before
      `ctx` ever reaches this function)
      -> resolve effective sensitivity (likewise folded into `ctx`)
      -> `authorize_operation` (via `operator_operation_service.
         authorize_for_consumption`, WITH the confirmation token)
      -> `consume_and_create_operation`
      -> execute via `run_or_replay` (which itself records action/effect
         receipts and finalizes the terminal receipt for every action it
         runs -- this substrate never calls those three individually)
      -> a bounded result: `build_result(execution)` on success, or
         `operator_mcp_policy.build_error` on ANY denial.

Hard invariants this module enforces for every caller (P3 implementer
contract, "Required properties of the substrate"):

1. **No caller-supplied identity anywhere.** Nothing in this module's public
   surface accepts an `AuthIdentity` or an identity-shaped mapping. The
   `ctx: PolicyContext` parameter :func:`run_pipeline` takes was ALREADY
   built via `PolicyContext.for_configured_operator` -- the only way to
   obtain a `ctx` whose `identity` is populated -- by the caller, before
   `run_pipeline` is ever invoked. (Finding NEW-18 recurred once because a
   *delegate* still accepted a caller identity; every function this module
   exports was enumerated against that failure mode -- none accepts one.)
2. **Fixed pipeline order**, never reordered per call site -- see above.
   Authorization (`authorize_for_consumption`) always runs before this
   module opens any durable connection or executes any action.
3. **Every denial returned to a caller is built by
   `operator_mcp_policy.build_error`.** No raw `str(exc)`, no traceback, no
   unbounded `detail` -- the single `except Exception` boundary in
   :func:`run_pipeline` logs only the exception's TYPE NAME (the NEW-13
   convention every other module in this family follows) and returns a
   closed `internal_error` denial built the same way as every other one.
4. **Dry run produces zero effects.** See :func:`run_pipeline`'s own
   docstring for the exact boundary.
5. **No fail-open default.** `get_adapter` returns `None` for an
   unregistered kind (never a default adapter); `register` refuses to
   register under a kind outside the closed `OPERATION_KINDS` enum; every
   branch in `run_pipeline` either returns a real result for a real
   terminal outcome or a `build_error`-shaped denial -- there is no
   fallthrough that returns `ok=True` without one of those two.
6. **No CLI / Typer / `subprocess` import, directly or transitively.** This
   module imports only `operator_mcp_policy`, the three P2
   `operator_*_service` modules, and `research_foundry.paths` -- none of
   which import a CLI framework or shell out.
7. **Imports cleanly without the `[serve]` extra** (fastapi/uvicorn absent).
   Every module this file imports already satisfies that boundary (P1's
   NEW-23 for `operator_mcp_policy`; the three P2 `operator_*_service`
   modules import `research_foundry.auth_identity`, never
   `api.auth.provider`, at module level) -- this module adds no import that
   would regress it. See `tests/unit/test_operator_mcp_adapter_base.py`'s
   own subprocess-blocked boundary test, which extends the existing
   `tests/unit/test_operator_mcp_serve_extra_boundary.py` pattern.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services.operator_cancel_resume_service import (
    ActionSpec,
    ExecutionOutcome,
    OperatorCancelResumeService,
)
from research_foundry.services.operator_operation_service import (
    OperationOutcome,
    OperatorOperationService,
    authorize_for_consumption,
)

_logger = logging.getLogger(__name__)

__all__ = [
    "OperatorAdapterResult",
    "OperatorAdapter",
    "SupportsActionManifest",
    "register",
    "get_adapter",
    "all_adapters",
    "run_pipeline",
    "get_action_manifest",
]


@dataclass(frozen=True)
class OperatorAdapterResult:
    """Bounded outcome returned by every Operator MCP adapter's `invoke`.

    Exactly one of (`result`, `error`) is meaningful, gated by `ok`:

    `ok=True`: `result` is the adapter's own JSON-safe, canonical result
    payload (e.g. `run.plan`'s four artifact refs). `error` is always
    `None`.

    `ok=False`: `result` is always `None` and `error` is a schema-valid
    `operator_mcp_error` envelope built EXCLUSIVELY by
    `operator_mcp_policy.build_error` (requirement 3) -- never a raw
    exception, never `str(exc)`, never hand-assembled here.

    `operation_id` is populated only once an operation manifest was
    actually durably persisted (`consume_and_create_operation` returned
    `"created"` or `"exact_replay"`); it is `None` for a pre-consumption
    denial (capability/rbac/audit_health/guard/preflight/confirmation) and
    for every dry-run result, since dry run never consumes a confirmation
    or creates a manifest.
    """

    ok: bool
    operation_id: str | None = None
    result: Mapping[str, Any] | None = None
    error: Mapping[str, Any] | None = None


@runtime_checkable
class OperatorAdapter(Protocol):
    """Shape every P3 operation-kind adapter module exposes.

    `operation_kind` MUST be a member of `operator_mcp_policy.OPERATION_KINDS`
    (enforced by :func:`register`, not merely documented here). `invoke`'s
    own keyword-only signature is operation-kind-specific -- a `run.plan`
    adapter's request shape (`intent_id`, `depth`, ...) differs from a
    `swarm.start` adapter's, so this Protocol intentionally does not
    constrain it beyond "callable, returns an `OperatorAdapterResult`".
    There is deliberately no MCP transport or tool-dispatch server in this
    phase (P5 scope) -- this Protocol is what that future dispatcher will
    call by `operation_kind`, nothing more.
    """

    operation_kind: str

    def invoke(self, **kwargs: Any) -> "OperatorAdapterResult": ...


@runtime_checkable
class SupportsActionManifest(Protocol):
    """OPTIONAL capability an `OperatorAdapter` MAY implement ALONGSIDE
    `invoke()` -- exposing the SAME ordered `ActionSpec` sequence `invoke()`
    hands to :func:`run_pipeline`, WITHOUT authorizing, consuming, or
    executing anything.

    **What this closes.** `job_lifecycle.py`'s own module docstring names
    the exact gap this seam exists for: a generic `job.resume` adapter
    cannot reconstruct an arbitrary TARGET operation's `actions` sequence
    from its persisted `input_payload` alone, because every P3 adapter's
    `invoke()` builds `actions` internally and hands them straight to
    `run_pipeline` -- there was previously no way for one adapter to ask
    another "what would you run, in what order, if invoked with these
    arguments" without actually invoking it. `SupportsActionManifest` is
    that ask, nothing more. Wiring `job.resume` to actually consume this
    seam and replay a target operation's original actions is explicitly
    OUT OF SCOPE for this seam itself -- see :func:`get_action_manifest`'s
    own docstring.

    **What this is NOT.** A SEPARATE Protocol from `OperatorAdapter`, never
    a required method added to it -- adding a required method to
    `OperatorAdapter` would break every adapter owned by a concurrent leg
    that does not implement this capability. `get_action_manifest` MUST
    NOT call `authorize_for_consumption`, `consume_and_create_operation`,
    or `run_or_replay` (directly or transitively) -- descriptor
    construction only, no authorize, no consume, no execute. `ActionSpec.
    run` closures are themselves side-effect-free to CONSTRUCT (the side
    effect happens only when `run()` is later INVOKED by `run_or_replay`
    inside `run_pipeline`'s own non-dry-run path), so a conforming
    implementation can build and return the real closures without running
    any of them -- see `job_lifecycle.JobCancelAdapter.get_action_manifest`
    for a worked example, which shares a single `_build_cancel_actions`
    helper with `invoke_cancel` so the two sequences are IDENTICAL by
    construction, never merely by convention.

    `operation_kind` mirrors `OperatorAdapter.operation_kind` (an
    implementer satisfies both Protocols with the SAME dataclass field, as
    `JobCancelAdapter` does) -- restated on this Protocol only so
    `isinstance(adapter, SupportsActionManifest)` alone is sufficient to
    confirm the capability without also checking `OperatorAdapter`.
    """

    operation_kind: str

    def get_action_manifest(self, **kwargs: Any) -> Sequence[ActionSpec]: ...


_REGISTRY: dict[str, OperatorAdapter] = {}


def register(adapter: OperatorAdapter) -> OperatorAdapter:
    """Register `adapter` under its own `operation_kind` (idempotent -- a
    second registration for the same kind REPLACES the first, exactly like
    `research_foundry/adapters/base.py`'s own discovery-adapter registry --
    a DIFFERENT registry this substrate deliberately mirrors the shape of,
    never imports from).

    Raises `ValueError` if `adapter.operation_kind` is not a member of
    `operator_mcp_policy.OPERATION_KINDS` -- registering under an unknown
    kind would let :func:`get_adapter` return something for a lookup key no
    legitimate dispatcher could ever produce (every real dispatch key is
    itself checked against the SAME closed enum first), silently widening
    the closed operation surface (requirement 5, no fail-open).
    """

    if adapter.operation_kind not in policy.OPERATION_KINDS:
        raise ValueError(
            "operator_mcp_adapters.base.register: unknown operation_kind "
            f"{adapter.operation_kind!r} -- must be one of {policy.OPERATION_KINDS!r}"
        )
    _REGISTRY[adapter.operation_kind] = adapter
    return adapter


def get_adapter(operation_kind: str) -> OperatorAdapter | None:
    """`None` for an unregistered `operation_kind` -- callers MUST treat
    `None` as "deny, no such adapter", never fall back to a default
    adapter or to whatever adapter happens to be registered (requirement
    5)."""

    return _REGISTRY.get(operation_kind)


def all_adapters() -> dict[str, OperatorAdapter]:
    """A shallow copy of the registry -- callers cannot mutate the real
    one through the returned dict."""

    return dict(_REGISTRY)


def get_action_manifest(adapter: OperatorAdapter, /, **kwargs: Any) -> Sequence[ActionSpec] | None:
    """`adapter.get_action_manifest(**kwargs)` when `adapter` implements the
    OPTIONAL `SupportsActionManifest` capability (checked via `isinstance`,
    `runtime_checkable`'s structural check), else `None` for an adapter that
    does not implement it -- `None` here is "this adapter has no manifest
    accessor", the SAME no-fail-open convention `get_adapter` already uses
    for "not registered" (requirement 5), never a default/empty sequence
    that could be mistaken for a real, zero-action manifest.

    Never authorizes, consumes, or executes anything itself -- a thin
    capability-check-and-delegate, not a second pipeline. Does NOT wire
    `job.resume`'s re-execution gap (see `SupportsActionManifest`'s own
    docstring and `job_lifecycle.py`'s module docstring's "documented gap"
    section) -- this function is the seam a future `job.resume` fix would
    call `base.get_action_manifest(base.get_adapter(target_kind), **target_
    kwargs)` through; that wiring is explicitly NOT done here.
    """

    if not isinstance(adapter, SupportsActionManifest):
        return None
    return adapter.get_action_manifest(**kwargs)


def _denial(reason_code: str, *, retryable: bool = False, stage: str = "confirmation") -> policy.PolicyDecision:
    """Build a `PolicyDecision`-shaped denial for a reason this substrate
    itself determined (never echoing caller-supplied text) -- the ONLY
    input `operator_mcp_policy.build_error` accepts. `reason_code` MUST
    already be a member of `operator_mcp_policy.CLOSED_REASON_CODES`;
    `build_error` itself raises `ValueError` if it is not, which is the
    correct failure mode for a programming error in THIS module rather than
    silently swallowing an unknown code."""

    return policy.PolicyDecision(False, stage, reason_code, retryable=retryable)


def run_pipeline(
    *,
    ctx: policy.PolicyContext,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    action_manifest: Mapping[str, Any],
    actions: Sequence[ActionSpec],
    build_result: Callable[[ExecutionOutcome], Mapping[str, Any]],
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
    operations: OperatorOperationService | None = None,
    cancel_resume: OperatorCancelResumeService | None = None,
    attempt_ref: str | None = None,
    audit_actor_user_id: str | None = None,
) -> OperatorAdapterResult:
    """The ONE authorize -> consume -> execute -> bounded-result sequence
    every P3 adapter's `invoke` calls after building its own `ctx` (via
    `PolicyContext.for_configured_operator`), `actions` (the
    `ActionSpec` sequence its operation performs), `action_manifest` (a
    small, adapter-owned descriptive dict persisted durably as part of the
    operation manifest), and `build_result` (a callback turning a
    successful `ExecutionOutcome` into the adapter's own JSON-safe result
    payload).

    **Dry run (requirement 4 -- zero effects)**: when `dry_run=True`, this
    function runs ONLY `operator_mcp_policy.evaluate_policy` (the five
    non-confirmation stages: capability, RBAC, audit-health, guard,
    preflight) and returns immediately -- `confirmation_record`/
    `presented_token` are never inspected, `authorize_for_consumption`,
    `consume_and_create_operation`, and `run_or_replay` are never called.
    No operation manifest, no action/effect/terminal receipt, and no
    adapter-specific artifact (e.g. `run.plan`'s planned run directory) is
    ever written on this path -- `actions` is never invoked (see
    `tests/unit/test_operator_mcp_adapter_base.py`'s spy-based proof, not
    mere inspection). The only disk activity `evaluate_policy` itself
    performs for a confirmation-requiring kind is `audit_service.
    health_check`'s own self-cleaning write-then-read-then-delete probe --
    an `operator_mcp_policy`-owned invariant that runs on EVERY such
    evaluation, dry run or not (see that module's docstring); it is not a
    governed manifest/receipt/artifact write this substrate owns.

    **Authorization precedes any lookup of the target (requirement 2)**:
    `authorize_for_consumption` is the FIRST thing this function does on
    the non-dry-run path, before any durable connection is opened and
    before `actions` can ever run.

    **No fail-open (requirement 5)**: every return in this function is
    either `ok=True` with a `build_result`-produced payload for a real
    `"completed"`/`"canceled"` terminal outcome, or `ok=False` with an
    `operator_mcp_policy.build_error`-built denial -- there is no other
    exit.
    """

    try:
        if dry_run:
            decision = policy.evaluate_policy(ctx, paths=paths)
            if decision.denied:
                return OperatorAdapterResult(ok=False, error=policy.build_error(decision, now=now))
            return OperatorAdapterResult(
                ok=True, result={"dry_run": True, "operation_kind": ctx.operation_kind}
            )

        authorization = authorize_for_consumption(
            ctx,
            confirmation_record=confirmation_record,
            presented_token=presented_token,
            paths=paths,
            now=now,
        )
        if authorization.decision.stage != "confirmation":
            # Denied at capability/RBAC/audit-health/guard/preflight --
            # never reached the confirmation stage. Propagate that stage's
            # own decision verbatim; there is no operation to consume.
            return OperatorAdapterResult(
                ok=False, error=policy.build_error(authorization.decision, now=now)
            )

        resolved_paths = paths or FoundryPaths.discover()
        op_service = operations or OperatorOperationService(resolved_paths)
        confirmation_id = (
            str(confirmation_record.get("confirmation_id", ""))
            if confirmation_record is not None
            else ""
        )
        outcome: OperationOutcome = op_service.consume_and_create_operation(
            confirmation_id=confirmation_id,
            presented_token=presented_token or "",
            ctx=ctx,
            authorization=authorization,
            action_manifest=action_manifest,
        )

        if outcome.outcome == "denied":
            reason = outcome.reason_code or "internal_error"
            return OperatorAdapterResult(
                ok=False,
                error=policy.build_error(
                    _denial(reason, retryable=(reason == "internal_error")), now=now
                ),
            )
        if outcome.outcome == "idempotency_conflict":
            return OperatorAdapterResult(
                ok=False,
                error=policy.build_error(_denial("idempotency_conflict"), now=now),
            )
        if outcome.operation is None:  # pragma: no cover - defense in depth, see OperationOutcome docstring
            return OperatorAdapterResult(
                ok=False, error=policy.build_error(_denial("internal_error", retryable=True), now=now)
            )

        operation = outcome.operation
        cancel_resume_service = cancel_resume or OperatorCancelResumeService(
            resolved_paths, operations=op_service
        )
        # ctx.identity is guaranteed non-None here: a None identity denies
        # at the RBAC stage inside evaluate_policy, long before
        # consume_and_create_operation could ever return "created"/
        # "exact_replay" -- see operator_mcp_policy's NEW-18 Layer 3. Asserted
        # (not silently defaulted) because `run_or_replay`'s `identity`
        # parameter is non-Optional (NB-D, a carried P2 hardening pass that
        # landed CONCURRENTLY with this task in this same worktree -- see
        # this module's own P3 implementer report for the drift note): a
        # None here would be a genuine programming-error invariant
        # violation, not a normal denial path, so it is caught by the
        # surrounding `except Exception` boundary rather than silently
        # coerced into an empty-string identity.
        assert ctx.identity is not None, "run_pipeline: ctx.identity must be resolved post-authorization"
        execution: ExecutionOutcome = cancel_resume_service.run_or_replay(
            operation,
            is_replay=(outcome.outcome == "exact_replay"),
            identity=ctx.identity,
            operation_kind=ctx.operation_kind,
            actions=actions,
            attempt_ref=attempt_ref or f"{operation.operation_id}:attempt-1",
            audit_actor_user_id=audit_actor_user_id,
        )

        if execution.status in ("failed", "denied"):
            reason = None
            if execution.terminal_receipt is not None:
                reason = execution.terminal_receipt.get("denial_reason_code")
            return OperatorAdapterResult(
                ok=False,
                operation_id=operation.operation_id,
                error=policy.build_error(_denial(reason or "internal_error"), now=now),
            )

        return OperatorAdapterResult(
            ok=True, operation_id=operation.operation_id, result=build_result(execution)
        )
    except Exception as exc:
        # H8-style boundary (mirrors operator_mcp_policy.authorize_operation's
        # own convention): never let a raw exception cross this substrate's
        # public surface. Log only the exception TYPE NAME (NEW-13
        # convention) -- never str(exc), which could embed caller-influenced
        # data.
        _logger.warning(
            "operator_mcp_adapters.base.run_pipeline: internal_error (%s)", type(exc).__name__
        )
        return OperatorAdapterResult(
            ok=False, error=policy.build_error(_denial("internal_error", retryable=True), now=now)
        )
