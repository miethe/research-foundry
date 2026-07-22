"""Admin settings API router (public-multiuser-release Phase 5, P5.6 T2;
extended Phase 3 (public-multiuser-release-activation), ACT-301..303).

Exposes workspace-management, auth-provider status, rate-limit config,
service-account + personal-access-token (PAT) management, and
deployment-mode-status endpoints that the admin settings panel (P5.8)
consumes.

Role gating
-----------
Every route in this router except the two documented self-service exceptions
below is gated with ``require_role("owner", "admin")`` from
:mod:`~research_foundry.api.auth.rbac`. No other bespoke auth checks are used
for those routes.

Self-service exceptions (manual RBAC, NOT ``Depends(require_role(...))``):
  * ``GET /api/admin/rbac-status`` — any authenticated user (pre-existing).
  * ``POST/GET /api/admin/pats``, ``DELETE /api/admin/pats/{token_id}`` — any
    authenticated user may self-issue/list/revoke their OWN PATs; acting on
    another user's PAT requires owner/admin (403, not a 404-leak — see the
    PAT section below). These routes are exempt from the blanket
    ``require_role`` route-sweep check for the same documented reason
    ``reports.py``'s ``publish-preview`` route is: the permission decision
    depends on request BODY/PATH content (whose PAT), not just the caller's
    role, so it cannot be expressed as a single static ``Depends(...)``.

Endpoints
---------
GET   /api/admin/workspace                              — member list for caller's workspace
PATCH /api/admin/members/{user_id}/role                  — update a member's role
GET   /api/admin/auth-provider-status                    — active provider + availability
GET   /api/admin/rate-limit-config                       — current rate-limit budget
PATCH /api/admin/rate-limit-config                       — update rate-limit budget (in-memory)
GET   /api/admin/rbac-status                              — RBAC enforcement state (any authed user)
POST  /api/admin/service-accounts                         — create a service account
GET   /api/admin/service-accounts                         — list service accounts (paginated)
DELETE /api/admin/service-accounts/{id}                   — disable a service account
POST  /api/admin/service-accounts/{id}/tokens             — issue/rotate its access token
GET   /api/admin/service-accounts/{id}/tokens             — list its tokens (paginated, no secrets)
DELETE /api/admin/service-accounts/{id}/tokens/{token_id} — revoke a specific token
POST  /api/admin/pats                                      — issue a PAT (self, or on-behalf via owner/admin)
GET   /api/admin/pats                                      — list PATs (self, or any via owner/admin)
DELETE /api/admin/pats/{token_id}                          — revoke a PAT (self, or any via owner/admin)
GET   /api/admin/deployment-mode-status                    — resolved deployment_mode + gate conditions

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

Service accounts / PATs / tokens (Phase 3, ACT-301/ACT-302)
-------------------------------------------------------------
POST /api/admin/service-accounts
    body: { "name": str, "role": str, "description"?: str }
    → 201 { "id", "name", "workspace_id", "role", "description", "created_by",
             "created_at", "disabled_at" } — NEVER a token/secret.

GET /api/admin/service-accounts?limit=&offset=
    → { "items": [...same shape as above...], "total": int, "limit": int, "offset": int }

DELETE /api/admin/service-accounts/{id}
    → { "id": str, "disabled": true } ; 404 if unknown or in another workspace.

POST /api/admin/service-accounts/{id}/tokens
    body: { "expires_at"?: str }
    Issues a fresh token for the account, revoking any prior ACTIVE token for
    it first (rotate-on-issue — never more than one live token per service
    account). → 201 { "token_id", "plaintext", "token_prefix",
    "principal_type", "principal_id", "workspace_id", "role", "expires_at" }
    **``plaintext`` is shown here ONLY — never again, never logged.**

GET /api/admin/service-accounts/{id}/tokens?limit=&offset=
    → { "items": [{"token_id","token_prefix","created_at","expires_at",
                    "revoked_at","last_used_at"}...], "total", "limit", "offset" }
    NEVER includes ``token_hash`` or a plaintext secret.

DELETE /api/admin/service-accounts/{id}/tokens/{token_id}
    → { "token_id": str, "revoked": true } ; 404 if unknown / wrong account.

POST /api/admin/pats
    body: { "role": str, "expires_at"?: str, "user_id"?: str }
    Self-issues a PAT for the caller by default. Setting ``user_id`` to
    someone else requires the caller's role to include owner/admin (403
    otherwise). → 201, same shape as the service-account token response.
    **``plaintext`` is shown here ONLY.**

GET /api/admin/pats?user_id=&limit=&offset=
    Lists the caller's own PATs by default; ``user_id`` targeting another
    user requires owner/admin (403, never a silent empty list).
    → { "items": [...token metadata, no secrets...], "total", "limit", "offset" }

DELETE /api/admin/pats/{token_id}
    Revokes a PAT. Non-owner/admin callers may only revoke their OWN PAT —
    a same-workspace PAT belonging to someone else yields 403 (existence is
    knowable, action is denied); a PAT in a different workspace yields 404
    (existence is not confirmed, mirroring ``audit.py``'s cross-workspace
    convention). → { "token_id": str, "revoked": true }

GET /api/admin/deployment-mode-status
    { "deployment_mode": str, "gate_applicable": bool, "gate_passed": bool,
      "conditions": [{"id": "a".."d", "passed": bool, "detail": str}, ...] }
    Read-only introspection over the FR-4 multi_user startup gate
    (:meth:`~research_foundry.config.FoundryConfig.deployment_mode_validate`).
    ``conditions`` is empty when ``deployment_mode=single_user`` (gate is a
    no-op). NEVER includes secret material.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

from ..auth.provider import get_provider
from ..auth.rbac import require_role
from ...config import FoundryConfig
from ...paths import FoundryPaths
from ...services import audit_service, rbac_store, token_service
from ...services.audit_service import AuditEvent
from ...services.token_service import RoleCeilingError, TokenServiceError
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


def _get_identity(request: Request) -> Optional[Any]:
    """Return ``request.state.identity`` (an ``AuthIdentity``) or ``None``.

    Thin, named wrapper around the ``getattr(..., None)`` pattern used
    throughout this router — kept as a single call site for the Phase 3
    token/PAT routes below, which (unlike the pre-existing routes) need to
    branch on identity presence/role for manual, request-content-dependent
    RBAC (see the module docstring's "Self-service exceptions" section).
    """
    return getattr(request.state, "identity", None)


def _is_owner_or_admin(identity: Optional[Any]) -> bool:
    """True when *identity* is present and carries the owner or admin role."""
    if identity is None:
        return False
    return bool({"owner", "admin"} & set(identity.roles))


def _paginate(items: list[dict], *, limit: int, offset: int) -> dict[str, Any]:
    """Return the standard ``{"items", "total", "limit", "offset"}`` page envelope.

    Simple offset-slice pagination over an already-materialized list — the
    admin-scoped listings this backs (service accounts, tokens, PATs within
    one workspace) are expected to be small, so no cursor/DB-level LIMIT is
    needed. Mirrors ``audit.py``'s pagination *shape* (an ``items`` array
    plus paging metadata) without inheriting its cursor mechanics, which are
    unnecessary at this data volume.
    """
    total = len(items)
    return {
        "items": items[offset : offset + limit],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


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

    Phase 3 ACT-303: every successful update produces exactly one
    ``audit_event`` row (``mutation_type="role_change"``), recorded AFTER the
    mutation commits (fail-open — an audit-write failure here can never turn
    a successful role update into an error response).
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

    identity = _get_identity(request)
    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="role_change",
            action="member_role_updated",
            target_ref=user_id,
            actor_user_id=identity.user_id if identity is not None else None,
            actor_workspace_id=workspace_id,
            result="success",
        ),
    )

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


# ---------------------------------------------------------------------------
# Token response helpers (Phase 3, ACT-301/ACT-302)
# ---------------------------------------------------------------------------


def _issued_token_response(issued: Any) -> dict[str, Any]:
    """Serialize an ``IssuedToken`` for a one-time issuance response.

    This is the ONLY place ``plaintext`` is ever put into a response body in
    this router — every other token-shaped response goes through
    :func:`_token_metadata` instead, which omits it.
    """
    return {
        "token_id": issued.token_id,
        "plaintext": issued.plaintext,
        "token_prefix": issued.token_prefix,
        "principal_type": issued.principal_type,
        "principal_id": issued.principal_id,
        "workspace_id": issued.workspace_id,
        "role": issued.role,
        "expires_at": issued.expires_at,
    }


def _token_metadata(row: dict[str, Any]) -> dict[str, Any]:
    """Project an access-token row for list/get display — NEVER a secret.

    *row* is one of the dicts returned by ``token_service.list_tokens`` /
    ``token_service.get_token``, both of which already omit ``token_hash``
    at the data layer. This helper is a second, router-level enforcement of
    the same invariant, plus an explicit denylist of the plaintext key name,
    so a future change to the token_service row shape cannot silently leak a
    secret through this endpoint.
    """
    return {
        "token_id": row["id"],
        "principal_type": row["principal_type"],
        "principal_id": row["principal_id"],
        "workspace_id": row["workspace_id"],
        "role": row["role"],
        "token_prefix": row["token_prefix"],
        "created_by": row.get("created_by"),
        "created_at": row.get("created_at"),
        "expires_at": row.get("expires_at"),
        "revoked_at": row.get("revoked_at"),
        "last_used_at": row.get("last_used_at"),
    }


# ---------------------------------------------------------------------------
# Service accounts (Phase 3, ACT-301)
# ---------------------------------------------------------------------------


def _service_account_response(account: dict[str, Any]) -> dict[str, Any]:
    """Project a ``service_accounts`` row for display.

    Never a secret — accounts themselves never hold one; only their tokens
    do (see :func:`_issued_token_response` / :func:`_token_metadata`).
    """
    return {
        "id": account["id"],
        "name": account["name"],
        "workspace_id": account["workspace_id"],
        "role": account["role"],
        "description": account.get("description"),
        "created_by": account.get("created_by"),
        "created_at": account.get("created_at"),
        "disabled_at": account.get("disabled_at"),
    }


def _get_service_account_or_404(
    paths: FoundryPaths, account_id: str, workspace_id: str
) -> dict[str, Any]:
    """Return the ``service_accounts`` row for *account_id*, scoped to *workspace_id*.

    404s uniformly for "unknown id" and "exists but in another workspace" —
    the same cross-workspace-existence-hiding convention ``audit.py`` uses.
    """
    conn = rbac_store.bootstrap(paths)
    try:
        account = rbac_store.get_service_account(conn, account_id)
    finally:
        conn.close()
    if account is None or account["workspace_id"] != workspace_id:
        raise HTTPException(status_code=404, detail=f"Service account {account_id!r} not found")
    return account


@router.post(
    "/admin/service-accounts",
    status_code=201,
    summary="Create a service account",
    tags=["admin"],
)
def create_service_account(
    request: Request,
    body: dict[str, Any] = Body(...),
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_ADMIN,
) -> dict[str, Any]:
    """Create a new service account with a single fixed role (FR-8).

    Request body: ``{ "name": str, "role": str, "description"?: str }``.
    Never returns a token — call ``POST .../{id}/tokens`` next to obtain one.

    Access: owner / admin only.
    """
    name: str = str(body.get("name") or "").strip()
    role: str = str(body.get("role") or "")
    description: Optional[str] = body.get("description")
    if not name:
        raise HTTPException(status_code=422, detail="'name' field is required")
    if role not in token_service.VALID_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"'role' must be one of: {', '.join(sorted(token_service.VALID_ROLES))}",
        )

    workspace_id = _resolve_workspace_id(request)
    identity = _get_identity(request)
    account_id = f"svc_{uuid.uuid4().hex}"

    conn = rbac_store.bootstrap(paths)
    try:
        rbac_store.create_service_account(
            conn,
            service_account_id=account_id,
            name=name,
            workspace_id=workspace_id,
            role=role,
            description=description,
            created_by=identity.user_id if identity is not None else None,
        )
        account = rbac_store.get_service_account(conn, account_id)
    finally:
        conn.close()

    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="principal_mutation",
            action="service_account_created",
            target_ref=account_id,
            actor_user_id=identity.user_id if identity is not None else None,
            actor_workspace_id=workspace_id,
            result="success",
        ),
    )
    if account is None:  # pragma: no cover — defensive; just created in the same call.
        raise HTTPException(status_code=500, detail="Service account created but could not be re-read")
    return _service_account_response(account)


@router.get(
    "/admin/service-accounts",
    summary="List service accounts (paginated)",
    tags=["admin"],
)
def list_service_accounts_route(
    request: Request,
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_ADMIN,
) -> dict[str, Any]:
    """List service accounts in the caller's workspace.

    Access: owner / admin only.
    """
    workspace_id = _resolve_workspace_id(request)
    conn = rbac_store.bootstrap(paths)
    try:
        accounts = rbac_store.list_service_accounts(conn, workspace_id=workspace_id)
    finally:
        conn.close()
    return _paginate(
        [_service_account_response(a) for a in accounts], limit=limit, offset=offset
    )


@router.delete(
    "/admin/service-accounts/{account_id}",
    summary="Disable a service account",
    tags=["admin"],
)
def disable_service_account_route(
    account_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_ADMIN,
) -> dict[str, Any]:
    """Disable *account_id* (idempotent).

    Disabling does not itself revoke previously-issued tokens as a separate
    step — ``token_service.verify_token`` independently checks
    ``disabled_at`` at every resolution, so the practical effect is
    immediate regardless (see ``rbac_store.disable_service_account``).

    404 when unknown or in another workspace.

    Access: owner / admin only.
    """
    workspace_id = _resolve_workspace_id(request)
    _get_service_account_or_404(paths, account_id, workspace_id)

    conn = rbac_store.bootstrap(paths)
    try:
        rbac_store.disable_service_account(conn, account_id)
    finally:
        conn.close()

    identity = _get_identity(request)
    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="principal_mutation",
            action="service_account_disabled",
            target_ref=account_id,
            actor_user_id=identity.user_id if identity is not None else None,
            actor_workspace_id=workspace_id,
            result="success",
        ),
    )
    return {"id": account_id, "disabled": True}


@router.post(
    "/admin/service-accounts/{account_id}/tokens",
    status_code=201,
    summary="Issue (or rotate) a service account's access token",
    tags=["admin"],
)
def issue_service_account_token_route(
    account_id: str,
    request: Request,
    body: dict[str, Any] = Body(default={}),
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_ADMIN,
) -> dict[str, Any]:
    """Issue a fresh access token for *account_id*, rotating out any prior
    active token for it first (FR-8; rotate-on-issue — a service account
    never has more than one live token).

    Request body: ``{ "expires_at"?: str }`` (both optional; may be omitted).

    **``plaintext`` in the response is shown here ONLY** — it is never
    persisted, logged, or returned by any other route in this router.

    404 when *account_id* is unknown or in another workspace.

    Access: owner / admin only.
    """
    workspace_id = _resolve_workspace_id(request)
    _get_service_account_or_404(paths, account_id, workspace_id)

    identity = _get_identity(request)
    try:
        issued = token_service.rotate_service_account_token(
            paths,
            service_account_id=account_id,
            created_by=identity.user_id if identity is not None else None,
            expires_at=body.get("expires_at"),
        )
    except TokenServiceError as exc:
        # The only way to reach here after the existence check above is a
        # disabled account (a race with a concurrent disable) — 409
        # Conflict, not 404 (we already KNOW the account exists).
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="access_token_issued",
            action="service_account_token_rotated",
            target_ref=issued.token_id,
            actor_user_id=identity.user_id if identity is not None else None,
            actor_workspace_id=workspace_id,
            result="success",
        ),
    )
    return _issued_token_response(issued)


@router.get(
    "/admin/service-accounts/{account_id}/tokens",
    summary="List a service account's tokens (paginated, no secrets)",
    tags=["admin"],
)
def list_service_account_tokens_route(
    account_id: str,
    request: Request,
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_ADMIN,
) -> dict[str, Any]:
    """List *account_id*'s tokens.

    NEVER includes ``token_hash`` or a plaintext secret.

    404 when *account_id* is unknown or in another workspace.

    Access: owner / admin only.
    """
    workspace_id = _resolve_workspace_id(request)
    _get_service_account_or_404(paths, account_id, workspace_id)
    rows = token_service.list_tokens(paths, principal_id=account_id, principal_type="service")
    return _paginate([_token_metadata(r) for r in rows], limit=limit, offset=offset)


@router.delete(
    "/admin/service-accounts/{account_id}/tokens/{token_id}",
    summary="Revoke a specific service-account token",
    tags=["admin"],
)
def revoke_service_account_token_route(
    account_id: str,
    token_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_ADMIN,
) -> dict[str, Any]:
    """Revoke *token_id*, provided it belongs to *account_id* in the caller's workspace.

    404 when the token is unknown, belongs to a different account, is not a
    service-account token, or is in another workspace — never confirms
    existence of a token outside the caller's own service account/workspace.

    Access: owner / admin only.
    """
    workspace_id = _resolve_workspace_id(request)
    _get_service_account_or_404(paths, account_id, workspace_id)

    token = token_service.get_token(paths, token_id)
    if (
        token is None
        or token["principal_type"] != "service"
        or token["principal_id"] != account_id
        or token["workspace_id"] != workspace_id
    ):
        raise HTTPException(status_code=404, detail=f"Token {token_id!r} not found")

    token_service.revoke_token(paths, token_id)

    identity = _get_identity(request)
    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="access_token_revoked",
            action="service_account_token_revoked",
            target_ref=token_id,
            actor_user_id=identity.user_id if identity is not None else None,
            actor_workspace_id=workspace_id,
            result="success",
        ),
    )
    return {"token_id": token_id, "revoked": True}


# ---------------------------------------------------------------------------
# Personal access tokens / PATs (Phase 3, ACT-302)
#
# NOT gated with Depends(require_role(...)) — see the module docstring's
# "Self-service exceptions" section. Every route below enforces RBAC
# manually: any authenticated (or no-auth/single-operator-trust) caller may
# act on their OWN PAT; acting on ANOTHER user's PAT requires owner/admin.
# ---------------------------------------------------------------------------


@router.post(
    "/admin/pats",
    status_code=201,
    summary="Issue a personal access token (self, or on-behalf via owner/admin)",
    tags=["admin"],
)
def issue_pat(
    request: Request,
    body: dict[str, Any] = Body(...),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Issue a PAT.

    Request body: ``{ "role": str, "expires_at"?: str, "user_id"?: str }``.

    Self-issues for the caller by default (``user_id`` defaults to the
    caller's own identity). Setting ``user_id`` to a DIFFERENT user requires
    the caller to hold owner/admin (403 otherwise) — e.g. an admin
    provisioning a PAT on behalf of another workspace member.

    Role-ceiling (FR-9): *role* must be <= the target user's CURRENT role in
    the workspace; :func:`token_service.issue_user_pat` enforces this and
    independently re-checks it at every resolution (a later role downgrade
    for the target user invalidates the PAT's elevated privilege
    immediately, no restart required).

    **``plaintext`` in the response is shown here ONLY.**

    422 when ``user_id`` is omitted AND there is no caller identity (no
    "self" to default to in single-operator/no-auth mode — the caller must
    say who the PAT is for).
    """
    role: str = str(body.get("role") or "")
    if role not in token_service.VALID_ROLES:
        raise HTTPException(
            status_code=422,
            detail=f"'role' must be one of: {', '.join(sorted(token_service.VALID_ROLES))}",
        )

    identity = _get_identity(request)
    target_user_id: Optional[str] = body.get("user_id") or (
        identity.user_id if identity is not None else None
    )
    if not target_user_id:
        raise HTTPException(
            status_code=422,
            detail="'user_id' is required when there is no caller identity",
        )
    if (
        identity is not None
        and target_user_id != identity.user_id
        and not _is_owner_or_admin(identity)
    ):
        raise HTTPException(
            status_code=403,
            detail="Insufficient role to issue a PAT on behalf of another user",
        )

    workspace_id = _resolve_workspace_id(request)
    try:
        issued = token_service.issue_user_pat(
            paths,
            issuer_user_id=target_user_id,
            workspace_id=workspace_id,
            role=role,
            expires_at=body.get("expires_at"),
        )
    except RoleCeilingError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TokenServiceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="access_token_issued",
            action="pat_issued",
            target_ref=issued.token_id,
            actor_user_id=identity.user_id if identity is not None else None,
            actor_workspace_id=workspace_id,
            result="success",
        ),
    )
    return _issued_token_response(issued)


@router.get(
    "/admin/pats",
    summary="List personal access tokens (self, or any via owner/admin)",
    tags=["admin"],
)
def list_pats(
    request: Request,
    user_id: Optional[str] = Query(None, description="Target user id (defaults to caller)"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """List PATs.

    Defaults to the caller's OWN PATs. Passing ``user_id`` to target a
    DIFFERENT user requires owner/admin (403 — never a silently-empty list,
    so a caller can't mistake "no permission" for "no PATs").

    In single-operator/no-auth mode (no caller identity), an omitted
    ``user_id`` lists every PAT in the workspace — matches this router's
    existing no-identity passthrough (see ``require_role``'s absent-identity
    semantics).
    """
    identity = _get_identity(request)
    workspace_id = _resolve_workspace_id(request)

    target_user_id = user_id
    if identity is not None:
        if target_user_id is None:
            target_user_id = identity.user_id
        elif target_user_id != identity.user_id and not _is_owner_or_admin(identity):
            raise HTTPException(
                status_code=403,
                detail="Insufficient role to list another user's PATs",
            )

    rows = token_service.list_tokens(
        paths,
        workspace_id=workspace_id,
        principal_id=target_user_id,
        principal_type="user_pat",
    )
    return _paginate([_token_metadata(r) for r in rows], limit=limit, offset=offset)


@router.delete(
    "/admin/pats/{token_id}",
    summary="Revoke a personal access token (self, or any via owner/admin)",
    tags=["admin"],
)
def revoke_pat(
    token_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Revoke a PAT by id.

    404 when the token is unknown, is a service-account token (not a PAT —
    hidden behind this endpoint's 404 rather than exposed as "wrong type"),
    or belongs to a DIFFERENT workspace (existence not confirmed, mirroring
    ``audit.py``'s cross-workspace convention).

    403 when the token exists in the caller's OWN workspace but belongs to a
    different user AND the caller lacks owner/admin — existence is knowable
    here (the caller is a legitimate member of that workspace) but the
    action is denied; never a 404-leak (ACT-302 acceptance criteria).
    """
    identity = _get_identity(request)

    token = token_service.get_token(paths, token_id)
    if token is None or token["principal_type"] != "user_pat":
        raise HTTPException(status_code=404, detail=f"PAT {token_id!r} not found")
    if identity is not None and token["workspace_id"] != identity.workspace_id:
        # Cross-workspace: hide existence entirely (404), never a 403.
        raise HTTPException(status_code=404, detail=f"PAT {token_id!r} not found")
    if (
        identity is not None
        and token["principal_id"] != identity.user_id
        and not _is_owner_or_admin(identity)
    ):
        raise HTTPException(
            status_code=403,
            detail="Insufficient role to revoke another user's PAT",
        )

    token_service.revoke_token(paths, token_id)

    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="access_token_revoked",
            action="pat_revoked",
            target_ref=token_id,
            actor_user_id=identity.user_id if identity is not None else None,
            actor_workspace_id=token["workspace_id"],
            result="success",
        ),
    )
    return {"token_id": token_id, "revoked": True}


# ---------------------------------------------------------------------------
# GET /api/admin/deployment-mode-status (Phase 3, ACT-303)
# ---------------------------------------------------------------------------


@router.get(
    "/admin/deployment-mode-status",
    summary="Resolved deployment_mode + FR-4 startup-gate condition status",
    tags=["admin"],
)
def get_deployment_mode_status(
    config: FoundryConfig = _CONFIG_DEP,
    _rbac: None = _RBAC_ADMIN,
) -> dict[str, Any]:
    """Return the resolved ``deployment_mode`` and, for ``multi_user``, the
    pass/fail status of every FR-4 startup-gate condition (a)-(d).

    Read-only introspection over
    :meth:`~research_foundry.config.FoundryConfig.deployment_mode_validate`
    (via the shared, non-raising
    :meth:`~research_foundry.config.FoundryConfig.deployment_mode_status`
    helper) — this endpoint NEVER raises the way the startup gate does, so
    an operator can inspect why a multi_user deployment would refuse to
    start without taking the server down.

    ``conditions`` is an empty list when ``deployment_mode=single_user``
    (the gate is a no-op outside multi_user).

    **Never returns secret material** — every condition ``detail`` only
    ever names config keys, resolved booleans, or file paths (identical to
    the text ``deployment_mode_validate`` raises with).

    Access: owner / admin only.
    """
    return config.deployment_mode_status()


__all__ = ["router"]
