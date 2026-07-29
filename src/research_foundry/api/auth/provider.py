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

from typing import Protocol, runtime_checkable

from starlette.requests import Request

from research_foundry.auth_identity import AuthIdentity

# ---------------------------------------------------------------------------
# Identity value-object
# ---------------------------------------------------------------------------
#
# NEW-23: ``AuthIdentity`` now lives in ``research_foundry.auth_identity`` (a
# serve-extra-free module) because it is consumed well outside the HTTP API
# surface -- e.g. the Operator MCP policy/audit chain, which must import
# cleanly in a BASE install without fastapi/uvicorn/starlette. This is a
# re-export of that exact class object, NOT a redefinition: every existing
# ``isinstance(x, AuthIdentity)`` check and every existing
# ``from research_foundry.api.auth.provider import AuthIdentity`` import
# across the repo keeps working unchanged. See ``auth_identity.py`` for the
# full docstring/contract.


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
