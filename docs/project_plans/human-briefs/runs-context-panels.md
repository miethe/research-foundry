---
schema_name: ccdash_document
schema_version: 2

doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans

id: BRIEF-runs-context-panels
title: "Runs Viewer — Run Context Panels (FR-14) — Human Brief"
status: draft
category: human-briefs

feature_slug: runs-context-panels
feature_family: runs-context-panels
feature_version: v1

prd_ref: docs/project_plans/PRDs/features/runs-context-panels-v1.md
plan_ref: docs/project_plans/implementation_plans/features/runs-context-panels-v1.md
intent_ref: null
epic_ref: null

related_documents:
  - docs/project_plans/design-specs/runs-context-panels.md
  - docs/dev/architecture/rf-run-export-schema.md
  - .claude/worknotes/runs-context-panels/decisions-block.md
  - docs/project_plans/PRDs/features/runs-frontend-v1.md

owner: nick
contributors: []

audience: [humans]

priority: medium
confidence: 0.82

created: 2026-06-23
updated: 2026-06-23
target_release: ""

tags: [human-brief, runs-viewer, context-panels, fr-14, schema]
---

# Runs Viewer — Run Context Panels (FR-14) — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-06-23

---

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/features/runs-context-panels-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/features/runs-context-panels-v1.md`
- **Design Spec**: `docs/project_plans/design-specs/runs-context-panels.md`
- **Decisions Block**: `.claude/worknotes/runs-context-panels/decisions-block.md` (authoritative scaffold; OQ-1 resolved here)
- **Frozen Schema Contract**: `docs/dev/architecture/rf-run-export-schema.md`
- **SPIKEs**: None — SPIKE waived (design spec settled approach; clean H5 anchor exists)
- **Related Briefs**: `docs/project_plans/human-briefs/runs-frontend.md`, `docs/project_plans/human-briefs/runs-loopback-api.md`

---

## 2. Estimation Sanity Check

_Migrated from decisions block §4. Human-authored; not agent-relevant._

**Bottom-up total**: 15 pts
**Top-down anchor**: `run-metadata-enrichment` (~16–20 pts actual) is the closest comparable feature (schema + derivation + backfill + creation-path + faceting + FE). FR-14 is the read-only subset of that feature's surface area.
**Reconciliation**: Bottom-up 15 pts vs. top-down "12–15 pts" intuition — aligned. The +2 delta vs. the "~13 pt minimum" intuition reflects the governance gate overhead (backend-architect re-review) and the R9 redaction extension, both of which add real bounded work not present in simpler schema bumps.

H1–H6 heuristic application (bottom-up, per decisions block §4):

- **H1 (noun-counting)**: One new schema key (`context`) with 4 sub-objects. No new CRUD-with-RBAC tables. H1 floor contribution: low (~1 pt for schema plumbing). The work is predominantly FE component authoring and export wiring, not relational entity management.

- **H2 (dual-implementation multiplier)**: Does NOT apply. This feature touches `export_service.py` (single Python module, no local/enterprise split on this path) and FE panel components (single implementation). No repository-layer dual-impl required.

- **H3 (algorithmic flag)**: Does NOT fire. The swarm_plan tree view is presentation, not computation — no dependency resolution, graph traversal, cycle detection, or ranking logic in the implementation. The two-level tree cap (OQ-3) further removes recursion risk. This is the key confirmation that no SPIKE was required.

- **H4 (bundle decomposition)**: 4 capability areas independently estimated:

  | Capability Area | Independent Est. | Notes |
  |----------------|-----------------|-------|
  | P1: Schema & Contract | 3 pts | +1 pt governance overhead vs. anchor P1 |
  | P2: Export Wiring & Redaction | 4 pts | 4 heterogeneous source files (yaml/md/yaml/ids) + redaction extension |
  | P3: FE Context Panels | 6 pts | 4 panels; 2 reused renderers (MD + lineage-tree style); no faceting |
  | P4: Tests, Docs & Validation | 2 pts | Narrower surface than anchor P8 (no backfill, no creation-path tests) |
  | **Σ** | **15 pts** | floor = plan total; no compression |

- **H5 (anchor reference)**: `run-metadata-enrichment` (~16–20 pts, features: schema + derivation + backfill + creation-path + faceting + FE). FR-14 subtracts: derivation, backfill, creation-path, faceting (≈ −6 to −8 pts). Adds: governance gate + redaction extension (≈ +2 pts). Net: **15 pts** — within ±30% of the 16 pt anchor floor. Delta documented and justified (decisions block §4).

- **H6 (hidden plumbing budget)**: ~2 pts absorbed into P1/P4 — TS types, schema-doc stub+final, CHANGELOG, backward-compat assertion, structured error handling. This is ~13% of subtotal, within the 15–20% guideline. No separate plumbing line item needed at this size.

**Locked estimate**: 15 pts. Bottom-up sum = plan total; no compression below floor.

---

## 3. Wave & Orchestration Notes

**Critical path**: P1 (schema + governance gate) → P2 (export wiring) → P3 (FE panels) → P4 (karen)
**Key bottleneck**: P1 backend-architect re-review. This is the only uncontrollable wait in the plan. Initiate the review request at P1 start, not at P1-004 completion. Include the field contract + backward-compat assertion in the initial PR draft.

**Parallel opportunities**:
- **P3-scaffold ∥ P2**: After P1 completes, FE stubs panel shells against P1 TS types while P2 wires export. Saves 0.5–1 day on the P3 critical path.
- **4-panel batch within P3**: `RoutingDecisionPanel`, `ResearchBriefPanel`, `SwarmPlanPanel`, `UpstreamEntitiesPanel` are independent files → execute as a single parallel batch.
- **Within P1**: Schema-doc stub authoring ∥ Python schema + TS type definitions.

**ICA delegation**: P2 (export wiring) and P4 test-authoring sub-tasks are bounded and well-specified → ICA free-tier candidate (`~/ica-claude.sh`). P1 (schema design + governance) and P3 (FE integration) stay on native agents (higher integration sensitivity). All authoritative gates (pytest, tsc, backend-architect, karen) re-run in-session.

**Merge order**: P1 (schema frozen) → P2 (export) → P3 (FE) → P4 (seal). Each phase merges to branch, not main. Final merge to main after karen feature-end gate.

**Cross-feature coupling**: None currently in-flight. `runs-loopback-api-v1` is shipped and available; this feature does not depend on it running (embed option chosen). Schema 1.3 bump should be coordinated to ensure no concurrent schema change is in flight — verify with backend-architect at P1 gate.

---

## 4. Open Questions Ledger

| ID | Source | Question | Status | Resolved By |
|----|--------|----------|--------|-------------|
| OQ-1 | PRD §12; Decisions Block | Delivery mechanism: embed `context` in `run.json` at export time (Option A) vs. lazy-load via loopback API (Option B)? | **RESOLVED — Option A (embed)** | Decisions Block: offline-SPA invariant + single redaction seam; lazy-load deferred to v2 as DFR-001 |
| OQ-2 | Decisions Block §7 | Exact mechanism for "collapsed by default, persists per-session" — sessionStorage key scheme and reset semantics? | **RESOLVED** | Plan §Design Decisions: `rf:context-panel:${runId}:${panelId}` in sessionStorage; resets on page reload |
| OQ-3 | Decisions Block §7 | Concrete tree node model + render-depth cap + raw-YAML escape hatch for SwarmPlanPanel; lineage-graph component reuse vs. lighter list? | **RESOLVED** | Plan §Design Decisions: typed `SwarmPlanNode` interface; 3-level depth cap; raw-YAML escape hatch; new lighter list-based tree (no MeatyWiki code import) |
| OQ-4 | Decisions Block §7 | If P3 detail pushes plan >800 lines, split P3 into P3a/P3b? | **RESOLVED — no split** | Plan stays under 800 lines with unified structure; P3 panels execute as parallel file-owned batch within single phase |
| OQ-5 | Decisions Block §7 | Redaction policy: reuse existing R9 rules or add field-specific rules (e.g., always-redact source URLs in research_brief)? | **RESOLVED** | Plan §Design Decisions: reuse existing R9 rules; one extension — source URLs + `sensitivity: work_sensitive` text in `research_brief_md` also redacted; implementation owner verifies against policy doc in P2 |

---

## 5. Deferred Items Rationale

- **DFR-001 — v2 lazy-load optimization via loopback API**: Deferred from OQ-1 resolution. The embed approach (Option A) is correct for v1 because the viewer must work offline and embedding keeps sensitivity redaction in a single deterministic pass. The lazy-load path (loopback API `GET /runs/{run_id}/context`) would add a second redaction surface and break the offline-SPA invariant. Promote DFR-001 when: (a) `run.json` median file size exceeds 500 KB in practice, OR (b) operator feedback specifically requests live-refresh of context data without re-exporting. Design spec authored in P4 DOC-006 at `docs/project_plans/design-specs/runs-context-panels-lazy-load-v2.md`.

---

## 6. Risk Narrative

- **Frozen-schema governance gate (Risk 1 — HIGH)**: The P1 backend-architect re-review is the only non-parallelizable blocking dependency outside of code. A 1-day delay here cascades into the full timeline. Mitigate by initiating the review at P1 start with a well-formed PR draft (field contract + backward-compat assertion + OQ-1 rationale). The additive+optional nature of the `context` key should make this a quick approval — but never skip it, as it's the governance control that prevents export contract regressions.

- **Sensitive content in `context.*` fields (Risk 2 — MEDIUM-HIGH)**: This is the decisive reason OQ-1 resolved to embed (not lazy-load). Embedding guarantees redaction happens in the existing single export-time R9 pass. The extension to cover `context.*` fields must be tested per-sub-object (BE-003). Watch for `research_brief.md` source URLs and routing rationale text that may contain governed content not currently in scope of the R9 pass.

- **Offline static-viewer regression (Risk 3 — MEDIUM)**: The panel components must never assume `context` is always present. The R-P2 resilience ACs (one per sub-object) and the TEST-SMOKE pre-1.3 scenario are the verification controls. If TEST-SMOKE scenario 2 or 3 fails at P3 exit, do not pass the gate.

- **SwarmPlanPanel tree complexity (Risk 4 — LOW-MEDIUM)**: The OQ-3 resolution caps this by: typed interface, 3-level depth cap, raw-YAML escape hatch. The main risk is discovering that real `swarm_plan.yaml` structures from actual runs have variable shapes not covered by `SwarmPlanNode`. Mitigate by testing against 2–3 real run fixtures in P3-003 unit tests, not just synthetic fixtures.

---

## 7. What to Watch For

- **P1 gate delay**: If backend-architect re-review hasn't responded by end of day 2 of P1, escalate. Do not let P2 wait more than 1 extra day without a gate decision.
- **`ibom_id`/`intenttree_node_id` field location**: Assumption is `run.yaml` top-level. Verify before writing P2-001. If these IDs are absent from `run.yaml` or stored differently, Panel 4 must degrade gracefully — do not error, do not hard-code paths.
- **sessionStorage key collision**: Ensure the `rf:context-panel:${runId}:${panelId}` scheme is unique enough to avoid collisions with other sessionStorage keys already in use by the viewer.
- **research_brief.md frontmatter**: Real research briefs may have YAML frontmatter that the Markdown renderer would display as raw text. The P3-002 implementation must strip frontmatter before passing to the renderer. Catch this in the unit test fixture.
- **karen milestone (P3 exit)**: This is a mid-feature gate, not just a rubber-stamp. karen checks the offline-SPA invariant and schema governance. Have the TEST-SMOKE results and backward-compat assertion ready as evidence when karen runs.

---

## 8. Expected Success Behaviors

_Observable, human-verifiable outcomes after ship. Not agent acceptance criteria._

- [ ] Open any run exported with schema 1.3: four collapsed panels ("Routing Decision", "Research Brief", "Swarm Plan", "Upstream Entities") appear below the existing trust panel in the run-detail view.
- [ ] Expand "Routing Decision": model profile name, routing rationale, estimated vs. budget cost, and sensitivity tier are visible without a CLI round-trip.
- [ ] Expand "Research Brief": `research_brief.md` renders as formatted Markdown with the same visual style as the report overlay.
- [ ] Expand "Swarm Plan": a two-level collapsible tree shows adapters at the top level and steps within each adapter, with cost columns.
- [ ] Expand "Upstream Entities": `intent_id`, `ibom_id`, `intenttree_node_id` render as badge links (or plain-text badges when offline).
- [ ] Open a pre-1.3 run (or a run exported without context): all four panels show "Context not available for this run" empty-state — no JS errors, no blank panels.
- [ ] Close the browser tab and re-open the run in the same session: previously expanded panels remain expanded.
- [ ] Open the viewer from the offline static export (no `rf serve` running): all panels work from `run.json` data alone.
- [ ] `rf run export --json` on a new run produces a `run.json` with `"schema_version": "1.3"` and a populated `context` block (or `"context": null` if source artifacts are absent).
- [ ] Existing viewer views (claim ledger, governance block, report overlay) are visually and functionally unchanged after the schema 1.3 bump.

---

## 9. Running Log

_Append-only. Short notes during execution — surprises, pivots, validated assumptions._
_Agents may append here only if explicitly instructed in a task prompt._

- 2026-06-23: Human brief created. Decisions block authored by Opus. Implementation plan and human brief scaffolded. OQ-1 resolved (embed). OQ-2 through OQ-5 resolved in plan design-decisions section.
