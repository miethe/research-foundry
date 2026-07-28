"""Knowledge API router -- GET-only parity for the RF Knowledge MCP (KMCP-5.2).

Thin transport layer over
:mod:`research_foundry.services.knowledge_access` (the shared, governed P2/P3
read service) -- this module contains ONLY request parsing and response
rendering (invariant 4, "one service contract: transports contain parsing/
rendering only"). It adds no local filtering, ranking, redaction, receipt, or
URL logic of its own.

Route inventory (mirrors the exact eight-tool inventory
:mod:`research_foundry.knowledge_mcp.registry` registers for the stdio MCP
process, decisions-block Section 9.2, one GET route per tool name):

  GET /api/knowledge/v1/search              -> core ``search``  (frozen SearchDTO)
  GET /api/knowledge/v1/fetch/{knowledge_id} -> core ``fetch``   (frozen FetchDTO;
                                                 THIS is the literal route every
                                                 ``local_resource_url`` -- both core
                                                 and RF-extended -- points back to;
                                                 see "Local resource URL contract"
                                                 below)
  GET /api/knowledge/search                 -> ``rf_search``  (kinds/limit/cursor/receipt)
  GET /api/knowledge/fetch/{knowledge_id}    -> ``rf_fetch``   (cursor/receipt/rf_metadata)
  GET /api/knowledge/source/{knowledge_id}   -> ``rf_source_get``    (typed getter)
  GET /api/knowledge/assertion/{knowledge_id} -> ``rf_assertion_get`` (typed getter)
  GET /api/knowledge/report/{knowledge_id}   -> ``rf_report_get``    (typed getter)
  GET /api/knowledge/run/{knowledge_id}      -> ``rf_run_get``       (typed getter)

There is NO POST/PUT/PATCH/DELETE route in this router (KMCP-5.2 acceptance:
"No POST/PUT/PATCH/DELETE"). Every route above is a read.

**Local resource URL contract (KMCP-OQ-3, invariant 6).** Every ``url`` field
:mod:`knowledge_access` emits is built by
:func:`knowledge_access.build_local_resource_url` against the frozen,
schema-pinned path ``/api/knowledge/v1/fetch/<percent-encoded-opaque-id>``
(``knowledge_search_response.schema.yaml``'s and ``knowledge_document.
schema.yaml``'s own ``$defs.local_resource_url`` regex) -- this router's
``GET /api/knowledge/v1/fetch/{knowledge_id}`` route is that literal
resource, registered here so those URLs are real, allowlisted GET routes
rather than dead references. It is intentionally distinct from the richer
``GET /api/knowledge/fetch/{knowledge_id}`` route below (``rf_fetch``
parity) -- the two return different DTO shapes (frozen core vs RF-extended),
exactly mirroring the MCP process's own separately-named ``fetch``/
``rf_fetch`` tools.

**Identity and sensitivity ceiling (KMCP-5.2).** Unlike the stdio MCP
transport (KMCP-4.1, which always resolves ``identity=None`` -- "local
trust", no separate remote auth in v1), this HTTP transport resolves and
enforces an explicit identity exactly like every other GET-only RF read
router (``request.state.identity``, set by the optional auth middleware;
``None`` when no auth provider is configured -- single-operator-trust,
unchanged behavior). The sensitivity ceiling is the SAME server-wide
``rf serve --sensitivity-threshold`` override every other reader router
already honors (``request.app.state.catalog_sensitivity_threshold``, set
once at startup by ``api.app.create_app`` -- see
``research_foundry.api.routers.catalog._sensitivity_threshold_override``'s
own docstring for why this cannot be re-derived from ``paths`` alone), with
an explicit ``?sensitivity_threshold=`` query parameter taking precedence
when supplied (mirrors ``routers.runs``'s ``effective_threshold`` pattern
exactly).

**Safe denial (decisions-block Section 0/3 Risk 2, KMCP-OQ-1) -- same
no-existence-leak shape as the service.** ``search``/``rf_search`` never
raise for a policy denial or malformed query -- any
:class:`knowledge_access.KnowledgeAccessError` collapses to the SAME empty,
HTTP 200 shape a zero-match query would produce. ``fetch``/``rf_fetch`` and
all four typed getters map EVERY such error (malformed id, missing, hidden,
cross-workspace, rights-denied, stale/unavailable projection, or a
wrong-kind id for a typed getter) to the SAME generic
``HTTPException(404, _FETCH_DENIED_MESSAGE)`` -- the exception's own
internal ``reason`` is never rendered in the response body, and a caller can
never distinguish "unknown" from "hidden" by status code or message
(mirrors ``research_foundry.knowledge_mcp.registry``'s identical "Safe
denial" contract).

**No ``rf_schema_version`` stamp on knowledge responses.** Every other RF
read router (see ``response_stamp.stamp``) additively sets a top-level
``rf_schema_version`` key on its JSON body. This router deliberately never
does that: the P1-frozen core DTOs
(``knowledge_search_response.schema.yaml`` / ``knowledge_document.
schema.yaml``) are CLOSED roots (``additionalProperties: false``, invariant
5 -- "no root/result fields added"), so stamping an extra key onto a core
``search``/``fetch`` response would violate its own frozen shape. The
RF-extended and typed-getter responses stay unstamped too, for the same
closed-root reason and for byte-for-byte service/CLI/API/MCP parity
(AC KMCP-5).
"""

from __future__ import annotations

from typing import Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...errors import RFError
from ...paths import FoundryPaths
from ...services import knowledge_access as ka
from .runs import get_paths

router = APIRouter()

# Module-level singleton (ruff B008: avoid calling Depends()/Query() in an
# argument default expression) -- mirrors this repo's own
# `_PATHS_DEP`/`_TERM_QUERY` convention in api/routers/catalog.py. Wraps the
# same `get_paths` callable `app.dependency_overrides[get_paths]` targets in
# tests, so overriding still works regardless of where this instance lives.
_PATHS_DEP = Depends(get_paths)
_KIND_QUERY = Query(None)

# Same generic, detail-free denial message
# `research_foundry.knowledge_mcp.registry` uses for every `fetch`-shaped
# denial (decisions-block Section 0/3 Risk 2) -- reimplemented by value, not
# imported, so this always-installed router never depends on the optional
# `mcp` SDK's package (research_foundry.knowledge_mcp is an independent,
# optional-SDK process boundary -- invariant 1).
_FETCH_DENIED_MESSAGE = "Unable to fetch the requested knowledge id."


def _sensitivity_threshold_override(request: Request) -> str | None:
    """Read the serve-time sensitivity-threshold override off ``app.state``.

    Mirrors ``research_foundry.api.routers.catalog._sensitivity_threshold_
    override`` / ``routers.runs._sensitivity_threshold_override`` exactly --
    same server-wide state key, same fallback-to-``None`` contract.
    """

    return getattr(request.app.state, "catalog_sensitivity_threshold", None)


def _identity_from_request(request: Request) -> Any:
    """Read ``request.state.identity`` (``None`` when no auth middleware is
    configured -- see ``api/auth/provider.py``'s absent-identity contract).
    Mirrors ``routers.runs``/``routers.assertions``'s identical helper."""

    return getattr(request.state, "identity", None)


def _bootstrap_projectors(paths: FoundryPaths) -> None:
    """Seed :mod:`knowledge_access`'s process-global projector registry for
    THIS ``rf serve`` process's resolved workspace.

    The projector registry is a plain process-global dict in
    ``knowledge_access.py``; a request handler in a freshly-started ``rf
    serve`` process would otherwise only ever see the P2 skeleton's own "no
    projector registered" exit condition (empty results /
    ``projection_unavailable`` denial for every kind). Overwriting on every
    call is intentional and cheap (five dict assignments) -- it is what lets
    a long-lived ``rf serve`` process serve correctly regardless of when a
    request first arrives, without a separate app-startup hook. Reimplemented
    by value from ``research_foundry.knowledge_mcp.registry._bootstrap_
    projectors`` (not imported -- this router never depends on the optional
    ``mcp`` SDK package).
    """

    ka.register_projector("source", ka.SourceKindProjector(paths))
    ka.register_projector("assertion", ka.AssertionKindProjector(paths))
    ka.register_projector("report_draft", ka.ReportKindProjector(paths, target_kind="report_draft"))
    ka.register_projector("report_final", ka.ReportKindProjector(paths, target_kind="report_final"))
    ka.register_projector("run", ka.RunKindProjector(paths))


def _context(
    paths: FoundryPaths,
    request: Request,
    tool: str,
    sensitivity_threshold: str | None,
) -> ka.KnowledgeAccessContext:
    """Resolve one request's :class:`knowledge_access.KnowledgeAccessContext`.

    Threads the real ``request.state.identity`` (never ``None`` by
    construction on this transport -- see module docstring) and the
    effective sensitivity ceiling: the explicit ``?sensitivity_threshold=``
    query parameter when supplied, else the ``rf serve
    --sensitivity-threshold`` server-wide override, else
    ``export_service.resolve_threshold``'s own foundry.yaml/hardcoded-default
    fallback. Raises :class:`fastapi.HTTPException` (400) if the resolved
    label is not a recognised sensitivity value -- ``resolve_context`` itself
    raises ``export_service.ExportError`` (an :class:`~research_foundry.errors.RFError`,
    not a :class:`knowledge_access.KnowledgeAccessError`) for that case, so
    this catches the broader base class rather than only the Knowledge-
    specific hierarchy.
    """

    _bootstrap_projectors(paths)
    effective_threshold = (
        sensitivity_threshold
        if sensitivity_threshold is not None
        else _sensitivity_threshold_override(request)
    )
    try:
        return ka.resolve_context(
            paths,
            tool=tool,
            identity=_identity_from_request(request),
            sensitivity_threshold=effective_threshold,
        )
    except RFError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _fetch_denied() -> NoReturn:
    raise HTTPException(status_code=404, detail=_FETCH_DENIED_MESSAGE)


def _typed_get(
    paths: FoundryPaths,
    request: Request,
    tool: str,
    expected_kinds: frozenset[str],
    *,
    knowledge_id: str,
    cursor: str | None,
    parent_run_ref: str | None,
    sensitivity_threshold: str | None,
) -> dict[str, Any]:
    """Shared body for every typed getter (source/assertion/report/run) --
    a THIN ``fetch_extended`` call additionally gated to ``expected_kinds``,
    checked via :func:`knowledge_access.parse_knowledge_id` BEFORE the
    underlying governed read authority is ever touched (mirrors
    ``research_foundry.knowledge_mcp.registry``'s identical ``_typed_get``
    helper)."""

    context = _context(paths, request, tool, sensitivity_threshold)
    service = ka.KnowledgeAccessService(paths)
    try:
        resolved_kind, _opaque = ka.parse_knowledge_id(knowledge_id)
        if resolved_kind not in expected_kinds:
            raise ka.KnowledgeDenied("kind_not_eligible")
        document = service.fetch_extended(
            context,
            knowledge_id=knowledge_id,
            cursor=cursor,
            parent_run_ref=parent_run_ref,
            include_receipt=True,
        )
    except ka.KnowledgeAccessError:
        _fetch_denied()
    return document.to_dict()


# ---------------------------------------------------------------------------
# Core tools (KMCP-1.2 frozen shapes) -- versioned `/v1/` path segment, the
# literal `local_resource_url` route.
# ---------------------------------------------------------------------------


@router.get("/knowledge/v1/search", summary="Frozen core knowledge search")
def get_knowledge_core_search(
    request: Request,
    query: str = Query(..., min_length=1, max_length=ka.QUERY_MAX_LENGTH),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Frozen core ``search(query)`` (KMCP-1.2) -- exactly one input field.

    Returns the exact core ``SearchDTO``: ``{"results": [{id, title, url},
    ...]}``, at most 10 items, each snippet-free. A policy-hidden or
    genuinely absent match never distinguishably affects this result -- both
    collapse to the same ``results: []``-shaped outcome, HTTP 200 (see
    module docstring's "Safe denial" section).
    """

    context = _context(paths, request, "search", None)
    service = ka.KnowledgeAccessService(paths)
    try:
        response = service.search_core(context, query=query)
    except ka.KnowledgeAccessError:
        return ka.KnowledgeSearchResponse().to_dict()
    return response.to_dict()


@router.get(
    "/knowledge/v1/fetch/{knowledge_id}",
    summary="Frozen core knowledge fetch (local resource URL contract)",
)
def get_knowledge_core_fetch(
    knowledge_id: str,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Frozen core ``fetch(id)`` (KMCP-1.2) -- exactly one input field.

    Returns the exact core ``FetchDTO``: required ``id``/``title``/``text``/
    ``url`` plus optional generic ``metadata``. This is the literal route
    every ``local_resource_url`` (core or RF-extended) points back to (see
    module docstring's "Local resource URL contract" section). Every denial
    cause maps to the same generic 404 (see module docstring's "Safe
    denial" section); the exception's own internal ``reason`` is never
    rendered.
    """

    context = _context(paths, request, "fetch", None)
    service = ka.KnowledgeAccessService(paths)
    try:
        document = service.fetch_core(context, knowledge_id=knowledge_id)
    except ka.KnowledgeAccessError:
        _fetch_denied()
    return document.to_dict()


# ---------------------------------------------------------------------------
# RF-extended tools (KMCP-FR-5) -- unversioned `/api/knowledge/` prefix.
# ---------------------------------------------------------------------------


@router.get("/knowledge/search", summary="RF-extended knowledge search")
def get_knowledge_search(
    request: Request,
    query: str = Query(..., min_length=1, max_length=ka.QUERY_MAX_LENGTH),
    kind: list[str] | None = _KIND_QUERY,
    limit: int = Query(ka.RF_SEARCH_DEFAULT_LIMIT, ge=1, le=ka.RF_SEARCH_MAX_RESULTS),
    cursor: str | None = Query(None),
    parent_run_ref: str | None = Query(None),
    sensitivity_threshold: str | None = Query(
        None, description="Override foundry.yaml viewer.sensitivity_threshold (default: public)."
    ),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """RF-extended ``rf_search`` (KMCP-FR-5) -- thin call to
    :meth:`knowledge_access.KnowledgeAccessService.search_extended`.

    Adds the optional ``kind`` allowlist (narrows, never widens, eligibility
    -- ``knowledge_access.eligible_kinds``), ``limit``/``cursor`` paging, and
    a caller-carried, non-persisted RF activity receipt
    (``include_receipt=True`` always, for this route). Each result item
    carries ``kind``/``snippet``/``rank``/``score``/``content_is_untrusted``
    -- every field the core ``search`` result intentionally omits (invariant
    5). Denial contract identical to core ``search`` (see module docstring's
    "Safe denial" section).
    """

    context = _context(paths, request, "rf_search", sensitivity_threshold)
    service = ka.KnowledgeAccessService(paths)
    try:
        outcome = service.search_extended(
            context,
            query=query,
            kinds=kind or None,
            limit=limit,
            cursor=cursor,
            parent_run_ref=parent_run_ref,
            include_receipt=True,
        )
    except ka.KnowledgeAccessError:
        return ka.RfKnowledgeSearchOutcome().to_dict()
    return outcome.to_dict()


@router.get("/knowledge/fetch/{knowledge_id}", summary="RF-extended knowledge fetch")
def get_knowledge_fetch(
    knowledge_id: str,
    request: Request,
    cursor: str | None = Query(None),
    parent_run_ref: str | None = Query(None),
    sensitivity_threshold: str | None = Query(
        None, description="Override foundry.yaml viewer.sensitivity_threshold (default: public)."
    ),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """RF-extended ``rf_fetch`` (KMCP-FR-5) -- thin call to
    :meth:`knowledge_access.KnowledgeAccessService.fetch_extended`.

    Adds cursor-based text paging, the typed per-kind ``rf_metadata`` bag,
    ``original_source_url`` (when policy allows one), and a caller-carried
    receipt (``include_receipt=True`` always). Denial contract identical to
    core ``fetch`` -- see module docstring's "Safe denial" section.
    """

    context = _context(paths, request, "rf_fetch", sensitivity_threshold)
    service = ka.KnowledgeAccessService(paths)
    try:
        document = service.fetch_extended(
            context,
            knowledge_id=knowledge_id,
            cursor=cursor,
            parent_run_ref=parent_run_ref,
            include_receipt=True,
        )
    except ka.KnowledgeAccessError:
        _fetch_denied()
    return document.to_dict()


@router.get("/knowledge/source/{knowledge_id}", summary="Typed getter: source")
def get_knowledge_source(
    knowledge_id: str,
    request: Request,
    cursor: str | None = Query(None),
    parent_run_ref: str | None = Query(None),
    sensitivity_threshold: str | None = Query(None),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Typed getter scoped to the ``source`` kind (``rf_source_get`` parity)."""

    return _typed_get(
        paths,
        request,
        "rf_source_get",
        frozenset({"source"}),
        knowledge_id=knowledge_id,
        cursor=cursor,
        parent_run_ref=parent_run_ref,
        sensitivity_threshold=sensitivity_threshold,
    )


@router.get("/knowledge/assertion/{knowledge_id}", summary="Typed getter: assertion")
def get_knowledge_assertion(
    knowledge_id: str,
    request: Request,
    cursor: str | None = Query(None),
    parent_run_ref: str | None = Query(None),
    sensitivity_threshold: str | None = Query(None),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Typed getter scoped to the ``assertion`` kind (``rf_assertion_get`` parity)."""

    return _typed_get(
        paths,
        request,
        "rf_assertion_get",
        frozenset({"assertion"}),
        knowledge_id=knowledge_id,
        cursor=cursor,
        parent_run_ref=parent_run_ref,
        sensitivity_threshold=sensitivity_threshold,
    )


@router.get("/knowledge/report/{knowledge_id}", summary="Typed getter: report")
def get_knowledge_report(
    knowledge_id: str,
    request: Request,
    cursor: str | None = Query(None),
    parent_run_ref: str | None = Query(None),
    sensitivity_threshold: str | None = Query(None),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Typed getter addressing BOTH ``report_draft`` and ``report_final`` ids
    (KMCP-OQ-2 -- two distinct kinds, one getter name; ``rf_report_get`` parity)."""

    return _typed_get(
        paths,
        request,
        "rf_report_get",
        frozenset({"report_draft", "report_final"}),
        knowledge_id=knowledge_id,
        cursor=cursor,
        parent_run_ref=parent_run_ref,
        sensitivity_threshold=sensitivity_threshold,
    )


@router.get("/knowledge/run/{knowledge_id}", summary="Typed getter: run")
def get_knowledge_run(
    knowledge_id: str,
    request: Request,
    cursor: str | None = Query(None),
    parent_run_ref: str | None = Query(None),
    sensitivity_threshold: str | None = Query(None),
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Typed getter scoped to the ``run`` kind (``rf_run_get`` parity)."""

    return _typed_get(
        paths,
        request,
        "rf_run_get",
        frozenset({"run"}),
        knowledge_id=knowledge_id,
        cursor=cursor,
        parent_run_ref=parent_run_ref,
        sensitivity_threshold=sensitivity_threshold,
    )


__all__ = ["router"]
