---
schema_name: ccdash_document
schema_version: 2
doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans
id: BRIEF-reusable-assertion-ledger
title: "Reusable Assertion Ledger — Human Brief"
status: draft
category: human-briefs
feature_slug: reusable-assertion-ledger
feature_family: reusable-assertion-ledger
feature_version: v1
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
intent_ref: null
epic_ref: null
related_documents:
  - docs/project_plans/reports/investigations/reusable-assertion-ledger-findings.md
  - docs/project_plans/SPIKEs/reusable-assertion-ledger-historical-replay-charter.md
  - docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-charter.md
  - docs/project_plans/SPIKEs/reusable-assertion-ledger-retraction-propagation-charter.md
owner: nick
contributors: []
audience: [humans]
priority: high
confidence: 0.82
created: 2026-07-12
updated: 2026-07-14
target_release: null
tags: [human-brief, tier-3, assertions, provenance, private-first]
---

# Reusable Assertion Ledger — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-14

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md`
- **Findings**: `docs/project_plans/reports/investigations/reusable-assertion-ledger-findings.md`
- **SPIKEs**: historical replay/economics, identity/semantic merge, and correction/retraction propagation charters under `docs/project_plans/SPIKEs/reusable-assertion-ledger-*-charter.md`
- **Design specs**: Shared-index isolation and public-rights promotion specs are deferred P8 deliverables; they do not exist yet.
- **Related briefs**: None.

## 2. Estimation Sanity Check

**Bottom-up total**: 72 points across P0–P8, including 12 embedded H6 points; the 12 points are not additive.
**Top-down anchor**: The findings estimate 4–7 engineer-weeks for a private pilot and 3–6 engineer-months for a durable private beta. No directly comparable completed feature provides a stronger H5 anchor.
**Reconciliation**: The 72-point plan covers the durable private-beta slice, not only a proof of concept. Confidence is 0.82 because phase scope and gates are explicit, while replay economics, identity safety, and propagation feasibility remain SPIKE-dependent.

H1–H6 heuristic application:

- **H1 (new durable nouns)**: Immutable editions, passages, assertions, evaluations, lifecycle/audit records, relationships, and workspace-scoped projections justify the P1–P4 schema/repository/service floor.
- **H2 (dual implementation)**: No local-plus-enterprise duplicate implementation is planned. The v1 boundary is one private, workspace-scoped architecture, so no 1.8× multiplier applies.
- **H3 (algorithmic services)**: Identity/versioning, qualifier-aware merge proposals, dependency traversal, reuse decisions, ranking, and invalidation are algorithmic. P0 therefore runs three blocking SPIKEs; merge failure selects assertion-only mode.
- **H4 (bundle versus sum)**: Nine phase estimates sum to the locked 72 points across research, schemas, registry, materialization, API/search, lifecycle, UI, hardening, and rollout. The plan total does not discount any capability-area subtotal.
- **H5 (anchor)**: The findings' private pilot/private beta ranges are the best available anchor. Actual replay time, review effort, and storage/index behavior must recalibrate the plan after P0.
- **H6 (hidden plumbing)**: 12 points are embedded in P1-003 (2), P3-003 (2), P4-003 (2), P6-000 (1), P6-001 (1), P8-001 (2), P8-002 (1), and DOC-006 (1) for compatibility, DTO/codegen, export seams, the impact read seam, flags, migration/rollback, telemetry, docs, and deferred-spec capture.

## 3. Wave & Orchestration Notes

**Critical path**: `P0 -> P1 -> P2 -> P3 -> P4 -> P5 -> P6 -> P7 -> P8`. P0 can stop or narrow the feature; deterministic identity, complete impact enumeration, and isolation are hard blockers for automated reuse.

**Parallel opportunities**: Historical replay and identity/merge can run in parallel. Retraction propagation consumes the identity fixture contract, and verdict synthesis follows all three SPIKE results. Evaluation fixture authoring may overlap P2–P5, but P6 is serialized after P5: P6-000 consumes P5-002/P5-003, and every remaining P6 task depends directly or indirectly on P6-000.

**Merge order**: Land approved P0 result artifacts before contract work; then schemas/ADR (P1), registry (P2), materialization/export lineage (P3), API/OpenAPI and generated types (P4), lifecycle/impact work (P5), the P6-000 impact read seam followed by the remaining reviewer experience (P6), integrated hardening (P7), and docs/private-rollout artifacts (P8). Only one writer owns a file at a time. P7 must test the serialized P5-to-P6 result before P8.

**Cross-feature coupling**: Compose with existing source-card, claim-ledger, export, catalog, WKSP-304 isolation, writeback-default-deny, and runs-viewer contracts. Do not replace these seams or create parallel governance mechanisms.

**Review cadence**: `task-completion-validator` closes every phase. Karen reviews P0, P4, P7, and final closeout. A failed reviewer gate prevents phase completion.

## 4. Open Questions Ledger

| ID | Source | Question | Status | Resolved By |
|---|---|---|---|---|
| OQ-REUSE-001 | PRD §13 | Which recurring corpus avoids upward reuse bias? | open | Historical replay SPIKE |
| OQ-REUSE-002 | PRD §13 | Which reuse dimension governs release while all dimensions remain reported? | open | Historical replay SPIKE |
| OQ-ID-001 | PRD §13 | Which fields define assertion identity versus version lineage? | open | Identity/merge SPIKE |
| OQ-ID-002 | PRD §13 | What minimum qualifier vocabulary preserves unknown domain qualifiers? | open | Identity/merge SPIKE |
| OQ-MERGE-001 | PRD §13 | Does canonical grouping clear ≥80% acceptance and <2% harmful false merges? | open; default off | Identity/merge SPIKE |
| OQ-RET-001 | PRD §13 | Which writebacks accept automated correction and which require a manual queue? | open | Retraction SPIKE |
| OQ-RET-002 | PRD §13 | What non-leaking tombstone survives rights-driven deletion? | open | Retraction SPIKE + security review |
| OQ-STORE-001 | PRD §13 | Which durable boundary balances portability, transactions, and scale? | open | P1 architecture gate |
| OQ-PERF-001 | PRD §13 | What p95 lookup, ingestion, and rebuild targets does the pilot support? | open | Replay SPIKE + P7 |
| OQ-PUBLIC-001 | PRD §13 | What rights-cleared corpus and promotion policy could support a public pilot? | deferred | Future public-rights gate |
| OQ-SHARED-001 | PRD §13 | Can a shared index prove zero cross-workspace leakage economically? | deferred | Future isolation gate |
| OQ-INTERCHANGE-001 | PRD §13 | Should public assertions use signed nanopublications or RO-Crate? | deferred | Future public-promotion decision |

## 5. Deferred Items Rationale

- **Shared lexical/vector/graph indexes**: Prohibited in v1 because counts, candidates, caches, facets, and graph traversal can leak corpus membership across workspaces. Promote only after private value is proven and an adversarial isolation gate shows zero unauthorized disclosure at acceptable operating cost.
- **Public corpus rights and promotion**: Prohibited in v1 because lawful reuse, license/retention state, moderation, revocation, poisoning response, and correction operations are a separate product boundary. Promote only with a rights-cleared corpus, explicit allowed-use policy, auditable withdrawal, and proven private economics.
- **Public interchange**: Nanopublication/RO-Crate export stays bundled with public promotion; internal schemas should remain mappable but need not ship a public contract.
- **Canonical claims after a failed merge gate**: Keep `RF_CANONICAL_CLAIMS_ENABLED` off and ship the useful assertion-only ledger. Reopen with domain-specific fixtures rather than weakening the threshold.

## 6. Risk Narrative

- **Semantic laundering**: The greatest product risk is presenting normalized or inferred content as something a source asserted. Preserve distinct source-assertion, canonical-claim, and inference types in schemas, API, exports, and UI labels.
- **Qualifier loss and false merges**: Population, modality, timeframe, geography, and method can reverse meaning. Candidate-only, reversible grouping and assertion-only fallback are non-negotiable.
- **Derived-signal leakage**: A denied passage is still leaked if its existence appears in counts, suggestions, ranking, caches, or impact graphs. Authorization must run before every retrieval and derived signal.
- **Stale evidence reuse**: Retraction eligibility must change synchronously before asynchronous cleanup. Any incomplete traversal or unknown adapter remains denied and resumable.
- **Legacy regression**: Persistent IDs are additive. Existing run-local claim IDs, report anchors, redactions, exports, and viewer behavior must work when ledger fields are absent.
- **Economics inversion**: Review, refresh, OCR, and index maintenance could cost more than re-extraction. P0 and private-beta telemetry must report denominators and human effort, not only cache-hit rate.
- **Premature rollout**: Implementation authority does not imply public, shared-index, external-writeback, or production deployment authority. P8 is private, reversible, and separately authorized.

## 7. What to Watch For

- SPIKE results that report favorable percentages without exact corpus, denominator, and reviewer-time evidence.
- Identity normalization that makes changed passages look unchanged or exposes content hashes as public identifiers.
- Canonical-claim work creeping onto the critical path despite the assertion-only fallback.
- API, OpenAPI, generated TypeScript, and UI state changes landing out of order.
- Search/facet/cache implementations that scope returned rows but not precomputed aggregates or suggestions.
- Invalidation tests that cover the ledger but omit exports, reports, runs, caches, indexes, or queued writebacks.
- Phase estimates being silently reduced after P0 rather than explicitly recalibrated with observed evidence.
- P8 producing shared/public behavior instead of only the two deferred design specifications.

## 8. Expected Success Behaviors

- [ ] A reviewer can open a reused assertion and see its exact immutable edition, passage, qualifiers, evaluation state, freshness, rights decision, and prior report/run uses.
- [ ] Source assertions, canonical claims, and inferences remain visibly distinct in catalog, provenance, audit, export, and legacy/missing-field states.
- [ ] Unchanged evidence resolves to the same durable identity; materially changed evidence receives new identity plus predecessor lineage.
- [ ] A retraction immediately blocks reuse, enumerates every affected fixture object, converges after retry, and keeps authorized historical provenance readable.
- [ ] Unauthorized workspaces receive no content, identifiers, counts, candidates, cache hits, suggestions, or membership clues.
- [ ] Legacy runs without persistent ledger fields continue to render and export without inferred values.
- [ ] Operators can disable ledger writes, automated reuse, and canonical claims independently and complete migration/rollback rehearsals from documented receipts.
- [ ] Private-beta telemetry shows whether saved processing and evidence-preparation effort exceed extraction, refresh, review, and maintenance cost.
- [ ] No public corpus, shared index, or external writeback is enabled by the v1 closeout.

## 9. Running Log

- [2026-07-12] Brief created from the accepted findings report, draft Tier 3 PRD/plan, nine phase plans, and three blocking SPIKE charters; confidence set to 0.82 pending P0 verdicts.
- [2026-07-14] P6 reviewer experience gained the P6-000 impact read seam (1 embedded H6 point). Current estimate locked at 72 points with 12 embedded H6 points; P6 is serialized after P5-002/P5-003, with every remaining P6 task ordered behind P6-000 directly or transitively.
