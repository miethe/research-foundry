# Project-Level Tracking Spec

**Version**: 1.0 (Design)
**Status**: Draft
**Purpose**: Cross-feature visibility layer for the IDD planning system
**Problem**: Individual plan/progress files have no aggregation; cross-feature state requires manual inspection of N independent files.

---

## Design Principle

**Derive, don't author.** All tracking artifacts are generated from existing plan frontmatter and progress files. No manually maintained registers.

---

## Architecture: Three Layers

### Layer 1 — Active Work Register (Priority: High)

A single generated file providing cross-feature visibility for agents and humans.

**Location**: `.claude/plans/active-work.md`
**Generator**: `scripts/generate-active-register.py`
**Trigger**: Pre-session hook, on-demand, or file watcher on `.claude/progress/`

**Format**:

```yaml
---
generated_at: 2026-03-31T14:00:00Z
active_features: 3
blocked: 1
completed_since_last: 2
---
```

Followed by structured tables:

| Section | Content | Source |
|---------|---------|--------|
| In-Flight | Feature name, current phase, status, branch, blockers | Progress file frontmatter |
| Recently Completed | Feature name, completed date, outcome | Plan frontmatter `completed_at` |
| Blocked | Feature name, blocker description, blocked since | Progress file `blockers` field |
| Upcoming | Planned features not yet started | PRDs with status `approved` |
| Ideas & Specs | Spec name, status, category, related PRD | Design spec frontmatter |

**Agent context use**: This file can be included in agent context to answer "what else is happening?" without reading 15+ files. Budget: <2K tokens for typical project state.

**Data sources** (scanner reads these):

| Source | Fields Extracted |
|--------|-----------------|
| `.claude/progress/*/phase-*-progress.md` | Phase status, task completion %, blockers |
| PRDs (`.claude/plans/*.md`, `project_plans/`) | Feature name, status, epic, depends_on |
| Design specs (`.claude/specs/*.md`) | Spec name, status, category, related PRD |

**Note**: Implementation plans are excluded — they contain engineering execution detail, not cross-feature visibility data.

**Prerequisite**: Design specs require a frontmatter standardization pass before scanner can parse them (see SPIKE design doc).

### Layer 2 — Epic Grouping (Priority: Medium)

Lightweight docs grouping 3+ related features under a shared goal.

**Location**: `.claude/plans/epics/`
**When to create**: Only when 3+ features share a goal (e.g., enterprise overhaul, DVCS, marketplace)
**Existing precedent**: `.claude/plans/enterprise-overhaul-roadmap.md`

**Format**:

```yaml
---
title: Enterprise Overhaul
status: in-progress  # draft | approved | in-progress | completed
features:
  - prd: enterprise-multi-tenant
    status: completed
  - prd: enterprise-governance
    status: in-progress
  - prd: enterprise-billing
    status: planned
depends_on: []
---
```

Followed by:
- Goal statement (2-3 sentences)
- Dependency graph between constituent features
- Key decisions / constraints that span features
- Overall status (derived: epic is `completed` when all children are)

**Roll-up**: Active work register groups by epic when epic docs exist, flat list otherwise.

### Layer 3 — Completed Work Archive (Priority: Low — Use Git Instead)

**Decision**: Do NOT create a separate historical register. Instead:

1. Add `completed_at` and `outcome` fields to PRD frontmatter when features finish
2. The scanner can generate a historical view on demand from these fields
3. Git tags + CHANGELOG remain the authoritative history

**Rationale**: Separate registers drift from reality. Enhancing existing frontmatter is zero-maintenance.

---

## New Frontmatter Fields

Minimal additions to existing plan document frontmatter:

| Field | Added To | Purpose | Required |
|-------|----------|---------|----------|
| `epic` | PRD | Links feature to epic doc | Optional |
| `depends_on` | PRD | Cross-feature dependencies (list of PRD slugs) | Optional |
| `completed_at` | PRD | ISO date when feature was completed | On completion |
| `outcome` | PRD | One-line result summary | On completion |
| `branch` | Implementation plan | Active git branch | Recommended |

No changes to progress file format — existing fields (`status`, `blockers`, task tables) are sufficient.

---

## Automation

### Scanner Script (`scripts/generate-active-register.py`)

1. Glob `.claude/progress/*/phase-*-progress.md` — extract YAML frontmatter
2. Glob PRDs — extract status, epic, depends_on, completed_at
3. Glob `.claude/specs/*.md` — extract spec status, category, related PRD (separate table)
4. Glob epic docs — extract feature lists
5. Generate `active-work.md` with timestamp

### Multi-Trigger Refresh Strategy

| Trigger | Mechanism | Phase | Notes |
|---------|-----------|-------|-------|
| SessionStart hook | Run scanner on session start | 1 | Baseline; ensures fresh data even without daemon |
| Command hooks | Regenerate after `/plan:plan-feature`, `/dev:execute-phase`, `/plan:spike` | 1b | Updates at natural planning boundaries |
| File watcher | Watch progress/plan/spec dirs, debounced 5s | 2 | Real-time freshness during long sessions; via CCDash daemon or standalone |
| On-demand | `python scripts/generate-active-register.py` | 1 | Manual fallback; always available |
| CCDash | Read `active-work.md` for board view | 1 | No new scanning logic; new data source |
| `inferred_complete` | Extend existing CCDash pattern | 1 | All phases complete = feature rolls up as complete |

### Prerequisite: Spec Frontmatter Standardization

Before specs can be scanned, all `.claude/specs/*.md` files need structured YAML frontmatter (`title`, `status`, `created`, `updated`, `category`, `related_prd`). Planning skills must be updated to produce specs with this schema.

### What NOT to Automate

- Epic creation (manual — requires human judgment on grouping)
- MeatyCapture integration (MC is request-level; project tracking is a different concern; cross-reference only)
- Historical archive generation (on-demand only, not continuous)

---

## Scope Boundaries

**In scope**:
- Aggregating existing plan/progress data into a single view
- Epic-level grouping for related features
- Automation via scanner script + hooks
- Agent context injection of active work state

**Out of scope**:
- Replacing individual feature plans/progress files
- Manual register maintenance
- Deep MeatyCapture merge (separate concern)
- New UI in CCDash (CCDash reads the generated file — no new features needed initially)

---

## Implementation Sequence

1. **Spike**: Validate existing frontmatter has sufficient data; identify backfill needs
2. **Layer 1**: Scanner script + active-work.md format + pre-session hook
3. **Backfill**: Add `epic`/`depends_on`/`branch` to existing plans as needed
4. **Layer 2**: Standardize epic doc format; convert enterprise-overhaul-roadmap
5. **Layer 3**: Add `completed_at`/`outcome` to PRD template; on-demand historical query

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why | Instead |
|--------------|-----|---------|
| Manually maintained registers | Go stale within days | Derive from frontmatter |
| Deep new frontmatter schema | Maintenance burden, rarely queried | Minimal additions (5 fields) |
| Merging with MeatyCapture | Different granularity (request vs project) | Cross-reference only |
| Continuous historical archive | Drifts from git reality | On-demand generation |
| Agent-authored status updates | Token-expensive, error-prone | CLI scripts + file watcher |
