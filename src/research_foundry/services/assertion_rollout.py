"""Repository-local readiness helpers for the reusable assertion ledger.

These helpers deliberately do not enable a capability, materialize an
assertion, contact an external system, or inspect source text.  They provide
deterministic dry-run, disable/rollback rehearsal, and aggregate health
evidence for an operator who has separately obtained private-rollout authority.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
from typing import Any

from ..config import AssertionLedgerControls, FoundryConfig
from ..frontmatter import load_md
from ..paths import FoundryPaths
from ..yamlio import dumps_yaml, load_yaml
from . import claim_mapping
from .assertion_materialization import AbstainedClaim, AssertionMaterializer
from .assertion_registry import AssertionRegistry, RegistryIntegrityError
from .assertion_workspace import resolve_or_deny

_RECEIPT_SCHEMA_VERSION = "1.0"
_RECEIPT_ID_RE = re.compile(r"^ral_(?:backfill_dry_run|rollback_disable)_[a-f0-9]{16}$")
_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")

#: P2-06 (SPIKE RQ2): only these two abstention codes describe "no exact
#: passage bound" -- the narrow surface the fuzzy-recovery add-on targets.
#: Deferred-reference, non-source-claim, and integrity-rejection codes are
#: deliberately excluded: a fuzzy match can never make those eligible, and
#: flagging them spot-check-pending would misrepresent why the fact abstained.
_FUZZY_RECOVERY_ELIGIBLE_CODES = frozenset({"missing_exact_passage_quote", "unresolved_passage_binding"})
#: SPIKE RQ2's own manual inspection of the 0.90-0.999 band found real
#: paraphrase drift even at the top of that range (a tense-changed sentence at
#: 0.992); 0.9 is the floor, not a soft target, and this add-on never lowers
#: it. Below 0.9 (e.g. 0.8), a candidate is rejected outright.
_FUZZY_RECOVERY_THRESHOLD = 0.9


class BackfillConflict(ValueError):
    """A persisted backfill receipt conflicts with a freshly computed one."""


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


# ---------------------------------------------------------------------------
# P2-02: write-path backfill driver (per docs/project_plans/design-specs/
# assertion-ledger-backfill-mapping-strategy.md and the parent phase file's
# "Post-Fix Re-Measurement" section).
# ---------------------------------------------------------------------------


def _dedup_quotes(points: Sequence[Any]) -> list[str]:
    """Return each evidence point's distinct verbatim quote, in card order.

    Mirrors ``source_cards.py::ingest_source``'s own dedup-by-normalized-
    whitespace rule (P1.5's ``passages=`` wiring), so a backfilled edition's
    passages are constructed identically to a forward-path ingestion of the
    same source card -- no divergent backfill-only passage-selection rule.
    """

    seen: set[str] = set()
    quotes: list[str] = []
    for point in points:
        if not isinstance(point, Mapping):
            continue
        quote = point.get("quote")
        if isinstance(quote, str) and quote:
            normalized = " ".join(quote.split())
            if normalized not in seen:
                seen.add(normalized)
                quotes.append(quote)
    return quotes


def _load_source_card(paths: FoundryPaths, run_id: str, source_card_id: str) -> dict[str, Any] | None:
    """Read one run-local source card's front matter, or ``None`` if unusable."""

    path = paths.run_paths(run_id).sources / f"{source_card_id}.md"
    if not path.is_file():
        return None
    try:
        metadata, _body = load_md(path)
    except Exception:  # noqa: BLE001 - an unreadable historical card is skipped, not fatal
        return None
    if not isinstance(metadata, dict) or metadata.get("source_card_id") != source_card_id:
        return None
    return metadata


def _ingest_run_source_cards(
    run_id: str, *, registry: AssertionRegistry, paths: FoundryPaths
) -> dict[str, int]:
    """Reconstruct one run's editions/passages from its persisted source cards.

    No raw fetched document is cached anywhere in this workspace for a
    historical run (SPIKE RQ4); the only verbatim substrate that has ever
    existed is each evidence point's own ``quote`` field. Per the SPIKE's
    post-fix re-measurement methodology, an edition's reconstructed content is
    the join of its source card's deduped verbatim quotes, segmented into
    passages via the same ``passages=`` wiring P1.5 already uses on the
    forward path -- not a divergent backfill-only write path (P2-03's seam
    check). A card with zero verbatim quotes contributes nothing (every fact
    bound to it can only abstain ``missing_exact_passage_quote`` downstream,
    which is correct, not an error).

    Deliberately calls :meth:`AssertionRegistry.ingest` directly rather than
    ``source_cards.ingest_source()``: that function mints a *new*
    deterministic ``source_card_id`` and regenerates brand-new
    ``extracted_points``, which would silently overwrite the historical,
    LLM-authored points a run's claim mappings already reference by
    ``evidence_id``/``locator`` (SPIKE "Dead ends" section) -- reproducing the
    registry-write block against the *existing* historical card is the
    faithful backfill.
    """

    run_paths = paths.run_paths(run_id)
    counts = {"created": 0, "reused": 0, "skipped_no_quotes": 0, "not_reusable": 0}
    if not run_paths.sources.exists():
        return counts
    for card_path in sorted(run_paths.sources.glob("*.md")):
        source_card_id = card_path.stem
        metadata = _load_source_card(paths, run_id, source_card_id)
        if metadata is None:
            counts["not_reusable"] += 1
            continue
        points = metadata.get("extracted_points")
        quotes = _dedup_quotes(points) if isinstance(points, list) else []
        if not quotes:
            counts["skipped_no_quotes"] += 1
            continue
        usage = metadata.get("usage")
        sensitivity = metadata.get("sensitivity")
        source = metadata.get("source") if isinstance(metadata.get("source"), Mapping) else {}
        locator = source.get("locator") if isinstance(source, Mapping) else None
        if not isinstance(usage, Mapping) or not usage or not isinstance(sensitivity, str) or not sensitivity:
            counts["not_reusable"] += 1
            continue
        try:
            snapshot = registry.source_card_snapshot(source_card_id, metadata)
        except RegistryIntegrityError:
            counts["not_reusable"] += 1
            continue
        content = "\n\n".join(quotes)
        result = registry.ingest(
            source_card_id,
            content,
            media_type="text/plain",
            access_scope=sensitivity,
            allowed_use=dict(usage),
            retrieval_locator=dict(locator) if isinstance(locator, Mapping) else {},
            passages=quotes,
            source_card_snapshot=snapshot,
        )
        if not result.reusable:
            counts["not_reusable"] += 1
        elif result.created:
            counts["created"] += 1
        else:
            counts["reused"] += 1
    return counts


def _fuzzy_ratio(left: str, right: str) -> float:
    """A whitespace-normalized, case-folded ``difflib`` similarity ratio."""

    normalized_left = " ".join(left.split()).casefold()
    normalized_right = " ".join(right.split()).casefold()
    if not normalized_left or not normalized_right:
        return 0.0
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def _fuzzy_recovery_candidates(
    run_id: str,
    abstained_claims: Sequence[AbstainedClaim],
    *,
    paths: FoundryPaths,
) -> tuple[dict[str, Any], ...]:
    """P2-06: flag (never materialize) a spot-check-pending fuzzy quote match.

    For each abstained fact whose code is in
    :data:`_FUZZY_RECOVERY_ELIGIBLE_CODES`, compares the extraction
    fact/claim's paraphrased text against every candidate ``quote`` on its own
    source card (not just the one evidence point it was bound to -- the
    paraphrase may describe a *different* point on the same card) and keeps
    the best match. A match at ratio >= 0.9 is recorded as
    ``spot_check_pending``; nothing below 0.9 is recorded at all (SPIKE RQ2:
    0.8 and below demonstrably admits real paraphrase drift). This never
    writes an assertion, edition, or passage -- it only annotates the
    backfill receipt for a human/agent spot-check.
    """

    eligible = [item for item in abstained_claims if item.code in _FUZZY_RECOVERY_ELIGIBLE_CODES]
    if not eligible:
        return ()
    try:
        mappings = claim_mapping.extraction_fact_claim_mappings(run_id, paths=paths)
    except ValueError:
        return ()
    by_claim_id = {mapping.claim_id: mapping for mapping in mappings}

    candidates: list[dict[str, Any]] = []
    for item in eligible:
        mapping = by_claim_id.get(item.claim_id)
        if mapping is None:
            continue
        metadata = _load_source_card(paths, run_id, mapping.source_card_id)
        if metadata is None:
            continue
        points = metadata.get("extracted_points")
        if not isinstance(points, list):
            continue
        best_ratio = 0.0
        best_point: Mapping[str, Any] | None = None
        for point in points:
            if not isinstance(point, Mapping):
                continue
            quote = point.get("quote")
            if not isinstance(quote, str) or not quote:
                continue
            ratio = _fuzzy_ratio(mapping.text, quote)
            if ratio > best_ratio:
                best_ratio, best_point = ratio, point
        if best_point is not None and best_ratio >= _FUZZY_RECOVERY_THRESHOLD:
            candidates.append(
                {
                    "claim_id": item.claim_id,
                    "abstention_code": item.code,
                    "candidate_evidence_id": best_point.get("evidence_id"),
                    "candidate_locator": best_point.get("locator"),
                    "fuzzy_ratio": round(best_ratio, 4),
                    "status": "spot_check_pending",
                    "materialized": False,
                }
            )
    return tuple(candidates)


def _backfill_receipt_path(registry: AssertionRegistry, run_id: str) -> Path:
    if not _RUN_ID_RE.fullmatch(run_id):
        raise ValueError("invalid_run_id")
    return registry.root / "backfill_operations" / f"{run_id}.yaml"


def _atomic_yaml_dump(data: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(dumps_yaml(dict(data)))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


#: Fields describing *this specific invocation*'s call-local outcome
#: (materialized-vs-reused, created-vs-reused) rather than the run's durable
#: materialization outcome. These legitimately differ across an idempotent
#: replay -- ``AssertionRegistry.ingest()``/``AssertionMaterializer.
#: materialize_run()`` return "reused" on a 2nd call precisely because they
#: made 0 new writes -- so a difference confined to these fields is not a
#: conflict and does not trigger a rewrite (P2-05: 0 new writes on replay).
_VOLATILE_BACKFILL_RECEIPT_FIELDS = frozenset({"materialization_status", "source_cards"})


def _stable_backfill_receipt_fields(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in receipt.items() if key not in _VOLATILE_BACKFILL_RECEIPT_FIELDS}


def _write_backfill_receipt(receipt: Mapping[str, Any], path: Path) -> None:
    """Write one run's backfill receipt idempotently (P2-05).

    Only the run's durable outcome (materialized/abstained counts, ids,
    abstention codes, fuzzy-recovery candidates) is conflict-checked. A
    receipt already on disk whose durable outcome differs from a freshly
    computed one raises -- the same fail-closed posture as every other
    immutable record in this ledger. When the durable outcome is unchanged,
    this is a no-op (0 new writes) even if the call-local
    ``materialization_status``/``source_cards`` fields differ (e.g.
    materialized-vs-reused on a 2nd invocation).
    """

    if path.exists():
        existing = load_yaml(path)
        if not isinstance(existing, dict) or _stable_backfill_receipt_fields(
            existing
        ) != _stable_backfill_receipt_fields(receipt):
            raise BackfillConflict("conflicting_backfill_receipt")
        return
    _atomic_yaml_dump(receipt, path)


def backfill_run(
    run_id: str,
    *,
    workspace_id: str,
    paths: FoundryPaths,
    _interrupt_before_publish: bool = False,
) -> dict[str, Any]:
    """Backfill one historical run: reconstruct its editions, then materialize.

    Idempotent and resumable by construction: :meth:`AssertionRegistry.ingest`
    and :meth:`AssertionMaterializer.materialize_run` are each already
    content-addressed/idempotent (P1/P1.5); replaying this function after an
    interruption (including the test-only ``_interrupt_before_publish`` hook)
    reproduces the same editions/passages/assertions rather than duplicating
    or partially completing them. This function's own receipt write is always
    the last step, and is itself conflict-checked (P2-05).

    Never raises on a per-fact abstention -- ``materialize_run()`` is
    skip-and-continue (P2-01b). Ledger-level failures (missing run, invalid
    ledger, non-bijective mapping) surface as a documented run-level
    abstention in the receipt, never an exception; a
    :class:`~research_foundry.services.assertion_materialization.MaterializationConflict`
    (a real integrity conflict) is not caught here and propagates -- a corpus
    backfill fails closed on a corrupted run rather than silently skipping it.
    """

    registry = AssertionRegistry(workspace_id=workspace_id, paths=paths)
    source_cards = _ingest_run_source_cards(run_id, registry=registry, paths=paths)

    materializer = AssertionMaterializer(workspace_id=workspace_id, paths=paths)
    result = materializer.materialize_run(run_id, _interrupt_before_publish=_interrupt_before_publish)

    abstention_breakdown: dict[str, int] = {}
    for item in result.abstained_claims:
        abstention_breakdown[item.code] = abstention_breakdown.get(item.code, 0) + 1

    fuzzy_candidates = _fuzzy_recovery_candidates(run_id, result.abstained_claims, paths=paths)

    receipt: dict[str, Any] = {
        "schema_version": _RECEIPT_SCHEMA_VERSION,
        "type": "assertion_backfill_run_receipt",
        "operation": "assertion_ledger_backfill",
        "run_id": run_id,
        "workspace_id": workspace_id,
        "source_cards": source_cards,
        "materialization_status": result.status,
        "run_level_abstention_code": result.abstention_code if not result.abstained_claims else None,
        "materialized_count": len(result.assertion_ids),
        "materialized_claim_ids": list(result.claim_ids),
        "materialized_assertion_ids": list(result.assertion_ids),
        "abstained_count": len(result.abstained_claims),
        "abstained_claims": [{"claim_id": item.claim_id, "code": item.code} for item in result.abstained_claims],
        "abstention_breakdown": abstention_breakdown,
        "fuzzy_recovery_candidates": list(fuzzy_candidates),
    }
    _write_backfill_receipt(receipt, _backfill_receipt_path(registry, run_id))
    return receipt


def _discover_backfill_candidates(paths: FoundryPaths) -> list[str]:
    """Every run_id with a persisted ``claims/claim_ledger.yaml``, sorted."""

    if not paths.runs.exists():
        return []
    return sorted(
        path.parent.parent.name for path in paths.runs.glob("*/claims/claim_ledger.yaml") if path.is_file()
    )


def backfill_corpus(
    *,
    assertion_registry_workspace_id: str | None,
    paths: FoundryPaths,
    run_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """Write-path counterpart to :func:`backfill_dry_run` (P2-02).

    Resolves the workspace via :func:`resolve_or_deny` before any write --
    ``allowed=False`` (missing workspace context, or
    ``foundry.assertion_ledger.ledger_write_enabled`` not set) performs zero
    writes and returns a typed denial receipt rather than raising or silently
    no-opping. Reports the *actual measured* per-run and aggregate yield;
    never assumes the SPIKE's pre-fix (~3.0%/~6.8%) or fix-isolated (94.78%)
    figures still hold once real writes occur against this workspace's own
    corpus (see the design-spec's "State the yield as two numbers" section).
    """

    resolution = resolve_or_deny(assertion_registry_workspace_id)
    if not resolution.allowed:
        return {
            "schema_version": _RECEIPT_SCHEMA_VERSION,
            "operation": "assertion_ledger_backfill",
            "allowed": False,
            "reason": resolution.reason,
            "workspace_id": None,
            "runs": [],
            "runs_total": 0,
            "materialized_total": 0,
            "abstained_total": 0,
            "abstention_breakdown": {},
            "fuzzy_recovery_candidates_total": 0,
        }

    capabilities = FoundryConfig(paths=paths).assertion_ledger_capabilities()
    if not capabilities.ledger_write_allowed:
        return {
            "schema_version": _RECEIPT_SCHEMA_VERSION,
            "operation": "assertion_ledger_backfill",
            "allowed": False,
            "reason": "ledger_write_disabled",
            "workspace_id": resolution.workspace_id,
            "runs": [],
            "runs_total": 0,
            "materialized_total": 0,
            "abstained_total": 0,
            "abstention_breakdown": {},
            "fuzzy_recovery_candidates_total": 0,
        }

    selected = list(run_ids) if run_ids is not None else _discover_backfill_candidates(paths)
    assert resolution.workspace_id is not None  # narrows for mypy; guaranteed by resolve_or_deny when allowed
    receipts = [backfill_run(run_id, workspace_id=resolution.workspace_id, paths=paths) for run_id in selected]

    abstention_breakdown: dict[str, int] = {}
    for receipt in receipts:
        for code, count in receipt["abstention_breakdown"].items():
            abstention_breakdown[code] = abstention_breakdown.get(code, 0) + count

    return {
        "schema_version": _RECEIPT_SCHEMA_VERSION,
        "operation": "assertion_ledger_backfill",
        "allowed": True,
        "reason": resolution.reason,
        "workspace_id": resolution.workspace_id,
        "runs": receipts,
        "runs_total": len(receipts),
        "materialized_total": sum(receipt["materialized_count"] for receipt in receipts),
        "abstained_total": sum(receipt["abstained_count"] for receipt in receipts),
        "abstention_breakdown": abstention_breakdown,
        "fuzzy_recovery_candidates_total": sum(len(receipt["fuzzy_recovery_candidates"]) for receipt in receipts),
    }


__all__ = [
    "BackfillConflict",
    "backfill_corpus",
    "backfill_dry_run",
    "backfill_run",
    "readiness_metrics",
    "rollback_disable_rehearsal",
    "write_readiness_receipt",
]
