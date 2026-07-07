"""Agent Jobs API router — P4.4 (public-multiuser-release Phase 4).

All agent-job lifecycle endpoints live here.  Auth/RBAC is deferred to P5
(D12); ``workspace_id`` and ``created_by`` are accepted as nullable fields
without enforcement.

Route table (registered under /api prefix in app.py):

  POST   /agent-jobs                         launch a new agent job (guard-gated)
  GET    /agent-jobs/{job_id}                job detail (status + metadata)
  GET    /agent-jobs/{job_id}/artifacts      staged (not-yet-accepted) artifacts
  GET    /agent-jobs/{job_id}/events         SSE event stream (server-sent events)
  POST   /agent-jobs/{job_id}/cancel         cancel job + credential cleanup
  POST   /agent-jobs/{job_id}/accept         SOLE WRITE PATH: promote staged artifacts

Security invariants:
  * guard_check() is called before any subprocess is spawned (API-4.1).
  * Every SSE event payload passes governance.redact_payload() before serialisation
    (API-4.3 CRITICAL invariant).
  * accept() is the ONLY write path from agent-job staging to catalog/report (API-4.5).
  * Indistinguishable 404: malformed IDs and missing jobs return identical 404
    (no information leakage), mirroring the discipline in reports.py landmine #4.

SSE pattern note (OQ-A resolution):
  No existing SSE or WebSocket patterns were found in this codebase
  (checked api/routers/*.py and api/app.py).  This router introduces the first
  SSE endpoint, implemented from scratch using FastAPI's ``StreamingResponse``
  with ``media_type="text/event-stream"`` and an async generator that polls
  the persisted ``events.jsonl`` file.  Reuse vs. new-endpoint: new endpoint
  chosen because no existing pattern exists to reuse.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...errors import NotFoundError
from ...paths import FoundryPaths
from ...services.agent_job_schemas import AgentJobStatus
from ...services.agent_job_service import AgentJobService, InProcessProviderError
from ...services.governance import GuardContext, guard_check, redact_payload
from .runs import get_paths

logger = logging.getLogger(__name__)

router = APIRouter()

_PATHS_DEP = Depends(get_paths)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _not_found(job_id: str, detail: str = "agent job not found") -> HTTPException:
    """Return a 404 that does NOT leak whether the id is malformed vs. absent.

    Indistinguishable-404 discipline: both a path-traversal payload
    (ValueError from _validate_path_component) and a genuinely missing job
    (KeyError from load_job) produce the same opaque 404.
    """
    return HTTPException(status_code=404, detail=detail)


def _get_service(paths: FoundryPaths) -> AgentJobService:
    """Construct a per-request :class:`AgentJobService`."""
    return AgentJobService(paths)


def _load_job_or_404(service: AgentJobService, job_id: str) -> Any:
    """Load a job from disk; map ValueError/KeyError to indistinguishable 404."""
    try:
        return service.load_job(job_id)
    except (ValueError, KeyError):
        raise _not_found(job_id)


# ---------------------------------------------------------------------------
# Request body models
# ---------------------------------------------------------------------------


class LaunchJobBody(BaseModel):
    """Body for POST /api/agent-jobs.

    ``policy_snapshot`` is required and must contain at least
    ``allowed_tools`` and ``data_scopes`` (validated by
    :func:`~research_foundry.services.agent_job_schemas.validate_agent_job`).
    ``workspace_id`` and ``created_by`` are nullable (D12 — auth in P5).
    ``credential_b64`` is the base64-encoded raw credential bytes forwarded to
    the spawned subprocess; omit (or pass ``null``) to use empty bytes.
    """

    provider: str
    model_profile: str
    request_kind: str
    policy_snapshot: dict[str, Any]
    project_id: str = "default"
    workspace_id: str | None = None
    created_by: str | None = None
    input_claim_ids: list[str] = []
    input_source_ids: list[str] = []
    input_report_id: str | None = None
    budget_usd: float | None = None
    max_runtime_minutes: int | None = None
    credential_b64: str | None = None  # base64-encoded credential bytes (optional)


class AcceptJobBody(BaseModel):
    """Body for POST /api/agent-jobs/{job_id}/accept."""

    accepted_by: str | None = None
    notes: str | None = None


# ---------------------------------------------------------------------------
# API-4.1: POST /agent-jobs — launch endpoint
# ---------------------------------------------------------------------------


@router.post("/agent-jobs", summary="Launch a new agent job", status_code=201)
def launch_job(
    body: LaunchJobBody,
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Launch a new agent job, gated by ``governance.guard_check()``.

    **Guard gate (API-4.1 invariant):** ``guard_check()`` is called *before*
    any subprocess is spawned.  A rejected guard (exit_code 3 or 7) returns
    422/400 immediately and guarantees no subprocess is spawned.

    Returns the created :class:`~research_foundry.services.agent_job_schemas.AgentJob`
    record on success (HTTP 201).
    """
    # Build governance context from the policy_snapshot.
    ps = body.policy_snapshot
    ctx = GuardContext(
        profile=str(ps.get("key_profile") or "personal"),
        sensitivity=ps.get("sensitivity"),
        model_provider=body.provider,
        writeback_targets=tuple(ps.get("writeback_targets") or []),
        source_sensitivities=tuple(ps.get("source_sensitivities") or []),
        intent_key_profile_allowed=ps.get("intent_key_profile_allowed"),
    )

    # Guard gate — MUST happen before create_job / spawn_job.
    guard_result = guard_check(ctx, paths=paths)
    if not guard_result.passed:
        # Map exit_code → HTTP status: 3 (GOVERNANCE block) → 422; 7 (HUMAN_REVIEW) → 400.
        status_code = 422 if guard_result.exit_code == 3 else 400
        raise HTTPException(
            status_code=status_code,
            detail={
                "error": "governance_rejected",
                "exit_code": guard_result.exit_code,
                "violations": [
                    {
                        "rule_id": v.rule_id,
                        "severity": v.severity,
                        "message": v.message,
                        "detail": v.detail,
                    }
                    for v in guard_result.violations
                ],
            },
        )

    service = _get_service(paths)

    # Create and persist the job record.
    try:
        job = service.create_job(
            provider=body.provider,
            model_profile=body.model_profile,
            request_kind=body.request_kind,
            policy_snapshot=body.policy_snapshot,
            project_id=body.project_id,
            workspace_id=body.workspace_id,
            created_by=body.created_by,
            input_claim_ids=body.input_claim_ids,
            input_source_ids=body.input_source_ids,
            input_report_id=body.input_report_id,
            budget_usd=body.budget_usd,
            max_runtime_minutes=body.max_runtime_minutes,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to create agent job: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create agent job record") from exc

    # Decode credentials (empty bytes when not provided — P5 will enforce auth).
    credential_bytes: bytes = b""
    if body.credential_b64:
        try:
            credential_bytes = base64.b64decode(body.credential_b64)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=422, detail=f"Invalid credential_b64: {exc}"
            ) from exc

    # Spawn subprocess (only if not an in-process provider).
    try:
        service.spawn_job(job, credential_bytes)
    except InProcessProviderError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Provider '{body.provider}' is an in-process adapter and cannot be spawned via this endpoint.",
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("Spawn failed for job %s: %s", job.agent_job_id, exc)
        raise HTTPException(status_code=500, detail="Failed to spawn agent job subprocess") from exc

    # Redact before returning — defense-in-depth: the disk write via
    # _safe_write_json is already redacted, but the API response must also
    # be clean in case policy_snapshot carries a secret (Codex R2 NEW-B).
    return redact_payload(job.to_dict(), config=service._config)


# ---------------------------------------------------------------------------
# API-4.2: GET /agent-jobs/{job_id} + GET /agent-jobs/{job_id}/artifacts
# ---------------------------------------------------------------------------


@router.get("/agent-jobs/{job_id}", summary="Get agent job detail")
def get_job(
    job_id: str,
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Return status and metadata for *job_id*.

    Returns the same indistinguishable 404 for malformed IDs and missing jobs
    (no information leakage about whether the ID format is wrong vs. not found).
    """
    service = _get_service(paths)
    job = _load_job_or_404(service, job_id)
    return job.to_dict()


@router.get("/agent-jobs/{job_id}/artifacts", summary="List staged artifacts for a job")
def list_artifacts(
    job_id: str,
    paths: FoundryPaths = _PATHS_DEP,
) -> list[dict[str, Any]]:
    """Return staged (not-yet-accepted) artifacts for *job_id*.

    Distinct from accepted items: only artifacts with ``accepted == False`` are
    returned.  Returns the same indistinguishable 404 for malformed IDs and
    missing jobs (no information leakage).
    """
    service = _get_service(paths)
    # Verify job exists first (404 gate).
    _load_job_or_404(service, job_id)
    try:
        return service.list_staged_artifacts(job_id)
    except (ValueError, KeyError):
        raise _not_found(job_id)


# ---------------------------------------------------------------------------
# API-4.3: GET /agent-jobs/{job_id}/events — SSE event stream
# ---------------------------------------------------------------------------


async def _sse_event_generator(
    job_id: str,
    service: AgentJobService,
    paths: FoundryPaths,
) -> Any:
    """Async generator yielding SSE-formatted, redacted event lines.

    Security invariant: every event payload is passed through
    :func:`~research_foundry.services.governance.redact_payload` BEFORE
    serialisation.  This is the authoritative redaction point (P4.2 invariant).

    Streaming behaviour:
    - Streams persisted events from ``events.jsonl`` in order.
    - If the job is still running, polls for new events (1 s interval, max 300 s).
    - Once the job reaches a terminal state (completed/failed/canceled/accepted),
      flushes remaining events and closes the stream.
    """
    _TERMINAL = {
        AgentJobStatus.completed,
        AgentJobStatus.failed,
        AgentJobStatus.canceled,
        AgentJobStatus.accepted,
    }
    events_file = paths.agent_job_dir(job_id) / "events.jsonl"
    yielded_count = 0
    max_polls = 300  # stop after 5 minutes of polling
    poll_count = 0

    # Resolve governance config once before the hot loop so governance.yaml
    # secret_patterns are applied on every event without per-event I/O.
    cfg = service.config

    while poll_count < max_polls:
        # Read any new lines from the JSONL file.
        if events_file.exists():
            try:
                with events_file.open("r", encoding="utf-8") as fh:
                    all_lines = fh.readlines()
                for raw_line in all_lines[yielded_count:]:
                    stripped = raw_line.strip()
                    if not stripped:
                        continue
                    try:
                        event = json.loads(stripped)
                        # CRITICAL SECURITY INVARIANT: redact before sending.
                        # Pass resolved config so custom secret_patterns apply.
                        redacted = redact_payload(event, config=cfg)
                        yield f"data: {json.dumps(redacted)}\n\n"
                    except json.JSONDecodeError as exc:
                        logger.warning("Skipping malformed event in SSE stream: %s", exc)
                    finally:
                        yielded_count += 1
            except OSError as exc:
                logger.warning("Could not read events file for %s: %s", job_id, exc)

        # Check whether job has reached a terminal state.
        try:
            job = service.load_job(job_id)
            if job.status in _TERMINAL:
                break
        except (ValueError, KeyError):
            break  # Job disappeared; close stream.

        await asyncio.sleep(1.0)
        poll_count += 1


@router.get("/agent-jobs/{job_id}/events", summary="Stream agent job events (SSE)")
async def stream_events(
    job_id: str,
    paths: FoundryPaths = _PATHS_DEP,
) -> StreamingResponse:
    """Deliver stage-transition events for *job_id* as a Server-Sent Events stream.

    **Security invariant (API-4.3):** every event payload is passed through
    :func:`~research_foundry.services.governance.redact_payload` server-side
    before being sent to the client.  Credentials and secrets are never echoed.

    Uses FastAPI's :class:`~fastapi.responses.StreamingResponse` with
    ``media_type="text/event-stream"``.  Events follow the SSE wire format::

        data: {json}\\n\\n

    The stream closes when the job reaches a terminal state or the poll
    limit (300 s) is reached.
    """
    service = _get_service(paths)
    # Verify job exists before opening the stream (404 gate).
    _load_job_or_404(service, job_id)

    return StreamingResponse(
        _sse_event_generator(job_id, service, paths),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# API-4.4: POST /agent-jobs/{job_id}/cancel
# ---------------------------------------------------------------------------


@router.post("/agent-jobs/{job_id}/cancel", summary="Cancel an agent job")
def cancel_job(
    job_id: str,
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Cancel *job_id*, guaranteeing credential temp-file cleanup.

    Calls :meth:`~research_foundry.services.agent_job_service.AgentJobService.terminate_job`
    then :meth:`~research_foundry.services.agent_job_service.AgentJobService.cleanup_job`,
    which reuses the SEC-2.2 crash-safe cleanup path (credential temp files are
    always unlinked regardless of child exit status).

    After cancel, zero staged artifacts are promoted (cancel before accept means
    nothing was accepted — the existing behaviour is preserved).

    Returns 200 on success, 404 if job not found.
    """
    service = _get_service(paths)
    # 404 gate.
    _load_job_or_404(service, job_id)

    service.terminate_job(job_id)
    service.cleanup_job(job_id)

    # Update on-disk status to canceled.
    try:
        service.update_job_status(job_id, AgentJobStatus.canceled)
    except (KeyError, ValueError) as exc:
        logger.warning("Could not update status for canceled job %s: %s", job_id, exc)

    return {"agent_job_id": job_id, "status": "canceled"}


# ---------------------------------------------------------------------------
# API-4.5: POST /agent-jobs/{job_id}/accept — SOLE WRITE PATH
# ---------------------------------------------------------------------------


@router.post("/agent-jobs/{job_id}/accept", summary="Accept agent job output")
def accept_job(
    job_id: str,
    body: AcceptJobBody,
    paths: FoundryPaths = _PATHS_DEP,
) -> dict[str, Any]:
    """Promote staged artifacts from *job_id* into the catalog or report store.

    **This is the SOLE WRITE PATH from agent-job staging into catalog/report.**
    No other route in this router writes directly from agent-job context.

    Gate: only jobs in ``waiting_for_approval`` or ``completed`` state may be
    accepted.  Jobs in other terminal states (``failed``, ``canceled``) return 422.

    Accepted items carry a resolvable ``created_by_agent_job_id`` field pointing
    back to this job.

    Returns 200 with a summary of what was accepted.
    """
    service = _get_service(paths)
    _load_job_or_404(service, job_id)

    try:
        result = service.accept_job(
            job_id,
            accepted_by=body.accepted_by,
            notes=body.notes,
        )
    except KeyError:
        raise _not_found(job_id)
    except ValueError as exc:
        # Job is in a non-acceptable state.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise _not_found(job_id) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("accept_job failed for %s: %s", job_id, exc)
        raise HTTPException(status_code=500, detail="Acceptance failed") from exc

    return result


__all__ = ["router"]
