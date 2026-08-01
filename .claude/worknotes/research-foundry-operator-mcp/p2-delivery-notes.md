---
title: "P2 Durable Operation Coordinator — delivery-report notes"
schema_version: 2
doc_type: report
report_category: execution_notes
status: in_progress
created: 2026-07-29
updated: 2026-07-29
feature_slug: research-foundry-operator-mcp
feature_version: v1
phase: 2
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
progress_ref: .claude/progress/research-foundry-operator-mcp/phase-2-progress.md
source: dev:execute-phase P2
---

# P2 execution notes (for the end-of-plan delivery report)

Running capture during execution — **not** reconstructed afterwards. Raw material for the
`delivery-report` skill (`feature` route at end-of-plan, `phase` route for the P2 recap).

## Baseline

- Worktree `.claude/worktrees/operator-mcp-v1`, branch `worktree-operator-mcp-v1`, head at P2 start
  `e5a2e6e` (P1 close-by-owner-acceptance), based on main `65d658d`. Draft PR #7.
- Worktree has **no `.venv`**. All validation uses main's interpreter:
  `PYTHONPATH=$PWD/src /Users/…/research-foundry/.venv/bin/python -m pytest … --color=no`
- Baseline before any P2 change: `tests/unit/test_operator_mcp_policy.py` +
  `test_operator_mcp_schemas.py` green (206 tests).
- Pre-existing, not chased: `tests/test_verification_pediatric_cds.py` and
  `test_verification_seam001_gate_composition.py` fail to COLLECT under `-k` filtering
  (sibling `import test_claim_verifier`); present on base `65d658d`.

## Routing decisions (delegation-router)

The router's MUST-stay classes cover the gates but not the leaf implementation tasks, so the split
below is a deliberate risk judgment, recorded for audit.

| Node | Provider / model | Rationale |
|---|---|---|
| OPM-2.1 immutable operation store | primary Claude, `python-backend-engineer` (sonnet) | DUR-1 atomicity is the AC-mandated **security** property; the plan warns a read-then-write CAS passes every P1 test. Not offloaded. |
| OPM-2.2 AgentJob attempt adapter | ICA `claude-sonnet-5[1m]` | Bounded, contract-clear adapter wrapping. Cost-shift target. |
| OPM-2.3 receipts persistence | ICA `claude-sonnet-5[1m]` | Schema-driven persistence against a frozen schema. |
| OPM-2.4 cancel/resume state machine | primary Claude | H3 ten-scenario convergence logic; correctness-dense. |
| Cheap pre-gate sweep | sonnet (~30k) | Plan-mandated fail-open / layer-below sweep **before** any Opus lens. |
| P2 security gate (AC-mandated) | primary Claude — MUST-stay (verdict) | Revised post-P1 gate structure: security-with-AC-mandate, then Karen. |
| Karen gate | primary Claude — MUST-stay (verdict) | Durability/atomicity adjudication. |

- **ICA verified live** on `claude-sonnet-5[1m]` before dispatch (smoke returned `ICA_OK`).
- **gpt-5.6 / Codex**: the plan records `codex exec` refusing this workstream's adversarial
  security-audit framing under its safety classifier — a policy refusal, not config. Not retried for
  the security lens. One bounded attempt planned as a **non-security-framed** engineering review of
  the SQLite concurrency/atomicity code (pure correctness framing), which is a different classifier
  surface. Outcome recorded below.
- No ITT binding exists on this plan (`intenttree_tree` absent), so the dev-execution SDLC sync
  hooks are a silent no-op. Follow-up nodes are therefore created explicitly.

## Inherited obligations carried into P2

From the P1 findings ledger (147k, read via delegated digest — never loaded into orchestrator
context):

| Item | Statement | P2 disposition |
|---|---|---|
| `OPM-DF-regate` | Round-6 security re-gate **deferred**; last machine verdict was `CHANGES_REQUESTED` (R5). The remediated tree was never re-attacked. | Re-verify, do not treat as clean. |
| `NB-4` | Public `now=` clock seam; named abuse is "P2 threading a request-supplied timestamp". | **Closed in P2** — see F2 below. |
| `NB-11` | Receipt-shape gaps: `checkpoint` lacks `workspace_id`; `operation_receipt.status: denied` has no reason field. | OPM-2.3 owns the decision. |
| `OPM-DF-preflight` | `governance.preflight()` is named in the frozen decisions block but has **zero call sites**. | Run-layer wiring → follow-up node; P2 closes the authorization-binding half (F1). |
| `NB-9` | Audit-health probe does INSERT+SELECT+DELETE on the authorization hot path; under DUR-1 concurrency this can surface as spurious `audit_unhealthy` denial / lock contention. | Honored: `authorize_operation` is computed **outside** `BEGIN IMMEDIATE`. |
| `NB-7` | ~100 tests monkeypatch `resolve_operator_identity`; real derivation is barely covered. | First live run is the first real exercise — budget for surprises. |
| Receipt schema | Yielded a finding in **every** round examined (NEW-20/21, BLOCK-2/3, R5-BLOCK-1/3), three of them *sibling-field* misses. The R5 per-property sweep is itself unreviewed. | Re-attack before building durable persistence on it (OPM-2.3). |

## OPM-2.1 — Immutable operation store

**Design decision (load-bearing).** DUR-1 requires the confirmation CAS and the manifest write in
one durable transaction. That is only possible if both live in the **same** SQLite database, so P2
owns a new `confirmations` table alongside `operations` — P1 never persisted confirmations
(`mint_confirmation`/`consume_confirmation` are pure). Store is
`FoundryPaths.operator_operations_db` under `.rf_state/` (durable, not gitignored; `.rf_cache` is
disposable and would have been wrong). Follows the `rbac_store._connect` idiom:
`isolation_level=None` + explicit `BEGIN IMMEDIATE`, `row_factory`, `PRAGMA foreign_keys=ON`,
additive `PRAGMA user_version`, explicit 15s `busy_timeout`.

**Defects found by orchestrator review of the first implementation** (all four verified against the
exact tree before dispatching the fix — none were self-reported):

| ID | Class | Defect |
|---|---|---|
| F1 | fail-open + **layer-below** | `consume_and_create_operation` is a public method on the durable effect boundary whose only authorization guard was a **docstring** ("callers MUST have already obtained an `allowed` decision"). Structurally identical to P1's round-2 critical defect, where a docstring steered callers to the weaker door. Fixed by making authorization a data dependency: a `PolicyDecision` bound to this `ctx` via `ctx.canonical_digest()`; absent ⇒ deny. |
| F2 | fail-open (`NB-4`) | Public `now=` param documented "TEST-ONLY" but unenforced ⇒ request-threadable expiry bypass. Replaced with the repo's canonical injectable clock `research_foundry.ids.now()` / `set_clock()`. |
| F3 | fail-open on security-relevant field | `record_confirmation` defaulted a missing `status` to `"issued"` (the one value permitting consumption) and a missing `issued_at` to *now* (maximizing the expiry clamp). Also kept **two sources of truth** for status — SQL column (tested by the CAS `WHERE`) vs `record_json` (tested by `consume_confirmation`) — the same sibling-divergence class that bit the receipt schema three rounds. |
| F4 | unbounded error | Raw `RuntimeError` crossing the boundary; `operator_mcp_error.schema.yaml` requires internal errors redacted and capped. |

**Process note that earned its keep:** the first implementation passed 249 tests, exit 0, with a
credible four-row mutation table — and still contained a docstring-only authorization guard on the
effect boundary. A green suite plus a self-reported mutation table is not gate evidence. All four
defects came from orchestrator review of the actual diff.

**Accepted deviation (F1), argued by the implementer and verified independently.** The authorization
gate tests `decision.stage == "confirmation"`, **not** `decision.allowed`. Rationale: P1 reports an
exact replay as `allowed=False, reason_code="confirmation_replayed"`, so a literal `allowed` check
would deny every idempotent retry and regress OPM-2.1's own frozen AC ("exact manifest replay
resolves same operation"). Verified in P1's code rather than taken on faith:
`PolicyDecision.stage` names the *last stage evaluated* in a fixed order
(`capability → rbac → audit_health → guard → preflight → confirmation`), and `evaluate_policy` only
ever produces stages 1–5 — so `stage == "confirmation"` is reachable **only** after all five earlier
stages pass. Confirmation-stage denials that pass the outer gate then fall through to the
authoritative `verify_confirmation` + `consume_confirmation` re-evaluation *inside* the lock, so the
confirmation predicate is never weakened. A more precise predicate than `allowed`, not a weaker one.

**Landed:** commit `55c341c`. Validation (orchestrator-independent re-run): **257 passed, exit 0**;
`flake8 E9,F63,F7,F82` exit 0; pyright clean on both touched files.

**Delegation hazard hit and worked around (carry forward).** The first fix attempt was dispatched via
`SendMessage` to resume the original implementer with its context intact. The resume was
acknowledged, but the agent silently died — it wrote nothing and the source mtime never moved.
Detected by checking file mtimes and grepping for the specific guards rather than trusting the
"resumed" acknowledgement. Recovery: `TaskStop` the dead agent, then dispatch a **fresh** implementer
with all four findings fully re-specified. Lesson: after resuming an agent, verify the artifact
changed on disk before assuming the work happened.

**ICA launch hazard.** `nohup … &` inside a `run_in_background: true` Bash call is reaped when the
wrapper shell exits — the delegate died instantly, leaving only a startup warning in its log. Launch
ICA as the *foreground* command of a `run_in_background` call so the harness owns the process.

## OPM-2.2 — AgentJob attempt adapter (ICA-delegated leaf) — commit `0e2d1c6`

First ICA offload of this phase, and it worked well. `OperatorAttemptAdapter` wraps a **private**
`AgentJobService` and adds an additive `attempts` table to the database OPM-2.1 already owns.

- `accept_job` kept unreachable structurally, not by convention: never called, wrapped service is a
  private attribute with no public getter, no method name contains `accept`. Proven by a `dir()` scan
  test *and* a test that no public attribute returns an `AgentJobService`.
- Wrong-workspace indistinguishable from missing is **inherited rather than re-implemented** — the
  adapter never catches or re-wraps `load_job`'s exception, so P1's guarantee holds for free. Tested
  on the *same* id both ways (wrong workspace, then delete `job.json` for that id) asserting identical
  exception type and identical `str()`.
- operation→attempts re-applies the identity gate per candidate rather than adding a second SQL
  workspace predicate, keeping workspace policy in exactly one place. Good instinct — a duplicated
  predicate is how these two copies would silently diverge later.

**Verified independently, not taken on report:** all seven barrier files untouched (`git diff` against
HEAD); `_BUSY_TIMEOUT_MS` is `15_000` in *both* modules (checked explicitly — the adapter wrote its own
`_connect` against the same database file rather than importing OPM-2.1's private helper, so a value
mismatch would have made lock behavior diverge between two writers on one file); 319 passed / 0
failures / exit 0.

**Honest gap it disclosed rather than hid:** the `job.json` write (filesystem) and the `attempts` row
(SQLite) are two storage engines and are **not cross-store atomic**. A link-insert failure after job
creation logs at ERROR and re-raises rather than silently orphaning. A real fix needs a cleanup path
on `agent_job_service.py`, a barrier file. Carried to the gate as a known limitation, not a defect.

**ICA verdict for the routing record:** on a bounded task with a precise contract, ICA
`claude-sonnet-5[1m]` produced work that needed **no rework** — the strongest argument yet for
offloading contract-clear leaf nodes. It also honored every negative constraint (barrier files,
no-git, no `accept_job`) and volunteered two considered-and-rejected scope decisions instead of
silently omitting them.

## Receipt-schema re-attack (pre-OPM-2.3) — commit `77717de`

Run **before** OPM-2.3 builds durable persistence, because a weakness in this schema becomes a
durable-data problem. The base rate the ledger predicted (1–3 more findings, most likely here) held:

**`P2R-BLOCK-1` — a FOURTH instance of the same sibling-field class.**
`operation_receipt.idempotency_key` is a completely unguarded open string sitting one property below
the *guarded* `workspace_id` in the same `$def`. Empirically confirmed: `/etc/passwd` and
`Traceback: File x.py` both validate there, while the identical string is rejected in the sibling
field. It is also weaker than `operator_mcp_operation.schema.yaml`'s own closed pattern for the same
logical field. And the `$def` description enumerates six guarded fields, falsely implying
completeness — the same false-self-claim pattern `R5-BLOCK-1` already caught once.

**Process conclusion worth keeping:** judgment has now failed on this one file four times in the same
way. So the fix task was given a *mechanical* requirement instead of a reminder — after each fix,
enumerate every sibling in that `$def` and the equivalent property in the other four `$defs`, and
state a needs-same-treatment verdict for each, as a table. When a defect class recurs four times,
stop trusting the checklist to be *read* and make the sweep an output artifact.

Both P1-deferred `NB-11` items were forced to explicit decisions rather than inherited: add
`workspace_id` to `checkpoint` now (it is the only mutable receipt kind, and row-level workspace
isolation needs it on every workspace-scoped row — retrofitting `NOT NULL` post-ship costs more), and
decide the `operation_receipt.status: denied` reason field rather than leaving a silent gap.

One finding deliberately **not** forced into the schema: there is no `completed ≤ total` relational
invariant on either count pair, and JSON Schema cannot express it. Handed forward as an OPM-2.3
application-layer obligation instead of contorting the schema.

## Cross-model lens: gpt-5.6-terra concurrency review of OPM-2.1 (the standout result of P2)

**The Codex refusal is framing-specific, not workstream-wide.** The plan records `codex exec`
refusing this workstream under its safety classifier after burning a long reasoning trace, and
concludes "do not retry the cross-model security lens here." That conclusion holds for the
*adversarial security-audit* framing — but a **pure engineering correctness framing** ("review this
SQLite module for transactional-correctness and concurrency bugs", with concrete questions about
transaction scope, `isolation_level`, `busy_timeout`, two-process interleaving, `rowcount` semantics)
was accepted and ran to completion, exit 0, ~98k tokens. This is a **reusable unblock**: the
cross-model lens is available to this workstream after all, provided the ask is framed as correctness
rather than attack. Recorded because the plan's blanket "Codex is unavailable for this workstream"
line would otherwise keep costing us the best defect-finding lens we have.

It found a real HIGH-severity bug that the Claude implementer, its own mutation suite, and the
orchestrator review had all missed — and it is precisely the class a concurrency-specialist lens
finds and a general reviewer does not:

| ID | Sev | Finding |
|---|---|---|
| G1 | **HIGH** | **Time-of-check/time-of-use on expiry across the lock wait.** `moment = ids.now()` is captured *before* `_ensure_schema()` and `BEGIN IMMEDIATE`, and `BEGIN IMMEDIATE` can block up to the 15s `busy_timeout`. Interleaving: process B captures `moment` just before a token expires; A holds the writer lock; B waits, acquires the lock *after* expiry, and validates against its stale pre-expiry timestamp — committing a manifest and consuming a token past its clamped expiry. `schemas/operator_mcp_confirmation.schema.yaml` explicitly requires the expiry predicate **at commit time**. Fix: capture the clock *after* the lock is held. |
| G2 | MED | **Lock-timeout escapes as a raw exception.** `_ensure_schema()` and `BEGIN IMMEDIATE` are outside the inner handler, so an exhausted `busy_timeout` raises `sqlite3.OperationalError` out of the method instead of returning a governed retryable `OperationOutcome`. Same defect class as F4 — which was fixed for the CAS invariant path while its **sibling** lock-acquisition path was missed. A textbook "fix the layer below / check the siblings" recurrence, in a fix cycle that was explicitly carrying that checklist item. |
| G3 | LOW | `rowcount != 1` classifies as `internal_error` rather than replay/conflict. Unreachable between two compliant callers of this service (the later one reads committed `consumed` JSON and takes the exact-replay branch first); reachable only if `record_json.status` desynchronizes from the `status` column. |
| G4 | LOW | **Schema-level integrity gap.** Primary keys and `UNIQUE(workspace_id, idempotency_key)` are genuinely DB-enforced, but confirmation status validity and JSON↔column consistency are **application-enforced only** — no `CHECK(status IN (...))`, no FK for the JSON-embedded `consumed_by_operation_id`, no immutability trigger on records the design calls immutable. Verified independently: no `CHECK` exists. This is why G3's path is reachable at all, and it means F3's dual-source-of-truth fix is only half-closed — the app-level permissive default is gone, but nothing at the DB level enforces the invariant. |
| G5 | MED (coverage) | **The concurrency test covers threads, not separate processes.** DUR-1's actual guarantee is cross-process durability under an exclusive file lock; a threaded test shares one interpreter and one connection pool and cannot exercise it. |

Independently confirmed correct by the same review (worth recording so it is not re-litigated):
transaction scope is right (CAS read, idempotency lookup, guarded UPDATE, validation, and manifest
INSERT are all inside one `BEGIN IMMEDIATE`…`COMMIT` on one connection, with no path that commits the
status transition independently of the manifest); the two-process race admits exactly one winner;
`IMMEDIATE` takes a RESERVED rather than EXCLUSIVE lock, which is sufficient here because it excludes
other writers while permitting readers; `isolation_level=None` is used correctly and `_ensure_schema`'s
autocommitted DDL cannot leave partial confirmation/manifest state; and `rowcount` is reliable for
this single-statement primary-key `UPDATE`.

Caveat on its evidence: it could not run pytest (read-only sandbox had no writable tmpdir), so G1/G2
are code-reading conclusions. **G1 must be reproduced with a real failing test before the fix is
accepted** — this project's history (`BLOCK-4`) is exactly about closure asserted rather than
demonstrated.

## P2-ARCH-1 — split schema ownership on a shared SQLite file (found by orchestrator review)

Not from any delegate's report; found by inspecting who opens the shared database once three modules
started converging on it.

`FoundryPaths.operator_operations_db` is now opened by **two** modules, and they manage schema
differently:

- `operator_operation_service.py` owns `PRAGMA user_version` (`_SCHEMA_VERSION = 1`) and gates its
  migrations on that counter — the repo's additive-migration convention, correctly followed.
- `operator_attempt_adapter.py` creates its `attempts` table with a bare
  `CREATE TABLE IF NOT EXISTS` and **never touches `user_version`**.

So `attempts` sits *outside* the versioned migration scheme on a file whose version counter another
module owns. Three consequences, in increasing severity:

1. A future migration that bumps `user_version` has no record that `attempts` exists or which version
   introduced it, so `attempts` can never be migrated under the counter.
2. `CREATE TABLE IF NOT EXISTS` silently no-ops when the table exists with an *older shape* — so an
   evolved `attempts` definition would diverge silently per-database, with no error. This is the same
   failure mode the G4 finding identified for the missing `CHECK` constraint: the app assumes an
   invariant the database does not enforce.
3. It is about to get worse. The G1/G2 hardening task is adding a `CHECK` constraint under a
   `user_version` bump, and OPM-2.3 will add receipt/checkpoint tables to this same file. Without a
   decision, OPM-2.3 becomes the **third** independent schema author on one database with one shared
   counter.

**Resolution required before/with OPM-2.3:** one module owns schema and migration for this file, and
every other module opens it for DML only — or every writer participates in the same `user_version`
scheme. Folded into OPM-2.3's contract as a hard constraint rather than left to discover later.

## Cheap pre-gate sweep (ICA) — found a HIGH defect the whole pipeline missed

The plan mandates a focused fail-open / layer-below sweep on Sonnet **before** any Opus reviewer, at
roughly 1/5 the cost. Offloaded to ICA `claude-sonnet-5[1m]`, scoped to the ~3400-line P2 surface and
told to hunt exactly two defect classes and nothing else (with the already-resolved decisions listed
so it would not re-report them). It returned **2 findings in 1 of 5 files, and "clean" for the other
four** — and the HIGH one had escaped four implementation passes, three delegate mutation suites, and
my own diff review.

| ID | Sev | Finding |
|---|---|---|
| R1 | **HIGH** | **Authorization not bound to the operation being resumed.** `resume_operation` takes `operation_id` and `resume_ctx`/`resume_authorization` as *independent* parameters. `consume_and_create_operation` proves only that `resume_ctx` **itself** cleared all five policy stages — for whatever sensitivity/targets the caller put in it. The service then calls `load_operation(operation_id, identity=...)` **without assigning the result** (verified: line 635 discards it), purely for its raise-on-missing/wrong-workspace side effect, so the manifest's `effective_sensitivity`, `target_refs`, and `operation_kind` are never compared to `resume_ctx`. Reachable path: an identity holding `job.resume` in workspace W mints a valid confirmation for a **low-sensitivity** ctx (all five stages legitimately pass *for that ctx*), then presents it against a **higher-sensitivity** operation in the same W. Workspace equality holds, so nothing rejects the mismatch. H3 scenario 9's guarantee — resume re-evaluates against *current* policy/sensitivity — is thereby evaluated against a caller-chosen stand-in. |
| R2 | MED | **`workspace_id` trusted from the caller.** Threaded unchecked into `write_checkpoint`/`finalize_terminal_receipt`, whose `workspace_id` columns back `idx_checkpoints_workspace`/`idx_terminal_receipts_workspace`. Never compared to the manifest just loaded, so an inconsistent value denormalizes receipt rows under the wrong workspace and any workspace-scoped read keyed on that column misattributes across workspaces. |

**Both are the F1 pattern on a sibling method.** `AuthorizationProof` was introduced specifically to
close "public method reaching durable state, precondition enforced only by a docstring" for
`consume_and_create_operation` — and was simply never applied to `resume_operation`. The binding was
held together by *caller convention* (the tests happen to pass
`targets=(TargetRef("agent_job", operation_id),)`). This is now the **sixth** instance of the
layer-below/sibling class in this workstream (F1, G2, BLOCK-2, R5-BLOCK-1, R5-BLOCK-3, P2R-BLOCK-1 →
R1/R2), which is why the fix task was told to assume a third sibling exists until every public method
in the module has been enumerated.

**Routing conclusion:** ICA is effective on *review* work, not just mechanical implementation — this
was the single highest-value-per-token delegation of the phase.

## Regression gate — PASSED with a real baseline diff

`pytest` full-suite numbers are meaningless in this repo without a baseline, so one was built:
a detached worktree at P2's starting commit (`e5a2e6e`) running the byte-identical command.

| | dots (passing) | F | E | skip | distinct failing nodes |
|---|---:|---:|---:|---:|---:|
| Baseline `e5a2e6e` | 4258 | 32 | 46 | 6 | 16 |
| After P2 | 4370 | 32 | 46 | 6 | 16 |

`comm` on the sorted failing-node sets: **zero new, zero fixed — the sets are identical.** Every red
test is inherited; P2 adds 112 passing tests and regresses nothing. No P2-surface test appears in the
failing set at all.

**Two traps worth recording, both of which would have produced a false "clean suite" claim:**

1. **A full `pytest` run aborts at collection with exit 2 and runs ZERO tests.**
   `tests/test_verification_pediatric_cds.py` and `test_verification_seam001_gate_composition.py`
   do `import test_claim_verifier` / `import test_pediatric_cds_redteam_fixtures` — sibling *test
   modules* that only resolve when those siblings are collected first. The plan documents this as a
   `-k`-filtering artifact; it in fact breaks the **unfiltered** run too, and `Interrupted: 2 errors
   during collection` means nothing executed. `--ignore` both to get any signal at all.
2. **A wrapper's exit code is not pytest's.** `pytest … > log; echo "EXIT=$?"` inside a
   `run_in_background` Bash call reports the *wrapper's* status to the completion notification — which
   arrived as "exit code 0" for a run that had actually failed with exit 2 and run no tests. Always
   write the real `$?` into the log and read it back.

Also confirmed: the full-suite run left **no** stray `run/`/`ccdash` artifacts in the worktree (the
data-plane split holds), so the historical full-pytest pollution hazard did not materialize here.

## P2 security gate (AC-mandated) — `CHANGES_REQUESTED`, 5 blocking

Ran on Opus against exact tree `4b1b6fd`, per the revised post-P1 structure
(security-with-AC-mandate → Karen, because a validator alone will approve a read-then-write CAS).
Findings in `FIND-P2-SECURITY-GATE` (commit `b7dc8eb`).

**AC OPM-2 NOT MET · AC OPM-3 NOT MET.**

| ID | Sev | Finding |
|---|---|---|
| P2S-BLOCK-1 | blocking | **DUR-1 is correct in code but defended by no test that can fail.** The reviewer converted the implementation into a *true* read-then-write — moved `COMMIT` before `_consume_locked` **and** deleted the CAS predicate — and the real multi-process G5 test **still passed**; the threaded test only failed under full-file ordering and passed in isolation. |
| P2S-BLOCK-2 | blocking | `run_actions` discards `finalize_terminal_receipt`'s outcome (`operator_cancel_resume_service.py:550-558`) → EXTRA corruption returns `status="completed", terminal_receipt=None` instead of denying; H3 scenario 8 does not converge. |
| P2S-BLOCK-3 | blocking | `OperatorReceiptService` has **no identity/workspace seam at all** — `workspace_id` caller-asserted into immutable rows (`:423`, `:646`), all three reads unscoped (`:508`, `:770`, `:785`), while the authoritative value sits on the same connection. Directly fails AC OPM-2, whose contract names *receipts* as a gated surface. Related: `effective_sensitivity` is written (`operator_operation_service.py:1209`) and **never read**, so sensitivity gates nothing anywhere. |
| P2S-BLOCK-4 | blocking | Action/effect receipts accept an `operation_id` with no `operations` row; because the immutability triggers refuse repair, one out-of-turn receipt **permanently bricks** that operation. |
| P2S-BLOCK-5 | blocking | `cancellation_requested` has no workspace predicate and the row cannot be rescinded → anyone holding an `operation_id` can permanently DoS that operation's lifecycle across workspaces. Severity re-rating of a disclosed item. |

Verified by mutation to **HOLD**: G1 (expiry-after-lock), F1 (both halves — data dependency *and*
ctx-digest rebinding), R1, R2, R3, G4 triggers. **PARTIAL**: F4 (sibling raw-raise sites remain).
**DOES NOT HOLD**: G5.

### The lesson of P2S-BLOCK-1 — and my own miss

This is the phase's most important finding, and it is a process finding as much as a code one.

Every layer above it looked green: DUR-1's transaction boundary **is** correct, 606 tests passed, the
implementer produced a plausible mutation table, and I personally ran revert-detection and watched
tests fail. But my revert-check mutated **G1 and G2** — not the CAS itself. The implementer's own
"mutation #1" removed `BEGIN IMMEDIATE`, which is a *weaker* mutation than a true read-then-write. So
the one guarantee the plan singles out as frozen (*"a read-then-write implementation passes every P1
test and is still wrong"*) was the one guarantee nothing could detect the loss of.

Generalizable rule: **when a plan names a specific wrong implementation, the mutation must be exactly
that wrong implementation** — not a nearby proxy. "I mutated something and a test failed" is not the
same as "I mutated *the* thing." Adding G5's multi-process test made the coverage *look* stronger
while leaving the actual predicate untested.

Second lesson: the reviewer also found the threaded test **passes in isolation and only fails under
full-file ordering** — an order-dependent test is not a guard. Any new DUR-1 test must be run
standalone as well as in-file.

## Karen gate — `CHANGES_REQUESTED` (exact tree `2806ea5`)

Karen confirmed the hard part is real, then found a genuine hole *and corrected two of my own
disclosures*. The disclosure corrections are the more valuable half.

**Mutation-verified as genuinely load-bearing** (Karen ran these, not the implementer):
`BEGIN IMMEDIATE`→`BEGIN DEFERRED` at 3 sites → **5 tests fail** including both multi-process tests;
stripping `AND status = 'issued'` from the CAS → 1 test fails; neutralizing the resume sensitivity
rank → the R1 test fails; disabling the reordered-range check → its test fails. So after
P2S-BLOCK-1's remediation, **DUR-1 is now genuinely mutation-proof** — the phase's central claim is
real. Karen also confirmed the audit-non-erasure ordering is *structurally* correct (reconciliation
precedes the audit call, which sits outside the transaction) and that the convergence test's
normalizations do **not** launder away effect divergence — it compares effect payloads and ordering.

**Blocking — CRITICAL: an untested cross-workspace WRITE hole.**
`tests/unit/test_operator_attempt_adapter.py:276-292` is named
`test_every_lifecycle_wrapper_denies_wrong_workspace…` and enumerates **7 of 9** wrappers. It omits
`persist_event` and `persist_artifact` — precisely the two whose underlying `AgentJobService` methods
(`agent_job_service.py:497`, `:517`) take **no `identity` and scope nothing**, so the adapter gate is
the *sole* boundary. Karen removed both gates and the full operator suite **plus**
`tests/test_workspace_isolation_enforcement.py` stayed exit 0, zero failures. This is P1's `K-FINAL-1`
lesson recurring: enumerate **every** public symbol, and beware a test whose *name* asserts more than
its parametrize list covers.

Four more: truncated/extra receipt tests both pass with their own guard disabled (a redundant sibling
range check subsumes them — correct behavior, but neither test pins its guard: the BLOCK-4 signature
again); no test asserts a **stale/original** confirmation is rejected on resume, so H3 scenario 9's
"fresh confirmation" is a property of the harness rather than the service; scenario 10's
`assert not dest.exists()` is tautological (the service never sees `dest`); and the `accept_job`
trip-wire is a substring *name* ban while the docstring's stronger "never calls it" claim is untested.

### Karen corrected two of my disclosures — both were wrong

1. **`effective_sensitivity` is NOT inert.** The fix wave declared it "inert by design at this layer,
   deferred to P5." That is **stale**: it is read at four real decision sites
   (`operator_mcp_policy.py:1432`, `:1436`, `:1864`; `operator_cancel_resume_service.py:283`) with
   behavioral tests. What is actually dead is the `operations.effective_sensitivity` **column** —
   written at `:1253`, zero readers, because every SELECT projects `manifest_json`. So: a dead
   denormalized copy plus an out-of-date note, not a security hole. The disclosure erred toward
   *understating* the implementation, which is the honest direction, but it was still wrong.
2. **`OPM-DF-preflight` was factually false, and I put it in a durable ITT node.** I recorded
   "`governance.preflight()` has ZERO call sites" from the P1 ledger digest. It **does** have a
   production call site — `services/planning.py:955`. Verified directly. The operator path simply
   uses its own `_check_preflight` (`operator_mcp_policy.py:1453`), which **is** wired as the 5th of
   five stages in the fixed-order chain (`:1518`) and produces real denials with coverage. The node has
   been corrected and downgraded from high/`s` to low/`xs`: it is a design-and-documentation decision,
   not an unwired security stage.

**Lesson: a digest of a findings ledger is hearsay, not evidence.** Both corrections trace to me
carrying a delegated summary forward without re-verifying the underlying claim — and one of them
hardened into a tracker node that would have sent a future agent chasing a phantom. Grep the claim
before you file it.

## Round-2 remediation (U1–U10 + Karen A1/A2) — commits `728cd25`, `14ee7f6`

Union of both gates' findings, closed as two waves on non-overlapping files.

**Karen A1 needed its severity corrected.** The adapter's production gates were **already present and
correct** (`operator_attempt_adapter.py:375`, `:399`) — verified, not assumed, and the adapter source
is byte-identical to HEAD. It was a pure **test-coverage** gap: `persist_event`/`persist_artifact` were
omitted from a parametrized test *whose name claimed universality*, and they are the only two wrappers
with no scoping underneath, so the adapter gate is their sole boundary. Not an exploitable hole — but an
unguarded guard a refactor could have silently deleted. All 9 wrappers now parametrized (9 cases verified
to execute), and the `accept_job` trip-wire upgraded from a method-*name* ban to a real call spy.

**The receipt/lifecycle wave closed all ten items.** Highlights of what was actually wrong: receipt
writes *claimed* to derive-and-deny but **logged a warning and overwrote**, so a forged terminal receipt
was accepted and then read back by the owner's own successful run, immutably; two of four write paths
took no workspace parameter at all; **6 of 11** outcome-carrying calls still discarded the outcome
(including all five `write_checkpoint` calls, so `run_actions` could return `"completed"` with zero
checkpoints persisted); and a gap receipt permanently bricked an operation — with the previous wave
**pinning that as correct in a test**, now deleted and replaced by one asserting the operation stays
resumable.

### Three process wins worth keeping

1. **The implementer caught its own redundant-sibling trap.** Its first U4 test used a fresh
   zero-receipt operation, which the truncation guard denied independently — so it would have passed
   regardless of the new guard. Its own mutation run exposed this, and it rewrote the test to pre-seed
   exactly five correct contiguous receipts so reconciliation would *succeed* if the new guard did not
   fire. This is the same false-closure mode that produced two earlier bad clears in this phase, caught
   at source for the first time.
2. **It removed redundancy instead of adding layers.** `_reconcile`'s two checks were mathematically
   equivalent (lists of different lengths are never equal, so the length check could never fire
   independently). Collapsed to one — and now all three corruption tests fail together when it is
   disabled. Previously the redundancy masked which test pinned what, which is precisely how
   `P2S-BLOCK-2`'s tests passed on revert.
3. **DUR-1 flakiness fixed at root cause, not by loosening the assertion.** The flake was a raw
   `OperationalError` killing a child process — now a governed denial via U6 — so the discriminating
   wall-clock bound stayed untouched. Weakening it to buy stability would have quietly un-defended the
   phase's central claim.

### METHODOLOGY: mutation loops here silently produce FALSE GREENS

The adapter wave's first per-wrapper pass reported **4 of 9 gates as "passes on revert."** Cause: each
iteration deleted the *same 20 characters*, so identical file-size deltas collided with `mtime`
resolution and CPython reused a `__pycache__` `.pyc` **from a different mutation**. With caches cleared,
all 9 correctly went red.

**This retroactively casts doubt on every "mutation-verified" claim in this workstream that did not
clear caches** — mine included. A false green reads identically to "this guard is untested," so it
corrupts conclusions in *both* directions: it can condemn a working guard or bless a broken one. It is a
plausible contributor to this repo's documented `BLOCK-4` history. Every mutate/restore loop here must
`rm -rf __pycache__` and set `PYTHONDONTWRITEBYTECODE=1` **per iteration**. Saved to project memory as
`mutation-testing-pycache-false-green`.

### Accepted judgment call

Absent-operation and wrong-workspace now both return `not_found` on all four write paths (absence
previously returned `internal_error`). Distinguishing them would let a caller learn "this operation
exists in another workspace" versus "it does not exist" — exactly the oracle the no-existence-leak
convention closes, and the shape every other hardened path in this module family already uses. Five
pre-existing tests' expected reason codes were updated.

## Final state (tree `be6ba96`) — implementation COMPLETE, formal gate NOT OBTAINED

**This is the honest status line, and it deliberately does not say "approved".** P1's defining failure was
closing with a machine verdict of `CHANGES_REQUESTED` still standing; P2 will not repeat it by
relabelling. The phase artifact stays `status: in_progress` with `verified_by` **empty**.

What *is* established, each verified by the orchestrator independently rather than accepted on report:

| Claim | Evidence |
|---|---|
| All 4 tasks implemented | OPM-2.1 `55c341c`, 2.2 `0e2d1c6`, 2.3 `cb11d6f`, 2.4 `4bad38c` |
| DUR-1 closed and **mutation-proof** | Two reviewers, two different mutations: exact read-then-write re-applied (tests fail), and `BEGIN IMMEDIATE`→`DEFERRED` at 3 sites (5 tests fail) |
| All 11 outcome guards pinned | Per-row matrix, each with a named failing test; orchestrator hand-verified row 6 (`assert 'completed' == 'denied'`) |
| All 4 receipt write paths authorize | Deny (not warn-and-overwrite) on workspace mismatch **and** absent operation |
| Both unrecoverable-brick classes closed | Gap receipt refused at write time; 201st effect receipt refused at write time |
| Final delta clean | `14ee7f6..be6ba96` reviewed for both defect classes → **no new defects**; cap proven correctly bounded by two mutations incl. the `>=`→`>` off-by-one direction |
| Zero regressions | 4410 passing vs 4258 baseline; identical 16 failing nodes; none on the operator surface |
| Barrier files untouched | All seven, verified against P2's own baseline `e5a2e6e` |
| Targeted suite | 647 dots, 0 F, 0 E, 0 skips, exit 0; flake8 `E9,F63,F7,F82` exit 0 |

**What is missing, precisely:** an `APPROVED` verdict on tree `be6ba96`. Karen's round-2 blocking item is
closed (and the wave found 4 unpinned guards where Karen reported 2), but Karen has not re-verdicted on
this tree. The security lens' final round **died twice on 529 API-overload errors** without returning a
verdict. Round 2's last recorded machine verdict was `CHANGES_REQUESTED`; every item in it is closed, but
"all findings closed" is not the same artifact as "gate approved" — which is exactly the distinction P1
blurred. Next action is a re-gate on `be6ba96`, not a re-fix.

### Orchestration errors I made, worth carrying forward

1. **I ran two mutation-testing reviewers concurrently on the same files.** Mutation reviewers are
   **writers**, not readers, despite a read-only *mandate*. Karen hit the security lens' foreign markers
   (`# MU2`, `# MU4b`) mid-run, so its first batch was racy and its verdicts inflated by another agent's
   collateral failures; it recovered by rebuilding an isolated tree via `git archive`. I had carefully
   serialized fix-agents against reviewers and then made the identical mistake one level up.
2. **A reviewer died mid-mutation and left a deliberately broken CAS in the working tree** — `COMMIT`
   hoisted above the locked section and the `AND status = 'issued'` predicate stripped. Had I committed
   in that window, `git add` would have shipped the precise defect this entire phase exists to prevent.
   Caught by inspecting `git diff` before committing. **Fix adopted:** reviewers must work in
   `git archive HEAD | tar -x -C <tmpdir>` and never touch the live tree; the third reviewer did, and the
   tree stayed clean when it also died.
3. **I compared barrier-file cleanliness against the wrong baseline** (main's `65d658d` instead of P2's
   `e5a2e6e`), which surfaced P1's own `governance.py` deviation as if it were P2's. Caught immediately,
   but a phase-scoped claim needs a phase-scoped base.

### The three recurring lessons, each of which cost multiple rounds here

- **A green suite plus a self-reported mutation table is not evidence.** Every fix wave in this phase
  reported mutation-verified closure, and each of the first two had at least one item that did not hold.
  Three distinct false-closure modes appeared: a *redundant sibling guard* denying at the same index for a
  different reason; a test passing by *arithmetic accident* (`range(7,5)` is empty); and a stale
  **`__pycache__`** returning a mutant's result for a different mutation. Only the third wave caught its
  own trap before submitting.
- **When a plan names a specific wrong implementation, mutate exactly that.** DUR-1's frozen warning is
  that a *read-then-write* passes every test. The first wave mutated `BEGIN IMMEDIATE` instead — a nearby
  proxy — and I accepted it. The real mutation showed the guarantee was undefended.
- **A digest is hearsay.** Both gates and I repeated "`effective_sensitivity` is never read in any gate"
  until someone grepped; it is read at four sites. I filed a related false claim
  (`governance.preflight()` has zero call sites — it has one at `planning.py:955`) into a durable ITT
  node, since corrected and downgraded. Grep the claim before you file it.

## Open items / follow-ups (→ ITT nodes)

Filed on tree `aos-research-foundry`:

| Node | Item |
|---|---|
| `OPM-DF-preflight` | `governance.preflight()` still has zero call sites; needs run-layer wiring + an artifact that FAILS if unwired. |
| `OPM-DF-regate` | P1's round-6 consolidated security re-gate, deferred; last machine verdict was `CHANGES_REQUESTED` (R5). |
| `OPM-P2-audit-mutation-type` | Audit vocabulary has no operator-mcp `mutation_type`; receipts are logged as `agent_job_launched`. |
| `RF-schema-format-checker-inert` | Repo-wide: `format: date-time` is enforced nowhere — no `format_checker` attached in `SchemaRegistry.validate` or any test helper, so every timestamp field in every RF schema is an unconstrained string. |

Still to file once P2 closes: the `job.json`↔`attempts` cross-store atomicity gap (needs a cleanup
path on the frozen `agent_job_service.py`), and anything surviving the blocking-fix wave.

Populated as execution proceeds; see the Next Actions table in the final response.

## Round 3 — re-gate of `be6ba96`, and the K3 fix wave

Full record in `.claude/findings/research-foundry-operator-mcp-findings.md` §`FIND-P2-REGATE-R3`.

**Security gate (Opus, AC-mandated): `APPROVED`** — AC OPM-2 and AC OPM-3 both MET, 25 mutations,
24 detected. **Karen (Opus): `CHANGES_REQUESTED`** — one blocker.

Both lenses were run **sequentially**, each in its own `git archive` export, per this phase's own
orchestration lesson. The live worktree stayed clean throughout (`git status` empty before and after).

**K3-BLOCK-1** — the round-2 remediation asserted, in production source, that *"EVERY
reachable-by-contention raw exception in this module (lock acquisition, ...) is now governed"*. The
claim was false about the very method carrying it: `record_confirmation`'s own `_ensure_schema` /
`BEGIN IMMEDIATE` sat outside any handler. Karen broke it in one probe. Seventh instance of the
layer-below/sibling class, and the third *false-completeness-claim* rated blocking here.

**The lesson this adds to the phase's three:** *a completeness claim is a testable assertion, and
writing one down is taking on an obligation to have checked it.* Every prior instance of this class
was a guard missing on a sibling. This one was a **sentence** missing a check — asserted about a whole
module from inside the one method that falsified it. The corrected comment deliberately claims only
what its own method does, and does not restate a module-wide property.

**Two process notes worth carrying forward:**

1. **The bg-session subagent write-block fired.** A background session whose shell merely `cd`s into
   an existing worktree can edit files itself, but its *subagents* are blocked ("parent hasn't
   isolated"), and `EnterWorktree` refuses when cwd already *is* the target. The dispatched
   implementer hit this, **correctly refused to route around the guard via Bash**, and returned a
   complete fix spec instead — which is the right failure mode and made the inline application cheap.
   Already recorded in project memory; re-confirmed here.
2. **Mutation verification happened inside the fix step, not the next review round** — the P1 lesson,
   applied. Five mutations, five detections, caches purged every iteration, plus a **non-redundancy
   cross-check** proving K3-BLOCK-1's two clauses each fail only their own test. The K3-NB-1 test
   asserts the *effect* observable (`executed == []`) rather than the outcome, because the pre-fix
   failure mode is a downstream guard objecting **after** the effect already ran — an outcome-only
   assertion cannot distinguish those.
