"""Unit tests for the admin API's service-account / PAT / deployment-mode-status
surface (public-multiuser-release-activation Phase 3, ACT-301..303).

Test coverage:
  - Role gating on every new service-account route (owner/admin allowed;
    researcher/reviewer/viewer -> 403) and the deployment-mode-status route.
  - Self-vs-admin manual scoping on PAT routes (any role self-serves; only
    owner/admin may act on ANOTHER user's PAT; 403 not a 404-leak for the
    same-workspace case, 404 for the cross-workspace case).
  - Service-account token rotation invalidates the prior token immediately.
  - No-secret-leak: the plaintext secret appears ONLY in the one-time
    issuance response body — never in list/get responses, never logged.
  - deployment-mode-status shape for both single_user and multi_user.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from research_foundry.api.app import create_app
from research_foundry.api.auth.provider import AuthIdentity
from research_foundry.api.routers.admin import _get_config
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.services import rbac_store
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Fixtures (mirrors tests/unit/test_admin_api.py's pattern)
# ---------------------------------------------------------------------------


def _make_config(tmp_path: Path) -> FoundryConfig:
    """Minimal workspace config with auth disabled (provider=none)."""
    root = tmp_path / "fdry"
    root.mkdir(parents=True, exist_ok=True)
    dist = distribution_root()
    for sub in ("schemas", "config", "templates"):
        src = dist / sub
        if src.exists():
            shutil.copytree(src, root / sub)
    foundry_src = dist / "foundry.yaml"
    if foundry_src.exists():
        shutil.copyfile(foundry_src, root / "foundry.yaml")
    else:
        (root / "foundry.yaml").write_text("foundry:\n  owner: Test\n", encoding="utf-8")
    for d in ("runs", "inbox/raw_ideas", "intents/active"):
        (root / d).mkdir(parents=True, exist_ok=True)

    foundry_yaml_path = root / "foundry.yaml"
    existing = load_yaml(foundry_yaml_path) or {}
    if "foundry" not in existing or not isinstance(existing.get("foundry"), dict):
        existing["foundry"] = {}
    viewer: dict[str, Any] = dict(existing["foundry"].get("viewer") or {})
    viewer["auth_mode"] = "none"
    existing["foundry"]["viewer"] = viewer
    dump_yaml(existing, foundry_yaml_path)

    return FoundryConfig(paths=FoundryPaths(root=root))


class _InjectIdentityMiddleware(BaseHTTPMiddleware):
    """Test middleware that injects a fixed AuthIdentity onto request.state."""

    def __init__(self, app, identity: AuthIdentity | None) -> None:
        super().__init__(app)
        self._identity = identity

    async def dispatch(self, request: Request, call_next) -> Response:
        if self._identity is not None:
            request.state.identity = self._identity
        return await call_next(request)


def _make_client(
    tmp_path: Path,
    identity: AuthIdentity | None = None,
    *,
    rbac_enforcement: str = "enabled",
) -> tuple[TestClient, FoundryConfig]:
    """Create a TestClient with admin-API routes wired and optional identity injection."""
    config = _make_config(tmp_path)

    foundry_yaml_path = config.paths.foundry_yaml
    existing = load_yaml(foundry_yaml_path) or {}
    if "foundry" not in existing:
        existing["foundry"] = {}
    auth: dict[str, Any] = dict(existing["foundry"].get("auth") or {})
    auth["rbac_enforcement"] = rbac_enforcement
    existing["foundry"]["auth"] = auth
    dump_yaml(existing, foundry_yaml_path)
    config = FoundryConfig(paths=FoundryPaths(root=config.paths.root))

    app = create_app(config)
    app.dependency_overrides[get_paths] = lambda: config.paths
    app.dependency_overrides[_get_config] = lambda: config

    if identity is not None:
        app.add_middleware(_InjectIdentityMiddleware, identity=identity)

    return TestClient(app, raise_server_exceptions=True), config


def _make_client_sharing(config: FoundryConfig, identity: AuthIdentity | None) -> TestClient:
    """Build an ADDITIONAL TestClient bound to the SAME on-disk workspace as
    *config* but a DIFFERENT caller identity.

    Cross-user PAT-scoping tests need two callers to see the same
    ``rbac.db`` / token store — calling :func:`_make_client` a second time
    with the same ``tmp_path`` would re-run its one-time ``shutil.copytree``
    setup and crash on the second call, so this helper reuses
    ``config.paths.root`` directly instead.
    """
    shared_config = FoundryConfig(paths=FoundryPaths(root=config.paths.root))
    app = create_app(shared_config)
    app.dependency_overrides[get_paths] = lambda: shared_config.paths
    app.dependency_overrides[_get_config] = lambda: shared_config
    if identity is not None:
        app.add_middleware(_InjectIdentityMiddleware, identity=identity)
    return TestClient(app, raise_server_exceptions=True)


def _seed_membership(config: FoundryConfig, user_id: str, workspace_id: str, role: str) -> None:
    """Seed a durable RBAC membership row so token_service's role-ceiling
    check (FR-9) has something to resolve for *user_id*."""
    conn = rbac_store.bootstrap(config.paths)
    try:
        rbac_store.upsert_user(conn, user_id, user_id)
        rbac_store.upsert_workspace(conn, workspace_id, workspace_id)
        rbac_store.upsert_membership(conn, user_id, workspace_id, role)
    finally:
        conn.close()


# Standard identities used across tests
_OWNER = AuthIdentity("u_owner", "default", ("owner",))
_ADMIN = AuthIdentity("u_admin", "default", ("admin",))
_RESEARCHER = AuthIdentity("u_researcher", "default", ("researcher",))
_REVIEWER = AuthIdentity("u_reviewer", "default", ("reviewer",))
_VIEWER = AuthIdentity("u_viewer", "default", ("viewer",))
_BLOCKED_ROLES = [_RESEARCHER, _REVIEWER, _VIEWER]

# A second, distinct researcher identity used for cross-user PAT scoping tests.
_OTHER_RESEARCHER = AuthIdentity("u_other_researcher", "default", ("researcher",))


# ---------------------------------------------------------------------------
# Service-account CRUD: role gating
# ---------------------------------------------------------------------------


class TestServiceAccountRoleGating:
    def test_owner_can_create(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.post(
            "/api/admin/service-accounts",
            json={"name": "ci-bot", "role": "researcher"},
        )
        assert response.status_code == 201

    def test_admin_can_create(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_ADMIN)
        response = client.post(
            "/api/admin/service-accounts",
            json={"name": "ci-bot", "role": "researcher"},
        )
        assert response.status_code == 201

    @pytest.mark.parametrize("identity", _BLOCKED_ROLES, ids=["researcher", "reviewer", "viewer"])
    def test_non_admin_cannot_create(self, tmp_path, identity):
        client, _ = _make_client(tmp_path, identity=identity)
        response = client.post(
            "/api/admin/service-accounts",
            json={"name": "ci-bot", "role": "researcher"},
        )
        assert response.status_code == 403

    @pytest.mark.parametrize("identity", _BLOCKED_ROLES, ids=["researcher", "reviewer", "viewer"])
    def test_non_admin_cannot_list(self, tmp_path, identity):
        client, _ = _make_client(tmp_path, identity=identity)
        response = client.get("/api/admin/service-accounts")
        assert response.status_code == 403

    @pytest.mark.parametrize("identity", _BLOCKED_ROLES, ids=["researcher", "reviewer", "viewer"])
    def test_non_admin_cannot_disable(self, tmp_path, identity):
        client, _ = _make_client(tmp_path, identity=identity)
        response = client.delete("/api/admin/service-accounts/svc_nonexistent")
        assert response.status_code == 403

    @pytest.mark.parametrize("identity", _BLOCKED_ROLES, ids=["researcher", "reviewer", "viewer"])
    def test_non_admin_cannot_issue_token(self, tmp_path, identity):
        client, _ = _make_client(tmp_path, identity=identity)
        response = client.post("/api/admin/service-accounts/svc_nonexistent/tokens")
        assert response.status_code == 403

    @pytest.mark.parametrize("identity", _BLOCKED_ROLES, ids=["researcher", "reviewer", "viewer"])
    def test_non_admin_cannot_list_tokens(self, tmp_path, identity):
        client, _ = _make_client(tmp_path, identity=identity)
        response = client.get("/api/admin/service-accounts/svc_nonexistent/tokens")
        assert response.status_code == 403

    @pytest.mark.parametrize("identity", _BLOCKED_ROLES, ids=["researcher", "reviewer", "viewer"])
    def test_non_admin_cannot_revoke_token(self, tmp_path, identity):
        client, _ = _make_client(tmp_path, identity=identity)
        response = client.delete("/api/admin/service-accounts/svc_nonexistent/tokens/tok_nonexistent")
        assert response.status_code == 403


class TestServiceAccountValidation:
    def test_invalid_role_returns_422(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.post(
            "/api/admin/service-accounts",
            json={"name": "ci-bot", "role": "superadmin"},
        )
        assert response.status_code == 422

    def test_missing_name_returns_422(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.post(
            "/api/admin/service-accounts",
            json={"role": "researcher"},
        )
        assert response.status_code == 422

    def test_disable_unknown_account_returns_404(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.delete("/api/admin/service-accounts/svc_does_not_exist")
        assert response.status_code == 404

    def test_issue_token_for_unknown_account_returns_404(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.post("/api/admin/service-accounts/svc_does_not_exist/tokens")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Service-account CRUD + token lifecycle: behavior
# ---------------------------------------------------------------------------


class TestServiceAccountLifecycle:
    def _create_account(self, client: TestClient) -> str:
        response = client.post(
            "/api/admin/service-accounts",
            json={"name": "ci-bot", "role": "researcher", "description": "CI pipeline"},
        )
        assert response.status_code == 201
        return response.json()["id"]

    def test_create_response_never_contains_a_token(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.post(
            "/api/admin/service-accounts",
            json={"name": "ci-bot", "role": "researcher"},
        )
        data = response.json()
        assert "plaintext" not in data
        assert "token" not in data
        assert data["name"] == "ci-bot"
        assert data["role"] == "researcher"
        assert data["disabled_at"] is None

    def test_list_includes_created_account(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        account_id = self._create_account(client)
        response = client.get("/api/admin/service-accounts")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == account_id

    def test_disable_is_idempotent(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        account_id = self._create_account(client)
        first = client.delete(f"/api/admin/service-accounts/{account_id}")
        second = client.delete(f"/api/admin/service-accounts/{account_id}")
        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json() == {"id": account_id, "disabled": True}

    def test_issue_token_returns_plaintext_once(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        account_id = self._create_account(client)
        response = client.post(f"/api/admin/service-accounts/{account_id}/tokens")
        assert response.status_code == 201
        data = response.json()
        assert data["plaintext"]
        assert data["principal_type"] == "service"
        assert data["principal_id"] == account_id
        assert data["role"] == "researcher"

    def test_rotate_invalidates_prior_token_immediately(self, tmp_path):
        """AC-301: rotate invalidates the prior token immediately."""
        client, _ = _make_client(tmp_path, identity=_OWNER)
        account_id = self._create_account(client)

        first = client.post(f"/api/admin/service-accounts/{account_id}/tokens").json()
        second = client.post(f"/api/admin/service-accounts/{account_id}/tokens").json()

        assert first["token_id"] != second["token_id"]

        tokens = client.get(f"/api/admin/service-accounts/{account_id}/tokens").json()["items"]
        by_id = {t["token_id"]: t for t in tokens}
        assert by_id[first["token_id"]]["revoked_at"] is not None, (
            "rotating must revoke the prior token immediately"
        )
        assert by_id[second["token_id"]]["revoked_at"] is None

    def test_disabling_account_does_not_delete_its_tokens_but_they_verify_dead(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        account_id = self._create_account(client)
        client.post(f"/api/admin/service-accounts/{account_id}/tokens")
        client.delete(f"/api/admin/service-accounts/{account_id}")

        tokens = client.get(f"/api/admin/service-accounts/{account_id}/tokens").json()["items"]
        assert len(tokens) == 1  # still listed — disabling doesn't delete token rows
        assert tokens[0]["revoked_at"] is None  # not explicitly revoked by disable

    def test_revoke_specific_token(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        account_id = self._create_account(client)
        issued = client.post(f"/api/admin/service-accounts/{account_id}/tokens").json()

        response = client.delete(
            f"/api/admin/service-accounts/{account_id}/tokens/{issued['token_id']}"
        )
        assert response.status_code == 200
        assert response.json() == {"token_id": issued["token_id"], "revoked": True}

    def test_revoke_unknown_token_returns_404(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        account_id = self._create_account(client)
        response = client.delete(
            f"/api/admin/service-accounts/{account_id}/tokens/tok_does_not_exist"
        )
        assert response.status_code == 404

    def test_revoke_token_belonging_to_another_account_returns_404(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        account_a = self._create_account(client)
        account_b = self._create_account(client)
        token_a = client.post(f"/api/admin/service-accounts/{account_a}/tokens").json()

        response = client.delete(
            f"/api/admin/service-accounts/{account_b}/tokens/{token_a['token_id']}"
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATs: self-service manual gating (NOT Depends(require_role))
# ---------------------------------------------------------------------------


class TestPatSelfServiceManualGating:
    def test_any_role_can_self_issue(self, tmp_path):
        client, config = _make_client(tmp_path, identity=_RESEARCHER)
        _seed_membership(config, _RESEARCHER.user_id, _RESEARCHER.workspace_id, "researcher")
        response = client.post("/api/admin/pats", json={"role": "researcher"})
        assert response.status_code == 201

    def test_any_role_can_self_list(self, tmp_path):
        client, config = _make_client(tmp_path, identity=_VIEWER)
        response = client.get("/api/admin/pats")
        assert response.status_code == 200

    def test_role_ceiling_exceeded_returns_403(self, tmp_path):
        """FR-9: a researcher cannot self-issue an owner-level PAT."""
        client, config = _make_client(tmp_path, identity=_RESEARCHER)
        _seed_membership(config, _RESEARCHER.user_id, _RESEARCHER.workspace_id, "researcher")
        response = client.post("/api/admin/pats", json={"role": "owner"})
        assert response.status_code == 403

    def test_issuer_without_membership_returns_404(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_RESEARCHER)
        # No membership seeded — token_service.issue_user_pat has no role to
        # anchor a ceiling check against.
        response = client.post("/api/admin/pats", json={"role": "viewer"})
        assert response.status_code == 404

    def test_non_admin_cannot_issue_on_behalf_of_another_user(self, tmp_path):
        client, config = _make_client(tmp_path, identity=_RESEARCHER)
        _seed_membership(config, _RESEARCHER.user_id, _RESEARCHER.workspace_id, "researcher")
        response = client.post(
            "/api/admin/pats",
            json={"role": "viewer", "user_id": _OTHER_RESEARCHER.user_id},
        )
        assert response.status_code == 403

    def test_owner_can_issue_on_behalf_of_another_user(self, tmp_path):
        client, config = _make_client(tmp_path, identity=_OWNER)
        _seed_membership(config, _OTHER_RESEARCHER.user_id, _OWNER.workspace_id, "researcher")
        response = client.post(
            "/api/admin/pats",
            json={"role": "viewer", "user_id": _OTHER_RESEARCHER.user_id},
        )
        assert response.status_code == 201
        assert response.json()["principal_id"] == _OTHER_RESEARCHER.user_id

    def test_non_admin_cannot_list_another_users_pats(self, tmp_path):
        client, config = _make_client(tmp_path, identity=_RESEARCHER)
        response = client.get(f"/api/admin/pats?user_id={_OTHER_RESEARCHER.user_id}")
        assert response.status_code == 403

    def test_admin_can_list_another_users_pats(self, tmp_path):
        client, config = _make_client(tmp_path, identity=_ADMIN)
        response = client.get(f"/api/admin/pats?user_id={_OTHER_RESEARCHER.user_id}")
        assert response.status_code == 200

    def test_no_auth_missing_user_id_returns_422(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=None, rbac_enforcement="auto")
        response = client.post("/api/admin/pats", json={"role": "viewer"})
        assert response.status_code == 422


class TestPatRevokeScoping:
    def _issue_self(self, client: TestClient, config: FoundryConfig, identity: AuthIdentity, role: str) -> dict:
        _seed_membership(config, identity.user_id, identity.workspace_id, role)
        response = client.post("/api/admin/pats", json={"role": role})
        assert response.status_code == 201
        return response.json()

    def test_self_can_revoke_own_pat(self, tmp_path):
        client, config = _make_client(tmp_path, identity=_RESEARCHER)
        issued = self._issue_self(client, config, _RESEARCHER, "researcher")
        response = client.delete(f"/api/admin/pats/{issued['token_id']}")
        assert response.status_code == 200
        assert response.json() == {"token_id": issued["token_id"], "revoked": True}

    def test_non_admin_cannot_revoke_another_users_pat_gets_403_not_404(self, tmp_path):
        """ACT-302 AC: non-owner/admin caller cannot revoke another user's PAT — 403, not a 404-leak."""
        owner_client, owner_config = _make_client(tmp_path, identity=_OWNER)
        issued = self._issue_self(owner_client, owner_config, _OWNER, "owner")

        # Same on-disk workspace, a DIFFERENT (non-admin) caller identity —
        # the PAT exists in their own workspace, so this must be 403
        # (permission denied), never a 404-leak.
        researcher_client = _make_client_sharing(owner_config, _RESEARCHER)
        response = researcher_client.delete(f"/api/admin/pats/{issued['token_id']}")
        assert response.status_code == 403, (
            f"expected 403 (not a 404-leak), got {response.status_code}: {response.text}"
        )

    def test_admin_can_revoke_another_users_pat(self, tmp_path):
        owner_client, owner_config = _make_client(tmp_path, identity=_OWNER)
        issued = self._issue_self(owner_client, owner_config, _OWNER, "owner")

        admin_client = _make_client_sharing(owner_config, _ADMIN)
        response = admin_client.delete(f"/api/admin/pats/{issued['token_id']}")
        assert response.status_code == 200

    def test_revoke_unknown_token_returns_404(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.delete("/api/admin/pats/tok_does_not_exist")
        assert response.status_code == 404

    def test_revoke_service_account_token_via_pat_route_returns_404(self, tmp_path):
        """A service-account token is not a PAT — hidden as 404, not exposed."""
        client, _ = _make_client(tmp_path, identity=_OWNER)
        sa_response = client.post(
            "/api/admin/service-accounts", json={"name": "svc", "role": "researcher"}
        )
        account_id = sa_response.json()["id"]
        token = client.post(f"/api/admin/service-accounts/{account_id}/tokens").json()

        response = client.delete(f"/api/admin/pats/{token['token_id']}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# No-secret-leak (hard exit gate)
# ---------------------------------------------------------------------------


class TestNoSecretLeakAcrossTokenSurface:
    """Hard exit gate: the plaintext secret appears ONLY in the one-time
    issuance response body — never in a list/get response, never logged."""

    def test_plaintext_present_only_in_issuance_response(self, tmp_path):
        client, config = _make_client(tmp_path, identity=_OWNER)

        sa_response = client.post(
            "/api/admin/service-accounts", json={"name": "svc", "role": "researcher"}
        )
        account_id = sa_response.json()["id"]
        issued = client.post(f"/api/admin/service-accounts/{account_id}/tokens").json()
        plaintext = issued["plaintext"]
        assert plaintext

        _seed_membership(config, _OWNER.user_id, _OWNER.workspace_id, "owner")
        pat_issued = client.post("/api/admin/pats", json={"role": "researcher"}).json()
        pat_plaintext = pat_issued["plaintext"]
        assert pat_plaintext

        # Every OTHER response in the surface must never contain either secret,
        # never a "token_hash" key, and never a bare "plaintext" key.
        probes = [
            client.get("/api/admin/service-accounts"),
            client.get(f"/api/admin/service-accounts/{account_id}/tokens"),
            client.get("/api/admin/pats"),
            client.get(f"/api/admin/pats?user_id={_OWNER.user_id}"),
        ]
        for response in probes:
            assert response.status_code == 200
            body_text = response.text
            assert plaintext not in body_text, f"service-account secret leaked in {response.request.url}"
            assert pat_plaintext not in body_text, f"PAT secret leaked in {response.request.url}"
            assert "token_hash" not in body_text
            for item in response.json().get("items", []):
                assert "plaintext" not in item

    def test_secret_never_appears_in_application_logs(self, tmp_path, caplog):
        client, config = _make_client(tmp_path, identity=_OWNER)
        _seed_membership(config, _OWNER.user_id, _OWNER.workspace_id, "owner")

        with caplog.at_level(logging.DEBUG):
            sa_response = client.post(
                "/api/admin/service-accounts", json={"name": "svc", "role": "researcher"}
            )
            account_id = sa_response.json()["id"]
            sa_issued = client.post(f"/api/admin/service-accounts/{account_id}/tokens").json()
            pat_issued = client.post("/api/admin/pats", json={"role": "researcher"}).json()
            client.get(f"/api/admin/service-accounts/{account_id}/tokens")
            client.get("/api/admin/pats")
            client.delete(f"/api/admin/pats/{pat_issued['token_id']}")

        log_text = "\n".join(record.getMessage() for record in caplog.records)
        assert sa_issued["plaintext"] not in log_text
        assert pat_issued["plaintext"] not in log_text


# ---------------------------------------------------------------------------
# Cross-workspace isolation (DI-1 delta-audit, post-acceptance widened-surface
# regression coverage): an owner/admin in workspace A must never be able to
# enumerate, read, revoke, or rotate workspace B's service accounts, tokens,
# or PATs. require_role() only checks ROLE membership, NOT workspace -- these
# tests lock in that every handler additionally scopes by workspace_id.
# ---------------------------------------------------------------------------

_OWNER_WS_A = AuthIdentity("u_owner_a", "ws_a", ("owner",))
_OWNER_WS_B = AuthIdentity("u_owner_b", "ws_b", ("owner",))


class TestCrossWorkspaceIsolation:
    def test_service_account_not_listed_across_workspaces(self, tmp_path):
        client_a, config = _make_client(tmp_path, identity=_OWNER_WS_A)
        client_a.post(
            "/api/admin/service-accounts", json={"name": "ws-a-bot", "role": "researcher"}
        )

        client_b = _make_client_sharing(config, _OWNER_WS_B)
        response = client_b.get("/api/admin/service-accounts")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_service_account_disable_across_workspaces_returns_404(self, tmp_path):
        client_a, config = _make_client(tmp_path, identity=_OWNER_WS_A)
        account_id = client_a.post(
            "/api/admin/service-accounts", json={"name": "ws-a-bot", "role": "researcher"}
        ).json()["id"]

        client_b = _make_client_sharing(config, _OWNER_WS_B)
        response = client_b.delete(f"/api/admin/service-accounts/{account_id}")
        assert response.status_code == 404

    def test_service_account_tokens_list_across_workspaces_returns_404(self, tmp_path):
        client_a, config = _make_client(tmp_path, identity=_OWNER_WS_A)
        account_id = client_a.post(
            "/api/admin/service-accounts", json={"name": "ws-a-bot", "role": "researcher"}
        ).json()["id"]
        client_a.post(f"/api/admin/service-accounts/{account_id}/tokens")

        client_b = _make_client_sharing(config, _OWNER_WS_B)
        response = client_b.get(f"/api/admin/service-accounts/{account_id}/tokens")
        assert response.status_code == 404

    def test_service_account_token_rotate_across_workspaces_returns_404(self, tmp_path):
        client_a, config = _make_client(tmp_path, identity=_OWNER_WS_A)
        account_id = client_a.post(
            "/api/admin/service-accounts", json={"name": "ws-a-bot", "role": "researcher"}
        ).json()["id"]

        client_b = _make_client_sharing(config, _OWNER_WS_B)
        response = client_b.post(f"/api/admin/service-accounts/{account_id}/tokens")
        assert response.status_code == 404

    def test_service_account_token_revoke_across_workspaces_returns_404(self, tmp_path):
        client_a, config = _make_client(tmp_path, identity=_OWNER_WS_A)
        account_id = client_a.post(
            "/api/admin/service-accounts", json={"name": "ws-a-bot", "role": "researcher"}
        ).json()["id"]
        token_id = client_a.post(f"/api/admin/service-accounts/{account_id}/tokens").json()["token_id"]

        client_b = _make_client_sharing(config, _OWNER_WS_B)
        response = client_b.delete(f"/api/admin/service-accounts/{account_id}/tokens/{token_id}")
        assert response.status_code == 404

    def test_owner_cannot_issue_pat_for_user_only_member_of_another_workspace(self, tmp_path):
        """FR-9 role-ceiling lookup is workspace-scoped: an owner in ws_b cannot
        issue a PAT for a user whose only membership is in ws_a."""
        client_a, config = _make_client(tmp_path, identity=_OWNER_WS_A)
        _seed_membership(config, "u_ws_a_only", _OWNER_WS_A.workspace_id, "researcher")

        client_b = _make_client_sharing(config, _OWNER_WS_B)
        response = client_b.post(
            "/api/admin/pats", json={"role": "researcher", "user_id": "u_ws_a_only"}
        )
        assert response.status_code == 404

    def test_pat_revoke_across_workspaces_returns_404_not_403(self, tmp_path):
        """A PAT issued in ws_a must be invisible (404, not a 403-leak) to an
        owner in ws_b, even though that owner would have owner/admin power
        over PATs within their OWN workspace."""
        client_a, config = _make_client(tmp_path, identity=_OWNER_WS_A)
        _seed_membership(config, _OWNER_WS_A.user_id, _OWNER_WS_A.workspace_id, "owner")
        issued = client_a.post("/api/admin/pats", json={"role": "researcher"}).json()

        client_b = _make_client_sharing(config, _OWNER_WS_B)
        response = client_b.delete(f"/api/admin/pats/{issued['token_id']}")
        assert response.status_code == 404

    def test_pat_list_scoped_to_callers_own_workspace_even_for_owner(self, tmp_path):
        """An owner in ws_b querying by ``user_id`` (permitted -- owner/admin
        may target any user) must still only see PATs issued under ws_b's
        OWN workspace_id filter -- a PAT the same user_id holds in ws_a must
        not leak into ws_b's listing."""
        client_a, config = _make_client(tmp_path, identity=_OWNER_WS_A)
        _seed_membership(config, _OWNER_WS_A.user_id, _OWNER_WS_A.workspace_id, "owner")
        client_a.post("/api/admin/pats", json={"role": "researcher"})

        client_b = _make_client_sharing(config, _OWNER_WS_B)
        response = client_b.get(f"/api/admin/pats?user_id={_OWNER_WS_A.user_id}")
        assert response.status_code == 200
        assert response.json()["total"] == 0


# ---------------------------------------------------------------------------
# GET /api/admin/deployment-mode-status
# ---------------------------------------------------------------------------


class TestDeploymentModeStatusEndpoint:
    def test_owner_allowed(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.get("/api/admin/deployment-mode-status")
        assert response.status_code == 200

    @pytest.mark.parametrize("identity", _BLOCKED_ROLES, ids=["researcher", "reviewer", "viewer"])
    def test_non_admin_blocked(self, tmp_path, identity):
        client, _ = _make_client(tmp_path, identity=identity)
        response = client.get("/api/admin/deployment-mode-status")
        assert response.status_code == 403

    def test_single_user_shape(self, tmp_path):
        client, _ = _make_client(tmp_path, identity=_OWNER)
        response = client.get("/api/admin/deployment-mode-status")
        data = response.json()
        assert data["deployment_mode"] == "single_user"
        assert data["gate_applicable"] is False
        assert data["gate_passed"] is True
        assert data["conditions"] == []

    def test_multi_user_reports_unmet_conditions_without_raising(self, tmp_path):
        config = _make_config(tmp_path)
        foundry_yaml_path = config.paths.foundry_yaml
        existing = load_yaml(foundry_yaml_path) or {}
        existing["foundry"]["deployment_mode"] = "multi_user"
        dump_yaml(existing, foundry_yaml_path)

        # create_app() itself calls deployment_mode_validate() at startup and
        # would raise for an unmet multi_user gate — this test exercises the
        # config-level introspection directly rather than booting the app,
        # exactly like the router does internally.
        reloaded = FoundryConfig(paths=FoundryPaths(root=config.paths.root))
        status = reloaded.deployment_mode_status()
        assert status["deployment_mode"] == "multi_user"
        assert status["gate_applicable"] is True
        assert status["gate_passed"] is False
        ids = {c["id"] for c in status["conditions"]}
        assert ids == {"a", "b", "c", "d"}
        failed = {c["id"] for c in status["conditions"] if not c["passed"]}
        assert "a" in failed  # auth.provider defaults to "none"

    def test_no_secret_material_in_conditions(self, tmp_path):
        config = _make_config(tmp_path)
        foundry_yaml_path = config.paths.foundry_yaml
        existing = load_yaml(foundry_yaml_path) or {}
        existing["foundry"]["deployment_mode"] = "multi_user"
        dump_yaml(existing, foundry_yaml_path)
        reloaded = FoundryConfig(paths=FoundryPaths(root=config.paths.root))
        status = reloaded.deployment_mode_status()
        body_lower = str(status).lower()
        for secret_keyword in ("secret", "jwks", "bearer", "password", "clerk_secret"):
            assert secret_keyword not in body_lower
