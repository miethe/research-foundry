---
schema_version: 2
doc_type: phase_plan
title: "Phase 1 (P0): Research Gates"
status: review
created: 2026-07-12
updated: 2026-07-13
feature_slug: reusable-assertion-ledger
feature_version: v1
phase: 1
phase_id: P0
phase_title: Research Gates
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
entry_criteria:
  - Three reusable-assertion-ledger SPIKE charters exist.
  - Representative private corpus access is approved for read-only replay.
exit_criteria:
  - Replay, identity/merge, and propagation result artifacts have structured verdicts.
  - Existing citation, segmentation, and contradiction dependencies are consumed or explicitly gated.
  - Task-completion-validator and Karen approve continuation or reduced scope.
related_documents:
  - docs/project_plans/SPIKEs/reusable-assertion-ledger-historical-replay-charter.md
  - docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-charter.md
  - docs/project_plans/SPIKEs/reusable-assertion-ledger-retraction-propagation-charter.md
spike_ref: docs/project_plans/SPIKEs/reusable-assertion-ledger-historical-replay-charter.md
integration_owner: backend-architect
ui_touched: false
target_surfaces: []
seam_tasks: [P0-004]
owner: spike-writer
contributors: [backend-architect, data-layer-expert, python-backend-engineer, lead-pm]
priority: high
risk_level: high
files_affected:
  - docs/project_plans/SPIKEs/reusable-assertion-ledger-historical-replay-results.md
  - docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-results.md
  - docs/project_plans/SPIKEs/reusable-assertion-ledger-retraction-propagation-results.md
---

# Phase 1 (P0): Research Gates

**Effort:** 8 points
**Dependencies:** Existing citation precision/recall, segmentation/alignment, and contradiction-log charters.

## Outcome

Resolve the H3 uncertainties before persistent contracts are frozen. The phase may conclude with `go`, bounded `conditional`, or `no-go`; implementation cannot reinterpret a failed gate as approval.

## Task breakdown

| Task ID | Task | Deliverable and acceptance | Estimate | Assigned subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| P0-001 | Historical replay | Run 100–300 sources over 10–20 runs; publish reuse, provenance, quality, time, cost, and reviewer-effort metrics with exact denominators. | 3 pts | spike-writer, python-backend-engineer | sonnet | extended | None |
| P0-002 | Identity and merge audit | Prove deterministic edition/passage/assertion identity; audit qualifier-aware candidates; publish assertion-only fallback. | 3 pts | backend-architect, data-layer-expert | sonnet | extended | Citation/segmentation fixture contracts |
| P0-003 | Retraction propagation audit | Prove expected impact enumeration, authoritative reuse blocking, and idempotent replay against the identity fixture and contradiction contract. | 1 pt | backend-architect, data-layer-expert | sonnet | extended | P0-002 identity fixture, contradiction contract |
| P0-004 | Verdict synthesis and phase seam | Reconcile replay, identity/merge, and propagation verdicts into P1 contract inputs, feature-flag decisions, fallback scope, and stop conditions. | 1 pt | lead-pm, backend-architect | sonnet | extended | P0-001, P0-002, P0-003 |

## Detailed acceptance

#### AC P0-GATES: Research outputs constrain implementation
- target_surfaces:
  - `docs/project_plans/SPIKEs/reusable-assertion-ledger-historical-replay-results.md`
  - `docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-results.md`
  - `docs/project_plans/SPIKEs/reusable-assertion-ledger-retraction-propagation-results.md`
- propagation_contract: Each result records fixtures, methods, observed thresholds, verdict, unresolved risks, and explicit inputs or restrictions for P1-P5.
- resilience: Missing or inconclusive upstream extraction contracts select a conditional boundary; merge failure selects assertion-only mode; identity or propagation failure blocks automated reuse.
- visual_evidence_required: false
- verified_by: [P0-004]

## Quality and review gates

- [ ] Replay meets `>=20%` safe reuse and `>=95%` sampled passage provenance for `go`; conditional/no-go bands remain as chartered.
- [ ] Identity fixtures are deterministic and material changes receive lineage-linked identities.
- [ ] Propagation fixtures enumerate 100% of expected dependencies and converge after retries.
- [ ] Canonical claims remain independently gated from durable assertion reuse.
- [ ] `task-completion-validator` issues a phase pass.
- [ ] Karen issues the Tier 3 research-milestone pass.

## Validation

- Validate result frontmatter and fixture manifests.
- Recompute reported denominators from raw result tables.
- Confirm no production store, external writeback, public corpus, or shared index was mutated.

## P0-004 pre-review synthesis

**Result artifacts:**
`reusable-assertion-ledger-historical-replay-results.md`,
`reusable-assertion-ledger-identity-merge-results.md`, and
`reusable-assertion-ledger-retraction-propagation-results.md`.

All three deterministic local-fixture outputs are `conditional`, not an
empirical go. They demonstrate exact measurement, identity, lineage, impact
enumeration, and idempotence contracts without claiming private-corpus results.
Representative private-corpus access is unavailable and the citation,
segmentation/alignment, and contradiction charters remain draft with null
verdicts.

| Downstream boundary | Pre-review restriction |
|---|---|
| P1 canonical contracts | Freeze immutable hash, opaque-ID/version, lineage, eligibility, lifecycle-event, idempotency, and dependency-edge fields. Preserve source assertion/canonical claim/inference distinction. |
| P2–P4 registry/materialization/catalog | Support assertion-only records and auditable predecessor lineage; retain rejection and provenance fields. Do not expose merge-derived grouping or replay savings claims. |
| P5 reuse/impact | `RF_ASSERTION_REUSE_ENABLED=false` for unknown, stale, invalid, or unreviewed evidence; synchronous blocking precedes cleanup; unknown adapters default-denied/manual queue. |
| Canonical claims | `RF_CANONICAL_CLAIMS_ENABLED=false`; no automatic canonical merge until two-reviewer narrow-domain audit clears the charter threshold. |
| Ledger writes | `RF_ASSERTION_LEDGER_ENABLED` may not be enabled beyond a local development fixture until P1 contracts and independent review pass. |

**Fallback and stop conditions:** assertion-only, provenance-preserving storage
is the only allowable scope after review. Any nondeterministic identity, missing
lineage, missed dependency, stale eligible reuse, divergent replay, duplicate
downstream action, or failed independent reviewer gate blocks automated reuse.

**Reviewer gate:** `task-completion-validator` and Karen are pending. The
canonical tracker is `.Codex/progress/reusable-assertion-ledger/phase-1-progress.md`
(`phase: 1`, task namespace `P0-*`); this phase is pre-review, not complete.

## Local RF evidence boundary

The P0 fixture evidence is reproducibly ingested through the local RF pipeline:
two checked-in fixture sources produce two source cards, 16 supported ledger
claims, a deterministic 16-tag report, and a passing `rf verify` result. The
exact successful artifacts are committed under
`tests/fixtures/assertion_ledger/rf_phase0_evidence_snapshot/`; the ignored
`rf_run_reusable_assertion_ledger_p0_fixture_v1` path is only the local rebuild
location. This is evidence of traceability for the constructed fixture values
only; it is not an RF replay or private-corpus measurement. No `rf replay`
command exists. Discovery, fetch, bundle, publication, writeback, and telemetry
remain skipped by scope.

### Exact RF command record

```text
./.venv/bin/rf guard check --profile default                         # exit 0
mkdir -p runs/rf_run_reusable_assertion_ledger_p0_fixture_v1
./.venv/bin/rf ingest tests/fixtures/assertion_ledger/phase0_rf_evidence_source.md --run rf_run_reusable_assertion_ledger_p0_fixture_v1 --source-type personal_note --sensitivity personal --no-fetch  # exit 0
./.venv/bin/rf ingest tests/fixtures/assertion_ledger/phase0_rf_metrics_source.md --run rf_run_reusable_assertion_ledger_p0_fixture_v1 --source-type personal_note --sensitivity personal --no-fetch  # exit 0
./.venv/bin/python tests/fixtures/assertion_ledger/enrich_phase0_rf_source_cards.py runs/rf_run_reusable_assertion_ledger_p0_fixture_v1/sources  # exit 0; local deterministic limitations enrichment before extraction
./.venv/bin/rf extract rf_run_reusable_assertion_ledger_p0_fixture_v1 --model-profile rf_extract_cheap  # exit 0; 2 cards
./.venv/bin/rf claim-map rf_run_reusable_assertion_ledger_p0_fixture_v1  # exit 0; 16 supported claims
./.venv/bin/rf synthesize rf_run_reusable_assertion_ledger_p0_fixture_v1 --deterministic  # exit 0; 16 claim tags
./.venv/bin/rf verify rf_run_reusable_assertion_ledger_p0_fixture_v1 --fail-on-unsupported  # exit 0; all error checks pass
```

The first attempt stopped at ingest because `--source-type fixture` violates
the source-card schema; it was corrected to `personal_note` before any extract,
claim-map, or verify command ran. No `rf verify` invocation has exited nonzero.

### Claim traceability map

The committed claim ledger is at
`tests/fixtures/assertion_ledger/rf_phase0_evidence_snapshot/claims/claim_ledger.yaml`;
its source cards, deterministic report, and verification record are in the
matching `sources/`, `reports/`, and `reviews/` directories.

| P0 quantitative evidence | Supported ledger claims |
|---|---|
| 12 runs, 120 inputs, 144 opportunities, 36 safe reuse, 36/36 provenance | `clm_011`–`clm_013` |
| 25.0% reuse, 100.0% provenance, zero fixture mismatch, baseline/replay units, rejection counts | `clm_003`–`clm_006` |
| 1,440 deterministic identity comparisons, 48 identity/predecessor links, lifecycle state-machine path | `clm_014`–`clm_016` |
| 108 candidates / 48 hard negatives | Fixture construction metadata only; no reviewer-label or merge-safety result |
| 12 propagation graphs, 120/120 enumeration, 12 delivery scenarios | `clm_007`–`clm_008`; lifecycle/eligibility/current-read/idempotence checks: fixture test plus independently authored expected manifest |

Rates, deltas, and collision observations are explicitly labeled inference from
deterministic fixture evidence in the result artifacts. Quality regression is
explicitly unmeasured. Lifecycle behavior is a bounded fixture assertion, not a
private-corpus, reviewer-study, or deployment-adapter claim.

[Return to parent plan](../reusable-assertion-ledger-v1.md)
