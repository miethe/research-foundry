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


def test_internal_error_envelope_for_unexpected_exception(server: Any) -> None:
    """An `input_payload` key colliding with a server-reserved keyword
    (`dry_run`) makes the `adapter.invoke(dry_run=..., **input_payload)`
    call raise `TypeError` (duplicate keyword argument) at the transport
    layer -- caught by the D7 chokepoint, never a raw traceback, never a
    distinguishing message."""

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
    assert payload["reason_code"] == "internal_error"
    assert payload["retryable"] is True
    assert "TypeError" not in str(payload)  # never a raw exception name/message


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
