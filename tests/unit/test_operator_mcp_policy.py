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

import copy
import dataclasses
import hashlib
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
#: D2 "wrong actor" case: SAME workspace as `_IDENTITY`, DIFFERENT user_id
#: -- deliberately distinct from `_IDENTITY_OTHER_WORKSPACE`, which differs
#: in BOTH fields at once and therefore cannot, on its own, prove the
#: binding check catches a user_id mismatch independent of a workspace one.
_IDENTITY_SAME_WORKSPACE_DIFFERENT_ACTOR = AuthIdentity("mallory", "ws-mine", ("owner",))

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
# D2 (M3, OPM-6.2): structural zero-effect snapshot/diff harness.
#
# This module's own docstring is explicit that `operator_mcp_policy` mints/
# verifies/consumes confirmations as PURE functions -- "no effect adapter,
# AgentJob attempt, or MCP server exists in this module" and
# `consume_confirmation` "is a PURE function -- it returns a new dict ...
# and touches no disk". The manifest/receipt/job/attempt/confirmation-store
# durable rows D2 requires a snapshot of therefore do not exist AT THIS
# LAYER (they belong to `operator_operation_service.py`, P2's persistence
# owner, exercised by the sibling `test_operator_operation_service.py`
# suite) -- what this module CAN, and does, touch on disk is: (a) the
# `audit_event` log via `audit_service.health_check`'s write-then-read-
# then-DELETE probe (`_check_audit_health`, gating every confirmation-
# requiring evaluation) -- that probe never calls `record_event()`, so a
# denied adversarial attempt must produce ZERO new audit-log entries; and
# (b) `governance.guard_check`'s read of workspace `governance.yaml` (read-
# only, never a write). `_snapshot_stores` below captures BOTH: the full
# audit-event log (proving no durable audit trail is created for a denied
# operation) and a content-hash manifest of every file under the workspace
# root (proving no filesystem artifact -- config, confirmation-adjacent, or
# otherwise -- is created or mutated). The ONE store this module
# legitimately, intentionally, and unconditionally writes on every
# confirmation-requiring evaluation -- the single `audit_health` row the
# health probe upserts (`id=1`, `last_probe_at` advances every call,
# allow or deny) -- is captured SEPARATELY (`_snapshot_audit_health`) and
# deliberately EXCLUDED from `_assert_zero_effect`'s comparison: it is not
# an operation effect (no manifest, no receipt, nothing a caller could
# observe as "this adversarial request did something"), it is a documented
# policy-evaluation side channel that changes identically whether the
# request is ultimately allowed or denied -- see the module docstring's
# "Audit-health is a LIVE, UNCONDITIONAL probe" paragraph. Using it as the
# vacuity-detection POSITIVE CONTROL instead (below) turns this
# by-design exclusion into the proof that the diff mechanism actually
# works, rather than leaving it as an unexplained gap in the comparison.
# ---------------------------------------------------------------------------


def _snapshot_audit_health(paths: FoundryPaths) -> tuple[Any, ...]:
    state = audit_service.get_health_state(paths)
    return (state.healthy, state.last_probe_at, state.last_success_at, state.error_detail)


def _snapshot_stores(paths: FoundryPaths) -> dict[str, Any]:
    """Structural before/after snapshot of every durable store an
    adversarial `operator_mcp_policy` call could conceivably touch, per D2.
    See the section docstring above for what is (audit log, filesystem) and
    is not (the `audit_health` probe row) part of the zero-EFFECT
    comparison `_assert_zero_effect` performs.

    `paths.rbac_db` is excluded from the raw file-hash walk below: it is
    the SAME physical SQLite file `audit_service`'s `audit_event` table AND
    `audit_health` row both live in (`audit_service` imports `rbac_store.
    _connect`) -- the `audit_health` upsert changes this file's on-disk
    bytes (page writes, not merely a logical row) on every confirmation-
    -requiring evaluation regardless of allow/deny, which would otherwise
    make EVERY zero-effect assertion in this file spuriously fail on a
    documented, expected side channel. Its two logically distinct halves
    are captured precisely instead: `audit_events` above (the real,
    durable audit trail -- must never gain an entry) and
    `_snapshot_audit_health` (the excluded, expected-to-change probe row,
    used only by the positive control)."""

    events = audit_service.list_events(paths, limit=10_000)["items"]
    excluded = {paths.rbac_db.resolve()} if paths.rbac_db.exists() else set()
    files: dict[str, str] = {}
    if paths.root.exists():
        for file_path in sorted(paths.root.rglob("*")):
            if not file_path.is_file() or file_path.resolve() in excluded:
                continue
            try:
                digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
            except OSError:
                digest = "<unreadable>"
            files[str(file_path.relative_to(paths.root))] = digest
    return {"audit_events": events, "files": files}


def _assert_zero_effect(before: dict[str, Any], after: dict[str, Any]) -> None:
    """D2: an adversarial (denied) case must leave every durable store this
    module can touch byte-identical -- zero new/changed files, zero new
    audit-log entries. Deliberately does NOT compare `audit_health` -- see
    the section docstring above; `test_audit_health_probe_is_the_positive_control_...`
    below proves that omission is a documented exclusion, not a blind spot
    that would let a REAL effect slip through unnoticed."""

    assert after["files"] == before["files"], (
        "adversarial case produced a filesystem delta -- diff: "
        f"{ {k: v for k, v in after['files'].items() if before['files'].get(k) != v} !r}"
    )
    assert after["audit_events"] == before["audit_events"], (
        "adversarial case produced a durable audit-log entry (a denied "
        "operation must never appear in the audit trail)"
    )


def test_snapshot_diff_mechanism_detects_a_real_effect_positive_control(
    tmp_foundry: FoundryPaths,
) -> None:
    """D2's mandatory positive control: a zero-effect assertion that can
    never fail is vacuous. This proves `_snapshot_stores`/`_assert_zero_effect`
    are NOT that -- `evaluate_policy` for a confirmation-requiring kind
    (`run.plan`, allowed) legitimately writes exactly one thing to disk:
    the `audit_health` row `_check_audit_health`'s live probe upserts on
    EVERY such evaluation (module docstring: "Audit-health is a LIVE,
    UNCONDITIONAL probe"). `_snapshot_audit_health` (excluded from
    `_assert_zero_effect`'s own comparison, by design -- see that
    function's docstring) DOES detect this real, expected change, proving
    the diffing mechanism this file's whole adversarial matrix relies on
    can distinguish "something happened" from "nothing happened" -- it is
    not comparing `None == None` or some other tautology. The files/
    audit-log halves stay at zero delta even for this ALLOWED call
    (`evaluate_policy` mints nothing and writes no audit-log event by
    itself; only `mint_confirmation`+`operator_operation_service`, outside
    this module, would produce a manifest/receipt), which is itself a
    second, independent confirmation that `_assert_zero_effect` measures a
    real, non-trivial property rather than always vacuously passing."""

    ctx = _basic_ctx(targets=_run_targets())
    audit_health_before = _snapshot_audit_health(tmp_foundry)
    stores_before = _snapshot_stores(tmp_foundry)

    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.allowed

    audit_health_after = _snapshot_audit_health(tmp_foundry)
    stores_after = _snapshot_stores(tmp_foundry)

    # The positive control: a REAL, expected effect (the health-probe
    # upsert) that the mechanism must detect.
    assert audit_health_after != audit_health_before, (
        "the audit-health probe did not advance on a confirmation-requiring "
        "evaluation -- either the probe stopped running (a policy-stage "
        "regression) or _snapshot_audit_health stopped observing it (a test-"
        "harness regression); either way this positive control has gone "
        "silent and every zero-effect assertion in this file is now unproven"
    )
    # The by-design exclusions: no OTHER store moved for this allowed,
    # pre-mint evaluation.
    _assert_zero_effect(stores_before, stores_after)


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

    # BLOCK-6 (round 4 gate): the record presented below is minted from the
    # REAL, unforged `ctx` -- so the `authorize_operation` denial asserted
    # here is attributable ONLY to the forged `ctx` it is presented with,
    # not to `mint_confirmation` independently rejecting the forgery (which
    # it also now does -- see `test_mint_confirmation_rejects_a_forged_identity`
    # below, which supersedes this test's prior "mint succeeds regardless"
    # premise for the mint half specifically).
    issued = policy.mint_confirmation(ctx, paths=tmp_foundry)
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


def test_mint_confirmation_rejects_a_forged_identity(
    tmp_foundry: FoundryPaths,
) -> None:
    """BLOCK-6 (round 4 gate): supersedes
    `test_forged_identity_cannot_produce_an_authorized_mint_confirmation`
    (round 3), whose premise -- "mint_confirmation cannot detect the
    forgery on its own" -- was exactly the gap BLOCK-6 closes (see the
    module docstring's "BLOCK-6 adjudication" paragraph for the full
    empirical repro this closes: a forged mint previously let
    `verify_confirmation(ctx=forged)` return `allowed=True` and let
    `consume_confirmation` transition the record with no identity check at
    all -- `authorize_operation` was the ONLY safe entry point).
    `mint_confirmation` now derives the record's `actor` block from a
    FRESH `resolve_operator_identity` call and raises `ValueError` when
    that disagrees with `ctx.identity`, so a forged identity can no longer
    even be MINTED into a schema-valid confirmation record, let alone
    verified or consumed through either of the other two exported
    entry points."""

    ctx = _basic_ctx(targets=_run_targets())
    forged = _forge_identity(ctx, AuthIdentity("mallory", "ws-mine", ("owner",)))

    with pytest.raises(ValueError):
        policy.mint_confirmation(forged, paths=tmp_foundry)


def test_mint_confirmation_never_leaks_a_raw_yaml_exception_on_malformed_config(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R5-BLOCK-2 (round 5 gate): the BLOCK-6 (round 4) fix placed the
    `resolve_operator_identity(paths)` re-derive call OUTSIDE
    `mint_confirmation`'s exception boundary -- a malformed `foundry.yaml`
    therefore propagated a raw `yaml.parser.ParserError`/`yaml.scanner.
    ScannerError` embedding the malformed file's content verbatim,
    reopening NEW-8 in the very function NEW-8 was raised against. This
    bypasses the `_default_operator_identity` autouse fixture's monkeypatch
    (which would mask the real `resolve_operator_identity` call entirely)
    by restoring the REAL function for this test only, then corrupting
    `foundry.yaml` AFTER the ctx has already resolved a valid identity via
    the (still-patched, at ctx-construction time) default -- so the ONLY
    call that hits the real, malformed-YAML-reading code path is
    `mint_confirmation`'s own re-derive."""

    ctx = _basic_ctx(targets=_run_targets())  # identity resolved via the autouse patch
    monkeypatch.setattr(policy, "resolve_operator_identity", _REAL_RESOLVE_OPERATOR_IDENTITY)
    tmp_foundry.foundry_yaml.write_text(
        "foundry:\n  operator_mcp:\n    identity:\n\tbad_indent: [unclosed\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError) as excinfo:
        policy.mint_confirmation(ctx, paths=tmp_foundry)

    assert "internal_error during confirmation minting" in str(excinfo.value)
    assert "bad_indent" not in str(excinfo.value)
    assert "yaml" not in str(excinfo.value).lower()
    assert not isinstance(excinfo.value, (ValueError,)) or type(excinfo.value) is RuntimeError


def test_for_configured_operator_no_longer_accepts_a_config_parameter() -> None:
    """R5-BLOCK-4 (round 5 gate): `PolicyContext.for_configured_operator`
    previously accepted a `config: FoundryConfig | None` parameter, threaded
    to `resolve_operator_identity(paths, config=config)` -- a SEPARATE
    derivation input `_check_identity_and_rbac` and `mint_confirmation`
    could never agree with, since neither accepted it. A ctx built with a
    divergent `config=` then HARD-FAILED `mint_confirmation` with
    `ValueError` even though every individual derivation site was correct
    in isolation -- the parameter itself was the trap. It is removed here
    (not threaded to the other two sites) so the divergent seam cannot
    exist at all; this pins the removal so it cannot silently be re-added
    without a corresponding fix to the other two derivation sites."""

    with pytest.raises(TypeError):
        policy.PolicyContext.for_configured_operator(
            operation_kind="run.plan",
            idempotency_key="idem-1",
            effective_sensitivity="public",
            sensitivity_ceiling="client_sensitive",
            config=FoundryConfig(paths=FoundryPaths.discover()),
        )


def test_mint_confirmation_agrees_with_for_configured_operator_end_to_end(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R5-BLOCK-4 closure evidence (positive path, real derivation, no
    autouse patch): a `ctx` built via `for_configured_operator(paths=...)`
    against a REAL configured identity, then minted with the SAME `paths`,
    must succeed -- the three derivation sites (`for_configured_operator`,
    `_check_identity_and_rbac`, `mint_confirmation`) now all call
    `resolve_operator_identity(paths)` with no `config` override and
    therefore cannot disagree."""

    monkeypatch.setattr(policy, "resolve_operator_identity", _REAL_RESOLVE_OPERATOR_IDENTITY)
    _write_operator_identity(tmp_foundry, user_id="dana", workspace_id="ws-real", roles=["owner"])

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="run.plan",
        idempotency_key="idem-real-1",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        paths=tmp_foundry,
    )
    assert ctx.identity is not None
    assert ctx.identity.user_id == "dana"

    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.allowed

    issued = policy.mint_confirmation(ctx, paths=tmp_foundry)
    assert issued.record["actor"]["user_id"] == "dana"
    assert issued.record["actor"]["workspace_id"] == "ws-real"


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


def test_capability_rejects_oversized_input_payload_by_byte_size(tmp_foundry: FoundryPaths) -> None:
    """NB-1 (round 5, fixed): `_MAX_INPUT_PAYLOAD_PROPERTIES` bounds top-
    level KEY COUNT only -- round 5's empirical repro showed 32 properties x
    300 KB each (9,600,086 bytes total) was ACCEPTED. A single well-under-
    count-limit property can still carry an effectively unbounded string;
    this pins the new total-byte-size cap."""

    ctx = _basic_ctx(input_payload={"blob": "x" * (policy._MAX_INPUT_PAYLOAD_BYTES + 1)})
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "capability"
    assert decision.reason_code == "payload_too_large"


def test_capability_allows_input_payload_under_the_byte_size_cap(tmp_foundry: FoundryPaths) -> None:
    # Leave headroom for the JSON structural characters (quotes/braces/key
    # name) the canonical-JSON encoding of this payload also counts.
    ctx = _basic_ctx(input_payload={"blob": "x" * (policy._MAX_INPUT_PAYLOAD_BYTES - 100)})
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.allowed


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
    """D2 (missing identity): the denial is asserted below AND the durable
    stores this module could touch are proven to have zero delta -- a
    missing identity denies at `rbac`, before the LATER `audit_health`
    stage ever runs, so this is expected to be a true no-op on disk."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: None)
    ctx = _basic_ctx(targets=_run_targets(), resolved_target_workspaces=(None,))
    before = _snapshot_stores(tmp_foundry)
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    after = _snapshot_stores(tmp_foundry)
    assert decision.denied
    assert decision.stage == "rbac"
    assert decision.reason_code == "identity_denied"
    _assert_zero_effect(before, after)


def test_matching_resolved_target_workspace_is_not_denied(tmp_foundry: FoundryPaths) -> None:
    ctx = _basic_ctx(targets=_run_targets(), resolved_target_workspaces=("ws-mine",))
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.allowed


def test_rbac_denies_insufficient_role_for_mutating_kind(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D2 (denial): general RBAC denial, zero-effect asserted."""

    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: _VIEWER_IDENTITY)
    ctx = _basic_ctx()
    before = _snapshot_stores(tmp_foundry)
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    after = _snapshot_stores(tmp_foundry)
    assert decision.denied
    assert decision.stage == "rbac"
    assert decision.reason_code == "rbac_denied"
    _assert_zero_effect(before, after)


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


def test_operation_roles_align_with_rbac_permissions() -> None:
    """Part C (round 5, Karen Adjudication 2): the alignment between
    `_OPERATION_ROLES` and `api.auth.rbac.ROLE_PERMISSIONS` was, until this
    test, ONE PROSE COMMENT (`operator_mcp_policy.py:539`) with ZERO
    mechanical linkage -- NEW-22 (security review round 3) already found TWO
    real privilege escalations in that map by hand. This module deliberately
    does NOT import `api.auth.rbac` at module level (NEW-23, the serve-extra
    import boundary) -- this test imports it locally instead; tests in this
    suite run WITH the `[serve]` extra installed, so that import is safe
    here even though it is forbidden inside `operator_mcp_policy.py` itself.

    Each `operation_kind` is mapped to ONE representative permission string
    that `_OPERATION_ROLES`' role SET for that kind is defined by (e.g. every
    `_MUTATION_ROLES`-classified kind maps to `catalog:update`, one of
    several permissions that set happens to hold identically -- any would
    do; `catalog:update` is simply the one this test's work order named).
    For each kind, the roles `_OPERATION_ROLES` grants must equal EXACTLY
    the roles `rbac.ROLE_PERMISSIONS` grants that permission to -- if either
    map drifts (a role gains/loses the permission in rbac.py, or a kind's
    classification changes here) without updating the other, this fails."""

    from research_foundry.api.auth import rbac

    operation_kind_permissions: dict[str, str] = {
        "run.plan": "catalog:update",
        "swarm.start": "agent_job:launch",
        "job.status": "run:read",
        "job.cancel": "agent_job:launch",
        "job.resume": "agent_job:launch",
        "external_report.import": "catalog:update",
        "source.ingest": "catalog:update",
        "run.extract": "catalog:update",
        "run.claim_map": "catalog:update",
        "run.synthesize": "catalog:update",
        "run.verify": "catalog:update",
        "run.bundle": "catalog:update",
        "writeback.preview": "catalog:update",
    }
    # Every OPERATION_KINDS member must be covered by this drift guard too --
    # an unmapped kind here would silently escape the check below.
    assert set(operation_kind_permissions) == set(policy.OPERATION_KINDS)

    for kind, permission in operation_kind_permissions.items():
        expected_roles = {role for role, perms in rbac.ROLE_PERMISSIONS.items() if permission in perms}
        actual_roles = policy._OPERATION_ROLES[kind]
        assert actual_roles == expected_roles, (
            f"{kind!r}: _OPERATION_ROLES grants {sorted(actual_roles)} but "
            f"rbac.ROLE_PERMISSIONS[*][{permission!r}] grants {sorted(expected_roles)} -- "
            "the two maps have drifted apart"
        )


# ---------------------------------------------------------------------------
# R5-NB-3 / Part B: pin the frozen DUR-1 contract text (module-docstring
# half; the mirrored schema-description half is pinned in
# test_operator_mcp_schemas.py::test_confirmation_schema_pins_the_frozen_dur1_binding_predicate).
# ---------------------------------------------------------------------------


def test_dur1_binding_predicate_is_pinned_in_module_docstring() -> None:
    """R5-NB-3 (round 5, fixed): round 5's mutation sweep found that
    deleting the entire BINDING CHECK clause (b) from the frozen DUR-1 text
    -- in EITHER of its two locations (this module's docstring and the
    confirmation schema's description) -- went completely UNDETECTED (exit
    0, zero failures). No test anywhere pinned this frozen normative prose,
    the exact text P2's closeout is graded against. This asserts the
    REQUIRED PREDICATE CLAUSES remain present in the module docstring --
    deliberately not a byte-for-byte comparison (which would be brittle to
    an ordinary copy-edit that preserves the normative content), so
    deleting a clause (or the compare-and-swap framing entirely) fails this
    test while a harmless rewording does not."""

    doc = policy.__doc__ or ""
    from tests.unit.test_operator_mcp_schemas import _DUR1_REQUIRED_CLAUSES

    for clause in _DUR1_REQUIRED_CLAUSES:
        assert clause in doc, f"DUR-1 predicate clause missing from the module docstring: {clause!r}"


# ---------------------------------------------------------------------------
# Audit-health stage (OPM-OQ-6)
# ---------------------------------------------------------------------------


def _persist_health_row(
    paths: FoundryPaths,
    *,
    healthy: bool,
    last_probe_at: str,
    last_success_at: str | None,
    error_detail: str | None,
) -> None:
    """BLOCK-4 (round 4 gate) helper: write a REAL row into `tmp_foundry`'s
    sqlite `audit_health` table, mirroring exactly what
    `audit_service.health_check` itself persists on a probe. The pre-BLOCK-4
    fakes below returned an `AuditHealth` value WITHOUT persisting it, so
    `get_health_state` always saw a fresh, never-probed row (`last_probe_at
    is None`) regardless of how many times the fake had "run" -- which meant
    a reverted pre-NEW-19 latch (`if get_health_state(...).last_probe_at is
    None: health_check(...)`) re-probed on EVERY call by accident, masking
    the very latch these tests exist to pin. See BLOCK-4 in
    `.claude/findings/research-foundry-operator-mcp-findings.md`."""

    conn = audit_service._connect(paths)
    try:
        audit_service._ensure_schema(conn)
        conn.execute(
            (
                "INSERT OR REPLACE INTO audit_health "
                "(id, healthy, last_probe_at, last_success_at, error_detail) "
                "VALUES (1, ?, ?, ?, ?)"
            ),
            (1 if healthy else 0, last_probe_at, last_success_at, error_detail),
        )
    finally:
        conn.close()


def _unhealthy_probe(paths: FoundryPaths) -> audit_service.AuditHealth:
    """BLOCK-4: PERSISTS its result (unlike the pre-BLOCK-4 version) so a
    reverted latch sees a real, non-`None` `last_probe_at` on the NEXT call."""

    _persist_health_row(
        paths,
        healthy=False,
        last_probe_at="2026-01-01T00:00:00Z",
        last_success_at=None,
        error_detail="simulated",
    )
    return audit_service.AuditHealth(
        healthy=False,
        last_probe_at="2026-01-01T00:00:00Z",
        last_success_at=None,
        error_detail="simulated",
    )


def _healthy_probe(paths: FoundryPaths) -> audit_service.AuditHealth:
    """BLOCK-4: PERSISTS its result -- see `_unhealthy_probe`'s docstring."""

    _persist_health_row(
        paths,
        healthy=True,
        last_probe_at="2026-01-01T00:00:01Z",
        last_success_at="2026-01-01T00:00:01Z",
        error_detail=None,
    )
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

    BLOCK-4 (round 4 gate): the prior version of this test used fakes that
    never persisted a row, so `get_health_state` always saw `last_probe_at
    is None` regardless of how many probes had "run" -- which meant a
    reverted pre-NEW-19 latch re-probed on every call BY ACCIDENT, and this
    test could not distinguish the fix from the defect it exists to pin
    (confirmed by mutation: all four NEW-19 tests passed under the reverted
    code). `_unhealthy_probe`/`_healthy_probe` now persist real state, and a
    call-count spy proves `health_check` genuinely runs on BOTH evaluations
    -- the actual NEW-19 property, per the required-fix note.
    """

    ctx = _basic_ctx(targets=_run_targets())
    call_count = {"n": 0}

    def _spy_unhealthy(paths: FoundryPaths) -> audit_service.AuditHealth:
        call_count["n"] += 1
        return _unhealthy_probe(paths)

    def _spy_healthy(paths: FoundryPaths) -> audit_service.AuditHealth:
        call_count["n"] += 1
        return _healthy_probe(paths)

    monkeypatch.setattr(audit_service, "health_check", _spy_unhealthy)
    first = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert first.denied
    assert first.reason_code == "audit_unhealthy"
    assert first.retryable is True
    assert call_count["n"] == 1

    # The audit store comes back. The very next call must observe it.
    monkeypatch.setattr(audit_service, "health_check", _spy_healthy)
    second = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert second.allowed, "retryable=True was unachievable -- the failure latched"
    assert call_count["n"] == 2, (
        "health_check must run again on the second evaluation, not reuse the "
        "persisted (stale, unhealthy) row from the first call"
    )


def test_audit_health_degradation_after_a_healthy_probe_is_detected(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The symmetric half of the latch: a store that degrades AFTER a healthy
    probe must be caught. The old "probe once, then trust the row forever"
    shape would have kept authorizing indefinitely.

    BLOCK-4: persisting fakes + call-count spy -- see
    `test_audit_health_recovers_after_a_failed_probe`'s docstring for why
    this is required for the closure evidence to be valid."""

    ctx = _basic_ctx(targets=_run_targets())
    call_count = {"n": 0}

    def _spy_healthy(paths: FoundryPaths) -> audit_service.AuditHealth:
        call_count["n"] += 1
        return _healthy_probe(paths)

    def _spy_unhealthy(paths: FoundryPaths) -> audit_service.AuditHealth:
        call_count["n"] += 1
        return _unhealthy_probe(paths)

    monkeypatch.setattr(audit_service, "health_check", _spy_healthy)
    assert policy.evaluate_policy(ctx, paths=tmp_foundry).allowed
    assert call_count["n"] == 1

    monkeypatch.setattr(audit_service, "health_check", _spy_unhealthy)
    degraded = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert degraded.denied, "a store that degraded after a healthy probe was never re-checked"
    assert degraded.reason_code == "audit_unhealthy"
    assert call_count["n"] == 2, (
        "health_check must run again on the second evaluation, not reuse the "
        "persisted (stale, healthy) row from the first call"
    )


def test_audit_health_does_not_read_the_assume_healthy_persisted_default(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The stage must never trust ANY persisted `get_health_state` snapshot
    as a substitute for a live probe -- neither the "never probed, assume
    healthy" default NOR a stale, already-probed-once-and-cached-healthy
    row (the exact shape the NEW-19 latch trusted).

    BLOCK-4 (round 4 gate): the prior version of this test stubbed
    `get_health_state` to return `last_probe_at=None` -- precisely the value
    that ALSO triggers a re-probe under the reverted pre-NEW-19 latch (`if
    last_probe_at is None: health_check(...)`), so it could not distinguish
    the fix from the defect. This version stubs a `get_health_state` that
    reports a PREVIOUSLY-probed, healthy row (`last_probe_at` populated,
    `healthy=True`) -- exactly the shape the reverted latch would trust and
    skip re-probing on -- while the LIVE probe reports unhealthy, and spies
    on call count. Only a genuinely unconditional live probe denies here and
    never even consults `get_health_state`; the reverted latch would allow
    and would call `get_health_state` at least once."""

    call_count = {"get_health_state": 0}

    def _spy_get_health_state(paths: FoundryPaths) -> audit_service.AuditHealth:
        call_count["get_health_state"] += 1
        return audit_service.AuditHealth(
            healthy=True,
            last_probe_at="2026-01-01T00:00:00Z",
            last_success_at="2026-01-01T00:00:00Z",
            error_detail=None,
        )

    monkeypatch.setattr(audit_service, "get_health_state", _spy_get_health_state)
    monkeypatch.setattr(audit_service, "health_check", _unhealthy_probe)
    ctx = _basic_ctx(targets=_run_targets())
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.reason_code == "audit_unhealthy"
    # The fixed stage has zero `get_health_state` call sites (see BLOCK-5 /
    # the module docstring) -- it must not even be consulted.
    assert call_count["get_health_state"] == 0


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


def test_audit_unhealthy_denial_logs_contention_suspected_for_a_lock_shaped_failure(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """NB-9 (round 5, partially mitigated): the probe runs at least twice
    per mint->execute flow (see `_check_audit_health`'s in-code comment),
    so under concurrent callers a transient SQLite write-lock contention can
    surface identically to a genuine store failure. This module cannot
    structurally distinguish them (that would require touching
    `audit_service.py`, out of this fix's file ownership) -- it applies a
    heuristic to the error text's SHAPE only, logged for telemetry, NEVER
    the error text itself (NEW-13 convention). The denial's OUTCOME is
    unchanged either way -- this only pins the added observability."""

    def _contended_probe(paths: FoundryPaths) -> audit_service.AuditHealth:
        return audit_service.AuditHealth(
            healthy=False,
            last_probe_at="2026-01-01T00:00:00Z",
            last_success_at=None,
            error_detail="database is locked",
        )

    monkeypatch.setattr(audit_service, "health_check", _contended_probe)
    ctx = _basic_ctx(targets=_run_targets())
    with caplog.at_level("WARNING", logger="research_foundry.services.operator_mcp_policy"):
        decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.reason_code == "audit_unhealthy"
    assert decision.retryable is True
    assert any("contention_suspected=True" in record.message for record in caplog.records)
    assert not any("database is locked" in record.message for record in caplog.records)


def test_audit_unhealthy_denial_logs_contention_not_suspected_for_a_genuine_failure(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def _broken_probe(paths: FoundryPaths) -> audit_service.AuditHealth:
        return audit_service.AuditHealth(
            healthy=False,
            last_probe_at="2026-01-01T00:00:00Z",
            last_success_at=None,
            error_detail="disk I/O error",
        )

    monkeypatch.setattr(audit_service, "health_check", _broken_probe)
    ctx = _basic_ctx(targets=_run_targets())
    with caplog.at_level("WARNING", logger="research_foundry.services.operator_mcp_policy"):
        decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.reason_code == "audit_unhealthy"
    assert any("contention_suspected=False" in record.message for record in caplog.records)


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


def test_writeback_preview_with_empty_writeback_targets_denies_at_preflight(
    tmp_foundry: FoundryPaths,
) -> None:
    """BLOCK-7 (round 4 gate): a default-constructed `writeback.preview`
    context (`writeback_targets=()`, the field's own default) previously
    sailed through `_check_guard` with NONE of the three block-severity
    `*_writeback_requires_review` rules even able to fire -- they are all
    gated on `GuardContext.writeback_targets` being non-empty. This is the
    SAME omitted-means-skip shape H3 removed from `requested_workspace_id`
    on the mutating plane; `_check_guard` silently reduced to the H7
    ceiling comparison alone for any caller that did not opt in. Preflight
    must now fail closed BEFORE the guard stage is even reached."""

    ctx = _basic_ctx(
        operation_kind="writeback.preview",
        targets=(policy.TargetRef("evidence_bundle", "eb_demo"),),
        effective_sensitivity="work_sensitive",
        # writeback_targets deliberately omitted -- defaults to ().
    )
    decision = policy.evaluate_policy(ctx, paths=tmp_foundry)
    assert decision.denied
    assert decision.stage == "preflight"
    assert decision.reason_code == "preflight_failed"
    assert decision.retryable is True


def test_writeback_preview_guard_review_unreachable_by_omission_pre_block7(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BLOCK-7 empirical repro, isolating the GUARD stage specifically:
    directly probing `_check_guard` (bypassing the now-fixed preflight
    gate above) with the SAME `work_sensitive`+`meatywiki` scenario that
    `test_guard_requires_review_for_work_sensitive_meatywiki_writeback`
    correctly denies -- but with `writeback_targets` empty, exactly as a
    default-constructed context would have reached this stage before
    BLOCK-7. Confirms the underlying `governance.guard_check` behavior the
    preflight fix is closing off: with no writeback target declared, the
    review rule cannot fire and the guard stage passes."""

    ctx = _basic_ctx(
        operation_kind="writeback.preview",
        targets=(policy.TargetRef("evidence_bundle", "eb_demo"),),
        effective_sensitivity="work_sensitive",
    )
    guard_decision = policy._check_guard(ctx, tmp_foundry)
    assert guard_decision.allowed, (
        "the guard stage alone cannot detect the missing writeback target -- "
        "this is exactly why BLOCK-7 gates at preflight instead"
    )


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

    # D2 (wrong workspace): snapshot once, run all three denials, snapshot
    # once more -- proves the whole batch of H6 no-existence-leak cases is
    # collectively a zero-effect no-op, not merely that each individually
    # "returns the right error".
    before = _snapshot_stores(tmp_foundry)
    decisions = [
        policy.evaluate_policy(wrong_workspace_ctx, paths=tmp_foundry),
        policy.evaluate_policy(genuinely_missing_ctx, paths=tmp_foundry),
        policy.evaluate_policy(above_ceiling_ctx, paths=tmp_foundry),
    ]
    after = _snapshot_stores(tmp_foundry)
    _assert_zero_effect(before, after)
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


def test_build_error_forces_null_detail_for_not_found_regardless_of_caller() -> None:
    """BLOCK-8 (round 4 gate): NEW-9 (round 2) forced `operation_id`/
    `receipt_ref` to `None` for `not_found` on the CLOSED-envelope argument
    -- "H6's one-denial-shape guarantee is a property of the envelope this
    function builds, not something a caller can be trusted to preserve by
    convention". `detail` is on the SAME envelope and is subject to the
    IDENTICAL argument, but NEW-9 left it passed through verbatim. A caller
    that attaches a `detail` naming the resource on the "exists, not yours"
    case and omits it on the genuinely-absent case would restore exactly
    the existence oracle H6/NEW-9 closed. `detail` must now be forced to
    absent for `not_found` too, the same as `operation_id`/`receipt_ref`."""

    decision = policy.PolicyDecision(False, "rbac", "not_found", retryable=False)
    envelope = policy.build_error(
        decision,
        operation_id="opm_should_be_dropped",
        receipt_ref="rcpt_should_be_dropped",
        detail="run rn_abc123 is owned by workspace ws_other",
    )
    assert envelope["operation_id"] is None
    assert envelope["receipt_ref"] is None
    assert "detail" not in envelope

    # Contrast: for every OTHER reason code, build_error still passes the
    # caller's detail through (redacted/bounded as usual) -- this is a
    # `not_found`-SPECIFIC guard, not a general suppression.
    other_decision = policy.PolicyDecision(False, "guard", "guard_blocked", retryable=False)
    other_envelope = policy.build_error(other_decision, detail="rule fired for this request")
    assert other_envelope.get("detail") == "rule fired for this request"


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


def test_verify_confirmation_expired_token(tmp_foundry: FoundryPaths) -> None:
    """D2 (expiry): zero-effect proven over the record dict itself (never
    mutated by a failed verification) plus every durable store."""

    ctx = _basic_ctx(targets=_run_targets())
    minted_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    issued = policy.mint_confirmation(ctx, now=minted_at)
    record_before = copy.deepcopy(issued.record)
    later = minted_at + policy.CONFIRMATION_TTL + timedelta(seconds=1)

    before = _snapshot_stores(tmp_foundry)
    verification = policy.verify_confirmation(
        issued.record, presented_token=issued.token, ctx=ctx, now=later
    )
    after = _snapshot_stores(tmp_foundry)

    assert verification.outcome == "expired"
    assert verification.decision.reason_code == "confirmation_expired"
    assert verification.decision.retryable is True
    assert issued.record == record_before, "verify_confirmation must never mutate the record it reads"
    _assert_zero_effect(before, after)


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
        lambda ctx: _forge_identity(ctx, _IDENTITY_SAME_WORKSPACE_DIFFERENT_ACTOR),
        lambda ctx: dataclasses.replace(ctx, input_payload={"changed": True}),
    ],
    ids=[
        "idempotency_key_drift",
        "operation_kind_drift",
        "policy_snapshot_version_drift",
        "effective_sensitivity_drift",
        "target_drift",
        "wrong_actor_and_workspace",
        "wrong_actor_same_workspace",
        "payload_drift",
    ],
)
def test_verify_confirmation_mismatched_bound_field_denies(mutate, tmp_foundry: FoundryPaths) -> None:
    """D2: this single parametrized test covers SIX of the required
    matrix categories in one place -- payload drift, target drift, policy
    drift, sensitivity drift, and (across the two actor-identity cases)
    wrong actor / wrong workspace -- each with an explicit zero-effect
    assertion, not merely a typed-error assertion."""

    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    record_before = copy.deepcopy(issued.record)
    changed_ctx = mutate(ctx)

    before = _snapshot_stores(tmp_foundry)
    verification = policy.verify_confirmation(issued.record, presented_token=issued.token, ctx=changed_ctx)
    after = _snapshot_stores(tmp_foundry)

    assert verification.outcome == "mismatched"
    assert verification.decision.reason_code == "confirmation_mismatch"
    assert verification.decision.retryable is False
    assert issued.record == record_before, "a denied verification must never mutate the record it read"
    _assert_zero_effect(before, after)


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
    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64, ctx=ctx)
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
    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64, ctx=ctx)
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
    """D2 (replay): zero-effect asserted around the SECOND (replay)
    `authorize_operation` call specifically -- the first call is the
    legitimate accept this test needs to set up the replay scenario, so
    only the replay attempt itself is required to be a store no-op."""

    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)

    accepted = policy.authorize_operation(
        ctx, confirmation_record=issued.record, presented_token=issued.token, paths=tmp_foundry
    )
    assert accepted.allowed

    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64, ctx=ctx)
    assert consumed is not None
    consumed_before = copy.deepcopy(consumed)

    # verify_confirmation directly: outcome is still correctly "not an
    # error" (NEW-1: but `.decision` itself is now a real, non-accepting
    # denial -- round 1 left this returning `allowed=True`, which is
    # EXACTLY the shape a naive caller following round 1's own docstring
    # instruction to "call verify_confirmation directly" would read as a
    # fresh accept, skipping capability/RBAC/audit-health/guard/preflight).
    before = _snapshot_stores(tmp_foundry)
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
    after = _snapshot_stores(tmp_foundry)
    assert replay_decision.denied
    assert replay_decision.allowed is False
    assert replay_decision.reason_code == "confirmation_replayed"
    assert replay_decision.retryable is False
    # D2 (replay): neither the direct `verify_confirmation` replay call nor
    # the `authorize_operation` replay call produced any durable-store
    # delta, and neither mutated the already-consumed record it read.
    assert consumed == consumed_before, "a replayed verify/authorize call must never mutate the consumed record"
    _assert_zero_effect(before, after)

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
    consumed = policy.consume_confirmation(
        issued.record, operation_id="opm_" + "a" * 64, ctx=ctx, now=minted_at
    )
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

    consumed = policy.consume_confirmation(record, operation_id="opm_" + "a" * 64, ctx=ctx)
    assert consumed is None


# ---------------------------------------------------------------------------
# H5: consume_confirmation is a guarded compare-and-swap-shaped transition.
# ---------------------------------------------------------------------------


def test_consume_confirmation_refuses_to_rebind_an_already_consumed_record(
    tmp_foundry: FoundryPaths,
) -> None:
    """D2 (atomic token consumption): the SECOND consumption attempt is the
    adversarial case under test -- it must be refused (CAS precondition
    failure) AND leave zero effect: no durable-store delta, and the
    already-consumed record it was handed must come back byte-identical
    (never silently rebound to the second, attacker-supplied operation_id).
    The FIRST consumption is legitimate setup, not part of the assertion."""

    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64, ctx=ctx)
    assert consumed is not None
    assert consumed["consumed_by_operation_id"] == "opm_" + "a" * 64
    consumed_before = copy.deepcopy(consumed)

    # A second consumption attempt against the now-consumed record must be
    # refused (CAS precondition failure), never silently rebound to a new
    # operation_id.
    before = _snapshot_stores(tmp_foundry)
    second = policy.consume_confirmation(consumed, operation_id="opm_" + "b" * 64, ctx=ctx)
    after = _snapshot_stores(tmp_foundry)

    assert second is None
    assert consumed == consumed_before, (
        "a refused (already-consumed) re-consumption must never rebind or otherwise mutate "
        "the record it was handed -- this is the atomic-single-use property DUR-1 freezes"
    )
    _assert_zero_effect(before, after)


def test_consume_confirmation_refuses_expired_record() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    minted_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    issued = policy.mint_confirmation(ctx, now=minted_at)
    later = minted_at + policy.CONFIRMATION_TTL + timedelta(seconds=1)
    result = policy.consume_confirmation(
        issued.record, operation_id="opm_" + "a" * 64, ctx=ctx, now=later
    )
    assert result is None


def test_consume_confirmation_succeeds_for_fresh_issued_record() -> None:
    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64, ctx=ctx)
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
    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64, ctx=ctx)
    assert consumed is not None
    consumed["actor"]["user_id"] = "mutated"
    consumed["targets"][0]["target_ref"] = "mutated"
    assert issued.record["actor"]["user_id"] != "mutated"
    assert issued.record["targets"][0]["target_ref"] != "mutated"


def test_consume_confirmation_ctx_binding_denies_mismatch(tmp_foundry: FoundryPaths) -> None:
    """NEW-12 (round 2, hardening) added `consume_confirmation`'s binding
    check (`_bindings_match(record, ctx)`) but left `ctx` OPTIONAL --
    BLOCK-9 (round 4 gate) made it REQUIRED, folding the binding predicate
    into the frozen DUR-1 compare-and-swap text. This test now pins BOTH
    halves: a mismatched `ctx` denies, and `ctx` is no longer omittable at
    all (a `TypeError`, not a silent skip). D2 (atomic token consumption,
    binding variant): the mismatched-`ctx` denial is a store no-op and
    never mutates the still-`issued` record."""

    ctx = _basic_ctx(targets=_run_targets())
    issued = policy.mint_confirmation(ctx)
    record_before = copy.deepcopy(issued.record)

    mismatched_ctx = dataclasses.replace(ctx, idempotency_key="a-different-key")
    before = _snapshot_stores(tmp_foundry)
    denied = policy.consume_confirmation(
        issued.record, operation_id="opm_" + "a" * 64, ctx=mismatched_ctx
    )
    after = _snapshot_stores(tmp_foundry)
    assert denied is None
    assert issued.record == record_before, "a binding-mismatch denial must never mutate the still-issued record"
    _assert_zero_effect(before, after)

    # BLOCK-9: `ctx` is a REQUIRED keyword argument -- omitting it is a
    # TypeError, not a silent "skip the binding check" default.
    with pytest.raises(TypeError):
        policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64)  # type: ignore[call-arg]

    # A MATCHING ctx succeeds -- proves the denial above was a genuine
    # binding check, not an unconditionally-broken consumption path.
    matching = policy.consume_confirmation(issued.record, operation_id="opm_" + "b" * 64, ctx=ctx)
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


def test_build_error_scrubs_bare_path_shaped_detail_with_no_traceback_framing() -> None:
    """BLOCK-1 (round 4 gate): NEW-21's guard (`_TRACEBACK_LIKE`) only ever
    matched traceback/stack-frame shapes. `detail`'s natural producer is
    `str(exc)`, and a filesystem-related exception's message embeds an
    absolute path with NO traceback framing at all -- empirically, prior to
    this fix, `build_error(detail=str(OSError(...)))` emitted the path
    VERBATIM (the receipt schema's sibling `build_audit_delivery` producer
    showed the identical leak). `_redact_and_bound` now detects
    `_PATH_LIKE` too and replaces the WHOLE string, not just the matched
    span."""

    decision = policy.PolicyDecision(False, "preflight", "internal_error", retryable=False)
    raw = str(
        OSError(2, "No such file or directory", "/Users/alice/.config/research-foundry/serve.env")
    )
    assert "/Users/alice" in raw, "precondition: the raw exception text really embeds a path"

    error = policy.build_error(decision, detail=raw)
    produced_detail = error.get("detail", "")
    assert "/Users/alice" not in produced_detail
    assert "serve.env" not in produced_detail

    raw_permission = str(PermissionError(13, "Permission denied", "/home/bob/.ssh/id_ed25519"))
    error_permission = policy.build_error(decision, detail=raw_permission)
    produced_permission_detail = error_permission.get("detail", "")
    assert "/home/bob" not in produced_permission_detail
    assert "id_ed25519" not in produced_permission_detail


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
    consumed = policy.consume_confirmation(issued.record, operation_id="opm_" + "a" * 64, ctx=ctx)
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


def test_resolve_operator_identity_fails_closed_on_malformed_config(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R5-BLOCK-2: a malformed `foundry.yaml` must NOT propagate a raw parser
    exception carrying the file's content out of this function.

    `resolve_operator_identity` is public in `__all__` and is called DIRECTLY by
    `PolicyContext.for_configured_operator` and `mint_confirmation`, so a raw
    raise here reopened NEW-8 (no caller-influenced data in an exception raised
    outside an H8 boundary) on all three paths. `evaluate_policy` happened to
    catch it; the others did not. Fail closed to `None` (deny) instead.
    """

    root = tmp_path / "fdry"
    root.mkdir()
    # Invalid YAML (unclosed flow sequence) with a distinctive secret alongside it.
    (root / "foundry.yaml").write_text(
        "foundry:\n  operator_mcp:\n   identity: [unclosed\n  SUPERSECRET_MARKER: leaked\n"
    )
    paths = FoundryPaths(root=root)

    real_resolve = _REAL_RESOLVE_OPERATOR_IDENTITY
    assert real_resolve(paths) is None, "malformed config must resolve to None (deny)"

    # Bypass the module-wide `_default_operator_identity` autouse patch (NB-7)
    # so the factory exercises REAL derivation against the malformed config
    # rather than the fixture's canned identity.
    monkeypatch.setattr(policy, "resolve_operator_identity", real_resolve)

    # And the same must hold through the two direct callers.
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind="run.plan",
        idempotency_key="k",
        effective_sensitivity="public",
        sensitivity_ceiling="client_sensitive",
        paths=paths,
    )
    assert ctx.identity is None

    decision = policy.evaluate_policy(ctx, paths=paths)
    assert decision.denied
    assert decision.reason_code in {"identity_denied", "internal_error"}
