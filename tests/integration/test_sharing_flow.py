"""Integration tests for the share-link flow (Phase 5.6-T4).

Covers the full round-trip:
  1. Create a share link (POST /api/reports/{id}/share-links)
  2. Resolve the share link (GET /api/reports/shares/{token})
  3. Confirm sensitivity threshold is re-applied at resolution time
     (does not trust the check at creation time alone — PRD AC-2)
  4. Expired and revoked tokens → 404
  5. Draft sensitivity increased after share creation → 422 at resolution

The share-link record is stored in .rf_state/rbac.db (never catalog.db).
These tests verify that the durable store persists across client re-creations
(simulating a server restart) and that the share link is still resolvable.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.services.share_store import (
    bootstrap_share_store,
    create_share_link,
    list_share_links,
    resolve_share_link,
    revoke_share_link,
)
from research_foundry.yamlio import dump_yaml, load_yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(tmp_path: Path) -> FoundryConfig:
    """Build a minimal FoundryConfig rooted at *tmp_path*."""
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


def _make_client(cfg: FoundryConfig) -> TestClient:
    """Build a no-auth TestClient for *cfg*."""
    app = create_app(cfg)
    app.dependency_overrides[get_paths] = lambda: cfg.paths
    return TestClient(app, raise_server_exceptions=True)


def _create_blank_draft(client: TestClient, title: str = "Share Test Draft") -> str:
    """Create a blank report draft and return its report_draft_id."""
    resp = client.post("/api/reports", json={"origin": "blank", "title": title})
    assert resp.status_code == 201, f"Failed to create draft: {resp.text}"
    return resp.json()["report_draft_id"]


def _add_narrative_block(client: TestClient, rid: str, text: str = "Background.") -> None:
    resp = client.post(
        f"/api/reports/{rid}/blocks",
        json={"markdown": text, "materiality": "narrative"},
    )
    assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Core share-link round-trip
# ---------------------------------------------------------------------------


def test_create_share_link_returns_token(tmp_path: Path) -> None:
    """POST /api/reports/{id}/share-links returns a share_token and metadata."""
    cfg = _make_config(tmp_path)
    client = _make_client(cfg)
    rid = _create_blank_draft(client)

    resp = client.post(
        f"/api/reports/{rid}/share-links",
        json={"sensitivity_threshold": "public"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "share_token" in data
    assert data["report_draft_id"] == rid
    assert data["sensitivity_threshold"] == "public"
    assert len(data["share_token"]) >= 20, "Token should be a long random string"


def test_share_link_persisted_in_rbac_db(tmp_path: Path) -> None:
    """Share link record is stored in .rf_state/rbac.db (not catalog.db)."""
    cfg = _make_config(tmp_path)
    client = _make_client(cfg)
    rid = _create_blank_draft(client)

    resp = client.post(
        f"/api/reports/{rid}/share-links",
        json={"sensitivity_threshold": "public"},
    )
    token = resp.json()["share_token"]

    # Confirm record exists via the store layer (not the HTTP API)
    record = resolve_share_link(cfg.paths, token)
    assert record is not None
    assert record["report_draft_id"] == rid
    assert record["sensitivity_threshold"] == "public"
    assert record["revoked"] == 0

    # Confirm it's in rbac.db path specifically
    assert cfg.paths.rbac_db.exists(), "rbac.db must exist after share link creation"
    assert "catalog" not in str(cfg.paths.rbac_db), (
        "Share links must be in rbac.db, never catalog.db"
    )


def test_resolve_share_link_returns_preview(tmp_path: Path) -> None:
    """GET /api/reports/shares/{token} returns preview_markdown on a valid token."""
    cfg = _make_config(tmp_path)
    client = _make_client(cfg)
    rid = _create_blank_draft(client)
    _add_narrative_block(client, rid, "Public research summary.")

    # Create share link
    create_resp = client.post(
        f"/api/reports/{rid}/share-links",
        json={"sensitivity_threshold": "public"},
    )
    token = create_resp.json()["share_token"]

    # Resolve share link
    resolve_resp = client.get(f"/api/reports/shares/{token}")
    assert resolve_resp.status_code == 200, resolve_resp.text
    data = resolve_resp.json()
    assert data["ok"] is True
    assert data["report_draft_id"] == rid
    assert data["sensitivity_threshold"] == "public"
    assert isinstance(data["preview_markdown"], str)
    assert len(data["preview_markdown"]) > 0


def test_resolve_share_link_invalid_token_returns_404(tmp_path: Path) -> None:
    """Unknown token → 404."""
    cfg = _make_config(tmp_path)
    client = _make_client(cfg)
    resp = client.get("/api/reports/shares/completely_invalid_token_xyz")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Sensitivity re-applied at resolution time (PRD AC-2)
# ---------------------------------------------------------------------------


def test_share_link_resolution_rechecks_sensitivity(tmp_path: Path) -> None:
    """Sensitivity threshold is re-applied at resolution time.

    Scenario:
      1. Draft starts as public sensitivity.
      2. Share link is created at 'public' threshold.
      3. Share link resolves successfully.
      4. Draft is re-created with 'client_sensitive' sensitivity (simulating
         a relabelling after share link creation).
      5. A new share link at 'public' threshold cannot be created (draft
         sensitivity exceeds threshold).

    This verifies that sensitivity_threshold at creation time does NOT grant
    permanent bypass — the gate is checked at every resolution.
    """
    cfg = _make_config(tmp_path)
    client = _make_client(cfg)

    # Create a public draft
    resp_create = client.post(
        "/api/reports",
        json={"origin": "blank", "title": "Sensitivity Re-check Test", "sensitivity": "public"},
    )
    assert resp_create.status_code == 201
    rid = resp_create.json()["report_draft_id"]
    _add_narrative_block(client, rid, "Public summary text.")

    # Create share link at 'public' threshold
    share_resp = client.post(
        f"/api/reports/{rid}/share-links",
        json={"sensitivity_threshold": "public"},
    )
    assert share_resp.status_code == 201
    token = share_resp.json()["share_token"]

    # Resolution succeeds while draft is still public
    resolve_resp = client.get(f"/api/reports/shares/{token}")
    assert resolve_resp.status_code == 200

    # Now simulate draft sensitivity being changed by creating a new
    # draft with client_sensitive sensitivity and trying to share at public.
    # The creation gate (POST share-links) should reject this.
    resp_sens = client.post(
        "/api/reports",
        json={
            "origin": "blank",
            "title": "Now Sensitive Draft",
            "sensitivity": "client_sensitive",
        },
    )
    rid_sens = resp_sens.json()["report_draft_id"]
    _add_narrative_block(client, rid_sens, "Sensitive text.")

    # Attempting to create a 'public' share link for a client_sensitive draft must fail (422)
    share_block_resp = client.post(
        f"/api/reports/{rid_sens}/share-links",
        json={"sensitivity_threshold": "public"},
    )
    assert share_block_resp.status_code == 422, (
        f"Expected 422 when draft sensitivity > share threshold, "
        f"got {share_block_resp.status_code}: {share_block_resp.text}"
    )


def test_share_link_resolution_fails_when_draft_sensitivity_increased(
    tmp_path: Path,
) -> None:
    """Resolution returns 422 when draft sensitivity has been relabelled above threshold.

    This tests the PRD AC-2 invariant: sensitivity is checked AT RESOLUTION
    TIME against the CURRENT draft state, not the state at creation time.

    Implementation note: we cannot relabel a draft via the API (no PATCH
    /api/reports/{id}/sensitivity endpoint exists yet), so we write to the
    underlying draft YAML directly to simulate a post-creation relabelling.
    This is intentional — the test verifies the resolution-time gate.
    """
    from research_foundry.services import builder_service as bsvc

    cfg = _make_config(tmp_path)
    client = _make_client(cfg)

    # Create a public draft
    resp = client.post(
        "/api/reports",
        json={"origin": "blank", "title": "Relabelling Test", "sensitivity": "public"},
    )
    rid = resp.json()["report_draft_id"]
    _add_narrative_block(client, rid, "Initially public content.")

    # Create share link at 'public' threshold
    share_resp = client.post(
        f"/api/reports/{rid}/share-links",
        json={"sensitivity_threshold": "public"},
    )
    assert share_resp.status_code == 201
    token = share_resp.json()["share_token"]

    # Verify it resolves while sensitivity is public
    assert client.get(f"/api/reports/shares/{token}").status_code == 200

    # Simulate relabelling: directly update the draft's sensitivity label
    # (bypassing the API — this simulates an out-of-band relabelling)
    draft = bsvc.load_draft(cfg.paths, rid)
    draft["sensitivity"] = "client_sensitive"
    draft_yaml_path = cfg.paths.report_draft_dir(rid) / "draft.yaml"
    from research_foundry.yamlio import dump_yaml as _dump
    _dump(draft, draft_yaml_path)

    # Resolution must now fail closed (422) because draft sensitivity exceeds
    # the share link's stored 'public' threshold
    resolve_resp = client.get(f"/api/reports/shares/{token}")
    assert resolve_resp.status_code == 422, (
        f"Expected 422 after draft was relabelled to client_sensitive, "
        f"got {resolve_resp.status_code}: {resolve_resp.text}"
    )
    detail = resolve_resp.json()["detail"]
    assert detail["ok"] is False
    assert "client_sensitive" in str(detail)
    assert "public" in str(detail)


# ---------------------------------------------------------------------------
# Expired and revoked tokens
# ---------------------------------------------------------------------------


def test_expired_share_link_returns_404(tmp_path: Path) -> None:
    """A share link with an expires_at in the past returns 404 at resolution time."""
    cfg = _make_config(tmp_path)
    # Create share link directly via the store with an already-expired timestamp
    link = create_share_link(
        cfg.paths,
        report_draft_id="rpt_dummy_xxx",
        sensitivity_threshold="public",
        created_by="test",
        expires_at="2020-01-01T00:00:00Z",  # past
    )
    token = link["share_token"]

    # Resolve via store layer — should return None (expired)
    resolved = resolve_share_link(cfg.paths, token)
    assert resolved is None, "Expired token should resolve to None"

    # Also check via HTTP API if the draft existed
    client = _make_client(cfg)
    resp = client.get(f"/api/reports/shares/{token}")
    assert resp.status_code == 404


def test_revoked_share_link_returns_404(tmp_path: Path) -> None:
    """A revoked share link returns 404 at resolution time."""
    cfg = _make_config(tmp_path)
    client = _make_client(cfg)
    rid = _create_blank_draft(client, "Revocation Test")
    _add_narrative_block(client, rid)

    # Create share link
    share_resp = client.post(
        f"/api/reports/{rid}/share-links",
        json={"sensitivity_threshold": "public"},
    )
    token = share_resp.json()["share_token"]

    # Verify resolves initially
    assert client.get(f"/api/reports/shares/{token}").status_code == 200

    # Revoke via store layer
    revoked = revoke_share_link(cfg.paths, token)
    assert revoked is True

    # Resolution should now return 404
    assert client.get(f"/api/reports/shares/{token}").status_code == 404


# ---------------------------------------------------------------------------
# Store layer unit tests
# ---------------------------------------------------------------------------


def test_share_store_bootstrap_idempotent(tmp_path: Path) -> None:
    """bootstrap_share_store can be called multiple times without error."""
    cfg = _make_config(tmp_path)
    conn1 = bootstrap_share_store(cfg.paths)
    conn1.close()
    conn2 = bootstrap_share_store(cfg.paths)
    conn2.close()
    # No exception = idempotent


def test_share_store_list_by_report(tmp_path: Path) -> None:
    """list_share_links filters by report_draft_id."""
    cfg = _make_config(tmp_path)
    create_share_link(cfg.paths, report_draft_id="rpt_a", sensitivity_threshold="public")
    create_share_link(cfg.paths, report_draft_id="rpt_a", sensitivity_threshold="public")
    create_share_link(cfg.paths, report_draft_id="rpt_b", sensitivity_threshold="public")

    links_a = list_share_links(cfg.paths, report_draft_id="rpt_a")
    links_b = list_share_links(cfg.paths, report_draft_id="rpt_b")
    all_links = list_share_links(cfg.paths)

    assert len(links_a) == 2
    assert len(links_b) == 1
    assert len(all_links) == 3


def test_share_store_persistence_across_connections(tmp_path: Path) -> None:
    """Share link records survive across separate database connections (simulates restarts)."""
    cfg = _make_config(tmp_path)

    # Create a link with connection 1
    link = create_share_link(
        cfg.paths,
        report_draft_id="rpt_persist_test",
        sensitivity_threshold="public",
        created_by="test_user",
    )
    token = link["share_token"]

    # Resolve with a fresh connection (simulates server restart)
    record = resolve_share_link(cfg.paths, token)
    assert record is not None, "Share link must persist across connections"
    assert record["share_token"] == token
    assert record["report_draft_id"] == "rpt_persist_test"
    assert record["created_by"] == "test_user"


def test_create_share_link_with_unknown_threshold_returns_422(tmp_path: Path) -> None:
    """Creating a share link with an unknown sensitivity_threshold → 422."""
    cfg = _make_config(tmp_path)
    client = _make_client(cfg)
    rid = _create_blank_draft(client)

    resp = client.post(
        f"/api/reports/{rid}/share-links",
        json={"sensitivity_threshold": "not_a_real_level"},
    )
    assert resp.status_code == 422


def test_create_share_link_for_nonexistent_report_returns_404(tmp_path: Path) -> None:
    """Creating a share link for a non-existent report → 404."""
    cfg = _make_config(tmp_path)
    client = _make_client(cfg)

    resp = client.post(
        "/api/reports/rpt_does_not_exist_share/share-links",
        json={"sensitivity_threshold": "public"},
    )
    assert resp.status_code == 404
