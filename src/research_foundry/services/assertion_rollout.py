"""Repository-local readiness helpers for the reusable assertion ledger.

These helpers deliberately do not enable a capability, materialize an
assertion, contact an external system, or inspect source text.  They provide
deterministic dry-run, disable/rollback rehearsal, and aggregate health
evidence for an operator who has separately obtained private-rollout authority.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..config import AssertionLedgerControls, FoundryConfig
from ..paths import FoundryPaths

_RECEIPT_SCHEMA_VERSION = "1.0"
_RECEIPT_ID_RE = re.compile(r"^ral_(?:backfill_dry_run|rollback_disable)_[a-f0-9]{16}$")


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _receipt_id(kind: str, payload: Mapping[str, Any]) -> str:
    return f"ral_{kind}_{sha256(_canonical_json(payload).encode()).hexdigest()[:16]}"


def _count_files(root: Path, pattern: str) -> int:
    return sum(1 for path in root.glob(pattern) if path.is_file()) if root.exists() else 0


def readiness_metrics(*, paths: FoundryPaths, config: FoundryConfig | None = None) -> dict[str, Any]:
    """Return aggregate health/economics-safe metrics without source content.

    The result intentionally contains only booleans and aggregate counts.  It
    omits assertion IDs, workspace names, passages, source text, locators, and
    customer/private metadata so it can be attached to an operator receipt.
    """

    controls = (config or FoundryConfig(paths=paths)).assertion_ledger_controls()
    ledger_root = paths.root / "assertion_ledger" / "workspaces"
    return {
        "schema_version": _RECEIPT_SCHEMA_VERSION,
        "metric_scope": "aggregate_no_sensitive_text",
        "controls": {
            "ledger_write_enabled": controls.ledger_write_enabled,
            "automated_reuse_enabled": controls.automated_reuse_enabled,
            "canonical_claims_enabled": controls.canonical_claims_enabled,
        },
        "counts": {
            "run_directories": sum(1 for path in paths.runs.iterdir() if path.is_dir()) if paths.runs.exists() else 0,
            "claim_ledgers": _count_files(paths.runs, "*/claims/claim_ledger.yaml"),
            "assertion_records": _count_files(ledger_root, "*/assertions/*.yaml"),
            "materialization_generations": _count_files(
                ledger_root, "*/materializations/*/generations/*.yaml"
            ),
            "impact_receipts": _count_files(ledger_root, "*/impact_operations/*.yaml"),
        },
        "economics": {
            "automated_reuse_actions": 0,
            "external_writeback_actions": 0,
            "public_promotion_actions": 0,
        },
    }


def backfill_dry_run(*, paths: FoundryPaths, config: FoundryConfig | None = None) -> dict[str, Any]:
    """Build an idempotent, no-write backfill rehearsal receipt.

    It counts run-local claim ledgers that could be considered by a separately
    authorized operator.  It does not materialize data, expose run IDs, or
    require the ledger-write flag to be enabled.
    """

    metrics = readiness_metrics(paths=paths, config=config)
    payload = {
        "operation": "assertion_ledger_backfill_dry_run",
        "mode": "dry_run",
        "candidate_claim_ledgers": metrics["counts"]["claim_ledgers"],
        "existing_assertion_records": metrics["counts"]["assertion_records"],
        "ledger_write_enabled": metrics["controls"]["ledger_write_enabled"],
        "authoritative_data_mutated": False,
        "external_writeback_executed": False,
    }
    return {
        "schema_version": _RECEIPT_SCHEMA_VERSION,
        "receipt_id": _receipt_id("backfill_dry_run", payload),
        **payload,
    }


def rollback_disable_rehearsal(
    *,
    controls: AssertionLedgerControls,
) -> dict[str, Any]:
    """Return a deterministic receipt proving the safe disabled target state.

    This is a rehearsal record, not a configuration mutator.  Operators change
    ``foundry.assertion_ledger`` through reviewed configuration management;
    keeping the function non-mutating prevents a health check from enabling or
    disabling a real private deployment as a side effect.
    """

    payload = {
        "operation": "assertion_ledger_rollback_disable_rehearsal",
        "prior_controls": {
            "ledger_write_enabled": controls.ledger_write_enabled,
            "automated_reuse_enabled": controls.automated_reuse_enabled,
            "canonical_claims_enabled": controls.canonical_claims_enabled,
        },
        "target_controls": {
            "ledger_write_enabled": False,
            "automated_reuse_enabled": False,
            "canonical_claims_enabled": False,
        },
        "preserves_authoritative_ledger_records": True,
        "external_writeback_executed": False,
    }
    return {
        "schema_version": _RECEIPT_SCHEMA_VERSION,
        "receipt_id": _receipt_id("rollback_disable", payload),
        "mode": "rehearsal",
        **payload,
    }


def _readiness_receipt_path(*, paths: FoundryPaths, receipt_id: str) -> Path:
    """Return a confined receipt path for a canonical generated receipt ID."""

    if _RECEIPT_ID_RE.fullmatch(receipt_id) is None:
        raise ValueError("readiness receipt requires a canonical deterministic receipt_id")
    directory = paths.rf_state / "assertion_ledger" / "readiness"
    directory.mkdir(parents=True, exist_ok=True)
    resolved_directory = directory.resolve()
    path = (resolved_directory / f"{receipt_id}.json").resolve()
    try:
        path.relative_to(resolved_directory)
    except ValueError as exc:  # pragma: no cover - defense in depth after ID validation
        raise ValueError("readiness receipt path escapes the readiness directory") from exc
    return path


def write_readiness_receipt(*, paths: FoundryPaths, receipt: Mapping[str, Any]) -> Path:
    """Persist one deterministic readiness receipt under durable local state."""

    receipt_id = receipt.get("receipt_id")
    if not isinstance(receipt_id, str):
        raise ValueError("readiness receipt requires a canonical deterministic receipt_id")
    path = _readiness_receipt_path(paths=paths, receipt_id=receipt_id)
    encoded = json.dumps(dict(receipt), indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(path)
    return path


__all__ = [
    "backfill_dry_run",
    "readiness_metrics",
    "rollback_disable_rehearsal",
    "write_readiness_receipt",
]
