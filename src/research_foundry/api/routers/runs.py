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
    paths: FoundryPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return the full denormalized export for *run_id*.

    All sensitivity redaction is applied by
    :func:`~research_foundry.services.export_service.export_run` (R1).

    Raises 404 when the run does not exist.
    """
    try:
        return export_run(paths, run_id)
    except ExportError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc


@router.get("/runs/{run_id}/claims", summary="Get claim ledger for a run")
def get_run_claims(
    run_id: str,
    paths: FoundryPaths = Depends(get_paths),
) -> list[dict[str, Any]]:
    """Return the claims array from the run's denormalized export.

    Empty ledger returns ``[]`` — never null.  Propagates 404 when the run
    does not exist.  All data routed through export_service (R1).
    """
    try:
        run = export_run(paths, run_id)
    except ExportError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    # export_run always populates "claims" as a list; guard defensively
    claims = run.get("claims")
    return claims if isinstance(claims, list) else []


@router.get(
    "/runs/{run_id}/sources/{source_card_id}",
    summary="Get a resolved source from a run's claim graph",
)
def get_source_card(
    run_id: str,
    source_card_id: str,
    paths: FoundryPaths = Depends(get_paths),
) -> dict[str, Any]:
    """Return the first :class:`RFResolvedSource` whose ``source_card_id``
    matches *source_card_id*.

    Scans ``export_run(...)["claims"][*]["sources"]`` — data always routed
    through the export service (R1).

    Raises 404 when the run is absent or when no claim cites the requested
    source card.
    """
    try:
        run = export_run(paths, run_id)
    except ExportError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc

    for claim in (run.get("claims") or []):
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

    **Sensitivity gating (no-existence-leak)**: an over-threshold run returns
    404 — the same response as an unknown run.  The two cases are
    indistinguishable to callers by design (fail-closed: existence of hidden
    sensitive runs is not leaked).  Accepts a
    ``sensitivity_threshold`` query parameter consistent with other read
    endpoints (landmine #5).
    """
    # Resolve threshold first (raises ExportError on an invalid label).
    try:
        threshold = resolve_threshold(paths, sensitivity_threshold)
    except ExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    threshold_rank = SENSITIVITY_ORDER[threshold]

    # Route through the export service (R1 invariant — never read run files directly).
    try:
        data = export_run(paths, run_id)
    except ExportError as exc:
        raise HTTPException(status_code=404, detail="not found") from exc

    # No-existence-leak gate: a run whose sensitivity exceeds the threshold is
    # indistinguishable from a non-existent run (landmine #4).
    run_sensitivity = data.get("sensitivity") or "public"
    run_rank = SENSITIVITY_ORDER.get(str(run_sensitivity), len(SENSITIVITY_ORDER))
    if run_rank > threshold_rank:
        raise HTTPException(status_code=404, detail="not found")

    return {"run_id": run_id, "report_anchors": data.get("report_anchors")}


__all__ = ["router"]
