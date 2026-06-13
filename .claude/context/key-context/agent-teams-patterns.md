---
title: Agent Teams Patterns
description: When to use Agent Teams vs standard Task() subagents
audience: developers
tags: [teams, orchestration, delegation]
created: 2024-11-15
updated: 2026-05-21
category: orchestration
status: current
---

# Agent Teams Patterns

Use Agent Teams for cross-cutting refactors and parallel-investigation debug sessions where a fixed roster of teammates needs peer-to-peer coordination. For everything else (single-task work, batch ops, multi-phase plans), prefer standard `Task()` subagents.

## Decision Framework

| Criterion | Subagents (Task) | Agent Teams |
|-----------|------------------|-------------|
| Scope | Single task, 1-3 files | Cross-cutting refactor or parallel investigation |
| Duration | Minutes | Session-long investigation or coordinated change |
| Context | Shares parent context | Each teammate gets full 200K context |
| Communication | Returns result to parent only | Peer-to-peer messaging |
| Parallelism | Limited by parent context | True independent parallel with shared roster |
| Coordination | Parent orchestrates all | Task list + direct messaging |
| When to Use | Quick fixes, batch ops, exploration, multi-phase plans | Refactors (same team on every layer), debug sessions |

## When NOT to Use Agent Teams

**Any flow needing `isolation: "worktree"` on a teammate** → Known broken (issue #33045: worktree silently ignored for team-spawned agents). Use plain `Task(..., isolation="worktree", run_in_background=true)` instead.

**Any flow needing `skills:` preload on a teammate** → Known broken (issue #29441: skills frontmatter not preloaded for team-spawned teammates).

**Per-teammate `permissionMode` differentiation at spawn** → Not supported; teammates inherit lead's permission mode (L7 in https://code.claude.com/docs/en/agent-teams#limitations).

**Nested delegation from a teammate** → Teammates cannot spawn teammates (L5). If a workflow needs a teammate to dispatch its own subtasks, use plain `Task()` instead.

## When Agent Teams IS The Right Primitive

**Cross-cutting refactor** — Same agent type works on every layer in lockstep (refactor-team). Example: refactoring repository patterns across API, cache, and web layers in parallel.

**Parallel-investigation debugging** — Fixed roster with peer-to-peer `SendMessage` across files. Example: codebase-explorer searches for patterns while backend-engineer implements fix; both report findings directly.

**Interactive brainstorming** — Human lead + fixed teammate roster for iterative design sessions.

## Team Templates

### Debug Team (Parallel Investigation)

```python
TeamCreate(team_name="debug-team", description="Investigate [issue]")

# Parallel investigation: explorer searches, fixer implements
Task("codebase-explorer", "Search for patterns related to the bug",
     team_name="debug-team", name="explorer")
Task("python-backend-engineer", "Implement fix once root cause is found",
     team_name="debug-team", name="fixer")

# Peers use SendMessage to coordinate
# explorer sends findings to fixer; fixer asks explorer for more context
```

### Refactor Team (Cross-Layer Changes)

```python
TeamCreate(team_name="refactor-team", description="Refactor [system]")

# Same refactor applied in lockstep across layers
Task("python-backend-engineer", "Apply changes to backend layer",
     team_name="refactor-team", name="backend-dev")
Task("ui-engineer-enhanced", "Apply changes to frontend layer",
     team_name="refactor-team", name="frontend-dev")
Task("code-reviewer", "Continuous peer review",
     team_name="refactor-team", name="reviewer")

# Teammates coordinate via SendMessage for cross-layer consistency
```

## Team Lifecycle

1. **Create**: `TeamCreate(team_name=..., description=...)`
2. **Plan**: Create tasks with `TaskCreate`, set dependencies with `TaskUpdate`
3. **Spawn**: Launch teammates with `Task(agent_type, prompt, team_name=..., name=...)`
4. **Assign**: Use `TaskUpdate(taskId, owner="teammate-name")` to assign work
5. **Monitor**: Use `TaskList` to check progress, respond to teammate messages
6. **Coordinate**: Use `SendMessage(recipient="teammate-name", ...)` for peer-to-peer communication
7. **Shutdown**: `SendMessage(type="shutdown_request", recipient="teammate-name")`
8. **Cleanup**: `TeamDelete()` after all teammates have shut down
