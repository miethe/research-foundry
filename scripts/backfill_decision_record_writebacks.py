#!/usr/bin/env python3
"""Backfill decision_record writebacks over existing runs.

Re-renders ``runs/*/writebacks/decision_record_writeback.md`` for every run
whose claim ledger contains at least one ``status: inference`` claim. Runs
with zero inference claims are silently skipped (they would produce empty
records with no signal).

Usage examples::

    # Preview only — no writes (default)
    python scripts/backfill_decision_record_writebacks.py --dry-run

    # Apply to all eligible runs
    python scripts/backfill_decision_record_writebacks.py --write

    # Apply to a single run only
    python scripts/backfill_decision_record_writebacks.py --write --run-id rf_run_20260614_example

    # Use an explicit workspace root instead of auto-discovery
    python scripts/backfill_decision_record_writebacks.py --write --root /path/to/workspace

Risk rules (hard invariants):
- Default is ``--dry-run``; ``--write`` must be passed explicitly to write anything.
- Idempotent: re-running on an already-rendered run overwrites with the same content.
- Never touches ``runs/*/run.yaml``, the claim ledger, or any non-writeback artifact.
- Atomic write: dump_md (in frontmatter module) creates parent dirs then writes directly.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Backfill decision_record writebacks over runs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Preview which runs would receive a decision_record (default: True).",
    )
    p.add_argument(
        "--write",
        action="store_true",
        default=False,
        help="Actually write decision_record_writeback.md files (overrides --dry-run).",
    )
    p.add_argument(
        "--run-id",
        default=None,
        metavar="RUN_ID",
        help="Process only this specific run_id; default processes all runs.",
    )
    p.add_argument(
        "--root",
        default=None,
        metavar="PATH",
        help="Workspace root; auto-discovered from cwd if omitted.",
    )
    return p.parse_args()


def main() -> int:
    args = _parse_args()
    dry_run = not args.write  # --write overrides the default dry-run

    # Resolve workspace root before importing research_foundry (it reads foundry.yaml).
    if args.root:
        root = Path(args.root).resolve()
    else:
        root = None  # will be discovered

    # Import research_foundry from the installed (or editable) package.
    try:
        from research_foundry.ids import bundle_id as make_bundle_id
        from research_foundry.paths import FoundryPaths
        from research_foundry.services.writeback import (
            _inference_claims,
            _ledger,
            _load_bundle,
            _render_decision_record,
            _sensitivity,
        )
    except ImportError as exc:  # pragma: no cover
        print(f"ERROR: could not import research_foundry — {exc}", file=sys.stderr)
        print("Run with: PYTHONPATH=src python scripts/backfill_decision_record_writebacks.py", file=sys.stderr)
        return 1

    paths = FoundryPaths(root=root) if root else FoundryPaths.discover()

    runs_dir = paths.runs
    if not runs_dir.exists():
        print(f"No runs directory found at {runs_dir}", file=sys.stderr)
        return 1

    # Determine which run directories to process.
    if args.run_id:
        run_dirs = [runs_dir / args.run_id]
        if not run_dirs[0].exists():
            print(f"ERROR: run not found: {args.run_id} ({run_dirs[0]})", file=sys.stderr)
            return 1
    else:
        run_dirs = sorted(d for d in runs_dir.iterdir() if d.is_dir())

    if not run_dirs:
        print("No runs found.")
        return 0

    print(f"{'DRY-RUN' if dry_run else 'WRITE'} mode — scanning {len(run_dirs)} run(s) under {runs_dir}")
    print()

    would_write: list[str] = []
    skipped_no_inference: list[str] = []
    errors: list[tuple[str, str]] = []

    for run_dir in run_dirs:
        run_id = run_dir.name
        try:
            rp = paths.run_paths(run_id)
            ledger = _ledger(rp)

            inference = _inference_claims(ledger)
            if not inference:
                skipped_no_inference.append(run_id)
                continue

            # Resolve bundle_ident from the existing bundle (if any).
            bundle = _load_bundle(rp)
            bundle_ident = str(bundle.get("id") or make_bundle_id(run_id))
            sensitivity = _sensitivity(rp)
            requires_review = sensitivity in {"work_sensitive", "client_sensitive"}

            n_inference = len(inference)
            n_recs = sum(1 for c in inference if (c or {}).get("claim_type") == "recommendation")
            label = f"{run_id}: {n_inference} inference claim(s), {n_recs} recommendation(s)"

            if dry_run:
                would_write.append(label)
                print(f"  [would write] {label}")
            else:
                rp.ensure_scaffold()
                out = _render_decision_record(
                    rp,
                    paths,
                    bundle_ident=bundle_ident,
                    sensitivity=sensitivity,
                    ledger=ledger,
                    requires_review=requires_review,
                )
                if out:
                    print(f"  [written]     {label} → {out.relative_to(paths.root)}")
                    would_write.append(label)
                else:
                    # Should not happen (inference is non-empty), but guard anyway.
                    skipped_no_inference.append(run_id)
                    print(f"  [skipped]     {run_id} — renderer returned None unexpectedly")

        except Exception as exc:  # noqa: BLE001 — report but continue
            errors.append((run_id, str(exc)))
            print(f"  [ERROR]       {run_id} — {exc}", file=sys.stderr)

    print()
    print(f"Summary: {len(would_write)} eligible, {len(skipped_no_inference)} skipped (no inference), {len(errors)} error(s)")
    if dry_run and would_write:
        print("Re-run with --write to apply.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
