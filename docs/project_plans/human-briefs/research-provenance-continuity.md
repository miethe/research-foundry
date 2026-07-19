---
schema_name: ccdash_document
schema_version: 2
doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans
id: BRIEF-research-provenance-continuity
title: "Research Provenance Continuity — Human Brief"
status: draft
category: human-briefs
feature_slug: research-provenance-continuity
feature_family: research-provenance-continuity
feature_version: v1
prd_ref: docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
intent_ref: null
epic_ref: null
related_documents:
  - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
  - .codex/plans/research-interchange-provenance-access-initiative-v1.md
  - .codex/worknotes/research-provenance-continuity/decisions-block.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
  - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/project_plans/human-briefs/catalog-assisted-research-planning.md
owner: nick
contributors: []
audience: [humans]
priority: high
confidence: 0.72
created: 2026-07-18
updated: 2026-07-18
target_release: null
tags: [human-brief, provenance, assertion-ledger, report-lineage, inference]
---

# Research Provenance Continuity — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-18

---

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md`
- **Decisions Block**: `.codex/worknotes/research-provenance-continuity/decisions-block.md`
- **RAL**: `docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md`
- **Activation**: `docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md`
- **RFUP**: `docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md`
- **Coupled Feature**: `docs/project_plans/human-briefs/catalog-assisted-research-planning.md`
- **SPIKEs**: None required before planning; inference identity/lifecycle tests are enumerated and use shipped seams.

---

## 2. Estimation Sanity Check

**Bottom-up total**: 40 pts
**Top-down intuition**: 36–42 pts for a Tier 3 canonical provenance layer spanning seven phases
**Locked estimate**: 40 pts; trust the bottom-up sum.

### H1 — Noun Count

No new CRUD-with-RBAC database noun is introduced. Six file-canonical artifact
kinds are planned or made reachable: `provenance_origin`,
`research_run_envelope`, `search_activity_receipt`, `report_assertion_use`,
runtime-produced `inference_record`, and optional runtime-produced
`canonical_claim`. None receives general CRUD. Their persistence, policy,
rebuild, and tests are priced directly in P1-P6 rather than applying the
database noun floor.

### H2 — Dual-Implementation Multiplier

Not applicable. Research Foundry uses one file-backed implementation for this assertion-ledger path. The derived SQLite general catalog and JSON assertion projection are not two authoritative repository implementations; this plan only extends the assertion projection and existing export/API adapters.

### H3 — Algorithmic Service Flag

Three services qualify:

- **Activity/receipt materialization and discovery (P2, 6 pts)**: deterministically persists planned/search-only activity, preserves exact query/scope/selection receipts, and supports governed list/fetch without requiring a planned run. Fixtures cover planned, search-only, denied, degraded, missing optional AOS refs, tamper, replay, and facet rebuild.
- **Inference and canonical-claim resolution (P4, 6 pts)**: resolves run-local bases to exact source-assertion versions and separately materializes an explicitly requested canonical claim. Fixtures cover exact/empty/unresolved/wrong-version/stale/cross-workspace support, implicit merge, producer omission, partial write, and replay conflict.
- **Lifecycle dependent enumeration (P6, 5 pts)**: computes inference/canonical-claim/report revision actions and exact receipt identities. Fixtures cover no dependents, one/many dependents, unaffected sibling, interruption/resume, truncated/extra/duplicate receipts, and identity mismatch.

All clear H3's 3-point floor and enumerate more than five scenarios. A separate SPIKE is not required because the base impact manifest/receipt algorithm, search artifacts, and inference/canonical-claim schemas already exist; invalidating discoveries become findings and may force replanning.

### H4 — Bundle vs Sum

| Capability Area | Independent Estimate | Notes |
|---|---:|---|
| Canonical contract freeze | 7 pts | Origin, run/activity, receipts, AOS refs, materialization, compatibility, Karen exact-tree gate |
| Origin/run/activity materialization | 6 pts | H3 search-only discovery, scope/selection receipts, facet rebuild |
| Report-use materialization | 5 pts | Canonical writer + verification hook + adversarial matrix |
| Inference/canonical-claim materialization | 6 pts | H3 typed resolution + atomic references |
| Projection/API/export | 5 pts | Activity discovery plus governed lineage reads |
| Lifecycle continuity | 5 pts | H3 manifest/receipt integration |
| Plumbing, hardening, docs | 6 pts | 17.6% of 34-point implementation subtotal |
| **Sum** | **40 pts** | Locked floor and total |

### H5 — Anchor Reference

Closest completed code surfaces are the RAL physical Phase 4 assertion
materializer, Phase 5 assertion catalog/API, Phase 6 impact reconciler, and the
assertion-ledger activation forward/reuse phases. Git history confirms those
capabilities landed, and their plans provide phase estimates, but the inspected
tree does not contain an authoritative actual-point ledger. The 40-point
estimate therefore uses their planned surfaces and shipped implementation shape
as medium-confidence anchors, not as claimed measured velocity.

The delta over any one RAL phase is intentional: this package combines six canonical artifact kinds, search-only discoverability, three algorithmic services, optional AOS references, generated contracts, and multiple Tier 3 exact-tree gates.

### H6 — Hidden Plumbing Budget

The implementation subtotal before finalization is 34 pts. P7 budgets 6 pts (17.6%) for cross-stage DTO/schema propagation, adversarial matrices, OpenAPI/type generation, compatibility snapshots, test integration, deferred specs, docs, CHANGELOG, and reviewer evidence. This sits inside the recommended 15–20% range.

**Reconciliation**: No estimate compression is claimed from reusing RAL. Reuse reduces architecture uncertainty but does not remove the adversarial tests or cross-stage propagation work.

---

## 3. Wave & Orchestration Notes

**Critical path**: P1 exact-tree contract gate → P2/P3/P4 canonical writers → P5/P6 consumers → P7 integrated candidate.

**Parallel opportunities**: P2 origin/activity, P3 report-use, and P4 inference/canonical-claim work can run concurrently after `RPC-1.G` with non-overlapping writer ownership. P5 catalog/API/export and P6 lifecycle work can then run concurrently.

**Merge order**: P1 first, with task-completion-validator and Karen approving the same exact tree. Integrate P2, P3, and P4 separately and rerun reviewers after material conflict resolution. Integrate P5 and P6 next; regenerate OpenAPI/types only after P5 response shapes freeze. P7 owns the final-candidate evidence set.

**Cross-feature coupling**: Catalog-assisted planning, External Research Interchange, Knowledge MCP, and Operator MCP depend on `RPC-1.G`. Adapter exploration may run in parallel, but no competing origin, run/activity, selection, AOS-reference, inference/canonical-claim, or report-use fields may land.

---

## 4. Open Questions Ledger

| ID | Source | Question | Status | Default if unresolved |
|---|---|---|---|---|
| RPC-OQ-1 | PRD/decisions P1 | Report-use identity: report digest, revision ID, or both? | open | Both: digest binds bytes; revision ID supports lineage. |
| RPC-OQ-2 | PRD/decisions P1 | When does canonical publication occur? | open | Prepare during synthesis; publish only after verification passes. |
| RPC-OQ-3 | PRD/decisions P1 | Which legacy fields remain compatibility aliases? | open | Canonical nested envelopes; legacy fields are read aliases only and never authority. |
| RPC-OQ-4 | Decisions block | How does canonical-claim materialization relate to inference? | open | Separate optional typed writer; exact assertion/inference support; never implicit merge. |
| RPC-OQ-5 | Decisions block | Projection repair surface? | open | Extend existing rebuild/service path; no canonical mutation API. |

---

## 5. Deferred Items Rationale

- **Historical report-use reconstruction**: Old artifacts may not contain exact persistent refs. Promote only after deterministic mapping proves no synthetic identity is needed.
- **Report-to-report transclusion**: Needs a component/revision identity model. Promote with a concrete approved use case.
- **Public provenance export**: Requires separate rights promotion and threat model.
- **Graph/vector lineage service**: Bounded lineage already meets v1. Promote only for measured need with a security review.

P7 authors one design spec per deferred item and populates `deferred_items_spec_refs` before closeout.

---

## 6. Risk Narrative

- **Report mutability**: The most important contract decision is binding use to immutable bytes, not merely a report path. Treat any digest-free shortcut as a phase blocker.
- **Search invisibility**: A search-only activity that is not discoverable through governed list/fetch is a contract failure even when its raw artifact exists.
- **Facet authority drift**: Any producer that writes flattened origin/search facets independently of the canonical envelope creates a second authority and blocks the phase.
- **Inference conflation**: Watch for implementation reuse that routes inference claims through `AssertionMaterializer._prepare_one`; that function correctly accepts only `status == supported` and should retain that boundary.
- **Policy ordering**: Scope and rights decisions must happen before record resolution or derived counts. A helpful error that names a hidden ID is still a leak.
- **Lifecycle completeness**: Source assertion blocking is authoritative and must happen even if downstream reconciliation fails. New dependents cannot weaken existing fail-closed ordering.
- **Evidence truth**: Synthetic fixture success is repository readiness, not representative private-corpus qualification or public activation.

---

## 7. What to Watch For

- `assertion_catalog.py` currently sets `report_uses: []` literally; P5 must replace that with a rebuild from canonical records, not a scan of mutable report text.
- `inference_record.schema.yaml` has no runtime writer today; schema validity alone is not reachability.
- Claim-ledger persistent references are updated after source assertion publication; mirror the publish-then-reference atomicity carefully for inference.
- Generated OpenAPI/type updates change the exact tree and invalidate earlier approvals.
- P2/P3/P4 worktrees must not share writer ownership of provenance, synthesis, or materialization files without an explicit integration owner.

---

## 8. Expected Success Behaviors

- [ ] Starting from a verified report revision, an operator can resolve exact assertion/inference versions and their source passage/edition.
- [ ] A search-only activity is discoverable without a planned run and retains exact query, purpose, provider/site/corpus/filter/time scope, and selection outcome.
- [ ] Deleting derived origin/run facets and rebuilding them restores the same authorized values from canonical envelopes.
- [ ] Optional AOS project/intent/knowledge refs round trip as opaque refs; absence does not change behavior.
- [ ] Canonical-claim materialization occurs only through an explicit typed request and exact support refs; no inference is silently merged.
- [ ] A report changed after use publication fails digest/revision verification instead of silently retaining lineage.
- [ ] An inference with one unresolved or cross-workspace basis remains run-local and has no durable inference ID.
- [ ] Deleting the assertion projection and rebuilding it restores the same authorized report-use lineage.
- [ ] Invalidating a source assertion marks its dependent inference/canonical-claim/report revision stale and resumes correctly after an injected interruption.
- [ ] A historical request/run/report without the new context remains readable with no fabricated IDs and no new writes.
- [ ] Denied cross-workspace reads return no assertion/report text, facets, counts, or candidate IDs.
- [ ] Final status distinguishes repository-local review approval from owner/private qualification and release activation.

---

## 9. Running Log

- [2026-07-18] Reviewer expansion added canonical origin/run/activity envelopes, search-only discoverability, exact scope/selection receipts, optional AOS refs, and canonical-claim materialization. Estimate re-derived and locked at 40 pts after H1-H6; H5 remains medium confidence because comparable completed surfaces have plans/commits but no authoritative actual-point ledger in the inspected tree.
