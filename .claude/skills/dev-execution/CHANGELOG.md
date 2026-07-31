# Changelog — dev-execution

## v1.2 — 2026-07-30

- **Wire in the Claude-5-generation execution doctrine** (`references/execution-doctrine.md`, new —
  authoring-side counterpart is `planning/references/plan-doctrine.md`; long form + evidence:
  `docs/project_plans/design-specs/claude5-plan-doctrine-v1.md`). One pointer near the top of
  SKILL.md; every gate/section cites it rather than restating it.
- **Gate budget: 2 re-passes per scope x lens, then auto re-scope.** Replaced the "2+ failed fix
  cycles → escalate to Opus" language (Mandatory Reviewer Gates + Tier 1 Sprint Flow) with the hard
  rule: the 3rd failure against the same lens auto-escalates to re-scope/redesign, not to a human
  looking at it. Re-passes count per scope x lens, not per dispatch.
- **Delta-context gate dispatch.** Mandatory Reviewer Gates now states explicitly that a gate
  dispatch — including re-passes — carries only the failure summary, touched files, and the AC in
  question, never the full plan/cumulative diff/progress file; a reviewer needing the whole plan is a
  signal the AC is under-specified.
- **Continue, don't re-dispatch; fresh context is for verification.** Fix loops now continue the
  existing executor session instead of re-spawning; fresh context is reserved for the reviewer/
  verifier. Documented explicitly that today's actual default is inverted (implementers re-spawned,
  validators inherit stale context) and that this doctrine flips it.
- **150% context tripwire** added to Token Discipline: above 150% utilization in one session, split
  or summarize-forward before continuing. Documented honestly as an executor-observed live signal,
  not an automated gate — the CCDash `context_ballooning` signal remains a follow-up.
- **Implementation notes over halt-and-gate** (new Core Principles §4): executors log deviations to
  `.claude/worknotes/<slug>/implementation-notes.md` and keep going; reviewed at milestone
  boundaries. Mid-milestone halts reserved for destructive actions, real scope changes, or
  operator-only input. Mode-D boundaries are explicitly called out as unchanged and non-negotiable.
- **Bookkeeping demotions**: IntentTree lookup/claim/status-sync now fires once per plan milestone
  (was every task start; task-done/phase-done syncs unchanged); the living-dossier
  `hooks/update-dossier.sh` now fires once at end-of-plan (was every phase boundary); the plan-level
  Completion Report (`.claude/worknotes/<slug>/completion-report.md`) is **retired** — the reviewer
  verdict + `commit_refs` is the record. The Tier 1 sprint's contract-appended Completion Report is a
  **different, surviving artifact** — Tier 1 has no wave/phase record to fall back on; the Exit
  Criteria section now states the distinction explicitly so the two are never conflated.
- **Deleted `orchestrator_model`** — the plan/phase frontmatter field and its handoff-string emit
  site in Execution Model Routing. It was advisory and never read; the workflow cannot switch its own
  main-loop model mid-run.
- Added two rows to Deferred / Do Not Say: the context tripwire is executor-observed, not automated;
  there is no gate-budget counter hook enforcing the 2-re-pass cap.

## v1.1 — 2026-07-29

- **Add the `plan-optimization` mode** (risk-classed reviewer-gate selection at the plan/execute
  boundary): new `modes/plan-optimization.md` (the pre-dispatch procedure) + `references/gate-risk-classes.md`
  (risk-class → reviewer-lens ruleset, verbatim defect checklist, cost calibration, and the RF
  Operator MCP P1 worked example). Wired into the Execution Modes dispatch table and the Mandatory
  Reviewer Gates section. Emits advisory `gate_lens`/`gate_shared_with` keys per phase, a duplicate-lens
  report, a paste-ready defect checklist, a cheap pre-gate before each security lens, and a
  cost/inversion projection. Never removes the only lens a phase's risk class requires.
  Spec: `docs/skill-development/plan-optimizer/spec.md`. Grounding: RF Operator MCP P1 execution retro.
- **First validator-conformant version.** Added `version`/`app_version`/`updated` frontmatter, this
  CHANGELOG, and the required `When NOT To Use` + `Deferred / Do Not Say` + absolute `Key References`
  sections. Clears all 6 `skill-dev` `validate_skill.py` FAILs (mirror-parity + ≤500-line WARNs remain;
  mirror parity is skillmeat-generated on codex deploy).
