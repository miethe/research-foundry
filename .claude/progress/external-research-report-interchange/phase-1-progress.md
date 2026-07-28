---
type: progress
schema_version: 2
doc_type: progress
prd: external-research-report-interchange
feature_slug: external-research-report-interchange
phase: 1
title: Contract Freeze
status: completed
created: '2026-07-26'
updated: '2026-07-26'
prd_ref: docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
commit_refs: []
pr_refs: []
started: 2026-07-26T00:00Z
completed: null
overall_progress: 0
completion_estimate: on-track
total_tasks: 5
completed_tasks: 5
in_progress_tasks: 0
blocked_tasks: 0
owners:
- backend-architect
contributors:
- api-designer
- task-completion-validator
execution_model: sequential
model_usage:
  primary: sonnet
  external:
  - gpt-5.6-terra
tasks:
- id: ERI-1.1
  description: 'Packet schemas: define external_research_handoff, external_research_sources,
    external_assertion_candidates, external_research_import_receipt, external_research_import_checkpoint,
    external_research_acquisition_policy schemas plus valid/invalid golden instances;
    required members and optional activity/attachments explicit'
  status: completed
  assigned_to:
  - backend-architect
  dependencies: []
  estimated_effort: 2 pts
  assigned_model: sonnet
  model_effort: extended
  evidence:
  - note: 6 schemas + golden/negative fixtures + tests/unit/test_external_research_schemas.py
      (30 tests) authored and green; pytest -m PYTHONPATH -q passes; see phase-1a-completion.md
- id: ERI-1.2
  description: 'Identity contract: freeze packet/member/receipt/action/effect digest
    inputs, target context, safe exclusions, replay conflict behavior, directory-only
    v1 boundary (resolves ERI-OQ-1, ERI-OQ-2)'
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - ERI-1.1
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: extended
  started: 2026-07-26T17:20Z
  completed: 2026-07-26T17:38Z
  evidence:
  - doc: docs/dev/architecture/external-research-handoff-contract.md
- id: ERI-1.3
  description: 'Tier and quarantine vocabulary: freeze computed completeness tiers,
    terminal action states, safe reason codes, policy ordering, verified authority'
  status: completed
  assigned_to:
  - api-designer
  dependencies:
  - ERI-1.1
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: adaptive
  started: 2026-07-26T17:20Z
  completed: 2026-07-26T17:38Z
  evidence:
  - doc: docs/dev/architecture/external-research-handoff-contract.md
- id: ERI-1.4
  description: 'Compatibility and dependency gate: prove legacy absence is readable;
    map RPC/RFUP/RAL/intake fields without duplicate authority; select bounded configurable
    defaults or record a blocking finding (resolves ERI-OQ-3, ERI-OQ-4)'
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - ERI-1.2
  - ERI-1.3
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: extended
  started: 2026-07-26T17:20Z
  completed: 2026-07-26T17:38Z
  evidence:
  - doc: docs/dev/architecture/external-research-handoff-contract.md
- id: ERI-1.5
  description: 'Hostile-data and acquisition contract: freeze inert-data rules plus
    scheme/authority/IP/DNS/redirect/connected-peer policy, safe denial, no fallback,
    governed-local-ingest separation'
  status: completed
  assigned_to:
  - backend-architect
  dependencies:
  - ERI-1.1
  - ERI-1.3
  estimated_effort: 1 pt
  assigned_model: sonnet
  model_effort: extended
  started: 2026-07-26T17:20Z
  completed: 2026-07-26T17:38Z
  evidence:
  - doc: docs/dev/architecture/external-research-handoff-contract.md
parallelization:
  batch_1:
  - ERI-1.1
  batch_2:
  - ERI-1.2
  - ERI-1.3
  batch_3:
  - ERI-1.4
  - ERI-1.5
progress: 100
---

# Phase 1 — Contract Freeze

Freeze the `external_research_handoff/v1` packet contract, identity/digest inputs,
completeness-tier + quarantine vocabulary, dependency mapping, and the hostile-data /
SSRF-safe acquisition policy.

## Dependency note (RPC-1.G)

The plan declares `depends_on: [RPC-1.G]` (Research Provenance Continuity Phase-1
contract freeze). RPC is unexecuted (`status: draft`). Of RPC-1.G's seven schemas,
four already exist on the tree from prior features — `canonical_claim.schema.yaml`,
`inference_record.schema.yaml`, `search_request.schema.yaml`, `search_run.schema.yaml`
— and three are absent: `provenance_origin.schema.yaml`,
`research_run_envelope.schema.yaml`, `search_activity_receipt.schema.yaml`.

ERI therefore takes the ERI-1.4 escape hatch: reference the four present schemas
directly, and define the seam to the three absent ones as **optional and
forward-compatible** (nullable refs, no ERI-side duplicate authority, no invented
RPC field semantics). This is recorded as a finding, not a silent assumption.
