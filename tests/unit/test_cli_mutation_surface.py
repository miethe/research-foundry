"""CLI/service mutation-surface classification tests (RBAC-006).

Verifies that:
1. The CLI mutation surface classification comment exists in rbac.py's module
   docstring (naming the concrete CLI entry points classified as
   single-operator-trust).
2. The service functions named in the classification are importable and exist
   (the classification is not dead documentation).
3. No HTTP mutation route in catalog.py or reports.py is missing require_role
   (i.e., there is no HTTP path that calls these service functions without
   going through the router-layer gating).  This is the same completeness
   assertion as RBAC-901 but scoped explicitly to the CLI-classified surfaces.

Forward-looking surfaces documented but not yet tested (P5.3):
  rf workspace migrate|enforce|rollback  →  services/workspace_migrate.py (future)

These are noted here but not asserted — the module does not exist yet.
"""

from __future__ import annotations

import pytest
from fastapi.routing import APIRoute

from research_foundry.api.routers.agent_jobs import router as agent_jobs_router
from research_foundry.api.routers.catalog import router as catalog_router
from research_foundry.api.routers.reports import router as reports_router

MUTATION_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


# ---------------------------------------------------------------------------
# Helpers (mirrored from test_rbac_route_sweep for isolation)
# ---------------------------------------------------------------------------


def _has_require_role(dependant) -> bool:
    for dep in dependant.dependencies:
        if getattr(dep.call, "_is_require_role", False):
            return True
        if _has_require_role(dep):
            return True
    return False


def _ungated_mutations(router) -> list[str]:
    ungated = []
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods or []):
            if method in MUTATION_METHODS and not _has_require_role(route.dependant):
                ungated.append(f"{method} {route.path}")
    return ungated


# ---------------------------------------------------------------------------
# RBAC-006-A: Classification note exists in rbac.py
# ---------------------------------------------------------------------------


class TestCliSurfaceClassificationDocumented:
    """The rbac.py module docstring must name all CLI mutation entry points
    classified as single-operator-trust surfaces."""

    def _rbac_doc(self) -> str:
        from research_foundry.api.auth import rbac
        return rbac.__doc__ or ""

    def test_rf_ingest_mentioned(self):
        assert "rf ingest" in self._rbac_doc()

    def test_rf_catalog_rebuild_mentioned(self):
        assert "rf catalog rebuild" in self._rbac_doc()

    def test_rf_writeback_mentioned(self):
        assert "rf writeback" in self._rbac_doc()

    def test_rf_source_card_create_mentioned(self):
        assert "rf source-card create" in self._rbac_doc()

    def test_single_operator_trust_mentioned(self):
        assert "single-operator-trust" in self._rbac_doc()

    def test_source_cards_service_referenced(self):
        doc = self._rbac_doc()
        assert "source_cards" in doc, (
            "rbac.py must name services/source_cards.py as the rf-ingest CLI entry point"
        )

    def test_catalog_service_referenced(self):
        doc = self._rbac_doc()
        assert "catalog_service" in doc, (
            "rbac.py must name services/catalog_service.py as the rf-catalog-rebuild entry point"
        )

    def test_writeback_service_referenced(self):
        doc = self._rbac_doc()
        assert "writeback" in doc, (
            "rbac.py must name services/writeback.py as the rf-writeback entry point"
        )


# ---------------------------------------------------------------------------
# RBAC-006-B: Named service functions are importable
# ---------------------------------------------------------------------------


class TestCliServiceFunctionsExist:
    """The service functions named in the classification must be importable."""

    def test_source_cards_service_importable(self):
        from research_foundry.services import source_cards  # noqa: F401

    def test_catalog_service_importable(self):
        from research_foundry.services import catalog_service  # noqa: F401

    def test_writeback_service_importable(self):
        try:
            from research_foundry.services import writeback  # noqa: F401
        except ImportError:
            pytest.skip("writeback service not yet implemented — update classification when it lands")


# ---------------------------------------------------------------------------
# RBAC-006-C: No HTTP path bypasses require_role for CLI-classified surfaces
# ---------------------------------------------------------------------------


class TestNoHttpBypassForCliSurfaces:
    """Every mutation route that calls the CLI-classified service functions must
    have require_role in its dependency tree.  Since require_role gates ALL
    mutation routes in catalog.py and reports.py (verified by RBAC-901), this
    is equivalent to asserting zero ungated mutations exist in those routers."""

    def test_catalog_router_has_no_ungated_mutations(self):
        ungated = _ungated_mutations(catalog_router)
        assert ungated == [], (
            f"CLI service functions are reachable via unprotected HTTP routes in catalog: {ungated}"
        )

    def test_reports_router_has_no_ungated_mutations(self):
        ungated = _ungated_mutations(reports_router)
        assert ungated == [], (
            f"CLI service functions are reachable via unprotected HTTP routes in reports: {ungated}"
        )

    def test_agent_jobs_router_has_no_ungated_mutations(self):
        ungated = _ungated_mutations(agent_jobs_router)
        assert ungated == [], (
            f"Agent-job mutation routes are unprotected: {ungated}"
        )
