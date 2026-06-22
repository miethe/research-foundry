"""Tests for the decision_record writeback (Gap 1).

Covers:
- Fixture ledger with ≥1 inference/recommendation claim → decision_record produced
  with writeback_type: decision_record, Decision+Rationale populated from
  inference_basis, and Links to source claim IDs; schema-valid front-matter.
- Deterministic-only ledger (zero inference claims) → NO decision_record emitted
  and no error.
- skillbom purpose/known_failure_modes populated from claims when inference exists.
- decision_record is additive: source_note is still emitted alongside it.
- work_sensitive run: decision_record marked proposed, NOT mirrored into wiki.
- _render_decision_record exposed in writeback.__all__.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from research_foundry.frontmatter import load_md
from research_foundry.paths import FoundryPaths
from research_foundry.schemas import validate
from research_foundry.services import writeback
from research_foundry.services.capture import capture_idea, triage_idea
from research_foundry.services.claim_mapping import build_claim_ledger
from research_foundry.services.extraction import extract_run
from research_foundry.services.planning import plan_run
from research_foundry.services.source_cards import ingest_source
from research_foundry.services.synthesis import synthesize_report
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

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


def _inject_inference_claim(rp, *, claim_id: str = "clm_inf_001") -> None:
    """Append a synthetic inference/recommendation claim to the claim ledger."""

    ledger = load_yaml(rp.claim_ledger)
    if not isinstance(ledger, dict):
        ledger = {}
    claims = list(ledger.get("claims") or [])
    claims.append({
        "claim_id": claim_id,
        "text": "Agentic research workflows benefit from claim traceability gates.",
        "materiality": "material",
        "claim_type": "recommendation",
        "status": "inference",
        "confidence": "high",
        "sources": [],
        "inference_basis": {
            "from_claims": ["clm_001", "clm_002"],
            "reasoning_summary": (
                "Combining evidence on claim ledgers and unsupported-synthesis drift "
                "strongly implies that explicit traceability gates reduce errors."
            ),
        },
        "report_locations": [],
        "reviewer_notes": "",
    })
    ledger["claims"] = claims
    dump_yaml(ledger, rp.claim_ledger)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_decision_record_produced_with_inference_claim(tmp_foundry: FoundryPaths):
    """A ledger with ≥1 inference claim → decision_record written and schema-valid."""

    paths = tmp_foundry
    run_id = _build_run(paths)
    rp = paths.run_paths(run_id)
    _inject_inference_claim(rp)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    result = writeback.writeback(run_id, paths=paths)

    assert result.decision_record_path is not None
    assert result.decision_record_path.exists()

    front, body = load_md(result.decision_record_path)

    # Schema-valid front-matter.
    assert validate(front, "meatywiki_writeback").ok
    assert front["writeback_type"] == "decision_record"
    assert front["status"] == "written"

    # Key claims include the inference claim.
    claim_ids_in_front = [kc.get("claim_id") for kc in (front.get("key_claims") or [])]
    assert "clm_inf_001" in claim_ids_in_front

    # from_claims back-referenced in Links.
    links = front.get("links") or {}
    from_claims = links.get("from_claims") or []
    assert "clm_001" in from_claims
    assert "clm_002" in from_claims


def test_decision_record_body_has_decision_and_rationale(tmp_foundry: FoundryPaths):
    """Decision + Rationale sections are populated from inference_basis."""

    paths = tmp_foundry
    run_id = _build_run(paths)
    rp = paths.run_paths(run_id)
    _inject_inference_claim(rp)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    result = writeback.writeback(run_id, paths=paths)
    assert result.decision_record_path is not None

    _, body = load_md(result.decision_record_path)

    assert "## Decision" in body
    assert "## Rationale" in body
    assert "clm_inf_001" in body
    # The reasoning_summary text should appear in Rationale.
    assert "traceability gates reduce errors" in body


def test_decision_record_no_inference_claims_emits_nothing(tmp_foundry: FoundryPaths):
    """A deterministic-only ledger (zero inference claims) → no decision_record, no error."""

    paths = tmp_foundry
    run_id = _build_run(paths)
    rp = paths.run_paths(run_id)
    # Do NOT inject any inference claim — deterministic pipeline may or may not
    # produce inference claims; ensure the ledger has none.
    ledger = load_yaml(rp.claim_ledger)
    if isinstance(ledger, dict):
        claims = [c for c in (ledger.get("claims") or []) if (c or {}).get("status") != "inference"]
        ledger["claims"] = claims
        dump_yaml(ledger, rp.claim_ledger)

    writeback.build_bundle(run_id, verify=True, paths=paths)
    result = writeback.writeback(run_id, paths=paths)

    # No decision_record emitted; no exception.
    assert result.decision_record_path is None
    assert not rp.decision_record_writeback.exists()


def test_decision_record_does_not_replace_source_note(tmp_foundry: FoundryPaths):
    """decision_record is additive — source_note is still emitted."""

    paths = tmp_foundry
    run_id = _build_run(paths)
    rp = paths.run_paths(run_id)
    _inject_inference_claim(rp)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    result = writeback.writeback(run_id, paths=paths)

    assert result.meatywiki_path is not None
    assert result.meatywiki_path.exists()
    assert result.decision_record_path is not None
    assert result.decision_record_path.exists()

    source_note_front, _ = load_md(rp.meatywiki_writeback)
    assert source_note_front["writeback_type"] == "source_note"


def test_decision_record_mirrored_to_meatywiki_decisions(tmp_foundry: FoundryPaths):
    """For non-sensitive runs the decision_record is mirrored to meatywiki/decisions/."""

    paths = tmp_foundry
    (paths.meatywiki / "decisions").mkdir(parents=True, exist_ok=True)
    run_id = _build_run(paths)
    rp = paths.run_paths(run_id)
    _inject_inference_claim(rp)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    result = writeback.writeback(run_id, paths=paths)

    mirrors = list((paths.meatywiki / "decisions").glob("*.md"))
    assert mirrors, "expected a meatywiki/decisions/<slug>.md mirror"


def test_decision_record_work_sensitive_proposed_not_mirrored(tmp_foundry: FoundryPaths):
    """work_sensitive run: decision_record is proposed, NOT mirrored into the wiki."""

    paths = tmp_foundry
    (paths.meatywiki / "decisions").mkdir(parents=True, exist_ok=True)
    run_id = _build_run(paths, sensitivity="work_sensitive")
    rp = paths.run_paths(run_id)
    _inject_inference_claim(rp)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    result = writeback.writeback(run_id, paths=paths)

    assert result.decision_record_path is not None
    front, _ = load_md(rp.decision_record_writeback)
    assert front["status"] == "proposed"
    assert front["approval"]["required"] is True
    assert not list((paths.meatywiki / "decisions").glob("*.md"))


def test_skillbom_purpose_populated_from_inference_claims(tmp_foundry: FoundryPaths):
    """skillbom purpose is derived from the primary inference claim's reasoning_summary."""

    paths = tmp_foundry
    run_id = _build_run(paths)
    rp = paths.run_paths(run_id)
    _inject_inference_claim(rp)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    writeback.writeback(run_id, paths=paths)

    front, _ = load_md(rp.skillbom_candidate)
    assert validate(front, "skillbom_candidate").ok
    # purpose should have been overridden from the fixed stub.
    assert "traceability gates reduce errors" in front["purpose"]


def test_skillbom_purpose_static_when_no_inference(tmp_foundry: FoundryPaths):
    """skillbom purpose falls back to static stub when ledger has no inference claims."""

    paths = tmp_foundry
    run_id = _build_run(paths)
    rp = paths.run_paths(run_id)
    # Strip all inference claims.
    ledger = load_yaml(rp.claim_ledger)
    if isinstance(ledger, dict):
        ledger["claims"] = [
            c for c in (ledger.get("claims") or []) if (c or {}).get("status") != "inference"
        ]
        dump_yaml(ledger, rp.claim_ledger)
    writeback.build_bundle(run_id, verify=True, paths=paths)

    writeback.writeback(run_id, paths=paths)

    front, _ = load_md(rp.skillbom_candidate)
    assert "Reusable research swarm" in front["purpose"]


def test_render_decision_record_in_dunder_all():
    """_render_decision_record must be exported so the backfill script can import it."""

    assert "_render_decision_record" in writeback.__all__
