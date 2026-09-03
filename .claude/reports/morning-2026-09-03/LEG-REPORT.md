# LEG-REPORT — ADP-M3 R2a closeout (2026-09-03)

## Files changed

- `docs/reports/adp-m3-r2a-close-2026-09-03.md` — verified row-by-row closeout, reconcile measurements, and blocking categories.
- `docs/reports/adp-m3-r2a-diffs/` — 10 preserved local-agent copies and 10 nonempty catalog diffs (pre-existing partial work verified here).
- `docs/reports/adp-m3-r2a-dev-execution-merge/` — proposal-only merge evidence (pre-existing partial work verified here).
- This report. No source artifact was modified, and `delegation-router` remains untouched.

## Commands run / verified output

- Read required artifact-registration and claim-verification rules; inspected SkillMeat and IntentTree help before mutations.
- `itt node dedup-check` returned no match during a race; the resulting duplicate was immediately archived after the canonical node was identified. Canonical mapping finding is `node_01M1KZR6NRS01J948D0CDT3N49`; archived duplicate is `node_01M1M124G9R753ZDNK719HMD8R`.
- `itt tree list`, `itt node get`, `itt node delete --help`, and archive/read-back verified the single live mapping finding.
- `skillmeat project reconcile . --check --json` was attempted foreground-only; it emitted only `checking 147 catalog artifacts`, not a final JSON result in this window.

## Counts

- 10 agent backups + 10 nonempty diffs; all 10 dry-runs successful; first 8 materializations verified HTTP 404/no writes; no successful materialization for any of the 10.
- 5 no-ledger skill rows remain unactioned; 9 context mappings excluded; planning captured at Enterprise version `38455bc7-51cc-4741-ba10-9d6858fd22bf`; one dev-execution proposal exists.
- Completed post-action reconcile evidence: 24 gaps / 17 drift / 181 expected. Historical requested baseline: 146 / 17 / 180. Fresh after-count is unverified.

## Open questions

The worktree cannot be safely registered with `init`/`project register`: its manifest points to the primary checkout, and deployment returns HTTP 404 before writes. A path-correct enterprise project record is required before retrying deployment. Resolve the five skill drift rows, nine context mappings, 14 remaining genuine gaps, and the dev-execution owner decision before R2 exit.
