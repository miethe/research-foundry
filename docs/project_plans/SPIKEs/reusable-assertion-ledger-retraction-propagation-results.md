---
schema_version: 2
doc_type: report
title: "Reusable Assertion Ledger: Retraction Propagation Audit Result"
status: review
created: 2026-07-13
updated: 2026-07-13
feature_slug: reusable-assertion-ledger
report_category: investigation
source: automated
outcome: conditional
metrics: ["120/120 independently authored expected fixture objects matched", "12/12 fixture events converge under complete, duplicate, out-of-order, interrupted, and partial-resume delivery"]
findings: ["The isolated graph contract is complete; real adapter and contradiction-contract evidence is unavailable."]
action_items: ["Default-deny unknown adapters and validate traversal against a production-shaped but local-only graph before reuse enablement."]
promoted_to: ["docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1/phase-1-research-gates.md"]
---

# Correction and Retraction Propagation Audit Result

## Scope and evidence class

The frozen local-only manifest defines 12 isolated dependency graphs: four each
for `corrected_edition`, `invalid_extraction`, and `formal_retraction`. Each
graph has all ten required object classes: source edition, passage, assertion
version, canonical-claim/evidence edge, inference, report revision, run,
export, derived cache/index, and a mocked downstream writeback receipt. The
harness has no real connector or external writeback target.

The contradiction-log charter is still `draft` with no verdict. The test keeps
contradiction as lineage context only; it never turns disagreement into an
invalidation event.

## RF evidence chain and traceability

The same local RF evidence run,
`rf_run_reusable_assertion_ledger_p0_fixture_v1`, has two local source cards, a
16-entry supported claim ledger, a deterministic report with 16 claim tags, and
a passing `verification.yaml` (verify exit 0). These artifacts are checked in
under `tests/fixtures/assertion_ledger/rf_phase0_evidence_snapshot/` and rebuilt
by `tests/fixtures/assertion_ledger/run_phase0_rf_evidence.sh` using local
ingest, extract, claim-map, deterministic synthesis, and verify commands only.
The full command sequence and explicit skips of discovery/fetch/bundle/
writeback/telemetry are recorded in the historical replay result; no `rf replay`
command exists or was used.

Propagation counts map to supported ledger entries: 12 graphs and 120/120
enumeration `clm_007`, and complete/duplicate/out-of-order/interrupted/
partial-resume coverage for 12 events `clm_008`. Lifecycle actions,
authoritative eligibility blocking, current-read exclusion, and idempotent
receipts are deterministic isolated-fixture checks in
`tests/test_reusable_assertion_ledger_phase0.py` against the separately authored
`tests/fixtures/assertion_ledger/phase0_propagation_expected_manifest.json`, not
observations of existing deployment adapters.

## Proposed event and action contract

An immutable lifecycle event carries an event ID, initiating object/version,
monotonic sequence, cause, occurred-at time, and idempotency key. Traversal must
enumerate every dependent object and assign one action: block reuse, mark stale,
retract, regenerate, purge derived cache, or queue default-denied downstream
reconciliation. The authoritative assertion eligibility state changes before
any asynchronous cleanup. Authorized history remains resolvable with an
invalidation state; current eligible reads return no invalidated assertion.

| Target class | Required action |
|---|---|
| Edition, passage, assertion version | Invalidate and synchronously block reuse |
| Canonical edge, inference, report, run, export | Mark stale; retain audit/history reference |
| Cache/index | Exclude from current reads; purge or bounded rebuild |
| Mocked writeback receipt | Queue idempotent reconciliation; default-deny unknown adapter |

## Expected-versus-observed fixture result

| Check | Numerator / denominator | Observed fixture result |
|---|---:|---:|
| Dependency graphs | 12 / 12 | Four per initiating event type |
| Expected object enumeration | 120 / 120 | Independently authored expected-object manifest matched |
| Lifecycle action | 120 / 120 expected objects | Required action asserted for every object class |
| Immediate reuse/current-read exclusion | 12 / 12 invalidating fixture events | Assertion eligibility blocked and current cache/index read excluded before resume |
| Duplicate delivery convergence | 12 / 12 | Same expected state; no duplicate receipt |
| Out-of-order delivery convergence | 12 / 12 | Same expected state |
| Interrupted/partial-resume convergence | 12 / 12 | First half persists, second half resumes to the same expected state |

The 120-object result is a graph-fixture assertion. It is not proof that every
existing report, export, cache, or writeback adapter in a private deployment is
enumerated.

## Verdict: conditional — automated reuse remains blocked

The fixture meets the charter's complete-enumeration and idempotence arithmetic,
but it has not consumed a concluded contradiction contract or exercised real
private materializations/adapters. The verdict is **conditional**. It supports
the P5 event/state-machine contract only with synchronous default-deny reuse
blocking and no real automated writeback.

Any missed expected object, invalid assertion eligible for reuse, divergent
replay state, or duplicate downstream action is a no-go for automated reuse.

## Inputs and restrictions for P1–P5

- **P1:** model lifecycle event, monotonic sequence/idempotency key, invalidation
  cause, and dependency-edge type separately from contradiction evidence.
- **P2–P4:** persist enough source/assertion/report/export lineage to enumerate
  impact; current projections must honor authoritative invalidation.
- **P5:** require synchronous `RF_ASSERTION_REUSE_ENABLED=false` on unknown,
  stale, or invalid state; adapters default-denied and reconcile via a manual
  queue until local adapter fixtures and review pass.
- **Fallback:** a bounded derived-index rebuild is allowed only while reuse is
  already blocked; do not enable any external writeback automation.

## Unresolved risks

The graph is synthetic, all receipts are mocked, current adapters have not been
inventoried, and private source/report/export graph shape may expose new edges.
The unresolved contradiction contract must be consumed as a dependency, not
reimplemented here.
