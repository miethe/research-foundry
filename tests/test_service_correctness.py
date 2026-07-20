"""Adversarial service-correctness regression cases (Focus-4 audit).

These tests pin down REAL defects found by an adversarial audit of the service
layer. Each test documents the *current* behavior and, where the current
behavior is a defect, marks the "correct" assertion with ``xfail(strict=True)``
so the suite stays green today but flips loudly the moment the bug is fixed
(at which point the xfail should be removed and the assertion inverted).

Findings exercised here:

1.  ``extract_run`` is not a clean overwrite: removing/replacing a source card
    leaves an ORPHAN extraction card on disk, which produces a claim sourced to
    a source card that no longer exists.
2.  The verifier's ``supported_claims_have_source_cards`` check only verifies a
    claim carries a non-empty ``source_card_id`` string — it does NOT verify the
    referenced source card actually exists. A "supported" claim citing a phantom
    source passes verification (exit 0). This undermines the core guarantee.
3.  Per-status claim counts (``telemetry.emit_ccdash_event`` and
    ``writeback.build_bundle``) silently drop the schema-valid ``mixed`` and
    ``contradicted`` statuses, so the per-status fields do not sum to
    ``claims_total``.
4.  ``build_bundle`` lineage ``raw_idea_ids`` is structurally un-populatable:
    ``triage_idea`` never records the originating raw_idea_id on the intent, so
    the idea->intent->bundle lineage is broken (always ``[]``).
5.  id collision: two distinct ideas whose first-6-word slugs match mint the
    SAME intent_id / run_id / ccdash event_id, silently overwriting the first.
6.  Pipeline stages run on a NONEXISTENT run id succeed (create a phantom run)
    instead of raising ``NotFoundError`` — a footgun for typo'd run ids.
"""

from __future__ import annotations

import pytest

from research_foundry.frontmatter import load_md
from research_foundry.services import (
    capture,
    claim_mapping,
    extraction,
    planning,
    source_cards,
    synthesis,
    telemetry,
    verification,
    writeback,
)
from research_foundry.yamlio import dump_yaml, load_yaml


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _planned_run(paths, *, title="Audit topic", idea="Latency dropped by 40%."):
    cap = capture.capture_idea(idea, title=title, paths=paths)
    tri = capture.triage_idea(cap.raw_idea_id, paths=paths)
    plan = planning.plan_run(tri.intent_id, paths=paths)
    return tri, plan


# --------------------------------------------------------------------------- #
# 1) extract_run leaves orphan extraction cards on rerun
# --------------------------------------------------------------------------- #
def test_extract_prunes_orphan_card_when_source_removed(tmp_foundry):
    paths = tmp_foundry
    _, plan = _planned_run(paths)
    run = plan.run_id
    rp = paths.run_paths(run)

    source_cards.ingest_source("Alpha latency dropped 40%.", run_id=run, title="A", paths=paths)
    source_cards.ingest_source("Beta cost rose 10%.", run_id=run, title="B", paths=paths)
    extraction.extract_run(run, paths=paths)
    assert len(list(rp.extractions.glob("*.yaml"))) == 2

    # Drop source B and re-extract.
    for p in rp.sources.glob("*.md"):
        if "_b_" in p.name:
            p.unlink()
    remaining = {p.stem for p in rp.sources.glob("*.md")}
    assert len(remaining) == 1

    extraction.extract_run(run, paths=paths)
    ext_cards = list(rp.extractions.glob("*.yaml"))

    # FIXED: extract_run produces a clean set mirroring the current source cards.
    assert len(ext_cards) == 1, "stale extraction card for the removed source is pruned"

    # Every surviving extraction card references a source card that still exists.
    referenced = {load_yaml(p).get("source_card_id") for p in ext_cards}
    src_ids = set()
    for p in rp.sources.glob("*.md"):
        meta, _ = load_md(p)
        src_ids.add(meta.get("source_card_id"))
    assert all(sid in src_ids for sid in referenced), "no extraction card points to a deleted source"


def test_extract_should_prune_orphan_cards(tmp_foundry):
    paths = tmp_foundry
    _, plan = _planned_run(paths)
    run = plan.run_id
    rp = paths.run_paths(run)
    source_cards.ingest_source("Alpha latency dropped 40%.", run_id=run, title="A", paths=paths)
    source_cards.ingest_source("Beta cost rose 10%.", run_id=run, title="B", paths=paths)
    extraction.extract_run(run, paths=paths)
    for p in rp.sources.glob("*.md"):
        if "_b_" in p.name:
            p.unlink()
    extraction.extract_run(run, paths=paths)
    # Correct behavior: extraction set mirrors the current source set (1 card).
    assert len(list(rp.extractions.glob("*.yaml"))) == 1


# --------------------------------------------------------------------------- #
# 2) verifier accepts a 'supported' claim citing a non-existent source card
# --------------------------------------------------------------------------- #
def test_verifier_accepts_phantom_source_card(tmp_foundry):
    paths = tmp_foundry
    tri, plan = _planned_run(paths)
    run = plan.run_id
    rp = paths.run_paths(run)
    rp.ensure_scaffold()

    ledger = {
        "id": "claims_audit",
        "intent_id": tri.intent_id,
        "report_ref": "reports/report_draft.md",
        "verification_status": "pending",
        "claims": [
            {
                "claim_id": "clm_001",
                "text": "The system is fast.",
                "materiality": "material",
                "claim_type": "factual",
                "status": "supported",
                "confidence": "medium",
                "sources": [
                    {
                        "source_card_id": "src_THIS_NEVER_EXISTED",
                        "evidence_id": "ev_001",
                        "relation": "supports",
                        "locator": "para/1",
                    }
                ],
                "inference_basis": {"from_claims": [], "reasoning_summary": None},
                "report_locations": [],
                "reviewer_notes": "",
            }
        ],
        "unresolved_questions": [],
    }
    dump_yaml(ledger, rp.claim_ledger)
    synthesis.synthesize_report(run, paths=paths)
    result = verification.verify_report(run, paths=paths)

    # FIXED: a 'supported' claim citing a non-existent source card is rejected.
    assert result.passed is False
    check = next(c for c in result.checks if c.id == "supported_claims_have_source_cards")
    assert check.status == "fail"


def test_verifier_should_reject_phantom_source_card(tmp_foundry):
    paths = tmp_foundry
    tri, plan = _planned_run(paths)
    run = plan.run_id
    rp = paths.run_paths(run)
    rp.ensure_scaffold()
    ledger = {
        "id": "claims_audit",
        "intent_id": tri.intent_id,
        "report_ref": "reports/report_draft.md",
        "verification_status": "pending",
        "claims": [
            {
                "claim_id": "clm_001",
                "text": "The system is fast.",
                "materiality": "material",
                "claim_type": "factual",
                "status": "supported",
                "confidence": "medium",
                "sources": [
                    {"source_card_id": "src_THIS_NEVER_EXISTED", "evidence_id": "ev_001",
                     "relation": "supports", "locator": "para/1"}
                ],
                "inference_basis": {"from_claims": [], "reasoning_summary": None},
                "report_locations": [],
                "reviewer_notes": "",
            }
        ],
        "unresolved_questions": [],
    }
    dump_yaml(ledger, rp.claim_ledger)
    synthesis.synthesize_report(run, paths=paths)
    result = verification.verify_report(run, paths=paths)
    # Correct behavior: a supported claim citing a missing source card must fail.
    assert result.passed is False


# --------------------------------------------------------------------------- #
# 3) per-status claim counts drop mixed/contradicted statuses
# --------------------------------------------------------------------------- #
def _ledger_with_mixed(tri):
    def claim(cid, status):
        return {
            "claim_id": cid, "text": cid, "materiality": "material",
            "claim_type": "factual", "status": status, "confidence": "medium",
            "sources": [{"source_card_id": "s1", "evidence_id": "ev_001",
                         "relation": "supports", "locator": "p"}],
            "inference_basis": {"from_claims": [], "reasoning_summary": None},
            "report_locations": [], "reviewer_notes": "",
        }
    return {
        "id": "claims_audit", "intent_id": tri.intent_id,
        "report_ref": "reports/report_draft.md", "verification_status": "pending",
        "claims": [claim("clm_001", "supported"), claim("clm_002", "mixed"),
                   claim("clm_003", "contradicted")],
        "unresolved_questions": [],
    }


def test_ccdash_metrics_count_mixed_and_contradicted(tmp_foundry):
    paths = tmp_foundry
    tri, plan = _planned_run(paths)
    run = plan.run_id
    rp = paths.run_paths(run)
    rp.ensure_scaffold()
    dump_yaml(_ledger_with_mixed(tri), rp.claim_ledger)

    telemetry.emit_ccdash_event(run, paths=paths)
    event = load_yaml(rp.ccdash_event)
    m = event["metrics"]
    accounted = (
        m["claims_supported"] + m["claims_mixed"] + m["claims_contradicted"]
        + m["claims_inference"] + m["claims_speculation"] + m["unsupported_claims"]
    )
    # FIXED: every status (incl. mixed/contradicted) is counted and sums to total.
    assert m["claims_total"] == 3
    assert m["claims_mixed"] == 1
    assert m["claims_contradicted"] == 1
    assert accounted == m["claims_total"]


def test_bundle_counts_include_mixed_and_contradicted(tmp_foundry):
    paths = tmp_foundry
    tri, plan = _planned_run(paths)
    run = plan.run_id
    rp = paths.run_paths(run)
    rp.ensure_scaffold()
    dump_yaml(_ledger_with_mixed(tri), rp.claim_ledger)

    bundle = writeback.build_bundle(run, verify=False, paths=paths)
    c = bundle.counts
    accounted = (
        c["claims_supported"] + c["claims_mixed"] + c["claims_contradicted"]
        + c["claims_inference"] + c["claims_speculation"] + c["claims_unsupported"]
    )
    # FIXED: mixed/contradicted are counted, so the breakdown sums to the total.
    assert c["claims_total"] == 3
    assert c["claims_mixed"] == 1
    assert c["claims_contradicted"] == 1
    assert accounted == c["claims_total"]


def test_bundle_per_status_counts_should_sum_to_total(tmp_foundry):
    paths = tmp_foundry
    tri, plan = _planned_run(paths)
    run = plan.run_id
    rp = paths.run_paths(run)
    rp.ensure_scaffold()
    dump_yaml(_ledger_with_mixed(tri), rp.claim_ledger)
    c = writeback.build_bundle(run, verify=False, paths=paths).counts
    accounted = (
        c["claims_supported"] + c["claims_inference"]
        + c["claims_speculation"] + c["claims_unsupported"]
        + c.get("claims_mixed", 0) + c.get("claims_contradicted", 0)
    )
    assert accounted == c["claims_total"]


# --------------------------------------------------------------------------- #
# 4) lineage raw_idea_ids is structurally empty
# --------------------------------------------------------------------------- #
def test_triage_records_raw_idea_id_on_intent(tmp_foundry):
    paths = tmp_foundry
    cap = capture.capture_idea("Lineage test idea body.", title="Lineage topic", paths=paths)
    tri = capture.triage_idea(cap.raw_idea_id, paths=paths)
    intent = load_yaml(paths.intents_active / f"{tri.intent_id}.yaml")
    # FIXED: triage records the originating raw_idea_id on the intent.
    assert intent.get("raw_idea_ids") == [cap.raw_idea_id]


def test_bundle_lineage_includes_raw_idea_ids(tmp_foundry):
    paths = tmp_foundry
    cap = capture.capture_idea("Lineage test idea body.", title="Lineage topic", paths=paths)
    tri = capture.triage_idea(cap.raw_idea_id, paths=paths)
    plan = planning.plan_run(tri.intent_id, paths=paths)
    run = plan.run_id
    source_cards.ingest_source("Latency dropped 40%.", run_id=run, paths=paths)
    extraction.extract_run(run, paths=paths)
    claim_mapping.build_claim_ledger(run, paths=paths)
    bundle = load_yaml(writeback.build_bundle(run, verify=False, paths=paths).bundle_path)
    # The other lineage links ARE populated...
    assert bundle["lineage"]["intent_id"] == tri.intent_id
    assert bundle["lineage"]["ibom_id"] == tri.ibom_id
    assert bundle["lineage"]["intenttree_node_id"] == tri.node_id
    # FIXED: raw_idea_ids is backfilled from the intent's recorded raw_idea_id.
    assert bundle["lineage"]["raw_idea_ids"] == [cap.raw_idea_id]


def test_bundle_lineage_should_include_raw_idea_id(tmp_foundry):
    paths = tmp_foundry
    cap = capture.capture_idea("Lineage test idea body.", title="Lineage topic", paths=paths)
    tri = capture.triage_idea(cap.raw_idea_id, paths=paths)
    plan = planning.plan_run(tri.intent_id, paths=paths)
    run = plan.run_id
    source_cards.ingest_source("Latency dropped 40%.", run_id=run, paths=paths)
    extraction.extract_run(run, paths=paths)
    claim_mapping.build_claim_ledger(run, paths=paths)
    bundle = load_yaml(writeback.build_bundle(run, verify=False, paths=paths).bundle_path)
    assert cap.raw_idea_id in bundle["lineage"]["raw_idea_ids"]


# --------------------------------------------------------------------------- #
# 5) id collision silently overwrites a distinct idea's intent/run/event
# --------------------------------------------------------------------------- #
def test_distinct_ideas_do_not_collide_on_six_word_slug(tmp_foundry):
    paths = tmp_foundry
    t1 = "How fast are vector databases really when extra words follow A"
    t2 = "How fast are vector databases really when extra words follow B"

    cap1 = capture.capture_idea("body one", title=t1, paths=paths)
    tri1 = capture.triage_idea(cap1.raw_idea_id, paths=paths)
    cap2 = capture.capture_idea("body two", title=t2, paths=paths)
    tri2 = capture.triage_idea(cap2.raw_idea_id, paths=paths)

    # FIXED: two genuinely different ideas mint DISTINCT intent ids despite the
    # shared first-6-word slug, so the second does not overwrite the first.
    assert tri1.intent_id != tri2.intent_id
    assert (paths.intents_active / f"{tri1.intent_id}.yaml").exists()
    assert (paths.intents_active / f"{tri2.intent_id}.yaml").exists()

    plan1 = planning.plan_run(tri1.intent_id, paths=paths)
    plan2 = planning.plan_run(tri2.intent_id, paths=paths)
    assert plan1.run_id != plan2.run_id  # distinct run dirs -> both survive

    # Both run directories exist for the two distinct research ideas.
    assert sum(1 for _ in paths.runs.iterdir()) == 2


# --------------------------------------------------------------------------- #
# 6) pipeline stages on a nonexistent run id do not raise NotFoundError
# --------------------------------------------------------------------------- #
def test_extract_on_missing_run_raises(tmp_foundry):
    from research_foundry.errors import NotFoundError

    paths = tmp_foundry
    # No plan/run exists. FIXED: extract raises instead of creating a phantom run.
    with pytest.raises(NotFoundError):
        extraction.extract_run("rf_run_NOPE", paths=paths)
    assert not paths.run_paths("rf_run_NOPE").run.exists(), "no phantom run dir created"


def test_claim_map_on_missing_run_raises(tmp_foundry):
    from research_foundry.errors import NotFoundError

    paths = tmp_foundry
    # FIXED: claim-map raises instead of writing a phantom ledger.
    with pytest.raises(NotFoundError):
        claim_mapping.build_claim_ledger("rf_run_NOPE", paths=paths)
    assert not paths.run_paths("rf_run_NOPE").run.exists(), "no phantom run dir created"


def test_extract_on_missing_run_should_raise(tmp_foundry):
    from research_foundry.errors import NotFoundError

    paths = tmp_foundry
    with pytest.raises(NotFoundError):
        extraction.extract_run("rf_run_NOPE", paths=paths)
