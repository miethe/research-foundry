---
type: worknote
schema_version: 2
doc_type: worknote
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: completed
created: '2026-07-31'
updated: '2026-07-31'
---

# AAR — Operator MCP M1 remainder (ex-P4)

**Outcome**: milestone M1 complete. Seven closed adapters landed, gate **APPROVED** on the first
formal round, on tree `76f5a29`. Branch `worktree-operator-mcp-v1` pushed at `d447af9`.
109 adapter tests; full suite 3 failed / 2371 passed (the 3 are the documented baseline).

This is the first milestone in this workstream to reach an APPROVED verdict without a fix-and-
re-gate loop. That is the result worth explaining.

## What actually produced the clean gate

**The pre-gate did the work the gate would otherwise have done.** Two cheap lenses found six
defects — three BLOCKING — on a tree where all 97 adapter tests passed and regression was clean.
Had those gone into the formal gate, this would have been a CHANGES_REQUESTED round plus a fix
cycle plus a re-gate: the exact three-round shape P1 and P2 both paid for.

**Lens diversity, quantified.** Both lenses found F1 and F6. codex alone found F2, F3, F4, F5.
ICA alone established that F1 *silently succeeds* rather than raising, and reproduced F6
empirically across a real workspace boundary. ICA refuted H3 while codex found a different defect
in the same file. **A single deeper pass would have missed four of six.** This is the third
consecutive milestone where diversity beat depth; it should stop being treated as an experiment.

**Seeding the pre-gate with named hypotheses paid off.** Six hypotheses went in (H1–H6) drawn from
reviewing the implementers' own flagged judgment calls. Three were confirmed, three refuted — and
the refutations were as useful as the confirmations, because they closed questions that would
otherwise have consumed gate attention. Two of the six defects (F3, F4) were found *outside* the
seeded hypotheses, so seeding focused the lenses without narrowing them.

## The uncomfortable finding

**The orchestrator's own contract caused a BLOCKING defect.** Contract §D1 correctly removed the
`sensitivity_ceiling` *parameter* from every adapter — the exact fix that closed the HIGH fail-open
at all five P3 boundaries. It left the **sibling** caller-supplied `sensitivity` input feeding the
very guard the ceiling protects (F3). That is defect class 1's own warning — "check the producer,
not the field" — applied one level too shallowly, by the party writing that checklist into every
implementer prompt.

**Lesson: a contract that hardens a field must enumerate every sibling input reaching the same
guard.** The "fix the layer below" discipline the plan demands of implementers applies with equal
force to the contract directing them. Contracts are code.

Corroborating pattern: **three of six defects were sibling-parameter bypasses of a correct guard**
— F2 (`target_run_id` beside a properly re-derived `workspace_id`), F3 (`sensitivity` beside the
removed ceiling), F5 (explicit paths beside an authorized run target). In every case the guard was
right and the *parameter inventory* was incomplete. A per-adapter table — "every caller-supplied
input reaching the canonical service, and what authorizes each" — would plausibly have caught all
three before review, at a fraction of a review round's cost. **This is the single highest-value
change to carry into M2.**

## What else worked

- **Decide the design questions before offloading.** Scoping surfaced seven open questions; four
  were traced to definitive code facts and decided in the contract *before* any implementer ran.
  The two that mattered most — the substrate has no channel for "ran fine but the verdict failed",
  and `build_bundle` provably never blocks — would each have produced a wrong implementation if
  handed over as ambiguity. Offloading is safe against a decided contract, not against an open one.
- **Fix legs were told about each other's findings.** The `research_stages` fixer was warned about
  F6 (a pre-authorization existence leak being fixed concurrently in another file) and deliberately
  ordered its new gate *after* authorization instead of copying the then-current shape. Cheap
  cross-pollination prevented a fresh instance of a known defect.
- **Checklist item 2 paid out inside the fix cycle** — applying "fix the layer below" to its own
  fix, the `research_stages` leg found the same silent-success class one hop upstream in
  `run.extract`. Neither review lens had reported it.
- **Both ICA legs reported their judgment calls honestly** rather than silently guessing: leg A
  surfaced the `_REQUIRED_TARGET_KINDS` gap the contract missed; leg B flagged its own
  workspace-declaration choice for review. Offloaded legs are trustworthy about *uncertainty* when
  the prompt makes flagging a first-class outcome.

## Routing

Legs A and B (five mechanical adapters) ran on the ICA free lane; leg C (verify/bundle, carrying
the governed-result design) claude-primary. **When the pre-gate returned authorization and
confirmation-binding defects, every fix was re-routed claude-primary** — F4 sits on the P1
confirmation surface, which is MUST-stay. The durable rule: *thin-wrapper authoring is
offload-eligible; closing an authorization finding in the same file is not.* The boundary is the
nature of the work, not the file.

## Process defects found (all filed as ITT nodes)

- **A vacuous AC.** M1's "closed dispatch, no CLI reach" check grepped two paths that never
  existed. `rg` on a missing path exits 0 with zero matches, so it satisfied its own evidence bar
  while inspecting nothing — the hollow-evidence class reached by accident rather than by an agent
  cutting a corner. **Standing rule proposed: every zero-match AC command must assert its scanned
  paths exist.**
- **"Rebase before resuming" was an instruction with no mechanism.** The branch sat 4 commits
  behind, reading a superseded 731-line plan while main carried the 798-line milestone retrofit.
  An executor that started without checking would have implemented against retired task IDs.
- **Two fix legs used `git stash` inside a worktree.** The stash stack is shared across all
  worktrees and concurrent sessions; a `stash`/`pop` pair races anyone else's entry. Both restored
  correctly and the stack was verified clean after each, but "stash the source, keep the new test,
  confirm it fails" should be replaced with a scratch copy in implementer prompts before it bites.
  The *intent* — proving a regression test fails pre-fix — is excellent and should be kept.

## Carry into M2

1. Require the per-adapter caller-input/authorization inventory table. Highest-value item here.
2. Keep two diverse cheap pre-gates before the formal gate; seed them with named hypotheses drawn
   from the implementers' own flagged judgment calls.
3. Treat the contract as reviewable code — sibling-input enumeration is part of writing it.
4. M2's preview negative proof and every adversarial security lens stay claude-primary and
   fresh-context (unchanged plan constraint; codex refuses adversarial-audit framing on this
   workstream — do not retry).
5. Replace `git stash` with a scratch copy in the pre-fix-failure verification recipe.
