"""Unit tests for the ``verify.exact_passage`` config key + CLI override plumbing.

TASK-2.1 (RFUP-3, decisions-block OQ-1) is plumbing-only: a config default in
``config/claim_policy.yaml``, a resolver function, and a run-level CLI override
that beats the config value. TASK-2.2 wires the actual eligibility check on top
of the resolved mode — these tests only cover resolution/precedence, not any
exact-passage matching behavior.
"""

from __future__ import annotations

import copy

import pytest

from research_foundry.errors import ExitCode, RFError
from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services.synthesis import synthesize_report
from research_foundry.services.verification import resolve_exact_passage_mode, verify_report
from research_foundry.yamlio import dump_yaml, load_yaml

RUN_ID = "rf_run_20260613_exact_passage_demo"


def _set_claim_policy_verify_block(paths: FoundryPaths, verify_block: dict | None) -> None:
    """Overwrite ``config/claim_policy.yaml``'s top-level ``verify`` key.

    Passing ``None`` removes the key entirely (simulating an old workspace
    that predates this feature, for the backward-compat default test).
    """

    policy_path = paths.config / "claim_policy.yaml"
    policy = load_yaml(policy_path)
    assert isinstance(policy, dict)
    if verify_block is None:
        policy.pop("verify", None)
    else:
        policy["verify"] = verify_block
    dump_yaml(policy, policy_path)


def test_config_default_is_warn_when_no_verify_section(tmp_foundry):
    """Backward compat: a workspace with no ``verify:`` block at all defaults to warn."""

    _set_claim_policy_verify_block(tmp_foundry, None)
    assert resolve_exact_passage_mode(tmp_foundry) == "warn"


def test_config_value_strict_is_honored_with_no_override(tmp_foundry):
    _set_claim_policy_verify_block(tmp_foundry, {"exact_passage": "strict"})
    assert resolve_exact_passage_mode(tmp_foundry) == "strict"


def test_config_value_warn_is_honored_with_no_override(tmp_foundry):
    _set_claim_policy_verify_block(tmp_foundry, {"exact_passage": "warn"})
    assert resolve_exact_passage_mode(tmp_foundry) == "warn"


def test_cli_override_strict_wins_over_config_warn(tmp_foundry):
    """CLI beats config per OQ-1: config says warn, override says strict -> strict."""

    _set_claim_policy_verify_block(tmp_foundry, {"exact_passage": "warn"})
    assert resolve_exact_passage_mode(tmp_foundry, override="strict") == "strict"


def test_cli_override_warn_wins_over_config_strict(tmp_foundry):
    """CLI beats config per OQ-1, in the other direction: config says strict,
    override says warn -> warn."""

    _set_claim_policy_verify_block(tmp_foundry, {"exact_passage": "strict"})
    assert resolve_exact_passage_mode(tmp_foundry, override="warn") == "warn"


def test_cli_override_is_case_insensitive(tmp_foundry):
    _set_claim_policy_verify_block(tmp_foundry, {"exact_passage": "warn"})
    assert resolve_exact_passage_mode(tmp_foundry, override="STRICT") == "strict"


def test_invalid_override_raises_rferror(tmp_foundry):
    """A bad --exact-passage value must fail closed, not silently fall back."""

    with pytest.raises(RFError):
        resolve_exact_passage_mode(tmp_foundry, override="loose")


def test_missing_or_invalid_config_value_defaults_to_warn(tmp_foundry):
    """An invalid config value (not warn/strict) must never regress to something
    other than the safe default."""

    _set_claim_policy_verify_block(tmp_foundry, {"exact_passage": "bogus"})
    assert resolve_exact_passage_mode(tmp_foundry) == "warn"


def test_verify_report_threads_override_into_result(tmp_foundry):
    """End-to-end: verify_report's exact_passage_override reaches the result,
    winning over the config default, confirming the CLI wiring in
    cli_commands.py resolves to the same precedence as the unit-level resolver.
    """

    _set_claim_policy_verify_block(tmp_foundry, {"exact_passage": "warn"})
    result = verify_report(RUN_ID, paths=tmp_foundry, exact_passage_override="strict")
    assert result.exact_passage_mode == "strict"


def test_verify_report_defaults_to_config_when_no_override(tmp_foundry):
    _set_claim_policy_verify_block(tmp_foundry, {"exact_passage": "strict"})
    result = verify_report(RUN_ID, paths=tmp_foundry)
    assert result.exact_passage_mode == "strict"


# --- TASK-2.2: exact_passage_present eligibility check -----------------------
#
# PRD FR-3.1 / AC-RFUP3-1 / AC-RFUP3-2: a supported claim citing a source card
# should have an exact-passage (quoted) anchor on that card
# (extracted_points[].quote), not merely a locator. warn (default) mode is
# informational only; strict mode blocks publish exactly like an unsupported
# claim.

_EXACT_RUN_ID = "rf_run_20260613_exact_passage_check"
_EXACT_INTENT_ID = "intent_research_20260613_exact_passage_check"
_EXACT_SOURCE_ID = "src_20260613_exactpassage_aaaaaaaa"

_EXACT_LEDGER = {
    "id": "claim_ledger_exact_passage_check",
    "intent_id": _EXACT_INTENT_ID,
    "verification_status": "pending",
    "claims": [
        {
            "claim_id": "clm_100",
            "text": "PaperQA2 supports scientific PDF ingestion",
            "materiality": "material",
            "claim_type": "factual",
            "status": "supported",
            "confidence": "high",
            "sources": [
                {
                    "source_card_id": _EXACT_SOURCE_ID,
                    "evidence_id": "ev_100",
                    "relation": "supports",
                    "locator": "p.3",
                }
            ],
        }
    ],
}


def _write_exact_intent(paths: FoundryPaths) -> None:
    intent = {
        "id": _EXACT_INTENT_ID,
        "title": "Exact-passage demo intent",
        "type": "research",
        "status": "active",
        "governance": {"sensitivity": "personal", "requires_human_review": False},
        "output": {"audience": "technical"},
    }
    dump_yaml(intent, paths.intents_active / f"{_EXACT_INTENT_ID}.yaml")


def _write_exact_ledger(paths: FoundryPaths, ledger: dict) -> None:
    rp = paths.run_paths(_EXACT_RUN_ID)
    rp.ensure_scaffold()
    dump_yaml(ledger, rp.claim_ledger)


def _write_exact_source_card(paths: FoundryPaths, *, quote: str | None) -> None:
    """A source card with a locator, and — when *quote* is given — a matching
    ``extracted_points[].quote`` (an exact-passage anchor)."""

    rp = paths.run_paths(_EXACT_RUN_ID)
    rp.ensure_scaffold()
    front: dict = {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": _EXACT_SOURCE_ID,
        "created_at": "2026-06-13T09:41:00-04:00",
        "created_by_agent": "researcher",
        "sensitivity": "personal",
        "source": {
            "title": "Exact passage source",
            "source_type": "paper",
            "locator": {"url": "https://example.org/paper", "file_path": None},
            "authors": ["A. Author"],
            "accessed_at": "2026-06-13T09:41:00-04:00",
        },
    }
    if quote is not None:
        front["extracted_points"] = [
            {
                "evidence_id": "ev_100",
                "locator": "p.3",
                "summary": "Supporting passage",
                "quote": quote,
            }
        ]
    dump_md(
        front,
        "# Exact passage source\n\nSummary of exact passage source.\n",
        rp.sources / f"{_EXACT_SOURCE_ID}.md",
    )


def _seed_exact_run(paths: FoundryPaths, *, with_quote: bool) -> None:
    _write_exact_intent(paths)
    _write_exact_ledger(paths, copy.deepcopy(_EXACT_LEDGER))
    _write_exact_source_card(
        paths,
        quote="The system supports scientific PDF ingestion." if with_quote else None,
    )


def test_missing_quote_anchor_warns_by_default(tmp_foundry):
    """AC-RFUP3-1/2: default (warn) mode surfaces a warning but leaves
    passed/exit_code COMPLETELY unchanged for a claim citing a source card
    with no extracted_points/quote."""

    _seed_exact_run(tmp_foundry, with_quote=False)
    synthesize_report(_EXACT_RUN_ID, paths=tmp_foundry)

    result = verify_report(_EXACT_RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}

    assert result.exact_passage_mode == "warn"
    assert by_id["exact_passage_present"].status == "warn"
    assert "clm_100" in by_id["exact_passage_present"].locations
    assert result.passed is True
    assert result.exit_code == int(ExitCode.OK)
    assert not any("clm_100" in u for u in result.unsupported)


def test_missing_quote_anchor_blocks_in_strict_mode(tmp_foundry):
    """AC-RFUP3-1/2: strict mode treats the same missing anchor as a failure
    that blocks publish — added to unsupported[], nonzero exit code."""

    _seed_exact_run(tmp_foundry, with_quote=False)
    synthesize_report(_EXACT_RUN_ID, paths=tmp_foundry)

    result = verify_report(_EXACT_RUN_ID, paths=tmp_foundry, exact_passage_override="strict")
    by_id = {c.id: c for c in result.checks}

    assert result.exact_passage_mode == "strict"
    assert by_id["exact_passage_present"].status == "fail"
    assert "clm_100" in by_id["exact_passage_present"].locations
    assert result.passed is False
    assert result.exit_code == int(ExitCode.UNSUPPORTED)
    assert any("clm_100" in u for u in result.unsupported)


def test_quote_anchor_present_passes_in_both_modes(tmp_foundry):
    """A claim whose cited source card DOES carry a matching quote passes the
    check regardless of exact_passage_mode."""

    _seed_exact_run(tmp_foundry, with_quote=True)
    synthesize_report(_EXACT_RUN_ID, paths=tmp_foundry)

    warn_result = verify_report(_EXACT_RUN_ID, paths=tmp_foundry)
    assert {c.id: c for c in warn_result.checks}["exact_passage_present"].status == "pass"
    assert warn_result.passed is True

    strict_result = verify_report(
        _EXACT_RUN_ID, paths=tmp_foundry, exact_passage_override="strict"
    )
    assert {c.id: c for c in strict_result.checks}["exact_passage_present"].status == "pass"
    assert strict_result.passed is True


def test_source_cards_have_locators_check_is_independent_of_exact_passage(tmp_foundry):
    """The pre-existing locator check stays its own, unaffected check: it still
    only warns on a MISSING locator, regardless of exact-passage anchor
    presence or exact_passage_mode."""

    _seed_exact_run(tmp_foundry, with_quote=False)
    synthesize_report(_EXACT_RUN_ID, paths=tmp_foundry)

    result = verify_report(_EXACT_RUN_ID, paths=tmp_foundry, exact_passage_override="strict")
    by_id = {c.id: c for c in result.checks}
    # The source card has a locator (url set) -> source_cards_have_locators still
    # passes even though exact_passage_present fails in strict mode.
    assert by_id["source_cards_have_locators"].status == "pass"
    assert by_id["exact_passage_present"].status == "fail"


# --- TASK-2.3: dedicated exact_passage_violations field ----------------------
#
# PRD FR-3.3/FR-3.4, AC-RFUP3-4/AC-RFUP3-5: verify output carries its own
# ``exact_passage_violations`` list (claim ids missing an anchor), populated
# regardless of warn/strict mode, and distinct from the
# source_cards_have_locators check's own CheckResult.locations. It must be
# optional/absent-safe for downstream consumers.


def test_exact_passage_violations_populated_in_warn_mode(tmp_foundry):
    """Warn mode still surfaces the dedicated violation list, even though it
    does not block publish — this is the whole point of AC-RFUP3-4: warn-mode
    users get visibility into which claims lack anchors."""

    _seed_exact_run(tmp_foundry, with_quote=False)
    synthesize_report(_EXACT_RUN_ID, paths=tmp_foundry)

    result = verify_report(_EXACT_RUN_ID, paths=tmp_foundry)

    assert result.exact_passage_mode == "warn"
    assert result.exact_passage_violations == ["clm_100"]
    assert result.passed is True  # unchanged despite non-empty violation list

    persisted = load_yaml(tmp_foundry.run_paths(_EXACT_RUN_ID).verification)
    assert persisted["exact_passage_violations"] == ["clm_100"]


def test_exact_passage_violations_populated_in_strict_mode_too(tmp_foundry):
    """Same population, strict mode: the dedicated list is not a strict-only
    artifact — it fires identically in both modes (only passed/exit_code and
    the exact_passage_present CheckResult.status differ by mode)."""

    _seed_exact_run(tmp_foundry, with_quote=False)
    synthesize_report(_EXACT_RUN_ID, paths=tmp_foundry)

    result = verify_report(_EXACT_RUN_ID, paths=tmp_foundry, exact_passage_override="strict")

    assert result.exact_passage_mode == "strict"
    assert result.exact_passage_violations == ["clm_100"]
    assert result.passed is False


def test_exact_passage_violations_empty_when_no_violations(tmp_foundry):
    """AC-RFUP3-5: zero violations -> empty list (not omitted, matching this
    dict's existing convention for optional list fields like ``unsupported``)."""

    _seed_exact_run(tmp_foundry, with_quote=True)
    synthesize_report(_EXACT_RUN_ID, paths=tmp_foundry)

    result = verify_report(_EXACT_RUN_ID, paths=tmp_foundry)

    assert result.exact_passage_violations == []

    persisted = load_yaml(tmp_foundry.run_paths(_EXACT_RUN_ID).verification)
    assert persisted["exact_passage_violations"] == []


def test_exact_passage_violations_distinct_from_locator_check_locations(tmp_foundry):
    """The dedicated list must never be conflated with
    source_cards_have_locators's own CheckResult.locations — a source card can
    have a locator (so that check passes) while still lacking a quote anchor
    (so exact_passage_violations is non-empty)."""

    _seed_exact_run(tmp_foundry, with_quote=False)
    synthesize_report(_EXACT_RUN_ID, paths=tmp_foundry)

    result = verify_report(_EXACT_RUN_ID, paths=tmp_foundry)
    by_id = {c.id: c for c in result.checks}

    assert by_id["source_cards_have_locators"].status == "pass"
    assert by_id["source_cards_have_locators"].locations == []
    assert result.exact_passage_violations == ["clm_100"]


def test_exact_passage_violations_field_is_absent_safe_for_downstream_consumers(tmp_foundry):
    """AC-RFUP3-5 resilience: a consumer built before this feature existed —
    keyword-constructing VerificationResult without exact_passage_violations,
    or reading it via .get() off a dict that predates this key — must not
    raise KeyError/AttributeError/TypeError."""

    from research_foundry.services.verification import VerificationResult

    legacy = VerificationResult(
        run_id="rf_run_legacy",
        passed=True,
        exit_code=0,
        checks=[],
        verification_path=tmp_foundry.run_paths(_EXACT_RUN_ID).verification,
        unsupported=[],
    )
    assert legacy.exact_passage_violations == []

    legacy_record: dict = {"run_id": "rf_run_legacy", "passed": True}
    assert legacy_record.get("exact_passage_violations", []) == []


# --- TASK-2.3: real-corpus / existing-fixture zero-regression gate -----------
#
# AC-RFUP3-3: warn (default) mode engaging the exact_passage_present check
# must never change passed/exit_code for any pre-existing fixture. This
# worktree has no live 2,835-assertion backfill corpus mounted (data-plane
# split — see project memory: run/report data lives in a private
# research-foundry-data repo, not this worktree). In its place this test
# reuses the largest existing multi-claim/multi-source-card fixture already in
# the test suite (test_claim_verifier.LEDGER: 2 supported claims each citing
# their own source card, plus an inference and a speculation claim) and
# asserts the verify_report outcome is byte-for-byte identical to what
# test_claim_verifier.test_synthesize_then_verify_passes already asserts for
# this exact fixture pre-feature: passed=True, exit_code=OK.
import tests.test_claim_verifier as _tcv  # noqa: E402 - deliberate cross-fixture reuse (package-relative for the packaged tests/ layout)


def test_exact_passage_default_mode_zero_regression_on_existing_fixtures(tmp_foundry):
    """Default (warn) mode must be a strict no-op on passed/exit_code for the
    existing test_claim_verifier happy-path corpus (2 supported claims across
    2 source cards, neither carrying a quote anchor) — even though the new
    check now actively engages and flags both claims."""

    _tcv._seed_happy_run(tmp_foundry)
    synthesize_report(_tcv.RUN_ID, paths=tmp_foundry)

    result = verify_report(_tcv.RUN_ID, paths=tmp_foundry)

    # Zero-regression gate (AC-RFUP3-3): identical to the pre-existing
    # baseline in test_claim_verifier.test_synthesize_then_verify_passes.
    assert result.passed is True
    assert result.exit_code == int(ExitCode.OK)

    # Confirm the new check is genuinely engaged (not silently skipped) and
    # surfaces both claims via the dedicated field, in warn-only fashion.
    by_id = {c.id: c for c in result.checks}
    assert by_id["exact_passage_present"].status == "warn"
    assert sorted(result.exact_passage_violations) == ["clm_001", "clm_002"]
