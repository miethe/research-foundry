"""Thin MCP server wrapper around the Research Foundry Search Router.

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
serializes that to the client. No business logic lives here — this file is a
thin transport adapter.
"""

from __future__ import annotations

from typing import Any

from .router import extract_urls, run_search

__all__ = ["build_server", "main"]


_MISSING_SDK_MSG = (
    "The 'mcp' Python SDK is not installed. The Research Foundry Search Router "
    "MCP server is an optional surface; install it with:\n"
    "    uv sync --extra mcp\n"
    "or\n"
    "    pip install 'research-foundry[mcp]'"
)


def build_server() -> Any:
    """Construct and return a :class:`FastMCP` server with the router tools registered.

    Lazily imports the MCP SDK; raises :class:`RuntimeError` with a clear
    install hint if the SDK is missing. Returning the server object (rather
    than running it) keeps this function unit-testable once the SDK is
    available, and lets the caller (e.g. tests or a custom entry point) tune
    transport / lifecycle settings.
    """

    try:
        # FastMCP is the high-level decorator API in the official SDK.
        from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]
    except ImportError as exc:  # noqa: BLE001 - re-raise as a clear runtime error
        raise RuntimeError(_MISSING_SDK_MSG) from exc

    server = FastMCP("research-foundry-search-router")

    # --- core tools (spec §10.2) -----------------------------------------

    @server.tool()
    def search_run(request: dict[str, Any]) -> dict[str, Any]:
        """Execute a Search Router run.

        ``request`` must validate against ``schemas/search_request.schema.yaml``
        (at minimum: ``query`` and ``mode``). Returns the full ``search_run``
        record produced by :func:`router.run_search`, including ``run_id``,
        ``normalized_results``, ``source_cards``, ``metrics``, and (if any)
        ``schema_errors``.
        """

        return run_search(request)

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

    @server.tool()
    def search_source_discovery(request: dict[str, Any]) -> dict[str, Any]:
        """Run a search with ``mode="source_discovery"`` (Brave → Exa)."""
        return run_search(_with_mode(request, "source_discovery"))

    @server.tool()
    def search_semantic_discovery(request: dict[str, Any]) -> dict[str, Any]:
        """Run a search with ``mode="semantic_discovery"`` (Exa → GitHub → Brave)."""
        return run_search(_with_mode(request, "semantic_discovery"))

    @server.tool()
    def search_github_discovery(request: dict[str, Any]) -> dict[str, Any]:
        """Run a search with ``mode="github_discovery"`` (GitHub → Exa → Brave)."""
        return run_search(_with_mode(request, "github_discovery"))

    @server.tool()
    def search_quick_lookup(request: dict[str, Any]) -> dict[str, Any]:
        """Run a search with ``mode="quick_lookup"`` (Brave; fast, low-cost, single fact)."""
        return run_search(_with_mode(request, "quick_lookup"))

    @server.tool()
    def search_official_sources(request: dict[str, Any]) -> dict[str, Any]:
        """Run a search with ``mode="official_source_check"`` (Brave → Exa).

        Prefers high-authority/official domains; also produces a
        ``claim_ledger`` output when the request asks for one.
        """
        return run_search(_with_mode(request, "official_source_check"))

    @server.tool()
    def search_academic_discovery(request: dict[str, Any]) -> dict[str, Any]:
        """Run a search with ``mode="academic_discovery"``.

        Searches academic databases (OpenAlex, Semantic Scholar, PubMed,
        arXiv) for peer-reviewed sources.
        """
        return run_search(_with_mode(request, "academic_discovery"))

    return server


def main() -> None:
    """Module entry point: build the server and run it on stdio.

    Wired to ``python -m research_foundry.services.search_router.mcp_server``.
    Tests cannot exercise the live transport without the ``mcp`` SDK
    installed — that is expected.
    """

    server = build_server()
    # FastMCP defaults to stdio transport, which is what an MCP-aware agent
    # harness (Claude Code, OpenCode, Hermes) expects when launching the
    # server as a subprocess.
    server.run()


if __name__ == "__main__":  # pragma: no cover - thin entrypoint
    main()
