"""GET /auth/identity — caller's own identity endpoint (P5.4 FU-2).

Route: GET /auth/identity  (mounted under /api in create_app → /api/auth/identity)

Three-mode behaviour
--------------------
1. ``auth.provider=none`` (no auth middleware installed):
   ``request.state`` never gains an ``identity`` attribute; the route handler
   returns an anonymous/null response.  The frontend (useClerkAuth.ts) only
   invokes this endpoint when ``auth.provider=clerk`` is active, so this branch
   is the graceful degradation path for single-operator / no-auth deployments.

   JSON: ``{"user_id": null, "workspace_id": null, "roles": []}``

2. ``auth.provider=clerk`` or ``auth.provider=local_static`` — request
   unauthenticated (no valid token):
   :class:`~research_foundry.api.middleware.auth.AuthProviderMiddleware`
   intercepts the request and returns HTTP 401 **before this route runs**.
   The route handler is never reached.

3. ``auth.provider=clerk`` or ``auth.provider=local_static`` — request
   authenticated (valid token):
   The middleware sets ``request.state.identity`` and forwards the request.
   The route handler returns the caller's own identity.

   JSON: ``{"user_id": str, "workspace_id": str, "roles": [str, ...]}``

Security notes
--------------
* Only the **caller's own** identity is returned — there is no ``user_id``
  query parameter and no admin RBAC gate.  A caller can only inspect their
  own resolved identity.
* No raw token content, JWKS material, or provider name is included in any
  response body.
"""

from __future__ import annotations

from fastapi import APIRouter
from starlette.requests import Request

from ..auth.provider import AuthIdentity

router = APIRouter()


@router.get("/auth/identity", tags=["auth"])
def get_auth_identity(request: Request) -> dict:
    """Return the current request's resolved :class:`~AuthIdentity`.

    The response shape matches the FE ``AuthIdentity`` interface in
    ``useClerkAuth.ts`` exactly:

    .. code-block:: json

        {"user_id": "string", "workspace_id": "string", "roles": ["string"]}

    In ``auth.provider=none`` mode every field is ``null`` / ``[]``:

    .. code-block:: json

        {"user_id": null, "workspace_id": null, "roles": []}

    Returns:
        A JSON dict with ``user_id`` (str | None), ``workspace_id``
        (str | None), and ``roles`` (list[str]).  HTTP 401 is returned
        by the upstream middleware before this handler runs when auth is
        enabled and the request carries no valid credential.
    """
    identity: AuthIdentity | None = getattr(request.state, "identity", None)
    if identity is None:
        # auth.provider=none — no auth middleware; anonymous single-operator mode.
        return {"user_id": None, "workspace_id": None, "roles": []}
    return {
        "user_id": identity.user_id,
        "workspace_id": identity.workspace_id,
        "roles": list(identity.roles),
    }


__all__ = ["router"]
