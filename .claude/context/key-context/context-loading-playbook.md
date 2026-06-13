# Context Loading Playbook

Use this ladder to minimize tokens and stale-context risk.

## Loading Ladder

1. Query runtime truth first (`openapi.json`, hooks barrel, symbols).
2. Read entry `CLAUDE.md` for scope invariants and routing.
3. Read the relevant key-context file for task-level playbook.
4. Pull deep context files only for unresolved details.
5. Use reports/plans for rationale only; re-verify behavior from runtime truth.

## Task Routing Matrix

| Task | Read First | Then Read |
|---|---|---|
| API contract mismatch | `skillmeat/api/openapi.json`, `ai/symbols-api.json` | `api-contract-source-of-truth.md`, `router-patterns.md` |
| Hook/component changes | `skillmeat/web/hooks/index.ts`, `ai/symbols-web.json` | `hook-selection-and-deprecations.md`, `component-patterns.md` |
| Sync/diff component changes | diff-viewer, sync-status-tab, artifact-operations-modal files | `sync-diff-patterns.md` |
| FE/BE payload drift | OpenAPI + SDK/types in use | `fe-be-type-sync-playbook.md` |
| Debugging unknown area | symbols + stack trace files | `debugging-patterns.md`, `symbols-query-playbook.md` |
| Planning/migration work | runtime truth artifacts | latest plan/report after verification |
| Multi-model task planning | `.claude/config/multi-model.toml`, relevant model capability spec | `.claude/skills/planning/references/multi-model-guidance.md`, escalation protocol |

## Stop Conditions

Stop loading more docs when all are true:

- Target files identified.
- Contract behavior confirmed from machine artifacts.
- One implementation pattern is selected and testable.
