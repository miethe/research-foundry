---
title: "Implementation Plan: Catalog-Assisted Research Planning"
schema_version: 2
doc_type: implementation_plan
status: draft
created: 2026-07-18
updated: 2026-07-23
feature_slug: catalog-assisted-research-planning
feature_version: v1
tier: 3
prd_ref: docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
plan_ref: null
human_brief_ref: docs/project_plans/human-briefs/catalog-assisted-research-planning.md
scope: "Use the existing governed assertion catalog and reuse decisions before discovery, write a deterministic evidence plan with covered/residual questions, make cache_first operational, and route only authorized residual work to existing providers."
effort_estimate: "28 pts bottom-up"
architecture_summary: "Authenticated catalog adapter → conservative evidence planner → residual-only Search Router orchestration → additive API/MCP/export/metrics, using the Research Provenance Continuity envelope."
related_documents:
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/human-briefs/catalog-assisted-research-planning.md
  - .codex/worknotes/catalog-assisted-research-planning/decisions-block.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
  - docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1.md
  - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
references:
  user_docs:
    - docs/dev/guides/catalog-assisted-research-planning.md
  context: []
  specs:
    - .agents/skills/planning/references/ac-schema.md
    - .agents/skills/planning/references/deferred-items-and-findings.md
    - .claude/specs/changelog-spec.md
    - schemas/search_request.schema.yaml
    - schemas/search_run.schema.yaml
    - schemas/research_brief.schema.yaml
    - schemas/routing_decision.schema.yaml
    - schemas/research_evidence_plan.schema.yaml
    - docs/dev/architecture/carp-contract-freeze.md
  related_prds:
    - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
    - docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
    - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
spike_ref: null
adr_refs: []
deferred_items_spec_refs:
  - docs/project_plans/design-specs/catalog-planning-semantic-reranking.md
  - docs/project_plans/design-specs/catalog-planning-adaptive-query-decomposition.md
  - docs/project_plans/design-specs/catalog-planning-canonical-claim-coverage.md
  - docs/project_plans/design-specs/catalog-planning-shared-evidence.md
findings_doc_ref: null
charter_ref: null
changelog_ref: CHANGELOG.md#unreleased
changelog_required: true
test_plan_ref: null
plan_structure: unified
progress_init: auto
owner: nick
contributors: []
priority: high
risk_level: high
category: enhancements
tags: [implementation, planning, catalog, retrieval-first, residual-discovery, assertions]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - schemas/search_request.schema.yaml
  - schemas/search_run.schema.yaml
  - schemas/research_brief.schema.yaml
  - schemas/research_evidence_plan.schema.yaml
  - schemas/routing_decision.schema.yaml
  - src/research_foundry/services/assertion_catalog.py
  - src/research_foundry/services/assertion_reuse.py
  - src/research_foundry/services/catalog_retrieval.py
  - src/research_foundry/services/research_evidence_planning.py
  - src/research_foundry/services/planning.py
  - src/research_foundry/services/run_launch.py
  - src/research_foundry/services/search_router/modes.py
  - src/research_foundry/services/search_router/policy.py
  - src/research_foundry/services/search_router/router.py
  - src/research_foundry/services/search_router/mcp_server.py
  - src/research_foundry/api/routers/runs.py
  - src/research_foundry/api/openapi.json
open_questions:
  - id: CARP-OQ-1
    status: resolved
    question: "Freeze the conservative deterministic evidence-coverage rule."
    resolution: >
      Six-condition conservative rule (docs/dev/architecture/carp-contract-freeze.md §3.1): a
      question is covered only if ALL SIX hold (lexical match on search_text, lifecycle eligible
      at immediate-before-selection re-read, evaluate_reuse() returns allow, required
      source-types/qualifiers satisfied, no contradicting authorized candidate, exact
      assertion_version pinned at selection). Any failure/uncertainty/error resolves to residual
      via a 14-member closed residual_reason enum (§3.2), never to covered and never left
      unresolved. Schema-enforced by research_evidence_plan.schema.yaml's covered/residual `allOf`
      partition (§3.1) plus the P1-addendum candidate-level `allOf` (five of the six conditions
      gated on `selected: true`; the sixth — version pinning — via the required
      `selected_assertion_ref.assertion_version`).
  - id: CARP-OQ-2
    status: resolved
    question: "Confirm opt-in versus default-on retrieval policy for v1."
    resolution: >
      Opt-in; default `disabled` (docs/dev/architecture/carp-contract-freeze.md §1). Absent/omitted
      `retrieval.policy` on `search_request` behaves byte-identically to pre-CARP legacy behavior:
      no catalog query, no evidence plan, no additive metrics. No implicit network fallback from
      any state, in any policy.
  - id: CARP-OQ-3
    status: resolved
    question: "Decide whether cache_first exposes anonymous refresh-required state."
    resolution: >
      No anonymous refresh-required state (docs/dev/architecture/carp-contract-freeze.md §2.4).
      `reuse_decision.action == "refresh"` is visible only inside `evaluated_candidates[]` on a
      plan built for an authorized identity inside the owning workspace. A denied/cross-workspace
      caller's `evaluated_candidates` is always empty (never populated with a refresh entry) —
      the denial path returns before any candidate is evaluated.
wave_plan:
  serialization_barriers:
    - schemas/search_request.schema.yaml
    - schemas/search_run.schema.yaml
    - src/research_foundry/services/planning.py
    - src/research_foundry/services/search_router/router.py
    - src/research_foundry/api/openapi.json
  phases:
    - id: P1
      depends_on: [RPC-1.G]
      isolation: shared
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - schemas/search_request.schema.yaml
        - schemas/search_run.schema.yaml
        - schemas/research_evidence_plan.schema.yaml
        - schemas/research_brief.schema.yaml
        - schemas/routing_decision.schema.yaml
    - id: P2
      depends_on: [CARP-1.G]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: adaptive
      files_affected:
        - src/research_foundry/services/catalog_retrieval.py
        - src/research_foundry/services/assertion_catalog.py
        - src/research_foundry/services/assertion_reuse.py
    - id: P3
      depends_on: [P2]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - src/research_foundry/services/research_evidence_planning.py
    - id: P4
      depends_on: [P3]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - src/research_foundry/services/planning.py
        - src/research_foundry/services/run_launch.py
        - src/research_foundry/services/search_router/modes.py
        - src/research_foundry/services/search_router/policy.py
        - src/research_foundry/services/search_router/router.py
    - id: P5
      depends_on: [P4]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: adaptive
      files_affected:
        - src/research_foundry/services/search_router/mcp_server.py
        - src/research_foundry/api/routers/runs.py
        - src/research_foundry/api/openapi.json
        - src/research_foundry/services/export_service.py
    - id: P6
      depends_on: [P5]
      isolation: shared
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: adaptive
      files_affected:
        - tests/unit/test_catalog_retrieval.py
        - tests/unit/test_research_evidence_planning.py
        - tests/test_search_router_router.py
        - tests/integration/test_run_launch_reuse.py
        - docs/dev/guides/catalog-assisted-research-planning.md
        - CHANGELOG.md
  waves:
    - [P1]
    - [P2]
    - [P3]
    - [P4]
    - [P5]
    - [P6]
---

# Implementation Plan: Catalog-Assisted Research Planning

**Plan ID**: `IMPL-2026-07-18-CATALOG-ASSISTED-RESEARCH-PLANNING`
**Date**: 2026-07-18
**Author**: Codex planning worker under delegated orchestration
**Human Brief**: `docs/project_plans/human-briefs/catalog-assisted-research-planning.md`
**Decisions Block**: `.codex/worknotes/catalog-assisted-research-planning/decisions-block.md`
**Complexity**: Large / Tier 3
**Total Estimated Effort**: 28 points

## Executive Summary

This plan activates the approved retrieval-before-discovery architecture without
adding a new index. It freezes an opt-in policy and evidence-plan contract,
wraps the existing assertion catalog/packet/reuse services behind an
authenticated adapter, computes conservative question coverage and residual
states, then integrates those outcomes into planning and the Search Router.
API/MCP/export/metrics work follows the settled orchestration, and one final
phase validates privacy, zero-network cache behavior, compatibility,
documentation, and Tier 3 reviewer gates.

The plan is intentionally serial through P5 because each phase freezes a contract consumed by the next and the central planning/router files are serialization barriers. It does not claim real-corpus reuse rate, quality uplift, or cost savings.

## Implementation Strategy

### Architecture Sequence

1. Consume the RPC provenance-context schema and freeze retrieval policy/evidence-plan contracts.
2. Query the existing assertion catalog through a bounded identity-aware adapter.
3. Evaluate exact candidates with existing reuse/version/lifecycle rules.
4. Produce a deterministic question-level evidence plan; uncertainty becomes residual.
5. Make `cache_first` catalog-backed and route only residual IDs under explicit fallback policy.
6. Propagate settled request/result/metric shapes through API, MCP, search run, launch, and export.
7. Validate adversarial privacy, no-network, deterministic replay, compatibility, docs, and exact-tree gates.

### Critical Path

`RPC-1.G → P1 → CARP-1.G → P2 → P3 → P4 → P5 → P6`

### Phase Summary

| Phase | Title | Estimate | Target Subagent(s) | Model | Effort | Notes |
|---|---|---:|---|---|---|---|
| P1 | Contract and Policy Freeze | 4 pts | backend-architect, api-designer | sonnet | extended | Requires RPC-1.G; validator + Karen exact-tree gate |
| P2 | Governed Catalog Adapter | 5 pts | python-backend-engineer | sonnet | adaptive | No direct ledger scans |
| P3 | Evidence Planner | 6 pts | backend-architect, python-backend-engineer | sonnet | extended | H3 algorithm |
| P4 | Retrieval-Then-Discovery Integration | 5 pts | python-backend-engineer | sonnet | extended | Planning/router integration owner |
| P5 | API, MCP, Export, Metrics | 4 pts | api-designer, python-backend-engineer | sonnet | adaptive | Generate contracts once |
| P6 | Hardening and Documentation | 4 pts | validation agents, docs agents, reviewers | sonnet/haiku/opus | adaptive/extended | Exact integrated candidate |
| **Total** | — | **28 pts** | — | — | — | — |

> H1-H6 details live in the linked Human Brief. H5 uses shipped surfaces and planned estimates as medium-confidence anchors because no authoritative actual-point ledger was found in the inspected tree.

## Deferred Items & In-Flight Findings Policy

### Deferred Items Triage

| Item ID | Category | Reason Deferred | Trigger for Promotion | Target Spec Path |
|---|---|---|---|---|
| CARP-DF-1 | research | Vector/semantic reranking is excluded by RAL and unnecessary for conservative lexical fallback | Measured lexical miss rate plus approved private-index threat model | docs/project_plans/design-specs/catalog-planning-semantic-reranking.md |
| CARP-DF-2 | research | Model-generated query decomposition adds nondeterminism and prompt/model provenance | Approved evaluation shows deterministic residual questions insufficient | docs/project_plans/design-specs/catalog-planning-adaptive-query-decomposition.md |
| CARP-DF-3 | dependency-blocked | Canonical-claim coverage depends on qualified merge safety and activation | Canonical merge qualified and authorized | docs/project_plans/design-specs/catalog-planning-canonical-claim-coverage.md |
| CARP-DF-4 | policy | Cross-workspace/public planning violates private-first v1 | Rights/federation design and security approval | docs/project_plans/design-specs/catalog-planning-shared-evidence.md |

P6 authors four `maturity: idea` design specs and appends their paths to `deferred_items_spec_refs`. No progress artifacts are created now.

### In-Flight Findings

Leave `findings_doc_ref: null`. On the first load-bearing execution finding, create `.claude/findings/catalog-assisted-research-planning-findings.md`, link it here, and promote unresolved design work to a spec before final closeout.

## Phase Breakdown

### Phase P1: Contract and Policy Freeze

**Dependencies**: Research Provenance Continuity `RPC-1.G` validator and Karen approval on the same exact contract tree.
**Assigned Subagents**: backend-architect, api-designer
**Exit State**: Adapter/planner/router writers have stable DTOs, enums, limits, denial behavior, and compatibility rules.

**RPC-1.G waiver**: every P1 task below declares `RPC-1.G` as a dependency (directly on CARP-1.1/
CARP-1.2, and via the phase-level Dependencies line above), but P1 executed and closed
(`CARP-1.G` APPROVED-with-conditions, then closed by this addendum) without it — sibling child `C1`
(Research Provenance Continuity) has not been executed, and no `RPC-1.G` gate exists to satisfy.
`docs/dev/architecture/carp-contract-freeze.md` §4 is honest about this ("Research Provenance
Continuity (`C1`) has not been executed... This document and its schemas therefore..." plus the §4
"Normative substitution" note); this plan was silent about it until now. The waiver: P1 substitutes
the CARP-owned `selected_assertion_ref` + `retrieval_receipt` pair for "the RPC context" everywhere
downstream ACs (CARP-5, CARP-4.2, CARP-6.6) name it, and the actual RPC leg is deferred to the §4.2
rebase whenever `C1` lands. See freeze doc §4 for the full contract.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| CARP-1.1 | Retrieval policy | Define disabled, catalog-only, and catalog-then-discovery states; default opt-in; explicit fallback/approval behavior. | No implicit network fallback; schema examples validate | 1 pt | backend-architect | sonnet | extended | RPC-1.G |
| CARP-1.2 | Identity and denial contract | Thread AuthIdentity/workspace requirements into service DTOs; freeze safe empty/denied response and metric behavior. | No-identity/two-workspace examples reveal no candidate-derived fields | 1 pt | api-designer | sonnet | extended | RPC-1.G |
| CARP-1.3 | Evidence-plan/coverage contract | Define stable question entries, evaluated candidates, exact decision refs, covered/residual states/reasons, limits, and deterministic ordering. | ≥10 H3 scenarios enumerated; uncertain states residual | 1.5 pts | backend-architect | sonnet | extended | CARP-1.1, CARP-1.2 |
| CARP-1.4 | RPC seam/compatibility review | Import/reference RPC context, prove legacy absence, and forbid duplicate evidence-selection fields. | Contract round-trip design approved | 0.5 pt | task-completion-validator | sonnet | adaptive | CARP-1.3 |
| CARP-1.G | Tier-3 contract gate | Review policy, provenance reuse, privacy, task/AC traceability, and exact P1 tree. | task-completion-validator then Karen APPROVE the same exact tree; material changes invalidate both verdicts | gate | task-completion-validator, Karen | sonnet/opus | extended | CARP-1.4 |

**Quality Gates**:

- `cache_first` has a zero-provider-call invariant.
- Catalog-only denial/empty does not trigger discovery.
- Catalog-then-discovery fallback is explicit and question-level.
- Candidate/page/question limits are schema-validated.
- CARP-OQ-1..3 are resolved or carry safe defaults.

### Phase P2: Governed Catalog Adapter

**Dependencies**: `CARP-1.G` approved on the exact current tree.
**Assigned Subagent**: python-backend-engineer
**Ownership**: `catalog_retrieval.py`, focused adapter DTOs/tests; existing catalog/reuse changes only if the frozen contract requires a narrow additive seam.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| CARP-2.1 | Bounded search/packet adapter | Accept identity, stable question, constraints, and limits; call catalog search then packet; never read ledger paths directly. | Stable authorized order; cursor/page caps; typed denial/empty | 2 pts | python-backend-engineer | sonnet | adaptive | CARP-1.G |
| CARP-2.2 | Exact reuse/version evaluation | Re-evaluate packets immediately before selection with workspace, required edition/extraction contract, capability, and lifecycle state. | allow/refresh/deny receipts exact; stale projection cannot select stale packet | 1.5 pts | python-backend-engineer | sonnet | adaptive | CARP-2.1 |
| CARP-2.3 | Privacy/integrity matrix | Test missing identity, cross-workspace, rights missing/denied, invalid page, empty projection, stale/invalidated/tombstoned, wrong edition, wrong extraction contract, packet disappearance. | Verifies policy-first behavior and zero derived denial metrics | 1.5 pts | python-backend-engineer | sonnet | extended | CARP-2.2 |
| CARP-2.G | Phase reviewer | Inspect exact tree and denial matrix. | task-completion-validator APPROVE | gate | task-completion-validator | sonnet | adaptive | CARP-2.3 |

### Phase P3: Evidence Planner

**Dependencies**: P2 approved.
**Assigned Subagents**: backend-architect, python-backend-engineer
**Ownership**: `research_evidence_planning.py` and tests; consumes adapter DTOs only.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| CARP-3.1 | Coverage rule implementation | Map lexical match, required source types, qualifiers, exact eligibility/version, and contradictions to conservative terminal states/reasons. | Uncertainty/conflict/missing constraint always residual | 2 pts | backend-architect | sonnet | extended | CARP-2.G |
| CARP-3.2 | Evidence-plan builder | Iterate stable question IDs, evaluate bounded candidates, select deterministically, record receipts/refs, and atomically write schema-valid plan. | Same inputs/catalog generation replay byte-equivalent | 3 pts | python-backend-engineer | sonnet | extended | CARP-3.1 |
| CARP-3.3 | H3 fixture gate | Exercise exact match, no hit, refresh, deny, stale, conflicting packet, missing qualifier, source-type mismatch, multiple equivalent hits, pagination boundary, duplicate candidate, catalog change. | Verifies AC CARP-3 semantics | 1 pt | data-layer-expert | sonnet | adaptive | CARP-3.2 |
| CARP-3.G | Milestone reviewers | Review conservative behavior and exact tree. | task-completion-validator and karen APPROVE | gate | task-completion-validator, karen | sonnet/opus | adaptive/extended | CARP-3.3 |

### Phase P4: Retrieval-Then-Discovery Integration

**Dependencies**: P3 approved.
**Assigned Subagent**: python-backend-engineer
**Integration Owner**: python-backend-engineer owns `planning.py`, `run_launch.py`, and Search Router orchestration edits.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| CARP-4.1 | Operational cache-first | Add catalog branch to `run_search`; persist governed selected refs/receipts and observed metrics; hard-block provider calls. | AC CARP-2; provider spies report zero calls | 2 pts | python-backend-engineer | sonnet | extended | CARP-3.G |
| CARP-4.2 | Evidence-aware run planning | Thread identity/policy through launch/plan; persist evidence plan; mark brief/swarm/routing questions covered/residual; carry RPC context. | Each question terminal; selected refs exact; legacy disabled behavior stable | 2 pts | python-backend-engineer | sonnet | extended | CARP-4.1 |
| CARP-4.3 | Residual discovery seam | Build provider requests only for residual IDs; preserve budgets/constraints; merge discovery outputs without changing covered decisions. | Provider spy queries equal residual set exactly | 1 pt | python-backend-engineer | sonnet | extended | CARP-4.2 |
| CARP-4.G | Milestone reviewers | Review zero-network and residual-only invariants on exact tree. | task-completion-validator and karen APPROVE | gate | task-completion-validator, karen | sonnet/opus | adaptive/extended | CARP-4.3 |

### Phase P5: API, MCP, Export, Metrics

**Dependencies**: P4 approved.
**Assigned Subagents**: api-designer, python-backend-engineer
**Integration Owner**: api-designer freezes DTO shape; backend engineer implements and regenerates once.

| Task ID | Task | Description | Acceptance Criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| CARP-5.1 | Run-launch identity/policy API | Thread request identity to service; add optional retrieval policy/limits; return evidence-plan/ref and safe retrieval summary. | RBAC/workspace tests pass; legacy request keys behave as before | 1 pt | api-designer, python-backend-engineer | sonnet | adaptive | CARP-4.G |
| CARP-5.2 | MCP/search contracts | Add policy/context options to search tools without business logic duplication; expose typed run results. | MCP wrappers remain thin; offline-safe imports preserved | 1 pt | python-backend-engineer | sonnet | adaptive | CARP-5.1 |
| CARP-5.3 | Export/metrics propagation | Add observed authorized retrieval counts and exact evidence-plan refs through search run/export; denial metrics contain no candidate signals. | AC CARP-5/6 contract round trip passes | 1 pt | python-backend-engineer | sonnet | adaptive | CARP-5.1 |
| CARP-5.4 | OpenAPI/type seam | Regenerate OpenAPI/types once; verify missing fields tolerated by clients; exercise service → router → schema seam. | Generated checks green; no hand-edited drift | 1 pt | api-designer | sonnet | adaptive | CARP-5.2, CARP-5.3 |
| CARP-5.G | Phase reviewer | Review exact transport/generated tree. | task-completion-validator APPROVE | gate | task-completion-validator | sonnet | adaptive | CARP-5.4 |

### Phase P6: Hardening and Documentation

**Dependencies**: P5 approved on integrated candidate.
**Assigned Subagents**: validation agents, documentation-writer, changelog-generator

| Task ID | Task | Description | Acceptance Criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| CARP-6.2 | Policy/privacy gate | Run missing-identity, two-workspace, rights-denial, disabled capability, denial-metric cases. | Verifies AC CARP-1 | 0.5 pt | task-completion-validator | sonnet | adaptive | CARP-5.G |
| CARP-6.3 | Cache-first gate | Run eligible, empty, denied, stale-projection, provider-spy, zero-budget cases. | Verifies AC CARP-2 | 0.5 pt | python-backend-engineer | sonnet | adaptive | CARP-5.G |
| CARP-6.4 | Evidence-plan gate | Run full H3 scenario/replay/schema matrix. | Verifies AC CARP-3 | 0.5 pt | backend-architect | sonnet | extended | CARP-5.G |
| CARP-6.5 | Residual-discovery gate | Compare residual IDs to provider calls; test disabled and explicit fallback modes. | Verifies AC CARP-4 | 0.5 pt | python-backend-engineer | sonnet | adaptive | CARP-5.G |
| CARP-6.6 | Provenance/contract gate | Round-trip selected refs/receipts through RPC context, search run, plan, launch, export, OpenAPI/types. | Verifies AC CARP-5 | 0.5 pt | api-designer | sonnet | adaptive | CARP-5.G |
| CARP-6.7 | Metrics/legacy regression | Verify authorized observed counts, denied zeros/absence, and pre-feature request/provider/output snapshots. | Verifies AC CARP-6 | 0.5 pt | task-completion-validator | sonnet | adaptive | CARP-6.2..6.6 |
| CARP-6.8 | Docs and deferred specs | Write user/dev guide, CHANGELOG, four deferred design specs, crosslinks; populate frontmatter refs. | Docs resolve; no unsupported savings claim; deferred refs populated | 1 pt | documentation-writer, changelog-generator | haiku | adaptive | CARP-6.7 |
| CARP-6.G | Final Tier 3 gate | Validate exact final tree/evidence and issue formal verdict. | task-completion-validator then karen APPROVE | gate | task-completion-validator, karen | sonnet/opus | adaptive/extended | CARP-6.8 |

## Structured Acceptance Criteria

#### AC CARP-1: Policy and identity precede retrieval
- target_surfaces:
    - src/research_foundry/services/planning.py
    - src/research_foundry/services/catalog_retrieval.py
    - src/research_foundry/api/routers/runs.py
- propagation_contract: Authenticated workspace identity, capability state, and explicit retrieval policy enter the service before any catalog query.
- resilience: Missing/denied context returns no candidate-derived values or ambient fallback.
- visual_evidence_required: false
- verified_by: [CARP-6.2]

#### AC CARP-2: Cache-first is catalog-backed and network-free
- target_surfaces:
    - src/research_foundry/services/search_router/modes.py
    - src/research_foundry/services/search_router/router.py
    - src/research_foundry/services/catalog_retrieval.py
- propagation_contract: The mode retrieves and evaluates governed packets while provider search/extract call counts remain zero.
- resilience: Empty or denied catalog states return typed bounded results and never fall through to providers.
- visual_evidence_required: false
- verified_by: [CARP-6.3]

#### AC CARP-3: Evidence plan is conservative and deterministic
- target_surfaces:
    - schemas/research_evidence_plan.schema.yaml
    - src/research_foundry/services/research_evidence_planning.py
    - schemas/research_brief.schema.yaml
- propagation_contract: Stable question IDs map to bounded evaluated candidates, exact decision refs, one terminal coverage state, and residual reason where needed.
- resilience: Missing constraints, uncertainty, conflict, refresh, denial, stale state, or version mismatch remains residual.
- visual_evidence_required: false
- verified_by: [CARP-6.4]

#### AC CARP-4: Discovery receives residual work only
- target_surfaces:
    - src/research_foundry/services/planning.py
    - src/research_foundry/services/search_router/policy.py
    - src/research_foundry/services/search_router/router.py
- propagation_contract: Catalog-then-discovery mode emits provider requests whose question IDs equal the evidence plan's residual set.
- resilience: Disabled retrieval preserves the prior question/provider flow; empty catalog becomes residual only under explicit fallback policy.
- visual_evidence_required: false
- verified_by: [CARP-6.5]

#### AC CARP-5: Selection uses the RPC provenance contract
- target_surfaces:
    - schemas/search_request.schema.yaml
    - schemas/search_run.schema.yaml
    - src/research_foundry/services/run_launch.py
    - src/research_foundry/services/export_service.py
- propagation_contract: Exact selected assertion versions and retrieval receipts flow through the RPC-defined context into persisted and exported run artifacts.
- resilience: Legacy artifacts omit selection lineage and remain readable without placeholder IDs.
- visual_evidence_required: false
- verified_by: [CARP-6.6]

#### AC CARP-6: Metrics reflect executed authorized control flow
- target_surfaces:
    - schemas/search_run.schema.yaml
    - src/research_foundry/services/search_router/router.py
    - src/research_foundry/services/export_service.py
- propagation_contract: Authorized runs derive question, candidate, selection, residual, and avoided-call counts from actual adapter/provider execution.
- resilience: Denied retrieval exposes no candidate-derived metrics; legacy runs may omit the additive block.
- visual_evidence_required: false
- verified_by: [CARP-6.7]

## Risk and Rollback

| Risk | Detection | Rollback / Containment |
|---|---|---|
| False coverage | H3 matrix, provider-call diff, review of residual reasons | Disable retrieval policy; retain evidence plan as non-authoritative diagnostic; schedule normal discovery |
| Workspace leak | Two-workspace response/timing and metric tests | Remove retrieval surface while preserving existing catalog/RAL services |
| Cache-first network call | Injected providers that fail test on invocation | Hard-disable mode integration; existing discovery modes remain untouched |
| Envelope drift | RPC/CARP schema round-trip and duplicate-field scan | Rebase on RPC contract; no compatibility alias without review |
| Legacy planning regression | Snapshot of brief/swarm/routing/provider chain with policy absent | Feature flag/policy disabled; restore prior branch without canonical data migration |

## Validation Commands

Focused implementation gates (exact file list finalized by writers):

```bash
./.venv/bin/python -m pytest tests/unit/test_assertion_catalog.py tests/integration/test_assertion_reuse.py
./.venv/bin/python -m pytest tests/test_search_router_foundation.py tests/test_search_router_router.py tests/integration/test_run_launch_reuse.py
./.venv/bin/python -m ruff check src/research_foundry tests
./.venv/bin/python -m mypy src/research_foundry --ignore-missing-imports
cd frontend/runs-viewer && npm run codegen:check && npx tsc --noEmit
```

Planning artifact gates:

```bash
./.venv/bin/python .agents/skills/artifact-tracking/scripts/validate_artifact.py --file docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md --artifact-type prd --strict
./.venv/bin/python .agents/skills/artifact-tracking/scripts/validate_artifact.py --file docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md --artifact-type implementation-plan --strict
./.venv/bin/python .agents/skills/artifact-tracking/scripts/ac-coverage-report.py --plan docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md --dry
git diff --check
```

## Reviewer and Closeout Contract

- Each phase requires exact-tree `task-completion-validator` approval; P1/P3/P4/final also require `karen`.
- Coverage/residual changes invalidate downstream P4/P5 evidence and require reruns.
- Generated OpenAPI/type changes are material and invalidate previous transport approval.
- `cache_first` cannot be considered complete without provider-spy proof of zero calls.
- Repository readiness does not establish real-corpus usefulness, default-on eligibility, owner/private qualification, deployment, or release.
- No commit, merge, publish, deploy, external writeback, or progress-file creation is authorized by this planning package.
