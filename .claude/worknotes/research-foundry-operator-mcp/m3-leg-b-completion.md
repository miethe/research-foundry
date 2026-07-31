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

# M3 Leg B completion — lifecycle recovery + fixtures

Branch `worktree-operator-mcp-v1`. Scope: OPM-6.1 (fixture matrix) + OPM-6.4 / AC OPM-3 (H3
ten-scenario lifecycle recovery matrix), per
`.claude/worknotes/research-foundry-operator-mcp/m3-implementer-contract.md` Leg B.

## What changed

- **NEW** `tests/fixtures/operator_mcp/workspaces.json` — public-safe two-workspace fixture
  (2 synthetic workspaces/identities, 2 synthetic runs, 2 synthetic sources; all ids/urls
  fixture-only).
- **NEW** `tests/fixtures/operator_mcp/interrupted_operations.json` — the H3-01..H3-10 scenario
  matrix: each scenario declares `workspace_id`, `actions` (action_id/effect_kind/effect_ref),
  `interruption_point`, and an `expected` block (effect_pairs, action_receipt_count,
  effect_receipt_count, terminal_status) that is the acceptance oracle the tests assert against.
- **EXTENDED** `tests/unit/test_operator_operation_service.py` (audited existing 34 tests first —
  DUR-1/confirmation-layer coverage only, zero H3/lifecycle-recovery tests present; extended, did
  not duplicate):
  - New imports: `hashlib`, `re`, `AuthIdentity`, `OperatorAttemptAdapter`,
    `operator_cancel_resume_service.{ActionEffect, ActionSpec, OperatorCancelResumeService}`,
    `OperatorReceiptService`.
  - Fixture loader helpers (`_scenario`, `_fixture_identity`, `_fixture_actions`), convergence
    helpers (`_canonical_effects`, `_action_receipt_count`, `_effect_receipt_count`,
    `_normalize_terminal_receipt`, `_assert_scenario_convergence`), and `_consume_op`.
  - `test_operator_mcp_fixtures_are_grep_clean_of_owner_or_private_data` — pins D4 as a property
    (substring + private-IPv4-regex scan over every file under `tests/fixtures/operator_mcp/`).
  - 10 scenario tests, `test_h3_01_*` .. `test_h3_10_*` (see table below).
- Touched no file outside Leg B's ownership (`test_operator_operation_service.py`,
  `test_operator_mcp_adapter_job_lifecycle.py` [read-only for this leg — audited, not edited; its
  existing coverage of `job.resume` after a terminal cancel was corroborating evidence, not a gap],
  new fixtures under `tests/fixtures/operator_mcp/`). No git commands run.

## H3 scenario table (scenario × convergence assertion)

| Scenario | Interruption point / property | Convergence assertion |
|---|---|---|
| H3-01 | After manifest write, before `run_actions` ever runs | Fresh instance resumes at index 0; SET-equal canonical effects + receipt counts vs. an uninterrupted twin |
| H3-02 | Mid-attempt (attempt minted, zero receipts committed under it) | Resume mints a NEW `attempt_id` (never reuses/resurrects the stale one); SET-equal effects vs. twin; both attempts remain durably linked |
| H3-03 | After an `effect_receipt`, before the following checkpoint | `resolve_resume_point` reconstructs from real rows (not checkpoint); action 0 is asserted to never re-run (raises if invoked); SET-equal effects vs. twin |
| H3-04 | After every action's receipts + checkpoint, before `finalize_terminal_receipt` | `run_or_replay` finalizes the SAME terminal receipt an uninterrupted run would, zero re-execution of any action |
| H3-05 | During cancel (request + action 0's receipts committed, CANCELED checkpoint/terminal lost) | Fresh instance observes durable cancellation at the resumed safe point; finalizes `canceled` with exactly 1 completed action; SET-equal effects vs. a control run canceled mid-flight |
| H3-06 | Exact-retry idempotency (`run_or_replay(is_replay=True)`) | Identical terminal receipt, zero re-execution, action/effect-receipt counts unchanged |
| H3-07 | Cancel before the first action | `canceled`, zero completed actions — explicit D2 zero-effect assertion (`_canonical_effects == set()`) |
| H3-08 | Resume-after-cancel refusal | `resume_operation` → `ResumeOutcome.outcome == "already_terminal"`, `new_attempt is None`, `execution is None`, returns the exact canceled receipt, zero new attempts/receipts |
| H3-09 | Duplicate suppression (fresh confirmation, same idempotency_key+digest) | `consume_and_create_operation` → `exact_replay` against the SAME `operation_id`; `operations` row count stays 1 throughout; zero duplicate action/effect receipts |
| H3-10 | Full D6 convergence (5 actions, interrupted after action 2's effect receipt) | SET-equal canonical effects, equal receipt counts, and an identical normalized terminal receipt between control and interrupted+resumed runs |

Every test drives the real public entry surface (`consume_and_create_operation`,
`OperatorCancelResumeService.run_actions` / `run_or_replay` / `resume_operation`,
`OperatorAttemptAdapter.create_attempt`) against real sqlite persistence (`tmp_foundry`); process
loss is simulated by durably writing pre-loss receipts via one service instance, then
resolving/resuming via brand-new service instances backed by the same files — never an in-process
continuation (mirrors `test_operator_cancel_resume_service.py`'s own proof requirement).

## Fixture inventory

```
tests/fixtures/operator_mcp/
├── workspaces.json              # 2 synthetic workspaces/identities, 2 runs, 2 sources
└── interrupted_operations.json  # H3-01..H3-10 scenario + expected-effects/receipts manifest
```

D4 grep-clean check (own test, `test_operator_mcp_fixtures_are_grep_clean_of_owner_or_private_data`):
scans for `miethe`, `10.42.`, `/users/`, `/home/`, `ghp_`, `sk-ant-`, `sk-proj-`, `bearer `, `akia`,
plus a regex for any private/LAN-shaped IPv4 (10.x / 192.168.x / 172.16-31.x). **Mutation-verified**:
injected `"miethe test workspace"` into `workspaces.json`, confirmed the test fails with the exact
injected string named in the assertion, then restored the file and re-confirmed the full 86-test
run is green again (see Validation below).

## Real command output

Pre-check — collection is clean (no import/syntax errors):
```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_operation_service.py -q --collect-only
tests/unit/test_operator_operation_service.py: 44
```

H3 matrix + fixture grep-clean test, isolated:
```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_operation_service.py -q -k "h3_ or fixtures_are_grep_clean" -v
11 passed, 33 deselected in 1.87s
```

Full validation set (owned files + `test_operator_mcp_adapter_base.py` per the task's VALIDATION
instruction), lock-protected, no color, no cache noise:
```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_operation_service.py \
    tests/unit/test_operator_mcp_adapter_job_lifecycle.py \
    tests/unit/test_operator_mcp_adapter_base.py --color=no -p no:cacheprovider
........................................................................ [ 83%]
..............                                                           [100%]
86 passed in 9.89s
```

Per-file breakdown:
```
test_operator_operation_service.py:        44 passed in 10.26s
test_operator_mcp_adapter_job_lifecycle.py: 31 passed in 7.53s
test_operator_mcp_adapter_base.py:          11 passed in 2.57s
```

Mutation-verify transcript (grep-clean guard, restored afterward):
```
$ python3 -c "... replace 'Fixture Primary Workspace' with 'miethe test workspace' in workspaces.json ..."
$ ./.venv/bin/python -m pytest tests/unit/test_operator_operation_service.py -q -k "fixtures_are_grep_clean" --color=no
FAILED tests/unit/test_operator_operation_service.py::test_operator_mcp_fixtures_are_grep_clean_of_owner_or_private_data
AssertionError: .../tests/fixtures/operator_mcp/workspaces.json: forbidden pattern 'miethe' found
$ cp workspaces.json.bak workspaces.json   # restored
$ ./.venv/bin/python -m pytest ... (the 3-file set above) → 86 passed in 9.89s
```

All pytest invocations ran wrapped in the mandatory mkdir lock
(`/tmp/opm-m3-pytest.lock`), never concurrently with another leg, per D7.

## Product defects found

None. `OperatorCancelResumeService`/`OperatorReceiptService`/`OperatorOperationService` already
carry the full, correct H3 contract from prior milestones (P2/M1/M2); this leg's job was proving it
via a fixture-driven, D6-compliant convergence matrix in the AC-OPM-3-evidencing file, not
remediating a gap. `resume_operation`'s `already_terminal` short-circuit (H3-08) and `run_actions`'
safe-point cancellation check (H3-05/H3-07) both matched their documented contracts on first attempt
— no fix-loop was needed, no test asserts current-but-wrong behavior (defect-class checklist item 3:
n/a, nothing to invert).

## Deviations from the contract

- **`tests/unit/test_operator_mcp_adapter_job_lifecycle.py` was audited, not edited.** The contract
  lists it as Leg B's own file; its existing 31 tests already cover `job.status`/`job.cancel`/
  `job.resume` at the adapter layer (including `test_job_resume_already_terminal_denies_...`, which
  independently corroborates H3-08's service-layer contract). No gap was found there that OPM-6.1/
  OPM-6.4 required filling, so it was left untouched and only re-run for validation, per "audit what
  already exists first — extend, don't duplicate."
- **H3-04 and H3-09 use `run_or_replay` rather than `resume_operation`** (the full fresh-confirmation
  resume path) because both scenarios are specifically about the operation's OWN
  execution/replay contract (finalize-on-restart, idempotency-key dedup), not about the
  `job.resume` MCP-facing surface — `resume_operation` is exercised directly in H3-08 (where the
  resume-after-terminal contract is the point of the scenario) and indirectly via
  `test_operator_mcp_adapter_job_lifecycle.py`'s own coverage.
- Fixture identities are minted fresh per scenario (`AuthIdentity(user_fixture-*, ws-fixture-*,
  ("owner",))`) via `policy.resolve_operator_identity` monkeypatching, rather than reusing
  `test_operator_mcp_policy._IDENTITY` (`"alice"/"ws-mine"`) — keeps the fixture matrix genuinely
  load-bearing for identity resolution, not just action/effect content, per the task's "load-bearing,
  not decorative" instruction.

## Files touched

- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/tests/fixtures/operator_mcp/workspaces.json` (new)
- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/tests/fixtures/operator_mcp/interrupted_operations.json` (new)
- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/tests/unit/test_operator_operation_service.py` (extended)
- `/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/operator-mcp-v1/.claude/worknotes/research-foundry-operator-mcp/m3-leg-b-completion.md` (this file)
