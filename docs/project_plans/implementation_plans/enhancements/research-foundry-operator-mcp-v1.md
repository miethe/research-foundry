---
title: "Implementation Plan: Research Foundry Operator MCP"
schema_version: 2
doc_type: implementation_plan
status: in_progress
created: 2026-07-18
updated: 2026-07-30
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
  - docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1/phases-1-2-executed-record.md
  - docs/project_plans/human-briefs/operator-mcp-p1-execution-retro.md
  - docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md
  - docs/project_plans/human-briefs/research-foundry-operator-mcp.md
  - .codex/worknotes/research-foundry-operator-mcp/decisions-block.md
  - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
  - .codex/plans/research-interchange-provenance-access-initiative-v1.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/enhancements/research-foundry-knowledge-mcp-v1.md
  - docs/project_plans/design-specs/research_foundry_search_router_spec.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
references:
  user_docs: []
  context: []
  specs:
    - .claude/skills/planning/references/plan-doctrine.md
    - .claude/skills/planning/references/ac-schema.md
    - .claude/skills/dev-execution/references/execution-doctrine.md
    - .claude/specs/changelog-spec.md
    - schemas/research_brief.schema.yaml
    - schemas/swarm_plan.schema.yaml
    - schemas/source_card.schema.yaml
    - schemas/claim_ledger.schema.yaml
    - schemas/evidence_bundle.schema.yaml
spike_ref: null
adr_refs: []
deferred_items_spec_refs:
  - docs/project_plans/design-specs/operator-mcp-remote-transport-shaping.md
  - docs/project_plans/design-specs/operator-mcp-live-writeback-shaping.md
findings_doc_ref: .claude/findings/research-foundry-operator-mcp-findings.md
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
tags: [implementation, mcp, operator, governance, jobs, receipts, local-stdio, retro-remediated, gate-economics, milestone-retrofit]
milestone: null
# Sizes AGENT CONTEXT, not behavior (plan-doctrine.md § Context class). Dominant class for the
# remaining milestones: cross-module in one repo, adversarially gated, on declared serialization
# barriers. M3 is the C4 outlier — see its per-milestone note.
context_class: C3
# CONSTRAINTS, never model ids — `delegation-router` resolves provider+model at dispatch time
# against the live registry. Applies to M1-M3 only; P1/P2 finish under their authored pins.
routing_constraints:
  - "Confirmation/authorization semantics and the writeback-preview negative proof MUST stay claude-primary — never offload, at any milestone."
  - "Every adversarial security lens (M2 preview proof, M3 AC OPM-1/2/3 matrices) MUST stay claude-primary and MUST run on fresh context, never the implementer's session."
  - "Cross-model offload is unavailable for this workstream's security lenses: codex exec refused the adversarial-audit framing under its safety classifier. Do not re-attempt (see Field Notes)."
  - "Mechanical work is offload-eligible: swarm-service extraction (M1), fixture assembly (M3), docs + CHANGELOG + deferred shaping specs (M3)."
  - "Capability bar — M1: workhorse-class, parity-test-driven. M2: frontier-class for the preview negative proof; workhorse for scaffold/packaging. M3: frontier-class for the final exact-tree verdict; economy-class for docs."
  - "Reviewers get findings-ledger write access ONLY (no source, no tests); the ledger must not round-trip through the orchestrator context."
commit_refs: [41bcafb, f1bfa39, 725faba, 61c3691]
pr_refs: ["https://github.com/miethe/research-foundry/pull/7"]
files_affected:
  - schemas/operator_mcp_operation.schema.yaml
  - schemas/operator_mcp_confirmation.schema.yaml
  - schemas/operator_mcp_receipt.schema.yaml
  - schemas/operator_mcp_error.schema.yaml
  - src/research_foundry/services/operator_mcp_policy.py
  - src/research_foundry/services/operator_operation_service.py
  - src/research_foundry/services/operator_mcp_adapters/
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
# Resolved against the SkillMeat enterprise catalog 2026-07-30. All entries are `available`
# (in-catalog; the dev-execution provisioning gate deploys any that are absent on-disk), so no
# batch_0 authoring task and no named blocker is required before M1.
# NOTE: `skillmeat show <name> --type agent` reports not-found for these; `skillmeat search` finds
# them. Use search to resolve, and be aware `skillmeat list` currently 401s against the node API.
required_artifacts:
  - {type: agent, name: python-backend-engineer, skillmeat_ref: python-backend-engineer, status: available, lifecycle: permanent, scope: null, note: "M1/M2 adapter + server implementation"}
  - {type: agent, name: api-designer, skillmeat_ref: api-designer, status: available, lifecycle: permanent, scope: null, note: "M2 tool registry + error mapping. On-disk already. WARNING: /dev:execute-plan has been observed silently skipping non-roster agents such as api-designer as HITL — confirm it is dispatched, do not assume"}
  - {type: agent, name: senior-code-reviewer, skillmeat_ref: senior-code-reviewer, status: available, lifecycle: permanent, scope: null, note: "M2 preview negative-proof call-path scan"}
  - {type: agent, name: task-completion-validator, skillmeat_ref: task-completion-validator, status: available, lifecycle: permanent, scope: null, note: "milestone validator gate; on-disk at user scope"}
  - {type: agent, name: karen, skillmeat_ref: karen, status: available, lifecycle: permanent, scope: null, note: "final exact-tree verdict only; on-disk at user scope"}
  - {type: agent, name: documentation-writer, skillmeat_ref: documentation-writer, status: available, lifecycle: permanent, scope: null, note: "M3 docs. Ships with a haiku default that hard-errors in this environment — dispatch at workhorse class"}
  - {type: agent, name: changelog-generator, skillmeat_ref: changelog-generator, status: available, lifecycle: permanent, scope: null, note: "M3 CHANGELOG [Unreleased]. Same haiku-default caveat as documentation-writer"}
  - {type: skill, name: delegation-router, skillmeat_ref: delegation-router, status: available, lifecycle: permanent, scope: null, note: "resolves provider+model per leg at dispatch from routing_constraints; user-scope install"}
  - {type: skill, name: dev-execution, skillmeat_ref: dev-execution, status: available, lifecycle: permanent, scope: null, note: "milestone execution engine; on-disk"}
  - {type: skill, name: artifact-tracking, skillmeat_ref: artifact-tracking, status: available, lifecycle: permanent, scope: null, note: "progress tracking; on-disk"}
open_questions:
  - id: OPM-OQ-1
    status: resolved
    question: "Freeze the trusted local actor/workspace identity source."
    resolved_by: "P1 (OPM-1.2) — trusted local AuthIdentity, workspace required, strictest-sensitivity computation, no-existence-leak before lookup"
  - id: OPM-OQ-2
    status: resolved
    question: "Freeze confirmation TTL, consumption, and exact-replay semantics."
    resolved_by: "P1 (OPM-1.3) froze the contract; P2 (OPM-2.1, DUR-1) made consumption a real CAS on status issued->consumed in the same durable transaction as the manifest write"
  - id: OPM-OQ-3
    status: resolved
    question: "Decide whether v1 confirmations authorize one stage only or one fully previewed bounded manifest."
    resolved_by: "P1 (OPM-1.3) — one fully previewed bounded manifest, bound by canonical digest + policy snapshot + targets + expiry"
  - id: OPM-OQ-4
    status: resolved
    question: "Freeze operation cancellation safe points and atomic non-cancelable sections."
    resolved_by: "P2 (OPM-2.4) — cancel/resume state machine; H3 ten-scenario matrix converges with uninterrupted effects"
  - id: OPM-OQ-5
    status: open
    question: "Does M3's Karen final pass discharge OPM-DF-regate (the deferred P1 round-6 re-gate), or does the P1 surface need its own re-verdict first? Named, not guessed — see Deferred Items."
decisions:
  - decision: "Retrofit the remaining work (P3-P6) to the Claude-5 milestone doctrine as M1-M3; leave P1-P2 under their authored rules."
    rationale: "Doctrine applies to new plans and lets in-flight work finish as authored. P1/P2 are complete/gated-pending, so converting them would rewrite an executed record for no gain. The remaining 20 pts had not started, so they take the cheaper structure. Scope, AC OPM-1..7, and every negative-proof obligation are unchanged."
    status: accepted
  - decision: "Collapse P3 and P4 into a single milestone (M1)."
    rationale: "They were split to wait on two upstream external gates (CARP-4.G, ERI-5.G), both now satisfied on main (95e8419, e76784b). They already shared a review gate and wrote the same barrier files, so the split bought serialization, not review value."
    status: accepted
  - decision: "Remove per-task agent/model/effort pins from the remaining work; carry routing_constraints instead."
    rationale: "plan-doctrine rule 3. The pins were authored 2026-07-18 against a model roster that has already moved; delegation-router resolves provider+model at dispatch against the live registry. P1/P2 pins are retained as the executed record (deprecated-not-deleted)."
    status: accepted
  - decision: "Adopt the 2-re-pass gate budget with auto-escalation to re-scope."
    rationale: "The most load-bearing change for this plan specifically: P1 ran five gate rounds and closed by owner acceptance with CHANGES_REQUESTED standing; P2 ran four and closed with no verdict. Both are exactly the failure this rule stops."
    status: accepted
wave_plan:
  serialization_barriers:
    - src/research_foundry/services/agent_job_service.py
    - src/research_foundry/services/agent_job_schemas.py
    - src/research_foundry/services/governance.py
    - src/research_foundry/services/audit_service.py
    - src/research_foundry/services/writeback.py
    - src/research_foundry/services/operator_operation_service.py
    - src/research_foundry/services/operator_mcp_adapters/
    - src/research_foundry/operator_mcp/server.py
  phases:
    # P1/P2 are the executed record; their model/effort pins are deprecated-not-deleted and must
    # not be stripped or extended. Per-phase `files_affected` is omitted (both are complete; the
    # union is in top-level `files_affected`, the detail in the phases-1-2 companion file).
    - id: P1
      depends_on: [RPC-1.G, KMCP-1.G]
      isolation: shared
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      gate_lens: [security, validator, karen]
      status: closed_by_owner_acceptance
    - id: P2
      depends_on: [OPM-1.G]
      isolation: worktree
      parallelizable: false
      owner_skills: []
      model: sonnet
      effort: extended
      gate_lens: [security, karen]
      status: implementation_complete_gate_pending
    # Milestones (Claude-5 doctrine retrofit, 2026-07-30). P3-P6 collapsed to M1-M3.
    # No model/provider/effort keys by design: routing resolves at dispatch from
    # `routing_constraints` above. `gate_lens` is retained — it encodes WHICH lens must fire
    # (a risk-class decision earned by the P1 retro), not which model runs it.
    - id: M1
      title: "Every mutation runs through a canonical service adapter"
      depends_on: [P2, CARP-4.G, ERI-5.G]
      isolation: worktree
      parallelizable: false
      context_class: C3
      gate_lens: [validator]
      exit_criteria:
        - "No registered tool path reaches Typer, the CLI module, a shell, or a subprocess"
        - "Direct-service and adapter invocations return equivalent canonical refs for plan, swarm, job lifecycle, import, and all six research stages"
        - "Exact retry creates no duplicate source card, claim, or import receipt"
      files_affected:
        - src/research_foundry/services/swarm_service.py
        - src/research_foundry/services/operator_mcp_adapters/
        - src/research_foundry/cli_commands.py
        - src/research_foundry/services/external_research_import.py
        - src/research_foundry/services/source_cards.py
        - src/research_foundry/services/extraction.py
        - src/research_foundry/services/claim_mapping.py
        - src/research_foundry/services/synthesis.py
        - src/research_foundry/services/verification.py
        - src/research_foundry/services/writeback.py
    - id: M2
      # Scoping note (M2 fix cycle 1/2, TERRA-5/SEC-8): "provably cannot execute" is scoped to
      # every path a real caller can drive, not to arbitrary in-process code execution -- see the
      # "### M2" section body below (its own scoping note) and server.py's module docstring.
      title: "The stdio surface exists and provably cannot execute"
      depends_on: [M1, KMCP-1.G]
      isolation: worktree
      parallelizable: false
      context_class: C3
      gate_lens: [security, validator]
      exit_criteria:
        - "Tool introspection matches the closed inventory exactly, with no Knowledge MCP overlap"
        - "Network, integration-client, and mirror spies stay at zero across every writeback-preview path"
        - "Base package imports and the CLI work with the MCP SDK absent; missing SDK prints one install hint"
      files_affected:
        - src/research_foundry/operator_mcp/__init__.py
        - src/research_foundry/operator_mcp/server.py
        - src/research_foundry/services/writeback.py
        - src/research_foundry/services/operator_mcp_adapters/
        - pyproject.toml
    - id: M3
      title: "One exact tree satisfies AC OPM-1..7"
      depends_on: [M2]
      isolation: shared
      parallelizable: false
      # C4: adversarial matrices over a novel authorization surface with fresh-context verifiers
      # and an operator checkpoint at the boundary. Budget explicitly, per plan-doctrine.md.
      context_class: C4
      gate_lens: [validator, karen-final-tree-only]
      exit_criteria:
        - "AC OPM-1..7 each evidenced by a named command with real, re-run output"
        - "Docs, CHANGELOG [Unreleased], and both deferred shaping specs exist and claim no live/remote qualification"
        - "Karen approves the final tree; deferred_items_spec_refs populated"
      files_affected:
        - tests/unit/test_operator_mcp_policy.py
        - tests/unit/test_operator_operation_service.py
        - tests/unit/test_operator_mcp_adapter_*.py
        - tests/integration/test_operator_mcp_server.py
        - tests/integration/test_operator_mcp_workspace_isolation.py
        - tests/integration/test_operator_mcp_writeback_preview.py
        - docs/user/research-foundry-operator-mcp.md
        - docs/dev/architecture/operator-mcp-governance.md
        - CHANGELOG.md
  waves:
    - [P1]
    - [P2]
    - [M1]
    - [M2]
    - [M3]
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

A local stdio privileged-operation surface, kept separate from the read-only Knowledge MCP. It freezes
operation/identity/sensitivity/confirmation/receipt/error contracts; builds a durable operation
coordinator over existing AgentJob attempts; extracts swarm orchestration from the CLI; wraps canonical
planning/import/research-stage services; and only then registers tools in a thin FastMCP server.
Writeback is a pure preview with negative evidence that no live client or downstream mirror is reachable.

The critical path is serial: each stage establishes the trust contract the next consumes. Progress
artifacts for P1-P2 are under `.claude/progress/research-foundry-operator-mcp/`; M1-M3 progress is
initialized by the artifact tracker at dispatch.

## Execution Status (as of 2026-07-31, M3 close)

- **P2 re-gate: CLOSED 2026-07-30** — both gates genuinely APPROVED (security on `be6ba96`, Karen
  on `ad7d461`). **M1: CLOSED 2026-07-31**, validator APPROVED first round (`d447af9`/`053a2c8`,
  12 adapters, 109 tests). **M2: CLOSED 2026-07-31** (`a4e320e`, pushed, PR #7; whole-tree
  failure set byte-identical to baseline; stdio server, closed 14-tool registry, preview seam).
- **M3: executed 2026-07-31** on this branch (commits `a107d84` wave 1 + fix, `c6df04d` pre-gate
  fixes, `569879c` validator fixes). Pre-gate 0 BLOCKING/0 HIGH; validator APPROVED on `569879c`
  (FIND-M3-V1 all resolved, FIND-M3-V2). Four real product defects found and mutation-verified
  fixed during M3: `job.status` route TypeError-masking, `swarm_start` existence oracle (F6
  class), required-key TypeError→internal_error masking (13-kind class fix), and `swarm.start`'s
  preflight→execute route wholly broken (server-resolved governance fields unreachable). Karen
  final-exact-tree verdict is the remaining gate; evidence artifact:
  `.claude/worknotes/research-foundry-operator-mcp/m3-exact-tree-evidence.md`.
- **Still not merged to main** — merge is a human decision on PR #7 after Karen's verdict.

### Superseded status (as of 2026-07-30, retained for context)

- **Branch/worktree**: `worktree-operator-mcp-v1`, worktree `.claude/worktrees/operator-mcp-v1`, based on
  main `65d658d`, draft PR [#7](https://github.com/miethe/research-foundry/pull/7).
- **P1 (4 pts): CLOSED BY OWNER ACCEPTANCE** at `e5a2e6e`, round-6 re-gate deferred (`OPM-DF-regate`).
  Owner acceptance is **not** a machine verdict: the last one on record was `CHANGES_REQUESTED`.
  Treat `schemas/operator_mcp_receipt.schema.yaml` as **still under-reviewed** — it produced findings
  in every round in which it was actually examined, and was not attacked at all until round 3.
- **P2 (5 pts): implementation COMPLETE, formal gate NOT OBTAINED** (head `b98c0c4`, candidate tree
  `be6ba96`). All findings from four review rounds are closed and independently re-verified;
  regression is clean (4410 passing against a 4258 baseline, the same 16 failing nodes, none on the
  operator surface). But there is **no APPROVED verdict**: Karen's blocking item was closed without a
  re-verdict, and the security lens' final round died twice on 529 API-overload errors. The phase
  artifact stays `in_progress` with `verified_by` empty on purpose. **Next action is a re-gate, not a
  re-fix** — do not reopen the implementation.
- **Not merged to main.** The plan document itself is maintained on main (this file); the *code* stays
  on the branch until the feature completes, so main does not accumulate one commit per phase or carry
  an uncalled authorization module whose gate has not passed.
- **M1-M3 (20 pts): not started**, and blocked on the P2 re-gate above.
- **Read before resuming**: `docs/project_plans/human-briefs/operator-mcp-p1-execution-retro.md` §4
  (recommendations) and §5 (traps discovered), plus "Field Notes" in this document.

> **Plan doctrine note (retrofit, 2026-07-30).** P1/P2 finish under the pre-Claude-5 rules they were
> authored on (executed record: the phases-1-2 companion file). The remaining work is converted to
> the Claude-5 milestone doctrine (`.claude/skills/planning/references/plan-doctrine.md`): P3-P6
> collapsed into **M1-M3**, agent/model/effort pins replaced by `routing_constraints` resolved at
> dispatch by `delegation-router`, `context_class` added to size agent context. This changes **how
> the remaining work is dispatched and reviewed, not what it must deliver** — AC OPM-1..7, the closed
> tool inventory, and every negative-proof obligation carry through unchanged.

## Implementation Strategy

### Architecture sequence

Contracts -> coordinator -> adapters -> transport -> proof. Each stage establishes the trust contract
the next consumes, which is why nothing here parallelizes. Contracts and coordinator are **done**
(P1: schemas/identity/confirmation/receipts/errors; P2: immutable manifest over AgentJob attempts with
idempotency/cancel/resume). The rest is **M1-M3** — see [Milestones](#milestones-m1-m3).

### Non-duplication rules

Operator MCP registers **none** of the following — it calls their owners:

- **Knowledge MCP** — read-only knowledge resources. **Search Router** — discovery/extraction, providers, router policy.
- **RPC** — provenance context and receipt references. **CARP** — catalog-before-discovery planning.
- **ERI** — external packet parsing, staging, source/citation resolution, checkpoints, import receipts.
- **RAL/activation** — assertion identity, reuse, lifecycle, population, promotion.
- **AgentJob** — attempts/events/artifacts/termination; operation manifests own confirmed effect semantics.
- Audit events are supplemental; immutable operator receipts are the effect authority.

### Critical path and external gates

`RPC-1.G + KMCP-1.G -> P1 -> OPM-1.G -> P2 -> OPM-2.G -> M1 -> M2 -> M3`

| Gate | Required evidence before the dependent work starts | Status (2026-07-30) |
|---|---|---|
| RPC-1.G | Canonical origin/run/activity/receipt/AOS/materialization schemas approved by validator and Karen on one exact tree | **Satisfied** — RPC C1 landed on main `65d658d` |
| KMCP-1.G | Read-only Knowledge MCP tool/resource names and non-overlap inventory approved on the exact tree M2 registers against | **Satisfied upstream** — Knowledge MCP landed (`1376e85`, skill `e84c19c`); re-confirm the inventory diff at M2, not before |
| CARP-4.G | Settled run plan/swarm/routing behavior and provenance propagation | **Satisfied** — CARP C3 landed on main `95e8419` |
| ERI-5.G | Resumable import service, immutable receipt/checkpoint contract, and Operator-MCP seam | **Satisfied** — ERI C2 landed on main `e76784b` |
| OPM-2.G | P2 lifecycle candidate approved (security-with-AC-mandate, then Karen) on tree `be6ba96` | **OPEN — the only live blocker.** Implementation is complete; this is a re-gate, not a re-fix |

Both gates that originally forced P3 and P4 apart (`CARP-4.G`, `ERI-5.G`) are now satisfied on main.
That is what makes collapsing them into a single milestone (**M1**) safe: the split existed to wait on
two upstream contracts, not because the adapter work divides at that seam. If a *new* external gate
appears, the dependent milestone stays pending; no temporary duplicate schema or service is introduced.

### Milestone Summary (M1-M3 — remaining 20 pts)

| Milestone | Reviewable state | Estimate | Context class | Gate lens |
|---|---|---:|---|---|
| M1 | Every mutation runs through a canonical service adapter | 10 pts | C3 | validator |
| M2 | The stdio surface exists and provably cannot execute\* | 6 pts | C3 | security + validator |
| M3 | One exact tree satisfies AC OPM-1..7 | 4 pts | C4 | validator, then Karen on the final tree only |
| **Total** | — | **20 pts** | — | — |

\* Scoped to every path a real caller can drive (M2 fix cycle 1/2, TERRA-5/SEC-8) — see the "### M2"
section body's own scoping note, and `server.py`'s module docstring, "Scope of the stdio-only guard".

> H1-H7 detail is in the Human Brief. Excludes remote transport, live writeback, arbitrary execution,
> approval UI, schedules, hosted/public qualification. **Points did not change**: 5+5+6+4 across
> P3-P6 becomes 10+6+4 across M1-M3 — the unit of dispatch changed, not the size of the work.

### Revised gate structure (post-P1 retro)

**Authoritative** wherever another section still lists an original gate assignment. Reviewer
lenses are not fungible: across P1's review record (~2.4M tokens) the validator approved a critical
authorization-bypass **twice** while the security lens found every real defect — so running both
every round bought one lens's yield at two lenses' cost.

| Phase / milestone | Original gates | Revised gate | Rationale |
|---|---|---|---|
| P2 | validator + karen | **security-with-AC-mandate**, then karen | Durability/atomicity is a security property; a validator will approve a read-then-write CAS |
| M1 (was P3+P4) | validator ×2 | validator ×1 | Mechanical extraction + thin adapters; the two phases shared a gate anyway, and the upstream gates that split them are now satisfied |
| M2 (was P5) | security + validator | **unchanged — do not cut** | Writeback-preview negative proof is the second-highest-risk surface after P1 |
| M3 (was P6) | validator then karen | validator, then karen on the **final tree only** | Karen's per-milestone passes duplicate the final one |

Net effect: ~4 fewer frontier review passes across the remaining work. **Do not cut security on
P1/M2 or Karen on the final tree — that is where the defects were. Cut duplicate lenses, not
distinct ones.** Dropping a milestone's only security lens is a scope cut disguised as gate
optimization and stays prohibited.

### Gate budget: 2 re-passes, then re-scope (execution doctrine rule 1)

Any adversarial or validator gate on the **same scope × lens** gets at most **two re-passes**. The
third failure does **not** escalate to "a human looks at it" — it auto-escalates to
**re-scope/redesign**. Three failures against the same lens is evidence the scope is wrong, not that
the fix was sloppy.

This is the single most load-bearing change for this plan specifically. P1 ran **five** gate rounds
and closed by owner acceptance with `CHANGES_REQUESTED` still standing; P2 ran **four** and closed
with no verdict at all. Both are the failure mode this rule exists to stop.

- Count re-passes per **scope × lens**, not per dispatch. Re-spawning an implementer does not reset
  the budget.
- The manual orchestrated path has **no counter** — the orchestrator counts. Only the scripted
  workflow path enforces the cap mechanically (`fixLoop` returns `needs_rescope`).
- **Mutation-verify inside the FIX step, not the next review round.** A P1 fix shipped with four
  tests that all passed on revert. A fix is not done until its test fails against the un-fixed tree.
- Fix loops **continue the existing implementer session** (cache-warm, already holds the context).
  Fresh context belongs on the **verifier** — inherited-context validators rubber-stamp. Today's
  default is inverted; invert it back.
- **Context tripwire at 150%** utilization in one session: split or summarize-forward *before*
  continuing. Past the tripwire is how a fix loop becomes a retry storm.

## Deferred Items & In-Flight Findings Policy

### Deferred Items Triage

| Item ID | Category | Reason deferred | Trigger for promotion | Target spec path |
|---|---|---|---|---|
| OPM-DF-1 | security/transport | Local stdio does not solve remote auth, TLS/origin, canonical URL, revocation, rate limit, or approval UX | Approved remote threat model and owner-authorized deployment need | docs/project_plans/design-specs/operator-mcp-remote-transport.md |
| OPM-DF-2 | external mutation | Preview safety does not authorize downstream effects or compensation | Target-specific approval/idempotency/rollback design and owner-held canary plan | docs/project_plans/design-specs/operator-mcp-live-writeback.md |
| OPM-DF-3 | scope | Arbitrary shell/files/provider/adapter/plugin/schedules violate closed-tool design | Named measured use case with canonical governed service | N/A — explicit non-goal until a concrete capability is named |
| OPM-DF-4 | operations | Public/hosted qualification requires owner identity, private data, deployment, monitoring, and incident response | Separate release plan and owner authorization | N/A — operational gate, not a code design spec |
| OPM-DF-5 | scope | M3 docs + deferred shaping specs are the only gate-free descope | Owner elects to cut scope to fit budget | follow-up plan (docs + OPM-DF-1/OPM-DF-2 shaping specs) |
| OPM-DF-regate | gate debt | P1 closed by **owner acceptance** at `e5a2e6e` with the last machine verdict standing at `CHANGES_REQUESTED`; the round-6 re-gate was deferred rather than run | M3's final exact-tree review — Karen's final pass must cover the P1 surface, not assume it approved | N/A — discharged inside M3, not a design spec |

M3 authors both named design specs at `maturity: shaping` and appends their paths to
`deferred_items_spec_refs`.

### In-flight findings

The findings ledger is **live** at `.claude/findings/research-foundry-operator-mcp-findings.md`
(`findings_doc_ref`), written directly by reviewers. Ordinary deviations are logged there or in the
implementation notes and reviewed at the milestone boundary — they do not halt. A load-bearing
**mismatch** (e.g. AgentJob records proving unsuitable for deterministic operations) is a blocker:
stop the milestone for targeted design and re-estimation rather than inventing a parallel job
authority. See [Execution ledger](#execution-ledger) for the deviation-vs-blocker line.

## Implementer Defect-Class Checklist (mandatory)

Every implementer prompt dispatched for M1-M3 MUST carry this checklist verbatim. It costs nothing
and attacks the two-cycle fix problem at its source: P1's three review rounds found the same
defect classes repeatedly, and the fix cycle itself introduced new instances of them while
"closing" prior findings.

1. **No fail-open defaults.** No permissive default on a security-relevant field, no
   `None`-means-skip, no unknown-label fallback that grants rather than denies. Check the
   *producer* of a value, not just the field — NEW-4 survived round 1 because the field default was
   removed while the function producing it still returned `"public"`.
2. **Fix the layer below.** After hardening a symbol, enumerate its delegates, callers, and
   siblings in `__all__` and ask whether reaching for any of them yields the unsafe behavior. This
   is what found the critical defect in round 2: the fix hardened `authorize_operation` while its
   delegate `verify_confirmation` still reported the replay as an accept, and the new docstring
   steered callers to the weaker door.
3. **Never pin unsafe behavior with a test.** If a test asserts current behavior and the current
   behavior is wrong, the test is wrong — say so and invert it. Three round-2 defects were pinned
   as correct by tests the fix cycle itself wrote.
4. **Never fabricate a validation transcript.** Paste real output or report the failure. A
   fabricated transcript was caught in round 1.

### Cheap pre-gate before the expensive lens

A focused ~30k-token fail-open / layer-below sweep at workhorse class runs BEFORE any frontier
reviewer — ~1/5 the cost; only what survives escalates. An addition to the gates, never a replacement.

## Phase Breakdown (P1-P2) — moved

Executed record with its legacy task tables and pins:
[`phases-1-2-executed-record.md`](./research-foundry-operator-mcp-v1/phases-1-2-executed-record.md).
Historical; M1-M3 below are the remaining work.

## Milestones (M1-M3)

> A milestone is a **reviewable state of the system**, not a batch of tasks — hand the executor the
> whole milestone. Tasks are enumerated **only** where sequencing is load-bearing, with the reason
> named at that point; everything else is deliberately unordered.
>
> Superseded phase IDs: M1 = P3+P4, M2 = P5, M3 = P6. The old `OPM-3.x`/`4.x`/`5.x`/`6.x` task IDs
> are retired; cite milestone IDs and AC IDs in commits and findings from here on.

### Rubric — what "good" looks like

Every AC is satisfiable in more than one way and the wrong ways are the cheap ones. An executor that
reads only the AC and this rubric should make the same calls the plan author would.

1. **Thin adapters, not a second implementation.** An adapter binds identity, workspace,
   sensitivity, prerequisites, and budgets, then calls one named canonical service and maps its
   result into the common envelope. Parsing a packet member, re-deriving a ref, or reimplementing
   stage logic is wrong even when the tests pass. The tell: adapter and direct-service invocation
   yield **equivalent canonical refs**, not merely both-succeed.
2. **Negative proof is evidence, not assertion.** "The preview cannot execute" is proved by a
   call-path scan plus runtime spies reading zero on the exact tree reviewed. A docstring, a
   comment, or a passing happy-path test is not proof.
3. **The scope shrinks before the gate loops a third time.** See the gate budget above.
4. **The four defect classes in the [Implementer Defect-Class Checklist](#implementer-defect-class-checklist-mandatory)
   are part of this bar** — fail-open defaults, fixing the symbol instead of the layer below, pinning
   wrong behavior with a test, and fabricated transcripts. Not restated here; carried verbatim into
   every implementer prompt.

### Named risks

- **The validator lens approves authorization bugs.** Measured twice in P1 on a critical bypass.
  Any AC touching authorization, confirmation, workspace scoping, or the preview boundary needs the
  **security** lens — the validator is not a substitute, and running both every round buys one
  lens's yield at two lenses' cost.
- **Fixing the symbol, not the layer below it.** P1's most expensive defect: hardening
  `authorize_operation` while its delegate `verify_confirmation` still reported the replay as an
  accept, and the new docstring steered callers to the weaker door. When closing any
  access-boundary finding, enumerate **every** public symbol in the module's `__all__`, plus the
  fixed symbol's delegates and callers, and re-attack each.
- **The receipt schema is still under-reviewed.** `operator_mcp_receipt.schema.yaml` yielded
  findings in every round in which it was actually examined and was not attacked until P1 round 3.
  M3 must run a **per-property** matrix against it, not a golden-instance pass.
- **Serialization barriers are shared with live code.** `writeback.py`,
  `operator_mcp_adapters/`, `agent_job_service.py`, `governance.py`, and `audit_service.py` are
  declared barriers. M1 and M2 both write `writeback.py` and `operator_mcp_adapters/`; that is
  why they are sequential waves, not parallel ones.
- **Verification failure must be a governed result, not an exception.** A verify failure that
  propagates as a raw error will be caught by a broad `except` somewhere upstream and read as
  success. It must block the dependent bundle action with a typed, schema-valid denial.
- **Mutation sweeps false-green in this repo** — the pytest `pythonpath` trap nearly published a
  wrong conclusion in P1 round 3. Mechanics and the correct invocation are in Field Notes.

### M1 — Every mutation runs through a canonical service adapter

*(supersedes P3 + P4; 10 pts; context class C3; gate: validator)*

Swarm orchestration no longer lives in Typer. Run planning, swarm start, job lifecycle
(status/cancel/resume), external import, and all six canonical research stages (ingest, extract,
claim-map, synthesize, verify, bundle) are reachable **only** through closed adapters that bind
identity, workspace, effective sensitivity, prerequisites, and budgets, and that return the common
operation/receipt envelope. ERI's import seam and CARP's planning behavior are consumed, never
reimplemented — both landed upstream on main, so there is no temporary duplicate to introduce.

**Load-bearing sequence (the only ordering M1 asserts):** the swarm-service extraction lands
*before* any adapter that dispatches through it, because CLI and adapter must call the same closed
service — building the adapter first creates two dispatch paths and a parity test that passes
against the wrong one.

**AC:**
- No registered tool path reaches Typer, `cli_commands.py`, a shell, a subprocess, or an arbitrary
  dispatch; adapter IDs are policy-allowlisted and unknown/disallowed adapters deny.
- CLI parity holds after extraction: existing CLI behavior is unchanged, and dry-run produces zero
  effects.
- Direct-service and adapter invocation return **equivalent canonical refs** for plan, swarm, job
  lifecycle, import, and each of the six stages.
- Exact retry of any operation creates no duplicate source card, claim, import receipt, or
  source-candidate artifact; cancel/resume does not duplicate a candidate artifact.
- Verify failure is a typed governed result that blocks the dependent bundle action; quarantine and
  missing-input cases deny with reason codes rather than raising.
- `job.status` / `job.cancel` / `job.resume` are bounded and identity-scoped — no raw event-file
  reads, no unbounded pages, no wrong-workspace detail.
- No hard-coded default workspace anywhere in the ingest path.

### M2 — The stdio surface exists and provably cannot execute

*(supersedes P5; 6 pts; context class C3; gate: security + validator — do not cut)*

> **Scoping note (M2 fix cycle 1/2, TERRA-5/SEC-8):** "provably cannot execute" means no registered
> tool, and no code path reachable from a real stdio request, can mount a network transport or
> execute an effect without a bound confirmation — it is provable and holds against every path a
> real caller can drive. It does **not** mean the stdio-only transport guard survives arbitrary
> in-process code execution (an unbound `FastMCP.sse_app(instance)`-style base-class call is a known,
> accepted, documented limitation — see `src/research_foundry/operator_mcp/server.py`'s own
> module docstring, "Scope of the stdio-only guard" section, for the precise boundary). Reaching that
> call already requires arbitrary code execution in-process, at which point the guard is moot either
> way.

A thin FastMCP stdio server registers exactly the closed tool inventory over the M1 adapters, with
bounded inputs, results, events, and errors. The MCP SDK is an optional dependency: the base package
and CLI work without it. Writeback is exposed as a **pure preview** that validates bundle, targets,
and policy and writes only a staged preview — with negative evidence that no live writeback path,
integration client, or downstream mirror is reachable from any registered tool.

**AC:**
- Tool introspection matches the PRD's closed inventory **exactly**, with zero Knowledge MCP overlap
  and no wildcard/arbitrary execution surface.
- Static call-path scan **and** runtime spies both show zero network calls, zero integration-client
  construction, zero mirror writes, and no `accept_job`, shell, subprocess, or arbitrary-path reach
  from any registered handler.
- Preview returns schema-valid reason codes for missing, degraded, and review-required targets, with
  zero external effect in every case.
- Base import and the CLI succeed with the MCP SDK absent; a missing SDK prints exactly one install
  hint; startup performs no network call and no effect.
- Oversize inputs, internal errors, and wrong-workspace refs all return bounded, redacted, safe
  envelopes with retryability and audit-delivery disposition.
- Wheel and editable installs expose the module entrypoint without auto-start, daemon, or listener.

**Mode-D note:** M2 touches no auth, payments, migration, deletion, secret-rotation, or infrastructure
path. Turning the preview seam into a live writeback would be a Mode-D change and halts for explicit
human approval regardless of anything this plan says.

### M3 — One exact tree satisfies AC OPM-1..7

*(supersedes P6; 4 pts; context class **C4** — adversarial matrices over a novel authorization
surface, fresh-context verifiers, operator checkpoint at the boundary; gate: validator, then Karen
on the final tree only)*

A single integrated candidate tree carries public-safe two-workspace fixtures and interrupted-
operation fixtures, and evidences each of AC OPM-1 through OPM-7 with real command output. Docs,
CHANGELOG, and the two deferred shaping specs land, stating truthful repository and live boundaries.

**AC:**
- Each of AC OPM-1..7 is evidenced by its named command in the matrix below, with real re-run output
  on one exact tree; a material change to any of them invalidates prior approval and re-runs it.
- The confirmation adversarial matrix covers missing identity, denial, expiry, replay, wrong
  actor/workspace, payload/target/policy/sensitivity drift, and atomic token consumption — each with
  an **explicit zero-effect assertion**.
- The receipt schema gets a **per-property** re-attack (not a golden-instance pass), per Named Risks.
- Fixtures contain no owner or private corpus data.
- Docs match the exact shipped tool inventory, link to Knowledge MCP / RPC / ERI / CARP / RAL /
  RFUP / Search Router rather than restating their authority, and label remote transport and live
  writeback `deferred` and owner qualification `not_executed_owner_data_absent`.
- `deferred_items_spec_refs` is populated with both shaping-spec paths.

## AC -> command -> evidence

The single home for verification detail. The PRD owns narrative AC; this matrix owns proof. Run from
the repo root with the project venv (`./.venv/bin/python` — the pyenv shim will fail to import
`research_foundry`).

| AC | Command | Evidence of pass |
|---|---|---|
| M1 — closed dispatch, no CLI reach | `rg -n "typer\|cli_commands\|subprocess\|os\.system\|shell=True" src/research_foundry/services/operator_mcp_adapters/` — extend with `src/research_foundry/operator_mcp/` once M2 creates it. Verify the paths exist first: `rg` on a missing path exits 0 with zero matches, which reads as a pass. | Zero matches in **live code** on paths confirmed to exist — comment/docstring hits are expected (11 as of M3) and must each be classified as non-code (see `m3-evidence-reconciliation.md`); an anchored real-import search returns 0 |
| M1 — adapter/service parity | `./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_*.py -q` | Parity assertions compare canonical refs from direct-service vs adapter and match |
| M1 — CLI unchanged after extraction | `./.venv/bin/python -m pytest tests/test_search_router_router.py tests/integration/test_run_launch_reuse.py -q` | Pre-existing CLI/run behavior green, no new failures vs the 4258-node baseline |
| M1 — retry/cancel idempotency | `./.venv/bin/python -m pytest tests/unit/test_operator_operation_service.py -q -k "retry or cancel or resume or duplicate"` | Exact retry yields prior state; no duplicate card/claim/receipt/candidate. **This row was VACUOUS (0/33 selected) until M3**: the file had no test containing any filter term through two closed milestones (M3 Leg C reconciliation; the VAL-1 class hitting the plan itself). M3's H3 matrix (`test_h3_*` retry/cancel/resume/duplicate names) makes it select a real set — verify ≥8 selected via `--collect-only -q` before trusting a green run. |
| M2 — exact tool inventory | `./.venv/bin/python -m pytest tests/integration/test_operator_mcp_server.py -q -k "inventory or introspect or overlap"` | Introspected tool set diffs clean against the closed inventory; no Knowledge MCP overlap. **2 passed** — the `overlap` term is load-bearing: without it the filter selects only `test_exact_14_tool_inventory` and silently drops `test_zero_overlap_with_knowledge_mcp_tool_names`, so the command reports `1 passed` while proving only half the row's claim (VAL-1, M2 validator gate). |
| M2 — preview cannot execute | `./.venv/bin/python -m pytest tests/integration/test_operator_mcp_writeback_preview.py -q` | Network/client/mirror spies assert **zero** calls on every preview path |
| M2 — optional-SDK behavior | `./.venv/bin/python -c "import sys; sys.modules['mcp']=None; import research_foundry; print('base ok')"` then `./.venv/bin/rf --help` | Base package and CLI both succeed with the SDK absent |
| AC OPM-1 — confirmation binding | `./.venv/bin/python -m pytest tests/unit/test_operator_mcp_policy.py -q -k "confirm or replay or expiry or drift"` | Every adversarial case yields zero manifest **and** an explicit zero-effect assertion |
| AC OPM-2 — workspace/sensitivity | `./.venv/bin/python -m pytest tests/integration/test_operator_mcp_workspace_isolation.py -q` | Two-identity matrix returns safe non-existence; no derived detail leaks |
| AC OPM-3 — idempotent/cancel/resume | `./.venv/bin/python -m pytest tests/unit/test_operator_operation_service.py -q` | H3 ten-scenario matrix: interrupted and uninterrupted runs converge to identical canonical effects |
| AC OPM-4 — closed adapters | `./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_*.py -q` + handler call-path scan | Every tool resolves to one named canonical service; no arbitrary dispatch |
| AC OPM-5 — import/stage seams | `./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_*.py -q -k "import or stage or prerequisite"` | ERI receipts/prerequisites/provenance refs preserved; verify-failure blocks bundle |
| AC OPM-6 — preview-only | `./.venv/bin/python -m pytest tests/integration/test_operator_mcp_writeback_preview.py -q` + call-path scan | Static and runtime evidence both show zero external/mirror effect |
| AC OPM-7 — bounded transport | `./.venv/bin/python -m pytest tests/integration/test_operator_mcp_server.py tests/integration/test_operator_mcp_workspace_isolation.py -q -k "limit or error or redact or oversize or payload or workspace"` | Oversize/internal-error/wrong-workspace all return bounded redacted envelopes. **Command widened at M3**: the original `-k "limit or error or redact"` silently dropped the file's own oversize-payload tests (`redact` matched 0 names) and had zero wrong-workspace coverage in the named file — the same silent-subset class as the M2 VAL-1 inventory row. |
| Whole-suite regression | `./.venv/bin/python -m pytest` | 4410+ passing; the same 16 known-failing nodes, none on the operator surface |
| Lint gate | `./.venv/bin/ruff check src/research_foundry --select E9,F63,F7,F82` | Exit 0. **Command corrected at M3**: `flake8` is not installed in the project venv (pyproject lists only `ruff`); the original command silently ran via the global pyenv shim or not at all. |

Exact test filenames are reconciled against the current tree at execution; **a missing planned file
is not evidence of a pass**. No owner/private corpus, remote transport, live writeback, deployment,
or release test is implied by repository fixtures.

## Sequencing (load-bearing)

Order is asserted only where it is real:

- **P2 re-gate -> M1.** M1's adapters call the operation coordinator; dispatching M1 against an
  ungated lifecycle would build on an unverified trust contract.
- **M1 -> M2.** M2 registers tools over M1's adapters; there is nothing to register before they
  exist. Both also write `writeback.py` and `operator_mcp_adapters/` — declared serialization
  barriers — so they cannot run concurrently regardless.
- **M2 -> M3.** M3 evidences AC against the integrated surface; there is no exact tree to attack
  until the server and preview exist.
- **Inside M1**, the swarm-service extraction precedes adapters that dispatch through it (reason
  given in M1 above). No other intra-milestone order is asserted.

## Execution ledger

Deviations and conservative choices are logged with rationale to
`.claude/worknotes/research-foundry-operator-mcp/implementation-notes.md` and reviewed at each
milestone boundary rather than halting on them. **Blockers still stop**: a failing test on the
current work, an unsatisfiable declared artifact, an exhausted recovery path. Beyond those,
mid-milestone halts are reserved for a **destructive** action, a **real scope change**, or **input
only the operator has**.

**Mode-D boundaries are non-negotiable** — always halt for explicit human approval: **auth ·
payments/billing · schema migrations · data deletion · secret rotation · infrastructure**. No
milestone here is expected to touch one; if one starts to, that is a real scope change and stops.

## Field Notes (carry into every M1-M3 dispatch)

Hard-won during P1/P2. These cost nothing to carry and each one has already burned a round.

- **pytest `pythonpath` trap.** `pyproject.toml` sets `[tool.pytest.ini_options] pythonpath =
  ["src"]`, inserted *ahead* of the `PYTHONPATH` env var, so a scratch-tree mutation sweep silently
  tests the real worktree source and reports false negatives. Correct form:
  `--override-ini="pythonpath=<scratch>/src"`; mirror `config/`, `schemas/`, and `templates/` into
  the scratch root (`distribution_root()` resolves via `parents[2]`); purge stale `__pycache__`
  every iteration (`PYTHONDONTWRITEBYTECODE=1`); always take a baseline first.
  `python -c "import x; print(x.__file__)"` is **not** a sufficient check, and a `PYTHONPATH=$PWD/src`
  prefix is decorative — it provides no isolation and is not evidence of a scratch-tree run.
- **`FAILED` lines carry ANSI codes.** `grep "^FAILED"` returns 0 on a red suite. Match without
  anchoring, or strip ANSI first, before concluding a suite is green.
- **Run the suite yourself after every agent** (~2k tokens). A self-reported test result is not
  evidence — this is how a fabricated transcript was caught.
- **Reviewers write findings to disk**, to the ledger `.claude/findings/research-foundry-operator-mcp-findings.md`
  only (no source, no tests). The ledger must not round-trip through the orchestrator context.
- **Do not use phase-owner agents.** They cannot reliably dispatch nested `Task()` in this
  environment, which caused direct implementation and false passes. Dispatch implementers directly.
- **`/dev:execute-plan` silently skips non-roster agents** (observed with `api-designer`), treating
  them as HITL. Confirm each intended agent actually ran; do not infer it from the absence of an
  error.
- **Codex is unavailable for this workstream's security lens.** `codex exec` refused the adversarial
  security-audit framing under its safety classifier after a long reasoning trace. Policy refusal,
  not config — do not retry. (Unrelated: pipe prompts via stdin; the argument form hangs.)
- **Doc agents ship a haiku default that hard-errors here.** Dispatch `documentation-writer` and
  `changelog-generator` at workhorse class.
## Structured Acceptance-Criteria Verification

**The PRD owns the narrative AC** — `.../PRDs/enhancements/research-foundry-operator-mcp-v1.md` §12
carries AC OPM-1..7 in full with `target_surfaces`, `propagation_contract`, and `resilience`. Per
`plan-doctrine.md` rule 4 that prose appears once; this plan owns the **proof**. This section maps
each AC to its evidencing milestone; commands are in the
[AC -> command -> evidence](#ac---command---evidence) matrix above.

| AC | What it asserts (one line — PRD §12 is authoritative) | Evidenced by |
|---|---|---|
| OPM-1 | Preflight and confirmation bind exact authority | M3 — confirmation adversarial matrix |
| OPM-2 | Workspace and sensitivity precede lookup and execution | M3 — two-identity workspace/sensitivity matrix |
| OPM-3 | Jobs are idempotent, cancelable, and resumable | M3 — H3 lifecycle recovery matrix |
| OPM-4 | Closed tools delegate to canonical services | M3 — adapter introspection + handler call-path scan |
| OPM-5 | Import and research stages preserve prerequisites and receipts | M3 — import/stage seam matrix |
| OPM-6 | Writeback preview cannot execute or mirror | M3 — static + runtime negative proof |
| OPM-7 | Transport, errors, and receipts stay bounded | M3 — transport/error bounds matrix |

The PRD's `verified_by` fields now carry these milestone references (the retired `OPM-6.x` task IDs
no longer resolve). Every AC is evidenced **on one exact tree**; a material change to any invalidates
prior approval for all.

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
| Green suite over a real defect | Adversarial pass mandatory on every security-relevant phase; defect-class checklist in implementer prompts | Re-attack the fix, not just the symbol; mutation matrix proves revert-detection | Reopen the phase gate; never treat a passing suite as gate evidence |

Rollback **never deletes** run artifacts, source/extraction cards, claim ledgers, reports, bundles,
import receipts, operation manifests, effect receipts, audit events, or staged previews. Disable the
MCP entrypoint/tool registration and leave durable state for explicit review.

## Validation Strategy

> **Per-AC commands live in the [AC -> command -> evidence](#ac---command---evidence) matrix above —
> the single home for verification detail.** This section carries only what the matrix does not: the
> regression baseline and the negative-proof techniques. The pytest `pythonpath` trap and the ANSI
> `FAILED` trap moved to **Field Notes**.

### Existing-regression gates

```bash
./.venv/bin/python -m pytest tests/integration/test_agent_jobs_api.py tests/unit/test_agent_job_schemas.py tests/unit/test_agent_job_service.py
./.venv/bin/python -m pytest tests/integration/test_run_launch_reuse.py
./.venv/bin/python -m pytest tests/test_search_router_router.py
./.venv/bin/python -m pytest tests/test_schema_validation.py
./.venv/bin/python -m pytest
flake8 src/research_foundry --select=E9,F63,F7,F82
```

**Baseline**: 4258 passing on base `65d658d`; P2's candidate reached 4410 with the same 16 failing
nodes, none on the operator surface. A milestone is green when the whole-suite delta is *only*
additions — not when its own tests pass. Exact test filenames are reconciled against the current tree
at execution; a missing planned file is not evidence of a pass. No owner/private corpus, remote
transport, live writeback, deployment, or release test is implied by repository fixtures.
Pre-existing and not to be chased: `tests/test_verification_pediatric_cds.py` and
`tests/test_verification_seam001_gate_composition.py` fail to COLLECT under `-k` filtering
(sibling `import test_claim_verifier`); present on base `65d658d`.

### Contract and negative-proof gates

- Validate operation/confirmation/receipt/error schemas against golden and negative instances.
- Introspect FastMCP tools and diff against the closed inventory.
- Search registered handler call paths for CLI, shell, subprocess, accept, arbitrary dispatch, live writeback, clients, and mirrors.
- Spy on network and integration clients during preview.
- Compare exact canonical effects and terminal receipt for uninterrupted versus resumed fixtures.
- Diff disabled-mode CLI/service outputs to preserve legacy behavior.

## Documentation Finalization

M3 updates (docs work is offload-eligible per `routing_constraints`; dispatch the doc agents at
workhorse class — their haiku default hard-errors in this environment):

- `docs/user/research-foundry-operator-mcp.md`: install optional dependency, start local stdio, tool inventory, preflight/confirmation, status/cancel/resume, receipt/error interpretation, preview-only writeback, troubleshooting.
- `docs/dev/architecture/operator-mcp-governance.md`: identity/workspace/sensitivity, token binding, operation/effect receipts, AgentJob reuse, audit distinction, limits, threat boundary.
- `README.md`: concise optional local integration pointer if the exact shipped surface warrants it.
- `CHANGELOG.md` `[Unreleased]`: local Operator MCP and its preview-only limitation.
- Deferred shaping specs for remote transport and live writeback.

Docs link to Knowledge MCP, RPC, ERI, CARP, RAL/activation, RFUP, and Search Router rather than
copying their authority contracts, and must label remote transport and live writeback `deferred` and
owner qualification `not_executed_owner_data_absent` absent real authorized evidence.

## Reviewer Gates and Execution Handoff

Per-milestone lens assignment is in "Revised gate structure"; the re-pass cap is in "Gate budget";
dispatch mechanics are in "Field Notes". Not repeated here.

- `task-completion-validator` reviews each milestone against the exact current tree.
- `karen` reviews P1 (done, by owner acceptance), P2 lifecycle (post-security, **pending**), and the
  final feature candidate at **M3, final tree only**. There is no per-milestone Karen pass on M1/M2.
- Security review is mandatory for P1 identity/confirmation, P2 durability/atomicity (AC-mandated),
  and **M2 preview-negative proof**. **Do not cut security on P1/M2 or Karen on the final tree.**
- **Fresh-context verifiers, continued implementer sessions.** Reviewers must not inherit the
  implementer's session — inherited-context validators rubber-stamp. Fix loops continue the
  implementer's existing session rather than re-dispatching.
- A material fix, schema change, tool-registry change, generated artifact, receipt change, or docs/evidence update invalidates prior exact-tree approval.
- The integration owner serializes writes to `agent_job_service.py`, `agent_job_schemas.py`, `governance.py`, `audit_service.py`, `writeback.py`, operation registry, and server registry.
- Implementation approval, metadata closeout, repository readiness, owner-held canary, deployment, release, remote authorization, and live writeback authorization are separate truths.
- **Open scope deviation queued for Karen:** `src/research_foundry/services/governance.py` was
  modified in round 2 (config `secret_patterns` now UNIONs with built-ins rather than replacing
  them). It is a declared serialization-barrier file outside P1's phase ownership. The change is
  strictly strengthening — config can only add detection surface. Reviewer recommends
  accept-with-conditions; adjudication is queued for Karen.

### Execution handoff

Provider and model are **dispatch-time** decisions resolved by `delegation-router` from
`routing_constraints` in frontmatter — this handoff deliberately names no orchestrator model.

> Execute: `/dev:execute-plan docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md`

Before dispatch, the operator should know:

1. **Blocker: the P2 re-gate (`OPM-2.G`) is open.** M1 waits on it. This is a **re-gate, not a
   re-fix** — the implementation is complete and independently re-verified.
2. **This plan lives on `main`; the code lives on `worktree-operator-mcp-v1`.** Rebase that branch
   onto main before resuming so the executor reads these milestones and not the superseded P3-P6
   phase sections.
3. **MUST-stay-claude-primary**: confirmation/authorization semantics, the M2 preview negative
   proof, and every adversarial security lens (Codex offload unavailable — see Field Notes).
4. `required_artifacts` resolved clean on 2026-07-30 — all `available` in the SkillMeat catalog, so
   no `batch_0` provisioning task is needed. Re-resolve if the catalog has moved.
