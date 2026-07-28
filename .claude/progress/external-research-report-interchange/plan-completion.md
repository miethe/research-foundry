# ERI v1 — Plan Completion

> 2026-07-28 · branch `worktree-eri-v1` · final HEAD `dd5ae1e` (17 commits) · squash-merged to `main`

## Final state

All 6 phases (38 pts) of `docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md` implemented, validated, and gated. Plan frontmatter `status: completed`.

## Gate record (ERI-6.5)

| Gate | Model | Verdict |
|---|---|---|
| Round-1 adversarial audit (contract) | gpt-5.6-sol | 20 findings → remediated |
| task-completion-validator (mid-run) | sonnet | PASS (caught stale-branch revert hazard) |
| Round-2 adversarial audit (implementation) | gpt-5.6-sol | 13 findings → 11 closed, 2 partial |
| task-completion-validator (final re-run, `16d60c4`) | sonnet | **PASS** — all 7 ACs, rebase integrity, suite exit 0 |
| Karen (final verdict, Fable 5) | fable | **BLOCKED** round 1 → **APPROVED** round 2 |

Karen's round-1 block was real: the R2-#8 raw-string uniqueness check was empirically bypassable
via path-alias normalization (`attachments/./table1.csv` aliased `attachments/table1.csv`; two
manifest entries, one file, `ok=True`). Fixed in `dd5ae1e` (canonical-form rejection + uniqueness
on the normalized set); Karen re-ran her bypass plus an extended alias battery against the fixed
tree — all rejected — and approved.

## Open-items disposition (from HANDOFF)

| Item | Disposition |
|---|---|
| R2-#5 exactly-once effect promotion | **Deferred as ERI-DF-5** — `docs/project_plans/design-specs/external-research-exactly-once-promotion.md`; in `deferred_items_spec_refs` + Deferred Items table |
| R2-#8 unique member path | **CLOSED** (`16d60c4` + `dd5ae1e`): canonical-form + normalization-aware uniqueness in `inspect_packet()`, parametrized alias regression tests |
| R1-#16 timing side-channels | Accepted risk, recorded in contract (unchanged) |
| `caller=None` bare-CLI posture | By design under trusted-local-shell; MUST NOT be reused by HTTP/MCP/automation surfaces (unchanged) |
| RPC-1.G refs | Draft; 3 missing schemas kept optional/nullable (unchanged) |
| Producer profiles | Offline-unvalidated (honestly labeled in CHANGELOG); first live-vendor validation is the follow-up |

## Follow-ups (post-merge)

1. First live-vendor validation of the five producer profiles (the one honest OPEN item).
2. ERI-DF-1..5 remain gated design specs; promote only on their stated triggers.

## Validation

Full 12-file ERI suite green (exit 0) at final HEAD, re-verified independently by both gate
reviewers. zsh/pytest gotchas recorded in HANDOFF §Operational gotchas.
