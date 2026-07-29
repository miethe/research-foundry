---
type: report
schema_version: 2
doc_type: report
report_category: plan-completion
prd: research-provenance-continuity
feature_slug: research-provenance-continuity
status: completed
created: 2026-07-29
updated: 2026-07-29
plan_ref: docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
commit_refs:
  - 4e9e0f9
  - 20066d7
  - f0a42bf
pr_refs: []
---

# Plan Completion — C1 Research Provenance Continuity (40 pts, 7 phases)

Executed on branch `worktree-rpc-v1` (worktree `.claude/worktrees/rpc-v1`, base `e76784b`).
Tracker: node_01KY5SH3AD7DX28NPBAFSSP41D. Final gate: **RPC-7.G VERDICT: APPROVED** (Karen-on-Fable, 2026-07-29).

## Per-wave summary

| Wave | Phases | Commit | Isolation | Gate verdicts |
|------|--------|--------|-----------|---------------|
| 1 | P1 contract freeze (split ≤4pt) | `4e9e0f9` | shared worktree, single committer | RPC-1.G APPROVED — validator + **gpt-5.6-sol ×4 rounds** (30 findings SOL-1..30, all closed/ratified) + Karen (19/19 identity vectors; OQ-1/2/3 + §22b bounded limitations ratified) |
| 2 | P2 origin/envelope/activity · P3 report-use · P4 inference/canonical materializers | `20066d7` | parallel lanes, exclusive file ownership | Per-phase validators + **gpt-5.6-terra** audits (16 findings T2-1..T4-4, all fixed) + Karen Wave-2 (re-attacked every terra closure) — RPC-2.G/3.G/4.G APPROVED |
| 3 | P5 projections/read contracts · P6 lifecycle continuity | `f0a42bf` | parallel lanes | Validators (V5-1 no-500 fix) + Karen Wave-3 APPROVED (novel attack found **F19** policy-blocked-yet-citable — fixed in all writer paths) |
| 4 | P7 hardening/docs/AC evidence | (this commit) | single lane | RPC-7.11 validator APPROVED (497-test regression independently re-summed) + **gpt-5.6-sol final pass** (SOL-31..39 → fixed → closure CLOSED) + Karen final: BLOCKED on K-FINAL-1 → surgical fix → re-attack **APPROVED** (658 passed, exit 0) |

## Headline outcomes

- Frozen contract `docs/dev/architecture/research-provenance-contract-freeze.md` (§1–§22c) with worked identity vectors; implementation verified conformant by cross-model gates.
- New services: `provenance_envelope`, `research_run_discovery`, `assertion_report_use`, `assertion_inference`, `canonical_claim_materialization`; extended `assertion_impact`/`assertion_materialization`/`assertion_catalog`/`export_service` (schema 1.8)/`verification` (additive attest→publish hook).
- 4 new schemas + 5 additive schema amendments; OpenAPI insertions-only; runs-viewer codegen extended.
- Reconciliation with shipped C2/C3/C4: all conflicts logged as findings (F1–F19, N1–N7 in `.claude/findings/research-provenance-continuity-findings.md`), never silently overwritten; legacy surfaces preserved (AC RPC-8 spot-checked by sol final pass).
- AC evidence matrix: `.claude/progress/research-provenance-continuity/ac-evidence-map.md` (all 16 gates).
- Docs: dev guide, CHANGELOG entry, 4 deferred-item design specs (validated, linked from plan frontmatter).

## Security/gate highlights (why the gate stack earned its cost)

Validators approved repeatedly while cross-model + Karen gates found real defects: sol 30+9 findings, terra 16, Karen F19 and **K-FINAL-1** (two-call self-attestation minting a verification-pass anchor without reading report bytes — closed by privatizing `_resolve_verification_pass_created_at`, sole public entry `attest_verification_pass`, permanent regression test `test_two_call_self_attestation_through_public_api_is_denied`).

## Deviations & escalations

- No Mode-D edits were made; DI-1 untouched (no deployment flags flipped, no gate self-signing). No pushes.
- Two codex runs killed for stall (sol r3 xhigh, terra wave-2 re-verify); r3 relaunched at `high`, re-verify folded into Karen's empirical gate.
- Two implementer agents used `git stash` against repo rule — stash stack verified clean both times.
- Karen suggested excluding `.claude/worknotes/rpc-terra-*-findings.md` from the landing squash; kept on-branch for gate provenance (operator may strip at landing).

## Accepted bounded limitations / follow-ups

| Item | Disposition |
|---|---|
| §22b items 1–5 (incl. attestation trust boundary = fs-write or module-private access) | Accepted, documented in freeze doc |
| RPC-7.19 capability-flag sub-check | Bounded limitation, documented |
| sol round-1 idempotent re-enumeration residual | Accepted |
| Flat worknote files (`rpc-*-findings.md`) vs ONE-context.md policy | Low hygiene follow-up |
| F19 relevance to future DI-1 re-audit | Flag for DI-1 re-audit scope |
| Worktree/branch removal after squash-merge | Follow-up (session runs inside the worktree) |

## Validation at close

Wave regression suite (14 resolvable files incl. `test_verification_draft.py`): **658 passed, exit 0** (Karen final run, current tree). Known-unrelated pre-existing baseline failures (pediatric-CDS ×2, whole-`tests/` collection break) out of scope.
