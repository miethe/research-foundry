---
title: "Implementation Plan: Assertion-Ledger Population & Activation"
schema_version: 2
doc_type: implementation_plan
it_schema: 1
status: complete
created: 2026-07-15
updated: 2026-07-15
feature_slug: assertion-ledger-activation
feature_version: v1
tier: 3  # PROMOTED from decisions block's Tier 2 (SPIKE-waived). Both promotion triggers fired: (1)
         # bottom-up estimate 21 pts > ~18 pt anchor; (2) OQ-1 investigation confirms the historical
         # claim-ledger to source-assertion mapping is NOT 1:1. See "Tier 3 Promotion" callout below.
prd_ref: docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
plan_ref: null
scope: "Wire the already-built assertion-ledger write/reuse/merge-UI machinery (reusable-assertion-ledger-v1) to real, workspace-scoped entry points -- historical backfill, forward ingest, reuse fields, merge-UI build flag -- so the three enabled foundry.yaml flags produce observable ledger population instead of a silent no-op."
effort_estimate: "30 pts bottom-up (P1 3 / P1.5 3 / P2 13 / P3 3 / P4 3 / P5 2 / P6 3). Revised 2026-07-16 per the SPIKE's post-fix re-measurement (docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md, '## Post-fix re-measurement (2026-07-16)'): +4 pts for two new blocking Phase 2 prerequisite tasks (P2-01a: fix defect 1c claim-ledger bijection gate; P2-01b: skip-and-continue materialization mode), discovered when the landed P1.5 fix was re-measured against the real corpus. Prior revision (2026-07-15) added +3 pts for blocking Phase 1.5 and +2 pts for Phase 2's SPIKE-resolved backfill scope, over the pre-SPIKE 21-pt estimate (21 -> 26 -> 30). See Estimation Sanity Check (not yet re-run against this latest revision) and the SPIKE for full detail."
architecture_summary: "No new services or tables. New: a fix to the existing extraction/ingest contract that binds assertion_text to the source card's verbatim quote instead of the paraphrased claim text, plus passage segmentation on ingest (P1.5, blocking); a shared workspace-resolution/fail-closed helper (P1); a write-path counterpart to backfill_dry_run() sharing AssertionRegistry.ingest()/AssertionMaterializer.materialize_run() with the forward driver (P2/P3); reuse fields threaded from LaunchRunRequest into the existing assertion_reuse/assertion_impact services (P4); a frontend build-flag wired through deploy (P5)."
related_documents:
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/aars/2026-07-15-catalog-visibility-regressions.md
  - .claude/worknotes/assertion-ledger-activation/decisions-block.md
  - docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
  - docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
  - docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md
references:
  user_docs: []
  context: []
  specs:
    - .claude/specs/artifact-structures/human-brief-spec.md
  related_prds:
    - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
spike_ref: docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md   # P2-01 SPIKE delivered 2026-07-15.
                  # Verdict: fix-forward-extraction-contract (new blocking Phase 1.5) is the primary,
                  # mandatory track; Phase 2 backfill adopts accept-low-yield + a narrow fuzzy>=0.9
                  # quote-recovery add-on. See "P2-01 SPIKE Verdict" callout below.
adr_refs: []
deferred_items_spec_refs:
  - docs/project_plans/design-specs/assertion-ledger-backfill-mapping-strategy.md
findings_doc_ref: null
charter_ref: null
changelog_ref: CHANGELOG.md
test_plan_ref: null
plan_structure: unified
progress_init: auto
owner: nick
contributors: []
priority: high
risk_level: high
category: "product-planning"
tags: [implementation, planning, phases, tasks, assertion-ledger, wksp-304, security, backfill, spike-resolved, tier-3-promotion, extraction-contract-fix]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/services/extraction.py
  - src/research_foundry/services/assertion_rollout.py
  - src/research_foundry/services/assertion_registry.py
  - src/research_foundry/services/assertion_materialization.py
  - src/research_foundry/services/assertion_workspace.py
  - src/research_foundry/services/source_cards.py
  - src/research_foundry/services/run_launch.py
  - src/research_foundry/api/routers/runs.py
  - src/research_foundry/cli_commands.py
  - frontend/runs-viewer/src/lib/canonicalClaimsFlag.ts
  - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
  - foundry.yaml
  - CHANGELOG.md
  - docs/project_plans/design-specs/assertion-ledger-backfill-mapping-strategy.md
  - docs/project_plans/reports/audits/assertion-ledger-activation-di1-scoped-audit.md
planning_maturity: in_progress
open_questions:
  - q: "OQ-1: Is the historical claim-ledger to source-assertion mapping 1:1?"
    owner: implementation-planner
    status: resolved
  - q: "OQ-2: Which entry point wires the forward write driver (C1/P3)?"
    owner: implementation-planner
    status: resolved
  - q: "OQ-3: What assertion_registry_workspace_id does a single-operator run resolve to?"
    owner: python-backend-engineer
    status: open
  - q: "OQ-4: Does the merge UI (P5) require populated canonical claims, or can it be verified against a synthetic fixture?"
    owner: ui-engineer
    status: open
decisions:
  - decision: "OQ-1 resolved: the historical claim-ledger to source-assertion mapping is NOT 1:1 under assertion_materialization's fail-closed exact-quote-match contract."
    rationale: "Corpus-wide check across all 42 runs with claim_ledger.yaml (2,984 extraction facts): 2,779 facts (93.1%) have fact.text != the source card's evidence_point.quote, plus 115 facts (3.9%) with no matching quote/evidence point at all -- 97.0% combined abstain-eligible rate against assertion_materialization's fact_source_quote_mismatch / missing_exact_passage_quote gates. The extraction pipeline stores a paraphrased summary as extracted_facts[].text; the verbatim quote lives separately on the source card's extracted_points[].quote, and the materializer requires the two to be byte-identical by design (it 'neither segments passages nor attempts citation resolution')."
    status: accepted
  - decision: "Promote this plan from Tier 2 to Tier 3 per the decisions block's own conditional trigger."
    rationale: "Decisions block: 'if it finds the materialization mapping is not 1:1, promote to Tier 3 and author a targeted backfill-mapping SPIKE first.' Both trigger conditions fired: non-1:1 mapping confirmed (97.0% abstain-eligible), and the bottom-up estimate (21 pts) exceeds the ~18 pt anchor."
    status: accepted
  - decision: "OQ-2 resolved: the forward write driver (P3) wires the existing `rf ingest` CLI command."
    rationale: "src/research_foundry/cli_commands.py:316-337 is the only caller of source_cards.ingest_source() outside its own module. No discovery-swarm-specific ingest path or POST /api/runs ingest call exists; this is also the command the discovery swarm's carder agents invoke per the project's Path-B swarm execution pattern."
    status: accepted
  - decision: "The backfill mapping-strategy SPIKE (task P2-01) is authored inline in Phase 2, not deferred to the final documentation phase."
    rationale: "The standard deferred-items lifecycle assumes a design-spec can wait until the final phase; here the open design question is a hard prerequisite gating P2's own build tasks (P2-02 onward), so it is sequenced as P2's first task rather than deferred."
    status: accepted
  - decision: "P2-01 SPIKE delivered and resolved: adopt fix-forward-extraction-contract as a new, separate, blocking Phase 1.5; Phase 2 backfill adopts accept-low-yield + a narrow fuzzy>=0.9 quote-recovery add-on."
    rationale: "docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md (2026-07-15) found the historical paraphrase/quote mismatch (defect 1a) AND passage-segmentation gap (defect 1b, new finding) are systemic, not historical debris, and independently cap forward yield near 0% -- not the assumed ~3% floor -- without a contract fix. Primary/mandatory: fix-forward-extraction-contract, sequenced as a new blocking Phase 1.5 before the forward-driver phase (P3). Secondary (backfill only): accept-low-yield (option a) + scoped fuzzy>=0.9 quote-recovery (re-scoped option b, ~6.8% total yield, +1-2 pts) -- not the open-ended 'cached source text' re-derivation the original Phase 2 task text assumed, which the SPIKE confirmed does not exist for this corpus (no assertion_ledger/ directory has ever existed; ledger writes were only just enabled in commit ba9e551). Rejected: open-ended gate-relaxation (RQ3 -- no generic threshold is safe) and defer (RQ4 -- evidence is decisive now)."
    status: accepted
  - decision: "Post-fix re-measurement (2026-07-16): the P1.5 passage-binding fix (commit 6af82ce) is validated at 94.78% fact-level materialization yield (2,835/2,991 supported facts) across all 42 runs, an order-of-magnitude improvement over the pre-fix 3.0%/6.8% estimate used to scope Phase 2."
    rationale: "Re-measured against the real, unmodified AssertionMaterializer._prepare_one() and source_cards.ingest_source() registry-write logic, isolated under a throwaway /tmp registry (no writes to real run/state artifacts), across all 42 runs. See docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md -- '## Post-fix re-measurement (2026-07-16)' for full methodology and evidence. Confirms Phase 1.5's fix (P1.5-01/P1.5-02) is a decisive success at the fact level."
    status: accepted
  - decision: "A third, independent, pre-existing defect (1c) discovered by the same re-measurement: claim_mapping.py::validate_extraction_fact_claim_mappings() requires each run's persisted claim ledger to be byte-identical to a fresh re-scan of extraction cards and rejects any ledger with claims appended after the fact-derived prefix -- exactly what normal report synthesis does when it appends inference/speculation claims. 39/42 runs (92.9%) abort with non_bijective_fact_claim_mapping before any fact reaches the (now-fixed) passage-binding gate; real, unmodified materialize_run() yield across the whole corpus today is only 0.70% (21/2,991) -- worse than this plan's own pre-fix 3.0% floor."
    rationale: "Confirmed pre-existing and untouched by the P1.5 fix: claim_mapping.py was last modified in adeddcb, long before 6af82ce; git show 6af82ce touches only assertion_materialization.py and source_cards.py. Not a regression -- a previously-undiscovered blocker surfaced by this re-measurement. See the SPIKE's '## Post-fix re-measurement (2026-07-16)' section, 'RQ1-extended -- Defect 1c' subsection."
    status: accepted
  - decision: "Skip-and-continue materialization mode required: AssertionMaterializer._prepare()'s all-or-nothing-per-run design means even with defect 1c hypothetically fixed, only 8/42 runs (19%) would publish anything -- the other 34/42 (81%) have >=1 abstaining fact each and would still yield zero assertions for the entire run. Two new blocking prerequisite tasks are added to Phase 2 ahead of its existing build tasks: P2-01a (fix defect 1c, a careful integrity-gate analysis, not a blind relaxation) and P2-01b (skip-and-continue mode in materialize_run()). Phase 2 total revised 9 -> 13 pts (+4); plan total revised 26 -> 30 pts (+4)."
    rationale: "Per the SPIKE's verdict: '94.78% fact-level yield is achievable once 1c is fixed; run-level output additionally requires the all-or-nothing design to become skip-and-continue, or ~81% of runs will still publish nothing despite eligible facts.' Restates Phase 2's success criteria from the pre-re-measurement '~6.8% total yield' framing to the two-metric split: 94.78% fact-level yield achievable once 1c + skip-and-continue land; 0.70% end-to-end yield today."
    status: accepted
decision_gates:
  - gate: "OQ-3 confirmed against the WKSP-304 identity=None default-workspace resolution pattern"
    status: pending
  - gate: "OQ-4 resolved: real backfilled data vs. synthetic fixture required for AC-6 verification"
    status: pending
  - gate: "P2-01 SPIKE decision: RESOLVED per docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md (2026-07-15) -- primary: fix-forward-extraction-contract (new blocking Phase 1.5); backfill: accept-low-yield + narrow fuzzy>=0.9 quote-recovery add-on (~6.8% total yield, +1-2 pts); rejected: open-ended gate-relaxation, defer"
    status: resolved
  - gate: "Defect 1c integrity analysis (P2-01a): the relaxed claim-ledger bijection check must still catch real tampering (a fact-derived claim modified, reordered, or deleted within the fact-derived prefix) while tolerating only legitimately-typed trailing inference/speculation claims -- validated against an adversarial fixture, not a blind relaxation of the byte-identity check."
    status: pending
wave_plan:
  serialization_barriers:
    - src/research_foundry/cli_commands.py
    - CHANGELOG.md
  phases:
    - id: P1
      depends_on: []
      isolation: worktree
      parallelizable: true
      model: sonnet
      effort: extended
      owner_skills: []
      files_affected:
        - src/research_foundry/services/assertion_registry.py
        - src/research_foundry/services/assertion_materialization.py
        - src/research_foundry/services/assertion_workspace.py
        - tests/unit/test_assertion_workspace_isolation.py
      entry_criteria: ["PRD approved", "decisions block reviewed"]
      exit_criteria: ["isolation tests green", "senior-code-reviewer Mode E sign-off", "DI-1 scoping enumeration reviewed"]
    - id: P1.5
      depends_on: []
      isolation: worktree
      parallelizable: true
      model: sonnet
      effort: extended
      owner_skills: []
      files_affected:
        - src/research_foundry/services/extraction.py
        - src/research_foundry/services/assertion_materialization.py
        - src/research_foundry/services/source_cards.py
        - tests/unit/test_assertion_materialization.py
      entry_criteria: ["PRD approved", "P2-01 SPIKE verdict reviewed (docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md)"]
      exit_criteria: ["a verbatim quote materializes end-to-end (>=1 exact-passage match)", "no-workspace-id/flag-off path unchanged", "karen security sign-off"]
    - id: P2
      depends_on: [P1, P1.5]
      isolation: worktree
      parallelizable: true
      model: sonnet
      effort: extended
      owner_skills: []
      files_affected:
        - src/research_foundry/services/assertion_rollout.py
        - src/research_foundry/services/assertion_registry.py
        - src/research_foundry/services/assertion_materialization.py
        - src/research_foundry/cli_commands.py
        - tests/unit/test_assertion_backfill.py
      entry_criteria: ["P1 shared workspace-resolution helper merged", "P1.5 extraction/ingest contract fix merged"]
      exit_criteria: ["P2-01 SPIKE decision recorded", "backfill idempotency tests green", "karen security sign-off"]
    - id: P3
      depends_on: [P1, P1.5]
      isolation: worktree
      parallelizable: true
      model: sonnet
      effort: adaptive
      files_affected:
        - src/research_foundry/services/source_cards.py
        - src/research_foundry/cli_commands.py
        - tests/unit/test_source_cards_ingest.py
      entry_criteria: ["P1 shared workspace-resolution helper merged", "P1.5 extraction/ingest contract fix merged"]
      exit_criteria: ["forward-write integration test green", "flag-off regression test green", "karen security sign-off"]
    - id: P4
      depends_on: [P1]
      isolation: worktree
      parallelizable: true
      model: sonnet
      effort: adaptive
      files_affected:
        - src/research_foundry/api/routers/runs.py
        - src/research_foundry/services/run_launch.py
        - tests/integration/test_run_launch_reuse.py
      entry_criteria: ["P1 shared workspace-resolution helper merged"]
      exit_criteria: ["reuse decision invocable via CLI/HTTP", "governed-deny path tested"]
    - id: P5
      depends_on: []
      isolation: shared
      parallelizable: true
      model: sonnet
      effort: adaptive
      files_affected:
        - frontend/runs-viewer/src/lib/canonicalClaimsFlag.ts
        - frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx
      exit_criteria: ["merge UI renders against populated ledger on :3030", "tsc -p tsconfig.app.json --noEmit clean"]
    - id: P6
      depends_on: [P2, P3, P4, P5]
      isolation: shared
      parallelizable: false
      model: sonnet
      effort: adaptive
      files_affected:
        - CHANGELOG.md
        - docs/project_plans/reports/audits/assertion-ledger-activation-di1-scoped-audit.md
      exit_criteria: ["karen feature-end sign-off", "DI-1-scoped audit artifact accepted"]
  waves:
    - [P1, P1.5, P5]
    - [P2, P4]
    - [P3]
    - [P6]
success_metrics:
  - "A verbatim quote materializes end-to-end for at least one fact (>=1 exact-passage match), proving the P1.5 extraction/ingest contract fix closes the near-0% forward-yield gap the P2-01 SPIKE identified; the no-workspace-id/flag-off path remains byte-identical to today."
  - "Backfill materializes source-assertions for the exact-match-eligible subset (~3.0%) plus a narrow, spot-checked fuzzy>=0.9 quote-recovery add-on (~6.8% total yield per the P2-01 SPIKE, docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md); overall corpus coverage, including the abstention-code breakdown, is reported transparently in the backfill receipt -- not assumed at 100% or at any higher figure than the SPIKE's empirically-measured safe ceiling."
  - "A second run of the backfill command against the same corpus performs 0 new writes (idempotency)."
  - "A fresh run's ingest populates the ledger when ledger_write_enabled=true; run outcome and artifacts are byte-identical to today when the flag is false."
  - "A reuse decision (allow/deny/refresh) is invocable via CLI or HTTP for at least one governed reuse scenario, including the blocked/denied path."
  - "Canonical-merge review controls render on :3030 against populated ledger data when VITE_RF_CANONICAL_CLAIMS_ENABLED=true; tsc clean; absent when the flag is false."
  - "DI-1-scoped audit of the new write sites (assertion_materialization, extraction, assertion_rollout, source_cards, run_launch) records 0 unscoped write paths, reviewed by senior-code-reviewer/karen."
acceptance_criteria:
  - "AC-1: New writes are workspace-confined and fail closed without a workspace id"
  - "AC-2: The flag-off path is unchanged from today"
  - "AC-3: Backfill is idempotent -- re-run is a no-op"
  - "AC-4: A fresh run's ingest writes assertions when the flag is on"
  - "AC-5: Reuse decision is invocable and governed"
  - "AC-6: Canonical-merge UI activates against real data"
  - "AC-7: DI-1-scoped audit closes this feature's new-write-site delta"
  - "AC-8: A verbatim quote materializes end-to-end for at least one fact (>=1 exact-passage match), proving the extraction/ingest contract fix"
  - "AC-9: The no-workspace-id/flag-off path is unchanged by the contract fix"
execution_mode: agent
agent_title: "Fix the extraction/ingest contract and wire assertion-ledger write/reuse/merge-UI drivers behind workspace-scoped writes (Tier 3, SPIKE-resolved contract fix + backfill)"
agent_summary: "Fix the extraction/ingest contract that binds assertion_text to the source card's verbatim quote (new blocking Phase 1.5), then populate the empty assertion ledger via a gated, SPIKE-informed backfill and forward write driver, expose reuse fields, and activate the canonical-merge UI -- every write confined to assertion_registry_workspace_id, fail-closed when absent. The P2-01 SPIKE (docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md) found the historical paraphrase/quote mismatch is systemic, not historical debris, and -- independently -- that passage segmentation was never wired into the registry, capping forward yield near 0% without Phase 1.5's fix. Phase 2's backfill scope is accept-low-yield + a narrow fuzzy>=0.9 quote-recovery add-on (~6.8% total yield)."
agent_context: "Read the decisions block (.claude/worknotes/assertion-ledger-activation/decisions-block.md), the PRD (docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md), and the P2-01 SPIKE (docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md) before touching any file in this plan. This feature calls existing services from reusable-assertion-ledger-v1; Phase 1.5 is the one exception that changes existing service-internal behavior (assertion_materialization.py's exact-match gate), per the SPIKE's explicit finding that the gate's assumption (paraphrase byte-identical to quote) is unsatisfiable by design. P1, P1.5, P2, P3, and P4 are Mode-D (workspace-write / provenance-binding surface, no auto-merge, diffs reviewed before merge/deploy)."
changelog_required: true
---

# Implementation Plan: Assertion-Ledger Population & Activation

**Plan ID**: `IMPL-2026-07-15-ASSERTION-LEDGER-ACTIVATION`
**Date**: 2026-07-15
**Author**: Opus (decisions-block expansion, Mode B contract drafting)
**Human Brief**: N/A -- not yet created. Recommended on approval of the Tier 3 promotion below (feature crosses the ≥8 pt / ≥2-phase / non-trivial-anchor-delta heuristic in `.claude/specs/artifact-structures/human-brief-spec.md` §4).
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md`
- **Decisions block**: `.claude/worknotes/assertion-ledger-activation/decisions-block.md`
- **Driven system (v1)**: `docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md`
- **AAR**: `docs/project_plans/aars/2026-07-15-catalog-visibility-regressions.md`
- **WKSP-304 plan**: `docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md`
- **SPIKE (P2-01, delivered)**: `docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md`

**Complexity**: Large (promoted from Medium/Tier-2; reshaped 2026-07-15 by the P2-01 SPIKE)
**Total Estimated Effort**: 26 pts bottom-up (revised from 21 pts pre-SPIKE)
**Target Timeline**: ~3-4 weeks (Tier 3, phase-by-phase orchestration with mandatory karen milestones)

---

## IMPORTANT -- Tier 3 Promotion & Backfill-Mapping SPIKE Recommendation

**This plan is promoted from the decisions block's Tier 2 (SPIKE-waived) to Tier 3.** Both of the decisions block's own promotion triggers fired during expansion:

1. **Bottom-up estimate (21 pts) exceeds the ~18 pt anchor** by ~17% (see [Estimation Sanity Check](#estimation-sanity-check)).
2. **OQ-1 was investigated, not assumed, and the historical claim-ledger to source-assertion mapping is confirmed NOT 1:1.**

### What was investigated

The decisions block's SPIKE-waiver rationale rested on `assertion_materialization.materialize_run()` already implementing "the write path this feature calls" -- i.e., feasibility, not correctness, was the open question. To resolve OQ-1 before locking P2's task breakdown, a bounded, corpus-wide check was run (no SPIKE required to *discover* this -- it is a direct `grep`/`yaml`-diff of existing artifacts):

- `assertion_materialization.py`'s own module docstring states it "intentionally consumes only the existing deterministic 1:1 `extraction_card.extracted_facts` to run-local claim mapping. It neither segments passages nor attempts citation resolution... A candidate is materialized only when the extraction fact, claim locator, source-card evidence point, private registry edition, and exact passage all bind to one another." Concretely, `_prepare()` requires `quote == mapping.text` (`src/research_foundry/services/assertion_materialization.py:293-297`) or the candidate abstains with `fact_source_quote_mismatch`.
- A script diffed every `extractions/*.yaml` fact's `text` field against its source card's matching `extracted_points[].quote` field, across **all 42 runs with a `claims/claim_ledger.yaml`** (2,984 total extraction facts -- matches the PRD's "~3,000 historical claims across 41 runs" estimate):

  | Outcome | Count | % of corpus |
  |---|---:|---:|
  | `fact.text == source quote` (materializable) | 90 | 3.0% |
  | `fact.text != source quote` (`fact_source_quote_mismatch`) | 2,779 | 93.1% |
  | No matching quote/evidence point found (`missing_exact_passage_quote` or similar) | 115 | 3.9% |
  | **Combined abstain-eligible rate** | **2,894** | **97.0%** |

- **Root cause**: the extraction pipeline stores a *paraphrased summary* in `extracted_facts[].text` (what the claim ledger also carries as `claim.text`), while the *verbatim* quote lives separately on the source card at `extracted_points[].quote`. The materializer's exact-byte-match contract was designed for a world where these two are guaranteed identical; for the historical corpus, they routinely are not.

### What this means for the plan

- The PRD's success metric ("Backfill materializes source-assertions for every historical run with a `claims/claim_ledger.yaml`") is **not achievable as literally stated** without a design decision. This plan's frontmatter `success_metrics` has been revised to state the exact-match-eligible subset explicitly rather than silently assume 100% coverage (see also the WKSP-304 AAR's own lesson about false-completeness claims -- do not repeat it here).
- **Recommendation**: treat task **P2-01** (Phase 2, "Backfill mapping-strategy SPIKE & decision") as a hard, blocking prerequisite for the rest of Phase 2. It is scoped narrowly (targeted, not open-ended) and its three candidate resolutions are already enumerated in Phase 2's detail file. Per the decisions block's own instruction, if this decision surfaces meaningfully more work (e.g., a quote-recovery service), that is additional scope beyond this plan's 21-pt bottom-up and should be re-estimated before Phase 2's build tasks proceed.
- **Per the task's instruction not to override the decisions block's phase boundaries**, this plan does NOT insert a new phase for the SPIKE. It is sequenced as the first task inside Phase 2, since it gates Phase 2's own build tasks rather than being a deferrable nice-to-have.
- OQ-2 was also resolved during expansion (see Decisions, frontmatter): the forward write driver (Phase 3) wires the existing `rf ingest` CLI command (`src/research_foundry/cli_commands.py:316`).

### P2-01 SPIKE Verdict (delivered 2026-07-15) -- Reshapes This Plan

The P2-01 SPIKE (`docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md`) has since delivered its full investigation and a decisive verdict, going beyond the "is it 1:1?" question above to "why, and does the answer change what the forward driver (C1/P3) needs before it ships." **Headline finding: the 97.0% abstain rate is not historical debris -- it is a property of the current extraction/ingest pipeline that any forward run reproduces almost exactly, plus a second, independent, more severe defect (passage segmentation is never wired into the assertion registry) that caps forward yield even closer to 0% than the historical corpus's ~3% floor.**

**Two compounding defects, both proven by direct code inspection and a live experiment:**

1. **Defect 1a (paraphrase-vs-quote).** `extraction.py::_fact_from_point` copies the source card's paraphrased `summary` into `extracted_facts[].text`; the verbatim `quote` field is read only to set a boolean `quote_available` flag and is never persisted past the source card. The claim ledger's `text` field -- what the materializer must byte-match -- is therefore always the paraphrase, by construction, for every run.
2. **Defect 1b (no passage segmentation, new finding beyond OQ-1).** `source_cards.py::ingest_source()` calls `AssertionRegistry.ingest()` without a `passages=` argument, so the entire raw document becomes exactly one passage. A short verbatim quote can never bind via `find_exact_passages()` unless the quote is the entire document. Proven live: 0 matches before passing `passages=`, 1 match after.

**This plan is reshaped as follows (full detail in the Phase Summary table and each phase's detail file):**

- **New, blocking Phase 1.5 (`Forward extraction/ingest contract fix`)** is inserted before the forward-driver phase (P3) to fix both defects. This is the SPIKE's **primary recommendation** -- without it, P3 (which OQ-2 already resolved reuses `ingest_source()` verbatim) would materialize close to 0% of forward facts regardless of any other work in this plan.
- **Phase 2 (backfill) is re-scoped** from an open-ended re-derivation to **accept-low-yield (option a) + a narrow, spot-checked fuzzy>=0.9 quote-recovery add-on (re-scoped option b)** -- empirically measured at **~6.8% total materializable yield** (up from the 3.0% naive floor), at **+1-2 pts**, not the previously-flagged +3-5 pts. The SPIKE also corrects a factual assumption in Phase 2's original task text: no cached source text exists anywhere in this workspace (`assertion_ledger/` has never existed) -- the only verbatim substrate for recovery is the per-point `quote` already on each source card.
- **Phase 3 (forward driver) now hard-depends on Phase 1.5.** Once the contract is fixed, wiring `assertion_registry_workspace_id` into `rf ingest` remains the small, unchanged remaining step (matching the phase's original scope).
- **Rejected by the SPIKE:** open-ended gate-relaxation (RQ3 -- no generic similarity threshold preserves the fail-closed provenance guarantee) and deferring the decision (RQ4 -- the evidence is decisive now).

This raises the plan's bottom-up total from 21 pts to **26 pts** (P1.5: +3 pts; Phase 2 revision: +2 pts). See the revised Estimation Sanity Check below.

#### Update (2026-07-16): Post-Fix Re-Measurement Found a Third Defect

The SPIKE has since re-measured Phase 1.5's landed fix (commit `6af82ce`) against the real corpus -- see `docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md`, **"## Post-fix re-measurement (2026-07-16)"**, for the full methodology and evidence. Headline: the fix itself is validated as a decisive success -- **94.78% fact-level yield** (2,835/2,991), an order-of-magnitude improvement over the pre-fix 3.0%/6.8% estimate above -- but **real, unmodified `materialize_run()` yield across the whole corpus today is only 0.70% (21/2,991)**, because of a third, independent, pre-existing defect (1c: the claim-ledger bijection gate in `claim_mapping.py`, out of Phase 1.5's scope) that aborts 39/42 runs before any fact reaches the now-fixed passage-binding gate, compounded by `materialize_run()`'s all-or-nothing-per-run design. Phase 2 now carries two new, blocking prerequisite tasks (P2-01a, P2-01b; see `phase-2-backfill.md`) ahead of its existing build tasks, +4 pts (9 -> 13 pts; plan total 26 -> 30 pts). **Restated Phase 2 success criteria**: 94.78% fact-level yield is achievable once defect 1c and skip-and-continue materialization land; 0.70% end-to-end yield is what the corpus produces today, unmodified.

---

## Executive Summary

`reusable-assertion-ledger-v1` shipped the schemas, the read-only `/api/assertions/*` API, the runs-viewer "Source assertions" catalog tab (now default), and three enabled `foundry.yaml` flags -- but no shipped entry point exercises the write or reuse seams, so the ledger is empty. The P2-01 SPIKE (`docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md`) further found that the existing extraction/ingest contract itself is broken in two compounding ways that would cap any forward write at close to 0% yield. This plan now wires **seven** things to close both gaps: (P1) a shared workspace-scoped write contract with a fail-closed test harness; **(P1.5, new, blocking) a fix to the extraction/ingest contract** binding assertion_text to the source card's verbatim quote and wiring passage segmentation into the registry; (P2) a write-path counterpart to the existing dry-run backfill, re-scoped to accept-low-yield plus a narrow fuzzy-quote-recovery add-on because the historical corpus is not cleanly 1:1 materializable and no richer cache exists to recover from; (P3) the forward write driver on `rf ingest`, now dependent on P1.5; (P4) reuse-field reachability on `LaunchRunRequest`; (P5) the canonical-merge UI build flag; (P6) a DI-1-scoped audit of every new write site plus docs. No new services or tables are introduced; P1.5's algorithmic surface is a bounded fuzzy-match utility, not a new service. Success is a populated Catalog tab fed by a working forward path, a reachable reuse decision, an activatable merge UI, and zero unscoped writes -- not a claim that every historical claim was recovered.

**Priority**: HIGH

**Key Milestones**:
- Phase 1 exit: isolation contract proven, senior-code-reviewer signs off before P2/P3/P4 branch from it.
- Phase 1.5 exit: a verbatim quote materializes end-to-end (>=1 exact-passage match); flag-off/no-workspace-id path unchanged; **karen** security sign-off.
- Phase 2 exit: SPIKE decision recorded (delivered); backfill idempotent; **karen** security sign-off.
- Phase 3 exit: forward driver live (depends on Phase 1.5); flag-off regression proven; **karen** security sign-off.
- Phase 4 exit: reuse reachable via CLI/HTTP, denied path tested.
- Phase 5 exit: merge UI renders on `:3030`; `tsc` clean.
- Phase 6 exit: **karen** feature-end gate; DI-1-scoped audit accepted (now also covers Phase 1.5's write-binding change).

---

## Implementation Strategy

### Architecture Sequence

This is a **driver feature** -- it introduces no new database tables, repositories, or services. The sequence follows the decisions block's phase boundaries (reshaped per the P2-01 SPIKE verdict), which map to a safety-substrate-first ordering rather than the generic DB->Repo->Service->API->UI ladder:

1. **Write-Path Foundation (P1)** -- shared workspace-resolution + fail-closed contract; isolation test harness. Substrate for P2/P3/P4.
2. **Forward Extraction/Ingest Contract Fix (P1.5, new, blocking)** -- binds `assertion_text` to the source card's verbatim quote and wires passage segmentation into `AssertionRegistry.ingest()`. Prerequisite for P3; recommended landed before or alongside P2.
3. **Historical Backfill (P2)** -- write-path counterpart to `backfill_dry_run()`; SPIKE decision (P2-01) delivered -- accept-low-yield + narrow fuzzy>=0.9 recovery add-on.
4. **Forward Write Driver (P3)** -- wires `rf ingest` to pass workspace id into `ingest_source()`; depends on P1.5 landing first.
5. **Reuse Reachability (P4)** -- reuse fields on `LaunchRunRequest`, wired to the existing `assertion_reuse`/`assertion_impact` services.
6. **Merge UI Activation (P5)** -- frontend build-flag wiring; independent of P1-P4.
7. **Verification, DI-1 Audit, Docs (P6)** -- end-to-end smoke, scoped audit (now also covering P1.5), CHANGELOG/docs, karen feature-end gate.

### Parallel Work Opportunities

- **P5** has no backend dependency and can start immediately alongside P1 and P1.5 (wave 1). **P1.5** also has no dependency on P1's workspace-resolution helper (the contract fix is orthogonal to workspace scoping) and runs in wave 1 alongside P1.
- **P2 and P4** can run in parallel once P1 and P1.5 land (wave 2) -- they touch disjoint files (`assertion_rollout.py`/`assertion_registry.py`/`assertion_materialization.py` vs. `api/routers/runs.py`/`run_launch.py`).
- **P3** shares `src/research_foundry/cli_commands.py` with P2 (both add/modify CLI commands) -- this is a declared **serialization barrier**; P3 is pushed to the adjacent wave (wave 3) to avoid a concurrent-edit collision, per the wave-plan two-pass algorithm. P3 additionally hard-depends on P1.5 (wave 1), which is already satisfied by wave 3.

### Critical Path

`P1 -> P1.5 -> P2 -> P6` (P1.5 also gates `P3` directly). P2 remains the long pole for build volume: it now carries the resolved SPIKE decision (delivered, no longer blocking) plus the algorithmic backfill build and its scoped recovery add-on (H3-flagged). P1.5 is a new, smaller but strictly blocking pole for the forward path specifically -- P3 cannot produce a non-zero-yield forward write without it. P4 and P5 are parallelizable once their dependencies land and do not extend the critical path.

### Phase Summary

| Phase | Title | Estimate | Target Subagent(s) | Model(s) | Notes |
|-------|-------|----------|--------------------|----------|-------|
| P1 | Write-path foundation & WKSP-304 scoping contract | 3 pts | python-backend-engineer, senior-code-reviewer (Mode E) | sonnet | Mode-D. [Detail](./assertion-ledger-activation-v1/phase-1-foundation.md) |
| P1.5 | Forward extraction/ingest contract fix (**new, blocking**) | 3 pts | python-backend-engineer, karen | sonnet | Mode-D (WKSP-304-adjacent). SPIKE-mandated (P2-01 verdict). karen security milestone. Blocks P3; recommended landed before/alongside P2. [Detail](./assertion-ledger-activation-v1/phase-1-5-extraction-contract-fix.md) |
| P2 | Historical claim to assertion backfill migration | 13 pts | python-backend-engineer, data-layer-expert, karen | sonnet (validator/karen per their configs) | Mode-D. SPIKE decision RESOLVED (P2-01, delivered). **+4 pts (2026-07-16)**: two new blocking prerequisites found by the SPIKE's post-fix re-measurement -- P2-01a (fix defect 1c bijection gate) and P2-01b (skip-and-continue materialization mode). Restated success criteria: 94.78% fact-level yield achievable once 1c + skip-and-continue land; 0.70% end-to-end yield today. karen security milestone. [Detail](./assertion-ledger-activation-v1/phase-2-backfill.md) |
| P3 | Forward write driver | 3 pts | python-backend-engineer, karen | sonnet | Mode-D. **Depends on P1.5** (contract fix). karen security milestone. [Detail](./assertion-ledger-activation-v1/phase-3-4-forward-and-reuse.md) |
| P4 | Reuse reachability | 3 pts | python-backend-engineer, api-designer | sonnet | Mode-D. integration_owner: python-backend-engineer. [Detail](./assertion-ledger-activation-v1/phase-3-4-forward-and-reuse.md) |
| P5 | Canonical-merge UI activation | 2 pts | ui-engineer | sonnet | Frontend-only, not Mode-D. [Detail](./assertion-ledger-activation-v1/phase-5-6-ui-and-verification.md) |
| P6 | Verification, DI-1-scoped audit, docs | 3 pts | task-completion-validator, karen, senior-code-reviewer, ui-engineer, documentation-writer, changelog-generator | sonnet (haiku for docs); karen on opus | karen feature-end gate. Audit scope now also covers P1.5's write-binding change. [Detail](./assertion-ledger-activation-v1/phase-5-6-ui-and-verification.md) |
| **Total** | -- | **30 pts** | -- | -- | Pre-SPIKE locked estimate was 21 pts. Delta: +3 pts for blocking Phase 1.5 (contract fix) and +2 pts for Phase 2's SPIKE-resolved scope (2026-07-15), then **+4 pts (2026-07-16)** for two new blocking Phase 2 prerequisites (P2-01a, P2-01b) found by the SPIKE's post-fix re-measurement (`docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md` -- "## Post-fix re-measurement (2026-07-16)"). 21 -> 26 -> 30 pts. |

**Model column conventions:** Claude-only phases list the single Claude model. Karen's underlying model is `opus` per this project's agent registry (`CLAUDE.md` -> Review & Validation table); task-completion-validator and senior-code-reviewer run on `sonnet`.

---

## Estimation Sanity Check

**Noun count (H1)**: 0 new domain nouns (no new database tables or first-class CRUD entities). This feature calls existing services from `reusable-assertion-ledger-v1`; it wires new call sites, not new persisted entities. H1 floor: 0 pts.

**Dual-impl multiplier (H2)**: N/A -- Research Foundry has no local/enterprise dual-implementation repository split. Single-edition, file-first architecture. Not applied.

**Algorithmic flag (H3)**: **Flagged, on two phases.** (1) **P2's backfill** involves matching paraphrased extraction facts against verbatim source-assertion quotes via a bounded `difflib`-style fuzzy comparator -- correctness-dominated, H3-targeted. Per the P2-01 SPIKE's own empirical measurement, budgeted at 9 pts (2 pts SPIKE decision, delivered by the SPIKE document itself + 5 pts base write-path build, unchanged + 2 pts for the narrow fuzzy>=0.9 quote-recovery add-on -- the SPIKE explicitly recommends "+1-2 pts, not the plan's flagged +3-5 pts" for this add-on; this Sanity Check locks the upper end of that range because the recovery step also requires a spot-check/review step, not pure automation). (2) **P1.5's contract fix is explicitly NOT H3-flagged** -- it is a mechanical binding change (bind `assertion_text` to an already-resolved evidence-point quote; dedupe and pass a `passages=` list into an existing `ingest()` call), not a dependency/resolution/graph/ranking algorithm. Budgeted at 3 pts as substrate/contract work, comparable to P1's 3-pt foundation phase. The test matrix for both phases is enumerable and non-trivial -- Phase 2's detail file lists ≥9 concrete scenarios drawn from `assertion_materialization.py`'s real `_Abstain` codes (17 distinct denial codes exist in the module).

**Bundle decomposition (H4)**: This plan now bundles 7 capability areas under one feature slug (write-path foundation, **forward extraction/ingest contract fix**, historical backfill, forward driver, reuse reachability, merge-UI activation, verification/audit). Per H4, the plan total must be >= the sum of independent per-area estimates:

| Capability Area | Independent Estimate | Notes |
|-----------------|----------------------|-------|
| P1 -- Write-path foundation | 3 pts | Matches decisions-block anchor. |
| P1.5 -- Forward extraction/ingest contract fix (**new**) | 3 pts | New per the P2-01 SPIKE's primary recommendation; not in the original decisions-block anchor. |
| P2 -- Historical backfill | 9 pts | +2 pts vs. the pre-SPIKE 7-pt estimate: SPIKE decision (2 pts, delivered) + base build (5 pts, unchanged) + narrow fuzzy>=0.9 recovery add-on (2 pts, new, H3). |
| P3 -- Forward write driver | 3 pts | Matches anchor; scope unchanged (small remaining step once P1.5 lands), only its dependency graph changed. |
| P4 -- Reuse reachability | 3 pts | Matches anchor. |
| P5 -- Merge UI activation | 2 pts | Matches anchor. |
| P6 -- Verify, audit, docs | 3 pts | +1 pt vs. original anchor for the DI-1-scoped audit artifact + runtime smoke task (unchanged by this revision; audit scope now also enumerates P1.5's files). |
| **Σ** | **26 pts** | **Floor for plan total.** |

**Anchor (H5)**: `reusable-assertion-ledger-v1` (71 pts total) remains the primary anchor for the same reasons as before (this plan *drives* existing machinery rather than *building* it; no same-class comparable exists). The **P2-01 SPIKE itself now provides a tighter secondary anchor for P2 specifically**: its own math -- "2 pt SPIKE [delivered] + ~5 pt base build + ~1-2 pt scoped recovery add-on" = "~8-9 pts" -- lands almost exactly on this Sanity Check's independently-derived 9 pts, which is a meaningful corroboration signal (two derivations, same order of magnitude, converging within the SPIKE's own stated range). P1.5 has no comparable prior anchor (this project has not previously had to retrofit an extraction/ingest contract after the fact); its 3-pt estimate rests on comparison to P1's structurally similar 3-pt substrate phase, not a domain-matched anchor.

**Plumbing budget (H6)**: ~10% of subtotal (~2.5 pts), intentionally folded into existing line items rather than added as a separate row, to avoid double-counting: P4-01 already covers the `LaunchRunRequest` OpenAPI regen; P6-05 already covers CHANGELOG/docs; P1.5's test suite reuses P1-03's shared isolation fixture rather than duplicating plumbing. No dedicated plumbing task added.

**Huge-file touch (H7)**: Checked via `wc -l` on every file in `files_affected`, including the newly-added `extraction.py`. Largest is `assertion_registry.py` at 767 lines; `ClaimAuditWorkbench.tsx` at 769 lines. Both well under the 2K-line threshold. Not applied.

**Bottom-up total**: **26 pts**
**Top-down intuition**: pre-SPIKE locked estimate was 21 pts (decisions-block anchor 18 pts).
**Locked estimate**: **26 pts** (bottom-up governs; no compression applied -- the +5 pt delta vs. the pre-SPIKE locked estimate is fully attributed to the new blocking Phase 1.5 (+3 pts) and Phase 2's revised, SPIKE-corroborated scope (+2 pts), both explained above and both grounded in the P2-01 SPIKE's empirical corpus-wide measurement rather than estimation guesswork).

---

## Deferred Items & In-Flight Findings Policy

### Deferred Items

| Item ID | Category | Reason Deferred | Trigger for Promotion | Target Spec Path |
|---------|----------|-----------------|-----------------------|-------------------|
| DF-001 | spike-needed | OQ-1 investigation confirmed the historical claim-ledger to source-assertion mapping is not 1:1 (97.0% abstain-eligible); the resolution among "accept low yield / build a quote-recovery step / defer" is a scoped design decision, not yet made. | Task P2-01 completes with a recorded decision. | `docs/project_plans/design-specs/assertion-ledger-backfill-mapping-strategy.md` |
| DF-002 | research-needed | OQ-3: exact `assertion_registry_workspace_id` resolution for a single-operator deployment is asserted by analogy to the WKSP-304 `identity=None` pattern but not yet confirmed against the live default-workspace resolution path. | Confirmed during Phase 1 (task P1-01). | N/A -- resolved inline in P1; no standalone design-spec needed unless P1-01 surfaces a genuine ambiguity. |
| DF-003 | design | OQ-4: whether the canonical-merge UI (P5) must be verified against real backfilled data (which depends on P2's output and its mapping-strategy decision) or a synthetic fixture suffices. | Resolved during Phase 5 (task P5-02); if a fixture is used, document why real-data verification is not also required. | N/A -- resolved inline in P5; documented in the phase detail, not a standalone design-spec. |

**Note on sequencing (updated 2026-07-15)**: DF-001's decision has been **delivered** by the P2-01 SPIKE (`docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md`) rather than by the standalone design-spec P2-01's task text originally described -- the SPIKE's rigor (charter-driven, corpus-wide empirical measurement, live code experiment) exceeds what the original design-spec task scoped. The residual administrative step is to promote the SPIKE's verdict into `docs/project_plans/design-specs/assertion-ledger-backfill-mapping-strategy.md` (`maturity: ready`, `prd_ref` set, `related_documents` pointing back to the SPIKE) and append that path to this plan's `deferred_items_spec_refs` frontmatter field -- folded into P2-01's existing 2-pt estimate in the revised Phase 2 detail file, not a new line item.

### In-Flight Findings

**Lazy-creation rule applies.** `findings_doc_ref` remains `null` at plan authoring time. If execution surfaces a plan/reality mismatch not covered above, create `.claude/findings/assertion-ledger-activation-findings.md` on the first real finding per `.claude/skills/planning/references/deferred-items-and-findings.md`.

### Quality Gate

Phase 6 (Verification, DI-1-scoped audit, docs) cannot be sealed until:
- [ ] DF-001's design-spec is authored and linked in `deferred_items_spec_refs`.
- [ ] DF-002 and DF-003 are resolved inline (P1-01, P5-02 respectively) or escalated to a standalone design-spec if genuinely ambiguous.
- [ ] `findings_doc_ref` is populated and `status: accepted` if any in-flight finding occurred, or remains `null` if none did.

---

## Phase Breakdown

Detailed task tables, quality gates, key files, and AC mappings live in the linked phase files (this parent stays under the 800-line budget per the planning skill's optimization pattern).

### Phase 1: Write-Path Foundation & WKSP-304 Scoping Contract (3 pts) -- Mode D

Establishes the shared workspace-scoped write contract and fail-closed isolation test harness that every subsequent write-touching phase (P2, P3, P4) builds on. No user-facing behavior change.

**Detail**: [`phase-1-foundation.md`](./assertion-ledger-activation-v1/phase-1-foundation.md)

### Phase 1.5: Forward Extraction/Ingest Contract Fix (3 pts) -- Mode D (WKSP-304-adjacent), NEW, BLOCKING

Fixes the two compounding defects the P2-01 SPIKE found: (a) binds `assertion_text` to the source card's verbatim `extracted_points[].quote` instead of the paraphrased extraction/claim text; (b) wires passage segmentation into `AssertionRegistry.ingest()` via `source_cards.ingest_source()`'s `passages=` argument (proven live: 0 matches before, 1 match after). Blocking prerequisite for Phase 3 (forward write driver); recommended landed before or alongside Phase 2. **karen security milestone** at exit -- this phase changes what `assertion_text` means for every future write, forward or backfilled.

**Detail**: [`phase-1-5-extraction-contract-fix.md`](./assertion-ledger-activation-v1/phase-1-5-extraction-contract-fix.md)

### Phase 2: Historical Claim -> Assertion Backfill Migration (9 pts) -- Mode D, SPIKE decision RESOLVED

Write-path counterpart to `backfill_dry_run()`. The mapping-strategy decision (P2-01) is now **resolved and delivered** by the P2-01 SPIKE (`docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md`): accept the ~3.0% exact-match-eligible yield as the floor, plus a narrow, spot-checked fuzzy>=0.9 quote-recovery add-on (~6.8% total yield). No open-ended re-derivation against a "cached source text" -- the SPIKE confirmed no such cache exists for this corpus. Idempotent, resumable, workspace-scoped. Exposed as a gated operator CLI command. **karen security milestone** at exit.

**Detail**: [`phase-2-backfill.md`](./assertion-ledger-activation-v1/phase-2-backfill.md)

### Phase 3: Forward Write Driver (3 pts) -- Mode D

**Depends on Phase 1.5.** Wires the resolved OQ-2 entry point (`rf ingest`) to pass `assertion_registry_workspace_id` + `ledger_write_allowed` into `source_cards.ingest_source()` so new runs populate the ledger. Once Phase 1.5's contract fix lands, this remains the small step it always was -- wiring the workspace id -- rather than a separate correctness fix. **karen security milestone** at exit.

**Detail**: [`phase-3-4-forward-and-reuse.md`](./assertion-ledger-activation-v1/phase-3-4-forward-and-reuse.md)

### Phase 4: Reuse Reachability (3 pts) -- Mode D

Exposes reuse fields on `LaunchRunRequest`, wired to the existing `assertion_reuse`/`assertion_impact` decision services. `integration_owner: python-backend-engineer` (R-P3: overlapping ownership with `api-designer` on `api/routers/runs.py`/`run_launch.py`).

**Detail**: [`phase-3-4-forward-and-reuse.md`](./assertion-ledger-activation-v1/phase-3-4-forward-and-reuse.md)

### Phase 5: Canonical-Merge UI Activation (2 pts)

Wires `VITE_RF_CANONICAL_CLAIMS_ENABLED=true` through the standard deploy/bootstrap path (mirroring `RF_UI_LOOPBACK`); verifies merge-review controls render.

**Detail**: [`phase-5-6-ui-and-verification.md`](./assertion-ledger-activation-v1/phase-5-6-ui-and-verification.md)

### Phase 6: Verification, DI-1-Scoped Audit, Docs (3 pts) -- karen feature-end gate

End-to-end verification (R-P4 runtime smoke), DI-1-scoped audit of this feature's new write sites (now including Phase 1.5's write-binding change), CHANGELOG/docs. **karen feature-end gate.**

**Detail**: [`phase-5-6-ui-and-verification.md`](./assertion-ledger-activation-v1/phase-5-6-ui-and-verification.md)

---

## Model & Effort Assignment

Model and Effort columns in every phase's task table use the canonical vocabulary in `.claude/skills/planning/references/multi-model-guidance.md`. Summary of phase-level defaults (see `wave_plan.phases[]` in frontmatter):

| Phase | Default Model | Default Effort | Rationale |
|---|---|---|---|
| P1 | sonnet | extended | Security substrate -- isolation contract must be right the first time. |
| P1.5 | sonnet | extended | Provenance/trust-boundary fix -- what `assertion_text` means changes for every future write. |
| P2 | sonnet | extended | Algorithmic migration (H3-flagged) + SPIKE-resolved decision (delivered). |
| P3 | sonnet | adaptive | Mechanical wiring once P1 and P1.5 land. |
| P4 | sonnet | adaptive | Mechanical wiring once P1 lands. |
| P5 | sonnet | adaptive | Frontend build-flag wiring. |
| P6 | sonnet (haiku for docs; karen on opus) | adaptive | Verification/audit/docs mix. |

Per-task overrides appear in each phase's detail file where a task's complexity diverges from its phase default (e.g., P2-01's SPIKE task and P1's isolation-harness task both use `extended`).

---

## Risk Mitigation

### Technical Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|---------------------|
| WKSP-304 isolation leak on a new write site (DI-1-adjacent) | High | Medium | P1 shared test harness proves confinement + fail-closed before P2/P3/P4 build on it; DI-1-scoped audit in P6 (now also covering P1.5); senior-code-reviewer/karen milestones after P1, P1.5, P2, P3, and P6; Mode-D labeling -- no auto-merge, diffs reviewed before merge/deploy. |
| Forward extraction/ingest contract fix (P1.5) changes what `assertion_text` means for every future write, forward and backfilled alike | High | Confirmed (SPIKE-proven) | Scope is bounded to the two SPIKE-proven defects (bind to quote; wire `passages=`) -- no generic threshold relaxation (SPIKE RQ3 explicitly rejects that). karen security milestone reviews the diff before P2/P3 build on it. AC-8/AC-9 require a live end-to-end proof (>=1 verbatim-quote match) and a flag-off/no-workspace-id regression, not just unit coverage. |
| Backfill mapping strategy is unresolved or under-scoped (this plan's original headline finding) | ~~High~~ Resolved | ~~Confirmed~~ Delivered | **Resolved by the P2-01 SPIKE** (`docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md`, 2026-07-15): accept-low-yield + narrow fuzzy>=0.9 quote-recovery add-on (~6.8% total yield), +1-2 pts. Residual risk is now just correct implementation of that scoped decision, not decision ambiguity. |
| Backfill non-idempotency / double-materialization | Medium | Low | Content-addressed editions/passages already guarantee idempotency at the registry layer; explicit re-run-is-no-op regression test (P2-05); dry-run parity assertion. |
| Enabling the forward write driver changes existing run behavior | Medium | Medium | Gate strictly on `ledger_write_enabled`; flag-off path must be byte-identical to today (P3-02 regression test, mirrors the AAR's A2 fix approach). Compounded by P1.5's dependency: P3's flag-off test must also confirm the contract fix itself introduces no behavior change when the flag is off. |
| Reuse fields widen the run-launch validation/attack surface | Low-Med | Low | Validate/authorize reuse targets; wire the existing governed `block_authoritative_reuse` path rather than inventing new policy (P4-02). |
| Merge-UI build flag drifts on redeploy | Low | Medium | Set `VITE_RF_CANONICAL_CLAIMS_ENABLED` in bootstrap the same way `RF_UI_LOOPBACK` is set; document the deploy flag (P5-01, P6-05). |

### Schedule Risks

| Risk | Impact | Likelihood | Mitigation Strategy |
|------|--------|------------|---------------------|
| P2's fuzzy-recovery add-on (P2-06) surfaces materially more work than the 2 pt estimate covers | Medium | Low | Scope is capped at the SPIKE's own empirically-validated ceiling (fuzzy>=0.9 + spot-check); the SPIKE explicitly rejects lower thresholds as unsafe, which forecloses the most likely source of scope creep (a temptation to loosen the threshold for more yield). |
| P1.5 not landed before P2/P3 start, forcing rework | Medium | Medium | Wave plan places P1.5 in wave 1 (parallel with P1), strictly before P2/P3's wave 2/3; P2 and P3 both declare `depends_on: [P1, P1.5]` in the wave plan so an orchestrator cannot start them early by omission. |
| `cli_commands.py` serialization barrier (P2 and P3 both edit it) causes merge conflicts if run truly in parallel | Low | Low | Wave plan already sequences P3 into wave 3, after P2's wave 2 -- not a true parallel edit. |
| karen milestone backlog (5 gates: P1 reviewer, P1.5, P2, P3, P6) creates a queueing bottleneck | Medium | Low | Gates are staggered across the wave plan, not simultaneous; P1's gate is `senior-code-reviewer` (Mode E), not karen, keeping karen's load at 4 gates (P1.5, P2, P3, P6) -- one more than the pre-SPIKE plan, reflecting P1.5's genuine trust-boundary significance rather than gate proliferation for its own sake. |

---

## Resource Requirements

### Team Composition (agent routing, not human FTE -- this project delegates all implementation to subagents)

- **python-backend-engineer**: Primary across P1, P1.5, P2, P3, P4.
- **data-layer-expert**: Secondary in P2 (ledger-store semantics seam task).
- **api-designer**: Secondary in P4 (OpenAPI contract for reuse fields).
- **ui-engineer**: Primary in P5; smoke-test support in P6.
- **senior-code-reviewer**: Mode E review in P1; DI-1-scoped audit author in P6 (scope now includes P1.5).
- **task-completion-validator**: Gate at every phase exit (Tier 3 requirement).
- **karen**: Security milestone after P1.5, P2, and P3; feature-end gate at P6.
- **documentation-writer, changelog-generator**: Docs/CHANGELOG in P6.

### Skill Requirements

Python (FastAPI, Pydantic, content-addressed file I/O), the existing `assertion_registry`/`assertion_materialization` service contracts, Typer CLI patterns (`cli_commands.py`), React/Vite build-flag patterns (`frontend/runs-viewer`), and the WKSP-304 workspace-isolation confinement pattern.

---

## Success Metrics

See frontmatter `success_metrics` (revised per the P2-01 SPIKE verdict) and the PRD's §4 Success Metrics table, §11 structured acceptance criteria (AC-1..AC-9), and §11 Functional/Technical/Quality/Documentation Acceptance checklists -- this plan's phase task tables map directly to those via each phase detail file's AC-mapping section.

### Delivery Metrics
- Every phase's `task-completion-validator` gate passes before the next dependent phase starts.
- karen sign-off recorded at P1.5, P2, P3, and P6.
- Zero P0/P1 regressions in the flag-off / no-workspace-id path (P1.5's regression test, P3-02).

### Technical Metrics
- 0 unscoped write call sites at the P6 DI-1-scoped audit (scope now includes P1.5's changed files).
- At least one verbatim quote materializes end-to-end post-P1.5 (AC-8).
- `tsc -p tsconfig.app.json --noEmit` clean for all P5 frontend changes.
- Backfill idempotency and flag-off regression suites green.

---

## Wrap-Up: Feature Guide & PR

**Triggered**: Automatically after Phase 6 is sealed (all Phase 6 quality gates pass, including the karen feature-end gate).

### Step 1 -- Feature Guide

Delegate to `documentation-writer` (haiku) to create `.claude/worknotes/assertion-ledger-activation/feature-guide.md` per the standard frontmatter and section structure (What Was Built, Architecture Overview, How to Test, Test Coverage Summary, Known Limitations -- the latter MUST state the backfill's exact-match-eligible coverage rate transparently, not just "backfill implemented"). Commit before opening the PR.

### Step 2 -- Open PR

```bash
gh pr create \
  --title "Wire assertion-ledger write/reuse/merge-UI drivers (Tier 3, SPIKE-resolved contract fix + backfill)" \
  --body "$(cat <<'EOF'
## Summary
- Establishes a workspace-scoped, fail-closed write contract for the assertion ledger (P1)
- Fixes the extraction/ingest contract so a verbatim quote can materialize at all (P1.5, new, blocking; per the P2-01 SPIKE)
- Backfills historical claim ledgers under the SPIKE-resolved accept-low-yield + fuzzy-recovery decision (P2)
- Wires forward write, reuse reachability, and canonical-merge UI activation (P3-P5)
- DI-1-scoped audit closes this feature's new-write-site delta, including P1.5 (P6)

## Feature Guide
.claude/worknotes/assertion-ledger-activation/feature-guide.md

## Test plan
- [ ] Isolation regression matrix green (P1)
- [ ] Verbatim-quote end-to-end materialization + flag-off/no-workspace-id regression green (P1.5)
- [ ] Backfill idempotency + interrupted-run tests green (P2)
- [ ] Flag-off regression test green (P3)
- [ ] Reuse allow/deny reachability tests green (P4)
- [ ] tsc clean; merge UI screenshots attached, flag on/off (P5)
- [ ] DI-1-scoped audit artifact linked (covers P1.5); karen feature-end sign-off attached (P6)

🤖 Generated with Claude Code
EOF
)"
```

---

## Communication Plan

- Phase-exit status posted at each `task-completion-validator` gate.
- karen milestone results (P1.5, P2, P3, P6) posted verbatim -- do not summarize a karen "fail" as a "pass with notes."
- The Tier 3 promotion and the P2-01 SPIKE verdict (delivered 2026-07-15, `docs/project_plans/SPIKEs/assertion-ledger-backfill-mapping.md`) have already been escalated to and reviewed by the human orchestrator per this plan's Mode-D labeling; Phase 1.5 and Phase 2's build tasks may proceed against the resolved decision recorded in this plan's frontmatter `decisions`/`decision_gates`.

---

## Post-Implementation

- Monitor the backfill receipt's abstain-code distribution against the 97.0% pre-fix baseline established during planning; a materially different live distribution (e.g., meaningfully higher than the SPIKE's ~6.8% estimate) is itself a finding worth capturing -- especially given Phase 1.5 changes the same underlying materializer gate that Phase 2's backfill also calls; do not silently assume the SPIKE's estimate still holds byte-for-byte once P1.5 lands.
- Track DI-1 project-wide closure separately -- this feature's audit (P6) closes only its own delta, not the full-project gate (`docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md:329`).
- Revisit `VITE_RF_CANONICAL_CLAIMS_ENABLED` bootstrap wiring on the next `agentic_meta_dev` redeploy to confirm it survived (mirrors the `RF_UI_LOOPBACK` drift risk).

---

**Progress Tracking:**

Not created by this plan (artifact-tracking is a separate step). Once authorized: `.claude/progress/assertion-ledger-activation/phase-N-progress.md`.

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-07-15
