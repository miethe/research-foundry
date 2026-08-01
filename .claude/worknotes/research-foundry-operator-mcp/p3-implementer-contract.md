# P3 Implementer Contract — read this in full before your first edit

Applies to every implementer dispatched for Operator MCP Phase 3 (OPM-3.1 … OPM-3.4 and the
carried P2 obligations NB-D and P2S-NB-9). Written 2026-07-30 on branch `worktree-operator-mcp-v1`.

## 0. Where you are

- Repo root / cwd: `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1`
- Branch: `worktree-operator-mcp-v1`. **Do not commit.** The orchestrator is the single committer.
- Plan: `docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md`
  (section "Phase P3: Run Planning and Swarm Adapters").
- Findings ledger: `.claude/findings/research-foundry-operator-mcp-findings.md`.
- Progress: `.claude/progress/research-foundry-operator-mcp/phase-3-progress.md`.

## 1. Mandatory defect-class checklist (verbatim from the plan — apply to every line you write)

1. **No fail-open defaults.** No permissive default on a security-relevant field, no
   `None`-means-skip, no unknown-label fallback that grants rather than denies. Check the
   *producer* of a value, not just the field — NEW-4 survived round 1 because the field default was
   removed while the function producing it still returned `"public"`.
2. **Fix the layer below.** After hardening a symbol, enumerate its delegates, callers, and
   siblings in `__all__` and ask whether reaching for any of them yields the unsafe behavior. This
   is what found the critical defect in round 2: the fix hardened `authorize_operation` while its
   delegate `verify_confirmation` still reported the replay as an accept, and the new docstring
   steered callers to the weaker door.
3. **Never pin unsafe behavior with a test.** If a test asserts current behavior and the current
   behavior is wrong, the test is wrong — say so and invert it. Three round-2 defects were pinned
   as correct by tests the fix cycle itself wrote.
4. **Never fabricate a validation transcript.** Paste real output or report the failure. A
   fabricated transcript was caught in round 1.

## 2. The P2 process change — mutation-verify INSIDE your own step

**This is the highest-leverage rule in this document.** Rounds 4 and 5 of the P1 gate exist almost
entirely because closure was asserted rather than demonstrated: a correct fix shipped with four
purpose-built tests, **all four of which passed on revert**.

For every behavioral guard you add, before you report done:

1. Revert the guard in place (comment it out / invert the condition).
2. Run the **named** test that is supposed to cover it. It MUST fail.
3. Restore the guard. Re-run. It MUST pass.
4. Record the mutation, the named test, pre/mutant exit codes, and `RESTORED` in your report.

**`__pycache__` false-green trap (verified real in this repo):** successive mutations that share a
file-size delta make CPython reuse a stale `.pyc`, so the mutant silently tests the *old* bytecode
and reports a false green. On **every** iteration:

```bash
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
export PYTHONDONTWRITEBYTECODE=1
```

**Non-redundancy cross-check:** if a behavior is guarded by two separate clauses, verify each
mutation fails *only its own* test. Two tests that both fail on either mutation are one test.

## 3. Running tests

There is **no `.venv` in this worktree**. Use the main checkout's interpreter, invoked with the
worktree as cwd:

```bash
PYTHONDONTWRITEBYTECODE=1 \
  /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest <args> -q
```

- Do **not** use the pyenv shim — it gives `No module named research_foundry`.
- Do **not** add a `PYTHONPATH=$PWD/src` prefix. `pyproject.toml` sets
  `[tool.pytest.ini_options] pythonpath = ["src"]`, which pytest inserts **ahead of** the
  `PYTHONPATH` env var. Any such prefix is decorative and is **not** evidence of an isolated run.
  If you ever need a scratch-tree run, the correct form is
  `--override-ini="pythonpath=<scratch>/src"`.
- This repo's pytest config **suppresses the "N passed" summary line**. Trust the exit code.
  Capture it explicitly: `... -q > out.txt 2>&1; echo "REALEXIT=$?"`.
- `FAILED` lines carry ANSI colour codes — `grep "^FAILED"` returns 0 hits on a red suite. Use
  `grep -a "FAILED"` or strip ANSI first.

**Baseline established 2026-07-30 on this tree** (all 7 operator suites): `REALEXIT=0`, 376 dots,
0 F, 0 E. Reproduce this before your first edit.

**Pre-existing, DO NOT CHASE**: `tests/test_verification_pediatric_cds.py` and
`tests/test_verification_seam001_gate_composition.py` fail to *collect* under `-k` filtering
(sibling `import test_claim_verifier`). Present on base `65d658d`.

Lint gate for touched Python: `flake8 <file> --select=E9,F63,F7,F82` must exit 0.

## 4. Architecture facts you must not re-derive

Verified 2026-07-30 by exploration; trust these:

| Thing | Where |
|---|---|
| Frozen operation kinds + tool names | `services/operator_mcp_policy.py` — `OPERATION_KINDS`, `TOOL_NAMES`, `__all__` at `:403` |
| P3's five kinds | `run.plan`, `swarm.start`, `job.status`, `job.cancel`, `job.resume` |
| Only kind needing **no** confirmation | `job.status` (`CONFIRMATION_NOT_REQUIRED_KINDS`) |
| Identity type | `research_foundry/auth_identity.py:29` — `AuthIdentity(user_id, workspace_id, roles)`; deliberately import-clean of `starlette` so Operator MCP works without the `[serve]` extra |
| Structural identity derivation | `operator_mcp_policy.resolve_operator_identity` — **the only** legitimate source. A caller-supplied identity is finding NEW-18 and is forbidden. |
| Authorization entry | `authorize_operation(ctx, *, confirmation_record, presented_token, paths=None, now=None)` at `:1560` |
| Durable operation creation | `OperatorOperationService.consume_and_create_operation(...)` at `operator_operation_service.py:1011` |
| Action execution | `OperatorCancelResumeService.run_or_replay(...)` `:876`, `run_actions(...)` `:479` |
| Receipts | `OperatorReceiptService.record_action_receipt:314`, `record_effect_receipt:506`, `write_checkpoint:683`, `finalize_terminal_receipt:1035` |
| Bounded error envelope | `operator_mcp_policy.build_error` at `:2111` — every failure returned to a caller goes through this. Raw `str(exc)` / tracebacks are finding NEW-21. |
| Discovery adapter registry | `adapters/base.py` — `_REGISTRY:101`, `register:104`, `get_adapter:111`, `all_adapters:115` |
| `planning.plan_run` | `services/planning.py:565` — already takes `identity: AuthIdentity \| None` and CARP `retrieval_policy`/`retrieval_limits`; returns `PlanResult` (`:428`) |
| Swarm CLI logic to extract | `cli_commands.py` `swarm_run` at `:738-791` |
| Already service-backed (leave alone) | `swarm drive` → `services/swarm_drive.py` |
| AgentJob service | `services/agent_job_service.py` — `load_events:1068` (unbounded full-file read), `list_staged_artifacts:1037` (unbounded glob) |

**There is no Operator MCP tool-registration/dispatch server yet.** That is P5. P3 builds the
adapter *functions* the P5 server will later register — do not build a server, a Typer command, or
an MCP transport in this phase.

## 5. Hard prohibitions for P3

- Tool adapters MUST invoke **no** CLI / Typer / `subprocess` path (plan quality gate).
- No new provider, router policy, or discovery adapter (Search Router owns that).
- No knowledge/read-only resources (Knowledge MCP owns those).
- Mode D — auth, payments, schema migrations, data deletion, secret rotation, infrastructure —
  **STOP and report**. Do not edit.
- Do not touch files outside your assigned ownership list. If your task genuinely requires a change
  in another leg's file, **report the required change; do not make it**.
- Do not `git add` / `git commit` / `git push` / `git stash`.

## 6. What to report back

1. Files created/modified (paths only).
2. The mutation matrix from §2 — real pre/mutant exit codes, named tests, `RESTORED`.
3. Real pasted test output with `REALEXIT=`.
4. Every judgment call you made and why.
5. Anything you could **not** do, and why. Deviations get logged, not silently dropped —
   if you made a conservative choice, say so explicitly.
