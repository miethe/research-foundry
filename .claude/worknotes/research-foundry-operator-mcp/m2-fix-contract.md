---
type: worknote
schema_version: 2
doc_type: worknote
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: in_progress
created: '2026-07-31'
updated: '2026-07-31'
---

# M2 fix cycle 1 — consolidated contract (DECIDED)

Inputs: `.claude/findings/m2-pregate-terra.md` (8 findings, 3 blocking) and
`.claude/findings/m2-pregate-ica.md` (0 findings, 1 LOW note). Read BOTH before starting —
including the findings assigned to the other leg (M1 lesson O-8: cross-pollination prevents a
fresh instance of a known defect).

## Orchestrator adjudication (binding — do not re-litigate)

**The root cause of TERRA-1/2/3/4 is ONE structural gap: the registered MCP route was never
exercised end-to-end.** Every M2 test drove adapters directly with hand-built `PolicyContext`s, or
drove `server.call_tool` for a single call in isolation. Nothing ever ran
**preflight → (persist) → execute** as a sequence through the server. That gap masked missing
persistence (TERRA-1), a dropped context field (TERRA-2), a canonical-payload omission (TERRA-3),
and a generic kwargs pass-through (TERRA-4). The e2e test in F1.5 is the highest-value item in
this cycle — it is not optional and it is not a formality.

| Finding | Adjudication | Leg |
|---|---|---|
| TERRA-1 (BLOCKING) preflight never persists the minted confirmation | **FIX.** Confirmed: `record_confirmation` appears nowhere in `server.py`. | 1 |
| TERRA-2 (HIGH) preflight drops `writeback_targets` | **FIX.** Confirmed: `writeback_targets` appears nowhere in `server.py`. | 1 |
| TERRA-3 (BLOCKING) `retrieval_limits` reaches the service but not the canonical digest | **FIX + ENUMERATE THE WHOLE PATTERN** (F2.1). Confirmed by direct read of `run_plan.py`. | 2 |
| TERRA-4 (HIGH) caller can inject `now`/DI kwargs via the generic dispatcher | **FIX.** Controls confirmation expiry — an authorization bypass. | 1 |
| TERRA-5 (BLOCKING) unbound `FastMCP.sse_app(instance)` bypasses the guard | **DOWNGRADED to MED-documentation + queued for the security gate.** See below. | 1 |
| TERRA-6 (MED) `RecursionError` escapes the envelope on deep nesting | **FIX.** | 1 |
| TERRA-7 (MED) unbounded preview target cardinality → response amplification | **FIX.** | 2 |
| TERRA-8 (MED) staging not namespaced per operation | **FIX.** | 2 |
| ICA E2 (LOW) unknown fields are silently dropped, not rejected | **FIX AS A CLAIM CORRECTION** (docstring/D4 language) + assert the drop behavior in a test. | 1 |

### TERRA-5 adjudication (read this before touching the guard)

`FastMCP.sse_app(instance)` returning a Starlette app is **real and reproducible** — and it is
**not fixable in the strict structural sense**: Python cannot prevent `Base.method(instance)`, and
swapping the subclass for a wrapper trades this bypass for the `__self__`/`_inner` bypass class
that `knowledge_mcp/registry.py`'s own docstring explicitly rejected the wrapper to avoid.

The reachable threat model is the deciding factor: an MCP client speaking stdio can only invoke
registered tools, and **no registered tool evaluates caller-supplied Python**. Reaching the
unbound call requires arbitrary in-process code execution, at which point the attacker can
`import socket` directly and the guard is moot either way.

Therefore: **do not redesign the guard.** Instead —
1. Scope the claim precisely everywhere it is made (module docstring, D3 language, test names):
   the guard blocks every **reachable** activation path (entrypoint, config, env, `run()`,
   bound methods) — it is **defense-in-depth, not a sandbox**, and it does not survive arbitrary
   in-process code execution.
2. Add a test that **pins the limitation explicitly** (asserts the unbound base call is a known,
   documented escape) so no future reader mistakes the guard for stronger than it is.
3. **Do not mark this closed.** It goes to the security gate as an explicit queued adjudication.
   The identical limitation exists in the already-shipped `knowledge_mcp` guard (filed as a
   follow-up ITT node) — flag any disagreement rather than silently resolving it.

## Hard boundaries (unchanged from `m2-implementer-contract.md`; violating any is STOP-and-report)

1. **Do not edit** `operator_mcp_policy.py`, `operator_operation_service.py`,
   `operator_cancel_resume_service.py`, or `operator_mcp_adapters/base.py`. If a fix appears to
   require one, STOP and report — that is a real scope change, not a judgment call.
2. **Do not edit** `src/research_foundry/knowledge_mcp/`.
3. Live writeback must stay unreachable from every registered tool. Turning the preview seam live
   is **Mode-D** → halt for explicit human approval.
4. Never `git stash`; prove pre-fix failure with a scratch copy. The orchestrator is the only
   committer — run **no** git commands.
5. Do not weaken or delete an existing test to make a fix pass. If a test pins wrong behavior,
   **invert it** and say so loudly in your completion note (M1 defect class 3, now on its 4th
   occurrence in this workstream).

## Leg 1 — server/transport (claude-primary; MUST-stay: authorization semantics)

Owns: `src/research_foundry/operator_mcp/server.py`, `tests/integration/test_operator_mcp_server.py`,
and a NEW `tests/integration/test_operator_mcp_preflight_execute_e2e.py`.

- **F1.1 (TERRA-1)** Persist the minted confirmation durably before `operation.preflight` returns
  it, in the same atomic step the consume path expects (`record_confirmation`). A persistence
  failure must surface as a governed error envelope, never a silent success. Preflight still
  **never consumes** the token and still performs **zero effect** beyond this persistence — re-prove
  both.
- **F1.2 (TERRA-2)** Pass the caller's normalized writeback target list into `PolicyContext` as
  `writeback_targets` for `writeback.preview` preflight. Source the names from the same closed
  vocabulary Leg 2 owns — coordinate on the constant, do not duplicate the list.
- **F1.3 (TERRA-4)** Build a **per-adapter allowlist derived from the real adapter signature** and
  reject any caller key that is not a declared semantic parameter — explicitly including the DI /
  test-only names (`now`, `paths`, `operations`, `cancel_resume`, `receipts`, `attempts`). Rejection
  is an explicit bounded envelope, not a silent drop. `now` must be server-derived, always.
- **F1.4 (TERRA-6 + ICA E2)** Put all argument inspection inside the exception boundary and apply
  an explicit depth/structure cap before re-serialization, so deep nesting yields a bounded
  `internal_error`/`payload_too_large` envelope rather than `RecursionError`. Correct the D4/
  docstring language: unknown top-level fields are **dropped by model validation**, not rejected
  by the server (or make them rejected — your call, state which you chose and why).
- **F1.5 (THE KEY TEST)** New e2e file: drive **`operation.preflight` → execute** entirely through
  `server.call_tool` for (a) at least one mutation kind and (b) `writeback.preview`. Assert the
  confirmation minted by preflight is actually consumable by the subsequent execute call, and that
  drift between preflight and execute (changed payload/target/workspace, expiry, replay) is
  refused with an explicit **zero-effect** assertion on each. This test must fail against current
  HEAD — prove it.
- **F1.6 (TERRA-5)** Documentation/claim scoping + the limitation-pinning test per the adjudication
  above. Do **not** redesign the guard.

## Leg 2 — adapters/writeback (claude-primary; MUST-stay: confirmation binding)

Owns: `src/research_foundry/services/operator_mcp_adapters/*.py` (all adapter modules),
`src/research_foundry/services/writeback.py`,
`tests/unit/test_operator_mcp_adapter_*.py`, `tests/integration/test_operator_mcp_writeback_preview.py`.

- **F2.1 (TERRA-3 — ENUMERATE THE WHOLE PATTERN, highest value in this leg)** Fix
  `retrieval_limits` in `run_plan.py`, then **audit all 13 adapters** the same way. For each
  adapter produce a table: *every* caller-supplied parameter forwarded to the canonical service ×
  whether it appears in the canonical `input_payload` that feeds `PolicyContext.canonical_digest()`.
  Any parameter that reaches the service but not the digest is the same defect — fix each one.
  **Do not stop at the one instance the reviewer named.** (P2 memory: three adversarial rounds were
  burned on one pattern found one instance at a time. M1: 3 of 6 defects were this exact class.
  This is its 4th appearance in this workstream — enumerate it out of existence now.)
  Beware the mirror-image bug: adding a key to the digest changes idempotency collapse, so verify
  the None-dropping normalization still makes two callers who both omit an optional agree.
- **F2.2 (TERRA-7)** Bound `writeback.preview` targets before normalization: cap the count, cap
  per-name length, and accept only names in the closed 6-name `writeback()` vocabulary — anything
  else is `target_invalid`, not a per-target `unsupported_target` row. `ccdash` remains the one
  known-name `unsupported_target` (deferred by design). Cap the returned target list/effect summary.
- **F2.3 (TERRA-8)** Namespace staged preview artifacts by operation (operation id or immutable
  content digest) and return only that operation's own reference. State the replay/cleanup
  semantics you chose in your completion note. Leg 1's e2e test will exercise this — keep the
  returned path shape stable and tell Leg 1 if it changes.
- **F2.4** Re-prove the negative evidence after every change: zero client constructions, zero
  network primitives, nothing written outside the operation's own staging area, on **every**
  outcome path (happy / missing / degraded / unsupported / denied). ICA's E3 matrix is the bar —
  match or exceed it.

## Cross-leg coordination

- The closed writeback-target vocabulary is a **single constant owned by Leg 2**; Leg 1 imports it.
  Agree on the name early; do not define it twice.
- Leg 1's F1.5 e2e test depends on Leg 2's F2.3 staging path shape. If either side changes a
  contract the other consumes, say so in your completion note explicitly.
- If you find a defect in the OTHER leg's files: report it in your completion note, do not fix it.

## Validation (both legs; interpreter is ALWAYS `./.venv/bin/python`)

```
./.venv/bin/python -m pytest tests/integration/test_operator_mcp_server.py \
    tests/integration/test_operator_mcp_writeback_preview.py \
    tests/integration/test_operator_mcp_preflight_execute_e2e.py \
    tests/test_operator_mcp_offline_import.py \
    tests/unit/test_operator_mcp_adapter_*.py tests/unit/test_operator_mcp_packaging.py -q
./.venv/bin/python -m pytest tests/unit/test_operator_mcp_policy.py tests/unit/test_knowledge_mcp_registry.py -q
flake8 src/research_foundry --select=E9,F63,F7,F82
```

Whole-tree baseline for reference: 4694 collected, 5 pre-existing failures (3 documented baseline
+ 2 data-plane-absent), none on the operator surface. Report any NEW failure.

## Completion note (each leg, REQUIRED)

`.claude/worknotes/research-foundry-operator-mcp/m2-fix-leg-<1|2>-completion.md`: finding-by-finding
disposition (fixed / disputed-with-evidence / deferred-with-reason), the F2.1 full 13-adapter table
(Leg 2) or the per-adapter allowlist derivation (Leg 1), proof each regression test fails pre-fix,
real command tails, and anything the security gate should attack first.
