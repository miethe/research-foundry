"""Unit tests for the ``workspace_isolation_enforcement`` config flag parser
and resolver (WKSP-304 TASK-1.1 / TASK-1.2).

Structurally mirrors the config-level unit tests for ``auth.rbac_enforcement``
in ``tests/unit/test_rbac_enforcement_toggle.py`` (``TestResolveRbacEnforced``),
scoped to the config/resolver-function level only — no FastAPI ``TestClient``
app. This flag remains INERT as of TASK-1.2: the resolver and
``app.state.workspace_isolation_enforced`` wiring are exercised here, but
nothing in the app reads/consumes the resolved value yet to make an
enforcement decision (that lands in Phase 4).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from research_foundry.config import FoundryConfig, WorkspaceIsolationEnforcement
from research_foundry.paths import FoundryPaths
from research_foundry.yamlio import dump_yaml


def _make_config(
    tmp_path: Path,
    *,
    workspace_isolation_enforcement: str | None = None,
    provider: str | None = None,
    bind_host: str | None = None,
) -> FoundryConfig:
    """Create a minimal workspace with the given top-level flag value.

    Unlike the full RBAC toggle suite's ``_make_config`` helper, this does
    not need to copy the full distribution (schemas/config/templates) or
    stand up a FastAPI app — the parser and resolver under test only read
    ``foundry.yaml``. ``provider``/``bind_host`` are optional and only
    needed by the resolver test matrix (``TestResolveWorkspaceIsolationEnforced``);
    the parser tests above ignore them.
    """
    root = tmp_path / "fdry"
    root.mkdir(parents=True, exist_ok=True)
    foundry: dict = {"owner": "Test"}
    if workspace_isolation_enforcement is not None:
        foundry["workspace_isolation_enforcement"] = workspace_isolation_enforcement
    if bind_host is not None:
        foundry["viewer"] = {"bind_host": bind_host}
    if provider is not None:
        foundry["auth"] = {"provider": provider}
    dump_yaml({"foundry": foundry}, root / "foundry.yaml")
    return FoundryConfig(paths=FoundryPaths(root=root))


class TestWorkspaceIsolationEnforcementParsing:
    """Parser accepts all 3 valid values; raises ValueError on anything else."""

    def test_default_is_auto(self, tmp_path):
        """Absent key defaults to ``auto`` (mirrors auth.rbac_enforcement default)."""
        cfg = _make_config(tmp_path)
        assert cfg.workspace_isolation_enforcement() == WorkspaceIsolationEnforcement.AUTO

    def test_parses_auto(self, tmp_path):
        cfg = _make_config(tmp_path, workspace_isolation_enforcement="auto")
        assert cfg.workspace_isolation_enforcement() == WorkspaceIsolationEnforcement.AUTO

    def test_parses_enabled(self, tmp_path):
        cfg = _make_config(tmp_path, workspace_isolation_enforcement="enabled")
        assert cfg.workspace_isolation_enforcement() == WorkspaceIsolationEnforcement.ENABLED

    def test_parses_disabled(self, tmp_path):
        cfg = _make_config(tmp_path, workspace_isolation_enforcement="disabled")
        assert cfg.workspace_isolation_enforcement() == WorkspaceIsolationEnforcement.DISABLED

    def test_parsing_is_case_insensitive(self, tmp_path):
        cfg = _make_config(tmp_path, workspace_isolation_enforcement="ENABLED")
        assert cfg.workspace_isolation_enforcement() == WorkspaceIsolationEnforcement.ENABLED

    def test_invalid_value_raises_value_error_listing_valid_values(self, tmp_path):
        cfg = _make_config(tmp_path, workspace_isolation_enforcement="bogus")
        with pytest.raises(ValueError, match="auto, disabled, enabled"):
            cfg.workspace_isolation_enforcement()


class TestResolveWorkspaceIsolationEnforced:
    """Unit tests for FoundryConfig.resolve_workspace_isolation_enforced()
    (WKSP-304 TASK-1.2).

    Mirrors ``TestResolveRbacEnforced`` in test_rbac_enforcement_toggle.py,
    but note the ``AUTO`` truth table differs deliberately: this resolver's
    ``AUTO`` branch returns the literal provider-keyed bool (``provider !=
    "none"``), whereas ``resolve_rbac_enforced``'s ``AUTO`` branch always
    returns ``True`` (RBAC's provider-keyed semantics are realized via the
    identity-None passthrough in ``require_role`` instead). See the
    docstring on ``resolve_workspace_isolation_enforced`` for the full
    reasoning.
    """

    def test_auto_none_provider_is_false(self, tmp_path):
        """AUTO + provider=none → advisory-only (False), unlike resolve_rbac_enforced."""
        cfg = _make_config(tmp_path, workspace_isolation_enforcement="auto")
        assert cfg.resolve_workspace_isolation_enforced("none", "127.0.0.1") is False

    def test_auto_local_static_is_true(self, tmp_path):
        """AUTO + provider != none → enforced (True)."""
        cfg = _make_config(tmp_path, workspace_isolation_enforcement="auto")
        assert cfg.resolve_workspace_isolation_enforced("local_static", "127.0.0.1") is True

    def test_enabled_is_always_true(self, tmp_path):
        """ENABLED forces True regardless of provider."""
        cfg = _make_config(tmp_path, workspace_isolation_enforcement="enabled")
        assert cfg.resolve_workspace_isolation_enforced("none", "127.0.0.1") is True

    def test_disabled_loopback_is_false(self, tmp_path):
        """DISABLED + loopback bind → allowed, returns False."""
        cfg = _make_config(
            tmp_path, workspace_isolation_enforcement="disabled", bind_host="127.0.0.1"
        )
        assert cfg.resolve_workspace_isolation_enforced("none", "127.0.0.1") is False

    def test_disabled_nonloopback_raises(self, tmp_path):
        """DISABLED + non-loopback bind → fail-closed ValueError."""
        cfg = _make_config(
            tmp_path, workspace_isolation_enforcement="disabled", bind_host="0.0.0.0"
        )
        with pytest.raises(ValueError, match="non-loopback"):
            cfg.resolve_workspace_isolation_enforced("none", "0.0.0.0")

    def test_disabled_lan_ip_raises(self, tmp_path):
        """DISABLED + LAN-routable IP (not loopback) → also refused."""
        cfg = _make_config(
            tmp_path, workspace_isolation_enforcement="disabled", bind_host="10.42.10.76"
        )
        with pytest.raises(ValueError, match="non-loopback"):
            cfg.resolve_workspace_isolation_enforced("none", "10.42.10.76")
