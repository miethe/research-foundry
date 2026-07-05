"""Unit tests for report anchor derivation (public multi-user release, P2 Wave A).

Covers ``derive_report_anchors()`` directly (pure-function tests: determinism,
section/paragraph addressing, claim-span extraction, relation inference,
missing-claim handling, hash-drift/"stale" detection, and the documented
top-level-paragraph-only scope) plus its wiring into ``export_run()`` (the
``report_anchors`` field on ``run.json``).

No LLM, no network, no clock dependence — every test is a synchronous,
in-process call against synthetic markdown/claim fixtures.
"""

from __future__ import annotations

import hashlib
from typing import Any

from research_foundry.paths import FoundryPaths
from research_foundry.services import export_service as svc
from research_foundry.yamlio import dump_yaml

# --------------------------------------------------------------------------
# fixtures
# --------------------------------------------------------------------------

REPORT_MD = """# Title

Root paragraph with no section. [claim:clm_001]

## Introduction

This is an opening paragraph with no claims.

## Findings

Alpha supports the thesis. [claim:clm_001] Beta contradicts it. [claim:clm_002]

A second paragraph in Findings with an inference. [claim:clm_003]

## Findings

Duplicate heading paragraph. [claim:clm_999]
"""

CLAIMS: list[dict[str, Any]] = [
    {"claim_id": "clm_001", "status": "supported"},
    {"claim_id": "clm_002", "status": "contradicted"},
    {"claim_id": "clm_003", "status": "inference"},
    # clm_999 intentionally absent — exercises the dangling-tag path.
]


def _by_position(blocks: list[dict[str, Any]]) -> dict[tuple[str | None, int], dict[str, Any]]:
    return {(b["section_id"], b["paragraph_ordinal"]): b for b in blocks}


# --------------------------------------------------------------------------
# null / empty input
# --------------------------------------------------------------------------


def test_returns_none_when_report_draft_is_none() -> None:
    assert svc.derive_report_anchors(None, CLAIMS) is None


def test_returns_none_when_report_draft_is_empty_string() -> None:
    assert svc.derive_report_anchors("", CLAIMS) is None


def test_returns_empty_list_when_report_has_no_paragraphs() -> None:
    assert svc.derive_report_anchors("# Title Only\n", CLAIMS) == []


# --------------------------------------------------------------------------
# shape, section addressing, ordinals
# --------------------------------------------------------------------------


def test_block_shape_has_exactly_the_d8_fields() -> None:
    blocks = svc.derive_report_anchors(REPORT_MD, CLAIMS)
    assert blocks
    block = blocks[0]
    assert set(block.keys()) == {
        "block_id", "section_id", "paragraph_ordinal", "text_hash", "claim_links",
    }
    link = next(b for b in blocks if b["claim_links"])["claim_links"][0]
    assert set(link.keys()) == {
        "claim_id", "span_start", "span_end", "relation", "link_status",
    }


def test_section_id_none_before_first_heading_and_slugified_after() -> None:
    blocks = _by_position(svc.derive_report_anchors(REPORT_MD, CLAIMS))
    assert (None, 0) in blocks  # root paragraph before any h2/h3
    assert (None, 0) not in {(k[0], k[1]) for k in blocks if k[0] == "introduction"}
    assert ("introduction", 0) in blocks
    assert ("findings", 0) in blocks
    assert ("findings", 1) in blocks


def test_duplicate_heading_slug_gets_dash_2_suffix() -> None:
    """Two '## Findings' headings must not collide — mirrors the frontend's
    extractHeadings() duplicate-slug suffixing (reportOutlineUtils.ts)."""
    blocks = svc.derive_report_anchors(REPORT_MD, CLAIMS)
    section_ids = {b["section_id"] for b in blocks}
    assert "findings" in section_ids
    assert "findings-2" in section_ids


def test_paragraph_ordinal_resets_per_section() -> None:
    blocks = _by_position(svc.derive_report_anchors(REPORT_MD, CLAIMS))
    # "findings" has two paragraphs -> ordinals 0 and 1; "findings-2" restarts at 0.
    assert ("findings", 0) in blocks
    assert ("findings", 1) in blocks
    assert ("findings-2", 0) in blocks
    assert ("findings-2", 1) not in blocks


def test_h1_is_not_a_section_boundary() -> None:
    """h1 is the run title, not tracked as a section (matches the frontend outline,
    which only extracts h2/h3)."""
    blocks = svc.derive_report_anchors("# Title\n\nBody paragraph.\n", CLAIMS)
    assert blocks[0]["section_id"] is None


# --------------------------------------------------------------------------
# claim-span extraction + relation inference
# --------------------------------------------------------------------------


def test_claim_span_extraction_offsets_slice_the_tag_out_of_normalized_text() -> None:
    blocks = _by_position(svc.derive_report_anchors(REPORT_MD, CLAIMS))
    block = blocks[("findings", 0)]
    normalized = "Alpha supports the thesis. [claim:clm_001] Beta contradicts it. [claim:clm_002]"
    for link in block["claim_links"]:
        tag = f"[claim:{link['claim_id']}]"
        assert normalized[link["span_start"]:link["span_end"]] == tag


def test_multiple_claim_tags_in_one_block_each_get_a_link_entry() -> None:
    blocks = _by_position(svc.derive_report_anchors(REPORT_MD, CLAIMS))
    block = blocks[("findings", 0)]
    ids_in_order = [link["claim_id"] for link in block["claim_links"]]
    assert ids_in_order == ["clm_001", "clm_002"]


def test_relation_inferred_from_linked_claim_status() -> None:
    blocks = _by_position(svc.derive_report_anchors(REPORT_MD, CLAIMS))
    findings0 = {link["claim_id"]: link for link in blocks[("findings", 0)]["claim_links"]}
    findings1 = {link["claim_id"]: link for link in blocks[("findings", 1)]["claim_links"]}
    assert findings0["clm_001"]["relation"] == "supports"       # status: supported
    assert findings0["clm_002"]["relation"] == "contradicts"    # status: contradicted
    assert findings1["clm_003"]["relation"] == "inferred_from"  # status: inference


def test_relation_defaults_to_context_for_unmapped_status() -> None:
    claims = [{"claim_id": "clm_x", "status": "unsupported"}]
    blocks = svc.derive_report_anchors("## Sec\n\nSee it. [claim:clm_x]\n", claims)
    assert blocks[0]["claim_links"][0]["relation"] == "context"


def test_missing_claim_yields_missing_claim_status_and_null_relation() -> None:
    blocks = _by_position(svc.derive_report_anchors(REPORT_MD, CLAIMS))
    dangling = blocks[("findings-2", 0)]["claim_links"][0]
    assert dangling["claim_id"] == "clm_999"
    assert dangling["link_status"] == "missing_claim"
    assert dangling["relation"] is None


def test_resolved_claim_link_status_is_linked_without_previous_blocks() -> None:
    blocks = _by_position(svc.derive_report_anchors(REPORT_MD, CLAIMS))
    for link in blocks[("findings", 0)]["claim_links"]:
        assert link["link_status"] == "linked"


# --------------------------------------------------------------------------
# top-level-paragraph-only scope (documented gap: lists/blockquotes excluded)
# --------------------------------------------------------------------------


def test_list_and_blockquote_paragraphs_are_not_anchored() -> None:
    md = (
        "## Sec\n\n"
        "Top paragraph. [claim:clm_001]\n\n"
        "- List item one. [claim:clm_001]\n"
        "- List item two.\n\n"
        "> Blockquote paragraph. [claim:clm_001]\n\n"
        "Bottom paragraph. [claim:clm_001]\n"
    )
    claims = [{"claim_id": "clm_001", "status": "supported"}]
    blocks = svc.derive_report_anchors(md, claims)
    # Only the two top-level paragraphs are anchored; list/blockquote content
    # is excluded entirely in this pass (see derive_report_anchors docstring).
    assert len(blocks) == 2
    assert blocks[0]["paragraph_ordinal"] == 0
    assert blocks[1]["paragraph_ordinal"] == 1
    assert all(len(b["claim_links"]) == 1 for b in blocks)


# --------------------------------------------------------------------------
# determinism (hard constraint)
# --------------------------------------------------------------------------


def test_determinism_repeated_derivation_is_byte_identical() -> None:
    first = svc.derive_report_anchors(REPORT_MD, CLAIMS)
    second = svc.derive_report_anchors(REPORT_MD, CLAIMS)
    assert first == second
    assert first is not second  # genuinely recomputed, not a cached reference


def test_identical_text_in_two_paragraphs_still_gets_distinct_block_ids() -> None:
    """block_id incorporates the ordinal, so repeated identical paragraphs
    (e.g. a templated report) never collide."""
    md = "## Sec\n\nRepeated line.\n\nRepeated line.\n"
    blocks = svc.derive_report_anchors(md, [])
    assert blocks[0]["text_hash"] == blocks[1]["text_hash"]
    assert blocks[0]["block_id"] != blocks[1]["block_id"]


# --------------------------------------------------------------------------
# exact hashing recipe (regression guard for the contract handed to Waves B/C)
# --------------------------------------------------------------------------


def test_text_hash_matches_documented_formula() -> None:
    normalized = "Alpha paragraph text."
    blocks = svc.derive_report_anchors(f"## Sec\n\n{normalized}\n", [])
    expected = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    assert blocks[0]["text_hash"] == expected


def test_block_id_matches_documented_formula() -> None:
    normalized = "Alpha paragraph text."
    blocks = svc.derive_report_anchors(f"## Sec\n\n{normalized}\n", [])
    section_id = blocks[0]["section_id"]
    ordinal = blocks[0]["paragraph_ordinal"]
    key = f"{section_id or ''}\x1f{normalized}\x1f{ordinal}"
    expected = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    assert blocks[0]["block_id"] == expected


def test_normalization_collapses_soft_wrapped_whitespace() -> None:
    md = "## Sec\n\nLine one\ncontinues   here.\n"
    blocks = svc.derive_report_anchors(md, [])
    expected = hashlib.sha1(b"Line one continues here.").hexdigest()[:12]
    assert blocks[0]["text_hash"] == expected


# --------------------------------------------------------------------------
# drift detection ("stale" link_status) — the required deliverable behavior
# --------------------------------------------------------------------------


def test_drift_edit_paragraph_then_hash_mismatch_yields_stale() -> None:
    claims = [{"claim_id": "clm_001", "status": "supported"}]
    original = "## Sec\n\nOriginal paragraph text. [claim:clm_001]\n"
    edited = "## Sec\n\nEdited paragraph text now differs. [claim:clm_001]\n"

    baseline = svc.derive_report_anchors(original, claims)
    assert baseline[0]["claim_links"][0]["link_status"] == "linked"

    after_edit = svc.derive_report_anchors(edited, claims, previous_blocks=baseline)
    assert after_edit[0]["text_hash"] != baseline[0]["text_hash"]
    assert after_edit[0]["claim_links"][0]["link_status"] == "stale"


def test_drift_status_heals_once_previous_blocks_reflect_the_edit() -> None:
    """Re-deriving unchanged content against its OWN just-computed anchors
    (no further edit) reports 'linked' again — 'stale' only fires on a real
    text_hash mismatch at the same (section_id, paragraph_ordinal)."""
    claims = [{"claim_id": "clm_001", "status": "supported"}]
    edited = "## Sec\n\nEdited paragraph text now differs. [claim:clm_001]\n"

    once = svc.derive_report_anchors(edited, claims)
    again = svc.derive_report_anchors(edited, claims, previous_blocks=once)
    assert again[0]["claim_links"][0]["link_status"] == "linked"


def test_drift_unrelated_previous_position_does_not_flag_stale() -> None:
    claims = [{"claim_id": "clm_001", "status": "supported"}]
    md = "## Sec\n\nParagraph text. [claim:clm_001]\n"
    unrelated_previous = [
        {"section_id": "other", "paragraph_ordinal": 0, "text_hash": "deadbeefcafe"}
    ]
    blocks = svc.derive_report_anchors(md, claims, previous_blocks=unrelated_previous)
    assert blocks[0]["claim_links"][0]["link_status"] == "linked"


# --------------------------------------------------------------------------
# export_run() wiring — additive run.json field
# --------------------------------------------------------------------------


def _build_minimal_run(paths: FoundryPaths, run_id: str, *, report_md: str | None) -> None:
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {
            "schema_version": "0.1",
            "type": "run",
            "run_id": run_id,
            "status": "planned",
        },
        rp.run_yaml,
    )
    dump_yaml(
        {
            "schema_version": "0.1",
            "claims": [
                {"claim_id": "clm_001", "text": "alpha", "materiality": "core",
                 "claim_type": "factual", "status": "supported", "confidence": "high",
                 "sources": [], "inference_basis": {"from_claims": [], "reasoning_summary": None}},
            ],
        },
        rp.claim_ledger,
    )
    if report_md is not None:
        rp.report_draft.write_text(report_md, encoding="utf-8")


def test_export_run_emits_report_anchors_matching_pure_function(
    tmp_foundry: FoundryPaths,
) -> None:
    run_id = "rf_run_anchors001"
    _build_minimal_run(
        tmp_foundry,
        run_id,
        report_md="## Sec\n\nAlpha claim paragraph. [claim:clm_001]\n",
    )
    data = svc.export_run(tmp_foundry, run_id)

    assert data["report_anchors"] is not None
    expected = svc.derive_report_anchors(data["report_draft"], data["claims"])
    assert data["report_anchors"] == expected
    assert data["report_anchors"][0]["claim_links"][0]["link_status"] == "linked"


def test_export_run_report_anchors_null_when_no_report_draft(
    tmp_foundry: FoundryPaths,
) -> None:
    run_id = "rf_run_anchors002"
    _build_minimal_run(tmp_foundry, run_id, report_md=None)
    data = svc.export_run(tmp_foundry, run_id)
    assert data["report_draft"] is None
    assert data["report_anchors"] is None


def test_export_run_report_anchors_reexport_is_byte_identical(
    tmp_foundry: FoundryPaths,
) -> None:
    """Hard constraint: re-exporting the same on-disk run twice yields
    byte-identical report_anchors (no timestamps/randomness leak in)."""
    run_id = "rf_run_anchors003"
    _build_minimal_run(
        tmp_foundry,
        run_id,
        report_md="## Sec\n\nRepeat me. [claim:clm_001]\n\nAnd again. [claim:clm_001]\n",
    )
    first = svc.export_run(tmp_foundry, run_id)
    second = svc.export_run(tmp_foundry, run_id)
    assert first["report_anchors"] == second["report_anchors"]


def test_schema_version_bumped_for_report_anchors(tmp_foundry: FoundryPaths) -> None:
    assert svc.EXPORT_SCHEMA_VERSION == "1.4"
    run_id = "rf_run_anchors004"
    _build_minimal_run(tmp_foundry, run_id, report_md="## Sec\n\nBody.\n")
    data = svc.export_run(tmp_foundry, run_id)
    assert data["schema_version"] == "1.4"
    assert "report_anchors" in data
