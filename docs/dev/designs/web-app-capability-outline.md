---
schema_version: 2
doc_type: design_spec
maturity: shaping
title: "Web App — UI/UX Capability Outline"
status: draft
created: 2026-07-10
feature_slug: web-app-platform-evolution
related_documents:
  - docs/project_plans/exploration/web-app-platform-evolution/discovery/03-web-app.md
  - docs/project_plans/exploration/web-app-platform-evolution/discovery/04-public-service.md
  - docs/project_plans/exploration/web-app-platform-evolution/current-state-and-direction.md
---

# Web App — UI/UX Capability Outline

## 1. Purpose & handoff note

This document is the **information architecture + capability + component map** for the Research
Foundry web app (`frontend/runs-viewer/`). It is a handoff contract for design agents who will
produce the actual visual design (colors, typography, spacing, pixel layout, motion) in a later
pass. This doc deliberately contains **no visual design decisions** — no palette, no font stack, no
component styling. What it does fix is:

- Which **screens** exist or should exist, and what each one is *for*.
- Which **capabilities/actions** each screen exposes, to which **user**, in which **state**.
- Which **components** already exist (with source paths) vs. need to be built, so design work reuses
  rather than reinvents.
- The **phasing** — what ships now vs. what depends on backend capability that doesn't exist yet.

Design agents consuming this doc should treat every `EXISTS` row as "restyle, don't redesign the
interaction," every `ENHANCE` row as "extend an existing interaction," and every `NET-NEW` row as
"design the interaction from scratch, informed by the adjacent existing patterns this doc cites."

This is a **synthesis** of three discovery documents (`03-web-app.md`, `04-public-service.md`,
`current-state-and-direction.md`) plus one operator direction decision (2026-07-10, see §2). It does
not re-derive facts already established there; it cites them (`file:line` where useful) and builds
the forward-looking screen/capability map on top.

## 2. Product framing

### 2.1 Who it's for

The web app serves **two users** from one shell, not two separate products:

1. **The operator** — the person who runs Research Foundry: launches/monitors runs, reviews and
   approves plans, verifies claims, manages writebacks, and (for small-team deployments) manages
   auth/RBAC/workspace membership.
2. **The research reader** — anyone consuming the *output*: browsing reports, following claim
   provenance, checking trust/verification status, and searching across the evidence corpus. A
   reader may never launch a run.

Today's app is read-surface-mature and operator-authoring-immature (see `03-web-app.md` §5–6): nine
screens cover reading thoroughly; the only mutation surfaces (Report Builder, `/agents`) are
loopback-gated and largely undiscoverable in the shipped static build. This outline's job is to make
both personas first-class without regressing the read surface's maturity.

### 2.2 Platform context — four surfaces, one web app

Research Foundry has four surfaces (`current-state-and-direction.md` §3): the CLI/core engine, the
agentic/integration layer, the HTTP/MCP API, and the web app itself. The web app is a *client* of the
HTTP API (`rf serve`, `:7432`) — it does not own the deterministic pipeline (capture→verify→bundle),
the claim ledger, or governance policy; it renders and, where gated, triggers them. Every capability
in this outline maps to an existing or planned API surface — this doc does not invent new backend
behavior, only the UI surface for behavior the platform capability map already describes as
shipped, shipped-flag-gated, or explicitly planned.

### 2.3 Service model — small-team / self-host ready, not full multi-tenant SaaS

Per operator direction (2026-07-10): target is **option (b) small-team-ready**
(`current-state-and-direction.md` §6 axis a) — not personal-first (too narrow given the shipped
auth/RBAC/workspace-isolation stack) and not full multi-tenant SaaS (no shared store, no
self-service signup, DI-1 open). Concretely: auth-on is a supported, designed-for mode (login, role
display, admin panels are first-class chrome whenever `auth.provider != none`, never bolted on);
workspace scoping is treated as enforced in the target UI (badge, mismatch-denied error state) even
though the backend defaults to advisory-until-armed (`04-public-service.md` §4); RBAC-gated
affordances are hidden/disabled-with-reason, never silently server-fail-only; admin panels
(member list, role assignment, rate-limit, auth-provider status, RBAC status) stay in-app, not a
separate ops tool (`03-web-app.md` §3.7). **No workspace switcher today** — one `local_static` token
= one `(user_id, workspace_id, roles)` triple (`04-public-service.md` §1, §7) — a switcher is
designed as a target (§4.17) contingent on a backend multi-workspace-per-identity model that does
**not** exist yet. **Not full multi-tenant SaaS**: no cross-tenant admin, no self-service invite
flow, no shared multi-tenant store — out of scope here (see §8 for what would need to change).

### 2.4 Phased authoring — read/verify stays first-class throughout

Run **authoring** is phased; run **reading and verification** are not — mature today, and must stay
so at every phase. **Phase 1**: idea/intake capture, plan review, run monitoring — wraps the existing
`POST /api/runs` scaffold+plan endpoint (`current-state-and-direction.md` §2.3, never drives the
swarm itself); no live run-control yet. **Phase 2**: gated live run-control — promotes the existing
`/agents` job-launch model (loopback-only, undiscoverable today, `03-web-app.md` §2) to a role-/
flag-gated first-class capability. **Phase 3**: platform maturity — cross-run analytics, command
palette, export/share, full-text search, fuller admin/workspace-switcher once backend prerequisites
land. **Runs list, Run Detail's seven tabs, Catalog, Alerts, Policies are Phase 1 by definition** —
they exist today; enhancements to them ship alongside Phase 1 authoring, never blocked behind it.

## 3. Information architecture

### 3.1 Target top-level navigation

The current nav rail (`AppShell.tsx`) is a flat list: Runs, Settings, Help, Alerts, Policies,
Catalog, Builder, (Agents — hidden in static builds). The target groups navigation into four
sections that map to the phase/persona split above, without changing the underlying flat-route
structure (react-router stays simple; grouping is a nav-rail presentation concern for the design
pass):

| Nav group | Screens | Primary persona |
|---|---|---|
| **Research** | Runs, Run Detail, Catalog, Alerts | Reader + Operator |
| **Author** | Intake/New Run, Plan Review, Run Monitor, Agents (Phase 2), Report Builder | Operator |
| **Govern** | Policies, Audit, Settings → Administration | Operator (role-gated) |
| **Account/Workspace** | Login, Workspace Scoping/Switcher, Settings → Viewer Prefs | Both |
| (utility, not a nav group) | Help, Command Palette (global) | Both |

### 3.2 Full route/screen map — current vs. target

| Route | Screen | Status | Phase | Nav group |
|---|---|---|---|---|
| `/` → `/runs` | Redirect | EXISTS | 1 | — |
| `/runs` | Runs list (Portfolio) | EXISTS | 1 | Research |
| `/runs/:runId` | Run Detail (7 tabs) | EXISTS, ENHANCE (+ Run Monitor state) | 1 | Research |
| `/runs/:runId/swarm` | Legacy redirect shim | EXISTS (deprecated) | — | — |
| `/catalog` (alias `/library`) | Evidence Catalog | EXISTS | 1 | Research |
| `/alerts` | Alerts / attention feed | EXISTS | 1 | Research |
| `/policies` | Policies / governance | EXISTS | 1 | Govern |
| `/audit` | System Audit Log | **NET-NEW** | 1 | Govern |
| `/settings` | Settings (viewer prefs + admin) | EXISTS | 1 (viewer) / 2 (admin depth) | Govern + Account |
| `/help` | Help | EXISTS | 1 | (utility) |
| `/builder` | Report Builder | EXISTS (loopback-only writes) | 1 (read) / 2 (write, always-on) | Author |
| `/agents` | Agent Jobs (launch/monitor) | EXISTS (loopback-only, no static-nav entry) | 2 | Author |
| `/intake` (or `/new`) | Intake / New Run | **NET-NEW** | 1 | Author |
| `/intake/:draftId/plan` | Plan Review | **NET-NEW** | 1 | Author |
| `/runs/:runId?view=monitor` (or dedicated tab) | Run Monitor (live) | **NET-NEW / ENHANCE** of Run Detail | 1 | Author |
| `/login` | Login / Auth | ENHANCE (currently inline, not routed) | 1 | Account |
| (header-level, no dedicated route) | Workspace Scoping/Switcher | **NET-NEW** | 2 | Account |
| (global overlay, `Cmd+K`) | Command Palette | **NET-NEW** | 3 | (utility) |

## 4. Screen-by-screen outline

Each screen below: purpose · primary user(s) · key content/data · capabilities & actions · key
states · components used · status · phase.

### 4.1 Runs list ("Portfolio")

- **Purpose**: Portfolio command center — every run at a glance, triage entry point.
- **Primary user(s)**: Reader (browse), Operator (triage attention queue).
- **Key content/data**: `useRunList()` → `index.json` (static) or `GET /runs` (loopback); per-run
  summary (id, status, created_at, sensitivity, claim_counts, title, linked_projects, category,
  tags).
- **Capabilities & actions**: search/sort/filter by status lane (Published/Verified/In-Progress/
  Blocked); attention-queue and high-claim-volume saved views; metadata facets (project/category/
  tag); click row/card → Run Detail overlay.
- **Key states**: empty (no runs yet → point to Intake); loading (skeleton cards); error (API
  unreachable in loopback mode); permission-gated (none today — list is universally readable).
- **Components used**: `RunCard.tsx`, `FilterTabs.tsx`, `TagFilterPanel.tsx`, `tagColor.ts` — all in
  `frontend/runs-viewer/src/components/RunList/`.
- **Status**: EXISTS (mature, P6 metadata filtering shipped).
- **Phase**: 1.

### 4.2 Run Detail (workspace shell + 7 tabs)

- **Purpose**: The single-run deep-dive workspace — the app's densest, most-used surface.
- **Primary user(s)**: Reader (report/lineage/trust), Operator (writeback/context/monitor).
- **Key content/data**: `useRunDetail(runId)` → `run.json` (static) or `GET /runs/:id` (loopback);
  full `RFRunExport` (schema 1.4) — metadata, claims, sources, verification, governance, lineage,
  report draft, context.
- **Capabilities & actions**: tab switch (`?view=`), deep-link to a claim (`?claim=`), sticky header,
  lineage-node expand → modal; (target, ENHANCE) a **Monitor** state showing live run progress when
  a run is actively executing (Phase 1 net-new behavior on an existing screen).
- **Key states**: empty (pre-1.4 schema → legacy-mode gates on several tabs); loading; error
  (run not found / export missing); permission-gated (sensitivity-redacted quotes below the
  configured threshold); **in-progress** (new state for Run Monitor — partial data, "still running"
  banner).
- **Components used**: `RunDetailWorkspace.tsx`, `detailTabs.ts`, `DetailModal.tsx`,
  `RunDetailModal.tsx` — `frontend/runs-viewer/src/components/RunDetail/`.
- **Status**: EXISTS (mature); Monitor state is ENHANCE.
- **Phase**: 1.

#### 4.2.1 The seven tabs

| Tab | Purpose | Primary user | Key content | Capabilities/actions | Key states | Components | Status/Phase |
|---|---|---|---|---|---|---|---|
| **Overview** | Hero summary + metadata + enrichment | Both | Hero stats (claims/failed-checks/redacted/dangling); metadata (projects, category, tags, AOS identity); enrichment (cost, model profiles, source counts, claim distribution) | "Review Starting Points" (top 4 claims → jump to Ledger) | Every widget independently null-guarded — partial data, never a blank tab | inline `RunOverview`, `RunDetailWorkspace.tsx:177-467` | EXISTS / 1 |
| **Trust** | At-a-glance verification confidence | Reader (trust check), Operator (pre-writeback gate) | 8-stage lifecycle, claim-status distribution, verification checklist | Deep-link failing check → claim (`#clm_NNN`, P3-SEAM-001) | all-pass; has-failures; no-verification-run | `TrustCockpit`, `ClaimStatusDonut`, `TimelineStepper`, `VerificationChecklist` (`components/TrustPanel/`) | EXISTS / 1 |
| **Ledger** (`audit` alias — claim ledger, distinct from system Audit Log §4.9) | Claim-by-claim audit workbench | Reader (verify a claim), Operator (materiality triage) | Full claim table; facets (status/materiality/claim_type/confidence); report-anchor coverage (1.4) | Two-click claim→verbatim-quote; facet filter; coverage strip | legacy (pre-1.4); empty; redacted quote | `ClaimAuditWorkbench`, `ClaimLedgerTable`, `LedgerFacets`, `ProvenanceModal` (`components/ClaimLedger/`) | EXISTS / 1 |
| **Report** | Read synthesized report with inline provenance | Reader (primary surface) | Rendered `report_draft` markdown; inline claim chips; navigable outline | Composition-sidebar filter (supported/inference/speculation); active-section tracking; "Research this" → `/agents` (Phase 2) | no report yet; redacted chip; missing-anchor legacy | `ReportOverlay`, `ReportRenderer`, `CompositionSidebar`, `ReportOutline`, `ReportCoverageStrip`, `ClaimChip` (`components/ReportOverlay/`) | EXISTS / 1 |
| **Lineage** | Trace idea→source→claim→report provenance | Reader (trust drill-down), Operator (debug bad claim) | Full provenance tree | Graph (React Flow) ↔ flat/tree list toggle; expand-badge → `DetailModal` | empty; very-large-tree (no virtualization yet) | `LineageGraph`, `LineageFlow`, `lineageFlowElements`, `lineageLayout`, `lineageTree`, `LineageList`, `LineageDetailPanel`, `kindIcons` (`components/LineageGraph/`) | EXISTS / 1 |
| **Context** (`swarm` alias) | How the run was planned/orchestrated | Operator (debug swarm behavior) | Routing decision, research brief, swarm plan (2-level tree), upstream entities | 4 collapsible sections, persisted collapse state | gated on schema ≥1.3 (empty-state below) | `ContextPane`, `SwarmPane` (`components/RunDetail/`) | EXISTS / 1 |
| **Writeback** | Governance approval + writeback target visibility | Operator | Governance approval status, required-fix note, target count | Today read-only; target: trigger/re-trigger writeback (role-gated) | disabled-tab styling when no writeback export | inline, `RunDetailWorkspace.tsx:146-171` | EXISTS (read) / ENHANCE (trigger) — 1 / 2 |

### 4.3–4.6 Claim Ledger, Lineage graph, Report reader/overlay, Trust/verification

Each requested as a standalone item in the brief — all four are tabs on Run Detail, covered fully in
the table above (§4.2.1: Ledger, Lineage, Report, Trust rows respectively). No standalone route is
proposed; they remain tab-scoped.

### 4.7 Catalog & cross-run search

- **Purpose**: Cross-run/cross-project evidence search — claims, sources, inferences, reports,
  reusable outputs, writebacks.
- **Primary user(s)**: Reader (find prior evidence), Operator (reuse before re-researching).
- **Key content/data**: `useCatalogStats/useCatalogSearch/useCatalogItem` → static client-built index
  (`lib/catalog.ts`) or `GET /api/catalog/*` (loopback); 6-kind union (claim/source/inference/report/
  reusable_output/writeback).
- **Capabilities & actions**: tabbed by item type with live counts; filter by project/status/
  sensitivity; debounced search; right-rail inspector with provenance strip + usage-policy chips;
  "Add to Report" and "Run Follow-up Research" (currently disabled/planned — target: wire both).
- **Key states**: empty (no matches); disabled-action tooltip (loopback required); redacted item.
- **Components used**: `CatalogScreen.tsx`, `lib/catalog.ts`.
- **Status**: EXISTS (mature list+inspector); two actions are stub → ENHANCE.
- **Phase**: 1 (search/browse); 2 (wired actions, since both hand off to authoring surfaces).
- **Target enhancement — cross-run full-text/semantic search**: Catalog search today is scoped to
  catalog items, not raw run content, and Portfolio search is plain substring match
  (`03-web-app.md` §6 gap #5). A unified cross-run search (semantic or full-text) is a **Phase 3**
  net-new capability, likely surfaced both here and in the Command Palette (§5.4).

### 4.8 Writeback status

- **Purpose**: See where a run's outputs have (or haven't) landed downstream.
- **Primary user(s)**: Operator.
- **Key content/data**: today, folded into Run Detail's Writeback tab (§4.2.7) and the Policies
  screen's per-run governance table (§4.10).
- **Capabilities & actions**: (target) a dedicated cross-run writeback status view — which runs are
  approved-but-not-written-back, which writeback targets are configured but never fired (echoing the
  `current-state-and-direction.md` finding that ARC/IntentTree writebacks have never fired live).
- **Key states**: n/a today (no standalone screen).
- **Components used**: n/a today.
- **Status**: **NET-NEW** (currently only a per-run tab + per-run policy row, no cross-run rollup).
- **Phase**: 3 (cross-run rollup is a platform-maturity capability, not a Phase 1/2 blocker).

### 4.9 System Audit Log

- **Purpose**: Who did what, when — mutations, auth events, admin actions. Distinct from the claim
  Ledger tab (§4.2.3), which audits *claims*, not *system actions*.
- **Primary user(s)**: Operator/Admin only.
- **Key content/data**: backend `audit_service.py` + `api/routers/audit.py` already exist and are
  gated by RBAC on read (`current-state-and-direction.md` §2.3) — there is currently **no frontend
  screen** consuming this router.
- **Capabilities & actions**: filterable/sortable audit event table (actor, action, target,
  timestamp, workspace); jump-to-target links (e.g., an audit row for a run mutation links to that
  Run Detail).
- **Key states**: empty; permission-denied (non-admin role); loading.
- **Components used**: none yet — nearest analog is `PoliciesScreen.tsx`'s sortable per-run table
  pattern and `AlertsFeed.tsx`'s card-list pattern.
- **Status**: **NET-NEW** (backend exists, no frontend consumer).
- **Phase**: 1 (backend is already shipped-enforced; UI is cheap and closes a real governance gap
  early).

### 4.10 Policies (global governance + per-run)

- **Purpose**: Global governance config visibility + per-run governance/writeback-approval table.
- **Primary user(s)**: Operator.
- **Key content/data**: `fetchGovernanceConfig()` (static) + per-run `.governance` block across all
  runs.
- **Capabilities & actions**: sort by sensitivity / writeback-approved; graceful "—" for
  pre-migration runs.
- **Key states**: pre-migration run (missing governance block).
- **Components used**: `PoliciesScreen.tsx`.
- **Status**: EXISTS (mature).
- **Phase**: 1.

### 4.11 Report Builder

- **Purpose**: Author/edit a report draft with claim/source evidence attachment, verify, and
  publish-preview.
- **Primary user(s)**: Operator (author role).
- **Key content/data**: `ReportDraft`, `ReportBlock`, `ReportClaimLink`/`ReportSourceLink`; loopback:
  live via `useBuilder` hooks; static: fixed read-only demo draft (`lib/builderMocks.ts`).
- **Capabilities & actions**: 4-pane layout (catalog search → outline+editor → audit inspector →
  claim basket); insert/remove claim & source links; verify + publish-preview mutations; block
  markdown editing.
- **Key states**: static-mode banner ("read-only demo, writes require loopback"); no-permission
  (role lacks `report:edit`); verify-failed (blocking issues listed in audit inspector).
- **Components used**: `BuilderScreen.tsx`, `BuilderCatalogPane`, `BuilderDraftCard`,
  `BuilderOutline`, `BuilderBlockEditor`, `BuilderAuditInspector`, `ClaimBasket` — `frontend/
  runs-viewer/src/components/Builder/`.
- **Status**: EXISTS (loopback-only writes; static mode read-only demo) — target: ENHANCE to an
  always-on authoring surface once the Builder HTTP API is confirmed live end-to-end (per
  `03-web-app.md` §4.6, the API "had not landed" at authoring time of the code).
- **Phase**: 1 (read/demo) / 2 (always-on writes).

### 4.12 Intake / New Run

- **Purpose**: Capture a raw idea and turn it into a research intent — the Phase-1 entry point for
  authoring, replacing "edit `raw_idea.md` by hand."
- **Primary user(s)**: Operator.
- **Key content/data**: maps to the CLI's capture→triage step and the existing `POST /api/runs`
  scaffold+plan endpoint (`current-state-and-direction.md` §2.3) — the endpoint scaffolds and plans
  but never drives the swarm itself, matching a "capture, don't launch" screen.
  Inputs: free-text idea/notes, optional links, target sensitivity, target workspace (if switcher
  exists, §5.2), suggested tags/category.
- **Capabilities & actions**: submit idea → triggers scaffold+plan → navigates to Plan Review
  (§4.13); save-as-draft (don't submit yet); link an existing project/category.
- **Key states**: empty form; submitting (spinner, since plan generation is not instant); error
  (governance-gate rejection surfaced with the specific rule that failed, not a generic 400);
  permission-gated (role lacks `run:create`).
- **Components used**: none yet — nearest analogs are `Builder/BuilderBlockEditor.tsx` (free-text
  authoring) and `Agents/AgentJobLaunchForm.tsx` (form → submit → hand off to a monitor screen).
- **Status**: **NET-NEW**.
- **Phase**: 1.

### 4.13 Plan Review

- **Purpose**: Review the generated research plan (routing decision, research brief, swarm
  composition) before committing to a run — the human-in-the-loop gate for Phase 1 authoring.
- **Primary user(s)**: Operator.
- **Key content/data**: same shape as the existing Run Detail **Context** tab (§4.2.6) — routing
  decision, research brief, swarm plan tree — but rendered *pre-run*, as an editable/approvable
  artifact rather than a read-only historical record.
- **Capabilities & actions**: approve → launches the run (moves to Run Monitor, §4.14); request
  changes / edit brief inline; reject/discard; view estimated cost/model profile before approving.
- **Key states**: awaiting-plan (scaffold still generating); plan-ready (approve/reject); approved
  (transitioning to monitor); rejected (back to Intake, edited).
- **Components used**: none yet — reuse `ContextPane.tsx`'s section layout and collapsible tree
  pattern as the read half; the approve/reject action bar is net-new.
- **Status**: **NET-NEW**.
- **Phase**: 1.

### 4.14 Run Monitor (live)

- **Purpose**: Watch an approved run execute — progress, not control (Phase 1); progress **and**
  control (Phase 2, once agent-job launch/pause/cancel is promoted from `/agents`).
- **Primary user(s)**: Operator.
- **Key content/data**: Phase 1 — polling/streaming status of the run's pipeline stages (capture→
  ingest→extract→claim-map→synthesize→verify→bundle→writeback), surfaced as an enhancement to Run
  Detail (an "in-progress" variant of §4.2's Overview, or a dedicated `monitor` tab). Phase 2 — the
  existing `/agents` screen's live event stream (`useAgentJob*` SSE-like hooks) becomes the
  control+monitor surface for agent-orchestrated runs specifically.
- **Capabilities & actions**: Phase 1: live status only, auto-refresh, "jump to Ledger once claims
  start appearing." Phase 2 (promoting `/agents`): pause/cancel a job, accept evidence-intake
  artifacts, policy-gate summary before launch.
- **Key states**: running (progress bar/stage indicator); stalled (no progress N minutes — surface a
  warning); completed (auto-navigate to the finished Run Detail); failed (error detail + retry
  affordance); rate-limited (reuse the existing GATE-900 rate-limit badge pattern).
- **Components used**: Phase 2 reuses `AgentJobLaunchForm`, `AgentJobEventPanel`,
  `EvidenceIntakePanel`, `PolicyGateSummary` — `frontend/runs-viewer/src/components/Agents/`. Phase 1
  live-status needs a new lightweight stage-progress component.
- **Status**: **NET-NEW** (Phase 1 progress view) layered on **ENHANCE** (Phase 2 promotes existing
  `/agents` from loopback-only/hidden to a first-class, discoverable, flag/role-gated screen).
- **Phase**: 1 (progress) / 2 (control).

### 4.15 Admin — Settings → Administration

- **Purpose**: Auth/RBAC/workspace-member/rate-limit administration for the deployment.
- **Primary user(s)**: Admin/Owner role only.
- **Key content/data**: auth provider status, RBAC enforcement status, workspace member list +
  roles, rate-limit config.
- **Capabilities & actions**: view member roles; (target, Phase 2) assign/change a member's role
  in-app; view/adjust rate-limit thresholds; view auth provider health.
- **Key states**: hidden entirely when `auth.provider == none`; permission-denied banner if a non-
  admin somehow reaches it (defense-in-depth — the real gate is server-side per
  `03-web-app.md` §1.3).
- **Components used**: `WorkspaceMembersPanel`, `RoleAssignmentPanel`, `RateLimitConfigPanel`,
  `AuthProviderStatusPanel`, `RbacStatusPanel` — `frontend/runs-viewer/src/components/
  AdminSettings/`.
- **Status**: EXISTS (own-workspace-only visibility, no cross-tenant admin).
- **Phase**: 1 (visibility) / 2 (role-assignment mutation, if not already wired).

### 4.16 Login / Auth

- **Purpose**: Authenticate into the app under `local_static` or Clerk-hosted auth.
- **Primary user(s)**: Both (gate before any other screen, when auth is on).
- **Key content/data**: `AuthContext.tsx` resolves 3 modes: forced `none` (static export), build-env
  provider (`clerk`/`local_static`), localStorage override, default `none`.
- **Capabilities & actions**: local username/password form → `POST /api/auth/login`; Clerk-hosted
  sign-in redirect; (target) explicit logout affordance in the shell, not just a settings toggle.
- **Key states**: unauthenticated (show login); authenticating (spinner); auth-error (bad
  credentials / Clerk misconfiguration — `clerk_outbound_internet_enabled` gate); authenticated
  (normal shell).
- **Components used**: `AuthContext.tsx`, `ClerkShell.tsx` — `frontend/runs-viewer/src/auth/`.
- **Status**: EXISTS as inline chrome — ENHANCE to a first-class routed `/login` screen with clearer
  states (today it is not a dedicated route per `routes.tsx`).
- **Phase**: 1.

### 4.17 Workspace Scoping / Switcher

- **Purpose**: Show which workspace the current identity is scoped to, and (target) switch between
  workspaces the identity belongs to.
- **Primary user(s)**: Operator/Admin in a small-team deployment.
- **Key content/data**: today, workspace_id is implicit in the token — there is no UI surface for it
  at all (`04-public-service.md` §7: "no `WorkspaceSwitcher` component ... anywhere in the
  frontend"). Target: a persistent header badge showing the active workspace name/id at minimum,
  even before a real switcher exists.
- **Capabilities & actions**: Phase 2 minimum — read-only active-workspace badge (closes the "which
  scope am I in" trust gap even without switching). Phase 2/3 full — dropdown switcher if/when the
  backend grows a multi-workspace-per-identity model (**explicitly not present today** — this is
  aspirational and gated on backend work outside this doc's scope).
- **Key states**: single-workspace (badge only, no dropdown); multi-workspace (dropdown, target);
  mismatch-denied (if enforcement is armed and a stale link points at another workspace's resource —
  should render a clear "not in your workspace" error, not a blank/404).
- **Components used**: none yet.
- **Status**: **NET-NEW**.
- **Phase**: 2 (badge) / 3 (full switcher, backend-dependent).

### 4.18 Audit — see §4.9 (System Audit Log). Listed once; cross-referenced from both the requested
screen list and the IA table (§3.2) to avoid duplication.

## 5. Cross-cutting capabilities

### 5.1 Auth / login

Already covered per-screen (§4.16). Cross-cutting rule: every screen must render correctly in all
three auth states (`none`/`local_static`/`clerk`) without layout shift — today's nav-item role gating
(`AppShell.tsx:87-96,116-124`) is the existing pattern to extend, not replace.

### 5.2 Workspace scoping + RBAC-gated affordances

Two independent gates, both already modeled server-side as parallel `auto|disabled|enabled` enums
(`04-public-service.md` §4): **who can act** (RBAC) and **whose rows they can see/touch** (workspace
isolation). The UI must represent both independently:

- RBAC-gated: hide or disable-with-reason any action the current role's permission matrix (owner/
  admin/researcher/reviewer/viewer) does not allow — e.g., a `viewer` role should never see an
  enabled "Approve Plan" button.
- Workspace-gated: any attempt to open a resource outside the identity's workspace should surface a
  clear "not in your workspace" state, not a silent redirect or blank page — this becomes especially
  important once enforcement flips from advisory to armed (target state per §2.3).
- **Important honesty constraint for design**: today's client-side role checks are explicitly
  defense-in-depth only (`03-web-app.md` §1.3) — the UI should never claim an action is "safe" purely
  because it's rendered; the real gate is server-side. Design should avoid implying false confidence
  (e.g., don't remove server error-handling for actions the UI already hides).

### 5.3 Redaction / sensitivity

`RFSensitivity` ladder (`public` → `personal` → `work_sensitive` → `client_sensitive`) drives quote/
summary redaction, enforced twice (backend at export + frontend defense-in-depth,
`SourceCard.tsx:35-49`). Cross-cutting rule for every screen that renders a source quote: unknown
sensitivity is fail-closed (treated as redacted); the two existing bypasses (`rv_show_all` localStorage
toggle, `VITE_SHOW_ALL=1` build flag) are explicitly LAN-only-tool escapes and should be visually
distinct (a persistent "showing redacted content" banner) wherever active, never a silent state.

### 5.4 Cross-run search / command palette

Today: Portfolio search is plain substring match; Catalog search is real but scoped to catalog
items; no full-text/semantic search across raw run content; no Cmd-K style global navigation
(`03-web-app.md` §6, gaps #5 and #10). Target (Phase 3): a command palette (`Cmd+K`) that (a)
fuzzy-navigates to any screen/run/claim by name, and (b) doubles as the entry point for a unified
cross-run search once one exists. Ground this in the existing debounced-search pattern already
proven in `CatalogScreen.tsx`.

### 5.5 Export / share

Today: Report Builder has verify + publish-preview; report share tokens exist at the API layer
(`share_store.py`), consumed only via a token-authenticated read route
(`GET /api/reports/shares/{token}`) — no UI to *create* a share link, no PDF/markdown export, no
"invite a teammate" flow (`04-public-service.md` §7, `03-web-app.md` §6 gap #8). Target: a "Share"
action on Report Reader and Report Builder that creates/manages a share token, and a "Export" action
that produces a markdown/PDF snapshot — both Phase 3, since they extend rather than block current
functionality.

### 5.6 Notifications / toasts

No dedicated system found in discovery beyond the existing rate-limit badge (GATE-900,
`client.ts:109-157`, `AppShell.tsx:69-74,151-161`) and inline error states per screen. Target: a
lightweight toast system for async action feedback (plan approved, run failed, writeback fired) —
net-new, Phase 1 (needed as soon as Intake/Plan Review/Run Monitor introduce async submit actions).

### 5.7 Empty / error / permission-gated patterns

Existing precedent: `shared/EmptyState.tsx` (reused across Catalog), per-widget null-guarding in
`RunOverview` (every field independently null-safe rather than hiding the whole section), and the
graceful "—" pattern in Policies for pre-migration runs. Cross-cutting rule for every net-new screen:
follow the same three states at minimum — **empty** (no data yet, with a clear next action),
**error** (specific, not generic — surface the governance rule or API error that actually fired),
**permission-gated** (disabled-with-reason, not hidden-without-explanation, except where hiding is
itself the security-conscious choice per §5.2).

### 5.8 Loopback-vs-static data mode caveats

This is the single most important cross-cutting constraint for design agents to internalize: **the
shipped static SPA (`:3030`) has no backend at runtime.** Any screen whose primary function is a
*mutation* (Intake, Plan Review's approve action, Run Monitor's control actions, Builder's writes,
Agents) is **inherently loopback-only** until the "hosted, always-on backend" question is resolved
(`current-state-and-direction.md` §6, axis (c)). Every net-new authoring screen in this outline must
ship with an explicit static-mode fallback state — a "requires a running `rf serve` / hosted backend"
banner, following the precedent already set by Builder's static-mode demo banner and the `/agents`
static-mode informational stub. Design should never assume authoring screens are universally
reachable without checking which data mode is active.

## 6. Targeted component inventory

Design-system seed list. `EXISTS` rows cite the current source path; `NET-NEW` rows note the nearest
existing pattern to inform (not dictate) the new design.

| Component | Role | Source path (if exists) | Status | Reuse notes |
|---|---|---|---|---|
| `RunCard` | Per-run portfolio card | `src/components/RunList/RunCard.tsx` | EXISTS | Every field independently null-safe; exports `deriveFilterState()` |
| `FilterTabs` / `TagFilterPanel` | Saved-view tabs + metadata facets | `src/components/RunList/` | EXISTS | P6 metadata filtering shipped |
| `RunDetailWorkspace` (tab shell) | Generic tab-shell pattern for any multi-tab detail view | `src/components/RunDetail/RunDetailWorkspace.tsx` | EXISTS | Largest single file (~595 lines); the pattern to reuse for Plan Review's similar multi-section layout |
| `DetailModal` | Generic "expand any item" overlay (discriminated union over claim/node/source/issues) | `src/components/RunDetail/DetailModal.tsx` | EXISTS | Reuse for any new "expand this row" need (e.g., Audit Log rows) |
| `ContextPane` | 4-section collapsible plan/routing viewer | `src/components/RunDetail/ContextPane.tsx` | EXISTS | Direct pattern donor for Plan Review (§4.13) |
| `ClaimAuditWorkbench` / `ClaimLedgerTable` / `LedgerFacets` | Dense faceted claim table + inspector | `src/components/ClaimLedger/` | EXISTS | Pattern donor for Audit Log's filterable event table |
| `ProvenanceModal` | Two-click claim→verbatim-quote drill-down | `src/components/ProvenanceModal/ProvenanceModal.tsx` | EXISTS | `ref`-based `open(claimId)`/`close()` API |
| `SourceCard` | Resolved-source card + the primary redaction gate | `src/components/SourceCard/SourceCard.tsx` | EXISTS | `isRedacted()` fail-closed logic — the canonical sensitivity-gate component to reuse anywhere a quote renders |
| **Lineage graph** (`LineageGraph`/`LineageFlow`/`LineageList`/`LineageDetailPanel`) | Graph ↔ list toggle provenance visualizer | `src/components/LineageGraph/` | EXISTS | React Flow v12; both `nodeTypes` and `edgeTypes` must stay registered (past bug: unregistered `smoothstep` edge → invisible edges) |
| **Claim/evidence cards** (`ClaimChip`, `SourceCard`) | Inline claim reference + resolved-source display | `src/components/ReportOverlay/ClaimChip.tsx`, `src/components/SourceCard/` | EXISTS | The two atomic evidence-display units used throughout Report, Ledger, Catalog |
| **Trust meter** (`ClaimStatusDonut`, `TimelineStepper`) | Verification confidence visualization | `src/components/TrustPanel/` | EXISTS | Donut + 8-stage stepper composite is `TrustCockpit.tsx` |
| **Status/maturity badges** (lifecycle badge, sensitivity chip, schema-mismatch badge) | Compact status indicators | `RunCard.tsx` (lifecycle/sensitivity), various | EXISTS | Scattered across RunCard/Policies/Catalog — a design-system pass should consolidate into one badge component family |
| **Run-status pills** | Status-lane indicator (Published/Verified/In-Progress/Blocked) | `src/components/RunList/` (implicit in `FilterTabs`) | EXISTS (implicit) | Currently tab-derived, not a standalone reusable pill component — worth extracting |
| **Tab shells** | Generic tabbed-content container | `RunDetailWorkspace.tsx`, `detailTabs.ts` | EXISTS | The URL-query-driven tab pattern (`?view=`, alias coercion) generalizes well to any future tabbed screen |
| **Filter bar** | Search + facet + sort composite | `CatalogScreen.tsx` (debounced search + facets), `FilterTabs.tsx` | EXISTS (x2, not unified) | Catalog and Portfolio each implement their own filter bar — a design-system pass should unify into one `FilterBar` component |
| **Redaction gate** | Sensitivity-based content blanking | `SourceCard.tsx:35-49` (`isRedacted()`) | EXISTS | The authoritative pattern — any new component rendering source content must call through this, not reimplement |
| `EmptyState` | Generic empty-state block | `src/components/shared/EmptyState.tsx` | EXISTS | Reused across Catalog; extend to every net-new screen (§5.7) |
| **Admin panels** (`WorkspaceMembersPanel`, `RoleAssignmentPanel`, `RateLimitConfigPanel`, `AuthProviderStatusPanel`, `RbacStatusPanel`) | Deployment administration | `src/components/AdminSettings/` | EXISTS | All loopback-API-backed, own-workspace-only |
| **Agent job components** (`AgentJobLaunchForm`, `AgentJobEventPanel`, `EvidenceIntakePanel`, `PolicyGateSummary`) | Launch/monitor/accept agent-orchestrated jobs | `src/components/Agents/` | EXISTS | Direct component donors for Run Monitor's Phase-2 control mode (§4.14) |
| **Builder components** (`BuilderCatalogPane`, `BuilderDraftCard`, `BuilderOutline`, `BuilderBlockEditor`, `BuilderAuditInspector`, `ClaimBasket`) | Report authoring workspace | `src/components/Builder/` | EXISTS | 4-pane layout pattern; `BuilderBlockEditor` is the nearest existing free-text-authoring donor for Intake's idea-capture form |
| **Rate-limit badge** | Reactive GATE-900 rate-limit indicator | `AppShell.tsx:69-74,151-161`, `client.ts:109-157` | EXISTS | Module-level subject pattern — reusable for any future reactive-status badge (e.g., a run-monitor "live" indicator) |
| **Tray / Insert** | Loopback read/write "tray" surface referenced in prior operator memory | — | **DOES NOT EXIST** | Full-tree grep confirms zero hits for `Tray`, `"Tray Insert"`, or `RF_UI_LOOPBACK` in `frontend/runs-viewer/src` — flagged so design work does not assume this component exists; the actual loopback toggle is `VITE_RUNS_FRONTEND_LOOPBACK_API` |
| **Command palette** | Global `Cmd+K` navigation/search overlay | — | **NET-NEW** | No existing donor pattern in-repo beyond Catalog's debounced search; a genuinely new component |
| **Workspace switcher** | Active-workspace badge + (target) switch dropdown | — | **NET-NEW** | No existing donor; backend multi-workspace-per-identity model does not exist yet either (§4.17) |
| **Stage-progress indicator** | Pipeline-stage progress for Run Monitor Phase 1 | — | **NET-NEW** | Nearest donor is `TimelineStepper.tsx` (8-stage lifecycle, but post-hoc/historical, not live-updating) |
| **Toast/notification system** | Async action feedback | — | **NET-NEW** | No existing toast pattern found; only the rate-limit badge does anything similar |
| **Audit event table** | Filterable system-audit-log rows | — | **NET-NEW** | Nearest donor is `PoliciesScreen.tsx`'s sortable per-run table |
| **Approve/Reject action bar** | Plan Review's core interaction | — | **NET-NEW** | No existing donor; closest analog in spirit is Builder's verify/publish-preview gate button row |

## 7. Phased roadmap

### Phase 1 — Intake, Plan Review, Run Monitoring (progress-only); read/verify stays first-class

- Ship: Intake/New Run (§4.12), Plan Review (§4.13), Run Monitor progress view (§4.14, progress-only
  half), Login as a first-class route (§4.16), System Audit Log (§4.9), toast/notification system
  (§5.6).
- Keep mature and unblocked: Runs list, Run Detail (all 7 tabs), Catalog, Alerts, Policies, Settings
  (viewer prefs + admin visibility), Help.
- No live run-control (start/pause/cancel) yet; no workspace switcher yet; no command palette yet.

### Phase 2 — Gated live run-control; small-team RBAC/workspace depth

- Promote `/agents` from loopback-only/undiscoverable to a first-class, flag/role-gated screen —
  Run Monitor gains control actions (§4.14, control half).
- Report Builder becomes always-on for writes (not loopback-gated), contingent on the Builder HTTP
  API being confirmed live end-to-end.
- Workspace scoping badge ships (read-only, §4.17); RBAC-gated affordances become the default pattern
  across all mutation actions introduced in Phase 1 and 2.
- Admin role-assignment mutation (not just visibility) wires up if not already.
- Writeback trigger action (§4.2.7 enhancement) ships.

### Phase 3 — Platform maturity

- Cross-run analytics/trend dashboard, full-text/semantic cross-run search, command palette (§5.4),
  export/share (§5.5), cross-run writeback status rollup (§4.8), full workspace switcher (§4.17,
  contingent on a backend multi-workspace-per-identity model that does not exist today), and the
  DI-1-driven trust-signal surfacing (once the completeness audit lands, exposing *which* surfaces
  are proven workspace-scoped vs. advisory).

## 8. Open questions for design

1. **Nav-rail grouping vs. flat list** (§3.1) — literal grouped-sidebar redesign, or lighter-weight
   dividers/section labels within the existing rail?
2. **Run Monitor placement** (§4.14) — an 8th tab on the already-dense Run Detail shell, or a
   distinct in-progress variant of Overview?
3. **Static-mode authoring fallback prominence** (§5.8) — persistent banner (Builder precedent),
   full-screen gate, or hide Phase 2/3 nav entries entirely for static-mode users?
4. **Command palette launch scope** (§5.4) — navigation-only first, or wait for cross-run search to
   exist so it launches "complete"?
5. **Badge/pill consolidation** (§6) — formalize one `Badge`/`Pill` component family now (triggering
   a `RunCard.tsx`-and-friends refactor), or a purely visual-layer wrapper later?
6. **Workspace switcher UX ahead of the backend model** (§4.17) — ship only the read-only badge in
   Phase 2 and defer switcher visual design to Phase 3, or speculate the full interaction now so
   backend work has a concrete target?
7. **Toast persistence** (§5.6) — transient auto-dismiss only, or should failure toasts persist until
   acknowledged, echoing the Alerts feed's card-persistence model?
