"""Backlog metadata derivation — shared helper for Phase P2 (backfill) and P3 (creation).

This module is the SINGLE place that reads ``backlog/research_idea_backlog.yaml``
and converts it into run-level metadata.  Both the backfill migration script
(P2) and ``plan_run()`` (P3) import from here so there is no duplicated
derivation logic.  It is also the sole writer for lifecycle status and links
via :func:`reconcile_backlog`.

Public API
----------
BacklogMetadata
    Typed result container for the five new run metadata fields.
load_backlog_index(paths)
    Build a dict mapping each idea's ``ref`` (e.g. ``RIB-001``) to its
    :class:`BacklogMetadata`.
lookup_metadata(backlog_idea_ref, paths)
    Convenience wrapper — look up a single ref; returns ``None`` when absent.
ReconcileDiff
    A single field change produced by :func:`reconcile_backlog`.
reconcile_backlog(paths, dry_run)
    Idempotent run→backlog lifecycle writer.  Scans ``runs/*/run.yaml`` for
    ``backlog_idea_ref``, maps each back to its idea entry, and fills in
    missing ``status`` / ``links`` fields.  Never regresses a status or
    overwrites a non-null link.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..paths import FoundryPaths
from ..yamlio import dumps_yaml, load_yaml

# Path relative to workspace root where the backlog lives.
_BACKLOG_REL = Path("backlog") / "research_idea_backlog.yaml"

# Forward order of the lifecycle (must be strictly ordered).
_STATUS_ORDER = ["proposed", "captured", "planned", "running", "completed"]


@dataclass(frozen=True)
class BacklogMetadata:
    """Metadata derived from a single backlog idea for storage in ``run.yaml``."""

    # Backlog reference slug (e.g. ``RIB-001``).
    backlog_idea_ref: str
    # Stable idea id slug (e.g. ``idea_claim-segmentation-source-alignment``).
    backlog_idea_id: str
    # Pillar identifier maps to ``category`` in run.yaml.
    category: str | None
    # Union of idea tags.
    tags: list[str]
    # Derived from ``suggested_project`` (at most one entry for a single idea).
    linked_projects: list[str]


def _backlog_path(paths: FoundryPaths) -> Path:
    return paths.root / _BACKLOG_REL


def load_backlog_index(paths: FoundryPaths) -> dict[str, BacklogMetadata]:
    """Return a mapping of ``ref`` → :class:`BacklogMetadata` for all ideas.

    Ideas that have no ``ref`` field are skipped.  This function reads the
    backlog file fresh on every call (no caching) so the caller can control
    caching via :func:`cached_load_backlog_index` when needed.

    Parameters
    ----------
    paths:
        Workspace paths — used to locate ``backlog/research_idea_backlog.yaml``.

    Returns
    -------
    dict[str, BacklogMetadata]
        Keyed by idea ``ref`` (e.g. ``"RIB-001"``).
    """
    backlog_path = _backlog_path(paths)
    if not backlog_path.exists():
        return {}

    doc: dict[str, Any] = load_yaml(backlog_path)
    ideas: list[Any] = doc.get("ideas") or []

    index: dict[str, BacklogMetadata] = {}
    for idea in ideas:
        if not isinstance(idea, dict):
            continue
        ref = idea.get("ref")
        if not ref:
            continue

        idea_id: str = str(idea.get("id") or "")
        category_raw = idea.get("pillar")
        category: str | None = str(category_raw) if category_raw else None

        raw_tags = idea.get("tags") or []
        tags: list[str] = [str(t) for t in raw_tags if t]

        suggested = idea.get("suggested_project")
        linked_projects: list[str] = [str(suggested)] if suggested else []

        index[str(ref)] = BacklogMetadata(
            backlog_idea_ref=str(ref),
            backlog_idea_id=idea_id,
            category=category,
            tags=tags,
            linked_projects=linked_projects,
        )

    return index


def lookup_metadata(
    backlog_idea_ref: str,
    paths: FoundryPaths,
) -> BacklogMetadata | None:
    """Look up metadata for a single backlog ref.

    Parameters
    ----------
    backlog_idea_ref:
        The ``RIB-NNN`` style ref to look up.
    paths:
        Workspace paths.

    Returns
    -------
    BacklogMetadata | None
        ``None`` when the ref is not found in the backlog.
    """
    index = load_backlog_index(paths)
    return index.get(backlog_idea_ref)


def backlog_exists(paths: FoundryPaths) -> bool:
    """Return ``True`` if the backlog file is present in the workspace."""
    return _backlog_path(paths).exists()


# ---------------------------------------------------------------------------
# Reconciler
# ---------------------------------------------------------------------------


@dataclass
class ReconcileDiff:
    """A single field change proposed or applied by :func:`reconcile_backlog`."""

    ref: str
    field: str
    old: Any
    new: Any


def _status_rank(status: str | None) -> int:
    """Return the ordinal of *status* in the lifecycle, or -1 when unknown."""
    try:
        return _STATUS_ORDER.index(str(status)) if status else -1
    except ValueError:
        return -1


def _infer_run_status(run_yaml_path: Path, run_data: dict[str, Any]) -> str:
    """Determine whether a run is 'completed' or 'running'.

    Conservative heuristic:
    * ``completed``  if report_deterministic.md exists in ``reports/``, or
                     if ``run.yaml`` status is in {``verified``, ``bundled``, ``completed``}.
    * ``running``    otherwise (in-progress, planned, or anything uncertain).

    The 'running' default is intentional — never over-promote.
    """
    explicit_status = str(run_data.get("status") or "").lower()
    if explicit_status in {"verified", "bundled", "completed", "done"}:
        return "completed"

    # Presence of a deterministic report is the primary finished signal.
    det_report = run_yaml_path.parent / "reports" / "report_deterministic.md"
    if det_report.exists():
        return "completed"

    return "running"


def reconcile_backlog(
    paths: FoundryPaths,
    dry_run: bool = True,
) -> tuple[list[ReconcileDiff], list[str], list[str]]:
    """Idempotent run→backlog lifecycle writer.

    Scans ``runs/*/run.yaml`` for ``backlog_idea_ref``, maps each back to its
    idea entry, and fills in missing ``status`` / ``links`` fields.  Also
    reports inverse drift (backlog ideas marked ``completed`` with no matching
    run dir, and run dirs with no ``backlog_idea_ref``).

    Rules
    -----
    * Status advances FORWARD only: proposed < captured < planned < running <
      completed.  A higher status is never regressed.
    * Links are only backfilled when the current value is ``null`` or absent.
      Non-null links are never overwritten.
    * "Finished" heuristic: ``report_deterministic.md`` present → completed;
      run.yaml status in {verified, bundled, completed, done} → completed;
      anything else → running.

    Parameters
    ----------
    paths:
        Workspace paths — used to locate the backlog and runs directory.
    dry_run:
        When ``True`` (default), compute changes but do NOT write.  When
        ``False`` (``--write``), apply changes atomically and validate.

    Returns
    -------
    tuple[list[ReconcileDiff], list[str], list[str]]
        ``(diffs, orphaned_completed, runs_without_ref)``
        * ``diffs`` — list of proposed/applied changes.
        * ``orphaned_completed`` — backlog refs marked ``completed`` with no
          matching run dir found.
        * ``runs_without_ref`` — run ids that have no ``backlog_idea_ref``.
    """
    backlog_file = _backlog_path(paths)
    if not backlog_file.exists():
        return [], [], []

    doc: dict[str, Any] = load_yaml(backlog_file)
    ideas: list[Any] = doc.get("ideas") or []

    # Build ref → list index map (we need to patch by index for atomic write).
    ref_to_idx: dict[str, int] = {}
    for i, idea in enumerate(ideas):
        if isinstance(idea, dict) and idea.get("ref"):
            ref_to_idx[str(idea["ref"])] = i

    # Scan all runs/rf_run_*/run.yaml for backlog_idea_ref.
    runs_dir = paths.runs
    ref_to_run: dict[str, dict[str, Any]] = {}   # ref -> run data
    ref_to_run_yaml_path: dict[str, Path] = {}    # ref -> path of run.yaml
    runs_without_ref: list[str] = []

    if runs_dir.exists():
        for run_dir in sorted(runs_dir.iterdir()):
            if not run_dir.is_dir():
                continue
            run_yaml = run_dir / "run.yaml"
            if not run_yaml.exists():
                continue
            run_data: dict[str, Any] = load_yaml(run_yaml) or {}
            ref = run_data.get("backlog_idea_ref")
            if not ref:
                runs_without_ref.append(run_dir.name)
                continue
            ref_str = str(ref)
            # If multiple runs map to the same ref, keep the "most complete" one.
            if ref_str in ref_to_run:
                existing_status = _infer_run_status(
                    ref_to_run_yaml_path[ref_str], ref_to_run[ref_str]
                )
                new_status = _infer_run_status(run_yaml, run_data)
                if _status_rank(new_status) > _status_rank(existing_status):
                    ref_to_run[ref_str] = run_data
                    ref_to_run_yaml_path[ref_str] = run_yaml
            else:
                ref_to_run[ref_str] = run_data
                ref_to_run_yaml_path[ref_str] = run_yaml

    # Compute diffs.
    diffs: list[ReconcileDiff] = []
    orphaned_completed: list[str] = []

    for ref, idx in ref_to_idx.items():
        idea = ideas[idx]
        if not isinstance(idea, dict):
            continue

        current_status = idea.get("status")

        # TERMINAL guard: archived ideas are intentionally abandoned — never touch them.
        if current_status == "archived":
            continue

        if ref not in ref_to_run:
            # No matching run — check for inverse drift.
            if current_status == "completed":
                orphaned_completed.append(ref)
            continue

        run_data = ref_to_run[ref]
        run_yaml_path = ref_to_run_yaml_path[ref]
        desired_status = _infer_run_status(run_yaml_path, run_data)

        # Advance status only forward.
        if _status_rank(desired_status) > _status_rank(current_status):
            diffs.append(
                ReconcileDiff(ref=ref, field="status", old=current_status, new=desired_status)
            )

        # Fill links only when currently null/absent/empty-string.
        links_block: dict[str, Any] = idea.get("links") or {}

        _link_fields: list[tuple[str, str]] = [
            ("run_id", "run_id"),
            ("intent_id", "intent_id"),
            ("intenttree_node_id", "intenttree_node_id"),
        ]
        for link_key, run_key in _link_fields:
            current_val = links_block.get(link_key)
            if current_val not in (None, ""):
                # Non-null, non-empty — do not overwrite.
                continue
            new_val = run_data.get(run_key)
            if new_val:
                diffs.append(
                    ReconcileDiff(
                        ref=ref,
                        field=f"links.{link_key}",
                        old=current_val,
                        new=str(new_val),
                    )
                )

    if dry_run or not diffs:
        return diffs, orphaned_completed, runs_without_ref

    # --- apply changes atomically ---
    # Group diffs by ref for efficient patching.
    diffs_by_ref: dict[str, list[ReconcileDiff]] = {}
    for d in diffs:
        diffs_by_ref.setdefault(d.ref, []).append(d)

    for ref, ref_diffs in diffs_by_ref.items():
        idx = ref_to_idx[ref]
        idea = ideas[idx]
        for d in ref_diffs:
            if d.field == "status":
                idea["status"] = d.new
            elif d.field.startswith("links."):
                link_key = d.field[len("links."):]
                if "links" not in idea or idea["links"] is None:
                    idea["links"] = {}
                idea["links"][link_key] = d.new

    # Atomic write: temp file → os.replace.
    out_text = dumps_yaml(doc)
    fd, tmp_path = tempfile.mkstemp(
        dir=backlog_file.parent, prefix=".backlog_reconcile_", suffix=".yaml.tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(out_text)
        os.replace(tmp_path, backlog_file)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    # Post-write validation.
    from ..schemas import SchemaRegistry

    reg = SchemaRegistry(paths.schemas if paths.schemas.exists() else None)
    if reg.has("research_idea_backlog"):
        reloaded = load_yaml(backlog_file)
        result = reg.validate(reloaded, "research_idea_backlog")
        if not result.ok:
            raise ValueError(
                "Backlog failed schema validation after reconcile: "
                + "; ".join(result.errors[:5])
            )

    return diffs, orphaned_completed, runs_without_ref


__all__ = [
    "BacklogMetadata",
    "load_backlog_index",
    "lookup_metadata",
    "backlog_exists",
    "ReconcileDiff",
    "reconcile_backlog",
]
