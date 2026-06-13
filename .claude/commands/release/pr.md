---
description: Full PR workflow — squash-merge stacked branches into main, rebase with --onto, create/merge feature PR, then run changelog-sync and release tasks
allowed-tools: Bash, Task
argument-hint: "[--no-release] [--no-changelog] [parent-branch]"
---

# PR Workflow

Delegate to the `pr-workflow` agent to handle the full stacked-branch merge cycle: `$ARGUMENTS`

## Invocation

Use the `pr-workflow` agent to:
1. Detect the current branch and its parent
2. Squash-merge the parent branch into main (if parent ≠ main)
3. Rebase the feature branch onto updated main using `--onto`
4. Create and merge the feature PR

Pass any `$ARGUMENTS` to the agent for overrides (e.g. explicit parent branch name, `--no-release`).

## Post-merge Tasks (SkillMeat)

After both PRs are merged, unless `--no-changelog` is in `$ARGUMENTS`:

1. Run `/changelog-sync` to audit CHANGELOG coverage for merged commits
2. Unless `--no-release` is in `$ARGUMENTS`, run `/release` to evaluate whether a version bump is warranted

These steps are SkillMeat-specific. Skip them in other projects or when explicitly suppressed.
