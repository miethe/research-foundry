"""Tests for the attribution-summary divergence validator (SMP-2.5).

Covers ``check_attribution_divergence``'s stated divergence surface --
missing/extra ``attribution_ids``, wrong counts, wrong monotone rollup
pointers, a mirror id with no authoritative record backing it, legacy
absence (``needs_backfill``), supersession-staleness (``stale``), the
wall-clock isolation invariant, reproducibility, and one end-to-end test
through the real ``rf attribution validate`` CLI entry point.
"""

from __future__ import annotations

import json
import os
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import attribution_validation
from research_foundry.services.attribution_triage import mint_attribution_record, refresh_attribution_record
from research_foundry.services.attribution_validation import (
    REASON_MISMATCH,
    REASON_MISSING,
    REASON_UNLINKED,
    check_attribution_divergence,
)
from research_foundry.yamlio import dump_yaml

runner = CliRunner()

# --- fixture builders -------------------------------------------------------


def _write_source_card(tmp_path: Path, card_id: str, attribution_summary: dict[str, Any] | None) -> Path:
    metadata: dict[str, Any] = {
        "source_card_id": card_id,
        "type": "source_card",
        "source": {"title": "Test Source", "source_type": "official_doc"},
    }
    if attribution_summary is not None:
        metadata["attribution_summary"] = attribution_summary
    path = tmp_path / f"{card_id}.md"
    dump_md(metadata, "# Test Source\n", path)
    return path


def _write_attribution_record(records_dir: Path, record: Any) -> Path:
    path = records_dir / f"{record.attribution_id}.yaml"
    dump_yaml(record.as_dict(), path)
    return path


def _mirror(*, attribution_ids: list[str], count: int, rollups: list[dict[str, Any]]) -> dict[str, Any]:
    return {"attribution_ids": attribution_ids, "count": count, "rollups": rollups}


def _rollup(
    *,
    asserter_id: str,
    assertion_kind: str,
    attribution_ids: list[str],
    best_attribution_id: str | None,
    weakest_attribution_id: str | None,
    comparable: bool = True,
) -> dict[str, Any]:
    return {
        "asserter_id": asserter_id,
        "assertion_kind": assertion_kind,
        "attribution_ids": attribution_ids,
        "count": len(attribution_ids),
        "best_attribution_id": best_attribution_id,
        "weakest_attribution_id": weakest_attribution_id,
        "comparable": comparable,
    }


# --- Scenario 1: mirror matches authoritative records -- no divergence -----


def test_matching_mirror_is_not_divergence(tmp_path: Path) -> None:
    records_dir = tmp_path / "attribution_records"
    records_dir.mkdir()
    r1 = mint_attribution_record(
        source="src_match_001",
        asserter_id="semantic_scholar",
        asserter_type="third_party_api",
        assertion_kind="citation_count",
        value=10,
        observed_at="2026-07-01T00:00:00Z",
        license_basis="open_api",
    )
    _write_attribution_record(records_dir, r1)

    mirror = _mirror(
        attribution_ids=[r1.attribution_id],
        count=1,
        rollups=[
            _rollup(
                asserter_id="semantic_scholar",
                assertion_kind="citation_count",
                attribution_ids=[r1.attribution_id],
                best_attribution_id=r1.attribution_id,
                weakest_attribution_id=r1.attribution_id,
            )
        ],
    )
    path = _write_source_card(tmp_path, "src_match_001", mirror)

    results = check_attribution_divergence([path], as_of=date(2026, 7, 21), attribution_records_dir=records_dir)

    assert results[0].ok is True, results[0].findings
    assert results[0].needs_backfill is False
    assert results[0].stale is False


# --- Scenario 2: missing attribution_ids ------------------------------------


def test_missing_authoritative_record_not_in_mirror(tmp_path: Path) -> None:
    records_dir = tmp_path / "attribution_records"
    records_dir.mkdir()
    r1 = mint_attribution_record(
        source="src_missing_001",
        asserter_id="openalex",
        asserter_type="third_party_api",
        assertion_kind="citation_count",
        value=5,
        observed_at="2026-07-01T00:00:00Z",
        license_basis="open_api",
    )
    r2 = mint_attribution_record(
        source="src_missing_001",
        asserter_id="openalex",
        asserter_type="third_party_api",
        assertion_kind="citation_count",
        value=8,
        observed_at="2026-07-02T00:00:00Z",
        license_basis="open_api",
    )
    _write_attribution_record(records_dir, r1)
    _write_attribution_record(records_dir, r2)

    # Mirror only knows about r1 -- r2 is missing from it.
    mirror = _mirror(
        attribution_ids=[r1.attribution_id],
        count=1,
        rollups=[
            _rollup(
                asserter_id="openalex",
                assertion_kind="citation_count",
                attribution_ids=[r1.attribution_id],
                best_attribution_id=r1.attribution_id,
                weakest_attribution_id=r1.attribution_id,
            )
        ],
    )
    path = _write_source_card(tmp_path, "src_missing_001", mirror)

    results = check_attribution_divergence([path], as_of=date(2026, 7, 21), attribution_records_dir=records_dir)

    result = results[0]
    assert result.ok is False
    missing = [f for f in result.findings if f.reason == REASON_MISSING]
    assert any(f.authoritative_value == r2.attribution_id for f in missing), result.findings


# --- Scenario 3: mirror id with no authoritative record backing it ---------


def test_unlinked_mirror_id_has_no_authoritative_backing(tmp_path: Path) -> None:
    records_dir = tmp_path / "attribution_records"
    records_dir.mkdir()

    mirror = _mirror(attribution_ids=["attrib_ghost_001"], count=1, rollups=[])
    path = _write_source_card(tmp_path, "src_ghost_001", mirror)

    results = check_attribution_divergence([path], as_of=date(2026, 7, 21), attribution_records_dir=records_dir)

    result = results[0]
    assert result.ok is False
    assert any(
        f.reason == REASON_UNLINKED and f.mirror_value == "attrib_ghost_001" for f in result.findings
    ), result.findings


# --- Scenario 4: wrong count (self-consistency, no directory needed) -------


def test_wrong_count_is_divergence_without_records_dir(tmp_path: Path) -> None:
    mirror = _mirror(attribution_ids=["a", "b"], count=99, rollups=[])
    path = _write_source_card(tmp_path, "src_count_001", mirror)

    results = check_attribution_divergence([path], as_of=date(2026, 7, 21))

    result = results[0]
    assert result.ok is False
    assert any(f.field == "count" and f.reason == REASON_MISMATCH for f in result.findings)


# --- Scenario 5: wrong monotone rollup pointer ------------------------------


def test_wrong_rollup_pointer_is_divergence(tmp_path: Path) -> None:
    records_dir = tmp_path / "attribution_records"
    records_dir.mkdir()
    weak = mint_attribution_record(
        source="src_rollup_001",
        asserter_id="altmetric",
        asserter_type="third_party_api",
        assertion_kind="altmetric_score",
        value=1,
        observed_at="2026-07-01T00:00:00Z",
        license_basis="open_api",
    )
    best = mint_attribution_record(
        source="src_rollup_001",
        asserter_id="altmetric",
        asserter_type="third_party_api",
        assertion_kind="altmetric_score",
        value=50,
        observed_at="2026-07-02T00:00:00Z",
        license_basis="open_api",
    )
    _write_attribution_record(records_dir, weak)
    _write_attribution_record(records_dir, best)

    # Mirror has best/weakest SWAPPED -- a real recompute would put `best`
    # (value=50) as best_attribution_id, not `weak`.
    mirror = _mirror(
        attribution_ids=[weak.attribution_id, best.attribution_id],
        count=2,
        rollups=[
            _rollup(
                asserter_id="altmetric",
                assertion_kind="altmetric_score",
                attribution_ids=[weak.attribution_id, best.attribution_id],
                best_attribution_id=weak.attribution_id,
                weakest_attribution_id=best.attribution_id,
            )
        ],
    )
    path = _write_source_card(tmp_path, "src_rollup_001", mirror)

    results = check_attribution_divergence([path], as_of=date(2026, 7, 21), attribution_records_dir=records_dir)

    result = results[0]
    assert result.ok is False
    mismatch = [f for f in result.findings if "best_attribution_id" in f.field]
    assert mismatch, result.findings
    assert mismatch[0].authoritative_value == best.attribution_id
    assert mismatch[0].mirror_value == weak.attribution_id


# --- Scenario 6: attribution_summary absent -> needs_backfill, not failure -


def test_absent_attribution_summary_is_needs_backfill_not_failure(tmp_path: Path) -> None:
    path = _write_source_card(tmp_path, "src_legacy_001", attribution_summary=None)

    results = check_attribution_divergence([path], as_of=date(2026, 7, 21))

    result = results[0]
    assert result.needs_backfill is True
    assert result.findings == ()
    assert result.ok is True


# --- Scenario 7: supersession staleness, gated by as_of ---------------------


def test_superseded_record_before_as_of_flags_stale(tmp_path: Path) -> None:
    records_dir = tmp_path / "attribution_records"
    records_dir.mkdir()
    original = mint_attribution_record(
        source="src_stale_001",
        asserter_id="openalex",
        asserter_type="third_party_api",
        assertion_kind="citation_count",
        value=5,
        observed_at="2026-01-01T00:00:00Z",
        license_basis="open_api",
    )
    refreshed = refresh_attribution_record(original, value=12, observed_at="2026-06-01T00:00:00Z")
    _write_attribution_record(records_dir, original)
    _write_attribution_record(records_dir, refreshed)

    # Mirror still points at the ORIGINAL (pre-refresh) id.
    mirror = _mirror(
        attribution_ids=[original.attribution_id],
        count=1,
        rollups=[
            _rollup(
                asserter_id="openalex",
                assertion_kind="citation_count",
                attribution_ids=[original.attribution_id],
                best_attribution_id=original.attribution_id,
                weakest_attribution_id=original.attribution_id,
            )
        ],
    )
    path = _write_source_card(tmp_path, "src_stale_001", mirror)

    results = check_attribution_divergence(
        [path], as_of=date(2026, 7, 21), attribution_records_dir=records_dir
    )

    assert results[0].stale is True


def test_superseding_record_after_as_of_is_not_yet_stale(tmp_path: Path) -> None:
    records_dir = tmp_path / "attribution_records"
    records_dir.mkdir()
    original = mint_attribution_record(
        source="src_fresh_001",
        asserter_id="openalex",
        asserter_type="third_party_api",
        assertion_kind="citation_count",
        value=5,
        observed_at="2026-01-01T00:00:00Z",
        license_basis="open_api",
    )
    refreshed = refresh_attribution_record(original, value=12, observed_at="2026-06-01T00:00:00Z")
    _write_attribution_record(records_dir, original)
    _write_attribution_record(records_dir, refreshed)

    mirror = _mirror(
        attribution_ids=[original.attribution_id],
        count=1,
        rollups=[
            _rollup(
                asserter_id="openalex",
                assertion_kind="citation_count",
                attribution_ids=[original.attribution_id],
                best_attribution_id=original.attribution_id,
                weakest_attribution_id=original.attribution_id,
            )
        ],
    )
    path = _write_source_card(tmp_path, "src_fresh_001", mirror)

    # as_of is BEFORE the refresh's observed_at -- as of that earlier point in
    # time, the record had not yet been superseded.
    results = check_attribution_divergence(
        [path], as_of=date(2026, 2, 1), attribution_records_dir=records_dir
    )

    assert results[0].stale is False


# --- Scenario 8: reproducibility --------------------------------------------


def test_reproducible_byte_identical_output(tmp_path: Path) -> None:
    records_dir = tmp_path / "attribution_records"
    records_dir.mkdir()
    r1 = mint_attribution_record(
        source="src_repro_001",
        asserter_id="openalex",
        asserter_type="third_party_api",
        assertion_kind="citation_count",
        value=5,
        observed_at="2026-07-01T00:00:00Z",
        license_basis="open_api",
    )
    _write_attribution_record(records_dir, r1)

    mirror = _mirror(attribution_ids=[r1.attribution_id, "attrib_ghost_002"], count=1, rollups=[])
    card_path = _write_source_card(tmp_path, "src_repro_001", mirror)
    legacy_path = _write_source_card(tmp_path, "src_repro_legacy_001", attribution_summary=None)

    def _run() -> str:
        results = check_attribution_divergence(
            [card_path, legacy_path], as_of=date(2026, 7, 21), attribution_records_dir=records_dir
        )
        return json.dumps([r.as_dict() for r in results], sort_keys=True)

    first = _run()
    second = _run()

    assert first == second


# --- Governance invariant: never reads the wall clock -----------------------


class _BlockedDate(date):
    @classmethod
    def today(cls) -> date:  # type: ignore[override]
        raise AssertionError("date.today() must never be called by check_attribution_divergence")


class _BlockedDateTime(datetime):
    @classmethod
    def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
        raise AssertionError("datetime.now() must never be called by check_attribution_divergence")


def test_never_reads_wall_clock(monkeypatch: Any, tmp_path: Path) -> None:
    def _blocked_time() -> float:
        raise AssertionError("time.time() must never be called by check_attribution_divergence")

    monkeypatch.setattr(time, "time", _blocked_time)
    monkeypatch.setattr(attribution_validation, "date", _BlockedDate)
    monkeypatch.setattr(attribution_validation, "datetime", _BlockedDateTime)

    records_dir = tmp_path / "attribution_records"
    records_dir.mkdir()
    original = mint_attribution_record(
        source="src_clock_001",
        asserter_id="openalex",
        asserter_type="third_party_api",
        assertion_kind="citation_count",
        value=5,
        observed_at="2026-01-01T00:00:00Z",
        license_basis="open_api",
    )
    refreshed = refresh_attribution_record(original, value=12, observed_at="2026-06-01T00:00:00Z")
    _write_attribution_record(records_dir, original)
    _write_attribution_record(records_dir, refreshed)

    mirror = _mirror(attribution_ids=[original.attribution_id], count=1, rollups=[])
    card_path = _write_source_card(tmp_path, "src_clock_001", mirror)
    legacy_path = _write_source_card(tmp_path, "src_clock_legacy_001", attribution_summary=None)

    # as_of passed as an ISO string forces the module through its own
    # date.fromisoformat / datetime.fromisoformat parsing paths (inherited,
    # unpatched) without ever touching the patched .today()/.now().
    results = check_attribution_divergence(
        [card_path, legacy_path], as_of="2026-07-21", attribution_records_dir=records_dir
    )

    assert results[0].stale is True
    assert results[1].needs_backfill is True


# --- End-to-end: the real `rf attribution validate` CLI entry point --------


def _invoke(args: list[str], cwd: Path):
    prev = Path.cwd()
    os.chdir(cwd)
    try:
        return runner.invoke(app, args)
    finally:
        os.chdir(prev)


def test_cli_attribution_validate_empty_corpus_exits_zero(tmp_foundry: FoundryPaths) -> None:
    out = _invoke(["attribution", "validate", "--as-of", "2026-07-21"], tmp_foundry.root)

    assert out.exit_code == 0, out.output
    assert "0" in out.output


def test_cli_attribution_validate_surfaces_divergence_and_exits_nonzero(tmp_foundry: FoundryPaths) -> None:
    # A mirror id with no authoritative record anywhere is an unconditional
    # divergence (REASON_UNLINKED) once a records dir is in play.
    records_dir = tmp_foundry.root / "attribution_records"
    records_dir.mkdir(parents=True, exist_ok=True)

    mirror = _mirror(attribution_ids=["attrib_cli_ghost_001"], count=1, rollups=[])
    card_path = _write_source_card(tmp_foundry.root, "src_cli_divergence_001", mirror)

    out = _invoke(
        ["attribution", "validate", "--as-of", "2026-07-21", str(card_path)],
        tmp_foundry.root,
    )

    assert out.exit_code == 1, out.output
    assert "FAIL" in out.output
    assert "src_cli_divergence_001" in out.output

    out_json = _invoke(
        ["attribution", "validate", "--as-of", "2026-07-21", "--json", str(card_path)],
        tmp_foundry.root,
    )
    assert out_json.exit_code == 1, out_json.output
    payload = json.loads(out_json.output)
    assert len(payload) == 1
    assert payload[0]["findings"]
