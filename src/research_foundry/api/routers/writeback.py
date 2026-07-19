"""Writeback Approve & Dispatch API router — Phase 2 (API-001..005).

Wraps the Phase 1 orchestration primitive
:func:`~research_foundry.services.writeback.approve_and_dispatch` in a single
gated HTTP route.

Route table (registered under /api prefix in app.py, UNCONDITIONALLY — this
route is not behind the ``agents.enabled`` feature flag that gates
``agent_jobs.py``, since ``rf writeback`` is not an agent-job surface):

  POST /runs/{run_id}/writeback/approve   approve a run's evidence bundle and
                                           dispatch it to writeback targets

Security invariants:
  * Gated by ``Depends(require_role("owner", "admin"))`` — mirrors
    ``agent_jobs.py``'s RBAC-FORWARD-COMPAT pattern (RBAC-005/RBAC-901).
    Respects ``auth.rbac_enforcement``'s auto/disabled/enabled modes for
    free via the shared ``require_role`` dependency.
  * Exactly one ``audit_service.record_event()`` call happens per invocation,
    covering all four outcome classes: success, partial ("failure" per
    ``AuditEvent.result``'s three-value contract), blocked ("denied"), and an
    unexpected exception from ``approve_and_dispatch()`` itself ("failure"
    with ``error_detail``). ``record_event()`` is documented fail-open/
    never-raises (see ``services/audit_service.py``), so the audit call
    itself is never guarded.
  * ``governance_rejected`` mapping mirrors ``agent_jobs.py::launch_job``'s
    422-if-guard-exit-code-3-else-400 rule, with one addition: the combined
    gate in ``approve_and_dispatch`` can ALSO block purely because
    ``council_decision == "required_block"`` even when ``guard_result.passed``
    is True. In that case there is no failing-guard exit_code to key off of,
    so a synthetic violation-shaped entry (``rule_id:
    "council_required_block"``) is appended to the ``violations`` list and
    the governance-block status class (422) is used. This keeps the response
    body shape identical to the guard-failure case — no new top-level fields.

Judgment calls (for the phase-owner's Completion Note):
  * NotFoundError from ``approve_and_dispatch`` (propagated from
    ``build_bundle`` when ``run_id`` does not exist) is treated as its own
    branch -> 404, still audited as an "exception" outcome ("failure" result
    + ``error_detail``) before the 404 is raised, rather than falling through
    to the generic 500 branch. This keeps a missing-run response consistent
    with the rest of the API (e.g. ``reports.py``) while still satisfying the
    "exactly one audit row per invocation, even on exception" requirement.
  * "partial" maps to ``AuditEvent.result="failure"`` (the closest of the
    three allowed values ``success|failure|denied`` — dispatch ran but not
    every target succeeded); "blocked" maps to ``result="denied"`` (the
    combined governance gate refused to let dispatch happen at all).
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ...errors import NotFoundError
from ...paths import FoundryPaths
from ...services import audit_service
from ...services.audit_service import AuditEvent
from ...services.governance import GuardResult
from ...services.writeback import ApproveDispatchResult, approve_and_dispatch
from ..auth.rbac import require_role
from .runs import get_paths

logger = logging.getLogger(__name__)

router = APIRouter()

_PATHS_DEP = Depends(get_paths)

# RBAC-FORWARD-COMPAT (RBAC-005, RBAC-901): writeback:approve_dispatch is an
# admin-class action, mirroring agent_jobs.py's launch/cancel/accept routes.
# All mutation routes in this router require owner or admin at minimum.
_RBAC_WRITEBACK = Depends(require_role("owner", "admin"))

# Same MVP target triple as approve_and_dispatch()'s own default.
_DEFAULT_TARGETS: tuple[str, ...] = ("ccdash", "meatywiki", "skillmeat")


# ---------------------------------------------------------------------------
# Request body model
# ---------------------------------------------------------------------------


class ApproveDispatchBody(BaseModel):
    """Body for POST /api/runs/{run_id}/writeback/approve.

    ``targets`` defaults to the MVP triple (``ccdash``, ``meatywiki``,
    ``skillmeat``) when omitted or ``null``.
    """

    targets: list[str] | None = None


# ---------------------------------------------------------------------------
# Response models (API-006 OpenAPI polish)
#
# These mirror ``_result_to_dict`` / ``_governance_rejected_exception``'s
# hand-built dicts field-for-field — they exist purely to document the
# response shape in ``/openapi.json`` (matching the
# ``response_model`` + ``responses={...: {"model": ...}}`` convention used by
# ``assertions.py`` for its own error-envelope routes). No behavior change:
# the route bodies below still build and return plain dicts; FastAPI
# validates/serializes them against these models at the boundary.
# ---------------------------------------------------------------------------


class ViolationOut(BaseModel):
    """JSON-serializable projection of :class:`~...services.governance.Violation`."""

    rule_id: str
    severity: str
    message: str
    detail: str = ""


class GuardResultOut(BaseModel):
    """JSON-serializable projection of :class:`~...services.governance.GuardResult`."""

    passed: bool
    exit_code: int
    violations: list[ViolationOut] = []


class ApproveDispatchResponse(BaseModel):
    """200 response body — JSON-serializable projection of
    :class:`~...services.writeback.ApproveDispatchResult` (``"success"``/
    ``"partial"`` outcomes only; ``"blocked"`` never reaches this model —
    see :class:`GovernanceRejectedResponse` below).
    """

    bundle_id: str
    verified: bool
    council_decision: str
    reviewer_notes: str
    required_fix: str | None
    guard_result: GuardResultOut
    target_status: dict[str, str]
    overall_status: Literal["success", "partial"]


class GovernanceRejectedDetail(BaseModel):
    """The ``detail`` payload of a 422/400 ``governance_rejected`` response.

    Field set is intentionally identical whether the guard itself failed or
    the combined gate blocked solely on ``council_decision ==
    "required_block"`` (a synthetic ``council_required_block`` entry is
    appended to ``violations`` in the latter case) — no new top-level fields
    are invented for that branch.
    """

    error: Literal["governance_rejected"]
    exit_code: int
    violations: list[ViolationOut]


class GovernanceRejectedResponse(BaseModel):
    """The runtime ``HTTPException`` envelope for a blocked writeback."""

    detail: GovernanceRejectedDetail


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _violations_to_dicts(guard_result: GuardResult) -> list[dict[str, Any]]:
    """Flatten :class:`Violation` objects to plain dicts (JSON-serializable)."""
    return [
        {
            "rule_id": v.rule_id,
            "severity": v.severity,
            "message": v.message,
            "detail": v.detail,
        }
        for v in guard_result.violations
    ]


def _result_to_dict(result: ApproveDispatchResult) -> dict[str, Any]:
    """Flatten :class:`ApproveDispatchResult` into a JSON-serializable dict."""
    return {
        "bundle_id": result.bundle_id,
        "verified": result.verified,
        "council_decision": result.council_decision,
        "reviewer_notes": result.reviewer_notes,
        "required_fix": result.required_fix,
        "guard_result": {
            "passed": result.guard_result.passed,
            "exit_code": result.guard_result.exit_code,
            "violations": _violations_to_dicts(result.guard_result),
        },
        "target_status": dict(result.target_status),
        "overall_status": result.overall_status,
    }


def _governance_rejected_exception(result: ApproveDispatchResult) -> HTTPException:
    """Build the ``governance_rejected`` HTTPException for a blocked result.

    Mirrors ``agent_jobs.py::launch_job``'s 422-if-exit_code-3-else-400 rule
    when the guard itself failed. When the guard *passed* but the combined
    gate still blocked (council_decision == "required_block"), there is no
    failing exit_code to key off of — use the governance-block status class
    (422) and append a synthetic violation so the response shape stays
    consistent (no new top-level fields).
    """
    guard_result = result.guard_result
    violations = _violations_to_dicts(guard_result)

    if not guard_result.passed:
        status_code = 422 if guard_result.exit_code == 3 else 400
    else:
        # Guard passed; the block came solely from the council decision.
        status_code = 422
        violations.append(
            {
                "rule_id": "council_required_block",
                "severity": "block",
                "message": result.required_fix or result.reviewer_notes or "Council required a block.",
                "detail": "",
            }
        )

    return HTTPException(
        status_code=status_code,
        detail={
            "error": "governance_rejected",
            "exit_code": guard_result.exit_code,
            "violations": violations,
        },
    )


# ---------------------------------------------------------------------------
# API-001..004: POST /runs/{run_id}/writeback/approve
# ---------------------------------------------------------------------------


@router.post(
    "/runs/{run_id}/writeback/approve",
    summary="Approve a run's evidence bundle and dispatch to writeback targets",
    response_model=ApproveDispatchResponse,
    responses={
        400: {
            "model": GovernanceRejectedResponse,
            "description": "Governance guard requires human review (exit_code 7).",
        },
        404: {"description": "run not found"},
        422: {
            "model": GovernanceRejectedResponse,
            "description": (
                "Governance guard blocked (exit_code 3), or the guard passed but "
                "council_decision == \"required_block\" (synthetic "
                "council_required_block violation appended)."
            ),
        },
    },
)
def approve_dispatch(
    run_id: str,
    body: ApproveDispatchBody,
    request: Request,
    paths: FoundryPaths = _PATHS_DEP,
    _rbac: None = _RBAC_WRITEBACK,
) -> dict[str, Any]:
    """Approve *run_id*'s evidence bundle and dispatch it to writeback targets.

    Wraps :func:`~research_foundry.services.writeback.approve_and_dispatch`
    (Phase 1, locked contract — not modified here). See the module docstring
    above for the full governance-mapping and audit-outcome-class rules.

    Returns 200 with the full result on ``"success"``/``"partial"``
    (``"partial"`` is NOT an error — some targets failed but the run WAS
    approved and dispatch WAS attempted). Returns 422/400 with a
    ``governance_rejected`` envelope on ``"blocked"``. Returns 404 if
    *run_id* does not exist. Returns 500 on any other unexpected exception.
    """
    identity = getattr(request.state, "identity", None)
    actor_user_id = identity.user_id if identity is not None else None
    # API-004: thread the resolved identity into approve_and_dispatch's
    # approver_identity so ORC-004's approved_by field is populated
    # end-to-end from a real caller. None is valid (loopback/no-auth mode).
    approver_identity = identity.user_id if identity is not None else None

    targets = tuple(body.targets) if body.targets else _DEFAULT_TARGETS

    try:
        result = approve_and_dispatch(
            run_id,
            approver_identity=approver_identity,
            targets=targets,
            paths=paths,
        )
    except NotFoundError as exc:
        audit_service.record_event(
            paths,
            AuditEvent(
                mutation_type="writeback",
                action="approve_and_dispatch",
                target_ref=run_id,
                actor_user_id=actor_user_id,
                result="failure",
                error_detail=str(exc),
            ),
        )
        raise HTTPException(status_code=404, detail="run not found") from exc
    except Exception as exc:  # noqa: BLE001 — must audit before propagating
        logger.error("approve_and_dispatch failed for run %s: %s", run_id, exc)
        audit_service.record_event(
            paths,
            AuditEvent(
                mutation_type="writeback",
                action="approve_and_dispatch",
                target_ref=run_id,
                actor_user_id=actor_user_id,
                result="failure",
                error_detail=str(exc),
            ),
        )
        raise HTTPException(status_code=500, detail="approve_and_dispatch failed") from exc

    # API-003: exactly one audit row per invocation — this is the
    # success/partial/blocked branch (the exception branches above already
    # recorded and returned/raised their own single row).
    if result.overall_status == "success":
        audit_result = "success"
    elif result.overall_status == "partial":
        audit_result = "failure"
    else:  # "blocked"
        audit_result = "denied"

    audit_service.record_event(
        paths,
        AuditEvent(
            mutation_type="writeback",
            action="approve_and_dispatch",
            target_ref=run_id,
            actor_user_id=actor_user_id,
            result=audit_result,
        ),
    )

    # API-002: governance_rejected mapping for the blocked case.
    if result.overall_status == "blocked":
        raise _governance_rejected_exception(result)

    return _result_to_dict(result)


__all__ = ["router"]
