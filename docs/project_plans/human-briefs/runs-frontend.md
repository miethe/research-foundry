---
schema_name: ccdash_document
schema_version: 2

doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans

id: BRIEF-runs-frontend
title: "Research Foundry Runs Frontend v1 — Human Brief"
status: draft
category: human-briefs

feature_slug: runs-frontend
feature_family: runs-frontend
feature_version: v1

prd_ref: docs/project_plans/PRDs/features/runs-frontend-v1.md
plan_ref: docs/project_plans/implementation_plans/features/runs-frontend-v1.md
intent_ref: null
epic_ref: null

related_documents:
  - docs/project_plans/exploration/runs-frontend/runs-frontend-feasibility-brief.md
  - docs/project_plans/exploration/runs-frontend/runs-frontend-charter.md
  - .claude/worknotes/runs-frontend/decisions-block.md

owner: nick
contributors: []

audience: [humans]

priority: high
confidence: 0.84

created: 2026-06-19
updated: 2026-06-19
target_release: ""

tags: [human-brief, runs-frontend, provenance, viewer]
---

# Research Foundry Runs Frontend v1 — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-06-19

---

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/features/runs-frontend-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/features/runs-frontend-v1.md`
- **Phase files**:
  - `docs/project_plans/implementation_plans/features/runs-frontend-v1/phase-1-export-contract.md`
  - `docs/project_plans/implementation_plans/features/runs-frontend-v1/phase-2-data-layer.md`
  - `docs/project_plans/implementation_plans/features/runs-frontend-v1/phase-3-read-surfaces.md`
  - `docs/project_plans/implementation_plans/features/runs-frontend-v1/phase-4-flagship.md`
  - `docs/project_plans/implementation_plans/features/runs-frontend-v1/phase-5-testing-build-docs.md`
- **Decisions Block**: `.claude/worknotes/runs-frontend/decisions-block.md`
- **Feasibility Brief (GO verdict, confidence 0.84)**: `docs/project_plans/exploration/runs-frontend/runs-frontend-feasibility-brief.md`
- **Exploration Charter**: `docs/project_plans/exploration/runs-frontend/runs-frontend-charter.md`
- **SPIKEs**: `docs/project_plans/exploration/runs-frontend/spikes/`
- **Design Specs (deferred; authored in P5)**: `docs/project_plans/design-specs/runs-auth-lan.md`, `docs/project_plans/design-specs/runs-loopback-api.md`, `docs/project_plans/design-specs/runs-writeback-preview.md`, `docs/project_plans/design-specs/runs-context-panels.md`

---

## 2. Estimation Sanity Check

**Bottom-up total**: 14 pts (sum of 4+3+2+4+1), trimmed to 13 lean
**Top-down anchor**: IntentTree Web (the fork source) with a Python export contract added
**Reconciliation**: The 13-pt lean is justified by optimistic P3 reuse (IntentTree panels are ~70% direct-adaptation). P1 carries the 3–5 point variance band (the algorithmic export service is the least-certain estimate). The reconciled band from the feasibility brief §3 is 8–21 pts; 13 is the lean of that band. If P1 iterates on the schema after P2 starts, add 2–4 pts.

**H1 (noun-counting)**: Zero new database tables. This is a file-backed read-only viewer with no ORM entities. H1 does not apply as a floor.

**H2 (dual-implementation multiplier)**: Not applicable. No Python repository layer, no dual-edition split. The export service is a single implementation.

**H3 (algorithmic flag)**: **Fires twice.**
- P1 export service: claim-graph **join** (claim → source_card_id → YAML → extracted_points[].quote) + status **derivation** (evidence_bundle + verification + artifact presence) = H3 flag. Budgeted at 4 pts for P1; integration test + sensitivity redaction correctness test included.
- P4 provenance modal: inference chain **resolution** (`from_claims` walkable chain) + sensitivity-gate **rendering** = H3 flag (lighter). Budgeted at 1.5 pts for ProvenanceModal with `effort: extended`.

**H4 (bundle-vs-sum)**:

| Capability Area | Independent Est. | Notes |
|-----------------|-----------------|-------|
| Python export contract (P1) | 4 pts | Two new CLI sub-commands + export service (algorithmic, H3) |
| Data layer / TS fork (P2) | 3 pts | Fork wiring + codegen + hooks; mostly mechanical |
| Run list + trust panel (P3) | 2 pts | Direct IntentTree adaptations; ~70% reuse |
| Claim ledger + report overlay (P4) | 4 pts | Net-new provenance modal + inference chain + chip wiring |
| E2E + build + docs (P5) | 1 pt | Mechanical hardening; ADR is the only judgment item |
| **Sum** | **14 pts** | Trimmed 1 pt for optimistic P3 reuse → 13 lean |

Bundle sum = 14 pts floor. Locked at 13 with written justification (P3 reuse optimism). Justified.

**H5 (anchor)**: The closest comparable is IntentTree Web itself — the fork source. IntentTree Web was built as a Tier 2 feature. The delta is the Python export contract (net-new; no analog in IntentTree) and the provenance modal (net-new UI logic). These two deltas account for ~7 pts of the 13. The remaining ~6 pts are fork-and-adapt reuse (high confidence anchor match).

**H6 (plumbing budget)**: ~15% of 14 pts = ~2 pts implicit. In this plan, plumbing is absorbed into: P1's OQ-2/OQ-3 resolution tasks (0.5+0.5), P2's TS codegen setup (1 pt), P5's build pipeline wiring (0.25 pt). Not a separate line item — distributed into the phases where the actual work sits.

---

## 3. Wave & Orchestration Notes

**Critical path**: P1 → P2 → P3 → P4 → P5 (strictly serial at phase boundaries). The export contract schema (P1-SCHEMA-FREEZE) is the single hardest dependency in the feature. Nothing in P2 may begin until it is merged.

**Parallel opportunities**:
- Inside P3: run list track (ui-engineer-enhanced) ∥ trust panel track (frontend-developer) — disjoint component files, shared types
- Inside P4: claim ledger + provenance modal (ui-engineer-enhanced, `extended`) ∥ report overlay + lineage graph (frontend-developer, `adaptive`) — disjoint file sets
- Inside P5: E2E ∥ README ∥ CHANGELOG ∥ ADR — all independent; deferred design specs run after ADR

**Merge order**: No branch merges during Phases 2–4 (single `frontend/runs-viewer/` directory, additive). P1 merges before P2 starts. P5 merges after all tasks complete and `karen` signs off.

**Cross-feature coupling**: None active. IntentTree Web running on `agentic-nuc` (`:8032`) is unaffected — the fork creates a separate directory (`frontend/runs-viewer/`). MeatyWiki `ArtifactLineageGraph` is copy-adapted, not imported from MeatyWiki's live package.

**Budget**: 5 phases × ~25–30K tokens each = ~125–150K token budget estimate. P4 is the heaviest single phase (net-new provenance logic + two parallel tracks + seam task).

---

## 4. Open Questions Ledger

| ID | Source | Question | Status | Resolved By |
|----|--------|----------|--------|-------------|
| OQ-1 | PRD §12 | What is the exact `run.json` shape — flat or denormalized claim-graph? | Decided: denormalized (claim carries resolved sources[]) | P1-SCHEMA-FREEZE — first P1 task |
| OQ-2 | PRD §12 | Define the derived-status enum from `evidence_bundle.status` + `verification.passed` | Decided: planned → sources_ingested → extracted → claim_mapped → synthesized → verified → published | P1-STATUS-001 |
| OQ-3 | PRD §12 | Sensitivity threshold config — default `public`-only? | Decided: yes, `public`-only default; `foundry.yaml` viewer key configurable | P1-SENS-CONFIG |
| OQ-4 | PRD §12 | Auth/LAN exposure model for post-v1 | Deferred — loopback-only sufficient for v1 | P5-DOC-OQ4 (design spec) |
| OQ-5 | PRD §12 | `@miethe/ui` compatibility with IntentTree fork peer deps? | Open — resolved at P2 start (P2-AUDIT-OQ5) | P2-AUDIT-OQ5 |
| OQ-6 | PRD §12 | Static export vs. loopback live-browse API (FR-11) | Deferred — static export is primary; FR-11 behind feature flag | P5-DOC-OQ6 (design spec) |
| OQ-7 | PRD §12 / decisions block | Schema-version mismatch warning surface | Partial: stderr during export (P1); optional viewer badge in P3 | P3-SCHEMA-BADGE |

---

## 5. Deferred Items Rationale

- **OQ-4 (auth/LAN)**: Loopback-only binding is mandatory for v1 (no confirmed multi-device use case). Auth design would be premature without a real use case driving the security model. Promote when an operator confirms they need LAN access from a second device.
- **OQ-6 (loopback live-browse API / FR-11)**: The "browse runs as they land during an active swarm" JTBD has not been validated as a real pain point. Static export rebuilds are cheap (< 5 seconds for the current ~40-run corpus). Promote if operator identifies live-browse as a genuine workflow bottleneck post-v1.
- **FR-13 (writeback preview cards)**: The writeback governance posture (approved_for_writeback gate, destination badge) has low traversal value compared to the core W1/W2/W3 workflows. The operator's primary use of the viewer is trust-gate and auditor roles, not writeback review. Promote when writeback workflows mature and the operator wants integrated visibility.
- **FR-14 (run context panels)**: Upstream entity panels (routing decision card, research brief, swarm plan) are metadata that the operator currently skips in most post-run audits. Secondary value; the breadcrumb/badge pattern is the right approach but not urgent for v1. Promote if post-v1 user feedback confirms context panels reduce run review time.

---

## 6. Risk Narrative

**R9 — Sensitivity / Governance Leakage** (High severity — the one risk that produces real harm):
Treating this as a defense-in-depth problem: sensitive content is absent from the export JSON (P1 gate); the SourceCard component additionally checks the `sensitivity` field before rendering any quote (P4). Two independently-tested gates. The ADR records the invariant: the export/serve layer is the canonical gate, never a component. If the P1-SENS-001 test fails, the P1 gate must not be cleared. If the P4-SENS-001 test fails, P4 must not be cleared.

**OQ-1 — Schema Freeze Risk** (High severity — foundation risk):
The plan's single biggest schedule risk. If the export schema shape changes after P2 begins, every TypeScript type and hook must be regenerated and every component that uses entity fields must be audited. The mitigation (schema freeze as explicit P2 gate dependency) is the load-bearing mechanism. Don't let anyone rationalize "just a small schema change" post-P2 start — it's a multi-day rework event.

**OQ-5 — @miethe/ui Incompatibility** (Medium severity):
If the OQ-5 audit finds a peer-dep conflict, the v1 path is to use IntentTree's existing card/panel components. This is a fallback that was pre-accepted in the decisions block and the PRD — it does not block v1. The risk is discovering this in P4 (too late); the mitigation is the P2-AUDIT-OQ5 task being the second task in Phase 2, before any component work begins.

**R7 — Scope Creep to Write Mode** (Medium severity, High likelihood):
The viewer will display `reviewer_notes`, `required_fix`, and `approved_for_writeback` fields visually. The natural pressure to "just add an edit button" is high. The mitigation is architectural — GET-only serving, no form elements in any component, no mutation methods in the API client — all enforced in the P2 and P4 gate reviews. The ADR records this as a first-class constraint.

---

## 7. What to Watch For

- **P1 gate pressure to start P2 early**: The export service is the most technically interesting part for a Python engineer; there may be pressure to start frontend scaffolding while the schema is still in flux. Hold the line — a schema change after P2-TS-CODEGEN runs is a day of churn.
- **OQ-5 result timing**: If the audit finds an incompatibility, it needs to be communicated to the P3 subagent before P3 begins (not discovered mid-P3). P2-AUDIT-OQ5 must complete before P3 dispatch.
- **P4 provenance modal scope**: The modal is the feature's core complexity. Watch for scope creep into "interactive annotation" or "flag claim for review" features — these violate the read-only invariant and were explicitly deferred.
- **Lineage graph (should-have)**: P4-LINEAGE is explicitly should-have. If it runs long, drop it from v1 and add to the FR-14 design spec. The feature ships without it.
- **`tsc --noEmit` as a P2 gate**: Don't let an agent skip the TypeScript clean check at P2 exit — the types are the contract for P3 and P4; silent `any` at boundaries propagates into hard-to-debug render failures downstream.

---

## 8. Expected Success Behaviors

Post-ship, the operator should be able to do all of the following without opening any file manually:

- [ ] Open the runs frontend (static SPA at `frontend/runs-viewer/dist/`) and see all RF run cards including the 4 nested `runs/runs/` runs that were previously invisible to flat discovery
- [ ] Click a run card and see the trust panel with a named, per-check verification checklist (pass/fail/warning) within 10 seconds
- [ ] Click a failing verification check and land on the offending claim in the claim ledger
- [ ] Click a claim ledger row and see the verbatim supporting quote with locator in the provenance modal (≤ 2 interactions)
- [ ] See an RIB-018-class inference (empty `from_claims`) flagged as a visible warning in the provenance modal
- [ ] Open the report overlay and click any `[claim:clm_NNN]` chip to open the provenance modal
- [ ] See `**Inference:**` and `**Speculation:**` sentences color-coded in the report overlay
- [ ] Confirm that `work_sensitive` source card content is not visible anywhere in the UI (governance invariant)
- [ ] Build the static SPA fresh with `npm run build:runs-viewer` (which runs `rf run export --all` as a pre-step) and see the updated run corpus reflected

---

## 9. Running Log

- [2026-06-19] Brief created. GO verdict from pre-commitment exploration (confidence 0.84). Decisions block authored by Opus. Implementation plan authored by implementation-planner (sonnet). 5 phases; 13 pts lean.
