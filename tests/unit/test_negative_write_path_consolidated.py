"""P6-2: consolidate the two independent halves of the §9.10 negative-write-path
boundary into ONE pytest module, and add a genuine regression-guard test that
proves the combined boundary catches a leak even when one half of it regresses.

Background
----------
``test_synthesis_attestation_write_ceiling.py`` (P3-4) proves the agent-write
ban on ``synthesis.attestation.status`` via the service-layer write ceiling in
``assertion_materialization.py`` (``AssertionMaterializer._enforce_synthesis_attestation_ceiling``).

``test_rights_status_write_ceiling.py`` (P5-2) proves the agent-write ban on
the other 3 governed fields (``rights_record.overall_status``,
``content_reuse_assessment.decision.status``, ``rights_extension.clearance_status``)
via zero-construction-path proofs across 9 service/CLI modules, PLUS exercises
the governance-guard policy layer (``services.governance.guard_check`` /
rule ``no_agent_cleared_rights_value``) for those 3 fields.

Both modules pass independently today. Nothing forces them to be exercised
*together*, so either one could be accidentally marked ``skip``/``xfail`` (or
have a test silently removed) without the other file's CI signal changing at
all -- a CI job that only watches this consolidated module would not notice
unless this module itself re-verifies both halves every time it runs.

Consolidation strategy (documented per this task's instructions)
------------------------------------------------------------------
Chosen approach: **explicit sibling-module import + direct invocation**, not
a "collect and count" approach. ``tests/unit`` has no ``__init__.py``, so
pytest's default rootdir-relative ("prepend") import mode makes each test
file importable as a top-level module once its containing directory is on
``sys.path``; this module inserts that directory itself (defensively, in
case collection order would otherwise leave it absent) and imports both
sibling modules by name. This is simpler and more robust than re-implementing
or duplicating either suite's assertions, and more robust than a pure
collection-based check (e.g. asserting ``pytest.main([...])`` exit codes),
because:

1. It fails at *import time* (collection) if either sibling module is
   renamed, moved, or has a broken import -- loud, not silent.
2. ``test_flagship_proofs_from_both_suites_execute_in_one_pytest_run`` below
   directly *calls* one flagship proof function from each sibling module
   inside a single test node, so a single pytest invocation of this ONE file
   demonstrably runs both halves' core assertions together (not just that
   both files exist on disk).
3. ``test_neither_sibling_suite_has_a_skipped_or_xfailed_test`` dynamically
   introspects every ``test_*`` function defined in each sibling module (via
   ``inspect.getmembers``, not a hardcoded name list) and asserts none carry
   a ``skip``/``xfail`` pytest mark. Because the scan is dynamic, it stays
   correct if either suite gains or loses tests in the future without this
   file needing an update -- it would only need updating if the modules
   themselves are renamed.

Regression-guard test (the actual point of P6-2)
--------------------------------------------------
``test_regression_ceiling_bypass_is_still_caught_by_governance_guard_backstop``
below does not just re-run the two suites -- it simulates a genuine
regression: the P3-4 write-ceiling (``_enforce_synthesis_attestation_ceiling``)
is monkeypatched (test-scoped only, via pytest's ``monkeypatch`` fixture,
auto-reverted at teardown -- no production code is modified) down to an
identity no-op, as if a future refactor had silently broken it while leaving
the call site intact. Combined with P3-4's own ``_prepare_one`` smuggling
technique (reused, not reimplemented), this produces a *genuinely leaked*
``synthesis.attestation.status == "attested"`` value on disk -- proving the
bypass is real and the scenario is non-vacuous (if the ceiling were NOT
bypassed, P3-4's own tests already prove this can't happen).

The test then feeds that exact leaked value through the P5-2-exercised
governance-guard layer (``guard_check`` / rule ``no_agent_cleared_rights_value``,
which is one of the *same 4* ``_RIGHTS_GOVERNED_FIELDS`` -- ``synthesis.attestation.status``
is enumerated there too, see ``services/governance.py``) and asserts it is
independently blocked. This is the load-bearing proof: even with one half of
the boundary (the service-layer ceiling) simulated as broken, the OTHER half
(the governance-guard policy layer) still catches the identical disallowed
value -- demonstrating the two suites are not merely two tests of the same
single mechanism, but genuinely independent, overlapping defenses. Neither
production module is modified; the monkeypatch is scoped to this one test.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.governance import GuardContext, guard_check

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

import tests.unit.test_rights_status_write_ceiling as p5_2  # noqa: E402  (sibling suite, P5-2; package-relative for the packaged tests/ layout)
import tests.unit.test_synthesis_attestation_write_ceiling as p3_4  # noqa: E402  (sibling suite, P3-4; package-relative for the packaged tests/ layout)


# ---------------------------------------------------------------------------
# 1. Structural guard: dynamically prove neither sibling suite is
#    skipped/xfailed, without hardcoding either module's test names.
# ---------------------------------------------------------------------------


def _own_test_functions(module) -> list:
    """Every ``test_*`` function *defined in* (not merely imported into) module."""

    return [
        fn
        for name, fn in inspect.getmembers(module, inspect.isfunction)
        if name.startswith("test_") and inspect.getmodule(fn) is module
    ]


def _skip_or_xfail_mark_names(fn) -> list[str]:
    return [m.name for m in getattr(fn, "pytestmark", []) if m.name in ("skip", "xfail")]


@pytest.mark.parametrize(
    "module",
    [p3_4, p5_2],
    ids=["P3-4-synthesis-attestation-ceiling", "P5-2-rights-status-write-ceiling"],
)
def test_neither_sibling_suite_has_a_skipped_or_xfailed_test(module) -> None:
    """Fails loudly if either half of the §9.10 boundary is silently disabled.

    Dynamic (not a hardcoded function-name list): this test keeps working
    even as either sibling module gains or loses ``test_*`` functions over
    time -- it only needs updating if the modules themselves are renamed.
    """

    functions = _own_test_functions(module)
    assert functions, f"expected at least one test_* function defined in {module.__name__}"

    offenders = {fn.__name__: _skip_or_xfail_mark_names(fn) for fn in functions if _skip_or_xfail_mark_names(fn)}
    assert offenders == {}, (
        f"{module.__name__} has skip/xfail-marked test(s) -- this would silently "
        f"weaken half of the §9.10 negative-write-path boundary: {offenders}"
    )


# ---------------------------------------------------------------------------
# 2. Direct-invocation guard: prove both suites' flagship adversarial proofs
#    actually execute together inside a single pytest run of this one file.
# ---------------------------------------------------------------------------


def test_flagship_proofs_from_both_suites_execute_in_one_pytest_run(tmp_foundry, monkeypatch) -> None:
    """Calls one flagship adversarial test from each sibling module directly.

    This is stronger than a mark/collection check: it *runs* the P3-4
    materializer-smuggling proof and the P5-2 governance-guard proof inside
    the SAME test node, in the SAME pytest process, so a green result here
    is direct evidence both halves of the boundary were exercised together
    -- not merely that both files are present and collectible.
    """

    # P3-4 half: smuggled `synthesis.attestation.status: "attested"` is
    # forced back to "candidate" by the materializer's write ceiling.
    p3_4.test_prepare_one_smuggled_attestation_is_forced_to_candidate_on_materialize(tmp_foundry, monkeypatch)

    # P5-2 half: the governance-guard policy layer independently blocks
    # disallowed values on the 3 rights-clearance fields it names.
    p5_2.test_governance_guard_blocks_disallowed_values_on_the_3_covered_fields()


# ---------------------------------------------------------------------------
# 3. Regression guard (the point of P6-2): a simulated ceiling regression is
#    still caught by the OTHER half of the boundary.
# ---------------------------------------------------------------------------


def test_regression_ceiling_bypass_is_still_caught_by_governance_guard_backstop(tmp_foundry, monkeypatch) -> None:
    """Simulate the P3-4 write ceiling regressing to a no-op; prove the
    P5-2-exercised governance guard independently catches the same leak.

    Step 1 (construct the leak): monkeypatch
    ``AssertionMaterializer._prepare_one`` to smuggle an "attested" synthesis
    block (reusing P3-4's own ``_smuggle_synthesis_into`` helper verbatim --
    not reimplemented), AND monkeypatch
    ``AssertionMaterializer._enforce_synthesis_attestation_ceiling`` itself
    down to an identity pass-through, as if a future refactor had silently
    broken the ceiling's reset logic while leaving the call site in
    ``_write_immutable_assertion`` intact. Both patches are test-scoped via
    pytest's ``monkeypatch`` fixture and are reverted automatically at
    teardown -- no production code is modified.

    Step 2 (prove the leak is real): run the real ``materialize_run`` write
    path end-to-end and assert the persisted assertion on disk DOES carry
    ``attestation.status == "attested"``. This is the "genuine regression"
    half of the test -- without the ceiling-bypass patch, P3-4's own tests
    already prove this cannot happen, so a leak here is non-vacuous evidence
    the simulated regression took effect.

    Step 3 (prove the backstop): feed the exact leaked field/value pair
    through ``guard_check`` (the same governance-guard function P5-2
    exercises for the other 3 rights-clearance fields; ``synthesis.attestation.status``
    is one of the same 4 ``_RIGHTS_GOVERNED_FIELDS`` in ``services/governance.py``)
    and assert it is blocked with the ``no_agent_cleared_rights_value`` rule.
    This proves the two suites' boundaries are independent defenses: even
    with the service-layer ceiling simulated as broken, the governance-guard
    policy layer still catches the identical disallowed value.
    """

    run_id = "rf_run_p6_2_ceiling_bypass_regression"
    p3_4._setup_run(tmp_foundry, run_id)

    original_prepare_one = AssertionMaterializer._prepare_one

    def _smuggling_prepare_one(self, run_id, mapping, claim):  # noqa: ANN001
        record = original_prepare_one(self, run_id, mapping, claim)
        return p3_4._smuggle_synthesis_into(record)

    monkeypatch.setattr(AssertionMaterializer, "_prepare_one", _smuggling_prepare_one)
    # Simulate the ceiling regressing to a no-op (identity pass-through) --
    # the exact shape of bug this test is a regression guard against.
    monkeypatch.setattr(
        AssertionMaterializer,
        "_enforce_synthesis_attestation_ceiling",
        staticmethod(lambda assertion: dict(assertion)),
    )

    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    result = materializer.materialize_run(run_id)
    assert result.status == "materialized"

    persisted = p3_4._all_persisted_assertions(materializer)
    leaked = [
        a
        for a in persisted
        if a.get("synthesis", {}).get("attestation", {}).get("status") == "attested"
    ]
    assert leaked, (
        "ceiling-bypass simulation failed to produce a leaked attested value "
        "on disk -- this test would be vacuous without a genuine leak"
    )
    leaked_value = leaked[0]["synthesis"]["attestation"]["status"]
    assert leaked_value == "attested"

    # The backstop: the governance-guard policy layer, given the exact
    # leaked field/value pair, independently blocks it.
    guard_result = guard_check(
        GuardContext(proposed_field_writes=(("synthesis.attestation.status", leaked_value),))
    )
    assert guard_result.exit_code == 3
    assert "no_agent_cleared_rights_value" in {v.rule_id for v in guard_result.violations}
