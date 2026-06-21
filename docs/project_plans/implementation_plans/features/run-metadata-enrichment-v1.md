---
schema_version: 2
doc_type: implementation_plan
title: 'Implementation Plan: Run Metadata Enrichment (v1)'
status: completed
created: 2026-06-20
updated: '2026-06-21'
feature_slug: run-metadata-enrichment
feature_version: v1
prd_ref: docs/project_plans/PRDs/features/run-metadata-enrichment-v1.md
plan_ref: null
scope: "Add Linked Projects, Category, and Tags to every run \u2014 derived from the\
  \ research backlog, backfilled onto existing runs, threaded through the export pipeline,\
  \ and surfaced in the viewer with filtering."
effort_estimate: ~16-20 pts
architecture_summary: null
risk_level: medium
changelog_required: true
priority: high
owner: nick
contributors: []
category: product-planning
tags:
- implementation
- planning
- phases
- run-metadata
- enrichment
- runs-viewer
milestone: runs-viewer-v2.2-polish
commit_refs: []
pr_refs: []
files_affected:
- backlog/research_idea_backlog.yaml
- registries/run_index.yaml
- services/planning.py
- src/research_foundry/services/export_service.py
- scripts/backfill_run_metadata.py
- scripts/prebuild-static-data.mjs
- scripts/seed_swarm_runs.sh
- docs/dev/architecture/rf-run-export-schema.json
- docs/dev/architecture/rf-run-export-schema.md
- frontend/runs-viewer/src/types/rf/run-export.ts
- frontend/runs-viewer/src/screens/RunList.tsx
- frontend/runs-viewer/src/components/RunList/RunCard.tsx
- frontend/runs-viewer/src/components/RunList/FilterTabs.tsx
- frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx
- frontend/runs-viewer/src/components/RunDetail/RunDetailModal.tsx
- frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
- frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx
- CHANGELOG.md
deferred_items_spec_refs: []
findings_doc_ref: null
charter_ref: null
changelog_ref: null
test_plan_ref: null
plan_structure: independent
progress_init: auto
related_documents:
- docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md
- docs/project_plans/human-briefs/run-metadata-enrichment.md
- .claude/worknotes/runs-viewer-v2.2-polish/epic-brief.md
- .claude/worknotes/run-metadata-enrichment/decisions-block.md
references:
  user_docs: []
  context:
  - .claude/worknotes/runs-viewer-v2.2-polish/epic-brief.md
  specs:
  - .claude/specs/changelog-spec.md
  related_prds:
  - docs/project_plans/PRDs/features/run-metadata-enrichment-v1.md
wave_plan:
  serialization_barriers:
  - frontend/runs-viewer/src/types/rf/run-export.ts
  - src/research_foundry/services/export_service.py
  - scripts/prebuild-static-data.mjs
  phases:
  - id: P1
    depends_on: []
    isolation: shared
    parallelizable: true
    owner_skills: []
    files_affected:
    - frontend/runs-viewer/src/types/rf/run-export.ts
    - docs/dev/architecture/rf-run-export-schema.json
  - id: P2
    depends_on:
    - P1
    isolation: shared
    parallelizable: false
    files_affected:
    - registries/run_index.yaml
    - scripts/backfill_run_metadata.py
  - id: P3
    depends_on:
    - P1
    isolation: shared
    parallelizable: true
    files_affected:
    - services/planning.py
    - scripts/seed_swarm_runs.sh
  - id: P4
    depends_on:
    - P2
    - P3
    isolation: shared
    parallelizable: false
    files_affected:
    - src/research_foundry/services/export_service.py
    - scripts/prebuild-static-data.mjs
    - frontend/runs-viewer/src/types/rf/run-export.ts
  - id: P5
    depends_on:
    - P4
    isolation: shared
    parallelizable: true
    owner_skills:
    - frontend-design
    files_affected:
    - frontend/runs-viewer/src/screens/RunList.tsx
    - frontend/runs-viewer/src/components/RunList/RunCard.tsx
    - frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx
    - frontend/runs-viewer/src/components/RunDetail/RunDetailModal.tsx
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
    - frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx
  - id: P6
    depends_on:
    - P5
    isolation: shared
    files_affected:
    - frontend/runs-viewer/src/screens/RunList.tsx
    - frontend/runs-viewer/src/components/RunList/FilterTabs.tsx
  - id: P7
    depends_on:
    - P4
    isolation: shared
    parallelizable: true
    files_affected:
    - src/research_foundry/services/export_service.py
    - frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx
    - frontend/runs-viewer/src/types/rf/run-export.ts
  - id: P8
    depends_on:
    - P5
    - P6
    - P7
    isolation: shared
    parallelizable: false
    files_affected:
    - CHANGELOG.md
  waves:
  - - P1
  - - P2
    - P3
  - - P4
  - - P5
    - P7
  - - P6
  - - P8
---

# Implementation Plan: Run Metadata Enrichment (v1)

**Plan ID**: `IMPL-2026-06-20-RUN-METADATA-ENRICHMENT`
**Date**: 2026-06-20
**Author**: implementation-planner (sonnet) — expanded from Opus decisions block
**Human Brief**: `docs/project_plans/human-briefs/run-metadata-enrichment.md`
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/run-metadata-enrichment-v1.md`
- **Epic**: `docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md`
- **Decisions block**: `.claude/worknotes/run-metadata-enrichment/decisions-block.md`

**Complexity**: Large (L) — 8 phases, cross-stack (Python backend + TS export + React FE)
**Total Estimated Effort**: ~16–20 pts
**Target Timeline**: 2–3 weeks (F5 is the long pole in the runs-viewer v2.2-polish epic)

> **Estimation Sanity Check**: See Human Brief §2 at `docs/project_plans/human-briefs/run-metadata-enrichment.md`.
> Bottom-up from decisions block: schema(2) + migration(4.5) + creation(4.5) + export(5) + display(8) +
> filter(4) + enrichment(5) + tests/docs(4) ≈ 37 task-points; normalised to ~16–20 pts feature-level
> accounting for task granularity. Anchor: v2.1 facelift was ~13 pts FE-only; this adds full backend
> data model + migration → justified +30–50%.

---

## Executive Summary

Run Metadata Enrichment gives every RF run a first-class linked-metadata model: **Linked Projects**
(primary), **Category**, and **Tags** — derived from the research backlog where absent, populated at
run creation going forward, threaded through the export pipeline, and surfaced throughout the viewer
with filtering support. A secondary P1 scope surfaces additional high-value run data (cost, model
profiles, source stats, writeback status) as enrichment widgets in the Overview tab.

The feature ships in 8 phases: schema extension and formal export contract (P1) → backlog-derived
backfill of existing runs (P2) → creation-path wiring (P3) → export threading and FE type generation
(P4, serialization barrier) → viewer display across all target surfaces (P5) → portfolio filtering
(P6) → enrichment extras (P7) → tests and docs with karen gate (P8).

**Downstream unblocks**: F5 export data (P4) enables disabled viewer tabs G1 (Swarm), G2 (Policies),
G4 (Library) to consume enriched run exports.

---

## Implementation Strategy

### Architecture Sequence

This feature follows the RF data flow:

1. **Schema / Contract** — run.yaml fields + formal JSON schema + TS codegen decision
2. **Derivation / Backfill** — invert backlog links → idempotent migration script
3. **Creation Path** — plan_run() + rf capture CLI + seed script
4. **Export Threading** — export_service.py + index.json + schema_version bump
5. **Viewer Display** — React components across all target surfaces
6. **Filtering / Faceting** — FilterTabs + RunList filter state
7. **Enrichment Extras** — cost/model/source/writeback widgets in Overview
8. **Tests & Docs** — unit tests, runtime smoke (R-P4), CHANGELOG, README, docs, karen

### Parallel Work Opportunities

- **P2 and P3 run in parallel** after P1 (both need field definitions from P1 but are independent)
- **P5 and P7** can start in parallel after P4 lands (both read from the rebuilt export; they touch
  different output surfaces and different export fields)
- **P5 surfaces** can be split across FE agents once P4 is confirmed (barrier is P4 completion)

### Critical Path

```
P1 (schema) → P2 (backfill) ─┐
                               ├─→ P4 (export barrier) → P5 (display) → P6 (filter) → P8 (tests/docs)
P1 (schema) → P3 (creation) ─┘                         ↑
                                               P7 (enrichment) ──────────────────────────┘
```

P4 is the hard serialization barrier: no FE display work begins until the export is confirmed in
`public/data`. P8 is the final gate (tests, CHANGELOG, karen review).

### Phase Summary

| Phase | Title | Estimate | Target Subagent(s) | Model(s) | Notes |
|-------|-------|----------|--------------------|----------|-------|
| 1 | Schema & Contract | 2 pts | data-layer-expert, python-backend-engineer | sonnet | codegen decision recorded |
| 2 | Derivation & Backfill | 4.5 pts | python-backend-engineer | sonnet | human gate on dry-run diff |
| 3 | Creation Path | 3.5 pts | python-backend-engineer | sonnet | parallel to P2 |
| 4 | Export & FE Types | 5 pts | python-backend-engineer, ui-engineer-enhanced | sonnet | serialization barrier |
| 5 | Viewer Display | 8 pts | ui-engineer-enhanced, frontend-developer | sonnet | enumerate target_surfaces |
| 6 | Filtering/Faceting | 4 pts | ui-engineer-enhanced, frontend-developer | sonnet | after P5 display |
| 7 | Enrichment Extras (P1) | 5 pts | python-backend-engineer, ui-engineer-enhanced | sonnet | parallel to P5 after P4 |
| 8 | Tests & Docs | 5 pts | python-backend-engineer, ui-engineer-enhanced, documentation-writer, changelog-generator, karen | sonnet (impl), haiku (docs), opus (karen) | R-P4 smoke + karen gate |
| **Total** | — | **~37 task-pts / ~16-20 feature-pts** | — | — | bottom-up; see Human Brief §2 |

**Model column**: `sonnet` for implementation; `haiku` for docs/changelog; `opus` for karen gate only.

---

## Phase File Index

This plan exceeds 800 lines. Detailed task tables are in phase files:

| Phase file | Phases | Key content |
|------------|--------|-------------|
| [phase-1-3-schema-derivation-creation.md](./run-metadata-enrichment-v1/phase-1-3-schema-derivation-creation.md) | P1, P2, P3 | run.yaml fields, JSON schema, TS codegen, backfill script, creation path |
| [phase-4-5-export-and-display.md](./run-metadata-enrichment-v1/phase-4-5-export-and-display.md) | P4, P5 | export threading, index.json, FE types, all display target_surfaces |
| [phase-6-8-filter-enrichment-tests-docs.md](./run-metadata-enrichment-v1/phase-6-8-filter-enrichment-tests-docs.md) | P6, P7, P8 | filtering, enrichment widgets, unit tests, runtime smoke, CHANGELOG, docs, karen |

---

## Deferred Items & In-Flight Findings Policy

### Deferred Items Triage Table

| Item ID | Category | Reason Deferred | Trigger for Promotion | Target Spec Path |
|---------|----------|-----------------|-----------------------|-----------------|
| DEF-001 | backlog | Unresolved questions from claim_ledger not yet exported (needs schema change) | Claim enrichment epic | `docs/project_plans/design-specs/claim-ledger-unresolved-questions-export.md` |
| DEF-002 | backlog | Audience field from report frontmatter surfacing (needs report parsing) | Viewer demand / report tab epic | `docs/project_plans/design-specs/report-audience-surfacing.md` |
| DEF-003 | dependency-blocked | G-tab Swarm/Policies/Library data dep — unblocked by F5 export shipping | G epic | Tracked in G epic; no separate spec |

*DEF-001 and DEF-002 require design spec authoring tasks in P8 (see DOC-006 in phase file).*

### In-Flight Findings

Findings doc: lazy-created at `.claude/findings/run-metadata-enrichment-findings.md` on first finding.
Set `findings_doc_ref` here when created.

---

## Risk Mitigation

### Technical Risks

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| **Dual-write consistency** (run.yaml vs run_index.yaml vs derived backlog_context) | High | Medium | Single writer = migration script / plan_run; run_index derived from run.yaml; atomic file writes (tmp → rename) |
| **Backfill correctness** (slug matching backlog↔run) | High | Low | Use `links.run_id` as authoritative join key (NOT fuzzy title); dry-run diff reviewed by human before writes (MIG-005 gate) |
| **Export schema_version compat** for older static bundles | Medium | Medium | All new fields optional/nullable; FE resilient (R-P2); bump version for observability only |
| **"everywhere" surface sprawl** (R-P1) | Medium | High | Enumerate target_surfaces per §1.9; one runtime-smoke task per UI surface (SMOKE-001 in P8) |
| **Migration reversibility** | Medium | Low | `--backup` / `--restore` modes; run.yaml source persists in git |
| **TS type drift post-codegen decision** | Low | Medium | If codegen rejected: comment in run-export.ts documents reason; manual sync enforced by PR review |
| **F1 / F5 index.json conflict** | Medium | Medium | F5-P4 supersedes F1 index.json touch; coordinate: implement after F1 lands or merge the two index.json changes in the same PR |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Backfill dry-run review adds delay (human gate) | Medium | Medium | Schedule early; gate is async — engineer can proceed on P3 while human reviews |
| P4 export barrier blocks FE work | High | Low | P5 FE prep (design, component stubs) can start before P4 completes; data dependency is read-only |
| karen review raises architecture concerns | Medium | Low | Early decisions block review; karen is informed by the same decisions block that shaped the plan |

---

## Success Metrics

### Delivery
- All 8 phases sealed with quality gates passing
- `uv run pytest` clean (unit tests for derivation + export)
- `npx tsc --noEmit` clean (no new type errors)
- SMOKE-001 signed off (all 7 UI surfaces verified)

### Product
- Portfolio table shows Linked Projects for backlog-linked runs (≥ the runs with `links.run_id` in backlog)
- Filtering by project/category/tag reduces portfolio runs correctly
- No viewer regression on pre-migration runs (null fields render gracefully)
- Downstream tabs (G1, G2, G4) can proceed after F5-P4 ships

### Technical
- Export schema_version advanced to "1.2"
- Formal `rf-run-export-schema.json` exists and validates
- Backfill script is idempotent and dry-run-able
- CHANGELOG entry under `[Unreleased]`

---

## Wrap-Up: Feature Guide & PR

After P8 seals and karen clears:

1. Delegate to `documentation-writer` (haiku): create `.claude/worknotes/run-metadata-enrichment/feature-guide.md`
   with frontmatter (doc_type: feature_guide, prd_ref, plan_ref, created: 2026-06-20) and sections:
   What Was Built, Architecture Overview, How to Test (re-export + rebuild steps), Test Coverage Summary,
   Known Limitations (DEF-001, DEF-002).

2. Open PR:
   ```bash
   gh pr create \
     --title "feat(run-metadata): add Linked Projects, Category, Tags to runs + viewer display" \
     --body "$(cat <<'EOF'
   ## Summary
   - Extend run.yaml with linked_projects, category, tags, backlog_idea_ref (derived from research backlog)
   - Add idempotent backfill script + creation-path wiring in plan_run() and rf capture CLI
   - Thread fields through export pipeline; bump schema_version to 1.2; add formal JSON schema
   - Surface Linked Projects as primary portfolio column + tags/category chips on all viewer surfaces
   - Add portfolio filtering by project/category/tag
   - Add Overview enrichment widgets (cost, model profiles, source counts, writeback status)

   ## Feature Guide
   .claude/worknotes/run-metadata-enrichment/feature-guide.md

   ## Test plan
   - [ ] uv run pytest (derivation + export unit tests pass)
   - [ ] npx tsc --noEmit clean
   - [ ] SMOKE-001: all 7 UI surfaces verified with populated + null-field runs
   - [ ] CHANGELOG [Unreleased] entry present
   - [ ] karen gate cleared (REV-002)

   🤖 Generated with Claude Code
   EOF
   )"
   ```

---

**Progress Tracking**: `.claude/progress/run-metadata-enrichment/`

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-06-20
