---
name: project-knowledge-mcp-p4b-rf-tools-inventory
description: RF Knowledge MCP Phase P4 Part B (rf_* tools + exact eight-tool inventory gate, KMCP-4.3/4.4) shipped; key non-obvious findings for whoever runs P5/P6
metadata:
  type: project
---

KMCP-4.3/4.4 ("Phase P4 Part B") shipped on top of [[project_knowledge_mcp_p4_stdio_process]]'s Part A: registers
`rf_search`/`rf_fetch` (thin calls to `KnowledgeAccessService.search_extended`/`fetch_extended`, `include_receipt=True`
always) and the four typed getters `rf_source_get`/`rf_assertion_get`/`rf_report_get`/`rf_run_get` in
`src/research_foundry/knowledge_mcp/registry.py`. Adds `tests/test_knowledge_mcp_process.py` (22 tests) as the
authoritative eight-tool process/inventory/transport/environment gate (KMCP-4.4). 300+11 tests green
(`tests/test_knowledge_mcp_process.py` + `tests/unit/test_knowledge_mcp_registry.py` updated Part-A-only assertions +
full `test_knowledge_access.py`); ruff/mypy clean on `src/research_foundry/knowledge_mcp`.

**Why:** decisions-block §9.2's exact eight-tool inventory and §0's "typed getters as thin service calls" — this phase
only wires transport, it never adds new service-layer business logic (`knowledge_access.py` untouched).

**Non-obvious findings for KMCP-5 (CLI/API parity) and KMCP-6 (hardening/closeout):**

1. **`rf_assertion_get`/any `assertion`-kind `search`/`rf_search` result is UNREACHABLE through this local stdio
   process, for every id, always** — not a bug, a real v1 limitation worth flagging loudly to whoever builds P5.
   `registry.py`'s `_context()` helper hardcodes `identity=None` ("local trust" — no separate remote auth in v1;
   `settings.py`'s own docstring). `AssertionCatalog.search_read_only`/`packet_read_only` BOTH unconditionally raise/
   deny when `identity is None` — this is an assertion-catalog invariant, NOT gated by the WKSP-304 isolation flag
   (unlike `source`/`run`/`report_*`, which all short-circuit-allow when `identity is None`, per
   `export_service._run_read_allowed`'s own "identity is None... short-circuits to True" docstring). P5's CLI/API
   transports resolve a REAL identity, so this gap is transport-specific to P4's stdio process, not a service defect.
   Proved live in the new test file even with a REAL, materialized, eligible assertion id (not just a malformed one).

2. **Typed-getter kind scoping is enforced in the REGISTRY, not the service** — `knowledge_access.py` has no
   per-tool/per-kind restriction on `fetch_extended` (any tool name in `TOOL_NAMES` can fetch any of the 5 kinds).
   `rf_source_get`/`rf_run_get`/`rf_assertion_get` each pre-check `parse_knowledge_id(id)[0] in {expected_kind}` and
   `rf_report_get` checks `in {"report_draft", "report_final"}` (KMCP-OQ-2: one getter, two kinds) — BEFORE ever
   calling `fetch_extended`, so a wrong-kind id never touches its governed read authority. A mismatch raises
   `ka.KnowledgeDenied("kind_not_eligible")` caught by the SAME broad `except ka.KnowledgeAccessError` and mapped to
   the SAME generic `_FETCH_DENIED_MESSAGE` as every other denial cause — never a distinguishing "wrong kind" signal
   (mirrors `ReportKindProjector`'s own mismatched-kind-id contract, generalized to all four getters).

3. **`rf_search`/`rf_fetch` reuse the CORE tools' exact safe-denial shape, extended.** `rf_search` catches
   `ka.KnowledgeAccessError` broadly and returns `ka.RfKnowledgeSearchOutcome().to_dict()` (empty, receipt-less) —
   never builds a receipt for a denied/errored call (a receipt is only ever built from an already-succeeded outcome).
   `rf_fetch` and all four typed getters reuse the literal SAME `_FETCH_DENIED_MESSAGE` string constant as core
   `fetch` — a caller can never distinguish malformed/missing/hidden/cross-kind/local-trust-denied by message text.

4. **`inspect.signature(func, eval_str=True)` in the installed `mcp` SDK's `func_metadata.py` resolves
   `from __future__ import annotations`-stringified type hints correctly** — confirmed `list[str] | None = None` (the
   `rf_search` `kinds` param) round-trips through FastMCP's argument-model builder fine despite `registry.py` having
   postponed annotations at module scope; no need to avoid PEP 563 syntax for tool function signatures in this SDK
   version.

5. **AST-based import ALLOWLIST test needs per-alias dotted-path resolution, not just `node.module`.** For
   `from research_foundry.services import knowledge_access as ka`, `ast.ImportFrom.module` is only
   `"research_foundry.services"` — the actually-imported target is `f"{node.module}.{alias.name}"` =
   `"research_foundry.services.knowledge_access"`. A prefix-allowlist check against `node.module` alone would
   wrongly reject this legitimate import; `tests/test_knowledge_mcp_process.py::_resolved_absolute_imports` builds
   the per-alias resolved path first.

6. **The `_install_write_surface_spies`/`_snapshot_tree` helpers from `tests/unit/test_knowledge_access.py` are
   directly reusable at the FULL PROCESS level** — imported by name into the new process test file (same "sibling
   test module" convention already used repo-wide) to prove zero write-surface calls across all eight registered
   tools with real fixtures seeded across all five kinds, rather than re-deriving the spy list.

7. **Part A's still-open `AuthIdentity` module-level-import/`serve`-extra-dependency gap (memory item 1 in
   [[project_knowledge_mcp_p4_stdio_process]]) remains UNFIXED** — out of scope for this task too (registry-layer
   wiring only, no `knowledge_access.py` changes). Still worth a decision before KMCP-6 closeout.

See [[project_knowledge_mcp_p4_stdio_process]] for Part A's own findings (still-relevant gotchas 2-4 there).
