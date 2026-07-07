"""Audit log API router (public-multiuser-release Phase 5, AUDIT-003).

Exposes read-only access to the append-only audit event log.

Endpoints:
  GET /api/audit                    — paginated list of audit events
  GET /api/audit/{audit_event_id}   — single audit event detail

All data flows through :mod:`~research_foundry.services.audit_service`
(R1 invariant): handlers never touch the sqlite3 DB directly.

NOTE(P5.9): ``require_role("admin")`` guards are intentionally absent from
this phase — they depend on P5.2 (RBAC middleware) which ships in a later
batch.  Add them once P5.2 merges.
"""

from __future__ import annotations

# TODO(P5.9): add require_role("admin") once P5.2 merges
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ...paths import FoundryPaths
from ...services import audit_service
from .runs import get_paths

router = APIRouter()

# Module-level singleton (ruff B008: avoid calling Depends() in an argument
# default expression).  Wraps the same get_paths callable that
# app.dependency_overrides[get_paths] targets in tests, so overriding still
# works regardless of where the Depends() instance was constructed.
_PATHS_DEP = Depends(get_paths)


@router.get("/audit", summary="List audit events (paginated)")
def list_audit_events(
    mutation_type: str | None = Query(None, description="Filter by mutation type"),
    actor: str | None = Query(None, description="Filter by actor user id"),
    workspace: str | None = Query(None, description="Filter by workspace id"),
    since: str | None = Query(None, description="ISO-8601 lower bound (inclusive)"),
    until: str | None = Query(None, description="ISO-8601 upper bound (inclusive)"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    cursor: str | None = Query(None, description="Pagination cursor (last audit_event_id from prior page)"),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Return a cursor-paginated list of audit events, most-recent-first.

    Pass ``cursor`` (the ``next_cursor`` value from a prior response) to
    retrieve the next page.  An empty audit log returns ``{"items": [],
    "next_cursor": null, "total_hint": null}`` — never 404.
    """
    return audit_service.list_events(
        paths,
        mutation_type=mutation_type,
        actor_user_id=actor,
        workspace_id=workspace,
        since=since,
        until=until,
        limit=limit,
        cursor=cursor,
    )


@router.get("/audit/health", summary="Audit store health state")
def get_audit_health(
    paths: FoundryPaths = _PATHS_DEP,
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
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Return the full detail for *audit_event_id*.

    404 when the id is unknown.
    """
    event = audit_service.get_event(paths, audit_event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="audit event not found")
    return event


__all__ = ["router"]
