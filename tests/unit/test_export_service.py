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
    assert data["schema_version"] == svc.EXPORT_SCHEMA_VERSION == "1.1"
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


def test_schema_version_is_1_1(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry)
    data = svc.export_run(tmp_foundry, "rf_run_test001")
    assert data["schema_version"] == "1.1"


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
