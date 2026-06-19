---
type: context
schema_version: 2
doc_type: context
prd: "runs-frontend"
feature_slug: "runs-frontend"
title: "Runs Frontend v1 — Development Context"
status: "active"
created: 2026-06-19
updated: 2026-06-19
prd_ref: "docs/project_plans/PRDs/features/runs-frontend-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/runs-frontend-v1.md"
commit_refs: []
pr_refs: []

critical_notes_count: 4
implementation_decisions_count: 5
active_gotchas_count: 2
agent_contributors: []

phase_status:
  - phase: 1
    status: not_started
  - phase: 2
    status: not_started
  - phase: 3
    status: not_started
  - phase: 4
    status: not_started
  - phase: 5
    status: not_started

decisions:
  - id: "DECISION-1"
    question: "What is the sole data source for the frontend?"
    decision: "rf run export --json produces a denormalized run.json; frontend reads only static JSON files or loopback GET endpoints."
    rationale: "No LLM on the recall path; sensitivity filter applied at export layer; deterministic and auditable."
    tradeoffs: "Requires a pre-build export step; live-browse JTBD deferred to OQ-6."
    location: "docs/project_plans/implementation_plans/features/runs-frontend-v1.md"
    phase: 1

  - id: "DECISION-2"
    question: "Which SPA is forked as the frontend base?"
    decision: "Fork IntentTree Web into frontend/runs-viewer/; entity model swap AgentRun→RFRun; preserve React+Vite+React Query+Tailwind."
    rationale: "~60% code reuse; same team familiarity; avoids greenfield scaffold cost."
    tradeoffs: "Must audit @miethe/ui compatibility (OQ-5) before component work begins."
    location: "docs/project_plans/implementation_plans/features/runs-frontend-v1/phase-2-data-layer.md"
    phase: 2

  - id: "DECISION-3"
    question: "How are TypeScript types generated?"
    decision: "json-schema-to-typescript (or quicktype) build step generates TS interfaces from all 20 schemas/*.schema.yaml files into frontend/runs-viewer/src/types/rf/."
    rationale: "Single source of truth (YAML schemas); no manual type files at entity boundaries; optional fields automatically marked ?."
    tradeoffs: "Codegen must run before any component work; schema changes require re-running codegen."
    location: "docs/project_plans/implementation_plans/features/runs-frontend-v1/phase-2-data-layer.md"
    phase: 2

  - id: "DECISION-4"
    question: "How does the R9 sensitivity gate work?"
    decision: "Sensitivity filter applied at export layer (P1 export service) before writing run.json. Frontend SourceCard additionally checks sensitivity field as defense-in-depth but sensitive content should never reach the JSON."
    rationale: "Prevents any component from bypassing the gate by reading sensitive content. Default threshold: public-only (foundry.yaml viewer.sensitivity_threshold, defaulting to public)."
    tradeoffs: "If sensitivity field absent on a quote entry, treated as public (safe default — renders, not redacted)."
    location: "docs/project_plans/implementation_plans/features/runs-frontend-v1/phase-1-export-contract.md"
    phase: 1

  - id: "DECISION-5"
    question: "OQ-5: Use @miethe/ui or IntentTree's existing components?"
    decision: "Pending P2-AUDIT-OQ5. Preferred: @miethe/ui cards/modals if compatible. Fallback: IntentTree's own panel/card components for v1, @miethe/ui adoption post-v1."
    rationale: "Must resolve before P3 component work begins so component vocabulary is settled."
    tradeoffs: "If incompatibility found, IntentTree components serve as interim vocabulary; does not block P3."
    location: ".claude/worknotes/runs-frontend/oq5-decision.md (to be created in P2-AUDIT-OQ5)"
    phase: 2

gotchas:
  - id: "GOTCHA-1"
    title: "P1-SCHEMA-FREEZE is an explicit dependency of EVERY Phase 2 task"
    description: "The export schema doc at docs/dev/architecture/rf-run-export-schema.md must be authored, reviewed by backend-architect, and merged before any P2 task begins. This dependency propagates transitively to all P3+ tasks. Do not begin any Phase 2 work without confirming this doc is merged."
    solution: "Check that P1-SCHEMA-FREEZE task is status=completed and the file exists at the documented path before dispatching any P2 tasks."
    severity: "critical"
    affects: ["phase-2", "phase-3", "phase-4", "phase-5"]

  - id: "GOTCHA-2"
    title: "Derived status vs. run.yaml.status — stale status is a known data quality issue"
    description: "run.yaml.status can be stale. The export service must compute status_derived from evidence_bundle.status + verification.passed + artifact presence — never from run.yaml.status. rf run list --json must also return status_derived, not the stored field."
    solution: "P1-STATUS-001 implements the derived-status enum. The integration test (P1-INT-TEST) covers the stale-status case. Validate against a known stale-status run during P1-INT-TEST."
    severity: "high"
    affects: ["phase-1"]

blockers: []
---

# Runs Frontend v1 — Development Context

## Key Invariants (Never Break These)

### P1 Hard Gate

Phase 1 is the hard upstream gate. **No Phase 2+ task may begin until ALL of the following are true:**

1. `rf run export --json` produces valid `run.json` for `rf_run_20260613_*` real run
2. Export schema frozen and merged at `docs/dev/architecture/rf-run-export-schema.md`
3. `backend-architect` schema review sign-off recorded
4. Sensitivity redaction test (P1-SENS-001) passes — R9 gate
5. Integration round-trip test (P1-INT-TEST) green
6. `task-completion-validator` P1 phase review passed

**`P1-SCHEMA-FREEZE` is an explicit dependency on every Phase 2 task.** Check its completion status before dispatching any P2 work.

---

### IntentTree Web Fork + @miethe/ui Approach

- **Fork target**: IntentTree Web → `frontend/runs-viewer/`
- **Entity swap**: `AgentRun` → `RFRun`
- **Preserve**: React + Vite + React Query + Tailwind config, router shell, layout components, Vitest config, `tsconfig.json`
- **Component vocabulary**: Determined by P2-AUDIT-OQ5. Preferred: `@miethe/ui` cards/modals. Fallback: IntentTree's own components.
- **OQ-5 decision recorded at**: `.claude/worknotes/runs-frontend/oq5-decision.md` (created in P2-AUDIT-OQ5)
- **Key rule**: P2-AUDIT-OQ5 must complete before any P3 component work begins.

---

### R9 Sensitivity Gate

**Invariant**: Sensitivity filter is applied at the export/serve layer, never in the component.

- **Export service** (P1): Any `extracted_points[].sensitivity` value other than `public` (i.e., `work_sensitive`, `client_sensitive`) is redacted from the output `run.json`.
- **SourceCard** (P4): Defense-in-depth check — if `sensitivity` field is `work_sensitive` or `client_sensitive`, render a redaction placeholder even if the quote is somehow present.
- **Default threshold**: `public`-only via `foundry.yaml` `viewer.sensitivity_threshold` key (defaults to `public` when absent).
- **Safe default**: If `sensitivity` field is absent on a quote entry, treat as `public` (renders, not redacted).
- **This invariant is recorded in the ADR** authored in P5-ADR.

Gate tasks that must pass: **P1-SENS-001** (P1 export test) and **P4-SENS-001** (UI-level test).

---

## Document Pointers

| Document | Path |
|----------|------|
| PRD | `docs/project_plans/PRDs/features/runs-frontend-v1.md` |
| Implementation Plan | `docs/project_plans/implementation_plans/features/runs-frontend-v1.md` |
| Decisions Block | `.claude/worknotes/runs-frontend/decisions-block.md` |
| Export Schema (to be authored in P1) | `docs/dev/architecture/rf-run-export-schema.md` |
| OQ-5 Decision (to be authored in P2) | `.claude/worknotes/runs-frontend/oq5-decision.md` |
| ADR: Read Path (to be authored in P5) | `docs/dev/architecture/adr-runs-read-path.md` |
| Phase 1 Progress | `.claude/progress/runs-frontend/phase-1-progress.md` |
| Phase 2 Progress | `.claude/progress/runs-frontend/phase-2-progress.md` |
| Phase 3 Progress | `.claude/progress/runs-frontend/phase-3-progress.md` |
| Phase 4 Progress | `.claude/progress/runs-frontend/phase-4-progress.md` |
| Phase 5 Progress | `.claude/progress/runs-frontend/phase-5-progress.md` |

---

## Deferred Items

| Item | Trigger for Promotion | Target Spec |
|------|-----------------------|-------------|
| OQ-4: Auth/LAN exposure | Active operator need for LAN exposure confirmed | `docs/project_plans/design-specs/runs-auth-lan.md` |
| OQ-6: Loopback live-browse API | Operator identifies real live-browse JTBD; static export rebuild too slow | `docs/project_plans/design-specs/runs-loopback-api.md` |
| FR-13: Writeback preview cards | v1 ships; claim-audit workflow covers >80% daily use | `docs/project_plans/design-specs/runs-writeback-preview.md` |
| FR-14: Run context panels | Post-v1 feedback confirms context panels reduce run review time | `docs/project_plans/design-specs/runs-context-panels.md` |

All four design specs are authored in **P5** (P5-DOC-OQ4 through P5-DOC-FR14).
