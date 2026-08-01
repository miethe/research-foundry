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

# M2 Leg C completion — OPM-5.5 packaging/entrypoint tests

## What I built

One new file, `tests/unit/test_operator_mcp_packaging.py` (6 tests). No other file touched, no
git commands run. Technique: the exemplar's child-interpreter pattern
(`test_operator_mcp_serve_extra_boundary.py`) — `subprocess.run([sys.executable, "-c", script])`
with a `sys.meta_path` finder blocking `mcp`/`mcp.*`, `PYTHONPATH=<repo>/src`. Chose this over Leg
B's in-process `builtins.__import__` monkeypatch since this venv genuinely has `mcp` installed
(integration tests `importorskip("mcp")` against it) — a fresh subprocess is the only way to prove
"unimportable", not just "not yet imported in this process".

## Tests and intent

1. `test_process_entrypoint_resolves_without_mcp_sdk` — mcp blocked: `from
   research_foundry.operator_mcp.process import main` succeeds; `main` callable.
2. `test_pyproject_declares_operator_mcp_script_and_mcp_extra_pin` — `tomllib`-parses
   `pyproject.toml`: `[project.scripts]["rf-operator-mcp"] ==
   "research_foundry.operator_mcp.process:main"`; `[project.optional-dependencies]["mcp"] ==
   ["mcp>=1.0,<2"]` (exact list equality — fails loudly on a second appended pin).
3. `test_import_performs_no_auto_start_side_effects` — mcp blocked: imports `.operator_mcp`,
   `.process`, `.server`; asserts thread count unchanged, a socket-subclass trap never fires, AST
   walk finds no module-level `socket` import, stdout has none of
   `jsonrpc`/`Content-Length`/`initialize` (proves `server.run()` never fires on import).
4. `test_build_server_raises_single_hint_runtime_error_without_sdk` — mcp blocked:
   `build_server()` raises `RuntimeError`; message contains `"uv sync --extra mcp"` and
   `"research-foundry[mcp]"` **exactly once each** (`str.count(...) == 1`).
5. `test_base_package_imports_without_mcp_sdk` — mcp blocked: bare `import research_foundry`
   stays clean.
6. `test_rf_cli_help_exits_zero` — real subprocess `./.venv/bin/rf --help` exits 0.

Items 1–4 map 1:1 to the assignment's four checks; #5/#6 split the assignment's #5 ("base CLI
unaffected") into its two independent halves (in-process import vs. the real binary).

## Judgment calls / flagged failures

No flags, no `xfail` — all 6 tests passed on first write against the existing implementation
(`operator_mcp/{__init__,process,server}.py`, `pyproject.toml` lines 60–90); nothing contradicted
D1/D2. Combined static (AST) + dynamic (socket trap, thread count) checks for "no auto-start"
rather than picking one, per the assignment's own non-exclusive "e.g." framing. Verified the `mcp`
extra pin with exact list equality, not substring containment, per D2's "no new extra". Did not
duplicate Leg B's `tests/test_operator_mcp_offline_import.py` cases (similar-shaped
entrypoint/build_server checks exist there, in-process) — mine differ in technique (real
subprocess) and add pyproject parsing, no-auto-start, and the real `rf` binary; no name collisions.

## Commands run (real tails)

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_packaging.py -q
......                                                                   [100%]

$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_packaging.py tests/unit/test_operator_mcp_serve_extra_boundary.py tests/test_operator_mcp_offline_import.py -q
................                                                          [100%]

$ flake8 tests/unit/test_operator_mcp_packaging.py --select=E9,F63,F7,F82
(no output, exit 0)
```

`addopts = "-q"` here suppresses the "N passed" summary (confirmed: `-v` restores it) — the dot
lines above are the real, un-truncated tails. 6 dots = my tests, green; 16 dots = mine + the
5-test exemplar + 5-test Leg B offline-import file, green, no collisions. `./.venv/bin/python -m
flake8` errors (`No module named flake8`; only `ruff` is in this venv's `dev` extra) — used the
`pyenv`-shim global `flake8` instead, fine for a syntax-only selector set needing no project deps.

## What the security lens should attack first

Nothing here touches production code — no new attack surface. Re-checking test validity: the
socket-subclass trap in test 3 only intercepts `socket.socket(...)`, not the raw `_socket.socket`
primitive or an `asyncio` event-loop's internal self-pipe; the AST check is a partial backstop,
not exercised because nothing in `operator_mcp/*` does any of that today.
