"""P6-3 (phase-5-6-governance-finalize.md) — Release-gate bidirectional
INTEGRATION test.

``tests/test_release_gate_judgment_basis.py`` (P5-3) already covers the
release-gate predicate at the unit level
(:func:`research_foundry.services.governance.release_gate_blocked_by_unassessed_judgment`)
and exercises ``verify_report`` with a hand-authored run + a literal
``evidence_judgment_bases=["unassessed"]`` passed straight into the call. This
file goes one step further: it drives the REAL capture pipeline end-to-end —
``ingest_source`` -> ``extraction.extract_run`` -> ``claim_mapping.build_claim_ledger``
-> ``AssertionMaterializer.materialize_run`` (the same forward chain
``tests/unit/test_assertion_materialization.py`` proves for P3) — so the
``judgment_basis: "unassessed"`` value asserted here comes from the actual
on-disk ``source_assertion`` the materializer wrote (its fail-closed default,
``services/assertion_materialization.py`` ~L434-446), never a hardcoded test
literal. The report itself is produced by the real deterministic synthesizer
(``services.synthesis.synthesize_report``), not a hand-written fixture, so the
only mocked boundary left is... none: capture, taxonomy assignment, report
synthesis, and verification all run through their real service functions.

Both directions of the release-gate asymmetry NFR (decisions-block OQ-6) are
tested explicitly here, never assumed from the other:

* (a) a simulated commercial-release disposition check against the
  real, pipeline-produced ``unassessed`` evidence item is BLOCKED;
* (b) a simulated internal-capture disposition check against the SAME
  real, pipeline-produced ``unassessed`` evidence item SUCCEEDS.
"""

from __future__ import annotations

from research_foundry.services import claim_mapping, extraction
from research_foundry.services.assertion_materialization import AssertionMaterializer
from research_foundry.services.source_cards import ingest_source
from research_foundry.services.synthesis import synthesize_report
from research_foundry.services.verification import verify_report
from research_foundry.yamlio import dump_yaml, load_yaml


def _run_full_capture_pipeline(tmp_foundry, run_id: str) -> list[str]:
    """Drive the real capture -> taxonomy-assignment -> synthesis pipeline for
    *run_id* and return the ``judgment_basis`` values actually recorded on the
    materialized ``source_assertion`` file(s) on disk.

    No governance/verification boundary is mocked: every step below is the
    same production service function exercised by the project's own P3
    integration coverage (``tests/unit/test_assertion_materialization.py``).
    """

    foundry_doc = load_yaml(tmp_foundry.foundry_yaml)
    foundry_doc["foundry"]["assertion_ledger"] = {"ledger_write_enabled": True}
    dump_yaml(foundry_doc, tmp_foundry.foundry_yaml)

    tmp_foundry.run_paths(run_id).ensure_scaffold()
    ingest_source(
        "evidence.txt",
        run_id=run_id,
        title="Release-gate integration evidence",
        sensitivity="personal",
        content="The dataset is licensed for research use.",
        assertion_registry_workspace_id="workspace-release-gate-integration",
        paths=tmp_foundry,
    )
    extraction.extract_run(run_id, paths=tmp_foundry)
    claim_mapping.build_claim_ledger(run_id, paths=tmp_foundry)

    materializer = AssertionMaterializer(
        workspace_id="workspace-release-gate-integration", paths=tmp_foundry
    )
    result = materializer.materialize_run(run_id)
    assert result.status == "materialized", (
        "capture pipeline did not materialize a source_assertion for the "
        f"release-gate integration fixture: {result}"
    )
    assert result.assertion_ids, "capture pipeline produced no source_assertion ids"

    # Real taxonomy-assignment path (P1): read the judgment_basis actually
    # written to disk by the materializer's fail-closed default — never
    # injected by this test.
    judgment_bases: list[str] = []
    for assertion_id in result.assertion_ids:
        assertion = load_yaml(materializer._assertion_path(assertion_id))
        judgment_bases.append(
            assertion["extensions"]["evidence_taxonomy"]["judgment_basis"]
        )

    # Real deterministic synthesizer — produces a ledger-faithful report body
    # designed to satisfy every OTHER verify_report check cleanly, so the only
    # variable left in the two tests below is the release-gate disposition.
    synthesize_report(run_id, paths=tmp_foundry)

    return judgment_bases


def test_commercial_release_disposition_blocked_by_real_pipeline_unassessed_item(
    tmp_foundry,
) -> None:
    """Direction (a): a simulated commercial-release check against an evidence
    item whose ``judgment_basis: unassessed`` was assigned by the REAL capture
    pipeline (not injected) must be BLOCKED."""

    run_id = "rf_run_p6_release_gate_commercial"
    judgment_bases = _run_full_capture_pipeline(tmp_foundry, run_id)

    # Sanity: confirms the value driving this test came from the real
    # taxonomy-assignment path, not a hand-picked literal.
    assert judgment_bases == ["unassessed"]

    result = verify_report(
        run_id,
        paths=tmp_foundry,
        disposition="commercial_release",
        evidence_judgment_bases=judgment_bases,
    )

    by_id = {c.id: c for c in result.checks}
    assert by_id["release_gate_judgment_basis_assessed"].status == "fail"
    assert result.passed is False


def test_internal_capture_disposition_succeeds_with_same_real_pipeline_unassessed_item(
    tmp_foundry,
) -> None:
    """Direction (b), tested EXPLICITLY (never assumed from direction (a)
    above): a simulated internal-capture write against the SAME real,
    pipeline-produced ``unassessed`` evidence item must SUCCEED — the
    release-gate asymmetry NFR."""

    run_id = "rf_run_p6_release_gate_internal"
    judgment_bases = _run_full_capture_pipeline(tmp_foundry, run_id)

    assert judgment_bases == ["unassessed"]

    result = verify_report(
        run_id,
        paths=tmp_foundry,
        disposition="internal_capture",
        evidence_judgment_bases=judgment_bases,
    )

    by_id = {c.id: c for c in result.checks}
    assert by_id["release_gate_judgment_basis_assessed"].status == "pass"
    assert result.passed is True
