"""Audit service for Research Foundry (public-multiuser-release Phase 5, AUDIT-001).

Provides an append-only audit log stored in the durable ``.rf_state/rbac.db``
database (same store as the RBAC membership tables).  Every governed mutation --
catalog import, report edit, agent-job launch (reserved, N/A until P4), artifact
ingest, publish-preview, and writeback -- produces a queryable row capturing who
did what, from which source, and under which policy snapshot.

FAIL-OPEN INVARIANT
-------------------
``record_event`` is the sole write entrypoint.  It wraps its SQLite write in a
broad ``try/except`` that NEVER raises outward.  On failure it emits a
structured ``logging.ERROR`` (never a silent ``pass``) and optionally an OTel
span with ``status=ERROR``.  The caller is therefore safe to call this function
after its own mutation commit without risking a rollback or a changed HTTP
status -- a lost audit row is loud but non-blocking.

This is distinct from RBAC's fail-closed contract (P5.2): authorization gates
are evaluated *before* a mutation and must deny the request on any unresolved
identity.  Fail-open applies only to the audit side-channel; fail-closed applies
only to the authorization gate.  Never conflate the two.

APPEND-ONLY CONTRACT
--------------------
The ``audit_event`` table has no UPDATE or DELETE paths.  Rows are immutable.
Do not add UPDATE/DELETE helpers to this module.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from research_foundry.paths import FoundryPaths
from research_foundry.services.rbac_store import _connect, _ensure_schema

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mutation-type taxonomy (all 6 reserved; 5 wired in P5.5)
# ---------------------------------------------------------------------------

MUTATION_TYPES: frozenset[str] = frozenset(
    {
        "catalog_mutation",
        "report_edit",
        "agent_job_launched",  # Reserved -- N/A until P4 ships agent_jobs.py
        "artifact_accepted",
        "publish_preview",
        "writeback",
    }
)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class AuditEvent:
    """Immutable descriptor for a single governed mutation event.

    Required fields (``mutation_type``, ``action``, ``target_ref``) must always
    be present.  All other fields are optional/nullable and match the
    ``audit_event`` column set exactly.

    ``policy_snapshot`` is serialised to JSON on write; pass a plain ``dict``.
    """

    mutation_type: str  # must be one of MUTATION_TYPES
    action: str         # e.g. import_run, create_draft, delete_draft, ingest_source
    target_ref: str     # run_id / report_draft_id / source_card_id / etc.

    actor_user_id: Optional[str] = None
    actor_workspace_id: Optional[str] = None
    source_ref: Optional[str] = None
    policy_snapshot: Optional[dict[str, Any]] = None
    result: str = "success"          # success | failure | denied
    error_detail: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Secret redaction helper
# ---------------------------------------------------------------------------


def _redact_error_detail(text: Optional[str]) -> Optional[str]:
    """Return ``text`` with any detected secrets replaced by a placeholder.

    Uses ``governance.scan_secrets`` when available.  Falls back to the
    raw text (with a WARNING) if governance is not importable -- this keeps
    the fail-open write path free from import-chain failures while ensuring
    that any redaction gap is explicitly logged.
    """
    if text is None:
        return None
    try:
        from research_foundry.services.governance import _redact, scan_secrets  # type: ignore[attr-defined]

        hits = scan_secrets(text)
        if not hits:
            return text
        result = text
        for secret in hits:
            result = result.replace(secret, _redact(secret))
        return result
    except Exception as exc:  # pragma: no cover -- governance import failure
        log.warning(
            "audit_service: governance redaction unavailable -- storing error_detail as-is",
            extra={"redaction_error": str(exc)},
        )
        return text


# ---------------------------------------------------------------------------
# Write entrypoint -- fail-open, never raises
# ---------------------------------------------------------------------------


def record_event(paths: FoundryPaths, event: AuditEvent) -> Optional[str]:
    """Record a governed mutation event.  **Fail-open -- never raises.**

    Generates a UUID4 ``audit_event_id`` and an ISO-8601 UTC ``created_at``
    timestamp, redacts ``error_detail`` through governance secret-scan, then
    inserts a row into ``audit_event``.

    Returns the ``audit_event_id`` string on success, or ``None`` on any
    failure (the failure is logged at ERROR level and, if OTel is available,
    reported as an error span).

    This function must be called after the primary mutations own commit,
    never inside the same transaction -- that is what makes the fail-open
    guarantee real rather than aspirational.
    """
    try:
        return _record_event_inner(paths, event)
    except Exception as exc:
        _emit_record_error(exc, event)
        return None


def _record_event_inner(paths: FoundryPaths, event: AuditEvent) -> str:
    """Internal implementation -- called inside record_event try/except."""
    audit_event_id = str(uuid.uuid4())
    created_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    policy_json = (
        json.dumps(event.policy_snapshot) if event.policy_snapshot is not None else None
    )
    redacted_detail = _redact_error_detail(event.error_detail)

    conn = _connect(paths)
    try:
        _ensure_schema(conn)
        conn.execute(
            (
                "INSERT INTO audit_event ("
                "    audit_event_id, created_at, mutation_type, action, target_ref,"
                "    actor_user_id, actor_workspace_id, source_ref, policy_snapshot,"
                "    result, error_detail, trace_id, span_id"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            (
                audit_event_id,
                created_at,
                event.mutation_type,
                event.action,
                event.target_ref,
                event.actor_user_id,
                event.actor_workspace_id,
                event.source_ref,
                policy_json,
                event.result,
                redacted_detail,
                event.trace_id,
                event.span_id,
            ),
        )
    finally:
        conn.close()

    _emit_otel_record_success(audit_event_id, event)
    return audit_event_id


def _emit_record_error(exc: Exception, event: AuditEvent) -> None:
    """Log a structured ERROR and attempt an OTel error span."""
    log.error(
        "audit_service.record_event failed -- audit row dropped",
        extra={
            "mutation_type": event.mutation_type,
            "action": event.action,
            "target_ref": event.target_ref,
            "actor_user_id": event.actor_user_id,
            "actor_workspace_id": event.actor_workspace_id,
            "result": event.result,
            "error": str(exc),
        },
        exc_info=True,
    )
    # Soft-import OTel -- never require it.
    try:
        from opentelemetry import trace  # type: ignore[import]

        tracer = trace.get_tracer("research_foundry.audit_service")
        with tracer.start_as_current_span("audit_service.record_event") as span:
            span.set_status(trace.StatusCode.ERROR, str(exc))
            span.set_attribute("mutation_type", event.mutation_type)
            span.set_attribute("action", event.action)
    except Exception:  # OTel not available or span creation failed
        pass


def _emit_otel_record_success(audit_event_id: str, event: AuditEvent) -> None:
    """Emit an OTel success span if OTel is available (best-effort)."""
    try:
        from opentelemetry import trace  # type: ignore[import]

        tracer = trace.get_tracer("research_foundry.audit_service")
        with tracer.start_as_current_span("audit_service.record_event") as span:
            span.set_attribute("audit_event_id", audit_event_id)
            span.set_attribute("mutation_type", event.mutation_type)
            span.set_attribute("action", event.action)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Read entrypoints
# ---------------------------------------------------------------------------


def list_events(
    paths: FoundryPaths,
    *,
    mutation_type: Optional[str] = None,
    actor_user_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
) -> dict[str, Any]:
    """Return a cursor-paginated list of audit events.

    Results are ordered most-recent-first (descending ``created_at``).

    The ``cursor`` is the last ``audit_event_id`` seen in a previous page.
    Pass it to receive the next page.  Pass ``None`` (or omit) to start from
    the most recent event.

    Returns a dict with keys ``items``, ``next_cursor``, and ``total_hint``.
    Each item dict matches the ``audit_event`` table columns exactly.
    ``policy_snapshot`` is returned as a parsed ``dict`` (or ``None``).
    """
    conn = _connect(paths)
    try:
        _ensure_schema(conn)
        conn.row_factory = sqlite3.Row

        clauses: list[str] = []
        params: list[Any] = []

        if mutation_type is not None:
            clauses.append("mutation_type = ?")
            params.append(mutation_type)
        if actor_user_id is not None:
            clauses.append("actor_user_id = ?")
            params.append(actor_user_id)
        if workspace_id is not None:
            clauses.append("actor_workspace_id = ?")
            params.append(workspace_id)
        if since is not None:
            clauses.append("created_at >= ?")
            params.append(since)
        if until is not None:
            clauses.append("created_at <= ?")
            params.append(until)

        # Cursor pagination: find events older than (or equal to) the cursor's
        # created_at, excluding the cursor row itself.
        if cursor is not None:
            row = conn.execute(
                "SELECT created_at FROM audit_event WHERE audit_event_id = ?",
                (cursor,),
            ).fetchone()
            if row is not None:
                clauses.append(
                    "(created_at < ? OR (created_at = ? AND audit_event_id < ?))"
                )
                params.extend([row["created_at"], row["created_at"], cursor])

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        # Fetch limit+1 to detect whether a next page exists.
        rows = conn.execute(
            "SELECT * FROM audit_event "
            + where
            + " ORDER BY created_at DESC, audit_event_id DESC"
            + " LIMIT ?",
            params + [limit + 1],
        ).fetchall()

        has_more = len(rows) > limit
        page = rows[:limit]

        items = [_row_to_dict(r) for r in page]
        next_cursor = page[-1]["audit_event_id"] if has_more and page else None

        return {
            "items": items,
            "next_cursor": next_cursor,
            "total_hint": None,  # Expensive COUNT(*) omitted; use cursor pagination
        }
    finally:
        conn.close()


def get_event(paths: FoundryPaths, audit_event_id: str) -> Optional[dict[str, Any]]:
    """Return a single audit event by ID, or ``None`` if not found.

    The caller (router) is responsible for mapping ``None`` to a 404 response.
    """
    conn = _connect(paths)
    try:
        _ensure_schema(conn)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM audit_event WHERE audit_event_id = ?",
            (audit_event_id,),
        ).fetchone()
        return _row_to_dict(row) if row is not None else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Row serialisation helper
# ---------------------------------------------------------------------------


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a ``sqlite3.Row`` to a plain ``dict``.

    ``policy_snapshot`` is JSON-decoded when present.
    """
    d = dict(row)
    if d.get("policy_snapshot") is not None:
        try:
            d["policy_snapshot"] = json.loads(d["policy_snapshot"])
        except (json.JSONDecodeError, TypeError):
            pass  # Return the raw string rather than crashing
    return d
