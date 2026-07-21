---
type: context
schema_version: 2
doc_type: context
prd: "rights-entity-model"
feature_slug: rights-entity-model
created: 2026-07-21
updated: 2026-07-21
---

# Rights & Evidence-Item Entity Model — PRD-Level Context

**Goal (one-liner)**: Port RF's own canonical rights-governance substrate (currently absent from
this repo) and layer a fail-closed `rights_summary` mirror, evidence-quality taxonomy, derived
synthesis provenance, and capture-time emission on top of it — closing the two-write-path
authorization gap (§9.10) with independent negative tests, and proving every `CLEARED_*` /
`counsel_approved` / `attested` value is human-only.

## Critical Scope Note

**Phase 0 ports the v1.0 rights substrate because it is absent from the RF product repo.** The
five substrate schemas (`rights_record`, `rights_extension`, `content_reuse_assessment`,
`permission_record`, `rights_failure`) and the ten §9 schema-conflict adjudications currently
exist only as spec artifacts in the **pediatric-anemia-site** repo
(`docs/project_plans/research/research_foundry_rights_governance_spec_v1.0/` and the
`research-foundry-rights-entity-model-handoff-v1.md` handoff doc there). This plan ports the
schema *structure* into RF's own `schemas/*.schema.yaml` as RF-canonical — it does not edit the
pediatric-repo's v1.0 spec, and it does not port that repo's vendored JSON example fixtures (see
DI-RIGHTS-6 / §9.9 — moot for RF, closed in P6-5). Every phase after P0 depends on this port
existing; nothing in P1–P6 has a fallback if P0 is skipped or partial.

## 7-Phase Map

| Phase | Title | Capability | Reviewer Gate |
|-------|-------|------------|----------------|
| P0 | Rights Substrate | Port 5 schemas; apply all 10 §9 adjudications | task-completion-validator |
| P1 | Evidence Taxonomy | C2 — `evidence_item_type` / `judgment_basis` (independent axis from rights) | task-completion-validator |
| P2 | `rights_summary` Mirror + Validator | C1 — denormalized mirror + time-parameterized, non-wall-clock divergence validator | task-completion-validator |
| P3 | Derived Synthesis | C3 — `derived_synthesis` provenance; closes §9.10's `synthesis.attestation.status` write path | **karen** |
| P4 | Capture Emission + Substitutability | C4 — capture-time `rights_summary` emission, terms snapshotting, substitutability search | **karen** |
| P5 | Governance Gate + Canonical ADR | Closes §9.10's other write path (`overall_status`/`decision.status`/`clearance_status`); authors RF's rights ADR | task-completion-validator |
| P6 | Testing / Docs / Fixtures / Finalization | Consistency/negative/release-gate/determinism test sweeps; fixture regen; 3× DOC-006 design specs; CHANGELOG/docs | **karen** (end-of-feature) |

**Dependency shape**: P0→P1→P2→P3→P4→P6 is the critical path. **P5 depends on P3, not P4**, and
may run alongside P4 (different owner-file set — `governance.py`/`verification.py`/the ADR vs.
`source_cards.py`/`capture.py`/`cli_commands.py`; no file overlap). P6 depends on **both** P4 and
P5 completing. This is the plan's one deliberate parallel slice.

**§9.10 boundary — do not treat either negative test alone as sufficient**: P3-4 proves the agent
path to `synthesis.attestation.status=attested` is unreachable; P5-2 proves the agent path to
`rights_record.overall_status` / `content_reuse_assessment.decision.status` /
`rights_extension.clearance_status` is unreachable. The authorization boundary is only fully
closed once **both** pass — they are independent test suites over different fields/write-paths,
never collapse one into the other. P6-2 formalizes this as a combined CI cross-check.

## Progress Files

`.claude/progress/rights-entity-model/phase-{0,1,2,3,4,5,6}-progress.md` — one per phase, per
`.claude/specs/doc-policy-spec.md`. Phase 0–4 authored in a prior session; Phase 5–6 authored in
this session after a mid-run API error interrupted the original authoring pass.

## Pointers

- **PRD**: `docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md`
- **Implementation Plan (parent)**: `docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md`
- **Phase files**: `.../rights-entity-model-v1/phase-0-2-schema.md`, `phase-3-4-capture.md`, `phase-5-6-governance-finalize.md`
- **Decisions Block (binding)**: `.claude/worknotes/rights-entity-model/decisions-block.md` — do not edit; contains the locked §9 adjudications, risk table, and Model Routing Notes (haiku hard-errors in this environment — always override to sonnet).
- **Human Brief**: `docs/project_plans/human-briefs/rights-entity-model.md`
- **Canonical ADR (authored in P5-4)**: `docs/dev/architecture/adr-rights-entity-model.md` (does not exist yet — created by this feature)
- **Source spec artifacts (pediatric-anemia-site repo, read-only reference)**:
  `/Users/miethe/dev/homelab/development/pediatric-anemia-site/docs/project_plans/research/research-foundry-rights-entity-model-handoff-v1.md`
  and `.../research_foundry_rights_governance_spec_v1.0/Research_Foundry_Source_Reuse_and_Rights_Governance_Spec_v1.0.md`

## Estimate & Model Routing

53 pts bottom-up reconciled (decisions-block anchored 41; PRD range 45–55). All tasks route to
`sonnet` — `haiku` hard-errors in this environment, including for agents that default to it
(`changelog-generator`, `documentation-writer`); always pass `model="sonnet"` explicitly.
