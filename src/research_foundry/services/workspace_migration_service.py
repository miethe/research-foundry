"""Workspace isolation migration service — public-multiuser-release P5.3 WKSP-301/302.

Dry-run evaluation, forward backfill, rollback runbook, and shared dataclass
schemas for the workspace_id migration.

Critical invariants
-------------------
* :func:`dry_run` performs **zero writes** to any file or database.  This is
  contractual: the WKSP-301 unit test asserts that every ``draft.yaml``'s
  mtime and content hash are byte-identical before and after calling
  :func:`dry_run`.
* :func:`backfill` ONLY touches records where ``workspace_id`` is currently
  ``None`` or absent.  Records with a non-null ``workspace_id`` are skipped
  unconditionally.
* :func:`rollback` NEVER keys on the value ``workspace_id == "default"``.
  It uses ONLY the explicit record-id list from the stored manifest.
* The shared dataclasses (:class:`DryRunReport`, :class:`BackfillReport`,
  :class:`BackfillManifestEntry`) are the **canonical schemas** for WKSP-302
  and WKSP-303.  Each task MUST reuse these classes; defining local variants
  is prohibited.

Why direct file walk instead of catalog_report_drafts (Critical Schema Finding)
--------------------------------------------------------------------------------
``catalog_report_drafts`` is a derived, rebuildable index table in
``catalog.db``.  It:

* May be absent or stale.
* Does NOT contain ``workspace_id`` / ``created_by`` (the column does not
  exist in ``catalog_items`` or ``catalog_report_drafts`` until WKSP-303's
  schema bump + rebuild).
* Is rebuilt from the canonical ``draft.yaml`` files by
  :func:`~research_foundry.services.builder_service.reindex_all_drafts`.

:func:`dry_run` and :func:`backfill` therefore walk
``<workspace>/reports/drafts/<id>/draft.yaml`` files directly (the same
pattern as ``builder_service.reindex_all_drafts``) to tally and mutate
actual on-disk workspace_id / created_by presence.

``catalog_items`` row count is read from ``catalog.db``; that read is
read-only (no lock escalation) and the column-absent state is expected
and documented.

Migration manifest location
----------------------------
Each :func:`backfill` run writes a JSON manifest to::

    <workspace>/.rf_state/migrations/<migration_run_id>-workspace-backfill.json

The ``migration_run_id`` is an ISO-8601 compact timestamp (microsecond
precision).  Pass it to :func:`rollback` to reverse the run.

Run-record backfill (DF-004)
-----------------------------
:func:`dry_run_runs` / :func:`backfill_runs` are the parallel entry points
for legacy ``runs/<run_id>/run.yaml`` records (created before ``workspace_id``
existed on the run schema — a concurrent DF-004 task adds ``workspace_id`` /
``visibility`` to newly-created runs; this module only backfills the
pre-existing ones already on disk).  They reuse the canonical
:class:`BackfillReport` / :class:`BackfillManifestEntry` schemas
(``record_type="run"``) and the shared atomic-write + manifest helpers, so a
single :func:`rollback` call reverses either kind of record by
``migration_run_id``.  Runs are pure files with no rebuildable SQLite index
(unlike ``catalog_items`` for drafts) so :func:`backfill_runs` has no
DB-rebuild step, and it never sets ``visibility`` — only ``workspace_id`` —
so legacy runs stay at the reader's ``"workspace"`` default rather than
becoming public.
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..paths import FoundryPaths
from ..yamlio import dumps_yaml, load_yaml


# ---------------------------------------------------------------------------
# Shared dataclasses (WKSP-301/302/303 — canonical schemas)
# ---------------------------------------------------------------------------


@dataclass
class DryRunReport:
    """Results of a zero-write workspace migration dry-run evaluation.

    Attributes
    ----------
    total_drafts:
        Total ``draft.yaml`` files found under
        ``<workspace>/reports/drafts/``.
    drafts_missing_workspace_id:
        Drafts whose ``draft.yaml`` has a null or absent ``workspace_id``
        field.  These are the primary target of the WKSP-303 forward backfill.
    drafts_missing_created_by:
        Drafts whose ``draft.yaml`` has a null or absent ``created_by``
        field (secondary migration target).
    total_catalog_items:
        Current row count in the ``catalog_items`` table.  Always
        workspace-less pre-migration because the ``workspace_id`` column does
        not yet exist in ``catalog.db`` (see Critical Schema Finding above).
    target_workspace_id:
        The ``workspace_id`` that will be written to all pre-migration records
        during the WKSP-303 forward backfill (``"default"`` for the
        single-tenant initial deployment).
    caller_impact_summary:
        Human-readable impact statement for the operator reviewing the
        dry-run output before approving GATE-1.
    """

    total_drafts: int = 0
    drafts_missing_workspace_id: int = 0
    drafts_missing_created_by: int = 0
    total_catalog_items: int = 0
    target_workspace_id: str = "default"
    caller_impact_summary: str = (
        "Today there is 1 implicit workspace so 0 existing callers "
        "would be newly denied by the workspace isolation migration."
    )


@dataclass
class RunDryRunReport:
    """Results of a zero-write dry-run evaluation over legacy ``run.yaml`` records.

    Parallel to :class:`DryRunReport` but scoped to ``runs/<run_id>/run.yaml``
    files (DF-004 backfill).  Unlike the draft dry-run, there is no
    ``catalog_items`` counterpart — runs are pure files with no rebuildable
    SQLite index — so this report tracks only run counts.

    Attributes
    ----------
    total_runs:
        Total ``run.yaml`` files found directly under ``<workspace>/runs/``.
    runs_missing_workspace_id:
        Runs whose ``run.yaml`` has a null or absent ``workspace_id`` field —
        the target of :func:`backfill_runs`.
    target_workspace_id:
        The ``workspace_id`` that :func:`backfill_runs` will stamp onto every
        pre-migration run record (``"default"`` for the initial deployment).
    caller_impact_summary:
        Human-readable impact statement for the operator reviewing the
        dry-run output.
    """

    total_runs: int = 0
    runs_missing_workspace_id: int = 0
    target_workspace_id: str = "default"
    caller_impact_summary: str = (
        "Today there is 1 implicit workspace so 0 existing callers "
        "would be newly denied by the run workspace-isolation backfill."
    )


@dataclass
class BackfillManifestEntry:
    """One record in the backfill manifest (used by WKSP-302/303/DF-004).

    Attributes
    ----------
    record_type:
        ``"draft"`` for ``draft.yaml`` records; ``"catalog_item"`` for rows
        in ``catalog.db``'s ``catalog_items`` table; ``"run"`` for
        ``run.yaml`` records (DF-004 backfill).
    record_id:
        Stable identifier (``report_draft_id`` for drafts;
        ``catalog_item_id`` for catalog items).
    prior_workspace_id:
        The ``workspace_id`` value **before** the backfill — typically
        ``None`` for all pre-migration records.
    prior_created_by:
        The ``created_by`` value before the backfill (may also be ``None``).
    new_workspace_id:
        The ``workspace_id`` assigned by the backfill operation
        (``"default"`` for the initial single-tenant migration).
    migration_run_id:
        The identifier of the :func:`backfill` run that created this entry.
        Set automatically; ``""`` is the backward-compatible default for
        entries constructed outside of :func:`backfill`.
    """

    record_type: str  # "draft" | "catalog_item"
    record_id: str
    prior_workspace_id: str | None
    prior_created_by: str | None
    new_workspace_id: str
    migration_run_id: str = ""  # set by backfill(); empty string = backward-compat default


@dataclass
class BackfillReport:
    """Results of an applied backfill operation.

    Shared schema for WKSP-302 (rollback runbook) and WKSP-303 (forward
    migration).  Each task MUST use this class instead of defining its own.

    Attributes
    ----------
    total_attempted:
        Total records targeted by the backfill run.
    total_succeeded:
        Records successfully updated.
    total_failed:
        Records that could not be updated (missing file, schema mismatch,
        unreadable YAML, etc.).  A non-zero value means partial success —
        the manifest contains per-record detail for debugging.
    manifest:
        Full list of :class:`BackfillManifestEntry` items (for the audit
        trail and the WKSP-302 rollback index).
    target_workspace_id:
        The ``workspace_id`` value applied to all records in this run.
    migration_run_id:
        Identifier of this backfill run (ISO-8601 timestamp).  Pass to
        :func:`rollback` to reverse this run.
    """

    total_attempted: int = 0
    total_succeeded: int = 0
    total_failed: int = 0
    manifest: list[BackfillManifestEntry] = field(default_factory=list)
    target_workspace_id: str = "default"
    migration_run_id: str = ""  # set by backfill(); empty string = not-yet-run default
    catalog_rebuild_ok: bool = True
    catalog_rebuild_error: str | None = None


@dataclass
class RollbackReport:
    """Results of a :func:`rollback` operation.

    Attributes
    ----------
    migration_run_id:
        The identifier of the backfill run that was reversed.
    total_attempted:
        Total records in the manifest that were attempted (drafts + runs +
        catalog_items).
    total_reverted_drafts:
        Draft records successfully reverted to their prior state.
    total_reverted_runs:
        Run records (``run.yaml``, DF-004) successfully reverted to their
        prior state.
    total_failed:
        Records whose revert failed (missing file, unreadable YAML, etc.).
    catalog_item_note:
        Explains that ``catalog_items`` rollback is not automated; the
        operator must revert the schema version and run ``rf catalog rebuild``.
    is_dry_run:
        ``True`` when called with ``dry_run=True`` — no writes occurred.
    """

    migration_run_id: str
    total_attempted: int = 0
    total_reverted_drafts: int = 0
    total_reverted_runs: int = 0
    total_failed: int = 0
    catalog_item_note: str = (
        "catalog_items rollback = revert schema_version + run 'rf catalog rebuild' "
        "(no coded per-row reverter for the disposable index table)"
    )
    is_dry_run: bool = False


# ---------------------------------------------------------------------------
# dry_run — zero-write evaluation (WKSP-301)
# ---------------------------------------------------------------------------


def dry_run(paths: FoundryPaths) -> DryRunReport:
    """Evaluate what the workspace isolation migration would affect.

    Reads ``draft.yaml`` files on disk and the ``catalog.db`` row count.
    **Performs zero writes** to any file, table, or lock.

    Draft walk
    ----------
    Iterates ``<workspace>/reports/drafts/<id>/draft.yaml`` directly (NOT
    the derived ``catalog_report_drafts`` index — see module docstring for
    rationale).  Drafts whose ``workspace_id`` field is falsy (``None``,
    empty string, absent key) are counted as missing.

    Catalog count
    -------------
    Issues a read-only ``SELECT COUNT(*) FROM catalog_items`` against
    ``catalog.db``.  The ``workspace_id`` column is expected to be absent at
    this stage — the count reflects total row cardinality pre-migration.
    Absence of ``catalog.db`` or absence of the ``catalog_items`` table both
    result in ``total_catalog_items=0`` (no error raised).

    Parameters
    ----------
    paths:
        Resolved :class:`~research_foundry.paths.FoundryPaths` for the
        workspace under inspection.

    Returns
    -------
    DryRunReport
        Snapshot of on-disk state: draft counts by workspace_id / created_by
        presence, catalog item count, and the projected migration target.
    """
    report = DryRunReport(target_workspace_id="default")

    # --- Walk draft.yaml files directly (NOT catalog_report_drafts) ----------
    drafts_root = paths.report_drafts
    if drafts_root.is_dir():
        for draft_dir in sorted(drafts_root.iterdir()):
            if not draft_dir.is_dir():
                continue
            draft_yaml_path = draft_dir / "draft.yaml"
            if not draft_yaml_path.exists():
                continue
            report.total_drafts += 1
            try:
                data: Any = load_yaml(draft_yaml_path)
                if not isinstance(data, dict):
                    # Malformed draft — count as missing both fields.
                    report.drafts_missing_workspace_id += 1
                    report.drafts_missing_created_by += 1
                    continue
                if not data.get("workspace_id"):
                    report.drafts_missing_workspace_id += 1
                if not data.get("created_by"):
                    report.drafts_missing_created_by += 1
            except Exception:  # noqa: BLE001 — unreadable draft still counted
                report.drafts_missing_workspace_id += 1
                report.drafts_missing_created_by += 1

    # --- Count catalog_items rows (all workspace-less pre-migration) ---------
    catalog_db_path = paths.catalog_db
    if catalog_db_path.exists():
        try:
            with sqlite3.connect(str(catalog_db_path)) as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM catalog_items"
                ).fetchone()
                report.total_catalog_items = row[0] if row else 0
        except Exception:  # noqa: BLE001 — table absent or schema mismatch
            report.total_catalog_items = 0

    return report


# ---------------------------------------------------------------------------
# dry_run_runs — zero-write evaluation over run.yaml records (DF-004)
# ---------------------------------------------------------------------------


def dry_run_runs(paths: FoundryPaths) -> RunDryRunReport:
    """Evaluate what the run-record workspace backfill would affect.

    Mirrors :func:`dry_run`'s draft walk but scoped to
    ``<workspace>/runs/<run_id>/run.yaml`` files. **Performs zero writes**
    to any file.

    Runs are pure files with no rebuildable SQLite index counterpart (unlike
    ``catalog_items`` for drafts), so this function has no DB-count step.

    Parameters
    ----------
    paths:
        Resolved :class:`~research_foundry.paths.FoundryPaths` for the
        workspace under inspection.

    Returns
    -------
    RunDryRunReport
        Snapshot of on-disk state: run counts by ``workspace_id`` presence
        and the projected migration target.
    """
    report = RunDryRunReport(target_workspace_id="default")

    runs_root = paths.runs
    if runs_root.is_dir():
        for run_dir in sorted(runs_root.iterdir()):
            if not run_dir.is_dir():
                continue
            run_yaml_path = paths.run_paths(run_dir.name).run_yaml
            if not run_yaml_path.exists():
                continue
            report.total_runs += 1
            try:
                data: Any = load_yaml(run_yaml_path)
                if not isinstance(data, dict):
                    # Malformed run record — count as missing.
                    report.runs_missing_workspace_id += 1
                    continue
                if not data.get("workspace_id"):
                    report.runs_missing_workspace_id += 1
            except Exception:  # noqa: BLE001 — unreadable run still counted
                report.runs_missing_workspace_id += 1

    return report


# ---------------------------------------------------------------------------
# Internal helpers (WKSP-302)
# ---------------------------------------------------------------------------


def _atomic_write_yaml(obj: dict[str, Any], path: Path) -> Path:
    """Write YAML atomically: temp file in same directory, then ``os.replace``.

    Mirrors the pattern from ``builder_service._atomic_write_yaml``.  A crash
    mid-write never leaves a torn ``draft.yaml`` — ``os.replace`` is atomic on
    the same filesystem and the temp file is unlinked on any failure.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(dumps_yaml(obj))
        os.replace(tmp_name, path)
    except BaseException:
        with suppress(OSError):
            os.unlink(tmp_name)
        raise
    return path


def _migrations_dir(paths: FoundryPaths) -> Path:
    """Return (and lazily create) the ``.rf_state/migrations/`` directory."""
    d = Path(paths.rf_state) / "migrations"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _manifest_path(paths: FoundryPaths, migration_run_id: str) -> Path:
    """Return the filesystem path for ``migration_run_id``'s manifest JSON."""
    return _migrations_dir(paths) / f"{migration_run_id}-workspace-backfill.json"


def _write_manifest(
    paths: FoundryPaths, migration_run_id: str, report: BackfillReport
) -> Path:
    """Serialize ``report.manifest`` to JSON; return the path written."""
    mpath = _manifest_path(paths, migration_run_id)
    payload = {
        "migration_run_id": migration_run_id,
        "target_workspace_id": report.target_workspace_id,
        "total_attempted": report.total_attempted,
        "total_succeeded": report.total_succeeded,
        "total_failed": report.total_failed,
        "entries": [
            {
                "record_type": e.record_type,
                "record_id": e.record_id,
                "prior_workspace_id": e.prior_workspace_id,
                "prior_created_by": e.prior_created_by,
                "new_workspace_id": e.new_workspace_id,
                "migration_run_id": e.migration_run_id,
            }
            for e in report.manifest
        ],
    }
    mpath.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return mpath


def _read_manifest(
    paths: FoundryPaths, migration_run_id: str
) -> list[BackfillManifestEntry]:
    """Load manifest entries for ``migration_run_id`` from ``.rf_state/migrations/``.

    Raises ``FileNotFoundError`` when no manifest exists for the given id.
    """
    mpath = _manifest_path(paths, migration_run_id)
    if not mpath.exists():
        raise FileNotFoundError(
            f"No migration manifest found for run_id={migration_run_id!r}; "
            f"expected: {mpath}"
        )
    payload = json.loads(mpath.read_text(encoding="utf-8"))
    return [
        BackfillManifestEntry(
            record_type=e["record_type"],
            record_id=e["record_id"],
            prior_workspace_id=e.get("prior_workspace_id"),
            prior_created_by=e.get("prior_created_by"),
            new_workspace_id=e["new_workspace_id"],
            migration_run_id=e.get("migration_run_id", migration_run_id),
        )
        for e in payload.get("entries", [])
    ]


# ---------------------------------------------------------------------------
# backfill — forward mutation (WKSP-302)
# ---------------------------------------------------------------------------


def backfill(
    paths: FoundryPaths, workspace_id: str = "default"
) -> BackfillReport:
    """Assign ``workspace_id`` to every legacy draft record that lacks one.

    Walk Logic
    ----------
    Iterates ``<workspace>/reports/drafts/<id>/draft.yaml`` directly (NOT
    the derived index).  Only records where ``workspace_id`` is currently
    falsy (``None``, empty string, absent key) are mutated.  Records with an
    existing non-null ``workspace_id`` are silently skipped.

    Atomic Writes
    -------------
    Each ``draft.yaml`` is updated using the temp-file + ``os.replace``
    atomic pattern to prevent torn writes.

    Manifest
    --------
    After processing all drafts a JSON manifest is written to::

        <workspace>/.rf_state/migrations/<migration_run_id>-workspace-backfill.json

    The manifest is the sole input to :func:`rollback`.

    Parameters
    ----------
    paths:
        Resolved :class:`~research_foundry.paths.FoundryPaths` for the
        workspace to migrate.
    workspace_id:
        The workspace identifier to stamp on all pre-migration records
        (default ``"default"``).

    Returns
    -------
    BackfillReport
        Counts and full manifest for the run.  ``migration_run_id`` on the
        returned report is the key needed to call :func:`rollback`.
    """
    migration_run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    report = BackfillReport(
        target_workspace_id=workspace_id, migration_run_id=migration_run_id
    )

    drafts_root = Path(paths.report_drafts)
    if drafts_root.is_dir():
        for draft_dir in sorted(drafts_root.iterdir()):
            if not draft_dir.is_dir():
                continue
            draft_yaml_path = draft_dir / "draft.yaml"
            if not draft_yaml_path.exists():
                continue

            try:
                data: Any = load_yaml(draft_yaml_path)
                if not isinstance(data, dict):
                    # Malformed draft — skip (dry_run already tallied it).
                    continue

                # INVARIANT: only touch records where workspace_id is null.
                if data.get("workspace_id"):
                    continue

                prior_workspace_id: str | None = data.get("workspace_id")  # None
                prior_created_by: str | None = data.get("created_by")
                record_id = str(data.get("report_draft_id", draft_dir.name))

                entry = BackfillManifestEntry(
                    record_type="draft",
                    record_id=record_id,
                    prior_workspace_id=prior_workspace_id,
                    prior_created_by=prior_created_by,
                    new_workspace_id=workspace_id,
                    migration_run_id=migration_run_id,
                )

                report.total_attempted += 1

                # Atomic write: stamp workspace_id onto the draft.
                updated_data = dict(data)
                updated_data["workspace_id"] = workspace_id
                _atomic_write_yaml(updated_data, draft_yaml_path)

                report.manifest.append(entry)
                report.total_succeeded += 1

            except Exception:  # noqa: BLE001 — unreadable draft; skip
                report.total_attempted += 1
                report.total_failed += 1

    _write_manifest(paths, migration_run_id, report)

    # Rebuild the catalog schema + data with the new workspace_id column.
    # SCHEMA_VERSION bump (2→3) ensures drop+recreate on next _ensure_schema;
    # calling rebuild() here makes the migration atomic from the operator's
    # perspective — both draft YAML files and catalog.db are updated in one
    # `rf workspace migrate --apply` invocation.
    # catalog.db is 100% disposable — any failure here is logged but non-fatal.
    try:
        from . import catalog_service as _cs  # noqa: PLC0415
        _cs.rebuild(paths)
    except Exception as _rebuild_err:  # noqa: BLE001
        report.catalog_rebuild_ok = False
        report.catalog_rebuild_error = str(_rebuild_err)

    return report


# ---------------------------------------------------------------------------
# backfill_runs — forward mutation over run.yaml records (DF-004)
# ---------------------------------------------------------------------------


def backfill_runs(
    paths: FoundryPaths, workspace_id: str = "default"
) -> BackfillReport:
    """Assign ``workspace_id`` to every legacy run record that lacks one.

    Mirrors :func:`backfill`'s draft walk/mutation logic but scoped to
    ``<workspace>/runs/<run_id>/run.yaml`` files (DF-004). Reuses the
    canonical :class:`BackfillReport` / :class:`BackfillManifestEntry`
    schemas with ``record_type="run"`` so :func:`rollback` can reverse this
    run unambiguously alongside draft-record migrations.

    Walk Logic
    ----------
    Iterates ``<workspace>/runs/<run_id>/run.yaml`` directly. Only records
    where ``workspace_id`` is currently falsy (``None``, empty string,
    absent key) are mutated — records with an existing non-null
    ``workspace_id`` are silently skipped (same invariant as :func:`backfill`).

    Visibility is intentionally NOT set here: legacy runs must not become
    public. Only ``workspace_id`` is stamped; the reader defaults absent
    ``visibility`` to ``"workspace"``.

    No DB Rebuild
    -------------
    Unlike :func:`backfill`, this function does **not** rebuild any catalog
    index — runs are pure files with no rebuildable SQLite counterpart.
    ``catalog_rebuild_ok``/``catalog_rebuild_error`` on the returned report
    are left at their defaults (``True``/``None``) and should be ignored by
    callers of this function.

    Atomic Writes
    -------------
    Each ``run.yaml`` is updated using the temp-file + ``os.replace`` atomic
    pattern (:func:`_atomic_write_yaml`) to prevent torn writes.

    Manifest
    --------
    After processing all runs a JSON manifest is written via
    :func:`_write_manifest` to::

        <workspace>/.rf_state/migrations/<migration_run_id>-workspace-backfill.json

    The manifest is the sole input to :func:`rollback`.

    Parameters
    ----------
    paths:
        Resolved :class:`~research_foundry.paths.FoundryPaths` for the
        workspace to migrate.
    workspace_id:
        The workspace identifier to stamp on all pre-migration run records
        (default ``"default"``).

    Returns
    -------
    BackfillReport
        Counts and full manifest for the run. ``migration_run_id`` on the
        returned report is the key needed to call :func:`rollback`.
    """
    migration_run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
    report = BackfillReport(
        target_workspace_id=workspace_id, migration_run_id=migration_run_id
    )

    runs_root = Path(paths.runs)
    if runs_root.is_dir():
        for run_dir in sorted(runs_root.iterdir()):
            if not run_dir.is_dir():
                continue
            run_yaml_path = paths.run_paths(run_dir.name).run_yaml
            if not run_yaml_path.exists():
                continue

            try:
                data: Any = load_yaml(run_yaml_path)
                if not isinstance(data, dict):
                    # Malformed run record — skip (dry_run_runs already tallied it).
                    continue

                # INVARIANT: only touch records where workspace_id is null.
                if data.get("workspace_id"):
                    continue

                prior_workspace_id: str | None = data.get("workspace_id")  # None
                prior_created_by: str | None = data.get("created_by")
                record_id = str(data.get("run_id", run_dir.name))

                entry = BackfillManifestEntry(
                    record_type="run",
                    record_id=record_id,
                    prior_workspace_id=prior_workspace_id,
                    prior_created_by=prior_created_by,
                    new_workspace_id=workspace_id,
                    migration_run_id=migration_run_id,
                )

                report.total_attempted += 1

                # Atomic write: stamp workspace_id onto the run record.
                # visibility is intentionally NOT set — the reader defaults
                # absent visibility to "workspace"; legacy runs must not
                # become public.
                updated_data = dict(data)
                updated_data["workspace_id"] = workspace_id
                _atomic_write_yaml(updated_data, run_yaml_path)

                report.manifest.append(entry)
                report.total_succeeded += 1

            except Exception:  # noqa: BLE001 — unreadable run; skip
                report.total_attempted += 1
                report.total_failed += 1

    _write_manifest(paths, migration_run_id, report)

    # No DB rebuild for runs — they are pure files (see docstring). Leave
    # report.catalog_rebuild_ok / catalog_rebuild_error at their defaults.

    return report


# ---------------------------------------------------------------------------
# rollback — reverse mutation (WKSP-302)
# ---------------------------------------------------------------------------


def rollback(
    paths: FoundryPaths, migration_run_id: str, *, dry_run: bool = False
) -> RollbackReport:
    """Reverse a previous :func:`backfill` run identified by ``migration_run_id``.

    Safety invariants
    -----------------
    * NEVER keys on the value ``workspace_id == "default"``.  The only
      authority is the explicit record-id list in the stored manifest.
    * ``catalog_items`` have no coded per-row rollback (the table is a
      rebuildable index); the ``catalog_item_note`` field on the returned
      report explains what the operator must do manually.
    * ``run`` entries (DF-004, produced by :func:`backfill_runs`) are
      reverted with the exact same restore logic as ``draft`` entries —
      only the on-disk path differs (``runs/<run_id>/run.yaml`` via
      ``paths.run_paths(record_id).run_yaml`` instead of
      ``reports/drafts/<id>/draft.yaml``).

    Parameters
    ----------
    paths:
        Resolved :class:`~research_foundry.paths.FoundryPaths` for the
        workspace whose migration is being reversed.
    migration_run_id:
        The ``migration_run_id`` from the :class:`BackfillReport` returned
        by the original :func:`backfill` call (and printed by
        ``rf workspace rollback``).
    dry_run:
        When ``True`` no files are written; the returned report describes
        what *would* be reverted.

    Returns
    -------
    RollbackReport
        Counts, ``is_dry_run`` flag, and the ``catalog_item_note``.

    Raises
    ------
    FileNotFoundError
        When no manifest exists for ``migration_run_id``.
    """
    entries = _read_manifest(paths, migration_run_id)
    result = RollbackReport(migration_run_id=migration_run_id, is_dry_run=dry_run)

    for entry in entries:
        if entry.record_type == "catalog_item":
            # No coded per-row rollback for catalog_items (rebuildable index).
            # The caller must revert schema_version and run `rf catalog rebuild`.
            result.total_attempted += 1
            # Counted as attempted; result.catalog_item_note explains the manual step.
            continue

        if entry.record_type == "draft":
            record_path = Path(paths.report_drafts) / entry.record_id / "draft.yaml"
        elif entry.record_type == "run":
            record_path = paths.run_paths(entry.record_id).run_yaml
        else:
            # Unknown record type — skip silently.
            continue

        result.total_attempted += 1

        if not record_path.exists():
            result.total_failed += 1
            continue

        try:
            data = load_yaml(record_path)
            if not isinstance(data, dict):
                result.total_failed += 1
                continue

            # Restore prior_workspace_id.
            # If prior value was None → remove the key entirely (byte-stable).
            if entry.prior_workspace_id is None:
                data.pop("workspace_id", None)
            else:
                data["workspace_id"] = entry.prior_workspace_id

            # Restore prior_created_by.
            if entry.prior_created_by is None:
                data.pop("created_by", None)
            else:
                data["created_by"] = entry.prior_created_by

            if not dry_run:
                _atomic_write_yaml(data, record_path)

            if entry.record_type == "run":
                result.total_reverted_runs += 1
            else:
                result.total_reverted_drafts += 1

        except Exception:  # noqa: BLE001 — unreadable record
            result.total_failed += 1

    return result


def _catalog_has_workspace_id_column(paths: FoundryPaths) -> bool:
    """Return True when catalog.db already has a workspace_id column in catalog_items.

    Used by the CLI idempotency gate to detect workspaces where legacy drafts
    are already migrated but the catalog schema has not yet been rebuilt to v3
    (i.e., the ``workspace_id`` column is missing from ``catalog_items``).

    Returns False when catalog.db is absent, the catalog_items table does not
    exist, or any error prevents the check — so the caller conservatively falls
    through to ``backfill()`` which will trigger the catalog rebuild.
    """
    catalog_db_path = paths.catalog_db
    if not catalog_db_path.exists():
        return False
    try:
        with sqlite3.connect(str(catalog_db_path)) as conn:
            rows = conn.execute("PRAGMA table_info(catalog_items)").fetchall()
            return any(row[1] == "workspace_id" for row in rows)
    except Exception:  # noqa: BLE001
        return False


__all__ = [
    "DryRunReport",
    "RunDryRunReport",
    "BackfillManifestEntry",
    "BackfillReport",
    "RollbackReport",
    "dry_run",
    "dry_run_runs",
    "backfill",
    "backfill_runs",
    "rollback",
]
