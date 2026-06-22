"""Tests for the RF ``serve`` CLI command and core footprint isolation (TEST-008, TEST-010).

Coverage:
  TEST-008  (CRITICAL) Fail-closed bind checks via CliRunner with uvicorn.run stubbed:
              - ``rf serve --bind-host 0.0.0.0 --auth-mode none``  → nonzero exit
              - ``rf serve --bind-host 0.0.0.0 --auth-mode token`` with token unset → nonzero
              - ``rf serve --bind-host 0.0.0.0 --auth-mode token`` with token set   → exit 0
              - loopback bind with no auth → exit 0 (no restriction)
  TEST-010  Core footprint isolation: importing research_foundry must NOT also
            import fastapi, even when fastapi is installed.
            (Full "no-extra install" assertion belongs to CI; here we verify the
            import guard is wired correctly by checking that fastapi is not
            imported as a side-effect of ``import research_foundry``.)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.paths import FoundryPaths, distribution_root

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scaffold_workspace(tmp_path: Path) -> Path:
    """Create a minimal foundry workspace under tmp_path and return its root."""
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
    (root / "runs").mkdir(exist_ok=True)
    return root


def _invoke_serve(args: list[str], cwd: Path, env_extra: dict | None = None) -> object:
    """Run ``rf serve`` from *cwd* with uvicorn.run stubbed to a no-op.

    Uses os.chdir so workspace discovery finds the right foundry.yaml.
    uvicorn.run is patched so no port is ever opened in tests.
    """
    prev = Path.cwd()
    env_patch = {**os.environ}
    if env_extra:
        env_patch.update(env_extra)

    # Ensure RF_SERVE_TOKEN is absent unless caller supplies it.
    if env_extra is None or "RF_SERVE_TOKEN" not in env_extra:
        env_patch.pop("RF_SERVE_TOKEN", None)

    os.chdir(cwd)
    try:
        with patch.dict("os.environ", env_patch, clear=True):
            with patch("uvicorn.run", MagicMock()):
                return runner.invoke(app, ["serve"] + args)
    finally:
        os.chdir(prev)


# ---------------------------------------------------------------------------
# TEST-008  Fail-closed bind checks
# ---------------------------------------------------------------------------


class TestServeFailClosed:
    """Fail-closed pre-bind security invariants (TEST-008)."""

    def test_lan_bind_without_auth_mode_is_rejected(self, tmp_path):
        """``--bind-host 0.0.0.0 --auth-mode none`` → nonzero exit (no open port)."""
        root = _scaffold_workspace(tmp_path)
        result = _invoke_serve(
            ["--bind-host", "0.0.0.0", "--auth-mode", "none"],
            cwd=root,
        )
        assert result.exit_code != 0, (
            f"Expected nonzero exit, got {result.exit_code}. Output: {result.output}"
        )

    def test_lan_bind_auth_token_but_env_unset_is_rejected(self, tmp_path):
        """``--bind-host 0.0.0.0 --auth-mode token`` with RF_SERVE_TOKEN unset → nonzero."""
        root = _scaffold_workspace(tmp_path)
        result = _invoke_serve(
            ["--bind-host", "0.0.0.0", "--auth-mode", "token"],
            cwd=root,
            # No RF_SERVE_TOKEN in env_extra → env_patch will have it removed.
        )
        assert result.exit_code != 0, (
            f"Expected nonzero exit, got {result.exit_code}. Output: {result.output}"
        )

    def test_lan_bind_auth_token_with_env_set_starts_ok(self, tmp_path):
        """``--bind-host 0.0.0.0 --auth-mode token`` with RF_SERVE_TOKEN set → exit 0 (uvicorn stubbed)."""
        root = _scaffold_workspace(tmp_path)
        result = _invoke_serve(
            ["--bind-host", "0.0.0.0", "--auth-mode", "token"],
            cwd=root,
            env_extra={"RF_SERVE_TOKEN": "valid-token-value"},
        )
        assert result.exit_code == 0, (
            f"Expected exit 0, got {result.exit_code}. Output: {result.output}"
        )

    def test_loopback_bind_no_auth_starts_ok(self, tmp_path):
        """Loopback bind (127.0.0.1) without auth → exit 0 (no restrictions)."""
        root = _scaffold_workspace(tmp_path)
        result = _invoke_serve(
            ["--bind-host", "127.0.0.1", "--auth-mode", "none"],
            cwd=root,
        )
        assert result.exit_code == 0, (
            f"Expected exit 0, got {result.exit_code}. Output: {result.output}"
        )

    def test_default_bind_no_auth_starts_ok(self, tmp_path):
        """Default bind (127.0.0.1 implied) → exit 0."""
        root = _scaffold_workspace(tmp_path)
        result = _invoke_serve(
            ["--auth-mode", "none"],
            cwd=root,
        )
        assert result.exit_code == 0, (
            f"Expected exit 0, got {result.exit_code}. Output: {result.output}"
        )

    def test_error_message_on_lan_without_auth(self, tmp_path):
        """Failure output mentions auth requirement (user-facing error quality)."""
        root = _scaffold_workspace(tmp_path)
        result = _invoke_serve(
            ["--bind-host", "0.0.0.0", "--auth-mode", "none"],
            cwd=root,
        )
        # Output should mention the reason for rejection.
        combined = (result.output or "") + str(getattr(result, "stderr", "") or "")
        assert any(
            kw in combined for kw in ("auth-mode", "auth_mode", "token", "refusing")
        ), f"Expected an error mentioning auth requirement. Output: {combined!r}"


# ---------------------------------------------------------------------------
# TEST-010  Core footprint isolation
# ---------------------------------------------------------------------------


def test_core_import_does_not_import_fastapi():
    """Importing research_foundry must NOT trigger fastapi import.

    This is validated via a fresh subprocess so the current test process's
    already-imported modules do not interfere.

    Note: The CI-level assertion ("fastapi not installed at all without the
    [serve] extra") belongs to a separate CI job; here we confirm only that
    the import guard is wired so fastapi is not pulled in as a side-effect.
    """
    check_code = (
        "import research_foundry, sys; "
        "assert 'fastapi' not in sys.modules, "
        "'fastapi was imported as a side-effect of research_foundry'"
    )
    result = subprocess.run(
        [sys.executable, "-c", check_code],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Core footprint check failed.\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
