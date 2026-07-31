---
type: worknote
schema_version: 2
doc_type: worknote
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: in_progress
created: '2026-07-31'
updated: '2026-07-31'
---

# M2 — implementer contract (DECIDED)

Authoritative for the M2 legs ("The stdio surface exists and provably cannot execute" — scoped to
every path a real caller can drive, not to arbitrary in-process code execution; see `m2-fix-contract.md`'s
TERRA-5 adjudication and `server.py`'s module docstring, "Scope of the stdio-only guard" section,
added in fix cycle 1/2, SEC-8; supersedes
P5; tasks OPM-5.1..5.6). Design questions are **already decided here** — do not re-open them; if
you believe a decision is wrong, STOP and report rather than deviating. A non-blocking judgment
call gets logged in your completion note and you keep going.

Read first:
- Plan §M2 + "AC -> command -> evidence": `docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md`
- PRD §6.1 tool inventory + AC OPM-6/OPM-7: `docs/project_plans/PRDs/enhancements/research-foundry-operator-mcp-v1.md`
- M1 AAR "Carry into M2": `.claude/worknotes/research-foundry-operator-mcp/m1-remainder-aar.md`

## Leg ownership (disjoint; violating file ownership is a STOP)

| Leg | Tasks | Owns (exclusively) |
|---|---|---|
| A | OPM-5.3 | `src/research_foundry/services/writeback.py`, `src/research_foundry/services/operator_mcp_adapters/writeback_preview.py`, `operator_mcp_adapters/__init__.py` (registration + `__all__` lines only), `tests/unit/test_operator_mcp_adapter_writeback_preview.py`, `tests/integration/test_operator_mcp_writeback_preview.py` |
| B | OPM-5.1 + OPM-5.2 + OPM-5.4 | `src/research_foundry/operator_mcp/` (new package), `pyproject.toml`, `tests/integration/test_operator_mcp_server.py`, `tests/test_operator_mcp_offline_import.py` |
| C | OPM-5.5 | `tests/unit/test_operator_mcp_packaging.py` (new file ONLY) |

## Hard boundaries (violating any is STOP-and-report, not a judgment call)

1. **Do not edit** `operator_mcp_policy.py`, `operator_operation_service.py`,
   `operator_cancel_resume_service.py`, or `operator_mcp_adapters/base.py` — P1/P2-gated
   confirmation/authorization surfaces. If preflight or error mapping seems to require a policy
   edit, STOP and report.
2. **Do not edit** `src/research_foundry/knowledge_mcp/` — separate, shipped, read-only surface.
3. No Typer, `cli_commands`, `subprocess`, `os.system`, or `shell=True` anywhere in
   `operator_mcp/` or any adapter call path (test files exercising child interpreters via
   `subprocess` are exempt — tests only).
4. **Live writeback stays unreachable from every registered tool.** Turning the preview seam into
   a live writeback is Mode-D: STOP for explicit human approval regardless of anything else.
5. Do not modify existing tests. If an existing test pins behavior your change must alter, STOP
   and report (defect class 3 — the fix is inversion, but that is a reviewed decision).
6. Never `git stash`. To prove a regression test fails pre-change, copy the touched source file(s)
   to a scratch dir (`$CLAUDE_JOB_DIR/tmp` or `/tmp/m2-scratch-$$`), revert, run, restore from the
   copy. Never touch git state; the orchestrator is the only committer.
7. Additions to `.claude/` are limited to your own completion note.

## Decisions

### D1 — Package layout mirrors `knowledge_mcp` exactly

`src/research_foundry/operator_mcp/` = `__init__.py` (SDK-free; package docstring states scope +
the no-SDK guarantee), `server.py` (build_server + stdio-only guard + tool registration + envelope
mapping), `process.py` (`main()`: resolve paths/log level → `build_server()` → `server.run()`).
Package/module import NEVER requires the `mcp` SDK; only `build_server()` imports it, inside the
function, with the try/except → `RuntimeError` carrying exactly ONE install hint (mirror
`knowledge_mcp/registry.py:292-315` and its `_MISSING_SDK_MSG`: `uv sync --extra mcp` /
`pip install 'research-foundry[mcp]'`). Log-level env: `RF_OPERATOR_MCP_LOG_LEVEL`, same pattern
as `RF_KNOWLEDGE_MCP_LOG_LEVEL`; no other new env vars.

### D2 — Packaging reuses the existing `mcp` extra; no new extra, no auto-start

`pyproject.toml`: add `rf-operator-mcp = "research_foundry.operator_mcp.process:main"` to
`[project.scripts]` (beside `rf-knowledge-mcp`, ~line 75) with the same "reuses the shared mcp
extra" comment convention. Nothing else changes in packaging. No daemon, no listener, no import-time
side effects; hatchling picks up the new package automatically.

### D3 — Stdio-only guard is a LOCAL subclass (deliberate duplication)

`server.py` implements its own `_stdio_only_fastmcp_class` mirroring
`knowledge_mcp/registry.py:241-289`: a cached **subclass** of the real FastMCP; `sse_app`,
`streamable_http_app`, `run_sse_async`, `run_streamable_http_async` raise; the two `run_*_async`
overrides are deliberately NOT `async def`; `run(transport=...)` raises unless stdio. Do NOT import
private symbols from `knowledge_mcp.registry`. (Unification into a shared module is a filed
follow-up, not this milestone.)

### D4 — Tool inventory is derived, closed, and fail-loud

The registered tool set is exactly `operator_mcp_policy.TOOL_NAMES` (14 = the 13 `OPERATION_KINDS`
+ `operation.preflight`). Registration derives from that tuple: for each operation kind, the
handler resolves via `operator_mcp_adapters.get_adapter(kind)`; `operation.preflight` is the one
server-implemented meta tool (D5). **`build_server()` raises at build time** if any kind lacks a
registered adapter or any registered adapter's kind is not in `OPERATION_KINDS` — no silent
13-tool server, ever. No wildcard tool, no dynamic registration path, no name rewriting. Every
tool's input schema is closed (`additionalProperties: false`) — force it the way
`knowledge_mcp/registry.py:_close_input_schema` does. Tools registered with
`structured_output=False` + dual-encode (`CallToolResult` + `structuredContent`), same as
Knowledge MCP.

### D5 — `operation.preflight` is evaluate + mint, never consume, zero effect

Preflight calls `operator_mcp_policy.evaluate_policy(...)` and, on an allow decision, mints a
confirmation using the exact public policy functions exercised by
`tests/unit/test_operator_mcp_serve_extra_boundary.py:170` (read that test for the real names —
do not invent a new mint path). It NEVER consumes a token, never writes a manifest, receipt, or
artifact, and performs no filesystem mutation beyond what the policy functions themselves do.
Denials return the standard `build_error` envelope. Response = decision + confirmation record,
schema-valid against `operator_mcp_confirmation.schema.yaml`.

### D6 — `writeback.preview` is a pure-render adapter over a NEW client-free seam (Leg A)

- New adapter `operator_mcp_adapters/writeback_preview.py`, kind `writeback.preview` (already in
  `OPERATION_KINDS`), registered via `register()` like the other 12, dispatching through
  `base.run_pipeline` with a `_render` stage that calls the new seam below. Same
  resolve-don't-accept posture as M1: no `sensitivity_ceiling` parameter; workspace re-derived.
- New public `writeback.preview_writeback(run_id, *, targets=..., paths=None, now=None) ->
  WritebackPreviewResult` in `writeback.py`: validates bundle + targets + policy using the
  existing validation paths, renders per-target candidates using ONLY client-free renderers, and
  writes them under the operation staging root. It must be impossible to reach a live emit from
  it: **no integration-client import, construction, or call in its entire call graph.**
- **Layer-below refactor (the point of this leg):** `_render_intenttree_update`,
  `_render_arc_council`, and `_render_notebolm_update` (sic — `_render_notebooklm_update`) each
  construct a live client internally today. Split each into a pure payload-render function (no
  client, no network, no import of `..integrations`) + the existing live path recomposed as
  pure-render → emit. Live behavior must be byte-identical: every existing writeback test stays
  green UNMODIFIED. If a split cannot preserve behavior, STOP and report.
- **Staging root:** stage under the operation's own directory, colocated with where
  `operator_operation_service` writes manifests/receipts —
  `<operation_dir>/staging/writeback_preview/<target>.md|.json`. Read
  `operator_operation_service.py` to match the exact layout convention; record the resolved path
  shape in your completion note. Nothing is written outside the workspace; nothing outside the
  operation dir.
- **Per-target statuses** for missing / degraded / review-required targets come from a closed
  vocabulary defined as a module-level tuple in `writeback.py` (no open strings), returned in the
  preview result payload, and validated in tests. Error paths (not the per-target statuses) use
  the standard closed `build_error` reason codes. If you believe the closed error enum needs a new
  member, STOP and report — the enum is frozen.
- `dry_run=True` on the adapter behaves exactly like every other adapter (policy stages only —
  even the staged preview file is NOT written).

### D7 — Transport error mapping wraps, never invents (Leg B)

Adapter-returned error envelopes pass through untouched (they are already `build_error` products).
The server maps ONLY transport-level failures, all via `operator_mcp_policy.build_error`:
unknown tool → `tool_unknown`; payload over the policy caps → `payload_too_large` (check size
BEFORE deserializing where the SDK allows); any unexpected exception in a handler →
`internal_error` with `_redact_and_bound`-safe detail. No raw exception, traceback, or absolute
path ever crosses the transport. Wrong-workspace refs surface as whatever the policy/adapter layer
already returns (`not_found` two-shape rule) — the server adds NOTHING that could distinguish
existence. Result payloads are bounded: reuse the policy caps; no unbounded lists or blobs.

### D8 — Per-tool caller-input inventory table (MANDATORY, every leg)

M1's top carry-in. Your completion note MUST contain, for every tool/handler you author or wire:
a table of **every caller-supplied input that reaches a canonical service or policy function, and
what authorizes/bounds it** (policy stage, cap, enum, re-derivation). "The guard was right but the
parameter inventory was incomplete" caused 3 of 6 M1 defects — enumerate siblings, not just the
field you were told about. The security lens reads these tables first.

### D9 — Tests to write (per leg; prove failure pre-change per boundary rule 6)

- Leg A: unit adapter test (parity + dry-run + denial paths, mirroring
  `test_operator_mcp_adapter_verify_bundle.py`) + `tests/integration/test_operator_mcp_writeback_preview.py`:
  runtime spies monkeypatching `IntentTreeClient`, `ArcClient`, `get_notebooklm_client`,
  `get_meatywiki_client`, and `httpx` — **assert zero constructions and zero calls on every
  preview path**, including denial and degraded paths; plus staged-artifact content assertions.
- Leg B: `tests/test_operator_mcp_offline_import.py` mirroring
  `test_knowledge_mcp_offline_import.py` (block `mcp` imports; package imports clean; server build
  raises the single-hint RuntimeError; operator_mcp package never imports `knowledge_mcp`,
  `search_router`, or `..integrations`); `tests/integration/test_operator_mcp_server.py`
  (`importorskip("mcp")`): exact-14 inventory introspection diff vs `TOOL_NAMES`, zero overlap
  with `knowledge_access.TOOL_NAMES` (8), closed input schemas, oversize/internal-error/unknown-
  tool envelope tests, preflight allow/deny, stdio-only guard raises on SSE/HTTP.
- Leg C: packaging tests mirroring the strongest existing pattern
  (`test_operator_mcp_serve_extra_boundary.py`: child interpreter via `subprocess`): module
  entrypoint resolves (`python -c "from research_foundry.operator_mcp.process import main"`),
  `rf --help` works with SDK absent, `[project.scripts]` contains `rf-operator-mcp`, import of
  `research_foundry.operator_mcp` performs no auto-start/listener (no socket, no thread spawn at
  import), base import with `sys.modules['mcp']` blocked stays clean.

Full-suite baseline: 3 known-failing nodes pre-exist (documented in M1 notes) — do not chase them;
report any NEW failure.

### D10 — Integration note for parallel legs

Legs A and B run concurrently with disjoint files. Leg B: if `writeback.preview` is not yet
registered when you self-test, your fail-loud build (D4) raising IS the correct behavior — verify
that path, leave the exact-14 inventory test in place, and note it; the orchestrator runs the
integrated suite after both legs land. Leg A: registration in `operator_mcp_adapters/__init__.py`
is yours (side-effect import + `__all__`), matching lines 91-97 pattern.

## Completion note (each leg, REQUIRED)

`.claude/worknotes/research-foundry-operator-mcp/m2-leg-<a|b|c>-completion.md`: what you built,
the D8 inventory table, every judgment call + rationale (flagging is a first-class outcome —
M1's ICA legs were praised for it), test counts, commands run + real tails, and anything you
believe the security lens should attack first.
