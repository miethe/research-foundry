---
title: "In-flight findings: Research Foundry Operator MCP"
schema_version: 2
doc_type: report
report_category: findings
status: in_progress
created: 2026-07-28
updated: 2026-07-28
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
