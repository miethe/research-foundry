---
title: "Phase 3: Workspace Isolation + Migration"
schema_version: 2
doc_type: phase_plan
status: draft
created: 2026-07-06
updated: 2026-07-06
feature_slug: "public-multiuser-p5-auth-rbac"
feature_version: "v1"
phase: 3
phase_title: "Workspace Isolation + Migration"
prd_ref: /docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
plan_ref: /docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
entry_criteria:
  - "P5.2 RBAC enforcement working and Human gate #2 in progress or complete"
exit_criteria:
  - "Dry-run output reviewed"
  - "Human gate #1 approved"
  - "Rollback runbook tested"
  - "Cross-workspace isolation regression suite green (0 leaks)"
  - "karen isolation-milestone sign-off"
  - "task-completion-validator sign-off"
related_documents:
  - /docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
  - /.claude/worknotes/public-multiuser-p5-auth-rbac/decisions-block.md
  - /docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-2-rbac-enforcement.md
  - /docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-8-auth-context-ui.md
spike_ref: /docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
adr_refs: []
charter_ref: null
changelog_ref: null
test_plan_ref: null
integration_owner: null
ui_touched: false
target_surfaces:
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/services/builder_service.py
  - src/research_foundry/services/workspace_migration_service.py
  - src/research_foundry/api/routers/catalog.py
  - src/research_foundry/api/routers/reports.py
  - src/research_foundry/api/auth/scope.py
  - src/research_foundry/cli_commands.py
  - src/research_foundry/config.py
seam_tasks: []
owner: null
contributors: [data-layer-expert, backend-architect]
priority: critical
risk_level: critical
category: "product-planning"
tags: [phase-plan, implementation, mode-d, migration, workspace-isolation, must-stay, irreversible]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/services/catalog_service.py
  - src/research_foundry/services/builder_service.py
  - src/research_foundry/services/workspace_migration_service.py
  - src/research_foundry/api/routers/catalog.py
  - src/research_foundry/api/routers/reports.py
  - src/research_foundry/api/auth/scope.py
  - src/research_foundry/cli_commands.py
  - src/research_foundry/config.py
  - src/research_foundry/paths.py
  - tests/unit/test_workspace_migration_service.py
  - tests/integration/test_workspace_isolation.py
  - docs/dev/architecture/runbooks/workspace-migration-rollback.md
---

# Phase 3: Workspace Isolation + Migration

> ## ⚠️ MODE D — MUST-STAY — NO ICA/CODEX OFFLOAD, EVER
>
> This is the **single most sensitive phase in the 46-point P5 plan**: an **irreversible data
> migration** that flips `workspace_id`/`created_by` from unenforced forward-compat columns
> (P2/P3 decision D12) into a live authorization boundary. Every task in this phase runs on
> **Claude Sonnet, `sonnet` / `extended` effort, on the Anthropic subscription only** — never ICA
> Sonnet 4.6, never Codex, never any offload path, at any point, for any sub-task. This is one of
> only three phases in the whole plan requiring a **mid-feature `karen` review** (the other two are
> P5.6 and P5.9), and the only phase with a **human sign-off gate that blocks enforcement**, not
> merely a courtesy review. Treat every task below as Mode D: explore, propose, and for the
> migration-writing tasks specifically, stop at the documented checkpoints for human approval
> before flipping any behavior that changes what a live deployment does.

**Parent Plan**: [Public Multi-User P5 — Auth/RBAC/Isolation/Audit Hardening](../public-multiuser-p5-auth-rbac-v1.md)
**Duration**: ~4-5 days (includes mandatory human-gate wait time — do not compress)
**Effort**: 6 story points
**Dependencies**: P5.2 (RBAC enforcement) complete or Human gate #2 in progress
**Team Members**: `data-layer-expert` (primary), `backend-architect` (primary) — **no secondary agents on this phase**

---

## Phase Overview

Phase 3 turns the nullable, unenforced `workspace_id`/`created_by` columns that P2/P3 shipped as
"cheap forward-compat" (plan decision D12) into a real, server-enforced isolation boundary. This
is the highest-risk phase in the entire P5 plan because it is the only one that **mutates existing
durable data** rather than adding new capability alongside old.

### Goals

- Give every operator a truthful, zero-write preview of exactly what the migration will do before
  any data changes (dry-run).
- Prove a tested, non-destructive path back to the pre-migration state exists *before* the
  forward migration runs for real (rollback runbook).
- Backfill every existing unscoped catalog/draft record into one synthetic `default` workspace
  (the locked OQ-B resolution — do not design per-`created_by` inference).
- Gate the actual behavior change (isolation checks start returning 404 for cross-workspace
  access) behind an explicit human approval that blocks **phase exit**, not just task completion.
- Prove 0 cross-workspace leaks across every AC-1 `target_surfaces` router once enforcement is
  live.

### Architecture Focus

- **Layer**: Data migration + Service (repository-level enforcement) + API (router wiring).
- **Patterns**: Mirrors the existing `catalog_service.py` disposable-cache-vs-durable-file split
  (see "Critical Schema Findings" below); reuses `builder_service.py`'s existing atomic
  temp-file-then-`os.replace()` write pattern for any durable file mutation; reuses OQ-A's locked
  "single shared FastAPI dependency" idiom (`require_role(...)` from P5.2) for the analogous
  `require_workspace_scope(...)` isolation check.
- **Standards**: Fail-closed by default (`.claude/rules` global fail-closed precedent,
  `export_service.py` `DEFAULT_THRESHOLD` pattern); no-existence-leak convention (a cross-workspace
  record must be indistinguishable from a non-existent one — landmine #4, restated in AC-1).

### Critical Schema Findings (read before assigning this phase — changes task scope)

Verified directly against `src/research_foundry/services/catalog_service.py` and
`builder_service.py` on 2026-07-06. These facts change the shape of "the migration" from what a
naive reading of FR-7 suggests, and materially change the risk profile of each sub-task:

1. **`catalog_items`** (the run-derived catalog rows) has **no `workspace_id`/`created_by` column
   today** (`catalog_service.py` DDL, lines ~122-141). `catalog.db` is explicitly disposable and
   100% derived — `SCHEMA_VERSION` bump triggers a full drop + recreate
   (`_ensure_schema`/`rebuild_schema`), and `rebuild()` (line ~1131) already re-imports every run
   and reindexes every draft in one call. Backfilling `catalog_items` is therefore a **schema
   addition + cache rebuild**, not a live-row UPDATE — low blast radius, trivially reversible
   (rebuild again after reverting the schema), because nothing here is canonical.
2. **`catalog_report_drafts`** (the derived draft index, same disposable `catalog.db`) already has
   nullable `workspace_id`/`created_by` columns, but this table is *also* fully derived — from
   `builder_service.reindex_all_drafts()`.
3. **The actual durable, canonical data lives in `<workspace>/reports/drafts/<id>/draft.yaml`**
   (confirmed: `builder_service.create_draft()` at lines ~332-394 persists `workspace_id`/
   `created_by` directly into the dict written to disk via `_save_draft()`). **This is the real
   irreversible-risk surface** — rewriting existing `draft.yaml` files to backfill a workspace_id
   is a mutation of canonical, hand-authored/durable state, unlike the `catalog.db` side which can
   always be regenerated from scratch.
4. Practical consequence for task design: the **backfill task has two genuinely different risk
   tiers within it** — (a) low-risk: bump `catalog_service.SCHEMA_VERSION`, add the column to
   `catalog_items`, inject `workspace_id` at `import_all()` time, `rebuild()` (fully reversible by
   re-bumping the version and rebuilding again); (b) high-risk: atomically rewrite every existing
   `draft.yaml` on disk (needs a recorded manifest + tested reverse path — this is what the
   rollback runbook task is really protecting).

---

## Task Breakdown

### Epic: Workspace Isolation Migration & Enforcement

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Assigned Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|--------------|---------------------|----------|----------------------|-------|--------|--------------|
| WKSP-301 | Dry-run workspace-scoping evaluation (no writes) | Implement the real scoping predicate in advisory (shadow) mode + a zero-write report of what the migration would do | See Detailed Spec below | 1.5 pts | data-layer-expert | sonnet | extended | None |
| WKSP-302 | Rollback runbook — tested reverse-migration path | Author + implement + test an actual reverse-migration script/procedure, not prose only | See Detailed Spec below | 1.5 pts | data-layer-expert | sonnet | extended | WKSP-301 |
| WKSP-303 | Legacy-record default-workspace backfill (OQ-B) | Execute the locked single-`default`-workspace backfill for real, using the already-tested WKSP-302 code path | See Detailed Spec below | 1 pt | data-layer-expert | sonnet | extended | WKSP-301, WKSP-302 |
| **GATE-1** | **Human Gate #1 checkpoint** | Human reviews WKSP-301 dry-run output + WKSP-303 backfill result + WKSP-302 tested rollback; explicitly approves flipping enforcement on | See "Human Gate #1" section below | 0 pts | Human (operator) | n/a | n/a | WKSP-301, WKSP-302, WKSP-303 |
| WKSP-304 | Enforcement flip — workspace isolation advisory → blocking | Flip the shared scoping predicate from log-only to blocking; non-admin cross-workspace access now 404s | See Detailed Spec below | 1 pt | backend-architect | sonnet | extended | GATE-1 (human approval) |
| WKSP-305 | Cross-workspace isolation regression suite (0 leaks) | New parametrized regression suite across every AC-1 `target_surfaces` router/service, asserting 0 leaks | See Detailed Spec below | 0.5 pt | data-layer-expert, backend-architect | sonnet | extended | WKSP-304 |
| WKSP-900 | AC: FE handles enforced workspace scoping (cross-workspace record -> 404, not 403) | Freeze + contract-test the exact backend response shape for a cross-workspace record, so Phase 8's FE work has a stable contract to consume | See Detailed Spec below | 0.5 pt | backend-architect | sonnet | extended | WKSP-304 |
| **Total** | — | — | — | **6 pts** | — | — | — | — |

**Model Selection Guidance**: Every task in this phase is Claude Sonnet, `extended` effort, on the
Anthropic subscription. No `nano-banana-pro`/`gemini`/Codex/ICA routing applies anywhere in this
phase — see the Mode D banner above.

---

## Detailed Task Specifications

### Task WKSP-301: Dry-run workspace-scoping evaluation (no writes)

**Estimate**: 1.5 points
**Assigned Subagent(s)**: data-layer-expert
**Model**: sonnet
**Effort**: extended
**Dependencies**: None (first task in phase)
**started**: null
**completed**: null
**verified_by**: [GATE-1]
**evidence**: []

**Description**:
Implement the real workspace-scoping predicate that Phase 3 will eventually enforce — but run it
in **advisory (shadow) mode only**: it evaluates every existing record against "would a caller in
a different workspace be denied this?" and records the answer, but never blocks a request or
raises anything callers can observe. The dry-run report *is* the artifact Human Gate #1 reviews —
it must be a faithful simulation of the real check, not a separate hand-rolled `COUNT(*)` query,
so that what gets approved is exactly what will later run for real.

Concretely:
1. Add `src/research_foundry/api/auth/scope.py` with a `require_workspace_scope(identity, record)`
   helper (mirrors the OQ-A-locked `require_role(...)` shared-dependency idiom from P5.2) that
   returns `WorkspaceScopeResult(allowed: bool, reason: str)`. In this task it is wired but always
   returns `allowed=True` — advisory mode never blocks; it only **logs** (structured JSON log,
   `event="workspace_scope_advisory_mismatch"`) when a record's `workspace_id` does not match the
   caller's identity (or is null).
2. Add `src/research_foundry/services/workspace_migration_service.py` with
   `dry_run(paths: FoundryPaths) -> DryRunReport`:
   - Walks every `<workspace>/reports/drafts/<id>/draft.yaml` on disk (never the derived
     `catalog_report_drafts` table) and tallies: total drafts, drafts with `workspace_id` null vs
     populated, `created_by` null vs populated.
   - Reads current `catalog_items` row count (100% will be workspace-less pre-migration, since the
     column does not exist yet — see Critical Schema Findings above).
   - For every draft + catalog item, simulates the post-migration state (`workspace_id="default"`)
     and reports, per AC-1's actual check semantics, how many *existing* API callers would newly be
     scoped/denied cross-workspace access (today: 0, since there is only one implicit workspace —
     the report must say this explicitly so a human reviewer isn't left guessing).
   - Performs **zero writes** to `draft.yaml`, `catalog.db`, or any other state. This is enforced by
     a unit test that snapshots file mtimes/hashes before and after calling `dry_run()`.
3. Wire a `rf workspace migrate-dry-run [--json]` CLI command (Typer, new `workspace_app` group in
   `cli_commands.py`, added via `app.add_typer(workspace_app, name="workspace")`, following the
   existing `catalog_app`/`report_app` pattern) that prints this report as a Rich table (default)
   or JSON (`--json`, for programmatic Human Gate #1 review / CCDash writeback).

**Acceptance Criteria**:
- [ ] `dry_run(paths)` performs zero writes — proven by a test asserting every `draft.yaml`'s mtime
      and content hash are byte-identical before/after, and `catalog.db`'s row counts are unchanged.
- [ ] Report output includes: total draft count, drafts missing `workspace_id`, drafts missing
      `created_by`, total `catalog_items` count (all currently workspace-less), and the exact
      workspace_id value (`"default"`) that would be assigned.
- [ ] `require_workspace_scope()` exists, is wired into at least one real call site in
      `catalog_service.py` and `builder_service.py` read paths, and is provably non-blocking in
      this task (a request for a record in a different workspace still succeeds — advisory-only,
      asserted by test).
- [ ] Advisory mismatches are logged as structured JSON with `trace_id`, `record_type`, `record_id`
      — never as an exception, never surfaced to the caller.
- [ ] `rf workspace migrate-dry-run` runs against a real/fixture workspace and produces
      human-readable output suitable for direct inclusion in the Human Gate #1 approval record.
- [ ] `rf workspace migrate-dry-run --json` produces machine-parseable output with the same fields.

**Implementation Notes**:
- Do not read `catalog_report_drafts` (the derived table) for the draft inventory — read the
  `draft.yaml` files directly, matching `builder_service.reindex_all_drafts()`'s own
  file-is-truth contract. Reading the derived table would silently miss any draft not yet indexed.
- Reuse `FoundryPaths` for path resolution; verify `FoundryPaths.rf_state` (the new durable store
  property from P5.1, D2) exists before this task starts — if P5.1 did not add it, add a `rf_state`
  property to `paths.py` analogous to the existing `rf_cache` property (line ~140) as a
  prerequisite, since WKSP-302's migration manifest needs a durable home outside `catalog.db`.
- This task defines the manifest/report data shape that WKSP-302 and WKSP-303 both reuse — do not
  let three tasks each invent their own report schema.

**Files Involved**:
- `src/research_foundry/api/auth/scope.py` - new `require_workspace_scope()` shared dependency (advisory mode)
- `src/research_foundry/services/workspace_migration_service.py` - new module; `dry_run()` + shared report/manifest dataclasses
- `src/research_foundry/services/catalog_service.py` - wire advisory check into a read call site (no schema change yet)
- `src/research_foundry/services/builder_service.py` - wire advisory check into `load_draft`/`list_drafts` read paths
- `src/research_foundry/cli_commands.py` - new `workspace_app` Typer group, `migrate-dry-run` command
- `src/research_foundry/paths.py` - add `rf_state` property if not already present from P5.1

---

### Task WKSP-302: Rollback runbook — tested reverse-migration path

**Estimate**: 1.5 points
**Assigned Subagent(s)**: data-layer-expert
**Model**: sonnet
**Effort**: extended
**Dependencies**: WKSP-301
**started**: null
**completed**: null
**verified_by**: [GATE-1]
**evidence**: []

**Description**:
Author and implement a **tested** reverse-migration path — not documentation alone. This task
co-designs the migration manifest schema that WKSP-303's real backfill will write, implements the
forward-backfill *function* itself (WKSP-303 then invokes it for real against the live workspace,
under the Human Gate #1-derived approval), and implements + tests the reverse path against a
throwaway fixture copy before any real data is touched.

Concretely:
1. Define a durable migration manifest written to
   `<workspace>/.rf_state/migrations/<ISO8601-timestamp>-workspace-backfill.json` (mirrors the
   precedent of the existing `catalog_import_log` table's shape, but lives in the new durable
   `.rf_state` store per D2 — never in disposable `catalog.db`). The manifest records, per touched
   record: `record_type` (`"draft"` | `"catalog_item"`), `record_id`, `prior_workspace_id` (always
   `null` pre-migration), `prior_created_by`, `new_workspace_id` (`"default"`), and a
   `migration_run_id` grouping key.
2. Implement `workspace_migration_service.backfill(paths, workspace_id="default") -> BackfillReport`
   — the actual forward mutation function (draft.yaml atomic rewrite + catalog schema bump/rebuild,
   see WKSP-303's spec for the exact mechanics) — but in THIS task it is only *exercised*, not run
   for real: build a throwaway fixture workspace (via `tmp_path`) seeded with N synthetic legacy
   `draft.yaml` files and catalog items, run `backfill()` against it, then run
   `rollback(paths, migration_run_id)` and assert the fixture workspace is **byte-identical** to
   its pre-backfill state (file content hash comparison, not just field-level equality).
3. Implement `workspace_migration_service.rollback(paths, migration_run_id) -> RollbackReport`:
   - Reads the manifest for the given `migration_run_id` from `.rf_state/migrations/`.
   - For `record_type="draft"`: reads the current `draft.yaml`, restores `workspace_id`/
     `created_by` to the manifest's `prior_*` values, atomic rewrite (temp file + `os.replace()`,
     same pattern as every other builder_service mutator).
   - For `record_type="catalog_item"`: no per-row restoration needed — rollback for this half is
     "revert `SCHEMA_VERSION`, `rf catalog rebuild`" (documented, not coded per-row, since the table
     is 100% disposable — see Critical Schema Findings).
   - **Never** reverts by pattern-matching on the *value* `workspace_id == "default"` — this would
     be unsafe once real per-workspace usage begins after enforcement ships (a legitimately-created
     `"default"`-workspace draft post-migration must not be touched by a rollback of the *original*
     migration run). The manifest's explicit record-id list is the only safe input.
4. Author the human-facing runbook at
   `docs/dev/architecture/runbooks/workspace-migration-rollback.md`: step-by-step operator
   procedure (stop the server / take a filesystem snapshot of `<workspace>/reports/drafts/` and
   `<workspace>/.rf_cache/catalog.db` before backfill; how to invoke `rf workspace rollback
   <migration_run_id>`; how to verify success; what "the rollback did not fully succeed" looks like
   and the manual fallback (restore from the pre-backfill filesystem snapshot)).

**Acceptance Criteria**:
- [ ] `rollback(paths, migration_run_id)` is invoked in an automated test that runs the *actual*
      `backfill()` → `rollback()` round trip against a fixture workspace and asserts every touched
      `draft.yaml`'s content hash matches its pre-backfill hash exactly (not just `workspace_id is
      None` — the full file, to catch any other unintended mutation).
- [ ] The round-trip test includes at least one draft that already had a non-null `workspace_id`
      pre-migration (a false-legacy record) and asserts `backfill()`/`rollback()` never touch it
      (manifest only ever lists records that were actually null before the run).
- [ ] Rollback is driven entirely by the migration manifest (`migration_run_id` lookup) — a test
      asserts that a draft manually re-tagged to `workspace_id="default"` by unrelated, legitimate
      post-migration activity is **not** reverted by a rollback of an earlier `migration_run_id`.
- [ ] `rf workspace rollback <migration_run_id> [--dry-run]` CLI command exists; `--dry-run` prints
      what would be reverted without writing.
- [ ] The runbook doc exists at `docs/dev/architecture/runbooks/workspace-migration-rollback.md`
      and includes: pre-migration snapshot step, exact CLI invocation, verification step, and a
      manual filesystem-restore fallback procedure for the case the automated rollback itself fails.
- [ ] Runbook is cross-linked from this phase file's `related_documents` (already set) and from the
      parent plan's Phase 3 row.

**Implementation Notes**:
- Reuse the exact atomic-write pattern already established in `builder_service.py` (temp file in
  the same directory, then `os.replace()`) for both the forward backfill and the rollback file
  writes — do not invent a new write primitive.
- The catalog_items half of rollback is intentionally documentation + a schema-version revert, not
  a coded per-row reverter — say so explicitly in the runbook so an operator doesn't go looking for
  code that isn't there.
- This task's fixture-based round-trip test is the "actual tested script/procedure" required by
  the phase brief — a runbook doc with no accompanying automated test does not satisfy this task.

**Files Involved**:
- `src/research_foundry/services/workspace_migration_service.py` - `backfill()`, `rollback()`, manifest read/write helpers (shared module with WKSP-301/303)
- `src/research_foundry/cli_commands.py` - `rf workspace rollback` command
- `tests/unit/test_workspace_migration_service.py` - new; backfill→rollback round-trip fixture test
- `docs/dev/architecture/runbooks/workspace-migration-rollback.md` - new runbook doc

---

### Task WKSP-303: Legacy-record default-workspace backfill (OQ-B resolution)

**Estimate**: 1 point
**Assigned Subagent(s)**: data-layer-expert
**Model**: sonnet
**Effort**: extended
**Dependencies**: WKSP-301, WKSP-302
**started**: null
**completed**: null
**verified_by**: [GATE-1]
**evidence**: []

**Description**:
Execute the **locked** backfill decision (OQ-B, closed — do not re-open or design a
per-`created_by`-inference alternative): every existing unscoped catalog/draft record is assigned
to **one synthetic `"default"` workspace**. This task runs the already-implemented,
already-round-trip-tested (WKSP-302) `backfill()` function for real against the live workspace,
records a migration manifest, and reports the outcome for Human Gate #1 review. This task does
**not** flip any enforcement — records are backfilled additively; every existing caller keeps
working exactly as before, because nothing yet reads `workspace_id` as an authorization boundary
(that is WKSP-304, gated separately).

Concretely:
1. Bump `catalog_service.SCHEMA_VERSION` (2 → 3); add `workspace_id TEXT NOT NULL DEFAULT
   'default'` to the `catalog_items` `CREATE TABLE` DDL.
2. Update `import_all()` (and any other `catalog_items` insert path) to set `workspace_id` from the
   resolved caller context, defaulting to `"default"` when no request-scoped identity is available
   (e.g. `rf catalog rebuild` run from the CLI with no HTTP identity).
3. Run `catalog_service.rebuild(paths)` — this is the existing, already-shipped function (drop +
   recreate schema, re-import every run, reindex every draft) that now naturally repopulates
   `catalog_items` with the new column populated.
4. Invoke `workspace_migration_service.backfill(paths, workspace_id="default")` for real: walks
   every `<workspace>/reports/drafts/<id>/draft.yaml` with a null `workspace_id`, atomically
   rewrites it to `workspace_id="default"` (leave `created_by` null — there is no way to safely
   infer a historical author; this is the correct, honest behavior, not a defect), and writes the
   migration manifest to `.rf_state/migrations/<timestamp>-workspace-backfill.json`.
5. Print/log a `BackfillReport` (records touched, manifest path, `migration_run_id`) — this, plus
   WKSP-301's dry-run output, is exactly what Human Gate #1 reviews before approving WKSP-304.

**Acceptance Criteria**:
- [ ] `catalog_items` gains a `workspace_id` column (schema version 3); pre-existing runs re-import
      cleanly via `rf catalog rebuild` with every item's `workspace_id="default"`.
- [ ] Every `draft.yaml` with a previously-null `workspace_id` now has `workspace_id="default"`;
      every `draft.yaml` that already had a non-null value (if any exist from prior ad-hoc testing)
      is left untouched — asserted by test.
- [ ] The backfill result count matches WKSP-301's dry-run prediction exactly (same record count) —
      this equivalence is itself an assertion in the test suite, not just an eyeballed comparison.
- [ ] A migration manifest exists at `.rf_state/migrations/<...>-workspace-backfill.json` listing
      every touched record id and its prior state, readable by WKSP-302's `rollback()`.
- [ ] No enforcement behavior changes as a result of this task alone — a test asserts a
      cross-workspace read still succeeds (200, not 404) immediately after backfill, proving the
      backfill is additive-only per the PRD's "additive/backfill, never destructive" mitigation.
- [ ] `rf workspace migrate --apply` CLI command runs this backfill; running it twice is a safe
      no-op the second time (idempotent — no double-manifest, no re-touching already-migrated
      records).

**Implementation Notes**:
- This task deliberately does NOT touch `require_workspace_scope()`'s advisory/blocking mode — that
  flip is WKSP-304, gated on human approval. Keep the two changes in separate commits so the
  backfill can land and be verified independently of the enforcement flip.
- `created_by` remains null for backfilled legacy records by design — do not invent a fake
  attribution. Document this as an expected, permanent gap for pre-migration records in the
  runbook (WKSP-302) rather than treating it as a bug to fix later.

**Files Involved**:
- `src/research_foundry/services/catalog_service.py` - `SCHEMA_VERSION` bump, `catalog_items` DDL, `import_all()` workspace_id injection
- `src/research_foundry/services/builder_service.py` - no code change expected beyond what WKSP-301/302 already added; this task only invokes `backfill()`
- `src/research_foundry/services/workspace_migration_service.py` - `backfill()` invoked for real; manifest written
- `src/research_foundry/cli_commands.py` - `rf workspace migrate --apply` command
- `tests/unit/test_workspace_migration_service.py` - backfill idempotency + dry-run-parity assertions

---

## Human Gate #1 (BLOCKS PHASE EXIT — not just task completion)

> **This gate blocks phase exit, not merely the completion of a single task.** Phase 3 is not
> "done" until this gate has fired, regardless of whether every other task's checkbox is ticked.

- **Trigger**: WKSP-301 (dry-run), WKSP-302 (tested rollback), and WKSP-303 (real backfill) are all
  complete.
- **Reviewer**: Human operator (not an agent, not `karen`, not `task-completion-validator` — this is
  a human sign-off per AC-GATE-1 in the PRD).
- **What is reviewed**: WKSP-301's dry-run report (record counts, workspace_id/created_by
  distribution, predicted assignment), WKSP-303's actual `BackfillReport` (must match the dry-run
  prediction exactly), and confirmation that WKSP-302's rollback round-trip test is green in CI.
- **What approval unlocks**: WKSP-304 (the enforcement flip) may only start after this gate fires.
  WKSP-304's CLI entry point (`rf workspace enforce --on`) must itself refuse to run without an
  explicit `--gate-1-approved-by <operator-name>` flag (or an equivalent recorded approval artifact
  under `.rf_state/`) — this is a concrete acceptance criterion on WKSP-304, not a process nicety.
- **What is NOT gated by this checkpoint**: the backfill itself (WKSP-303) is additive/non-destructive
  per the PRD's own risk mitigation language and may complete before this gate fires — only the
  *enforcement* flip (the behavior change a live deployment will notice) is blocked on human
  approval. This sequencing (dry-run → tested rollback → real backfill → **gate** → enforcement) is
  the safest ordering because the human is reviewing what actually happened, not a prediction, and
  because a tested, proven rollback path already exists before the higher-risk enforcement flip is
  even considered.
- **Record of approval**: written to `.rf_state/migrations/<migration_run_id>-gate1-approval.json`
  (operator name, timestamp, dry-run/backfill report references) — this is the artifact
  `rf workspace enforce --on` checks for.

---

### Task WKSP-304: Enforcement flip — workspace isolation advisory → blocking

**Estimate**: 1 point
**Assigned Subagent(s)**: backend-architect
**Model**: sonnet
**Effort**: extended
**Dependencies**: GATE-1 (Human Gate #1 approval — hard dependency, not advisory)
**started**: null
**completed**: null
**verified_by**: [WKSP-305, WKSP-900]
**evidence**: []

**Description**:
Flip `require_workspace_scope()` (WKSP-301) from advisory (log-only) to blocking, and add the
`auth.workspace_isolation: advisory | enforced` flag to `foundry.yaml`/`config.py` (mirrors the
existing `_validate_auth_mode` validator pattern in `config.py`), defaulting to `advisory` until
this task changes the shipped default to `enforced`. Wire the now-blocking predicate into every
`catalog.py`/`reports.py` router call site and the underlying `catalog_service.py`/
`builder_service.py` repository functions identified in AC-1's `target_surfaces`. A record whose
`workspace_id` does not match the caller's `AuthIdentity.workspace_id` (and the caller is not
owner/admin exercising an explicit cross-workspace override) must be treated identically to a
non-existent record — HTTP 404, never 403 (no-existence-leak convention, landmine #4).

**Acceptance Criteria**:
- [ ] `require_workspace_scope()` blocks (raises a `NotFoundError`-equivalent, never a
      distinguishable 403) on a workspace mismatch; the advisory log-only branch is removed
      (not just disabled by a flag left in the "off" position — there should be no code path left
      that silently allows a mismatch through once `auth.workspace_isolation: enforced`).
- [ ] `rf workspace enforce --on` refuses to run without a recorded Human Gate #1 approval artifact
      (`.rf_state/migrations/<...>-gate1-approval.json`); refusing prints a clear operator message
      pointing at the runbook and the gate requirement.
- [ ] Owner/admin explicit cross-workspace override path (per FR-7/AC-1) still functions and is
      covered by a dedicated test distinguishing it from the default-denied path.
- [ ] Every router listed in AC-1 `target_surfaces` (`catalog.py`, `reports.py`) enforces via the
      shared dependency — not a bespoke per-route check (mirrors the OQ-A pattern already locked
      for RBAC in P5.2).
- [ ] `auth.workspace_isolation` config flag exists, validated the same way `viewer.auth_mode` is
      validated in `config.py`, default `enforced` after this task ships.

**Implementation Notes**:
- This is a small, surgical change by design — the actual predicate logic already exists and was
  exercised (in log-only mode) since WKSP-301. Resist scope creep; this task is "flip the switch
  safely," not "redesign the check."
- Land in its own commit, separate from WKSP-303's backfill commit, so the enforcement flip can be
  reverted independently (config flag back to `advisory`) without touching the already-backfilled
  data if a regression surfaces post-flip.

**Files Involved**:
- `src/research_foundry/api/auth/scope.py` - remove advisory-only branch, make blocking
- `src/research_foundry/config.py` - `auth.workspace_isolation` flag + validator
- `src/research_foundry/api/routers/catalog.py` - wire enforced dependency
- `src/research_foundry/api/routers/reports.py` - wire enforced dependency
- `src/research_foundry/cli_commands.py` - `rf workspace enforce --on/--off`, gate-approval check

---

### Task WKSP-305: Cross-workspace isolation regression suite (0 leaks)

**Estimate**: 0.5 point
**Assigned Subagent(s)**: data-layer-expert, backend-architect
**Model**: sonnet
**Effort**: extended
**Dependencies**: WKSP-304
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

**Description**:
New parametrized regression suite (`tests/integration/test_workspace_isolation.py`) covering every
AC-1 `target_surfaces` entry (`catalog_service.py`, `builder_service.py`, `catalog.py`,
`reports.py`) across both read and write operations, two identities in two different workspaces,
asserting a non-admin, non-owner caller in workspace A gets a 404 (never 403, never 200) for any
record created in workspace B — and that the owner/admin explicit override path still works.

**Acceptance Criteria**:
- [ ] Suite is parametrized across every router in AC-1's `target_surfaces` list; **0 leaks** —
      any 200 or 403 result for a cross-workspace record is a hard test failure, not a warning.
- [ ] Covers both catalog items and report drafts (both record types touched by this phase's
      migration).
- [ ] Covers both read (`GET`) and write (`PATCH`/`POST` mutation) paths for report drafts.
- [ ] Includes a positive-path assertion: same-workspace access still succeeds (200) — proves the
      suite isn't just testing "everything 404s."
- [ ] Includes an owner/admin override-path assertion distinct from the default-denied path.
- [ ] Runs green in CI in both `auth_mode=none` (single-operator, `workspace_id="default"`
      everywhere — trivially passes) and a multi-identity fixture configuration.

**Implementation Notes**:
- This suite is the authoritative source for the plan's "0 cross-workspace leaks" success metric
  (parent plan `success_metrics`) — do not substitute unit-level mocking for real
  request/response-level integration tests here.

**Files Involved**:
- `tests/integration/test_workspace_isolation.py` - new suite

---

### Task WKSP-900: AC: FE handles enforced workspace scoping (cross-workspace record -> 404, not 403)

**Estimate**: 0.5 point
**Assigned Subagent(s)**: backend-architect
**Model**: sonnet
**Effort**: extended
**Dependencies**: WKSP-304
**started**: null
**completed**: null
**verified_by**: []
**evidence**: []

> **Cross-phase reference**: this exact task ID (`WKSP-900`) is referenced by Phase 8
> (`phase-8-auth-context-ui.md`, authored in a parallel agent run) as the upstream backend contract
> its FE work consumes. Do not renumber this ID.

**Description**:
This is the resilience AC required by R-P2 (every new/changed backend field/behavior gets an
explicit "FE handles X" AC) for the behavior WKSP-304 introduces. Within Phase 3 (backend), this
task's job is to **freeze and contract-test the exact HTTP response shape** for a cross-workspace
record so that Phase 8's frontend auth-context work has a stable, tested contract to build
against — matching the existing no-existence-leak convention (a cross-workspace record is
indistinguishable from a non-existent one; the FE must not special-case "cross-workspace" as a
distinct state from "not found").

- target_surfaces:
    - src/research_foundry/api/routers/catalog.py
    - src/research_foundry/api/routers/reports.py
    - frontend/runs-viewer/src/api/client.ts  (consumed in Phase 8 — not modified here)
- propagation_contract: >
    WKSP-304's `require_workspace_scope()` raises the same not-found error class used for a
    genuinely non-existent record; both routers catch it identically and return an HTTP 404 with
    the project's standard error envelope, carrying no field that distinguishes
    "exists-in-another-workspace" from "does not exist." Phase 8's `client.ts` error handling
    (already extended for 401/403 per PRD AC-5's additional resilience bullets) needs no new branch
    for this case — it is a plain 404, handled by the existing not-found path.
- resilience: >
    If `AuthIdentity.workspace_id` is itself missing/null on the request context (should not happen
    post-P5.1/P5.2, but checked defensively here), the scoping check fails closed (treats as
    workspace mismatch → 404), never fails open.
- visual_evidence_required: false
- verified_by:
    - contract-test in tests/integration/test_workspace_isolation.py (WKSP-305) asserting response
      body equality between a genuinely-missing record and a cross-workspace record (same shape,
      same status, same fields — no distinguishing signal)

**Acceptance Criteria**:
- [ ] A cross-workspace record and a genuinely non-existent record return byte-identical response
      bodies (status 404, same error envelope shape) — asserted by a dedicated test.
- [ ] No response header, timing-observable difference, or body field leaks the existence of a
      cross-workspace record (best-effort: same code path, not a bespoke early-return).
- [ ] This contract is documented in this task's spec (above) so Phase 8 can reference it without
      re-deriving it from source.

**Implementation Notes**:
- Do not implement any frontend code in this task — that is explicitly Phase 8's scope. This task
  only guarantees the backend contract Phase 8 depends on is real, tested, and stable.

**Files Involved**:
- `src/research_foundry/api/routers/catalog.py` - confirm shared not-found error path
- `src/research_foundry/api/routers/reports.py` - confirm shared not-found error path
- `tests/integration/test_workspace_isolation.py` - response-body-equality contract test

---

## Quality Gates

This phase is complete when:

- [ ] **Functional**: WKSP-301 dry-run, WKSP-302 rollback, WKSP-303 backfill, WKSP-304 enforcement
      flip, WKSP-305 regression suite, and WKSP-900 contract test are all complete.
- [ ] **Testing**: `tests/unit/test_workspace_migration_service.py` (backfill/rollback round-trip)
      and `tests/integration/test_workspace_isolation.py` (0-leak regression suite) both green.
- [ ] **Migration Safety**: Human Gate #1 approval artifact exists and is referenced by the
      enforcement-flip commit.
- [ ] **Security**: 0 cross-workspace leaks (WKSP-305); no-existence-leak convention holds
      (WKSP-900); fail-closed on missing identity context.
- [ ] **Documentation**: rollback runbook (`docs/dev/architecture/runbooks/workspace-migration-rollback.md`) exists and is cross-linked.
- [ ] **Code Quality**: `flake8`/`mypy` clean on all changed files.
- [ ] **Architecture**: reuses the shared-dependency idiom (OQ-A) rather than per-route checks;
      respects the disposable-vs-durable split documented in Critical Schema Findings.
- [ ] **Seam verification**: N/A — `integration_owner` is null; both primary agents are
      backend-specialty (no FE/BE seam within this phase). WKSP-900 is the cross-phase contract
      handoff to Phase 8, tracked via `related_documents`, not a within-phase seam task.
- [ ] **Runtime smoke**: N/A — `ui_touched: false`, no `.tsx` files in this phase's `files_affected`.
- [ ] **Reviewer gates — BOTH required, not either/or**: `task-completion-validator` **and**
      `karen` (isolation milestone) must both sign off. Neither reviewer's pass substitutes for
      the other on this phase.

---

## Integration Points

### External Systems

- **None** — this phase is entirely internal (SQLite `catalog.db`, on-disk `draft.yaml` files, the
  new `.rf_state/` durable store). No third-party auth provider (Clerk/OIDC) is touched here.

### Internal Systems

- **P5.1 (`.rf_state` durable store, `AuthIdentity`)**: this phase's manifest/approval artifacts
  live in `.rf_state/migrations/`, and `require_workspace_scope()` consumes
  `AuthIdentity.workspace_id` from the request context P5.1 establishes.
- **P5.2 (RBAC enforcement, `require_role(...)`)**: this phase's `require_workspace_scope()`
  mirrors the same shared-dependency idiom (OQ-A) so the two checks compose predictably at each
  router (role check + workspace check, not one giant combined predicate).
- **Phase 8 (frontend auth-context)**: consumes the WKSP-900 contract; no direct code dependency,
  cross-referenced via `related_documents` and the WKSP-900 task ID.
- **`catalog_service.rebuild()`**: reused as-is (already handles both `catalog_items` re-import and
  `reindex_all_drafts()`) — WKSP-303 does not reimplement this, only triggers it post-schema-bump.

---

## Key Files Modified

| File Path | Purpose | Subagent |
|-----------|---------|----------|
| `src/research_foundry/services/workspace_migration_service.py` | New module: dry-run, backfill, rollback, manifest schema | data-layer-expert |
| `src/research_foundry/services/catalog_service.py` | `SCHEMA_VERSION` 2→3; `catalog_items.workspace_id` column; `import_all()` injection | data-layer-expert |
| `src/research_foundry/services/builder_service.py` | Advisory/enforced scoping wired into draft read/write paths | data-layer-expert, backend-architect |
| `src/research_foundry/api/auth/scope.py` | New shared `require_workspace_scope()` dependency (advisory → blocking) | backend-architect |
| `src/research_foundry/config.py` | New `auth.workspace_isolation: advisory\|enforced` flag + validator | backend-architect |
| `src/research_foundry/api/routers/catalog.py` | Wire enforced dependency | backend-architect |
| `src/research_foundry/api/routers/reports.py` | Wire enforced dependency | backend-architect |
| `src/research_foundry/cli_commands.py` | New `workspace_app` group: `migrate-dry-run`, `migrate --apply`, `rollback`, `enforce --on/--off` | data-layer-expert |
| `src/research_foundry/paths.py` | Confirm/add `rf_state` property (P5.1 dependency check) | data-layer-expert |
| `tests/unit/test_workspace_migration_service.py` | Backfill/rollback round-trip + dry-run-parity tests | data-layer-expert |
| `tests/integration/test_workspace_isolation.py` | 0-leak cross-workspace regression suite + WKSP-900 contract test | data-layer-expert, backend-architect |
| `docs/dev/architecture/runbooks/workspace-migration-rollback.md` | Operator rollback runbook | data-layer-expert |

---

## Testing Strategy

### Unit Tests

- `dry_run()` zero-write proof (mtime/hash snapshot comparison).
- `backfill()` / `rollback()` round-trip fidelity (byte-identical file content restoration).
- `backfill()` idempotency (running twice is a safe no-op).
- Manifest-driven rollback safety (a legitimately post-migration `"default"`-workspace record is
  never touched by an unrelated `migration_run_id`'s rollback).
- `auth.workspace_isolation` config validator (mirrors `_validate_auth_mode` test pattern).

### Integration Tests

- Full `tests/integration/test_workspace_isolation.py` suite: 0-leak parametrized sweep across
  every AC-1 `target_surfaces` router, both read and write, two workspaces, owner/admin override
  path, and the WKSP-900 response-body-equality contract test.
- `rf workspace migrate-dry-run` → `rf workspace migrate --apply` → `rf workspace enforce --on`
  (with a synthetic gate-1-approval artifact) → regression suite, run end-to-end against a fixture
  workspace as a single CI job, proving the full operator workflow this runbook describes actually
  works, not just each function in isolation.

### E2E Tests

- Not applicable in this phase (no `.tsx` touched) — Phase 8/9 cover E2E auth/workspace scenarios.

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Workspace migration breaks a working single-operator deployment | High | Dry-run (WKSP-301) + tested rollback (WKSP-302) before real backfill (WKSP-303); backfill is additive-only and does not itself change behavior; enforcement flip (WKSP-304) is separately gated |
| Human approves enforcement without actually reviewing dry-run output | High | `rf workspace enforce --on` mechanically refuses to run without a recorded gate-1-approval artifact referencing the specific dry-run/backfill report — approval is not just a verbal/Slack sign-off |
| Rollback manifest logic reverts records touched by unrelated, legitimate post-migration activity | Medium | Manifest keyed by `migration_run_id` + explicit record-id list, never by value-matching on `workspace_id == "default"`; tested explicitly (WKSP-302 AC) |
| `catalog_items` schema bump silently loses data on rebuild | Low | `catalog.db` is provably disposable (module docstring, `rebuild()` already shipped and exercised in P2/P3); no new risk introduced, only a new column |
| Enforcement flip introduces a leak on an un-covered router/repository call site | High | WKSP-305's 0-leak regression suite is parametrized across every AC-1 `target_surfaces` entry, not a spot check; Codex adversarial pass at P5.9 re-checks this |
| Migration work accidentally touches P4/P5.1/P5.2 files outside this phase's scope, causing merge conflicts across parallel worktrees | Medium | Dedicated worktree/branch for this phase (see Isolation & Execution Notes) |

---

## Isolation & Execution Notes

Given the Mode D / irreversible-migration risk profile of this phase, **execute Phase 3 in a
dedicated worktree/branch**, separate from any parallel phase work (P5.4 Clerk, P5.5 audit, P5.7
deferred-sensitivity are all running in parallel per the parent plan's dependency map, and none of
them should share a working tree with a phase that is rewriting durable `draft.yaml` files). This
mirrors the parent plan's `wave_plan.phases[].isolation: worktree` setting for `P5.3`. Merge only
after both reviewer gates (`task-completion-validator` and `karen`) have signed off and Human Gate
#1's approval artifact is recorded — do not merge mid-gate.

---

## Success Metrics

- **Completion**: All 6 tasks (WKSP-301 through WKSP-305, WKSP-900) + Human Gate #1 checkpoint
  complete.
- **Quality**: Both reviewer gates (`task-completion-validator` and `karen` isolation milestone)
  pass; no quality gate skipped.
- **Migration Safety**: 0 cross-workspace leaks (WKSP-305); rollback round-trip proven byte-identical
  (WKSP-302); dry-run prediction matched real backfill result exactly (WKSP-303).
- **Testing**: `tests/unit/test_workspace_migration_service.py` and
  `tests/integration/test_workspace_isolation.py` both green in CI, in both `auth_mode=none` and
  multi-identity fixture configurations.

---

## Notes

### Implementation Approach

Sequence strictly: WKSP-301 (dry-run + advisory predicate) → WKSP-302 (rollback, tested against a
fixture round-trip) → WKSP-303 (real backfill, additive only) → **Human Gate #1** → WKSP-304
(enforcement flip) → WKSP-305 + WKSP-900 (verification). Do not parallelize WKSP-303 with WKSP-302
— the backfill task intentionally reuses WKSP-302's already-tested code path rather than
re-implementing the same logic twice.

### Gotchas

- **`catalog_items` has no `workspace_id` column today** — do not assume it exists; this phase adds
  it (see Critical Schema Findings). Confusing this with `catalog_report_drafts` (which already has
  the column) is the single most likely early-execution mistake.
- **The durable source of truth for report drafts is `draft.yaml` on disk, not `catalog.db`** — any
  migration logic that only touches `catalog_report_drafts` rows has migrated nothing durable; a
  `rebuild()` would silently discard that work and re-derive nulls from the still-unmodified
  `draft.yaml` files.
- **`created_by` cannot be safely backfilled** — there is no historical record of who created a
  pre-migration draft/catalog item. Leave it null; do not invent a placeholder identity.
- **Rollback must never key on the `"default"` value itself** — only on the specific
  `migration_run_id`'s manifest — because legitimate post-enforcement usage will also produce
  `workspace_id="default"` records that must never be touched by an earlier rollback.

### Learnings

*(Populate during execution.)*

### Findings Captured This Phase

- [ ] No new findings this phase (default)

---

**Phase Version**: 1.0
**Last Updated**: 2026-07-06

[Return to Parent Plan](../public-multiuser-p5-auth-rbac-v1.md)
