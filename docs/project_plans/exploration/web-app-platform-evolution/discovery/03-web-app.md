---
doc_type: report
report_category: investigation
title: "Web App Discovery — Research Foundry Runs Viewer"
status: draft
created: 2026-07-10
feature_slug: web-app-platform-evolution
---

# Web App Discovery — Research Foundry Runs Viewer

## 0. Location

The web app lives at `frontend/runs-viewer/` — **not** Next.js. It is a **Vite + React 18 SPA**
(`frontend/runs-viewer/package.json:1-53`), routed client-side with `react-router-dom` v6. There is
no `apps/` or `web/` directory; this is the only frontend in the repo.

---

## 1. Architecture summary

### 1.1 Stack

| Layer | Choice | Evidence |
|---|---|---|
| Build tool | Vite 5 (`vite@^5.4.8`) | `frontend/runs-viewer/package.json:45` |
| UI framework | React 18.3, `react-router-dom@^6.26.2` (client routing, no SSR) | `package.json:19,22` |
| Data fetching | `@tanstack/react-query@^5.59.0` | `package.json:17`; `src/app/providers.tsx:1-34` |
| Graph view | `@xyflow/react@^12.3.6` (React Flow v12) | `package.json:18`; `src/components/LineageGraph/LineageFlow.tsx` |
| Report rendering | `react-markdown@^10` + `remark-gfm` | `package.json:21,23` |
| Auth (optional) | `@clerk/clerk-react@^5` (dev dep, lazy-loaded) | `package.json:26`; `src/auth/ClerkShell.tsx`, `src/auth/AuthContext.tsx:1-40` |
| Tests | Vitest (unit) + Playwright (e2e, 5 specs in `e2e/`) | `package.json:12-13` |
| Type codegen | `json-schema-to-typescript` (20 generated schema types) + hand-written run-export types | `package.json:42`; `codegen/generate-types.mjs` |

There is **no SSR / server component layer** — this is a pure client-rendered SPA. "Static export"
means Vite's standard production build (`vite build` → static HTML/JS/CSS + baked JSON data files),
not a Next.js static-export mode.

### 1.2 Two operating modes (dual-mode client)

The entire data layer is dual-mode, gated by a single build-time env flag, implemented once in
`src/api/client.ts:33-55` and reused by `reportsClient.ts` / `agentJobsClient.ts` via
`isLoopbackEnabled()` / `getLoopbackBase()` / `getLoopbackAuthHeaders()`.

- **Mode A — Static (default, production).** `scripts/prebuild-static-data.mjs` shells out to
  `python -m research_foundry run export --all` against the repo's `.venv`
  (`scripts/prebuild-static-data.mjs:36-49`), then copies every `runs/<run_id>/run.json` into
  `public/data/<run_id>/run.json` and writes a rollup `public/data/index.json` (id, status,
  created_at, sensitivity, claim_counts, title, linked_projects, category, tags —
  `prebuild-static-data.mjs:92-105`) plus `public/data/governance.json` (baked from
  `config/governance.yaml`, `prebuild-static-data.mjs:114-143`). Vite bundles/serves these as static
  assets; `fetchRunList()`/`fetchRunDetail()` in `client.ts:270-308` read them via plain `fetch()`
  against `BASE_URL` + the configurable `dataPath` setting (default `/data`). **No backend process
  is required at runtime.** This is the mode deployed to `10.42.10.76:3030`
  (`frontend/runs-viewer/README.md:7-17`).
- **Mode B — Live Loopback API.** Build-time flag `VITE_RUNS_FRONTEND_LOOPBACK_API=true` switches
  every client call to `loopbackGet()` against a running `rf serve` instance (default
  `http://127.0.0.1:7432/api`, overridable via `VITE_RUNS_LOOPBACK_API_BASE`, token via
  `VITE_RUNS_LOOPBACK_API_TOKEN` — `client.ts:213-243`; `README.md:19-79`). This is the **only**
  mode that makes `/agents` and the Report Builder's write actions functional (see §3, Builder/Agents).
  The client is explicitly documented as GET-only/read-only at the module level
  (`client.ts:21-24`) — mutations for the Builder live in a **separate** client
  (`src/api/reportsClient.ts`) gated by its own `isBuilderLoopbackEnabled()` check.
- Auth-token resolution is layered: a runtime resolver injected by `AuthContext` on login takes
  priority over the build-time `VITE_RUNS_LOOPBACK_API_TOKEN` env var; if neither is set, no
  `Authorization` header is sent (`client.ts:64-107`).
- A reactive rate-limit badge (GATE-900) is wired end-to-end: `loopbackGet()` parses
  `X-RateLimit-*`/`Retry-After` response headers into a module-level subject that `AppShell`
  subscribes to and renders (`client.ts:109-157`, `AppShell.tsx:69-74,151-161`).

### 1.3 Auth model (3 modes, defense-in-depth only in the UI)

`src/auth/AuthContext.tsx:1-40` documents three concrete modes, resolved in this order: forced
`none` when `VITE_RUNS_STATIC_EXPORT=true` → `VITE_AUTH_PROVIDER` build env (`clerk` |
`local_static`) → `rv_auth_provider` localStorage override → default `none` (today's
single-operator behavior, unchanged). Nav-item role gating in `AppShell.tsx:87-96,116-124` and the
Settings screen's admin section (`SettingsScreen.tsx:42-49`) are explicitly commented as
**"defense-in-depth ONLY, NOT the authorization boundary"** — the real gate is server-side
(`require_role()`, workspace-scoped repository queries), which live in the backend, not this app.

### 1.4 Deploy target & port map

`rf serve` / static SPA serve on **`10.42.10.76:3030`** (README.md:81-89), distinct from MeatyWiki
Portal (`:8765`), IntentTree API (`:8032`), SkillMeat API (`:8080`), and the RF API itself
(`:7432`). Redeploy path: `pnpm build` (or `pnpm build:runs-viewer` which runs the prebuild script
first) → restart `research-foundry-ui.service` on the node (per the v2.2 polish PRD, SC-1).

---

## 2. Screen / route inventory

Routes are declared in `src/app/routes.tsx:18-30` and wired in `src/app/App.tsx:34-53`. All routes
render inside `AppShell` (`src/app/AppShell.tsx`), a persistent left nav rail + content outlet — there
is no per-route layout variance beyond that shell.

| Route | Screen file | Purpose | Data source | Key interactions | Maturity |
|---|---|---|---|---|---|
| `/` → `/runs` | redirect | — | — | — | stable |
| `/runs` | `screens/RunList.tsx` | "Portfolio Command Center" — all runs at a glance | `useRunList()` → `index.json` or `GET /runs` | search/sort/filter (status tabs, attention queue, high-claim-volume, metadata facets by project/category/tag); status lanes (Published/Verified/In-Progress/Blocked); click row/card opens `RunDetailModal` overlay | mature (P6 metadata filtering shipped) |
| `/runs/:runId` | `screens/RunDetail.tsx` | Full run detail — 7-tab workspace | `useRunDetail(runId)` → `run.json` or `GET /runs/:id` | tab switch via `?view=`, deep-link via `?claim=`, sticky header (ResizeObserver-driven), lineage-node expand → `DetailModal` | mature |
| `/runs/:runId/swarm` | `SwarmRedirect` (inline in `App.tsx:28-32`) | Legacy alias | — | 302-style client redirect to `?view=swarm` (now itself aliased to `context`, see detailTabs) | deprecated redirect shim |
| `/settings` | `screens/SettingsScreen.tsx` | Viewer prefs (Display/Appearance/Navigation/Data) + Administration section (role-gated) | `localStorage` via `useViewerSettings()`; admin panels hit loopback admin API | toggle redaction bypass, theme, default tab, data path (requires reload); admin: workspace members, role matrix, rate-limit config, auth provider status, RBAC status | mature; admin section requires `admin`/`owner` role when `authMode !== "none"` |
| `/help` | `screens/HelpScreen.tsx` | Static reference: About, Keyboard Shortcuts, Glossary, Links | none (fully static) | none — read-only reference | complete, low-complexity |
| `/alerts` | `screens/AlertsFeed.tsx` | Cross-run attention feed | `fetchRunList()` + N×`fetchRunDetail()` in parallel, progressive render | 8 signal types (failed checks, warning checks, unsupported/mixed claims, dangling/redacted sources, empty inference basis, schema mismatch); "View run" link per card | mature, N+1 fetch pattern (fine at current corpus size, ~60 runs) |
| `/policies` | `screens/PoliciesScreen.tsx` | Global governance config + per-run governance table | `fetchGovernanceConfig()` (static `governance.json`) + `useQueries` over all runs' `.governance` block | sortable by sensitivity / writeback-approved; graceful "—" for pre-migration runs | mature |
| `/catalog` (alias `/library` redirects here) | `screens/CatalogScreen.tsx` | Evidence Catalog — cross-run/cross-project claims, sources, inferences, reports, "report-ready" outputs | `useCatalogStats/useCatalogSearch/useCatalogItem` → client-built index in static mode (`lib/catalog.ts`) or `GET /api/catalog/*` in loopback | tabbed by item type with live counts; filter by project/status/sensitivity; debounced search; paginated results table; right-rail inspector with provenance strip + usage-policy chips; "Add to Report" / "Run Follow-up Research" (both disabled/planned) | mature list+inspector; two actions are stubs |
| `/builder` | `screens/BuilderScreen.tsx` | Report Builder workspace | loopback: live `ReportDraft` via `useBuilder` hooks; static: read-only demo draft (`lib/builderMocks.ts`) | 4-pane layout (catalog search → outline+editor → audit inspector → claim basket); insert/remove claim & source links; verify + publish-preview mutations; block markdown editing | **loopback-only for writes**; static mode is a fixed read-only demo, persistent banner explains this |
| `/agents` | `screens/AgentsScreen.tsx` | Governed Agent Research — launch/monitor/accept agent jobs | loopback-only; `useAgentJob*` hooks (SSE-like event stream) | policy-gate summary, job-launch form (accepts `input_claim_ids`/`input_report_id` via router state — wired from Catalog "Run Follow-up Research" intent and Report "Research this"), live event panel, evidence-intake accept flow | **hard-gated to loopback**; static-mode direct nav shows an informational stub, no nav entry point at all in static builds |

### 2.1 Run Detail — the 7 tabs (in `components/RunDetail/RunDetailWorkspace.tsx:39-51`)

| Tab id | Label | Component | What it shows |
|---|---|---|---|
| `overview` | Overview | inline `RunOverview` (same file, `:177-467`) | Hero (title/created/claims/failed-checks/redacted/dangling/top-attention); Run Metadata (linked projects, category, tags, backlog ref, AOS identity UUIDs, native aliases); Run Enrichment (cost, model profiles, source-count-by-type, claim distribution bars, writeback target list) — every widget individually null-guarded; "Review Starting Points" (top 4 claims → jump to Audit) |
| `trust` | Trust | `TrustPanel/TrustCockpit.tsx` | Lifecycle stepper (8-stage), claim status donut, verification checklist |
| `ledger` (URL alias `audit`) | Audit (N) | `ClaimLedger/ClaimAuditWorkbench.tsx` | Full claim table + facets (status/materiality/claim_type/confidence) + `ProvenanceModal` two-click verbatim-quote drill-down + report-anchor coverage strip |
| `report` | Report | `ReportOverlay/ReportOverlay.tsx` | Rendered `report_draft` markdown with claim chips, composition sidebar filter (supported/inference/speculation), navigable outline (IntersectionObserver-driven active-section tracking), "Research this" → `/agents` handoff |
| `lineage` | Lineage | `LineageGraph/LineageGraph.tsx` (+ `LineageFlow.tsx` / `LineageList.tsx`) | Toggle between React-Flow graph view and a flat/tree list view of the provenance chain; double-click / expand-badge → `DetailModal` |
| `context` (URL alias `swarm`, forwarded) | Context | `RunDetail/ContextPane.tsx` | 4 collapsible sections: Routing Decision, Research Brief (markdown), Swarm Plan (2-level collapsible tree), Upstream Entities (intent/ibom/intenttree badge links); gated on `schema_version >= "1.3"` |
| `writeback` | Writeback | inline (`RunDetailWorkspace.tsx:146-171`) | Governance approval status, required-fix note, writeback target count; disabled tab styling when no writeback export present |

Default tab is configurable via Settings (`rv_default_tab`, `detailTabs.ts:5-22`); legacy query
values `audit`/`swarm` are coerced forward. `RunDetail.tsx` (page mode) and `RunDetailModal.tsx`
(overlay mode) both render the same `RunDetailWorkspace` — this is the shared "item expansion"
pattern (F2 in the v2.2 polish PRD) reused across Portfolio card clicks, Catalog "Open run", and
Alerts "View run".

---

## 3. Component inventory

### 3.1 RunList (`src/components/RunList/`)

| Component | Role | Reuse notes |
|---|---|---|
| `RunCard.tsx` | Per-run card: lifecycle badge, sensitivity chip, linked-project badge, tag chips (top-3+overflow), claim counts, verification pass/fail, governance verdict, schema-mismatch badge — every field independently null-safe | exports `deriveFilterState()` used by `RunListScreen` tab counts |
| `FilterTabs.tsx` | Saved-view tabs (All/Verified/Needs Review/Planned) + P6 metadata facet panel | consumes `MetadataFilterOptions`/`MetadataFilterState` |
| `TagFilterPanel.tsx` | Tag/project/category multi-select facet UI | used inside `FilterTabs` |
| `tagColor.ts` | Deterministic tag→color mapping | shared by `RunCard` |

### 3.2 RunDetail (`src/components/RunDetail/`)

| Component | Role |
|---|---|
| `RunDetailWorkspace.tsx` | Tab shell + Overview tab body (largest single file in the surface, ~595 lines) |
| `ContextPane.tsx` | Context tab (routing/brief/swarm-plan/upstream entities), sessionStorage-persisted collapse state via `useCollapseState` |
| `DetailModal.tsx` | Generic "expand any item" overlay — discriminated union over `claim` / `node` / `source` / `issues` payloads; used from lineage nodes, ledger rows, Builder issue categories |
| `RunDetailModal.tsx` / `RunCard` double-click | Full-run overlay modal (page-equivalent of `/runs/:runId`, used from Portfolio, Catalog, Alerts) |
| `SwarmPane.tsx` | Legacy name retained for `RoutingDecisionCard`/`SwarmPlanSection` (now consumed by `ContextPane`, sourced from `screens/SwarmScreen.tsx`) |
| `detailTabs.ts` | Tab enum + URL query coercion/aliasing (`audit`↔`ledger`, `swarm`↔`context`) |

### 3.3 ClaimLedger (`src/components/ClaimLedger/`)

| Component | Role |
|---|---|
| `ClaimAuditWorkbench.tsx` | Composes table + facets + `ProvenanceModal` + `ReportRenderer`/`ReportCoverageStrip` + report-anchor filters into one audit workspace |
| `ClaimLedgerTable.tsx` | Dense claim table, keyboard-navigable rows, double-click → `DetailModal` |
| `LedgerFacets.tsx` | Facet chips (status/materiality/claim_type/confidence) driving the audit highlight state machine (`lib/auditStateMachine.ts`) |

### 3.4 LineageGraph (`src/components/LineageGraph/`)

| Component | Role |
|---|---|
| `LineageGraph.tsx` | Top-level list↔graph toggle wrapper |
| `LineageFlow.tsx` | React Flow (`@xyflow/react` v12) tree renderer. **Registers both `nodeTypes` and `edgeTypes`** at module scope (`edgeTypes = { smoothstep: SmoothStepEdge }`, `LineageFlow.tsx:180-182`) — this is the fix for the v2.2-polish bug where invisible edges resulted from an unregistered `smoothstep` edge type; confirmed present in current code. Custom node renders icon/title/subtitle/chips + expand badge with child count. |
| `lineageFlowElements.ts` | Pure function building React-Flow `nodes`/`edges` from the lineage tree |
| `lineageLayout.ts` | Horizontal tree layout algorithm (positions only; consumed, never recomputed, by the flow renderer) |
| `lineageTree.ts` | `LineageNode`/`LineageKindMeta` domain types + `LINEAGE_KIND_META` (per-kind accent color/label) |
| `LineageList.tsx` | Flat/tree list alternative view (keyboard: ArrowRight/Left expand/collapse) |
| `LineageDetailPanel.tsx` | Side panel for the selected lineage node; has the ⤢ expand-to-modal affordance |
| `kindIcons.tsx` | Icon set per lineage node kind + chevrons |

### 3.5 ReportOverlay (`src/components/ReportOverlay/`)

`ReportOverlay.tsx` (composite) → `ReportRenderer.tsx` (markdown render via `react-markdown` +
`remark-gfm`, claim-chip injection), `CompositionSidebar.tsx` (supported/inference/speculation
filter → dims chips), `ReportOutline.tsx` + `reportOutlineUtils.ts` (heading extraction +
IntersectionObserver-driven active-section tracking, anchored to the nearest
`data-scroll-container` ancestor — a documented contract shared with page/modal scroll containers),
`ReportCoverageStrip.tsx` (coverage % strip), `ClaimChip.tsx` (inline claim reference chip).

### 3.6 TrustPanel (`src/components/TrustPanel/`)

`TrustCockpit.tsx` (composite, used in the `trust` tab) → `TrustPanel.tsx` (legacy/simple variant),
`ClaimStatusDonut.tsx`, `TimelineStepper.tsx` (8-stage lifecycle), `VerificationChecklist.tsx`
(deep-links to failing checks via `#clm_NNN` anchors per the P3-SEAM-001 navigation contract).

### 3.7 Other cross-cutting components

| Component | Role |
|---|---|
| `ProvenanceModal/ProvenanceModal.tsx` | Two-click claim→verbatim-quote modal (`ref`-based `open(claimId)`/`close()` API); AC: ≤2 interactions from ledger row to quote |
| `SourceCard/SourceCard.tsx` | Single resolved-source card: trust badge, source-type icon, usage-permission pills, expandable quote — **the primary sensitivity/redaction gate** (see §4.3) |
| `Builder/*` | `BuilderCatalogPane` (search+basket-toggle), `BuilderDraftCard` (outline+editor shell), `BuilderOutline`, `BuilderBlockEditor`, `BuilderAuditInspector` (coverage/issues/verify/publish gate), `ClaimBasket` (staged items pending insertion) |
| `Agents/*` | `AgentJobLaunchForm`, `AgentJobEventPanel` (live event stream), `EvidenceIntakePanel` (accept-artifacts flow), `PolicyGateSummary` |
| `AdminSettings/*` | `WorkspaceMembersPanel`, `RoleAssignmentPanel`, `RateLimitConfigPanel`, `AuthProviderStatusPanel`, `RbacStatusPanel` — all admin-only, all loopback-API-backed |
| `shared/EmptyState.tsx` | Generic empty-state block, reused across Catalog and elsewhere |

---

## 4. Data model notes

### 4.1 Type sources — two parallel systems

1. **Hand-written run-export types** — `src/types/rf/run-export.ts`. Bound to
   **`schema_version` `"1.4"`** (file header, `run-export.ts:8`), source of truth
   `docs/dev/architecture/rf-run-export-schema.json` / `.md`. Explicitly **not** codegen'd: the
   file header (`run-export.ts:1-23`) records that `json-schema-to-typescript` was evaluated and
   rejected (anonymous enum unions instead of reusable named types; `additionalProperties: true`
   objects would degrade to `unknown`; hand-written types already carry richer docs). Manual sync
   is enforced by PR review (referenced as SCH-003 in the phase-1 schema-derivation plan). Older
   memory of "schema 1.3" is superseded — the code and its own docstring now say 1.4; 1.3 is
   referenced as the **context-tab gate** (`ContextPane.tsx:13`: renders empty-state below that
   version), so both numbers are real but describe different thresholds.
2. **Auto-generated types** — `src/types/rf/*.generated.ts`, one per schema YAML (20 files:
   `source_card`, `claim_ledger`, `evidence_bundle`, `extraction_card`, `foundry` workspace
   manifest, `research_intent`, `research_brief`, `swarm_plan`, `review_packet`,
   `arc_review_request`, `ccdash_event`, `meatywiki_writeback`, `notebooklm_update`, `ibom`,
   `intenttree_node`/`intenttree_update`, `raw_idea`, `report_frontmatter`, `routing_decision`,
   `skillbom_candidate`). Regenerated via `pnpm codegen` → `codegen/generate-types.mjs`. All
   re-exported through the single barrel `src/types/rf/index.ts:1-107` — "consumers should import
   from `@/types/rf` only, not from sub-files" (barrel header comment).

### 4.2 The three-step "export-threading" rule (dual/triple-update discipline)

The v2.2-polish PRD (`docs/project_plans/PRDs/enhancements/runs-viewer-v2.2-polish-epic-v1.md:97,190`)
documents the actual chain a new field must travel, confirmed by the code:
`run.yaml` field → **explicit threading** in `export_service.py:export_run()` (backend, not in this
repo leg) → (if list-visible) **`prebuild-static-data.mjs` summary object**
(`prebuild-static-data.mjs:92-105`) → **hand-written TS type** in `run-export.ts`. Every one of
these three points must be updated by hand for a new field to reach the UI; there is no single
schema-driven source of truth for the export contract today (OQ-1 in the PRD proposes but does not
mandate codegen for this file).

### 4.3 Sensitivity / redaction model

`RFSensitivity = "public" | "personal" | "work_sensitive" | "client_sensitive"` (ascending order,
`run-export.ts:32-36`). Redaction happens **twice**:
- **Backend, at export time** — sources above the configured `viewer.sensitivity_threshold` are
  replaced with a `"[redacted:sensitivity]"` string literal in `quote`/`summary` before the JSON
  ever reaches the browser (referenced as P1-SENS-001).
- **Frontend, defense-in-depth** — `SourceCard.tsx:35-49` (`isRedacted()`) re-checks
  `source.sensitivity` against a threshold and blanks quote/summary client-side too. Unknown
  sensitivity labels are **fail-closed** (treated as redacted). Two bypasses exist, both
  explicitly LAN-only-tool rationale in comments: `rv_show_all` in `localStorage` (toggle on the
  Settings screen, `SettingsScreen.tsx:70-102`) and build-time `VITE_SHOW_ALL=1`.
- `RFResolvedSource.redacted?: boolean` (`run-export.ts:96`) is an optional flag the backend can
  set explicitly; `sourceHasRedactedText()` in `lib/runs.ts:92-96` also detects the literal string
  prefix as a secondary signal.

### 4.4 Claim / verification / governance shapes

`RFClaim` carries `claim_type` (factual/inference/speculation), `status` (supported/mixed/
contradicted/inference/speculation/unsupported), `confidence` (low/medium/high), `materiality`
(core/background/style/material), and a `sources: RFResolvedSource[]` array — this is the fully
denormalized join the backend performs once so the frontend never has to resolve `claim_ledger` ↔
`source_card` ↔ `extraction_card` itself. `RFVerification`/`RFVerificationCheck` carry pass/fail/skip
+ severity per check (feeds `VerificationChecklist` and the Alerts "failedChecks"/"warningChecks"
signals). `RFGovernanceBlock` (`sensitivity`, `approved_for_writeback`, `allowed_writebacks`,
`requires_human_review`) backs the Policies screen's per-run table. `report_anchors` (schema 1.4,
§16) is an **additive, nullable** field — its complete absence (not merely `null`) on pre-1.4
exports is the documented "legacy mode" trigger consumed throughout `ClaimAuditWorkbench` and
`lib/reportAnchors.ts`.

### 4.5 Evidence Catalog model (cross-run)

`src/types/rf/catalog.ts` defines a **6-kind** union (`claim | source | inference | report |
reusable_output | writeback`) mapped 1:1 from run-export fields (comment block,
`catalog.ts:33-41`): non-inference claims → `claim`, claims with `inference_basis` → `inference`,
resolved claim sources → `source`, one `report` per run with a `report_draft`,
`reusable_output_candidates[]` → `reusable_output`, `writebacks.targets[]` → `writeback`. Critically,
**the same mapping logic is implemented twice** — once server-side (`catalog_service.py`, not in
this leg) and once client-side (`src/lib/catalog.ts: buildCatalogIndex/searchCatalog/catalogStats`)
so that static mode and loopback mode are "behaviorally equivalent" (file header comment,
`catalog.ts:6-13`) — this is the same manual-parity risk pattern as §4.2, one level up the stack.

### 4.6 Report Builder draft model

`src/types/rf/report_draft.ts` defines `ReportDraft`, `ReportBlock` (typed, e.g. `heading`),
`ReportClaimLink`/`ReportSourceLink` (block-scoped evidence attachments), verify/publish-preview
result shapes. The Builder HTTP API is explicitly called out as **not yet landed** (`BuilderScreen.tsx:16-25`)
— the screen is built and tested purely against the typed client (`api/reportsClient.ts`) plus a
bundled mock draft (`lib/builderMocks.ts`) for static mode; this is a documented contract-ahead-of-
backend situation, not a bug.

---

## 5. Feature set — confirmed present vs. absent

| Feature | Present? | Evidence |
|---|---|---|
| Runs list (portfolio) | Yes | `RunList.tsx` |
| Run detail (7 tabs incl. lineage/report/trust/audit/context/writeback) | Yes | `RunDetailWorkspace.tsx` |
| Telemetry / trace | Partial — "Context" tab surfaces routing decision + swarm plan; no dedicated raw-telemetry/trace viewer screen exists (no `telemetry` or `trace` route/tab found) | routes.tsx, detailTabs.ts |
| Reports (rendered + composable) | Yes, both read (`ReportOverlay`) and author (`BuilderScreen`, loopback-only) | — |
| Catalog (cross-run evidence search) | Yes | `CatalogScreen.tsx` |
| Audit / claim ledger | Yes | `ClaimAuditWorkbench.tsx` |
| Tray Insert (loopback read/write mode) | **Not found as a named feature/component.** No `Tray` component, string "Tray Insert", or `RF_UI_LOOPBACK` env reference exists anywhere in `frontend/runs-viewer/src` or `README.md` (grep returned zero hits). The actual loopback toggle found is `VITE_RUNS_FRONTEND_LOOPBACK_API`, which unlocks `/agents` + Builder writes + admin panels — this may be what memory's "Tray Insert" refers to, but no literal "tray" surface exists in the current codebase. **Flagging as a discrepancy vs. the brief's assumption for the orchestrator to reconcile.** |
| Search/filter | Yes — Portfolio (string match + facets), Catalog (debounced search + facets); no cross-run full-text/semantic search |
| Alerts / attention feed | Yes | `AlertsFeed.tsx` |
| Policies / governance | Yes | `PoliciesScreen.tsx` |
| Settings (viewer prefs + admin) | Yes | `SettingsScreen.tsx` |
| Help | Yes | `HelpScreen.tsx` |
| Agent job launch/monitor (governed) | Yes, loopback-only | `AgentsScreen.tsx` |
| Auth (Clerk / local / none) | Yes, 3 modes | `AuthContext.tsx` |
| RBAC UI surface | Yes, advisory only | `AppShell.tsx`, `SettingsScreen.tsx` admin section |
| Rate-limit awareness | Yes | `client.ts` GATE-900, `AppShell.tsx` badge |

---

## 6. Observed gaps / limitations (for a public, multi-capability research product)

1. **Read-only by default; authoring is loopback-gated.** The only mutation surface (Report
   Builder) and the only agent-orchestration surface (`/agents`) both require a live `rf serve`
   process and are functionally absent from the shipped static/public deployment. A public product
   needs either a hosted backend behind these gates or a redesigned always-available authoring path.
2. **Three-step manual type-sync chain** (`export_service.py` → prebuild summary → hand-written TS)
   is a standing drift risk, acknowledged multiple times in-repo (SC-2/SC-3/OQ-1) but never
   resolved with codegen. Any platform evolution that adds fields will hit this every time.
3. **Catalog mapping logic is duplicated** between the (external) backend `catalog_service.py` and
   `src/lib/catalog.ts` to keep static/loopback parity — a second instance of the same
   "manually-synced twin implementation" risk as #2, one layer up.
4. **No cross-run analytics/trend view.** Catalog is the only cross-run surface; there is no
   dashboard for cost-over-time, corpus growth, run-to-run comparison, or portfolio trend metrics
   beyond the health-strip counts on `/runs`.
5. **No full-text/semantic search across runs.** Portfolio search is a plain substring match over
   a handful of summary fields (`RunList.tsx:147-155`); Catalog has real filtering/sort but scoped
   to catalog items, not raw run content.
6. **RBAC/roles are UI-advisory only.** Every role check in this app is explicitly commented as
   non-authoritative; a public multi-tenant product would need this app to consume a real
   session/claims model rather than a client-side `identity.roles` array with graceful-degrade
   defaults.
7. **No workspace switcher in the primary nav.** `WorkspaceMembersPanel` exists under Settings, but
   there's no user-facing way to switch active workspace/tenant from the main rail — multi-tenant
   navigation is effectively unbuilt at the UX layer even though backend types support workspaces.
8. **No export/share affordance.** Report Builder has verify + publish-preview mutations, but no
   PDF/markdown export, share-link, or external publish action is wired from the UI.
9. **No mobile/responsive pass.** Explicitly out of scope in the v2.2-polish PRD ("Out of scope"
   §8) and no evidence of it having been picked up since.
10. **No command palette / global search.** The Help screen documents scattered per-component
    keyboard shortcuts (Escape/Enter/Arrow only); there's no Cmd-K style cross-surface navigation.
11. **`/agents` has no discoverable nav entry in static/public builds** — it's reachable only via
    direct navigation or the "Research this"/"Run Follow-up Research" handoff links from
    Report/Catalog, which themselves are disabled unless loopback is enabled. This is a
    discoverability dead-end for anyone not running a local `rf serve`.
12. **Builder's underlying HTTP API had not landed as of this code** (`BuilderScreen.tsx` header
    comment) — the whole authoring screen is currently validated against a typed client contract
    and a mock draft, not a live backend integration test.
13. **No "Tray Insert" component found** despite it being called out as an existing capability in
    prior context — see §5 row above; worth reconciling before basing UX capability claims on it.
