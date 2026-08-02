"""Fixture coverage for the M2 value-free mirror + recompute-only invariants (SMP-2.6).

This is the file ``test_attribution_record_schema.py`` (SMP-2.2) reserved by name
in its own module docstring: that file covers the *authoritative*
``source_attribution`` record schema in isolation (minimal-valid,
``additionalProperties: false`` on the record, each required field removed).
This file covers the plan's M2 accepted decision that resolves OQ-3 --
``source_card.schema.yaml``'s ``attribution_summary`` mirror is **value-free**
(ids/counts/monotone-rollup-pointers only, never a raw third-party value) and
**recompute-only** (never itself the source of truth for a value) -- plus the
authoritative record's own round-trip, which SMP-2.2's file exercises too but
is repeated here per this task's explicit instruction (AC-M2-1/AC-M2-2/
AC-M2-3 in ``.claude/progress/source-metadata-propagation/phase-2-progress.md``
name this exact filename as the evidence surface for all three).

Four things are proven, each written so it FAILS if the corresponding
feature were absent (see the non-vacuousness note below the imports):

1. A valid authoritative ``source_attribution`` record round-trips: it
   validates, survives a YAML dump/reload cycle byte-for-value identical,
   and validates again.
2. A hand-written raw third-party value anywhere under ``attribution_summary``
   -- at the summary's own level OR inside one of its ``rollups[]`` entries --
   is a validation error, across several shapes an agent would plausibly
   reach for (a bare number, a bare string, a nested object, and several
   plausible field names: ``value``, ``citation_count``, ``best_value``,
   ``weakest_value``, an arbitrarily-named escape hatch). The control is
   schema SHAPE (``additionalProperties: false`` at both levels, plus every
   declared property being scalar/id/bool-typed with nowhere to put an
   arbitrary value) -- not a field-name list, so this parametrizes over
   shapes rather than asserting one magic key is blocked.
3. A mirror can claim an ``attribution_id`` no authoritative record backs
   and still pass pure JSON-Schema shape validation (jsonschema has no
   cross-document referential-integrity construct) -- but the mirror is
   documented as *recompute-only from authoritative records*, and
   attempting to actually do that recomputation (``load_attribution_records``
   over the files the claimed ids should resolve to) raises when one of
   them has no backing file on disk. This is the real enforcement
   mechanism available today (``attribution_validation.py``'s divergence
   checker is a concurrent, not-yet-landed leg) and is what "a mirror
   without its authoritative record fails validation" cashes out to.
4. Each of the authoritative record's required fields, individually
   removed, is rejected (mirrors SMP-2.2's own coverage; kept here too
   because the progress doc's AC row cites this filename).

Non-vacuousness of point 2 (per this task's explicit instruction): before
finalizing, a scratch COPY of ``schemas/source_card.schema.yaml`` was made in
a temp dir with ``attribution_summary``'s ``additionalProperties`` relaxed
from ``false`` to ``true`` at both the summary level and the ``rollups[]``
item level, pointed to via a standalone ``SchemaRegistry(schemas_dir=...)``
(bypassing the process-wide cached ``default_registry()``), and every
raw-value-shape case below was re-run against it. All of them flipped from
RED (correctly invalid) to GREEN (incorrectly valid), confirming the
assertions are not vacuous -- see the task report for the exact command and
observed output. The real ``schemas/`` directory is never modified by this
module.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from research_foundry.schemas import validate
from research_foundry.services.attribution_triage import (
    load_attribution_records,
    mint_attribution_record,
)

RECORD_SCHEMA = "source_attribution"
CARD_SCHEMA = "source_card"


# ---------------------------------------------------------------------------
# Fixture builders (``_valid``/``_invalid`` style, per test_rights_record_
# schema_fixtures.py's convention)
# ---------------------------------------------------------------------------


def _valid_record(**overrides: Any) -> dict[str, Any]:
    """A minimal, fully valid ``source_attribution`` instance."""

    record: dict[str, Any] = {
        "schema_version": "1.0",
        "attribution_id": "attrib_20260802_srcdemo_abc1234",
        "source": "src_demo",
        "asserter_id": "semantic_scholar",
        "asserter_type": "third_party_api",
        "assertion_kind": "citation_count",
        "value": 42,
        "observed_at": "2026-08-02T12:00:00Z",
        "license_basis": "licensed_api",
        # asserter_type is "third_party_api" above, so M3 (SMP-3.2B)'s
        # root-level if/then on this schema now requires this to be a
        # non-null string -- `None` (valid before M3) would make this
        # otherwise-valid fixture fail every test that calls
        # `validate(_valid_record(), RECORD_SCHEMA)` below.
        "retrieval_evidence_ref": "fetch_receipt_demo_001",
        "supersedes_attribution_id": None,
    }
    record.update(overrides)
    return record


def _valid_rollup_entry(**overrides: Any) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "asserter_id": "semantic_scholar",
        "assertion_kind": "citation_count",
        "attribution_ids": ["attrib_20260802_srcdemo_abc1234"],
        "count": 1,
        "best_attribution_id": "attrib_20260802_srcdemo_abc1234",
        "weakest_attribution_id": "attrib_20260802_srcdemo_abc1234",
        "comparable": True,
    }
    entry.update(overrides)
    return entry


def _valid_attribution_summary(**overrides: Any) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "attribution_ids": ["attrib_20260802_srcdemo_abc1234"],
        "count": 1,
        "rollups": [_valid_rollup_entry()],
    }
    summary.update(overrides)
    return summary


def _valid_card(**overrides: Any) -> dict[str, Any]:
    card: dict[str, Any] = {
        "source_card_id": "src_demo",
        "type": "source_card",
        "source": {"title": "Demo source"},
    }
    card.update(overrides)
    return card


def _assert_valid(instance: Any, schema_name: str) -> None:
    result = validate(instance, schema_name)
    assert result.ok, f"expected valid, got errors: {result.errors}"


def _assert_invalid(instance: Any, schema_name: str) -> None:
    result = validate(instance, schema_name)
    assert not result.ok, "expected invalid, but instance validated cleanly"
    assert result.errors


# ---------------------------------------------------------------------------
# 1. Authoritative record round-trips
# ---------------------------------------------------------------------------


def test_valid_record_validates() -> None:
    _assert_valid(_valid_record(), RECORD_SCHEMA)


def test_valid_record_round_trips_through_yaml_and_revalidates() -> None:
    """validate -> serialize -> reload -> validate again, unchanged."""

    record = _valid_record()
    _assert_valid(record, RECORD_SCHEMA)

    dumped = yaml.safe_dump(record)
    reloaded = yaml.safe_load(dumped)

    assert reloaded == record
    _assert_valid(reloaded, RECORD_SCHEMA)


def test_record_fixture_is_not_mutated_by_deepcopy_helpers() -> None:
    original = _valid_record()
    mutated = copy.deepcopy(original)
    mutated["value"] = 999
    assert original["value"] != 999


# ---------------------------------------------------------------------------
# 4. Authoritative record: each required field, individually removed, rejected
# ---------------------------------------------------------------------------

REQUIRED_RECORD_FIELDS = [
    "schema_version",
    "attribution_id",
    "source",
    "asserter_id",
    "asserter_type",
    "assertion_kind",
    "value",
    "observed_at",
    "license_basis",
]


@pytest.mark.parametrize("field", REQUIRED_RECORD_FIELDS)
def test_record_missing_required_field_is_rejected(field: str) -> None:
    instance = _valid_record()
    del instance[field]
    _assert_invalid(instance, RECORD_SCHEMA)


# ---------------------------------------------------------------------------
# Sanity: the card + value-free mirror, unmodified, must validate cleanly --
# guards the builders themselves so the raw-value-shape cases below are
# testing the invariant, not a broken fixture.
# ---------------------------------------------------------------------------


def test_valid_card_with_attribution_summary_validates() -> None:
    card = _valid_card(attribution_summary=_valid_attribution_summary())
    _assert_valid(card, CARD_SCHEMA)


def test_card_with_null_attribution_summary_validates() -> None:
    """A pre-existing card, or one with no attribution records yet, is not a
    validation failure -- absent means "not yet assessed", per the schema's
    own resilience posture (mirrors ``rights_summary``'s convention)."""

    card = _valid_card(attribution_summary=None)
    _assert_valid(card, CARD_SCHEMA)


def test_card_missing_attribution_summary_entirely_validates() -> None:
    card = _valid_card()
    assert "attribution_summary" not in card
    _assert_valid(card, CARD_SCHEMA)


# ---------------------------------------------------------------------------
# 2. Value-free mirror invariant: a hand-written raw value anywhere under
# attribution_summary is rejected, across several shapes/field names.
# ---------------------------------------------------------------------------

# Deliberately varied: a plausible "obvious" name, a plausible "renamed to
# dodge a name-list" escape hatch, a numeric literal, a string literal, and a
# nested structured object -- proving the control is additionalProperties +
# scalar-only declared properties (shape), not a guard against one specific
# key name.
RAW_VALUE_SHAPES: list[tuple[str, Any]] = [
    ("value", 42),
    ("citation_count", 128),
    ("best_value", 99.5),
    ("weakest_value", "retracted"),
    ("raw_third_party_value", {"nested": "object", "score": 7}),
    ("impact_factor", 3.14),
]


@pytest.mark.parametrize("field_name,raw_value", RAW_VALUE_SHAPES)
def test_raw_value_at_summary_top_level_is_rejected(field_name: str, raw_value: Any) -> None:
    summary = _valid_attribution_summary()
    summary[field_name] = raw_value
    card = _valid_card(attribution_summary=summary)
    _assert_invalid(card, CARD_SCHEMA)


@pytest.mark.parametrize("field_name,raw_value", RAW_VALUE_SHAPES)
def test_raw_value_inside_rollup_entry_is_rejected(field_name: str, raw_value: Any) -> None:
    summary = _valid_attribution_summary()
    summary["rollups"] = [_valid_rollup_entry(**{field_name: raw_value})]
    card = _valid_card(attribution_summary=summary)
    _assert_invalid(card, CARD_SCHEMA)


def test_summary_missing_required_key_is_rejected() -> None:
    for key in ("attribution_ids", "count", "rollups"):
        summary = _valid_attribution_summary()
        del summary[key]
        card = _valid_card(attribution_summary=summary)
        _assert_invalid(card, CARD_SCHEMA)


def test_rollup_entry_missing_required_key_is_rejected() -> None:
    for key in (
        "asserter_id",
        "assertion_kind",
        "attribution_ids",
        "count",
        "best_attribution_id",
        "weakest_attribution_id",
        "comparable",
    ):
        entry = _valid_rollup_entry()
        del entry[key]
        card = _valid_card(attribution_summary=_valid_attribution_summary(rollups=[entry]))
        _assert_invalid(card, CARD_SCHEMA)


# ---------------------------------------------------------------------------
# 3. Recompute-only invariant: shape validation alone cannot catch an
# unbacked attribution_id (jsonschema has no cross-document referential
# check) -- but actually recomputing the mirror from the authoritative
# records it claims to summarize DOES fail when one is missing.
# ---------------------------------------------------------------------------


def test_mirror_with_unbacked_attribution_id_passes_shape_but_fails_to_recompute(
    tmp_path: Path,
) -> None:
    backed = mint_attribution_record(
        source="src_demo",
        asserter_id="semantic_scholar",
        asserter_type="third_party_api",
        assertion_kind="citation_count",
        value=42,
        observed_at="2026-08-02T12:00:00Z",
        license_basis="licensed_api",
    )
    backed_path = tmp_path / f"{backed.attribution_id}.yaml"
    backed_path.write_text(yaml.safe_dump(backed.as_dict()), encoding="utf-8")

    unbacked_id = "attrib_ghost_00000000_unbacked"
    unbacked_path = tmp_path / f"{unbacked_id}.yaml"
    assert not unbacked_path.exists()

    summary = _valid_attribution_summary(
        attribution_ids=sorted([backed.attribution_id, unbacked_id]),
        count=2,
    )
    card = _valid_card(attribution_summary=summary)

    # Shape alone validates cleanly: a mirror is free to CLAIM an id nothing
    # backs, because jsonschema cannot assert "this id resolves to a file on
    # disk" -- this is the gap the recompute step below actually closes.
    _assert_valid(card, CARD_SCHEMA)

    # Recomputing the mirror from the authoritative records it names is the
    # real "recompute-only" invariant, and it raises: the mirror is only
    # ever an index into records that must actually exist.
    with pytest.raises(FileNotFoundError):
        load_attribution_records([backed_path, unbacked_path])


def test_mirror_backed_by_every_claimed_id_recomputes_cleanly(tmp_path: Path) -> None:
    """Positive control for the test above: when every claimed id IS backed
    by a real record file, recomputation succeeds -- proving the prior
    test's failure is specifically about the missing file, not an unrelated
    fixture mistake."""

    record = mint_attribution_record(
        source="src_demo",
        asserter_id="semantic_scholar",
        asserter_type="third_party_api",
        assertion_kind="citation_count",
        value=42,
        observed_at="2026-08-02T12:00:00Z",
        license_basis="licensed_api",
    )
    path = tmp_path / f"{record.attribution_id}.yaml"
    path.write_text(yaml.safe_dump(record.as_dict()), encoding="utf-8")

    loaded = load_attribution_records([path])
    assert len(loaded) == 1
    assert loaded[0] == record
