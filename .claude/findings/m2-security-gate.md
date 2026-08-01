---
title: "M2 security gate — findings"
schema_version: 2
doc_type: report
report_category: findings
status: complete
created: 2026-07-31
updated: 2026-07-31
feature_slug: research-foundry-operator-mcp
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
---

# M2 formal security gate — Operator MCP (fix cycle 1 tree, `b4c335c`)

Reviewer: senior-code-reviewer (Mode E). Tree: `worktree-operator-mcp-v1` @ `b4c335c`.
No repo file was modified by this review; no git write command was run. All mutation used
`/tmp` scratch copies driven via `--override-ini="pythonpath=<scratch>/src"`, harness proven
live by a `SCRATCH_ACTIVE_SENTINEL` negative control (`research_foundry.__file__` →
`/tmp/.../scratch/src/research_foundry/__init__.py`). Baseline: **313 passed** on the operator
suite. `git status --porcelain` identical before/after (only the pre-existing dirty
`m2-delivery-notes.md`).

Method: full read of `operator_mcp/server.py`; independent 7-module adapter re-audit (S1);
12-mutation revert campaign (S3); 8-probe attack of the preflight→execute seam (S4);
13-path runtime-spy re-proof of the preview seam (S5); arbitrary-path reach probe (S6).

---

## S2 — TERRA-5 adjudication: I ACCEPT the downgrade. Not a blocking overclaim.

The unbound `FastMCP.sse_app(instance)` bypass is real, and the orchestrator's reasoning holds.
Decisive facts I verified independently: (a) `server.py:123-153` now states the boundary precisely
— every *reachable* activation path is blocked, the unbound base call is not and structurally
cannot be, and the guard is "defense in depth ... not a sandbox against arbitrary in-process code
execution"; (b) `test_transport_guard_unbound_base_class_call_bypasses_the_guard_by_design` pins
the limitation as an asserted, documented escape; (c) **no registered tool exposes a caller-reachable
parameter that is a callable, a module, or a service instance** — I re-derived the live allowlist for
all 13 kinds and confirmed this (S1/B3 below), so there is no in-process code-execution primitive on
this transport to reach the unbound call with; (d) import of `operator_mcp.{server,process}` and
`build_server()` open no socket, spawn no thread, and write no file. Reaching the bypass presupposes
arbitrary in-process execution, at which point `import socket` is available directly and the guard is
moot either way. The shipped claim is now truthful and correctly scoped.

**One residual, filed as SEC-8:** the scoping lives only in `server.py`'s docstring. The milestone
title "The stdio surface exists and provably cannot execute" is repeated unqualified at four doc
sites, and `test_operator_mcp_server.py:710` reuses the same phrase for a *different* guarantee
(no-effect-without-confirmation). That is a claim-hygiene issue, not a reason to reopen TERRA-5.

---

## S1 spot-check — the F2.1 "zero further instances" negative result

I re-derived the parameter × canonical-`input_payload` table from source for **7 adapter modules
covering 12 of the 13 operation kinds** (all except `run.plan`, the already-fixed instance), choosing
them myself rather than trusting Leg 2's table: `source_ingest.py`, `research_stages.py`
(`run.extract`/`run.claim_map`/`run.synthesize`), `verify_bundle.py` (`run.verify`/`run.bundle`),
`external_import.py`, `swarm_start.py`, `job_lifecycle.py` (`job.status`/`job.cancel`/`job.resume`),
`writeback_preview.py`. Method: verbatim extraction of each `invoke*` signature, the literal
`input_payload` dict, the full `for_configured_operator(...)` call, and every argument of the
canonical-service call inside `_run()`.

**Result: I confirm the negative. Zero further instances of the TERRA-3 class.** Every caller
parameter forwarded to a canonical service appears in `input_payload`. The three near-misses each
have an explicit, deliberate binding mechanism rather than a silent omission:
- `source_ingest.content` → bound as `content_digest` (documented F4), raw value forwarded.
- `verify_bundle.report_path`/`claim_ledger_path` → in `input_payload` when non-None, *plus* an
  independent containment check (see SEC-7 — that check is dead on the MCP route).
- `writeback_preview.now` → the one DI-classified name that reaches a canonical service
  (`preview_writeback(now=now)`); it is rejected at the server boundary by `_DI_ONLY_KEYS`, and it
  only sets `generated_at`.

I also verified the mirror-image risk the contract warned about: the None-drop normalization is
applied consistently, so two callers who both omit an optional still collapse to one digest.

**Caveat on the strength of this negative:** it is a *point-in-time* result with no drift protection.
See SEC-5.

---

## SEC-1 — BLOCKING — `packet_dir` is unbounded arbitrary-path reach from a registered handler

File: `src/research_foundry/services/operator_mcp_adapters/external_import.py:210,256-263`
(exposed by `src/research_foundry/operator_mcp/server.py:418` allowlisting `packet_dir`).

**Defect:** an MCP caller can name any absolute host path as `external_report.import`'s `packet_dir`
and the adapter forwards it verbatim to `import_external_report`, which recursively `os.scandir`s it —
falsifying the M2 acceptance criterion "no `accept_job`, shell, subprocess, or **arbitrary-path reach
from any registered handler**" (implementation plan `research-foundry-operator-mcp-v1.md:547-548`).

**Evidence** (real `server.call_tool` dispatch, real preflight-minted confirmation, isolated tmp
workspace, one fresh workspace per case; filesystem calls instrumented):

```
packet_dir='/etc'                    isError=False ok=True block_reason='unsafe_member_path'
packet_dir='/Users/miethe/.ssh'      isError=False ok=True block_reason='required_member_missing'
packet_dir='/var/root'               isError=False ok=True block_reason='unsafe_member_path'
packet_dir='<out-of-ws>/withmanifest' isError=False ok=True 'unsupported_schema_version'  (CONTENT READ)
packet_dir='/etc/passwd' (a file)    isError=True  internal_error
packet_dir='<ws>/evil_link' -> /etc  os.scandir: /private/etc          (SYMLINK ESCAPE)
packet_dir=<another run in same ws>  8 recursive os.scandir over that subtree

paths touched OUTSIDE the isolated workspace:
  os.scandir: /private/etc
  os.scandir: /private/tmp/m2secb-outside-ws
```

The four distinguishable outcomes (`unsafe_member_path` / `required_member_missing` /
`unsupported_schema_version` / `internal_error`) make this an existence + type + symlink-presence +
content oracle over the entire host filesystem, driven from a registered tool, with a durable receipt
written per probe. The `workspace_id` H3 gate does not help: it re-derives the *label*, never inspects
the path.

**This is the sibling-adjacency pattern.** `verify_bundle.py:261-296` received exactly this check
(`_explicit_path_within_run`) under F5. `external_import.py` never did, and its 83-line module
docstring — which discusses `workspace_id` and the `target_run_id` sibling-parameter fix at length —
never mentions `packet_dir` containment at all.

**Fix direction (either closes it):** (1) bound `packet_dir` to a configured packet-staging root and
refuse symlink escape, mirroring `_explicit_path_within_run`'s shape; or (2) if out-of-workspace
packet paths are genuinely intentional (the CLI has the same surface), then scope the AC honestly —
delete "arbitrary-path reach" from the M2 claim, document `packet_dir` as a deliberate operator-trust
surface, normalize the `ok=True`/`internal_error` split so the envelope stops discriminating, and pin
it with a test. What is not acceptable is shipping the AC as written; it is empirically false.

---

## SEC-2 — HIGH — preflight is now an unbounded, un-deduplicated, never-reclaimed durable write

File: `src/research_foundry/operator_mcp/server.py:825`;
`src/research_foundry/services/operator_operation_service.py:868`.

**Defect:** TERRA-1's fix created a resource-exhaustion path that did not exist before it. Measured:

```
200 preflights, varying idempotency_key   -> 200 rows, db 0 -> 348,160 B
200 preflights, IDENTICAL arguments       -> 400 rows  (DEDUPE? NO — 200 distinct rows)
max accepted request (65,236 B)           -> record_json 6,679 B, ~9,490 B on disk / request
sustained                                 -> 50.1 req/s = 435.7 KiB/s = 25.5 MiB/min
grep DELETE FROM|VACUUM|prune|purge|evict|sweep|quota|rate_limit  -> no output
```

`confirmation_id` embeds `secrets.token_hex(16)`, so byte-identical repeats never collapse.
`record_confirmation` is a plain INSERT — no upsert, no quota, no eviction — and there is no pruning,
expiry sweep, or vacuum anywhere in `operator_operation_service.py`. The 5-minute TTL expires the
*token*; the *row* is permanent. The size lever is `targets`: `run.plan` has no required target kinds,
yet preflight accepts and durably binds 20 × 256-char `TargetRef`s that `run_plan.invoke` (which builds
`targets=()`) can never reproduce — maximum-size, structurally-unconsumable rows.

Correct behaviours confirmed: a DENIED preflight writes nothing; `job.status`
(`CONFIRMATION_NOT_REQUIRED_KINDS`) writes nothing.

**Fix direction:** bound it — an expiry sweep of `status='issued' AND expires_at < now` on write, or a
per-workspace issued-confirmation cap, or dedupe by `(canonical_input_digest, idempotency_key)`. There
is no `no-DELETE` trigger on `confirmations` (unlike `operations`/receipts), so a sweep is available.

---

## SEC-3 — MED — the shipped "preflight has zero effect" claim is now false, and its test still endorses it

Files: `src/research_foundry/operator_mcp/server.py:45`;
`src/research_foundry/operator_mcp/__init__.py:19-20`;
`tests/integration/test_operator_mcp_server.py:9,433,449-481`.

`server.py:45` still reads "no operation manifest, no receipt, no adapter action ever runs on this path
**(zero effect)**". The enumerated list is accurate; the parenthetical is not — preflight now performs a
durable INSERT. `__init__.py:19-20` repeats "zero effect" and defers to that same docstring. The
reconciliation exists only ~780 lines later at `server.py:822-825`.

Worse, `test_preflight_allow_mints_confirmation_with_zero_effect` (`:449-481`) proves zero effect by
diffing **only `registries/` and `runs/`** — it never looks at `.rf_state/operator_operations.db`, the
one place the new effect lands. So a false claim is currently test-endorsed. This is the fixers
updating the inline comment and missing its docstring sibling.

**Fix direction:** correct both docstrings to "zero effect beyond one durable `confirmations` row"
(the fix contract's own wording at `m2-fix-contract.md:86`), and widen that test's snapshot to include
`.rf_state` so it asserts *exactly one* new confirmation row and nothing else.

---

## SEC-4 — HIGH — TERRA-6's regression test is vacuous; the fix fails the gate's own closure standard

File: `tests/integration/test_operator_mcp_server.py::test_deeply_nested_argument_maps_to_payload_too_large_not_recursion_error`;
guard at `src/research_foundry/operator_mcp/server.py:398`.

**Mutation result — SURVIVED (313/313 still green) on two independent reverts:**
- **M6:** delete the `_mapping_depth(...) > _MAX_ARGUMENT_DEPTH` block → suite green.
- **M6b:** hoist the name/size checks back *outside* the `try` (reverting F1.4's other half) → suite green.

Root cause of the vacuity: the test nests under key `"n"`, which is not a `run.plan` parameter, so
**TERRA-4's DI-allowlist guard returns the same `payload_too_large` reason code** and satisfies the
assertion. Proven by a combined M6+M5 mutation: with both guards removed the test fails with
`internal_error`. The depth cap has no independent coverage at all.

**The shipped code is nevertheless correct** — I verified it positively rather than by mutation. Deep
nesting under a *legitimate* parameter (`run.plan` → `input_payload.retrieval_limits`), at the top level
of `arguments`, inside a `targets` entry, and as deep *lists*, all return bounded `payload_too_large`
with no `RecursionError` at depths 50,000 / 33 / 31, and the 32/33 boundary is exact.

But per this gate's own standard — "a fix whose test passes against the reverted source is not fixed" —
TERRA-6 is **not closed**. **Fix direction:** one-line change — nest under `retrieval_limits` (a real
parameter) so the depth cap is the only guard that can answer, and add a direct assertion on
`_mapping_depth`. Separately, cover M6b (assert a raising size-check maps to `internal_error`).

---

## SEC-5 — MED — the F1.3 allowlist is a 5-name deny-list with no drift protection

File: `src/research_foundry/operator_mcp/server.py:418` (`_allowed_input_payload_keys`).

The allowlist is `inspect.signature(...)` minus two hardcoded frozensets. It is therefore a **deny-list
of five DI names**: any future adapter parameter not named `now`/`operations`/`cancel_resume`/
`receipts`/`attempts` becomes caller-reachable silently. Searches (`_allowed_input_payload_keys`,
`_DI_ONLY_KEYS`, `_SERVER_SUPPLIED_KEYS`, `allowlist|allowed_keys` across `tests/`) return **no test
that pins the expected allowlist for any kind**. The only coverage
(`test_operator_mcp_server.py:319`) loops over the same five literals the deny-list contains — a
tautology, not drift protection.

Concrete latent vector: the service this family already wraps,
`external_research_import.import_external_report`, declares `policy`, `limits`, `resolver`,
`authorization_policy`, `acquire`, `promote`, `caller` — none in `_DI_ONLY_KEYS`. The moment one is
added to `external_import.invoke`'s signature, an MCP caller can inject it via `input_payload` and the
suite stays green. This is the M1 defect class ("the guard was right, the parameter inventory was
incomplete") on its next occurrence.

**Fix direction:** one test asserting `_allowed_input_payload_keys(kind) == <exact frozenset>` for all
13 kinds, so any adapter signature change becomes a deliberate, reviewed test edit. This is also what
converts my S1 negative from point-in-time to durable.

---

## SEC-6 — MED — TERRA-4's preflight-side check has zero coverage (mutation M5b SURVIVED)

File: `src/research_foundry/operator_mcp/server.py:693`.

Replacing `if set(payload) - _allowed_input_payload_keys(operation_kind):` with `if False:` leaves
313/313 green. I then established empirically what the check is worth: it is **hygiene, not an
authorization bypass**. With it neutralized in a scratch copy, a DI-poisoned confirmation is
unconsumable in both directions — replaying the same payload trips the execute-side allowlist
(`payload_too_large`), and dropping `now` breaks the digest (`confirmation_mismatch`). Even with
*both* guards neutralized, a caller-supplied `now` arrives over JSON as a `str` and dies as
`internal_error` (`AttributeError`) before reaching expiry logic. So `server.py:259-267`'s comment
calling caller-supplied `now` "an authorization bypass" **overstates it** for this transport.

The check is still worth keeping — it is one of the free levers on SEC-2's write-amplification path
(without it, preflight mints and durably persists confirmations that can never be consumed).

**Fix direction:** add the missing regression test, and soften the `server.py:259-267` comment to what
was actually demonstrated (digest poisoning + unconsumable durable rows), not an expiry bypass.

---

## SEC-7 — MED — `run.verify`'s path parameters are unusable over MCP; the F5 guard is dead code on this route

File: `src/research_foundry/services/operator_mcp_adapters/verify_bundle.py:513,517`.

MCP delivers `input_payload` values as JSON **strings**; `report_path`/`claim_ledger_path` are annotated
`Path | None` and are never coerced, so `_explicit_path_within_run(run_root, "<str>")` raises
`AttributeError: 'str' object has no attribute 'is_absolute'` for **every** value.

```
report_path = <the run's own reports/report_draft.md>  -> internal_error   (legitimate value!)
report_path omitted                                     -> ok=True, passed=true
report_path = /etc/passwd | ../../../../etc/passwd | symlink-out | NUL | newline -> internal_error
observed filesystem paths outside the workspace: NONE
```

Security-safe today, but **by type crash, not by the guard**. The consequence for this gate: no green
test on the MCP route can attest to F5, and the day someone adds `Path(report_path)` coercion, an
untested containment guard goes live. **Fix direction:** coerce at the adapter boundary and make the
existing containment check actually execute, with a test on the MCP route asserting both the
legitimate-in-run accept and the escape deny.

---

## SEC-8 — LOW — unqualified "provably cannot execute" claim sites, and one overloaded use of the phrase

`docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md:202,343,534`;
`.claude/worknotes/research-foundry-operator-mcp/m2-implementer-contract.md:14`;
`m2-delivery-notes.md:12`. None carries the TERRA-5 scoping caveat that `server.py:123-153` now
carries. Separately, `tests/integration/test_operator_mcp_server.py:710-712` reuses the exact phrase
"provably cannot execute" for a *different* guarantee (no-effect-without-confirmation), so a reader
cannot tell which property is being reasserted. **Fix direction:** one scoping sentence at the
milestone claim site, and disambiguate the test comment.

---

## SEC-9 — LOW — `payload_too_large` is overloaded across five unrelated conditions

`server.py:634,694`; `operator_mcp_policy.py:1263,1268,1281,1287`. The same reason code now covers:
oversized bytes, excessive nesting depth, a forbidden DI/reserved key, >20 targets, and a malformed
`idempotency_key`. An **authorization-probing request** (injecting `now`) is indistinguishable from a
benign size error both in the envelope and in the server log. The closed enum is frozen by contract, so
the envelope is arguably correct — but the *detection* gap is not. **Fix direction:** log the rejected
key names at `server.py:634` so the security-relevant case is distinguishable operationally. (I also
note SEC-4's vacuity was *caused* by this overload — two guards sharing a reason code made a test
unable to tell them apart. Reason-code reuse has a testability cost, not only an ergonomic one.)

---

## SEC-10 — LOW — two preflight/adapter asymmetries in the F2.2 bounds

`writeback_preview.py:124,230` vs `server.py:737-748`. (a) The `>32 raw targets` cap exists only in the
adapter; preflight dedups *before* validating, so 33 duplicate names mint a usable confirmation
(harmless — the transport's 64 KiB cap bounds it and the digest still matches — but the two layers are
not equivalent). (b) `_MAX_TARGET_NAME_LENGTH` (64) is an unreachable condition: any name longer than
64 chars is by definition outside the 6-member vocabulary, so the membership clause always fires first.
Dead condition, not a hole.

---

## Verified clean

Everything below I checked and it held on this tree.

**Fixes that mutation-KILLED with a purpose-built test (S3):** TERRA-1 persistence (M1); the
`now=ids.now()` clock-source companion (M2); TERRA-2 `writeback_targets` threading (M3); TERRA-3
`retrieval_limits` in the digest (M4); TERRA-4 execute-side DI rejection (M5); TERRA-7 target bounds
(M7) *and* its vocabulary clause alone (M7b); TERRA-8 staging namespace (M8) *and* the sharper M8b —
replacing the digest with a constant `"fixed"` still fails, so the test genuinely binds the namespace
to operation identity rather than to "some subdirectory exists"; F1.2's preflight vocabulary check (M9).

**Preflight→execute seam (S4), all zero-effect-proven by row deltas on `operations`/`action_receipts`/
`terminal_receipts` plus on-disk run counts:** a confirmation cannot be consumed with a changed
`effective_sensitivity`, changed `policy_snapshot_version`, reversed `targets` order, a different
operation kind, or a different run — every case `confirmation_mismatch`, zero effect. Hand-editing any
of ten fields of the presented record is structurally inert (the persisted record is authoritative and
re-verified under `BEGIN IMMEDIATE`); tampering with `confirmation_id` fails closed as
`confirmation_missing`. Wrong token, mismatched token/record pair, empty token, and empty record all
deny with zero effect. TTL holds (`confirmation_expired` at +5m01s on a never-consumed token); the
NEW-7 future-`issued_at` anti-forgery clamp holds; the H4 far-future-`expires_at` clamp holds. Exact
replay is an idempotent success returning the *same* `operation_id` with no second `operations` row;
an already-consumed confirmation presented for a different request denies `idempotency_conflict`.
Persistence failure (`ConfirmationPersistenceError`, `sqlite3.IntegrityError`, and a `RuntimeError`
carrying a fake absolute path + "Traceback") each yield a byte-identical **248-byte** redacted
`internal_error` envelope — no path, no exception text, no token, no `opc_` id — with **no half-state**
(zero rows, no db file, no stale lock; the next preflight succeeds normally). Policy bounds hold: 21
targets → `payload_too_large`, a 257-char `target_ref` → `target_invalid`, `../../../etc/passwd` as a
`target_ref` → `target_invalid`.

**Preview seam negative evidence, re-proven on the current tree (S5)** — 13 outcome paths driven
through the real `server.call_tool` dispatch (happy / repeat / missing bundle / `unsupported_target` /
review-required / degraded / the three new `target_invalid` denials at both the adapter and preflight /
`dry_run`), each with 13 spies armed to raise on touch (`IntentTreeClient.from_config`,
`ArcClient.from_config`, `get_notebooklm_client`, `get_meatywiki_client`, `urllib.request.urlopen`,
`urllib.request.Request`, `socket.socket`, `socket.create_connection`, `http.client.HTTPConnection`,
`subprocess.Popen`, `subprocess.run`, `os.system`, `os.popen`): **zero spies fired on every path.**
Full workspace tree diffed before/after each call: every created file matched
`^runs/.*/staging/writeback_preview/[0-9a-f]{64}/`, `outside = NONE` on all 13, and two operations on
the same run landed in disjoint 64-hex subdirectories. Denial paths created zero files.

**Surface and startup:** exactly 14 registered tools, set-equal to `operator_mcp_policy.TOOL_NAMES`,
**zero** overlap with `knowledge_mcp`'s 8; every advertised schema `additionalProperties is False`; no
wildcard or dynamic registration path. Importing `operator_mcp.{server,process}` and calling
`build_server(paths=…)` fire no socket/subprocess spy, create no thread, write no file, and emit
nothing on stdout/stderr. Under a `sys.meta_path` `find_spec` blocker for `mcp` in a child interpreter:
`import research_foundry.operator_mcp.server` succeeds, `build_server()` raises the clear RuntimeError
naming the extra, and `research_foundry.cli:app() --help` exits **0**. `flake8 --select=E9,F63,F7,F82`
on `src/research_foundry` is clean.

**S1 (see above):** 7 modules / 12 operation kinds re-audited; the F2.1 negative confirmed.

---

## Note on a hazard for whoever re-runs this

Two spy-harness traps produced false results before I corrected them, worth carrying forward: a
`socket.socket` spy must be a **subclass** (a plain function breaks stdlib `ssl`'s
`class SSLSocket(socket)` at import), and `asyncio.run()` inside an armed window fires `socket.socket`
from the event loop's own `socketpair` self-pipe. Also, a `/tmp` scratch copy of `src/` needs
`schemas/`, `config/`, `templates/`, and `foundry.yaml` copied to the scratch **root**, because
`paths.distribution_root()` is `Path(__file__).resolve().parents[2]`.

SECURITY GATE VERDICT: CHANGES_REQUESTED (1 blocking)
