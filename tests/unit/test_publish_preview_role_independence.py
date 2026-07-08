"""Role-independence tests for publish_preview gate (PRD AC-2 / Phase 5.6-T4).

Verifies the core security invariant:

  publish_preview returns 422 on ANY error-severity sensitivity violation
  REGARDLESS of the caller's role — including owner and admin.

No role can bypass the sensitivity gate.  RBAC (owner/admin only) fires AFTER
the sensitivity check, so a sensitivity violation always surfaces as 422 before
a potential 403 could reach the caller.

Also covers the fail-closed case when the global source index is unavailable
(sentinel entry in the index → 422, never 200).
"""

from __future__ import annotations

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
from research_foundry.api.routers.runs import get_paths
from research_foundry.config import FoundryConfig
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Test fixture constants
# ---------------------------------------------------------------------------

_SENSITIVE_QUOTE = "TOP SECRET CLASSIFIED FIGURE $99 TRILLION PER ANNUM."

# All five canonical roles — ordered from highest to lowest privilege.
_ALL_ROLES = [
    ("owner",      AuthIdentity("user_owner",      "ws1", ("owner",))),
    ("admin",      AuthIdentity("user_admin",       "ws1", ("admin",))),
    ("researcher", AuthIdentity("user_researcher",  "ws1", ("researcher",))),
    ("reviewer",   AuthIdentity("user_reviewer",    "ws1", ("reviewer",))),
    ("viewer",     AuthIdentity("user_viewer",      "ws1", ("viewer",))),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _InjectIdentityMiddleware(BaseHTTPMiddleware):
    """Injects a synthetic AuthIdentity into request.state for testing."""

    def __init__(self, app, identity: AuthIdentity | None) -> None:
        super().__init__(app)
        self._identity = identity

    async def dispatch(self, request: Request, call_next) -> Response:
        if self._identity is not None:
            request.state.identity = self._identity
        return await call_next(request)


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


def _make_client(cfg: FoundryConfig, identity: AuthIdentity | None = None) -> TestClient:
    """Build a TestClient for *cfg*, optionally injecting *identity*."""
    app = create_app(cfg)
    app.dependency_overrides[get_paths] = lambda: cfg.paths
    app.add_middleware(_InjectIdentityMiddleware, identity=identity)
    return TestClient(app, raise_server_exceptions=True)


def _plant_sensitive_run(paths: FoundryPaths, run_id: str = "rf_run_ri_sens") -> None:
    """Plant a run with a client_sensitive source containing _SENSITIVE_QUOTE."""
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "status": "verified",
            "sensitivity": "public",
            "created_at": "2026-01-01T00:00:00Z",
        },
        rp.run_yaml,
    )
    dump_md(
        {
            "type": "source_card",
            "source_card_id": "src_ri_sens",
            "sensitivity": "client_sensitive",
            "source": {"title": "Secret Deck", "source_type": "document"},
            "trust": "high",
            "usage": "direct",
            "extracted_points": [
                {
                    "evidence_id": "ev_ri_sens",
                    "locator": "p1",
                    "summary": "classified figure",
                    "quote": _SENSITIVE_QUOTE,
                    "sensitivity": "client_sensitive",
                }
            ],
        },
        "",
        rp.sources / "src_ri_sens.md",
    )


def _create_draft_with_sensitivity_violation(cfg: FoundryConfig) -> str:
    """Create a draft with a raw sensitive quote embedded in a body block.

    Returns the ``report_draft_id``.  Uses a no-auth client so any role
    injection for the actual test is independent.
    """
    _plant_sensitive_run(cfg.paths)
    client = _make_client(cfg, identity=None)

    # Create draft
    created = client.post(
        "/api/reports",
        json={"origin": "blank", "title": "Sensitivity Role Test"},
    ).json()
    rid = created["report_draft_id"]

    # Add a narrative block that embeds the raw sensitive quote
    client.post(
        f"/api/reports/{rid}/blocks",
        json={"markdown": f"Finding: {_SENSITIVE_QUOTE}", "materiality": "narrative"},
    )
    # Link the sensitive source so the per-run sensitivity check can inspect it
    client.post(
        f"/api/reports/{rid}/source-links",
        json={"source_card_id": "src_ri_sens", "run_id": "rf_run_ri_sens"},
    )
    return rid


# ---------------------------------------------------------------------------
# Core test: 422 for ALL roles on sensitivity violation (PRD AC-2)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("role_name,identity", _ALL_ROLES)
def test_publish_preview_422_for_all_roles_on_sensitivity_violation(
    tmp_path: Path, role_name: str, identity: AuthIdentity
) -> None:
    """PRD AC-2: publish_preview returns 422 for every role on a sensitivity violation.

    The sensitivity gate fires before the RBAC gate, so no role — not even
    owner or admin — can bypass a sensitivity failure.
    """
    cfg = _make_config(tmp_path)
    rid = _create_draft_with_sensitivity_violation(cfg)

    # Use a fresh client with the parametrized role injected
    client = _make_client(cfg, identity=identity)
    resp = client.post(f"/api/reports/{rid}/publish-preview")

    assert resp.status_code == 422, (
        f"Role {role_name!r} received HTTP {resp.status_code} instead of 422 "
        "on a draft with a sensitivity violation. "
        "The sensitivity gate must be role-independent (PRD AC-2): "
        "422 must fire for ALL roles before any role-based 403 can occur."
    )
    detail = resp.json()["detail"]
    assert detail["ok"] is False, (
        f"Role {role_name!r}: response body ok should be False on 422, got {detail}"
    )
    blocking_ids = [c["id"] for c in detail.get("blocking", [])]
    # Either the per-run or global sensitivity check must be in blocking list.
    assert (
        "report_body_sensitivity" in blocking_ids
        or "report_body_sensitivity_global" in blocking_ids
    ), (
        f"Role {role_name!r}: expected a sensitivity check in blocking list, "
        f"got: {blocking_ids!r}"
    )


# ---------------------------------------------------------------------------
# Verify that publish_preview passes for permitted roles when sensitivity is clean
# ---------------------------------------------------------------------------


def test_publish_preview_owner_succeeds_when_sensitivity_clean(tmp_path: Path) -> None:
    """Sanity check: owner gets 200 when no sensitivity violation exists."""
    cfg = _make_config(tmp_path)
    client_owner = _make_client(cfg, identity=AuthIdentity("owner", "ws1", ("owner",)))

    created = client_owner.post(
        "/api/reports",
        json={"origin": "blank", "title": "Clean Draft"},
    ).json()
    rid = created["report_draft_id"]
    # Add a narrative block (non-material, no claim link needed)
    client_owner.post(
        f"/api/reports/{rid}/blocks",
        json={"markdown": "Background context.", "materiality": "narrative"},
    )

    resp = client_owner.post(f"/api/reports/{rid}/publish-preview")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_publish_preview_researcher_gets_403_when_sensitivity_clean(tmp_path: Path) -> None:
    """Researcher gets 403 (not 422) when no sensitivity violation exists.

    This confirms that the RBAC gate fires correctly in step 3 (after sensitivity
    passes) — researcher lacks report:publish permission.
    """
    cfg = _make_config(tmp_path)
    client_noauth = _make_client(cfg, identity=None)
    created = client_noauth.post(
        "/api/reports",
        json={"origin": "blank", "title": "Clean Draft Researcher"},
    ).json()
    rid = created["report_draft_id"]
    client_noauth.post(
        f"/api/reports/{rid}/blocks",
        json={"markdown": "Background text.", "materiality": "narrative"},
    )

    # Now try with researcher role — should get 403 (sensitivity clean)
    client_researcher = _make_client(cfg, identity=AuthIdentity("r", "ws1", ("researcher",)))
    resp = client_researcher.post(f"/api/reports/{rid}/publish-preview")
    assert resp.status_code == 403, (
        f"Researcher expected 403 on a clean draft (RBAC gate), got {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# Fail-closed: global source index unavailable → 422
# ---------------------------------------------------------------------------


def test_check_report_body_sensitivity_global_sentinel_fails_closed(tmp_path: Path) -> None:
    """check_report_body_sensitivity_global with an IO-error sentinel → fail closed.

    If any run's sources/ directory is unreadable, build_global_source_index
    inserts a sentinel entry.  check_report_body_sensitivity_global detects it
    and returns a fail-closed error result (severity=error, status=fail).
    This test exercises that path directly without filesystem manipulation.
    """
    from research_foundry.services.verification import (
        _IO_ERROR_SENTINEL_PREFIX,
        check_report_body_sensitivity_global,
    )

    # Construct an index with a sentinel (simulates an unreadable sources/ dir)
    sentinel_index = {
        f"{_IO_ERROR_SENTINEL_PREFIX}rf_run_broken": ("unknown", "restricted")
    }
    blocks = [
        {"block_id": "blk_1", "markdown": "Some safe text.", "block_type": "paragraph"}
    ]

    # paths is not used when the sentinel is detected (function returns early)
    result = check_report_body_sensitivity_global(
        paths=None,  # type: ignore[arg-type]  — not reached when sentinel present
        blocks=blocks,
        global_source_index=sentinel_index,
    )

    assert result.status == "fail", (
        "Expected status='fail' when global source index contains a sentinel entry"
    )
    assert result.severity == "error", (
        "Expected severity='error' — sentinel means we cannot confirm safety"
    )
    assert "unreadable" in result.detail.lower() or "cannot verify" in result.detail.lower(), (
        f"Expected 'unreadable' or 'cannot verify' in detail, got: {result.detail!r}"
    )


def test_publish_preview_non_existent_report_reviewer_gets_403(tmp_path: Path) -> None:
    """Reviewer gets 403 for a non-existent report (RBAC existence pre-check).

    When the report doesn't exist AND the caller lacks report:publish permission,
    403 is returned instead of 404 to prevent probing for non-existent report IDs.
    This preserves the existing test_rbac_reports.py behavior.
    """
    cfg = _make_config(tmp_path)
    client = _make_client(cfg, identity=AuthIdentity("r", "ws1", ("reviewer",)))
    resp = client.post("/api/reports/rpt_does_not_exist_xyz/publish-preview")
    assert resp.status_code == 403, (
        f"Reviewer expected 403 on a non-existent report (existence pre-check), "
        f"got {resp.status_code}"
    )


def test_publish_preview_non_existent_report_owner_gets_404(tmp_path: Path) -> None:
    """Owner gets 404 for a non-existent report (report not found, no RBAC block)."""
    cfg = _make_config(tmp_path)
    client = _make_client(cfg, identity=AuthIdentity("o", "ws1", ("owner",)))
    resp = client.post("/api/reports/rpt_does_not_exist_xyz/publish-preview")
    assert resp.status_code == 404, (
        f"Owner expected 404 on a non-existent report, got {resp.status_code}"
    )


# ---------------------------------------------------------------------------
# RBAC toggle regression tests (DEFECT P2 fix)
# ---------------------------------------------------------------------------


def _make_client_rbac_disabled(
    cfg: FoundryConfig, identity: AuthIdentity | None = None
) -> TestClient:
    """Build a TestClient with RBAC globally disabled (simulates rbac_enforcement=disabled).

    Sets ``app.state.rbac_enforced = False`` after ``create_app`` so the manual
    role gate in ``publish_preview`` sees the same flag as ``require_role()``.
    """
    app = create_app(cfg)
    app.dependency_overrides[get_paths] = lambda: cfg.paths
    app.state.rbac_enforced = False  # Override: simulate loopback/disabled mode
    app.add_middleware(_InjectIdentityMiddleware, identity=identity)
    return TestClient(app, raise_server_exceptions=True)


def test_publish_preview_rbac_disabled_non_admin_gets_200_on_clean_draft(
    tmp_path: Path,
) -> None:
    """RBAC disabled: researcher CAN invoke publish-preview and gets 200 on a clean draft.

    Regression for DEFECT P2: the manual role check in publish_preview was not
    reading app.state.rbac_enforced, so it rejected non-admins even when RBAC
    was globally disabled (loopback mode).  This test FAILS before the fix.
    """
    cfg = _make_config(tmp_path)

    # Create a clean draft via a no-auth client (shares the same filesystem paths)
    noauth_client = _make_client(cfg, identity=None)
    created = noauth_client.post(
        "/api/reports",
        json={"origin": "blank", "title": "RBAC Disabled Clean"},
    ).json()
    rid = created["report_draft_id"]
    noauth_client.post(
        f"/api/reports/{rid}/blocks",
        json={"markdown": "Background context.", "materiality": "narrative"},
    )

    # Researcher calling with RBAC disabled — must get 200, not 403
    client = _make_client_rbac_disabled(
        cfg, identity=AuthIdentity("r", "ws1", ("researcher",))
    )
    resp = client.post(f"/api/reports/{rid}/publish-preview")
    assert resp.status_code == 200, (
        f"Expected 200 when rbac_enforced=False (RBAC disabled), "
        f"researcher got {resp.status_code}. "
        "DEFECT: manual role check in publish_preview must honor the rbac_enforced toggle."
    )
    assert resp.json()["ok"] is True


def test_publish_preview_rbac_disabled_sensitivity_violation_still_422(
    tmp_path: Path,
) -> None:
    """RBAC disabled: sensitivity gate is absolute — non-admin still gets 422 on violation.

    The RBAC toggle ONLY affects the role/authz check (step 3, 403).
    The sensitivity gate (PRD AC-2, step 2, 422) is role-independent and must
    fire regardless of RBAC mode.  Disabling RBAC must NEVER bypass sensitivity.
    """
    cfg = _make_config(tmp_path)
    rid = _create_draft_with_sensitivity_violation(cfg)

    # Researcher with RBAC disabled — sensitivity gate must still fire 422
    client = _make_client_rbac_disabled(
        cfg, identity=AuthIdentity("r", "ws1", ("researcher",))
    )
    resp = client.post(f"/api/reports/{rid}/publish-preview")
    assert resp.status_code == 422, (
        f"Expected 422 on sensitivity violation even with RBAC disabled, "
        f"got {resp.status_code}. "
        "CRITICAL INVARIANT: the sensitivity gate must remain absolute and cannot "
        "be bypassed by the RBAC enforcement toggle."
    )
    detail = resp.json()["detail"]
    assert detail["ok"] is False
    blocking_ids = [c["id"] for c in detail.get("blocking", [])]
    assert (
        "report_body_sensitivity" in blocking_ids
        or "report_body_sensitivity_global" in blocking_ids
    ), f"Expected sensitivity check in blocking list, got: {blocking_ids!r}"


def test_publish_preview_rbac_enabled_non_admin_still_403(tmp_path: Path) -> None:
    """RBAC enabled (default): researcher still gets 403 on a clean draft.

    Confirms the fix is backward-compatible — when rbac_enforced is True (or not
    explicitly False), the role gate is unchanged and researcher is still denied.
    """
    cfg = _make_config(tmp_path)

    # Create a clean draft
    noauth_client = _make_client(cfg, identity=None)
    created = noauth_client.post(
        "/api/reports",
        json={"origin": "blank", "title": "RBAC Enabled Clean"},
    ).json()
    rid = created["report_draft_id"]
    noauth_client.post(
        f"/api/reports/{rid}/blocks",
        json={"markdown": "Background text.", "materiality": "narrative"},
    )

    # Researcher with RBAC enabled (default via _make_client) — must still get 403
    client = _make_client(cfg, identity=AuthIdentity("r", "ws1", ("researcher",)))
    resp = client.post(f"/api/reports/{rid}/publish-preview")
    assert resp.status_code == 403, (
        f"Expected 403 when rbac_enforced=True (RBAC enabled), "
        f"researcher got {resp.status_code}. "
        "The fix must not weaken RBAC enforcement when it is enabled."
    )
