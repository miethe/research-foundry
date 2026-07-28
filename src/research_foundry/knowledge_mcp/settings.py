"""Read-only settings and credential allowlist for `rf-knowledge-mcp` (KMCP-4.1).

Freezes decisions-block §9.3 ("Settings and credential allowlist") into code.
This module resolves ONLY the following, and nothing else:

* Foundry workspace root -- via :meth:`FoundryPaths.discover`, the SAME
  `RESEARCH_FOUNDRY_HOME`-aware mechanism every other RF CLI/API/MCP
  transport already uses. No new identity/workspace mechanism is
  introduced by this process.
* An optional sensitivity-ceiling override, read from a dedicated
  `foundry.knowledge_mcp.sensitivity_threshold_max` config block --
  deliberately a SEPARATE namespace from the Search Router's own
  `foundry.mcp.*` block (`search_router.mcp_launcher`), so an operator can
  set a ceiling for one process without silently affecting the other, and
  so this module never has to read that block at all.
* A logging level, via a dedicated, namespaced environment variable.

**FORBIDDEN** (decisions-block §9.3, invariant 1) -- this module never reads,
references, defaults to, or declares as an optional dependency:

* Any Search Router / `rf-mcp` provider credential or env key (a search
  provider secret or endpoint override).
* Any Operator/Hermes credential or routing config (service tokens,
  `RF_TOKEN_AGENT`, or any model-routing provider API key).
* Any writeback credential (MeatyWiki, SkillMeat, CCDash) or
  catalog-build/migration flag.
* The Search Router's own registry/settings modules
  (`research_foundry.services.search_router.*`), or an Operator/Hermes
  registry module.

:data:`ALLOWED_ENV_VARS` is the exact, exhaustive set of environment
variable names this module ever reads -- kept in sync with
:func:`resolve_settings` below. A future KMCP-4.4 inventory snapshot can
assert the process's actual environment access never exceeds this tuple.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths

__all__ = [
    "ALLOWED_ENV_VARS",
    "DEFAULT_LOG_LEVEL",
    "LOG_LEVEL_ENV",
    "WORKSPACE_ROOT_ENV",
    "KnowledgeMcpSettings",
    "resolve_settings",
]

# Same workspace-root override every other RF transport already honors via
# `FoundryPaths.find_workspace_root` -- not re-implemented here, only listed
# for the allowlist's own record.
WORKSPACE_ROOT_ENV = "RESEARCH_FOUNDRY_HOME"

# Dedicated, namespaced logging-level override for this process only. This is
# a DISTINCT env var from the Search Router's `RF_MCP_PRINCIPAL_*` family --
# this process has no identity/principal concept at all (the local stdio
# transport always runs under "local trust", identity=None; see
# `knowledge_access.KnowledgeAccessContext`'s own docstring).
LOG_LEVEL_ENV = "RF_KNOWLEDGE_MCP_LOG_LEVEL"
DEFAULT_LOG_LEVEL = "WARNING"

# Exact, exhaustive allowlist of every environment variable this module ever
# reads (decisions-block §9.3). Nothing outside this tuple is ever consulted.
ALLOWED_ENV_VARS: tuple[str, ...] = (WORKSPACE_ROOT_ENV, LOG_LEVEL_ENV)

# Dedicated config namespace -- see module docstring's second bullet.
_CONFIG_SECTION = "knowledge_mcp"
_SENSITIVITY_CEILING_KEY = "sensitivity_threshold_max"


@dataclass(frozen=True)
class KnowledgeMcpSettings:
    """Resolved, read-only settings for one `rf-knowledge-mcp` process.

    Every field is drawn only from the module docstring's ALLOWED list.
    There is no credential field on this dataclass because this process
    holds none.
    """

    paths: FoundryPaths
    sensitivity_threshold_max: str | None
    log_level: str


def resolve_settings(paths: FoundryPaths | None = None) -> KnowledgeMcpSettings:
    """Resolve :class:`KnowledgeMcpSettings` for one process (KMCP-4.1).

    ``paths`` defaults to :meth:`FoundryPaths.discover` when omitted. A
    missing/malformed `foundry.knowledge_mcp` config block degrades to no
    ceiling override (``None``) -- config is advisory, never load-bearing
    for this resolution to succeed.
    """

    resolved_paths = paths if paths is not None else FoundryPaths.discover()

    foundry_block = FoundryConfig(paths=resolved_paths).foundry
    section = foundry_block.get(_CONFIG_SECTION) if isinstance(foundry_block, dict) else None
    ceiling = section.get(_SENSITIVITY_CEILING_KEY) if isinstance(section, dict) else None

    log_level = os.environ.get(LOG_LEVEL_ENV) or DEFAULT_LOG_LEVEL

    return KnowledgeMcpSettings(
        paths=resolved_paths,
        sensitivity_threshold_max=str(ceiling) if ceiling else None,
        log_level=log_level,
    )
