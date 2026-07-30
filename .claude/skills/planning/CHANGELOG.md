# Changelog — planning

## v2.0 — 2026-07-30

- **Wire in the Claude-5-generation plan doctrine** (`references/plan-doctrine.md` +
  `templates/milestone-plan-template.md`): Tier 2/3 Implementation Plans default to **milestone-based
  thin plans** — 3-4 reviewable-state milestones with AC, replacing the 8-standard-phase task-table
  breakdown. `implementation-plan-template.md` is retained as the legacy/expanded template for
  in-flight plans and the economy-class-executor decisions-block expansion path (Workflow 2 step 2.5)
  only — not the default for a new plan.
- **No plan-time model or agent pins.** Workflow 2 steps 4 ("Assign Subagents") and 5 ("Model
  Assignment") are replaced by a single `routing_constraints` authoring step: plans declare MUST-stay-
  claude-primary classes, offload-eligibility, and the capability bar per milestone; `delegation-router`
  resolves provider + model at dispatch time. `assigned_to` and `phases[].model`/`effort` are
  **deprecated, not deleted** — in-flight plans authored under the old rules keep them.
  `wave_plan.orchestrator_model` is **deleted outright** (advisory field, never read by the execution
  loop) — including from the `Execute: /dev:execute-plan <plan>` handoff string, which no longer names
  an orchestrator model.
- **Add `context_class` (C1-C4) sizing**, step 3.6 of Workflow 2 — points size behavior, context class
  sizes agent context and is the actual burn predictor (`plan-doctrine.md` § "Context class").
  Generalizes the per-task **H7 heuristic** (huge-file touch multiplier), added to
  `references/estimation-heuristics.md` and the mandatory Estimation Sanity Check (now H1-H7).
- **Delete the mandatory Phase Summary table.** It duplicated the milestones + AC-matrix that now
  own the same information; the instruction that made it mandatory is removed outright, not
  deprecated — new plans do not emit it. In-flight plans that already carry one finish under the
  rules they were authored on.
- **Plan mass is now a budget.** New Tier 2/3 plans target **<=150 lines total**, frontmatter
  included ("Prompt and Artifact Sizing", Tier Matrix, Key Benefits, Best Practices — all reconciled
  against the pre-existing **~800-line hard ceiling**, which still applies to every planning doc but
  is no longer the plan-specific target).
- **First validator-conformant version.** Added `version`/`app_version`/`updated` frontmatter, this
  CHANGELOG, and the required `When NOT To Use` section. Clears the `skill-dev` `validate_skill.py`
  frontmatter/heading FAILs (the `.agents/` mirror `.Codex/`-ref FAIL and `MirrorParity` WARN are
  pre-existing, out of scope for this change — `.agents/` is the deprecated stale mirror).
- Rewrote the `description` frontmatter and worked example to describe milestone-based thin plans
  instead of "8 standard phases + subagent assignments"; Tier Matrix Tier 2/3 rows now show
  constraint-style routing language instead of a model-pin cell.
