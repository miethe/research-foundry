"""`run.extract`, `run.claim_map`, and `run.synthesize` Operator MCP adapters
(research-foundry-operator-mcp-v1 M1 remainder).

Wraps `research_foundry.services.extraction.extract_run`,
`claim_mapping.build_claim_ledger`, and `synthesis.synthesize_report`
behind the fixed authorize -> consume -> execute -> bounded-result pipeline
in `operator_mcp_adapters.base.run_pipeline`, following the exact shape
`run_plan.py`/`swarm_start.py` established: build a `PolicyContext`, an
`ActionSpec` sequence, an `action_manifest`, and a `build_result` callback,
then hand all four to `base.run_pipeline`. All three canonical services are
already plain, typed, `paths`-injectable functions with no CLI/Typer
coupling -- this module wraps them; it does not change them.

**Eager (non-lazy) canonical-service imports, unlike `run_plan.py`'s own
`planning` import.** `run_plan.py`'s module docstring documents why its
import of `research_foundry.services.planning` must be lazy: `planning.py`
imports `assertion_catalog` at module level, which imports `api.auth.provider`
eagerly, dragging in fastapi/starlette. `extraction.py`, `claim_mapping.py`,
and `synthesis.py` (and everything each imports transitively -- `term_index`,
`registry`, `schemas`, `frontmatter`, `yamlio`, `ids`, `errors`, `paths`) were
checked and carry no `api.auth`/`fastapi` import anywhere in their import
graphs, so importing all three at THIS module's top level does not regress
requirement 7 ("imports cleanly without the `[serve]` extra").

**Resolved, never caller-supplied, run-level governance inputs (requirement
5, no fail-open) -- same doctrine as `swarm_start.py`'s own "resolved,
never caller-supplied" section, one field narrower.** All three of these
adapters operate on an EXISTING run whose own sensitivity and owning
workspace were already established once, durably, by `run.plan`
(`run.yaml`, written by `planning.plan_run`). Accepting either as a
caller-supplied parameter here would let a later pipeline stage silently
re-declare a run's sensitivity/workspace after the fact -- so, exactly like
`swarm_start._resolve_run_context`, `_resolve_run_context` below is a
read-only, best-effort lookup of `run.yaml`'s own `sensitivity`/
`workspace_id` fields that resolves every field to `None` on ANY failure
(missing run, malformed YAML, wrong types) -- never a permissive default.
Unlike `swarm_start.py`, none of `extract_run`/`build_claim_ledger`/
`synthesize_report` has a budget/timeout/governance-profile concept, so this
module's `_RunContext` carries only the two fields these three adapters
actually need.

**Two extra target kinds, one judgment call not covered by the P3
exemplars.** `operator_mcp_policy._REQUIRED_TARGET_KINDS` declares
`run.claim_map` requires `{"run", "extraction_card"}` and `run.synthesize`
requires `{"run", "claim_ledger"}` -- one target kind more than `run.extract`
(`{"run"}`, the same single-target shape `swarm.start` uses). Tracing
`_check_preflight`/`_check_identity_and_rbac`: the preflight stage only
checks that a `TargetRef` of each REQUIRED KIND is present in
`ctx.targets` (never that the referenced artifact exists on disk -- that is
explicitly left to "P3/P4 adapters own their own richer prerequisite checks
once they exist", per that dict's own comment); the rbac stage then requires
`resolved_target_workspaces` to supply one owning-workspace entry per
target, denying `not_found` for any entry that is `None` or does not match
the caller's own workspace. Neither `extraction_card` nor `claim_ledger` is
individually addressable at invoke time (a run has a whole SET of extraction
cards, and exactly one claim-ledger singleton) and neither carries a
persisted owning-workspace field of its own -- both are always children of
the SAME run, so this module's judgment call is: use `run_id` itself as the
`target_ref` for the secondary target kind (a real, well-formed, bounded
string that already satisfies the closed target-ref pattern, since it is
also used unmodified for the `"run"` target), and resolve its owning
workspace to the SAME `run_ctx.workspace_id` the `"run"` target resolves to
-- an extraction card or claim ledger belonging to a foreign-workspace run
is exactly as "not this caller's" as the run itself, and there is no
narrower resolution available without inventing a new persisted field this
task does not own. This mirrors, rather than reinvents, H3's existing
per-target workspace-match mechanism.

**`run.synthesize`'s own `sensitivity` parameter is NOT this operation's
`effective_sensitivity`/`sensitivity_ceiling`.** `synthesis.synthesize_report`
accepts an optional `sensitivity: str | None` that becomes the SYNTHESIZED
REPORT's own front-matter content-sensitivity label (falling back to the
originating intent's `governance.sensitivity`, then `"personal"`) -- a
downstream content-classification decision, not an authorization input. This
adapter forwards it straight through, exactly like `audience`/`model_profile`/
`final`/`llm`, and keeps it out of the `effective_sensitivity` computation
entirely: THAT value is always resolved from the target run's OWN already-
governed `run.yaml` sensitivity via `_resolve_run_context`, the same
structural source every other run-scoped adapter in this family uses. A
caller cannot use this parameter to loosen or tighten what ceiling check
this operation itself is subject to.

**Replay result-recovery gap (documented limitation, NOT fixed here, same
shape as `run_plan.py`/`swarm_start.py`'s own).** On a genuine exact-replay
of an ALREADY-terminal operation, `ActionSpec.run()` is never invoked a
second time, so `captured` (below) is empty and the real canonical result
cannot be reconstructed from durable operator-layer state alone
(`OperatorReceiptService` exposes no public reader for a persisted
`effect_ref` by `operation_id`/`action_id`). `_build_result` returns a
bounded, honest partial payload on that path (`"canonical_refs_available":
False`) rather than fabricating one -- the same follow-up gap `run_plan.py`
already reports, not re-solved here (out of this task's file ownership:
`operator_receipt_service.py`).
"""

from __future__ import annotations

import hashlib
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from research_foundry.paths import FoundryPaths
from research_foundry.services import claim_mapping, extraction, synthesis
from research_foundry.services import operator_mcp_policy as policy
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

__all__ = [
    "EXTRACT_OPERATION_KIND",
    "CLAIM_MAP_OPERATION_KIND",
    "SYNTHESIZE_OPERATION_KIND",
    "RunExtractAdapter",
    "RunClaimMapAdapter",
    "RunSynthesizeAdapter",
    "EXTRACT_ADAPTER",
    "CLAIM_MAP_ADAPTER",
    "SYNTHESIZE_ADAPTER",
    "invoke_extract",
    "invoke_claim_map",
    "invoke_synthesize",
]

EXTRACT_OPERATION_KIND = "run.extract"
CLAIM_MAP_OPERATION_KIND = "run.claim_map"
SYNTHESIZE_OPERATION_KIND = "run.synthesize"


@dataclass(frozen=True)
class _RunContext:
    """Read-only, best-effort resolution of the target run's OWN already-
    governed `sensitivity`/`workspace_id` -- see module docstring's
    "resolved, never caller-supplied" section. Both fields are `None` on
    ANY resolution failure (missing run, malformed `run.yaml`, wrong
    types); every `invoke_*` function below denies rather than defaulting
    for either one."""

    sensitivity: str | None
    workspace_id: str | None


def _resolve_run_context(run_id: str, paths: FoundryPaths) -> _RunContext:
    """See `_RunContext`'s own docstring. Swallows EVERY exception loading
    `run.yaml` and resolves both fields to `None` on failure -- mirrors
    `swarm_start._resolve_run_context`'s own fail-closed convention (a
    strict subset of its fields: this family has no budget/timeout/
    governance-profile concept)."""

    try:
        run_doc = load_yaml(paths.run_paths(run_id).run_yaml)
    except Exception as exc:
        _logger.warning(
            "operator_mcp_adapters.research_stages: run.yaml lookup failed (%s) for "
            "run_id=%s -- resolving sensitivity/workspace_id to None (deny, never default)",
            type(exc).__name__,
            run_id,
        )
        return _RunContext(None, None)

    if not isinstance(run_doc, dict):
        return _RunContext(None, None)

    sensitivity = run_doc.get("sensitivity")
    sensitivity = sensitivity if isinstance(sensitivity, str) else None

    workspace_id = run_doc.get("workspace_id")
    workspace_id = workspace_id if isinstance(workspace_id, str) and workspace_id else None

    return _RunContext(sensitivity, workspace_id)


# ---------------------------------------------------------------------------
# run.extract
# ---------------------------------------------------------------------------


def invoke_extract(
    *,
    run_id: str,
    idempotency_key: str,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    model_profile: str = "rf_extract_cheap",
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
    operations: OperatorOperationService | None = None,
    cancel_resume: OperatorCancelResumeService | None = None,
) -> base.OperatorAdapterResult:
    """The `run.extract` Operator MCP tool.

    Deliberately accepts NO `identity`/`workspace_id`/`sensitivity_ceiling`
    parameter -- see module docstring and `run_plan.py`'s own docstring for
    the full rationale (identity is resolved structurally inside
    `policy.PolicyContext.for_configured_operator`; the ceiling is resolved
    structurally via `resolve_local_sensitivity_ceiling`, the H7 defect fix
    every adapter in this package reproduces verbatim).
    """

    from . import (
        resolve_local_sensitivity_ceiling,  # lazy: avoids the circular import operator_mcp_adapters/__init__.py's own docstring documents
    )

    resolved_paths = paths or FoundryPaths.discover()
    sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)
    run_ctx = _resolve_run_context(run_id, resolved_paths)
    effective_sensitivity = policy.resolve_effective_sensitivity(run_ctx.sensitivity)

    input_payload: dict[str, Any] = {"run_id": run_id, "model_profile": model_profile}

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=EXTRACT_OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling=sensitivity_ceiling,
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload=input_payload,
        paths=resolved_paths,
    )

    # Captures extract_run's own ExtractResult so `_build_result` can read
    # the real canonical refs after `run_or_replay` executes this action --
    # see module docstring's "replay result-recovery gap" note.
    captured: list[extraction.ExtractResult] = []

    def _run() -> ActionEffect:
        result = extraction.extract_run(run_id, model_profile=model_profile, paths=resolved_paths)
        captured.append(result)
        effect_ref = f"{EXTRACT_OPERATION_KIND}:{run_id}"
        return ActionEffect(
            effect_kind="run_extracted",
            effect_digest=hashlib.sha256(effect_ref.encode("utf-8")).hexdigest(),
            effect_ref=effect_ref,
        )

    def _build_result(execution: ExecutionOutcome) -> Mapping[str, Any]:
        if execution.status == "completed" and captured:
            result = captured[0]
            return {
                "status": "completed",
                "run_id": result.run_id,
                "cards": list(result.cards),
                "count": result.count,
                "canonical_refs_available": True,
            }
        if execution.status == "completed":
            return {"status": "completed", "replayed": True, "canonical_refs_available": False}
        return {"status": execution.status, "replayed": execution.replayed}

    action_manifest: dict[str, Any] = {
        "adapter": EXTRACT_OPERATION_KIND,
        "run_id": run_id,
        "model_profile": model_profile,
    }

    return base.run_pipeline(
        ctx=ctx,
        confirmation_record=confirmation_record,
        presented_token=presented_token,
        action_manifest=action_manifest,
        actions=(ActionSpec(action_id="extract_run", run=_run),),
        build_result=_build_result,
        dry_run=dry_run,
        paths=resolved_paths,
        now=now,
        operations=operations,
        cancel_resume=cancel_resume,
    )


# ---------------------------------------------------------------------------
# run.claim_map
# ---------------------------------------------------------------------------


def invoke_claim_map(
    *,
    run_id: str,
    idempotency_key: str,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    intent_id: str | None = None,
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
    operations: OperatorOperationService | None = None,
    cancel_resume: OperatorCancelResumeService | None = None,
) -> base.OperatorAdapterResult:
    """The `run.claim_map` Operator MCP tool.

    See module docstring's "two extra target kinds" section for why
    `targets` declares both `run` and `extraction_card` (both resolving to
    the SAME owning workspace) rather than `run` alone.
    """

    from . import resolve_local_sensitivity_ceiling  # lazy: see invoke_extract's own comment

    resolved_paths = paths or FoundryPaths.discover()
    sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)
    run_ctx = _resolve_run_context(run_id, resolved_paths)
    effective_sensitivity = policy.resolve_effective_sensitivity(run_ctx.sensitivity)

    input_payload: dict[str, Any] = {"run_id": run_id, "intent_id": intent_id}
    # Drop the None-valued optional so two callers who both omit intent_id
    # collapse to the same canonical digest (mirrors run_plan.py's own
    # rationale for the identical pattern).
    input_payload = {k: v for k, v in input_payload.items() if v is not None}

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=CLAIM_MAP_OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling=sensitivity_ceiling,
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("extraction_card", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload=input_payload,
        paths=resolved_paths,
    )

    captured: list[claim_mapping.ClaimMapResult] = []

    def _run() -> ActionEffect:
        result = claim_mapping.build_claim_ledger(run_id, intent_id=intent_id, paths=resolved_paths)
        captured.append(result)
        effect_ref = f"{CLAIM_MAP_OPERATION_KIND}:{run_id}"
        return ActionEffect(
            effect_kind="claim_ledger_built",
            effect_digest=hashlib.sha256(effect_ref.encode("utf-8")).hexdigest(),
            effect_ref=effect_ref,
        )

    def _build_result(execution: ExecutionOutcome) -> Mapping[str, Any]:
        if execution.status == "completed" and captured:
            result = captured[0]
            return {
                "status": "completed",
                "run_id": result.run_id,
                "ledger_path": str(result.ledger_path),
                "claims_total": result.claims_total,
                "by_status": dict(result.by_status),
                "canonical_refs_available": True,
            }
        if execution.status == "completed":
            return {"status": "completed", "replayed": True, "canonical_refs_available": False}
        return {"status": execution.status, "replayed": execution.replayed}

    action_manifest: dict[str, Any] = {
        "adapter": CLAIM_MAP_OPERATION_KIND,
        "run_id": run_id,
        "intent_id": intent_id,
    }

    return base.run_pipeline(
        ctx=ctx,
        confirmation_record=confirmation_record,
        presented_token=presented_token,
        action_manifest=action_manifest,
        actions=(ActionSpec(action_id="build_claim_ledger", run=_run),),
        build_result=_build_result,
        dry_run=dry_run,
        paths=resolved_paths,
        now=now,
        operations=operations,
        cancel_resume=cancel_resume,
    )


# ---------------------------------------------------------------------------
# run.synthesize
# ---------------------------------------------------------------------------


def invoke_synthesize(
    *,
    run_id: str,
    idempotency_key: str,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    model_profile: str = "rf_synthesize_deep",
    final: bool = False,
    audience: str | None = None,
    sensitivity: str | None = None,
    llm: bool = False,
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
    operations: OperatorOperationService | None = None,
    cancel_resume: OperatorCancelResumeService | None = None,
) -> base.OperatorAdapterResult:
    """The `run.synthesize` Operator MCP tool.

    `sensitivity` here is `synthesis.synthesize_report`'s own content-
    classification parameter, forwarded verbatim -- see module docstring's
    "NOT this operation's `effective_sensitivity`" section. It plays no
    part in this operation's own `effective_sensitivity`/`sensitivity_
    ceiling`, both of which are resolved structurally from the target
    run's OWN `run.yaml`, exactly like `invoke_extract`/`invoke_claim_map`.

    See module docstring's "two extra target kinds" section for why
    `targets` declares both `run` and `claim_ledger`.
    """

    from . import resolve_local_sensitivity_ceiling  # lazy: see invoke_extract's own comment

    resolved_paths = paths or FoundryPaths.discover()
    sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)
    run_ctx = _resolve_run_context(run_id, resolved_paths)
    effective_sensitivity = policy.resolve_effective_sensitivity(run_ctx.sensitivity)

    input_payload: dict[str, Any] = {
        "run_id": run_id,
        "model_profile": model_profile,
        "final": final,
        "audience": audience,
        "sensitivity": sensitivity,
        "llm": llm,
    }
    input_payload = {k: v for k, v in input_payload.items() if v is not None}

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=SYNTHESIZE_OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling=sensitivity_ceiling,
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("claim_ledger", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload=input_payload,
        paths=resolved_paths,
    )

    captured: list[synthesis.SynthResult] = []

    def _run() -> ActionEffect:
        result = synthesis.synthesize_report(
            run_id,
            model_profile=model_profile,
            final=final,
            audience=audience,
            sensitivity=sensitivity,
            llm=llm,
            paths=resolved_paths,
        )
        captured.append(result)
        effect_ref = f"{SYNTHESIZE_OPERATION_KIND}:{run_id}"
        return ActionEffect(
            effect_kind="report_synthesized",
            effect_digest=hashlib.sha256(effect_ref.encode("utf-8")).hexdigest(),
            effect_ref=effect_ref,
        )

    def _build_result(execution: ExecutionOutcome) -> Mapping[str, Any]:
        if execution.status == "completed" and captured:
            result = captured[0]
            return {
                "status": "completed",
                "run_id": result.run_id,
                "report_path": str(result.report_path),
                "claims_cited": list(result.claims_cited),
                "canonical_refs_available": True,
            }
        if execution.status == "completed":
            return {"status": "completed", "replayed": True, "canonical_refs_available": False}
        return {"status": execution.status, "replayed": execution.replayed}

    action_manifest: dict[str, Any] = {
        "adapter": SYNTHESIZE_OPERATION_KIND,
        "run_id": run_id,
        "model_profile": model_profile,
        "final": final,
    }

    return base.run_pipeline(
        ctx=ctx,
        confirmation_record=confirmation_record,
        presented_token=presented_token,
        action_manifest=action_manifest,
        actions=(ActionSpec(action_id="synthesize_report", run=_run),),
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
class RunExtractAdapter:
    """`base.OperatorAdapter` Protocol implementation for `run.extract`."""

    operation_kind: str = EXTRACT_OPERATION_KIND

    def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:
        return invoke_extract(**kwargs)


@dataclass(frozen=True)
class RunClaimMapAdapter:
    """`base.OperatorAdapter` Protocol implementation for `run.claim_map`."""

    operation_kind: str = CLAIM_MAP_OPERATION_KIND

    def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:
        return invoke_claim_map(**kwargs)


@dataclass(frozen=True)
class RunSynthesizeAdapter:
    """`base.OperatorAdapter` Protocol implementation for `run.synthesize`."""

    operation_kind: str = SYNTHESIZE_OPERATION_KIND

    def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:
        return invoke_synthesize(**kwargs)


EXTRACT_ADAPTER = RunExtractAdapter()
CLAIM_MAP_ADAPTER = RunClaimMapAdapter()
SYNTHESIZE_ADAPTER = RunSynthesizeAdapter()
base.register(EXTRACT_ADAPTER)
base.register(CLAIM_MAP_ADAPTER)
base.register(SYNTHESIZE_ADAPTER)
