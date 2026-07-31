"""`writeback.preview` Operator MCP adapter (research-foundry-operator-mcp-v1
M2 leg A, task OPM-5.3).

Wraps `research_foundry.services.writeback.preview_writeback` behind the
fixed authorize -> consume -> execute -> bounded-result pipeline in
`operator_mcp_adapters.base.run_pipeline`, following the exact shape
`verify_bundle.py` established for `run.verify`/`run.bundle`: build a
`PolicyContext`, an `ActionSpec` sequence, an `action_manifest`, and a
`build_result` callback, then hand all four to `base.run_pipeline`.

**Governed RESULT, never a denial, for a render-time condition (D4-style
doctrine, mirrors `verify_bundle.py`'s own module docstring).**
`writeback.preview_writeback` itself never raises for a missing bundle, an
unsupported target name, or an unresolved target-specific correlation --
those are reported per-target via `writeback.WRITEBACK_PREVIEW_TARGET_
STATUSES` inside an `ok=True` result (see that function's own docstring).
`_run()` below therefore ALWAYS returns normally once `preview_writeback`
itself runs.

**Review-required sensitivity denies the WHOLE operation one layer up, at
the policy layer -- `preview_writeback` never needs to represent it as one
of its own per-target statuses.** `ctx.writeback_targets` (populated below
from the caller's `targets`) feeds `governance.GuardContext.writeback_
targets` inside `operator_mcp_policy._check_guard`, which fires the SAME
`intenttree_writeback_requires_review`/`arc_writeback_requires_review` rules
`_check_guard` already applies to every other writeback path (see
`operator_mcp_policy.PolicyContext`'s own docstring, and D6's own text:
"the SAME ... guard rules apply here as everywhere else"). A request whose
sensitivity would trigger one of those rules denies with
`reason_code=guard_review_required` (retryable) BEFORE `_run()` -- and
therefore before `writeback.preview_writeback` -- is ever invoked. This is
also why `_check_preflight` REQUIRES `ctx.writeback_targets` to be non-empty
for `writeback.preview` (BLOCK-7, `operator_mcp_policy.py`): this adapter
always forwards the caller's own requested `targets` there, never an empty
default, so that gate is guaranteed reachable for every real request.

**`evidence_bundle` target reference reuses `run_id` (mirrors `run.bundle`'s
own "verification" target).** `_REQUIRED_TARGET_KINDS["writeback.preview"]
== frozenset({"evidence_bundle"})` (`operator_mcp_policy.py`) requires a
declared target of that kind, but there is no separate "evidence bundle id"
this contract phase can resolve without an authorized filesystem read
(reading `evidence_bundle.yaml` BEFORE authorization would leak target
existence to an unauthorized caller -- the exact class of leak F6 closed in
`verify_bundle.py`). `run_id` is reused as the `target_ref` for this second
target too, exactly like `run.bundle`'s own `TargetRef("verification",
run_id)` -- confirmed (mirroring that module's own research) that no guard/
RBAC logic anywhere keys on `target_kind == "evidence_bundle"` specifically
or inspects its `target_ref` value; `_check_identity_and_rbac` only walks
`resolved_target_workspaces` POSITIONALLY, so both entries must supply the
SAME owning workspace (the run's).

**`targets` normalization.** The caller-supplied target sequence is
normalized to a SORTED, DEDUPLICATED tuple before it ever reaches `ctx` --
two callers requesting the same set of targets in a different order (or
with a duplicate) collapse to the SAME canonical digest, mirroring
`run_plan.py`'s own `input_payload` construction rationale for dropping
semantically-equivalent variation before hashing.

**Zero client construction, whole call graph.** For the three preview-
supported targets (`intenttree`, `arc`, `notebooklm`), neither this module
nor `writeback.preview_writeback` ever imports `..integrations`, constructs
an `IntentTreeClient`/`ArcClient`/NotebookLM client, or reaches
`urllib.request.urlopen` (this codebase's actual HTTP primitive --
`integrations/base.py`'s own module docstring: stdlib `urllib` only, no
`httpx` dependency exists here at all). See this leg's completion note for
the integration test that spies on all of these plus `get_meatywiki_client`
(never imported here either) to prove it.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Mapping, Sequence

from research_foundry.paths import FoundryPaths
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

# `writeback` is imported LAZILY (inside `invoke_preview`'s body), never at
# module level -- mirrors `verify_bundle.py`'s own rationale: this package's
# own `operator_mcp_adapters` import graph must keep importing cleanly
# without the `[serve]` extra (requirement 7, `base.py`'s own module
# docstring). `writeback.py` does not currently carry an eager `[serve]`-
# gated import, but is lazily imported here too for the same defensive
# reason and for symmetry with every other adapter module in this family.
if TYPE_CHECKING:
    from research_foundry.services import writeback

_logger = logging.getLogger(__name__)

__all__ = [
    "OPERATION_KIND",
    "WritebackPreviewAdapter",
    "PREVIEW_ADAPTER",
    "invoke_preview",
]

OPERATION_KIND = "writeback.preview"


@dataclass(frozen=True)
class _RunContext:
    """Read-only, best-effort resolution of the target run's own declared
    sensitivity and owning workspace. Both fields are `None` on ANY
    resolution failure (missing run, malformed `run.yaml`) -- callers deny
    rather than defaulting for either one. Deliberately duplicated here
    rather than imported from `verify_bundle.py`: each adapter module in
    this family defines its own narrow copy of this exact shape (see that
    module's own precedent, and `operator_mcp_adapters/__init__.py`'s
    documented rationale for the analogous `resolve_local_sensitivity_
    ceiling` convention) -- adapter modules do not cross-import each
    other's private helpers."""

    sensitivity: str | None
    workspace_id: str | None


def _resolve_run_context(run_id: str, paths: FoundryPaths) -> _RunContext:
    """Swallows EVERY exception (`run.yaml` load/parse failure) and resolves
    both fields to `None` on failure -- mirrors `verify_bundle._resolve_run_
    context`'s own fail-closed convention."""

    try:
        run_doc = load_yaml(paths.run_paths(run_id).run_yaml)
    except Exception as exc:
        _logger.warning(
            "operator_mcp_adapters.writeback_preview: run.yaml lookup failed (%s) for "
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


def invoke_preview(
    *,
    run_id: str,
    idempotency_key: str,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    targets: Sequence[str],
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
    operations: OperatorOperationService | None = None,
    cancel_resume: OperatorCancelResumeService | None = None,
) -> base.OperatorAdapterResult:
    """The `writeback.preview` Operator MCP tool.

    Deliberately accepts NO `identity`/`workspace_id`/`AuthIdentity`-shaped
    parameter and NO `sensitivity_ceiling` parameter -- both resolved
    structurally, exactly like every other adapter in this family (see
    module docstring).

    See the module docstring for: the D4-style "governed result, never a
    denial for a render-time condition" contract; why review-required
    sensitivity denies one layer up, at the policy guard stage, before this
    function's `_run()` closure ever runs; the `evidence_bundle` target
    reference reuse; and the `targets` canonicalization.
    """

    from research_foundry.services import writeback

    from . import resolve_local_sensitivity_ceiling  # lazy: avoids circular import, see operator_mcp_adapters/__init__.py's own docstring

    resolved_paths = paths or FoundryPaths.discover()
    sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)
    run_ctx = _resolve_run_context(run_id, resolved_paths)

    effective_sensitivity = policy.resolve_effective_sensitivity(run_ctx.sensitivity)

    # Sorted + deduplicated so two callers requesting the same set in a
    # different order (or with a duplicate) collapse to the same canonical
    # digest (module docstring, "targets normalization").
    normalized_targets = tuple(sorted({str(t) for t in targets}))

    input_payload: dict[str, Any] = {"run_id": run_id, "targets": list(normalized_targets)}

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling=sensitivity_ceiling,
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("evidence_bundle", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload=input_payload,
        writeback_targets=normalized_targets,
        paths=resolved_paths,
    )

    # Captures preview_writeback's own WritebackPreviewResult so
    # `_build_result` can read the real governed outcome after
    # `run_or_replay` executes this action -- empty on a genuine exact-
    # replay of an already-terminal operation (same "replay result-recovery
    # gap" every other adapter in this family documents).
    captured: list["writeback.WritebackPreviewResult"] = []

    def _run() -> ActionEffect:
        # D4: `preview_writeback` itself never raises for a render-time
        # condition (missing bundle, unsupported target, unresolved
        # correlation) -- this ALWAYS returns normally once it runs.
        result = writeback.preview_writeback(
            run_id,
            targets=normalized_targets,
            paths=resolved_paths,
            now=now,
        )
        captured.append(result)
        # effect_digest must match `^[a-f0-9]{64}$` (operator_mcp_receipt
        # schema); effect_ref stays bounded (run_id alone, mirrors
        # verify_bundle.py's own `_effect_ref_for` rationale).
        effect_ref = f"{OPERATION_KIND}:{run_id}"
        target_summary = ",".join(f"{t.target}={t.status}" for t in result.targets)
        digest_source = f"{effect_ref}:bundle_found={result.bundle_found}:targets={target_summary}"
        return ActionEffect(
            effect_kind="writeback_previewed",
            effect_digest=hashlib.sha256(digest_source.encode("utf-8")).hexdigest(),
            effect_ref=effect_ref,
        )

    def _build_result(execution: ExecutionOutcome) -> Mapping[str, Any]:
        if execution.status == "completed" and captured:
            result = captured[0]
            return {
                "status": "completed",
                "run_id": result.run_id,
                "bundle_id": result.bundle_id,
                "bundle_found": result.bundle_found,
                "generated_at": result.generated_at,
                "staging_root": result.staging_root,
                "targets": [
                    {"target": t.target, "status": t.status, "staged_path": t.staged_path}
                    for t in result.targets
                ],
                "canonical_refs_available": True,
            }
        if execution.status == "completed":
            # Exact replay of an already-terminal operation -- see module
            # docstring's "replay result-recovery gap" note.
            return {
                "status": "completed",
                "replayed": True,
                "canonical_refs_available": False,
            }
        return {"status": execution.status, "replayed": execution.replayed}

    action_manifest: dict[str, Any] = {
        "adapter": OPERATION_KIND,
        "run_id": run_id,
        "targets": list(normalized_targets),
    }

    return base.run_pipeline(
        ctx=ctx,
        confirmation_record=confirmation_record,
        presented_token=presented_token,
        action_manifest=action_manifest,
        actions=(ActionSpec(action_id="preview_writeback", run=_run),),
        build_result=_build_result,
        dry_run=dry_run,
        paths=resolved_paths,
        now=now,
        operations=operations,
        cancel_resume=cancel_resume,
    )


@dataclass(frozen=True)
class WritebackPreviewAdapter:
    """`base.OperatorAdapter` Protocol implementation for `writeback.preview`."""

    operation_kind: str = OPERATION_KIND

    def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:
        return invoke_preview(**kwargs)


PREVIEW_ADAPTER = WritebackPreviewAdapter()
base.register(PREVIEW_ADAPTER)
