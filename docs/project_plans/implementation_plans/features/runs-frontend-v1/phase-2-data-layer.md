---
schema_version: 2
doc_type: phase_plan
title: "Phase 2: Data Layer + TypeScript Types"
status: draft
created: 2026-06-19
updated: 2026-06-19
phase: 2
phase_title: "Data Layer + TypeScript Types"
feature_slug: runs-frontend
prd_ref: docs/project_plans/PRDs/features/runs-frontend-v1.md
plan_ref: docs/project_plans/implementation_plans/features/runs-frontend-v1.md
entry_criteria:
  - P1 gate cleared (export schema frozen + merged at docs/dev/architecture/rf-run-export-schema.md)
  - rf run export --json integration test green
  - backend-architect schema review sign-off recorded
  - task-completion-validator P1 phase review passed
exit_criteria:
  - App boots in browser against P1 export fixture; no console errors
  - tsc --noEmit clean; no `any` at entity boundaries
  - All four React Query hooks return typed data from static JSON fixture
  - OQ-5 @miethe/ui compatibility decision recorded before P3 begins
  - Vitest hook contract tests passing
  - task-completion-validator P2 phase review passed
---

# Phase 2: Data Layer + TypeScript Types

**Parent Plan**: [runs-frontend-v1.md](../runs-frontend-v1.md)
**Duration**: ~2–3 days
**Primary Subagent**: `ui-engineer-enhanced` | Model: `sonnet` | Effort: `adaptive`

> **Explicit gate dependency**: Every task in this phase depends on **P1-SCHEMA-FREEZE** being merged. Do not begin any task until the P1 gate is cleared.

---

## Phase Overview

Phase 2 forks IntentTree Web into `frontend/runs-viewer/`, swaps the entity model (`AgentRun` → `RFRun`), generates TypeScript types from the 20 `schemas/*.schema.yaml` files, wires React Query hooks, and resolves the OQ-5 `@miethe/ui` compatibility question. This is mostly mechanical fork wiring — novelty is low, which is why `effort: adaptive` is correct. The OQ-5 audit must complete before P3 so that the component vocabulary is settled.

**Resolves in this phase**: OQ-5 (`@miethe/ui` compatibility audit).

---

## Task Table

All tasks depend on **P1-SCHEMA-FREEZE** (the schema freeze doc being merged). This dependency is listed on the first task below and propagates transitively to all subsequent tasks.

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P2-FORK | Fork scaffold + entity swap | Fork IntentTree Web into `frontend/runs-viewer/`. Remove or stub out IntentTree-specific entity files (`AgentRun`, `agentRuns.ts` API module, IntentTree-specific screens). Rename/replace entity root: `AgentRun` → `RFRun`. Preserve: React + Vite + React Query + Tailwind config, router shell, layout components, Vitest config, `tsconfig.json`. | `frontend/runs-viewer/` directory exists; app starts (Vite dev server boots without import errors); no remaining `AgentRun` type references in entity files; `RFRun` stub type defined | 0.5 pts | ui-engineer-enhanced | sonnet | adaptive | P1-SCHEMA-FREEZE |

#### AC P2-FORK-1: FE Handles Missing Fields (R-P2)
The P1 export service introduces new fields on `RFClaim`, `RFSourceCard`, and `RFEvidenceBundle`. The fork scaffold must handle any missing optional field gracefully.
- target_surfaces:
    - frontend/runs-viewer/src/types/rf/index.ts
    - frontend/runs-viewer/src/components/ (all)
- propagation_contract: All optional fields in generated types marked `?` (optional); access via `?.` operator throughout components
- resilience: Missing optional field renders empty-state or omits sub-section; never throws a runtime error
- visual_evidence_required: false
- verified_by: [P2-TS-CODEGEN, P3-EMPTY-STATES]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P2-TS-CODEGEN | TypeScript type generation | Set up `json-schema-to-typescript` (or `quicktype`) build step. Generate TypeScript interfaces from all 20 `schemas/*.schema.yaml` files into `frontend/runs-viewer/src/types/rf/`. Generated types include: `RFRun`, `RFRunSummary`, `RFClaim`, `RFSourceCard`, `RFEvidenceBundle`, `RFVerification`, `RFGovernanceBlock`, `RFTimelineEvent`, and generated types for all 9 optional entities. | Build step (`npm run codegen:types` or equivalent) generates all 20 entity types; no manual type files at entity boundaries; `tsc --noEmit` clean after codegen; required fields non-optional, optional fields marked `?`; no `any` at entity boundaries | 1 pt | ui-engineer-enhanced | sonnet | adaptive | P2-FORK |
| P2-AUDIT-OQ5 | @miethe/ui compatibility audit | Audit the IntentTree Web fork's existing component dependencies against `@miethe/ui` peer requirements. Check: React version compat, Tailwind version compat, any conflicting radix-ui / headlessui peer deps. Record decision: (a) use `@miethe/ui` cards/modals for v1 (preferred), or (b) use IntentTree's existing panel/card components for v1 + plan `@miethe/ui` adoption post-v1. Record the decision in a `.claude/worknotes/runs-frontend/oq5-decision.md` worknote. | OQ-5 decision recorded in worknote before any P3 component work begins; if incompatibility found, IntentTree's own components identified as interim vocabulary; decision does not block P3 | 0.5 pts | ui-engineer-enhanced | sonnet | adaptive | P2-FORK |
| P2-API-CLIENT | API client module | Implement `frontend/runs-viewer/src/api/client.ts`. Dual-mode fetch wrapper: (a) static JSON mode — reads pre-built `run.json` from `frontend/runs-viewer/public/data/`; (b) loopback mode — fetches from `http://127.0.0.1:<port>/api/` (behind `RUNS_FRONTEND_LOOPBACK_API` flag). GET-only; no POST/PUT/DELETE methods defined. Typed return values using generated types (P2-TS-CODEGEN). | Client module exports typed fetch functions for all entity endpoints; static JSON mode works without a running server; loopback mode function stubs present but gated behind env flag; no POST/PUT/DELETE methods exported; all return types use generated interfaces | 0.5 pts | ui-engineer-enhanced | sonnet | adaptive | P2-TS-CODEGEN |

#### AC P2-API-CLIENT-1: Read-Only Enforcement (NFR-S2)
- target_surfaces:
    - frontend/runs-viewer/src/api/client.ts
- propagation_contract: Client module only exports GET-typed functions; mutation methods (post, put, delete, patch) are absent from the module surface
- resilience: If static JSON file missing, returns typed empty result with `error: "fixture not found"`; never throws unhandled rejection
- visual_evidence_required: false
- verified_by: [P2-HOOKS, P5-E2E-W1]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P2-HOOKS | React Query hooks | Implement four React Query hooks in `frontend/runs-viewer/src/hooks/`: `useRunList()`, `useRunDetail(runId)`, `useClaimLedger(runId)`, `useSourceCard(runId, sourceCardId)`. Adapted from IntentTree's `api/agentRuns.ts` pattern. All hooks return typed data via generated types. Static JSON fixture (from P1 integration test output) wired as default test data source. | All four hooks return correctly typed data when called against the static JSON fixture; hooks handle loading / error / success states; Vitest tests pass for hook contract (mock the API client); no `any` in hook signatures or return types | 1 pt | ui-engineer-enhanced | sonnet | adaptive | P2-API-CLIENT |
| P2-FIXTURE | Vitest test fixtures | Copy the `run.json` produced by P1 integration test (`rf_run_20260613_*` export) into `frontend/runs-viewer/src/test/fixtures/`. Add a synthetic empty-state fixture (scaffold-only run with no optional entities). Wire fixtures into Vitest config for all P2+ tests. | `frontend/runs-viewer/src/test/fixtures/run.json` exists and is valid; scaffold-only fixture exists; Vitest imports fixtures without path errors; hook tests import fixtures | 0.25 pts | ui-engineer-enhanced | sonnet | adaptive | P2-HOOKS |

---

## Phase 2 Dependency Graph

```
P1-SCHEMA-FREEZE (P1 gate cleared)
     └── P2-FORK
              ├── P2-TS-CODEGEN ──────┐
              ├── P2-AUDIT-OQ5        │
              └── (after codegen)     │
                   P2-API-CLIENT ─────┤
                        └── P2-HOOKS ─┴── P2-FIXTURE
```

---

## Key Files Affected

- `frontend/runs-viewer/` (new — forked from IntentTree Web)
- `frontend/runs-viewer/src/types/rf/` (new — generated TypeScript types)
- `frontend/runs-viewer/src/api/client.ts` (new)
- `frontend/runs-viewer/src/hooks/useRunList.ts` (new)
- `frontend/runs-viewer/src/hooks/useRunDetail.ts` (new)
- `frontend/runs-viewer/src/hooks/useClaimLedger.ts` (new)
- `frontend/runs-viewer/src/hooks/useSourceCard.ts` (new)
- `frontend/runs-viewer/src/test/fixtures/` (new)
- `.claude/worknotes/runs-frontend/oq5-decision.md` (new — OQ-5 resolution)

---

## Phase 2 Notes

- **OQ-5 timing**: The audit (P2-AUDIT-OQ5) is the second task after fork, before any component work. If incompatibility is found, the decision to use IntentTree's existing cards/panels for v1 does not change the P2 scope — it only affects which component imports P3/P4 use. P2 is component-free.
- **No form elements rule**: The API client (P2-API-CLIENT) must not export any mutation methods. This is enforced in the AC and reviewed at the P2 gate.
- **R-P2 compliance**: All generated types from P2-TS-CODEGEN mark optional fields with `?`. P3 and P4 components access optional fields via `?.` throughout. This is validated at the P2 `tsc --noEmit` gate and at P3/P4 component reviews.
