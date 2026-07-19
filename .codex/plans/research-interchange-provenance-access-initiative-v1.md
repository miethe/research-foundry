---
schema_version: 2
doc_type: meta_plan
title: "Research Interchange, Provenance, and Access Initiative v1"
description: >-
  Workflow authority for sequencing five linked Research Foundry feature packages
  and six shaping design specs without duplicating reusable-assertion-ledger or RFUP scope.
status: draft
scope: workflow
created: 2026-07-18
updated: 2026-07-18
feature_slug: research-interchange-provenance-access-initiative
feature_version: v1
prd_ref: docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
plan_ref: null
related_documents:
  - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
  - docs/project_plans/design-specs/notebooklm-research-foundry-refresh.md
  - docs/project_plans/design-specs/browser-research-capture-extension.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
  - docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1.md
  - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/projects/research-foundry/notebooklm-integration-plan.md
owner: nick
contributors: []
priority: high
risk_level: high
affects_skills:
  - planning
  - artifact-tracking
  - dev-execution
  - research-foundry
  - research-foundry-swarm
affects_commands:
  - /dev:execute-phase
  - /plan:plan-feature
outcome: >-
  Deliver an ordered, review-gated initiative in which structured provenance remains
  authoritative, external prose remains candidate material until exact verification,
  and read-only knowledge access stays separate from privileged operator mutations.
tags:
  - meta-plan
  - initiative
  - workflow
  - provenance
  - interchange
  - mcp
  - agent-access
commit_refs: []
pr_refs: []
files_affected: []
---

# Research Interchange, Provenance, and Access Initiative v1

> This meta-plan is the execution-order authority for the initiative. It does not
> authorize implementation, replace child plans, or create progress state.

## 1. Purpose

Coordinate five independently estimated feature packages and six shaping design
specs so that new intake, provenance, catalog, and agent-access capabilities compose
with Research Foundry's existing evidence control plane.

The initiative must preserve three independent truths:

1. **Planning complete** means a child packet is internally linked and approved.
2. **Repository ready** means code and repository-owned tests passed exact-tree review.
3. **Integration qualified** means the literal external or owner-held workflow ran
   successfully with its required evidence. Repository readiness does not imply it.

## 2. Authority Hierarchy

When documents disagree, use this order:

1. Runtime code, schemas, and exact-tree validation evidence.
2. The child PRD and implementation plan for its owned boundary.
3. This meta-plan for dependency order and cross-child gates.
4. The umbrella epic for shared product intent and initiative acceptance.
5. Historical plans and design rationale.

Human briefs explain estimates and orchestration but do not override executable
contracts. Design specs at `maturity: shaping` do not authorize implementation.

## 3. Linked Artifact Manifest

| Kind | Slug / path | Authority |
|---|---|---|
| Epic | `docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md` | Shared product boundary and initiative gates |
| Child 1 | `docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md` | Origin envelope, derived facets, discovery/search receipts, canonical run envelope, inference/canonical-claim materialization, report-use edges, AOS context refs |
| Child 2 | `docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md` | `external_research_handoff/v1`, immutable import receipt, completeness tiers, exact source resolution, candidate quarantine, resumability |
| Child 3 | `docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md` | Governed pre-discovery catalog retrieval, deterministic selection/denial receipt, freshness/revalidation, gap routing |
| Child 4 | `docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md` | Exact schema-aligned core/RF reads in an independent local stdio process/registry/settings/credential/inventory boundary |
| Child 5 | `docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md` | Governed cost-bearing and mutating MCP operations, local stdio first |
| Design | `docs/project_plans/design-specs/notebooklm-research-foundry-refresh.md` | NotebookLM qualification and promotion questions only |
| Design | `docs/project_plans/design-specs/browser-research-capture-extension.md` | MV3 capture-envelope and native-messaging questions only |
| Design | `docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-transport.md` | Remote identity, transport, session, and qualification gates only |
| Design | `docs/project_plans/design-specs/research-foundry-knowledge-mcp-canonical-resource-urls.md` | Reachable canonical HTTPS namespace and migration gates only |
| Design | `docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-cache-isolation.md` | Tenant partition, timing, invalidation, and deletion gates only |
| Design | `docs/project_plans/design-specs/reusable-assertion-ledger-shared-indexes.md` | Shared-index isolation and evaluation gates only |

Expected implementation plans live under
`docs/project_plans/implementation_plans/enhancements/<child-slug>-v1.md`.
Expected human briefs live under `docs/project_plans/human-briefs/<child-slug>.md`.
Expected decisions blocks live under `.codex/worknotes/<child-slug>/decisions-block.md`.

### Current estimate rollup

| Child | Points | Final plumbing/hardening phase |
|---|---:|---:|
| Research Provenance Continuity | 40 | 6 |
| External Research Interchange | 38 | 5 |
| Catalog-Assisted Research Planning | 28 | 4 |
| Research Foundry Knowledge MCP | 34 | 5 |
| Research Foundry Operator MCP | 29 | 4 |
| **Initiative** | **169** | **24** |

H4 uses the full 169-point sum with no bundle discount. H6 reserves 24 points
against a 145-point core subtotal, or 16.6%, for final integration plumbing,
adversarial gates, generated contracts, documentation, and exact-tree evidence.

## 4. Reuse and Non-Duplication Boundary

### Reusable Assertion Ledger

Reference, do not rebuild:

- immutable source editions and exact passages,
- source assertions, evaluations, and correction/retraction lineage,
- workspace-scoped assertion catalog and search,
- reuse, freshness, impact, and reviewer contracts,
- private-first rollout and compatibility rules.

### Assertion-ledger activation

Reference, do not rebuild:

- historical backfill and forward-ingest activation,
- workspace-resolution and fail-closed write helpers,
- run-launch reuse-field threading,
- merge-UI activation and activation audit evidence.

### RFUP upstream evidence foundry

Reference, do not rebuild:

- machine-contract and schema-version stamping,
- exact-passage verification mode,
- governed URL/PDF extraction,
- council result normalization,
- run sealing and run-level lineage,
- Path-B workflow parameterization.

Any child that discovers a required change to these authorities must raise a
cross-plan finding and obtain an explicit amendment; it must not introduce a parallel
registry, verifier, source-card model, run-launch service, or schema vocabulary.

## 5. Shared Trust Boundaries

### Provenance authority

Structured origin, receipt, edition, passage, assertion, claim/inference, and
report-use records are authoritative. Tags and facets are derived indexes and cannot
substitute for those records.

### External research

Vendor reports, notebook synthesis, browser annotations, and imported claim text are
platform synthesis or assertion candidates. They remain quarantined until the
original source is re-fetched or bound to an immutable edition and the exact passage
relationship passes RF verification.

### Catalog reuse

Catalog discovery is an optimization, not a truth shortcut. Rights, sensitivity,
workspace, freshness, evaluation, retraction, and coverage decisions must be recorded
in a deterministic selection or denial receipt. Uncovered scope routes to discovery.

### Agent access

Knowledge MCP is read-only. Operator MCP and Search Router are privileged,
cost-bearing, mutating, or acquisition-capable. Knowledge runs as an independent
OS process with its own registry, entry point, settings/credential allowlist,
dependency boundary, and inventory; only governed read services are shared.
Local stdio is schema-aligned, not OpenAI/ChatGPT-compatible. Remote access stays
deferred until the transport, canonical HTTPS URL, and cache-isolation specs promote.

## 6. Dependency Waves

Critical path: existing RAL/activation/RFUP -> provenance continuity -> interchange
and catalog planning -> knowledge MCP -> operator MCP -> integration qualification.

### Wave 0 — Planning and contract freeze

- Validate the epic and each child packet strictly.
- Resolve schema ownership for origin envelopes, receipts, completeness tiers,
  canonical run/activity envelopes, report-use edges, and MCP resource identifiers.
- Keep all six design specs at `maturity: shaping`/deferred.
- No progress files or execution branches are created.

### Wave 1 — Research provenance continuity

Land the shared origin, receipt, run-envelope, inference/canonical-claim, report-use,
and AOS-context contracts first. All downstream packages consume these definitions.

### Wave 2 — External interchange and catalog planning

The interchange and catalog packages may execute in parallel after the Wave-1
contract gate. Their writers must serialize overlapping source-card, assertion,
run-launch, CLI, schema, and documentation files.

### Wave 3 — Read-only knowledge MCP

Start the independent Knowledge MCP process after provenance and catalog read
contracts stabilize. Freeze exact query/id-only core DTOs with identical
`structuredContent` and canonical-JSON text encoding; put filters, paging, receipts,
and typed reads only in separately named `rf_*` tools. Search-only activity must be
observable in the canonical run/activity envelope before this wave closes.

### Wave 4 — Governed operator MCP

Expose plan, swarm, import, verify, bundle, and job operations only through existing
governed services. Require idempotency keys, typed confirmations where appropriate,
guard checks, and preserved human-review outcomes. Remote mutations are absent.

### Wave 5 — Initiative integration and qualification

Run cross-child fixtures from external handoff through source resolution, assertion
verification, catalog reuse, report-use lineage, read-only retrieval, and governed
operator action. Record external integrations as `offline-unvalidated` until their
literal live flows succeed.

## 7. Decision Gates

| Gate | Required evidence | Blocks |
|---|---|---|
| DG-0 Planning integrity | Strict artifact validation, AC dry coverage for each child plan, path/link check, files below 800 lines, no duplicate authority | Any implementation |
| DG-1 Provenance contract | One owner for origin/receipt/run/report-use schemas; candidate-vs-authoritative states explicit; derived facets labeled | Waves 2-4 |
| DG-2 External trust | Missing/drift/mismatch/denial/replay/resume plus SSRF URL/DNS/redirect/rebinding and vendor prompt/tool/control-injection fixtures fail closed or remain inert until verified | Interchange completion |
| DG-3 Catalog safety | Eligible, stale, retracted, rights-denied, workspace-denied, low-evaluation, and coverage-gap fixtures produce deterministic receipts | Knowledge MCP catalog tools |
| DG-4 Read-only access | Exact eight-tool inventory, independent process/import/env/settings/credential boundary, core dual-encoding equality, RF-only extensions, and zero filesystem/provider/mutation effects; local profile labeled schema-aligned only | Wave 3 close |
| DG-5 Operator governance | Retry idempotency, confirmation, guard, audit, and exit-code-7 review fixtures pass; remote mutation tools are absent | Wave 4 close |
| DG-6 Integration truth | Live external qualification evidence is separated from synthetic and repository-readiness evidence | Initiative close |

Tier-3 child phases require `task-completion-validator` review at every exit and Karen
review at contract, integration, and final exact-tree milestones. A material fix
invalidates prior approval until the same reviewer checks the new tree.

## 8. Design-Spec Promotion Rules

### NotebookLM refresh

Remain shaping while the local CLI is absent and live behavior is unqualified. The
first supported route is manual deterministic export. Promotion requires current
`notebooklm source add` syntax verification, a pinned client or CLI version, a canary
track for any unofficial API, deterministic receipts, secret handling, and rollback.
The older `add-source` assumption is not copied forward.

### Browser capture extension

Remain shaping until the capture envelope, permission model, and native-host boundary
are accepted. Prefer Manifest V3 `activeTab` plus native messaging. The first release
stages a capture receipt; it does not promote page prose into source cards or
assertions automatically. Promotion requires origin hashing, sensitivity handling,
restricted-page policy, attachment limits, native-host allowlisting, and explicit
operator promotion.

### Knowledge MCP remote profile

Remote transport, canonical resource URLs, and remote cache isolation remain
shaping/deferred and promote as one compatibility profile, not independently.
Promotion requires authenticated workspace binding, an owned reachable HTTPS
endpoint, canonical URL migration/revocation semantics, tenant-safe cache
partition/invalidation/deletion, preserved exact core DTO/dual encoding, and live
hosted-client qualification. The shared-index spec remains a separate isolation and
quality gate; no remote or OpenAI/ChatGPT compatibility follows from local schemas.

## 9. Completion Rules

The initiative is complete only when:

- Each child has an approved PRD, unified plan, human brief, and decisions block.
- Child H1-H6 estimates reconcile to their task-table totals without package discount.
- Dependency waves and serialization barriers were honored.
- Every child phase has exact-tree reviewer evidence.
- Cross-child contract tests cover the full provenance chain.
- Docs, CHANGELOG, architecture references, and affected skills match runtime truth.
- Deferred items have shaping specs or explicit non-promotion rationale.
- No protected or owner-held data is claimed as executed when absent.
- No live integration is claimed from mocked, synthetic, or offline-only evidence.
- The epic and this meta-plan are updated with final commit/PR references.

Completion does not imply release, deployment, remote MCP enablement, NotebookLM live
qualification, or browser-extension distribution unless separate evidence proves it.

## 10. Explicit Next Commands

### Planning validation

```bash
.venv/bin/python .agents/skills/artifact-tracking/scripts/validate_artifact.py \
  -f docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md --strict
.venv/bin/python .agents/skills/artifact-tracking/scripts/validate_artifact.py \
  -f docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md --strict
.venv/bin/python .agents/skills/artifact-tracking/scripts/ac-coverage-report.py \
  --plan docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md --dry
git diff --check
git -c core.fsmonitor=false status --short
```

Repeat strict validation and AC dry coverage for the remaining four child packages
before approval.

### First execution handoff

After human approval of Wave 0:

```text
Skill("dev-execution")
Skill("artifact-tracking")
/dev:execute-phase 1
```

The execution prompt must name
`docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md`
and create only its Phase-1 progress tracker. Do not begin an MCP or importer phase
first.

### Design-spec follow-up

```text
Resolve NotebookLM OQs against the installed environment and current notebooklm skill.
Resolve browser-capture OQs against MV3 activeTab/native-messaging constraints.
Resolve the three Knowledge remote-profile specs together; do not claim compatibility before reachable canonical HTTPS qualification.
Advance maturity only after the promotion gates in Section 8 pass.
```

## 11. Stop Conditions

Stop and return to planning if a child needs a new evidence authority, an import loses
its receipt or locator, catalog behavior is not explainable, read-only access requires
mutation, operator access bypasses governance, remote resources require filesystem
identifiers, a shaping spec is treated as executable, or reviewer evidence names a
different tree.

## 12. Running Log

- 2026-07-18: Reviewer reconciliation locked the child rollup at 169 points
  (40 + 38 + 28 + 34 + 29), H6 at 24/145 = 16.6%, expanded external hostile-input
  gates, and separated Knowledge MCP at the process/registry/settings/credential/
  inventory layers. No implementation or remote compatibility is authorized.

**Status:** Draft. Next action: Wave-0 packet validation and human approval, not implementation.
