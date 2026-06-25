---
schema_version: 2
doc_type: spec
title: "Subagent Nesting Specification — Governance for Nested Agent Spawning"
status: active
created: 2026-06-17
updated: '2026-06-17'
owner: nick
feature_slug: subagent-nesting
source_of_truth: true
related_documents:
  - .claude/plans/subagent-nesting-orchestration-strategy-v1.md
  - .claude/rules/delegation-modes.md
  - .claude/specs/provider-routing-spec.md
  - .claude/skills/delegation-router/SKILL.md
  - .claude/specs/workflows/workflow-authoring-spec.md
  - .claude/rules/context-budget.md
---

# Subagent Nesting Specification

**Single authoritative home for subagent-nesting governance** (a subagent spawning its own
subagents via the `Agent` tool). Every other governance file points HERE for nesting rules rather
than duplicating them. When a nesting rule changes, change it here only.

Three sibling files cross-reference this spec and MUST NOT re-derive its rules:
`delegation-modes.md` → "Mode-D at Depth"; `provider-routing-spec.md` + `delegation-router` SKILL
→ "Claude-Primary-Only Nesting"; `context-budget.md` → "Per-Level Context Budget".

---

## Scope & Status

Subagent nesting is GA in Claude Code CLI **v2.1.172+** (no flag, no permission prompt). It is a
**dev-time orchestration** capability only — the embedded `claude-agent-sdk` still forbids nesting,
so nesting never appears in SkillMeat product runtime code. Nesting is **additive to Dynamic
Workflows, not a replacement**: workflows retain deterministic control flow, same-session resume,
a shared budget pool, and an enforceable Mode-D boundary that raw nested trees lack. The unlock is
**composition** — workflow-spawned phase-owners nest their own implementers. Nesting is **governed,
not banned.** Phases 0 (empirical validation) and 1 (Tier A pilots) have SHIPPED; this spec encodes
**Phase 2 governance** (strategy plan §5). Adoption beyond pilots is gated on the rules below.

---

## Verified Mechanics

Phase 0 empirical findings (CLI v2.1.173, 2026-06-11). Source: strategy plan §11.

| Mechanic | Verified behaviour | Confidence |
|---|---|---|
| Depth cap | **No cap enforced through depth 7** — zero friction (no error/prompt/warning). Documented "5-level cap" did not trigger. Depth is self-governed, never a runtime guardrail. | High |
| Single `Agent` call | **Blocks** — parent halts until the child returns; `agentId` is a resume handle, not an async future. | High |
| Batched `Agent` calls | **Run CONCURRENTLY** — multiple `Agent` calls in one message overlap, same semantics as the top level. | High |
| `permissionMode` | **PROPAGATES to nested children** — a child inherits `acceptEdits`/`bypassPermissions` and writes unprompted. | High |
| `run_in_background` | **Works at depth** — nested children accept `run_in_background: true`. | High |
| `isolation: worktree` | **Works at depth** — isolated worktree under `.claude/worktrees/`, auto-cleaned. | High |
| Token accounting | Per-call `subagent_tokens` visible to the **immediate parent only** (foreground). Whole-tree aggregation into workflow `budget.spent()` **UNCONFIRMED**. | Medium |

---

## Claude-Primary-Only Nesting

**CANONICAL** (strategy plan §5.2). `provider-routing-spec.md` and the `delegation-router` SKILL
point HERE; do not re-derive.

- **Rule:** nesting is a **claude-primary-only** capability. Nested children ALWAYS run on the
  primary subscription.
- **Rule:** cross-provider offload (ICA / Bob / Gemini / Codex) stays **FLAT** and router-governed.
- **Rule:** a router-offloaded executor **NEVER nests.** Nesting from an offloaded leg would create
  ungoverned spawn points that escape the `RoutingRecord` / `routing-decisions.jsonl` audit log.
- **Rationale:** the router's MUST-stay/RoutingRecord model assumes the orchestrator routes *each*
  leg. Keeping nesting on claude-primary means there is nothing to audit-route — the audit-log blind
  spot cannot open.

---

## Mode-D at Depth

**CANONICAL** (strategy plan §5.1). `delegation-modes.md` points HERE; do not re-derive.

- **Rule:** nested agents are **PROHIBITED from Mode-D work outright** — auth, payments, migrations,
  deletion, force-push, secret-rotation.
- **Rule:** on hitting Mode-D territory a nested agent **STOPS** and bubbles a `needs_opus` /
  `mode_d` signal up its chain. Each parent **relays it upward UNCHANGED** until it reaches Opus.
- **HARD prerequisite, not advisory.** Unlike a workflow's `return {needs_opus}`, there is **no
  runtime boundary at depth.** Because `permissionMode` propagates (Verified Mechanics; OQ-4), a
  deeply nested agent inherits `acceptEdits`/`bypassPermissions` and *would* write Mode-D code
  unprompted. Mode-D-at-depth is therefore a precondition for any Tier B adoption, not a follow-up.
- **Encode in agent definitions:** any agent permitted to nest carries the Mode-D-stop instruction
  in its prompt; the safety boundary lives in the definition, never in inline task text alone.

---

## Per-Level Context Budget

Strategy plan §5.3. `context-budget.md` cross-references HERE.

- **Compounding failure:** context-blow (the recurring "Prompt is too long" work-loss) **COMPOUNDS
  with depth** — more handoff points, and a deep child's blow-up silently loses work shallower
  levels cannot see.
- **Rule:** each nesting level carries a tool-use / token ceiling. Nested helpers MUST be bounded —
  recommend **< ~40 tool uses per level**. Pre-scout with haiku where possible.
- **Rule:** because batched spawns run concurrently (Verified Mechanics; OQ-2), a parent can fan out
  several children at once with **no `parallel()` cap+queue**. Budget defensively for the whole fan-out,
  not per-child.
- Keep *governed* throughput at the workflow `parallel()`/`pipeline()` level; treat in-agent batching
  as a bounded decomposition tool, never a substitute for the workflow concurrency cap.

---

## Durability Contract

- A workflow caches a phase-owner's **FINAL result only.** From the workflow's view a nested subtree
  is one `agent()` call.
- **If a nested child blows up mid-nest, shallower levels can't see it and the WHOLE phase re-runs.**
  There is **no partial-subtree resume.**
- **Consequence:** nesting trades adaptivity for **coarser failure recovery.** Keep nests **shallow
  and bounded.** Commit-as-you-go at the workflow level remains the only durability mechanism;
  in-nest progress is not durable.

---

## OQ-5: Nesting via `Agent` vs `workflow()` Re-entry

**Resolved.** Nesting via the `Agent` tool is **ORTHOGONAL** to the `workflow()` one-level re-entry
cap in the authoring spec.

- A workflow-spawned agent **MAY** spawn its own children via `Agent` — this is the nesting capability.
- The `workflow()` re-entry mechanism **remains capped at one level** per
  `workflow-authoring-spec.md` §1.
- The two mechanisms are **independent.** Do not conflate them: `Agent`-nesting depth is governed by
  this spec (self-budgeted, no enforced cap); `workflow()` re-entry depth is governed by the
  authoring spec (one level).

---

## OQ-3: Token Accounting (Defensive Budgeting)

**Partial / unconfirmed.** Whole-tree token aggregation into workflow `budget.spent()` is **NOT
established.**

- **Assume the workflow UNDERCOUNTS deep subtrees.** Per-call `subagent_tokens` reaches only the
  immediate parent; background spawns report tokens only at completion.
- **Budget defensively** — do not rely on tree-wide accounting for any budget gate.
- **Re-confirm empirically** before relying on tree-wide accounting (carry to a follow-up probe).

---

## Cross-References

- `.claude/plans/subagent-nesting-orchestration-strategy-v1.md` §5 — governance prerequisites (full rationale, decision log, Phase 0 findings).
- `.claude/rules/delegation-modes.md` — consumes "Mode-D at Depth" (Mode-D-at-depth subsection points here).
- `.claude/specs/provider-routing-spec.md` — consumes "Claude-Primary-Only Nesting".
- `.claude/skills/delegation-router/SKILL.md` — consumes "Claude-Primary-Only Nesting" (offloaded executors never nest).
- `.claude/specs/workflows/workflow-authoring-spec.md` §1 — `workflow()` one-level re-entry cap (orthogonal to `Agent`-nesting; see OQ-5).
- `.claude/rules/context-budget.md` — consumes "Per-Level Context Budget".
