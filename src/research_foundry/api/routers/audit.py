"""Audit log API router (public-multiuser-release Phase 5, AUDIT-003).

Exposes read-only access to the append-only audit event log.

Endpoints:
  GET /api/audit                    — paginated list of audit events
  GET /api/audit/{audit_event_id}   — single audit event detail
  GET /api/audit/health             — audit store health state

All data flows through :mod:`~research_foundry.services.audit_service`
(R1 invariant): handlers never touch the sqlite3 DB directly.

Access control: all three routes require ``owner`` or ``admin`` role (RBAC-006).
In single-operator mode (auth.provider=none / no identity on request.state),
the gate passes unconditionally per the require_role semantics in
:mod:`~research_foundry.api.auth.rbac`.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..auth.rbac import require_role
from ...paths import FoundryPaths
from ...services import audit_service
from .runs import get_paths

router = APIRouter()

# Module-level singletons (ruff B008: avoid calling Depends() in an argument
# default expression).  Wraps the same get_paths callable that
# app.dependency_overrides[get_paths] targets in tests, so overriding still
# works regardless of where the Depends() instance was constructed.
_PATHS_DEP = Depends(get_paths)

# RBAC-006: audit data contains actor IDs, workspace IDs, policy snapshots, and
# failure details — admin-class data.  Gate all three audit routes on owner/admin.
# Single-operator mode (no identity on request.state) passes unconditionally.
_RBAC_AUDIT = Depends(require_role("owner", "admin"))


@router.get("/audit", summary="List audit events (paginated)")
def list_audit_events(
    request: Request,
    mutation_type: str | None = Query(None, description="Filter by mutation type"),
    actor: str | None = Query(None, description="Filter by actor user id"),
    workspace: str | None = Query(
        None,
        description=(
            "Filter by workspace id. Ignored once workspace isolation "
            "enforcement is active for an authenticated caller — the "
            "caller's own workspace always wins (DI-1, Phase 4 ACT-401)."
        ),
    ),
    since: str | None = Query(None, description="ISO-8601 lower bound (inclusive)"),
    until: str | None = Query(None, description="ISO-8601 upper bound (inclusive)"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    cursor: str | None = Query(None, description="Pagination cursor (last audit_event_id from prior page)"),
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_AUDIT,
) -> dict[str, Any]:
    """Return a cursor-paginated list of audit events, most-recent-first.

    Pass ``cursor`` (the ``next_cursor`` value from a prior response) to
    retrieve the next page.  An empty audit log returns ``{"items": [],
    "next_cursor": null, "total_hint": null}`` — never 404.

    DI-1 (Phase 4 ACT-401): ``owner``/``admin`` (the RBAC-006 gate above) is
    a workspace-scoped role, so ``identity`` is threaded into
    :func:`~research_foundry.services.audit_service.list_events` — once
    isolation enforcement is active, the caller's own workspace always wins
    over the ``workspace`` query param.
    """
    identity = getattr(request.state, "identity", None)
    return audit_service.list_events(
        paths,
        mutation_type=mutation_type,
        actor_user_id=actor,
        workspace_id=workspace,
        since=since,
        until=until,
        limit=limit,
        cursor=cursor,
        identity=identity,
    )


@router.get("/audit/health", summary="Audit store health state")
def get_audit_health(
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_AUDIT,
) -> dict[str, Any]:
    """Return the persisted health state of the audit store.

    This is a read-only endpoint — it returns the last persisted probe
    result from ``audit_health`` without triggering a new probe.

    ``status`` is ``"healthy"`` when the store is operational or has never
    been probed; ``"degraded"`` when the last probe detected a failure.
    """
    state = audit_service.get_health_state(paths)
    return {
        "status": "healthy" if state.healthy else "degraded",
        "healthy": state.healthy,
        "last_probe_at": state.last_probe_at,
        "last_success_at": state.last_success_at,
        "error_detail": state.error_detail if not state.healthy else None,
    }


@router.get("/audit/{audit_event_id}", summary="Get a single audit event")
def get_audit_event(
    audit_event_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_AUDIT,
) -> dict[str, Any]:
    """Return the full detail for *audit_event_id*.

    404 when the id is unknown, OR when it exists but belongs to another
    workspace under active isolation enforcement (DI-1, Phase 4 ACT-401) —
    indistinguishable from "unknown", never a distinct 403 (no confirmation
    that a cross-workspace event exists).
    """
    identity = getattr(request.state, "identity", None)
    event = audit_service.get_event(paths, audit_event_id, identity=identity)
    if event is None:
        raise HTTPException(status_code=404, detail="audit event not found")
    return event


__all__ = ["router"]
