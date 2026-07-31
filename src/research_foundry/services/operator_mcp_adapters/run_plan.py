"""`run.plan` Operator MCP adapter (research-foundry-operator-mcp-v1 P3, OPM-3.1).

Wraps `research_foundry.services.planning.plan_run` (signature at
`planning.py:565`) behind the fixed authorize -> consume -> execute ->
bounded-result pipeline in `operator_mcp_adapters.base.run_pipeline`. This is
the FIRST P3 adapter, built to prove the substrate's shape -- OPM-3.2/3.3/3.4
(`swarm.start`/`job.status`/`job.cancel`/`job.resume`) follow the same
pattern: build a `PolicyContext`, an `ActionSpec` sequence, an
`action_manifest`, and a `build_result` callback, then hand all four to
`base.run_pipeline`.

**Sensitivity resolution happens before authorization (documented, bounded
exception)**: `operator_mcp_policy.PolicyContext` requires a real
`effective_sensitivity` at construction (`__post_init__` rejects anything
outside the closed vocabulary) -- there is no way to build `ctx` without
first knowing it. For `run.plan`, the only meaningful source of that value
is the target intent's own `governance.sensitivity` field, so this module
reads the intent (via `planning.load_intent`, read-only) BEFORE `ctx` exists
and therefore before authorization. This does NOT read a `target` in the
`operator_mcp_policy` sense: `run.plan` declares no targets at all
(`operator_mcp_policy._REQUIRED_TARGET_KINDS["run.plan"] == frozenset()`),
and `"intent"` is not a member of `TARGET_KINDS` -- it is an input parameter
this adapter resolves sensitivity from, the same role `writeback_targets`/
`model_provider` play for `writeback.preview`. Any failure reading the
intent (missing, malformed, or any other exception) is swallowed here and
resolves to the STRICTEST sensitivity via `policy.resolve_effective_
sensitivity(None)` -- never a permissive default -- so a genuinely missing
intent is denied later, through the NORMAL authorization/execution path
(the confirmed operation's own action raises `NotFoundError`, which
`run_or_replay`'s action-failure handling turns into a governed `"failed"`
terminal outcome), not through a special early-exit branch here.

**Replay result-recovery gap (documented limitation, NOT fixed here)**: on a
genuine exact-replay of an ALREADY-terminal operation (`run_or_replay`'s own
fast path -- a caller re-presenting an already-consumed confirmation after
the original run finished), the `ActionSpec.run()` closure below is never
invoked a second time, so the captured `PlanResult` is unavailable and this
adapter cannot reconstruct the full canonical refs from durable
operator-layer state alone: `OperatorReceiptService` (P2, out of this task's
file ownership) exposes no public reader for a persisted `effect_ref` by
`operation_id`/`action_id` -- only `load_terminal_receipt` (whose
`effect_receipt_refs` are content digests, not the refs themselves) and
`load_checkpoint`. `_build_result` below returns a bounded, honest partial
payload on that path (`"canonical_refs_available": False`) rather than
fabricating refs. A follow-up adding such a reader to
`operator_receipt_service.py` would close this; this task does not own that
file (see the P3 implementer contract's file-ownership list) and reports the
gap rather than making the change.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Mapping

from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services.operator_cancel_resume_service import (
    ActionEffect,
    ActionSpec,
    ExecutionOutcome,
    OperatorCancelResumeService,
)
from research_foundry.services.operator_operation_service import OperatorOperationService

from . import base

# `research_foundry.services.planning` is imported LAZILY (inside `invoke`
# and `_resolve_intent_sensitivity` below), never at module level, and
# ONLY for type annotations under TYPE_CHECKING here. This is NOT this
# adapter's own serve-extra concern (requirement 7) -- `planning.py`
# itself is careful (its own `AuthIdentity` import is TYPE_CHECKING-only,
# with the same rationale). The reason for the lazy import is ONE HOP
# further down `planning.py`'s import graph: it imports
# `research_foundry.services.assertion_catalog` at module level, and
# THAT module imports `..api.auth.provider` (which drags in
# fastapi/starlette) eagerly, NOT under TYPE_CHECKING. `assertion_catalog.py`
# is outside this task's file ownership (only the `operator_mcp_adapters`
# package + its two test files) -- reported as a required follow-up in
# this task's report, not fixed here. Deferring the import means the
# `operator_mcp_adapters` PACKAGE (this substrate's own deliverable)
# still imports cleanly without the `[serve]` extra; only a REAL call to
# `invoke()` (which necessarily calls `planning.plan_run`) requires it,
# exactly as it already would via `cli_commands.py`'s own `rf plan`
# command today.
if TYPE_CHECKING:
    from research_foundry.services import planning

_logger = logging.getLogger(__name__)

__all__ = ["OPERATION_KIND", "RunPlanAdapter", "ADAPTER", "invoke"]

OPERATION_KIND = "run.plan"


def _effect_ref_for(result: "planning.PlanResult") -> str:
    """Bounded `ActionEffect.effect_ref` -- `operator_mcp_receipt.schema.yaml`'s
    `effect_receipt.effect_ref` caps at `maxLength: 256`. `run_id` alone
    (bounded ~62 chars: `rf_run_<8-digit-date>_<slug up to 48 chars>`,
    optionally `disambiguate_id`-suffixed) is used rather than concatenating
    all four canonical ids -- empirically, `run_id` + `brief_id` + `swarm_id`
    + `routing_id` joined can exceed 256 chars for a long intent title (a
    real schema-validation denial observed while developing this adapter,
    not a hypothetical). See this module's docstring's "replay
    result-recovery gap" note: the full four-id payload is NOT recoverable
    from `effect_ref` alone on any path regardless of this encoding choice,
    so a shorter, always-bounded encoding loses nothing that was actually
    guaranteed before."""

    return f"{OPERATION_KIND}:{result.run_id}"


def _plan_result_to_dict(result: "planning.PlanResult") -> dict[str, Any]:
    return {
        "status": "completed",
        "run_id": result.run_id,
        "brief_id": result.brief_id,
        "swarm_id": result.swarm_id,
        "routing_id": result.routing_id,
        "run_dir": str(result.run_dir),
        "brief_path": str(result.brief_path),
        "swarm_path": str(result.swarm_path),
        "routing_path": str(result.routing_path),
        "evidence_plan_ref": result.evidence_plan_ref,
        "canonical_refs_available": True,
    }


def _resolved_within(root: Path, candidate: Path) -> bool:
    """M2 fix cycle 2, path-containment sweep (sibling to SEC-1) -- the same
    resolve-then-contain posture `external_import._resolved_within`/
    `source_ingest._resolved_within` establish, duplicated here per this
    family's own "adapter modules do not cross-import each other's private
    helpers" convention. Never probes whether the resolved `candidate`
    exists -- an existence check outside the authorized boundary would
    itself be an oracle (F6/H6's own class of leak)."""

    try:
        root_resolved = root.resolve()
        effective = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    except OSError as exc:
        _logger.warning(
            "operator_mcp_adapters.run_plan: path resolution failed (%s) -- denying "
            "(never a permissive fallback)",
            type(exc).__name__,
        )
        return False
    return effective == root_resolved or root_resolved in effective.parents


def _resolve_intent_sensitivity(intent_id: str, paths: FoundryPaths) -> str | None:
    """Best-effort, read-only lookup of the target intent's declared
    `governance.sensitivity` -- swallows EVERY exception (missing intent,
    malformed YAML, anything else) and returns `None` on failure, which
    `policy.resolve_effective_sensitivity` resolves to the STRICTEST label
    (fail-closed, never permissive) -- see module docstring.

    **M2 fix cycle 2 (path-containment sweep, sibling to SEC-1) -- a NEW
    instance found, same severity class as `packet_dir`.**
    `planning.load_intent` builds `paths.intents_active / f"{intent_id}.
    yaml"` -- an F-STRING join, not a single safe path component. Because
    Python's `Path.__truediv__` treats a right-hand operand containing `/`
    as sub-path segments (not a literal filename) and DISCARDS the left
    operand entirely when the right-hand side is itself absolute, an
    `intent_id` of `"/etc/passwd"` resolves `load_intent`'s own join to the
    literal absolute path `/etc/passwd.yaml` -- a full escape, no
    containment anywhere in that call chain, and `intent_id` is NEVER a
    `TargetRef` for `run.plan` (module docstring's own "no targets at all"
    section) so `operator_mcp_policy._TARGET_REF_PATTERN` never validates it
    either, at any point. Contained HERE, to `paths.intents_active`,
    BEFORE `load_intent` is ever called -- this is the FIRST thing `invoke()`
    does (module docstring's "sensitivity resolution happens before
    authorization" section), so this containment check is the only gate
    that will ever run for this parameter."""

    if not _resolved_within(paths.intents_active, Path(f"{intent_id}.yaml")):
        _logger.warning(
            "operator_mcp_adapters.run_plan: intent_id=%s escapes the authorized "
            "intents/active/ tree -- resolving to strictest sensitivity (deny, "
            "never a permissive fallback)",
            intent_id,
        )
        return None

    from research_foundry.services import planning  # lazy: see module docstring

    try:
        intent = planning.load_intent(intent_id, paths=paths)
    except Exception as exc:
        _logger.warning(
            "operator_mcp_adapters.run_plan: intent sensitivity lookup failed (%s) for "
            "intent_id=%s -- resolving to strictest sensitivity",
            type(exc).__name__,
            intent_id,
        )
        return None
    governance = intent.get("governance") if isinstance(intent, dict) else None
    sensitivity = governance.get("sensitivity") if isinstance(governance, dict) else None
    return sensitivity if isinstance(sensitivity, str) else None


def invoke(
    *,
    intent_id: str,
    idempotency_key: str,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    depth: str = "standard",
    audience: str = "technical",
    max_cost_usd: float = 5.0,
    max_runtime_minutes: int = 60,
    freshness_days: int = 180,
    profile: str | None = None,
    project: str | None = None,
    retrieval_policy: str | None = None,
    retrieval_limits: Mapping[str, Any] | None = None,
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
    operations: OperatorOperationService | None = None,
    cancel_resume: OperatorCancelResumeService | None = None,
) -> base.OperatorAdapterResult:
    """The `run.plan` Operator MCP tool.

    Deliberately accepts NO `identity`/`workspace_id`/`AuthIdentity`-shaped
    parameter anywhere -- the operator identity is resolved structurally,
    exactly once, inside `policy.PolicyContext.for_configured_operator`
    (requirement 1 of the P3 implementer contract).

    `confirmation_record`/`presented_token` are the caller's already-minted
    confirmation for this exact request (from `operation.preflight` -- P1
    scope, no transport in this repo yet) -- both are ignored entirely when
    `dry_run=True`.

    Also deliberately accepts NO `sensitivity_ceiling` parameter (P3
    hardening pass, H7 defect fix) -- see
    `operator_mcp_adapters.resolve_local_sensitivity_ceiling`'s own
    docstring for the full defect and remediation rationale. The ceiling is
    resolved structurally, exactly once per call, from `foundry.yaml`'s
    `operator_mcp.sensitivity_ceiling`, the same way identity is resolved.
    """

    from research_foundry.services import planning  # lazy: see module docstring
    from . import resolve_local_sensitivity_ceiling  # lazy: see operator_mcp_adapters/__init__.py's own docstring -- avoids the circular import a module-level import back into the package would create

    resolved_paths = paths or FoundryPaths.discover()
    sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)

    intent_sensitivity = _resolve_intent_sensitivity(intent_id, resolved_paths)
    effective_sensitivity = policy.resolve_effective_sensitivity(intent_sensitivity)

    input_payload: dict[str, Any] = {
        "intent_id": intent_id,
        "depth": depth,
        "audience": audience,
        "max_cost_usd": max_cost_usd,
        "max_runtime_minutes": max_runtime_minutes,
        "freshness_days": freshness_days,
        "profile": profile,
        "project": project,
        "retrieval_policy": retrieval_policy,
        # F2.1 fix (TERRA-3): retrieval_limits reaches planning.plan_run
        # below (see _run()) exactly like every other keyword here -- it
        # MUST be bound into the canonical digest, or a confirmation minted
        # for one retrieval_limits value (including None/unset) could be
        # replayed with a different one. Coerced to a plain dict (never the
        # caller's own Mapping instance) so canonical_json() sees the same
        # JSON-primitive shape every other adapter in this family already
        # produces for its own dict-shaped optionals.
        "retrieval_limits": dict(retrieval_limits) if retrieval_limits is not None else None,
    }
    # PolicyContext.canonical_digest() hashes input_payload verbatim -- drop
    # None-valued optionals so two callers who both omit the same optional
    # produce the SAME canonical digest (and therefore correctly collapse
    # to the same idempotent operation under a shared idempotency_key).
    input_payload = {k: v for k, v in input_payload.items() if v is not None}

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling=sensitivity_ceiling,
        input_payload=input_payload,
        paths=resolved_paths,
    )

    # Captures plan_run's own PlanResult so `_build_result` can read the
    # real canonical refs after `run_or_replay` executes this action -- see
    # module docstring's "replay result-recovery gap" note for why this box
    # is sometimes empty even on a "completed" ExecutionOutcome.
    captured: list["planning.PlanResult"] = []

    def _run() -> ActionEffect:
        # M2 fix cycle 2, path-containment sweep -- closes the RESIDUAL
        # exposure `_resolve_intent_sensitivity`'s own pre-auth containment
        # check cannot fully close on its own: if a caller's local ceiling
        # is permissive enough to admit the STRICTEST sensitivity label (the
        # value a rejected `intent_id` resolves to), the guard stage would
        # never deny, and this closure would otherwise reach `planning.
        # plan_run`, which calls `planning.load_intent` again internally --
        # the SAME vulnerable f-string join `_resolve_intent_sensitivity`'s
        # own docstring documents, reachable a second time, this time past a
        # real minted confirmation. `planning.py` is out of this leg's file
        # ownership, so this module-level, adapter-side re-check is the only
        # available closure point.
        if not _resolved_within(resolved_paths.intents_active, Path(f"{intent_id}.yaml")):
            raise RuntimeError(
                "run.plan: intent_id escapes the authorized intents/active/ tree"
            )
        result = planning.plan_run(
            intent_id,
            depth=depth,
            audience=audience,
            max_cost_usd=max_cost_usd,
            max_runtime_minutes=max_runtime_minutes,
            freshness_days=freshness_days,
            profile=profile,
            project=project,
            identity=ctx.identity,
            retrieval_policy=retrieval_policy,
            retrieval_limits=retrieval_limits,
            paths=resolved_paths,
        )
        captured.append(result)
        # effect_digest must match `^[a-f0-9]{64}$` (operator_mcp_receipt
        # schema) -- a real sha256 hex digest, never `result.run_id` itself
        # (which is a slug, not a digest).
        effect_ref = _effect_ref_for(result)
        return ActionEffect(
            effect_kind="run_planned",
            effect_digest=hashlib.sha256(effect_ref.encode("utf-8")).hexdigest(),
            effect_ref=effect_ref,
        )

    def _build_result(execution: ExecutionOutcome) -> Mapping[str, Any]:
        # base.run_pipeline only ever calls this for "completed"/"canceled"
        # -- "failed"/"denied" are already turned into a build_error
        # envelope before build_result is reached.
        if execution.status == "completed" and captured:
            return _plan_result_to_dict(captured[0])
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
        "intent_id": intent_id,
        "depth": depth,
        "audience": audience,
    }

    return base.run_pipeline(
        ctx=ctx,
        confirmation_record=confirmation_record,
        presented_token=presented_token,
        action_manifest=action_manifest,
        actions=(ActionSpec(action_id="plan_run", run=_run),),
        build_result=_build_result,
        dry_run=dry_run,
        paths=resolved_paths,
        now=now,
        operations=operations,
        cancel_resume=cancel_resume,
    )


@dataclass(frozen=True)
class RunPlanAdapter:
    """`base.OperatorAdapter` Protocol implementation for `run.plan`."""

    operation_kind: str = OPERATION_KIND

    def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:
        return invoke(**kwargs)


ADAPTER = RunPlanAdapter()
base.register(ADAPTER)
