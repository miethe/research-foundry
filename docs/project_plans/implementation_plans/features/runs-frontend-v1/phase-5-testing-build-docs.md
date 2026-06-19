---
schema_version: 2
doc_type: phase_plan
title: "Phase 5: Testing, Build, and Documentation"
status: draft
created: 2026-06-19
updated: 2026-06-19
phase: 5
phase_title: "Testing, Build, and Documentation"
feature_slug: runs-frontend
prd_ref: docs/project_plans/PRDs/features/runs-frontend-v1.md
plan_ref: docs/project_plans/implementation_plans/features/runs-frontend-v1.md
entry_criteria:
  - Phase 4 complete (claim ledger + provenance modal + report overlay all Vitest green; seam task passed; task-completion-validator P4 review passed)
integration_owner: null
exit_criteria:
  - E2E smoke green for W1, W2, W3 on static export fixture
  - Provenance correctness test passes
  - Runtime smoke covers all P3 + P4 target_surfaces
  - Static SPA build pipeline wired to rf run export --all; build completes cleanly
  - ADR authored with R9 sensitivity invariant + read-only constraint + read-path decision
  - README CLI reference updated
  - CHANGELOG [Unreleased] entry added; changelog_ref set in plan frontmatter
  - All 4 deferred design specs authored; deferred_items_spec_refs populated in plan frontmatter
  - Plan frontmatter updated: status completed, commit_refs, files_affected, updated
  - task-completion-validator P5 phase review passed
  - karen feature-end review passed
---

# Phase 5: Testing, Build, and Documentation

**Parent Plan**: [runs-frontend-v1.md](../runs-frontend-v1.md)
**Duration**: ~1–2 days
**Subagents** (parallel tracks):
- `ui-engineer-enhanced` (E2E + provenance correctness + build pipeline) | Model: `sonnet` | Effort: `adaptive`
- `documentation-writer` (README) | Model: `haiku` | Effort: `adaptive`
- `changelog-generator` (CHANGELOG) | Model: `haiku` | Effort: `adaptive`
- `backend-architect` (ADR) | Model: `sonnet` | Effort: `adaptive`
- `documentation-writer` (deferred design specs + plan frontmatter, sequential after parallel tracks) | Model: `sonnet` | Effort: `adaptive`

---

## Phase Overview

Phase 5 hardens and closes the feature. E2E smoke tests cover the W1/W2/W3 workflows end-to-end on the static export fixture; a provenance correctness assertion verifies every claim chip in the report resolves in the export JSON; the static SPA build is wired to `rf run export --all`; an ADR captures the read-path and read-only architectural decisions (including the R9 sensitivity invariant); and all four deferred items (OQ-4, OQ-6, FR-13, FR-14) receive design spec stubs. Documentation tasks run in parallel with E2E and ADR.

**R-P4 Runtime Smoke Coverage**: Phase 5 runtime smoke tasks must reference every `target_surfaces` entry from P3 and P4:
- P3 surfaces: `RunListScreen`, `RunDetailScreen` / `TrustPanel`
- P4 surfaces: `ClaimLedgerView`, `ProvenanceModal`, `ReportOverlay`, `SourceCard`, `LineageGraph` (should-have)

---

## Task Table — E2E + Build Track (ui-engineer-enhanced)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P5-E2E-W2 | E2E smoke: W2 verification checklist | Playwright test: navigate to a run's detail view; assert `TrustPanel` renders a named verification checklist; assert at least one check shows pass/fail badge; assert a failing check renders a `href="#clm_NNN"` anchor. Run on static export fixture. | Playwright test green; `TrustPanel` present in DOM; verification checklist check items present; one failing check anchor asserted | 0.25 pts | ui-engineer-enhanced | sonnet | adaptive | Phase 4 complete |

#### AC P5-E2E-W2-1: Runtime Smoke — P3 Target Surfaces
- target_surfaces:
    - frontend/runs-viewer/src/screens/RunDetailScreen.tsx
    - frontend/runs-viewer/src/components/TrustPanel/TrustPanel.tsx
    - frontend/runs-viewer/src/components/TrustPanel/VerificationChecklist.tsx
- propagation_contract: E2E test navigates to RunDetailScreen; asserts TrustPanel is visible in the rendered DOM; asserts VerificationChecklist renders check items
- resilience: If TrustPanel absent or checklist empty, test fails explicitly (not silently)
- visual_evidence_required: false
- verified_by: [P5-E2E-W2]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P5-E2E-W3 | E2E smoke: W3 report chip navigation | Playwright test: navigate to a run's report overlay tab; assert at least one `[claim:clm_NNN]` chip is rendered in the report; click the chip; assert `ProvenanceModal` opens with claim data. Run on static export fixture. | Playwright test green; report chip present; clicking chip opens ProvenanceModal dialog in DOM | 0.25 pts | ui-engineer-enhanced | sonnet | adaptive | Phase 4 complete |

#### AC P5-E2E-W3-1: Runtime Smoke — P4 Target Surfaces
- target_surfaces:
    - frontend/runs-viewer/src/screens/RunDetailScreen.tsx
    - frontend/runs-viewer/src/components/ReportOverlay/ReportOverlay.tsx
    - frontend/runs-viewer/src/components/ReportOverlay/ClaimChip.tsx
    - frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx
    - frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx
    - frontend/runs-viewer/src/components/LineageGraph/LineageGraph.tsx
- propagation_contract: E2E test navigates ReportOverlay tab; finds ClaimChip elements; clicks one; asserts ProvenanceModal is visible; optionally asserts SourceCard visible in modal
- resilience: If LineageGraph tab absent (should-have not built), test skips that assertion; not a test failure
- visual_evidence_required: false
- verified_by: [P5-E2E-W3]

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P5-E2E-W1 | E2E smoke: W1 claim audit (2-click) | Playwright test: navigate to claim ledger view; click the first claim row in `ClaimLedgerTable`; assert `ProvenanceModal` opens; assert at least one `SourceCard` is visible with a non-empty quote section. Measure: ≤ 2 UI interactions from ledger to quote. Run on static export fixture. | Playwright test green; ProvenanceModal opens; SourceCard with quote section visible; interaction count ≤ 2 asserted | 0.25 pts | ui-engineer-enhanced | sonnet | adaptive | Phase 4 complete |
| P5-PROVENANCE-CORRECT | Provenance correctness test | Python + pytest (or Node.js) test: parse `report_draft.md` for all `[claim:clm_NNN]` patterns; for each, assert the `clm_NNN` exists as a key in the export `run.json` `claims[]` array; for supported claims, assert at least one entry in `sources[]` with non-empty `quote`. | Test passes for `rf_run_20260613_*` fixture; every `[claim:clm_NNN]` tag in `report_draft.md` resolves; no orphaned chip references | 0.25 pts | ui-engineer-enhanced | sonnet | adaptive | Phase 4 complete |
| P5-BUILD | Static SPA build pipeline | Wire the static SPA build: (1) pre-build script runs `rf run export --all` and writes `run.json` files to `frontend/runs-viewer/public/data/`; (2) `vite build` compiles to `frontend/runs-viewer/dist/`; (3) build output can be served as a standalone SPA. Add `npm run build:runs-viewer` to project scripts. | `npm run build:runs-viewer` runs cleanly; `dist/` contains `index.html` and assets; no TypeScript errors in build; pre-build export step runs without error on a local runs corpus | 0.25 pts | ui-engineer-enhanced | sonnet | adaptive | Phase 4 complete |

---

## Task Table — Documentation Track (parallel)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P5-ADR | ADR: read path + read-only invariant | `backend-architect` authors ADR at `docs/dev/architecture/adr-runs-read-path.md`. Decision: static export as primary read path (loopback API deferred to OQ-6). Constraints recorded: (1) R9 sensitivity invariant — filter at export layer, never in component; (2) read-only architectural invariant — GET-only serving, zero form elements, no mutation methods in API client; (3) `FoundryPaths.discover()` path derivation invariant (no stored absolute paths). Status: accepted. | ADR exists at target path; all three invariants documented; R9 sensitivity invariant explicitly named; status: accepted | 0.25 pts | backend-architect | sonnet | adaptive | Phase 4 complete |
| P5-README | README CLI reference | `documentation-writer` updates `README.md` CLI reference section: add `rf run export --json [--run-id ID | --all]` and `rf run list --json` sub-command documentation with examples. Keep concise (usage + example only, no prose). | README has CLI reference for both commands; examples correct and runnable; update is ≤ 20 lines | 0.25 pts | documentation-writer | haiku | adaptive | Phase 4 complete |
| P5-CHANGELOG | CHANGELOG [Unreleased] entry | `changelog-generator` adds entry to CHANGELOG `[Unreleased]` section. Category: `Added`. Entry covers: `rf run export --json` and `rf run list --json` CLI commands; runs frontend SPA (static build mode); provenance drill-down (two-click claim audit); verification checklist view; run corpus portfolio view. Follow Keep A Changelog format. Set `changelog_ref: CHANGELOG.md` in plan frontmatter. | CHANGELOG `[Unreleased]` has entry; correct `Added` category; 4–6 bullet items covering the major deliverables; `changelog_ref` set | 0.25 pts | changelog-generator | haiku | adaptive | Phase 4 complete |

---

## Task Table — Deferred Items + Frontmatter (sequential, after parallel tracks)

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| P5-DOC-OQ4 | Design spec: auth/LAN (OQ-4) | Author `docs/project_plans/design-specs/runs-auth-lan.md` with `doc_type: design_spec`, `maturity: idea`, `prd_ref` pointing to the runs-frontend PRD. Capture: what OQ-4 asks, why it was deferred (loopback-only sufficient for v1, no confirmed LAN use case), and what trigger condition would promote it. | Design spec exists at target path; maturity: idea; prd_ref set; deferred rationale documented | 0.25 pts | documentation-writer | sonnet | adaptive | P5-ADR |
| P5-DOC-OQ6 | Design spec: loopback live-browse API (OQ-6) | Author `docs/project_plans/design-specs/runs-loopback-api.md` with `doc_type: design_spec`, `maturity: idea`, `prd_ref` set. Capture: FR-11 scope, why deferred (static export sufficient for current cadence), trigger condition (operator identifies real live-browse JTBD), and the `RUNS_FRONTEND_LOOPBACK_API` feature flag status. | Design spec exists at target path; captures FR-11 scope and deferral rationale; maturity: idea | 0.25 pts | documentation-writer | sonnet | adaptive | P5-ADR |
| P5-DOC-FR13 | Design spec: writeback preview cards (FR-13) | Author `docs/project_plans/design-specs/runs-writeback-preview.md` with `doc_type: design_spec`, `maturity: idea`, `prd_ref` set. Capture: FR-13 scope (writeback-review governance view, approved_for_writeback gate), deferral reason (low traversal value for v1 operator workflows), and promotion trigger. | Design spec exists at target path; FR-13 scope documented; maturity: idea | 0.25 pts | documentation-writer | sonnet | adaptive | P5-ADR |
| P5-DOC-FR14 | Design spec: run context panels (FR-14) | Author `docs/project_plans/design-specs/runs-context-panels.md` with `doc_type: design_spec`, `maturity: idea`, `prd_ref` set. Capture: FR-14 scope (routing decision card, research brief, swarm plan, upstream entity panels), deferral reason (secondary metadata value; not on W1/W2/W3 critical path), and promotion trigger. | Design spec exists at target path; FR-14 scope documented; maturity: idea | 0.25 pts | documentation-writer | sonnet | adaptive | P5-ADR |
| P5-FRONTMATTER | Plan frontmatter finalization | Update `docs/project_plans/implementation_plans/features/runs-frontend-v1.md` frontmatter: set `status: completed`, populate `commit_refs` with implementation commits, populate `files_affected` with the full affected file list, update `updated` date, set `deferred_items_spec_refs` to the four design spec paths from P5-DOC-OQ4 through P5-DOC-FR14, set `changelog_ref: CHANGELOG.md`. | Plan frontmatter complete per CCDash lifecycle spec; all four deferred_items_spec_refs populated; no null fields that should be populated | 0.25 pts | documentation-writer | haiku | adaptive | P5-DOC-FR14, P5-CHANGELOG |

---

## Phase 5 Parallel Execution

```
Phase 4 complete
      │
      ├── E2E + Build track (ui-engineer-enhanced):
      │     P5-E2E-W2 ∥ P5-E2E-W3 ∥ P5-E2E-W1 ∥ P5-PROVENANCE-CORRECT ∥ P5-BUILD
      │
      ├── Documentation track (parallel):
      │     P5-ADR (backend-architect)
      │     P5-README (documentation-writer, haiku)
      │     P5-CHANGELOG (changelog-generator, haiku)
      │
      └── After parallel tracks:
            P5-DOC-OQ4 → P5-DOC-OQ6 → P5-DOC-FR13 → P5-DOC-FR14 → P5-FRONTMATTER
            (sequential within deferred-items sub-track; all after P5-ADR)
      │
      task-completion-validator P5 review
      karen feature-end review
```

---

## Reviewer Gates (Phase 5 Only)

| Gate | Reviewer | Blocks |
|------|----------|--------|
| P5 phase quality gates all pass | `task-completion-validator` | karen review |
| Feature end: all phases complete, deferred specs authored, frontmatter final | `karen` | PR merge + feature guide authoring |

---

## Key Files Affected

- `tests/e2e/test_w1_claim_audit.py` (or `.spec.ts`) (new)
- `tests/e2e/test_w2_verification.py` (or `.spec.ts`) (new)
- `tests/e2e/test_w3_report_nav.py` (or `.spec.ts`) (new)
- `tests/test_provenance_correctness.py` (new)
- `docs/dev/architecture/adr-runs-read-path.md` (new)
- `CHANGELOG.md` (updated)
- `README.md` (updated)
- `docs/project_plans/design-specs/runs-auth-lan.md` (new)
- `docs/project_plans/design-specs/runs-loopback-api.md` (new)
- `docs/project_plans/design-specs/runs-writeback-preview.md` (new)
- `docs/project_plans/design-specs/runs-context-panels.md` (new)
- `docs/project_plans/implementation_plans/features/runs-frontend-v1.md` (frontmatter update)
- `frontend/runs-viewer/package.json` (build script addition)
- `frontend/runs-viewer/vite.config.ts` (build pipeline wiring)

---

## Phase 5 Notes

- **R-P4 coverage**: All P3 and P4 `target_surfaces` are covered by the E2E smoke tasks. The `LineageGraph` (should-have) is included in P5-E2E-W3-1's `target_surfaces` with a graceful skip if not built.
- **CHANGELOG requirement**: `changelog_required: true` is set in the plan frontmatter (inherited from the PRD). DOC-001 equivalent = P5-CHANGELOG. The `changelog_ref` frontmatter field must be set before feature close.
- **karen gate**: The feature-end `karen` review runs after all P5 quality gates pass. `karen` reads the git diff, Completion Reports from each phase's `task-completion-validator` reviews, and the plan frontmatter. Review output is the go/no-go for PR merge.
- **Feature guide**: After `karen` passes, `documentation-writer` (haiku) authors `.claude/worknotes/runs-frontend/feature-guide.md` as the Wrap-Up step before the PR is opened.
