---
schema_version: 2
doc_type: spike
title: "Reusable Assertion Ledger — Correction and Retraction Propagation SPIKE"
status: draft
created: 2026-07-12
updated: 2026-07-12
feature_slug: reusable-assertion-ledger
complexity: large
estimated_research_time: "5 working days"
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
research_questions:
  - "Can a correction, invalid extraction, or retraction enumerate every already-materialized dependent object?"
  - "Which invalidation states and reuse gates prevent stale evidence from being silently reused?"
  - "How are caches, indexes, exports, reports, runs, and downstream writebacks reconciled idempotently?"
  - "Where does propagation consume contradiction evidence edges without conflating disagreement with invalidation?"
related_documents:
  - docs/project_plans/reports/investigations/reusable-assertion-ledger-findings.md
  - docs/project_plans/exploration/contradiction-log-v1/contradiction-log-v1-charter.md
output_artifact: docs/project_plans/SPIKEs/reusable-assertion-ledger-retraction-propagation-results.md
downstream_phase_unlocked: "P5 / Phase 6 — Reuse, Refresh, and Impact"
---

# Correction and Retraction Propagation SPIKE Charter

## Decision to make

Prove that invalid evidence can be contained after it has already propagated
through the ledger and derived surfaces. Define the impact-enumeration and
invalidation contract required before automated assertion reuse is enabled.

## Required upstream input

Consume `docs/project_plans/exploration/contradiction-log-v1/contradiction-log-v1-charter.md`
for evidence-edge and valid-time concepts. Contradiction means two assertions
disagree; correction/retraction propagation means an edition or extraction is
invalidated and every dependent use must be found. This SPIKE must keep those
states and workflows distinct.

## Hypothesis

An explicit dependency graph from immutable source edition through passage,
assertion version, canonical-claim edge, inference, report revision, run, export,
derived cache/index, and downstream writeback can enumerate 100% of affected
objects in a bounded fixture set. A monotonic invalidation event plus idempotent
reconciliation can block future reuse immediately while preserving an audit
trail and historical report context.

## Deal-killer

Do not enable automated cross-run reuse unless every affected object in the
fixture graph is enumerated. A single missed report, export, cache/index entry,
or downstream writeback after one remediation cycle is a no-go.

## Timebox

Five working days: one for the fixture graph, two for event and traversal
prototypes, one for failure/replay tests, and one for synthesis.

## Bounded method and fixtures

1. Build at least 12 isolated dependency graphs, four for each initiating event:
   corrected source edition, invalid extraction, and formal source retraction.
2. Across the fixtures, include every target class: source edition, passage,
   assertion version, canonical-claim/evidence edge, inference, report revision,
   run, export, catalog/search row, vector/cache record if present, and one
   mocked downstream writeback receipt.
3. Include branching and shared dependencies: one assertion used by multiple
   reports, one report using multiple assertions, a canonical claim spanning
   editions, and an inference depending on both valid and invalid assertions.
4. Define event IDs, reason codes, effective time, supersession links, actor,
   review state, and scope. Retain original immutable objects; apply lifecycle
   state rather than destructive deletion.
5. Implement an isolated impact traversal that emits the full affected-object
   set and required action per object: block reuse, mark stale, retract,
   regenerate, purge derived cache, or queue downstream reconciliation.
6. Compare traversal output with a hand-authored expected manifest for every
   fixture. Test duplicate delivery, out-of-order delivery, interrupted replay,
   and reconciliation resume for idempotence.
7. Verify stale objects disappear from eligible-reuse and current search/read
   paths while remaining visible in authorized audit/history views. The harness
   must not call real external writeback targets.

## Required result artifact

Write `docs/project_plans/SPIKEs/reusable-assertion-ledger-retraction-propagation-results.md`
with the dependency-edge inventory, event and state-machine proposal, fixture
manifests, expected-versus-observed enumeration, failure/replay results,
reconciliation action matrix, contradiction/invalidation boundary, verdict, and
unresolved adapter obligations.

## Verdict thresholds

### Go

- 100% of expected affected objects are enumerated in all fixture graphs.
- 100% of invalidated assertions are excluded from eligible reuse and current
  derived search/read results after reconciliation.
- Duplicate, out-of-order, interrupted, and resumed processing converges to the
  same state without duplicate downstream actions.
- Historical provenance remains resolvable with explicit invalid/retracted state.

### Conditional

- Enumeration and reuse blocking are 100%, but one non-production downstream
  adapter lacks an automated reconciliation action. Proceed only with that
  adapter default-denied and a named manual queue/implementation gate; or
- Enumeration is 100% but current derived-index purge requires bounded manual
  rebuild. Permit a private pilot only if reuse is blocked synchronously.

### No-go

- Any expected object is missed after one remediation cycle;
- Any invalid assertion remains eligible for automated reuse;
- Replay can produce divergent lifecycle state or duplicate external actions; or
- Invalidation destroys the historical provenance needed to explain past use.

## Risks and controls

| Risk | Control |
|---|---|
| Hidden dependencies are absent from the graph | Inventory every materialized surface and require fixture coverage per class. |
| Event ordering resurrects stale evidence | Use monotonic lifecycle rules, idempotency keys, and out-of-order tests. |
| Cache purge races current reads | Block reuse at the authoritative policy boundary before asynchronous cleanup. |
| Retraction is mistaken for contradiction | Separate event types and consume contradiction edges only as lineage context. |
| External side effects occur during research | Use mocked receipts and default-deny every real writeback connector. |

## Scope boundary

This SPIKE does not build contradiction detection, public correction moderation,
tenant-shared indexes, rights revocation policy, or production connectors.
Public and shared deployment gates remain conditional later work.

## Downstream handoff

A `go` verdict unlocks P5 / Phase 6 Reuse, Refresh, and Impact. A `conditional`
verdict unlocks a private pilot only with the named adapter or index
default-denied. A `no-go` verdict blocks automated reuse regardless of the
historical replay result.
