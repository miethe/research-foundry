---
title: Testing Patterns Reference
description: Testing patterns for Research Foundry (Python backend + runs-viewer frontend)
references:
  - tests/**/*.py
  - tests/unit/**/*.py
  - tests/integration/**/*.py
  - frontend/runs-viewer/src/test/**/*.test.ts(x)
  - frontend/runs-viewer/e2e/**/*.spec.ts
last_verified: 2026-06-22
category: testing
related:
  - pyproject.toml
  - frontend/runs-viewer/package.json
  - frontend/runs-viewer/vite.config.ts
---

# Testing Patterns Reference

Testing patterns for Research Foundry: Python backend (pytest) and the runs-viewer frontend (Vitest + Playwright).

## Test Types Overview

| Type | Location | Purpose | Runner |
|------|----------|---------|--------|
| Python unit | `tests/` (top-level), `tests/unit/` | Services, CLI, schemas | pytest |
| Python integration | `tests/integration/` | Multi-service pipelines, export round-trips | pytest (`-m integration`) |
| Frontend unit | `frontend/runs-viewer/src/test/` | Components, hooks, lib utils | Vitest + RTL |
| Frontend E2E | `frontend/runs-viewer/e2e/` | Full viewer workflows | Playwright |

---

## Critical: Python Interpreter Requirement

**ALWAYS use the project venv or `uv run`** — never the bare `python` / `pytest` shim:

```bash
# Preferred (uv manages the venv)
uv run pytest

# Direct venv call (equivalent)
./.venv/bin/python -m pytest

# With specific test file
uv run pytest tests/test_search_router_router.py -v

# Integration tests only
uv run pytest -m integration
```

The bare `pyenv` shim does NOT have project dependencies installed. Tests will fail with `ModuleNotFoundError` if you use it.

---

## Python Test File Structure

```
tests/
├── conftest.py                        # Shared fixtures (FoundryPaths, tmp workspaces)
├── fixtures/                          # Static YAML/Markdown fixtures
├── unit/
│   ├── test_export_service.py         # Export determinism, redaction
│   └── test_sensitivity_redaction.py  # Sensitivity gating
├── integration/
│   └── test_export_round_trip.py      # End-to-end export pipeline
├── test_serve_api.py                  # FastAPI loopback endpoints (TestClient)
├── test_serve_auth.py                 # Token auth middleware
├── test_serve_cli.py                  # `rf serve` CLI wiring
├── test_search_router_foundation.py   # Modes, budgets, dedupe, ranking
├── test_search_router_providers.py    # Provider adapters (mocked network)
├── test_search_router_router.py       # run_search orchestrator
├── test_backlog_reconcile.py          # Backlog ↔ run lifecycle sync
├── test_plan_run_metadata.py          # Metadata derivation during planning
├── test_writebacks.py                 # Writeback + evidence bundle assembly
├── test_planning.py                   # rf plan service
├── test_pipeline_ingest_extract_claims.py  # Full pipeline chain
├── test_end_to_end.py                 # Cross-service integration
└── ...
```

**Naming Convention**: `test_[module_or_feature].py`

### Python Test Commands

| Command | Purpose |
|---------|---------|
| `uv run pytest` | Run all tests (quick mode, `-q` from pyproject.toml) |
| `uv run pytest -v` | Verbose output |
| `uv run pytest --cov=research_foundry` | Run with coverage |
| `uv run pytest -k "search_router"` | Filter by keyword |
| `uv run pytest -m integration` | Integration tests only |
| `uv run pytest tests/test_serve_api.py` | Single file |

---

## Python Test Template (Service Layer)

```python
"""Test backlog metadata derivation."""
import pytest
from pathlib import Path

from research_foundry.services.backlog_metadata import (
    load_backlog_index,
    lookup_metadata,
    reconcile_backlog,
)
from research_foundry.paths import FoundryPaths


@pytest.fixture
def workspace(tmp_path: Path) -> FoundryPaths:
    """Create a minimal workspace with backlog + run fixtures."""
    backlog = tmp_path / "backlog" / "research_idea_backlog.yaml"
    backlog.parent.mkdir(parents=True)
    backlog.write_text("ideas:\n  - ref: RIB-001\n    title: Test Idea\n")
    return FoundryPaths(root=tmp_path)


class TestBacklogMetadata:
    def test_load_index_returns_mapping(self, workspace: FoundryPaths):
        index = load_backlog_index(workspace)
        assert "RIB-001" in index

    def test_lookup_missing_ref_returns_none(self, workspace: FoundryPaths):
        assert lookup_metadata("RIB-999", workspace) is None

    def test_reconcile_dry_run_no_writes(self, workspace: FoundryPaths):
        diffs = reconcile_backlog(workspace, dry_run=True)
        # dry_run should never mutate files
        assert isinstance(diffs, list)
```

---

## Python Test Template (FastAPI / Loopback API)

The loopback API uses `httpx` via Starlette's `TestClient` (declared in `[dev]` extras):

```python
"""Test loopback API endpoints."""
import pytest
from fastapi.testclient import TestClient

from research_foundry.api.app import create_app
from research_foundry.config import FoundryConfig


@pytest.fixture
def client(tmp_path):
    """TestClient with a temporary workspace."""
    config = FoundryConfig.load(root=tmp_path)
    app = create_app(config)
    return TestClient(app)


class TestRunsAPI:
    def test_health(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_list_runs_empty(self, client: TestClient):
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_run_detail_not_found(self, client: TestClient):
        resp = client.get("/api/runs/nonexistent")
        assert resp.status_code == 404
```

---

## Python Test Template (Search Router)

```python
"""Test search router orchestrator."""
import pytest
from unittest.mock import patch, MagicMock

from research_foundry.services.search_router.router import run_search
from research_foundry.paths import FoundryPaths


@pytest.fixture
def search_workspace(tmp_path):
    runs = tmp_path / "runs" / "test-run"
    runs.mkdir(parents=True)
    return FoundryPaths(root=tmp_path)


class TestRunSearch:
    def test_run_search_no_providers_degrades(self, search_workspace):
        """Missing providers produce empty results, not exceptions."""
        result = run_search(
            paths=search_workspace,
            run_id="test-run",
            query="test query",
            mode="quick",
        )
        assert result is not None
        # Should still write search_run.yaml on disk
        assert (search_workspace.root / "runs" / "test-run" / "search_run.yaml").exists()
```

---

## Frontend: Runs-Viewer Tests (Vitest)

The runs-viewer is a Vite + React 18 SPA under `frontend/runs-viewer/`.

### File Structure

```
frontend/runs-viewer/
├── src/test/                          # Vitest unit/component tests
│   ├── run-table-title.test.tsx
│   ├── p3-components.test.tsx
│   ├── p4-components.test.tsx
│   ├── provenance-correctness.test.ts
│   ├── lineage-flow-edges.test.tsx
│   └── ...
├── src/hooks/hooks.test.tsx           # Hook tests (colocated)
├── src/lib/
│   ├── auditStateMachine.test.ts
│   ├── format.test.ts
│   └── runs.test.ts
├── e2e/                               # Playwright E2E specs
│   ├── runs-facelift-v2.spec.ts
│   ├── w1-claim-audit.spec.ts
│   ├── w2-verification-checklist.spec.ts
│   └── w3-report-chip-navigation.spec.ts
└── playwright.config.ts
```

### Frontend Test Commands

| Command | Purpose | CWD |
|---------|---------|-----|
| `pnpm test` | Run all Vitest tests | `frontend/runs-viewer/` |
| `pnpm test:watch` | Watch mode | `frontend/runs-viewer/` |
| `pnpm exec playwright test` | Run Playwright E2E headless | `frontend/runs-viewer/` |
| `pnpm exec playwright test --ui` | Playwright interactive UI | `frontend/runs-viewer/` |

---

## Frontend Component Test Template (Vitest + RTL)

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { RunTable } from '../components/RunTable';

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('RunTable', () => {
  it('renders run titles from fixture data', () => {
    render(<RunTable runs={[{ id: 'r1', title: 'My Run' }]} />, {
      wrapper: createWrapper(),
    });
    expect(screen.getByText('My Run')).toBeInTheDocument();
  });

  it('shows empty state when no runs', () => {
    render(<RunTable runs={[]} />, { wrapper: createWrapper() });
    expect(screen.getByText(/no runs/i)).toBeInTheDocument();
  });
});
```

---

## Frontend E2E Template (Playwright)

Playwright tests run against `vite dev` on port 5175 (configured in `playwright.config.ts`):

```typescript
import { test, expect } from '@playwright/test';

test.describe('Runs Viewer', () => {
  test('displays run list on load', async ({ page }) => {
    await page.goto('/');
    // Wait for the run table to render from bundled fixture data
    await expect(page.getByRole('table')).toBeVisible();
    await expect(page.getByRole('row')).not.toHaveCount(0);
  });

  test('navigates to run detail', async ({ page }) => {
    await page.goto('/');
    // Click first run link
    const firstLink = page.getByRole('link').first();
    await firstLink.click();
    // Should show claim ledger section
    await expect(page.getByText(/claims/i)).toBeVisible();
  });

  test('claim audit checklist toggles', async ({ page }) => {
    await page.goto('/');
    const firstLink = page.getByRole('link').first();
    await firstLink.click();
    // Find and toggle a verification checkbox
    const checkbox = page.getByRole('checkbox').first();
    await checkbox.check();
    await expect(checkbox).toBeChecked();
  });
});
```

---

## Common Antipatterns (Python)

### Using bare `python` or `pytest`

```bash
# ❌ BAD: bare shim — missing deps
pytest tests/
python -m pytest tests/

# ✅ GOOD: project venv
uv run pytest tests/
./.venv/bin/python -m pytest tests/
```

### Hardcoding paths or relying on CWD

```python
# ❌ BAD: absolute or CWD-relative paths
data = open("runs/test/run.yaml").read()

# ✅ GOOD: use FoundryPaths from fixture
data = (workspace.root / "runs" / "test" / "run.yaml").read_text()
```

### Not isolating file-system tests

```python
# ❌ BAD: writing to repo working tree
workspace = FoundryPaths(root=Path("."))

# ✅ GOOD: use tmp_path fixture
@pytest.fixture
def workspace(tmp_path):
    return FoundryPaths(root=tmp_path)
```

---

## Common Antipatterns (Frontend)

### Using `jest.*` in Vitest

```typescript
// ❌ BAD: jest globals don't exist in Vitest
jest.fn();
jest.mock('./module');

// ✅ GOOD: import from vitest
import { vi } from 'vitest';
vi.fn();
vi.mock('./module');
```

### Missing router/query wrappers

```typescript
// ❌ BAD: components that use useParams / useQuery crash
render(<RunDetail />);

// ✅ GOOD: wrap in providers
render(<RunDetail />, { wrapper: createWrapper() });
```

---

## Quick Reference

### Python

```bash
uv run pytest                             # all tests
uv run pytest -k "serve"                  # keyword filter
uv run pytest --cov=research_foundry      # coverage
uv run pytest tests/unit/                 # unit only
uv run pytest -m integration              # integration only
```

### Frontend (from `frontend/runs-viewer/`)

```bash
pnpm test                                 # vitest (all unit)
pnpm test:watch                           # vitest watch
pnpm exec playwright test                 # e2e headless
pnpm exec playwright test --ui            # e2e interactive
```

### Debugging

```bash
# Python: drop into debugger on failure
uv run pytest --pdb tests/test_serve_api.py

# Python: show full diff on assertion failure
uv run pytest -vv

# Frontend: vitest UI
pnpm test -- --ui

# Playwright: headed + slow-mo
pnpm exec playwright test --headed --slow-mo=500
```
