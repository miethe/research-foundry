"""Backfill for the write-time term/usage-role index (`_term_index`, P3).

``backfill_term_index`` re-runs the exact deterministic extraction the
write path uses (``services.term_index.build_term_index`` /
``index_pediatric_cds_thresholds``, wired at write time by
``services.claim_mapping.build_claim_ledger``) against pre-existing
``claims/claim_ledger.yaml`` files, and attaches `_term_index` to any claim
that lacks one. Modeled directly on ``services/rights_backfill.py``: same
dry-run-by-default posture, same non-clobbering-by-construction guarantee.

Non-clobbering by construction
-------------------------------
This function only ever *adds* the `_term_index` key to a claim that has
none. Any claim already carrying a `_term_index` -- whether written by the
live P1 write path or a prior backfill run -- is left byte-for-byte
untouched. Re-running on an already-backfilled ledger is therefore a no-op
(idempotent), and this module can never touch ``verification_status``,
``status``, or any other already-attested field (FR-14): the only key ever
assigned is ``claim["_term_index"]``, and a ledger with zero eligible claims
is never re-written at all.

"Absent entirely" uses the exact same check as
``services/rights_backfill.py``'s own convention
(``claim.get("_term_index") is None`` -- true for both a missing key and an
explicit ``_term_index: null``).

Fail-closed vocabulary handling
--------------------------------
A missing vocabulary file (``load_vocabulary`` returns ``None`` with a
logged warning) is not an error -- every eligible claim is reported
``ACTION_SKIPPED_NO_VOCABULARY`` and nothing is written, matching the write
path's own OQ-D resilience contract. A malformed vocabulary file raises
``VocabularyError`` (``load_vocabulary``'s own fail-closed contract) and is
left to propagate -- this module never catches it, silences it, or
substitutes a default.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from ..paths import FoundryPaths
from ..yamlio import dump_yaml, load_yaml
from .term_index import build_term_index, index_pediatric_cds_thresholds, load_vocabulary

__all__ = [
    "ACTION_BACKFILLED",
    "ACTION_SKIPPED_NO_MATCH",
    "ACTION_SKIPPED_NO_VOCABULARY",
    "ACTION_SKIPPED_PRESENT",
    "BackfillResult",
    "backfill_term_index",
]

# Outcome labels for BackfillResult.action.
ACTION_BACKFILLED = "backfilled"
ACTION_SKIPPED_PRESENT = "skipped_present"
ACTION_SKIPPED_NO_MATCH = "skipped_no_match"
ACTION_SKIPPED_NO_VOCABULARY = "skipped_no_vocabulary"


@dataclass(frozen=True)
class BackfillResult:
    """Outcome of backfilling (or skipping) one claim in one claim ledger."""

    path: str
    claim_id: str | None
    action: str
    dry_run: bool

    def as_dict(self) -> dict[str, Any]:
        """JSON-safe representation (CLI ``--json`` output)."""

        return asdict(self)


def backfill_term_index(
    ledger_paths: Iterable[Path | str],
    *,
    dry_run: bool = True,
    paths: FoundryPaths | None = None,
) -> list[BackfillResult]:
    """Backfill `_term_index` onto every claim lacking one across *ledger_paths*.

    Args:
        ledger_paths: ``claims/claim_ledger.yaml`` files to check.
        dry_run: When ``True`` (the default), report what *would* change
            without writing anything.
        paths: Workspace paths, for vocabulary resolution
            (``FoundryPaths.discover()`` if omitted).

    Returns:
        One :class:`BackfillResult` per claim across all input ledgers, in
        input order (ledger order, then claim order within each ledger).

    Raises:
        term_index.VocabularyError: the vocabulary file exists but is
            malformed. Propagates unmodified -- fail closed, never
            substitutes a default vocabulary.
    """

    paths = paths or FoundryPaths.discover()
    vocabulary = load_vocabulary(paths=paths)

    results: list[BackfillResult] = []
    for raw_path in ledger_paths:
        results.extend(_backfill_ledger(Path(raw_path), vocabulary, dry_run=dry_run))
    return results


def _sources_dir_for_ledger(ledger_path: Path) -> Path:
    """``<run>/claims/claim_ledger.yaml`` -> ``<run>/sources`` (spec §5)."""

    return ledger_path.parent.parent / "sources"


def _backfill_ledger(
    ledger_path: Path,
    vocabulary: dict[str, Any] | None,
    *,
    dry_run: bool,
) -> list[BackfillResult]:
    if not ledger_path.exists():
        return []

    ledger = load_yaml(ledger_path)
    claims = ledger.get("claims") if isinstance(ledger, dict) else None
    if not isinstance(claims, list):
        return []

    pediatric_cds_thresholds = (
        index_pediatric_cds_thresholds(_sources_dir_for_ledger(ledger_path)) if vocabulary else {}
    )

    results: list[BackfillResult] = []
    changed = False

    for claim in claims:
        if not isinstance(claim, dict):
            continue
        claim_id = claim.get("claim_id")

        if claim.get("_term_index") is not None:
            # Already present (live write path or a prior backfill) -- never clobber.
            results.append(
                BackfillResult(str(ledger_path), claim_id, ACTION_SKIPPED_PRESENT, dry_run)
            )
            continue

        if vocabulary is None:
            results.append(
                BackfillResult(str(ledger_path), claim_id, ACTION_SKIPPED_NO_VOCABULARY, dry_run)
            )
            continue

        text = str(claim.get("text") or "")
        sources = claim.get("sources")
        first_source = sources[0] if isinstance(sources, list) and sources else {}
        if not isinstance(first_source, dict):
            first_source = {}
        threshold_key = (
            str(first_source.get("source_card_id") or ""),
            str(first_source.get("evidence_id") or ""),
        )

        term_index = build_term_index(
            text,
            vocabulary,
            pediatric_cds_threshold=pediatric_cds_thresholds.get(threshold_key, False),
        )
        if term_index is None:
            # Zero vocabulary hits -- AC-1 resilience: stay absent, never an
            # empty-but-present block.
            results.append(
                BackfillResult(str(ledger_path), claim_id, ACTION_SKIPPED_NO_MATCH, dry_run)
            )
            continue

        if not dry_run:
            claim["_term_index"] = term_index
            changed = True
        results.append(BackfillResult(str(ledger_path), claim_id, ACTION_BACKFILLED, dry_run))

    if changed:
        dump_yaml(ledger, ledger_path)

    return results
