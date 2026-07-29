"""Serve-extra-free home for :class:`AuthIdentity` (NEW-23).

``AuthIdentity`` is consumed well outside the HTTP API surface -- notably by
the Operator MCP policy/audit chain (``services/operator_mcp_policy.py``,
``services/audit_service.py``), which must import cleanly in a BASE install
(``pip install research-foundry``, without the optional ``[serve]`` extra --
i.e. no fastapi / uvicorn / starlette).

The dataclass previously lived in ``api/auth/provider.py``, which imports
``starlette.requests.Request`` at module level (for the ``AuthProvider``
Protocol's ``authenticate`` signature) and therefore transitively requires
the ``serve`` extra just to *import*. Moving the value-object here breaks
that coupling: this module imports nothing beyond the standard library.

``api/auth/provider.py`` re-exports this exact class object (``from
research_foundry.auth_identity import AuthIdentity``) -- it is NOT
redefined there. Every existing ``isinstance(x, AuthIdentity)`` check and
every existing ``from research_foundry.api.auth.provider import
AuthIdentity`` import across the repo continues to reference this same
class unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass


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


__all__ = ["AuthIdentity"]
