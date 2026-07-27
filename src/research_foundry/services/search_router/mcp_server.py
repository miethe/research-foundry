"""Thin MCP server wrapper around the Research Foundry Search Router.

**CARP-5.2 (catalog-assisted-research-planning) additions.** The core
``search_run`` tool and every mode-preset tool below also accept three
optional, keyword-style JSON arguments that marshal through to
:func:`router.run_search`'s own keyword-only ``identity`` /
``sensitivity_threshold`` / ``evidence_plan`` parameters (carp-contract-
freeze.md §2, §4). ``retrieval.policy`` and ``retrieval.limits`` already ride
inside ``request`` itself (validated against ``search_request.schema.yaml``)
and need no wrapper change. All three default to ``None``, reproducing the
pre-CARP call shape:

* ``identity`` -- a plain ``{"user_id": ..., "workspace_id": ..., "roles":
  [...]}`` mapping (MCP arguments are JSON, never Python objects).
  **DI-1 F2 remediation (was a cross-workspace enumeration oracle):** this
  payload is no longer marshaled into an :class:`AuthIdentity` verbatim. It
  is reconciled against the server's launch-time principal via
  :mod:`.mcp_launcher` (:func:`mcp_launcher.reconcile_client_identity`) --
  the launch principal's ``workspace_id``/``roles`` are always authoritative;
  a client-declared ``workspace_id`` that disagrees with it is rejected, not
  honored. See :func:`_resolve_tool_identity` and the ``mcp_launcher`` module
  docstring for the full contract.
* ``sensitivity_threshold`` -- **DI-1 F2 remediation:** no longer forwarded
  verbatim. Clamped to a server-configured ceiling via
  :func:`_resolve_tool_sensitivity_threshold`
  (:func:`mcp_launcher.clamp_sensitivity_threshold`) before reaching
  ``run_search``. Per ``catalog_retrieval.RetrievalConstraints``, an
  *omitted* threshold is still not defaulted to "allow everything" -- it
  passes through as ``None`` regardless of any configured ceiling, which the
  P2 adapter denies fail-closed.
* ``evidence_plan`` -- an already-built ``research_evidence_plan`` dict (the
  same shape :mod:`planning` persists). When supplied, ``run_search``
  consumes it as-is instead of building an ad-hoc single-question plan.

This module is launched exclusively via :mod:`.mcp_launcher` (the packaged
``rf-mcp`` entry point, and this module's own :func:`main`, both delegate
there): it resolves the launch principal, logs it, and enforces the
stdio-only transport guard. See ``mcp_launcher.py``'s module docstring for
the full DI-1 F2 remediation contract.

This module exposes the router's Python API (``run_search`` / ``extract_urls``)
as a small set of MCP tools, matching the minimum surface from spec §10.2.

**Tool naming convention.** Tool names are the underscored Python function
names the ``@server.tool()`` decorator derives by default (e.g.
``search_run``, ``search_source_discovery``) — *not* the dotted form
(``search.run``) some early spec drafts used. This is the single source of
truth for registered tool names; ``docs/dev/architecture/search-router/
deployment.md`` §5 must be kept in sync with this list:

* ``search_run``                  → :func:`router.run_search`
* ``extract_url``                 → :func:`router.extract_urls`
* ``search_source_discovery``     → ``run_search`` with ``mode="source_discovery"``
* ``search_semantic_discovery``   → ``run_search`` with ``mode="semantic_discovery"``
* ``search_github_discovery``     → ``run_search`` with ``mode="github_discovery"``
* ``search_quick_lookup``         → ``run_search`` with ``mode="quick_lookup"``
* ``search_official_sources``     → ``run_search`` with ``mode="official_source_check"``
* ``search_academic_discovery``   → ``run_search`` with ``mode="academic_discovery"``

**Offline-safe import contract.** The module itself MUST import successfully
without the ``mcp`` SDK installed. Only :func:`build_server` (and therefore
:func:`main`) attempt to import the SDK, and they raise a clear
:class:`RuntimeError` telling the operator to ``uv sync --extra mcp`` if it
isn't there. This mirrors the rest of the router's adapter pattern: optional
deps are lazy, never top-level.

Tools return the raw run dict / extraction dict produced by the router (which
includes ``run_id``, ``source_cards``, ``schema_errors`` etc.). The MCP SDK
serializes that to the client. Identity reconciliation and sensitivity-ceiling
clamping are delegated to :mod:`.mcp_launcher`; otherwise this file stays a
thin transport adapter with no routing/synthesis logic of its own.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from . import mcp_launcher
from .router import extract_urls, run_search

if TYPE_CHECKING:
    from research_foundry.api.auth.provider import AuthIdentity

__all__ = ["build_server", "main"]

logger = logging.getLogger(__name__)


_MISSING_SDK_MSG = (
    "The 'mcp' Python SDK is not installed. The Research Foundry Search Router "
    "MCP server is an optional surface; install it with:\n"
    "    uv sync --extra mcp\n"
    "or\n"
    "    pip install 'research-foundry[mcp]'"
)


def _resolve_tool_identity(identity: dict[str, Any] | None) -> AuthIdentity | None:
    """Resolve the effective identity for one MCP tool call (DI-1 F2).

    Routes through :mod:`.mcp_launcher`'s one choke point instead of
    marshaling the client-supplied ``identity`` payload verbatim: the
    server's launch principal (:func:`mcp_launcher.get_launch_principal`) is
    always authoritative for ``workspace_id``/``roles``; a client-declared
    ``workspace_id`` that disagrees with it is rejected (raises
    :class:`mcp_launcher.CrossWorkspaceIdentityError`), and in
    single-operator-trust mode (no launch principal configured) the client
    payload is ignored entirely -- see
    :func:`mcp_launcher.reconcile_client_identity` for the full contract.
    """

    launch_principal = mcp_launcher.get_launch_principal()
    return mcp_launcher.reconcile_client_identity(launch_principal, identity)


def _resolve_tool_sensitivity_threshold(sensitivity_threshold: str | None) -> str | None:
    """Clamp a client-declared ``sensitivity_threshold`` to the server-side
    ceiling (DI-1 F2 Change 3) before it reaches :func:`router.run_search`.

    See :func:`mcp_launcher.clamp_sensitivity_threshold`. Clamping (not
    rejecting) means a well-behaved client that asks above the ceiling still
    gets a successful, just-more-restricted run; the clamp is logged at
    WARNING so it is visible in the server's own logs.
    """

    ceiling = mcp_launcher.get_sensitivity_ceiling()
    effective, was_clamped = mcp_launcher.clamp_sensitivity_threshold(sensitivity_threshold, ceiling)
    if was_clamped:
        logger.warning(
            "MCP client requested sensitivity_threshold=%r, above the configured ceiling %r; "
            "clamped to %r.",
            sensitivity_threshold,
            ceiling,
            effective,
        )
    return effective


def build_server() -> Any:
    """Construct and return a :class:`FastMCP` server with the router tools registered.

    Lazily imports the MCP SDK; raises :class:`RuntimeError` with a clear
    install hint if the SDK is missing. Returning the server object (rather
    than running it) keeps this function unit-testable once the SDK is
    available.

    **DI-1 F2 Change 4 (generation 4 -- subclass, not proxy):** the returned
    object is an instance of :func:`mcp_launcher.stdio_only_fastmcp_class`'s
    ``_StdioOnlyFastMCP`` -- a genuine ``FastMCP`` SUBCLASS constructed
    directly here, in place of the plain ``FastMCP(...)`` construction this
    function used before. ``server.sse_app()`` / ``server.
    streamable_http_app()`` / ``server.run_sse_async()`` / ``server.
    run_streamable_http_async()`` and ``server.run(transport="sse")`` /
    ``"streamable-http"`` all raise :class:`mcp_launcher.
    UnsupportedTransportError`. Because tools are registered on this
    subclass instance from birth (every ``@server.tool()`` call below runs
    against the already-guarded object), and because a subclass instance IS
    the server rather than wrapping a distinct one, there is no bound
    method anywhere on it (``server.list_tools``, ``server.call_tool``,
    etc.) whose ``__self__`` resolves to a different, unguarded object --
    the bypass that defeated the prior delegating-proxy generations of this
    guard (Codex gpt-5.6-sol, 2026-07-27). See ``mcp_launcher.py``'s module
    docstring and the block comment above ``stdio_only_fastmcp_class`` for
    the full history.
    """

    try:
        # FastMCP is the high-level decorator API in the official SDK.
        from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]
    except ImportError as exc:  # noqa: BLE001 - re-raise as a clear runtime error
        raise RuntimeError(_MISSING_SDK_MSG) from exc

    StdioOnlyFastMCP = mcp_launcher.stdio_only_fastmcp_class(FastMCP)
    server = StdioOnlyFastMCP("research-foundry-search-router")

    # --- core tools (spec §10.2) -----------------------------------------

    @server.tool()
    def search_run(
        request: dict[str, Any],
        identity: dict[str, Any] | None = None,
        sensitivity_threshold: str | None = None,
        evidence_plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a Search Router run.

        ``request`` must validate against ``schemas/search_request.schema.yaml``
        (at minimum: ``query`` and ``mode``). Returns the full ``search_run``
        record produced by :func:`router.run_search`, including ``run_id``,
        ``normalized_results``, ``source_cards``, ``metrics``, and (if any)
        ``schema_errors``.

        ``identity``, ``sensitivity_threshold``, and ``evidence_plan`` are
        CARP-5.2 context passthroughs -- see the module docstring. All three
        default to ``None``, reproducing the pre-CARP call shape. ``identity``
        and ``sensitivity_threshold`` are reconciled/clamped against the
        server's launch principal and sensitivity ceiling (DI-1 F2) before
        reaching ``run_search`` -- see :func:`_resolve_tool_identity` and
        :func:`_resolve_tool_sensitivity_threshold`.
        """

        return run_search(
            request,
            identity=_resolve_tool_identity(identity),
            sensitivity_threshold=_resolve_tool_sensitivity_threshold(sensitivity_threshold),
            evidence_plan=evidence_plan,
        )

    @server.tool()
    def extract_url(urls: list[str]) -> dict[str, Any]:
        """Extract Markdown from known URLs into source cards.

        Thin wrapper over :func:`router.extract_urls`. Returns a dict with
        ``run_id``, ``source_cards`` (list of source-card ids), and
        ``degraded`` (True if any extraction fell through to content-empty).
        """

        return extract_urls(list(urls))

    # --- mode-preset convenience tools -----------------------------------
    #
    # Each preset is a thin shim that fills in ``mode`` on the request before
    # delegating to ``run_search``. They exist so an agent harness can call the
    # router via a *named* tool ("search.source_discovery") that already
    # encodes the intent, without forcing the agent to know the mode taxonomy.

    def _with_mode(request: dict[str, Any], mode: str) -> dict[str, Any]:
        merged = dict(request or {})
        merged["mode"] = mode
        return merged

    def _run_search_with_context(
        request: dict[str, Any],
        identity: dict[str, Any] | None,
        sensitivity_threshold: str | None,
        evidence_plan: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Shared CARP-5.2 marshal-and-delegate tail for every mode preset.

        Identity/sensitivity-threshold reconciliation (DI-1 F2) happens here
        too, via the same :func:`_resolve_tool_identity` /
        :func:`_resolve_tool_sensitivity_threshold` helpers ``search_run`` uses.
        """

        return run_search(
            request,
            identity=_resolve_tool_identity(identity),
            sensitivity_threshold=_resolve_tool_sensitivity_threshold(sensitivity_threshold),
            evidence_plan=evidence_plan,
        )

    @server.tool()
    def search_source_discovery(
        request: dict[str, Any],
        identity: dict[str, Any] | None = None,
        sensitivity_threshold: str | None = None,
        evidence_plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a search with ``mode="source_discovery"`` (Brave → Exa)."""
        return _run_search_with_context(
            _with_mode(request, "source_discovery"), identity, sensitivity_threshold, evidence_plan
        )

    @server.tool()
    def search_semantic_discovery(
        request: dict[str, Any],
        identity: dict[str, Any] | None = None,
        sensitivity_threshold: str | None = None,
        evidence_plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a search with ``mode="semantic_discovery"`` (Exa → GitHub → Brave)."""
        return _run_search_with_context(
            _with_mode(request, "semantic_discovery"), identity, sensitivity_threshold, evidence_plan
        )

    @server.tool()
    def search_github_discovery(
        request: dict[str, Any],
        identity: dict[str, Any] | None = None,
        sensitivity_threshold: str | None = None,
        evidence_plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a search with ``mode="github_discovery"`` (GitHub → Exa → Brave)."""
        return _run_search_with_context(
            _with_mode(request, "github_discovery"), identity, sensitivity_threshold, evidence_plan
        )

    @server.tool()
    def search_quick_lookup(
        request: dict[str, Any],
        identity: dict[str, Any] | None = None,
        sensitivity_threshold: str | None = None,
        evidence_plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a search with ``mode="quick_lookup"`` (Brave; fast, low-cost, single fact)."""
        return _run_search_with_context(
            _with_mode(request, "quick_lookup"), identity, sensitivity_threshold, evidence_plan
        )

    @server.tool()
    def search_official_sources(
        request: dict[str, Any],
        identity: dict[str, Any] | None = None,
        sensitivity_threshold: str | None = None,
        evidence_plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a search with ``mode="official_source_check"`` (Brave → Exa).

        Prefers high-authority/official domains; also produces a
        ``claim_ledger`` output when the request asks for one.
        """
        return _run_search_with_context(
            _with_mode(request, "official_source_check"), identity, sensitivity_threshold, evidence_plan
        )

    @server.tool()
    def search_academic_discovery(
        request: dict[str, Any],
        identity: dict[str, Any] | None = None,
        sensitivity_threshold: str | None = None,
        evidence_plan: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a search with ``mode="academic_discovery"``.

        Searches academic databases (OpenAlex, Semantic Scholar, PubMed,
        arXiv) for peer-reviewed sources.
        """
        return _run_search_with_context(
            _with_mode(request, "academic_discovery"), identity, sensitivity_threshold, evidence_plan
        )

    # `server` is already a `StdioOnlyFastMCP` instance (constructed above,
    # before any `@server.tool()` registration) -- no separate wrap/guard
    # step is needed or performed here; see `build_server`'s docstring.
    return server


def main() -> None:
    """Module entry point -- delegates to :func:`mcp_launcher.main`.

    Preserved (rather than removed) so ``python -m research_foundry.services.
    search_router.mcp_server`` -- the exact invocation ``.mcp.json`` uses --
    keeps working unchanged. :mod:`mcp_launcher` is now the sole place that
    resolves the launch principal, logs it, and runs the stdio-only guarded
    server (DI-1 F2); the packaged ``rf-mcp`` entry point (``pyproject.toml``)
    points directly at ``mcp_launcher:main``.
    """

    mcp_launcher.main()


if __name__ == "__main__":  # pragma: no cover - thin entrypoint
    main()
