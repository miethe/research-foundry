"""Integration-level wiring tests for ACT-102 (public-multiuser-release-activation
Phase 1): ``rf serve --mode`` CLI flag + ``deployment_mode_validate()`` called
at ``create_app()`` startup.

Structurally mirrors ``tests/test_seal_cli_flag.py`` (CLI wiring smoke test
pattern) and ``tests/test_config_workspace_enforcement.py`` (create_app()
fail-closed pattern). Unit-level coverage of the gate's decision logic itself
lives in ``tests/unit/test_deployment_mode.py`` — this file only verifies the
two call sites (CLI + app startup) are actually wired.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi import FastAPI
from typer.testing import CliRunner

from research_foundry.api.app import create_app
from research_foundry.cli import app
from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.yamlio import dump_yaml, load_yaml

runner = CliRunner()


def _scaffold_workspace(tmp_path: Path) -> Path:
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
    return root


@pytest.fixture()
def workspace(tmp_path, monkeypatch):
    root = _scaffold_workspace(tmp_path)
    monkeypatch.chdir(root)
    return root


# ---------------------------------------------------------------------------
# FR-5: rf serve --mode flag
# ---------------------------------------------------------------------------


class TestServeModeFlag:
    def test_mode_multi_user_without_provider_refuses_before_binding(self, workspace):
        """--mode multi_user with no auth.provider configured must exit 1
        WITHOUT ever reaching create_app()/uvicorn.run() — the gate stub
        (condition a) fires first."""
        result = runner.invoke(app, ["serve", "--mode", "multi_user"])

        assert result.exit_code == 1
        assert "multi_user" in result.output
        assert "(a)" in result.output

    def test_mode_single_user_is_default_and_does_not_gate(self, workspace):
        """Omitting --mode entirely must behave exactly as before this
        feature existed (FR-2) — no gate error, CLI flag is optional."""
        foundry_yaml = workspace / "foundry.yaml"
        existing = load_yaml(foundry_yaml) or {}
        existing.setdefault("foundry", {})["viewer"] = {
            **(existing.get("foundry", {}).get("viewer") or {}),
            "bind_host": "127.0.0.1",
        }
        dump_yaml(existing, foundry_yaml)

        with pytest.MonkeyPatch.context() as mp:
            # Avoid actually starting a live server: stub uvicorn.run.
            mp.setattr("uvicorn.run", lambda *a, **k: None)
            result = runner.invoke(app, ["serve"])

        assert result.exit_code == 0, result.output
        assert "(a)" not in result.output

    def test_explicit_mode_single_user_flag_does_not_gate(self, workspace):
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("uvicorn.run", lambda *a, **k: None)
            result = runner.invoke(app, ["serve", "--mode", "single_user"])

        assert result.exit_code == 0, result.output

    def test_invalid_mode_value_refused(self, workspace):
        result = runner.invoke(app, ["serve", "--mode", "bogus"])

        assert result.exit_code == 1
        assert "deployment_mode" in result.output


# ---------------------------------------------------------------------------
# create_app() startup wiring
# ---------------------------------------------------------------------------


def _config_with_mode(
    tmp_path: Path,
    *,
    deployment_mode: str,
    provider: str = "none",
    di1_accepted: bool = False,
) -> FoundryConfig:
    """``di1_accepted`` (Phase 4 ACT-402) — when ``True``, also satisfies
    condition (d): writes a throwaway ``status: accepted`` audit artifact
    and sets ``auth.di1_audit_acknowledged``. Defaults ``False`` so existing
    condition-(a)-only tests (e.g. the ``provider=none`` refusal case) are
    unaffected — they fail on (a) regardless of (d)'s state.
    """
    root = _scaffold_workspace(tmp_path)
    foundry_yaml = root / "foundry.yaml"
    existing = load_yaml(foundry_yaml) or {}
    existing.setdefault("foundry", {})["deployment_mode"] = deployment_mode
    auth_block = {**(existing["foundry"].get("auth") or {}), "provider": provider}
    if di1_accepted:
        audit_path = tmp_path / "di1-audit-accepted.md"
        audit_path.write_text("---\nstatus: accepted\n---\n\nbody\n", encoding="utf-8")
        auth_block["di1_audit_acknowledged"] = True
        auth_block["di1_audit_report_path"] = str(audit_path)
    existing["foundry"]["auth"] = auth_block
    dump_yaml(existing, foundry_yaml)
    return FoundryConfig(paths=FoundryPaths(root=root))


class TestCreateAppDeploymentModeGate:
    def test_single_user_builds_normally(self, tmp_path):
        config = _config_with_mode(tmp_path, deployment_mode="single_user")
        app_instance = create_app(config)
        assert isinstance(app_instance, FastAPI)

    def test_multi_user_with_provider_none_raises_before_app_object_exists(self, tmp_path):
        config = _config_with_mode(tmp_path, deployment_mode="multi_user", provider="none")
        with pytest.raises(ValueError, match=r"\(a\)"):
            create_app(config)

    def test_multi_user_with_provider_configured_builds(self, tmp_path):
        config = _config_with_mode(
            tmp_path,
            deployment_mode="multi_user",
            provider="local_static",
            di1_accepted=True,
        )
        app_instance = create_app(config)
        assert isinstance(app_instance, FastAPI)
        # multi_user preset defaults these to enforced (FR-3).
        assert app_instance.state.rbac_enforced is True
        assert app_instance.state.workspace_isolation_enforced is True
