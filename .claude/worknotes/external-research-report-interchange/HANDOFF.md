# ERI v1 — Session Handoff

> **✅ CLOSED 2026-07-28.** All NEXT STEPS below were completed in the follow-up session:
> third rebase onto `main` (`1376e85`), R2-#8 closed (`16d60c4` + normalization-aware fix
> `dd5ae1e` after Karen empirically proved the raw-string check bypassable via path aliasing),
> R2-#5 formally deferred as ERI-DF-5, final validator PASS + Karen (Fable 5) APPROVED,
> squash-merged to `main`. See `.claude/progress/external-research-report-interchange/plan-completion.md`
> for the gate record and open-items disposition. This document is retained as history.

> Written 2026-07-27 at branch `worktree-eri-v1` @ `0b4ada5`, 14 commits ahead of `main`
> (`2bf6895`). Prior session ran `/dev:execute-plan` on the External Research Report
> Interchange plan.
>
> ⚠️ **`main` drifted TWICE mid-run** and the branch was rebased both times. SHAs below are
> post-rebase and will change again if you rebase. **Always run
> `git log --oneline $(git merge-base main HEAD)..main` before any squash** — a stale branch
> here would silently revert real work on `main`, including security remediation commits
> (`294a8be` DI-1 delta re-audit, `2bf6895` its F1-F7/G1-G2 remediation).

## TL;DR for the next session

All 6 phases (38 pts) are **implemented, committed, and green**. Two full adversarial audit
rounds have run. What remains is **one final gate + squash to main** — plus deciding what to
do about 4 honestly-open items listed below.

**Do not re-execute any phase.** Everything is on disk and committed.

```bash
cd /Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/eri-v1
git log --oneline main..HEAD          # 13 commits
```

## Validation command (the one that matters)

zsh does NOT word-split unquoted variables — pass the file list literally, not via `$VAR`.

```bash
PYTHONPATH=$PWD/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python \
  -m pytest \
  tests/unit/test_external_research_schemas.py \
  tests/unit/test_external_research_interchange.py \
  tests/unit/test_external_research_profiles.py \
  tests/unit/test_source_acquisition_policy.py \
  tests/unit/test_external_research_cli.py \
  tests/unit/test_external_research_caller_authorization.py \
  tests/integration/test_external_research_resolution.py \
  tests/integration/test_external_research_import.py \
  tests/integration/test_external_research_cross_profile_compat.py \
  tests/integration/test_external_research_adversarial_matrix.py \
  tests/integration/test_external_research_large_report_resume.py \
  tests/test_schema_validation.py -q
```
Last run: **exit 0**. This repo's pytest config suppresses the `N passed` summary line — trust
the **exit code**, not the absence of a summary.

## What was built

`external_research_handoff/v1` — a file-canonical interchange for importing externally-produced
research reports (ChatGPT Deep Research, Perplexity, Gemini, NotebookLM, generic) as
`platform_synthesis` + quarantined assertion candidates, with immutable receipts and resumable
bounded imports.

| Phase | Deliverable | Commit |
|---|---|---|
| P1 | 6 schemas, frozen contract doc, 32 fixtures | `e69105d` |
| P2+P3 | staging/receipts service; 5 producer profiles + injection fixtures | `53d98ef` |
| — | round-1 audit record (contract) | `c03af4d` |
| P1' | contract remediation, 18 findings | `1a1eebd` |
| P2' | hardening: hardlink, lease, safe YAML | `99186e0` |
| — | plan frontmatter / OQ resolution | `a27a9ce` |
| P4 | SSRF-safe acquisition + resolution + promotion | `5cb0ef1`, `9feaa7c` |
| P5 | resumable importer + `rf intake external-report` CLI | `5a70b03` |
| P6 | adversarial matrix, docs, deferred specs, closes audit #9 | `fb93611` |
| — | validator remediation + first rebase onto main | `8022b33` |
| — | round-2 audit record (implementation) | `3423366` |
| — | round-2 remediation | `2112ac1` |
| — | this handoff | `0b4ada5` |

Key files:
- `src/research_foundry/services/source_acquisition_policy.py` — the SSRF gate
- `src/research_foundry/services/external_research_resolution.py` — normalize/resolve/promote
- `src/research_foundry/services/external_research_interchange.py` — staging, receipts, authz, lease
- `src/research_foundry/services/external_research_import.py` — orchestration + resume
- `docs/dev/architecture/external-research-handoff-contract.md` — normative contract
- `templates/external_research_handoff/v1/{generic,chatgpt,perplexity,gemini,notebooklm}/`

## Review history — read before trusting anything

Two adversarial rounds ran because **green tests repeatedly did not mean correct**. Every
material defect in this feature was found by a reviewer, never by a passing suite.

1. **Round 1 (gpt-5.6-sol, contract)** → `.claude/findings/eri-p1-contract-audit-gpt56.md`
   20 findings. CRITICAL: the SSRF gate was *structurally bypassable* — validating then handing
   a URL to RFUP let RFUP open its own connection and re-resolve after a rebind. Fixed: the
   policy layer now owns the whole HTTP lifecycle and passes **bytes**, never the URL.
2. **`task-completion-validator`** → all 7 ACs PASS, no vacuous tests found, but caught that the
   branch was stale and **squash-merging would have silently reverted 3 commits on `main`**
   (`77fe327`, `294a8be` DI-1 delta re-audit, `307a202`). Fixed by rebase.
3. **Round 2 (gpt-5.6-sol, implementation)** → `.claude/findings/eri-implementation-audit-round2-gpt56.md`
   13 findings the validator missed, including a **vacuous injection test** (dry-run only,
   asserting nothing that could fail) and **membership mistaken for permission** (a viewer with
   no permissions passed `authorize_caller()`). 11 closed, 2 partial.

## OPEN ITEMS — do not let these silently close

| # | Item | Status | Why it matters |
|---|---|---|---|
| R2-#5 | Exactly-once effect promotion | **PARTIAL** | Effect resume binds/recomputes and `.prepare` outbox markers order intent before promotion, but full prepare/commit idempotency is incomplete. A crash in the window can still repeat a downstream promotion. |
| R2-#8 | Unique member `path` across packet members | **PARTIAL** | `maxContains: 1` closed the duplicate-role half. Cross-item field uniqueness is not expressible in plain JSON Schema — needs a runtime check or a custom keyword. |
| R1-#16 | Timing side-channels | **ACCEPTED RISK** | Explicitly scoped out of v1 with rationale in the contract. Not a fix. |
| — | `caller=None` bare-CLI bypass | **BY DESIGN, FRAGILE** | Safe today only because the shipped CLI is the sole entry point under trusted-local-shell (matches `api/auth/rbac.py` precedent). It is a **fail-open default that must NOT be reused by any HTTP/MCP/automation surface.** |
| — | RPC-1.G unexecuted | **BY DESIGN** | Research Provenance Continuity is `draft`. 4 of its 7 schemas already exist (`canonical_claim`, `inference_record`, `search_request`, `search_run`); 3 do not (`provenance_origin`, `research_run_envelope`, `search_activity_receipt`). ERI keeps refs to those 3 optional/nullable and invents no field semantics. |
| — | Producer profiles | **OFFLINE-UNVALIDATED** | None validated against live vendor output. ChatGPT profile was modelled on ONE real captured Deep Research packet (`pediatric-anemia-site/docs/project_plans/expansion/dr-packets/cbc/chatgpt-dr/`). Do not claim otherwise in docs or CHANGELOG. |

## NEXT STEPS

1. **Final verdict gate.** The plan's `ERI-6.5` requires `task-completion-validator` then **Karen**
   on the exact tree. The validator has passed (post-remediation re-run advisable since the tree
   moved). **Karen has NOT run.**
   → Recommended: run this gate on **`claude-fable-5`**. Per `~/.claude/config/model-registry.yaml`,
   Fable 5 explicitly earns its 2× on *"high-stakes verdict gates — final sign-off on core-path /
   auth / migration work where a wrong 'done' ships a regression."* That is exactly this.
   → **Do NOT make Fable 5 the orchestrator**: its registry entry lists `tools: [one_million_context]`
   and does **not** include `agent_tool`/`task_tool`, which `claude-opus-5` does. This workload is
   delegation-heavy (14+ subagent dispatches). Keep Opus 5 orchestrating.
2. **Decide on R2-#5 and R2-#8** — close them, or formally defer each with a design spec under
   `docs/project_plans/design-specs/` and append to the plan's `deferred_items_spec_refs` (the
   ERI-DF-1..4 pattern is already established there).
3. **Squash to main** (the user asked for this explicitly):
   ```bash
   git checkout main && git merge --squash worktree-eri-v1 && git commit
   ```
   Re-check `git log --oneline $(git merge-base main worktree-eri-v1)..main` first — main drifted
   once already mid-run.
4. Mark plan `status: completed` via
   `.claude/skills/artifact-tracking/scripts/manage-plan-status.py`, and write
   `.claude/progress/external-research-report-interchange/plan-completion.md`.

## Operational gotchas learned this run

- **Session rate limits killed 5 subagents mid-task.** Work is checkpointed per wave so nothing was
  lost, but this was the dominant cost. Resume a dead agent with `SendMessage` to its agentId — it
  resumes from transcript with context intact, far cheaper than re-dispatching.
- **Split large phases.** Every death happened on a long-running single leg.
- **zsh does not word-split unquoted `$VAR`** — pytest file lists must be literal.
- **`codex exec` needs the prompt on stdin** (`codex exec -m <model> - < prompt.md`). Passing it
  positionally while stdin is a pipe makes it hang waiting on stdin.
- **~12 orphaned ICA processes** (1–3 days old) were observed running. Not from this session; worth
  a cleanup pass. Use `timeout -k` when launching ICA legs.
- ICA (`~/ica-claude.sh -p ... --model 'claude-sonnet-5[1m]' --dangerously-skip-permissions`) worked
  well for bounded authoring (P1 schemas, P3 profiles). Security-critical work stayed on primary.
