"""CLI-level determinism integration tests for ``rf rights validate`` (P6-4).

Finalizes ``tests/test_rights_validation.py``'s P2-3 unit-level reproducibility
and wall-clock-isolation coverage of
:func:`research_foundry.services.rights_validation.check_rights_divergence` at
the full CLI-integration level, driving the command through Typer's
``CliRunner`` (``research_foundry.cli.app``, matching the pattern in
``tests/test_cli_rights.py``) rather than calling the service function
directly:

1. Two full ``rf rights validate --as-of <date>`` CLI invocations against the
   same on-disk corpus produce byte-identical stdout.
2. Monkeypatching ``datetime.now``/``date.today``/``time.time`` to raise, then
   running the full CLI-layer + service-layer code path with an explicit
   ``--as-of``, completes without ever hitting the patched-to-raise call.
"""

from __future__ import annotations

import os
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import rights_validation
from research_foundry.yamlio import dump_yaml

runner = CliRunner()


def _invoke(args: list[str], cwd: Path):
    """Run the CLI from ``cwd`` so workspace discovery resolves to the tmp root."""

    prev = Path.cwd()
    os.chdir(cwd)
    try:
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(prev)


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


def _write_source_card(
    paths: FoundryPaths, card_id: str, rights_summary: dict[str, Any] | None
) -> Path:
    metadata: dict[str, Any] = {
        "source_card_id": card_id,
        "type": "source_card",
        "source": {"title": "Test Source", "source_type": "official_doc"},
    }
    if rights_summary is not None:
        metadata["rights_summary"] = rights_summary
    path = paths.root / f"{card_id}.md"
    dump_md(metadata, "# Test Source\n", path)
    return path


def _write_rights_record(
    records_dir: Path,
    record_id: str,
    *,
    access_basis: str = "institutional_subscription",
    next_review_at: str | None = "2026-01-01T00:00:00Z",
) -> Path:
    record: dict[str, Any] = {
        "schema_version": "1.0",
        "rights_record_id": record_id,
        "source_id": "src_demo",
        "record_scope": "source_and_access_context",
        "jurisdictions": ["US"],
        "access": {"basis": access_basis, "terms_verified_at": "2026-07-21T12:00:00Z"},
        "copyright": {"status": "copyrighted"},
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


def _build_corpus(tmp_foundry: FoundryPaths) -> tuple[Path, Path, Path]:
    """A corpus mixing divergence, needs_backfill, and stale results — the
    same mix of non-trivial outcomes exercised at the unit level by
    ``test_scenario5_reproducible_byte_identical_output``, but built against
    the on-disk CLI corpus."""

    records_dir = tmp_foundry.root / "rights_records"
    records_dir.mkdir(parents=True, exist_ok=True)
    _write_rights_record(
        records_dir,
        "rr_int_001",
        access_basis="public_web",
        next_review_at="2026-01-01T00:00:00Z",  # before --as-of -> stale
    )

    diverging_summary = _rights_summary(
        access_basis="institutional_subscription", rights_record_ids=["rr_int_001"]
    )
    card_path = _write_source_card(tmp_foundry, "src_int_diverge_001", diverging_summary)
    legacy_path = _write_source_card(tmp_foundry, "src_int_legacy_001", rights_summary=None)
    return card_path, legacy_path, records_dir


# --- (1) two full CLI invocations -> byte-identical stdout ------------------


def test_cli_rights_validate_two_invocations_are_byte_identical(tmp_foundry: FoundryPaths) -> None:
    card_path, legacy_path, records_dir = _build_corpus(tmp_foundry)
    args = [
        "rights",
        "validate",
        "--as-of",
        "2026-07-21",
        "--rights-records-dir",
        str(records_dir),
        "--json",
        str(card_path),
        str(legacy_path),
    ]

    first = _invoke(args, tmp_foundry.root)
    second = _invoke(args, tmp_foundry.root)

    assert first.exit_code == second.exit_code
    assert first.output == second.output
    assert first.output.encode("utf-8") == second.output.encode("utf-8")

    # Sanity: the corpus actually produced a mix of outcomes (not a trivial
    # all-empty diff), and the Rich-table rendering path is equally stable.
    assert "src_int_diverge_001" in first.output

    table_args = [
        "rights",
        "validate",
        "--as-of",
        "2026-07-21",
        "--rights-records-dir",
        str(records_dir),
        str(card_path),
        str(legacy_path),
    ]
    table_first = _invoke(table_args, tmp_foundry.root)
    table_second = _invoke(table_args, tmp_foundry.root)
    assert table_first.output == table_second.output


# --- (2) full CLI path never touches the wall clock --------------------------


class _BlockedDate(date):
    @classmethod
    def today(cls) -> date:  # type: ignore[override]
        raise AssertionError("date.today() must never be called by `rf rights validate`")


class _BlockedDateTime(datetime):
    @classmethod
    def now(cls, tz: Any = None) -> datetime:  # type: ignore[override]
        raise AssertionError("datetime.now() must never be called by `rf rights validate`")


def test_cli_rights_validate_full_path_never_reads_wall_clock(
    monkeypatch: Any, tmp_foundry: FoundryPaths
) -> None:
    def _blocked_time() -> float:
        raise AssertionError("time.time() must never be called by `rf rights validate`")

    # Patch every wall-clock entry point the divergence-validator module
    # could reach, plus the global `time.time` — the same governance
    # invariant P2-3 proved at the service layer, now asserted through the
    # full Typer CLI dispatch (option parsing -> workspace discovery ->
    # check_rights_divergence) rather than calling the service directly.
    monkeypatch.setattr(time, "time", _blocked_time)
    monkeypatch.setattr(rights_validation, "date", _BlockedDate)
    monkeypatch.setattr(rights_validation, "datetime", _BlockedDateTime)

    card_path, legacy_path, records_dir = _build_corpus(tmp_foundry)

    out = _invoke(
        [
            "rights",
            "validate",
            "--as-of",
            "2026-07-21",
            "--rights-records-dir",
            str(records_dir),
            "--json",
            str(card_path),
            str(legacy_path),
        ],
        tmp_foundry.root,
    )

    # `catch_exceptions=False` in `_invoke` means any AssertionError raised by
    # the patched clock functions would propagate and fail this test with a
    # clear traceback rather than being swallowed into a nonzero exit code.
    assert out.exit_code == 1, out.output  # the diverging fixture still fails validation
    assert "src_int_diverge_001" in out.output
