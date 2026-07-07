"""R9 sensitivity gate (P1-SENS-001).

A synthetic ``src_SYNTH001`` source card carries a ``work_sensitive`` evidence
point. The export service MUST drop its quote/body before the JSON is produced,
so no frontend component can ever surface governed content. Public content from
the same run must still appear. Repeatable in CI (no network, no real data).

Also covers P5.7.2 — the global source index that closes the blank-origin-draft
residual: a draft with no declared sources that embeds sensitive text must fail
``verify_draft``, and a cross-run quote must also fail.
"""

from __future__ import annotations

import json

import pytest

from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import builder_service as bsvc
from research_foundry.services import export_service as svc
from research_foundry.services import verification as vsvc
from research_foundry.yamlio import dump_yaml

WORK_SENSITIVE_QUOTE = "INTERNAL_WORK_ONLY_REVENUE_FIGURE_42M"
PUBLIC_QUOTE = "PUBLICLY_DOCUMENTED_RELEASE_0_2_101"


def _build_synth_run(paths: FoundryPaths) -> str:
    run_id = "rf_run_synth_sensitivity"
    rp = paths.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml({"run_id": run_id, "status": "verified", "sensitivity": "personal"},
              rp.run_yaml)

    # The governed card: card-level work_sensitive.
    dump_md(
        {
            "schema_version": "0.1",
            "type": "source_card",
            "source_card_id": "src_SYNTH001",
            "sensitivity": "work_sensitive",
            "source": {"title": "Internal Memo", "source_type": "doc",
                       "locator": {"url": "file:///internal/memo"}},
            "trust": {"source_rank": "primary"},
            "usage": {"allowed_for_public_output": False, "allowed_for_work_output": True},
            "extracted_points": [
                {"evidence_id": "ev_001", "locator": "p1",
                 "summary": "the sensitive revenue figure",
                 "quote": WORK_SENSITIVE_QUOTE},
            ],
        },
        "",
        rp.sources / "src_SYNTH001.md",
    )
    # A public card whose content must survive.
    dump_md(
        {
            "schema_version": "0.1",
            "type": "source_card",
            "source_card_id": "src_SYNTH002",
            "sensitivity": "public",
            "source": {"title": "PyPI Page", "source_type": "web",
                       "locator": {"url": "https://pypi.org/x"}},
            "extracted_points": [
                {"evidence_id": "ev_001", "locator": "p1", "summary": "public fact",
                 "quote": PUBLIC_QUOTE},
            ],
        },
        "",
        rp.sources / "src_SYNTH002.md",
    )

    dump_yaml(
        {
            "claims": [
                {"claim_id": "clm_001", "text": "sensitive claim", "status": "supported",
                 "sources": [{"source_card_id": "src_SYNTH001", "evidence_id": "ev_001",
                              "relation": "supports", "locator": "p1"}]},
                {"claim_id": "clm_002", "text": "public claim", "status": "supported",
                 "sources": [{"source_card_id": "src_SYNTH002", "evidence_id": "ev_001",
                              "relation": "supports", "locator": "p1"}]},
            ]
        },
        rp.claim_ledger,
    )
    return run_id


def test_work_sensitive_quote_absent_at_default_public_threshold(
    tmp_foundry: FoundryPaths,
) -> None:
    run_id = _build_synth_run(tmp_foundry)
    # default threshold from foundry.yaml is 'public'
    data = svc.export_run(tmp_foundry, run_id)
    blob = json.dumps(data, ensure_ascii=False)

    # R9 gate: governed content NEVER reaches the export JSON.
    assert WORK_SENSITIVE_QUOTE not in blob
    assert "the sensitive revenue figure" not in blob  # summary redacted too
    # public content survives the same export.
    assert PUBLIC_QUOTE in blob

    sens_claim = next(c for c in data["claims"] if c["claim_id"] == "clm_001")
    sens_src = sens_claim["sources"][0]
    assert sens_src["redacted"] is True
    assert sens_src["quote"] == svc.REDACTION_MARKER


def test_round_trips_via_export_to_file(tmp_foundry: FoundryPaths) -> None:
    run_id = _build_synth_run(tmp_foundry)
    out = svc.export_to_file(tmp_foundry, run_id)
    assert WORK_SENSITIVE_QUOTE not in out.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# FIX 1 regression: null/absent quote+summary on a redacted point
# --------------------------------------------------------------------------
def test_null_quote_and_summary_on_sensitive_point_still_show_marker(
    tmp_foundry: FoundryPaths,
) -> None:
    """FIX 1 regression (R9 governance gap).

    A ``work_sensitive`` evidence point whose ``quote`` AND ``summary`` are
    absent (None) must still export both fields as ``REDACTION_MARKER`` when
    the threshold is below ``work_sensitive``.

    The old ``redacted and value`` conjunction silently passed ``None`` through
    — a consumer could then distinguish "never authored" from "redacted",
    leaking governance state.  The corrected guard uses ``redacted`` alone.
    """
    run_id = "rf_run_null_sens_test"
    rp = tmp_foundry.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {"run_id": run_id, "status": "planned", "sensitivity": "work_sensitive"},
        rp.run_yaml,
    )
    # evidence point is work_sensitive but has no quote and no summary
    dump_md(
        {
            "schema_version": "0.1",
            "type": "source_card",
            "source_card_id": "src_nullsens",
            "sensitivity": "work_sensitive",
            "source": {
                "title": "Null Sens Card",
                "source_type": "doc",
                "locator": {"url": "file:///internal/null"},
            },
            "extracted_points": [
                {"evidence_id": "ev_001", "locator": "p1"},  # no quote, no summary
            ],
        },
        "",
        rp.sources / "src_nullsens.md",
    )
    dump_yaml(
        {
            "claims": [
                {
                    "claim_id": "clm_001",
                    "text": "null-field sensitive claim",
                    "status": "supported",
                    "sources": [
                        {
                            "source_card_id": "src_nullsens",
                            "evidence_id": "ev_001",
                            "relation": "supports",
                            "locator": "p1",
                        }
                    ],
                }
            ]
        },
        rp.claim_ledger,
    )
    # default threshold is "public" < "work_sensitive" → point is redacted
    data = svc.export_run(tmp_foundry, run_id)
    src = data["claims"][0]["sources"][0]

    assert src["redacted"] is True, "point with work_sensitive card must be flagged redacted"
    assert src["quote"] == svc.REDACTION_MARKER, (
        "null quote on a redacted point must surface REDACTION_MARKER, not None"
    )
    assert src["summary"] == svc.REDACTION_MARKER, (
        "null summary on a redacted point must surface REDACTION_MARKER, not None"
    )


# --------------------------------------------------------------------------
# FIX 2 regression: invalid threshold must fail closed
# --------------------------------------------------------------------------
def test_invalid_threshold_raises_export_error(tmp_foundry: FoundryPaths) -> None:
    """FIX 2 regression: a bogus threshold label must raise ExportError.

    Previously an unrecognized label mapped to ``_UNKNOWN_SENSITIVITY`` rank
    (> every known rank), causing nothing to be redacted — a silent fail-open.
    ``resolve_threshold`` now validates the resolved label and raises before
    any export logic runs.
    """
    with pytest.raises(svc.ExportError, match="unknown sensitivity threshold") as exc_info:
        svc.resolve_threshold(tmp_foundry, override="bogus_level")
    assert "valid values" in str(exc_info.value)


def test_valid_threshold_labels_all_resolve_without_error(
    tmp_foundry: FoundryPaths,
) -> None:
    """FIX 2: every label in SENSITIVITY_ORDER must still resolve cleanly."""
    for label in svc.SENSITIVITY_ORDER:
        result = svc.resolve_threshold(tmp_foundry, override=label)
        assert result == label


# --------------------------------------------------------------------------
# P5.7.2 — build_global_source_index + blank-origin-draft gap
# --------------------------------------------------------------------------

_GLOBAL_SENSITIVE_QUOTE = "GLOBAL_WORK_SENSITIVE_SECRET_TOKEN_XYZ"
_POINT_SENSITIVE_QUOTE = "POINT_LEVEL_SENSITIVE_REVENUE_TOKEN_ABC"
_NESTED_RUN_SENSITIVE_QUOTE = "NESTED_RUN_SENSITIVE_TOKEN_DEF_456"


def _build_two_runs_for_global_index(paths: FoundryPaths) -> tuple[str, str]:
    """Plant two runs with source cards in the workspace.

    run_A has a work_sensitive card (src_A_secret).
    run_B has a public card (src_B_public).
    Returns (run_A_id, run_B_id).
    """
    run_a = "rf_run_global_idx_a"
    run_b = "rf_run_global_idx_b"

    for run_id in (run_a, run_b):
        rp = paths.run_paths(run_id)
        rp.ensure_scaffold()
        dump_yaml(
            {"run_id": run_id, "status": "verified", "sensitivity": "public"},
            rp.run_yaml,
        )

    # sensitive card in run_A
    dump_md(
        {
            "schema_version": "0.1",
            "type": "source_card",
            "source_card_id": "src_A_secret",
            "sensitivity": "work_sensitive",
            "source": {
                "title": "Internal Run A Doc",
                "source_type": "doc",
                "locator": {"url": "file:///internal/a"},
            },
            "extracted_points": [
                {
                    "evidence_id": "ev_a",
                    "locator": "p1",
                    "summary": "top-secret figure",
                    "quote": _GLOBAL_SENSITIVE_QUOTE,
                }
            ],
        },
        "",
        paths.run_paths(run_a).sources / "src_A_secret.md",
    )

    # public card in run_B
    dump_md(
        {
            "schema_version": "0.1",
            "type": "source_card",
            "source_card_id": "src_B_public",
            "sensitivity": "public",
            "source": {
                "title": "Public Run B Doc",
                "source_type": "web",
                "locator": {"url": "https://example.com/b"},
            },
            "extracted_points": [
                {
                    "evidence_id": "ev_b",
                    "locator": "p1",
                    "summary": "public fact",
                    "quote": "TOTALLY_PUBLIC_FACT_B",
                }
            ],
        },
        "",
        paths.run_paths(run_b).sources / "src_B_public.md",
    )

    return run_a, run_b


def test_build_global_source_index_maps_all_runs(tmp_foundry: FoundryPaths) -> None:
    """build_global_source_index returns a correct workspace-wide mapping."""
    run_a, run_b = _build_two_runs_for_global_index(tmp_foundry)

    index = vsvc.build_global_source_index(tmp_foundry)

    # Both source cards must appear.
    assert "src_A_secret" in index
    assert "src_B_public" in index

    # Verify correct (run_id, sensitivity) tuples.
    assert index["src_A_secret"] == (run_a, "work_sensitive")
    assert index["src_B_public"] == (run_b, "public")


def test_build_global_source_index_fail_closed_on_unreadable_sources_dir(
    tmp_foundry: FoundryPaths,
) -> None:
    """Fail-closed: a run whose sources/ dir raises OSError on listing must be
    included as a sentinel rather than silently omitted.

    Python 3.12+ glob() silently ignores PermissionError on macOS, so we
    simulate the I/O failure via a mock that raises at the glob() call site —
    the only reliable cross-platform way to exercise this code path in CI.
    """
    from pathlib import Path
    from unittest.mock import patch

    run_id = "rf_run_global_idx_locked"
    rp = tmp_foundry.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml({"run_id": run_id, "status": "verified"}, rp.run_yaml)
    rp.sources.mkdir(parents=True, exist_ok=True)

    _target = rp.sources.resolve()
    _original_glob = Path.glob

    def _failing_glob(self: Path, pattern: str, **kw):  # type: ignore[override]
        if self.resolve() == _target:
            raise PermissionError("simulated: unreadable sources/ dir")
        return _original_glob(self, pattern, **kw)

    with patch.object(type(rp.sources), "glob", _failing_glob):
        index = vsvc.build_global_source_index(tmp_foundry)

    # The locked run must appear as a sentinel — not silently dropped.
    sentinel_keys = [k for k in index if k.startswith(vsvc._IO_ERROR_SENTINEL_PREFIX)]
    assert any(run_id in k for k in sentinel_keys), (
        f"expected a sentinel for {run_id!r} but got keys: {list(index.keys())}"
    )
    # The real card from the locked run must NOT appear (we couldn't read it).
    assert "src_locked" not in index


def test_verify_draft_fails_blank_origin_draft_with_sensitive_body(
    tmp_foundry: FoundryPaths,
) -> None:
    """P5.7.2 integration — a blank-origin draft (no source_run_id, no
    source_links, no claim_links) that pastes a sensitive raw quote into its
    body must fail verify_draft via the global check even though the per-run
    check finds no run_ids to scan."""
    run_a, _ = _build_two_runs_for_global_index(tmp_foundry)

    # Create a draft with NO link to any run.
    draft = bsvc.create_draft(
        tmp_foundry,
        title="Blank Origin Leaky Draft",
        sensitivity="public",
        # Deliberately no source_run_id
    )
    report_draft_id = draft["report_draft_id"]
    bsvc.add_block(
        tmp_foundry,
        report_draft_id,
        markdown=f"Some narrative text pasted in: {_GLOBAL_SENSITIVE_QUOTE}",
        materiality="narrative",
    )
    # No claim_link, no source_link added.

    result = vsvc.verify_draft(tmp_foundry, report_draft_id)

    assert result.passed is False
    global_check = next(
        c for c in result.checks if c.id == "report_body_sensitivity_global"
    )
    assert global_check.status == "fail", (
        "global check must fail when blank-origin draft embeds sensitive text"
    )
    # The existing per-run check must still pass (no run_ids → nothing to scan).
    per_run_check = next(c for c in result.checks if c.id == "report_body_sensitivity")
    assert per_run_check.status == "pass", (
        "per-run check should pass (no declared runs) but global check catches the leak"
    )


def test_verify_draft_fails_cross_run_quote_not_in_declared_sources(
    tmp_foundry: FoundryPaths,
) -> None:
    """P5.7.2 integration — a draft whose body quotes a source card from a run
    that is NOT listed in its declared source_links/claim_links must fail via
    the global check."""
    run_a, run_b = _build_two_runs_for_global_index(tmp_foundry)

    # Create a draft linked only to run_B (the public run), then paste a
    # quote from run_A's sensitive card — run_A is NOT a declared source.
    draft = bsvc.create_draft(
        tmp_foundry,
        title="Cross-Run Leak Draft",
        sensitivity="public",
        source_run_id=run_b,  # only run_B is declared
    )
    report_draft_id = draft["report_draft_id"]
    bsvc.add_block(
        tmp_foundry,
        report_draft_id,
        markdown=f"Cross-run paste: {_GLOBAL_SENSITIVE_QUOTE}",
        materiality="narrative",
    )
    # No source_link or claim_link to run_A — it's not in declared sources.

    result = vsvc.verify_draft(tmp_foundry, report_draft_id)

    assert result.passed is False
    global_check = next(
        c for c in result.checks if c.id == "report_body_sensitivity_global"
    )
    assert global_check.status == "fail", (
        "global check must flag a quote from a run not in the draft's declared sources"
    )


# --------------------------------------------------------------------------
# P5.7.2 remediation — Gap 1 (point-level sensitivity) and Gap 2 (nested runs)
# --------------------------------------------------------------------------


def test_verify_draft_fails_point_level_sensitivity_in_global_index(
    tmp_foundry: FoundryPaths,
) -> None:
    """P5.7.2 gap 1 — build_global_source_index must store effective sensitivity.

    A source card whose ``meta.sensitivity`` is ``"public"`` but whose
    ``extracted_points[]`` entry has ``sensitivity = "work_sensitive"`` has an
    effective sensitivity of ``"work_sensitive"``.  A blank-origin draft that
    embeds that point's quote text must fail ``verify_draft`` via the global
    check, even though the card-level label alone would pass the threshold gate.
    """
    run_id = "rf_run_point_sens_gap"
    rp = tmp_foundry.run_paths(run_id)
    rp.ensure_scaffold()
    dump_yaml(
        {"run_id": run_id, "status": "verified", "sensitivity": "public"},
        rp.run_yaml,
    )
    # Card-level sensitivity is "public" — the old broken index would store "public"
    # and let the draft through.  The point-level "work_sensitive" must win.
    dump_md(
        {
            "schema_version": "0.1",
            "type": "source_card",
            "source_card_id": "src_point_sens",
            "sensitivity": "public",
            "source": {
                "title": "Point Sens Card",
                "source_type": "doc",
                "locator": {"url": "file:///internal/point"},
            },
            "extracted_points": [
                {
                    "evidence_id": "ev_ps",
                    "locator": "p1",
                    "summary": "a point-level sensitive fact",
                    "quote": _POINT_SENSITIVE_QUOTE,
                    "sensitivity": "work_sensitive",
                }
            ],
        },
        "",
        rp.sources / "src_point_sens.md",
    )

    # Blank-origin draft: no source_run_id, no source_links, no claim_links.
    draft = bsvc.create_draft(
        tmp_foundry,
        title="Point Sens Leak Draft",
        sensitivity="public",
    )
    report_draft_id = draft["report_draft_id"]
    bsvc.add_block(
        tmp_foundry,
        report_draft_id,
        markdown=f"Pasted point quote: {_POINT_SENSITIVE_QUOTE}",
        materiality="narrative",
    )

    result = vsvc.verify_draft(tmp_foundry, report_draft_id)

    assert result.passed is False, (
        "draft embedding a point-level sensitive quote must fail verify_draft"
    )
    global_check = next(
        c for c in result.checks if c.id == "report_body_sensitivity_global"
    )
    assert global_check.status == "fail", (
        "global check must catch point-level sensitive quote even when card-level "
        "sensitivity is 'public'"
    )


def test_verify_draft_fails_nested_run_source_card_indexed(
    tmp_foundry: FoundryPaths,
) -> None:
    """P5.7.2 gap 2 — build_global_source_index must discover nested runs.

    A source card under ``runs/nested_runs/<run_id>/sources/`` (depth 2) must
    appear in the global index.  A blank-origin draft that embeds its sensitive
    quote must fail ``verify_draft`` via the global check.
    """
    # Create a run nested TWO levels under paths.runs (runs/nested_runs/<id>/).
    nested_parent = tmp_foundry.runs / "nested_runs"
    nested_parent.mkdir(parents=True, exist_ok=True)
    nested_run_id = "rf_run_nested_sens"
    run_dir = nested_parent / nested_run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    sources_dir = run_dir / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run.yaml").write_text(
        f"run_id: {nested_run_id}\nstatus: verified\nsensitivity: work_sensitive\n",
        encoding="utf-8",
    )
    dump_md(
        {
            "schema_version": "0.1",
            "type": "source_card",
            "source_card_id": "src_nested_secret",
            "sensitivity": "work_sensitive",
            "source": {
                "title": "Nested Run Doc",
                "source_type": "doc",
                "locator": {"url": "file:///internal/nested"},
            },
            "extracted_points": [
                {
                    "evidence_id": "ev_ns",
                    "locator": "p1",
                    "summary": "nested run sensitive fact",
                    "quote": _NESTED_RUN_SENSITIVE_QUOTE,
                }
            ],
        },
        "",
        sources_dir / "src_nested_secret.md",
    )

    # Blank-origin draft: no source_run_id, no source_links, no claim_links.
    draft = bsvc.create_draft(
        tmp_foundry,
        title="Nested Run Leak Draft",
        sensitivity="public",
    )
    report_draft_id = draft["report_draft_id"]
    bsvc.add_block(
        tmp_foundry,
        report_draft_id,
        markdown=f"Copied from nested run: {_NESTED_RUN_SENSITIVE_QUOTE}",
        materiality="narrative",
    )

    result = vsvc.verify_draft(tmp_foundry, report_draft_id)

    assert result.passed is False, (
        "draft quoting a nested-run sensitive source must fail verify_draft"
    )
    global_check = next(
        c for c in result.checks if c.id == "report_body_sensitivity_global"
    )
    assert global_check.status == "fail", (
        "global check must index source cards from nested-run directories and catch the leak"
    )
