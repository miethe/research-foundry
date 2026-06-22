"""Tests for backlog reconcile: service function + CLI command.

Fixtures build an isolated foundry workspace with a minimal
``backlog/research_idea_backlog.yaml`` and synthetic run dirs.
CLI tests go through :class:`typer.testing.CliRunner`.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.paths import FoundryPaths, distribution_root
from research_foundry.schemas import SchemaRegistry
from research_foundry.services.backlog_metadata import (
    ReconcileDiff,
    reconcile_backlog,
)
from research_foundry.yamlio import dump_yaml, load_yaml

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SUBSTRATE = [
    "inbox/raw_ideas",
    "intents/active",
    "runs",
    "registries",
    "backlog",
]


def _make_foundry(tmp_path: Path) -> FoundryPaths:
    root = tmp_path / "fdry"
    root.mkdir(parents=True)
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
    for d in _SUBSTRATE:
        (root / d).mkdir(parents=True, exist_ok=True)
    return FoundryPaths(root=root)


def _minimal_backlog(
    ideas: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return a minimal backlog document valid against the schema."""
    return {
        "schema_version": "0.1",
        "type": "research_idea_backlog",
        "title": "Test Backlog",
        "pillars": [
            {
                "id": "pillar_test",
                "title": "Test Pillar",
                "intenttree_level": "pillar",
            }
        ],
        "ideas": ideas,
    }


def _idea(ref: str, *, status: str = "proposed", run_id: Any = None,
          intent_id: Any = None, node_id: Any = None) -> dict[str, Any]:
    return {
        "ref": ref,
        "id": f"idea_{ref.lower().replace('-', '_')}",
        "title": f"Test idea {ref}",
        "pillar": "pillar_test",
        "status": status,
        "research_question": f"What is {ref}?",
        "links": {
            "raw_idea_id": None,
            "intent_id": intent_id,
            "intenttree_node_id": node_id,
            "run_id": run_id,
        },
    }


def _write_run(runs_dir: Path, run_id: str, *,
               backlog_idea_ref: str | None = None,
               intent_id: str | None = None,
               intenttree_node_id: str | None = None,
               status: str = "planned",
               with_report: bool = False) -> Path:
    run_dir = runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_data: dict[str, Any] = {
        "schema_version": "0.1",
        "type": "run",
        "run_id": run_id,
        "status": status,
        "sensitivity": "personal",
    }
    if backlog_idea_ref:
        run_data["backlog_idea_ref"] = backlog_idea_ref
    if intent_id:
        run_data["intent_id"] = intent_id
    if intenttree_node_id:
        run_data["intenttree_node_id"] = intenttree_node_id
    dump_yaml(run_data, run_dir / "run.yaml")
    if with_report:
        (run_dir / "reports").mkdir(parents=True, exist_ok=True)
        (run_dir / "reports" / "report_deterministic.md").write_text(
            "# Report\n", encoding="utf-8"
        )
    return run_dir


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


class TestReconcileBacklogDryRun:
    """reconcile_backlog(dry_run=True) reports stale state without writing."""

    def test_stale_status_reported(self, tmp_path: Path) -> None:
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([_idea("RIB-001", status="proposed")])
        dump_yaml(doc, paths.root / "backlog" / "research_idea_backlog.yaml")
        _write_run(paths.runs, "rf_run_rib001", backlog_idea_ref="RIB-001",
                   with_report=True)

        diffs, orphaned, no_ref = reconcile_backlog(paths, dry_run=True)

        status_diffs = [d for d in diffs if d.field == "status"]
        assert len(status_diffs) == 1
        assert status_diffs[0].ref == "RIB-001"
        assert status_diffs[0].old == "proposed"
        assert status_diffs[0].new == "completed"

    def test_stale_links_reported(self, tmp_path: Path) -> None:
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([_idea("RIB-002", status="proposed")])
        dump_yaml(doc, paths.root / "backlog" / "research_idea_backlog.yaml")
        _write_run(paths.runs, "rf_run_rib002", backlog_idea_ref="RIB-002",
                   intent_id="intent_rib002")

        diffs, _, _ = reconcile_backlog(paths, dry_run=True)

        link_diffs = {d.field: d for d in diffs if d.field.startswith("links.")}
        assert "links.run_id" in link_diffs
        assert link_diffs["links.run_id"].new == "rf_run_rib002"
        assert "links.intent_id" in link_diffs
        assert link_diffs["links.intent_id"].new == "intent_rib002"

    def test_dry_run_does_not_write(self, tmp_path: Path) -> None:
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([_idea("RIB-003", status="proposed")])
        backlog_path = paths.root / "backlog" / "research_idea_backlog.yaml"
        dump_yaml(doc, backlog_path)
        mtime_before = backlog_path.stat().st_mtime

        _write_run(paths.runs, "rf_run_rib003", backlog_idea_ref="RIB-003",
                   with_report=True)
        reconcile_backlog(paths, dry_run=True)

        assert backlog_path.stat().st_mtime == mtime_before, "dry-run must not modify the file"

    def test_running_status_without_report(self, tmp_path: Path) -> None:
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([_idea("RIB-004", status="proposed")])
        dump_yaml(doc, paths.root / "backlog" / "research_idea_backlog.yaml")
        _write_run(paths.runs, "rf_run_rib004", backlog_idea_ref="RIB-004",
                   with_report=False)

        diffs, _, _ = reconcile_backlog(paths, dry_run=True)

        status_diffs = [d for d in diffs if d.field == "status"]
        assert len(status_diffs) == 1
        assert status_diffs[0].new == "running"

    def test_inverse_drift_orphaned_completed(self, tmp_path: Path) -> None:
        """Backlog idea marked completed but no run dir."""
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([_idea("RIB-005", status="completed")])
        dump_yaml(doc, paths.root / "backlog" / "research_idea_backlog.yaml")
        # No run created.

        _, orphaned, _ = reconcile_backlog(paths, dry_run=True)

        assert "RIB-005" in orphaned

    def test_inverse_drift_runs_without_ref(self, tmp_path: Path) -> None:
        """Run dir with no backlog_idea_ref is flagged."""
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([])
        dump_yaml(doc, paths.root / "backlog" / "research_idea_backlog.yaml")
        _write_run(paths.runs, "rf_run_orphan_run")

        _, _, no_ref = reconcile_backlog(paths, dry_run=True)

        assert "rf_run_orphan_run" in no_ref


class TestReconcileBacklogWrite:
    """reconcile_backlog(dry_run=False) advances stale status/links."""

    def test_write_advances_status_to_completed(self, tmp_path: Path) -> None:
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([_idea("RIB-010", status="proposed")])
        backlog_path = paths.root / "backlog" / "research_idea_backlog.yaml"
        dump_yaml(doc, backlog_path)
        _write_run(paths.runs, "rf_run_rib010", backlog_idea_ref="RIB-010",
                   with_report=True)

        diffs, _, _ = reconcile_backlog(paths, dry_run=False)

        assert any(d.field == "status" and d.new == "completed" for d in diffs)
        updated = load_yaml(backlog_path)
        idea = next(i for i in updated["ideas"] if i["ref"] == "RIB-010")
        assert idea["status"] == "completed"

    def test_write_fills_null_links(self, tmp_path: Path) -> None:
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([_idea("RIB-011", status="proposed")])
        backlog_path = paths.root / "backlog" / "research_idea_backlog.yaml"
        dump_yaml(doc, backlog_path)
        _write_run(paths.runs, "rf_run_rib011", backlog_idea_ref="RIB-011",
                   intent_id="intent_rib011",
                   intenttree_node_id="node_rib011",
                   with_report=True)

        reconcile_backlog(paths, dry_run=False)

        updated = load_yaml(backlog_path)
        idea = next(i for i in updated["ideas"] if i["ref"] == "RIB-011")
        assert idea["links"]["run_id"] == "rf_run_rib011"
        assert idea["links"]["intent_id"] == "intent_rib011"
        assert idea["links"]["intenttree_node_id"] == "node_rib011"

    def test_write_does_not_regress_status(self, tmp_path: Path) -> None:
        """A manually-advanced status must never be regressed."""
        paths = _make_foundry(tmp_path)
        # Idea already at 'completed'; run has no report → infer 'running'.
        doc = _minimal_backlog([_idea("RIB-012", status="completed")])
        backlog_path = paths.root / "backlog" / "research_idea_backlog.yaml"
        dump_yaml(doc, backlog_path)
        _write_run(paths.runs, "rf_run_rib012", backlog_idea_ref="RIB-012",
                   with_report=False)

        diffs, _, _ = reconcile_backlog(paths, dry_run=False)

        status_diffs = [d for d in diffs if d.field == "status"]
        assert not status_diffs, "status must not be regressed from completed to running"

        updated = load_yaml(backlog_path)
        idea = next(i for i in updated["ideas"] if i["ref"] == "RIB-012")
        assert idea["status"] == "completed"

    def test_write_does_not_overwrite_non_null_link(self, tmp_path: Path) -> None:
        """A non-null link.run_id must never be overwritten."""
        paths = _make_foundry(tmp_path)
        # Idea already has a manually-set run_id.
        doc = _minimal_backlog([
            _idea("RIB-013", status="completed", run_id="rf_run_manual")
        ])
        backlog_path = paths.root / "backlog" / "research_idea_backlog.yaml"
        dump_yaml(doc, backlog_path)
        _write_run(paths.runs, "rf_run_rib013", backlog_idea_ref="RIB-013",
                   with_report=True)

        reconcile_backlog(paths, dry_run=False)

        updated = load_yaml(backlog_path)
        idea = next(i for i in updated["ideas"] if i["ref"] == "RIB-013")
        assert idea["links"]["run_id"] == "rf_run_manual", "non-null link must not be overwritten"

    def test_idempotent_second_reconcile_reports_zero_changes(self, tmp_path: Path) -> None:
        """A second reconcile after a write must report no changes."""
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([_idea("RIB-014", status="proposed")])
        dump_yaml(doc, paths.root / "backlog" / "research_idea_backlog.yaml")
        _write_run(paths.runs, "rf_run_rib014", backlog_idea_ref="RIB-014",
                   with_report=True)

        reconcile_backlog(paths, dry_run=False)
        diffs2, orphaned2, no_ref2 = reconcile_backlog(paths, dry_run=False)

        assert not diffs2, f"second reconcile should be a no-op; got: {diffs2}"

    def test_written_file_validates_against_schema(self, tmp_path: Path) -> None:
        """After --write, the backlog must still pass schema validation."""
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([_idea("RIB-015", status="proposed")])
        backlog_path = paths.root / "backlog" / "research_idea_backlog.yaml"
        dump_yaml(doc, backlog_path)
        _write_run(paths.runs, "rf_run_rib015", backlog_idea_ref="RIB-015",
                   with_report=True)

        reconcile_backlog(paths, dry_run=False)

        updated = load_yaml(backlog_path)
        reg = SchemaRegistry(paths.schemas)
        result = reg.validate(updated, "research_idea_backlog")
        assert result.ok, f"schema errors after write: {result.errors}"

    def test_write_advances_multiple_ideas(self, tmp_path: Path) -> None:
        """Multiple ideas in a single reconcile."""
        paths = _make_foundry(tmp_path)
        ideas = [
            _idea("RIB-020", status="proposed"),
            _idea("RIB-021", status="proposed"),
            _idea("RIB-022", status="proposed"),
        ]
        backlog_path = paths.root / "backlog" / "research_idea_backlog.yaml"
        dump_yaml(_minimal_backlog(ideas), backlog_path)
        _write_run(paths.runs, "rf_run_rib020", backlog_idea_ref="RIB-020", with_report=True)
        _write_run(paths.runs, "rf_run_rib021", backlog_idea_ref="RIB-021", with_report=False)
        # RIB-022 has no run.

        diffs, orphaned, _ = reconcile_backlog(paths, dry_run=False)

        refs_changed = {d.ref for d in diffs if d.field == "status"}
        assert "RIB-020" in refs_changed
        assert "RIB-021" in refs_changed
        assert "RIB-022" not in refs_changed

        updated = load_yaml(backlog_path)
        by_ref = {i["ref"]: i for i in updated["ideas"]}
        assert by_ref["RIB-020"]["status"] == "completed"
        assert by_ref["RIB-021"]["status"] == "running"
        assert by_ref["RIB-022"]["status"] == "proposed"

    def test_archived_idea_is_never_touched(self, tmp_path: Path) -> None:
        """Archived is a terminal state — reconcile must not touch it regardless of run state."""
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([_idea("RIB-090", status="archived")])
        backlog_path = paths.root / "backlog" / "research_idea_backlog.yaml"
        dump_yaml(doc, backlog_path)
        _write_run(paths.runs, "rf_run_rib090", backlog_idea_ref="RIB-090", with_report=True)

        # Dry-run must report ZERO changes for this idea.
        diffs, _, _ = reconcile_backlog(paths, dry_run=True)
        assert all(d.ref != "RIB-090" for d in diffs), (
            "archived idea must produce no diffs, got: "
            + str([d for d in diffs if d.ref == "RIB-090"])
        )

        # Write must also leave it archived.
        reconcile_backlog(paths, dry_run=False)
        updated = load_yaml(backlog_path)
        idea = next(i for i in updated["ideas"] if i["ref"] == "RIB-090")
        assert idea["status"] == "archived"

    def test_empty_string_link_is_filled(self, tmp_path: Path) -> None:
        """links.run_id: '' (empty string) should be treated as fillable."""
        paths = _make_foundry(tmp_path)
        idea = _idea("RIB-091", status="proposed", run_id="")
        doc = _minimal_backlog([idea])
        backlog_path = paths.root / "backlog" / "research_idea_backlog.yaml"
        dump_yaml(doc, backlog_path)
        _write_run(paths.runs, "rf_run_rib091", backlog_idea_ref="RIB-091", with_report=True)

        reconcile_backlog(paths, dry_run=False)

        updated = load_yaml(backlog_path)
        filled = next(i for i in updated["ideas"] if i["ref"] == "RIB-091")
        assert filled["links"]["run_id"] == "rf_run_rib091", (
            "empty-string run_id should be backfilled"
        )

    def test_non_empty_link_is_not_overwritten(self, tmp_path: Path) -> None:
        """A real non-empty links.run_id must still NOT be overwritten."""
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([_idea("RIB-092", status="completed", run_id="rf_run_manual_set")])
        backlog_path = paths.root / "backlog" / "research_idea_backlog.yaml"
        dump_yaml(doc, backlog_path)
        _write_run(paths.runs, "rf_run_rib092", backlog_idea_ref="RIB-092", with_report=True)

        reconcile_backlog(paths, dry_run=False)

        updated = load_yaml(backlog_path)
        idea = next(i for i in updated["ideas"] if i["ref"] == "RIB-092")
        assert idea["links"]["run_id"] == "rf_run_manual_set", (
            "non-empty run_id must not be overwritten"
        )


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------


def _invoke(args: list[str], cwd: Path):
    """Run the CLI from ``cwd`` so workspace discovery resolves to the tmp root."""
    import os

    orig = os.getcwd()
    os.chdir(cwd)
    try:
        result = runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(orig)
    return result


class TestBacklogReconcileCLI:
    """CLI: rf backlog reconcile [--dry-run] [--write]"""

    def test_dry_run_default_no_write(self, tmp_path: Path) -> None:
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([_idea("RIB-030", status="proposed")])
        backlog_path = paths.root / "backlog" / "research_idea_backlog.yaml"
        dump_yaml(doc, backlog_path)
        mtime_before = backlog_path.stat().st_mtime
        _write_run(paths.runs, "rf_run_rib030", backlog_idea_ref="RIB-030", with_report=True)

        result = _invoke(["backlog", "reconcile"], cwd=paths.root)

        assert result.exit_code == 0
        assert backlog_path.stat().st_mtime == mtime_before, "default dry-run must not write"

    def test_dry_run_shows_table(self, tmp_path: Path) -> None:
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([_idea("RIB-031", status="proposed")])
        dump_yaml(doc, paths.root / "backlog" / "research_idea_backlog.yaml")
        _write_run(paths.runs, "rf_run_rib031", backlog_idea_ref="RIB-031", with_report=True)

        result = _invoke(["backlog", "reconcile", "--dry-run"], cwd=paths.root)

        assert result.exit_code == 0
        assert "RIB-031" in result.output
        assert "completed" in result.output

    def test_write_applies_changes(self, tmp_path: Path) -> None:
        paths = _make_foundry(tmp_path)
        doc = _minimal_backlog([_idea("RIB-032", status="proposed")])
        backlog_path = paths.root / "backlog" / "research_idea_backlog.yaml"
        dump_yaml(doc, backlog_path)
        _write_run(paths.runs, "rf_run_rib032", backlog_idea_ref="RIB-032", with_report=True)

        result = _invoke(["backlog", "reconcile", "--write"], cwd=paths.root)

        assert result.exit_code == 0
        updated = load_yaml(backlog_path)
        idea = next(i for i in updated["ideas"] if i["ref"] == "RIB-032")
        assert idea["status"] == "completed"

    def test_no_changes_message(self, tmp_path: Path) -> None:
        paths = _make_foundry(tmp_path)
        # Already in sync.
        doc = _minimal_backlog([
            _idea("RIB-033", status="completed", run_id="rf_run_rib033")
        ])
        dump_yaml(doc, paths.root / "backlog" / "research_idea_backlog.yaml")
        _write_run(paths.runs, "rf_run_rib033", backlog_idea_ref="RIB-033", with_report=True)

        result = _invoke(["backlog", "reconcile", "--dry-run"], cwd=paths.root)

        assert result.exit_code == 0
        assert "no changes needed" in result.output

    def test_inverse_drift_shown_in_output(self, tmp_path: Path) -> None:
        paths = _make_foundry(tmp_path)
        # An idea marked completed but no run, and a run without a ref.
        doc = _minimal_backlog([_idea("RIB-034", status="completed")])
        dump_yaml(doc, paths.root / "backlog" / "research_idea_backlog.yaml")
        _write_run(paths.runs, "rf_run_no_ref_at_all")

        result = _invoke(["backlog", "reconcile", "--dry-run"], cwd=paths.root)

        assert result.exit_code == 0
        # Strip ANSI codes before asserting — Rich may color numeric portions.
        import re
        plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert "RIB-034" in plain
        assert "rf_run_no_ref_at_all" in plain
