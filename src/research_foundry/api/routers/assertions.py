"""Governed assertion-catalog read endpoints.

These routes intentionally expose lexical, workspace-scoped evidence packets
only.  They do not add vector retrieval, graph traversal, or mutation paths.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ...paths import FoundryPaths
from ...services.assertion_catalog import AssertionCatalog, AssertionCatalogDenied
from ...services.assertion_impact import AssertionImpactReadDenied, AssertionImpactReader
from ...services.research_run_discovery import ResearchRunDiscovery, ResearchRunDiscoveryDenied
from .runs import get_paths

router = APIRouter()
_PATHS_DEP = Depends(get_paths)


class RightsDecision(BaseModel):
    allowed: bool
    reason_code: str


class AssertionSummary(BaseModel):
    assertion_id: str
    assertion_version: int
    lifecycle_state: str
    access_scope: str
    rights_decision: RightsDecision


class AssertionFacets(BaseModel):
    lifecycle_states: list[str]
    access_scopes: list[str]


class AssertionSearchResponse(BaseModel):
    items: list[AssertionSummary]
    next_cursor: str | None
    facets: AssertionFacets
    denial_reason: str | None


class InferenceLineageEntry(BaseModel):
    inference_id: str
    inference_version: int
    status: str | None = None
    report_uses: list[str] = Field(default_factory=list)


class CanonicalClaimLineageEntry(BaseModel):
    canonical_claim_id: str
    canonical_claim_version: int
    state: str | None = None
    report_uses: list[str] = Field(default_factory=list)


class EvidencePacket(BaseModel):
    packet_version: str
    assertion_id: str
    assertion_version: int
    assertion: dict[str, Any]
    passage: dict[str, Any]
    source_edition: dict[str, Any]
    qualifiers: dict[str, Any]
    # Older ledger exports predate this additive map.  Preserve that absence
    # through the read boundary so consumers can render an explicit legacy
    # state instead of mistaking it for an authoritatively empty map.
    qualifier_extensions: dict[str, Any] | None = None
    evaluations: list[dict[str, Any]]
    freshness: dict[str, Any]
    access_scope: str
    rights_decision: RightsDecision
    relationships: list[dict[str, Any]]
    run_uses: list[str]
    report_uses: list[str]
    # RPC-5.2: additive activity/lineage projections (AC RPC-5). A legacy
    # assertion with no inference/canonical-claim/report-use/origin activity
    # simply has empty optional values here -- never an omitted key (AC
    # RPC-5 resilience: "legacy records expose empty optional fields").
    inference_lineage: list[InferenceLineageEntry] = Field(default_factory=list)
    canonical_claim_lineage: list[CanonicalClaimLineageEntry] = Field(default_factory=list)
    run_facets: dict[str, dict[str, Any] | None] = Field(default_factory=dict)
    search_activity_ids: list[str] = Field(default_factory=list)


class AssertionLineage(BaseModel):
    assertion_id: str
    assertion_version: int
    relationships: list[dict[str, Any]]
    run_uses: list[str]
    report_uses: list[str]
    inference_lineage: list[InferenceLineageEntry] = Field(default_factory=list)
    canonical_claim_lineage: list[CanonicalClaimLineageEntry] = Field(default_factory=list)
    run_facets: dict[str, dict[str, Any] | None] = Field(default_factory=dict)
    search_activity_ids: list[str] = Field(default_factory=list)
    denial_reason: str | None


class AssertionImpactAction(BaseModel):
    object_id: str
    object_class: str
    action: str
    status: Literal["pending", "completed", "failed", "blocked"]
    writeback_status: Literal["default_denied", "denied", "queued"] | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
    )


class AssertionImpactSummary(BaseModel):
    event_id: str
    assertion_id: str
    lifecycle_state: str
    access_scope: str
    authoritative_reuse_blocked: Literal[True]
    operation_status: Literal["pending", "blocked", "completed"]
    reason_code: str | None = None
    replacement_edition_id: str | None = None
    resumable: bool
    actions: list[AssertionImpactAction]


class AssertionImpactReasonDetail(BaseModel):
    """A safe, reason-code-only detail payload for impact denial or absence."""

    reason_code: str


class AssertionImpactReasonResponse(BaseModel):
    """The runtime HTTPException envelope for governed impact failures."""

    detail: AssertionImpactReasonDetail


class ResearchActivitySummary(BaseModel):
    """RPC-5.3: one row of ``ResearchRunDiscovery.list_activities``'s output.

    Mirrors that service's own ``_summary`` shape verbatim -- no fabricated
    ``run_id`` on a ``search_only`` row (RPC-FR-2).
    """

    envelope_id: str
    activity_kind: str
    activity_id: str | None = None
    planned_run_ref: dict[str, Any] | None = None
    outcome: str | None = None


class ResearchActivityListResponse(BaseModel):
    items: list[ResearchActivitySummary]
    next_cursor: str | None
    denial_reason: str | None


class ResearchActivityDetail(BaseModel):
    """RPC-5.3/5.4: exact envelope/receipt round trip for one activity."""

    envelope: dict[str, Any]
    receipt: dict[str, Any] | None


def _catalog(paths: FoundryPaths) -> AssertionCatalog:
    return AssertionCatalog(paths)


def _impact_reader(paths: FoundryPaths) -> AssertionImpactReader:
    return AssertionImpactReader(paths)


def _discovery(paths: FoundryPaths, workspace_id: str) -> ResearchRunDiscovery:
    return ResearchRunDiscovery(workspace_id=workspace_id, paths=paths)


def _denial(exc: AssertionCatalogDenied) -> HTTPException:
    return HTTPException(status_code=403, detail={"reason_code": exc.reason_code})


def _impact_denial(exc: AssertionImpactReadDenied) -> HTTPException:
    return HTTPException(status_code=403, detail={"reason_code": exc.reason_code})


def _impact_unavailable() -> HTTPException:
    """Return one safe unavailable result for absent or unreadable receipts."""

    return HTTPException(status_code=404, detail={"reason_code": "impact_unavailable"})


@router.get("/assertions/search", response_model=AssertionSearchResponse, summary="Search governed assertions")
def search_assertions(
    request: Request,
    q: str | None = Query(None, max_length=512),
    lifecycle_state: str | None = Query(None),
    access_scope: str | None = Query(None),
    limit: int = Query(25, ge=1, le=100),
    cursor: str | None = Query(None, max_length=512),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Search the caller's private assertion projection.

    Authorization and rights filtering occur before lexical matching, counts,
    facets, and pagination.  Missing context produces a typed empty response.
    """

    identity = getattr(request.state, "identity", None)
    return _catalog(paths).search(
        identity=identity,
        query=q,
        lifecycle_state=lifecycle_state,
        access_scope=access_scope,
        limit=limit,
        cursor=cursor,
    )


@router.get("/assertions/{assertion_id}/lineage", response_model=AssertionLineage, summary="Get assertion lineage")
def get_assertion_lineage(
    assertion_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Return typed, bounded lineage already present in durable ledger records."""

    try:
        lineage = _catalog(paths).lineage(assertion_id, identity=getattr(request.state, "identity", None))
    except AssertionCatalogDenied as exc:
        raise _denial(exc) from exc
    if lineage is None:
        raise HTTPException(status_code=404, detail="assertion not found")
    return lineage


@router.get(
    "/assertions/{assertion_id}/impact",
    response_model=AssertionImpactSummary,
    responses={
        403: {"model": AssertionImpactReasonResponse, "description": "Impact read denied"},
        404: {"model": AssertionImpactReasonResponse, "description": "Impact unavailable"},
    },
    summary="Get a governed assertion impact summary",
)
def get_assertion_impact(
    assertion_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Expose a policy-authorized P5 receipt without ledger-path details.

    Missing, malformed, interrupted-unreadable, and cross-workspace state all
    resolve to the identical unavailable response.  This route is read-only;
    lifecycle reconciliation remains outside the HTTP API.
    """

    try:
        summary = _impact_reader(paths).summary(
            assertion_id,
            identity=getattr(request.state, "identity", None),
        )
    except AssertionImpactReadDenied as exc:
        raise _impact_denial(exc) from exc
    if summary is None:
        raise _impact_unavailable()
    return summary


@router.get(
    "/assertions/activities",
    response_model=ResearchActivityListResponse,
    summary="List governed research-run activities",
)
def list_research_activities(
    request: Request,
    activity_kind: Literal["planned_run", "search_only"] | None = Query(None),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """List the caller's workspace-scoped research-run activities (RPC-5.3).

    A ``search_only`` activity with no planned run and no linked assertion
    (e.g. a zero-match search) has no OTHER governed HTTP surface -- an
    evidence packet's ``search_activity_ids`` only names an activity once its
    receipt has selected at least one assertion version. This route reuses
    ``research_run_discovery.ResearchRunDiscovery`` verbatim, so listing stays
    workspace-isolated and applies the SAME run-visibility gate a
    ``planned_run`` row already gets in a packet's ``run_facets``. Missing
    workspace context degrades to the SAME typed-empty shape
    ``/assertions/search`` uses -- never a 4xx that would distinguish
    "no workspace" from "empty workspace".
    """

    identity = getattr(request.state, "identity", None)
    if identity is None or not identity.workspace_id:
        return ResearchRunDiscovery.denied_payload("workspace_context_missing")
    discovery = _discovery(paths, identity.workspace_id)
    return discovery.list_activities(activity_kind=activity_kind, identity=identity)


@router.get(
    "/assertions/activities/{envelope_id}",
    response_model=ResearchActivityDetail,
    responses={404: {"model": AssertionImpactReasonResponse, "description": "Activity not found or denied"}},
    summary="Fetch one governed research-run activity",
)
def get_research_activity(
    envelope_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Fetch one activity's exact envelope/receipt pair (RPC-5.3/5.4).

    Missing workspace context, an unknown ``envelope_id``, a cross-workspace
    ``envelope_id``, and a denied run-scope gate all resolve to the identical
    404/``not_authorized_or_not_found`` shape -- mirroring
    ``ResearchRunDiscoveryDenied``'s own no-existence-leak contract rather
    than inventing a second, more informative denial here.
    """

    identity = getattr(request.state, "identity", None)
    if identity is None or not identity.workspace_id:
        raise HTTPException(status_code=404, detail={"reason_code": "workspace_context_missing"})
    discovery = _discovery(paths, identity.workspace_id)
    try:
        record = discovery.fetch_activity(envelope_id, identity=identity)
    except ResearchRunDiscoveryDenied as exc:
        raise HTTPException(status_code=404, detail={"reason_code": exc.reason_code}) from exc
    return {"envelope": record.envelope, "receipt": record.receipt}


@router.get("/assertions/{assertion_id}", response_model=EvidencePacket, summary="Get a governed evidence packet")
def get_assertion_packet(
    assertion_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Return an assertion only with its passage, edition, rights, and lineage."""

    try:
        packet = _catalog(paths).packet(assertion_id, identity=getattr(request.state, "identity", None))
    except AssertionCatalogDenied as exc:
        raise _denial(exc) from exc
    if packet is None:
        raise HTTPException(status_code=404, detail="assertion not found")
    return packet


__all__ = ["router"]
