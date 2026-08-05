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

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...paths import FoundryPaths
from ...services import catalog_service as svc
from ...services.clearance import ClearanceDenied
from ..auth.rbac import require_role
from ..response_stamp import stamp
from .runs import get_paths

router = APIRouter()

# Module-level singleton (ruff B008: avoid calling Depends() in an argument
# default expression). Wraps the same get_paths callable that
# app.dependency_overrides[get_paths] targets in tests, so overriding still
# works regardless of where the Depends() instance was constructed.
_PATHS_DEP = Depends(get_paths)

# RBAC-003: catalog write gate — owner, admin, researcher may create/update.
# Module-level so tests can reference the inner callable for dependency_overrides.
_RBAC_CATALOG_WRITE = Depends(require_role("owner", "admin", "researcher"))

# Module-level singletons (ruff B008: same rationale as _PATHS_DEP above —
# fires specifically for list-typed Query() defaults, which `term`/`role`
# are, TASK-2.6).
_TERM_QUERY = Query(None)
_ROLE_QUERY = Query(None)


def _clearance_refusal(exc: ClearanceDenied) -> HTTPException:
    """Map a clearance refusal to 403 (clearance-gates-v1 M5).

    ``catalog_service.search``/``get_item`` (and, via ``_build_catalog_rows`` ->
    ``export_service.export_run``, ``import_run``/``import_all``) now mediate
    every raw record before projecting it, and raise ``ClearanceDenied`` — an
    ``RFError`` subclass, NOT a ``svc.CatalogError``. Without this mapping the
    exception escaped every handler in this router and surfaced as a bare 500:
    technically fail-closed (no data left the process) but an unreadable signal.

    403, not 404: a genuine clearance refusal is a *decision*, not an existence
    question, so it must not be folded into this router's no-existence-leak 404s
    (that would make a blocked item indistinguishable from a missing one and
    silently hide the governance event). Matches the convention leg B used in
    ``api/routers/runs.py`` and the pre-existing 403s in ``assertions.py`` /
    ``reports.py`` / ``admin.py``.
    """

    return HTTPException(status_code=403, detail=str(exc))


def _sensitivity_threshold_override(request: Request) -> str | None:
    """Read the serve-time sensitivity-threshold override off ``app.state``.

    Set once at startup by :func:`research_foundry.api.app.create_app` from
    the (already CLI-flag > foundry.yaml resolved) ``FoundryConfig`` — see
    that function for why the catalog router cannot resolve this itself from
    ``paths`` alone. ``None`` when no override was captured, in which case
    ``catalog_service.resolve_threshold()`` falls back to its own foundry.yaml
    / hardcoded-default resolution, unchanged from prior behavior.
    """
    return getattr(request.app.state, "catalog_sensitivity_threshold", None)


@router.get("/catalog/stats", summary="Catalog aggregate counts")
def get_catalog_stats(request: Request, paths: FoundryPaths = _PATHS_DEP) -> dict[str, Any]:
    """Return per-item-type counts (visible only), runs indexed, last import.

    Never raises — an empty/never-imported catalog returns zeroed counts.

    Also carries ``attribution_coverage`` (SMP-4.5): the tri-state
    ``present``/``absent``/``not_yet_assessed`` breakdown over visible
    ``source`` items, plus ``assessed`` and a human-readable
    ``coverage_line`` ("N of M sources assessed"). This is the milestone's
    honesty control for the plan's no-backfill decision — ``absent``
    (assessed, and the attribute genuinely isn't there) and
    ``not_yet_assessed`` (never evaluated) are distinct keys, never
    collapsed into each other or into ``null``. Computed by
    :func:`catalog_service.stats`; no separate endpoint is needed since
    every caller of this route already receives it.
    """
    identity = getattr(request.state, "identity", None)
    # NOTE: identity now scopes ONLY the attribution_coverage block inside
    # svc.stats() (see that function's docstring). The rest of stats()'s
    # counts remain unscoped — that is still the WKSP-304 P4 gap, unchanged
    # by this fix.
    return stamp(
        svc.stats(
            paths,
            sensitivity_threshold=_sensitivity_threshold_override(request),
            identity=identity,
        )
    )


@router.get("/catalog/search", summary="Search the catalog")
def get_catalog_search(
    request: Request,
    q: str | None = Query(None),
    item_type: str | None = Query(None),
    project: str | None = Query(None),
    status: str | None = Query(None),
    sensitivity: str | None = Query(None),
    run_id: str | None = Query(None),
    term: list[str] | None = _TERM_QUERY,
    role: list[str] | None = _ROLE_QUERY,
    sort: str = Query("updated"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=200),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Search catalog items. Over-threshold items are excluded (fail-closed).

    Empty corpus / no matches → ``{"items": [], "total": 0, ...}`` — never 404.

    ``term``/``role`` (claim-term-indexing v1, TASK-2.6) are passed straight
    through to :func:`catalog_service.search` with zero additional
    computation here (FR-13) — the service layer owns both the OR-within-
    repeats/AND-across-flags semantics (OQ-C) and the sensitivity-rank gate
    on ``catalog_terms`` (D3).

    Raises:
        HTTPException(403): a clearance-stamped record inside a matched row's
            raw ``payload_json`` blocks the ``redistribution``/``acquisition``
            scope (``clearance.ClearanceDenied`` from
            :func:`catalog_service.search`, clearance-gates-v1 M5).
    """
    identity = getattr(request.state, "identity", None)
    try:
        result = svc.search(
            paths,
            q=q,
            item_type=item_type,
            project=project,
            status=status,
            sensitivity=sensitivity,
            run_id=run_id,
            term=term,
            role=role,
            sort=sort,
            page=page,
            page_size=page_size,
            sensitivity_threshold=_sensitivity_threshold_override(request),
            identity=identity,
        )
    except ClearanceDenied as exc:
        raise _clearance_refusal(exc) from exc
    return stamp(result)


@router.get("/catalog/items/{catalog_item_id}", summary="Get a catalog item's full detail")
def get_catalog_item(
    catalog_item_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Return the summary fields + payload + links for *catalog_item_id*.

    404 for both an unknown id and an id excluded by the resolved sensitivity
    threshold — the two cases are indistinguishable to the caller by design
    (fail-closed: existence of hidden sensitive items is not leaked).

    403 — deliberately distinct from those 404s — when a clearance-stamped
    record inside this item's raw payload blocks the ``redistribution``/
    ``acquisition`` scope (``clearance.ClearanceDenied`` from
    :func:`catalog_service.get_item`, clearance-gates-v1 M5); see
    :func:`_clearance_refusal`.
    """
    identity = getattr(request.state, "identity", None)
    try:
        item = svc.get_item(
            paths,
            catalog_item_id,
            sensitivity_threshold=_sensitivity_threshold_override(request),
            identity=identity,
        )
    except ClearanceDenied as exc:
        raise _clearance_refusal(exc) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="catalog item not found")
    return stamp(item)


@router.post("/catalog/import/run/{run_id}", summary="(Re)import a single run")
def post_catalog_import_run(
    run_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_CATALOG_WRITE,
) -> dict[str, Any]:
    """(Re)import one run. Delete-then-insert — idempotent. 404 on unknown run.

    403 when a clearance-stamped record cited by the run blocks the
    ``redistribution``/``acquisition`` scope: ``import_run`` derives its rows via
    ``_build_catalog_rows`` -> ``export_service.export_run``, which leg B made
    mediating, and ``ClearanceDenied`` is not a ``svc.CatalogError`` so the
    existing handler below never saw it (clearance-gates-v1 M5).
    """
    identity = getattr(request.state, "identity", None)  # noqa: F841 — reserved for WKSP-304 P4 (svc.import_run() has no identity param; not a Phase 3 scoping target)
    try:
        # TODO(WKSP-304 P4): svc.import_run() does not accept identity (confirmed not a Phase 3 scoping target); wire once a future phase adds scoping here.
        result = svc.import_run(paths, run_id)
    except ClearanceDenied as exc:
        raise _clearance_refusal(exc) from exc
    except svc.CatalogError as exc:
        raise HTTPException(status_code=404, detail="run not found") from exc
    return stamp({"imported": {"runs": 1, "items": result["items"]}})


@router.post("/catalog/import", summary="(Re)import every discovered run")
def post_catalog_import_all(
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_CATALOG_WRITE,
) -> dict[str, Any]:
    """(Re)import every discovered run. Best-effort — a malformed run is skipped.

    ``errors`` carries ``import_all()``'s per-run failure list through to the
    caller (``[]`` when every run imported cleanly) instead of silently
    dropping it.

    403 on a clearance refusal (clearance-gates-v1 M5). NOTE the asymmetry:
    ``import_all`` catches only ``svc.CatalogError`` per-run, so a
    ``ClearanceDenied`` from one run aborts the whole sweep rather than landing
    in ``errors`` — reported as a leg-B-file observation, not changed here
    (``catalog_service.py`` is another leg's file).
    """
    identity = getattr(request.state, "identity", None)  # noqa: F841 — reserved for WKSP-304 P4 (svc.import_all() has no identity param; not a Phase 3 scoping target)
    # TODO(WKSP-304 P4): svc.import_all() does not accept identity (confirmed not a Phase 3 scoping target); wire once a future phase adds scoping here.
    try:
        result = svc.import_all(paths)
    except ClearanceDenied as exc:
        raise _clearance_refusal(exc) from exc
    return stamp(
        {
            "imported": {"runs": result["runs"], "items": result["items"]},
            "errors": result["errors"],
        }
    )


__all__ = ["router"]
