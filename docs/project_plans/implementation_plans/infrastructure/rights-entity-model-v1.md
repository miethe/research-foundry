---
title: "Implementation Plan: Rights & Evidence-Item Entity Model"
schema_version: 2
doc_type: implementation_plan
it_schema: 1
status: draft
created: 2026-07-21
updated: 2026-07-21
feature_slug: "rights-entity-model"
feature_version: "v1"
tier: 3
prd_ref: docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md
plan_ref: null
scope: "Port the v1.0 pediatric-anemia-site rights substrate into RF's own schemas/*.schema.yaml with the ten §9 adjudications applied, then layer a rights_summary mirror (C1), evidence_item_type/judgment_basis taxonomy (C2), derived_synthesis provenance (C3), and capture-time emission + substitutability search (C4) — all fail-closed by construction, with a governance gate proving no agent path reaches CLEARED_*/counsel_approved/attested."
effort_estimate: "53 pts (bottom-up reconciled; see Estimation Sanity Check — decisions block anchored 41, PRD estimated 45-55)"
architecture_summary: "Schema-first: 5 new RF-canonical schemas + 2 extended existing schemas (source_card, source_assertion), one new service (rights_validation.py), one new governance.py guard rule, one new verification.py release-gate check, one new rf rights CLI group. No new tables/services outside RF's existing file-backed control-plane pattern."
related_documents:
  - .claude/worknotes/rights-entity-model/decisions-block.md
  - /Users/miethe/dev/homelab/development/pediatric-anemia-site/docs/project_plans/research/research-foundry-rights-entity-model-handoff-v1.md
  - /Users/miethe/dev/homelab/development/pediatric-anemia-site/docs/project_plans/research/research_foundry_rights_governance_spec_v1.0/Research_Foundry_Source_Reuse_and_Rights_Governance_Spec_v1.0.md
  - docs/project_plans/design-specs/reusable-assertion-ledger-public-rights-promotion.md
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
references:
  user_docs: []
  context: []
  specs:
    - docs/project_plans/design-specs/reusable-assertion-ledger-public-rights-promotion.md
  related_prds: []
spike_ref: null
adr_refs: []
deferred_items_spec_refs: []
findings_doc_ref: null
charter_ref: null
changelog_ref: null
changelog_required: true
test_plan_ref: null
plan_structure: independent
progress_init: auto
owner: null
contributors: []
priority: high
risk_level: medium
category: "product-planning"
tags: [rights, governance, evidence-model, rf, infrastructure, schema, implementation-plan]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - schemas/rights_record.schema.yaml
  - schemas/rights_extension.schema.yaml
  - schemas/content_reuse_assessment.schema.yaml
  - schemas/permission_record.schema.yaml
  - schemas/rights_failure.schema.yaml
  - schemas/source_assertion.schema.yaml
  - schemas/source_card.schema.yaml
  - src/research_foundry/schemas.py
  - src/research_foundry/services/source_cards.py
  - src/research_foundry/services/capture.py
  - src/research_foundry/services/governance.py
  - src/research_foundry/services/verification.py
  - src/research_foundry/services/rights_validation.py
  - src/research_foundry/cli_commands.py
  - docs/dev/architecture/adr-rights-entity-model.md
  - tests/test_schema_validation.py
planning_maturity: in_progress
open_questions:
  - q: "OQ-RF-5: Does RF own rights-terms surveillance as a service?"
    owner: rf
    status: "record-the-debt — schema carries next_review_at; DOC-006 design spec authored in P6; execution loop not built"
  - q: "OQ-RF-6: Is there an RF rights-owner/counsel role to gate CLEARED_*/counsel_approved writes?"
    owner: rf
    status: "record-the-debt — no role exists upstream; DOC-006 design spec authored in P6; shipped human-only-by-exclusion"
  - q: "OQ-3 (decisions block): Should a runtime resolution API replace the mirror?"
    owner: rf
    status: "deferred to DOC-006 design spec in P6; mirror is MVP for this plan"
  - q: "OQ-6 (decisions block, resolved by this plan): Does the release-gate rule live in governance.py or verification.py?"
    owner: implementation-planner
    status: "resolved — governance.py owns the judgment_basis:unassessed predicate (P5-3); verification.py calls it at verify time"
decisions:
  - {decision: "Port v1.0 rights substrate into RF schemas/*.yaml as a Phase 0 prerequisite before any capability work", rationale: "C1 rights_summary mirrors rights_record, which does not exist in RF today", status: locked}
  - {decision: "Denormalized entity-level rights_summary mirror (mirror_is_authoritative const false), not a runtime resolution API", rationale: "Files-canonical + no-service-on-recall-path constraint; a run must be readable offline", status: locked}
  - {decision: "RF authors its own canonical rights ADR; does not edit the pediatric-repo v1.0 spec", rationale: "Repo boundaries — canonical model assigned to RF", status: locked}
  - {decision: "evidence_item_type + judgment_basis live in extensions.evidence_taxonomy, a sibling block, not inside rights_extension", rationale: "§9.1 — rights and evidence-quality are independent axes", status: locked}
  - {decision: "CLEARED_*/counsel_approved/attestation.status=attested are human-only, fail-closed, proven by negative tests over BOTH write paths in BOTH P3 and P5", rationale: "§9.10 flagged one of two write paths unguarded in the baseline; Mode-D-adjacent boundary", status: locked}
  - {decision: "Record-the-debt for surveillance execution (OQ-RF-5) and counsel/rights-owner role (OQ-RF-6) via DOC-006 design specs", rationale: "Ship the schema field that records the debt; name the gap rather than build the loop/role now", status: locked}
  - {decision: "governance.py owns the judgment_basis release-gate predicate; verification.py calls it at verify time", rationale: "Resolves decisions-block OQ-6 — gate is policy (governance), fires at verify-time (verification)", status: accepted}
  - {decision: "Bottom-up estimate reconciled to 53 pts (up from the decisions block's 41-pt anchor, within the PRD's 45-55 pt range)", rationale: "H3/H6 heuristics under-counted P0's 6-adjudication schema-diff work and P3/P5's dual mandatory negative-test tasks in the original decisions-block anchor; see Estimation Sanity Check", status: accepted}
success_metrics:
  - "100% of newly ingested source_card and source_assertion instances carry a non-null rights_summary at review_status=agent_triage_only within the same capture pass (no backfill sweep)"
  - "Zero agent-writable code paths can produce CLEARED_* / counsel_approved / attestation.status=attested — proven by negative tests over both enum write paths (P3 + P5)"
  - "rights-divergence validator run is byte-reproducible across two invocations with the same --as-of value and unchanged inputs"
  - "judgment_basis: unassessed blocks 100% of commercial-release gate evaluations and blocks 0% of internal-capture writes, in automated tests exercising both directions"
execution_mode: agent
agent_title: "Port + extend RF's rights and evidence-taxonomy entity model"
agent_summary: "Add rights_record/rights_extension/content_reuse_assessment/permission_record/rights_failure schemas with §9 adjudication fixes, then extend source_card/source_assertion with a rights_summary mirror, evidence_item_type/judgment_basis taxonomy, derived_synthesis provenance, and capture-time emission — all fail-closed, all human-only for CLEARED_* writes, proven by negative tests over both write paths."
wave_plan:
  serialization_barriers:
    - src/research_foundry/cli_commands.py
    - src/research_foundry/schemas.py
  phases:
    - id: P0
      depends_on: []
      isolation: shared
      parallelizable: false
      owner_skills: []
      files_affected:
        - schemas/rights_record.schema.yaml
        - schemas/rights_extension.schema.yaml
        - schemas/content_reuse_assessment.schema.yaml
        - schemas/permission_record.schema.yaml
        - schemas/rights_failure.schema.yaml
        - src/research_foundry/schemas.py
        - tests/test_schema_validation.py
    - id: P1
      depends_on: [P0]
      isolation: shared
      parallelizable: false
      owner_skills: []
      files_affected:
        - schemas/source_assertion.schema.yaml
    - id: P2
      depends_on: [P1]
      isolation: shared
      parallelizable: false
      owner_skills: []
      files_affected:
        - schemas/source_card.schema.yaml
        - schemas/source_assertion.schema.yaml
        - src/research_foundry/services/rights_validation.py
        - src/research_foundry/cli_commands.py
    - id: P3
      depends_on: [P2]
      isolation: shared
      parallelizable: false
      owner_skills: []
      files_affected:
        - schemas/source_assertion.schema.yaml
        - src/research_foundry/services/source_cards.py
    - id: P4
      depends_on: [P3]
      isolation: shared
      parallelizable: false
      owner_skills: []
      files_affected:
        - src/research_foundry/services/source_cards.py
        - src/research_foundry/services/capture.py
        - src/research_foundry/cli_commands.py
    - id: P5
      depends_on: [P3]
      isolation: shared
      parallelizable: true
      owner_skills: []
      files_affected:
        - src/research_foundry/services/governance.py
        - src/research_foundry/services/verification.py
        - docs/dev/architecture/adr-rights-entity-model.md
    - id: P6
      depends_on: [P4, P5]
      isolation: shared
      parallelizable: false
      owner_skills: []
      files_affected:
        - tests/test_schema_validation.py
        - CHANGELOG.md
        - docs/project_plans/design-specs/rights-runtime-resolution-api.md
        - docs/project_plans/design-specs/rights-surveillance-loop.md
        - docs/project_plans/design-specs/rights-counsel-workflow.md
  waves:
    - [P0]
    - [P1, P2, P3, P4]
    - [P5, P6]
---

# Implementation Plan: Rights & Evidence-Item Entity Model

**Plan ID**: `IMPL-2026-07-21-RIGHTS-ENTITY-MODEL`
**Date**: 2026-07-21
**Author**: Implementation planning session (Sonnet 5), Mode B — Contract Drafting
**Human Brief**: N/A — not created for this pass (feature qualifies at 53 pts / 7 phases; author `docs/project_plans/human-briefs/rights-entity-model.md` before execution begins if wave-coordination narrative is needed)
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md`
- **Decisions Block (binding)**: `.claude/worknotes/rights-entity-model/decisions-block.md`
- **ADR (authored in P5)**: `docs/dev/architecture/adr-rights-entity-model.md`

**Complexity**: Large (Tier 3)
**Total Estimated Effort**: **53 pts** (bottom-up reconciled — see Estimation Sanity Check)
**Target Timeline**: Mostly-serial critical path, ~7 sequential phases; P5 ADR-authoring may run alongside P4.

## Executive Summary

This plan ports the pediatric-anemia-site's v1.0 rights-governance schemas into Research Foundry's own `schemas/*.schema.yaml` registry as RF's canonical substrate (Phase 0), applying the ten §9 schema-conflict adjudications at the source rather than carrying them forward as debt. It then layers four capabilities in strict dependency order: an evidence-quality taxonomy independent of rights (P1, C2), a denormalized `rights_summary` mirror with a time-parameterized, non-wall-clock divergence validator (P2, C1), first-class `derived_synthesis` provenance with an agent-write ceiling on attestation (P3, C3), and capture-time rights emission with terms snapshotting and substitutability search (P4, C4). A governance gate (P5) closes the authorization boundary over **both** enum write paths named in §9.10 — split deliberately across P3 (the `synthesis.attestation.status` path) and P5 (the `rights_record.overall_status` / `content_reuse_assessment.decision.status` path) so neither phase alone can claim the boundary is proven — and authors RF's canonical rights ADR. Testing, fixture regeneration, and the three deferred-item design specs close the feature in P6.

**Key Milestones**:
- P0 exit: 5 substrate schemas register in `SchemaRegistry`; all ten §9 adjudications applied at the schema level.
- P3 milestone (**karen**): synthesis provenance ships with a passing negative test proving the agent-write ceiling on `attestation.status`.
- P4 milestone (**karen**): capture-time emission is fail-closed by construction; no separate backfill sweep required.
- P6 end-of-feature (**karen**): full test sweep green, ADR published, all deferred items have a DOC-006 spec.

## Implementation Strategy

### Architecture Sequence

This is a schema-and-service feature, not a full-stack (DB→API→UI) feature — RF has no database layer or UI in this domain. The sequence follows RF's own layering:

1. **Schema Substrate** (P0) — Draft 2020-12 JSON Schema authored as YAML, registered in `SchemaRegistry`.
2. **Evidence Taxonomy** (P1) — new schema fields on an existing entity (`source_assertion`), independent axis.
3. **Mirror + Validator** (P2) — new schema fields on two existing entities (`source_card`, `source_assertion`) + a new service module.
4. **Derived Synthesis** (P3) — conditional schema fields + a service-layer write-ceiling.
5. **Capture Emission** (P4) — hooks into existing capture services (`source_cards.py`, `capture.py`).
6. **Governance Gate + ADR** (P5) — a new `governance.py` rule + a new `verification.py` check + documentation synthesis.
7. **Testing / Docs / Finalization** (P6) — consistency/negative/determinism test sweep, fixture regen, CHANGELOG, deferred-item design specs.

### Parallel Work Opportunities

This plan is **mostly serial by design** — each phase's schema shape is the prior phase's direct dependency (P0's `rights_record` is what P2's mirror mirrors; P1's `evidence_item_type` enum member `derived_synthesis` is what P3's conditional schema keys off). The one genuine parallel slice: **P5's ADR-authoring task (P5-4) can start once P3 lands** (it needs the full §9 adjudication set and the P3 attestation-boundary decision, not P4's capture-emission implementation) and can run alongside P4's implementation work with a different owner (`documentation-writer` vs `python-backend-engineer`) and no file overlap.

### Critical Path

**P0 → P1 → P2 → P3 → P4 → P6**, with **P5 running alongside P4** (both depend on P3) rather than strictly after it. P6 depends on both P4 and P5 completing.

### High-Friction Surfaces (H7)

`src/research_foundry/cli_commands.py` is **2,755 lines** (`wc -l`, checked 2026-07-21) — exceeds the 2K-line H7 threshold. Every task touching it (P2-4, P4-5 — the `rf rights` CLI group) applies the **H7 ≥2× dispatch multiplier** and the anti-blow guardrail: do not read the whole file, use `grep -n` to locate the `assertion_app` pattern and insertion point, budget ≤40 tool uses, and STOP-and-report-partial if the budget is exhausted rather than pushing through. No other in-scope file exceeds 2K lines (`verification.py` at 1,398 lines is below threshold but is the second-largest surface in scope — worth a targeted-read discipline even though it doesn't trigger the multiplier).

### Phase Summary

| Phase | Title | Estimate | Target Subagent(s) | Model(s) | Notes |
|-------|-------|----------|--------------------|----------|-------|
| P0 | Rights Substrate | 8 pts | data-layer-expert, python-backend-engineer | sonnet (extended) | Ports 5 schemas; owns §9.2/9.3/9.4/9.5/9.6/9.7(shared)/9.8 adjudications |
| P1 | Evidence Taxonomy (C2) | 6 pts | data-layer-expert, python-backend-engineer | sonnet (adaptive) | Owns §9.1, OQ-RF-2 |
| P2 | Rights Summary Mirror + Validator (C1) | 9 pts | data-layer-expert (schema), python-backend-engineer (validator) | sonnet (extended) | H3 algorithmic flag: time-parameterized validator |
| P3 | Derived Synthesis (C3) | 7 pts | python-backend-engineer, data-layer-expert | sonnet (extended) | **karen** milestone; owns half of §9.10 (synthesis.attestation.status path) |
| P4 | Capture Emission + Substitutability (C4) | 9 pts | python-backend-engineer | sonnet (extended) | **karen** milestone; H3 flags: snapshot diff, substitute ranking |
| P5 | Governance Gate + Canonical ADR | 7 pts | python-backend-engineer (governance), documentation-writer (ADR) | sonnet (adaptive) | Owns other half of §9.10 (overall_status/decision.status path) + §9.7 shared |
| P6 | Testing / Docs / Fixtures / Finalization | 7 pts | python-backend-engineer, documentation-writer, changelog-generator | sonnet (adaptive) | **karen** end-of-feature; owns §9.9; 3× DOC-006 design specs |
| **Total** | — | **53 pts** | — | — | — |

**Reviewer gates**: `task-completion-validator` at end of P0, P1, P2, P5. **`karen`** at end of P3, end of P4, and end of P6 (feature close).

### Estimation Sanity Check

**Noun count (H1)**: 5 new schema entities in P0 (`rights_record`, `rights_extension`, `content_reuse_assessment`, `permission_record`, `rights_failure`) + 4 new schema objects attached to existing entities (`rights_summary` mirror ×2 attach points, `synthesis`, capture-time snapshot/substitutability blocks). These are not CRUD-with-RBAC web entities (RF has no DB/RBAC layer here) but are comparably substantial: full Draft 2020-12 documents with nested objects, conditionals, and valid/invalid instance builders. H1's ~2 pt/noun floor doesn't map cleanly to schema-only nouns; treated instead via H3/H6 below.

**Dual-impl multiplier (H2)**: N/A — RF is a single file-backed control plane, no local/enterprise split.

**Algorithmic flag (H3)**: 4 services/checks flagged:
- P2's `check_rights_divergence` (time-parameterized, no-wall-clock validator) — budgeted 3 pts of P2's 9.
- P3's attestation write-ceiling + negative test — budgeted 2 pts of P3's 7.
- P4's terms-snapshot content-addressing + re-snapshot diff — budgeted 3 pts of P4's 9.
- P4's substitutability search/ranking — budgeted 2 pts of P4's 9.
- P5's second negative-test task (the other §9.10 write path) — budgeted 2 pts of P5's 7.

Each carries an enumerable test-scenario list in its phase file (≥5 scenarios each); none required a SPIKE precursor — the algorithms are bounded (divergence check, sha256 diff, discovery record, enum-write negative assertion), matching the decisions block's SPIKE-waiver rationale.

**Bundle decomposition (H4)**:

| Capability Area | Independent Estimate | Notes |
|-----------------|----------------------|-------|
| Rights Substrate (Phase 0 prerequisite) | 8 pts | Gates all 4 capability areas below |
| C1 — rights_summary mirror + validator | 9 pts | H3-flagged validator |
| C2 — evidence_item_type / judgment_basis | 6 pts | Independent axis |
| C3 — derived_synthesis | 7 pts | Half of the §9.10 authorization boundary |
| C4 — capture emission + substitutability | 9 pts | 2× H3-flagged sub-services |
| Governance gate + ADR (cross-cutting, closes §9.10) | 7 pts | Other half of §9.10 boundary + doc synthesis |
| Testing / docs / finalization (cross-cutting) | 7 pts | Consistency tests + 3× DOC-006 specs |
| **Σ** | **53 pts** | **Floor for plan total** |

**Anchor (H5)**: `reusable-assertion-ledger-v1` (`docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md`) — actual cost **72 pts**, `risk_level: high`, Tier 3, multi-phase schema+service+API+UI rollout. This plan's surface (7 phases, 5 new schemas + 2 extended entities + 3 new service modules, no API/UI layer) is narrower than the anchor's (which included a full frontend reviewer UI and API layer). **Estimate delta vs anchor**: 53/72 ≈ **−26%**, within the ±30% band given this plan has strictly less surface (no UI, no new API router beyond one CLI group) — no further justification required by H5's threshold.

**Plumbing budget (H6)**: P6 (7 pts) plus P5's ADR-authoring task (2 pts of P5's 7) together total ~9 pts of doc/consistency-test plumbing against a P0–P4 core subtotal of 39 pts → **~23%**, above the 15–20% floor because this plan carries 3 mandatory DOC-006 design specs (a fixed cost not present in most plans) on top of the standard CHANGELOG/README/context-file line items.

**Huge-file touch (H7)**: `src/research_foundry/cli_commands.py` (2,755 lines) is in scope for P2-4 and P4-5 (the `rf rights` CLI group). Both tasks carry the ≥2× dispatch multiplier and are flagged in each phase file's task description with the anti-blow guardrail. No other in-scope file exceeds 2K lines.

**Bottom-up total**: **53 pts**
**Top-down intuition (PRD)**: 45–55 pts (PRD `effort_estimate`)
**Decisions-block anchor**: 41 pts
**Locked estimate**: **53 pts**

**Reconciliation note**: The decisions block's 41-pt anchor under-counted two things the bottom-up pass above corrects: (1) P0's schema-port work was anchored to a prior multi-schema *landing* feature without separately costing the **6 §9 adjudications P0 owns** (§9.2, §9.3/9.4, §9.5, §9.6, §9.7-shared, §9.8), each requiring a careful cross-schema diff-and-fix, not just a structural port; and (2) the binding requirement that **P3 and P5 each carry an independent, non-duplicate negative-test task** (closing *different* halves of the §9.10 write-path gap) was present in the decisions block's phase scope but not separately budgeted as two distinct 2-pt algorithmic-flag line items. Correcting both lands at 53 pts — inside the PRD's own 45–55 pt top-down range and a smaller, justified delta (+29%, just under the 30% flag) from the decisions-block anchor, not a re-litigation of phase boundaries or agent routing (both unchanged from the decisions block).

## Deferred Items & In-Flight Findings Policy

### Deferred Items Triage Table

| Item ID | Category | Reason Deferred | Trigger for Promotion | Target Spec Path |
|---------|----------|------------------|------------------------|-------------------|
| DI-RIGHTS-1 | research-needed | Runtime rights-resolution API (OQ-3/OQ-RF-3 alternative to the mirror) — mirror chosen for v1; a fast resolution API is a larger, separate infra investment | A consumer needs sub-request-latency rights resolution at scale the mirror can't provide | `docs/project_plans/design-specs/rights-runtime-resolution-api.md` |
| DI-RIGHTS-2 | scope-cut | Terms-snapshot external hosting beyond the RF run directory (OQ-RF-4) — resolved to hash+artifact-in-run-dir only | A consumer needs to fetch terms snapshots without RF run access | Covered in ADR (P5); no separate spec — hosting is a storage/ops decision, not a design question |
| DI-RIGHTS-3 | backlog | Rights-terms surveillance execution loop (OQ-RF-5) — schema ships `next_review_at` but it is decorative until a scheduler exists | A second consumer needs proactive re-review notifications | `docs/project_plans/design-specs/rights-surveillance-loop.md` |
| DI-RIGHTS-4 | backlog | Formal rights-owner/counsel role and attestation workflow (OQ-RF-6) — no such role exists anywhere upstream today | A human reviewer workflow needs a first-class role/permission model | `docs/project_plans/design-specs/rights-counsel-workflow.md` |
| DI-RIGHTS-5 | dependency-blocked | Cross-file `$ref`/shared `$defs` support in `SchemaRegistry` (YAGNI for v1) — duplicated-enum + P6 consistency test closes the drift risk without new schema-loading infra | `SchemaRegistry` gains a second consumer needing cross-file `$ref` for an unrelated reason | N/A — closed by P6-1 consistency test; no spec warranted |
| DI-RIGHTS-6 | scope-cut | §9.9 example-fixture correction (role-string-in-reviewer-field defect) — moot for RF; RF does not port the pediatric-repo's vendored JSON examples | N/A — will never trigger for RF | N/A — documented in P6-5; no spec warranted |

**DOC-006 tasks** (P6-8a/b/c) author design specs for DI-RIGHTS-1, DI-RIGHTS-3, and DI-RIGHTS-4 — the three items with a real future trigger. DI-RIGHTS-2, -5, -6 are marked N/A with rationale (documented in the ADR or the P6-1/P6-5 tasks) per the "OR documented as N/A" exit clause.

### In-Flight Findings

Not pre-created. If a load-bearing finding surfaces during execution (e.g., a §9 adjudication proves unimplementable as adjudicated), create `.claude/findings/rights-entity-model-findings.md`, set `findings_doc_ref` in this plan's frontmatter, and add a DOC-006 row for it if it changes scope.

### Quality Gate

P6 cannot be sealed until all three DOC-006 design specs exist and their paths are appended to `deferred_items_spec_refs`, and DI-RIGHTS-2/-5/-6 remain documented N/A with rationale (already satisfied above — no further action needed for those three).

## Phase Breakdown

Full task tables, acceptance criteria, and quality gates live in the phase files below (parent plan stays under the 800-line budget):

| Phases | File | Covers |
|--------|------|--------|
| P0–P2 | [phase-0-2-schema.md](./rights-entity-model-v1/phase-0-2-schema.md) | Rights Substrate, Evidence Taxonomy, Rights Summary Mirror + Validator |
| P3–P4 | [phase-3-4-capture.md](./rights-entity-model-v1/phase-3-4-capture.md) | Derived Synthesis, Capture Emission + Substitutability |
| P5–P6 | [phase-5-6-governance-finalize.md](./rights-entity-model-v1/phase-5-6-governance-finalize.md) | Governance Gate + Canonical ADR, Testing / Docs / Fixtures / Finalization |

**Column conventions** (apply to every task table in the phase files):
- `Estimate` — story points. Never conflate with `Effort`.
- `Model` — all tasks in this plan are `sonnet` (haiku agents hard-error in this environment; override any haiku default, per decisions-block Model Routing Notes).
- `Effort` — `extended` for P0/P2/P3/P4 algorithmic/correctness-critical tasks; `adaptive` elsewhere (P1, P5, P6), per the binding constraint in this plan's authoring brief.

## Risk Mitigation

Full risk detail (severity, rationale, mitigation) is in the decisions block §3; summarized here:

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-------------|
| Fail-closed authorization boundary leaks (agent sets a cleared value) | Critical | Medium | Two independent negative-test tasks (P3-4, P5-2) cover both §9.10 write paths; **karen** milestone at P3 |
| Substrate port drifts from the verified v1.0 schemas | High | Medium | P0 ports field-by-field with the §9 adjudication table as the ONLY intended deltas; ADR (P5-4) records every deviation |
| Validator reads wall-clock time → non-reproducible runs | Critical | Low | `--as-of` is a hard requirement (P2-3); reproducibility test + monkeypatch guard (P2-3, P6-4) |
| Backfill migration breaks existing runs | Medium | Medium | Backfill emits all-`unknown` summaries (fail-closed = valid by construction); P2-5 exit gate runs the existing corpus through the validator |
| `cli_commands.py` (2,755 lines) drives 2×+ dispatch cost on `rf rights` CLI tasks | Medium | Medium | H7 multiplier applied to P2-4/P4-5; anti-blow guardrail (grep-only navigation, ≤40 tool uses) mandated |

## Resource Requirements

RF has no frontend/UI layer in scope for this feature. All work routes to `data-layer-expert` (schema authoring) and `python-backend-engineer` (services, governance, CLI), with `documentation-writer` for the ADR and `changelog-generator` for the CHANGELOG entry. No external models required — no image generation, web research, or UI wireframing in scope.

## Success Metrics

See frontmatter `success_metrics` (mirrors PRD §4 Success Metrics table verbatim — measurement methods are in the PRD).

## Wrap-Up: Feature Guide & PR

Triggered automatically after P6's quality gates pass (karen end-of-feature sign-off). Delegate to `documentation-writer` (sonnet — override haiku default) to create `.claude/worknotes/rights-entity-model/feature-guide.md` per the standard template (What Was Built / Architecture Overview / How to Test / Test Coverage Summary / Known Limitations), then open the PR. See `.claude/skills/planning/templates/implementation-plan-template.md` → "Wrap-Up" for the full template and PR body format.

---

**Progress Tracking**: `.claude/progress/rights-entity-model/all-phases-progress.md` (created via artifact-tracking skill before execution begins)

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-07-21
