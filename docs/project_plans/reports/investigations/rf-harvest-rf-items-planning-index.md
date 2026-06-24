---
schema_version: 2
doc_type: report
report_category: planning_index
title: "RF Research-Harvest — Implementation Planning Index (research-foundry items)"
status: active
source: agent
created: 2026-06-23
updated: 2026-06-23
feature_slug: rf-harvest-rf-items-planning
description: >
  Triage + planning routing for the research-foundry-owned outcomes surfaced by the
  2026-06-22 completed-runs outcome harvest and the writeback/backlog reconcile handoff.
  Classifies each item as implementation-ready vs design-unresolved, routes it to the
  right-tier artifact (Feature Contract / SPIKE Charter), and records the build sequencing.
related_documents:
  - docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md
  - docs/project_plans/reports/investigations/rf-writeback-and-backlog-reconcile-handoff.md
  - backlog/research_idea_backlog.yaml
tags: [research-foundry, research-harvest, planning-index, feature-contracts, spike-charters]
---

# RF Research-Harvest — Implementation Planning Index

**What this is.** The harvest ([rf-completed-runs-outcomes-harvest](./rf-completed-runs-outcomes-harvest.md))
routed 18 completed-run outcomes into per-project work queues. This index takes the **11
research-foundry-owned items** (the 9 RF-owned harvest outcomes + the 2 seam fixes from the
[writeback/backlog handoff](./rf-writeback-and-backlog-reconcile-handoff.md)), triages each as
*implementation-ready* vs *design-unresolved*, and routes it to a right-sized planning artifact.
Cross-project outcomes (meatywiki, agentic_meta_dev, ccdash, skillmeat) are **out of scope** here —
owned by those projects (see the harvest's per-project rollup).

**Triage method.** Each item was grounded against current RF code (two read-only exploration
passes). The deciding question per item: *does the design have an unresolved fork, or is it a
bounded build on understood surface?* Bounded builds → **Feature Contract** (executable now).
Unresolved design forks → **SPIKE Charter** (resolve first, then contract/PRD). No item was found
"already shipped"; several are partial (the gate, governance, key-profile, telemetry scaffolds all
exist and are extended rather than built fresh).

## Routing table — 11 RF items

| Item | Current state | Decision | Artifact | Tier / pts |
|------|---------------|----------|----------|-----------|
| **Gap 1** — decision_record writeback | scaffolded (schema+template+claim data exist; render stubbed) | build now | [Feature Contract](../../feature_contracts/enhancements/writeback-decision-record.md) | T1 / 4 |
| **Gap 2** — `rf backlog reconcile` | reader exists; no writer; CLI namespace free | build now | [Feature Contract](../../feature_contracts/enhancements/backlog-reconcile-command.md) | T1 / 4 |
| **RIB-042** — deterministic quality_score | telemetry scaffold; score = `"pending"` | build now | [Feature Contract](../../feature_contracts/enhancements/deterministic-quality-score.md) | T1 / 5 |
| **RIB-002** — verifier URL-check + abstain band | mandatory gate exists; URL/abstain/residual-rate missing | build now (enhance gate) | [Feature Contract](../../feature_contracts/enhancements/verifier-url-check-abstain-band.md) | T1 / 6 |
| **RIB-041** — two-leg eval harness | pytest only; no cassette/nightly/scoring | build now (phased) | [Feature Contract](../../feature_contracts/infrastructure/two-leg-eval-harness.md) | T2 / 8 |
| **RIB-053** — intake adapters → citation tuple | adapter framework exists; no OpenAI/Perplexity intake, no tuple schema | build (resolve tuple schema in-contract) | [Feature Contract](../../feature_contracts/features/intake-citation-adapters.md) | T2 / 8 |
| **RIB-017** — writeback default-deny gate | governance rules exist; `target_topology` undefined; no override flow | **SPIKE first** | [SPIKE Charter](../../exploration/writeback-default-deny-gate/writeback-default-deny-gate-charter.md) | SPIKE |
| **RIB-018** — credential process isolation | key-profile framework exists; adapters in-process (spawn re-arch); Mode D | **SPIKE first** | [SPIKE Charter](../../exploration/credential-process-isolation/credential-process-isolation-charter.md) | SPIKE |
| **RIB-003** — contradiction_log v1 | v0 self-declared cautions only; no embedding/scorer/arbiter | **SPIKE first** (new subsystem; med evidence) | [SPIKE Charter](../../exploration/contradiction-log-v1/contradiction-log-v1-charter.md) | SPIKE |
| **RIB-001** — claim segmentation + alignment | 1:1 extraction + locator string; greenfield | **SPIKE first** (heaviest) | [SPIKE Charter](../../exploration/claim-segmentation-source-alignment/claim-segmentation-source-alignment-charter.md) | SPIKE |
| **RIB-025** — citation precision/recall metrics | persistence ~satisfied; metrics greenfield (med evidence) | **SPIKE** net-new metrics only | [SPIKE Charter](../../exploration/citation-precision-recall-metrics/citation-precision-recall-metrics-charter.md) | SPIKE |

**Outcome:** 6 Feature Contracts (executable) + 5 SPIKE Charters (design-resolution). Nothing
discarded as "just an idea" — but three items carry an explicit deal-killer that could downgrade
them to no-go after their SPIKE: **RIB-003** (real-card contradiction recall may be too low —
medium evidence), **RIB-018** (process isolation may not beat in-process scoping for RF's threat
model), and **RIB-001** (Claimify/LongCite may not fit the offline-first cost model). Those
deal-killers are the harvest's "idea vs build" question made falsifiable.

## A note on RIB-025

The research framed RIB-025 as two MVP gaps. Gap (a) — explicit plan/state persistence — is
**already largely satisfied** in current RF (`plan_run()` persists run.yaml / research_brief /
swarm_plan / routing_decision; `telemetry/run_trace.jsonl` traces every stage). Only Gap (b),
FActScore/ALCE citation precision-recall metrics, is net-new and methodology-unresolved, so the
SPIKE scopes that alone.

## Recommended build sequencing

The harvest proposed a verification-core spine + quality/safety rails. With current-state grounding,
the sequence is:

1. **Seam fixes first (stop the bleeding, unblock self-harvest).** Gap 1 (decision_record
   writeback) → Gap 2 (backlog reconcile). Both T1, no dependencies, scaffolding present. Gap 1 is
   highest-leverage: once the deterministic tail emits decision-records, future completed runs
   self-harvest and this manual review becomes a scan.
2. **Quality rails (make output measurable + CI-safe).** RIB-042 (quality_score, T1) → RIB-041
   (eval harness, T2). 042 supplies the metric 041 regression-gates — sequence 042 before/with 041.
   The RIB-025 citation-metrics SPIKE feeds both; run it in parallel to inform 041's scoring leg.
3. **Verifier hardening.** RIB-002 (URL-check + abstain band, T1) — independent; extends the
   existing gate; ship anytime after the seam fixes.
4. **Intake breadth.** RIB-053 (intake adapters + citation tuple, T2) — independent enhancer.
5. **Design SPIKEs (resolve before committing build budget).** RIB-017 (default-deny gate),
   RIB-018 (credential isolation, Mode D — needs human sign-off on any GO), RIB-003
   (contradiction_log), RIB-001 (claim segmentation). Run as timeboxed charters; each concludes to
   go/no-go/conditional. RIB-001 depends on RIB-025's metrics for its value leg.

**Verification-core caveat vs the harvest.** The harvest's "verification core (do first):
RIB-002 → 001 → 003" assumed all three were greenfield builds. Grounding shows RIB-002 is a bounded
*enhancement* (gate already exists) — promotable now — while RIB-001 and RIB-003 are genuinely
SPIKE-gated. So the executable verification work today is RIB-002; 001/003 are design-first.

## Execution pointers

- **Feature Contracts** → run each via `/dev:execute-contract <contract-path>` (single autonomous
  `feature-sprint-executor` sprint), with the mandatory `task-completion-validator` gate.
- **SPIKE Charters** → run each via `/plan:explore --charter=<charter-path>` (or `/plan:spike
  --leg-of=<charter-path>` per leg). On a `go`/`conditional` verdict, author the downstream Feature
  Contract or PRD; the charter auto-imports its feasibility brief into the new artifact.
- **Backlog status** is intentionally **not** mutated: the RIB entries are research-lifecycle
  `completed` (the research is done); implementation lifecycle is tracked by these artifacts +
  IntentTree nodes (see the harvest routing table for per-item node IDs), not by regressing the
  research status.
