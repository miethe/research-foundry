#!/usr/bin/env python3
"""Backfill run metadata from the research idea backlog.

Inverts the ``backlog/research_idea_backlog.yaml`` ``links.run_id`` mapping to
write ``linked_projects``, ``category``, ``tags``, ``backlog_idea_ref``, and
``backlog_idea_id`` onto existing ``runs/*/run.yaml`` files, then re-derives
``registries/run_index.yaml`` from the updated run.yaml files.

Usage examples::

    # Preview only — no writes
    python scripts/backfill_run_metadata.py --dry-run

    # Apply to all runs with backlog links
    python scripts/backfill_run_metadata.py

    # Apply to a single run only
    python scripts/backfill_run_metadata.py --run-id rf_run_20260614_claim_segmentation_and_claim_to_source

    # Back up originals before writing
    python scripts/backfill_run_metadata.py --backup

    # Restore from backups
    python scripts/backfill_run_metadata.py --restore

    # Force-overwrite already-set fields
    python scripts/backfill_run_metadata.py --force

Risk rules (hard invariants):
- Join key = backlog ``links.run_id``; NEVER fuzzy title match.
- Idempotent: re-run on an already-enriched run produces zero writes.
- Single writer: write ``run.yaml`` then DERIVE ``run_index.yaml`` from it.
- Atomic write: write to ``<file>.tmp`` then rename.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# YAML I/O (self-contained; does not import research_foundry to stay usable
# as a standalone script even before the package is installed)
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(UTC).astimezone().isoformat(timespec="seconds")


def _load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _dump_yaml(obj: Any) -> str:
    """Serialize with insertion-order and readable style (matches yamlio.py)."""
    return yaml.dump(
        obj,
        Dumper=yaml.SafeDumper,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )


def _write_atomic(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` atomically (tmp → rename, same dir)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ---------------------------------------------------------------------------
# Backlog inversion (MIG-001)
# ---------------------------------------------------------------------------


def build_inversion_map(backlog_path: Path) -> dict[str, dict[str, Any]]:
    """Read backlog YAML; return ``{run_id: metadata_dict}`` for all ideas
    that have ``links.run_id`` set.

    When multiple ideas share the same run_id, metadata is merged:
    - ``linked_projects``: union of ``suggested_project`` values (de-duped, order-stable)
    - ``tags``: union of ``tags`` lists (de-duped, order-stable)
    - ``category``: first non-null ``pillar`` wins (multiple ideas rarely disagree)
    - ``backlog_idea_ref``: first idea's ``ref`` field (e.g. ``RIB-001``); ``None`` when
      the idea has no ``ref`` field.  Must match ``^RIB-\\d+$`` per the JSON schema.
    - ``backlog_idea_id``: first idea's ``id`` slug (e.g. ``idea_claim-...``); retained
      as a stable human-readable identifier separate from the ref.
    """
    data = _load_yaml(backlog_path)
    ideas: list[dict[str, Any]] = data.get("ideas", [])

    inv: dict[str, dict[str, Any]] = {}
    for idea in ideas:
        links: dict[str, Any] = idea.get("links") or {}
        run_id = links.get("run_id")
        if not run_id:
            continue

        idea_id: str = idea.get("id", "")
        # ``ref`` is the RIB-NNN backlog reference slug required by the run.yaml
        # JSON schema (pattern ^RIB-\d+$).  Gracefully handle ideas that lack a ref.
        idea_ref: str | None = idea.get("ref") or None
        pillar: str | None = idea.get("pillar") or None
        tags: list[str] = idea.get("tags") or []
        suggested_project: str | None = idea.get("suggested_project") or None

        if run_id not in inv:
            inv[run_id] = {
                "linked_projects": ([suggested_project] if suggested_project else []),
                "category": pillar,
                "tags": list(tags),
                "backlog_idea_ref": idea_ref,
                "backlog_idea_id": idea_id,
            }
        else:
            # Merge: union (preserving insertion order via dict-keyed de-dup)
            existing = inv[run_id]
            if suggested_project and suggested_project not in existing["linked_projects"]:
                existing["linked_projects"].append(suggested_project)
            for tag in tags:
                if tag not in existing["tags"]:
                    existing["tags"].append(tag)
            if existing["category"] is None and pillar:
                existing["category"] = pillar

    return inv


# ---------------------------------------------------------------------------
# Per-run patching (MIG-002)
# ---------------------------------------------------------------------------


def _diff_lines(run_id: str, before: dict, after: dict) -> list[str]:
    """Return human-readable diff lines for changed fields."""
    lines: list[str] = []
    for key in ("linked_projects", "category", "tags", "backlog_idea_ref", "backlog_idea_id"):
        b_val = before.get(key)
        a_val = after.get(key)
        if b_val != a_val:
            lines.append(f"  [{run_id}] {key}: {b_val!r} -> {a_val!r}")
    return lines


def patch_run_yaml(
    run_yaml: Path,
    metadata: dict[str, Any],
    *,
    dry_run: bool,
    force: bool,
    backup: bool,
) -> list[str]:
    """Apply metadata fields to ``run.yaml``.

    Returns a list of diff-line strings (empty if no changes needed).
    Writes only if ``not dry_run`` and there are actual changes (or ``force``).
    """
    run_data: dict[str, Any] = _load_yaml(run_yaml) or {}
    before = {k: run_data.get(k) for k in
               ("linked_projects", "category", "tags", "backlog_idea_ref", "backlog_idea_id")}

    changed_fields: dict[str, Any] = {}
    for key, new_val in metadata.items():
        current = run_data.get(key)
        # "Already set" means: field is present AND has a non-null, non-empty value.
        # Treat None, [], and "" as "not yet enriched" (write through without --force).
        # This handles P1-stub runs that have empty-list placeholders.
        already_set = current is not None and current != [] and current != ""
        if not already_set or force:
            changed_fields[key] = new_val

    diff = _diff_lines(run_data.get("run_id", run_yaml.parent.name), before,
                       {**before, **changed_fields})
    if not diff:
        return []  # idempotent — nothing to do

    if dry_run:
        return diff

    # Perform actual write
    if backup:
        bak = run_yaml.with_suffix(".yaml.bak")
        shutil.copy2(run_yaml, bak)

    updated = {**run_data, **changed_fields}
    _write_atomic(run_yaml, _dump_yaml(updated))
    return diff


# ---------------------------------------------------------------------------
# run_index.yaml re-derivation (MIG-003)
# ---------------------------------------------------------------------------


def _metadata_fields_for_run(run_yaml: Path) -> dict[str, Any]:
    """Read metadata fields from a run.yaml (returns empty dict on any error)."""
    try:
        data: dict[str, Any] = _load_yaml(run_yaml) or {}
    except Exception:
        return {}
    return {
        k: data[k]
        for k in ("linked_projects", "category", "tags", "backlog_idea_ref", "backlog_idea_id")
        if k in data
    }


def update_run_index(
    index_path: Path,
    runs_root: Path,
    updated_run_ids: set[str],
    *,
    dry_run: bool,
) -> list[str]:
    """Re-derive ``run_index.yaml`` entries for ``updated_run_ids`` from their
    ``run.yaml`` sources.

    Returns diff lines (empty if no changes). In ``dry_run`` mode, returns what
    *would* change without writing.
    """
    if not index_path.exists():
        return []

    index_data: dict[str, Any] = _load_yaml(index_path) or {}
    items: list[dict[str, Any]] = index_data.get("items", [])

    METADATA_KEYS = ("linked_projects", "category", "tags", "backlog_idea_ref", "backlog_idea_id")
    diff_lines: list[str] = []
    changed = False

    for item in items:
        item_id: str = item.get("id", "")
        if item_id not in updated_run_ids:
            continue
        run_yaml = runs_root / item_id / "run.yaml"
        if not run_yaml.exists():
            continue
        new_fields = _metadata_fields_for_run(run_yaml)
        for key in METADATA_KEYS:
            old_val = item.get(key)
            new_val = new_fields.get(key)
            # Only update if the new value is meaningful (non-null, non-empty)
            if new_val is None or new_val == [] or new_val == "":
                continue
            if old_val != new_val:
                diff_lines.append(
                    f"  [run_index] {item_id}.{key}: {old_val!r} -> {new_val!r}"
                )
                if not dry_run:
                    item[key] = new_val
                    changed = True

    if not dry_run and changed:
        index_data["items"] = items
        index_data["count"] = len(items)
        index_data["updated_at"] = _now_iso()
        _write_atomic(index_path, _dump_yaml(index_data))

    return diff_lines


# ---------------------------------------------------------------------------
# Backup / restore (MIG-004)
# ---------------------------------------------------------------------------


def restore_backups(runs_root: Path, run_id: str | None) -> None:
    """Restore ``run.yaml.bak`` → ``run.yaml`` for the given run (or all)."""
    targets: list[Path] = []
    if run_id:
        bak = runs_root / run_id / "run.yaml.bak"
        if bak.exists():
            targets.append(bak)
        else:
            print(f"[WARN] No backup found: {bak}", file=sys.stderr)
    else:
        targets = list(runs_root.rglob("run.yaml.bak"))

    for bak in targets:
        dest = bak.with_suffix("")  # removes .bak → run.yaml
        shutil.copy2(bak, dest)
        print(f"Restored {bak} -> {dest}")


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def _print_summary(dry_run: bool, backfilled: int, skipped: int, diff_all: list[str]) -> None:
    mode = "[DRY-RUN]" if dry_run else "[APPLIED]"
    print(f"\n{mode} Backfill complete.")
    print(f"  Runs backfilled : {backfilled}")
    print(f"  Runs skipped    : {skipped}  (no link or already up-to-date)")
    if diff_all:
        print(f"  Field changes   : {len(diff_all)}")
        print("\nDiff:")
        for line in diff_all:
            print(line)
    else:
        print("  No field changes (all runs already enriched).")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "Backfill run metadata (linked_projects, category, tags, backlog_idea_ref, "
            "backlog_idea_id) onto existing runs/*/run.yaml by inverting "
            "backlog/research_idea_backlog.yaml links.run_id mapping, "
            "then re-derive registries/run_index.yaml."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview all changes (no writes):
  python scripts/backfill_run_metadata.py --dry-run

  # Apply and back up originals first:
  python scripts/backfill_run_metadata.py --backup

  # Limit to one run:
  python scripts/backfill_run_metadata.py --run-id rf_run_20260614_claim_segmentation_and_claim_to_source

  # Force overwrite already-set fields:
  python scripts/backfill_run_metadata.py --force

  # Restore from backups (undo):
  python scripts/backfill_run_metadata.py --restore
        """,
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print diff only; do not write any files. DEFAULT for preview.",
    )
    p.add_argument(
        "--run-id",
        metavar="RUN_ID",
        default=None,
        help="Limit backfill to a single run directory (e.g. rf_run_20260614_...).",
    )
    p.add_argument(
        "--force",
        action="store_true",
        default=False,
        help=(
            "Overwrite fields that are already set. Default: skip already-set fields "
            "(idempotent behaviour)."
        ),
    )
    p.add_argument(
        "--backup",
        action="store_true",
        default=False,
        help=(
            "Back up run.yaml to run.yaml.bak before overwriting. "
            "Use --restore to undo."
        ),
    )
    p.add_argument(
        "--restore",
        action="store_true",
        default=False,
        help=(
            "Restore run.yaml from run.yaml.bak (rollback). "
            "When combined with --run-id, restores only that run."
        ),
    )
    p.add_argument(
        "--backlog",
        metavar="PATH",
        default=None,
        help=(
            "Path to research_idea_backlog.yaml "
            "(default: auto-detected from workspace root)."
        ),
    )
    p.add_argument(
        "--root",
        metavar="DIR",
        default=None,
        help="Workspace root (default: auto-detected via foundry.yaml marker).",
    )
    return p.parse_args(argv)


def _find_workspace_root(start: Path) -> Path:
    """Walk up from ``start`` to find foundry.yaml marker."""
    for d in [start, *start.parents]:
        if (d / "foundry.yaml").exists():
            return d
        if (d / ".git").exists():
            return d
    return start


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # --- Resolve workspace root ---
    root = Path(args.root).resolve() if args.root else _find_workspace_root(Path.cwd())
    runs_root = root / "runs"
    index_path = root / "registries" / "run_index.yaml"
    backlog_path = Path(args.backlog).resolve() if args.backlog else root / "backlog" / "research_idea_backlog.yaml"

    if not backlog_path.exists():
        print(f"[ERROR] Backlog not found: {backlog_path}", file=sys.stderr)
        return 1

    # --- Restore mode ---
    if args.restore:
        restore_backups(runs_root, args.run_id)
        return 0

    # --- Build inversion map ---
    inv_map = build_inversion_map(backlog_path)
    if not inv_map:
        print("[WARN] No ideas with links.run_id found in backlog.", file=sys.stderr)
        return 0

    # --- Determine target runs ---
    if args.run_id:
        targets = [args.run_id] if args.run_id in inv_map else []
        if not targets:
            print(
                f"[WARN] run_id {args.run_id!r} has no backlog link; nothing to backfill.",
                file=sys.stderr,
            )
            return 0
    else:
        targets = list(inv_map.keys())

    # --- Backfill each run ---
    all_diffs: list[str] = []
    backfilled = 0
    skipped = 0
    updated_run_ids: set[str] = set()

    for run_id in sorted(targets):
        run_yaml = runs_root / run_id / "run.yaml"
        if not run_yaml.exists():
            print(f"[WARN] run.yaml not found: {run_yaml}", file=sys.stderr)
            skipped += 1
            continue

        diffs = patch_run_yaml(
            run_yaml,
            inv_map[run_id],
            dry_run=args.dry_run,
            force=args.force,
            backup=args.backup,
        )
        if diffs:
            all_diffs.extend(diffs)
            backfilled += 1
            updated_run_ids.add(run_id)
        else:
            skipped += 1

    # --- Update run_index.yaml ---
    index_diffs: list[str] = []
    if updated_run_ids and index_path.exists():
        index_diffs = update_run_index(
            index_path,
            runs_root,
            updated_run_ids,
            dry_run=args.dry_run,
        )
        all_diffs.extend(index_diffs)

    _print_summary(args.dry_run, backfilled, skipped, all_diffs)
    return 0


if __name__ == "__main__":
    sys.exit(main())
