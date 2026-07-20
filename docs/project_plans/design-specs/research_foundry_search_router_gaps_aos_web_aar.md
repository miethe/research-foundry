---
schema_version: 0.1
id: aar-2026-07-20-search-router-gaps-aos-web
type: after_action_review
title: AAR — Search Router Gap-Closing + aos-web/SearXNG Discovery Lane
project: Research Foundry
owner: Nick Miethe
created_at: 2026-07-20
related:
  - docs/project_plans/design-specs/research_foundry_search_router_spec.md
  - docs/project_plans/design-specs/research_foundry_search_router_implementation_plan.md
  - docs/project_plans/design-specs/research_foundry_search_router_aar.md
  - docs/project_plans/implementation_plans/features/search-router-gaps-aos-web-v1.md
merge_commit: c3a2545
tags: [search-router, aos-web, searxng, execute-plan, reconciliation, aar]
---

# AAR — Search Router Gap-Closing + aos-web/SearXNG Discovery Lane

**What:** `/execute-plan` on the search-router "P2–4 + aos-web" theme (effort: ultracode).
Reconciled the shipped MVP (`d119993`) against the IntentTree nodes via 3 parallel recon agents,
authored a fresh gap-closing wave-plan, ran a 4-wave execute-plan workflow, and squash-merged to
`main` (`c3a2545`). 16 agents, ~2.6M subagent tokens, 135 tests green.

## What went well

- **Reconcile-before-execute caught a false premise.** The literal ask (execute-plan the design-spec)
  was impossible as stated — the spec and its impl-plan had **no `wave_plan` frontmatter**, and "P2–4"
  was mostly already-done (P2 MCP server real in the MVP) or a real gap the MVP AAR wrongly reported as
  done (P3 CCDash/SkillMeat — only generic pre-router machinery existed, nothing search-specific).
  Recon reclassified P2=finishing / P3=real gap / P4=deferred; authoring a new gap+aos-web wave-plan
  was correct, not fabricating a graph over the spec.
- **Branch isolation neutralized the known fix-cycle-to-main hazard.** Ran the whole workflow on a
  feature branch (`isolation: shared`) off local HEAD via plain `git checkout -b` (NOT EnterWorktree,
  which the workflow ignores). `main` stayed pinned at `a82ebf9` the entire run; Opus owned the single
  squash. This is the recommended pattern: branch-first, squash-last, never run execute-plan on `main`.
- **Authoritative post-run validation over self-reports.** Confirmed the `writeback.py`/`telemetry.py`
  Pyright/ruff findings were **pre-existing** (byte-identical code on `main`, `E402` present on `main`);
  ran mypy + ruff + pytest on scope before the squash.

## What went wrong / friction

- **Workflow report unreliable.** Wave 3 reported two failed "undefined"/empty task-envelope dispatches
  AND re-dispatched work that was already committed — only git-history reconciliation (by the reviewer
  and by Opus) revealed the true state. Trust `git log main..HEAD`, not the workflow's per-task status.
- **"never `git add -A`" not honored.** An agent swept unrelated uncommitted WIP (`.claude/agents/dev/*`)
  into a commit despite the explicit prohibition in its prompt; excluded at squash via
  `git restore --staged` (restoring it to the original uncommitted state).
- **haiku doc agent inaccessible** — `documentation-writer` ran as a direct Mode-B task (known env
  limitation; [[haiku-subagents-inaccessible]]).

## Lessons

1. For "execute-plan `<spec>`" requests, verify `wave_plan` frontmatter EXISTS first. If not, reconcile
   the substrate and author a real plan before any run — the spec being called a "plan" doesn't make it
   one.
2. Run execute-plan on a dedicated feature branch, never `main`; verify `git log main..HEAD`, not the
   workflow report; confirm scope with `git diff --cached --stat` and strip swept-in WIP before squash.
3. The MVP AAR overstated P3 completeness ("already reused"). Evidence-audit reconciliation, not a prior
   AAR, is the authority for what actually shipped.

## Follow-ups (deferred)

- **Live-provider validation** (real keys) for the 5 paid providers AND the new aos-web/SearXNG lane
  against a live SearXNG — everything remains offline-validated only.
- **P2 budget governance** — server-side budget ceiling + enforcing `requires_human_approval`
  (currently recorded, never consulted).
- **P4** monitoring/repo-scout still deferred (stub `monitoring_delta` mode only).
- `source_type` vocabulary unification (carried from the MVP AAR).
