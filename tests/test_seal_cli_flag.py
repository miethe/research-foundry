"""CLI-wiring smoke test for ``rf run export --seal`` (TASK-4.2).

This test covers ONLY the trigger surface added in TASK-4.2: that ``--seal``
is accepted as a flag on ``rf run export``, that it resolves ``run_id`` and
calls the seal entrypoint (``research_foundry.services.run_seal.seal_run``)
exactly once with the expected arguments, and that ``--seal`` combined with
``--all`` is rejected with a nonzero exit rather than silently looping.

It intentionally does NOT test digest correctness or tamper-evidence
guarantees — that is TASK-4.3 (digest/lineage-write logic) and TASK-4.4
(tamper-evidence hardening) territory. The real ``export_to_file``/``seal_run``
bodies are stubbed/mocked here so this test is stable regardless of whether
TASK-4.3's real implementation has landed yet.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.paths import distribution_root

runner = CliRunner()


def _scaffold_workspace(tmp_path: Path) -> Path:
    """Minimal foundry workspace with a ``foundry.yaml`` marker + runs dir."""

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


@pytest.fixture()
def workspace(tmp_path, monkeypatch):
    root = _scaffold_workspace(tmp_path)
    monkeypatch.chdir(root)
    return root


class TestSealCliFlagWiring:
    """TASK-4.2: --seal flag parses and wires to the seal entrypoint."""

    def test_seal_flag_calls_seal_entrypoint_with_run_id(self, workspace):
        run_id = "rf_run_seal_test"
        fake_out = workspace / "runs" / run_id / "run.json"

        with patch(
            "research_foundry.services.export_service.export_to_file",
            MagicMock(return_value=fake_out),
        ) as mock_export, patch(
            "research_foundry.services.run_seal.seal_run",
            MagicMock(return_value={"digest": None, "run_id": run_id}),
        ) as mock_seal:
            result = runner.invoke(app, ["run", "export", "--run-id", run_id, "--seal"])

        assert result.exit_code == 0, result.output
        mock_export.assert_called_once()
        mock_seal.assert_called_once()
        # seal_run(paths, run_id) — run_id is the second positional/keyword arg.
        call_args, call_kwargs = mock_seal.call_args
        called_run_id = call_kwargs.get("run_id", call_args[1] if len(call_args) > 1 else None)
        assert called_run_id == run_id

    def test_export_without_seal_does_not_call_seal_entrypoint(self, workspace):
        run_id = "rf_run_no_seal_test"
        fake_out = workspace / "runs" / run_id / "run.json"

        with patch(
            "research_foundry.services.export_service.export_to_file",
            MagicMock(return_value=fake_out),
        ), patch(
            "research_foundry.services.run_seal.seal_run",
            MagicMock(),
        ) as mock_seal:
            result = runner.invoke(app, ["run", "export", "--run-id", run_id])

        assert result.exit_code == 0, result.output
        mock_seal.assert_not_called()

    def test_seal_with_all_flag_is_rejected(self, workspace):
        result = runner.invoke(app, ["run", "export", "--all", "--seal"])
        assert result.exit_code != 0, (
            f"Expected nonzero exit for --seal + --all, got {result.exit_code}. "
            f"Output: {result.output}"
        )
