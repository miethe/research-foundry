"""Unit tests for `rf-knowledge-mcp`'s read-only settings + allowlist (KMCP-4.1).

Proves decisions-block §9.3: workspace-root resolution reuses the existing
`FoundryPaths.discover` mechanism, an optional sensitivity ceiling is read
from a DEDICATED `foundry.knowledge_mcp.*` config namespace (never the
Search Router's own `foundry.mcp.*` block), a namespaced log-level env var
is honored, and the module never reads anything outside its own declared
`ALLOWED_ENV_VARS` allowlist.
"""

from __future__ import annotations

from typing import Any

import pytest

from research_foundry.knowledge_mcp import settings as kmcp_settings
from research_foundry.paths import FoundryPaths
from research_foundry.yamlio import dump_yaml, load_yaml


def test_resolve_settings_defaults(tmp_foundry: FoundryPaths) -> None:
    resolved = kmcp_settings.resolve_settings(tmp_foundry)
    assert resolved.paths == tmp_foundry
    assert resolved.sensitivity_threshold_max is None
    assert resolved.log_level == kmcp_settings.DEFAULT_LOG_LEVEL


def test_resolve_settings_reads_dedicated_config_namespace(tmp_foundry: FoundryPaths) -> None:
    data: dict[str, Any] = load_yaml(tmp_foundry.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"]["knowledge_mcp"] = {"sensitivity_threshold_max": "personal"}
    dump_yaml(data, tmp_foundry.foundry_yaml)

    resolved = kmcp_settings.resolve_settings(tmp_foundry)
    assert resolved.sensitivity_threshold_max == "personal"


def test_resolve_settings_ignores_search_router_config_namespace(tmp_foundry: FoundryPaths) -> None:
    """A `foundry.mcp.sensitivity_threshold_max` value (the Search Router's
    OWN config knob -- `search_router.mcp_launcher.resolve_sensitivity_ceiling`)
    must never leak into `rf-knowledge-mcp`'s settings; the two processes use
    disjoint config namespaces by design (module docstring)."""

    data: dict[str, Any] = load_yaml(tmp_foundry.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"]["mcp"] = {"sensitivity_threshold_max": "public"}
    dump_yaml(data, tmp_foundry.foundry_yaml)

    resolved = kmcp_settings.resolve_settings(tmp_foundry)
    assert resolved.sensitivity_threshold_max is None


def test_resolve_settings_honors_namespaced_log_level_env(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(kmcp_settings.LOG_LEVEL_ENV, "DEBUG")
    resolved = kmcp_settings.resolve_settings(tmp_foundry)
    assert resolved.log_level == "DEBUG"


def test_resolve_settings_defaults_paths_via_discover(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    monkeypatch.setenv(kmcp_settings.WORKSPACE_ROOT_ENV, str(tmp_path))
    resolved = kmcp_settings.resolve_settings()
    assert resolved.paths.root == tmp_path.resolve()


def test_allowed_env_vars_is_exact_and_minimal() -> None:
    assert kmcp_settings.ALLOWED_ENV_VARS == (
        kmcp_settings.WORKSPACE_ROOT_ENV,
        kmcp_settings.LOG_LEVEL_ENV,
    )


def test_resolve_settings_never_reads_env_outside_allowlist(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulate a poisoned environment carrying Search Router / Operator /
    writeback credentials and prove `resolve_settings` never reads any of
    them -- the returned settings are unaffected by their presence."""

    poisoned = {
        "RF_MCP_PRINCIPAL_USER_ID": "attacker",
        "RF_MCP_PRINCIPAL_WORKSPACE_ID": "attacker-workspace",
        "RF_TOKEN_AGENT": "super-secret-token",
        "BRAVE_API_KEY": "brave-secret",
        "MEATYWIKI_TOKEN": "wiki-secret",
    }
    for key, value in poisoned.items():
        monkeypatch.setenv(key, value)

    resolved = kmcp_settings.resolve_settings(tmp_foundry)
    assert resolved.sensitivity_threshold_max is None
    assert resolved.log_level == kmcp_settings.DEFAULT_LOG_LEVEL
    assert resolved.paths == tmp_foundry
