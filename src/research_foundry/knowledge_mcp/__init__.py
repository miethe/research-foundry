"""RF Knowledge MCP -- independent local stdio process (Phase P4, KMCP-4.1).

This package is a SEPARATE OS process/registry/settings boundary from the
Search Router MCP (`research_foundry.services.search_router.*`) and from any
Operator/Hermes-adjacent module (decisions-block §9.1, invariant 1). It is
never imported by, and never imports from, either.

Modules:

* :mod:`.settings` -- read-only settings + credential allowlist (§9.3).
* :mod:`.registry` -- the SOLE place any `rf-knowledge-mcp` tool name is
  registered; builds the guarded, stdio-only FastMCP server around the
  governed :mod:`research_foundry.services.knowledge_access` service.
* :mod:`.process` -- the packaged `rf-knowledge-mcp` entry point.

Importing this package (or any of its submodules) never requires the
optional `mcp` SDK to be installed -- only :func:`registry.build_server`
(and therefore :func:`process.main`) touch it, and only lazily. See each
submodule's own docstring for its specific scope.
"""

from __future__ import annotations

__all__: list[str] = []
