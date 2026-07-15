#!/usr/bin/env python3
"""Emit safe P8 assertion-ledger readiness receipts for a local workspace."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from research_foundry.config import FoundryConfig
from research_foundry.paths import FoundryPaths
from research_foundry.services.assertion_rollout import (
    backfill_dry_run,
    readiness_metrics,
    rollback_disable_rehearsal,
    write_readiness_receipt,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True, help="Local foundry workspace root")
    parser.add_argument("--write-receipts", action="store_true", help="Persist deterministic local readiness receipts")
    args = parser.parse_args()

    paths = FoundryPaths(root=args.root.resolve())
    config = FoundryConfig(paths=paths)
    receipts = [
        backfill_dry_run(paths=paths, config=config),
        rollback_disable_rehearsal(controls=config.assertion_ledger_controls()),
    ]
    result = {"metrics": readiness_metrics(paths=paths, config=config), "receipts": receipts}
    if args.write_receipts:
        result["receipt_paths"] = [str(write_readiness_receipt(paths=paths, receipt=receipt)) for receipt in receipts]
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
