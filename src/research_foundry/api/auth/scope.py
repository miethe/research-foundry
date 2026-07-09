"""Workspace scope enforcement (advisory mode) — public-multiuser-release P5.3 WKSP-301.

In WKSP-301 this module was **purely advisory**: :func:`require_workspace_scope`
always allowed the request through but emitted a structured JSON log event at
``WARNING`` level when a workspace_id mismatch or null workspace_id was
detected.  This telemetry drove the dry-run evaluation (WKSP-301) and informed
backfill planning (WKSP-302/303) ahead of enforcement (WKSP-304).

Enforcement flag (WKSP-304 Phase 4 — TASK-4.1)
-----------------------------------------------
:func:`require_workspace_scope` now accepts an optional
``resolve_enforcement`` callable.  When the caller passes one AND it
resolves truthy, a workspace_id mismatch (including a ``None``
``record.workspace_id``) is **denied** (``allowed=False``) instead of
merely logged.  When no resolver is passed (the default — pre-Phase-4
callers are unaffected) or the resolver resolves falsy, behaviour is
byte-for-byte identical to WKSP-301 advisory mode.

**D3 ordering invariant (Critical, no partial credit):** the
``identity is None`` (single-operator-trust) check is the literal first
statement in the function body.  It returns before ``resolve_enforcement``
is read or called at all — single-operator-trust callers never pay for, and
are never affected by, the enforcement-flag lookup. See
``test_require_workspace_scope_identity_none_never_resolves_enforcement_flag``
in ``tests/unit/test_workspace_migration_service.py`` for the ordering proof.

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
from typing import Any, Callable

from ...config import FoundryConfig
from ...paths import FoundryPaths
from .provider import AuthIdentity

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared enforcement-flag resolver (WKSP-304 Phase 4, TASK-4.2 consolidation)
# ---------------------------------------------------------------------------


def resolve_workspace_isolation_active(paths: FoundryPaths) -> bool:
    """Resolve whether WKSP-304 workspace isolation is actively enforced.

    Single shared implementation of the ``_isolation_active`` idiom that
    Phase 3 (deliberately, per-service, single-owner-phase) duplicated
    identically into ``catalog_service.py``, ``builder_service.py``, and
    ``AgentJobService`` (as a bound method). Those call sites now delegate
    here — this is a pure refactor with no behaviour change: same
    ``config.auth_provider()`` lookup (degrading to ``"none"`` on a
    ``ValueError``, since a misconfigured/incomplete provider block is not
    this function's concern — the app itself refuses to start in that case),
    then the same
    :meth:`~research_foundry.config.FoundryConfig.resolve_workspace_isolation_enforced`
    truth-table lookup (Phase 1, TASK-1.2) that this function never
    reimplements.
    """

    config = FoundryConfig(paths=paths)
    try:
        provider = config.auth_provider()
    except ValueError:
        provider = "none"
    return config.resolve_workspace_isolation_enforced(provider, config.viewer_bind_host())


# ---------------------------------------------------------------------------
# Result value-object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkspaceScopeResult:
    """Result of a workspace scope check.

    Attributes
    ----------
    allowed:
        ``True`` unless a ``resolve_enforcement`` resolver is supplied AND
        resolves truthy AND the record's ``workspace_id`` mismatches (or is
        ``None``) — in which case ``False`` (WKSP-304 Phase 4 enforcing mode).
    reason:
        Short token describing the outcome:
        ``"single_operator_trust"``   — identity is ``None``, no check possible;
        ``"workspace_match"``         — identity and record share the same workspace;
        ``"advisory_mode"``           — mismatch or null detected, not enforcing; advisory logged;
        ``"workspace_mismatch_denied"`` — mismatch or null detected, enforcing mode.
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
    resolve_enforcement: Callable[[], bool] | None = None,
) -> WorkspaceScopeResult:
    """Workspace scope predicate — advisory by default, enforcing when armed.

    When ``identity`` is ``None`` (single-operator-trust mode — no auth
    middleware is configured), this function returns immediately with
    ``allowed=True, reason="single_operator_trust"``.  This is the literal
    first statement in the function body (WKSP-304 D3 — Critical, no partial
    credit): ``resolve_enforcement`` is never read or invoked on this path,
    so single-operator-trust callers never pay for, and can never be affected
    by, the enforcement-flag lookup.

    When ``identity`` is not ``None``, ``resolve_enforcement`` (if supplied)
    is called exactly once to resolve whether WKSP-304 workspace isolation is
    currently enforcing:

    * **Enforcing** (``resolve_enforcement`` supplied and resolves truthy):
      a ``record.workspace_id`` mismatch — including ``None`` / absent,
      which is treated as a mismatch and never defaulted to allowed — denies
      the request (``allowed=False, reason="workspace_mismatch_denied"``).
      An exact match still allows (``reason="workspace_match"``).
    * **Advisory** (no resolver passed, or the resolver resolves falsy —
      the WKSP-301 default, unchanged pre-Phase-4 behaviour): a mismatch or
      null ``workspace_id`` emits a structured JSON advisory log event at
      ``WARNING`` level and still returns ``allowed=True,
      reason="advisory_mode"``.  An exact match returns
      ``allowed=True, reason="workspace_match"`` with no log.

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
    resolve_enforcement:
        Optional zero-arg callable resolving whether WKSP-304 workspace
        isolation enforcement is currently active (e.g. a service's
        ``_isolation_active`` helper).  Defaults to ``None``, which resolves
        to advisory-only — existing callers that do not pass this parameter
        keep byte-for-byte WKSP-301 behaviour until they are updated
        (WKSP-304 TASK-4.2/4.3) to pass a resolver.

    Returns
    -------
    WorkspaceScopeResult
    """
    if identity is None:
        # Single-operator trust mode — no workspace context to compare.
        # D3: returns before `resolve_enforcement` is ever read/called.
        return WorkspaceScopeResult(allowed=True, reason="single_operator_trust")

    # WKSP-304 TASK-4.1: the enforcement flag is resolved here — only ever
    # reached once the identity=None short-circuit above has already
    # returned. Absent a resolver, this defaults to advisory-only (False).
    enforcing = resolve_enforcement() if resolve_enforcement is not None else False

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

    # Exact match — allowed in either mode, no log.
    if rec_workspace_id is not None and rec_workspace_id == identity.workspace_id:
        return WorkspaceScopeResult(allowed=True, reason="workspace_match")

    # Mismatch (or null workspace_id on the record).
    if enforcing:
        # WKSP-304 TASK-4.1: enforcing mode denies. A null workspace_id is
        # treated as a mismatch — never defaulted to allowed (AC-3 / D3).
        return WorkspaceScopeResult(allowed=False, reason="workspace_mismatch_denied")

    # Advisory mode — unchanged from pre-Phase-4 WKSP-301 behaviour: log and allow.
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


__all__ = [
    "WorkspaceScopeResult",
    "require_workspace_scope",
    "resolve_workspace_isolation_active",
]
