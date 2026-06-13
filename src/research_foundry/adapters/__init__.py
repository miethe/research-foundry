"""Tool adapters. Concrete adapters self-register on import (see ``load_all``)."""

from __future__ import annotations

from .base import (
    Adapter,
    AdapterResult,
    BaseAdapter,
    all_adapters,
    get_adapter,
    module_available,
    register,
)

# Names of the concrete adapter modules. They are imported lazily by
# ``load_all`` so a missing/partial module never breaks ``import research_foundry``.
_CONCRETE = (
    "claude_agent_sdk",
    "gpt_researcher",
    "paperqa2",
    "opencode",
    "litellm_router",
)


def load_all() -> dict[str, Adapter]:
    """Import every concrete adapter module so it self-registers; return registry."""

    import importlib

    for name in _CONCRETE:
        try:
            importlib.import_module(f"{__name__}.{name}")
        except Exception:  # noqa: BLE001 - an adapter must never break startup
            continue
    return all_adapters()


__all__ = [
    "Adapter",
    "AdapterResult",
    "BaseAdapter",
    "all_adapters",
    "get_adapter",
    "module_available",
    "register",
    "load_all",
]
