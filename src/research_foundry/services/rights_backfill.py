"""Legacy ``rights_summary`` backfill (rights-entity-model-v1, P2-5).

``backfill_rights_summary`` writes an all-``"unknown"`` fail-closed
``rights_summary`` block (see ``schemas/source_card.schema.yaml`` /
``schemas/source_assertion.schema.yaml``) onto ``source_card``/
``source_assertion`` instances that predate the rights-substrate phase and
lack the field entirely. This is the migration mechanism the schemas'
own comments point to: a pre-existing instance missing ``rights_summary``
is not a *schema* validation failure (deliberate resilience), but it is
also not yet compliant with the fail-closed posture the field exists to
guarantee — this module closes that gap explicitly rather than leaving it
implicit.

Non-clobbering by construction
-------------------------------
This function only ever *adds* the field to an instance that has none. Any
instance already carrying a ``rights_summary`` — whether a real,
partially-populated mirror or the output of a prior backfill run — is left
byte-for-byte untouched. Re-running on an already-backfilled corpus is
therefore a no-op (idempotent), and this module can never overwrite real
rights data.

"Absent entirely" uses the exact same check as
``services.rights_validation.check_rights_divergence``'s ``needs_backfill``
(``metadata.get("rights_summary") is None`` — true for both a missing key
and an explicit ``rights_summary: null``), so a ``rf rights validate`` run
immediately after a backfill is guaranteed to report ``needs_backfill=False``
for every instance this function touched.

File conventions
-----------------
Same as ``services/rights_validation.py``: ``source_card`` instances are
Markdown files with YAML front matter (``research_foundry.frontmatter``);
``source_assertion`` instances are plain YAML files
(``research_foundry.yamlio``), auto-detected by file suffix.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from ..frontmatter import dump_md, load_md
from ..yamlio import dump_yaml, load_yaml

__all__ = [
    "ACTION_BACKFILLED",
    "ACTION_SKIPPED_PRESENT",
    "BackfillResult",
    "all_unknown_rights_summary",
    "backfill_rights_summary",
]

# Outcome labels for BackfillResult.action.
ACTION_BACKFILLED = "backfilled"
ACTION_SKIPPED_PRESENT = "skipped_present"


def all_unknown_rights_summary() -> dict[str, Any]:
    """A fresh, all-``"unknown"`` fail-closed ``rights_summary`` block.

    Byte-identical in shape to the ``rights_summary`` property shared by
    ``schemas/source_card.schema.yaml`` and
    ``schemas/source_assertion.schema.yaml`` (same block, mirrored on both —
    see ``tests/test_schema_validation.py``'s own
    ``_all_unknown_rights_summary()`` fixture helper, which this matches
    field-for-field). Returns a fresh dict (including fresh nested dict/list
    values) on every call — callers must not share or mutate a cached
    return value across instances.
    """

    return {
        "mirror_of_record_id": None,
        "mirror_derived_at": None,
        "mirror_is_authoritative": False,
        "rights_record_ids": [],
        "reuse_assessment_ids": [],
        "permission_record_ids": [],
        "copyright_status": "unknown",
        "access_basis": "unknown",
        "restrictions": {
            "incorporation_into_other_products": "unknown",
            "adaptation": "unknown",
            "commercial_use": "unknown",
            "redistribution": "unknown",
            "bulk_retrieval": "unknown",
            "model_training": "unknown",
        },
        "clearance_status": "UNKNOWN",
        "review_status": "unknown",
    }


@dataclass(frozen=True)
class BackfillResult:
    """Outcome of backfilling (or skipping) one instance file."""

    path: str
    instance_id: str | None
    action: str  # ACTION_BACKFILLED | ACTION_SKIPPED_PRESENT
    dry_run: bool

    def as_dict(self) -> dict[str, Any]:
        """JSON-safe representation (CLI ``--json`` output)."""

        return asdict(self)


def backfill_rights_summary(
    paths: Iterable[Path | str],
    *,
    dry_run: bool = False,
) -> list[BackfillResult]:
    """Backfill an all-``"unknown"`` ``rights_summary`` onto every path lacking one.

    Args:
        paths: ``source_card``/``source_assertion`` instance files to check
            (``.md`` front matter or plain ``.yaml``, auto-detected by
            suffix).
        dry_run: When ``True``, report what *would* change without writing
            anything.

    Returns:
        One :class:`BackfillResult` per input path, in input order.
    """

    return [_backfill_one(Path(p), dry_run=dry_run) for p in paths]


def _load_instance(path: Path) -> tuple[dict[str, Any], str | None]:
    """Load ``(metadata, body)``. ``body`` is ``None`` for plain-YAML instances."""

    if path.suffix.lower() == ".md":
        metadata, body = load_md(path)
        return metadata, body
    return (load_yaml(path) or {}), None


def _write_instance(path: Path, metadata: dict[str, Any], body: str | None) -> None:
    if path.suffix.lower() == ".md":
        dump_md(metadata, body or "", path)
    else:
        dump_yaml(metadata, path)


def _backfill_one(path: Path, *, dry_run: bool) -> BackfillResult:
    metadata, body = _load_instance(path)
    instance_id = metadata.get("source_card_id") or metadata.get("assertion_id")

    if metadata.get("rights_summary") is not None:
        # Already present (real data or a prior backfill) — never clobber.
        return BackfillResult(
            path=str(path), instance_id=instance_id, action=ACTION_SKIPPED_PRESENT, dry_run=dry_run
        )

    if not dry_run:
        metadata["rights_summary"] = all_unknown_rights_summary()
        _write_instance(path, metadata, body)

    return BackfillResult(path=str(path), instance_id=instance_id, action=ACTION_BACKFILLED, dry_run=dry_run)
