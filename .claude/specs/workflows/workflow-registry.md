---
schema_version: 2
doc_type: reference
title: "Workflow Registry — SkillMeat Authoritative Index"
status: active
created: 2026-06-01
updated: 2026-06-13  # RF workflows registered: research-foundry-swarm (Path B discovery), research-foundry-council (offline council gate), notebooklm-extended (async NLM artifact runs), notebooklm-sourcing (NLM grounded sourcing -> RF source cards), notebooklm-report (NLM grounded artifacts between synthesize and verify)
owner: nick
related_documents:
  - .claude/specs/workflows/workflow-authoring-spec.md
  - .claude/plans/workflow-orchestration-integration-v1.md
---

# Workflow Registry

This file is the authoritative index of every SkillMeat workflow — current and planned. Every entry must conform to the master contract in `.claude/specs/workflows/workflow-authoring-spec.md`. No workflow script is saved to `.claude/workflows/` or per-workflow spec authored to `.claude/specs/workflows/` without a corresponding entry here.

New workflows are added to this registry when authored via the (future) `workflow-authoring` skill (Phase 5). Until that skill exists, registry entries are authored directly by the `ai-artifacts-engineer` following §13 of the master contract.

**Maintenance ownership**: nick. Update the `updated` frontmatter date on every change.

---

## Registered Workflows

| Workflow | Spec | Script | Status | Owner | Introduced | Notes |
|---|---|---|---|---|---|---|
| `execute-plan` | `.claude/specs/workflows/execute-plan-workflow-spec.md` | `.claude/workflows/execute-plan.js` | `active` | nick | P1 | Prime target. Drives Tier 2/3 wave execution: sequential waves, parallel phases, file-ownership batching, reviewer gates, tracker steps. Replaces the manual Opus wave loop in `/dev:execute-plan`. Pilot runs against one real Tier 2 plan before retiring the manual fallback. |
| `execute-contract` | `.claude/specs/workflows/execute-contract-workflow-spec.md` | `.claude/workflows/execute-contract.js` | `active` | nick | P2 | Tier 1 autonomous sprint. Implements the sprint → validate → fix-loop pattern for a single Feature Contract. Resumable fix-loop with budget guard; `task-completion-validator` / `karen` / `council-review` reviewer gate (routing by review_intensity). Mode D boundary check before sprint spawns. Measured against the ~326K trial baseline from the current single-`feature-sprint-executor` path. |
| `explore` | `.claude/specs/workflows/explore-spike-workflow-spec.md` | `.claude/workflows/explore.js` | `active` | nick | P3 | Pre-commitment exploration. Parallel investigation legs (read-only `codebase-explorer` / `search-specialist`) → `pipeline` deep-read → `adversarialVerify` (2–3 skeptics) → `implementation-planner` synthesis → `completenessCritic` (budget-guarded). Returns `ExplorationCharter` result. Verdict sign-off stays with Opus + human; workflow always returns `needs_opus / verdict_signoff`. |
| `spike` | `.claude/specs/workflows/explore-spike-workflow-spec.md` | `.claude/workflows/spike.js` | `active` | nick | P3 | Research SPIKE. Same phase structure as `explore`. Produces schema-valid `FeasibilityBrief` with `verdict`, `verdict_confidence`, `risk_summary`, `cost_estimate_range`. Supports standalone SPIKE and exploration-leg mode (`args.leg_of`). Verdict sign-off stays with Opus + human; workflow always returns `needs_opus / verdict_signoff`. |
| `review-council` | `.claude/specs/workflows/review-council-workflow-spec.md` | `.claude/workflows/review-council.js` | `active` | nick | P4 | Agent Review Council (ARC) wrapper. Embeds the `council-review` skill as a deterministic workflow step. Operates standalone (direct invocation) and as an embedded `review_intensity: council` gate inside `execute-plan`. Produces the full ARC artifact set: `findings.yaml`, `scorecard.json`, `risk_register.yaml`, `decision_record.md`, `validation_plan.md`. Seeded-bug gate test required before Phase 4 exit. |
| `auto-feature` | `.claude/specs/workflows/auto-feature-workflow-spec.md` | `.claude/workflows/auto-feature.js` | `active` | nick | P7 | Autopilot lane (`/dev:autopilot`). Takes a RAW request (no PRD/contract): `implementation-planner` classifies + decomposes + writes a durable plan artifact (Stage A, no schema) -> haiku structurer extracts an `AutopilotPlan` (Stage B, schema) -> deterministic single-pass feasibility gate -> nests `execute-contract` (single wave) or `execute-plan` (<=3 waves). Escalates to full planning via `needs_opus` reasons `mode_d` / `spike_required` / `scope_exceeds_single_pass`, always leaving the plan artifact on disk. Implements the recalibrated single-pass capacity from `tiered-workflow-overhaul.md` 12. One level of `workflow()` nesting only. |
| `research-foundry-swarm` | `.claude/specs/workflows/research-foundry-swarm-workflow-spec.md` | `.claude/workflows/research-foundry-swarm.js` | `active` | Nick Miethe | RF | Research Foundry Path B discovery swarm. Orchestrates a Claude Code multi-agent swarm (`rf_discovery_lead`, `rf_deep_reader`, `rf_domain_researcher`) to locate and vet sources for a given RF run, then feeds accepted sources into `rf ingest` as schema-valid source cards. Operates after `rf guard check` preflight; produces `runs/<run_id>/sources/src_*.md` cards ready for the deterministic tail (`rf extract` → `rf claim-map` → `rf synthesize` → `rf verify`). RF is the governance and evidence spine; this workflow is the disposable discovery muscle. Does NOT call `rf swarm run` (adapter path) — implements Path B (Claude Code-orchestrated) from `.claude/skills/research-foundry-swarm/SKILL.md §2`. |
| `notebooklm-extended` | `.claude/specs/workflows/notebooklm-extended-workflow-spec.md` | `.claude/workflows/notebooklm-extended.js` | `active` | Nick Miethe | RF | Extended Runs: async, long-latency, rate-limited NotebookLM artifact generation (audio deep-dive 10-20 min, video 15-45 min) across N notebooks (one per swarm leg) via `pipeline()` with no inter-item barrier. Each notebook flows Generate -> Poll -> Collect independently; a slow/rate-limited notebook never blocks others. Background polling (`notebooklm artifact wait`, auto-runs in subagent context) + `nlm_task_id` checkpoint/resume: on resume a prior task_id is REUSED rather than regenerating a non-deterministic artifact (constraint-4 handling). Generation legs budget-guarded (`budget.remaining() < 60_000`); rate-limit/timeout degrades to a skipped status (never fails the run). Always passes explicit FULL-UUID `-n`; per-agent `NOTEBOOKLM_HOME` isolation. Downloads to `runs/<run_id>/nlm_artifacts/`; records non-authoritative artifacts in `runs/<run_id>/evidence_bundle.yaml` (`artifacts.notebooklm_extended[]`) — never spliced into report_draft.md, never a claim. Returns a custom shape with a `checkpoint` map (`notebook_id -> task_id`) the operator passes back as `args.resume_task_ids`. NLM auth is a PRECONDITION (`notebooklm login` out-of-band), not a Mode D gate; destructive NLM ops (delete) forbidden. Implements §3.3 of `docs/projects/research-foundry/notebooklm-integration-plan.md`. |
| `notebooklm-sourcing` | `.claude/specs/workflows/notebooklm-sourcing-workflow-spec.md` | `.claude/workflows/notebooklm-sourcing.js` | `active` | Nick Miethe | RF | Sourcing: drives NotebookLM grounded research + cited Q&A for an RF run's research questions, then ingests the results into RF as source cards. Purely additive — no Python/`src/` changes; complements the future `NotebookLMAdapter` (`rf swarm run --adapters notebooklm`). Three phases: Plan (`codebase-explorer`, Mode A, reads `runs/<run_id>/research_brief.md` -> ordered primary+secondary question list, sensitivity, max_sources), Source (`parallel()` over questions capped at `max_sources`; each `python-backend-engineer` leg runs `notebooklm source add-research`/`ask`/`source fulltext --json` and maps each NLM reference into a `gpt_researcher`-shaped candidate `{candidate_id,title,source_type:'notebook',locator{url|notebook_source_id},discovery_method:'notebook_knowledge',label,notes,quote?}`; degrades to empty on missing auth/CLI, never fails; budget guard `< 40_000`), Ingest (`pipeline()` over deduped candidates; each `python-backend-engineer` runs `rf guard check` then `rf ingest <locator> --run <run_id> --source-type notebooklm` and tags the card `usage.requires_network: true` + reliability note; budget guard `< 60_000`). Dedup between Source and Ingest is plain JS (merge by locator), no agent. Returns a custom manifest (`source_cards[]`, `failed_sources[]`, `notebook_id`, `post_run_commands[]`) — NOT a standard ExecutionReport (same precedent as `research-foundry-swarm`). NLM auth is a PRECONDITION (`notebooklm login` out-of-band), not a Mode D gate; destructive NLM ops (delete) forbidden. Implements §3.1 SOURCING of `docs/projects/research-foundry/notebooklm-integration-plan.md`. |
| `notebooklm-report` | `.claude/specs/workflows/notebooklm-report-workflow-spec.md` | `.claude/workflows/notebooklm-report.js` | `draft` | Nick Miethe | 2026-06-13 | Report: between `rf synthesize` and `rf verify`, generates NotebookLM grounded artifacts (briefing-doc, mind-map, data-table) from a synthesized RF run and attaches them as NON-AUTHORITATIVE evidence. Three phases — Prepare (`codebase-explorer`, Mode A, confirms `report_draft.md`/`claim_ledger.yaml` and resolves `notebook_id`), Generate (`parallel()` over requested formats; each `python-backend-engineer` runs `notebooklm generate ...` and captures a `task_id`; budget-guarded `< 50_000`; degrades on rate-limit, never fails), Integrate (`pipeline()` no inter-item barrier; per artifact: `notebooklm artifact wait` then `notebooklm download` into `runs/<run_id>/nlm_artifacts/`, recorded under `evidence_bundle.yaml` `artifacts.notebooklm_report[]`). Artifacts are NEVER spliced into `report_draft.md` — any prose to be cited must first become a source card and earn a `[claim:<id>]`. NLM auth + uploaded sources are a PRECONDITION (`notebooklm login` out-of-band), not a Mode D gate; destructive NLM ops (delete) forbidden. Implements §3.2 of `docs/projects/research-foundry/notebooklm-integration-plan.md`. |
| `research-foundry-council` | `.claude/specs/workflows/research-foundry-council-workflow-spec.md` | `.claude/workflows/research-foundry-council.js` | `active` | Nick Miethe | RF | Offline council gate over a completed RF run's report and claim ledger. Embeds `council-review` skill as a deterministic workflow step (exit code 7 path from `rf council`). Reads `runs/<run_id>/reports/report_draft.md` and `runs/<run_id>/claims/claim_ledger.yaml`; routes to vendored council agents in `.claude/agents/council/`; produces the full ARC artifact set under `runs/<run_id>/council/` (`findings.yaml`, `scorecard.json`, `risk_register.yaml`, `decision_record.md`, `validation_plan.md`). Fully offline and file-based — does NOT require an arc server. Designed for use at step 16 of the 21-step RF run loop or standalone via `rf council <run_id>`. |

---

## Future Candidates (registered, not built)

The following workflows are registered per §5.5 of the integration plan. Each requires a per-workflow spec and script; none are in scope until the primary five workflows are piloted and the `workflow-authoring` skill exists (Phase 5+).

| Workflow | Intended scope | Status |
|---|---|---|
| `release` | Version bump → OpenAPI regeneration → SDK release → changelog audit → tag. Replaces the manual multi-command release sequence. Scope: `release` + `changelog-sync` skill integration with worktree isolation for the version-bump commit. | `candidate` |
| `migrate-sweep` | N-file schema migration or large refactor with per-file worktree isolation. Each file processed as a `pipeline` item through extract → transform → validate stages. Scope: data-layer and cross-cutting migrations that currently require manual wave management. | `candidate` |
| `audit` | Codebase-wide bug or security sweep. Fans out `security-review` or `code-reviewer` agents across file groups via `pipeline`; synthesises findings into a ranked issue register. Scope: periodic audits triggered manually or on schedule. | `candidate` |
| `docs-sync` | Authoring-to-docs-site sync pipeline. Runs `sync-from-source.py`, validates MkDocs nav consistency, commits to `skillmeat-docs`. Codifies the manual sync step from `.claude/rules/docs-site-sync.md`. | `candidate` |
| `symbols-refresh` | Regenerates `ai/symbols-*.json` graph artifacts after structural changes. Coordinates `symbols-engineer` agents, validates output against graph schema, commits refreshed symbols. | `candidate` |

---

## Authoring a New Workflow

Invoke `Skill("workflow-authoring")` first. The skill operationalizes the full procedure:

1. Load `.claude/specs/workflows/workflow-authoring-spec.md` (master contract) and the per-workflow spec.
2. Read or author a per-workflow spec at `.claude/specs/workflows/<name>-workflow-spec.md`
   (template: `.claude/skills/workflow-authoring/per-workflow-spec-template.md`).
3. Choose patterns from `.claude/skills/dev-execution/orchestration/workflow-patterns.md`.
4. Author the script at `.claude/workflows/<name>.js`, passing the four-constraints checklist (§5 of master contract).
5. Validate syntax via `.claude/skills/workflow-authoring/syntax-check-helper.js`.
6. Add a row to the **Registered Workflows** table above with all columns populated.
7. Update this file's `updated` frontmatter date.

**Skill reference**: `.claude/skills/workflow-authoring/SKILL.md`
