---
skill: intenttree-cli
---

# intenttree-cli — Changelog

Tracks changes to the skill pack (SKILL.md, SPEC.md, workflows, references, templates).
Implementation changes live in git commit messages; this file tracks skill surface changes only.

---

## v1.0 — 2026-06-10

- Restructured to the SkillMeat progressive-disclosure pattern.
- SKILL.md is now a thin router (≤80 lines): trigger-rich `description`,
  When-To-Use / When-NOT tables, a Route Table (Intent | Workflow Doc | Notes),
  a Policy block (Progressive Disclosure, Permission Protocol, Route-First
  Invariant), and a Setup / Confidence-Anchor section (install, config
  precedence, env vars, self-set token). No command flags in SKILL.md.
- Workflow docs rewritten to a uniform skeleton (When to use / Prerequisites /
  Recipe(s) / Error handling / See also), each ≤120 lines, every recipe `--json`.
- `references/command-quick-reference.md` compacted to ≤100 lines, all 11 groups.
- **CLI reconciliation (live source wins over docs/CLI.md):** corrected
  `tree create` to `--title`/`--slug`/`--description` (was `--name`/`--intent`);
  `today schedule` to `--start`/`--lane`/`--duration` (was `--start-min`);
  `agent list`/`artifact list` to `--workspace-id`; added `run list --workspace`
  and `events --actor`. docs/CLI.md drift recorded as follow-ups.
- decompose recipe carries the verbatim "Current behavior" note (no implied
  prose→tree intelligence; points to `intenttree-prose-distillation-v1`).
- Added a worked end-to-end example (prose request → capture/promote → progress).

## v0.1.0 — 2026-06-05

- Initial skill pack authored.
- SKILL.md: 10-section structure (intro, When To Use, When NOT To Use, Confidence Anchor,
  Routing Posture, Routing Table, Output Guidance, Multi-Step Flows, Do Not Say, Key References).
- SPEC.md: 7-section contract (Purpose & Scope, Capability Coverage, Invariants, Enhancement
  Backlog, Changelog, Integration Points, Success Signals).
- Capability coverage: 35 intents across 6 workflows, 1 reference, and 1 template.
- Verified against `docs/CLI.md` and `backend/src/intenttree/cli/commands/` as of 2026-06-05.
- Workflows, references, and templates authored:
  - `workflows/creation-workflow.md`
  - `workflows/reading-workflow.md`
  - `workflows/updating-workflow.md`
  - `workflows/whats-next-workflow.md`
  - `workflows/dispatch-workflow.md`
  - `workflows/bootstrap-workflow.md`
  - `references/command-quick-reference.md`
  - `templates/claude-md-snippet.md`
- Enhancement Backlog: 6 entries (BL-1 through BL-6).
- Status: draft.
