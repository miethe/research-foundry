"""`swarm.start` Operator MCP adapter (research-foundry-operator-mcp-v1 P3, OPM-3.3).

Wraps `research_foundry.services.swarm_service.run_swarm` behind the fixed
authorize -> consume -> execute -> bounded-result pipeline in
`operator_mcp_adapters.base.run_pipeline`, following the exact shape
`run_plan.py` established (OPM-3.1): build a `PolicyContext`, an `ActionSpec`
sequence, an `action_manifest`, and a `build_result` callback, then hand all
four to `base.run_pipeline`. This module never calls `swarm_service.get_adapter`
directly, never imports a CLI/Typer/subprocess path, and never dispatches a
discovery adapter any way other than through `swarm_service.run_swarm` --
requirement 1 of this task's brief.

**Per-adapter action decomposition (requirement 2).** Unlike `run.plan`
(exactly one action), this adapter builds ONE `ActionSpec` per element of
`adapter_ids`, each calling `swarm_service.run_swarm` with a SINGLE-element
list. This is deliberate, not incidental: `operator_cancel_resume_service.
OperatorCancelResumeService.run_actions` checks for a durable cancellation
request at a SAFE POINT before every action in the sequence -- decomposing
per adapter is what gives a cancellation request a safe point BETWEEN any
two adapters' dispatches, and gives each dispatch its own action/effect
receipt and checkpoint boundary (`run_actions` writes a checkpoint after
every action unconditionally, plus an additional pre-action checkpoint for
a `non_cancelable=True` action -- see `ActionSpec` below). A single action
wrapping the WHOLE `adapter_ids` list in one `run_swarm` call would satisfy
"call `run_swarm`" literally but would make the entire dispatch atomic and
cancelable only before the first adapter starts, which this task's brief
explicitly rules out ("each adapter dispatch is a distinct, receipted action
with a checkpoint boundary between them").

**Non-duplication (the hard AC, requirement 3).** `swarm_service.run_swarm`'s
own write path REPLACES `source_candidates.yaml` wholesale on every call --
correct for the CLI's single, all-adapters-at-once call, but wrong for N
separate per-adapter calls, where a naive loop would have each later call
silently erase every earlier action's already-persisted candidates. This
adapter always passes `merge_with_existing=True` (added to `run_swarm` in
THIS task, alongside the P3-F1 fix, for exactly this reason -- see that
function's own docstring): each action's write ADDS to whatever is already
durably on disk. Combined with `operator_cancel_resume_service`'s own,
already-existing, already-hardened guarantee that a completed action's
`run()` closure is NEVER re-invoked on resume (`run_actions` only ever
begins at `resolve_resume_point`'s `next_action_index`, reconstructed from
REAL persisted action/effect receipt rows, never from checkpoint alone or
any in-process state), this means: a genuinely interrupted-then-resumed
`swarm.start` operation runs each requested adapter's dispatch AT MOST ONCE,
system-wide, and its merge-write is the only write that can ever add that
adapter's candidates to the file -- no action can ever double-write, and no
action's candidates are ever lost by a LATER action's write. Proven in
`tests/unit/test_operator_mcp_adapter_swarm_start.py` with a real
interrupted-then-resumed fixture (adapted from `operator_cancel_resume_
service`'s own scenario-7 "process loss" idiom: real receipts durably
committed for a real completed dispatch, a fresh service instance computing
the SAME `resolve_resume_point`, `run_actions` continuing from there) that
asserts on the actual `source_candidates.yaml` content and count, not merely
on the guard being present.

Cancellation, in this substrate's actual vocabulary, is a durable, TERMINAL
fact -- `OperatorCancelResumeService.resume_operation` returns
`"already_terminal"` (zero re-execution) for an operation that already has a
persisted terminal receipt, canceled or completed alike. The only
interruption class from which THIS substrate can continue executing
remaining actions is process loss on an operation that never reached a
terminal receipt -- exactly what the test above exercises. This is a
documented judgment call about what "cancel/resume does not duplicate" means
operationally in a system where true cancellation is irrevocable by design
(see `operator_cancel_resume_service.py`'s own module docstring); this
module does not invent a second, parallel "resumable cancellation" concept.

**Resolved, never caller-supplied, governance inputs (requirement 5, no
fail-open).** Sensitivity, the target run's owning workspace, its governing
budget/timeout ceiling, and its governance (key) profile are ALL read-only
resolutions from the target run's OWN already-governed state -- `run.yaml`
(written once, durably, by `run.plan`) and, one hop further, its originating
intent's `governance.key_profile_allowed`. None of the five is a caller-
suppliable parameter to `invoke`: accepting a caller override for any of
them would let a `swarm.start` call silently escalate past whatever ceiling
`run.plan` originally established for this run. Sensitivity/workspace_id
resolve to `None` on failure and flow into `ctx` exactly like `run_plan.py`'s
own `_resolve_intent_sensitivity` pattern (`None` sensitivity resolves to
the STRICTEST label via `policy.resolve_effective_sensitivity`; a `None`
`resolved_target_workspaces` entry denies at the rbac stage per
`PolicyContext`'s own H3 handling -- both existing substrate mechanisms,
reused, not reinvented). Budget/timeout/governance-profile have NO
equivalent existing substrate-level gate (`PolicyContext` carries no budget/
timeout field at all), so THIS module adds one explicit, bounded preflight
check of its own (built via `operator_mcp_policy.build_error`, exactly like
every other denial in this family): any of the three resolving to `None`
denies with `preflight_failed` BEFORE `ctx` is even constructed -- never a
permissive numeric/string default synthesized here.

**Degraded adapters remain typed (requirement 4).** `swarm_service.run_swarm`
already guarantees this for an individual discovery adapter's own failure
(`AdapterOutcome.error` is a bounded `"ExceptionType: message"` string, never
a raised exception -- see that module). An unexpected exception escaping
THIS module's own action closures (e.g. a `swarm_service`/filesystem-layer
failure) is caught by `operator_cancel_resume_service.run_actions` itself
(its own `except Exception` around `spec.run()`), which records a typed
`"failed"` action receipt and finalizes a `"failed"` terminal receipt --
`base.run_pipeline` then turns that into a `build_error` envelope before
this module's own `_build_result` is ever reached. No path in this module
raises a raw exception to its own caller.

**Replay result-recovery gap (documented limitation, NOT fixed here, same
shape as `run_plan.py`'s own).** On a genuine exact-replay of an ALREADY-
terminal operation, none of this adapter's `ActionSpec.run()` closures are
invoked a second time, so `captured` (below) is empty and the per-adapter
breakdown cannot be reconstructed from durable operator-layer state alone
(`OperatorReceiptService` exposes no public reader for a persisted
`effect_ref` by `operation_id`/`action_id`). `_build_result` returns a
bounded, honest partial payload on that path (`"canonical_refs_available":
False`) rather than fabricating a breakdown -- same follow-up gap
`run_plan.py` already reports, not re-solved here (out of this task's file
ownership: `operator_receipt_service.py`).
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services import swarm_service as swarm_svc
from research_foundry.services.operator_cancel_resume_service import (
    ActionEffect,
    ActionSpec,
    ExecutionOutcome,
    OperatorCancelResumeService,
)
from research_foundry.services.operator_operation_service import OperatorOperationService
from research_foundry.yamlio import load_yaml

from . import base

_logger = logging.getLogger(__name__)

__all__ = ["OPERATION_KIND", "SwarmStartAdapter", "ADAPTER", "invoke"]

OPERATION_KIND = "swarm.start"


@dataclass(frozen=True)
class _RunContext:
    """Read-only, best-effort resolution of everything `swarm.start` needs
    from the target run's OWN already-governed state -- see module
    docstring's "resolved, never caller-supplied" section. Every field is
    `None` on ANY resolution failure (missing run, malformed `run.yaml`,
    missing/malformed originating intent, non-numeric budget/timeout) --
    `invoke` denies rather than defaulting for every one of them."""

    sensitivity: str | None
    workspace_id: str | None
    budget_usd: float | None
    timeout_minutes: int | None
    governance_profile: str | None


def _resolve_run_context(run_id: str, paths: FoundryPaths) -> _RunContext:
    """See `_RunContext`'s own docstring. Swallows EVERY exception at EVERY
    hop (`run.yaml` load, intent load) and resolves the corresponding
    field(s) to `None` on failure -- mirrors `run_plan._resolve_intent_
    sensitivity`'s own fail-closed convention, one hop further (`run.yaml`
    -> its own `intent_id` -> that intent's `governance.key_profile_allowed`)."""

    try:
        run_doc = load_yaml(paths.run_paths(run_id).run_yaml)
    except Exception as exc:
        _logger.warning(
            "operator_mcp_adapters.swarm_start: run.yaml lookup failed (%s) for "
            "run_id=%s -- resolving every run-context field to None (deny, never default)",
            type(exc).__name__,
            run_id,
        )
        return _RunContext(None, None, None, None, None)

    if not isinstance(run_doc, dict):
        return _RunContext(None, None, None, None, None)

    sensitivity = run_doc.get("sensitivity")
    sensitivity = sensitivity if isinstance(sensitivity, str) else None

    workspace_id = run_doc.get("workspace_id")
    workspace_id = workspace_id if isinstance(workspace_id, str) and workspace_id else None

    profile_block = run_doc.get("profile")
    profile_block = profile_block if isinstance(profile_block, dict) else {}
    raw_budget = profile_block.get("max_cost_usd")
    budget_usd = (
        float(raw_budget)
        if isinstance(raw_budget, (int, float)) and not isinstance(raw_budget, bool)
        else None
    )
    raw_timeout = profile_block.get("max_runtime_minutes")
    timeout_minutes = (
        int(raw_timeout)
        if isinstance(raw_timeout, (int, float)) and not isinstance(raw_timeout, bool)
        else None
    )

    governance_profile: str | None = None
    intent_id = run_doc.get("intent_id")
    if isinstance(intent_id, str) and intent_id:
        from research_foundry.services import planning  # lazy: see run_plan.py's own rationale

        try:
            intent = planning.load_intent(intent_id, paths=paths)
        except Exception as exc:
            _logger.warning(
                "operator_mcp_adapters.swarm_start: originating intent lookup failed "
                "(%s) for run_id=%s intent_id=%s -- governance_profile resolves to None",
                type(exc).__name__,
                run_id,
                intent_id,
            )
            intent = None
        governance = intent.get("governance") if isinstance(intent, dict) else None
        allowed = governance.get("key_profile_allowed") if isinstance(governance, dict) else None
        governance_profile = allowed if isinstance(allowed, str) else None

    return _RunContext(sensitivity, workspace_id, budget_usd, timeout_minutes, governance_profile)


def _preflight_denial(reason_code: str) -> policy.PolicyDecision:
    """Adapter-owned preflight denial, built the same shape `operator_mcp_
    policy._check_preflight`'s own denials use -- this module does not
    import that (private) helper or touch `operator_mcp_policy.py`; this is
    an independent, narrow duplicate of the same one-line construction, fed
    to the SAME `policy.build_error` every other denial in this family
    goes through."""

    return policy.PolicyDecision(False, "preflight", reason_code, retryable=True)


def _make_action(
    run_id: str,
    index: int,
    adapter_id: str,
    *,
    profile: str,
    paths: FoundryPaths,
    captured: list[swarm_svc.SwarmRunResult],
) -> ActionSpec:
    """Build ONE checkpointed, receipted action dispatching exactly
    `adapter_id` for `run_id` -- see module docstring's "per-adapter action
    decomposition" and "non-duplication" sections for why this is a
    MODULE-LEVEL function (reused identically by `invoke` and directly
    importable by `tests/unit/test_operator_mcp_adapter_swarm_start.py`'s
    own interrupted-then-resumed non-duplication fixture, which needs REAL
    `ActionSpec` objects outside of a full `invoke()` call) rather than a
    closure nested inside `invoke`. `captured` is an caller-owned,
    mutable accumulator list (mirrors `invoke`'s own local list) so a test
    exercising a SUBSET of actions directly (e.g. only action 0, to
    simulate process loss before action 1) can inspect exactly what that
    one action produced."""

    def _run() -> ActionEffect | None:
        result = swarm_svc.run_swarm(
            run_id,
            [adapter_id],
            profile=profile,
            dry_run=False,
            paths=paths,
            merge_with_existing=True,
        )
        captured.append(result)
        outcome = result.outcomes[0] if result.outcomes else None
        # Bounded, deterministic ref/digest -- operator_mcp_receipt schema
        # caps `effect_ref` at 256 chars; `run_id`+`adapter_id` is always
        # well under that (mirrors `run_plan.py`'s own `_effect_ref_for`
        # rationale for not encoding the unbounded candidate payload itself
        # into the ref).
        effect_ref = f"{OPERATION_KIND}:{run_id}:{adapter_id}"
        digest_source = (
            f"{effect_ref}:ran={outcome.ran if outcome else False}:"
            f"count={outcome.source_candidate_count if outcome else 0}:"
            f"denial={outcome.denial.reason if outcome and outcome.denial else ''}:"
            f"error={'yes' if outcome and outcome.error else 'no'}"
        )
        return ActionEffect(
            effect_kind="swarm_adapter_dispatched",
            effect_digest=hashlib.sha256(digest_source.encode("utf-8")).hexdigest(),
            effect_ref=effect_ref,
        )

    return ActionSpec(
        action_id=f"swarm_adapter:{index}:{adapter_id}",
        run=_run,
        # Judgment call (see this task's report): each per-adapter dispatch
        # is a real external call plus a durable merge-write, treated as an
        # atomic, indivisible section -- a cancellation request observed
        # WHILE one adapter is mid-dispatch defers to the NEXT safe point
        # (before the next adapter starts), never truncating an in-flight
        # external call, and this action's own pre-action checkpoint is
        # durably recorded before it starts.
        non_cancelable=True,
    )


def invoke(
    *,
    run_id: str,
    adapter_ids: Sequence[str],
    idempotency_key: str,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
    operations: OperatorOperationService | None = None,
    cancel_resume: OperatorCancelResumeService | None = None,
) -> base.OperatorAdapterResult:
    """The `swarm.start` Operator MCP tool.

    Deliberately accepts NO `identity`/`workspace_id`/`AuthIdentity`-shaped
    parameter anywhere -- the operator identity is resolved structurally,
    exactly once, inside `policy.PolicyContext.for_configured_operator`
    (requirement 1 of the P3 implementer contract, same as `run_plan.py`).

    Also deliberately accepts NO `profile`/`budget_usd`/`timeout_minutes`
    parameter -- see module docstring's "resolved, never caller-supplied"
    section; all three (plus sensitivity and the target run's owning
    workspace) are read-only resolutions from `run_id`'s own already-
    governed `run.yaml`.

    `confirmation_record`/`presented_token` are the caller's already-minted
    confirmation for this exact request (from `operation.preflight` -- P1
    scope, no transport in this repo yet) -- both are ignored entirely when
    `dry_run=True`.

    Also deliberately accepts NO `sensitivity_ceiling` parameter (P3
    hardening pass, H7 defect fix) -- see
    `operator_mcp_adapters.resolve_local_sensitivity_ceiling`'s own
    docstring for the full defect and remediation rationale; resolved
    structurally, the same way identity is resolved, exactly like
    `run_plan.py`'s own `invoke`.
    """

    from . import resolve_local_sensitivity_ceiling  # lazy: see operator_mcp_adapters/__init__.py's own docstring -- avoids the circular import a module-level import back into the package would create

    resolved_paths = paths or FoundryPaths.discover()
    sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)
    run_ctx = _resolve_run_context(run_id, resolved_paths)

    # No fail-open (requirement 5): budget, timeout, and governance profile
    # have no existing PolicyContext-level gate (unlike sensitivity/
    # workspace_id below, which reuse the substrate's own H3/rbac
    # mechanism) -- this adapter denies, before `ctx` is even constructed,
    # rather than defaulting any of the three.
    if run_ctx.budget_usd is None or run_ctx.timeout_minutes is None or run_ctx.governance_profile is None:
        decision = _preflight_denial("preflight_failed")
        return base.OperatorAdapterResult(ok=False, error=policy.build_error(decision, now=now))

    budget_usd: float = run_ctx.budget_usd
    timeout_minutes: int = run_ctx.timeout_minutes
    governance_profile: str = run_ctx.governance_profile

    effective_sensitivity = policy.resolve_effective_sensitivity(run_ctx.sensitivity)

    requested_ids = tuple(adapter_ids)
    input_payload: dict[str, Any] = {
        "run_id": run_id,
        "adapter_ids": list(requested_ids),
        "profile": governance_profile,
        "budget_usd": budget_usd,
        "timeout_minutes": timeout_minutes,
    }

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling=sensitivity_ceiling,
        targets=(policy.TargetRef("run", run_id),),
        # H3: exactly one entry, matching `targets` -- `None` (an
        # unresolvable/foreign run) denies at the rbac stage, the SAME
        # substrate mechanism `run_plan.py` relies on for sensitivity.
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload=input_payload,
        paths=resolved_paths,
    )

    # Captures each per-adapter dispatch's own `SwarmRunResult`, in action
    # order, so `_build_result` can report a real, bounded per-adapter
    # breakdown after `run_or_replay` executes these actions -- empty on a
    # genuine exact-replay of an already-terminal operation (module
    # docstring's "replay result-recovery gap").
    captured: list[swarm_svc.SwarmRunResult] = []

    actions = tuple(
        _make_action(run_id, i, aid, profile=governance_profile, paths=resolved_paths, captured=captured)
        for i, aid in enumerate(requested_ids)
    )

    def _build_result(execution: ExecutionOutcome) -> Mapping[str, Any]:
        # base.run_pipeline only ever calls this for "completed"/"canceled"
        # -- "failed"/"denied" are already turned into a build_error
        # envelope before build_result is reached.
        #
        # `execution.replayed` (not `captured` truthiness) is the correct
        # discriminator here: unlike `run_plan.py` (always exactly one
        # action, so a non-replayed "completed" outcome guarantees
        # `captured` is non-empty), `adapter_ids` may legitimately be empty
        # (zero actions) -- a genuine, non-replayed, zero-action completion
        # must still report `replayed=False` with an empty (not fabricated)
        # per-adapter breakdown, not be misread as a replay.
        if execution.status == "completed" and not execution.replayed:
            per_adapter: list[dict[str, Any]] = []
            total_candidates = 0
            for result in captured:
                outcome = result.outcomes[0] if result.outcomes else None
                if outcome is None:
                    continue
                per_adapter.append(
                    {
                        "adapter_id": outcome.adapter_id,
                        "ran": outcome.ran,
                        "degraded": outcome.degraded,
                        "source_candidate_count": outcome.source_candidate_count,
                        "denial_reason": outcome.denial.reason if outcome.denial else None,
                        "error": outcome.error,
                    }
                )
                total_candidates += outcome.source_candidate_count
            last_path = captured[-1].source_candidates_path if captured else None
            return {
                "status": "completed",
                "replayed": False,
                "run_id": run_id,
                "adapter_outcomes": per_adapter,
                "total_source_candidate_count": total_candidates,
                "source_candidates_path": str(last_path) if last_path else None,
                "canonical_refs_available": True,
            }
        if execution.status == "completed":
            # execution.replayed is True here: exact replay of an
            # already-terminal operation -- see module docstring's "replay
            # result-recovery gap" note.
            return {
                "status": "completed",
                "replayed": True,
                "canonical_refs_available": False,
            }
        return {"status": execution.status, "replayed": execution.replayed}

    action_manifest: dict[str, Any] = {
        "adapter": OPERATION_KIND,
        "run_id": run_id,
        "adapter_ids": list(requested_ids),
        "profile": governance_profile,
        "budget_usd": budget_usd,
        "timeout_minutes": timeout_minutes,
    }

    return base.run_pipeline(
        ctx=ctx,
        confirmation_record=confirmation_record,
        presented_token=presented_token,
        action_manifest=action_manifest,
        actions=actions,
        build_result=_build_result,
        dry_run=dry_run,
        paths=resolved_paths,
        now=now,
        operations=operations,
        cancel_resume=cancel_resume,
    )


@dataclass(frozen=True)
class SwarmStartAdapter:
    """`base.OperatorAdapter` Protocol implementation for `swarm.start`."""

    operation_kind: str = OPERATION_KIND

    def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:
        return invoke(**kwargs)


ADAPTER = SwarmStartAdapter()
base.register(ADAPTER)
