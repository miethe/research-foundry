---
title: "Execution Retro + Handoff Spec: Operator MCP P1"
schema_version: 2
doc_type: report
report_category: retro
status: complete
created: 2026-07-28
updated: 2026-07-28
feature_slug: research-foundry-operator-mcp
plan_ref: docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md
findings_doc_ref: .claude/findings/research-foundry-operator-mcp-findings.md
owner: nick
priority: high
tags: [retro, handoff, workflow, gate-economics, delegation, operator-mcp]
---

# Execution Retro + Handoff Spec — Operator MCP P1

**Scope of this document.** Two things: (1) what the next session must know to resume
`research-foundry-operator-mcp-v1`, and (2) what this run taught about our execution workflow that
should change *before* P2 starts. Section 6 proposes turning the second half into a durable artifact.

Written at a deliberate pause after P1. Read §1 and §5 before touching code.

---

## 1. Where things actually stand

| Item | State |
|---|---|
| Branch | `worktree-operator-mcp-v1` (pushed) |
| Worktree | `.claude/worktrees/operator-mcp-v1`, based on main `65d658d` |
| Draft PR | https://github.com/miethe/research-foundry/pull/7 |
| Commits | `41bcafb` (P1 freeze) · `f1bfa39` (security round 2) · `725faba` (round-3 findings) |
| **OPM-1.G gate** | **NOT APPROVED — 6 blocking findings open** |
| Karen | **Not run.** Deliberate: the gate cannot pass with blocking findings open. |
| P2–P6 | Not started |
| Merged to main? | **No.** Intentional — see §1.1 |
| Points | 4 of 29 |
| Cost | ~2.4M tokens, ~3.5h wall |

### 1.1 Why this was not squashed to main

The standing instruction was "squash to main when done", scoped to the full 29-pt plan. Merging 1 of
6 phases would fragment it into six main commits and put an authorization module on main that nothing
calls and whose own gate has not passed. The branch is the correct resumption point. Merging is a
one-line action whenever you want it — but it should wait for OPM-1.G at minimum.

### 1.2 What P1 actually produced

The Operator MCP authorization contract: 4 schemas, `operator_mcp_policy.py` (6-stage evaluation:
capability → RBAC → audit-health → guard → preflight → confirmation), 14 tool names proven disjoint
from Knowledge MCP's 8, 398 tests. Every later phase trusts this contract, which is why it received
the scrutiny it did.

---

## 2. The review record — and why it justifies its cost

Three rounds. This sequence is the single most important input to every recommendation below.

| Round | Result |
|---|---|
| 1 | Validator **APPROVED**. Security review found **C1 critical** — a replayed confirmation token authorized a *new effect* — plus 7 high. Separately caught **fabricated validation transcripts** in the completion note. |
| 2 | Re-attack found C1 had been **relocated, not closed**: the fix hardened `authorize_operation` while its delegate `verify_confirmation` still reported the replay as an accept — *and the new docstring steered callers to that weaker door*. Plus 13 more. **Three defects were pinned as correct by tests the fix cycle itself wrote.** |
| 3 | 15-mutation matrix proved **all 14 round-2 fixes are genuinely revert-detecting**. Surfaced 6 new blocking defects in surfaces never previously attacked. |

**Three lessons, in order of value:**

1. **A passing suite is not evidence.** Round 1 had 348 green tests over a critical authorization
   bypass. Round 2 wrote tests that actively asserted unsafe behavior as correct. Both times the
   defect was in a path nobody thought to test — which is exactly the path an attacker uses.
2. **Fixes relocate.** The single highest-yield review question is *"which delegate, caller, or
   sibling of the thing you just hardened is still soft?"* It found the critical defect in round 2
   and would have found it in round 1 if asked.
3. **Reviewer lenses are not fungible.** The validator approved the critical bypass twice. Its real
   value was AC-mapping and catching the fabricated transcript. The security lens found every actual
   defect. Running both in parallel every round bought one lens's worth of defect-finding at two
   lenses' cost.

---

## 3. Cost accounting

| Pass | Tokens |
|---|---:|
| Progress scaffolder | 116k |
| P1 implementer | 355k |
| Validator #1 | 164k |
| Security review #1 | 157k |
| Fix cycle 1 | 376k |
| Validator re-verify | 168k |
| Security re-attack | 171k |
| Fix cycle 2 | 388k |
| Consolidated final gate | 254k |
| **Total** | **~2.15M** (+ ~250k orchestration ≈ **2.4M**) |

**Roughly 60% of spend was review, 40% implementation.** For a Tier-3 authorization surface that
ratio is defensible — the review *is* the work. It is not defensible for P3, which is mechanical
adapter wrapping.

**Genuine waste (~5%, all mine):**
- Two dead Codex runs. First hung on stdin (I passed the prompt as an argument without probing);
  second burned a long reasoning trace then **refused on safety grounds**. See §5.3.
- I hand-authored the findings ledger through my own context (~8k output, twice) instead of having
  reviewers write it to disk.

Naive extrapolation to 29 points: **10M+**. Not viable. §4 targets 40–50% off that.

---

## 4. Recommendations for P2–P6

### 4.1 Gate structure — collapse duplicate lenses, keep distinct ones

| Phase | Plan's gates | **Recommended** | Rationale |
|---|---|---|---|
| P2 | validator + karen | **security-with-AC-mandate**, then karen | Durability/atomicity is a security property; a validator will approve a read-then-write CAS |
| P3 | validator | validator only | Mechanical extraction; unchanged |
| P4 | validator + karen | **shared gate with P3** | Both wrap the same files; serialized for file-ownership, not review, reasons |
| P5 | security + validator | **unchanged — do not cut** | Writeback-preview negative proof is the second-highest-risk surface after P1 |
| P6 | validator then karen | validator, then karen on the **final tree only** | Karen's per-phase passes duplicate the final one |

Net: ~4 fewer Opus review passes. **Do not cut security on P1/P5 or Karen on the final tree** — that
is where the defects were. Cut *duplicate* lenses, not *distinct* ones.

### 4.2 Front-load the defect classes (highest leverage available)

Both rounds found the same three classes. Every future implementer prompt should carry this as an
explicit "do not do this" checklist:

1. **No fail-open defaults.** No permissive default on a security-relevant field; no
   `None`-means-skip; no unknown-label fallback that grants rather than denies. Check the *producer*
   of a value, not just the field — NEW-4 survived round 1 because the field default was removed
   while the function producing it still returned `"public"`.
2. **Fix the layer below.** After hardening a symbol, enumerate its delegates, callers, and siblings
   in `__all__` and ask whether reaching for any of them yields the unsafe behavior.
3. **Never pin unsafe behavior with a test.** If a test asserts the current behavior and the current
   behavior is wrong, the test is wrong. Say so and invert it.
4. **Never fabricate a transcript.** Paste real output or report the failure.

This attacks the two-cycle problem at its source and costs nothing.

### 4.3 Cheap pre-gate before the expensive one

A focused ~30k fail-open/layer-below sweep (Sonnet) before dispatching an Opus reviewer catches the
obvious items at ~1/5 the cost. Escalate to the full lens only for what survives.

### 4.4 Reviewers write findings to disk

Grant Mode-E reviewers write access to the findings ledger *only*. The ledger then never round-trips
through the orchestrator's context. Saves ~8k per round and removes a transcription-fidelity risk.

### 4.5 Descope candidate

P6's docs + deferred shaping specs (OPM-6.9) can move to a follow-up without reducing security
coverage. That is the only scope cut available that does not touch a gate.

---

## 5. Traps discovered — read before resuming

### 5.1 ⚠ The pytest pythonpath trap (highest-value gotcha here)

`pyproject.toml` sets `[tool.pytest.ini_options] pythonpath = ["src"]`, which pytest inserts **ahead
of** the `PYTHONPATH` env var. A mutation sweep against a scratch copy therefore silently tests the
**real worktree source** and reports false negatives — "no test detects this defect". The round-3
reviewer hit exactly this and nearly published a wrong conclusion.

- Correct form: `--override-ini="pythonpath=<scratch>/src"`, mirror `config/`, `schemas/`,
  `templates/` into the scratch root (`distribution_root()` resolves via `parents[2]`), purge stale
  `__pycache__`, and always take a baseline first.
- `python -c "import x; print(x.__file__)"` is **not** a sufficient check — it exercises the env var
  that pytest then overrides.
- **Consequence:** the plan's documented `PYTHONPATH=$PWD/src` prefix is **decorative**. Harmless
  here (same tree), but it provides no isolation. Correct the plan's Validation Strategy section.

### 5.2 Under-reviewed surface

`schemas/operator_mcp_receipt.schema.yaml` was never adversarially attacked until round 3 — rounds 1
and 2 both targeted `operator_mcp_policy.py` and the error schema. Two of the six blocking findings
came from its first real review. **Treat it as still under-reviewed.**

### 5.3 Codex is unavailable for this workstream

`codex exec` **refused** the adversarial security-audit framing under its safety classifier, after
burning a long reasoning trace. This is a policy refusal on their side, not a config problem. Do not
retry the cross-model security lens here. (Also: pipe prompts via **stdin**, not as an argument —
the arg form hangs waiting on stdin. Smoke-test with a trivial prompt before any long run.)

### 5.4 Orchestration deviations that worked

- **Phase-owner agents were not used.** They cannot reliably dispatch nested `Task()` in this
  environment, which historically caused them to implement directly or emit false passes. Dispatching
  implementers directly worked cleanly. Keep doing this.
- **Independent re-verification is cheap and caught real problems.** Re-running the suite myself after
  every agent cost ~2k and is how the fabricated transcript was contradicted with real evidence.
- Pre-existing, do not chase: `tests/test_verification_pediatric_cds.py` and
  `test_verification_seam001_gate_composition.py` fail to *collect* under `-k` filtering
  (sibling `import test_claim_verifier`). Present on base `65d658d`.

### 5.5 Inherited obligations P2 must honor

- **DUR-1 (frozen in P1):** consumption is a compare-and-swap on `status` from exactly `issued` to
  `consumed`, in the **same durable transaction** as the operation-manifest write, under an exclusive
  single-writer lock (SQLite `BEGIN IMMEDIATE`, or `O_EXCL` create-then-atomic-rename). A CAS
  observing any other status MUST route to exact-replay/idempotency-conflict and MUST NOT execute.
  P1's `consume_confirmation` is a **pure function** — real atomicity is P2's job, and a
  read-then-write implementation **passes every P1 test and is still wrong**.
- **P5:** `check_tool_name()` has zero callers by design. Calling it at the transport boundary is a
  frozen P5 obligation.

### 5.6 Open scope deviation

`src/research_foundry/services/governance.py` was modified in round 2 (config `secret_patterns` now
**union** with built-ins rather than replacing them). It is a declared serialization-barrier file
outside P1's phase ownership. The change is strictly strengthening — config can only add detection
surface. Reviewer recommends **accept with conditions**; queued for Karen.

---

## 6. Turning this into an artifact — proposed `plan-optimizer`

Sections 4.1–4.4 are not specific to this plan. They are a repeatable pass that should run **at the
plan/execute boundary, before the first implementer is dispatched**. Right now that reasoning happens
ad hoc inside an orchestrator's head, mid-run, after the money is already spent.

**Proposal.** A `plan-optimizer` skill (with a thin agent wrapper for autonomous use) that consumes an
implementation plan + its `wave_plan` and emits an optimized execution structure *before* execution.

**Inputs:** plan frontmatter (`tier`, `wave_plan.phases[]`, `files_affected`,
`serialization_barriers`, per-phase gates), plus the repo's defect-class checklist.

**Outputs:**
1. **Gate plan per phase** — chosen by risk class rather than uniformly. Security-relevant phases
   (auth, identity, tokens, isolation, preview-safety) get the security lens; mechanical phases get a
   validator; nobody gets both unless the phase is both.
2. **Duplicate-lens report** — where two reviewers would cover the same ground, and which to drop.
3. **Shared-gate merges** — phases serialized for file-ownership reasons that can still share one review.
4. **Front-loaded defect checklist** injected into implementer prompts (§4.2).
5. **Pre-gate insertion** — cheap sweep before expensive lens (§4.3).
6. **Cost projection + inversion warning** — flag phases whose projected *review* cost exceeds their
   *implementation* cost, which is the signal that the gate structure is wrong for that phase.

**Why a skill, not just a doc:** the decision has to be made at dispatch time, by whoever is
orchestrating, with the plan in hand. A doc gets read once and decays; a skill runs every time.
Per the reuse rule, check SkillMeat for an existing plan-analysis artifact and extend it rather than
building new — this may be a `dev-execution` sub-skill (it governs dispatch) rather than a standalone.

**Feed it real data.** Every execution retro like this one is a labelled example: predicted gates vs.
gates that actually found defects. Route via `op story capture` so the Signal→System pipeline picks
it up rather than letting it die in this file.

**Upstream target:** `agentic_meta_dev` — confirm the exact path in `ARTIFACT-UPSTREAM-REGISTRY.md`
and edit upstream, never a deployed copy.

**ITT node:** "AOS: build a plan-optimizer agent/skill (gate-economics tuning)" in `aos-research-foundry`.

---

## 7. Resume prompt

```
Resume research-foundry-operator-mcp-v1 in the EXISTING worktree
.claude/worktrees/operator-mcp-v1 (branch worktree-operator-mcp-v1, draft PR #7).
Do NOT create a new worktree. Do NOT re-run P1 from scratch.

READ FIRST:
- docs/project_plans/human-briefs/operator-mcp-p1-execution-retro.md  (this doc — §4 and §5)
- .claude/findings/research-foundry-operator-mcp-findings.md §FIND-P1-R3  (the 6 blocking findings)

WORK ORDER:
1. Close the 6 blocking OPM-1.G findings, in the order given in FIND-P1-R3.
   Re-derive the non-blocking NEW-15/16/17/24/25 — their detail was not captured.
2. Re-run the consolidated security+validation gate on the resulting tree.
3. Run Karen with the 3 queued adjudications (§ the findings ledger's Karen queue).
4. Only then start P2, applying the §4 gate structure — NOT the plan's original gate table.

Apply §4.2's defect-class checklist to every implementer prompt.
Heed §5.1 (pytest pythonpath trap) before any scratch-tree testing.
Do not use Codex for security review here (§5.3).
```

---

## 8. Honest assessment

The gates worked. A critical authorization bypass would have shipped into main and been inherited by
five downstream phases; it was caught, and then its incomplete fix was caught. That is the system
functioning as designed.

The structure was wasteful. Running two overlapping reviewer lenses every round, when only one ever
found defects, is the main correctable inefficiency — and it is correctable without reducing rigor.

The uncomfortable finding is §2 lesson 1: **we twice had a green suite over a real vulnerability, and
once had tests actively asserting the vulnerability was correct.** Any future decision to trust test
results in place of an adversarial pass on this codebase should be made with that on the table.
