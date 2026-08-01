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

# M2 delivery notes — stdio surface exists and provably cannot execute

> **Scoping note (fix cycle 1/2, TERRA-5/SEC-8):** "provably cannot execute" is scoped to every
> path a real caller can drive through the registered stdio surface, not to arbitrary in-process
> code execution — see `server.py`'s module docstring, "Scope of the stdio-only guard" section, and
> `m2-fix-contract.md`'s TERRA-5 adjudication for the full reasoning.

Running capture for the M2 delivery report + AAR. Continues the M1 pattern
(`m1-remainder-delivery-notes.md`).

## Setup

- Branch `worktree-operator-mcp-v1` @ `053a2c8` (M1 head, pushed, PR #7). ITT node
  `node_01KY5SHNM6JVMCCKYXP44GRSDR` (C5, epic Wave 4) marked `in_progress` at M2 start.
- Provisioning gate: 1 non-fatal gap (skill:delegation-router overlay refused by SkillMeat
  enterprise — skill live at user scope; `enterprise.deploy.overlay_refused`). Non-blocking.
- Fact pack (read-only explorer): 14-tool closed inventory = 12 landed adapters +
  `operation.preflight` (server meta tool, no adapter) + `writeback.preview` (**no adapter, no
  preview seam, no staging root exist yet** — the real M2 build). Knowledge MCP supplies the
  optional-SDK/stdio-only/closed-schema patterns; pyproject already has the shared `mcp` extra.
- Contract: `m2-implementer-contract.md` (decided D1-D10; sibling-input enumeration per M1 AAR
  carry-in #1/#3; scratch-copy rule replaces `git stash` per carry-in #5).

## Routing (delegation-router resolved, logged intent)

| Leg | Work | Route |
|---|---|---|
| A | OPM-5.3 writeback.preview adapter + pure-render split + spies | claude-primary sonnet (preview seam is MUST-stay-adjacent) |
| B | OPM-5.1/5.2/5.4 server scaffold + closed registry + error mapping | claude-primary sonnet |
| C | OPM-5.5 packaging tests | ICA sonnet-5[1m] free lane |
| Pre-gate | two diverse cheap lenses | gpt-5.6-terra (high) + ICA sonnet-5[1m] |
| Gate | security lens (fresh context) | claude Opus — MUST-stay, frontier-class |
| Gate | validator | claude sonnet, fresh context |

Codex is NOT used for the security lens itself (workstream constraint: codex refuses
adversarial-audit framing — pre-gate is framed as code review, which held fine in M1).

## Observations for the AAR

- **O-1 — The orchestrator's environment provisioning caused the first defect.** `uv pip install
  "mcp>=1.0"` (matching the pyproject extra's own pin) resolved `mcp==2.0.0`, which **removed
  `mcp.server.fastmcp`** (renamed to `mcp.server.mcpserver.MCPServer`). Consequences: (a) the
  previously-*skipped* knowledge-MCP tests started *failing* — `import mcp` succeeds so
  `importorskip` passes, then `build_server()` raises the "SDK is not installed" RuntimeError —
  a misleading-hint failure mode worth its own defect class note; (b) Leg B, correctly reading its
  actual environment, adapted the server to the 2.0-only API, which would have forked the two MCP
  servers onto incompatible SDK APIs under one shared extra. Leg B flagged it rather than silently
  shipping — the flag-first posture paid out again (M1 O-10). Resolution: venv + shared extra
  pinned `mcp>=1.0,<2`; Leg B continued (same session, cache-warm) to revert to the fastmcp 1.x
  import; SDK-2.0 migration for BOTH servers filed as a follow-up ITT node. Echo of M1's O-5:
  the party who writes the contract can still hand implementers a defective premise — this time
  via the environment, not the contract text. Pre-flight venv assembly should pin what the code
  actually targets, not what the extra merely allows.

- **O-2 — Whole-tests-tree collection has been broken on main since 2026-07-22, and nobody
  noticed.** `2d40f1f` (swarm-driver PR #6) added `tests/__init__.py` ("packaged so pytest gives
  every module a unique dotted name"), which silently broke the three bare sibling imports in
  `tests/test_verification_pediatric_cds.py` / `tests/test_verification_seam001_gate_composition.py`
  — a whole-tree `pytest` run aborts at collection. Masked because every recent milestone ran
  `pytest tests/unit` and called it "full suite" (M1's 2371-node count vs the plan AC's 4410+
  whole-suite baseline). Surgical 2-line orchestrator fix in-branch (`import x` → `from tests
  import x`), logged as an authorized out-of-scope deviation; the M3 whole-suite AC depends on it.
  Lesson: "full suite" claims must name the collection scope; a green subset run reads identical
  to a green suite in a completion note.
- **O-3 — Leg continuation (continue-don't-redispatch) worked as doctrine predicts.** Both wave-1
  legs took a second instruction in their live session (Leg B: SDK revert + extra pin; Leg A:
  target-coverage extension) at a fraction of a fresh dispatch's cost, with no context loss and
  no re-derivation. The M1-style "fix the sibling" discipline held: Leg A's extension added spy
  coverage for the new paths unprompted-in-detail (the instruction named it once).

- **O-4 — The two pre-gate lenses CONTRADICTED each other, and both were right.** On the
  stdio-only transport guard: ICA ran E4 empirically (`server.sse_app()`, `run(transport="sse")`,
  `run_sse_async()`, mount_path variants — 8 attempts, zero sockets opened) and marked it
  **VERIFIED clean**, explicitly asserting "genuine subclass, confirmed no separate wrapped
  instance exists for `__self__` to resolve to". Terra called the SAME guard **BLOCKING**, having
  tried the one thing ICA didn't: the *unbound base-class* call `FastMCP.sse_app(instance)`, which
  returns a live Starlette app. Neither lens was wrong; they probed different bypass mechanics
  (bound dispatch vs. unbound base invocation). **A "checked clean" from a competent lens is not a
  clean bill** — it is one lens's coverage boundary, and coverage boundaries are invisible from
  inside the lens. This is the strongest evidence yet for AAR carry-in #2 (two diverse cheap
  pre-gates); it also means a *single* pre-gate would have shipped an overclaimed security
  property with an empirical "verified" stamp on it.
- **O-5 — 8 findings / 3 blocking on an all-green tree; 4 of them from one structural gap.**
  47 M2 tests passed, flake8 clean, whole tree at baseline — and the registered MCP route had
  never been driven end-to-end. Every test drove adapters directly with hand-built PolicyContexts
  or made single isolated `server.call_tool` calls, so nothing exercised **preflight → persist →
  execute** as a sequence. That one gap masked TERRA-1 (minted confirmations never persisted →
  the product's core flow cannot work), TERRA-2 (`writeback_targets` dropped → preview can never
  be preflighted), TERRA-3 (canonical-digest omission) and TERRA-4 (DI kwargs injectable through
  the generic dispatcher). **Test the product's own route, not a hand-assembled proxy for it** —
  a passing adapter-direct suite is not evidence the surface works.
- **O-6 — The sibling-parameter class has now appeared FOUR times in this workstream** (M1 F2/F3/F5,
  now TERRA-3). Fix cycle 1 therefore requires the full 13-adapter parameter×in-digest enumeration
  rather than fixing the one named instance — applying the P2 lesson (three adversarial rounds
  burned closing one pattern one instance at a time) before it costs a third round here.

- **O-7 — The orchestrator (me) published a wrong baseline number, twice, from bad measurement
  hygiene.** I reported "5 pre-existing whole-tree failures" — read off a `tail -12`, so it was
  only the *last five* FAILED lines of a longer summary — and that figure went into the wave-1
  commit message before Leg 1's independent count of 23 exposed it. Trying to verify, I then ran
  two full suites **concurrently in the same worktree**; these tests write shared run/ccdash
  state, so they polluted each other and produced a spurious operator-surface failure
  (`test_job_resume_wrong_workspace_indistinguishable_from_missing_dry_run`, which passes 31/31
  in isolation). A third attempt was killed at 7%. Corrected in the fix-cycle commit message
  rather than by rewriting history. **Three compounding lessons:** (1) never read a count off a
  truncated tail — `grep -c` the whole file, ANSI-stripped, or read the summary line; (2) never
  run two full suites concurrently in one worktree in this repo; (3) the number that actually
  answers the milestone's question was cheap and reliable all along — **the operator surface run
  as one invocation: 416/416**. Reach for the scoped, reproducible measurement before the
  expensive global one.
- **O-8 — There is no honest whole-tree baseline to compare against, and that is itself the
  finding.** The M1-head baseline worktree could not even *collect* (it aborts on the same two
  import errors this milestone fixed), which proves O-2 conclusively: from `2d40f1f` until now,
  **no whole-tree run has been possible in this repo**, so every "full suite / N passed" figure
  in this workstream's notes was `tests/unit` only. Establishing the real number is delegated to
  the validator gate (V5) rather than asserted here.

- **O-9 — RESOLVED: the honest whole-tree baseline, established for the first time since
  2026-07-22.** Method that finally worked: (1) scratch worktree at the M1 head with *only* the
  2-line collection fix applied, so it can collect at all; (2) extract the failing set from a
  clean serialized M2 run; (3) re-run **exactly that file set** at the baseline — 10 seconds, not
  12 minutes; (4) `comm` the two sorted failure lists. Result: **byte-identical, 23 = 23, zero
  new, zero fixed, zero on the operator surface.** M2 HEAD whole tree = **4691 passed / 23 failed
  / 5 skipped / 1 xfailed**; the 23 span 13 files M2 never touched (serve_api 5, pdf 3,
  assertion_rollout 2, verification 2, swarm_drive 2, contract_drift 2, + 7 singletons).
  **The diff of failure *sets* is the answer; the comparison of failure *counts* never was** —
  and the set diff cost a fraction of the runs I burned chasing counts.
- **O-10 — A third measurement trap, distinct from the ANSI one: non-UTF8 bytes.** `sed` on the
  raw pytest log dies with `RE error: illegal byte sequence` and — piped into `grep -c` — silently
  yields **0**, reading exactly like a green suite. This is a *different* failure mode from the
  known "FAILED lines carry ANSI" trap and defeats the usual `sed`-strip remedy. Working form:
  `LC_ALL=C perl -pe 's/\e\[[0-9;]*[A-Za-z]//g'` plus `grep -a`. Two of my three bad readings this
  milestone came from tooling that fails **toward green**; assume any zero-count is a lie until a
  positive control proves the pipeline can count.

- **O-11 — The security gate found a BLOCKING arbitrary-path escape that my fix contract's
  enumeration boundary structurally could not catch.** SEC-1: `packet_dir` in
  `external_import.py` is an unchecked caller-supplied absolute path; the gate drove it through
  the real MCP route with a genuine minted confirmation and got recursive `scandir` of `/etc`,
  `~/.ssh`, `/var/root`, a symlink escape, and content-parsing outside the workspace — four
  distinguishable envelopes, i.e. a filesystem **oracle**, falsifying M2's "no arbitrary-path
  reach from any registered handler" AC. The sibling `verify_bundle.py:261` has exactly this
  guard, added by **M1's own F5 fix** — which bounded one adapter's paths and left another's.
  **My fix contract then asked Leg 2 to enumerate exactly one class (digest omission).** Leg 2
  did that completely and correctly (the gate independently audited 7 modules / 12 of 13 kinds
  and confirmed the zero-further-instances result) — but a correct, complete enumeration of the
  *wrong* class cannot find the right one. **Lesson, sharper than M1's O-5: it is not enough for
  a contract to demand "enumerate the pattern" — the contract author picks WHICH pattern, and
  that choice is itself the highest-leverage decision. The instruction "fix the sibling" applies
  to defect *classes*, not just fields.** Fifth occurrence of guard-right/inventory-incomplete.
- **O-12 — Two mutations survived, and both were tests passing for the wrong reason.** SEC-4:
  the TERRA-6 depth-cap test nests under key `"n"`, which TERRA-4's allowlist rejects *first*
  with the *same* `payload_too_large` code — so the test never reached the depth cap and would
  pass with the cap deleted. The shipped code is in fact correct (the gate proved it positively
  at depth 50,000), so this is purely an evidence defect — the most expensive kind, because it
  reads as coverage. **Root cause is reason-code overloading**: one code answering five distinct
  conditions makes "the right envelope came back" worthless as a discriminator. A frozen enum
  bought contract stability and paid for it in diagnostic resolution.
- **O-13 — The gate improved on my own reasoning for a call I made.** I downgraded TERRA-5 on
  threat-model grounds ("no stdio client can execute in-process Python"). The gate accepted it
  but supplied a stronger, checkable proof: it re-derived the live caller-reachable parameter
  allowlist for all 13 kinds and showed none accepts a callable, module, or service instance —
  so there is no code-execution *primitive* to reach the unbound call with. Mine was an argument
  from architecture; the gate's is an enumeration over the actual surface. **Adjudications made
  by the party running the milestone should be routed to an independent lens precisely because a
  better proof may exist than the one that satisfied the decider.**

## Follow-ups to file as ITT nodes at close

- Unify the duplicated `_stdio_only_fastmcp_class` guard (knowledge_mcp + operator_mcp) into a
  shared module (deliberate duplication per contract D3).
- `itt node list --tree <research-foundry>` returns 0 rows from this repo context while
  `itt node get/update` work fine — list/filter defect or pagination gap in the CLI.
- MCP SDK 2.0 migration (fastmcp → `mcp.server.mcpserver.MCPServer` rename) for ALL THREE stdio
  servers (`rf-mcp`, `rf-knowledge-mcp`, `rf-operator-mcp`); shared extra now pinned `<2`.
- `ccdash` writeback-preview support: needs the same layer-below split applied to
  `telemetry.emit_ccdash_event` (constructs `CCDashClient` internally); out of M2 file scope.
- Skillmeat preview's `ccdash_event_id` is always empty in preview output (Leg A JC-6) — folds
  into the ccdash follow-up above.
- Whole-suite collection scope: add a CI/gate guard that runs `pytest --collect-only -q` on the
  FULL tree so a packaging change can't silently break collection again (O-2).
