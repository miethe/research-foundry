# M3 pre-gate review — TERRA

**Overall verdict:** 0 BLOCKING, 0 HIGH, 1 MED, and 2 LOW findings. The `job.status` dispatch correction is signature-safe for all currently registered adapters, and the receipt/H3 matrices use real durable-store reads rather than mock echoes. The M3 delta is not ready to claim a clean pre-gate without addressing the newly doubled policy probe or explicitly accepting it.

## Findings

### TERRA-M3-1 — MED — `swarm.start` now runs the mutating audit-health probe twice before every successful execution

- **File / line:** `src/research_foundry/services/operator_mcp_adapters/swarm_start.py:463`; `src/research_foundry/services/operator_mcp_adapters/base.py:271`
- **Failure scenario:** The new early `evaluate_policy()` is needed to make a missing run and a foreign run converge at RBAC, but a successful request then enters `base.run_pipeline()`, whose authorization path evaluates policy again before consuming the confirmation. `audit_health` performs a live SQLite write/read/delete probe on each evaluation. Thus every successful `swarm.start` has two probes instead of the prior one, and a transient database lock or audit-store failure between them can turn an otherwise authorized request into `audit_unhealthy`; an authorized malformed-run request now also performs a probe before returning its local precondition denial. The early pass does **not** consume a confirmation, so this is not a double-consumption bug.
- **Suggested fix direction:** Separate the non-mutating identity/workspace ordering gate from the full policy evaluation, or extend the pipeline with a safely carried pre-authorization result so the complete policy/audit-health pass happens once immediately before consumption.

### TERRA-M3-2 — LOW — the new `swarm.start` isolation test has no same-workspace server-route positive control

- **File / line:** `tests/integration/test_operator_mcp_workspace_isolation.py:360`
- **Failure scenario:** The test proves foreign and missing runs produce the same denial, and it will catch restoration of the specific former F6 ordering. But it also passes if a regression makes every server-routed `swarm.start` resolve its target workspace as missing (or otherwise deny all calls as `not_found`). The file’s only same-workspace positive control is for `job.status` at lines 330–341; the separate `swarm.start` unit test does not prove the registered server route succeeds.
- **Suggested fix direction:** Add an own-workspace `server.call_tool("swarm.start", ...)` test with a valid confirmation and `adapter_ids: []` (or a deterministic adapter), asserting a non-error completed result.

### TERRA-M3-3 — LOW — architecture documentation overstates server-side ownership resolution

- **File / line:** `docs/dev/architecture/operator-mcp-governance.md:49-52`
- **Failure scenario:** The document says every target’s owning workspace is resolved server-side. `external_report.import` is an exception: its `import_packet` target’s `resolved_target_workspaces` entry is the caller-supplied `workspace_id`; RBAC validates that declaration against the configured operator, while only an optional `target_run_id` is resolved from disk. Treating the statement as universal can lead implementers to assume all target ownership has an authoritative object lookup when this import target intentionally does not.
- **Suggested fix direction:** Qualify the claim: adapters resolve ownership from canonical state where a target has an owner record; staging-only import packets bind and validate the declared workspace against the configured local operator.

## Review notes

- `server.py` dispatch: inspected the real `invoke*` signatures for all 13 registered operation kinds. Every current sibling accepts `confirmation_record` and `presented_token`; only `job.status` accepts neither, exactly matching `CONFIRMATION_NOT_REQUIRED_KINDS`. No current sibling parameter is silently dropped.
- `swarm_start.py` ordering: success-path values, confirmation binding, and consumption remain in `base.run_pipeline`; the new first pass does not consume a confirmation or skip the later authorization check.
- Test-vacuity checks: the zero-effect matrix hashes the workspace tree and enumerates audit events, with an explicit audit-health positive control. The receipt-schema sweep is live-schema-driven. H3 convergence reads `effect_receipts` and receipt counts from SQLite, and the interrupted-operation fixture’s `expected` values are used in those assertions. `workspaces.json` is load-bearing for H3 identity resolution; its illustrative `runs` and `sources` entries are currently unused.
- Validation: `./.venv/bin/python -m pytest -q tests/integration/test_operator_mcp_workspace_isolation.py tests/unit/test_operator_mcp_adapter_swarm_start.py tests/unit/test_operator_mcp_schemas.py tests/unit/test_operator_operation_service.py -k 'h3 or workspace or swarm or receipt or schema'` — 172 passed. `./.venv/bin/python -m pytest -q tests/unit/test_operator_mcp_policy.py` — 133 passed. Both runs used the requested `/tmp/opm-m3-pytest.lock` protocol.
