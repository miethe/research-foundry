"""Unit tests for `operator_mcp_policy` (research-foundry-operator-mcp-v1 P1,
OPM-1.2/1.3).

Covers: trusted local identity resolution (OPM-OQ-1), the fixed six-stage
policy order (capability -> rbac -> audit_health -> guard -> preflight ->
confirmation), the confirmation lifecycle (mint/verify/consume, OPM-OQ-2/3
-- TTL expiry, replay-as-success vs mismatch-as-denial, idempotency
conflict), the bounded/redacted error envelope, and the Knowledge MCP
tool-name disjointness invariant (invariant 6).

Also covers the security-review round 1 fix cycle (see
`.claude/findings/research-foundry-operator-mcp-findings.md`, section
FIND-P1): C1 (authorize_operation never conflates exact-replay with an
execute authorization), H2/H3/H7 (no permissive defaults on governed
fields), H4/H5 (expiry fails closed on every branch; consumption is a
guarded transition), H6/H7 (one denial shape for every post-lookup
no-existence-leak case), H8 (exception boundary), M1 (bounded envelope
enforced in code), M3 (`_bindings_match` identity-None guard), M4 (config
threaded into redaction), M5 (no `rule_id` leak), L4 (`allow_nan=False`),
L5 (naive timestamps rejected, never coerced).
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.services import audit_service, governance
from research_foundry.services.export_service import SENSITIVITY_ORDER
from research_foundry.services import operator_mcp_policy as policy
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_IDENTITY = AuthIdentity("alice", "ws-mine", ("owner",))
_IDENTITY_OTHER_WORKSPACE = AuthIdentity("bob", "ws-other", ("owner",))
_VIEWER_IDENTITY = AuthIdentity("carol", "ws-mine", ("viewer",))


def _write_operator_identity(paths: FoundryPaths, *, user_id: str, workspace_id: str, roles: list[str]) -> None:
    data: dict[str, Any] = load_yaml(paths.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"]["operator_mcp"] = {
        "identity": {"user_id": user_id, "workspace_id": workspace_id, "roles": roles}
    }
    dump_yaml(data, paths.foundry_yaml)


def _basic_ctx(**overrides: Any) -> policy.PolicyContext:
    """Build a `PolicyContext`. `sensitivity_ceiling` defaults to the
    loosest label (`client_sensitive`) so existing guard/preflight/
    confirmation tests are unaffected by the H7 ceiling gate unless they
    explicitly opt into testing it. When `targets` is supplied and
    `resolved_target_workspaces` is not explicitly overridden, it is
    auto-filled to match `identity.workspace_id` for every target (H3
    requires a same-length entry per target; tests that specifically
    exercise the wrong-workspace/absent-target gate pass an explicit
    override)."""

    fields: dict[str, Any] = {
        "identity": _IDENTITY,
        "operation_kind": "run.plan",
        "idempotency_key": "idem-1",
        "targets": (),
        "effective_sensitivity": "public",
        "sensitivity_ceiling": "client_sensitive",
    }
    fields.update(overrides)
    targets = fields.get("targets") or ()
    if targets and "resolved_target_workspaces" not in overrides:
        identity = fields.get("identity")
        workspace = identity.workspace_id if identity is not None else None
        fields["resolved_target_workspaces"] = tuple(workspace for _ in targets)
    return policy.PolicyContext(**fields)


def _run_targets() -> tuple[policy.TargetRef, ...]:
    return (policy.TargetRef("run", "run_demo"),)


# ---------------------------------------------------------------------------
# Identity resolution (OPM-OQ-1)
# ---------------------------------------------------------------------------


def test_resolve_operator_identity_missing_block_returns_none(tmp_foundry: FoundryPaths) -> None:
    assert policy.resolve_operator_identity(tmp_foundry) is None


def test_resolve_operator_identity_incomplete_block_returns_none(tmp_foundry: FoundryPaths) -> None:
    data: dict[str, Any] = load_yaml(tmp_foundry.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"]["operator_mcp"] = {"identity": {"user_id": "alice"}}  # missing workspace_id/roles
    dump_yaml(data, tmp_foundry.foundry_yaml)
    assert policy.resolve_operator_identity(tmp_foundry) is None


def test_resolve_operator_identity_roles_not_list_returns_none(tmp_foundry: FoundryPaths) -> None:
    data: dict[str, Any] = load_yaml(tmp_foundry.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"]["operator_mcp"] = {
        "identity": {"user_id": "alice", "workspace_id": "default", "roles": "owner"}
    }
    dump_yaml(data, tmp_foundry.foundry_yaml)
    assert policy.resolve_operator_identity(tmp_foundry) is None


def test_resolve_operator_identity_valid_block_resolves(tmp_foundry: FoundryPaths) -> None:
    _write_operator_identity(tmp_foundry, user_id="alice", workspace_id="default", roles=["owner"])
    identity = policy.resolve_operator_identity(tmp_foundry)
    assert identity is not None
    assert identity.user_id == "alice"
    assert identity.workspace_id == "default"
    assert identity.roles == ("owner",)


# ---------------------------------------------------------------------------
# Effective sensitivity (strictest wins)
# ---------------------------------------------------------------------------


def test_resolve_effective_sensitivity_strictest_wins() -> None:
    assert policy.resolve_effective_sensitivity("public", "work_sensitive", "personal") == "work_sensitive"


def test_resolve_effective_sensitivity_defaults_to_public_when_empty() -> None:
    assert policy.resolve_effective_sensitivity() == "public"
    assert policy.resolve_effective_sensitivity(None, None) == "public"


def test_resolve_effective_sensitivity_unknown_label_fails_closed_to_strictest() -> None:
    assert policy.resolve_effective_sensitivity("public", "not_a_real_label") == policy.SENSITIVITY_LEVELS[-1]


def test_sensitivity_levels_match_export_service_vocabulary() -> None:
    assert set(policy.SENSITIVITY_LEVELS) == set(SENSITIVITY_ORDER)
    # Same rank order too.
    ranked = sorted(policy.SENSITIVITY_LEVELS, key=lambda s: SENSITIVITY_ORDER[s])
    assert ranked == list(policy.SENSITIVITY_LEVELS)


# ---------------------------------------------------------------------------
# PolicyContext construction-time invariants (H2/H3/H7/H8 -- "impossible to
# construct a context that skips a governance check by omitting a field")
# ---------------------------------------------------------------------------


def test_context_rejects_unknown_effective_sensitivity() -> None:
    with pytest.raises(ValueError):
        _basic_ctx(effective_sensitivity="not_a_real_label")


def test_context_rejects_unknown_sensitivity_ceiling() -> None:
    with pytest.raises(ValueError):
        _basic_ctx(sensitivity_ceiling="not_a_real_label")


def test_context_requires_effective_sensitivity_and_ceiling_no_default() -> None:
    # No default exists at all -- omitting either is a TypeError (missing
    # positional/keyword argument), not a silently-permissive fallback.
    with pytest.raises(TypeError):
        policy.PolicyContext(
            identity=_IDENTITY,
            operation_kind="run.plan",
            idempotency_key="idem-1",
        )  # type: ignore[call-arg]


def test_context_rejects_target_count_mismatch_with_resolved_workspaces() -> None:
    with pytest.raises(ValueError):
        policy.PolicyContext(
            identity=_IDENTITY,
            operation_kind="run.plan",
            idempotency_key="idem-1",
            effective_sensitivity="public",
            sensitivity_ceiling="client_sensitive",
            targets=_run_targets(),
            resolved_target_workspaces=(),  # missing entry -- H3
        )


def test_context_rejects_non_json_primitive_input_payload() -> None:
    with pytest.raises(ValueError):
        _basic_ctx(input_payload={"bad": object()})


def test_context_accepts_nested_json_primitive_input_payload() -> None:
    ctx = _basic_ctx(input_payload={"a": [1, "two", {"three": None, "four": True}]})
    assert ctx.input_payload["a"][1] == "two"


# ---------------------------------------------------------------------------
# Capability stage
# ---------------------------------------------------------------------------


def test_capability_rejects_unknown_operation_kind(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(operation_kind="shell.exec")
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "capability"
    assert decision.reason_code == "operation_unknown"


def test_capability_rejects_wildcard_operation_kind(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(operation_kind="*")
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.reason_code == "operation_unknown"


def test_capability_rejects_unknown_target_kind(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(targets=(policy.TargetRef("filesystem_path", "/etc/passwd"),))
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "capability"
    assert decision.reason_code == "target_invalid"


def test_capability_rejects_oversized_targets_array(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(targets=tuple(policy.TargetRef("run", f"run_{i}") for i in range(21)))
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "capability"
    assert decision.reason_code == "payload_too_large"


def test_capability_rejects_oversized_input_payload(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(input_payload={f"field_{i}": i for i in range(33)})
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "capability"
    assert decision.reason_code == "payload_too_large"


def test_check_tool_name_rejects_unknown_and_wildcard() -> None:
    assert policy.check_tool_name("run.plan").allowed
    assert policy.check_tool_name(policy.PREFLIGHT_TOOL_NAME).allowed
    for bad in ("*", "shell.exec", "writeback.execute", "agent-job.accept", "url.fetch"):
        decision = policy.check_tool_name(bad)
        assert decision.denied
        assert decision.reason_code == "tool_unknown"


# ---------------------------------------------------------------------------
# RBAC / identity stage (no-existence-leak invariant)
# ---------------------------------------------------------------------------


def test_missing_identity_denied_with_identity_denied_code(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(identity=None, targets=_run_targets())
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "rbac"
    assert decision.reason_code == "identity_denied"


def test_matching_resolved_target_workspace_is_not_denied(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(targets=_run_targets(), resolved_target_workspaces=("ws-mine",))
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.allowed


def test_rbac_denies_insufficient_role_for_mutating_kind(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(identity=_VIEWER_IDENTITY)
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "rbac"
    assert decision.reason_code == "rbac_denied"


def test_rbac_allows_viewer_for_read_only_job_status(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(
        identity=_VIEWER_IDENTITY, operation_kind="job.status", targets=(policy.TargetRef("agent_job", "aj_1"),)
    )
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.allowed


# ---------------------------------------------------------------------------
# Audit-health stage (OPM-OQ-6)
# ---------------------------------------------------------------------------


def test_audit_unhealthy_blocks_mutating_operation(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(audit_service, "is_healthy_for_exposure", lambda paths: False)
    ctx = _basic_ctx(targets=_run_targets())
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "audit_health"
    assert decision.reason_code == "audit_unhealthy"
    assert decision.retryable is True


def test_audit_unhealthy_does_not_block_job_status(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(audit_service, "is_healthy_for_exposure", lambda paths: False)
    ctx = _basic_ctx(operation_kind="job.status", targets=(policy.TargetRef("agent_job", "aj_1"),))
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.allowed


def test_audit_health_never_probed_does_not_block_mutating_operation(tmp_foundry: FoundryPaths) -> None:
    """M6 wontfix-justified: a pristine workspace with no audit_health row
    (never probed) must still ALLOW mutating operations -- otherwise
    operator MCP would be unusable out of the box, since P1 has no
    probe-triggering code path. Locks in the documented decision so it
    cannot silently flip in either direction."""

    ctx = _basic_ctx(targets=_run_targets())
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert not (decision.denied and decision.stage == "audit_health")


# ---------------------------------------------------------------------------
# Guard stage (real governance.guard_check reuse) + H7 sensitivity ceiling
# ---------------------------------------------------------------------------


def test_guard_blocks_work_sensitive_to_unapproved_provider(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(
        targets=_run_targets(),
        effective_sensitivity="work_sensitive",
        model_provider="some_unapproved_provider",
    )
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "guard"
    assert decision.reason_code == "guard_blocked"
    assert decision.retryable is False


def test_guard_requires_review_for_work_sensitive_meatywiki_writeback(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(
        operation_kind="writeback.preview",
        targets=(policy.TargetRef("evidence_bundle", "eb_demo"),),
        effective_sensitivity="work_sensitive",
        writeback_targets=("meatywiki",),
    )
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "guard"
    assert decision.reason_code == "guard_review_required"
    assert decision.retryable is True


def test_guard_passes_for_public_sensitivity(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(targets=_run_targets(), effective_sensitivity="public")
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.allowed


def test_guard_denies_rule_id_never_reaches_policy_decision_or_error(tmp_foundry: FoundryPaths) -> None:
    """M5: governance `rule_id` (e.g. `no_work_sensitive_to_unapproved_provider`)
    must never leak into `PolicyDecision.detail` or a built error envelope."""

    ctx = _basic_ctx(
        targets=_run_targets(),
        effective_sensitivity="work_sensitive",
        model_provider="some_unapproved_provider",
    )
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.reason_code == "guard_blocked"
    assert decision.detail is None
    error = policy.build_error(decision)
    assert "detail" not in error
    assert "no_work_sensitive_to_unapproved_provider" not in repr(error)


def test_guard_denies_above_sensitivity_ceiling_with_not_found(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(
        targets=_run_targets(), effective_sensitivity="client_sensitive", sensitivity_ceiling="public"
    )
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "guard"
    assert decision.reason_code == "not_found"
    assert decision.retryable is False


def test_guard_allows_when_effective_sensitivity_within_ceiling(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(
        targets=_run_targets(), effective_sensitivity="personal", sensitivity_ceiling="personal"
    )
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.allowed


# ---------------------------------------------------------------------------
# H6: one denial shape for every post-lookup no-existence-leak case
# ---------------------------------------------------------------------------


def test_wrong_workspace_above_ceiling_and_genuinely_missing_target_share_one_denial_shape(
    tmp_foundry: FoundryPaths,
) -> None:
    """Replaces the prior (wrong-pair) test that compared wrong-workspace
    against MISSING IDENTITY -- proving nothing, since both traveled the
    same `identity is None` code path. This compares the three DISTINCT
    post-lookup scenarios H6 requires to be indistinguishable: a target
    owned by another workspace, a target above the caller's sensitivity
    ceiling, and a target that could not be resolved at all."""

    wrong_workspace_ctx = _basic_ctx(targets=_run_targets(), resolved_target_workspaces=("ws-other",))
    genuinely_missing_ctx = _basic_ctx(targets=_run_targets(), resolved_target_workspaces=(None,))
    above_ceiling_ctx = _basic_ctx(
        targets=_run_targets(), effective_sensitivity="client_sensitive", sensitivity_ceiling="public"
    )

    decisions = [
        policy.evaluate_policy(wrong_workspace_ctx, paths=tmp_foundry),
        policy.evaluate_policy(genuinely_missing_ctx, paths=tmp_foundry),
        policy.evaluate_policy(above_ceiling_ctx, paths=tmp_foundry),
    ]
    for decision in decisions:
        assert decision.denied
        assert decision.reason_code == "not_found"
        assert decision.retryable is False
        assert decision.detail is None

    envelopes = [policy.build_error(d, operation_id=None, receipt_ref=None) for d in decisions]
    reference = {k: v for k, v in envelopes[0].items() if k not in ("occurred_at",)}
    for envelope in envelopes[1:]:
        comparable = {k: v for k, v in envelope.items() if k not in ("occurred_at",)}
        assert comparable == reference
    for envelope in envelopes:
        assert envelope["reason_code"] == "not_found"
        assert envelope["message"] == policy._SAFE_MESSAGES["not_found"]
        assert envelope["retryable"] is False
        assert "detail" not in envelope


def test_identity_denied_reserved_strictly_for_missing_identity(tmp_foundry: FoundryPaths) -> None:
    missing_identity_decision = policy.evaluate_policy(
        _basic_ctx(identity=None, targets=_run_targets(), resolved_target_workspaces=(None,)),
        paths=tmp_foundry,
    )
    wrong_workspace_decision = policy.evaluate_policy(
        _basic_ctx(targets=_run_targets(), resolved_target_workspaces=("ws-other",)), paths=tmp_foundry
    )
    assert missing_identity_decision.reason_code == "identity_denied"
    assert wrong_workspace_decision.reason_code == "not_found"
    assert missing_identity_decision.reason_code != wrong_workspace_decision.reason_code


# ---------------------------------------------------------------------------
# Preflight stage (stage-prerequisite target kinds)
# ---------------------------------------------------------------------------


def test_preflight_denies_missing_required_target(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(operation_kind="swarm.start", targets=())
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "preflight"
    assert decision.reason_code == "preflight_failed"
    assert decision.retryable is True


def test_preflight_passes_when_required_target_present(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(operation_kind="swarm.start", targets=(policy.TargetRef("run", "run_demo"),))
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.allowed


# ---------------------------------------------------------------------------
# Fixed stage order (invariant 2)
# ---------------------------------------------------------------------------


def test_stage_order_is_capability_before_rbac_before_audit_health_before_guard_before_preflight(
    tmp_foundry: FoundryPaths,
) -> None:
    """A request that would fail EVERY stage must fail at the FIRST one
    (capability) -- proves the fixed order, not just that each stage works
    in isolation."""

    ctx = _basic_ctx(identity=None, operation_kind="shell.exec")
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.stage == "capability"
    assert decision.reason_code == "operation_unknown"

    # Fix capability, still fails at rbac (identity missing) before audit/guard/preflight.
    ctx2 = _basic_ctx(identity=None, operation_kind="swarm.start", targets=())
    decision2 = policy.evaluate_policy(ctx2, paths=tmp_foundry)
    assert decision2.stage == "rbac"


def test_authorize_operation_runs_confirmation_stage_last(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(targets=_run_targets())
    decision = policy.authorize_operation(
        ctx, confirmation_record=None, presented_token=None, paths=tmp_foundry
    )
    assert decision.denied
    assert decision.stage == "confirmation"
    assert decision.reason_code == "confirmation_missing"


# ---------------------------------------------------------------------------
# H8: exception boundary -- evaluate_policy/authorize_operation/verify_confirmation
# never raise; unexpected failures become internal_error.
# ---------------------------------------------------------------------------


def test_evaluate_policy_wraps_unexpected_exception_as_internal_error(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(_ctx: Any, *, paths: Any = None) -> Any:
        raise RuntimeError("simulated malformed config/governance.yaml -- must never leak")

    monkeypatch.setattr(governance, "guard_check", _boom)
    ctx = _basic_ctx(targets=_run_targets())
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "guard"
    assert decision.reason_code == "internal_error"
    assert decision.retryable is True

    error = policy.build_error(decision)
    assert error["reason_code"] == "internal_error"
    assert "simulated" not in error["message"]
    assert "simulated" not in error.get("detail", "")


def test_verify_confirmation_wraps_unexpected_exception_as_internal_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)

    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("simulated failure inside _bindings_match")

    monkeypatch.setattr(policy, "_bindings_match", _boom)
    verification = policy.verify_confirmation(issued.record, presented_token=issued.token, ctx=ctx)
    assert verification.outcome == "error"
    assert verification.decision.reason_code == "internal_error"
    assert verification.decision.retryable is True


def test_authorize_operation_wraps_unexpected_exception_as_internal_error(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)

    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("simulated failure inside verify_confirmation")

    monkeypatch.setattr(policy, "verify_confirmation", _boom)
    decision = policy.authorize_operation(
        ctx, confirmation_record=issued.record, presented_token=issued.token, paths=tmp_foundry
    )
    assert decision.denied
    assert decision.reason_code == "internal_error"
    assert decision.retryable is True


# ---------------------------------------------------------------------------
# Confirmation lifecycle (OPM-OQ-2/3)
# ---------------------------------------------------------------------------


def test_mint_confirmation_requires_identity() -> None:
    ctx = _basic_ctx(identity=None)
    with pytest.raises(ValueError):
        policy.mint_confirmation(ctx)


def test_mint_and_verify_accepted() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    assert issued.record["status"] == "issued"
    verification = policy.verify_confirmation(
        issued.record, presented_token=issued.token, ctx=ctx
    )
    assert verification.outcome == "accepted"
    assert verification.decision.allowed


def test_verify_confirmation_missing_token_or_record() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    v1 = policy.verify_confirmation(None, presented_token=issued.token, ctx=ctx)
    assert v1.outcome == "missing"
    assert v1.decision.reason_code == "confirmation_missing"
    v2 = policy.verify_confirmation(issued.record, presented_token=None, ctx=ctx)
    assert v2.outcome == "missing"
    assert v2.decision.reason_code == "confirmation_missing"


def test_verify_confirmation_wrong_token_digest_is_missing() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    verification = policy.verify_confirmation(issued.record, presented_token="not-the-real-token", ctx=ctx)
    assert verification.outcome == "missing"
    assert verification.decision.reason_code == "confirmation_missing"


def test_verify_confirmation_expired_token() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    minted_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    issued = policy.mint_confirmation(ctx, now=minted_at)
    later = minted_at + policy.CONFIRMATION_TTL + timedelta(seconds=1)
    verification = policy.verify_confirmation(
        issued.record, presented_token=issued.token, ctx=ctx, now=later
    )
    assert verification.outcome == "expired"
    assert verification.decision.reason_code == "confirmation_expired"
    assert verification.decision.retryable is True


@pytest.mark.parametrize(
    "mutate",
    [
        lambda ctx: dataclasses.replace(ctx, idempotency_key="different-key"),
        lambda ctx: dataclasses.replace(ctx, operation_kind="run.extract", targets=_run_targets()),
        lambda ctx: dataclasses.replace(ctx, policy_snapshot_version="policy-order-v2"),
        lambda ctx: dataclasses.replace(ctx, effective_sensitivity="work_sensitive"),
        lambda ctx: dataclasses.replace(ctx, targets=(policy.TargetRef("run", "run_other"),)),
        lambda ctx: dataclasses.replace(ctx, identity=_IDENTITY_OTHER_WORKSPACE),
        lambda ctx: dataclasses.replace(ctx, input_payload={"changed": True}),
    ],
    ids=["idempotency_key", "operation_kind", "policy_snapshot_version", "effective_sensitivity", "targets", "actor_workspace", "input_payload"],
)
def test_verify_confirmation_mismatched_bound_field_denies(mutate) -> None:
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    changed_ctx = mutate(ctx)
    verification = policy.verify_confirmation(issued.record, presented_token=issued.token, ctx=changed_ctx)
    assert verification.outcome == "mismatched"
    assert verification.decision.reason_code == "confirmation_mismatch"
    assert verification.decision.retryable is False


def test_exact_replay_after_consumption_is_not_an_error() -> None:
    """`verify_confirmation` called DIRECTLY still reports exact replay as
    "not an error" -- this is the richer, non-boolean-shaped API a caller
    (P2) uses when it explicitly wants to route to the prior receipt. See
    the C1 tests below for why `authorize_operation` behaves differently."""

    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64)
    assert consumed is not None
    assert consumed["status"] == "consumed"

    verification = policy.verify_confirmation(consumed, presented_token=issued.token, ctx=ctx)
    assert verification.outcome == "exact_replay"
    assert verification.decision.allowed
    assert verification.decision.reason_code is None


def test_consumed_token_with_changed_inputs_is_idempotency_conflict() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64)
    assert consumed is not None

    changed_ctx = dataclasses.replace(ctx, idempotency_key="different-key")
    verification = policy.verify_confirmation(consumed, presented_token=issued.token, ctx=changed_ctx)
    assert verification.outcome == "mismatched"
    assert verification.decision.reason_code == "idempotency_conflict"
    assert verification.decision.retryable is False


def test_confirmation_not_required_kind_never_needs_a_token(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(operation_kind="job.status", targets=(policy.TargetRef("agent_job", "aj_1"),))
    decision = policy.authorize_operation(
        ctx, confirmation_record=None, presented_token=None, paths=tmp_foundry
    )
    assert decision.allowed
    assert decision.stage == "confirmation"


def test_authorize_operation_full_success_path(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(targets=_run_targets())
    preflight = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert preflight.allowed
    issued = policy.mint_confirmation(ctx)
    decision = policy.authorize_operation(
        ctx, confirmation_record=issued.record, presented_token=issued.token, paths=tmp_foundry
    )
    assert decision.allowed
    assert decision.stage == "confirmation"


# ---------------------------------------------------------------------------
# C1: authorize_operation must never conflate exact replay with an execute
# authorization.
# ---------------------------------------------------------------------------


def test_authorize_operation_denies_exact_replay_never_returns_accept(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)

    accepted = policy.authorize_operation(
        ctx, confirmation_record=issued.record, presented_token=issued.token, paths=tmp_foundry
    )
    assert accepted.allowed

    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64)
    assert consumed is not None

    # verify_confirmation directly: still correctly "not an error".
    direct_verification = policy.verify_confirmation(consumed, presented_token=issued.token, ctx=ctx)
    assert direct_verification.outcome == "exact_replay"
    assert direct_verification.decision.allowed

    # authorize_operation: the execute-time, boolean-shaped entry point --
    # a caller doing `if authorize_operation(...).allowed: execute()` must
    # NOT execute on replay.
    replay_decision = policy.authorize_operation(
        ctx, confirmation_record=consumed, presented_token=issued.token, paths=tmp_foundry
    )
    assert replay_decision.denied
    assert replay_decision.allowed is False
    assert replay_decision.reason_code == "confirmation_replayed"
    assert replay_decision.retryable is False

    # The two decisions are NOT equal -- a replay can never be mistaken for
    # the original accept.
    assert replay_decision != accepted
    assert replay_decision.stage == accepted.stage == "confirmation"
    assert replay_decision.allowed != accepted.allowed


# ---------------------------------------------------------------------------
# H4: expiry fails closed in every branch, including consumed/exact-replay.
# ---------------------------------------------------------------------------


def test_verify_confirmation_missing_expires_at_fails_closed() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    record = dict(issued.record)
    record["expires_at"] = None
    verification = policy.verify_confirmation(record, presented_token=issued.token, ctx=ctx)
    assert verification.outcome == "expired"
    assert verification.decision.reason_code == "confirmation_expired"


def test_verify_confirmation_far_future_expires_at_is_clamped_to_ttl() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    minted_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    issued = policy.mint_confirmation(ctx, now=minted_at)
    record = dict(issued.record)
    record["expires_at"] = "3000-01-01T00:00:00Z"  # forged/hand-edited far-future expiry
    later = minted_at + policy.CONFIRMATION_TTL + timedelta(seconds=1)
    verification = policy.verify_confirmation(record, presented_token=issued.token, ctx=ctx, now=later)
    assert verification.outcome == "expired"
    assert verification.decision.reason_code == "confirmation_expired"


def test_verify_confirmation_unparseable_issued_at_fails_closed() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    record = dict(issued.record)
    record["issued_at"] = "not-a-timestamp"
    verification = policy.verify_confirmation(record, presented_token=issued.token, ctx=ctx)
    assert verification.outcome == "expired"


def test_exact_replay_still_fails_closed_when_expired() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    minted_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    issued = policy.mint_confirmation(ctx, now=minted_at)
    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64, now=minted_at)
    assert consumed is not None

    later = minted_at + policy.CONFIRMATION_TTL + timedelta(seconds=1)
    verification = policy.verify_confirmation(consumed, presented_token=issued.token, ctx=ctx, now=later)
    assert verification.outcome == "expired"
    assert verification.decision.reason_code == "confirmation_expired"
    assert verification.decision.allowed is False


def test_parse_iso_rejects_naive_datetime_never_coerces_to_utc() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    record = dict(issued.record)
    record["expires_at"] = "2030-01-01T00:00:00"  # naive -- no offset/Z
    verification = policy.verify_confirmation(record, presented_token=issued.token, ctx=ctx)
    assert verification.outcome == "expired"


# ---------------------------------------------------------------------------
# H5: consume_confirmation is a guarded compare-and-swap-shaped transition.
# ---------------------------------------------------------------------------


def test_consume_confirmation_refuses_to_rebind_an_already_consumed_record() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64)
    assert consumed is not None
    assert consumed["consumed_by_operation_id"] == "opm_" + "a" * 64

    # A second consumption attempt against the now-consumed record must be
    # refused (CAS precondition failure), never silently rebound to a new
    # operation_id.
    second = policy.consume_confirmation(consumed, operation_id="opm_" + "b" * 64)
    assert second is None


def test_consume_confirmation_refuses_expired_record() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    minted_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    issued = policy.mint_confirmation(ctx, now=minted_at)
    later = minted_at + policy.CONFIRMATION_TTL + timedelta(seconds=1)
    result = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64, now=later)
    assert result is None


def test_consume_confirmation_succeeds_for_fresh_issued_record() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64)
    assert consumed is not None
    assert consumed["status"] == "consumed"
    assert consumed["consumed_at"] is not None


# ---------------------------------------------------------------------------
# L3: mint_confirmation defensive guards (operation_kind/target_kind).
# ---------------------------------------------------------------------------


def test_mint_confirmation_rejects_unknown_operation_kind() -> None:
    ctx = policy.PolicyContext(
        identity=_IDENTITY,
        operation_kind="shell.exec",
        idempotency_key="idem-1",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
    )
    with pytest.raises(ValueError):
        policy.mint_confirmation(ctx)


def test_mint_confirmation_rejects_unknown_target_kind() -> None:
    ctx = policy.PolicyContext(
        identity=_IDENTITY,
        operation_kind="run.plan",
        idempotency_key="idem-1",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("filesystem_path", "/etc/passwd"),),
        resolved_target_workspaces=("ws-mine",),
    )
    with pytest.raises(ValueError):
        policy.mint_confirmation(ctx)


# ---------------------------------------------------------------------------
# M3: _bindings_match identity-None guard (first line, no vacuous match).
# ---------------------------------------------------------------------------


def test_bindings_match_returns_false_when_identity_is_none() -> None:
    ctx = _basic_ctx(identity=None, targets=_run_targets(), resolved_target_workspaces=(None,))
    # A confirmation minted for a REAL identity, presented against a ctx
    # whose identity is None, must never spuriously match via a vacuous
    # {} == {} actor comparison.
    real_ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(real_ctx)
    assert policy._bindings_match(issued.record, ctx) is False


# ---------------------------------------------------------------------------
# L4: canonicalization hardening (allow_nan=False).
# ---------------------------------------------------------------------------


def test_canonical_json_rejects_nan_value() -> None:
    ctx = _basic_ctx(input_payload={"x": float("nan")})
    with pytest.raises(ValueError):
        ctx.canonical_json()


# ---------------------------------------------------------------------------
# M4: build_error threads FoundryConfig into redaction.
# ---------------------------------------------------------------------------


def test_build_error_threads_config_for_workspace_secret_patterns(tmp_foundry: FoundryPaths) -> None:
    data = load_yaml(tmp_foundry.config / "governance.yaml") or {}
    custom_pattern = r"WORKSPACE_SECRET_[A-Za-z0-9]+"
    data["secret_patterns"] = list(data.get("secret_patterns") or []) + [custom_pattern]
    dump_yaml(data, tmp_foundry.config / "governance.yaml")
    cfg = FoundryConfig(paths=tmp_foundry)

    decision = policy.PolicyDecision(False, "preflight", "preflight_failed", retryable=True)
    workspace_secret = "WORKSPACE_SECRET_abc123"

    without_config = policy.build_error(decision, detail=workspace_secret)
    assert without_config.get("detail") == workspace_secret  # builtin patterns don't know this shape

    with_config = policy.build_error(decision, detail=workspace_secret, config=cfg)
    assert workspace_secret not in with_config.get("detail", "")


# ---------------------------------------------------------------------------
# Bounded / redacted error envelope
# ---------------------------------------------------------------------------


def test_build_error_requires_denied_decision() -> None:
    allowed = policy.PolicyDecision(True, "guard")
    with pytest.raises(ValueError):
        policy.build_error(allowed)


def test_build_error_message_from_closed_safe_table_only() -> None:
    decision = policy.PolicyDecision(False, "guard", "guard_blocked", retryable=False, detail="rule fired")
    error = policy.build_error(decision, operation_id=None, receipt_ref=None)
    assert error["reason_code"] == "guard_blocked"
    assert error["message"] == policy._SAFE_MESSAGES["guard_blocked"]
    assert len(error["message"]) <= 300
    assert error["retryable"] is False
    assert error["operation_id"] is None
    assert error["receipt_ref"] is None
    assert "occurred_at" in error


def test_build_error_detail_is_redacted_and_bounded() -> None:
    decision = policy.PolicyDecision(
        False, "preflight", "preflight_failed", retryable=True, detail=None
    )
    secret_detail = "api_key: sk-ant-" + "x" * 40
    error = policy.build_error(decision, detail=secret_detail)
    assert "detail" in error
    assert "sk-ant-" not in error["detail"]
    assert len(error["detail"]) <= 500


def test_build_error_scrubs_traceback_shaped_detail() -> None:
    decision = policy.PolicyDecision(False, "preflight", "internal_error", retryable=False)
    raw = 'Traceback (most recent call last):\n  File "/x/y.py", line 12, in foo\nValueError: boom'
    error = policy.build_error(decision, detail=raw)
    assert "Traceback" not in error.get("detail", "")
    assert "File " not in error.get("detail", "")


def test_build_error_omits_detail_when_none() -> None:
    decision = policy.PolicyDecision(False, "capability", "operation_unknown", retryable=False)
    error = policy.build_error(decision)
    assert "detail" not in error


def test_build_error_rejects_unknown_reason_code() -> None:
    decision = policy.PolicyDecision(False, "capability", "not_a_real_reason_code", retryable=False)
    with pytest.raises(ValueError):
        policy.build_error(decision)


def test_all_safe_messages_cover_every_closed_reason_code() -> None:
    assert set(policy._SAFE_MESSAGES) == policy.CLOSED_REASON_CODES


def test_every_closed_reason_code_has_a_real_producer(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """L2: all seventeen reason codes now have at least one real producer
    (previously four -- confirmation_replayed, not_found, payload_too_large,
    internal_error -- had none)."""

    produced: set[str] = set()

    produced.add(policy.check_tool_name("shell.exec").reason_code)
    produced.add(policy.evaluate_policy(_basic_ctx(operation_kind="shell.exec"), paths=tmp_foundry).reason_code)
    produced.add(
        policy.evaluate_policy(
            _basic_ctx(targets=tuple(policy.TargetRef("run", f"run_{i}") for i in range(21))),
            paths=tmp_foundry,
        ).reason_code
    )
    produced.add(
        policy.evaluate_policy(
            _basic_ctx(targets=(policy.TargetRef("filesystem_path", "/x"),)), paths=tmp_foundry
        ).reason_code
    )
    produced.add(policy.evaluate_policy(_basic_ctx(identity=None), paths=tmp_foundry).reason_code)
    produced.add(policy.evaluate_policy(_basic_ctx(identity=_VIEWER_IDENTITY), paths=tmp_foundry).reason_code)
    produced.add(
        policy.evaluate_policy(
            _basic_ctx(targets=_run_targets(), resolved_target_workspaces=("ws-other",)), paths=tmp_foundry
        ).reason_code
    )
    produced.add(
        policy.evaluate_policy(
            _basic_ctx(
                targets=_run_targets(), effective_sensitivity="client_sensitive", sensitivity_ceiling="public"
            ),
            paths=tmp_foundry,
        ).reason_code
    )
    produced.add(
        policy.evaluate_policy(
            _basic_ctx(
                targets=_run_targets(),
                effective_sensitivity="work_sensitive",
                model_provider="some_unapproved_provider",
            ),
            paths=tmp_foundry,
        ).reason_code
    )
    produced.add(
        policy.evaluate_policy(
            _basic_ctx(
                operation_kind="writeback.preview",
                targets=(policy.TargetRef("evidence_bundle", "eb_demo"),),
                effective_sensitivity="work_sensitive",
                writeback_targets=("meatywiki",),
            ),
            paths=tmp_foundry,
        ).reason_code
    )
    produced.add(
        policy.evaluate_policy(_basic_ctx(operation_kind="swarm.start", targets=()), paths=tmp_foundry).reason_code
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(audit_service, "is_healthy_for_exposure", lambda paths: False)
        produced.add(
            policy.evaluate_policy(_basic_ctx(targets=_run_targets()), paths=tmp_foundry).reason_code
        )
    produced.add(
        policy.authorize_operation(
            _basic_ctx(targets=_run_targets()), confirmation_record=None, presented_token=None, paths=tmp_foundry
        ).reason_code
    )

    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    minted_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    expired_issued = policy.mint_confirmation(ctx, now=minted_at)
    later = minted_at + policy.CONFIRMATION_TTL + timedelta(seconds=1)
    produced.add(
        policy.verify_confirmation(
            expired_issued.record, presented_token=expired_issued.token, ctx=ctx, now=later
        ).decision.reason_code
    )
    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64)
    assert consumed is not None
    mismatched_ctx = dataclasses.replace(ctx, idempotency_key="different-key")
    produced.add(
        policy.verify_confirmation(consumed, presented_token=issued.token, ctx=mismatched_ctx).decision.reason_code
    )
    produced.add(
        policy.authorize_operation(
            ctx, confirmation_record=consumed, presented_token=issued.token, paths=tmp_foundry
        ).reason_code
    )
    fresh = policy.mint_confirmation(ctx)
    mismatched_bound = dataclasses.replace(ctx, idempotency_key="different-key-2")
    produced.add(
        policy.verify_confirmation(fresh.record, presented_token=fresh.token, ctx=mismatched_bound).decision.reason_code
    )

    def _boom(_ctx: Any, *, paths: Any = None) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(governance, "guard_check", _boom)
    produced.add(policy.evaluate_policy(_basic_ctx(targets=_run_targets()), paths=tmp_foundry).reason_code)

    produced.discard(None)
    missing = policy.CLOSED_REASON_CODES - produced
    assert not missing, f"reason codes with no producer exercised in this test: {missing}"


# ---------------------------------------------------------------------------
# Zero overlap with the read-only Knowledge MCP (invariant 6)
# ---------------------------------------------------------------------------


def test_no_overlap_with_knowledge_mcp_tool_names() -> None:
    from research_foundry.knowledge_mcp import registry as kmcp_registry

    assert set(policy.TOOL_NAMES).isdisjoint(set(kmcp_registry.TOOL_NAMES))
    assert set(policy.OPERATION_KINDS).isdisjoint(set(kmcp_registry.TOOL_NAMES))


def test_tool_names_is_operation_kinds_plus_preflight() -> None:
    assert set(policy.TOOL_NAMES) == set(policy.OPERATION_KINDS) | {policy.PREFLIGHT_TOOL_NAME}
    assert len(policy.TOOL_NAMES) == 14
    assert len(policy.OPERATION_KINDS) == 13


# ---------------------------------------------------------------------------
# Schema round-trip: code-level enums must match the frozen schema exactly
# ---------------------------------------------------------------------------


def _operation_schema() -> dict[str, Any]:
    from research_foundry.schemas import SchemaRegistry

    return SchemaRegistry().get("operator_mcp_operation")


def _error_schema() -> dict[str, Any]:
    from research_foundry.schemas import SchemaRegistry

    return SchemaRegistry().get("operator_mcp_error")


def test_operation_kind_enum_matches_schema() -> None:
    schema = _operation_schema()
    assert set(schema["properties"]["operation_kind"]["enum"]) == set(policy.OPERATION_KINDS)


def test_target_kind_enum_matches_schema() -> None:
    schema = _operation_schema()
    assert set(schema["$defs"]["target_ref"]["properties"]["target_kind"]["enum"]) == policy.TARGET_KINDS


def test_effective_sensitivity_enum_matches_schema() -> None:
    schema = _operation_schema()
    assert set(schema["properties"]["effective_sensitivity"]["enum"]) == set(policy.SENSITIVITY_LEVELS)


def test_reason_code_enum_matches_schema() -> None:
    schema = _error_schema()
    assert set(schema["properties"]["reason_code"]["enum"]) == policy.CLOSED_REASON_CODES
