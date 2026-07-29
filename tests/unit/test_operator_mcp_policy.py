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

Also covers the security-review round 2 fix cycle (FIND-P1-R2): NEW-1
(exact replay structurally non-accepting on BOTH entry points -- not just
`authorize_operation`), NEW-2 (all 7 envelope bounds enforced, not 2),
NEW-3 (audit-health probes on demand -- M6 reopened and closed), NEW-4
(`resolve_effective_sensitivity` fails closed to strictest on empty
input), NEW-5 (config secret_patterns union with, never replace, the
built-ins), NEW-6 (`_ceiling_rank`'s opposite fail-closed direction),
NEW-7 (forged future `issued_at` no longer extends the TTL window), NEW-8
(NaN/non-Mapping payload rejected at construction; `mint_confirmation`'s
own raise-shaped boundary), NEW-9 (`build_error` forces null
operation_id/receipt_ref for `not_found`), NEW-11 (revoked status is
non-retryable), NEW-12 (`consume_confirmation` optional ctx-binding
precondition), NEW-13 (internal_error is now logged, redacted), NEW-14
(deep copy on consume; colocated stage names).

Also covers the security-review round 3 fix cycle (FIND-P1-R3): NEW-18
(`PolicyContext.identity` is `init=False`; `PolicyContext.for_configured_operator`
is the sole sanctioned constructor; `_check_identity_and_rbac` re-derives
identity from config and never trusts `ctx.identity`). Since `identity` is
no longer a public constructor field, this module drives identity
resolution for every test via the `_default_operator_identity` autouse
fixture below (which monkeypatches `policy.resolve_operator_identity`) --
tests needing a non-default identity re-patch it themselves; the identity-
resolution unit tests immediately below bypass the patch by calling
`_REAL_RESOLVE_OPERATOR_IDENTITY` directly.
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

# NEW-18: captured at import time, BEFORE the `_default_operator_identity`
# autouse fixture below ever runs -- lets the identity-resolution unit
# tests in the next section exercise the REAL `resolve_operator_identity`
# implementation directly, independent of whatever `policy.resolve_operator_identity`
# is monkeypatched to for every other test in this module.
_REAL_RESOLVE_OPERATOR_IDENTITY = policy.resolve_operator_identity


def _write_operator_identity(paths: FoundryPaths, *, user_id: str, workspace_id: str, roles: list[str]) -> None:
    data: dict[str, Any] = load_yaml(paths.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"]["operator_mcp"] = {
        "identity": {"user_id": user_id, "workspace_id": workspace_id, "roles": roles}
    }
    dump_yaml(data, paths.foundry_yaml)


@pytest.fixture(autouse=True)
def _default_operator_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """NEW-18: `PolicyContext.identity` has no public constructor field
    anymore -- `PolicyContext.for_configured_operator` (which `_basic_ctx`
    below calls) and `_check_identity_and_rbac` both resolve identity by
    calling `policy.resolve_operator_identity`. Patch that ONE seam to
    `_IDENTITY` by default so the ~100 tests in this module that don't care
    about identity resolution specifically keep working without each
    writing a `foundry.yaml` identity block. Tests that need a DIFFERENT
    resolved identity (`_VIEWER_IDENTITY`, `_IDENTITY_OTHER_WORKSPACE`, or
    none at all) call `monkeypatch.setattr(policy, "resolve_operator_identity",
    lambda *a, **kw: ...)` themselves -- a plain re-patch of the same
    attribute, restored to its ORIGINAL (pre-fixture) value at teardown
    either way. The identity-resolution unit tests immediately below
    bypass this fixture entirely via `_REAL_RESOLVE_OPERATOR_IDENTITY`."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)


def _forge_identity(ctx: policy.PolicyContext, identity: AuthIdentity | None) -> policy.PolicyContext:
    """Test-only helper simulating an attacker who bypasses
    `PolicyContext.for_configured_operator` (the sole sanctioned
    construction path, NEW-18 Layer 2) and forces an arbitrary `identity`
    directly onto an already-built, frozen `PolicyContext` via
    `object.__setattr__` -- the ONLY way `identity` can be set post-
    construction now that it is `init=False` (Layer 1). `dataclasses.replace`
    cannot do this: passing `identity` in its `changes` raises `TypeError`
    (a `field(init=False, ...)` field cannot be specified to `replace()`),
    so it is called here with NO changes purely to obtain an independent
    copy without mutating the caller's original `ctx` in place."""

    forged = dataclasses.replace(ctx)
    object.__setattr__(forged, "identity", identity)
    return forged


def _basic_ctx(**overrides: Any) -> policy.PolicyContext:
    """Build a `PolicyContext` via `PolicyContext.for_configured_operator`
    (NEW-18 -- the sole sanctioned constructor). `sensitivity_ceiling`
    defaults to the loosest label (`client_sensitive`) so existing guard/
    preflight/confirmation tests are unaffected by the H7 ceiling gate
    unless they explicitly opt into testing it. When `targets` is supplied
    and `resolved_target_workspaces` is not explicitly overridden, it is
    auto-filled to match whatever `policy.resolve_operator_identity`
    currently resolves to (H3 requires a same-length entry per target;
    tests that specifically exercise the wrong-workspace/absent-target gate
    pass an explicit override).

    NEW-18: `identity` is NOT an accepted override -- there is no public
    identity-injection door left on `PolicyContext` to pass one through.
    Whichever identity a built context resolves to is controlled entirely
    by whatever `policy.resolve_operator_identity` currently resolves to
    (see `_default_operator_identity` above); a test wanting a different
    identity monkeypatches that function itself BEFORE calling this
    helper."""

    fields: dict[str, Any] = {
        "operation_kind": "run.plan",
        "idempotency_key": "idem-1",
        "targets": (),
        "effective_sensitivity": "public",
        "sensitivity_ceiling": "client_sensitive",
    }
    fields.update(overrides)
    targets = fields.get("targets") or ()
    if targets and "resolved_target_workspaces" not in overrides:
        identity = policy.resolve_operator_identity()
        workspace = identity.workspace_id if identity is not None else None
        fields["resolved_target_workspaces"] = tuple(workspace for _ in targets)
    return policy.PolicyContext.for_configured_operator(**fields)


def _run_targets() -> tuple[policy.TargetRef, ...]:
    return (policy.TargetRef("run", "run_demo"),)


# ---------------------------------------------------------------------------
# Identity resolution (OPM-OQ-1)
# ---------------------------------------------------------------------------


def test_resolve_operator_identity_missing_block_returns_none(tmp_foundry: FoundryPaths) -> None:
    assert _REAL_RESOLVE_OPERATOR_IDENTITY(tmp_foundry) is None


def test_resolve_operator_identity_incomplete_block_returns_none(tmp_foundry: FoundryPaths) -> None:
    data: dict[str, Any] = load_yaml(tmp_foundry.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"]["operator_mcp"] = {"identity": {"user_id": "alice"}}  # missing workspace_id/roles
    dump_yaml(data, tmp_foundry.foundry_yaml)
    assert _REAL_RESOLVE_OPERATOR_IDENTITY(tmp_foundry) is None


def test_resolve_operator_identity_roles_not_list_returns_none(tmp_foundry: FoundryPaths) -> None:
    data: dict[str, Any] = load_yaml(tmp_foundry.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"]["operator_mcp"] = {
        "identity": {"user_id": "alice", "workspace_id": "default", "roles": "owner"}
    }
    dump_yaml(data, tmp_foundry.foundry_yaml)
    assert _REAL_RESOLVE_OPERATOR_IDENTITY(tmp_foundry) is None


def test_resolve_operator_identity_valid_block_resolves(tmp_foundry: FoundryPaths) -> None:
    _write_operator_identity(tmp_foundry, user_id="alice", workspace_id="default", roles=["owner"])
    identity = _REAL_RESOLVE_OPERATOR_IDENTITY(tmp_foundry)
    assert identity is not None
    assert identity.user_id == "alice"
    assert identity.workspace_id == "default"
    assert identity.roles == ("owner",)


# ---------------------------------------------------------------------------
# Effective sensitivity (strictest wins)
# ---------------------------------------------------------------------------


def test_resolve_effective_sensitivity_strictest_wins() -> None:
    assert policy.resolve_effective_sensitivity("public", "work_sensitive", "personal") == "work_sensitive"


def test_resolve_effective_sensitivity_fails_closed_to_strictest_when_empty() -> None:
    """NEW-4 fix (round 2): replaces the prior
    `test_resolve_effective_sensitivity_defaults_to_public_when_empty`,
    which pinned the UNSAFE shape -- empty input is the FAILED-LOOKUP case
    (every upstream sensitivity source returned None/empty), and this
    function PRODUCES the value `PolicyContext.effective_sensitivity`
    consumes. Resolving a failed lookup to "public" (the LOOSEST label)
    would silently reintroduce, in the producer, the exact permissive
    default H2 removed from the consumer. The old assertion
    (`== "public"`) was the unsafe shape; this asserts the safe one."""
    assert policy.resolve_effective_sensitivity() == policy.SENSITIVITY_LEVELS[-1]
    assert policy.resolve_effective_sensitivity(None, None) == policy.SENSITIVITY_LEVELS[-1]


def test_resolve_effective_sensitivity_unknown_label_fails_closed_to_strictest() -> None:
    assert policy.resolve_effective_sensitivity("public", "not_a_real_label") == policy.SENSITIVITY_LEVELS[-1]


def test_sensitivity_levels_match_export_service_vocabulary() -> None:
    assert set(policy.SENSITIVITY_LEVELS) == set(SENSITIVITY_ORDER)


# ---------------------------------------------------------------------------
# NEW-6 (round 2): `_ceiling_rank`'s fail-closed direction is OPPOSITE
# `_sensitivity_rank`'s -- an unknown ceiling must rank BELOW every known
# level, never ABOVE (which would grant unknown/malformed ceilings maximum
# clearance). Defense-in-depth: unreachable via normal `PolicyContext`
# construction (validated in __post_init__), tested at the unit level
# directly against the shared vocabulary-drift scenario the docstring names.
# ---------------------------------------------------------------------------


def test_sensitivity_rank_unknown_label_ranks_strictest() -> None:
    assert policy._sensitivity_rank("not_a_real_label") == len(SENSITIVITY_ORDER)
    assert policy._sensitivity_rank("not_a_real_label") > policy._sensitivity_rank(
        policy.SENSITIVITY_LEVELS[-1]
    )


def test_ceiling_rank_unknown_label_ranks_below_every_known_level() -> None:
    """NEW-6: the OPPOSITE direction from `_sensitivity_rank` -- an unknown
    ceiling must never be treated as maximum clearance."""
    assert policy._ceiling_rank("not_a_real_label") == -1
    for level in policy.SENSITIVITY_LEVELS:
        assert policy._ceiling_rank("not_a_real_label") < policy._ceiling_rank(level)
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
            operation_kind="run.plan",
            idempotency_key="idem-1",
        )  # type: ignore[call-arg]


def test_context_rejects_target_count_mismatch_with_resolved_workspaces() -> None:
    with pytest.raises(ValueError):
        policy.PolicyContext(
            operation_kind="run.plan",
            idempotency_key="idem-1",
            effective_sensitivity="public",
            sensitivity_ceiling="client_sensitive",
            targets=_run_targets(),
            resolved_target_workspaces=(),  # missing entry -- H3
        )


# ---------------------------------------------------------------------------
# NEW-18 (security review round 3): PolicyContext.identity has no public
# constructor field -- for_configured_operator is the sole sanctioned way
# to obtain a context with a populated identity, and _check_identity_and_rbac
# never trusts ctx.identity for the authorization decision regardless.
# ---------------------------------------------------------------------------


def test_policy_context_rejects_identity_kwarg() -> None:
    """Layer 1: `identity` is `init=False` -- the public constructor cannot
    ACCEPT an `identity=` keyword at all, let alone honor one. This is the
    test that fails if Layer 1 is ever reverted (e.g. `identity` regains a
    plain `init=True` field)."""
    with pytest.raises(TypeError):
        policy.PolicyContext(
            identity=_IDENTITY,  # type: ignore[call-arg]
            operation_kind="run.plan",
            idempotency_key="idem-1",
            effective_sensitivity="public",
            sensitivity_ceiling="client_sensitive",
        )


def test_bare_construction_identity_defaults_to_none() -> None:
    ctx = policy.PolicyContext(
        operation_kind="run.plan",
        idempotency_key="idem-1",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
    )
    assert ctx.identity is None


def test_for_configured_operator_populates_identity_from_config(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Layer 2: the ONE sanctioned constructor populates `identity` from
    `resolve_operator_identity` -- proven here against the REAL
    implementation (bypassing the module's default test patch) so this test
    fails if `for_configured_operator` stops calling it, or calls something
    else instead."""
    monkeypatch.setattr(policy, "resolve_operator_identity", _REAL_RESOLVE_OPERATOR_IDENTITY)

    # Before any identity is configured, the factory faithfully carries
    # `None` through rather than substituting a permissive default.
    ctx_none = policy.PolicyContext.for_configured_operator(
        operation_kind="run.plan",
        idempotency_key="idem-1",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        paths=tmp_foundry,
    )
    assert ctx_none.identity is None

    _write_operator_identity(tmp_foundry, user_id="alice", workspace_id="ws-mine", roles=["owner"])
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="run.plan",
        idempotency_key="idem-1",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        paths=tmp_foundry,
    )
    assert ctx.identity == _IDENTITY


def test_layer3_denies_forged_identity_forced_via_setattr(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Layer 3 -- the actual guard: a forged `identity` forced onto an
    already-built context via `object.__setattr__` (simulating a caller
    that bypasses `for_configured_operator` entirely) is DENIED by BOTH
    `evaluate_policy` and `authorize_operation` with `identity_denied`,
    never authorized against the forged value. This is the test that fails
    if Layer 3 is ever reverted to trusting `ctx.identity` directly."""
    ctx = _basic_ctx(targets=_run_targets())
    forged = _forge_identity(ctx, AuthIdentity("mallory", "ws-mine", ("owner",)))
    assert forged.identity != ctx.identity

    decision = policy.evaluate_policy(forged, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "rbac"
    assert decision.reason_code == "identity_denied"

    issued = policy.mint_confirmation(forged)
    exec_decision = policy.authorize_operation(
        forged, confirmation_record=issued.record, presented_token=issued.token, paths=tmp_foundry
    )
    assert exec_decision.denied
    assert exec_decision.stage == "rbac"
    assert exec_decision.reason_code == "identity_denied"

    # A forged identity that happens to be `None` is likewise never treated
    # as "skip the check" -- it re-derives and evaluates on the REAL
    # (configured) identity exactly as a bare, un-forged `ctx.identity is
    # None` context would.
    forged_none = _forge_identity(ctx, None)
    decision_none = policy.evaluate_policy(forged_none, paths=tmp_foundry)
    assert decision_none.allowed


def test_forged_identity_cannot_produce_an_authorized_mint_confirmation(
    tmp_foundry: FoundryPaths,
) -> None:
    """`mint_confirmation` has no `paths` parameter and cannot re-derive
    identity itself, so it embeds a forged `ctx.identity` into the minted
    record's `actor` block verbatim -- proving that record IS mintable.
    What must NOT be possible is using that record to complete an
    `authorize_operation` that returns `allowed=True`: `authorize_operation`
    always re-runs `evaluate_policy` first, whose `rbac` stage independently
    re-derives identity and denies the forgery before the confirmation
    stage is ever reached, regardless of what the record's `actor` block
    claims or whether the presented token/record binds correctly to it."""
    ctx = _basic_ctx(targets=_run_targets())
    forged = _forge_identity(ctx, AuthIdentity("mallory", "ws-mine", ("owner",)))

    # The forged confirmation mints successfully (mint_confirmation cannot
    # detect the forgery on its own) and its actor block reflects the
    # forged identity, not the real configured one.
    issued = policy.mint_confirmation(forged)
    assert issued.record["actor"]["user_id"] == "mallory"

    # Even presenting the SAME forged ctx/token/record combination back to
    # authorize_operation -- the only way execution could proceed -- is
    # denied at the rbac stage, never reaching (let alone passing) the
    # confirmation stage the minted record would otherwise satisfy.
    decision = policy.authorize_operation(
        forged, confirmation_record=issued.record, presented_token=issued.token, paths=tmp_foundry
    )
    assert decision.denied
    assert decision.allowed is False
    assert decision.stage == "rbac"
    assert decision.reason_code == "identity_denied"


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


# ---------------------------------------------------------------------------
# NEW-2 (round 2): all 7 declared envelope bounds enforced in code, not just
# the 2 counts (maxItems/maxProperties) round 1 enforced.
# ---------------------------------------------------------------------------


def test_capability_rejects_path_shaped_target_ref(tmp_foundry: FoundryPaths) -> None:
    """The exact attack NEW-2 names: a raw filesystem path as target_ref,
    which round 1's partial enforcement let pass every stage and reach a
    minted confirmation."""
    ctx = _basic_ctx(targets=(policy.TargetRef("run", "../../../etc/passwd"),))
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "capability"
    assert decision.reason_code == "target_invalid"


def test_capability_rejects_oversized_target_ref(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(targets=(policy.TargetRef("run", "r" * 257),))
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "capability"
    assert decision.reason_code == "target_invalid"


def test_capability_rejects_empty_idempotency_key(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(idempotency_key="")
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "capability"
    assert decision.reason_code == "payload_too_large"


def test_capability_rejects_oversized_idempotency_key(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(idempotency_key="k" * 129)
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "capability"
    assert decision.reason_code == "payload_too_large"


def test_capability_rejects_idempotency_key_with_disallowed_characters(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(idempotency_key="has a space")
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "capability"
    assert decision.reason_code == "payload_too_large"


def test_capability_rejects_oversized_policy_snapshot_version(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(policy_snapshot_version="v" * 65)
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


def test_missing_identity_denied_with_identity_denied_code(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: None)
    ctx = _basic_ctx(targets=_run_targets(), resolved_target_workspaces=(None,))
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "rbac"
    assert decision.reason_code == "identity_denied"


def test_matching_resolved_target_workspace_is_not_denied(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(targets=_run_targets(), resolved_target_workspaces=("ws-mine",))
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.allowed


def test_rbac_denies_insufficient_role_for_mutating_kind(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _VIEWER_IDENTITY)
    ctx = _basic_ctx()
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "rbac"
    assert decision.reason_code == "rbac_denied"


def test_rbac_denies_viewer_for_read_only_job_status(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NEW-22: INVERTED from `test_rbac_allows_viewer_for_read_only_job_status`.

    That test pinned behaviour that contradicted `api/auth/rbac.py`, which is
    the single source of truth for role grants: it sets `"viewer": set()`
    (zero permissions) and marks `run:read` as NOT granted to viewer. The old
    `_READ_ROLES` nevertheless included `viewer`, and this test asserted that
    divergence was correct. Per the standing rule "never pin unsafe behaviour
    with a test", the assertion is inverted rather than the fix weakened.
    """

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _VIEWER_IDENTITY)
    ctx = _basic_ctx(operation_kind="job.status", targets=(policy.TargetRef("agent_job", "aj_1"),))
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "rbac"
    assert decision.reason_code == "rbac_denied"


def test_rbac_allows_reviewer_for_read_only_job_status(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The read grant still admits `reviewer`, which rbac.py DOES give
    `run:read`. This pins that NEW-22 narrowed `_READ_ROLES` by exactly one
    role (`viewer`) rather than collapsing it to owner/admin."""

    reviewer = AuthIdentity("dave", "ws-mine", ("reviewer",))
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: reviewer)
    ctx = _basic_ctx(operation_kind="job.status", targets=(policy.TargetRef("agent_job", "aj_1"),))
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.allowed


def test_rbac_denies_researcher_for_agent_job_class_kinds(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NEW-22 core: `swarm.start`/`job.cancel`/`job.resume` are
    `agent_job:launch`-class actions. rbac.py withholds `agent_job:launch`
    from `researcher` explicitly, so the Operator MCP surface must too."""

    researcher = AuthIdentity("erin", "ws-mine", ("researcher",))
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: researcher)
    for kind, targets in (
        ("swarm.start", (policy.TargetRef("run", "run_1"),)),
        ("job.cancel", (policy.TargetRef("agent_job", "aj_1"),)),
        ("job.resume", (policy.TargetRef("agent_job", "aj_1"),)),
    ):
        ctx = _basic_ctx(operation_kind=kind, targets=targets)
        decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
        assert decision.denied, f"{kind} must deny researcher"
        assert decision.stage == "rbac"
        assert decision.reason_code == "rbac_denied"


def test_rbac_still_allows_researcher_for_non_agent_job_mutations(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NEW-22 must not over-correct: researcher keeps the catalog/report-class
    mutations rbac.py DOES grant it (`catalog:create`/`update`,
    `report:create`/`update`)."""

    researcher = AuthIdentity("erin", "ws-mine", ("researcher",))
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: researcher)
    ctx = _basic_ctx(operation_kind="run.plan")
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.allowed


def test_every_operation_kind_has_an_explicit_role_classification() -> None:
    """Fail-closed invariant: a new `OPERATION_KINDS` member must be classified
    in `_OPERATION_ROLES`, never silently inherit the researcher-inclusive
    mutation grant."""

    assert set(policy.OPERATION_KINDS) == set(policy._OPERATION_ROLES)


# ---------------------------------------------------------------------------
# Audit-health stage (OPM-OQ-6)
# ---------------------------------------------------------------------------


def _unhealthy_probe(_paths: FoundryPaths) -> audit_service.AuditHealth:
    return audit_service.AuditHealth(
        healthy=False,
        last_probe_at="2026-01-01T00:00:00Z",
        last_success_at=None,
        error_detail="simulated",
    )


def _healthy_probe(_paths: FoundryPaths) -> audit_service.AuditHealth:
    return audit_service.AuditHealth(
        healthy=True,
        last_probe_at="2026-01-01T00:00:01Z",
        last_success_at="2026-01-01T00:00:01Z",
        error_detail=None,
    )


def test_audit_unhealthy_blocks_mutating_operation(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A LIVE probe that comes back unhealthy denies the mutating operation.

    NEW-19: this test previously seeded a persisted `get_health_state` row and
    asserted the stage "must deny WITHOUT re-probing" -- i.e. it pinned the
    very latching behaviour NEW-19 identifies as the defect. Rewritten to
    drive the real probe instead; the recovery test below pins the behaviour
    the old assertion made impossible.
    """

    monkeypatch.setattr(audit_service, "health_check", _unhealthy_probe)
    ctx = _basic_ctx(targets=_run_targets())
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "audit_health"
    assert decision.reason_code == "audit_unhealthy"
    assert decision.retryable is True


def test_audit_health_recovers_after_a_failed_probe(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NEW-19 core: `retryable=True` must be ACHIEVABLE.

    Previously the first failed probe latched `healthy=False` into the
    persisted row and the stage never re-probed, so a caller honouring
    `retryable=True` could retry forever and never succeed. A later call must
    now re-probe and pass once the audit store recovers.
    """

    ctx = _basic_ctx(targets=_run_targets())

    monkeypatch.setattr(audit_service, "health_check", _unhealthy_probe)
    first = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert first.denied
    assert first.reason_code == "audit_unhealthy"
    assert first.retryable is True

    # The audit store comes back. The very next call must observe it.
    monkeypatch.setattr(audit_service, "health_check", _healthy_probe)
    second = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert second.allowed, "retryable=True was unachievable -- the failure latched"


def test_audit_health_degradation_after_a_healthy_probe_is_detected(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The symmetric half of the latch: a store that degrades AFTER a healthy
    probe must be caught. The old "probe once, then trust the row forever"
    shape would have kept authorizing indefinitely."""

    ctx = _basic_ctx(targets=_run_targets())

    monkeypatch.setattr(audit_service, "health_check", _healthy_probe)
    assert policy.evaluate_policy(ctx, paths=tmp_foundry).allowed

    monkeypatch.setattr(audit_service, "health_check", _unhealthy_probe)
    degraded = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert degraded.denied, "a store that degraded after a healthy probe was never re-checked"
    assert degraded.reason_code == "audit_unhealthy"


def test_audit_health_does_not_read_the_assume_healthy_persisted_default(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`get_health_state` returns `healthy=True` when no probe has ever run
    ("assume healthy until proven otherwise"). That fail-open default must not
    be reachable from the authorization path at all: even if it reports
    healthy, a failing live probe still denies."""

    monkeypatch.setattr(
        audit_service,
        "get_health_state",
        lambda paths: audit_service.AuditHealth(
            healthy=True, last_probe_at=None, last_success_at=None, error_detail=None
        ),
    )
    monkeypatch.setattr(audit_service, "health_check", _unhealthy_probe)
    ctx = _basic_ctx(targets=_run_targets())
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.reason_code == "audit_unhealthy"


def test_audit_unhealthy_does_not_block_job_status(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(audit_service, "is_healthy_for_exposure", lambda paths: False)
    ctx = _basic_ctx(operation_kind="job.status", targets=(policy.TargetRef("agent_job", "aj_1"),))
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.allowed


def test_audit_health_never_probed_runs_live_probe_and_allows_when_healthy(
    tmp_foundry: FoundryPaths,
) -> None:
    """NEW-3 fix (round 2): replaces
    `test_audit_health_never_probed_does_not_block_mutating_operation`,
    which pinned M6's fail-open (never-probed silently assumed healthy,
    with NO real probe ever run). A pristine workspace now runs a REAL
    `audit_service.health_check` probe on its first mutating call
    (self-heal) -- against `tmp_foundry`'s real, writable sqlite store the
    probe genuinely succeeds, so the operation is still allowed, but for
    the RIGHT reason (a live probe passed), not because never-probed was
    assumed healthy."""

    ctx = _basic_ctx(targets=_run_targets())
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert not (decision.denied and decision.stage == "audit_health")
    # The probe must have actually run and persisted a result -- proves
    # this is a live probe, not the old "never-probed == healthy" fiction.
    state = audit_service.get_health_state(tmp_foundry)
    assert state.last_probe_at is not None
    assert state.healthy is True


def test_audit_health_never_probed_runs_live_probe_and_blocks_when_unhealthy(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """NEW-3 fix (round 2): the other half of the replaced pinning test --
    proves the fail-open is ACTUALLY closed, not merely relocated. On a
    never-probed workspace (`tmp_foundry`, fresh), `_check_audit_health`
    must run a REAL live probe (`audit_service.health_check`) and USE its
    result -- simulated here as a failing probe -- rather than assuming
    healthy. This is the scenario the M6 wontfix's justification claimed
    was unreachable/unnecessary to guard; it is now guarded."""

    def _failing_probe(paths: FoundryPaths) -> audit_service.AuditHealth:
        return audit_service.AuditHealth(
            healthy=False,
            last_probe_at="2026-01-01T00:00:00Z",
            last_success_at=None,
            error_detail="simulated probe failure",
        )

    monkeypatch.setattr(audit_service, "health_check", _failing_probe)
    ctx = _basic_ctx(targets=_run_targets())
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "audit_health"
    assert decision.reason_code == "audit_unhealthy"
    assert decision.retryable is True


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


def test_identity_denied_reserved_strictly_for_missing_identity(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: None)
    missing_identity_decision = policy.evaluate_policy(
        _basic_ctx(targets=_run_targets(), resolved_target_workspaces=(None,)),
        paths=tmp_foundry,
    )
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
    wrong_workspace_decision = policy.evaluate_policy(
        _basic_ctx(targets=_run_targets(), resolved_target_workspaces=("ws-other",)), paths=tmp_foundry
    )
    assert missing_identity_decision.reason_code == "identity_denied"
    assert wrong_workspace_decision.reason_code == "not_found"
    assert missing_identity_decision.reason_code != wrong_workspace_decision.reason_code


def test_build_error_forces_null_identity_fields_for_not_found_regardless_of_caller(
    tmp_foundry: FoundryPaths,
) -> None:
    """NEW-9 fix (round 2): the H6 no-existence-leak test above (and the
    round-1 one it replaced) hard-codes `operation_id=None`,
    `receipt_ref=None` at every call site -- proving H6 holds ONLY when the
    caller cooperates. `build_error` itself must force both to `None` for
    `not_found`, independent of what the caller passes: a caller that
    populates `operation_id` only on the "exists, not yours" branch (and
    leaves it `None` on the genuinely-absent branch) would otherwise
    silently restore the existence oracle H6 closed."""
    decision = policy.PolicyDecision(False, "rbac", "not_found", retryable=False)
    envelope = policy.build_error(
        decision, operation_id="opm_should_be_dropped", receipt_ref="rcpt_should_be_dropped"
    )
    assert envelope["operation_id"] is None
    assert envelope["receipt_ref"] is None

    # Contrast: for every OTHER reason code, build_error still passes the
    # caller's identifiers through -- this is a `not_found`-SPECIFIC guard,
    # not a general suppression.
    other_decision = policy.PolicyDecision(False, "guard", "guard_blocked", retryable=False)
    other_envelope = policy.build_error(
        other_decision, operation_id="opm_keep_me", receipt_ref="rcpt_keep_me"
    )
    assert other_envelope["operation_id"] == "opm_keep_me"
    assert other_envelope["receipt_ref"] == "rcpt_keep_me"


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
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A request that would fail EVERY stage must fail at the FIRST one
    (capability) -- proves the fixed order, not just that each stage works
    in isolation."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: None)
    ctx = _basic_ctx(operation_kind="shell.exec")
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.stage == "capability"
    assert decision.reason_code == "operation_unknown"

    # Fix capability, still fails at rbac (identity missing) before audit/guard/preflight.
    ctx2 = _basic_ctx(operation_kind="swarm.start", targets=())
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


def test_evaluate_policy_internal_error_is_logged_without_leaking_exception_text(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """NEW-13 fix (round 2): `internal_error` was previously completely
    silent (zero telemetry) -- a genuine bug hidden behind a policy denial
    with nothing to page on, AND nothing to distinguish it from a retry
    loop worth investigating. A warning is now logged, but ONLY the failing
    stage and the exception's TYPE NAME -- never `str(exc)`, which could
    embed caller-influenced data (e.g. a value read back out of a
    malformed governance.yaml)."""

    secret_marker = "SIMULATED_SECRET_MARKER_never_logged"

    def _boom(_ctx: Any, *, paths: Any = None) -> Any:
        raise RuntimeError(secret_marker)

    monkeypatch.setattr(governance, "guard_check", _boom)
    ctx = _basic_ctx(targets=_run_targets())
    with caplog.at_level("WARNING", logger="research_foundry.services.operator_mcp_policy"):
        decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.reason_code == "internal_error"
    assert any("guard" in record.message for record in caplog.records)
    assert not any(secret_marker in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# Confirmation lifecycle (OPM-OQ-2/3)
# ---------------------------------------------------------------------------


def test_mint_confirmation_requires_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: None)
    ctx = _basic_ctx()
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


def test_verify_confirmation_revoked_status_denies_non_retryable_not_expired() -> None:
    """NEW-11 fix (round 2): a `status: revoked` record (the schema's third
    non-`issued`/`consumed` status) was previously reported as
    `confirmation_expired` (`retryable=True`, message "request a new
    preflight preview") -- actively inviting a retry on a token that was
    DELIBERATELY revoked, which a new preflight would not fix. Revocation
    now maps to `confirmation_mismatch` (`retryable=False`)."""
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    record = dict(issued.record)
    record["status"] = "revoked"
    verification = policy.verify_confirmation(record, presented_token=issued.token, ctx=ctx)
    assert verification.outcome == "mismatched"
    assert verification.decision.reason_code == "confirmation_mismatch"
    assert verification.decision.retryable is False


@pytest.mark.parametrize(
    "mutate",
    [
        lambda ctx: dataclasses.replace(ctx, idempotency_key="different-key"),
        lambda ctx: dataclasses.replace(ctx, operation_kind="run.extract", targets=_run_targets()),
        lambda ctx: dataclasses.replace(ctx, policy_snapshot_version="policy-order-v2"),
        lambda ctx: dataclasses.replace(ctx, effective_sensitivity="work_sensitive"),
        lambda ctx: dataclasses.replace(ctx, targets=(policy.TargetRef("run", "run_other"),)),
        lambda ctx: _forge_identity(ctx, _IDENTITY_OTHER_WORKSPACE),
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


def test_exact_replay_after_consumption_is_not_an_error_but_is_non_accepting() -> None:
    """NEW-1 fix (round 2): replaces
    `test_exact_replay_after_consumption_is_not_an_error`, which pinned the
    UNSAFE shape (`verification.decision.allowed` was `True` for a replay).
    `outcome == "exact_replay"` remains the non-error SIGNAL a caller uses
    to route to the prior receipt, but `decision` itself is now a real,
    non-retryable denial (`confirmation_replayed`) -- structurally
    indistinguishable from what `authorize_operation` returns for the same
    case (see the C1/NEW-1 tests below). No caller reading only `.decision`
    can mistake a replay for a fresh accept, regardless of which function
    they called."""

    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64)
    assert consumed is not None
    assert consumed["status"] == "consumed"

    verification = policy.verify_confirmation(consumed, presented_token=issued.token, ctx=ctx)
    assert verification.outcome == "exact_replay"
    assert verification.decision.allowed is False
    assert verification.decision.reason_code == "confirmation_replayed"
    assert verification.decision.retryable is False


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
# C1/NEW-1: authorize_operation AND verify_confirmation must never conflate
# exact replay with an execute authorization -- by shape, not docstring.
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

    # verify_confirmation directly: outcome is still correctly "not an
    # error" (NEW-1: but `.decision` itself is now a real, non-accepting
    # denial -- round 1 left this returning `allowed=True`, which is
    # EXACTLY the shape a naive caller following round 1's own docstring
    # instruction to "call verify_confirmation directly" would read as a
    # fresh accept, skipping capability/RBAC/audit-health/guard/preflight).
    direct_verification = policy.verify_confirmation(consumed, presented_token=issued.token, ctx=ctx)
    assert direct_verification.outcome == "exact_replay"
    assert direct_verification.decision.allowed is False
    assert direct_verification.decision.reason_code == "confirmation_replayed"

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

    # NEW-1: the two entry points now agree EXACTLY -- verify_confirmation's
    # own decision for the replay is dataclass-`==`-equal to
    # authorize_operation's. There is no longer a discrepancy a caller
    # could exploit by choosing which function to call.
    assert direct_verification.decision == replay_decision

    # The replay decision is NOT equal to the original accept -- a replay
    # can never be mistaken for it.
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


def test_forged_future_issued_at_does_not_extend_the_ttl_window() -> None:
    """NEW-7 fix (round 2): H4's clamp (`min(expires_at, issued_at + TTL)`)
    defended against a forged far-future `expires_at` but NOT a forged
    far-future `issued_at` -- inflating BOTH operands together previously
    yielded a token effectively valid for as long as the forged
    `issued_at` implied. `moment` is now compared against `issued_at`
    directly: an `issued_at` in the future relative to `now` is always
    expired, in both `verify_confirmation` and `consume_confirmation`."""

    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    record = dict(issued.record)
    forged_issued_at = "3000-01-01T00:00:00Z"
    record["issued_at"] = forged_issued_at
    record["expires_at"] = "3000-01-01T00:05:00Z"  # consistent, still forged

    verification = policy.verify_confirmation(record, presented_token=issued.token, ctx=ctx)
    assert verification.outcome == "expired"
    assert verification.decision.reason_code == "confirmation_expired"

    consumed = policy.consume_confirmation(record, operation_id="opm_" + "a" * 64)
    assert consumed is None


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


def test_consume_confirmation_returns_a_deep_copy_not_a_shared_shallow_one() -> None:
    """NEW-14 hygiene fix (round 2): `dict(record)` (shallow) shares nested
    `actor`/`targets` values with the input record -- mutating the returned
    record's nested structures could previously mutate the original too.
    `consume_confirmation` now deep-copies."""
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64)
    assert consumed is not None
    consumed["actor"]["user_id"] = "mutated"
    consumed["targets"][0]["target_ref"] = "mutated"
    assert issued.record["actor"]["user_id"] != "mutated"
    assert issued.record["targets"][0]["target_ref"] != "mutated"


def test_consume_confirmation_optional_ctx_binding_denies_mismatch() -> None:
    """NEW-12 fix (round 2, hardening): `consume_confirmation` previously
    had NO binding precondition at all -- only `record`/`operation_id`.
    When `ctx` is supplied, it now additionally requires
    `_bindings_match(record, ctx)`."""
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)

    mismatched_ctx = dataclasses.replace(ctx, idempotency_key="a-different-key")
    denied = policy.consume_confirmation(
        issued.record, operation_id="opm_" + "a" * 64, ctx=mismatched_ctx
    )
    assert denied is None

    # Backward compatible: omitting `ctx` (the default) skips this check --
    # P1's own call sites/tests pre-verify bindings via verify_confirmation.
    allowed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64)
    assert allowed is not None

    # And a MATCHING ctx succeeds too.
    fresh = policy.mint_confirmation(ctx)
    matching = policy.consume_confirmation(fresh.record, operation_id="opm_" + "b" * 64, ctx=ctx)
    assert matching is not None
    assert matching["status"] == "consumed"


# ---------------------------------------------------------------------------
# L3: mint_confirmation defensive guards (operation_kind/target_kind).
# ---------------------------------------------------------------------------


def test_mint_confirmation_rejects_unknown_operation_kind() -> None:
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="shell.exec",
        idempotency_key="idem-1",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
    )
    with pytest.raises(ValueError):
        policy.mint_confirmation(ctx)


def test_mint_confirmation_rejects_unknown_target_kind() -> None:
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="run.plan",
        idempotency_key="idem-1",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        targets=(policy.TargetRef("filesystem_path", "/etc/passwd"),),
        resolved_target_workspaces=("ws-mine",),
    )
    with pytest.raises(ValueError):
        policy.mint_confirmation(ctx)


def test_mint_confirmation_unexpected_failure_raises_sanitized_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NEW-8(b) fix (round 2): `mint_confirmation` returns
    `ConfirmationIssued`, not a `PolicyDecision`, so it cannot participate
    in the PolicyDecision-shaped H8 boundary the other three entry points
    use. Any UNEXPECTED exception during minting (distinct from the
    deliberate L3 `ValueError` guards, which stay outside this boundary) is
    now re-raised as a plain `RuntimeError` with NO caller-supplied text --
    the raise-shaped equivalent of the PolicyDecision boundary."""

    ctx = _basic_ctx(targets=_run_targets())
    secret_marker = "SIMULATED_SECRET_MARKER_never_leaked"

    def _boom(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError(secret_marker)

    monkeypatch.setattr(policy.secrets, "token_urlsafe", _boom)
    with pytest.raises(RuntimeError) as excinfo:
        policy.mint_confirmation(ctx)
    assert secret_marker not in str(excinfo.value)


# ---------------------------------------------------------------------------
# M3: _bindings_match identity-None guard (first line, no vacuous match).
# ---------------------------------------------------------------------------


def test_bindings_match_returns_false_when_identity_is_none() -> None:
    ctx = _forge_identity(
        _basic_ctx(targets=_run_targets(), resolved_target_workspaces=(None,)), None
    )
    # A confirmation minted for a REAL identity, presented against a ctx
    # whose identity is None, must never spuriously match via a vacuous
    # {} == {} actor comparison.
    real_ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(real_ctx)
    assert policy._bindings_match(issued.record, ctx) is False


# ---------------------------------------------------------------------------
# L4/NEW-8: canonicalization hardening (allow_nan=False; construction-time
# rejection of non-finite floats and non-Mapping input_payload).
# ---------------------------------------------------------------------------


def test_context_construction_rejects_nan_value() -> None:
    """NEW-8(a) fix (round 2): replaces
    `test_canonical_json_rejects_nan_value`. Round 1's `allow_nan=False`
    fix made `canonical_json()` raise on NaN, but ONLY once called -- the
    `PolicyContext` itself could still be CONSTRUCTED with a NaN payload,
    and `mint_confirmation` (which calls `ctx.canonical_digest()` with no
    exception boundary of its own before the round-2 fix) could then raise
    an uncaught, unbounded `ValueError` outside every H8 boundary. NaN is
    now rejected at `PolicyContext.__post_init__` -- construction itself
    fails, before `canonical_json()`/`mint_confirmation` is ever reached."""

    with pytest.raises(ValueError):
        _basic_ctx(input_payload={"x": float("nan")})


def test_context_construction_rejects_infinite_value() -> None:
    with pytest.raises(ValueError):
        _basic_ctx(input_payload={"x": float("inf")})


def test_context_construction_rejects_non_mapping_input_payload() -> None:
    """NEW-8(b) fix: a bare `str` passes the OLD `_is_json_primitive`
    recursive check (a `str` IS a JSON primitive) but
    `canonical_payload()`'s `dict(self.input_payload)` would then raise,
    uncaught, deep inside `canonical_digest()`. `__post_init__` now
    requires `input_payload` to be an actual `Mapping`, not merely
    JSON-primitive-shaped."""

    with pytest.raises(ValueError):
        _basic_ctx(input_payload="not-a-mapping")  # type: ignore[arg-type]


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


def test_build_error_config_secret_patterns_union_with_builtins_never_replace(
    tmp_foundry: FoundryPaths,
) -> None:
    """NEW-5 fix (round 2): extends the test above, which only asserted
    the CUSTOM pattern fires and never re-checked a BUILT-IN pattern once a
    `config` was supplied. `governance._secret_patterns` previously
    REPLACED the built-in list whenever governance.yaml declared its own
    (narrow) `secret_patterns` -- a workspace with a custom list became
    LESS strict than the no-config default. Config patterns must UNION with
    the built-ins, never replace them."""
    data = load_yaml(tmp_foundry.config / "governance.yaml") or {}
    narrow_custom_pattern = r"WORKSPACE_SECRET_[A-Za-z0-9]+"
    data["secret_patterns"] = [narrow_custom_pattern]  # deliberately narrow -- no built-ins listed
    dump_yaml(data, tmp_foundry.config / "governance.yaml")
    cfg = FoundryConfig(paths=tmp_foundry)

    decision = policy.PolicyDecision(False, "preflight", "preflight_failed", retryable=True)
    builtin_shaped_secret = "sk-ant-" + "x" * 40

    error = policy.build_error(decision, detail=builtin_shaped_secret, config=cfg)
    assert "sk-ant-" not in error.get("detail", ""), (
        "a workspace's narrow custom secret_patterns list must not turn off "
        "built-in secret detection (NEW-5)"
    )


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
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: None)
    produced.add(policy.evaluate_policy(_basic_ctx(), paths=tmp_foundry).reason_code)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _VIEWER_IDENTITY)
    produced.add(policy.evaluate_policy(_basic_ctx(), paths=tmp_foundry).reason_code)
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _IDENTITY)
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
        # NEW-19: the audit-health stage now runs a LIVE probe on every
        # confirmation-requiring call rather than latching a persisted row,
        # so `health_check` is the producer to drive here. (This previously
        # patched `get_health_state` to reach the "already probed, unhealthy"
        # branch -- a branch that no longer exists, because trusting it was
        # the defect.) Patching the probe is also inherently independent of
        # prior probe state, which was the original reason for the detour.
        mp.setattr(audit_service, "health_check", _unhealthy_probe)
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
