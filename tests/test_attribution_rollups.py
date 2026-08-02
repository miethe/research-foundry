"""M2 rollup evidence tests (source-metadata-propagation-v1, SMP-2.7).

Dedicated evidence file for the plan's AC row "M2 rollups monotone + sorted"
(``docs/project_plans/implementation_plans/infrastructure/source-metadata-propagation-v1.md``).
Distinct from ``tests/test_attribution_triage.py`` (SMP-2.4's general unit-test
file for the same module) -- this file exists so the AC's evidence command
(``pytest tests/test_attribution_rollups.py -q``) has one dedicated,
non-vacuous home. It asserts, against ``services/attribution_triage.py``
(landed, not modified by this task):

1. Monotone reduction: ``best_value`` == ``max``, ``weakest_value`` == ``min``,
   including the single-record case and a tie at the max.
2. Set-union keyed by ``(asserter_id, assertion_kind)`` -- same-key records
   from different physical sources union into one rollup; different asserters
   or different assertion kinds never collapse into each other.
3. The canonical sort is genuinely order-independent: the same logical record
   set, fed in three different orders (as-authored, reversed, and shuffled
   under a fixed seed), serializes byte-identically.
4. No averaging code path exists anywhere in ``services/attribution_*.py``
   -- checked structurally (source text, not behaviour), with an explicit
   existence assertion on the globbed file list first (a grep over zero
   files returns zero matches and reads as a false pass).
5. No wall-clock read anywhere in the rollup path, matching this repo's
   injected-clock idiom (``now_iso()`` at ``services/ids.py:41``, not just
   ``datetime.now``).
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

from research_foundry.services.attribution_triage import (
    mint_attribution_record,
    triage_records,
)

_SERVICES_DIR = Path(__file__).resolve().parent.parent / "src" / "research_foundry" / "services"


def _mint(**overrides):
    defaults = dict(
        source="src_20260802_example_abc123",
        asserter_id="openalex",
        asserter_type="third_party_api",
        assertion_kind="citation_count",
        value=42,
        observed_at="2026-08-02T10:00:00+00:00",
        license_basis="open_api",
    )
    defaults.update(overrides)
    return mint_attribution_record(**defaults)


# --- 1. Monotone: best = max, weakest = min --------------------------------


def test_single_record_rollup_best_equals_weakest():
    only = _mint(value=17)

    result = triage_records("src_single", [only])

    assert result.count == 1
    rollup = result.rollups[0]
    assert rollup.best_value == 17
    assert rollup.weakest_value == 17
    assert rollup.best_attribution_id == only.attribution_id
    assert rollup.weakest_attribution_id == only.attribution_id
    assert rollup.comparable is True


def test_monotone_best_is_max_weakest_is_min_over_known_ranks():
    low = _mint(value=5, observed_at="2026-08-02T10:00:00+00:00")
    mid = _mint(value=20, observed_at="2026-08-02T11:00:00+00:00")
    high = _mint(value=50, observed_at="2026-08-02T12:00:00+00:00")

    result = triage_records("src_ranked", [mid, high, low])  # deliberately unsorted input

    rollup = result.rollups[0]
    assert rollup.best_value == 50
    assert rollup.best_attribution_id == high.attribution_id
    assert rollup.weakest_value == 5
    assert rollup.weakest_attribution_id == low.attribution_id
    # A plain average of {5, 20, 50} would be 25 -- neither best nor weakest may equal it.
    assert rollup.best_value != 25
    assert rollup.weakest_value != 25


def test_monotone_tie_at_max_still_yields_the_unique_min():
    tied_a = _mint(value=10, observed_at="2026-08-02T10:00:00+00:00")
    tied_b = _mint(value=10, observed_at="2026-08-02T11:00:00+00:00")
    clear_min = _mint(value=3, observed_at="2026-08-02T12:00:00+00:00")

    result = triage_records("src_tie", [tied_a, tied_b, clear_min])

    rollup = result.rollups[0]
    # Tie at the top: best_value is the tied max, and its id is genuinely one
    # of the two tied records (not the min, not a synthesized id).
    assert rollup.best_value == 10
    assert rollup.best_attribution_id in {tied_a.attribution_id, tied_b.attribution_id}
    # The minimum is unambiguous despite the tie among the other two.
    assert rollup.weakest_value == 3
    assert rollup.weakest_attribution_id == clear_min.attribution_id
    assert rollup.comparable is True


# --- 2. Set-union keyed by (asserter_id, assertion_kind) -------------------


def test_same_key_records_from_different_sources_union_into_one_rollup():
    from_source_a = _mint(source="src_A", value=5, observed_at="2026-08-02T10:00:00+00:00")
    from_source_b = _mint(source="src_B", value=50, observed_at="2026-08-02T11:00:00+00:00")

    result = triage_records("combined", [from_source_a, from_source_b])

    assert len(result.rollups) == 1
    rollup = result.rollups[0]
    assert rollup.attribution_ids == tuple(
        sorted([from_source_a.attribution_id, from_source_b.attribution_id])
    )
    assert rollup.best_value == 50
    assert rollup.weakest_value == 5


def test_different_asserter_id_does_not_collapse_into_same_rollup():
    openalex_record = _mint(asserter_id="openalex", value=5, observed_at="2026-08-02T10:00:00+00:00")
    semantic_scholar_record = _mint(
        asserter_id="semantic_scholar", value=50, observed_at="2026-08-02T11:00:00+00:00"
    )

    result = triage_records("combined", [openalex_record, semantic_scholar_record])

    assert len(result.rollups) == 2
    keys = {(r.asserter_id, r.assertion_kind) for r in result.rollups}
    assert keys == {("openalex", "citation_count"), ("semantic_scholar", "citation_count")}
    for rollup in result.rollups:
        assert rollup.best_value == rollup.weakest_value  # each group has exactly one record


def test_different_assertion_kind_does_not_collapse_into_same_rollup():
    citation_record = _mint(
        assertion_kind="citation_count", value=5, observed_at="2026-08-02T10:00:00+00:00"
    )
    impact_record = _mint(
        assertion_kind="impact_factor", value=3.2, observed_at="2026-08-02T11:00:00+00:00"
    )

    result = triage_records("combined", [citation_record, impact_record])

    assert len(result.rollups) == 2
    keys = {(r.asserter_id, r.assertion_kind) for r in result.rollups}
    assert keys == {("openalex", "citation_count"), ("openalex", "impact_factor")}


# --- 3. Canonical sort is genuinely order-independent -----------------------


def test_canonical_sort_is_byte_identical_across_genuinely_different_input_orders():
    records = [
        _mint(asserter_id="openalex", assertion_kind="citation_count", value=5, observed_at="2026-08-02T10:00:00+00:00"),
        _mint(asserter_id="openalex", assertion_kind="citation_count", value=50, observed_at="2026-08-02T11:00:00+00:00"),
        _mint(asserter_id="openalex", assertion_kind="citation_count", value=20, observed_at="2026-08-02T12:00:00+00:00"),
        _mint(asserter_id="semantic_scholar", assertion_kind="citation_count", value=8, observed_at="2026-08-02T13:00:00+00:00"),
        _mint(asserter_id="openalex", assertion_kind="impact_factor", value=1.1, observed_at="2026-08-02T14:00:00+00:00"),
        _mint(asserter_id="openalex", assertion_kind="impact_factor", value=9.9, observed_at="2026-08-02T15:00:00+00:00"),
    ]
    # No two records in the same (asserter_id, assertion_kind) group share a
    # value, so best/weakest selection cannot depend on iteration-order tie
    # breaking -- any residual non-determinism here can only come from a
    # missing/implicit sort, which is exactly what this test is for.

    as_authored = list(records)
    reversed_order = list(reversed(records))
    random.seed(42)
    shuffled_order = list(records)
    random.shuffle(shuffled_order)

    # Prove the input orders are genuinely different before trusting the
    # comparison below -- an assertion that re-serializes the same in-memory
    # sequence would prove nothing.
    authored_ids = [r.attribution_id for r in as_authored]
    reversed_ids = [r.attribution_id for r in reversed_order]
    shuffled_ids = [r.attribution_id for r in shuffled_order]
    assert authored_ids != reversed_ids
    assert authored_ids != shuffled_ids
    assert reversed_ids != shuffled_ids

    result_authored = triage_records("src_stability", as_authored)
    result_reversed = triage_records("src_stability", reversed_order)
    result_shuffled = triage_records("src_stability", shuffled_order)

    json_authored = json.dumps(result_authored.as_dict())
    json_reversed = json.dumps(result_reversed.as_dict())
    json_shuffled = json.dumps(result_shuffled.as_dict())

    assert json_authored == json_reversed
    assert json_authored == json_shuffled

    # And the rollups' attribution_ids sets are each individually sorted --
    # not merely equal to each other by coincidence.
    for rollup in result_authored.rollups:
        assert list(rollup.attribution_ids) == sorted(rollup.attribution_ids)


# --- 4. No averaging path exists, checked structurally ---------------------

_NO_AVERAGING_PATTERN = re.compile(
    r"\bmean\(|\bstatistics\.|\bavg\b|sum\([^)]*\)\s*/\s*len\(",
    re.IGNORECASE,
)


def test_attribution_service_files_exist_before_the_grep_that_relies_on_them():
    # Mandatory per this repo's rule (ITT node_01KYVBG7K191K4BKAZPEP5CRDF): a
    # bare grep/regex scan over a glob that matches zero files returns zero
    # matches and reads as a pass. Assert non-empty existence FIRST.
    service_files = sorted(_SERVICES_DIR.glob("attribution_*.py"))
    assert len(service_files) > 0, (
        f"no attribution_*.py files found under {_SERVICES_DIR} -- "
        "the no-averaging check below would vacuously pass"
    )


def test_no_averaging_code_path_exists_in_attribution_services():
    service_files = sorted(_SERVICES_DIR.glob("attribution_*.py"))
    assert len(service_files) > 0  # re-asserted here so this test is independently non-vacuous

    offending: list[str] = []
    for path in service_files:
        text = path.read_text(encoding="utf-8")
        if _NO_AVERAGING_PATTERN.search(text):
            offending.append(str(path))
    assert offending == [], f"averaging-shaped code found in: {offending}"


# --- 5. No wall-clock read in the rollup path -------------------------------

_WALL_CLOCK_PATTERN = re.compile(r"\bnow_iso\b|\bdatetime\.now\b|\btime\.time\b")


def test_no_wall_clock_read_in_the_rollup_path():
    service_files = sorted(_SERVICES_DIR.glob("attribution_*.py"))
    assert len(service_files) > 0

    offending: list[str] = []
    for path in service_files:
        text = path.read_text(encoding="utf-8")
        if _WALL_CLOCK_PATTERN.search(text):
            offending.append(str(path))
    assert offending == [], f"wall-clock read found in: {offending}"
