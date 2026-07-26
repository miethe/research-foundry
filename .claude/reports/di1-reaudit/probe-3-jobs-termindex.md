---
title: DI-1 Re-Audit Probe 3 — Agent-Jobs (row 9 follow-up) + Claim Term-Index (new surface)
mode: E — Reviewer (read-only)
audited_commit: d71a261
scope: >
  Two targets: (A) prior-audit row 9 (agent-jobs client-supplied workspace_id,
  spoofable FR-12 attribution) as it stands after the DF-004 fix; (B) the new
  claim term-index surface (services/term_index.py, term_index_backfill.py)
  for cross-workspace claim-content leak risk.
---

# Probe 3 — Agent-Jobs + Claim Term-Index

## A. AGENT-JOBS (prior audit row 9 follow-up)

**Verdict: CONFINED** — conditioned on `auth.provider != "none"` (isolation
actively enforced). **Advisory-only by documented design** when
`auth.provider == "none"` (the shipped default, single-operator-trust LAN
mode) — not a code defect, but the precondition a human accepting
multi-tenant trust must verify is actually configured.

### What changed since the prior audit

Prior finding (`docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md`
row 9): `workspace_id=body.workspace_id` was taken verbatim from the client
body in both the persisted job record and the `agent_job_launched` audit
event's `actor_workspace_id` — `identity` was fetched but never used
(`# noqa: F841`).

DF-004 closed this. Evidence:

- `src/research_foundry/api/routers/agent_jobs.py:172-174` — the router
  computes `effective_workspace_id = body.workspace_id if identity is None
  else identity.workspace_id` and uses it for the **audit event's**
  `actor_workspace_id` (line 268), not the raw body value.
- `src/research_foundry/api/routers/agent_jobs.py:212-226` — `create_job(...)`
  is still called with `workspace_id=body.workspace_id` (the raw client
  value) *and* `identity=identity`. This looked like the exact bug the task
  brief suspected — **but it is not**, because:
- `src/research_foundry/services/agent_job_service.py:865` —
  `AgentJobService.create_job` internally recomputes
  `effective_workspace_id = workspace_id if identity is None else
  identity.workspace_id` and stamps **that** onto the persisted `AgentJob`
  (line 872: `workspace_id=effective_workspace_id`). The client-supplied
  `workspace_id` parameter is only ever used as the identity-less fallback.

So: **the job record's own `workspace_id` is stamped from the trusted
identity** (not the spoofable client body) whenever an identity is present.
**The audit-trail `actor_workspace_id` is independently computed via the
same formula** in both the router (for the always-fired outer audit call)
and inside `create_job` (for the FR-12 service-account audit call) — so the
two attribution channels the prior audit called out as divergent
(`created_by` protected, `actor_workspace_id` not) are now both protected,
and by the *same* formula, so they cannot diverge from each other either.

Read-side enforcement: `AgentJobService.load_job` (agent_job_service.py:929-1011)
threads `identity` through `require_workspace_scope()`
(`api/auth/scope.py:113`), which — when `resolve_enforcement()` (the
`_isolation_active` flag, agent_job_service.py:301-320,
`api/auth/scope.py:56-78`) resolves `True` — denies a `workspace_id`
mismatch by raising `KeyError`, which the router's `_load_job_or_404`
(agent_jobs.py:88-103) maps to the same opaque 404 used for a genuinely
missing job. `GET /agent-jobs/{id}`, `POST /agent-jobs/{id}/cancel`, and
`POST /agent-jobs/{id}/accept` all call `_load_job_or_404` **before** any
mutation, so a cross-workspace caller under enforced isolation never reaches
`terminate_job`/`cleanup_job`/`accept_job`/`list_staged_artifacts` at all.

There is **no bulk-list endpoint** for agent jobs (`AgentJobService` has no
`list_jobs` method — confirmed both by source grep and by
`tests/test_workspace_isolation_enforcement.py::TestTargetMethodMismatchFindings::test_agent_job_service_has_no_list_jobs_method`),
so the "list" half of the adversarial question is moot — there is nothing to
enumerate.

### Adversarial outcome (ws_b vs ws_a)

- **Create**: ws_b cannot create a job attributed to or stamped as ws_a —
  `create_job` overrides any client-supplied `workspace_id` with
  `identity.workspace_id` whenever an identity exists. Verified by
  `tests/unit/test_agent_jobs_workspace_stamp.py` (both unit- and
  router-level), all passing at HEAD (ran locally, 4/4 pass).
- **Read/cancel/accept**: ws_b querying/cancelling/accepting a job owned by
  ws_a gets an opaque 404 **when isolation is enforced**
  (`auth.provider != "none"`, the `AUTO` default per
  `config.py:787-827`). Verified by
  `tests/test_workspace_isolation_enforcement.py::TestAgentJobRouterMatrix`
  and the `test_cancel_job_cross_workspace_never_calls_terminate_or_cleanup`
  / `test_accept_job_cross_workspace_never_calls_accept_job` tests — all
  passing at HEAD (ran locally, 8/8 in the AgentJob-scoped subset).
- **Under `identity=None` (no-auth, the shipped default)**: `workspace_id`
  is fully client-controlled on create, and read/cancel/accept perform no
  workspace check at all (`require_workspace_scope`'s D3 short-circuit
  returns "allowed" before `resolve_enforcement` is ever read — this is
  documented, deliberate, and consistent with the identical `AUTO` pattern
  already used for RBAC). This is **not** a code gap: with no auth
  provider configured there is no second identity to spoof against in the
  first place — every caller on the LAN is already the same unauthenticated
  principal. It **is** the load-bearing precondition: a human treating this
  install as multi-tenant-isolated MUST first confirm `auth.provider` is
  actually set to something other than `"none"` in `foundry.yaml`. Code
  reading alone cannot certify that a given live deployment has done so —
  reserved for the Mode-D human gate per the hard rule.

## B. CLAIM TERM-INDEX (new surface)

### B.1 — Per-run or global?

**Verdict: CONFINED (per-run/per-claim; no cross-run global store).**

`_term_index` is not a persistent index of its own — `build_term_index()`
(`services/term_index.py:332`) is a pure, stateless function that computes a
block from one claim's text + a shared read-only vocabulary file, and the
result is written **inline onto that claim** inside that run's own
`claims/claim_ledger.yaml` (`services/claim_mapping.py:276-284`, write-time
path). There is no separate on-disk or in-memory term→claim lookup table
outside of what SQLite `catalog_terms` derives at import time.

`catalog_terms` (the only persisted, cross-item structure derived from
`_term_index`) is populated per-run at `catalog_service.import_run()`
(`catalog_service.py:1164` deletes `WHERE run_id = ?` before re-insert;
`catalog_service.py:1208-1213` inserts rows carrying `run_id` +
`sensitivity_rank` but explicitly **no `workspace_id` column of its own**
(`catalog_service.py:218-230`, schema). Workspace scoping is achieved by
joining back to `catalog_items.workspace_id`
(`catalog_service.py:1584-1596`, `_facets()`; `catalog_service.py:1419-1436`,
the `term`/`role` `EXISTS` predicates in `search()`) — the same join-based
pattern already used elsewhere in this file for `workspace_id`-less derived
tables.

### B.2 — Read/search endpoint over the term index; is it workspace-scoped?

**Verdict: CONFINED under the same conditions as A** (isolation enforced +
identity present); **no dedicated term-index route exists** — the only
surface is the generic catalog search, reused.

- `grep -rn "term_index\|_term_index" src/research_foundry --include="*.py"`
  turns up **zero** API router hits — there is no dedicated
  `/term-index`/`/index`/`/search-terms` endpoint.
- The actual read surface is `GET /api/catalog/search?term=...&role=...`
  (`api/routers/catalog.py:71-113`), which passes `term`/`role` straight
  through to `catalog_service.search()` (`catalog_service.py:1356-1436`).
  The router **does** thread `identity = request.state.identity` into this
  call (`catalog.py:104-113`).
- Inside `search()`, `workspace_scoped = identity is not None and
  _isolation_active(paths)` (`catalog_service.py:1397`) gates a
  `workspace_id = ?` predicate applied to `catalog_items`, and the
  `term`/`role` `EXISTS (... FROM catalog_terms ...)` sub-clauses additionally
  re-check `sensitivity_rank <= threshold_rank` per row
  (`catalog_service.py:1419-1436`). The `_facets()` term/role rollup
  (surfaced in every search response so the UI's filter dropdowns populate)
  is explicitly documented and coded to apply the *same* workspace join
  (`catalog_service.py:1474-1484`, `1580-1620`) — the code comment names the
  exact risk this probe was asked to check: *"a term/role row above the
  caller's threshold can never be used to match an item... closing the same
  flat-blob leak class `_redact_evidence_points` guards against"* and *"a
  term belonging to another workspace's item silently crosses [the
  boundary]"* is the docstring of the regression test guarding this.
- Verified: `tests/unit/test_catalog_terms.py::test_facets_terms_workspace_isolation_excludes_other_workspace_term`
  seeds a term row under `ws-other`, searches as `ws-mine`, and asserts the
  other workspace's term is absent from the facet rollup. Ran locally at
  HEAD: **19/19 tests pass** in this file, including this one.
- Same caveat as A: this scoping is gated by `identity is not None and
  _isolation_active(paths)` — under the shipped `auth.provider="none"`
  default, `workspace_scoped` is `False` and the term/role facets/filters
  are unscoped across the whole (single-tenant-trust) install, exactly like
  every other catalog query. Not a term-index-specific gap — it inherits
  catalog_service's pre-existing, already-audited scoping mechanism
  verbatim; term-index introduces no new bypass of it.

### B.3 — Does backfill read across all runs regardless of workspace?

**Verdict: NEEDS-REMEDIATION is the wrong frame here — this is a local,
unauthenticated CLI/filesystem tool, not an API surface, and the DI-1 threat
model (adversarial callers sharing one deployed multi-tenant instance) does
not apply to it. Flagging as: BY-DESIGN, OUT-OF-DI-1-SCOPE, but worth a
human note.**

- `rf term-index backfill` (`cli_commands.py:2917-2971`) with no `--run`
  filter defaults to
  `ledger_paths = sorted(fp.runs.glob("*/claims/claim_ledger.yaml"))`
  (`cli_commands.py:2953`) — **every** run's claim ledger on disk, with zero
  workspace filtering, zero identity, zero auth check of any kind.
  `backfill_term_index()` itself (`services/term_index_backfill.py:79-182`)
  takes a flat `ledger_paths: Iterable[Path | str]` and has no
  workspace-aware parameter at all.
- This is architecturally identical to `catalog_service.rebuild()` /
  `import_all()` (`catalog_service.py:1283-1301`), which also unconditionally
  re-imports every run on disk — this is the established, pre-existing
  pattern for every full-tree CLI maintenance command in this codebase, not
  something term-index introduced. Whoever can invoke this CLI already has
  direct filesystem read access to every run's `claim_ledger.yaml` — the
  command adds no new read capability beyond what `cat runs/*/claims/claim_ledger.yaml`
  already grants that same local operator.
- **This is not equivalent to** an unauthenticated network caller reading
  another tenant's claims through the API — there is no network path here.
  If this repo/data directory is ever mounted into a context where the `rf`
  CLI itself is exposed multi-tenant (e.g., a shared shell, a CI job running
  on behalf of multiple tenants), that is a filesystem/deployment isolation
  question, not a code-level DI-1 gap in this module.

## Summary (5 lines)

1. Agent-jobs (row 9): DF-004 fixed it — job `workspace_id` and audit
   `actor_workspace_id` are both stamped from `identity`, not the client
   body, whenever an identity exists; enforced-mode cross-workspace get
   /cancel/accept all 404 before touching the job. Verified by passing
   tests at HEAD.
2. No bulk agent-job list endpoint exists, so there is no read-enumeration
   surface to worry about beyond single-job lookup by (unguessable) id.
3. Term-index is per-run/per-claim, not a global index; its only derived
   store (`catalog_terms`) is workspace-scoped via a join back to
   `catalog_items`, verified by a passing dedicated regression test.
4. No dedicated term-index API route exists; the only read surface is the
   pre-existing, already-scoped `/catalog/search` term/role facets.
5. Both A and B's isolation is **config-conditioned**
   (`auth.provider != "none"` → enforcing): CODE-VERIFIED-CORRECT-UNDER-THAT-CONFIG,
   not adversarially-safe-by-default under the shipped no-auth default —
   per the hard rule, certifying the latter for a live install is a
   human Mode-D judgment, not something this read-only pass can grant.
