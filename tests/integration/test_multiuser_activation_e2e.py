"""Cross-phase E2E: the full activated ``multi_user`` lifecycle (public-multiuser
release activation, ACT-601).

This file is the single end-to-end test the plan's Phase 6 asks for -- it
exercises the whole feature against a REAL ``create_app()`` / ``TestClient``,
not per-phase unit mocks:

  1. ``deployment_mode=multi_user`` with the DI-1 two-part gate (FR-13)
     satisfied (ack + an ``accepted`` audit artifact) -- the app boots.
  2. An owner caller (authenticated via the ``local_static`` provider adapter,
     never the token store) issues a service account and its access token
     through the real admin HTTP API (ACT-301).
  3. A DIFFERENT request authenticates with that freshly-issued SA token --
     the composite auth chain (ACT-203) resolves the SA identity from the
     token store, not from the provider adapter.
  4. An agent job is launched through the real ``POST /api/agent-jobs`` HTTP
     path (governance guard + subprocess spawn mocked, exactly like
     ``tests/integration/test_agent_jobs_api.py`` -- this file is not
     re-testing agent-job mechanics, only that identity binding survives the
     full HTTP round trip) and binds to the SA's *execution* identity in the
     audit log (ACT-204, FR-12), while the *triggering* human identity is
     preserved alongside it.
  5. The SA token is revoked through the admin API and immediately stops
     authenticating -- FR-10, no restart required.
  6. A companion ``single_user`` app boots and operates with ZERO of the
     above DI-1/SA state configured at all (FR-2 -- byte-identical to
     pre-``multi_user`` behavior).

Existing per-phase fixtures reused rather than reinvented:
  * ``tmp_foundry`` (tests/conftest.py)
  * multi_user config shape (``tests/test_di1_gate_live_session_regression.py``)
  * ``local_static`` provider config shape + provider-registry restore
    (``tests/test_composite_auth_chain.py``)
  * admin-API service-account/token surface (``tests/unit/test_admin_tokens_api.py``)
  * agent-job HTTP launch mocking triple (``tests/integration/test_agent_jobs_api.py``)

NOTE: the owner Bearer value is a fresh ``secrets.token_urlsafe`` value
generated at test run time (never a literal secret-shaped string in source),
mirroring the documented convention in ``test_di1_gate_live_session_regression.py``.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import research_foundry.api.auth.provider as _provider_module
from research_foundry.api.app import create_app
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.services import audit_service, rbac_store
from research_foundry.services.agent_job_service import AgentJobService
from research_foundry.yamlio import dump_yaml, load_yaml

_OWNER_TOKEN_ENV = "RF_TEST_MULTIUSER_E2E_OWNER_TOKEN"
_OWNER_USER_ID = "u_owner_e2e"
_WORKSPACE_ID = "default"

_MINIMAL_POLICY_SNAPSHOT: dict = {"allowed_tools": ["search"], "data_scopes": []}


@pytest.fixture(autouse=True)
def _restore_provider_registry():
    """``create_app`` re-registers ``local_static`` with a config-bound
    instance on every call (module-level ``_REGISTRY`` in
    ``api/auth/provider.py``). Snapshot/restore around each test so this
    file's registrations never leak into other test modules collected later
    in the same pytest session (same discipline as
    ``test_composite_auth_chain.py``)."""
    snapshot = dict(_provider_module._REGISTRY)
    yield
    _provider_module._REGISTRY.clear()
    _provider_module._REGISTRY.update(snapshot)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _set_foundry_overrides(paths: FoundryPaths, overrides: dict) -> None:
    """Merge *overrides* into the ``foundry:`` block of ``foundry.yaml``."""
    existing: dict = load_yaml(paths.foundry_yaml) or {}
    if "foundry" not in existing or not isinstance(existing.get("foundry"), dict):
        existing["foundry"] = {}
    for key, value in overrides.items():
        existing["foundry"][key] = value
    dump_yaml(existing, paths.foundry_yaml)


def _write_accepted_audit(tmp_path: Path) -> Path:
    audit_path = tmp_path / "di1-audit-e2e.md"
    audit_path.write_text("---\nstatus: accepted\n---\n\nbody\n", encoding="utf-8")
    return audit_path


def _configure_multi_user(tmp_foundry: FoundryPaths, tmp_path: Path) -> FoundryConfig:
    """Build a ``multi_user`` config with the DI-1 gate satisfied and a
    ``local_static`` owner caller wired in -- no default service account
    bound yet (that id doesn't exist until the admin API creates it)."""
    audit_path = _write_accepted_audit(tmp_path)
    auth_block = {
        "provider": "local_static",
        "local_static": {
            "tokens": [
                {
                    "token_env": _OWNER_TOKEN_ENV,
                    "user_id": _OWNER_USER_ID,
                    "workspace_id": _WORKSPACE_ID,
                    "roles": ["owner"],
                }
            ]
        },
        "di1_audit_acknowledged": True,
        "di1_audit_report_path": str(audit_path),
    }
    _set_foundry_overrides(
        tmp_foundry,
        {
            "deployment_mode": "multi_user",
            "auth": auth_block,
            "agents": {"enabled": True},
        },
    )
    return FoundryConfig(paths=tmp_foundry)


def _bind_default_service_account(paths: FoundryPaths, service_account_id: str) -> None:
    """Set ``agents.default_service_account_id`` after the SA already exists.

    ``AgentJobService``/``AgentJobService.create_job`` construct a fresh
    ``FoundryConfig`` per call (see ``agent_job_service.py``), so mutating
    this file takes effect on the very next request against the SAME running
    app/TestClient -- no app rebuild required.
    """
    existing: dict = load_yaml(paths.foundry_yaml) or {}
    existing.setdefault("foundry", {})
    agents_block = dict(existing["foundry"].get("agents") or {})
    agents_block["default_service_account_id"] = service_account_id
    existing["foundry"]["agents"] = agents_block
    dump_yaml(existing, paths.foundry_yaml)


def _mock_popen() -> MagicMock:
    proc = MagicMock()
    proc.pid = 99999
    proc.poll.return_value = 0
    proc.wait.return_value = 0
    return proc


def _launch_job_via_http(
    client: TestClient, headers: dict, *, created_by: str
) -> dict:
    """Launch an agent job through the REAL HTTP path (governance guard +
    subprocess spawn mocked, matching ``test_agent_jobs_api.py``'s
    established pattern -- this file only cares that identity binding
    survives the full round trip, not agent-job spawn mechanics)."""
    body = {
        "provider": "claude_agent_sdk",
        "model_profile": "rf_synthesize_deep",
        "request_kind": "research",
        "policy_snapshot": dict(_MINIMAL_POLICY_SNAPSHOT),
        "project_id": "e2e-project",
        "workspace_id": _WORKSPACE_ID,
        "created_by": created_by,
    }
    with (
        patch(
            "research_foundry.services.agent_job_service.subprocess.Popen",
            return_value=_mock_popen(),
        ),
        patch(
            "research_foundry.services.agent_job_service.importlib.util.find_spec",
            return_value=MagicMock(),
        ),
    ):
        resp = client.post("/api/agent-jobs", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# The single end-to-end test
# ---------------------------------------------------------------------------


class TestFullMultiUserActivationLifecycleE2E:
    def test_gate_issue_authenticate_launch_bind_revoke_round_trip(
        self, tmp_foundry: FoundryPaths, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        owner_token = secrets.token_urlsafe(24)
        monkeypatch.setenv(_OWNER_TOKEN_ENV, owner_token)

        config = _configure_multi_user(tmp_foundry, tmp_path)

        # 1. The DI-1 gate passes and the app boots under multi_user.
        app = create_app(config)
        app.dependency_overrides[get_paths] = lambda: config.paths
        client = TestClient(app, raise_server_exceptions=True)
        assert app.state.rbac_enforced is True

        owner_headers = {"Authorization": f"Bearer {owner_token}"}

        # 2. Owner issues a service account + its access token via the REAL
        #    admin API (ACT-301) -- authenticated by the provider adapter,
        #    never the token store (no token exists for this caller).
        sa_create_resp = client.post(
            "/api/admin/service-accounts",
            json={"name": "e2e-service-account", "role": "researcher"},
            headers=owner_headers,
        )
        assert sa_create_resp.status_code == 201, sa_create_resp.text
        sa_id = sa_create_resp.json()["id"]
        assert "plaintext" not in sa_create_resp.json()

        sa_token_resp = client.post(
            f"/api/admin/service-accounts/{sa_id}/tokens", headers=owner_headers
        )
        assert sa_token_resp.status_code == 201, sa_token_resp.text
        sa_token_body = sa_token_resp.json()
        sa_plaintext = sa_token_body["plaintext"]
        sa_token_id = sa_token_body["token_id"]
        assert sa_plaintext

        # Bind the SA as this workspace's default execution identity for
        # multi_user agent jobs (ACT-204, FR-12) -- picked up live on the
        # next request against the SAME running app (see helper docstring).
        _bind_default_service_account(config.paths, sa_id)

        # 3. Authenticate a DIFFERENT request with the SA's own token: the
        #    composite auth chain (ACT-203) resolves it from the token
        #    store, not the local_static provider.
        identity_resp = client.get(
            "/api/auth/identity",
            headers={"Authorization": f"Bearer {sa_plaintext}"},
        )
        assert identity_resp.status_code == 200
        identity_body = identity_resp.json()
        assert identity_body["user_id"] == sa_id
        assert identity_body["workspace_id"] == _WORKSPACE_ID
        assert "researcher" in identity_body["roles"]

        # 4. Launch an agent job through the real HTTP path (owner-authorized
        #    caller; a distinct human "triggering" identity in the body) and
        #    confirm it binds to the SA's EXECUTING identity.
        job = _launch_job_via_http(
            client, owner_headers, created_by="human_caller_alice"
        )
        assert job["created_by"] == sa_id, (
            "agent job must persist the SA EXECUTING identity, not the "
            "triggering human caller, under multi_user (ACT-204, FR-12)"
        )

        audit_resp = client.get(
            "/api/audit",
            params={"mutation_type": "agent_job_launched", "limit": 50},
            headers=owner_headers,
        )
        assert audit_resp.status_code == 200
        binding_events = [
            e
            for e in audit_resp.json()["items"]
            if e["target_ref"] == job["agent_job_id"]
            and e.get("action") == "agent_job_create"
        ]
        assert len(binding_events) == 1, (
            f"expected exactly one ACT-204 binding audit row for {job['agent_job_id']!r}"
        )
        event = binding_events[0]
        assert event["actor_user_id"] == sa_id
        assert event["policy_snapshot"]["triggering_identity"] == "human_caller_alice"
        assert event["policy_snapshot"]["executing_identity"] == sa_id
        assert event["policy_snapshot"]["deployment_mode"] == "multi_user"

        # 5. Revoke the SA token via the admin API -- immediate effect
        #    (FR-10), no restart required.
        revoke_resp = client.delete(
            f"/api/admin/service-accounts/{sa_id}/tokens/{sa_token_id}",
            headers=owner_headers,
        )
        assert revoke_resp.status_code == 200
        assert revoke_resp.json() == {"token_id": sa_token_id, "revoked": True}

        post_revoke_resp = client.get(
            "/api/auth/identity",
            headers={"Authorization": f"Bearer {sa_plaintext}"},
        )
        assert post_revoke_resp.status_code == 401

    def test_single_user_operates_with_zero_di1_or_sa_state(
        self, tmp_foundry: FoundryPaths
    ) -> None:
        """FR-2: ``single_user`` needs NONE of the above -- no ack, no audit
        artifact, no service account, no bearer credential at all -- and the
        agent-job identity-binding rewrite never activates."""
        _set_foundry_overrides(
            tmp_foundry,
            {
                "deployment_mode": "single_user",
                "auth": {"provider": "none"},
                "agents": {"enabled": True},
            },
        )
        config = FoundryConfig(paths=tmp_foundry)

        app = create_app(config)  # must not raise -- no DI-1 state configured
        app.dependency_overrides[get_paths] = lambda: config.paths
        client = TestClient(app, raise_server_exceptions=True)

        assert config.di1_audit_acknowledged() is False
        assert client.get("/health").status_code == 200

        # provider=none -> no auth middleware at all -> single-operator-trust
        # (require_role passes unconditionally) -- reachable with no credential.
        job = _launch_job_via_http(client, headers={}, created_by="human_caller_bob")
        assert job["created_by"] == "human_caller_bob", (
            "single_user must never rewrite created_by to a service account"
        )

        events = audit_service.list_events(config.paths, mutation_type="agent_job_launched")
        binding_events = [
            e for e in events["items"] if e.get("action") == "agent_job_create"
        ]
        assert binding_events == [], (
            "the ACT-204 SA-binding audit row must never be written under single_user"
        )


# ---------------------------------------------------------------------------
# Success metric (PRD Success Metrics / plan Success Metrics, ACT-601):
# "100% of agent_jobs launched while deployment_mode=multi_user resolve to a
# service-account execution identity in the audit log."
# ---------------------------------------------------------------------------


class TestSuccessMetricAllMultiUserAgentJobsResolveToServiceAccountIdentity:
    def test_every_job_launched_under_multi_user_binds_to_sa_identity(
        self, tmp_foundry: FoundryPaths, tmp_path: Path
    ) -> None:
        """A batch of jobs, triggered by DIFFERENT human callers, ALL resolve
        to the SAME configured SA execution identity -- 0 exceptions, not
        just "usually" or "the happy path"."""
        config = _configure_multi_user(tmp_foundry, tmp_path)
        # No admin-API round trip needed for this metric check -- the SA
        # itself is seeded directly (its issuance mechanics are already
        # covered end-to-end above); this test's whole point is the
        # binding rate across many jobs launched via the service layer,
        # which is what AgentJobService.create_job's ACT-204 branch governs.
        sa_id = "svc_e2e_metric_researcher"
        conn = rbac_store.bootstrap(config.paths)
        try:
            rbac_store.upsert_workspace(conn, _WORKSPACE_ID, "Default")
            rbac_store.create_service_account(
                conn,
                service_account_id=sa_id,
                name="Metric Verification Service Account",
                workspace_id=_WORKSPACE_ID,
                role="researcher",
                created_by="test-harness",
            )
        finally:
            conn.close()
        _bind_default_service_account(config.paths, sa_id)

        service = AgentJobService(config.paths)
        triggering_callers = [
            "human_caller_alice",
            "human_caller_bob",
            None,
            "static_token_caller_ci",
        ]
        job_ids = [
            service.create_job(
                provider="claude_agent_sdk",
                model_profile="rf_synthesize_deep",
                request_kind="research",
                policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
                project_id="metric-project",
                workspace_id=_WORKSPACE_ID,
                created_by=caller,
            ).agent_job_id
            for caller in triggering_callers
        ]

        events = audit_service.list_events(config.paths, mutation_type="agent_job_launched")
        binding_by_job = {
            e["target_ref"]: e
            for e in events["items"]
            if e.get("action") == "agent_job_create"
        }

        assert set(binding_by_job) == set(job_ids), (
            "every job launched under multi_user must have exactly one "
            "ACT-204 binding audit row -- 100%, not a subset"
        )
        for job_id, caller in zip(job_ids, triggering_callers, strict=True):
            event = binding_by_job[job_id]
            assert event["actor_user_id"] == sa_id
            assert event["policy_snapshot"]["executing_identity"] == sa_id
            assert event["policy_snapshot"]["triggering_identity"] == caller
            assert event["policy_snapshot"]["deployment_mode"] == "multi_user"

        # And the persisted job records themselves (not just the audit
        # trail) all carry the SA as created_by -- the actual execution
        # identity the job runs under, not merely an audit annotation.
        for job_id in job_ids:
            loaded = service.load_job(job_id)
            assert loaded.created_by == sa_id
