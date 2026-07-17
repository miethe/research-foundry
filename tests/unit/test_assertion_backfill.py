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

from research_foundry.frontmatter import dump_md, load_md
from research_foundry.services import assertion_rollout as rollout
from research_foundry.services import claim_mapping, extraction
from research_foundry.services.assertion_materialization import (
    AssertionMaterializer,
    MaterializationInterrupted,
)
from research_foundry.services.assertion_registry import AssertionRegistry
from research_foundry.services.assertion_rollout import BackfillConflict
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


def _setup_historical_run(tmp_foundry, run_id: str, *, content: str = _MULTI_PARAGRAPH_CONTENT) -> str:
    """A run whose source card was ingested WITHOUT
    ``assertion_registry_workspace_id`` -- the historical, pre-P1 corpus shape
    P2's backfill driver targets (unlike ``_setup_run`` above, which wires the
    forward path at ingest time for P2-01a/P2-01b's materializer-focused
    tests). No ``assertion_ledger/`` data exists for this run until
    ``backfill_run()``/``backfill_corpus()`` populates it. Returns the
    ingested source_card_id.
    """

    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    source = ingest_source(
        "evidence.txt",
        run_id=run_id,
        title="Exact Evidence",
        sensitivity="personal",
        content=content,
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)
    return source.source_card_id


def _setup_historical_run_with_points(tmp_foundry, run_id: str, points: list[dict]) -> str:
    """A historical run (see :func:`_setup_historical_run`) whose single
    source card's ``extracted_points`` are exactly as given -- lets a test
    control each point's ``summary``/``quote`` pair independently of
    ``source_cards.py::_build_points()``'s deterministic derivation from raw
    content. Returns the source_card_id.
    """

    source_card_id = _setup_historical_run_no_extract(tmp_foundry, run_id)
    card_path = tmp_foundry.run_paths(run_id).sources / f"{source_card_id}.md"
    metadata, body = load_md(card_path)
    metadata["extracted_points"] = points
    dump_md(metadata, body, card_path)
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)
    return source_card_id


def _setup_historical_run_no_extract(tmp_foundry, run_id: str) -> str:
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)
    tmp_foundry.run_paths(run_id).ensure_scaffold()
    source = ingest_source(
        "evidence.txt",
        run_id=run_id,
        title="Exact Evidence",
        sensitivity="personal",
        content=_MULTI_PARAGRAPH_CONTENT,
        paths=tmp_foundry,
    )
    return source.source_card_id


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


# ---------------------------------------------------------------------------
# P2-02: backfill_run()/backfill_corpus() write-path driver
# ---------------------------------------------------------------------------


def test_backfill_run_ingests_source_cards_and_materializes_exact_facts(tmp_foundry) -> None:
    """Algorithmic Test Scenario Matrix #8 (happy path), driven through the
    backfill driver rather than a directly-constructed AssertionMaterializer:
    a historical run (no assertion_registry_workspace_id at ingest) is fully
    reconstructed and materialized in one call.
    """

    run_id = "rf_run_p2_02_exact"
    _setup_historical_run(tmp_foundry, run_id)
    assert not (tmp_foundry.root / "assertion_ledger").exists()

    receipt = rollout.backfill_run(run_id, workspace_id="default", paths=tmp_foundry)

    assert receipt["workspace_id"] == "default"
    assert receipt["materialization_status"] == "materialized"
    assert receipt["materialized_count"] == 2
    assert receipt["abstained_count"] == 0
    assert receipt["abstention_breakdown"] == {}
    assert receipt["fuzzy_recovery_candidates"] == []
    assert receipt["source_cards"] == {
        "created": 1,
        "reused": 0,
        "skipped_no_quotes": 0,
        "not_reusable": 0,
    }
    ledger = _ledger(tmp_foundry, run_id)
    assert all(claim.get("persistent_references") for claim in ledger["claims"])


def test_backfill_run_writes_receipt_under_workspace_backfill_operations(tmp_foundry) -> None:
    run_id = "rf_run_p2_02_receipt_path"
    _setup_historical_run(tmp_foundry, run_id)
    registry = AssertionRegistry(workspace_id="default", paths=tmp_foundry)

    receipt = rollout.backfill_run(run_id, workspace_id="default", paths=tmp_foundry)

    receipt_path = registry.root / "backfill_operations" / f"{run_id}.yaml"
    assert receipt_path.is_file()
    assert load_yaml(receipt_path) == receipt


def test_backfill_produces_same_assertion_record_shape_as_forward_write(tmp_foundry) -> None:
    """P2-03 seam self-check: confirm the backfill driver's writes are
    byte-identical in shape to what ``AssertionRegistry.ingest()``/
    ``AssertionMaterializer.materialize_run()`` already produce for forward
    writes -- no divergent "backfill-only" write path is introduced.
    ``assertion_rollout.py`` calls those two public methods directly and
    never constructs an assertion/edition/passage record itself.
    """

    forward_run_id = "rf_run_p2_03_forward"
    _setup_run(tmp_foundry, forward_run_id)  # forward path: wired at ingest time
    forward_materializer = AssertionMaterializer(workspace_id="workspace-a", paths=tmp_foundry)
    forward_result = forward_materializer.materialize_run(forward_run_id)
    assert forward_result.status == "materialized"
    forward_record = load_yaml(forward_materializer._assertion_path(forward_result.assertion_ids[0]))

    backfill_run_id = "rf_run_p2_03_backfill"
    _setup_historical_run(tmp_foundry, backfill_run_id)
    receipt = rollout.backfill_run(backfill_run_id, workspace_id="default", paths=tmp_foundry)
    backfill_materializer = AssertionMaterializer(workspace_id="default", paths=tmp_foundry)
    backfill_record = load_yaml(
        backfill_materializer._assertion_path(receipt["materialized_assertion_ids"][0])
    )

    assert set(forward_record.keys()) == set(backfill_record.keys())
    assert forward_record["schema_version"] == backfill_record["schema_version"]
    assert forward_record["type"] == backfill_record["type"] == "source_assertion"
    assert backfill_materializer.schemas.validate(backfill_record, "source_assertion").ok
    # Read surface: a backfilled edition resolves through the exact same
    # public registry lookup a forward-ingested one does -- no divergent
    # lookup path exists for backfilled data.
    registry = AssertionRegistry(workspace_id="default", paths=tmp_foundry)
    matches = registry.find_exact_passages(
        _ledger(tmp_foundry, backfill_run_id)["claims"][0]["sources"][0]["source_card_id"],
        backfill_record["assertion_text"],
    )
    assert len(matches) == 1


def test_backfill_run_reports_valid_receipt_when_no_exact_match_eligible_claims(tmp_foundry) -> None:
    """Resilience (P2-02 AC): a run with 0 exact-match-eligible claims
    produces a valid receipt with 0 materialized and a documented abstain
    breakdown -- never an error.
    """

    run_id = "rf_run_p2_02_no_eligible"
    points = [
        {
            "evidence_id": "ev_001",
            "locator": "para/1",
            "summary": "No quote available for this point.",
            "quote": None,
            "supports_potential_claims": ["clm_pending"],
        },
        {
            "evidence_id": "ev_002",
            "locator": "para/2",
            "summary": "Also no quote available for this point.",
            "quote": None,
            "supports_potential_claims": ["clm_pending"],
        },
    ]
    _setup_historical_run_with_points(tmp_foundry, run_id, points)

    receipt = rollout.backfill_run(run_id, workspace_id="default", paths=tmp_foundry)

    assert receipt["materialization_status"] == "abstained"
    assert receipt["materialized_count"] == 0
    assert receipt["abstained_count"] == 2
    assert receipt["abstention_breakdown"] == {"missing_exact_passage_quote": 2}
    assert receipt["source_cards"]["skipped_no_quotes"] == 1
    assert receipt["fuzzy_recovery_candidates"] == []


def test_backfill_corpus_denies_when_workspace_context_missing(tmp_foundry) -> None:
    receipt = rollout.backfill_corpus(assertion_registry_workspace_id=None, paths=tmp_foundry)

    assert receipt["allowed"] is False
    assert receipt["reason"] == "workspace_context_missing"
    assert receipt["runs"] == []
    assert not (tmp_foundry.root / "assertion_ledger").exists()


def test_backfill_corpus_denies_when_ledger_write_disabled(tmp_foundry) -> None:
    run_id = "rf_run_p2_02_write_disabled"
    _setup_historical_run(tmp_foundry, run_id)
    foundry = load_yaml(tmp_foundry.foundry_yaml)
    foundry["foundry"]["assertion_ledger"] = {"ledger_write_enabled": False}
    dump_yaml(foundry, tmp_foundry.foundry_yaml)

    receipt = rollout.backfill_corpus(assertion_registry_workspace_id="default", paths=tmp_foundry)

    assert receipt["allowed"] is False
    assert receipt["reason"] == "ledger_write_disabled"
    assert receipt["workspace_id"] == "default"
    assert receipt["runs"] == []
    assert not (tmp_foundry.root / "assertion_ledger").exists()


def test_backfill_corpus_discovers_and_backfills_every_run_with_a_claim_ledger(tmp_foundry) -> None:
    run_a = "rf_run_p2_02_corpus_a"
    run_b = "rf_run_p2_02_corpus_b"
    _setup_historical_run(tmp_foundry, run_a)
    _setup_historical_run(tmp_foundry, run_b, content="A single short exact sentence here.")

    receipt = rollout.backfill_corpus(assertion_registry_workspace_id="default", paths=tmp_foundry)

    assert receipt["allowed"] is True
    assert receipt["runs_total"] == 2
    assert {item["run_id"] for item in receipt["runs"]} == {run_a, run_b}
    assert receipt["materialized_total"] == 3
    assert receipt["abstained_total"] == 0


def test_backfill_corpus_respects_explicit_run_ids_filter(tmp_foundry) -> None:
    run_a = "rf_run_p2_02_filter_a"
    run_b = "rf_run_p2_02_filter_b"
    _setup_historical_run(tmp_foundry, run_a)
    _setup_historical_run(tmp_foundry, run_b, content="A single short exact sentence here.")

    receipt = rollout.backfill_corpus(
        assertion_registry_workspace_id="default", paths=tmp_foundry, run_ids=[run_b]
    )

    assert receipt["runs_total"] == 1
    assert receipt["runs"][0]["run_id"] == run_b


# ---------------------------------------------------------------------------
# P2-05: idempotency, interrupted-run convergence, dry-run parity
# ---------------------------------------------------------------------------


def test_backfill_run_is_idempotent_zero_new_writes_on_replay(tmp_foundry) -> None:
    """Algorithmic Test Scenario Matrix #9, driven through the backfill
    driver: identical content on a 2nd invocation produces 0 new files under
    ``assertion_ledger/`` (registry-layer + materializer-layer guarantee; the
    backfill driver itself must not defeat it).
    """

    run_id = "rf_run_p2_05_idempotent"
    _setup_historical_run(tmp_foundry, run_id)

    first = rollout.backfill_run(run_id, workspace_id="default", paths=tmp_foundry)
    ledger_root = tmp_foundry.root / "assertion_ledger"
    before = sorted(
        (str(path.relative_to(ledger_root)), path.stat().st_mtime_ns)
        for path in ledger_root.rglob("*")
        if path.is_file()
    )

    second = rollout.backfill_run(run_id, workspace_id="default", paths=tmp_foundry)
    after = sorted(
        (str(path.relative_to(ledger_root)), path.stat().st_mtime_ns)
        for path in ledger_root.rglob("*")
        if path.is_file()
    )

    assert before == after  # identical paths AND identical mtimes: 0 new/rewritten files
    assert second["materialization_status"] == "reused"
    assert second["materialized_count"] == first["materialized_count"] == 2
    assert second["materialized_assertion_ids"] == first["materialized_assertion_ids"]


def test_backfill_run_interrupted_before_publish_converges_on_retry(tmp_foundry) -> None:
    """Kill mid-run (before the materializer's publication boundary) and
    re-run: convergent end state, no duplicate/partial records.
    """

    run_id = "rf_run_p2_05_interrupted"
    _setup_historical_run(tmp_foundry, run_id)
    registry = AssertionRegistry(workspace_id="default", paths=tmp_foundry)
    receipt_path = registry.root / "backfill_operations" / f"{run_id}.yaml"

    with pytest.raises(MaterializationInterrupted):
        rollout.backfill_run(
            run_id, workspace_id="default", paths=tmp_foundry, _interrupt_before_publish=True
        )

    # The interruption happened before the materializer's own publication
    # pointer and before this driver's own (always-last) receipt write.
    assert not receipt_path.exists()

    retry = rollout.backfill_run(run_id, workspace_id="default", paths=tmp_foundry)

    assert retry["materialization_status"] == "materialized"
    assert retry["materialized_count"] == 2
    assert receipt_path.is_file()
    assert load_yaml(receipt_path) == retry


def test_backfill_dry_run_parity_with_observed_yield(tmp_foundry) -> None:
    """Dry-run parity: real-run counts match ``backfill_dry_run()``'s
    candidate counts, adjusted for the actually-observed (not merely
    estimated) abstention rate from the backfill receipt.
    """

    run_a = "rf_run_p2_05_parity_a"
    run_b = "rf_run_p2_05_parity_b"
    _setup_historical_run(tmp_foundry, run_a)
    _setup_historical_run(tmp_foundry, run_b, content="A single short exact sentence here.")

    before = rollout.backfill_dry_run(paths=tmp_foundry)
    assert before["candidate_claim_ledgers"] == 2
    assert before["existing_assertion_records"] == 0

    corpus_receipt = rollout.backfill_corpus(assertion_registry_workspace_id="default", paths=tmp_foundry)
    assert corpus_receipt["runs_total"] == before["candidate_claim_ledgers"]

    after = rollout.backfill_dry_run(paths=tmp_foundry)

    assert (
        after["existing_assertion_records"] - before["existing_assertion_records"]
        == corpus_receipt["materialized_total"]
        == 3
    )


def test_write_backfill_receipt_raises_on_conflicting_outcome(tmp_path) -> None:
    """A persisted receipt whose durable OUTCOME differs from a freshly
    computed one raises -- the same fail-closed posture as every other
    immutable record in this ledger.
    """

    path = tmp_path / "backfill_operations" / "rf_run_conflict_probe.yaml"
    first = {
        "schema_version": "1.0",
        "run_id": "rf_run_conflict_probe",
        "materialized_count": 1,
        "materialized_claim_ids": ["clm_001"],
        "abstained_count": 0,
    }
    rollout._write_backfill_receipt(first, path)

    conflicting = {**first, "materialized_count": 2, "materialized_claim_ids": ["clm_001", "clm_002"]}
    with pytest.raises(BackfillConflict, match="conflicting_backfill_receipt"):
        rollout._write_backfill_receipt(conflicting, path)


def test_write_backfill_receipt_is_a_no_op_when_only_volatile_fields_differ(tmp_path) -> None:
    """``materialization_status``/``source_cards`` describe one specific
    invocation's call-local outcome (materialized-vs-reused,
    created-vs-reused) and legitimately differ across an idempotent replay;
    that alone must not raise, and must not rewrite the file.
    """

    path = tmp_path / "backfill_operations" / "rf_run_volatile_probe.yaml"
    first = {
        "schema_version": "1.0",
        "run_id": "rf_run_volatile_probe",
        "materialization_status": "materialized",
        "source_cards": {"created": 1, "reused": 0},
        "materialized_count": 1,
    }
    rollout._write_backfill_receipt(first, path)
    before_mtime = path.stat().st_mtime_ns

    replay = {**first, "materialization_status": "reused", "source_cards": {"created": 0, "reused": 1}}
    rollout._write_backfill_receipt(replay, path)  # must not raise

    assert path.stat().st_mtime_ns == before_mtime
    assert load_yaml(path) == first  # on-disk content unchanged: 0 new writes


# ---------------------------------------------------------------------------
# P2-06: narrow fuzzy>=0.9 quote-recovery add-on
# ---------------------------------------------------------------------------


def test_fuzzy_ratio_boundary_above_and_below_threshold() -> None:
    """Algorithmic Test Scenario Matrix #10: a fact/quote pair at ratio>=0.9
    is a spot-check-pending candidate; a pair below 0.9 (SPIKE RQ2's own
    finding: 0.8-and-below demonstrably admits real paraphrase drift) is not.
    """

    quote = "The measured result was 42 percent complete."
    close_paraphrase = "The measured result was 42 percent complete"
    far_paraphrase = "The measured result was forty two percent complete."

    assert rollout._fuzzy_ratio(quote, close_paraphrase) >= 0.9
    assert rollout._fuzzy_ratio(quote, far_paraphrase) < 0.9


_QUOTE_WITH_MATCH = "The measured result was 42 percent complete."
_PARAPHRASE_CLOSE_MATCH = "The measured result was 42 percent complete"
_PARAPHRASE_FAR = "A completely unrelated sentence about something else entirely."


def test_backfill_run_flags_fuzzy_recovery_candidate_without_materializing(tmp_foundry) -> None:
    """A fact with no quote of its own, whose paraphrase closely (>=0.9)
    matches a *different* point's quote on the same source card, is flagged
    ``spot_check_pending`` in the receipt -- and never auto-materialized.
    """

    run_id = "rf_run_p2_06_fuzzy_recovered"
    points = [
        {
            "evidence_id": "ev_001",
            "locator": "para/1",
            "summary": "Unrelated summary for point one.",
            "quote": _QUOTE_WITH_MATCH,
            "supports_potential_claims": ["clm_pending"],
        },
        {
            "evidence_id": "ev_002",
            "locator": "para/2",
            "summary": _PARAPHRASE_CLOSE_MATCH,
            "quote": None,
            "supports_potential_claims": ["clm_pending"],
        },
    ]
    _setup_historical_run_with_points(tmp_foundry, run_id, points)
    assert len(_ledger(tmp_foundry, run_id)["claims"]) == 2

    receipt = rollout.backfill_run(run_id, workspace_id="default", paths=tmp_foundry)

    assert receipt["materialized_count"] == 1
    assert receipt["abstained_count"] == 1
    assert receipt["abstained_claims"][0]["code"] == "missing_exact_passage_quote"
    assert len(receipt["fuzzy_recovery_candidates"]) == 1
    candidate = receipt["fuzzy_recovery_candidates"][0]
    assert candidate["status"] == "spot_check_pending"
    assert candidate["materialized"] is False
    assert candidate["fuzzy_ratio"] >= 0.9
    assert candidate["candidate_evidence_id"] == "ev_001"
    # Never auto-materialized: only the genuine exact-match fact produced an
    # assertion record.
    materializer = AssertionMaterializer(workspace_id="default", paths=tmp_foundry)
    assert len(list((materializer.root / "assertions").glob("*.yaml"))) == 1


def test_backfill_run_does_not_flag_a_below_threshold_paraphrase(tmp_foundry) -> None:
    run_id = "rf_run_p2_06_fuzzy_rejected"
    points = [
        {
            "evidence_id": "ev_001",
            "locator": "para/1",
            "summary": "Unrelated summary for point one.",
            "quote": _QUOTE_WITH_MATCH,
            "supports_potential_claims": ["clm_pending"],
        },
        {
            "evidence_id": "ev_002",
            "locator": "para/2",
            "summary": _PARAPHRASE_FAR,
            "quote": None,
            "supports_potential_claims": ["clm_pending"],
        },
    ]
    _setup_historical_run_with_points(tmp_foundry, run_id, points)

    receipt = rollout.backfill_run(run_id, workspace_id="default", paths=tmp_foundry)

    assert receipt["abstained_count"] == 1
    assert receipt["fuzzy_recovery_candidates"] == []
