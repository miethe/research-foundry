---
type: worknote
schema_version: 2
doc_type: worknote
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: complete
created: '2026-07-31'
updated: '2026-07-31'
---

# M3 AAR — Operator MCP final milestone (and feature close)

M3 (4 pts, C4) executed and closed 2026-07-31 in one session: 4 parallel legs → cheap diverse
pre-gate → 1 validator round-trip → Karen APPROVED on the final exact tree (0C/0H/0M/2L, both LOWs
dispositioned same-day). Feature complete pending human merge of PR #7. Full observation log:
`m3-delivery-notes.md` (O-0..O-9); evidence: `m3-exact-tree-evidence.md`.

## What worked (keep doing)

1. **Reading the prior milestone's notes before scoping paid for itself twice before wave 1
   dispatched** (O-0): the M2 failure-set record resolved a baseline discrepancy in minutes, and
   M2's O-7 resolved a "flake" as my own concurrent-pytest pollution — killing a root-cause leg
   the original contract had already budgeted. Delivery-notes discipline has measurable compound
   value.
2. **"Test the product's own route" is 2-for-2 across milestones as the highest-yield lens**
   (O-4): four real product defects shipped through every prior gate and fell out of M3's
   registered-route matrices — including `swarm.start`'s preflight→execute route being *wholly
   broken*, found only because a pre-gate LOW demanded a positive control. Positive controls are
   not decoration.
3. **One implementer session, five continuations** (O-7): Leg A absorbed the wave-1 build, the
   existence-leak fix, the pre-gate cycle, and the validator cycle without a single re-dispatch —
   cache-warm, no context re-derivation, and the gate sequence converged in ONE re-pass (vs 5 and
   4 rounds for P1/P2). Continue-don't-redispatch plus delta-scoped re-passes is the workstream's
   proven fix-loop shape.
4. **The read-only reconciliation leg on the free lane** (O-2): 1 vacuous + 3 incomplete evidence
   rows and 15 unattacked schema properties for free-tier tokens — including the plan document
   itself carrying a 0/33-selecting `-k` filter through two closed milestones.
5. **Lens diversity kept catching what single lenses can't** (O-5): terra caught the fix-introduced
   probe-doubling that envelope-level tests structurally cannot see; ICA independently confirmed
   the isolation properties empirically; the validator's residual yield was contract-vs-artifact
   consistency. No lens overlap, no duplicate spend.

## What to change (carry-ins)

1. **Collect-only audit of every `-k` filter belongs at plan AUTHORING time** — seconds per row;
   the vacuous-row class survived two milestones because nobody counted selections until M3.
   Filed: `node_01KYWYK82E3RVF0AXJCH5A1PG6` (planning-skill lesson).
2. **Read-only legs need "never execute the suite" as an explicit prohibition** (O-3): the ICA leg
   ran a full pytest outside its collect-only scope, hit the concurrent-suite hazard, and burned
   its own measurement. Implication, not instruction, does not bind delegates.
3. **Don't launch codex + ICA simultaneously on this machine** (O-5): both parallel pre-gate
   launches were killed at ~0s under 94% swap; sequential relaunch worked first try.
4. **A worktree venv is part of the evidence surface** (Karen K-M3-1): 5 of the "23 pre-existing
   baseline failures" were a missing `pypdf` in this worktree's venv, not code. Baseline claims
   should name the venv provisioning state, or the venv should be provisioned to parity before
   the first baseline capture.
5. **The quiet-mode pytest summary suppression + capture-pipeline `exit=` mix-up** produced three
   separate "zero reads like a lie" moments this session (O-10 class from M2, still alive).
   Standard evidence form going forward: write full log to file, report pytest's own exit code,
   grep the file with `-a` + ANSI strip, and annotate any pipeline-derived exit values inline.

## Defect-class ledger (for the next plan's checklist)

- The **TypeError→internal_error masking at the dispatch seam** appeared three times (M2 fix, M3
  job.status, M3 required-keys). M3 closed it at the class level with signature-derived gates —
  the first time in this workstream a class fix was self-maintaining (`inspect.signature`).
- The **F6 existence-oracle class** recurred once (swarm_start) after being fixed in
  research_stages during P-era work; the M3 enumeration table proved it was the last instance.
- **Fix-introduced regressions invisible to the fixer's own tests** (probe-doubling) remain the
  strongest argument for the cheap external pre-gate between fix and validator.

## Numbers

- 4 legs: 2 claude-primary (Sonnet 5), 1 ICA free-lane, 1 Codex gpt-5.6 (~76k tokens for the full
  doc set). Pre-gate: terra + ICA sequential. Gates: validator ×2 (245k + 131k tokens), Karen ×1
  (213k). Leg A total across 5 continuations: ~800k agent tokens.
- Tests: operator family 519 → 716 nodes over the milestone; whole tree 4835 passed / 23 failed
  (set-identical to baseline; 18 of 23 are code-baseline, 5 are venv-gap per K-M3-1).
- 4 product defects fixed + mutation-verified; 2 defects reported-not-fixed → ITT nodes; 4
  follow-up ITT nodes filed total.
