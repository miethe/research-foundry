---
title: 'Implementation Plan: Research Foundry Runs Frontend v1'
schema_version: 2
doc_type: implementation_plan
status: completed
created: 2026-06-19
updated: '2026-06-19'
feature_slug: runs-frontend
feature_version: v1
prd_ref: docs/project_plans/PRDs/features/runs-frontend-v1.md
plan_ref: null
scope: Read-only web viewer for RF run provenance and verification status; Python
  export contract + forked SPA (IntentTree Web) + E2E hardening.
effort_estimate: 13 pts
architecture_summary: 'Phase 1 (Python-only upstream gate): rf run export --json denormalized
  claim-graph + sensitivity redaction. Phases 2-5: forked IntentTree Web SPA (frontend/runs-viewer/),
  entity swap AgentRun->RFRun, TS codegen from schemas/*.schema.yaml, React Query
  hooks, P3 read surfaces, P4 flagship provenance, P5 E2E + build + docs.'
related_documents:
- docs/project_plans/PRDs/features/runs-frontend-v1.md
- docs/project_plans/exploration/runs-frontend/runs-frontend-feasibility-brief.md
- docs/project_plans/exploration/runs-frontend/runs-frontend-charter.md
- docs/project_plans/exploration/runs-frontend/spikes/tech-findings.md
- docs/project_plans/exploration/runs-frontend/spikes/risk-findings.md
- docs/project_plans/exploration/runs-frontend/spikes/priorart-findings.md
- .claude/worknotes/runs-frontend/decisions-block.md
references:
  user_docs: []
  context: []
  specs:
  - docs/dev/architecture/rf-run-export-schema.md
  related_prds: []
spike_ref: null
adr_refs:
- docs/dev/architecture/adr-runs-read-path.md
deferred_items_spec_refs:
- docs/project_plans/design-specs/runs-auth-lan.md
- docs/project_plans/design-specs/runs-loopback-api.md
- docs/project_plans/design-specs/runs-writeback-preview.md
- docs/project_plans/design-specs/runs-context-panels.md
findings_doc_ref: null
charter_ref: docs/project_plans/exploration/runs-frontend/runs-frontend-charter.md
changelog_ref: CHANGELOG.md
changelog_required: true
test_plan_ref: null
plan_structure: independent
progress_init: auto
owner: nick
contributors: []
priority: high
risk_level: medium
category: features
tags:
- implementation
- planning
- phases
- runs-frontend
- viewer
- provenance
- export
milestone: null
commit_refs: []
pr_refs: []
files_affected:
- src/research_foundry/services/export_service.py
- src/research_foundry/cli_commands.py
- frontend/runs-viewer/
- docs/dev/architecture/rf-run-export-schema.md
wave_plan:
  serialization_barriers:
  - docs/dev/architecture/rf-run-export-schema.md
  - CHANGELOG.md
  - README.md
  phases:
  - id: P1
    depends_on: []
    isolation: shared
    parallelizable: false
    owner_skills: []
    files_affected:
    - src/research_foundry/services/export_service.py
    - src/research_foundry/cli_commands.py
    - docs/dev/architecture/rf-run-export-schema.md
    - tests/unit/test_export_service.py
    - tests/integration/test_export_round_trip.py
  - id: P2
    depends_on:
    - P1
    isolation: shared
    parallelizable: false
    owner_skills: []
    files_affected:
    - frontend/runs-viewer/
    - frontend/runs-viewer/src/types/rf/
    - frontend/runs-viewer/src/api/
    - frontend/runs-viewer/src/hooks/
  - id: P3
    depends_on:
    - P2
    isolation: shared
    parallelizable: true
    owner_skills: []
    files_affected:
    - frontend/runs-viewer/src/components/RunList/
    - frontend/runs-viewer/src/components/TrustPanel/
    - frontend/runs-viewer/src/screens/RunListScreen.tsx
    - frontend/runs-viewer/src/screens/RunDetailScreen.tsx
  - id: P4
    depends_on:
    - P3
    isolation: shared
    parallelizable: true
    owner_skills: []
    files_affected:
    - frontend/runs-viewer/src/components/ClaimLedger/
    - frontend/runs-viewer/src/components/ProvenanceModal/
    - frontend/runs-viewer/src/components/ReportOverlay/
    - frontend/runs-viewer/src/components/SourceCard/
    - frontend/runs-viewer/src/components/LineageGraph/
  - id: P5
    depends_on:
    - P4
    isolation: shared
    parallelizable: true
    owner_skills: []
    files_affected:
    - tests/e2e/
    - CHANGELOG.md
    - README.md
    - docs/dev/architecture/adr-runs-read-path.md
    - docs/project_plans/design-specs/runs-loopback-api.md
    - docs/project_plans/design-specs/runs-auth-lan.md
    - docs/project_plans/design-specs/runs-writeback-preview.md
    - docs/project_plans/design-specs/runs-context-panels.md
  waves:
  - - P1
  - - P2
  - - P3
  - - P4
  - - P5
---

# Implementation Plan: Research Foundry Runs Frontend v1

**Plan ID**: `IMPL-2026-06-19-RUNS-FRONTEND`
**Date**: 2026-06-19
**Author**: implementation-planner (Claude Sonnet 4.6)
**Human Brief**: `docs/project_plans/human-briefs/runs-frontend.md`
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/runs-frontend-v1.md`
- **Decisions Block**: `.claude/worknotes/runs-frontend/decisions-block.md`
- **Feasibility Brief**: `docs/project_plans/exploration/runs-frontend/runs-frontend-feasibility-brief.md`
- **Export Schema (to be authored in P1)**: `docs/dev/architecture/rf-run-export-schema.md`

**Complexity**: Medium (Tier 2)
**Total Estimated Effort**: 13 pts
**Track**: Standard — `task-completion-validator` per phase; `karen` at feature end

> **Estimation Rationale**: Lives in the Human Brief (§2). Plan retains per-phase task estimates only.

---

## Executive Summary

This plan delivers a read-only web viewer for Research Foundry run artifacts in five phases across two implementation layers: a Python-only upstream export contract (Phase 1, hard upstream gate) and a forked SPA (Phases 2–5). The export contract deterministically serializes the on-disk claim graph to a denormalized `run.json` with sensitivity redaction applied at source; no LLM is on the recall path. The SPA adapts IntentTree Web (~60% code reuse) with entity model swapped (`AgentRun` → `RFRun`) and TypeScript types generated from the 20 `schemas/*.schema.yaml` files. The flagship deliverable is the Phase 4 claim ledger and provenance drill-down modal, which resolves the two-ID-hop audit problem (the RIB-018 false-pass class) in two clicks. Success is measured by W1 (claim audit ≤ 30 sec), W2 (verification checklist visible without any CLI call), and W3 (run corpus browsable as a living portfolio).

**Key milestones**:
1. P1 schema-freeze + merge (required before any frontend work begins — hard gate)
2. P2 app boots against P1 export fixture, `tsc --noEmit` clean
3. P3 run list + trust panel render correctly from fixture
4. P4 two-click claim provenance drill-down working; sensitivity fixture test passes
5. P5 E2E green on static export fixture; build clean; docs merged; `karen` final review

---

## Implementation Strategy

### Architecture Sequence

This plan follows a two-layer architecture sequence:

**Layer A (Phase 1 — Python only):**
1. Export service + CLI commands
2. Sensitivity redaction gate
3. Schema freeze + documentation
4. Integration test on real run

**Layer B (Phases 2–5 — TypeScript SPA fork):**
1. Fork scaffold + entity swap + TS type generation (P2)
2. React Query hooks + static-JSON fetch client (P2)
3. Run list + trust panel read surfaces (P3)
4. Claim ledger + provenance modal + report overlay (P4)
5. E2E testing + static build + docs (P5)

### Parallel Work Opportunities

- Inside P3: run list ∥ trust panel (disjoint component files; shared types from P2)
- Inside P4: claim ledger + provenance modal ∥ report overlay ∥ lineage graph (should-have; file-ownership-disjoint)
- Inside P5: README ∥ CHANGELOG ∥ ADR ∥ E2E ∥ deferred-item design specs

### Critical Path

**P1 → P2 → P3 → P4 → P5** (strictly serial at phase boundaries; the export contract gates everything downstream)

**P1 is the hard upstream gate.** The export schema must be frozen, documented in `docs/dev/architecture/rf-run-export-schema.md`, and merged before any P2 task begins. Every P2 task has an explicit dependency on the schema-freeze task (P1-SCHEMA-FREEZE). This dependency propagates transitively to all P3+ tasks via P2's foundation.

### Phase Summary

| Phase | Title | Estimate | Target Subagent(s) | Model | Effort | Notes |
|-------|-------|----------|--------------------|-------|--------|-------|
| 1 | Export contract (upstream gate) | 4 pts | python-backend-engineer + backend-architect (schema review) | sonnet | P1 main: extended; schema review: adaptive | Hard gate — no P2+ task starts before schema merged |
| 2 | Data layer + TS types | 3 pts | ui-engineer-enhanced | sonnet | adaptive | Fork scaffold; TS codegen; React Query hooks; OQ-5 audit |
| 3 | Read surfaces — run list + trust panel | 2 pts | ui-engineer-enhanced + frontend-developer (parallel) | sonnet | adaptive | integration_owner: ui-engineer-enhanced |
| 4 | Flagship — claim ledger + report overlay | 4 pts | ui-engineer-enhanced + frontend-developer (parallel) | sonnet | P4 main: extended; P4 parallel: adaptive | Highest novelty; provenance logic |
| 5 | Testing, build, docs | 1 pt | ui-engineer-enhanced (E2E) + documentation-writer (README) + changelog-generator (CHANGELOG) + backend-architect (ADR) | sonnet (impl) / haiku (docs) | adaptive | Parallel docs ∥ E2E; 4 deferred-item design specs |
| **Total** | — | **13 pts** | — | — | — | Lean of reconciled 8–21 band |

---

## Deferred Items & In-Flight Findings Policy

### Deferred Items

| Item ID | Category | Reason Deferred | Trigger for Promotion | Target Spec Path |
|---------|----------|-----------------|-----------------------|-----------------|
| OQ-4 | scope-cut | Auth/LAN exposure not needed for loopback-only v1; no confirmed use case for agentic-nuc multi-device access | Active operator need for LAN exposure confirmed | `docs/project_plans/design-specs/runs-auth-lan.md` |
| OQ-6 | scope-cut | Static-export cycle sufficient for current operator cadence; live-browse JTBD not validated post-P2 | Operator identifies real "browse as runs land" JTBD; static export rebuild too slow | `docs/project_plans/design-specs/runs-loopback-api.md` |
| FR-13 | backlog | Writeback preview cards (writeback-review governance view) have low traversal value for v1 operator workflows | v1 ships and claim-audit workflow covers >80% of daily use | `docs/project_plans/design-specs/runs-writeback-preview.md` |
| FR-14 | backlog | Run context panels (routing decision, research brief, swarm plan, upstream entities) are secondary metadata; not on the W1/W2/W3 critical path | Post-v1 operator feedback confirms context panels would reduce run review time | `docs/project_plans/design-specs/runs-context-panels.md` |

**Rule**: DOC-006 in Phase 5 authors design specs for all four deferred items. Paths are pre-registered in the table above; append to `deferred_items_spec_refs` in this plan's frontmatter after authoring.

### In-Flight Findings

Lazy-creation rule applies: create `.claude/findings/runs-frontend-findings.md` only on the first real finding. Set `findings_doc_ref` in frontmatter on creation.

### Quality Gate

Phase 5 (Documentation + Hardening) cannot be sealed until:
- All four deferred items have design specs at their target paths, OR each is marked N/A with documented rationale in the triage table above
- If `findings_doc_ref` is populated: findings doc finalized and status advanced from `draft` → `accepted`

---

## Phase Breakdown

> Full task tables for each phase are in the linked phase files below. This parent plan retains the phase header, integration owner declarations (R-P3), and reviewer gates.

**Column conventions** (in phase files):
- `Estimate` — story points (never in Effort column)
- `Model` — `sonnet` | `haiku` | (no external models this feature)
- `Effort` — `adaptive` | `extended` (Claude only)

---

### Phase 1: Export Contract (Upstream Gate)

**Full details**: [`runs-frontend-v1/phase-1-export-contract.md`](./runs-frontend-v1/phase-1-export-contract.md)

**Duration**: ~3–4 days
**Dependencies**: None
**Assigned Subagent(s)**: `python-backend-engineer` (primary); `backend-architect` (schema-freeze review)
**Integration Owner**: N/A (Python-only phase; no FE/BE seam)
**Effort**: `extended` (algorithmic claim-graph join + path re-derivation + redaction correctness)

**P1 Hard Gate**: Phase 1 is not complete until ALL of the following are true:
1. `rf run export --json` produces valid `run.json` for `rf_run_20260613_*` real run
2. Export schema documented and frozen at `docs/dev/architecture/rf-run-export-schema.md`
3. Sensitivity redaction test passes with synthetic sensitivity fixture
4. Integration round-trip test green (claim → source → quote chain correct)
5. Schema-freeze doc merged to main

**No Phase 2+ task may begin until the P1 gate is cleared.**

**Phase 1 Quality Gates** (required to clear the hard gate):
- [ ] `rf run export --json` produces valid `run.json` for a real run; claim→source→quote chain correct
- [ ] `rf run list --json` returns derived status (not `run.yaml.status`) for representative runs including stale-status runs
- [ ] Sensitivity redaction: `work_sensitive` source card body content absent from export JSON; confirmed by synthetic fixture test (R9 gate)
- [ ] No stored absolute paths read from `run_index.yaml` or `verification.yaml`; all file reads via `FoundryPaths.discover()`
- [ ] Export schema documented and frozen at `docs/dev/architecture/rf-run-export-schema.md`
- [ ] OQ-2 derived-status enum encoded in export schema
- [ ] OQ-3 sensitivity threshold default resolved (`public`-only; `foundry.yaml` configurable)
- [ ] Unit test coverage > 80% for export service
- [ ] Integration test green on `rf_run_20260613_*`
- [ ] `backend-architect` schema review sign-off recorded
- [ ] `task-completion-validator` phase review passed

---

### Phase 2: Data Layer + TypeScript Types

**Full details**: [`runs-frontend-v1/phase-2-data-layer.md`](./runs-frontend-v1/phase-2-data-layer.md)

**Duration**: ~2–3 days
**Dependencies**: **P1 schema-freeze task (P1-SCHEMA-FREEZE) — HARD DEPENDENCY; no task in this phase may begin before the P1 gate is cleared**
**Assigned Subagent(s)**: `ui-engineer-enhanced`
**Integration Owner**: N/A (single owner phase; no FE/BE seam)
**Effort**: `adaptive` (mostly mechanical fork wiring + codegen; low novelty)

**Phase 2 Quality Gates**:
- [ ] App boots in browser against P1 export fixture with no console errors
- [ ] `tsc --noEmit` clean; no `any` at entity (`RFRun`, `RFClaim`, `RFSourceCard`, `RFEvidenceBundle`) boundaries
- [ ] `useRunList()`, `useRunDetail()`, `useClaimLedger()`, `useSourceCard()` hooks return typed data from static JSON fixture
- [ ] OQ-5 `@miethe/ui` compatibility decision recorded in ADR or worknote before P3 begins
- [ ] Vitest unit tests passing for hook contract
- [ ] `task-completion-validator` phase review passed

---

### Phase 3: Read Surfaces — Run List + Trust Panel

**Full details**: [`runs-frontend-v1/phase-3-read-surfaces.md`](./runs-frontend-v1/phase-3-read-surfaces.md)

**Duration**: ~2 days
**Dependencies**: Phase 2 complete (which implies P1 gate cleared)
**Assigned Subagent(s)**: `ui-engineer-enhanced` (run list + integration owner) ∥ `frontend-developer` (trust panel)
**Integration Owner**: `ui-engineer-enhanced` — owns shared P2 types and the `RunDetailScreen.tsx` seam
**Effort**: `adaptive` (adapting existing IntentTree panels; low novelty)

**R-P3 Declaration**: This phase has two FE owners sharing the `RunDetailScreen.tsx` parent container and `useRunDetail()` hook. The `integration_owner` (`ui-engineer-enhanced`) is responsible for the seam task (P3-SEAM-001) that verifies the run list → trust panel navigation contract and the shared hook contract.

**Phase 3 Quality Gates**:
- [ ] Run list renders all runs including the 4 nested `runs/runs/` runs
- [ ] Run list filter tabs (verified / needs-review / failed / planned) function correctly from fixture
- [ ] Trust panel renders per-check verification checklist from `verification.yaml` fixture; failing check deep-link renders correct `clm_NNN` anchor
- [ ] Claim-status donut renders from `evidence_bundle.counts` data
- [ ] All 9 optional entities show graceful empty-states (never errors) on a scaffold-only fixture
- [ ] OQ-7 schema-mismatch badge in run card metadata renders when `schema_version` mismatch detected
- [ ] Seam task (P3-SEAM-001) passes: run list card → run detail navigation contract verified end-to-end against fixture
- [ ] Vitest tests green for list/filter/checklist
- [ ] `task-completion-validator` phase review passed

---

### Phase 4: Flagship — Claim Ledger + Report Overlay

**Full details**: [`runs-frontend-v1/phase-4-flagship.md`](./runs-frontend-v1/phase-4-flagship.md)

**Duration**: ~3–4 days
**Dependencies**: Phase 3 complete
**Assigned Subagent(s)**: `ui-engineer-enhanced` (claim ledger + provenance modal) ∥ `frontend-developer` (report overlay + lineage graph)
**Integration Owner**: `ui-engineer-enhanced` — owns `ClaimLedger` types and `ProvenanceModal` shared between the two task groups
**Effort**: `ui-engineer-enhanced` tasks: `extended` (net-new provenance logic, inference chains, chip wiring); `frontend-developer` tasks: `adaptive`

**R-P3 Declaration**: Two FE owners share the `[claim:clm_NNN]` modal trigger contract and `useClaimDetail()` hook. Seam task (P4-SEAM-001) verifies the report-chip → claim modal open contract and the sensitivity-gate boundary between `ReportOverlay` and `ProvenanceModal`.

**Phase 4 Quality Gates**:
- [ ] Claim ledger table renders all `clm_NNN` entries with status/confidence/materiality badges
- [ ] Facets (status, materiality, claim_type, confidence) filter correctly
- [ ] Provenance drill-down modal resolves claim → sources[] → verbatim quote in ≤ 2 clicks from fixture
- [ ] Inference claim (`status: inference`) modal shows `from_claims` basis chain; empty `from_claims` (RIB-018 class) flagged as warning
- [ ] Source card rendered with sensitivity gate: `work_sensitive` body content absent from rendered output; confirmed by synthetic sensitivity fixture test (R9 gate — must pass)
- [ ] Report overlay renders `report_draft.md` Markdown with working `[claim:clm_NNN]` chips (click opens modal)
- [ ] `**Inference:**` and `**Speculation:**` sentences color-coded by claim status
- [ ] Composition sidebar shows % supported/inference/speculation with click-to-filter
- [ ] Lineage graph panel (should-have): renders with correct node types and edges for a representative run; graceful empty-state if absent
- [ ] Seam task (P4-SEAM-001) passes: report-chip → modal open contract and sensitivity-gate boundary verified
- [ ] Vitest tests green for drill-down/inference/sensitivity
- [ ] `task-completion-validator` phase review passed

---

### Phase 5: Testing, Build, and Documentation

**Full details**: [`runs-frontend-v1/phase-5-testing-build-docs.md`](./runs-frontend-v1/phase-5-testing-build-docs.md)

**Duration**: ~1–2 days
**Dependencies**: Phase 4 complete
**Assigned Subagent(s)**: `ui-engineer-enhanced` (E2E) ∥ `documentation-writer` (README) ∥ `changelog-generator` (CHANGELOG) ∥ `backend-architect` (ADR) — then `documentation-writer` (deferred design specs + plan frontmatter)
**Integration Owner**: N/A (hardening phase; no new cross-owner seams)
**Effort**: `adaptive` for all P5 tasks

**R-P4 Runtime Smoke**: All UI-touching phases (P3 + P4) must be covered by Playwright smoke tests in this phase. Smoke tasks reference each phase's `target_surfaces`:
- P3 surfaces: `RunListScreen`, `RunDetailScreen` / `TrustPanel`
- P4 surfaces: `ClaimLedgerView`, `ProvenanceModal`, `ReportOverlay`, `SourceCard`, `LineageGraph` (should-have)

**Phase 5 Quality Gates**:
- [ ] E2E smoke: W1 (claim drill-down from report chip to verbatim quote) — Playwright green on static export fixture
- [ ] E2E smoke: W2 (verification checklist rendering) — Playwright green on static export fixture
- [ ] E2E smoke: W3 (report chip navigation to claim modal) — Playwright green on static export fixture
- [ ] Provenance correctness test: every `[claim:clm_NNN]` tag in `report_draft.md` resolves to a valid ledger entry and at least one source card in the export JSON
- [ ] Runtime smoke covers all P3 + P4 target_surfaces
- [ ] Static SPA build pipeline wired to `rf run export --all` pre-build step; build completes cleanly
- [ ] ADR authored: read path decision (static export primary, loopback optional) + read-only architectural invariant; R9 sensitivity gate invariant recorded
- [ ] README CLI reference updated for `rf run export` and `rf run list`
- [ ] CHANGELOG `[Unreleased]` entry added; `changelog_ref` set in frontmatter
- [ ] All 4 deferred design specs authored (OQ-4, OQ-6, FR-13, FR-14) at their target paths; `deferred_items_spec_refs` populated
- [ ] Plan frontmatter updated: `status: completed`, `commit_refs`, `files_affected`, `updated`
- [ ] `task-completion-validator` phase review passed
- [ ] `karen` feature-end review passed

---

## Reviewer Gates

| Gate | Trigger | Reviewer | Blocks |
|------|---------|----------|--------|
| P1 phase review | All P1 quality gates pass including sensitivity fixture | `task-completion-validator` | P2 start |
| P1 schema review | Schema freeze candidate ready before merge | `backend-architect` | P1 gate clearance |
| P2 phase review | App boots, `tsc --noEmit` clean, OQ-5 resolved | `task-completion-validator` | P3 start |
| P3 phase review | List + trust panel render from fixture; seam task passes | `task-completion-validator` | P4 start |
| P4 phase review | Drill-down works; sensitivity fixture test passes; seam task passes | `task-completion-validator` | P5 start |
| P5 phase review | E2E green; build clean; docs merged | `task-completion-validator` | Feature close |
| Feature end | All phases complete; deferred specs authored; plan frontmatter final | `karen` | PR merge |

---

## Risk Mitigation

### High-Severity Risks (Concrete Task Coverage)

**R9 — Sensitivity / Governance Leakage (High, FR-9, NFR-S1)**
- Concrete tasks: P1-SENS-001 (synthetic sensitivity fixture + export redaction test), P4-SENS-001 (source card sensitivity gate in UI), P4-SEAM-001 (seam task verifies sensitivity boundary at modal boundary)
- Gate: Sensitivity fixture test must pass before P1 gate clears; source card sensitivity test must pass before P4 gate clears
- ADR: Records the invariant "sensitivity filter is applied at the export/serve layer, never in the component"
- Default threshold: `public`-only via `foundry.yaml` viewer key (OQ-3, resolved in P1)

**OQ-1 — Export Contract Schema Freeze (High, foundation risk)**
- Concrete task: P1-SCHEMA-FREEZE (first P1 task; authors `docs/dev/architecture/rf-run-export-schema.md` with denormalized claim-graph shape)
- Gate: This task is an explicit dependency of every Phase 2 task. Phase 2 cannot begin until the schema doc is merged
- Rationale: Every TypeScript type and React Query hook depends on this shape; iterating after P2 starts forces entity-swap rework across all hooks and components

### Medium-Severity Risks

| Risk | Mitigation Task(s) | Phase |
|------|--------------------|-------|
| R2: Stored absolute paths | P1-PATHS-001: unit test asserts no absolute path from stored fields | P1 |
| R4: Stale `run.yaml.status` | OQ-2 derived-status enum in export schema; P1-STATUS-001 | P1 |
| OQ-5: @miethe/ui incompatibility | P2-AUDIT-001: OQ-5 audit first task of P2; decision before P3 | P2 |
| R7: Scope creep to write mode | ADR records GET-only invariant; no form elements rule enforced in P3/P4 review | P3/P4 |
| R5: Schema drift | Viewer binds only `required:` fields; optional fields via `?.`; per-artifact empty-state | P2/P3/P4 |

---

## Success Metrics

### Delivery Metrics
- W1: Claim audit time < 30 sec (2-click provenance drill-down, measured on first 5 post-launch audits)
- W2: Verification checklist visible without any CLI call (feature present and rendering named checks with deep-links)
- W3: All runs discovered and listed including nested `runs/runs/` (run count in viewer = on-disk `rf_run_*` count)

### Technical Metrics
- Python export service: > 80% unit-test coverage
- TypeScript: no `any` at entity boundaries; `tsc --noEmit` clean
- E2E: Playwright smoke covers W1, W2, W3 on static export fixture
- Sensitivity: R9 fixture test passes (P1 and P4)
- Read-only: no POST/PUT/DELETE routes; no form elements in any UI component

---

## Wrap-Up: Feature Guide & PR

After all five phases are sealed:

1. `documentation-writer` (haiku) authors `.claude/worknotes/runs-frontend/feature-guide.md` with: What Was Built, Architecture Overview, How to Test (static export mode + optional loopback), Test Coverage Summary, Known Limitations (deferred OQ-4/OQ-6/FR-13/FR-14)
2. Open PR: title "feat(runs-frontend): read-only run provenance viewer v1" — body links to feature guide and CHANGELOG entry

---

**Progress Tracking**: `.claude/progress/runs-frontend/` (to be created at phase-execution time)
