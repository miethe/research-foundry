"""Shared evidence catalog API router (public-multiuser-release Phase 1).

All data routes through :mod:`~research_foundry.services.catalog_service`
(R1 invariant): handlers never touch the sqlite3 DB or run artifacts
directly. Sensitivity gating (item exclusion + payload redaction) is enforced
inside the service, not here.

Endpoint → client mapping (plan §"Backend deliverables (Wave B)"):
  GET  /api/catalog/stats                → fetchCatalogStats()
  GET  /api/catalog/search                → fetchCatalogSearch(params)
  GET  /api/catalog/items/{id}            → fetchCatalogItem(id)
  POST /api/catalog/import/run/{run_id}   → (manual reindex, single run)
  POST /api/catalog/import                → (manual reindex, all runs)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from ...paths import FoundryPaths
from ...services import catalog_service as svc
from .runs import get_paths

router = APIRouter()

# Module-level singleton (ruff B008: avoid calling Depends() in an argument
# default expression). Wraps the same get_paths callable that
# app.dependency_overrides[get_paths] targets in tests, so overriding still
# works regardless of where the Depends() instance was constructed.
_PATHS_DEP = Depends(get_paths)


@router.get("/catalog/stats", summary="Catalog aggregate counts")
def get_catalog_stats(paths: FoundryPaths = _PATHS_DEP) -> dict[str, Any]:
    """Return per-item-type counts (visible only), runs indexed, last import.

    Never raises — an empty/never-imported catalog returns zeroed counts.
    """
    return svc.stats(paths)


@router.get("/catalog/search", summary="Search the catalog")
def get_catalog_search(
    q: str | None = Query(None),
    item_type: str | None = Query(None),
    project: str | None = Query(None),
    status: str | None = Query(None),
    sensitivity: str | None = Query(None),
    run_id: str | None = Query(None),
    sort: str = Query("updated"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Search catalog items. Over-threshold items are excluded (fail-closed).

    Empty corpus / no matches → ``{"items": [], "total": 0, ...}`` — never 404.
    """
    return svc.search(
        paths,
        q=q,
        item_type=item_type,
        project=project,
        status=status,
        sensitivity=sensitivity,
        run_id=run_id,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@router.get("/catalog/items/{catalog_item_id}", summary="Get a catalog item's full detail")
def get_catalog_item(
    catalog_item_id: str,
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Return the summary fields + payload + links for *catalog_item_id*.

    404 for both an unknown id and an id excluded by the resolved sensitivity
    threshold — the two cases are indistinguishable to the caller by design
    (fail-closed: existence of hidden sensitive items is not leaked).
    """
    item = svc.get_item(paths, catalog_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="catalog item not found")
    return item


@router.post("/catalog/import/run/{run_id}", summary="(Re)import a single run")
def post_catalog_import_run(
    run_id: str,
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """(Re)import one run. Delete-then-insert — idempotent. 404 on unknown run."""
    try:
        result = svc.import_run(paths, run_id)
    except svc.CatalogError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    return {"imported": {"runs": 1, "items": result["items"]}}


@router.post("/catalog/import", summary="(Re)import every discovered run")
def post_catalog_import_all(paths: FoundryPaths = _PATHS_DEP) -> dict[str, Any]:
    """(Re)import every discovered run. Best-effort — a malformed run is skipped.

    ``errors`` carries ``import_all()``'s per-run failure list through to the
    caller (``[]`` when every run imported cleanly) instead of silently
    dropping it.
    """
    result = svc.import_all(paths)
    return {
        "imported": {"runs": result["runs"], "items": result["items"]},
        "errors": result["errors"],
    }


__all__ = ["router"]
