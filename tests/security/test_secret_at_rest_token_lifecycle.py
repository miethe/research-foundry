"""Feature-level secret-at-rest guard (public-multiuser release activation,
ACT-601) -- consolidates and extends the per-phase static scans:

  * P2 (``tests/unit/test_token_service.py::test_static_scan_zero_plaintext_secrets_in_rbac_db``)
    scanned raw ``rbac.db`` bytes after issuance only.
  * P3 (``tests/unit/test_admin_tokens_api.py::TestNoSecretLeakAcrossTokenSurface``)
    scanned the admin-API HTTP response surface + logs after issuance only.

This file is the single feature-level guard for the PRD/plan success metric:

    "0 plaintext secrets persisted anywhere (DB, logs, audit)"

It sweeps THREE independent surfaces -- raw ``rbac.db`` bytes (which holds
BOTH ``access_tokens`` and ``audit_event`` in the same file, per
``rbac_store.py``'s docstring), parsed ``audit_event`` rows via
``audit_service.list_events`` (a different code path than a raw-bytes scan,
in case the audit store is ever split out), and captured application logs --
across the FULL issue -> use (repeated ``verify_token``) -> revoke lifecycle,
for BOTH principal types (``service`` and ``user_pat``), through BOTH the
service layer directly and the real admin HTTP API, and with the SA identity
additionally threaded through an ``agent_job_launched`` audit row (ACT-204)
so the audit-row sweep has real identity-bearing content to check, not an
empty table.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

import research_foundry.api.auth.provider as _provider_module
from research_foundry.api.app import create_app
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.services import audit_service, rbac_store, token_service
from research_foundry.services.agent_job_service import AgentJobService
from research_foundry.yamlio import dump_yaml, load_yaml

_MINIMAL_POLICY_SNAPSHOT: dict = {"allowed_tools": ["search"], "data_scopes": []}


@pytest.fixture(autouse=True)
def _restore_provider_registry():
    """``create_app`` re-registers ``local_static`` with a config-bound
    instance on every call (module-level ``_REGISTRY`` in
    ``api/auth/provider.py``). Snapshot/restore around each test so the
    admin-API guard's registration never leaks into other test modules
    collected later in the same pytest session."""
    snapshot = dict(_provider_module._REGISTRY)
    yield
    _provider_module._REGISTRY.clear()
    _provider_module._REGISTRY.update(snapshot)


# ---------------------------------------------------------------------------
# Shared seeding helpers
# ---------------------------------------------------------------------------


def _seed_workspace_and_users(paths: FoundryPaths, *, workspace_id: str = "ws1") -> None:
    conn = rbac_store.bootstrap(paths)
    try:
        rbac_store.upsert_workspace(conn, workspace_id, "Workspace One")
        rbac_store.upsert_user(conn, "alice", "Alice")
        rbac_store.upsert_membership(conn, "alice", workspace_id, "owner")
    finally:
        conn.close()


def _create_service_account(
    paths: FoundryPaths,
    *,
    service_account_id: str,
    workspace_id: str = "ws1",
    role: str = "researcher",
) -> None:
    conn = rbac_store.bootstrap(paths)
    try:
        rbac_store.create_service_account(
            conn,
            service_account_id=service_account_id,
            name="Secret-Scan Service Account",
            workspace_id=workspace_id,
            role=role,
            created_by="alice",
        )
    finally:
        conn.close()


def _bind_default_service_account(paths: FoundryPaths, service_account_id: str) -> None:
    """Set ``deployment_mode: multi_user`` + ``agents.default_service_account_id``
    so an ``agent_job_launched`` audit row is written with real identity
    content (ACT-204) -- giving the audit-row sweep below something concrete
    to check, not an empty table."""
    existing: dict = load_yaml(paths.foundry_yaml) or {}
    existing.setdefault("foundry", {})
    existing["foundry"]["deployment_mode"] = "multi_user"
    agents_block = dict(existing["foundry"].get("agents") or {})
    agents_block["default_service_account_id"] = service_account_id
    existing["foundry"]["agents"] = agents_block
    dump_yaml(existing, paths.foundry_yaml)


def _assert_absent_everywhere(
    plaintext: str,
    *,
    paths: FoundryPaths,
    log_text: str,
    context: str,
) -> None:
    """One secret's worth of the full three-surface sweep."""
    assert len(plaintext) > 8, "sanity: not trivially short/coincidental"

    # Surface 1: raw rbac.db bytes -- covers access_tokens, audit_event,
    # service_accounts, EVERY table, in one file (rbac_store.py keeps the
    # append-only audit log in the same durable sqlite file as RBAC/tokens).
    raw = paths.rbac_db.read_bytes()
    assert plaintext.encode("utf-8") not in raw, (
        f"[{context}] plaintext secret found verbatim in rbac.db: {plaintext[:8]}..."
    )
    # The HMAC's own message input (the remainder after the 8-char prefix)
    # must never appear verbatim either -- see token_service._hash_token.
    remainder = plaintext[8:]
    assert remainder.encode("utf-8") not in raw, (
        f"[{context}] token remainder found verbatim in rbac.db: {plaintext[:8]}..."
    )

    # Surface 2: parsed audit_event rows via the service API -- a DIFFERENT
    # code path than the raw-bytes scan above (would still fail if audit
    # storage were ever split into its own file/table).
    events = audit_service.list_events(paths, limit=200)
    events_text = json.dumps(events)
    assert plaintext not in events_text, (
        f"[{context}] plaintext secret found in parsed audit_event rows"
    )

    # Surface 3: captured application logs across the lifecycle.
    assert plaintext not in log_text, (
        f"[{context}] plaintext secret found in application logs"
    )


# ---------------------------------------------------------------------------
# Guard 1: service layer, full issue -> use -> revoke lifecycle, both
# principal types, WITH the SA identity threaded through a real audit row.
# ---------------------------------------------------------------------------


class TestServiceLayerZeroPlaintextAcrossFullLifecycle:
    def test_issue_use_revoke_lifecycle_zero_plaintext_in_db_audit_or_logs(
        self, tmp_foundry: FoundryPaths, caplog: pytest.LogCaptureFixture
    ) -> None:
        _seed_workspace_and_users(tmp_foundry)
        _create_service_account(tmp_foundry, service_account_id="svc_secret_scan")

        with caplog.at_level(logging.DEBUG):
            # --- issue ---
            sa_issued = token_service.issue_service_account_token(
                tmp_foundry, service_account_id="svc_secret_scan"
            )
            pat_issued = token_service.issue_user_pat(
                tmp_foundry, issuer_user_id="alice", workspace_id="ws1", role="owner"
            )

            # --- use (repeated, simulating real traffic across a session) ---
            for _ in range(3):
                assert token_service.verify_token(tmp_foundry, sa_issued.plaintext) is not None
                assert token_service.verify_token(tmp_foundry, pat_issued.plaintext) is not None

            # --- tie the SA identity into a REAL audit_event row (ACT-204) so
            # the audit-row sweep below has real identity-bearing content ---
            _bind_default_service_account(tmp_foundry, "svc_secret_scan")
            service = AgentJobService(tmp_foundry)
            service.create_job(
                provider="claude_agent_sdk",
                model_profile="rf_synthesize_deep",
                request_kind="research",
                policy_snapshot=dict(_MINIMAL_POLICY_SNAPSHOT),
                project_id="secret-scan-project",
                workspace_id="ws1",
                created_by="human_trigger",
            )

            # --- revoke ---
            token_service.revoke_token(tmp_foundry, sa_issued.token_id)
            token_service.revoke_token(tmp_foundry, pat_issued.token_id)
            assert token_service.verify_token(tmp_foundry, sa_issued.plaintext) is None
            assert token_service.verify_token(tmp_foundry, pat_issued.plaintext) is None

        log_text = "\n".join(record.getMessage() for record in caplog.records)

        for plaintext, context in (
            (sa_issued.plaintext, "service-account token, post-revoke"),
            (pat_issued.plaintext, "PAT, post-revoke"),
        ):
            _assert_absent_everywhere(
                plaintext, paths=tmp_foundry, log_text=log_text, context=context
            )

        # Confirm the audit row this lifecycle produced actually exists and
        # carries the SA identity -- i.e. the sweep above had real content
        # to check, not an empty table (a guard that only passes because
        # there was nothing to find would be worthless).
        events = audit_service.list_events(tmp_foundry, mutation_type="agent_job_launched")
        binding_events = [
            e for e in events["items"] if e.get("action") == "agent_job_create"
        ]
        assert len(binding_events) == 1
        assert binding_events[0]["actor_user_id"] == "svc_secret_scan"


# ---------------------------------------------------------------------------
# Guard 2: the real admin HTTP API surface -- extends P3's issuance-only
# check to the same issue -> use -> revoke lifecycle, plus the response-body
# sweep across every list/get route.
# ---------------------------------------------------------------------------


_ADMIN_OWNER_TOKEN_ENV = "RF_TEST_SECRET_SCAN_OWNER_TOKEN"


def _make_admin_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple:
    """A REAL ``local_static``-authenticated owner caller (never identity
    injection) -- so a Bearer credential genuinely flows through the
    composite auth chain (ACT-203) for the "use" step below, exactly like
    ``test_multiuser_activation_e2e.py``."""
    import secrets
    import shutil

    from research_foundry.paths import distribution_root

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

    owner_token = secrets.token_urlsafe(24)
    monkeypatch.setenv(_ADMIN_OWNER_TOKEN_ENV, owner_token)

    foundry_yaml_path = root / "foundry.yaml"
    existing: dict = load_yaml(foundry_yaml_path) or {}
    existing.setdefault("foundry", {})
    existing["foundry"]["viewer"] = {"auth_mode": "none"}
    existing["foundry"]["auth"] = {
        "provider": "local_static",
        "local_static": {
            "tokens": [
                {
                    "token_env": _ADMIN_OWNER_TOKEN_ENV,
                    "user_id": "u_owner_secret_scan",
                    "workspace_id": "default",
                    "roles": ["owner"],
                }
            ]
        },
    }
    dump_yaml(existing, foundry_yaml_path)

    from fastapi.testclient import TestClient

    from research_foundry.api.routers.admin import _get_config

    config = FoundryConfig(paths=FoundryPaths(root=root))
    app = create_app(config)
    app.dependency_overrides[get_paths] = lambda: config.paths
    app.dependency_overrides[_get_config] = lambda: config

    client = TestClient(app, raise_server_exceptions=True)
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    return client, config, owner_headers


class TestAdminApiZeroPlaintextAcrossFullLifecycle:
    def test_issue_use_revoke_via_http_zero_plaintext_in_db_audit_or_logs(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        client, config, owner_headers = _make_admin_client(tmp_path, monkeypatch)

        with caplog.at_level(logging.DEBUG):
            sa_resp = client.post(
                "/api/admin/service-accounts",
                json={"name": "http-secret-scan", "role": "researcher"},
                headers=owner_headers,
            )
            assert sa_resp.status_code == 201, sa_resp.text
            account_id = sa_resp.json()["id"]

            issued_resp = client.post(
                f"/api/admin/service-accounts/{account_id}/tokens", headers=owner_headers
            )
            assert issued_resp.status_code == 201, issued_resp.text
            sa_plaintext = issued_resp.json()["plaintext"]
            token_id = issued_resp.json()["token_id"]

            # --- use (repeated, over the REAL Bearer path -- composite auth
            # chain resolves the SA identity from the token store, distinct
            # from the owner's local_static-provider identity above) ---
            for _ in range(3):
                resp = client.get(
                    "/api/auth/identity",
                    headers={"Authorization": f"Bearer {sa_plaintext}"},
                )
                assert resp.status_code == 200
                assert resp.json()["user_id"] == account_id

            # P3-equivalent response-body sweep -- every OTHER route in the
            # surface must never echo the secret back.
            list_probes = [
                client.get("/api/admin/service-accounts", headers=owner_headers),
                client.get(
                    f"/api/admin/service-accounts/{account_id}/tokens", headers=owner_headers
                ),
            ]
            for probe in list_probes:
                assert probe.status_code == 200
                assert sa_plaintext not in probe.text
                assert "token_hash" not in probe.text

            # --- revoke ---
            revoke_resp = client.delete(
                f"/api/admin/service-accounts/{account_id}/tokens/{token_id}",
                headers=owner_headers,
            )
            assert revoke_resp.status_code == 200

            post_revoke = client.get(
                "/api/auth/identity",
                headers={"Authorization": f"Bearer {sa_plaintext}"},
            )
            assert post_revoke.status_code == 401

        log_text = "\n".join(record.getMessage() for record in caplog.records)
        _assert_absent_everywhere(
            sa_plaintext,
            paths=config.paths,
            log_text=log_text,
            context="admin HTTP API, post-revoke",
        )


# ---------------------------------------------------------------------------
# Explicit success-metric test (PRD Success Metrics / plan Success Metrics,
# ACT-601): "0 plaintext secrets persisted anywhere (DB, logs, audit)".
# ---------------------------------------------------------------------------


def test_success_metric_zero_plaintext_secrets_persisted_anywhere(
    tmp_foundry: FoundryPaths, caplog: pytest.LogCaptureFixture
) -> None:
    """Compact, single-assertion-surface restatement of the PRD/plan success
    metric verbatim -- kept intentionally separate from the two detailed
    guards above so the metric itself has one unambiguous, minimally-scoped
    pass/fail signal, covering both principal types in one issue-use-revoke
    pass."""
    _seed_workspace_and_users(tmp_foundry)
    _create_service_account(tmp_foundry, service_account_id="svc_metric")

    with caplog.at_level(logging.DEBUG):
        sa_issued = token_service.issue_service_account_token(
            tmp_foundry, service_account_id="svc_metric"
        )
        pat_issued = token_service.issue_user_pat(
            tmp_foundry, issuer_user_id="alice", workspace_id="ws1", role="owner"
        )
        assert token_service.verify_token(tmp_foundry, sa_issued.plaintext) is not None
        assert token_service.verify_token(tmp_foundry, pat_issued.plaintext) is not None
        token_service.revoke_token(tmp_foundry, sa_issued.token_id)
        token_service.revoke_token(tmp_foundry, pat_issued.token_id)

    log_text = "\n".join(record.getMessage() for record in caplog.records)
    raw = tmp_foundry.rbac_db.read_bytes()
    audit_text = json.dumps(audit_service.list_events(tmp_foundry, limit=200))

    zero_plaintext_secrets_found = 0
    for plaintext in (sa_issued.plaintext, pat_issued.plaintext):
        if plaintext.encode("utf-8") in raw:
            zero_plaintext_secrets_found += 1
        if plaintext in audit_text:
            zero_plaintext_secrets_found += 1
        if plaintext in log_text:
            zero_plaintext_secrets_found += 1

    assert zero_plaintext_secrets_found == 0, (
        "success metric violated: 0 plaintext secrets persisted anywhere "
        "(DB, logs, audit) — see PRD Success Metrics / plan Success Metrics"
    )
