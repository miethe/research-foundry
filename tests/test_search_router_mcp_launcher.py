"""Tests for the Search Router MCP launcher (DI-1 F2 remediation).

Covers the four remediation changes from the delta re-audit
(``docs/project_plans/reports/audits/di-1-delta-reaudit-2026-07-26.md``,
finding F2):

1. Launch principal resolution (env vars -> ``foundry.mcp.principal``
   config -> ``None``/single-operator-trust).
2. Per-call client-identity reconciliation against the launch principal.
3. Server-side ``sensitivity_threshold`` ceiling clamping.
4. The stdio-only transport guard on a built ``FastMCP`` server.

Modules 1-3 (``resolve_launch_principal``/``reconcile_client_identity``/
``clamp_sensitivity_threshold``) never import the optional ``mcp`` SDK, so
this file's TESTS for them run unconditionally. Only the transport-guard
tests at the bottom need a real ``FastMCP`` instance and are gated on
``pytest.importorskip("mcp", ...)`` like the rest of the MCP test suite.
"""

from __future__ import annotations

from typing import Any

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.services.search_router import mcp_launcher
from research_foundry.yamlio import dump_yaml, load_yaml


@pytest.fixture(autouse=True)
def _reset_caches() -> Any:
    mcp_launcher.reset_launch_principal_cache()
    mcp_launcher.reset_sensitivity_ceiling_cache()
    yield
    mcp_launcher.reset_launch_principal_cache()
    mcp_launcher.reset_sensitivity_ceiling_cache()


def _clear_principal_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RF_MCP_PRINCIPAL_USER_ID", raising=False)
    monkeypatch.delenv("RF_MCP_PRINCIPAL_WORKSPACE_ID", raising=False)
    monkeypatch.delenv("RF_MCP_PRINCIPAL_ROLES", raising=False)


# ---------------------------------------------------------------------------
# 1. Launch principal resolution
# ---------------------------------------------------------------------------


def test_resolve_launch_principal_from_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RF_MCP_PRINCIPAL_USER_ID", "alice")
    monkeypatch.setenv("RF_MCP_PRINCIPAL_WORKSPACE_ID", "workspace-a")
    monkeypatch.setenv("RF_MCP_PRINCIPAL_ROLES", "researcher, admin")

    principal = mcp_launcher.resolve_launch_principal()

    assert principal is not None
    assert principal.user_id == "alice"
    assert principal.workspace_id == "workspace-a"
    assert principal.roles == ("researcher", "admin")


def test_resolve_launch_principal_from_config_block_when_no_env(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_principal_env(monkeypatch)

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["mcp"] = {
        "principal": {"user_id": "bob", "workspace_id": "workspace-b", "roles": ["viewer"]}
    }
    dump_yaml(foundry, tmp_foundry.foundry_yaml)

    principal = mcp_launcher.resolve_launch_principal(tmp_foundry)

    assert principal is not None
    assert principal.user_id == "bob"
    assert principal.workspace_id == "workspace-b"
    assert principal.roles == ("viewer",)


def test_resolve_launch_principal_none_when_neither_configured(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_principal_env(monkeypatch)

    assert mcp_launcher.resolve_launch_principal(tmp_foundry) is None


def test_resolve_launch_principal_partial_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RF_MCP_PRINCIPAL_USER_ID", "alice")
    monkeypatch.delenv("RF_MCP_PRINCIPAL_WORKSPACE_ID", raising=False)

    with pytest.raises(mcp_launcher.LaunchPrincipalError):
        mcp_launcher.resolve_launch_principal()


def test_resolve_launch_principal_partial_env_raises_other_order(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RF_MCP_PRINCIPAL_USER_ID", raising=False)
    monkeypatch.setenv("RF_MCP_PRINCIPAL_WORKSPACE_ID", "workspace-a")

    with pytest.raises(mcp_launcher.LaunchPrincipalError):
        mcp_launcher.resolve_launch_principal()


def test_get_launch_principal_caches_across_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RF_MCP_PRINCIPAL_USER_ID", "alice")
    monkeypatch.setenv("RF_MCP_PRINCIPAL_WORKSPACE_ID", "workspace-a")

    first = mcp_launcher.get_launch_principal()
    # Mutate the env after the first resolution -- the cached value must win.
    monkeypatch.setenv("RF_MCP_PRINCIPAL_WORKSPACE_ID", "workspace-b")
    second = mcp_launcher.get_launch_principal()

    assert first is second
    assert second is not None
    assert second.workspace_id == "workspace-a"

    refreshed = mcp_launcher.get_launch_principal(refresh=True)
    assert refreshed is not None
    assert refreshed.workspace_id == "workspace-b"


# ---------------------------------------------------------------------------
# 2. Client identity reconciliation
# ---------------------------------------------------------------------------


def test_reconcile_client_identity_matching_workspace_allowed() -> None:
    from research_foundry.api.auth.provider import AuthIdentity

    principal = AuthIdentity(user_id="alice", workspace_id="workspace-a", roles=("researcher",))
    client_identity = {"user_id": "alice", "workspace_id": "workspace-a", "roles": ["ignored"]}

    effective = mcp_launcher.reconcile_client_identity(principal, client_identity)

    assert effective is not None
    assert effective.workspace_id == "workspace-a"
    assert effective.roles == ("researcher",)  # client-declared roles never win


def test_reconcile_client_identity_mismatched_workspace_rejected() -> None:
    from research_foundry.api.auth.provider import AuthIdentity

    principal = AuthIdentity(user_id="alice", workspace_id="workspace-a", roles=("researcher",))
    client_identity = {"user_id": "alice", "workspace_id": "workspace-b"}

    with pytest.raises(mcp_launcher.CrossWorkspaceIdentityError):
        mcp_launcher.reconcile_client_identity(principal, client_identity)


def test_reconcile_client_identity_no_principal_ignores_client_identity(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client_identity = {"user_id": "eve", "workspace_id": "workspace-a", "roles": ["admin"]}

    with caplog.at_level("WARNING", logger="research_foundry.services.search_router.mcp_launcher"):
        effective = mcp_launcher.reconcile_client_identity(None, client_identity)

    assert effective is None
    assert any("single-operator-trust" in record.message for record in caplog.records)


def test_reconcile_client_identity_no_principal_and_no_client_identity_is_quiet(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level("WARNING", logger="research_foundry.services.search_router.mcp_launcher"):
        effective = mcp_launcher.reconcile_client_identity(None, None)

    assert effective is None
    assert caplog.records == []


def test_reconcile_client_identity_user_id_hint_passes_through() -> None:
    from research_foundry.api.auth.provider import AuthIdentity

    principal = AuthIdentity(user_id="alice", workspace_id="workspace-a", roles=("researcher",))
    client_identity = {"user_id": "alice-agent-session-7", "workspace_id": "workspace-a"}

    effective = mcp_launcher.reconcile_client_identity(principal, client_identity)

    assert effective is not None
    assert effective.user_id == "alice-agent-session-7"
    assert effective.workspace_id == "workspace-a"
    assert effective.roles == ("researcher",)


def test_reconcile_client_identity_absent_client_identity_passes_principal_through() -> None:
    from research_foundry.api.auth.provider import AuthIdentity

    principal = AuthIdentity(user_id="alice", workspace_id="workspace-a", roles=("researcher",))

    assert mcp_launcher.reconcile_client_identity(principal, None) is principal
    assert mcp_launcher.reconcile_client_identity(principal, {}) is principal


# ---------------------------------------------------------------------------
# 3. Sensitivity ceiling
# ---------------------------------------------------------------------------


def test_clamp_sensitivity_threshold_below_ceiling_passes_through() -> None:
    effective, clamped = mcp_launcher.clamp_sensitivity_threshold("public", "personal")

    assert effective == "public"
    assert clamped is False


def test_clamp_sensitivity_threshold_above_ceiling_is_clamped() -> None:
    effective, clamped = mcp_launcher.clamp_sensitivity_threshold("client_sensitive", "personal")

    assert effective == "personal"
    assert clamped is True


def test_clamp_sensitivity_threshold_no_ceiling_passes_through_unclamped() -> None:
    effective, clamped = mcp_launcher.clamp_sensitivity_threshold("client_sensitive", None)

    assert effective == "client_sensitive"
    assert clamped is False


def test_clamp_sensitivity_threshold_omitted_client_value_passes_through() -> None:
    effective, clamped = mcp_launcher.clamp_sensitivity_threshold(None, "personal")

    assert effective is None
    assert clamped is False


def test_clamp_sensitivity_threshold_unknown_label_clamped_fail_closed() -> None:
    effective, clamped = mcp_launcher.clamp_sensitivity_threshold("not_a_real_label", "personal")

    assert effective == "personal"
    assert clamped is True


def test_resolve_sensitivity_ceiling_prefers_mcp_config_over_viewer(
    tmp_foundry: FoundryPaths,
) -> None:
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["mcp"] = {"sensitivity_threshold_max": "work_sensitive"}
    foundry["foundry"]["viewer"] = {"sensitivity_threshold": "public"}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)

    assert mcp_launcher.resolve_sensitivity_ceiling(tmp_foundry) == "work_sensitive"


def test_resolve_sensitivity_ceiling_falls_back_to_viewer_threshold(
    tmp_foundry: FoundryPaths,
) -> None:
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["viewer"] = {"sensitivity_threshold": "personal"}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)

    assert mcp_launcher.resolve_sensitivity_ceiling(tmp_foundry) == "personal"


def test_resolve_sensitivity_ceiling_none_when_unconfigured(tmp_foundry: FoundryPaths) -> None:
    """The distributed/canonical ``foundry.yaml`` (copied verbatim by the
    ``tmp_foundry`` fixture) ships a deliberate fail-closed
    ``viewer.sensitivity_threshold: public`` default (public-multiuser
    P0/P1). To exercise the true "neither configured" branch, strip both
    blocks explicitly rather than relying on the fixture's ambient state."""

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"].pop("viewer", None)
    foundry["foundry"].pop("mcp", None)
    dump_yaml(foundry, tmp_foundry.foundry_yaml)

    assert mcp_launcher.resolve_sensitivity_ceiling(tmp_foundry) is None


# ---------------------------------------------------------------------------
# 4. Transport guard (generation 4 -- FastMCP subclass, not a proxy)
# ---------------------------------------------------------------------------
#
# Generations 1-3 of this guard were each a delegating PROXY wrapping a
# distinct real ``FastMCP`` instance; generation 3 was bypassed (Codex
# gpt-5.6-sol, 2026-07-27) via ``server.list_tools.__self__.sse_app()`` --
# every "safe" method the proxy delegated returned a bound method whose
# ``__self__`` was the real, unguarded server, by construction of Python's
# descriptor protocol. No attribute-name denylist on the proxy could ever
# close that: the leak was the existence of a second object, not any
# particular name it was reachable through.
#
# Generation 4 (current) closes the bug CLASS instead of the next attribute
# name: ``build_server()`` constructs a genuine ``FastMCP`` SUBCLASS
# (``mcp_launcher.stdio_only_fastmcp_class``) directly, so there is no
# second object anywhere. The tests below verify that property directly --
# via the bound-method ``__self__`` bypass specifically -- rather than
# re-testing an attribute-access denylist that no longer exists in this
# design (see ``test_transport_guard_bare_attribute_access_does_not_raise``
# for the resulting, deliberate behavior change).

pytest.importorskip("mcp", reason="optional 'mcp' extra not installed (uv sync --extra mcp)")

from mcp.server.fastmcp import FastMCP  # noqa: E402

from research_foundry.services.search_router import mcp_server  # noqa: E402


def test_transport_guard_allows_default_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str | None] = []

    def _fake_run(self: Any, transport: str | None = "stdio", mount_path: str | None = None) -> None:
        calls.append(transport)

    monkeypatch.setattr(FastMCP, "run", _fake_run)

    server = mcp_server.build_server()
    server.run()

    assert calls == ["stdio"]


def test_transport_guard_allows_explicit_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str | None] = []

    def _fake_run(self: Any, transport: str | None = "stdio", mount_path: str | None = None) -> None:
        calls.append(transport)

    monkeypatch.setattr(FastMCP, "run", _fake_run)

    server = mcp_server.build_server()
    server.run(transport="stdio")

    assert calls == ["stdio"]


def test_transport_guard_rejects_sse(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str | None] = []

    def _fake_run(self: Any, transport: str | None = "stdio", mount_path: str | None = None) -> None:
        calls.append(transport)

    monkeypatch.setattr(FastMCP, "run", _fake_run)

    server = mcp_server.build_server()
    with pytest.raises(mcp_launcher.UnsupportedTransportError):
        server.run(transport="sse")

    assert calls == []  # the real (faked) run was never reached


def test_transport_guard_rejects_streamable_http(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str | None] = []

    def _fake_run(self: Any, transport: str | None = "stdio", mount_path: str | None = None) -> None:
        calls.append(transport)

    monkeypatch.setattr(FastMCP, "run", _fake_run)

    server = mcp_server.build_server()
    with pytest.raises(mcp_launcher.UnsupportedTransportError):
        server.run(transport="streamable-http")

    assert calls == []


def test_transport_guard_rejects_sse_app() -> None:
    server = mcp_server.build_server()
    with pytest.raises(mcp_launcher.UnsupportedTransportError):
        server.sse_app()


def test_transport_guard_rejects_streamable_http_app() -> None:
    server = mcp_server.build_server()
    with pytest.raises(mcp_launcher.UnsupportedTransportError):
        server.streamable_http_app()


def test_transport_guard_rejects_run_sse_async() -> None:
    """``run_sse_async`` is a coroutine method on the real ``FastMCP``, but
    the guarded override is deliberately a PLAIN function (see the comment
    above it in ``mcp_launcher.py``) so calling it -- with no ``await`` --
    raises immediately, rather than silently handing back an inert,
    never-executed coroutine object."""

    server = mcp_server.build_server()
    with pytest.raises(mcp_launcher.UnsupportedTransportError):
        server.run_sse_async()


def test_transport_guard_rejects_run_streamable_http_async() -> None:
    server = mcp_server.build_server()
    with pytest.raises(mcp_launcher.UnsupportedTransportError):
        server.run_streamable_http_async()


def test_transport_guard_rejects_run_sse_async_when_awaited() -> None:
    """A well-behaved caller doing ``await server.run_sse_async()`` (the
    natural way to invoke what looks like a coroutine method) still observes
    the identical error -- Python evaluates the call ``server.
    run_sse_async()`` before it ever reaches the ``await``, so the guard's
    synchronous raise happens first; there is no coroutine left to await.
    No ``pytest-asyncio`` dependency needed: ``asyncio.run`` drives a plain
    async wrapper that performs the ``await`` itself."""

    import asyncio

    server = mcp_server.build_server()

    async def _await_it() -> None:
        await server.run_sse_async()

    with pytest.raises(mcp_launcher.UnsupportedTransportError):
        asyncio.run(_await_it())


def test_transport_guard_allows_passthrough_attributes_unchanged() -> None:
    """Non-blocked attributes (e.g. ``list_tools``) are the real, inherited
    ``FastMCP`` methods -- the guard is a denylist over four names, not an
    allowlist; nothing delegates, because ``build_server()`` constructs the
    guarded subclass directly rather than wrapping a separately-built
    server."""

    server = mcp_server.build_server()
    assert callable(server.list_tools)
    assert callable(server.call_tool)


def test_transport_guard_bare_attribute_access_does_not_raise() -> None:
    """Deliberate behavior change from generations 2-3: those proxy
    generations denied the four blocked names on bare ATTRIBUTE ACCESS
    (``server.sse_app`` alone raised, before any call). A subclass cannot
    replicate that without reintroducing a ``__getattribute__`` override --
    i.e. becoming proxy-shaped again -- so this generation blocks on CALL
    only. Grabbing the bound method reference is harmless: the reference is
    itself bound to THIS guarded instance (see
    ``test_transport_guard_bound_method_self_bypass_is_closed`` below), so
    calling it later still raises."""

    server = mcp_server.build_server()
    fn = server.sse_app  # does not raise
    assert callable(fn)
    with pytest.raises(mcp_launcher.UnsupportedTransportError):
        fn()


# ---------------------------------------------------------------------------
# Generation 4 "F2-subclass" hardening: generations 1-3 were each a
# delegating PROXY wrapping a distinct, real ``FastMCP`` instance. Generation
# 3 (module-level ``WeakKeyDictionary``, ``__getattribute__`` override) was
# bypassed by Codex gpt-5.6-sol (2026-07-27) via
# ``server.list_tools.__self__.sse_app()``: every "safe" method the proxy
# delegated via ``getattr(wrapped, name)`` came back already bound to
# ``wrapped`` by Python's descriptor protocol, so its ``__self__`` was
# always the real, unguarded server -- no attribute-name denylist on the
# PROXY could ever inspect or block that, because the leak was not a named
# attribute of the proxy at all.
#
# This generation closes the bug CLASS: ``build_server()`` constructs a
# genuine ``FastMCP`` SUBCLASS (``mcp_launcher.stdio_only_fastmcp_class``)
# directly, so there is no second object anywhere. The tests below verify
# that property directly, plus the specific regression case (bound-method
# ``__self__``) that defeated generation 3.
# ---------------------------------------------------------------------------


def test_transport_guard_server_is_a_stdio_only_fastmcp_subclass() -> None:
    """``build_server()`` returns an instance of ``mcp_launcher.
    stdio_only_fastmcp_class(FastMCP)`` -- a real ``FastMCP`` (``isinstance``
    holds) whose own ``type()`` is the guarded subclass, not the plain
    ``FastMCP`` class the SDK ships."""

    server = mcp_server.build_server()
    guarded_cls = mcp_launcher.stdio_only_fastmcp_class(FastMCP)

    assert isinstance(server, FastMCP)
    assert type(server) is guarded_cls
    assert type(server) is not FastMCP
    assert type(server).__name__ == "_StdioOnlyFastMCP"
    assert hasattr(server, "run_stdio_async")


def test_transport_guard_bound_method_self_bypass_is_closed() -> None:
    """THE regression test for the Codex gpt-5.6-sol generation-3 bypass:
    ``server.list_tools.__self__.sse_app()`` (and the same pattern via
    ``call_tool``, ``add_tool``, ``tool``) must raise, because
    ``__self__`` on every one of these bound methods is ``server`` itself --
    there is no distinct wrapped object for it to be bound to instead."""

    server = mcp_server.build_server()

    for attr_name in ("list_tools", "call_tool", "add_tool", "tool"):
        bound = getattr(server, attr_name)
        assert bound.__self__ is server, (
            f"{attr_name}.__self__ is a distinct object from `server` -- "
            "the exact shape of the generation-3 bypass would reopen here"
        )
        with pytest.raises(mcp_launcher.UnsupportedTransportError):
            bound.__self__.sse_app()


def test_transport_guard_class_level_invocation_still_raises() -> None:
    """``type(server).sse_app(server)`` and ``server.__class__.sse_app(
    server)`` both resolve to THIS class's override (there is only one
    class in the picture), so both raise the guard error -- not
    ``AttributeError`` as they would have against generations 1-3's
    non-``FastMCP`` proxy class, which simply had no ``sse_app`` of its own."""

    server = mcp_server.build_server()

    assert type(server) is not FastMCP
    assert server.__class__ is not FastMCP
    with pytest.raises(mcp_launcher.UnsupportedTransportError):
        type(server).sse_app(server)
    with pytest.raises(mcp_launcher.UnsupportedTransportError):
        server.__class__.sse_app(server)


def test_transport_guard_no_wrapped_attribute_exists() -> None:
    """There is no ``_wrapped`` (or similarly-named) attribute holding a
    second, distinct server object -- unlike generations 1-2, this is not
    because such an attribute is deliberately blocked; it is because there
    is only ever one object, so nothing would ever assign one. ``vars(
    server)`` legitimately contains the real ``FastMCP`` instance state
    (``_tool_manager``, ``settings``, etc.) now, since this object both
    holds that state AND is the guarded server -- that is expected and is
    not a regression: none of that state is transport-related, and does not
    include an underlying-reference attribute."""

    server = mcp_server.build_server()

    for candidate in ("_wrapped", "__wrapped__", "wrapped", "_server", "_real_server", "_target"):
        assert getattr(server, candidate, "MISSING") == "MISSING", (
            f"unexpected reachable attribute {candidate!r} on the guarded server"
        )


def test_transport_guard_tool_registration_and_dispatch_still_work() -> None:
    """Functional smoke test: tools registered via ``@server.tool()`` in
    ``mcp_server.build_server()`` -- against the already-guarded subclass
    instance, from birth -- are genuinely present and listable. Proves the
    subclass swap doesn't disturb ordinary ``FastMCP`` operation."""

    import asyncio

    server = mcp_server.build_server()

    tools = asyncio.run(server.list_tools())
    tool_names = {tool.name for tool in tools}
    assert "search_run" in tool_names
    assert "extract_url" in tool_names
    assert callable(server.call_tool)
    assert callable(server.add_tool)
