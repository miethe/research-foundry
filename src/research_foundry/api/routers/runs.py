"""Runs API router — Phase P2 read endpoints.

All data paths route through the export service (R1 invariant):
  - list_runs()   → export_service.list_runs(paths)
  - export_run()  → export_service.export_run(paths, run_id)
  - claims slice  → export_run(...)["claims"]
  - source lookup → scan export_run(...)["claims"][*]["sources"]

Raw run artifact files are NEVER read directly here; all sensitivity
gating is enforced inside the export service before data reaches these
handlers.

Endpoint → client.ts mapping:
  GET /api/runs                              → fetchRunList()
  GET /api/runs/{run_id}                     → fetchRunDetail()
  GET /api/runs/{run_id}/claims              → fetchClaimLedger()
  GET /api/runs/{run_id}/sources/{sc_id}     → fetchSourceCard()

The /data/governance.json route is defined in app.py (not under /api).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ...config import FoundryConfig
from ...paths import FoundryPaths
from ...services.export_service import (
    SENSITIVITY_ORDER,
    ExportError,
    export_run,
    list_runs,
    resolve_threshold,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency: FoundryPaths
# ---------------------------------------------------------------------------

def get_paths() -> FoundryPaths:
    """Resolve :class:`FoundryPaths` from the workspace config.

    Called per-request via FastAPI dependency injection so that tests can
    override it without monkeypatching module globals.
    """
    return FoundryConfig.load().paths


# ---------------------------------------------------------------------------
# Shared sensitivity-gate helper
# ---------------------------------------------------------------------------

def _enforce_existence_gate(
    paths: FoundryPaths,
    run_id: str,
    sensitivity_threshold: str | None,
) -> dict[str, Any]:
    """Load and gate *run_id* against *sensitivity_threshold*.

    Returns the export dict when the run exists and is at or below the
    caller's requested threshold.

    Raises:
        HTTPException(400): *sensitivity_threshold* is not a recognised label.
        HTTPException(404): run not found **or** run sensitivity exceeds the
            threshold — the two cases are intentionally indistinguishable so
            that hidden sensitive run IDs are not leaked (no-existence-leak /
            landmine #4).
    """
    try:
        threshold = resolve_threshold(paths, sensitivity_threshold)
    except ExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    threshold_rank = SENSITIVITY_ORDER[threshold]

    # Route through the export service (R1 invariant — never read run files directly).
    # Pass the already-resolved threshold so export-time claim filtering honors
    # the same override used for the existence gate.
    try:
        data = export_run(paths, run_id, sensitivity_threshold=threshold)
    except ExportError as exc:
        raise HTTPException(status_code=404, detail="not found") from exc

    # No-existence-leak gate: a run whose sensitivity exceeds the threshold is
    # indistinguishable from a non-existent run (landmine #4).
    run_sensitivity = data.get("sensitivity") or "public"
    run_rank = SENSITIVITY_ORDER.get(str(run_sensitivity), len(SENSITIVITY_ORDER))
    if run_rank > threshold_rank:
        raise HTTPException(status_code=404, detail="not found")

    return data


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/runs", summary="List all runs")
def get_run_list(paths: FoundryPaths = Depends(get_paths)) -> list[dict[str, Any]]:
    """Return a summary of every discovered run.

    Empty corpus returns ``[]`` — never 404.  All data is routed through
    :func:`~research_foundry.services.export_service.list_runs` (R1).
    """
    return list_runs(paths)


@router.get("/runs/{run_id}", summary="Get run detail")
def get_run_detail(
    run_id: str,
    sensitivity_threshold: str | None = Query(
        None,
        description="Override foundry.yaml viewer.sensitivity_threshold (default: public).",
    ),
    paths: FoundryPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return the full denormalized export for *run_id*.

    All sensitivity redaction is applied by
    :func:`~research_foundry.services.export_service.export_run` (R1).

    An existence gate is enforced: a run whose sensitivity exceeds the
    threshold returns 404, indistinguishable from a genuinely absent run
    (no-existence-leak / landmine #4).

    Raises 404 when the run does not exist or is over-threshold.
    Raises 400 on invalid sensitivity_threshold.
    """
    return _enforce_existence_gate(paths, run_id, sensitivity_threshold)


@router.get("/runs/{run_id}/claims", summary="Get claim ledger for a run")
def get_run_claims(
    run_id: str,
    sensitivity_threshold: str | None = Query(
        None,
        description="Override foundry.yaml viewer.sensitivity_threshold (default: public).",
    ),
    paths: FoundryPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Return the claims array from the run's denormalized export.

    Empty ledger returns ``[]`` — never null.  Propagates 404 when the run
    does not exist or is over-threshold.  All data routed through
    export_service (R1).
    """
    data = _enforce_existence_gate(paths, run_id, sensitivity_threshold)
    # export_run always populates "claims" as a list; guard defensively
    claims = data.get("claims")
    return claims if isinstance(claims, list) else []


@router.get(
    "/runs/{run_id}/sources/{source_card_id}",
    summary="Get a resolved source from a run's claim graph",
)
def get_source_card(
    run_id: str,
    source_card_id: str,
    sensitivity_threshold: str | None = Query(
        None,
        description="Override foundry.yaml viewer.sensitivity_threshold (default: public).",
    ),
    paths: FoundryPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return the first :class:`RFResolvedSource` whose ``source_card_id``
    matches *source_card_id*.

    Scans ``export_run(...)["claims"][*]["sources"]`` — data always routed
    through the export service (R1).

    Raises 404 when the run is absent, over-threshold, or when no claim
    cites the requested source card.
    """
    data = _enforce_existence_gate(paths, run_id, sensitivity_threshold)

    for claim in (data.get("claims") or []):
        for source in (claim.get("sources") or []):
            if source.get("source_card_id") == source_card_id:
                return source

    raise HTTPException(status_code=404, detail="source not found")


@router.get("/reports/{run_id}/anchors", summary="Get report anchors for a run")
def get_run_anchors(
    run_id: str,
    sensitivity_threshold: str | None = Query(
        None,
        description="Override foundry.yaml viewer.sensitivity_threshold (default: public).",
    ),
    paths: FoundryPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return the ``report_anchors`` block for *run_id*.

    The response shape is ``{"run_id": str, "report_anchors": list | null}``,
    where ``report_anchors`` mirrors the same-named field in the run's
    ``run.json`` (schema 1.4 / D8).  ``null`` when the run has no report
    draft.

    **Sensitivity gating**: an existence gate is applied — an over-threshold
    run returns 404, indistinguishable from an unknown run (fail-closed:
    existence of hidden sensitive runs is not leaked / landmine #4).
    The ``sensitivity_threshold`` query parameter is honored consistently for
    both the existence gate and export-time content filtering (which claims
    are visible, and therefore which claim links appear in the derived anchors).
    """
    data = _enforce_existence_gate(paths, run_id, sensitivity_threshold)
    return {"run_id": run_id, "report_anchors": data.get("report_anchors")}


# RBAC-005 audit: runs.py has no mutation routes as of P5.2 — all endpoints
# are GET (read-only).  The five routes above are:
#   GET /runs
#   GET /runs/{run_id}
#   GET /runs/{run_id}/claims
#   GET /runs/{run_id}/sources/{source_card_id}
#   GET /reports/{run_id}/anchors
#
# Role-gating (run:read permission) will be needed if mutation routes are
# added in future phases, or when read-gate enforcement is implemented
# for P5.3/P5.7.  Until then no require_role dependency is warranted here.
#
# agent_jobs.py forward-compat: see RBAC-FORWARD-COMPAT note in
# src/research_foundry/api/auth/rbac.py module docstring (RBAC-005, RBAC-901).

__all__ = ["router"]
