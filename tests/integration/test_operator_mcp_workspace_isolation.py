"""Two-identity/two-workspace adversarial matrix through the REGISTERED
server route (research-foundry-operator-mcp-v1 M3, Leg A, OPM-6.3, AC
OPM-2).

**Why through `server.call_tool`, not a hand-built `PolicyContext`.** The
M2 lesson (see `.claude/worknotes/research-foundry-operator-mcp/
m3-implementer-contract.md`, D1's OPM-6.3 scope note) is that defects hid
at the E2E seam: a hand-built `PolicyContext` in a unit test can only prove
`operator_mcp_policy`'s own six-stage order is correct in isolation, never
that the REAL registered tool -- `operation.preflight` mints, the server
persists it, an adapter re-derives `resolved_target_workspaces` from real
on-disk state, `authorize_operation` re-validates -- actually wires those
pieces together the same way for two DIFFERENT local operator identities.
Every test below drives `server.call_tool(...)` directly (via `_call`,
mirroring `test_operator_mcp_preflight_execute_e2e.py`'s own convention),
never a hand-built `PolicyContext`.

**The "two workspaces" model (OPM-OQ-1).** Operator MCP trusts exactly ONE
locally configured operator identity per `foundry.yaml` -- there is no
per-request caller identity. Two workspaces are therefore represented as
TWO SEPARATE `build_server()` calls against the SAME shared `tmp_foundry`
root, with `foundry.yaml`'s `operator_mcp.identity` block rewritten between
them (`_server_as` below) -- exactly the "swap the locally configured
identity, keep the durable store" shape a real single-operator-per-session
deployment would exhibit. A genuinely separate `tmp_foundry` per identity
would trivially pass every wrong-workspace case (two disjoint SQLite
files can never collide) and would prove nothing about workspace
SCOPING within one shared store -- the actual property D5 cares about.

**D5 (safe non-existence).** For each tool, a request from identity X
targeting identity Y's real, existing data must produce a denial envelope
BYTE-COMPARABLE (after stripping the legitimately-varying `occurred_at`
timestamp) to the SAME identity X's request against a syntactically-valid,
never-existing reference -- same `reason_code` (`not_found`), same
`retryable` (`False`), same forced-null `operation_id`/`receipt_ref`, no
`detail` key. Tested in BOTH directions (B against A's data, A against
B's data) across three distinct tools: `job.status` (a read),
`run.extract` (a mutation), and `job.cancel` (a job-lifecycle mutation).

**A fourth tool, `swarm.start`, is also covered.** Building this matrix
originally discovered a real product defect there -- a recurrence of the
`research_stages.py`-documented "F6" existence-leak shape, initially out
of this Leg's file ownership and captured as a `strict=True` `xfail`. A
follow-up work order expanded ownership to include
`src/research_foundry/services/operator_mcp_adapters/swarm_start.py`; it
is now fixed (mirroring `research_stages.py`'s own F6 fix exactly) and
`test_swarm_start_wrong_workspace_is_indistinguishable_from_missing` is a
real, passing, mutation-verified assertion. See the M3 Leg A completion
note's "Fix follow-up" section for the full repro, fix, and
mutation-verify transcript.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

pytest.importorskip("mcp", reason="optional 'mcp' extra not installed (uv sync --extra mcp)")

from research_foundry.auth_identity import AuthIdentity  # noqa: E402
from research_foundry.operator_mcp import server as server_module  # noqa: E402
from research_foundry.paths import FoundryPaths  # noqa: E402
from research_foundry.services import operator_mcp_policy as policy  # noqa: E402
from research_foundry.yamlio import dump_yaml, load_yaml  # noqa: E402

from tests.integration.test_operator_mcp_writeback_preview import _build_run  # noqa: E402

# D4 (public-safe fixtures): synthetic identities/ids only, no owner
# strings, no real run ids, no LAN addresses, no tokens.
_IDENTITY_A = AuthIdentity("alice", "ws-a", ("owner",))
_IDENTITY_B = AuthIdentity("bob", "ws-b", ("owner",))

#: Syntactically-valid-but-never-existing references, matching each
#: target kind's own closed pattern (`operator_mcp_policy._TARGET_REF_PATTERN`
#: for the generic case; `operation_id` additionally matches the receipt
#: schema's `^opm_[a-f0-9]{64}$` shape so it can never be rejected earlier,
#: at capability, for looking malformed -- the comparison this file makes
#: is only meaningful once both cases reach the SAME later stage).
_NEVER_EXISTED_RUN_ID = "run_zzz_never_existed_00000000"
_NEVER_EXISTED_OPERATION_ID = "opm_" + "0" * 64


def _call(server: Any, name: str, arguments: dict[str, Any]) -> Any:
    return asyncio.run(server.call_tool(name, arguments))


def _configure_operator(
    paths: FoundryPaths, *, identity: AuthIdentity, sensitivity_ceiling: str = "client_sensitive"
) -> None:
    """Same shape as `test_operator_mcp_server.py`/
    `test_operator_mcp_preflight_execute_e2e.py`'s own `_configure_operator`
    -- deliberately re-inlined, not imported (their own convention for a
    ~10-line helper)."""

    data: dict[str, Any] = load_yaml(paths.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"]["operator_mcp"] = {
        "identity": {
            "user_id": identity.user_id,
            "workspace_id": identity.workspace_id,
            "roles": list(identity.roles),
        },
        "sensitivity_ceiling": sensitivity_ceiling,
    }
    dump_yaml(data, paths.foundry_yaml)


def _server_as(paths: FoundryPaths, identity: AuthIdentity) -> Any:
    """Rewrite the ONE locally configured operator identity to `identity`
    and build a fresh server over the SAME shared root -- see this module's
    docstring's "two workspaces" section for why this, not two separate
    roots, is the meaningful cross-workspace configuration."""

    _configure_operator(paths, identity=identity)
    return server_module.build_server(paths=paths)


def _envelope(result: Any) -> dict[str, Any]:
    assert result.isError is True, (
        "expected a denial envelope but the call succeeded",
        result.structuredContent,
    )
    return dict(result.structuredContent)


def _assert_safe_nonexistence(foreign_envelope: dict[str, Any], missing_envelope: dict[str, Any]) -> None:
    """D5's core assertion: the two envelopes must be structurally
    identical once the one legitimately-varying field (`occurred_at`, a
    fresh wall-clock timestamp per call) is stripped -- same `reason_code`,
    same `message`, same `retryable`, and both `operation_id`/`receipt_ref`
    forced null with no `detail` key (the SAME `not_found` shape
    `operator_mcp_policy.build_error` freezes for every H6 no-existence-
    leak case)."""

    foreign = dict(foreign_envelope)
    missing = dict(missing_envelope)
    foreign.pop("occurred_at", None)
    missing.pop("occurred_at", None)
    assert foreign == missing, (foreign_envelope, missing_envelope)
    assert foreign["reason_code"] == "not_found"
    assert foreign["retryable"] is False
    assert foreign.get("operation_id") is None
    assert foreign.get("receipt_ref") is None
    assert "detail" not in foreign


def _seed_workspace(paths: FoundryPaths, identity: AuthIdentity) -> dict[str, str]:
    """Real data owned by `identity`: a full run (`_build_run`, via the
    canonical services directly -- not through Operator MCP) plus a REAL,
    durably persisted operator operation (`run.extract`, driven through
    THIS identity's own server -- the ONLY way to get a genuine
    `.rf_state/operator_operations.db` row tagged to this workspace).
    `run.extract` is chosen as the mutation-kind setup call because
    `research_stages.py`'s own module docstring documents that it does
    NOT reproduce the pre-`ctx` existence-leak ordering `swarm_start.py`
    has (see this module's own docstring) -- setup succeeding is itself a
    sanity precondition (`assert ... isError is False`), not a case under
    test."""

    run_id = _build_run(paths, identity=identity, sensitivity="personal")
    server = _server_as(paths, identity)

    # `model_profile` must be spelled out explicitly (not omitted at its
    # default) on BOTH calls: `invoke_extract`'s own `input_payload` dict
    # always includes it (`{"run_id": ..., "model_profile": model_profile}`,
    # defaulted to `"rf_extract_cheap"` when the caller omits it) when
    # execute independently reconstructs `ctx.input_payload` -- an omitted
    # preflight `input_payload` would bind a DIFFERENT canonical digest than
    # execute recomputes, mirroring `test_operator_mcp_preflight_execute_e2e.py`'s
    # own `_run_plan_payload` helper's documented reasoning.
    seed_payload = {"run_id": run_id, "model_profile": "rf_extract_cheap"}

    preflight = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "run.extract",
            "idempotency_key": f"seed-extract-{identity.workspace_id}",
            "effective_sensitivity": "personal",
            "targets": [{"target_kind": "run", "target_ref": run_id}],
            "input_payload": seed_payload,
        },
    )
    assert preflight.isError is False, preflight.structuredContent
    confirmation = preflight.structuredContent["confirmation"]
    assert confirmation is not None

    execute = _call(
        server,
        "run.extract",
        {
            "idempotency_key": f"seed-extract-{identity.workspace_id}",
            "input_payload": seed_payload,
            "confirmation_record": confirmation["record"],
            "presented_token": confirmation["token"],
        },
    )
    assert execute.isError is False, execute.structuredContent
    operation_id = execute.structuredContent["operation_id"]
    assert operation_id, execute.structuredContent

    return {"run_id": run_id, "operation_id": operation_id, "workspace_id": identity.workspace_id}


@pytest.fixture()
def workspace_a_data(tmp_foundry: FoundryPaths) -> dict[str, str]:
    return _seed_workspace(tmp_foundry, _IDENTITY_A)


@pytest.fixture()
def workspace_b_data(tmp_foundry: FoundryPaths) -> dict[str, str]:
    return _seed_workspace(tmp_foundry, _IDENTITY_B)


#: (attacker identity, name of the fixture producing the VICTIM's data) --
#: both directions, per D5.
_CROSS_WORKSPACE_CASES = [
    pytest.param(_IDENTITY_B, "workspace_a_data", id="B-against-A"),
    pytest.param(_IDENTITY_A, "workspace_b_data", id="A-against-B"),
]


# ---------------------------------------------------------------------------
# Tool 1: job.status -- a READ (CONFIRMATION_NOT_REQUIRED_KINDS member).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("attacker, victim_fixture", _CROSS_WORKSPACE_CASES)
def test_job_status_wrong_workspace_is_indistinguishable_from_missing(
    request: pytest.FixtureRequest,
    tmp_foundry: FoundryPaths,
    attacker: AuthIdentity,
    victim_fixture: str,
) -> None:
    victim = request.getfixturevalue(victim_fixture)
    server = _server_as(tmp_foundry, attacker)

    foreign = _call(
        server,
        "job.status",
        {"idempotency_key": "status-foreign", "input_payload": {"operation_id": victim["operation_id"]}},
    )
    missing = _call(
        server,
        "job.status",
        {
            "idempotency_key": "status-missing",
            "input_payload": {"operation_id": _NEVER_EXISTED_OPERATION_ID},
        },
    )
    _assert_safe_nonexistence(_envelope(foreign), _envelope(missing))


# ---------------------------------------------------------------------------
# Tool 2: run.extract -- a MUTATION targeting a "run".
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("attacker, victim_fixture", _CROSS_WORKSPACE_CASES)
def test_run_extract_wrong_workspace_is_indistinguishable_from_missing(
    request: pytest.FixtureRequest,
    tmp_foundry: FoundryPaths,
    attacker: AuthIdentity,
    victim_fixture: str,
) -> None:
    """No confirmation is presented on either call -- `authorize_operation`
    always re-runs `evaluate_policy` (capability -> rbac -> ...) BEFORE it
    ever inspects a confirmation, so the rbac-stage `not_found` denial for
    both the foreign and the missing run is reached identically without
    one, and this test does not need to preflight/mint first."""

    victim = request.getfixturevalue(victim_fixture)
    server = _server_as(tmp_foundry, attacker)

    foreign = _call(
        server,
        "run.extract",
        {"idempotency_key": "extract-foreign", "input_payload": {"run_id": victim["run_id"]}},
    )
    missing = _call(
        server,
        "run.extract",
        {"idempotency_key": "extract-missing", "input_payload": {"run_id": _NEVER_EXISTED_RUN_ID}},
    )
    _assert_safe_nonexistence(_envelope(foreign), _envelope(missing))


# ---------------------------------------------------------------------------
# Tool 3: job.cancel -- a job-lifecycle MUTATION targeting an "agent_job"
# (== an operation_id; see job_lifecycle.py's own module docstring).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("attacker, victim_fixture", _CROSS_WORKSPACE_CASES)
def test_job_cancel_wrong_workspace_is_indistinguishable_from_missing(
    request: pytest.FixtureRequest,
    tmp_foundry: FoundryPaths,
    attacker: AuthIdentity,
    victim_fixture: str,
) -> None:
    victim = request.getfixturevalue(victim_fixture)
    server = _server_as(tmp_foundry, attacker)

    foreign = _call(
        server,
        "job.cancel",
        {"idempotency_key": "cancel-foreign", "input_payload": {"operation_id": victim["operation_id"]}},
    )
    missing = _call(
        server,
        "job.cancel",
        {
            "idempotency_key": "cancel-missing",
            "input_payload": {"operation_id": _NEVER_EXISTED_OPERATION_ID},
        },
    )
    _assert_safe_nonexistence(_envelope(foreign), _envelope(missing))


# ---------------------------------------------------------------------------
# Positive control: same-workspace access to real, existing data must NOT
# get the not_found treatment -- proves the comparison above is measuring
# something real, not a vacuous "every call denies identically" artifact.
# ---------------------------------------------------------------------------


def test_job_status_same_workspace_is_not_treated_as_missing(
    tmp_foundry: FoundryPaths, workspace_a_data: dict[str, str]
) -> None:
    server = _server_as(tmp_foundry, _IDENTITY_A)
    result = _call(
        server,
        "job.status",
        {
            "idempotency_key": "status-own",
            "input_payload": {"operation_id": workspace_a_data["operation_id"]},
        },
    )
    assert result.isError is False, result.structuredContent
    assert result.structuredContent["result"]["operation_id"] == workspace_a_data["operation_id"]


def test_swarm_start_same_workspace_server_route_completes(
    tmp_foundry: FoundryPaths, workspace_a_data: dict[str, str]
) -> None:
    """TERRA-M3-2 (LOW): `swarm.start`'s own foreign/missing comparison
    test proves the DENIAL shape converges, but proves nothing about the
    ACCEPT path -- a regression that made `swarm.start`'s target-workspace
    resolution always resolve to "missing" (denying every call as
    `not_found`) would pass every existing `swarm.start` test in this file
    without a same-workspace positive control. Valid confirmation,
    deterministic/empty adapter set (`adapter_ids: []` -- no real
    discovery-adapter dispatch, no network/subprocess reach, a single
    fast, deterministic completed result since zero actions means
    `run_actions` completes immediately), through the REAL registered
    `operation.preflight` -> execute route.

    Discovered while building this exact test: the real route was
    ADDITIONALLY broken end-to-end (`confirmation_mismatch`, always, even
    for this fully authorized case) because `operation.preflight`'s
    generic tool had no way to supply `profile`/`budget_usd`/
    `timeout_minutes` -- three fields `swarm.start`'s own `invoke` always
    resolves server-side and bakes into its canonical digest, never a
    caller-suppliable parameter. Fixed in `server.py`'s `_preflight_tool`
    (a new swarm.start-specific augmentation block, mirroring the existing
    `writeback.preview` one) and `swarm_start.py` (a new PUBLIC
    `resolve_preflight_governance_inputs` function) -- see the M3 Leg A
    completion note's "Pre-gate fix cycle" section for the full repro."""

    server = _server_as(tmp_foundry, _IDENTITY_A)
    run_id = workspace_a_data["run_id"]

    preflight = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "swarm.start",
            "idempotency_key": "swarm-own-workspace",
            "effective_sensitivity": "personal",
            "targets": [{"target_kind": "run", "target_ref": run_id}],
            "input_payload": {"run_id": run_id, "adapter_ids": []},
        },
    )
    assert preflight.isError is False, preflight.structuredContent
    confirmation = preflight.structuredContent["confirmation"]
    assert confirmation is not None

    execute = _call(
        server,
        "swarm.start",
        {
            "idempotency_key": "swarm-own-workspace",
            "input_payload": {"run_id": run_id, "adapter_ids": []},
            "confirmation_record": confirmation["record"],
            "presented_token": confirmation["token"],
        },
    )
    assert execute.isError is False, execute.structuredContent
    assert execute.structuredContent["ok"] is True
    assert execute.structuredContent["operation_id"]
    assert execute.structuredContent["result"]["status"] == "completed"


# ---------------------------------------------------------------------------
# ICA-M3-1 (MED): every direct tool call omitting a kind-specific required
# `input_payload` key must yield a TYPED, non-retryable `payload_too_large`
# denial -- never a raw TypeError misreported as a generic `internal_error`.
# Enumerated over ALL 13 operation kinds x each kind's own required keys,
# derived LIVE from `server_module._required_input_payload_keys` (the same
# `inspect.signature`-driven mechanism the fix itself uses) -- never a
# hand-typed table that could silently drift from the real fix.
# ---------------------------------------------------------------------------

_REQUIRED_KEYS_BY_KIND: dict[str, tuple[str, ...]] = {
    kind: tuple(sorted(server_module._required_input_payload_keys(kind))) for kind in policy.OPERATION_KINDS
}

_REQUIRED_KEY_OMISSION_CASES = [
    pytest.param(kind, missing_key, id=f"{kind}-missing-{missing_key}")
    for kind in policy.OPERATION_KINDS
    for missing_key in _REQUIRED_KEYS_BY_KIND[kind]
]


def test_required_key_tables_are_non_empty_for_every_kind() -> None:
    """Completeness precondition: every one of the 13 kinds must have at
    least one required key (true today -- `run_id` alone, at minimum, for
    every kind) -- if a future kind's real `invoke*` signature ever made
    EVERY parameter optional, `_REQUIRED_KEY_OMISSION_CASES` would
    silently stop covering it at all, and this assertion is what would
    catch that."""

    assert set(_REQUIRED_KEYS_BY_KIND) == set(policy.OPERATION_KINDS)
    for kind, required in _REQUIRED_KEYS_BY_KIND.items():
        assert required, f"{kind}: no required input_payload keys derived -- suspicious, check by hand"


@pytest.mark.parametrize("kind, missing_key", _REQUIRED_KEY_OMISSION_CASES)
def test_operation_tool_missing_required_key_denies_typed_never_internal_error(
    tmp_foundry: FoundryPaths, kind: str, missing_key: str
) -> None:
    """ICA-M3-1: for every one of the 13 kinds' own required
    `input_payload` keys, a direct tool call (never through
    `operation.preflight`) that omits exactly that one key must deny with
    the typed, non-retryable `payload_too_large` envelope -- never the
    generic `internal_error` a raw `TypeError` from `adapter.invoke(
    **invoke_kwargs)` produced before this fix. Every OTHER required key
    for `kind` is still supplied (with a placeholder value -- irrelevant,
    since this check runs BEFORE `adapter.invoke` is ever called, purely
    on key PRESENCE) so this proves the check operates per-key, not merely
    "any payload smaller than N keys denies"."""

    server = _server_as(tmp_foundry, _IDENTITY_A)
    payload = {key: "placeholder" for key in _REQUIRED_KEYS_BY_KIND[kind] if key != missing_key}

    result = _call(
        server,
        kind,
        {"idempotency_key": f"missing-{missing_key}", "input_payload": payload},
    )
    envelope = _envelope(result)
    assert envelope["reason_code"] == "payload_too_large", (
        f"{kind} omitting {missing_key!r}: expected payload_too_large, got "
        f"{envelope['reason_code']!r} (message: {envelope.get('message')!r})"
    )
    assert envelope["retryable"] is False
    assert envelope["operation_id"] is None


# ---------------------------------------------------------------------------
# FIXED product defect (follow-up work order, orchestrator-adjudicated):
# swarm.start reproduced the F6 existence-leak shape `research_stages.py`'s
# own docstring names and says was fixed elsewhere. File ownership was
# expanded to include `swarm_start.py` (waves complete, no other writer);
# fixed there to mirror `research_stages.py`'s `invoke_extract`/
# `invoke_claim_map`/`invoke_synthesize` exactly -- `evaluate_policy` now
# runs BEFORE the budget/timeout/governance_profile precondition check, so
# a missing run and a foreign-workspace run deny identically at rbac. This
# test previously carried a `strict=True` xfail describing the defect; it
# is now a real, passing assertion (mutation-verified -- see the M3 Leg A
# completion note's "Fix follow-up" section for the revert/restore
# transcript).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("attacker, victim_fixture", _CROSS_WORKSPACE_CASES)
def test_swarm_start_wrong_workspace_is_indistinguishable_from_missing(
    request: pytest.FixtureRequest,
    tmp_foundry: FoundryPaths,
    attacker: AuthIdentity,
    victim_fixture: str,
) -> None:
    """D5 case, now genuinely passing against real code (see the section
    docstring above for the fix)."""

    victim = request.getfixturevalue(victim_fixture)
    server = _server_as(tmp_foundry, attacker)

    foreign = _call(
        server,
        "swarm.start",
        {
            "idempotency_key": "swarm-foreign",
            "input_payload": {"run_id": victim["run_id"], "adapter_ids": []},
        },
    )
    missing = _call(
        server,
        "swarm.start",
        {
            "idempotency_key": "swarm-missing",
            "input_payload": {"run_id": _NEVER_EXISTED_RUN_ID, "adapter_ids": []},
        },
    )
    _assert_safe_nonexistence(_envelope(foreign), _envelope(missing))
