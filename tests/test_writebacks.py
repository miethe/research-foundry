"""Tests for the writeback + telemetry services (contract §9, §10).

Each test drives the full deterministic pipeline
(capture → triage → plan → ingest → extract → claim_map → synthesize) so the
writeback layer operates on real run artifacts, then exercises bundle assembly,
the three writeback targets + workspace mirrors, CCDash emission, the daily
rollup, and the work-sensitive review gate.
"""

from __future__ import annotations

from research_foundry.frontmatter import load_md
from research_foundry.paths import FoundryPaths
from research_foundry.schemas import validate
from research_foundry.services import telemetry, writeback
from research_foundry.services.capture import capture_idea, triage_idea
from research_foundry.services.claim_mapping import build_claim_ledger
from research_foundry.services.extraction import extract_run
from research_foundry.services.planning import plan_run
from research_foundry.services.source_cards import ingest_source
from research_foundry.services.synthesis import synthesize_report
from research_foundry.yamlio import load_yaml

_IDEA = (
    "Research how agentic research workflows should handle evidence bundles and "
    "claim traceability across cheap extraction and deep synthesis models. "
    "Studies show 40% of unsupported claims come from synthesis drift."
)

_SOURCE_TEXT = (
    "Evidence bundles let a research run carry its sources, claims, and a report "
    "in one auditable package. A 2025 study found that 40% of unsupported claims "
    "originate during synthesis when extraction and synthesis use different models. "
    "Claim ledgers reduce citation mismatch by mapping every material sentence to "
    "an evidence id. Limitations: small sample, single domain."
)


def _build_run(paths: FoundryPaths, *, sensitivity: str = "personal") -> str:
    """Drive the deterministic pipeline and return the run_id."""

    cap = capture_idea(_IDEA, sensitivity=sensitivity, paths=paths)
    tri = triage_idea(cap.raw_idea_id, paths=paths)
    assert tri.intent_id
    plan = plan_run(tri.intent_id, paths=paths)
    run_id = plan.run_id

    src_file = paths.root / "input_source.txt"
    src_file.write_text(_SOURCE_TEXT, encoding="utf-8")
    ingest_source(
        str(src_file),
        run_id=run_id,
        source_type="paper",
        sensitivity=sensitivity,
        title="Evidence bundles and claim traceability",
        paths=paths,
    )

    extract_run(run_id, paths=paths)
    build_claim_ledger(run_id, intent_id=tri.intent_id, paths=paths)
    synthesize_report(run_id, paths=paths)
    return run_id


def test_build_bundle_is_schema_valid_with_counts(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)

    result = writeback.build_bundle(run_id, verify=True, paths=paths)

    assert result.bundle_path.exists()
    bundle = load_yaml(result.bundle_path)
    assert validate(bundle, "evidence_bundle").ok

    rp = paths.run_paths(run_id)
    n_sources = len(list(rp.sources.glob("*.md")))
    n_extractions = len(list(rp.extractions.glob("*.yaml")))
    ledger = load_yaml(rp.claim_ledger)
    n_claims = len(ledger.get("claims") or [])

    assert n_sources >= 1
    assert n_extractions >= 1
    assert n_claims >= 1

    counts = bundle["counts"]
    assert counts["source_cards"] == n_sources
    assert counts["extraction_cards"] == n_extractions
    assert counts["claims_total"] == n_claims
    # Status counts partition the total.
    partition = (
        counts["claims_supported"]
        + counts["claims_inference"]
        + counts["claims_speculation"]
        + counts["claims_unsupported"]
    )
    assert partition <= n_claims

    # References point at real run artifacts.
    artifacts = bundle["artifacts"]
    assert artifacts["claim_ledger"] == "claims/claim_ledger.yaml"
    assert artifacts["report"] in {"reports/report_draft.md", "reports/report_final.md"}
    assert bundle["run_id"] == run_id
    assert bundle["lineage"]["intent_id"]


def test_writeback_materializes_all_targets_and_mirrors(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    result = writeback.writeback(run_id, paths=paths)
    rp = paths.run_paths(run_id)

    # Three run-local targets exist.
    assert result.meatywiki_path and result.meatywiki_path.exists()
    assert result.skillbom_path and result.skillbom_path.exists()
    assert result.ccdash_path and result.ccdash_path.exists()
    assert rp.meatywiki_writeback.exists()
    assert rp.skillbom_candidate.exists()
    assert rp.ccdash_event.exists()
    assert result.requires_review is False

    # MeatyWiki mirror + schema-valid front matter.
    mwb_front, _ = load_md(rp.meatywiki_writeback)
    assert validate(mwb_front, "meatywiki_writeback").ok
    assert mwb_front["status"] == "written"
    mirror_sources = list((paths.meatywiki / "sources").glob("*.md"))
    assert mirror_sources, "expected a meatywiki/sources/<slug>.md mirror"

    # SkillBOM mirror + schema-valid front matter.
    skb_front, _ = load_md(rp.skillbom_candidate)
    assert validate(skb_front, "skillbom_candidate").ok
    assert skb_front["proposed_skillbom_id"] == "skill_research_swarm_v0"
    skb_mirror = list((paths.skillmeat / "skillboms").glob("*.md"))
    assert skb_mirror, "expected a skillmeat/skillboms/<id>.md mirror"

    # CCDash mirror.
    ccdash_mirror = list((paths.ccdash / "events").glob("*.yaml"))
    assert ccdash_mirror, "expected a ccdash/events/<id>.yaml mirror"

    # SkillBOM index updated.
    idx = load_yaml(paths.registries / "skillbom_index.yaml")
    assert any(i.get("proposed_skillbom_id") == "skill_research_swarm_v0" for i in idx["items"])


def test_emit_ccdash_event_is_schema_valid_with_reuse_flags(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    event_id = telemetry.emit_ccdash_event(run_id, paths=paths)
    rp = paths.run_paths(run_id)
    event = load_yaml(rp.ccdash_event)
    assert event["event_id"] == event_id

    assert validate(event, "ccdash_event").ok
    assert event["run_id"] == run_id
    assert event["project"] == "Research Foundry"
    assert event["reuse"]["meatywiki_writeback_candidate"] is True
    assert event["reuse"]["skillbom_candidate"] is True
    assert event["metrics"]["claims_total"] >= 1
    assert event["metrics"]["source_cards_created"] >= 1

    # Mirrored into ccdash/events/<event_id>.yaml.
    mirror = paths.ccdash / "events" / f"{event['event_id']}.yaml"
    assert mirror.exists()


def test_summarize_daily_writes_rollup(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)
    telemetry.emit_ccdash_event(run_id, paths=paths)

    summary_path = telemetry.summarize("daily", paths=paths)
    assert summary_path.exists()

    daily_files = list((paths.ccdash / "daily").glob("*.yaml"))
    assert daily_files, "expected a ccdash/daily/<date>.yaml rollup"

    rollup = load_yaml(summary_path)
    assert rollup["period"] == "daily"
    assert rollup["totals"]["runs"] >= 1
    assert rollup["totals"]["claims_total"] >= 1
    assert rollup["reuse_candidates"]["skillbom_candidates"] >= 1


def test_council_review_is_schema_valid(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    council_path = writeback.council_review(
        run_id,
        roles=["domain_reviewer", "claim_critic", "governance_officer"],
        paths=paths,
    )
    packet = load_yaml(council_path)
    assert validate(packet, "review_packet").ok
    assert len(packet["members"]) == 3
    assert packet["output"]["decision"] in {"approve", "revise", "required_block"}


def test_work_sensitive_run_requires_review(tmp_foundry: FoundryPaths):
    paths = tmp_foundry
    run_id = _build_run(paths, sensitivity="work_sensitive")
    writeback.build_bundle(run_id, verify=True, paths=paths)

    result = writeback.writeback(run_id, paths=paths)
    rp = paths.run_paths(run_id)

    assert result.requires_review is True

    # MeatyWiki writeback is proposed (not written) and NOT mirrored into the wiki.
    mwb_front, _ = load_md(rp.meatywiki_writeback)
    assert mwb_front["status"] == "proposed"
    assert mwb_front["approval"]["required"] is True
    assert not list((paths.meatywiki / "sources").glob("*.md"))

    # The CCDash event flags human review.
    event = load_yaml(rp.ccdash_event)
    assert event["human_review"]["required"] is True
