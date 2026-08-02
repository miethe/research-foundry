"""Narrow unit coverage for the M3 defence-in-depth attribution guard (SMP-3.1/3.2).

Scope: the ``no_agent_authored_attribution_value`` rule and the 2 attribution
entries appended to ``_RIGHTS_GOVERNED_FIELDS``. This module does NOT own the
negative-test suite for the structural/primary control (schema if/then,
SMP-3.2B) or the sibling-field-bypass proof (SMP-3.3B) — those live in
``tests/test_governance_adversarial.py`` (SMP-3.3/3.3B, a separate task).
This file only locks in that the new rule fires the way rule 7
(``no_agent_cleared_rights_value``) already does, and stays inert otherwise.
"""

from __future__ import annotations

from research_foundry.services.governance import GuardContext, guard_check


def _ids(result) -> set[str]:
    return {v.rule_id for v in result.violations}


def test_fires_for_cleared_value_on_attribution_asserter_type():
    r = guard_check(
        GuardContext(proposed_field_writes=(("source_attribution.asserter_type", "CLEARED_FAIR_USE"),))
    )
    assert r.exit_code == 3
    assert "no_agent_authored_attribution_value" in _ids(r)


def test_fires_for_attested_value_on_attribution_license_basis():
    r = guard_check(
        GuardContext(proposed_field_writes=(("source_attribution.license_basis", "attested"),))
    )
    assert r.exit_code == 3
    assert "no_agent_authored_attribution_value" in _ids(r)


def test_passes_for_legitimate_enum_value_on_attribution_fields():
    r = guard_check(
        GuardContext(
            proposed_field_writes=(
                ("source_attribution.asserter_type", "third_party_api"),
                ("source_attribution.license_basis", "open_api"),
            )
        )
    )
    assert r.exit_code == 0
    assert "no_agent_authored_attribution_value" not in _ids(r)


def test_sibling_field_bypass_is_not_caught_by_this_rule():
    """Documents the exact miss the plan calls out: a name list is blind to a
    sibling field it never enumerated. This is the reason SMP-3.2B's schema
    shape, not this rule, is the primary M3 control.
    """

    r = guard_check(
        GuardContext(proposed_field_writes=(("trust.third_party_citation_rank", "CLEARED_FAIR_USE"),))
    )
    assert r.exit_code == 0
    assert "no_agent_authored_attribution_value" not in _ids(r)
    assert "no_agent_cleared_rights_value" not in _ids(r)
