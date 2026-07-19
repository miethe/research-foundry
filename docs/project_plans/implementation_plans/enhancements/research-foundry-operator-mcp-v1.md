---
title: "Implementation Plan: Research Foundry Operator MCP"
schema_version: 2
doc_type: implementation_plan
status: draft
created: 2026-07-18
updated: 2026-07-18
feature_slug: research-foundry-operator-mcp
feature_version: v1
tier: 3
prd_ref: docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
plan_ref: null
human_brief_ref: docs/project_plans/human-briefs/research-foundry-operator-mcp.md
scope: "Build a local-stdio-only governed operator MCP with identity-bound preflight and confirmation, durable idempotent jobs, cancel/resume, closed canonical-service adapters, bounded errors and receipts, and preview-only writeback."
effort_estimate: "29 pts bottom-up"
architecture_summary: "FastMCP stdio adapter -> trusted local identity/workspace/sensitivity resolution -> governance preflight -> bound confirmation -> immutable operation manifest -> AgentJob-backed attempts -> closed canonical-service adapters -> effect/checkpoint/terminal receipts; Knowledge MCP stays read-only and separate."
related_documents:
  - docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
  - docs/project_plans/human-briefs/research-foundry-operator-mcp.md
  - .codex/worknotes/research-foundry-operator-mcp/decisions-block.md
  - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
  - .codex/plans/research-interchange-provenance-access-initiative-v1.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
  - docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/design-specs/research_foundry_search_router_spec.md
  - docs/project_plans/design-specs/research_foundry_search_router_implementation_plan.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
references:
  user_docs: []
  context: []
  specs:
    - .agents/skills/planning/references/ac-schema.md
    - .agents/skills/planning/references/deferred-items-and-findings.md
    - .claude/specs/changelog-spec.md
    - schemas/research_brief.schema.yaml
    - schemas/swarm_plan.schema.yaml
    - schemas/source_card.schema.yaml
    - schemas/claim_ledger.schema.yaml
    - schemas/evidence_bundle.schema.yaml
  related_prds:
    - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
    - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
    - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
    - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
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
tags: [implementation, mcp, operator, governance, jobs, receipts, local-stdio]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - schemas/operator_mcp_operation.schema.yaml
  - schemas/operator_mcp_confirmation.schema.yaml
  - schemas/operator_mcp_receipt.schema.yaml
  - schemas/operator_mcp_error.schema.yaml
  - src/research_foundry/services/operator_mcp_policy.py
  - src/research_foundry/services/operator_operation_service.py
  - src/research_foundry/services/operator_tool_adapters.py
  - src/research_foundry/services/agent_job_service.py
  - src/research_foundry/services/agent_job_schemas.py
  - src/research_foundry/services/swarm_service.py
  - src/research_foundry/services/governance.py
  - src/research_foundry/services/audit_service.py
  - src/research_foundry/services/writeback.py
  - src/research_foundry/cli_commands.py
  - src/research_foundry/operator_mcp/__init__.py
  - src/research_foundry/operator_mcp/server.py
  - pyproject.toml
open_questions:
  - id: OPM-OQ-1
    status: open
    question: "Freeze the trusted local actor/workspace identity source."
  - id: OPM-OQ-2
    status: open
    question: "Freeze confirmation TTL, consumption, and exact-replay semantics."
  - id: OPM-OQ-3
    status: open
    question: "Decide whether v1 confirmations authorize one stage only or one fully previewed bounded manifest."
  - id: OPM-OQ-4
    status: open
    question: "Freeze operation cancellation safe points and atomic non-cancelable sections."
wave_plan:
  serialization_barriers:
    - src/research_foundry/services/agent_job_service.py
    - src/research_foundry/services/agent_job_schemas.py
    - src/research_foundry/services/governance.py
    - src/research_foundry/services/audit_service.py
    - src/research_foundry/services/writeback.py
    - src/research_foundry/services/operator_operation_service.py
    - src/research_foundry/services/operator_tool_adapters.py
    - src/research_foundry/operator_mcp/server.py
  phases:
    - id: P1
      depends_on: [RPC-1.G, KMCP-1.G]
      isolation: shared
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - schemas/operator_mcp_operation.schema.yaml
        - schemas/operator_mcp_confirmation.schema.yaml
        - schemas/operator_mcp_receipt.schema.yaml
        - schemas/operator_mcp_error.schema.yaml
        - src/research_foundry/services/operator_mcp_policy.py
    - id: P2
      depends_on: [OPM-1.G]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - src/research_foundry/services/operator_operation_service.py
        - src/research_foundry/services/agent_job_service.py
        - src/research_foundry/services/agent_job_schemas.py
        - src/research_foundry/services/audit_service.py
    - id: P3
      depends_on: [P2, CARP-4.G]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: adaptive
      files_affected:
        - src/research_foundry/services/swarm_service.py
        - src/research_foundry/services/operator_tool_adapters.py
        - src/research_foundry/cli_commands.py
    - id: P4
      depends_on: [P3, ERI-5.G]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - src/research_foundry/services/operator_tool_adapters.py
        - src/research_foundry/services/external_research_import.py
        - src/research_foundry/services/source_cards.py
        - src/research_foundry/services/extraction.py
        - src/research_foundry/services/claim_mapping.py
        - src/research_foundry/services/synthesis.py
        - src/research_foundry/services/verification.py
        - src/research_foundry/services/writeback.py
    - id: P5
      depends_on: [P4, KMCP-1.G]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - src/research_foundry/operator_mcp/__init__.py
        - src/research_foundry/operator_mcp/server.py
        - src/research_foundry/services/writeback.py
        - src/research_foundry/services/operator_tool_adapters.py
        - pyproject.toml
    - id: P6
      depends_on: [P5]
      isolation: shared
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: adaptive
      files_affected:
        - tests/unit/test_operator_mcp_policy.py
        - tests/unit/test_operator_operation_service.py
        - tests/unit/test_operator_tool_adapters.py
        - tests/integration/test_operator_mcp_server.py
        - tests/integration/test_operator_mcp_workspace_isolation.py
        - tests/integration/test_operator_mcp_writeback_preview.py
        - docs/user/research-foundry-operator-mcp.md
        - docs/dev/architecture/operator-mcp-governance.md
        - CHANGELOG.md
  waves:
    - [P1]
    - [P2]
    - [P3]
    - [P4]
    - [P5]
    - [P6]
---

# Implementation Plan: Research Foundry Operator MCP

**Plan ID**: `IMPL-2026-07-18-RESEARCH-FOUNDRY-OPERATOR-MCP`
**Date**: 2026-07-18
**Author**: Codex planning worker under delegated orchestration
**Human Brief**: `docs/project_plans/human-briefs/research-foundry-operator-mcp.md`
**Decisions Block**: `.codex/worknotes/research-foundry-operator-mcp/decisions-block.md`
**Complexity**: Large / Tier 3
**Total Estimated Effort**: 29 points

## Executive Summary

This plan creates a local stdio privileged-operation surface without combining it
with the read-only Knowledge MCP. It freezes operation, identity, sensitivity,
confirmation, receipt, and error contracts; builds a durable operation coordinator
over existing AgentJob attempts; extracts swarm orchestration from the CLI; wraps
canonical planning/import/research-stage services; and only then registers tools in
a thin FastMCP server. Writeback exposure is a pure preview with negative evidence
proving no live client or downstream mirror is reachable.

The critical path is deliberately serial because each phase establishes the trust
contract consumed by the next. No progress files are created with this draft.
Execution begins only after parent/child dependency gates are approved and the
artifact tracker initializes phase progress.

## Implementation Strategy

### Architecture sequence

1. Freeze closed operation/tool schemas, trusted identity/workspace/sensitivity, governance ordering, confirmation binding, receipts, and errors.
2. Persist an immutable operation manifest and reuse AgentJob for attempts/events/artifacts/status/termination.
3. Prove idempotency, cancel, resume, and effect reconciliation before exposing expensive tools.
4. Register plan/swarm/job lifecycle adapters and move swarm business logic out of Typer.
5. Consume ERI's import seam and register the canonical ingest/extract/claim-map/synthesize/verify/bundle services.
6. Add the stdio server, optional dependency behavior, tool limits, namespace separation, and pure writeback preview.
7. Run adversarial matrices, compatibility gates, docs, deferred specs, and exact-tree reviews.

### Non-duplication rules

- Knowledge MCP owns read-only knowledge resources; Operator MCP does not register them.
- Search Router remains the discovery/extraction authority; Operator MCP does not add providers or router policy.
- RPC owns provenance context and receipt references.
- ERI owns external packet parsing, staging, source/citation resolution, checkpoints, and import receipts.
- CARP owns catalog-before-discovery planning behavior.
- RAL/activation own assertion identity, reuse, lifecycle, population, and promotion semantics.
- AgentJob owns attempts/events/artifacts/termination; operation manifests own confirmed effect semantics.
- Audit events are supplemental. Immutable operator receipts are the effect authority.

### Critical path and external gates

`RPC-1.G + KMCP-1.G -> P1 -> OPM-1.G -> P2 -> CARP-4.G-gated P3 -> ERI-5.G-gated P4 -> P5 -> P6`

| Gate | Required evidence before phase starts |
|---|---|
| RPC-1.G | Canonical origin/run/activity/receipt/AOS/materialization schemas approved by validator and Karen on one exact tree |
| KMCP-1.G | Read-only Knowledge MCP tool/resource names and non-overlap inventory approved on the exact P1 tree |
| CARP-4.G | Settled run plan/swarm/routing behavior and provenance propagation approved on the exact P4 tree |
| ERI-5.G | Resumable import service, immutable receipt/checkpoint contract, and Operator-MCP seam approved on the exact P5 tree |

If an external gate is absent, the dependent phase stays pending; no temporary duplicate schema or service is introduced.

### Phase Summary

| Phase | Title | Estimate | Target subagent(s) | Model | Effort | Gate |
|---|---|---:|---|---|---|---|
| P1 | Contract, Identity, and Confirmation | 4 pts | backend-architect, api-designer | sonnet | extended | Security + validator + Karen exact-tree gate |
| P2 | Durable Operation Coordinator | 5 pts | python-backend-engineer | sonnet | extended | Validator + karen |
| P3 | Run Planning and Swarm Adapters | 5 pts | python-backend-engineer | sonnet | adaptive | Validator |
| P4 | Import and Research-Stage Adapters | 5 pts | python-backend-engineer, api-designer | sonnet | extended | Validator + karen |
| P5 | Stdio Server and Writeback Preview | 6 pts | python-backend-engineer, api-designer | sonnet | extended | Security + validator |
| P6 | Hardening, Docs, Exact-Tree Review | 4 pts | validation implementer, docs agents, reviewers | sonnet/haiku/opus | adaptive/extended | Validator then karen |
| **Total** | — | **29 pts** | — | — | — | — |

> H1-H6 details live in the linked Human Brief. The estimate excludes remote transport, live writeback, arbitrary execution, approval UI, schedules, and hosted/public qualification.

## Deferred Items & In-Flight Findings Policy

### Deferred Items Triage

| Item ID | Category | Reason deferred | Trigger for promotion | Target spec path |
|---|---|---|---|---|
| OPM-DF-1 | security/transport | Local stdio does not solve remote auth, TLS/origin, canonical URL, revocation, rate limit, or approval UX | Approved remote threat model and owner-authorized deployment need | docs/project_plans/design-specs/operator-mcp-remote-transport.md |
| OPM-DF-2 | external mutation | Preview safety does not authorize downstream effects or compensation | Target-specific approval/idempotency/rollback design and owner-held canary plan | docs/project_plans/design-specs/operator-mcp-live-writeback.md |
| OPM-DF-3 | scope | Arbitrary shell/files/provider/adapter/plugin/schedules violate closed-tool design | Named measured use case with canonical governed service | N/A — explicit non-goal until a concrete capability is named |
| OPM-DF-4 | operations | Public/hosted qualification requires owner identity, private data, deployment, monitoring, and incident response | Separate release plan and owner authorization | N/A — operational gate, not a code design spec |

P6 authors the two named design specs at `maturity: shaping` and appends their paths
to `deferred_items_spec_refs`. No progress artifact is created by this plan draft.

### In-flight findings

Leave `findings_doc_ref: null`. If execution discovers a load-bearing mismatch—such
as AgentJob records being unsuitable for deterministic operations—create
`.claude/findings/research-foundry-operator-mcp-findings.md`, link it here, and stop the
affected phase for targeted design/re-estimation rather than inventing a parallel
job authority.

## Phase Breakdown

### Phase P1: Contract, Identity, and Confirmation

**Dependencies**: Research Provenance Continuity `RPC-1.G` and Knowledge MCP `KMCP-1.G` approved exact-tree contracts.
**Integration owner**: backend-architect.
**Exit state**: effect writers have stable schemas, trusted identity inputs, policy order, confirmation semantics, limits, and safe errors.

| Task ID | Task | Description | Acceptance criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|
| OPM-1.1 | Operation and tool contract | Define closed operation kinds/tool names, input/result schemas, canonicalization, limits, target refs, stage prerequisites, and Knowledge MCP non-overlap inventory. | Positive/negative fixtures validate; unknown/wildcard operations reject | 1 pt | api-designer | sonnet | extended | RPC-1.G, KMCP-1.G |
| OPM-1.2 | Identity and sensitivity contract | Resolve trusted local `AuthIdentity`, require workspace, compute strictest sensitivity, and freeze no-existence-leak behavior before lookup. | Missing/wrong identity and two-workspace fixtures return one safe denial | 1 pt | backend-architect | sonnet | extended | OPM-1.1 |
| OPM-1.3 | Guard/preflight and confirmation | Order capability/RBAC/audit-health/guard/preflight checks; define opaque token binding, TTL, one-time atomic consumption, policy-drift and exact-replay rules. | Expired/replayed/mismatched token matrix produces zero manifest/effects | 1 pt | backend-architect, python-backend-engineer | sonnet | extended | OPM-1.2 |
| OPM-1.4 | Receipt and bounded-error schemas | Freeze operation/action/effect/checkpoint/terminal receipt fields, audit disposition, reason codes, retryability, redaction, and size limits. | Golden/negative schemas reject unbounded/raw exception and unauthorized fields | 1 pt | api-designer | sonnet | extended | OPM-1.1 |
| OPM-1.G | Tier-3 contract gate | Review identity source, authorization-before-lookup, confirmation binding, receipts, tool inventory, provenance reuse, task/AC traceability, and exact P1 tree. | task-completion-validator then Karen APPROVE the same exact tree; material changes invalidate both verdicts | gate | task-completion-validator, Karen | sonnet/opus | extended | OPM-1.2, OPM-1.3, OPM-1.4 |

**Quality gate**:

- OPM-OQ-1..4 resolved or defaults explicitly approved.
- Security reviewer verifies authorization-before-lookup and token binding.
- `task-completion-validator` then Karen approve the same exact schemas/examples/threat-matrix tree.
- No effect adapter or MCP server exists yet.

### Phase P2: Durable Operation Coordinator

**Dependencies**: `OPM-1.G` approved on the exact current tree.
**Integration owner**: python-backend-engineer.
**Exit state**: stable operation manifests coordinate AgentJob attempts and converge through retry/cancel/resume.

| Task ID | Task | Description | Acceptance criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|---|
| OPM-2.1 | Immutable operation store | Atomically persist canonical operation/action manifests, input/policy digests, token-consumption proof, workspace, sensitivity, and target refs under confined local state. | Exact manifest replay resolves same operation; changed manifest conflicts | 1.5 pts | python-backend-engineer | sonnet | extended | OPM-1.G |
| OPM-2.2 | AgentJob attempt adapter | Reuse create/load/events/artifacts/status/poll/terminate/cleanup with identity scoping; link attempts to operation id; do not expose `accept_job`. | Legacy AgentJob reads pass; wrong-workspace attempts are indistinguishable from missing | 1.5 pts | python-backend-engineer | sonnet | extended | OPM-2.1 |
| OPM-2.3 | Effect/checkpoint/terminal receipts | Persist immutable action/effect receipts and separate atomic checkpoints; reconcile counts/digests into one terminal receipt; link supplemental audit event/disposition. | Truncated/extra/duplicate/reordered/mismatched receipt fixtures deny | 1 pt | python-backend-engineer, data-layer-expert | sonnet | extended | OPM-2.2 |
| OPM-2.4 | Cancel and resume state machine | Persist cancellation request, honor safe points, mark non-cancelable atomic sections, resume first incomplete action under fresh policy/confirmation and new attempt. | H3 ten-scenario matrix converges with uninterrupted effects | 1 pt | python-backend-engineer | sonnet | extended | OPM-2.3 |

**Quality gate**:

- Process-loss, exact-retry, conflict, cancel, resume, policy-change, and reconciliation fixtures pass.
- Operation receipt is primary; audit-service failure is explicit and cannot erase effect truth.
- `task-completion-validator` and `karen` approve the exact lifecycle candidate.

### Phase P3: Run Planning and Swarm Adapters

**Dependencies**: P2 and `CARP-4.G`.
**Integration owner**: python-backend-engineer.
**Exit state**: plan/swarm operations and lifecycle tools execute through canonical services and common receipts.

| Task ID | Task | Description | Acceptance criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|---|
| OPM-3.1 | Plan adapter | Wrap `planning.plan_run()` with explicit depth/audience/cost/freshness/profile/project fields, prerequisites, guard context, result/effect mapping, and RPC refs. | Direct-service/MCP-adapter fixture outputs equivalent canonical refs | 1 pt | python-backend-engineer | sonnet | adaptive | P2, CARP-4.G |
| OPM-3.2 | Canonical swarm service | Move adapter dispatch/source-candidate persistence out of `cli_commands.py` into `swarm_service`; CLI and adapter call same closed service; adapter ids must be policy allowlisted. | CLI parity passes; unknown/disallowed adapters deny; dry-run has zero effects | 1.5 pts | python-backend-engineer | sonnet | adaptive | OPM-3.1 |
| OPM-3.3 | Swarm start adapter | Register `swarm.start` action planning, budgets/timeouts, effective sensitivity/profile, checkpoint boundaries, source-candidate effect receipt, and cancellation. | Degraded adapters remain typed; cancel/resume does not duplicate candidate artifact | 1.5 pts | python-backend-engineer | sonnet | adaptive | OPM-3.2 |
| OPM-3.4 | Job lifecycle adapters | Implement bounded identity-scoped `job.status`, `job.cancel`, and `job.resume` DTO adapters over operation service. | No raw event file reads, unbounded pages, or wrong-workspace detail | 1 pt | python-backend-engineer | sonnet | adaptive | OPM-2.4 |

**Quality gate**:

- Tool adapters invoke no CLI/Typer/subprocess path.
- Plan/swarm/cancel/resume parity and negative policy fixtures pass.
- `task-completion-validator` approves exact service extraction and adapters.

### Phase P4: Import and Research-Stage Adapters

**Dependencies**: P3 and `ERI-5.G`.
**Integration owner**: python-backend-engineer.
**Exit state**: import and canonical research stages share the operation lifecycle, preserve prerequisites/receipts, and block unsafe chaining.

| Task ID | Task | Description | Acceptance criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|---|
| OPM-4.1 | External import adapter | Consume ERI's service-level dry-run/import/resume request and immutable receipt/checkpoint result; bind packet/target/workspace/sensitivity/idempotency. | MCP adapter parses no packet member; direct ERI/MCP receipts match refs | 1 pt | python-backend-engineer | sonnet | extended | ERI-5.G, OPM-2.4 |
| OPM-4.2 | Source ingest adapter | Wrap `ingest_source()` with identity-derived assertion workspace, sensitivity, fetch policy, source limits, and source/materialization receipt refs. | No hard-coded default workspace; denied/degraded ingest remains explicit | 1 pt | python-backend-engineer | sonnet | extended | OPM-4.1 |
| OPM-4.3 | Extract and claim-map adapters | Wrap `extract_run()` and `build_claim_ledger()` with stage prerequisites, model-profile policy, budgets, action/effect receipts, cancel safe points, and bounded result summaries. | Missing/changed inputs deny; exact retry creates no duplicate cards/claims | 1.5 pts | python-backend-engineer | sonnet | extended | OPM-4.2 |
| OPM-4.4 | Synthesize, verify, and bundle adapters | Wrap canonical services; bind model/final/LLM policy; make verify failure a governed result; allow bundle only under configured verification prerequisite. | Unsupported verification blocks dependent bundle action; no false success | 1 pt | python-backend-engineer | sonnet | extended | OPM-4.3 |
| OPM-4.5 | Cross-stage seam gate | Prove each adapter uses RPC/ERI/canonical refs, one operation envelope, exact prerequisites, and no duplicate parsing/business logic. | Service parity, interrupted chain, and provenance-reference fixtures pass | 0.5 pt | api-designer, task-completion-validator | sonnet | adaptive | OPM-4.1..4.4 |

**Quality gate**:

- External Interchange exact-tree dependency is recorded.
- Verification-denial, stage-missing, wrong-workspace, sensitivity, timeout, cancel, and resume cases pass.
- `task-completion-validator` and `karen` approve the integrated mutation milestone.

### Phase P5: Stdio Server and Writeback Preview

**Dependencies**: P4 and approved Knowledge MCP inventory.
**Integration owner**: python-backend-engineer.
**Exit state**: optional local stdio server exposes only approved tools, bounded outputs, and non-executing writeback preview.

| Task ID | Task | Description | Acceptance criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|---|
| OPM-5.1 | FastMCP server scaffold | Add lazy optional MCP import, `build_server()`, stdio `main()`, explicit server identity/version, and no-effect startup. | Base import works without SDK; missing SDK prints one install hint | 1.5 pts | python-backend-engineer | sonnet | adaptive | P4 |
| OPM-5.2 | Closed tool registry | Register §6.1 tools with versioned schemas, bounded inputs/results, operation adapter delegation, and tool-introspection fixture. | Exact inventory; no Knowledge MCP duplicates or wildcard execution | 1 pt | api-designer, python-backend-engineer | sonnet | extended | OPM-5.1, KMCP-1.G |
| OPM-5.3 | Pure writeback preview | Add `preview_writeback()` that validates bundle/targets/policy and writes only a staged operation preview; never call live writeback, clients, or mirror paths. | Network/client/mirror spies remain zero; preview reason codes schema-valid | 1.5 pts | python-backend-engineer | sonnet | extended | OPM-5.2 |
| OPM-5.4 | Limits and error mapping | Enforce input/action/event/result/error size caps, runtime/cost limits, redaction, retryable reason codes, and no-existence-leak mapping at transport boundary. | Oversize/internal-error/wrong-workspace fixtures return bounded safe envelopes | 1 pt | api-designer | sonnet | extended | OPM-5.2 |
| OPM-5.5 | Packaging and entrypoint | Reuse/add optional `mcp` extra and package entrypoint without auto-start, daemon, listener, or network probe. | Wheel/editable install and module entrypoint tests pass | 0.5 pt | python-backend-engineer | sonnet | adaptive | OPM-5.1 |
| OPM-5.6 | P5 safety gate | Static source/call-path review plus runtime spies prove no HTTP route, live writeback, agent-job accept, shell, subprocess, arbitrary path, or integration client in registered tools. | Security reviewer and validator approve exact registry/call path | 0.5 pt | senior-code-reviewer, task-completion-validator | sonnet | extended | OPM-5.3..5.5 |

**Quality gate**:

- Tool inventory matches PRD exactly and remains separate from Knowledge MCP.
- Preview-only negative proof includes static and runtime evidence.
- `task-completion-validator` approves; any registry change requires rerun.

### Phase P6: Hardening, Documentation, and Exact-Tree Review

**Dependencies**: P5.
**Integration owner**: validation implementer.
**Exit state**: one exact integrated candidate satisfies AC OPM-1..7 with truthful repository/live boundaries.

| Task ID | Task | Description | Acceptance criteria | Estimate | Subagent | Model | Effort | Dependencies |
|---|---|---|---|---:|---|---|---|---|---|
| OPM-6.1 | Integrated fixture matrix | Assemble public-safe two-workspace runs/import packets and interrupted operations for deterministic end-to-end validation. | Fixtures contain no owner/private data and enumerate expected receipts/effects | 0.5 pt | validation implementer | sonnet | adaptive | P5 |
| OPM-6.2 | Confirmation adversarial gate | Test missing identity, denial, expiry, replay, wrong actor/workspace, payload/target/policy/sensitivity drift, and atomic token consumption. | AC OPM-1 evidenced; zero-effect assertions explicit | 0.5 pt | validation implementer | sonnet | extended | OPM-6.1 |
| OPM-6.3 | Workspace/sensitivity gate | Test lookup, status/events/errors, ingest, import, stages, and receipts under two identities and threshold changes. | AC OPM-2 evidenced with no existence leak | 0.5 pt | validation implementer | sonnet | extended | OPM-6.1 |
| OPM-6.4 | Lifecycle recovery gate | Run H3 exact replay/conflict/cancel/resume/process-loss/receipt-corruption matrix and compare canonical effects. | AC OPM-3 evidenced; interrupted/uninterrupted converge | 0.5 pt | validation implementer | sonnet | extended | OPM-6.1 |
| OPM-6.5 | Closed-adapter gate | Introspect tools and scan handler call paths; compare direct service and adapter result refs; assert no arbitrary dispatch. | AC OPM-4 evidenced | 0.5 pt | validation implementer, senior-code-reviewer | sonnet | adaptive | OPM-6.1 |
| OPM-6.6 | Import/stage seam gate | Run ERI import plus ingest/extract/claim-map/synthesize/verify/bundle prerequisite/receipt matrix. | AC OPM-5 evidenced | 0.25 pt | validation implementer | sonnet | adaptive | OPM-6.1 |
| OPM-6.7 | Preview-only gate | Run target/sensitivity/degraded cases with network/client/mirror spies and call-path scan. | AC OPM-6 evidenced; zero external/mirror effects | 0.25 pt | validation implementer, senior-code-reviewer | sonnet | extended | OPM-6.1 |
| OPM-6.8 | Transport/error gate | Test missing SDK, startup, bounded inputs/events/errors, redaction, and base-package/CLI compatibility. | AC OPM-7 evidenced | 0.25 pt | validation implementer | sonnet | adaptive | OPM-6.1 |
| OPM-6.9 | Docs, CHANGELOG, deferred specs | Write user setup/operation guide, architecture/governance doc, `[Unreleased]` entry, remote-transport and live-writeback shaping specs; populate refs. | Docs match exact tool inventory and do not claim live qualification | 0.5 pt | documentation-writer, changelog-generator | haiku | adaptive | OPM-6.2..6.8 |
| OPM-6.10 | Final exact-tree review | Run focused/full gates, duplicate-authority scan, docs/link validation, task-completion validator, then karen. | Tier 3 approval recorded on exact current tree | 0.25 pt | task-completion-validator, karen | opus | extended | OPM-6.9 |

## Structured Acceptance-Criteria Verification

#### AC OPM-1: Preflight and confirmation bind exact authority

- target_surfaces:
    - schemas/operator_mcp_operation.schema.yaml
    - schemas/operator_mcp_confirmation.schema.yaml
    - src/research_foundry/services/operator_mcp_policy.py
- propagation_contract: Trusted actor/workspace, effective sensitivity, operation, canonical digest, idempotency key, policy snapshot, targets, and expiry are frozen before token minting and revalidated before manifest creation.
- resilience: Missing identity, denial, expiry, replay, or any bound-field mismatch produces zero manifest and zero effect.
- visual_evidence_required: false
- verified_by: [OPM-6.2]

#### AC OPM-2: Workspace and sensitivity precede lookup and execution

- target_surfaces:
    - src/research_foundry/services/operator_mcp_policy.py
    - src/research_foundry/services/agent_job_service.py
    - src/research_foundry/services/source_cards.py
- propagation_contract: Identity-derived workspace and strictest sensitivity gate operation lookup, attempts, adapters, events, receipts, and errors.
- resilience: Wrong-workspace or above-threshold refs return a safe non-existence shape without derived detail.
- visual_evidence_required: false
- verified_by: [OPM-6.3]

#### AC OPM-3: Jobs are idempotent, cancelable, and resumable

- target_surfaces:
    - schemas/operator_mcp_receipt.schema.yaml
    - src/research_foundry/services/operator_operation_service.py
    - src/research_foundry/services/agent_job_service.py
- propagation_contract: Stable manifests coordinate bounded attempts, immutable effects, safe cancellation, and resume from the first incomplete action.
- resilience: Exact replay returns prior state; conflicts and receipt corruption deny; completed effects never replay.
- visual_evidence_required: false
- verified_by: [OPM-6.4]

#### AC OPM-4: Closed tools delegate to canonical services

- target_surfaces:
    - src/research_foundry/services/operator_tool_adapters.py
    - src/research_foundry/services/swarm_service.py
    - src/research_foundry/operator_mcp/server.py
- propagation_contract: Each registered tool delegates through one named canonical service adapter and returns the common operation/receipt envelope.
- resilience: Unknown tool/provider/adapter/path/URL-fetch/command input is invalid and never dispatched.
- visual_evidence_required: false
- verified_by: [OPM-6.5]

#### AC OPM-5: Import and research stages preserve prerequisites and receipts

- target_surfaces:
    - src/research_foundry/services/operator_tool_adapters.py
    - src/research_foundry/services/external_research_import.py
    - src/research_foundry/services/verification.py
    - src/research_foundry/services/writeback.py
- propagation_contract: ERI import and canonical stage adapters retain service receipts, prerequisites, and provenance refs in exact operation effects.
- resilience: Quarantine, missing input, or verify failure blocks dependent actions with a typed governed result.
- visual_evidence_required: false
- verified_by: [OPM-6.6]

#### AC OPM-6: Writeback preview cannot execute or mirror

- target_surfaces:
    - src/research_foundry/services/writeback.py
    - src/research_foundry/services/operator_tool_adapters.py
    - src/research_foundry/operator_mcp/server.py
- propagation_contract: Preview validates and renders only under operation staging without invoking live writeback, integration clients, or downstream mirrors.
- resilience: Missing/degraded/review-required targets return reason codes and zero external/mirror effect.
- visual_evidence_required: false
- verified_by: [OPM-6.7]

#### AC OPM-7: Transport, errors, and receipts stay bounded

- target_surfaces:
    - schemas/operator_mcp_error.schema.yaml
    - schemas/operator_mcp_receipt.schema.yaml
    - src/research_foundry/operator_mcp/server.py
- propagation_contract: Local stdio tools return versioned bounded operation, status, event, receipt, and error envelopes with retry and audit-delivery dispositions.
- resilience: Missing SDK yields one install hint; startup has no network/effect; internal errors are redacted and capped.
- visual_evidence_required: false
- verified_by: [OPM-6.8]

## Risk Controls and Rollback

| Risk | Prevention | Detection | Rollback / safe state |
|---|---|---|---|
| Identity/workspace bypass | Trusted identity and confirmation binding | Two-workspace matrix and no-existence tests | Disable stdio entrypoint; retain receipts/manifests |
| Confirmation replay/confusion | Canonical digest, TTL, atomic consumption | Replay/drift adversarial gate | Revoke outstanding tokens; no effect deletion |
| Partial effects after cancel | Action manifest, effect receipts, safe points | Interrupted/uninterrupted reconciliation | Resume or manual review; never delete canonical evidence |
| Service/MCP drift | Thin adapters and parity tests | Direct-service vs adapter contract tests | Remove affected tool registration |
| Live writeback reachability | Pure preview seam and absent execute tool | Call-path scan and client/network/mirror spies | Disable preview; retain staged preview/receipt |
| Audit delivery failure | Audit-health preflight + primary receipt | Receipt `audit_delivery` and health checks | Block new confirmations until healthy; preserve effects/receipt |
| Optional dependency breakage | Lazy MCP import | Base package and missing-SDK tests | Remove/disable optional entrypoint |

Rollback never deletes run artifacts, source cards, extraction cards, claim ledgers,
reports, bundles, import receipts, operation manifests, effect receipts, audit events,
or staged previews. Disable the MCP entrypoint/tool registration and leave durable
state for explicit review.

## Validation Strategy

### Focused implementation gates

```bash
./.venv/bin/python -m pytest tests/unit/test_operator_mcp_policy.py
./.venv/bin/python -m pytest tests/unit/test_operator_operation_service.py
./.venv/bin/python -m pytest tests/unit/test_operator_tool_adapters.py
./.venv/bin/python -m pytest tests/integration/test_operator_mcp_server.py
./.venv/bin/python -m pytest tests/integration/test_operator_mcp_workspace_isolation.py
./.venv/bin/python -m pytest tests/integration/test_operator_mcp_writeback_preview.py
```

### Existing-regression gates

```bash
./.venv/bin/python -m pytest tests/integration/test_agent_jobs_api.py tests/unit/test_agent_job_schemas.py tests/unit/test_agent_job_service.py
./.venv/bin/python -m pytest tests/integration/test_run_launch_reuse.py
./.venv/bin/python -m pytest tests/test_search_router_router.py
./.venv/bin/python -m pytest tests/test_schema_validation.py
./.venv/bin/python -m pytest
flake8 src/research_foundry --select=E9,F63,F7,F82
```

Exact test filenames must be reconciled against the current tree at execution; a
missing planned file is not evidence of a pass. No owner/private corpus, remote
transport, live writeback, deployment, or release test is implied by repository
fixtures.

### Contract and negative-proof gates

- Validate operation/confirmation/receipt/error schemas against golden and negative instances.
- Introspect FastMCP tools and diff against the closed inventory.
- Search registered handler call paths for CLI, shell, subprocess, accept, arbitrary dispatch, live writeback, clients, and mirrors.
- Spy on network and integration clients during preview.
- Compare exact canonical effects and terminal receipt for uninterrupted versus resumed fixtures.
- Diff disabled-mode CLI/service outputs to preserve legacy behavior.

## Documentation Finalization

P6 updates:

- `docs/user/research-foundry-operator-mcp.md`: install optional dependency, start local stdio, tool inventory, preflight/confirmation, status/cancel/resume, receipt/error interpretation, preview-only writeback, troubleshooting.
- `docs/dev/architecture/operator-mcp-governance.md`: identity/workspace/sensitivity, token binding, operation/effect receipts, AgentJob reuse, audit distinction, limits, threat boundary.
- `README.md`: concise optional local integration pointer if the exact shipped surface warrants it.
- `CHANGELOG.md` `[Unreleased]`: local Operator MCP and its preview-only limitation.
- Deferred shaping specs for remote transport and live writeback.

Documentation must link to Knowledge MCP, RPC, ERI, CARP, RAL/activation, RFUP, and
Search Router instead of copying their authority contracts. It must label remote
transport and live writeback `deferred`, and owner/private qualification
`not_executed_owner_data_absent` unless real authorized evidence exists.

## Reviewer Gates and Execution Handoff

- `task-completion-validator` reviews each phase against the exact current tree.
- `karen` reviews P2 lifecycle, P4 integrated effects, and final feature candidate.
- Security review is mandatory for P1 identity/confirmation and P5 preview-negative proof.
- A material fix, schema change, tool-registry change, generated artifact, receipt change, or docs/evidence update invalidates prior exact-tree approval.
- The integration owner serializes writes to `agent_job_service.py`, `agent_job_schemas.py`, `governance.py`, `audit_service.py`, `writeback.py`, operation registry, and server registry.
- Phase progress is initialized only after this plan and its external entry gates are approved; this package creates no progress files now.
- Implementation approval, metadata closeout, repository readiness, owner-held canary, deployment, release, remote authorization, and live writeback authorization are separate truths.
