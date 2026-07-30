"""Unit tests for the `run.plan` Operator MCP adapter (research-foundry-
operator-mcp-v1 P3, OPM-3.1).

Covers: the acceptance criterion ("a direct-service call and the MCP-adapter
call produce equivalent canonical refs"), dry run's zero-effects guarantee,
and the fail-closed sensitivity-resolution guard for a missing/unreadable
intent.

Reuses, never reinvents: `tests/test_planning.py`'s `_make_intent` helper
(capture + triage a real intent via the SAME service calls `plan_run` itself
is exercised against elsewhere in this suite) and
`tests/unit/test_operator_mcp_policy.py`'s identity fixtures.
"""

from __future__ import annotations

from typing import Any

import pytest

from research_foundry import ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_adapters as adapters_pkg
from research_foundry.services import operator_mcp_policy as policy
import research_foundry.services.planning as planning_module
from research_foundry.services.operator_mcp_adapters import run_plan
from research_foundry.services.operator_operation_service import OperatorOperationService

from tests.test_planning import _make_intent
from tests.unit.test_operator_mcp_policy import _default_operator_identity  # noqa: F401

# ---------------------------------------------------------------------------
# H7 defect fix (this task): every P3 adapter now resolves
# `sensitivity_ceiling` structurally via `operator_mcp_adapters.
# resolve_local_sensitivity_ceiling` instead of accepting it as a caller-
# supplied parameter (see that function's own docstring in
# `operator_mcp_adapters/__init__.py` for the full defect). Patch that ONE
# seam to the loosest label by default, autouse, so every PRE-EXISTING test
# in this module (none of which is testing the ceiling gate itself) keeps
# exercising its own intended behavior without each writing a
# `foundry.yaml` `operator_mcp.sensitivity_ceiling` block -- exactly the
# same convention `test_operator_mcp_policy._default_operator_identity`
# (imported above) already establishes for identity resolution. The
# negative fixture below (`test_invoke_denies_above_ceiling_...`) re-patches
# this to a LOWER ceiling to prove the H7 guard actually fires when it is
# not overridden this way.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _default_sensitivity_ceiling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        adapters_pkg, "resolve_local_sensitivity_ceiling", lambda *a, **kw: "client_sensitive"
    )


# Captured at import time, BEFORE `_default_sensitivity_ceiling` above ever
# runs -- mirrors `test_operator_mcp_policy.py`'s own
# `_REAL_RESOLVE_OPERATOR_IDENTITY` convention -- lets the direct unit tests
# below exercise the REAL `resolve_local_sensitivity_ceiling` implementation,
# independent of whatever it is monkeypatched to for every other test in
# this module.
_REAL_RESOLVE_LOCAL_SENSITIVITY_CEILING = adapters_pkg.resolve_local_sensitivity_ceiling


# ---------------------------------------------------------------------------
# `operator_mcp_adapters.resolve_local_sensitivity_ceiling` direct unit
# tests (H7 defect fix) -- the producer this task's fix relies on. Every
# adapter's own above-ceiling test elsewhere in this file/suite monkeypatches
# this function directly and therefore never exercises ITS OWN fail-closed
# default; these tests close that gap.
# ---------------------------------------------------------------------------


def test_resolve_local_sensitivity_ceiling_returns_public_when_unconfigured(
    tmp_foundry: FoundryPaths,
) -> None:
    assert _REAL_RESOLVE_LOCAL_SENSITIVITY_CEILING(tmp_foundry) == "public"


def test_resolve_local_sensitivity_ceiling_returns_configured_value_when_valid(
    tmp_foundry: FoundryPaths,
) -> None:
    from research_foundry.yamlio import dump_yaml, load_yaml

    data: dict[str, Any] = load_yaml(tmp_foundry.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"]["operator_mcp"] = {"sensitivity_ceiling": "personal"}
    dump_yaml(data, tmp_foundry.foundry_yaml)

    assert _REAL_RESOLVE_LOCAL_SENSITIVITY_CEILING(tmp_foundry) == "personal"


def test_resolve_local_sensitivity_ceiling_unknown_label_fails_closed(
    tmp_foundry: FoundryPaths,
) -> None:
    """MUTATION-TESTED GUARD (see this task's report): an unrecognized
    ceiling label in `foundry.yaml` (typo, stale value, anything outside
    `operator_mcp_policy.SENSITIVITY_LEVELS`) must NOT pass through to
    `PolicyContext.for_configured_operator` (which would raise `ValueError`
    -- an uncaught raw exception crossing an adapter's public boundary) and
    must NOT silently grant the loosest clearance either -- it resolves to
    `"public"`, the single most-restrictive ceiling."""

    from research_foundry.yamlio import dump_yaml, load_yaml

    data: dict[str, Any] = load_yaml(tmp_foundry.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"]["operator_mcp"] = {"sensitivity_ceiling": "not_a_real_sensitivity_level"}
    dump_yaml(data, tmp_foundry.foundry_yaml)

    assert _REAL_RESOLVE_LOCAL_SENSITIVITY_CEILING(tmp_foundry) == "public"


def test_resolve_local_sensitivity_ceiling_fails_closed_on_malformed_config(
    tmp_path: Any,
) -> None:
    """Mirrors `test_operator_mcp_policy.py`'s own `test_resolve_operator_
    identity_fails_closed_on_malformed_config`: a malformed `foundry.yaml`
    must not propagate a raw parser exception out of this function -- it is
    public, `run_plan.py`/`swarm_start.py`/`job_lifecycle.py` all call it
    directly inside their own `invoke*` bodies with no surrounding
    try/except of their own (`job_lifecycle.invoke_cancel`/`invoke_resume`
    call it BEFORE their own try block even opens), so an uncaught raise
    here would cross an adapter's public boundary raw."""

    from research_foundry.paths import FoundryPaths as _FoundryPaths

    root = tmp_path / "fdry"
    root.mkdir()
    (root / "foundry.yaml").write_text(
        "foundry:\n  operator_mcp:\n   sensitivity_ceiling: [unclosed\n"
    )
    paths = _FoundryPaths(root=root)

    assert _REAL_RESOLVE_LOCAL_SENSITIVITY_CEILING(paths) == "public"

# ---------------------------------------------------------------------------
# Acceptance criterion: direct-service call vs MCP-adapter call produce
# equivalent canonical refs
# ---------------------------------------------------------------------------


def test_invoke_result_matches_direct_plan_run_call(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P3 implementer contract acceptance criterion, proven precisely:

    `planning.plan_run` is NOT idempotent -- two separate calls for the same
    intent mint two DIFFERENT `run_id`s via `disambiguate_id`, so comparing
    two independent invocations (one direct, one through the adapter) would
    not be a meaningful "equivalence" check; a genuine difference there
    would be expected behavior, not a defect. Instead, this test spies on
    the ONE REAL `planning.plan_run` call `run_plan.invoke()` makes
    (`monkeypatch` on the shared module object, not a second live call) and
    asserts the adapter's bounded result dict carries EXACTLY the same four
    canonical ids and four canonical paths the direct `PlanResult` holds --
    i.e. `run_plan._plan_result_to_dict` is a lossless, non-mangling view of
    the real service call's own output, not an independently reconstructed
    (and therefore possibly divergent) one.
    """

    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)

    identity = AuthIdentity("alice", "ws-mine", ("owner",))
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    captured_direct: list[Any] = []
    real_plan_run = planning_module.plan_run

    def _spy_plan_run(*args: Any, **kwargs: Any) -> Any:
        result = real_plan_run(*args, **kwargs)
        captured_direct.append(result)
        return result

    monkeypatch.setattr(planning_module, "plan_run", _spy_plan_run)

    # Build a PolicyContext with the EXACT SAME canonical fields
    # `run_plan.invoke()` will independently construct for this call (same
    # idempotency_key, same intent-derived effective_sensitivity, same
    # default depth/audience/budget args) so the confirmation minted
    # against it binds to the SAME canonical digest `invoke()` recomputes
    # internally -- mirrors how a real P5 caller would use
    # `operation.preflight` (mint) then present the token to the execute
    # tool, just without a transport in between yet.
    effective_sensitivity = policy.resolve_effective_sensitivity(
        run_plan._resolve_intent_sensitivity(intent_id, tmp_foundry)
    )
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=run_plan.OPERATION_KIND,
        idempotency_key="idem-equivalence",
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling="client_sensitive",
        input_payload={
            "intent_id": intent_id,
            "depth": "standard",
            "audience": "technical",
            "max_cost_usd": 5.0,
            "max_runtime_minutes": 60,
            "freshness_days": 180,
        },
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = run_plan.invoke(
        intent_id=intent_id,
        idempotency_key="idem-equivalence",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert len(captured_direct) == 1, "plan_run must be called exactly once"
    direct = captured_direct[0]

    assert result.result is not None
    assert result.result["run_id"] == direct.run_id
    assert result.result["brief_id"] == direct.brief_id
    assert result.result["swarm_id"] == direct.swarm_id
    assert result.result["routing_id"] == direct.routing_id
    assert result.result["run_dir"] == str(direct.run_dir)
    assert result.result["brief_path"] == str(direct.brief_path)
    assert result.result["swarm_path"] == str(direct.swarm_path)
    assert result.result["routing_path"] == str(direct.routing_path)
    assert result.result["evidence_plan_ref"] == direct.evidence_plan_ref
    assert result.result["canonical_refs_available"] is True


# ---------------------------------------------------------------------------
# Dry run: zero effects (requirement 4, proven at the adapter's own surface)
# ---------------------------------------------------------------------------


def test_invoke_dry_run_never_calls_plan_run(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)
    identity = AuthIdentity("alice", "ws-mine", ("owner",))
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("dry run must never call planning.plan_run")

    monkeypatch.setattr(planning_module, "plan_run", _must_not_run)

    result = run_plan.invoke(
        intent_id=intent_id,
        idempotency_key="idem-dry",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert result.ok is True
    assert result.operation_id is None
    assert result.result == {"dry_run": True, "operation_kind": "run.plan"}


# ---------------------------------------------------------------------------
# Fail-closed sensitivity resolution for a missing/unreadable intent
# ---------------------------------------------------------------------------


def test_resolve_intent_sensitivity_swallows_lookup_failure(tmp_foundry: FoundryPaths) -> None:
    """MUTATION-TESTED GUARD (see this task's report): `_resolve_intent_
    sensitivity` swallows a failed `planning.load_intent` lookup (missing
    intent, malformed YAML, anything else) and returns `None` -- NEVER lets
    the exception propagate, and NEVER guesses a permissive value. `None`
    then resolves to the STRICTEST sensitivity via
    `policy.resolve_effective_sensitivity` (P1's own fail-closed
    convention, not re-tested here)."""

    result = run_plan._resolve_intent_sensitivity("does-not-exist-at-all", tmp_foundry)
    assert result is None


def test_missing_intent_denies_through_the_normal_execution_path_not_a_special_branch(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A caller-supplied `intent_id` that does not exist is NOT special-
    cased before authorization (module docstring's documented judgment
    call) -- it is denied only once the confirmed operation's own action
    actually tries to load it, via the NORMAL `run_or_replay` action-failure
    path (`ExecutionOutcome.status == "failed"` -> `base.run_pipeline`'s
    `ok=False` mapping), proven here end-to-end with a real (non-spied)
    `planning.load_intent`/`plan_run` call."""

    identity = AuthIdentity("alice", "ws-mine", ("owner",))
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=run_plan.OPERATION_KIND,
        idempotency_key="idem-missing-intent",
        effective_sensitivity=policy.SENSITIVITY_LEVELS[-1],  # fail-closed strictest, per the guard
        sensitivity_ceiling="client_sensitive",
        input_payload={
            "intent_id": "does-not-exist-at-all",
            "depth": "standard",
            "audience": "technical",
            "max_cost_usd": 5.0,
            "max_runtime_minutes": 60,
            "freshness_days": 180,
        },
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = run_plan.invoke(
        intent_id="does-not-exist-at-all",
        idempotency_key="idem-missing-intent",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is False
    assert result.result is None
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"


# ---------------------------------------------------------------------------
# H7 defect fix: an above-ceiling intent denies at the guard stage, with the
# SAME `not_found` shape a genuinely-missing target gets (this task's
# negative fixture -- proves the fix, not merely the absence of a crash).
# ---------------------------------------------------------------------------


def test_invoke_denies_above_ceiling_h7_guard_stage_indistinguishable_from_missing_intent(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Before this task's fix, `run_plan.invoke` accepted a caller-supplied
    `sensitivity_ceiling` defaulting to `"client_sensitive"` (the loosest
    label) -- `_check_guard`'s H7 comparison
    (`_sensitivity_rank(effective_sensitivity) > _ceiling_rank(ceiling)`)
    could then never deny for any caller that did not go out of its way to
    override the default, making the guard a permanent no-op. This proves
    the fix: with the LOCALLY CONFIGURED ceiling resolved to `"public"`
    (patched here to simulate `foundry.yaml`'s `operator_mcp.
    sensitivity_ceiling: public`, below `resolve_local_sensitivity_
    ceiling`'s own fail-closed default too), a real, existing intent whose
    OWN declared `governance.sensitivity` is `"personal"` -- one rank above
    `"public"` -- is denied.

    Also proves H6/H7's one-denial-shape guarantee end to end at this
    adapter's own public surface: the above-ceiling denial (real intent,
    too sensitive) and a genuinely-missing-intent denial (no intent at all,
    `_resolve_intent_sensitivity` swallows the lookup failure and resolves
    to the STRICTEST label, `"client_sensitive"`, itself above the SAME
    `"public"` ceiling) are BYTE-IDENTICAL `error` envelopes -- an attacker
    probing `run.plan` cannot distinguish "this intent exists but you are
    not cleared for it" from "this intent does not exist" from the
    response alone, which is precisely H7's design intent (mirrors
    `test_operator_mcp_adapter_job_lifecycle.py`'s own
    `*_wrong_workspace_indistinguishable_from_missing` convention).
    """

    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)
    identity = AuthIdentity("alice", "ws-mine", ("owner",))
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", lambda *a, **kw: "public")

    # Direct proof of STAGE: build the identical PolicyContext `invoke()`
    # would build internally and evaluate it directly, so the stage
    # attribute (not exposed on the adapter's own bounded envelope) can be
    # asserted precisely.
    direct_ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=run_plan.OPERATION_KIND,
        idempotency_key="idem-above-ceiling",
        effective_sensitivity=policy.resolve_effective_sensitivity(
            run_plan._resolve_intent_sensitivity(intent_id, tmp_foundry)
        ),
        sensitivity_ceiling="public",
        input_payload={"intent_id": intent_id, "depth": "standard", "audience": "technical"},
        paths=tmp_foundry,
    )
    direct_decision = policy.evaluate_policy(direct_ctx, paths=tmp_foundry)
    assert direct_decision.allowed is False
    assert direct_decision.stage == "guard"
    assert direct_decision.reason_code == "not_found"
    assert direct_decision.retryable is False

    above_ceiling_result = run_plan.invoke(
        intent_id=intent_id,
        idempotency_key="idem-above-ceiling",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )
    missing_intent_result = run_plan.invoke(
        intent_id="does-not-exist-at-all-either",
        idempotency_key="idem-above-ceiling-missing",
        confirmation_record=None,
        presented_token=None,
        dry_run=True,
        paths=tmp_foundry,
    )

    assert above_ceiling_result.ok is False
    assert above_ceiling_result.error is not None
    assert above_ceiling_result.error["reason_code"] == "not_found"
    assert above_ceiling_result.error["retryable"] is False
    assert above_ceiling_result.error["operation_id"] is None
    assert above_ceiling_result.error["receipt_ref"] is None
    assert "detail" not in above_ceiling_result.error

    assert missing_intent_result.ok is False
    assert above_ceiling_result.error == missing_intent_result.error
