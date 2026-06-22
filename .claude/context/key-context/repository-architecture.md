# Repository Architecture — Research Foundry

**Status**: Active  
**Scope**: Single Python package + Vite SPA frontend

## Package layout: `src/research_foundry/`

```
src/research_foundry/
├── cli.py              # Typer app; entry point `rf` (pyproject [project.scripts])
├── cli_commands.py     # All rf subcommands (thin wiring → services)
├── config.py           # FoundryConfig loader (YAML workspace config)
├── paths.py            # FoundryPaths — run/artifact directory conventions
├── schemas.py          # SchemaRegistry (YAML schema validation)
├── errors.py           # Exit codes + RFError hierarchy
├── api/                # Thin read-only FastAPI loopback (app.py factory)
│   ├── app.py          # create_app() → mounts /api/runs, /health, /data/governance.json
│   ├── routers/runs.py # 4 GET endpoints via export_service
│   └── middleware/     # auth.py (Bearer token, hmac), allowlist.py (IP filter)
├── services/           # Business logic — one module per pipeline stage
│   ├── capture.py      # rf capture / triage
│   ├── planning.py     # rf plan → run scaffold
│   ├── intake.py       # rf ingest sources
│   ├── extraction.py   # rf extract
│   ├── claim_mapping.py
│   ├── synthesis.py    # rf synthesize → markdown report
│   ├── verification.py # rf verify — the differentiated gate
│   ├── export_service.py  # Deterministic run.json denormalizer (viewer data)
│   ├── governance.py   # Sensitivity, writeback gating
│   ├── search_router/  # Multi-provider search (Brave/Exa/Jina/GitHub/Firecrawl)
│   │   ├── router.py, mcp_server.py, providers/, policy.py …
│   └── …              # workspace, writeback, telemetry, source_cards, etc.
├── adapters/           # Optional external tool adapters (lazy imports)
├── integrations/       # ARC council, IntentTree, NotebookLM
└── validators/         # Pre-tool guards, artifact scanners
```

## Frontend: `frontend/runs-viewer/`

Vite + React 18 SPA (no Next.js). Fetches from the read-only loopback API or static JSON.

## Tests

`pytest` under `tests/`. Run: `./.venv/bin/python -m pytest`
