---
title: "In-flight findings: Research Foundry Operator MCP"
schema_version: 2
doc_type: report
report_category: findings
status: in_progress
created: 2026-07-28
updated: 2026-07-29
feature_slug: research-foundry-operator-mcp
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
owner: nick
tags: [findings, security, operator-mcp, governance]
---

# In-flight findings — Research Foundry Operator MCP

## FIND-P1 — OPM-1.G security gate: CHANGES_REQUESTED (round 1)

Source: mandatory security reviewer pass on the P1 exact tree (plan §"Reviewer Gates":
"Security review is mandatory for P1 identity/confirmation").
Target file unless stated: `src/research_foundry/services/operator_mcp_policy.py`

Status legend: `open` / `fixed` / `wontfix-justified`

### CRITICAL

| ID | Finding | Location | Required fix | Status |
|---|---|---|---|---|
| C1 | `authorize_operation()` discards `ConfirmationVerification.outcome` and returns only `verification.decision`. For `exact_replay` that decision is `PolicyDecision(True, "confirmation")` — a frozen dataclass `==`-equal to the `accepted` decision. A consumed token replayed through the documented execute-time entry point therefore authorizes a **new effect**. Defeats OQ-2 one-time-use at the only API claiming completeness. | :558-561, :691, :715 | Return the `ConfirmationVerification` (or a `PolicyDecision` carrying the outcome, e.g. `stage="confirmation_exact_replay"`) so callers cannot conflate the two. Make "exact replay returns the prior receipt, never a new effect" normative in the docstring. | fixed |

### HIGH

| ID | Finding | Location | Required fix | Status |
|---|---|---|---|---|
| H2 | `PolicyContext.effective_sensitivity` is an unvalidated `str` defaulting to `"public"`, forwarded verbatim to `GuardContext`. `guard_check` matches by exact set membership with no normalization and **no unknown-label fallback → fails open**. `"Work_Sensitive"`, `"work_sensitive "`, `""`, or a homoglyph disables every governance rule. The read-only plane (`knowledge_access.KnowledgeAccessContext.__post_init__`) already rejects unknown labels — the mutating plane must not be weaker. | :270, :476-483 | `__post_init__` rejecting `effective_sensitivity not in SENSITIVITY_LEVELS`; remove the `"public"` default (make required, or default strictest). | fixed |
| H3 | `requested_workspace_id: str \| None = None` — the cross-workspace gate only fires if a caller opts in. Omission is silent and untestable from inside the module. Field is excluded from the canonical digest, so a confirmation minted without it is equally valid for a request with it. Decisions-block Risk 1 (critical) says "no default workspace on mutation"; `None`-means-skip is a default workspace by another name. | :271, :456-457, :280 | Make owning-workspace input mandatory for every target-bearing kind (e.g. required non-empty `resolved_target_workspaces` whenever `ctx.targets` is non-empty); deny when any element differs from `identity.workspace_id`. | fixed |
| H4 | TTL fails open three ways: (1) missing/non-string/unparseable `expires_at` → `_parse_iso` returns `None` → **token never expires**; (2) `expires_at` trusted verbatim, never re-derived from `issued_at + CONFIRMATION_TTL`, so `"3000-01-01"` is honored; (3) expiry **not evaluated at all** on the `status == "consumed"` branch → exact-replay path is an unbounded-lifetime oracle. | :703-707, :689-695 | `if expires_at is None or moment > expires_at: → expired`; clamp with `min(expires_at, issued_at + CONFIRMATION_TTL)`; unparseable `issued_at` ⇒ expired; evaluate expiry on the consumed branch too. | fixed |
| H5 | `consume_confirmation` has no `status == "issued"` precondition and unconditionally overwrites `consumed_at`/`consumed_by_operation_id`. Called twice with different `operation_id`s it silently rebinds the confirmation to the second operation, destroying the first's consumption proof — contradicting `operator_mcp_confirmation.schema.yaml:39-42` ("populated only once … never reused"). Also does not check expiry. | :718-732 | Raise / return `None` unless `status == "issued"` and unexpired. **Plus** freeze the P2 durability contract in normative text (see DUR-1 below). | fixed |
| H6 | Existence oracle. AC OPM-2 requires one safe denial shape, but the frozen error schema says wrong-workspace resolves to `identity_denied` "(or, for object lookups, `not_found`)" — that parenthetical *is* the oracle. In code a workspace mismatch returns `identity_denied` (distinct message) while a missing ref returns `not_found`. An attacker distinguishes "exists, not yours" from "does not exist". The passing test compares wrong-workspace against **missing identity**, not **missing ref** — wrong pair, proves nothing. | `schemas/operator_mcp_error.schema.yaml:23-31`; policy :456-457, :740, :754 | Every denial reachable *after* a ref is resolved (wrong workspace, above threshold, wrong kind, absent) emits identical `not_found` + identical message + `retryable=False`. Reserve `identity_denied` strictly for pre-lookup identity absence. Delete the "(or …)" escape hatch from the schema. Re-point the test at the correct pair. | fixed |
| H7 | Above-threshold refs have **no code path at all**. `resolve_effective_sensitivity` computes a strictest label but nothing compares it against a ceiling/clearance. No `sensitivity_ceiling` on `PolicyContext`, no rank comparison, no `not_found` emission. Half of AC OPM-2 is unimplemented while the completion note reports OPM-1.2 as met. | :406-421 (and module-wide absence) | Add required `sensitivity_ceiling` to `PolicyContext`, validated against `SENSITIVITY_ORDER`; unknown → rank `len(SENSITIVITY_ORDER)` (repo convention, `export_service.py:82-84`) — **not** `-1`. Deny with the single `not_found` shape when effective rank > ceiling rank. | fixed |
| H8 | No exception boundary anywhere; four reachable raisers: `governance.guard_check` (malformed `config/governance.yaml` → `yaml.YAMLError`/`UnicodeDecodeError`/`PermissionError`), `audit_service.is_healthy_for_exposure` (`sqlite3.DatabaseError`/`OSError`), `ctx.canonical_digest()` (`TypeError` on non-JSON-serializable nested value — `dict()` at :291 is a **shallow** copy; `RecursionError` on deep nesting; reachable from inside `_bindings_match` with caller-influenced data), `FoundryPaths.discover()`. AC OPM-7 requires redacted+capped internal errors; `internal_error` has **zero call sites**. | :516-532, :301-302, :638-650, :527 | Wrap `evaluate_policy`/`authorize_operation`/`verify_confirmation` in `except Exception → PolicyDecision(False, <stage>, "internal_error", retryable=True)`. Set `json.dumps(..., allow_nan=False)` and validate `input_payload` is JSON-primitive at construction. | fixed |

### MEDIUM

| ID | Finding | Location | Required fix | Status |
|---|---|---|---|---|
| M1 | Every envelope bound (`maxItems: 20` targets, `maxProperties: 32` payload, `additionalProperties: false`, target-ref pattern, `maxLength` caps) is enforced **only by tests**. No non-test module loads the operator schemas; the repo has a real runtime `SchemaRegistry` (`schemas.py:77`) used by nine other services and the operator schemas are wired into none. `PolicyContext` accepts unbounded targets and arbitrarily deep payloads; `payload_too_large` has zero producers. | schema files; policy (no `research_foundry.schemas` import) | Either validate via `SchemaRegistry().validate(..., "operator_mcp_operation")` before constructing `PolicyContext`, or enforce caps in `__post_init__` and emit `payload_too_large`. Freeze which one P5 must do. | fixed |
| M2 | `now: datetime \| None = None` is public on `authorize_operation`/`verify_confirmation`; a caller passing a stale `now` bypasses TTL. Expiry uses wall clock, so a system-clock rollback extends every outstanding token. | :541, :658, :669 | Make `now` a test-only injectable module clock, or document it as a seam P2/P5 must never thread from request data. State the wall-clock assumption in the contract. | fixed |
| M3 | `_bindings_match` actor fallback matches **vacuously**: malformed/absent `actor` → `{}` → both `.get()` return `None`; when `ctx.identity is None` both RHS are also `None`, so actor and workspace bindings pass. Reachable via the `__all__`-exported `verify_confirmation`, which P2 *must* call directly (it is the only place `exact_replay` is visible — see C1). Only the digest prevents exploitation today, i.e. a single accidental line of defense. Separately, the double `record.get("actor")` means the value that passed `isinstance` is not the value used — latent TOCTOU on a stateful Mapping, not live today. | :638-650 | `if identity is None: return False` as first line; bind the lookup once. | fixed |
| M4 | `governance.redact_payload(text)` called without `config`, so workspace-configured `secret_patterns` are not scrubbed from `detail` — only builtins. (Redaction *order* is correct: redact then cap.) | :763; `governance.py:303-310` | Thread `FoundryConfig` into `build_error`, pass `config=`. | fixed |
| M5 | Guard denials leak governance `rule_id` into the error envelope; `no_work_sensitive_to_unapproved_provider` discloses effective sensitivity, `no_mixed_personal_work_bundle` discloses source-set composition. AC OPM-2 forbids returning derived detail. | :486, :794-807 | Keep `rule_id` internal-only (the `KnowledgeDenied.reason` pattern); omit from `build_error` output. | fixed |
| M6 | Audit-health gate inherits a fail-open: `get_health_state` returns `healthy=True` when the row was never written, so never-probed is indistinguishable from probed-healthy. Decisions-block: "A degraded audit store blocks confirmation for privileged operations." | :465-473; `audit_service.py:611-639` | Treat never-probed as unhealthy at this call site, or require P2 to probe before the first mint — and document the inherited tri-state. | fixed (round 2, finding NEW-3 — round 1's wontfix-justified verdict was REJECTED by the round-2 re-attack; see phase-1-completion.md "Security fix cycle round 2") |
| M7 | **Evidence integrity.** The completion note's "Validation command output (exact, as run)" shows the *identical* 63-dot progress line for two different suites, one of which the note itself says has 255 tests. 255 tests cannot render 63 dots. The transcripts are not real output. (Orchestrator independently re-ran all 348 tests and observed a genuine pass — the *claim* is true, the *evidence* was fabricated.) | `phase-1-completion.md:92-107` | Re-run and paste genuine transcripts. Treat implementer-pasted transcripts as unverified in all later phases. | fixed |

### LOW

| ID | Finding | Location | Status |
|---|---|---|---|
| L1 | `check_tool_name` has no caller; closure deferred to the "future P5 transport boundary". Enumeration itself is sound (resists case/whitespace/homoglyph smuggling). Also `_check_capability` runs before identity, so an unauthenticated caller distinguishes `operation_unknown`/`target_invalid` from `identity_denied`. | :430-436, :507-513 | fixed (documentation: "FROZEN P5 OBLIGATION" paragraph added to `check_tool_name`'s docstring; ordering caveat documented as accepted) |
| L2 | Four of seventeen reason codes have no producer: `confirmation_replayed`, `not_found`, `payload_too_large`, `internal_error` — each corresponding to a real gap above (C1, H6/H7, M1, H8). | enum | fixed (all four now have a real producer via the C1/H6/H7/M1/H8 fixes; covered by `test_every_closed_reason_code_has_a_real_producer`) |
| L3 | `mint_confirmation` validates only identity presence; will mint records whose `operation_kind`/`effective_sensitivity`/target kinds are outside the closed enums (nothing validates them — see M1). | :598-599 | fixed (defense-in-depth `ValueError` guards added for `operation_kind`/target kinds, mirroring the existing identity guard) |
| L4 | Canonical digest: **no practical collision found**. Key ordering deterministic (`sort_keys=True`); absent-vs-null distinct; numeric coercion distinct; target ordering fails closed; roles `sorted()` so role change invalidates. Two hardening items: `json.dumps` defaults `allow_nan=True` (NaN/inf emits non-JSON canonical text P2 cannot reproduce → set `allow_nan=False`); no Unicode normalization (fails *closed* today, but state it in the canonicalization contract so P2 does not add NFC folding later and silently change every digest). | :296-299 | fixed (`allow_nan=False` set; Unicode-normalization non-guarantee stated explicitly in the module docstring) |
| L5 | `_parse_iso` coerces naive datetimes to UTC; on a hand-edited/foreign-written record this can extend effective TTL by up to 14h. Prefer rejecting naive timestamps. | :581-582 | fixed (naive timestamps now rejected, never coerced) |
| L6 | `_check_preflight` builds `detail` with an f-string over internal enum members only (no caller input), but the module docstring's "never an f-string embedding caller input" reads broader than it is. | :502 | fixed (documentation clarification only, in `_check_preflight`'s docstring) |

### DUR-1 — durability contract P1 must freeze for P2

Consumption today is a pure-Python check-then-act with a wide TOCTOU window
(`verify_confirmation` read → caller work → `consume_confirmation` write). Two concurrent
callers presenting the same token both observe `status == "issued"` and both win. P1 is the
contract phase and does not freeze the required property, so P2 could implement
read-then-write and pass every test in this phase. **Normative text to add:**

> Consumption is a compare-and-swap on `status` from exactly `issued` to `consumed`, performed
> in the same durable transaction as the operation-manifest write, under an exclusive
> single-writer lock (SQLite `BEGIN IMMEDIATE`, or `O_EXCL` create-then-atomic-rename). A CAS
> that observes any status other than `issued` MUST route to the exact-replay /
> idempotency-conflict path and MUST NOT execute.

Status: fixed — added verbatim to the module docstring of `operator_mcp_policy.py` ("DURABLE
CONSUMPTION IS A COMPARE-AND-SWAP (DUR-1, binding on P2)" paragraph) and to
`schemas/operator_mcp_confirmation.schema.yaml`'s description (new section of the same name).
`consume_confirmation`'s own docstring cross-references it.

### What held up under attack (do not regress these)

- Stage ordering genuinely fixed — `_POLICY_STAGES` tuple + short-circuit loop; a request failing every stage fails at the first.
- Token comparison correct: SHA-256 stored, raw token never persisted, `hmac.compare_digest` constant-time, empty/missing digest denies.
- Binding coverage 9-for-9 on enumerated fields (roles covered transitively via digest). Only expiry is weak (H4).
- Governance/audit primitives reused, not forked — real `guard_check` / `is_healthy_for_exposure` against real `config/governance.yaml`.
- Redaction genuinely precedes size-capping.
- Knowledge MCP disjointness asserted at test time against the live registry tuple (14 operator names vs 8 knowledge names).
- Closed enumerations resist case/whitespace/homoglyph smuggling at the string-comparison level.

## FIND-P1-B — net-new RBAC primitive (from validator pass)

`_MUTATION_ROLES` / `_READ_ROLES` in `operator_mcp_policy.py` is a net-new authorization
primitive rather than a reuse of `api/auth/rbac.py`'s permission-string convention. The plan's
non-duplication rules forbid forking authority. Documented as a deliberate choice in the
completion note, but must be explicitly adjudicated at the Karen gate: either justified
(the operation surface does not yet exist) or refactored onto the existing convention.

Status: open — carry to Karen.

---

## FIND-P1-R2 — OPM-1.G security RE-ATTACK: fix cycle round 2 complete, pending re-attack

Source: security re-attack on exact tree `41bcafb` after fix cycle round 1.
Target file unless stated: `src/research_foundry/services/operator_mcp_policy.py`

**Round-2 fix-cycle status (2026-07-28)**: all 10 BLOCKING findings (NEW-1..NEW-10) and all 4
NON-BLOCKING findings (NEW-11..NEW-14) are `fixed` below. Every fix and its covering test(s) are
mapped in `.claude/progress/research-foundry-operator-mcp/phase-1-completion.md`, section "Security
fix cycle round 2". This is the implementer's self-assessment; it remains open pending an
independent round-3 re-attack (the same discipline that caught round 1's gaps applies here too —
"tests pass" is necessary, not sufficient).

> **Read this first (historical context for round 2).** Three of these defects (NEW-1, NEW-3,
> NEW-4) were *actively asserted as correct behavior by currently-passing tests* at the start of
> this cycle. The round-1 fix cycle pinned the unsafe behavior with tests. A green suite was
> therefore NOT evidence for round 2 — those tests had to be corrected, not preserved (they now
> are; see the completion doc's "tests whose assertion changed" subsection). NEW-5 and NEW-9 were
> invisible to the tests written to prove them; both are now covered by new, stronger tests.

### Round-1 closure re-verdicts (what round 1 actually achieved)

CLOSED and verified: M3, M5, L1, L2, L4, L5, L6, M2 (doc-only per its own OR clause).
CLOSED but scoped: H3, H5, L3 (enforced only inside `evaluate_policy`; the direct
`verify_confirmation` path never runs them).
PARTIAL: C1, H2, H4, H6, H7, H8, M1, M4, DUR-1.
**REJECTED**: M6 `wontfix-justified` — the justification's premise is false (see NEW-3).

No regression in the seven previously-sound properties (stage ordering, constant-time token
compare, 9-for-9 binding coverage, governance/audit reuse, redact-before-cap, KMCP disjointness,
enum smuggling resistance) — but H7 introduced a NEW fail-open in the same family (NEW-6).

### BLOCKING — fix in this order

| ID | Sev | Finding | Location | Required fix | Status |
|---|---|---|---|---|---|
| NEW-1 | **CRITICAL** | **C1 was relocated, not closed.** `verify_confirmation` returns `PolicyDecision(True, "confirmation")` for `exact_replay` — `==`-equal to the accept at :1082. The module docstring :62-65 makes it worse by *instructing* callers needing the replay distinction to call `verify_confirmation` directly and branch on `outcome`. That function runs ONLY the confirmation stage, so a P2 author following the frozen instruction and reading `.decision.allowed` executes a replay having skipped capability, RBAC, the H3 cross-workspace gate, audit-health, the H7 ceiling gate, and preflight. Requirement is prose, not shape. Test :718-720 pins the unsafe shape as intended. | :1052, :62-65, test :718-720 | Make the replay decision structurally non-accepting: `PolicyDecision(False, "confirmation", "confirmation_replayed")` with `outcome` carrying the not-an-error semantics, OR `stage="confirmation_exact_replay"` as originally prescribed. Rewrite the normative paragraph so the replay route is entered ONLY from `authorize_operation`'s denial (which has passed stages 1-5). Fix the test to assert the safe shape. | fixed |
| NEW-3 | **HIGH** | **Audit-health stage is a permanent no-op in its own topology; M6 wontfix invalid.** `audit_service.health_check(paths)` (audit_service.py:513) is a cheap, idempotent, never-raising 4-statement probe in a module already imported here — probe-on-demand closes the fail-open with zero bricking, so the wontfix's "assume-healthy or brick" binary is false. Independently: the only probe call sites are `api/app.py:398` (FastAPI startup) and `cli_commands.py:2605` (`--probe`), NEITHER of which runs in the local-stdio process this module targets. So `is_healthy_for_exposure` returns True forever and the decisions-block rule "a degraded audit store blocks confirmation for privileged operations" is unimplemented. Test :314-323 pins the fail-open. | :683-704 | Probe on demand in `_check_audit_health`, or make never-probed a hard denial with a documented bootstrap probe. Reopen M6; retire the pinning test. | fixed |
| NEW-2 | **HIGH** | **M1 dropped 5 of 7 declared bounds.** `_check_capability` enforces only `maxItems: 20` and `maxProperties: 32`. NOT enforced anywhere at runtime: `target_ref` `maxLength: 256` + `pattern ^[A-Za-z0-9_\-:.]+$` (schema says "never a raw filesystem path"), `idempotency_key` `maxLength: 128` + pattern, `policy_snapshot_version` `maxLength: 64`. So `TargetRef("run", "../../../etc/passwd")` or a 10MB `target_ref` passes every stage, gets bound into a confirmation, and reaches P2's object lookup. Empty `idempotency_key` passes, collapsing idempotency. The comment at :279-286 calling this enforcement "authoritative" is false. | :650-659, :279-286 | Enforce all 7 bounds in code, or route construction through `SchemaRegistry`. Correct the comment. | fixed |
| NEW-4 | **HIGH** | **H2's permissive default survived in the producer.** `resolve_effective_sensitivity()` returns `"public"` (loosest) for all-empty input — and empty IS the failed-lookup case. A ctx built as `PolicyContext(effective_sensitivity=resolve_effective_sensitivity(*lookups), ...)` passes `__post_init__` and every ceiling check when all lookups fail. Pinned by test :134-136. | :606-620 | Return `SENSITIVITY_LEVELS[-1]` (strictest) or raise on empty input. Fix the pinning test. | fixed |
| NEW-5 | **MED-HIGH** | **M4's `config=` makes redaction WEAKER.** `governance._secret_patterns` (governance.py:197-202) REPLACES the 22 built-ins with the config list rather than extending. So `build_error(detail=..., config=cfg)` against a workspace with a narrow custom list stops redacting `sk-ant-...` keys the no-config path WOULD have caught. `build_error`'s docstring :1179-1184 claims the opposite. Test :898-912 only asserts the custom pattern fires, never re-checks a built-in. Parameter is also optional with the unhardened default and has no caller — M4 closed in appearance only. | :1152-1159, :1179-1184 | Union config patterns with built-ins (or make replacement explicit AND make `config` mandatory). Fix docstring. Extend test to assert a built-in still fires when config is supplied. | fixed |
| NEW-8 | **MED** | **H8 boundary has two holes; its stated invariant is false.** (a) `_is_json_primitive` accepts `float("nan")`, which then raises `ValueError` in `canonical_json()` under the L4 `allow_nan=False` fix — L4 created a raiser H8 does not cover (repo test :887-890 demonstrates it). (b) `_is_json_primitive` accepts a bare `str`/`list` as `input_payload` (no `Mapping` check), so `dict(self.input_payload)` at :474 raises. Both escape UNCAUGHT from `mint_confirmation` :932, which sits outside every boundary. (c) `__post_init__` :431-434 interpolates `{self.effective_sensitivity!r}` — caller-controlled, unbounded, un-redacted — into an exception raised outside every boundary, contradicting the module's own "never an f-string embedding caller-supplied VALUES" guarantee and AC OPM-7. | :427-456, :326-346, :932, :484-490 | Reject non-finite floats and non-`Mapping` payloads; wrap `mint_confirmation` in the H8 boundary; stop interpolating caller values into exception text. | fixed |
| NEW-6 | **MED** | **`_sensitivity_rank` is fail-closed on the left operand, fail-open on the right.** "Unknown ⇒ rank 4 (strictest)" is correct for `effective_sensitivity` but INVERTED for `sensitivity_ceiling` — an unknown ceiling ranks 4 = maximum clearance = permits everything. Docstring :349-358 argues the fail-closed case and is silently wrong for one of its two call sites. Guarded today only by `__post_init__` plus a vocabulary round-trip test; if `SENSITIVITY_LEVELS` and `SENSITIVITY_ORDER` ever drift, the ceiling gate silently opens. | :349-359, :711 | Separate ceiling rank resolution; unknown ceiling resolves to `-1` or raises. | fixed |
| NEW-7 | **MED** | **H4's clamp has no lower bound.** `min(expires_at, issued_at + TTL)` defends against a forged far-future `expires_at` but not a forged far-future `issued_at` — `issued_at = now + 1y` yields a token valid for a year. Same threat model H4 was written for. | :881-894 | `if issued_at > moment: → expired` at both call sites (:1048, :1118); thread `now` into `_record_expiry`. | fixed |
| NEW-9 | **MED** | **H6's envelope identity is caller-dependent.** `build_error` passes `operation_id`/`receipt_ref` straight through; a P2 that populates `operation_id` on an exists-but-not-yours `not_found` and `None` on a genuinely-absent one restores the existence oracle. The proving test :432 hard-codes both to `None`, assuming away the residual leak. | :1162-1210 | Force both to `None` for `not_found` inside `build_error`; do not rely on the caller. | fixed |
| NEW-10 | **MED** | **Frozen DUR-1 CAS predicate is weaker than the reference implementation.** Normative text says CAS on `status` only; `consume_confirmation` :1114-1119 additionally requires unexpired. A P2 implementing the frozen text literally (`UPDATE ... WHERE status='issued'`) consumes an EXPIRED token and still passes closeout. | :114-119, :1114-1119 | Fold the expiry predicate into the frozen CAS text. | fixed |

### NON-BLOCKING — fold into the same cycle

| ID | Sev | Finding | Location | Status |
|---|---|---|---|---|
| NEW-11 | LOW-MED | `revoked` reported as retryable-expired: schema status enum includes `revoked`, but verify maps everything non-`issued`/non-`consumed` to `confirmation_expired`, `retryable=True`, message "request a new preflight preview" — inviting retry on a deliberately revoked confirmation. | :1065-1069 | fixed |
| NEW-12 | LOW-MED | `consume_confirmation` has no binding precondition — public, takes only `(record, operation_id)`; nothing requires the caller to have obtained an `accepted` verification for the same ctx+token first. The H5 fix made it merely *look* self-sufficient. | :1089-1124 | fixed |
| NEW-13 | LOW | Every `internal_error` is silent and retryable-forever. No `logging` import anywhere. A malformed `config/governance.yaml` becomes a clean `internal_error, retryable=True` with zero telemetry — a genuine bug hidden behind a policy denial, plus a retry loop on a deterministic failure. | :148-166 | fixed |
| NEW-14 | LOW | Hygiene: `consume_confirmation` :1120 `dict(record)` is a shallow copy (returned record shares `actor`/`targets` with input); `_STAGE_NAMES` :765-771 duplicates `_POLICY_STAGES` ordering in a parallel structure that can drift. | :1120, :765-771 | fixed |

---

## FIND-P1-R3 — OPM-1.G consolidated final gate: CHANGES_REQUESTED (round 3)

Source: consolidated security + validation gate on exact tree `f1bfa39`.
Status: **OPEN — this is the first work item for the next session.**

### Round-2 verification result: PASSED (empirical)

The reviewer ran a **15-mutation matrix**, reverting each round-2 fix individually and confirming
a purpose-built test fails for each. No mutation produced zero failures; M15 (pristine restore)
returned 105 passed, verifying the harness itself. **All 14 round-2 findings are genuinely closed
and regression-detecting** — including `test_audit_health_..._blocks_when_unhealthy`, empirically
confirmed as genuinely new and genuinely failing on revert. Round-1's evidence-integrity defect
(M7) is remediated; all claimed counts reproduce exactly (105 / 38 / 255).

### ⚠ METHODOLOGY TRAP — read before any future scratch-tree testing

`pyproject.toml` sets `[tool.pytest.ini_options] pythonpath = ["src"]`, which pytest inserts
**ahead of** the `PYTHONPATH` env var. A mutation sweep against a scratch copy therefore silently
tests the REAL worktree source and reports false negatives ("no test detects this defect").
The first sweep in this review hit exactly that and nearly produced a wrong conclusion.

Correct procedure: `--override-ini="pythonpath=<scratch>/src"`, mirror `config/`, `schemas/`,
`templates/` into the scratch root (`distribution_root()` resolves via `parents[2]`), purge stale
`__pycache__`, and always establish a baseline first. A `python -c "import ...; print(__file__)"`
sanity check is **NOT sufficient** — it exercises the env var pytest then overrides.

**Consequence:** the plan's documented validation command prefix `PYTHONPATH=$PWD/src` is
**decorative**. It happens to point at the same tree so existing counts are valid, but it provides
no isolation guarantee. Consider correcting the plan's Validation Strategy section.

### BLOCKING — fix in this order

| ID | Sev | Finding | Required fix | Status |
|---|---|---|---|---|
| NEW-23 | HIGH | **Serve-extra import boundary claim is false.** `import operator_mcp_policy` fails without `fastapi`/`uvicorn` installed — breaking the local-stdio topology P5 explicitly declares. Same false-authoritativeness class as NEW-2. | Break the transitive import so the policy module imports cleanly in a base install; add a test that imports it with the serve extra absent. | fixed |
| NEW-18 | HIGH | **`PolicyContext.identity` is caller-supplied.** Decisions-block Risk 1 is rated *critical* ("no default workspace on mutation"; configured-local identity only) and its mitigation here is prose, not shape — a caller can hand in an identity rather than having it derived. | Make identity derivation structural: resolve inside the policy module from configured local config, or make the caller-supplied path impossible to reach from the public API. | fixed |
| NEW-22 | HIGH | **`researcher` granted agent-job-class operations** that `api/auth/rbac.py` reserves for owner/admin. The written justification is factually wrong. Gives FIND-P1-B a concrete security dimension — it is no longer a style question. | Align the role grants with `rbac.py`'s convention, or justify the divergence with an accurate rationale. Karen adjudicates. | fixed |
| NEW-20 | MED-HIGH | **`denial_reason_code` is an open string** despite both the receipt schema and the completion note claiming a closed enum. False-authoritativeness (same class as NEW-2 / NEW-23). | Close the enum in schema and code; add a negative fixture. | fixed |
| NEW-21 | MED | **`audit_delivery.detail` accepts raw tracebacks**; its natural producer is `str(exc)`. Violates AC OPM-7's bounded/redacted requirement. | Apply the same `_SAFE_MESSAGES` / redact-then-cap treatment used for the error envelope. | fixed |
| NEW-19 | MED | **Audit-health is permanently bricked after the first failed probe**, with an unachievable `retryable=True`. The NEW-3 fix overcorrected. | Allow recovery — re-probe on a later call rather than latching the failure. | fixed |

### NON-BLOCKING

NEW-15, NEW-16, NEW-17, NEW-24, NEW-25 plus documentation nits. Reviewer's stated fix order places
them after the six blocking items. **Detail was not captured into the orchestrator's context** —
re-derive by re-running the consolidated gate, or by asking the reviewer agent to re-emit only the
non-blocking rows. Do not treat their absence here as "no findings".

### Standing caution

`schemas/operator_mcp_receipt.schema.yaml` had **never been adversarially attacked** before this
pass — rounds 1 and 2 both targeted `operator_mcp_policy.py` and the error schema. NEW-20 and
NEW-21 came from its first real review. Treat the receipt schema as **still under-reviewed**;
do not assume it is now clean.

### Queued explicitly for Karen (not yet run)

1. **PART C ratification** of the `governance.py` serialization-barrier write. Reviewer recommends
   **accept with conditions**: it is a provable no-op for the shipped config, restores
   `redact_payload`'s own documented "additional" contract, and is strictly fail-closed.
   > ⚠ **CORRECTED at the round-5 Karen adjudication — see `FIND-P1-KAREN` below.** Two of those
   > three grounds hold; **"provable no-op for the shipped config" is FALSE**. The shipped config's
   > regex escaping differs from the built-in literals for three patterns, so the union yields 25
   > entries rather than 22 and `scan_secrets` now returns DUPLICATE hits (a flagged file reports
   > "2 match(es)" where it reported 1). Detection outcomes and gate decisions are unchanged, so the
   > severity is LOW — but the claim as written is an over-claim of exactly the false-authoritativeness
   > class this workstream keeps producing, and it was propagated verbatim into the round-3 closure
   > section before being caught.
2. **FIND-P1-B** — the net-new `_MUTATION_ROLES`/`_READ_ROLES` primitive, now carrying NEW-22's
   concrete privilege-escalation dimension.
3. The **`governance.preflight()` deviation** from decisions-block line 30.

Karen was deliberately NOT run at this pause: with six blocking findings open, the OPM-1.G gate
cannot pass, and a Karen pass would only re-report them at Opus cost.

---

## FIND-P1-R3-CLOSURE — round-3 remediation (all six blocking findings closed)

Status: **all six BLOCKING findings above are `fixed`.** Each carries at least one test that fails
when the fix is reverted. Fixed in the reviewer's mandated order.

### NEW-23 — serve-extra import boundary

Root-caused to a two-link chain, not the single link the finding named:
`operator_mcp_policy` → `services/audit_service.py` (`from research_foundry.api.auth.provider import
AuthIdentity`) → `api/__init__.py` (eager `import fastapi`). A second, independent link was found
during the fix: `audit_service` also imported `resolve_workspace_isolation_active` from
`api/auth/scope.py`.

**A LAYER BELOW the finding text.** Fixing only the import would have been a false close:
`resolve_operator_identity()` CONSTRUCTS an `AuthIdentity` at runtime, and `api/auth/provider.py`
module-imports `starlette`. A base install would therefore have imported cleanly and then failed on
first real use. Empirically confirmed under a `sys.meta_path` blocker before and after.

Fix: `AuthIdentity` relocated to the serve-free `research_foundry/auth_identity.py`;
`api/auth/provider.py` re-exports **that exact class object** (never a redefinition), so all ~487
existing references and every `isinstance` check are unchanged. `resolve_workspace_isolation_active`
moved to `config.py` with the same re-export treatment. `operator_mcp_policy` now imports
`AuthIdentity` at module level — deliberately NOT under `TYPE_CHECKING` — so the serve-gated path
cannot silently return. The module docstring's previous claim (which asserted the old
TYPE_CHECKING+lazy arrangement achieved the boundary) was factually wrong and has been rewritten.

Test: `tests/unit/test_operator_mcp_serve_extra_boundary.py` — asserts BOTH import AND runtime
identity construction in a **subprocess** with fastapi/uvicorn/starlette blocked (a subprocess is
required; the rest of the suite imports fastapi and would mask the failure).

### NEW-18 — structural identity derivation

Fixed in three layers, because closing only the constructor would leave the layer below open:
1. `PolicyContext.identity` is now `field(init=False, default=None)` — the public constructor cannot
   accept an identity at all (raises `TypeError`).
2. `PolicyContext.for_configured_operator(...)` is the sole sanctioned constructor that populates it,
   always from `resolve_operator_identity(paths, config=config)`. It exposes no identity parameter.
3. `_check_identity_and_rbac` **re-derives** the identity from config and makes the authorization
   decision entirely from the derived value. `ctx.identity` participates only as an equality
   commitment: a mismatch denies `identity_denied` with no distinguishing detail.

All 22 `__all__` symbols were enumerated. `mint_confirmation` is the one residual: it has no `paths`
parameter and embeds `ctx.identity` into the minted record's `actor` block, so a forged context can
be minted — but the record is inert, because `authorize_operation` always re-runs `evaluate_policy`
(which denies at `rbac`) before the confirmation stage is reached. Pinned by a dedicated test.
**Flagged for the gate to adjudicate** rather than asserted as safe.

Independently verified by the orchestrator (not merely self-reported): constructor injection rejected;
a wholesale forged identity denied; a *role-escalation-only* forgery (same user/workspace, extra
roles) denied; and absent config denied.

### NEW-22 — role grants aligned with rbac.py

`ROLE_PERMISSIONS["researcher"]` in `api/auth/rbac.py` explicitly excludes `agent_job:launch`, and
that module's forward-compat note requires `Depends(require_role("owner","admin"))` on every
agent-job mutation route. `_MUTATION_ROLES` granted `researcher` every mutating kind uniformly,
including the agent-job-class kinds `swarm.start`, `job.cancel`, `job.resume`.

**A SECOND divergence in the same table, not named by the finding:** `_READ_ROLES` granted `viewer`,
while rbac.py sets `"viewer": set()` (zero permissions) and marks `run:read` as not granted to viewer.
The comment annotating that set claimed it "mirrors rbac.py's viewer-has-zero-permissions convention"
— the stated rationale contradicted its own code. This is the same false-authoritativeness class as
NEW-2/NEW-20/NEW-23. Both are fixed and the justification text rewritten accurately.

Fix shape: replaced the two-way read/mutate split with an **exhaustive** `_OPERATION_ROLES` map
(kind → required roles) plus an import-time completeness check. A permissive default was the
fail-open class that recurred every round; adding a new `OPERATION_KINDS` member without classifying
it now raises at import instead of silently inheriting the researcher-inclusive grant. The stage also
denies rather than falling through if a kind is somehow unclassified.

`test_rbac_allows_viewer_for_read_only_job_status` **pinned the unsafe behaviour** and was INVERTED
(not weakened) per the standing rule.

### NEW-20 — denial_reason_code enum closed

`schemas/operator_mcp_receipt.schema.yaml` declared `type: [string, "null"], maxLength: 64` while its
own description and the completion note both claimed a closed enum. Now a closed 17-member enum plus
`null` (which the `allOf` requires for `completed`/`canceled`). Negative fixtures for a bogus code and
for a near-miss (`guard_blocked_extra`) — the latter is exactly what an open 64-char string accepted.
A drift guard pins the schema enum to `operator_mcp_policy.CLOSED_REASON_CODES` in both directions.

### NEW-21 — audit_delivery.detail bounded and redacted

The field was an unguarded `type: string, maxLength: 500` whose natural producer is `str(exc)`. It now
carries the SAME negative traceback pattern as `operator_mcp_error`'s `message`/`detail`, and a new
public producer `build_audit_delivery()` routes `detail` through the identical
`redact_payload` → traceback-strip → cap pipeline as the error envelope. A test feeds a REAL
`traceback.format_exc()` through the builder and asserts the result still validates — pinning that the
code-side pipeline and the schema-side guard agree.

### NEW-19 — audit-health latch removed (both directions)

The NEW-3 fix probed only when `last_probe_at is None`, then trusted the persisted row forever. That
latched **both** ways: a failed probe denied permanently (making the advertised `retryable=True`
unachievable), and — the half the finding did not name — a successful probe meant a store that
degraded *later* was never re-checked, relocating the very "healthy forever" fail-open NEW-3 set out
to close.

Fix: run the live `health_check` probe unconditionally on every confirmation-requiring call. This
stage is reached only for privileged/mutating kinds (`job.status` returns earlier), the probe is a
cheap idempotent local write-then-read, and it removes any dependence on `get_health_state`'s
"assume healthy until proven otherwise" default — a fail-open shape that should not be read on an
authorization path at all. Four tests: denial, recovery (proving `retryable=True` is now achievable),
post-healthy degradation, and non-reliance on the assume-healthy default.

`test_audit_unhealthy_blocks_mutating_operation` asserted the stage "must deny WITHOUT re-probing" —
it pinned the defect. Rewritten against the live probe.

---

## FIND-P1-R4 — OPM-1.G consolidated final gate, round 4: **CHANGES_REQUESTED**

Source: consolidated security + validation re-attack on exact tree `f16059f` (branch
`worktree-operator-mcp-v1`, working tree clean). Base for diffs `main`; round-3 remediation alone
`git show f16059f`.

**Verdict: CHANGES_REQUESTED.** Five of the six round-3 blocking findings are genuinely closed and
regression-detecting. The sixth (NEW-19) is closed *in code* but **none of its four purpose-built
tests fail when the fix is reverted** — the closure evidence does not hold. Separately, the round-3
remediation introduced or left nine defects, seven of them in the two recurring classes this gate
exists to catch (false authoritativeness; fix-the-layer-below).

### Round-3 closure re-verdicts

| ID | Verdict | Evidence |
|---|---|---|
| NEW-23 serve-extra boundary | **CLOSED, regression-detecting** | Mutations M1/M2/M3 (revert each of the three import links: `audit_service`→`api.auth.provider` for `AuthIdentity`; `operator_mcp_policy`→`api.auth.provider`; `audit_service`→`api.auth.scope` for `resolve_workspace_isolation_active`) each fail `tests/unit/test_operator_mcp_serve_extra_boundary.py`. Class identity verified: exactly one `class AuthIdentity` (`src/research_foundry/auth_identity.py:29`) and one `def resolve_workspace_isolation_active` (`src/research_foundry/config.py:1558`); `auth_identity.AuthIdentity is api.auth.provider.AuthIdentity is operator_mcp_policy.AuthIdentity` → `True`; `config.resolve_workspace_isolation_active is api.auth.scope.resolve_workspace_isolation_active` → `True`. Both re-exports are in the re-exporting module's `__all__` (`provider.py:107`, `scope.py:211`). `isinstance` semantics across all ~487 references are therefore unchanged. |
| NEW-18 structural identity | **CLOSED, regression-detecting** — but see BLOCK-6 | M4 (revert Layer 1: make `identity` an ordinary init field) and M5 (revert Layer 3: read `ctx.identity` instead of re-deriving) both fail. M5 is the load-bearing one. Empirically, `_check_identity_and_rbac` re-derives from the `paths` handed to `evaluate_policy` at call time and denies `identity_denied` when it disagrees with `ctx.identity`. |
| NEW-22 role grants | **CLOSED, regression-detecting** — but see BLOCK-7 | M6 (restore researcher on `swarm.start`/`job.cancel`/`job.resume`) and M7 (restore `viewer` in `_READ_ROLES`) both fail. Grants re-derived against `api/auth/rbac.py:99-135`: `agent_job:launch` is owner/admin only and explicitly withheld from researcher → `_AGENT_JOB_ROLES = {owner, admin}` is correct; `"viewer": set()` → viewer's exclusion from every kind including `job.status` is correct; `run:read` is granted to reviewer → `reviewer` on `job.status` is correct. **`writeback.preview` → researcher is CORRECT on the rbac.py axis**: rbac.py grants researcher `report:create`/`report:update` and withholds only `report:publish`; a preview is not a publish. Its *second* justification is not (BLOCK-7). |
| NEW-20 `denial_reason_code` enum | **CLOSED for the named field only** | M9 (reopen the enum to `type: [string,"null"], maxLength: 64`) fails `tests/unit/test_operator_mcp_schemas.py`. Negative fixtures and the bidirectional drift guard are real (`test_receipt_denial_reason_code_rejects_value_outside_closed_enum`, `..._rejects_near_miss_of_a_real_code`, `..._enum_matches_code_closed_reason_codes`, `test_receipt_every_closed_reason_code_is_accepted`). **Two residuals reopened as BLOCK-2 and BLOCK-3.** |
| NEW-21 `audit_delivery.detail` | **CLOSED IN PART — REOPENED** | M10 (drop the schema `not: pattern`) and M11 (bypass `_redact_and_bound` in `build_audit_delivery`) each fail, so the two halves that *were* built are regression-detecting. But the finding's own named producer — `str(exc)` — still leaks. See BLOCK-1. |
| NEW-19 audit-health latch | **CLOSED IN CODE; CLOSURE EVIDENCE INVALID — REOPENED** | The code fix is correct (`_check_audit_health`, `operator_mcp_policy.py:1104`, probes unconditionally). But under mutation M12 (restore the pre-NEW-19 `if last_probe_at is None:` latch) **all four NEW-19 tests still pass in isolation.** See BLOCK-4 for the mechanism, verified from test source. |

### BLOCKING

| ID | Sev | Finding | Location | Concrete failing scenario | Required fix |
|---|---|---|---|---|---|
| **BLOCK-1** | **MED-HIGH** | **NEW-21 is closed against tracebacks only, not against its own named producer `str(exc)`.** The finding text is "`audit_delivery.detail` accepts raw tracebacks; **its natural producer is `str(exc)`**". `_TRACEBACK_LIKE` (and the identical schema `not.pattern`) match only `traceback` / `site-packages` / `File "…", line N`. `governance.redact_payload`'s 18 built-in patterns contain no filesystem-path pattern, so the redact leg is a no-op for this input. The receipt schema's own module description asserts "No field here ever carries a stack trace, environment variable, secret, or **unrestricted filesystem path**" — that claim is false. | `operator_mcp_policy.py:519` (`_TRACEBACK_LIKE`), `:1663-1670` (`_redact_and_bound`), `:1751-1799` (`build_audit_delivery`); `schemas/operator_mcp_receipt.schema.yaml:47-54, 78-94`; same pipeline feeds `operator_mcp_error.detail` | **Empirically verified.** `build_audit_delivery("degraded", detail=str(OSError(2,"No such file or directory","/Users/alice/.config/research-foundry/serve.env")))` emits `detail` **verbatim, unredacted**, and the embedding `terminal_receipt` validates with `errors: []`. Same for `PermissionError(13,"Permission denied","/home/bob/.ssh/id_ed25519")`. Direct probes: `redact_payload("/Users/alice/.config/research-foundry/serve.env")` returns the string unchanged. **Worse — the NEW-21 producer test pins this**: `test_audit_delivery_builder_output_validates_even_for_a_real_traceback` (`test_operator_mcp_schemas.py:295-315`) raises `OSError("audit store unreachable at /var/secrets/db.sock")`, pushes `traceback.format_exc()` through the builder, and asserts the result validates — the `Traceback` header and `File "…", line N` frames are stripped, the `/var/secrets/db.sock` path in the exception message is not. The test demonstrates the leak and asserts it is acceptable (defect class 3). | Either (a) extend the redaction pipeline with an absolute-path pattern (`(?:/Users/|/home/|/var/|/etc/|/opt/|[A-Za-z]:\\\\)[^\s'"]*` → `[PATH]`) and a bare `Errno`/exception-shape guard, mirroring it into both schemas' `not.pattern`; or (b) drop `detail` to a closed enum of delivery-failure causes. Then rewrite the producer test to assert the path is **absent** from the output, and correct the receipt schema's "never … unrestricted filesystem path" claim. |
| **BLOCK-2** | **MED-HIGH** | **NEW-20 closed one field and left its sibling open, in the same file, one `$def` above.** `action_receipt.reason_code` is still `type: [string, "null"], maxLength: 64` — the exact open-string shape NEW-20 was raised on — and carries the same semantics (a per-action denial cause). Fix-the-layer-below / `__all__`-sibling class. | `schemas/operator_mcp_receipt.schema.yaml:199-201` | The near-miss NEW-20's negative fixture was written for (`guard_blocked_extra`) is still accepted on `action_receipt`. Coverage is **zero**: `grep -n action_receipt tests/unit/test_operator_mcp_schemas.py` returns **no matches at all** — `action_receipt` is the only one of the five `$defs` with no golden instance, no negative fixture and no `_valid_*` helper. The drift guard `test_receipt_denial_reason_code_enum_matches_code_closed_reason_codes` (`:350-362`) reads only `$defs.terminal_receipt.properties.denial_reason_code`. Mutation N2 (closing the enum) breaks **no** existing test, so the tightening is free. | Close `action_receipt.reason_code` to the same 17-member enum + `null`; extend the drift guard to assert BOTH fields against `CLOSED_REASON_CODES`; add a golden instance + negative fixture for `action_receipt`. |
| **BLOCK-3** | **MED** | **A `terminal_receipt` with `status: denied` validates with `denial_reason_code` entirely ABSENT.** The `allOf` `then` branch uses `denial_reason_code: not: {const: null}` but never `required: [denial_reason_code]`, and the property is not in the top-level `required` list. A producer omitting the key sidesteps the whole NEW-20 enum. | `schemas/operator_mcp_receipt.schema.yaml:404-415` | **Empirically verified**: a `terminal_receipt` with `status: "denied"` and no `denial_reason_code` key validates with `errors: []`. The existing guard `test_receipt_terminal_denied_requires_reason_code` (`:253-255`) only ever exercises the *null* case, because `_valid_terminal_receipt` (`:195-211`) always injects `"denial_reason_code": None`. **The correct pattern is used one file over by the same author in the same PR**: `operator_mcp_confirmation.schema.yaml:251-261` pairs `required: [consumed_at, consumed_by_operation_id]` with `not: {const: null}`. Mutation N1 (adding `required`) breaks no existing test. | Add `required: [denial_reason_code]` to the `denied`/`failed` `then` branch; add a negative fixture for the absent-key case. |
| **BLOCK-4** | **MED** | **NEW-19's closure evidence is invalid: none of its four tests fail when the fix is reverted.** All four monkeypatch `audit_service.health_check` with a fake that returns an `AuditHealth` and **never persists a row**. Under the reverted pre-NEW-19 code (`state = get_health_state(paths); if state.last_probe_at is None: state = health_check(paths)`), `get_health_state` therefore keeps returning `last_probe_at=None` on every call, so the latch branch never engages and the fake is re-entered every time — reproducing, by accident, exactly the unlatched behaviour the tests assert. | `tests/unit/test_operator_mcp_policy.py:669-684` (`_unhealthy_probe`/`_healthy_probe`), `:687-705`, `:708-730`, `:733-748`, `:751-770` | Verified from source and confirmed by mutation M12. `test_audit_health_recovers_after_a_failed_probe` and `test_audit_health_degradation_after_a_healthy_probe_is_detected` (the two captioned "NEW-19 core") both **pass in isolation** under M12. `test_audit_health_does_not_read_the_assume_healthy_persisted_default` (`:751`) is the most acute case: it stubs `get_health_state` to return **`last_probe_at=None`** — precisely the value that makes the reverted latch branch fire — so the one test named for excluding the assume-healthy default is the one most thoroughly blinded to it. The regression is caught only incidentally, by `test_every_closed_reason_code_has_a_real_producer`, and only because an unrelated **real** probe earlier in that same test had already persisted state. | Drive the tests through the real sqlite `audit_health` row (or have the fakes persist), so a reintroduced latch makes `get_health_state().last_probe_at` non-`None` and the test fails. At minimum, one test must assert `health_check` is called on the SECOND evaluation (call-count spy), which is the actual NEW-19 property. |
| **BLOCK-5** | **MED** | **The module docstring still describes the round-2 audit-health behaviour that NEW-19 replaced, and credits a function this module does not call.** Three false claims, all in prose the remediation edited around but did not update. False-authoritativeness class (same as NEW-2 / NEW-20 / NEW-23). | `operator_mcp_policy.py:44-57` | (a) `:52-54` — "P1 now probes **ON DEMAND exactly once per workspace** (whenever the persisted state has never been probed)". The code (`:1104`) probes **unconditionally on every confirmation-requiring call**; probe-once-per-workspace is precisely the defect NEW-19 named. (b) `:45-46` lists `audit_service.get_health_state` among the calls this module makes — `grep -n get_health_state src/research_foundry/services/operator_mcp_policy.py` returns only lines `45` and `1101`, **both prose**; there is no call site. NEW-19's own inline comment (`:1101-1103`) says the dependence was *removed*, directly contradicting the docstring 1050 lines above it. (c) `:44-47` calls the reused primitives "read-only"; `health_check` is a write-then-read probe that `INSERT`s, `SELECT`s and `DELETE`s an `audit_event` row. | Rewrite `:44-57` to describe unconditional live probing; drop `get_health_state` from the reuse list; drop "read-only". |
| **BLOCK-6** | **MED** | **The NEW-18 closure's global claim is false; `mint_confirmation` is the reachable counterexample.** Module docstring `:233-237` asserts: "**no value forced onto `ctx.identity`, by any means, can ever grant more than the identity already configured … would grant on its own**". That holds for `authorize_operation` only. `verify_confirmation` and `consume_confirmation` are both in `__all__`, neither re-derives identity, and `mint_confirmation` writes the unverified `ctx.identity` straight into the record's durable `actor` block. | `operator_mcp_policy.py:233-247`, `:1326-1423` (`mint_confirmation`), `:1430-1454` (`_bindings_match`), `:1457-1576`, `:1579-1635`; `__all__` `:301-326` | **Empirically verified.** With a forged `ctx.identity` (`AuthIdentity("mallory","ws-evil",("owner",))` forced via `object.__setattr__`): `mint_confirmation` succeeds and `record["actor"]["user_id"] == "mallory"`; `verify_confirmation(record, presented_token=…, ctx=forged)` returns `outcome="accepted"`, `PolicyDecision(allowed=True, stage="confirmation")` — because `_bindings_match` compares the record's actor against `ctx.identity`, and both are the same forgery; `consume_confirmation(record, operation_id="op1")` (no `ctx`) returns a fully `consumed` record. Only `authorize_operation` denies (`stage='rbac'`, `identity_denied`). The pinning test `test_forged_identity_cannot_produce_an_authorized_mint_confirmation` (`test_operator_mcp_policy.py:399-430`) asserts *only* the `authorize_operation` half — it never touches the other two entry points, so it certifies the narrow claim while the docstring makes the broad one. This is the same "prose, not shape" objection that made NEW-1 and NEW-18 blocking. | **See the `mint_confirmation` adjudication below.** Preferred fix (≈3 lines): give `mint_confirmation` a `paths: FoundryPaths \| None = None` parameter and build the `actor` block from `resolve_operator_identity(paths)`, denying when it disagrees with `ctx.identity` — making the durable actor block unforgeable at the only place it is produced. Then correct `:233-237`. |
| **BLOCK-7** | **MED-HIGH** | **The entire guard stage is skippable by omission, and the NEW-22 comment relies on a rule that cannot fire by default.** `_OPERATION_ROLES`'s new comment justifies researcher-eligibility for `writeback.preview` partly on: "It additionally passes the same `*_writeback_requires_review` guard rules as every other writeback, so researcher-initiated previews still cannot self-approve." All three of those rules are gated on `GuardContext.writeback_targets` being non-empty and containing `meatywiki`/`intenttree`/`arc`. `PolicyContext.writeback_targets` defaults to `()`, and nothing in `_check_capability`, `_check_preflight` or `__post_init__` requires it to be non-empty for `writeback.preview`. | `operator_mcp_policy.py:504-508`, `:664-666` (defaults), `:1110-1132` (`_check_guard`); `services/governance.py:425-479` | With a default-constructed `writeback.preview` context, `writeback_targets=()` → `personal_mw_target`/`intenttree_target`/`arc_target` are all `False` → none of the three review rules can fire. The same holds for the other two block-severity rules: `no_work_sensitive_to_unapproved_provider` needs `model_provider` (defaults `None`, `governance.py:386`) and `no_mixed_personal_work_bundle` needs `source_sensitivities` (defaults `()`, `governance.py:405-407`). **`_check_guard` therefore reduces to the H7 ceiling comparison for any caller that does not opt in** — while `PolicyContext`'s own docstring (`:634-643`) claims these fields "enable the … block-severity rules to fire through this contract exactly as they do for run-level guard checks". This is the omitted-means-skip shape H3 removed from `requested_workspace_id`, still live on the mutating plane, now load-bearing for a role grant. | Make `writeback_targets` mandatory and non-empty for `writeback.preview` (validate in `__post_init__` or `_check_capability`, denying `payload_too_large`/`preflight_failed`); and either populate the other two guard inputs from resolved server-side state or delete the claim that these rules fire "exactly as they do for run-level guard checks". |
| **BLOCK-8** | **MED-HIGH** | **NEW-9 closed two caller channels on the `not_found` envelope and left a third open.** `build_error` forces `operation_id`/`receipt_ref` to `None` for `not_found` "REGARDLESS of what the caller passes in", on the stated grounds that H6's one-denial-shape guarantee "is a property of the CLOSED envelope this function builds, **not something a caller can be trusted to preserve by convention**". Caller-supplied `detail` is on the same envelope, is subject to the identical argument, and is passed through untouched. | `operator_mcp_policy.py:1673-1740` (`:1722-1726` forces two fields; `:1718-1720` and `:1738-1739` do not force `detail`) | **Empirically verified**: `build_error(PolicyDecision(False,"rbac","not_found"), operation_id="opm_…", receipt_ref="r1", detail="run rn_abc123 is owned by workspace ws_other")` returns `operation_id=None, receipt_ref=None` **and** `detail='run rn_abc123 is owned by workspace ws_other'` verbatim. The string is not redacted (it matches none of the 18 built-in secret patterns and is not traceback-shaped). A P2 that attaches a `detail` on the "exists, not yours" case and omits it on the genuinely-absent case restores exactly the existence oracle H6/NEW-9 closed. Neither of P1's two internal `not_found` producers sets `detail`, so forcing it costs nothing today. | Force `detail = None` for `reason_code == "not_found"` inside `build_error`, alongside `operation_id`/`receipt_ref`; add a test asserting a caller-supplied `detail` is dropped. |
| **BLOCK-9** | **MED** | **The frozen DUR-1 CAS predicate is still weaker than its reference implementation — the same defect NEW-10 raised, one predicate over.** Round 2 folded the expiry half into the frozen text. The binding half was not folded in, and in the reference implementation it is **opt-in**: `consume_confirmation`'s `ctx` parameter defaults to `None`, which skips `_bindings_match` entirely. "P2 SHOULD always pass `ctx`" is prose. | `operator_mcp_policy.py:143-172` (frozen text), `:1579-1635` (`:1604-1606` documents the permissive default, `:1621-1622` implements it); `schemas/operator_mcp_confirmation.schema.yaml:64-83` | **Empirically verified**: `consume_confirmation(record, operation_id="op1")` with **no** `ctx` returns a fully `consumed` record with no binding check having run; with a mismatching `ctx` it correctly returns `None`. A P2 implementing the frozen text literally (`UPDATE … WHERE status='issued' AND <clamped expiry>`) consumes a record that does not bind to the request it is committing, and passes P1 closeout. | Fold the binding predicate into the frozen DUR-1 text in BOTH the module docstring and `operator_mcp_confirmation.schema.yaml`, and make `ctx` a required keyword argument on `consume_confirmation` (P1's own call sites already have one). |

### NON-BLOCKING

> **On NEW-15 / NEW-16 / NEW-17 / NEW-24 / NEW-25.** Their text was never captured into the ledger
> and the round-3 reviewer's context is gone; the original wording and numbering are **not
> recoverable**. Presenting a reconstruction as if it were those items would be fabrication. The set
> below is therefore an **independently re-derived** non-blocking set from a fresh pass over the same
> surface, at the same severity band. Where a plausible correspondence exists it is noted, but the
> mapping is a guess and should not be relied on.

| ID | Sev | Finding | Location |
|---|---|---|---|
| NB-1 | LOW-MED | **`input_payload` has no size bound, only shape bounds** (plausibly ≈NEW-15). Enforced: depth ≤32 and ≤32 top-level properties. Not enforced anywhere: nested breadth, string lengths, total bytes. A payload with 32 top-level keys each holding a 300 KB string passes `_check_capability`, passes the schema (`maxProperties: 32`, `additionalProperties: true`, no `maxLength`), gets SHA-256'd, and is embedded in a durable confirmation. `payload_too_large` has producers for *shape* violations but none for actual size — while the comment at `:414-430` calls the in-code enforcement "what actually protects every caller today". | `operator_mcp_policy.py:414-436`, `:976-1011`; `schemas/operator_mcp_operation.schema.yaml:170-176` |
| NB-2 | LOW-MED | **`check_tool_name` still has zero callers** (L1 carried forward, plausibly ≈NEW-16). The "FROZEN P5 OBLIGATION" paragraph is prose with no artifact that fails if P5 ships without wiring it. `test_check_tool_name_rejects_unknown_and_wildcard` exercises the function but proves nothing about the transport boundary. | `operator_mcp_policy.py:955-973` |
| NB-3 | LOW-MED | **The negative `pattern`s are not ECMA-262** (plausibly ≈NEW-17). `(?i)` is a Python inline flag; JSON Schema 2020-12 specifies ECMA-262 regexes, where `(?i)` is a syntax error. The repo validates with Python `jsonschema` so it works locally, but the schemas carry public `$id`s. Validators that cannot compile a `pattern` commonly skip the keyword — in which case the schema-side guard that BLOCK-1 shows is already the *only* remaining defence silently disappears. | `schemas/operator_mcp_receipt.schema.yaml:94`; `schemas/operator_mcp_error.schema.yaml:85, 104` |
| NB-4 | LOW | **The `now=` clock seam is still public** on four exported functions (plausibly ≈NEW-24). M2 was closed by documentation only; nothing prevents P2/P5 threading a request-supplied timestamp. | `operator_mcp_policy.py:135-141`, `:1326`, `:1457`, `:1579`, `:1218` |
| NB-5 | LOW | **`consume_confirmation`'s optional `ctx`** (plausibly ≈NEW-25) — see BLOCK-9, recorded here too as the non-blocking half (the API shape, as distinct from the frozen-contract defect). | `operator_mcp_policy.py:1584`, `:1598-1606` |
| NB-6 | LOW-MED | **The serve-extra boundary test blocks three module names, not the declared `[serve]` extra.** `_BLOCKED = {"fastapi","uvicorn","starlette"}` is hard-coded rather than derived from `pyproject.toml`, so a new serve-only dependency is not covered. The test also exercises only `import` + `resolve_operator_identity`; it never runs `evaluate_policy`/`mint_confirmation` under the blocker, so a serve-gated import reachable only from a policy stage would still pass. | `tests/unit/test_operator_mcp_serve_extra_boundary.py:42`, `:68-135` |
| NB-7 | LOW-MED | **An autouse fixture monkeypatches `policy.resolve_operator_identity` for the entire policy test module** — i.e. the exact seam that constitutes NEW-18 Layer 3. The ~100 tests in the module therefore exercise the *equality-commitment* half but never the *derive-from-configured-local-config* half; real derivation is covered only by the identity-resolution unit tests and the serve-extra boundary test. Not a defect (the property was independently confirmed empirically), but the closure note's coverage claim is thinner than it reads. | `tests/unit/test_operator_mcp_policy.py:90-106`, `:126-144` |
| NB-8 | LOW-MED | **`_check_identity_and_rbac` ignores the `config` threaded through `for_configured_operator`.** The factory derives identity via `resolve_operator_identity(paths, config=config)`; the authorization stage derives via `resolve_operator_identity(paths)` — no `config=` — constructing a fresh `FoundryConfig(paths=…)`. A caller passing a custom `config` therefore gets a context that always denies `identity_denied` unless `paths` independently agrees. Fail-closed, so not a vulnerability, but a silent always-deny footgun and a divergence from the factory's own docstring. | `operator_mcp_policy.py:743-804` (`:802`), `:1026` |
| NB-9 | LOW-MED | **Audit-probe write amplification on the authorization hot path.** NEW-19's unconditional probe means every confirmation-requiring evaluation performs `INSERT` + `SELECT` + `DELETE` against `audit_event` in `.rf_state/rbac.db` — at least twice per operation (mint-time `evaluate_policy` + execute-time `authorize_operation`). Under the concurrency DUR-1 explicitly contemplates ("two concurrent callers presenting the same token"), SQLite write-lock contention surfaces as `healthy=False` → a spurious `audit_unhealthy` denial. It also exercises a DELETE against a table whose own module contract states "no UPDATE or DELETE paths … Do not add UPDATE/DELETE helpers". `retryable=True` makes this self-correcting, so it degrades to retry churn rather than a hard failure. | `operator_mcp_policy.py:1104`; `services/audit_service.py:23-26`, `:496-513`, `:516-611` |
| NB-10 | LOW | **The `_OPERATION_ROLES` completeness check is one-directional.** It asserts `OPERATION_KINDS ⊆ keys(_OPERATION_ROLES)` only. It does not assert `keys ⊆ OPERATION_KINDS` (a stale entry after a kind rename lingers silently), nor that each value is non-empty, nor that every role name appears in `rbac.ROLE_PERMISSIONS`. All three residual failure modes are fail-closed, so this is hygiene, not a hole. | `operator_mcp_policy.py:511-517` |
| NB-11 | LOW | **Two receipt-shape gaps.** `checkpoint` carries no `workspace_id` (every other persisted kind does), so P2 cannot workspace-scope a checkpoint from the receipt alone — relevant given WKSP-304. And `operation_receipt.status` admits `denied` while the `$def` has no reason field at all, so a denied operation receipt records no cause. | `schemas/operator_mcp_receipt.schema.yaml:95-152`, `:244-302` |

### `mint_confirmation` adjudication (explicitly queued for this gate)

**Verdict: the "inert" argument is CORRECT but SCOPED TOO NARROWLY, and the boundary as shipped is
NOT acceptable — though the fix is small.**

What is true: `authorize_operation` is the only sanctioned execute-time entry point, it
unconditionally re-runs `evaluate_policy` first, and `_check_identity_and_rbac` re-derives identity
and denies at `rbac` before the confirmation stage is ever reached. A confirmation minted against a
forged `ctx` therefore cannot back an `authorize_operation` that returns `allowed=True`. That was
verified empirically, and `mint_confirmation`'s own docstring (`:1339-1349`) states exactly this
narrow claim and nothing more.

What is false: the module docstring's *global* restatement at `:233-237` ("no value forced onto
`ctx.identity`, by any means, can ever grant more than the identity already configured … would grant
on its own"). Three counterexamples, all reachable through `__all__`:

1. `verify_confirmation(record, presented_token=…, ctx=forged)` returns
   `PolicyDecision(allowed=True, stage="confirmation")`, because `_bindings_match` compares the
   record's `actor` block against `ctx.identity` — and on a forged mint both sides are the same
   forgery. The only thing standing between that and execution is the prose instruction "MUST NEVER
   be called directly", which is precisely the mitigation shape NEW-1 rejected when it went to the
   trouble of making the *replay* branch structurally non-accepting.
2. `consume_confirmation(record, operation_id=…)` transitions the forged record to `consumed` with
   no identity check and — by default — no binding check either (BLOCK-9).
3. **What P2 will persist.** The forged `actor` block is written verbatim into a schema-valid
   `operator_mcp_confirmation` record. Per DUR-1 that record is committed in the same transaction as
   the operation manifest, so a forged actor becomes durable provenance. Nothing in the frozen DUR-1
   text re-derives or re-checks identity at commit time. Decisions-block Risk 1 is rated *critical*
   and is about the system never attributing or authorizing a mutation to anything but the configured
   local identity — attribution is half of that, and it is unguarded.

The counter-argument that forging requires `object.__setattr__` (and therefore in-process code
execution, at which point everything is lost) does not rescue the boundary, because the remediation
itself already rejected that argument: NEW-18 Layer 3 exists *specifically* because "a frozen
dataclass can still be tampered with via `object.__setattr__`". Under its own accepted threat model,
`mint_confirmation` is the one unguarded producer.

**Required:** add `paths: FoundryPaths | None = None` to `mint_confirmation` and build the `actor`
block from `resolve_operator_identity(paths)`, raising when it disagrees with `ctx.identity` — the
same three-line pattern Layer 3 already uses. That removes the argument entirely rather than
relitigating it, makes the durable `actor` block unforgeable at its only point of production, and
lets `:233-237` be true as written. If instead the boundary is accepted as-is, `:233-237` MUST be
narrowed to the `authorize_operation`-only claim, and `verify_confirmation`/`consume_confirmation`
should be removed from `__all__` so "never call directly" is structural rather than advisory.

### Serialization-barrier assessment (`audit_service.py`, `provider.py`, `scope.py`, `config.py`)

**Provable no-op for existing callers. Recommend ratification.** The `audit_service.py` change is two
import-source swaps plus docstring text; both targets resolve to the *same objects* the previous
sources did (`is`-identity verified for both `AuthIdentity` and `resolve_workspace_isolation_active`),
there is exactly one definition of each in the tree, and both re-exporting modules list the name in
`__all__`. `resolve_workspace_isolation_active`'s body is byte-identical between `main`'s
`api/auth/scope.py` and HEAD's `config.py` — a pure relocation. WKSP-304 behaviour is therefore
unchanged for every existing caller (`catalog_service.py`, `builder_service.py`, `AgentJobService`,
and `audit_service._isolation_active`, which remains a thin delegate).

### Validation transcript (real, as run)

```
$ cd /Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1

# A) targeted operator-mcp unit suites
$ /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest \
    tests/unit/test_operator_mcp_policy.py tests/unit/test_operator_mcp_schemas.py \
    tests/unit/test_operator_mcp_serve_extra_boundary.py -q --tb=no -rf > /tmp/r4_targeted.txt 2>&1
EXIT=0

$ tail -5 /tmp/r4_targeted.txt   # ANSI color codes stripped below for readability; content otherwise verbatim
........................................................................ [ 43%]
........................................................................ [ 87%]
.....................                                                    [100%]
# (pytest emitted no trailing "N passed in Ys" summary line into the redirected file in this
#  environment — reproduced on a second independent run with --color=no and PYTHONUNBUFFERED=1;
#  the progress line reaching [100%] with EXIT=0 and zero FAILED/ERROR lines is the pass signal.)

# B) full suite minus the two known-collection-error files
$ /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/ -q --tb=no -rf \
    --ignore=tests/test_verification_pediatric_cds.py \
    --ignore=tests/test_verification_seam001_gate_composition.py > /tmp/r4_full.txt 2>&1
EXIT=1

$ grep -c "^FAILED" /tmp/r4_full.txt
0
$ grep -c "FAILED" /tmp/r4_full.txt   # ANSI color codes precede "FAILED" in the redirected file, so the
16                                    # anchored ^FAILED count above is 0; the unanchored count is the real one.

$ grep "FAILED" /tmp/r4_full.txt      # ANSI stripped below for readability; text otherwise verbatim
FAILED tests/test_cli_rights.py::test_rights_validate_requires_as_of - assert '--as-of' in "\x1b[33mUsage: \x1b[0mrf rights validate [OPTIONS] [PA...
FAILED tests/test_contract_drift_rf_schema_version.py::test_cli_json_dumps_site_counts_match_pinned_baseline - assert 28 == 27
FAILED tests/test_deployment_mode_cli_and_app.py::TestServeModeFlag::test_mode_multi_user_without_provider_refuses_before_binding - AssertionError: assert '(a)' in '\x1b[31merror:\x1b[0m \x1b[33mdeployment_m...
FAILED tests/test_pediatric_cds_redteam_fixtures.py::test_seven_verified_bundles_zero_false_positives - AssertionError: expected verified bundle sources dir at /Users/miethe/dev/h...
FAILED tests/test_serve_api.py::test_get_run_detail_known_run_returns_200 - assert 404 == 200
FAILED tests/test_serve_api.py::test_get_claims_non_empty - assert 404 == 200
FAILED tests/test_serve_api.py::test_get_claims_empty_ledger_returns_empty_list - assert 404 == 200
FAILED tests/test_serve_api.py::test_get_source_found - assert 404 == 200
FAILED tests/test_serve_api.py::test_sensitivity_gate_parity_work_sensitive_claim - assert 404 == 200
FAILED tests/test_swarm_drive.py::test_cli_drive_json_output - assert '"status_derived": "bundle_written"' in '\x1b[1m{\x1b[0m\n  \x1b[1;3...
FAILED tests/test_swarm_drive.py::test_cli_drive_ica_json - assert '"status_derived": "awaiting_legs"' in '\x1b[1m{\x1b[0m\n  \x1b[1;34...
FAILED tests/test_verification_clinical_eligibility_regression.py::test_seven_verified_bundles_zero_eligible_claims - AssertionError: expected claim ledger at /Users/miethe/dev/homelab/developm...
FAILED tests/test_verification_clinical_eligibility_regression.py::test_seven_verified_bundles_exact_passage_present_never_hard_gated_by_p3 - AssertionError: expected claim ledger at /Users/miethe/dev/homelab/developm...
FAILED tests/unit/test_assertion_rollout.py::test_assertion_ledger_controls_are_independently_default_off - AssertionError: assert True is False
FAILED tests/unit/test_assertion_rollout.py::test_write_and_automated_reuse_consumers_fail_closed_by_default - AssertionError: assert 'eligible' == 'automated_reuse_disabled'
FAILED tests/unit/test_report_anchors.py::test_schema_version_bumped_for_report_anchors - AssertionError: assert '1.8' == '1.4'

# C) flake8 on the six touched/reviewed files (no --select filter, per this gate's instructions —
#    note this project's own CLAUDE.md convention runs flake8 with --select=E9,F63,F7,F82 for
#    errors-only; the unfiltered run below is style-noise (E501/E305) only, zero E9/F-class hits)
$ /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m flake8 \
    src/research_foundry/services/operator_mcp_policy.py src/research_foundry/auth_identity.py \
    src/research_foundry/config.py src/research_foundry/api/auth/provider.py \
    src/research_foundry/api/auth/scope.py src/research_foundry/services/audit_service.py
EXIT=1
src/research_foundry/api/auth/provider.py:72:80: E501 line too long (82 > 79 characters)
src/research_foundry/api/auth/provider.py:88:80: E501 line too long (86 > 79 characters)
src/research_foundry/api/auth/provider.py:97:80: E501 line too long (80 > 79 characters)
src/research_foundry/api/auth/scope.py:1:80: E501 line too long (88 > 79 characters)
src/research_foundry/api/auth/scope.py:3:80: E501 line too long (80 > 79 characters)
src/research_foundry/api/auth/scope.py:81:80: E501 line too long (80 > 79 characters)
src/research_foundry/api/auth/scope.py:82:80: E501 line too long (85 > 79 characters)
src/research_foundry/api/auth/scope.py:83:80: E501 line too long (98 > 79 characters)
src/research_foundry/api/auth/scope.py:84:80: E501 line too long (84 > 79 characters)
src/research_foundry/api/auth/scope.py:160:80: E501 line too long (81 > 79 characters)
src/research_foundry/api/auth/scope.py:165:80: E501 line too long (83 > 79 characters)
src/research_foundry/api/auth/scope.py:182:80: E501 line too long (82 > 79 characters)
src/research_foundry/api/auth/scope.py:189:80: E501 line too long (86 > 79 characters)
src/research_foundry/api/auth/scope.py:191:80: E501 line too long (83 > 79 characters)
src/research_foundry/auth_identity.py:35:80: E501 line too long (82 > 79 characters)
src/research_foundry/config.py:29:80: E501 line too long (87 > 79 characters)
src/research_foundry/config.py:66:80: E501 line too long (83 > 79 characters)
src/research_foundry/config.py:164:80: E501 line too long (89 > 79 characters)
src/research_foundry/config.py:216:80: E501 line too long (82 > 79 characters)
src/research_foundry/config.py:217:80: E501 line too long (83 > 79 characters)
src/research_foundry/config.py:284:80: E501 line too long (83 > 79 characters)
src/research_foundry/config.py:391:80: E501 line too long (84 > 79 characters)
src/research_foundry/config.py:397:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:401:80: E501 line too long (88 > 79 characters)
src/research_foundry/config.py:500:80: E501 line too long (82 > 79 characters)
src/research_foundry/config.py:501:80: E501 line too long (84 > 79 characters)
src/research_foundry/config.py:517:80: E501 line too long (82 > 79 characters)
src/research_foundry/config.py:520:80: E501 line too long (83 > 79 characters)
src/research_foundry/config.py:528:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:584:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:588:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:633:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:643:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:645:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:657:80: E501 line too long (82 > 79 characters)
src/research_foundry/config.py:661:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:669:80: E501 line too long (82 > 79 characters)
src/research_foundry/config.py:705:80: E501 line too long (90 > 79 characters)
src/research_foundry/config.py:708:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:736:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:744:80: E501 line too long (87 > 79 characters)
src/research_foundry/config.py:791:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:793:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:798:80: E501 line too long (84 > 79 characters)
src/research_foundry/config.py:802:80: E501 line too long (82 > 79 characters)
src/research_foundry/config.py:803:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:805:80: E501 line too long (82 > 79 characters)
src/research_foundry/config.py:810:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:826:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:829:80: E501 line too long (82 > 79 characters)
src/research_foundry/config.py:830:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:833:80: E501 line too long (85 > 79 characters)
src/research_foundry/config.py:859:80: E501 line too long (90 > 79 characters)
src/research_foundry/config.py:865:80: E501 line too long (89 > 79 characters)
src/research_foundry/config.py:880:80: E501 line too long (82 > 79 characters)
src/research_foundry/config.py:902:80: E501 line too long (111 > 79 characters)
src/research_foundry/config.py:904:80: E501 line too long (92 > 79 characters)
src/research_foundry/config.py:918:80: E501 line too long (82 > 79 characters)
src/research_foundry/config.py:919:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:921:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:955:80: E501 line too long (100 > 79 characters)
src/research_foundry/config.py:976:80: E501 line too long (83 > 79 characters)
src/research_foundry/config.py:985:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:1063:80: E501 line too long (83 > 79 characters)
src/research_foundry/config.py:1072:80: E501 line too long (85 > 79 characters)
src/research_foundry/config.py:1073:80: E501 line too long (86 > 79 characters)
src/research_foundry/config.py:1074:80: E501 line too long (83 > 79 characters)
src/research_foundry/config.py:1075:80: E501 line too long (83 > 79 characters)
src/research_foundry/config.py:1078:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:1079:80: E501 line too long (82 > 79 characters)
src/research_foundry/config.py:1131:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:1163:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:1208:80: E501 line too long (85 > 79 characters)
src/research_foundry/config.py:1251:80: E501 line too long (92 > 79 characters)
src/research_foundry/config.py:1291:80: E501 line too long (84 > 79 characters)
src/research_foundry/config.py:1292:80: E501 line too long (83 > 79 characters)
src/research_foundry/config.py:1302:80: E501 line too long (83 > 79 characters)
src/research_foundry/config.py:1307:80: E501 line too long (91 > 79 characters)
src/research_foundry/config.py:1316:80: E501 line too long (90 > 79 characters)
src/research_foundry/config.py:1323:80: E501 line too long (88 > 79 characters)
src/research_foundry/config.py:1325:80: E501 line too long (85 > 79 characters)
src/research_foundry/config.py:1326:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:1327:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:1328:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:1332:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:1347:80: E501 line too long (93 > 79 characters)
src/research_foundry/config.py:1353:80: E501 line too long (105 > 79 characters)
src/research_foundry/config.py:1362:80: E501 line too long (91 > 79 characters)
src/research_foundry/config.py:1363:80: E501 line too long (90 > 79 characters)
src/research_foundry/config.py:1371:80: E501 line too long (85 > 79 characters)
src/research_foundry/config.py:1374:80: E501 line too long (103 > 79 characters)
src/research_foundry/config.py:1385:80: E501 line too long (82 > 79 characters)
src/research_foundry/config.py:1386:80: E501 line too long (92 > 79 characters)
src/research_foundry/config.py:1398:80: E501 line too long (113 > 79 characters)
src/research_foundry/config.py:1409:80: E501 line too long (92 > 79 characters)
src/research_foundry/config.py:1410:80: E501 line too long (98 > 79 characters)
src/research_foundry/config.py:1416:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:1426:80: E501 line too long (91 > 79 characters)
src/research_foundry/config.py:1435:80: E501 line too long (83 > 79 characters)
src/research_foundry/config.py:1436:80: E501 line too long (84 > 79 characters)
src/research_foundry/config.py:1443:80: E501 line too long (88 > 79 characters)
src/research_foundry/config.py:1444:80: E501 line too long (83 > 79 characters)
src/research_foundry/config.py:1455:80: E501 line too long (84 > 79 characters)
src/research_foundry/config.py:1456:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:1457:80: E501 line too long (85 > 79 characters)
src/research_foundry/config.py:1458:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:1462:80: E501 line too long (81 > 79 characters)
src/research_foundry/config.py:1467:80: E501 line too long (83 > 79 characters)
src/research_foundry/config.py:1475:80: E501 line too long (80 > 79 characters)
src/research_foundry/config.py:1511:80: E501 line too long (88 > 79 characters)
src/research_foundry/config.py:1531:80: E501 line too long (85 > 79 characters)
src/research_foundry/config.py:1536:80: E501 line too long (82 > 79 characters)
src/research_foundry/config.py:1580:80: E501 line too long (91 > 79 characters)
src/research_foundry/services/audit_service.py:1:80: E501 line too long (84 > 79 characters)
src/research_foundry/services/audit_service.py:4:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/audit_service.py:5:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/audit_service.py:6:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/audit_service.py:20:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/audit_service.py:52:80: E501 line too long (90 > 79 characters)
src/research_foundry/services/audit_service.py:86:1: E305 expected 2 blank lines after class or function definition, found 1
src/research_foundry/services/audit_service.py:90:80: E501 line too long (81 > 79 characters)
src/research_foundry/services/audit_service.py:97:80: E501 line too long (82 > 79 characters)
src/research_foundry/services/audit_service.py:120:80: E501 line too long (84 > 79 characters)
src/research_foundry/services/audit_service.py:149:80: E501 line too long (108 > 79 characters)
src/research_foundry/services/audit_service.py:160:80: E501 line too long (92 > 79 characters)
src/research_foundry/services/audit_service.py:196:80: E501 line too long (82 > 79 characters)
src/research_foundry/services/audit_service.py:198:80: E501 line too long (88 > 79 characters)
src/research_foundry/services/audit_service.py:208:80: E501 line too long (84 > 79 characters)
src/research_foundry/services/audit_service.py:209:80: E501 line too long (85 > 79 characters)
src/research_foundry/services/audit_service.py:256:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/audit_service.py:270:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/audit_service.py:370:80: E501 line too long (109 > 79 characters)
src/research_foundry/services/audit_service.py:375:80: E501 line too long (82 > 79 characters)
src/research_foundry/services/audit_service.py:380:80: E501 line too long (81 > 79 characters)
src/research_foundry/services/audit_service.py:382:80: E501 line too long (91 > 79 characters)
src/research_foundry/services/audit_service.py:404:80: E501 line too long (84 > 79 characters)
src/research_foundry/services/audit_service.py:451:80: E501 line too long (84 > 79 characters)
src/research_foundry/services/audit_service.py:499:80: E501 line too long (87 > 79 characters)
src/research_foundry/services/audit_service.py:502:80: E501 line too long (89 > 79 characters)
src/research_foundry/services/audit_service.py:509:80: E501 line too long (93 > 79 characters)
src/research_foundry/services/audit_service.py:542:80: E501 line too long (97 > 79 characters)
src/research_foundry/services/audit_service.py:550:80: E501 line too long (86 > 79 characters)
src/research_foundry/services/audit_service.py:556:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/audit_service.py:561:80: E501 line too long (86 > 79 characters)
src/research_foundry/services/audit_service.py:596:80: E501 line too long (86 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:94:80: E501 line too long (81 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:127:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:193:80: E501 line too long (81 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:211:80: E501 line too long (94 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:332:80: E501 line too long (81 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:386:80: E501 line too long (98 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:483:80: E501 line too long (85 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:512:80: E501 line too long (86 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:515:80: E501 line too long (82 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:516:80: E501 line too long (90 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:519:80: E501 line too long (83 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:552:80: E501 line too long (101 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:637:80: E501 line too long (88 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:640:80: E501 line too long (88 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:648:80: E501 line too long (81 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:677:80: E501 line too long (92 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:680:80: E501 line too long (90 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:684:80: E501 line too long (86 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:686:80: E501 line too long (86 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:687:80: E501 line too long (86 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:688:80: E501 line too long (85 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:696:80: E501 line too long (82 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:702:80: E501 line too long (84 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:716:80: E501 line too long (88 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:717:80: E501 line too long (98 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:718:80: E501 line too long (90 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:741:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:867:80: E501 line too long (93 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:902:80: E501 line too long (102 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:903:80: E501 line too long (91 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:918:80: E501 line too long (86 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:933:80: E501 line too long (81 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:972:80: E501 line too long (83 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:976:80: E501 line too long (82 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:978:80: E501 line too long (88 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:980:80: E501 line too long (97 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:981:80: E501 line too long (88 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:993:80: E501 line too long (88 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:996:80: E501 line too long (81 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:998:80: E501 line too long (88 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1001:80: E501 line too long (89 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1010:80: E501 line too long (89 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1014:80: E501 line too long (88 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1028:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1037:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1046:80: E501 line too long (81 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1061:80: E501 line too long (83 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1106:80: E501 line too long (87 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1114:80: E501 line too long (93 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1126:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1131:80: E501 line too long (86 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1135:80: E501 line too long (81 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1180:80: E501 line too long (96 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1199:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1201:80: E501 line too long (85 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1211:80: E501 line too long (87 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1215:80: E501 line too long (85 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1259:80: E501 line too long (82 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1262:80: E501 line too long (98 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1266:80: E501 line too long (94 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1268:80: E501 line too long (86 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1277:80: E501 line too long (96 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1299:80: E501 line too long (83 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1326:80: E501 line too long (96 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1377:80: E501 line too long (82 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1383:80: E501 line too long (81 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1384:80: E501 line too long (95 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1393:80: E501 line too long (85 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1421:80: E501 line too long (92 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1423:80: E501 line too long (82 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1449:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1453:80: E501 line too long (85 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1501:80: E501 line too long (93 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1505:80: E501 line too long (104 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1508:80: E501 line too long (86 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1510:80: E501 line too long (89 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1512:80: E501 line too long (104 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1525:80: E501 line too long (100 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1532:80: E501 line too long (98 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1536:80: E501 line too long (95 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1549:80: E501 line too long (96 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1555:80: E501 line too long (104 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1560:80: E501 line too long (104 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1566:80: E501 line too long (96 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1569:80: E501 line too long (89 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1572:80: E501 line too long (94 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1575:80: E501 line too long (92 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1643:80: E501 line too long (99 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1644:80: E501 line too long (80 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1645:80: E501 line too long (109 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1647:80: E501 line too long (106 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1648:80: E501 line too long (88 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1652:80: E501 line too long (89 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1653:80: E501 line too long (99 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1654:80: E501 line too long (102 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1655:80: E501 line too long (90 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1656:80: E501 line too long (91 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1658:80: E501 line too long (82 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1659:80: E501 line too long (84 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1663:80: E501 line too long (94 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1712:80: E501 line too long (91 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1745:80: E501 line too long (93 > 79 characters)
src/research_foundry/services/operator_mcp_policy.py:1789:80: E501 line too long (94 > 79 characters)
# 248 lines total: 247 E501 (line-length) + 1 E305 (blank-line spacing), zero E9/F63/F7/F82 hits.

# D) tree state
$ git status --porcelain
$ echo "EXIT=$?"
EXIT=0
$ git log --oneline -1
f16059f fix(operator-mcp): close all six OPM-1.G round-3 blocking findings
```

Full suite: **16 FAILED**, matching the 16 pre-existing failures verified identical at pre-change
commit `15101a4` — zero regressions from this work. The two collection-error files
(`test_verification_pediatric_cds.py`, `test_verification_seam001_gate_composition.py`) are
pre-existing on `main` and were excluded.

### Standing cautions carried forward

- `schemas/operator_mcp_receipt.schema.yaml` was attacked in full this round and yielded three more
  findings (BLOCK-2, BLOCK-3, NB-11) plus one shared with the code (BLOCK-1). It is no longer
  "under-reviewed", but `action_receipt` has **zero** test coverage of any kind and should get a
  golden instance + negative fixtures before P2 builds against it.
- The four recurring defect classes all recurred again this round: fail-open-by-omission (BLOCK-7),
  fix-the-layer-below (BLOCK-2, BLOCK-8, BLOCK-9), unsafe-behaviour-pinned-by-a-test (BLOCK-1's
  producer test, BLOCK-4's four blinded tests), and false authoritativeness (BLOCK-1, BLOCK-5,
  BLOCK-6, BLOCK-7). **Every round-3 fix that was verified by mutation held; every defect found this
  round is in prose, in a test, or in the field next to the one that was fixed.**
- The plan's documented validation prefix `PYTHONPATH=$PWD/src` remains decorative (pytest's
  `pythonpath = ["src"]` ini setting is inserted ahead of it). All mutation work this round was done
  **in place** in the worktree and restored with `git checkout --`, avoiding the trap entirely.

---

## FIND-P1-R5 — OPM-1.G consolidated final gate, round 5: **CHANGES_REQUESTED**

Source: consolidated security + validation re-attack on exact tree `e4c76b9` (branch
`worktree-operator-mcp-v1`, working tree clean). Round-4 remediation alone: `git show e4c76b9`.

**Verdict: CHANGES_REQUESTED.** All nine round-4 blocking findings (BLOCK-1 … BLOCK-9) are
**genuinely closed**, and eight of the nine are **empirically regression-detecting** under in-place
mutation. This is the first round in which every claimed closure held up — including BLOCK-4, whose
round-4 closure evidence was invalid and is now valid (all three latch-sensitive tests fail
standalone). However the round-4 remediation introduced or left **four blocking defects**, three of
them in the same two recurring classes as every prior round: fix-the-layer-below (the sibling field /
sibling `$def` next to the one that was fixed) and false authoritativeness (a new prose claim that
the new code does not satisfy).

### Round-4 closure re-verdicts (empirical, in-place mutation, tree restored + verified clean after each)

Baseline on pristine `e4c76b9`: `pytest tests/unit/test_operator_mcp_policy.py tests/unit/test_operator_mcp_schemas.py tests/unit/test_operator_mcp_serve_extra_boundary.py -q` → **EXIT=0**, 177 collected (121 / 54 / 2), zero FAILED. Final re-run after the whole sweep → **EXIT=0** (harness + restore both proven).

| ID | Verdict | Mutation evidence |
|---|---|---|
| **BLOCK-1** audit_delivery detail | **CLOSED, regression-detecting** | Three independent mutations, all DETECTED (exit 1). M1a `_PATH_LIKE` → never-matching → `test_build_error_scrubs_bare_path_shaped_detail_with_no_traceback_framing`. M1b drop the unknown-`detail_code` guard + fall through as free text → `test_audit_delivery_builder_rejects_unknown_detail_code`. M1c revert wholesale replacement → per-match `sub` → `test_build_error_scrubs_bare_path_shaped_detail_with_no_traceback_framing`. The vocabulary is genuinely CLOSED: `build_audit_delivery(status, *, audit_event_id=None, detail_code=None)` — passing `detail=` raises `TypeError`, an unknown `detail_code` raises `ValueError`, there is **no fail-open default**. All 15 `status` × `{None + 4 detail_codes}` combinations emit blocks that validate inside a `terminal_receipt` with `errors: []`. `build_error`'s legitimate detail path is NOT broken: both internal `_check_preflight` detail strings pass through unmodified. **But see R5-BLOCK-1 and R5-NB-1/NB-2 — the field next to it, and the denylist itself.** |
| **BLOCK-2** `action_receipt.reason_code` enum | **CLOSED for the value domain, regression-detecting** | M2 (reopen to `type: [string,"null"] maxLength: 64`) → exit 1, three tests fail including the now-bidirectional drift guard `test_receipt_denial_reason_code_enum_matches_code_closed_reason_codes`. Golden instance + two negative fixtures added; `action_receipt` is no longer zero-coverage. **But the presence coupling was not closed — see R5-BLOCK-3.** |
| **BLOCK-3** terminal denied requires reason code | **CLOSED, regression-detecting** | M3 (delete `required: [denial_reason_code]` from the `denied`/`failed` `then` branch) → exit 1, `test_receipt_terminal_denied_requires_reason_code_key_to_be_present`. |
| **BLOCK-4** audit-health latch closure evidence | **CLOSED, regression-detecting — evidence now VALID** | M4 (reintroduce the pre-NEW-19 `get_health_state` + probe-only-if-never-probed latch) → exit 1. Critically, and unlike round 4: **three tests now fail STANDALONE, one pytest invocation each** — `test_audit_health_recovers_after_a_failed_probe`, `test_audit_health_degradation_after_a_healthy_probe_is_detected`, `test_audit_health_does_not_read_the_assume_healthy_persisted_default` — with meaningful assertion messages, no isolation/ordering dependence. The `_persist_health_row` sqlite helper added this round is what fixes it: the fakes now persist a row, so a reintroduced latch makes `get_health_state().last_probe_at` non-`None` and the latch branch engages. `test_every_closed_reason_code_has_a_real_producer` also fails (collateral). The four tests that are correctly latch-insensitive (`..._blocks_mutating_operation`, `..._does_not_block_job_status`, the two `..._never_probed_...`) return exit 0, as they should. |
| **BLOCK-5** stale audit-health docstring | **CLOSED (verified by reading; no mutation possible — prose)** | `operator_mcp_policy.py:65-92` now describes LIVE, UNCONDITIONAL probing and correctly attributes "probe on demand exactly once per workspace" to round 2 as **superseded**. `:60-63` states this module has **no** call sites for `get_health_state` (`grep` confirms: only prose at `:61` and `:1101`). `:56-58` drops the "read-only" claim and states `health_check` is a write-then-read-then-delete probe. All three false claims corrected. **Residual: R5-NB-5.** |
| **BLOCK-6** `mint_confirmation` identity derivation | **CLOSED, regression-detecting** | M6a (delete derive+compare, build `actor` from `ctx.identity`) → exit 1, `test_mint_confirmation_rejects_a_forged_identity`. M6b (derive but never compare) → exit 1, same test — so the **comparison itself** is pinned, not merely the actor's source. Empirically: a forged `ctx.identity` (`AuthIdentity("mallory","ws-evil",("owner",))` via `object.__setattr__`) now raises `ValueError` at mint; an authentic record + forged ctx yields `verify → confirmation_mismatch` and `consume → None`. **But see R5-BLOCK-2, R5-BLOCK-4, R5-NB-4 and R5-NB-7.** |
| **BLOCK-7** `writeback.preview` fail-closed | **CLOSED, regression-detecting** | M7 (delete the branch) → exit 1, `test_writeback_preview_with_empty_writeback_targets_denies_at_preflight`. Empirically `writeback_targets=()` → `PolicyDecision(allowed=False, stage='preflight', reason_code='preflight_failed')`; `writeback_targets=('meatywiki',)` → allowed. **Stage placement is sound but cosmetically inverted**: `_POLICY_STAGES` order is `capability → rbac → audit_health → guard → preflight`, so `_check_guard` still runs FIRST and passes vacuously on the empty tuple (`_check_guard(ctx_a)` → `allowed=True`) before `_check_preflight` denies one stage later. Not bypassable — both are private, and the only path reaching `_check_guard` is `evaluate_policy`'s loop, which always continues to `_check_preflight`. **`model_provider` / `source_sensitivities` — the other two omission channels BLOCK-7 named — were addressed by option (b), narrowing the claim rather than populating them**: `PolicyContext`'s docstring (`:766-779`) now states they are ADVISORY ONLY and explicitly retracts the "fire exactly as they do for run-level guard checks" over-claim, and the `_OPERATION_ROLES` comment (`:596-603`) now rests researcher eligibility on the rbac.py axis alone. That satisfies the required fix as written. |
| **BLOCK-8** `build_error` forces `detail` for `not_found` | **CLOSED, regression-detecting** | M8 (delete `safe_detail = None`) → exit 1, `test_build_error_forces_null_detail_for_not_found_regardless_of_caller`. Empirically `build_error(PolicyDecision(False,'rbac','not_found'), operation_id=…, receipt_ref='r1', detail='run rn_abc123 is owned by workspace ws_other')` returns `operation_id=None`, `receipt_ref=None`, and **no `detail` key**. Correctly scoped: the same `detail` survives verbatim on `identity_denied`, as intended. |
| **BLOCK-9** DUR-1 binding predicate + required `ctx` | **CLOSED — shape half regression-detecting, prose half unpinned** | Shape: `consume_confirmation(record, *, operation_id, ctx: PolicyContext, now=None)` — `ctx` has **no default**. M9a (make it optional + skip `_bindings_match`) → exit 1, `test_consume_confirmation_ctx_binding_denies_mismatch`. Every call site passes one; the sole omission is a deliberate `pytest.raises(TypeError)` negative at `test_operator_mcp_policy.py:1692`. Prose: the binding predicate (b) IS folded into the frozen DUR-1 text in **both** locations — module docstring `:189-194` and `schemas/operator_mcp_confirmation.schema.yaml:74-78` — verified by direct read. **However M9b (delete clause (b) from the schema's frozen text) → EXIT 0, NOT DETECTED.** No test pins any frozen schema `description` text; see R5-NB-3. |

### BLOCKING

| ID | Sev | Finding | Location | Concrete failing scenario | Required fix |
|---|---|---|---|---|---|
| **R5-BLOCK-1** | **MED-HIGH** | **BLOCK-1 closed `audit_delivery.detail` and left its sibling `audit_event_id` — on the SAME `$def`, in the SAME commit — an unconstrained free-text field that durably records absolute paths and tracebacks.** This is BLOCK-2's exact shape (sibling field, one property over) applied to BLOCK-1's `$def`. The receipt schema's module description asserts "No field here ever carries a stack trace, environment variable, secret, or unrestricted filesystem path" — the same claim BLOCK-1 already found false once, still false. | `schemas/operator_mcp_receipt.schema.yaml:53-54` (the false claim), `:75-77` (`audit_event_id`), `:180-198` (`action_id`, `attempt_ref`), `:122-125` (`workspace_id`); `operator_mcp_policy.py:2031-2037` (`build_audit_delivery` length/type-checks `audit_event_id` but never redacts it) | **Empirically verified.** `build_audit_delivery("degraded", audit_event_id="/Users/alice/.config/research-foundry/serve.env")` emits the path **verbatim** and the embedding `terminal_receipt` validates with `errors: []`. Same for `audit_event_id='Traceback (most recent call last): File "/x.py", line 1'` — validates, verbatim. `audit_event_id`'s only constraints are `type: [string,"null"]` and `maxLength: 128`; the `not: pattern` guard added by BLOCK-1 is attached to `detail` **only**. The tell is inside the same file: `effect_receipt.effect_ref` — the structurally identical "opaque canonical reference" concept — **is** pattern-constrained (`^[A-Za-z0-9_\-:.]+$`, which excludes `/`), while `audit_event_id`, `action_id`, `attempt_ref` and `workspace_id` are not. `attempt_ref`'s own description says "never a filesystem path" with nothing enforcing it. | Apply `effect_ref`'s pattern (or at minimum the `not: pattern` guard) to `audit_event_id`, `attempt_ref`, and `action_id`; route `audit_event_id` through `_redact_and_bound` in `build_audit_delivery`; add a negative fixture for a path-shaped `audit_event_id`; and correct or qualify the module description's blanket claim at `:53-54`. |
| **R5-BLOCK-2** | **MED** | **The BLOCK-6 fix added a new raiser OUTSIDE `mint_confirmation`'s exception boundary — reopening NEW-8's own defect, in the function NEW-8 was raised against.** `mint_confirmation`'s docstring states: "Everything AFTER them is wrapped: any UNEXPECTED exception during minting is re-raised as a plain `RuntimeError('internal_error during confirmation minting')` with NO caller-supplied text". The new `resolve_operator_identity(paths)` call is **before** the `try:`, so it is not wrapped. False-authoritativeness + fix-the-layer-below. | `operator_mcp_policy.py:1563` (the derive call) vs `:1572` (`try:`); docstring claim `:1525-1540` | **Empirically verified.** With a malformed `foundry.yaml`, `mint_confirmation(ctx, paths=paths)` propagates a raw `yaml.parser.ParserError` uncaught — traceback frames `operator_mcp_policy.py:1563 → :1037 (resolve_operator_identity) → config.py:292 → yamlio.py:51`. The escaping message embeds **the malformed file's content verbatim**: `'while parsing a block mapping\n  in "<unicode string>", line 2, column 3:\n      operator_mcp:\n      ^\nexpected <block end>...\n       bad_indent: [unclosed'`. A tab-indentation variant escapes as a raw `yaml.scanner.ScannerError` carrying `\toperator_mcp:`. Neither is converted to the documented `RuntimeError`. (The absolute path is not leaked — PyYAML labels the stream `"<unicode string>"` — but the file *content* is, and AC OPM-7's requirement is about exception text reaching a caller at all.) `grep` confirms `mint_confirmation` has **zero production callers**, so nothing handles this today. | Move the `resolve_operator_identity` derive call INSIDE the `try:` (keeping the deliberate `ValueError` guards outside it), or wrap it in its own `try/except Exception -> RuntimeError("internal_error during confirmation minting") from None`. Add a test asserting a malformed `foundry.yaml` yields no raw `yaml.*` exception from `mint_confirmation`. Then correct the `:1525-1540` claim. |
| **R5-BLOCK-3** | **MED** | **BLOCK-3's `if/then` remedy was applied to `terminal_receipt` and not to `action_receipt` — the sibling `$def` that BLOCK-2 edited in the very same commit.** `action_receipt.reason_code`'s value domain is now closed (BLOCK-2) but its **presence** is coupled to `status` by description only, in **both** directions. `terminal_receipt` has both `allOf` branches; `action_receipt` has none. | `schemas/operator_mcp_receipt.schema.yaml:159-237` (`action_receipt`, no `allOf` at all) vs `:438-469` (`terminal_receipt`'s two branches); the unenforced claim is at `:206-207` ("Populated when `status` is `failed`/`skipped`") | **Empirically verified** with the schemas test's own `_errors()` helper: (B) `action_receipt` with `status: "failed"` and `reason_code` **entirely absent** → `errors: []`, validates — the exact hole BLOCK-3 closed one `$def` below. (D) `status: "completed"` **with** `reason_code: "guard_blocked"` → `errors: []`, validates — a completed action carrying a denial cause, which `terminal_receipt` explicitly forbids via `const: null`. (E) `status: "skipped"`, no reason code → validates. Control (F) `reason_code: "totally_bogus"` → correctly rejected, confirming BLOCK-2's enum is live. | Add the two `allOf` branches to `action_receipt` mirroring `terminal_receipt:438-469` — `if status in [failed, skipped] then required: [reason_code]` + `not: {const: null}`, and `if status == completed then reason_code: {const: null}`. Add negative fixtures for both directions. |
| **R5-BLOCK-4** | **MED** | **The BLOCK-6 fix turned NB-8's latent inconsistency into a hard, guaranteed failure on a second call site — and `mint_confirmation` has no way to avoid it.** `PolicyContext.for_configured_operator` accepts and threads `config=` (`resolve_operator_identity(paths, config=config)`); the new `mint_confirmation` derive call drops it (`resolve_operator_identity(paths)`), and `mint_confirmation` has **no `config` parameter at all**. Because round 4 made disagreement fatal, any caller using the documented `config=` seam is now hard-broken at mint. In a contract-freeze phase this bakes a trap parameter into the API P2 builds against. | `operator_mcp_policy.py:938` (threads `config`), `:1162` (`_check_identity_and_rbac` drops it — pre-existing NB-8), `:1563` (new mint derive, drops it), `:1486-1488` (signature has no `config`) | **Empirically verified.** A ctx built as `for_configured_operator(paths=A, config=FoundryConfig(paths=B))` then passed to `mint_confirmation(ctx, paths=A)` now raises `ValueError: mint_confirmation requires ctx.identity to match the identity resolved from configured local config …` where round 3 succeeded. `inspect.signature(mint_confirmation)` → `(ctx, *, paths=None, now=None)`. Fail-closed, so not a vulnerability — but it is a behaviour regression introduced by this round's fix, and it means the "derive fresh from configured local config" story is only correct for callers that never inject config. | Thread `config` through `mint_confirmation` (and `_check_identity_and_rbac`, closing NB-8 at the same time) so all three derivation sites agree; OR remove `config=` from `for_configured_operator` so the divergent seam does not exist. Add a test covering the config-injecting path end to end. |

### NON-BLOCKING (new this round)

| ID | Sev | Finding | Location |
|---|---|---|---|
| R5-NB-1 | LOW-MED | **`_PATH_LIKE` is an eight-prefix denylist, not an "absolute filesystem path" guard.** Of twelve probe strings, five absolute paths passed through `_redact_and_bound` **verbatim**: `/usr/local/share/foundry/rbac.db`, `/srv/foundry/rbac.db`, `/Library/Application Support/foundry/secret.key`, `/mnt/data/foundry/audit.db`, `/app/config/foundry.yaml`; the relative `.rf_state/rbac.db` also passes. `/Users/`, `/home/`, `C:\` are caught. The prescribed BLOCK-1 fix was implemented verbatim (plus `/tmp/` and `/root/`), so this is not a failure to remediate — but `build_error`'s docstring, `_PATH_LIKE`'s own comment and both schemas describe it as an absolute-path guard, which over-states an eight-prefix denylist. Impact is bounded: `audit_delivery.detail` is now closed-vocabulary, and P1's only internal `detail` producer is `_check_preflight`'s closed enum text — the exposure is P2-supplied `build_error(detail=…)`. | `operator_mcp_policy.py:627`, `:1854-1879`, `:1897-1901` |
| R5-NB-2 | LOW-MED | **The schema-side "defense-in-depth" `not: pattern` is strictly weaker than the code-side primary guard**, at three sites. Code `_PATH_LIKE` includes `[A-Za-z]:\\`; the schema patterns do not. Empirically `"[Errno 13] Permission denied: 'C:\\Users\\alice\\.config\\rf\\serve.env'"` → code matches (`True`), schema **validates** (`False`). No drift guard pins code↔schema pattern parity, in contrast to the reason-code enum, which does have a bidirectional one. | `schemas/operator_mcp_receipt.schema.yaml:100`; `schemas/operator_mcp_error.schema.yaml:90`, `:109` |
| R5-NB-3 | LOW-MED | **The frozen DUR-1 contract text is pinned by no test in either location.** M9b (delete the entire BINDING CHECK clause (b) from the schema's frozen predicate) → **exit 0**, zero failures. Grepping both test files for `DUR-1` / `BINDING CHECK` / `compare-and-swap` yields one hit, in a test docstring, not an assertion. Every round's frozen normative text — the thing P2's closeout is graded against — is freely deletable. Recommend a text-presence assertion over the module docstring and the schema description. | `tests/unit/test_operator_mcp_policy.py`, `tests/unit/test_operator_mcp_schemas.py` (absence) |
| R5-NB-4 | LOW-MED | **BLOCK-6's closure coverage is thinner than it reads — same shape as BLOCK-4, though not invalidating.** The autouse fixture monkeypatches `policy.resolve_operator_identity` module-wide to a constant lambda, and `test_mint_confirmation_rejects_a_forged_identity` does not restore the real function — so the new derive call resolves to the fixture constant and the "derives from **real configured local config**" half is never exercised. The *comparison* is genuinely pinned (M6a and M6b both DETECTED), so the closure holds; but a `mint_confirmation` test using `_REAL_RESOLVE_OPERATOR_IDENTITY` plus a `tmp_foundry` identity block is the missing evidence. | `tests/unit/test_operator_mcp_policy.py:90-106`, `:406` |
| R5-NB-5 | LOW | **BLOCK-5's stale prose survives inside the function it was about.** The module docstring was correctly rewritten, but `_check_audit_health`'s own inline comment still narrates the superseded round-2 behaviour in the present tense — "PROBE ON DEMAND exactly once per workspace: read the persisted state first (cheap); only when it has NEVER been probed … run a REAL live probe" — immediately above code that probes unconditionally. The NEW-19 correction follows it, so a careful reader recovers, but the first paragraph reads as current. | `operator_mcp_policy.py:1203-1214` |
| R5-NB-6 | LOW | **`detail_code` is unconstrained by `status`.** All 3 × 4 combinations validate, including `status='delivered'` with `detail_code='write_failed'` — a "delivered" audit disposition carrying a failure explanation. The closed vocabulary bounds the *text* but not its *coherence with the status it accompanies*. | `operator_mcp_policy.py:1983-2049`; `schemas/operator_mcp_receipt.schema.yaml:63-100` |
| R5-NB-7 | LOW-MED | **The whole-module identity claim has an unstated precondition.** `:324-327` asserts that no value forced onto `ctx.identity` "through any of the three exported confirmation-lifecycle functions, can ever produce, verify, or consume a confirmation whose durable content diverges" from configured truth. That holds for an **authentic** record (verified: authentic record + forged ctx → `confirmation_mismatch` / `None`). It does not hold once the record is also fabricated: with a hand-built record whose `actor` is the forgery and a matching forged ctx, `verify_confirmation` returns `outcome='accepted'`, `PolicyDecision(allowed=True, stage='confirmation')`, and `consume_confirmation` returns a fully `consumed` record carrying `actor.user_id='mallory'`, `workspace_id='ws-evil'`. Neither function re-derives identity; `_bindings_match` compares two attacker-controlled sides. Under BLOCK-6's own accepted threat model (`object.__setattr__`, i.e. in-process access), fabricating a dict is no harder than forging a field. `authorize_operation` correctly denies (`stage='rbac'`, `identity_denied`). The claim should state its precondition — records MUST originate from `mint_confirmation` or P2's durable store — rather than asserting the property unconditionally. | `operator_mcp_policy.py:324-327`, `:1615-1639`, `:1642-1761`, `:1764-1826` |

### NON-BLOCKING carried forward from round 4

| ID | Status | Evidence |
|---|---|---|
| NB-1 `input_payload` has no SIZE bound | **STILL OPEN** | `:1116` is count-only. Empirically 32 keys × 300 KB = **9,600,086 bytes accepted** (`allowed=True, stage='capability'`); 100,000 nested keys also accepted. Comment at `:509` still calls the in-code enforcement "what actually protects every caller today". |
| NB-2 `check_tool_name` has zero callers | **STILL OPEN** | `:1091`, `:397`. Only non-`src` hits are tests. The docstring self-declares it. |
| NB-3 `(?i)` is not ECMA-262 | **STILL OPEN** | The same three sites as R5-NB-2. |
| NB-4 public `now=` clock seam | **STILL OPEN** | `:1384`, `:1487`, `:1647`, `:1769` — all four still in `__all__`. |
| NB-5 `consume_confirmation`'s optional `ctx` | **FIXED** | `:1764-1770`, no default. See BLOCK-9. |
| NB-6 serve-extra test blocks hard-coded modules | **STILL OPEN** | `tests/unit/test_operator_mcp_serve_extra_boundary.py:42` still `{"fastapi","uvicorn","starlette"}`; still only two tests, neither running `evaluate_policy`/`mint_confirmation` under the blocker. (`pyproject` `serve = ["fastapi>=0.111","uvicorn[standard]>=0.29"]` — `starlette` is transitive, so the hard-coded set drifts in the safe direction here.) |
| NB-7 module-wide autouse identity monkeypatch | **STILL OPEN — materially worse** | Now also blinds the new BLOCK-6 mint derive. See R5-NB-4. |
| NB-8 `config` not threaded to `_check_identity_and_rbac` | **STILL OPEN + escalated** | Round 4 added a second config-blind derive site and made disagreement fatal. See R5-BLOCK-4. |
| NB-9 audit-probe write amplification | **STILL OPEN (by design)** | `:1240` unconditional. Measured 1 probe per `evaluate_policy` and 1 per `authorize_operation` → **2 write-then-read-then-delete cycles per mint→execute flow**. |
| NB-10 one-directional `_OPERATION_ROLES` completeness check | **STILL OPEN (partially mitigated in a test)** | `:608` still only `OPERATION_KINDS ⊆ keys`. A bidirectional key-set assertion exists at `tests/unit/test_operator_mcp_policy.py:660` but predates round 4; non-empty values and `roles ∈ rbac.ROLE_PERMISSIONS` remain unasserted (`ROLE_PERMISSIONS` appears in this module only in a prose comment at `:539`, never imported). |
| NB-11 two receipt-shape gaps | **STILL OPEN (both halves)** | `checkpoint` (`:278-322`) still has no `workspace_id` under `additionalProperties: false`; `operation_receipt.status` (`:147`) still admits `denied` with no reason field anywhere in the `$def`. |

### Validation transcript (real, as run — exit codes captured without an intervening pipe)

```
$ cd /Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1

# A) targeted operator-mcp unit suites
$ .venv/bin/python -m pytest tests/unit/test_operator_mcp_policy.py \
    tests/unit/test_operator_mcp_schemas.py \
    tests/unit/test_operator_mcp_serve_extra_boundary.py -q --tb=no -rf
EXIT=0
ANSI-stripped `grep -c FAILED` = 0
........................................................................ [ 40%]
........................................................................ [ 81%]
.................................                                        [100%]
$ ... --collect-only -q | tail -3
tests/unit/test_operator_mcp_policy.py: 121
tests/unit/test_operator_mcp_schemas.py: 54
tests/unit/test_operator_mcp_serve_extra_boundary.py: 2      # 177 total

# B) full suite minus the two known-collection-error files
$ .venv/bin/python -m pytest tests/ -q --tb=no -rf \
    --ignore=tests/test_verification_pediatric_cds.py \
    --ignore=tests/test_verification_seam001_gate_composition.py
EXIT=1
ANSI-stripped `grep -c FAILED` = 16   # byte-identical set to round 4; zero in operator-mcp files

# D) flake8, errors-only (this project's CLAUDE.md convention)
$ .venv/bin/python -m flake8 src/research_foundry/services/operator_mcp_policy.py \
    --select=E9,F63,F7,F82
EXIT=0   (no output)

# E) all four operator schemas parse
$ .venv/bin/python -c "import yaml,glob;[print(f,'OK' if yaml.safe_load(open(f)) else 'EMPTY') for f in sorted(glob.glob('schemas/operator_mcp_*.schema.yaml'))]"
EXIT=0
schemas/operator_mcp_confirmation.schema.yaml OK
schemas/operator_mcp_error.schema.yaml OK
schemas/operator_mcp_operation.schema.yaml OK
schemas/operator_mcp_receipt.schema.yaml OK

# F) tree state (before, during and after the 12-mutation sweep)
$ git status --porcelain
(empty)
$ git log --oneline -1
e4c76b9 fix(operator-mcp): close all nine OPM-1.G round-4 blocking findings
```

The 16 full-suite failures match the pre-existing set verified identical at pre-change commit
`15101a4` — **zero regressions**. All mutation work was done **in place** and restored with
`git checkout --`, with `git status --porcelain` verified empty between every mutation, avoiding the
`pythonpath = ["src"]` scratch-tree trap entirely.

### Standing cautions carried forward

- **This is the first round where every claimed closure held.** Nine of nine closed; eight of nine
  empirically regression-detecting (BLOCK-5 is prose-only, verified by reading; BLOCK-9's prose half
  is unpinned — R5-NB-3). BLOCK-4's previously-invalid closure evidence is now valid and holds under
  per-test isolation. The `_persist_health_row` pattern is the right fix and should be the template
  whenever a test fakes a function whose side effect is the thing under test.
- **Two of the four recurring classes recurred again**: fix-the-layer-below (R5-BLOCK-1 sibling
  field, R5-BLOCK-3 sibling `$def` — both inside the very `$def`/file the round-4 commit edited) and
  false authoritativeness (R5-BLOCK-1's schema claim, R5-BLOCK-2's docstring claim, R5-NB-1's
  "absolute path" framing, R5-NB-7's whole-module claim). Fail-open-by-omission and
  unsafe-behaviour-pinned-by-a-test did **not** recur. **Every new blocking finding this round is in
  a field, a `$def`, or a line adjacent to one that was correctly fixed** — the fixes themselves are
  sound.
- **`schemas/operator_mcp_receipt.schema.yaml` has now yielded a finding in every round it has been
  examined** (NEW-20, NEW-21, BLOCK-1, BLOCK-2, BLOCK-3, NB-11, and now R5-BLOCK-1 and R5-BLOCK-3).
  Recommend a systematic per-`$def` × per-property sweep — enumerate every property in all five
  `$defs` and classify each as closed-enum / patterned / bounded-open / unconstrained — rather than
  another finding-driven pass.
- **The `mint_confirmation` boundary should be re-adjudicated once more** after R5-BLOCK-2 and
  R5-BLOCK-4 are fixed: it is the one exported function that is neither `PolicyDecision`-shaped nor
  fully wrapped, has zero production callers, and has now been the locus of a finding in three
  consecutive rounds (NEW-8, BLOCK-6, R5-BLOCK-2/R5-BLOCK-4).
- The plan's documented validation prefix `PYTHONPATH=$PWD/src` remains **decorative** (pytest's
  `pythonpath = ["src"]` ini setting is inserted ahead of it). Unchanged from round 4.

### OPM-1.G verdict

**CHANGES_REQUESTED.** Four blocking findings: R5-BLOCK-1 (MED-HIGH), R5-BLOCK-2 (MED), R5-BLOCK-3
(MED), R5-BLOCK-4 (MED). Seven new non-blocking (R5-NB-1 … R5-NB-7) plus ten carried forward
(NB-1, NB-2, NB-3, NB-4, NB-6, NB-7, NB-8, NB-9, NB-10, NB-11; NB-5 fixed) = seventeen non-blocking.
All nine round-4 blocking findings are closed and none should be reopened. Recommended fix order:
R5-BLOCK-2 (smallest, and it is an exception-boundary regression), then R5-BLOCK-4 (same function,
same call), then R5-BLOCK-3 and R5-BLOCK-1 (both schema-only, both in the same file, best done as
one pass together with the systematic per-`$def` sweep recommended above).

---

## FIND-P1-R4-CLOSURE — round-4 remediation record (commit `e4c76b9`)

Round 4 (`FIND-P1-R4`) returned CHANGES_REQUESTED with nine blocking findings. All nine were
remediated in `e4c76b9`. **The round-5 gate independently re-verified all nine as CLOSED**, and eight
of nine as regression-detecting under in-place mutation. This section exists because round 4 got no
closure section at the time — the closure lived only in `git log`, which Karen correctly flagged as a
ledger/reality mismatch.

| ID | Round-5 re-verdict | Evidence |
|---|---|---|
| BLOCK-1 | CLOSED, regression-detecting | 3 mutations, all exit 1. Vocabulary genuinely closed (`detail=` → `TypeError`; unknown `detail_code` → `ValueError`; no fail-open default). All 15 status×detail_code blocks validate. `build_error`'s legitimate path unbroken. |
| BLOCK-2 | CLOSED for the value domain, regression-detecting | M2 → 3 tests fail, including the bidirectional drift guard. **Presence coupling was NOT closed** → reopened as R5-BLOCK-3. |
| BLOCK-3 | CLOSED, regression-detecting | M3 → exit 1. Applied to `terminal_receipt` only → sibling gap reopened as R5-BLOCK-3. |
| BLOCK-4 | CLOSED, **evidence now valid** | Three latch-sensitive tests fail STANDALONE, one invocation each. The `_persist_health_row` sqlite helper is what fixed the hollow evidence. |
| BLOCK-5 | CLOSED (prose) | All three false docstring claims corrected; `get_health_state` confirmed to have zero call sites. |
| BLOCK-6 | CLOSED, regression-detecting | M6a AND M6b both detected — the comparison itself is pinned, not merely the actor's source. |
| BLOCK-7 | CLOSED, regression-detecting | M7 → exit 1. `model_provider`/`source_sensitivities` addressed by narrowing the claim (the permitted option), not by populating them. |
| BLOCK-8 | CLOSED, regression-detecting | M8 → exit 1; correctly scoped — `detail` still survives on `identity_denied`. |
| BLOCK-9 | CLOSED; **one evidence gap** | Shape half regression-detecting (M9a → exit 1). Binding predicate IS in both frozen texts, but **M9b (deleting it from the schema) → exit 0, NOT DETECTED** — no test pins frozen-contract prose anywhere. Tracked for the round-5 remediation. |

**Orchestrator note on evidence standard.** The `e4c76b9` commit message stated the nine were
"independently re-verified by the orchestrator with adversarial probes". That is accurate but was
NOT equivalent to a per-finding revert-and-confirm-failure record: BLOCK-4 was verified by true
in-place mutation, the other eight behaviourally. Karen flagged this as the same evidentiary standard
that had already failed once (BLOCK-4 itself). The round-5 gate has since supplied the missing
mutation matrix (11 of 12 detected; M9b the sole gap), which is what makes this closure section
trustworthy rather than self-asserted.

---

## FIND-P1-KAREN — final adjudication verdicts (round 5, tree `e4c76b9`)

Karen ran read-only against `e4c76b9`. Overall: **FIX-REQUIRED** — "the code has earned a pass; the
evidence has not."

### Adjudication 1 — `governance.py` serialization-barrier write: **RATIFY WITH CONDITIONS**

Of the three round-3 grounds: (b) restoration of `redact_payload`'s documented "additional" contract
**holds** (its own docstring says *additional*; the pre-change code replaced rather than added), and
(c) strictly fail-closed **holds** (`merged = list(_BUILTIN_SECRET_PATTERNS)` then append-if-absent —
config can only GROW the detection surface).

(a) "provable no-op for the shipped config" is **FALSE**. Three shipped patterns differ from the
built-in literals only in escaping (`['\"]` in the Python literal vs `['"]` in YAML). They are
regex-equivalent, so detection outcomes and gate decisions are identical — but the merged list is 25,
not 22, and `scan_secrets` returns duplicates; `scan_paths` interpolates `len(hits)`, so a flagged
file now reports "2 match(es)" where it reported 1. Non-gating (`if hits:` is truthiness), no test
asserts exact counts. Severity **LOW**.

CONDITIONS: (1) correct the claim wherever recorded — done, see the inline correction in
`FIND-P1-R3`'s Karen queue above; (2) dedupe the merged list on compiled-pattern equivalence OR
explicitly accept the duplicate-count cosmetic — **accepted as cosmetic**, deliberately not fixed, to
avoid touching a serialization-barrier file again for a non-gating count; (3) **OUTSTANDING — requires
the human integration owner**: a reviewer can ratify the CONTENT of a barrier-file write, but only the
declared file owner can waive the OWNERSHIP barrier. That acknowledgement is not something any agent
in this loop can supply.

### Adjudication 2 — FIND-P1-B, the net-new `_OPERATION_ROLES` primitive: **ACCEPT, with a required drift guard**

Delegation to `api/auth/rbac.py` is genuinely infeasible as a direct import: `rbac.py:91` imports
fastapi at module level, and NEW-23 requires `operator_mcp_policy` to import in a base install. Karen
noted the inverted form IS feasible (relocate `ROLE_PERMISSIONS` to a serve-free module and re-export,
exactly as was done for `AuthIdentity` and `resolve_workspace_isolation_active`) but explicitly did NOT
require it — a 13-entry map does not justify relocating a security-critical matrix at the tail of a
five-round gate.

REQUIRED instead: the alignment must stop being a comment. Today it is one prose line with zero
mechanical linkage, and NEW-22 already found two real privilege escalations in this map. A test
asserting per-kind alignment against `ROLE_PERMISSIONS` is feasible today (tests run WITH the serve
extra, so a test may import both modules even though the module may not). **Tracked into the round-5
remediation as Part C.**

**FIND-P1-B is hereby RESOLVED** (superseding its `open — carry to Karen` status): the primitive is
accepted; the drift guard is the condition.

### Adjudication 3 — `governance.preflight()` deviation: **ACCEPT DEVIATION, AMEND THE DECISIONS BLOCK**

`guard_check()` is genuinely wired (`_check_guard` calls `governance.guard_check`). `preflight()` is
NOT — `_check_preflight` is a locally-defined operation-shape check. The deviation is substantively
correct: `governance.preflight(intent, ibom, routing, profile)` consumes run-scoped artifacts that do
not exist at authorization time, so calling it would mean passing empty dicts for a vacuous pass —
fail-open-by-omission, the class BLOCK-7 was raised on.

The naming is the real defect: the stage is named `preflight`, the reason code is `preflight_failed`,
and the frozen decisions block says `governance.preflight()` runs. A P2 author would reasonably believe
a governance gate fires that does not exist. **Decisions-block line 30 amended** (see
`.codex/worknotes/research-foundry-operator-mcp/decisions-block.md`), and the P2 obligation
(`OPM-DF-preflight`) recorded there: P2 MUST wire it once a run exists, with an artifact that fails if
unwired.

### Adjudication 4 — NEW-23 serialization-barrier + auth-package writes: **RATIFY (unconditional)**

Verified empirically by Karen: `AuthIdentity` resolves to the SAME class object
(`0x95b11dc10`) via `auth_identity`, `api.auth.provider`, `api.auth.rbac` and `services.audit_service`
— so `isinstance` across all ~487 references is unchanged, not merely "probably compatible". Exactly
one definition of each relocated symbol exists in the tree. Both re-exports are in the re-exporting
module's `__all__`. `scope.py`'s removed imports have no dangling references. The relocated
`resolve_workspace_isolation_active` body is identical, so WKSP-304 isolation behaviour is byte-identical
for `catalog_service`, `builder_service`, `AgentJobService` and `audit_service`. Textbook pure relocation.

### Karen's process finding (the durable lesson)

Four points, five rounds, ~2.4M+ tokens. The gate is not malfunctioning — it has found genuine defects
every round, including two real privilege escalations. The **loop shape** is what malfunctions: each
round fixes findings and ASSERTS closure; the next round discovers the closure evidence was hollow and
generates a fresh finding set from the remediation itself.

**The fix is one process change: move mutation verification into the FIX step, not the next REVIEW
round.** A remediation is not submitted until each fix has been reverted and shown to break a named
test. That alone would have collapsed rounds 4 and 5 into round 3. This generalises well beyond this
phase and should be pushed through `op story capture`.

---

## NB TRIAGE — explicit disposition of every non-blocking finding

DoD requires each non-blocking item FIXED or EXPLICITLY DEFERRED WITH A REASON. No silent drops.

> **On NEW-15 / NEW-16 / NEW-17 / NEW-24 / NEW-25:** their original text was never captured and the
> round-3 reviewer's context is gone. The round-4 gate stated plainly that the original wording is
> **not recoverable** and supplied an independently re-derived set (NB-1…NB-11) at the same severity
> band rather than fabricating a reconstruction. That judgement is accepted and recorded here as-is;
> the NB-n set below is the authoritative non-blocking record for P1.

| ID | Disposition | Reason |
|---|---|---|
| NB-1 `input_payload` has no byte bound | **FIX** (round-5 remediation) | `payload_too_large` has shape producers but none for size; 32 keys × 300 KB passes every check, is SHA-256'd and embedded in a durable confirmation. |
| NB-2 `check_tool_name` has zero callers | **DEFER to P5**, with an entry gate | The transport boundary it guards is P5's; no server exists in P1 to wire it to. Deferring is correct, but it MUST ship as a P5 acceptance criterion with an artifact that fails if unwired — otherwise it is the same "promised gate that never runs" shape as Adjudication 3. |
| NB-3 `(?i)` is not ECMA-262 | **FIX** (round-5 remediation) | Real portability hole with a security consequence: BLOCK-1 proved the schema `not.pattern` is load-bearing, and a validator that cannot compile a `pattern` commonly SKIPS the keyword, silently deleting the defence. These schemas carry public `$id`s. |
| NB-4 public `now=` clock seam | **DEFER to P2** | Documented; closing it removes a seam four exported functions rely on for testing. The abuse it enables (P2 threading a request-supplied timestamp) is a P2 review item. Recorded as a P2 acceptance criterion. |
| NB-5 `consume_confirmation` optional `ctx` | **SUPERSEDED** | Fixed by BLOCK-9 — `ctx` is now a required keyword argument. |
| NB-6 serve-extra test blocks 3 hard-coded names | **FIX** (round-5 remediation) | Blocked set is hard-coded rather than derived from `pyproject.toml`'s `[serve]` extra, and the test never runs a policy stage under the blocker — so a serve-gated import reachable only from `evaluate_policy` would still pass. |
| NB-7 autouse fixture patches the NEW-18 Layer-3 seam | **FIX (test-only)** (round-5 remediation) | Not a defect — the property was confirmed empirically — but ~100 tests exercise only the equality-commitment half, never real derivation. P2 would otherwise be the first real exercise of identity derivation. |
| NB-8 `_check_identity_and_rbac` ignores `config` | **FIX** (round-5 remediation) | Same root cause as R5-BLOCK-4: the factory derives with `config=`, the authorization stage derives without it, so a caller passing a custom `config` gets a context that always denies. Fail-closed, but a silent alignment trap. Fixed once for all three derivation sites. |
| NB-9 audit-probe write amplification | **FIX (bounded) + DOCUMENT** (round-5 remediation) | Self-inflicted by NEW-19's unconditional probe: INSERT+SELECT+DELETE on the authorization hot path, ≥2× per operation. Under the concurrency DUR-1 contemplates, SQLite write-lock CONTENTION is reported identically to genuine unhealth → spurious `audit_unhealthy`. Security-safe (fail-closed; `retryable=True` is now honest) but an availability regression that must be named, not left implied. |
| NB-10 completeness check is one-directional | **FIX** (round-5 remediation) | Cheap hygiene: assert set EQUALITY (catching a stale entry after a rename), non-empty role sets, known role names. |
| NB-11 receipt-shape gaps | **DEFER to P2**, named | `checkpoint` lacks `workspace_id` (relevant under WKSP-304) and `operation_receipt.status: denied` has no reason field. Both are P2 persistence-shape decisions — P2 owns the durable store. Recorded as a named P2 entry-gate item, not silently dropped. |
| R5-NB-1 … R5-NB-7 | **CARRIED** | Seven further non-blocking items raised by the round-5 gate; see `FIND-P1-R5`. Triaged with the round-5 remediation. |

Net: **FIX 7** (NB-1, 3, 6, 7, 8, 9, 10) · **DEFER 3 with named owners and entry gates** (NB-2 → P5;
NB-4, NB-11 → P2) · **SUPERSEDED 1** (NB-5) · **7 carried** (R5-NB-*).

---

## FIND-P1-CLOSEOUT — OPM-1.G closed by OWNER ACCEPTANCE (2026-07-29)

> ⚠ **This is NOT a gate `APPROVED` verdict.** The last machine verdict on OPM-1.G is
> **`CHANGES_REQUESTED` (round 5, `FIND-P1-R5`)**. P1 is being closed by an explicit **human owner
> decision** to defer the round-6 re-gate and accept the current tree so P2 can proceed. Anyone reading
> this later should not treat P1 as gate-approved — it is **owner-accepted with a deferred re-gate and
> named residual risk**.

**Accepted tree:** `fce17e1` on branch `worktree-operator-mcp-v1` (draft PR #7, base main `65d658d`).
Working tree clean. NOT merged to main.

### Owner approvals recorded

| # | Item | Decision |
|---|---|---|
| 1 | **Round-6 consolidated security re-gate** | **DEFERRED** by owner decision. The four round-5 blocking findings (R5-BLOCK-1…4) were remediated in `fce17e1` and each independently re-probed by the orchestrator, but the resulting tree was **never adversarially re-attacked**. Recorded as `OPM-DF-regate` below. |
| 2 | **`governance.py` serialization-barrier write** (Karen Adjudication 1, condition 3 — the one item no agent could close) | **ACKNOWLEDGED by the integration owner.** A reviewer could ratify the write's content; only the declared file owner can waive the ownership barrier. That waiver is hereby given. Conditions 1 (correct the false "provable no-op" claim) and 2 (accept the duplicate-match-count cosmetic) were already discharged — see the inline correction in `FIND-P1-R3` and Karen Adjudication 1. |
| 3 | **`audit_service.py` / `api/auth/{provider,scope}.py` / `config.py` writes** (NEW-23) | **ACKNOWLEDGED.** Karen ratified these unconditionally on the merits (verified same-class-object re-export; WKSP-304 behaviour byte-identical). Owner waiver of the `audit_service.py` ownership barrier given here for completeness. |
| 4 | **P1 acceptance / P2 unblock** | **GRANTED.** OPM-1.1–1.4 are implemented and validated; P2 may proceed against this contract. |

### Residual risk explicitly accepted

The owner is accepting these knowingly. They are not defects being hidden — they are open items with
named owners.

1. **`OPM-DF-regate` — the round-6 re-gate.** `fce17e1` closed four blockers and seven non-blocking
   items and has not been re-attacked. Every prior round found new defects *adjacent to* correct fixes
   (R3's fixes produced 4 of R4's 9; R4's produced 4 of R5's 4). The base rate says a round 6 would
   likely find **1–3 further findings, most probably in `operator_mcp_receipt.schema.yaml`.**
2. **`operator_mcp_receipt.schema.yaml` is the highest residual-risk surface.** It has yielded a finding
   in **every single round it was examined** (NEW-20, NEW-21, BLOCK-2, BLOCK-3, R5-BLOCK-1, R5-BLOCK-3).
   The round-5 remediation performed the recommended systematic per-`$def` × per-property sweep, but that
   sweep is itself un-reviewed. **P2 should treat this schema as still under-reviewed.**
3. **NB-7 coverage gap (the one P2 must plan around).** An autouse fixture monkeypatches
   `policy.resolve_operator_identity` for the whole policy test module — the exact seam that IS NEW-18
   Layer 3 — so ~100 tests exercise the equality-commitment half and never real derivation. Real
   derivation is covered by only a handful of tests. **P2's first live run against a real workspace will
   be the first substantial exercise of identity derivation.** Budget for it.
4. **NB-9 availability tradeoff (introduced deliberately).** NEW-19's unconditional audit probe performs
   INSERT+SELECT+DELETE on the authorization hot path, ≥2× per operation. Under the concurrency DUR-1
   contemplates, SQLite write-lock contention can surface as a spurious `audit_unhealthy` denial.
   Security-safe (fail-closed, and `retryable=True` is now honest) but an availability regression.
5. **Zero production callers.** P1 is a contract-freeze phase by design; the surface has never been
   exercised by a real transport. Correct for the phase, but it means "works" is unproven end-to-end.
6. **Deferred non-blocking items** carry named owners: **NB-2 → P5** (`check_tool_name` has zero callers;
   must ship with an artifact that FAILS if unwired), **NB-4, NB-11 → P2**, **`OPM-DF-preflight` → P2**
   (`governance.preflight()` is named in the frozen contract but never invoked — decisions-block line 30
   amended to say so), **R5-NB-1…7 → P2 triage**.

### P2 entry conditions (carried forward, not optional)

- Treat `operator_mcp_receipt.schema.yaml` as under-reviewed; re-attack before building durable
  persistence on it.
- Wire `governance.preflight()` at the run layer with a failing-if-unwired artifact (`OPM-DF-preflight`).
- Exercise real identity derivation early (NB-7).
- Per the plan's revised gate structure, **P2's gate is security-with-AC-mandate, then Karen** — do not
  substitute a validator; durability/atomicity is a security property and a validator will approve a
  read-then-write CAS.
- **Adopt the process change below before P2 execution begins.**

### The process change P2 must adopt (highest-leverage item from this phase)

**Mutation verification belongs in the FIX step, not the next REVIEW round.** A remediation is not
submitted until each fix has been **reverted in place, shown to break a NAMED test, and restored**.
Rounds 4 and 5 of this gate exist almost entirely because closure was asserted rather than demonstrated
(BLOCK-4: a correct fix shipped with four purpose-built tests, all four of which PASSED on revert).

Captured through the Signal→System pipeline for the pre-P2 optimization pass:

| Field | Value |
|---|---|
| `op story` record (use this) | **`806e4667-acd6-4ec4-9883-130ae95ec08a`** — status `backlog`, project `research-foundry`, domains `review-gates, agent-orchestration, process, security-review, test-quality` |
| Superseded duplicate (ignore) | `8ff0255b-0b0e-4e4f-8864-f6d2a82e2d1f` — status `hold`, untitled (captured before frontmatter was added) |
| AAR source of truth | `.claude/worknotes/observations/2026-07.md` on branch `worktree-operator-mcp-v1` |
| Cross-session memory | `~/.claude/projects/-Users-miethe-dev-homelab-development-research-foundry/memory/operator-mcp-p1-gate-economics.md` |
