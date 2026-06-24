"""Unit tests for the deterministic run export service (runs-frontend P1).

Covers the claim-graph join, derived-status ladder (including the stale
``run.yaml.status`` case), sensitivity filtering, path re-derivation (no stored
absolute path is ever used for I/O), recursive discovery, and error handling.
All tests run against synthetic YAML fixtures — no real run data, no network.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths, RunPaths
from research_foundry.services import export_service as svc
from research_foundry.yamlio import dump_yaml


# --------------------------------------------------------------------------
# synthetic-run builder
# --------------------------------------------------------------------------
def _source_card(
    sid: str,
    *,
    sensitivity: str,
    points: list[dict[str, Any]],
    title: str = "Synthetic Source",
) -> dict[str, Any]:
    return {
        "schema_version": "0.1",
        "type": "source_card",
        "source_card_id": sid,
        "sensitivity": sensitivity,
        "source": {
            "title": title,
            "source_type": "web",
            "locator": {"url": f"https://example.test/{sid}"},
        },
        "trust": {"source_rank": "primary"},
        "usage": {"allowed_for_public_output": False},
        "extracted_points": points,
    }


def build_run(
    paths: FoundryPaths,
    run_id: str = "rf_run_test001",
    *,
    raw_status: str = "planned",
    with_sources: bool = True,
    with_extractions: bool = True,
    with_ledger: bool = True,
    with_report: bool = True,
    with_verification: bool = True,
    verification_passed: bool = True,
    with_bundle: bool = True,
    approved_for_writeback: bool = False,
    with_writebacks: bool = False,
    with_trace: bool = True,
) -> RunPaths:
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()

    dump_yaml(
        {
            "schema_version": "0.1",
            "type": "run",
            "run_id": run_id,
            "intent_id": "intent_test001",
            "status": raw_status,  # deliberately may be stale
            "sensitivity": "personal",
            "created_at": "2026-06-13T22:46:23-04:00",
        },
        rp.run_yaml,
    )

    if with_sources:
        dump_md(
            _source_card(
                "src_pub01",
                sensitivity="public",
                points=[
                    {"evidence_id": "ev_001", "locator": "p1", "summary": "pub one",
                     "quote": "PUBLIC_QUOTE_ALPHA"},
                    {"evidence_id": "ev_002", "locator": "p2", "summary": "pub two",
                     "quote": "PUBLIC_QUOTE_BETA"},
                ],
            ),
            "",
            rp.sources / "src_pub01.md",
        )
        dump_md(
            _source_card(
                "src_sens01",
                sensitivity="work_sensitive",
                points=[
                    {"evidence_id": "ev_001", "locator": "s1", "summary": "secret sum",
                     "quote": "SECRET_WORK_QUOTE"},
                ],
            ),
            "",
            rp.sources / "src_sens01.md",
        )
        dump_md(
            _source_card(
                "src_mixed01",
                sensitivity="public",
                points=[
                    {"evidence_id": "ev_001", "locator": "m1", "summary": "point secret",
                     "quote": "POINT_SECRET_QUOTE", "sensitivity": "work_sensitive"},
                    {"evidence_id": "ev_002", "locator": "m2", "summary": "point public",
                     "quote": "POINT_PUBLIC_QUOTE"},
                ],
            ),
            "",
            rp.sources / "src_mixed01.md",
        )

    if with_extractions:
        dump_yaml({"id": "ext_001", "evidence": []}, rp.extractions / "ext_001.yaml")

    if with_ledger:
        dump_yaml(
            {
                "schema_version": "0.1",
                "report_ref": "reports/report_draft.md",
                "claims": [
                    {"claim_id": "clm_001", "text": "alpha fact", "materiality": "core",
                     "claim_type": "factual", "status": "supported", "confidence": "high",
                     "sources": [{"source_card_id": "src_pub01", "evidence_id": "ev_001",
                                  "relation": "supports", "locator": "p1"}],
                     "inference_basis": {"from_claims": [], "reasoning_summary": None}},
                    {"claim_id": "clm_002", "text": "secret fact", "materiality": "core",
                     "claim_type": "factual", "status": "supported", "confidence": "medium",
                     "sources": [{"source_card_id": "src_sens01", "evidence_id": "ev_001",
                                  "relation": "supports", "locator": "s1"}],
                     "inference_basis": {"from_claims": [], "reasoning_summary": None}},
                    {"claim_id": "clm_inf03", "text": "an inference", "materiality": "core",
                     "claim_type": "inference", "status": "inference", "confidence": "low",
                     "sources": [],
                     "inference_basis": {"from_claims": ["clm_001"],
                                         "reasoning_summary": "derived from alpha"}},
                    {"claim_id": "clm_004", "text": "mixed-point fact", "materiality": "background",
                     "claim_type": "factual", "status": "supported", "confidence": "medium",
                     "sources": [
                         {"source_card_id": "src_mixed01", "evidence_id": "ev_001",
                          "relation": "supports", "locator": "m1"},
                         {"source_card_id": "src_mixed01", "evidence_id": "ev_002",
                          "relation": "supports", "locator": "m2"}],
                     "inference_basis": {"from_claims": [], "reasoning_summary": None}},
                    {"claim_id": "clm_005", "text": "dangling fact", "materiality": "background",
                     "claim_type": "factual", "status": "unsupported", "confidence": "low",
                     "sources": [{"source_card_id": "src_missing", "evidence_id": "ev_999",
                                  "relation": "supports", "locator": "x"}],
                     "inference_basis": {"from_claims": [], "reasoning_summary": None}},
                ],
            },
            rp.claim_ledger,
        )

    if with_report:
        rp.report_draft.write_text(
            "# Report\n\nAlpha. [claim:clm_001] An inference. [claim:clm_inf03]\n",
            encoding="utf-8",
        )

    if with_verification:
        dump_yaml(
            {
                "run_id": run_id,
                "passed": verification_passed,
                "exit_code": 0 if verification_passed else 2,
                # stored absolute paths — must never be used for I/O:
                "report_path": "/abs/POISON/report_draft.md",
                "claim_ledger_path": "/abs/POISON/claim_ledger.yaml",
                "checks": [
                    {"id": "all_claim_ids_exist", "severity": "error", "status": "pass",
                     "detail": "ok", "locations": []},
                ],
            },
            rp.verification,
        )

    if with_bundle:
        dump_yaml(
            {
                "schema_version": "0.1",
                "run_id": run_id,
                "status": "verified",
                "counts": {"claims_total": 5, "claims_supported": 3},
                "governance": {"sensitivity": "personal",
                               "approved_for_writeback": approved_for_writeback},
            },
            rp.evidence_bundle,
        )

    if with_writebacks:
        rp.ccdash_event.write_text("event: writeback\n", encoding="utf-8")

    if with_trace:
        rp.run_trace.write_text(
            '{"stage": "plan", "ts": "2026-06-13T22:46:23-04:00"}\n'
            '{"stage": "verify", "ts": "2026-06-13T23:46:23-04:00"}\n',
            encoding="utf-8",
        )
    return rp


# --------------------------------------------------------------------------
# claim-graph join
# --------------------------------------------------------------------------
def test_claim_graph_join_resolves_source_and_quote(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry)
    data = svc.export_run(tmp_foundry, "rf_run_test001",
                          sensitivity_threshold="work_sensitive")
    by_id = {c["claim_id"]: c for c in data["claims"]}

    clm1 = by_id["clm_001"]
    src = clm1["sources"][0]
    assert src["source_card_id"] == "src_pub01"
    assert src["evidence_id"] == "ev_001"
    assert src["quote"] == "PUBLIC_QUOTE_ALPHA"
    assert src["title"] == "Synthetic Source"
    assert src["url"] == "https://example.test/src_pub01"
    assert src["evidence_locator"] == "p1"
    assert src["resolved"] is True and src["dangling"] is False


def test_inference_basis_chain_preserved(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry)
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    inf = next(c for c in data["claims"] if c["claim_id"] == "clm_inf03")
    assert inf["sources"] == []
    assert inf["inference_basis"]["from_claims"] == ["clm_001"]
    assert inf["inference_basis"]["reasoning_summary"] == "derived from alpha"


def test_dangling_source_is_flagged_not_dropped(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry)
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    dangling = next(c for c in data["claims"] if c["claim_id"] == "clm_005")
    src = dangling["sources"][0]
    assert src["resolved"] is False and src["dangling"] is True
    assert src["quote"] is None


def test_claim_counts_and_top_level_shape(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry)
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    assert data["schema_version"] == svc.EXPORT_SCHEMA_VERSION == "1.3"
    assert data["run_id"] == "rf_run_test001"
    assert data["claim_counts"]["total"] == 5
    assert data["claim_counts"]["supported"] == 3
    assert data["verification"]["passed"] is True
    assert len(data["verification"]["checks"]) == 1
    assert len(data["timeline"]) == 2


# --------------------------------------------------------------------------
# derived-status ladder (OQ-2) — computed from artifacts, not run.yaml.status
# --------------------------------------------------------------------------
def test_status_stale_planned_resolves_to_verified(tmp_foundry: FoundryPaths) -> None:
    # run.yaml says planned, but verification passed and no writebacks/approval.
    build_run(tmp_foundry, raw_status="planned", verification_passed=True,
              approved_for_writeback=False, with_writebacks=False)
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    assert data["status_raw"] == "planned"
    assert data["status_derived"] == "verified"


def test_status_published_when_writebacks_present(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, with_writebacks=True)
    assert svc.export_run(tmp_foundry, "rf_run_test001")["status_derived"] == "published"


def test_status_published_when_approved_for_writeback(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, approved_for_writeback=True, with_writebacks=False)
    assert svc.export_run(tmp_foundry, "rf_run_test001")["status_derived"] == "published"


@pytest.mark.parametrize(
    "flags,expected",
    [
        (dict(with_sources=False, with_extractions=False, with_ledger=False,
              with_report=False, with_verification=False, with_bundle=False,
              with_trace=False), "planned"),
        (dict(with_extractions=False, with_ledger=False, with_report=False,
              with_verification=False, with_bundle=False), "sources_ingested"),
        (dict(with_ledger=False, with_report=False, with_verification=False,
              with_bundle=False), "extracted"),
        (dict(with_report=False, with_verification=False, with_bundle=False),
         "claim_mapped"),
        (dict(with_verification=False, with_bundle=False), "synthesized"),
    ],
)
def test_status_ladder_partial(tmp_foundry: FoundryPaths, flags, expected) -> None:
    rp = build_run(tmp_foundry, **flags)
    assert svc.derive_status(rp, run_id="rf_run_test001") == expected


# --------------------------------------------------------------------------
# sensitivity filter (card-level and point-level)
# --------------------------------------------------------------------------
def test_default_public_threshold_redacts_personal_and_above(
    tmp_foundry: FoundryPaths,
) -> None:
    build_run(tmp_foundry)  # default threshold from foundry.yaml = public
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    blob = _json_blob(data)
    # public card content survives
    assert "PUBLIC_QUOTE_ALPHA" in blob
    # work_sensitive card content is gone
    assert "SECRET_WORK_QUOTE" not in blob


def test_point_level_sensitivity_redacts_only_that_point(
    tmp_foundry: FoundryPaths,
) -> None:
    build_run(tmp_foundry, raw_status="planned")
    # threshold personal: card src_mixed01 is public, but ev_001 point is
    # work_sensitive -> only that point's quote is redacted.
    data = svc.export_run(tmp_foundry, "rf_run_test001",
                          sensitivity_threshold="personal")
    clm4 = next(c for c in data["claims"] if c["claim_id"] == "clm_004")
    points = {s["evidence_id"]: s for s in clm4["sources"]}
    assert points["ev_001"]["redacted"] is True
    assert points["ev_001"]["quote"] == svc.REDACTION_MARKER
    assert points["ev_002"]["redacted"] is False
    assert points["ev_002"]["quote"] == "POINT_PUBLIC_QUOTE"


def test_threshold_allows_work_sensitive_when_raised(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry)
    data = svc.export_run(tmp_foundry, "rf_run_test001",
                          sensitivity_threshold="work_sensitive")
    assert "SECRET_WORK_QUOTE" in _json_blob(data)


def test_absent_sensitivity_treated_as_public(tmp_foundry: FoundryPaths) -> None:
    rp = tmp_foundry.run_paths("rf_run_test002")
    rp.ensure_scaffold()
    dump_yaml({"run_id": "rf_run_test002", "status": "planned"}, rp.run_yaml)
    dump_md(
        {
            "source_card_id": "src_nosens",
            "source": {"title": "No Sens", "locator": {"url": "u"}},
            # no card-level sensitivity at all
            "extracted_points": [
                {"evidence_id": "ev_001", "quote": "NOSENS_QUOTE", "locator": "l"}
            ],
        },
        "",
        rp.sources / "src_nosens.md",
    )
    dump_yaml(
        {"claims": [{"claim_id": "clm_001", "status": "supported",
                     "sources": [{"source_card_id": "src_nosens",
                                  "evidence_id": "ev_001"}]}]},
        rp.claim_ledger,
    )
    data = svc.export_run(tmp_foundry, "rf_run_test002")  # default public
    assert "NOSENS_QUOTE" in _json_blob(data)


# --------------------------------------------------------------------------
# threshold resolution (OQ-3)
# --------------------------------------------------------------------------
def test_threshold_override_beats_config(tmp_foundry: FoundryPaths) -> None:
    assert svc.resolve_threshold(tmp_foundry, "client_sensitive") == "client_sensitive"


def test_threshold_from_foundry_yaml(tmp_foundry: FoundryPaths) -> None:
    (tmp_foundry.root / "foundry.yaml").write_text(
        "foundry:\n  owner: T\n  viewer:\n    sensitivity_threshold: work_sensitive\n",
        encoding="utf-8",
    )
    assert svc.resolve_threshold(tmp_foundry) == "work_sensitive"


def test_threshold_defaults_public_when_absent(tmp_foundry: FoundryPaths) -> None:
    (tmp_foundry.root / "foundry.yaml").write_text(
        "foundry:\n  owner: T\n", encoding="utf-8"
    )
    assert svc.resolve_threshold(tmp_foundry) == svc.DEFAULT_THRESHOLD


# --------------------------------------------------------------------------
# path derivation — NO stored absolute path is ever used for file I/O
# --------------------------------------------------------------------------
def test_no_stored_absolute_path_used_for_io(
    tmp_foundry: FoundryPaths, monkeypatch: pytest.MonkeyPatch
) -> None:
    rp = build_run(tmp_foundry)

    # Plant a decoy file OUTSIDE the workspace, and point the stored path
    # fields (run_index.yaml + verification.yaml) at it. If the export ever
    # trusted those fields, the decoy content would surface / be read.
    decoy = tmp_foundry.root.parent / "POISON_decoy.md"
    decoy.write_text("POISON_CONTENT_MUST_NOT_APPEAR", encoding="utf-8")
    dump_yaml(
        {"items": [{"id": "rf_run_test001", "run_dir": str(decoy.parent),
                    "report_path": str(decoy)}]},
        tmp_foundry.registries / "run_index.yaml",
    )
    # overwrite verification stored paths with the decoy too
    from research_foundry.yamlio import load_yaml
    vdata = load_yaml(rp.verification)
    vdata["report_path"] = str(decoy)
    vdata["claim_ledger_path"] = str(decoy)
    dump_yaml(vdata, rp.verification)

    reads: list[str] = []
    original = Path.read_text

    def _spy(self: Path, *args: Any, **kwargs: Any) -> str:
        reads.append(str(self))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _spy)

    data = svc.export_run(tmp_foundry, "rf_run_test001")
    blob = _json_blob(data)

    # 1. decoy stored path was never opened for reading
    assert str(decoy) not in reads
    # 2. decoy content never leaked into the export
    assert "POISON_CONTENT_MUST_NOT_APPEAR" not in blob
    # 3+. at least 5 file reads happened, all within the workspace root
    assert len(reads) >= 5
    root = str(tmp_foundry.root)
    assert all(r.startswith(root) for r in reads)
    # the run's own artifacts were the source of truth
    assert str(rp.claim_ledger) in reads
    assert str(rp.run_yaml) in reads


# --------------------------------------------------------------------------
# discovery, listing, file output, errors
# --------------------------------------------------------------------------
def test_recursive_discovery_finds_nested_runs(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_top")
    # nested anomaly: runs/runs/<id>/run.yaml (depth 2)
    nested = RunPaths(run=tmp_foundry.runs / "runs" / "rf_run_nested")
    nested.ensure_scaffold()
    dump_yaml({"run_id": "rf_run_nested", "status": "planned"}, nested.run_yaml)

    found = {p.parent.name for p in svc.discover_run_yamls(tmp_foundry.runs)}
    assert "rf_run_top" in found
    assert "rf_run_nested" in found


def test_list_runs_uses_derived_status(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_top", with_writebacks=True)
    rows = svc.list_runs(tmp_foundry)
    row = next(r for r in rows if r["run_id"] == "rf_run_top")
    assert row["status_raw"] == "planned"
    assert row["status_derived"] == "published"
    assert row["verification_passed"] is True


def test_export_to_file_writes_run_json(tmp_foundry: FoundryPaths) -> None:
    rp = build_run(tmp_foundry)
    out = svc.export_to_file(tmp_foundry, "rf_run_test001")
    assert out == rp.run / "run.json"
    assert out.exists()
    import json
    assert json.loads(out.read_text(encoding="utf-8"))["run_id"] == "rf_run_test001"


def test_export_all_writes_each_run(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_a")
    build_run(tmp_foundry, "rf_run_b")
    written = svc.export_all(tmp_foundry)
    assert len(written) == 2
    assert all(p.name == "run.json" and p.exists() for p in written)


def test_resolve_run_paths_via_discovery(tmp_foundry: FoundryPaths) -> None:
    nested = RunPaths(run=tmp_foundry.runs / "runs" / "rf_run_nested")
    nested.ensure_scaffold()
    dump_yaml({"run_id": "rf_run_nested", "status": "planned"}, nested.run_yaml)
    resolved = svc.resolve_run_paths(tmp_foundry, "rf_run_nested")
    assert resolved.run == nested.run


def test_unknown_run_raises_export_error(tmp_foundry: FoundryPaths) -> None:
    with pytest.raises(svc.ExportError) as exc:
        svc.export_run(tmp_foundry, "rf_run_does_not_exist")
    assert exc.value.run_id == "rf_run_does_not_exist"


def test_malformed_ledger_raises_with_artifact_path(tmp_foundry: FoundryPaths) -> None:
    rp = build_run(tmp_foundry)
    rp.claim_ledger.write_text("claims: [unterminated\n", encoding="utf-8")
    with pytest.raises(svc.ExportError) as exc:
        svc.export_run(tmp_foundry, "rf_run_test001")
    assert exc.value.artifact_path is not None
    assert "claim_ledger.yaml" in exc.value.artifact_path
    assert exc.value.as_payload()["run_id"] == "rf_run_test001"


def test_claim_tags_in_report_helper(tmp_foundry: FoundryPaths) -> None:
    rp = build_run(tmp_foundry)
    tags = svc.claim_tags_in_report(rp.report_draft)
    assert set(tags) == {"clm_001", "clm_inf03"}


# --------------------------------------------------------------------------
# report_draft field
# --------------------------------------------------------------------------
def test_report_draft_present_when_report_exists(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry)
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    assert data["report_draft"] is not None
    assert len(data["report_draft"]) > 0


def test_report_draft_contains_claim_tags(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry)
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    assert "[claim:clm_" in data["report_draft"]


def test_report_draft_null_when_no_report(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, with_report=False)
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    assert data["report_draft"] is None


def test_report_draft_falls_back_to_final(tmp_foundry: FoundryPaths) -> None:
    """report_final.md should be used when report_draft.md is absent."""
    rp = build_run(tmp_foundry, with_report=False)
    final_content = "# Final Report\n\nFinal text. [claim:clm_001]\n"
    rp.report_final.write_text(final_content, encoding="utf-8")
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    assert data["report_draft"] == final_content


def test_schema_version_is_1_3(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry)
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    assert data["schema_version"] == "1.3"


# --------------------------------------------------------------------------
# metadata enrichment fields (schema 1.2)
# --------------------------------------------------------------------------

def _build_run_with_metadata(
    paths: FoundryPaths,
    run_id: str = "rf_run_meta001",
    *,
    linked_projects: list[str] | None = None,
    category: str | None = None,
    tags: list[str] | None = None,
    backlog_idea_ref: str | None = None,
    backlog_idea_id: str | None = None,
) -> RunPaths:
    """Build a minimal run with optional metadata enrichment fields."""
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()

    run_yaml: dict[str, Any] = {
        "schema_version": "0.1",
        "type": "run",
        "run_id": run_id,
        "status": "planned",
    }
    if linked_projects is not None:
        run_yaml["linked_projects"] = linked_projects
    if category is not None:
        run_yaml["category"] = category
    if tags is not None:
        run_yaml["tags"] = tags
    if backlog_idea_ref is not None:
        run_yaml["backlog_idea_ref"] = backlog_idea_ref
    if backlog_idea_id is not None:
        run_yaml["backlog_idea_id"] = backlog_idea_id

    dump_yaml(run_yaml, rp.run_yaml)
    return rp


def test_metadata_fields_emitted_when_present(tmp_foundry: FoundryPaths) -> None:
    """EXP-001: All 5 new fields are present in export output when set in run.yaml."""
    _build_run_with_metadata(
        tmp_foundry,
        linked_projects=["Research Foundry", "KnitWit"],
        category="AI Engineering",
        tags=["agents", "python"],
        backlog_idea_ref="RIB-042",
        backlog_idea_id="idea_agent-framework-eval",
    )
    data = svc.export_run(tmp_foundry, "rf_run_meta001")

    assert data["linked_projects"] == ["Research Foundry", "KnitWit"]
    assert data["category"] == "AI Engineering"
    assert data["tags"] == ["agents", "python"]
    assert data["backlog_idea_ref"] == "RIB-042"
    assert data["backlog_idea_id"] == "idea_agent-framework-eval"


def test_metadata_fields_null_when_absent(tmp_foundry: FoundryPaths) -> None:
    """EXP-001: All 5 new fields are present as null (not key-omitted) when absent."""
    _build_run_with_metadata(tmp_foundry)  # no metadata fields set
    data = svc.export_run(tmp_foundry, "rf_run_meta001")

    # Keys must be present (not omitted), with null values
    assert "linked_projects" in data and data["linked_projects"] is None
    assert "category" in data and data["category"] is None
    assert "tags" in data and data["tags"] is None
    assert "backlog_idea_ref" in data and data["backlog_idea_ref"] is None
    assert "backlog_idea_id" in data and data["backlog_idea_id"] is None


def test_metadata_fields_null_on_pre_migration_run(tmp_foundry: FoundryPaths) -> None:
    """EXP-001: Pre-migration runs (no metadata fields in run.yaml) emit null for all 5."""
    build_run(tmp_foundry)  # uses the standard builder without metadata fields
    data = svc.export_run(tmp_foundry, "rf_run_test001")

    assert data["linked_projects"] is None
    assert data["category"] is None
    assert data["tags"] is None
    assert data["backlog_idea_ref"] is None
    assert data["backlog_idea_id"] is None


def test_schema_version_bumped_to_1_3(tmp_foundry: FoundryPaths) -> None:
    """EXP-003: schema_version in export output is '1.3'."""
    assert svc.EXPORT_SCHEMA_VERSION == "1.3"
    _build_run_with_metadata(tmp_foundry)
    data = svc.export_run(tmp_foundry, "rf_run_meta001")
    assert data["schema_version"] == "1.3"


def test_existing_fields_unaffected_by_metadata_addition(tmp_foundry: FoundryPaths) -> None:
    """EXP-001: Adding metadata fields must not alter existing export fields."""
    _build_run_with_metadata(
        tmp_foundry,
        linked_projects=["My Project"],
        category="Backend",
        tags=["python"],
    )
    data = svc.export_run(tmp_foundry, "rf_run_meta001")

    # Core fields still present and correct
    assert data["run_id"] == "rf_run_meta001"
    assert data["schema_version"] == "1.3"
    assert data["status_derived"] == "planned"
    assert "claims" in data
    assert "claim_counts" in data


# --------------------------------------------------------------------------
# ENR-001: cost_usd + model_profiles from run.yaml.profile
# --------------------------------------------------------------------------

def _build_run_with_profile(
    paths: FoundryPaths,
    run_id: str = "rf_run_profile001",
    *,
    profile: dict[str, Any] | None = None,
) -> RunPaths:
    """Build a minimal run with an optional profile block."""
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    run_yaml: dict[str, Any] = {
        "schema_version": "0.1",
        "type": "run",
        "run_id": run_id,
        "status": "planned",
    }
    if profile is not None:
        run_yaml["profile"] = profile
    dump_yaml(run_yaml, rp.run_yaml)
    return rp


def test_cost_usd_and_model_profiles_present_when_profile_set(
    tmp_foundry: FoundryPaths,
) -> None:
    """ENR-001: cost_usd and model_profiles threaded from run.yaml.profile."""
    _build_run_with_profile(
        tmp_foundry,
        profile={
            "max_cost_usd": 7.0,
            "max_runtime_minutes": 60,
            "freshness_days": 180,
            "extraction_model_profile": "rf_extract_cheap",
            "synthesis_model_profile": "rf_synthesize_deep",
            "verification_model_profile": "rf_verify_balanced",
        },
    )
    data = svc.export_run(tmp_foundry, "rf_run_profile001")

    assert data["cost_usd"] == 7.0
    mp = data["model_profiles"]
    assert mp is not None
    assert mp["max_cost_usd"] == 7.0
    assert mp["max_runtime_minutes"] == 60
    assert mp["freshness_days"] == 180
    assert mp["extraction_model_profile"] == "rf_extract_cheap"
    assert mp["synthesis_model_profile"] == "rf_synthesize_deep"
    assert mp["verification_model_profile"] == "rf_verify_balanced"


def test_cost_usd_and_model_profiles_null_when_no_profile(
    tmp_foundry: FoundryPaths,
) -> None:
    """ENR-001: cost_usd and model_profiles are null for runs without profile."""
    _build_run_with_profile(tmp_foundry)  # no profile block
    data = svc.export_run(tmp_foundry, "rf_run_profile001")

    assert "cost_usd" in data and data["cost_usd"] is None
    assert "model_profiles" in data and data["model_profiles"] is None


# --------------------------------------------------------------------------
# ENR-002: source_count_by_type aggregated from source cards
# --------------------------------------------------------------------------

def test_source_count_by_type_aggregated_correctly(tmp_foundry: FoundryPaths) -> None:
    """ENR-002: source_count_by_type aggregates source_type from source cards."""
    build_run(tmp_foundry, "rf_run_srccount")
    # The standard build_run uses source_type "web" for the source cards;
    # check that source_count_by_type is derived correctly.
    data = svc.export_run(tmp_foundry, "rf_run_srccount")
    sct = data["source_count_by_type"]
    assert sct is not None
    assert isinstance(sct, dict)
    # All 3 source cards in build_run have source_type "web"
    assert sct.get("web") == 3


def test_source_count_by_type_null_when_no_sources(tmp_foundry: FoundryPaths) -> None:
    """ENR-002: source_count_by_type is null for runs with no source cards."""
    build_run(tmp_foundry, "rf_run_nosrc", with_sources=False)
    data = svc.export_run(tmp_foundry, "rf_run_nosrc")
    assert "source_count_by_type" in data and data["source_count_by_type"] is None


# --------------------------------------------------------------------------
# ENR-003: context block (routing_decision + swarm_plan)
# --------------------------------------------------------------------------

def _build_run_with_routing(
    paths: FoundryPaths,
    run_id: str = "rf_run_ctx001",
    *,
    with_routing: bool = True,
    with_swarm: bool = True,
) -> RunPaths:
    """Build a minimal run with optional routing_decision.yaml and swarm_plan.yaml."""
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {"schema_version": "0.1", "run_id": run_id, "status": "planned"},
        rp.run_yaml,
    )
    if with_routing:
        dump_yaml(
            {
                "schema_version": "0.1",
                "type": "routing_decision",
                "id": f"route_{run_id}",
                "selected_abstraction_level": "L4",
                "rationale": "Test rationale for routing",
                "human_required": False,
            },
            rp.routing_decision,
        )
    if with_swarm:
        dump_yaml(
            {
                "schema_version": "0.1",
                "type": "swarm_plan",
                "id": f"swarm_{run_id}",
                "agents": [
                    {"role": "source_scout", "posture": "researcher"},
                    {"role": "synthesis_lead", "posture": "synthesizer"},
                ],
                "required_outputs": ["source_cards", "report_draft.md"],
            },
            rp.swarm_plan,
        )
    return rp


def test_context_routing_and_swarm_present(tmp_foundry: FoundryPaths) -> None:
    """ENR-003: context.routing_decision and context.swarm_plan populated when files exist."""
    _build_run_with_routing(tmp_foundry)
    data = svc.export_run(tmp_foundry, "rf_run_ctx001")

    ctx = data.get("context")
    assert ctx is not None

    rd = ctx.get("routing_decision")
    assert rd is not None
    assert rd.get("rationale") == "Test rationale for routing"

    sp = ctx.get("swarm_plan")
    assert sp is not None
    agents = sp.get("agents")
    assert agents is not None
    assert "source_scout" in agents
    assert "synthesis_lead" in agents


def test_context_null_when_no_routing_or_swarm(tmp_foundry: FoundryPaths) -> None:
    """ENR-003: context is null for runs without routing_decision.yaml or swarm_plan.yaml."""
    _build_run_with_routing(tmp_foundry, "rf_run_noctx", with_routing=False, with_swarm=False)
    data = svc.export_run(tmp_foundry, "rf_run_noctx")
    assert "context" in data and data["context"] is None


def test_context_partial_routing_only(tmp_foundry: FoundryPaths) -> None:
    """ENR-003: context populated with routing only when swarm_plan absent."""
    _build_run_with_routing(tmp_foundry, "rf_run_ronly", with_routing=True, with_swarm=False)
    data = svc.export_run(tmp_foundry, "rf_run_ronly")
    ctx = data.get("context")
    assert ctx is not None
    assert ctx.get("routing_decision") is not None
    assert ctx.get("swarm_plan") is None


def test_context_partial_swarm_only(tmp_foundry: FoundryPaths) -> None:
    """ENR-003: context populated with swarm_plan only when routing_decision absent."""
    _build_run_with_routing(tmp_foundry, "rf_run_sonly", with_routing=False, with_swarm=True)
    data = svc.export_run(tmp_foundry, "rf_run_sonly")
    ctx = data.get("context")
    assert ctx is not None
    assert ctx.get("routing_decision") is None
    assert ctx.get("swarm_plan") is not None


# --------------------------------------------------------------------------
# ENR schema_version and full enrichment round-trip
# --------------------------------------------------------------------------

def test_enrichment_extra_fields_all_present_on_full_run(tmp_foundry: FoundryPaths) -> None:
    """ENR-001/002/003: All enrichment-extra fields present on a fully-enriched run."""
    # Build a run with profile, routing, swarm, and sources
    rp = build_run(tmp_foundry, "rf_run_enr_full")
    # Add profile to run.yaml
    from research_foundry.yamlio import load_yaml
    run_data = load_yaml(rp.run_yaml)
    run_data["profile"] = {
        "max_cost_usd": 5.0,
        "max_runtime_minutes": 30,
        "freshness_days": 90,
        "extraction_model_profile": "rf_extract_cheap",
        "synthesis_model_profile": "rf_synthesize_std",
        "verification_model_profile": "rf_verify_std",
    }
    dump_yaml(run_data, rp.run_yaml)
    # Add routing_decision + swarm_plan
    dump_yaml(
        {
            "schema_version": "0.1", "type": "routing_decision",
            "id": "route_enr_full", "selected_abstraction_level": "L3",
            "rationale": "Standard research route",
        },
        rp.routing_decision,
    )
    dump_yaml(
        {
            "schema_version": "0.1", "type": "swarm_plan",
            "id": "swarm_enr_full",
            "agents": [{"role": "paper_analyst", "posture": "researcher"}],
            "required_outputs": ["source_cards"],
        },
        rp.swarm_plan,
    )

    data = svc.export_run(tmp_foundry, "rf_run_enr_full")

    # ENR-001
    assert data["cost_usd"] == 5.0
    assert data["model_profiles"] is not None
    assert data["model_profiles"]["extraction_model_profile"] == "rf_extract_cheap"
    # ENR-002
    assert data["source_count_by_type"] is not None
    assert isinstance(data["source_count_by_type"], dict)
    # ENR-003
    assert data["context"] is not None
    assert data["context"]["routing_decision"] is not None
    assert data["context"]["swarm_plan"] is not None
    # schema_version is now 1.3
    assert data["schema_version"] == "1.3"


def test_enrichment_extra_fields_null_on_pre_enrichment_run(
    tmp_foundry: FoundryPaths,
) -> None:
    """ENR-001/002/003: All enrichment-extra fields null on pre-enrichment run (no sources/profile/routing)."""
    rp = tmp_foundry.run_paths("rf_run_bare")
    rp.ensure_scaffold()
    dump_yaml({"run_id": "rf_run_bare", "status": "planned"}, rp.run_yaml)

    data = svc.export_run(tmp_foundry, "rf_run_bare")

    assert data["cost_usd"] is None
    assert data["model_profiles"] is None
    assert data["source_count_by_type"] is None
    assert data["context"] is None


# --------------------------------------------------------------------------
# Fix 1: title field present and non-null in export_run()
# --------------------------------------------------------------------------

def test_title_present_and_non_null(tmp_foundry: FoundryPaths) -> None:
    """BLOCKER FIX: export_run() must include a non-null 'title' key."""
    build_run(tmp_foundry)
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    assert "title" in data
    assert data["title"] is not None
    assert isinstance(data["title"], str)
    assert len(data["title"]) > 0


def test_title_derived_from_slug_when_no_report_frontmatter(
    tmp_foundry: FoundryPaths,
) -> None:
    """Title falls back to humanized slug when report draft has no frontmatter title."""
    build_run(tmp_foundry)
    # The standard report draft has no YAML frontmatter title.
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    # Slug "rf_run_test001" → strips "rf_run_" prefix → "test001" → title-cased → "Test001"
    assert data["title"] == "Test001"


def test_title_extracted_from_report_frontmatter(tmp_foundry: FoundryPaths) -> None:
    """Title comes from YAML frontmatter title: field when present."""
    rp = build_run(tmp_foundry, with_report=False)
    rp.report_draft.write_text(
        "---\ntitle: My Research Report\nauthor: Test\n---\n\nBody text.\n",
        encoding="utf-8",
    )
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    assert data["title"] == "My Research Report"


def test_title_slug_helpers_correct() -> None:
    """Unit test the slug-humanization helpers directly."""
    # "rf_run_test001" → strips prefix → "test001" → no word boundary on digits → "Test001"
    assert svc._title_from_slug("rf_run_test001") == "Test001"
    # multi-word slugs split on underscores → each word capitalized
    assert svc._title_from_slug("intent_research_ai_agents") == "Ai Agents"
    assert svc._title_from_slug("intent_scaling_law") == "Scaling Law"
    assert svc._title_from_slug(None) is None
    assert svc._extract_title_from_report_draft(None) is None
    assert svc._extract_title_from_report_draft("no frontmatter") is None
    assert (
        svc._extract_title_from_report_draft(
            "---\ntitle: Hello World\n---\n\nBody.\n"
        )
        == "Hello World"
    )


# --------------------------------------------------------------------------
# Fix 2: list_runs() includes linked_projects, category, tags
# --------------------------------------------------------------------------

def test_list_runs_includes_metadata_fields(tmp_foundry: FoundryPaths) -> None:
    """list_runs() summaries must include linked_projects, category, tags."""
    rp = tmp_foundry.run_paths("rf_run_listmeta")
    rp.ensure_scaffold()
    from research_foundry.yamlio import dump_yaml as _dump
    _dump(
        {
            "schema_version": "0.1",
            "type": "run",
            "run_id": "rf_run_listmeta",
            "status": "planned",
            "linked_projects": ["Proj A", "Proj B"],
            "category": "Engineering",
            "tags": ["python", "testing"],
        },
        rp.run_yaml,
    )
    rows = svc.list_runs(tmp_foundry)
    row = next(r for r in rows if r["run_id"] == "rf_run_listmeta")
    assert row["linked_projects"] == ["Proj A", "Proj B"]
    assert row["category"] == "Engineering"
    assert row["tags"] == ["python", "testing"]


def test_list_runs_metadata_fields_null_when_absent(tmp_foundry: FoundryPaths) -> None:
    """list_runs() emits null (not key-omitted) for metadata fields on pre-migration runs."""
    build_run(tmp_foundry, "rf_run_listbase")
    rows = svc.list_runs(tmp_foundry)
    row = next(r for r in rows if r["run_id"] == "rf_run_listbase")
    assert "linked_projects" in row and row["linked_projects"] is None
    assert "category" in row and row["category"] is None
    assert "tags" in row and row["tags"] is None


# --------------------------------------------------------------------------
# Fix 3: ENR-004 writebacks field in export_run()
# --------------------------------------------------------------------------

def test_writebacks_null_when_no_writeback_files(tmp_foundry: FoundryPaths) -> None:
    """ENR-004: writebacks is null when no writeback files exist."""
    build_run(tmp_foundry, with_writebacks=False)
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    assert "writebacks" in data
    assert data["writebacks"] is None


def test_writebacks_emitted_when_present(tmp_foundry: FoundryPaths) -> None:
    """ENR-004: writebacks object emitted when writeback files are present (RFRunWritebacksSummary shape)."""
    build_run(tmp_foundry, with_writebacks=True)
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    assert "writebacks" in data
    wb = data["writebacks"]
    assert wb is not None
    # Must be an object (RFRunWritebacksSummary), not a bare list.
    assert isinstance(wb, dict), "writebacks must be an object, not a list"
    # Must have 'targets' list (what FE reads as writebacks.targets?.length)
    assert "targets" in wb
    targets_list = wb["targets"]
    assert isinstance(targets_list, list)
    assert len(targets_list) >= 1
    # Must have approved_for_writeback field (bool or null)
    assert "approved_for_writeback" in wb
    # The standard build_run with_writebacks=True writes ccdash_event.yaml
    target_names = {entry["target"] for entry in targets_list}
    assert "ccdash" in target_names
    for entry in targets_list:
        assert "target" in entry
        assert "status" in entry


def test_writebacks_url_extracted_from_yaml(tmp_foundry: FoundryPaths) -> None:
    """ENR-004: url field extracted from YAML writeback when present."""
    rp = build_run(tmp_foundry, "rf_run_wburl", with_writebacks=False)
    from research_foundry.yamlio import dump_yaml as _dump
    _dump({"url": "https://wiki.example.com/page/42", "status": "synced"},
          rp.intenttree_update)
    data = svc.export_run(tmp_foundry, "rf_run_wburl")
    wb = data["writebacks"]
    assert wb is not None
    assert isinstance(wb, dict), "writebacks must be an object (RFRunWritebacksSummary)"
    assert "targets" in wb
    itt_entry = next((e for e in wb["targets"] if e["target"] == "intenttree"), None)
    assert itt_entry is not None
    assert itt_entry.get("url") == "https://wiki.example.com/page/42"


# --------------------------------------------------------------------------
# Fix 4: _context_summary allowlist — no unanticipated keys leak
# --------------------------------------------------------------------------

def test_context_summary_allowlist_blocks_unknown_keys(tmp_foundry: FoundryPaths) -> None:
    """ENR-004/security: _context_summary must not forward unknown routing keys."""
    rp = tmp_foundry.run_paths("rf_run_ctx_safe")
    rp.ensure_scaffold()
    from research_foundry.yamlio import dump_yaml as _dump
    _dump({"run_id": "rf_run_ctx_safe", "status": "planned"}, rp.run_yaml)
    # Write routing_decision with both allowlisted and non-allowlisted keys
    _dump(
        {
            "schema_version": "0.1",
            "type": "routing_decision",
            "id": "route_safe",
            "selected_abstraction_level": "L3",
            "rationale": "safe rationale",
            "human_required": False,
            "CONFIDENTIAL_FIELD": "must_not_appear",
            "internal_note": "also_must_not_appear",
        },
        rp.routing_decision,
    )
    _dump(
        {
            "schema_version": "0.1",
            "type": "swarm_plan",
            "id": "swarm_safe",
            "agents": [{"role": "scout"}],
            "required_outputs": ["report_draft.md"],
            "SECRET_KEY": "leaked_secret",
        },
        rp.swarm_plan,
    )
    data = svc.export_run(tmp_foundry, "rf_run_ctx_safe")
    import json
    blob = json.dumps(data)
    assert "CONFIDENTIAL_FIELD" not in blob
    assert "must_not_appear" not in blob
    assert "internal_note" not in blob
    assert "also_must_not_appear" not in blob
    assert "SECRET_KEY" not in blob
    assert "leaked_secret" not in blob
    # Allowlisted fields DO appear
    ctx = data.get("context")
    assert ctx is not None
    assert ctx["routing_decision"]["rationale"] == "safe rationale"
    assert ctx["routing_decision"]["human_required"] is False


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _json_blob(data: dict[str, Any]) -> str:
    import json
    return json.dumps(data, ensure_ascii=False)


# --------------------------------------------------------------------------
# title derivation helpers (nav-titles-lineage-fixes contract)
# --------------------------------------------------------------------------

class TestTitleFromSlug:
    """Unit tests for _title_from_slug (Python equivalent of FE titleFromSlug)."""

    def test_strips_rf_run_prefix_and_datestamp(self) -> None:
        result = svc._title_from_slug("rf_run_20260613_my_cool_research")
        assert result == "My Cool Research"

    def test_strips_rf_run_prefix_no_datestamp(self) -> None:
        result = svc._title_from_slug("rf_run_roots_wave")
        assert result == "Roots Wave"

    def test_strips_intent_prefix(self) -> None:
        result = svc._title_from_slug("intent_knitwit_crochet")
        assert result == "Knitwit Crochet"

    def test_strips_intent_research_prefix(self) -> None:
        result = svc._title_from_slug("intent_research_homelab_security")
        assert result == "Homelab Security"

    def test_returns_none_for_none_input(self) -> None:
        assert svc._title_from_slug(None) is None

    def test_returns_none_for_empty_string(self) -> None:
        assert svc._title_from_slug("") is None

    def test_title_cases_result(self) -> None:
        result = svc._title_from_slug("rf_run_abc_def")
        assert result is not None
        assert result == result.title() or result[0].isupper()

    def test_hyphen_separator_is_humanized(self) -> None:
        result = svc._title_from_slug("rf_run_20260601_foo-bar-baz")
        assert result == "Foo Bar Baz"


class TestExtractTitleFromReportDraft:
    """Unit tests for _extract_title_from_report_draft."""

    def test_extracts_title_from_yaml_frontmatter(self) -> None:
        report = "---\ntitle: My Research Report\ndate: 2026-06-13\n---\n# Heading\n\nBody text.\n"
        result = svc._extract_title_from_report_draft(report)
        assert result == "My Research Report"

    def test_extracts_title_with_double_quotes(self) -> None:
        report = '---\ntitle: "Quoted Title"\n---\n\nBody.\n'
        result = svc._extract_title_from_report_draft(report)
        assert result == "Quoted Title"

    def test_extracts_title_with_single_quotes(self) -> None:
        report = "---\ntitle: 'Single Quoted'\n---\n\nBody.\n"
        result = svc._extract_title_from_report_draft(report)
        assert result == "Single Quoted"

    def test_returns_none_when_no_frontmatter(self) -> None:
        report = "# No Frontmatter\n\nBody text without YAML block.\n"
        result = svc._extract_title_from_report_draft(report)
        assert result is None

    def test_returns_none_when_title_key_absent(self) -> None:
        report = "---\ndate: 2026-06-13\nauthor: Test\n---\n\nBody.\n"
        result = svc._extract_title_from_report_draft(report)
        assert result is None

    def test_returns_none_for_none_input(self) -> None:
        assert svc._extract_title_from_report_draft(None) is None

    def test_returns_none_for_empty_string(self) -> None:
        assert svc._extract_title_from_report_draft("") is None

    def test_does_not_raise_on_malformed_frontmatter(self) -> None:
        # Should return None gracefully, not raise
        malformed = "---\ntitle:\n  nested:\n    value:\n---\n\nBody.\n"
        result = svc._extract_title_from_report_draft(malformed)
        # result may be None or empty — either is acceptable; must not raise
        assert result is None or isinstance(result, str)


class TestDeriveRunTitle:
    """Unit tests for _derive_run_title — the top-level title combinator."""

    def test_prefers_frontmatter_title_over_slug(self) -> None:
        report = "---\ntitle: Explicit Title From Frontmatter\n---\n# H1\n"
        result = svc._derive_run_title("rf_run_20260613_foo", report)
        assert result == "Explicit Title From Frontmatter"

    def test_falls_back_to_slug_when_no_frontmatter(self) -> None:
        result = svc._derive_run_title("rf_run_20260613_roots_wave", None)
        assert result == "Roots Wave"

    def test_falls_back_to_run_id_when_slug_is_empty(self) -> None:
        # An edge case where the slug normalizes to empty — should return raw run_id
        result = svc._derive_run_title("---", None)
        assert result  # must be non-empty
        assert isinstance(result, str)

    def test_always_returns_non_empty_string(self) -> None:
        # Even with no report_draft and a minimal run_id
        result = svc._derive_run_title("x", None)
        assert result
        assert isinstance(result, str)


class TestExportRunIncludesTitle:
    """Integration tests verifying the title field appears in export_run() output."""

    def test_export_run_includes_title_field(self, tmp_foundry: FoundryPaths) -> None:
        build_run(tmp_foundry)
        data = svc.export_run(tmp_foundry, "rf_run_test001")
        assert "title" in data
        assert data["title"] is not None
        assert isinstance(data["title"], str)
        assert len(data["title"]) > 0

    def test_export_run_title_uses_report_frontmatter(self, tmp_foundry: FoundryPaths) -> None:
        """When report_draft has a title: key, export uses it."""
        rp = build_run(tmp_foundry, with_report=False)
        report = "---\ntitle: Roots Wave High Priority\n---\n# Roots Wave High Priority\n\nBody.\n"
        rp.report_draft.write_text(report, encoding="utf-8")
        data = svc.export_run(tmp_foundry, "rf_run_test001")
        assert data["title"] == "Roots Wave High Priority"

    def test_export_run_title_falls_back_to_slug_when_no_report(
        self, tmp_foundry: FoundryPaths
    ) -> None:
        """When report_draft is absent, title is slug-humanized run_id."""
        build_run(tmp_foundry, with_report=False)
        data = svc.export_run(tmp_foundry, "rf_run_test001")
        assert "title" in data
        # slug of "rf_run_test001" → "Test001" (stripped rf_run_ prefix)
        assert data["title"] is not None
        assert data["title"] != "rf_run_test001"  # must NOT be the raw slug


# --------------------------------------------------------------------------
# P1-004: schema 1.2 backward-compat regression
# --------------------------------------------------------------------------

def test_schema_12_run_json_loads_without_context_key(tmp_foundry: FoundryPaths) -> None:
    """Backward-compat: a cached schema-1.2 run.json (no 'context' key) must not
    raise when accessed through the existing consumer interface.

    The export service always writes 1.3 now; this test ensures that a consumer
    reading a previously-cached run.json at schema 1.2 (which lacks the 'context'
    key entirely) can access all expected keys with safe optional access — matching
    how the frontend guards every field with `?.`.

    Concretely: build a run with no routing/swarm (context=None in 1.3), then
    simulate a 1.2-era dict by removing 'context' entirely, and verify that all
    1.2-era required keys are still present and that optional access on 'context'
    is safe.
    """
    build_run(tmp_foundry, "rf_run_compat12")
    data_13 = svc.export_run(tmp_foundry, "rf_run_compat12")

    # Simulate a schema-1.2 cached run.json: drop the 'context' key entirely
    data_12 = {k: v for k, v in data_13.items() if k != "context"}
    data_12["schema_version"] = "1.2"

    # 1. All 1.2-era required top-level keys must still be present
    required_12 = {
        "schema_version", "run_id", "status_derived", "status_raw",
        "sensitivity", "sensitivity_threshold", "claim_counts",
        "verification", "governance", "timeline", "claims",
    }
    assert required_12 <= set(data_12), required_12 - set(data_12)

    # 2. Accessing the absent 'context' key with .get() returns None safely
    ctx = data_12.get("context")
    assert ctx is None

    # 3. Optional chaining equivalents do not raise
    routing = (data_12.get("context") or {}).get("routing_decision")
    assert routing is None
    brief = (data_12.get("context") or {}).get("research_brief_md")
    assert brief is None

    # 4. The 1.3 export itself emits 'context' as a key (null or object)
    assert "context" in data_13  # key always present in 1.3 output


def test_schema_13_context_null_when_no_v2_artifacts(tmp_foundry: FoundryPaths) -> None:
    """Schema 1.3 runs without any v2 artifacts emit context=null (not key-omitted).

    This is the 'pre-v2 run re-exported under 1.3' case: context key is present
    but null, which is indistinguishable from the 1.3 null-placeholder shape from
    the frontend's perspective.
    """
    # build_run creates a run without routing_decision, swarm_plan, or research_brief.md
    build_run(tmp_foundry, "rf_run_noctx12")
    data = svc.export_run(tmp_foundry, "rf_run_noctx12")

    assert data["schema_version"] == "1.3"
    assert "context" in data
    assert data["context"] is None


def test_schema_13_context_shape_complete_when_v2_artifacts_present(
    tmp_foundry: FoundryPaths,
) -> None:
    """Schema 1.3: when v2 artifacts exist, context always has all 4 keys
    (routing_decision, swarm_plan, research_brief_md, upstream_entities).
    """
    _build_run_with_routing(tmp_foundry, "rf_run_ctx13")
    data = svc.export_run(tmp_foundry, "rf_run_ctx13")

    assert data["schema_version"] == "1.3"
    ctx = data.get("context")
    assert ctx is not None

    # All 4 keys must be present (even if null)
    for key in ("routing_decision", "swarm_plan", "research_brief_md", "upstream_entities"):
        assert key in ctx, f"context missing required key '{key}' in schema 1.3"

    # P2 now populates these when artifacts exist; _build_run_with_routing
    # writes neither a research_brief.md nor upstream IDs, so they stay null.
    assert ctx["research_brief_md"] is None
    assert ctx["upstream_entities"] is None
    # Existing fields from 1.2 still populated
    assert ctx["routing_decision"] is not None
    assert ctx["swarm_plan"] is not None


# --------------------------------------------------------------------------
# P2: context population (research_brief_md + upstream_entities) + redaction
# --------------------------------------------------------------------------

def _build_run_with_full_context(
    paths: FoundryPaths,
    run_id: str = "rf_run_p2ctx",
    *,
    with_routing: bool = True,
    with_swarm: bool = True,
    with_brief: bool = True,
    with_intent_id: bool = True,
    with_ibom_id: bool = True,
    with_node_id: bool = True,
    routing_sensitivity: str | None = None,
    swarm_sensitivity: str | None = None,
    brief_sensitivity: str | None = None,
) -> RunPaths:
    """Build a run with optional routing/swarm/brief artifacts + upstream IDs.

    Each source can be toggled independently to exercise the null-fill
    semantics (P2-002).  Sensitivity labels on each artifact drive the
    redaction pass (P2-003).
    """
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()

    run_yaml: dict[str, Any] = {
        "schema_version": "0.1",
        "type": "run",
        "run_id": run_id,
        "status": "planned",
    }
    if with_intent_id:
        run_yaml["intent_id"] = "intent_p2_001"
    if with_ibom_id:
        run_yaml["ibom_id"] = "ibom_p2_001"
    dump_yaml(run_yaml, rp.run_yaml)

    if with_routing:
        routing: dict[str, Any] = {
            "schema_version": "0.1",
            "type": "routing_decision",
            "id": f"route_{run_id}",
            "selected_abstraction_level": "L4",
            "rationale": "ROUTING_RATIONALE_TEXT",
            "human_required": False,
        }
        if with_node_id:
            routing["active_node_id"] = "node_p2_001"
        if routing_sensitivity is not None:
            routing["sensitivity"] = routing_sensitivity
        dump_yaml(routing, rp.routing_decision)

    if with_swarm:
        swarm: dict[str, Any] = {
            "schema_version": "0.1",
            "type": "swarm_plan",
            "id": f"swarm_{run_id}",
            "agents": [{"role": "source_scout"}, {"role": "synthesis_lead"}],
            "required_outputs": ["source_cards", "report_draft.md"],
            "swarm_notes": "SWARM_NOTES_TEXT",
        }
        if swarm_sensitivity is not None:
            swarm["sensitivity"] = swarm_sensitivity
        dump_yaml(swarm, rp.swarm_plan)

    if with_brief:
        if brief_sensitivity is not None:
            brief = (
                f"---\ntitle: Test Brief\nsensitivity: {brief_sensitivity}\n---\n\n"
                "# Research Brief\n\nBRIEF_BODY_TEXT.\n"
            )
        else:
            brief = "# Research Brief\n\nBRIEF_BODY_TEXT.\n"
        rp.research_brief.write_text(brief, encoding="utf-8")

    return rp


def test_context_all_four_sources_present(tmp_foundry: FoundryPaths) -> None:
    """BE-001: all 4 context sources present → all 4 keys populated correctly."""
    _build_run_with_full_context(tmp_foundry, "rf_run_be001")
    data = svc.export_run(
        tmp_foundry, "rf_run_be001", sensitivity_threshold="client_sensitive"
    )
    ctx = data["context"]
    assert ctx is not None

    # routing_decision
    assert ctx["routing_decision"] is not None
    assert ctx["routing_decision"]["rationale"] == "ROUTING_RATIONALE_TEXT"

    # swarm_plan
    assert ctx["swarm_plan"] is not None
    assert "source_scout" in ctx["swarm_plan"]["agents"]

    # research_brief_md — verbatim Markdown
    assert ctx["research_brief_md"] is not None
    assert "BRIEF_BODY_TEXT" in ctx["research_brief_md"]

    # upstream_entities — all three IDs
    ue = ctx["upstream_entities"]
    assert ue is not None
    assert ue["intent_id"] == "intent_p2_001"
    assert ue["ibom_id"] == "ibom_p2_001"
    assert ue["intenttree_node_id"] == "node_p2_001"


def test_context_research_brief_absent_independently(tmp_foundry: FoundryPaths) -> None:
    """BE-002: research_brief absent → field None, others populated."""
    _build_run_with_full_context(tmp_foundry, "rf_run_be002a", with_brief=False)
    ctx = svc.export_run(tmp_foundry, "rf_run_be002a")["context"]
    assert ctx is not None
    assert ctx["research_brief_md"] is None
    assert ctx["routing_decision"] is not None
    assert ctx["swarm_plan"] is not None
    assert ctx["upstream_entities"] is not None


def test_context_routing_absent_independently(tmp_foundry: FoundryPaths) -> None:
    """BE-002: routing_decision absent → field None, others populated."""
    _build_run_with_full_context(
        tmp_foundry, "rf_run_be002b", with_routing=False, with_node_id=False
    )
    ctx = svc.export_run(tmp_foundry, "rf_run_be002b")["context"]
    assert ctx is not None
    assert ctx["routing_decision"] is None
    assert ctx["swarm_plan"] is not None
    assert ctx["research_brief_md"] is not None
    # node_id falls back to None (no routing, no bundle node id)
    assert ctx["upstream_entities"]["intenttree_node_id"] is None
    assert ctx["upstream_entities"]["intent_id"] == "intent_p2_001"


def test_context_swarm_absent_independently(tmp_foundry: FoundryPaths) -> None:
    """BE-002: swarm_plan absent → field None, others populated."""
    _build_run_with_full_context(tmp_foundry, "rf_run_be002c", with_swarm=False)
    ctx = svc.export_run(tmp_foundry, "rf_run_be002c")["context"]
    assert ctx is not None
    assert ctx["swarm_plan"] is None
    assert ctx["routing_decision"] is not None
    assert ctx["research_brief_md"] is not None


def test_context_upstream_entities_absent_independently(
    tmp_foundry: FoundryPaths,
) -> None:
    """BE-002: all upstream IDs absent → upstream_entities None, others populated."""
    _build_run_with_full_context(
        tmp_foundry,
        "rf_run_be002d",
        with_intent_id=False,
        with_ibom_id=False,
        with_node_id=False,
    )
    ctx = svc.export_run(tmp_foundry, "rf_run_be002d")["context"]
    assert ctx is not None
    # all three IDs None → upstream_entities collapses to None
    assert ctx["upstream_entities"] is None
    assert ctx["routing_decision"] is not None
    assert ctx["swarm_plan"] is not None
    assert ctx["research_brief_md"] is not None


def test_context_partial_upstream_entities(tmp_foundry: FoundryPaths) -> None:
    """BE-002: one ID present → upstream_entities dict with that ID, others None."""
    _build_run_with_full_context(
        tmp_foundry,
        "rf_run_be002e",
        with_ibom_id=False,
        with_node_id=False,
    )
    ctx = svc.export_run(tmp_foundry, "rf_run_be002e")["context"]
    ue = ctx["upstream_entities"]
    assert ue is not None
    assert ue["intent_id"] == "intent_p2_001"
    assert ue["ibom_id"] is None
    assert ue["intenttree_node_id"] is None


def test_context_all_sources_absent_yields_null(tmp_foundry: FoundryPaths) -> None:
    """BE-002: all 4 sources absent → context is None.

    intent_id alone in run.yaml does NOT constitute a v2 context (backward
    compat: pre-v2 runs always carried an intent_id).
    """
    _build_run_with_full_context(
        tmp_foundry,
        "rf_run_be002f",
        with_routing=False,
        with_swarm=False,
        with_brief=False,
        with_node_id=False,
    )
    data = svc.export_run(tmp_foundry, "rf_run_be002f")
    assert "context" in data
    assert data["context"] is None


def test_context_node_id_falls_back_to_bundle(tmp_foundry: FoundryPaths) -> None:
    """BE-001/002: intenttree_node_id falls back to evidence_bundle governance."""
    rp = _build_run_with_full_context(
        tmp_foundry, "rf_run_be_fb", with_node_id=False
    )
    # Provide node id only via evidence_bundle governance block.
    dump_yaml(
        {
            "schema_version": "0.1",
            "run_id": "rf_run_be_fb",
            "governance": {"intenttree_node_id": "node_from_bundle"},
        },
        rp.evidence_bundle,
    )
    ctx = svc.export_run(tmp_foundry, "rf_run_be_fb")["context"]
    assert ctx["upstream_entities"]["intenttree_node_id"] == "node_from_bundle"


def test_context_redacts_work_sensitive_routing_and_swarm(
    tmp_foundry: FoundryPaths,
) -> None:
    """BE-003: work_sensitive routing/swarm content is redacted at public threshold."""
    _build_run_with_full_context(
        tmp_foundry,
        "rf_run_be003a",
        routing_sensitivity="work_sensitive",
        swarm_sensitivity="work_sensitive",
        with_brief=False,
    )
    # explicit public threshold; work_sensitive exceeds it → redact
    data = svc.export_run(tmp_foundry, "rf_run_be003a", sensitivity_threshold="public")
    blob = _json_blob(data)
    assert "ROUTING_RATIONALE_TEXT" not in blob
    assert "SWARM_NOTES_TEXT" not in blob
    # Redaction marker present in the redacted string fields
    ctx = data["context"]
    assert ctx["routing_decision"]["rationale"] == svc.REDACTION_MARKER
    # Non-string structural metadata survives redaction (human_required bool)
    assert ctx["routing_decision"]["human_required"] is False


def test_context_routing_swarm_not_redacted_when_threshold_raised(
    tmp_foundry: FoundryPaths,
) -> None:
    """BE-003: raising the threshold lets work_sensitive context through."""
    _build_run_with_full_context(
        tmp_foundry,
        "rf_run_be003b",
        routing_sensitivity="work_sensitive",
        swarm_sensitivity="work_sensitive",
        with_brief=False,
    )
    data = svc.export_run(
        tmp_foundry, "rf_run_be003b", sensitivity_threshold="work_sensitive"
    )
    blob = _json_blob(data)
    assert "ROUTING_RATIONALE_TEXT" in blob
    assert "SWARM_NOTES_TEXT" in blob


def test_context_work_sensitive_not_redacted_at_production_threshold(
    tmp_foundry: FoundryPaths,
) -> None:
    """BE-003: work_sensitive context passes through unredacted at the production default.

    The distribution foundry.yaml pins ``viewer.sensitivity_threshold: client_sensitive``
    (rank 3).  ``work_sensitive`` is rank 2.  Because 2 ≤ 3 the content is BELOW the
    redaction cut-off and intentionally survives the export — this is the operator's
    deliberate configuration choice, not a bug.

    This test exists as a governance sentinel: if someone accidentally tightens the
    production threshold (e.g. changes it to ``work_sensitive`` or lower) these
    assertions will fail loudly, requiring a conscious decision to update them.
    """
    _build_run_with_full_context(
        tmp_foundry,
        "rf_run_be003_prod",
        routing_sensitivity="work_sensitive",
        swarm_sensitivity="work_sensitive",
        with_brief=False,
    )
    # No sensitivity_threshold override → tmp_foundry uses the copied production
    # foundry.yaml which sets viewer.sensitivity_threshold = client_sensitive.
    data = svc.export_run(tmp_foundry, "rf_run_be003_prod")
    blob = _json_blob(data)
    # Sentinels must survive — work_sensitive is below client_sensitive threshold
    assert "ROUTING_RATIONALE_TEXT" in blob, (
        "work_sensitive routing rationale was unexpectedly redacted at the "
        "production threshold (client_sensitive); check foundry.yaml viewer config"
    )
    assert "SWARM_NOTES_TEXT" in blob, (
        "work_sensitive swarm notes were unexpectedly redacted at the "
        "production threshold (client_sensitive); check foundry.yaml viewer config"
    )
    # Confirm no redaction marker crept in for these fields
    ctx = data["context"]
    assert ctx["routing_decision"]["rationale"] != svc.REDACTION_MARKER
    assert ctx["routing_decision"]["rationale"] == "ROUTING_RATIONALE_TEXT"


def test_context_redacts_work_sensitive_research_brief(
    tmp_foundry: FoundryPaths,
) -> None:
    """BE-003: research_brief_md tagged work_sensitive → redacted wholesale."""
    _build_run_with_full_context(
        tmp_foundry,
        "rf_run_be003c",
        brief_sensitivity="work_sensitive",
    )
    data = svc.export_run(tmp_foundry, "rf_run_be003c", sensitivity_threshold="public")
    ctx = data["context"]
    assert ctx["research_brief_md"] == svc.REDACTION_MARKER
    assert "BRIEF_BODY_TEXT" not in _json_blob(data)


def test_context_public_research_brief_not_redacted(tmp_foundry: FoundryPaths) -> None:
    """BE-003: a public/untagged research brief survives at public threshold."""
    _build_run_with_full_context(
        tmp_foundry, "rf_run_be003d", brief_sensitivity="public"
    )
    ctx = svc.export_run(tmp_foundry, "rf_run_be003d")["context"]
    assert ctx["research_brief_md"] is not None
    assert "BRIEF_BODY_TEXT" in ctx["research_brief_md"]


def test_context_full_pipeline_round_trip(tmp_foundry: FoundryPaths) -> None:
    """BE-004: full export pipeline round-trip → context present, schema 1.3.

    Writes run.json to disk, reads it back, and asserts the populated +
    redacted context survives JSON serialization with all 4 keys intact.
    """
    import json

    _build_run_with_full_context(
        tmp_foundry,
        "rf_run_be004",
        routing_sensitivity="work_sensitive",
        brief_sensitivity="public",
    )
    out = svc.export_to_file(
        tmp_foundry, "rf_run_be004", sensitivity_threshold="public"
    )
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))

    assert data["schema_version"] == "1.3"
    ctx = data["context"]
    assert ctx is not None
    for key in (
        "routing_decision",
        "swarm_plan",
        "research_brief_md",
        "upstream_entities",
    ):
        assert key in ctx, f"context missing key {key!r} after round-trip"

    # work_sensitive routing redacted at default public threshold
    assert ctx["routing_decision"]["rationale"] == svc.REDACTION_MARKER
    # public brief survives
    assert ctx["research_brief_md"] is not None
    assert "BRIEF_BODY_TEXT" in ctx["research_brief_md"]
    # upstream entities populated
    assert ctx["upstream_entities"]["intent_id"] == "intent_p2_001"
    assert ctx["upstream_entities"]["intenttree_node_id"] == "node_p2_001"
