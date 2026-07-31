"""`external_report.import` Operator MCP adapter (research-foundry-operator-
mcp-v1, M1 remainder leg B).

Wraps `research_foundry.services.external_research_import.import_external_report`
behind the fixed authorize -> consume -> execute -> bounded-result pipeline in
`operator_mcp_adapters.base.run_pipeline`, following the exact shape
`run_plan.py`/`swarm_start.py` established: build a `PolicyContext`, an
`ActionSpec` sequence, an `action_manifest`, and a `build_result` callback,
then hand all four to `base.run_pipeline`.

**ONE dry-run concept (m1-remainder-implementer-contract.md, decision D3).**
`base.run_pipeline`'s dry-run path runs only the five non-confirmation policy
stages (capability, RBAC, audit-health, guard, preflight) and NEVER invokes
`actions` at all. `import_external_report` also has its own native `dry_run`
parameter -- a true zero-effect plan by its own contract (no receipt,
checkpoint, staging artifact, lease, or timeline write). This adapter exposes
exactly ONE dry-run -- the substrate's: the live-path call inside `_run()`
below always passes `dry_run=False`. The service's own `dry_run` is therefore
deliberately UNREACHABLE from this adapter's surface. `resume` is forwarded
as a distinct, real live-path parameter -- it bypasses the service's
`PendingImportError` pending-checkpoint guard and continues from the stored
cursor -- and is therefore meaningful only when this adapter's own
`dry_run=False`; when `dry_run=True`, `base.run_pipeline` short-circuits
before `_run()` (and therefore `resume`) is ever consulted.

**`workspace_id` is a caller-supplied operation parameter, not an identity
field.** Unlike `run_id`/`intent_id` elsewhere in this family, there is no
pre-existing durable object to resolve an "owning workspace" from for a
brand-new import -- the caller's `workspace_id` argument IS the declaration
of which workspace this import targets, mirroring the CLI's own required
`--workspace` option (`cli_commands.py`'s `intake_external_report`, the M1 AC
CLI-parity target). The declared value is never trusted outright for
authorization: it is threaded into `resolved_target_workspaces` exactly as
declared, and `operator_mcp_policy`'s H3 cross-workspace gate
(`_check_identity_and_rbac`) independently re-derives the real configured
operator identity and denies (`not_found`, H6-shaped -- no distinguishing
leak) unless the two agree. A caller cannot import into any workspace but
the one local operator's own, regardless of what string it passes.

**No target-content signal for `effective_sensitivity`.** There is no
pre-existing object whose `governance.sensitivity` this operation could read
before authorization (contrast `run_plan.py`'s intent lookup) -- an inbound
packet's real content sensitivity is unknowable before `import_external_report`
inspects it, and inspecting it here ourselves would be a second, redundant
`inspect_packet` call outside that function's own single-inspection contract
(ERI round-2 audit finding #6). This adapter always resolves
`effective_sensitivity` via `policy.resolve_effective_sensitivity()` with no
arguments -- that function's own documented "no signal supplied" fail-closed
default (the STRICTEST label) -- rather than trusting any caller-supplied
guess about content it has not yet examined.

**Known limitation, not fixed here (out of this task's file ownership).**
Both `import_external_report` and `operator_mcp_adapters/base.py` are
outside this leg's file-ownership boundary. On a genuine exact-replay of an
already-terminal operation, `_run()` below is never invoked a second time,
so this module cannot reconstruct the full `ImportOutcome` refs from durable
operator-layer state alone -- the same documented "replay result-recovery
gap" `run_plan.py`/`swarm_start.py` already report for their own targets.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from research_foundry.paths import FoundryPaths
from research_foundry.services import external_research_import
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services.operator_cancel_resume_service import (
    ActionEffect,
    ActionSpec,
    ExecutionOutcome,
    OperatorCancelResumeService,
)
from research_foundry.services.operator_operation_service import OperatorOperationService

from . import base

__all__ = ["OPERATION_KIND", "ExternalReportImportAdapter", "ADAPTER", "invoke"]

OPERATION_KIND = "external_report.import"


def _target_ref_for(packet_dir: str, workspace_id: str) -> str:
    """Bounded, deterministic `import_packet` target reference.

    A raw `packet_dir` filesystem path cannot be used directly --
    `operator_mcp_policy._TARGET_REF_PATTERN` rejects `/` -- so this hashes
    the declared `packet_dir` + `workspace_id` instead of inspecting the
    packet itself (see module docstring's "no target-content signal" note
    for why this module never calls `inspect_packet` on its own)."""

    return hashlib.sha256(f"{packet_dir}:{workspace_id}".encode("utf-8")).hexdigest()


def _outcome_to_dict(outcome: "external_research_import.ImportOutcome") -> dict[str, Any]:
    """`ImportOutcome.safe_dict()` already carries every ref this task's
    contract names (`workspace_id`, `target_run_id`, `packet_digest`,
    `receipt_id`, `receipt_digest`, `status`) plus `complete`/`replayed`/
    `dry_run`/`block_reason`/`counts`/`cursor` -- the redaction-matrix-
    compliant subset (never packet-derived free text, never a resolved
    address). This is a lossless, non-mangling view of it, not an
    independently reconstructed one."""

    payload = outcome.safe_dict()
    payload["canonical_refs_available"] = True
    return payload


def invoke(
    *,
    packet_dir: str,
    workspace_id: str,
    idempotency_key: str,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    target_run_id: str | None = None,
    resume: bool = False,
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
    operations: OperatorOperationService | None = None,
    cancel_resume: OperatorCancelResumeService | None = None,
) -> base.OperatorAdapterResult:
    """The `external_report.import` Operator MCP tool.

    Deliberately accepts NO `identity`/`AuthIdentity`-shaped parameter
    anywhere -- the operator identity is resolved structurally, exactly
    once, inside `policy.PolicyContext.for_configured_operator` (P3
    implementer contract requirement 1, reused here verbatim).

    `confirmation_record`/`presented_token` are the caller's already-minted
    confirmation for this exact request -- both are ignored entirely when
    `dry_run=True`.

    Also deliberately accepts NO `sensitivity_ceiling` parameter (H7 defect
    fix, `8b694d5`) -- see `operator_mcp_adapters.resolve_local_sensitivity_
    ceiling`'s own docstring; resolved structurally, exactly once, from
    `foundry.yaml`'s `operator_mcp.sensitivity_ceiling`.

    See this module's own docstring for the dry-run/resume collapse (D3)
    and the `workspace_id`/`effective_sensitivity` resolution decisions.
    """

    from . import resolve_local_sensitivity_ceiling  # lazy: see operator_mcp_adapters/__init__.py's own docstring -- avoids the circular import a module-level import back into the package would create

    resolved_paths = paths or FoundryPaths.discover()
    sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)

    # No pre-existing target object to read a real sensitivity signal from
    # (module docstring) -- always the strictest label, never a caller-
    # supplied or content-derived guess.
    effective_sensitivity = policy.resolve_effective_sensitivity()

    target_ref = _target_ref_for(packet_dir, workspace_id)

    input_payload: dict[str, Any] = {
        "packet_dir": packet_dir,
        "workspace_id": workspace_id,
        "target_run_id": target_run_id,
        "resume": resume,
    }
    # PolicyContext.canonical_digest() hashes input_payload verbatim -- drop
    # None-valued optionals so two callers who both omit target_run_id
    # produce the SAME canonical digest (mirrors run_plan.py's own rationale).
    input_payload = {k: v for k, v in input_payload.items() if v is not None}

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling=sensitivity_ceiling,
        targets=(policy.TargetRef("import_packet", target_ref),),
        # H3: the caller's OWN declared workspace_id, exactly as supplied --
        # never trusted outright (see module docstring). The independent
        # RBAC re-derivation inside `_check_identity_and_rbac` is what
        # actually enforces this can only ever be the one configured
        # operator's own workspace.
        resolved_target_workspaces=(workspace_id,),
        input_payload=input_payload,
        paths=resolved_paths,
    )

    # Captures import_external_report's own ImportOutcome so `_build_result`
    # can read the real canonical refs after `run_or_replay` executes this
    # action -- see module docstring's "known limitation" note for why this
    # is sometimes empty even on a "completed" ExecutionOutcome.
    captured: list["external_research_import.ImportOutcome"] = []

    def _run() -> ActionEffect:
        outcome = external_research_import.import_external_report(
            packet_dir,
            workspace_id=workspace_id,
            target_run_id=target_run_id,
            dry_run=False,  # substrate's dry-run is the ONE dry-run this adapter exposes (D3)
            resume=resume,
            paths=resolved_paths,
        )
        captured.append(outcome)
        # effect_digest must match `^[a-f0-9]{64}$` (operator_mcp_receipt
        # schema); effect_ref stays well under maxLength: 256 (receipt_digest
        # is itself a bounded sha256 hex string).
        effect_ref = f"{OPERATION_KIND}:{outcome.receipt_digest}"
        return ActionEffect(
            effect_kind="external_report_imported",
            effect_digest=hashlib.sha256(effect_ref.encode("utf-8")).hexdigest(),
            effect_ref=effect_ref,
        )

    def _build_result(execution: ExecutionOutcome) -> Mapping[str, Any]:
        # base.run_pipeline only ever calls this for "completed"/"canceled"
        # -- "failed"/"denied" are already turned into a build_error
        # envelope before build_result is reached.
        if execution.status == "completed" and captured:
            return _outcome_to_dict(captured[0])
        if execution.status == "completed":
            # Exact replay of an already-terminal operation -- see module
            # docstring's "known limitation" note.
            return {
                "status": "completed",
                "replayed": True,
                "canonical_refs_available": False,
            }
        return {"status": execution.status, "replayed": execution.replayed}

    action_manifest: dict[str, Any] = {
        "adapter": OPERATION_KIND,
        "packet_dir": packet_dir,
        "workspace_id": workspace_id,
        "target_run_id": target_run_id,
        "resume": resume,
    }

    return base.run_pipeline(
        ctx=ctx,
        confirmation_record=confirmation_record,
        presented_token=presented_token,
        action_manifest=action_manifest,
        actions=(ActionSpec(action_id="import_external_report", run=_run),),
        build_result=_build_result,
        dry_run=dry_run,
        paths=resolved_paths,
        now=now,
        operations=operations,
        cancel_resume=cancel_resume,
    )


@dataclass(frozen=True)
class ExternalReportImportAdapter:
    """`base.OperatorAdapter` Protocol implementation for `external_report.import`."""

    operation_kind: str = OPERATION_KIND

    def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:
        return invoke(**kwargs)


ADAPTER = ExternalReportImportAdapter()
base.register(ADAPTER)
