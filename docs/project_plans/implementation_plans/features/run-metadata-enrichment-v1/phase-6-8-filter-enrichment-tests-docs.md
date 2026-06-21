---
schema_version: 2
doc_type: phase_plan
title: "Run Metadata Enrichment — Phases 6–8: Filtering, Enrichment Extras & Tests/Docs"
status: draft
phase: "6-8"
phase_title: "Filtering/Faceting, Enrichment Extras (P1), Tests & Docs"
created: 2026-06-20
updated: 2026-06-20
feature_slug: run-metadata-enrichment
prd_ref: docs/project_plans/PRDs/features/run-metadata-enrichment-v1.md
plan_ref: docs/project_plans/implementation_plans/features/run-metadata-enrichment-v1.md
entry_criteria:
  - "P5 complete (all display surfaces verified)"
  - "P4 export barrier confirmed (static data rebuilt with new fields)"
exit_criteria:
  - "P6: filter by linked_project / category / tag works; empty state graceful"
  - "P7: enrichment widget fields threaded + shown in Overview; resilience per field"
  - "P8: all tests pass; runtime smoke signed off; CHANGELOG entry exists; README + viewer docs updated; karen gate cleared"
---

# Phases 6–8: Filtering/Faceting · Enrichment Extras · Tests & Docs

**Parent plan**: [run-metadata-enrichment-v1.md](../run-metadata-enrichment-v1.md)
**Phases covered**: P6 (Filtering/Faceting), P7 (Enrichment Extras), P8 (Tests & Docs)

---

## Column conventions

| Column | Values |
|--------|--------|
| Estimate | story points |
| Model | `sonnet` \| `haiku` |
| Effort | `adaptive` \| `extended` (Claude only) |

---

## Phase 6: Filtering / Faceting

**Duration**: 1–2 days
**Dependencies**: Phase 5 complete (display surfaces verified)
**Assigned Subagents**: ui-engineer-enhanced (primary), frontend-developer

### Overview

Extend `FilterTabs.tsx` and `RunList.tsx` filter state to filter portfolio runs by `linked_project`,
`category`, and `tags`. Use the existing filter pattern (AND logic, applyFacets-style). Provide
graceful empty states when no runs match.

### Source references (verified)
- `FilterTabs.tsx` at `components/RunList/FilterTabs.tsx`: current filter tabs (epic brief §1.9).
- `RunList.tsx` filter state: applyFacets-style AND logic on left table (epic brief §1.7 LedgerFacets
  pattern). RunList uses its own filter state at the portfolio level.
- `LedgerFacets.tsx` (audit tab) uses AND-logic filtering — use the same approach for portfolio.

### Task table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| FILT-001 | Filter state extension | Extend RunList filter state (wherever `FilterTabs` and `RunList.tsx` maintain active filters) to add `activeLinkedProjects: string[]`, `activeCategories: string[]`, `activeTags: string[]`. Default all to `[]` (no filter). | Filter state compiles; no existing filter behaviour broken; default state = unfiltered | 1 pt | ui-engineer-enhanced | sonnet | adaptive | DISP-002 |
| FILT-002 | FilterTabs UI for metadata | Add three collapsible filter sections to `FilterTabs.tsx`: "Project" (checkbox list of all unique linked_projects across index.json), "Category" (checkbox list of all unique categories), "Tags" (checkbox list of all unique tags). Derive options dynamically from the loaded run summaries — do not hardcode. Null-safe: if a run has no linked_projects, it doesn't contribute to the list but also doesn't cause errors. | FilterTabs renders Project/Category/Tags filter sections with dynamic option lists; options derived from actual run data; null runs omitted from option derivation; existing Status filter unchanged | 2 pts | ui-engineer-enhanced | sonnet | adaptive | FILT-001 |
| FILT-003 | Apply filters in RunList | Wire `activeLinkedProjects`, `activeCategories`, `activeTags` into RunList's run filtering: a run passes if (linked_projects intersects activeLinkedProjects OR activeLinkedProjects empty) AND (category in activeCategories OR activeCategories empty) AND (tags intersect activeTags OR activeTags empty). Runs with null fields fail a non-empty filter (they have no matching values). | Selecting "Project: ResearchFoundry" shows only runs with that linked project; selecting a tag filters correctly; combining filters uses AND logic; null-field runs correctly excluded; "clear all" resets to show all runs | 1 pt | ui-engineer-enhanced | sonnet | adaptive | FILT-002 |
| FILT-004 | Empty state | When all runs are filtered out, show a graceful empty-state message: "No runs match the selected filters. [Clear filters]" with a button to reset all filters. | Empty state renders when filter combination matches 0 runs; "Clear filters" button resets all activeFilters to []; no layout errors | 1 pt | frontend-developer | sonnet | adaptive | FILT-003 |

#### AC FILT-003 (structured)

```
AC FILT-003: Metadata filter application
- target_surfaces:
    - frontend/runs-viewer/src/screens/RunList.tsx
    - frontend/runs-viewer/src/components/RunList/FilterTabs.tsx
- propagation_contract: FilterTabs emits active filter selections → RunList applies AND-logic filter on RFRunSummary[]
- resilience: runs with null linked_projects/category/tags excluded when filter active (not shown); no console error
- visual_evidence_required: false
- verified_by: [TEST-001, SMOKE-001]
```

**Phase 6 Quality Gates:**
- [ ] Filtering by linked_project, category, tag all work correctly
- [ ] AND-logic verified: combining 2 filter types narrows results
- [ ] Empty state renders when 0 matches
- [ ] Runs with null metadata excluded from filtered views (not shown, no error)
- [ ] Existing status filter unchanged and working

---

## Phase 7: Enrichment Extras (P1 data)

**Duration**: 2 days
**Dependencies**: Phase 4 complete (export pattern established); parallel to P5/P6 where timeline permits
**Assigned Subagents**: python-backend-engineer (export), ui-engineer-enhanced (widgets)

### Overview

Surface additional high-value run data that is already captured in run.yaml / run.json but not shown
in the viewer. These are P1 (nice-to-have) but unlock downstream tabs (Swarm, Policies, Library from
epic G). All follow the same export threading pattern established in P4.

### Source references (verified)
- All data candidates from epic brief §1.10: cost_usd / model profiles (run.yaml.profile), 
  routing_decision (context), swarm plan + agents, source-count-by-type, confidence distribution,
  materiality distribution, freshness (research_brief max_age_days), writeback targets+status,
  unresolved_questions (claim_ledger, not exported), audience (report frontmatter), governance
  approved_by/timestamp.
- Already in `RFRunExport` (no export threading needed): `verification`, `governance`, `timeline`,
  `writebacks` — just need UI widgets.

### Task table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| ENR-001 | Thread cost/model profile to export | In `export_run()`, add `cost_usd?: number`, `model_profiles?: object` (max_cost_usd, extraction_model, synthesis_model, verification_model, max_runtime_minutes, freshness_days) to the output dict. Read from `run.yaml.profile`. Emit null if absent. | run.json has `cost_usd` + `model_profiles` fields; null for runs without profile; `RFRunExport` type extended; `npx tsc --noEmit` clean | 1 pt | python-backend-engineer | sonnet | adaptive | EXP-005 |
| ENR-002 | Thread source count by type | In `export_run()`, derive `source_count_by_type: {web?: n, doc?: n, ...}` by aggregating source types from the run's sources. Add to dict. | run.json has `source_count_by_type` with correct counts; null/empty object for runs with no sources | 1 pt | python-backend-engineer | sonnet | adaptive | EXP-005 |
| ENR-003 | Thread routing/swarm context | Thread `context.routing_decision` (string) and `context.swarm_plan` (object) into the export output (they are in `context?` already in `RFRunExport` but may not be populated in export dict). Verify they appear in run.json. | run.json `context.routing_decision` and `context.swarm_plan` populated for runs that have them; null for others | 0.5 pts | python-backend-engineer | sonnet | adaptive | EXP-005 |
| ENR-004 | Re-export + rebuild for enrichment fields | After ENR-001..003: re-run `rf run export --all` + `pnpm --filter runs-viewer build`. Verify enrichment fields appear in sample run.json files. | `public/data` rebuilt; sample run.json shows cost_usd, model_profiles, source_count_by_type, context fields | 0.5 pts | python-backend-engineer | sonnet | adaptive | ENR-001, ENR-002, ENR-003 |
| ENR-005 | Overview enrichment widgets | In `RunDetailWorkspace.tsx` Overview tab, add an "Enrichment" section (below Run Metadata section from DISP-004) with visual widgets for: Cost (formatted USD), Model Profiles (compact table), Source Count by Type (mini bar or counts), Confidence + Materiality distribution (already in claim_counts — render as progress bars), Writeback status (already in writebacks — render targets list). Each widget: show only when data present; hide when null (R-P2). | Each widget shows correct data when present; graceful omission when null; no layout errors for all-null Overview | 2 pts | ui-engineer-enhanced | sonnet | adaptive | ENR-004, DISP-004 |
| ENR-006 | RFRunExport type updates for enrichment | Extend `RFRunExport` in `run-export.ts` with `cost_usd?: number \| null`, `model_profiles?: {...} \| null`, `source_count_by_type?: Record<string, number> \| null` (routing_decision/swarm_plan already in context). | Types compile; `npx tsc --noEmit` clean; each enrichment field explicitly typed and nullable | 0.5 pts | ui-engineer-enhanced | sonnet | adaptive | ENR-001 |

#### AC ENR-005 (structured)

```
AC ENR-005: Overview enrichment widgets
- target_surfaces:
    - frontend/runs-viewer/src/components/RunDetail/RunDetailWorkspace.tsx
- propagation_contract: RunDetailWorkspace receives RFRunExport; reads cost_usd, model_profiles, source_count_by_type, claim_counts, writebacks
- resilience: each widget shown only when its data field non-null; Overview renders without any widget when all enrichment fields null (pre-enrichment run); no console errors
- visual_evidence_required: "Overview tab screenshot for enriched run + for un-enriched run"
- verified_by: [SMOKE-001]
```

**Phase 7 Quality Gates:**
- [ ] `cost_usd`, `model_profiles`, `source_count_by_type` threaded into export
- [ ] `routing_decision` and `swarm_plan` confirmed in run.json for runs that have them
- [ ] Overview enrichment widgets render correctly for enriched runs
- [ ] All widgets omit gracefully when data null (R-P2)
- [ ] `RFRunExport` types compile after enrichment field additions
- [ ] Re-export + rebuild confirms enrichment fields in `public/data`

---

## Phase 8: Tests & Docs

**Duration**: 1–2 days
**Dependencies**: Phases 1–7 complete
**Assigned Subagents**: python-backend-engineer (unit tests), ui-engineer-enhanced (runtime smoke), documentation-writer (haiku), changelog-generator (haiku)

### Overview

Unit tests for derivation and export threading. Runtime smoke verification for all UI surfaces
(R-P4 mandate). CHANGELOG entry, README update, viewer docs, run-export schema doc. Final reviewer
gates: task-completion-validator per phase + karen at feature end.

### Runtime smoke task (R-P4 mandatory)

Per R-P4: any phase that touched `*.tsx` files MUST have a runtime smoke task referencing every
`target_surfaces` entry from that phase.

| Surface | Phases that touched it | Smoke check |
|---------|------------------------|-------------|
| `screens/RunList.tsx` | P5, P6 | Project column visible; filter works |
| `components/RunList/RunCard.tsx` | P5 | Project badge + tags chips shown |
| `components/RunList/FilterTabs.tsx` | P6 | Filter sections expand; filter applies |
| `components/RunDetail/RunDetailWorkspace.tsx` | P5, P7 | Metadata section + enrichment widgets |
| `components/RunDetail/RunDetailModal.tsx` | P5 | Sub-header line with project/tags |
| `components/ClaimLedger/ClaimAuditWorkbench.tsx` | P5 | Tags reference chips in ClaimInspector |
| `components/LineageGraph/LineageDetailPanel.tsx` | P5 | Tags reference chips in panel header |

### Task table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|---------------------|----------|-------------|-------|--------|--------------|
| TEST-001 | Unit tests: derivation & backfill | Write pytest tests for `MIG-001`/`MIG-002` logic: (a) inversion map correctness (given a mock backlog, produces correct run→metadata map), (b) idempotency (re-run on already-updated run.yaml produces no diff), (c) `--dry-run` produces diff but no writes, (d) merge logic (2 ideas → same run_id: union tags, collect linked_projects). | All 4 test scenarios pass; `uv run pytest` clean | 1 pt | python-backend-engineer | sonnet | adaptive | MIG-002 |
| TEST-002 | Unit tests: export threading | Write pytest tests for `export_run()` additions: (a) run with all 5 new fields in run.yaml → all 5 in output dict; (b) run with none of the new fields → all 5 in output as null; (c) schema_version is "1.2" in all cases; (d) enrichment fields (cost_usd, etc.) correct. | All export tests pass; `uv run pytest` clean | 1 pt | python-backend-engineer | sonnet | adaptive | EXP-001, ENR-001 |
| TEST-003 | TS type compile verification | Run `npx tsc --noEmit` in `frontend/runs-viewer`. Capture and resolve any errors introduced by phase 4–7 type changes. Confirm `RFRunSummary` and `RFRunExport` changes are clean. | `npx tsc --noEmit` exits 0; no new type errors introduced by this feature | 0.5 pts | ui-engineer-enhanced | sonnet | adaptive | EXP-004, EXP-005, ENR-006 |
| SMOKE-001 | Runtime smoke: all UI surfaces (R-P4) | After `pnpm --filter runs-viewer build` + serving the SPA locally: verify each of the 7 target_surfaces in the smoke table above renders correctly. Use a run known to have backlog linkage AND a pre-migration run (null fields). Capture screenshots for visual ACs. Note any surface where null-field rendering is incorrect. | All 7 surfaces pass smoke check; screenshots captured for ACs DISP-001 through DISP-004 and ENR-005; no console errors on null-field runs; failures documented as bugs before feature is sealed | 1 pt | ui-engineer-enhanced | sonnet | adaptive | FILT-004, ENR-005 |
| DOC-001 | Update CHANGELOG | Add entry under `[Unreleased]` (Added section): "Run Metadata Enrichment: runs now carry Linked Projects, Category, and Tags derived from the research backlog; visible in the portfolio table, RunCard, RunDetail Overview, and run modals; filtering by project/category/tag enabled." | CHANGELOG `[Unreleased]` has entry; categorized as Added; `changelog_ref` frontmatter set | 0.5 pts | changelog-generator | haiku | adaptive | SMOKE-001 |
| DOC-002 | Update README | If README documents viewer features/screenshots, add a note about the new metadata fields and filter. | README reflects current feature set; no stale information | 0.5 pts | documentation-writer | haiku | adaptive | DOC-001 |
| DOC-003 | Viewer docs | Create or update `docs/dev/runs-viewer.md` (or similar): add section "Run Metadata (Linked Projects, Category, Tags)" explaining what the fields are, where they come from (backlog), and how to backfill existing runs (`scripts/backfill_run_metadata.py`). | Docs accurate; backfill workflow documented; audience: developers | 1 pt | documentation-writer | haiku | adaptive | DOC-001 |
| DOC-004 | Run-export schema doc | Update `docs/dev/architecture/rf-run-export-schema.md` (referenced in epic brief §1.12) to document schema 1.2: new fields, their types, nullability, and how they're derived. Link to the JSON schema file from SCH-002. | Schema doc describes v1.2 fields accurately; links to JSON schema file; diff from v1.1 documented | 0.5 pts | documentation-writer | haiku | adaptive | EXP-003 |
| DOC-005 | Human brief annotation | Append a note to `docs/project_plans/human-briefs/run-metadata-enrichment.md` §9 Running Log: "Feature shipped. Backfill run. Static data rebuilt. Karen gate cleared YYYY-MM-DD." | Human brief Running Log updated; status field advanced to `completed` | 0.5 pts | documentation-writer | haiku | adaptive | DOC-001 |
| DOC-006 | Plan frontmatter finalization | Set `status: completed`, populate `commit_refs`, `pr_refs`, `files_affected` in implementation plan frontmatter. | All lifecycle frontmatter fields populated | 0.5 pts | documentation-writer | haiku | adaptive | DOC-001 |
| REV-001 | Reviewer gate: task-completion-validator | task-completion-validator reviews Phase 8 completion: (a) all unit tests pass, (b) SMOKE-001 signed off, (c) CHANGELOG entry exists, (d) all deferred items have design specs or N/A. | Reviewer passes; any failures documented and resolved | 0.5 pts | task-completion-validator | sonnet | adaptive | DOC-006 |
| REV-002 | Karen gate: feature-end review | karen reviews the full feature diff: phase quality gates, acceptance criteria coverage, architectural consistency, no scope drift. Gate: karen must pass before PR is opened. | Karen passes or raises issues resolved before PR | 1 pt | karen | opus | extended | REV-001 |

**Phase 8 Quality Gates:**
- [ ] All unit tests pass (`uv run pytest` clean)
- [ ] `npx tsc --noEmit` clean
- [ ] SMOKE-001 signed off (all 7 surfaces verified; screenshots captured)
- [ ] CHANGELOG `[Unreleased]` has "Run Metadata Enrichment" entry
- [ ] README updated (if applicable)
- [ ] Viewer docs and schema doc updated
- [ ] Human brief Running Log updated
- [ ] Plan frontmatter complete (status: completed, commit_refs, files_affected)
- [ ] task-completion-validator passed (REV-001)
- [ ] **karen gate cleared (REV-002) — mandatory before PR**

---

## Deferred Items (from P8 triage)

| Item ID | Category | Reason Deferred | Trigger for Promotion | Target Spec Path |
|---------|----------|-----------------|-----------------------|-----------------|
| DEF-001 | backlog | Unresolved questions from claim_ledger not yet exported | Needs claim_ledger schema change; defer to claim enrichment epic | `docs/project_plans/design-specs/claim-ledger-unresolved-questions-export.md` |
| DEF-002 | backlog | Audience field from report frontmatter surfacing | Low viewer demand; requires report parsing | `docs/project_plans/design-specs/report-audience-surfacing.md` |
| DEF-003 | dependency-blocked | G-tab data deps (Swarm/Policies/Library): these tabs need enriched export data, now unblocked | G epic gates on F5 shipping | Tracked in G epic; no new design spec needed |

*Both DEF-001 and DEF-002 require design spec authoring in this phase (DOC-006 task above).*
