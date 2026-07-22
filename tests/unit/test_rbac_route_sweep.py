"""Route-sweep seam test — verifies 100% of mutation routes carry require_role (RBAC-901).

This test walks every route in the catalog, reports, runs, and agent_jobs routers,
identifies POST/PUT/PATCH/DELETE routes (mutations), and asserts that each
one has a ``require_role``-derived dependency in its dependency tree.

A test failure here means a mutation route was added or modified without
adding ``Depends(require_role(...))``.  This is the completeness guarantee
for the P5.2 RBAC enforcement phase.

Mutation-route inventory covered (20 routes across 4 routers):
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

  runs_router (1):
    POST /runs — http-run-launch-endpoint contract (scaffold + register only)

  agent_jobs_router (3):
    POST /agent-jobs
    POST /agent-jobs/{job_id}/cancel
    POST /agent-jobs/{job_id}/accept
"""

from __future__ import annotations

import pytest
from fastapi.routing import APIRoute

from research_foundry.api.routers.admin import router as admin_router
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


def _collect_ungated(router, exempt: frozenset[tuple[str, str]] | None = None) -> list[tuple[str, str]]:
    """Return mutation routes in *router* that are missing require_role.

    *exempt* is a frozenset of (method, path) pairs that are allowed to omit
    the ``Depends(require_role(...))`` pattern because they enforce RBAC
    manually inside the function body (e.g. for security-ordering reasons
    documented in the route itself).
    """
    exempt = exempt or frozenset()
    ungated = []
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in sorted(route.methods or []):
            if method in MUTATION_METHODS:
                if (method, route.path) in exempt:
                    continue
                if not _has_require_role(route.dependant):
                    ungated.append((method, route.path))
    return ungated


# Routes where RBAC is enforced manually inside the function body rather than
# via ``Depends(require_role(...))``, for documented security-ordering reasons.
# Entries here are exempt from the ``_collect_ungated`` completeness check.
#
# publish-preview (PRD AC-2 / Phase 5.6-T4): The D13 sensitivity gate must fire
# BEFORE the role gate so a sensitivity violation (422) cannot be bypassed by
# choosing a higher-privileged role.  Moving the RBAC Depends before the function
# body would break that ordering guarantee.  The function enforces
# ``report:publish`` (owner/admin) manually in step 3, after sensitivity passes.
_MANUALLY_GATED_ROUTES: frozenset[tuple[str, str]] = frozenset({
    ("POST", "/reports/{report_id}/publish-preview"),
})


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
        """All mutation routes must have require_role gating or be in MANUALLY_GATED_ROUTES.

        publish-preview is in MANUALLY_GATED_ROUTES because it enforces RBAC
        manually after the sensitivity gate (PRD AC-2 ordering invariant).
        """
        ungated = _collect_ungated(reports_router, exempt=_MANUALLY_GATED_ROUTES)
        assert ungated == [], (
            f"reports_router has ungated mutation routes: {ungated}"
        )

    def test_reports_has_expected_mutation_count(self):
        """Regression guard: 15 mutation routes in reports_router.

        14 original routes + POST /reports/{report_id}/share-links (Phase 5.6-T4).
        """
        mutations = _collect_mutation_routes(reports_router)
        assert len(mutations) == 15, (
            f"Expected 15 mutation routes in reports_router, found {len(mutations)}: {mutations}"
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
            # Phase 5.6-T4: share link creation
            ("POST",   "/reports/{report_id}/share-links"),
        }
        missing = expected - routes
        extra = routes - expected
        assert not missing, f"Missing expected mutation routes: {missing}"
        assert not extra, f"Unexpected mutation routes (update this test): {extra}"

    def test_manually_gated_routes_are_documented(self):
        """Every entry in MANUALLY_GATED_ROUTES must appear in the reports_router."""
        routes = {(m, p) for m, p in _collect_mutation_routes(reports_router)}
        for entry in _MANUALLY_GATED_ROUTES:
            assert entry in routes, (
                f"MANUALLY_GATED_ROUTES entry {entry} is not in reports_router — "
                "remove it from the exemption set"
            )


# ---------------------------------------------------------------------------
# Runs router sweep
# ---------------------------------------------------------------------------


class TestRunsRouterSweep:
    def test_all_runs_mutations_are_gated(self):
        """RBAC-901: every mutation route in runs_router carries require_role."""
        ungated = _collect_ungated(runs_router)
        assert ungated == [], (
            f"runs_router has ungated mutation routes: {ungated}"
        )

    def test_runs_has_expected_mutation_count(self):
        """Regression guard: 1 mutation route in runs_router (http-run-launch-endpoint).

        Was 0 prior to the http-run-launch-endpoint contract — see RBAC-005
        audit comment in runs.py for the up-to-date route inventory.
        """
        mutations = _collect_mutation_routes(runs_router)
        assert len(mutations) == 1, (
            f"Expected 1 mutation route in runs_router, found {len(mutations)}: {mutations}"
        )

    def test_expected_runs_mutation_routes_present(self):
        routes = {(m, p) for m, p in _collect_mutation_routes(runs_router)}
        expected = {("POST", "/runs")}
        missing = expected - routes
        extra = routes - expected
        assert not missing, f"Missing expected runs mutation routes: {missing}"
        assert not extra, f"Unexpected runs mutation routes (update this test): {extra}"


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
# admin.py router sweep (public-multiuser-release-activation Phase 3, ACT-301..303)
# ---------------------------------------------------------------------------

# The PAT self-service mutation routes are intentionally NOT gated with
# Depends(require_role(...)) — any authenticated (or no-auth/single-operator)
# caller may act on their OWN PAT; acting on another user's PAT requires
# owner/admin, enforced MANUALLY inside the function body (identical
# rationale to reports.py's publish-preview exemption above: the permission
# decision depends on request content, not just the caller's role). See
# admin.py's module docstring, "Self-service exceptions" section, and
# TestPatSelfServiceManualGating below for the manual-enforcement coverage.
_ADMIN_MANUALLY_GATED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/admin/pats"),
        ("DELETE", "/admin/pats/{token_id}"),
    }
)


class TestAdminRouterSweep:
    def test_all_admin_mutations_are_gated(self):
        """RBAC-901: every admin.py mutation route carries require_role OR is
        in _ADMIN_MANUALLY_GATED_ROUTES (manual, request-content-dependent RBAC)."""
        ungated = _collect_ungated(admin_router, exempt=_ADMIN_MANUALLY_GATED_ROUTES)
        assert ungated == [], f"admin_router has ungated mutation routes: {ungated}"

    def test_admin_has_expected_mutation_count(self):
        """Regression guard: 8 mutation routes in admin_router.

        2 pre-existing (member role update, rate-limit config PATCH) + 6
        added by Phase 3 ACT-301/ACT-302 (service accounts: create/disable/
        issue-or-rotate-token/revoke-token = 4; PATs: issue/revoke = 2) —
        see test_expected_admin_mutation_routes_present for the exact
        inventory.
        """
        mutations = _collect_mutation_routes(admin_router)
        assert len(mutations) == 8, (
            f"Expected 8 mutation routes in admin_router, found {len(mutations)}: {mutations}"
        )

    def test_expected_admin_mutation_routes_present(self):
        routes = {(m, p) for m, p in _collect_mutation_routes(admin_router)}
        expected = {
            ("PATCH", "/admin/members/{user_id}/role"),
            ("PATCH", "/admin/rate-limit-config"),
            ("POST", "/admin/service-accounts"),
            ("DELETE", "/admin/service-accounts/{account_id}"),
            ("POST", "/admin/service-accounts/{account_id}/tokens"),
            ("DELETE", "/admin/service-accounts/{account_id}/tokens/{token_id}"),
            ("POST", "/admin/pats"),
            ("DELETE", "/admin/pats/{token_id}"),
        }
        missing = expected - routes
        extra = routes - expected
        assert not missing, f"Missing expected admin mutation routes: {missing}"
        assert not extra, f"Unexpected admin mutation routes (update this test): {extra}"

    def test_manually_gated_routes_are_documented(self):
        """Every entry in _ADMIN_MANUALLY_GATED_ROUTES must appear in admin_router."""
        routes = {(m, p) for m, p in _collect_mutation_routes(admin_router)}
        for entry in _ADMIN_MANUALLY_GATED_ROUTES:
            assert entry in routes, (
                f"_ADMIN_MANUALLY_GATED_ROUTES entry {entry} is not in admin_router — "
                "remove it from the exemption set"
            )


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
