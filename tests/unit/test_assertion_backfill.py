"""P2-01a/P2-01b: claim-ledger bijection-gate tolerance and skip-and-continue
materialization.

See docs/project_plans/implementation_plans/features/
assertion-ledger-activation-v1/phase-2-backfill.md (tasks P2-01a, P2-01b, and
the "Algorithmic Test Scenario Matrix" scenarios 11-12) and
docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md ("Post-fix
re-measurement (2026-07-16)") for the defects these tests guard against:

- Defect 1c: ``claim_mapping.py::validate_extraction_fact_claim_mappings()``
  used to reject any ledger with claims appended after the fact-derived
  prefix -- which is exactly what normal report synthesis does when it
  appends ``inference``/``speculation`` claims. 39/42 real runs aborted with
  ``non_bijective_fact_claim_mapping`` before this fix.
- The all-or-nothing-per-run design: even with 1c fixed, a single abstaining
  fact used to abort the entire run's materialization. 34/42 runs would
  still have published zero assertions apiece despite eligible facts.
"""

from __future__ import annotations

import pytest

from research_foundry.services import claim_mapping, extraction
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.source_cards import ingest_source
from research_foundry.yamlio import dump_yaml, load_yaml

_PARAGRAPH_ONE = (
    "The average research task takes around 3 minutes to complete. "
    "It also costs about ten cents per run."
)
_PARAGRAPH_TWO = "A second paragraph adds unrelated context that is not quoted."
_MULTI_PARAGRAPH_CONTENT = f"{_PARAGRAPH_ONE}\n\n{_PARAGRAPH_TWO}"


def _setup_run(tmp_foundry, run_id: str, *, content: str = _MULTI_PARAGRAPH_CONTENT) -> None:
    """Create the smallest run satisfying the fact-claim mapping contract."""

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        "evidence.txt",
        run_id=run_id,
        title="Exact Evidence",
        sensitivity="personal",
        content=content,
        assertion_registry_workspace_id="workspace-a",
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)


def _ledger(tmp_foundry, run_id: str) -> dict:
    return load_yaml(tmp_foundry.run_paths(run_id).claim_ledger)


def _dump_ledger(tmp_foundry, run_id: str, ledger: dict) -> None:
    dump_yaml(ledger, tmp_foundry.run_paths(run_id).claim_ledger)


def _trailing_claim(claim_id: str, status: str) -> dict:
    """A minimal, schema-shaped trailing claim mirroring a report-synthesis
    append -- the normal, expected downstream behavior this SPIKE's own
    corpus diagnostic confirmed (588 inference + 88 speculation = 676 claims
    across the 42-run corpus, all appended after their run's fact-derived
    prefix)."""

    return {
        "claim_id": claim_id,
        "text": f"A {status} sentence not derived from any extraction fact.",
        "materiality": "background",
        "claim_type": "factual",
        "status": status,
        "confidence": "low",
        "sources": [],
        "inference_basis": {"from_claims": [], "reasoning_summary": None},
        "report_locations": [],
        "reviewer_notes": "",
    }


# ---------------------------------------------------------------------------
# P2-01a: claim-ledger bijection gate (Algorithmic Test Scenario Matrix #11)
# ---------------------------------------------------------------------------


def test_legitimate_trailing_inference_and_speculation_claims_do_not_raise(tmp_foundry) -> None:
    """The normal, expected 39/42-run case: the fact-derived prefix is intact
    and only inference/speculation claims are appended after it. Must NOT
    raise ``non_bijective_fact_claim_mapping``.
    """

    run_id = "rf_run_p2_01a_legit_trailing"
    _setup_run(tmp_foundry, run_id)
    ledger = _ledger(tmp_foundry, run_id)
    assert len(ledger["claims"]) == 2
    ledger["claims"].append(_trailing_claim("clm_003", "inference"))
    ledger["claims"].append(_trailing_claim("clm_004", "speculation"))
    _dump_ledger(tmp_foundry, run_id, ledger)

    mappings = claim_mapping.validate_extraction_fact_claim_mappings(run_id, ledger, paths=tmp_foundry)

    assert len(mappings) == 2


@pytest.mark.parametrize("tamper", ["modified", "reordered", "deleted"])
def test_tampered_fact_derived_prefix_still_raises_alongside_legitimate_trailing_claims(
    tmp_foundry, tamper: str
) -> None:
    """Adversarial fixture: a modified/reordered/deleted claim INSIDE the
    fact-derived prefix, alongside legitimate trailing inference/speculation
    claims, must still raise ``non_bijective_fact_claim_mapping`` -- the
    trailing-claim tolerance must not weaken the prefix's integrity
    guarantee.
    """

    run_id = f"rf_run_p2_01a_tampered_{tamper}"
    _setup_run(tmp_foundry, run_id)
    ledger = _ledger(tmp_foundry, run_id)
    assert len(ledger["claims"]) == 2

    if tamper == "modified":
        ledger["claims"][0]["text"] = "Tampered claim text inside the fact-derived prefix."
    elif tamper == "reordered":
        ledger["claims"][0], ledger["claims"][1] = ledger["claims"][1], ledger["claims"][0]
    else:  # deleted
        del ledger["claims"][0]

    ledger["claims"].append(_trailing_claim("clm_099", "inference"))
    _dump_ledger(tmp_foundry, run_id, ledger)

    with pytest.raises(ValueError, match="non_bijective_fact_claim_mapping"):
        claim_mapping.validate_extraction_fact_claim_mappings(run_id, ledger, paths=tmp_foundry)


def test_trailing_non_inference_speculation_claim_still_raises(tmp_foundry) -> None:
    """A trailing claim typed anything other than inference/speculation (e.g.
    a smuggled extra 'supported' claim) still raises the bijection error --
    the tolerance is narrowly scoped to those two statuses only.
    """

    run_id = "rf_run_p2_01a_smuggled_trailing"
    _setup_run(tmp_foundry, run_id)
    ledger = _ledger(tmp_foundry, run_id)
    ledger["claims"].append(_trailing_claim("clm_099", "supported"))
    _dump_ledger(tmp_foundry, run_id, ledger)

    with pytest.raises(ValueError, match="non_bijective_fact_claim_mapping"):
        claim_mapping.validate_extraction_fact_claim_mappings(run_id, ledger, paths=tmp_foundry)


def test_ledger_shorter_than_fact_derived_mappings_still_raises(tmp_foundry) -> None:
    """Fewer claims than fact-derived mappings (no trailing suffix to even
    consider) is still non-bijective -- guards against a length-only relaxed
    check accidentally accepting truncated ledgers.
    """

    run_id = "rf_run_p2_01a_too_short"
    _setup_run(tmp_foundry, run_id)
    ledger = _ledger(tmp_foundry, run_id)
    del ledger["claims"][1]
    _dump_ledger(tmp_foundry, run_id, ledger)

    with pytest.raises(ValueError, match="non_bijective_fact_claim_mapping"):
        claim_mapping.validate_extraction_fact_claim_mappings(run_id, ledger, paths=tmp_foundry)


# ---------------------------------------------------------------------------
# P2-01b: skip-and-continue materialization (Algorithmic Test Scenario
# Matrix #12)
# ---------------------------------------------------------------------------


def test_mixed_materializable_and_abstaining_facts_publishes_subset_without_aborting(
    tmp_foundry,
) -> None:
    """A run with >=2 facts where >=1 materializes and >=1 abstains must
    publish the materializable subset and record the abstention in the
    receipt -- not abort the entire run.

    The abstaining fact is forced via a deferred ``canonical_claim_id`` on
    its own claim only (mirrors ``test_canonical_candidate_abstains_...`` in
    test_assertion_materialization.py) rather than mutating the shared
    source card: both facts here bind to the same source card, and mutating
    any one of its evidence points changes the whole card's registered
    snapshot (``AssertionRegistry.verify_source_card_binding`` hashes every
    point together), which would abstain *both* facts with
    ``registry_integrity_rejected`` instead of isolating the abstention to
    one fact.
    """

    run_id = "rf_run_p2_01b_mixed"
    _setup_run(tmp_foundry, run_id)
    ledger = _ledger(tmp_foundry, run_id)
    assert len(ledger["claims"]) == 2
    ledger["claims"][1]["persistent_references"] = {"canonical_claim_id": "ccl_deferred"}
    _dump_ledger(tmp_foundry, run_id, ledger)

    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    result = materializer.materialize_run(run_id)

    assert result.status == "materialized"
    assert result.claim_ids == ("clm_001",)
    assert len(result.assertion_ids) == 1
    assert len(result.abstained_claims) == 1
    assert result.abstained_claims[0].claim_id == "clm_002"
    assert result.abstained_claims[0].code == "canonical_or_inference_candidate_deferred"


def test_all_facts_abstaining_completes_with_full_abstention_receipt_without_raising(
    tmp_foundry,
) -> None:
    """A run where every fact individually abstains (>=2 facts) still
    completes -- a 100% abstention receipt, never a raised exception.
    """

    run_id = "rf_run_p2_01b_all_abstain"
    _setup_run(tmp_foundry, run_id)
    ledger = _ledger(tmp_foundry, run_id)
    for claim in ledger["claims"]:
        claim["persistent_references"] = {"canonical_claim_id": "ccl_deferred"}
    _dump_ledger(tmp_foundry, run_id, ledger)

    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)

    result = materializer.materialize_run(run_id)

    assert result.status == "abstained"
    assert result.assertion_ids == ()
    assert result.abstention_code is None  # multi-fact breakdown, no single code
    assert len(result.abstained_claims) == 2
    assert {item.code for item in result.abstained_claims} == {
        "canonical_or_inference_candidate_deferred"
    }
    assert not (materializer.root / "assertions").exists()


def test_mixed_outcome_is_idempotent_on_replay(tmp_foundry) -> None:
    """Re-running a mixed materialize/abstain run must not raise and must
    reproduce the same materialized subset and abstention breakdown --
    skip-and-continue must not defeat the existing reuse/replay contract.
    """

    run_id = "rf_run_p2_01b_mixed_replay"
    _setup_run(tmp_foundry, run_id)
    ledger = _ledger(tmp_foundry, run_id)
    ledger["claims"][1]["persistent_references"] = {"canonical_claim_id": "ccl_deferred"}
    _dump_ledger(tmp_foundry, run_id, ledger)
    materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)

    first = materializer.materialize_run(run_id)
    second = materializer.materialize_run(run_id)

    assert first.status == "materialized"
    assert second.status == "reused"
    assert first.assertion_ids == second.assertion_ids
    assert first.abstained_claims == second.abstained_claims
