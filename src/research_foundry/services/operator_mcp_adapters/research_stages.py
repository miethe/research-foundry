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

**F1 fix (M1 remainder pre-gate finding): missing secondary/upstream
artifacts now deny with a reason code, never silently succeed.** Both
lenses (codex + ICA) reproduced this empirically: `run.claim_map` on a run
with ZERO extraction cards returned `ok=True, claims_total=0`, and
`run.synthesize` on a run with NO claim ledger returned `ok=True` with a
fully "completed" placeholder report (`synthesis._load_ledger` silently
substitutes an empty ledger rather than raising). Neither denied. This
module now gates both with a read-only, on-disk existence check
(`_claim_map_prerequisites_met`/`_synthesize_prerequisites_met`) --
absent, empty, or unreadable denies `preflight_failed`; the canonical
service is never called.

**Ordering (F6 lesson, deliberately NOT verify_bundle.py's own shape):**
`verify_bundle.py`'s sibling prerequisite gate runs BEFORE `ctx` is even
constructed -- for ANY caller, authorized or not -- which is exactly what
lets an unauthorized caller distinguish "run exists but lacks the
artifact" (`preflight_failed`) from "not found / not yours" (`not_found`)
by reason code alone (F6, a genuine cross-workspace existence leak). This
module does NOT reproduce that ordering: each `invoke_*` below calls
`policy.evaluate_policy(ctx, ...)` itself (the same capability -> rbac ->
audit_health -> guard -> preflight stack `base.run_pipeline`'s own dry-run
path and `authorize_operation` both already re-run -- "policy may have
drifted since mint time" is that function's own documented rationale for
tolerating a second evaluation) and returns its denial VERBATIM if it
denies. The on-disk existence check runs ONLY once that call has already
returned `allowed=True` -- i.e. only for a caller already proven to own
this run's workspace -- so an unauthorized caller can never reach the new
`preflight_failed` branch at all; they deny at `rbac`/`not_found` exactly
as before, with zero behavioral change to that path. This also applies
regardless of `dry_run`, mirroring `verify_bundle.py`'s own "the gate runs
before execution, dry run or not" shape.

**`run.extract`'s own equivalent, one hop upstream (checklist item 2,
"fix the layer below").** `extraction.extract_run` raises `NotFoundError`
for a wholly missing run (unaffected -- RBAC already denies `not_found`
for that case before any of this is reached) but, for a run that EXISTS
with zero `sources/*.md` cards, silently returns `ExtractResult(cards=[],
count=0)`, `ok=True` -- the identical "declared input silently treated as
present" shape F1 named for the other two adapters, just one stage
earlier in the pipeline (a run that has not yet received any ingested
source, or had all its sources removed). `run.extract` declares only the
single `{"run"}` target kind (no secondary target kind exists for it to
under-check, unlike `run.claim_map`/`run.synthesize`), so this is not
literally F1's shape -- but it is the same defect class, in the same
file, gated here too (`_extract_prerequisites_met`) for consistency and
because leaving it ungated after fixing the other two would just move the
silent-success failure mode one hop earlier rather than closing it.

**F7 (documented, not "fixed" by inventing a new field):** the secondary
`extraction_card`/`claim_ledger` target `TargetRef` (see "two extra
target kinds" above) remains what it always was -- a KIND-LABEL required
to satisfy `_REQUIRED_TARGET_KINDS`'s "expected kinds present" preflight
gate, resolving to the SAME workspace as the primary `run` target, so its
own RBAC pass is a provable no-op. It is NOT an independent check and was
never meant to be one; the actual "does the artifact exist" check F1
needed is the NEW `_claim_map_prerequisites_met`/
`_synthesize_prerequisites_met` gate above, not this target. Documented
honestly here rather than left to imply a defense-in-depth property it
does not provide.

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
from pathlib import Path
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


def _resolved_within(root: Path, candidate: Path) -> bool:
    """M2 fix cycle 2, path-containment sweep (sibling to SEC-1) -- the same
    resolve-then-contain posture every other adapter module in this family
    establishes, duplicated here per convention (adapter modules do not
    cross-import each other's private helpers)."""

    try:
        root_resolved = root.resolve()
        effective = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    except OSError as exc:
        _logger.warning(
            "operator_mcp_adapters.research_stages: path resolution failed (%s) -- "
            "denying (never a permissive fallback)",
            type(exc).__name__,
        )
        return False
    return effective == root_resolved or root_resolved in effective.parents


def _resolve_run_context(run_id: str, paths: FoundryPaths) -> _RunContext:
    """See `_RunContext`'s own docstring. Swallows EVERY exception loading
    `run.yaml` and resolves both fields to `None` on failure -- mirrors
    `swarm_start._resolve_run_context`'s own fail-closed convention (a
    strict subset of its fields: this family has no budget/timeout/
    governance-profile concept).

    **M2 fix cycle 2 (path-containment sweep, sibling to SEC-1).** `run_id`
    is contained to `paths.runs` FIRST -- before `run.yaml` is ever read --
    see `external_import._resolve_run_workspace_id`'s identical fix for the
    full rationale."""

    if not _resolved_within(paths.runs, Path(run_id)):
        _logger.warning(
            "operator_mcp_adapters.research_stages: run_id=%s escapes the authorized "
            "runs/ tree -- resolving sensitivity/workspace_id to None (deny, never "
            "a permissive fallback)",
            run_id,
        )
        return _RunContext(None, None)

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


def _preflight_denial(reason_code: str) -> policy.PolicyDecision:
    """Adapter-owned preflight denial -- an independent, narrow duplicate of
    `verify_bundle._preflight_denial` (module-private there, and
    `verify_bundle.py` is out of this task's file-ownership boundary), fed
    to the SAME public `policy.build_error` every other denial in this
    family goes through."""

    return policy.PolicyDecision(False, "preflight", reason_code, retryable=True)


def _extract_prerequisites_met(run_id: str, paths: FoundryPaths) -> bool:
    """Read-only, best-effort check that `run_id` has at least one source
    card for `extract_run` to read -- see module docstring's "run.extract's
    own equivalent" section (checklist item 2, applied to this same file).
    `extract_run` itself raises `NotFoundError` for a wholly missing run
    (unaffected: RBAC already denies `not_found` for that case before this
    function is ever reached), but silently returns `ExtractResult(cards=[],
    count=0)` -- `ok=True` -- for a run that exists yet has zero
    `sources/*.md` cards. Absent run, absent `sources/` directory, or zero
    `*.md` cards within it all deny -- never a permissive default."""

    try:
        rp = paths.run_paths(run_id)
        if not rp.run.exists():
            return False
        return rp.sources.exists() and any(rp.sources.glob("*.md"))
    except Exception as exc:
        _logger.warning(
            "operator_mcp_adapters.research_stages: run.extract prerequisite check "
            "failed (%s) for run_id=%s -- denying (never a permissive default)",
            type(exc).__name__,
            run_id,
        )
        return False


def _claim_map_prerequisites_met(run_id: str, paths: FoundryPaths) -> bool:
    """Read-only, best-effort check that `run_id` has at least one
    extraction card for `build_claim_ledger` to map (F1). Called ONLY after
    `policy.evaluate_policy` has already authorized the caller for this
    run's own targets -- see module docstring's F1/F6 sections for why this
    function is never reached by an unauthorized caller. Absent run, absent
    `extractions/` directory, or zero `*.yaml` cards within it all deny --
    never a permissive default."""

    try:
        rp = paths.run_paths(run_id)
        if not rp.run.exists():
            return False
        return rp.extractions.exists() and any(rp.extractions.glob("*.yaml"))
    except Exception as exc:
        _logger.warning(
            "operator_mcp_adapters.research_stages: run.claim_map prerequisite check "
            "failed (%s) for run_id=%s -- denying (never a permissive default)",
            type(exc).__name__,
            run_id,
        )
        return False


def _synthesize_prerequisites_met(run_id: str, paths: FoundryPaths) -> bool:
    """Read-only, best-effort check that `run_id` has a real, on-disk claim
    ledger for `synthesize_report` to read (F1) -- `synthesis._load_ledger`
    never raises for a missing ledger, it silently substitutes
    `{"claims": [], "unresolved_questions": []}`, producing a fully
    "completed" placeholder report indistinguishable from a real one
    downstream. Called ONLY after `policy.evaluate_policy` has already
    authorized the caller for this run's own targets -- see module
    docstring's F1/F6 sections. Absent run or absent
    `claims/claim_ledger.yaml` denies -- never a permissive default."""

    try:
        rp = paths.run_paths(run_id)
        if not rp.run.exists():
            return False
        return rp.claim_ledger.exists()
    except Exception as exc:
        _logger.warning(
            "operator_mcp_adapters.research_stages: run.synthesize prerequisite check "
            "failed (%s) for run_id=%s -- denying (never a permissive default)",
            type(exc).__name__,
            run_id,
        )
        return False


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

    # F1/F6 fix (checklist item 2, applied to run.extract): authorize FIRST
    # (capability -> rbac -> audit_health -> guard -> preflight), then --
    # ONLY for an already-authorized caller -- check that the run actually
    # has source cards to extract from. See module docstring's F1/F6/F7
    # sections. Applies regardless of `dry_run`.
    decision = policy.evaluate_policy(ctx, paths=resolved_paths)
    if decision.denied:
        return base.OperatorAdapterResult(ok=False, error=policy.build_error(decision, now=now))
    if not _extract_prerequisites_met(run_id, resolved_paths):
        return base.OperatorAdapterResult(
            ok=False, error=policy.build_error(_preflight_denial("preflight_failed"), now=now)
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

    # F1/F6 fix: authorize FIRST (capability -> rbac -> audit_health ->
    # guard -> preflight), then -- ONLY for an already-authorized caller --
    # check that the run actually has extraction cards to map. See module
    # docstring's F1/F6/F7 sections. Applies regardless of `dry_run`.
    decision = policy.evaluate_policy(ctx, paths=resolved_paths)
    if decision.denied:
        return base.OperatorAdapterResult(ok=False, error=policy.build_error(decision, now=now))
    if not _claim_map_prerequisites_met(run_id, resolved_paths):
        return base.OperatorAdapterResult(
            ok=False, error=policy.build_error(_preflight_denial("preflight_failed"), now=now)
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

    # F1/F6 fix: authorize FIRST (capability -> rbac -> audit_health ->
    # guard -> preflight), then -- ONLY for an already-authorized caller --
    # check that the run actually has a claim ledger to synthesize from.
    # See module docstring's F1/F6/F7 sections. Applies regardless of
    # `dry_run`.
    decision = policy.evaluate_policy(ctx, paths=resolved_paths)
    if decision.denied:
        return base.OperatorAdapterResult(ok=False, error=policy.build_error(decision, now=now))
    if not _synthesize_prerequisites_met(run_id, resolved_paths):
        return base.OperatorAdapterResult(
            ok=False, error=policy.build_error(_preflight_denial("preflight_failed"), now=now)
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
