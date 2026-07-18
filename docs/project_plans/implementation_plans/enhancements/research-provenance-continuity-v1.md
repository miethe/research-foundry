---
title: "Implementation Plan: Research Provenance Continuity"
schema_version: 2
doc_type: implementation_plan
status: draft
created: 2026-07-18
updated: 2026-07-18
feature_slug: research-provenance-continuity
feature_version: v1
tier: 3
prd_ref: docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
plan_ref: null
human_brief_ref: docs/project_plans/human-briefs/research-provenance-continuity.md
scope: "Add canonical origin and planned/search-run envelopes, discoverable search-only activity, immutable activity/selection/report-use receipts, optional AOS references, typed inference/canonical-claim materialization, governed projections, and lifecycle reconciliation without replacing RAL, activation, RFUP, or retrieval-selection behavior."
effort_estimate: "40 pts bottom-up"
architecture_summary: "File-canonical origin/run/activity/use/inference/canonical-claim records; rebuildable facets and read projections; exact-tree P1 serialization gate; existing impact manifest/receipt integration."
related_documents:
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/human-briefs/research-provenance-continuity.md
  - .codex/worknotes/research-provenance-continuity/decisions-block.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
  - docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1.md
  - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
references:
  user_docs: []
  context: []
  specs:
    - .agents/skills/planning/references/ac-schema.md
    - .agents/skills/planning/references/deferred-items-and-findings.md
    - .claude/specs/changelog-spec.md
    - schemas/provenance_origin.schema.yaml
    - schemas/research_run_envelope.schema.yaml
    - schemas/search_activity_receipt.schema.yaml
    - schemas/source_assertion.schema.yaml
    - schemas/inference_record.schema.yaml
    - schemas/canonical_claim.schema.yaml
    - schemas/assertion_lifecycle_event.schema.yaml
  related_prds:
    - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
    - docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
    - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
spike_ref: null
adr_refs: []
deferred_items_spec_refs: []
findings_doc_ref: null
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
tags: [implementation, planning, provenance, assertion-ledger, report-lineage, inference, lifecycle]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - schemas/provenance_origin.schema.yaml
  - schemas/research_run_envelope.schema.yaml
  - schemas/search_activity_receipt.schema.yaml
  - schemas/search_request.schema.yaml
  - schemas/search_run.schema.yaml
  - schemas/report_assertion_use.schema.yaml
  - schemas/inference_record.schema.yaml
  - schemas/canonical_claim.schema.yaml
  - src/research_foundry/services/provenance_envelope.py
  - src/research_foundry/services/research_run_discovery.py
  - src/research_foundry/services/assertion_materialization.py
  - src/research_foundry/services/assertion_catalog.py
  - src/research_foundry/services/assertion_impact.py
  - src/research_foundry/services/synthesis.py
  - src/research_foundry/services/verification.py
  - src/research_foundry/services/export_service.py
  - src/research_foundry/services/run_launch.py
  - src/research_foundry/api/routers/assertions.py
  - src/research_foundry/api/openapi.json
open_questions:
  - id: RPC-OQ-1
    status: open
    question: "Bind report use to report digest, report revision ID, or both?"
  - id: RPC-OQ-2
    status: open
    question: "Prepare inference/report-use records before verification and publish after pass, or create only after verification?"
  - id: RPC-OQ-3
    status: open
    question: "Which legacy search_request/search_run fields remain compatibility aliases after the canonical nested envelopes freeze?"
wave_plan:
  serialization_barriers:
    - schemas/provenance_origin.schema.yaml
    - schemas/research_run_envelope.schema.yaml
    - schemas/search_activity_receipt.schema.yaml
    - schemas/inference_record.schema.yaml
    - schemas/canonical_claim.schema.yaml
    - src/research_foundry/services/assertion_catalog.py
    - src/research_foundry/services/assertion_impact.py
    - src/research_foundry/api/openapi.json
  phases:
    - id: P1
      depends_on: []
      isolation: shared
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - schemas/provenance_origin.schema.yaml
        - schemas/research_run_envelope.schema.yaml
        - schemas/search_activity_receipt.schema.yaml
        - schemas/search_request.schema.yaml
        - schemas/search_run.schema.yaml
        - schemas/inference_record.schema.yaml
        - schemas/canonical_claim.schema.yaml
    - id: P2
      depends_on: [RPC-1.G]
      isolation: worktree
      parallelizable: true
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - src/research_foundry/services/provenance_envelope.py
        - src/research_foundry/services/research_run_discovery.py
        - src/research_foundry/services/run_launch.py
    - id: P3
      depends_on: [RPC-1.G]
      isolation: worktree
      parallelizable: true
      owner_skills: []
      model: sonnet
      effort: adaptive
      files_affected:
        - schemas/report_assertion_use.schema.yaml
        - src/research_foundry/services/assertion_report_use.py
        - src/research_foundry/services/synthesis.py
        - src/research_foundry/services/verification.py
    - id: P4
      depends_on: [RPC-1.G]
      isolation: worktree
      parallelizable: true
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - schemas/inference_record.schema.yaml
        - schemas/canonical_claim.schema.yaml
        - src/research_foundry/services/assertion_inference.py
        - src/research_foundry/services/canonical_claim_materialization.py
        - src/research_foundry/services/assertion_materialization.py
    - id: P5
      depends_on: [P2, P3, P4]
      isolation: worktree
      parallelizable: true
      owner_skills: []
      model: sonnet
      effort: adaptive
      files_affected:
        - src/research_foundry/services/assertion_catalog.py
        - src/research_foundry/services/research_run_discovery.py
        - src/research_foundry/services/export_service.py
        - src/research_foundry/api/routers/assertions.py
        - src/research_foundry/api/openapi.json
    - id: P6
      depends_on: [P3, P4]
      isolation: worktree
      parallelizable: true
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - src/research_foundry/services/assertion_impact.py
    - id: P7
      depends_on: [P5, P6]
      isolation: shared
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: adaptive
      files_affected:
        - tests/unit/test_assertion_report_use.py
        - tests/unit/test_assertion_inference.py
        - tests/unit/test_provenance_envelope.py
        - tests/integration/test_research_run_discovery.py
        - tests/unit/test_assertion_catalog.py
        - tests/integration/test_assertions_api.py
        - tests/integration/test_assertion_reuse.py
        - docs/dev/guides/research-provenance-continuity.md
        - CHANGELOG.md
  waves:
    - [P1]
    - [P2, P3, P4]
    - [P5, P6]
    - [P7]
---

# Implementation Plan: Research Provenance Continuity

**Plan ID**: `IMPL-2026-07-18-RESEARCH-PROVENANCE-CONTINUITY`
**Date**: 2026-07-18
**Author**: Codex planning worker under delegated orchestration
**Human Brief**: `docs/project_plans/human-briefs/research-provenance-continuity.md`
**Decisions Block**: `.codex/worknotes/research-provenance-continuity/decisions-block.md`
**Complexity**: Large / Tier 3
**Total Estimated Effort**: 40 points

## Executive Summary

The implementation adds the canonical provenance layer around existing RAL
records: structured origin and planned/search-run envelopes, discoverable
search-only activity, immutable scope/selection receipts, optional AOS refs,
verified report uses, and typed inference/canonical-claim records. Three writer
lanes open only after Karen approves the exact Phase 1 contract tree; read
projections and lifecycle reconciliation then consume those records before one
integrated hardening/review phase.

The plan intentionally avoids registry redesign, source-assertion backfill, retrieval selection, vector/graph work, RFUP requirements, and owner/private activation. Repository-local success proves contracts and deterministic behavior only.

## Implementation Strategy

### Architecture Sequence

1. Freeze canonical origin, run/activity, receipt, optional AOS-ref, materialization, denial, and legacy contracts; obtain exact-tree validator and Karen approval.
2. Write origin/run/search-only activity and immutable selection receipts through one provenance service.
3. Write report-use, inference, and optional canonical-claim records through separate immutable services.
4. Treat successful canonical writes as the only authority for persistent reference updates; derive all facets/read models from those records.
5. Extend governed discovery/API/export and existing lifecycle manifests/receipts.
6. Validate adversarial integrity, compatibility, generated contracts, documentation, and exact-tree gates.

### Critical Path

`P1 exact-tree gate → (P2 + P3 + P4) → (P5 + P6) → P7`

### Phase Summary

| Phase | Title | Estimate | Target Subagent(s) | Model | Effort | Notes |
|---|---|---:|---|---|---|---|
| P1 | Canonical Contract Freeze | 7 pts | backend-architect, api-designer | sonnet | extended | Hard serialization barrier; validator + Karen |
| P2 | Origin, Run, and Activity Materialization | 6 pts | python-backend-engineer, data-layer-expert | sonnet | extended | Search-only discoverability + facet rebuild |
| P3 | Report-Use Materialization | 5 pts | python-backend-engineer | sonnet | adaptive | Parallel after P1 gate |
| P4 | Inference and Canonical-Claim Materialization | 6 pts | python-backend-engineer, data-layer-expert | sonnet | extended | Typed, separate H3 paths |
| P5 | Projection and Read Contracts | 5 pts | python-backend-engineer, api-designer | sonnet | adaptive | Activity/catalog/API/export integration |
| P6 | Lifecycle Continuity | 5 pts | backend-architect, python-backend-engineer | sonnet | extended | Existing impact seam only |
| P7 | Hardening and Documentation | 6 pts | validation agents, documentation-writer, reviewers | sonnet/haiku/opus | adaptive/extended | Final exact-tree candidate |
| **Total** | — | **40 pts** | — | — | — | — |

> H1-H6 details live only in the linked Human Brief. The estimate is bottom-up; no measured actual-point ledger was available for H5, so comparable plan/commit anchors are labeled medium confidence.

## Deferred Items & In-Flight Findings Policy

### Deferred Items Triage

| Item ID | Category | Reason Deferred | Trigger for Promotion | Target Spec Path |
|---|---|---|---|---|
| RPC-DF-1 | research | Historical reports can lack exact persistent refs; synthetic IDs would weaken provenance | A deterministic mapping study demonstrates exact reconstruction | docs/project_plans/design-specs/research-provenance-historical-report-reconstruction.md |
| RPC-DF-2 | design | Report-to-report transclusion needs component/revision identity beyond v1 | A concrete transclusion use case enters an approved PRD | docs/project_plans/design-specs/research-provenance-report-transclusion.md |
| RPC-DF-3 | policy | Public provenance export requires rights-promotion policy | Public-rights approval and threat model accepted | docs/project_plans/design-specs/research-provenance-public-export.md |
| RPC-DF-4 | research | Graph/vector traversal is unnecessary for bounded lineage and can leak membership | Measured need plus separate threat model | docs/project_plans/design-specs/research-provenance-derived-graph.md |

P7 must author these four `maturity: idea` design specs and append their paths to `deferred_items_spec_refs`. No progress files are created by this planning package.

### In-Flight Findings

Keep `findings_doc_ref: null` until execution discovers a real plan/reality mismatch. On the first finding, create `.claude/findings/research-provenance-continuity-findings.md`, link it here, and promote load-bearing findings to design specs before P7 seals.

## Phase Breakdown

### Phase P1: Canonical Contract Freeze

**Dependencies**: RAL and assertion-ledger activation code present on the exact starting tree.
**Assigned Subagents**: backend-architect, api-designer
**Exit State**: `RPC-1.G` records task-completion-validator and Karen approval against the same exact contract tree. Every downstream package depends on that gate.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| RPC-1.1 | Origin authority contract | Freeze canonical origin identity/version, acquisition/import/capture/generation method, producer/tool, source kind, locator/digest, workspace/timestamps/parent refs, and rebuildable facet rules. | AC RPC-1 positive, legacy, tamper, cross-workspace, and facet-rebuild examples specified | 2 pts | backend-architect, api-designer | sonnet | extended | None |
| RPC-1.2 | Run/activity and receipt contract | Freeze planned/search-only activity kinds, discovery rules, query/purpose/provider/site/corpus/filter/time scope, candidate-set digest, selection/denial/degraded receipts, and optional AOS project/intent/knowledge refs. | AC RPC-2/7 schemas preserve search-only activity and never fabricate scope/AOS refs | 2 pts | backend-architect, api-designer | sonnet | extended | None |
| RPC-1.3 | Report-use contract | Define immutable report-use identity, report digest/revision binding, exact assertion/inference/canonical-claim refs, rights/workspace snapshot, and replay conflict rules. | AC RPC-3 examples validate; substitution fixture rejected | 1.5 pts | backend-architect | sonnet | extended | None |
| RPC-1.4 | Inference/canonical-claim contracts | Freeze separate eligibility, identity, support, atomicity, optional-canonicalization, lifecycle, and typed skip rules. | AC RPC-4 matrix forbids inference/source conflation and implicit semantic merge | 1 pt | backend-architect | sonnet | extended | None |
| RPC-1.5 | Compatibility and ownership review | Resolve legacy aliases, RFUP/RAL/activation boundaries, downstream dependencies, denial shape, and OQ-1..3 defaults. | Validator verdict references exact contract tree | 0.5 pt | task-completion-validator | sonnet | adaptive | RPC-1.1..1.4 |
| RPC-1.G | Tier-3 contract serialization gate | Review schemas, examples, ownership, threat boundaries, task/AC traceability, and exact tree. | task-completion-validator then Karen APPROVE the same exact tree; later material change invalidates both verdicts | gate | task-completion-validator, Karen | sonnet/opus | extended | RPC-1.5 |

### Phase P2: Origin, Run, and Activity Materialization

**Dependencies**: `RPC-1.G` approved. May run beside P3/P4 with isolated ownership.
**Ownership**: provenance envelope/discovery services, search/run propagation, origin/activity tests.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| RPC-2.1 | Canonical origin writer | Validate, atomically persist, and replay canonical origin envelopes; derive facets through one rebuild path. | Tamper/conflict fails closed; delete/rebuild parity proves facets non-authoritative | 2 pts | python-backend-engineer | sonnet | extended | RPC-1.G |
| RPC-2.2 | Planned/search-only activity writer | Persist planned and search-only envelopes and make both discoverable through governed list/fetch. | Search-only fixture remains discoverable with no planned run or fabricated identifier | 2 pts | python-backend-engineer | sonnet | extended | RPC-2.1 |
| RPC-2.3 | Scope and selection receipts | Persist exact query/purpose/provider/site/corpus/filter/time plus candidate digest and selection/denial/degraded/fallback receipt; propagate selected exact versions to launch/export. | Receipt round trip and denial matrix satisfy AC RPC-2 | 1 pt | data-layer-expert | sonnet | extended | RPC-2.2 |
| RPC-2.4 | Optional AOS refs | Propagate opaque project/intent/knowledge refs after workspace/policy validation without loading or copying AOS payloads. | AC RPC-7 present/absent/malformed/cross-workspace cases pass | 1 pt | python-backend-engineer | sonnet | adaptive | RPC-2.2 |
| RPC-2.G | Phase reviewer | Review exact origin/activity tree, focused tests, and discoverability behavior. | task-completion-validator APPROVE | gate | task-completion-validator | sonnet | adaptive | RPC-2.3, RPC-2.4 |

### Phase P3: Report-Use Materialization

**Dependencies**: `RPC-1.G` approved. May run beside P2/P4.
**Ownership**: report-use schema/service/tests and narrow synthesis/verification hooks.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| RPC-3.1 | Immutable report-use service | Prepare, validate, atomically publish, and replay exact report revision/evidence use records under workspace-scoped ledger storage. | Same input replays; digest/version/workspace mismatch fails closed | 2 pts | python-backend-engineer | sonnet | adaptive | RPC-1.G |
| RPC-3.2 | Verification finalization seam | Prepare from cited persistent refs and publish only on verified report revision; preserve report iteration before verification. | Failed verification creates no canonical use; passed verification is deterministic | 2 pts | python-backend-engineer | sonnet | adaptive | RPC-3.1 |
| RPC-3.3 | Report-use adversarial gate | Test mutable report substitution, cross-workspace ref, stale input, hidden rights, duplicate ref, legacy missing ref, partial write, and replay conflict. | AC RPC-3 evidence recorded | 1 pt | python-backend-engineer | sonnet | extended | RPC-3.2 |
| RPC-3.G | Phase reviewer | Review exact tree and focused results. | task-completion-validator APPROVE | gate | task-completion-validator | sonnet | adaptive | RPC-3.3 |

### Phase P4: Inference and Canonical-Claim Materialization

**Dependencies**: `RPC-1.G` approved. May run beside P2/P3.
**Ownership**: separate inference and canonical-claim services, schemas, claim-ref hooks, tests.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| RPC-4.1 | Resolve inference bases | Resolve run-local inference bases through exact persistent source-assertion refs; enforce one workspace and eligible lifecycle. | Exact, missing, mixed, stale, and cross-workspace cases deterministic | 2 pts | python-backend-engineer | sonnet | extended | RPC-1.G |
| RPC-4.2 | Durable inference writer | Canonicalize identity, validate, atomically write, then update `persistent_references.inference_id`; replay safely. | No partial record/ref pair; inference remains separate from source assertions | 2 pts | python-backend-engineer | sonnet | extended | RPC-4.1 |
| RPC-4.3 | Canonical-claim materializer | Publish an explicitly requested canonical-claim version from exact assertion/inference support refs through its own typed writer and reference. | No implicit merge; absent/ambiguous/conflicting support remains unmaterialized | 1 pt | python-backend-engineer | sonnet | extended | RPC-4.2 |
| RPC-4.4 | Materialization adversarial matrix | Test empty/unresolved/stale/mixed support, producer omission, implicit merge, substitution, partial write, and replay conflict. | AC RPC-4 evidence recorded | 1 pt | data-layer-expert | sonnet | adaptive | RPC-4.3 |
| RPC-4.G | Materialization milestone | Review typed separation, atomicity, and exact tree. | task-completion-validator and Karen APPROVE | gate | task-completion-validator, Karen | sonnet/opus | extended | RPC-4.4 |

### Phase P5: Projection and Read Contracts

**Dependencies**: P2, P3, and P4 approved and integrated.
**Integration Owner**: python-backend-engineer

| Task ID | Task | Description | Acceptance Criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| RPC-5.1 | Activity and lineage projections | Rebuild origin/run facets, search-only discovery, report uses, inference lineage, and canonical-claim lineage from canonical records after policy filtering. | Delete/rebuild produces identical authorized results | 2 pts | python-backend-engineer | sonnet | adaptive | RPC-2.G, RPC-3.G, RPC-4.G |
| RPC-5.2 | API/export propagation | Add governed optional activity/lineage shapes; regenerate OpenAPI/types; preserve legacy absence. | AC RPC-5 response and denial matrix passes | 1.5 pts | api-designer, python-backend-engineer | sonnet | adaptive | RPC-5.1 |
| RPC-5.3 | Search-only discovery seam | Exercise canonical activity → discovery service → router/export with no planned run and exact receipt. | List/fetch/export remain workspace isolated and complete | 1 pt | python-backend-engineer | sonnet | adaptive | RPC-5.2 |
| RPC-5.4 | End-to-end lineage seam | Exercise origin/activity → evidence versions → inference/canonical claim/report use → governed read. | Cross-owner propagation proved on one exact fixture | 0.5 pt | python-backend-engineer | sonnet | adaptive | RPC-5.3 |
| RPC-5.G | Phase reviewer | Review exact tree, generated files, and no-existence-leak behavior. | task-completion-validator APPROVE | gate | task-completion-validator | sonnet | adaptive | RPC-5.4 |

### Phase P6: Lifecycle Continuity

**Dependencies**: P3 and P4 approved and integrated; consumes canonical records only.
**Ownership**: `assertion_impact.py` and focused lifecycle tests.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| RPC-6.1 | Dependent enumeration | Read canonical inference/canonical-claim/report-use records and add exact actions without changing authoritative assertion-blocking order. | Affected/unaffected fixtures enumerate exactly | 2 pts | backend-architect | sonnet | extended | RPC-3.G, RPC-4.G |
| RPC-6.2 | Receipt/replay integration | Reuse checkpoint/resume and exact ordered identity rules for new actions; keep external writeback default denied. | Interruption resumes; malformed receipts fail closed | 1.5 pts | python-backend-engineer | sonnet | extended | RPC-6.1 |
| RPC-6.3 | Lifecycle seam | Invalidated assertion → stale inference/canonical claim/report revision → rebuilt projection; assert no cross-workspace data. | AC RPC-6 evidence recorded | 1 pt | python-backend-engineer | sonnet | adaptive | RPC-6.2 |
| RPC-6.4 | Lifecycle adversarial matrix | Test truncated/extra/duplicate/mismatched actions, unaffected siblings, repeated resume, and repair. | Exact manifest/receipt equality enforced | 0.5 pt | data-layer-expert | sonnet | adaptive | RPC-6.3 |
| RPC-6.G | Lifecycle milestone | Review exact lifecycle candidate. | task-completion-validator and Karen APPROVE | gate | task-completion-validator, Karen | sonnet/opus | extended | RPC-6.4 |

### Phase P7: Hardening and Documentation

**Dependencies**: P5 and P6 approved and integrated on one exact candidate tree.
**Assigned Subagents**: validation agents, documentation-writer, changelog-generator

| Task ID | Task | Description | Acceptance Criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| RPC-7.2 | Origin/facet gate | Run origin positive/legacy/tamper/cross-workspace and delete/rebuild fixtures. | Verifies AC RPC-1 | 0.5 pt | data-layer-expert | sonnet | adaptive | RPC-5.G |
| RPC-7.3 | Activity/receipt gate | Run planned/search-only, scope/filter/time, selection/denial/degraded, launch/export, and discoverability fixtures. | Verifies AC RPC-2 | 0.5 pt | python-backend-engineer | sonnet | extended | RPC-5.G |
| RPC-7.4 | Report-use gate | Run verified/unverified, legacy, substitution, rights, lifecycle, and replay fixtures. | Verifies AC RPC-3 | 0.5 pt | python-backend-engineer | sonnet | adaptive | RPC-5.G, RPC-6.G |
| RPC-7.5 | Inference/canonical-claim gate | Run eligible/unresolved/mixed/stale/cross-workspace/implicit-merge/partial-write fixtures. | Verifies AC RPC-4 | 0.75 pt | data-layer-expert | sonnet | extended | RPC-5.G, RPC-6.G |
| RPC-7.6 | Governed read gate | Run discovery/API/export/OpenAPI/type and no-existence-leak cases. | Verifies AC RPC-5 | 0.5 pt | api-designer | sonnet | adaptive | RPC-5.G |
| RPC-7.7 | Lifecycle replay gate | Run interruption and exact receipt-identity adversarial cases. | Verifies AC RPC-6 | 0.5 pt | backend-architect | sonnet | extended | RPC-6.G |
| RPC-7.8 | Optional AOS gate | Run absent/present/malformed/cross-workspace AOS-reference cases. | Verifies AC RPC-7 | 0.25 pt | task-completion-validator | sonnet | adaptive | RPC-5.G |
| RPC-7.9 | Regression gate | Run focused RAL/activation/search/launch/export suites and diff legacy response key sets. | Verifies AC RPC-8 | 0.5 pt | task-completion-validator | sonnet | adaptive | RPC-7.2..7.8 |
| RPC-7.10 | Docs and deferred specs | Write usage/dev guide, CHANGELOG entry, four deferred design specs, and crosslinks; reconcile findings truth. | Docs resolve and deferred refs populate | 1 pt | documentation-writer, changelog-generator | haiku | adaptive | RPC-7.9 |
| RPC-7.11 | Final evidence assembly | Map RPC-1..8 to exact commands/results and verify repository/private/release status labels. | One auditable exact-tree evidence set | 1 pt | task-completion-validator | sonnet | extended | RPC-7.10 |
| RPC-7.G | Final Tier 3 gate | Validate exact tree and evidence; issue formal verdict. | task-completion-validator then Karen APPROVE | gate | task-completion-validator, Karen | sonnet/opus | extended | RPC-7.11 |

## Structured Acceptance Criteria

#### AC RPC-1: Canonical origin and derived facets
- target_surfaces:
    - schemas/provenance_origin.schema.yaml
    - src/research_foundry/services/provenance_envelope.py
    - src/research_foundry/services/assertion_catalog.py
- propagation_contract: One canonical versioned envelope retains acquisition/import/capture/generation method, producer/tool, source kind, locator/digest, workspace, timestamps, and parent origin refs; facets derive only from it.
- resilience: Facet deletion/rebuild is identical; malformed/cross-workspace parent refs fail closed and legacy absence mints no origin identity.
- visual_evidence_required: false
- verified_by: [RPC-7.2]

#### AC RPC-2: Planned and search-only activity round trip
- target_surfaces:
    - schemas/research_run_envelope.schema.yaml
    - schemas/search_activity_receipt.schema.yaml
    - schemas/search_request.schema.yaml
    - schemas/search_run.schema.yaml
    - src/research_foundry/services/research_run_discovery.py
- propagation_contract: Each activity retains request/activity IDs, kind, workspace, parent/planned-run refs, query/purpose/provider/site/corpus/filter/time scope, candidate digest, selected evidence versions, and selection/denial/degraded receipt; search-only activity is listable and fetchable.
- resilience: Missing planned-run remains valid; denied/legacy records expose no hidden candidate values or fabricated IDs.
- visual_evidence_required: false
- verified_by: [RPC-7.3]

#### AC RPC-3: Report revision uses exact evidence versions
- target_surfaces:
    - src/research_foundry/services/synthesis.py
    - src/research_foundry/services/verification.py
    - src/research_foundry/services/assertion_catalog.py
- propagation_contract: Verification publishes immutable use records bound to report digest/revision and exact assertion/inference/canonical-claim versions; projection rebuild returns those revision IDs.
- resilience: Missing persistent refs remain legacy-unresolved and create no canonical use.
- visual_evidence_required: false
- verified_by: [RPC-7.4]

#### AC RPC-4: Inference and canonical claims are distinct and atomic
- target_surfaces:
    - schemas/inference_record.schema.yaml
    - schemas/canonical_claim.schema.yaml
    - src/research_foundry/services/assertion_materialization.py
    - src/research_foundry/services/verification.py
- propagation_contract: Eligible inference bases resolve to exact assertions before inference publication; an explicitly requested canonical claim separately binds exact assertion/inference support before publication.
- resilience: Unresolved/stale/cross-workspace support or implicit merge creates no durable record/reference.
- visual_evidence_required: false
- verified_by: [RPC-7.5]

#### AC RPC-5: Activity and lineage reads remain governed
- target_surfaces:
    - src/research_foundry/services/research_run_discovery.py
    - src/research_foundry/services/assertion_catalog.py
    - src/research_foundry/api/routers/assertions.py
    - src/research_foundry/services/export_service.py
    - src/research_foundry/api/openapi.json
- propagation_contract: Canonical origin/activity/use/inference/canonical-claim records feed authorized discovery, packet, lineage, and export shapes only after scope, rights, lifecycle, and version checks.
- resilience: Legacy records expose empty optional fields; denied candidates expose no derived values.
- visual_evidence_required: false
- verified_by: [RPC-7.6]

#### AC RPC-6: Lifecycle reconciliation uses exact action identity
- target_surfaces:
    - schemas/assertion_lifecycle_event.schema.yaml
    - src/research_foundry/services/assertion_impact.py
- propagation_contract: Canonical records produce deterministic inference/canonical-claim/report actions and exact manifest-derived receipt identities.
- resilience: Interrupted work resumes; malformed or identity-mismatched receipts fail closed.
- visual_evidence_required: false
- verified_by: [RPC-7.7]

#### AC RPC-7: Optional AOS refs remain optional and governed
- target_surfaces:
    - schemas/research_run_envelope.schema.yaml
    - src/research_foundry/services/provenance_envelope.py
    - src/research_foundry/services/export_service.py
- propagation_contract: Supplied AOS project/intent/knowledge refs round trip as opaque identifiers without copying AOS payloads or becoming provenance authority.
- resilience: Missing refs preserve behavior; malformed/unauthorized/cross-workspace refs reveal no existence signal.
- visual_evidence_required: false
- verified_by: [RPC-7.8]

#### AC RPC-8: Existing seams keep prior behavior
- target_surfaces:
    - src/research_foundry/services/assertion_registry.py
    - src/research_foundry/services/assertion_materialization.py
    - src/research_foundry/services/run_launch.py
    - src/research_foundry/services/search_router/router.py
- propagation_contract: Legacy fixtures preserve registry identity, supported-claim materialization, explicit reuse decisions, and discovery behavior when new inputs are omitted.
- resilience: Historical artifacts stay readable and do not trigger new canonical writes.
- visual_evidence_required: false
- verified_by: [RPC-7.9]

## Risk and Rollback

| Risk | Detection | Rollback / Containment |
|---|---|---|
| New record writer corrupts canonical state | Immutable conflict tests, digest checks, exact directory diff | Disable new hook; retain already valid immutable records; rebuild projections only |
| API leaks hidden existence | Two-workspace denial matrix and empty derived response checks | Remove additive response field/route while retaining canonical private records |
| Inference/report dependent missed | Impact manifest fixture mismatch | Keep authoritative source assertion blocked; mark feature not ready; rerun enumeration after fix |
| Legacy clients break | Before/after key-set and absent-field tests | Omit additive fields for legacy paths; no destructive schema migration |

## Validation Commands

Run from the repository root with the saved local environment:

```bash
./.venv/bin/python -m pytest tests/unit/test_assertion_materialization.py tests/unit/test_assertion_catalog.py tests/unit/test_assertion_impact.py
./.venv/bin/python -m pytest tests/integration/test_assertions_api.py tests/integration/test_assertion_reuse.py tests/integration/test_run_launch_reuse.py
./.venv/bin/python -m ruff check src/research_foundry tests
./.venv/bin/python -m mypy src/research_foundry --ignore-missing-imports
cd frontend/runs-viewer && npm run codegen:check && npx tsc --noEmit
```

Artifact and plan gates:

```bash
./.venv/bin/python .agents/skills/artifact-tracking/scripts/validate_artifact.py --file docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md --artifact-type prd --strict
./.venv/bin/python .agents/skills/artifact-tracking/scripts/validate_artifact.py --file docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md --artifact-type implementation-plan --strict
./.venv/bin/python .agents/skills/artifact-tracking/scripts/ac-coverage-report.py --plan docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md --dry
git diff --check
```

## Reviewer and Closeout Contract

- A phase stays `review` until its named reviewer approves the exact candidate tree.
- Generated OpenAPI/type changes are material tree changes and invalidate earlier approval.
- Reviewer remediation is single-writer and bounded to named findings; rereview uses the same reviewer when available.
- Repository-local completion does not prove owner-held/private corpus qualification or public activation.
- Tracker metadata, if later created under lowercase `.codex/progress/...`, is not implementation evidence by itself.
- No commit, merge, publish, deployment, or external writeback is authorized by this plan.
