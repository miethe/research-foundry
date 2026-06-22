# Project Onboarding — Research Foundry

## Install

```bash
# Editable install (recommended for development)
pip install -e ".[dev]"
# — or via uv —
uv tool install --editable .
```

The `rf` CLI is registered as a console script (`pyproject.toml [project.scripts]`).

## Key CLI commands

| Command | Purpose |
|---------|---------|
| `rf capture` | Capture a raw idea into `inbox/raw_ideas/` |
| `rf triage` | Derive intent + I-BOM + intent-tree node from a raw idea |
| `rf plan` | Generate a planned run (run.yaml, research_brief, swarm_plan, routing) |
| `rf ingest` | Ingest sources into a run |
| `rf extract` | Extract structured data from ingested sources |
| `rf claim-map` | Map extracted evidence to claims |
| `rf synthesize` | Produce markdown report from claim ledger |
| `rf verify` | Verify report claims against the ledger (the quality gate) |
| `rf serve` | Start the read-only loopback API (port 7432) for runs-viewer |
| `rf swarm` | Execute a multi-agent swarm run |
| `rf status` | Show run lifecycle status |
| `rf council` | Submit run to ARC council review |

## Runtime truth

- Python package: `src/research_foundry/`
- Config: `FoundryConfig` loaded from workspace YAML (see `config.py`)
- Paths: `FoundryPaths` resolves run/artifact directories (see `paths.py`)
- Schemas: YAML-based, validated by `SchemaRegistry` (see `schemas.py`)

## Tests

```bash
./.venv/bin/python -m pytest
```

## Frontend (runs-viewer)

```bash
cd frontend/runs-viewer
npm install && npm run dev
```

Vite dev server; connects to `rf serve` in loopback mode or uses static fixtures.
