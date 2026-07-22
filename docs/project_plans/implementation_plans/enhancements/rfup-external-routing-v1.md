---
title: 'Implementation Plan: RFUP External-Routing Gap Closure'
schema_version: 2
doc_type: implementation_plan
it_schema: 1
status: completed
created: '2026-07-22'
updated: '2026-07-22'
feature_slug: rfup-external-routing
feature_version: v1
tier: 3
prd_ref: docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md
plan_ref: null
scope: "Delta plan closing 4 still-open RFUP items (pediatric evidence-card schema\
  \ hard-gate, exact-passage auto-strict eligibility, Path-B test hardening, native-adapter\
  \ eval) plus a new quote-fidelity check; evidence\u2192verified-claim seam only."
effort_estimate: ~24-27 pts across 6 phases + 1 seam task (bottom-up, Tier 3)
architecture_summary: "Extends rf's existing verify-time fail-closed gate idiom (resolve_exact_passage_mode\
  \ / exact_passage_present) with three new gates (schema completeness, eligibility-driven\
  \ strict mode, quote fidelity) on the same evidence pipeline stage sequence (ingest\u2192\
  extract\u2192claim-map\u2192verify\u2192council\u2192bundle); no new routers/repositories/DB\
  \ layers."
related_documents:
- docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md
- .claude/worknotes/rfup-external-routing/decisions-block.md
- .claude/worknotes/rfup-external-routing/scope-brief.md
- .claude/worknotes/rfup-external-routing/state-audit.md
- docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md
references:
  user_docs: []
  context: []
  specs:
  - .claude/skills/planning/references/ac-schema.md
  - .claude/specs/changelog-spec.md
  - .claude/skills/planning/references/deferred-items-and-findings.md
  - .claude/skills/planning/references/estimation-heuristics.md
  related_prds:
  - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
spike_ref: null
adr_refs:
- /Users/miethe/dev/homelab/development/pediatric-anemia-site/docs/adr/0008-pathb-hardening-vs-native-adapter.md
deferred_items_spec_refs:
- docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md
- docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md
findings_doc_ref: null
charter_ref: null
changelog_ref: CHANGELOG.md
test_plan_ref: null
plan_structure: independent
progress_init: auto
owner: null
contributors: []
priority: high
risk_level: medium
category: enhancements
tags:
- rfup
- evidence-foundry
- upstream
- delta
- verify
- quote-fidelity
- adapters
milestone: null
commit_refs:
- 51e3aae
- 925f42a
- 8a2a2eb
- 702ae95
- 987a37b
- c18cc18
- 97181d6
- 3045f47
- 9033718
- 8a0b014
- 8880a0b
- 2d2a3f1
- e86dc0c
- 5d8a37f
- 4cf320d
- 0a64478
- 7e1a4e9
- 7375d39
- 2137bd5
pr_refs: []
files_affected:
- src/research_foundry/services/verification.py
- src/research_foundry/schemas/pediatric_cds.schema.json
- src/research_foundry/services/quote_fidelity.py
- config/claim_policy.yaml
- .claude/workflows/__tests__/rf-run-execute.test.js
- .claude/workflows/__tests__/rf-pediatric-cds-run-execute.test.js
- tests/test_pediatric_cds_redteam_fixtures.py
- tests/test_quote_fidelity.py
- tests/test_verification_clinical_eligibility.py
- tests/test_verification_clinical_eligibility_regression.py
- tests/test_verification_pediatric_cds.py
- tests/test_verification_seam001_gate_composition.py
- tests/fixtures/pediatric_cds/red_team/01_missing_top_level_section.json
- tests/fixtures/pediatric_cds/red_team/02_wrong_type_required_field.json
- tests/fixtures/pediatric_cds/red_team/03_empty_required_object.json
- tests/fixtures/pediatric_cds/red_team/04_unexpected_additional_property.json
- tests/fixtures/pediatric_cds/red_team/05_nested_field_required_violation.json
- tests/fixtures/pediatric_cds/red_team/06_legacy_shape_missing_required_field.json
- docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md
- docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md
- CHANGELOG.md
- CLAUDE.md
planning_maturity: shipped
open_questions: []
decisions:
- decision: 'P1 JS test harness: use Node''s built-in node:test + `node --test` (no
    --experimental flag needed on Node 20).'
  rationale: 'No existing JS test harness in this repo (zero grep hits across *.test.js);
    node:test has been stable in Node core since 18 LTS and this environment runs
    Node 20.19.3. New files: .claude/workflows/__tests__/rf-run-execute.test.js and
    .claude/workflows/__tests__/rf-pediatric-cds-run-execute.test.js.'
  status: accepted
- decision: 'P2 hard-gate enforcement point: primarily verify-time (rf verify), consistent
    with the existing resolve_exact_passage_mode/exact_passage_present idiom (config-resolved
    + CLI override + fail-closed). An ingest-time cheap check is a Should, not a Must.'
  rationale: Reuses the established fail-closed pattern in verification.py rather
    than introducing a second enforcement idiom in source_cards.py; keeps the seam
    boundary narrow (rf validates structural completeness only).
  status: accepted
- decision: "P3 eligibility trigger: assertion_kind == threshold AND an explicit clinical-sensitivity\
    \ signal (a pediatric_cds block present on the cited card, or an existing sensitivity\
    \ tag) \u2014 NOT threshold alone."
  rationale: Resolves PRD OQ-1 / decisions-block OQ-4. Triggering on threshold alone
    risks silently hard-gating non-clinical research-only runs that never asked for
    strict mode (PRD Risks table, Risk 1, High/Medium).
  status: accepted
- decision: "P4 fidelity policy: two-stage \u2014 Stage 1 applies a normalization\
    \ allowlist (NFKC, whitespace collapsing, quote-mark style) before diffing; Stage\
    \ 2 treats any residual difference after allowlist normalization as material (flag/fail),\
    \ never silently auto-corrected."
  rationale: "Resolves PRD OQ-3 / decisions-block OQ-3. Auto-correcting material corruption\
    \ (e.g. superscript-digit stripping that changes \xD710\u2079/L \u2192 \xD710/L)\
    \ would hide the exact failure mode this phase exists to catch."
  status: accepted
- decision: 'P4 behavior for extraction_status: locator_only cards: warn (emit a distinguishable
    non-blocking finding), not skip and not fail.'
  rationale: Resolves PRD OQ-2. There is no stored full text to diff against for locator-only
    cards; failing would incorrectly hard-gate a retrieval-completeness gap the check
    wasn't designed to catch, while skipping silently would hide the coverage hole.
    Warn keeps it visible without blocking.
  status: accepted
- decision: "P5 evaluation method: static-only \u2014 PyPI/GitHub metadata review\
    \ (maintainer activity, release cadence, CVE history, dependency count) plus `pip\
    \ download --no-deps litellm` to inspect the wheel/sdist dependency tree and code\
    \ surface without installing or importing."
  rationale: Resolves PRD OQ-4 / decisions-block OQ-5. Satisfies the hard no-install/no-live-call/no-credentials
    constraint while still producing a citable, non-hand-wavy verdict that can survive
    a karen review.
  status: accepted
- decision: 'PRD OQ-5 (ADR-0008 status transition): this plan produces an rf-side
    verdict/install-plan artifact only, in this repo. The actual ADR-0008 status transition
    happens in pediatric-anemia-site and is explicitly out of scope here.'
  rationale: Seam boundary + cross-repo write restriction (this PRD's Hard Constraint
    1 and Out-of-Scope list both forbid editing pediatric-anemia-site). Tracked as
    a deferred item (category dependency-blocked) rather than a task in this plan.
  status: accepted
decision_gates: []
wave_plan:
  serialization_barriers: []
  phases:
  - id: P1
    depends_on: []
    isolation: shared
    parallelizable: true
    owner_skills: []
    files_affected:
    - .claude/workflows/__tests__/rf-run-execute.test.js
    - .claude/workflows/__tests__/rf-pediatric-cds-run-execute.test.js
  - id: P2
    depends_on: []
    isolation: shared
    parallelizable: false
    owner_skills: []
    files_affected:
    - src/research_foundry/schemas/pediatric_cds.schema.json
    - src/research_foundry/services/source_cards.py
    - src/research_foundry/services/verification.py
  - id: P3
    depends_on:
    - P2
    isolation: shared
    parallelizable: true
    owner_skills: []
    files_affected:
    - src/research_foundry/services/verification.py
    - config/claim_policy.yaml
  - id: P4
    depends_on:
    - P2
    isolation: shared
    parallelizable: true
    owner_skills: []
    files_affected:
    - src/research_foundry/services/verification.py
    - src/research_foundry/services/quote_fidelity.py
  - id: P5
    depends_on: []
    isolation: shared
    parallelizable: true
    owner_skills: []
    files_affected:
    - .claude/worknotes/rfup-external-routing/litellm-router-eval.md
  - id: P6
    depends_on:
    - P1
    - P3
    - P4
    - P5
    isolation: shared
    parallelizable: false
    owner_skills: []
    files_affected:
    - CHANGELOG.md
    - docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md
    - docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md
  waves:
  - - P1
    - P5
  - - P2
  - - P3
    - P4
  - - P6
success_metrics:
- 'P1: run-date + path-injection test suite passes for both workflow scripts; 0 regressions.'
- 'P2: schema hard-gates 100% of a >=5-case red-team malformed-block fixture set with
  0 false positives against the 7 existing verified pediatric-CDS bundles.'
- 'P3: threshold + clinical-eligible claims default to strict passage mode; 0 regressions
  in non-clinical warn-mode runs.'
- "P4: quote-fidelity check flags the PMC superscript-stripping fixture (\xD710\u2079\
  /L \u2192 \xD710/L) with 0 false positives against the 7 verified bundles."
- 'P5: ADR-0008 accept/reject verdict recorded with an install/wiring plan; 0 live
  external calls, 0 credentials used.'
- 'P6: CHANGELOG [Unreleased] entry lands; rfup-6 design-spec updated with the litellm_router
  verdict; ADR-0008 verdict design-spec authored.'
execution_mode: unassigned
agent_title: "RFUP external-routing gap closure \u2014 Tier 3 delta implementation\
  \ plan (6 phases + 1 seam task)"
agent_summary: Close 4 remaining upstream rf gaps for the Evidence Foundry seam (pediatric
  schema hard-gate, exact-passage auto-strict, Path-B tests, native-adapter eval)
  plus a new quote-fidelity phase; python-backend-engineer (sonnet) primary for P1-P4,
  spike-writer (opus) for P5, documentation-writer/changelog-generator (sonnet, haiku
  hard-errors in this env) for P6.
changelog_required: true
---

# Implementation Plan: RFUP External-Routing Gap Closure

**Plan ID**: `IMPL-2026-07-22-RFUP-EXTERNAL-ROUTING`
**Date**: 2026-07-22
**Author**: implementation-planner (Sonnet 5)
**Human Brief**: N/A — not yet created (decisions-block.md §8 recommends one given ≥8 pts + ≥2 phases; scaffolding is out of scope for this planning pass)
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md`
- **Decisions Block**: `.claude/worknotes/rfup-external-routing/decisions-block.md`
- **ADRs**: `/Users/miethe/dev/homelab/development/pediatric-anemia-site/docs/adr/0008-pathb-hardening-vs-native-adapter.md` (read-only reference, `proposed` — see Hard Constraints)

**Complexity**: Large (Tier 3)
**Total Estimated Effort**: ~24-27 pts (bottom-up; see Estimation Sanity Check)
**Target Timeline**: 4 waves, no fixed calendar target (this is an orchestrated delta, not a scheduled sprint)

## Origin Note

IntentTree source node `node_01KXRTYKKW9ECTF9MCBQ8JV1EB` is this work's origin node, but it lives in the pediatric program's tree, not `rf`'s — it is a reference pointer only, not a live binding for this plan's own IntentTree sync (this repo's `wave_plan` and frontmatter are the authoritative planning surface).

## Executive Summary

RFUP-1..5,7 landed on `main` at commit `001a834`. This is a **delta plan**, not a rebuild: it closes the four items the Evidence Foundry seam (pediatric-anemia-site's CDS pipeline) still needs — a formal JSON Schema hard-gate for the `pediatric_cds` evidence-card block (P2), an auto-strict exact-passage eligibility filter for threshold/clinical claims (P3), a regression-test suite for the already-parameterized Path-B workflow scripts (P1), and an eval-only native-adapter/ADR-0008 verdict (P5) — plus one newly-discovered gap with no scoped RFUP item: a character-level quote-content-fidelity check (P4). A final phase (P6) closes out documentation and deferred-item tracking. The plan runs in 4 waves: Wave 1 (P1 ∥ P5, independent), Wave 2 (P2, the schema-gate root), Wave 3 (P3 ∥ P4, both extending `verification.py`, gated by a shared seam-regression task), Wave 4 (P6, final docs).

## Invariants — Hard Constraints (verbatim, do not deviate)

1. **Seam boundary**: only evidence→verified-claim logic goes upstream into `rf`; CDS-specific FHIR/rule-DSL/signing logic never crosses into `rf`, in either direction.
2. **P5 is EVAL-ONLY**: no install, no live external calls, no credentials. The ADR-0008 accept/reject verdict is the sole deliverable. Any install is a separate future feature, gated on this verdict.
3. **This is a DELTA plan**: RFUP-1..5,7 already landed on `main` at commit `001a834`. Do not re-scope, re-litigate, or re-implement that work.

## Implementation Strategy

### Pipeline Sequence (not a routers→repositories→services stack)

Per the PRD's Architectural Context, this feature does not follow MP's routers→services→repositories→DB layering — there is no new DB schema and no new frontend surface. Instead it extends `rf`'s existing **evidence pipeline stage sequence** (ingest → extract → claim-map → verify → council → bundle), adding three new gates at the `verify` stage:

1. **P2 — schema completeness gate** (blocks structurally-incomplete `pediatric_cds` blocks)
2. **P3 — eligibility-driven strict passage gate** (blocks threshold/clinical claims lacking an exact passage)
3. **P4 — quote-fidelity gate** (blocks character-level source corruption)

P1 (tests) and P5 (eval) sit off this pipeline entirely — P1 tests the Path-B orchestration script, P5 is a documentation/eval artifact with zero code execution. P6 is docs-only.

### Parallel Work Opportunities

- **Wave 1**: P1 (Path-B test hardening) ∥ P5 (native-adapter SPIKE/eval) — fully independent domains, no shared files.
- **Wave 3**: P3 (eligibility gate) ∥ P4 (quote-fidelity gate) — both extend `verification.py` but touch disjoint functions; see `integration_owner` + `SEAM-001` below for how the overlap is managed without serializing the wave.

### Critical Path

**P2 → {P3, P4} → SEAM-001 → P6.** P1 and P5 are off the critical path but are still hard dependencies of P6 (Wave 4 `depends_on: [P1, P3, P4, P5]`) since P6 finalizes docs/deferrals for all five preceding phases.

```mermaid
graph LR
  P1[P1 Path-B tests] --> P6
  P5[P5 native-adapter SPIKE/ADR] --> P6
  P2[P2 pediatric schema gate] --> P3[P3 exact-passage eligibility]
  P2 --> P4[P4 quote-fidelity]
  P3 --> SEAM[SEAM-001 rf verify regression]
  P4 --> SEAM
  SEAM --> P6[P6 docs/deferrals]
```

### Phase Summary

| Phase | Title | Estimate | Target Subagent(s) | Model(s) | Notes |
|-------|-------|----------|--------------------|----------|-------|
| P1 | Path-B test hardening | 2 pts | python-backend-engineer | sonnet | Wave 1, ∥ P5. Tests only, no script logic change. |
| P2 | Pediatric evidence-card schema + hard-gate | 5 pts | python-backend-engineer, data-layer-expert | sonnet | Wave 2. Critical-path root. |
| P3 | Exact-passage eligibility + threshold hard-gate | 4 pts | python-backend-engineer | sonnet | Wave 3, ∥ P4. `integration_owner`. |
| P4 | Quote-fidelity check (new) | 5 pts | python-backend-engineer | sonnet | Wave 3, ∥ P3. `integration_owner`. |
| SEAM-001 | `rf verify` gate-composition regression | 1 pt (H6 bucket) | python-backend-engineer | sonnet | Wave 3, after P3+P4 land. R-P3 seam task. |
| P5 | Native-adapter SPIKE + ADR-0008 verdict (eval-only) | 5 pts | spike-writer | opus (+ search-specialist, sonnet, prior-art) | Wave 1, ∥ P1. Doubles as this plan's Tier-3 SPIKE. |
| P6 | Docs / deferrals finalization | 3 pts | documentation-writer, changelog-generator | sonnet (haiku hard-errors in this env — see below) | Wave 4, final. |
| **Total** | — | **~24-27 pts** | — | — | See Estimation Sanity Check |

**Haiku override (explicit)**: the decisions-block's default agent-routing table assumes `documentation-writer`/`changelog-generator` run on haiku (per this repo's standard doc-task convention). That default does not apply here: haiku-model default agents hard-error in this environment (see project memory `haiku-subagents-inaccessible`). **P6 routes both agents on sonnet.**

### Estimation Sanity Check

**Noun count (H1)**: 0 new CRUD-with-RBAC domain nouns — no new DB tables. `pediatric_cds` is a JSON-Schema-validated block on an existing evidence-card structure, not a new first-class entity with its own repository/router. H1 floor = 0 pts (does not apply).

**Dual-impl multiplier (H2)**: N/A — `rf` has no local/enterprise dual-implementation split; single Python service layer throughout.

**Algorithmic flag (H3)**: P4 (quote-fidelity diff/normalize/transform) trips the flag (`diff`, `transform` in its description). Budgeted at 5 pts (>3 pt floor) with the required ≥5 enumerable fixture scenarios:
1. Superscript-class corruption (PMC ×10⁹/L → ×10/L) — must be flagged.
2. NFKC-safe normalization (compatibility Unicode forms) — must NOT be flagged.
3. Curly-quote-safe normalization (curly ↔ straight quotes) — must NOT be flagged.
4. `extraction_status: locator_only` card (no source text to diff) — warn, not fail/skip.
5. Clean/no-corruption pass case (exact match after normalization) — must NOT be flagged.

**Bundle decomposition (H4)** — 6 capability areas (≥3 triggers the per-area floor):

| Capability Area | Independent Estimate | Notes |
|------------------|----------------------|-------|
| P1 — Path-B tests | 2 pts | Tests only, no new logic |
| P2 — pediatric schema gate | 5 pts | New schema + hard-gate wiring + fixtures |
| P3 — eligibility gate | 4 pts | Eligibility filter + default policy + regression |
| P4 — quote-fidelity gate | 5 pts | H3-flagged; ≥5 fixture scenarios |
| P5 — native-adapter eval | 5 pts | Research/eval effort, no install |
| P6 — docs/deferrals | 3 pts | CHANGELOG + 2 design-spec authoring tasks + context pointers |
| **Σ** | **24 pts** | Floor for plan total (excludes SEAM-001 + remaining H6) |

**Anchor (H5)**: commit `001a834` "RFUP-1..5,7" — same surface (`verification.py`, `source_cards.py`, `.claude/workflows/*.js`, `config/claim_policy.yaml`), ran as a 6-phase Tier-3 plan at ~29 pts actual. This delta plan's 24-27 pts is smaller (-7% to -17% vs. anchor), justified because 3 of 6 phases here (P1, P2, P3) extend already-designed/settled mechanisms (DF-E1-03, ADR-0008 recommendation, existing RFUP-1/3 code) rather than building net-new machine-contract plumbing from zero, as the anchor plan did. Within the ±30% band — no further justification required.

**Plumbing budget (H6)**: ~3 pts (~12.5% of the 24-pt subtotal) covering: schema DTO/version stamp consistent with RFUP-4's machine-contract (P2), CLI flag wiring for the eligibility default (P3), test fixtures across P2/P3/P4, the CHANGELOG entry (P6), and **SEAM-001** (1 of the 3 pts) — the cross-owner `rf verify` regression proving P2/P3/P4 compose without masking or double-counting.

**Huge-file touch (H7)**: `verification.py` is 1,398 lines (`wc -l`, verified at planning time) — under the 2K-line trigger. `source_cards.py` (451 lines), `rf-run-execute.js` (309 lines), `rf-pediatric-cds-run-execute.js` (388 lines), and `litellm_router.py` (151 lines) are all well under threshold. **H7 does not trigger** — no ≥2× multiplier applied to any task in this plan.

**Bottom-up total**: 24 (H4 Σ) + 3 (H6, includes SEAM-001) = **27 pts**
**Top-down intuition**: ~24-26 pts (decisions-block estimate)
**Locked estimate**: **~24-27 pts** (range retained rather than a single point — H6 plumbing is a budget, not yet task-decomposed to the 0.5-pt level; no compression below the H4 floor of 24).

### Generator Rule Compliance

- **R-P1** (no bare "across/everywhere/all X" without `target_surfaces:`): No AC in this plan uses "across", "everywhere", "throughout", "all X", or "visible" to describe scope. All ACs name concrete files/functions/fixtures directly. Compliant by construction — no expansion needed.
- **R-P2** (every new field gets an implicit "handles missing field" AC): Three new fields are introduced across this plan — the `pediatric_cds` schema's sub-fields (P2), the clinical-eligibility signal (P3), and the fidelity-check output/status field (P4). Each phase file below carries an explicit "handles missing/absent field" AC for its new field(s) (see Phase 2 AC-P2-4, Phase 3-4 file AC-P3-3, AC-P4-4).
- **R-P3** (≥2 owner specialties + `files_affected` intersection ≥1 → `integration_owner` + seam task): P2, P3, and P4 all touch `src/research_foundry/services/verification.py` (P2 also touches `source_cards.py`). `integration_owner: python-backend-engineer` is declared on the Wave-3 pair (P3+P4) — see the Phase 3-4 file frontmatter — and **SEAM-001** is the seam task: it runs the full `rf verify` regression after both P3 and P4 land, proving the three gates (P2 schema, P3 eligibility, P4 fidelity) compose without masking or double-counting each other. Compliant.
- **R-P4** (UI-touching phases → runtime-smoke task): **Does not trigger.** This plan has no UI files in scope — zero `*.tsx`/`*.ts` frontend files appear in any phase's `files_affected`. All work is backend Python (`.py`), one new JSON Schema, JS workflow tests (`.js`, orchestration scripts, not UI), and documentation. No runtime-smoke task is added, and this is stated explicitly per the rule's own instruction rather than silently omitted.

## Deferred Items & In-Flight Findings Policy

### Deferred Items Triage Table

| Item ID | Category | Reason Deferred | Trigger for Promotion | Target Spec Path |
|---------|----------|-----------------|------------------------|-------------------|
| DF-RFUP-EXT-01 | research-needed | The 5 native adapters NOT evaluated by P5 (`gpt_researcher`, `notebooklm`, `openai_agents`, `paperqa2`, `opencode`) remain scaffold-only per the RFUP-6 design-spec's existing defer-until gate. P5 evaluates only `litellm_router`. | The RFUP-6 design-spec's own existing defer-until trigger: a measured Path-B value gap (documented comparison run) OR a governance/DI-1-cleared requirement — per `docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md` §1. | docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md — **updated in place by P6/DOC-006a** (litellm_router row reflects the P5 conditional verdict; the other 5 remain `maturity: idea`, defer-until trigger reaffirmed unchanged). |
| DF-RFUP-EXT-02 | dependency-blocked | PRD OQ-5: ADR-0008 lives in `pediatric-anemia-site` and is `proposed`, not `accepted`. This plan's seam boundary forbids writing to that repo, so the actual ADR-0008 status transition cannot happen here. | The pediatric-anemia-site maintainer accepts/rejects ADR-0008 based on this plan's P5 verdict artifact. | docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md — **authored by P6/DOC-006b** (`maturity: shaping`; documents the `conditional` verdict + unexecuted install/wiring plan; the actual ADR-0008 status transition remains out of scope, tracked here). |

`litellm_router` itself is P5's own eval subject, not a deferred item — it is intentionally excluded from this table.

### In-Flight Findings

Not pre-created. `.claude/findings/rfup-external-routing-findings.md` will be created lazily on the first real finding during execution, per the lazy-creation rule. `findings_doc_ref: null` at plan authoring time.

### Quality Gate

P6 (final phase) cannot be sealed until:
- Both triage-table rows above have a populated `Target Spec Path` and the corresponding design-spec has been authored (see P6 phase file, DOC-006a/DOC-006b tasks) — `deferred_items_spec_refs` frontmatter updated accordingly.
- `findings_doc_ref` is either still `null` (no findings occurred) or, if populated, the findings doc is finalized to `status: accepted`.

## Reviewer Gates

- **`task-completion-validator`** at the end of every phase, P1 through P6 (mandatory Tier-3 gate per-phase).
- **ONE `karen` milestone after Wave 3 completes** (after P3 + P4 + SEAM-001) — **not** a separate `karen` pass at P2. This is a deliberate orchestrator decision consolidating the clinical-gate cluster's entire risk surface (P2 schema + P3 eligibility + P4 fidelity, per decisions-block Risk R1 — "false-pass admits corrupt/incomplete evidence into a pediatric CDS pipeline; false-block halts valid runs... this is *why* the feature is Tier 3 despite modest points") into a single review point after all three gates are provably composed by SEAM-001. This **overrides** the decisions-block's per-phase exit-gate column, which lists `karen` at P2 and again at P4 individually — do not add that separate P2 pass.
- **`karen` again at end of feature**, after P6.

## Phase Files

Detailed task breakdowns, structured ACs, and quality gates for each phase live in sibling files (this parent exceeds the 800-line budget when phase detail is inlined):

| Phase(s) | File | Wave |
|----------|------|------|
| P1 | [phase-1-pathb-tests.md](./rfup-external-routing-v1/phase-1-pathb-tests.md) | 1 |
| P2 | [phase-2-pediatric-schema-gate.md](./rfup-external-routing-v1/phase-2-pediatric-schema-gate.md) | 2 |
| P3, P4, SEAM-001 | [phase-3-4-clinical-gate-cluster.md](./rfup-external-routing-v1/phase-3-4-clinical-gate-cluster.md) | 3 |
| P5 | [phase-5-adapter-eval.md](./rfup-external-routing-v1/phase-5-adapter-eval.md) | 1 |
| P6 | [phase-6-docs-deferrals.md](./rfup-external-routing-v1/phase-6-docs-deferrals.md) | 4 |

## Risk Mitigation (Summary)

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-------------|
| R1 — Clinical-gate correctness (P2/P3/P4 false-pass or false-block) | High | Medium | Fail-closed defaults; paired valid+corrupt fixtures per gate; single consolidated `karen` milestone after Wave 3; SEAM-001 regression. |
| R2 — Shared `verification.py` churn across P2/P3/P4 | Medium | Medium | Sequence P2 before Wave 3; `integration_owner` declared; SEAM-001 seam task. |
| R3 — Item-4 scope creep into install / Mode-D | Medium | Low | Hard Constraint 2 (P5 eval-only, no egress/credentials); ADR verdict is the sole deliverable. |
| R4 — Quote-fidelity strategy ambiguity (normalize vs. reject; corruption classes) | Medium | Medium | Resolved via decisions list (two-stage allowlist policy); scoped to known superscript-class + extensible detector for v1. |
| R5 — JS test harness absence | Low | Low | Resolved via decisions list (`node:test`, confirmed available on Node 20.19.3 in this env). |
| R6 — Schema-version/machine-contract drift vs. RFUP-4 | Low | Low | Reuse existing schema-version stamping pattern from `001a834`; fail-closed on drift. |

Full risk detail (including per-phase mitigations tied to specific tasks) lives in each phase file's Risk Mitigation section.

## Success Metrics

See frontmatter `success_metrics` (mirrors the PRD's §4 Success Metrics table 1:1 — this plan does not restate them in prose to avoid drift between the two documents).

---

**Progress Tracking**: `.claude/progress/rfup-external-routing/all-phases-progress.md` (create via artifact-tracking skill when execution begins)

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-07-22
