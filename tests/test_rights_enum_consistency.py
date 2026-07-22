"""Enum-consistency sweep for the rights/evidence entity schemas (P6-1).

Formalizes the byte-identical / value-set-equivalence guarantees called out
across ``schemas/rights_record.schema.yaml``,
``schemas/content_reuse_assessment.schema.yaml``, and
``schemas/rights_extension.schema.yaml`` by the §9 adjudications recorded in
those files (§9.5, §9.7, §9.8) and seeded in
``tests/test_rights_record_schema_fixtures.py`` (P0-3/P2-2). Those fixture
tests prove individual values round-trip; this module proves the *shared
enums stay identical* over time.

Deliberately reads the **live** schema dicts via
``research_foundry.schemas.SchemaRegistry`` (the same loader the runtime
validator uses) rather than hardcoding duplicate enum lists here — any edit
to one schema file without a matching edit to its paired schema(s) fails
this module immediately, with the actual differing members in the assertion
message. No ``pytest.skip`` / ``pytest.mark.skip`` anywhere in this file:
missing schemas or missing enum paths must raise (``KeyError``/
``FileNotFoundError``), not be silently skipped.
"""

from __future__ import annotations

from typing import Any

from research_foundry.schemas import SchemaRegistry

_registry = SchemaRegistry()


def _schema(name: str) -> dict[str, Any]:
    """Load the live schema dict by name. Raises loudly if missing."""

    return _registry.get(name)


def _enum_at(schema: dict[str, Any], *path: str) -> list[str]:
    """Navigate ``schema`` through nested ``properties``/``items`` keys and
    return the ``enum`` list at ``path``. Uses direct dict indexing (no
    ``.get`` defaults) so a renamed/removed field raises ``KeyError``
    immediately instead of silently resolving to an empty list that would
    make a downstream equality assertion vacuously pass.
    """

    node: Any = schema
    for key in path:
        if key == "[]":
            node = node["items"]
        else:
            node = node["properties"][key]
    return node["enum"]


# ---------------------------------------------------------------------------
# 1. overall_status value-set == union(decision.status, clearance_status)
# ---------------------------------------------------------------------------
#
# rights_record.overall_status and content_reuse_assessment.decision.status
# are the same 12-member set (§9.5 locked: OWNED added for first-party
# records). rights_extension.clearance_status (no OWNED member — a rights
# container never represents first-party ownership) is a strict subset of
# that same set. The invariant is therefore value-set equivalence between
# overall_status and the union of the other two, not identical field names
# or identical member counts.


def test_overall_status_equals_union_of_decision_status_and_clearance_status() -> None:
    rights_record = _schema("rights_record")
    content_reuse_assessment = _schema("content_reuse_assessment")
    rights_extension = _schema("rights_extension")

    overall_status = set(_enum_at(rights_record, "overall_status"))
    decision_status = set(_enum_at(content_reuse_assessment, "decision", "status"))
    clearance_status = set(_enum_at(rights_extension, "clearance_status"))

    union_of_pair = decision_status | clearance_status

    assert overall_status == union_of_pair, (
        "rights_record.overall_status must equal the union of "
        "content_reuse_assessment.decision.status and "
        "rights_extension.clearance_status.\n"
        f"overall_status only: {sorted(overall_status - union_of_pair)}\n"
        f"union only:          {sorted(union_of_pair - overall_status)}"
    )

    # clearance_status must remain a subset of decision_status (its known
    # divergence is the absent OWNED member) — if a future edit adds a
    # clearance_status member that decision_status lacks, that's a new
    # unmodeled overall_status-shaped value and must be caught here too.
    assert clearance_status <= decision_status, (
        "rights_extension.clearance_status has member(s) not present in "
        f"content_reuse_assessment.decision.status: "
        f"{sorted(clearance_status - decision_status)}"
    )


# ---------------------------------------------------------------------------
# 2. review_status byte-identical: rights_record.review vs.
#    content_reuse_assessment.review (§9.7 locked)
# ---------------------------------------------------------------------------


def test_review_status_byte_identical_rights_record_vs_content_reuse_assessment() -> None:
    rights_record = _schema("rights_record")
    content_reuse_assessment = _schema("content_reuse_assessment")

    rr_review_status = _enum_at(rights_record, "review", "review_status")
    cra_review_status = _enum_at(content_reuse_assessment, "review", "review_status")

    assert rr_review_status == cra_review_status, (
        "review.review_status enum drifted between rights_record.schema.yaml "
        "and content_reuse_assessment.schema.yaml (§9.7 requires a byte-"
        "identical literal list — order included).\n"
        f"rights_record:               {rr_review_status}\n"
        f"content_reuse_assessment:    {cra_review_status}"
    )


# ---------------------------------------------------------------------------
# 3. component_type byte-identical: rights_record.component_decisions[] vs.
#    content_reuse_assessment.component (§9.8 locked)
# ---------------------------------------------------------------------------


def test_component_type_byte_identical_rights_record_vs_content_reuse_assessment() -> None:
    rights_record = _schema("rights_record")
    content_reuse_assessment = _schema("content_reuse_assessment")

    rr_component_type = _enum_at(rights_record, "component_decisions", "[]", "component_type")
    cra_component_type = _enum_at(content_reuse_assessment, "component", "component_type")

    assert rr_component_type == cra_component_type, (
        "component_type enum drifted between "
        "rights_record.schema.yaml#component_decisions[].component_type and "
        "content_reuse_assessment.schema.yaml#component.component_type "
        "(§9.8 requires a byte-identical singular vocabulary — order "
        "included).\n"
        f"rights_record.component_decisions[]:  {rr_component_type}\n"
        f"content_reuse_assessment.component:   {cra_component_type}"
    )
