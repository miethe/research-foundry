---
title: "Phase 3-4: Exact-Passage Eligibility + Quote-Fidelity Gate Cluster"
schema_version: 2
doc_type: phase_plan
status: draft
created: '2026-07-22'
updated: '2026-07-22'
feature_slug: rfup-external-routing
feature_version: v1
phase: "3-4"
phase_title: "Exact-passage eligibility (P3) + quote-fidelity check (P4) + seam regression (SEAM-001)"
prd_ref: docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
entry_criteria:
  - "Phase 2 (pediatric schema gate) complete — P3 and P4 both depend_on P2"
exit_criteria:
  - "P3: threshold+clinical-eligible claims default to strict passage mode; 0 regressions on non-clinical warn-mode runs"
  - "P4: PMC superscript fixture detected; 0 false positives against the 7 verified bundles"
  - "SEAM-001: full rf verify regression proves all 3 gates (P2/P3/P4) compose without masking or double-counting"
  - "task-completion-validator pass for P3, P4 individually, then karen milestone for the consolidated cluster"
related_documents:
  - docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
spike_ref: null
adr_refs: []
charter_ref: null
changelog_ref: null
test_plan_ref: null
integration_owner: python-backend-engineer
ui_touched: false
target_surfaces: []
seam_tasks: [SEAM-001]
owner: null
contributors: []
priority: high
risk_level: high
category: enhancements
tags: [phase-plan, verification, eligibility, quote-fidelity, seam-task]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/services/verification.py
  - config/claim_policy.yaml
  - src/research_foundry/services/quote_fidelity.py
---

# Phase 3-4: Exact-Passage Eligibility + Quote-Fidelity Gate Cluster (+ SEAM-001)

**Parent Plan**: [rfup-external-routing-v1.md](../rfup-external-routing-v1.md)
**Wave**: 3 (P3 ∥ P4, both `depends_on: [P2]`), then SEAM-001 after both land
**Effort**: P3 = 4 pts, P4 = 5 pts, SEAM-001 = 1 pt (H6 bucket) — 10 pts total
**Dependencies**: Phase 2 (pediatric schema gate) complete
**Agents**: python-backend-engineer (sonnet, extended) for both P3 and P4; same agent serves as `integration_owner` for SEAM-001

## Phase Overview

This file groups P3, P4, and the seam task **SEAM-001** because all three converge on the same file (`src/research_foundry/services/verification.py`) and the same risk class: PRD Risk R1 — "false-pass admits corrupt/incomplete evidence into a pediatric CDS pipeline; false-block halts valid runs... this is *why* the feature is Tier 3 despite modest points." Per **R-P3** (this repo's Plan Generator Rules), any phase with ≥2 owner specialties and `files_affected` intersection ≥1 must declare an `integration_owner` and at least one seam task — see frontmatter above (`integration_owner: python-backend-engineer`, `seam_tasks: [SEAM-001]`).

P3 and P4 touch **disjoint functions** within `verification.py` (P3 extends the existing `exact_passage_present` check at lines 712-753; P4 adds a wholly new check function) — this is why they run in the same wave rather than being serialized. SEAM-001 exists specifically to prove that disjointness holds at runtime, not just at code-review time.

### P3 Goals — Exact-Passage Eligibility

- Add an eligibility filter that auto-selects `exact_passage_mode: strict` for claims with `assertion_kind: threshold` **AND** an explicit clinical-sensitivity signal — resolved decision (parent plan frontmatter): a `pediatric_cds` block present on the cited card, OR an existing sensitivity tag. **Not** `threshold` alone.
- Set a documented default policy in `config/claim_policy.yaml` so pediatric/CDS runs get this behavior without extra flags.
- 0 regressions against existing non-clinical warn-mode runs.

### P4 Goals — Quote-Fidelity Check (new)

- Detect character-level source corruption between an extracted quote and its stored source-card full text (e.g. PMC stripping superscripts, `×10⁹/L` → `×10/L`).
- Apply the resolved two-stage policy (parent plan decisions list): Stage 1 normalization allowlist (NFKC, whitespace, quote-mark style) before diffing; Stage 2 any residual difference after allowlist normalization is flagged/failed, never silently auto-corrected.
- `extraction_status: locator_only` cards: warn (non-blocking distinguishable finding), not skip, not fail.

### SEAM-001 Goal — Gate Composition Regression

- After both P3 and P4 land, run the full `rf verify` regression proving the three gates (P2 schema, P3 eligibility, P4 fidelity) compose: no gate masks another's failure, no finding is double-counted across gates, and the 7 verified pediatric-CDS bundles still pass end-to-end through all three gates simultaneously (not just each gate in isolation, which P2-003/P3-003/P4-004 already cover individually).

## Task Breakdown

| Task ID | Task Name | Description | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|----------|-------------|-------|--------|--------------|
| P3-001 | Clinical-eligibility filter | Implement the eligibility check: `assertion_kind == "threshold"` AND (`pediatric_cds` block present on a cited card OR existing sensitivity tag) → force `exact_passage_mode: strict` for that claim regardless of the run's configured/CLI-level mode. | 2 pts | python-backend-engineer | sonnet | extended | P2 |
| P3-002 | Default policy wiring | Set the documented default in `config/claim_policy.yaml` (and/or CLI default) so pediatric/CDS runs get P3-001's behavior without an explicit `--exact-passage strict` flag. | 1 pt | python-backend-engineer | sonnet | adaptive | P3-001 |
| P3-003 | Eligibility regression tests | Regression-test against existing non-clinical warn-mode runs (0 false-positive hard-gates on non-eligible claims) plus positive cases (threshold+clinical-eligible claim lacking a locator fails closed). | 1 pt | python-backend-engineer | sonnet | adaptive | P3-002 |
| P4-001 | Quote-vs-source diff check | New check function comparing an extracted quote's characters against the stored full-text source rendering (where available); this is distinct from `check_anchor_hash_match` (line 1051-1099), which only detects post-hoc tampering of an already-stored quote, not extraction-time corruption. | 2 pts | python-backend-engineer | sonnet | extended | P2 |
| P4-002 | Two-stage normalization policy | Implement Stage 1 allowlist (NFKC normalization, whitespace collapsing, quote-mark style) applied before diffing; Stage 2 treats any residual difference as material (flag/fail) — never silently auto-corrects. | 1 pt | python-backend-engineer | sonnet | extended | P4-001 |
| P4-003 | `locator_only` card handling | Cards with `extraction_status: locator_only` (no full text to diff against) emit a warn-level, distinguishable, non-blocking finding — not skip (invisible), not fail (incorrectly hard-gates a retrieval gap this check wasn't designed to catch). | 1 pt | python-backend-engineer | sonnet | adaptive | P4-001 |
| P4-004 | Fidelity fixtures (H3 — 5 scenarios) | Author the 5 enumerated fixture scenarios from the parent plan's Estimation Sanity Check (superscript corruption / NFKC-safe / curly-quote-safe / locator-only-warn / clean-pass) and validate against the 7 verified bundles (0 false positives). | 1 pt | python-backend-engineer | sonnet | adaptive | P4-002, P4-003 |
| **SEAM-001** | `rf verify` gate-composition regression | Run the full `rf verify` regression suite (all 7 verified pediatric-CDS bundles + the red-team/corruption fixture sets from P2/P4) with P2+P3+P4 all active simultaneously. Assert: (a) no gate's failure reason masks another gate's independent failure on the same fixture; (b) no single finding is emitted/counted by more than one gate; (c) all 7 verified bundles still pass end-to-end. | 1 pt | python-backend-engineer | sonnet | extended | P3-003, P4-004 |

## Detailed Task Specifications

### Task P3-001: Clinical-eligibility filter

**Estimate**: 2 pts · **Dependencies**: P2

**Acceptance Criteria**:
- [x] AC-P3-1: Eligibility trigger is `assertion_kind == "threshold"` AND (a `pediatric_cds` block is present on ≥1 cited source card OR the claim/card carries an existing sensitivity tag) — resolved per parent plan decisions list, overriding a threshold-alone trigger.
- [x] AC-P3-2: When eligible, `exact_passage_mode` is forced to `strict` for that specific claim's `exact_passage_present` evaluation, independent of the run's configured/CLI `--exact-passage` value (i.e., this is a per-claim override, not a global mode flip).
- [x] AC-P3-3 (**R-P2 implicit AC** — new field: the clinical-eligibility signal): When the signal itself cannot be determined (e.g. the cited card has no `pediatric_cds` block AND no sensitivity-tag field present at all, vs. explicitly `false`/absent-but-checked), the claim defaults to **non-eligible** (fails safe toward the existing warn-only behavior, not toward strict) — this is the direction PRD Risk 1 requires (avoid over-broad hard-gating), not the fidelity-check direction (P4, which fails toward visibility). Document this asymmetry inline in the code comment.

**Files Involved**:
- `src/research_foundry/services/verification.py` — new eligibility-check function feeding into the existing `exact_passage_present` check (lines 712-753).

### Task P3-002: Default policy wiring

**Estimate**: 1 pt · **Dependencies**: P3-001

**Acceptance Criteria**:
- [x] AC-P3-4: `config/claim_policy.yaml` documents the default policy such that pediatric/CDS runs get P3-001's auto-strict behavior without requiring `--exact-passage strict` on every invocation.
- [x] AC-P3-5: Non-pediatric/non-clinical runs relying on default settings retain today's warn-only behavior (no global default flip to `strict`).

**Files Involved**:
- `config/claim_policy.yaml` — new default-policy entry.

### Task P3-003: Eligibility regression tests

**Estimate**: 1 pt · **Dependencies**: P3-002

**Acceptance Criteria**:
- [x] AC-P3-6: 0 false-positive hard-gates against existing non-clinical warn-mode regression runs.
- [x] AC-P3-7: A threshold+clinical-eligible claim lacking a locator fails closed (non-zero exit / `unsupported[]` append) as a positive-path assertion.

**Files Involved**:
- Test suite exercising `verification.py`'s eligibility path; `./.venv/bin/python -m pytest`.

### Task P4-001: Quote-vs-source diff check

**Estimate**: 2 pts · **Dependencies**: P2

**Acceptance Criteria**:
- [ ] AC-P4-1: New check compares an extracted quote's characters against the source card's stored full-text rendering, operating only on already-ingested/stored text (no new live fetch or re-crawl — per PRD assumption).
- [ ] AC-P4-2: Explicitly distinguished from `check_anchor_hash_match` (verification.py:1051-1099) in code comments — that check detects post-hoc tampering of an already-extracted quote; this check detects extraction-time corruption against the original source rendering.
- [ ] AC-P4-3: Diffing scope is capped to the source card's stored full text (no new I/O scaling worse than linear in source-text length, per PRD NFR).

**Files Involved**:
- `src/research_foundry/services/quote_fidelity.py` (new) — diff/detector logic, kept separate from `verification.py`'s existing monolith to bound the H3-flagged algorithmic surface.
- `src/research_foundry/services/verification.py` — wiring call-site only.

### Task P4-002: Two-stage normalization policy

**Estimate**: 1 pt · **Dependencies**: P4-001

**Acceptance Criteria**:
- [ ] AC-P4-4 (**R-P2 implicit AC** — new field: the fidelity-check output/status field): When the normalization/diff pipeline cannot determine a status for a given quote (e.g. an internal error during Stage 1 normalization, not a locator_only case — see P4-003 for that), the check defaults to a distinguishable **error/unknown** status, never silently reported as "pass." Missing this field elsewhere in the pipeline (e.g. a card processed before this check existed) must not be misread as "verified fidelity" — absence and "checked, passed" are distinct states.
- [ ] AC-P4-5: Stage 1 (safe transforms — NFKC normalization, whitespace collapsing, quote-mark style differences) never triggers a flag.
- [ ] AC-P4-6: Stage 2 (any residual difference after Stage 1 normalization) is always flagged/failed — the check never silently auto-corrects a material difference in place.

**Files Involved**:
- `src/research_foundry/services/quote_fidelity.py` — normalization allowlist + two-stage comparison logic.

### Task P4-003: `locator_only` card handling

**Estimate**: 1 pt · **Dependencies**: P4-001

**Acceptance Criteria**:
- [ ] AC-P4-7: Cards with `extraction_status: locator_only` produce a warn-level finding distinguishable from both a pass and a Stage-2 fail (e.g. a distinct reason code like `quote_fidelity_unverifiable_locator_only`).
- [ ] AC-P4-8: This warn does not append to `unsupported[]` (non-blocking, per resolved decision — warn, not fail).

**Files Involved**:
- `src/research_foundry/services/quote_fidelity.py`.

### Task P4-004: Fidelity fixtures (H3 — 5 scenarios)

**Estimate**: 1 pt · **Dependencies**: P4-002, P4-003

**Acceptance Criteria**:
- [ ] AC-P4-9: PMC superscript-stripping fixture (`×10⁹/L` → `×10/L`) is detected and flagged (Stage 2).
- [ ] AC-P4-10: NFKC-safe normalization fixture is NOT flagged (Stage 1).
- [ ] AC-P4-11: Curly-quote-safe normalization fixture is NOT flagged (Stage 1).
- [ ] AC-P4-12: `locator_only` fixture produces the warn finding from P4-003, not a fail.
- [ ] AC-P4-13: Clean/no-corruption fixture passes with no finding.
- [ ] AC-P4-14: 0 false positives against the 7 existing verified pediatric-CDS bundles when this check runs in isolation (SEAM-001 covers the composed case).

**Files Involved**:
- Test fixtures (e.g. `tests/fixtures/quote_fidelity/`); `./.venv/bin/python -m pytest`.

### Task SEAM-001: `rf verify` gate-composition regression

**Estimate**: 1 pt · **Dependencies**: P3-003, P4-004 · **Owner**: `integration_owner` (python-backend-engineer)

**Acceptance Criteria**:
- [ ] AC-SEAM-1: With P2 (schema), P3 (eligibility), and P4 (fidelity) all active simultaneously, all 7 existing verified pediatric-CDS bundles pass `rf verify` end-to-end (composed regression, distinct from each gate's individual 0-false-positive check).
- [ ] AC-SEAM-2: The red-team fixture set from P2-003 and the corruption fixture set from P4-004 each fail for their own expected reason code and no other gate's reason code appears alongside it on the same fixture (no masking).
- [ ] AC-SEAM-3: No single underlying data issue on a fixture is counted by more than one gate's `unsupported[]`/finding emission (no double-counting) — e.g. a fixture that is BOTH schema-incomplete AND quote-corrupted should surface both findings distinctly, not collapse into one or duplicate.
- [ ] AC-SEAM-4: Result of this task (pass/fail + evidence) is the explicit prerequisite the parent plan's `karen` milestone consumes — do not proceed to that review until SEAM-001 is green.

**Files Involved**:
- Composed regression test exercising `verification.py` with all three new checks active; `./.venv/bin/python -m pytest`.

## Quality Gates

This phase-pair is complete when:

- [ ] **Functional**: P3 and P4 each individually satisfy their own AC sets; SEAM-001 additionally passes.
- [ ] **Testing**: `./.venv/bin/python -m pytest` green for all P3/P4/SEAM-001 test files.
- [ ] **Seam verification** (R-P3): SEAM-001 is completed and its evidence is recorded before this cluster is considered closed — this is the mandatory seam-task gate for the declared `integration_owner`.
- [ ] **Reviewer gate**: `task-completion-validator` passes P3 and P4 individually; **one consolidated `karen` milestone** runs after SEAM-001 is green (per parent plan's explicit Reviewer Gates override — no separate `karen` pass at P2, and no separate `karen` pass mid-cluster).

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| P3's eligibility heuristic too broad, hard-gates non-clinical runs | High | AC-P3-1/AC-P3-3 narrow trigger + fail-safe-to-non-eligible default; AC-P3-6 regression. |
| P4 false positives on paraphrase/OCR noise/benign Unicode variation | Medium | Two-stage allowlist (AC-P4-5/AC-P4-6); pilot against 7 verified bundles (AC-P4-14) before hard-gating. |
| P4 has no source text for `locator_only` cards | Medium | AC-P4-7/AC-P4-8 — warn, not fail/skip. |
| Shared `verification.py` churn masks or double-counts findings across P2/P3/P4 | Medium | SEAM-001 (AC-SEAM-2/AC-SEAM-3) — this is the entire purpose of the seam task. |

## Findings Captured This Phase

- [ ] No new findings this phase (default)

---

**Phase Version**: 1.0 · **Last Updated**: 2026-07-22

[Return to Parent Plan](../rfup-external-routing-v1.md)
