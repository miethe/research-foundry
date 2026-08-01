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

# M3 implementer contract — one exact tree satisfies AC OPM-1..7

Branch `worktree-operator-mcp-v1` @ `a4e320e` (M2 close, pushed, PR #7). Milestone M3 (supersedes
P6, 4 pts, context class C4). Plan authority:
`docs/project_plans/implementation_plans/enhancements/research-foundry-operator-mcp-v1.md` —
sections "### M3", "AC -> command -> evidence", "Implementer Defect-Class Checklist", "Field Notes",
"Named risks". Progress artifact: `.claude/progress/research-foundry-operator-mcp/phase-6-progress.md`.

## Decisions (D1–D8)

- **D1 — Leg split by file ownership.** Leg A owns `tests/unit/test_operator_mcp_policy.py`,
  `tests/unit/test_operator_mcp_schemas.py`, NEW `tests/integration/test_operator_mcp_workspace_isolation.py`.
  Leg B owns `tests/unit/test_operator_operation_service.py`,
  `tests/unit/test_operator_mcp_adapter_job_lifecycle.py`, NEW fixture assets under
  `tests/fixtures/operator_mcp/`. Leg C is **read-only** (report only). Leg D owns
  `docs/user/`, `docs/dev/architecture/`, `README.md`, `CHANGELOG.md`,
  `docs/project_plans/design-specs/`. No leg touches another leg's files; the orchestrator is the
  only committer.
- **D2 — Zero-effect assertion is structural, not nominal.** Every adversarial case asserts BOTH
  the typed denial AND that no manifest / receipt / job / attempt / store row / filesystem artifact
  was produced — snapshot the durable stores before the attempt and diff after. "Raises the right
  error" alone does not satisfy AC OPM-1.
- **D3 — Receipt schema attack is per-property.** For every property in
  `schemas/operator_mcp_receipt.schema.yaml`: wrong type, out-of-enum value, missing-required,
  additional-property injection, and (where string) oversize/control-char payloads. A golden
  instance pass is explicitly NOT acceptance (Named Risks).
- **D4 — Two-workspace fixtures are public-safe.** Synthetic workspace ids/names, synthetic run
  and source data. Grep-clean for owner strings (`miethe`, real run ids, LAN addresses, tokens).
- **D5 — Wrong-workspace = safe non-existence.** The error envelope for a wrong-workspace target
  must be byte-comparable to the true-missing envelope (same code, same message shape, no
  timing/detail channel asserting existence). Test both directions across two identities.
- **D6 — Interrupted-operation convergence.** For each interruption point in the H3 matrix, the
  resumed run's canonical effects (refs, receipts, effect counts) must equal the uninterrupted
  run's — assert set-equality on canonical refs, not just terminal status.
- **D7 — RESOLVED pre-dispatch (orchestrator measurement error, not a flake).** The observed
  failure of `test_job_resume_wrong_workspace_indistinguishable_from_missing_dry_run` reproduces
  M2's documented O-7 mechanism exactly: two pytest invocations running **concurrently in the same
  worktree** pollute each other through shared run/ccdash state. The orchestrator's first recon
  batch ran two suites in parallel — self-inflicted. No Leg B action. Standing rule for ALL M3
  legs: **never run two pytest invocations concurrently in this worktree.** Wrap every pytest run
  in the mkdir lock: `while ! mkdir /tmp/opm-m3-pytest.lock 2>/dev/null; do sleep 5; done` …run…
  `rmdir /tmp/opm-m3-pytest.lock` (mkdir is the portable atomic primitive on Darwin; there is no
  flock(1) here).
- **D8 — Docs claim only what the tree shows.** Tool inventory in docs is generated/verified
  against the server registry (14 tools). Remote transport and live writeback are labeled
  `deferred`; owner qualification `not_executed_owner_data_absent`. Link Knowledge MCP / RPC / ERI /
  CARP / RAL / RFUP / Search Router docs; do not restate their authority contracts.

## Defect-Class Checklist (verbatim, mandatory in every leg)

1. **No fail-open defaults.** No permissive default on a security-relevant field, no
   `None`-means-skip, no unknown-label fallback that grants rather than denies. Check the
   *producer* of a value, not just the field.
2. **Fix the layer below.** After hardening a symbol, enumerate its delegates, callers, and
   siblings in `__all__` and ask whether reaching for any of them yields the unsafe behavior.
3. **Never pin unsafe behavior with a test.** If a test asserts current behavior and the current
   behavior is wrong, the test is wrong — say so and invert it.
4. **Never fabricate a validation transcript.** Paste real output or report the failure.

## Leg scopes

### Leg A — adversarial matrices (claude-primary, Sonnet 5, xhigh)

- **OPM-6.2 (AC OPM-1)**: confirmation adversarial matrix covering missing identity, denial,
  expiry, replay, wrong actor, wrong workspace, payload drift, target drift, policy drift,
  sensitivity drift, atomic token consumption — each with D2 zero-effect assertions. Extend
  `tests/unit/test_operator_mcp_policy.py`; audit existing cases and upgrade any that assert only
  the error.
- **OPM-6.3 (AC OPM-2)**: NEW `tests/integration/test_operator_mcp_workspace_isolation.py` —
  two-identity/two-workspace matrix per D4/D5, driven through the registered server route
  (`server.call_tool`), not hand-built PolicyContexts (M2 O-5 lesson: the E2E seam is where the
  defects hid).
- **Receipt schema re-attack** per D3 in `tests/unit/test_operator_mcp_schemas.py`.

### Leg B — lifecycle + fixtures (claude-primary, Sonnet 5, high)

- **OPM-6.1**: integrated fixture matrix under `tests/fixtures/operator_mcp/` — two-workspace
  public-safe fixtures + interrupted-operation fixtures, each with an expected-receipts/effects
  manifest consumed by tests.
- **OPM-6.4 (AC OPM-3)**: H3 ten-scenario lifecycle recovery matrix in
  `tests/unit/test_operator_operation_service.py` — interrupted/uninterrupted convergence per D6;
  exact-retry idempotency; cancel; resume; duplicate suppression.
- (D7 removed from scope — resolved pre-dispatch as orchestrator measurement error; see D7.)

### Leg C — evidence reconciliation (ICA, read-only)

For every row of the plan's "AC -> command -> evidence" matrix: verify the named files exist, run
`--collect-only -q` for every `-k` filter, record selected counts + names, flag vacuous filters
(0 selected, or a load-bearing term missing — the VAL-1 class), flag AC paths not covered by any
existing test. Verify the closed-dispatch `rg` scan hits are comments/docstrings only (report
line-level classification). Output: `.claude/worknotes/research-foundry-operator-mcp/m3-evidence-reconciliation.md`.
NO code edits.

### Leg D — docs (Codex gpt-5.6-terra, workspace-write)

Per plan "Documentation Finalization": `docs/user/research-foundry-operator-mcp.md`,
`docs/dev/architecture/operator-mcp-governance.md`, `README.md` pointer (one short subsection max),
`CHANGELOG.md` `[Unreleased]`, and two deferred shaping specs
`docs/project_plans/design-specs/operator-mcp-remote-transport-shaping.md` +
`docs/project_plans/design-specs/operator-mcp-live-writeback-shaping.md`. D8 governs claims.
Read `src/research_foundry/operator_mcp/server.py` for the real inventory; read
`schemas/operator_mcp_*.schema.yaml` for receipt/error interpretation.

## Gates (revised gate structure — authoritative)

Pre-gate: two diverse cheap lenses (terra + ICA, code-review framing) on the M3 delta. Then
validator (fresh context) on the milestone. Then **Karen on the final exact tree only**. Gate
budget: 2 re-passes per scope × lens; mutation-verify inside the fix step; fix loops continue the
implementer session. A material change after evidence capture invalidates and re-runs the matrix.
