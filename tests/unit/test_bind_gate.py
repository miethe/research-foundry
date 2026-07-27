"""Unit tests for the shared non-loopback bind safety gate.

DI-1 delta re-audit remediation, finding F1(2)
(``docs/project_plans/reports/audits/di-1-delta-reaudit-2026-07-26.md``):
``create_app`` is directly ASGI-mountable — uvicorn, gunicorn, or any other
runner can construct it without ever going through the ``rf serve`` CLI, so
the CLI's own pre-bind gate
(``research_foundry.cli_commands._validate_nonloopback_bind``) is not a
complete guarantee. ``research_foundry.api._bind_gate.assert_bind_is_safe``
is the invariant enforced INSIDE ``create_app`` itself (regardless of
caller) so a non-loopback bind can never produce a fully-open server. See
``research_foundry/api/_bind_gate.py`` for the full rationale.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI

from research_foundry.api._bind_gate import assert_bind_is_safe
from research_foundry.api.app import create_app
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.yamlio import dump_yaml, load_yaml

_LOOPBACK_HOST = "127.0.0.1"
_NON_LOOPBACK_HOST = "0.0.0.0"


def _make_config(
    tmp_path: Path,
    *,
    bind_host: str,
    provider: str = "none",
    auth_mode: str = "none",
) -> FoundryConfig:
    """Build a minimal full workspace — ``create_app()`` needs the real
    schemas/config/templates distribution to wire its routers.

    ``deployment_mode`` is pinned to ``"single_user"`` explicitly so the
    DI-1 delta re-audit remediation's G1 bind/auth-based ``multi_user``
    INFERENCE can never interfere with this file's bind-gate-only matrix
    (an inferred ``multi_user`` would raise on the separate, unconfigured
    DI-1-acknowledgment condition instead of exercising the bind gate this
    file targets) — mirrors the identical rationale in
    ``tests/test_config_workspace_enforcement.py::_make_config``.

    Phase 5 "G1-precedence" hardening: an explicit ``deployment_mode:
    single_user`` on a non-loopback, auth-enabled bind now requires a
    declared ``trusted_single_operator_posture`` or ``deployment_mode()``
    raises at load. A fully-populated posture is declared unconditionally
    alongside the pin above (inert for the loopback/no-auth cases; the
    escape hatch this file's non-loopback + real-auth-provider / legacy
    ``auth_mode=token`` cases now need instead of hitting the new gate).
    """
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
    viewer["bind_host"] = bind_host
    viewer["auth_mode"] = auth_mode
    existing["foundry"]["viewer"] = viewer

    auth: dict[str, Any] = dict(existing["foundry"].get("auth") or {})
    auth["provider"] = provider
    existing["foundry"]["auth"] = auth

    existing["foundry"]["deployment_mode"] = "single_user"

    # Phase 5 "G1-precedence" hardening: see docstring above.
    existing["foundry"]["trusted_single_operator_posture"] = {
        "declared": True,
        "rationale": (
            "test fixture: exercises the bind-gate-only matrix, not the "
            "G1 bind/auth inference gate"
        ),
        "declared_at": "2026-07-27",
        "declared_by": "test-fixture",
    }

    dump_yaml(existing, foundry_yaml_path)
    return FoundryConfig(paths=FoundryPaths(root=root))


# ---------------------------------------------------------------------------
# Direct unit coverage of assert_bind_is_safe() — no FastAPI app needed.
# ---------------------------------------------------------------------------


class TestAssertBindIsSafeUnit:
    def test_nonloopback_no_auth_raises(self, tmp_path):
        config = _make_config(tmp_path, bind_host=_NON_LOOPBACK_HOST, provider="none")
        with pytest.raises(ValueError, match="non-loopback"):
            assert_bind_is_safe(config)

    def test_nonloopback_with_local_static_provider_does_not_raise(self, tmp_path):
        config = _make_config(
            tmp_path, bind_host=_NON_LOOPBACK_HOST, provider="local_static"
        )
        assert_bind_is_safe(config)  # must not raise

    def test_nonloopback_with_legacy_token_auth_mode_does_not_raise(self, tmp_path):
        """The legacy viewer.auth_mode=token path also satisfies the gate —
        is_auth_enabled() covers both, matching _validate_nonloopback_bind's
        own Gate 1 semantics."""
        config = _make_config(
            tmp_path, bind_host=_NON_LOOPBACK_HOST, provider="none", auth_mode="token"
        )
        assert_bind_is_safe(config)  # must not raise

    def test_loopback_no_auth_never_raises(self, tmp_path):
        config = _make_config(tmp_path, bind_host=_LOOPBACK_HOST, provider="none")
        assert_bind_is_safe(config)  # must not raise

    def test_lan_ip_no_auth_also_raises(self, tmp_path):
        """A LAN-routable IP is not loopback — must also be refused."""
        config = _make_config(tmp_path, bind_host="10.42.10.76", provider="none")
        with pytest.raises(ValueError, match="non-loopback"):
            assert_bind_is_safe(config)


# ---------------------------------------------------------------------------
# Integration-level: create_app() itself enforces the gate, regardless of
# caller — the DI-1 delta re-audit's exposure (B) is a DIRECT create_app()
# mount, never routed through `rf serve` at all.
# ---------------------------------------------------------------------------


class TestCreateAppEnforcesBindGate:
    def test_nonloopback_bind_no_auth_raises_at_create_app(self, tmp_path):
        """bind_host=0.0.0.0 + auth.provider=none -> create_app() raises."""
        config = _make_config(tmp_path, bind_host=_NON_LOOPBACK_HOST, provider="none")
        with pytest.raises(ValueError, match="non-loopback"):
            create_app(config)

    def test_nonloopback_bind_with_auth_configured_does_not_raise(self, tmp_path):
        """Same bind_host, but with a real auth provider configured (auth
        present) — the gate is satisfied and create_app() builds normally."""
        config = _make_config(
            tmp_path, bind_host=_NON_LOOPBACK_HOST, provider="local_static"
        )
        app = create_app(config)
        assert isinstance(app, FastAPI)
