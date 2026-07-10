"""Report Builder API router — Phase 3 Wave E.

All paths route through :mod:`~research_foundry.services.builder_service`
(file-canonical draft store, Wave D) and
:func:`~research_foundry.services.verification.verify_draft` (D13 checks).
No auth/RBAC (deferred to P5 D12). Draft truth stays in files; this router
is a thin HTTP wrapper.

Route table (registered under /api prefix in app.py):

  POST   /reports                               create draft (blank / from-run / from-collection)
  GET    /reports                               list drafts (sensitivity-gated, fail-closed)
  GET    /reports/{report_id}                   load draft (rpt_ id only; sensitivity-gated)
  DELETE /reports/{report_id}                   delete draft
  GET    /reports/{report_id}/versions          list revisions
  POST   /reports/{report_id}/versions          create revision snapshot
  GET    /reports/{report_id}/versions/{vid}    get revision snapshot
  POST   /reports/{report_id}/versions/{vid}/restore  restore revision
  POST   /reports/{report_id}/blocks            add block
  PATCH  /reports/{report_id}/blocks/reorder    reorder blocks (fixed before param)
  PATCH  /reports/{report_id}/blocks/{block_id} update block
  DELETE /reports/{report_id}/blocks/{block_id} delete block (200 + updated draft)
  POST   /reports/{report_id}/claim-links       add claim link
  DELETE /reports/{report_id}/claim-links/{claim_link_id}   remove claim link (200 + updated draft)
  POST   /reports/{report_id}/source-links      add source link
  DELETE /reports/{report_id}/source-links/{source_link_id} remove source link (200 + updated draft)
  POST   /reports/{report_id}/verify            run D13 checks (structured result)
  POST   /reports/{report_id}/publish-preview   D13 fail-closed gate + Markdown preview
  GET    /reports/{report_id}/export            export draft as Markdown

Critical routing note:
  GET /api/reports/{run_id}/anchors is defined in runs.py.  That route has a
  fixed '/anchors' suffix (4-segment path) vs this router's bare
  '/reports/{report_id}' (3-segment path).  FastAPI resolves them
  unambiguously by path-segment count + fixed component.  No changes to the
  anchors route are needed.

Id validation note (R2 CRITICAL fix):
  ``report_draft_id``/``report_version_id`` shape validation and filesystem
  containment now live in ``builder_service`` (``_validate_draft_id`` /
  ``_validate_version_id`` / ``_draft_dir`` / ``_revision_path``), not here —
  a router-level ``report_id.startswith("rpt_")`` check is a PREFIX check
  that a traversal payload satisfies unchanged. Every handler below relies on
  the service layer raising :class:`NotFoundError` for a malformed id, which
  is caught and mapped to the same indistinguishable 404 as "doesn't exist"
  (landmine #4), so a CLI caller or any other direct ``builder_service``
  consumer gets the identical protection.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ..auth.rbac import require_role
from ...errors import NotFoundError
from ...paths import FoundryPaths
from ...services import audit_service, builder_service as bsvc
from ...services.audit_service import AuditEvent
from ...services.export_service import SENSITIVITY_ORDER, ExportError, resolve_threshold
from ...services.verification import verify_draft
from .runs import get_paths

router = APIRouter()

_PATHS_DEP = Depends(get_paths)

# RBAC-004: report mutation gates — module-level to avoid ruff B008 and to allow
# test dependency_overrides on the inner callable.
#
# builder_service.py bypass confirmation (RBAC-004 invariant): builder_service.py
# has no HTTP entry point — its write methods (create_draft, add_block, etc.) are
# pure Python functions called only from this router. There is no HTTP path into
# builder_service mutation functions that bypasses the router-layer gating below.
_RBAC_REPORT_WRITE = Depends(require_role("owner", "admin", "researcher"))
_RBAC_REPORT_ADMIN = Depends(require_role("owner", "admin"))


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------


class CreateDraftBody(BaseModel):
    """Body for POST /api/reports.

    *origin* drives dispatch:
      "blank"      → create_draft (empty)
      "template"   → create_draft (title/audience/sensitivity only; no source)
      "run"        → create_draft_from_run (requires source_run_id)
      "collection" → create_draft_from_collection (requires catalog_item_ids)
    """

    origin: str = "blank"
    title: str = "Untitled Draft"
    source_run_id: str | None = None
    collection_id: str | None = None          # kept for compat; prefer catalog_item_ids
    catalog_item_ids: list[str] | None = None  # for origin="collection"
    audience: str = "self"
    sensitivity: str = "public"
    project_id: str | None = None
    workspace_id: str | None = None
    created_by: str | None = None
    sensitivity_threshold: str | None = None  # passed through to from_run / from_collection


class CreateRevisionBody(BaseModel):
    note: str | None = None
    created_by: str | None = None


class AddBlockBody(BaseModel):
    block_type: str = "paragraph"
    markdown: str = ""
    order: int | None = None
    materiality: str = "material"
    updated_by: str | None = None


class UpdateBlockBody(BaseModel):
    markdown: str | None = None
    block_type: str | None = None
    materiality: str | None = None
    order: int | None = None
    risk_flags: list[str] | None = None
    updated_by: str | None = None


class ReorderBlocksBody(BaseModel):
    block_ids: list[str]
    updated_by: str | None = None


class AddClaimLinkBody(BaseModel):
    block_id: str
    claim_id: str
    relation: str | None = None
    source_run_id: str | None = None
    catalog_item_id: str | None = None
    span_start: int | None = None
    span_end: int | None = None
    insert_tag: bool = True
    updated_by: str | None = None


class AddSourceLinkBody(BaseModel):
    source_card_id: str
    run_id: str | None = None
    catalog_item_id: str | None = None
    block_id: str | None = None
    relation: str | None = None
    updated_by: str | None = None


class CreateShareLinkBody(BaseModel):
    """Body for POST /api/reports/{report_id}/share-links.

    *sensitivity_threshold* defaults to the draft's own sensitivity label when
    omitted.  The resolved threshold must be ``<=`` the draft's sensitivity rank
    (creating a share link at a *higher* threshold than the draft's label is
    permitted — the gate will still block access when the draft's label exceeds
    the threshold at resolution time).

    *expires_at* is an optional ISO-8601 UTC timestamp after which the link is
    considered expired.  ``None`` means the link never expires (revocation is
    the only mechanism to invalidate it).
    """

    sensitivity_threshold: str | None = None
    expires_at: str | None = None
    created_by: str | None = None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _not_found(report_id: str, detail: str = "report draft not found") -> HTTPException:
    """Return a 404 that does NOT leak whether the id is a wrong type vs absent.

    Landmine #4: do not distinguish 'unknown rpt_ id' from 'this is a run id'.
    """
    return HTTPException(status_code=404, detail=detail)


def _builder_error(exc: bsvc.BuilderError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


def _resolve_threshold_rank(paths: FoundryPaths, sensitivity_threshold: str | None) -> int:
    """Resolve the active sensitivity threshold to its rank (400 on a bogus label).

    Mirrors ``get_run_anchors``' existence-gate pattern in ``runs.py`` and
    ``catalog_service.get_item``'s fail-closed rank lookup, applied here to
    Report Builder draft reads (R2 fix: these previously had zero sensitivity
    gating at all).
    """
    try:
        threshold = resolve_threshold(paths, sensitivity_threshold)
    except ExportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SENSITIVITY_ORDER[threshold]


def _sensitivity_rank(label: str | None) -> int:
    """Fail-closed rank lookup — an unknown/missing label ranks stricter than
    every known level (mirrors ``catalog_service._rank``), so it can never
    silently pass a threshold gate."""
    return SENSITIVITY_ORDER.get(str(label), len(SENSITIVITY_ORDER))


# ---------------------------------------------------------------------------
# Draft CRUD
# ---------------------------------------------------------------------------


@router.post("/reports", summary="Create a report draft", status_code=201)
def create_draft(
    body: CreateDraftBody,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_REPORT_WRITE,
) -> dict[str, Any]:
    """Create a new draft.  Origin-driven dispatch:
    - ``blank`` / ``template`` → empty draft with optional title/audience/sensitivity
    - ``run``        → seed blocks from run's report_draft + report_anchors
    - ``collection`` → one evidence_summary block per catalog item
    """
    # identity is wired into the blank/template create_draft() call below, and
    # into create_draft_from_run()/create_draft_from_collection() (WKSP-304).
    identity = getattr(request.state, "identity", None)
    try:
        if body.origin == "run":
            if not body.source_run_id:
                raise HTTPException(
                    status_code=422,
                    detail="origin 'run' requires source_run_id",
                )
            return bsvc.create_draft_from_run(
                paths,
                run_id=body.source_run_id,
                title=body.title if body.title != "Untitled Draft" else None,
                audience=body.audience,
                sensitivity=body.sensitivity if body.sensitivity != "public" else None,
                project_id=body.project_id,
                workspace_id=body.workspace_id,
                created_by=body.created_by,
                sensitivity_threshold=body.sensitivity_threshold or "client_sensitive",
                identity=identity,
            )
        if body.origin == "collection":
            ids_ = body.catalog_item_ids or (
                [body.collection_id] if body.collection_id else []
            )
            if not ids_:
                raise HTTPException(
                    status_code=422,
                    detail="origin 'collection' requires catalog_item_ids",
                )
            return bsvc.create_draft_from_collection(
                paths,
                catalog_item_ids=ids_,
                title=body.title,
                audience=body.audience,
                sensitivity=body.sensitivity,
                project_id=body.project_id,
                workspace_id=body.workspace_id,
                created_by=body.created_by,
                sensitivity_threshold=body.sensitivity_threshold or "client_sensitive",
                identity=identity,
            )
        # blank / template / unknown origin → plain create_draft
        return bsvc.create_draft(
            paths,
            title=body.title,
            origin=body.origin,
            audience=body.audience,
            sensitivity=body.sensitivity,
            project_id=body.project_id,
            workspace_id=body.workspace_id,
            created_by=body.created_by,
            identity=identity,
        )
    except bsvc.BuilderError as exc:
        raise _builder_error(exc) from exc


@router.get("/reports", summary="List report drafts")
def list_drafts(
    request: Request,
    sensitivity_threshold: str | None = Query(
        None,
        description="Override foundry.yaml viewer.sensitivity_threshold (default: public).",
    ),
    paths: FoundryPaths = _PATHS_DEP,
) -> list[dict[str, Any]]:
    """Return summary rows for on-disk drafts visible at the resolved
    sensitivity threshold.  Fail-closed (R2 fix): a draft whose sensitivity
    rank exceeds the threshold — including one with an unrecognized label —
    is silently omitted, mirroring ``catalog_service.search``'s gating.
    Empty/fully-gated corpus → ``[]``.
    """
    identity = getattr(request.state, "identity", None)
    threshold_rank = _resolve_threshold_rank(paths, sensitivity_threshold)
    return [
        d
        for d in bsvc.list_drafts(paths, identity=identity)
        if _sensitivity_rank(d.get("sensitivity")) <= threshold_rank
    ]


@router.get("/reports/{report_id}", summary="Get report draft detail")
def get_draft(
    report_id: str,
    request: Request,
    sensitivity_threshold: str | None = Query(
        None,
        description="Override foundry.yaml viewer.sensitivity_threshold (default: public).",
    ),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Return the full draft state for *report_id* (a ``rpt_`` id).

    404 for unknown ids, ids that resolve to a run, AND a draft whose
    sensitivity exceeds the resolved threshold — all indistinguishable
    (no-existence-leak, landmine #4; R2 fix: this endpoint previously applied
    zero sensitivity gating, unlike ``catalog_service.get_item``).
    """
    identity = getattr(request.state, "identity", None)
    threshold_rank = _resolve_threshold_rank(paths, sensitivity_threshold)
    try:
        draft = bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    if _sensitivity_rank(draft.get("sensitivity")) > threshold_rank:
        raise _not_found(report_id)
    return draft


@router.delete("/reports/{report_id}", summary="Delete a report draft", status_code=204)
def delete_draft(
    report_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_REPORT_ADMIN,
) -> None:
    """Delete draft directory (draft.yaml + revisions) and its catalog index row.

    Idempotent: deleting a non-existent (but well-formed) draft id returns
    204. A malformed id (bad shape / traversal attempt) 404s instead — the
    service layer's :func:`~research_foundry.services.builder_service._draft_dir`
    raises :class:`NotFoundError` before anything is touched on disk.

    WKSP-304 P4 (TASK-4.3, AC-5): a workspace-scoped pre-flight check gates
    the actual delete, but the idempotent-204 contract above must survive it.
    ``bsvc.load_draft`` cannot distinguish "malformed id" / "genuinely
    missing" from "exists but is cross-workspace-denied" — all three raise
    the same :class:`NotFoundError` (by design, no-existence-leak). So when
    the identity-scoped load denies, a second identity=None probe (byte-
    identical to pre-Phase-4 behavior) tells us which case we are in: if the
    draft doesn't exist AT ALL either, this is the pre-existing idempotent
    no-op path — fall through unchanged to ``bsvc.delete_draft`` below. If
    the identity=None probe SUCCEEDS, the draft genuinely exists in another
    workspace — fail closed (404) WITHOUT ever calling ``bsvc.delete_draft``,
    so no cross-workspace file is ever touched.
    """
    identity = getattr(request.state, "identity", None)
    if identity is not None:
        try:
            bsvc.load_draft(paths, report_id, identity=identity)
        except NotFoundError:
            try:
                bsvc.load_draft(paths, report_id, identity=None)
            except NotFoundError:
                pass  # genuinely missing / malformed — idempotent path below.
            else:
                raise _not_found(report_id)
    try:
        bsvc.delete_draft(paths, report_id)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc


# ---------------------------------------------------------------------------
# Revisions
# ---------------------------------------------------------------------------


@router.get("/reports/{report_id}/versions", summary="List draft revisions")
def list_versions(
    report_id: str,
    request: Request,
    sensitivity_threshold: str | None = Query(
        None,
        description="Override foundry.yaml viewer.sensitivity_threshold (default: public).",
    ),
    paths: FoundryPaths = _PATHS_DEP,
) -> list[dict[str, Any]]:
    """Return revision pointer list (report_version_id, created_at, note) for *report_id*.

    404 for unknown ids AND drafts whose sensitivity exceeds the resolved threshold
    (no-existence-leak, mirrors ``get_draft`` gating).
    """
    identity = getattr(request.state, "identity", None)
    threshold_rank = _resolve_threshold_rank(paths, sensitivity_threshold)
    try:
        draft = bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    if _sensitivity_rank(draft.get("sensitivity")) > threshold_rank:
        raise _not_found(report_id)
    try:
        # TODO(WKSP-304 P4): bsvc.list_revisions() does not accept identity (confirmed not a Phase 3 scoping target); wire once a future phase adds scoping here.
        return bsvc.list_revisions(paths, report_id)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc


@router.post("/reports/{report_id}/versions", summary="Create a revision snapshot", status_code=201)
def create_version(
    report_id: str,
    body: CreateRevisionBody,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_REPORT_WRITE,
) -> dict[str, Any]:
    """Snapshot the current draft state into an immutable revision file."""
    identity = getattr(request.state, "identity", None)
    try:
        bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    try:
        return bsvc.create_revision(
            paths, report_id, created_by=body.created_by, note=body.note
        )
    except NotFoundError as exc:
        raise _not_found(report_id) from exc


@router.get("/reports/{report_id}/versions/{version_id}", summary="Get a revision snapshot")
def get_version(
    report_id: str,
    version_id: str,
    request: Request,
    sensitivity_threshold: str | None = Query(
        None,
        description="Override foundry.yaml viewer.sensitivity_threshold (default: public).",
    ),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Return the full snapshot for *version_id* under *report_id*.

    404 for unknown ids AND drafts whose sensitivity exceeds the resolved threshold
    (no-existence-leak, mirrors ``get_draft`` gating).
    """
    identity = getattr(request.state, "identity", None)
    threshold_rank = _resolve_threshold_rank(paths, sensitivity_threshold)
    try:
        draft = bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    if _sensitivity_rank(draft.get("sensitivity")) > threshold_rank:
        raise _not_found(report_id)
    try:
        # TODO(WKSP-304 P4): bsvc.get_revision() does not accept identity (confirmed not a Phase 3 scoping target); wire once a future phase adds scoping here.
        return bsvc.get_revision(paths, report_id, version_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="revision not found") from exc


@router.post(
    "/reports/{report_id}/versions/{version_id}/restore",
    summary="Restore a prior revision",
)
def restore_version(
    report_id: str,
    version_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_REPORT_WRITE,
) -> dict[str, Any]:
    """Overwrite current draft content with the *version_id* snapshot.

    Callers wanting a pre-restore checkpoint should POST /versions first.
    """
    identity = getattr(request.state, "identity", None)
    try:
        bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    try:
        return bsvc.restore_revision(paths, report_id, version_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail="revision not found") from exc


# ---------------------------------------------------------------------------
# Block CRUD — IMPORTANT: fixed /reorder MUST be registered before /{block_id}
# ---------------------------------------------------------------------------


@router.post("/reports/{report_id}/blocks", summary="Add a block to a draft", status_code=201)
def add_block(
    report_id: str,
    body: AddBlockBody,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_REPORT_WRITE,
) -> dict[str, Any]:
    """Append a new block to *report_id*.  Returns the full updated draft."""
    identity = getattr(request.state, "identity", None)
    try:
        bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    try:
        return bsvc.add_block(
            paths,
            report_id,
            block_type=body.block_type,
            markdown=body.markdown,
            order=body.order,
            materiality=body.materiality,
            updated_by=body.updated_by,
        )
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    except bsvc.BuilderError as exc:
        raise _builder_error(exc) from exc


@router.patch("/reports/{report_id}/blocks/reorder", summary="Reorder blocks")
def reorder_blocks(
    report_id: str,
    body: ReorderBlocksBody,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_REPORT_WRITE,
) -> dict[str, Any]:
    """Set block order by supplying the complete ordered list of block_ids.

    Must be a permutation of all block ids in the draft (builder_service
    enforces this).
    """
    identity = getattr(request.state, "identity", None)
    try:
        bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    try:
        return bsvc.reorder_blocks(
            paths, report_id, body.block_ids, updated_by=body.updated_by
        )
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    except bsvc.BuilderError as exc:
        raise _builder_error(exc) from exc


@router.patch("/reports/{report_id}/blocks/{block_id}", summary="Update a block")
def update_block(
    report_id: str,
    block_id: str,
    body: UpdateBlockBody,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_REPORT_WRITE,
) -> dict[str, Any]:
    """Patch one or more fields of *block_id*.  Returns the full updated draft."""
    identity = getattr(request.state, "identity", None)
    try:
        bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    try:
        return bsvc.update_block(
            paths,
            report_id,
            block_id,
            markdown=body.markdown,
            block_type=body.block_type,
            materiality=body.materiality,
            order=body.order,
            risk_flags=body.risk_flags,
            updated_by=body.updated_by,
        )
    except NotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"block not found: {block_id}",
        ) from exc
    except bsvc.BuilderError as exc:
        raise _builder_error(exc) from exc


@router.delete(
    "/reports/{report_id}/blocks/{block_id}",
    summary="Delete a block",
)
def delete_block(
    report_id: str,
    block_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_REPORT_WRITE,
) -> dict[str, Any]:
    """Remove *block_id* and its associated claim/source links from *report_id*.

    Returns the full updated draft (200) — R2 fix: this previously answered
    204 No Content while ``builder_service.delete_block`` already computed
    and returned the updated draft, so the frontend's ``Promise<ReportDraft>``
    client (which writes the response straight into the React Query cache)
    silently stomped the cache with ``undefined``. Matches the sibling
    ``add_block``/``update_block``/``reorder_blocks`` contract.
    """
    identity = getattr(request.state, "identity", None)
    try:
        bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    try:
        return bsvc.delete_block(paths, report_id, block_id)
    except NotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"block not found: {block_id}",
        ) from exc


# ---------------------------------------------------------------------------
# Claim links
# ---------------------------------------------------------------------------


@router.post("/reports/{report_id}/claim-links", summary="Add a claim link", status_code=201)
def add_claim_link(
    report_id: str,
    body: AddClaimLinkBody,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_REPORT_WRITE,
) -> dict[str, Any]:
    """Link *claim_id* to *block_id*.  Inserts a ``[claim:<id>]`` tag unless
    ``insert_tag=false``.  Returns the full updated draft."""
    identity = getattr(request.state, "identity", None)
    try:
        bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    try:
        return bsvc.add_claim_link(
            paths,
            report_id,
            block_id=body.block_id,
            claim_id=body.claim_id,
            relation=body.relation,
            source_run_id=body.source_run_id,
            catalog_item_id=body.catalog_item_id,
            span_start=body.span_start,
            span_end=body.span_end,
            insert_tag=body.insert_tag,
            updated_by=body.updated_by,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bsvc.BuilderError as exc:
        raise _builder_error(exc) from exc


@router.delete(
    "/reports/{report_id}/claim-links/{claim_link_id}",
    summary="Remove a claim link",
)
def remove_claim_link(
    report_id: str,
    claim_link_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_REPORT_WRITE,
) -> dict[str, Any]:
    """Remove *claim_link_id* from the draft and recompute block coverage.

    Returns the full updated draft (200) — see ``delete_block`` above for why.
    """
    identity = getattr(request.state, "identity", None)
    try:
        bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    try:
        return bsvc.remove_claim_link(paths, report_id, claim_link_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Source links
# ---------------------------------------------------------------------------


@router.post("/reports/{report_id}/source-links", summary="Add a source link", status_code=201)
def add_source_link(
    report_id: str,
    body: AddSourceLinkBody,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_REPORT_WRITE,
) -> dict[str, Any]:
    """Link a source card to the draft (optionally anchored to a block)."""
    identity = getattr(request.state, "identity", None)
    try:
        bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    try:
        return bsvc.add_source_link(
            paths,
            report_id,
            source_card_id=body.source_card_id,
            run_id=body.run_id,
            catalog_item_id=body.catalog_item_id,
            block_id=body.block_id,
            relation=body.relation,
            updated_by=body.updated_by,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bsvc.BuilderError as exc:
        raise _builder_error(exc) from exc


@router.delete(
    "/reports/{report_id}/source-links/{source_link_id}",
    summary="Remove a source link",
)
def remove_source_link(
    report_id: str,
    source_link_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_REPORT_WRITE,
) -> dict[str, Any]:
    """Remove *source_link_id* from the draft.

    Returns the full updated draft (200) — see ``delete_block`` above for why.
    """
    identity = getattr(request.state, "identity", None)
    try:
        bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    try:
        return bsvc.remove_source_link(paths, report_id, source_link_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


@router.post("/reports/{report_id}/verify", summary="Verify a draft (D13 checks)")
def verify_draft_endpoint(
    report_id: str,
    request: Request,
    sensitivity_threshold: str | None = Query(
        None,
        description="Override sensitivity threshold for the body-sensitivity check.",
    ),
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_REPORT_WRITE,
) -> dict[str, Any]:
    """Run all D13 checks against *report_id*.

    Always returns 200 with a structured result (``passed``, per-check details).
    Use /publish-preview for the fail-closed gate.
    """
    identity = getattr(request.state, "identity", None)  # noqa: F841 — reserved for WKSP-304 P4 (verify_draft() is services.verification, not builder_service, and has no identity param; not a Phase 3 scoping target)
    try:
        # TODO(WKSP-304 P4): verify_draft() (services.verification) does not accept identity (confirmed not a Phase 3 scoping target); wire once a future phase adds scoping here.
        result = verify_draft(
            paths, report_id, sensitivity_threshold=sensitivity_threshold
        )
    except NotFoundError as exc:
        raise _not_found(report_id) from exc

    return {
        "report_draft_id": report_id,
        "passed": result.passed,
        "exit_code": result.exit_code,
        "checks": [
            {
                "id": c.id,
                "severity": c.severity,
                "status": c.status,
                "detail": c.detail,
                "locations": c.locations,
            }
            for c in result.checks
        ],
        "unsupported": result.unsupported,
    }


@router.post("/reports/{report_id}/publish-preview", summary="Publish-preview gate (D13 fail-closed)")
def publish_preview(
    report_id: str,
    request: Request,
    sensitivity_threshold: str | None = Query(
        None,
        description=(
            "Override sensitivity threshold for body-sensitivity check "
            "(default: draft's own sensitivity label)."
        ),
    ),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Run D13 checks FAIL-CLOSED and return a Markdown preview on pass.

    **Failure behavior (spec §11)**:
    - ``paragraph_has_support`` fails → ``{ok: false, blocking: [...]}`` + HTTP 422
    - ``report_body_sensitivity`` fails (raw sensitive quote in body) → same
    - Any other error-severity D13 failure → same

    **Success**: ``{ok: true, preview_markdown: "...", checks: [...]}`` + HTTP 200

    **PRD AC-2 — Role-independent fail-closed gate**:
    The D13 sensitivity checks fire BEFORE the RBAC role gate.  Any
    error-severity sensitivity failure returns 422 for ALL callers regardless of
    their role — including ``owner`` and ``admin``.  No role can bypass the
    sensitivity gate.  RBAC (``report:publish`` → owner/admin only) is enforced
    in step 3, after the sensitivity gate passes.

    The preview Markdown is generated from the current draft blocks.  Nothing
    is persisted — callers decide whether to actually publish.

    **RBAC-901 note**: this route enforces ``report:publish`` (owner/admin)
    manually rather than via ``Depends(require_role(...))`` so that the
    sensitivity gate (step 2, 422) fires before the role gate (step 3, 403).
    The test_rbac_route_sweep.py MANUALLY_GATED_ROUTES exemption documents this.
    """
    # Resolve caller identity once — used in both the RBAC pre-check below
    # and the post-sensitivity RBAC gate (step 3).
    # RBAC-disabled: when app.state.rbac_enforced is False the global
    # require_role() is a no-op; this manual gate must honor the same toggle so
    # that loopback/disabled mode is consistent end-to-end (DEFECT P2 fix).
    _app_state = getattr(getattr(request, "app", None), "state", None)
    rbac_enforced: bool | None = (
        getattr(_app_state, "rbac_enforced", None) if _app_state is not None else None
    )
    identity = getattr(request.state, "identity", None)
    _has_publish_perm: bool = (rbac_enforced is False) or identity is None or bool(
        set(identity.roles) & {"owner", "admin"}
    )

    # Step 1: Sensitivity-first D13 verification (PRD AC-2 invariant).
    # verify_draft loads the draft and runs all D13 checks BEFORE the RBAC
    # check below, so a sensitivity violation (422) cannot be bypassed by
    # choosing a higher-privileged role.
    try:
        result = verify_draft(
            paths, report_id, sensitivity_threshold=sensitivity_threshold
        )
    except NotFoundError as exc:
        # Draft not found.  Under-privileged callers get 403 (existence pre-check)
        # so probing for non-existent report IDs is indistinguishable from
        # "you lack the report:publish permission."
        if not _has_publish_perm:
            raise HTTPException(status_code=403, detail="Insufficient role") from exc
        raise _not_found(report_id) from exc

    check_dicts = [
        {
            "id": c.id,
            "severity": c.severity,
            "status": c.status,
            "detail": c.detail,
            "locations": c.locations,
        }
        for c in result.checks
    ]

    # Step 2: Role-independent sensitivity gate (PRD AC-2).
    # 422 fires for ALL callers regardless of role when any error-severity
    # D13 check fails.  This is the "publish_preview must be role-independent
    # fail-closed" requirement — no privileged role can bypass this.
    blocking = [c for c in check_dicts if c["severity"] == "error" and c["status"] == "fail"]
    if blocking:
        # Audit: record denied publish-preview before raising (fail-open).
        audit_service.record_event(
            paths,
            AuditEvent(
                mutation_type="publish_preview",
                action="publish_preview",
                target_ref=report_id,
                result="denied",
                error_detail=str([c["id"] for c in blocking]),
            ),
        )
        raise HTTPException(
            status_code=422,
            detail={
                "ok": False,
                "blocking": blocking,
                "checks": check_dicts,
            },
        )

    # Step 3: RBAC gate — reached only when all D13 sensitivity checks pass.
    # Only owner/admin hold report:publish permission.
    if not _has_publish_perm:
        raise HTTPException(status_code=403, detail="Insufficient role")

    # Step 4: Generate Markdown preview (no side-effects on draft state).
    try:
        preview_md = bsvc.export_markdown(paths, report_id, identity=identity)
    except NotFoundError as exc:  # pragma: no cover  — already verified load above
        raise _not_found(report_id) from exc

    # Audit: record successful publish-preview (fail-open).
    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="publish_preview",
            action="publish_preview",
            target_ref=report_id,
            result="success",
        ),
    )

    # Step 5: Audit-health gate (REVIEW-001 must-fix, AUDIT-004).
    # Unconditional regardless of RBAC-enforcement mode — a degraded audit
    # store must not silently allow exposure of preview content just because
    # this caller cleared the sensitivity gate (step 1/2) and the RBAC gate
    # (step 3).  record_event() above stays fail-open and unchanged; this
    # check is purely additive.
    if not audit_service.is_healthy_for_exposure(paths):
        raise HTTPException(status_code=503, detail="Audit log unavailable")

    return {
        "ok": True,
        "preview_markdown": preview_md,
        "checks": check_dicts,
    }


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@router.get("/reports/{report_id}/export", summary="Export draft as Markdown")
def export_draft(
    report_id: str,
    request: Request,
    sensitivity_threshold: str | None = Query(
        None,
        description="Override foundry.yaml viewer.sensitivity_threshold (default: public).",
    ),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Return the draft rendered as Markdown with YAML frontmatter.

    404 for unknown ids AND drafts whose sensitivity exceeds the resolved threshold
    (no-existence-leak, mirrors ``get_draft`` gating).  The sensitivity check runs
    before any content is returned.

    The response carries ``{"report_draft_id": ..., "markdown": "..."}`` so
    callers can display or save the output without additional parsing.
    """
    identity = getattr(request.state, "identity", None)
    threshold_rank = _resolve_threshold_rank(paths, sensitivity_threshold)
    try:
        draft = bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    if _sensitivity_rank(draft.get("sensitivity")) > threshold_rank:
        raise _not_found(report_id)
    try:
        md = bsvc.export_markdown(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc
    return {"report_draft_id": report_id, "markdown": md}


# ---------------------------------------------------------------------------
# Share links (Phase 5.6 — D5: READ-ONLY, sensitivity-scoped share primitive)
#
# Design decision (D5 / LOCKED):
#   v1 shares are READ-ONLY tokens scoped to a single draft at a fixed
#   sensitivity threshold.  General public URLs (no token) are deferred.
# ---------------------------------------------------------------------------


@router.post(
    "/reports/{report_id}/share-links",
    summary="Create a sensitivity-scoped share link (read-only)",
    status_code=201,
)
def create_share_link(
    report_id: str,
    body: CreateShareLinkBody,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_REPORT_ADMIN,
) -> dict[str, Any]:
    """Create a read-only, sensitivity-scoped share link for *report_id*.

    The returned ``share_token`` is a bearer credential that grants read
    access to the draft at ``sensitivity_threshold``.  Sensitivity is
    re-checked at resolution time (``GET /reports/shares/{token}``) — the
    token alone cannot bypass the gate (PRD AC-2).

    Share link records are stored in ``.rf_state/rbac.db`` (NEVER
    ``catalog.db`` — the catalog store drops and rebuilds on schema
    version mismatch, which would silently invalidate live tokens).
    """
    from ...services.share_store import create_share_link as _create_link

    identity = getattr(request.state, "identity", None)

    # Load the draft to validate it exists and resolve the default threshold.
    try:
        draft = bsvc.load_draft(paths, report_id, identity=identity)
    except NotFoundError as exc:
        raise _not_found(report_id) from exc

    # Resolve the effective share threshold.
    threshold = body.sensitivity_threshold or draft.get("sensitivity") or "public"
    if threshold not in SENSITIVITY_ORDER:
        raise HTTPException(
            status_code=422,
            detail=f"unknown sensitivity_threshold {threshold!r}; "
            f"valid values: {', '.join(sorted(SENSITIVITY_ORDER, key=SENSITIVITY_ORDER.__getitem__))}",
        )

    # Gate: draft sensitivity must not exceed the share threshold.
    # A draft with sensitivity "client_sensitive" cannot be shared at
    # threshold "public" — that would expose the draft to readers who should
    # not see it.
    draft_rank = SENSITIVITY_ORDER.get(
        str(draft.get("sensitivity") or "public"), len(SENSITIVITY_ORDER)
    )
    threshold_rank = SENSITIVITY_ORDER[threshold]
    if draft_rank > threshold_rank:
        raise HTTPException(
            status_code=422,
            detail=(
                f"draft sensitivity {draft.get('sensitivity')!r} exceeds the requested "
                f"share link threshold {threshold!r} — cannot create a share link that "
                "would expose the draft beyond its sensitivity label"
            ),
        )

    # Audit-health gate (REVIEW-001 must-fix, AUDIT-004). Unconditional —
    # a degraded audit store must not silently allow minting a new
    # sensitivity-scoped share credential.
    if not audit_service.is_healthy_for_exposure(paths):
        raise HTTPException(status_code=503, detail="Audit log unavailable")

    return _create_link(
        paths,
        report_draft_id=report_id,
        sensitivity_threshold=threshold,
        created_by=body.created_by,
        expires_at=body.expires_at,
    )


@router.get(
    "/reports/shares/{share_token}",
    summary="Resolve a share link (read-only, token-authenticated)",
)
def resolve_share_link(
    share_token: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Resolve a share link token to a read-only Markdown preview.

    This endpoint is publicly accessible via the share token (no session auth
    required — the token IS the bearer credential).

    **PRD AC-2 — Sensitivity re-applied at resolution time**:
    The draft's current sensitivity label is re-checked against the share
    link's stored threshold at every request.  The creation-time check is NOT
    trusted.  If the draft's sensitivity has increased since the link was
    created (e.g. relabelled from ``public`` to ``client_sensitive``), this
    endpoint returns 422 (fail-closed).

    Returns:
    - ``404`` — token not found, revoked, or expired.
    - ``422`` — draft's current sensitivity exceeds the share link threshold.
    - ``200`` — ``{ok: true, report_draft_id, sensitivity_threshold, preview_markdown}``.
    """
    from ...services.share_store import resolve_share_link as _resolve
    from ...services.export_service import SENSITIVITY_ORDER as _SO

    # WKSP-304 P4 (D5 share-link semantics, fail-closed): the share token is
    # the SOLE authorization boundary for this endpoint. The caller's own
    # session identity/workspace membership must never broaden OR narrow
    # access to the one resource the token names — so ``identity`` is NOT
    # threaded from ``request.state`` here (unlike every other draft-reading
    # handler in this router). Both draft loads below pass ``identity=None``
    # explicitly.

    link = _resolve(paths, share_token)
    if link is None:
        raise HTTPException(
            status_code=404, detail="share link not found, revoked, or expired"
        )

    report_id = link["report_draft_id"]
    threshold = link["sensitivity_threshold"]
    threshold_rank = _SO.get(threshold, len(_SO))

    # Load the current draft state.
    try:
        draft = bsvc.load_draft(paths, report_id, identity=None)
    except NotFoundError:
        # Draft was deleted after the share link was created — treat as expired.
        raise HTTPException(
            status_code=404, detail="share link not found, revoked, or expired"
        )

    # Re-apply sensitivity check at resolution time (PRD AC-2).
    # The draft's sensitivity may have increased since the link was created.
    draft_sensitivity = str(draft.get("sensitivity") or "public")
    draft_rank = _SO.get(draft_sensitivity, len(_SO))
    if draft_rank > threshold_rank:
        raise HTTPException(
            status_code=422,
            detail={
                "ok": False,
                "reason": (
                    "draft sensitivity exceeds share link threshold — "
                    "fail-closed at resolution time (PRD AC-2)"
                ),
                "draft_sensitivity": draft_sensitivity,
                "share_threshold": threshold,
            },
        )

    # Generate read-only Markdown preview.
    try:
        preview_md = bsvc.export_markdown(paths, report_id, identity=None)
    except NotFoundError:  # pragma: no cover — draft existence verified above
        raise HTTPException(
            status_code=404, detail="share link not found, revoked, or expired"
        )

    # Audit-health gate (REVIEW-001 must-fix, AUDIT-004). This is the actual
    # public-exposure moment for a share token — a degraded audit store must
    # not silently allow returning preview content to an anonymous bearer.
    if not audit_service.is_healthy_for_exposure(paths):
        raise HTTPException(status_code=503, detail="Audit log unavailable")

    return {
        "ok": True,
        "report_draft_id": report_id,
        "sensitivity_threshold": threshold,
        "preview_markdown": preview_md,
    }


__all__ = ["router"]
