"""Agent provider contract for long-running research jobs.

Providers wrap an execution backend (local Claude agent swarm, remote worker,
subprocess, etc.) and expose a uniform job lifecycle: start → stream events →
accept/cancel → list artifacts.

Every provider MUST implement the full :class:`ResearchAgentProvider` Protocol.
Use :class:`BaseProvider` as a convenience base so subclasses only override the
methods they need.

Registry pattern mirrors :mod:`research_foundry.adapters.base` exactly:
``register`` / ``get_provider`` / ``all_providers``.
"""

from __future__ import annotations

from typing import Any, Iterator, Protocol, runtime_checkable


@runtime_checkable
class ResearchAgentProvider(Protocol):
    """Protocol every agent provider implements."""

    id: str  # unique provider identifier, e.g. "local_swarm"

    def start_job(self, job: dict[str, Any]) -> str:
        """Start a research job described by *job* and return a ``job_id``."""
        ...

    def stream_events(self, job_id: str) -> Iterator[dict[str, Any]]:
        """Yield progress events for a running or completed job."""
        ...

    def cancel_job(self, job_id: str) -> None:
        """Request cancellation of a running job."""
        ...

    def list_artifacts(self, job_id: str) -> list[dict[str, Any]]:
        """Return the artifact records produced by a completed job."""
        ...

    def accept_artifacts(
        self, job_id: str, artifact_ids: list[str]
    ) -> None:
        """Mark a subset of artifacts as accepted by the caller."""
        ...


class BaseProvider:
    """Convenience base implementing stub bodies for all Protocol methods.

    Subclasses override only the methods they need.  Every method raises
    :exc:`NotImplementedError` by default so missing implementations are caught
    at test time rather than silently succeeding.
    """

    id: str = "base"

    def start_job(self, job: dict[str, Any]) -> str:  # pragma: no cover
        raise NotImplementedError

    def stream_events(self, job_id: str) -> Iterator[dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError
        yield  # make it a generator to satisfy the return type

    def cancel_job(self, job_id: str) -> None:  # pragma: no cover
        raise NotImplementedError

    def list_artifacts(self, job_id: str) -> list[dict[str, Any]]:  # pragma: no cover
        raise NotImplementedError

    def accept_artifacts(
        self, job_id: str, artifact_ids: list[str]
    ) -> None:  # pragma: no cover
        raise NotImplementedError


_REGISTRY: dict[str, ResearchAgentProvider] = {}


def register(provider: ResearchAgentProvider) -> ResearchAgentProvider:
    """Register a provider instance under its ``id`` (idempotent)."""

    _REGISTRY[provider.id] = provider
    return provider


def get_provider(provider_id: str) -> ResearchAgentProvider | None:
    """Return the registered provider for *provider_id*, or ``None``."""

    return _REGISTRY.get(provider_id)


def all_providers() -> dict[str, ResearchAgentProvider]:
    """Return a snapshot of the full registry."""

    return dict(_REGISTRY)


__all__ = [
    "ResearchAgentProvider",
    "BaseProvider",
    "register",
    "get_provider",
    "all_providers",
]
