"""Auth provider contract for the Research Foundry API.

AuthProvider is a *thin*, pluggable identity layer.  Concrete adapters live
in ``api/auth/adapters/`` and self-register via :func:`register_provider` at
import time.  This module stays adapter-neutral — it defines only the shared
contract and the module-level registry.

Absent-identity semantics (canonical signal)
--------------------------------------------
When ``auth.provider`` is set to ``none`` in ``foundry.yaml`` no auth
middleware is added and ``request.state`` never gains an ``identity``
attribute.  Consumers — the ``require_role`` dependency (P5.2), the Phase 8
frontend, and any future gate — **must** treat
``getattr(request.state, "identity", None)`` returning ``None`` as
"no identity configured", not as an error state.  Raising on ``None`` is
wrong; silently allowing unrestricted access when identity IS expected is
equally wrong — consumers are responsible for deciding which case applies
to their route.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from starlette.requests import Request


# ---------------------------------------------------------------------------
# Identity value-object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthIdentity:
    """Immutable identity resolved from an inbound request.

    Attributes
    ----------
    user_id:
        Provider-scoped user identifier (e.g. ``"alice"``, an OIDC ``sub`` value).
        Always non-empty when an identity exists.
    workspace_id:
        Workspace the request is acting within.  Single-tenant deployments
        may use a fixed sentinel (e.g. ``"default"``).
    roles:
        Immutable tuple of role strings granted to this identity within the
        workspace.  Never a mutable list — callers that need set semantics
        should do ``set(identity.roles)``.

        **JSON serialization note** (RBAC-900): when this dataclass is
        serialized via :func:`dataclasses.asdict` or a Pydantic model,
        ``roles`` is emitted as a JSON array ``[]``.  Deserializers MUST
        convert that array back to a ``tuple[str, ...]`` before constructing
        an :class:`AuthIdentity`; the in-memory contract is always a tuple,
        never a list.  An identity with no roles assigned should use
        ``roles=()`` (the default empty tuple), not ``None``.
    """

    user_id: str
    workspace_id: str
    roles: tuple[str, ...]


# ---------------------------------------------------------------------------
# Provider Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class AuthProvider(Protocol):
    """Protocol every auth provider adapter must satisfy.

    Adapters must expose:

    * ``id`` — a stable, lower-snake string name (e.g. ``"my_provider"``).
      Used as the registry key and matches the ``auth.provider`` value in
      ``foundry.yaml``.
    * :meth:`authenticate` — resolve an :class:`AuthIdentity` from the
      inbound Starlette ``Request``, or return ``None`` if no valid credential
      is present.  Returning ``None`` is *not* an error — it means "this
      request carries no recognisable identity".
    * :meth:`available` — True when the adapter can operate in real (non-stub)
      mode.  Adapters that require optional dependencies (e.g. PyJWT, Clerk
      SDK) SHOULD return ``False`` when those are absent and fall back to a
      safe degraded mode rather than raising at import time.  This mirrors the
      ``Adapter.available()`` contract in ``adapters/base.py``.
    """

    id: str

    def authenticate(self, request: Request) -> AuthIdentity | None:
        """Resolve an identity from ``request``, or ``None`` if absent/invalid."""
        ...

    def available(self) -> bool:
        """Whether this provider can operate in non-degraded mode."""
        ...


# ---------------------------------------------------------------------------
# Module-level registry
# ---------------------------------------------------------------------------

_REGISTRY: dict[str, AuthProvider] = {}


def register_provider(provider: AuthProvider) -> AuthProvider:
    """Register ``provider`` under its ``id`` (idempotent — re-registration replaces).

    Adapters call this at module level so they self-register on import.
    """
    _REGISTRY[provider.id] = provider
    return provider


def get_provider(name: str) -> AuthProvider | None:
    """Return the registered provider for ``name``, or ``None`` if not found."""
    return _REGISTRY.get(name)


def all_providers() -> dict[str, AuthProvider]:
    """Return a shallow copy of the current provider registry."""
    return dict(_REGISTRY)


__all__ = [
    "AuthIdentity",
    "AuthProvider",
    "register_provider",
    "get_provider",
    "all_providers",
]
