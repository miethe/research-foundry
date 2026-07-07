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
    include_unknown: bool = True,
    include_multi_source_claim: bool = False,
) -> RunPaths:
    """A run exercising every item_type + the mixed-point / unknown-label cases.

    Item inventory (see the module-level assertions in the tests below for the
    derived expectations):
      - source items: src_alpha (plain public), src_mixed (public card, one
        work_sensitive point — exercises per-citation rank probing),
        src_unknown (bogus/unrecognized card sensitivity — fail-closed; only
        planted when ``include_unknown``).
      - claim items: clm_001 (cites src_alpha; has report_locations),
        clm_mixed (cites both src_mixed points), clm_unknown (cites
        src_unknown; only planted when ``include_unknown``), clm_dangling
        (cites a source card that does not exist).
      - inference item: clm_inf (from_claims=["clm_001"]; has
        report_locations).
      - report item: one, from the report_draft below.
      - writeback items: meatywiki + ccdash (both writeback files planted).
      - reusable_output items: none (export_run() never emits
        reusable_output_candidates — see catalog_service's module docstring).

    ``include_unknown=False`` omits src_unknown/clm_unknown entirely — used
    by tests that need the report/reusable_output item to stay *visible*
    (F1's ``run_content_max`` would otherwise permanently fail-closed to the
    unknown rank for every item in the run, since it maxes over ALL claims
    and cited sources).

    ``include_multi_source_claim=True`` additionally plants clm_multi, which
    cites BOTH src_alpha (low rank) and src_mixed's elevated point — giving a
    source (src_alpha) an incoming "supports" edge from a claim (clm_multi)
    whose own rank is strictly higher than the source's, the scenario F3's
    link-visibility fix targets.
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

    if include_unknown:
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

    claims: list[dict[str, Any]] = [
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
    ]
    if include_unknown:
        claims.append(
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
            }
        )
    claims.append(
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
        }
    )
    claims.append(
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
        }
    )
    if include_multi_source_claim:
        claims.append(
            {
                "claim_id": "clm_multi",
                "text": "Claim citing both a low- and a high-sensitivity source.",
                "materiality": "core",
                "claim_type": "factual",
                "status": "supported",
                "confidence": "medium",
                "sources": [
                    {
                        "source_card_id": "src_alpha",
                        "evidence_id": "ev_001",
                        "relation": "supports",
                        "locator": "p1",
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
            }
        )

    dump_yaml(
        {
            "id": f"ledger_{run_id}",
            "claims": claims,
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
    # include_unknown=False: an unknown-sensitivity claim/source anywhere in
    # the run now (correctly, per F1) poisons run_content_max for the
    # report item too, hiding it at every defined threshold. Unknown-label
    # exclusion itself is covered by test_unknown_sensitivity_fails_closed_*;
    # this test is about the counts/aggregation shape, so it uses a "clean"
    # fixture that keeps the report visible and counts stable.
    build_catalog_run(tmp_foundry, run_id="rf_run_a", sensitivity="public", include_unknown=False)
    build_catalog_run(tmp_foundry, run_id="rf_run_b", sensitivity="public", include_unknown=False)
    result = svc.import_all(tmp_foundry)
    assert result["runs"] == 2
    assert result["items"] == 18  # (3 claim + 1 inference + 2 source + 1 report + 2 writeback) * 2
    assert result["errors"] == []

    _write_threshold(tmp_foundry, "client_sensitive")
    s = svc.stats(tmp_foundry)
    assert s["runs_indexed"] == 2
    assert s["last_import_at"] is not None
    assert s["counts"]["claim"] == 6  # clm_001 + clm_mixed + clm_dangling, * 2 runs
    assert s["counts"]["inference"] == 2
    assert s["counts"]["source"] == 4  # src_alpha + src_mixed, * 2 runs
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
    # include_unknown=False: F1 floors the report's sensitivity to
    # run_content_max (max over every claim/source in the run, not just
    # report_locations-linked ones); the default fixture's unknown-label
    # claim/source would push that to the unknown rank and hide the report
    # at every defined threshold. This test is about field mapping, not
    # sensitivity, so it uses the unknown-free variant to keep the report
    # visible at client_sensitive (see
    # test_report_sensitivity_propagates_unknown_label_fail_closed for the
    # unknown-propagation case).
    build_catalog_run(tmp_foundry, include_unknown=False)
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
        fake_export, "run_x", project=None, created_at=None, sensitivity_rank=0
    )
    assert len(rows) == 1
    assert rows[0]["title"] == "A candidate output."
    assert rows[0]["item_type"] == "reusable_output"


# ---------------------------------------------------------------------------
# Sensitivity exclusion (fail-closed)
# ---------------------------------------------------------------------------


def test_sensitivity_exclusion_at_public_threshold(tmp_foundry: FoundryPaths) -> None:
    """F2: every item floors at the run's own sensitivity — src_alpha is
    card-labeled "public", but the run itself is "personal", so it must NOT
    leak at threshold=public (previously it leaked at its own rank alone)."""

    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "public")

    result = svc.search(tmp_foundry, run_id="rf_run_catalog001", page_size=200)
    # Run sensitivity is "personal" (rank 1); every item in the run — sources
    # included — now floors at rank >= 1, so nothing is visible at
    # threshold=public (rank 0).
    assert result["items"] == []
    assert result["total"] == 0


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
        "wb_meatywiki",
        "wb_ccdash",
    }
    # work_sensitive (src_mixed / clm_mixed) and unknown (src_unknown /
    # clm_unknown) must both be excluded.
    assert "src_mixed" not in local_refs
    assert "clm_mixed" not in local_refs
    assert "src_unknown" not in local_refs
    assert "clm_unknown" not in local_refs
    # F1: the report's sensitivity is run_content_max — the strictest rank
    # across every claim/source in the run (clm_mixed/src_mixed alone push it
    # to work_sensitive, before even counting the unknown-label items) — not
    # just the run's own "personal" label, so it is excluded here too.
    assert "report" not in local_refs


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


def test_source_sensitivity_floors_to_run_rank(tmp_foundry: FoundryPaths) -> None:
    """F2: a source item's sensitivity is max(run sensitivity, its own
    effective rank) — a card labeled "public" inside a "personal" run must
    not be visible at threshold=public, only from threshold=personal on."""

    build_catalog_run(tmp_foundry, sensitivity="personal")
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    src_alpha_id = svc._make_item_id("source", "rf_run_catalog001", "src_alpha")

    _write_threshold(tmp_foundry, "public")
    assert svc.get_item(tmp_foundry, src_alpha_id) is None
    result = svc.search(tmp_foundry, run_id="rf_run_catalog001", item_type="source", page_size=200)
    assert result["items"] == []

    _write_threshold(tmp_foundry, "personal")
    item = svc.get_item(tmp_foundry, src_alpha_id)
    assert item is not None
    assert item["sensitivity"] == "personal"


def test_report_sensitivity_floors_to_max_content_rank(tmp_foundry: FoundryPaths) -> None:
    """F1: report/reusable_output sensitivity is run_content_max — the
    strictest effective rank across every claim/source in the run — not just
    the run's own label. clm_mixed/src_mixed are work_sensitive even though
    the run itself is "personal", so the report must NOT be visible at
    threshold=personal (it would have been, pre-fix)."""

    build_catalog_run(tmp_foundry, sensitivity="personal", include_unknown=False)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    report_id = svc._make_item_id("report", "rf_run_catalog001", "report")

    _write_threshold(tmp_foundry, "personal")
    assert svc.get_item(tmp_foundry, report_id) is None

    _write_threshold(tmp_foundry, "work_sensitive")
    item = svc.get_item(tmp_foundry, report_id)
    assert item is not None
    assert item["sensitivity"] == "work_sensitive"


def test_report_sensitivity_propagates_unknown_label_fail_closed(
    tmp_foundry: FoundryPaths,
) -> None:
    """F1 + fail-closed: an unrecognized sensitivity label ANYWHERE in the
    run (even on a claim/source with no report_locations) poisons
    run_content_max, hiding the report at every defined threshold — including
    the loosest (client_sensitive). writeback items stay pinned to the run's
    own sensitivity and are unaffected."""

    build_catalog_run(tmp_foundry, sensitivity="personal")  # include_unknown=True (default)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    report_id = svc._make_item_id("report", "rf_run_catalog001", "report")
    assert svc.get_item(tmp_foundry, report_id) is None

    rows, _links = svc._build_catalog_rows(tmp_foundry, "rf_run_catalog001")
    report_row = next(r for r in rows if r["item_type"] == "report")
    assert report_row["sensitivity_rank"] == svc._UNKNOWN_RANK
    assert report_row["sensitivity"] == "unknown"

    writeback_rows = [r for r in rows if r["item_type"] == "writeback"]
    assert writeback_rows
    assert all(r["sensitivity_rank"] == svc._rank("personal") for r in writeback_rows)


def test_get_item_filters_hidden_link_endpoints(tmp_foundry: FoundryPaths) -> None:
    """F3: get_item() must not surface a link edge to an item that is itself
    over-threshold — that leaks a hidden catalog_item_id (and its relation)
    even though the requested item is visible. clm_multi cites both src_alpha
    (low rank) and src_mixed's elevated point, so clm_multi's own rank
    (work_sensitive) exceeds src_alpha's (personal) — src_alpha's incoming
    "supports" edge from clm_multi must disappear once clm_multi itself is
    over-threshold."""

    build_catalog_run(tmp_foundry, sensitivity="personal", include_multi_source_claim=True)
    svc.import_run(tmp_foundry, "rf_run_catalog001")

    src_alpha_id = svc._make_item_id("source", "rf_run_catalog001", "src_alpha")
    clm_001_id = svc._make_item_id("claim", "rf_run_catalog001", "clm_001")
    clm_multi_id = svc._make_item_id("claim", "rf_run_catalog001", "clm_multi")

    _write_threshold(tmp_foundry, "personal")
    item = svc.get_item(tmp_foundry, src_alpha_id)
    assert item is not None
    incoming_ids = {link["catalog_item_id"] for link in item["links"]["incoming"]}
    assert clm_001_id in incoming_ids  # visible citer stays
    assert clm_multi_id not in incoming_ids  # over-threshold citer must not leak

    _write_threshold(tmp_foundry, "work_sensitive")
    item2 = svc.get_item(tmp_foundry, src_alpha_id)
    assert item2 is not None
    incoming_ids2 = {link["catalog_item_id"] for link in item2["links"]["incoming"]}
    assert clm_multi_id in incoming_ids2  # visible once threshold covers it too


def test_stats_runs_indexed_excludes_fully_hidden_runs(tmp_foundry: FoundryPaths) -> None:
    """F7: runs_indexed counts only runs with >=1 item visible at the
    resolved threshold — a global COUNT(*) over catalog_import_log leaks the
    existence of a run that is entirely above threshold."""

    build_catalog_run(tmp_foundry, run_id="rf_run_pub", sensitivity="public", include_unknown=False)
    build_catalog_run(
        tmp_foundry, run_id="rf_run_hidden", sensitivity="client_sensitive", include_unknown=False
    )
    result = svc.import_all(tmp_foundry)
    assert result["errors"] == []

    _write_threshold(tmp_foundry, "public")
    s = svc.stats(tmp_foundry)
    assert s["runs_indexed"] == 1  # rf_run_hidden has zero visible items at "public"
    assert s["last_import_at"] is not None  # last_import_at stays global


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


def test_fts_query_strips_degenerate_tokens() -> None:
    """F9: a trailing bare quote must not degenerate into an empty ""* token
    that ANDs the whole match to zero results; NUL/control chars are also
    stripped rather than reaching the FTS5 parser."""

    assert svc._fts_query("alpha") == '"alpha"*'
    # 'alpha "' previously produced '"alpha"* AND ""*' (matches nothing).
    assert svc._fts_query('alpha "') == '"alpha"*'
    # A lone quote mark has no valid token left at all.
    assert svc._fts_query('"') is None
    assert svc._fts_query("   ") is None
    # Control characters (including NUL) are stripped, not treated as
    # separators — they simply vanish from the token.
    assert svc._fts_query("a\x00b") == '"ab"*'
    assert svc._fts_query("\x00\x01\x02") is None


def test_search_trailing_quote_query_still_matches(tmp_foundry: FoundryPaths) -> None:
    """F9 regression: q='alpha "' must behave like q='alpha', not return
    zero results."""

    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    result = svc.search(tmp_foundry, q='alpha "')
    refs = {i["local_ref"] for i in result["items"]}
    assert "clm_001" in refs
    assert "src_alpha" in refs


def test_search_null_byte_query_does_not_raise(tmp_foundry: FoundryPaths) -> None:
    """F9 regression: a NUL byte in the query string must not raise
    sqlite3.OperationalError — it is stripped, and an all-control-character
    query is treated as no query at all."""

    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    result = svc.search(tmp_foundry, q="alpha\x00")
    refs = {i["local_ref"] for i in result["items"]}
    assert "src_alpha" in refs

    result_all_control = svc.search(tmp_foundry, q="\x00\x01", run_id="rf_run_catalog001")
    assert result_all_control["total"] > 0  # no valid token -> treated as no query


def test_search_falls_back_to_like_on_fts_operational_error(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F9: any FTS5 MATCH syntax error we didn't sanitize away must fall back
    to the LIKE path instead of propagating as a 500."""

    build_catalog_run(tmp_foundry)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    # Simulate a malformed MATCH expression slipping past sanitization.
    monkeypatch.setattr(svc, "_fts_query", lambda q: '"unterminated')
    result = svc.search(tmp_foundry, q="alpha")
    refs = {i["local_ref"] for i in result["items"]}
    assert "clm_001" in refs
    assert "src_alpha" in refs


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


def test_rebuild_reindexes_report_drafts_from_disk(tmp_foundry: FoundryPaths) -> None:
    """R2 fix: ``rebuild()`` (the exact op ``rf catalog rebuild`` and a
    SCHEMA_VERSION bump both trigger) must also repopulate
    ``catalog_report_drafts`` from on-disk draft.yaml files —
    ``builder_service.reindex_all_drafts`` existed but was dead code, never
    called from here, leaving the draft index empty after any schema drop
    until a draft was individually mutated."""

    from research_foundry.services import builder_service as bsvc

    draft = bsvc.create_draft(tmp_foundry, title="Rebuild Reindex Test")
    report_draft_id = draft["report_draft_id"]
    assert svc.get_draft_index(tmp_foundry, report_draft_id) is not None

    result = svc.rebuild(tmp_foundry)
    assert result["drafts"] == 1
    assert result["draft_errors"] == []

    reindexed = svc.get_draft_index(tmp_foundry, report_draft_id)
    assert reindexed is not None
    assert reindexed["title"] == "Rebuild Reindex Test"


# ---------------------------------------------------------------------------
# --sensitivity-threshold override (CLI-local; service layer)
# ---------------------------------------------------------------------------


def test_sensitivity_threshold_override_search_reveals_hidden_items(
    tmp_foundry: FoundryPaths,
) -> None:
    """search() with sensitivity_threshold='client_sensitive' reveals items that
    ambient 'public' default hides."""

    build_catalog_run(tmp_foundry, sensitivity="client_sensitive", include_unknown=False)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "public")

    # Ambient threshold = public; run sensitivity = client_sensitive → nothing visible.
    ambient = svc.search(tmp_foundry, run_id="rf_run_catalog001", page_size=200)
    assert ambient["total"] == 0

    # Override to client_sensitive unlocks the run's items.
    with_override = svc.search(
        tmp_foundry,
        run_id="rf_run_catalog001",
        page_size=200,
        sensitivity_threshold="client_sensitive",
    )
    assert with_override["total"] > 0


def test_sensitivity_threshold_override_stats_reveals_hidden_items(
    tmp_foundry: FoundryPaths,
) -> None:
    """stats() with sensitivity_threshold='client_sensitive' reveals runs/counts
    that ambient 'public' default hides."""

    build_catalog_run(tmp_foundry, sensitivity="client_sensitive", include_unknown=False)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "public")

    ambient = svc.stats(tmp_foundry)
    assert ambient["runs_indexed"] == 0

    with_override = svc.stats(tmp_foundry, sensitivity_threshold="client_sensitive")
    assert with_override["runs_indexed"] == 1
    assert with_override["counts"]["claim"] > 0


def test_sensitivity_threshold_override_unknown_label_raises(
    tmp_foundry: FoundryPaths,
) -> None:
    """An unrecognized --sensitivity-threshold label raises ExportError (fail-closed)."""

    with pytest.raises(svc.ExportError):
        svc.stats(tmp_foundry, sensitivity_threshold="bogus_label")

    with pytest.raises(svc.ExportError):
        svc.search(tmp_foundry, sensitivity_threshold="bogus_label")


# ---------------------------------------------------------------------------
# Draft -> run/claim reverse catalog links (P5.7.3)
# ---------------------------------------------------------------------------


def test_get_item_citing_drafts_via_claim_link(tmp_foundry: FoundryPaths) -> None:
    """citing_drafts surfaces a draft that cites a claim via a 'cites' link."""

    build_catalog_run(tmp_foundry, include_unknown=False)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    claim_id = svc._make_item_id("claim", "rf_run_catalog001", "clm_001")

    svc.index_draft(
        tmp_foundry,
        {
            "report_draft_id": "draft_cites_claim",
            "title": "Citing Draft",
            "sensitivity": "public",
            "draft_path": "/tmp/draft_cites_claim.yaml",
        },
        links=[{"to_item_id": claim_id, "relation": "cites"}],
    )

    item = svc.get_item(tmp_foundry, claim_id)
    assert item is not None
    citing = item["links"]["citing_drafts"]
    assert len(citing) == 1
    assert citing[0]["report_draft_id"] == "draft_cites_claim"
    assert citing[0]["draft_name"] == "Citing Draft"
    assert citing[0]["relation"] == "cites"
    assert citing[0]["project_id"] is None


def test_get_item_citing_drafts_via_derived_from_link(tmp_foundry: FoundryPaths) -> None:
    """citing_drafts surfaces a draft whose source_run_id generates a
    'derived_from' link to the run's synthetic report catalog item."""

    build_catalog_run(tmp_foundry, include_unknown=False)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    report_id = svc.report_item_id("rf_run_catalog001")

    svc.index_draft(
        tmp_foundry,
        {
            "report_draft_id": "draft_derived",
            "title": "Run-derived Draft",
            "sensitivity": "public",
            "draft_path": "/tmp/draft_derived.yaml",
            "project_id": "proj-x",
        },
        links=[{"to_item_id": report_id, "relation": "derived_from"}],
    )

    item = svc.get_item(tmp_foundry, report_id)
    assert item is not None
    citing = item["links"]["citing_drafts"]
    match = next((d for d in citing if d["report_draft_id"] == "draft_derived"), None)
    assert match is not None, "draft_derived not found in citing_drafts"
    assert match["relation"] == "derived_from"
    assert match["project_id"] == "proj-x"


def test_get_item_citing_drafts_via_source_link(tmp_foundry: FoundryPaths) -> None:
    """citing_drafts surfaces a draft citing a source item."""

    build_catalog_run(tmp_foundry, include_unknown=False)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    source_id = svc._make_item_id("source", "rf_run_catalog001", "src_alpha")

    svc.index_draft(
        tmp_foundry,
        {
            "report_draft_id": "draft_cites_source",
            "title": "Source-citing Draft",
            "sensitivity": "public",
            "draft_path": "/tmp/draft_src.yaml",
        },
        links=[{"to_item_id": source_id, "relation": "cites"}],
    )

    item = svc.get_item(tmp_foundry, source_id)
    assert item is not None
    citing = item["links"]["citing_drafts"]
    assert len(citing) == 1
    assert citing[0]["report_draft_id"] == "draft_cites_source"
    assert citing[0]["relation"] == "cites"


def test_get_item_citing_drafts_zero_returns_empty_list(tmp_foundry: FoundryPaths) -> None:
    """Zero-citation case: no drafts citing the item; citing_drafts is [] with
    no regression to the existing incoming/outgoing lists."""

    build_catalog_run(tmp_foundry, include_unknown=False)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    claim_id = svc._make_item_id("claim", "rf_run_catalog001", "clm_001")
    item = svc.get_item(tmp_foundry, claim_id)
    assert item is not None

    # New field is present and empty
    assert item["links"]["citing_drafts"] == []

    # Existing fields retain their types and are unaffected
    assert isinstance(item["links"]["incoming"], list)
    assert isinstance(item["links"]["outgoing"], list)


def test_get_item_citing_drafts_sensitivity_threshold_gates_drafts(
    tmp_foundry: FoundryPaths,
) -> None:
    """A draft whose sensitivity_rank exceeds the resolved threshold must NOT
    appear in citing_drafts — leaking it would reveal a hidden draft's existence."""

    build_catalog_run(tmp_foundry, include_unknown=False)
    svc.import_run(tmp_foundry, "rf_run_catalog001")

    claim_id = svc._make_item_id("claim", "rf_run_catalog001", "clm_001")

    # public draft (rank 0) — visible at every threshold
    svc.index_draft(
        tmp_foundry,
        {
            "report_draft_id": "draft_public",
            "title": "Public Draft",
            "sensitivity": "public",
            "draft_path": "/tmp/draft_pub.yaml",
        },
        links=[{"to_item_id": claim_id, "relation": "cites"}],
    )

    # client_sensitive draft (rank 3) — only visible at threshold=client_sensitive
    svc.index_draft(
        tmp_foundry,
        {
            "report_draft_id": "draft_sensitive",
            "title": "Sensitive Draft",
            "sensitivity": "client_sensitive",
            "draft_path": "/tmp/draft_sens.yaml",
        },
        links=[{"to_item_id": claim_id, "relation": "cites"}],
    )

    # At personal threshold (rank 1): only the public draft is visible
    _write_threshold(tmp_foundry, "personal")
    item = svc.get_item(tmp_foundry, claim_id)
    assert item is not None
    ids = {d["report_draft_id"] for d in item["links"]["citing_drafts"]}
    assert "draft_public" in ids
    assert "draft_sensitive" not in ids

    # At client_sensitive threshold (rank 3): both drafts are visible
    _write_threshold(tmp_foundry, "client_sensitive")
    item2 = svc.get_item(tmp_foundry, claim_id)
    assert item2 is not None
    ids2 = {d["report_draft_id"] for d in item2["links"]["citing_drafts"]}
    assert "draft_public" in ids2
    assert "draft_sensitive" in ids2


def test_get_item_citing_drafts_rebuild_matches_incremental(
    tmp_foundry: FoundryPaths,
) -> None:
    """catalog rebuild (reindex_all_drafts path) followed by get_item() produces
    the same citing_drafts as the incremental write path (_save_draft ->
    _sync_catalog_index)."""

    from research_foundry.services import builder_service as bsvc

    build_catalog_run(tmp_foundry, include_unknown=False)
    svc.import_run(tmp_foundry, "rf_run_catalog001")
    _write_threshold(tmp_foundry, "client_sensitive")

    source_id = svc._make_item_id("source", "rf_run_catalog001", "src_alpha")

    # Incremental path: create a real on-disk draft via builder_service and
    # add a source link carrying a catalog_item_id.  block_id is optional, so
    # this does not require a block to exist in the draft.
    draft = bsvc.create_draft(tmp_foundry, title="Rebuild-check Draft", sensitivity="public")
    draft_id = draft["report_draft_id"]
    bsvc.add_source_link(
        tmp_foundry,
        draft_id,
        source_card_id="src_alpha",
        run_id="rf_run_catalog001",
        catalog_item_id=source_id,
    )

    item_before = svc.get_item(tmp_foundry, source_id)
    assert item_before is not None
    cd_before = item_before["links"]["citing_drafts"]
    assert any(d["report_draft_id"] == draft_id for d in cd_before)

    # Rebuild drops + repopulates catalog_items and catalog_report_drafts from disk.
    result = svc.rebuild(tmp_foundry)
    assert result["drafts"] == 1
    assert result["draft_errors"] == []

    item_after = svc.get_item(tmp_foundry, source_id)
    assert item_after is not None
    cd_after = item_after["links"]["citing_drafts"]

    # The same draft must appear after rebuild via the reindex_all_drafts path.
    before_ids = {d["report_draft_id"] for d in cd_before}
    after_ids = {d["report_draft_id"] for d in cd_after}
    assert before_ids == after_ids
