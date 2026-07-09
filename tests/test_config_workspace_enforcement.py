"""App-integration-level tests for the ``workspace_isolation_enforcement`` flag
(WKSP-304 Phase 5, TASK-5.6 / AC-7).

Structurally mirrors ``tests/unit/test_rbac_enforcement_toggle.py`` (the
sibling ``auth.rbac_enforcement`` toggle's integration-level scenarios), but
targets ``create_app()`` / ``app.state.workspace_isolation_enforced`` for the
orthogonal ``workspace_isolation_enforcement`` flag instead.

This file extends — and does not duplicate — the config-module-level unit
coverage already in ``tests/unit/test_workspace_isolation_enforcement_flag.py``
(parser + ``resolve_workspace_isolation_enforced()`` called directly). Here we
actually construct the FastAPI app via ``create_app()`` and assert the
ValueError/resolution behaviour observable at app-create time, across the
full matrix:

    workspace_isolation_enforcement (auto | enabled | disabled)
        x bind_host (loopback | non-loopback)
        x auth.provider (none | other)

Mandatory scenarios (AC-7):
  - disabled + non-loopback bind_host -> ValueError raised at app-create time
    (mirrors the auth.rbac_enforcement fail-closed startup check).
  - disabled + loopback bind_host -> app builds; enforcement resolves to
    disabled/advisory (False).
  - enabled -> always enforced (True) regardless of loopback/provider.
  - auto + provider=none -> advisory (False), not enforced.
  - auto + provider!=none -> enforced (True).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI

from research_foundry.api.app import create_app
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LOOPBACK_HOST = "127.0.0.1"
_NON_LOOPBACK_HOST = "0.0.0.0"

_PROVIDER_NONE = "none"
_PROVIDER_OTHER = "local_static"


def _make_config(
    tmp_path: Path,
    *,
    provider: str = _PROVIDER_NONE,
    workspace_isolation_enforcement: str = "auto",
    bind_host: str = _LOOPBACK_HOST,
) -> FoundryConfig:
    """Create a temporary full workspace with the given auth/isolation settings.

    Mirrors ``test_rbac_enforcement_toggle.py::_make_config`` — copies the
    canonical distribution (schemas/config/templates) so ``create_app()`` can
    fully wire routers, then overlays ``foundry.auth.provider``,
    ``foundry.viewer.bind_host``, and the top-level
    ``foundry.workspace_isolation_enforcement`` key (a sibling of ``auth:``,
    not nested under it — see ``FoundryConfig.workspace_isolation_enforcement``
    docstring for why).
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

    # viewer block
    viewer: dict[str, Any] = dict(existing["foundry"].get("viewer") or {})
    viewer["auth_mode"] = "none"
    viewer["bind_host"] = bind_host
    existing["foundry"]["viewer"] = viewer

    # auth block (auth.provider only — rbac_enforcement stays default/auto,
    # orthogonal to the flag under test here)
    auth: dict[str, Any] = dict(existing["foundry"].get("auth") or {})
    auth["provider"] = provider
    existing["foundry"]["auth"] = auth

    # workspace_isolation_enforcement: TOP-LEVEL sibling of auth:, not nested.
    existing["foundry"]["workspace_isolation_enforcement"] = workspace_isolation_enforcement

    dump_yaml(existing, foundry_yaml_path)
    return FoundryConfig(paths=FoundryPaths(root=root))


# ---------------------------------------------------------------------------
# disabled + non-loopback -> ValueError at app-create time
# ---------------------------------------------------------------------------


class TestDisabledNonLoopbackRaisesAtAppCreate:
    """disabled + non-loopback bind_host -> create_app() must raise ValueError.

    Mirrors the fail-closed ``auth.rbac_enforcement=disabled`` startup gate
    (test_rbac_enforcement_toggle.py::TestScenarioD_DisabledNonLoopbackRefused).
    """

    @pytest.mark.parametrize("provider", [_PROVIDER_NONE, _PROVIDER_OTHER])
    def test_disabled_nonloopback_raises_regardless_of_provider(self, tmp_path, provider):
        config = _make_config(
            tmp_path,
            provider=provider,
            workspace_isolation_enforcement="disabled",
            bind_host=_NON_LOOPBACK_HOST,
        )
        with pytest.raises(ValueError, match="non-loopback"):
            create_app(config)

    def test_disabled_lan_ip_also_raises(self, tmp_path):
        """A LAN-routable IP is not loopback — must also be refused at create_app()."""
        config = _make_config(
            tmp_path,
            provider=_PROVIDER_NONE,
            workspace_isolation_enforcement="disabled",
            bind_host="10.42.10.76",
        )
        with pytest.raises(ValueError, match="non-loopback"):
            create_app(config)


# ---------------------------------------------------------------------------
# disabled + loopback -> app builds; resolves to disabled/advisory (False)
# ---------------------------------------------------------------------------


class TestDisabledLoopbackBuildsAdvisory:
    """disabled + loopback bind_host -> app builds; state resolves to False."""

    @pytest.mark.parametrize("provider", [_PROVIDER_NONE, _PROVIDER_OTHER])
    def test_app_builds_and_state_is_false(self, tmp_path, provider):
        config = _make_config(
            tmp_path,
            provider=provider,
            workspace_isolation_enforcement="disabled",
            bind_host=_LOOPBACK_HOST,
        )
        app = create_app(config)
        assert isinstance(app, FastAPI)
        assert app.state.workspace_isolation_enforced is False


# ---------------------------------------------------------------------------
# enabled -> always enforced (True) regardless of loopback/provider
# ---------------------------------------------------------------------------


class TestEnabledAlwaysEnforced:
    """enabled -> app.state.workspace_isolation_enforced is True in every combo."""

    @pytest.mark.parametrize("bind_host", [_LOOPBACK_HOST, _NON_LOOPBACK_HOST])
    @pytest.mark.parametrize("provider", [_PROVIDER_NONE, _PROVIDER_OTHER])
    def test_enabled_is_always_true(self, tmp_path, provider, bind_host):
        config = _make_config(
            tmp_path,
            provider=provider,
            workspace_isolation_enforcement="enabled",
            bind_host=bind_host,
        )
        # enabled has no fail-closed bind_host gate (only disabled does) —
        # create_app must not raise here.
        app = create_app(config)
        assert app.state.workspace_isolation_enforced is True


# ---------------------------------------------------------------------------
# auto + provider=none -> advisory (False)
# ---------------------------------------------------------------------------


class TestAutoProviderNoneAdvisory:
    """auto + auth.provider=none -> not enforced (False), regardless of bind_host."""

    @pytest.mark.parametrize("bind_host", [_LOOPBACK_HOST, _NON_LOOPBACK_HOST])
    def test_auto_none_resolves_false(self, tmp_path, bind_host):
        config = _make_config(
            tmp_path,
            provider=_PROVIDER_NONE,
            workspace_isolation_enforcement="auto",
            bind_host=bind_host,
        )
        app = create_app(config)
        assert app.state.workspace_isolation_enforced is False


# ---------------------------------------------------------------------------
# auto + provider!=none -> enforced (True)
# ---------------------------------------------------------------------------


class TestAutoProviderOtherEnforced:
    """auto + auth.provider!=none -> enforced (True), regardless of bind_host."""

    @pytest.mark.parametrize("bind_host", [_LOOPBACK_HOST, _NON_LOOPBACK_HOST])
    def test_auto_other_provider_resolves_true(self, tmp_path, bind_host):
        config = _make_config(
            tmp_path,
            provider=_PROVIDER_OTHER,
            workspace_isolation_enforcement="auto",
            bind_host=bind_host,
        )
        app = create_app(config)
        assert app.state.workspace_isolation_enforced is True
