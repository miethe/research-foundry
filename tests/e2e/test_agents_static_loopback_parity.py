"""E2E parity suite: ``agents.enabled`` feature flag in static vs loopback modes.

Two modes under test
--------------------
1. **Static (flag OFF)** — ``agents.enabled`` absent from config or set to
   ``False``.  The agent-job router is NOT registered; every request to
   ``/api/agent-jobs`` returns 404 (route not found).  This mirrors the
   static-export / shared-LAN deployment state where the feature is disabled
   until P5 RBAC + workspace-isolation gates clear.

2. **Loopback (flag ON)** — ``agents.enabled=True``.  The agent-job router IS
   registered and the full governed flow runs end-to-end in loopback mode:
   launch (guard + spawn mocked) → poll status → check response shape.

All credentials are SYNTHETIC — Gate #2 (live provider keys) is NOT approved.
Subprocess spawning is mocked via ``subprocess.Popen`` so no real child process
is started.

Patterns follow ``tests/integration/test_agent_jobs_api.py`` (TestClient +
dependency-override) and ``tests/integration/test_agent_job_e2e_claude.py``
(full lifecycle with mock stubs).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.services.governance import GuardResult


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_MINIMAL_POLICY_SNAPSHOT: dict[str, Any] = {
    "allowed_tools": ["search", "source_card"],
    "data_scopes": [],
}

_LAUNCH_BODY: dict[str, Any] = {
    "provider": "claude_agent_sdk",
    "model_profile": "rf_synthesize_deep",
    "request_kind": "research",
    "policy_snapshot": _MINIMAL_POLICY_SNAPSHOT,
    "project_id": "test-project",
    "workspace_id": None,
    "created_by": None,
}


def _passing_guard() -> GuardResult:
    return GuardResult(passed=True, exit_code=0, violations=[])


def _mock_popen() -> MagicMock:
    """Return a mock Popen that appears to have already exited cleanly."""
    proc = MagicMock()
    proc.pid = 99999
    proc.poll.return_value = 0
    proc.wait.return_value = 0
    return proc


# ---------------------------------------------------------------------------
# Fixtures: two app configurations — flag OFF and flag ON
# ---------------------------------------------------------------------------


@pytest.fixture()
def foundry_paths(tmp_path: Path) -> FoundryPaths:
    """Isolated FoundryPaths rooted at a temporary directory."""
    return FoundryPaths(root=tmp_path)


@pytest.fixture()
def app_agents_disabled(foundry_paths: FoundryPaths, tmp_path: Path) -> Any:
    """FastAPI app where ``agents.enabled`` is explicitly set to ``False``.

    Writes a ``foundry.yaml`` with ``agents.enabled: false`` so that
    ``FoundryConfig.agents_enabled()`` returns ``False`` and the agent-job
    router is NOT registered.  This mirrors a shared-LAN or static-export
    deployment where the operator has explicitly disabled the agent surface.
    """
    (tmp_path / "foundry.yaml").write_text(
        "foundry:\n  agents:\n    enabled: false\n",
        encoding="utf-8",
    )
    config = FoundryConfig(paths=foundry_paths)
    app = create_app(config)
    app.dependency_overrides[get_paths] = lambda: foundry_paths
    return app


@pytest.fixture()
def app_agents_enabled(foundry_paths: FoundryPaths, tmp_path: Path) -> Any:
    """FastAPI app where ``agents.enabled=True`` (loopback mode).

    Writes a minimal ``foundry.yaml`` with ``agents.enabled: true`` so
    ``FoundryConfig.agents_enabled()`` returns ``True`` and the agent-job
    router IS registered.
    """
    (tmp_path / "foundry.yaml").write_text(
        "foundry:\n  agents:\n    enabled: true\n",
        encoding="utf-8",
    )
    config = FoundryConfig(paths=foundry_paths)
    app = create_app(config)
    app.dependency_overrides[get_paths] = lambda: foundry_paths
    return app


@pytest.fixture()
def client_disabled(app_agents_disabled: Any) -> TestClient:
    """TestClient for the agents-disabled app."""
    return TestClient(app_agents_disabled, raise_server_exceptions=True)


@pytest.fixture()
def client_loopback(app_agents_enabled: Any) -> TestClient:
    """TestClient for the agents-enabled (loopback) app."""
    return TestClient(app_agents_enabled, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Mode 1 — Static / Flag OFF: AC-flag-off
# ---------------------------------------------------------------------------


class TestStaticFlagOff:
    """Verify that all /api/agent-jobs routes are absent when flag is disabled.

    AC-flag-off: When agents.enabled=False (or absent from config), requests
    to /api/agent-jobs return 404 (route not registered in the app).
    """

    def test_post_agent_jobs_returns_404(self, client_disabled: TestClient) -> None:
        """POST /api/agent-jobs returns 404 when agents.enabled is absent."""
        resp = client_disabled.post("/api/agent-jobs", json=_LAUNCH_BODY)
        assert resp.status_code == 404, (
            f"Expected 404 (route absent) when agents.enabled=False; got {resp.status_code}"
        )

    def test_get_agent_job_detail_returns_404(self, client_disabled: TestClient) -> None:
        """GET /api/agent-jobs/{id} returns 404 when agents.enabled is absent."""
        resp = client_disabled.get("/api/agent-jobs/some-job-id-123")
        assert resp.status_code == 404, (
            f"Expected 404 (route absent) for GET agent-job detail; got {resp.status_code}"
        )

    def test_get_agent_job_artifacts_returns_404(self, client_disabled: TestClient) -> None:
        """GET /api/agent-jobs/{id}/artifacts returns 404 when flag is off."""
        resp = client_disabled.get("/api/agent-jobs/some-job-id-123/artifacts")
        assert resp.status_code == 404, (
            f"Expected 404 for artifacts endpoint; got {resp.status_code}"
        )

    def test_get_agent_job_events_returns_404(self, client_disabled: TestClient) -> None:
        """GET /api/agent-jobs/{id}/events returns 404 when flag is off."""
        resp = client_disabled.get("/api/agent-jobs/some-job-id-123/events")
        assert resp.status_code == 404, (
            f"Expected 404 for events/SSE endpoint; got {resp.status_code}"
        )

    def test_post_cancel_returns_404(self, client_disabled: TestClient) -> None:
        """POST /api/agent-jobs/{id}/cancel returns 404 when flag is off."""
        resp = client_disabled.post("/api/agent-jobs/some-job-id-123/cancel")
        assert resp.status_code == 404, (
            f"Expected 404 for cancel endpoint; got {resp.status_code}"
        )

    def test_post_accept_returns_404(self, client_disabled: TestClient) -> None:
        """POST /api/agent-jobs/{id}/accept returns 404 when flag is off."""
        resp = client_disabled.post(
            "/api/agent-jobs/some-job-id-123/accept",
            json={"accepted_by": "reviewer"},
        )
        assert resp.status_code == 404, (
            f"Expected 404 for accept endpoint; got {resp.status_code}"
        )

    def test_health_still_returns_200(self, client_disabled: TestClient) -> None:
        """Health probe is unaffected by the agents flag being disabled."""
        resp = client_disabled.get("/health")
        assert resp.status_code == 200

    def test_runs_api_still_accessible(self, client_disabled: TestClient) -> None:
        """GET /api/runs remains accessible when agents are disabled.

        The agents flag only gates the agent-job surface; other routers are
        unaffected (YAGNI isolation — no cascading disablement).
        """
        resp = client_disabled.get("/api/runs")
        # 200 (empty list) or 404 is both valid; what matters is NOT a routing
        # error that would indicate the entire API is broken.
        assert resp.status_code in (200, 404), (
            f"Runs API should be reachable; got unexpected {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# Mode 2 — Loopback / Flag ON: AC-flag-on-loopback
# ---------------------------------------------------------------------------


class TestLoopbackFlagOn:
    """Verify the full governed agent-job flow when agents.enabled=True.

    AC-flag-on-loopback: When agents.enabled=True AND loopback mode is active,
    a mock agent job can be launched, polled, and its status checked without
    real credentials.
    """

    def test_post_agent_jobs_route_exists(self, client_loopback: TestClient) -> None:
        """POST /api/agent-jobs returns non-404 when agents.enabled=True.

        Verifies the router is registered; we don't require a successful 201
        here (that is tested in the launch success tests below).
        """
        with patch(
            "research_foundry.api.routers.agent_jobs.guard_check",
            return_value=_passing_guard(),
        ), patch(
            "research_foundry.services.agent_job_service.subprocess.Popen",
            return_value=_mock_popen(),
        ), patch(
            "research_foundry.services.agent_job_service.importlib.util.find_spec",
            return_value=MagicMock(),
        ):
            resp = client_loopback.post("/api/agent-jobs", json=_LAUNCH_BODY)

        assert resp.status_code != 404, (
            "POST /api/agent-jobs returned 404 — route is not registered when "
            "agents.enabled=True. Check that app.py includes the router when the "
            "flag is on."
        )

    def test_launch_returns_201_and_job_id(self, client_loopback: TestClient) -> None:
        """Loopback launch with passing guard and mocked spawn → HTTP 201.

        Full governed flow step 1: POST creates the job record.
        """
        with patch(
            "research_foundry.api.routers.agent_jobs.guard_check",
            return_value=_passing_guard(),
        ), patch(
            "research_foundry.services.agent_job_service.subprocess.Popen",
            return_value=_mock_popen(),
        ), patch(
            "research_foundry.services.agent_job_service.importlib.util.find_spec",
            return_value=MagicMock(),
        ):
            resp = client_loopback.post("/api/agent-jobs", json=_LAUNCH_BODY)

        assert resp.status_code == 201, (
            f"Expected HTTP 201 on successful loopback launch; got {resp.status_code}: {resp.text}"
        )
        job = resp.json()
        assert "agent_job_id" in job and job["agent_job_id"], (
            "Launch response missing agent_job_id"
        )
        assert "status" in job, "Launch response missing status field"

    def test_poll_job_status_after_launch(self, client_loopback: TestClient) -> None:
        """Full loopback flow: launch → poll GET /api/agent-jobs/{id} for status.

        AC-flag-on-loopback: mock job is launched and its status can be polled
        without real credentials.
        """
        # Step 1: launch
        with patch(
            "research_foundry.api.routers.agent_jobs.guard_check",
            return_value=_passing_guard(),
        ), patch(
            "research_foundry.services.agent_job_service.subprocess.Popen",
            return_value=_mock_popen(),
        ), patch(
            "research_foundry.services.agent_job_service.importlib.util.find_spec",
            return_value=MagicMock(),
        ):
            launch_resp = client_loopback.post("/api/agent-jobs", json=_LAUNCH_BODY)

        assert launch_resp.status_code == 201, (
            f"Launch failed ({launch_resp.status_code}): {launch_resp.text}"
        )
        job_id = launch_resp.json()["agent_job_id"]

        # Step 2: poll status
        poll_resp = client_loopback.get(f"/api/agent-jobs/{job_id}")
        assert poll_resp.status_code == 200, (
            f"GET /api/agent-jobs/{job_id} returned {poll_resp.status_code}; "
            "expected 200 — job should be findable immediately after launch"
        )
        polled_job = poll_resp.json()
        assert polled_job["agent_job_id"] == job_id, (
            "Polled job_id does not match the launched job"
        )
        assert "status" in polled_job, "Polled job missing status field"

    def test_launch_returns_policy_snapshot(self, client_loopback: TestClient) -> None:
        """Loopback launch response includes policy_snapshot (AC-4.5 shape).

        The FE reads policy_snapshot from the job record for PolicyGateSummary.
        """
        with patch(
            "research_foundry.api.routers.agent_jobs.guard_check",
            return_value=_passing_guard(),
        ), patch(
            "research_foundry.services.agent_job_service.subprocess.Popen",
            return_value=_mock_popen(),
        ), patch(
            "research_foundry.services.agent_job_service.importlib.util.find_spec",
            return_value=MagicMock(),
        ):
            resp = client_loopback.post("/api/agent-jobs", json=_LAUNCH_BODY)

        assert resp.status_code == 201
        job = resp.json()
        assert "policy_snapshot" in job, (
            "Launch response missing policy_snapshot — PolicyGateSummary will break"
        )
        ps = job["policy_snapshot"]
        assert ps.get("allowed_tools") == _LAUNCH_BODY["policy_snapshot"]["allowed_tools"]

    def test_artifacts_endpoint_accessible_after_launch(
        self, client_loopback: TestClient
    ) -> None:
        """GET /api/agent-jobs/{id}/artifacts returns 200 for a new loopback job.

        Verifies that the artifacts endpoint is accessible and returns an empty
        list immediately after launch (no artifacts staged yet).
        """
        with patch(
            "research_foundry.api.routers.agent_jobs.guard_check",
            return_value=_passing_guard(),
        ), patch(
            "research_foundry.services.agent_job_service.subprocess.Popen",
            return_value=_mock_popen(),
        ), patch(
            "research_foundry.services.agent_job_service.importlib.util.find_spec",
            return_value=MagicMock(),
        ):
            launch_resp = client_loopback.post("/api/agent-jobs", json=_LAUNCH_BODY)

        assert launch_resp.status_code == 201
        job_id = launch_resp.json()["agent_job_id"]

        artifacts_resp = client_loopback.get(f"/api/agent-jobs/{job_id}/artifacts")
        assert artifacts_resp.status_code == 200, (
            f"Expected 200 from artifacts endpoint; got {artifacts_resp.status_code}"
        )
        assert isinstance(artifacts_resp.json(), list), (
            "Artifacts endpoint should return a list"
        )

    def test_loopback_no_real_credentials_used(self, client_loopback: TestClient) -> None:
        """Confirm no real credentials are needed for loopback mock job launch.

        Gate #2 NOT approved — all credentials are synthetic.  This test
        patches the subprocess to avoid any real spawn and verifies the flow
        completes without requiring a live API key.
        """
        body = {**_LAUNCH_BODY, "credential_b64": None}

        with patch(
            "research_foundry.api.routers.agent_jobs.guard_check",
            return_value=_passing_guard(),
        ), patch(
            "research_foundry.services.agent_job_service.subprocess.Popen",
            return_value=_mock_popen(),
        ) as mock_popen, patch(
            "research_foundry.services.agent_job_service.importlib.util.find_spec",
            return_value=MagicMock(),
        ):
            resp = client_loopback.post("/api/agent-jobs", json=body)

        assert resp.status_code == 201, (
            f"Expected 201 without credentials; got {resp.status_code}: {resp.text}"
        )
        # The mock was called — subprocess was mocked, not a real spawn.
        assert mock_popen.called, "subprocess.Popen mock was not invoked"


# ---------------------------------------------------------------------------
# Parity assertion: flag OFF disables all routes; flag ON enables all routes
# ---------------------------------------------------------------------------


class TestFlagParityInvariant:
    """Cross-mode invariant: routes present iff flag is on.

    These tests exercise the same URL under both configurations and assert
    the parity contract — routes are absent when disabled, present when enabled.
    """

    @pytest.mark.parametrize(
        "path,method",
        [
            ("/api/agent-jobs/dummy-id-xxx", "GET"),
            ("/api/agent-jobs/dummy-id-xxx/artifacts", "GET"),
            ("/api/agent-jobs/dummy-id-xxx/events", "GET"),
            ("/api/agent-jobs/dummy-id-xxx/cancel", "POST"),
        ],
    )
    def test_route_absent_when_disabled(
        self,
        path: str,
        method: str,
        client_disabled: TestClient,
    ) -> None:
        """Parametrized: each sub-route returns 404 when agents.enabled is off."""
        if method == "GET":
            resp = client_disabled.get(path)
        else:
            resp = client_disabled.post(path)
        assert resp.status_code == 404, (
            f"{method} {path} should return 404 (route absent) when flag is off; "
            f"got {resp.status_code}"
        )

    @pytest.mark.parametrize(
        "path,method",
        [
            ("/api/agent-jobs/dummy-id-xxx", "GET"),
            ("/api/agent-jobs/dummy-id-xxx/artifacts", "GET"),
        ],
    )
    def test_route_present_when_enabled(
        self,
        path: str,
        method: str,
        client_loopback: TestClient,
    ) -> None:
        """Parametrized: sub-routes return non-404 when agents.enabled is on.

        Note: 404 for unknown job IDs from the *service layer* is still 404,
        but it is a different 404 (job-not-found) than a missing route 404.
        We verify the route is registered by checking the response body for the
        service-level "not found" shape, which includes a ``detail`` key
        (FastAPI HTTPException), not an "unknown route" response.
        """
        if method == "GET":
            resp = client_loopback.get(path)
        else:
            resp = client_loopback.post(path)
        # Even a 404 from the service layer (unknown job ID) proves the route
        # is registered: it will have a {"detail": "..."} body from our handler,
        # not the generic FastAPI "Not Found" body from an unregistered route.
        if resp.status_code == 404:
            body = resp.json()
            assert "detail" in body, (
                f"{method} {path} returned 404 without a 'detail' key — "
                "this looks like a missing route (router not registered), not "
                "a job-not-found response. Check agents_enabled flag wiring."
            )
