---
schema_name: ccdash_document
schema_version: 2
doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans
id: BRIEF-run-metadata-enrichment
title: "Run Metadata Enrichment \u2014 Human Brief"
status: completed
category: human-briefs
feature_slug: run-metadata-enrichment
feature_family: run-metadata-enrichment
feature_version: v1
prd_ref: docs/project_plans/PRDs/features/run-metadata-enrichment-v1.md
plan_ref: docs/project_plans/implementation_plans/features/run-metadata-enrichment-v1.md
intent_ref: null
epic_ref: null
related_documents:
- docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md
- .claude/worknotes/run-metadata-enrichment/decisions-block.md
- .claude/worknotes/runs-viewer-v2.2-polish/epic-brief.md
owner: nick
contributors: []
audience:
- humans
priority: high
confidence: 0.78
created: '2026-06-20'
updated: '2026-06-21'
target_release: ''
tags:
- human-brief
- runs-viewer
- metadata
- enrichment
- tier-3
---

# Run Metadata Enrichment — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-06-20

---

## 1. Context Pointers

One-line pointers. Do not restate content.

- **PRD**: `docs/project_plans/PRDs/features/run-metadata-enrichment-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/features/run-metadata-enrichment-v1.md`
- **Epic**: `docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md` (F5 row)
- **Decisions Block**: `.claude/worknotes/run-metadata-enrichment/decisions-block.md` (phase boundaries, agent routing, risk hotspots, estimation anchors, dependency map, model routing)
- **Epic Brief**: `.claude/worknotes/runs-viewer-v2.2-polish/epic-brief.md` §1.10–1.12, §2-F5 (all verified source facts)
- **Design Specs**: None
- **SPIKEs**: None
- **Related Briefs**: `docs/project_plans/human-briefs/runs-frontend.md` (sibling viewer work)

---

## 2. Estimation Sanity Check

_Migrated from decisions block (H1–H6 anchors). Human-authored; not agent-relevant._

**Bottom-up total**: ~16–20 pts (Tier 3)
**Top-down anchor**: v2.1 facelift (export + display work) was ~13 pts FE-only; this plan adds a full backend data model + migration, so +30–50% is defensible → puts the range at 17–19.5 pts. Locked at **18 pts** as the working target; treat 20 as the realistic ceiling.
**Reconciliation**: Bottom-up and top-down agree within 15%. The top-down anchor deliberately comes in a bit under bottom-up because the v2.1 work did not require a schema migration or a multi-step derivation pipeline. Trust the bottom-up floor.

H1–H6 heuristic application:

- **H1 (noun-counting)**: ~4 new first-class metadata fields per run (`linked_projects[]`, `category`, `tags[]`, `backlog_idea_ref`/`backlog_idea_id`) extending an existing model — not new CRUD tables. Fields propagate across 4 layers (run.yaml → export_run() dict → index.json → TS types), which is the work, not the CRUD machinery. Roughly equivalent to ~3 table-like effort units: **base ~6 pts floor before algorithmic and UI work.**
- **H2 (dual-impl multiplier)**: Does NOT apply. This is a Python + React SPA codebase with a static-export serving model — no dual-edition repository split (LocalX / EnterpriseX). Export service is a single implementation.
- **H3 (algorithmic flag)**: Derivation/backfill phase (P2) performs a join/inversion of the backlog `links.run_id` index — a deterministic set operation, not a solver or graph traversal. No H3 penalty. Budgeted at ~3 pts for migration complexity (dry-run gate, idempotency, slug disambiguation, index update). P3 (creation path) straightforward plumbing (~2 pts).
- **H4 (bundle decomposition)**: This PRD packages 7 capability areas. Per-area independent estimates:

  | Capability Area | Independent Estimate | Notes |
  |-----------------|---------------------|-------|
  | Schema + codegen (P1) | 2 pts | Formal JSON schema file + optional TS codegen; no DB table |
  | Derivation + backfill (P2) | 3 pts | Idempotent migration, dry-run, slug-match correctness |
  | Creation path (P3) | 2 pts | plan_run() + capture CLI plumbing |
  | Export threading (P4) | 2 pts | export_run() dict + index.json + RFRunSummary/RFRunExport TS types |
  | Viewer display (P5) | 4 pts | Linked Projects PRIMARY everywhere (5 surfaces) + chips (5+ surfaces) |
  | Filtering/faceting (P6) | 2 pts | FilterTabs + RunList state extension |
  | Enrichment extras P1 scope (P7) | 3 pts | 8+ additional fields threaded + Overview widgets |
  | **Σ** | **18 pts** | |

  Cross-cutting plumbing (H6) included in individual estimates above but also spot-checked separately. **18 pts is the bundle floor; plan total must not be less.**

- **H5 (anchor reference)**: Closest analog is the v2.1 facelift (export + FE display work), which delivered ~13 pts of FE-only work with no backend schema changes. This plan adds the full data model + migration + creation-path layers on top of equivalent display work. Delta vs anchor: +38%, justified by P1 (schema), P2 (migration), P3 (creation path) which have no counterpart in v2.1. Within expected range; no red flag.
- **H6 (hidden plumbing budget)**: ~15% of 18 pts = ~2.7 pts for TS codegen wiring, index.json field threading, run-export schema doc, CHANGELOG, README, type-drift cleanup (`RFResolvedSource` missing `redacted: boolean`). This plumbing is explicit in P8 (tests + docs) and scattered in P1/P4. Not separately line-itemed in the phase table but accounted in the per-area estimates above.

---

## 3. Wave & Orchestration Notes

_Critical path narrative and parallelization hints. Plan owns the phase summary table._

**Critical path**: P1 (schema + codegen) → P2 (derivation/backfill) → P4 (export threading) → P5 (viewer display PRIMARY) → P6 (filtering). This 5-phase chain gates the main user-visible value. P4 is the integration barrier — nothing in the FE can render correctly until the export fields are present in `public/data`.

**Parallel opportunities**:
- P3 (creation path: `plan_run()` + capture CLI) is independent after P1 exits and can run in parallel with P2.
- P7 (enrichment extras, P1 scope) can start immediately after P4 lands — it shares the same export threading pattern and does not gate filtering.
- P5 viewer surfaces can be split per-surface across FE agents once P4 lands (barrier is strictly P4).
- P8 (tests + docs) runs last but changelog-generator + documentation-writer tasks within it can parallelize.

**Merge order**: P1 (Python schema) → P2 (migration script) → P3 (plan_run) → P4 (export + types) → P5 (FE display) → P6 (FE filter) → P7 (enrichment) → P8 (tests + docs). Each phase merges as a unit; no cross-phase mid-merge.

**Cross-feature coupling**:
- F1 (`nav-titles-lineage-fixes`) touches `export_service.py` and `index.json` for the `title` field. F5 P4 supersedes and extends F1's title threading — coordinate to avoid conflicts (F1 merges first; F5 P4 extends without regressing the title field).
- Downstream: disabled tabs G1 (Swarm), G2 (Policies), G4 (Library) depend on F5 P4/P7 enriched export being present. G1–G4 should not land until after F5 P4 is merged.

---

## 4. Open Questions Ledger

_Pointer inventory harvested from epic brief §2-F5, decisions block, and plan architecture. Update status as resolved._

| ID | Source | Question | Status | Resolved By |
|----|--------|----------|--------|-------------|
| OQ-1 | Decisions block §Risk | **Dual-write storage choice**: should new metadata fields live in `run.yaml` only, or also be mirrored into `run_index.yaml`, or into a separate `backlog_context.yaml` per run? The decisions block mandates single writer (migration/plan_run) with run_index derived from run.yaml — but the derivation mechanism needs a concrete design decision. | open | — |
| OQ-2 | Epic brief §1.11 | **Slug-match vs explicit ref**: backfill relies on backlog `links.run_id` as the authoritative key (NOT fuzzy title match). But some runs in `run_index.yaml` may have `run_id`s that predate the backlog link backfill. Are there runs that executed from a backlog idea but whose `links.run_id` was never set? | open | — |
| OQ-3 | Epic brief §1.12 | **`schema_version` policy for export**: bumping export `schema_version` (1.1 → 1.2) signals the presence of new optional fields. But older static bundles deployed at `:3030` will have run.json at 1.1. What is the policy: bump on every new optional-field addition, or only on breaking changes? The FE must be resilient either way (R-P2), but the versioning policy affects the schema doc and the formal JSON schema file. | open | — |
| OQ-4 | Epic brief §1.12 | **TS codegen adoption**: the plan proposes adding formal run-export JSON Schema + optional TS codegen to kill hand-sync drift. "Optional" is ambiguous — is codegen gated on a follow-up PR, or must it ship in P1 for the plan to be complete? If deferred, what prevents new hand-sync drift in P4 when adding fields? | open | — |
| OQ-5 | Decisions block §Phase 1 | **`backlog_idea_ref` vs `backlog_idea_id`**: the schema proposes both a `backlog_idea_ref` (RIB-NNN slug) and `backlog_idea_id` (reverse link). Are these two distinct fields carrying different semantics, or is one redundant? The backlog `links` block already has both `raw_idea_id` (slug) and an implied numeric id — clarify which field is authoritative and which is derived. | open | — |
| OQ-6 | Epic brief §2-F5 P1 scope | **Enrichment extras sequencing**: P7 (cost/model profiles, source-count-by-type, confidence + materiality distributions, etc.) is labeled "P1 scope" in the PRD but appears as Phase 7 in the plan. Is P7 required for the feature to ship, or is it a separate follow-on? Downstream tab contracts (G1, G4) need some P7 fields — clarify dependency surface before G-track planning starts. | open | — |

---

## 5. Deferred Items Rationale

_Why items were deferred and what would trigger promotion. Plan owns the triage table._

- **Composition highlight-text toggle UI**: Noted as P1 in epic brief §1.13. Deferred to F3 polish or a later phase — ReportRenderer already supports the mode; only the toggle UI is missing. Promote when F3 ships and the audit tab state machine is stable.
- **Inference/speculation basis hover tooltips**: P1 in §1.13. No data-model dependency. Deferred because it requires claim schema extensions not yet designed. Promote when claim-level basis field is added to the export.
- **Dangling/redaction warning badges in ClaimInspector**: P1 in §1.13. FE-only. Deferred to a targeted harden-polish pass after F3 audit state machine is stable.
- **`unresolved_questions` field in export**: Listed in §1.10 as existing in claim_ledger but not currently exported. Deferred to P7 enrichment extras. Promote to P0 if a downstream tab (G2 Policies or G3 Alerts) requires it.
- **`VITE_SHOW_ALL` env bypass for FE redaction gate**: Scoped in F4 as optional. If F4 ships the config-driven approach (sensitivity_threshold in foundry.yaml), the env bypass is a convenience feature. Deferred until F4 is live and the threshold approach proves sufficient.
- **Formal run-export JSON schema doc** (`docs/dev/architecture/rf-run-export-schema.md`): Schema doc is referenced in code comments (epic brief §1.12) but does not yet exist. Promoted to P8 (tests + docs) in this plan. Must ship with the feature; not truly deferred.

---

## 6. Risk Narrative

_Orchestrator-facing risk rationale sourced from decisions block risk hotspots._

- **Dual-write consistency (HIGH)**: `linked_projects`, `category`, `tags`, `backlog_idea_ref` could end up written by multiple code paths (migration script, `plan_run()`, manual edits to run.yaml, a future `rf update` command). The plan mandates a single-writer discipline (only migration and plan_run touch these fields; run_index.yaml is derived, never the source of truth). Watch for any agent that attempts to update run_index.yaml directly rather than deriving it from run.yaml. If this constraint is violated, the metadata can silently diverge between the two files and cause confusing display bugs in the viewer.

- **Backfill correctness / slug matching (HIGH)**: The derivation phase (P2) must use `backlog links.run_id` as the exact join key — no fuzzy matching, no title similarity. The risk is that some runs executed from backlog ideas before `links.run_id` was consistently backfilled, leaving them with no backlog link. The migration must handle and report these as "unlinked" rather than silently assigning a wrong category. The dry-run output must be reviewed by a human before the write pass is executed. **This is the one place where human review is mandatory before proceeding from P2 to P3.**

- **Export schema version compatibility (MEDIUM)**: The viewer deploys as a static bundle at `:3030`. If old bundles are cached (browser or CDN), they may receive run.json with `schema_version: 1.2` but only understand 1.1. All new fields must be optional and absent-tolerant in the FE (R-P2 resilience). The risk is that a future agent or developer adds a required field, causing null-pointer errors on older runs. Enforce: every AC for a new field must include a resilience clause tested against a pre-migration run fixture.

- **"Everywhere" surface sprawl (MEDIUM)**: The PRD says Linked Projects, category, and tags should appear "everywhere" in the viewer. Without explicit `target_surfaces` enumeration (R-P1), implementation agents will likely miss 2–3 surfaces. Mitigation: P5 ACs must enumerate each of the 10 canonical surfaces from epic brief §1.9 and mark which ones receive the primary display, chip display, or no display. The runtime smoke task (R-P4) must cover every surface listed in P5 ACs. This risk is process, not technical — prevent it at plan-authoring time.

- **Migration reversibility (MEDIUM)**: The backfill script writes new fields into existing run.yaml files. If the script has a bug (wrong category assigned due to a stale backlog snapshot), reverting requires re-running the script with a corrected backlog or manually editing run.yaml files. Mitigation: (a) the migration must perform a git-tracked diff or produce a log file before writing; (b) idempotent re-runnable design means a corrected run is safe; (c) the original backlog-derived values are always recoverable from `backlog/research_idea_backlog.yaml` since that file is the authoritative source.

---

## 7. What to Watch For

_Gotchas, trap-doors, and retrospective hooks for real-time review during execution._

- **F1 and F5 P4 will both touch `export_service.py` and `index.json`.** If F1 is in-flight when F5 P4 starts, there is a merge conflict risk. Ensure F1 merges first and F5 P4's agent is briefed on the F1 title field changes before touching those files.
- **TS type drift is the recurring failure mode in this codebase** (noted in epic brief §1.8: `RFResolvedSource` missing `redacted: boolean`). Every P4 and P5 agent must be reminded that `run-export.ts` types are hand-written and not codegen'd (unless P1 codegen ships). Spot-check that every new export field has a corresponding TS interface update.
- **The `re-export + rebuild static data` task must be explicitly in the plan** (epic brief §0.1.1). Agents working on P4 often complete the Python export code and mark the task done without triggering the actual data rebuild. The smoke task (R-P4) will catch this, but the rebuild must be part of the P4 definition of done.
- **P2 dry-run output needs human eyes.** Before the migration writes to any run.yaml, a human must inspect the diff. Build the dry-run flag into the migration script and document this review step as a gate in the P2 progress file.
- **P7 enrichment extras dependency on G-track**: If G1 (Swarm) or G4 (Library) contract authors start before F5 P7 is clearly scoped, they may assume export fields exist that have not been designed yet. Hold G1/G4 contract authoring until F5 P7 fields are confirmed in the plan.
- **Double-check that `backlog_idea_ref` (RIB-NNN) and `backlog_idea_id` are not conflated.** OQ-5 above flags this ambiguity. If P1 ships with conflated semantics and P2 writes them both, unwinding the model post-backfill is painful.

---

## 8. Expected Success Behaviors

_Observable, human-verifiable post-ship outcomes. Not agent acceptance criteria._

- [ ] **Linked Projects visible and primary on portfolio**: Navigate to `http://10.42.10.76:3030/runs`. Every RunCard that has a backlog-derived `linked_projects` value shows it as a primary labeled field (not hidden, not in a tooltip). Verify on at least 3 cards that have RIB backlog links.
- [ ] **Category and tags chips on RunCard**: On any RunCard with a linked backlog idea, the pillar-derived `category` and `tags[]` appear as chips. Chips are visible without hovering or expanding the card.
- [ ] **Category/tags chips on Overview tab**: Open a run that has backlog metadata. Navigate to the Overview tab. Category and tags chips are present in the metadata section. Same chips visible in the RunDetailModal header when opened from portfolio.
- [ ] **Filter by linked project works**: Use the portfolio filter controls (FilterTabs or equivalent) to filter by a specific linked project (e.g., "Research Foundry"). Only runs linked to that project appear. Clear the filter and all runs return.
- [ ] **Filter by category and tag works**: Filter portfolio by a pillar category (e.g., "Agentic OS"). Only runs in that category appear. Filter by a tag. Confirm results narrow correctly.
- [ ] **Old runs degrade gracefully**: A run that was exported before the backfill migration (no `linked_projects`, no `category`, no `tags`) must render without errors. The RunCard shows a blank/absent state for those fields — no null-pointer error, no "[object Object]", no broken layout.
- [ ] **No hand-sync drift in TS types**: Open `frontend/runs-viewer/src/types/rf/run-export.ts` and verify that `RFRunSummary` includes `linked_projects`, `category`, and `tags` fields. Verify `RFRunExport` includes the same plus any P7 enrichment fields that shipped.
- [ ] **P1 scope enrichment extras visible in Overview**: If P7 shipped, open a run and navigate to Overview. Cost/model profile widget, source-count breakdown, and at least one confidence/materiality distribution widget are visible and populated (not loading skeletons stuck in empty state).
- [ ] **Re-export + rebuild completed**: After P4 merges, run `rf run export --all` and `pnpm --filter runs-viewer build` (or equivalent). Verify that `public/data/index.json` contains `linked_projects`, `category`, and `tags` for at least one run. Verify at least one full `public/data/<id>/run.json` contains the same fields.
- [ ] **CHANGELOG entry present**: The `[Unreleased]` section of CHANGELOG.md includes an entry for run metadata enrichment (linked projects, categories, tags) under the appropriate category (Added or Changed).

---

## 9. Running Log

_Optional. Append-only. Short notes during execution — surprises, pivots, validated assumptions._
_Agents may append here only if explicitly instructed in a task prompt._

- [2026-06-20] Brief created. OQ-1 through OQ-6 harvested from epic brief and decisions block. Estimation anchored at 18 pts (Tier 3). Human review gate flagged at P2 dry-run.
- [2026-06-21] **Feature shipped.** All 8 phases executed via wave-driven workflow orchestration (P1→[P2,P3]→P4→[P5,P7]→P6→P8). Backfill applied to 18 runs (run.yaml + run_index.yaml), `backlog_idea_ref` = RIB-NNN per schema. Static data rebuilds at deploy. **Tier 3 gate cleared** (karen + correctness + architecture, all APPROVED) after two remediation cycles: (1) restored the human-readable run title accidentally dropped while making Linked Projects primary; fixed `backlog_idea_ref` slug→RIB-NNN; closed list_runs/plan_run/writebacks/context gaps; (2) aligned `writebacks` to the `RFRunWritebacksSummary` object shape and added missing top-level schema fields (`title`/`cost_usd`/`model_profiles`/`source_count_by_type`) + a strict Draft7 schema-validation regression test. Final: 534 pytest + 244 vitest green, tsc/eslint/ruff clean. Squash-merged to `main`. See `.claude/progress/run-metadata-enrichment/plan-completion.md`.
