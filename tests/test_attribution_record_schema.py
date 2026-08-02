"""Fixture coverage for ``schemas/source_attribution.schema.yaml`` (SMP-2.2).

Standalone module for the *authoritative record* schema only — deliberately
NOT named ``..._fixtures.py`` (that name is reserved for a later task's
mirror/rollup/divergence fixture file, ``test_attribution_record_schema_
fixtures.py``, so this file must not collide with it).

Covers exactly what SMP-2.2 requires:

- a minimal valid record (only the required properties) validates cleanly;
- an unknown extra top-level property is REJECTED — proves
  ``additionalProperties: false`` is actually live on this schema, not just
  written in the YAML;
- a record missing each individually required field is rejected, one case
  per field.

Later milestones (M2's mirror/rollup/divergence/staleness tests, M3's
structural provenance gate) get their own dedicated test files per the
plan/progress doc — this file does not anticipate them.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from research_foundry.schemas import validate

SCHEMA_NAME = "source_attribution"


def _valid_record() -> dict[str, Any]:
    """A minimal, fully valid ``source_attribution`` instance."""

    # asserter_type is deliberately NOT a `third_party_*` member here: M3
    # (SMP-3.2B) added a root-level if/then to this schema that requires a
    # non-null `retrieval_evidence_ref` whenever asserter_type starts with
    # `third_party_`, and this file's minimal record is meant to carry ONLY
    # the globally required properties (see module docstring). Picking a
    # non-third-party enum member keeps that "only required properties"
    # claim true without adding an otherwise-optional field.
    return {
        "schema_version": "1.0",
        "attribution_id": "attr_demo_001",
        "source": "src_demo",
        "asserter_id": "semantic_scholar",
        "asserter_type": "human_reviewer",
        "assertion_kind": "citation_count",
        "value": 42,
        "observed_at": "2026-08-02T12:00:00Z",
        "license_basis": "licensed_api",
    }


def _assert_valid(instance: dict[str, Any]) -> None:
    result = validate(instance, SCHEMA_NAME)
    assert result.ok, f"expected valid, got errors: {result.errors}"


def _assert_invalid(instance: dict[str, Any]) -> None:
    result = validate(instance, SCHEMA_NAME)
    assert not result.ok, "expected invalid, but instance validated cleanly"
    assert result.errors


# ---------------------------------------------------------------------------
# Minimal valid record round-trips
# ---------------------------------------------------------------------------


def test_minimal_valid_record_validates() -> None:
    _assert_valid(_valid_record())


def test_valid_record_fixture_is_not_mutated_by_deepcopy_helpers() -> None:
    original = _valid_record()
    mutated = copy.deepcopy(original)
    mutated["value"] = 999
    assert original["value"] != 999


# ---------------------------------------------------------------------------
# additionalProperties: false is live (proves the record-level lock, not
# just the YAML text)
# ---------------------------------------------------------------------------


def test_unknown_extra_property_is_rejected() -> None:
    instance = _valid_record()
    instance["trust_third_party_citation_rank"] = "sneaked in"
    _assert_invalid(instance)


# ---------------------------------------------------------------------------
# Each required field, individually removed, must fail validation
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
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


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_missing_required_field_is_rejected(field: str) -> None:
    instance = _valid_record()
    del instance[field]
    _assert_invalid(instance)


def test_required_fields_list_matches_schema_minimum_plus_design_fields() -> None:
    """Guards this test file's own coverage claim: the parametrized list above
    must actually match what the schema declares required, so a future schema
    edit that adds/removes a required field is caught here rather than
    silently under-tested."""

    from research_foundry.schemas import default_registry

    schema = default_registry().get(SCHEMA_NAME)
    assert sorted(schema["required"]) == sorted(REQUIRED_FIELDS)
