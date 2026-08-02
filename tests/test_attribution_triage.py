"""Unit tests for ``services/attribution_triage.py`` (source-metadata-propagation-v1, SMP-2.4)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from research_foundry.services.attribution_triage import (
    AttributionRecord,
    compute_source_attribution_triage,
    load_attribution_records,
    mint_attribution_record,
    refresh_attribution_record,
    triage_records,
)


def _mint(**overrides):
    defaults = dict(
        source="src_20260802_example_abc123",
        asserter_id="semantic_scholar",
        asserter_type="third_party_api",
        assertion_kind="citation_count",
        value=42,
        observed_at="2026-08-02T10:00:00+00:00",
        license_basis="open_api",
    )
    defaults.update(overrides)
    return mint_attribution_record(**defaults)


def test_mint_attribution_record_is_schema_shaped():
    record = _mint()
    assert record.schema_version == "1.0"
    assert record.attribution_id.startswith("attrib_20260802_")
    assert len(record.attribution_id) >= 5
    assert record.retrieval_evidence_ref is None
    assert record.supersedes_attribution_id is None


def test_mint_attribution_record_is_deterministic():
    a = _mint()
    b = _mint()
    assert a.attribution_id == b.attribution_id
    assert a.as_dict() == b.as_dict()


def test_mint_attribution_record_id_changes_with_value_context():
    a = _mint()
    b = _mint(assertion_kind="impact_factor")
    assert a.attribution_id != b.attribution_id


def test_refresh_never_mutates_previous_and_is_append_only():
    original = _mint()
    refreshed = refresh_attribution_record(
        original,
        value=99,
        observed_at="2026-08-03T10:00:00+00:00",
    )

    # Append-only: a NEW record, distinct id, pointing backward.
    assert refreshed.attribution_id != original.attribution_id
    assert refreshed.supersedes_attribution_id == original.attribution_id
    assert refreshed.value == 99

    # The original is untouched.
    assert original.value == 42
    assert original.supersedes_attribution_id is None

    # Structural enforcement: AttributionRecord is frozen -- no mutation path.
    with pytest.raises(Exception):
        original.value = 100  # type: ignore[misc]


def test_frozen_dataclass_has_no_setattr_path():
    record = _mint()
    with pytest.raises(Exception):
        record.attribution_id = "tampered"  # type: ignore[misc]


def test_triage_records_groups_by_asserter_and_kind_with_monotone_rollup():
    low = _mint(asserter_id="openalex", assertion_kind="citation_count", value=5)
    high = _mint(asserter_id="openalex", assertion_kind="citation_count", value=50, observed_at="2026-08-02T11:00:00+00:00")
    other_kind = _mint(asserter_id="openalex", assertion_kind="altmetric_score", value=7, observed_at="2026-08-02T12:00:00+00:00")

    result = triage_records("src_20260802_example_abc123", [low, high, other_kind])

    assert result.count == 3
    assert result.attribution_ids == tuple(sorted([low.attribution_id, high.attribution_id, other_kind.attribution_id]))

    citation_rollup = next(r for r in result.rollups if r.assertion_kind == "citation_count")
    assert citation_rollup.best_value == 50
    assert citation_rollup.best_attribution_id == high.attribution_id
    assert citation_rollup.weakest_value == 5
    assert citation_rollup.weakest_attribution_id == low.attribution_id
    assert citation_rollup.comparable is True
    assert citation_rollup.attribution_ids == tuple(sorted([low.attribution_id, high.attribution_id]))


def test_no_numeric_averaging_path_exists():
    # A rollup only ever exposes best_value/weakest_value (max/min) -- there is
    # no "average"/"mean" field or code path anywhere in the module.
    import research_foundry.services.attribution_triage as mod

    source = mod.__file__
    with open(source, "r", encoding="utf-8") as f:
        text = f.read()
    assert "average" not in text.lower()
    assert "mean(" not in text
    assert "statistics." not in text


def test_rollup_set_union_is_canonically_sorted_and_stable_across_runs():
    a = _mint(asserter_id="openalex", assertion_kind="citation_count", value=5)
    b = _mint(asserter_id="openalex", assertion_kind="citation_count", value=50, observed_at="2026-08-02T11:00:00+00:00")

    first = triage_records("src_1", [b, a])
    second = triage_records("src_1", [a, b])

    first_ids = next(r for r in first.rollups if r.assertion_kind == "citation_count").attribution_ids
    second_ids = next(r for r in second.rollups if r.assertion_kind == "citation_count").attribution_ids
    assert first_ids == second_ids
    assert list(first_ids) == sorted(first_ids)


def test_incomparable_values_degrade_to_non_comparable_rollup():
    a = _mint(asserter_id="human_reviewer_1", asserter_type="human_reviewer", assertion_kind="retraction_status", value=1)
    b = _mint(
        asserter_id="human_reviewer_1",
        asserter_type="human_reviewer",
        assertion_kind="retraction_status",
        value={"structured": True},
        observed_at="2026-08-02T13:00:00+00:00",
    )

    result = triage_records("src_1", [a, b])
    rollup = result.rollups[0]
    assert rollup.comparable is False
    assert rollup.best_value is None
    assert rollup.weakest_value is None


def test_load_attribution_records_round_trips_from_yaml(tmp_path: Path):
    record = _mint()
    path = tmp_path / f"{record.attribution_id}.yaml"
    path.write_text(yaml.safe_dump(record.as_dict()), encoding="utf-8")

    loaded = load_attribution_records([path])
    assert len(loaded) == 1
    assert loaded[0] == record


def test_load_attribution_records_missing_required_field_raises(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump({"schema_version": "1.0", "source": "x"}), encoding="utf-8")

    with pytest.raises(ValueError):
        load_attribution_records([path])


def test_compute_source_attribution_triage_never_raises_on_missing_file(tmp_path: Path):
    missing = tmp_path / "does_not_exist.yaml"
    result = compute_source_attribution_triage(
        "src_1",
        [missing],
        attempted_at="2026-08-02T10:00:00+00:00",
    )
    assert result.count == 0
    assert result.triage_failure is not None
    assert result.triage_failure["attempted_at"] == "2026-08-02T10:00:00+00:00"
    assert result.triage_failure["reason"] == "triage_error"


def test_compute_source_attribution_triage_success_has_no_failure_record(tmp_path: Path):
    record = _mint()
    path = tmp_path / f"{record.attribution_id}.yaml"
    path.write_text(yaml.safe_dump(record.as_dict()), encoding="utf-8")

    result = compute_source_attribution_triage("src_1", [path])
    assert result.triage_failure is None
    assert result.count == 1


def test_module_never_reads_wall_clock():
    import inspect

    import research_foundry.services.attribution_triage as mod

    source = inspect.getsource(mod)
    assert "now_iso" not in source
    assert "datetime.now" not in source
    assert "time.time" not in source


def test_attribution_record_from_dict_requires_fields():
    with pytest.raises(ValueError):
        AttributionRecord.from_dict({"source": "x"})
