"""Operator MCP adapter package (research-foundry-operator-mcp-v1 P3, OPM-3.1).

Re-exports the substrate (`base.py`) and imports each built-in adapter
module for its registration side effect (`base.register(...)` at module
import time) -- mirroring the convention `research_foundry/adapters/base.py`
uses for the unrelated discovery-adapter registry. Importing this package is
sufficient to populate `all_adapters()`/`get_adapter(...)` with every P3
adapter shipped so far.

There is no MCP transport or tool-dispatch server here (P5 scope) -- this
package only builds the adapter *functions* a future server will register.

**`resolve_local_sensitivity_ceiling` (P3 hardening pass, HIGH-severity fix).**
All five P3 adapter entry points (`run_plan.invoke`, `swarm_start.invoke`,
`job_lifecycle.invoke_status`/`invoke_cancel`/`invoke_resume`) previously
declared `sensitivity_ceiling: str = "client_sensitive"` as a caller-supplied
keyword argument defaulting to `operator_mcp_policy.SENSITIVITY_LEVELS`'s
HIGHEST rank -- the loosest possible clearance. `_check_guard`'s H7 gate
(`operator_mcp_policy.py`) denies only when
`_sensitivity_rank(effective_sensitivity) > _ceiling_rank(sensitivity_ceiling)`;
with the ceiling permanently pinned to the maximum, that comparison could
never be true for any caller that did not go out of its way to override the
default, making the guard a permanent no-op. This is exactly the class of
defect P1's `PolicyContext.__post_init__` was built to make structurally
impossible one layer down (`sensitivity_ceiling` has no default there and is
validated against the closed vocabulary) -- P3 reintroduced a permissive
default one layer ABOVE it, at the public adapter boundary, where
`__post_init__`'s validation cannot see the difference between a genuine
`"client_sensitive"` clearance and an unexamined default.

The fix mirrors `operator_mcp_policy.resolve_operator_identity`'s own
doctrine exactly: NONE of the five entry points accept a
`sensitivity_ceiling` parameter anymore (option 2 of the P3 implementer
contract's remediation choices -- preferred explicitly over a caller-
supplied, monotonic-only override, option 3 -- for the same reason identity
is not caller-suppliable: a value a caller can lower is also a value a
caller-side bug or omission can leave at its permissive extreme, and this
defect is proof that boundary is not reliably defended in practice).
`resolve_local_sensitivity_ceiling` reads a NEW, sibling config key to
`operator_mcp.identity` in `foundry.yaml`::

    foundry:
      operator_mcp:
        identity: {user_id: alice, workspace_id: default, roles: [owner]}
        sensitivity_ceiling: client_sensitive

Absent block, absent key, non-string value, or a string outside
`operator_mcp_policy.SENSITIVITY_LEVELS` -- and any exception raised loading
`foundry.yaml` itself -- ALL resolve to `SENSITIVITY_LEVELS[0]` (`"public"`,
the STRICTEST/most-restrictive ceiling, never the loosest): fail-closed,
never a raise, never a permissive fallback. This is the OPPOSITE fail-closed
direction from `resolve_effective_sensitivity`'s "unresolvable content is
maximally sensitive" convention -- correct here, since a ceiling is a grant
of clearance, not a description of content risk (mirrors
`operator_mcp_policy._ceiling_rank`'s own documented rationale for why an
unknown ceiling ranks BELOW every known level rather than above it). The
producer is checked, not merely the field: this function can never return a
value outside `SENSITIVITY_LEVELS`, so
`PolicyContext.for_configured_operator(sensitivity_ceiling=...)` can never
receive an invalid string and therefore never raises `ValueError` on this
path (an uncaught `ValueError` there would itself cross an adapter's public
boundary as a raw exception, unbounded -- the class of defect the
`operator_mcp_policy` module docstring's H8 boundary exists to prevent).

Every adapter module imports this function via a LAZY `from . import
resolve_local_sensitivity_ceiling` inside its own `invoke*` function body
(never at module level) -- the same lazy-import convention `run_plan.py`'s
own module docstring documents for `planning`, required here because this
package's own `__init__.py` (this file) imports `run_plan`/`swarm_start`/
`job_lifecycle` for their registration side effect; a module-level import
back from any of them would be circular.
"""

from __future__ import annotations

import logging

from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.services import operator_mcp_policy as policy

from .base import (
    OperatorAdapter,
    OperatorAdapterResult,
    all_adapters,
    get_adapter,
    register,
    run_pipeline,
)
from . import run_plan as _run_plan  # noqa: F401  -- import for registration side effect
from . import swarm_start as _swarm_start  # noqa: F401  -- import for registration side effect
from . import job_lifecycle as _job_lifecycle  # noqa: F401  -- import for registration side effect

_logger = logging.getLogger(__name__)

#: `foundry.yaml` config coordinates for the ONE local operator's
#: sensitivity ceiling -- sibling section/key to
#: `operator_mcp_policy._IDENTITY_CONFIG_SECTION`/`_IDENTITY_CONFIG_KEY`
#: (same `foundry.operator_mcp` block, a different key: `identity` vs
#: `sensitivity_ceiling`). Deliberately NOT imported from
#: `operator_mcp_policy` (those two names are private there, and this
#: module does not touch that file per the P3 implementer contract's file-
#: ownership boundary) -- an independent, narrow duplicate of the same
#: one-line convention, exactly like `swarm_start._preflight_denial`'s own
#: documented rationale for not importing a private policy helper.
_CEILING_CONFIG_SECTION = "operator_mcp"
_CEILING_CONFIG_KEY = "sensitivity_ceiling"


def resolve_local_sensitivity_ceiling(paths: FoundryPaths | None = None) -> str:
    """Structurally derive the ONE local operator's `sensitivity_ceiling`
    (H7 defect fix -- see this module's own docstring for the full defect
    and remediation rationale). Every P3 adapter entry point calls this
    instead of accepting a `sensitivity_ceiling` parameter.

    Reads `foundry.operator_mcp.sensitivity_ceiling` from `foundry.yaml`.
    Returns that value only when it is a `str` member of
    `operator_mcp_policy.SENSITIVITY_LEVELS`; otherwise -- including a
    missing block/key, a non-string value, an unknown label, or ANY
    exception raised while loading/parsing `foundry.yaml` -- returns
    `SENSITIVITY_LEVELS[0]` (`"public"`), the single most-restrictive
    ceiling. Never raises. Callers MUST treat the returned value as
    authoritative; there is no environment-variable or caller-supplied
    override, matching `resolve_operator_identity`'s own "the ONLY source"
    contract.
    """

    resolved_paths = paths if paths is not None else FoundryPaths.discover()
    try:
        foundry_block = FoundryConfig(paths=resolved_paths).foundry
    except Exception as exc:
        # Mirrors resolve_operator_identity's own R5-BLOCK-2 boundary: log
        # only the exception TYPE NAME (NEW-13 convention), never str(exc),
        # and fail closed to the strictest ceiling rather than propagate.
        _logger.warning(
            "operator_mcp_adapters.resolve_local_sensitivity_ceiling: config load "
            "failed (%s) -- resolving to %r (deny above it)",
            type(exc).__name__,
            policy.SENSITIVITY_LEVELS[0],
        )
        return policy.SENSITIVITY_LEVELS[0]

    section = foundry_block.get(_CEILING_CONFIG_SECTION) if isinstance(foundry_block, dict) else None
    ceiling = section.get(_CEILING_CONFIG_KEY) if isinstance(section, dict) else None
    if isinstance(ceiling, str) and ceiling in policy.SENSITIVITY_LEVELS:
        return ceiling
    return policy.SENSITIVITY_LEVELS[0]


__all__ = [
    "OperatorAdapter",
    "OperatorAdapterResult",
    "all_adapters",
    "get_adapter",
    "register",
    "run_pipeline",
    "resolve_local_sensitivity_ceiling",
]
