"""Unit tests for ERI Phase 5 — CLI and machine output (ERI-5.3).

``rf intake external-report`` wiring only: the underlying service call
(``external_research_import.import_external_report``) is mocked throughout
(exercised for real by
``tests/integration/test_external_research_import.py``), so these tests
focus purely on argument translation, exit codes, and machine-output shape.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.services.external_research_import import ImportOutcome, PendingImportError

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _plain(text: str) -> str:
    """Strip ANSI/Rich styling so substring checks don't split on
    per-character color spans (Rich renders each glyph of a styled
    flag like ``--workspace`` with its own escape codes)."""

    return _ANSI_RE.sub("", text)


def _outcome(**overrides: object) -> ImportOutcome:
    defaults: dict[str, object] = {
        "complete": True,
        "workspace_id": "ws_demo",
        "target_run_id": None,
        "packet_digest": "p" * 64,
        "receipt_id": "erh_" + "a" * 64,
        "receipt_digest": "a" * 64,
        "status": "completed",
        "replayed": False,
        "dry_run": False,
        "block_reason": None,
        "counts": {"actions_total": 2, "completed": 2, "quarantined": 0, "by_completeness_tier": {}},
        "cursor": None,
        "receipt": {"schema_version": "1.0", "receipt_digest": "a" * 64, "status": "completed"},
        "checkpoint": None,
    }
    defaults.update(overrides)
    return ImportOutcome(**defaults)  # type: ignore[arg-type]


def _invoke(*args: str):
    runner = CliRunner()
    return runner.invoke(app, ["intake", "external-report", *args])


class TestArgumentWiring:
    def test_default_invocation_passes_expected_kwargs(self, tmp_path: Path) -> None:
        packet_dir = str(tmp_path / "packet")
        with patch(
            "research_foundry.services.external_research_import.import_external_report",
            return_value=_outcome(),
        ) as mock_call:
            result = _invoke(packet_dir, "--workspace", "ws_demo")

        assert result.exit_code == 0
        mock_call.assert_called_once()
        _, kwargs = mock_call.call_args
        assert kwargs["workspace_id"] == "ws_demo"
        assert kwargs["target_run_id"] is None
        assert kwargs["dry_run"] is False
        assert kwargs["resume"] is False
        assert kwargs["limit"] == 100  # ERI-OQ-4 frozen default

    def test_run_flag_forwards_target_run_id(self, tmp_path: Path) -> None:
        packet_dir = str(tmp_path / "packet")
        with patch(
            "research_foundry.services.external_research_import.import_external_report",
            return_value=_outcome(target_run_id="rf_run_x"),
        ) as mock_call:
            _invoke(packet_dir, "--workspace", "ws_demo", "--run", "rf_run_x")

        _, kwargs = mock_call.call_args
        assert kwargs["target_run_id"] == "rf_run_x"

    def test_dry_run_and_resume_flags_forwarded(self, tmp_path: Path) -> None:
        packet_dir = str(tmp_path / "packet")
        with patch(
            "research_foundry.services.external_research_import.import_external_report",
            return_value=_outcome(dry_run=True),
        ) as mock_call:
            _invoke(packet_dir, "--workspace", "ws_demo", "--dry-run", "--resume")

        _, kwargs = mock_call.call_args
        assert kwargs["dry_run"] is True
        assert kwargs["resume"] is True

    def test_limit_zero_maps_to_unlimited_none(self, tmp_path: Path) -> None:
        packet_dir = str(tmp_path / "packet")
        with patch(
            "research_foundry.services.external_research_import.import_external_report",
            return_value=_outcome(),
        ) as mock_call:
            _invoke(packet_dir, "--workspace", "ws_demo", "--limit", "0")

        _, kwargs = mock_call.call_args
        assert kwargs["limit"] is None

    def test_custom_limit_forwarded(self, tmp_path: Path) -> None:
        packet_dir = str(tmp_path / "packet")
        with patch(
            "research_foundry.services.external_research_import.import_external_report",
            return_value=_outcome(),
        ) as mock_call:
            _invoke(packet_dir, "--workspace", "ws_demo", "--limit", "25")

        _, kwargs = mock_call.call_args
        assert kwargs["limit"] == 25

    def test_missing_workspace_option_fails_usage(self, tmp_path: Path) -> None:
        packet_dir = str(tmp_path / "packet")
        result = _invoke(packet_dir)
        assert result.exit_code != 0


class TestExitCodesAndOutput:
    def test_completed_exits_zero(self, tmp_path: Path) -> None:
        with patch(
            "research_foundry.services.external_research_import.import_external_report",
            return_value=_outcome(status="completed"),
        ):
            result = _invoke(str(tmp_path / "packet"), "--workspace", "ws_demo")
        assert result.exit_code == 0

    def test_completed_with_quarantine_exits_zero(self, tmp_path: Path) -> None:
        with patch(
            "research_foundry.services.external_research_import.import_external_report",
            return_value=_outcome(status="completed_with_quarantine"),
        ):
            result = _invoke(str(tmp_path / "packet"), "--workspace", "ws_demo")
        assert result.exit_code == 0
        assert "quarantine" in result.output.lower()

    def test_blocked_exits_nonzero(self, tmp_path: Path) -> None:
        with patch(
            "research_foundry.services.external_research_import.import_external_report",
            return_value=_outcome(status="blocked", block_reason="required_member_missing", counts=None),
        ):
            result = _invoke(str(tmp_path / "packet"), "--workspace", "ws_demo")
        assert result.exit_code != 0

    def test_pending_batch_limit_exits_zero_with_hint(self, tmp_path: Path) -> None:
        with patch(
            "research_foundry.services.external_research_import.import_external_report",
            return_value=_outcome(
                complete=False,
                status="pending",
                receipt=None,
                counts=None,
                cursor={"next_action_id": "era_x", "completed_count": 2, "total_count": 6},
            ),
        ):
            result = _invoke(str(tmp_path / "packet"), "--workspace", "ws_demo")
        assert result.exit_code == 0
        assert "--resume" in result.output

    def test_pending_import_error_exits_nonzero(self, tmp_path: Path) -> None:
        with patch(
            "research_foundry.services.external_research_import.import_external_report",
            side_effect=PendingImportError("a pending import already exists; pass resume=True to continue"),
        ):
            result = _invoke(str(tmp_path / "packet"), "--workspace", "ws_demo")
        assert result.exit_code != 0


class TestMachineOutput:
    def test_json_output_is_safe_dict_shape(self, tmp_path: Path) -> None:
        with patch(
            "research_foundry.services.external_research_import.import_external_report",
            return_value=_outcome(),
        ):
            result = _invoke(str(tmp_path / "packet"), "--workspace", "ws_demo", "--json")

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert "rf_schema_version" in payload
        assert payload["workspace_id"] == "ws_demo"
        assert payload["status"] == "completed"
        # Never the full receipt/checkpoint document -- only safe_dict()'s fields.
        assert "receipt" not in payload
        assert "checkpoint" not in payload

    def test_json_output_never_leaks_packet_dir_path(self, tmp_path: Path) -> None:
        packet_dir = str(tmp_path / "some" / "private" / "packet")
        with patch(
            "research_foundry.services.external_research_import.import_external_report",
            return_value=_outcome(),
        ):
            result = _invoke(packet_dir, "--workspace", "ws_demo", "--json")

        payload_text = result.output
        assert "private" not in payload_text

    def test_rich_table_output_contains_receipt_digest(self, tmp_path: Path) -> None:
        with patch(
            "research_foundry.services.external_research_import.import_external_report",
            return_value=_outcome(),
        ):
            result = _invoke(str(tmp_path / "packet"), "--workspace", "ws_demo")

        assert "a" * 64 in result.output or "receipt_digest" in result.output


class TestHelp:
    def test_help_lists_expected_flags(self) -> None:
        runner = CliRunner()
        result = runner.invoke(app, ["intake", "external-report", "--help"])
        assert result.exit_code == 0
        output = _plain(result.output)
        for flag in ("--workspace", "--run", "--dry-run", "--resume", "--limit", "--json"):
            assert flag in output
