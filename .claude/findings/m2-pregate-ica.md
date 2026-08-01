---
type: worknote
schema_version: 2
doc_type: worknote
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: completed
created: '2026-07-31'
updated: '2026-07-31'
---

# M2 pre-gate empirical review (ICA) — server/transport/writeback-preview

All checks executed against `./.venv/bin/python` (`mcp==1.29.0`), commit = M2 wave 1
(`a759aa6`). Every experiment ran a real command; tails below are trimmed (log
lines with `[timestamp] WARNING ...` elided for brevity, content unaffected).
Scratch scripts under `/tmp/m2-ica/` (never touched repo source/tests, no `git`
commands run). Post-hoc `git status --porcelain` confirmed zero repo-side-effects
from any experiment (only pre-existing untracked `m2-pregate-terra.md`).

## E1 — VERIFIED: exact-14 inventory, name equality, zero overlap, closed schemas

```
count: 14
names==TOOL_NAMES sorted: True
overlap with knowledge_access: set()
bad_schema: []
TOOL_NAMES len: 14  |  knowledge_access.TOOL_NAMES len: 8
```
`build_server()` (in-process, `research_foundry.operator_mcp.server`) registers
exactly `operator_mcp_policy.TOOL_NAMES` (13 `OPERATION_KINDS` + `operation.preflight`),
zero overlap with `knowledge_access.TOOL_NAMES` (8), every `Tool.parameters['additionalProperties'] is False`.

## E2 — VERIFIED (with a LOW note): undeclared extra args never reach `adapter.invoke`

Drove `run.plan`, `source.ingest`, `writeback.preview`, `operation.preflight`
through `server.call_tool(name, arguments)` (the real dispatch path, not the
adapter directly) with an extra top-level key (`EXTRA_UNDECLARED`/`HACK`/
`SNEAKY`/`ROGUE`) alongside legitimate args, spying on `adapter.get_adapter`'s
returned adapter's `.invoke(**kwargs)`:
```
adapter.invoke call count: 3 (run.plan denied identity_denied; source.ingest/
writeback.preview raised internal_error for an UNRELATED reason — see below)
recorded kwargs for run.plan:      {'idempotency_key':'k1','confirmation_record':None,
                                     'presented_token':None,'dry_run':False,'paths':...,
                                     'intent_id':'i1'}   # no EXTRA_UNDECLARED key
```
Isolated `source.ingest`'s `internal_error`: reproduced identically **with the
extra key removed** (baseline, no `HACK`) — proves the error is caused by a
missing required `input_payload` field, not the injected key. Confirmed via
`mcp.server.fastmcp.utilities.func_metadata.FuncMetadata.call_fn_with_arg_validation`
source read: `arg_model.model_validate(...)` then `model_dump_one_level()` —
only fields declared on the pydantic arg model are ever passed to the handler.

**LOW note (not blocking):** the mechanism is **silent drop**, not **explicit
rejection**. `ArgModelBase.model_config = ConfigDict(arbitrary_types_allowed=True)`
— no `extra="forbid"` — so pydantic's v2 default (`extra="ignore"`) drops
unknown top-level keys with no error signal to the caller. `additionalProperties:
false` in the *advertised* `list_tools()` schema is therefore enforced only by
omission-from-the-model, not by a request-level rejection. Security-neutral
(nothing ever reaches the adapter), but a caller sending garbage extra fields
gets silent success/normal-denial instead of a validation error — worth noting
for anyone reading D4 as "the server rejects unknown fields."

## E3 — VERIFIED: `writeback.preview` is client-free and staging-contained across every reachable outcome

Built an isolated tmp `FoundryPaths` workspace (mirrors `tests/conftest.py`'s
`tmp_foundry`), a real run+bundle, then drove **every** outcome through the
REAL MCP dispatch (`server.call_tool("writeback.preview", ...)`), spying on
`IntentTreeClient.from_config`, `ArcClient.from_config`, `get_notebooklm_client`,
`get_meatywiki_client`, `urllib.request.urlopen`, **and `socket.socket`** (beyond
D9's mandated list) — each spy raises `AssertionError` on touch:

| Path | isError | Spies fired | Files changed outside `staging/` or `.rf_state` |
|---|---|---|---|
| happy (5 targets, notebook bound) | False | none | `[]` |
| second call, same run, 1 target (E7) | False | none | `[]` |
| missing bundle (5 targets) | False (`bundle_found:false`) | none | staging dir never created |
| unsupported target (`ccdash`) | False (`unsupported_target`, `staged_path:null`) | none | `[]` |
| review-required denial (`arc`+`meatywiki`, client_sensitive) | True (`guard_review_required`) | none | staging dir never created |
| degraded (blank `intenttree_node_ref`) | False (`degraded`, still stages) | none | `[]` |

All 6 paths: zero constructions/calls on all 6 spies. `.rf_state` (the operator
operations DB — global substrate, not run-scoped) is the only location that
changes outside the run's own `staging/writeback_preview/` — expected, not a leak.

## E7 — VERIFIED: no cross-call content/attribution leak

Second call (different idempotency_key, single target `intenttree`, same run)
returns an envelope containing **only** the `intenttree` target it requested;
its staged `intenttree.json` content is byte-identical to the first call's
(deterministic per-run render, not idempotency-key-keyed) — no mixing. The
first call's other 4 staged files (`arc.json`/`meatywiki.md`/`notebooklm.json`/
`skillmeat.md`) remain on disk untouched (matches Leg A's own JC-1 flag:
staging is idempotent-overwrite-per-target, not per-operation-namespaced).
This is a **known, already-flagged limitation** (JC-1), not a new defect: a
caller with independent filesystem read access to `<run>/staging/` could see
a *different* caller's staged preview content for that run — but nothing in
the MCP envelope itself misattributes content across operations.

## E4 — VERIFIED: stdio-only guard raises before any socket/server work, every path tried

Spied `socket.socket` globally, then exercised: `run(transport="sse")`,
`run(transport="streamable-http")`, `run(transport="sse", mount_path="/x")`,
`run_sse_async()`, `run_streamable_http_async()`, `sse_app()`,
`sse_app(mount_path="/x")`, `streamable_http_app()`.
```
run(transport=sse)                     => raised UnsupportedTransportError
run(transport=streamable-http)         => raised UnsupportedTransportError
run_sse_async()                        => raised UnsupportedTransportError
run_streamable_http_async()            => raised UnsupportedTransportError
sse_app() / sse_app(mount_path=/x)     => raised UnsupportedTransportError
streamable_http_app()                  => raised UnsupportedTransportError
run(transport=sse, mount_path=/x)      => raised UnsupportedTransportError
sockets opened during all attempts: []
```
Confirmed via source read: base `FastMCP.run()`'s `match transport: case "sse":
anyio.run(lambda: self.run_sse_async(...))` is never reached — the subclass's
`run()` override raises before ever calling `super().run()` for a non-stdio
value, and `self.run_sse_async`/`self.streamable_http_app` resolve to the
overridden bound methods (genuine subclass, confirmed no separate wrapped
instance exists for `__self__` to resolve to instead).

## E5 — VERIFIED: oversize payload → bounded `payload_too_large`, zero partial execution

200KB `input_payload` blob through `server.call_tool("run.plan", ...)`,
`adapter.get_adapter` spied:
```
isError: True
structuredContent: {'reason_code': 'payload_too_large', 'retryable': False, ...}
content length bytes: 247
adapter.invoke calls: []
```
Zero adapter dispatch (no partial execution). Ordering confirmed by source
read: `_check_transport_payload_size(arguments)` runs on the raw dict BEFORE
`await super().call_tool(name, arguments)` — i.e. before the SDK's own
`pre_parse_json`/pydantic `arg_model.model_validate` step and before any
adapter code. (The check operates on an already-parsed Python dict, not raw
wire bytes — the JSON-RPC frame itself is deserialized upstream by the SDK's
transport layer before `call_tool` is ever invoked; D7's "before deserializing
where the SDK allows" is satisfied at the layer this module actually controls.)

## E6 — VERIFIED: internal exception → redacted, bounded `internal_error`

Adapter monkeypatched to raise with an embedded fake absolute path +
traceback-shaped text in the exception message:
```
isError: True
structuredContent: {'reason_code': 'internal_error', 'retryable': True, ...}
raw text bytes: 248
SECRET_PATH leaked in envelope? False
word 'Boom' leaked? False | 'Traceback' leaked? False | 'raise' leaked? False
```
Server log line: `internal_error dispatching tool 'run.plan' (ToolError)` —
only `type(exc).__name__` (the SDK's wrapping `ToolError`, not even the inner
`Boom`), matching the docstring's claim; no `str(exc)` in logs either.

## E8 — VERIFIED: genuinely-unimportable-SDK reality (child interpreter, `sys.meta_path`)

Used `find_spec`-based `sys.meta_path` blocker (not `builtins.__import__`,
and not the legacy `find_module`/`load_module` API — confirmed empirically
that the old-style finder API is a no-op under this venv's Python 3.14; only
`find_spec` actually intercepts):
```
BASE_IMPORT_OK True
RuntimeError_uv_count 1
RuntimeError_pip_count 1
MSG: "The 'mcp' Python SDK is not installed. ... uv sync --extra mcp ... pip install 'research-foundry[mcp]'"
```
`./.venv/bin/rf --help`, exercised by invoking `research_foundry.cli:app()`
directly inside the SAME mcp-blocked child interpreter (stronger proof than
shelling the real binary — proves the CLI's `--help` path never transitively
imports `mcp`): `EXIT_CODE 0`, help text rendered normally.

## E9 — VERIFIED: no forbidden imports; import performs no handshake/listener

```
$ grep -rnE "^\s*(import|from)\s+(typer|cli_commands|subprocess)\b" src/research_foundry/operator_mcp/
NO REAL IMPORT MATCHES (clean)
$ grep -rn "os\.system(\|shell=True\|subprocess\." src/research_foundry/operator_mcp/*.py
(only doc-string prose mentioning the forbidden names, no real call/import site)
```
Import of `research_foundry.operator_mcp.process` with `socket.socket`
subclassed to raise on construction: no exception, thread count unchanged,
zero stdout/stderr. `process.main()`'s body (`build_server()` + `server.run()`)
is only reachable via an explicit call or the `if __name__ == "__main__":`
guard — never at import time.

## Additional observation (not one of E1-E9, informational only)

Several early experiments called `build_server()`/adapters with the DEFAULT
`paths=None` (→ `FoundryPaths.discover()`), which in this worktree resolves to
the **real repo root** (`./foundry.yaml`, `./runs/` exist here). Every such
call denied before any write (`identity_denied` / missing-required-kwarg
`internal_error` / transport-level `payload_too_large`) — `git status
--porcelain` confirmed zero repo mutation after the full review. Flagging only
as an experimental-hygiene note: any future empirical pass should default to
an isolated `paths=` fixture from the start rather than relying on early
denial to avoid touching the real workspace.

## ICA VERDICT: 0 findings, 0 blocking (1 LOW informational note under E2)

E1..E9 status: **E1 VERIFIED · E2 VERIFIED (LOW note) · E3 VERIFIED · E4 VERIFIED
· E5 VERIFIED · E6 VERIFIED · E7 VERIFIED · E8 VERIFIED · E9 VERIFIED**

No BLOCKING/HIGH/MED defects found empirically. The M2 wave-1 implementation
(server.py/process.py/writeback_preview.py) holds up under adversarial,
executed probing of every hypothesis in scope: closed tool inventory, transport
error mapping (size/unknown-tool/internal-error), stdio-only guard, and the
writeback-preview client-free seam — including the two paths (`socket.socket`
spy, MCP-dispatch-path E3/E7 rather than adapter-direct) that go beyond what
the existing test suite already exercises.
