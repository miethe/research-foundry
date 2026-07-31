# M2 security RE-GATE (re-pass 1 of 2) — Operator MCP, fix cycle 2 tree `5025e97`

Reviewer: senior-code-reviewer (Mode E). Predecessor ledger: `.claude/findings/m2-security-gate.md`
(SEC-1..SEC-10, verdict CHANGES_REQUESTED / 1 blocking on `b4c335c`). No repo file was modified by
this review; no git write command was run. All mutation used a `/tmp` scratch tree proven live by a
`research_foundry.__file__` sentinel plus a deliberate `RuntimeError` negative control, with
`__pycache__` purged and `PYTHONDONTWRITEBYTECODE=1` on every iteration. Every attack below was
driven through the real `build_server()` → `server.call_tool("operation.preflight", …)` →
`server.call_tool(<kind>, …)` route with a genuinely minted confirmation, one fresh isolated tmp
workspace per case, and recording (never blocking) wrappers on `open`, `Path.open/exists/is_file/
read_text`, `os.scandir`, `os.replace`, `shutil.move`, and `urllib.request.urlopen`.

The prior gate's "Verified clean" sections stand; I found no reason to doubt them.

---

## R1 — SEC-1 (`packet_dir`): **NOT CLOSED.** The fix closes the reported vectors and opens a new one.

What the fix genuinely closes, re-run case by case (all `internal_error`, **zero** out-of-root
filesystem touches): `/etc`; `~/.ssh`; `/var/root`; a symlink planted inside the workspace pointing
to `/etc` (`.resolve()` follows it before the containment test); `<root>/../../etc/passwd`;
`../../etc`; and — decisively for the classic `str.startswith` bug — the prefix-sibling
`<root>EVIL` in both direct and `<root>/../<rootname>EVIL` form, with a valid packet planted inside
it so a containment failure would have been visible. `_resolved_within`
(`external_import.py:115-139`) uses `Path.resolve()` plus `root_resolved in effective.parents` —
not `str.startswith`. **Oracle:** every one of those nine denials is byte-identical (same
`isError=true`, same `reason_code="internal_error"`, same fixed message from `_SAFE_MESSAGES`), so
the predecessor's four-way `unsafe_member_path`/`required_member_missing`/
`unsupported_schema_version`/`internal_error` existence oracle is genuinely collapsed **for paths
that are actually denied**. Controls all pass, no over-blocking: legitimate in-workspace absolute
path, a workspace root reached through a symlink, and a benign in-root `..`
(`<root>/runs/../packets/p1`) all still succeed.

**But the check and the use disagree about what a RELATIVE path means.** See SEC2-1 — reproduced
live, on this tree, through the real MCP route.

## R2 — the path-containment sweep: **complete for the class it enumerated; it missed two other classes.**

I re-derived the caller-reachable surface myself (`_allowed_input_payload_keys` over all 13 kinds,
plus every value the server threads explicitly: `targets[].target_ref`, `idempotency_key`,
`workspace_id`, `dry_run`) and traced each to a filesystem sink one and two hops below the adapter.

**The 9 claimed fixes are all present, correctly ordered before the read, and fail closed** —
`external_import.target_run_id` (`:164`), `writeback_preview.run_id` (`:185`),
`source_ingest.run_id` (`:166`), `source_ingest.locator` (`:323-327`), `run_plan.intent_id`
(`:180` pre-auth **and** `:310` inside `_run()`), `swarm_start.run_id` (`:202`),
`swarm_start.intent_id` (`:248`), `research_stages.run_id` (`:246`), `verify_bundle.run_id`
(`:248`). Empirically attacked `writeback.preview.run_id`, `run.extract.run_id` and
`external_report.import.target_run_id` with `../..`, `/etc`, `..%2f..`, absolute paths, an
in-`runs/` symlink to `/etc`, and a nonexistent-but-pattern-valid id: all denied
(`target_invalid` at the capability stage, or `guard_review_required`/`not_found` at execute),
**zero** out-of-root touches, and symlink-vs-nonexistent produce identical envelopes — no oracle.
Controls (a real run) still work in all three.

**Drift check on the duplicated helper: none.** All six `_resolved_within` copies plus
`verify_bundle._explicit_path_within_run` are logically byte-identical; no copy uses
`str.startswith`, `strict=True`, or probes `.exists()` on an out-of-root candidate. Only a log
string and one local variable name differ.

**The three "traced as safe" rows hold**, re-verified from source rather than from the docstrings:
`run.claim_map.intent_id` is written only into ledger metadata dicts and never reaches
`planning.load_intent`; `run.synthesize.model_profile` has zero body references in `synthesis.py`;
`swarm.start.adapter_ids` resolves via `adapters/base.py:111-112` `_REGISTRY.get(...)`, a dict
lookup (confirmed empirically: `get_adapter('../../etc/passwd') -> None`). `job.status/cancel/
resume`'s `operation_id` reaches no path sink (`grep` for `Path(`/`open(`/`glob(` in
`job_lifecycle.py` returns zero hits). Also cleared: `source.ingest.title` (`slugify` strips every
non-alnum char — `slugify('../../../../etc/passwd; rm -rf /') -> 'etc_passwd_rm_rf'`),
`workspace_id` (digested before use — `self.workspace_key = _digest(workspace_id)`),
`idempotency_key`, `writeback.preview.targets` (bounded to the closed 6-name vocabulary before it
becomes a filename), and the staging `operation_ref` (always `ctx.canonical_digest()`, re-validated
against `^[A-Za-z0-9_-]{1,128}$`). `run.plan`'s `profile`/`project`/`retrieval_policy` never index a
config file by name.

**No 11th instance of the enumerated class exists.** The sweep's own count is right. What it missed
is that it enumerated path-shaped *values* and never questioned (a) the *anchor* those values are
resolved against downstream (SEC2-1) or (b) the *scheme* bypass it wrote into its own guard
(SEC2-2). Both are one hop below the adapter — the same place every prior miss in this workstream
has lived.

## R3 — SEC-4 (vacuous depth-cap test): **CLOSED.** All four mutations killed.

Guard at `server.py:448-449`. Scratch harness proven live (sentinel + negative control) before any
result was trusted. `M6` (delete the `_mapping_depth(...) > _MAX_ARGUMENT_DEPTH` block) →
`AssertionError: assert 'internal_error' == 'payload_too_large'`. `M6a` (neuter to `> 10**9`) →
identical failure. `M6b` (hoist the name/size checks back outside the `try`) →
`test_transport_size_check_exception_maps_to_internal_error_not_uncaught` fails with the raw
`RuntimeError: boom` escaping `asyncio.run`. **COMBINED (M6 + neuter the execute-side allowlist
guard simultaneously)** — the predecessor's own vacuity detector — still fails with the same
`internal_error != payload_too_large`, proving the depth cap now has genuinely independent
coverage. `retrieval_limits` is confirmed a real `run.plan` parameter (`run_plan.py:220`, in
neither `_SERVER_SUPPLIED_KEYS` nor `_DI_ONLY_KEYS`), so no other guard can answer first. The test
also carries a direct `_mapping_depth` assertion. One nuance for the record: the kill works because
*no other path returns `payload_too_large`* once the cap is gone (removing it makes `json.dumps`
raise `RecursionError`, which `_check_transport_payload_size` swallows and falls through to
dispatch), not because a second guard cleanly reproduces the denial — slightly less robust than an
independent positive, but genuinely discriminating. I could not construct an input that leaves the
test green with the cap removed.

## R4 — SEC-5 (allowlist): **CLOSED AS SCOPED — but the mechanism is still a deny-list.**

`_allowed_input_payload_keys` (`server.py:467-486`) is `inspect.signature(fn).parameters` minus
`_SERVER_SUPPLIED_KEYS` minus `_DI_ONLY_KEYS`. That is signature-minus-denylist, not a positive
enumeration — the fix note's "Code mechanism unchanged" is accurate, and the pinning test's own
docstring calls it a "POSITIVE derivation" while simultaneously conceding a new parameter "becomes
silently caller-reachable". **Proven decisively:** adding `resolver: Any = None` to
`external_import.invoke`'s signature in a scratch copy made `resolver` appear in the live allowlist
with no other change, and an MCP call supplying `input_payload.resolver` delivered
`'INJECTED_DI_PAYLOAD_VALUE'` into the adapter's real kwargs (spy wrapped with `functools.wraps` so
the derivation stayed honest). So a new DI parameter *is* caller-reachable at runtime.

**The compensating test is real, however.** `test_allowed_input_payload_keys_is_pinned_per_kind`
(`test_operator_mcp_server.py:341-413`) pins a **hardcoded literal** `frozenset` per kind with
exact `==` equality — not recomputed from `inspect.signature`, so it is not the tautology its
predecessor was — and it FAILED correctly on the decisive drift mutation
(`Extra items in the left set: 'resolver'`). The import-time invariant also fails loudly: removing
`writeback.preview` from `_ADAPTER_INVOKE_TARGETS` raises at import naming the diff.

Verdict: accepted as scoped, because the gate's own fix direction asked for exactly this test. But
record honestly that this is a **test-time tripwire, not a runtime control** — its protection is
entirely contingent on the suite being run and its failure honored before deploy.

## R5 — SEC-2 (per-workspace mint cap): sound per-instance, **but the residual is materially understated.** See SEC2-3.

Implementation read and probed (`server.py:281-282`, `640-664`, call site `879-881`). The bound is
real on its own axis: 60 preflights → exactly 20 allowed, 20 rows, first denial on the 21st call,
and a denied call writes **zero** rows (check is strictly before `mint_confirmation`/
`record_confirmation`). No caller-reachable key evasion: the bucket key is
`ctx.identity.workspace_id`, sourced only from `foundry.yaml` (`operator_mcp_policy.py:1120-1186`,
"the ONLY identity source"); `_preflight_tool` has no `workspace_id` parameter, and smuggling one
via `input_payload` is rejected `payload_too_large` by the F1.3 allowlist. No race: 60 concurrent
threads → 20 rows; 60 `asyncio.gather` tasks → 20 rows; zero overshoot. The window rolls forward
correctly under a real clock (+61s reopens exactly one slot) and is deterministic under the pinned
test clock — both directions checked. No reclamation exists in `operator_operation_service.py`
(all 20 `DELETE` hits are `BEFORE DELETE … RAISE(ABORT)` immutability triggers on other tables;
`confirmations` has none, so the deferred sweep is unobstructed). No over-blocking: nothing in the
CLI, API, runs-viewer, or workflows issues preflight bursts anywhere near 20/60s.

## R6 — SEC-3 / SEC-6 / SEC-8 **CLOSED**; SEC-7 **NOT CLOSED**.

**SEC-3 — closed.** No unqualified "(zero effect)" claim remains; `server.py:49-50` and
`__init__.py:20` both read "zero effect beyond one durable `confirmations` row".
`test_preflight_allow_mints_confirmation_with_zero_effect` (`:643-708`) now snapshots the
`confirmations` table and asserts `len(rows_after) == len(rows_before) + 1` **and**
`new_rows == [(confirmation_id, "issued")]` — exactly one row, id-matched, not `>= 1` — while
preserving the original byte-identical `registries/`/`runs/` assertions.

**SEC-6 — closed.** `test_preflight_di_only_input_payload_key_denies_before_minting_with_zero_effect`
(`:416-465`) spies `policy.mint_confirmation`, asserts `mint_calls == []`, and asserts zero new
rows. The "authorization bypass" language is softened at `server.py:301` and `:707` to
digest-poisoning / write-amplification, matching what was actually demonstrated.

**SEC-8 — closed.** All six `"provably cannot execute"` sites (plan `:202,205,346,540,544`;
`m2-implementer-contract.md:14`; `m2-delivery-notes.md:12,14`) now carry the TERRA-5 scoping
caveat, and `test_operation_tool_without_confirmation_denies_confirmation_missing`
(`:988-1000`) explicitly disambiguates its docstring from the transport-guard claim.

**SEC-7 — the coercion is real and the guard is now live** (the legitimate in-run report, absolute
and relative, verifies successfully where it previously crashed; `/etc/passwd`, `../../../../etc/
passwd`, an in-run symlink to `/etc/passwd`, and the prefix-sibling `<run_root>EVIL/report.md` with
a real file planted are all denied with zero touches). **But the now-reachable guard is bypassable
via the same anchor mismatch, and here the bypass achieves an out-of-root WRITE.** See SEC2-1.

## R7 — inverted tests: **CORRECT INVERSION.** No regression is being papered over.

`git show 5025e97 -- tests/unit/test_operator_mcp_adapter_external_import.py` shows both tests
changed exactly one line — `_blocked_packet(tmp_path)` → `_blocked_packet(tmp_foundry.root)`. Every
assertion in both is byte-identical before and after (9 field-parity assertions in
`test_invoke_result_matches_direct_import_call`; `call_count == 1` + `replayed is True` in
`test_exact_retry_does_not_duplicate_import_receipt`). Neither test's assertions reference where
`packet_dir` lives — the out-of-workspace placement was incidental fixture convenience, not the
property under test. On intent: the **CLI** does accept an arbitrary `--packet-dir`
(`cli_commands.py:1136-1194`, documented in `docs/user/external-research-interchange.md`), but that
is a human with their own filesystem access — a different trust boundary. I found no doc, PRD, or
plan text extending that to the MCP adapter, and the M2 AC (plan `:564-565`) forbids exactly the
behavior the original fixtures pinned. Inversion is the right remedy here.

**Independent audit of every other pre-existing test touched** (`git diff b4c335c..5025e97 -- tests/`):
six of eight files have **zero deletions** (pure additions). Beyond the two fixture moves, only
three pre-existing tests changed and all three are docstring-only; plus the two deliberate,
disclosed rewrites — SEC-4's depth-cap test (strengthened, see R3) and SEC-3's zero-effect test
(widened; all original assertions preserved verbatim, new ones additive). `grep` over the test diff
for `skip`/`xfail` and for removed `assert … ==` lines returns **zero** matches. Nothing was
weakened.

## R8 — new guards: no over-blocking, no new leak.

A legitimate bare run_id passes (`_resolved_within(paths.runs, Path("run_20260731_abc")) -> True`).
The **data-plane split is not a symlink hazard** — the data plane lives physically inside the
working tree under a second `--git-dir`, `runs/` is a plain directory, and because both sides
resolve through the same `root` object there is no asymmetric-resolution path that could deny a
legitimate in-root run. No guard calls `.exists()`/`.stat()` on a candidate, so there is no timing
or existence oracle from the guards themselves; each runs after authorization but before the
expensive canonical-service call. Every new `RuntimeError` message is a static string with no path
interpolation, and all of them funnel through `base.py:359-369`'s single `except Exception` into the
fixed `_SAFE_MESSAGES` envelope — I confirmed the emitted envelope carries no `detail`,
`operation_id`, or `receipt_ref` and is indistinguishable from any other `internal_error`.
`_logger.warning` does embed caller-supplied values, but nothing wires log records into the MCP
response. Clean.

---

# New findings

## SEC2-1 — **BLOCKING** — check/use path-ANCHOR mismatch: relative paths pass containment trivially, then are read (and written) relative to the process CWD

Files: `external_import.py:115-139, 322-333`; `source_ingest.py:101-123, 323-328`;
`verify_bundle.py:280-315, 555-575`; consumers `external_research_interchange.py:846-859`,
`source_cards.py:222`, `verification.py:778-799` and `verification.py:1402-1408`.

**Defect.** Every containment helper resolves a **relative** candidate as
`(root / candidate).resolve()` — anchored at the authorized root. The adapter then forwards the
**original raw string** to the canonical service, which resolves it against the **process CWD**.
Two anchors, one check. Any relative string containing no escaping `..` is therefore *trivially*
"contained" by the check's own arithmetic — including totally mundane ones — and is then consumed
from a location that was never authorized. Nothing in this codebase pins the server's CWD to
`FoundryPaths.root`; an MCP server runs with whatever CWD its client launched it from.

**Evidence — three instances, all reproduced live through `server.call_tool` with a real confirmation:**

1. `external_report.import.packet_dir` → `inspect_packet`'s `Path(packet_dir)`.
   `packet_dir="."` (no `..`, no setup): `isError=false`, `ok=true`, a real durable receipt, and
   **632 real host paths recursively `os.scandir`'d** — a full walk of the live repo tree including
   `.venv/lib/python3.14/site-packages/…` and `.github/workflows`. With a packet planted at a
   CWD-relative name outside any declared root, the returned receipt's `block_reason`/`complete`
   genuinely reflect that outside packet's structure.
2. `run.verify.report_path` / `claim_ledger_path` → `verification._resolve_explicit_path`, which
   after `run_relative.exists()` fails falls back to `Path.cwd() / p` (`verification.py:796-798`).
   Planted canaries at the process CWD: `report_path="pwn_report.md"` → `ok=true`, and the
   response's own `unsupported` list contains the literal planted canary text (**content read**,
   not a stat). `claim_ledger_path="pwn_ledger.yaml"` → `verification.py:1402-1408` **WROTE** to it,
   flipping a planted `UNTOUCHED_SENTINEL` to `verification_status: failed`, confirmed by
   `Path.open[w]`, byte-diff, and mtime. A control where the run-relative candidate *does* exist
   shows zero touches to an identically-named CWD shadow — the fallback is reached exactly when the
   run-relative path is absent. `_explicit_path_within_run`'s own docstring claims it "does not
   honor `verify_report`'s own cwd-relative fallback … at all". **That claim is false**; the guard
   returns a bool and never rewrites the path, so it cannot honor or block anything.
3. `source.ingest.locator` → `source_cards.py:222` `Path(locator).exists() and .is_file()`.
   With the process CWD moved to an unrelated directory and `secret.txt` planted there,
   `locator="secret.txt"` (no `..`) → `_resolved_within` returns `True`, `isError=false`,
   `extraction_status="full_text"`, and the canary string appears **verbatim** in the source card
   written into the workspace. `locator="sub/secret.txt"` works identically.

**Correctly unaffected:** every `run_id`/`target_run_id`/`intent_id` guard. Those consume via
`paths.run_paths(run_id)` → `self.runs / run_id` (`paths.py:226-230`), which is anchored at the same
absolute root the guard used. Verified in source and empirically (zero out-of-root touches on all
denial paths for those three adapters). The finding is precisely scoped to the four *explicit-path*
parameters.

**Second-order:** this re-opens an existence oracle the fix had closed. For absolute out-of-tree
candidates the envelopes are byte-identical (no oracle). For **relative** candidates, `ok=true`
versus `internal_error` is itself a working existence oracle over the entire CWD-relative filespace.

**Fix direction (one shape closes all four parameters):** make the helper *resolve-and-substitute*,
not validate-only — return the resolved, root-anchored `Path` and have the adapter forward **that**
to the canonical service, never the caller's raw string. (Alternatively, reject relative values
outright for `packet_dir`/`locator`/`report_path`/`claim_ledger_path` and require absolute
in-workspace paths.) Whichever is chosen, add a regression test that plants a file at a CWD-relative
name and asserts it is never touched — and mutation-verify it, since the current tests all run with
CWD inside the tree and cannot see this.

This falsifies the same M2 acceptance criterion SEC-1 did (plan `:564-565`, "no … arbitrary-path
reach from any registered handler").

## SEC2-2 — **BLOCKING** — `source.ingest` `file://` locator is an unrestricted local file read, by design of the guard's own bypass

Files: `source_ingest.py:126-135` and `:323`; `source_cards.py:90-92` and `:111-126`.

**Defect.** `_looks_like_url` returns True for scheme `file`, and the containment guard is skipped
entirely when it does — justified in-comment on the grounds that "its fetch … goes over the
network, a separate concern". `file://` is not a network scheme. `source_cards._fetch_url` then
calls `urllib.request.urlopen(url, timeout=…)` on the raw caller string with **no scheme
allowlist anywhere on the path** (verified across every `urlopen(` call site in the repo), and
urllib's built-in `FileHandler` reads local files.

**Evidence** (real MCP route, genuine confirmation, `content` omitted, `fetch=True`):
`locator="file:///etc/passwd"` → `isError=false`, `extraction_status="full_text"`,
`degraded=false`; `urlopen` called with `file:///etc/passwd`; `builtins.open('/etc/passwd')` fired.
Decisive: the assertion ledger's edition file is **byte-identical to `/etc/passwd`** —
`diff .../editions/sed_.../content.bin /etc/passwd` → identical, 9344 bytes both — i.e. the full
file, every account line included, durably persisted in a ledger-backed artifact. Variants
`file://localhost/etc/passwd`, `FILE:///etc/passwd` (urlparse lowercases the scheme), and
`file:/etc/passwd` (single slash) all succeed identically. `fetch=False` correctly never reads —
the bypass is fetch-gated, not locator-gated.

Note: `_looks_like_url` and `source_cards._is_url` never disagree (tested over 14 candidates
including `//etc/passwd`, `C:/etc`, `data:`, `ftp://`, `file:`, `http:/etc/passwd`), so this is not
a two-checks-diverging bug — both correctly agree `file://` is "a URL", and that agreement is
exactly what routes it around containment.

**Fix direction:** restrict `_fetch_url` to an explicit `("http", "https")` scheme allowlist before
`urlopen`, and drop `file` from both `_looks_like_url` and `_is_url` so a `file:` locator is either
refused or routed through `_resolved_within` like any other local path. Pin with a test asserting
`file:///etc/passwd` is denied and that `urlopen` is never called for a non-http(s) scheme.

## SEC2-3 — HIGH — the SEC-2 partial bound is sound per-instance, but restart evasion achieves a HIGHER write rate than the pre-fix baseline; the residual is understated

`build_server()` costs **≈12-18 ms**. Five fresh instances × 20 preflights → **100 rows** (vs 20 if
state persisted). Measured achievable full-cycle throughput under restart evasion:
**≈83-87 confirmations/sec ≈ 34-48 MiB/min**, against the predecessor's measured pre-fix baseline of
**25.5 MiB/min**. So under the one evasion its own authors disclosed, the cap delivers **no net
reduction in durable write rate at all** — arguably a slight increase. (Caveat: measured with a warm
interpreter; a real attacker forced to spawn OS subprocesses pays more, but `build_server()` is only
~5-6% of full-cycle time, so the ceiling stays high.)

Deferring the store-side fix remains acceptable — `operator_operation_service.py` was legitimately
off-limits. **The description is not.** `m2-fix-leg-1-completion.md`'s residual section is
qualitatively honest (restart-reset, no eviction/dedupe/sweep) but omits that the reset costs
milliseconds and that the achievable rate meets or exceeds the pre-fix number. As written it reads
as an improvement; it is not one against this vector. **Fix direction:** correct the residual text
with these numbers and carry them into the ITT node, so whoever picks up the store-side work knows
the current bound buys nothing against a restarting caller. Also file alongside it:
`_preflight_mint_history` has no bound on its number of distinct keys (dormant today, since
`workspace_id` is config-resolved and not caller-supplied — it would activate the moment identity
becomes caller-influenced or multi-identity).

## SEC2-4 — MED — phantom effect: a `source.ingest` disk write persists on a call reported as `internal_error`

`source_card_id` is deterministic (`src_{date}_{slug}_{hash(title, locator)}`, no randomness). Two
ingests with the same title+locator collide: the second call's `_run()` executed `ingest_source` and
**overwrote the first call's already-written card on disk**, and only afterwards did
`operator_receipt_service` reject it as a duplicate `effect_receipt` (same `effect_digest`, different
operation), surfacing as `internal_error`. The disk mutation survived the reported failure. This
contradicts the family's own "a denial has zero effect" posture and is new — not previously filed.
**Fix direction:** either make the effect-receipt uniqueness check precede the write, or make the
write transactional/rolled-back on receipt rejection; pin with a test asserting the first card is
byte-unchanged after the colliding second call.

## SEC2-5 — MED — `source.ingest` with `content` supplied can never be consumed on this transport

Preflight canonicalizes the caller's raw `content` (an allowlisted key, since it is a real
`invoke` parameter), but `invoke` rebuilds its own `input_payload` substituting `content_digest`
(`source_ingest.py:265-282`) before computing the execute-side digest. The two canonical shapes can
never match → **every** content-bearing `source.ingest` denies `confirmation_mismatch`, zero effect.
Supplying `content_digest` directly is rejected by the F1.3 allowlist (it is not a parameter name).
Independently reproduced by two probes. Functional rather than security-critical, but it means the
`content` branch has zero real coverage on the sanctioned route — and it is the accident currently
hiding the unconditional `Path(locator).exists()/.is_file()` stat at `source_cards.py:222` (a minor
existence oracle that runs regardless of whether `content` was supplied). **Fix direction:** make
preflight and execute canonicalize the same shape (digest `content` at the server boundary), then
re-examine that stat.

## SEC2-6 — LOW — the containment helpers catch only `OSError`; a NUL byte raises `ValueError` out of a function documented to always return `bool`

`Path("run_root/evil\x00.md").resolve()` raises `ValueError: lstat: embedded null character in
path`, which `except OSError` does not catch. Absorbed safely by the generic `except Exception` one
layer up (verified: clean `internal_error`, no leak), so not exploitable — but the guards' own
stated invariant ("never a permissive default", always returns a bool) is false for this input
class. **Fix direction:** `except (OSError, ValueError)` in all seven copies.

## SEC2-7 — LOW — SEC-7's `except TypeError` coercion block is dead code on the sanctioned route

`12345`/`None`/`[]`/`{}`/`True` as `report_path` all die at `confirmation_mismatch` before `_run()`
executes, because `invoke_verify` stringifies the value (`str(report_path)`) when building the
execute-side digest while preflight hashed the raw JSON type. Safe, but safe by side-channel rather
than by the handler — the same shape as the original SEC-7 defect. Worth one line in the docstring
so the next reader does not mistake the block for exercised coverage.

## SEC2-8 — LOW — `schemas.default_registry()` is a process-wide `@lru_cache(maxsize=1)` resolved from ambient CWD

`schemas.py:112-116` resolves via `FoundryPaths.discover()` from whatever CWD the process started
in, then caches for the process lifetime regardless of any explicit `paths=` passed elsewhere
(observed as `foundry.yaml` probes walking up to `/`). Not attacker-directed, but it means schema
validation in a long-lived server is pinned to an ambient tree — same CWD-coupling root cause as
SEC2-1, and worth fixing in the same pass. Flagged, not blocking.

---

# Confirmed closed

- **SEC-3** — docstrings corrected; the zero-effect test now asserts exactly one new `confirmations` row.
- **SEC-4** — depth-cap test non-vacuous; M6, M6a, M6b and the COMBINED vacuity detector all killed.
- **SEC-5** — closed as scoped: the pinning test is a hardcoded, non-tautological, exact-equality pin
  for all 13 kinds and fails correctly on drift. Recorded caveat: the mechanism is still
  signature-minus-denylist, so this is a test-time tripwire, not a runtime control.
- **SEC-6** — preflight-side check now covered; mint spy proves it is never reached; language softened.
- **SEC-8** — all six claim sites scoped; the overloaded test docstring disambiguated.
- **The 9 swept `run_id`/`intent_id`/`target_run_id` instances** — guards present, correctly ordered,
  fail closed, no drift across seven copies, no oracle, controls unaffected.
- **R7 test inversions** — correct inversion, not a papered-over regression; no other pre-existing
  assertion was weakened anywhere in the diff.
- **R8** — no over-blocking, no information leak from the new guards.

**Not closed:** SEC-1 → SEC2-1. SEC-7 → SEC2-1. SEC-2 → remains open by design, with SEC2-3.
**Not re-examined** (LOW, unassigned this cycle): SEC-9, SEC-10.

# Priority for fix cycle 3

**Must fix to be correct:** SEC2-1, SEC2-2. Both are live, unauthenticated-by-path arbitrary local
file reads from a registered handler (SEC2-1 additionally achieves an out-of-root *write*), and both
falsify the M2 acceptance criterion as written. They share one root cause with the prior round —
enumerating the named class and stopping one hop above the consumer — so fix cycle 3 should attack
*every* caller-supplied value at its **consumer**, not at the adapter.

**Should fix:** SEC2-3 (at minimum correct the residual text with the measured numbers), SEC2-4.

**Would be nice:** SEC2-5, SEC2-6, SEC2-7, SEC2-8.

SECURITY RE-GATE VERDICT: CHANGES_REQUESTED (2 blocking)
