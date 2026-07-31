"""Integration tests for the `rf-operator-mcp` stdio server (M2 Leg B,
OPM-5.1/5.2/5.4).

Requires the optional `mcp` extra (`uv sync --extra mcp`) -- skipped, not
failed, otherwise. Covers the ACTUAL transport surface this leg owns: the
closed, exact-14 tool inventory (D4), the stdio-only transport guard
(invariant 8), the D7 transport-level error mapping (`tool_unknown`/
`payload_too_large`/`internal_error`), and the `operation.preflight` meta
tool (D5: evaluate + mint, never consume, zero effect). It deliberately
does NOT re-test any individual adapter's own domain logic (`run.plan`'s
sensitivity resolution, `swarm.start`'s per-adapter action decomposition,
etc.) -- that is each adapter's own `tests/unit/test_operator_mcp_adapter_*.py`
file's job; this file proves the transport dispatches to the SAME,
unmodified P1-P3 pipeline, nothing more.

See `_StubWritebackPreviewAdapter`'s own docstring for why this file
carries a test-only stand-in for `writeback.preview` (Leg A's own file
ownership, not yet registered at the time this leg was implemented -- D10).
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

pytest.importorskip("mcp", reason="optional 'mcp' extra not installed (uv sync --extra mcp)")

from research_foundry.operator_mcp import server as server_module  # noqa: E402
from research_foundry.paths import FoundryPaths  # noqa: E402
from research_foundry.services import knowledge_access as ka  # noqa: E402
from research_foundry.services import operator_mcp_adapters as adapters_pkg  # noqa: E402
from research_foundry.services import operator_mcp_policy as policy  # noqa: E402
from research_foundry.services.operator_mcp_adapters import base as adapters_base  # noqa: E402
from research_foundry.yamlio import dump_yaml, load_yaml  # noqa: E402


def _call(server: Any, name: str, arguments: dict[str, Any]) -> Any:
    return asyncio.run(server.call_tool(name, arguments))


def _configure_operator(
    paths: FoundryPaths,
    *,
    user_id: str = "alice",
    workspace_id: str = "ws-mine",
    roles: tuple[str, ...] = ("owner",),
    sensitivity_ceiling: str = "client_sensitive",
) -> None:
    """Writes a REAL `foundry.operator_mcp` block -- mirrors
    `tests/unit/test_operator_mcp_policy.py::_write_operator_identity` +
    `tests/unit/test_operator_mcp_adapter_run_plan.py::
    _default_sensitivity_ceiling`'s combined shape, inlined here (this file
    intentionally never imports either test module, both of which pull in
    the serve-gated `research_foundry.api.auth.provider` import path at
    module level -- out of scope for this transport-only leg)."""

    data: dict[str, Any] = load_yaml(paths.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"]["operator_mcp"] = {
        "identity": {"user_id": user_id, "workspace_id": workspace_id, "roles": list(roles)},
        "sensitivity_ceiling": sensitivity_ceiling,
    }
    dump_yaml(data, paths.foundry_yaml)


class _StubWritebackPreviewAdapter:
    """Test-only stand-in for Leg A's `writeback.preview` adapter.

    At the time this leg was implemented, Leg A had not yet registered
    `writeback.preview` (`operator_mcp_adapters.get_adapter("writeback.preview")`
    returned `None`), so `build_server()`'s D4 fail-loud check correctly
    raised (D10 -- the expected, documented behavior, not a bug). This stub
    exists ONLY so this file's own transport-layer tests (inventory, schema
    closure, dispatch, dual encoding, error mapping) can exercise a REAL,
    full 14-tool server today without depending on Leg A's landing order.
    It always denies with `preflight_failed`, so it can never be mistaken
    for real coverage of `writeback.preview`'s own business logic -- that
    is Leg A's own test file's job.
    """

    operation_kind = "writeback.preview"

    def invoke(self, **kwargs: Any) -> Any:
        decision = policy.PolicyDecision(False, "preflight", "preflight_failed", retryable=True)
        return adapters_base.OperatorAdapterResult(ok=False, error=policy.build_error(decision))


@pytest.fixture()
def _writeback_preview_registered(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub-registers `writeback.preview` ONLY if Leg A has not already
    landed it for real. Uses `monkeypatch.setitem` directly on the private,
    unexported `_REGISTRY` dict owned by `operator_mcp_adapters/base.py`
    (a file this leg never edits -- this is a runtime-state patch that
    pytest's `monkeypatch` fixture guarantees to fully revert after the
    test, regardless of whatever state existed before it ran; there is no
    public `unregister()` -- `register()` is a permanent, idempotent-
    replace-only operation, which would leak a stub registration into
    every later test in the process for a kind that had no prior entry)."""

    if adapters_pkg.get_adapter("writeback.preview") is not None:
        return
    monkeypatch.setitem(adapters_base._REGISTRY, "writeback.preview", _StubWritebackPreviewAdapter())


@pytest.fixture()
def server(tmp_foundry: FoundryPaths, _writeback_preview_registered: None) -> Any:
    return server_module.build_server(paths=tmp_foundry)


# ---------------------------------------------------------------------------
# D10: the fail-loud build IS the correct behavior until every kind lands
# ---------------------------------------------------------------------------


def test_build_server_fails_loud_when_an_operation_kind_has_no_adapter(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D4/D10: `build_server()` raises, naming the missing kind, rather
    than silently building a partial server -- proven by deleting whatever
    is currently registered for `writeback.preview` (Leg A's real adapter,
    if it has landed, or nothing), independent of this repo's actual
    current state."""

    monkeypatch.delitem(adapters_base._REGISTRY, "writeback.preview", raising=False)
    with pytest.raises(RuntimeError, match="writeback.preview"):
        server_module.build_server(paths=tmp_foundry)


# ---------------------------------------------------------------------------
# D4: exact, closed 14-tool inventory
# ---------------------------------------------------------------------------


def test_exact_14_tool_inventory(server: Any) -> None:
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert len(policy.TOOL_NAMES) == 14
    assert names == set(policy.TOOL_NAMES)


def test_zero_overlap_with_knowledge_mcp_tool_names(server: Any) -> None:
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert len(ka.TOOL_NAMES) == 8
    assert names.isdisjoint(set(ka.TOOL_NAMES))


def test_all_tool_input_schemas_are_closed(server: Any) -> None:
    tools = asyncio.run(server.list_tools())
    assert len(tools) == 14
    for tool in tools:
        assert tool.inputSchema.get("additionalProperties") is False, tool.name


def test_preflight_schema_advertises_closed_enums(server: Any) -> None:
    tools = {t.name: t for t in asyncio.run(server.list_tools())}
    preflight_schema = tools[policy.PREFLIGHT_TOOL_NAME].inputSchema
    props = preflight_schema["properties"]
    assert set(props["operation_kind"]["enum"]) == set(policy.OPERATION_KINDS)
    assert set(props["effective_sensitivity"]["enum"]) == set(policy.SENSITIVITY_LEVELS)


# ---------------------------------------------------------------------------
# Stdio-only transport guard (invariant 8)
# ---------------------------------------------------------------------------


def test_transport_guard_allows_stdio(server: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from mcp.server.fastmcp import FastMCP

    monkeypatch.setattr(FastMCP, "run", lambda self, transport=None, mount_path=None: None)
    server.run()  # default
    server.run(transport="stdio")  # explicit


def test_transport_guard_rejects_sse(server: Any) -> None:
    with pytest.raises(server_module.UnsupportedTransportError):
        server.run(transport="sse")


def test_transport_guard_rejects_streamable_http(server: Any) -> None:
    with pytest.raises(server_module.UnsupportedTransportError):
        server.run(transport="streamable-http")


def test_transport_guard_blocks_sse_app_directly(server: Any) -> None:
    with pytest.raises(server_module.UnsupportedTransportError):
        server.sse_app()


def test_transport_guard_blocks_streamable_http_app_directly(server: Any) -> None:
    with pytest.raises(server_module.UnsupportedTransportError):
        server.streamable_http_app()


def test_transport_guard_server_is_a_genuine_fastmcp_subclass(server: Any) -> None:
    """Same closed generation-4 shape `knowledge_mcp/registry.py`'s own
    guard documents -- no bound-method `__self__` bypass exists because
    there is only one object."""

    from mcp.server.fastmcp import FastMCP

    assert isinstance(server, FastMCP)
    assert server.list_tools.__self__ is server
    assert server.call_tool.__self__ is server


def test_transport_guard_unbound_base_class_call_bypasses_the_guard_by_design(server: Any) -> None:
    """M2 fix cycle 1, F1.6 (TERRA-5) -- pins the documented, ADJUDICATED
    limitation (see this module's docstring's "Scope of the stdio-only
    guard" section, and `m2-fix-contract.md`'s TERRA-5 adjudication): an
    UNBOUND base-class call on this SAME guarded instance is NOT blocked
    and structurally CANNOT be blocked by this shape of guard -- only
    REACHABLE activation paths (bound-method dispatch, `run()`, the
    process entrypoint) are. Deliberately NOT redesigned this fix cycle:
    reaching an unbound base-class call requires the caller to already be
    executing arbitrary Python in this process, at which point this guard
    is moot either way (they could `import socket` directly). This test
    exists so no future reader mistakes the guard above for a sandbox."""

    from mcp.server.fastmcp import FastMCP

    # A real, unguarded Starlette app is returned -- confirms the bypass is
    # genuine (would raise `UnsupportedTransportError` through the guarded,
    # bound instance method; see `test_transport_guard_blocks_sse_app_
    # directly` above for that contrast).
    assert FastMCP.sse_app(server) is not None
    assert FastMCP.streamable_http_app(server) is not None


# ---------------------------------------------------------------------------
# D7: transport-level error mapping (the ONE dispatch chokepoint)
# ---------------------------------------------------------------------------


def test_unknown_tool_maps_to_tool_unknown_envelope(server: Any) -> None:
    result = _call(server, "not_a_real_tool", {})
    assert result.isError is True
    payload = result.structuredContent
    assert payload["type"] == "operator_mcp_error"
    assert payload["reason_code"] == "tool_unknown"
    # H9-shaped: content and structuredContent carry the SAME payload.
    import json

    assert json.loads(result.content[0].text) == payload


def test_oversized_payload_maps_to_payload_too_large_envelope(server: Any) -> None:
    huge = {"idempotency_key": "idem-1", "input_payload": {"blob": "x" * 200_000}}
    result = _call(server, "run.plan", huge)
    assert result.isError is True
    assert result.structuredContent["reason_code"] == "payload_too_large"


def test_reserved_input_payload_key_maps_to_payload_too_large_envelope(server: Any) -> None:
    """M2 fix cycle 1, F1.3 (TERRA-4) -- **inverts** this test's own
    pre-fix assertion (contract hard boundary 5: do not weaken/delete a
    test that pins wrong behavior, invert it and say so loudly). Pre-fix,
    an `input_payload` key colliding with a server-reserved keyword
    (`dry_run`) reached `adapter.invoke(dry_run=..., **input_payload)` and
    raised a raw `TypeError` (duplicate keyword argument), caught only
    ACCIDENTALLY by the D7 `internal_error` boundary -- never a deliberate
    rejection, and this collision-based mechanism did NOT close the
    sharper sibling case (`now`, which never collides with an explicitly-
    supplied server keyword and therefore reached the adapter completely
    silently -- the actual TERRA-4 authorization-bypass vector; see
    `test_di_only_input_payload_keys_are_rejected_before_reaching_the_adapter`
    below). This test now asserts the CORRECT, deliberate behavior: every
    non-semantic key is rejected BEFORE `adapter.invoke` is ever called,
    with an explicit `payload_too_large` envelope (reused reason code, not
    a raw exception leak either way)."""

    result = _call(
        server,
        "run.plan",
        {
            "idempotency_key": "idem-1",
            "input_payload": {"dry_run": True, "intent_id": "does-not-matter"},
        },
    )
    assert result.isError is True
    payload = result.structuredContent
    assert payload["reason_code"] == "payload_too_large"
    assert "TypeError" not in str(payload)  # never a raw exception name/message


def test_di_only_input_payload_keys_are_rejected_before_reaching_the_adapter(
    server: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M2 fix cycle 1, F1.3 (TERRA-4) -- the sharper reproduction. `now`
    (and the other DI-only names) does NOT collide with any
    server-reserved keyword, so pre-fix it reached `adapter.invoke(now=
    <caller-controlled value>, **input_payload)` completely silently -- an
    in-process MCP caller could supply `now` and control confirmation
    expiry, an authorization bypass (TERRA-4's actual finding, not the
    `dry_run` TypeError accident). Spies on `adapters.get_adapter` so this
    proves `adapter.invoke` is NEVER called for any of these five names,
    not merely that the final envelope happens to look right."""

    real_get_adapter = adapters_pkg.get_adapter
    invoked: list[str] = []

    def _spy_get_adapter(kind: str) -> Any:
        real_adapter = real_get_adapter(kind)
        if real_adapter is None:
            return None

        class _InvokeSpy:
            operation_kind = kind

            def invoke(self, **kwargs: Any) -> Any:
                invoked.append(kind)
                return real_adapter.invoke(**kwargs)

        return _InvokeSpy()

    monkeypatch.setattr(adapters_pkg, "get_adapter", _spy_get_adapter)

    for reserved_key in ("now", "operations", "cancel_resume", "receipts", "attempts"):
        result = _call(
            server,
            "run.plan",
            {
                "idempotency_key": "idem-1",
                "input_payload": {"intent_id": "does-not-matter", reserved_key: "hack"},
            },
        )
        assert result.isError is True, reserved_key
        assert result.structuredContent["reason_code"] == "payload_too_large", reserved_key

    assert invoked == [], f"adapter.invoke was reached for a DI-only key: {invoked!r}"


def test_legitimate_optional_adapter_parameter_still_reaches_the_adapter(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    """The F1.3 allowlist must not become an accidental over-broad
    rejection: a REAL, declared `run.plan` optional parameter (`depth`)
    still reaches `adapter.invoke` -- denies downstream (no confirmation),
    never at the allowlist gate itself."""

    _configure_operator(tmp_foundry)
    result = _call(
        server,
        "run.plan",
        {
            "idempotency_key": "idem-1",
            "input_payload": {"intent_id": "does-not-exist", "depth": "quick"},
        },
    )
    assert result.isError is True
    assert result.structuredContent["reason_code"] == "confirmation_missing"


def test_unknown_top_level_argument_is_silently_dropped_not_rejected(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    """M2 fix cycle 1, F1.4/ICA E2 claim correction -- pins the ACTUAL
    (silent-drop, not reject) behavior for an unrelated TOP-LEVEL key
    alongside legitimate arguments (a DIFFERENT layer than F1.3's
    `input_payload`-nested allowlist above: the SDK's own generated
    pydantic arg model for each tool uses `extra='ignore'`, not
    `'forbid'`). Denial here is for the UNRELATED reason
    `confirmation_missing` -- the SAME denial an equivalent request with NO
    extra key at all would get -- proving the extra key changed nothing
    about how the request was processed, not merely that no error
    escaped. See this module's docstring's "Unknown top-level tool
    arguments" section."""

    _configure_operator(tmp_foundry)
    result = _call(
        server,
        "run.plan",
        {
            "idempotency_key": "idem-1",
            "input_payload": {"intent_id": "does-not-exist"},
            "EXTRA_UNDECLARED": "should be silently dropped, not rejected",
        },
    )
    assert result.isError is True
    assert result.structuredContent["reason_code"] == "confirmation_missing"


def test_deeply_nested_argument_maps_to_payload_too_large_not_recursion_error(server: Any) -> None:
    """M2 fix cycle 1, F1.4 (TERRA-6). Pre-fix, calling
    `_check_transport_payload_size` directly on an equivalently deep
    mapping raised `RecursionError` (TERRA-6's own reproduction, and this
    module's PRE-fix `json.dumps`-based size check would do the same).
    Drives the FULL transport path (`server.call_tool`, not the helper in
    isolation) to prove a bounded envelope is returned instead."""

    nested: dict[str, Any] = {}
    cursor = nested
    for _ in range(50_000):
        cursor["n"] = {}
        cursor = cursor["n"]

    result = _call(server, "run.plan", {"idempotency_key": "idem-1", "input_payload": nested})
    assert result.isError is True
    assert result.structuredContent["reason_code"] == "payload_too_large"


def test_internal_error_envelope_for_genuine_adapter_exception(
    server: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D7's `internal_error` mapping, re-proven under a GENUINE unexpected
    exception -- the pre-fix version of this coverage relied on an
    ACCIDENTAL `TypeError` collision (see
    `test_reserved_input_payload_key_maps_to_payload_too_large_envelope`'s
    docstring for why that assertion was inverted, not merely renamed).
    Here every `input_payload` key is legitimate; the exception comes from
    a monkeypatched adapter's own `.invoke()` body, exactly like ICA's E6
    reproduction."""

    class _BoomAdapter:
        operation_kind = "run.plan"

        def invoke(self, **kwargs: Any) -> Any:
            raise RuntimeError("/etc/shadow leaked path -- must never reach the caller")

    monkeypatch.setitem(adapters_base._REGISTRY, "run.plan", _BoomAdapter())

    result = _call(
        server, "run.plan", {"idempotency_key": "idem-1", "input_payload": {"intent_id": "x"}}
    )
    assert result.isError is True
    payload = result.structuredContent
    assert payload["reason_code"] == "internal_error"
    assert payload["retryable"] is True
    assert "shadow" not in str(payload)
    assert "RuntimeError" not in str(payload)


# ---------------------------------------------------------------------------
# D5: operation.preflight -- evaluate + mint, never consume, zero effect
# ---------------------------------------------------------------------------


def test_preflight_denies_without_configured_identity(server: Any) -> None:
    result = _call(
        server,
        "operation.preflight",
        {"operation_kind": "run.plan", "idempotency_key": "idem-1", "effective_sensitivity": "public"},
    )
    assert result.isError is True
    assert result.structuredContent["reason_code"] == "identity_denied"


def test_preflight_allow_mints_confirmation_with_zero_effect(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    _configure_operator(tmp_foundry)

    registries_before = sorted(p.name for p in (tmp_foundry.root / "registries").rglob("*") if p.is_file())
    runs_before = sorted(p.name for p in (tmp_foundry.root / "runs").rglob("*") if p.is_file())

    result = _call(
        server,
        "operation.preflight",
        {"operation_kind": "run.plan", "idempotency_key": "idem-1", "effective_sensitivity": "public"},
    )

    assert result.isError is False
    payload = result.structuredContent
    assert payload["allowed"] is True
    confirmation = payload["confirmation"]
    assert confirmation["record"]["status"] == "issued"
    assert confirmation["record"]["operation_kind"] == "run.plan"
    assert confirmation["record"]["idempotency_key"] == "idem-1"
    assert isinstance(confirmation["token"], str) and confirmation["token"]
    # The raw token is never persisted; the durable record carries only its digest.
    assert "token" not in confirmation["record"]
    assert confirmation["record"]["token_digest"]

    # Zero effect (D5): no operation manifest, receipt, or artifact exists
    # -- the durable registries/runs trees are byte-for-byte unchanged.
    registries_after = sorted(p.name for p in (tmp_foundry.root / "registries").rglob("*") if p.is_file())
    runs_after = sorted(p.name for p in (tmp_foundry.root / "runs").rglob("*") if p.is_file())
    assert registries_after == registries_before
    assert runs_after == runs_before


def test_preflight_confirmation_not_required_kind_mints_no_confirmation(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    _configure_operator(tmp_foundry)
    assert policy.CONFIRMATION_NOT_REQUIRED_KINDS == frozenset({"job.status"})

    result = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "job.status",
            "idempotency_key": "idem-1",
            "effective_sensitivity": "public",
            "targets": [{"target_kind": "agent_job", "target_ref": "op_fake123"}],
        },
    )

    assert result.isError is False
    payload = result.structuredContent
    assert payload == {"allowed": True, "confirmation": None}


def test_preflight_missing_required_target_denies_preflight_failed(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    """`swarm.start` requires a `run` target (`_REQUIRED_TARGET_KINDS`) --
    omitting it is an honest, accurate `preflight_failed` denial, never a
    false ALLOW."""

    _configure_operator(tmp_foundry)
    result = _call(
        server,
        "operation.preflight",
        {"operation_kind": "swarm.start", "idempotency_key": "idem-1", "effective_sensitivity": "public"},
    )
    assert result.isError is True
    assert result.structuredContent["reason_code"] == "preflight_failed"


def test_preflight_malformed_target_denies_target_invalid(server: Any, tmp_foundry: FoundryPaths) -> None:
    _configure_operator(tmp_foundry)
    result = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "swarm.start",
            "idempotency_key": "idem-1",
            "effective_sensitivity": "public",
            "targets": [{"target_kind": "run"}],  # missing target_ref
        },
    )
    assert result.isError is True
    assert result.structuredContent["reason_code"] == "target_invalid"


# ---------------------------------------------------------------------------
# M2 fix cycle 1, F1.1 (TERRA-1): preflight durably persists the minted
# confirmation before returning it
# ---------------------------------------------------------------------------


def test_preflight_persists_minted_confirmation_for_later_consumption(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    """Pre-fix, `record_confirmation` was never called anywhere on this
    path (`grep -n record_confirmation src/.../operator_mcp/server.py`
    returned nothing) -- a real `confirmations` row for the minted
    `confirmation_id` never existed, so no normal preflight -> execute flow
    through this transport could ever consume its own confirmation
    (TERRA-1). Queries the SAME durable store `consume_and_create_
    operation` reads from directly (mirrors
    `tests/unit/test_operator_operation_service.py`'s own `_raw_connect`
    convention) rather than re-deriving the full e2e execute path -- that
    full preflight -> execute proof is `test_operator_mcp_preflight_
    execute_e2e.py`'s job (F1.5)."""

    _configure_operator(tmp_foundry)
    result = _call(
        server,
        "operation.preflight",
        {"operation_kind": "run.plan", "idempotency_key": "idem-persist", "effective_sensitivity": "public"},
    )
    assert result.isError is False
    confirmation_id = result.structuredContent["confirmation"]["record"]["confirmation_id"]

    from research_foundry.services import operator_operation_service as ops_module

    conn = ops_module._connect(tmp_foundry)
    try:
        row = conn.execute(
            "SELECT status FROM confirmations WHERE confirmation_id = ?", (confirmation_id,)
        ).fetchone()
    finally:
        conn.close()
    assert row is not None, "record_confirmation was never called -- TERRA-1 regression"
    assert row[0] == "issued"


# ---------------------------------------------------------------------------
# M2 fix cycle 1, F1.2 (TERRA-2): writeback.preview preflight can mint a
# USABLE confirmation (writeback_targets is no longer silently dropped)
# ---------------------------------------------------------------------------


def test_preflight_writeback_preview_allows_with_valid_targets(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    """Pre-fix, `writeback.preview` could NEVER mint a confirmation through
    this transport regardless of what the caller supplied -- `ctx.
    writeback_targets` was always `()` (the field was never threaded from
    `input_payload["targets"]`), and `_check_preflight` denies
    `preflight_failed` whenever it is empty for this kind. This is the
    positive proof TERRA-2 asked for: a real, valid `targets` list now
    allows."""

    _configure_operator(tmp_foundry)
    result = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "writeback.preview",
            "idempotency_key": "idem-wb-1",
            "effective_sensitivity": "public",
            "targets": [{"target_kind": "evidence_bundle", "target_ref": "rf_run_fake"}],
            "input_payload": {"run_id": "rf_run_fake", "targets": ["meatywiki", "arc"]},
        },
    )
    assert result.isError is False, result.structuredContent
    assert result.structuredContent["allowed"] is True
    assert result.structuredContent["confirmation"]["record"]["status"] == "issued"


def test_preflight_writeback_preview_missing_targets_denies_preflight_failed(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    """The pre-fix behavior (empty `writeback_targets`) stays reachable --
    and correct -- when the caller genuinely omits `targets` from
    `input_payload`; this is the honest `preflight_failed` denial, not a
    regression."""

    _configure_operator(tmp_foundry)
    result = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "writeback.preview",
            "idempotency_key": "idem-wb-2",
            "effective_sensitivity": "public",
            "targets": [{"target_kind": "evidence_bundle", "target_ref": "rf_run_fake"}],
            "input_payload": {"run_id": "rf_run_fake"},
        },
    )
    assert result.isError is True
    assert result.structuredContent["reason_code"] == "preflight_failed"


def test_preflight_writeback_preview_unknown_target_name_denies_target_invalid(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    """Validated against `writeback.WRITEBACK_TARGET_NAMES` -- the closed,
    six-member vocabulary Leg 2 owns -- never a second, independently
    typed vocabulary this leg invents."""

    _configure_operator(tmp_foundry)
    result = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "writeback.preview",
            "idempotency_key": "idem-wb-3",
            "effective_sensitivity": "public",
            "targets": [{"target_kind": "evidence_bundle", "target_ref": "rf_run_fake"}],
            "input_payload": {"run_id": "rf_run_fake", "targets": ["not_a_real_target"]},
        },
    )
    assert result.isError is True
    assert result.structuredContent["reason_code"] == "target_invalid"


def test_preflight_writeback_preview_malformed_targets_shape_denies_target_invalid(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    _configure_operator(tmp_foundry)
    result = _call(
        server,
        "operation.preflight",
        {
            "operation_kind": "writeback.preview",
            "idempotency_key": "idem-wb-4",
            "effective_sensitivity": "public",
            "targets": [{"target_kind": "evidence_bundle", "target_ref": "rf_run_fake"}],
            "input_payload": {"run_id": "rf_run_fake", "targets": "meatywiki"},  # str, not list
        },
    )
    assert result.isError is True
    assert result.structuredContent["reason_code"] == "target_invalid"


# ---------------------------------------------------------------------------
# Operation-kind tools: thin dispatch via get_adapter(kind), unchanged P1-P3
# pipeline (no new capability, no live writeback reachable)
# ---------------------------------------------------------------------------


def test_operation_tool_dry_run_dispatches_through_get_adapter_with_zero_effect(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    _configure_operator(tmp_foundry)
    result = _call(
        server,
        "run.plan",
        {
            "idempotency_key": "idem-1",
            "dry_run": True,
            "input_payload": {"intent_id": "does-not-exist"},
        },
    )
    assert result.isError is False
    payload = result.structuredContent
    assert payload == {"ok": True, "operation_id": None, "result": {"dry_run": True, "operation_kind": "run.plan"}}


def test_operation_tool_without_confirmation_denies_confirmation_missing(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    """Proves the real pipeline runs end to end (capability -> rbac ->
    audit_health -> guard -> preflight -> confirmation) and that NO tool
    this transport registers can execute a real effect without a bound
    confirmation -- the hard boundary this whole milestone exists to prove
    ("provably cannot execute")."""

    _configure_operator(tmp_foundry)
    result = _call(
        server,
        "run.plan",
        {"idempotency_key": "idem-1", "input_payload": {"intent_id": "does-not-exist"}},
    )
    assert result.isError is True
    payload = result.structuredContent
    assert payload["type"] == "operator_mcp_error"
    assert payload["reason_code"] == "confirmation_missing"


def test_operation_tool_forged_confirmation_denies_confirmation_missing(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    """A caller-fabricated confirmation record/token (never minted by this
    server's own `operation.preflight`) is rejected the SAME way a wholly
    absent one is -- no distinguishing signal (H6)."""

    _configure_operator(tmp_foundry)
    forged_record = {
        "schema_version": "1.0",
        "type": "operator_mcp_confirmation",
        "confirmation_id": "opc_forged",
        "token_digest": "0" * 64,
        "actor": {"user_id": "alice", "workspace_id": "ws-mine", "roles": ["owner"]},
        "effective_sensitivity": "public",
        "operation_kind": "run.plan",
        "canonical_input_digest": "0" * 64,
        "idempotency_key": "idem-1",
        "policy_snapshot_version": "policy-order-v1",
        "targets": [],
        "status": "issued",
        "issued_at": "2026-01-01T00:00:00Z",
        "expires_at": "2026-01-01T00:05:00Z",
        "consumed_at": None,
        "consumed_by_operation_id": None,
    }
    result = _call(
        server,
        "run.plan",
        {
            "idempotency_key": "idem-1",
            "input_payload": {"intent_id": "does-not-exist"},
            "confirmation_record": forged_record,
            "presented_token": "not-the-real-token",
        },
    )
    assert result.isError is True
    assert result.structuredContent["reason_code"] == "confirmation_missing"


def test_writeback_preview_tool_denies_via_adapter_never_reaches_a_live_client(
    server: Any, tmp_foundry: FoundryPaths
) -> None:
    """`writeback.preview` is registered (real Leg A adapter or this
    file's own `_StubWritebackPreviewAdapter` -- see D10) and dispatches
    exactly like every other kind; either way it denies here (no
    confirmation presented), proving no path through THIS transport can
    ever reach a live client regardless of which adapter answers."""

    _configure_operator(tmp_foundry)
    result = _call(
        server,
        "writeback.preview",
        {"idempotency_key": "idem-1", "input_payload": {"run_id": "does-not-exist"}},
    )
    assert result.isError is True
    assert result.structuredContent["type"] == "operator_mcp_error"
