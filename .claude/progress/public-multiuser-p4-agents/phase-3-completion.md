## Phase P4.3 Completion Note

**Status**: PASS
**Validator verdict**: PASS — all 8 integration tests pass offline, acceptance criteria met, Gate #2 constraint enforced throughout.
**Isolation**: shared (branch: feat/public-multiuser-p4-agents)

### Files Changed

- `src/research_foundry/adapters/claude_agent_sdk.py` — promoted from degraded-only stub to dual-mode: real path via injected `sdk_client` (or importable SDK), degraded path preserved intact; `MockSDKClient` test double exported; guarded `import claude_agent_sdk` with `try/except`; no env-var credential reads anywhere in this file
- `src/research_foundry/services/agent_providers/claude_agent_sdk_provider.py` — **new file**; `ClaudeAgentSDKProvider` implements all 5 `ResearchAgentProvider` methods; injectable `credential_bytes_factory` (defaults to `b"test-mock-key-stub"`); all writes routed through `AgentJobService._safe_write_json` → `redact_payload` chokepoint; self-registers at module import; appended to `agent_providers/__init__.py` re-exports
- `src/research_foundry/services/agent_job_service.py` — added `_TOOL_CATALOG` (module-level descriptor map for `search`/`fetch`/`source_card`), `AgentJobService.build_job_brief()` (composes existing services; no search logic duplicated), `AgentJobService.run_job_tool()` (dispatches to `run_search`/`extract_urls`/`create_source_card`; enforces `allowed_tools` policy gate; output passes through `redact_payload`)
- `src/research_foundry/services/search_router/router.py` — **untouched** (already callable from job context)
- `src/research_foundry/services/source_cards.py` — **untouched** (already callable from job context)
- `tests/integration/test_agent_job_e2e_claude.py` — **new file**; 8 integration tests covering full lifecycle; all offline with mock credentials; Gate #2 non-approval logged at file top

### Batch Summary

| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | ADP-3.1 | completed | python-backend-engineer |
| 2 | ADP-3.2 | completed | python-backend-engineer |
| 3 | ADP-3.3 | completed | python-backend-engineer |

### Commit References

| Commit | Task | Description |
|--------|------|-------------|
| `8d70488` | ADP-3.1 | feat(p4.3/adp-3.1): promote claude_agent_sdk adapter + add ClaudeAgentSDKProvider |
| `34c6a08` | ADP-3.2 | feat(agents): wire search router + source-card tools as job tool stages (ADP-3.2) |
| `fab5928` | ADP-3.3 | test(agents): ADP-3.3 — E2E integration tests for claude_agent_sdk lifecycle |

### Mode-D Gate #2 Status

NOT approved (by design). All P4.3 work uses mock credentials only:
- `MockSDKClient` (no live network)
- `b"test-mock-key-stub"` credential bytes
- Zero `ANTHROPIC_API_KEY` or similar env-var reads in new code
- Gate #2 approval logged in `test_agent_job_e2e_claude.py` preamble comment

The first real-key run is a deferred operational step requiring explicit human approval.

### Known Non-Blocking Gap

`update-field.py` (artifact-tracking CLI) fails on this progress file due to a missing `type` field in the YAML frontmatter (`doc_type` present, `type` absent). The `update-batch.py` and `update-status.py` scripts work correctly. Commit SHAs are documented in this Completion Note. Recommend adding `type: progress` to the progress schema or aliasing `doc_type` in the CLI validator as a follow-up.

### Escalation Reason

N/A — no Mode-D triggers encountered beyond the pre-declared Gate #2 constraint.

### Follow-Up Recommendations

1. **Gate #2 approval** — when a human approves the first real-key run, update `_make_sdk_client()` in `claude_agent_sdk.py` with actual SDK construction (auth, base URL). `MockSDKClient` can be retired at that point.
2. **`provider.start_job()` path** — currently tests bypass `start_job()` via `command_override` on `svc.spawn_job()`. Once the real `sdk_runner` module exists (P4.4), add a test that calls `provider.start_job()` end-to-end.
3. **`update-field.py` schema gap** — add `type: progress` field or alias to unblock `commit_refs` appending via CLI.
4. **P4.4 is ready to begin** — all P4.3 acceptance criteria satisfied; the subprocess/isolation/tool-wiring foundation is in place for the agent-job API layer.
