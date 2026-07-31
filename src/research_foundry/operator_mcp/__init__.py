"""RF Operator MCP -- independent local stdio process (research-foundry-
operator-mcp-v1 M2 Leg B, OPM-5.1/5.2/5.4).

This package is the STDIO TRANSPORT SURFACE over the already-hardened P1-P3
Operator MCP substrate (`research_foundry.services.operator_mcp_policy`,
`research_foundry.services.operator_mcp_adapters`). It is a SEPARATE OS
process/registry boundary from `research_foundry.knowledge_mcp` (the
read-only Knowledge MCP surface) and from the Search Router MCP
(`research_foundry.services.search_router.*`) -- never imported by, and
never imports from, either (M2 implementer contract hard boundary 2, and
`knowledge_mcp`'s own invariant 1 in reverse).

Modules:

* :mod:`.server` -- the SOLE place any `rf-operator-mcp` tool name is
  registered; builds the guarded, stdio-only MCP server around the closed,
  14-tool inventory (`operator_mcp_policy.TOOL_NAMES`): the 13 operation
  kinds, each a thin dispatch to `operator_mcp_adapters.get_adapter(kind)`,
  plus the server-implemented `operation.preflight` meta tool (evaluate +
  mint, never consume, zero effect -- see `server.py`'s own module
  docstring for the full contract).
* :mod:`.process` -- the packaged `rf-operator-mcp` entry point.

Importing this package (or any of its submodules) never requires the
optional `mcp` SDK to be installed -- only :func:`server.build_server` (and
therefore :func:`process.main`) touch it, and only lazily. See each
submodule's own docstring for its specific scope.

**No live writeback is reachable through any tool this package registers**
(M2 implementer contract hard boundary 4). Every registered operation kind
dispatches through the SAME P1-hardened authorize -> consume -> execute
pipeline (`operator_mcp_adapters.base.run_pipeline`) that already gates
every effect behind identity, RBAC, audit-health, guard, preflight, and a
bound confirmation token -- this package adds a transport, never a new
capability, and never edits any of the P1-P3 files it dispatches through
(the M2 contract's hard boundary 1).
"""

from __future__ import annotations

__all__: list[str] = []
