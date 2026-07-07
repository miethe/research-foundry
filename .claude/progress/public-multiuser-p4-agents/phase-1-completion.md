## Phase P4.1 Completion Note

**Status**: PASS
**Validator verdict**: PASS — all 8 acceptance criteria verified; 28 tests passing; flake8 clean on all changed files.
**Isolation**: shared
**Branch**: feat/public-multiuser-p4-agents
**Commits**: `ba53bf8` (agent_job_schemas.py + tests), `ec9fac7` (agent_providers/, paths.py, progress file)

### Files Changed

- `src/research_foundry/services/agent_providers/base.py` — new file: `ResearchAgentProvider` `@runtime_checkable` Protocol (5 methods: start_job, stream_events, cancel_job, list_artifacts, accept_artifacts), `BaseProvider` convenience base, `register`/`get_provider`/`all_providers` registry mirroring `adapters/base.py`
- `src/research_foundry/services/agent_providers/__init__.py` — new file: package init with re-exports
- `src/research_foundry/services/agent_job_schemas.py` — new file: `AgentJobStatus` (7-value str enum), `AgentJob` frozen dataclass (19 fields, to_dict/from_dict, validate_agent_job), 5 child record dataclasses (`AgentJobEvent`, `AgentJobArtifact`, `AgentJobToolCall`, `AgentJobApproval`, `AgentJobAcceptance`), `AgentJobStage` (8-value enum), `LEGAL_TRANSITIONS` dict, `validate_transition()` function
- `src/research_foundry/paths.py` — added `agent_jobs` property + `agent_job_dir(id)` method to `FoundryPaths`; resolves under `<root>/agent_jobs/` (NOT `.rf_cache/`) per OQ-B
- `tests/unit/test_agent_job_schemas.py` — new file: 28 tests covering all 6 record round-trips, registry isinstance, validate_agent_job, FoundryPaths.agent_job_dir location guard, state machine (10 legal + 39 illegal transition pairs, 3 terminal states)
- `.claude/progress/public-multiuser-p4-agents/phase-1-progress.md` — progress tracking file for this phase
- `docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md` — plan status updated: draft → in_progress

### Batch Summary

| Batch | Tasks | Status | Agent |
|-------|-------|--------|-------|
| 1 | JOB-1.1 | completed | backend-architect |
| 2 | JOB-1.2 | completed | python-backend-engineer |
| 3 | JOB-1.3 | completed | python-backend-engineer |
| 4 | JOB-1.4 | completed | backend-architect |

### Phase Exit Gate Verification

- [x] Schema fixtures for all 6 record types committed and validated
- [x] Registry round-trip (register→get→list) unit-tested
- [x] State machine transition matrix unit-tested (10 legal edges, 39 illegal pairs, 3 terminal states)
- [x] No provider implementation exists — `agent_providers/` contains only `base.py` + `__init__.py`
- [x] `task-completion-validator` review: PASS

### Escalation Reason

N/A — no Mode-D triggers encountered. P4.2 (credential isolation / subprocess spawn) is explicitly blocked behind Mode-D Gate #1; this phase made no attempt to begin it.

### Follow-Up Recommendations

1. **Mode-D Gate #1** must be logged (who approved, when, what was reviewed) before any P4.2 task begins. See `phase-1-2-foundations.md` §"Mode-D Gate #1".
2. The `agent_job_schemas.py` `policy_snapshot` field stores `allowed_tools` and `data_scopes` but has no enforcement yet — consumed by the frontend in P4.5 (UI-5.7 per phase file note on AC-4.5).
3. `validate_agent_job` checks required fields and `policy_snapshot` keys; stricter enum validation for `status` is already present via `AgentJobStatus`.
