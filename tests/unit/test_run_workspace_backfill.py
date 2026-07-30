"""Unit tests for the run-record workspace backfill (DF-004).

Coverage
--------
* :func:`~research_foundry.services.workspace_migration_service.dry_run_runs` —
  zero-write contract (mtime + content-hash invariant), counting accuracy.
* :func:`~research_foundry.services.workspace_migration_service.backfill_runs` —
  stamps ``workspace_id="default"`` only on runs missing it; never touches
  ``visibility``; writes a manifest with ``record_type="run"``.
* :func:`~research_foundry.services.workspace_migration_service.rollback` —
  reverses a run-record backfill (key removal on rollback, not
  ``workspace_id == "default"``); never touches runs absent from the manifest.
* ``rf workspace migrate-dry-run`` / ``rf workspace migrate --apply`` /
  ``rf workspace rollback`` (CLI wiring) — run coverage surfaced in the dry-run
  report, stamped on ``--apply``, and reversed by a single ``rollback`` call
  via the drafts/runs manifest linkage written by ``migrate --apply``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.paths import FoundryPaths
from research_foundry.services.workspace_migration_service import (
    BackfillReport,
    RunDryRunReport,
    backfill_runs,
    dry_run_runs,
    rollback,
)
from research_foundry.yamlio import dump_yaml, load_yaml

runner = CliRunner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _file_hash(path: Path) -> str:
    """SHA-256 hex digest of file bytes (content-identity proof)."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plant_run(
    paths: FoundryPaths,
    run_id: str,
    *,
    workspace_id: str | None = None,
    created_by: str | None = None,
) -> Path:
    """Create a minimal run.yaml under <workspace>/runs/<run_id>/.

    Avoids timestamp fields so YAML round-trips byte-identically (PyYAML
    safe_load auto-converts ISO-8601 strings to datetime objects, which then
    serialize differently — breaking byte-hash equality on rollback).
    """
    run_dir = paths.runs / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    run_yaml_path = run_dir / "run.yaml"
    payload: dict = {
        "schema_version": 1,
        "run_id": run_id,
        "title": f"Legacy Run {run_id}",
        "status": "completed",
    }
    if workspace_id is not None:
        payload["workspace_id"] = workspace_id
    if created_by is not None:
        payload["created_by"] = created_by
    dump_yaml(payload, run_yaml_path)
    return run_yaml_path


# ---------------------------------------------------------------------------
# dry_run_runs — structural + zero-write tests
# ---------------------------------------------------------------------------


def test_dry_run_runs_empty_workspace(tmp_foundry: FoundryPaths) -> None:
    """dry_run_runs on a workspace with no runs returns zeroes."""
    report = dry_run_runs(tmp_foundry)

    assert isinstance(report, RunDryRunReport)
    assert report.total_runs == 0
    assert report.runs_missing_workspace_id == 0
    assert report.target_workspace_id == "default"
    assert isinstance(report.caller_impact_summary, str)
    assert len(report.caller_impact_summary) > 0


def test_dry_run_runs_counts_exactly_unowned(tmp_foundry: FoundryPaths) -> None:
    """dry_run_runs over 2 unowned + 1 already-owned run reports exactly 2 to migrate."""
    run_paths = [
        _plant_run(tmp_foundry, "run_a_unowned"),
        _plant_run(tmp_foundry, "run_b_unowned"),
        _plant_run(tmp_foundry, "run_c_owned", workspace_id="ws_existing"),
    ]

    # Snapshot: mtime + content hash before dry_run_runs.
    before = {p: (p.stat().st_mtime, _file_hash(p)) for p in run_paths}

    report = dry_run_runs(tmp_foundry)

    assert report.total_runs == 3
    assert report.runs_missing_workspace_id == 2
    assert report.target_workspace_id == "default"

    # ZERO-WRITE contract: every run.yaml is byte-identical and untouched.
    for p in run_paths:
        mtime_before, hash_before = before[p]
        assert p.stat().st_mtime == mtime_before, (
            f"dry_run_runs touched mtime of {p.name}"
        )
        assert _file_hash(p) == hash_before, (
            f"dry_run_runs mutated content of {p.name}"
        )


# ---------------------------------------------------------------------------
# backfill_runs — forward mutation
# ---------------------------------------------------------------------------


def test_backfill_runs_stamps_default_skips_owned(tmp_foundry: FoundryPaths) -> None:
    """backfill_runs stamps "default" on the 2 unowned runs, skips the owned one."""
    run_a = _plant_run(tmp_foundry, "run_bf_a")
    run_b = _plant_run(tmp_foundry, "run_bf_b")
    run_c = _plant_run(tmp_foundry, "run_bf_c", workspace_id="ws_existing")
    hash_c_before = _file_hash(run_c)

    report = backfill_runs(tmp_foundry)

    assert isinstance(report, BackfillReport)
    assert report.total_attempted == 2
    assert report.total_succeeded == 2
    assert report.total_failed == 0
    assert report.target_workspace_id == "default"
    assert report.migration_run_id != ""

    # Manifest reflects only the two backfilled runs, tagged record_type="run".
    assert len(report.manifest) == 2
    record_ids = {e.record_id for e in report.manifest}
    assert record_ids == {"run_bf_a", "run_bf_b"}
    for entry in report.manifest:
        assert entry.record_type == "run"
        assert entry.new_workspace_id == "default"
        assert entry.prior_workspace_id is None

    # On-disk: the two unowned runs now have workspace_id="default".
    assert load_yaml(run_a).get("workspace_id") == "default"
    assert load_yaml(run_b).get("workspace_id") == "default"

    # The already-owned run is never modified.
    assert _file_hash(run_c) == hash_c_before, "backfill_runs must not touch run_c"
    assert load_yaml(run_c).get("workspace_id") == "ws_existing"


def test_backfill_runs_never_sets_visibility(tmp_foundry: FoundryPaths) -> None:
    """backfill_runs stamps workspace_id only — visibility is never written."""
    run_path = _plant_run(tmp_foundry, "run_novis")

    backfill_runs(tmp_foundry)

    data = load_yaml(run_path)
    assert data.get("workspace_id") == "default"
    assert "visibility" not in data, (
        "backfill_runs must not set visibility on legacy runs "
        "(reader defaults absent visibility to 'workspace')"
    )


def test_backfill_runs_writes_manifest(tmp_foundry: FoundryPaths) -> None:
    """backfill_runs writes a JSON manifest to .rf_state/migrations/."""
    _plant_run(tmp_foundry, "run_manifest_a")

    report = backfill_runs(tmp_foundry)

    manifest_path = (
        tmp_foundry.rf_state
        / "migrations"
        / f"{report.migration_run_id}-workspace-backfill.json"
    )
    assert manifest_path.exists(), "backfill_runs must write a manifest JSON file"


def test_backfill_runs_idempotent(tmp_foundry: FoundryPaths) -> None:
    """Running backfill_runs twice: the second run touches nothing."""
    _plant_run(tmp_foundry, "run_idem_a")
    _plant_run(tmp_foundry, "run_idem_b")

    first = backfill_runs(tmp_foundry)
    assert first.total_succeeded == 2

    second = backfill_runs(tmp_foundry)
    assert second.total_attempted == 0
    assert second.total_succeeded == 0
    assert second.total_failed == 0
    assert second.manifest == []


def test_dry_run_runs_parity_with_backfill_runs(tmp_foundry: FoundryPaths) -> None:
    """dry_run_runs' prediction equals backfill_runs' actual succeeded count."""
    _plant_run(tmp_foundry, "run_par_a")
    _plant_run(tmp_foundry, "run_par_b")
    _plant_run(tmp_foundry, "run_par_c", workspace_id="already_set")

    preview = dry_run_runs(tmp_foundry)
    assert preview.runs_missing_workspace_id == 2

    bf = backfill_runs(tmp_foundry)
    assert bf.total_succeeded == preview.runs_missing_workspace_id


# ---------------------------------------------------------------------------
# rollback — reverse mutation over run records
# ---------------------------------------------------------------------------


def test_rollback_restores_unowned_runs(tmp_foundry: FoundryPaths) -> None:
    """rollback restores the 2 backfilled runs to unowned (key removed, not '')."""
    run_a = _plant_run(tmp_foundry, "run_rb_a")
    run_b = _plant_run(tmp_foundry, "run_rb_b")
    run_c = _plant_run(tmp_foundry, "run_rb_c", workspace_id="ws_existing")

    before_hashes = {p: _file_hash(p) for p in (run_a, run_b, run_c)}

    report = backfill_runs(tmp_foundry)
    assert report.total_succeeded == 2

    rb = rollback(tmp_foundry, report.migration_run_id)

    assert rb.total_reverted_runs == 2
    assert rb.total_failed == 0
    assert rb.is_dry_run is False

    # The two backfilled runs are byte-identical to their pre-backfill state
    # (the workspace_id key was removed entirely, not set to "" or null).
    assert _file_hash(run_a) == before_hashes[run_a]
    assert _file_hash(run_b) == before_hashes[run_b]
    data_a = load_yaml(run_a)
    data_b = load_yaml(run_b)
    assert "workspace_id" not in data_a
    assert "workspace_id" not in data_b

    # The already-owned run was never part of the manifest/backfill; untouched.
    assert _file_hash(run_c) == before_hashes[run_c]


def test_rollback_run_never_keys_off_default_value(tmp_foundry: FoundryPaths) -> None:
    """rollback must not revert a run merely because workspace_id == 'default'.

    A run created POST-backfill with workspace_id='default' was NOT part of
    the original migration manifest; rollback must leave it untouched.
    """
    _plant_run(tmp_foundry, "run_safety_a")

    report = backfill_runs(tmp_foundry)
    assert report.total_succeeded == 1

    # POST-BACKFILL: a new run that happens to already have workspace_id="default"
    # (e.g. created going forward by the DF-004-adjacent write-path task).
    run_b = _plant_run(tmp_foundry, "run_safety_b", workspace_id="default")
    hash_b_before = _file_hash(run_b)

    rb = rollback(tmp_foundry, report.migration_run_id)

    assert rb.total_reverted_runs == 1
    assert _file_hash(run_b) == hash_b_before, (
        "rollback must not revert a run absent from the original manifest, "
        "even if its workspace_id happens to equal 'default'"
    )
    assert load_yaml(run_b).get("workspace_id") == "default"


def test_rollback_dry_run_runs_no_writes(tmp_foundry: FoundryPaths) -> None:
    """rollback(dry_run=True) over a run manifest performs zero writes."""
    run_a = _plant_run(tmp_foundry, "run_dr_a")

    report = backfill_runs(tmp_foundry)
    assert report.total_succeeded == 1

    hash_after_backfill = _file_hash(run_a)
    mtime_after_backfill = run_a.stat().st_mtime

    rb = rollback(tmp_foundry, report.migration_run_id, dry_run=True)

    assert rb.is_dry_run is True
    assert rb.total_reverted_runs == 1
    assert _file_hash(run_a) == hash_after_backfill, "dry-run rollback must not write"
    assert run_a.stat().st_mtime == mtime_after_backfill, (
        "dry-run rollback must not touch mtime"
    )


def test_existing_workspace_id_run_never_modified(tmp_foundry: FoundryPaths) -> None:
    """A run with an existing workspace_id is never modified by dry_run_runs or backfill_runs."""
    run_path = _plant_run(tmp_foundry, "run_never_touch", workspace_id="ws_prod")
    before_mtime = run_path.stat().st_mtime
    before_hash = _file_hash(run_path)

    dry_run_runs(tmp_foundry)
    assert run_path.stat().st_mtime == before_mtime
    assert _file_hash(run_path) == before_hash

    report = backfill_runs(tmp_foundry)
    assert report.total_attempted == 0
    assert run_path.stat().st_mtime == before_mtime
    assert _file_hash(run_path) == before_hash
    assert load_yaml(run_path).get("workspace_id") == "ws_prod"


# ---------------------------------------------------------------------------
# CLI wiring — `rf workspace migrate-dry-run` / `migrate --apply` / `rollback`
# ---------------------------------------------------------------------------


def _invoke_with_paths(paths: FoundryPaths, *args: str):
    """Invoke the CLI with FoundryPaths.discover() patched to return *paths*.

    Mirrors the pattern in tests/unit/test_reports_cli.py — workspace commands
    do a local ``from .paths import FoundryPaths`` inside each function body,
    so patching the classmethod on the real class covers every call site.
    """
    with patch("research_foundry.paths.FoundryPaths.discover", return_value=paths):
        return runner.invoke(app, list(args))


def test_cli_migrate_dry_run_reports_run_counts(tmp_foundry: FoundryPaths) -> None:
    """`rf workspace migrate-dry-run --json` surfaces total_runs/runs_missing_workspace_id."""
    _plant_run(tmp_foundry, "cli_dr_run_a")
    _plant_run(tmp_foundry, "cli_dr_run_b")
    _plant_run(tmp_foundry, "cli_dr_run_c", workspace_id="ws_existing")

    result = _invoke_with_paths(tmp_foundry, "workspace", "migrate-dry-run", "--json")
    assert result.exit_code == 0, result.output

    payload = json.loads(result.output)
    assert payload["total_runs"] == 3
    assert payload["runs_missing_workspace_id"] == 2

    # Zero-write contract holds through the CLI path too.
    assert dry_run_runs(tmp_foundry).runs_missing_workspace_id == 2


def test_cli_migrate_dry_run_table_shows_run_rows(tmp_foundry: FoundryPaths) -> None:
    """`rf workspace migrate-dry-run` (Rich table) includes the run fields."""
    _plant_run(tmp_foundry, "cli_dr_table_a")

    result = _invoke_with_paths(tmp_foundry, "workspace", "migrate-dry-run")
    assert result.exit_code == 0, result.output
    assert "total_runs" in result.output
    assert "runs_missing_workspace_id" in result.output


def test_cli_migrate_apply_stamps_run_yaml(tmp_foundry: FoundryPaths) -> None:
    """`rf workspace migrate --apply` stamps workspace_id onto a fixture run.yaml lacking it."""
    run_a = _plant_run(tmp_foundry, "cli_apply_run_a")
    run_b_owned = _plant_run(tmp_foundry, "cli_apply_run_b", workspace_id="ws_existing")
    hash_b_before = _file_hash(run_b_owned)

    result = _invoke_with_paths(
        tmp_foundry, "workspace", "migrate", "--apply", "--json"
    )
    assert result.exit_code == 0, result.output

    payload = json.loads(result.output)
    assert payload["status"] == "applied"
    assert payload["total_runs_attempted"] == 1
    assert payload["total_runs_succeeded"] == 1
    assert payload["total_runs_failed"] == 0
    assert "run_migration_run_id" in payload and payload["run_migration_run_id"]

    assert load_yaml(run_a).get("workspace_id") == "default"
    # Untouched: already had a workspace_id.
    assert _file_hash(run_b_owned) == hash_b_before


def test_cli_migrate_apply_idempotency_gate_considers_runs(tmp_foundry: FoundryPaths) -> None:
    """Idempotency gate does not short-circuit to 'already migrated' while runs are pending.

    Simulates the drafts side being fully migrated (no drafts exist at all, so
    drafts_missing_workspace_id == 0) while a run.yaml still lacks workspace_id.
    Without factoring runs_missing_workspace_id into the gate, the CLI would
    report "already migrated" and never touch the pending run.
    """
    run_a = _plant_run(tmp_foundry, "cli_gate_run_a")

    result = _invoke_with_paths(
        tmp_foundry, "workspace", "migrate", "--apply", "--json"
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "applied", (
        "idempotency gate incorrectly short-circuited while a run still needed "
        f"workspace_id stamping: {payload}"
    )
    assert payload["total_runs_succeeded"] == 1
    assert load_yaml(run_a).get("workspace_id") == "default"


def test_cli_migrate_apply_second_call_reports_already_migrated(tmp_foundry: FoundryPaths) -> None:
    """After both drafts and runs are migrated, a second --apply reports already_migrated."""
    _plant_run(tmp_foundry, "cli_gate_run_second")

    first = _invoke_with_paths(tmp_foundry, "workspace", "migrate", "--apply", "--json")
    assert first.exit_code == 0, first.output
    assert json.loads(first.output)["status"] == "applied"

    second = _invoke_with_paths(tmp_foundry, "workspace", "migrate", "--apply", "--json")
    assert second.exit_code == 0, second.output
    second_payload = json.loads(second.output)
    assert second_payload["status"] == "already_migrated"


def test_cli_rollback_reverses_linked_draft_and_run_manifests(tmp_foundry: FoundryPaths) -> None:
    """A single `rf workspace rollback <migration_run_id>` reverses drafts AND runs.

    `rf workspace migrate --apply` mints two separate BackfillReport manifests
    (backfill() and backfill_runs() each call datetime.now(UTC) independently),
    so the CLI writes a small linkage file associating the drafts
    migration_run_id with the runs migration_run_id. This test proves rollback
    follows that link automatically.
    """
    run_a = _plant_run(tmp_foundry, "cli_rb_run_a")
    hash_before = _file_hash(run_a)

    apply_result = _invoke_with_paths(
        tmp_foundry, "workspace", "migrate", "--apply", "--json"
    )
    assert apply_result.exit_code == 0, apply_result.output
    apply_payload = json.loads(apply_result.output)
    drafts_migration_run_id = apply_payload["migration_run_id"]
    runs_migration_run_id = apply_payload["run_migration_run_id"]
    assert drafts_migration_run_id != runs_migration_run_id, (
        "backfill() and backfill_runs() mint independent migration_run_ids"
    )

    assert load_yaml(run_a).get("workspace_id") == "default"

    rollback_result = _invoke_with_paths(
        tmp_foundry, "workspace", "rollback", drafts_migration_run_id, "--json"
    )
    assert rollback_result.exit_code == 0, rollback_result.output
    rollback_payload = json.loads(rollback_result.output)

    assert rollback_payload["linked_run_migration_run_id"] == runs_migration_run_id
    assert rollback_payload["total_reverted_runs"] == 1
    assert rollback_payload["total_failed"] == 0

    # run.yaml is restored byte-identically (workspace_id key removed, not "").
    assert _file_hash(run_a) == hash_before
    assert "workspace_id" not in load_yaml(run_a)


def test_cli_rollback_without_link_reverses_drafts_only(tmp_foundry: FoundryPaths) -> None:
    """Rolling back a migration_run_id with no linkage file behaves as before (drafts only).

    Regression guard: calling `backfill_runs` directly (bypassing the CLI's
    `migrate --apply` linkage step) must not confuse a later rollback of an
    unrelated drafts-only migration_run_id.
    """
    from research_foundry.services.workspace_migration_service import (
        backfill as _backfill,
    )

    _plant_run(tmp_foundry, "cli_rb_unlinked_run")

    # Draft-only backfill via the service directly — no CLI linkage file written.
    draft_report = _backfill(tmp_foundry, "default")

    result = _invoke_with_paths(
        tmp_foundry, "workspace", "rollback", draft_report.migration_run_id, "--json"
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["linked_run_migration_run_id"] is None
    assert payload["total_reverted_runs"] == 0
