---
title: "Feature Contract: Verifier-gate hardening — URL-existence check + abstain band + residual-unsupported-rate"
schema_version: 2
doc_type: feature_contract
status: draft
created: 2026-06-23
updated: 2026-06-23
feature_slug: "verifier-url-check-abstain-band"
category: "enhancements"
estimated_points: 6
tier: 1
owner: null
priority: high
risk_level: medium
changelog_required: true
related_documents:
  - docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md
spike_ref: null
prd_ref: null
plan_ref: null
commit_refs: []
pr_refs: []
files_affected: []
---

# Feature Contract: Verifier-gate hardening — URL-existence check + abstain band + residual-unsupported-rate

> Derives from completed research run **RIB-002** ("Claim-traceability and hallucination-mitigation"),
> IntentTree node `node_01KVQYKB4SQ1AHK52X6J61G3XQ`, high evidence. The research recommends pre-hoc
> grounded generation plus a mandatory post-hoc atomic-claim verifier gate, hardened with a
> URL-existence check, an "abstain band" for borderline claims, and management of a
> residual-unsupported-rate.

## 0. Grounding & Framing (read first)

RF **already has** the mandatory deterministic post-hoc verifier gate this research recommends:
`src/research_foundry/services/verification.py::verify_report()` (≈lines 335–715) enforces spec §12.3.
It already runs the checks `material_claims_have_claim_ids`, `all_claim_ids_exist`,
`supported_claims_have_source_cards`, `inferences_have_basis`, `*_is_labeled`,
`unsupported_claims_block_publish`, and `work_sensitive_claims_block_public_report`, with exit-code
precedence **SCHEMA → GOVERNANCE → UNSUPPORTED → OK**. Claim statuses
(`supported` / `inference` / `mixed` / `contradicted` / `speculation` / `unsupported`) and
`[claim:clm_NNN]` tag tracing already exist.

**This contract is an ENHANCEMENT to that existing gate, not a new gate.** The net-new work is the
three sub-features below; the established gate, its checks, and its exit-code precedence must remain
behaviorally identical when the new checks are disabled.

---

## 1. Goal

Harden the existing deterministic verifier gate with three opt-in, offline-safe additions —
a URL-existence reachability check on source locators, an abstain band for borderline material
claims, and a computed-and-emitted residual-unsupported-rate per run — without changing the existing
gate's behavior or exit-code precedence when the additions are disabled.

---

## 2. User / Actor

- **Primary user**: RF operator / research-run author who runs `rf verify` and relies on the claim
  ledger as the authority for what is publishable.
- **Secondary users**: downstream verification reviewers (`rf_claim_auditor` agent) and CCDash
  dashboards that consume run telemetry to track research quality over time.

---

## 3. Job To Be Done

When **a research report has passed the existing binary supported/unsupported gate but still carries
risk** (dead source URLs, claims whose support is genuinely borderline, or a creeping rate of
unsupported material claims), the operator wants to **probe source reachability, mark borderline
claims into an explicit "abstain" band rather than force a binary verdict, and see the
residual-unsupported-rate surfaced**, so they can **trust the gate's verdict and catch quality
erosion that today's binary checks miss — without breaking RF's offline-first, deterministic test
guarantees.**

---

## 4. Scope

### In Scope

- **URL-existence check**: an opt-in reachability probe over source-card `locator` URLs (HTTP HEAD/GET),
  results recorded **per source** as telemetry. **Non-blocking and offline-safe by default**; gates
  only when explicitly enabled.
- **Abstain band**: a configurable rule that classifies a material claim's support as **borderline**
  and marks/withholds it into an `abstain` band instead of forcing `supported`/`unsupported`.
- **Residual-unsupported-rate**: compute the rate of unsupported material claims per run and emit it
  (telemetry + verification result), with an **optional, off-by-default** threshold guard.
- Configuration surface for all three (under the existing `claim_policy` / verification config), with
  offline-safe defaults.
- Unit tests for each sub-feature using offline fixtures (no live network in the deterministic suite).

### Out of Scope

- Pre-hoc grounded generation (RIB-002 also recommends this; tracked separately — this contract is the
  post-hoc verifier hardening only).
- Claim segmentation / alignment improvements (RIB-001) and contradiction_log v1 (RIB-003).
- Any change to the existing checks' semantics or the SCHEMA→GOVERNANCE→UNSUPPORTED→OK precedence when
  the new checks are disabled.
- A persistent reachability cache / scheduled re-probing service (file-backed telemetry only for now).
- Networked behavior in CI / the deterministic test suite (live probing is opt-in and excluded from
  deterministic fixtures).
- runs-viewer / CCDash UI rendering of the new metric (emit only; rendering is downstream).

---

## 5. UX / Behavior Requirements

- **Default (offline-safe)**: running `rf verify` with no new flags behaves exactly as today — no
  network calls, identical checks, identical exit codes. The new checks are dormant.
- **URL check, opt-in**: when enabled (flag/config, e.g. `--check-urls` or
  `verification.url_check.enabled: true`), the verifier probes each unique source `locator` that is a
  URL. Each probe records a reachability result (`reachable` / `unreachable` / `skipped` / `error`)
  with status code where available. On network failure, DNS failure, or timeout the probe **degrades to
  `skipped`/`error` and never raises** — the run is not failed by an unreachable network unless URL
  gating is explicitly turned on.
- **URL gating (opt-in within opt-in)**: only when an explicit `url_check.gate: true` is set does an
  `unreachable` URL contribute an error-severity check; absent that, URL results are advisory telemetry
  only and do not affect the exit code.
- **Abstain band**: a material claim whose support score/condition falls inside the configured band is
  reported with an `abstain` outcome and a per-claim location, **withheld from the unsupported set** (so
  it does not by itself trigger UNSUPPORTED) while being clearly flagged. The documented default rule
  and band bounds are stated in §6; the band is empty by default unless the operator opts in.
- **Residual-unsupported-rate**: always computed (count of unsupported material claims ÷ total material
  claims) and surfaced in the verification result and telemetry. If a threshold guard is configured and
  exceeded, it contributes an error-severity check (off by default).
- **Determinism**: with the new checks disabled, output (`reviews/verification.yaml`, exit code,
  ledger `verification_status`) is byte-stable vs. current behavior. Probe ordering is deterministic
  (sorted unique locators).

---

## 6. Data Requirements

- **Entities affected**:
  - `reviews/verification.yaml` (verification result) — gains a `url_reachability` block (per-source
    results), an `abstain` list, and a `residual_unsupported_rate` field. Additive only.
  - Claim ledger `verification_status` — unchanged in meaning; abstain-banded claims are reported, not
    re-statused in the ledger (the six existing statuses are not extended in this contract).
- **New fields** (additive, all optional / default-empty):
  - `url_reachability`: list of `{ locator, status: reachable|unreachable|skipped|error, http_status?, checked_at? }`.
  - `abstain`: list of `{ claim_id, reason, location }`.
  - `residual_unsupported_rate`: float in `[0,1]` (with `unsupported_material_count` /
    `material_claim_count` for transparency).
- **Config (under existing verification/`claim_policy` config; offline-safe defaults — DECISION)**:
  - `url_check.enabled: false`, `url_check.gate: false`, `url_check.timeout_s: 5`,
    `url_check.method: head` (fallback to GET on 405).
  - `abstain_band.enabled: false`, and a **documented default rule**: a material claim is abstained when
    it is borderline between supported and unsupported — concretely, when its support evidence is
    present-but-insufficient (e.g. `mixed` status, or a support score in the half-open band
    `[low, high)` if a score is available). **Default band**: `low=0.4, high=0.6` (only active when
    `enabled: true`). The rule is documented in the verification docs/spec note alongside the code.
  - `residual_unsupported_rate.threshold: null` (no guard) by default.
- **State changes**: none destructive; only additive fields in the run's `reviews/` artifact.
- **Storage implications**: no migrations, no new tables — file-backed YAML, consistent with RF's
  Markdown/YAML-first model.

**DECISION — where the residual-unsupported-rate lives**: it is written to **both** the verification
result (`reviews/verification.yaml`, the authoritative per-run ledger-adjacent artifact) **and** emitted
as a **CCDash event metric** via the existing `src/research_foundry/validators/emit_ccdash_event.py`
path, so dashboards can trend it. The verification YAML is source of truth; the CCDash event is a
best-effort, non-blocking emission (failure to emit never fails the verify).

---

## 7. API / Integration Requirements

**New or modified entry points:**
- `verify_report(...)` in `services/verification.py` — gains optional knobs sourced from config
  (no required-arg signature break). Existing callers continue to work unchanged.
- `rf verify` CLI — additive flags (`--check-urls`, and either reuse config for gating or add
  `--url-gate`); flags default to the offline-safe behavior. Follow the existing flag patterns in
  `src/research_foundry/cli_commands.py`.

**External service calls** (only when opted in):
- HTTP HEAD/GET to source `locator` URLs. Bounded timeout; per-probe try/except; **degrade gracefully**
  on any network error. Never invoked in the deterministic test suite (mocked/stubbed in fixtures).

**Internal service dependencies:**
- `_load_policy()` / config loader in `verification.py` for the new config block (extend defaults in the
  built-in `_DEFAULT_*` style already present ≈line 35).
- `validators/emit_ccdash_event.py` for the residual-rate metric emission (best-effort).

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `src/research_foundry/services/verification.py` — the `add(check_id, status, detail, locations)`
  check-recording pattern, `_load_policy()` defaults, and the `CheckResult`/`VerificationResult`
  shapes. New checks must register through `add(...)` so severity/precedence flows through the existing
  machinery.
- `src/research_foundry/validators/emit_ccdash_event.py` — for metric emission.
- `src/research_foundry/cli_commands.py` — for CLI flag conventions.

**Must not change** (protected areas):
- The existing checks' semantics and IDs.
- The exit-code precedence **SCHEMA → GOVERNANCE → UNSUPPORTED → OK**. New checks slot into this
  precedence: URL gating (when on) and residual-rate threshold (when on) map to existing severities;
  they must **not** introduce a new exit class. Abstain must **not** push a claim into UNSUPPORTED.
- The six claim statuses and the `[claim:clm_NNN]` tracing format.
- Default offline behavior and deterministic-test guarantees.

**New dependencies:**
- Allowed? **Prefer No.** Use the standard library / any HTTP client already vendored in RF
  (`httpx` is already a declared dependency — see `[dev]`/runtime extras). Do **not** add a new HTTP
  library. If `httpx` is not available at runtime in the default install, gate the probe behind an
  import guard that degrades to `skipped` (offline-safe), and note it in the Completion Report.

---

## 9. Acceptance Criteria

- [ ] URL-existence check runs **only when opted in**, probes unique source `locator` URLs, and records
      a per-source reachability result in `reviews/verification.yaml`.
- [ ] URL check **degrades offline without failing** — network/DNS/timeout errors yield
      `skipped`/`error`, never an exception, and never change the exit code unless `url_check.gate` is
      explicitly enabled.
- [ ] Abstain band marks borderline material claims into an `abstain` outcome per the documented default
      rule (§6), withholding them from the unsupported set rather than forcing a binary verdict.
- [ ] Residual-unsupported-rate is computed (`unsupported_material ÷ material_total`) and surfaced in
      both the verification result and a CCDash event; emission failure does not fail the verify.
- [ ] With all new checks disabled (the default), existing verifier behavior — checks, output artifact,
      and exit-code precedence SCHEMA→GOVERNANCE→UNSUPPORTED→OK — is **unchanged** (regression-locked by
      test).
- [ ] Optional residual-rate threshold guard and URL gating, when enabled, slot into existing
      severities without introducing a new exit class.
- [ ] Unit tests cover each sub-feature with **offline fixtures** (URL probing mocked/stubbed); the
      deterministic suite makes no live network calls.
- [ ] CHANGELOG updated (changelog_required: true).

---

## 10. Validation Requirements

- [ ] **Typecheck**: `mypy src/research_foundry/services/verification.py --ignore-missing-imports` clean
      for changed scope.
- [ ] **Lint**: `flake8 src/research_foundry --select=E9,F63,F7,F82` clean.
- [ ] **Tests added/updated** for URL check (reachable/unreachable/offline-degrade), abstain band
      (in-band / out-of-band / disabled), and residual-rate (computation + threshold on/off).
- [ ] **Relevant tests pass**: run under the venv — `./.venv/bin/python -m pytest` (per memory:
      `pytest must run under venv`; in a worktree use
      `PYTHONPATH=<wt>/src <main>/.venv/bin/python -m pytest` per `RF test-suite gotchas`).
- [ ] **Regression**: an existing/representative verify test confirms byte-stable output and identical
      exit codes with the new checks disabled.
- [ ] **No live network** in the deterministic suite (probing mocked).
- [ ] **Docs updated**: verification spec/doc note describing the abstain rule, URL-check opt-in, and
      residual-rate field; CHANGELOG entry.
- [ ] **No unrelated changes** introduced.

---

## 11. Risk Areas

- **Determinism regression**: easiest way to break RF is to make `verify` non-deterministic or
  network-dependent by default. Mitigation: new checks dormant unless opted in; sorted/unique probe
  order; live network excluded from fixtures; explicit regression test.
- **Exit-code precedence leakage**: a new check accidentally changing the exit class would silently
  alter publish gating. Mitigation: route all new checks through `add(...)` with existing severities;
  no new `ExitCode` value; assert precedence unchanged.
- **Abstain over-suppression**: the research explicitly flags over-suppression as a documented failure
  mode — abstain must not become a loophole that hides genuinely unsupported claims. Mitigation:
  band off by default, narrow default bounds, claims still reported and counted; abstain excluded from
  "supported" too.
- **URL-check flakiness / rate limits**: probing many URLs could be slow or trigger remote rate limits.
  Mitigation: bounded timeout, HEAD-first, dedup locators, opt-in only, non-blocking.
- **Residual-rate denominator ambiguity**: defining "material claim total" inconsistently with the
  existing `material_claim_types` policy would make the metric misleading. Mitigation: reuse
  `_load_policy()` material types as the single source of truth for the denominator.

**Candidate carve-outs** (note, do not pre-split): if the abstain-band *scoring* model proves to need a
real support score that the ledger does not yet carry (today's statuses are categorical), implement the
conservative status-based default (`mixed` ⇒ abstain when enabled) and flag the score-based band as a
follow-up. If URL gating needs caching/retry policy beyond a single bounded probe, defer that to a
follow-up. All three sub-features otherwise stay in-scope Tier 1 with offline-safe defaults.

---

## 12. Implementation Notes

**Suggested approach** (agent may improve):
- Step 1 — Config & defaults: extend the `_DEFAULT_*` block (~line 35) and `_load_policy()` (~line 275)
  with the `url_check`, `abstain_band`, and `residual_unsupported_rate` config, all defaulting to the
  offline-safe / disabled values in §6.
- Step 2 — Residual-rate (cheapest, no network): compute from the material-claim set already gathered by
  the gate; add the field to `VerificationResult`; emit via `emit_ccdash_event.py` best-effort.
- Step 3 — Abstain band: between the supported/unsupported classification, apply the documented rule to
  move borderline material claims into an `abstain` list; ensure they are excluded from the unsupported
  set and from triggering UNSUPPORTED.
- Step 4 — URL check: behind the opt-in flag, dedup+sort URL locators, probe with bounded timeout via
  `httpx` (import-guarded), record per-source results; only contribute an error check when
  `url_check.gate` is on.
- Step 5 — Tests: offline fixtures for all three; regression test asserting unchanged default behavior +
  exit-code precedence.

**Similar existing code**:
- Reference: `src/research_foundry/services/verification.py` (the `add(...)` check pattern, `_load_policy`,
  `_DEFAULT_VERIFIER_CHECKS`, exit-code precedence ≈lines 35–55, 275–280, 335–715).
- Reference: `src/research_foundry/validators/emit_ccdash_event.py` for metric emission.
- Reason: stay inside the established check/severity/precedence machinery so the gate's guarantees hold.

**Known gotchas**:
- `pytest` must run under the venv interpreter (memory: `pytest must run under venv`); in a worktree set
  `PYTHONPATH=<wt>/src` against the **main** `.venv` (memory: `RF test-suite gotchas`).
- The full suite pollutes a few tracked real-run files via a non-isolated test — revert any such drift
  before committing (memory: `RF test-suite gotchas`).
- `locator` is the source URL/path field (`cli_commands.py`, `ids.py::source_card_id`); only probe
  locators that are actually URLs (skip local file paths → `skipped`).
- ARC/IntentTree/NotebookLM emission paths may be untested live — keep CCDash emission best-effort and
  non-fatal.

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: all modified/new files with brief reason.
- **Tests run**: tests added/updated and results (offline fixtures; venv interpreter).
- **Validation results**: table of mypy / flake8 / pytest / regression / docs with pass-fail.
- **Deviations from contract**: any material changes (e.g. status-based vs score-based abstain) and why.
- **Risks / Limitations**: residual risks (e.g. live URL probing unvalidated against real remotes;
  CCDash emission untested live).
- **Follow-up recommendations**: score-based abstain band, URL reachability caching/retry, runs-viewer
  rendering of the residual-rate metric, and the deferred RIB-002 pre-hoc grounded-generation half.

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion Report
template.

---

## Metadata & References

**Tier**: 1 (3–8 points) · **Estimated**: 6 points

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion, no phase
orchestration.

**Reviewer**: `task-completion-validator` (mandatory).

**Related Documents**:
- `docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md` (RIB-002 harvest —
  the source recommendation; row 002 + sequencing notes).
- `backlog/research_idea_backlog.yaml` (RIB-002 entry; IntentTree node
  `node_01KVQYKB4SQ1AHK52X6J61G3XQ`).
- `src/research_foundry/services/verification.py` (the existing gate this contract hardens, spec §12.3).

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass validation.
The single hardest invariant: **default `rf verify` must stay offline, deterministic, and
behaviorally identical to today** — every new capability is opt-in. If you find scope ambiguity, make a
conservative assumption (favor the offline-safe / disabled default) and note it in the Completion
Report. Stay within scope; do not touch the existing checks' semantics or the exit-code precedence.
