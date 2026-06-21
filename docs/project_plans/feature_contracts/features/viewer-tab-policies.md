---
title: "Feature Contract: Policies Tab (Governance + Per-Run Governance)"
schema_version: 2
doc_type: feature_contract
status: ready
created: 2026-06-20
updated: 2026-06-21
feature_slug: "viewer-tab-policies"
category: "features"
estimated_points: 5
tier: 1
owner: nick
priority: medium
risk_level: low
changelog_required: false
audience: [ai-agents, developers]
related_documents:
  - docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md
  - docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md
  - docs/project_plans/feature_contracts/features/viewer-tab-swarm.md
  - docs/project_plans/implementation_plans/features/run-metadata-enrichment-v1.md
spike_ref: null
prd_ref: docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md
plan_ref: null
commit_refs: []
pr_refs: []
files_affected: []
---

# Feature Contract: Policies Tab (Governance + Per-Run Governance)

## 1. Goal

Enable the hard-disabled "Policies" top-level nav tab so the viewer can display global governance configuration (key profiles, policy rules) alongside per-run governance state (sensitivity, writeback approval, allowed writebacks, human-review flag) derived from the already-exported `run.json` governance block.

---

## 2. User / Actor

- **Primary user**: Nick Miethe — LAN-only Research Foundry operator reviewing governance posture across runs and checking whether individual runs are cleared for writeback or require human review.
- **Secondary users**: Any developer or AI agent inspecting the viewer to understand the governance enforcement state of a run.

---

## 3. Job To Be Done

When reviewing research runs in the viewer, the operator wants to see the governance configuration and each run's governance verdict in one place, so they can quickly confirm which runs are writeback-approved, which need human review, and what policy rules govern the system — without leaving the viewer or opening raw YAML files.

---

## 4. Scope

### In Scope

- Enable the "Policies" nav item in `AppShell.tsx` `NAV_ITEMS` (change `state: "disabled"` → `state: "enabled"`; set `resolveTarget: () => "/policies"`).
- Register a `/policies` route in `app/routes.tsx` (add `RouteName`, `ROUTES` entry, and export a lazy-loaded screen element).
- Implement a new `PoliciesScreen` React component (e.g., `frontend/runs-viewer/src/screens/PoliciesScreen.tsx`) with two sections:
  1. **Global Governance Panel**: display the key profiles and policy rules loaded from the static `governance.yaml` config snapshot (source: `governance.py` loads `config/governance.yaml` → `key_profiles` + `policy_rules`). Since this is a static SPA, the panel shows whatever governance config is baked into the export; display it as a read-only reference table.
  2. **Per-Run Governance Table**: list all runs (from the already-available `index.json` summary + lazily loaded `run.json`) with per-run governance columns: `sensitivity`, `approved_for_writeback`, `allowed_writebacks`, `requires_human_review` — drawn from `RFRunExport.governance` (`RFGovernanceBlock`; `run-export.ts` lines 177-182) and from the run's writeback summary (`RFRunWritebacksSummary.approved_for_writeback`).
- Export the governance config snapshot into `public/data/governance.json` via `prebuild-static-data.mjs` (a new static file, written once per build from `config/governance.yaml`).
- Add `governance_config` TS type for the static snapshot (minimal: `key_profiles`, `policy_rules`).
- Graceful empty state when governance data is absent (runs exported before this feature, or no `governance.yaml` present).

### Out of Scope

- Mutating governance settings from the viewer (viewer is read-only; `foundry.yaml` / `governance.yaml` are edited on disk).
- Displaying governance audit trails or the `governance_audit_log.jsonl` file (separate concern).
- Secret-pattern display (sensitive; governance.py manages patterns, not the viewer).
- Deriving governance fields from `run.yaml` for runs that predate the export (handled by F5 backfill if/when shipped).
- Any dependency on F5 run-metadata-enrichment fields (`linked_projects`, `tags`, `category`) — Policies tab reads only what is already in `run.json` governance block and `governance.yaml`.

---

## 5. UX / Behavior Requirements

- The "Policies" nav rail item (`short: "PL"`) is clickable and navigates to `/policies`; it is no longer visually disabled. `isActiveNav()` returns true when `pathname === '/policies'`.
- The `/policies` route renders `PoliciesScreen` at top-level (not nested under a run; run context is optional).
- **Global Governance Panel** (top section):
  - Loads `governance.json` (fetched from `public/data/governance.json`).
  - If the file is absent or empty, renders a muted "No governance config found — governance.json not present in this build." message; no error thrown.
  - Displays key profiles as a labeled list or table: profile name → allowed sensitivity levels, writeback permissions, notes.
  - Displays policy rules as a table: rule ID → severity → description.
  - Labels are read-only; no edit controls.
- **Per-Run Governance Table** (below global panel):
  - Reuses the existing run index (`/data/index.json`) as the row source (run_id, status_derived already there).
  - For each run, loads the `governance` block from the corresponding `run.json` on demand (lazy, triggered by the table render; or batch-load all on mount since the index is small).
  - Columns: Run ID (link to `/runs/:runId`), Sensitivity, Writeback Approved, Allowed Writebacks, Requires Human Review.
  - Boolean fields rendered as Yes / No / — (dash for absent/null).
  - `allowed_writebacks` rendered as a comma-joined list of target names, or "—" if empty/absent.
  - Rows sortable by Sensitivity and Writeback Approved columns.
  - Clicking Run ID navigates to the run detail page (same behavior as RunCard click in portfolio).
- **Empty/loading states**: spinner while fetching; "No runs found" if index is empty; per-cell "—" when a field is null/absent.
- Screen title: "Policies" (h1); sub-headings: "Governance Configuration" and "Run Governance Summary".

---

## 6. Data Requirements

- **New static file**: `public/data/governance.json` — built by `prebuild-static-data.mjs` from `config/governance.yaml`. Shape:
  ```json
  {
    "key_profiles": { "<profile_name>": { ... } },
    "policy_rules": [ { "id": "...", "severity": "...", "description": "..." } ]
  }
  ```
  Written atomically alongside the existing `public/data/index.json` step. If `config/governance.yaml` is absent, write `{}` (empty object) so the fetch never 404s.
- **Existing fields consumed** (no new backend export fields required for this tab):
  - `RFRunExport.governance` → `RFGovernanceBlock` (already in `run-export.ts:177-182`):
    - `sensitivity?: RFSensitivity`
    - `approved_for_writeback?: boolean`
    - `approved_by?: string | null`
    - `approval_timestamp?: string | null`
  - `RFRunWritebacksSummary` (`run-export.ts:227-233`): `approved_for_writeback`, `reviewer_notes`.
- **Missing fields** (`allowed_writebacks`, `requires_human_review`) — these are in the run.yaml `governance:` block (sourced from the backlog idea's `governance:` YAML per `§1.11`) but NOT currently in `RFGovernanceBlock` or exported by `export_service.py` (line 431 exports the raw `governance` dict from the evidence_bundle, not from run.yaml). Two options:
  1. (Preferred, minimal) Thread `allowed_writebacks` and `requires_human_review` from `run_meta.get("governance")` into the exported governance dict in `export_service.py:export_run()` (lines ~404-431), add them to `RFGovernanceBlock` in `run-export.ts`, and re-export all runs.
  2. (Fallback) Show "—" for these two fields if absent and document as a known gap.
  - The contract **prefers option 1** — thread the two fields — since the export already reads `run_meta` and `governance`. This is a minimal backend touch (two dict lookups).
- **New TS types**:
  - `GovernanceConfig` interface in a new `types/governance.ts` (or inline in `PoliciesScreen`): `{ key_profiles?: Record<string, unknown>; policy_rules?: Array<{ id: string; severity: string; description?: string }> }`.
  - Extend `RFGovernanceBlock` with `allowed_writebacks?: string[] | null` and `requires_human_review?: boolean | null`.
- **No new DB tables, migrations, or schema files** required.

---

## 7. API / Integration Requirements

**Static data (no live API calls in production):**
- `GET /data/governance.json` — new static file served by Vite dev server and bundled build. Fetched once on `PoliciesScreen` mount using the same pattern as `client.ts` `fetchIndex()` / `fetchRun()`.
- `GET /data/index.json` — existing; reused to enumerate runs for the per-run table.
- `GET /data/<runId>/run.json` — existing; loaded per-run to extract the `governance` block.

**Internal service dependencies:**
- `prebuild-static-data.mjs` — extended to read `config/governance.yaml` (via `js-yaml` already imported) and write `public/data/governance.json`.
- `export_service.py:export_run()` — minimal extension to thread `allowed_writebacks` and `requires_human_review` from `run_meta.get("governance", {})` into the exported `governance` dict (if present in run.yaml).
- `api/client.ts` — add `fetchGovernanceConfig(): Promise<GovernanceConfig>` helper (same pattern as `fetchIndex`).

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `app/AppShell.tsx` `NAV_ITEMS` array — add the `resolveTarget` lambda; match the existing `NavCapability` shape exactly (lines 24-35).
- `app/routes.tsx` `ROUTES` / `RouteName` — add `policies` key following the existing `runList`/`runDetail` pattern; lazy-load screen via React Router `<Route element={<PoliciesScreen />}>`.
- `api/client.ts` fetch helpers — new `fetchGovernanceConfig()` follows the same fetch + JSON parse + error propagation pattern as `fetchIndex()`.
- `prebuild-static-data.mjs` static export pipeline — write `public/data/governance.json` in the same loop that writes `index.json`.
- `export_service.py` governance dict construction (lines 404-431) — additive only; do not alter the existing keys; append `allowed_writebacks` and `requires_human_review` from `run_meta`.

**Must not change (protected areas):**
- `RFRunExport` schema_version string or existing frozen field shapes — only additive extension of `RFGovernanceBlock`.
- The existing redaction logic in `export_service.py` — this tab does not touch sources or claims.
- `RunDetailWorkspace.tsx`, `RunDetailModal.tsx`, `ClaimAuditWorkbench.tsx` — no changes to existing run-detail surfaces.

**New dependencies:**
- Allowed? **No** — no new npm packages or Python libraries required. `js-yaml` already used in `prebuild-static-data.mjs`; existing React primitives sufficient for the table UI.

---

## 9. Acceptance Criteria

#### AC-1: Nav enabled and route resolves

- target_surfaces:
    - frontend/runs-viewer/src/app/AppShell.tsx
    - frontend/runs-viewer/src/app/routes.tsx
- propagation_contract: `NAV_ITEMS[6]` (Policies) `state` changed from `"disabled"` to `"enabled"`; `resolveTarget: () => "/policies"` added. `ROUTES` gains a `policies` entry with `path: "/policies"`. React Router renders `PoliciesScreen` at `/policies`.
- resilience: If `PoliciesScreen` throws on mount, an error boundary (existing pattern) prevents full shell crash; nav remains usable.
- visual_evidence_required: Screenshot showing "Policies" nav item active and `/policies` URL in the address bar with screen content visible.
- verified_by: [runtime-smoke task]

#### AC-2: Global Governance Panel renders from governance.json

- target_surfaces:
    - frontend/runs-viewer/src/screens/PoliciesScreen.tsx
- propagation_contract: `prebuild-static-data.mjs` writes `public/data/governance.json` from `config/governance.yaml`; `fetchGovernanceConfig()` fetches it; `PoliciesScreen` renders key profiles + policy rules tables.
- resilience: If `governance.json` is absent (404) or empty (`{}`), panel renders the muted "No governance config found" message; no uncaught error.
- visual_evidence_required: false
- verified_by: [runtime-smoke task, unit test for empty/absent case]

#### AC-3: Per-run governance table shows sensitivity and writeback approval

- target_surfaces:
    - frontend/runs-viewer/src/screens/PoliciesScreen.tsx
- propagation_contract: `run.json` `governance.sensitivity` and `governance.approved_for_writeback` columns populated from `RFGovernanceBlock`; displayed as text / Yes/No per row.
- resilience: If `governance` block is null/absent in a `run.json` (pre-feature runs), all governance columns render "—" for that row; no error thrown.
- visual_evidence_required: false
- verified_by: [runtime-smoke task]

#### AC-4: allowed_writebacks and requires_human_review threaded from run.yaml and displayed

- target_surfaces:
    - frontend/runs-viewer/src/screens/PoliciesScreen.tsx
    - frontend/runs-viewer/src/types/rf/run-export.ts
- propagation_contract: `export_service.py:export_run()` appends `allowed_writebacks` and `requires_human_review` from `run_meta.get("governance", {})` to the `governance` export dict. `RFGovernanceBlock` extended with `allowed_writebacks?: string[] | null` and `requires_human_review?: boolean | null`. Per-run table renders these columns.
- resilience: If fields are absent in run.yaml `governance:` (older runs or runs created without backlog linkage), columns show "—"; no runtime error.
- visual_evidence_required: false
- verified_by: [re-export + rebuild static data task, runtime-smoke task]

#### AC-5: Re-export + rebuild after backend governance changes

- target_surfaces:
    - frontend/runs-viewer/src/screens/PoliciesScreen.tsx
- propagation_contract: After `export_service.py` change, running `rf run export --all` + `pnpm --filter runs-viewer build` produces updated `public/data/<id>/run.json` files and updated `public/data/governance.json`. New columns appear in the per-run table.
- resilience: Build does not fail if some runs lack governance fields.
- visual_evidence_required: false
- verified_by: [re-export + rebuild static data task]

#### AC-6: Runtime smoke — full Policies screen reachable in built SPA

- target_surfaces:
    - frontend/runs-viewer/src/app/AppShell.tsx
    - frontend/runs-viewer/src/app/routes.tsx
    - frontend/runs-viewer/src/screens/PoliciesScreen.tsx
- propagation_contract: After `pnpm --filter runs-viewer build`, the built SPA serves `/policies` without a blank screen or console error. Nav item is clickable and highlights correctly.
- resilience: Verified in Vite dev mode (or built preview) with at least one run in index.json.
- visual_evidence_required: Screenshot of `/policies` route rendered in browser (dev or preview mode).
- verified_by: [runtime-smoke task]

---

## 10. Validation Requirements

- [ ] **Typecheck** passes (`npx tsc --noEmit` from `frontend/runs-viewer/`) with no new errors after `RFGovernanceBlock` extension and new types.
- [ ] **Lint** passes (`eslint` for TS/TSX).
- [ ] **Build** passes (`pnpm --filter runs-viewer build`) including `prebuild-static-data.mjs` step that writes `governance.json`.
- [ ] **Unit tests** added for: (a) `PoliciesScreen` rendering with empty/absent governance data; (b) `RFGovernanceBlock` extension shape; (c) `prebuild-static-data.mjs` governance.json write (if testable in isolation).
- [ ] **Re-export + rebuild static data** task executed and verified (`rf run export --all` + `pnpm build`).
- [ ] **Runtime smoke** task: navigate to `/policies` in dev mode, confirm both panels render, confirm no console errors, capture screenshot.
- [ ] **No unrelated changes** introduced.

---

## 11. Risk Areas

- **Governance.yaml parsing in prebuild**: `config/governance.yaml` may have varied structure across deployments. The prebuild step must handle absent file, empty file, and arbitrary YAML keys gracefully — write `{}` on any read failure rather than aborting the build.
- **allowed_writebacks / requires_human_review availability**: These fields live in `run.yaml`'s `governance:` block (sourced from backlog idea governance), but not all runs were created from backlog ideas. Many existing runs will show "—" for these columns until F5 backfill or manual annotation. Document this as expected behavior in the Completion Report.
- **Export service change triggers re-export**: Extending the `governance` export dict requires re-running `rf run export --all`, which overwrites all `run.json` files. This is safe (atomic write, source-of-truth is `runs/*/` YAML files) but is a deploy step that must not be forgotten. The implementation MUST include the re-export task in the sprint execution.
- **Soft dependency on F5**: G2 does not require F5, but F5 may later extend `RFGovernanceBlock` further. This contract must not conflict with F5's planned `RFGovernanceBlock` extensions. Additive-only changes to the type are safe.
- **No live governance.py data**: The viewer is a static SPA; it cannot call governance.py at runtime. The Policies tab is a read-only snapshot baked at build time. Users who change `governance.yaml` after build must rebuild to see updates. Document this limitation.

---

## 12. Implementation Notes

**Suggested approach** (agent may improve):

1. **Backend first — export_service.py**: Add `allowed_writebacks` and `requires_human_review` extraction from `run_meta.get("governance", {})` into the returned dict at lines ~417-435. Keep additive; do not alter existing keys.
2. **Types**: Extend `RFGovernanceBlock` in `run-export.ts` (lines 177-182) with the two new optional fields. Add `GovernanceConfig` type (new file or inline).
3. **Prebuild**: In `prebuild-static-data.mjs`, after writing `index.json`, read `config/governance.yaml` with `js-yaml`, write `public/data/governance.json` (fallback `{}` on error).
4. **Client helper**: Add `fetchGovernanceConfig()` to `api/client.ts` following the `fetchIndex()` pattern.
5. **Route + nav**: Update `NAV_ITEMS[6]` in `AppShell.tsx` and add `policies` to `ROUTES` / `RouteName` in `routes.tsx`. Wire React Router `<Route path="/policies" element={<PoliciesScreen />} />` in the router config (find where `runList`/`runDetail` routes are rendered, likely `main.tsx` or a router component).
6. **PoliciesScreen**: New file at `frontend/runs-viewer/src/screens/PoliciesScreen.tsx`. Two sections: GlobalGovernancePanel (fetches `governance.json`, shows key_profiles + policy_rules) + RunGovernanceTable (fetches index, then lazily loads run.json per row or batch-loads all). Keep it simple: plain HTML table with Tailwind/CSS classes matching existing `.rv-*` BEM patterns; no new component library entries needed.
7. **Re-export + rebuild**: Run `rf run export --all` then `pnpm --filter runs-viewer build` to bake updated `run.json` files and `governance.json` into `public/data/`.
8. **Runtime smoke**: Navigate to `/policies` in Vite dev mode; confirm both panels render without console errors; screenshot for AC-6 evidence.

**Similar existing code:**
- `api/client.ts` `fetchIndex()` — follow this pattern for `fetchGovernanceConfig()`.
- `screens/RunList.tsx` — reference for a top-level screen that consumes the index and renders a data table.
- `app/AppShell.tsx` NAV_ITEMS — copy the structure of an existing `enabled` item (e.g., Portfolio at line 25).
- `app/routes.tsx` ROUTES — add `policies` matching the `runList` pattern (lines 18-21).
- `prebuild-static-data.mjs` index.json write block — extend in the same function to write `governance.json`.

**Known gotchas:**
- React Router route registration: find where `createBrowserRouter` or `<Routes>` is defined (likely `main.tsx` or a dedicated `Router.tsx`) and add the `/policies` `<Route>` there — `routes.tsx` only exports the metadata object, it does not register routes automatically.
- `governance.yaml` key_profiles structure may be nested differently than `policy_rules`. Render it with `JSON.stringify(profile, null, 2)` in a `<pre>` block if the structure is too varied for a table — acceptable for v1.
- The per-run table will trigger N `fetch` calls for N runs if batch-loading eagerly. For small deployments (< 100 runs) this is acceptable. If the run set is larger, consider loading governance data only for visible rows (virtualization) — but this is P1 polish, not required for this contract.

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: List of all modified/new files with brief reason.
- **Tests run**: What tests were added/updated and results.
- **Validation results**: Table of all validation commands and their results (pass/fail/not applicable).
- **Deviations from contract**: Any material changes to the contract during implementation and why.
- **Risks / Limitations**: Any remaining risks or known limitations (especially: which runs show "—" for `allowed_writebacks`/`requires_human_review` and why).
- **Follow-up recommendations**: Suggested next steps (e.g., F5 backfill once shipped to populate allowed_writebacks for all runs; governance.yaml structural notes).

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion Report template.

---

## Metadata & References

**Tier**: 1 (estimated 5 points)

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion, no phase orchestration.

**Reviewer**: `task-completion-validator` (mandatory — reviews Completion Report against ACs and validation results before Opus commits).

**Soft dependency**: F5 (`run-metadata-enrichment`) — G2 does not require F5 to ship, but F5 backfill will populate `allowed_writebacks` / `requires_human_review` for more runs once complete.

**Related Documents**:
- Epic index: `docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md`
- Sub-epic (disabled tabs): `docs/project_plans/PRDs/features/enable-disabled-viewer-tabs-epic-v1.md`
- F5 metadata enrichment plan: `docs/project_plans/implementation_plans/features/run-metadata-enrichment-v1.md`
- Run export types: `frontend/runs-viewer/src/types/rf/run-export.ts`
- Export service (governance dict, lines 404-431): `src/research_foundry/services/export_service.py`
- Governance service (key_profiles / policy_rules): `src/research_foundry/services/governance.py`
- AppShell NAV_ITEMS (lines 24-35): `frontend/runs-viewer/src/app/AppShell.tsx`
- Route table: `frontend/runs-viewer/src/app/routes.tsx`
- Static export prebuild: `scripts/prebuild-static-data.mjs`

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass validation. Key constraints to keep in mind:

- **Viewer is read-only**: no mutation of governance config from the UI — display only.
- **Static SPA**: all data comes from pre-built JSON files under `public/data/`; no runtime API calls to the Python backend.
- **Additive only**: every change to `export_service.py`, `RFGovernanceBlock`, and `routes.tsx` must be additive — do not alter or remove existing fields/entries.
- **Re-export is mandatory**: after modifying `export_service.py`, you MUST run `rf run export --all` + rebuild before the runtime smoke task.
- **Scope boundary**: do not add governance editing, secret-pattern display, governance audit log, or any F5 metadata fields. Stay within the Policies display scope defined above.
