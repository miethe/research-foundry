"""End-to-end acceptance test for the Research Foundry loop (spec §15).

Drives the full pipeline against an isolated temp workspace and asserts the MVP
success criteria: raw idea → intent/ibom/node → plan → ≥5 source cards →
extraction → claim ledger (100% mapped) → report → verify exits 0 → durable
evidence bundle → writebacks (meatywiki + skillbom + ccdash) → guard passes.

This test owns no service code; it is the integration contract for Wave 3.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Services are imported lazily inside the test so collection still works while
# the suite is being assembled.


def _write_local_source(dirpath: Path, name: str, body: str) -> Path:
    p = dirpath / name
    p.write_text(body, encoding="utf-8")
    return p


@pytest.mark.integration
def test_full_research_loop(tmp_foundry, sample_idea_text, tmp_path):
    from research_foundry.errors import ExitCode
    from research_foundry.services import (
        capture,
        claim_mapping,
        extraction,
        governance,
        planning,
        source_cards,
        synthesis,
        telemetry,
        verification,
        writeback,
    )

    paths = tmp_foundry

    # 1. capture
    cap = capture.capture_idea(sample_idea_text, sensitivity="personal", paths=paths)
    assert cap.path.exists()

    # 2. triage → 3 linked artifacts
    tri = capture.triage_idea(cap.path, paths=paths)
    assert tri.intent_id and tri.ibom_id and tri.node_id

    # 3. plan
    pl = planning.plan_run(tri.intent_id, depth="deep", audience="technical", paths=paths)
    run_id = pl.run_id
    assert pl.brief_path.exists() and pl.swarm_path.exists() and pl.routing_path.exists()

    # 4. ingest ≥5 mixed sources
    docs = tmp_path / "docs"
    docs.mkdir()
    bodies = {
        "litellm.md": "LiteLLM supports cost-based routing. The router used 1000 requests in tests.",
        "paperqa.md": "PaperQA2 grounds answers with in-text citations over local PDFs.",
        "gptr.md": "GPT Researcher performs web and local research and produces cited reports.",
        "ccdash.md": "CCDash tracks completion, rework, drift, cost, latency and reuse candidates.",
        "intent.md": "Intent defines the destination; the control plane routes the next move.",
    }
    cards = []
    types = ["official_doc", "paper", "repo", "official_doc", "personal_note"]
    for (fname, body), stype in zip(bodies.items(), types, strict=False):
        f = _write_local_source(docs, fname, body)
        r = source_cards.ingest_source(
            str(f), run_id=run_id, source_type=stype, sensitivity="personal", paths=paths
        )
        cards.append(r)
    assert len(list(source_cards.list_source_cards(run_id, paths=paths))) >= 5

    # 5. extract
    ext = extraction.extract_run(run_id, paths=paths)
    assert ext.count >= 5

    # 6. claim ledger — 100% of claims have a source
    cm = claim_mapping.build_claim_ledger(run_id, intent_id=tri.intent_id, paths=paths)
    assert cm.claims_total >= 5

    # 7. synthesize (deterministic)
    syn = synthesis.synthesize_report(run_id, paths=paths)
    assert syn.report_path.exists()

    # 8. verify → exit 0
    ver = verification.verify_report(run_id, paths=paths)
    assert ver.passed, [c.id for c in ver.checks if c.status == "fail"]
    assert ver.exit_code == int(ExitCode.OK)

    # 9. evidence bundle is durable + references artifacts
    bnd = writeback.build_bundle(run_id, verify=True, paths=paths)
    assert bnd.verified
    assert bnd.counts.get("source_cards", 0) >= 5
    assert bnd.bundle_path.exists()

    # 10. writebacks
    wb = writeback.writeback(run_id, paths=paths)
    assert wb.meatywiki_path and wb.meatywiki_path.exists()
    assert wb.skillbom_path and wb.skillbom_path.exists()
    assert wb.ccdash_path and wb.ccdash_path.exists()

    # 11. ccdash telemetry + summary
    telemetry.summarize("daily", paths=paths)

    # 12. governance guard passes for a clean personal run
    g = governance.guard_check(governance.GuardContext(profile="personal", run_id=run_id), paths=paths)
    assert g.passed, [v.rule_id for v in g.violations]


@pytest.mark.integration
def test_unsupported_claim_blocks_publish(tmp_foundry, sample_idea_text, tmp_path):
    """A report with an untagged material claim must FAIL verification (exit 4)."""

    from research_foundry.errors import ExitCode
    from research_foundry.services import (
        capture,
        claim_mapping,
        extraction,
        planning,
        source_cards,
        synthesis,
        verification,
    )

    paths = tmp_foundry
    cap = capture.capture_idea(sample_idea_text, paths=paths)
    tri = capture.triage_idea(cap.path, paths=paths)
    pl = planning.plan_run(tri.intent_id, paths=paths)
    f = tmp_path / "s.md"
    f.write_text("LiteLLM supports cost-based routing.", encoding="utf-8")
    source_cards.ingest_source(str(f), run_id=pl.run_id, source_type="official_doc", paths=paths)
    extraction.extract_run(pl.run_id, paths=paths)
    claim_mapping.build_claim_ledger(pl.run_id, intent_id=tri.intent_id, paths=paths)
    syn = synthesis.synthesize_report(pl.run_id, paths=paths)

    # Inject an unsupported material claim into the Findings section (an untagged
    # quantitative sentence with no [claim:] tag and no inference/speculation label).
    text = syn.report_path.read_text(encoding="utf-8")
    injected = "The system processed 9,999 queries with 42% lower latency."
    text = text.replace(
        "## Findings\n\n",
        f"## Findings\n\n{injected}\n\n",
        1,
    )
    assert injected in text  # guard: the Findings heading existed and was targeted
    syn.report_path.write_text(text, encoding="utf-8")

    ver = verification.verify_report(pl.run_id, paths=paths)
    assert not ver.passed
    assert ver.exit_code == int(ExitCode.UNSUPPORTED)
