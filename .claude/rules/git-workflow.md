# Git Workflow Rule (Global)

**Purpose**: Make commit + integration automatic on completion so agents don't re-ask every time.
This is a project convention that **overrides** the generic harness default ("commit/push only when
the user asks") for commit + local merge. Pushing to a remote still requires an explicit request.

## Invariants

1. **Commit on completion.** When a unit of work is complete **and validated** (tests/build/lint or an
   explicit sanity check pass — state what was checked), commit it. Do not wait to be asked to commit.

2. **Squash-merge on completion.** After committing, squash-merge the working/feature/worktree branch
   into its integration target as **one clean commit per unit of work**.

3. **Default target = the current working branch.** Merge to `main` **only when explicitly directed**
   (e.g., "merge to main", "squash to main"). When unsure which non-main target, ask; never merge to
   `main` by default.

4. **Push is still gated.** Commit and merge **locally** by default. `git push` (and anything outward-
   facing — PRs, releases) happens **only when the user explicitly asks**.

5. **Validate before the merge, not after.** Run the applicable suite for the changed scope
   (`pytest` / `pnpm test` / `tsc --noEmit` / `flake8`) before squash-merging. If validation fails, do
   not merge — report.

6. **Worktree flow.** For worktree branches: commit on the branch → squash-merge to the directed target
   → remove the branch + worktree once integrated (no orphan branches).

7. **Commit message trailers.** End commit messages with the standard Co-Authored-By and Claude-Session
   trailers. Conventional-commit prefixes (`feat`/`fix`/`docs`/`chore`/`refactor`) by scope.

## Notes

- "Complete" means the requested deliverable is done and verified — not a partial/in-flight checkpoint.
  An in-progress checkpoint commit is fine on the working branch, but do not squash-merge incomplete work.
- This rule does not authorize destructive history rewrites on shared branches (no force-push to `main`).
