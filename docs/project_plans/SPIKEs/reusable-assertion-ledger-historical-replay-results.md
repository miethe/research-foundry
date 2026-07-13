---
schema_version: 2
doc_type: report
title: "Reusable Assertion Ledger: Historical Replay Result"
status: review
created: 2026-07-13
updated: 2026-07-13
feature_slug: reusable-assertion-ledger
report_category: investigation
source: automated
outcome: conditional
metrics: ["36/144 safe synthetic reuse opportunities", "36/36 fixture provenance checks"]
findings: ["The local fixture clears the charter's numeric go bands but cannot establish representative-corpus economics."]
action_items: ["Run the frozen method against approved read-only private corpus access before enabling reuse."]
promoted_to: ["docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-1-research-gates.md"]
---

# Historical Replay and Reuse Economics Result

## Scope and evidence class

This is a deterministic, **synthetic/local-only** harness result, not an
empirical private-corpus replay. The frozen manifest is
`tests/fixtures/assertion_ledger/phase0_fixture_manifest.json`; the harness is
`tests/test_reusable_assertion_ledger_phase0.py`. It makes no network call,
does not read a source run, and does not mutate a catalog or connector.

Representative private-corpus access was not available in this checkout.
The citation precision/recall and segmentation/alignment charters are also
`draft` with no verdict. Consequently, fixture numbers below demonstrate only
measurement arithmetic and decision-boundary behavior; they are not a claim of
actual savings, model cost, quality, or reviewer effort.

## RF evidence chain and traceability

The local evidence run is `rf_run_reusable_assertion_ledger_p0_fixture_v1`.
It was rebuilt from two checked-in local-only source fixtures with
`tests/fixtures/assertion_ledger/run_phase0_rf_evidence.sh`; no replay command
exists in the `rf` CLI and none is claimed here. The successful workflow was:

```text
./.venv/bin/rf guard check --profile default                         # exit 0
mkdir -p runs/rf_run_reusable_assertion_ledger_p0_fixture_v1
./.venv/bin/rf ingest <each local fixture> --run <run> --source-type personal_note --sensitivity personal --no-fetch  # exit 0
./.venv/bin/python tests/fixtures/assertion_ledger/enrich_phase0_rf_source_cards.py runs/<run>/sources  # exit 0; local deterministic source-card limitation enrichment
./.venv/bin/rf extract <run> --model-profile rf_extract_cheap        # exit 0; 2 cards
./.venv/bin/rf claim-map <run>                                       # exit 0; 16 supported claims
./.venv/bin/rf synthesize <run> --deterministic                       # exit 0; 16 claim tags
./.venv/bin/rf verify <run> --fail-on-unsupported                     # exit 0; all error checks pass
```

The checked-in evidence snapshot is
`tests/fixtures/assertion_ledger/rf_phase0_evidence_snapshot/`, containing the
two source cards, `claims/claim_ledger.yaml`, `reports/report_draft.md`, and
`reviews/verification.yaml` copied from the successful local run. The source
cards are deterministically enriched before extraction with limitations stating
the synthetic/local-only boundary, unavailable representative private-corpus
economics, and unavailable real-source canonical-merge safety. The ignored
`runs/<run>/` output is only the rebuild location. The snapshot is intentionally
unbundled/unpublished. `rf swarm run`, `rf fetch`, `rf bundle`, `rf writeback`,
and CCDash telemetry were skipped because this phase permits no external
discovery, fetch, publication, writeback, or telemetry.

The counts in the table map to supported RF ledger entries: runs/inputs
`clm_011`; opportunities/safe reuse `clm_012`; provenance audit `clm_013`; the
25.0% rate `clm_003`; 100.0% provenance and zero fixture mismatches `clm_004`;
fixture call/time/cost/review values `clm_005`; and rejection reasons `clm_006`.
Any percentage or avoided-unit statement is an **inference from those supported
fixture values**, not a private-corpus measurement.

## Frozen method and formulas

The manifest fixes 12 synthetic runs and 120 source inputs, yielding 144
run-source processing opportunities. An opportunity is safely reusable only if
the fixture's edition, extraction contract, freshness, rights/sensitivity, and
evaluation state all permit it.

- Safe reuse rate = `safe_reuse / processing_opportunities`.
- Provenance accuracy = `correct fixture passage audits / sampled reused assertions`.
- Avoided calls = `baseline model calls - replay model calls`.
- Net effort values are synthetic units: they are reported only to prove the
  denominator calculation and must be replaced by elapsed wall time, measured
  call cost, and reviewer time in a read-only corpus replay.

## Observed deterministic-fixture output

| Measure | Numerator / denominator | Result |
|---|---:|---:|
| Runs | 12 | 12 |
| Source inputs | 120 | 120 |
| Safe reuse | 36 / 144 processing opportunities | 25.0% |
| Provenance audit | 36 / 36 reused assertions (all eligible assertions; fewer than 60) | 100.0% |
| Baseline to replay model calls | 144 to 108 | 36 avoided (25.0%) |
| Baseline to replay elapsed fixture seconds | 720 to 576 | 144 avoided (20.0%) |
| Baseline to replay cost units | 144 to 108 | 36 avoided (25.0%) |
| Baseline to replay review fixture minutes | 72 to 54 | 18 avoided (25.0%) |

Rejection reasons total exactly 108: changed edition 28, freshness expired 24,
extraction-contract mismatch 20, rights/sensitivity denied 18, and evaluation
not approved 18. The fixture contains zero provenance mismatches. **Quality
regression is not measured**: this fixture has no independently scored
baseline-versus-replay quality evaluation. Those fixture values are not sampled
human-review findings.

## Verdict: conditional — no enablement authority

The local fixture crosses the charter's numerical `go` bands (`>=20%` reuse and
`>=95%` provenance), but it is not representative evidence and the dependent
extraction contracts are unresolved. This result is therefore **conditional**:
it validates a bounded replay protocol only. It does not authorize
`RF_ASSERTION_REUSE_ENABLED` or any savings claim.

### Required next measurement

Before a `go` verdict, execute the same frozen definitions against 10–20
approved read-only historical runs and 100–300 source inputs, publish raw
per-run rows and rejection reasons, audit at least 60 reused assertions (or all
if fewer qualify), and record elapsed time, actual model billing/call counts,
and independently measured reviewer effort. Preserve the workspace boundary and
aggregate/redact any failure detail.

## Inputs and restrictions for P1–P5

- **P1/P2:** may define additive identity and eligibility fields, but may not
  assert a production reuse-rate baseline.
- **P3/P4:** must retain per-decision rejection reasons and passage provenance
  fields; no replay-derived performance claim may ship.
- **P5:** keep `RF_ASSERTION_REUSE_ENABLED=false` until representative replay,
  citation/segmentation contracts, and lifecycle gates pass.
- **Fallback:** continue with provenance-preserving ingestion and assertion-only
  storage; re-extract whenever a reuse predicate is unknown or denied.

## Unresolved risks

The synthetic recurrence mix may not resemble private workloads; human review
time can erase apparent savings; unresolved citation/segmentation contracts may
change eligible passage boundaries; and rights/freshness policy requires a real
workspace-scoped source of truth. These remain explicit pre-review risks.
