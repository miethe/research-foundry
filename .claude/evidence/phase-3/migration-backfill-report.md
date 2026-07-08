---
title: "Phase 3 — Real Backfill Apply Report"
generated: 2026-07-08
workspace_root: "/Users/miethe/dev/homelab/development/research-foundry"
gate_1_approval_artifact: ".rf_state/migrations/mig_20260708T145811-gate1-approval.json"
gate_1_operator: "Nick Miethe"
gate_1_decision: "approve_migration_apply__hold_enforcement"
migration_run_id: "20260708T145911.176668Z"
manifest_path: ".rf_state/migrations/20260708T145911.176668Z-workspace-backfill.json"
enforcement_status: "INERT — NOT applied; deferred to Wave 6/7 per operator decision"
report_type: backfill_apply
---

# Workspace Isolation Migration — Real Backfill Apply Report

> **Gate #1 Approved.** Operator: Nick Miethe. Decision: approve_migration_apply__hold_enforcement.
> Backfill was run against the real workspace on 2026-07-08T14:59:11Z.
> Enforcement flip (WKSP-304) is explicitly HELD and deferred to Wave 6/7.

---

## Raw BackfillReport Output

```json
{
  "total_attempted": 0,
  "total_succeeded": 0,
  "total_failed": 0,
  "manifest": [],
  "target_workspace_id": "default",
  "migration_run_id": "20260708T145911.176668Z",
  "catalog_rebuild_ok": true,
  "catalog_rebuild_error": null
}
```

---

## Dry-Run Parity Check

| Metric | Dry-Run Prediction | Real Backfill Result | Match? |
|--------|-------------------|----------------------|--------|
| total_drafts / total_attempted | 0 | 0 | YES |
| drafts_missing_workspace_id / total_succeeded | 0 | 0 | YES |
| catalog_items | 0 | catalog_rebuild_ok=true | YES |
| target_workspace_id | "default" | "default" | YES |

**Parity: CONFIRMED.** The dry-run prediction matched the real backfill result exactly, satisfying Gate #1 check #2.

---

## Manifest

Written to: `.rf_state/migrations/20260708T145911.176668Z-workspace-backfill.json`

```json
{
  "migration_run_id": "20260708T145911.176668Z",
  "target_workspace_id": "default",
  "total_attempted": 0,
  "total_succeeded": 0,
  "total_failed": 0,
  "entries": []
}
```

Empty `entries` list is expected — no draft.yaml files existed in this workspace, so nothing was touched. The rollback function (`rf workspace rollback 20260708T145911.176668Z`) would be a safe no-op against this manifest.

---

## Enforcement Status

`require_workspace_scope()` remains advisory (always `allowed=True`). No behavioral change was made to any request-handling path. Per operator Gate #1 decision (`hold_enforcement`), the enforcement flip (WKSP-304), 0-leak regression suite (WKSP-305), and FE contract test (WKSP-900) are DEFERRED to Wave 6/7 pending:
- Resolution of the `cli.py`/`cli/` package conflict in the `rf` binary
- Sequencing of the behavioral cutover with P5.6

---

## Gate #1 Artifacts Reference

| Artifact | Path |
|----------|------|
| Gate approval | `.rf_state/migrations/mig_20260708T145811-gate1-approval.json` |
| Backfill manifest | `.rf_state/migrations/20260708T145911.176668Z-workspace-backfill.json` |
| Dry-run report | `.claude/evidence/phase-3/migration-dry-run-report.md` |
| This report | `.claude/evidence/phase-3/migration-backfill-report.md` |
