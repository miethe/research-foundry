"""Workspace scope enforcement (advisory mode) — public-multiuser-release P5.3 WKSP-301.

In WKSP-301 this module is **purely advisory**: :func:`require_workspace_scope`
always allows the request through but emits a structured JSON log event at
``WARNING`` level when a workspace_id mismatch or null workspace_id is
detected.  This telemetry drives the dry-run evaluation (WKSP-301) and informs
backfill planning (WKSP-302/303) before enforcement is enabled (WKSP-304).

Enforcement flag (WKSP-304)
---------------------------
The enforcement gate lives in ``config.py``
(``workspace_isolation_enforcement`` flag) and is wired in WKSP-304.  Until
that flag is active this module is advisory-only regardless of what the record
or identity carries.

Design — mirrors the ``require_role`` idiom (P5.2)
--------------------------------------------------
:func:`require_workspace_scope` mirrors the OQ-A pattern from P5.2's
``require_role``: it is a callable that works in *both* the HTTP router layer
(via ``Depends``) and the service layer (direct call with
``identity=None`` for single-operator-trust mode).  Advisory-only today;
enforcement flag added in WKSP-304.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any

from .provider import AuthIdentity

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result value-object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkspaceScopeResult:
    """Result of a workspace scope check.

    Attributes
    ----------
    allowed:
        Always ``True`` in WKSP-301 advisory mode.  WKSP-304 will flip this
        to ``False`` when enforcement is enabled and a mismatch is detected.
    reason:
        Short token describing the outcome:
        ``"single_operator_trust"`` — identity is ``None``, no check possible;
        ``"workspace_match"``       — identity and record share the same workspace;
        ``"advisory_mode"``         — mismatch or null detected; advisory logged.
    """

    allowed: bool
    reason: str


# ---------------------------------------------------------------------------
# Advisory predicate
# ---------------------------------------------------------------------------


def require_workspace_scope(
    identity: AuthIdentity | None,
    record: dict[str, Any] | object,
    *,
    record_type: str = "unknown",
    record_id: str | None = None,
) -> WorkspaceScopeResult:
    """Advisory-mode workspace scope predicate.

    Always returns ``WorkspaceScopeResult(allowed=True, ...)``.  Emits a
    structured JSON advisory log event at ``WARNING`` level when:

    * ``identity`` is not ``None`` **and** the record's ``workspace_id`` is
      ``None`` / absent (pre-migration record lacking a workspace_id field), OR
    * ``identity`` is not ``None`` **and** ``record.workspace_id`` does not
      match ``identity.workspace_id`` (cross-workspace access).

    When ``identity`` is ``None`` (single-operator-trust mode — no auth
    middleware is configured), the advisory is suppressed: there is no
    workspace context to compare against, so emitting a log for every record
    read would produce meaningless noise.

    Parameters
    ----------
    identity:
        Resolved caller identity (from ``request.state.identity`` on the HTTP
        path) or ``None`` for CLI / single-operator-trust callers.
    record:
        The record being returned to the caller.  ``workspace_id`` is resolved
        via ``record.get("workspace_id")`` (dict) or
        ``getattr(record, "workspace_id", None)`` (object).
    record_type:
        Human-readable record type label (e.g. ``"catalog_item"``,
        ``"draft"``).  Included in the advisory log event.
    record_id:
        Stable identifier for the record.  When not supplied, derived from
        common field names (``catalog_item_id``, ``report_draft_id``, ``id``).

    Returns
    -------
    WorkspaceScopeResult
        Always ``allowed=True`` in WKSP-301 advisory mode.
    """
    if identity is None:
        # Single-operator trust mode — no workspace context to compare.
        return WorkspaceScopeResult(allowed=True, reason="single_operator_trust")

    # Resolve workspace_id + record_id from the record.
    if isinstance(record, dict):
        rec_workspace_id: str | None = record.get("workspace_id")
        if record_id is None:
            record_id = (
                record.get("catalog_item_id")
                or record.get("report_draft_id")
                or str(record.get("id", "unknown"))
            )
    else:
        rec_workspace_id = getattr(record, "workspace_id", None)
        if record_id is None:
            record_id = str(getattr(record, "id", "unknown"))

    # Exact match — no advisory needed.
    if rec_workspace_id is not None and rec_workspace_id == identity.workspace_id:
        return WorkspaceScopeResult(allowed=True, reason="workspace_match")

    # Mismatch (or null workspace_id on the record) — emit the advisory log.
    trace_id = str(uuid.uuid4())
    _logger.warning(
        json.dumps(
            {
                "event": "workspace_scope_advisory_mismatch",
                "trace_id": trace_id,
                "record_type": record_type,
                "record_id": record_id,
                "record_workspace_id": rec_workspace_id,
                "identity_workspace_id": identity.workspace_id,
            }
        )
    )
    return WorkspaceScopeResult(allowed=True, reason="advisory_mode")


__all__ = ["WorkspaceScopeResult", "require_workspace_scope"]
