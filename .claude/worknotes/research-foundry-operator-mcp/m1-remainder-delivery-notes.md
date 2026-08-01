---
type: worknote
schema_version: 2
doc_type: worknote
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: in_progress
created: '2026-07-31'
updated: '2026-07-31'
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
---

# M1 remainder (ex-P4) — delivery + AAR capture

Running capture for the delivery-report and the AAR. Append as the run proceeds; do not
retro-fit at the end.

## Run context

- **Scope**: the second half of milestone **M1** — external import adapter + six canonical
  research-stage adapters (ingest, extract, claim-map, synthesize, verify, bundle) + the
  cross-stage seam gate. Supersedes the retired `OPM-4.x` task IDs.
- **Branch/worktree**: `worktree-operator-mcp-v1` @ `.claude/worktrees/operator-mcp-v1`.
- **Gate for M1** (per plan): `task-completion-validator` only. No Karen pass at M1; no
  mandatory security lens at M1 (those are P1 / P2 / M2-preview / M3-final).
- **ITT tree**: `tree_01KVTH95G09FX26HCRPBV77DAE` (research-foundry).

## Timeline

### 2026-07-31 — pre-flight

1. **Branch was 4 commits behind main and reading a superseded plan.** The worktree copy of the
   implementation plan was the 731-line phase-based version; main carried the 798-line
   milestone-doctrine retrofit (`230b224`). The plan itself instructs *"rebase that branch onto
   main before resuming so the executor reads these milestones and not the superseded P3–P6 phase
   sections"* — that step had not been done. Merged main → branch at `837b856`.
   - **Conflict 1** (`docs/.../research-foundry-operator-mcp-v1.md`, 22 hunks): resolved by taking
     main wholesale. Justified by the plan's own stated convention — *"the plan document itself is
     maintained on main; the code stays on the branch."* The branch's copy was strictly older
     (execution status "as of 2026-07-29", claiming P2–P6 not started, when P2 and P3 were done).
   - **Conflict 2** (`src/research_foundry/api/auth/provider.py`): both sides had independently
     performed the *same* serve-extra decoupling of `AuthIdentity` — main via `deff14f`, the branch
     via the P3 "serve-extra closure" (`9ddb087`). Resolved to the union import minus the now-dead
     `dataclass` (`AuthIdentity` no longer defined in this module; it is re-exported from
     `research_foundry.auth_identity`).
   - **Validation**: `tests/unit` → 3 failures, all three reproduced identically on `main`
     (`test_assertion_rollout.py` ×2, `test_report_anchors.py` ×1) ⇒ pre-existing baseline, not
     merge-induced.

2. **Routing resolved via `delegation-router`** (dispatch-time, per plan frontmatter
   `routing_constraints` — the plan deliberately pins no model ids):

   | Leg | task_class | Resolved | Rationale |
   |---|---|---|---|
   | Exploration / contract | `exploration` | claude sonnet-5 | short, on the critical path |
   | Adapter implementation | `implementation` | ICA `claude-sonnet-5[1m]` (free lane) | offload-eligible: these adapters *consume* the P1 confirmation/authorization policy, they do not author it |
   | Cheap pre-gate sweep | `code_review` | gpt-5.6-terra + ICA (diverse lenses) | see "lens diversity" below |
   | Milestone gate | `verdict` | MUST-stay claude | router hard-override |

   **MUST-stay boundary enforced in the implementer prompt**: no edits to
   `operator_mcp_policy.py` or any confirmation/authorization semantics — stop and report instead.

## Observations for the AAR

- **O-1 — Stale router registry.** `delegation-router`'s `model-registry.yaml` resolves ICA sonnet
  to `claude-sonnet-4-5[1m]`, but `~/.claude/ica-settings.json` has served `claude-sonnet-5[1m]`
  since 2026-07-08. The router's `reason` string therefore names a model the lane no longer runs.
  Not blocking (the alias resolves), but the RoutingRecord is inaccurate as an audit record.
  → follow-up ITT node.
- **O-2 — "Rebase before resuming" was a plan instruction with no mechanism.** The plan told the
  executor to sync the branch; nothing enforced it, and the branch sat 4 commits behind reading a
  superseded plan. Any executor that had started M1 from the worktree without checking would have
  implemented against retired `OPM-4.x` task tables. → candidate for a pre-flight hook.
- **O-3 — Lens diversity is the demonstrated winner on this workstream.** P3's own record: the
  cheap gpt-5.6/ICA pre-gate passes caught five defects (G1–G6) on a tree that had already passed
  mutation-matrixed implementation *and* independent orchestrator re-verification; and the
  validator lens caught P3's most serious defect (the `sensitivity_ceiling` no-op) that the
  security lens's own round missed. Carrying that forward: run **two cheap diverse pre-gates**
  (gpt-5.6 + ICA) before the validator, not one deeper pass.

### 2026-07-31 — finding F-M1-1 (plan defect, found pre-implementation)

**The M1 "closed dispatch, no CLI reach" AC command was vacuous.** The plan's AC→command→evidence
matrix verified it with:

```
rg -n "typer|cli_commands|subprocess|os\.system|shell=True" \
   src/research_foundry/services/operator_tool_adapters.py \
   src/research_foundry/operator_mcp/
```

Neither path exists. `operator_tool_adapters.py` was never created — P3 implemented the adapters as
a **package**, `src/research_foundry/services/operator_mcp_adapters/` (`base.py`, `run_plan.py`,
`swarm_start.py`, `job_lifecycle.py`) — and `operator_mcp/` does not land until M2. `rg` on a
missing path writes to stderr and **exits 0 with zero matches**, so the command satisfies its own
stated evidence bar ("Zero matches in registered handler call paths") while inspecting nothing.
This is precisely defect class 4 (fabricated/hollow validation evidence) reached by accident rather
than by an agent cutting a corner.

The same stale name appears in 8 places: `files_affected`, three serialization-barrier lists, the
barrier prose (×2), and three AC-evidence commands. The two `pytest tests/unit/test_operator_tool_adapters.py`
commands fail loudly (usage error, non-zero) rather than silently, so only the `rg` row was a false
pass — but all eight were drift.

**Fixed on the branch**: all references repointed to `operator_mcp_adapters/` and
`tests/unit/test_operator_mcp_adapter_*.py`; the `rg` row now carries an explicit
"verify the paths exist first" caveat.

**Carry-back required**: the plan document is maintained on `main`, so this correction must be
applied there too — it is currently only on `worktree-operator-mcp-v1`.

**Generalizable lesson**: an `rg`-based negative-proof AC is only evidence if the paths are asserted
to exist. Any "zero matches = pass" check needs a companion existence assertion, or it degrades into
a guaranteed pass the moment a file is renamed. Worth a standing rule in the plan-authoring guidance.

### 2026-07-31 — implementation, pre-gate, fix cycle 1

**Implementation** (`fcfcd89`). Seven adapters across three parallel legs with disjoint file
ownership; `__init__.py` registration held by the integration owner. Routing per
`delegation-router`: legs A (`run.extract`/`claim_map`/`synthesize`) and B
(`external_report.import`/`source.ingest`) to the ICA free lane; leg C (`run.verify`/`run.bundle`,
carrying the governed-result design) claude-primary. 12 adapters register (5 from P3 + 7).
97 adapter tests; full suite 3 failed / 2359 passed, the 3 being the documented baseline.

**Pre-gate** — two cheap diverse lenses in parallel (gpt-5.6-terra at high effort; ICA
sonnet-5[1m]), per observation O-3. **Six defects, three BLOCKING**, on a tree where every test
passed and regression was clean. Consolidated at `.claude/findings/m1-remainder-pregate-consolidated.md`.

**Fix cycle 1** (`76f5a29`). All six closed; 109 adapter tests; full suite 3 failed / 2371 passed.
Every regression test confirmed to fail against pre-fix source before passing.

## Observations for the AAR (continued)

- **O-4 — Lens diversity confirmed a third time, and this run quantifies it.** Both lenses found
  F1 and F6. **codex alone** found F2, F3, F4, F5. **ICA alone** established that F1 *silently
  succeeds* rather than raising (materially worse than the hypothesis) and reproduced F6
  empirically across a real workspace boundary. ICA **refuted** H3 while codex found a *different*
  defect in the same file. Neither lens was a superset of the other; a single deeper pass would
  have missed four of six. Cost was a fraction of the implementation legs.
- **O-5 — The orchestrator's own contract caused a BLOCKING defect.** §D1 correctly removed the
  `sensitivity_ceiling` *parameter* — and left its **sibling**, the caller-supplied `sensitivity`
  input, feeding the very guard the ceiling protects (F3). This is defect class 1's own warning
  ("check the producer, not the field") applied one level too shallowly, committed by the party
  writing the checklist into everyone else's prompt. **Lesson: when a contract hardens a field,
  it must enumerate every sibling input that reaches the same guard** — the same "layer below"
  discipline the plan demands of implementers applies to the contract that directs them.
- **O-6 — Three of six defects were sibling-parameter bypasses of a correct guard** (F2
  `target_run_id` beside a properly re-derived `workspace_id`; F3 `sensitivity` beside the removed
  ceiling; F5 explicit paths beside an authorized run target). The guards were right; the
  parameter *inventory* was incomplete. A per-adapter "enumerate every caller-supplied input that
  reaches the canonical service, and state what authorizes each" table would likely have caught all
  three before review. Cheaper than a review round.
- **O-7 — A test pinned the unsafe behavior again** (F4: the parity test minted a confirmation
  without `content`, then invoked *with* content and asserted success). Third occurrence of defect
  class 3 on this workstream. The fix inverted it rather than adding a sibling test — worth
  keeping as the standing remedy, since an added test leaves the wrong assertion in place.
- **O-8 — Fix legs correctly avoided reproducing each other's defects.** The `research_stages`
  fixer was told about F6 (the pre-authorization existence leak being fixed concurrently in
  another file) and deliberately ordered its new prerequisite gate *after* authorization rather
  than copying `verify_bundle`'s then-current shape. Cross-pollinating findings between concurrent
  fix legs is cheap and prevented a fresh instance of a known defect.
- **O-9 — Checklist item 2 paid out inside the fix cycle.** Applying "fix the layer below" to its
  own fix, the `research_stages` leg found the same silent-success class one hop upstream in
  `run.extract` (zero source cards) — a defect neither review lens had reported.
- **O-10 — Offload boundary held, and the re-route was the right call.** ICA authored five of
  seven adapters cleanly against a decided contract, and both ICA legs reported their judgment
  calls honestly rather than silently guessing (leg A surfaced the `_REQUIRED_TARGET_KINDS` gap
  the contract missed; leg B flagged its own workspace-declaration choice for review). But when
  the pre-gate returned authorization and confirmation-binding defects, **all fixes were routed
  claude-primary** — F4 sits on the P1 confirmation surface, which is MUST-stay. Thin-wrapper
  authoring is offload-eligible; closing an authorization finding in the same file is not.
- **O-11 — Two fix legs used `git stash` in a worktree.** The shared stash stack is visible to
  every worktree and to other concurrent sessions; a `stash`/`pop` pair races anyone else's entry.
  Both legs restored correctly and the stack was verified clean after each, but "stash the source,
  keep the new test, confirm it fails" is a pattern worth replacing with a scratch copy or
  `git worktree add` in implementer prompts before it bites.
