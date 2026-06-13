---
paths:
  - ".claude/progress/**/*.md"
---

# Progress File Rule (Path-Scoped)

## Invariant

**Never use Edit, Write, or MultiEdit to modify progress file YAML frontmatter.**

Progress files use structured YAML frontmatter (task status, metrics, completion %). Direct edits risk YAML syntax errors, missed metric recalculation, and inconsistent timestamps. Use the CLI scripts instead — they handle all of this automatically.

## What To Do Instead

| Operation | Command |
|-----------|---------|
| Mark task complete | `python .claude/skills/artifact-tracking/scripts/update-status.py -f FILE -t TASK-ID -s completed` |
| Mark task blocked | `python .claude/skills/artifact-tracking/scripts/update-status.py -f FILE -t TASK-ID -s blocked -n "reason"` |
| Batch update (2+ tasks) | `python .claude/skills/artifact-tracking/scripts/update-batch.py -f FILE --updates "TASK-1.1:completed,TASK-1.2:completed"` |
| Append commit SHA | `python .claude/skills/artifact-tracking/scripts/update-field.py -f FILE --append "commit_refs=SHA"` |
| Mark phase complete | `python .claude/skills/artifact-tracking/scripts/update-status.py -f FILE -t __phase__ -s completed` |

Valid status values: `pending`, `in_progress`, `completed`, `blocked`, `at_risk`

## Exceptions (When Direct Edit IS Allowed)

- **Creating** a new progress file (planning agents only, via `artifact-tracker` agent)
- **Adding blockers with resolution plans** that need free-text markdown (via `artifact-tracker` agent)
- **Appending implementation notes** to the markdown body (below the `---` frontmatter delimiter)

## Why This Exists

Agents repeatedly attempt `Edit()` or `Update()` on progress frontmatter to update task status. This triggers `.claude/` path protection prompts and risks YAML corruption. The CLI scripts cost ~50-100 tokens vs ~4000+ for an agent edit cycle, recalculate metrics automatically, and never trigger permission prompts.
