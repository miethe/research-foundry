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
from research_foundry.services import operator_mcp_policy as policy
import research_foundry.services.planning as planning_module
from research_foundry.services.operator_mcp_adapters import run_plan
from research_foundry.services.operator_operation_service import OperatorOperationService

from tests.test_planning import _make_intent
from tests.unit.test_operator_mcp_policy import _default_operator_identity  # noqa: F401

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
