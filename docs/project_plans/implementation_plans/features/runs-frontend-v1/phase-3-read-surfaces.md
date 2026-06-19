---
schema_version: 2
doc_type: phase_plan
title: "Phase 3: Read Surfaces — Run List + Trust Panel"
status: draft
created: 2026-06-19
updated: 2026-06-19
phase: 3
phase_title: "Read Surfaces — Run List + Trust Panel"
feature_slug: runs-frontend
prd_ref: docs/project_plans/PRDs/features/runs-frontend-v1.md
plan_ref: docs/project_plans/implementation_plans/features/runs-frontend-v1.md
entry_criteria:
  - Phase 2 complete (app boots, tsc --noEmit clean, hooks typed, OQ-5 decision recorded)
  - P1 gate cleared (implicit via P2 dependency chain)
  - Static JSON fixtures available in frontend/runs-viewer/src/test/fixtures/
integration_owner: ui-engineer-enhanced
exit_criteria:
  - Run list renders all runs including 4 nested runs/runs/ runs
  - Filter tabs function correctly from fixture
  - Trust panel renders per-check verification checklist; failing check deep-link renders clm_NNN anchor
  - All 9 optional entities show graceful empty-states
  - Seam task P3-SEAM-001 passes
  - Vitest tests green for list/filter/checklist
  - task-completion-validator P3 phase review passed
---

# Phase 3: Read Surfaces — Run List + Trust Panel

**Parent Plan**: [runs-frontend-v1.md](../runs-frontend-v1.md)
**Duration**: ~2 days
**Primary Subagent**: `ui-engineer-enhanced` (run list + integration owner) | Model: `sonnet` | Effort: `adaptive`
**Parallel Subagent**: `frontend-developer` (trust panel) | Model: `sonnet` | Effort: `adaptive`
**Integration Owner**: `ui-engineer-enhanced`

---

## Phase Overview

Phase 3 builds the two "direct adaptation" surfaces: the run list (adapted from IntentTree `WorkspaceRuns.tsx`) and the run overview trust panel (adapted from IntentTree `WorkflowViewerScreen` 4-panel layout). Both are low-novelty, high-reuse adaptations. The two subagents work in parallel on disjoint component files but share the `useRunDetail()` hook and the `RunDetailScreen.tsx` parent container. The integration owner (ui-engineer-enhanced) resolves any hook contract questions and owns the seam task.

**R-P3 (two FE owners)**: `ui-engineer-enhanced` owns run list + `RunListScreen.tsx` + `RunDetailScreen.tsx` parent. `frontend-developer` owns trust-panel child components (`TrustPanel/`, `VerificationChecklist/`, `ClaimStatusDonut/`). The seam is `RunDetailScreen.tsx` → `TrustPanel` composition. Seam task P3-SEAM-001 verifies this contract.

**R-P1 compliance**: FR-3 says "all runs" — this requires explicit `target_surfaces:` enumeration (see AC P3-LIST-001-1 below).

---

## Task Table — Run List Sub-Track (ui-engineer-enhanced)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P3-LIST-CARD | Run list card component | Implement `frontend/runs-viewer/src/components/RunList/RunCard.tsx`. Displays per-run: derived lifecycle badge (verified / needs-review / failed / planned), sensitivity badge, claim counts (supported/inference/speculation), verification pass/fail indicator, governance verdict. Uses `RFRunSummary` typed data from `useRunList()`. Component vocabulary: `@miethe/ui` card (if OQ-5 compatible) or IntentTree card (per P2-AUDIT-OQ5 decision). | `RunCard` renders all five data points for a run with non-null data; renders graceful empty-state when any optional field absent (R-P2 compliance: missing sensitivity badge, missing governance verdict handled); no `any` in props | 0.5 pts | ui-engineer-enhanced | sonnet | adaptive | P2-HOOKS |
| P3-LIST-SCREEN | Run list screen + filter tabs | Implement `frontend/runs-viewer/src/screens/RunListScreen.tsx`. Uses `useRunList()` hook. Renders one `RunCard` per run. Filter tabs by derived state (verified / needs-review / failed / planned). Tab selection updates displayed cards without page navigation. Discovery: relies on P1-CLI-LIST's recursive `runs/**/run.yaml` walk (depth ≤ 3) — the 4 nested `runs/runs/` runs must appear. | Run list renders all runs from fixture including nested `runs/runs/` runs; filter tabs filter correctly; selecting "verified" tab shows only runs with `status_derived: verified` | 0.5 pts | ui-engineer-enhanced | sonnet | adaptive | P3-LIST-CARD |

#### AC P3-LIST-001-1: All Runs Visible (R-P1 — FR-3)
FR-3 says "all runs" and "across" — explicit target_surfaces required:
- target_surfaces:
    - frontend/runs-viewer/src/screens/RunListScreen.tsx
    - frontend/runs-viewer/src/components/RunList/RunCard.tsx
    - frontend/runs-viewer/src/hooks/useRunList.ts
- propagation_contract: `useRunList()` returns all runs from the fixture JSON (sourced from P1-CLI-LIST recursive discovery); `RunListScreen` renders one card per returned run; filter tabs operate on the full set
- resilience: If a run's optional field (e.g., `governance_verdict`) is absent, `RunCard` renders without that badge; never crashes on partial data
- visual_evidence_required: false
- verified_by: [P3-LIST-SCREEN, P5-E2E-W3]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P3-SCHEMA-BADGE | Schema-mismatch badge | OQ-7 (partial resolution): add optional schema-version mismatch badge to `RunCard`. If `run.json` metadata contains `schema_version_mismatch: true`, render a warning badge in the run card metadata section. Graceful: badge absent when field absent (not an error). | Badge renders when `schema_version_mismatch: true` present in fixture run; badge absent when field absent; no render error when field absent | 0.25 pts | ui-engineer-enhanced | sonnet | adaptive | P3-LIST-CARD |

---

## Task Table — Trust Panel Sub-Track (frontend-developer)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P3-TRUST-CHECKLIST | Verification checklist component | Implement `frontend/runs-viewer/src/components/TrustPanel/VerificationChecklist.tsx`. Renders named checks from `verification.yaml` (pass/fail/warning per check, severity badge). Each failing check renders a deep-link anchor pointing to `#clm_NNN` in the claim ledger view. Adapted from IntentTree `WorkflowViewerScreen` panel component. | Checklist renders all named checks from fixture `verification.yaml`; pass/fail/warning badges correct; failing check deep-link anchor renders as `href="#clm_NNN"`; no render error when `verification.yaml` absent (empty-state) | 0.5 pts | frontend-developer | sonnet | adaptive | P2-HOOKS |

#### AC P3-TRUST-001-1: Deep-Link from Failing Check to Ledger (FR-4)
- target_surfaces:
    - frontend/runs-viewer/src/components/TrustPanel/VerificationChecklist.tsx
    - frontend/runs-viewer/src/screens/RunDetailScreen.tsx
- propagation_contract: Each failing check in VerificationChecklist renders an anchor `<a href="#clm_NNN">` where `clm_NNN` is the check's `claim_ref` from `verification.yaml`; clicking navigates to the claim in the ledger view
- resilience: If `claim_ref` is absent on a check entry, render the check without a deep-link (no crash)
- visual_evidence_required: false
- verified_by: [P3-TRUST-CHECKLIST, P3-SEAM-001]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P3-TRUST-DONUT | Claim-status donut | Implement `frontend/runs-viewer/src/components/TrustPanel/ClaimStatusDonut.tsx`. Renders a donut chart (or simple stat display) from `evidence_bundle.counts`: supported/inference/speculation counts. Graceful empty-state when `evidence_bundle` absent. | Donut renders correct counts from fixture; renders empty-state with "No claims data" when `evidence_bundle.counts` absent; no render error | 0.25 pts | frontend-developer | sonnet | adaptive | P2-HOOKS |
| P3-TRUST-PANEL | Trust panel composite | Implement `frontend/runs-viewer/src/components/TrustPanel/TrustPanel.tsx`. Assembles: header (derived status + sensitivity + governance badges), `VerificationChecklist`, `ClaimStatusDonut`, timeline stepper from `telemetry/run_trace.jsonl` events, governance/approval block from `evidence_bundle.governance`. Adapted from IntentTree `WorkflowViewerScreen` 4-panel layout. | TrustPanel renders all sub-components; timeline stepper shows stage events from fixture JSONL; governance block renders when present; all sub-components show empty-state when data absent | 0.5 pts | frontend-developer | sonnet | adaptive | P3-TRUST-CHECKLIST, P3-TRUST-DONUT |

---

## Task Table — Shared + Seam Tasks (ui-engineer-enhanced)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P3-EMPTY-STATES | Optional entity empty-states | All 9 optional entities must show graceful empty-states when absent from the fixture. Optional entities: `source_candidates`, `report_final`, `critic_review`, `council_review`, `governance_review`, `raw_idea`, `research_intent`, `ibom`, `intenttree_node`. Add empty-state rendering to each relevant component slot in `RunDetailScreen.tsx`. | Tested with scaffold-only fixture (no optional entities present): all 9 optional entity slots render "Not available" or equivalent empty-state; no console errors; no null-pointer component crashes | 0.5 pts | ui-engineer-enhanced | sonnet | adaptive | P3-TRUST-PANEL, P3-LIST-SCREEN |

#### AC P3-EMPTY-001-1: All 9 Optional Entities (FR-10, R-P1)
FR-10 says "all 9 optional entities" — explicit `target_surfaces:` required:
- target_surfaces:
    - frontend/runs-viewer/src/screens/RunDetailScreen.tsx
    - frontend/runs-viewer/src/components/TrustPanel/TrustPanel.tsx
    - frontend/runs-viewer/src/components/RunList/RunCard.tsx (governance_review badge)
- propagation_contract: Each of the 9 optional entity slots renders an empty-state component when the entity is absent from `useRunDetail()` data
- resilience: Absence of optional entity (null or undefined) triggers empty-state; never propagates to a React error boundary
- visual_evidence_required: false
- verified_by: [P3-EMPTY-STATES, P3-SEAM-001]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P3-SEAM-001 | Seam task: run list → run detail navigation contract | Verify the cross-owner navigation contract: (1) clicking a `RunCard` in `RunListScreen` navigates to `RunDetailScreen` with the correct `runId`; (2) `RunDetailScreen` composes `TrustPanel` using `useRunDetail(runId)`; (3) failing check deep-link from `VerificationChecklist` renders the correct `#clm_NNN` anchor. This is the integration seam between `ui-engineer-enhanced` (list/screen) and `frontend-developer` (trust panel). | Navigation from `RunListScreen` → `RunDetailScreen` passes correct `runId`; `TrustPanel` receives correct `run` data; failing check anchor renders `#clm_NNN` for a check with `claim_ref: clm_042` in fixture | 0.25 pts | ui-engineer-enhanced | sonnet | adaptive | P3-EMPTY-STATES |
| P3-VITEST | Phase 3 Vitest tests | Unit tests: (a) run list card rendering with all badge variants; (b) filter tab logic (correct set visible per tab); (c) verification checklist check rendering (pass/fail/warning badges); (d) sensitivity badge renders/absent correctly; (e) empty-state renders for scaffold-only fixture. | All P3 Vitest tests passing in CI; at least one test per AC listed above | 0.5 pts | ui-engineer-enhanced | sonnet | adaptive | P3-SEAM-001 |

---

## Phase 3 Parallel Execution

```
Phase 2 complete
      │
      ├── ui-engineer-enhanced track:
      │     P3-LIST-CARD → P3-LIST-SCREEN → P3-SCHEMA-BADGE
      │
      └── frontend-developer track (parallel):
            P3-TRUST-CHECKLIST → P3-TRUST-DONUT → P3-TRUST-PANEL
      │
      ├── P3-EMPTY-STATES (ui-engineer-enhanced; after both tracks complete)
      └── P3-SEAM-001 (ui-engineer-enhanced; seam verification)
              └── P3-VITEST
```

---

## Key Files Affected

- `frontend/runs-viewer/src/screens/RunListScreen.tsx` (new)
- `frontend/runs-viewer/src/screens/RunDetailScreen.tsx` (new — seam file; owned by integration_owner)
- `frontend/runs-viewer/src/components/RunList/RunCard.tsx` (new)
- `frontend/runs-viewer/src/components/RunList/FilterTabs.tsx` (new)
- `frontend/runs-viewer/src/components/TrustPanel/TrustPanel.tsx` (new)
- `frontend/runs-viewer/src/components/TrustPanel/VerificationChecklist.tsx` (new)
- `frontend/runs-viewer/src/components/TrustPanel/ClaimStatusDonut.tsx` (new)
- `frontend/runs-viewer/src/components/TrustPanel/TimelineStepper.tsx` (new)
- `frontend/runs-viewer/src/components/shared/EmptyState.tsx` (new or reused from fork)
