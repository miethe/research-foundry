# Provenance Rules

This workflow decides whether the day was shipped, branch-local, docs-only, or empty.

## Evidence Precedence

1. Exact git date-window commits and merges
2. `origin/main` history for the same window
3. Branch divergence (`origin/main...HEAD`)
4. Release tags
5. Dated changelog headings
6. Plan/progress/worknote docs

## Classification Rules

### `empty_day`

Use when:

- no commits land in the target window
- no merges land in the target window
- no dated release heading matches the target date

Allowed context:

- nearest prior visible work, clearly labeled as context only

### `docs_only`

Use when:

- the target window has commits
- the commits are docs/plans/reports/design-only in practice
- there is no mainline shipping proof for live product behavior

Do not describe planned commands, routes, or UI as live features.

### `branch_local`

Use when:

- there is meaningful completed work in the target window
- the work is not proven on `origin/main`
- changelog state remains `Unreleased` or equivalent

This includes completed plans or progress files that did not land in a shipped release.

### `shipped`

Use when one or more of the following is true:

- `origin/main` shows same-window commits or merges tied to the work
- a same-window tag or dated changelog heading proves a shipped release
- release evidence and git history line up

If the same day also contains branch-local follow-up work, keep that separate.

## Common Drift Patterns

- plan status says `completed`, but no shipping evidence exists
- `CHANGELOG.md` has `Unreleased`, but the branch has same-day commits
- a sibling worktree landed related work, but not in the active branch
- a dated changelog section exists, but the local branch view is incomplete

When signals conflict, explain the conflict rather than flattening it.
