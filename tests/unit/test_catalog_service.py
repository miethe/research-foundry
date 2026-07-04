"""Unit tests for the shared evidence catalog service (public-multiuser P1).

Covers: import determinism + idempotency (including double-import), ID
stability, mapping correctness for every item_type, fail-closed sensitivity
exclusion (including an unrecognized label), FTS5 + LIKE-fallback search, and
schema rebuild on a ``PRAGMA user_version`` mismatch. All tests run against
synthetic YAML/Markdown fixtures — no real run data, no network, no LLM.
"""

from __future__ import annotations

import hashlib
import sqlite3
from typing import Any

import pytest

from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths, RunPaths
from research_foundry.services import catalog_service as svc
from research_foundry.yamlio import dump_yaml, load_yaml

# ---------------------------------------------------------------------------
# Synthetic-run fixture builder
# ---------------------------------------------------------------------------


def _write_threshold(paths: FoundryPaths, label: str) -> None:
    """Pin ``foundry.yaml``'s ``viewer.sensitivity_threshold`` deterministically.

    ``tmp_foundry`` copies this repo's own dev ``foundry.yaml`` verbatim
    (currently ``client_sensitive``, i.e. max-permissive) — tests that need a
    specific gating threshold must set it explicitly rather than rely on the
    ambient default.
    """

    data: dict[str, Any] = load_yaml(paths.foundry_yaml) or {}
    data.setdefault("foundry", {})
    data["foundry"].setdefault("viewer", {})
    data["foundry"]["viewer"]["sensitivity_threshold"] = label
    dump_yaml(data, paths.foundry_yaml)


_DEFAULT_LINKED_PROJECTS = ["proj-alpha"]


def build_catalog_run(
    paths: FoundryPaths,
    run_id: str = "rf_run_catalog001",
    *,
    sensitivity: str = "personal",
    linked_projects: list[str] | None = None,
    category: str | None = "AI Engineering",
) -> RunPaths:
    """A run exercising every item_type + the mixed-point / unknown-label cases.

    Item inventory (see the module-level assertions in the tests below for the
    derived expectations):
      - source items: src_alpha (plain public), src_mixed (public card, one
        work_sensitive point — exercises per-citation rank probing),
        src_unknown (bogus/unrecognized card sensitivity — fail-closed).
      - claim items: clm_001 (cites src_alpha; has report_locations),
        clm_mixed (cites both src_mixed points), clm_unknown (cites
        src_unknown), clm_dangling (cites a source card that does not exist).
      - inference item: clm_inf (from_claims=["clm_001"]; has
        report_locations).
      - report item: one, from the report_draft below.
      - writeback items: meatywiki + ccdash (both writeback files planted).
      - reusable_output items: none (export_run() never emits
        reusable_output_candidates — see catalog_service's module docstring).
    """

    if linked_projects is None:
        linked_projects = list(_DEFAULT_LINKED_PROJECTS)
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()

    dump_yaml(
        {
            "schema_version": "0.1",
            "type": "run",
            "run_id": run_id,
            "intent_id": f"intent_{run_id}",
            "status": "planned",
            "sensitivity": sensitivity,
            "created_at": "2026-06-13T09:41:00-04:00",
            "linked_projects": linked_projects,
            "category": category,
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
                {
                    "evidence_id": "ev_001",
                    "locator": "p1",
                    "summary": "alpha summary",
                    "quote": "ALPHA QUOTE",
                }
            ],
        },
        "",
        rp.sources / "src_alpha.md",
    )

    dump_md(
        {
            "type": "source_card",
            "source_card_id": "src_mixed",
            "sensitivity": "public",
            "source": {"title": "Mixed Source", "source_type": "paper"},
            "trust": "medium",
            "usage": "paraphrase",
            "extracted_points": [
                {
                    "evidence_id": "ev_pub",
                    "locator": "m1",
                    "summary": "public point",
                    "quote": "MIXED PUBLIC QUOTE",
                },
                {
                    "evidence_id": "ev_sens",
                    "locator": "m2",
                    "summary": "sensitive point",
                    "quote": "MIXED SENSITIVE QUOTE",
                    "sensitivity": "work_sensitive",
                },
            ],
        },
        "",
        rp.sources / "src_mixed.md",
    )

    dump_md(
        {
            "type": "source_card",
            "source_card_id": "src_unknown",
            "sensitivity": "bogus_label",
            "source": {"title": "Unknown Sensitivity Source", "source_type": "web"},
            "trust": "low",
            "usage": "direct",
            "extracted_points": [
                {
                    "evidence_id": "ev_001",
                    "locator": "u1",
                    "summary": "unknown summary",
                    "quote": "UNKNOWN QUOTE",
                }
            ],
        },
        "",
        rp.sources / "src_unknown.md",
    )

    dump_yaml(
        {
            "id": f"ledger_{run_id}",
            "claims": [
                {
                    "claim_id": "clm_001",
                    "text": "Alpha is true and holds under scrutiny for the thesis.",
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
                    "report_locations": [{"file": "report_draft.md", "heading": "Alpha"}],
                },
                {
                    "claim_id": "clm_mixed",
                    "text": "Mixed evidence claim.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "mixed",
                    "confidence": "medium",
                    "sources": [
                        {
                            "source_card_id": "src_mixed",
                            "evidence_id": "ev_pub",
                            "relation": "supports",
                            "locator": "m1",
                        },
                        {
                            "source_card_id": "src_mixed",
                            "evidence_id": "ev_sens",
                            "relation": "supports",
                            "locator": "m2",
                        },
                    ],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                    "report_locations": [],
                },
                {
                    "claim_id": "clm_unknown",
                    "text": "Unknown sensitivity claim.",
                    "materiality": "background",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "low",
                    "sources": [
                        {
                            "source_card_id": "src_unknown",
                            "evidence_id": "ev_001",
                            "relation": "supports",
                            "locator": "u1",
                        }
                    ],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                    "report_locations": [],
                },
                {
                    "claim_id": "clm_inf",
                    "text": "Derived inference.",
                    "materiality": "core",
                    "claim_type": "inference",
                    "status": "inference",
                    "confidence": "low",
                    "sources": [],
                    "inference_basis": {
                        "from_claims": ["clm_001"],
                        "reasoning_summary": "Because alpha holds.",
                    },
                    "report_locations": [{"file": "report_draft.md", "heading": "Inference"}],
                },
                {
                    "claim_id": "clm_dangling",
                    "text": "Dangling claim.",
                    "materiality": "background",
                    "claim_type": "factual",
                    "status": "unsupported",
                    "confidence": "low",
                    "sources": [
                        {
                            "source_card_id": "src_missing",
                            "evidence_id": "ev_999",
                            "relation": "supports",
                            "locator": "x",
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
        "---\ntitle: Catalog Test Report\n---\n\n"
        "# Catalog Test Report\n\n"
        "Alpha holds and supports the thesis of this run. [claim:clm_001]\n\n"
        "## Details\n\nMore detail here about the inference. [claim:clm_inf]\n",
        encoding="utf-8",
    )

    dump_yaml({"run_id": run_id, "passed": True, "exit_code": 0, "checks": []}, rp.verification)
    dump_yaml(
        {
            "schema_version": "0.1",
            "run_id": run_id,
            "status": "verified",
            "counts": {"claims_total": 5, "claims_supported": 2},
            "governance": {"sensitivity": sensitivity, "approved_for_writeback": True},
        },
        rp.evidence_bundle,
    )

    rp.meatywiki_writeback.write_text("# Writeback\n", encoding="utf-8")
    dump_yaml({"url": "https://ccdash.local/e/1"}, rp.ccdash_event)

    return rp


# ---------------------------------------------------------------------------
# Import: determinism, idempotency, ID stability
# ---------------------------------------------------------------------------


def test_import_run_returns_item_count(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    result = svc.import_run(tmp_foundry, "rf_run_catalog001")
    # 4 claim + 1 inference + 3 source + 1 report + 0 reusable_output + 2 writeback
    assert result == {"run_id": "rf_run_catalog001", "items": 11}


def test_double_import_is_idempotent(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    first = svc.import_run(tmp_foundry, "rf_run_catalog001")
    second = svc.import_run(tmp_foundry, "rf_run_catalog001")
    assert first == second

    with svc._db(tmp_foundry) as conn:
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM catalog_items WHERE run_id = ?", ("rf_run_catalog001",)
        ).fetchone()
        assert count == 11
        (link_count,) = conn.execute(
            "SELECT COUNT(*) FROM catalog_links WHERE run_id = ?", ("rf_run_catalog001",)
        ).fetchone()
        assert link_count == 6  # 3 supports + 1 inferred_from + 2 contains


def test_item_ids_are_stable_across_imports(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")
    first = {
        i["local_ref"]: i["catalog_item_id"]
        for i in svc.search(tmp_foundry, run_id="rf_run_catalog001", page_size=200)["items"]
    }

    svc.import_run(tmp_foundry, "rf_run_catalog001")
    second = {
        i["local_ref"]: i["catalog_item_id"]
        for i in svc.search(tmp_foundry, run_id="rf_run_catalog001", page_size=200)["items"]
    }
    assert first == second
    assert (
        first["clm_001"]
        == "ci_" + hashlib.sha1(b"claim:rf_run_catalog001:clm_001").hexdigest()[:12]
    )


def test_deterministic_id_formula(tmp_foundry: FoundryPaths) -> None:
    assert svc._make_item_id("claim", "run_a", "clm_001") == svc._make_item_id(
        "claim", "run_a", "clm_001"
    )
    assert svc._make_item_id("claim", "run_a", "clm_001") != svc._make_item_id(
        "inference", "run_a", "clm_001"
    )
    expected = "ci_" + hashlib.sha1(b"claim:run_a:clm_001").hexdigest()[:12]
    assert svc._make_item_id("claim", "run_a", "clm_001") == expected


def test_reimport_after_fixture_change_replaces_rows(tmp_foundry: FoundryPaths) -> None:
    """Delete-then-insert: a claim removed from the ledger disappears on reimport."""

    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")

    # Rewrite the ledger with one fewer claim.
    dump_yaml(
        {
            "id": "ledger_rf_run_catalog001",
            "claims": [
                {
                    "claim_id": "clm_001",
                    "text": "Alpha is true.",
                    "materiality": "core",
                    "claim_type": "factual",
                    "status": "supported",
                    "confidence": "high",
                    "sources": [],
                    "inference_basis": {"from_claims": [], "reasoning_summary": None},
                    "report_locations": [],
                }
            ],
        },
        tmp_foundry.run_paths("rf_run_catalog001").claim_ledger,
    )
    svc.import_run(tmp_foundry, "rf_run_catalog001")

    with svc._db(tmp_foundry) as conn:
        (count,) = conn.execute(
            "SELECT COUNT(*) FROM catalog_items WHERE run_id = ? AND item_type = 'claim'",
            ("rf_run_catalog001",),
        ).fetchone()
        assert count == 1


def test_import_unknown_run_raises_catalog_error(tmp_foundry: FoundryPaths) -> None:
    with pytest.raises(svc.CatalogError):
        svc.import_run(tmp_foundry, "rf_run_does_not_exist")


def test_import_all_and_stats(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry, run_id="rf_run_a", sensitivity="public")
    build_catalog_run(tmp_foundry, run_id="rf_run_b", sensitivity="public")
    result = svc.import_all(tmp_foundry)
    assert result["runs"] == 2
    assert result["items"] == 22
    assert result["errors"] == []

    _write_threshold(tmp_foundry, "client_sensitive")
    s = svc.stats(tmp_foundry)
    assert s["runs_indexed"] == 2
    assert s["last_import_at"] is not None
    assert s["counts"]["claim"] == 6  # 3 visible claims/run (clm_unknown excluded) * 2 runs
    assert s["counts"]["inference"] == 2
    assert s["counts"]["source"] == 4  # src_alpha + src_mixed visible, src_unknown excluded, *2
    assert s["counts"]["report"] == 2
    assert s["counts"]["writeback"] == 4


# ---------------------------------------------------------------------------
# Mapping correctness per item_type
# ---------------------------------------------------------------------------


def test_claim_mapping(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    item_id = svc._make_item_id("claim", "rf_run_catalog001", "clm_001")
    item = svc.get_item(tmp_foundry, item_id)
    assert item is not None
    assert item["item_type"] == "claim"
    assert item["title"].startswith("Alpha is true")
    assert item["status"] == "supported"
    assert item["trust_label"] == "supported"
    assert item["confidence"] == "high"
    assert item["source_count"] == 1
    assert item["project"] == "proj-alpha"
    assert item["payload"]["cited_sources"][0]["source_card_id"] == "src_alpha"
    assert item["payload"]["inference_basis"]["from_claims"] == []


def test_inference_mapping(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    item_id = svc._make_item_id("inference", "rf_run_catalog001", "clm_inf")
    item = svc.get_item(tmp_foundry, item_id)
    assert item is not None
    assert item["item_type"] == "inference"
    assert item["summary"] == "Because alpha holds."
    assert item["payload"]["inference_basis"]["from_claims"] == ["clm_001"]

    # inference -> claim ("inferred_from") link recorded both ways.
    claim_item_id = svc._make_item_id("claim", "rf_run_catalog001", "clm_001")
    outgoing = {(link["catalog_item_id"], link["relation"]) for link in item["links"]["outgoing"]}
    assert (claim_item_id, "inferred_from") in outgoing


def test_source_mapping_and_dedupe(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    item_id = svc._make_item_id("source", "rf_run_catalog001", "src_mixed")
    item = svc.get_item(tmp_foundry, item_id)
    assert item is not None
    assert item["item_type"] == "source"
    assert item["title"] == "Mixed Source"
    assert item["trust_label"] == "medium"
    # Deduped: one source item even though src_mixed is cited by 2 evidence points
    # from the same claim.
    assert item["source_count"] == 1  # cited by exactly 1 distinct claim
    assert len(item["payload"]["evidence_points"]) == 2


def test_report_mapping(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    item_id = svc._make_item_id("report", "rf_run_catalog001", "report")
    item = svc.get_item(tmp_foundry, item_id)
    assert item is not None
    assert item["item_type"] == "report"
    assert item["title"] == "Catalog Test Report"
    assert item["summary"] == "Alpha holds and supports the thesis of this run. [claim:clm_001]"
    assert "report_draft" in item["payload"]
    assert item["payload"]["claim_counts"] is not None

    # report -> claim ("contains") links for both report_locations-bearing claims.
    outgoing = {(link["catalog_item_id"], link["relation"]) for link in item["links"]["outgoing"]}
    clm_001_id = svc._make_item_id("claim", "rf_run_catalog001", "clm_001")
    clm_inf_id = svc._make_item_id("inference", "rf_run_catalog001", "clm_inf")
    assert (clm_001_id, "contains") in outgoing
    assert (clm_inf_id, "contains") in outgoing


def test_writeback_mapping(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    item_id = svc._make_item_id("writeback", "rf_run_catalog001", "wb_meatywiki")
    item = svc.get_item(tmp_foundry, item_id)
    assert item is not None
    assert item["item_type"] == "writeback"
    # export_service always emits status="present" for writeback targets, which
    # normalizeWritebackStatus (LibraryScreen.tsx) maps to "other".
    assert item["status"] == "other"


def test_reusable_output_mapping_is_a_noop_today(tmp_foundry: FoundryPaths) -> None:
    """Documented deviation: export_run() never emits reusable_output_candidates."""

    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    result = svc.search(
        tmp_foundry, item_type="reusable_output", run_id="rf_run_catalog001"
    )
    assert result["items"] == []
    assert result["total"] == 0

    # But the mapper itself is correct and forward-compatible: feed it a
    # synthetic export dict with the field the plan describes.
    fake_export = {"reusable_output_candidates": [{"description": "A candidate output."}]}
    rows = svc._build_reusable_output_rows(
        fake_export, "run_x", project=None, created_at=None, run_sensitivity_rank=0
    )
    assert len(rows) == 1
    assert rows[0]["title"] == "A candidate output."
    assert rows[0]["item_type"] == "reusable_output"


# ---------------------------------------------------------------------------
# Sensitivity exclusion (fail-closed)
# ---------------------------------------------------------------------------


def test_sensitivity_exclusion_at_public_threshold(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "public")

    result = svc.search(tmp_foundry, run_id="rf_run_catalog001", page_size=200)
    local_refs = {i["local_ref"] for i in result["items"]}
    # src_alpha is public (rank 0); everything with run sensitivity="personal"
    # (rank 1) or above is excluded at threshold=public.
    assert local_refs == {"src_alpha"}


def test_sensitivity_exclusion_at_personal_threshold(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "personal")

    result = svc.search(tmp_foundry, run_id="rf_run_catalog001", page_size=200)
    local_refs = {i["local_ref"] for i in result["items"]}
    assert local_refs == {
        "src_alpha",
        "clm_001",
        "clm_dangling",
        "clm_inf",
        "report",
        "wb_meatywiki",
        "wb_ccdash",
    }
    # work_sensitive (src_mixed / clm_mixed) and unknown (src_unknown /
    # clm_unknown) must both be excluded.
    assert "src_mixed" not in local_refs
    assert "clm_mixed" not in local_refs
    assert "src_unknown" not in local_refs
    assert "clm_unknown" not in local_refs


def test_unknown_sensitivity_fails_closed_even_at_loosest_threshold(
    tmp_foundry: FoundryPaths,
) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")  # loosest defined threshold

    result = svc.search(tmp_foundry, run_id="rf_run_catalog001", page_size=200)
    local_refs = {i["local_ref"] for i in result["items"]}
    assert "src_unknown" not in local_refs
    assert "clm_unknown" not in local_refs

    item_id = svc._make_item_id("source", "rf_run_catalog001", "src_unknown")
    assert svc.get_item(tmp_foundry, item_id) is None


def test_visible_source_evidence_point_redaction(tmp_foundry: FoundryPaths) -> None:
    """A visible source item still redacts any point above the read threshold."""

    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "work_sensitive")

    item_id = svc._make_item_id("source", "rf_run_catalog001", "src_mixed")
    item = svc.get_item(tmp_foundry, item_id)
    assert item is not None
    points = {p["evidence_id"]: p for p in item["payload"]["evidence_points"]}
    assert points["ev_pub"]["quote"] == "MIXED PUBLIC QUOTE"
    # ev_sens itself is exactly at the threshold (work_sensitive == rank 2 ==
    # threshold rank 2) so it is NOT redacted (rank > threshold triggers
    # redaction, not rank >= threshold).
    assert points["ev_sens"]["quote"] == "MIXED SENSITIVE QUOTE"


def test_get_item_unknown_id_returns_none(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    assert svc.get_item(tmp_foundry, "ci_doesnotexist") is None


# ---------------------------------------------------------------------------
# Search: FTS + LIKE fallback
# ---------------------------------------------------------------------------


def test_search_fts_match(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    result = svc.search(tmp_foundry, q="alpha")
    refs = {i["local_ref"] for i in result["items"]}
    assert "clm_001" in refs
    assert "src_alpha" in refs


def test_search_no_match_returns_empty_with_facets(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    result = svc.search(tmp_foundry, q="zzzznomatch")
    assert result["items"] == []
    assert result["total"] == 0
    # Facets still reflect the full gated catalog, not the (empty) query result.
    assert "proj-alpha" in result["facets"]["projects"]


def test_search_like_fallback_when_fts_unavailable(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    monkeypatch.setattr(svc, "_fts_available", lambda conn: False)
    result = svc.search(tmp_foundry, q="alpha")
    refs = {i["local_ref"] for i in result["items"]}
    assert "clm_001" in refs
    assert "src_alpha" in refs


def test_search_filters_and_pagination(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    only_claims = svc.search(tmp_foundry, item_type="claim", page_size=2, page=1)
    assert len(only_claims["items"]) == 2
    # clm_001, clm_dangling, clm_mixed are visible "claim" items at
    # client_sensitive; clm_unknown (rank 4, unknown label) stays excluded.
    assert only_claims["total"] == 3

    by_project = svc.search(tmp_foundry, project="proj-alpha")
    assert by_project["total"] > 0
    assert all(i["project"] == "proj-alpha" for i in by_project["items"])


# ---------------------------------------------------------------------------
# Schema rebuild on user_version mismatch
# ---------------------------------------------------------------------------


def test_rebuild_on_user_version_mismatch(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")

    # Simulate a stale schema by corrupting user_version out-of-band.
    conn = sqlite3.connect(str(tmp_foundry.catalog_db))
    conn.execute("PRAGMA user_version = 999")
    conn.commit()
    conn.close()

    # Any subsequent connect() drops + recreates the schema (empties data).
    with svc._db(tmp_foundry) as conn:
        (version,) = conn.execute("PRAGMA user_version").fetchone()
        assert version == svc.SCHEMA_VERSION
        (count,) = conn.execute("SELECT COUNT(*) FROM catalog_items").fetchone()
        assert count == 0


def test_rebuild_reimports_everything(tmp_foundry: FoundryPaths) -> None:
    build_catalog_run(tmp_foundry, run_id="rf_run_a")
    build_catalog_run(tmp_foundry, run_id="rf_run_b")
    svc.import_all(tmp_foundry)

    result = svc.rebuild(tmp_foundry)
    assert result["runs"] == 2
    assert result["errors"] == []

    with svc._db(tmp_foundry) as conn:
        (count,) = conn.execute("SELECT COUNT(DISTINCT run_id) FROM catalog_items").fetchone()
        assert count == 2
