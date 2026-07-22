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

from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.auth.scope import resolve_workspace_isolation_active
from research_foundry.paths import FoundryPaths
from research_foundry.services.rbac_store import _connect, _ensure_schema

log = logging.getLogger(__name__)


def _isolation_active(paths: FoundryPaths) -> bool:
    """Resolve whether WKSP-304 workspace isolation is actively enforced.

    Thin delegate to the single shared implementation
    (:func:`research_foundry.api.auth.scope.resolve_workspace_isolation_active`)
    that ``catalog_service.py``/``builder_service.py``/``AgentJobService``
    already use — see that module's docstring. Kept as a module-local
    wrapper only for call-site symmetry with those modules (DI-1 full-surface
    audit, Phase 4 ACT-401).
    """

    return resolve_workspace_isolation_active(paths)

# ---------------------------------------------------------------------------
# Health state dataclass (AUDIT-004)
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class AuditHealth:
    """Immutable snapshot of the audit-store health state.

    ``last_probe_at`` is ``None`` only when ``get_health_state`` is called
    before the first ``health_check`` probe has ever run (i.e., no row in
    the ``audit_health`` table yet).
    """

    healthy: bool
    last_probe_at: Optional[str]    # ISO-8601 UTC; None = never probed
    last_success_at: Optional[str]  # None if never succeeded
    error_detail: Optional[str]     # populated when healthy=False

# ---------------------------------------------------------------------------
# Mutation-type taxonomy (all 6 reserved; 5 wired in P5.5)
# ---------------------------------------------------------------------------

MUTATION_TYPES: frozenset[str] = frozenset(
    {
        "catalog_mutation",
        "report_edit",
        "agent_job_launched",  # Wired ACT-204 (multi_user identity binding only)
        "artifact_accepted",
        "publish_preview",
        "writeback",
        # Wired public-multiuser-release-activation Phase 3 (ACT-303) — admin
        # API mutations over principals, access tokens, and role assignments.
        "principal_mutation",   # service-account create/disable
        "access_token_issued",  # PAT issuance, service-account token issue/rotate
        "access_token_revoked",  # PAT revoke, service-account token revoke
        "role_change",           # workspace member role update
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
    identity: Optional[AuthIdentity] = None,
) -> dict[str, Any]:
    """Return a cursor-paginated list of audit events.

    Results are ordered most-recent-first (descending ``created_at``).

    The ``cursor`` is the last ``audit_event_id`` seen in a previous page.
    Pass it to receive the next page.  Pass ``None`` (or omit) to start from
    the most recent event.

    Returns a dict with keys ``items``, ``next_cursor``, and ``total_hint``.
    Each item dict matches the ``audit_event`` table columns exactly.
    ``policy_snapshot`` is returned as a parsed ``dict`` (or ``None``).

    ``identity`` is DI-1 full-surface audit scoping (Phase 4 ACT-401): the
    ``RBAC-006`` ``owner``/``admin`` gate on this endpoint is
    **workspace-scoped** (``AuthIdentity.roles`` is granted "within the
    workspace" — see ``api/auth/provider.py``), so without this the
    caller-supplied ``workspace_id`` filter let an owner/admin of workspace A
    read workspace B's audit trail (actor IDs, policy snapshots) simply by
    passing ``?workspace=B`` — or read *every* workspace's events at once by
    omitting the filter entirely. When ``identity`` is not ``None`` and
    isolation is actively enforced, the caller's own ``identity.workspace_id``
    always wins over any client-supplied ``workspace_id`` argument — mirrors
    the "identity overrides client input" idiom used by
    ``builder_service.create_draft``/``admin.py``'s ``_resolve_workspace_id``.
    ``identity=None`` (the default) or isolation inactive is byte-identical
    to the pre-Phase-4 behavior (FR-2 regression guarantee) — every existing
    caller that omits ``identity`` is unaffected.
    """
    effective_workspace_id = workspace_id
    if identity is not None and _isolation_active(paths):
        effective_workspace_id = identity.workspace_id
    workspace_id = effective_workspace_id

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


def get_event(
    paths: FoundryPaths,
    audit_event_id: str,
    *,
    identity: Optional[AuthIdentity] = None,
) -> Optional[dict[str, Any]]:
    """Return a single audit event by ID, or ``None`` if not found.

    The caller (router) is responsible for mapping ``None`` to a 404 response.

    ``identity`` is DI-1 full-surface audit scoping (Phase 4 ACT-401): this
    lookup previously had **no** workspace check at all, so any owner/admin
    (a workspace-scoped role — see :func:`list_events`) could read any other
    workspace's audit event by ID. When ``identity`` is not ``None`` and
    isolation is actively enforced, a row whose ``actor_workspace_id`` does
    not match ``identity.workspace_id`` is treated exactly like a missing
    event (``None``) — the same fail-closed, indistinguishable-404 contract
    every other cross-workspace read in this codebase uses (e.g.
    ``catalog_service.get_item``, ``builder_service.load_draft``).
    ``identity=None`` (the default) or isolation inactive is byte-identical
    to the pre-Phase-4 behavior.
    """
    conn = _connect(paths)
    try:
        _ensure_schema(conn)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM audit_event WHERE audit_event_id = ?",
            (audit_event_id,),
        ).fetchone()
        if row is None:
            return None
        result = _row_to_dict(row)
        if identity is not None and _isolation_active(paths):
            if result.get("actor_workspace_id") != identity.workspace_id:
                log.error(
                    json.dumps(
                        {
                            "event": "workspace_scope_enforced_denial",
                            "record_type": "audit_event",
                            "record_id": audit_event_id,
                            "record_workspace_id": result.get("actor_workspace_id"),
                            "identity_workspace_id": identity.workspace_id,
                        }
                    )
                )
                return None
        return result
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


# ---------------------------------------------------------------------------
# Audit-store health check (AUDIT-004)
# ---------------------------------------------------------------------------


def _run_probe(conn: sqlite3.Connection, probe_id: str, now: str) -> None:
    """Write-then-read round-trip probe against ``audit_event``.

    Inserts a row with the given ``probe_id``, reads it back, then deletes
    it.  Raises on any failure.  The probe row is ephemeral and is never
    surfaced through ``list_events`` or ``get_event``.

    INVARIANT: this function may be monkeypatched in tests to simulate
    a probe failure without affecting the rest of ``health_check``.
    """
    conn.execute(
        (
            "INSERT INTO audit_event ("
            "    audit_event_id, created_at, mutation_type, action, target_ref, result"
            ") VALUES (?, ?, ?, ?, ?, ?)"
        ),
        (probe_id, now, "catalog_mutation", "_health_probe", "_health_probe", "success"),
    )
    row = conn.execute(
        "SELECT audit_event_id FROM audit_event WHERE audit_event_id = ?",
        (probe_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError("health probe row not found after write — store may be read-only")
    conn.execute(
        "DELETE FROM audit_event WHERE audit_event_id = ?",
        (probe_id,),
    )


def health_check(paths: FoundryPaths) -> AuditHealth:
    """Run a write-then-read probe and persist the result in ``audit_health``.

    Returns an :class:`AuditHealth` with ``healthy=True`` on success or
    ``healthy=False`` (with ``error_detail`` populated) on any failure.

    CRITICAL INVARIANTS
    -------------------
    - NEVER calls ``record_event()`` — the probe row is ephemeral and must
      NOT appear in the audit log returned by ``list_events()``.
    - ``is_healthy_for_exposure()`` MUST NOT be called from this function
      or any mutation call-site — it is reserved for the P5.6 exposure gate.
    """
    now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    probe_id = f"_probe_{uuid.uuid4()}"

    try:
        conn = _connect(paths)
        try:
            _ensure_schema(conn)

            # Capture prior last_success_at before the probe so failure
            # reporting can preserve the last-known-good timestamp.
            prior_row = conn.execute(
                "SELECT last_success_at FROM audit_health WHERE id = 1"
            ).fetchone()
            prior_success_at: Optional[str] = prior_row["last_success_at"] if prior_row else None

            try:
                _run_probe(conn, probe_id, now)
                # Persist healthy state.
                conn.execute(
                    (
                        "INSERT OR REPLACE INTO audit_health "
                        "(id, healthy, last_probe_at, last_success_at, error_detail) "
                        "VALUES (1, 1, ?, ?, NULL)"
                    ),
                    (now, now),
                )
            except Exception as probe_exc:
                # Probe failed — persist failure state while we still hold conn.
                error_str = str(probe_exc)
                conn.execute(
                    (
                        "INSERT OR REPLACE INTO audit_health "
                        "(id, healthy, last_probe_at, last_success_at, error_detail) "
                        "VALUES (1, 0, ?, ?, ?)"
                    ),
                    (now, prior_success_at, error_str),
                )
                return AuditHealth(
                    healthy=False,
                    last_probe_at=now,
                    last_success_at=prior_success_at,
                    error_detail=error_str,
                )
        finally:
            conn.close()

        return AuditHealth(
            healthy=True,
            last_probe_at=now,
            last_success_at=now,
            error_detail=None,
        )

    except Exception as exc:
        # Connection-level or schema failure — best-effort persistence only.
        error_str = str(exc)
        try:
            _conn2 = _connect(paths)
            try:
                _ensure_schema(_conn2)
                _prior = _conn2.execute(
                    "SELECT last_success_at FROM audit_health WHERE id = 1"
                ).fetchone()
                _prior_success = _prior["last_success_at"] if _prior else None
                _conn2.execute(
                    (
                        "INSERT OR REPLACE INTO audit_health "
                        "(id, healthy, last_probe_at, last_success_at, error_detail) "
                        "VALUES (1, 0, ?, ?, ?)"
                    ),
                    (now, _prior_success, error_str),
                )
            finally:
                _conn2.close()
        except Exception:
            pass  # Best-effort — if DB is unreachable we cannot persist

        return AuditHealth(
            healthy=False,
            last_probe_at=now,
            last_success_at=None,
            error_detail=error_str,
        )


def get_health_state(paths: FoundryPaths) -> AuditHealth:
    """Return the persisted health state without running a new probe.

    Returns ``AuditHealth(healthy=True, last_probe_at=None, ...)`` when no
    probe has ever run (i.e., the ``audit_health`` row does not yet exist).
    This is the "assume healthy until proven otherwise" default.
    """
    conn = _connect(paths)
    try:
        _ensure_schema(conn)
        row = conn.execute(
            "SELECT healthy, last_probe_at, last_success_at, error_detail "
            "FROM audit_health WHERE id = 1"
        ).fetchone()
        if row is None:
            return AuditHealth(
                healthy=True,
                last_probe_at=None,
                last_success_at=None,
                error_detail=None,
            )
        return AuditHealth(
            healthy=bool(row["healthy"]),
            last_probe_at=row["last_probe_at"],
            last_success_at=row["last_success_at"],
            error_detail=row["error_detail"],
        )
    finally:
        conn.close()


def is_healthy_for_exposure(paths: FoundryPaths) -> bool:
    """Return ``True`` if the audit store is in a healthy state.

    Reads the persisted health state; does NOT run a new probe.  Has no
    side effects.

    CRITICAL: do NOT call this from ``record_event()`` or any mutation
    call-site — that would silently break the fail-open write guarantee.
    This function is reserved for the P5.6 public-exposure decision point.
    """
    return get_health_state(paths).healthy
