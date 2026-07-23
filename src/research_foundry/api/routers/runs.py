"""Runs API router — Phase P2 read endpoints + P5 run-launch mutation.

All data paths route through the export service (R1 invariant):
  - list_runs()   → export_service.list_runs(paths)
  - export_run()  → export_service.export_run(paths, run_id)
  - claims slice  → export_run(...)["claims"]
  - source lookup → scan export_run(...)["claims"][*]["sources"]

Raw run artifact files are NEVER read directly here; all sensitivity
gating is enforced inside the export service before data reaches these
handlers.

Endpoint → client.ts mapping:
  GET  /api/runs                              → fetchRunList()
  GET  /api/runs/{run_id}                     → fetchRunDetail()
  GET  /api/runs/{run_id}/claims              → fetchClaimLedger()
  GET  /api/runs/{run_id}/sources/{sc_id}     → fetchSourceCard()
  GET  /api/runs/{run_id}/context             → fetchRunContext() (DFR-001 v2
                                                 lazy-load; same shape as
                                                 run.json's "context" key)
  POST /api/runs                              → scaffold + register a new run
                                                 (http-run-launch-endpoint contract;
                                                 does NOT drive the Path B swarm)

The /data/governance.json route is defined in app.py (not under /api).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ...config import FoundryConfig
from ...errors import GovernanceError, NotFoundError, RFError, SchemaError
from ...paths import FoundryPaths
from ...services import audit_service, run_launch
from ...services.audit_service import AuditEvent
from ...services.export_service import (
    SENSITIVITY_ORDER,
    ExportError,
    export_run,
    list_runs,
    resolve_threshold,
)
from ..auth.provider import AuthIdentity
from ..auth.rbac import require_role
from ..response_stamp import stamp

logger = logging.getLogger(__name__)

router = APIRouter()

# RBAC-FORWARD-COMPAT (RBAC-005, RBAC-901): run:launch is an admin-class
# mutation (scaffolds file-backed artifacts + registers a run) -- same class
# as agent_jobs.py's POST /agent-jobs. All mutation routes in this router
# require owner or admin (http-run-launch-endpoint contract, Decision #3).
_RBAC_RUN_LAUNCH = Depends(require_role("owner", "admin"))


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

def _sensitivity_threshold_override(request: Request) -> str | None:
    """Read the serve-time sensitivity-threshold override off ``app.state``.

    Mirrors :func:`research_foundry.api.routers.catalog._sensitivity_threshold_override`
    exactly. Set once at startup by :func:`research_foundry.api.app.create_app`
    from the (already CLI-flag > foundry.yaml resolved) ``FoundryConfig`` — see
    that function for why this router cannot resolve this itself from ``paths``
    alone. Without this, ``rf serve --sensitivity-threshold <X>`` was silently
    ignored by every GET endpoint below: each one only ever received a bare
    ``FoundryPaths`` via the ``get_paths()`` dependency, so
    ``resolve_threshold()`` always fell back to whatever foundry.yaml's
    ``viewer.sensitivity_threshold`` said instead (``"public"`` by default),
    even when the CLI flag requested a looser threshold.

    ``None`` when no override was captured, in which case
    ``export_service.resolve_threshold()`` falls back to its own foundry.yaml
    / hardcoded-default resolution, unchanged from prior behavior — so this is
    a no-op when ``rf serve`` was started without the flag.
    """
    return getattr(request.app.state, "catalog_sensitivity_threshold", None)


def _identity_from_request(request: Request) -> AuthIdentity | None:
    """Read ``request.state.identity`` (``None`` when no auth middleware is
    configured -- see ``api/auth/provider.py``'s absent-identity contract)."""

    return getattr(request.state, "identity", None)


def _enforce_existence_gate(
    paths: FoundryPaths,
    run_id: str,
    sensitivity_threshold: str | None,
    identity: AuthIdentity | None = None,
) -> dict[str, Any]:
    """Load and gate *run_id* against *sensitivity_threshold* and *identity*.

    Returns the export dict when the run exists, is at or below the caller's
    requested threshold, AND (DF-004) is readable by *identity* under the
    workspace-scope read gate.

    Raises:
        HTTPException(400): *sensitivity_threshold* is not a recognised label.
        HTTPException(404): run not found, run sensitivity exceeds the
            threshold, **or** the run is workspace-scoped away from
            *identity* (DF-004) — all three cases are intentionally
            indistinguishable so that hidden/other-workspace run IDs are
            never leaked (no-existence-leak / landmine #4; never a 403).
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
        data = export_run(paths, run_id, sensitivity_threshold=threshold, identity=identity)
    except ExportError as exc:
        raise HTTPException(status_code=404, detail="not found") from exc

    # DF-004: export_run() returns None on a workspace-scope enforced denial —
    # map it to the same 404 a genuinely-missing run gets (never a 403).
    if data is None:
        raise HTTPException(status_code=404, detail="not found")

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
def get_run_list(
    request: Request, paths: FoundryPaths = Depends(get_paths)
) -> list[dict[str, Any]]:
    """Return a summary of every discovered run.

    Empty corpus returns ``[]`` — never 404.  All data is routed through
    :func:`~research_foundry.services.export_service.list_runs` (R1).

    DF-004: runs the caller's ``identity`` cannot read under active workspace
    isolation (not public, not the caller's own workspace) are silently
    omitted — filtered, never 403/404'd (there is no single "not found" run
    to gate on a list endpoint).
    """
    return list_runs(paths, identity=_identity_from_request(request))


@router.get("/runs/{run_id}", summary="Get run detail")
def get_run_detail(
    run_id: str,
    request: Request,
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

    The explicit ``?sensitivity_threshold=`` query param always takes
    precedence; when omitted, falls back to the ``rf serve
    --sensitivity-threshold`` override captured on ``app.state`` (see
    :func:`_sensitivity_threshold_override`).

    Raises 404 when the run does not exist or is over-threshold.
    Raises 400 on invalid sensitivity_threshold.
    """
    effective_threshold = (
        sensitivity_threshold
        if sensitivity_threshold is not None
        else _sensitivity_threshold_override(request)
    )
    return stamp(_enforce_existence_gate(
        paths, run_id, effective_threshold, _identity_from_request(request)
    ))


@router.get("/runs/{run_id}/claims", summary="Get claim ledger for a run")
def get_run_claims(
    run_id: str,
    request: Request,
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

    The explicit ``?sensitivity_threshold=`` query param always takes
    precedence over the ``rf serve --sensitivity-threshold`` override on
    ``app.state`` (see :func:`_sensitivity_threshold_override`).
    """
    effective_threshold = (
        sensitivity_threshold
        if sensitivity_threshold is not None
        else _sensitivity_threshold_override(request)
    )
    data = _enforce_existence_gate(
        paths, run_id, effective_threshold, _identity_from_request(request)
    )
    # export_run always populates "claims" as a list; guard defensively
    claims = data.get("claims")
    return claims if isinstance(claims, list) else []


@router.get("/runs/{run_id}/context", summary="Get context block for a run")
def get_run_context(
    run_id: str,
    request: Request,
    sensitivity_threshold: str | None = Query(
        None,
        description="Override foundry.yaml viewer.sensitivity_threshold (default: public).",
    ),
    paths: FoundryPaths = Depends(get_paths),
) -> dict[str, Any] | None:
    """Return the ``context`` block for *run_id* (DFR-001 v2 lazy-load endpoint).

    Response shape matches ``run.json``'s top-level ``context`` key exactly
    (schema 1.3 contract, §9 of ``rf-run-export-schema.md``) — the same shape
    the SPA's embedded ``run.context`` fallback already renders. Returns
    ``null`` (HTTP 200) when the run exists but carries no v2 context
    artifacts (no ``routing_decision.yaml``, ``swarm_plan.yaml``, or
    ``research_brief.md``).

    **Sensitivity gating**: identical existence-gate + redaction pass as
    ``GET /runs/{run_id}`` — a run whose sensitivity exceeds the threshold
    returns 404, indistinguishable from an unknown run (no-existence-leak /
    landmine #4). Redaction of ``routing_decision`` / ``swarm_plan`` /
    ``research_brief_md`` content is applied by
    :func:`~research_foundry.services.export_service._context_summary`
    before reaching this handler — data is always routed through the export
    service (R1), never read directly from run artifact files here.

    Raises 404 when the run does not exist or is over-threshold.
    Raises 400 on invalid sensitivity_threshold.
    """
    effective_threshold = (
        sensitivity_threshold
        if sensitivity_threshold is not None
        else _sensitivity_threshold_override(request)
    )
    data = _enforce_existence_gate(
        paths, run_id, effective_threshold, _identity_from_request(request)
    )
    return data.get("context")


@router.get(
    "/runs/{run_id}/sources/{source_card_id}",
    summary="Get a resolved source from a run's claim graph",
)
def get_source_card(
    run_id: str,
    source_card_id: str,
    request: Request,
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
    effective_threshold = (
        sensitivity_threshold
        if sensitivity_threshold is not None
        else _sensitivity_threshold_override(request)
    )
    data = _enforce_existence_gate(
        paths, run_id, effective_threshold, _identity_from_request(request)
    )

    for claim in (data.get("claims") or []):
        for source in (claim.get("sources") or []):
            if source.get("source_card_id") == source_card_id:
                return stamp(source)

    raise HTTPException(status_code=404, detail="source not found")


@router.get("/reports/{run_id}/anchors", summary="Get report anchors for a run")
def get_run_anchors(
    run_id: str,
    request: Request,
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
    effective_threshold = (
        sensitivity_threshold
        if sensitivity_threshold is not None
        else _sensitivity_threshold_override(request)
    )
    data = _enforce_existence_gate(
        paths, run_id, effective_threshold, _identity_from_request(request)
    )
    return stamp({"run_id": run_id, "report_anchors": data.get("report_anchors")})


# ---------------------------------------------------------------------------
# Mutation: POST /runs (http-run-launch-endpoint contract)
# ---------------------------------------------------------------------------


class LaunchRunRequest(BaseModel):
    """Body for POST /api/runs.

    Exactly one of ``text`` / ``intent_id`` is required — supplying both or
    neither is a 400 (raised as ``ValueError`` by
    :func:`~research_foundry.services.run_launch.launch_run` and mapped here).

    ``title``, ``sensitivity``, ``urgency``, ``tags``, and ``backlog_idea_ref``
    are ``text``-path fields (forwarded to ``capture_idea``) and are ignored
    when ``intent_id`` is supplied instead. The remaining fields are common
    planning passthrough forwarded to ``plan_run`` on both paths.

    ``reuse_assertion``, ``reuse_workspace_id``, ``required_reuse_edition_id``,
    and ``required_extraction_contract`` are optional reuse-reachability
    fields (Phase 4 of the assertion-ledger activation plan). All four are
    absent by default and, when omitted, ``run_launch.launch_run`` performs
    NO reuse evaluation at all -- launch behaves exactly as it did before
    this field set existed. When ``reuse_assertion`` is supplied, it is
    routed through the existing ``assertion_reuse.evaluate_reuse`` /
    ``retrieve_first_reuse_decision`` seam (no new policy logic here); an
    ineligible result (deny or refresh -- including a target denied via the
    existing ``block_authoritative_reuse`` lifecycle path, or a cross-
    workspace target) surfaces as a 400 via the existing
    ``except ValueError`` mapping below.

    ``visibility`` (DF-004) is the new run's read-visibility: ``"workspace"``
    (default) or ``"public"``. The owning ``workspace_id`` is NEVER taken
    from this request body -- it is always stamped server-side from
    ``request.state.identity.workspace_id`` (or left ``None`` when no auth
    middleware is configured, i.e. single-operator-trust mode).
    """

    text: str | None = None
    intent_id: str | None = None
    title: str | None = None
    sensitivity: str = "personal"
    urgency: str = "medium"
    tags: list[str] | None = None
    backlog_idea_ref: str | None = None
    depth: str = "standard"
    audience: str = "technical"
    max_cost_usd: float = 5.0
    freshness_days: int = 180
    profile: str | None = None
    project: str | None = None
    reuse_assertion: dict[str, Any] | None = None
    reuse_workspace_id: str | None = None
    required_reuse_edition_id: str | None = None
    required_extraction_contract: str | None = None
    visibility: str = "workspace"


@router.post("/runs", summary="Launch a new run (scaffold + register only)", status_code=201)
def launch_run_endpoint(
    body: LaunchRunRequest,
    request: Request,
    paths: FoundryPaths = Depends(get_paths),
    _rbac: None = _RBAC_RUN_LAUNCH,
) -> dict[str, Any]:
    """Scaffold and register a new run over HTTP (scaffold + register only).

    Accepts either ``text`` (runs ``capture_idea`` -> ``triage_idea`` ->
    ``plan_run``, mirroring ``rf capture`` -> ``rf triage`` -> ``rf plan``) or
    ``intent_id`` (calls ``plan_run`` directly, mirroring
    ``rf plan <intent_id>`` alone).

    **This endpoint does NOT spawn, drive, or poll the Path B Claude-agent
    discovery swarm** — see the Feature Contract Decision #1
    (``docs/project_plans/feature_contracts/features/http-run-launch-endpoint.md``).
    ``status`` in the response is always ``"planned"`` on success; poll
    ``GET /api/runs/{run_id}``'s ``status_derived`` field for actual progress
    once a swarm has run against the returned ``run_id`` out-of-band.
    """
    # DF-004: identity is now threaded through to launch_run() -> plan_run(),
    # which stamps run.yaml.workspace_id from identity.workspace_id (never
    # from client input). None when no auth middleware is configured.
    identity = _identity_from_request(request)

    try:
        result = run_launch.launch_run(
            text=body.text,
            intent_id=body.intent_id,
            title=body.title,
            sensitivity=body.sensitivity,
            urgency=body.urgency,
            tags=body.tags,
            backlog_idea_ref=body.backlog_idea_ref,
            depth=body.depth,
            audience=body.audience,
            max_cost_usd=body.max_cost_usd,
            freshness_days=body.freshness_days,
            profile=body.profile,
            project=body.project,
            reuse_assertion=body.reuse_assertion,
            reuse_workspace_id=body.reuse_workspace_id,
            required_reuse_edition_id=body.required_reuse_edition_id,
            visibility=body.visibility,
            identity=identity,
            required_extraction_contract=body.required_extraction_contract,
            paths=paths,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except GovernanceError as exc:
        # GovernanceError.violations is list[str] (rule_id strings) — a
        # simpler, DIFFERENT shape from agent_jobs.py's guard_check
        # GuardResult.violations (richer Violation objects with
        # rule_id/severity/message/detail). Adapt rather than force a false
        # 1:1 match (contract §11 Risk Area).
        raise HTTPException(
            status_code=422,
            detail={
                "error": "governance_rejected",
                "violations": [
                    {
                        "rule_id": rule_id,
                        "severity": "block",
                        "message": rule_id,
                        "detail": None,
                    }
                    for rule_id in exc.violations
                ],
            },
        ) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SchemaError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RFError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to launch run: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to launch run") from exc

    # Audit: record successful run launch after the run is scaffolded and
    # registered (fail-open — audit_service.record_event never raises).
    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="run_launched",
            action="launch_run",
            target_ref=result.run_id,
            result="success",
        ),
    )

    response: dict[str, Any] = {
        "run_id": result.run_id,
        "status": result.status,
        "intent_id": result.intent_id,
        "raw_idea_id": result.raw_idea_id,
        "brief_path": str(result.brief_path),
        "swarm_path": str(result.swarm_path),
        "routing_path": str(result.routing_path),
        "next_step": (
            f"Poll GET /api/runs/{result.run_id} for status_derived. This "
            "endpoint performs scaffold + register only — it does not drive "
            "the Path B discovery swarm; run the swarm out-of-band "
            f"(Claude Code agents authoring source cards) against run_id="
            f"{result.run_id}."
        ),
    }
    # reuse_decision is populated ONLY when a caller supplied reuse_assertion
    # (see LaunchRunRequest docstring) -- omitted entirely otherwise, so a
    # request with no reuse_* fields gets a byte-identical response shape to
    # before this field set existed (no behavior change on omission).
    if result.reuse_decision is not None:
        response["reuse_decision"] = {
            "action": result.reuse_decision.action,
            "reason_code": result.reuse_decision.reason_code,
            "assertion_id": result.reuse_decision.assertion_id,
        }
    return stamp(response)


# RBAC-005 / RBAC-901 audit: runs.py has one mutation route as of the
# http-run-launch-endpoint contract — POST /runs (gated by
# Depends(require_role("owner", "admin")) via _RBAC_RUN_LAUNCH, mirroring
# agent_jobs.py's mutation-route pattern exactly). The six GET routes below
# remain read-only:
#   GET  /runs
#   GET  /runs/{run_id}
#   GET  /runs/{run_id}/claims
#   GET  /runs/{run_id}/context
#   GET  /runs/{run_id}/sources/{source_card_id}
#   GET  /reports/{run_id}/anchors
#
# POST /runs:
#   POST /runs — scaffold + register a new run (launch_run_endpoint above).
#
# agent_jobs.py forward-compat: see RBAC-FORWARD-COMPAT note in
# src/research_foundry/api/auth/rbac.py module docstring (RBAC-005, RBAC-901).

__all__ = ["router", "LaunchRunRequest"]
