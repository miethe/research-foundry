---
schema_version: '0.1'
type: research_report
report_id: report_20260713_research_report_for_rf_run_reusable
title: Research report for rf_run_reusable_assertion_ledger_p0_fixture_v1
intent_id: intent_research_20260713_rf_run_reusable_assertion_ledger_p0
evidence_bundle_id: pending
created_at: '2026-07-13T10:43:39-04:00'
status: draft
audience: self
sensitivity: personal
claim_policy: Every material claim maps to claim_ledger.yaml or is labeled inference/speculation.
verification_status: pending
---

## Findings

# Reusable Assertion Ledger Phase 0 deterministic fixture metrics. [claim:clm_001]
This local-only source records the generated metrics and limitations of the frozen Phase 0 fixture. [claim:clm_002]
The fixture safe reuse rate is 36 divided by 144, which equals 25.0 percent. [claim:clm_003]
The fixture provenance rate is 36 divided by 36, which equals 100.0 percent, with zero fixture provenance mismatches. [claim:clm_004]
The fixture baseline and replay values are 144 and 108 model calls, 720 and 576 elapsed fixture seconds, 144 and 108 cost units, and 72 and 54 review fixture minutes. [claim:clm_005]
The fixture rejection counts are 28 changed editions, 24 expired freshness states, 20 extraction-contract mismatches, 18 rights-or-sensitivity denials, and 18 evaluation-not-approved states. [claim:clm_006]
The fixture contains 12 retraction-propagation graphs and 120 expected affected objects, and it enumerates 120 of 120 objects. [claim:clm_007]
The fixture checks complete, duplicate, out-of-order, interrupted, and partial-resume delivery for all 12 invalidating fixture events against an independently authored expected-object manifest. [claim:clm_008]
# Reusable Assertion Ledger Phase 0 deterministic fixture evidence. [claim:clm_009]
This local-only source describes the frozen `reusable-assertion-ledger-phase0-local-only-v1` fixture. [claim:clm_010]
The fixture contains 12 synthetic runs and 120 synthetic source inputs. [claim:clm_011]
The fixture defines 144 run-source processing opportunities, of which 36 are safe reuse opportunities. [claim:clm_012]
The fixture audits all 36 eligible reused assertions and records 36 correct passage-provenance checks. [claim:clm_013]
The fixture identity check compares 240 assertions across three reruns in two input orders, for 1,440 comparisons. [claim:clm_014]
The fixture changes 48 assertion timeframes and validates 48 new identities, 48 predecessor links, and retention of all prior fixture IDs. [claim:clm_015]
The fixture runs `proposed -> reviewed -> active -> split -> superseded -> rolled_back`; source IDs and history persist. [claim:clm_016]

## Inferences

<!-- No analytic inferences were drawn for this run. -->

## Speculation

<!-- No speculation was recorded for this run. -->

## Open questions

- None recorded.

## Sources

- src_20260713_reusable_assertion_ledger_phase_0_fixture_144e728c: Reusable Assertion Ledger Phase 0 Fixture Metrics
- src_20260713_reusable_assertion_ledger_phase_0_fixture_2cc94967: Reusable Assertion Ledger Phase 0 Fixture Evidence
