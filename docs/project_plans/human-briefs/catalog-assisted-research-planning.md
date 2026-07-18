---
schema_name: ccdash_document
schema_version: 2
doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans
id: BRIEF-catalog-assisted-research-planning
title: "Catalog-Assisted Research Planning — Human Brief"
status: draft
category: human-briefs
feature_slug: catalog-assisted-research-planning
feature_family: catalog-assisted-research-planning
feature_version: v1
prd_ref: docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
intent_ref: null
epic_ref: null
related_documents:
  - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
  - .codex/plans/research-interchange-provenance-access-initiative-v1.md
  - .codex/worknotes/catalog-assisted-research-planning/decisions-block.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
  - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
owner: nick
contributors: []
audience: [humans]
priority: high
confidence: 0.68
created: 2026-07-18
updated: 2026-07-18
target_release: null
tags: [human-brief, catalog, retrieval-first, residual-discovery, assertions]
---

# Catalog-Assisted Research Planning — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-18

---

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md`
- **Decisions Block**: `.codex/worknotes/catalog-assisted-research-planning/decisions-block.md`
- **RPC dependency**: `docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md`
- **RAL**: `docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md`
- **Activation**: `docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md`
- **RFUP**: `docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md`
- **SPIKEs**: None before planning; the H3 algorithm has an explicit conservative fixture matrix. Escalate to a SPIKE if Phase 1 cannot freeze the scenarios.

---

## 2. Estimation Sanity Check

**Bottom-up total**: 28 pts
**Top-down intuition**: 21–28 pts for a six-phase integration over shipped catalog/reuse/search/planning seams
**Locked estimate**: 28 pts; no bundle discount.

### H1 — Noun Count

No new CRUD-with-RBAC database noun is introduced. `research_evidence_plan` is a file-canonical run artifact with one producer and governed readers, not a user-managed CRUD entity. Its schema, writer, propagation, and tests are priced directly in P1/P3/P4/P5.

### H2 — Dual-Implementation Multiplier

Not applicable. The feature uses one file-backed planning path and the existing assertion catalog projection. API/MCP/CLI are transport adapters over the same services, not divergent authoritative repositories.

### H3 — Algorithmic Service Flag

The evidence planner and residual router are algorithmic (`ranking`, `resolution`, `dependency`, `scheduling` semantics):

- **P3 Evidence Planner (6 pts)** covers exact eligible hit, no hit, refresh, deny, stale, conflicting packet, missing qualifier, required source-type mismatch, multiple equivalent hits, pagination boundary, duplicate candidate, and catalog-generation change.
- **P4 Retrieval/Discovery Integration (5 pts)** covers zero-network catalog-only, fully covered plan, fully residual plan, mixed plan, empty catalog with explicit fallback, disabled retrieval, budget exhaustion, provider failure, and replay.

P3 exceeds the 3-point H3 floor and enumerates twelve cases. If P1 cannot express deterministic expected outcomes for those cases, stop and create a SPIKE rather than implementing a model-based guess.

### H4 — Bundle vs Sum

| Capability Area | Independent Estimate | Notes |
|---|---:|---|
| Contracts/auth/policy | 4 pts | RPC dependency, identity, enums, limits, compatibility |
| Governed catalog adapter | 5 pts | Bounded packet/reuse decisions + privacy matrix |
| Evidence coverage/residual planner | 6 pts | H3 algorithm and deterministic persistence |
| Planning/Search Router integration | 5 pts | `cache_first`, residual requests, legacy mode |
| API/MCP/export/metrics | 4 pts | Identity and contract breadth; one OpenAPI generation |
| Plumbing, hardening, docs | 4 pts | 16.7% of 24-point implementation subtotal |
| **Sum** | **28 pts** | Locked total |

### H5 — Anchor Reference

Direct completed analogs are RAL's assertion catalog/API and reuse/impact phases
plus assertion-ledger activation's P4 run-launch reuse reachability. The Search
Router and `planning.plan_run()` are also live, tested seams. Plans provide
comparable point estimates and commits demonstrate landed code, but the
inspected repository has no authoritative actual-point ledger. H5 is therefore
medium-confidence surface comparison, not an actual-velocity assertion.

This package is larger than the explicit reuse-launch slice because it adds identity threading, bounded catalog retrieval, an H3 coverage planner, evidence-plan persistence, question-level discovery splitting, three transports, metrics, and Tier 3 validation.

### H6 — Hidden Plumbing Budget

P1–P5 total 24 pts. P6 budgets 4 pts (16.7%) for schema/DTO propagation, OpenAPI/types, adversarial integration, legacy snapshots, docs, CHANGELOG, deferred design specs, and reviewer evidence. This is inside the 15–20% guideline.

**Reconciliation**: Reusing the catalog avoids building an index but does not eliminate authorization, selection correctness, residual routing, or cross-transport verification. The 28-point total is the bottom-up sum, not an assumed efficiency discount.

---

## 3. Wave & Orchestration Notes

**Critical path**: RPC P1 envelope → CARP P1 policy/contracts → P2 adapter → P3 planner → P4 planning/router integration → P5 transports → P6 exact candidate.

**Parallel opportunities**: Limited by design. Within P1, schema examples and threat/error review can proceed in separate read-only lanes. Within P2/P6, tests may be prepared beside implementation if ownership does not overlap. Do not parallelize the central `planning.py`/`router.py` writers.

**Merge order**: RPC envelope first. Land each CARP phase after its exact-tree reviewer. Freeze P4 orchestration before starting P5 response schemas; generate OpenAPI/types once. P6 evidence is valid only on the integrated candidate.

**Cross-feature coupling**: RPC supplies the selected-evidence/correlation envelope. If RPC P1 changes after CARP P1 approval, invalidate CARP contract approval and rerun the seam review.

---

## 4. Open Questions Ledger

| ID | Source | Question | Status | Default if unresolved |
|---|---|---|---|---|
| CARP-OQ-1 | PRD/decisions P1 | What proves a question covered? | open | Exact eligible packet + lexical match + required source/qualifier constraints; conflict/uncertainty residual. |
| CARP-OQ-2 | PRD/decisions P1 | Opt-in or default-on in v1? | open | Opt-in; no default-on before owner evaluation. |
| CARP-OQ-3 | PRD/decisions P1 | Can cache-first show refresh-required candidates? | open | Reason only, no candidate identity unless policy review proves safe. |
| CARP-OQ-4 | Decisions block | Question/candidate/page caps? | open | Conservative schema-bounded limits; no unbounded cursor traversal. |
| CARP-OQ-5 | Decisions block | Store packets or refs in plan? | open | Exact refs + receipts; resolve packets at governed read time. |

---

## 5. Deferred Items Rationale

- **Semantic/vector reranking**: RAL excludes vector indexes. Promote after measured lexical misses and an approved private-index threat model.
- **Adaptive/model-generated query decomposition**: Promote only if an approved evaluation set shows deterministic residual questions insufficient and prompt/model lineage is designed.
- **Canonical-claim coverage**: Promote after merge safety and canonical claim activation are qualified.
- **Cross-workspace/public planning**: Requires separate rights/federation architecture and security approval.

P6 authors four design specs and populates `deferred_items_spec_refs` before closeout.

---

## 6. Risk Narrative

- **False coverage is the core product risk**: A hit is not an answer. The safe failure mode is extra discovery, not suppressed discovery.
- **Privacy ordering**: The API router currently notes that launch identity is not threaded into `launch_run()`. Retrieval cannot ship around that TODO by using a default workspace.
- **Zero-network meaning**: `cache_first` has a zero external-query budget today. Preserve that literal contract; empty catalog must not become a hidden web fallback.
- **Projection freshness**: Search may return an eligible projection row that changes before selection. Re-evaluate the exact packet immediately before marking coverage.
- **Evidence claims**: Repository fixtures can count avoided provider calls in those fixtures. They cannot establish cost savings, real reuse rate, or quality uplift.

---

## 7. What to Watch For

- `search_router.modes.py` declares `cache_first` with an empty provider chain; `run_search()` currently only executes provider discovery and therefore needs an explicit catalog branch.
- `AssertionCatalog.search()` summary rows omit assertion text by design; the adapter must fetch governed packets rather than widening summary leakage.
- `run_launch.retrieve_first_reuse_decision()` is policy logic to reuse, not reimplement; selected packets should pass through it or the underlying same decision seam.
- `planning._build_questions()` already creates stable question IDs; reuse them instead of minting a second question identity.
- `LaunchRunRequest` currently accepts a caller-supplied `reuse_assertion`; retrieval-first should remain additive and preserve that explicit path.
- OpenAPI regeneration after response changes invalidates earlier exact-tree approval.

---

## 8. Expected Success Behaviors

- [ ] `cache_first` returns eligible private assertion packets for a fixture query and a provider spy records zero search/extract calls.
- [ ] A denied or missing-identity request returns no candidate IDs, text, facets, counts, or implicit discovery fallback.
- [ ] A mixed intent produces one evidence plan where covered question IDs have exact selected assertion versions and residual IDs alone reach providers.
- [ ] A stale, invalidated, wrong-edition, or wrong-extraction-contract packet never marks a question covered.
- [ ] Disabling retrieval yields the same research questions, provider chain, budget, and legacy output behavior as before the feature.
- [ ] Replaying the same request against the same catalog generation produces the same candidate order, selections, reasons, and evidence-plan bytes.
- [ ] Search/run/launch/export outputs carry the RPC provenance context without duplicate selected-evidence fields.
- [ ] Metrics report observed authorized counts only; denied results reveal no catalog-derived values.
- [ ] Final closeout labels repository readiness separately from private-corpus evaluation, default-on activation, deployment, and release.

---

## 9. Running Log

- [2026-07-18] Draft package created. Estimate locked at 28 pts after H1-H6. H5 remains medium confidence because comparable shipped surfaces have plans/commits but no authoritative actual-point ledger in the inspected tree; no empirical reuse or savings claim is made.
