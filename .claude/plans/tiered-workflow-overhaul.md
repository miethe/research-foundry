---
schema_version: 2
doc_type: meta_plan
title: "Tiered Workflow Overhaul (Research Foundry) — Right-Sizing Planning, Execution, and the Autopilot Lane"
description: "Three-tier model that matches workflow weight to change complexity, plus the single-pass autopilot lane that powers /autopilot and the auto-feature workflow."
status: active
scope: workflow
created: 2026-06-22
updated: 2026-06-22
owner: nick
affects_skills:
  - planning
  - dev-execution
  - workflow-authoring
affects_commands:
  - /autopilot
  - /dev:execute-contract
  - /dev:execute-plan
  - /plan:plan-feature
related_documents:
  - .claude/specs/workflows/workflow-authoring-spec.md
  - .claude/specs/workflows/auto-feature-workflow-spec.md
  - .claude/specs/workflows/execute-contract-workflow-spec.md
  - .claude/specs/workflows/execute-plan-workflow-spec.md
  - .claude/rules/delegation-modes.md
  - .claude/commands/autopilot.md
plan_ref: null
---

# Tiered Workflow Overhaul (Research Foundry)

This is the **Research Foundry-contextual** tier + autopilot reference. It is the resolution
target for three referrers that cite it by anchor:

- `.claude/commands/autopilot.md` → §2.1 (tier matrix).
- `.claude/specs/workflows/auto-feature-workflow-spec.md` → §12 / "Opus 4.8 + Autopilot Recalibration".
- `.claude/rules/delegation-modes.md` → §2 (tier matrix and economics) and §4.8 (mode definitions).

It is intentionally tight: the canonical detail for *how* the workflows execute lives in
`workflow-authoring-spec.md` (the master contract) and the per-workflow specs. This file is the
tier/lane policy those scripts and commands implement.

> **RF context.** Research Foundry is a Markdown/YAML-first, evidence-first research control plane
> (the `rf` CLI + `research_foundry` Python package, plus the `frontend/runs-viewer` pnpm SPA). The
> dev-workflow family ported here (`auto-feature`, `execute-contract`, `execute-plan`) drives
> *changes to RF itself* — backend Python and the runs-viewer frontend — not research runs. The
> research pipeline has its own workflows (`research-foundry-swarm`, `research-foundry-council`,
> the `rf-run-execute` tail). Keep the two families distinct: this overhaul governs code delivery.

---

## §2 — Target State (tiers and economics)

A three-tier workflow where artifact weight, orchestration intensity, and model routing all scale
with change complexity. Tiers describe **artifact weight and review intensity**; the autopilot lane
(§12) is an orthogonal express path layered on top.

### §2.1 Tier matrix

| Tier | Size | Planning artifact | Execution engine | Reviewer | Model routing |
|------|------|-------------------|------------------|----------|---------------|
| **0** | 1–3 pts, single file | none | `/dev:quick-feature` | optional | sonnet executor |
| **1** | 3–8 pts | **Feature Contract** (single ~200–400 line file) | one autonomous sprint — `execute-contract` | **mandatory** `task-completion-validator` | sonnet `feature-sprint-executor` + sonnet contract writer + Opus design block |
| **2** | 8–13 pts | PRD + Implementation Plan | wave-by-wave — `execute-plan` | mandatory `task-completion-validator` per phase; `karen` at milestones | sonnet executor + sonnet `implementation-planner` + Opus decisions block |
| **3** | 13+ pts | SPIKE + PRD + Implementation Plan | wave-by-wave — `execute-plan` | mandatory `karen` per milestone phase | sonnet executor + sonnet `implementation-planner` + Opus decisions block |

**Large-change override (capacity, not points).** Tier is normally chosen by story points, but a
single-agent sprint has a hard context ceiling. Any change that rewrites, relocates, or substantially
restructures a large source file (>~2K lines; >5K always) is **Tier 2 minimum regardless of point
estimate** — a Tier 1 sprint agent cannot hold the large source plus its call-sites at once and will
blow context mid-sprint. Localized edits *inside* a large file (a handful of functions) are exempt.

### §2.2 Token economics target

| Tier | Indicative cost | Target | Lever |
|------|-----------------|--------|-------|
| 0 | ~30K | ~30K | n/a |
| 1 | ~150–200K | ~60–80K | autonomous sprint replaces PRD+Plan+N-phase orchestration |
| 2 | ~325K | ~280K | deterministic wave loop moves mechanical dispatch out of Opus context |
| 3 | ~500K+ | ~450K | better plans (sonnet planner + Opus decisions block) reduce rework |

Most changes land in Tier 1, so the headline win is concentrated there. The economics are *targets*
that calibrate the autopilot ceiling (§12.5), not hard gates.

---

## §4.8 — Mode classification as a delegation prefix

Every delegation prompt carries a one-line **mode marker** as its first line. This calibrates agent
autonomy without restating long context and encodes the safety boundary in one phrase. The five
modes (authoritative definitions live in `.claude/rules/delegation-modes.md`, which cites this
section):

- **Mode A — Exploration Only**: read-only investigation; no edits, no file writes.
- **Mode B — Contract Drafting**: author a contract / plan / spec; no production-code edits.
- **Mode C — Autonomous Feature Sprint**: Tier 1 full implementation per a Feature Contract.
- **Mode D — High-Risk Change**: auth, payments/billing, migrations, data deletion, secret rotation,
  infrastructure. Explore + propose only; **await explicit human approval** before any production
  edit. In a workflow this is a **hard boundary** — the script returns control to Opus, never
  auto-implements (master contract §5 constraint 2, §7).
- **Mode E — Reviewer**: read diff + artifacts, score against criteria, no edits.

Mode determines the safety boundary, not the agent's pre-configured `permissionMode`; both must
align. Inside a workflow, mode boundaries are enforced by `agentType` selection (for read-only roles)
and by returning to Opus (for Mode D) — never by prompt text alone.

---

## §12 — Opus 4.8 + Autopilot Recalibration

Opus 4.8 + Dynamic Workflows raise the autonomous single-pass ceiling: parallel waves and background
agents absorb work that previously forced full phase-orchestration with a PRD + Implementation Plan.
This section adds a **Single-Pass Capacity** predicate — it does *not* change the tier thresholds in
§2.1, which still describe artifact weight. It powers the `/autopilot` command and the `auto-feature`
workflow.

### §12.1 — Single-Pass Capacity (autopilot eligibility)

The `/autopilot` lane plans + executes + reviews in ONE workflow pass when **all** of the following
hold (otherwise it escalates to the tier-appropriate full flow):

| Predicate | Threshold | Rationale |
|---|---|---|
| `effort_points` | ≤ 13 | Raised from Tier 1's 8-pt ceiling — Opus 4.8 + parallel waves absorb more. |
| `wave_count` | ≤ 3 | Sequential dependency depth is the real cost/risk multiplier; parallel fan-out *within* a wave is cheap and not counted. |
| `mode_d` | `false` | No auth / payments / billing / migrations / deletion / secret rotation / infra. |
| `needs_spike` | `false` | No unresolved research or feasibility unknowns. |
| bounded graph | ≤ 8 phases AND ≤ 25 files | Soft caps; exceeding either escalates. |

The gate is a **deterministic check in `auto-feature.js`**, authoritative over the planner's own
`single_pass_feasible` self-assessment.

### §12.2 — Recalibrated tier → lane mapping

| Tier band | Effort | Conditions | Lane | Engine |
|---|---|---|---|---|
| Tier 0 | 1–3 pts | single file/unit | Autopilot (single sprint) | `execute-contract` |
| Tier 1 | 3–8 pts | clear scope | Autopilot (single sprint) | `execute-contract` |
| Tier 2-LOW | 8–13 pts | ≤3 waves, no SPIKE, no Mode D | Autopilot (multi-wave) | `execute-plan` |
| Tier 2-HIGH | 8–13 pts | >3 waves OR unbounded graph | Full planning scope | `execute-plan` (Opus-built graph) |
| Tier 3 | 13+ pts | multi-area / very complex | Full planning scope | `execute-plan` |
| Any tier | — | Mode D OR needs_spike | Escalate (boundary) | interactive / `/plan:explore` |

### §12.3 — Escalation routing

| Failed predicate | Workflow `reason` code | Opus routes to |
|---|---|---|
| `mode_d == true` | `mode_d` | Interactive Opus under Mode D discipline (`delegation-modes.md`) |
| `needs_spike == true` | `spike_required` | `/plan:explore` or `/plan:spike` |
| `effort_points > 13` OR `tier ≥ 3` | `scope_exceeds_single_pass` | `/plan:plan-feature` (Tier 2/3 → PRD + Implementation Plan) |
| `wave_count > 3` OR `phases > 8` OR `files > 25` | `scope_exceeds_single_pass` | `/plan:plan-feature` |

The workflow writes a draft plan artifact regardless, so escalation hands the full-planning flow a
head start — see `autopilot.plan_artifact_path` in the returned `ExecutionReport`.

### §12.4 — Autopilot lane vs. tiers (orthogonality)

The autopilot lane is an **orthogonal express path**, not a replacement for tiers. Tiers still
describe artifact weight and review intensity. Autopilot auto-classifies a raw request and either
executes it within single-pass capacity or bails to the tier-appropriate full flow. §12.1 is the
authoritative gate, NOT the planner's self-assessment.

### §12.5 — Reversion criterion

Track the **autopilot escalation rate**. If >25% of `/autopilot` runs escalate to full planning, the
single-pass ceiling is set too high — lower `max_points` / `max_waves` via the command's `ceiling`
override. If <5% escalate AND token costs stay bounded, consider raising the ceiling. **Mode-D and
spike escalations are EXCLUDED** — they are correct boundary behavior, not mis-sizing.

### §12.6 — Cross-references

- `.claude/specs/workflows/auto-feature-workflow-spec.md`
- `.claude/workflows/auto-feature.js`
- `.claude/commands/autopilot.md`
- `.claude/rules/delegation-modes.md`
- `.claude/specs/workflows/workflow-authoring-spec.md` (master contract)
