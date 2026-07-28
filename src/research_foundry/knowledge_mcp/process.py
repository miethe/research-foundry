"""The `rf-knowledge-mcp` process entry point (KMCP-4.1).

An independent OS process, packaged entry point, and dependency boundary
distinct from the Search Router's `rf-mcp` (`research_foundry.services.
search_router.mcp_launcher`) and from any Operator/Hermes process
(decisions-block §9.1, invariant 1). This module never imports from
`research_foundry.services.search_router.*` or an Operator/Hermes-adjacent
module -- only from its own sibling modules (:mod:`.settings`,
:mod:`.registry`).

**Offline-safe-import contract.** This module imports cleanly without the
optional `mcp` SDK installed; only :func:`main` (via
:func:`registry.build_server`) touches it, and only lazily.

Wired to the packaged `rf-knowledge-mcp` entry point (`pyproject.toml`).
"""

from __future__ import annotations

import logging

from .registry import build_server
from .settings import resolve_settings

__all__ = ["main"]

logger = logging.getLogger("research_foundry.knowledge_mcp")


def main() -> None:
    """The one blessed way to launch `rf-knowledge-mcp`.

    Resolves this process's read-only :class:`~.settings.KnowledgeMcpSettings`
    (workspace root, optional sensitivity ceiling, log level), applies the
    log level, builds the server (bootstrapping the P3 domain projectors and
    registering the two core tools), and runs it over stdio -- the only
    transport the guarded server built by :func:`registry.build_server`
    allows this process to start (invariant 8).
    """

    settings = resolve_settings()
    logger.setLevel(settings.log_level)
    logger.info(
        "rf-knowledge-mcp starting: workspace_root=%r sensitivity_threshold_max=%r",
        str(settings.paths.root),
        settings.sensitivity_threshold_max,
    )

    server = build_server(settings)
    server.run()


if __name__ == "__main__":  # pragma: no cover - thin entrypoint
    main()
