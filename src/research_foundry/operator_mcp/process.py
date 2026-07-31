"""The `rf-operator-mcp` process entry point (M2 Leg B, OPM-5.1/5.4).

An independent OS process, packaged entry point, and dependency boundary
distinct from `rf-knowledge-mcp` (`research_foundry.knowledge_mcp.process`)
and from the Search Router's `rf-mcp`
(`research_foundry.services.search_router.mcp_launcher`). This module never
imports from `research_foundry.knowledge_mcp.*` or `research_foundry.
services.search_router.*` -- only from its own sibling module (:mod:`.server`).

**Offline-safe-import contract.** This module imports cleanly without the
optional `mcp` SDK installed; only :func:`main` (via :func:`server.
build_server`) touches it, and only lazily.

Wired to the packaged `rf-operator-mcp` entry point (`pyproject.toml`).

**Log-level env var (D1).** `RF_OPERATOR_MCP_LOG_LEVEL` -- the ONE new
environment variable this process reads, the same namespaced-per-process
pattern `RF_KNOWLEDGE_MCP_LOG_LEVEL` uses for `rf-knowledge-mcp`. No other
new env var is introduced anywhere in this package.
"""

from __future__ import annotations

import logging
import os

from .server import build_server

__all__ = ["main"]

logger = logging.getLogger("research_foundry.operator_mcp")

#: The ONE new environment variable this process reads (D1) -- kept as a
#: module-level constant so a future inventory check can assert against it
#: directly, mirroring `knowledge_mcp.settings.LOG_LEVEL_ENV`'s own role.
LOG_LEVEL_ENV = "RF_OPERATOR_MCP_LOG_LEVEL"
DEFAULT_LOG_LEVEL = "WARNING"


def main() -> None:
    """The one blessed way to launch `rf-operator-mcp`.

    Resolves this process's log level from :data:`LOG_LEVEL_ENV` (falling
    back to :data:`DEFAULT_LOG_LEVEL`), builds the guarded, stdio-only
    server (which itself resolves the Foundry workspace via
    `FoundryPaths.discover()` -- see `server.build_server`'s own
    docstring), and runs it over stdio -- the only transport the guarded
    server allows this process to start (invariant 8).
    """

    log_level = os.environ.get(LOG_LEVEL_ENV) or DEFAULT_LOG_LEVEL
    logger.setLevel(log_level)
    logger.info("rf-operator-mcp starting (log_level=%r)", log_level)

    server = build_server()
    server.run()


if __name__ == "__main__":  # pragma: no cover - thin entrypoint
    main()
