"""RBAC enforcement for the Research Foundry API (public-multiuser-release P5.2).

Role × Permission Capability Matrix
-------------------------------------

This matrix defines which of the five workspace roles hold which permissions.
Router-layer enforcement is via :func:`require_role` (a FastAPI ``Depends``
factory below); CLI and service-direct callers are classified separately.

Roles (from low to high privilege):

  viewer      — read-only viewing of published artifacts
  reviewer    — review and comment on drafts; no mutations
  researcher  — can create and update catalog items and report drafts
  admin       — all mutations including destructive operations and publishing
  owner       — same as admin; the workspace creator / billing contact

+--------------------+-------+-------+------------+----------+--------+
| Permission         | owner | admin | researcher | reviewer | viewer |
+====================+=======+=======+============+==========+========+
| catalog:create     |   Y   |   Y   |     Y      |    -     |   -    |
| catalog:update     |   Y   |   Y   |     Y      |    -     |   -    |
| catalog:delete     |   Y   |   Y   |     -      |    -     |   -    |
| report:create      |   Y   |   Y   |     Y      |    -     |   -    |
| report:update      |   Y   |   Y   |     Y      |    -     |   -    |
| report:publish     |   Y   |   Y   |     -      |    -     |   -    |
| run:read           |   Y   |   Y   |     Y      |    Y     |   -    |
| agent_job:launch   | (N/A) | (N/A) |   (N/A)   |  (N/A)   | (N/A)  |
+--------------------+-------+-------+------------+----------+--------+

Notes:
  - ``run:read`` gates are deferred to P5.3/P5.7; current GET routes are open.
  - ``agent_job:launch`` is forward-compat only (N/A-until-P4). See below.

CLI / service-direct mutation surface classification
----------------------------------------------------

CLI entry points bypass the HTTP router layer and therefore bypass
``require_role``.  These surfaces are classified as *single-operator-trust*
(no RBAC enforcement needed today — a single unattended operator runs them
from a trusted shell).  The concrete entry points are:

  ``rf ingest``          → ``services/source_cards.py::ingest_source``
                           / ``create_source_card``
  ``rf source-card create`` → ``services/source_cards.py::create_source_card``
                               (alias of rf ingest; same admin-only/single-operator-trust classification)
  ``rf catalog rebuild`` → ``services/catalog_service.py::import_all``
                           / ``rebuild``
  ``rf writeback``       → ``services/writeback.py::writeback``

None of these are reachable via the gated HTTP mutation routes in
``catalog.py`` or ``reports.py`` — there is no HTTP path that calls these
service functions without going through a ``require_role``-gated route
handler.  See :func:`~research_foundry.services.catalog_service.import_all`
and the companion ``test_cli_mutation_surface.py`` for verification.

Forward-compat: agent_jobs.py (RBAC-FORWARD-COMPAT, RBAC-005)
--------------------------------------------------------------

# RBAC-FORWARD-COMPAT: agent_jobs.py does not exist today (N/A-until-P4).
#
# When public-multiuser-p4-agents-v1 Phase 4 lands and agent_jobs.py is
# created, EVERY mutation route in that router MUST carry:
#
#   Depends(require_role("owner", "admin"))
#
# at minimum (``agent_job:launch`` is an admin-class action; adjust
# allowed_roles when the final permission model for P4 is agreed).
# See RBAC-005 and the route-sweep test (RBAC-901) for enforcement context.
"""

from __future__ import annotations

from typing import Callable

from fastapi import HTTPException, Request

from .provider import AuthIdentity  # noqa: F401 — re-exported as a convenience

# ---------------------------------------------------------------------------
# Capability matrix
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "owner": {
        "catalog:create",
        "catalog:update",
        "catalog:delete",
        "report:create",
        "report:update",
        "report:publish",
        "run:read",
        "agent_job:launch",  # N/A-until-P4
    },
    "admin": {
        "catalog:create",
        "catalog:update",
        "catalog:delete",
        "report:create",
        "report:update",
        "report:publish",
        "run:read",
        "agent_job:launch",  # N/A-until-P4
    },
    "researcher": {
        "catalog:create",
        "catalog:update",
        # catalog:delete NOT granted to researcher
        "report:create",
        "report:update",
        # report:publish NOT granted to researcher
        "run:read",
        # agent_job:launch NOT granted to researcher
    },
    "reviewer": {
        "run:read",
        # No mutations on catalog, reports, or runs
    },
    "viewer": set(),  # zero permissions — read-only viewer gates are in P5.3/P5.7
}


# ---------------------------------------------------------------------------
# require_role — FastAPI dependency factory
# ---------------------------------------------------------------------------


def require_role(*allowed_roles: str) -> Callable:
    """FastAPI dependency factory — checks caller's role before a mutation route.

    Parameters
    ----------
    *allowed_roles:
        Role strings that are permitted to invoke the route this dependency
        guards.  These should be drawn from ``ROLE_PERMISSIONS`` keys.

    Behavior
    --------
    * If ``request.state.identity`` is **absent** (``auth.provider=none`` /
      no middleware set it): **allow** unconditionally — single-operator-trust
      mode.  The absent-identity semantics are documented in
      ``api/auth/provider.py``.  Do NOT raise here; that would break the
      default single-operator deployment mode.

    * If ``identity`` is present but ``identity.roles`` has **no intersection**
      with ``allowed_roles``: raise ``HTTPException(status_code=403, detail="Insufficient role")``.

    * An **empty** ``roles`` tuple (``roles=()``) is treated as zero
      permissions → 403.  This is not an error; it is a valid state for an
      identity that has not been assigned any role.

    * If ``identity`` is present and **has at least one matching role**: allow.

    Internal marker
    ---------------
    The returned inner function is marked ``_is_require_role = True`` so the
    RBAC-901 route-sweep test can detect it via ``route.dependant.dependencies``
    without relying on fragile name-based string matching.
    """

    def _check_role(request: Request) -> None:  # FastAPI injects Request automatically
        # P5.6 T5: Check the global RBAC enforcement flag stored on app.state
        # at create_app time.  When False, bypass all role checks immediately.
        # This handles both rbac_enforcement=disabled (explicit opt-out on
        # loopback) and rbac_enforcement=auto + provider=none (the default
        # single-operator-trust shortcut).
        _app_state = getattr(getattr(request, "app", None), "state", None)
        if _app_state is not None:
            rbac_enforced: bool | None = getattr(_app_state, "rbac_enforced", None)
            if rbac_enforced is False:
                # RBAC globally disabled — passthrough unconditionally.
                return

        identity: AuthIdentity | None = getattr(request.state, "identity", None)
        if identity is None:
            # Auth disabled / provider=none — single-operator-trust mode, allow.
            return
        if not set(identity.roles) & set(allowed_roles):
            raise HTTPException(status_code=403, detail="Insufficient role")

    # Marker used by the RBAC-901 programmatic route-sweep test.
    _check_role._is_require_role = True  # type: ignore[attr-defined]
    return _check_role


__all__ = [
    "ROLE_PERMISSIONS",
    "require_role",
]
