# Runs-Viewer v2.2 Polish — Epic Brief (Opus decisions scaffold)

> Working file for plan authoring. NOT a deliverable. Source of truth for all child-plan
> authoring agents: read this + your assigned template + your target file pointers, then author.
> Do NOT re-explore the codebase — every fact below is verified (file:line). Author from these facts.
> Date: 2026-06-20 | Author: Nick Miethe (via Opus orchestration)

---

## 0. Epic framing

**Epic**: `runs-viewer-v2.2-polish` — finish the runs-viewer facelift. Many v2.1 items shipped
by codex are partial; plus new requests (item modals, audit highlight/filter state machine,
sticky report header, un-redaction for LAN, a run linked-metadata model, surfacing more run data,
and enabling the disabled tabs).

**App context**: read-only React SPA at `frontend/runs-viewer`, deployed LAN-only at
`10.42.10.76:3030`. Data is a **static export**: `prebuild-static-data.mjs` runs `rf run export --all`,
copies `runs/<id>/run.json` → `public/data/<id>/run.json` + `public/data/index.json`; Vite bundles it.
Viewer is read-only; it never mutates RF data. (`client.ts` also supports an optional loopback API.)

**Audience for child docs**: ai-agents + developers. Tier-appropriate (see §3).

### 0.1 Shared concerns (apply to every child plan)

1. **Static re-export discipline.** Any backend export field change requires re-running
   `rf run export --all` + `pnpm --filter runs-viewer build` (prebuild reruns export). Plans that
   add export fields MUST include a "re-export + rebuild static data" task. Deploy via the manual
   UI-only path (reset --hard + `pnpm build` + restart `research-foundry-ui.service`) or the bootstrap.
2. **Export-threading is explicit, not spread.** `export_service.py:export_run()` (lines ~417-436)
   builds the run.json dict field-by-field. New `run.yaml` fields are NOT auto-included; each must be
   threaded explicitly into the export dict, then into `index.json` summary (if needed on list views),
   then into the hand-written TS types `frontend/runs-viewer/src/types/rf/run-export.ts`.
3. **Frontend types are hand-written** (`run-export.ts`), not codegen'd from the export. Keep them in
   sync manually unless a codegen step is added (proposed in the metadata-enrichment plan).
4. **R-P1 multi-surface rule (mandatory).** Any AC that says "everywhere / all pages / all cards /
   surface X across the app" MUST enumerate explicit `target_surfaces:` component paths. The canonical
   viewer surfaces are listed in §1.9 — copy the relevant subset into each AC.
5. **R-P2 resilience.** Every new backend/export field gets an implicit AC: "FE renders gracefully when
   the field is absent/null" (older runs won't have it until re-exported). State this per field.
6. **Reviewer gates** per tier (Tier 1 → task-completion-validator at sprint end; Tier 2/3 →
   task-completion-validator per phase + karen at feature end).
7. **No Mode D here.** Un-redaction touches governance config but it is the operator's own LAN data,
   explicitly authorized, and recoverable (unredacted source-of-truth persists in `runs/*/sources/*.md`).
   Treat as normal Tier 1, but note the re-export overwrites run.json atomically (safe, recoverable).

### 0.2 Child deliverables & sequencing

| # | Slug | Tier | Doc(s) | Depends on |
|---|------|------|--------|-----------|
| E0 | `runs-viewer-v2.2-polish-epic` | epic | PRD-style epic (index) | — |
| F1 | `nav-titles-lineage-fixes` | 1 | Feature Contract | — (can start now) |
| F2 | `item-modal-expansion` | 1 | Feature Contract | F1 (default-tab/title helpers) — soft |
| F3 | `audit-highlight-filter-and-sticky-report` | 1 | Feature Contract | — |
| F4 | `viewer-unredact-lan` | 1 | Feature Contract | — |
| F5 | `run-metadata-enrichment` | 3 | PRD + Implementation Plan | F1 (title in summary) — soft |
| G | `enable-disabled-viewer-tabs-epic` | epic | PRD-style sub-epic (index) | F5 (some tabs need enriched export) |
| G1..G6 | `viewer-tab-{swarm,policies,alerts,library,settings,help}` | 1 each | Feature Contract | G, F5 (data-dependent) |

Critical path: F5 (data model) is the long pole and unblocks several disabled tabs (Swarm/Policies/Alerts/
Library read enriched export data). F1–F4 are independent FE-mostly fixes that can run in parallel now.

---

## 1. Verified current-state intel (cite these; do not re-derive)

### 1.1 Shell & navigation — `frontend/runs-viewer/src/app/AppShell.tsx`
- `NAV_ITEMS` (lines ~24-35): enabled/contextual = Portfolio (always → `/runs`), Runs (contextual:
  `resolveTarget()` returns `/runs/:runId` if a run is selected else `/runs`), Reports (contextual),
  Ledger (contextual). **Hard-disabled ('not implemented')**: Library, Swarm, Policies, Alerts,
  Settings, Help.
- `isActiveNav()` (lines ~105-111): Portfolio active when `pathname === '/runs'`; Runs active when
  `routeRunId` truthy and view ∈ {null, overview, trust, lineage, writeback}.

### 1.2 Portfolio / list / titles — `screens/RunList.tsx`, `components/RunList/RunCard.tsx`, `lib/runs.ts`
- Portfolio (`RunList.tsx:154` `.rv-portfolio`) renders StatusLanes + RunCards. Display uses
  `run.run_id` directly (RunCard.tsx:163; StatusLane RunList.tsx:~429). **No readable title rendered.**
- Clicking a card → `onClick` → `setModalRunId(runId)` (RunList.tsx:~333-336) opens `RunDetailModal`.
- `deriveRunTitle()` exists `lib/runs.ts:193-202` (from report_draft H1 / context.research_brief_md /
  intent_id slug / fallback run_id) but needs full `RFRunExport`; **not available in list** because
  `RFRunSummary` lacks report_draft/intent_id. `titleFromSlug()` at `lib/runs.ts:245-254` works on run_id.
- `RFRunSummary` = `{run_id, status_derived, created_at?, sensitivity?, claim_counts?}` (run-export.ts).
- `index.json` summary shape = `{run_id, status_derived, created_at, sensitivity, claim_counts}`
  (`prebuild-static-data.mjs`).

### 1.3 Detail tabs & default tab — `components/RunDetail/detailTabs.ts`, `RunDetailWorkspace.tsx`, `RunDetailModal.tsx`, `screens/RunDetail.tsx`
- `DetailTab` = `overview | trust | ledger | report | lineage | writeback` (alias `audit`→`ledger`).
- `coerceDetailTab(null)` returns **`'trust'`** (detailTabs.ts:8) → **page mode defaults to Trust** (bug).
  Modal mode defaults to `'overview'` (RunDetailModal.tsx:23) → inconsistent.
- Tabs array RunDetailWorkspace.tsx:34-45; `writeback` disabled when `!writebackAvailable && activeTab!=='writeback'` (line 42).
- **USER DECISION: default tab must be Overview** (both page and modal). Fix `coerceDetailTab` fallback
  to `'overview'`; keep modal at `'overview'`.

### 1.4 Run-click "changes nav point but doesn't go there" (routing bug)
- Symptom: clicking a run updates the active nav highlight (Runs becomes active via selectedRunId) but
  the user does not land on the run. In portfolio, card click opens a modal (`setModalRunId`); the
  perceived "nav changed but didn't go" is the seam between selectedRunId state (drives `isActiveNav`)
  and the actual modal-open / route. **Desired**: clicking a run reliably (a) opens the run modal
  (primary), AND (b) provides an explicit "open full page" affordance (RunDetailModal already has an
  'Open full page' Link at RunDetailModal.tsx:94). Implementer must reproduce, then make click → modal
  deterministic and ensure nav highlight matches actual location. Likely a missing navigate() or a
  state-only update without route change in the list/lineage/audit card click paths.

### 1.5 Item detail + modal infra — `components/RunDetail/RunDetailModal.tsx`, `components/ProvenanceModal/ProvenanceModal.tsx`, side panes `LineageDetailPanel.tsx`, `ClaimAuditWorkbench.tsx` (ClaimInspector)
- Reusable overlay pattern: `role="dialog" aria-modal`, Escape + backdrop-click close. `ProvenanceModal`
  is ref-based (`{open(claimId), close()}`), supports `stacked` (z-index layering) + `onOpenChange`
  (suppress parent Escape while child open). `RunDetailModal` stacks ProvenanceModal.
- Side panes: lineage = `LineageDetailPanel` (selection-driven, `onOpenProvenance` callback);
  audit = `ClaimInspector` inside `ClaimAuditWorkbench` (has an 'Open modal' button → `onOpenModal(claim_id)`).
- **Gaps**: no double-click on RunCard / lineage rows / ledger rows; no expand/fullscreen button on
  `LineageDetailPanel` (lineage nodes have no modal path — ProvenanceModal is claim-only); RunCard has
  no expand button.
- Seam to add modal expansion: a generic `<DetailModal stacked>` (mirroring ProvenanceModal overlay)
  that accepts a claim OR a lineage node payload; double-click + explicit expand-button handlers wired
  through: RunCard, LineageList rows → LineageGraph → workspace; ClaimLedgerTable rows + ClaimInspector.

### 1.6 Lineage tree edges (BUG) — `components/LineageGraph/LineageFlow.tsx` + `lineageFlowElements.ts` + `lineageLayout.ts` + `lineageTree.ts`
- Graph view uses React Flow v12 (`@xyflow/react`), horizontal L→R tree. List view (`LineageList.tsx`)
  works (CSS guide lines).
- **Root cause**: `LineageFlow.tsx` passes `nodeTypes` (defined module-scope ~line 166-168) to
  `<ReactFlow>` but does **NOT** pass `edgeTypes`. Edges ARE built correctly by `buildFlowElements`
  (`type:'smoothstep'`, stroke color from targetKind accent, `ArrowClosed` marker, strokeWidth 2,
  opacity .85) and unit tests pass (lineageFlowElements.test.ts). React Flow v12 won't render
  `smoothstep` edges unless the edge type is registered.
- **Fix (high-confidence)**: `import { SmoothStepEdge } from '@xyflow/react'`; define
  `const edgeTypes: EdgeTypes = { smoothstep: SmoothStepEdge }` at module scope; pass
  `edgeTypes={edgeTypes}` to `<ReactFlow>`. Add a render-level test/smoke confirming edge `<path>`
  elements appear. Optionally add `className: 'rv-lineage-edge'` + CSS.
- Tree derives from `RFRunExport.claims[].sources` (run→source→extraction→claim→report/writeback);
  conceptually parent/child like intenttree nodes.

### 1.7 Audit tab + Report pane — `components/ClaimLedger/ClaimAuditWorkbench.tsx`, `LedgerFacets.tsx`, `ClaimLedgerTable.tsx`, `components/ReportOverlay/ReportRenderer.tsx`, `ClaimChip.tsx`, `CompositionSidebar.tsx`
- Audit = 3-pane grid (CSS ~2087): Ledger (facets + table) | Report (ReportRenderer) | ClaimInspector.
- Report pane title `h3 'Report' + status` is rendered **inside** the scrolling `.rv-audit-report`
  container (ClaimAuditWorkbench.tsx:92-96, body max-height 760 overflow auto). → must split into a
  sticky/locked header (title + run ID + run title) + a scrolling body (ReportRenderer only).
- `LedgerFacets` does AND-logic filtering of the **left table only** (applyFacets ~line 72); no report
  effect. Claim row click → `selectedClaimId` → ReportRenderer `activeClaimIds={Set([id])}`,
  `highlightMode='selected-claim'`, `highlightText=true`.
- `ReportRenderer` already supports `highlightMode: 'none' | 'composition' | 'selected-claim'` +
  `highlightText` (block dim/highlight via `rv-report-block--highlighted/--dimmed`); `[claim:clm_NNN]`
  → `ClaimChip` (props `dimmed` opacity .25, `selected` glow).
- **Desired state machine** (ClaimAuditWorkbench): track `activeFacets` + `selectedClaimId`.
  - facets active & no claim selected → compute union of matching claim IDs → `activeClaimIds`,
    `highlightMode='composition'` (highlight all matching in report; do NOT hide).
  - claim selected → `highlightMode='selected-claim'`, `activeClaimIds={Set([id])}` (filter to that one).
  - claim deselected while facets still active → revert to composition highlight-all.
  - no facets & no claim → `highlightMode='none'`.

### 1.8 Redaction — `src/research_foundry/services/export_service.py`, `foundry.yaml`, `config.py`, FE `components/SourceCard/SourceCard.tsx`, `lib/runs.ts`
- Backend: `REDACTION_MARKER='[redacted:sensitivity]'` (export_service.py:51). In `_resolve_source()`
  (~277-295): if `effective_rank > threshold_rank`, set `redacted=True`, replace quote+summary with
  marker. Sensitivity ranks: public=0, personal=1, work_sensitive=2, client_sensitive=3.
- Threshold precedence: CLI `--sensitivity-threshold` > `foundry.yaml viewer.sensitivity_threshold`
  (default `public`, foundry.yaml:~27-28) > `'public'`. `config.py` `viewer` property loads it.
- **Unredacted text is NOT in run.json once redacted** — only the marker. Source-of-truth unredacted
  values persist in `runs/<id>/sources/*.md` frontmatter (`extracted_points[].quote/summary`).
- FE display gate `SourceCard.tsx:27-35 isRedacted()` re-checks `source.sensitivity > sensitivityThreshold`
  (defense-in-depth). `lib/runs.ts:81-105`: `sourceExceedsThreshold`, `sourceHasRedactedText`,
  `shouldRedactSource`; `summarizeRunAttention` counts redactedSources.
- Type drift: `RFResolvedSource` TS interface is missing the `redacted: boolean` field the backend writes.
- **Show-all approach (LAN)**: set `foundry.yaml viewer.sensitivity_threshold: client_sensitive`,
  re-export all runs (`rf run export --all`), rebuild static data → run.json now carries full text;
  AND align FE gate (threshold passed to viewer so `isRedacted` returns false), add `redacted?: boolean`
  to type. Optionally a viewer env flag `VITE_SHOW_ALL=1` to force-bypass the display gate.

### 1.9 Canonical viewer surfaces (use for `target_surfaces:` enumeration)
- `frontend/runs-viewer/src/screens/RunList.tsx` (portfolio table + status lanes)
- `frontend/runs-viewer/src/components/RunList/RunCard.tsx`
- `frontend/runs-viewer/src/components/RunList/FilterTabs.tsx`
- `frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx` (Overview tab content)
- `frontend/runs-viewer/src/components/RunDetail/RunDetailModal.tsx`
- `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx` (ClaimInspector pane)
- `frontend/runs-viewer/src/components/ClaimLedger/ClaimLedgerTable.tsx`
- `frontend/runs-viewer/src/components/LineageGraph/LineageDetailPanel.tsx`
- `frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx`
- `frontend/runs-viewer/src/components/SourceCard/SourceCard.tsx`

### 1.10 Run data model & unsurfaced data — `types/rf/run-export.ts`, schemas, `runs/*/run.yaml`
- `RFRunExport` (schema 1.1, frozen): schema_version, run_id, intent_id?, created_at?, status_derived,
  status_raw?, sensitivity?, sensitivity_threshold?, claim_counts?, verification?, governance?,
  timeline?, claims[], artifact_schema_versions?, report_draft? (md w/ frontmatter; title required),
  context? (v2 optional: routing_decision, research_brief_md, swarm_plan, upstream_entities),
  writebacks? (v2 optional: targets[]{name,destination,status,url}, approved_for_writeback, notes).
- **Title** lives only in report_draft frontmatter (not a top-level field).
- **No project/category/tags/topic/domain** at run/export level. BUT `run.yaml` ALREADY has `project`
  (planning.py plan_run ~449-475: explicit arg > intent.project > raw_idea.suggested_project > 'unassigned').
- Unsurfaced data candidates worth visualizing: cost_usd / model profiles (run.yaml.profile:
  max_cost_usd, extraction/synthesis/verification_model_profile, max_runtime_minutes, freshness_days),
  routing_decision (context, often absent in 1.1), swarm plan + agents, source-count-by-type,
  confidence distribution, materiality distribution, freshness (research_brief max_age_days),
  writeback targets+status, unresolved_questions (in claim_ledger, not exported), audience
  (report frontmatter), governance approved_by/timestamp.

### 1.11 Backlog linkage — `backlog/research_idea_backlog.{yaml,schema.yaml}`, `seed_swarm_runs.sh`, `registries/run_index.yaml`
- 55 ideas (RIB-NNN) in 8 pillars. Idea fields incl.: id (slug), title, **pillar** (canonical category),
  status, research_question, **tags[]** (free-form), **suggested_project** (enum: Research Foundry |
  Agentic OS | unassigned), sensitivity, urgency, research_potential, desired_output, swarm_hint,
  governance (sensitivity, key_profile_allowed, requires_human_review, allowed_writebacks), intenttree
  (level, priority, dependencies, success_criteria, reusable_output_candidates), source_refs, rationale,
  **links** {raw_idea_id, intent_id, intenttree_node_id, **run_id**}.
- **Linkage is one-directional**: backlog idea → run via `links.run_id` (backfilled). Runs do NOT carry
  backlog_idea_id, tags, pillar, or suggested_project. `run_index.yaml` lacks them too.
- `seed_swarm_runs.sh`: one `rf capture`/plan per idea; passes research_question, tags (→ raw_idea.tags),
  sensitivity, governance; does NOT pass suggested_project.
- **Derivation**: invert `links.run_id` to build run→backlog map; backfill `linked_projects`
  (suggested_project + run.yaml.project), `category` (pillar/title), `tags` onto runs; thread to export.

### 1.12 Creation & serving — `services/planning.py:plan_run()`, `services/export_service.py`, `scripts/prebuild-static-data.mjs`, `api/client.ts`
- New run-metadata field path: run.yaml (populate in plan_run) → export_run() dict (explicit) →
  index.json summary (if list-visible) → `run-export.ts` types → UI. prebuild reruns `rf run export --all`
  so new export fields auto-appear in `public/data` on rebuild.
- No formal run.json JSON-schema file today (contract is in code; comment references
  `docs/dev/architecture/rf-run-export-schema.md`). Proposed: add formal export schema + TS codegen
  in the metadata-enrichment plan.

### 1.13 v2/v2.1 incomplete items to fold in (confirmed via specs + e2e)
- Portfolio title not displayed (F1). Default-tab inconsistency (F1). Report sticky header (F3).
- Composition highlight-text toggle UI missing; inference/speculation basis tooltips; dangling/redaction
  warning badges in ClaimInspector (fold into F3 polish or note as P1).
- 'This Week' filter disabled (no created_at window — now createable since created_at is in summary);
  'High Claim Volume' hardcoded 75 (data-driven). (Fold into F1 list polish as P1.)

---

## 2. Child plan specs

> Each block: author the named doc at the path using the named template. Frontmatter must follow the
> planning skill's field checklist. `feature_slug` is the slug. created: 2026-06-20. status: draft.
> owner: nick. Use Claude models (sonnet executor) unless noted. Enumerate `target_surfaces` per R-P1.

### E0 — Epic index  (doc_type: prd; title marks it EPIC)
- Path: `docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md`
- Template: prd-template.md (use as an EPIC: exec summary, problem, the 8 workstreams as a table with
  tier/status/dependencies, sequencing/critical path = §0.2, shared concerns = §0.1, success metrics,
  links to all child docs via `related_documents`). Keep ≤ 400 lines.
- Must list child paths (F1–F5, G + G1–G6) and the dependency graph. P0 = F1–F4 + F5 core
  (linked projects/categories/tags). P1 = F5 enrichment extras + disabled tabs.

### F1 — nav-titles-lineage-fixes  (Tier 1 Feature Contract)
- Path: `docs/project_plans/feature_contracts/harden-polish/nav-titles-lineage-fixes.md`
- Template: feature-contract-template.md. frontmatter `tier: 1`, `estimated_points: 7`, category harden-polish.
- Goal: fix the broken/missing basics so the viewer is trustworthy at a glance.
- Scope (in): (a) readable titles on Portfolio table, RunCard, StatusLane — add `title` to export +
  `index.json` summary + `RFRunSummary`, populate from report_draft frontmatter title (fallback
  `titleFromSlug(run_id)`); FE uses it with `deriveRunTitle`/`titleFromSlug` fallback chain.
  (b) Run-click reliably opens the run modal and nav highlight matches actual location; keep
  RunDetailModal 'Open full page' affordance (fix §1.4). (c) Default detail tab = Overview
  (coerceDetailTab fallback → 'overview'; modal stays 'overview'). (d) Lineage tree edges render
  (register `edgeTypes={{smoothstep: SmoothStepEdge}}` in LineageFlow.tsx per §1.6) + render-level test.
- Scope (out): item modals (F2), audit (F3), metadata model (F5).
- ACs (structured, with target_surfaces): title display across RunList.tsx + RunCard.tsx + (StatusLane in
  RunList.tsx); resilience = fallback to titleFromSlug when title absent (older runs). Default-tab AC.
  Run-click AC with reproduction. Lineage-edge AC with visual_evidence_required (graph screenshot
  showing connector lines) + render test.
- Key files: §1.1–1.4, §1.6. Backend touch: export_service.py (+title), prebuild index.json (+title),
  run-export.ts (RFRunSummary +title). Include "re-export + rebuild static data" task (§0.1.1).
- Risks: title fetch cost on list (mitigate: title in summary, not full export). React Flow edge API
  version drift (verify against installed @xyflow/react).
- P1 (optional, note only): data-driven High-Claim-Volume threshold; enable 'This Week' filter
  (created_at now present in summary).

### F2 — item-modal-expansion  (Tier 1 Feature Contract)
- Path: `docs/project_plans/feature_contracts/features/item-modal-expansion.md`
- Template: feature-contract-template.md. `tier: 1`, `estimated_points: 7`, category features.
- Goal: any clicked item (run card, lineage node, claim row) can be expanded to a full modal — via
  double-click AND an explicit expand/⤢ button — in BOTH list and side-pane contexts, in addition to
  the existing single-click side-pane detail.
- Scope (in): generic reusable `<DetailModal stacked>` (reuse ProvenanceModal overlay conventions:
  role=dialog, Escape, backdrop, stacked z-index, onOpenChange) accepting a claim OR lineage-node
  payload; double-click + expand-button handlers on RunCard, LineageList rows + LineageDetailPanel
  (expand → opens node modal), ClaimLedgerTable rows + ClaimInspector (expand → claim modal, reuse
  ProvenanceModal where it fits). Keep single-click = side pane (unchanged).
- Scope (out): new data; redaction; metadata.
- ACs (target_surfaces = RunCard.tsx, LineageList rows in LineageGraph, LineageDetailPanel.tsx,
  ClaimLedgerTable.tsx, ClaimAuditWorkbench ClaimInspector, ProvenanceModal.tsx). Keyboard: double-click
  + an 'expand' control; Escape ordering preserved when stacked. Resilience: expand on a node with no
  provenance still opens a sensible modal.
- Key files: §1.5. Risks: stacked-modal Escape/focus ordering; double-click vs single-click race
  (debounce/selection). FE-only.

### F3 — audit-highlight-filter-and-sticky-report  (Tier 1 Feature Contract)
- Path: `docs/project_plans/feature_contracts/harden-polish/audit-highlight-filter-and-sticky-report.md`
- Template: feature-contract-template.md. `tier: 1`, `estimated_points: 7`, category harden-polish.
- Goal: (a) Audit filter→highlight vs claim→filter state machine (§1.7); (b) lock the Report pane
  header (title + run ID + run title) into a sticky non-scrolling header with only the body scrolling.
- Scope (in): ClaimAuditWorkbench state machine (activeFacets + selectedClaimId → ReportRenderer
  highlightMode composition/selected-claim/none per §1.7); wire LedgerFacets to emit active-facet claim
  ID union to the report (currently filters left table only); deselect-returns-to-highlight; split
  `.rv-audit-report` into sticky `__header` + scrolling `__body` (move title/ID/title out of scroll).
  Add a 'clear selection' control in the sticky header.
- Scope (out): new claim data; the Report tab's separate ReportOverlay (only the AUDIT tab Report pane).
- ACs: state-machine AC (4 states enumerated); sticky-header AC (visual_evidence_required: scrolled
  screenshot showing header fixed); resilience: no facets/no claim → highlightMode none, all chips normal.
  target_surfaces: ClaimAuditWorkbench.tsx, LedgerFacets.tsx, ReportRenderer.tsx, ClaimChip.tsx + CSS.
- Key files: §1.7. Note: ReportRenderer already supports the modes — mostly wiring + CSS.
- P1 (note only): composition highlight-text toggle UI; inference/speculation basis hover tooltips;
  dangling/redacted warning badges in ClaimInspector.

### F4 — viewer-unredact-lan  (Tier 1 Feature Contract)
- Path: `docs/project_plans/feature_contracts/harden-polish/viewer-unredact-lan.md`
- Template: feature-contract-template.md. `tier: 1`, `estimated_points: 4`, category harden-polish.
- Goal: show ALL content (no `[redacted…]`) in the LAN-only personal viewer.
- Scope (in): set `foundry.yaml viewer.sensitivity_threshold: client_sensitive`; re-export all runs
  (`rf run export --all`) so run.json carries full quote/summary; rebuild static data; align FE display
  gate so `SourceCard.isRedacted` does not re-mask (pass the active threshold through to the viewer /
  add `VITE_SHOW_ALL` env bypass); add `redacted?: boolean` to `RFResolvedSource` TS type (fix drift).
- Scope (out): changing author-time governance/secret-scanning (governance.py stays — it's policy, not
  viewer redaction); making the viewer writeable.
- ACs: after re-export+rebuild, no `[redacted:sensitivity]` markers in any source quote/summary in the
  viewer (target_surfaces: SourceCard.tsx, ClaimInspector, ProvenanceModal); resilience: a run that was
  exported pre-change still shows markers until re-exported (document this). Verify unredacted truth
  exists in `runs/*/sources/*.md` before re-export.
- Risks: re-export overwrites run.json atomically (safe; recoverable from sources/*.md). Note this is
  the operator's own data, explicitly authorized — not Mode D.
- Key files: §1.8.

### F5 — run-metadata-enrichment  (Tier 3 → PRD + Implementation Plan)
- PRD path: `docs/project_plans/PRDs/features/run-metadata-enrichment-v1.md`
- Impl plan path: `docs/project_plans/implementation_plans/features/run-metadata-enrichment-v1.md`
  (split into phase files under `.../run-metadata-enrichment-v1/` if > 800 lines).
- Template: prd-template.md (PRD) + implementation-plan-template.md (plan). `risk_level: medium`,
  effort ~16-20 pts, Tier 3. changelog_required: true (user-facing viewer changes).
- Goal: give every run a first-class linked-metadata model — **Linked Projects (primary), Categories,
  Tags** — derived from the backlog where absent, populated at creation going forward, threaded through
  export, and surfaced **everywhere** in the viewer with Linked Projects as a primary list-view field;
  PLUS surface other high-value run data we already have but don't show (P1).
- Core (P0) scope:
  1. **Schema/model**: extend run.yaml with `linked_projects[]` (string slugs; seed from run.yaml.project
     + backlog suggested_project), `category` (backlog pillar/title), `tags[]` (from backlog/raw_idea),
     `backlog_idea_ref` (RIB-NNN) + `backlog_idea_id` (reverse link). Add formal run-export JSON schema
     file + optional TS codegen for `run-export.ts` (kills hand-sync drift; §1.12).
  2. **Derivation + backfill migration**: invert backlog `links.run_id` → write metadata onto existing
     runs (run.yaml and/or a derived `backlog_context.yaml` per run + `run_index.yaml`). Non-destructive,
     idempotent, dry-run-able. (§1.11)
  3. **Creation path**: `plan_run()` populates the new fields going forward; `seed_swarm_runs.sh`/
     `rf capture` pass `--backlog-idea-ref` so future runs carry linkage. (§1.12)
  4. **Export threading**: thread the fields into `export_service.export_run()` dict + `index.json`
     summary (Linked Projects/category/tags needed on list views); bump export schema_version; add to
     `RFRunSummary` + `RFRunExport` TS types. (§0.1.2)
  5. **Viewer display (R-P1 — enumerate target_surfaces from §1.9)**: Linked Projects as a PRIMARY
     column/field on RunList table + RunCard + StatusLane; category + tags chips on RunCard, RunDetail
     Overview, RunDetailModal header, ClaimInspector/LineageDetailPanel where relevant. Resilience
     (R-P2): every surface renders gracefully when fields absent (pre-migration runs).
  6. **Filtering/faceting**: filter Portfolio by linked project / category / tag (extend FilterTabs +
     RunList filter state).
- P1 scope (same plan, later phases): surface additional run data (§1.10) — cost/model profiles,
  source-count-by-type, confidence + materiality distributions, freshness, writeback targets+status,
  unresolved_questions, routing/swarm context, audience — threaded via the same export pattern and shown
  in Overview enrichment widgets. Note dependency: several disabled tabs (G) consume these enriched fields.
- Phasing (suggested, for impl plan): P1 schema+codegen → P2 derivation/backfill → P3 creation →
  P4 export+types → P5 viewer display (Linked Projects primary + chips everywhere) → P6 filtering →
  P7 enrichment extras (P1 data) → P8 tests + docs (CHANGELOG, README, viewer docs, run-export schema doc).
- Opus decisions block: author `.claude/worknotes/run-metadata-enrichment/decisions-block.md` first
  (phase boundaries, agent routing, risk hotspots, estimation anchors, dependency map, model routing),
  then expand via implementation-planner. (Authoring agent for the plan should produce both the
  decisions-aligned plan and the Estimation Sanity Check in a human brief if ≥8 pts — it is, so create
  `docs/project_plans/human-briefs/run-metadata-enrichment.md` too.)
- Risks: dual-write (run.yaml vs run_index vs derived file) consistency; backfill correctness on slug
  matching; export schema_version compatibility for older static bundles; "everywhere" surface sprawl
  (mitigate with target_surfaces + a runtime smoke task per R-P4); migration must be reversible.

### G — enable-disabled-viewer-tabs-epic  (sub-epic index; doc_type prd)
- Path: `docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md`
- Template: prd-template.md (as sub-epic). Enumerate the 6 hard-disabled top-level nav tabs (Library,
  Swarm, Policies, Alerts, Settings, Help) + note writeback detail-tab is conditional (enabled by F5
  writeback-status data, not here). Per-tab row: data source, scope, tier, dependency on F5, AC summary,
  child contract path. Link children via related_documents. Sequencing: Settings + Help first (cheap,
  no data dep); Swarm/Policies/Alerts/Library after F5 export enrichment.

### G1..G6 — per-tab Feature Contracts (Tier 1 each; concise, ~150-250 lines)
- Template: feature-contract-template.md, `tier: 1`, category features, owner nick, status draft.
  Each: goal, data source (cite §1.10/§1.11/governance.py), in/out scope, ACs (target_surfaces incl.
  AppShell.tsx NAV_ITEMS enable + new screen/route + route registration in app/routes.tsx), resilience
  (graceful empty state when data absent), risks, dependency on F5 where data-driven.
- G1 `viewer-tab-swarm.md` (path features/): Swarm tab — visualize swarm_plan + agents + routing_decision
  per run (needs F5 export of context.swarm_plan/routing). est 5.
- G2 `viewer-tab-policies.md`: Policies tab — governance/key profiles/policy rules + per-run governance
  (sensitivity, approved_for_writeback, allowed_writebacks, requires_human_review); source governance.py
  + run governance block. est 5.
- G3 `viewer-tab-alerts.md`: Alerts tab — cross-run attention feed (verification failures, unsupported/
  contradicted claims, dangling sources, redactions, needs-human-review) derived from existing
  run.json + summarizeRunAttention. est 5. (Least data-dependent — can start earlier.)
- G4 `viewer-tab-library.md`: Library tab — reusable outputs / writeback artifacts / skillbom candidates /
  published reports index across runs (needs F5 writeback + reusable_output data). est 5.
- G5 `viewer-tab-settings.md`: Settings tab — viewer config surface (sensitivity threshold display toggle
  tied to F4, theme, default tab, base data path). est 3. No data dep — can start early.
- G6 `viewer-tab-help.md`: Help tab — static help/about/keyboard-shortcuts/glossary of RF terms. est 2.
  No data dep — can start early.

---

## 3. Authoring instructions for agents
- Read THIS brief + your assigned template file + (optionally) the specific source files cited in your
  block for AC precision. Do NOT broadly re-explore.
- Frontmatter: follow the planning skill field checklist for your doc_type. schema_version: 2 where the
  template uses it. created: 2026-06-20. updated: 2026-06-20. status: draft. owner: nick.
  feature_slug = your slug. Set prd_ref/plan_ref/related_documents to the epic + siblings as relevant.
- Every "across/everywhere/all" AC MUST list target_surfaces (use §1.9). Every new field MUST have a
  resilience AC (R-P2). UI-touching phases get a runtime-smoke verification task (R-P4).
- Keep Tier 1 contracts 200-400 lines (G1-G6 may be 150-250). Keep the epic ≤ 400 lines. Split the F5
  impl plan into phase files if > 800 lines.
- Write ONLY your assigned file(s). Return a one-line confirmation with the path(s) and line count.
