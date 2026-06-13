# Delegation Modes Rule (Global)

**Purpose**: Mode markers calibrate agent autonomy without restating long context. Every delegation prompt includes one mode marker as the first line to encode the safety boundary and expected behavior.

---

## The Five Modes

**Mode A: Exploration Only**

Read-only investigation. No edits, no file writes. Agent explores codebase, traces patterns, answers questions like "where is X used?" or "how does Y work?". Used for `codebase-explorer`, `search-specialist`, `symbols-engineer`. Output is findings/summary, never code changes.

**Mode B: Contract Drafting**

Author a contract, plan, PRD, or specification; no production-code edits. Agent writes planning/design artifacts. Used for `prd-writer`, `implementation-planner`, contract writers, and feature planning work. Output is the authored artifact itself.

**Mode C: Autonomous Feature Sprint**

Tier 1 full implementation per a Feature Contract. Single agent explores, implements, tests, validates, produces Completion Report. Complete autonomy within contract scope. Used for `feature-sprint-executor`. Permission: `acceptEdits` within contract boundaries.

**Mode D: High-Risk Change**

Auth, payments, data deletion, infrastructure, or database migrations. Agent explores, proposes solution in Completion Report, stops before edits. Await explicit human approval before any production changes. No code writes without user sign-off.

**Mode E: Reviewer**

Read diff and validation artifacts; score against criteria; produce recommendation. No edits, no file writes. Used for `task-completion-validator`, `karen`, `code-reviewer`. Output is the review/recommendation, never code.

---

## Invariants

1. **Every delegation prompt SHOULD include exactly one mode marker** as the first line: e.g., `Mode: C — Autonomous Feature Sprint`.

2. **Mode determines the safety boundary**, not the agent's pre-configured `permissionMode`. Both must align. Mixing a Mode A prompt with an agent configured as `acceptEdits` is a safety violation.

3. **Cross-mode escalation requires explicit user approval.** A Mode C sprint that hits Mode D territory (touches auth or payment code) must stop and report. Requesting user approval or Opus judgment before continuing.

4. **In v1 these are advisory** (encoded in prompt text). v2 may split into distinct agent profiles per mode, each with aligned `permissionMode` and resource constraints (see Open Question OQ-2 in `.claude/plans/tiered-workflow-overhaul.md`).

5. **Mode E reviewers read diffs,** not source files. Use `git diff` output, Completion Reports, and artifact frontmatter. Reviewers never have edit permissions; they cannot implement fixes, only identify them.

---

## Cross-References

- **Tier system**: `.claude/plans/tiered-workflow-overhaul.md` §2 (tier matrix and economics).
- **Mode definitions**: `.claude/plans/tiered-workflow-overhaul.md` §4.8.
- **Feature Sprint executor**: `feature-sprint-executor` agent definition (Mode C consumer).
- **Mandatory reviewer gates**: `.claude/skills/dev-execution/validation/completion-criteria.md`.
