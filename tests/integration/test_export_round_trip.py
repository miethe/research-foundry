"""Integration round-trip: export the real rf_run_20260613_* run end-to-end.

Asserts the export contract holds against actual 91-claim run data:
* every ``[claim:clm_NNN]`` cited in the report draft has a ``claims[]`` entry;
* sampled supported claims carry non-empty quotes (threshold permits personal);
* the export exits 0 and validates against the frozen schema shape.

Skips cleanly if the reference run is absent (e.g. a partial checkout).
"""

from __future__ import annotations

import json

import pytest

from research_foundry.paths import FoundryPaths
from research_foundry.services import export_service as svc

REF_RUN = "rf_run_20260613_what_is_the_current_release_state"


@pytest.fixture(scope="module")
def real_paths() -> FoundryPaths:
    paths = FoundryPaths.discover()
    rp = paths.run_paths(REF_RUN)
    if not rp.run_yaml.exists():
        pytest.skip(f"reference run {REF_RUN} not present")
    return paths


def _export(real_paths: FoundryPaths) -> dict:
    # Threshold raised to work_sensitive so the run's personal-sensitivity
    # cards expose their quotes — proving the claim->source->quote chain.
    return svc.export_run(real_paths, REF_RUN, sensitivity_threshold="work_sensitive")


def test_every_report_claim_tag_has_claim_entry(real_paths: FoundryPaths) -> None:
    data = _export(real_paths)
    rp = real_paths.run_paths(REF_RUN)
    cited = set(svc.claim_tags_in_report(rp.report_draft))
    assert cited, "expected at least one [claim:clm_NNN] tag in the report"
    claim_ids = {c["claim_id"] for c in data["claims"]}
    missing = cited - claim_ids
    assert not missing, f"report cites claims missing from export: {sorted(missing)}"


def test_sampled_claims_have_nonempty_quote(real_paths: FoundryPaths) -> None:
    data = _export(real_paths)
    with_sources = [
        c for c in data["claims"]
        if c["sources"] and any(s.get("resolved") for s in c["sources"])
    ]
    assert len(with_sources) >= 3
    # deterministic sample: evenly spaced across the sorted set
    sampled = [with_sources[0],
               with_sources[len(with_sources) // 2],
               with_sources[-1]]
    for claim in sampled:
        resolved = [s for s in claim["sources"] if s.get("resolved")]
        assert resolved, f"claim {claim['claim_id']} lost its resolved source"
        assert any(
            s["quote"] and s["quote"] != svc.REDACTION_MARKER for s in resolved
        ), f"claim {claim['claim_id']} has no non-empty quote"


def test_export_status_is_not_stale(real_paths: FoundryPaths) -> None:
    data = _export(real_paths)
    # run.yaml.status is the stale 'planned'; derived status must advance past it.
    assert data["status_raw"] == "planned"
    assert data["status_derived"] in {"verified", "published"}


def test_run_json_validates_against_frozen_schema(real_paths: FoundryPaths) -> None:
    out = svc.export_to_file(real_paths, REF_RUN,
                             sensitivity_threshold="work_sensitive")
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    _assert_matches_frozen_schema(data)


def _assert_matches_frozen_schema(data: dict) -> None:
    """Lightweight structural validator mirroring rf-run-export-schema.md."""

    required_top = {
        "schema_version", "run_id", "status_derived", "status_raw",
        "sensitivity", "sensitivity_threshold", "claim_counts",
        "verification", "governance", "timeline", "claims",
    }
    assert required_top <= set(data), required_top - set(data)
    assert data["schema_version"] == svc.EXPORT_SCHEMA_VERSION
    assert data["status_derived"] in svc.STATUS_LADDER
    assert isinstance(data["claims"], list) and data["claims"]
    assert isinstance(data["verification"], dict)
    assert "checks" in data["verification"]

    for claim in data["claims"]:
        assert "claim_id" in claim
        assert "inference_basis" in claim
        assert "from_claims" in claim["inference_basis"]
        assert isinstance(claim["sources"], list)
        for src in claim["sources"]:
            assert {"source_card_id", "evidence_id", "resolved", "redacted"} <= set(src)
