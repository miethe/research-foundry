# Plan Bookkeeping Rule (Global)

**Purpose**: Stop the three recurring mechanisms behind plan/tracker drift (unreachable commit refs, split progress trackers, and status/criteria contradictions) so tracking artifacts stay trustworthy without a dedicated audit pass.

## Invariants

1. **`commit_refs` holds only commits reachable from `main`.** Never a tree id, never a pre-squash
   worktree commit. Verify every entry with `git merge-base --is-ancestor <sha> main` before writing
   it — `git log -1 <sha>` SUCCEEDS on an orphaned commit because it resolves the object, not a ref,
   so it is not proof of reachability. Rationale: this repo squash-merges and deletes worktree
   branches (per `git-workflow.md`), so any sha cited from a worktree at review time goes unreachable
   the moment the squash lands, and will eventually be garbage-collected.

2. **Review approvals are cited as `<commit> / <tree>` pairs; never let the tree half reach
   `commit_refs`.** The pair is for reverifying exact reviewed content in prose. When assembling
   frontmatter, collapse each pair to its commit and then apply invariant 1. A real instance:
   `26e8f77…` was written into `commit_refs` and was literally the tree of `9cf7e6b…`, the entry
   above it.

3. **Progress trackers live in two places; a closeout pass must reconcile both.**
   Codex-executed phases write `.codex/progress/<feature>/phase-N-progress.md`; Claude-orchestrated
   phases write `.claude/progress/<feature>/phase-N-progress.md`. Both are git-tracked and legitimate
   records. Before concluding a phase never closed, check for the twin under the other convention.
   When flipping a root plan to `completed`, flip every phase file in the same pass.

4. **Sibling plans must not reuse phase ids.** Where two plans in the same feature family both number
   phases (e.g. `reusable-assertion-ledger-v1` P0–P8 and `assertion-ledger-activation-v1` P1–P6),
   commits get cross-attributed between them. Attribute a commit to a plan by which plan's files it
   touches (`git show --name-only <sha> | grep 'features/<slug>'`), never by the phase label in the
   commit subject. When authoring a new plan in an existing family, prefix phase ids with the
   feature slug or continue the family's numbering.

5. **Status values come from the repo's own vocabulary.** Use `completed`, not `complete`. Check what
   sibling artifacts use before inventing a value.

6. **Use a surgical `Edit` for status/frontmatter flips — never `manage-plan-status.py`.** The CLI
   reflows the entire frontmatter (quotes, flow→block lists, dates, `wave_plan`), churning ~231 lines
   for a one-field change. Reserve the CLI for `.claude/progress/*` files where formatting is
   immaterial.

7. **A `completed` status must not contradict its own `exit_criteria`.** If an exit item is deferred,
   annotate that criterion in place with the deferral and its gate, so status and criteria agree on
   later read.

## Notes

- A plan doc, its phase files, both progress dirs, and the IntentTree node are five independent
  surfaces. Disagreement among them is the normal case, not the exception — reconcile all five, and
  treat any single one as a claim rather than as truth.
