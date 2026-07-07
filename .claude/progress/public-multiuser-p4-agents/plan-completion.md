# Plan Completion Report — Public Multi-User P4 (Embedded Agent Research)

- **Plan**: `docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md`
- **Tier**: 3 (24 pts) · **Branch**: `feat/public-multiuser-p4-agents` (37 commits) · **Completed**: 2026-07-07
- **Execution**: wave-driven phase-owner orchestration (`/dev:execute-plan`), Opus orchestrating; MUST-stay-Claude implementers + Codex read-only adversarial review.

## Wave Summary

| Wave | Phase(s) | Isolation | Reviewer verdict |
|------|----------|-----------|------------------|
| 1 | P4.1 job model + provider port | shared | task-completion-validator ✅ |
| — | **Mode-D Gate #1** (subprocess/credential code) | — | **approved (nick, 2026-07-07)** |
| 2 | P4.2 credential isolation + firewall | worktree → merged | validator ✅ + karen ✅ |
| 3 | P4.3 claude_agent_sdk e2e (mock only) | shared | validator ✅ |
| 4 | P4.4 agent-job APIs + P4.5 frontend `/agents` (serialized on shared branch for git-safety + contract fidelity) | shared | validator ✅ (both) + karen ✅ (P4.5) |
| 5 | P4.6 openai_agents adapter | shared | validator ✅ |
| 6 | P4.7 tests/benchmark/docs/CLI | shared | validator ✅ + karen ✅ |
| R1–R3 | Firewall hardening from Codex adversarial review | shared | see below |

## Codex Adversarial Firewall Review (VAL-7.2)

Three read-only `codex exec` rounds on the credential firewall:
- **v1** (pre-hardening): 5 HIGH + 1 MED credential-leak findings.
- **v2**: confirmed #2 (config patterns), #3 (artifact_id filename), #4 (exception logging) CLOSED; found residuals + 2 new adapter-specific vectors.
- **v3**: confirmed A–D CLOSED; 2 further credible residuals (tuple dict keys already partial; sweeper wired) closed in R3.

Remediation rounds (all MUST-stay-Claude, each with named regression tests):
- **R1** (`ca966b7`): thread `governance.yaml` `secret_patterns` into all agent-job redaction call sites (HIGH #2).
- **Gate #4 / MED #6** (`87991c9`): loud warning on missing `RF_KEY_PROFILE_PEPPER` (fail-closed deferred to P5).
- **R2** (`bf2b675`): tuple/dict-key redaction, crash-orphan sweeper wiring, OpenAI exception redaction, launch-response redaction.
- **R3** (`4cfaf53`): credential-safe artifact filenames (`_safe_artifact_stem` hashing), source-card `tool_input` redacted pre-write.

## Mode-D Gates

| Gate | Status | Note |
|------|--------|------|
| #1 subprocess/credential code | ✅ approved (nick, 2026-07-07) | logged in plan frontmatter |
| #2 first run with REAL provider keys | ⏳ DEFERRED (operational) | automated tests use mock/synthetic providers; needs real keys + human observation post-merge |
| #3 redaction verified on REAL agent-job trace | ⏳ DEFERRED (operational) | structurally downstream of #2; 1 skipped test is the placeholder |
| #4 pepper storage location | ✅ approved (nick, 2026-07-07) | Option A (env via foundry.yaml key-profile) pre-P5; Option B (OS keyring) required before non-loopback |

## Validation

- **154 passed, 1 skipped** (Gate-3 real-trace placeholder), 0 failures across the full agent-job suite at HEAD `4cfaf53`.
- Frontend (P4.5): 853/853 tests, build clean, lint 0 warnings.
- Spawn-latency FU-1: p50≈1.6ms / p99≈3.7ms → **GO** (subprocess design viable; no in-process fallback).

## Final Reviewer Gate

**karen (Tier 3 end-of-feature): APPROVED** for disabled-by-default merge to main. Independently verified credential boundary (temp-file→`Popen(env={})`, redaction completeness, exit-7 accept-only, loopback gating).

## Deferred to P5 (NOT merge-blockers — feature ships `agents.enabled=false` + loopback-only)

1. Gate #2 (real-key run) + Gate #3 (real-trace redaction verification) — operational.
2. Real SDK runner (`research_foundry/agents/sdk_runner`) is a fail-closed placeholder.
3. Auth/RBAC enforcement + workspace isolation (D12; nullable `workspace_id`/`created_by` carried unenforced).
4. **karen follow-up #1 (LOW)**: redact guard-rejection HTTP `detail` (echoes `provider`/`targets` metadata — not credentials) for defense-in-depth symmetry.
5. **karen follow-up #2 (LOW)**: redact `accepted_by` in accept response/log for symmetry when auth lands.
6. Pepper fail-closed enforcement (currently warns); selective `artifact_ids`; Playwright e2e.

## Release Constraint (hard)

`agents.enabled=true` permitted only in loopback/single-operator mode pre-P5. `openai_agents` (SPIKE G3 live tool-loop) must not be enabled for any multi-user-reachable deployment until P5.2 (RBAC) + P5.3 (workspace isolation) are both sealed.
