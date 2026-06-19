---
type: progress
schema_version: 2
doc_type: progress
prd: "runs-frontend"
feature_slug: "runs-frontend"
phase: 4
title: "Flagship — Claim Ledger + Report Overlay"
status: "pending"
created: 2026-06-19
updated: 2026-06-19
prd_ref: "docs/project_plans/PRDs/features/runs-frontend-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/runs-frontend-v1.md"
commit_refs: []
pr_refs: []
started: null
completed: null

overall_progress: 0
completion_estimate: "on-track"

total_tasks: 12
completed_tasks: 0
in_progress_tasks: 0
blocked_tasks: 0

owners: ["ui-engineer-enhanced"]
contributors: ["frontend-developer"]

execution_model: batch-parallel

model_usage:
  primary: "sonnet"
  external: []

tasks:
  # Claim Ledger sub-track (ui-engineer-enhanced)
  - id: "P4-LEDGER-TABLE"
    description: "Implement ClaimLedgerTable.tsx: tabular display of all clm_NNN entries with status/confidence/materiality badges; row click triggers onClaimSelect(claimId); each row has id=clm_NNN anchor"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P2-HOOKS"]
    estimated_effort: "0.5 pts"
    assigned_model: "sonnet"
    model_effort: "extended"

  - id: "P4-LEDGER-FACETS"
    description: "Implement LedgerFacets.tsx: facets for status/materiality/claim_type/confidence; each facet updates visible claims in ClaimLedgerTable; multi-facet AND logic"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4-LEDGER-TABLE"]
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P4-SOURCE-CARD"
    description: "Implement SourceCard.tsx: trust badge, source-type icon, usage-permission pills, expandable verbatim quote; sensitivity gate: work_sensitive quote→redaction placeholder (R9 defense-in-depth)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P2-TS-CODEGEN"]
    estimated_effort: "0.75 pts"
    assigned_model: "sonnet"
    model_effort: "extended"

  - id: "P4-MODAL"
    description: "Implement ProvenanceModal.tsx: opens on onClaimSelect(claimId); renders claim text+status, sources[] as SourceCards; inference modal shows from_claims chain; empty from_claims→RIB-018 warning; ≤2 clicks to verbatim quote"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4-LEDGER-TABLE", "P4-SOURCE-CARD"]
    estimated_effort: "1.5 pts"
    assigned_model: "sonnet"
    model_effort: "extended"

  - id: "P4-SENS-001"
    description: "UI-level sensitivity test: using synthetic fixture from P1-SENS-001, verify SourceCard renders redaction placeholder (not quote) for work_sensitive; public content does appear"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4-SOURCE-CARD"]
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "extended"

  # Report Overlay sub-track (frontend-developer — parallel)
  - id: "P4-REPORT-MD"
    description: "Implement ReportRenderer.tsx: renders report_draft.md as Markdown; transforms [claim:clm_NNN] patterns to interactive chips calling onClaimSelect; Inference/Speculation sentences color-coded"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P2-HOOKS"]
    estimated_effort: "0.75 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P4-REPORT-SIDEBAR"
    description: "Implement CompositionSidebar.tsx: shows % supported/inference/speculation from evidence_bundle.counts; click on category dims non-matching chips in report"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P4-REPORT-MD"]
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P4-REPORT-OVERLAY"
    description: "Implement ReportOverlay.tsx: composes ReportRenderer + CompositionSidebar two-column layout; wires onClaimSelect to ProvenanceModal.open(); run detail tabs between TrustPanel and ReportOverlay"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P4-REPORT-SIDEBAR"]
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  - id: "P4-LINEAGE"
    description: "Adapt ArtifactLineageGraph from MeatyWiki Portal: SVG DAG showing source_card→extraction_card→claim_ledger_entry→evidence_bundle→report chain with verdict badges; graceful empty-state (should-have)"
    status: "pending"
    assigned_to: ["frontend-developer"]
    dependencies: ["P2-TS-CODEGEN"]
    estimated_effort: "0.75 pts"
    assigned_model: "sonnet"
    model_effort: "adaptive"

  # Seam + Vitest (ui-engineer-enhanced; after both tracks)
  - id: "P4-SEAM-001"
    description: "Seam task: (1) ReportRenderer chip click→ProvenanceModal.open(claimId) contract; (2) sensitivity-gate boundary: work_sensitive source card in modal shows redaction placeholder"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4-REPORT-OVERLAY", "P4-MODAL", "P4-SENS-001"]
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "extended"

  - id: "P4-VITEST-INFERENCE"
    description: "Unit test ProvenanceModal with inference claim: non-empty from_claims=[clm_010,clm_022]→linked chain renders; empty from_claims=[]→inference unsupported warning renders (RIB-018 class)"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4-MODAL"]
    estimated_effort: "0.25 pts"
    assigned_model: "sonnet"
    model_effort: "extended"

  - id: "P4-VITEST"
    description: "Full P4 Vitest suite: claim ledger render, facet filter, provenance modal open/close, inference chain, RIB-018 warning, source card sensitivity, report chip click triggers modal, composition sidebar filter"
    status: "pending"
    assigned_to: ["ui-engineer-enhanced"]
    dependencies: ["P4-SEAM-001", "P4-VITEST-INFERENCE"]
    estimated_effort: "0.5 pts"
    assigned_model: "sonnet"
    model_effort: "extended"

parallelization:
  batch_1:
    - "P4-LEDGER-TABLE"
    - "P4-SOURCE-CARD"
    - "P4-REPORT-MD"
    - "P4-LINEAGE"
  batch_2:
    - "P4-LEDGER-FACETS"
    - "P4-MODAL"
    - "P4-SENS-001"
    - "P4-REPORT-SIDEBAR"
  batch_3:
    - "P4-REPORT-OVERLAY"
    - "P4-VITEST-INFERENCE"
  batch_4: ["P4-SEAM-001"]
  batch_5: ["P4-VITEST"]
  critical_path: ["P4-LEDGER-TABLE", "P4-MODAL", "P4-SEAM-001", "P4-VITEST"]
  estimated_total_time: "3-4 days"

blockers: []

success_criteria:
  - "Claim ledger table renders all clm_NNN entries with status/confidence/materiality badges"
  - "Facets (status, materiality, claim_type, confidence) filter correctly"
  - "Provenance drill-down modal resolves claim→sources[]→verbatim quote in ≤2 clicks from fixture"
  - "Inference claim (status: inference) modal shows from_claims basis chain; empty from_claims (RIB-018 class) flagged as warning"
  - "Source card sensitivity gate: work_sensitive body content absent from rendered output (R9 gate — must pass)"
  - "Report overlay renders report_draft.md Markdown with working [claim:clm_NNN] chips"
  - "Inference and Speculation sentences color-coded by claim status"
  - "Composition sidebar shows % supported/inference/speculation with click-to-filter"
  - "Lineage graph panel (should-have): renders with correct node types; graceful empty-state if absent"
  - "Seam task P4-SEAM-001 passes: report-chip→modal open contract and sensitivity-gate boundary verified"
  - "Vitest tests green for drill-down/inference/sensitivity"
  - "task-completion-validator P4 phase review passed"
---

# runs-frontend - Phase 4: Flagship — Claim Ledger + Report Overlay

**YAML frontmatter is the source of truth for tasks, status, and assignments.** Do not duplicate in markdown.

```bash
python .claude/skills/artifact-tracking/scripts/update-status.py -f .claude/progress/runs-frontend/phase-4-progress.md -t P4-LEDGER-TABLE -s completed --force
```

---

## Objective

Highest-value and highest-novelty phase: delivers the two-click claim audit (W1 flagship) via claim ledger table and provenance drill-down modal, plus the report overlay with live `[claim:clm_NNN]` chips. The claim-graph join is pre-computed in P1 export service; Phase 4 only handles UI presentation logic. H3 algorithmic flag fires for inference-chain walkability (RIB-018 false-pass class) and sensitivity-gate rendering in the source card terminus.

---

## Parallel Execution Structure

- **Batch 1 (parallel)**: ui-engineer-enhanced (P4-LEDGER-TABLE, P4-SOURCE-CARD) ∥ frontend-developer (P4-REPORT-MD, P4-LINEAGE)
- **Batch 2 (parallel)**: ui-engineer-enhanced (P4-LEDGER-FACETS, P4-MODAL, P4-SENS-001) ∥ frontend-developer (P4-REPORT-SIDEBAR)
- **Batch 3 (parallel)**: frontend-developer (P4-REPORT-OVERLAY) ∥ ui-engineer-enhanced (P4-VITEST-INFERENCE)
- **Sequential after both tracks**: P4-SEAM-001 → P4-VITEST (both ui-engineer-enhanced)

## Integration Owner

`ui-engineer-enhanced` — owns `ClaimLedger` types, `ProvenanceModal`, and the `[claim:clm_NNN]` modal trigger interface shared between tracks.

---

## Reviewer Gate

| Reviewer | Trigger | Blocks |
|----------|---------|--------|
| `task-completion-validator` | Drill-down works; sensitivity fixture test passes; seam task passes | P5 start |
