"""Unit tests for `_term_index` propagation through the run export layer
(claim-term-indexing v1, Phase 2, TASK-2.1/TASK-2.2).

`_term_index` is written by ``services/term_index.py`` (Phase 1) directly
onto claim ledger entries. The export layer's only job here is to copy the
block forward verbatim -- these tests lock in additivity (schema 1.7),
omission-on-absence, and backward compatibility for pre-1.7 consumers.
"""

from __future__ import annotations

import json

from research_foundry.paths import FoundryPaths
from research_foundry.services import export_service as svc
from research_foundry.yamlio import dump_yaml, load_yaml

from tests.unit.test_export_service import build_run

_SAMPLE_TERM_INDEX = {
    "terms": ["cbc", "hemoglobin"],
    "usage_roles": {"cbc": "background", "hemoglobin": "threshold"},
    "vocabulary_version": "pediatric-terms-v1",
}


def _plant_term_index_on_clm_001(rp, term_index: dict) -> None:
    ledger = load_yaml(rp.claim_ledger)
    claim = next(c for c in ledger["claims"] if c["claim_id"] == "clm_001")
    claim["_term_index"] = term_index
    dump_yaml(ledger, rp.claim_ledger)


# --------------------------------------------------------------------------
# schema version bump
# --------------------------------------------------------------------------
def test_schema_version_bumped_to_1_7(tmp_foundry: FoundryPaths) -> None:
    build_run(tmp_foundry, "rf_run_ti_ver")
    data = svc.export_run(tmp_foundry, "rf_run_ti_ver")
    assert svc.EXPORT_SCHEMA_VERSION == "1.8"
    assert data["schema_version"] == "1.8"


# --------------------------------------------------------------------------
# TASK-2.1 AC: run.json includes _term_index for indexed claims
# --------------------------------------------------------------------------
def test_term_index_included_for_indexed_claim(tmp_foundry: FoundryPaths) -> None:
    rp = build_run(tmp_foundry, "rf_run_ti_present")
    _plant_term_index_on_clm_001(rp, _SAMPLE_TERM_INDEX)

    data = svc.export_run(tmp_foundry, "rf_run_ti_present")
    clm = next(c for c in data["claims"] if c["claim_id"] == "clm_001")
    assert clm["_term_index"] == _SAMPLE_TERM_INDEX


# --------------------------------------------------------------------------
# TASK-2.1 AC: a legacy claim with no _term_index exports cleanly (key
# omitted entirely, mirroring claim-map's own omission convention).
# --------------------------------------------------------------------------
def test_legacy_claim_without_term_index_exports_with_key_omitted(
    tmp_foundry: FoundryPaths,
) -> None:
    build_run(tmp_foundry, "rf_run_ti_absent")  # standard fixture, no _term_index
    data = svc.export_run(tmp_foundry, "rf_run_ti_absent")

    assert data["claims"], "fixture must produce at least one claim"
    for claim in data["claims"]:
        assert "_term_index" not in claim


def test_mixed_ledger_only_indexed_claim_carries_the_key(
    tmp_foundry: FoundryPaths,
) -> None:
    """One claim carries `_term_index`, the rest of the ledger does not --
    export must not backfill or synthesize the key onto siblings."""
    rp = build_run(tmp_foundry, "rf_run_ti_mixed")
    _plant_term_index_on_clm_001(rp, _SAMPLE_TERM_INDEX)

    data = svc.export_run(tmp_foundry, "rf_run_ti_mixed")
    by_id = {c["claim_id"]: c for c in data["claims"]}
    assert by_id["clm_001"]["_term_index"] == _SAMPLE_TERM_INDEX
    for claim_id in ("clm_002", "clm_inf03", "clm_004", "clm_005"):
        assert "_term_index" not in by_id[claim_id]


# --------------------------------------------------------------------------
# non-authoritative: presence/content of _term_index must not perturb any
# other exported field (status, verification, claim_counts, sources).
# --------------------------------------------------------------------------
def test_term_index_does_not_perturb_other_claim_fields(
    tmp_foundry: FoundryPaths,
) -> None:
    rp = build_run(tmp_foundry, "rf_run_ti_inert")
    baseline = svc.export_run(tmp_foundry, "rf_run_ti_inert")
    baseline_clm1 = next(c for c in baseline["claims"] if c["claim_id"] == "clm_001")

    _plant_term_index_on_clm_001(rp, _SAMPLE_TERM_INDEX)
    data = svc.export_run(tmp_foundry, "rf_run_ti_inert")
    clm1 = next(c for c in data["claims"] if c["claim_id"] == "clm_001")

    for key in ("claim_id", "text", "materiality", "claim_type", "status",
                "confidence", "report_locations", "inference_basis", "sources"):
        assert clm1[key] == baseline_clm1[key]
    assert data["claim_counts"] == baseline["claim_counts"]
    assert data["verification"] == baseline["verification"]


# --------------------------------------------------------------------------
# TASK-2.1 AC: a 1.6-shaped consumer fixture still parses 1.7 output without
# error. A 1.6-era consumer only knows the pre-1.7 RFClaim key set; it must
# ignore the new `_term_index` key gracefully (never raise, never require it).
# --------------------------------------------------------------------------
_RF_CLAIM_1_6_KNOWN_KEYS = {
    "claim_id", "text", "materiality", "claim_type", "status", "confidence",
    "report_locations", "inference_basis", "persistent_references", "sources",
}


def test_1_6_shaped_consumer_parses_1_7_output_without_error(
    tmp_foundry: FoundryPaths,
) -> None:
    rp = build_run(tmp_foundry, "rf_run_ti_compat")
    _plant_term_index_on_clm_001(rp, _SAMPLE_TERM_INDEX)

    data = svc.export_run(tmp_foundry, "rf_run_ti_compat")
    assert data["schema_version"] == "1.8"

    # Simulate a 1.6-shaped consumer: project each claim down to the key set
    # it knows about, ignoring anything unrecognized (the frontend's actual
    # discipline -- optional access, never a required-key assumption).
    for claim in data["claims"]:
        projected = {k: v for k, v in claim.items() if k in _RF_CLAIM_1_6_KNOWN_KEYS}
        # every 1.6-required field the consumer expects is still resolvable
        assert projected["claim_id"] == claim["claim_id"]
        assert projected["sources"] == claim["sources"]
        # the consumer's own view has no knowledge of the new key -- that's
        # fine, it never touches it.
        assert "_term_index" not in projected

    # Round-trip through JSON, as the real over-the-wire/cached-file shape.
    reparsed = json.loads(json.dumps(data))
    indexed = next(c for c in reparsed["claims"] if c["claim_id"] == "clm_001")
    assert indexed["_term_index"] == _SAMPLE_TERM_INDEX


# --------------------------------------------------------------------------
# TASK-2.2 AC (Python-side half): a run.json fixture with `_term_index`
# populated round-trips through the exporter (export_to_file) without a
# dropped field. The TS-type half of this AC (absent field types as
# optional, not required) lives in run-export.ts + the tsc gate.
# --------------------------------------------------------------------------
def test_term_index_round_trips_through_export_to_file(
    tmp_foundry: FoundryPaths,
) -> None:
    rp = build_run(tmp_foundry, "rf_run_ti_roundtrip")
    _plant_term_index_on_clm_001(rp, _SAMPLE_TERM_INDEX)

    out = svc.export_to_file(tmp_foundry, "rf_run_ti_roundtrip")
    written = json.loads(out.read_text(encoding="utf-8"))

    assert written["schema_version"] == "1.8"
    clm = next(c for c in written["claims"] if c["claim_id"] == "clm_001")
    assert clm["_term_index"] == _SAMPLE_TERM_INDEX
