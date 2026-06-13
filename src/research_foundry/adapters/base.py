"""Adapter contract for external research/agent tools.

Adapters are *thin*: they wrap an external tool (GPT Researcher, PaperQA2,
Claude Agent SDK, OpenCode, LiteLLM) and normalize its output into the
Research Foundry YAML substrate. Per the spec, the external tool's output is
*never* the authority — it becomes source candidates / source cards /
extraction cards that still flow through the claim ledger and verifier.

Every adapter MUST run in two modes:

* **available** — the external dependency is installed and configured; the
  adapter performs the real call.
* **offline / degraded** — the dependency is absent or no key is present; the
  adapter returns a deterministic, clearly-labeled stub result with
  ``degraded=True`` so the pipeline still completes and is testable.

This dual mode is what lets the MVP install and run end-to-end with no API keys.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


def module_available(module_name: str) -> bool:
    """True if ``module_name`` can be imported without importing it."""

    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError):
        return False


@dataclass
class AdapterResult:
    """Normalized output of an adapter invocation.

    Attributes
    ----------
    adapter: id of the adapter that produced this result.
    degraded: True when produced in offline/stub mode (no real external call).
    source_candidates: list of normalized candidate-source records (schema:
        source_card fields subset) the adapter discovered.
    artifacts: arbitrary named payloads (e.g. raw report markdown) to persist
        under the run's ``telemetry/`` as non-authoritative trace.
    notes: human-readable notes (e.g. why it degraded).
    cost_usd / tokens: best-effort accounting for CCDash telemetry.
    """

    adapter: str
    degraded: bool = False
    source_candidates: list[dict[str, Any]] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    cost_usd: float = 0.0
    tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "degraded": self.degraded,
            "source_candidates": self.source_candidates,
            "notes": self.notes,
            "cost_usd": self.cost_usd,
            "tokens": self.tokens,
            "artifact_keys": sorted(self.artifacts),
        }


@runtime_checkable
class Adapter(Protocol):
    """Protocol every adapter implements."""

    id: str
    requires: tuple[str, ...]  # python modules that must import for real mode

    def available(self) -> bool:
        """Whether the real (non-degraded) mode can run in this environment."""
        ...

    def run(self, request: dict[str, Any]) -> AdapterResult:
        """Execute the adapter against ``request`` and return a normalized result."""
        ...


class BaseAdapter:
    """Convenience base implementing :meth:`available` from :attr:`requires`."""

    id: str = "base"
    requires: tuple[str, ...] = ()

    def available(self) -> bool:
        return all(module_available(m) for m in self.requires)

    def run(self, request: dict[str, Any]) -> AdapterResult:  # pragma: no cover
        raise NotImplementedError


_REGISTRY: dict[str, Adapter] = {}


def register(adapter: Adapter) -> Adapter:
    """Register an adapter instance under its ``id`` (idempotent)."""

    _REGISTRY[adapter.id] = adapter
    return adapter


def get_adapter(adapter_id: str) -> Adapter | None:
    return _REGISTRY.get(adapter_id)


def all_adapters() -> dict[str, Adapter]:
    return dict(_REGISTRY)


__all__ = [
    "module_available",
    "AdapterResult",
    "Adapter",
    "BaseAdapter",
    "register",
    "get_adapter",
    "all_adapters",
]
