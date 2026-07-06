---
title: "Phase 5: Audit Log"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-07-06
updated: 2026-07-06
feature_slug: public-multiuser-p5-auth-rbac
feature_version: "v1"
phase: 5
phase_title: "Audit Log"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
entry_criteria:
  - "P5.1 durable store (.rf_state/rbac.db) schema exists"
exit_criteria:
  - "Audit-coverage assertion test green: every mutating path in the 6 governed types emits an audit row (or N/A-with-rationale for agent-job launch pending P4)"
  - "Audit-store health probe (AUDIT-004) exists; degraded state is visible via admin warning and API/CLI, not silent"
  - "task-completion-validator sign-off on the ICA-produced wave"
related_documents:
  - .claude/worknotes/public-multiuser-p5-auth-rbac/decisions-block.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
spike_ref: docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
adr_refs:
  - "ADR-001 (auth-provider port / durable-store constraint — audit_event lives in the same store, composed here, not re-decided)"
charter_ref: null
changelog_ref: null
test_plan_ref: null
integration_owner: null
ui_touched: false
target_surfaces:
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/services/builder_service.py
  - src/research_foundry/api/routers/reports.py
  - src/research_foundry/services/writeback.py
  - src/research_foundry/services/source_cards.py
  - src/research_foundry/services/audit_service.py
seam_tasks: []
owner: python-backend-engineer
contributors: [ICA Sonnet 4.6]
priority: high
risk_level: medium
category: "product-planning"
tags: [phase-plan, implementation, audit, ica-offload]
milestone: "public-multiuser-p5"
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/services/audit_service.py
  - src/research_foundry/services/rbac_store.py
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/services/builder_service.py
  - src/research_foundry/api/routers/reports.py
  - src/research_foundry/api/routers/audit.py
  - src/research_foundry/api/app.py
  - src/research_foundry/services/writeback.py
  - src/research_foundry/services/source_cards.py
  - src/research_foundry/cli_commands.py
  - src/research_foundry/cli.py
---

# Phase 5: Audit Log

**Parent Plan**: [Public Multi-User P5 — Auth/RBAC/Isolation/Audit Hardening](../public-multiuser-p5-auth-rbac-v1.md)
**Duration**: ~2-3 days
**Effort**: 4.75 story points
**Dependencies**: P5.1 (Auth-Provider Port + durable RBAC store) complete — the `.rf_state/rbac.db`
schema and connection helper must exist before `audit_event` can extend it. **Not** dependent on
P5.2/P5.3 (RBAC enforcement / workspace migration) at the schema level; this phase runs in parallel
with P5.4 (Clerk) and P5.7 (deferred sensitivity) per the wave plan.
**Team Members**: `python-backend-engineer` (interface + coordination), **ICA Sonnet 4.6** (offload
wave — mechanical wiring + CLI), `task-completion-validator` (mandatory gate on the ICA wave)

---

## Phase Overview

This phase adds an append-only `audit_event` record to Research Foundry: every governed mutation —
catalog (re)import, report-draft edits, agent-job launch (N/A until P4 ships), evidence-artifact
acceptance, publish-preview, and writeback — produces a queryable row capturing who did what, from
which source, and under which policy snapshot (PRD FR-8; success metric: "100% of 6 governed
mutation types produce an audit_event row").

The `audit_event` table lives in the **same durable store** established in Phase 1
(`<workspace>/.rf_state/rbac.db`) — never `catalog.db`, which is an explicitly disposable cache that
drops and rebuilds on `PRAGMA user_version` mismatch (P2/P3 D10, landmine #3). Audit state must
survive a catalog rebuild the same way identity/RBAC state must.

### Goals

- Ship `audit_event` schema (in `rbac.db`) + `audit_service.py` with a single, fail-open write
  entrypoint (`record_event`) and read/list functions.
- Wire an audit-write call into every one of the 5 governed mutation types currently implemented in
  the codebase; add a documented, forward-compatible N/A placeholder for the 6th (agent-job launch)
  until P4 lands `api/routers/agent_jobs.py`.
- Expose the audit log via `rf audit list`/`rf audit show` (CLI) and a minimal read API
  (`GET /api/audit`, `GET /api/audit/{audit_event_id}`).
- Precisely separate two failure domains that are easy to conflate: a failed **audit write** must
  fail open (never block or corrupt the mutation it's recording); a failed **authorization check**
  (RBAC, owned by P5.2) must fail closed. This phase owns only the former.
- Make a persistently-failing audit store **visible, not silent**: add a startup/on-demand health
  probe, a durable degraded-health state, an admin-facing warning, and a public-exposure gate that
  requires the audit store to be writable before shared/public exposure is allowed — without ever
  making an individual mutation's own fail-open guarantee conditional on audit health (AUDIT-004).
  A silently-broken audit store that never surfaces to an operator defeats the entire "100% of
  governed mutation types produce an audit_event row" guarantee this phase exists to provide.

### Architecture Focus

- **Layer**: Service (new `audit_service.py`) + thin Repository-equivalent (`rbac.db` schema
  extension) + API (new `audit.py` router) + CLI (`rf audit` command group).
- **Patterns**: Append-only event table (no UPDATE/DELETE — audit rows are immutable); single
  fail-open write entrypoint mirroring the project's existing `governance.py::guard_check` idiom of
  "never let an observability/policy side-channel corrupt the primary path"; cursor-paginated list
  endpoint per the project's standard API list-shape convention.
- **Standards**: OpenTelemetry spans + structured JSON logs on every `record_event` call (success and
  failure), per PRD NFR-Observability.

---

## Offload Plan (ICA Sonnet 4.6 — one of only 3 phases in this plan with an ICA wave)

This phase is contract-clear once the interface is fixed, which is exactly the offload profile the
decisions block (§2, §6) calls for. Be explicit about the split:

**What's offloaded to ICA Sonnet 4.6**:
- The mechanical wiring of audit-write calls into the 5 available mutation call-sites (AUDIT-002)
  once `audit_service.py`'s interface and the `audit_event` schema are fixed by Claude.
- The CLI command implementation for `rf audit list` / `rf audit show` (AUDIT-003), and the
  corresponding thin `GET /api/audit` / `GET /api/audit/{id}` read-router handlers.

**What stays on Claude (sonnet)**:
- `audit_service.py`'s interface/schema design (AUDIT-001) — the `AuditEvent` shape, the
  `mutation_type` taxonomy (including the forward-compat `agent_job_launched` placeholder), and the
  `record_event`/`list_events`/`get_event` function contracts.
- The durable-store integration decision: coordinating with Phase 1's `rbac.db` schema and reusing
  its connection helper (see Task AUDIT-001 Implementation Notes) rather than opening a second,
  competing SQLite connection path to the same file.
- The fail-open-audit / fail-closed-mutation distinction in the write path (see Risk Mitigation
  below) — this is a security-adjacent correctness property, not mechanical wiring, and stays on
  Claude even though the call-site wiring itself is offloadable.
- The audit-store health probe, degraded-health state, admin warning, and public-exposure gate
  (AUDIT-004) — this is the same class of security-adjacent correctness property as the fail-open/
  fail-closed distinction above (a silently-degraded audit store is a governance gap, not a
  mechanical feature), and stays on Claude in full — not offloaded to ICA at all.

**Validator gate (mandatory)**: The ICA-produced wave (AUDIT-002 wiring + AUDIT-003 CLI/API) **must**
pass `task-completion-validator` review before being considered complete. Do not merge or accept ICA
output without this gate — this is the phase's primary quality gate (see Quality Gates below) and is
called out explicitly in the parent plan's Model & Offload Routing section.

---

## Task Breakdown

### Epic: Audit Log

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|----------------------|----------|------------------------|-------|--------|--------------|
| AUDIT-001 | `audit_event` schema + `audit_service.py` interface | Design the append-only `audit_event` table (in `rbac.db`) and the `audit_service.py` module: `AuditEvent` dataclass, `record_event`, `list_events`, `get_event`. Claude-owned (not offloaded). | See Task AUDIT-001 below | 1.5 pts | python-backend-engineer | sonnet | adaptive | P5.1 durable store exists |
| AUDIT-002 | Wire audit-write calls into the 5 available mutation types + N/A note for agent-job launch | Add `audit_service.record_event(...)` calls at the 5 real call-sites; document the 6th (agent-job launch) as N/A-pending-P4 with a reserved taxonomy slot. **ICA offload wave.** | See Task AUDIT-002 below | 1.5 pts | python-backend-engineer (design), **ICA Sonnet 4.6** (wiring) | sonnet | adaptive | AUDIT-001 |
| AUDIT-003 | `rf audit list`/`show` CLI + `GET /api/audit` read API | Add a `audit` Typer sub-app (`rf audit list`, `rf audit show <id>`) and a thin `api/routers/audit.py` with `GET /api/audit` (cursor-paginated) + `GET /api/audit/{audit_event_id}`. **ICA offload wave.** | See Task AUDIT-003 below | 0.75 pts | **ICA Sonnet 4.6** | sonnet | adaptive | AUDIT-001 |
| AUDIT-004 | Audit-store degraded-health state + startup/write probe + admin warning + public-exposure gate | Health probe (write-then-read against `rbac.db`'s `audit_event` table) run at `create_app` startup and on-demand; durable `audit_degraded` state; admin-visible warning (`rf audit health`, `GET /api/audit/health`); flags the requirement — enforced at the actual exposure point in P5.6 — that shared/public exposure is blocked while degraded. Claude-owned, not offloaded. | See Task AUDIT-004 below | 0.75 pts | python-backend-engineer | sonnet | adaptive | AUDIT-001 |
| AUDIT-900 | AC: FE handles missing audit-row fields (conditional) | R-P2 forward-compat AC — applies only if Phase 6/8 ships an admin-settings audit-log UI view. | See Task AUDIT-900 below | 0.25 pts | ui-engineer-enhanced (Phase 8, if applicable) | sonnet | adaptive | AUDIT-001 (schema), Phase 8 (conditional trigger) |
| **Total** | — | — | — | **4.75 pts** | — | — | — | — |

**Model Selection Guidance**: `python-backend-engineer` owns interface/schema design and reviews the
ICA output; ICA Sonnet 4.6 executes the two offloadable waves (AUDIT-002 wiring, AUDIT-003 CLI/API)
behind the mandatory `task-completion-validator` gate. AUDIT-004 (health/degraded-state/exposure-gate)
stays on Claude in full, same as AUDIT-001. AUDIT-900 is not executed in this phase — it
is a forward-referenced conditional AC consumed by Phase 8's phase file.

---

## Detailed Task Specifications

### Task AUDIT-001: `audit_event` schema + `audit_service.py` interface

**Estimate**: 1.5 points
**Assigned Subagent(s)**: python-backend-engineer
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: P5.1 durable store (`.rf_state/rbac.db`) schema exists
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:

Design and implement the `audit_event` table (extending Phase 1's `rbac.db` schema, via a migration
step consistent with however P5.1 versions that store) and `src/research_foundry/services/audit_service.py`.

`audit_event` columns (append-only; no UPDATE/DELETE path):
- `audit_event_id` (TEXT PRIMARY KEY — ULID or UUID4)
- `created_at` (TEXT, ISO-8601 UTC)
- `mutation_type` (TEXT — enum: `catalog_mutation` | `report_edit` | `agent_job_launched` |
  `artifact_accepted` | `publish_preview` | `writeback`; **all 6 values reserved now**, even though
  only 5 are wired in this phase — see AUDIT-002)
- `action` (TEXT — e.g. `import_run`, `create_draft`, `update_block`, `delete_draft`, `ingest_source`,
  `publish_preview`, `writeback`)
- `target_ref` (TEXT — the run_id / report_draft_id / source_card_id / writeback run_id being acted on)
- `actor_user_id` (TEXT, nullable — null when `auth_mode=none`/no identity resolved, matching P5.1's
  `AuthIdentity` shape)
- `actor_workspace_id` (TEXT, nullable)
- `source_ref` (TEXT, nullable — provenance of the triggering request, e.g. CLI vs API)
- `policy_snapshot` (TEXT, JSON-encoded — sensitivity threshold, resolved role, auth provider name at
  time of action)
- `result` (TEXT — `success` | `failure` | `denied`)
- `error_detail` (TEXT, nullable)
- `trace_id` / `span_id` (TEXT, nullable — OTel correlation, per PRD NFR-Observability)

`audit_service.py` public interface:
- `record_event(paths: FoundryPaths, event: AuditEvent) -> str | None` — the single write entrypoint.
  **Fail-open**: wraps its own SQLite write in `try/except`; on failure, logs a structured `ERROR`
  (full event context, never silently swallowed) and emits an OTel span with `status=ERROR`, then
  returns `None` — it never raises into the caller. Callers invoke this **after** their own mutation
  has already committed, so an audit-write failure cannot roll back or corrupt the mutation's durable
  state (see Risk Mitigation).
- `list_events(paths, *, mutation_type=None, actor_user_id=None, workspace_id=None, since=None,
  until=None, limit=50, cursor=None) -> dict` — cursor-paginated, per the project's standard list-API
  shape.
- `get_event(paths, audit_event_id: str) -> dict | None`.
- `AuditEvent` — a frozen dataclass mirroring the columns above (required: `mutation_type`, `action`,
  `target_ref`; everything else optional/nullable).

**Acceptance Criteria**:
- [ ] `audit_event` table created in `.rf_state/rbac.db` (NOT `catalog.db`); schema migration is
      idempotent (safe to run against an existing store).
- [ ] `audit_service.py` reuses Phase 1's SQLite connection helper for `rbac.db` (see Implementation
      Notes) rather than opening a second, independent connection path to the same file.
- [ ] `record_event()` never raises on a write failure; a forced write failure (e.g. read-only mount,
      simulated in a unit test) still logs a structured ERROR and returns `None`.
- [ ] `mutation_type` enum reserves all 6 values now (including `agent_job_launched`), even though
      only 5 are wired to a real call-site in this phase.
- [ ] `list_events`/`get_event` unit-tested against a seeded `rbac.db` fixture.

**Implementation Notes**:
- Coordinate with Phase 1's actual `rbac_store.py` (or equivalent module name) for the connection
  helper (`_connect`/`_db`-style context manager) — reconcile the exact helper name/signature against
  Phase 1's shipped implementation at execution time; this phase's entry criterion is that the P5.1
  store exists, not a specific function name.
- `record_event` should be called **after** the primary mutation's own commit, never inside the same
  transaction — this is what makes the fail-open guarantee real rather than aspirational.
- Mirror the project's existing `governance.py::guard_check` idiom of treating a policy/observability
  side-channel as advisory-but-loud, not blocking.

**Files Involved**:
- `src/research_foundry/services/audit_service.py` — new module (schema init, `AuditEvent`,
  `record_event`, `list_events`, `get_event`).
- `src/research_foundry/services/rbac_store.py` — read/reuse Phase 1's connection helper; do not
  duplicate schema-init logic outside the shared module if P5.1 already centralizes it.

---

### Task AUDIT-002: Wire audit-write calls into the 5 available mutation types (+ N/A note)

**Estimate**: 1.5 points
**Assigned Subagent(s)**: python-backend-engineer (design of call-site contract), **ICA Sonnet 4.6**
(mechanical wiring)
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: AUDIT-001
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:

Wire `audit_service.record_event(...)` into each of the 5 governed mutation types that exist in the
codebase today, using the concrete call-sites confirmed by direct code read (2026-07-06):

1. **Catalog mutation** (`mutation_type="catalog_mutation"`) — hook inside
   `catalog_service.import_run()` (`services/catalog_service.py:1080`), immediately after
   `conn.commit()` succeeds. `import_all()` (`:1108`) loops `import_run()` per discovered run, so
   wiring only `import_run()` gives one audit row per imported run for both
   `POST /catalog/import/run/{run_id}` and `POST /catalog/import` (`api/routers/catalog.py:92,105`) —
   do not duplicate the call in `import_all()`.
2. **Report edit** (`mutation_type="report_edit"`) — hook inside `builder_service._save_draft()`
   (`services/builder_service.py:282`), the single choke-point called by `create_draft`, block
   add/reorder/update, claim-link/source-link add, and version-snapshot creation (11 call-sites
   confirmed, `:394,453,486,498,511,641,654,693,713,754,787`). Add a **separate** explicit call inside
   `delete_draft()` (`:318`), which does not route through `_save_draft` (the draft is removed, not
   re-persisted).
3. **Agent-job launch** (`mutation_type="agent_job_launched"`) — **N/A in this phase.**
   `src/research_foundry/api/routers/agent_jobs.py` does not exist yet (confirmed: only
   `catalog.py`, `reports.py`, `runs.py` exist under `api/routers/` as of 2026-07-06) — this is the
   same "pending P4" pattern used elsewhere in this plan (parent plan: "P5.2's `agent_jobs.py` target
   surface... compose with P4's ADR-002 once it ships, contract-test fallback if P4 slips"). The
   `agent_job_launched` mutation_type is already reserved in AUDIT-001's taxonomy so P4 (or a later
   P5 follow-up) only needs to add the call-site, not touch `audit_service.py`'s interface.
4. **Accepted artifact** (`mutation_type="artifact_accepted"`) — hook inside
   `services/source_cards.py::ingest_source()`/`create_source_card()` (invoked via CLI
   `cli_commands.py:239` `rf ingest` and `:272` `rf source-card create` — confirmed as the "accepted
   artifact" governed type; there is no API-routed equivalent today, only CLI).
5. **Publish preview** (`mutation_type="publish_preview"`) — hook inside
   `api/routers/reports.py::publish_preview()` (`:627`), recording both the pass case (`ok: true`) and
   the fail-closed HTTP 422 case (`result="denied"`, `error_detail` = the failing check IDs) — a
   blocked publish attempt is itself audit-worthy.
6. **Writeback** (`mutation_type="writeback"`) — hook inside `services/writeback.py::writeback()`
   (`:960`), invoked via CLI `cli_commands.py:488`. Record both success and the `RFError` failure path
   (`result="failure"`, `error_detail=str(e)`) — a failed writeback attempt is audit-worthy the same
   way a failed publish-preview is.

**Acceptance Criteria**:
- [ ] `catalog_service.import_run()` emits one `catalog_mutation` audit row per successful import,
      after commit.
- [ ] `builder_service._save_draft()` emits one `report_edit` audit row per save; `delete_draft()`
      emits its own `report_edit` row (action=`delete_draft`).
- [ ] `services/source_cards.py::ingest_source()`/`create_source_card()` emits one `artifact_accepted`
      row per successful ingest.
- [ ] `reports.py::publish_preview()` emits one `publish_preview` row per call, `result` reflecting
      pass/fail.
- [ ] `writeback.py::writeback()` emits one `writeback` row per call, `result` reflecting
      success/failure, never raising a *second* exception if the audit write itself fails.
- [ ] Agent-job launch is explicitly documented (code comment + this phase file) as N/A pending P4,
      with the `agent_job_launched` taxonomy value already reserved — not a schema change later.
- [ ] None of the above call-sites' audit-write hook can cause the underlying mutation to fail,
      rollback, or return a different HTTP status than it would have without the audit hook (verified
      by a fault-injection unit test that forces `record_event` to raise/fail internally and asserts
      the mutation still succeeds).

**Implementation Notes**:
- This is the primary ICA Sonnet 4.6 offload wave. The call-site contract (which function, which
  `mutation_type`/`action` values, before-or-after-commit placement) is fixed by AUDIT-001 and this
  task's description — ICA's job is mechanical: import `audit_service`, construct the `AuditEvent`,
  call `record_event`, at each of the 5 named locations. Do not redesign the interface.
- `task-completion-validator` review of this wave is mandatory before merge (see Quality Gates).

**Files Involved**:
- `src/research_foundry/services/catalog_service.py` — `import_run()`.
- `src/research_foundry/services/builder_service.py` — `_save_draft()`, `delete_draft()`.
- `src/research_foundry/services/source_cards.py` — `ingest_source()`, `create_source_card()`.
- `src/research_foundry/api/routers/reports.py` — `publish_preview()`.
- `src/research_foundry/services/writeback.py` — `writeback()`.

---

### Task AUDIT-003: `rf audit list`/`show` CLI + `GET /api/audit` read API

**Estimate**: 0.75 points
**Assigned Subagent(s)**: **ICA Sonnet 4.6**
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: AUDIT-001
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:

Expose the audit log for operator consumption via CLI and a minimal read API, following existing
project conventions exactly (no new patterns):

- **CLI**: add an `audit_app = typer.Typer(...)` sub-app registered via
  `app.add_typer(audit_app, name="audit")` in `cli.py`, mirroring the existing `source_card_app`
  pattern (`cli_commands.py:262-264`). Commands: `rf audit list [--mutation-type] [--actor]
  [--workspace] [--since] [--until] [--limit] [--cursor] [--json]` and
  `rf audit show <audit_event_id> [--json]`, both calling `audit_service.list_events`/`get_event`.
- **API**: new `src/research_foundry/api/routers/audit.py` (`router = APIRouter()`, mirroring
  `catalog.py`/`reports.py`), with `GET /api/audit` (cursor-paginated, same query params as the CLI)
  and `GET /api/audit/{audit_event_id}`. Register via `app.include_router(audit_router, prefix="/api",
  tags=["audit"])` in `api/app.py`, mirroring the existing router registrations (`api/app.py:158-164`).

**Acceptance Criteria**:
- [ ] `rf audit list` and `rf audit show <id>` work against a seeded `rbac.db` fixture, both
      human-readable (Rich table) and `--json` output modes.
- [ ] `GET /api/audit` returns a cursor-paginated envelope consistent with the project's other list
      endpoints; `GET /api/audit/{id}` returns 404 (not an existence-leak — audit read access itself
      is not sensitivity-scoped in this phase) for an unknown ID.
- [ ] Both CLI and API read paths use `audit_service.list_events`/`get_event` only — no direct SQL
      outside `audit_service.py`.

**Implementation Notes**:
- **Coordination note (not blocking this phase, flag for P5.2/P5.9)**: the audit log is
  security-sensitive read data; once P5.2's `require_role(...)` dependency exists, `GET /api/audit`
  and `GET /api/audit/{id}` should be gated to `admin`/`owner` roles. This phase's wave-plan
  dependency is only on P5.1 (not P5.2), so ship the endpoints without a role gate now and add
  `require_role("admin")` as a one-line follow-up once P5.2 merges — do not block this task on P5.2's
  completion. Record this as a note for P5.9's regression pass to confirm it landed.
- ICA offload wave — same validator gate as AUDIT-002.

**Files Involved**:
- `src/research_foundry/api/routers/audit.py` — new.
- `src/research_foundry/api/app.py` — router registration.
- `src/research_foundry/cli_commands.py` — `audit_app` Typer commands.
- `src/research_foundry/cli.py` — sub-app registration (if `cli.py` is where `app.add_typer` calls
  live; confirm against the `source_card_app` registration site during implementation).

---

### Task AUDIT-004: Audit-store degraded-health state + startup/write probe + admin warning + public-exposure gate

**Estimate**: 0.75 points
**Assigned Subagent(s)**: python-backend-engineer
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: AUDIT-001
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:

AUDIT-001/002 establish that a failed *individual* audit write fails open (never blocks the
mutation it's recording) and logs loudly. That guarantee has a blind spot this task closes: if the
audit store itself is persistently unwritable (disk full, permissions error, corrupted `rbac.db`),
every mutation still succeeds and every audit write still fails — silently, from an operator's
perspective, because the per-event error log is easy to miss and there is no aggregate signal that
"the audit trail has stopped working." A workspace could run for weeks with zero audit coverage and
nothing would surface that fact to an operator deciding whether to share it.

This task adds the missing signal, without changing AUDIT-001/002's fail-open write contract:

1. **Health probe**: `audit_service.health_check(paths) -> AuditHealth` performs an actual
   write-then-read round trip against a dedicated probe row in the `audit_event` table (not a mere
   "can I open the file" check) and returns `AuditHealth(healthy: bool, last_probe_at: str,
   last_success_at: str | None, error_detail: str | None)`. Run this probe (a) once at `create_app`
   startup (`api/app.py`), and (b) on-demand whenever `GET /api/audit/health` or `rf audit health` is
   invoked.
2. **Durable degraded-health state**: persist the most recent probe result in `rbac.db` (a small
   `audit_health` table or a single-row state record — reuse Phase 1's connection helper, same as
   AUDIT-001) so the degraded state survives a process restart and is visible across CLI/API/admin
   surfaces consistently, not just held in an in-process variable that resets on restart.
3. **Admin warning**: `rf audit health` (CLI) and `GET /api/audit/health` (API) surface the current
   state prominently — a degraded state is a **loud, top-level warning** (Rich `[red]DEGRADED[/red]`
   panel in the CLI; a non-2xx-adjacent but clearly-flagged `status: "degraded"` field in the API
   response), not a buried log line.
4. **Public-exposure gate (mechanism built here, enforced at the exposure point in P5.6)**: expose a
   single, simple check — `audit_service.is_healthy_for_exposure(paths) -> bool` — that P5.6's
   sharing/publish-preview flow calls before allowing any shared/public-facing exposure action. This
   task builds and unit-tests the check itself; wiring it into the actual exposure decision point is
   P5.6's responsibility (coordination note below, same pattern as AUDIT-003's P5.2 role-gate note).

**Acceptance Criteria**:
- [ ] `audit_service.health_check(paths)` performs a real write-then-read probe against
      `audit_event` (not a file-existence check) and returns a structured `AuditHealth` result.
- [ ] The most recent health result is durable (survives a process restart) — a unit test kills and
      re-creates the connection between a forced-degraded probe and a subsequent read, and asserts
      the degraded state is still reported.
- [ ] `rf audit health [--json]` and `GET /api/audit/health` both surface the current state, and a
      degraded result is visually/structurally distinct from a healthy one (not the same shape with
      a different string buried in a field).
- [ ] `audit_service.is_healthy_for_exposure(paths)` exists, is unit-tested against both a healthy
      and a forced-degraded fixture, and returns `False` (fail-closed for *exposure*, not for
      individual writes) when the store is degraded.
- [ ] This task does **not** make any individual mutation's audit write fail-closed — AUDIT-001/002's
      fail-open write contract is unchanged; only the *exposure* decision (owned by P5.6) becomes
      conditional on audit health.
- [ ] A coordination note is recorded (see Implementation Notes) flagging that P5.6 must call
      `is_healthy_for_exposure()` before enabling shared/public exposure — this task does not itself
      modify P5.6's sharing/publish-preview flow.

**Implementation Notes**:
- **Coordination note (not blocking this phase, flag for P5.6/P5.9)**: this task ships the health
  probe and the `is_healthy_for_exposure()` check; it does **not** wire that check into P5.6's
  sharing/publish-preview flow or Human Gate #2's public/LAN-exposure decision — that wiring is
  P5.6's responsibility (mirrors AUDIT-003's existing P5.2 role-gate coordination note pattern).
  Record this as a note for P5.9's regression pass to confirm P5.6 actually calls it.
- Do not conflate this with AUDIT-001/002's fail-open write guarantee — a degraded audit store still
  never blocks a mutation. This task only makes the degradation *visible* and gates *exposure*, two
  different, narrower things than gating every write.
- Reuse Phase 1's `rbac.db` connection helper for the health-state persistence, same as AUDIT-001 —
  do not open a second connection path.

**Files Involved**:
- `src/research_foundry/services/audit_service.py` — `health_check()`, `is_healthy_for_exposure()`,
  `AuditHealth` dataclass, health-state persistence.
- `src/research_foundry/api/routers/audit.py` — `GET /api/audit/health`.
- `src/research_foundry/api/app.py` — startup health probe invocation.
- `src/research_foundry/cli_commands.py` — `rf audit health` command.
- `tests/unit/test_audit_service.py` (or equivalent) — health-probe, durability, and
  `is_healthy_for_exposure()` unit tests.

---

### Task AUDIT-900: AC: FE handles missing audit-row fields (conditional)

**Estimate**: 0.25 points
**Assigned Subagent(s)**: ui-engineer-enhanced (only if triggered — see below)
**Model**: sonnet
**Effort**: adaptive
**Dependencies**: AUDIT-001 (schema must exist to know which fields are nullable); Phase 6 (P5.6)
admin-settings scope decision (conditional trigger)
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:

R-P2 (Plan Generator Rule) requires that every new backend field introduce an implicit "FE handles
missing X" AC. This phase introduces several nullable `audit_event` fields
(`actor_user_id`/`actor_workspace_id`/`error_detail`/`trace_id`/`span_id`), but this phase does not
itself build a UI surface — Phase 6 (P5.6, rate limits + admin settings + sharing gates) or Phase 8
(P5.8, auth-context UI) *might* surface the audit log in the admin settings UI; this is explicitly
TBD as of this phase's authoring.

**IMPORTANT — this task ID is referenced by the Phase 8 (frontend) phase file. Do not renumber this
ID (`AUDIT-900`) even when marking it N/A.**

**Acceptance Criteria**:

#### AC AUDIT-900: FE handles missing/malformed audit_event fields (conditional)
- target_surfaces:
    - frontend/runs-viewer/src/pages/AdminSettings*.tsx  # speculative — exact component TBD by Phase 6/8
- propagation_contract: >
    IF Phase 6 (P5.6) or Phase 8 (P5.8) admin settings exposes an audit-log view in the UI, this AC
    applies: the audit-log list/detail view renders the row using `audit_service`'s
    `list_events`/`get_event` response shape as-is (no client-side re-shaping of nullable fields).
- resilience: >
    FE renders a fallback ("audit data unavailable") for the specific field or row rather than
    crashing, when a field is null/missing/malformed (e.g. `actor_user_id` null under
    `auth_mode=none`, or a legacy pre-migration row missing `policy_snapshot`).
- visual_evidence_required: false
- verified_by:
    - "Phase 8 (P5.8) phase file assigns the concrete verifying task ID when/if the admin
      audit-log UI is built; if Phase 6/8 does not surface audit in the UI, this AC is marked N/A
      with that rationale recorded in Phase 8's phase file."

**Implementation Notes**:
- This task is **not executed in this phase**. It exists here only to satisfy R-P2 at the point the
  backend field is introduced, and to give Phase 6/8 authoring a stable, pre-reserved ID to resolve
  against (N/A-with-rationale, or implemented) once that phase's UI scope is decided.

**Files Involved**:
- None in this phase. Resolved by Phase 6 (P5.6) or Phase 8 (P5.8) phase files.

---

## Quality Gates

This phase is complete when:

- [ ] **Functional**: All 5 available mutation types (catalog, report edit, artifact accepted,
      publish preview, writeback) emit an `audit_event` row; agent-job launch is documented N/A with
      the taxonomy slot reserved.
- [ ] **Testing**: Audit-coverage assertion test green (parametrized over the 6 governed types, one
      of which asserts N/A-with-rationale); fault-injection test proves a forced `record_event`
      failure never breaks the underlying mutation; AUDIT-004's health-probe durability and
      `is_healthy_for_exposure()` tests green.
- [ ] **Performance**: N/A for this phase (no explicit perf budget beyond "does not block the
      mutation path," covered by the fault-injection test above).
- [ ] **Security**: Audit rows never contain raw secrets/credentials (reuse
      `governance.py::scan_secrets`/`_redact` on any free-text `error_detail` field before
      persisting). Audit-store degradation is visible (not silent) via a durable health state, an
      admin warning (`rf audit health`/`GET /api/audit/health`), and a coordination note requiring
      P5.6 to gate shared/public exposure on `is_healthy_for_exposure()` (AUDIT-004).
- [ ] **Documentation**: `rf audit list`/`show` documented in CLI help text (Typer `--help` is
      sufficient; no separate doc file required for this phase — full docs land in P5.9).
- [ ] **Code Quality**: `flake8`/`mypy` clean on all touched files.
- [ ] **Architecture**: `audit_event` lives in `.rf_state/rbac.db`, never `catalog.db`; `audit_service.py`
      is the only module performing writes to the `audit_event` table.
- [ ] **task-completion-validator sign-off on the ICA-produced wave** (AUDIT-002 + AUDIT-003) — this
      is the phase's primary quality gate; do not merge the ICA output without it.
- [ ] **Seam verification**: N/A — `integration_owner` is null; no cross-owner-specialty seam in this
      phase (both AUDIT-001 design and AUDIT-002/003 offload wiring are backend/python-backend
      specialty; the ICA/Claude split is an execution-tier distinction, not an owner-specialty one).
- [ ] **Runtime smoke**: N/A — `ui_touched: false`; no `.tsx` file is touched by this phase.

No `karen` gate and no human gate apply to this phase (per parent plan Phase Summary table).

---

## Integration Points

### External Systems

- **None** — this phase is entirely internal (SQLite store + FastAPI routes + Typer CLI).

### Internal Systems

- **Phase 1 (`.rf_state/rbac.db`)**: this phase's `audit_event` table is added to the same durable
  store and must reuse Phase 1's connection helper — the single most load-bearing coordination point
  in this phase (see AUDIT-001 Implementation Notes).
- **Phase 2 (RBAC enforcement)**: not a hard dependency for this phase's wave (P5.5 depends only on
  P5.1), but `GET /api/audit*` should gain a `require_role("admin")` gate once P5.2 lands — flagged as
  a coordination note in AUDIT-003, not blocking this phase's completion.
- **Phase 4 (P4 agent-job launch)**: the `agent_job_launched` mutation_type is reserved now; wiring
  the actual call-site is P4's (or a later P5 follow-up's) job once `api/routers/agent_jobs.py`
  exists.
- **Phase 6/8 (admin settings / auth-context UI)**: AUDIT-900 is the forward-referenced, conditional
  AC these phases must resolve (implement or N/A-with-rationale) — do not renumber it. Phase 6
  (P5.6) additionally consumes AUDIT-004's `is_healthy_for_exposure()` check and must call it before
  enabling any shared/public exposure action (sharing links, publish-preview) — this phase builds
  the check, P5.6 wires the enforcement; P5.6's already-scheduled karen public-exposure milestone is
  the natural review point for confirming that wiring landed.
- **Phase 9 (regression/E2E/docs)**: the audit-coverage assertion test, the `GET /api/audit`
  role-gate follow-up (see AUDIT-003), and confirmation that P5.6 actually calls
  `is_healthy_for_exposure()` before exposure (AUDIT-004) are all candidates for P5.9's regression
  sweep to confirm.

---

## Key Files Modified

| File Path | Purpose | Subagent |
|-----------|---------|----------|
| `src/research_foundry/services/audit_service.py` | New: `AuditEvent`, `record_event`, `list_events`, `get_event`, schema init | python-backend-engineer |
| `src/research_foundry/services/rbac_store.py` | Reuse connection helper for `rbac.db` | python-backend-engineer |
| `src/research_foundry/services/catalog_service.py` | Audit hook in `import_run()` | ICA Sonnet 4.6 |
| `src/research_foundry/services/builder_service.py` | Audit hook in `_save_draft()`, `delete_draft()` | ICA Sonnet 4.6 |
| `src/research_foundry/services/source_cards.py` | Audit hook in `ingest_source()`/`create_source_card()` | ICA Sonnet 4.6 |
| `src/research_foundry/api/routers/reports.py` | Audit hook in `publish_preview()` | ICA Sonnet 4.6 |
| `src/research_foundry/services/writeback.py` | Audit hook in `writeback()` | ICA Sonnet 4.6 |
| `src/research_foundry/api/routers/audit.py` | New: `GET /api/audit`, `GET /api/audit/{id}`, `GET /api/audit/health` (AUDIT-004) | ICA Sonnet 4.6 (list/get), python-backend-engineer (health) |
| `src/research_foundry/api/app.py` | Register `audit_router`; startup audit-health probe invocation (AUDIT-004) | ICA Sonnet 4.6 (registration), python-backend-engineer (startup probe) |
| `src/research_foundry/cli_commands.py` | New `audit_app` Typer sub-app; `rf audit health` (AUDIT-004) | ICA Sonnet 4.6 (`audit_app` base), python-backend-engineer (`health` subcommand) |
| `src/research_foundry/cli.py` | Register `audit_app` | ICA Sonnet 4.6 |
| `tests/unit/test_audit_service.py` | Health-probe, durability, `is_healthy_for_exposure()` tests (AUDIT-004) | python-backend-engineer |

---

## Testing Strategy

### Unit Tests

- `audit_service.record_event`/`list_events`/`get_event` against a seeded `rbac.db` fixture.
- Fault-injection: force `record_event`'s internal write to raise; assert (a) no exception propagates
  to the caller, (b) a structured ERROR log is emitted, (c) the calling mutation's own result is
  unaffected.
- Taxonomy completeness: assert all 6 `mutation_type` values are valid enum members even though only
  5 have a wired call-site.
- Audit-health probe (AUDIT-004): `health_check()` against a healthy fixture returns
  `healthy=True`; against a forced-degraded fixture (e.g., a read-only `rbac.db` mount) returns
  `healthy=False` with a populated `error_detail`; the degraded state persists across a simulated
  process restart (re-open the connection, re-read the health state).
- `is_healthy_for_exposure()` (AUDIT-004): returns `True`/`False` matching the underlying health
  state; unit-tested independently of the CLI/API surfaces that call it.

### Integration Tests

- **Audit-coverage assertion test** (exit criterion): parametrized over the 6 governed mutation
  types; for the 5 available types, perform the mutation and assert exactly one matching
  `audit_event` row exists with the expected `mutation_type`/`action`/`result`; for agent-job launch,
  assert the taxonomy value is reserved and the test explicitly documents N/A pending P4 (not simply
  skipped silently).
- `publish_preview` and `writeback` audit rows correctly capture both success and
  denied/failure outcomes (not only the happy path).
- `rf audit list`/`show` CLI round-trip against a seeded fixture; `GET /api/audit`/`GET
  /api/audit/{id}` API round-trip.
- `rf audit health`/`GET /api/audit/health` round-trip against both a healthy and a forced-degraded
  fixture, asserting the degraded state is visually/structurally distinct (not a buried field).

### E2E Tests (if applicable)

- N/A for this phase — no UI surface exists yet (AUDIT-900 covers the conditional forward reference).

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Audit-write failure silently drops a row, breaking the "100% of 6 governed types" guarantee with no visible signal | Medium | `record_event` logs a structured ERROR + OTel error span on any internal write failure — never a silent `except: pass`. Fault-injection test asserts the log/span fire. |
| Audit-write failure is mistakenly wired to block or roll back the underlying mutation (conflating audit's fail-open contract with RBAC's fail-closed contract) | High | **These are two distinct failure domains and must never be conflated.** `record_event` is called *after* the mutation's own commit and is wrapped in its own internal try/except that never raises outward — a lost audit row cannot roll back or corrupt catalog/draft/writeback state. RBAC authorization (P5.2's `require_role` dependency, evaluated *before* the mutation is attempted) is the opposite: an unresolved identity/role/workspace scope must deny the request. Fail-open applies only to the audit side-channel; fail-closed applies only to the authorization gate. The fault-injection unit test (AUDIT-002 AC) is the concrete guard against this conflation. |
| `audit_service.py` opens a second, independent SQLite connection to `rbac.db`, risking lock contention or schema drift against Phase 1's connection | Medium | AUDIT-001 explicitly requires reusing Phase 1's connection helper; reconcile the exact helper name/signature with P5.1's shipped implementation at execution time (this phase's entry criterion is the P5.1 store existing, not a hardcoded function name). |
| ICA-produced wiring (AUDIT-002/003) subtly changes a mutation's return shape or error handling while adding the audit call | Medium | Mandatory `task-completion-validator` gate before merge; fault-injection test isolates whether a failure originates in the audit call vs. the underlying mutation. |
| Free-text `error_detail` on a `writeback`/`publish_preview` failure accidentally captures a raw secret in the audit row | Low | Pass `error_detail` through `governance.py::scan_secrets`/`_redact` before persisting, mirroring the existing redaction discipline in `middleware/auth.py`. |
| A persistently-failing audit store goes unnoticed because AUDIT-001/002's fail-open write contract is, by design, silent to the mutation caller — a workspace could run for weeks with 0 audit coverage and no operator would know | High | AUDIT-004: durable health state + startup/on-demand probe + loud admin warning (`rf audit health`/`GET /api/audit/health`) + a public-exposure gate (`is_healthy_for_exposure()`) that P5.6 must call before allowing shared/public exposure. This does not change the fail-open write contract — it makes the degradation visible and gates only the *exposure* decision. |
| P5.6 forgets to wire `is_healthy_for_exposure()` into its sharing/publish-preview flow, leaving the exposure gate built but unused | Medium | Explicit coordination note in AUDIT-004 and this phase's Integration Points; P5.6's already-scheduled karen public-exposure milestone is the natural review point; flagged again for P5.9's regression sweep to confirm the wiring landed. |

---

## Success Metrics

- **Completion**: All 5 tasks (AUDIT-001, AUDIT-002, AUDIT-003, AUDIT-004, AUDIT-900) resolved —
  AUDIT-900 may resolve as N/A-with-rationale in Phase 8 rather than implemented here.
- **Quality**: All Quality Gates passed, including the mandatory `task-completion-validator` sign-off
  on the ICA wave.
- **Coverage**: 5 of 5 available governed mutation types produce an audit row (100% of what's
  currently implementable); agent-job launch documented N/A pending P4, with its taxonomy slot
  already reserved (0 follow-up schema changes needed when P4 ships).
- **Fail-open guarantee**: 0 cases where a forced audit-write failure changes the underlying
  mutation's outcome or HTTP status (fault-injection test suite).
- **Degraded-health visibility**: a forced-degraded audit store is detected by the health probe,
  persists across a simulated restart, and surfaces via both `rf audit health` and
  `GET /api/audit/health`; `is_healthy_for_exposure()` correctly returns `False` in that state
  (AUDIT-004 test suite).

---

## Notes

### Implementation Approach

Design the interface once (AUDIT-001, Claude-owned), then offload the repetitive call-site wiring
(AUDIT-002) and the CLI/API read surface (AUDIT-003) to ICA Sonnet 4.6 behind a validator gate. The
architecturally interesting decisions — where `audit_event` lives, how it reuses Phase 1's store, and
the fail-open/fail-closed distinction — are exactly the parts that stay on Claude; the mechanical
"call this function at these 5 places" work is exactly the profile ICA is suited for.

### Gotchas

- `import_all()` must **not** get its own audit call — it already produces coverage transitively
  through its per-run calls to `import_run()`. Double-wiring both would produce duplicate rows per
  catalog-wide reimport.
- `_save_draft()` is called from 11 different sites in `builder_service.py` — wiring the audit call
  there (not at each call-site individually) is both less error-prone and cheaper for the ICA wave.
  `delete_draft()` is the one exception that needs its own explicit call.
- Do not gate `GET /api/audit*` on `require_role` in this phase — that dependency doesn't exist yet
  (P5.2 not required by this phase's wave-plan entry). Flag it as a coordination note for P5.9 instead
  of blocking this phase on P5.2's completion.
- **Do not let AUDIT-004's exposure gate leak into the write path** — `is_healthy_for_exposure()`
  is consulted only at the point P5.6 decides whether to allow shared/public exposure; it must never
  be called from `record_event()` or any mutation call-site, or the fail-open write guarantee
  (AUDIT-001/002) is silently broken.
- **This phase builds the exposure-gate check; it does not enforce it** — `is_healthy_for_exposure()`
  wired into P5.6's actual sharing/publish-preview decision point is P5.6's task, not this phase's.
  Do not mark AUDIT-004 "done" expecting P5.6's enforcement to already exist.

### Learnings

_(Populate during execution.)_

### Findings Captured This Phase

- [ ] No new findings this phase (default)

---

**Phase Version**: 1.0
**Last Updated**: 2026-07-06

[Return to Parent Plan](../public-multiuser-p5-auth-rbac-v1.md)
