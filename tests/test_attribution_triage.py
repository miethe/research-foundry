"""Unit tests for ``services/attribution_triage.py`` (source-metadata-propagation-v1, SMP-2.4)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from research_foundry.services.attribution_triage import (
    AttributionRecord,
    _merge_attribution_summaries,
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


# ---------------------------------------------------------------------------
# SMP-4.4 Part 2: `_merge_attribution_summaries` — cross-source rollup
# consumption. Monotone-only (no averaging path exists), refuses to launder
# a raw value when a (asserter_id, assertion_kind) key is contributed by
# more than one source, and canonically sorts every id list.
# ---------------------------------------------------------------------------

_ROLLUP_KEYS = {
    "asserter_id",
    "assertion_kind",
    "attribution_ids",
    "count",
    "best_attribution_id",
    "weakest_attribution_id",
    "comparable",
}


def test_merge_attribution_summaries_returns_none_when_all_absent() -> None:
    assert _merge_attribution_summaries([(None, None), (None, None)]) is None
    assert _merge_attribution_summaries([]) is None
    assert _merge_attribution_summaries([(None, None), ("src_b", "not-a-dict"), ("src_c", 42)]) is None


def test_merge_attribution_summaries_single_source_passthrough() -> None:
    """Exactly one contributing source per key: that source's own
    already-computed best/weakest pointers are still authoritative and
    must pass through unchanged — this function never second-guesses a
    single source's own monotone reduction."""

    mirror = {
        "attribution_ids": ["attrib_b", "attrib_a"],
        "count": 2,
        "rollups": [
            {
                "asserter_id": "semantic_scholar",
                "assertion_kind": "citation_count",
                "attribution_ids": ["attrib_b", "attrib_a"],
                "count": 2,
                "best_attribution_id": "attrib_b",
                "weakest_attribution_id": "attrib_a",
                "comparable": True,
            }
        ],
    }
    merged = _merge_attribution_summaries([("src_a", mirror)])
    assert merged == {
        "attribution_ids": ["attrib_a", "attrib_b"],  # canonically sorted
        "count": 2,
        "sources_assessed": 1,
        "sources_total": 1,
        "rollups": [
            {
                "asserter_id": "semantic_scholar",
                "assertion_kind": "citation_count",
                "attribution_ids": ["attrib_a", "attrib_b"],
                "count": 2,
                "best_attribution_id": "attrib_b",
                "weakest_attribution_id": "attrib_a",
                "comparable": True,
            }
        ],
    }


def test_merge_attribution_summaries_cross_source_ambiguous_key_refuses_to_pick_a_winner() -> None:
    """Two DIFFERENT sources both assert under the SAME (asserter_id,
    assertion_kind) key. Picking a "best" between them would require the
    raw values, which this value-free mirror never carries — the merge
    must NOT launder a winner. It degrades to `comparable=False` with both
    pointers `None`, while still unioning the id set and disjoint keys
    (`crossref` below) still pass through as single-source, unaffected.
    """

    source_a = {
        "attribution_ids": ["a1", "a2", "a3"],
        "count": 3,
        "rollups": [
            {
                "asserter_id": "semantic_scholar",
                "assertion_kind": "citation_count",
                "attribution_ids": ["a1", "a2"],
                "count": 2,
                "best_attribution_id": "a2",
                "weakest_attribution_id": "a1",
                "comparable": True,
            },
            {
                "asserter_id": "crossref",
                "assertion_kind": "citation_count",
                "attribution_ids": ["a3"],
                "count": 1,
                "best_attribution_id": "a3",
                "weakest_attribution_id": "a3",
                "comparable": True,
            },
        ],
    }
    source_b = {
        "attribution_ids": ["b1"],
        "count": 1,
        "rollups": [
            {
                "asserter_id": "semantic_scholar",
                "assertion_kind": "citation_count",
                "attribution_ids": ["b1"],
                "count": 1,
                "best_attribution_id": "b1",
                "weakest_attribution_id": "b1",
                "comparable": True,
            }
        ],
    }

    merged = _merge_attribution_summaries([("src_a", source_a), ("src_b", source_b)])
    assert merged is not None
    assert merged["attribution_ids"] == ["a1", "a2", "a3", "b1"]
    assert merged["count"] == 4
    # Both contributing sources were assessed -- full coverage, not partial.
    assert merged["sources_assessed"] == 2
    assert merged["sources_total"] == 2

    by_key = {(r["asserter_id"], r["assertion_kind"]): r for r in merged["rollups"]}

    ambiguous = by_key[("semantic_scholar", "citation_count")]
    assert ambiguous["attribution_ids"] == ["a1", "a2", "b1"]
    assert ambiguous["count"] == 3
    assert ambiguous["comparable"] is False
    assert ambiguous["best_attribution_id"] is None
    assert ambiguous["weakest_attribution_id"] is None

    unambiguous = by_key[("crossref", "citation_count")]
    assert unambiguous["attribution_ids"] == ["a3"]
    assert unambiguous["best_attribution_id"] == "a3"
    assert unambiguous["weakest_attribution_id"] == "a3"
    assert unambiguous["comparable"] is True

    # Structural, not vocabulary-based, non-averaging proof: every rollup
    # entry has EXACTLY the schema-shaped 7 keys — no `best_value`/
    # `weakest_value`/`average_value`/`mean_value` leaked through, and no
    # numeric field exists anywhere for an averaging path to write into.
    for entry in merged["rollups"]:
        assert set(entry.keys()) == _ROLLUP_KEYS


def test_merge_attribution_summaries_is_order_independent() -> None:
    """Canonical sort means the merge result must not depend on the order
    mirrors are passed in — `json.dump` preserves insertion order but does
    not impose one (plan decision)."""

    source_a = {
        "attribution_ids": ["z9", "a1"],
        "count": 2,
        "rollups": [
            {
                "asserter_id": "openalex",
                "assertion_kind": "citation_count",
                "attribution_ids": ["z9"],
                "count": 1,
                "best_attribution_id": "z9",
                "weakest_attribution_id": "z9",
                "comparable": True,
            }
        ],
    }
    source_b = {
        "attribution_ids": ["m5"],
        "count": 1,
        "rollups": [
            {
                "asserter_id": "openalex",
                "assertion_kind": "retraction_status",
                "attribution_ids": ["m5"],
                "count": 1,
                "best_attribution_id": "m5",
                "weakest_attribution_id": "m5",
                "comparable": True,
            }
        ],
    }

    forward = _merge_attribution_summaries([("src_a", source_a), ("src_b", source_b)])
    backward = _merge_attribution_summaries([("src_b", source_b), ("src_a", source_a)])
    assert forward == backward
    assert forward is not None
    assert forward["attribution_ids"] == sorted(forward["attribution_ids"])
    # Coverage counts are cardinalities, not order-dependent either.
    assert forward["sources_assessed"] == 2
    assert forward["sources_total"] == 2


# ---------------------------------------------------------------------------
# Partial-coverage bug fix: a claim citing an unassessed source (its mirror
# is `None`) alongside an assessed one must NOT read identically to a claim
# whose sources were all assessed. See _merge_attribution_summaries's own
# "Partial-coverage honesty (bug fix)" docstring section.
# ---------------------------------------------------------------------------


def test_merge_attribution_summaries_distinguishes_partial_from_full_coverage() -> None:
    """AC: a claim citing one assessed + one unassessed source must assert a
    DIFFERENT merged value than a claim citing two assessed sources."""

    assessed_a = {
        "attribution_ids": ["a1"],
        "count": 1,
        "rollups": [
            {
                "asserter_id": "semantic_scholar",
                "assertion_kind": "citation_count",
                "attribution_ids": ["a1"],
                "count": 1,
                "best_attribution_id": "a1",
                "weakest_attribution_id": "a1",
                "comparable": True,
            }
        ],
    }
    assessed_b = {
        "attribution_ids": ["b1"],
        "count": 1,
        "rollups": [
            {
                "asserter_id": "crossref",
                "assertion_kind": "citation_count",
                "attribution_ids": ["b1"],
                "count": 1,
                "best_attribution_id": "b1",
                "weakest_attribution_id": "b1",
                "comparable": True,
            }
        ],
    }

    partial = _merge_attribution_summaries([("src_a", assessed_a), ("src_b", None)])
    full = _merge_attribution_summaries([("src_a", assessed_a), ("src_b", assessed_b)])

    assert partial is not None
    assert full is not None
    assert partial != full  # the AC's core assertion

    # The unassessed source contributes no ids/rollups of its own -- the
    # known-good half is reported exactly as if it were the only input --
    # but the coverage counts now honestly say "only some of what this
    # claim cites has been checked".
    assert partial["attribution_ids"] == ["a1"]
    assert partial["count"] == 1
    assert partial["rollups"] == assessed_a["rollups"]
    assert partial["sources_assessed"] == 1
    assert partial["sources_total"] == 2  # <- the fix: the unassessed source still counts

    assert full["attribution_ids"] == ["a1", "b1"]
    assert full["count"] == 2
    assert full["sources_assessed"] == 2
    assert full["sources_total"] == 2


def test_merge_attribution_summaries_malformed_entry_counts_as_unassessed() -> None:
    """A non-dict, non-None entry (e.g. a corrupt mirror) degrades exactly
    like `None` for coverage purposes -- it is not silently dropped from
    `sources_total` either."""

    mirror = {
        "attribution_ids": ["x1"],
        "count": 1,
        "rollups": [],
    }
    merged = _merge_attribution_summaries([("src_a", mirror), ("src_b", "not-a-dict"), ("src_c", 42)])
    assert merged is not None
    assert merged["sources_assessed"] == 1
    assert merged["sources_total"] == 3


def test_merge_attribution_summaries_partial_coverage_is_order_independent() -> None:
    """Partial-coverage counts must not depend on where the unassessed
    entry falls in the input sequence."""

    assessed = {
        "attribution_ids": ["z1"],
        "count": 1,
        "rollups": [],
    }

    leading_none = _merge_attribution_summaries([("src_b", None), ("src_a", assessed)])
    trailing_none = _merge_attribution_summaries([("src_a", assessed), ("src_b", None)])
    assert leading_none == trailing_none
    assert leading_none is not None
    assert leading_none["sources_assessed"] == 1
    assert leading_none["sources_total"] == 2


# ---------------------------------------------------------------------------
# Phase C: input-contract fix -- (source_card_id, attribution_summary) PAIRS,
# not bare summaries. Closes the position-vs-cardinality over-count: a claim
# citing one source through N evidence anchors must report "1 of 1", not
# "N of N". See _merge_attribution_summaries's "Input contract" docstring
# section.
# ---------------------------------------------------------------------------


def test_merge_attribution_summaries_dedupes_duplicate_source_card_id() -> None:
    """AC: the same source_card_id cited via multiple evidence anchors must
    count as ONE distinct source in sources_assessed/sources_total, not one
    per input position -- the exact bug this contract-shape fix closes."""

    mirror = {
        "attribution_ids": ["a1", "a2"],
        "count": 2,
        "rollups": [
            {
                "asserter_id": "semantic_scholar",
                "assertion_kind": "citation_count",
                "attribution_ids": ["a1", "a2"],
                "count": 2,
                "best_attribution_id": "a2",
                "weakest_attribution_id": "a1",
                "comparable": True,
            }
        ],
    }
    # Same source_card_id, three evidence anchors -- one card, mirror repeated.
    merged = _merge_attribution_summaries([("src_a", mirror), ("src_a", mirror), ("src_a", mirror)])
    assert merged is not None
    assert merged["sources_assessed"] == 1
    assert merged["sources_total"] == 1
    assert merged["attribution_ids"] == ["a1", "a2"]
    assert merged["count"] == 2


def test_merge_attribution_summaries_one_distinct_source_via_n_anchors_reports_1_of_1() -> None:
    """AC: "N anchors, 1 source" must report "1 of 1", never "N of N" --
    the literal defect described in the review finding."""

    mirror = {
        "attribution_ids": ["z1"],
        "count": 1,
        "rollups": [],
    }
    merged = _merge_attribution_summaries(
        [("src_only", mirror), ("src_only", mirror), ("src_only", mirror), ("src_only", mirror)]
    )
    assert merged is not None
    assert merged["sources_assessed"] == 1
    assert merged["sources_total"] == 1


def test_merge_attribution_summaries_mixed_duplicate_and_unassessed_reports_1_of_2() -> None:
    """AC: source A cited twice (assessed) + source B cited once
    (unassessed) must report 1 of 2 -- 2 distinct sources, 1 assessed."""

    mirror_a = {
        "attribution_ids": ["a1"],
        "count": 1,
        "rollups": [],
    }
    merged = _merge_attribution_summaries([("src_a", mirror_a), ("src_a", mirror_a), ("src_b", None)])
    assert merged is not None
    assert merged["sources_assessed"] == 1
    assert merged["sources_total"] == 2
    assert merged["attribution_ids"] == ["a1"]


def test_merge_attribution_summaries_dedupe_preserves_invariant_3_distinction() -> None:
    """Invariant 3 distinction: two entries sharing a source_card_id (one
    card, two anchors) must be treated as ONE source and pass through its
    own pointers unchanged (comparable=True); two entries with genuinely
    DIFFERENT source_card_ids at the same (asserter_id, assertion_kind) key
    must still refuse to pick a winner (comparable=False). The dedupe fix
    must not collapse the second case into the first, nor split the first
    into the second."""

    mirror = {
        "attribution_ids": ["a1", "a2"],
        "count": 2,
        "rollups": [
            {
                "asserter_id": "semantic_scholar",
                "assertion_kind": "citation_count",
                "attribution_ids": ["a1", "a2"],
                "count": 2,
                "best_attribution_id": "a2",
                "weakest_attribution_id": "a1",
                "comparable": True,
            }
        ],
    }
    # Same source, cited via two anchors -- one distinct source -> passthrough.
    same_source = _merge_attribution_summaries([("src_a", mirror), ("src_a", mirror)])
    assert same_source is not None
    assert same_source["sources_assessed"] == 1
    assert same_source["sources_total"] == 1
    rollup = same_source["rollups"][0]
    assert rollup["comparable"] is True
    assert rollup["best_attribution_id"] == "a2"
    assert rollup["weakest_attribution_id"] == "a1"

    other_mirror = {
        "attribution_ids": ["b1"],
        "count": 1,
        "rollups": [
            {
                "asserter_id": "semantic_scholar",
                "assertion_kind": "citation_count",
                "attribution_ids": ["b1"],
                "count": 1,
                "best_attribution_id": "b1",
                "weakest_attribution_id": "b1",
                "comparable": True,
            }
        ],
    }
    # Genuinely different sources under the same key -- still ambiguous.
    different_sources = _merge_attribution_summaries([("src_a", mirror), ("src_b", other_mirror)])
    assert different_sources is not None
    assert different_sources["sources_assessed"] == 2
    assert different_sources["sources_total"] == 2
    different_rollup = different_sources["rollups"][0]
    assert different_rollup["comparable"] is False
    assert different_rollup["best_attribution_id"] is None
    assert different_rollup["weakest_attribution_id"] is None
