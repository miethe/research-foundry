---
title: "Implementation Plan: Wave-5 Integration & Qualification"
schema_version: 2
doc_type: implementation_plan
status: draft
created: 2026-07-31
updated: 2026-07-31
feature_slug: wave5-integration-qualification
feature_version: v1
tier: 3
prd_ref: docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
plan_ref: null
human_brief_ref: null
scope: >-
  Close out the research-interchange-provenance-access initiative's final wave (the
  epic's H6 24-pt reserve): author a repo-wide evidence taxonomy that generalizes C2's
  ad-hoc vocabulary into a checkable artifact (DG-6), remediate C4's self-attested
  reviewer evidence with an independent re-attestation, build the cross-child contract
  test suite spanning the seven seams (S-1..S-7) between C1-C5, and clear the ten
  §9-blocking reconciliation items (R-1..R-10). No new production capability is
  in scope — this wave proves and reconciles what the five children already shipped.
effort_estimate: "24 pts bottom-up (epic's H6 reserve; no package discount, §9)"
architecture_summary: >-
  A read-only synthesis wave over five already-landed children: consolidates scattered
  evidence claims into one taxonomy, obtains independent re-attestation for the one
  self-attested child (C4), wires seven cross-child integration tests through existing
  fixture builders and the `integration` pytest marker (no new production surfaces),
  and closes epic-level bookkeeping (status, refs, OQs, ACs, CHANGELOG).
related_documents:
  - .claude/findings/wave5-integration-qualification-audit.md
  - .codex/plans/research-interchange-provenance-access-initiative-v1.md
  - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
  - docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
  - docs/user/external-research-interchange.md
  - docs/dev/architecture/artifact-type-reference.md
references:
  user_docs: []
  context: []
  specs:
    - .claude/skills/planning/references/plan-doctrine.md
    - .claude/skills/planning/references/ac-schema.md
    - .claude/skills/dev-execution/references/execution-doctrine.md
    - .claude/skills/dev-execution/references/gate-risk-classes.md
spike_ref: null
adr_refs: []
deferred_items_spec_refs: []
findings_doc_ref: .claude/findings/wave5-integration-qualification-audit.md
charter_ref: null
changelog_ref: null
changelog_required: true
test_plan_ref: null
plan_structure: unified
progress_init: auto
owner: nick
contributors: []
priority: high
risk_level: high
category: enhancements
tags: [implementation, integration, qualification, dg-6, cross-child-testing, epic-closeout, wave5, reconciliation]
milestone: null
# Sizes AGENT CONTEXT, not behavior (plan-doctrine.md § Context class). Dominant class:
# repo-wide synthesis over five children's artifacts. M3 is the outlier — see its note.
context_class: C3
# CONSTRAINTS, never model ids — `delegation-router` resolves provider+model at dispatch
# time against the live registry.
routing_constraints:
  - "M2's independent reviewer re-attestation MUST stay claude-primary, on fresh context, and MUST NOT be run by the session that implemented or last touched Knowledge MCP (C4) — self-attestation is the exact defect being remediated."
  - "M3's S-5 (C4→C5) and S-6 (C5→C1) test assertions MUST stay claude-primary on fresh context — the only two seams in this plan that cross an authorization/governance boundary (Operator MCP mutation, audit-to-receipt closure)."
  - "Fixture assembly for S-1..S-4 and S-7 scaffolding (M3), and all R-1..R-10 bookkeeping (M4), are offload-eligible."
  - "M1 taxonomy schema authoring is offload-eligible for drafting; the schema shape gets an Opus sanity read before it is applied to five children's frontmatter (M1-T3)."
  - "Capability bar — M1: workhorse-class. M2: frontier-class for the re-attestation pass itself; workhorse for report.json bookkeeping. M3: frontier-class for S-5/S-6 and the S-7 full-chain test; workhorse for S-1..S-4. M4: economy-class throughout."
  - "Cross-model offload is unavailable for governance-boundary lenses in this initiative — the C5 plan records that Codex refused the adversarial-audit framing under its safety classifier. Do not re-attempt for M3's S-5/S-6."
required_artifacts:
  - {type: agent, name: task-completion-validator, skillmeat_ref: task-completion-validator, status: available, lifecycle: permanent, scope: null, note: "milestone validator gate; on-disk at user scope"}
  - {type: agent, name: karen, skillmeat_ref: karen, status: available, lifecycle: permanent, scope: null, note: "M3 per-milestone (context_class C4 trigger) + M4 final-tree pass"}
  - {type: agent, name: senior-code-reviewer, skillmeat_ref: senior-code-reviewer, status: available, lifecycle: permanent, scope: null, note: "M2 independent re-attestation candidate lens — fresh context, not the C4 implementer"}
  - {type: agent, name: python-backend-engineer, skillmeat_ref: python-backend-engineer, status: available, lifecycle: permanent, scope: null, note: "M3 integration test authoring"}
  - {type: agent, name: documentation-writer, skillmeat_ref: documentation-writer, status: available, lifecycle: permanent, scope: null, note: "M1 taxonomy/ledger doc, M4 DG-6 report; haiku default hard-errors here, dispatch workhorse"}
  - {type: agent, name: changelog-generator, skillmeat_ref: changelog-generator, status: available, lifecycle: permanent, scope: null, note: "M4 dated CHANGELOG sections; same haiku caveat"}
  - {type: skill, name: delegation-router, skillmeat_ref: delegation-router, status: available, lifecycle: permanent, scope: null, note: "resolves provider+model per leg at dispatch"}
  - {type: skill, name: dev-execution, skillmeat_ref: dev-execution, status: available, lifecycle: permanent, scope: null, note: "milestone execution engine"}
  - {type: skill, name: artifact-tracking, skillmeat_ref: artifact-tracking, status: available, lifecycle: permanent, scope: null, note: "progress tracking"}
open_questions:
  - id: W5-OQ-1
    status: open
    question: "R-10: does Wave 5 author an agent-facing Operator MCP skill, or record explicit non-goal rationale? Architecture + user docs exist; nothing teaches the governed tool surface, and affects_skills never listed one — possibly by design, decide explicitly (M4-T5)."
  - id: W5-OQ-2
    status: open
    question: "Carried from C5 (OPM-OQ-5): does M3's Karen pass discharge OPM-DF-regate (deferred P1 round-6 re-gate), or does the P1 surface need its own re-verdict? Resolve inside M4-T3 alongside epic OQ closure."
decisions:
  - decision: "Wave 5 introduces no new production code surface."
    rationale: "§9 completion rules are about proving and reconciling what already shipped, not building new capability. If M3 test authoring discovers a genuinely missing production seam (not just missing coverage), that is a §11 stop condition, not an in-scope fix."
    status: accepted
  - decision: "M1's taxonomy generalizes C2's existing four-state vocabulary (repository-ready → offline-unvalidated → owner/private-qualified → live-qualified) rather than inventing a new one."
    rationale: "Audit §3: it is the only precedent in the repo and is already honestly applied where it exists (docs/user/external-research-interchange.md:21-25). Reuse avoids a second, competing vocabulary — the audit found no overstated claim, only a scattered, unenforced one."
    status: accepted
  - decision: "M2's remediation path allows an explicit evidence-strength downgrade as a valid outcome, not only a passing re-attestation."
    rationale: "§9 requires exact-tree reviewer evidence, not a guaranteed pass. A recorded, honest downgrade is compliant; leaving 'verified_by: self' unexamined is not."
    status: accepted
  - decision: "M1/M2/M3 run in one parallel wave; M4 runs alone afterward."
    rationale: "M1 (taxonomy + ledger), M2 (C4 re-attestation), and M3 (new test files under tests/integration/) touch disjoint file sets and have no data dependency on each other. M4 (status flips, refs, CHANGELOG, epic ACs, DG-6 report) reads the outcomes of all three and writes to files each of them may also have touched (child plan frontmatter, docs cross-links) — it must run last, against the merged result."
    status: accepted
wave_plan:
  serialization_barriers:
    - CHANGELOG.md
    - .codex/plans/research-interchange-provenance-access-initiative-v1.md
    - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
    - docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
    - docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
    - docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
    - docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
    - docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
  phases:
    - id: M1
      title: "One evidence taxonomy replaces five scattered vocabularies"
      depends_on: []
      isolation: worktree
      parallelizable: true
      context_class: C2
      gate_lens: [validator]
      exit_criteria:
        - "Taxonomy schema (4 states) exists as a reusable, checkable artifact — not prose-only"
        - "Consolidated ledger covers every row in audit §3's integration-status table"
        - "Taxonomy field is applied to all 5 child implementation plans' frontmatter"
      files_affected:
        - docs/dev/architecture/integration-evidence-taxonomy.md
        - docs/dev/architecture/integration-evidence-ledger.md
        - docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
        - docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
        - docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
        - docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
        - docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
        - docs/user/external-research-interchange.md
        - docs/dev/architecture/artifact-type-reference.md
    - id: M2
      title: "C4's reviewer evidence is independent, not self-attested"
      depends_on: []
      isolation: worktree
      parallelizable: true
      context_class: C2
      gate_lens: [validator]
      exit_criteria:
        - "An independent reviewer (not the C4 implementing session) examines tree 1376e85"
        - "report.json's four self-attested verified_by fields carry a real reviewer identity, or the ledger records an explicit downgrade with rationale"
        - "C4 plan status (R-2) reflects the outcome"
      files_affected:
        - .claude/reports/research-foundry-knowledge-mcp-v1/report.json
        - .claude/findings/wave5-integration-qualification-findings.md
        - docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
    - id: M3
      title: "Seven cross-child seams are asserted by tests, not narrative"
      depends_on: []
      isolation: worktree
      parallelizable: true
      # C4: adversarial fixtures over a novel cross-child authorization boundary (S-5/S-6),
      # fresh-context verifiers, largest and highest-risk milestone. Budget explicitly.
      context_class: C4
      gate_lens: [security, validator, karen]
      exit_criteria:
        - "S-1..S-6 each have a dedicated integration test under tests/integration/, using the integration marker and reusing named fixture builders (audit §2)"
        - "S-7 has one test driving all seven hops end-to-end"
        - "Whole-suite regression is clean against baseline; new tests are additive only"
      files_affected:
        - tests/integration/test_wave5_seam_eri_to_provenance.py
        - tests/integration/test_wave5_seam_eri_to_catalog.py
        - tests/integration/test_wave5_seam_catalog_to_knowledge.py
        - tests/integration/test_wave5_seam_provenance_to_knowledge.py
        - tests/integration/test_wave5_seam_knowledge_to_operator.py
        - tests/integration/test_wave5_seam_operator_to_provenance.py
        - tests/integration/test_wave5_full_chain.py
    - id: M4
      title: "The epic is reconciled to what actually shipped"
      depends_on: [M1, M2, M3]
      isolation: shared
      parallelizable: false
      context_class: C1
      gate_lens: [validator, karen-final-tree-only]
      exit_criteria:
        - "R-1..R-10 are each closed with a named diff or explicit rationale"
        - "All 12 epic ACs are ticked with an evidence pointer"
        - "Epic PRD, meta-plan, and all 5 child PRDs carry non-empty commit_refs/pr_refs"
        - "DG-6 qualification report separates live / synthetic / repository-readiness evidence"
      files_affected:
        - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
        - .codex/plans/research-interchange-provenance-access-initiative-v1.md
        - docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
        - docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
        - docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
        - docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
        - docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
        - CHANGELOG.md
        - docs/dev/architecture/dg-6-qualification-report.md
  waves:
    - [M1, M2, M3]
    - [M4]
---

# Implementation Plan: Wave-5 Integration & Qualification

**Plan ID**: `IMPL-2026-07-31-WAVE5-INTEGRATION-QUALIFICATION`
**Date**: 2026-07-31
**Audit**: `.claude/findings/wave5-integration-qualification-audit.md` (pre-execution audit at tree `1c8dfc9`; read that file for the full evidence base — this plan does not restate its findings)
**Complexity**: Large / Tier 3
**Total Estimated Effort**: 24 pts (epic's H6 reserve, §9 no-package-discount)

## Executive Summary

The five children of the research-interchange-provenance-access initiative are all landed on
`main` (C1 `65d658d`, C2 `e76784b`, C3 `95e8419`, C4 `1376e85`, C5 PR #7 merged `0afb56d`). Wave 5
is the initiative's own closing gate (§6 Wave 5, DG-6, §9 Completion Rules) — it does not add a
feature, it proves the five children compose correctly and reconciles the epic's paperwork. The
audit found: (1) no repo-wide evidence taxonomy exists despite DG-6 requiring one — only an ad-hoc
vocabulary living in C2's prose; (2) every child is well-tested in isolation but the seven seams
between them are essentially untested; (3) C4 alone is self-attested among five otherwise
independently-reviewed children; (4) ten bookkeeping items block §9's literal text. Nothing found
reopens a child contract or requires a new evidence authority — the §11 stop conditions are not
triggered by the audit itself, but remain live for M3's discovery work (see Stop Conditions below).

## Rubric — what "good" looks like

1. **Taxonomy over restatement.** M1 does not re-litigate whether an integration is live —it takes
   the audit's own findings and C2's existing vocabulary and makes them checkable. Inventing a
   fifth vocabulary is wrong even if internally consistent.
2. **Independent means independent.** M2's re-attestation is void if run by, or with context
   inherited from, the session that shipped C4. A reviewer that rubber-stamps because it already
   "knows" the code passed is not evidence — this is the same lesson the C5 plan already paid for
   (inherited-context validators rubber-stamp).
3. **A seam test proves composition, not existence.** Each S-1..S-6 test must drive real data
   through both children's real entry points (adapters, services, MCP tools) — importing a sibling
   test's fixture *builder* is an established, acceptable convention here (audit §2); importing its
   *assertions* is not a substitute for writing new ones.
4. **Bookkeeping is evidence-backed, not asserted.** Every R-1..R-10 closure and every epic AC tick
   in M4 names the commit, file, or test that backs it. "Done" without a pointer is not done.

## Named risks

- **M1 becomes a sixth undocumented claim.** The taxonomy must be applied to something (M1-T3) or
  it repeats exactly the defect it fixes — a well-formed vocabulary nobody uses. Do not close M1 on
  the schema doc alone.
- **M2 self-selects a "friendly" reviewer.** The routing constraint (fresh context, not the C4
  implementer) is necessary but not sufficient — the dispatched reviewer must be told explicitly
  that it is auditing, not confirming, and must have access to the findings ledger, not a summary.
- **S-5/S-6 are the highest-risk tests in this plan.** They are the only seams crossing an
  authorization boundary (a Knowledge MCP read authorizing an Operator MCP mutation; an operator
  audit event closing into a provenance receipt). A test that merely calls both services in
  sequence without asserting the actual authorization/audit linkage is a false pass — see AC
  matrix below for the exact assertion each seam test must make.
- **M3 discovers a real gap, not just a missing test.** If assembling S-1..S-7 reveals that a seam
  literally cannot be exercised (e.g., no code path actually propagates a receipt from C5 back to
  C1), that is the §11 "child needs a new evidence authority" stop condition — halt M3 for that
  seam and return to planning, do not invent a shim to make the test pass.
- **Serialization barrier conflicts.** M1 and M4 both write child-plan frontmatter and
  cross-referenced docs; M4 explicitly waits on M1/M2/M3 (wave 2) to avoid a merge race on the same
  files.

## Milestones (M1-M4)

### M1 — One evidence taxonomy replaces five scattered vocabularies

*(7 pts; context class C2; gate: validator)*

| Task | Description | Pts | Maps to |
|---|---|---:|---|
| W5-M1-T1 | Define the evidence taxonomy schema: the 4 states (`repository-ready`, `offline-unvalidated`, `owner-or-private-qualified`, `live-qualified`) as a reusable spec at `docs/dev/architecture/integration-evidence-taxonomy.md`, with a field name (e.g. `integration_evidence_status`) applicable to child artifacts, external integrations, and deferred specs alike | 2 | DG-6; audit §3 |
| W5-M1-T2 | Author the consolidated ledger `docs/dev/architecture/integration-evidence-ledger.md` covering every row of audit §3's table (MeatyWiki/SkillMeat/CCDash, IntentTree/ARC, NotebookLM, SearXNG/Search Router, ERI producer profiles ×5, Knowledge/Operator MCP remote) with a state, source-of-claim pointer, and last-verified date per row | 2 | audit §3 |
| W5-M1-T3 | Apply the taxonomy field to the 5 child implementation plans' frontmatter (or a direct pointer to the ledger row), so the classification is machine-checkable, not prose-only | 2 | DG-6 "checkable artifact" |
| W5-M1-T4 | Cross-link the ledger from every doc currently carrying an ad-hoc evidence claim (`docs/user/external-research-interchange.md`, `docs/dev/architecture/artifact-type-reference.md`, Knowledge MCP docs) so claims are made once and referenced, not restated | 1 | audit §3 |

**AC:**
- The taxonomy is a standalone spec file with exactly 4 named states and a machine-readable field
  name — not embedded only in ledger prose.
- The ledger has one row per audit §3 entry (6 rows minimum) with state + source pointer.
- All 5 child implementation plans carry the taxonomy field or an explicit ledger pointer in
  frontmatter.
- No doc in `files_affected` states an integration-status claim that contradicts the ledger.

### M2 — C4's reviewer evidence is independent, not self-attested

*(3 pts; context class C2; gate: validator — reviewer identity itself is the AC)*

| Task | Description | Pts | Maps to |
|---|---|---:|---|
| W5-M2-T1 | Dispatch an independent reviewer (fresh context, never the C4 implementing session) against exact tree `1376e85`, examining the 4 items `report.json` currently tags `"verified_by": "self"` | 1.5 | audit §4 |
| W5-M2-T2 | Remediate any findings from T1; update `report.json`'s `verified_by` fields to the real reviewer identity **or** — if independent review genuinely cannot be obtained — record an explicit evidence-strength downgrade in the M1 ledger with rationale | 1 | audit §4; §9 |
| W5-M2-T3 | Record the M2 outcome in the Wave-5 findings ledger and update C4's plan `status` field (closes R-2 jointly with M4-T1) | 0.5 | R-2 |

**AC:**
- The reviewer identity in `report.json` is not `"self"` for any of the 4 tagged items, unless
  paired with an explicit downgrade rationale in the ledger — never left silently as-is.
- The reviewer's findings (if any) are written to `.claude/findings/wave5-integration-qualification-findings.md`,
  not summarized only in a session transcript.
- C4 plan `status` reflects the true post-M2 state.

### M3 — Seven cross-child seams are asserted by tests, not narrative

*(11 pts; context class **C4** — adversarial fixtures over a novel cross-child authorization
boundary, fresh-context verifiers; gate: security + validator, then karen on this milestone)*

Reuse `tests/fixtures/external_research_handoff/` (60 files), `tests/fixtures/assertion_ledger/`
(26 files, incl. `rf_phase0_evidence_snapshot`), and the proven builder-import convention
(`build_catalog_run`, `build_packet`, `_default_operator_identity` — audit §2). The `integration`
marker and `tests/e2e/` already exist; no new pytest infrastructure is required.

| Task | Seam | Description | Pts |
|---|---|---|---:|
| W5-M3-T1 | S-1 (C2→C1) | New test: an ERI-imported report mints/binds a traceable origin/receipt via `provenance_envelope` | 1.5 |
| W5-M3-T2 | S-2 (C2→C3) | New test: an ERI-sourced candidate feeds `evaluate_reuse`/`block_authoritative_reuse` and receives a real reuse verdict | 1.5 |
| W5-M3-T3 | S-3 (C3→C4) | New test: a catalog-reused record is faithfully retrievable through `rf_search`/`rf_fetch`/`rf_source_get`, reusing `test_knowledge_parity.py`'s builder | 1.5 |
| W5-M3-T4 | S-4 (C1→C4) | New test: report-use records are read back correctly through Knowledge MCP | 1.5 |
| W5-M3-T5 | S-5 (C4→C5) — **governance boundary, claude-primary** | New test: a Knowledge MCP read feeds a governed Operator MCP mutation, with an explicit audit-event assertion tying the two | 2 |
| W5-M3-T6 | S-6 (C5→C1) — **governance boundary, claude-primary** | New test: an operator audit record closes into a C1 receipt envelope, asserted by receipt content, not by absence-of-error | 1.5 |
| W5-M3-T7 | S-7 (all) — **claude-primary** | One test driving the full seven-hop chain: external handoff → source resolution → assertion verification → catalog reuse → report-use lineage → read-only retrieval → governed operator action | 1.5 |

**AC:**
- Each of S-1..S-6 has a dedicated test module under `tests/integration/`, marked `integration`,
  asserting the actual cross-child data linkage (not merely that both calls succeed).
- S-5 and S-6 each include an explicit assertion that the authorization/audit artifact (audit event,
  receipt) exists and references the correct upstream identifiers — a passing happy-path call with
  no linkage assertion does not satisfy this AC.
- S-7 exercises all seven hops in one test and fails clearly (not silently skips) if any hop's
  fixture or seam is unavailable.
- Whole-suite regression: new tests are additive only against the current baseline; no existing
  test starts failing.
- No owner/private corpus data is used; fixtures stay public-safe per existing convention.

**Mode-D note:** M3 touches no auth, payments, migration, deletion, secret-rotation, or
infrastructure surface directly — it *tests* an existing authorization boundary (S-5/S-6), it does
not modify one. If test authoring reveals the boundary itself needs a code change, that is a real
scope change and halts per Named Risks above.

### M4 — The epic is reconciled to what actually shipped

*(3 pts; context class C1; gate: validator, then karen on the final tree only)*

| Task | Item(s) | Description | Pts |
|---|---|---|---:|
| W5-M4-T1 | R-1, R-2, R-3 | Flip stale `status: draft` to the correct lifecycle state on the C3 plan, C4 plan, and epic PRD; update `updated` dates | 0.5 |
| W5-M4-T2 | R-4, R-9 | Populate non-empty `commit_refs`/`pr_refs` on the epic PRD, meta-plan, and all 5 child PRDs; add versioned/dated CHANGELOG sections tying entries to their landing commits (currently all sit under `[Unreleased]`) | 0.75 |
| W5-M4-T3 | R-5, R-6, R-7, W5-OQ-2 | Fix C5 plan's stale "still not merged" prose (PR #7 merged `0afb56d`); resolve epic OQ-E1..E6 against owning children's recorded resolutions; tick all 12 epic ACs with evidence pointers; resolve whether OPM-DF-regate is discharged by M3's Karen pass | 0.75 |
| W5-M4-T4 | R-8 | Reconcile meta-plan self-inconsistencies (§3 vs §13 phase counts for C2 and C5) | 0.25 |
| W5-M4-T5 | R-10, W5-OQ-1 | Decide explicitly on an Operator MCP skill: author it, or record non-goal rationale and update `affects_skills` | 0.25 |
| W5-M4-T6 | DG-6 | Author `docs/dev/architecture/dg-6-qualification-report.md`, separating live / synthetic / repository-readiness evidence using M1's taxonomy and M2's outcome | 0.5 |

**AC:**
- Every one of R-1..R-10 is closed with a named diff (commit or file+line) or an explicit,
  written rationale for why it is not applicable — never silently dropped.
- All 12 epic acceptance criteria are ticked with a pointer to the evidencing commit, test, or doc.
- Epic PRD, meta-plan, and all 5 child PRDs carry non-empty `commit_refs`/`pr_refs`.
- The DG-6 report exists and, for every integration in the M1 ledger, states which of live /
  synthetic / repository-readiness evidence backs it — no integration is left unclassified.
- `karen` reviews the final exact tree (M1+M2+M3+M4 merged) once; a material fix after that
  invalidates the prior approval.

## AC → command → evidence

Single home for verification detail; run from repo root under the project venv
(`./.venv/bin/python` — the pyenv shim will fail to import `research_foundry`).

| AC | Command | Evidence of pass |
|---|---|---|
| M1 — taxonomy exists & is applied | `test -f docs/dev/architecture/integration-evidence-taxonomy.md && rg -l "integration_evidence_status" docs/project_plans/implementation_plans/enhancements/*.md` | File exists; field present in all 5 child plan frontmatter |
| M1 — ledger completeness | `rg -c "^\| " docs/dev/architecture/integration-evidence-ledger.md` | Row count ≥ 6 (one per audit §3 entry) |
| M2 — reviewer independence | Diff `report.json` `verified_by` fields before/after M2; check findings ledger for a dated, non-self entry | 4 items no longer read `"self"`, or a downgrade rationale is present in the M1 ledger |
| M3 — seam tests exist and pass | `./.venv/bin/python -m pytest tests/integration/test_wave5_seam_*.py tests/integration/test_wave5_full_chain.py -m integration -q` | 7 new tests collected and passing |
| M3 — S-5/S-6 assert real linkage, not happy-path | `rg -n "assert.*audit\|assert.*receipt" tests/integration/test_wave5_seam_knowledge_to_operator.py tests/integration/test_wave5_seam_operator_to_provenance.py` | Non-trivial assertions present on the linkage artifact itself, not only on a 200/success status |
| M3 — whole-suite regression | `./.venv/bin/python -m pytest -q` | Passing count is baseline + exactly the new Wave-5 tests; no new failures |
| M4 — R-items closed | `rg -n "R-[0-9]+" .claude/findings/wave5-integration-qualification-findings.md` | Each of R-1..R-10 has a closure note with a commit/file pointer |
| M4 — epic ACs ticked | Manual diff of epic PRD §12 (or equivalent AC section) before/after | All 12 ACs show `verified_by` populated |
| M4 — DG-6 report | `test -f docs/dev/architecture/dg-6-qualification-report.md` | File exists; every M1-ledger row is classified live/synthetic/repository-readiness |
| Lint gate | `./.venv/bin/ruff check src/research_foundry --select E9,F63,F7,F82` | Exit 0 |

Exact test filenames are reconciled against the current tree at execution; a missing planned file
is not evidence of a pass. No owner/private corpus, remote transport, or live external-vendor call
is implied by any fixture in this plan.

## Sequencing (load-bearing)

- **M1, M2, M3 → M4.** M4 reads the taxonomy (M1), the re-attestation outcome (M2), and the seam
  test results (M3) to write the DG-6 report and tick epic ACs; it also writes to child-plan
  frontmatter M1 may have touched. Running it first would report on work that doesn't exist yet.
- **No order asserted among M1/M2/M3.** They touch disjoint file sets (new taxonomy docs; one
  Knowledge MCP report.json; new test files) and have no data dependency on one another —
  dispatch all three as one parallel wave.
- **Inside M3**, no order is asserted between S-1..S-7 individually; S-7 (full chain) is easiest to
  author last since it composes fixtures the other six tasks already built, but nothing blocks
  starting it in parallel.

## Deferred Items & In-Flight Findings Policy

No new deferred items are introduced by this plan — Wave 5 closes the initiative's existing
deferred tracks (NotebookLM refresh, browser capture extension, Knowledge MCP remote profile),
it does not open new ones. `deferred_items_spec_refs` stays empty unless M3 discovers a genuine
missing seam per Named Risks, in which case the discovered gap gets a shaping spec and this field
is populated retroactively.

The findings ledger is live at `.claude/findings/wave5-integration-qualification-findings.md`
(`findings_doc_ref`), written directly by reviewers — no source, no tests, no round-trip through
the orchestrator context (same convention as the C5 plan).

## Reviewer Gates and Execution Handoff

- `task-completion-validator` reviews M1, M2, M3, and M4 at each milestone's exit against the
  exact current tree.
- **Security lens on M3** — S-5/S-6 cross an authorization boundary (Knowledge MCP read →
  Operator MCP mutation; operator audit → provenance receipt). `gate_lens_reason: authz-boundary`.
- **Karen on M3** — `context_class: C4` triggers a per-milestone Karen pass on M3 specifically
  (the highest-risk milestone), independent of the feature-end pass.
- **Karen on M4, final tree only** — the tier-3 feature-end pass, covering the fully merged
  M1+M2+M3+M4 result. A material fix after this invalidates the prior approval.
- Fresh-context verifiers, continued implementer sessions: M2's reviewer and M3's security/karen
  lenses must not inherit the implementing session's context — inherited-context validators
  rubber-stamp (lesson carried from the C5 plan's P1 retro).
- The integration owner serializes writes to the shared files listed in `wave_plan.serialization_barriers`
  above (CHANGELOG, epic PRD, meta-plan, 5 child implementation plans).

### Execution handoff

Provider and model are **dispatch-time** decisions resolved by `delegation-router` from
`routing_constraints` in frontmatter — this handoff deliberately names no orchestrator model.

> Execute: `/dev:execute-plan docs/project_plans/implementation_plans/enhancements/wave5-integration-qualification-v1.md`

Before dispatch, the operator should know:

1. **MUST-stay-claude-primary**: M2's independent re-attestation, and M3's S-5/S-6 governance-
   boundary assertions (Codex offload is unavailable for this initiative's governance lenses —
   see the C5 plan's Field Notes; do not re-attempt).
2. **No new production code is authorized by this plan** — if M3 discovers a genuinely missing
   seam (not just missing coverage), stop that task and return to planning per Stop Conditions
   below; do not patch around it to make a test pass.
3. `required_artifacts` resolved against the SkillMeat catalog on 2026-07-31 — all `available`,
   no `batch_0` provisioning task needed. Re-resolve if the catalog has moved.
4. M4 must run after M1/M2/M3 complete — do not dispatch it as part of the first wave.

## Stop Conditions (§11)

Halt this plan and return to planning — do not patch around any of the following:

- A child needs a **new evidence authority** to make a seam claim credible (M3 discovery).
- An **import loses its receipt or locator** anywhere in the S-1/S-2/S-7 chain.
- **Catalog behavior is not explainable** when tracing S-2/S-3.
- **Read-only access requires mutation** to satisfy S-3/S-4 (Knowledge MCP staying read-only is
  load-bearing across the whole initiative).
- **Operator access bypasses governance** when tracing S-5/S-6 — this is the single most likely
  place a real defect would surface, given these are the two seams that were previously
  completely untested.
- **Remote resources require filesystem identifiers** anywhere touched by M1's taxonomy work.
- **A shaping spec is treated as executable** — the three deferred design specs (NotebookLM,
  browser capture, Knowledge MCP remote profile) stay `maturity: shaping`; M1/M4 record their
  status, they do not promote them.
- **Reviewer evidence names a different tree** than the one under review — any M2 or M3 gate whose
  approval references a tree SHA other than the exact candidate is void and must re-run.

If a stop condition fires, halt the affected milestone, write the finding to
`.claude/findings/wave5-integration-qualification-findings.md`, and escalate to the operator —
resuming execution on other milestones is fine; the triggering milestone waits for a planning
decision.
