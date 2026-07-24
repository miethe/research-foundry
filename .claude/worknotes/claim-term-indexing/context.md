---
type: context
doc_type: context
prd: claim-term-indexing
title: Claim Term Indexing - Development Context
status: active
created: '2026-07-24'
updated: '2026-07-24'
prd_ref: docs/project_plans/PRDs/features/claim-term-indexing-v1.md
plan_ref: docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md
critical_notes_count: 0
implementation_decisions_count: 0
active_gotchas_count: 0
agent_contributors: []
agents: []
---

# claim-term-indexing - Development Context

**Status**: Active Development
**Created**: 2026-07-24
**Last Updated**: 2026-07-24

> **Purpose**: Shared worknotes for all agents working on the claim-term-indexing feature. Add brief observations, decisions, gotchas, and implementation notes that future agents should know.

---

## Feature Summary

`_term_index` is a namespaced, additive, non-authoritative field computed once at `claim-map` write time (Phase 1) and copied forward read-only through `export`, `catalog`, `search`, and `serve` (Phase 2) — never recomputed, never model-derived, never touching identity hashing or verification. Phase 1's guard tests (fingerprint regression + verify byte-inertness) are an entry-blocking exit gate for every downstream phase. Phase 3 (backfill of 7 verified pediatric-CDS bundles) and Phase 4 (runs-viewer facets/badges) fork off Phase 2 in parallel on disjoint file sets, then join at Phase 5 (docs + deferred-item design specs + karen gate).

**Tier**: 2 | **Effort**: 12 pts | **Phases**: 5 (P1 → P2 → [P3 ∥ P4] → P5)

---

## Links

- **PRD**: `docs/project_plans/PRDs/features/claim-term-indexing-v1.md`
- **Implementation Plan**: `docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md`
- **Decisions Block**: `.claude/worknotes/claim-term-indexing/decisions-block.md`
- **Design Spec**: `docs/project_plans/design-specs/claim-term-indexing.md`
- **Charter / Feasibility Brief**: `docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-charter.md`, `docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-feasibility-brief.md`
- **ADR**: `docs/dev/architecture/adr-rights-entity-model.md`
- **Progress files**: `.claude/progress/claim-term-indexing/phase-{1..5}-progress.md`

---

## Key Invariants

- **Namespaced, non-authoritative `_term_index`** — always under the single key `_term_index: {terms, usage_roles, vocabulary_version}`; never a bare `usage_role` field anywhere in output (D2). Stays outside `SOURCE_ASSERTION_MATERIAL_FIELDS`, all verification/identity/rights paths, and audit-safety next to real `pediatric_cds` threshold blocks.
- **Deterministic write-time only** — computed once in `claim_mapping.build_claim_ledger`; never recomputed downstream; never a model/embedding call anywhere (D6). Export/catalog/search/serve/runs-viewer are read-only copy-forward consumers.
- **Guard tests entry-block Phase 2** — TASK-1.6's fingerprint-byte-inertness regression and the `rf verify` before/after fixture suite (>=2 runs, 0 status flips) must be green before any P2 task starts. This is the single hardest blocking dependency in the whole plan.
- **Per-row `sensitivity_rank` on `catalog_terms`** — each row carries the sensitivity rank of the claim/evidence point it derives from (D3); read-time filter is `rank <= threshold`. Never a single flat blob computed once at max-permissive tier — that repeats the `search_text` leak precedent (`catalog_service.py:541-563`).
- **v1 scope is claims-only, open schemas only** (D1) — `claim_ledger.yaml` + `report_frontmatter` rollup; strict families (`canonical_claim`, `inference_record`, `source_assertion`) are explicitly out of scope, deferred to DOC-D2/v2.
- **Fail-closed vocab loading** (OQ-D) — malformed `vocab/*.yaml` raises and blocks claim-map; a missing vocab file warns and skips indexing (claims still produced without `_term_index`).
- **P3/P4 parallel fork** — disjoint file ownership confirmed at plan authoring time (no shared file in either phase's `files_affected`); both depend only on P2's frozen contract (schema 1.7 + `catalog_terms` + search/serve params).
- **Real tsc gate** — `cd frontend/runs-viewer && npx tsc -p tsconfig.app.json --noEmit`; plain `npx tsc --noEmit` is a known no-op in this repo (see [[rf-test-suite-gotchas]] memory).

---

## Running Notes

<!-- Agents: append dated entries below using the format-specification.md structure (Implementation Decisions / Gotchas & Observations / Integration Notes / Agent Handoff Notes). This section starts empty. -->
