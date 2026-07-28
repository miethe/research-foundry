---
schema_version: 2
doc_type: report
report_category: finding
title: "Findings: Research Foundry Knowledge MCP"
status: draft
source: agent
created: 2026-07-27
updated: 2026-07-27
feature_slug: research-foundry-knowledge-mcp
promoted_to: null
related_plan: docs/project_plans/implementation_plans/enhancements/research-foundry-knowledge-mcp-v1.md
---

# Findings — Research Foundry Knowledge MCP (P6)

## Phase P6 Findings

### KMCP-F1 — `rf-knowledge-mcp` process transitively requires the `serve` extra (fastapi/uvicorn/starlette), not only `mcp`

**Discovered:** P6 (KMCP-6.2, process/tool/SDK gate), 2026-07-27, while investigating whether the
`AuthIdentity` import in `src/research_foundry/services/knowledge_access.py` could be decoupled
from FastAPI by a purely mechanical change (per this phase's own task instructions, mirroring the
precedent already set by `research_foundry/services/search_router/mcp_launcher.py`, which imports
`AuthIdentity` only inside `TYPE_CHECKING` plus lazily inside the two functions that actually
construct one).

**Symptom:** `import research_foundry.knowledge_mcp.process` (the packaged `rf-knowledge-mcp`
entry point) pulls `fastapi`, `starlette`, and `uvicorn` into `sys.modules`, even though this
process declares only the `mcp` extra in `pyproject.toml` and its own module docstrings
(`process.py`, `registry.py`, `settings.py`) describe it as an independent process boundary that
never depends on the Search Router / Operator / `serve` surface. Confirmed live:

```
$ .venv/bin/python -c "
import sys
import research_foundry.knowledge_mcp.process
print('fastapi' in sys.modules)   # -> True
"
```

**Root cause — TWO separate transitive imports, not one:**

1. `knowledge_access.py` imports `AuthIdentity` from `..api.auth.provider` at module level, used
   only as a type annotation (`identity: AuthIdentity | None` on `KnowledgeAccessContext` and
   `resolve_context`). Because the module has `from __future__ import annotations`, this
   annotation is never evaluated at runtime and no call site does `isinstance()`/`get_type_hints()`
   against it — this half genuinely IS a purely mechanical, non-behavioral fix (verified: grep for
   `get_type_hints`/`ka.AuthIdentity` outside the module returns zero hits), and mirrors
   `mcp_launcher.py`'s own precedent exactly (`TYPE_CHECKING` import + a second, lazy,
   inside-the-function import at the one or two call sites that actually construct an
   `AuthIdentity`).

2. `knowledge_access.py` ALSO imports `resolve_workspace_isolation_active` from `..api.auth.scope`
   at module level, and calls it as a REAL runtime function (not a type annotation) at line ~1075
   (`SourceKindProjector`'s workspace-scoping check). This import is genuinely load-bearing
   business logic, not decorative — `mcp_launcher.py` has no equivalent call at all (it uses its
   own independent, non-WKSP-304 identity/sensitivity mechanism), so there is no existing
   "lazy-import" precedent to mirror for this half.

3. **The two are not independent in practice.** `research_foundry/api/__init__.py` unconditionally
   does `import fastapi; import uvicorn` in its own package body (not lazily, not inside
   `create_app`) — by design, so that importing the always-installed `research_foundry.api`
   package fails loudly and immediately if the `serve` extra is missing, rather than failing
   confusingly deep inside route registration. Python always executes a package's `__init__.py`
   before any of its submodules, so **any** import reaching into `research_foundry.api.*` —
   `..api.auth.provider` (`AuthIdentity`) OR `..api.auth.scope`
   (`resolve_workspace_isolation_active`) — triggers that same unconditional probe. Confirmed live
   that `import research_foundry.api.auth.scope` alone (with no `AuthIdentity` import at all) still
   pulls `fastapi` into `sys.modules`, for exactly this reason.

**Why the purely-mechanical fix is NOT sufficient on its own:** relocating only the `AuthIdentity`
import to `TYPE_CHECKING` (as this phase's task instructions authorize for a mechanical,
non-behavioral change) would NOT achieve "the process import graph no longer pulls fastapi" — the
`resolve_workspace_isolation_active` import remains eager and load-bearing, and it alone still
transits through `research_foundry.api.__init__`'s unconditional probe. Making it lazy too (moving
the import inside the one function that calls it) goes beyond a decorative annotation change: it
would alter *when* a missing-fastapi environment fails (at process-import time today, versus at
first-source-search-call time after the change) — a real, observable behavior difference this
phase's instructions explicitly say to avoid ("If it would require ANY auth logic/behavior change,
do NOT"). A full fix would require relocating `resolve_workspace_isolation_active` (or
`AuthIdentity`) out of the `research_foundry.api.*` package hierarchy entirely — a structural
change touching `catalog_service.py`, `builder_service.py`, `AgentJobService`, and every other
existing call site that already imports it from there today, which is out of scope for a
mechanical P6 hardening pass.

**Decision:** no code change made in `knowledge_access.py` for this finding. `AuthIdentity`
remains a module-level import (kept consistent with, and no worse than, the equally-eager
`resolve_workspace_isolation_active` import right below it — splitting the two into
differently-lazy forms while leaving the underlying dependency unresolved would add churn without
closing the gap).

**Impact — scoped precisely, not overstated:**

- AC KMCP-1's actual *forbidden* set (Search Router / Operator registries, provider
  credentials/clients, mutators, cost-bearing tools) remains genuinely absent from the process's
  transitive import graph — this finding does not weaken that guarantee. Verified directly against
  the real transitive closure (not just the four `knowledge_mcp.*` files' own static AST imports)
  by `tests/test_knowledge_mcp_process.py::test_full_process_import_transitive_closure_excludes_search_router_and_operator_but_documents_fastapi`.
- `rf-knowledge-mcp` needs the `serve` extra installed (or the full dev venv, which already
  bundles `mcp + dev + serve + pdf + search`) to import successfully in practice, contradicting
  its own `pyproject.toml` declaration of only the `mcp` extra and its module docstrings'
  "independent process, no Search Router/Operator dependency" framing. An operator who installs
  ONLY `pip install 'research-foundry[mcp]'` (no `serve`) will see the process fail at import time
  with `ModuleNotFoundError: fastapi`, not the module's own clear, hand-written
  `_MISSING_SDK_MSG` (which only covers a missing `mcp` SDK, not a missing `fastapi`).
- This is a real, pre-existing gap (also flagged by `[[project_knowledge_mcp_p4_stdio_process]]` at
  P4 and left unfixed at every subsequent phase) — not a regression introduced by this phase.

**Promotion trigger:** revisit once `AuthIdentity` and/or `resolve_workspace_isolation_active` are
decoupled from the `research_foundry.api.*` package (e.g. relocated to a neutral, non-FastAPI
module such as `research_foundry.services.sensitivity`/`research_foundry.paths`-adjacent, with the
`api.auth.*` modules re-exporting for back-compat) — at that point `rf-knowledge-mcp` can drop the
`serve` extra requirement and this finding can close. Until then, `pyproject.toml`'s `mcp` extra
declaration and this process's own "independent" framing should be read as "independent in code
authority/registry terms," not "installable without `serve`."
