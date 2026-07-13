---
schema_version: 2
doc_type: implementation_plan
title: "Implementation Plan: Reusable Assertion Ledger v1"
description: "Tier 3 delivery plan for a private, passage-bound assertion ledger with governed reuse and lifecycle propagation."
status: review
created: 2026-07-12
updated: 2026-07-13
feature_slug: reusable-assertion-ledger
feature_version: v1
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
plan_ref: null
human_brief_ref: docs/project_plans/human-briefs/reusable-assertion-ledger.md
scope: "SPIKE-gated private assertion memory, immutable source editions/passages, durable assertions, scoped discovery, reuse policy, impact propagation, reviewer UI, hardening, and private rollout."
effort_estimate: "71 pts"
priority: high
risk_level: high
owner: nick
contributors: []
category: features
tags: [implementation, planning, tier-3, assertions, provenance, private-first]
spike_ref: docs/project_plans/SPIKEs/reusable-assertion-ledger-historical-replay-charter.md
related_documents:
  - .codex/worknotes/reusable-assertion-ledger/decisions-block.md
  - docs/project_plans/reports/investigations/reusable-assertion-ledger-findings.md
  - docs/project_plans/SPIKEs/reusable-assertion-ledger-historical-replay-charter.md
  - docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-charter.md
  - docs/project_plans/SPIKEs/reusable-assertion-ledger-retraction-propagation-charter.md
  - docs/project_plans/exploration/citation-precision-recall-metrics/citation-precision-recall-metrics-charter.md
  - docs/project_plans/exploration/claim-segmentation-source-alignment/claim-segmentation-source-alignment-charter.md
  - docs/project_plans/exploration/contradiction-log-v1/contradiction-log-v1-charter.md
  - docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
  - docs/project_plans/implementation_plans/features/runs-frontend-v1.md
deferred_items_spec_refs: []
findings_doc_ref: null
charter_ref: null
changelog_ref: null
changelog_required: true
test_plan_ref: null
plan_structure: independent
progress_init: pre-created
commit_refs: []
pr_refs: []
files_affected:
  - schemas/
  - src/research_foundry/services/
  - src/research_foundry/api/
  - frontend/runs-viewer/
  - tests/
  - docs/
  - CHANGELOG.md
wave_plan:
  serialization_barriers:
    - docs/project_plans/SPIKEs/reusable-assertion-ledger-historical-replay-results.md
    - docs/project_plans/SPIKEs/reusable-assertion-ledger-identity-merge-results.md
    - docs/project_plans/SPIKEs/reusable-assertion-ledger-retraction-propagation-results.md
    - schemas/source_assertion.schema.yaml
    - src/research_foundry/api/openapi.json
    - frontend/runs-viewer/src/types/rf/generated.ts
  phases:
    - id: P0
      depends_on: []
      model: sonnet
      effort: extended
      parallelizable: true
      files_affected: [docs/project_plans/SPIKEs/, docs/project_plans/exploration/]
    - id: P1
      depends_on: [P0]
      model: sonnet
      effort: extended
      parallelizable: false
      files_affected: [schemas/, docs/dev/architecture/]
    - id: P2
      depends_on: [P1]
      model: sonnet
      effort: adaptive
      parallelizable: false
      files_affected: [src/research_foundry/services/assertion_registry.py, tests/fixtures/assertion_ledger/]
    - id: P3
      depends_on: [P2]
      model: sonnet
      effort: adaptive
      parallelizable: false
      files_affected: [src/research_foundry/services/assertion_materialization.py, src/research_foundry/services/export_service.py]
    - id: P4
      depends_on: [P3]
      model: sonnet
      effort: adaptive
      parallelizable: false
      files_affected: [src/research_foundry/services/assertion_catalog.py, src/research_foundry/api/routers/assertions.py, src/research_foundry/api/openapi.json]
    - id: P5
      depends_on: [P4]
      model: sonnet
      effort: extended
      parallelizable: false
      files_affected: [src/research_foundry/services/assertion_reuse.py, src/research_foundry/services/assertion_impact.py]
    - id: P6
      depends_on: [P4]
      model: sonnet
      effort: adaptive
      parallelizable: true
      files_affected: [frontend/runs-viewer/src/screens/CatalogScreen.tsx, frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx, frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx]
    - id: P7
      depends_on: [P5, P6]
      model: sonnet
      effort: extended
      parallelizable: false
      files_affected: [tests/, frontend/runs-viewer/e2e/]
    - id: P8
      depends_on: [P7]
      model: sonnet
      effort: adaptive
      parallelizable: false
      files_affected: [docs/, README.md, CHANGELOG.md]
  waves:
    - [P0]
    - [P1]
    - [P2]
    - [P3]
    - [P4]
    - [P5, P6]
    - [P7]
    - [P8]
---

# Implementation Plan: Reusable Assertion Ledger v1

## Phase 0 evidence status (pre-review)

The three P0 result artifacts and the deterministic local-only harness are
ready for independent review. Their verdict is `conditional`, because no
representative private corpus or concluded citation, segmentation, and
contradiction contracts were available. The canonical P0 tracker is
`.Codex/progress/reusable-assertion-ledger/phase-1-progress.md`; it must retain
the pending `P0-GATES` reviewer task. No P1 implementation or flag enablement is
authorized by this pre-review evidence.

**Human Brief:** `docs/project_plans/human-briefs/reusable-assertion-ledger.md`
**Decisions Block:** `.codex/worknotes/reusable-assertion-ledger/decisions-block.md`
**Track:** Tier 3; `task-completion-validator` closes each phase, and `karen` reviews P0, P4, P7, and feature closeout.

## Executive summary

This plan adds a private, reusable ledger of exact passage-bound source assertions without replacing run-local Markdown/YAML evidence. Work is gated by measured replay economics, deterministic identity, and complete retraction propagation. Durable records feed rebuildable workspace-scoped read models; authorization and reuse policy precede ranking or content return. Canonical claims are optional and remain disabled if the merge audit misses its gate. Automated reuse remains separately flagged until fidelity, lifecycle, isolation, and rollback gates pass.

The target is private beta only. Public promotion, shared retrieval indexes, cross-tenant federation, and public-source rights operations are deferred design specifications, not v1 implementation.

## Locked decisions

- Source assertion, canonical claim, and inference remain distinct object types.
- Immutable editions and passages are content-addressed; mutable concepts use opaque stable IDs and versions.
- Exact dedupe ships before any semantic grouping.
- The current catalog remains a rebuildable projection, never ledger authority.
- Search, caches, counts, facets, suggestions, and impact reads are workspace scoped.
- Retraction blocking is authoritative and synchronous; downstream reconciliation may resume asynchronously.
- Assertion-only operation is the required fallback when semantic-merge safety is not proven.
- The feature flags are `RF_ASSERTION_LEDGER_ENABLED`, `RF_ASSERTION_REUSE_ENABLED`, and `RF_CANONICAL_CLAIMS_ENABLED`.

## Implementation strategy

### Critical path

`P0 -> P1 -> P2 -> P3 -> P4 -> P5 -> P7 -> P8`

P6 may proceed beside P5 after the P4 OpenAPI/type-generation barrier. Only one writing agent owns a file at a time. P7 integrates both paths and performs the Tier 3 hardening gate.

### Phase summary

| Phase | Name | Estimate | Primary agents | Model | Effort | Detailed plan |
|---|---|---:|---|---|---|---|
| P0 | Research gates | 8 pts | spike-writer, backend-architect, data-layer-expert | sonnet | extended | [Phase 1](./reusable-assertion-ledger-v1/phase-1-research-gates.md) |
| P1 | Canonical contracts | 8 pts | backend-architect, data-layer-expert | sonnet | extended | [Phase 2](./reusable-assertion-ledger-v1/phase-2-canonical-contracts.md) |
| P2 | Edition and passage registry | 8 pts | python-backend-engineer, data-layer-expert | sonnet | adaptive | [Phase 3](./reusable-assertion-ledger-v1/phase-3-edition-passage-registry.md) |
| P3 | Assertion materialization | 8 pts | python-backend-engineer, backend-architect | sonnet | adaptive | [Phase 4](./reusable-assertion-ledger-v1/phase-4-assertion-materialization.md) |
| P4 | Catalog, search, and API | 8 pts | python-backend-engineer, data-layer-expert | sonnet | adaptive | [Phase 5](./reusable-assertion-ledger-v1/phase-5-catalog-search-api.md) |
| P5 | Reuse, refresh, and impact | 8 pts | backend-architect, python-backend-engineer | sonnet | extended | [Phase 6](./reusable-assertion-ledger-v1/phase-6-reuse-refresh-impact.md) |
| P6 | Reviewer experience | 7 pts | ui-engineer-enhanced, frontend-developer | sonnet | adaptive | [Phase 7](./reusable-assertion-ledger-v1/phase-7-reviewer-experience.md) |
| P7 | Evaluation and hardening | 8 pts | python-backend-engineer, data-layer-expert, frontend-developer | sonnet | extended | [Phase 8](./reusable-assertion-ledger-v1/phase-8-evaluation-hardening.md) |
| P8 | Documentation and private rollout | 8 pts | documentation-writer, DevOps, lead-pm | sonnet/haiku | adaptive | [Phase 9](./reusable-assertion-ledger-v1/phase-9-docs-private-rollout.md) |
| **Total** |  | **71 pts** |  |  |  |  |

The phase rows and detailed task estimates both sum to the locked 71-point total. The H6 plumbing reserve is embedded in labeled tasks and is not additive to 71.

### H6 plumbing allocation

| Task | Plumbing surface | Points |
|---|---|---:|
| P1-003 | Compatibility and schema-generation contract | 2 |
| P3-003 | Run/export persistent-reference seam | 2 |
| P4-003 | DTO, OpenAPI, generated-type barrier | 2 |
| P6-001 | Frontend client/type plumbing | 1 |
| P8-001 | Feature flags, migration, rollback, monitoring | 2 |
| P8-002 | User/dev docs and CHANGELOG | 1 |
| DOC-006 | Deferred design-spec capture and reference append | 1 |
| **H6 total** |  | **11** |

## File ownership and serialization

| Surface | Owner | Consumers | Barrier |
|---|---|---|---|
| `schemas/source_*.schema.yaml`, `schemas/passage.schema.yaml`, assertion/evaluation/lifecycle schemas | data-layer-expert | services, API, codegen | P1 validator approval |
| `src/research_foundry/services/assertion_registry.py` | python-backend-engineer | materializer, reuse, impact | P2 validator approval |
| `src/research_foundry/services/assertion_materialization.py` | python-backend-engineer | export, catalog | P3 validator approval |
| `src/research_foundry/services/assertion_catalog.py` | data-layer-expert | assertions router | P4 seam task |
| `src/research_foundry/api/routers/assertions.py`, `src/research_foundry/api/openapi.json` | python-backend-engineer | runs-viewer codegen | OpenAPI commit and generated-type check |
| `src/research_foundry/services/assertion_reuse.py`, `assertion_impact.py` | backend-architect | run path, audit, writeback queues | P5 propagation gate |
| Runs-viewer assertion surfaces | ui-engineer-enhanced | P7 runtime smoke | P6 seam task |
| Evaluation fixtures and compatibility gold set | python-backend-engineer/frontend-developer | task-completion-validator, Karen | P7 approval |
| Adversarial isolation and performance suites | python-backend-engineer/data-layer-expert | senior-code-reviewer, Karen | P7 approval |
| Flags, runbooks, docs, CHANGELOG | DevOps/documentation-writer | private operators | P8 closeout |

## Global acceptance contracts

#### AC RAL-ISOLATION: Private-ledger policy covers retrieval and derived signals
- target_surfaces:
  - `src/research_foundry/services/assertion_catalog.py`
  - `src/research_foundry/services/assertion_reuse.py`
  - `src/research_foundry/api/routers/assertions.py`
  - `frontend/runs-viewer/src/screens/CatalogScreen.tsx`
  - `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx`
- propagation_contract: Workspace identity is resolved before search, ranking, facets, relationship traversal, packet assembly, cache lookup, export, and UI query construction.
- resilience: Missing workspace identity or policy context returns a typed denial; the UI renders no counts, suggestions, identifiers, or cached content.
- visual_evidence_required: "Desktop >=1440px screenshots for authorized results and denied/missing-policy states."
- verified_by: [P7-002, P7-004]

#### AC RAL-PACKET: Evidence packet propagates optional ledger fields safely
- target_surfaces:
  - `src/research_foundry/api/routers/assertions.py`
  - `frontend/runs-viewer/src/types/rf/generated.ts`
  - `frontend/runs-viewer/src/screens/CatalogScreen.tsx`
  - `frontend/runs-viewer/src/components/ProvenanceModal/ProvenanceModal.tsx`
  - `frontend/runs-viewer/src/components/ClaimLedger/ClaimAuditWorkbench.tsx`
- propagation_contract: The API returns a versioned packet; codegen creates optional TypeScript fields; the catalog, provenance modal, and audit workbench consume the same generated contract.
- resilience: Legacy or denied responses lacking persistent IDs, qualifiers, freshness, impact, or relationship fields render labeled unavailable/denied states and never infer values.
- visual_evidence_required: "Desktop >=1440px screenshots for full, legacy-missing, and denied packets."
- verified_by: [P7-001, P7-004]

#### AC RAL-LIFECYCLE: Invalid evidence is blocked before dependent cleanup
- target_surfaces:
  - `src/research_foundry/services/assertion_reuse.py`
  - `src/research_foundry/services/assertion_impact.py`
  - `src/research_foundry/services/catalog_service.py`
  - `src/research_foundry/services/export_service.py`
- propagation_contract: A monotonic lifecycle event changes authoritative eligibility first, then enumerates and reconciles report, run, export, index/cache, and writeback dependencies under one operation receipt.
- resilience: Unknown lifecycle state, interrupted traversal, or unavailable adapter remains denied and resumable; historical provenance stays readable to authorized auditors.
- visual_evidence_required: false
- verified_by: [P7-001, P7-003]

## Phase gates and review cadence

| Gate | Required evidence | Reviewer |
|---|---|---|
| P0 | Three result artifacts, threshold math, fallback decision, upstream exploration status | task-completion-validator + Karen |
| P1-P3 | Focused schema/service tests, compatibility fixtures, file ownership confirmation | task-completion-validator |
| P4 | Scoped API/catalog tests, OpenAPI/codegen diff, packet contract | task-completion-validator + Karen |
| P5-P6 | Retraction drill, frontend component tests, seam evidence | task-completion-validator |
| P7 | Gold-set metrics, leakage suite, runtime smoke, rollback rehearsal | task-completion-validator + Karen |
| P8 | Docs/CHANGELOG, migration receipt, private-beta health evidence, no public release action | task-completion-validator + Karen final |

No phase is complete until its named reviewer records `pass`. A failed canonical-merge gate selects assertion-only delivery; a failed replay, deterministic-identity, propagation, or isolation gate blocks automated reuse.

## Deferred items and findings policy

| Item | v1 treatment | Required artifact |
|---|---|---|
| Shared lexical/vector/graph indexes | Prohibited; workspace-scoped projections only | `docs/project_plans/design-specs/reusable-assertion-ledger-shared-indexes.md` |
| Public corpus rights and promotion | Prohibited; private sources stay private | `docs/project_plans/design-specs/reusable-assertion-ledger-public-rights-promotion.md` |
| Nanopublication/RO-Crate public interchange | Deferred with public promotion | Record in public-rights design spec |
| Canonical claims if merge gate fails | Feature flag stays off | Identity SPIKE result records assertion-only fallback |

During execution, create `findings_doc_ref` only when a load-bearing discovery occurs. Do not create progress files from this planning task; artifact tracking is initialized separately when execution is authorized.

## Validation commands

Each phase file narrows its commands. Feature closeout runs the project-supported Python tests, schema validation, API/OpenAPI consistency, runs-viewer typecheck/unit/E2E suite, workspace leakage matrix, replay benchmark, retraction drill, migration rehearsal, rollback rehearsal, and plan acceptance-coverage report.

## Private rollout boundary

P8 may prepare and execute only a private, workspace-scoped beta when separately authorized. It does not publish a corpus, enable shared indexes, contact external writeback systems during tests, promote assertions publicly, or infer production deployment authority. The default state after implementation is ledger writes enabled for the pilot workspace, automated reuse off until gate receipts are attached, and canonical claims off unless the merge verdict is `go`.
