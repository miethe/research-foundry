"""R9 sensitivity gate (P1-SENS-001).

A synthetic ``src_SYNTH001`` source card carries a ``work_sensitive`` evidence
point. The export service MUST drop its quote/body before the JSON is produced,
so no frontend component can ever surface governed content. Public content from
the same run must still appear. Repeatable in CI (no network, no real data).
"""

from __future__ import annotations

import json

import pytest

from research_foundry.frontmatter import dump_md
from research_foundry.paths import FoundryPaths
from research_foundry.services import export_service as svc
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
