"""Tests for ``rf run set-visibility`` / ``rf run set-workspace`` (itt0926-rfws,
node_01M1HV11263E3VNB2ZC0A0K1KZ, AC-1).

Covers the service functions directly (``services/run_admin.py``) and the CLI
wiring (``rf run set-visibility`` / ``rf run set-workspace``), following the
established ``rf run export --seal`` CLI-wiring test convention
(``tests/test_seal_cli_flag.py``).
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.services import run_admin
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
    (root / "runs").mkdir(exist_ok=True)
    return root


def _write_run(root: Path, run_id: str, *, workspace_id, visibility: str = "workspace") -> Path:
    run_dir = root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_yaml = run_dir / "run.yaml"
    dump_yaml(
        {
            "schema_version": "0.1",
            "type": "run",
            "run_id": run_id,
            "intent_id": "intent_test",
            "status": "planned",
            "sensitivity": "personal",
            "workspace_id": workspace_id,
            "visibility": visibility,
        },
        run_yaml,
    )
    return run_yaml


# --------------------------------------------------------------------------
# service layer
# --------------------------------------------------------------------------


def test_set_run_visibility_updates_run_yaml(tmp_path):
    root = _scaffold_workspace(tmp_path)
    _write_run(root, "rf_run_vis", workspace_id="default", visibility="workspace")
    paths = FoundryPaths(root=root)

    result = run_admin.set_run_visibility(paths, "rf_run_vis", "public")
    assert result["visibility"] == "public"

    on_disk = load_yaml(root / "runs" / "rf_run_vis" / "run.yaml")
    assert on_disk["visibility"] == "public"
    # Untouched fields survive the atomic rewrite.
    assert on_disk["workspace_id"] == "default"
    assert on_disk["run_id"] == "rf_run_vis"


def test_set_run_visibility_rejects_unrecognised_value(tmp_path):
    root = _scaffold_workspace(tmp_path)
    _write_run(root, "rf_run_vis2", workspace_id="default")
    paths = FoundryPaths(root=root)

    with pytest.raises(run_admin.RunAdminError):
        run_admin.set_run_visibility(paths, "rf_run_vis2", "everyone")

    # Refused outright -- the file is untouched.
    on_disk = load_yaml(root / "runs" / "rf_run_vis2" / "run.yaml")
    assert on_disk["visibility"] == "workspace"


def test_set_run_visibility_missing_run_raises(tmp_path):
    root = _scaffold_workspace(tmp_path)
    paths = FoundryPaths(root=root)

    with pytest.raises(run_admin.RunAdminError):
        run_admin.set_run_visibility(paths, "rf_run_does_not_exist", "public")


def test_set_run_workspace_repairs_null_workspace_id(tmp_path):
    """The exact repair story this node names: a run planned with
    ``workspace_id: null`` needs a targeted single-run fix."""

    root = _scaffold_workspace(tmp_path)
    _write_run(root, "rf_run_ws", workspace_id=None)
    paths = FoundryPaths(root=root)

    result = run_admin.set_run_workspace(paths, "rf_run_ws", "default")
    assert result["workspace_id"] == "default"

    on_disk = load_yaml(root / "runs" / "rf_run_ws" / "run.yaml")
    assert on_disk["workspace_id"] == "default"


def test_set_run_workspace_rejects_empty_value(tmp_path):
    root = _scaffold_workspace(tmp_path)
    _write_run(root, "rf_run_ws2", workspace_id="default")
    paths = FoundryPaths(root=root)

    with pytest.raises(run_admin.RunAdminError):
        run_admin.set_run_workspace(paths, "rf_run_ws2", "  ")


# --------------------------------------------------------------------------
# CLI wiring
# --------------------------------------------------------------------------


@pytest.fixture()
def workspace(tmp_path, monkeypatch):
    root = _scaffold_workspace(tmp_path)
    monkeypatch.chdir(root)
    return root


def test_cli_set_visibility_updates_run_yaml(workspace):
    _write_run(workspace, "rf_run_cli_vis", workspace_id="default", visibility="workspace")

    result = runner.invoke(app, ["run", "set-visibility", "rf_run_cli_vis", "public"])

    assert result.exit_code == 0, result.output
    on_disk = load_yaml(workspace / "runs" / "rf_run_cli_vis" / "run.yaml")
    assert on_disk["visibility"] == "public"


def test_cli_set_visibility_invalid_value_nonzero_exit(workspace):
    _write_run(workspace, "rf_run_cli_vis2", workspace_id="default")

    result = runner.invoke(app, ["run", "set-visibility", "rf_run_cli_vis2", "everyone"])

    assert result.exit_code != 0


def test_cli_set_workspace_updates_run_yaml(workspace):
    _write_run(workspace, "rf_run_cli_ws", workspace_id=None)

    result = runner.invoke(app, ["run", "set-workspace", "rf_run_cli_ws", "default"])

    assert result.exit_code == 0, result.output
    on_disk = load_yaml(workspace / "runs" / "rf_run_cli_ws" / "run.yaml")
    assert on_disk["workspace_id"] == "default"
