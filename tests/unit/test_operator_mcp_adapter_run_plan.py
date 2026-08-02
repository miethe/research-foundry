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

from pathlib import Path
from typing import Any, Callable

import pytest

from research_foundry import ids
from research_foundry.auth_identity import AuthIdentity
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_adapters as adapters_pkg
from research_foundry.services import operator_mcp_policy as policy
import research_foundry.services.planning as planning_module
from research_foundry.services.operator_mcp_adapters import run_plan
from research_foundry.services.operator_operation_service import OperatorOperationService
from research_foundry.yamlio import dump_yaml, load_yaml

from tests.test_planning import _make_intent
from tests.unit.test_operator_mcp_policy import _default_operator_identity  # noqa: F401

# ---------------------------------------------------------------------------
# H7 defect fix (this task): every P3 adapter now resolves
# `sensitivity_ceiling` structurally via `operator_mcp_adapters.
# resolve_local_sensitivity_ceiling` instead of accepting it as a caller-
# supplied parameter (see that function's own docstring in
# `operator_mcp_adapters/__init__.py` for the full defect).
#
# **P3 hardening pass, reviewer's fixture recommendation.** This autouse
# fixture used to `monkeypatch.setattr(adapters_pkg,
# "resolve_local_sensitivity_ceiling", lambda *a, **kw: "client_sensitive")`
# -- discarding the double's own `paths` argument entirely. That kept the
# suite green in a configuration NO real deployment has (the resolver
# permanently replaced, never actually exercised against a real
# `foundry.yaml` for the vast majority of this module's tests), which is
# precisely what let the HIGH-2 sibling defect (job_lifecycle.py's three
# `job.*` adapters hardcoding `effective_sensitivity` to the strictest
# label) go unnoticed by every reviewer who read a green run against this
# same masking pattern. Fixed: this fixture now WRITES the ceiling key into
# `tmp_foundry`'s REAL `foundry.yaml` and lets every PRE-EXISTING test in
# this module exercise the REAL `resolve_local_sensitivity_ceiling`
# implementation end to end (paths threaded correctly or the write is never
# seen -- this ALSO closes HIGH-1's "unprotected `paths` argument"
# unit-level gap for the common/default path, not merely the explicit
# negative-ceiling tests below). The negative fixture below (`test_invoke_
# denies_above_ceiling_...`) still re-patches the resolver function itself
# (via `_recording_ceiling`, HIGH-1 fix) to a LOWER ceiling, since that test
# needs a value LOWER than this fixture's own default and re-patching after
# this fixture already ran is the simplest way to override it per-test.
#
# The three `resolve_local_sensitivity_ceiling` direct unit tests
# immediately below this fixture's own definition each build their OWN
# ISOLATED `FoundryPaths` (a fresh `tmp_path`-rooted directory, NOT the
# shared `tmp_foundry` this fixture also writes into) specifically so this
# fixture's write can never pollute their own "unconfigured" assertion --
# see `test_resolve_local_sensitivity_ceiling_returns_public_when_
# unconfigured`'s own docstring below for why.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _default_sensitivity_ceiling(tmp_foundry: FoundryPaths) -> None:
    data: dict[str, Any] = load_yaml(tmp_foundry.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"].setdefault("operator_mcp", {})
    data["foundry"]["operator_mcp"]["sensitivity_ceiling"] = "client_sensitive"
    dump_yaml(data, tmp_foundry.foundry_yaml)


def _recording_ceiling(value: str) -> tuple[Callable[..., str], list[FoundryPaths | None]]:
    """Test helper (P3 hardening pass, HIGH-1 defect fix): builds a
    `resolve_local_sensitivity_ceiling`-shaped monkeypatch double that
    RECORDS its `paths` argument instead of discarding it.

    A `lambda *a, **kw: ...`-shaped double structurally CANNOT prove the
    real `invoke*` call site threads `paths` through to the resolver
    correctly -- three mutants survive all package tests with such a
    double: an `invoke*` call site dropping the `paths=resolved_paths`
    argument entirely, at ONE of the five real call sites (`run_plan.
    invoke`, `swarm_start.invoke`, `job_lifecycle.invoke_status`/
    `invoke_cancel`/`invoke_resume`), at ALL FIVE, or substituting
    `FoundryPaths.discover()` for it -- because the discarding double
    returns the SAME configured value regardless of what (if anything) it
    was called with. Returns `(double, seen)`; callers assert
    `seen == [<the paths value the real call site SHOULD have passed>,
    ...]` (one entry per `invoke*`/`invoke_status`/etc. call under test)
    after exercising the call under test."""

    seen: list[FoundryPaths | None] = []

    def _double(paths: FoundryPaths | None = None) -> str:
        seen.append(paths)
        return value

    return _double, seen


# Captured at import time, BEFORE `_default_sensitivity_ceiling` above ever
# runs -- mirrors `test_operator_mcp_policy.py`'s own
# `_REAL_RESOLVE_OPERATOR_IDENTITY` convention -- lets the direct unit tests
# below exercise the REAL `resolve_local_sensitivity_ceiling` implementation,
# independent of whatever `foundry.yaml` state any given test's own
# `FoundryPaths` carries.
_REAL_RESOLVE_LOCAL_SENSITIVITY_CEILING = adapters_pkg.resolve_local_sensitivity_ceiling


# ---------------------------------------------------------------------------
# `operator_mcp_adapters.resolve_local_sensitivity_ceiling` direct unit
# tests (H7 defect fix) -- the producer this task's fix relies on. Every
# adapter's own above-ceiling test elsewhere in this file/suite monkeypatches
# this function directly and therefore never exercises ITS OWN fail-closed
# default; these tests close that gap.
# ---------------------------------------------------------------------------


def test_resolve_local_sensitivity_ceiling_returns_public_when_unconfigured(
    tmp_path: Path,
) -> None:
    """Uses an ISOLATED `FoundryPaths` (NOT the shared `tmp_foundry`
    fixture) because `_default_sensitivity_ceiling` (this module's own
    autouse fixture, reviewer's fixture recommendation) now WRITES a
    configured `sensitivity_ceiling` into `tmp_foundry`'s real
    `foundry.yaml` for every other test in this module -- this test
    specifically needs a genuinely UNCONFIGURED `foundry.yaml` to prove the
    resolver's own fail-closed default, so it must not share that
    instance."""

    root = tmp_path / "fdry_unconfigured"
    root.mkdir(exist_ok=True)
    (root / "foundry.yaml").write_text("foundry:\n  owner: Test\n")
    paths = FoundryPaths(root=root)

    assert _REAL_RESOLVE_LOCAL_SENSITIVITY_CEILING(paths) == "public"


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
    root.mkdir(exist_ok=True)
    (root / "foundry.yaml").write_text(
        "foundry:\n  operator_mcp:\n   sensitivity_ceiling: [unclosed\n"
    )
    paths = _FoundryPaths(root=root)

    assert _REAL_RESOLVE_LOCAL_SENSITIVITY_CEILING(paths) == "public"


def test_resolve_local_sensitivity_ceiling_fails_closed_when_foundry_block_is_not_a_dict(
    tmp_path: Any,
) -> None:
    """MUTATION-TESTED GUARD (P3 hardening pass, MEDIUM-4 defect fix): a
    `foundry.yaml` whose top-level `foundry:` value is a non-Mapping (a
    scalar, here a plain string) must NOT crash this function. Removing
    the `isinstance(foundry_block, dict)` guard (`operator_mcp_adapters/
    __init__.py`) fails NO OTHER test in this suite -- `FoundryConfig.
    foundry`'s own `data.get("foundry", data)` happily returns a bare `str`
    for `foundry: hello`, no exception raised inside `.foundry` itself, so
    without the guard `foundry_block.get(_CEILING_CONFIG_SECTION)` would
    raise a raw `AttributeError` ('str' object has no attribute 'get')
    AFTER this function's own `try` has already closed -- crossing this
    function's public (`__all__`-listed), documented "Never raises"
    boundary raw. This is the load-bearing, previously-untested guard the
    P3 implementer contract's security lens flagged."""

    from research_foundry.paths import FoundryPaths as _FoundryPaths

    root = tmp_path / "fdry_nondict_foundry_block"
    root.mkdir(exist_ok=True)
    (root / "foundry.yaml").write_text("foundry: hello\n")
    paths = _FoundryPaths(root=root)

    assert _REAL_RESOLVE_LOCAL_SENSITIVITY_CEILING(paths) == "public"


def test_resolve_local_sensitivity_ceiling_fails_closed_when_discover_itself_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MUTATION-TESTED GUARD (P3 hardening pass, MEDIUM-3 defect fix): calls
    the REAL resolver with `paths=None` (forcing its own internal
    `FoundryPaths.discover()` fallback) while `FoundryPaths.discover` is
    patched to raise -- proving that call now happens INSIDE this
    function's own `try` block (moved there by the MEDIUM-3 fix) rather
    than before it. Before the fix, this raise crossed this function's
    public, documented "Never raises" boundary raw; the caller would see an
    uncaught exception instead of a bounded `"public"` fail-closed
    return -- exactly the class of defect `resolve_operator_identity`'s own
    R5-BLOCK-2 fix (`operator_mcp_policy.py`) already closed for the
    sibling identity-resolution primitive."""

    from research_foundry.paths import FoundryPaths as _FoundryPaths

    def _raise_on_discover() -> "_FoundryPaths":
        raise RuntimeError("simulated: cwd deleted / home unresolvable")

    monkeypatch.setattr(_FoundryPaths, "discover", staticmethod(_raise_on_discover))

    assert _REAL_RESOLVE_LOCAL_SENSITIVITY_CEILING(None) == "public"

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


def test_invoke_exact_replay_recovers_canonical_refs_via_effect_receipt(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """P3-F3 fix: on an exact replay of an already-terminal `run.plan`
    operation, `_build_result` no longer returns the bounded
    `"canonical_refs_available": False` partial -- it recovers the SAME
    canonical refs the first run produced from the durable `effect_receipt`
    (via the new `OperatorReceiptService.load_effect_receipt` reader) and
    `run.yaml`.

    Drives a REAL first run through the adapter (uninstrumented -- unlike
    `test_invoke_result_matches_direct_plan_run_call`, this test does not
    need to spy on `planning.plan_run`, only on the adapter's OWN bounded
    result), then re-presents a FRESH confirmation for the SAME
    `idempotency_key` (the `test_fresh_confirmation_same_idempotency_key_
    and_digest_is_exact_replay` shape from `test_operator_operation_
    service.py`, exercised through the adapter's own `invoke()` surface) --
    `consume_and_create_operation` resolves this to `"exact_replay"`,
    `run_or_replay` never re-invokes the `ActionSpec.run()` closure, and
    `_build_result` must recover the refs from durable state alone.
    """

    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)

    identity = AuthIdentity("alice", "ws-mine", ("owner",))
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    effective_sensitivity = policy.resolve_effective_sensitivity(
        run_plan._resolve_intent_sensitivity(intent_id, tmp_foundry)
    )
    op_service = OperatorOperationService(tmp_foundry)
    idempotency_key = "idem-exact-replay-refs"

    def _mint() -> Any:
        ctx = policy.PolicyContext.for_configured_operator(
            operation_kind=run_plan.OPERATION_KIND,
            idempotency_key=idempotency_key,
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
        issued = policy.mint_confirmation(ctx, now=ids.now())
        op_service.record_confirmation(issued.record)
        return issued

    issued_first = _mint()
    first = run_plan.invoke(
        intent_id=intent_id,
        idempotency_key=idempotency_key,
        confirmation_record=issued_first.record,
        presented_token=issued_first.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )
    assert first.ok is True, first.error
    assert first.result is not None
    assert first.result["canonical_refs_available"] is True
    assert "replayed" not in first.result

    # A FRESH confirmation for the SAME idempotency_key/canonical digest --
    # `consume_and_create_operation` resolves this to the pre-existing
    # operation ("exact_replay"), so `run_or_replay` takes its fast path
    # and `ActionSpec.run()` (and therefore `captured` inside `invoke()`)
    # is never touched a second time.
    issued_second = _mint()
    second = run_plan.invoke(
        intent_id=intent_id,
        idempotency_key=idempotency_key,
        confirmation_record=issued_second.record,
        presented_token=issued_second.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )
    assert second.ok is True, second.error
    assert second.result is not None
    assert second.operation_id == first.operation_id

    assert second.result["replayed"] is True
    assert second.result["canonical_refs_available"] is True
    for field in (
        "status",
        "run_id",
        "brief_id",
        "swarm_id",
        "routing_id",
        "run_dir",
        "brief_path",
        "swarm_path",
        "routing_path",
        "evidence_plan_ref",
    ):
        assert second.result[field] == first.result[field], field


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

    # HIGH-1 fix: a recording double, not a discarding `lambda *a, **kw:`
    # -- proves `invoke()`'s own call site threads its resolved `paths`
    # through to `resolve_local_sensitivity_ceiling`, not merely that SOME
    # ceiling value comes back.
    ceiling_double, ceiling_calls = _recording_ceiling("public")
    monkeypatch.setattr(adapters_pkg, "resolve_local_sensitivity_ceiling", ceiling_double)

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

    # HIGH-1 fix, direct proof: `resolve_local_sensitivity_ceiling` was
    # called with the REAL `paths` value (`tmp_foundry`) both times `invoke()`
    # ran above -- if `invoke()`'s own call site ever dropped its
    # `paths=resolved_paths` argument (the exact mutant class this guards
    # against), the double would have recorded `[None, None]` instead.
    assert ceiling_calls == [tmp_foundry, tmp_foundry]


# ---------------------------------------------------------------------------
# M2 fix cycle 1, F2.1 (TERRA-3): retrieval_limits must be bound into the
# canonical digest, exactly like every other keyword `_run()` forwards to
# `planning.plan_run`. Before this fix, a confirmation minted with one
# retrieval_limits value (including "unset") could be replayed at execute
# time with a DIFFERENT retrieval_limits value -- the same canonical digest
# either way, since the field was silently absent from `input_payload`.
# ---------------------------------------------------------------------------


def test_invoke_retrieval_limits_bound_into_canonical_digest_confirmation_mismatch(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A confirmation minted for `retrieval_limits=None` (the caller's own
    `PolicyContext` never mentions the key at all -- the same shape a caller
    who never supplies `retrieval_limits` produces) must NOT authorize an
    execute call that supplies a REAL, non-empty `retrieval_limits` mapping.
    `run_plan.invoke()` recomputes its own canonical digest from whatever
    `retrieval_limits` the live call actually supplies (mirrors every other
    F2.1-style optional in this module); a mismatched value must therefore
    deny with `confirmation_mismatch` at the confirmation stage, and
    `planning.plan_run` must never be called for that denied attempt --
    TERRA-3's own "valid confirmation reused with changed retrieval limits"
    scenario, closed."""

    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)
    identity = AuthIdentity("alice", "ws-mine", ("owner",))
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    def _must_not_run(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "plan_run must never be called for a request whose retrieval_limits "
            "does not match the confirmation's own canonical digest"
        )

    monkeypatch.setattr(planning_module, "plan_run", _must_not_run)

    effective_sensitivity = policy.resolve_effective_sensitivity(
        run_plan._resolve_intent_sensitivity(intent_id, tmp_foundry)
    )
    # Mint against retrieval_limits=None (omitted) -- the SAME input_payload
    # shape `run_plan.invoke()` itself builds when the caller never supplies
    # retrieval_limits (the None-valued optional is dropped, see invoke()'s
    # own comment on that pattern).
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=run_plan.OPERATION_KIND,
        idempotency_key="idem-retrieval-limits-mismatch",
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

    # Present the SAME confirmation, but now supply a REAL retrieval_limits
    # mapping the mint-time request never declared.
    result = run_plan.invoke(
        intent_id=intent_id,
        idempotency_key="idem-retrieval-limits-mismatch",
        confirmation_record=issued.record,
        presented_token=issued.token,
        retrieval_limits={"max_questions": 999},
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is False
    assert result.result is None
    assert result.error is not None
    assert result.error["reason_code"] == "confirmation_mismatch"
    assert result.operation_id is None


def test_invoke_retrieval_limits_reaches_plan_run_when_confirmation_matches(
    tmp_foundry: FoundryPaths, sample_idea_text: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The positive counterpart: a confirmation minted WITH the real
    `retrieval_limits` value authorizes an execute call presenting that SAME
    value, and `planning.plan_run` receives it unchanged."""

    intent_id, _ = _make_intent(sample_idea_text, sensitivity="personal", tmp_foundry=tmp_foundry)
    identity = AuthIdentity("alice", "ws-mine", ("owner",))
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    captured_kwargs: list[dict[str, Any]] = []
    real_plan_run = planning_module.plan_run

    def _spy_plan_run(*args: Any, **kwargs: Any) -> Any:
        captured_kwargs.append(kwargs)
        return real_plan_run(*args, **kwargs)

    monkeypatch.setattr(planning_module, "plan_run", _spy_plan_run)

    effective_sensitivity = policy.resolve_effective_sensitivity(
        run_plan._resolve_intent_sensitivity(intent_id, tmp_foundry)
    )
    retrieval_limits = {"max_questions": 7, "page_size": 3}
    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=run_plan.OPERATION_KIND,
        idempotency_key="idem-retrieval-limits-match",
        effective_sensitivity=effective_sensitivity,
        sensitivity_ceiling="client_sensitive",
        input_payload={
            "intent_id": intent_id,
            "depth": "standard",
            "audience": "technical",
            "max_cost_usd": 5.0,
            "max_runtime_minutes": 60,
            "freshness_days": 180,
            "retrieval_limits": dict(retrieval_limits),
        },
        paths=tmp_foundry,
    )
    op_service = OperatorOperationService(tmp_foundry)
    issued = policy.mint_confirmation(ctx, now=ids.now())
    op_service.record_confirmation(issued.record)

    result = run_plan.invoke(
        intent_id=intent_id,
        idempotency_key="idem-retrieval-limits-match",
        confirmation_record=issued.record,
        presented_token=issued.token,
        retrieval_limits=retrieval_limits,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert result.ok is True, result.error
    assert len(captured_kwargs) == 1
    assert captured_kwargs[0]["retrieval_limits"] == retrieval_limits


# ---------------------------------------------------------------------------
# M2 fix cycle 2 -- path-containment sweep: intent_id's own unbounded escape
# through `planning.load_intent` (a NEW instance found beyond packet_dir,
# same severity class: `paths.intents_active / f"{intent_id}.yaml"` is an
# f-string join, so an absolute-path-shaped intent_id fully escapes it, and
# intent_id was NEVER validated by any policy-layer pattern at all).
# ---------------------------------------------------------------------------


def test_resolve_intent_sensitivity_denies_absolute_path_escape_before_read(
    tmp_foundry: FoundryPaths, tmp_path: Path,
) -> None:
    """Direct unit proof: an absolute-path-shaped `intent_id` resolves to
    `None` (the SAME fail-closed sentinel a genuinely missing intent gets)
    without `planning.load_intent` ever being reached.

    MUTATION NOTE: a real, well-formed intent YAML (`governance.sensitivity:
    public`) is planted AT the escape target so an UNGUARDED read would
    return a REAL, non-`None` value -- a bare "resolves to None" assertion
    against a target that genuinely has nothing there (e.g. `/etc/passwd.
    yaml`, which never exists) would pass vacuously even with the guard
    removed. `tmp_path` (writable, NOT `/etc`) stands in for "anywhere the
    absolute-path escape can reach"; the escape MECHANISM under test
    (pathlib's `Path.__truediv__` discarding the left operand for an
    absolute right-hand side) is identical regardless of which absolute
    target is used."""

    evil_target = tmp_path / "evil_intent"
    (tmp_path / "evil_intent.yaml").write_text(
        "governance:\n  sensitivity: public\n", encoding="utf-8"
    )

    result = run_plan._resolve_intent_sensitivity(str(evil_target), tmp_foundry)
    assert result is None


def test_resolve_intent_sensitivity_denies_traversal_escape_before_read(
    tmp_foundry: FoundryPaths,
) -> None:
    """MUTATION NOTE: a real intent YAML is planted at `paths.intents/
    evil_intent.yaml` -- what `paths.intents_active / "../evil_intent.yaml"`
    resolves to -- so an unguarded read returns a REAL, non-`None` value."""

    tmp_foundry.intents.mkdir(parents=True, exist_ok=True)
    (tmp_foundry.intents / "evil_intent.yaml").write_text(
        "governance:\n  sensitivity: public\n", encoding="utf-8"
    )

    result = run_plan._resolve_intent_sensitivity("../evil_intent", tmp_foundry)
    assert result is None


def test_invoke_denies_malicious_intent_id_even_under_a_permissive_ceiling(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The residual-exposure closure: even with the LOOSEST possible ceiling
    (`client_sensitive`, which would admit the strictest-sensitivity label a
    rejected `intent_id` resolves to, so the guard stage does NOT deny), a
    malicious `intent_id` must still be denied INSIDE `_run()` before
    `planning.plan_run` -- and therefore `planning.load_intent` a second
    time -- is ever reached.

    MUTATION NOTE: the spy RECORDS (never raises) so this test is sensitive
    to the guard's ABSENCE, not merely to *some* exception firing inside
    `_run()` -- see `test_operator_mcp_adapter_external_import.py`'s
    identical note for the full rationale."""

    identity = AuthIdentity("alice", "ws-mine", ("owner",))
    monkeypatch.setattr(policy, "resolve_operator_identity", lambda *a, **kw: identity)

    malicious_intent_id = "/etc/passwd"

    calls: list[Any] = []

    def _recording_plan_run(*args: Any, **kwargs: Any) -> Any:
        calls.append((args, kwargs))
        raise AssertionError("plan_run reached -- containment guard did not fire")

    monkeypatch.setattr(planning_module, "plan_run", _recording_plan_run)

    ctx = policy.PolicyContext.for_configured_operator(
        operation_kind=run_plan.OPERATION_KIND,
        idempotency_key="idem-malicious-intent",
        effective_sensitivity=policy.SENSITIVITY_LEVELS[-1],  # what a rejected intent_id resolves to
        sensitivity_ceiling="client_sensitive",  # loosest -- guard stage does NOT deny this
        input_payload={
            "intent_id": malicious_intent_id,
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
        intent_id=malicious_intent_id,
        idempotency_key="idem-malicious-intent",
        confirmation_record=issued.record,
        presented_token=issued.token,
        paths=tmp_foundry,
        now=ids.now(),
        operations=op_service,
    )

    assert calls == [], "plan_run must never be called for a path-escaping intent_id"
    assert result.ok is False
    assert result.result is None
    assert result.error is not None
    assert result.error["reason_code"] == "internal_error"
