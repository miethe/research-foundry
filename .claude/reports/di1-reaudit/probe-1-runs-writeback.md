---
probe: probe-1-runs-writeback
mode: E (Reviewer, read-only)
head_verified: d71a261d85cf6eb05f12f250c244e7ef253b759e
date: 2026-07-26
scope: runs.py, writeback.py, api/auth/scope.py, services/run_launch.py (+ export_service.py, planning.py, config.py, middleware/auth.py as needed to close the trace)
prior_finding: docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md rows 10-12 (headline residual risk — runs had NO workspace_id at all; any authenticated caller in any workspace could read/act on every run)
claimed_fix: commit 08559a0 (DF-004)
---

# Probe 1 — Runs & Writeback cross-tenant re-audit (adversarial, code-only)

## Headline verdict

**The DF-004 remediation is present in the code at HEAD and closes the exact
gap rows 10-12 named** — `workspace_id` now exists on the run record,
is stamped exclusively server-side from `identity.workspace_id`, and is
checked on every read/write path enumerated below. **However, enforcement is
config-gated** (`workspace_isolation_enforcement`, see Q4 below) — the code
change makes cross-tenant denial *possible*, not *unconditional*. Whether
today's default deployment actually denies ws_b→ws_a access depends on a
flag resolution this probe does not certify (see HARD RULE below and the
per-endpoint notes). All 8 endpoints traced are **CONFINED given enforcement
is truthy**; none has an unconditional bypass independent of that flag.

## Per-endpoint trace

### Row 10 — the 6 read endpoints (`api/routers/runs.py`)

| Endpoint | Line(s) | Verdict | Evidence |
|---|---|---|---|
| `GET /runs` | `runs.py:163-177` | CONFINED | `get_run_list` calls `list_runs(paths, identity=_identity_from_request(request))` (line 177). `export_service.list_runs` (`export_service.py:1394-…`) filters per-run via `_run_read_allowed` (line 1417) — unreadable runs are **silently omitted**, never 404'd (correct for a list endpoint, no existence leak). |
| `GET /runs/{id}` | `runs.py:180-214` | CONFINED | Routes through `_enforce_existence_gate(paths, run_id, threshold, _identity_from_request(request))` (line 212-214) → `export_run(..., identity=identity)` (line 140) → `_run_read_allowed` (`export_service.py:1216`). A denial returns `export_run()==None`, mapped to `404` at `runs.py:146-147` — indistinguishable from a genuinely-missing run (no 403, no existence leak). |
| `GET /runs/{id}/claims` | `runs.py:217-247` | CONFINED | Same `_enforce_existence_gate` call (line 242-244) before returning `data["claims"]`. Same gate, same 404-on-deny. |
| `GET /runs/{id}/context` | `runs.py:250-289` | CONFINED | Same `_enforce_existence_gate` call (line 286-288) before returning `data["context"]`. |
| `GET /runs/{id}/sources/{source_card_id}` | `runs.py:292-329` | CONFINED | Same `_enforce_existence_gate` call (line 320-322) before scanning `data["claims"][*]["sources"]`; a denied run 404s before the source scan ever runs, so no source-card content leaks either. |
| `GET /reports/{id}/anchors` | `runs.py:332-364` | CONFINED | Same `_enforce_existence_gate` call (line 361-363) before returning `report_anchors`. |

All six funnel through the **same single choke point**
(`_enforce_existence_gate` for the five per-run reads, `list_runs` for the
list) which in turn delegates to the shared
`api/auth/scope.py::require_workspace_scope` predicate
(`export_service.py:1164-1186`, `_run_read_allowed`). There is no
alternate/legacy read path in `runs.py` that skips `_identity_from_request` —
every one of the 6 handlers calls it (confirmed by reading the full 590-line
file, not by grep sampling).

**Adversarial answer (ws_b reading a ws_a run):** DENIED (404, indistinguishable
from not-found) **when** (a) the run has a non-public `visibility` AND (b)
`workspace_isolation_enforcement` resolves to enforcing for the deployment.
ALLOWED (with a `workspace_scope_advisory_mismatch` WARNING log, not an ERROR)
when isolation is advisory-only. ALLOWED unconditionally when `visibility ==
"public"` on the run record (`export_service.py:1161-1162`, checked before any
workspace comparison — by design, not a leak: this is the caller's own
choice at launch time, see row 11).

### Row 11 — `POST /runs` (launch) (`api/routers/runs.py:436-569` → `run_launch.py::launch_run` → `services/planning.py::plan_run`)

**Q1 — is `workspace_id` stamped server-side from identity, never
client-supplied?** YES, confirmed end-to-end:

- `runs.py:460` — `identity = _identity_from_request(request)` (from
  `request.state.identity`, set only by the auth middleware — see Q2 below).
- The request body (`LaunchRunRequest`, `runs.py:372-433`) has **no
  `workspace_id` field at all** — a client cannot supply one even if it tried;
  the docstring at `runs.py:398-401` states this explicitly.
- `run_launch.launch_run` forwards `identity` unmodified into `plan_run`
  (`run_launch.py:234-235`) — the module docstring (`run_launch.py:153-159`)
  states it never inspects `identity` beyond that passthrough.
- `planning.py:747` — `effective_workspace_id = workspace_id if identity is
  None else identity.workspace_id`. The `workspace_id` **parameter** (which
  could theoretically be client-influenced) is used **only** when `identity is
  None`; the HTTP router never passes that parameter at all, so on the HTTP
  path `effective_workspace_id` is `identity.workspace_id` whenever an
  identity resolved, full stop.
- `planning.py:984` — `"workspace_id": effective_workspace_id` is what gets
  written into the new run's `run.yaml`.

Verdict: **CONFINED**. There is no code path by which an HTTP caller can stamp
a new run with a `workspace_id` other than their own resolved identity's.

### Row 12 — `POST /runs/{id}/writeback/approve` (`api/routers/writeback.py:342-455`)

**Q1-equivalent for actions — is the target run's ownership checked before
the side effect?** YES:

- `writeback.py:381` — `identity = getattr(request.state, "identity", None)`.
- `writeback.py:395` — `_enforce_run_workspace_scope(run_id, paths, identity)`
  is the **first statement inside the `try` block**, strictly before
  `result = approve_and_dispatch(...)` on the next line (`writeback.py:396`).
  No dispatch call, no external side effect, happens before this gate runs.
- `_enforce_run_workspace_scope` (`writeback.py:278-334`): reads
  `run.workspace_id` via `_run_workspace_id` (best-effort YAML read,
  `writeback.py:258-275`), then calls the same `require_workspace_scope`
  predicate rows 10/11 use (`writeback.py:313-319`). A denial raises
  `NotFoundError` (`writeback.py:334`), caught by the **same branch** as a
  genuinely-missing run (`writeback.py:402-414`) — 404, never 403, and
  crucially: `approve_and_dispatch` (the function that actually talks to
  MeatyWiki/SkillMeat/CCDash) is never reached on that branch.
- Unlike the reads, `_enforce_run_workspace_scope` does **not** have a
  `visibility == "public"` bypass — the module docstring
  (`writeback.py:32-34`) states this explicitly: "Writeback is a mutating
  cross-tenant action, so `public` visibility never grants it — only
  workspace ownership does." Confirmed by reading the function body in full;
  no `visibility` check exists in it.

Verdict: **CONFINED given enforcement is truthy**, same conditionality as rows
10/11. `identity.user_id` (not `workspace_id`) is separately threaded into
`approver_identity` purely for the `approved_by` audit-attribution field
(`writeback.py:386`) — this is the actor-attribution concern the prior audit
noted was already correct; it is orthogonal to the ownership gate.

**Adversarial answer (ws_b dispatching a ws_a run's writeback):** DENIED
(404) when isolation is enforcing. ALLOWED (dispatch proceeds, target systems
receive the writeback) when isolation is advisory-only, identical risk shape
to the reads but with a real external side effect instead of an information
leak — this is the highest-severity of the three original findings and it now
has the *same* enforcement-flag dependency as the reads, not a stronger one.

## The four specific adversarial questions

**Q1 — Is `workspace_id` stamped server-side from identity, never
client-supplied, at launch?** Yes — see row 11 above. No regression found;
no client-suppliable field exists in the request schema, and the identity
passthrough chain (`runs.py` → `run_launch.py` → `planning.py`) never
substitutes a client value once `identity` is non-`None`.

**Q2 — Is `require_workspace_scope` actually invoked on EVERY read/write
path, or do any endpoints skip it?** All 8 endpoints in `runs.py` +
`writeback.py` invoke it (directly or via `_run_read_allowed`'s delegation).
No bypass path was found in either file — both were read in full (590 +
458 lines), not sampled. One structural note worth flagging as **out of this
probe's direct trace scope but adjacent**: `request.state.identity` is only
ever populated by `AuthProviderMiddleware` (`api/middleware/auth.py:217-226`),
which returns a hard 401 (not a silent `identity=None` passthrough) whenever
authentication fails **and the middleware is installed at all**
(`middleware/auth.py:218-221`). `identity=None` at the router level is
therefore reachable only when `auth.provider == "none"` (no middleware
registered — single-operator-trust mode) — not as a way for an authenticated-
but-unverifiable request to slip through with a spoofed/absent identity. This
matters because it means the `identity is None` branch of
`require_workspace_scope` (always-allow) is the deliberate single-operator
design case, not a residual gap in the auth layer — but this probe did not
independently re-verify every provider adapter (`Clerk`, `local_static`,
token-store) for correctness; that is outside this trace's file list.

**Q3 — How are LEGACY / null-`workspace_id` runs handled — fail-closed or
fail-open?** **Conditional on the same enforcement flag, not uniform:**
- `require_workspace_scope` (`api/auth/scope.py:184-206`) treats a `None`/
  absent `record.workspace_id` as a **mismatch**, explicitly never a wildcard
  match (`scope.py:202-206`, "A null workspace_id is treated as a mismatch —
  never defaulted to allowed").
- Under **enforcing** mode: that mismatch → `allowed=False` → fail-closed
  (404/denied) for a legacy run, same as any other cross-workspace mismatch.
- Under **advisory** mode (the default when `auth.provider == "none"`, per
  the `AUTO` truth table in `config.py:802-814`): that mismatch → logged
  (`workspace_scope_advisory_mismatch` WARNING) but `allowed=True` →
  **fail-open**. Every pre-DF-004 run in an existing install (which by
  definition has no `workspace_id` in its `run.yaml`) is a "legacy null" run
  by this definition, so **the entire pre-existing run corpus stays
  universally readable/dispatchable under advisory mode**, exactly as it was
  before this fix, until/unless enforcement is turned on for that
  deployment's resolved provider.

**Q4 — Does enforcement depend on a config flag? Name it.** Yes:
`workspace_isolation_enforcement` (top-level key in `foundry.yaml`, sibling of
`auth:` — not nested under it; `config.py:744-785`, enum
`WorkspaceIsolationEnforcement` with values `auto` / `disabled` / `enabled`).
It is combined with `auth.provider` and `viewer.bind_host` inside
`FoundryConfig.resolve_workspace_isolation_enforced(provider, bind_host)`
(`config.py:787-…`), whose result is captured **once** at app-create time onto
`app.state.workspace_isolation_enforced` and read per-request via
`api/auth/scope.py::resolve_workspace_isolation_active`. **This probe does not
determine or assert what that flag resolves to in any given deployment** —
per the task's own instruction, that determination belongs to a different
probe. What this probe confirms is only the *dependency itself*: every one of
the 8 endpoints traced is enforcing-mode-conditional, not unconditionally
safe.

## Residual risk / things NOT closed by this fix (flagging, not fixing)

1. **Advisory-mode fail-open is total, not partial.** Under advisory mode
   (the `provider="none"` default), the fix changes *logging* (a new
   structured WARNING per mismatch) but changes **zero** access-control
   outcomes relative to pre-08559a0 behavior — every read and the writeback
   dispatch remain universally cross-tenant-readable/actionable. The fix's
   real security value is entirely gated on a deployment's
   `workspace_isolation_enforcement` + `auth.provider` combination landing in
   the enforcing branch of the truth table — that combination is exactly what
   another probe in this re-audit is tasked with determining, and this probe
   explicitly does not certify it.
2. **RBAC role scoping on the two mutation routes (`POST /runs`,
   `POST /runs/.../writeback/approve`) was not independently re-verified in
   this probe** — both are gated by `Depends(require_role("owner", "admin"))`
   (`runs.py:60`, `writeback.py:96`), and the prior audit's row 13 established
   that roles are workspace-scoped, but `api/auth/rbac.py::require_role`
   itself is outside this probe's file list; a ws_b "admin" role could only
   matter here if it also carried ws_a authority, which is a different
   surface (RBAC-006-adjacent) than the workspace-ownership gate traced above.
3. **`run_id` path construction is not sanitized in this trace's call
   path** (`paths.py::run_paths` → `run_dir(run_id)`, not independently
   walked to a validator in this probe) — a separate, orthogonal concern from
   workspace isolation (path traversal / injection), out of this probe's
   adversarial question but worth another probe's attention if not already
   covered elsewhere in this re-audit.
4. **No live HTTP requests were made.** This is a 100% static/code-reading
   verification, consistent with the Mode E read-only constraint. It cannot
   and does not certify runtime behavior — only what the code, as written at
   `d71a261`, does given a described input.

## Summary (5 lines)

1. DF-004 (commit 08559a0's remediation) is real and present at HEAD: `runs.py`'s 6 reads, `POST /runs` launch, and `POST /runs/{id}/writeback/approve` all now thread a server-stamped `identity.workspace_id` through a single shared predicate (`require_workspace_scope`), closing rows 10-12's original "no workspace_id concept at all" gap.
2. Launch-time stamping (row 11) is unconditionally safe: no client-suppliable `workspace_id` field exists anywhere in the request chain to the write.
3. Every read (row 10) and the writeback dispatch (row 12) resolve to an indistinguishable 404 on an enforced cross-workspace mismatch, with no `visibility`-bypass on the writeback action specifically (reads do have a deliberate `public`-visibility bypass, by design).
4. All of this protection is conditional on `workspace_isolation_enforcement` (+ `auth.provider`) resolving to "enforcing" — under advisory mode (the `provider="none"` default), a legacy/null-`workspace_id` run and any cross-workspace mismatch are still allowed through (fail-open, now logged instead of silent).
5. Verdict per endpoint: **CONFINED given enforcement is truthy** for all 8 traced endpoints — this is a code-behavior finding only, not a certification of adversarial multi-tenant safety in any specific deployment; that certification requires knowing the resolved flag state, reserved for a human Mode-D gate per the task's HARD RULE.
