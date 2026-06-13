# Layered Context Governance

Defines the ratified context model and budget guardrails.

## Ratified Layers

1. `Layer 0` runtime truth: machine-readable artifacts (`openapi.json`, hooks barrel, symbols).
2. `Layer 1` entry `CLAUDE.md`: routing + non-negotiable invariants only.
3. `Layer 2` key context: compact task-routing playbooks.
4. `Layer 3` deep context: domain docs and deep references.
5. `Layer 4` historical docs: reports/plans, never runtime truth.
6. `Layer 5` external retrieval: NotebookLM synthesis only, verify against Layer 0.

## Token Budgets

- `Layer 1` entry files: 150-300 lines each.
- `Layer 2` key-context docs: 120-250 lines each.
- `rules/` files (if retained): <= 40 lines and universal only.
- Per-task loaded context target (excluding code reads): <= 2,500 tokens.

## Ownership and Drift Checks

- Owners: platform maintainers for `CLAUDE.md`, domain owners for key-context docs.
- Drift check cadence: monthly.
- Required checks:
  - No dead links from entry `CLAUDE.md` files.
  - No references to missing rule files.
  - API claims in key-context validated against `skillmeat/api/openapi.json`.

## Change Policy

- New guidance starts in key-context unless globally universal.
- `rules/` additions require a universal-scope justification.
- Historical plans/reports must not be cited as canonical runtime behavior without Layer 0 verification.
