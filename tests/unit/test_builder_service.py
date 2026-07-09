"""Unit tests for the Report Builder draft store (public-multiuser P3 Wave D).

Covers: file-canonical draft round-trip (create -> edit -> export -> reload),
block/claim-link/source-link CRUD + denormalized coverage recomputation,
revision history round-trip, seeding a draft from a run's report_anchors, and
the catalog.db draft-index rebuild-safety guarantee (drop+rebuild must lose
zero draft content — plan D10/D11, landmine #3). D13 verification checks are
covered separately in test_verification_draft.py.
"""

from __future__ import annotations

import pytest

from research_foundry.errors import NotFoundError
from research_foundry.frontmatter import dump_md, split_frontmatter
from research_foundry.paths import FoundryPaths, RunPaths
from research_foundry.services import builder_service as bsvc
from research_foundry.services import catalog_service as csvc
from research_foundry.yamlio import dump_yaml

# ---------------------------------------------------------------------------
# Fixture helper: a minimal run with a claim ledger + report_draft.md
# ---------------------------------------------------------------------------


def _plant_run(paths: FoundryPaths, run_id: str = "rf_run_builder001") -> RunPaths:
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {
            "schema_version": "0.1",
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "status": "verified",
            "sensitivity": "public",
            "created_at": "2026-06-13T09:41:00+00:00",
        },
        rp.run_yaml,
    )
    dump_md(
        {
            "type": "source_card",
            "source_card_id": "src_alpha",
            "sensitivity": "public",
            "source": {
                "title": "Alpha Source",
                "source_type": "web",
                "locator": {"url": "https://example.test/alpha"},
            },
            "trust": "high",
            "usage": "direct",
            "extracted_points": [
                {"evidence_id": "ev_001", "locator": "p1", "summary": "alpha summary", "quote": "ALPHA QUOTE"}
            ],
        },
        "",
        rp.sources / "src_alpha.md",
    )
    dump_yaml(
        {
            "id": f"ledger_{run_id}",
            "claims": [
                {
                    "claim_id": "clm_a",
                    "text": "Alpha holds under scrutiny.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [
                        {
                            "source_card_id": "src_alpha",
                            "evidence_id": "ev_001",
                            "relation": "supports",
                            "locator": "p1",
                        }
                    ],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                    "report_locations": [],
                },
            ],
        },
        rp.claim_ledger,
    )
    rp.report_draft.write_text(
        "# Report Title\n\n"
        "Alpha holds under scrutiny for the thesis. [claim:clm_a]\n\n"
        "## Notes\n\n"
        "This is background narrative text with no claim tag.\n",
        encoding="utf-8",
    )
    dump_yaml(
        {
            "schema_version": "0.1",
            "run_id": run_id,
            "status": "verified",
            "counts": {"claims_total": 1},
            "governance": {"sensitivity": "public", "approved_for_writeback": False},
        },
        rp.evidence_bundle,
    )
    return rp


# ---------------------------------------------------------------------------
# Create / load / list / delete
# ---------------------------------------------------------------------------


def test_create_blank_draft_persists_to_disk(tmp_foundry: FoundryPaths) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="My New Report")

    assert draft["report_draft_id"].startswith("rpt_")
    assert draft["type"] == "report_draft"
    assert draft["status"] == "draft"
    assert draft["origin"] == "blank"
    assert draft["blocks"] == []
    assert draft["workspace_id"] is None
    assert draft["created_by"] is None

    on_disk = tmp_foundry.report_draft_dir(draft["report_draft_id"]) / "draft.yaml"
    assert on_disk.exists()

    reloaded = bsvc.load_draft(tmp_foundry, draft["report_draft_id"])
    assert reloaded == draft


def test_create_draft_rejects_unknown_enums(tmp_foundry: FoundryPaths) -> None:
    with pytest.raises(bsvc.BuilderError):
        bsvc.create_draft(tmp_foundry, title="Bad", origin="nonsense")
    with pytest.raises(bsvc.BuilderError):
        bsvc.create_draft(tmp_foundry, title="Bad", sensitivity="nonsense")


def test_load_draft_missing_raises_not_found(tmp_foundry: FoundryPaths) -> None:
    with pytest.raises(NotFoundError):
        bsvc.load_draft(tmp_foundry, "rpt_does_not_exist")


# ---------------------------------------------------------------------------
# R2 CRITICAL fix: path traversal via unvalidated draft/version ids
# ---------------------------------------------------------------------------


def test_load_draft_rejects_path_traversal_id(tmp_foundry: FoundryPaths) -> None:
    """A ``report_id.startswith('rpt_')`` PREFIX check lets a payload like
    ``rpt_../../../etc`` straight through unchanged. The service layer must
    reject any id that doesn't match the strict full-string shape, regardless
    of caller (API, CLI, or direct import)."""
    for bad_id in ("rpt_../../../etc", "../../etc/passwd", "rpt_..", "rpt_/etc/passwd", ""):
        with pytest.raises(NotFoundError):
            bsvc.load_draft(tmp_foundry, bad_id)


def test_delete_draft_rejects_path_traversal_id_without_touching_disk(
    tmp_foundry: FoundryPaths,
) -> None:
    """delete_draft must refuse a malformed/traversal id and must NEVER reach
    ``shutil.rmtree`` on anything outside ``reports/drafts/``."""
    sentinel_dir = tmp_foundry.root / "sentinel"
    sentinel_dir.mkdir()
    (sentinel_dir / "keep.txt").write_text("keep me", encoding="utf-8")

    with pytest.raises(NotFoundError):
        bsvc.delete_draft(tmp_foundry, "rpt_../../sentinel")

    assert (sentinel_dir / "keep.txt").exists()


def test_get_revision_rejects_path_traversal_version_id(tmp_foundry: FoundryPaths) -> None:
    """``report_version_id`` gets the same strict-shape treatment as
    ``report_draft_id`` — a real draft dir must not leak a read outside its
    own ``revisions/`` subdirectory via a crafted version id."""
    draft = bsvc.create_draft(tmp_foundry, title="Traversal Version Test")
    report_draft_id = draft["report_draft_id"]
    for bad_version_id in ("rptv_../../../etc", "../../etc/passwd", "rptv_.."):
        with pytest.raises(NotFoundError):
            bsvc.get_revision(tmp_foundry, report_draft_id, bad_version_id)


def test_list_drafts_scans_disk(tmp_foundry: FoundryPaths) -> None:
    d1 = bsvc.create_draft(tmp_foundry, title="Alpha Draft")
    d2 = bsvc.create_draft(tmp_foundry, title="Beta Draft")
    summaries = bsvc.list_drafts(tmp_foundry)
    ids = {s["report_draft_id"] for s in summaries}
    assert {d1["report_draft_id"], d2["report_draft_id"]} <= ids


def test_create_draft_avoids_clobber_on_id_collision(tmp_foundry: FoundryPaths) -> None:
    """R2 HIGH fix: a pre-existing draft directory at the deterministic base
    id (title + day, no time component) must not be clobbered by a
    same-titled ``create_draft`` — this simulates the losing side of the
    check-then-act race the old ``disambiguate_id``-based minting had.
    Exclusive ``os.mkdir`` makes the id claim atomic, so create_draft must
    pick a disambiguated id instead of silently overwriting."""

    from research_foundry.ids import report_draft_id as mint_base

    base_id = mint_base("Collision Test")
    colliding_dir = tmp_foundry.report_draft_dir(base_id)
    colliding_dir.mkdir(parents=True)
    (colliding_dir / "draft.yaml").write_text("sentinel: do-not-clobber\n", encoding="utf-8")

    draft = bsvc.create_draft(tmp_foundry, title="Collision Test")

    assert draft["report_draft_id"] != base_id
    assert (colliding_dir / "draft.yaml").read_text(encoding="utf-8") == "sentinel: do-not-clobber\n"


def test_delete_draft_removes_files_and_index(tmp_foundry: FoundryPaths) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="Ephemeral")
    report_draft_id = draft["report_draft_id"]
    assert csvc.get_draft_index(tmp_foundry, report_draft_id) is not None

    bsvc.delete_draft(tmp_foundry, report_draft_id)

    assert not tmp_foundry.report_draft_dir(report_draft_id).exists()
    assert csvc.get_draft_index(tmp_foundry, report_draft_id) is None
    with pytest.raises(NotFoundError):
        bsvc.load_draft(tmp_foundry, report_draft_id)


# ---------------------------------------------------------------------------
# Block CRUD
# ---------------------------------------------------------------------------


def test_add_update_delete_block(tmp_foundry: FoundryPaths) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="Block Test")
    report_draft_id = draft["report_draft_id"]

    draft = bsvc.add_block(tmp_foundry, report_draft_id, block_type="paragraph", markdown="Hello world.")
    assert len(draft["blocks"]) == 1
    block = draft["blocks"][0]
    assert block["block_type"] == "paragraph"
    assert block["order"] == 0
    assert block["materiality"] == "material"
    # No claim links yet -> unsupported (material paragraph, no links).
    assert block["coverage_status"] == "unsupported"

    draft = bsvc.update_block(tmp_foundry, report_draft_id, block["block_id"], markdown="Updated text.")
    assert draft["blocks"][0]["markdown"] == "Updated text."

    draft = bsvc.delete_block(tmp_foundry, report_draft_id, block["block_id"])
    assert draft["blocks"] == []
    with pytest.raises(NotFoundError):
        bsvc.delete_block(tmp_foundry, report_draft_id, block["block_id"])


def test_add_block_rejects_unknown_block_type(tmp_foundry: FoundryPaths) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="Bad Block")
    with pytest.raises(bsvc.BuilderError):
        bsvc.add_block(tmp_foundry, draft["report_draft_id"], block_type="nonsense")


def test_narrative_block_is_exempt_from_support(tmp_foundry: FoundryPaths) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="Narrative Test")
    draft = bsvc.add_block(
        tmp_foundry,
        draft["report_draft_id"],
        block_type="paragraph",
        markdown="Just scene-setting prose.",
        materiality="narrative",
    )
    assert draft["blocks"][0]["coverage_status"] == "narrative"


def test_reorder_blocks(tmp_foundry: FoundryPaths) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="Reorder Test")
    report_draft_id = draft["report_draft_id"]
    draft = bsvc.add_block(tmp_foundry, report_draft_id, markdown="One")
    draft = bsvc.add_block(tmp_foundry, report_draft_id, markdown="Two")
    draft = bsvc.add_block(tmp_foundry, report_draft_id, markdown="Three")
    ids = [b["block_id"] for b in draft["blocks"]]

    reordered_ids = list(reversed(ids))
    draft = bsvc.reorder_blocks(tmp_foundry, report_draft_id, reordered_ids)
    by_id = {b["block_id"]: b["order"] for b in draft["blocks"]}
    assert by_id[reordered_ids[0]] == 0
    assert by_id[reordered_ids[1]] == 1
    assert by_id[reordered_ids[2]] == 2

    with pytest.raises(bsvc.BuilderError):
        bsvc.reorder_blocks(tmp_foundry, report_draft_id, [ids[0]])  # not a permutation


# ---------------------------------------------------------------------------
# Claim links
# ---------------------------------------------------------------------------


def test_add_claim_link_resolves_against_run_ledger(tmp_foundry: FoundryPaths) -> None:
    _plant_run(tmp_foundry, "rf_run_claimlink")
    draft = bsvc.create_draft(tmp_foundry, title="Claim Link Test")
    report_draft_id = draft["report_draft_id"]
    draft = bsvc.add_block(tmp_foundry, report_draft_id, markdown="Alpha holds under scrutiny.")
    block_id = draft["blocks"][0]["block_id"]

    draft = bsvc.add_claim_link(
        tmp_foundry,
        report_draft_id,
        block_id=block_id,
        claim_id="clm_a",
        source_run_id="rf_run_claimlink",
    )

    block = draft["blocks"][0]
    assert "[claim:clm_a]" in block["markdown"]
    assert block["linked_claim_ids"] == ["clm_a"]
    assert block["coverage_status"] == "supported"

    link = draft["claim_links"][0]
    assert link["claim_id"] == "clm_a"
    assert link["link_status"] == "linked"
    assert link["relation"] == "supports"  # inferred from claim status "supported"
    assert link["quote_text_hash"] is not None
    # Default span covers the whole (post-tag-insertion) normalized block —
    # paragraph-level drift detection, matching P2's text_hash intent.
    assert link["span_start"] == 0
    assert link["span_end"] == len(block["markdown"])


def test_add_claim_link_missing_claim_is_unsupported(tmp_foundry: FoundryPaths) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="Missing Claim Test")
    report_draft_id = draft["report_draft_id"]
    draft = bsvc.add_block(tmp_foundry, report_draft_id, markdown="Ghost claim text.")
    block_id = draft["blocks"][0]["block_id"]

    draft = bsvc.add_claim_link(tmp_foundry, report_draft_id, block_id=block_id, claim_id="clm_ghost")

    link = draft["claim_links"][0]
    assert link["link_status"] == "missing_claim"
    assert draft["blocks"][0]["coverage_status"] == "unsupported"


def test_remove_claim_link_recomputes_coverage(tmp_foundry: FoundryPaths) -> None:
    _plant_run(tmp_foundry, "rf_run_removelink")
    draft = bsvc.create_draft(tmp_foundry, title="Remove Link Test")
    report_draft_id = draft["report_draft_id"]
    draft = bsvc.add_block(tmp_foundry, report_draft_id, markdown="Alpha text.")
    block_id = draft["blocks"][0]["block_id"]
    draft = bsvc.add_claim_link(
        tmp_foundry, report_draft_id, block_id=block_id, claim_id="clm_a", source_run_id="rf_run_removelink"
    )
    link_id = draft["claim_links"][0]["claim_link_id"]
    assert draft["blocks"][0]["coverage_status"] == "supported"

    draft = bsvc.remove_claim_link(tmp_foundry, report_draft_id, link_id)
    assert draft["claim_links"] == []
    assert draft["blocks"][0]["coverage_status"] == "unsupported"

    with pytest.raises(NotFoundError):
        bsvc.remove_claim_link(tmp_foundry, report_draft_id, link_id)


def test_add_claim_link_rejects_unknown_relation(tmp_foundry: FoundryPaths) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="Bad Relation")
    report_draft_id = draft["report_draft_id"]
    draft = bsvc.add_block(tmp_foundry, report_draft_id, markdown="Text.")
    block_id = draft["blocks"][0]["block_id"]
    with pytest.raises(bsvc.BuilderError):
        bsvc.add_claim_link(
            tmp_foundry, report_draft_id, block_id=block_id, claim_id="clm_x", relation="nonsense"
        )


# ---------------------------------------------------------------------------
# Source links
# ---------------------------------------------------------------------------


def test_add_remove_source_link_denormalizes_block(tmp_foundry: FoundryPaths) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="Source Link Test")
    report_draft_id = draft["report_draft_id"]
    draft = bsvc.add_block(tmp_foundry, report_draft_id, block_type="quote", markdown="A quotation.")
    block_id = draft["blocks"][0]["block_id"]

    draft = bsvc.add_source_link(
        tmp_foundry, report_draft_id, source_card_id="src_alpha", run_id="rf_run_x", block_id=block_id
    )
    assert draft["blocks"][0]["linked_source_ids"] == ["src_alpha"]
    link_id = draft["source_links"][0]["source_link_id"]

    draft = bsvc.remove_source_link(tmp_foundry, report_draft_id, link_id)
    assert draft["blocks"][0]["linked_source_ids"] == []
    with pytest.raises(NotFoundError):
        bsvc.remove_source_link(tmp_foundry, report_draft_id, link_id)


# ---------------------------------------------------------------------------
# Revisions
# ---------------------------------------------------------------------------


def test_revision_round_trip_preserves_anchors(tmp_foundry: FoundryPaths) -> None:
    _plant_run(tmp_foundry, "rf_run_revtest")
    draft = bsvc.create_draft(tmp_foundry, title="Revision Test")
    report_draft_id = draft["report_draft_id"]
    draft = bsvc.add_block(tmp_foundry, report_draft_id, markdown="Alpha holds under scrutiny.")
    block_id = draft["blocks"][0]["block_id"]
    draft = bsvc.add_claim_link(
        tmp_foundry, report_draft_id, block_id=block_id, claim_id="clm_a", source_run_id="rf_run_revtest"
    )
    original_markdown = draft["blocks"][0]["markdown"]
    original_hash = draft["claim_links"][0]["quote_text_hash"]

    pointer = bsvc.create_revision(tmp_foundry, report_draft_id, note="v1 checkpoint")
    assert pointer["report_version_id"].startswith("rptv_")

    revisions = bsvc.list_revisions(tmp_foundry, report_draft_id)
    assert len(revisions) == 1
    assert revisions[0]["report_version_id"] == pointer["report_version_id"]

    snapshot = bsvc.get_revision(tmp_foundry, report_draft_id, pointer["report_version_id"])
    assert snapshot["blocks"][0]["markdown"] == original_markdown
    assert snapshot["claim_links"][0]["quote_text_hash"] == original_hash

    # Drift the live draft's block text (simulates an edit after the checkpoint).
    draft = bsvc.update_block(tmp_foundry, report_draft_id, block_id, markdown="Alpha no longer holds.")
    assert draft["blocks"][0]["markdown"] != original_markdown

    # Restoring must bring back the exact pre-drift block text + hash (anchors preserved).
    restored = bsvc.restore_revision(tmp_foundry, report_draft_id, pointer["report_version_id"])
    assert restored["blocks"][0]["markdown"] == original_markdown
    assert restored["claim_links"][0]["quote_text_hash"] == original_hash
    assert restored["blocks"][0]["block_id"] == block_id


def test_get_revision_missing_raises(tmp_foundry: FoundryPaths) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="No Revisions")
    with pytest.raises(NotFoundError):
        bsvc.get_revision(tmp_foundry, draft["report_draft_id"], "rptv_ghost")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def test_export_markdown_has_frontmatter_and_stable_claim_tags(tmp_foundry: FoundryPaths) -> None:
    _plant_run(tmp_foundry, "rf_run_export")
    draft = bsvc.create_draft(tmp_foundry, title="Export Test", sensitivity="public")
    report_draft_id = draft["report_draft_id"]
    draft = bsvc.add_block(tmp_foundry, report_draft_id, block_type="heading", markdown="Findings")
    draft = bsvc.add_block(tmp_foundry, report_draft_id, markdown="Alpha holds under scrutiny.")
    block_id = draft["blocks"][1]["block_id"]
    bsvc.add_claim_link(
        tmp_foundry, report_draft_id, block_id=block_id, claim_id="clm_a", source_run_id="rf_run_export"
    )

    rendered = bsvc.export_markdown(tmp_foundry, report_draft_id)
    meta, body = split_frontmatter(rendered)
    assert meta["type"] == "research_report"
    assert meta["report_id"] == report_draft_id
    assert meta["title"] == "Export Test"
    assert "## Findings" in body
    assert "[claim:clm_a]" in body


# ---------------------------------------------------------------------------
# Create-from-run
# ---------------------------------------------------------------------------


def test_create_draft_from_run_seeds_blocks_and_claim_links(tmp_foundry: FoundryPaths) -> None:
    _plant_run(tmp_foundry, "rf_run_seed")
    draft = bsvc.create_draft_from_run(tmp_foundry, run_id="rf_run_seed")

    assert draft["origin"] == "run"
    assert draft["source_run_id"] == "rf_run_seed"
    block_types = [b["block_type"] for b in draft["blocks"]]
    assert "heading" in block_types
    assert block_types.count("paragraph") == 2

    linked_paragraph = next(
        b for b in draft["blocks"] if b["block_type"] == "paragraph" and "clm_a" in b["linked_claim_ids"]
    )
    assert "[claim:clm_a]" in linked_paragraph["markdown"]
    assert linked_paragraph["coverage_status"] == "supported"

    claim_link = next(cl for cl in draft["claim_links"] if cl["claim_id"] == "clm_a")
    assert claim_link["link_status"] == "linked"
    assert claim_link["relation"] == "supports"
    assert claim_link["source_run_id"] == "rf_run_seed"


# ---------------------------------------------------------------------------
# catalog.db draft index: rebuild safety (landmine #3)
# ---------------------------------------------------------------------------


def test_reindex_all_drafts_survives_catalog_schema_rebuild(tmp_foundry: FoundryPaths) -> None:
    """A catalog.db drop+rebuild must lose ZERO draft content.

    Plants two drafts (one with claim/source links), captures their on-disk
    draft.yaml content + derived index rows, forces a full schema drop via
    catalog_service.rebuild_schema() (the exact operation a user_version bump
    triggers — landmine #3), reindexes purely from disk via
    builder_service.reindex_all_drafts(), and asserts both the files AND the
    rebuilt index are byte-for-byte/field-for-field identical to before.
    """

    _plant_run(tmp_foundry, "rf_run_rebuild")
    d1 = bsvc.create_draft(tmp_foundry, title="Keep Me One", sensitivity="personal")
    d1 = bsvc.add_block(tmp_foundry, d1["report_draft_id"], markdown="Alpha holds under scrutiny.")
    bsvc.add_claim_link(
        tmp_foundry,
        d1["report_draft_id"],
        block_id=d1["blocks"][0]["block_id"],
        claim_id="clm_a",
        source_run_id="rf_run_rebuild",
    )
    d2 = bsvc.create_draft(tmp_foundry, title="Keep Me Two")

    d1_id, d2_id = d1["report_draft_id"], d2["report_draft_id"]
    draft_yaml_path_1 = tmp_foundry.report_draft_dir(d1_id) / "draft.yaml"
    draft_yaml_path_2 = tmp_foundry.report_draft_dir(d2_id) / "draft.yaml"
    before_text_1 = draft_yaml_path_1.read_text(encoding="utf-8")
    before_text_2 = draft_yaml_path_2.read_text(encoding="utf-8")
    before_index_1 = csvc.get_draft_index(tmp_foundry, d1_id)
    before_index_2 = csvc.get_draft_index(tmp_foundry, d2_id)
    assert before_index_1 is not None and before_index_2 is not None

    # Force the exact drop-and-recreate a user_version mismatch triggers.
    csvc.rebuild_schema(tmp_foundry)
    # Immediately after a schema drop, the index is empty (never touches files).
    assert csvc.get_draft_index(tmp_foundry, d1_id) is None
    assert csvc.get_draft_index(tmp_foundry, d2_id) is None
    # But the draft files on disk are completely untouched.
    assert draft_yaml_path_1.read_text(encoding="utf-8") == before_text_1
    assert draft_yaml_path_2.read_text(encoding="utf-8") == before_text_2

    result = bsvc.reindex_all_drafts(tmp_foundry)
    assert result["drafts"] == 2
    assert result["errors"] == []

    after_index_1 = csvc.get_draft_index(tmp_foundry, d1_id)
    after_index_2 = csvc.get_draft_index(tmp_foundry, d2_id)
    assert after_index_1 == before_index_1
    assert after_index_2 == before_index_2

    # And the draft content itself is still fully intact and loadable.
    reloaded_1 = bsvc.load_draft(tmp_foundry, d1_id)
    assert reloaded_1["blocks"][0]["markdown"].startswith("Alpha holds")
    assert reloaded_1["claim_links"][0]["claim_id"] == "clm_a"


def test_reindex_all_drafts_links_derived_from_run_report_item(tmp_foundry: FoundryPaths) -> None:
    """A draft created from a run gets a catalog_links 'derived_from' edge to
    that run's synthetic P1 'report' catalog item (plan D11)."""

    _plant_run(tmp_foundry, "rf_run_derived")
    draft = bsvc.create_draft_from_run(tmp_foundry, run_id="rf_run_derived")

    index = csvc.get_draft_index(tmp_foundry, draft["report_draft_id"])
    assert index is not None
    expected_report_item = csvc.report_item_id("rf_run_derived")
    relations = {(link["catalog_item_id"], link["relation"]) for link in index["links"]}
    assert (expected_report_item, "derived_from") in relations


# ---------------------------------------------------------------------------
# WKSP-304 Phase 3: query-layer workspace_id scoping (TASK-3.2)
# ---------------------------------------------------------------------------
#
# builder_service drafts are file-canonical (no SQL) — the flag-gated
# predicate's file-storage equivalent is applied in load_draft(): a
# cross-workspace draft is treated exactly like a missing one
# (NotFoundError). list_drafts() and export_markdown() thread `identity`
# straight into load_draft() rather than duplicating the check, so a single
# test per function proves (a) identity=None byte-identical, (b) identity +
# active isolation scopes, (c) identity + advisory/inactive (today's real
# default) stays unscoped.

from research_foundry.api.auth.provider import AuthIdentity  # noqa: E402
from research_foundry.config import FoundryConfig  # noqa: E402

_WS_MINE = AuthIdentity("u1", "ws-mine", ("owner",))
_WS_OTHER = AuthIdentity("u2", "ws-other", ("owner",))


def _force_isolation_active(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simulate ``workspace_isolation_enforcement`` resolving active.

    Monkeypatches :meth:`FoundryConfig.resolve_workspace_isolation_enforced`
    itself (never a private helper), so the test exercises the real Phase 1
    resolver's call contract. Every other test in the suite keeps the
    real, unmodified default (advisory — tmp_foundry's auth.provider is
    unset).
    """

    monkeypatch.setattr(
        FoundryConfig,
        "resolve_workspace_isolation_enforced",
        lambda self, provider, bind_host: True,
    )


def test_load_draft_identity_none_is_byte_identical(tmp_foundry: FoundryPaths) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="Scoping draft", workspace_id="ws-mine")
    draft_id = draft["report_draft_id"]

    baseline = bsvc.load_draft(tmp_foundry, draft_id)
    assert bsvc.load_draft(tmp_foundry, draft_id, identity=None) == baseline


def test_load_draft_identity_active_hides_cross_workspace_draft(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="Scoping draft", workspace_id="ws-mine")
    draft_id = draft["report_draft_id"]

    _force_isolation_active(monkeypatch)

    assert bsvc.load_draft(tmp_foundry, draft_id, identity=_WS_MINE)["report_draft_id"] == draft_id
    with pytest.raises(NotFoundError):
        bsvc.load_draft(tmp_foundry, draft_id, identity=_WS_OTHER)


def test_load_draft_identity_present_but_inactive_stays_unscoped(
    tmp_foundry: FoundryPaths,
) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="Scoping draft", workspace_id="ws-mine")
    draft_id = draft["report_draft_id"]

    # No monkeypatch: real default resolves advisory (auth.provider unset).
    loaded = bsvc.load_draft(tmp_foundry, draft_id, identity=_WS_OTHER)
    assert loaded["report_draft_id"] == draft_id


def test_list_drafts_workspace_scoping(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """(a)/(b)/(c) for list_drafts(), which threads identity into load_draft()."""

    mine = bsvc.create_draft(tmp_foundry, title="Mine", workspace_id="ws-mine")
    other = bsvc.create_draft(tmp_foundry, title="Other", workspace_id="ws-other")

    baseline = {d["report_draft_id"] for d in bsvc.list_drafts(tmp_foundry)}
    assert baseline == {mine["report_draft_id"], other["report_draft_id"]}

    # (a) identity=None byte-identical.
    assert {d["report_draft_id"] for d in bsvc.list_drafts(tmp_foundry, identity=None)} == baseline

    # (c) identity present, isolation advisory/inactive: unscoped (both visible).
    unscoped = {d["report_draft_id"] for d in bsvc.list_drafts(tmp_foundry, identity=_WS_MINE)}
    assert unscoped == baseline

    # (b) identity present, isolation active: only the matching-workspace draft.
    _force_isolation_active(monkeypatch)
    scoped = {d["report_draft_id"] for d in bsvc.list_drafts(tmp_foundry, identity=_WS_MINE)}
    assert scoped == {mine["report_draft_id"]}


def test_export_markdown_workspace_scoping(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    draft = bsvc.create_draft(tmp_foundry, title="Exportable", workspace_id="ws-mine")
    draft_id = draft["report_draft_id"]

    baseline = bsvc.export_markdown(tmp_foundry, draft_id)
    assert bsvc.export_markdown(tmp_foundry, draft_id, identity=None) == baseline
    # (c) advisory/inactive: unscoped.
    assert bsvc.export_markdown(tmp_foundry, draft_id, identity=_WS_OTHER) == baseline

    # (b) active: cross-workspace export is denied the same way load_draft is.
    _force_isolation_active(monkeypatch)
    assert bsvc.export_markdown(tmp_foundry, draft_id, identity=_WS_MINE) == baseline
    with pytest.raises(NotFoundError):
        bsvc.export_markdown(tmp_foundry, draft_id, identity=_WS_OTHER)
