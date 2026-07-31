"""`run.verify` + `run.bundle` Operator MCP adapters (research-foundry-
operator-mcp-v1 M1 remainder, leg C).

Wraps `research_foundry.services.verification.verify_report` and
`research_foundry.services.writeback.build_bundle` behind the fixed
authorize -> consume -> execute -> bounded-result pipeline in
`operator_mcp_adapters.base.run_pipeline`, following the exact shape
`run_plan.py`/`swarm_start.py` established: build a `PolicyContext`, an
`ActionSpec` sequence, an `action_manifest`, and a `build_result` callback,
then hand all four to `base.run_pipeline`. Both adapters live in ONE module
(mirroring `job_lifecycle.py`'s multi-adapter-per-file convention) because
`run.bundle`'s own prerequisite check is "is there a passing `run.verify`
result for this run" -- the two operation kinds are conceptually paired.

**`run.verify`: non-passing is a governed RESULT, not an execution failure
(implementer contract D4).** `verify_report` never raises on a failed
verification (see module-level `_verify_prerequisites_met`'s own docstring
for the traced evidence) -- it always returns a `VerificationResult` with
`.passed`/`.exit_code` describing the verdict. `_run()` below therefore
ALWAYS returns normally, regardless of `.passed` -- the adapter's bounded
result carries `passed: False` plus the unsupported-claim summary when
verification did not pass; the `OperatorAdapterResult` itself is `ok=True`.
The one exception (`_verify_prerequisites_met` failing) is a genuinely
*different* condition -- no report or no claim ledger exists at all, so
there is nothing for `verify_report` to verify -- and is denied at the
PREREQUISITE stage, before `ctx` is even constructed, with zero effects
(see that function's own docstring for why this matters: `verify_report`'s
bare-invocation path never raises for a missing report/ledger, but it DOES
unconditionally call `rp.ensure_scaffold()` and write `reviews/
verification.yaml`, neither of which should happen for a run with nothing
meaningful to verify).

Note on the implementer contract's phrasing: D4 also names "quarantine" as
a prerequisite-denial condition alongside missing report/claim ledger. A
dedicated investigation (M1 leg C, this task) found NO run-level quarantine
concept anywhere in this codebase -- `quarantine`/`quarantined` exists only
for ERI (external-import) action outcomes and canonical-claim/inference
crash-recovery directories, neither of which `verify_report` touches or
`run.verify` targets. Treated as either a drafting artifact bleeding over
from the ERI section of the same worknotes (`m1-remainder-scoping.md`'s own
`ImportOutcome` status enum lists `"completed_with_quarantine"` right next
to where this phrase likely originated) or, charitably, as loosely
gesturing at "any prerequisite-stage denial condition" -- which for
`run.verify` is exactly the two things implemented here: missing input, and
the H7 above-sensitivity-ceiling guard. Reported, not silently dropped; see
this task's completion note.

**`run.bundle`: the block is a PREREQUISITE, not a delegated check
(implementer contract D5).** `build_bundle(verify=True)` NEVER blocks on a
failed verification -- it writes `evidence_bundle.yaml` unconditionally,
marking it `status="draft"`/`governance.approved_for_writeback=False`, and
its own bare `except Exception` around the internal `verify_report` call
swallows even a verification *crash* into the same "not verified" state
(traced in `m1-remainder-unknowns.md` U2). This adapter therefore enforces
the block itself, in two places:

1. **Prerequisite stage** (`_bundle_prerequisites_met`, before `ctx` is
   constructed): requires an existing, on-disk `reviews/verification.yaml`
   whose `passed` field is `True` for this run. Absent, unparsable, or
   non-passing -> deny `preflight_failed`, `build_bundle` is NEVER called,
   zero effects.
2. **Live-path re-check** (`_run()`'s own body): after calling
   `writeback.build_bundle(run_id, verify=True, paths=...)`, this module
   inspects the returned `BundleResult.verified`. If it is `False` --
   meaning verification state changed between step 1's prerequisite read
   and this call actually running (a real race: another caller invalidated
   the run's verification between the two) -- this module RAISES inside
   the closure, which `operator_cancel_resume_service.run_actions` turns
   into a governed `"failed"` terminal outcome (`ok=False`), rather than
   reporting a draft bundle as a successful result.

**Known limitation (stated plainly, per the implementer contract, NOT
papered over here): in the race above, `build_bundle` has ALREADY WRITTEN
`evidence_bundle.yaml` to disk (as a `status="draft"`,
`approved_for_writeback=False` bundle) before this module's own `.verified`
check ever runs and raises.** The failed `run.bundle` operation is
therefore NOT perfectly zero-effect in that one race window -- a draft,
explicitly-not-approved-for-writeback bundle file is left behind. Closing
this requires changing `writeback.build_bundle` itself (e.g. checking
verification status before writing, or accepting an injected
pre-verified flag) -- `writeback.py` is out of this task's file ownership
(a declared serialization barrier shared with M2, per the implementer
contract's hard boundaries) and is not touched here. Logged as a follow-up.

**Sensitivity/workspace resolution (mirrors `swarm_start.py`'s own
"resolved, never caller-supplied" doctrine).** Both `run_id`'s sensitivity
and its owning workspace are read-only, best-effort resolutions from the
target run's own `run.yaml` -- never a caller-suppliable parameter. Every
field resolves to `None` on ANY failure (missing run, malformed YAML), which
denies (strictest sensitivity, or an RBAC `not_found` for an unresolvable
owning workspace) rather than defaulting -- the same fail-closed convention
`run_plan.py`/`swarm_start.py` already established.

**`sensitivity_ceiling` (P3 hardening pattern, mandatory for every
adapter).** Neither `invoke_verify` nor `invoke_bundle` accepts a
`sensitivity_ceiling` parameter -- both resolve it structurally via
`operator_mcp_adapters.resolve_local_sensitivity_ceiling`, exactly like
every other adapter in this family.

**H7 negative-fixture adaptation.** `run_plan.py`'s own H7 test compares an
above-ceiling denial to a genuinely-*missing*-intent denial (both reach the
guard stage). That comparison does not apply cleanly here: BOTH adapters'
own prerequisite checks (missing report/ledger for `run.verify`; missing
passing verification for `run.bundle`) intercept a target that does not
exist yet, denying with `preflight_failed` BEFORE `ctx` -- and therefore
the sensitivity ceiling -- is ever constructed (the exact same situation
`swarm_start.py`'s own H7 test documents and adapts to, for the same
reason: its own budget/timeout/profile preflight intercepts a missing run
first). This module's test suite therefore follows `swarm_start.py`'s own
precedent: compares an above-ceiling denial for a REAL, fully-prerequisite-
satisfied target against a WRONG-WORKSPACE denial for the SAME real
target -- both reach `ctx` and deny with the same byte-identical
`not_found` shape (guard stage vs. rbac stage), proving the one-denial-
shape guarantee without a target-existence confound.

**Replay result-recovery gap (documented limitation, NOT fixed here, same
shape as `run_plan.py`'s own).** On a genuine exact-replay of an ALREADY-
terminal operation, `_run()` is never invoked a second time, so `captured`
is empty and the real canonical refs cannot be reconstructed from durable
operator-layer state alone (`OperatorReceiptService` exposes no public
reader for a persisted `effect_ref` by `operation_id`/`action_id`).
`_build_result` returns a bounded, honest partial payload on that path
(`"canonical_refs_available": False`) rather than fabricating one -- same
follow-up gap `run_plan.py`/`swarm_start.py` already report, not re-solved
here (out of this task's file ownership: `operator_receipt_service.py`).
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
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

# `verification`/`writeback` are imported LAZILY (inside each `invoke_*`
# function body), never at module level, mirroring `run_plan.py`'s own
# rationale for lazily importing `planning`: `verification.py` imports
# `..api.auth.provider.AuthIdentity` at module level (see that module's own
# import block), and this package's own `operator_mcp_adapters` import graph
# must keep importing cleanly without the `[serve]` extra (requirement 7,
# `base.py`'s own module docstring). `writeback.py` does not currently carry
# the same eager import, but is lazily imported here too for the same
# defensive reason and for symmetry with its paired `run.verify` adapter in
# this same module.
if TYPE_CHECKING:
    from research_foundry.services import verification, writeback

_logger = logging.getLogger(__name__)

__all__ = [
    "VERIFY_OPERATION_KIND",
    "BUNDLE_OPERATION_KIND",
    "RunVerifyAdapter",
    "RunBundleAdapter",
    "VERIFY_ADAPTER",
    "BUNDLE_ADAPTER",
    "invoke_verify",
    "invoke_bundle",
]

VERIFY_OPERATION_KIND = "run.verify"
BUNDLE_OPERATION_KIND = "run.bundle"


@dataclass(frozen=True)
class _RunContext:
    """Read-only, best-effort resolution of the target run's own declared
    sensitivity and owning workspace -- see module docstring's "sensitivity/
    workspace resolution" section. Both fields are `None` on ANY resolution
    failure (missing run, malformed `run.yaml`) -- callers deny rather than
    defaulting for either one, mirroring `swarm_start._resolve_run_context`'s
    own convention (trimmed here to the two fields `run.verify`/`run.bundle`
    actually need -- neither has a budget/timeout/governance-profile
    concept)."""

    sensitivity: str | None
    workspace_id: str | None


def _resolve_run_context(run_id: str, paths: FoundryPaths) -> _RunContext:
    """Swallows EVERY exception (`run.yaml` load/parse failure) and resolves
    both fields to `None` on failure -- mirrors `run_plan._resolve_intent_
    sensitivity`/`swarm_start._resolve_run_context`'s own fail-closed
    convention."""

    try:
        run_doc = load_yaml(paths.run_paths(run_id).run_yaml)
    except Exception as exc:
        _logger.warning(
            "operator_mcp_adapters.verify_bundle: run.yaml lookup failed (%s) for "
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
    `operator_mcp_policy._check_preflight`'s own one-line construction, fed
    to the SAME public `policy.build_error` every other denial in this
    family goes through. Mirrors `swarm_start._preflight_denial` exactly
    (not imported from there: that name is module-private to
    `swarm_start.py`, and this module does not touch `operator_mcp_policy.py`
    per the implementer contract's file-ownership boundary)."""

    return policy.PolicyDecision(False, "preflight", reason_code, retryable=True)


def _verify_prerequisites_met(
    run_id: str,
    paths: FoundryPaths,
    *,
    report_path: Path | None,
    claim_ledger_path: Path | None,
) -> bool:
    """Read-only, best-effort check that `verify_report` has real input to
    verify.

    `verify_report`'s own bare-invocation path (traced in
    `m1-remainder-unknowns.md`) never RAISES for a missing report or claim
    ledger -- it degrades every affected check to `fail` and returns a
    `VerificationResult(passed=False, exit_code=SCHEMA)`. But it ALSO calls
    `rp.ensure_scaffold()` unconditionally (creating run-directory
    subdirectories as a side effect) and unconditionally writes `reviews/
    verification.yaml` -- neither of which is a "zero effects" outcome for a
    run that has nothing meaningful to verify yet (e.g. one that has not
    reached `run.synthesize`). This function denies BEFORE `verify_report`
    is ever called in that case, per implementer contract D4 ("deny with
    reason codes rather than raising" for missing input).

    When the caller supplies an EXPLICIT `report_path`/`claim_ledger_path`,
    this function does not second-guess it (that path is skipped from the
    auto-discovery check below) -- `verify_report`'s own explicit-path
    resolution (`_resolve_explicit_path`) raises `RFError` for a genuinely
    missing explicit path, which is handled the normal way: an exception
    escaping `_run()` is caught by `operator_cancel_resume_service.
    run_actions`'s own action-failure handling and turned into a governed
    `"failed"` terminal outcome (U1's normal exception-based failure
    channel) -- a materially different situation (a caller-supplied bad
    path) than "this run has no report/ledger at all yet"."""

    try:
        rp = paths.run_paths(run_id)
        if not rp.run.exists():
            return False
        if report_path is None and not (rp.report_draft.exists() or rp.report_final.exists()):
            return False
        if claim_ledger_path is None and not rp.claim_ledger.exists():
            return False
    except Exception as exc:
        _logger.warning(
            "operator_mcp_adapters.verify_bundle: run.verify prerequisite check failed "
            "(%s) for run_id=%s -- denying (never a permissive default)",
            type(exc).__name__,
            run_id,
        )
        return False
    return True


def _bundle_prerequisites_met(run_id: str, paths: FoundryPaths) -> bool:
    """Read-only, best-effort check that a PASSING `reviews/
    verification.yaml` already exists for this run -- the prerequisite
    `run.bundle` enforces itself (implementer contract D5), since
    `writeback.build_bundle(verify=True)` never blocks on its own (U2).
    Absent file, unparsable content, or `passed` not `True` (including a
    missing `passed` key entirely) all deny -- never a permissive default.
    `verify_report`'s own persisted record shape (`verification.py`, the
    `record = {...}` block ending in `dump_yaml(record, rp.verification)`)
    always writes a boolean `passed` key, so this reads that field directly
    rather than re-deriving pass/fail from `checks`/`exit_code`."""

    try:
        rp = paths.run_paths(run_id)
        if not rp.run.exists():
            return False
        if not rp.verification.exists():
            return False
        record = load_yaml(rp.verification)
        if not isinstance(record, dict):
            return False
        return record.get("passed") is True
    except Exception as exc:
        _logger.warning(
            "operator_mcp_adapters.verify_bundle: run.bundle prerequisite check failed "
            "(%s) for run_id=%s -- denying (never a permissive default)",
            type(exc).__name__,
            run_id,
        )
        return False


def _exit_code_name(exit_code: int) -> str:
    """Bounded, human-readable label for a `VerificationResult.exit_code` --
    NOT a `operator_mcp_policy.CLOSED_REASON_CODES` member (that closed set
    has no verification-shaped codes, and this adapter's `ok=True`/
    `passed=False` result never goes through `policy.build_error` at all --
    see module docstring's D4 section), purely a convenience field inside
    the bounded result payload."""

    from research_foundry.errors import ExitCode

    try:
        return ExitCode(exit_code).name.lower()
    except ValueError:
        return "unknown"


# ---------------------------------------------------------------------------
# run.verify
# ---------------------------------------------------------------------------


def invoke_verify(
    *,
    run_id: str,
    idempotency_key: str,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    report_path: Path | None = None,
    claim_ledger_path: Path | None = None,
    fail_on_unsupported: bool = True,
    exact_passage_override: str | None = None,
    disposition: str = "internal_capture",
    evidence_judgment_bases: Sequence[str] | None = None,
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
    operations: OperatorOperationService | None = None,
    cancel_resume: OperatorCancelResumeService | None = None,
) -> base.OperatorAdapterResult:
    """The `run.verify` Operator MCP tool.

    Deliberately accepts NO `identity`/`workspace_id`/`AuthIdentity`-shaped
    parameter and NO `sensitivity_ceiling` parameter -- both resolved
    structurally, exactly like every other adapter in this family (see
    module docstring).

    A non-passing verification is a governed RESULT, not a denial: this
    function returns `ok=True` with `result["passed"] is False` when
    `verify_report` ran and produced a failing verdict (implementer
    contract D4) -- it denies (`ok=False`) ONLY for a prerequisite failure
    (no report/no claim ledger at all -- see `_verify_prerequisites_met`)
    or the standard H7 above-ceiling guard.
    """

    from research_foundry.services import verification

    from . import resolve_local_sensitivity_ceiling  # lazy: avoids circular import, see operator_mcp_adapters/__init__.py's own docstring

    resolved_paths = paths or FoundryPaths.discover()
    sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)
    run_ctx = _resolve_run_context(run_id, resolved_paths)

    # Prerequisite stage (implementer contract D4): missing report/claim
    # ledger denies BEFORE `ctx` is even constructed, with zero effects --
    # see `_verify_prerequisites_met`'s own docstring for why this cannot
    # simply be "let verify_report run and report a failing check" (it would
    # still write `reviews/verification.yaml` and create scaffold
    # directories for a run with nothing to verify).
    if not _verify_prerequisites_met(
        run_id, resolved_paths, report_path=report_path, claim_ledger_path=claim_ledger_path
    ):
        decision = _preflight_denial("preflight_failed")
        return base.OperatorAdapterResult(ok=False, error=policy.build_error(decision, now=now))

    effective_sensitivity = policy.resolve_effective_sensitivity(run_ctx.sensitivity)

    input_payload: dict[str, Any] = {
        "run_id": run_id,
        "fail_on_unsupported": fail_on_unsupported,
        "disposition": disposition,
    }
    if report_path is not None:
        input_payload["report_path"] = str(report_path)
    if claim_ledger_path is not None:
        input_payload["claim_ledger_path"] = str(claim_ledger_path)
    if exact_passage_override is not None:
        input_payload["exact_passage_override"] = exact_passage_override
    if evidence_judgment_bases is not None:
        input_payload["evidence_judgment_bases"] = list(evidence_judgment_bases)
    # None-valued optionals dropped above (except the always-present three)
    # so two callers who both omit the same optional collapse to the same
    # canonical digest -- mirrors `run_plan.py`'s own `input_payload`
    # construction rationale.

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=VERIFY_OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling=sensitivity_ceiling,
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload=input_payload,
        paths=resolved_paths,
    )

    # Captures verify_report's own VerificationResult so `_build_result` can
    # read the real governed verdict after `run_or_replay` executes this
    # action -- see module docstring's "replay result-recovery gap" note for
    # why this is sometimes empty even on a "completed" ExecutionOutcome.
    captured: list["verification.VerificationResult"] = []

    def _run() -> ActionEffect:
        # D4: ALWAYS returns normally, regardless of `.passed` -- a
        # non-passing verdict is a governed RESULT, not raised as a failure.
        result = verification.verify_report(
            run_id,
            report_path=report_path,
            claim_ledger_path=claim_ledger_path,
            fail_on_unsupported=fail_on_unsupported,
            exact_passage_override=exact_passage_override,
            paths=resolved_paths,
            disposition=disposition,
            evidence_judgment_bases=evidence_judgment_bases,
        )
        captured.append(result)
        # effect_digest must match `^[a-f0-9]{64}$` (operator_mcp_receipt
        # schema) -- effect_ref stays bounded (run_id alone, mirrors
        # run_plan.py's own `_effect_ref_for` rationale).
        effect_ref = f"{VERIFY_OPERATION_KIND}:{run_id}"
        digest_source = f"{effect_ref}:passed={result.passed}:exit_code={result.exit_code}"
        return ActionEffect(
            effect_kind="run_verified",
            effect_digest=hashlib.sha256(digest_source.encode("utf-8")).hexdigest(),
            effect_ref=effect_ref,
        )

    def _build_result(execution: ExecutionOutcome) -> Mapping[str, Any]:
        # base.run_pipeline only ever calls this for "completed"/"canceled"
        # -- "failed"/"denied" are already turned into a build_error
        # envelope before build_result is reached. D4: `passed=False` is
        # reported HERE, inside an `ok=True` envelope -- never mapped to a
        # denial.
        if execution.status == "completed" and captured:
            result = captured[0]
            return {
                "status": "completed",
                "run_id": result.run_id,
                "passed": result.passed,
                "exit_code": result.exit_code,
                "exit_code_name": _exit_code_name(result.exit_code),
                "unsupported": list(result.unsupported),
                "human_review_required": result.human_review_required,
                "verification_path": str(result.verification_path),
                "exact_passage_mode": result.exact_passage_mode,
                "exact_passage_violations": list(result.exact_passage_violations),
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
        "adapter": VERIFY_OPERATION_KIND,
        "run_id": run_id,
        "fail_on_unsupported": fail_on_unsupported,
    }

    return base.run_pipeline(
        ctx=ctx,
        confirmation_record=confirmation_record,
        presented_token=presented_token,
        action_manifest=action_manifest,
        actions=(ActionSpec(action_id="verify_report", run=_run),),
        build_result=_build_result,
        dry_run=dry_run,
        paths=resolved_paths,
        now=now,
        operations=operations,
        cancel_resume=cancel_resume,
    )


# ---------------------------------------------------------------------------
# run.bundle
# ---------------------------------------------------------------------------


def invoke_bundle(
    *,
    run_id: str,
    idempotency_key: str,
    confirmation_record: Mapping[str, Any] | None,
    presented_token: str | None,
    dry_run: bool = False,
    paths: FoundryPaths | None = None,
    now: datetime | None = None,
    operations: OperatorOperationService | None = None,
    cancel_resume: OperatorCancelResumeService | None = None,
) -> base.OperatorAdapterResult:
    """The `run.bundle` Operator MCP tool.

    Deliberately accepts NO `identity`/`workspace_id`/`AuthIdentity`-shaped
    parameter and NO `sensitivity_ceiling` parameter -- both resolved
    structurally, exactly like every other adapter in this family.

    Requires an existing, on-disk PASSING `run.verify` result for `run_id`
    (`_bundle_prerequisites_met`) -- absent or non-passing denies
    `preflight_failed` BEFORE `ctx` is constructed, `writeback.build_bundle`
    is NEVER called, zero effects. See module docstring's D5 section for the
    live-path re-check this function also performs, and the one known
    limitation (a losing race can still leave a draft `evidence_bundle.yaml`
    on disk) that this task does NOT close (out of file-ownership:
    `writeback.py`).
    """

    from research_foundry.services import writeback

    from . import resolve_local_sensitivity_ceiling  # lazy: avoids circular import, see operator_mcp_adapters/__init__.py's own docstring

    resolved_paths = paths or FoundryPaths.discover()
    sensitivity_ceiling = resolve_local_sensitivity_ceiling(resolved_paths)
    run_ctx = _resolve_run_context(run_id, resolved_paths)

    # Prerequisite stage (implementer contract D5, point 1): no passing
    # verification for this run denies BEFORE `ctx` is even constructed,
    # `build_bundle` is NEVER invoked, zero effects.
    if not _bundle_prerequisites_met(run_id, resolved_paths):
        decision = _preflight_denial("preflight_failed")
        return base.OperatorAdapterResult(ok=False, error=policy.build_error(decision, now=now))

    effective_sensitivity = policy.resolve_effective_sensitivity(run_ctx.sensitivity)

    input_payload: dict[str, Any] = {"run_id": run_id}

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=BUNDLE_OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling=sensitivity_ceiling,
        # `_REQUIRED_TARGET_KINDS["run.bundle"] == frozenset({"run",
        # "verification"})` -- TWO target kinds required by `_check_
        # preflight`'s generic "expected kinds present" gate. There is no
        # separate "verification id" in this codebase (VerificationResult
        # carries no id of its own, only `run_id` + a persisted
        # `reviews/verification.yaml`) -- `run_id` is reused as the
        # `target_ref` for the "verification" target too. Confirmed (M1 leg
        # C research pass) that no guard/RBAC logic anywhere keys on
        # `target_kind == "verification"` specifically or inspects its
        # `target_ref` value; `_check_identity_and_rbac` only walks
        # `resolved_target_workspaces` POSITIONALLY, so both entries must
        # supply the SAME owning workspace (the run's) -- see
        # `PolicyContext.__post_init__`'s own length-parity invariant.
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("verification", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload=input_payload,
        paths=resolved_paths,
    )

    # Captures build_bundle's own BundleResult so `_build_result` can read
    # the real canonical refs after `run_or_replay` executes this action --
    # empty on a genuine exact-replay of an already-terminal operation
    # (module docstring's "replay result-recovery gap").
    captured: list["writeback.BundleResult"] = []

    def _run() -> ActionEffect:
        result = writeback.build_bundle(run_id, verify=True, paths=resolved_paths)
        captured.append(result)
        if not result.verified:
            # D5, live-path re-check: verification state changed between
            # the prerequisite read above and this call actually running.
            # Raising here is what makes `run_or_replay` terminate this
            # operation "failed" (`ok=False`) instead of reporting a draft
            # bundle as a successful result -- see module docstring's
            # "known limitation" section: `build_bundle` has ALREADY
            # written a draft `evidence_bundle.yaml` by the time this
            # raises, so this operation is not perfectly zero-effect in
            # this one race window.
            raise RuntimeError(
                "run.bundle: build_bundle reported verified=False despite a passing "
                "prerequisite check -- verification state changed concurrently; "
                "terminating as failed rather than reporting a draft bundle as success"
            )
        effect_ref = f"{BUNDLE_OPERATION_KIND}:{run_id}"
        digest_source = f"{effect_ref}:bundle_id={result.bundle_id}:verified={result.verified}"
        return ActionEffect(
            effect_kind="run_bundled",
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
                "bundle_path": str(result.bundle_path),
                "counts": dict(result.counts),
                "verified": result.verified,
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

    action_manifest: dict[str, Any] = {"adapter": BUNDLE_OPERATION_KIND, "run_id": run_id}

    return base.run_pipeline(
        ctx=ctx,
        confirmation_record=confirmation_record,
        presented_token=presented_token,
        action_manifest=action_manifest,
        actions=(ActionSpec(action_id="build_bundle", run=_run),),
        build_result=_build_result,
        dry_run=dry_run,
        paths=resolved_paths,
        now=now,
        operations=operations,
        cancel_resume=cancel_resume,
    )


@dataclass(frozen=True)
class RunVerifyAdapter:
    """`base.OperatorAdapter` Protocol implementation for `run.verify`."""

    operation_kind: str = VERIFY_OPERATION_KIND

    def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:
        return invoke_verify(**kwargs)


@dataclass(frozen=True)
class RunBundleAdapter:
    """`base.OperatorAdapter` Protocol implementation for `run.bundle`."""

    operation_kind: str = BUNDLE_OPERATION_KIND

    def invoke(self, **kwargs: Any) -> base.OperatorAdapterResult:
        return invoke_bundle(**kwargs)


VERIFY_ADAPTER = RunVerifyAdapter()
BUNDLE_ADAPTER = RunBundleAdapter()
base.register(VERIFY_ADAPTER)
base.register(BUNDLE_ADAPTER)
