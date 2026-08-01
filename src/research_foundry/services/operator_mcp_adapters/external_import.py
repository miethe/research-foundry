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

**`target_run_id` is a sibling-parameter authorization gap (F2 fix).** A
caller-declared `workspace_id` is re-derived and independently checked by
H3's RBAC gate (see above), but `target_run_id` -- a DISTINCT, optional
reference to a pre-existing run that `import_external_report` records
import activity against (`external_research_import.py:611`) -- was
previously never authorized at all: only `workspace_id` (the packet's OWN
declared workspace) was threaded into `resolved_target_workspaces`. A caller
could therefore supply their own `workspace_id` (which passes H3) together
with a `target_run_id` belonging to an entirely different workspace, and the
canonical service would still record import activity against that foreign
run. When `target_run_id` is supplied, this adapter now ALSO resolves ITS
OWN owning workspace from its already-governed `run.yaml` -- the SAME
read-only, fail-closed-to-`None` pattern `source_ingest._resolve_run_
context`/`swarm_start._resolve_run_context` use for the identical field --
and declares it as a second `TargetRef("run", target_run_id)`, whose
resolved owning workspace is threaded into `resolved_target_workspaces`
alongside the packet's. H3's existing per-entry RBAC loop
(`_check_identity_and_rbac`, unmodified) then denies unless BOTH the
packet's declared workspace AND the target run's real owning workspace
match the one configured operator identity -- a missing/foreign/malformed
target run resolves to `None` and denies with the SAME `not_found` shape
every other target-authorization denial in this family gets (no
distinguishing leak).

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
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
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
from research_foundry.yamlio import load_yaml

from . import base

_logger = logging.getLogger(__name__)

__all__ = ["OPERATION_KIND", "ExternalReportImportAdapter", "ADAPTER", "invoke"]

OPERATION_KIND = "external_report.import"


def _resolved_within(root: Path, candidate: Path) -> Path | None:
    """M2 fix cycle 3 (F3.1/SEC2-1) -- AUTHORITATIVE, not advisory: returns
    the resolved, root-anchored `Path` when `candidate` is contained,
    `None` otherwise. Originally bool-returning (M2 fix cycle 2); the
    security re-gate found that a bool-returning validator lets the check
    and the DOWNSTREAM USE disagree about what a RELATIVE `candidate` means
    -- this function resolved a relative value against `root`, but the
    caller then forwarded the ORIGINAL, UNRESOLVED string to
    `import_external_report`, which resolves relative paths against the
    server PROCESS's CWD, a different anchor entirely. A caller could name
    a perfectly "contained" relative path (no `..` needed at all) and have
    it read from wherever the process happened to be launched. Returning
    the resolved `Path` and requiring the caller to forward THAT (never the
    raw string) closes the anchor mismatch structurally: whatever
    `import_external_report` does internally with an already-absolute path
    cannot depend on CWD.

    The exact resolve-then-contain posture `verify_bundle.
    _explicit_path_within_run` established (F5): resolves both `root` and
    `candidate` (symlinks included -- SEC-1's own PoC used a symlink
    planted inside the workspace to reach `/etc`, so a lexical-only check
    would not close it) and requires `candidate` to land AT `root` or
    somewhere BENEATH it. Deliberately never probes whether the resolved
    `candidate` exists -- an existence check on a location outside the
    authorized boundary would itself be an oracle (the same class of leak
    F6/H6 close elsewhere in this family). `candidate` may be relative
    (joined under `root` first, still returned as the resolved absolute
    form) or absolute (resolved as given) -- callers that must reject a
    relative `candidate` outright (see `packet_dir`'s own check in
    `_run()`) do so themselves, BEFORE calling this function; this function
    itself still accepts and resolves a relative candidate for the
    `target_run_id` containment call site below, which never forwards its
    own string anywhere -- only the resolved containment DECISION matters
    there, not a substituted value."""

    try:
        root_resolved = root.resolve()
        effective = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    except OSError as exc:
        _logger.warning(
            "operator_mcp_adapters.external_import: path resolution failed (%s) -- "
            "denying (never a permissive default)",
            type(exc).__name__,
        )
        return None
    if effective == root_resolved or root_resolved in effective.parents:
        return effective
    return None


def _resolve_run_workspace_id(run_id: str, paths: FoundryPaths) -> str | None:
    """Read-only, best-effort lookup of `run_id`'s own declared
    `workspace_id` field (from `run.yaml`) -- swallows EVERY exception
    (missing run, malformed YAML, filesystem error) and resolves to `None`
    on ANY failure, including a non-dict document or a non-string/blank
    field -- never a permissive fallback. Mirrors
    `source_ingest._resolve_run_context`/`swarm_start._resolve_run_context`'s
    identical field resolution (F2 fix, module docstring).

    **M2 fix cycle 2 (path-containment sweep, sibling to SEC-1).**
    `target_run_id` reaches `paths.run_paths(run_id).run_yaml` the exact
    same way EVERY `run_id`-accepting adapter in this family resolves its
    own run context, and does so BEFORE `ctx`/authorization exists (the
    identical "necessary before `ctx` exists" category `run_plan.py`'s own
    docstring documents for its own intent lookup). Contained to
    `paths.runs` FIRST -- before the read is even attempted -- so a
    traversal-shaped `target_run_id` (e.g. `".."`) can never cause a read
    outside the `runs/` tree, regardless of what `operator_mcp_policy`'s own
    `_TARGET_REF_PATTERN` would eventually reject it for downstream (that
    downstream rejection happens too late to prevent this read, exactly the
    ordering hazard SEC-1 named for `packet_dir`)."""

    if _resolved_within(paths.runs, Path(run_id)) is None:
        _logger.warning(
            "operator_mcp_adapters.external_import: target_run_id=%s escapes the "
            "authorized runs/ tree -- resolving owning workspace to None (deny, "
            "never a fallback)",
            run_id,
        )
        return None
    try:
        run_doc = load_yaml(paths.run_paths(run_id).run_yaml)
    except Exception as exc:
        _logger.warning(
            "operator_mcp_adapters.external_import: run.yaml lookup failed (%s) for "
            "target_run_id=%s -- resolving owning workspace to None (deny, never a fallback)",
            type(exc).__name__,
            run_id,
        )
        return None
    if not isinstance(run_doc, dict):
        return None
    workspace_id = run_doc.get("workspace_id")
    return workspace_id if isinstance(workspace_id, str) and workspace_id else None


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

    targets: list[policy.TargetRef] = [policy.TargetRef("import_packet", target_ref)]
    # H3: the caller's OWN declared workspace_id, exactly as supplied --
    # never trusted outright (see module docstring). The independent RBAC
    # re-derivation inside `_check_identity_and_rbac` is what actually
    # enforces this can only ever be the one configured operator's own
    # workspace.
    resolved_target_workspaces: list[str | None] = [workspace_id]
    if target_run_id is not None:
        # F2 fix (module docstring): target_run_id is a DISTINCT target the
        # canonical service records import activity against -- it must be
        # independently authorized, never merely echoed through because
        # workspace_id (a sibling, unrelated parameter) already checked out.
        targets.append(policy.TargetRef("run", target_run_id))
        resolved_target_workspaces.append(_resolve_run_workspace_id(target_run_id, resolved_paths))

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling=sensitivity_ceiling,
        targets=tuple(targets),
        resolved_target_workspaces=tuple(resolved_target_workspaces),
        input_payload=input_payload,
        paths=resolved_paths,
    )

    # Captures import_external_report's own ImportOutcome so `_build_result`
    # can read the real canonical refs after `run_or_replay` executes this
    # action -- see module docstring's "known limitation" note for why this
    # is sometimes empty even on a "completed" ExecutionOutcome.
    captured: list["external_research_import.ImportOutcome"] = []

    def _run() -> ActionEffect:
        # SEC-1/SEC2-1 fix (M2 fix cycles 2+3, BLOCKING): `packet_dir` must
        # resolve inside the authorized workspace tree -- originally
        # forwarded VERBATIM to `import_external_report`, which recursively
        # `os.scandir`s it, making any absolute host path (`/etc`,
        # `~/.ssh`, `/var/root`, a symlink planted inside the workspace
        # pointing anywhere) a caller-reachable existence/type/symlink/
        # content oracle over the ENTIRE host filesystem (SEC-1). Cycle 2's
        # bool-returning guard closed every ABSOLUTE escape but left a
        # RELATIVE one open: the guard resolved a relative candidate
        # against `resolved_paths.root`, then this closure forwarded the
        # caller's ORIGINAL, unresolved string -- which
        # `import_external_report` resolves against the server PROCESS's
        # CWD, a different anchor (SEC2-1). Fixed by (a) rejecting a
        # relative `packet_dir` OUTRIGHT -- there is no ambiguity to
        # resolve if only an absolute, already-unambiguous value is ever
        # accepted -- and (b) forwarding the RESOLVED, root-anchored `Path`
        # `_resolved_within` returns, never the caller's raw string, so
        # even a symlink or relative-looking segment inside an otherwise
        # absolute `packet_dir` cannot reintroduce a CWD-dependent read.
        # Checked HERE, inside `_run()` -- after `base.run_pipeline` has
        # already authorized and durably consumed the operation (F6
        # posture) -- never before `ctx`. Containment root is
        # `resolved_paths.root` -- the ONE configured operator's own
        # authorized workspace tree, re-derived here, never caller-supplied
        # -- not merely a specific run's directory, since a staging-only
        # import (`target_run_id=None`) has no run tree to bind to at all.
        packet_path = Path(packet_dir)
        if not packet_path.is_absolute():
            raise RuntimeError(
                "external_report.import: packet_dir must be an absolute, "
                "in-workspace path (relative values are refused outright)"
            )
        resolved_packet_dir = _resolved_within(resolved_paths.root, packet_path)
        if resolved_packet_dir is None:
            raise RuntimeError(
                "external_report.import: packet_dir escapes the authorized workspace tree"
            )
        outcome = external_research_import.import_external_report(
            str(resolved_packet_dir),  # the RESOLVED, root-anchored path -- never the caller's raw string
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
