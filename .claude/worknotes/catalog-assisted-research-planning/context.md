---
type: context
schema_version: 2
doc_type: context
prd: "catalog-assisted-research-planning"
feature_slug: "catalog-assisted-research-planning"
title: "C3 Catalog-Assisted Research Planning — Execution Handoff (P1–P2 done, P3–P6 remaining)"
status: "complete"
created: 2026-07-23
updated: 2026-07-23
prd_ref: "docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md"
plan_ref: "docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md"
freeze_doc_ref: "docs/dev/architecture/carp-contract-freeze.md"
itt_node: "node_01KY5SHD2K1G9KT40E26XMVR43"
commit_refs: []
pr_refs: []
phase_status:
  - phase: P1
    status: complete
    gate: "CARP-1.G — validator APPROVE + karen APPROVE"
  - phase: P2
    status: complete
    gate: "CARP-2.G — validator APPROVE + karen APPROVE (two governance re-gates)"
  - phase: P3
    status: complete
    gate: "CARP-3.G — validator APPROVE + karen APPROVE (commit d9d67b0)"
  - phase: P4
    status: complete
    gate: "CARP-4.G — validator APPROVE + karen APPROVE after one fix-cycle (e8f5688 -> 4f94d1f)"
  - phase: P5
    status: complete
    gate: "CARP-5.G — validator APPROVE (c002412, 1f82ef6, 064f7ae, dcd4adb, 65284e8)"
  - phase: P6
    status: complete
    gate: "CARP-6.G — validator APPROVE + karen APPROVE after two fix-cycles (e9a06df, 4edd287, e4c8b71)"
---

# C3 Catalog-Assisted Research Planning — Execution Handoff

**Epic:** research-interchange-provenance-access (C3 of 5 children). **Tier 3, 28 pts, 6 serial phases.**
This worknote hands off a partially-executed plan so a fresh session can resume at **Phase P3**.

## Where things stand

- **P1 (Contract & Policy Freeze, 4 pts) — DONE, gated.** Commits `2d82d2d` → `9cf0c15` →
  `c223660` → `9dbcf73`. Gate CARP-1.G: `task-completion-validator` APPROVE **and** `karen` APPROVE
  on the exact tree. Three reject-fix cycles, each a real defect.
- **P2 (Governed Catalog Adapter, 5 pts) — DONE, gated.** Commits `74487f9` → `744a75e` →
  `3b0df83`. Gate CARP-2.G: validator + karen APPROVE after two governance re-gates — both were
  fail-open findings on the sensitivity axis. Worth internalizing (see Process rule §).
- **P3–P6 — NOT STARTED.** Their full briefs are embedded verbatim in `RESUME-PROMPT.md` in this
  directory (the job-scratch copies at `/Users/miethe/.claude/jobs/.../tmp/` will NOT survive).
- At pause, work through P2 was **squash-merged to `main`** (SHA in commit_refs once merged); the
  worktree branch `worktree-carp-c3-catalog-planning` was retained for P3+.

## The single most important thing to carry forward: the RPC deferral

C3's plan P1 formally depends on **RPC-1.G**, the contract-freeze gate of sibling child **C1
Research Provenance Continuity**. **C1 has NOT been executed** — no RPC schemas exist on disk.
Rather than block all 28 pts, C3 was executed under a stated assumption:

> CARP defines its **own** additive selection-provenance carrier (`selected_assertion_ref` +
> `retrieval_receipt`) inside CARP-owned schemas, authors **no** RPC-owned schema files, and the
> freeze doc §4.2 "RPC rebase contract" names every field that migrates into C1's envelope later.

The freeze doc §4 states normatively: *until C1 lands, every plan reference to "the RPC context" is
satisfied by the CARP-owned carrier; CARP-6.6's RPC leg is deferred to the rebase.* **P4/P5/P6 must
honor this** — do NOT author or fabricate an RPC surface when an AC says "RPC context". The P4/P6
briefs already carry this instruction.

## Frozen decisions (do NOT re-litigate — they passed a Tier-3 gate)

All in `docs/dev/architecture/carp-contract-freeze.md`. Resolutions of the plan's open questions:

- **CARP-OQ-2 (opt-in):** `retrieval_policy` ∈ {`disabled`, `catalog_only`, `catalog_then_discovery`};
  **default `disabled`**; absent policy is byte-identical to legacy. No implicit network fallback.
- **CARP-OQ-1 (coverage rule):** exactly one terminal state per question, `covered` | `residual`.
  `covered` requires ALL SIX: (1) conservative case-folded lexical match on required terms — **no
  semantic/vector/model matching**; (2) `lifecycle_state == eligible` re-read at selection;
  (3) `evaluate_reuse` = **allow** (refresh AND deny are residual); (4) all required source-types +
  qualifiers satisfied (missing data ⇒ residual); (5) no contradicting authorized candidate;
  (6) exact `assertion_version` pin. 14 closed `residual_reason` codes.
- **CARP-OQ-3 (no anonymous refresh state):** refresh-required visible only to an authorized
  identity in the owning workspace; denied callers get the existing `denied_payload` shape with all
  candidate-derived counters zeroed.

Schema-enforced (not just prose) after the P1 gate rounds: the six-condition covered/residual
partition; denial ⇒ zero candidate-derived counters keyed on `catalog_receipt.record_count == 0`
(covers BOTH denied and catalog-empty); `reuse_decision` action↔reason_code pairing; brief
covered/residual partition; `catalog_only` ⇒ empty `residual_question_ids`. Every `if`-on-optional
field carries `required: [<field>]` inside the `if` to defeat JSON-Schema vacuous truth.

## P2 outputs P3/P4 build on

- `src/research_foundry/services/catalog_retrieval.py` — the governed adapter. P3 consumes its DTOs
  (`RetrievalQuestion`, `RetrievalConstraints`, `RetrievalLimits`, `EvaluatedCandidate`,
  `RetrievalResult`, `RetrievalReceipt`) **only**. P3 must NOT import `assertion_catalog`/
  `assertion_reuse` or touch the ledger.
- **Seam 1 — `catalog_generation_id`** is a **sha256 content digest** over canonicalized projection
  records (in `assertion_catalog.py::rebuild`), idempotent under no-op rebuild. NOT a counter/path/
  mtime (a counter increments on cold-start reads because `_records()` calls `rebuild()` implicitly).
  P3's byte-equivalent replay keys on this.
- **Seam 2 — lexical match evidence** is reachable via per-term `search(query=term)` calls
  intersected on `assertion_id`; the adapter never reads `search_text` (privacy). `max_pages_per_
  question` is a **per-question budget shared across all term sub-queries**, not per-term.
- **P2 governance fix (CARP-2.G) — the biggest P4 wiring risk:** `sensitivity_allowed` is derived
  from `source_edition.access_scope` ranked against a **caller-supplied, never-defaulted**
  `RetrievalConstraints.sensitivity_threshold` via the shared
  `research_foundry.services.sensitivity.SENSITIVITY_RANK`. Threshold resolves with **no
  fallthrough**: unknown/malformed/empty threshold ⇒ **deny** (not "highest ceiling"); unknown
  scope ⇒ most-sensitive ⇒ deny. `SENSITIVITY_RANK` covers both vocabularies: `access_scope` uses
  `private` (most sensitive), run-sensitivity uses `top_secret` — both mapped co-top (rank 4).
  **P4 MUST thread a real threshold from the run/launch sensitivity posture into the adapter** or
  the `allow` path stays unreachable end-to-end (every candidate fails closed).

## Known limitations recorded (freeze doc §8)

- `required_extraction_contract` matching is **advisory in v1**: `extraction_contract` is projected
  from `extraction_provenance.schema_version`, a near-global constant, so it barely discriminates.
- Sensitivity axis is now gated (§8.1), but the ledger still has no independent sensitivity field
  distinct from `access_scope` + `allowed_for_work_output`.

## P4 fix-cycle: `_lexical_terms` cap defect (both reviewers rejected CARP-4.G on this)

`_lexical_terms()` (duplicated in `planning.py` and `search_router/router.py`) derived
`required_terms` from free text by regex-scanning for ≥3-char tokens, casefolded, first-occurrence
order, **capped at `_MAX_LEXICAL_TERMS = MAX_PAGES_PER_QUESTION` (=5)**, with no stopword
filtering. Two fail-open consequences: (1) truncation could satisfy condition 1
(`matched_terms == frozenset(required_terms)`) against only the *first 5* of a question's real
terms, marking a candidate `covered` without ever confirming the rest of the question — a false
positive on the governed coverage gate; (2) with no stopword filtering, the module's own default
fallback question (`f"What does the evidence say about {objective}?"`) burned all 5 cap slots on
boilerplate (`what, does, the, evidence, say`) before ever reaching the objective's real words.

**Fix:** added a small, explicit, module-level English stopword set (articles, auxiliaries,
prepositions, pronouns, conjunctions, wh-words, plus `say`/`evidence` as this module's own
fixed-template scaffolding vocabulary) to both copies, and removed `_MAX_LEXICAL_TERMS` +
its truncation guard entirely — every stopword-filtered term now passes through uncapped.

**Documented residual limitation (do NOT re-litigate — same freeze-doc §3.6 Seam-2 tension P2
already flagged, resolved conservatively/fail-closed):** `catalog_retrieval._collect_candidates`
still spends `max_pages_per_question` (frozen ceiling: 5) as ONE budget shared across every
required-term sub-query for a question, never per term. **A question whose distinct content-term
count exceeds that shared budget will resolve `residual`/`pagination_limit` even when catalog
evidence may exist** — the adapter's own pre-existing fail-closed mechanism (empty hit set once
`pages_remaining <= 0`) now reliably fires instead of being masked by the old truncation. This is a
real v1 limitation, not an optimal outcome; scaling the budget by term count or reading
`search_text` directly were both explicitly ruled out of scope for this fix (the former contradicts
the frozen shared-budget ruling, the latter reopens P2's privacy decision). One existing test
(`test_plan_run_catalog_only_marks_each_question_terminal_with_exact_selected_refs`'s `covered_q`)
had 6 distinct terms and only passed because of the removed cap — shortened to 5 terms to keep it a
valid "covered" happy path post-fix, per the ruling to fix the test's own setup rather than restore
the cap.

## P3 counter-emission trap (from the P1 Karen gate — will bite every catalog-empty/denied run)

The schema constrains ALL SIX candidate-derived summary counters — **including
`questions_residual`** — to 0/absent whenever `record_count == 0`. A builder that computes
`questions_residual = len([q for q in questions if residual])` emits an **invalid plan on every
catalog-empty and every denied run**. **Gate all six counters on `record_count > 0`, omit
otherwise.** `questions_total` (from the request) stays free. This is already in the P3 brief.

## Process rule learned (propagated to P3–P6 briefs)

A strict fail-closed / no-synthesis rule meeting a partially-wired data model creates pressure to
synthesize a value. That pattern produced BOTH P2 governance defects: first aliasing rights onto
the sensitivity axis (reported as "Deviations: None"), then — after the fix — an unknown threshold
string silently granting the highest ceiling (fail-open). **Rule:** if fail-closed makes the
feature dead, that is an ESCALATION to report as a blocker, not a licence to invent/alias/default.
Note the asymmetry that bit us twice: unknown *governance input* must deny, never default to the
permissive extreme. Verify "no such field exists" before claiming it. Report deviations as
deviations.

## Execution mechanics (how this was run — reuse it)

- **Orchestration:** Opus in-session drives the wave sequence directly. The `execute-plan`
  workflow shell can't reach ICA — its offload wiring only knows codex/bob executors, no
  `ica-executor` in RF's roster. Each phase = one ICA leaf + gate(s), gated serially P3→P4→P5→P6.
- **Leaves → ICA** (per `/delegation-router`: implementation/docs → `ica`/`ica-executor`,
  model `claude-sonnet-5[1m]`). Invoke:
  `ICA_KEY=CC1 ~/ica-claude.sh -p "<brief>" --model 'claude-sonnet-5[1m]' --dangerously-skip-permissions
  --max-turns N --allowedTools "Read Write Edit Bash Grep Glob" --add-dir <worktree> < /dev/null`
- **ICA budget is per-team (per key block), $2000/$4000 cap.** CC4/CC2/CC3 exhausted;
  **use `ICA_KEY=CC1` (fallback CC5)** — prefix the command. Haiku is free (unlimited) regardless.
- **Reviewer gates stay on `claude`** — `verdict` (task-completion-validator, sonnet) and
  `council-review` (karen, opus) are MUST-stay-primary; the router will not route them to ICA.
  Per the plan: P3/P4 and final also require karen; P5 is validator-only. Karen returns only on
  live children — silence is not a pass; resume by agentId via SendMessage.
- **Never trust a leaf's self-report.** Re-run authoritative `pytest`/schema-validation yourself;
  diff the full-suite failure set against the 16-failure baseline (list below). Both P2 fixes were
  found by reviewers catching what the leaf's "all green" report did not surface.

## Baseline (pre-existing, do NOT chase)

16 failing tests on the clean tree (missing pediatric fixtures from the data-plane split,
`test_serve_api` 404s = sensitivity-gate default, `test_assertion_rollout`, `test_report_anchors`,
`test_cli_rights`, `test_deployment_mode_cli_and_app`, `test_swarm_drive`); 215 ruff errors; 36
mypy errors (whole-package; **none in CARP files**). Bar every phase: **no NEW failures**.

## Resume prompt (paste into a fresh session)

See `RESUME-PROMPT.md` in this directory — it contains the exact prompt plus the full P3–P6 briefs.


---

# EXECUTION COMPLETE — P3–P6 landed and gated (2026-07-23)

All six phases of C3 are now complete. P3–P6 were executed in this worktree with every leaf on ICA
(`ICA_KEY=CC1`, `claude-sonnet-5[1m]`) and every reviewer gate on claude.

| Phase | Gate | Commits |
|---|---|---|
| P3 Evidence Planner | CARP-3.G — validator + karen APPROVE (first pass) | `d9d67b0` |
| P4 Retrieval-then-Discovery | CARP-4.G — validator + karen APPROVE after 1 fix-cycle | `e8f5688` → `4f94d1f` |
| P5 API/MCP/Export/Metrics | CARP-5.G — validator APPROVE | `c002412` `1f82ef6` `064f7ae` `dcd4adb` `65284e8` |
| P6 Hardening + Docs | CARP-6.G — validator + karen APPROVE after 2 fix-cycles | `b5023be` `1d41c1c` `9927a72` `d0f0569` `e41ae28` `f519463` `fc8010e` `e9a06df` `2d66a02` `504e3d4` `58e1c4b` `4edd287` `e4c8b71` |

Final validation at HEAD: full-suite failure set **identical to the 16-test pre-existing baseline**
(zero new failures); `validate_artifact.py --strict` exit 0; frontend `tsc -p tsconfig.app.json
--noEmit` clean; ruff clean on all touched files.

## Five fail-opens found and closed (the headline lesson)

This feature produced **five** fail-open defects of the SAME shape — a strict fail-closed rule
meeting a partially-wired data model creates pressure to synthesize or soften a value. **None was
caught by the implementing leaf's own "all green" report; every one was caught by a reviewer gate.**

1. **P2** — sensitivity axis aliased onto the rights boolean (fixed pre-handoff).
2. **P2 follow-up** — unknown/malformed threshold silently granted the highest ceiling.
3. **P4** — `_MAX_LEXICAL_TERMS` truncated `required_terms`, so `covered` was reachable on a strict
   subset; with no stopword filtering the default question derived `{what,does,the,evidence,say}`.
   Fixed by removing the cap + adding stopword filtering (`4f94d1f`).
4. **P6** — CARP's retrieval path never checked `AssertionLedgerCapabilities.automated_reuse_allowed`,
   bypassing a gate `run_launch.py:106-107` already enforced. Closed fail-closed (`e9a06df`).
5. **P6 fix-cycle** — stopword/short-token filtering could empty `required_terms`, making coverage
   condition 1 *vacuously true* for every candidate (an empty query returned an arbitrary assertion
   as `covered`). Closed at the plan-construction boundary (`4edd287`, `e4c8b71`).

**Rule reaffirmed:** if fail-closed makes a path dead, ESCALATE — never default/alias/synthesize.
Unknown governance input must DENY. A documented fail-**open** is not the same class of thing as a
documented fail-**closed** conservatism and must not ship as one.

## Maintainer watch items (from the final karen gate)

1. **`run_launch.py:105` fails open where CARP fails closed.** Its
   `capabilities is not None and not capabilities.automated_reuse_allowed` allows on `None`; CARP's
   `is not True` denies. Unreachable today (`:195` always passes a real object), but any new caller
   omitting the argument silently reopens the ledger-side gate. Consider aligning to `is not True`.
2. **Three duplicated helper pairs** now exist across `planning.py` and `search_router/router.py`:
   `_STOPWORDS`, `_lexical_terms`, `_evidence_plan_question`. Every fix must land twice. Three drift
   guards cover them — do not add a fourth pair without one.
3. **`covered` requires two default-off flags.** `ledger_write_enabled` and `automated_reuse_enabled`
   both default `False` (`config.py:110-111`). Any future test asserting `covered` must configure
   both, or it asserts against a world it did not build.
4. **Keep the `forced_residual_reason` escape hatch narrow.** It bypasses `retrieve()` entirely.
   Today only two call sites set it, only to `evaluation_error`, only on empty derived terms. Any
   widening deserves coverage-gate-level scrutiny — it is the one path producing a terminal question
   without consulting the catalog.

## Known limitations shipped (documented in the user guide)

Four fail-closed (cost recall, never over-cover): advisory `required_extraction_contract` matching;
no independent sensitivity field on the ledger; the shared per-question pagination-arithmetic limit
(>budget content terms ⇒ `residual`/`pagination_limit`); structurally-unsatisfiable
`required_source_types`. The fifth (blank query) is now closed outright.

## Execution mechanics worth reusing

- **The `execute-plan` workflow shell cannot reach ICA** — Opus drove the wave sequence directly.
- **Long ICA sessions are unstable on this gateway.** P5 died twice as one monolithic leaf; splitting
  it into four short sub-task leaves (5.1/5.2/5.3/5.4), each committing independently, worked.
- **Orphaned-leaf hazard (important):** a wrapper reporting "timed out"/exit 144 does NOT kill the
  underlying `claude` process. One orphan ran **37 minutes** unsupervised, committing to the branch
  (`1f82ef6`) and mid-writing files. Always `ps` for stragglers referencing the worktree, and wrap
  dispatches in `timeout -k` so leaves self-terminate instead of being orphaned.
