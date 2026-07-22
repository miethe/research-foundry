"""CLI-level tests for ``rf rights ...`` (rights-entity-model-v1, P2-4).

Covers the Typer wiring in ``cli_commands.py`` around the ``rights_app``
sub-app (``inspect``/``list`` stubs + the ``validate`` subcommand that calls
:func:`research_foundry.services.rights_validation.check_rights_divergence`).
Service-level behavior (the 5 H3 divergence scenarios + wall-clock isolation)
is already covered by ``tests/test_rights_validation.py``; these tests only
exercise the CLI surface:

1. ``rf rights validate`` with no ``--as-of`` -> non-zero exit, no crash,
   no wall-clock date is ever computed (Typer's own required-option gate).
2. ``rf rights validate --as-of <date>`` against an empty corpus -> exit 0
   with a sane empty-summary table.
3. ``rf rights validate --as-of <date> <path>`` against a fixture with a
   real ``rights_summary`` divergence -> non-zero exit, failure surfaced
   in the output.
4. ``rf rights inspect <id>`` prints the full rights posture (rights_summary
   + substitutability) for a known entity, and exits non-zero with a clear
   message for an unknown id (P4-5).
5. ``rf rights list --status <status>`` filters entities by
   ``rights_summary.review_status`` (P4-5).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from typer.testing import CliRunner

from research_foundry.cli import app
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.yamlio import dump_yaml

runner = CliRunner()


def _invoke(args: list[str], cwd: Path):
    """Run the CLI from ``cwd`` so workspace discovery resolves to the tmp root."""

    prev = Path.cwd()
    os.chdir(cwd)
    try:
        return runner.invoke(app, args)
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


def _write_source_card(paths: FoundryPaths, card_id: str, rights_summary: dict[str, Any]) -> Path:
    metadata: dict[str, Any] = {
        "source_card_id": card_id,
        "type": "source_card",
        "source": {"title": "Test Source", "source_type": "official_doc"},
        "rights_summary": rights_summary,
    }
    path = paths.root / f"{card_id}.md"
    dump_md(metadata, "# Test Source\n", path)
    return path


def _write_corpus_source_card(
    paths: FoundryPaths,
    card_id: str,
    rights_summary: dict[str, Any],
    *,
    run_id: str = "run_001",
    extra_metadata: dict[str, Any] | None = None,
) -> Path:
    """Write a source_card under ``runs/<run_id>/source_cards/`` — the default
    corpus glob ``rights inspect``/``rights list`` (and ``rights validate``
    with no explicit paths) scan."""

    metadata: dict[str, Any] = {
        "source_card_id": card_id,
        "type": "source_card",
        "source": {"title": "Test Source", "source_type": "official_doc"},
        "rights_summary": rights_summary,
    }
    if extra_metadata:
        metadata.update(extra_metadata)
    path = paths.runs / run_id / "source_cards" / f"{card_id}.md"
    dump_md(metadata, "# Test Source\n", path)
    return path


# --- (a) --as-of is required -----------------------------------------------


def test_rights_validate_requires_as_of(tmp_foundry: FoundryPaths) -> None:
    out = _invoke(["rights", "validate"], tmp_foundry.root)

    assert out.exit_code != 0, out.output
    assert out.exit_code == 2, out.output  # Click/Typer's own missing-option exit code
    assert "--as-of" in out.output


# --- (b) empty corpus --------------------------------------------------------


def test_rights_validate_empty_corpus_exits_zero(tmp_foundry: FoundryPaths) -> None:
    out = _invoke(["rights", "validate", "--as-of", "2026-07-21"], tmp_foundry.root)

    assert out.exit_code == 0, out.output
    assert "0" in out.output  # the "checked" column of the empty summary table


def test_rights_validate_empty_corpus_json_output(tmp_foundry: FoundryPaths) -> None:
    out = _invoke(["rights", "validate", "--as-of", "2026-07-21", "--json"], tmp_foundry.root)

    assert out.exit_code == 0, out.output
    assert out.output.strip() == "[]"


# --- (c) a real divergence fixture surfaces as a CLI failure ----------------


def test_rights_validate_surfaces_divergence_and_exits_nonzero(tmp_foundry: FoundryPaths) -> None:
    # Scenario 1 from test_rights_validation.py: a substantive mirror value
    # with no linked rights_record_ids is an unconditional divergence.
    summary = _rights_summary(access_basis="public_web", rights_record_ids=[])
    card_path = _write_source_card(tmp_foundry, "src_cli_divergence_001", summary)

    out = _invoke(
        ["rights", "validate", "--as-of", "2026-07-21", str(card_path)],
        tmp_foundry.root,
    )

    assert out.exit_code == 1, out.output
    assert "FAIL" in out.output
    assert "src_cli_divergence_001" in out.output


def test_rights_validate_surfaces_divergence_json(tmp_foundry: FoundryPaths) -> None:
    summary = _rights_summary(access_basis="public_web", rights_record_ids=[])
    card_path = _write_source_card(tmp_foundry, "src_cli_divergence_002", summary)

    out = _invoke(
        ["rights", "validate", "--as-of", "2026-07-21", "--json", str(card_path)],
        tmp_foundry.root,
    )

    assert out.exit_code == 1, out.output
    import json

    payload = json.loads(out.output)
    assert len(payload) == 1
    # NOTE: RightsCheckResult.ok is a @property, not a dataclass field, so
    # asdict() (used by as_dict()) omits it from the JSON payload — callers
    # must derive pass/fail from `findings` being non-empty. This is the
    # actual contract of the JSON output today; assert against it directly
    # rather than a key that isn't there.
    assert "ok" not in payload[0]
    assert payload[0]["findings"]


def test_rights_validate_matching_record_exits_zero(tmp_foundry: FoundryPaths) -> None:
    """Sanity counterpart: a linked, matching rights_record must NOT fail the CLI."""

    records_dir = tmp_foundry.root / "rights_records"
    records_dir.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "schema_version": "1.0",
        "rights_record_id": "rr_cli_match_001",
        "source_id": "src_demo",
        "record_scope": "source_and_access_context",
        "jurisdictions": ["US"],
        "access": {"basis": "public_web", "terms_verified_at": "2026-07-21T12:00:00Z"},
        "copyright": {"status": "copyrighted"},
        "component_decisions": [
            {"component_type": "bibliographic_metadata", "decision": "permitted"},
        ],
        "overall_status": "UNKNOWN",
        "review": {
            "reviewed_at": "2026-07-21T12:00:00Z",
            "review_status": "agent_triage_only",
            "next_review_at": "2027-01-01T00:00:00Z",
        },
    }
    dump_yaml(record, records_dir / "rr_cli_match_001.yaml")

    summary = _rights_summary(access_basis="public_web", rights_record_ids=["rr_cli_match_001"])
    card_path = _write_source_card(tmp_foundry, "src_cli_match_001", summary)

    out = _invoke(
        ["rights", "validate", "--as-of", "2026-07-21", str(card_path)],
        tmp_foundry.root,
    )

    assert out.exit_code == 0, out.output


# --- (d) rf rights inspect ---------------------------------------------------


def test_rights_inspect_prints_full_posture_for_known_id(tmp_foundry: FoundryPaths) -> None:
    summary = _rights_summary(
        access_basis="public_web",
        rights_record_ids=["rr_inspect_001"],
        review_status="agent_triage_only",
    )
    _write_corpus_source_card(
        tmp_foundry,
        "src_inspect_001",
        summary,
        extra_metadata={"substitutability": {"status": "no_substitute_found", "candidate_source_ids": []}},
    )

    records_dir = tmp_foundry.root / "rights_records"
    records_dir.mkdir(parents=True, exist_ok=True)
    dump_yaml(
        {
            "schema_version": "1.0",
            "rights_record_id": "rr_inspect_001",
            "source_id": "src_demo",
            "record_scope": "source",
            "jurisdictions": ["US"],
            "access": {"basis": "public_web"},
            "copyright": {"status": "copyrighted"},
            "component_decisions": [],
            "overall_status": "UNKNOWN",
            "review": {"review_status": "agent_triage_only"},
        },
        records_dir / "rr_inspect_001.yaml",
    )

    out = _invoke(["rights", "inspect", "src_inspect_001"], tmp_foundry.root)

    assert out.exit_code == 0, out.output
    assert "rights_summary.access_basis" in out.output
    assert "public_web" in out.output
    assert "substitutability.status" in out.output
    assert "no_substitute_found" in out.output
    assert "synthesis.record_scope" in out.output


def test_rights_inspect_json_output(tmp_foundry: FoundryPaths) -> None:
    summary = _rights_summary(access_basis="public_web", rights_record_ids=[])
    _write_corpus_source_card(tmp_foundry, "src_inspect_json_001", summary)

    out = _invoke(["rights", "inspect", "src_inspect_json_001", "--json"], tmp_foundry.root)

    assert out.exit_code == 0, out.output
    import json

    payload = json.loads(out.output)
    assert payload["id"] == "src_inspect_json_001"
    assert payload["rights_summary"]["access_basis"] == "public_web"
    assert payload["substitutability"] is None
    assert payload["linked_rights_record"] is None


def test_rights_inspect_unknown_id_exits_nonzero(tmp_foundry: FoundryPaths) -> None:
    out = _invoke(["rights", "inspect", "src_does_not_exist"], tmp_foundry.root)

    assert out.exit_code == 1, out.output
    assert "no source_card/source_assertion found" in out.output


# --- (e) rf rights list -------------------------------------------------------


def test_rights_list_filters_by_review_status(tmp_foundry: FoundryPaths) -> None:
    # --json (not the Rich table) is used for the assertion: the table's
    # columns elide long ids/paths under the narrow console width the test
    # harness captures at, which would make an `in out.output` substring
    # check flaky rather than a genuine behavior check.
    _write_corpus_source_card(
        tmp_foundry,
        "src_list_triage_001",
        _rights_summary(review_status="agent_triage_only"),
    )
    _write_corpus_source_card(
        tmp_foundry,
        "src_list_unknown_001",
        _rights_summary(review_status="unknown"),
    )

    out = _invoke(["rights", "list", "--status", "agent_triage_only", "--json"], tmp_foundry.root)

    assert out.exit_code == 0, out.output
    import json

    payload = json.loads(out.output)
    ids = {row["id"] for row in payload}
    assert ids == {"src_list_triage_001"}


def test_rights_list_json_output_no_filter_lists_all(tmp_foundry: FoundryPaths) -> None:
    _write_corpus_source_card(
        tmp_foundry, "src_list_all_001", _rights_summary(review_status="agent_triage_only")
    )
    _write_corpus_source_card(tmp_foundry, "src_list_all_002", _rights_summary(review_status="unknown"))

    out = _invoke(["rights", "list", "--json"], tmp_foundry.root)

    assert out.exit_code == 0, out.output
    import json

    payload = json.loads(out.output)
    ids = {row["id"] for row in payload}
    assert ids == {"src_list_all_001", "src_list_all_002"}


def test_rights_list_empty_corpus_exits_zero(tmp_foundry: FoundryPaths) -> None:
    out = _invoke(["rights", "list"], tmp_foundry.root)

    assert out.exit_code == 0, out.output
