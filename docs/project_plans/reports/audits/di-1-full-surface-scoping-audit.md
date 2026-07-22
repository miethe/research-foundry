---
title: "DI-1 Full-Surface Workspace-Scoping Audit"
doc_type: audit
schema_version: 2
feature_slug: public-multiuser-release-activation
phase: P4
created: 2026-07-22
updated: 2026-07-22
status: accepted
gate_ref: "Config.deployment_mode_validate() condition (d), FR-13"
signoff:
  decision: accepted
  scope_accepted: "trusted-cohort multi_user only (NOT adversarial multi-tenant isolation for runs/evidence)"
  signed_by: nick (human operator)
  signed_via: "Mode D human sign-off gate, /dev:execute-plan Wave 2/4 (ACT-406)"
  signed_date: 2026-07-22
  residual_risk_acknowledged: >
    Rows 10-12 (runs/claims/evidence have no workspace_id → cross-workspace read + writeback
    dispatch under multi_user) and row 9 (agent-jobs client-supplied workspace_id → spoofable
    FR-12 attribution) are explicitly accepted as deferred; tracked to DF-series design specs
    authored in P6. This acceptance does NOT authorize an untrusted multi-tenant deployment.
audited_commits: "60f40c8 (P1) + uncommitted worktree state at audit time (P2/P3 in-flight, ACT-203 auth chain); DELTA-AUDIT (2026-07-22, this revision) re-traces admin.py at HEAD in the public-multiuser-release-activation worktree, covering the 10 service-account/PAT/deployment-mode-status endpoints added by the P3/P5 admin surface (ACT-301..303) since the original 54-endpoint enumeration — see \"Surface widened post-acceptance\" below."
authorization_scope: >
  Accepting this audit (setting status: accepted) authorizes a TRUSTED-COHORT
  multi_user deployment only — callers who are not adversarial toward each
  other, sharing the install by convenience/organization rather than needing
  hard isolation guarantees. It does NOT certify tenant isolation for runs,
  claims, source cards, or evidence bundles: rows 10-12 below found that the
  run/evidence-bundle data model has no workspace_id concept at all, so
  every run in the install is listable and readable (including its full
  claim ledger, context, source cards, and anchors) by any authenticated
  caller in ANY workspace, and any authenticated caller can trigger a
  writeback dispatch on any run regardless of workspace. This is the
  headline residual risk a human accepting this document must weigh
  explicitly — see "SCOPE BOUNDARY STATEMENT" below, which opens with this
  same caveat verbatim.
revision_note: >
  karen (REV-P4-001, Mode E) returned CHANGES_REQUESTED on the first draft:
  the endpoint-count claim did not reconcile against an independent grep
  (claimed 61, actual 54) and the runs/evidence scope caveat was buried in
  the Conclusion rather than surfaced up front. Both fixed in this revision,
  along with three lesser corrections (row 21 factual error on
  verify_access_token reachability, row 12's severity reclassification, and
  an explicit FR-12 audit-spoofability caveat on row 9) — documentation-only,
  no gate code or acceptance status changed. See "Count reconciliation" and
  the elevated scope-boundary opening below.
---

# DI-1 Full-Surface Workspace-Scoping Audit

## STATUS (read this first)

**`status: accepted`** — set 2026-07-22 by the human operator (nick) via the Mode D
sign-off gate (see `signoff:` in the frontmatter). This was NOT self-certified by an
agent: per `.claude/rules/delegation-modes.md` Mode D and this phase's plan
(`phase-4-di1-audit-enforcement.md`, ACT-406), the audit was held at
`pending-human-signoff` until the operator explicitly reviewed the scope-boundary
statement below and accepted the **trusted-cohort** scope, expressly acknowledging the
rows 10-12 / row 9 residual risk as deferred. `Config.deployment_mode_validate()`
(ACT-402) reads this field literally — only the string `accepted` satisfies condition
(d); any other value fails closed. The **operator-ack half** of the FR-13 gate
(`auth.di1_audit_acknowledged`) remains a deploy-time config the operator sets on the
target install; both halves are required for `multi_user` to start.

## SCOPE BOUNDARY STATEMENT (for human sign-off)

**Read this paragraph first — it is the decision, not a footnote.** Accepting
this audit (setting `status: accepted`) authorizes a **trusted-cohort**
`multi_user` deployment only — callers who are not adversarial toward each
other. **It does NOT certify tenant isolation for runs, claims, source
cards, or evidence bundles.** Rows 10-12 (§ Per-surface table) found that
the run/evidence-bundle data model has **no `workspace_id` concept at all**:
every run in the install — its full claim ledger, context, source cards, and
anchors — is listable and readable by any authenticated caller in **any**
workspace, and any authenticated caller can trigger a writeback dispatch on
any run regardless of workspace. This is the single largest, highest-
priority open finding in this document (see "Residual risk — headline
finding" below) and the human reviewer's explicit accept-or-block call, not
something to discover by reading to the end.

**What was enumerated:** every HTTP router (`src/research_foundry/api/routers/*.py`,
9 files) and every service module those routers call into that reads or
writes a row carrying (or logically owned by) a `workspace_id` —
`catalog_service.py`, `builder_service.py`, `agent_job_service.py`,
`audit_service.py`, `assertion_catalog.py`, `assertion_impact.py`,
`rbac_store.py`, `share_store.py`, `run_launch.py`, `writeback.py`,
`workspace_migration_service.py`, `source_cards.py`. This supersedes the
prior `assertion-ledger-activation-di1-scoped-audit.md`, which explicitly
scoped itself to one feature's write-site delta only (per the WKSP-304 AAR,
that prior audit's own text names this full-project audit as the outstanding
gate).

**What was explicitly excluded, and why:**
1. **CLI-only, single-operator-trust entry points** (`rf ingest`, `rf catalog
   rebuild`, `rf writeback`, `rf assertion backfill`) — per `api/auth/rbac.py`'s
   documented classification, these bypass the HTTP router layer entirely and
   are not reachable by a multi-tenant caller; `test_cli_mutation_surface.py`
   already verifies no HTTP path reaches them unguarded. Not re-verified here.
2. **An in-progress, uncommitted composite-auth-chain subsystem** (ACT-203:
   `rbac_store.py`'s `service_accounts`/`access_tokens` tables,
   `services/token_service.py`, `api/middleware/auth.py`'s
   `AuthProviderMiddleware._resolve_token_identity`) was present in this
   shared worktree at audit time from a concurrent phase. Its
   identity-resolution output (`AuthIdentity(user_id, workspace_id, roles)`)
   was reviewed and is shape-identical to every other auth path this audit
   already covers — no special-casing required for the scoping checks below.
   **Correction (karen REV-P4-001):** the first draft claimed none of this
   subsystem's four functions were HTTP-reachable. That was wrong for one of
   them — see row 22/23 below, which now distinguishes the reachable READ
   path from the three still-unwired WRITE functions.
3. **`frontend/runs-viewer`** — a static-export SPA; it has no server-side
   write surface of its own (all writes go through the routers audited
   below). Not separately enumerated.

**Count reconciliation (karen REV-P4-001 finding, corrected; DELTA-AUDIT
2026-07-22 re-reconciled at HEAD).** The first draft of this document claimed
"61 endpoints total" and that re-running its grep would reproduce that
number. It did not: an independent check found the real total was **54** at
original-audit time, and one row (reports.py) undercounted by 4 while one
whole router (admin.py, 4 of its 6 endpoints) was omitted from the table
entirely. This is exactly the failure class the WKSP-304 AAR flags — a
coverage claim that does not survive re-running its own verification command
— so it was corrected in that revision with the literal reproducing command
and the exact per-file counts, not just a revised total. **Since acceptance,
10 new endpoints were added to `admin.py`** (service-account CRUD + tokens,
PAT CRUD, deployment-mode-status — ACT-301..303, see "Surface widened
post-acceptance" below), so the count re-reconciled at HEAD in this revision
is **64**, not 54:

```bash
grep -rEc '@router\.(get|post|patch|delete|put)' src/research_foundry/api/routers/*.py
```

```
admin.py:16  agent_jobs.py:6   assertions.py:4   audit.py:3   auth_identity.py:1
catalog.py:5   reports.py:21   runs.py:7   writeback.py:1        TOTAL = 64
```

Every one of these 64 endpoints is now individually accounted for in the
per-surface table below (each endpoint appears in exactly one row's endpoint
list; the router-backed rows' endpoint-counts sum to 64 — verified by hand
against the `grep -n` listing per file, reproduced in the Method section).
Corrections/updates across both revisions:
- **reports.py** (original revision): first draft's row 1 said "15" (and
  "versions ×3"); the real per-file count is **21** — 19 in row 1
  (`versions ×4`, not ×3 — the missed one was `restore_version`) + 2 in row 2
  (the share-link pair).
- **admin.py** (original revision): first draft's row 13 named only 2 of
  admin.py's then-6 endpoints (`get_workspace_members`, `update_member_role`).
  The other 4 (`get_auth_provider_status`, `get_rate_limit_config`,
  `update_rate_limit_config`, `get_rbac_status`) were never in the table at
  all — added as row 14 (all four are install-wide config reads/writes with
  no per-workspace row to leak, verified CONFINED by reading each in full —
  not silently assumed).
- **admin.py** (DELTA-AUDIT, this revision): `admin.py` grew from 6 to 16
  endpoints since acceptance. The 10 new ones (service-account CRUD/tokens,
  PAT CRUD, deployment-mode-status) are added below as rows 30-33, all
  verdict **CONFINED** — see "Surface widened post-acceptance."

## Method

Two complementary sweeps, chosen to extend (not repeat) the prior
feature-scoped audit's method (backward-trace from write call to gate):

1. **Router sweep (forward, by surface):** for every router file, every
   `@router.get/post/patch/delete` handler was read in full. For each, the
   question asked was: *does this handler either (a) resolve
   `identity = getattr(request.state, "identity", None)` and thread it into
   a service call that itself denies on workspace mismatch, OR (b) derive any
   workspace_id it uses for a write from `identity.workspace_id` rather than
   from client input (body/query/path)?* Handlers with neither were flagged.
   Enumeration grep (reconciled against, see Count reconciliation above):
   `grep -rEc '@router\.(get|post|patch|delete|put)' src/research_foundry/api/routers/*.py`.
2. **Service backward-trace (write-focused, extends the prior audit's
   method):** for every `INSERT INTO`/`UPDATE`/`DELETE FROM` and every
   file-write helper (`_atomic_write_yaml`, `_save_draft`, `_safe_write_json`)
   in the 12 service modules, traced backward to confirm a workspace-owning
   identity is stamped from the resolved caller (not trusted verbatim from a
   request body) before the write commits. Grep used:
   `grep -rn "INSERT INTO\|UPDATE \|DELETE FROM" src/research_foundry/services/*.py`.
3. **Targeted re-verification of the two known prior leaks** named in the
   phase plan (`create_draft_from_run`/`create_draft_from_collection`,
   `catalog_service.get_item`) — read in full to confirm the WKSP-304
   remediation is still in place and unregressed (it is — see rows 3, 6).

## Residual risk — headline finding (read before the full table)

**Rows 10-12: runs, claims, source cards, and evidence bundles have NO
`workspace_id` concept in the data model at all.** This is not a missed
check on an existing field — it is an absent field, and it is the single
largest gap this audit found:

- `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/claims`,
  `GET /runs/{id}/context`, `GET /source-cards/{id}`, `GET /reports/{id}/anchors`
  (row 10) — none of these 6 read endpoints check `identity` because there is
  no `workspace_id` column/key anywhere in the run-record schema to check
  against. Any authenticated caller, in any workspace, can currently list and
  read the full detail/claims/context/source-cards/anchors of **every** run
  in the install.
- `POST /runs` (row 11, launch) — `identity` is fetched and unused; the run
  being created is never stamped with an owning workspace in the first place,
  which is the root cause row 10 inherits.
- `POST /runs/{id}/writeback/approve` (row 12) — **this is a cross-tenant
  WRITE/ACTION, not merely a could-not-verify read gap**: any authenticated
  caller can trigger a real writeback dispatch (to MeatyWiki/SkillMeat/CCDash
  targets) against any run in any workspace, because the run being dispatched
  is never workspace-checked. Reclassified in this revision from
  "could-not-verify" to **NEEDS-REMEDIATION**, the same severity tier as rows
  10/11 — read-only under-scoping and an unscoped write/dispatch action are
  not the same risk class, and the table below no longer conflates them.

This is squarely a multi-tenant-readiness gap: the run/evidence-bundle data
model predates the workspace concept and was never retrofitted. It needs a
dedicated design decision (does a run belong to the workspace of the
identity that launched it? Is run data intentionally cross-workspace-shared,
e.g. a shared research corpus?) before it can be remediated — which is why
it is not attempted in this wave. **This is the finding the human reviewer
must weigh explicitly when deciding whether to accept this document** — see
the frontmatter `authorization_scope` field and the opening of the Scope
Boundary Statement above, both of which state this same caveat verbatim so
it cannot be missed by skimming to the Conclusion.

## Per-surface table

Verdict legend: **CONFINED** (scoped-ok) · **REMEDIATED** (was a clear leak,
fixed in this same commit, now scoped-ok) · **NEEDS-REMEDIATION** (a real,
named gap — read-under-scoping or an unscoped write/action — not fixed here
because it is design-level/ambiguous/multi-file, logged for a dedicated
future task rather than guessed at) · **COULD-NOT-VERIFY** (excluded from
full trace, flagged explicitly rather than assumed covered).

| # | Surface | File(s) | Verdict | Note |
|---|---------|---------|---------|------|
| 1 | `POST/GET/PATCH/DELETE /reports*` — 19 mutation+read endpoints (`create_draft`, `list_drafts`, `get_draft`, `delete_draft`, versions ×4 [`list_versions`, `create_version`, `get_version`, `restore_version`], blocks ×4 [`add_block`, `reorder_blocks`, `update_block`, `delete_block`], claim-links ×2, source-links ×2, `verify_draft`, `publish_preview`, `export_draft`) | `api/routers/reports.py` | **CONFINED** | Router calls `bsvc.load_draft(paths, report_id, identity=identity)` and catches `NotFoundError`→404 **before** every mutator. `load_draft` raises `NotFoundError` on a cross-workspace mismatch once isolation is enforced (verified read in full, `builder_service.py:302-367`). The mutators themselves (`add_block` etc.) take no `identity` param by design — the router pre-check is the sole deny mechanism, verified for all 15 mutator/read call sites in `reports.py` beyond the initial create/list pair. |
| 2 | `POST /reports/{id}/share-link`, `GET /share/{token}` (2 endpoints) | `api/routers/reports.py` (create_share_link, resolve_share_link) | **CONFINED** | `create_share_link` is gated by the same `load_draft(identity=identity)` pre-check as row 1. `resolve_share_link` deliberately passes `identity=None` — documented invariant: "session identity/workspace membership must never broaden OR narrow access to the one resource the token names." Intentional, not a gap. Rows 1+2 = 19+2 = 21, matching `reports.py`'s reconciled grep count. |
| 3 | `create_draft`, `create_draft_from_run`, `create_draft_from_collection` (create-path stamping) | `services/builder_service.py:455-1157` | **CONFINED** | Re-verified the two named prior leaks: `workspace_id` param is overridden by `identity.workspace_id` whenever `identity` is not `None` (line 511) — client input never wins once an identity resolves. Unregressed since WKSP-304. |
| 4 | `GET /catalog/stats` | `api/routers/catalog.py:54-62` | **NEEDS-REMEDIATION** | `identity` is fetched but marked `# noqa: F841` with an explicit in-code `TODO(WKSP-304 P4)` — `svc.stats()` has no `identity` param, so aggregate item counts are returned across **all** workspaces regardless of caller. Low severity (counts only, no record content) but real once multiple tenants exist. Proposed fix: add `identity` param to `catalog_service.stats()`, gate the `COUNT(*) ... GROUP BY item_type` query behind the same `_isolation_active`-gated `AND workspace_id = ?` predicate `search()`/`get_item()` already use. Not fixed this wave — single-function, low-risk, but touches an aggregate query with no existing test harness for cross-tenant counts; deferring to keep this wave's diff minimal and reviewable. |
| 5 | `GET /catalog/search` | `api/routers/catalog.py:65-99` | **CONFINED** | Threads `identity` into `svc.search()`, which applies an `_isolation_active`-gated `AND workspace_id = ?` predicate (`catalog_service.py:1289,1294-1295`). |
| 6 | `GET /catalog/items/{id}` | `api/routers/catalog.py:102+` → `catalog_service.get_item` | **CONFINED** | Re-verified the second named prior leak in full (`catalog_service.py:1518-1666`): scoped `WHERE catalog_item_id = ? AND workspace_id = ?` on the primary row, the same predicate applied to both the outgoing/incoming link JOINs and the citing-drafts JOIN (so a cross-workspace edge can't leak through even once isolation is active), plus an audit-logged enforced-denial helper. Unregressed. |
| 7 | `POST /catalog/import/run/{id}`, `POST /catalog/import` (2 endpoints) | `api/routers/catalog.py:126-165` → `catalog_service.import_run`/`import_all` | **NEEDS-REMEDIATION** | Every imported catalog item is stamped `workspace_id="default"` unconditionally (`catalog_service.py:548`, explicitly commented `# WKSP-303: all CLI/CLI-run imports land in "default"`) — `identity` is fetched in the router but marked `# noqa: F841`/`TODO(WKSP-304 P4)`, never threaded in. This is a **documented, intentional prior design decision**, not an accidental miss — but it means that once `deployment_mode=multi_user` is live, a non-`"default"`-workspace caller's own catalog imports still land in `"default"`, and (per row 6's now-active enforcement) that caller would then see **zero** of their own imported items via `get_item`/`search`. This is a functional/UX gap as much as a security one. Proposed fix: thread `identity` through `import_run`/`import_all`, stamp `identity.workspace_id` when present (mirroring `create_draft`'s pattern), else keep `"default"`. Deferred: this is a multi-tenant catalog-ownership *design* decision (does re-importing the same run from two workspaces produce two rows, or one shared row with an ownership conflict?) that this audit is not positioned to unilaterally decide — logging as a finding for a dedicated future task rather than guessing. Rows 4+5+6+7 = 1+1+1+2 = 5, matching `catalog.py`'s reconciled grep count. |
| 8 | `GET /agent-jobs/{id}`, `GET /agent-jobs/{id}/artifacts`, `GET /agent-jobs/{id}/events`, `POST /agent-jobs/{id}/cancel`, `POST /agent-jobs/{id}/accept` (5 endpoints) | `api/routers/agent_jobs.py` → `AgentJobService.load_job`/`_load_job_or_404` | **CONFINED** | Every one of these 5 endpoints calls `_load_job_or_404(service, job_id, identity=identity)` first; `load_job` raises on a cross-workspace mismatch once isolation is active (same file-storage-predicate idiom as `builder_service.load_draft`, verified in full: `agent_job_service.py:837-916`). Downstream calls in the same handler (`list_staged_artifacts`, `terminate_job`, `cleanup_job`, `update_job_status`, `accept_job`) take no `identity` param themselves — by the same router-pre-check-is-the-gate contract as row 1, not independently re-verified per call but consistent with the established, tested idiom. |
| 9 | `POST /agent-jobs` (create, 1 endpoint) | `api/routers/agent_jobs.py:149-260` → `AgentJobService.create_job` | **NEEDS-REMEDIATION** | `identity` is fetched (`# noqa: F841`) but never used. `workspace_id=body.workspace_id` is taken **verbatim from the client-supplied request body**, not stamped from `identity.workspace_id` — unlike `builder_service.create_draft`'s "identity always overrides client input" pattern. A caller could launch a job tagged with an arbitrary `workspace_id`, and the audit-trail row's `actor_workspace_id` (`agent_jobs.py:252`) inherits the same unverified client value. **FR-12 caveat:** this makes the `agent_job_launched` audit-trail attribution **spoofable until this row is fixed** — `agent_job_service.py:889` (the ACT-204/FR-12 identity-binding audit-event write, see below) records `actor_workspace_id=workspace_id` straight from this same unverified `body.workspace_id`, so the FR-12 execution-identity-vs-triggering-identity split does not protect the `actor_workspace_id` field even though it correctly protects `created_by`. Explicitly documented in-code as deferred (`D12 — auth in P5`, repeated `TODO(WKSP-304 P4)` comments across this router). Not fixed this wave: the correct fix touches the job-creation contract, the audit-trail sourcing, and likely `spawn_job`/`update_job_status`'s own `TODO` markers together — multi-call-site, needs its own test plan. **Adjacent, uncommitted, concurrent work found at audit time (ACT-204/FR-12, `agent_job_service.py::create_job`) adds an execution-identity vs. triggering-identity split for `created_by` under a configured default service account — it does not touch `workspace_id` at all and does NOT close this finding (see the FR-12 caveat above); re-check this row once ACT-204 lands.** Rows 8+9 = 5+1 = 6, matching `agent_jobs.py`'s reconciled grep count. |
| 10 | `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/claims`, `GET /runs/{id}/context`, `GET /source-cards/{id}`, `GET /reports/{id}/anchors` (6 endpoints) | `api/routers/runs.py` | **COULD-NOT-VERIFY** — **HEADLINE RESIDUAL RISK, see section above** | **Runs have no `workspace_id` field in their data model at all.** Any authenticated caller (any workspace) can currently list and read the full detail/claims/context/source-cards/anchors of **every** run in the install. See "Residual risk — headline finding" above — this is the single largest, top-priority open item in this document, not a co-equal bullet among several. |
| 11 | `POST /runs` (launch, 1 endpoint) | `api/routers/runs.py:384-425` → `run_launch.py::launch_run` | **NEEDS-REMEDIATION** — **HEADLINE RESIDUAL RISK, same root cause as row 10** | `identity` fetched, `# noqa: F841`, unused. `reuse_workspace_id` is used ONLY to gate the assertion-*reuse* decision (`resolve_or_deny`), not to stamp ownership of the run being launched — this is the root cause row 10 inherits. Rows 10+11 = 6+1 = 7, matching `runs.py`'s reconciled grep count. |
| 12 | `POST /runs/{id}/writeback/approve` (1 endpoint) | `api/routers/writeback.py:263-351` | **NEEDS-REMEDIATION** — **HEADLINE RESIDUAL RISK, reclassified from could-not-verify (karen REV-P4-001)** | **This is a cross-tenant WRITE/ACTION, not merely an under-scoped read** — any authenticated caller can trigger a real writeback dispatch against any run in any workspace, for the same root cause as row 10 (runs are not a workspace-scoped resource today). Previously classified could-not-verify at the same tier as a read gap; corrected here to the same severity tier as rows 10/11 since dispatching a real external writeback is an action with side effects, not just an information leak. `identity.user_id` IS threaded into `approve_and_dispatch`'s `approver_identity` (for the `approved_by` audit field), so the *actor* is correctly attributed even though the *run* itself isn't workspace-checked. Matches `writeback.py`'s reconciled grep count of 1. |
| 13 | `GET /admin/workspace`, `PATCH /admin/members/{user_id}/role` (2 endpoints) | `api/routers/admin.py:131-217` | **CONFINED** | `workspace_id` is derived **exclusively** from `_resolve_workspace_id(request)` (the caller's own `identity.workspace_id`, defaulting to `"default"` only in no-auth mode) — never client-supplied. `rbac_store.update_member_role`'s `UPDATE ... WHERE user_id = ? AND workspace_id = ?` (verified in full) cannot touch a membership row outside the caller's own workspace. |
| 14 | `GET /admin/auth-provider-status`, `GET /admin/rate-limit-config`, `PATCH /admin/rate-limit-config`, `GET /admin/rbac-status` (4 endpoints) | `api/routers/admin.py:225-437` | **CONFINED** | **Added in this revision (karen REV-P4-001) — omitted from the first draft's table entirely.** All four are install-wide (process-global) config reads/writes with no per-workspace row to leak: active auth provider name + availability, in-memory rate-limit budget, and RBAC enforcement state/effective flag — none of these have a `workspace_id` dimension at all, verified by reading each handler in full (`admin.py:225-277`, `285-390`, `394-437`). Rows 13+14 = 2+4 = 6, matching `admin.py`'s reconciled grep count. |
| 15 | `GET /audit`, `GET /audit/{id}` (2 endpoints) | `api/routers/audit.py` → `audit_service.list_events`/`get_event` | **REMEDIATED (this audit)** | **Clear, unambiguous cross-tenant leak, fixed in this same commit.** RBAC-006 gates these routes on `owner`/`admin`, but that role is workspace-scoped (`AuthIdentity.roles` — "granted... within the workspace", `api/auth/provider.py`); `require_role` only checks role membership, never workspace. `list_events` accepted a **client-supplied** `workspace` query param with no cross-check against the caller's identity (and defaulted to **zero** filter — all workspaces — when omitted); `get_event` had **no workspace parameter at all**. An owner/admin of workspace A could read workspace B's actor IDs and policy snapshots by passing `?workspace=B`, or every workspace's events by omitting the filter, or any single event by ID regardless of workspace. **Fix:** both functions now accept `identity`; once isolation is enforced, the caller's own `identity.workspace_id` always overrides any client-supplied `workspace` filter (`list_events`), and a workspace mismatch on `get_event` returns `None` (indistinguishable-404, same idiom as `catalog_service.get_item`). `identity=None` or isolation-inactive is byte-identical to pre-fix behavior (FR-2 regression guard). Regression tests: `tests/unit/test_audit_service.py::TestListEventsWorkspaceScoping`/`TestGetEventWorkspaceScoping` (service-level), `tests/unit/test_audit_rbac.py::TestAuditCrossTenantScoping` (router-level, end-to-end). |
| 16 | `GET /audit/health` | `api/routers/audit.py:74-94` | **CONFINED** | Returns only an aggregate healthy/degraded boolean + probe timestamps — no per-workspace record content to leak. Rows 15+16 = 2+1 = 3, matching `audit.py`'s reconciled grep count. |
| 17 | `GET /assertions/search`, `GET /assertions/{id}/lineage`, `GET /assertions/{id}/impact`, `GET /assertions/{id}` (4 endpoints) | `api/routers/assertions.py` → `assertion_catalog.py`, `assertion_impact.py` | **CONFINED** | Every method **requires** `identity` and denies (`None`/empty result) when absent or `workspace_id` is blank (`assertion_catalog.py:132,186`; `assertion_impact.py:132-133`) — stricter than the advisory-by-default idiom elsewhere (fail-closed unconditionally, not gated on `_isolation_active`). Projection cache keys are workspace-hashed (`_workspace_key`, `assertion_catalog.py:55-56`). Also covered by the prior feature-scoped audit; re-verified independently here. Matches `assertions.py`'s reconciled grep count of 4. |
| 18 | `GET /auth/identity` (1 endpoint) | `api/routers/auth_identity.py` | **CONFINED** | Echoes the caller's own resolved identity only; no other workspace's data is reachable. Matches `auth_identity.py`'s reconciled grep count of 1. |
| 19 | `assertion_registry.py`, `assertion_materialization.py`, `assertion_rollout.py`, `claim_mapping.py`, `run_launch.py`'s reuse-decision path | services | **CONFINED** | Covered by `assertion-ledger-activation-di1-scoped-audit.md` (prior art); F1/F2 findings there were remediated same-pass and are unregressed (spot-checked `backfill_run`'s self-gating `resolve_or_deny` call, still present). |
| 20 | `assertion_impact.py::AssertionImpactReconciler` | `services/assertion_impact.py` | **CONFINED** | Flagged as out-of-scope-but-incidental (F3) by the prior audit; independently re-traced here in full (row 17's grep) — requires `workspace_id`, raises on blank. F3 closed. |
| 21 | `rbac_store.py::list_workspace_members`, `update_member_role`, `get_member_role` | `services/rbac_store.py` | **CONFINED** | Every function takes an explicit `workspace_id` param and includes it in the `WHERE` clause; no function returns cross-workspace rows without an explicit, caller-supplied filter — and the one HTTP caller (row 13) always supplies its own identity's workspace. |
| 22 | `rbac_store.py::verify_access_token` (via `token_service.verify_token`) | `services/rbac_store.py`, `services/token_service.py`, `api/middleware/auth.py:258` | **CONFINED — but genuinely HTTP-reachable (karen REV-P4-001 correction)** | **The first draft's row 21 incorrectly stated ALL four ACT-203 token/service-account functions were "not HTTP-reachable."** That is false for this one: `AuthProviderMiddleware._resolve_token_identity` (`api/middleware/auth.py:258`) calls `token_service.verify_token()` on **every** authenticated request when `paths` is configured (verified: `verify_token` → `rbac_store.verify_access_token(conn, token_prefix)` at `token_service.py:369`), so this read path IS live today, not merely wired-but-inert. It is CONFINED: the returned `ResolvedIdentity` carries the token's own bound `workspace_id` (enforced at issuance, `token_service.py:307`), and comparisons use plain string equality on a value that was never client-suppliable at verify time — a token cannot be presented "as" a different workspace than the one it was issued for. |
| 23 | `rbac_store.py::create_service_account`, `create_access_token`, `list_service_accounts(workspace_id=None)` | `services/rbac_store.py` | **CONFINED — now HTTP-reachable, re-audited (DELTA-AUDIT 2026-07-22)** | **Superseded finding.** At original-audit time these three WRITE/list functions were genuinely not wired to any router — flagged COULD-NOT-VERIFY with an explicit "re-audit the moment a router wires any of these three" instruction. That router now exists: `admin.py`'s service-account routes (rows 30-31 below, ACT-301) call `create_service_account` (via `create_service_account_route`, always passed `workspace_id=_resolve_workspace_id(request)` — the caller's own identity, never client-supplied) and `list_service_accounts` (via `list_service_accounts_route`, always passed the caller's own `workspace_id=...`, **never** `None` — the only unscoped call site the original finding warned about does not exist on this router). `create_access_token` is only ever called by `token_service._issue`, itself only reached via `issue_service_account_token` (workspace taken from the service account's own immutable row) or `issue_user_pat` (workspace taken from the caller's own identity) — never with a client-suppliable `workspace_id`. Re-verified in full per "Surface widened post-acceptance" below. |
| 24 | `share_store.py::create_share_link`/`resolve_share_link`/`revoke_share_link` | `services/share_store.py` | **CONFINED** | `create_share_link`/`revoke_share_link` are only reachable through `reports.py` handlers already gated by row 1/2's `load_draft(identity=identity)` pre-check. `resolve_share_link` is intentionally identity-agnostic (row 2). |
| 25 | `workspace_migration_service.py` (WKSP-301/302/303 dry-run/backfill tooling) | `services/workspace_migration_service.py` | **CONFINED** | CLI-only per `api/auth/rbac.py`'s documented classification (not HTTP-reachable); this audit did not independently re-verify `test_cli_mutation_surface.py`'s claim, relying on that existing, named regression test instead of re-deriving it. |
| 26 | `source_cards.py::ingest_source`/`create_source_card` | `services/source_cards.py` | **CONFINED** | CLI-only (`rf ingest`), same classification as row 25; also independently re-verified as CONFINED by the prior feature-scoped audit (F1, remediated). |
| 27 | `swarm_drive.py` | `services/swarm_drive.py` | **COULD-NOT-VERIFY** | One incidental `workspace_id=None` reference found (line 1286) during the grep sweep; not traced to a conclusion given this wave's time-box. No router directly exposes this module by name, but it was not fully read end-to-end. Flagging rather than assuming CONFINED. |
| 28 | `agent_job_schemas.py`, `assertion_reuse.py`, `audit_service.record_event`'s write path itself | services | **CONFINED** | `record_event`'s `actor_workspace_id` is whatever the calling router/service passes in as an `AuditEvent` field — it has no independent trust boundary of its own; its correctness is entirely a function of the **caller's** scoping, which is covered by that caller's own row above (e.g. row 9's agent-jobs finding, including its FR-12 caveat, is what makes *that* particular `record_event` call's `actor_workspace_id` spoofable, not a defect in `record_event`/`audit_service.py` itself). |
| 29 | `frontend/runs-viewer` (SPA) | N/A | **CONFINED** | No server-side write surface; all API calls terminate in the routers above. Not separately enumerated (see Scope Boundary #3). |
| 30 | `POST /admin/service-accounts`, `GET /admin/service-accounts`, `DELETE /admin/service-accounts/{id}` (3 endpoints) | `api/routers/admin.py:671-806` → `services/rbac_store.py`, `services/audit_service.py` | **CONFINED (DELTA-AUDIT 2026-07-22, new since acceptance — ACT-301)** | All three derive `workspace_id` exclusively from `_resolve_workspace_id(request)` (caller's own `identity.workspace_id`, defaulting to `"default"` only in no-auth mode) — never client-supplied. `create_service_account` stamps that workspace_id at insert (`rbac_store.create_service_account`). `list_service_accounts_route` calls `rbac_store.list_service_accounts(conn, workspace_id=workspace_id)` — the caller's own value, never `None` (see row 23's supersession). `disable_service_account_route` calls the shared `_get_service_account_or_404` helper first, which 404s uniformly for "unknown id" and "exists but in another workspace" (`account["workspace_id"] != workspace_id`, `admin.py:666`) — the mirror-image of `catalog_service.get_item`'s (row 6) cross-workspace-existence-hiding convention. Verified with a new regression test class, `TestCrossWorkspaceIsolation` (`tests/unit/test_admin_tokens_api.py`): an owner in `ws_a` creating an account is invisible to an owner in `ws_b`'s list, and `ws_b` disabling `ws_a`'s account 404s. |
| 31 | `POST /admin/service-accounts/{id}/tokens`, `GET /admin/service-accounts/{id}/tokens`, `DELETE /admin/service-accounts/{id}/tokens/{token_id}` (3 endpoints) | `api/routers/admin.py:809-939` → `services/token_service.py`, `services/rbac_store.py` | **CONFINED (DELTA-AUDIT 2026-07-22, new since acceptance — ACT-301)** | Every handler calls `_get_service_account_or_404(paths, account_id, workspace_id)` FIRST (same cross-workspace-hiding gate as row 30), so `account_id` is guaranteed to belong to the caller's own workspace before any token operation runs. `issue_service_account_token_route` → `token_service.rotate_service_account_token` → `issue_service_account_token`, which re-reads the account row and takes `workspace_id`/`role` from it directly (never client-suppliable) — this is safe because `service_accounts.workspace_id` is immutable (no "move workspace" mutation exists anywhere in `rbac_store.py`, confirmed by an exhaustive function-name grep). `list_service_account_tokens_route` filters `token_service.list_tokens(principal_id=account_id, principal_type="service")` without an explicit `workspace_id` param, but this is still CONFINED: `access_tokens.workspace_id` is stamped from the owning account's workspace at issuance and that account's workspace is immutable, so filtering by an already-workspace-verified `principal_id` is equivalent to filtering by workspace. `revoke_service_account_token_route` additionally re-checks `token["workspace_id"] != workspace_id` explicitly (belt-and-suspenders, `admin.py:921`) before revoking. Verified with `TestCrossWorkspaceIsolation`: `ws_b` cannot list, rotate/issue, or revoke `ws_a`'s service-account tokens — all three 404. |
| 32 | `POST /admin/pats`, `GET /admin/pats`, `DELETE /admin/pats/{token_id}` (3 endpoints) | `api/routers/admin.py:952-1136` → `services/token_service.py`, `services/rbac_store.py` | **CONFINED (DELTA-AUDIT 2026-07-22, new since acceptance — ACT-302)** | Documented, deliberate exception to the blanket `Depends(require_role(...))` pattern (module docstring's "Self-service exceptions" — same documented-exception class as `reports.py`'s `publish-preview`): permission depends on request body/path content (whose PAT), not just the caller's role, so it is enforced manually per-handler instead. `issue_pat` resolves `workspace_id` from the caller's own identity only, then calls `token_service.issue_user_pat(workspace_id=workspace_id, ...)`, which internally re-checks `rbac_store.get_member_role(conn, issuer_user_id, workspace_id)` — this means an owner/admin in `ws_b` **cannot** issue a PAT on behalf of a user whose only membership is in `ws_a` (404, "issuer has no membership in this workspace"), closing exactly the cross-workspace-impersonation shape this delta-audit was scoped to find. `list_pats` always filters `token_service.list_tokens(workspace_id=_resolve_workspace_id(request), ...)` — an owner/admin targeting another user's PATs via `?user_id=` still only sees that user's PATs **within the caller's own workspace**, never a same-user_id PAT issued under a different workspace. `revoke_pat` checks `token["workspace_id"] != identity.workspace_id` FIRST and 404s (existence hidden) before the self-vs-admin 403 check runs — cross-workspace is never distinguishable from unknown-token, only same-workspace-different-user is a knowable 403. Verified with 3 new `TestCrossWorkspaceIsolation` cases: `ws_b` cannot issue-on-behalf into `ws_a`'s membership (404), cannot revoke `ws_a`'s PAT (404, not 403), and an owner/admin's `?user_id=` list stays scoped to their own workspace even when the same user_id holds a PAT elsewhere. |
| 33 | `GET /admin/deployment-mode-status` (1 endpoint) | `api/routers/admin.py:1144-1173` → `config.deployment_mode_status()` | **CONFINED (DELTA-AUDIT 2026-07-22, new since acceptance — ACT-303)** | Read-only introspection over process-global `FoundryConfig` state (resolved `deployment_mode` + FR-4 startup-gate condition pass/fail) — install-wide, no per-workspace row exists to leak, same category as row 14's auth-provider-status/rate-limit/rbac-status endpoints. Docstring and `tests/unit/test_admin_tokens_api.py::TestDeploymentModeStatusEndpoint::test_no_secret_material_in_conditions` both independently confirm no secret material appears in `conditions[].detail`. |

**Router-backed row endpoint counts, reconciled against the grep total of
64 (re-reconciled at HEAD, DELTA-AUDIT 2026-07-22):** row 1 (19) + row 2 (2)
= reports.py 21 · rows 4-7 (1+1+1+2) = catalog.py 5 · rows 8-9 (5+1) =
agent_jobs.py 6 · rows 10-11 (6+1) = runs.py 7 · row 12 (1) = writeback.py 1
· rows 13-14+30-33 (2+4+3+3+3+1) = admin.py 16 · rows 15-16 (2+1) = audit.py
3 · row 17 (4) = assertions.py 4 · row 18 (1) = auth_identity.py 1.
**21+5+6+7+1+16+3+4+1 = 64.** Matches the independent grep exactly — this is
the reproducible count karen's review required, re-verified against HEAD in
this revision.

## Surface widened post-acceptance (DELTA-AUDIT, 2026-07-22)

Since this document's original acceptance, 10 new endpoints were added to
`admin.py` for service-account and personal-access-token (PAT) management
plus a deployment-mode-status introspection route (ACT-301..303) — see rows
30-33 above for the per-endpoint trace. **Verdict: all 10 stay within the
scope this document already authorizes; none introduces a new risk the
operator must weigh beyond what acceptance already covers.**

- Every one of the 10 either derives its `workspace_id` exclusively from the
  caller's own resolved `identity.workspace_id` (never client-supplied), or
  is a legitimately install-wide read with no per-workspace row to leak
  (deployment-mode-status, row 33 — same category as the pre-existing row
  14 endpoints this document already accepted).
- The one place this surface could plausibly have repeated row 15's
  cross-tenant-leak pattern — `require_role("owner", "admin")` checking ROLE
  membership but not WORKSPACE — does not: every service-account/token
  handler additionally scopes through `_get_service_account_or_404` (rows
  30-31) or an explicit `workspace_id`/`identity.workspace_id` equality
  check (row 32's PAT routes), so an owner/admin in one workspace cannot
  enumerate, read, rotate, or revoke another workspace's service accounts,
  tokens, or PATs. This was verified by code trace AND by 8 new
  `TestCrossWorkspaceIsolation` regression tests
  (`tests/unit/test_admin_tokens_api.py`), not asserted from reading alone.
- Row 23 (the one pre-existing COULD-NOT-VERIFY finding this widened surface
  resolves) flips to CONFINED: the router wiring that finding said to watch
  for now exists, and it wires the three previously-unreachable
  `rbac_store` write functions with the caller's own workspace_id at every
  call site — never the unscoped `workspace_id=None` call the original
  finding warned about.
- No new NEEDS-REMEDIATION or COULD-NOT-VERIFY rows result from this delta.
  The `status: accepted` decision and its `trusted-cohort` scope boundary
  (frontmatter `signoff:`/`authorization_scope`) are unchanged by this
  finding and are NOT reopened by this revision — this section is
  informational reconciliation, not a re-litigation of the original
  sign-off.

## Findings requiring remediation (not fixed this wave — logged per instruction)

Ordered by severity, headline risk first:

1. **Rows 10-12 — runs, claims, source cards, and evidence bundles have no
   `workspace_id` concept in the data model at all** (see "Residual risk —
   headline finding" above for the full description). Row 12
   (`POST /runs/{id}/writeback/approve`) is a cross-tenant **write/action**
   (real writeback dispatch), not merely a read leak — the highest-severity
   single item in this document. This is a data-model decision, not a
   one-line fix, and is the single highest-priority item for a follow-up
   phase before a genuinely adversarial multi-tenant deployment (as opposed
   to a trusted-cohort one, which is what this audit's acceptance would
   authorize).
2. **Row 9 — `POST /agent-jobs` trusts client-supplied `workspace_id`
   verbatim**, including in the audit-trail `actor_workspace_id` (FR-12
   caveat: this remains true even after the adjacent ACT-204 identity-binding
   work lands, since that work protects `created_by`, not `actor_workspace_id`
   — see row 9's note). Multi-call-site fix (create_job, spawn_job, audit
   call, and the four other `TODO(WKSP-304 P4)`-marked calls in the same
   router) — needs its own test plan.
3. **Row 7 — catalog import always stamps `workspace_id="default"`.**
   Documented WKSP-303 design decision; becomes a functional gap (not just a
   leak) once isolation enforces — a multi-tenant caller's own imports
   become invisible to them. Needs a product decision on multi-tenant
   catalog ownership semantics before a fix is written.
4. **Row 4 — `GET /catalog/stats` leaks cross-workspace aggregate counts.**
   Low severity, single-function fix, no existing cross-tenant-count test
   harness. Proposed: thread `identity`, gate the `GROUP BY` query behind
   `_isolation_active`.

## Surfaces flagged as could-not-verify (not assumed covered)

- Rows 10/12 — could-not-verify/needs-remediation in the sense of "verified
  the gap exists and is real," not "assumed fine": explicitly not a clean
  bill of health. See "Residual risk — headline finding" above.
- Row 23 — **RESOLVED (DELTA-AUDIT 2026-07-22).** The three previously
  still-unwired ACT-203 service-account/access-token WRITE functions
  (`create_service_account`, `create_access_token`, `list_service_accounts`)
  are now wired by `admin.py` (rows 30-31) — re-audited per this finding's
  own instruction and confirmed CONFINED, not left as an open
  could-not-verify item. (Row 22, the READ path, was already separately
  confirmed CONFINED — see the row-21 correction above.)
- Row 27 — `swarm_drive.py`'s one `workspace_id=None` reference, not traced
  to a conclusion.

## Conclusion (draft, pending human review)

Of 29 enumerated table rows at original acceptance: 20 CONFINED, 1
REMEDIATED (row 15), 5 NEEDS-REMEDIATION (rows 4, 7, 9, 11, 12), 3
COULD-NOT-VERIFY (rows 10, 23, 27). **DELTA-AUDIT (2026-07-22) update:** 4
new rows (30-33, all CONFINED) were added for the 10 endpoints admin.py
grew by since acceptance, and row 23 flips from COULD-NOT-VERIFY to
CONFINED now that the router wiring it was waiting on exists (see "Surface
widened post-acceptance" above). **Reconciled total: 33 enumerated table
rows: 25 CONFINED (20 original + row 23 + rows 30-33), 1 REMEDIATED (row
15), 5 NEEDS-REMEDIATION (rows 4, 7, 9, 11, 12 — unchanged by this delta),
2 COULD-NOT-VERIFY (rows 10, 27 — row 23 resolved).** 25+1+5+2=33. Endpoint
totals reconcile to the independent grep (**64**, up from 54 at original
acceptance) exactly — see the table above. No recurrence of the two
specifically-named prior leaks (rows 3, 6) was found — both remain
remediated and unregressed. No new leak was found in the widened admin.py
surface — all 10 new endpoints traced CONFINED, backed by 8 new
`TestCrossWorkspaceIsolation` regression tests
(`tests/unit/test_admin_tokens_api.py`).

**This audit does not certify zero remaining gaps** — rows 4, 7, 9, 10-12,
and 23/27 are named, open items, with rows 10-12 (the runs/evidence
data-model gap) explicitly the headline residual risk, not one of several
co-equal bullets. It does certify that every surface was either traced to a
specific, evidenced verdict or explicitly flagged as not traced, and that
its own coverage claim (the endpoint count) reconciles against an
independent, reproducible grep — the exact failure mode this phase exists
to close (per the WKSP-304 AAR) is a claim that does not survive
re-verification; this revision corrects the one place that failure mode
appeared in the first draft.

**Recommendation to the human reviewer:** the `deployment_mode_validate()`
gate (ACT-402) is safe to wire now — it fails closed on this document's
`status` field regardless of the open findings above, so wiring the gate
does not certify anything by itself. Setting `status: accepted` is a
separate decision from wiring the gate, and per Mode D, requires your
explicit judgment call — stated up front in this document's frontmatter and
the opening of the Scope Boundary Statement, not just here — on whether
accepting authorizes a **trusted-cohort** `multi_user` rollout only (given
rows 10-12's runs/evidence data-model gap is NOT covered by acceptance), or
whether that gap should block acceptance until remediated in a follow-up
phase.
