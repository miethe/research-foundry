"""Route-sweep seam test — verifies 100% of mutation routes carry require_role (RBAC-901).

This test walks every route in the catalog, reports, runs, and agent_jobs routers,
identifies POST/PUT/PATCH/DELETE routes (mutations), and asserts that each
one has a ``require_role``-derived dependency in its dependency tree.

A test failure here means a mutation route was added or modified without
adding ``Depends(require_role(...))``.  This is the completeness guarantee
for the P5.2 RBAC enforcement phase.

Mutation-route inventory covered (19 routes across 4 routers):
  catalog_router (2):
    POST /catalog/import/run/{run_id}
    POST /catalog/import

  reports_router (14):
    POST   /reports
    DELETE /reports/{report_id}
    POST   /reports/{report_id}/versions
    POST   /reports/{report_id}/versions/{version_id}/restore
    POST   /reports/{report_id}/blocks
    PATCH  /reports/{report_id}/blocks/reorder
    PATCH  /reports/{report_id}/blocks/{block_id}
    DELETE /reports/{report_id}/blocks/{block_id}
    POST   /reports/{report_id}/claim-links
    DELETE /reports/{report_id}/claim-links/{claim_link_id}
    POST   /reports/{report_id}/source-links
    DELETE /reports/{report_id}/source-links/{source_link_id}
    POST   /reports/{report_id}/verify
    POST   /reports/{report_id}/publish-preview

  runs_router (0):
    [no mutation routes — see RBAC-005 audit comment in runs.py]

  agent_jobs_router (3):
    POST /agent-jobs
    POST /agent-jobs/{job_id}/cancel
    POST /agent-jobs/{job_id}/accept
"""

from __future__ import annotations

import pytest
from fastapi.routing import APIRoute

from research_foundry.api.routers.agent_jobs import router as agent_jobs_router
from research_foundry.api.routers.catalog import router as catalog_router
from research_foundry.api.routers.reports import router as reports_router
from research_foundry.api.routers.runs import router as runs_router

MUTATION_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _has_require_role(dependant) -> bool:
    """Recursively check if any dependency in the tree carries _is_require_role=True.

    ``require_role(...)`` marks its inner function with
    ``_is_require_role = True`` so this detection does not rely on fragile
    name-string matching.
    """
    for dep in dependant.dependencies:
        if getattr(dep.call, "_is_require_role", False):
            return True
        if _has_require_role(dep):  # recurse into nested deps
            return True
    return False


def _collect_mutation_routes(router) -> list[tuple[str, str]]:
    """Return (method, path) pairs for all mutation routes in *router*."""
    found = []
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods or []):
            if method in MUTATION_METHODS:
                found.append((method, route.path))
    return found


def _collect_ungated(router) -> list[tuple[str, str]]:
    """Return mutation routes in *router* that are missing require_role."""
    ungated = []
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods or []):
            if method in MUTATION_METHODS:
                if not _has_require_role(route.dependant):
                    ungated.append((method, route.path))
    return ungated


# ---------------------------------------------------------------------------
# Catalog router sweep
# ---------------------------------------------------------------------------


class TestCatalogRouterSweep:
    def test_all_catalog_mutations_are_gated(self):
        ungated = _collect_ungated(catalog_router)
        assert ungated == [], (
            f"catalog_router has ungated mutation routes: {ungated}"
        )

    def test_catalog_has_expected_mutation_count(self):
        """Regression guard: 2 mutation routes in catalog_router."""
        mutations = _collect_mutation_routes(catalog_router)
        assert len(mutations) == 2, (
            f"Expected 2 mutation routes in catalog_router, found {len(mutations)}: {mutations}"
        )

    def test_catalog_import_run_is_post(self):
        routes = {(m, p) for m, p in _collect_mutation_routes(catalog_router)}
        assert ("POST", "/catalog/import/run/{run_id}") in routes

    def test_catalog_import_all_is_post(self):
        routes = {(m, p) for m, p in _collect_mutation_routes(catalog_router)}
        assert ("POST", "/catalog/import") in routes


# ---------------------------------------------------------------------------
# Reports router sweep
# ---------------------------------------------------------------------------


class TestReportsRouterSweep:
    def test_all_reports_mutations_are_gated(self):
        ungated = _collect_ungated(reports_router)
        assert ungated == [], (
            f"reports_router has ungated mutation routes: {ungated}"
        )

    def test_reports_has_expected_mutation_count(self):
        """Regression guard: 14 mutation routes in reports_router."""
        mutations = _collect_mutation_routes(reports_router)
        assert len(mutations) == 14, (
            f"Expected 14 mutation routes in reports_router, found {len(mutations)}: {mutations}"
        )

    def test_expected_mutation_routes_present(self):
        routes = {(m, p) for m, p in _collect_mutation_routes(reports_router)}
        expected = {
            ("POST",   "/reports"),
            ("DELETE", "/reports/{report_id}"),
            ("POST",   "/reports/{report_id}/versions"),
            ("POST",   "/reports/{report_id}/versions/{version_id}/restore"),
            ("POST",   "/reports/{report_id}/blocks"),
            ("PATCH",  "/reports/{report_id}/blocks/reorder"),
            ("PATCH",  "/reports/{report_id}/blocks/{block_id}"),
            ("DELETE", "/reports/{report_id}/blocks/{block_id}"),
            ("POST",   "/reports/{report_id}/claim-links"),
            ("DELETE", "/reports/{report_id}/claim-links/{claim_link_id}"),
            ("POST",   "/reports/{report_id}/source-links"),
            ("DELETE", "/reports/{report_id}/source-links/{source_link_id}"),
            ("POST",   "/reports/{report_id}/verify"),
            ("POST",   "/reports/{report_id}/publish-preview"),
        }
        missing = expected - routes
        extra = routes - expected
        assert not missing, f"Missing expected mutation routes: {missing}"
        assert not extra, f"Unexpected mutation routes (update this test): {extra}"


# ---------------------------------------------------------------------------
# Runs router sweep
# ---------------------------------------------------------------------------


class TestRunsRouterSweep:
    def test_runs_has_no_mutation_routes(self):
        """RBAC-005 audit: runs_router has zero mutation routes."""
        mutations = _collect_mutation_routes(runs_router)
        assert mutations == [], (
            f"Unexpected mutation routes in runs_router: {mutations} — "
            "add require_role gating before exposing mutations in runs.py"
        )


# ---------------------------------------------------------------------------
# agent_jobs router sweep (landed with P4 — now covered by P5.2 gating)
# ---------------------------------------------------------------------------


class TestAgentJobsRouterSweep:
    def test_all_agent_jobs_mutations_are_gated(self):
        ungated = _collect_ungated(agent_jobs_router)
        assert ungated == [], (
            f"agent_jobs_router has ungated mutation routes: {ungated}"
        )

    def test_agent_jobs_has_expected_mutation_count(self):
        """Regression guard: 3 mutation routes in agent_jobs_router."""
        mutations = _collect_mutation_routes(agent_jobs_router)
        assert len(mutations) == 3, (
            f"Expected 3 mutation routes in agent_jobs_router, found {len(mutations)}: {mutations}"
        )

    def test_expected_agent_job_mutation_routes_present(self):
        routes = {(m, p) for m, p in _collect_mutation_routes(agent_jobs_router)}
        expected = {
            ("POST", "/agent-jobs"),
            ("POST", "/agent-jobs/{job_id}/cancel"),
            ("POST", "/agent-jobs/{job_id}/accept"),
        }
        missing = expected - routes
        extra = routes - expected
        assert not missing, f"Missing expected agent-job mutation routes: {missing}"
        assert not extra, f"Unexpected agent-job mutation routes (update this test): {extra}"


# ---------------------------------------------------------------------------
# agent_jobs.py forward-compat documentation assertion
# ---------------------------------------------------------------------------


class TestAgentJobsForwardCompat:
    def test_agent_jobs_forward_compat_documented_in_rbac(self):
        """The RBAC-FORWARD-COMPAT note for agent_jobs.py exists in rbac.py."""
        from research_foundry.api.auth import rbac

        module_doc = rbac.__doc__ or ""
        assert "agent_jobs.py" in module_doc, (
            "rbac.py module docstring must reference the agent_jobs.py forward-compat contract"
        )
        assert "RBAC-FORWARD-COMPAT" in module_doc or "agent_job:launch" in module_doc, (
            "rbac.py must document the agent_job:launch permission"
        )
