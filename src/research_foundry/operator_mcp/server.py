"""Sole tool registry for `rf-operator-mcp` (M2 Leg B, OPM-5.1/5.2/5.4).

This module is the ONE place any `rf-operator-mcp` tool name is ever
registered. It imports only `research_foundry.services.operator_mcp_policy`
(the P1 contract/policy module) and `research_foundry.services.
operator_mcp_adapters` (the P3 closed adapter registry) -- never
`research_foundry.knowledge_mcp.*`, never `research_foundry.services.
search_router.*`, never `..integrations` (M2 contract hard boundary 2, D9
Leg B). It never imports Typer, `cli_commands`, `subprocess`, `os.system`,
or uses `shell=True` anywhere in its own call path (hard boundary 3).

**Offline-safe-import contract** (mirrors `knowledge_mcp/registry.py`):
this module imports cleanly without the optional `mcp` SDK installed. Only
:func:`build_server` touches it, and only lazily, raising a clear
:class:`RuntimeError` (naming the `mcp` extra) if it is missing.

**Closed, derived tool inventory (D4).** The registered tool set is
EXACTLY `operator_mcp_policy.TOOL_NAMES` (14 = the 13 `OPERATION_KINDS` +
`operation.preflight`), built by iterating that tuple -- no wildcard tool,
no dynamic registration path, no name rewriting. For each operation kind,
:func:`build_server` builds ONE thin handler that resolves the adapter via
`operator_mcp_adapters.get_adapter(kind)` and forwards every caller input
to `adapter.invoke(**kwargs)` unchanged; `input_payload`'s keys become that
adapter's own kind-specific keyword arguments (e.g. `intent_id`/`depth`/
`audience` for `run.plan`, `run_id`/`adapter_ids` for `swarm.start`) --
this mirrors `operator_mcp_operation.schema.yaml`'s own generic, bounded
`input_payload` envelope field exactly (`additionalProperties: true,
maxProperties: 32` -- the per-tool payload SHAPE is intentionally NOT
frozen at the transport layer; each adapter's own `invoke()` signature is
the true, already-frozen per-kind contract). `build_server()` RAISES at
build time if any `OPERATION_KINDS` member lacks a registered adapter --
never a silent, partial server (see the "Leg A/B integration" section
below for why this is expected to raise until `writeback.preview` lands).

**`operation.preflight` (D5).** The one server-IMPLEMENTED meta tool.
Builds a `PolicyContext` via `PolicyContext.for_configured_operator` (the
ONE sanctioned way to obtain a populated `identity` -- never caller-
supplied), runs `operator_mcp_policy.evaluate_policy`, and on an ALLOW
decision for a confirmation-requiring kind mints a confirmation via
`operator_mcp_policy.mint_confirmation` -- the EXACT same two functions
`tests/unit/test_operator_mcp_serve_extra_boundary.py::
test_evaluate_policy_and_mint_confirmation_run_without_serve_extra`
exercises. It NEVER calls `authorize_for_consumption`/
`consume_and_create_operation`/`run_or_replay` -- no operation manifest, no
receipt, no adapter action ever runs on this path (zero effect). Denials
return the standard `build_error` envelope; a `CONFIRMATION_NOT_REQUIRED_KINDS`
member (`job.status`) returns `{"allowed": True, "confirmation": None}`
without minting (a token that could never be verified would be misleading,
not merely inert).

`sensitivity_ceiling` is NEVER caller-suppliable here either (H7 doctrine,
identical to every P3 adapter) -- resolved via `operator_mcp_adapters.
resolve_local_sensitivity_ceiling(paths)`, the SAME public helper every P3
adapter entry point already calls. `identity` is likewise never caller-
suppliable (NEW-18 doctrine) -- resolved exclusively inside
`PolicyContext.for_configured_operator`.

`targets` IS accepted (optional) so a caller can preview/mint for a
target-bearing kind (e.g. `swarm.start`'s required `run` target) -- see the
D8 caller-input table in this task's completion note for the full judgment
call on how `resolved_target_workspaces` is resolved for this generic,
per-kind-domain-lookup-free preview tool, and why it is structurally safe
(`resolved_target_workspaces` is never part of the canonical digest or the
minted confirmation record -- confirmed against `PolicyContext.
canonical_payload()`'s own docstring and `mint_confirmation`'s record
construction -- so this preview-only resolution can never weaken the REAL
execute-time `authorize_operation()` a target-bearing kind's own adapter
independently reconstructs from real domain state).

**Transport error mapping (D7).** `_stdio_only_fastmcp_class`'s
`call_tool` override is the ONE dispatch chokepoint every real stdio
request AND every direct `server.call_tool(...)` call goes through
(confirmed against the installed SDK: `FastMCP.__init__` registers
`self.call_tool` -- the overridden bound method, resolved via normal
attribute lookup -- as the low-level protocol server's own `call_tool`
handler: `self._mcp_server.call_tool(...)(self.call_tool)`). It maps ONLY
the three transport-level failures D7
names -- unknown tool name (`operator_mcp_policy.check_tool_name`,
P5's own "FROZEN P5 OBLIGATION"), an oversized raw argument payload (a
transport-level short-circuit BEFORE any adapter/policy code runs; the
authoritative, bound `_check_capability` stage inside `evaluate_policy`
still runs later, per adapter, over that adapter's own narrowed
`ctx.input_payload` -- this is defense-in-depth, not a replacement), and
any unexpected exception raised while dispatching a registered tool
function -- ALL via `operator_mcp_policy.build_error`. Every
adapter-returned error envelope (already `build_error`-shaped, per
`OperatorAdapterResult.error`'s own contract) passes through this method
UNTOUCHED inside the `CallToolResult` `super().call_tool(...)` already
returns; this module adds NOTHING that could distinguish existence beyond
what that layer already returns (the H6 "one denial shape" guarantee).

**Dual encoding.** Every tool result places the identical core payload
dict in BOTH `structuredContent` and exactly one `content` block of
`{"type": "text", "text": "<canonical-json>"}` -- the SAME canonical-JSON
convention (`json.dumps(obj, ensure_ascii=False, separators=(",", ":"),
sort_keys=True)`) `knowledge_mcp/registry.py`'s own `_canonical_json`
uses, reimplemented by value here (this module never imports from
`knowledge_mcp`). Tools are registered with `structured_output=False` so
the SDK's own `convert_result` passes an explicitly-returned
`CallToolResult` straight through unmodified, exactly as `knowledge_mcp`
does.

**Leg A/B integration note (D10).** `writeback.preview` is Leg A's file
ownership (`operator_mcp_adapters/writeback_preview.py` +
`operator_mcp_adapters/__init__.py` registration). At the time this leg
was implemented, Leg A had not yet registered it
(`operator_mcp_adapters.get_adapter("writeback.preview")` returns `None`)
-- `build_server()`'s fail-loud check (D4) therefore RAISES today; this is
the CORRECT, expected behavior per D10, not a bug in this module. The
exact-14 inventory test (`tests/integration/test_operator_mcp_server.py`)
is written for the FULL, integrated 14-tool surface and will pass once
Leg A lands; it is left in place, not weakened, per the contract.

**Stdio-only transport guard (invariant 8).** `build_server` constructs a
genuine `FastMCP` SUBCLASS (`_stdio_only_fastmcp_class`) directly --
a subclass, not a delegating wrapper/proxy, so there is no second,
unguarded object for a bound method's `__self__` to resolve to instead
(the same bypass class `knowledge_mcp/registry.py`'s own docstring
documents and closes). This module reimplements that shape independently,
by value, rather than importing it, per this module's own import
boundary (never `knowledge_mcp.*`).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any, Literal

from research_foundry.errors import RFError
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_adapters as adapters
from research_foundry.services import operator_mcp_policy as policy

__all__ = ["UnsupportedTransportError", "build_server"]

logger = logging.getLogger(__name__)

_MISSING_SDK_MSG = (
    "The 'mcp' Python SDK is not installed. The Research Foundry Operator "
    "MCP server is an optional surface; install it with:\n"
    "    uv sync --extra mcp\n"
    "or\n"
    "    pip install 'research-foundry[mcp]'"
)

# Closed literal types for the two enum-shaped `operation.preflight`
# arguments (D4 "closed input schemas") -- built FROM the policy module's
# own frozen tuples (single source of truth), never a second, independently
# hand-typed enum that could drift. `evaluate_policy`'s own `_check_capability`
# stage remains the AUTHORITATIVE runtime check either way (see
# `_preflight_tool` below); these annotations only make the ADVERTISED
# `list_tools()` schema strict too.
_OperationKindLiteral = Literal[*policy.OPERATION_KINDS]  # type: ignore[valid-type]
_SensitivityLiteral = Literal[*policy.SENSITIVITY_LEVELS]  # type: ignore[valid-type]

# D7: cheap, EARLY transport-level short-circuit on raw argument size,
# BEFORE any adapter/policy code runs -- mirrors `operator_mcp_policy`'s own
# private `_MAX_INPUT_PAYLOAD_BYTES` bound BY VALUE, not import (this module
# never imports a private, underscore-prefixed symbol from
# `operator_mcp_policy` -- the same convention `operator_mcp_adapters/
# __init__.py` documents for its own `_CEILING_CONFIG_SECTION`/
# `_CEILING_CONFIG_KEY`). `_check_capability` inside `evaluate_policy`
# remains the AUTHORITATIVE, later bound check over each adapter's OWN
# narrowed `ctx.input_payload`; this is defense-in-depth, not a
# replacement, and its numeric value is free to drift independently of the
# authoritative one without weakening anything (a stricter or looser
# transport-level short-circuit only changes how EARLY an oversized
# request is rejected, never whether it eventually is).
_MAX_TRANSPORT_ARGUMENT_BYTES = 65_536

_ALLOWED_TRANSPORTS: tuple[str | None, ...] = (None, "stdio")

# Cache for :func:`_stdio_only_fastmcp_class`, keyed by the real
# `FastMCP` class it was derived from -- mirrors `knowledge_mcp/
# registry.py`'s own sentinel-cache pattern, reimplemented independently.
_cached_stdio_only_class: Any = None
_cached_stdio_only_base: Any = None


class UnsupportedTransportError(RFError):
    """Raised when a caller attempts to run `rf-operator-mcp` over a
    non-stdio transport (invariant 8) -- enforced at the code level, not
    only by convention. Mirrors `knowledge_mcp.registry.
    UnsupportedTransportError` in spirit but is NOT imported from it --
    this package never imports from `research_foundry.knowledge_mcp.*`."""


def _blocked_transport_message(name: str) -> str:
    return (
        f"{name}() is not supported by rf-operator-mcp. stdio is the only enforced "
        "transport (invariant 8). This server is a FastMCP SUBCLASS constructed "
        "directly by build_server(), not a delegating proxy -- there is no distinct "
        "wrapped instance for any bound method's __self__ to resolve to instead."
    )


def _canonical_json(payload: Mapping[str, Any]) -> str:
    """Same canonical-JSON convention `knowledge_mcp/registry.py`'s own
    `_canonical_json` uses -- reimplemented by value, not import."""

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _build_dual_encoder(call_tool_result_cls: Any, text_content_cls: Any) -> Any:
    """Return a `(payload, *, is_error=False) -> CallToolResult` closure
    bound to the SDK's real `CallToolResult`/`TextContent` classes -- both
    `_stdio_only_fastmcp_class`'s `call_tool` override and `build_server`'s
    own tool handlers build one of these from their OWN lazy `mcp.types`
    import (each only ever invoked after that import already succeeded),
    rather than importing `mcp.types` at this module's top level."""

    def _dual_encode(payload: Mapping[str, Any], *, is_error: bool = False) -> Any:
        return call_tool_result_cls(
            content=[text_content_cls(type="text", text=_canonical_json(payload))],
            structuredContent=dict(payload),
            isError=is_error,
        )

    return _dual_encode


def _check_transport_payload_size(arguments: Mapping[str, Any]) -> policy.PolicyDecision | None:
    """`None` when `arguments` is within the transport-level bound;
    otherwise a `payload_too_large` denial. See this module's docstring's
    "Transport error mapping" section."""

    try:
        size = len(
            json.dumps(
                dict(arguments), ensure_ascii=False, separators=(",", ":"), sort_keys=True, default=str
            ).encode("utf-8")
        )
    except (TypeError, ValueError):
        # Not even measurable -- let the real dispatch attempt run; a
        # genuinely malformed argument mapping will fail there too, mapped
        # to internal_error by the SAME call_tool override's outer
        # try/except.
        return None
    if size > _MAX_TRANSPORT_ARGUMENT_BYTES:
        return policy.PolicyDecision(False, "capability", "payload_too_large", retryable=False)
    return None


def _stdio_only_fastmcp_class(fastmcp_cls: type[Any]) -> type[Any]:
    """Return the `_StdioOnlyFastMCP` subclass of `fastmcp_cls` (cached).
    See this module's docstring's "Stdio-only transport guard" and
    "Transport error mapping" sections. Mirrors `knowledge_mcp/registry.py`'s
    own `_stdio_only_fastmcp_class` shape by value, not import."""

    global _cached_stdio_only_class, _cached_stdio_only_base
    if _cached_stdio_only_class is not None and _cached_stdio_only_base is fastmcp_cls:
        return _cached_stdio_only_class

    from mcp.types import CallToolResult, TextContent  # type: ignore[import-not-found]

    dual_encode = _build_dual_encoder(CallToolResult, TextContent)

    class _StdioOnlyFastMCP(fastmcp_cls):  # type: ignore[misc]
        """`FastMCP` restricted to the `stdio` transport (invariant 8),
        with the D7 transport-error-mapping chokepoint (`call_tool`)."""

        def sse_app(self, mount_path: str | None = None) -> Any:
            raise UnsupportedTransportError(_blocked_transport_message("sse_app"))

        def streamable_http_app(self) -> Any:
            raise UnsupportedTransportError(_blocked_transport_message("streamable_http_app"))

        # Deliberately NOT `async def` -- see `knowledge_mcp/registry.py`'s
        # identical override for why a plain function raises strictly
        # earlier than an `async def` override would (the call itself
        # raises before there is ever a coroutine object left to await).
        def run_sse_async(self, mount_path: str | None = None) -> None:
            raise UnsupportedTransportError(_blocked_transport_message("run_sse_async"))

        def run_streamable_http_async(self) -> None:
            raise UnsupportedTransportError(_blocked_transport_message("run_streamable_http_async"))

        def run(self, transport: str | None = "stdio", mount_path: str | None = None) -> None:
            if transport not in _ALLOWED_TRANSPORTS:
                raise UnsupportedTransportError(
                    f"Non-stdio MCP transport {transport!r} is not supported by "
                    "rf-operator-mcp (invariant 8). Direct network-transport mounts "
                    "(sse/streamable-http) are refused at the code level, not only by "
                    "convention."
                )
            super().run(transport=transport or "stdio", mount_path=mount_path)  # type: ignore[misc]

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
            """D7's ONE dispatch chokepoint -- every real stdio request AND
            every direct `server.call_tool(...)` test call goes through
            this method (`FastMCP.__init__` registers the OVERRIDDEN bound
            method -- `self._mcp_server.call_tool(...)(self.call_tool)` --
            as the low-level protocol server's own handler; confirmed
            against the installed 1.x SDK's source)."""

            name_decision = policy.check_tool_name(name)
            if name_decision.denied:
                return dual_encode(policy.build_error(name_decision), is_error=True)

            size_decision = _check_transport_payload_size(arguments or {})
            if size_decision is not None:
                return dual_encode(policy.build_error(size_decision), is_error=True)

            try:
                return await super().call_tool(name, arguments)  # type: ignore[misc]
            except Exception as exc:  # noqa: BLE001 -- the ONE D7 internal_error boundary
                logger.warning(
                    "operator_mcp.server: internal_error dispatching tool %r (%s)",
                    name,
                    type(exc).__name__,
                )
                decision = policy.PolicyDecision(False, "capability", "internal_error", retryable=True)
                return dual_encode(policy.build_error(decision), is_error=True)

    _cached_stdio_only_class = _StdioOnlyFastMCP
    _cached_stdio_only_base = fastmcp_cls
    return _StdioOnlyFastMCP


def _close_input_schema(server: Any, name: str) -> None:
    """Best-effort tightening of one registered tool's ADVERTISED input
    schema to `additionalProperties: false` (D4) -- mirrors `knowledge_mcp/
    registry.py`'s own `_close_input_schema` by value, not import.
    Intentionally best-effort (guarded by `AttributeError`/`KeyError`)
    against the SDK's own internal `_tool_manager`/`Tool.parameters` shape
    ever changing; correct denial behavior never depends on it succeeding
    (the real, authoritative bound checks are `_check_capability` and each
    adapter's own `invoke()` signature, both unaffected by this schema
    annotation)."""

    try:
        tool = server._tool_manager.get_tool(name)
        if tool is not None:
            tool.parameters = {**tool.parameters, "additionalProperties": False}
    except (AttributeError, KeyError):  # pragma: no cover - defensive only
        logger.debug("Could not tighten input schema for tool %r (SDK internals changed).", name)


def build_server(paths: FoundryPaths | None = None) -> Any:
    """Construct and return a guarded, stdio-only `FastMCP` server with the
    exact 14-tool inventory registered (D4): the 13 `OPERATION_KINDS`, each
    a thin dispatch to `operator_mcp_adapters.get_adapter(kind)`, plus the
    server-implemented `operation.preflight` meta tool (D5).

    Lazily imports the `mcp` SDK; raises :class:`RuntimeError` with a clear
    install hint if it is missing (see :data:`_MISSING_SDK_MSG`). Raises a
    DIFFERENT, equally clear :class:`RuntimeError` if any `OPERATION_KINDS`
    member lacks a registered adapter (D4's fail-loud, no-silent-partial-
    server guarantee) -- see this module's docstring's "Leg A/B integration
    note" for why this is EXPECTED today (`writeback.preview` not yet
    registered by Leg A).

    ``paths`` defaults to :meth:`FoundryPaths.discover` when omitted; tests
    pass an explicit :class:`FoundryPaths` pointed at a fixture workspace.
    """

    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]
    except ImportError as exc:  # noqa: BLE001 - re-raise as a clear runtime error
        raise RuntimeError(_MISSING_SDK_MSG) from exc

    from mcp.types import CallToolResult, TextContent  # type: ignore[import-not-found]

    resolved_paths = paths if paths is not None else FoundryPaths.discover()

    missing = [kind for kind in policy.OPERATION_KINDS if adapters.get_adapter(kind) is None]
    if missing:
        raise RuntimeError(
            "operator_mcp.server.build_server: missing adapter registration for "
            f"operation kind(s) {missing!r} -- every member of "
            "operator_mcp_policy.OPERATION_KINDS must be registered in "
            "operator_mcp_adapters before this server can be built (D4: no "
            "silent, partial 13/14-tool server, ever)."
        )

    StdioOnlyFastMCP = _stdio_only_fastmcp_class(FastMCP)
    server = StdioOnlyFastMCP("rf-operator-mcp")

    dual_encode = _build_dual_encoder(CallToolResult, TextContent)

    def _adapter_result_payload(outcome: Any) -> dict[str, Any]:
        return {"ok": bool(outcome.ok), "operation_id": outcome.operation_id, "result": outcome.result}

    def _make_operation_tool(kind: str) -> Any:
        def _operation_tool(
            idempotency_key: str,
            input_payload: dict[str, Any] | None = None,
            confirmation_record: dict[str, Any] | None = None,
            presented_token: str | None = None,
            dry_run: bool = False,
        ) -> Any:
            adapter = adapters.get_adapter(kind)
            if adapter is None:  # pragma: no cover - build_server's own fail-loud check makes this unreachable
                decision = policy.PolicyDecision(False, "capability", "operation_unknown", retryable=False)
                return dual_encode(policy.build_error(decision), is_error=True)
            outcome = adapter.invoke(
                idempotency_key=idempotency_key,
                confirmation_record=confirmation_record,
                presented_token=presented_token,
                dry_run=dry_run,
                paths=resolved_paths,
                **(input_payload or {}),
            )
            if not outcome.ok:
                # D7: adapter-returned error envelopes pass through
                # UNTOUCHED -- outcome.error is already a build_error-built
                # operator_mcp_error instance; this handler adds nothing.
                return dual_encode(dict(outcome.error or {}), is_error=True)
            return dual_encode(_adapter_result_payload(outcome), is_error=False)

        _operation_tool.__name__ = kind.replace(".", "_").replace("-", "_")
        _operation_tool.__doc__ = (
            f"Operator MCP `{kind}` tool (M2, OPM-5.1/5.2/5.4). Thin dispatch to "
            "`operator_mcp_adapters.get_adapter(kind).invoke(**kwargs)` -- "
            "`input_payload`'s keys become that adapter's own kind-specific "
            "keyword arguments. Every caller input flows through the SAME "
            "P1-P3 authorize -> consume -> execute pipeline this transport "
            "does not modify."
        )
        return _operation_tool

    for _kind in policy.OPERATION_KINDS:
        server.tool(name=_kind, structured_output=False)(_make_operation_tool(_kind))

    def _preflight_tool(
        operation_kind: _OperationKindLiteral,
        idempotency_key: str,
        effective_sensitivity: _SensitivityLiteral,
        targets: list[dict[str, str]] | None = None,
        input_payload: dict[str, Any] | None = None,
        policy_snapshot_version: str = "policy-order-v1",
    ) -> Any:
        """`operation.preflight` -- evaluate + mint, never consume, zero
        effect. See this module's docstring's "operation.preflight"
        section for the full contract."""

        if operation_kind not in policy.OPERATION_KINDS:  # defense in depth; schema already restricts this
            decision = policy.PolicyDecision(False, "capability", "operation_unknown", retryable=False)
            return dual_encode(policy.build_error(decision), is_error=True)

        target_refs: list[policy.TargetRef] = []
        for raw_target in targets or []:
            kind_value = raw_target.get("target_kind") if isinstance(raw_target, dict) else None
            ref_value = raw_target.get("target_ref") if isinstance(raw_target, dict) else None
            if not isinstance(kind_value, str) or not isinstance(ref_value, str):
                decision = policy.PolicyDecision(False, "capability", "target_invalid", retryable=False)
                return dual_encode(policy.build_error(decision), is_error=True)
            target_refs.append(policy.TargetRef(kind_value, ref_value))

        # Judgment call -- see this module's docstring's "operation.preflight"
        # section and this task's completion note (D8 table): every
        # declared target's `resolved_target_workspaces` entry is resolved
        # OPTIMISTICALLY to the operator's OWN `identity.workspace_id`
        # (never caller-supplied). Structurally safe: `resolved_target_
        # workspaces` is excluded from `PolicyContext.canonical_payload()`
        # and from `mint_confirmation`'s own record construction, so this
        # preview-only guess can never weaken the REAL execute-time
        # `authorize_operation()` a target-bearing kind's own adapter
        # independently reconstructs from real domain state.
        preview_identity = policy.resolve_operator_identity(resolved_paths)
        workspace_guess = preview_identity.workspace_id if preview_identity is not None else None
        resolved_target_workspaces = tuple(workspace_guess for _ in target_refs)

        ctx = policy.PolicyContext.for_configured_operator(
            operation_kind=operation_kind,
            idempotency_key=idempotency_key,
            effective_sensitivity=effective_sensitivity,
            sensitivity_ceiling=adapters.resolve_local_sensitivity_ceiling(resolved_paths),
            targets=tuple(target_refs),
            resolved_target_workspaces=resolved_target_workspaces,
            input_payload=input_payload or {},
            policy_snapshot_version=policy_snapshot_version,
            paths=resolved_paths,
        )

        decision = policy.evaluate_policy(ctx, paths=resolved_paths)
        if decision.denied:
            return dual_encode(policy.build_error(decision), is_error=True)

        if operation_kind in policy.CONFIRMATION_NOT_REQUIRED_KINDS:
            return dual_encode({"allowed": True, "confirmation": None}, is_error=False)

        issued = policy.mint_confirmation(ctx, paths=resolved_paths)
        return dual_encode(
            {"allowed": True, "confirmation": {"token": issued.token, "record": issued.record}},
            is_error=False,
        )

    server.tool(name=policy.PREFLIGHT_TOOL_NAME, structured_output=False)(_preflight_tool)

    for _name in policy.TOOL_NAMES:
        _close_input_schema(server, _name)

    # `server` is already a `_StdioOnlyFastMCP` instance (constructed
    # above, before any `@server.tool()`-equivalent registration) -- no
    # separate wrap/guard step is needed or performed here.
    return server
