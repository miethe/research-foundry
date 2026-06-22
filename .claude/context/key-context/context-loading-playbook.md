# Context Loading Playbook

Use this ladder to minimize tokens and stale-context risk.

## Loading Ladder

1. Query runtime truth first (`src/research_foundry/` source, `ai/symbols-*.json` when generated).
2. Read entry `CLAUDE.md` for scope invariants and routing.
3. Read the relevant key-context file for task-level playbook.
4. Pull deep context files only for unresolved details.
5. Use reports/plans for rationale only; re-verify behavior from runtime truth.

## Task Routing Matrix

| Task | Read First | Then Read |
|---|---|---|
| CLI wiring / subcommand issues | `src/research_foundry/cli.py` (`_wire()`), `cli_commands.py` | `debugging-patterns.md` |
| Search router changes | `src/research_foundry/services/search_router/router.py`, `policy.py`, `providers/` | `router-patterns.md`, related `test_search_router_*.py` |
| Loopback API (runs endpoints) | `src/research_foundry/api/app.py`, `api/routers/runs.py` | `api/middleware/auth.py`, `api/middleware/allowlist.py` |
| Backlog metadata / reconcile | `src/research_foundry/services/backlog_metadata.py` | `tests/test_backlog_reconcile.py`, `tests/test_plan_run_metadata.py` |
| Writeback / evidence bundles | `src/research_foundry/services/writeback.py` | `services/verification.py`, `services/telemetry.py` |
| Export / run viewer data contract | `src/research_foundry/services/export_service.py` | `tests/unit/test_export_service.py`, `docs/dev/architecture/rf-run-export-schema.md` |
| Frontend (runs-viewer) | `frontend/runs-viewer/src/`, `package.json` | `frontend/runs-viewer/e2e/`, vitest tests under `src/test/` |
| Debugging unknown area | symbols (`ai/symbols-*.json`), stack trace files | `debugging-patterns.md`, `symbols-query-playbook.md` |
| Planning / migration work | runtime truth artifacts | latest plan/report after verification |
| Multi-model task planning | `.claude/config/multi-model.toml`, relevant model capability spec | `.claude/skills/planning/references/multi-model-guidance.md`, escalation protocol |

## Stop Conditions

Stop loading more docs when all are true:

- Target files identified (module path + test file).
- Contract behavior confirmed from source code or schema files on disk.
- One implementation pattern is selected and testable via `uv run pytest` or `pnpm test`.
