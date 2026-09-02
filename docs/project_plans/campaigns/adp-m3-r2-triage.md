# ADP-M3 / R2 — Artifact provenance triage (research-foundry)

> Campaign: artifact-deployment-program (spine in `agentic_meta_dev`)
> Child plan: `campaigns/artifact-deployment-program/children/research-foundry-v1.md`, phase R2
> IntentTree key: `node_01M19WH9FZ8A4TYVP0PSXD6V5R` (R2's repo-wide reconcile exit criterion)
> Status: **analysis only — no manifest writes, no captures, no reconcile --apply**

## Scope and method

R1 established that the repo-wide `skillmeat project reconcile <repo-root>` predicate
(`.gaps == [] and .drift == []`) is not R1's criterion — it is R2's, and it requires every
project-local artifact in `.claude/aos-artifacts.yaml` (205 entries) to carry real provenance
before reconcile can resolve it (currently: `gaps: 25`, `drift: 83`, `derived_unverified: 123`,
`gate_verdicts: refuse_queue×200`). This document classifies all 205 entries so that migration
work (a separate, HR-2-gated pass) has a triage table to execute against rather than a blank
slate.

**Test applied per artifact:**

- **`deployed-from-global`** — the artifact's content originates outside this repo. Checked via,
  in order: (1) exists at `~/.claude/agents/<name>.md`, `~/.claude/skills/<name>/`, or
  `~/.claude/commands/**/<name>.md` on this machine; (2) `SKILLMEAT_EDITION=enterprise skillmeat
  list --type <agent|skill|command> --format json` (the enterprise-federated catalog — 147
  agents / 286 skills / 127 commands, `local`+`github` origin) contains the name; (3) a manual
  cross-repo check for two provenance sources the automated tests above cannot see (both found
  live during this triage — see the Manual overrides note below).
- **`RF-authored`** — absent from all of the above. Verified additionally by reading file content
  for domain-specific signal (e.g. the `rf_*` agent personas and the `rf-*`/`research-foundry-*`
  Dynamic Workflow scripts describe Research Foundry's own discovery-swarm and run-execution
  pipeline in their own doc-comments — this is not generic tooling with a different name).

**Manual overrides (13 entries) — sources the automated test misses entirely:**

1. **ARC council reviewer-role roster** (10 agents: `architecture-reviewer`,
   `correctness-reviewer`, `council-coordinator`, `devex-platform-reviewer`,
   `domain-research-reviewer`, `evaluator-reviewer`, `gtm-executive-narrative-reviewer`,
   `mcp-tool-governance-reviewer`, `operator-sre-reviewer`, `platform-architecture-reviewer`) —
   each has a byte-identical file at
   `agentic-research/reviewer_roles/<name>.yaml`. These are the Agent Review Council's
   reviewer-persona roster, sourced from a sibling repo's council system, not from SkillMeat's
   agent catalog or this machine's `~/.claude/agents`. A test that only checks those two sources
   misclassifies all 10 as RF-authored.
2. **Cross-repo "dev-team" agent pack** (2 agents: `platform-engineer`,
   `vector-database-engineer`) — byte-identical files under `.claude/agents/dev-team/` in
   10+ sibling repos (`agentic-research`, `skillmeat`, `meatywiki`, `intenttree`,
   `artifact_atlas`, `chcw-live-readiness`, …). A widely-deployed pack, not RF-specific.
3. **Cross-project MeatyWiki skill** (1 skill: `meatywiki-author`) — identical directory at
   `meatywiki/.claude/skills/meatywiki-author` and `agentic-research/.claude/skills/meatywiki-author`.

**Workflow-type caveat:** `skillmeat list --type workflow` returns nothing federated
("No workflow definitions found") — Dynamic Workflow provenance is not tracked in SkillMeat's
catalog at all on this system. The 3 deployed-from-global workflows (`auto-feature`,
`execute-contract`, `execute-plan`) are instead verified against the *local* global roster
(`~/.claude/workflows/*.js`) and corroborated by this repo's own sync-commit history
(`8c9d080 chore(workflows): sync project-local Dynamic Workflow copies from upstream`). The 9
RF-authored workflows have no such external counterpart anywhere searched.

## Classification table

| name | type | verdict | evidence | proposed action |
|---|---|---|---|---|
| `a11y-sheriff` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `agent-expert` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `ai-artifacts-engineer` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `ai-engineer` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `api-designer` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `api-documenter` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `api-librarian` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `architecture-reviewer` | agent | deployed-from-global | matches agentic-research/reviewer_roles/architecture-reviewer.yaml — ARC council reviewer-role roster (cross-repo), not a SkillMeat-catalog agent | real ledger row |
| `artifact-curator` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `backend-architect` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `backend-typescript-architect` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `changelog-generator` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `code-reviewer` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `codebase-explorer` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `command-creator` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `content-curator` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `correctness-reviewer` | agent | deployed-from-global | matches agentic-research/reviewer_roles/correctness-reviewer.yaml — ARC reviewer-role roster | real ledger row |
| `council-coordinator` | agent | deployed-from-global | matches agentic-research/reviewer_roles/council-coordinator.yaml — ARC reviewer-role roster | real ledger row |
| `data-layer-expert` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `devex-platform-reviewer` | agent | deployed-from-global | matches agentic-research/reviewer_roles/devex-platform-reviewer.yaml — ARC reviewer-role roster | real ledger row |
| `devops-architect` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `documentation-complex` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `documentation-expert` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `documentation-planner` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `documentation-writer` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `domain-research-reviewer` | agent | deployed-from-global | matches agentic-research/reviewer_roles/domain-research-reviewer.yaml — ARC reviewer-role roster | real ledger row |
| `evaluator-reviewer` | agent | deployed-from-global | matches agentic-research/reviewer_roles/evaluator-reviewer.yaml — ARC reviewer-role roster | real ledger row |
| `feature-planner` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `feature-sprint-executor` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `frontend-architect` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `frontend-developer` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `gemini-orchestrator` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `gtm-executive-narrative-reviewer` | agent | deployed-from-global | matches agentic-research/reviewer_roles/gtm-executive-narrative-reviewer.yaml — ARC reviewer-role roster | real ledger row |
| `implementation-planner` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `karen` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `lead-architect` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `lead-pm` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `mcp-tool-governance-reviewer` | agent | deployed-from-global | matches agentic-research/reviewer_roles/mcp-tool-governance-reviewer.yaml — ARC reviewer-role roster | real ledger row |
| `mobile-app-builder` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `nextjs-architecture-expert` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `openapi-expert` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `operator-sre-reviewer` | agent | deployed-from-global | matches agentic-research/reviewer_roles/operator-sre-reviewer.yaml — ARC reviewer-role roster | real ledger row |
| `phase-owner` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `platform-architecture-reviewer` | agent | deployed-from-global | matches agentic-research/reviewer_roles/platform-architecture-reviewer.yaml — ARC reviewer-role roster | real ledger row |
| `platform-engineer` | agent | deployed-from-global | identical file at agentic-research/skillmeat/meatywiki/.claude/agents/dev-team/platform-engineer.md — cross-repo dev-team agent pack | real ledger row |
| `prd-writer` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `project-analyzer` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `prompt-engineer` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `python-backend-engineer` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `python-pro` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `react-performance-optimizer` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `refactoring-expert` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `research-technical-spike` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `rf_claim_auditor` | agent | RF-authored | absent from global roster + enterprise | project_original marker |
| `rf_deep_reader` | agent | RF-authored | absent from global roster + enterprise | project_original marker |
| `rf_discovery_lead` | agent | RF-authored | absent from global roster + enterprise | project_original marker |
| `rf_domain_researcher` | agent | RF-authored | absent from global roster + enterprise | project_original marker |
| `rf_governance_officer` | agent | RF-authored | absent from global roster + enterprise | project_original marker |
| `rf_intake_curator` | agent | RF-authored | absent from global roster + enterprise | project_original marker |
| `rf_knowledge_lookup` | agent | RF-authored | absent from global roster + enterprise | project_original marker |
| `rf_source_carder` | agent | RF-authored | absent from global roster + enterprise | project_original marker |
| `rf_source_scout` | agent | RF-authored | absent from global roster + enterprise | project_original marker |
| `rf_synthesizer` | agent | RF-authored | absent from global roster + enterprise | project_original marker |
| `search-specialist` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `senior-code-reviewer` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `spike-writer` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `symbols-engineer` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `system-architect` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `task-completion-validator` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `task-decomposition-expert` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `technical-writer` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `telemetry-auditor` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `ui-designer` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `ui-engineer` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `ui-engineer-enhanced` | agent | deployed-from-global | in ~/.claude/agents | real ledger row |
| `ultrathink-debugger` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `url-context-validator` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `url-link-extractor` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `ux-researcher` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `vector-database-engineer` | agent | deployed-from-global | identical file at chcw-live-readiness/artifact_atlas/intenttree/.claude/agents/dev-team/vector-database-engineer.md — cross-repo dev-team agent pack | real ledger row |
| `web-accessibility-checker` | agent | deployed-from-global | in enterprise catalog | real ledger row |
| `add-animation` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `analyze-codebase` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `architecture-review` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `architecture-scenario-explorer` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `autopilot` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `bugfix-commit` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `check-architecture` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `check-file` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `code-review` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `complete-user-story` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `create-adr` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `create-feature` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `debug` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `design` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `execute-contract` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `execute-phase` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `execute-plan` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `explore` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `fix-arch-violation` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `fix-gh-issue` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `freeze-api-version` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `generate-api-docs` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `github-create-issue` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `implement-story` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `linear-create-task` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `load-story` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `load-symbols` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `lyra` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `mc` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `memory-spring-cleaning` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `new-feature` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `plan-feature` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `plan-from-gh` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `plan-story` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `post-implementation-updates` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `pr` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `pre-pr-validation` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `quick-feature` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `refactor-code` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `refractor` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `refresh-ai-artifacts` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `review-story` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `scan-violations` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `session-learning-capture` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `spike` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `symbols-chunk` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `symbols-query` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `symbols-search` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `symbols-update` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `task_gen` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `test-stories` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `trello-add-card` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `ultra_think` | command | deployed-from-global | in ~/.claude/commands | real ledger row |
| `update-ai-hints` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `update-codeowners` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `update-readmes` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `update-repo-map` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `update-symbols-graph` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `user_stories` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `validate-chunking` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `validate-contracts` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `write-tests` | command | deployed-from-global | in enterprise catalog | real ledger row |
| `Design Principles` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `aesthetic` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `artifact-tracking` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `better-auth` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `bob-shell-delegate` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `changelog-generator` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `chrome-devtools` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `claude-code` | skill | deployed-from-global | in ~/.claude/skills | real ledger row |
| `clerk-install-auth` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `codex` | skill | deployed-from-global | in ~/.claude/skills | real ledger row |
| `cognitive-design` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `confidence-check` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `council-review` | skill | deployed-from-global | in ~/.claude/skills | real ledger row |
| `council-run` | skill | deployed-from-global | in ~/.claude/skills | real ledger row |
| `crafting-effective-readmes` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `debugging` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `design-system-patterns` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `dev-execution` | skill | deployed-from-global | in ~/.claude/skills | real ledger row |
| `devops` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `frontend-design` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `gemini-cli` | skill | deployed-from-global | in ~/.claude/skills | real ledger row |
| `generating-docker-compose-files` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `intenttree-cli` | skill | deployed-from-global | in ~/.claude/skills | real ledger row |
| `interface-design` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `managing-readmes` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `meatywiki` | skill | deployed-from-global | in ~/.claude/skills | real ledger row |
| `meatywiki-author` | skill | deployed-from-global | identical dir at meatywiki/.claude/skills/meatywiki-author and agentic-research/.claude/skills/meatywiki-author — cross-project MeatyWiki-suite skill | real ledger row |
| `meatywiki-suite` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `nano-banana` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `nano-banana-pro` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `notebooklm` | skill | deployed-from-global | in ~/.claude/skills | real ledger row |
| `notebooklm-skill` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `notebooklm-sync` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `plan-review` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `plan-status` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `planning` | skill | deployed-from-global | in ~/.claude/skills | real ledger row |
| `postgresql-psql` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `prior-day-summary` | skill | deployed-from-global | in ~/.claude/skills | real ledger row |
| `project-context-distiller` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `project-scaffolder` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `receiving-code-review` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `recovering-sessions` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `research-foundry` | skill | deployed-from-global | in ~/.claude/skills | real ledger row |
| `research-foundry-swarm` | skill | deployed-from-global | in ~/.claude/skills | real ledger row |
| `rf-knowledge` | skill | deployed-from-global | in ~/.claude/skills | real ledger row |
| `skill-builder` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `skill-creator` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `sora` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `symbols` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `workflow-authoring` | skill | deployed-from-global | in enterprise catalog | real ledger row |
| `auto-feature` | workflow | deployed-from-global | in ~/.claude/workflows | accepted-gap entry (no ledger mechanism for this type) |
| `execute-contract` | workflow | deployed-from-global | in ~/.claude/workflows | accepted-gap entry (no ledger mechanism for this type) |
| `execute-plan` | workflow | deployed-from-global | in ~/.claude/workflows | accepted-gap entry (no ledger mechanism for this type) |
| `notebooklm-extended` | workflow | RF-authored | absent from global roster (workflow catalog not enterprise-federated; RF-domain content confirmed by header) | accepted-gap entry (not capture-capable) |
| `notebooklm-report` | workflow | RF-authored | absent from global roster (workflow catalog not enterprise-federated; RF-domain content confirmed by header) | accepted-gap entry (not capture-capable) |
| `notebooklm-sourcing` | workflow | RF-authored | absent from global roster (workflow catalog not enterprise-federated; RF-domain content confirmed by header) | accepted-gap entry (not capture-capable) |
| `research-foundry-council` | workflow | RF-authored | absent from global roster (workflow catalog not enterprise-federated; RF-domain content confirmed by header) | accepted-gap entry (not capture-capable) |
| `research-foundry-swarm` | workflow | RF-authored | absent from global roster (workflow catalog not enterprise-federated; RF-domain content confirmed by header) | accepted-gap entry (not capture-capable) |
| `rf-pediatric-cds-run-execute` | workflow | RF-authored | absent from global roster (workflow catalog not enterprise-federated; RF-domain content confirmed by header) | accepted-gap entry (not capture-capable) |
| `rf-pediatric-cds-run-execute.test` | workflow | RF-authored | absent from global roster (workflow catalog not enterprise-federated; RF-domain content confirmed by header) | accepted-gap entry (not capture-capable) |
| `rf-run-execute` | workflow | RF-authored | absent from global roster (workflow catalog not enterprise-federated; RF-domain content confirmed by header) | accepted-gap entry (not capture-capable) |
| `rf-run-execute.test` | workflow | RF-authored | absent from global roster (workflow catalog not enterprise-federated; RF-domain content confirmed by header) | accepted-gap entry (not capture-capable) |

## Summary counts

| Dimension | Count |
|---|---|
| **Total artifacts in manifest** | 205 |
| **RF-authored** | 19 |
| — agent (`rf_*` swarm-role personas: claim_auditor, deep_reader, discovery_lead, domain_researcher, governance_officer, intake_curator, knowledge_lookup, source_carder, source_scout, synthesizer) | 10 |
| — workflow (`notebooklm-extended/report/sourcing`, `research-foundry-council`, `research-foundry-swarm`, `rf-pediatric-cds-run-execute[.test]`, `rf-run-execute[.test]`) | 9 |
| — skill | 0 |
| — command | 0 |
| **deployed-from-global** | 186 |
| — agent | 71 |
| — command | 62 |
| — skill | 50 |
| — workflow | 3 |

## Types that cannot be captured today

`CAPTURE_CAPABLE_TYPES = {skill, agent, command}` (`skillmeat/core/reconcile/classifier.py`).
Every RF-authored artifact in this manifest happens to be `agent` or `workflow` typed —
**0 RF-authored skills or commands** — so the capture-capable set covers all 10 RF-authored
agents (`project_original` marker via `skillmeat enterprise capture` /
`DeploymentTracker.record_project_original`) but **not** the 9 RF-authored workflows: Dynamic
Workflow `.js` files have no `project_original` marker mechanism and no ledger row mechanism at
all on this system. Those 9 need either a separate adoption step (extend
`CAPTURE_CAPABLE_TYPES` and the ledger schema to cover `workflow`) or an explicit accepted-gap
entry carried forward into R2's exit assertion. The 3 deployed-from-global workflows have the
weakest paper trail of the "resolved" rows in this table: a sync-commit in git history, not a
ledger row, is their only provenance record — real, but a different shape than every other
"real ledger row" action in this table, and worth flagging distinctly if R2's assertion script
starts treating the ledger-row and the sync-commit as interchangeable evidence.

Everything else — 71 agents, 62 commands, 50 skills, all `deployed-from-global` — is
capture-capable in principle (a `skillmeat deploy` of any one of them writes exactly the
`[[deployed]]` ledger row the classifier needs, as demonstrated for `research-foundry` itself
in this same R1 completion). But 12 of those 133 (the ARC reviewer-role roster + dev-team pack
+ `meatywiki-author`) did not come from a *SkillMeat* deploy at all — their real source is
another repo's file tree, not SkillMeat's catalog. Writing a `skillmeat deploy`-style ledger
row for those 12 would be recording the wrong upstream (it would claim SkillMeat-catalog
provenance for content SkillMeat has never served). R2's migration pass needs to decide,
artifact-by-artifact for those 12, between (a) uploading them into the SkillMeat catalog first
so a real deploy becomes possible, or (b) inventing a second ledger-row shape for
"cross-repo-file provenance, not SkillMeat provenance" — extending the classifier's
`Provenance` enum beyond `{UNKNOWN, PROJECT_ORIGINAL, DEPLOYED}` is itself new scope, not
covered by this triage.

## Recommendation

Route the 10 RF-authored agents through `skillmeat enterprise capture` to mint
`project_original` markers — mechanical, capture-capable, no open design question. File an
accepted-gap entry (or a scoped follow-up plan) for the 9 RF-authored workflows and the
workflow-ledger-mechanism gap generally, since extending `CAPTURE_CAPABLE_TYPES`/the ledger
schema to `workflow` is itself a small design decision, not a triage output. For the 186
deployed-from-global rows, real `skillmeat deploy` ledger rows are the right action for the
~174 that are genuinely SkillMeat-catalog artifacts (verified directly against the enterprise
catalog or local `~/.claude`); the 12 ARC/dev-team/MeatyWiki cross-repo artifacts need the
provenance-source decision above resolved first — deploying them through SkillMeat today would
plant a false SkillMeat-origin claim rather than close the real gap. None of the 205 rows
supports `remove from manifest`: every artifact here is real, currently in active use by this
repo's own `CLAUDE.md` agent-delegation tables and command bindings, and removing any of them
would just re-open the "missing artifact" failure mode `~/.claude-1x/CLAUDE.md`'s
artifact-provisioning rule exists to prevent — the manifest's problem is mislabeled `source`,
never presence.
