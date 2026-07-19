---
title: "Implementation Plan: External Research Report Interchange"
schema_version: 2
doc_type: implementation_plan
status: draft
created: 2026-07-18
updated: 2026-07-18
feature_slug: external-research-report-interchange
feature_version: v1
tier: 3
prd_ref: docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
plan_ref: null
human_brief_ref: docs/project_plans/human-briefs/external-research-report-interchange.md
scope: "Define external_research_handoff/v1, stage platform synthesis and candidate evidence with immutable receipts, resolve citations through RFUP/RAL, quarantine incomplete material, and resume bounded large-report imports."
effort_estimate: "38 pts bottom-up"
architecture_summary: "Versioned hostile-input packet -> safe manifest/staging -> inert vendor-data normalization -> immutable receipts -> hard SSRF-safe pre-effect gate -> RFUP acquisition -> RAL edition/passage resolution -> quarantine or explicit verification promotion -> resumable CLI/provenance export."
related_documents:
  - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
  - docs/project_plans/human-briefs/external-research-report-interchange.md
  - .codex/worknotes/external-research-report-interchange/decisions-block.md
  - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
  - .codex/plans/research-interchange-provenance-access-initiative-v1.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
  - docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1.md
  - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/project_plans/feature_contracts/features/intake-citation-adapters.md
references:
  user_docs: []
  context: []
  specs:
    - .agents/skills/planning/references/ac-schema.md
    - .agents/skills/planning/references/deferred-items-and-findings.md
    - .claude/specs/changelog-spec.md
    - schemas/source_card.schema.yaml
    - schemas/source_edition.schema.yaml
    - schemas/passage.schema.yaml
    - schemas/source_assertion.schema.yaml
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
tags: [implementation, planning, external-research, interchange, receipts, quarantine, resumability]
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - schemas/external_research_handoff.schema.yaml
  - schemas/external_research_sources.schema.yaml
  - schemas/external_assertion_candidates.schema.yaml
  - schemas/external_research_import_receipt.schema.yaml
  - schemas/external_research_import_checkpoint.schema.yaml
  - templates/external_research_handoff/v1/
  - src/research_foundry/services/external_research_interchange.py
  - src/research_foundry/services/external_research_resolution.py
  - src/research_foundry/services/source_cards.py
  - src/research_foundry/services/assertion_registry.py
  - src/research_foundry/services/export_service.py
  - src/research_foundry/cli_commands.py
  - tests/fixtures/external_research_handoff/
  - tests/integration/test_external_research_interchange.py
open_questions:
  - id: ERI-OQ-1
    status: open
    question: "Confirm materialized-directory-only transport for v1."
  - id: ERI-OQ-2
    status: open
    question: "Freeze packet/receipt identity inputs and safe exclusions."
  - id: ERI-OQ-3
    status: open
    question: "Confirm staging-only behavior when target_run_id is absent."
  - id: ERI-OQ-4
    status: open
    question: "Select conservative configurable member, byte, attachment, source, candidate, and batch limits."
wave_plan:
  serialization_barriers:
    - schemas/external_research_handoff.schema.yaml
    - schemas/external_research_import_receipt.schema.yaml
    - src/research_foundry/services/external_research_interchange.py
    - src/research_foundry/services/source_cards.py
    - src/research_foundry/services/assertion_registry.py
    - src/research_foundry/cli_commands.py
    - CHANGELOG.md
    - README.md
  phases:
    - id: P1
      depends_on: [RPC-1.G]
      isolation: shared
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - schemas/external_research_handoff.schema.yaml
        - schemas/external_research_sources.schema.yaml
        - schemas/external_assertion_candidates.schema.yaml
        - schemas/external_research_import_receipt.schema.yaml
        - schemas/external_research_import_checkpoint.schema.yaml
        - schemas/external_research_acquisition_policy.schema.yaml
    - id: P2
      depends_on: [P1]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - src/research_foundry/services/external_research_interchange.py
        - tests/unit/test_external_research_interchange.py
    - id: P3
      depends_on: [P1]
      isolation: worktree
      parallelizable: true
      owner_skills: []
      model: haiku
      effort: adaptive
      files_affected:
        - templates/external_research_handoff/v1/
        - tests/fixtures/external_research_handoff/
    - id: P4
      depends_on: [P2]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - src/research_foundry/services/external_research_resolution.py
        - src/research_foundry/services/source_acquisition_policy.py
        - src/research_foundry/services/source_cards.py
        - src/research_foundry/services/assertion_registry.py
        - tests/integration/test_external_research_resolution.py
    - id: P5
      depends_on: [P3, P4]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      files_affected:
        - src/research_foundry/services/external_research_interchange.py
        - src/research_foundry/services/export_service.py
        - src/research_foundry/cli_commands.py
        - tests/integration/test_external_research_interchange.py
    - id: P6
      depends_on: [ERI-5.G]
      isolation: shared
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: adaptive
      files_affected:
        - tests/fixtures/external_research_handoff/
        - tests/integration/test_external_research_interchange.py
        - docs/dev/architecture/external-research-handoff-contract.md
        - docs/user/external-research-interchange.md
        - .agents/skills/research-foundry/SKILL.md
        - README.md
        - CHANGELOG.md
  waves:
    - [P1]
    - [P2, P3]
    - [P4]
    - [P5]
    - [P6]
---

# Implementation Plan: External Research Report Interchange

**Plan ID**: `IMPL-2026-07-18-EXTERNAL-RESEARCH-REPORT-INTERCHANGE`
**Date**: 2026-07-18
**Author**: Codex implementation-planning worker
**Human Brief**: `docs/project_plans/human-briefs/external-research-report-interchange.md`
**Complexity**: Large / Tier 3
**Total Estimated Effort**: 38 story points
**Execution Status**: Not authorized; no progress artifacts exist for this plan

## Executive Summary

Implement one file-canonical interchange path for externally produced reports. The sequence freezes packet and receipt contracts, builds hostile-input-safe staging, ships offline producer profiles, resolves sources and exact citations through existing RFUP/RAL services, adds deterministic large-packet orchestration, and closes with adversarial validation and user-facing documentation.

`report.md` stays `platform_synthesis`; assertion candidates stay quarantined until exact source-edition/passage resolution and existing RF verification permit promotion. The plan introduces no URL/PDF extractor, vendor API client, fuzzy matcher, new ledger, automatic run creation, remote transport, or MCP tool.

## Implementation Strategy

### Architecture sequence

1. **Contract**: freeze schemas, identity, tiers, reason codes, legacy behavior, target context, hostile-data boundary, and SSRF-safe acquisition prerequisite.
2. **Staging**: inspect the directory safely, stream hashes, publish immutable manifests/effects, and maintain separate checkpoints.
3. **Producer profiles**: map five prompt/output profiles into the same offline packet contract; prove injection-shaped vendor fields remain inert data.
4. **Resolution**: normalize citation tuples, pass the hard URL/DNS/redirect/peer gate, call RFUP acquisition, reuse RAL registry identity, and quarantine or stage for verification.
5. **Orchestration**: execute stable action batches, resume interruptions, expose CLI/machine output, and project provenance to a target run only when explicit.
6. **Hardening**: prove cross-profile, adversarial, compatibility, privacy, limit, and resume behavior; finalize docs against the exact tree.

### Critical path

Research Provenance Continuity `RPC-1.G` → ERI P1 → P2 → P4 → P5 → P6.

P3 can run beside P2 after the generic schema freezes. P3 and P4 must both merge before P5 because CLI behavior and large-packet fixtures depend on profile outputs and resolution outcomes.

### Phase summary

| Phase | Title | Estimate | Target subagent(s) | Model(s) | Notes |
|---|---|---:|---|---|---|
| P1 | Contract Freeze | 6 pts | backend-architect, api-designer | sonnet | Karen contract milestone; hostile-data/acquisition policy |
| P2 | Staging and Receipts | 6 pts | python-backend-engineer | sonnet | Hostile input and idempotency |
| P3 | Producer Profiles | 6 pts | documentation-writer, python-backend-engineer | haiku + sonnet | Offline templates plus injection fixtures |
| P4 | Resolution and Promotion | 9 pts | backend-architect, python-backend-engineer | sonnet | H3 exact resolution + SSRF-safe acquisition gate |
| P5 | Resumable Importer | 6 pts | python-backend-engineer, api-designer | sonnet | H3 state machine and CLI |
| P6 | Hardening and Docs | 5 pts | validation implementer, documentation-writer | sonnet + haiku | Final exact-tree gates |
| **Total** | — | **38 pts** | — | — | — |

Estimation rationale and the mandatory H1-H6 derivation live in the Human Brief. Phase/task estimates below sum to 38 points without package discount.

## Deferred Items and In-Flight Findings Policy

### Deferred items

| Item ID | Category | Reason deferred | Trigger for promotion | Target spec path |
|---|---|---|---|---|
| ERI-DF-1 | research | Live provider automation adds secrets, cost, SDK drift, and vendor terms | Approved provider contract, live canary, rollback, secret owner | `docs/project_plans/design-specs/external-research-provider-automation.md` |
| ERI-DF-2 | design | Archive/remote transports add extraction, upload, auth, and path threats | Accepted threat model and concrete transfer requirement | `docs/project_plans/design-specs/external-research-transport-containers.md` |
| ERI-DF-3 | research | Fuzzy matching cannot establish exact passage identity safely | Measured unresolved need plus labeled evaluation corpus | `docs/project_plans/design-specs/external-research-citation-recovery.md` |
| ERI-DF-4 | policy | Public/cross-workspace exchange needs independent rights/sensitivity promotion | Rights review and tenant-safe resource identities | `docs/project_plans/design-specs/external-research-public-interchange.md` |

P6 task `ERI-6.4` authors each still-promotable shaping spec and appends it to `deferred_items_spec_refs`, or records why a row is not promoted. NotebookLM live qualification belongs to the initiative's dedicated refresh design spec and is not duplicated here.

### In-flight findings

Do not pre-create a findings document. On the first real plan/reality mismatch, create `.claude/findings/external-research-report-interchange-findings.md`, set `findings_doc_ref`, and link it here. Load-bearing findings receive their own design spec through `ERI-6.4`. Finalization cannot close while an existing findings doc remains draft.

## Phase Breakdown

### Phase 1 — Contract Freeze (6 pts)

**Dependencies**: Research Provenance Continuity `RPC-1.G` accepted; RAL/RFUP/Intake Citation Adapter contracts inspected against the exact tree.
**Integration owner**: backend-architect
**Exit reviewers**: api-designer, task-completion-validator, Karen

| Task ID | Task | Deliverable and acceptance | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| ERI-1.1 | Packet schemas | Define handoff, source, candidate, receipt, and checkpoint schemas plus valid/invalid golden instances; required members and optional activity/attachments are explicit. | 2 pts | backend-architect, api-designer | sonnet | extended | RPC-1.G |
| ERI-1.2 | Identity contract | Freeze packet/member/receipt/action/effect digest inputs, target context, safe exclusions, replay conflict behavior, and directory-only v1 boundary. | 1 pt | backend-architect | sonnet | extended | ERI-1.1 |
| ERI-1.3 | Tier and quarantine vocabulary | Freeze computed completeness tiers, terminal action states, safe reason codes, policy ordering, and verified authority. | 1 pt | api-designer | sonnet | adaptive | ERI-1.1 |
| ERI-1.4 | Compatibility and dependency gate | Prove legacy absence is readable; map RPC/RFUP/RAL/intake fields without duplicate authority; select bounded configurable defaults or record a blocking finding. | 1 pt | backend-architect, task-completion-validator | sonnet | extended | ERI-1.2, ERI-1.3 |
| ERI-1.5 | Hostile-data and acquisition contract | Freeze inert-data rules plus scheme/authority/IP/DNS/redirect/connected-peer policy, safe denial, no fallback, and governed-local-ingest separation. | 1 pt | backend-architect, api-designer | sonnet | extended | ERI-1.1, ERI-1.3 |

**Quality gate**:

- Required/optional member schemas reject unsafe or ambiguous contract states.
- Producer-declared completeness cannot set computed or verified state.
- No schema defines a second edition, passage, source assertion, extraction, or citation-tuple authority.
- All vendor fields are untrusted data; no field may become a prompt/tool description, route/control value, command, schema selector, or execution argument.
- Acquisition cannot begin until scheme, host, every DNS answer, every redirect, and the connected peer pass the forbidden-address policy.
- A material contract fix reruns task-completion-validator and Karen against the new tree.

### Phase 2 — Staging and Immutable Receipts (6 pts)

**Dependencies**: P1 approved.
**Integration owner**: python-backend-engineer
**Exit reviewer**: task-completion-validator

| Task ID | Task | Deliverable and acceptance | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| ERI-2.1 | Safe packet inspection | Validate containment, regular files, declared members, byte/count limits, schema versions, and streaming member hashes before effects. | 2 pts | python-backend-engineer | sonnet | extended | ERI-1.4 |
| ERI-2.2 | Stable staging manifest | Persist immutable packet/action manifest and workspace/target-scoped receipt identity using atomic publication; synthesis bytes remain governed artifacts. | 2 pts | python-backend-engineer | sonnet | extended | ERI-2.1 |
| ERI-2.3 | Effects and terminal receipt | Write immutable per-action effects, separate atomic checkpoints, and an immutable terminal receipt whose counts reconcile to exact actions. | 1 pt | python-backend-engineer | sonnet | extended | ERI-2.2 |
| ERI-2.4 | Replay, conflict, and dry-run | Exact replay returns the same terminal receipt; changed/conflicting manifests deny; dry-run reports safe planned actions with zero canonical effects. | 1 pt | python-backend-engineer | sonnet | adaptive | ERI-2.3 |

**Quality gate**:

- Traversal, symlink, special-file, undeclared-member, oversize, and digest-conflict fixtures block before effects.
- Faults between manifest, effect, checkpoint, and terminal publication have deterministic recovery.
- CLI-safe DTOs omit raw report/source/candidate text and private absolute paths.

### Phase 3 — Producer Prompt/Output Profiles (6 pts)

**Dependencies**: P1 approved. May execute beside P2 with profile-specific ownership.
**Integration owner**: documentation-writer for prompts; python-backend-engineer for fixtures
**Exit reviewer**: task-completion-validator

| Task ID | Task | Deliverable and acceptance | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| ERI-3.1 | Generic profile | Canonical prompt, four required file templates, optional-member examples, unknown-field rules, and schema-valid fixture. | 1 pt | documentation-writer, python-backend-engineer | sonnet | adaptive | ERI-1.4 |
| ERI-3.2 | ChatGPT profile | Manual prompt/output mapping with packet-local citation/source IDs and no API/session scraping; fixture round-trips. | 1 pt | documentation-writer | haiku | adaptive | ERI-3.1 |
| ERI-3.3 | Perplexity profile | Map citations/search-results metadata into canonical records plus namespaced extensions; ranking remains non-authoritative. | 1 pt | documentation-writer | haiku | adaptive | ERI-3.1 |
| ERI-3.4 | Gemini profile | Map answer spans and grounding/source references without Google API coupling; fixture preserves unknowns. | 1 pt | documentation-writer | haiku | adaptive | ERI-3.1 |
| ERI-3.5 | NotebookLM profile | Manual deterministic notebook synthesis/source export with `offline-unvalidated` label and no live CLI/API assumption. | 1 pt | documentation-writer | haiku | adaptive | ERI-3.1 |
| ERI-3.6 | Injection-shaped profile fixtures | Add report/source/candidate/activity/extension strings that imitate prompt overrides, tool calls/descriptions, route/schema selectors, commands, and path arguments; prove normalization/rendering leaves them inert escaped data. | 1 pt | python-backend-engineer | sonnet | extended | ERI-3.2..3.5, ERI-1.5 |

**Quality gate**:

- Five fixtures normalize through one generic schema and deterministic member order.
- Prompts prohibit invented locators, dates, authors, quotations, or verified labels.
- No provider credential, SDK, live endpoint, browser automation, or unofficial API appears.
- Injection-shaped vendor values remain data and cannot alter prompts, tools/resources, routing, schema selection, commands, or execution arguments.

### Phase 4 — Exact Resolution, Quarantine, and Promotion (9 pts)

**Dependencies**: P2 approved; P3 fixtures available for integration testing.
**Integration owner**: python-backend-engineer
**Exit reviewers**: task-completion-validator, Karen

| Task ID | Task | Deliverable and acceptance | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| ERI-4.1 | Citation/source normalization | Convert packet records and optional intake citation tuples into typed inert-data candidates while preserving packet IDs and namespaced extensions without control-surface promotion. | 2 pts | python-backend-engineer | sonnet | adaptive | ERI-2.4, ERI-3.6 |
| ERI-4.2 | SSRF-safe governed acquisition gate | Apply authorization/sensitivity/rights first; reject unauthorized local/file/non-HTTP, embedded-credential, loopback/private/reserved/link-local/multicast/unspecified/metadata and encoded-host targets; validate every DNS answer, bind and verify the connected peer, cap/revalidate redirects, and prohibit transport fallback before calling RFUP. | 4 pts | backend-architect, python-backend-engineer | sonnet | extended | ERI-4.1, ERI-1.5 |
| ERI-4.3 | Exact passage and quarantine resolver | Resolve quote/selector against the bound edition; unique exact match advances, zero/multiple/drift/conflict/policy failures quarantine with safe reasons. | 2 pts | python-backend-engineer | sonnet | extended | ERI-4.2 |
| ERI-4.4 | Explicit promotion seam | Stage passage-resolved candidates for existing RF verification/materialization; verified status requires accepted claim relationship and durable assertion refs. | 1 pt | python-backend-engineer | sonnet | extended | ERI-4.3 |

**Required H3 scenarios**:

- existing exact edition; newly acquired edition; unavailable locator; missing rights; sensitivity denial;
- unauthorized local/file; IPv4/IPv6 loopback/private/reserved/link-local/metadata; encoded host; mixed DNS answers; rebinding peer; public-to-private redirect; redirect loop/limit;
- unique quote; zero match; multiple match; drift; vendor-provided ID conflict;
- one candidate with many sources; many candidates sharing a source; partial basis; invalid relation;
- verification pass/fail; cross-workspace lookup; interrupted acquisition; exact replay.

**Quality gate**:

- Resolver never performs direct HTTP/PDF/HTML/OCR extraction.
- RFUP is never called until the full scheme/host/DNS/address/redirect/peer policy passes; every hop is revalidated and a failed hop has no fallback.
- Policy checks precede lookup and reveal no denied IDs, text, counts, or timing-sensitive distinctions in safe outputs.
- `report.md` content cannot enter source-card, claim, or assertion writers.

### Phase 5 — Resumable Importer and CLI (6 pts)

**Dependencies**: P3 and P4 approved.
**Integration owner**: python-backend-engineer
**Exit reviewers**: api-designer, task-completion-validator, Karen

| Task ID | Task | Deliverable and acceptance | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| ERI-5.1 | Deterministic action orchestration | Build sorted bounded actions from the canonical manifest, validate exact action/effect equality, and resume at the first incomplete action. | 2 pts | python-backend-engineer | sonnet | extended | ERI-4.4 |
| ERI-5.2 | Chunking and cancellation | Stream/hash packet members, process configurable source/candidate batches, preserve pending checkpoint on cancellation, and enforce resource limits. | 2 pts | python-backend-engineer | sonnet | extended | ERI-5.1 |
| ERI-5.3 | CLI and machine output | Add `rf intake external-report` with workspace, optional run, dry-run, resume, limit, and JSON/YAML-safe output; no-run is staging-only. | 1 pt | python-backend-engineer, api-designer | sonnet | adaptive | ERI-5.2 |
| ERI-5.4 | Provenance/export seam | Record the RPC import context and safe receipt reference in explicit target-run/export activity; preserve legacy output and expose a service seam for future Operator MCP. | 1 pt | python-backend-engineer | sonnet | adaptive | ERI-5.3 |
| ERI-5.G | Exact-tree importer gate | `task-completion-validator` then Karen APPROVE the same exact complete P5 importer, receipt/checkpoint, CLI, provenance/export, and Operator-MCP seam tree; material changes invalidate both verdicts. | gate | task-completion-validator, Karen | sonnet/opus | extended | ERI-5.4 |

**Quality gate**:

- Interrupted and uninterrupted runs over the same packet converge to a byte-identical terminal receipt and canonical effects.
- Truncated, extra, duplicate, reordered, wrong-target, and semantically impossible receipt/checkpoint fixtures deny.
- No target run means no run creation or run-local projection; import staging still completes truthfully.
- Machine output reports safe IDs/counts/reasons/cursor only.
- `task-completion-validator` then Karen APPROVE the same exact P5 tree; any material change invalidates both verdicts and reruns the gate.

### Phase 6 — Hardening, Documentation, and Exact-Tree Closeout (5 pts)

**Dependencies**: `ERI-5.G` approved on the exact P5 tree.
**Integration owner**: validation implementer
**Exit reviewers**: task-completion-validator, then Karen

| Task ID | Task | Deliverable and acceptance | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---|---|---|---:|---|---|---|---|
| ERI-6.1 | Cross-profile contracts and compatibility | Run five profile round-trips, schema golden/negative tests, legacy run/source/assertion reads, and a duplicate-authority/tree scan. | 1 pt | python-backend-engineer | sonnet | adaptive | ERI-5.G |
| ERI-6.2 | Adversarial trust matrix | Exercise unsafe members, all SSRF/address/DNS/redirect/rebinding cases, injection-shaped vendor fields, policy denials, drift, ambiguity, mismatch, partial basis, verification failure, replay conflict, and redaction. | 1 pt | python-backend-engineer | sonnet | extended | ERI-6.1 |
| ERI-6.3 | Large-report resume and limits | Run boundary/fault tests across batches and publication points; record representative elapsed/memory evidence without production claims. | 1 pt | python-backend-engineer | sonnet | extended | ERI-6.2 |
| ERI-6.4 | Docs, skill, CHANGELOG, and deferred specs | Update architecture/user guide, README command inventory, Research Foundry skill route, CHANGELOG, examples, findings, and promotable deferred specs. | 1 pt | documentation-writer, changelog-generator | haiku | adaptive | ERI-6.3 |
| ERI-6.5 | AC evidence and final reviewers | Map ERI-AC-1..7 to exact results, run focused/full relevant gates, verify docs/runtime parity, and obtain exact-tree task-completion-validator then Karen passes. | 1 pt | task-completion-validator, Karen | opus | extended | ERI-6.4 |

**Quality gate**:

- No required test is replaced by prose, a schema-only fixture, or a synthetic/live qualification claim.
- Generated or documentation fixes invalidate prior final approval and rerun the same reviewer on the new exact tree.
- Final evidence distinguishes repository-ready, offline-unvalidated vendor profiles, owner/private qualification, deployment, and release.

## Structured Acceptance Criteria

#### AC ERI-1: One packet contract covers five producer profiles
- target_surfaces:
    - schemas/external_research_handoff.schema.yaml
    - schemas/external_research_sources.schema.yaml
    - schemas/external_assertion_candidates.schema.yaml
    - templates/external_research_handoff/v1/
- propagation_contract: Each profile emits the same required packet members and canonical packet-local IDs; vendor-specific data survives only inside namespaced extensions.
- resilience: Missing members, unsafe paths, unknown major versions, or undeclared attachments block before effects; unknown nullable metadata is never invented.
- visual_evidence_required: false
- verified_by: [ERI-6.1, ERI-6.5]

#### AC ERI-2: Import receipt is immutable and replay-idempotent
- target_surfaces:
    - schemas/external_research_import_receipt.schema.yaml
    - schemas/external_research_import_checkpoint.schema.yaml
    - src/research_foundry/services/external_research_interchange.py
- propagation_contract: Canonical packet bytes and target context derive stable receipt/action identities; immutable effects reconcile into one immutable terminal receipt while checkpoints remain separate.
- resilience: Changed/conflicting manifests, missing effects, wrong target, or impossible terminal states deny without duplicate canonical writes.
- visual_evidence_required: false
- verified_by: [ERI-6.2, ERI-6.5]

#### AC ERI-3: Completeness and quarantine remain explicit
- target_surfaces:
    - schemas/external_research_import_receipt.schema.yaml
    - src/research_foundry/services/external_research_resolution.py
    - src/research_foundry/services/export_service.py
- propagation_contract: Each source/candidate receives one computed completeness tier and terminal outcome; aggregate tier/reason counts derive from the exact action set.
- resilience: Unresolved, ambiguous, drifted, sensitive, rights-missing, cross-workspace, or verification-failed items remain quarantined with safe reason codes and no text leakage.
- visual_evidence_required: false
- verified_by: [ERI-6.2, ERI-6.5]

#### AC ERI-4: Promotion requires exact existing evidence authority
- target_surfaces:
    - src/research_foundry/services/external_research_resolution.py
    - src/research_foundry/services/source_cards.py
    - src/research_foundry/services/assertion_registry.py
    - src/research_foundry/services/assertion_materialization.py
- propagation_contract: RFUP acquisition yields or reuses a source card/edition, RAL binds a unique exact passage, and existing verification/materialization alone advances the candidate to verified lineage.
- resilience: Platform synthesis, vendor IDs, a newer edition, fuzzy similarity, or partial basis cannot bypass revalidation and remain candidate/quarantined.
- visual_evidence_required: false
- verified_by: [ERI-6.2, ERI-6.5]

#### AC ERI-5: Large imports resume without repeated effects
- target_surfaces:
    - src/research_foundry/services/external_research_interchange.py
    - src/research_foundry/cli_commands.py
    - tests/integration/test_external_research_interchange.py
- propagation_contract: A deterministic bounded action manifest, immutable effect receipts, and atomic checkpoints permit retry to resume at the first incomplete action and converge with uninterrupted execution.
- resilience: Cancellation remains pending; truncated, extra, duplicate, reordered, oversize, or corrupted histories fail closed and never publish false completion.
- visual_evidence_required: false
- verified_by: [ERI-6.3, ERI-6.5]

#### AC ERI-6: Legacy and authority boundaries remain intact
- target_surfaces:
    - src/research_foundry/services/external_research_interchange.py
    - src/research_foundry/services/external_research_resolution.py
    - src/research_foundry/services/search_router/router.py
    - src/research_foundry/services/assertion_registry.py
    - src/research_foundry/cli_commands.py
- propagation_contract: The importer calls existing RFUP/RAL/public service seams, adds optional provenance/CLI output, and leaves legacy runs/source cards/assertion records readable.
- resilience: No new URL/PDF/HTML/OCR extractor, live provider dependency, auto-created run, remote transport, or MCP tool is present; absent target context remains staging-only.
- visual_evidence_required: false
- verified_by: [ERI-6.1, ERI-6.2, ERI-6.5]

#### AC ERI-7: Acquisition and vendor fields remain hostile-input safe
- target_surfaces:
    - schemas/external_research_acquisition_policy.schema.yaml
    - src/research_foundry/services/source_acquisition_policy.py
    - src/research_foundry/services/external_research_resolution.py
    - templates/external_research_handoff/v1/
    - tests/integration/test_external_research_resolution.py
- propagation_contract: Authorization and the full scheme/authority/IP/DNS/redirect/connected-peer policy pass before RFUP acquisition; packet and vendor-extension values remain inert escaped data through normalization and rendering.
- resilience: Unauthorized local/file, loopback/private/reserved/link-local/metadata, encoded-host, mixed-DNS, rebinding, redirect-pivot, and prompt/tool/control-injection fixtures fail closed or remain inert without network effects, transport fallback, or control-surface mutation.
- visual_evidence_required: false
- verified_by: [ERI-6.2, ERI-6.5]

## Risk, Rollback, and Containment

| Risk | Detection | Rollback / containment |
|---|---|---|
| Citation laundering | Negative report-to-claim and candidate-without-passage fixtures | Disable promotion seam; retain immutable staging/receipt for audit |
| Unsafe packet member | Traversal/symlink/special/oversize fixtures | Reject packet before effects; do not auto-clean external input |
| Identity/replay flaw | Golden digests, import-twice, conflicting-manifest tests | Disable importer entrypoint; canonical RAL records remain independently valid |
| Cross-workspace leak | Two-workspace denial, count, response, and safe-log tests | Remove external resolution route; preserve existing RAL/RFUP services |
| Resolver misbinding | Exact/zero/multiple/drift/version-conflict matrix | Quarantine all unresolved candidates; no fuzzy fallback |
| Resource exhaustion | Member/byte/batch boundary and memory observations | Lower configurable limits; leave receipt pending/blocked truthfully |
| Provider template drift | Five offline fixture round-trips | Fall back to generic profile; vendor overlays remain non-authoritative docs |
| SSRF or DNS/redirect rebinding | Forbidden-address, mixed-answer, peer-mismatch, and redirect-pivot fixtures with RFUP-call spy | Disable acquisition seam; retain locator-only quarantine; never weaken to fallback transport |
| Prompt/tool/control injection from vendor data | Injection strings across every member/profile and snapshots of prompts/tool inventory/routes | Reject control-surface promotion; retain only escaped inert data or quarantine item |

No rollback deletes source editions, passages, terminal receipts, or audit records. Disable the importer/CLI entrypoint and leave canonical artifacts for explicit review.

## Documentation Finalization

P6 updates only after runtime behavior freezes:

- `CHANGELOG.md`: user-facing external report intake command and trust boundary.
- `README.md`: concise command inventory and link to the user guide.
- `docs/user/external-research-interchange.md`: packet creation, profiles, dry-run/import/resume, tiers, quarantine, troubleshooting.
- `docs/dev/architecture/external-research-handoff-contract.md`: identity, receipts/checkpoints, authority, security, and compatibility.
- `.agents/skills/research-foundry/SKILL.md`: route external report intake to the new CLI/service without embedding full contract prose.
- Template examples: public-safe generic packet and machine receipt output.

No new top-level context file is warranted. If implementation changes a durable architecture invariant, add a concise pointer to the nearest existing context surface after review.

## Validation Commands

Focused implementation gates (exact file names may be finalized during execution):

```bash
./.venv/bin/python -m pytest tests/unit/test_external_research_interchange.py
./.venv/bin/python -m pytest tests/integration/test_external_research_resolution.py tests/integration/test_external_research_interchange.py
./.venv/bin/python -m pytest tests/unit/test_assertion_registry.py tests/unit/test_source_cards_ingest.py tests/test_schema_validation.py
./.venv/bin/python -m ruff check src/research_foundry tests
./.venv/bin/python -m mypy src/research_foundry --ignore-missing-imports
./.venv/bin/python -m research_foundry intake external-report tests/fixtures/external_research_handoff/generic-valid --workspace test --dry-run
```

Planning artifact gates:

```bash
./.venv/bin/python .agents/skills/artifact-tracking/scripts/validate_artifact.py --file docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md --artifact-type prd --strict
./.venv/bin/python .agents/skills/artifact-tracking/scripts/validate_artifact.py --file docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md --artifact-type implementation-plan --strict
./.venv/bin/python .agents/skills/artifact-tracking/scripts/validate_artifact.py --file docs/project_plans/human-briefs/external-research-report-interchange.md --artifact-type human-brief --strict
./.venv/bin/python .agents/skills/artifact-tracking/scripts/ac-coverage-report.py --plan docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md --dry
git diff --check
```

## Reviewer and Closeout Contract

- Every phase requires exact-tree `task-completion-validator` approval.
- Karen reviews P1 contracts, P4/P5 integration milestones, and the final exact tree.
- A material schema, identity, action ordering, policy order, resolver, generated output, or documentation fix invalidates the relevant approval.
- P4 cannot pass with only schema fixtures; it needs runtime resolution and quarantine evidence.
- P5 cannot pass without cancellation/interruption and corrupted-history tests.
- P6 cannot claim live vendor qualification from offline fixtures or repository readiness from planning validation.
- No commit, staging, merge, progress-file creation, provider call, external writeback, deploy, release, or MCP publication is authorized by this plan.
