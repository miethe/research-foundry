# LSP Diagnostics Rule (Global)

Invariant:

1. **LSP diagnostics are advisory, not authoritative.** The `<new-diagnostics>` system reminders report whatever the language server has at injection time. After parallel edits or multi-file changes, they are frequently stale — reflecting intermediate analysis states, not final truth.

2. **Never react to LSP diagnostics without verification.** Before fixing reported errors:
   - Run `npx tsc --noEmit 2>&1 | grep -v "__tests__/a11y/" | grep "error TS"` for TypeScript (filter known pre-existing test errors).
   - Run `flake8` or `mypy` for Python.
   - If a diagnostic disappears on re-check, it was stale — move on.

3. **Use LSP diagnostics efficiently (don't waste the signal).** They ARE useful for:
   - Catching obvious typos, missing imports, or syntax errors after single-file edits.
   - Quick sanity checks between sequential operations.
   - Spotting regressions immediately without running a full compile.

4. **Always run authoritative validation** after parallel subagent batches complete — never trust injected diagnostics alone for multi-agent work. Budget one `tsc --noEmit` call per batch completion (~10s, saves tokens vs. reacting to false positives).

5. **LSP setup**: TypeScript and Pyright run via global plugins (`typescript-lsp@claude-plugins-official`, `pyright-lsp@claude-plugins-official`). Only `ruff` is configured at project level. Do not add duplicate `lspServers` entries for languages already covered by global plugins.
