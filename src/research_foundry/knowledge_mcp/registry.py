"""Sole tool registry for `rf-knowledge-mcp` (KMCP-4.1/4.2).

This module is the ONE place any `rf-knowledge-mcp` tool name is ever
registered (decisions-block §9.1). It imports only from
:mod:`research_foundry.services.knowledge_access` (the governed P2/P3 read
service) and shared read-only substrate (:mod:`research_foundry.paths`,
:mod:`research_foundry.errors`) -- never a provider client, job runner,
acquisition/import/writeback service, or the Search Router's own registry
module (`research_foundry.services.search_router.*`, never imported here).

**Offline-safe-import contract** (mirrors
`search_router.mcp_server`/`mcp_launcher`): this module itself imports
cleanly without the optional `mcp` SDK installed. Only :func:`build_server`
touches it, and only lazily, raising a clear :class:`RuntimeError` (naming
the `mcp` extra) if it is missing.

**Scope of this task (KMCP-4.1/4.2 "Part A" + KMCP-4.3 "Part B").** Registers
the exact eight-tool inventory (decisions-block §9.2): the two CORE tools,
`search` and `fetch`, with the frozen input/output shapes from
`schemas/knowledge_search_request.schema.yaml`,
`schemas/knowledge_search_response.schema.yaml`, and
`schemas/knowledge_document.schema.yaml`; plus the six RF-extended tools --
`rf_search`/`rf_fetch` (validated filters/paging/receipts over
:meth:`knowledge_access.KnowledgeAccessService.search_extended` /
:meth:`fetch_extended`) and the four typed getters `rf_source_get`/
`rf_assertion_get`/`rf_report_get`/`rf_run_get` (each a THIN
:meth:`fetch_extended` call additionally scoped to its own kind -- see
"Typed getter kind scoping" below). :data:`CORE_TOOL_NAMES`/
:data:`RF_TOOL_NAMES`/:data:`TOOL_NAMES` (reused, not redefined, from
:mod:`knowledge_access`) are this module's own inventory truth.

**Typed getter kind scoping (KMCP-4.3).** `rf_source_get`/`rf_assertion_get`/
`rf_run_get` each accept only an id whose opaque-id kind segment is exactly
their own kind (`source`/`assertion`/`run`); `rf_report_get` accepts either
`report_draft` OR `report_final` (KMCP-OQ-2 -- two distinct kinds, one
getter name). An id of the WRONG kind for a given getter denies with the
SAME generic message :data:`_FETCH_DENIED_MESSAGE` as a missing id --
never a distinguishing "wrong kind" signal (mirrors
:class:`knowledge_access.ReportKindProjector`'s own mismatched-kind-id
contract, generalized to every typed getter). The kind check happens via
:func:`knowledge_access.parse_knowledge_id` BEFORE any
:meth:`fetch_extended` call, so a wrong-kind id never even reaches its
governed read authority.

**Local-trust caveat: `rf_assertion_get` always denies (KMCP-4.1).** This
process's `_context` helper below always resolves
`identity=None` ("local trust" -- see `settings.py`'s module docstring: this
stdio transport has no separate remote auth in v1). Every assertion read
(:class:`knowledge_access.AssertionKindProjector`'s
`search_read_only`/`packet_read_only` calls) unconditionally requires a
non-`None` identity with a workspace id -- this is an assertion-catalog
invariant, not gated by the WKSP-304 isolation flag. Consequently `search`/
`rf_search` never return an `assertion`-kind result and `rf_assertion_get`
denies generically for EVERY id through this local stdio process, until
P5 (CLI/API parity) or a future identity-bearing transport threads a real
identity through. This is expected v1 behavior, not a bug.

**Dual encoding (KMCP-1.3).** Every tool result places the identical core
DTO dict in BOTH ``structuredContent`` and exactly one ``content`` block of
``{"type": "text", "text": "<canonical-json>"}`` -- the SAME
`json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True)`
convention `assertion_identity.canonical_source_assertion_json` and
`knowledge_access._canonical_json` already use (reimplemented by value
below, not imported, to keep this module's import graph limited to the
substrate named above). This is done by hand -- constructing an explicit
``mcp.types.CallToolResult`` and returning it directly from each tool
function -- rather than relying on FastMCP's own automatic
signature-derived structured-output conversion, which uses indented,
insertion-ordered JSON (`pydantic_core.to_json`), not this repo's
canonical-JSON convention, for its auto-generated text block. Tools are
registered with ``structured_output=False`` so FastMCP's
``convert_result`` passes an explicitly-returned ``CallToolResult`` straight
through unmodified (see ``mcp.server.fastmcp.utilities.func_metadata.
FuncMetadata.convert_result``).

**Safe denial (decisions-block §0/§3 Risk 2, KMCP-OQ-1).** `search` never
raises for a policy denial -- a hidden/denied/missing record simply never
contributes to `results`, so a query with zero eligible matches returns the
same `{"results": []}` shape a query with zero hidden-but-existing matches
would (`knowledge_access._search`'s own per-kind projector contract already
guarantees this; this module never has to distinguish the two cases
itself). `fetch` maps EVERY :class:`knowledge_access.KnowledgeAccessError`
(malformed id, missing, hidden, cross-workspace, rights-denied, stale
projection -- all indistinguishable by exception type, per
`knowledge_access.parse_knowledge_id`'s and `KnowledgeDenied`'s own
docstrings) to the SAME generic, detail-free MCP tool error
(:data:`_FETCH_DENIED_MESSAGE`) -- the exception's own internal ``reason``
string is never rendered into a response. `rf_search` mirrors `search`'s
contract exactly (any :class:`knowledge_access.KnowledgeAccessError`
collapses to the SAME empty `RfKnowledgeSearchOutcome` shape, with no
`receipt` -- a receipt is never built for a denied/errored call). `rf_fetch`
and all four typed getters (`rf_source_get`/`rf_assertion_get`/
`rf_report_get`/`rf_run_get`) mirror `fetch`'s contract exactly, including
reusing the SAME :data:`_FETCH_DENIED_MESSAGE` -- a caller can never tell a
missing id, a hidden id, a cross-kind id (see "Typed getter kind scoping"
above), or an assertion-kind id denied by the local-trust caveat apart from
one another.

**Process bootstrap (KMCP-4.1).** The four concrete P3 domain projectors
(`SourceKindProjector`, `AssertionKindProjector`, `ReportKindProjector` x2,
`RunKindProjector`) are registered into `knowledge_access`'s shared,
process-global projector registry by :func:`_bootstrap_projectors`, called
once per :func:`build_server` invocation, bound to THIS process's resolved
`FoundryPaths`. Without this, `search`/`fetch` would only ever exercise the
P2 skeleton's own "no projector registered" exit condition (empty
results/`projection_unavailable` denial for every kind) -- `register_projector`
is otherwise only ever called by test fixtures today. Overwriting on every
call is intentional and cheap (a plain dict assignment); it is what makes
repeated `build_server()` calls against a different `paths` (e.g. across
test cases) behave correctly rather than leaking a stale workspace binding.

**Stdio-only transport guard (invariant 8).** :func:`build_server`
constructs a genuine ``FastMCP`` SUBCLASS (:func:`_stdio_only_fastmcp_class`)
directly, exactly like `search_router.mcp_server.build_server` /
`mcp_launcher.stdio_only_fastmcp_class`'s own "generation 4" design -- a
subclass, not a delegating wrapper/proxy, so there is no second, unguarded
object for a bound method's ``__self__`` to resolve to instead (the exact
bypass class that module's own docstring documents and closes across three
earlier generations). This module reimplements that SAME shape
independently, by value, rather than importing it, per invariant 1 (this
package never imports from `research_foundry.services.search_router.*`).
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any

from research_foundry.errors import RFError
from research_foundry.paths import FoundryPaths
from research_foundry.services import knowledge_access as ka

from .settings import KnowledgeMcpSettings, resolve_settings

__all__ = [
    "CORE_TOOL_NAMES",
    "RF_TOOL_NAMES",
    "TOOL_NAMES",
    "UnsupportedTransportError",
    "build_server",
]

logger = logging.getLogger(__name__)

# Reused, not redefined, from the governed service -- the SAME tuples KMCP-4.4
# snapshots as its negative-space guard (see module docstring).
CORE_TOOL_NAMES: tuple[str, ...] = ka.CORE_TOOL_NAMES
RF_TOOL_NAMES: tuple[str, ...] = ka.RF_TOOL_NAMES
TOOL_NAMES: tuple[str, ...] = ka.TOOL_NAMES

_MISSING_SDK_MSG = (
    "The 'mcp' Python SDK is not installed. The Research Foundry Knowledge "
    "MCP server is an optional surface; install it with:\n"
    "    uv sync --extra mcp\n"
    "or\n"
    "    pip install 'research-foundry[mcp]'"
)

# Single, generic, detail-free denial message for every `fetch` failure
# (decisions-block §0/§3 Risk 2) -- never derived from an exception's own
# `reason` string. See module docstring's "Safe denial" section.
_FETCH_DENIED_MESSAGE = "Unable to fetch the requested knowledge id."


def _canonical_json(payload: Mapping[str, Any]) -> str:
    """Same canonical-JSON convention as
    `assertion_identity.canonical_source_assertion_json` /
    `knowledge_access._canonical_json` (KMCP-1.3) -- reused by value, not
    import, per this module's own import-boundary docstring."""

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _bootstrap_projectors(paths: FoundryPaths) -> None:
    """Wire the concrete P3 domain projectors into `knowledge_access`'s
    shared registry for THIS process's workspace (see module docstring's
    "Process bootstrap" section)."""

    ka.register_projector("source", ka.SourceKindProjector(paths))
    ka.register_projector("assertion", ka.AssertionKindProjector(paths))
    ka.register_projector("report_draft", ka.ReportKindProjector(paths, target_kind="report_draft"))
    ka.register_projector("report_final", ka.ReportKindProjector(paths, target_kind="report_final"))
    ka.register_projector("run", ka.RunKindProjector(paths))


def _close_input_schema(server: Any, name: str) -> None:
    """Best-effort tightening of one registered tool's ADVERTISED input
    schema to `additionalProperties: false` (frozen core roots, KMCP-1.2).

    FastMCP's own signature-derived pydantic argument model silently ignores
    (rather than rejecting) an unrecognized property at call time -- a
    limitation of the installed SDK version, not a widened capability (an
    ignored extra key never reaches, or does anything for, the tool
    function). This helper only aligns the schema a client sees via
    `list_tools()` with the frozen contract; it is intentionally best-effort
    (guarded by `AttributeError`/`KeyError`) against the SDK's own internal
    `_tool_manager`/`Tool.parameters` shape ever changing, since correct
    behavior never depends on it succeeding.
    """

    try:
        tool = server._tool_manager.get_tool(name)
        if tool is not None:
            tool.parameters = {**tool.parameters, "additionalProperties": False}
    except (AttributeError, KeyError):  # pragma: no cover - defensive only
        logger.debug("Could not tighten input schema for tool %r (SDK internals changed).", name)


class UnsupportedTransportError(RFError):
    """Raised when a caller attempts to run `rf-knowledge-mcp` over a
    non-stdio transport (invariant 8) -- enforced at the code level, not
    only by convention. Mirrors
    `search_router.mcp_launcher.UnsupportedTransportError` in spirit but is
    NOT imported from it -- this package never imports from
    `research_foundry.services.search_router.*` (invariant 1)."""


_BLOCKED_TRANSPORT_METHODS: frozenset[str] = frozenset(
    {"sse_app", "streamable_http_app", "run_sse_async", "run_streamable_http_async"}
)
_ALLOWED_TRANSPORTS: tuple[str | None, ...] = (None, "stdio")

# Cache for :func:`_stdio_only_fastmcp_class`, keyed by the real `FastMCP`
# class it was derived from -- mirrors `mcp_launcher`'s own sentinel-cache
# pattern, reimplemented independently (see module docstring, invariant 1).
_cached_stdio_only_class: Any = None
_cached_stdio_only_base: Any = None


def _blocked_transport_message(name: str) -> str:
    return (
        f"{name}() is not supported by rf-knowledge-mcp. stdio is the only enforced "
        "transport (invariant 8). This server is a FastMCP SUBCLASS constructed "
        "directly by build_server(), not a delegating proxy -- there is no distinct "
        "wrapped instance for any bound method's __self__ to resolve to instead."
    )


def _stdio_only_fastmcp_class(fastmcp_cls: type[Any]) -> type[Any]:
    """Return the `_StdioOnlyFastMCP` subclass of `fastmcp_cls` (cached).

    A genuine subclass, not a wrapper or proxy -- see the module docstring's
    "Stdio-only transport guard" section for why that is the property that
    closes the bound-method `__self__` bypass the Search Router's own
    `mcp_launcher` module documents across its first three guard
    generations. Every override below lives directly on this class, and
    :func:`build_server` constructs THIS class (never the plain `FastMCP`),
    so there is no second object anywhere for a bound method, `type()`, or
    `__class__` access to resolve to instead.
    """

    global _cached_stdio_only_class, _cached_stdio_only_base
    if _cached_stdio_only_class is not None and _cached_stdio_only_base is fastmcp_cls:
        return _cached_stdio_only_class

    class _StdioOnlyFastMCP(fastmcp_cls):  # type: ignore[misc]
        """`FastMCP` restricted to the `stdio` transport (invariant 8)."""

        def sse_app(self, mount_path: str | None = None) -> Any:
            raise UnsupportedTransportError(_blocked_transport_message("sse_app"))

        def streamable_http_app(self) -> Any:
            raise UnsupportedTransportError(_blocked_transport_message("streamable_http_app"))

        # Deliberately NOT `async def` -- see `mcp_launcher`'s identical
        # override for why a plain function raises strictly earlier than an
        # `async def` override would (the call itself raises before there is
        # ever a coroutine object left to await).
        def run_sse_async(self, mount_path: str | None = None) -> None:
            raise UnsupportedTransportError(_blocked_transport_message("run_sse_async"))

        def run_streamable_http_async(self) -> None:
            raise UnsupportedTransportError(_blocked_transport_message("run_streamable_http_async"))

        def run(self, transport: str | None = "stdio", mount_path: str | None = None) -> None:
            if transport not in _ALLOWED_TRANSPORTS:
                raise UnsupportedTransportError(
                    f"Non-stdio MCP transport {transport!r} is not supported by "
                    "rf-knowledge-mcp (invariant 8). Direct network-transport mounts "
                    "(sse/streamable-http) are refused at the code level, not only by "
                    "convention."
                )
            super().run(transport=transport or "stdio", mount_path=mount_path)  # type: ignore[misc]

    _cached_stdio_only_class = _StdioOnlyFastMCP
    _cached_stdio_only_base = fastmcp_cls
    return _StdioOnlyFastMCP


def build_server(settings: KnowledgeMcpSettings | None = None) -> Any:
    """Construct and return a guarded, stdio-only `FastMCP` server with the
    exact eight-tool inventory registered: the two CORE tools (`search`,
    `fetch`) and the six RF-extended tools (`rf_search`, `rf_fetch`,
    `rf_source_get`, `rf_assertion_get`, `rf_report_get`, `rf_run_get`)
    (KMCP-4.1/4.2/4.3).

    Lazily imports the `mcp` SDK; raises :class:`RuntimeError` with a clear
    install hint if it is missing (see :data:`_MISSING_SDK_MSG`). Returning
    the server object (rather than running it) keeps this function
    unit-testable once the SDK is available -- mirrors
    `search_router.mcp_server.build_server`'s own contract.

    ``settings`` defaults to :func:`.settings.resolve_settings` when
    omitted; tests pass an explicit :class:`KnowledgeMcpSettings` pointed at
    a fixture workspace instead of relying on environment/cwd discovery.
    """

    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]
    except ImportError as exc:  # noqa: BLE001 - re-raise as a clear runtime error
        raise RuntimeError(_MISSING_SDK_MSG) from exc

    from mcp.types import CallToolResult, TextContent  # type: ignore[import-not-found]

    resolved_settings = settings if settings is not None else resolve_settings()
    _bootstrap_projectors(resolved_settings.paths)
    service = ka.KnowledgeAccessService(resolved_settings.paths)

    StdioOnlyFastMCP = _stdio_only_fastmcp_class(FastMCP)
    server = StdioOnlyFastMCP("rf-knowledge-mcp")

    def _context(tool: str) -> ka.KnowledgeAccessContext:
        return ka.resolve_context(
            resolved_settings.paths,
            tool=tool,
            identity=None,
            sensitivity_threshold=resolved_settings.sensitivity_threshold_max,
        )

    def _dual_encode(payload: dict[str, Any]) -> Any:
        return CallToolResult(
            content=[TextContent(type="text", text=_canonical_json(payload))],
            structuredContent=payload,
        )

    # --- core tools (KMCP-1.2 frozen shapes) --------------------------------

    @server.tool(structured_output=False)
    def search(query: str) -> Any:
        """Frozen core `search(query)` (KMCP-1.2) -- exactly one input field.

        Returns the exact core `SearchDTO`: `{"results": [{id, title, url},
        ...]}`, at most 10 items, each snippet-free (no `kind`/`rank`/
        `score`/`snippet` -- those exist only in the separately-named
        `rf_search` extension below). A policy-hidden or genuinely absent
        match never distinguishably affects this result -- both collapse to
        the same `results: []`-shaped outcome (see module docstring's "Safe
        denial" section).
        """

        try:
            response = service.search_core(_context("search"), query=query)
        except ka.KnowledgeAccessError:
            # Every service-side access error -- a malformed query
            # (`KnowledgeRequestError`) included -- collapses to the same
            # empty-results shape, never an MCP tool error, for a
            # search-shaped call (decisions-block §0/§3 Risk 2).
            return _dual_encode(ka.KnowledgeSearchResponse().to_dict())
        return _dual_encode(response.to_dict())

    @server.tool(structured_output=False)
    def fetch(id: str) -> Any:
        """Frozen core `fetch(id)` (KMCP-1.2) -- exactly one input field.

        Returns the exact core `FetchDTO`: required `id`/`title`/`text`/
        `url` plus optional generic `metadata`. Every denial cause --
        malformed id, missing, hidden, cross-workspace, rights-denied, or a
        stale/unavailable projection -- maps to the SAME generic MCP tool
        error (`isError=True`, :data:`_FETCH_DENIED_MESSAGE`); the
        exception's own internal `reason` is never rendered (see module
        docstring's "Safe denial" section).
        """

        try:
            document = service.fetch_core(_context("fetch"), knowledge_id=id)
        except ka.KnowledgeAccessError:
            return CallToolResult(
                isError=True,
                content=[TextContent(type="text", text=_FETCH_DENIED_MESSAGE)],
            )
        return _dual_encode(document.to_dict())

    # --- RF-extended tools (KMCP-4.3; KMCP-FR-5) ----------------------------

    def _fetch_denied() -> Any:
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=_FETCH_DENIED_MESSAGE)],
        )

    @server.tool(structured_output=False)
    def rf_search(
        query: str,
        kinds: list[str] | None = None,
        limit: int = ka.RF_SEARCH_DEFAULT_LIMIT,
        cursor: str | None = None,
        parent_run_ref: str | None = None,
    ) -> Any:
        """RF-extended `rf_search` (KMCP-FR-5) -- thin call to
        :meth:`knowledge_access.KnowledgeAccessService.search_extended`.

        Adds the optional `kinds` allowlist (narrows, never widens,
        eligibility -- `knowledge_access.eligible_kinds`), `limit`/`cursor`
        paging, and a caller-carried, non-persisted RF activity receipt
        (`include_receipt=True` always, for this tool). Each result item
        carries `kind`/`snippet`/`rank`/`score`/`content_is_untrusted` --
        every field the core `search` result intentionally omits (invariant
        5). Denial contract identical to `search` (see module docstring's
        "Safe denial" section): any
        :class:`knowledge_access.KnowledgeAccessError` collapses to the same
        empty, receipt-less outcome a zero-match query would produce.
        """

        try:
            outcome = service.search_extended(
                _context("rf_search"),
                query=query,
                kinds=kinds,
                limit=limit,
                cursor=cursor,
                parent_run_ref=parent_run_ref,
                include_receipt=True,
            )
        except ka.KnowledgeAccessError:
            return _dual_encode(ka.RfKnowledgeSearchOutcome().to_dict())
        return _dual_encode(outcome.to_dict())

    @server.tool(structured_output=False)
    def rf_fetch(id: str, cursor: str | None = None, parent_run_ref: str | None = None) -> Any:
        """RF-extended `rf_fetch` (KMCP-FR-5) -- thin call to
        :meth:`knowledge_access.KnowledgeAccessService.fetch_extended`.

        Adds cursor-based text paging, the typed per-kind `rf_metadata` bag,
        `original_source_url` (when policy allows one), and a caller-carried
        receipt (`include_receipt=True` always). Denial contract identical
        to `fetch` -- see module docstring's "Safe denial" section.
        """

        try:
            document = service.fetch_extended(
                _context("rf_fetch"),
                knowledge_id=id,
                cursor=cursor,
                parent_run_ref=parent_run_ref,
                include_receipt=True,
            )
        except ka.KnowledgeAccessError:
            return _fetch_denied()
        return _dual_encode(document.to_dict())

    def _typed_get(
        tool: str,
        expected_kinds: frozenset[str],
        *,
        id: str,
        cursor: str | None,
        parent_run_ref: str | None,
    ) -> Any:
        """Shared body for every typed getter (see module docstring's "Typed
        getter kind scoping" section) -- a THIN `fetch_extended` call
        additionally gated to `expected_kinds`, checked via
        :func:`knowledge_access.parse_knowledge_id` BEFORE the underlying
        governed read authority is ever touched."""

        try:
            resolved_kind, _opaque = ka.parse_knowledge_id(id)
            if resolved_kind not in expected_kinds:
                raise ka.KnowledgeDenied("kind_not_eligible")
            document = service.fetch_extended(
                _context(tool),
                knowledge_id=id,
                cursor=cursor,
                parent_run_ref=parent_run_ref,
                include_receipt=True,
            )
        except ka.KnowledgeAccessError:
            return _fetch_denied()
        return _dual_encode(document.to_dict())

    @server.tool(structured_output=False)
    def rf_source_get(id: str, cursor: str | None = None, parent_run_ref: str | None = None) -> Any:
        """Typed getter scoped to the `source` kind (KMCP-4.3)."""

        return _typed_get(
            "rf_source_get", frozenset({"source"}), id=id, cursor=cursor, parent_run_ref=parent_run_ref
        )

    @server.tool(structured_output=False)
    def rf_assertion_get(id: str, cursor: str | None = None, parent_run_ref: str | None = None) -> Any:
        """Typed getter scoped to the `assertion` kind (KMCP-4.3).

        See module docstring's "Local-trust caveat" section: this local
        stdio process always resolves `identity=None`, and every assertion
        read unconditionally requires a non-`None` identity with a
        workspace id -- so this getter denies generically for EVERY id
        through this transport in v1. Expected behavior, not a bug.
        """

        return _typed_get(
            "rf_assertion_get", frozenset({"assertion"}), id=id, cursor=cursor, parent_run_ref=parent_run_ref
        )

    @server.tool(structured_output=False)
    def rf_report_get(id: str, cursor: str | None = None, parent_run_ref: str | None = None) -> Any:
        """Typed getter addressing BOTH `report_draft` and `report_final`
        ids (KMCP-OQ-2 -- two distinct kinds, one getter name, KMCP-4.3)."""

        return _typed_get(
            "rf_report_get",
            frozenset({"report_draft", "report_final"}),
            id=id,
            cursor=cursor,
            parent_run_ref=parent_run_ref,
        )

    @server.tool(structured_output=False)
    def rf_run_get(id: str, cursor: str | None = None, parent_run_ref: str | None = None) -> Any:
        """Typed getter scoped to the `run` kind (KMCP-4.3)."""

        return _typed_get("rf_run_get", frozenset({"run"}), id=id, cursor=cursor, parent_run_ref=parent_run_ref)

    for _name in TOOL_NAMES:
        _close_input_schema(server, _name)

    # `server` is already a `StdioOnlyFastMCP` instance (constructed above,
    # before any `@server.tool()` registration) -- no separate wrap/guard
    # step is needed or performed here; see this function's own docstring.
    return server
