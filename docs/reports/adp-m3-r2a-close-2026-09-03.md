# ADP-M3 R2a closeout — 2026-09-03

Scope: enterprise SkillMeat only. `delegation-router` was not deployed or otherwise changed.
This is a closeout of verified work and blockers, not an R2 exit declaration.

## Reconcile measurements

| Measurement | Gaps | Drift | Expected | Evidence / qualification |
|---|---:|---:|---:|---|
| Requested historical baseline | 146 | 17 | 180 | `adp-m3-r2a-divergent-for-nick-2026-09-01.md` |
| Last completed post-action check | 24 | 17 | 181 | `20260903T154936Z-54514-codex.report.jsonl`, item 33; `--check` exit 2 is expected for nonempty findings |
| Current re-run attempt | unreported | unreported | unreported | `skillmeat project reconcile . --check --json` reached `checking 147 catalog artifacts` but did not emit JSON/counts in the foreground window; do not infer unchanged counts |

The historical and current inventories are not directly comparable: the expected-set/catalog state changed. The 24/17/181 record is the only completed measurement after this leg's capture/deploy attempt.

## Per-row results

| Group | Artifact(s) | Verified result |
|---|---|---|
| Agent drift (10) | a11y-sheriff; backend-architect; changelog-generator; data-layer-expert; documentation-expert; documentation-writer; feature-sprint-executor; frontend-developer; search-specialist; task-completion-validator | Each has a preserved `docs/reports/adp-m3-r2a-diffs/<name>.local.md` byte-matching its then-local copy and a nonempty `<name>.diff`. All 10 dry-runs exited 0. The first eight real materializations returned HTTP 404 before writes (`partial_writes: []`, `wrote_nothing: true`); project read-back found no successful materialization for any of the 10. No source agent was overwritten. |
| Other no-ledger skills (5) | artifact-tracking; council-review; intenttree-cli; symbols; workflow-authoring | Still no-ledger divergent rows. No backup, dry-run, deploy, overwrite, or catalog capture was authorized/performed in this leg. |
| Context mapping exclusion (9) | context-budget; delegation-modes; git-workflow; lsp-diagnostics; progress-cli-only; changelog-spec; doc-policy-spec; skills-index; version-bump-spec | Untouched and excluded from the R2 exit criterion. Canonical tracking finding: `node_01M1KZR6NRS01J948D0CDT3N49` in the SkillMeat tree. |
| Ledgered planning | planning | Captured to Enterprise as version `38455bc7-51cc-4741-ba10-9d6858fd22bf`; no project deployment occurred. |
| Ledgered dev-execution | dev-execution | Three-way merge proposal only at `docs/reports/adp-m3-r2a-dev-execution-merge/`; 60 proposed files, 12 selections, zero text conflicts; no deploy/capture. |

## R2 exit and why this is taking so long

R2 cannot exit: 10 authorized agent deploys are blocked by project registration, five skill drift rows remain unactioned, nine type/path rows need a canonical mapping decision, 14 genuine catalog gaps remain outside this bounded action, and the `dev-execution` proposal still requires an owner decision.

Measured blocking categories: **1 deployment-target defect** (the worktree manifest names the primary checkout; enterprise deploy returns 404 without writing), **5 deferred no-ledger skills**, **9 catalog type/path mappings**, **14 non-deployed expected artifacts**, and **1 human merge/versioning decision**. This is why the work has not reduced the drift count: preservation and dry-runs were safe, but no authorized mutation can pass the wrong-project boundary. Do not run `skillmeat init` or `skillmeat project register` here: inspected CLI behavior would write/bind the mispointed manifest. A correctly path-scoped enterprise project record is needed first.

## Evidence pointers

- Preservation and failed materialization read-back: `.claude/reports/morning-2026-09-03/LEG-REPORT.md` and `.claude/reports/legs/20260903T154936Z-54514-codex.report.jsonl` items 27, 32–34.
- Original 15 no-ledger rows and nine mappings: `docs/reports/adp-m3-r2a-divergent-for-nick-2026-09-01.md`.
- Merge evidence: `docs/reports/adp-m3-r2a-dev-execution-merge/MERGE-NOTES.md`.

## R3 — primary-checkout deploy (2026-09-03)

Executed by a Codex leg in the **primary** `research-foundry` checkout
(`/Users/miethe/dev/homelab/development/research-foundry`, not this worktree) — the R2a worktree's
SkillMeat manifest points at the primary checkout, so no enterprise deploy can materialize from
inside the worktree itself. Leg transcript:
`research-foundry/.claude/reports/legs/20260903T163259Z-46654-codex.report.jsonl`.

### Per-row hash verification (verified independently, not copied from the leg's self-report)

All 10 rows deployed at `2026-09-03T16:36:4x/5x` in `research-foundry/.claude/.skillmeat-deployed.toml`;
each file's on-disk `sha256sum` was recomputed and compared byte-for-byte to the ledger's
`content_hash`.

| Agent | Deployed path | Hash match |
|---|---|---|
| a11y-sheriff | `.claude/agents/a11y-sheriff.md` | yes |
| backend-architect | `.claude/agents/backend-architect.md` | yes |
| changelog-generator | `.claude/agents/changelog-generator.md` | yes |
| data-layer-expert | `.claude/agents/data-layer-expert.md` | yes |
| documentation-expert | `.claude/agents/documentation-expert.md` | yes |
| documentation-writer | `.claude/agents/documentation-writer.md` | yes |
| feature-sprint-executor | `.claude/agents/feature-sprint-executor.md` | yes |
| frontend-developer | `.claude/agents/frontend-developer.md` | yes |
| search-specialist | `.claude/agents/search-specialist.md` | yes |
| task-completion-validator | `.claude/agents/task-completion-validator.md` | yes |

10/10 match. All 10 `skillmeat deploy … --overwrite` calls exited 0; no `#6` baseline-guard refusal
occurred.

### Source-store-stale warnings — measured as 7, not 6

The leg's own summary claimed six `source_store_stale` warnings (Enterprise source differs from the
local collection mirror). Re-parsing the leg's own captured deploy output found **seven**:
`backend-architect`, `changelog-generator`, `data-layer-expert`, `documentation-expert`,
`documentation-writer`, `feature-sprint-executor`, `search-specialist`. Only `a11y-sheriff` and
`task-completion-validator` deployed clean. This is a correction to the leg's self-report, not a
restatement of it — the count needed catalog-refresh decision applies to 7 rows.

### Reconcile before/after

| Measurement | Expected | Present | Gaps | Drift |
|---|---:|---:|---:|---:|
| Pre-R3 (this session's own baseline, "Last completed post-action check" above) | 181 | — | 24 | 17 |
| Post-R3 (`skillmeat project reconcile . --check --json`, exit 2) | 181 | 34 | 24 | 16 |

Drift dropped by exactly 1 (17 → 16) — consistent with 10 agent rows moving from drift to clean,
offset by the leg's inability to resolve anything else (the 7 stale-source rows still count as
drift against the local-collection comparison used elsewhere, and 14 gaps remain genuine and
untouched).

### What remains

- **5 no-ledger skill drift rows** (artifact-tracking, council-review, intenttree-cli, symbols,
  workflow-authoring) — untouched by R3, same as R2a.
- **9 context/rule-spec type-mapping rows** — untouched; canonical tracking finding
  `node_01M1KZR6NRS01J948D0CDT3N49` (skillmeat tree).
- **14 genuine catalog gaps** — untouched, outside this bounded action.
- **`dev-execution` merge** — still a proposal only (`docs/reports/adp-m3-r2a-dev-execution-merge/`);
  needs an owner decision on which of the 60 proposed files to select.
- **7 (not 6) `source_store_stale` rows** — new follow-up from this leg; needs a catalog-refresh
  decision on whether Enterprise or the local collection is authoritative for each. Filed below.

`delegation-router` was not touched by R3 — confirmed via `git status --short` in the primary
checkout, which carries no delegation-router entry.

### Sandbox limitation

The Codex leg ran entirely inside the primary `research-foundry` checkout's sandbox and could not
write into this AMD worktree (`agentic_meta_dev/.claude/worktrees/adp-r2a`) — an attempted
incremental append was explicitly rejected before any write. This section and the accompanying
`LEG-REPORT-r3.md` were written by the current (AMD-worktree) session from the leg's transcript and
independently reverified, not copied from the leg's unwritten draft.
