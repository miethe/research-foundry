"""Regression tests: AuthProviderMiddleware exempts ONLY the share-token
resolution endpoint from authentication when auth.provider != none.

DEFECT being fixed (P1):
  GET /api/reports/shares/{share_token} was unreachable when auth.provider != none
  because AuthProviderMiddleware rejected all /api/* paths with 401 before routing.
  Recipients of share links always got 401.

FIX:
  A precisely-scoped public-path exemption in AuthProviderMiddleware for
  GET /api/reports/shares/{token} (non-empty token required).  All other
  /api/reports/* routes remain fully auth-gated.

Security invariants preserved:
  - The share_token itself is the credential.
  - The resolver validates token validity, expiry, and revocation.
  - The resolver enforces the share link's sensitivity threshold (PRD AC-2).
  - NO other /api/reports/* route becomes unauthenticated.

Test matrix
-----------
(a) Unauth GET of a nonexistent share token → 404 (not 401)
    [middleware lets it through; resolver reports "not found"]
(a2) Unauth GET of a valid share token → 200 (not 401)
    [middleware lets it through; resolver returns preview]
(b) Unauth GET of GET /api/reports → 401 (exemption not bleed through)
(b2) Unauth GET of GET /api/reports/{id} → 401 (exemption not bleed through)
(c) Share token with threshold=public against a client_sensitive draft → 422
    [middleware lets it through; resolver enforces sensitivity — PRD AC-2]
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.services import builder_service as bsvc
from research_foundry.services.share_store import create_share_link
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Config & client helpers
# ---------------------------------------------------------------------------

_API_TOKEN = "test-share-exemption-token"
_TOKEN_ENV = "RF_SHARE_EXEMPTION_TEST_TOKEN"


def _make_config_with_auth(tmp_path: Path, monkeypatch) -> FoundryConfig:
    """Build a FoundryConfig with local_static auth provider active.

    The local_static provider causes AuthProviderMiddleware to be added,
    which is the condition that triggers the defect.
    """
    monkeypatch.setenv(_TOKEN_ENV, _API_TOKEN)

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
    # viewer.auth_mode=none so the legacy path is skipped; auth.provider drives
    # everything.
    existing["foundry"]["viewer"] = {"auth_mode": "none"}
    existing["foundry"]["auth"] = {
        "provider": "local_static",
        "local_static": {
            "tokens": [
                {
                    "token_env": _TOKEN_ENV,
                    "user_id": "test_user",
                    "workspace_id": "default",
                    "roles": ["owner"],
                }
            ]
        },
    }
    dump_yaml(existing, foundry_yaml_path)
    return FoundryConfig(paths=FoundryPaths(root=root))


def _make_client(cfg: FoundryConfig) -> TestClient:
    app = create_app(cfg)
    app.dependency_overrides[get_paths] = lambda: cfg.paths
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# (a) Unauth GET of share-token route is not blocked by middleware
# ---------------------------------------------------------------------------


def test_unauth_share_token_not_blocked_by_middleware_unknown_token(
    tmp_path: Path, monkeypatch
) -> None:
    """DEFECT regression (a): GET /api/reports/shares/{token} must not return 401
    when auth.provider != none and no Authorization header is sent.

    An unknown token returns 404 from the resolver — confirming the middleware
    passed the request through and routing reached the handler.

    FAIL before fix: status_code == 401 (middleware blocked it).
    PASS after fix:  status_code == 404 (resolver ran, reported "not found").
    """
    cfg = _make_config_with_auth(tmp_path, monkeypatch)
    client = _make_client(cfg)

    resp = client.get("/api/reports/shares/nonexistent_token_abc123xyz")

    assert resp.status_code != 401, (
        "AuthProviderMiddleware blocked GET /api/reports/shares/{token} with 401. "
        "The middleware must exempt this path (share token IS the credential)."
    )
    assert resp.status_code == 404, (
        f"Expected 404 (token not found), got {resp.status_code}: {resp.text}"
    )


def test_unauth_get_valid_share_token_returns_200(
    tmp_path: Path, monkeypatch
) -> None:
    """DEFECT regression (a2): Unauthenticated GET of a real share token returns 200.

    Creates a draft and share link via the service layer (bypassing HTTP auth),
    then makes an unauthenticated HTTP GET — confirming the exemption works
    end-to-end.

    FAIL before fix: status_code == 401.
    PASS after fix:  status_code == 200, body.ok == True.
    """
    cfg = _make_config_with_auth(tmp_path, monkeypatch)
    paths = cfg.paths

    # Set up via service layer to avoid needing an authenticated HTTP call.
    draft = bsvc.create_draft(paths, title="Auth Exemption E2E Test", sensitivity="public")
    rid = draft["report_draft_id"]
    share = create_share_link(paths, report_draft_id=rid, sensitivity_threshold="public")
    token = share["share_token"]

    client = _make_client(cfg)

    # No Authorization header — testing the exemption.
    resp = client.get(f"/api/reports/shares/{token}")

    assert resp.status_code != 401, (
        "AuthProviderMiddleware blocked share token resolution with 401. "
        "The middleware must exempt GET /api/reports/shares/{token}."
    )
    assert resp.status_code == 200, (
        f"Expected 200 from the resolver, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body.get("ok") is True
    assert body.get("report_draft_id") == rid


# ---------------------------------------------------------------------------
# (b) Exemption scoping: non-share /api/reports/* routes still require auth
# ---------------------------------------------------------------------------


def test_list_reports_route_still_requires_auth(tmp_path: Path, monkeypatch) -> None:
    """Scoping check (b): GET /api/reports (list drafts) returns 401 without auth.

    The share-token exemption must not bleed into other /api/reports/* routes.

    FAIL (security regression): 401 not returned — exemption too broad.
    PASS:                        401 returned — non-share route still gated.
    """
    cfg = _make_config_with_auth(tmp_path, monkeypatch)
    client = _make_client(cfg)

    resp = client.get("/api/reports")

    assert resp.status_code == 401, (
        f"Expected 401 for GET /api/reports without auth (no exemption should apply), "
        f"got {resp.status_code}. The share-token exemption may be too broad."
    )


def test_specific_report_route_still_requires_auth(tmp_path: Path, monkeypatch) -> None:
    """Scoping check (b2): GET /api/reports/{id} returns 401 without auth.

    The exemption is ONLY for /api/reports/shares/{token} — not any other
    path under /api/reports/.

    PASS: 401 returned — specific-report route still gated.
    """
    cfg = _make_config_with_auth(tmp_path, monkeypatch)
    client = _make_client(cfg)

    resp = client.get("/api/reports/rpt_some_draft_id_0")

    assert resp.status_code == 401, (
        f"Expected 401 for GET /api/reports/{{id}} without auth, got {resp.status_code}. "
        "The share-token exemption must not apply to non-share report routes."
    )


# ---------------------------------------------------------------------------
# (c) Sensitivity threshold enforced inside the resolver (PRD AC-2)
# ---------------------------------------------------------------------------


def test_share_token_sensitivity_threshold_enforced_at_resolution_time(
    tmp_path: Path, monkeypatch
) -> None:
    """PRD AC-2 regression (c): A share token with threshold=public cannot return
    content from a draft whose sensitivity has been increased to client_sensitive.

    The middleware exemption must NOT bypass sensitivity gating — it only skips
    the session-auth check.  The resolver re-checks sensitivity at resolution time.

    Setup:
      1. Create a public draft via service layer.
      2. Create a share link at 'public' threshold via service layer.
      3. Relabel the draft to 'client_sensitive' (simulating post-creation
         relabelling, same approach as test_sharing_flow.py).
      4. GET /api/reports/shares/{token} without auth header.

    FAIL before fix: 401 (middleware blocks — PRD AC-2 check never runs).
    PASS after fix:  422 (resolver ran, sensitivity mismatch detected).
    """
    cfg = _make_config_with_auth(tmp_path, monkeypatch)
    paths = cfg.paths

    # Create a public draft via service layer (bypass HTTP auth).
    draft = bsvc.create_draft(
        paths, title="Sensitivity Gate Test", sensitivity="public"
    )
    rid = draft["report_draft_id"]

    # Create share link at 'public' threshold directly (bypass creation gate).
    share = create_share_link(
        paths, report_draft_id=rid, sensitivity_threshold="public"
    )
    token = share["share_token"]

    # Relabel draft to 'client_sensitive' to simulate post-creation relabelling.
    draft_yaml_path = paths.report_draft_dir(rid) / "draft.yaml"
    current_draft = bsvc.load_draft(paths, rid)
    current_draft["sensitivity"] = "client_sensitive"
    dump_yaml(current_draft, draft_yaml_path)

    client = _make_client(cfg)

    # No Authorization header — middleware should let it through; resolver
    # should reject with 422 (sensitivity mismatch).
    resp = client.get(f"/api/reports/shares/{token}")

    assert resp.status_code != 401, (
        "AuthProviderMiddleware blocked share token resolution with 401. "
        "The middleware must exempt GET /api/reports/shares/{token} so the "
        "resolver can run the PRD AC-2 sensitivity check."
    )
    assert resp.status_code == 422, (
        f"Expected 422 (sensitivity mismatch — PRD AC-2), "
        f"got {resp.status_code}: {resp.text}. "
        "The share-token exemption must not bypass sensitivity gating."
    )
    detail = resp.json().get("detail", {})
    assert detail.get("ok") is False, "422 detail must include ok=False"


# ---------------------------------------------------------------------------
# (d) WKSP-304 Phase 4 — share token is the SOLE authorization boundary,
#     unaffected by the viewer's own workspace membership
# ---------------------------------------------------------------------------


def test_share_token_ignores_viewer_workspace_even_when_isolation_enforcing(
    tmp_path: Path, monkeypatch
) -> None:
    """D5 fail-closed decision: a share link grants access to its one shared
    resource regardless of the *viewer's* own workspace, even with workspace
    isolation actively enforcing.

    Setup:
      1. Create a draft in workspace "ws-draft-owner".
      2. Create a public share link for it via the service layer.
      3. Force ``FoundryConfig.resolve_workspace_isolation_enforced`` to
         resolve ``True`` (enforcing mode active).
      4. GET /api/reports/shares/{token} WITH a valid session Authorization
         header whose identity's workspace_id is "default" — deliberately
         different from the draft's "ws-draft-owner".

    FAIL (regression): 404/422 — the resolver started threading the caller's
    session identity into ``load_draft``/``export_markdown``, letting
    workspace-isolation enforcement deny a request the share token alone
    should have authorized.
    PASS: 200 with the preview content — the share token is the sole
    authorization boundary; the viewer's own workspace never broadens or
    narrows it (``resolve_share_link`` passes ``identity=None`` explicitly to
    both draft loads, WKSP-304 Phase 4).
    """
    cfg = _make_config_with_auth(tmp_path, monkeypatch)
    paths = cfg.paths

    # Draft lives in a workspace distinct from the authenticated caller's
    # token workspace ("default", per _make_config_with_auth).
    draft = bsvc.create_draft(
        paths,
        title="Cross-Workspace Share Test",
        sensitivity="public",
        workspace_id="ws-draft-owner",
    )
    rid = draft["report_draft_id"]
    share = create_share_link(paths, report_draft_id=rid, sensitivity_threshold="public")
    token = share["share_token"]

    # Force workspace isolation into enforcing mode (WKSP-304 Phase 4).
    monkeypatch.setattr(
        FoundryConfig,
        "resolve_workspace_isolation_enforced",
        lambda self, provider, bind_host: True,
    )

    client = _make_client(cfg)

    # Authenticated caller whose session identity's workspace_id ("default")
    # differs from the draft's workspace_id ("ws-draft-owner").
    resp = client.get(
        f"/api/reports/shares/{token}",
        headers={"Authorization": f"Bearer {_API_TOKEN}"},
    )

    assert resp.status_code == 200, (
        f"Expected 200 — the share token alone authorizes access regardless "
        f"of the viewer's own workspace, got {resp.status_code}: {resp.text}"
    )
    body = resp.json()
    assert body.get("ok") is True
    assert body.get("report_draft_id") == rid
    assert "preview_markdown" in body
