"""Schema validation coverage for every Research Foundry artifact schema.

For each of the 16 distribution schemas this module builds a *minimal valid*
instance (required fields only, with correct ``const``/``enum`` values where a
required field constrains them) and asserts ``validate(...).ok`` is True, then
builds a *clearly invalid* instance (a required field removed, or a bad value
on a required ``const``) and asserts ``validate(...).ok`` is False with
non-empty ``.errors``.

Instances are built inline as plain dicts — no static fixture files. The
registry resolves the distribution ``schemas/`` directory by default, which is
exactly what we want to exercise here.
"""

from __future__ import annotations

import pytest

from research_foundry.schemas import SchemaRegistry, validate

# The 16 artifact schemas shipped under ``schemas/``. Kept explicit so the
# parametrization itself documents the expected surface; cross-checked against
# ``SchemaRegistry().names()`` in ``test_registry_lists_all_schemas``.
EXPECTED_SCHEMA_NAMES: list[str] = [
    "ccdash_event",
    "claim_ledger",
    "evidence_bundle",
    "extraction_card",
    "foundry",
    "ibom",
    "intenttree_node",
    "meatywiki_writeback",
    "raw_idea",
    "report_frontmatter",
    "research_brief",
    "research_intent",
    "review_packet",
    "routing_decision",
    "skillbom_candidate",
    "source_card",
    "swarm_plan",
]


def _valid(name: str) -> dict:
    """Return a minimal instance that satisfies ``name``'s required fields."""

    builders = {
        # required: event_id, timestamp, project
        "ccdash_event": {
            "event_id": "ccd_demo",
            "timestamp": "2026-06-13T09:41:00Z",
            "project": "Research Foundry",
        },
        # required: id, intent_id
        "claim_ledger": {
            "id": "claim_demo",
            "intent_id": "intent_demo",
        },
        # required: id, intent_id, run_id
        "evidence_bundle": {
            "id": "eb_demo",
            "intent_id": "intent_demo",
            "run_id": "run_demo",
        },
        # required: id, source_card_id
        "extraction_card": {
            "id": "extract_demo",
            "source_card_id": "src_demo",
        },
        # required: foundry (object with id, name, owner)
        "foundry": {
            "schema_version": 0.1,
            "foundry": {
                "id": "rf_demo",
                "name": "Demo Foundry",
                "owner": "Tester",
            },
        },
        # required: id, intent_id
        "ibom": {
            "id": "ibom_demo",
            "intent_id": "intent_demo",
        },
        # required: node_id, title, intent_id
        "intenttree_node": {
            "node_id": "node_demo",
            "title": "Demo Node",
            "intent_id": "intent_demo",
        },
        # required: id, evidence_bundle_id
        "meatywiki_writeback": {
            "id": "mww_demo",
            "evidence_bundle_id": "eb_demo",
        },
        # required: id, title, body
        "raw_idea": {
            "id": "raw_demo",
            "title": "Demo Idea",
            "body": "A captured idea body.",
        },
        # required: report_id, type (const research_report), title
        "report_frontmatter": {
            "report_id": "report_demo",
            "type": "research_report",
            "title": "Demo Report",
        },
        # required: id, intent_id, title
        "research_brief": {
            "id": "brief_demo",
            "intent_id": "intent_demo",
            "title": "Demo Brief",
        },
        # required: id, title, objective
        "research_intent": {
            "id": "intent_demo",
            "title": "Demo Intent",
            "objective": "Understand the demo domain.",
        },
        # required: id
        "review_packet": {
            "id": "review_demo",
        },
        # required: id, intent_id, active_node_id
        "routing_decision": {
            "id": "route_demo",
            "intent_id": "intent_demo",
            "active_node_id": "node_demo",
        },
        # required: id, name
        "skillbom_candidate": {
            "id": "skillbom_demo",
            "name": "Demo SkillBOM",
        },
        # required: source_card_id, type (const source_card), source
        "source_card": {
            "source_card_id": "src_demo",
            "type": "source_card",
            "source": {"title": "Demo Source"},
        },
        # required: id, brief_id, intent_id
        "swarm_plan": {
            "id": "swarm_demo",
            "brief_id": "brief_demo",
            "intent_id": "intent_demo",
        },
    }
    return dict(builders[name])


def _invalid(name: str) -> dict:
    """Return an instance that clearly violates ``name``'s schema.

    Most schemas constrain required fields only as strings with
    ``additionalProperties: true``, so the reliable, schema-agnostic way to
    force a failure is to drop a required field. For the two front-matter
    schemas whose required ``type`` is a ``const``, we instead supply a bad
    ``const`` value so the failure is an enum/const violation rather than a
    missing key.
    """

    instance = _valid(name)
    if name == "source_card":
        instance["type"] = "not_a_source_card"  # violates const "source_card"
        return instance
    if name == "report_frontmatter":
        instance["type"] = "not_a_report"  # violates const "research_report"
        return instance

    # Drop the first required field for every other schema.
    required_first = {
        "ccdash_event": "event_id",
        "claim_ledger": "id",
        "evidence_bundle": "id",
        "extraction_card": "id",
        "foundry": "foundry",
        "ibom": "id",
        "intenttree_node": "node_id",
        "meatywiki_writeback": "id",
        "raw_idea": "id",
        "research_brief": "id",
        "research_intent": "id",
        "review_packet": "id",
        "routing_decision": "id",
        "skillbom_candidate": "id",
        "swarm_plan": "id",
    }
    instance.pop(required_first[name], None)
    return instance


@pytest.mark.parametrize("name", EXPECTED_SCHEMA_NAMES)
def test_minimal_valid_instance_passes(name: str) -> None:
    """A minimal required-fields instance validates cleanly for each schema."""

    result = validate(_valid(name), name)
    assert result.ok, f"expected {name} minimal instance valid, got: {result.errors}"
    assert result.errors == []


@pytest.mark.parametrize("name", EXPECTED_SCHEMA_NAMES)
def test_invalid_instance_fails(name: str) -> None:
    """A clearly-invalid instance fails with non-empty errors for each schema."""

    result = validate(_invalid(name), name)
    assert not result.ok, f"expected {name} invalid instance to fail validation"
    assert result.errors, f"expected non-empty errors for invalid {name} instance"


def test_registry_lists_all_schemas() -> None:
    """The registry reports exactly the 17 expected schema names."""

    names = SchemaRegistry().names()
    assert len(names) == 17
    assert names == sorted(EXPECTED_SCHEMA_NAMES)


def test_unknown_schema_yields_error_result_not_exception() -> None:
    """An unknown schema name returns a non-ok result rather than raising."""

    result = validate({"id": "anything"}, "definitely_not_a_real_schema")
    assert not result.ok
    assert result.errors, "unknown schema should surface at least one error"
    assert result.schema == "definitely_not_a_real_schema"
