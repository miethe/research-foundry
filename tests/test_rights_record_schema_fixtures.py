"""Fixture coverage for ``schemas/rights_record.schema.yaml`` (P0-1).

Scratch/handoff fixtures for the rights-entity-model Phase 0 substrate port.
This module is deliberately **separate** from ``tests/test_schema_validation.py``
so P0-5 (Registry wiring + that file's builders) can extend the shared file
without any merge overlap with this one. P0-5 may reuse, copy, or
re-derive the instance shapes below when it wires ``rights_record`` into
``EXPECTED_SCHEMA_NAMES`` and the ``_valid``/``_invalid`` builders — this file
is not itself the registry coverage gate.

Covers, one valid + one invalid case per row (plus a dedicated §9.6b guard),
the 7 locked §9 adjudications applied in ``rights_record.schema.yaml``:

- §9.3  ``access.basis`` gains an ``unknown`` member.
- §9.4  ``access.{automated_retrieval_allowed,text_and_data_mining_allowed,
        model_training_allowed}`` + ``contract.{bulk_retrieval,model_training}``
        share ONE enum (``allowed|allowed_with_conditions|prohibited|
        not_addressed|unknown``).
- §9.5  ``record_scope: first_party`` + ``overall_status: OWNED``; ``source_id``
        conditionally optional only when ``record_scope == "first_party"``.
- §9.6a ``pattern: "^https?://"`` replaces ``format: uri`` on
        ``access.terms_url`` / ``copyright.license_url``.
- §9.6b When ``contract`` is non-null, all 7 restriction sub-fields are
        required (each accepting ``"unknown"``); an empty ``contract: {}``
        must FAIL (fail-open regression guard — dedicated fixture below).
- §9.7  Canonical 6-member ``review.review_status`` enum (byte-identical list
        for P0-3's ``content_reuse_assessment.schema.yaml`` to copy).
- §9.8  ``component_decisions[].component_type`` unified singular vocabulary,
        including ``abstract`` and ``supplementary_material``.
"""

from __future__ import annotations

import copy
from typing import Any

from research_foundry.schemas import validate

SCHEMA_NAME = "rights_record"


def _base_valid_record() -> dict[str, Any]:
    """A minimal, fully valid ``rights_record`` instance (third-party scope)."""

    return {
        "schema_version": "1.0",
        "rights_record_id": "rr_demo_001",
        "source_id": "src_demo",
        "record_scope": "source_and_access_context",
        "jurisdictions": ["US"],
        "access": {
            "basis": "institutional_subscription",
            "terms_verified_at": "2026-07-21T12:00:00Z",
        },
        "copyright": {
            "status": "copyrighted",
        },
        "component_decisions": [
            {"component_type": "bibliographic_metadata", "decision": "permitted"},
        ],
        "overall_status": "UNKNOWN",
        "review": {
            "reviewed_at": "2026-07-21T12:00:00Z",
            "review_status": "agent_triage_only",
        },
    }


def _assert_valid(instance: dict[str, Any]) -> None:
    result = validate(instance, SCHEMA_NAME)
    assert result.ok, f"expected valid, got errors: {result.errors}"


def _assert_invalid(instance: dict[str, Any]) -> None:
    result = validate(instance, SCHEMA_NAME)
    assert not result.ok, "expected invalid, but instance validated cleanly"
    assert result.errors


# ---------------------------------------------------------------------------
# §9.3 — access.basis gains "unknown"
# ---------------------------------------------------------------------------


def test_9_3_access_basis_unknown_is_valid() -> None:
    instance = _base_valid_record()
    instance["access"]["basis"] = "unknown"
    _assert_valid(instance)


def test_9_3_access_basis_arbitrary_string_is_invalid() -> None:
    """Pre-fix defect check: an agent guessing an unmodeled basis value must
    still be rejected — "unknown" is the ONLY sanctioned way to record
    ignorance, not a free-form fallback."""

    instance = _base_valid_record()
    instance["access"]["basis"] = "not_a_real_basis"
    _assert_invalid(instance)


# ---------------------------------------------------------------------------
# §9.4 — unified allowed|allowed_with_conditions|prohibited|not_addressed|unknown
# ---------------------------------------------------------------------------


def _contract_all_unknown() -> dict[str, str]:
    return {
        "incorporation_into_other_products": "unknown",
        "adaptation": "unknown",
        "commercial_use": "unknown",
        "redistribution": "unknown",
        "sublicensing": "unknown",
        "bulk_retrieval": "unknown",
        "model_training": "unknown",
    }


def test_9_4_unified_permission_enum_is_valid() -> None:
    instance = _base_valid_record()
    instance["access"]["automated_retrieval_allowed"] = "allowed_with_conditions"
    instance["access"]["text_and_data_mining_allowed"] = "not_addressed"
    instance["access"]["model_training_allowed"] = "unknown"
    instance["contract"] = _contract_all_unknown()
    instance["contract"]["bulk_retrieval"] = "prohibited"
    instance["contract"]["model_training"] = "allowed"
    _assert_valid(instance)


def test_9_4_old_pre_unification_enum_value_is_invalid() -> None:
    """Pre-fix defect check: the old ``access.*_allowed`` vocabulary
    (``yes``/``yes_with_conditions``/``no``) must no longer validate now that
    the field shares the unified enum with ``contract.*``."""

    instance = _base_valid_record()
    instance["access"]["automated_retrieval_allowed"] = "yes"
    _assert_invalid(instance)


# ---------------------------------------------------------------------------
# §9.5 — record_scope: first_party + overall_status: OWNED; conditional source_id
# ---------------------------------------------------------------------------


def test_9_5_first_party_owned_without_source_id_is_valid() -> None:
    instance = _base_valid_record()
    instance.pop("source_id", None)
    instance["record_scope"] = "first_party"
    instance["overall_status"] = "OWNED"
    _assert_valid(instance)


def test_9_5_non_first_party_without_source_id_is_invalid() -> None:
    """Pre-fix defect check: dropping source_id is ONLY legal when
    record_scope == "first_party" — any other scope must still require it."""

    instance = _base_valid_record()
    instance.pop("source_id", None)
    assert instance["record_scope"] != "first_party"
    _assert_invalid(instance)


# ---------------------------------------------------------------------------
# §9.6a — pattern replaces format: uri on terms_url / license_url
# ---------------------------------------------------------------------------


def test_9_6a_https_urls_are_valid() -> None:
    instance = _base_valid_record()
    instance["access"]["terms_url"] = "https://example.test/terms"
    instance["copyright"]["license_url"] = "https://example.test/license"
    _assert_valid(instance)


def test_9_6a_non_url_string_is_invalid() -> None:
    """Pre-fix defect check: `format: uri` is not enforced by every
    validator (fail-open on garbage input) — `pattern` must reject a
    non-URL string that a permissive `format` implementation would accept."""

    instance = _base_valid_record()
    instance["access"]["terms_url"] = "not a url"
    _assert_invalid(instance)


# ---------------------------------------------------------------------------
# §9.6b — contract non-null requires all 7 sub-fields; empty {} must fail
# ---------------------------------------------------------------------------


def test_9_6b_full_contract_object_is_valid() -> None:
    instance = _base_valid_record()
    instance["contract"] = _contract_all_unknown()
    _assert_valid(instance)


def test_9_6b_contract_missing_one_required_field_is_invalid() -> None:
    instance = _base_valid_record()
    contract = _contract_all_unknown()
    del contract["model_training"]
    instance["contract"] = contract
    _assert_invalid(instance)


def test_9_6b_empty_contract_object_is_invalid_dedicated_guard() -> None:
    """THE dedicated fail-open regression guard fixture (§9.6b): v1.0 made
    ``contract`` nullable with no required members, so ``{"contract": {}}``
    validated identically to ``contract: null`` — "not assessed" and "no
    restrictions" became indistinguishable. This must now fail."""

    instance = _base_valid_record()
    instance["contract"] = {}
    _assert_invalid(instance)


def test_9_6b_null_contract_remains_valid() -> None:
    """`contract: null` still means "not assessed at all" and must remain
    legal — only the empty OBJECT `{}` is the fail-open case being closed."""

    instance = _base_valid_record()
    instance["contract"] = None
    _assert_valid(instance)


# ---------------------------------------------------------------------------
# §9.7 — canonical 6-member review.review_status enum
# ---------------------------------------------------------------------------


def test_9_7_legal_review_required_member_is_valid() -> None:
    """The member content_reuse_assessment lacked pre-fix (v1.0) — proves the
    canonical 6-member list (to be copied verbatim by P0-3) round-trips."""

    instance = _base_valid_record()
    instance["review"]["review_status"] = "legal_review_required_before_commercial_use"
    _assert_valid(instance)


def test_9_7_unknown_review_status_value_is_invalid() -> None:
    instance = _base_valid_record()
    instance["review"]["review_status"] = "downgraded_and_wrong"
    _assert_invalid(instance)


# ---------------------------------------------------------------------------
# §9.8 — unified singular component_type vocabulary incl. abstract/supplementary_material
# ---------------------------------------------------------------------------


def test_9_8_singular_vocabulary_and_new_members_are_valid() -> None:
    instance = _base_valid_record()
    instance["component_decisions"] = [
        {"component_type": "abstract", "decision": "permitted"},
        {"component_type": "supplementary_material", "decision": "unknown"},
        {
            "component_type": "atomic_fact",
            "decision": "facts_only_subject_to_access_contract_and_legal_review",
        },
        {"component_type": "method", "decision": "unknown"},
        {"component_type": "trademark_or_logo", "decision": "prohibited"},
        {"component_type": "reference_interval_value", "decision": "unknown"},
    ]
    _assert_valid(instance)


def test_9_8_old_aggregate_plural_component_type_is_invalid() -> None:
    """Pre-fix defect check: the old aggregate/plural v1.0 members
    (``atomic_facts_and_methods``, ``reference_interval_values``,
    ``trademarks_and_logos``) must no longer validate now that the
    vocabulary is unified to singulars."""

    instance = _base_valid_record()
    instance["component_decisions"] = [
        {"component_type": "atomic_facts_and_methods", "decision": "permitted"},
    ]
    _assert_invalid(instance)


# ---------------------------------------------------------------------------
# P4-3 — access.terms_snapshot_failure typed structural failure record
# ---------------------------------------------------------------------------


def test_p4_3_terms_snapshot_failure_populated_with_null_snapshot_fields_is_valid() -> None:
    """The failure-path shape: terms_snapshot_uri/sha256 stay null while
    terms_snapshot_failure carries the typed record."""

    instance = _base_valid_record()
    instance["access"]["terms_snapshot_uri"] = None
    instance["access"]["terms_snapshot_sha256"] = None
    instance["access"]["terms_snapshot_failure"] = {
        "reason": "fetch_error",
        "detail": "simulated network failure",
        "attempted_at": "2026-07-21T12:00:00Z",
    }
    _assert_valid(instance)


def test_p4_3_terms_snapshot_failure_null_is_valid() -> None:
    """Explicit null (never attempted) must still validate."""

    instance = _base_valid_record()
    instance["access"]["terms_snapshot_failure"] = None
    _assert_valid(instance)


def test_p4_3_terms_snapshot_failure_missing_required_subfield_is_invalid() -> None:
    """A partial failure record (missing `detail`) must FAIL -- the whole
    point of a typed record is that it can't silently degrade to a
    half-populated shape either."""

    instance = _base_valid_record()
    instance["access"]["terms_snapshot_failure"] = {
        "reason": "fetch_error",
        "attempted_at": "2026-07-21T12:00:00Z",
    }
    _assert_invalid(instance)


def test_p4_3_terms_snapshot_failure_unmodeled_reason_is_invalid() -> None:
    """An agent must not invent a free-form reason string -- only the two
    enumerated members are sanctioned (mirrors the §9.3 "unknown" pattern:
    record ignorance via a modeled value, never a guess)."""

    instance = _base_valid_record()
    instance["access"]["terms_snapshot_failure"] = {
        "reason": "server_said_no",
        "detail": "simulated",
        "attempted_at": "2026-07-21T12:00:00Z",
    }
    _assert_invalid(instance)


# ---------------------------------------------------------------------------
# Sanity: the base valid fixture itself must validate (guards the helper).
# ---------------------------------------------------------------------------


def test_base_valid_fixture_validates() -> None:
    _assert_valid(_base_valid_record())


def test_base_valid_fixture_is_not_mutated_by_deepcopy_helpers() -> None:
    original = _base_valid_record()
    mutated = copy.deepcopy(original)
    mutated["access"]["basis"] = "unknown"
    assert original["access"]["basis"] != "unknown"
