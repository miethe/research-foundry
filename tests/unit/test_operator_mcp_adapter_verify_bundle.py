"""Unit tests for the `run.verify` + `run.bundle` Operator MCP adapters
(research-foundry-operator-mcp-v1 M1 remainder, leg C).

Covers: the parity acceptance criterion (direct-service call vs. adapter
call produce equivalent canonical refs, via the spy pattern -- never a
double call), dry run's zero-effects guarantee, the fail-closed H7
sensitivity-ceiling guard, the D4 "non-passing verification is a governed
result" contract (`ok=True`, `result["passed"] is False`, never a denial),
the D5 "run.bundle blocks on a non-passing prerequisite, zero effects, the
action is never invoked" contract, and exact-retry idempotency.

Reuses, never reinvents: `tests/test_writebacks.py`'s pipeline-driving
helper shape (capture -> triage -> plan -> ingest -> extract -> claim_map
-> synthesize), `tests/unit/test_operator_mcp_adapter_run_plan.py`'s
`_default_sensitivity_ceiling`/`_recording_ceiling` fixtures, and
`tests/unit/test_operator_mcp_policy.py`'s identity fixtures.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from research_foundry import ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_adapters as adapters_pkg
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.services import verification as verification_module
from research_foundry.services import writeback as writeback_module
from research_foundry.services.capture import capture_idea, triage_idea
from research_foundry.services.claim_mapping import build_claim_ledger
from research_foundry.services.extraction import extract_run
from research_foundry.services.operator_mcp_adapters import verify_bundle
from research_foundry.services.operator_operation_service import OperatorOperationService
from research_foundry.services.planning import plan_run
from research_foundry.services.source_cards import ingest_source
from research_foundry.services.synthesis import synthesize_report
from research_foundry.yamlio import dump_yaml, load_yaml

from tests.unit.test_operator_mcp_adapter_run_plan import (  # noqa: F401
    _default_sensitivity_ceiling,
    _recording_ceiling,
)

_IDENTITY = AuthIdentity("alice", "ws-mine", ("owner",))
_IDENTITY_OTHER_WORKSPACE = AuthIdentity("bob", "ws-other", ("owner",))

_IDEA = (
    "Research how agentic research workflows should handle evidence bundles and "
    "claim traceability across cheap extraction and deep synthesis models. "
    "Studies show 40% of unsupported claims come from synthesis drift."
)

_SOURCE_TEXT = (
    "Evidence bundles let a research run carry its sources, claims, and a report "
    "in one auditable package. A 2025 study found that 40% of unsupported claims "
    "originate during synthesis when extraction and synthesis use different models. "
    "Claim ledgers reduce citation mismatch by mapping every material sentence to "
    "an evidence id. Limitations: small sample, single domain."
)


def _build_verified_run(
    paths: FoundryPaths, *, identity: AuthIdentity = _IDENTITY, sensitivity: str = "personal"
) -> str:
    """Drives the real deterministic pipeline through synthesis (capture ->
    triage -> plan -> ingest -> extract -> claim_map -> synthesize),
    stamping `run.yaml`'s `workspace_id` from `identity` (mirrors
    `test_operator_mcp_adapter_swarm_start.py`'s own `_planned_run` --
    `plan_run` only writes a real `workspace_id` when an `identity` is
    passed through it) so `_resolve_run_context`'s workspace resolution
    matches whatever `policy.resolve_operator_identity` resolves to for a
    given test. Returns a run_id with a real `report_draft.md` and a real
    `claim_ledger.yaml` on disk, but NO verification/bundle yet -- callers
    that need those call `verification.verify_report`/`writeback.
    build_bundle` themselves."""

    cap = capture_idea(_IDEA, sensitivity=sensitivity, paths=paths)
    tri = triage_idea(cap.raw_idea_id, paths=paths)
    assert tri.intent_id
    plan = plan_run(tri.intent_id, identity=identity, paths=paths)
    run_id = plan.run_id

    src_file = paths.root / f"input_source_{run_id}.txt"
    src_file.write_text(_SOURCE_TEXT, encoding="utf-8")
    ingest_source(
        str(src_file),
        run_id=run_id,
        source_type="paper",
        sensitivity=sensitivity,
        title="Evidence bundles and claim traceability",
        paths=paths,
    )

    extract_run(run_id, paths=paths)
    build_claim_ledger(run_id, intent_id=tri.intent_id, paths=paths)
    synthesize_report(run_id, paths=paths)
    return run_id


def _mint_and_record(
    ctx: policy.PolicyContext, op_service: OperatorOperationService
) -> tuple[Any, str]:
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)
    return issued.record, issued.token


def _bundle_ctx(run_id: str, idempotency_key: str, tmp_foundry: FoundryPaths) -> policy.PolicyContext:
    """Builds the exact `ctx` `invoke_bundle` would construct internally for
    `run_id` -- reused by every test that needs a REAL (non-dry-run)
    confirmation cycle for `run.bundle` (Fix cycle 1 / F6: the prerequisite
    check now runs post-authorization, so most `run.bundle` denial tests
    need a full confirm cycle rather than `dry_run=True`)."""

    run_ctx = verify_bundle._resolve_run_context(run_id, tmp_foundry)
    return policy.PolicyContext.for_configured_operator(
        operation_kind=verify_bundle.BUNDLE_OPERATION_KIND,
        idempotency_key=idempotency_key,
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("verification", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id},
        paths=tmp_foundry,
    )


# ---------------------------------------------------------------------------
# run.verify -- parity (spy, never double-call)
# ---------------------------------------------------------------------------


def test_invoke_verify_result_matches_direct_verify_report_call(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Spies on the ONE real `verification.verify_report` call `invoke_
    verify` makes and asserts the adapter's bounded result carries the
    SAME governed verdict fields the direct `VerificationResult` holds --
    `invoke_verify`'s `_build_result` is a lossless, non-mangling view, not
    an independently reconstructed one."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)

    captured_direct: list[Any] = []
    real_verify_report = verification_module.verify_report

    def _spy_verify_report(*args: Any, **kwargs: Any) -> Any:
        result = real_verify_report(*args, **kwargs)
        captured_direct.append(result)
        return result

    monkeypatch.setattr(verification_module, "verify_report", _spy_verify_report)

    run_ctx = verify_bundle._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=verify_bundle.VERIFY_OPERATION_KIND,
        idempotency_key="idem-verify-equivalence",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload={"run_id": run_id, "fail_on_unsupported": True, "disposition": "internal_capture"},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    result = verify_bundle.invoke_verify(
        run_id=run_id,
        idempotency_key="idem-verify-equivalence",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert len(captured_direct) == 1, "verify_report must be called exactly once"
    direct = captured_direct[0]

    assert result.result is not None
    assert result.result["run_id"] == direct.run_id
    assert result.result["passed"] == direct.passed
    assert result.result["exit_code"] == direct.exit_code
    assert result.result["unsupported"] == list(direct.unsupported)
    assert result.result["human_review_required"] == direct.human_review_required
    assert result.result["verification_path"] == str(direct.verification_path)
    assert result.result["canonical_refs_available"] is True


# ---------------------------------------------------------------------------
# run.verify -- D4: non-passing verification is a governed RESULT
# ---------------------------------------------------------------------------


def test_invoke_verify_non_passing_is_ok_true_with_passed_false(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The hard D4 contract: a run whose claim ledger contains an
    unsupported claim yields a REAL, non-passing `VerificationResult` --
    `invoke_verify` must return `ok=True` with `result["passed"] is False`,
    never `ok=False`, never raise."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)

    # Inject an unsupported claim into the real ledger the pipeline already
    # produced -- forces a real, non-passing verify_report outcome without
    # hand-rolling a report/ledger from scratch.
    rp = tmp_foundry.run_paths(run_id)
    ledger = load_yaml(rp.claim_ledger)
    ledger["claims"].append(
        {
            "claim_id": "clm_injected_unsupported",
            "text": "This claim has no supporting evidence at all.",
            "materiality": "material",
            "claim_type": "factual",
            "status": "unsupported",
            "confidence": "low",
            "sources": [],
        }
    )
    dump_yaml(ledger, rp.claim_ledger)

    run_ctx = verify_bundle._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=verify_bundle.VERIFY_OPERATION_KIND,
        idempotency_key="idem-verify-nonpassing",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload={"run_id": run_id, "fail_on_unsupported": True, "disposition": "internal_capture"},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    result = verify_bundle.invoke_verify(
        run_id=run_id,
        idempotency_key="idem-verify-nonpassing",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert result.result is not None
    assert result.result["passed"] is False
    assert any("clm_injected_unsupported" in entry for entry in result.result["unsupported"])


# ---------------------------------------------------------------------------
# run.verify -- prerequisite denial: missing report/claim ledger, zero effects
# ---------------------------------------------------------------------------


def test_invoke_verify_missing_report_denies_after_authorization_zero_effects(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run that has been planned but never reached `run.synthesize` (no
    report at all) denies -- `verify_report` is NEVER called (no `reviews/
    verification.yaml` is written), per D4. Uses a REAL (non-dry-run)
    confirmation cycle: since the F6 fix, this prerequisite check runs
    INSIDE `_run()`, which `dry_run=True` never reaches at all -- only a
    genuinely authorized, consumed operation exercises it (see module
    docstring's "Fix cycle 1" section)."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    cap = capture_idea(_IDEA, sensitivity="personal", paths=tmp_foundry)
    tri = triage_idea(cap.raw_idea_id, paths=tmp_foundry)
    plan = plan_run(tri.intent_id, identity=_IDENTITY, paths=tmp_foundry)
    run_id = plan.run_id

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("verify_report must never be called when prerequisites are unmet")

    monkeypatch.setattr(verification_module, "verify_report", _must_not_run)

    run_ctx = verify_bundle._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=verify_bundle.VERIFY_OPERATION_KIND,
        idempotency_key="idem-verify-missing-report",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload={"run_id": run_id, "fail_on_unsupported": True, "disposition": "internal_capture"},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    result = verify_bundle.invoke_verify(
        run_id=run_id,
        idempotency_key="idem-verify-missing-report",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is False
    assert result.result is None
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"
    # Unlike a pre-authorization denial, a real operation manifest IS
    # created here (authorization already succeeded before the prerequisite
    # check ran) -- this is expected and matches `run_plan.py`'s own
    # missing-intent precedent, not a regression.
    assert result.operation_id is not None
    assert not tmp_foundry.run_paths(run_id).verification.exists()


# ---------------------------------------------------------------------------
# run.verify -- F5 regression: explicit report_path/claim_ledger_path must
# not escape the authorized run's own directory tree
# ---------------------------------------------------------------------------


def test_invoke_verify_foreign_report_path_denies_and_does_not_touch_foreign_run(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F5 regression. Before the fix: an authorized caller for run A could
    supply an ABSOLUTE `report_path` pointing at run B's own report -- a
    DIFFERENT run, owned by a DIFFERENT workspace -- and `verify_report`
    would happily read it (its own explicit-path resolution accepts an
    absolute path as-is with no ownership check), verify it under A's
    identity, and write `verification_status` back into B's
    `claim_ledger.yaml`. This test FAILS pre-fix (foreign write succeeds,
    `ok=True`) and PASSES post-fix (`ok=False`, B's ledger untouched) --
    confirmed by running it against the pre-fix code cited in the pregate
    finding (see this task's completion note for the verified pre-fix
    failure transcript)."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_a = _build_verified_run(tmp_foundry, identity=_IDENTITY, sensitivity="personal")

    # Run B: a DIFFERENT run, owned by a DIFFERENT workspace/identity, with
    # its own real report + ledger.
    run_b = _build_verified_run(
        tmp_foundry, identity=_IDENTITY_OTHER_WORKSPACE, sensitivity="personal"
    )
    rp_b = tmp_foundry.run_paths(run_b)
    ledger_b_before = load_yaml(rp_b.claim_ledger)
    assert ledger_b_before.get("verification_status") != "failed"
    assert ledger_b_before.get("verification_status") != "passed"
    assert not rp_b.verification.exists()

    foreign_report_path = rp_b.report_draft if rp_b.report_draft.exists() else rp_b.report_final
    assert foreign_report_path.exists()

    run_ctx = verify_bundle._resolve_run_context(run_a, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=verify_bundle.VERIFY_OPERATION_KIND,
        idempotency_key="idem-verify-foreign-report-path",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_a),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload={
            "run_id": run_a,
            "fail_on_unsupported": True,
            "disposition": "internal_capture",
            "report_path": str(foreign_report_path),
        },
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    result = verify_bundle.invoke_verify(
        run_id=run_a,
        idempotency_key="idem-verify-foreign-report-path",
        confirmation_record=record,
        presented_token=token,
        report_path=foreign_report_path,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"
    # The hard assertion: B's own ledger/verification state must be
    # UNTOUCHED -- no cross-run/cross-workspace write occurred.
    assert not rp_b.verification.exists()
    ledger_b_after = load_yaml(rp_b.claim_ledger)
    assert ledger_b_after == ledger_b_before
    # A's own verification record was never written either -- verify_report
    # was never reached at all.
    assert not tmp_foundry.run_paths(run_a).verification.exists()


def test_invoke_verify_foreign_claim_ledger_path_denies_and_does_not_touch_foreign_run(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F5 regression, `claim_ledger_path` variant -- same vulnerability
    shape, the OTHER explicit-path sibling parameter the finding named."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_a = _build_verified_run(tmp_foundry, identity=_IDENTITY, sensitivity="personal")
    run_b = _build_verified_run(
        tmp_foundry, identity=_IDENTITY_OTHER_WORKSPACE, sensitivity="personal"
    )
    rp_b = tmp_foundry.run_paths(run_b)
    ledger_b_before = load_yaml(rp_b.claim_ledger)
    assert not rp_b.verification.exists()

    run_ctx = verify_bundle._resolve_run_context(run_a, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=verify_bundle.VERIFY_OPERATION_KIND,
        idempotency_key="idem-verify-foreign-ledger-path",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_a),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload={
            "run_id": run_a,
            "fail_on_unsupported": True,
            "disposition": "internal_capture",
            "claim_ledger_path": str(rp_b.claim_ledger),
        },
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    result = verify_bundle.invoke_verify(
        run_id=run_a,
        idempotency_key="idem-verify-foreign-ledger-path",
        confirmation_record=record,
        presented_token=token,
        claim_ledger_path=rp_b.claim_ledger,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"
    assert not rp_b.verification.exists()
    assert load_yaml(rp_b.claim_ledger) == ledger_b_before
    assert not tmp_foundry.run_paths(run_a).verification.exists()


def test_explicit_path_within_run_rejects_traversal_and_absolute_foreign_paths(
    tmp_foundry: FoundryPaths,
) -> None:
    """Direct unit test of the F5 guard itself: relative traversal
    (`../other/...`) and an absolute foreign path are both rejected; a path
    genuinely inside the run's own tree is accepted."""

    run_root = tmp_foundry.run_paths("rf_run_probe").run
    run_root.mkdir(parents=True, exist_ok=True)

    assert verify_bundle._explicit_path_within_run(run_root, run_root / "reviews" / "verification.yaml")
    assert not verify_bundle._explicit_path_within_run(
        run_root, Path("../other_run/reviews/verification.yaml")
    )
    assert not verify_bundle._explicit_path_within_run(
        run_root, tmp_foundry.run_paths("rf_run_other").run / "reports" / "report_draft.md"
    )


# ---------------------------------------------------------------------------
# run.verify -- dry run: zero effects
# ---------------------------------------------------------------------------


def test_invoke_verify_dry_run_never_calls_verify_report(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("dry run must never call verification.verify_report")

    monkeypatch.setattr(verification_module, "verify_report", _must_not_run)

    result = verify_bundle.invoke_verify(
        run_id=run_id,
        idempotency_key="idem-verify-dry",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is True
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "run.verify"}


# ---------------------------------------------------------------------------
# run.verify -- H7 defect fix: above-ceiling denies at guard stage, SAME
# shape as a wrong-workspace denial for the same real, prerequisite-
# satisfied run (see module docstring's "H7 negative-fixture adaptation").
# ---------------------------------------------------------------------------


def test_invoke_verify_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_run(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fix cycle 1 (F6): now that the prerequisite check no longer runs
    before `ctx`, a genuinely missing `run_id` denies through the SAME
    normal path (RBAC `not_found`, since its `resolved_target_workspaces`
    entry is `None` and never matches the caller's identity) that a real,
    too-sensitive run denies through (guard `not_found`) -- both reachable
    under `dry_run=True`, both reaching `ctx` before either prerequisite
    check would ever run. This is the literal `run_plan.py`/`swarm_start.py`
    H7 exemplar comparison, restored now that F6 no longer forces a
    wrong-workspace substitute (see module docstring's "Fix cycle 1" and
    "H7 negative fixture" sections)."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry, sensitivity="personal")

    run_ctx = verify_bundle._resolve_run_context(run_id, tmp_foundry)
    assert run_ctx.sensitivity == "personal"

    ceiling_double, ceiling_calls = _recording_ceiling("public")
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    direct_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=verify_bundle.VERIFY_OPERATION_KIND,
        idempotency_key="idem-verify-above-ceiling",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="public",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload={"run_id": run_id},
        paths=tmp_foundry,
    )
    direct_decision = policy.evaluate_policy(direct_ctx, paths=tmp_foundry)
    assert direct_decision.allowed is False
    assert direct_decision.stage == "guard"
    assert direct_decision.reason_code == "not_found"
    assert direct_decision.retryable is False

    above_ceiling_result = verify_bundle.invoke_verify(
        run_id=run_id,
        idempotency_key="idem-verify-above-ceiling",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    assert above_ceiling_result.ok is False
    assert above_ceiling_result.error is not None
    assert above_ceiling_result.error["reason_code"] == "not_found"
    assert above_ceiling_result.error["retryable"] is False
    assert "detail" not in above_ceiling_result.error

    # A genuinely missing run_id -- F6 fix: the prerequisite check (which
    # would previously deny this with a DIFFERENT, DISTINGUISHABLE reason,
    # `preflight_failed`, before `ctx` even existed) no longer runs at all
    # under dry_run -- this now denies at the EARLIER rbac stage (`ctx.
    # resolved_target_workspaces` is `(None,)`, which never matches any
    # caller identity), yet produces the byte-identical envelope.
    missing_run_result = verify_bundle.invoke_verify(
        run_id="does-not-exist-at-all-either",
        idempotency_key="idem-verify-above-ceiling-missing",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    assert missing_run_result.ok is False
    assert missing_run_result.error is not None
    assert missing_run_result.error["reason_code"] == "not_found"
    assert above_ceiling_result.error == missing_run_result.error

    assert ceiling_calls == [tmp_foundry, tmp_foundry]


# ---------------------------------------------------------------------------
# run.verify -- F6 regression: prerequisite state must not leak before
# authorization
# ---------------------------------------------------------------------------


def test_invoke_verify_foreign_run_state_does_not_leak_before_authorization_f6(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F6 regression. Before the fix, `_verify_prerequisites_met` ran BEFORE
    `ctx`/authorization: an unauthorized caller (`_IDENTITY`, workspace
    `ws-mine`) probing a FOREIGN run (owned by `ws-other`) that HAS the
    required report+ledger would fall through the pre-ctx check and deny
    later, at the rbac stage (`not_found`) -- while the SAME caller probing
    a nonexistent/incomplete run would be denied IMMEDIATELY by the pre-ctx
    check itself, with a DIFFERENT reason code (`preflight_failed`),
    *before* authorization ever ran. The two reason codes let an
    unauthorized caller learn whether a run they do not own has reached the
    report+ledger stage. This test FAILS pre-fix (the two results differ)
    and PASSES post-fix (both deny identically, at the rbac stage, since
    the prerequisite check no longer runs for an unauthorized caller at
    all -- see module docstring's "Fix cycle 1" section)."""

    # A run owned by a DIFFERENT workspace, with a REAL report + ledger on
    # disk -- exactly the state an unauthorized caller should not be able
    # to distinguish from "does not exist".
    run_foreign_with_artifacts = _build_verified_run(
        tmp_foundry, identity=_IDENTITY_OTHER_WORKSPACE, sensitivity="personal"
    )

    # Caller authorized ONLY for `ws-mine` -- has no claim on either target
    # below.
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    result_foreign_with_artifacts = verify_bundle.invoke_verify(
        run_id=run_foreign_with_artifacts,
        idempotency_key="idem-f6-verify-foreign-with-artifacts",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    result_nonexistent = verify_bundle.invoke_verify(
        run_id="does-not-exist-f6-verify-probe",
        idempotency_key="idem-f6-verify-nonexistent",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result_foreign_with_artifacts.ok is False
    assert result_nonexistent.ok is False
    assert result_foreign_with_artifacts.error is not None
    assert result_nonexistent.error is not None
    assert result_foreign_with_artifacts.error["reason_code"] == "not_found"
    assert result_foreign_with_artifacts.error == result_nonexistent.error


# ---------------------------------------------------------------------------
# run.verify -- exact retry idempotency (D7)
# ---------------------------------------------------------------------------


def test_invoke_verify_exact_retry_does_not_recall_verify_report(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Presenting the SAME confirmation/token/idempotency_key a second time
    is an exact replay -- `verify_report` (and therefore its write to
    `reviews/verification.yaml`) must not be invoked a second time, and the
    second call must resolve to the SAME operation_id."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)

    call_count = 0
    real_verify_report = verification_module.verify_report

    def _counting_verify_report(*args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        return real_verify_report(*args, **kwargs)

    monkeypatch.setattr(verification_module, "verify_report", _counting_verify_report)

    run_ctx = verify_bundle._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=verify_bundle.VERIFY_OPERATION_KIND,
        idempotency_key="idem-verify-retry",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("run", run_id),),
        resolved_target_workspaces=(run_ctx.workspace_id,),
        input_payload={"run_id": run_id, "fail_on_unsupported": True, "disposition": "internal_capture"},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    first = verify_bundle.invoke_verify(
        run_id=run_id,
        idempotency_key="idem-verify-retry",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )
    second = verify_bundle.invoke_verify(
        run_id=run_id,
        idempotency_key="idem-verify-retry",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert first.ok is True, first.error
    assert second.ok is True, second.error
    assert first.operation_id == second.operation_id
    assert call_count == 1, "verify_report must be called exactly once across both invocations"


# ---------------------------------------------------------------------------
# run.bundle -- D5: prerequisite blocks, action never invoked, zero effects
# ---------------------------------------------------------------------------


def test_invoke_bundle_denies_when_no_passing_verification_zero_effects(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run with a report+ledger but NO prior `run.verify` at all denies --
    `writeback.build_bundle` is NEVER called, so `evidence_bundle.yaml` is
    never written (the hard D5 AC: "unsupported verification blocks
    dependent bundle action"). Uses a REAL (non-dry-run) confirmation
    cycle: since the F6 fix, this prerequisite check runs INSIDE `_run()`,
    which `dry_run=True` never reaches at all (see module docstring's "Fix
    cycle 1" section)."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)
    assert not tmp_foundry.run_paths(run_id).verification.exists()

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("build_bundle must never be called when prerequisites are unmet")

    monkeypatch.setattr(writeback_module, "build_bundle", _must_not_run)

    ctx = _bundle_ctx(run_id, "idem-bundle-no-verify", tmp_foundry)
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    result = verify_bundle.invoke_bundle(
        run_id=run_id,
        idempotency_key="idem-bundle-no-verify",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is False
    assert result.result is None
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"
    assert not tmp_foundry.run_paths(run_id).evidence_bundle.exists()


def test_invoke_bundle_denies_when_prior_verification_failed_zero_effects(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A run WITH a `reviews/verification.yaml` on disk, but whose `passed`
    field is `False`, also denies -- non-passing is treated the same as
    absent, never a permissive default. Uses a REAL (non-dry-run)
    confirmation cycle for the same reason as the sibling test above."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)
    verification_module.verify_report(run_id, fail_on_unsupported=False, paths=tmp_foundry)
    # Force a non-passing record without touching the real ledger content --
    # directly asserts the D5 "non-passing (not merely absent) also denies"
    # branch of `_bundle_prerequisites_met`.
    rp = tmp_foundry.run_paths(run_id)
    record_yaml = load_yaml(rp.verification)
    record_yaml["passed"] = False
    dump_yaml(record_yaml, rp.verification)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("build_bundle must never be called for a non-passing prerequisite")

    monkeypatch.setattr(writeback_module, "build_bundle", _must_not_run)

    ctx = _bundle_ctx(run_id, "idem-bundle-failed-verify", tmp_foundry)
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    result = verify_bundle.invoke_bundle(
        run_id=run_id,
        idempotency_key="idem-bundle-failed-verify",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is False
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"
    assert not rp.evidence_bundle.exists()


# ---------------------------------------------------------------------------
# run.bundle -- parity (spy, never double-call)
# ---------------------------------------------------------------------------


def test_invoke_bundle_result_matches_direct_build_bundle_call(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)
    verification_module.verify_report(run_id, fail_on_unsupported=False, paths=tmp_foundry)
    assert load_yaml(tmp_foundry.run_paths(run_id).verification)["passed"] is True

    captured_direct: list[Any] = []
    real_build_bundle = writeback_module.build_bundle

    def _spy_build_bundle(*args: Any, **kwargs: Any) -> Any:
        result = real_build_bundle(*args, **kwargs)
        captured_direct.append(result)
        return result

    monkeypatch.setattr(writeback_module, "build_bundle", _spy_build_bundle)

    run_ctx = verify_bundle._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=verify_bundle.BUNDLE_OPERATION_KIND,
        idempotency_key="idem-bundle-equivalence",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("verification", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    result = verify_bundle.invoke_bundle(
        run_id=run_id,
        idempotency_key="idem-bundle-equivalence",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert len(captured_direct) == 1, "build_bundle must be called exactly once"
    direct = captured_direct[0]

    assert result.result is not None
    assert result.result["run_id"] == direct.run_id
    assert result.result["bundle_id"] == direct.bundle_id
    assert result.result["bundle_path"] == str(direct.bundle_path)
    assert result.result["counts"] == dict(direct.counts)
    assert result.result["verified"] == direct.verified is True
    assert result.result["canonical_refs_available"] is True


# ---------------------------------------------------------------------------
# run.bundle -- dry run: zero effects
# ---------------------------------------------------------------------------


def test_invoke_bundle_dry_run_never_calls_build_bundle(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)
    verification_module.verify_report(run_id, fail_on_unsupported=False, paths=tmp_foundry)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("dry run must never call writeback.build_bundle")

    monkeypatch.setattr(writeback_module, "build_bundle", _must_not_run)

    result = verify_bundle.invoke_bundle(
        run_id=run_id,
        idempotency_key="idem-bundle-dry",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is True
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "run.bundle"}


# ---------------------------------------------------------------------------
# run.bundle -- H7 defect fix: above-ceiling denies at guard stage, SAME
# shape as a wrong-workspace denial for the same real, prerequisite-
# satisfied run (see module docstring's "H7 negative-fixture adaptation").
# ---------------------------------------------------------------------------


def test_invoke_bundle_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_run(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fix cycle 1 (F6): restored to the literal exemplar comparison, same
    rationale as `run.verify`'s own sibling test above."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry, sensitivity="personal")
    verification_module.verify_report(run_id, fail_on_unsupported=False, paths=tmp_foundry)
    assert load_yaml(tmp_foundry.run_paths(run_id).verification)["passed"] is True

    run_ctx = verify_bundle._resolve_run_context(run_id, tmp_foundry)
    assert run_ctx.sensitivity == "personal"

    ceiling_double, ceiling_calls = _recording_ceiling("public")
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

    direct_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=verify_bundle.BUNDLE_OPERATION_KIND,
        idempotency_key="idem-bundle-above-ceiling",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="public",
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("verification", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id},
        paths=tmp_foundry,
    )
    direct_decision = policy.evaluate_policy(direct_ctx, paths=tmp_foundry)
    assert direct_decision.allowed is False
    assert direct_decision.stage == "guard"
    assert direct_decision.reason_code == "not_found"

    above_ceiling_result = verify_bundle.invoke_bundle(
        run_id=run_id,
        idempotency_key="idem-bundle-above-ceiling",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    assert above_ceiling_result.ok is False
    assert above_ceiling_result.error is not None
    assert above_ceiling_result.error["reason_code"] == "not_found"
    assert "detail" not in above_ceiling_result.error

    missing_run_result = verify_bundle.invoke_bundle(
        run_id="does-not-exist-at-all-either",
        idempotency_key="idem-bundle-above-ceiling-missing",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    assert missing_run_result.ok is False
    assert missing_run_result.error is not None
    assert missing_run_result.error["reason_code"] == "not_found"
    assert above_ceiling_result.error == missing_run_result.error

    assert ceiling_calls == [tmp_foundry, tmp_foundry]


# ---------------------------------------------------------------------------
# run.bundle -- F6 regression: prerequisite state must not leak before
# authorization
# ---------------------------------------------------------------------------


def test_invoke_bundle_foreign_run_state_does_not_leak_before_authorization_f6(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F6 regression, `run.bundle` variant. Before the fix, an unauthorized
    caller could distinguish a foreign run WITH a passing verification
    (falls through the pre-ctx check, denies later at rbac `not_found`)
    from one WITHOUT (denied immediately, `preflight_failed`, before
    authorization). Same fail-pre-fix/pass-post-fix shape as the `run.
    verify` sibling test above."""

    run_foreign_verified = _build_verified_run(
        tmp_foundry, identity=_IDENTITY_OTHER_WORKSPACE, sensitivity="personal"
    )
    verification_module.verify_report(
        run_foreign_verified, fail_on_unsupported=False, paths=tmp_foundry
    )
    assert load_yaml(tmp_foundry.run_paths(run_foreign_verified).verification)["passed"] is True

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)

    result_foreign_verified = verify_bundle.invoke_bundle(
        run_id=run_foreign_verified,
        idempotency_key="idem-f6-bundle-foreign-verified",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    result_nonexistent = verify_bundle.invoke_bundle(
        run_id="does-not-exist-f6-bundle-probe",
        idempotency_key="idem-f6-bundle-nonexistent",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result_foreign_verified.ok is False
    assert result_nonexistent.ok is False
    assert result_foreign_verified.error is not None
    assert result_nonexistent.error is not None
    assert result_foreign_verified.error["reason_code"] == "not_found"
    assert result_foreign_verified.error == result_nonexistent.error


# ---------------------------------------------------------------------------
# run.bundle -- live-path re-check: build_bundle's own verified=False
# terminates the operation as failed, never a fabricated success
# ---------------------------------------------------------------------------


def test_invoke_bundle_raises_when_build_bundle_reports_unverified_despite_passing_prerequisite(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulates the D5 race: the prerequisite check passes (a real,
    on-disk `passed: True` record exists), but `writeback.build_bundle`
    itself -- monkeypatched here to a stub returning `verified=False`,
    standing in for a concurrent invalidation between the two reads --
    reports `verified=False`. `invoke_bundle` must terminate the operation
    `ok=False` rather than report the draft bundle as a success."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)
    verification_module.verify_report(run_id, fail_on_unsupported=False, paths=tmp_foundry)
    assert load_yaml(tmp_foundry.run_paths(run_id).verification)["passed"] is True

    from research_foundry.services.writeback import BundleResult

    rp = tmp_foundry.run_paths(run_id)

    def _stub_build_bundle(run_id_arg: str, *, verify: bool = True, paths: Any = None) -> BundleResult:
        return BundleResult(
            run_id=run_id_arg,
            bundle_id="bundle_stub",
            bundle_path=rp.evidence_bundle,
            counts={},
            verified=False,
        )

    monkeypatch.setattr(writeback_module, "build_bundle", _stub_build_bundle)

    result = verify_bundle.invoke_bundle(
        run_id=run_id,
        idempotency_key="idem-bundle-race",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    # dry_run=True never reaches the action at all -- this only proves the
    # prerequisite still passes for a genuinely-passing run. The live-path
    # raise is proven directly below, against the real substrate action
    # closure machinery via a full non-dry-run confirmation cycle.
    assert result.ok is True

    run_ctx = verify_bundle._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=verify_bundle.BUNDLE_OPERATION_KIND,
        idempotency_key="idem-bundle-race-live",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("verification", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    live_result = verify_bundle.invoke_bundle(
        run_id=run_id,
        idempotency_key="idem-bundle-race-live",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert live_result.ok is False
    assert live_result.error is not None
    assert live_result.error["reason_code"] == "internal_error"


# ---------------------------------------------------------------------------
# run.bundle -- exact retry idempotency (D7)
# ---------------------------------------------------------------------------


def test_invoke_bundle_exact_retry_does_not_recall_build_bundle(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    run_id = _build_verified_run(tmp_foundry)
    verification_module.verify_report(run_id, fail_on_unsupported=False, paths=tmp_foundry)

    call_count = 0
    real_build_bundle = writeback_module.build_bundle

    def _counting_build_bundle(*args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        return real_build_bundle(*args, **kwargs)

    monkeypatch.setattr(writeback_module, "build_bundle", _counting_build_bundle)

    run_ctx = verify_bundle._resolve_run_context(run_id, tmp_foundry)
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=verify_bundle.BUNDLE_OPERATION_KIND,
        idempotency_key="idem-bundle-retry",
        effective_sensitivity=policy.resolve_effective_sensitivity(run_ctx.sensitivity),
        sensitivity_ceiling="client_sensitive",
        targets=(
            policy.TargetRef("run", run_id),
            policy.TargetRef("verification", run_id),
        ),
        resolved_target_workspaces=(run_ctx.workspace_id, run_ctx.workspace_id),
        input_payload={"run_id": run_id},
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    record, token = _mint_and_record(ctx, op_service)

    first = verify_bundle.invoke_bundle(
        run_id=run_id,
        idempotency_key="idem-bundle-retry",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )
    second = verify_bundle.invoke_bundle(
        run_id=run_id,
        idempotency_key="idem-bundle-retry",
        confirmation_record=record,
        presented_token=token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert first.ok is True, first.error
    assert second.ok is True, second.error
    assert first.operation_id == second.operation_id
    assert call_count == 1, "build_bundle must be called exactly once across both invocations"
