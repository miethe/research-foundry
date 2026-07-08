"""Admin settings API router (public-multiuser-release Phase 5, P5.6 T2).

Exposes workspace-management, auth-provider status, and rate-limit config
endpoints that the admin settings panel (P5.8) consumes.

All mutation routes are gated with ``require_role("owner", "admin")`` from
:mod:`~research_foundry.api.auth.rbac`.  No bespoke auth checks are used in
this router.

Endpoints
---------
GET  /api/admin/workspace                     — member list for caller's workspace
PATCH /api/admin/members/{user_id}/role       — update a member's role
GET  /api/admin/auth-provider-status          — active provider + availability
GET  /api/admin/rate-limit-config             — current rate-limit budget
PATCH /api/admin/rate-limit-config            — update rate-limit budget (in-memory)
GET  /api/admin/rbac-status                   — RBAC enforcement state (any authed user)

Response contract (matches P5.8 frontend assumptions — do not change field names):

GET /api/admin/workspace
    { "workspace_id": str, "members": list[{user_id, email, role}] | null }

PATCH /api/admin/members/{user_id}/role
    body: { "role": str }  → 200 on success, 404 when member not found

GET /api/admin/rate-limit-config
    { "enabled": bool, "window_seconds": int, "max_requests": int,
      "per_identity": true, "per_route": true }

PATCH /api/admin/rate-limit-config
    body: { "max_requests"?: int, "window_seconds"?: int }
    → 200 with updated config on success
    NOTE: ``enabled`` is a startup-only setting (foundry.yaml auth.rate_limit.enabled)
    and cannot be toggled at runtime — include it in the body and it is silently ignored.

GET /api/admin/auth-provider-status
    { "provider": str, "available": bool, "details"?: str }
    NOTE: NEVER returns raw keys, JWKS secrets, or Bearer tokens.

GET /api/admin/rbac-status
    { "rbac_enforcement": str, "rbac_enforced": bool, "auth_provider": str }
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from ..auth.provider import get_provider
from ..auth.rbac import require_role
from ...config import FoundryConfig
from ...paths import FoundryPaths
from ...services import rbac_store
from .runs import get_paths

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Shared dependencies
# ---------------------------------------------------------------------------

# Re-use get_paths as the singleton dep (same override target as other routers).
_PATHS_DEP = Depends(get_paths)

# RBAC gates — owner/admin only for all mutation + sensitive read routes.
_RBAC_ADMIN = Depends(require_role("owner", "admin"))


def _get_config() -> FoundryConfig:
    """Resolve a :class:`~research_foundry.config.FoundryConfig` per request.

    Mirrors :func:`~research_foundry.api.routers.runs.get_paths` so tests can
    override via ``app.dependency_overrides[_get_config]``.
    """
    return FoundryConfig.load()


_CONFIG_DEP = Depends(_get_config)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DEFAULT_RATE_LIMIT: dict[str, Any] = {}  # module-level default overrides (empty)


def _resolve_workspace_id(request: Request) -> str:
    """Return the caller's workspace_id, defaulting to ``"default"`` in no-auth mode."""
    identity = getattr(request.state, "identity", None)
    if identity is not None:
        return identity.workspace_id
    return "default"


def _read_rate_limit(request: Request, config: FoundryConfig) -> dict[str, Any]:
    """Merge in-memory overrides with config defaults to produce the current budget.

    ``enabled`` is always sourced from ``foundry.yaml`` (startup-only); it is
    never stored in ``app.state.rate_limit_overrides`` because the middleware
    reads ``self._limiter`` (wired at startup) and cannot be toggled at runtime
    via the admin API.
    """
    overrides: dict[str, Any] = getattr(
        getattr(getattr(request, "app", None), "state", None),
        "rate_limit_overrides",
        {},
    ) or {}
    return {
        "enabled": config.auth_rate_limit_enabled(),
        "window_seconds": overrides.get(
            "window_seconds", config.auth_rate_limit_window_seconds()
        ),
        "max_requests": overrides.get(
            "max_requests", config.auth_rate_limit_requests_per_window()
        ),
        "per_identity": True,
        "per_route": True,
    }


# ---------------------------------------------------------------------------
# GET /api/admin/workspace
# ---------------------------------------------------------------------------


@router.get(
    "/admin/workspace",
    summary="List workspace members and roles",
    tags=["admin"],
)
def get_workspace_members(
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_ADMIN,
) -> dict[str, Any]:
    """Return the member list for the caller's workspace.

    Returns ``members: null`` when the workspace has no recorded memberships
    (e.g. a freshly bootstrapped single-operator workspace that has not yet
    synced its token-configured identities to the durable RBAC store).

    Access: owner / admin only.  403 for all other authenticated roles.
    In single-operator mode (no identity), passes unconditionally.
    """
    workspace_id = _resolve_workspace_id(request)
    try:
        conn = rbac_store.bootstrap(paths)
        try:
            members = rbac_store.list_workspace_members(conn, workspace_id)
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("admin: failed to query workspace members: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to read workspace members") from exc

    return {
        "workspace_id": workspace_id,
        "members": members if members else None,
    }


# ---------------------------------------------------------------------------
# PATCH /api/admin/members/{user_id}/role
# ---------------------------------------------------------------------------


@router.patch(
    "/admin/members/{user_id}/role",
    summary="Update a workspace member's role",
    tags=["admin"],
)
def update_member_role(
    user_id: str,
    request: Request,
    body: dict[str, Any] = Body(...),
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_ADMIN,
) -> dict[str, Any]:
    """Update *user_id*'s role within the caller's workspace.

    Request body: ``{ "role": "<role_name>" }``

    ``role`` must be one of the canonical values: owner, admin, researcher,
    reviewer, viewer.  Invalid values are rejected by the RBAC store FK
    constraint.

    Returns 404 when the user has no existing membership in this workspace.
    Use ``PATCH /api/admin/workspace`` to invite new members (future P5 work).

    Access: owner / admin only.
    """
    role: str = body.get("role", "")
    if not role:
        raise HTTPException(status_code=422, detail="'role' field is required")

    workspace_id = _resolve_workspace_id(request)
    try:
        conn = rbac_store.bootstrap(paths)
        try:
            rbac_store.update_member_role(conn, user_id, workspace_id, role)
        finally:
            conn.close()
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Member {user_id!r} not found in workspace {workspace_id!r}",
        )
    except Exception as exc:
        logger.warning("admin: failed to update member role: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to update member role") from exc

    return {"user_id": user_id, "workspace_id": workspace_id, "role": role}


# ---------------------------------------------------------------------------
# GET /api/admin/auth-provider-status
# ---------------------------------------------------------------------------


@router.get(
    "/admin/auth-provider-status",
    summary="Active auth provider name and availability",
    tags=["admin"],
)
def get_auth_provider_status(
    config: FoundryConfig = _CONFIG_DEP,
    _rbac: None = _RBAC_ADMIN,
) -> dict[str, Any]:
    """Return the active auth provider name and whether it is operational.

    **Security invariant**: This endpoint NEVER returns raw credentials,
    JWKS secrets, Clerk secret keys, Bearer tokens, or any other private
    material.  Only the provider name and a boolean availability flag are
    included.

    ``available`` reflects whether the registered provider's
    :meth:`~research_foundry.api.auth.provider.AuthProvider.available` method
    returns ``True``.  For ``provider=none`` this is always ``True`` (no-op
    provider needs no external dependencies).

    Access: owner / admin only.
    """
    try:
        provider_name = config.auth_provider()
    except ValueError:
        # Unrecognised / unimplemented provider — report the raw value safely.
        provider_name = str(config.auth.get("provider", "none"))

    provider = get_provider(provider_name)
    available: bool
    details: Optional[str] = None

    if provider is None:
        # provider=none or not yet registered — always available, trivially.
        available = True
        if provider_name == "none":
            details = "Authentication disabled (provider=none)"
    else:
        try:
            available = provider.available()
        except Exception as exc:
            available = False
            # Surface a non-sensitive summary only — no exception chain leakage.
            details = f"Provider availability check failed: {type(exc).__name__}"

    result: dict[str, Any] = {
        "provider": provider_name,
        "available": available,
    }
    if details is not None:
        result["details"] = details
    return result


# ---------------------------------------------------------------------------
# GET /api/admin/rate-limit-config
# ---------------------------------------------------------------------------


@router.get(
    "/admin/rate-limit-config",
    summary="Current rate-limit budget",
    tags=["admin"],
)
def get_rate_limit_config(
    request: Request,
    config: FoundryConfig = _CONFIG_DEP,
    _rbac: None = _RBAC_ADMIN,
) -> dict[str, Any]:
    """Return the current per-(identity, route) rate-limit budget.

    Reflects any in-memory updates applied via ``PATCH /api/admin/rate-limit-config``.

    ``per_identity`` and ``per_route`` are always ``true`` — they document the
    keying strategy (one counter per ``(user_id, route)`` pair) rather than a
    configurable option.

    Access: owner / admin only.
    """
    return _read_rate_limit(request, config)


# ---------------------------------------------------------------------------
# PATCH /api/admin/rate-limit-config
# ---------------------------------------------------------------------------


@router.patch(
    "/admin/rate-limit-config",
    summary="Update rate-limit budget (in-memory, until next restart)",
    tags=["admin"],
)
def update_rate_limit_config(
    request: Request,
    body: dict[str, Any] = Body(...),
    config: FoundryConfig = _CONFIG_DEP,
    _rbac: None = _RBAC_ADMIN,
) -> dict[str, Any]:
    """Apply in-memory overrides to the rate-limit budget.

    Only the keys present in the body are updated; omitted keys retain their
    current value.  Changes take effect for **new** requests immediately but
    are not persisted to ``foundry.yaml`` — a server restart restores the
    config-file defaults.

    Accepted body fields:
      ``max_requests``   (int)  — max requests per window per (user, route)
      ``window_seconds`` (int)  — sliding window width in seconds

    **Startup-only field (cannot be changed here)**:
      ``enabled`` is wired into ``RateLimitMiddleware`` at startup from
      ``foundry.yaml`` (``auth.rate_limit.enabled``).  The middleware reads
      ``self._limiter`` only — it never consults ``app.state`` — so sending
      ``enabled`` in the body has no effect on the running limiter.  Any
      ``enabled`` key in the request body is silently ignored.

    Returns the full updated config object on success.

    Access: owner / admin only.
    """
    app_state = getattr(getattr(request, "app", None), "state", None)
    if app_state is None:
        raise HTTPException(status_code=500, detail="App state unavailable")

    # Ensure overrides dict exists (should have been initialised by create_app).
    if not hasattr(app_state, "rate_limit_overrides"):
        app_state.rate_limit_overrides = {}

    overrides: dict[str, Any] = app_state.rate_limit_overrides

    # NOTE: "enabled" is intentionally not processed here.  It is a startup-only
    # decision driven by foundry.yaml (auth.rate_limit.enabled) and wired into
    # RateLimitMiddleware at process start.  The middleware reads self._limiter
    # only; it never reads app.state, so toggling enabled here would have no
    # effect.  Any "enabled" key in the request body is silently ignored.

    if "max_requests" in body:
        try:
            val = int(body["max_requests"])
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="'max_requests' must be an integer") from exc
        if val <= 0:
            raise HTTPException(
                status_code=422,
                detail="'max_requests' must be >= 1 (same boundary as startup config)",
            )
        overrides["max_requests"] = val

    if "window_seconds" in body:
        try:
            val = int(body["window_seconds"])
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="'window_seconds' must be an integer") from exc
        if val <= 0:
            raise HTTPException(
                status_code=422,
                detail="'window_seconds' must be >= 1 (same boundary as startup config)",
            )
        overrides["window_seconds"] = val

    return _read_rate_limit(request, config)


# ---------------------------------------------------------------------------
# GET /api/admin/rbac-status
# ---------------------------------------------------------------------------


@router.get(
    "/admin/rbac-status",
    summary="RBAC enforcement state (read-only; any authenticated user)",
    tags=["admin"],
)
def get_rbac_status(
    request: Request,
    config: FoundryConfig = _CONFIG_DEP,
) -> dict[str, Any]:
    """Return the current RBAC enforcement configuration.

    Unlike other admin endpoints this route is accessible by **any
    authenticated user** (no owner/admin gate) so that client-side code can
    check whether the server is running in enforced or pass-through mode.

    In single-operator mode (``auth.provider=none``, no identity on
    ``request.state``) the endpoint is also accessible unconditionally.

    Response shape:
    ``rbac_enforcement``  (str)  — raw configured value (auto / disabled / enabled)
    ``rbac_enforced``     (bool) — resolved effective state stored on app.state
    ``auth_provider``     (str)  — active auth.provider value
    """
    # Resolved effective state (written by create_app).
    app_state = getattr(getattr(request, "app", None), "state", None)
    rbac_enforced: bool = bool(getattr(app_state, "rbac_enforced", False))

    try:
        enforcement = config.auth_rbac_enforcement()
        enforcement_str = enforcement.value
    except ValueError:
        enforcement_str = str(config.auth.get("rbac_enforcement", "auto"))

    try:
        provider_name = config.auth_provider()
    except ValueError:
        provider_name = str(config.auth.get("provider", "none"))

    return {
        "rbac_enforcement": enforcement_str,
        "rbac_enforced": rbac_enforced,
        "auth_provider": provider_name,
    }


__all__ = ["router"]
