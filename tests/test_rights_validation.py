"""Tests for the rights-summary divergence validator (rights-entity-model-v1, P2-3).

Covers the 5 enumerated H3 scenarios from
``docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1/phase-0-2-schema.md``
(P2-3 row) plus a dedicated wall-clock-isolation test:

1. Non-``unknown`` mirror value with empty ``rights_record_ids`` -> divergence FAIL.
2. Mirror value diverges from its linked ``rights_record``'s actual value -> FAIL.
3. ``rights_summary`` absent entirely on a legacy instance -> non-fatal ``needs_backfill``.
4. Linked ``rights_record.review.next_review_at`` before ``as_of`` -> ``stale=True``.
5. Two invocations, identical ``as_of`` + unchanged inputs -> byte-identical output.
6. ``datetime.now``/``time.time``/``date.today`` are never read (governance invariant).
"""

from __future__ import annotations

import json
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

from research_foundry.frontmatter import dump_md
from research_foundry.services import rights_validation
from research_foundry.services.rights_validation import (
    REASON_MISMATCH,
    REASON_UNLINKED,
    check_rights_divergence,
)
from research_foundry.yamlio import dump_yaml

# --- fixture builders -------------------------------------------------------


def _rights_summary(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
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
    base.update(overrides)
    return base


def _write_source_card(tmp_path: Path, card_id: str, rights_summary: dict[str, Any] | None) -> Path:
    metadata: dict[str, Any] = {
        "source_card_id": card_id,
        "type": "source_card",
        "source": {"title": "Test Source", "source_type": "official_doc"},
    }
    if rights_summary is not None:
        metadata["rights_summary"] = rights_summary
    path = tmp_path / f"{card_id}.md"
    dump_md(metadata, "# Test Source\n", path)
    return path


def _write_source_assertion(tmp_path: Path, assertion_id: str, rights_summary: dict[str, Any] | None) -> Path:
    metadata: dict[str, Any] = {
        "schema_version": "1.0",
        "type": "source_assertion",
        "assertion_id": assertion_id,
    }
    if rights_summary is not None:
        metadata["rights_summary"] = rights_summary
    path = tmp_path / f"{assertion_id}.yaml"
    dump_yaml(metadata, path)
    return path


def _write_rights_record(
    records_dir: Path,
    record_id: str,
    *,
    access_basis: str = "institutional_subscription",
    copyright_status: str = "copyrighted",
    next_review_at: str | None = "2026-08-01T00:00:00Z",
) -> Path:
    record: dict[str, Any] = {
        "schema_version": "1.0",
        "rights_record_id": record_id,
        "source_id": "src_demo",
        "record_scope": "source_and_access_context",
        "jurisdictions": ["US"],
        "access": {
            "basis": access_basis,
            "terms_verified_at": "2026-07-21T12:00:00Z",
        },
        "copyright": {"status": copyright_status},
        "component_decisions": [
            {"component_type": "bibliographic_metadata", "decision": "permitted"},
        ],
        "overall_status": "UNKNOWN",
        "review": {
            "reviewed_at": "2026-07-21T12:00:00Z",
            "review_status": "agent_triage_only",
            "next_review_at": next_review_at,
        },
    }
    path = records_dir / f"{record_id}.yaml"
    dump_yaml(record, path)
    return path


# --- Scenario 1: substantive mirror value, no linked rights_record_ids -----


def test_scenario1_unlinked_substantive_value_is_divergence(tmp_path: Path) -> None:
    summary = _rights_summary(access_basis="public_web", rights_record_ids=[])
    path = _write_source_card(tmp_path, "src_001", summary)

    results = check_rights_divergence([path], as_of=date(2026, 7, 21))

    assert len(results) == 1
    result = results[0]
    assert result.needs_backfill is False
    assert result.ok is False
    assert any(f.reason == REASON_UNLINKED and f.field == "rights_record_ids" for f in result.findings)


# --- Scenario 2: mirror value diverges from its linked rights_record -------


def test_scenario2_mirror_diverges_from_linked_record(tmp_path: Path) -> None:
    records_dir = tmp_path / "rights_records"
    records_dir.mkdir()
    _write_rights_record(records_dir, "rr_diverge_001", access_basis="institutional_subscription")

    summary = _rights_summary(access_basis="public_web", rights_record_ids=["rr_diverge_001"])
    path = _write_source_card(tmp_path, "src_002", summary)

    results = check_rights_divergence([path], as_of=date(2026, 7, 21), rights_records_dir=records_dir)

    result = results[0]
    assert result.ok is False
    mismatch = [f for f in result.findings if f.reason == REASON_MISMATCH]
    assert mismatch, result.findings
    assert mismatch[0].field == "access_basis"
    assert mismatch[0].mirror_value == "public_web"
    assert mismatch[0].authoritative_value == "institutional_subscription"


def test_scenario2_matching_mirror_value_is_not_divergence(tmp_path: Path) -> None:
    """Sanity counterpart: identical values must NOT be flagged."""

    records_dir = tmp_path / "rights_records"
    records_dir.mkdir()
    _write_rights_record(records_dir, "rr_match_001", access_basis="public_web")

    summary = _rights_summary(access_basis="public_web", rights_record_ids=["rr_match_001"])
    path = _write_source_card(tmp_path, "src_002b", summary)

    results = check_rights_divergence([path], as_of=date(2026, 7, 21), rights_records_dir=records_dir)

    assert results[0].ok is True
    assert results[0].needs_backfill is False


# --- Scenario 3: rights_summary absent entirely on a legacy instance --------


def test_scenario3_absent_rights_summary_is_needs_backfill_not_failure(tmp_path: Path) -> None:
    path = _write_source_assertion(tmp_path, "ast_legacy_001", rights_summary=None)

    results = check_rights_divergence([path], as_of=date(2026, 7, 21))

    result = results[0]
    assert result.needs_backfill is True
    assert result.findings == ()
    assert result.ok is True  # non-fatal: absence must never read as divergence


# --- Scenario 4: linked rights_record.review.next_review_at before as_of ---


def test_scenario4_past_next_review_at_flags_stale(tmp_path: Path) -> None:
    records_dir = tmp_path / "rights_records"
    records_dir.mkdir()
    _write_rights_record(records_dir, "rr_stale_001", next_review_at="2026-01-01T00:00:00Z")

    # All mirror fields stay "unknown" -- rights_record_ids may still be
    # populated for provenance without triggering the link-before-assert
    # check, and staleness is independent of divergence.
    summary = _rights_summary(rights_record_ids=["rr_stale_001"])
    path = _write_source_card(tmp_path, "src_004", summary)

    results = check_rights_divergence([path], as_of=date(2026, 7, 21), rights_records_dir=records_dir)

    result = results[0]
    assert result.stale is True
    assert result.ok is True  # staleness is non-blocking
    assert result.needs_backfill is False


def test_scenario4_future_next_review_at_is_not_stale(tmp_path: Path) -> None:
    records_dir = tmp_path / "rights_records"
    records_dir.mkdir()
    _write_rights_record(records_dir, "rr_fresh_001", next_review_at="2027-01-01T00:00:00Z")

    summary = _rights_summary(rights_record_ids=["rr_fresh_001"])
    path = _write_source_card(tmp_path, "src_004b", summary)

    results = check_rights_divergence([path], as_of=date(2026, 7, 21), rights_records_dir=records_dir)

    assert results[0].stale is False


# --- Scenario 5: reproducibility -- identical as_of + unchanged inputs -----


def test_scenario5_reproducible_byte_identical_output(tmp_path: Path) -> None:
    records_dir = tmp_path / "rights_records"
    records_dir.mkdir()
    _write_rights_record(
        records_dir,
        "rr_repro_001",
        access_basis="public_web",
        next_review_at="2026-01-01T00:00:00Z",
    )

    summary = _rights_summary(access_basis="institutional_subscription", rights_record_ids=["rr_repro_001"])
    card_path = _write_source_card(tmp_path, "src_005", summary)
    assertion_path = _write_source_assertion(tmp_path, "ast_005", rights_summary=None)

    def _run() -> str:
        results = check_rights_divergence(
            [card_path, assertion_path],
            as_of=date(2026, 7, 21),
            rights_records_dir=records_dir,
        )
        return json.dumps([r.as_dict() for r in results], sort_keys=True)

    first = _run()
    second = _run()

    assert first == second


# --- Governance invariant: never reads the wall clock -----------------------


class _BlockedDate(date):
    @classmethod
    def today(cls) -> date:  # type: ignore[override]
        raise AssertionError("date.today() must never be called by check_rights_divergence")


class _BlockedDateTime(datetime):
    @classmethod
    def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
        raise AssertionError("datetime.now() must never be called by check_rights_divergence")


def test_never_reads_wall_clock(monkeypatch: Any, tmp_path: Path) -> None:
    def _blocked_time() -> float:
        raise AssertionError("time.time() must never be called by check_rights_divergence")

    monkeypatch.setattr(time, "time", _blocked_time)
    monkeypatch.setattr(rights_validation, "date", _BlockedDate)
    monkeypatch.setattr(rights_validation, "datetime", _BlockedDateTime)

    records_dir = tmp_path / "rights_records"
    records_dir.mkdir()
    _write_rights_record(
        records_dir,
        "rr_clock_001",
        access_basis="public_web",
        next_review_at="2026-01-01T00:00:00Z",
    )
    summary = _rights_summary(access_basis="public_web", rights_record_ids=["rr_clock_001"])
    card_path = _write_source_card(tmp_path, "src_006", summary)
    legacy_path = _write_source_assertion(tmp_path, "ast_006", rights_summary=None)

    # as_of passed as an ISO string forces the module through its own
    # date.fromisoformat / datetime.fromisoformat parsing paths (inherited,
    # unpatched) without ever touching the patched .today()/.now().
    results = check_rights_divergence([card_path, legacy_path], as_of="2026-07-21", rights_records_dir=records_dir)

    assert results[0].stale is True
    assert results[0].ok is True
    assert results[1].needs_backfill is True
