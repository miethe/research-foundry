---
description: Prepare a minimal bugfix commit (single change set).
allowed-tools: Bash(git status:*), Bash(git diff:*), Bash(git add:*), Bash(git commit:*), Read(./**), Edit
argument-hint: "[one-line summary]"
---

## Context

- Current git status: !`git status`
- Diff: !`git diff HEAD`
- Branch: !`git branch --show-current`

## Task

Describe the bug and fix in ≤3 bullet points, make the smallest safe change, stage, and craft a single commit message: "$ARGUMENTS".

<!-- MeatyCapture Integration - Project: skillmeat -->
## Post-Commit

Update bug-fixes doc and request-log in one command:

```bash
.claude/scripts/update-bug-docs.py --commits <sha> --req-log REQ-YYYYMMDD-skillmeat
```

**Spec**: `.claude/specs/script-usage/bug-automation-scripts.md`
