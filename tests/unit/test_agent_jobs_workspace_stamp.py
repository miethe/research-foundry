"""DF-004 — POST /agent-jobs must stamp workspace_id from identity, not the client body.

Regression coverage for the fix to ``agent_jobs.py::launch_job`` /
``AgentJobService.create_job``: an authenticated identity's own
``workspace_id`` must override any client-supplied ``body.workspace_id`` for
BOTH the persisted ``AgentJob`` record and the ``agent_job_launched`` audit
event's ``actor_workspace_id`` — the same "identity overrides client input"
idiom already proven by ``builder_service.create_draft`` and
``audit_service.record_event``'s ``effective_workspace_id`` override.

Two layers of coverage:

* ``TestCreateJobIdentityStamp`` — direct unit test of
  ``AgentJobService.create_job(identity=...)`` in isolation.
* ``TestLaunchJobRouterStamp`` — router-level integration test through
  ``POST /api/agent-jobs``, verifying the persisted job AND the audit trail
  both reflect the identity's workspace, not the spoofable request body.

``identity=None`` (LAN single_user / auth provider ``none``) must remain
byte-identical to pre-fix behavior in both layers (AC: no regression for the
default single-operator deployment).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from research_foundry.api.app import create_app
from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.services import audit_service
from research_foundry.services.agent_job_service import AgentJobService

_MINIMAL_POLICY_SNAPSHOT: dict[str, Any] = {
    "allowed_tools": ["search", "source_card"],
    "data_scopes": [],
}

_IDENTITY = AuthIdentity("u1", "ws-identity", ("owner", "admin"))


# ---------------------------------------------------------------------------
# Layer 1: AgentJobService.create_job unit coverage
# ---------------------------------------------------------------------------


class TestCreateJobIdentityStamp:
    """Direct unit coverage of the ``identity`` param on ``create_job``."""

    def test_identity_overrides_body_workspace_id(self, tmp_path: Path) -> None:
        """An authenticated identity's workspace wins over the workspace_id arg."""
        paths = FoundryPaths(root=tmp_path)
        service = AgentJobService(paths)

        job = service.create_job(
            provider="claude_agent_sdk",
            model_profile="rf_synthesize_deep",
            request_kind="research",
            policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
            workspace_id="ws-spoofed",
            identity=_IDENTITY,
        )

        assert job.workspace_id == "ws-identity"
        assert job.workspace_id != "ws-spoofed"

    def test_identity_none_falls_back_to_workspace_id_arg(self, tmp_path: Path) -> None:
        """identity=None (single-user default) is byte-identical to pre-fix behavior."""
        paths = FoundryPaths(root=tmp_path)
        service = AgentJobService(paths)

        job = service.create_job(
            provider="claude_agent_sdk",
            model_profile="rf_synthesize_deep",
            request_kind="research",
            policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
            workspace_id="ws-explicit",
            identity=None,
        )

        assert job.workspace_id == "ws-explicit"


# ---------------------------------------------------------------------------
# Layer 2: POST /api/agent-jobs router-level integration coverage
# ---------------------------------------------------------------------------


class _InjectIdentityMiddleware(BaseHTTPMiddleware):
    """Test middleware injecting a fixed AuthIdentity onto request.state.

    Established pattern — see ``tests/test_workspace_isolation_enforcement.py``
    / ``tests/unit/test_rbac_catalog.py``.
    """

    def __init__(self, app: Any, identity: AuthIdentity | None) -> None:
        super().__init__(app)
        self._identity = identity

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if self._identity is not None:
            request.state.identity = self._identity
        return await call_next(request)


def _make_client(paths: FoundryPaths, identity: AuthIdentity | None) -> TestClient:
    paths.foundry_yaml.write_text(
        "foundry:\n  agents:\n    enabled: true\n",
        encoding="utf-8",
    )
    config = FoundryConfig(paths=paths)
    app = create_app(config)
    app.dependency_overrides[get_paths] = lambda: paths
    app.add_middleware(_InjectIdentityMiddleware, identity=identity)
    return TestClient(app, raise_server_exceptions=True)


def _mock_popen() -> MagicMock:
    proc = MagicMock()
    proc.pid = 99999
    proc.poll.return_value = 0
    proc.wait.return_value = 0
    return proc


def _passing_guard() -> Any:
    from research_foundry.services.governance import GuardResult

    return GuardResult(passed=True, exit_code=0, violations=[])


@pytest.fixture()
def foundry_paths(tmp_path: Path) -> FoundryPaths:
    return FoundryPaths(root=tmp_path)


class TestLaunchJobRouterStamp:
    """POST /api/agent-jobs stamps workspace_id from identity, end-to-end."""

    def _launch(self, client: TestClient, body: dict[str, Any]) -> Any:
        with (
            patch(
                "research_foundry.api.routers.agent_jobs.guard_check",
                return_value=_passing_guard(),
            ),
            patch(
                "research_foundry.services.agent_job_service.subprocess.Popen",
                return_value=_mock_popen(),
            ),
            patch(
                "research_foundry.services.agent_job_service.importlib.util.find_spec",
                return_value=MagicMock(),
            ),
        ):
            return client.post("/api/agent-jobs", json=body)

    def test_authenticated_identity_overrides_body_workspace_id(
        self, foundry_paths: FoundryPaths
    ) -> None:
        """Persisted job AND audit event both use identity.workspace_id, not body value."""
        client = _make_client(foundry_paths, _IDENTITY)
        body = {
            "provider": "claude_agent_sdk",
            "model_profile": "rf_synthesize_deep",
            "request_kind": "research",
            "policy_snapshot": dict(_MINIMAL_POLICY_SNAPSHOT),
            "project_id": "test-project",
            "workspace_id": "ws-spoofed",
            "created_by": None,
        }

        resp = self._launch(client, body)
        assert resp.status_code == 201, resp.text
        job = resp.json()

        # Persisted job record: identity wins, not the client-supplied value.
        assert job["workspace_id"] == "ws-identity"
        assert job["workspace_id"] != "ws-spoofed"

        # Audit trail: actor_workspace_id on agent_job_launched matches the
        # SAME effective value — not independently spoofable via the body.
        result = audit_service.list_events(
            foundry_paths, mutation_type="agent_job_launched", limit=10
        )
        matching = [e for e in result["items"] if e["target_ref"] == job["agent_job_id"]]
        assert matching, "expected an agent_job_launched audit event for this job"
        assert matching[0]["actor_workspace_id"] == "ws-identity"
        assert matching[0]["actor_workspace_id"] != "ws-spoofed"

    def test_no_identity_falls_back_to_body_workspace_id(
        self, foundry_paths: FoundryPaths
    ) -> None:
        """identity=None (LAN single_user default) is byte-identical to pre-fix behavior."""
        client = _make_client(foundry_paths, identity=None)
        body = {
            "provider": "claude_agent_sdk",
            "model_profile": "rf_synthesize_deep",
            "request_kind": "research",
            "policy_snapshot": dict(_MINIMAL_POLICY_SNAPSHOT),
            "project_id": "test-project",
            "workspace_id": "ws-explicit",
            "created_by": None,
        }

        resp = self._launch(client, body)
        assert resp.status_code == 201, resp.text
        job = resp.json()

        assert job["workspace_id"] == "ws-explicit"

        result = audit_service.list_events(
            foundry_paths, mutation_type="agent_job_launched", limit=10
        )
        matching = [e for e in result["items"] if e["target_ref"] == job["agent_job_id"]]
        assert matching, "expected an agent_job_launched audit event for this job"
        assert matching[0]["actor_workspace_id"] == "ws-explicit"
