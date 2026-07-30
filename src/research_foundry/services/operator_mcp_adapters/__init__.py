"""Operator MCP adapter package (research-foundry-operator-mcp-v1 P3, OPM-3.1).

Re-exports the substrate (`base.py`) and imports each built-in adapter
module for its registration side effect (`base.register(...)` at module
import time) -- mirroring the convention `research_foundry/adapters/base.py`
uses for the unrelated discovery-adapter registry. Importing this package is
sufficient to populate `all_adapters()`/`get_adapter(...)` with every P3
adapter shipped so far.

There is no MCP transport or tool-dispatch server here (P5 scope) -- this
package only builds the adapter *functions* a future server will register.
"""

from __future__ import annotations

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

__all__ = [
    "OperatorAdapter",
    "OperatorAdapterResult",
    "all_adapters",
    "get_adapter",
    "register",
    "run_pipeline",
]
