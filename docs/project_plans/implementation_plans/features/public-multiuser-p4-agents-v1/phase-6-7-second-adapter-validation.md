---
schema_version: 2
doc_type: phase_plan
title: "Phase 6–7: Second Adapter & Validation"
status: draft
created: 2026-07-06
phase: "P4.6-P4.7"
phase_title: "Second provider adapter (openai_agents); Testing, benchmark, docs"
prd_ref: docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
entry_criteria:
  - "P4.6: P4.4 sealed (proven isolation boundary + API contract)"
  - "P4.7: P4.5 and P4.6 both sealed"
exit_criteria:
  - "P4.6: parity job runs; provider-parametrized tests pass"
  - "P4.7: full validation green; Mode-D Gates #3/#4 logged; karen end-of-feature review passed"
---

# Phase 6–7: Second Adapter & Validation

[← Back to plan summary](../public-multiuser-p4-agents-v1.md)

**Column conventions**: `Estimate` = story points. `Model`: `opus|sonnet|haiku|gpt-5.5-codex`. `Effort` (claude): `adaptive|extended`; (codex): `none|low|medium|high|xhigh`. `Provider`: `claude|codex`. See `.claude/skills/planning/references/multi-model-guidance.md`.

---

## Phase P4.6: Second provider adapter (`openai_agents`)

**Estimate**: 2 pts
**Dependencies**: P4.4 complete (proven isolation boundary + stable API contract)
**Isolation**: shared
**Assigned Subagent(s)**: python-backend-engineer (primary), backend-architect (secondary)
**Agent Routing**: MUST-stay — second provider adapter, reuses P4.2's isolation boundary unchanged; no new credential-handling code, so risk is lower than P4.3, but still no ICA/Codex offload for implementation per the decisions block's blanket MUST-stay on provider adapters.

### Overview

`openai_agents.py` is greenfield (SPIKE finding G4 — no adapter file exists yet). Implements the same `ResearchAgentProvider` Protocol via the OpenAI Agents SDK, running inside the *same* subprocess/temp-file/redaction-firewall boundary built in P4.2 — this phase adds no new isolation code, only a second Protocol implementation and its SDK-native guardrail wiring.

### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|----------------------|----------|--------------|-------|--------|--------------|
| ADP-6.1 | `openai_agents.py` adapter | Net-new adapter (FR-2) implementing the `agent_providers/base.py` Protocol via the OpenAI Agents SDK; reuses SEC-2.1/2.2/2.3/2.4 isolation boundary unchanged. | Registry lists the new provider; a stub job round-trips through the existing spawn/temp-file/firewall path with no isolation-layer changes. | 1 pt | python-backend-engineer | sonnet | adaptive | ADP-3.3, SEC-2.4 |
| ADP-6.2 | SDK-native guardrails/HITL/tracing wiring | Configure `policy_snapshot`'s `allowed_tools`/`data_scopes` enforcement via the OpenAI Agents SDK's native guardrail/permission hooks (AC-4.2 — an out-of-scope tool/data action is blocked at the SDK layer and recorded as an `agent_job_event`). | Blocked-action test asserts both the block and the recorded event. | 0.75 pt | python-backend-engineer, backend-architect | sonnet | adaptive | ADP-6.1 |
| ADP-6.3 | Provider-parametrized integration test suite | Parametrize the ADP-3.3 job-lifecycle test matrix over both providers (`claude_agent_sdk`, `openai_agents`) to prove parity. | Both providers pass the identical lifecycle test matrix. | 0.25 pt | python-backend-engineer | sonnet | adaptive | ADP-6.2 |

**Phase P4.6 Quality Gates:**
- [ ] Parity job runs on `openai_agents` through the unchanged isolation boundary.
- [ ] Provider-parametrized test suite green for both providers.
- [ ] No isolation-layer (P4.2) files modified by this phase — confirmed via diff review.
- [ ] `task-completion-validator` review passed.

---

## Phase P4.7: Testing, benchmark, docs

**Estimate**: 3 pts
**Dependencies**: P4.5 and P4.6 both complete
**Isolation**: shared
**Assigned Subagent(s)**: python-backend-engineer (tests), documentation-writer (docs)
**Agent Routing**: **Codex gpt-5.5** (`codex exec`, read-only sandbox) runs the adversarial review of the credential firewall (VAL-7.2) — review only, never implementation. Docs tasks route to haiku; the FU-1 design-spec (VAL-7.4) routes to sonnet per the standard DOC-006 convention (design-spec authoring, not mechanical docs).

### Overview

Closes the feature: the full credential-firewall regression suite run against a **real** run trace (closing Mode-D Gate #3), the Codex adversarial review, static+loopback E2E parity, the FU-1 benchmark writeup (DOC-006-style deferred-item design spec), the pepper-storage decision doc (closing Mode-D Gate #4), CLI parity (FR-20, moved here from P4.4 as house-style plumbing per H6), and standard documentation finalization.

### Mode-D Gates #3 and #4 (this phase)

- **Gate #3**: Explicit human approval verifying the write-time redaction guard (P4.2, SEC-2.3) against a **real run trace**, not a synthetic fixture (PRD AC-6.3) — closed by VAL-7.1.
- **Gate #4**: Explicit human sign-off on the server pepper storage location (PRD AC-6.4) before the key-fingerprint feature ships — closed by VAL-7.5.

### Task Table

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Provider | Dependencies |
|---------|-----------|-------------|----------------------|----------|--------------|-------|--------|----------|--------------|
| VAL-7.1 | Credential-firewall regression suite (Mode-D Gate #3) | Full pass of AC-5.1–5.5 (secret-scan, crash-safety, code-path audit, fingerprint construction, governance-pattern non-match) run against a **real** run trace, not a synthetic fixture — closes Gate #3. | All 5 AC-5.x assertions pass against the real trace; Gate #3 approval logged. | 0.75 pt | python-backend-engineer | sonnet | extended | claude | SEC-2.4, API-4.5 |
| VAL-7.2 | **Codex adversarial review** of the credential firewall | Read-only adversarial review (`codex exec`, sandbox read-only) probing the P4.2 subprocess/temp-file/redaction design for prompt-injection/exfiltration paths (Risk 1 mitigation). Findings route back to python-backend-engineer for fixes if any are found — this task is review-only, never implementation. | Review report produced; any findings triaged and either fixed (new follow-up task) or explicitly accepted with rationale. | 0.5 pt | python-backend-engineer (review target) | gpt-5.5-codex | xhigh | codex (read-only) | VAL-7.1 |
| VAL-7.3 | E2E static+loopback parity suite | `agents.enabled` flag off/on: static export shows the correct disabled/informational state; loopback mode exercises the full governed flow end-to-end. | Both flag states pass their respective E2E assertions. | 0.5 pt | python-backend-engineer | sonnet | adaptive | claude | ADP-6.3, UI-5.9 |
| VAL-7.4 | FU-1 benchmark writeup + design spec (DOC-006 pattern) | Author `docs/project_plans/design-specs/agent-job-spawn-latency-fu1.md` documenting SEC-2.5's benchmark numbers and a GO/fallback verdict (in-process scoping if latency proves prohibitive per D3); `maturity: shaping` (or `idea` if inconclusive); `prd_ref` set to the P4 PRD; append the resulting path to this plan's `deferred_items_spec_refs`. | Design spec exists with a stated verdict; `deferred_items_spec_refs` updated in the parent plan's frontmatter. | 0.5 pt | documentation-writer | sonnet | adaptive | claude | SEC-2.5 |
| VAL-7.5 | Pepper-storage decision doc (Mode-D Gate #4) | Short architecture note at `docs/project_plans/design-specs/agent-job-pepper-storage-decision.md` recording the sign-off on server pepper storage location (env var per D2, or promoted to keyring — record the actual decision made); links back to ADR-002, does not re-litigate it — closes Gate #4. | Doc exists; Gate #4 approval logged with the decision and rationale. | 0.25 pt | documentation-writer | haiku | adaptive | claude | SEC-2.4 |
| VAL-7.6 | CLI parity (FR-20) | `rf agent-job launch\|status\|events\|cancel\|accept` mirroring `rf catalog`/`rf report draft` conventions; threshold parity on sensitivity-gated reads. Budgeted here (not P4.4) as house-style plumbing per H6. | CLI commands exist and match existing `rf` help-text conventions; sensitivity-threshold flag parity confirmed. | 0.25 pt | python-backend-engineer | sonnet | adaptive | claude | API-4.5 |
| VAL-7.7 | Documentation finalization bundle | CHANGELOG `[Unreleased]` entry (`changelog_required: true` — `/agents` route ships, per `.claude/specs/changelog-spec.md`); `/agents` user doc + `rf agent-job --help` consistency; context-file updates (CLAUDE.md pointer only if agent-facing patterns changed, e.g. the Mode-D gate precedent); plan frontmatter finalization (`status: completed`, `commit_refs`, `files_affected`, `updated`). | `[Unreleased]` contains a matching entry; `changelog_ref` set; frontmatter lifecycle fields populated on the parent plan. | 0.25 pt | changelog-generator, documentation-writer | haiku | adaptive | claude | All P4.1–P4.6 tasks |

**Phase P4.7 Quality Gates (phase exit gate, per decisions block — end of feature):**
- [ ] Full credential-firewall regression suite green against a real run trace (Gate #3 logged).
- [ ] Codex adversarial review complete; findings triaged (fixed or explicitly accepted).
- [ ] E2E static+loopback parity suite green.
- [ ] FU-1 design spec authored with a stated verdict; `deferred_items_spec_refs` populated.
- [ ] Pepper-storage decision doc authored (Gate #4 logged).
- [ ] CLI parity commands implemented and documented.
- [ ] CHANGELOG `[Unreleased]` entry present; plan frontmatter finalized.
- [ ] `task-completion-validator` **and** `karen` (end-of-feature review, Tier 3) both passed — the plan's 3rd and final mandatory `karen` gate.

---

[← Back to plan summary](../public-multiuser-p4-agents-v1.md) | [← Phase 5](./phase-5-frontend.md)
