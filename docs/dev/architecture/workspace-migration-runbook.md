---
title: Workspace Migration Operator Runbook
description: Operator guide for executing the workspace isolation migration (dry-run → enforcement → rollback if needed)
audience: operators
category: runbook
scope: public-multiuser-release/P5.3
status: active
created: 2026-07-08
tags: [workspace-isolation, migration, operator-guide, P5.3]
related_documents:
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-3-workspace-migration.md
  - docs/dev/architecture/runbooks/workspace-migration-rollback.md
---

# Workspace Migration Operator Runbook

This runbook guides operators through the complete workspace isolation migration process: dry-run → human approval → enforcement → rollback (if needed).

## What This Migration Does

The workspace isolation migration backfills the `workspace_id` field across all legacy draft records and catalog items, assigning them to a single synthetic `"default"` workspace. This is a one-time migration that prepares the system for workspace-scoped access control.

After migration:
- All legacy records are tagged with `workspace_id = "default"`
- The system can enforce workspace isolation: cross-workspace access returns 404
- Existing single-operator deployments continue to work (everything is in the `"default"` workspace)

This is a **reversible operation** — a tested rollback procedure exists and can restore the pre-migration state if issues surface.

---

## Prerequisites

Before starting the migration:

1. **Backup your data** — create a full filesystem snapshot of `<workspace>/reports/drafts/` and `<workspace>/.rf_cache/catalog.db`:
   ```bash
   rsync -a <workspace>/reports/drafts/ /backup/drafts-$(date +%Y%m%d-%H%M%S)/
   rsync -a <workspace>/.rf_cache/catalog.db /backup/catalog-$(date +%Y%m%d-%H%M%S).db
   ```

2. **Stop the server** — ensure no API requests are active during the dry-run and backfill:
   ```bash
   # Example: systemctl stop research-foundry
   ```

3. **Confirm `rf` CLI is available** — test the command:
   ```bash
   rf --version
   ```

---

## Phase 1: Dry-Run (Zero Writes)

The dry-run evaluates the migration without changing any files. This is what the human approval gate reviews.

### Step 1.1 — Run the dry-run

```bash
rf workspace migrate-dry-run
```

**Output** — a human-readable table showing:
- Total draft count
- Drafts missing `workspace_id` (will be backfilled)
- Drafts missing `created_by`
- Total catalog items (all will gain `workspace_id = "default"`)
- Migration timestamp

### Step 1.2 — Review dry-run output for approval gate

The dry-run output is the primary artifact the human approval gate reviews. Verify:

1. **Record counts look reasonable** — compare against your current draft/catalog volume
2. **No unexpected zeros** — if you expect 100+ drafts but the dry-run shows 0 missing `workspace_id`, investigate before proceeding
3. **`created_by` expected to be null** — legacy records cannot be safely attributed; this is by design

### Step 1.3 — Machine-readable output (for documentation/records)

Export the dry-run result as JSON for the approval record:

```bash
rf workspace migrate-dry-run --json > dry-run-report.json
```

Store this JSON in your change request, PRD, or operations log for traceability.

---

## Phase 2: Backfill (Additive-Only Data Change)

After the dry-run is reviewed and approved, the backfill applies the migration. The backfill is **additive** — it only stamps `workspace_id = "default"` on records that lack it. No records are deleted or transformed.

### Step 2.1 — Run the backfill

```bash
rf workspace migrate --apply
```

**Output** — a `BackfillReport` showing:
- `migration_run_id` — a timestamp key you'll need for rollback if required
- Records touched
- Manifest path (e.g., `<workspace>/.rf_state/migrations/20260708T123456Z-workspace-backfill.json`)

**Important**: Save the `migration_run_id` from this output. You will need it if rollback is required.

### Step 2.2 — Verify backfill result

Check that records were backfilled:

```bash
rf workspace migrate-dry-run
```

Expected: `drafts_missing_workspace_id` should now be 0 (or match only newly-added records without `workspace_id`).

Spot-check a specific draft:

```bash
cat <workspace>/reports/drafts/<report_id>/draft.yaml | grep workspace_id
# Should show: workspace_id: default
```

### Step 2.3 — Backfill result matches dry-run prediction

The backfill report counts must match the dry-run output exactly. If they diverge, **stop** and investigate before proceeding to enforcement.

---

## Phase 3: Human Approval Gate (BLOCKS ENFORCEMENT)

At this point:
- Dry-run has been reviewed and approved
- Backfill has been applied and verified
- Data is now tagged with `workspace_id = "default"`

**The enforcement flip is gated on explicit human approval.** You must record approval before the system will activate workspace isolation.

### Step 3.1 — Record approval

Create an approval artifact (this is what the `rf workspace enforce` command checks for):

```bash
# Approver name, timestamp, references to dry-run/backfill reports
rf workspace approve-migration <migration_run_id> --approver "<your-name>"
```

This writes an approval record to `.rf_state/migrations/<migration_run_id>-gate1-approval.json`.

Alternatively, if the CLI does not yet support this, create the approval JSON manually:

```json
{
  "migration_run_id": "20260708T123456Z",
  "approved_by": "ops-team",
  "approved_at": "2026-07-08T14:30:00Z",
  "dry_run_report": "dry-run-report.json",
  "backfill_report": "backfill-report.json",
  "notes": "Reviewed counts; backfill matched dry-run. Approved for enforcement."
}
```

Save this as `.rf_state/migrations/<migration_run_id>-gate1-approval.json`.

---

## Phase 4: Enforcement Flip (Enables Workspace Isolation)

After human approval, the enforcement flip activates workspace isolation in the running system.

### Step 4.1 — Flip enforcement on

```bash
rf workspace enforce --on --gate-1-approved-by <migration_run_id>
```

The command checks for the approval artifact and refuses to run without it.

**Output** — confirmation that workspace isolation is now **enforced**:
- Cross-workspace access will now return 404 (not 200)
- Same-workspace access continues to work normally

### Step 4.2 — Restart the server

Enforcement is a configuration change. Restart the API server to pick it up (or reload config if your deployment supports it):

```bash
# Example: systemctl restart research-foundry
# Or: kill the server process and restart
```

### Step 4.3 — Smoke test

After restart, verify the system is operational:

```bash
# Basic connectivity test
curl http://localhost:8000/api/health

# If available, run your smoke-test suite
pytest tests/integration/test_workspace_isolation.py -v
```

---

## Rollback (If Issues Surface)

If enforcement causes unexpected failures, rollback to the pre-migration state.

### Rollback Procedure

See [Workspace Migration Rollback Runbook](runbooks/workspace-migration-rollback.md) for detailed step-by-step rollback instructions.

**Quick summary**:

```bash
# 1. Dry-run the rollback
rf workspace rollback <migration_run_id> --dry-run

# 2. Apply rollback
rf workspace rollback <migration_run_id> --execute

# 3. Flip enforcement off
rf workspace enforce --off

# 4. Restart server
# systemctl restart research-foundry

# 5. Verify pre-migration state
rf workspace migrate-dry-run
# Expected: drafts_missing_workspace_id returns to pre-backfill counts
```

The rollback is **atomic per-file** and **safe** — it uses the migration manifest (not value-matching) to identify records that were touched by this specific migration run.

---

## Troubleshooting

### Dry-run shows 0 drafts when I expect many

Check that:
1. The workspace path is correct: `echo $RF_WORKSPACE` or `rf workspace show`
2. Drafts exist: `find <workspace>/reports/drafts/ -name "draft.yaml" | wc -l`
3. Drafts are readable: `cat <workspace>/reports/drafts/<any-id>/draft.yaml`

If the count is genuinely 0, the migration is a no-op and safe to proceed.

### Backfill report does not match dry-run

**Stop and investigate** before proceeding to enforcement. Possible causes:
- Draft files were added/deleted between dry-run and backfill
- Permissions issue preventing backfill from reading/writing drafts
- Catalog rebuild failed partway through

Recommended action: take the recent backup and restore, then try the dry-run again.

### Enforcement flip fails with "gate-1-approval.json not found"

The approval artifact was not recorded. Either:
1. Use `rf workspace approve-migration` to create it retroactively, or
2. Create `.rf_state/migrations/<migration_run_id>-gate1-approval.json` manually (see Phase 3.1 above)

### Cross-workspace requests now return 404 but I expected 403

This is **correct behavior** — the system treats cross-workspace access identically to non-existent records (no-existence-leak convention). If you see 404 on a record that should be same-workspace, verify the request context includes `workspace_id` matching the record's `workspace_id`.

### Server fails to start after enforcement flip

Likely causes:
1. Config syntax error in `foundry.yaml` — check the `auth.workspace_isolation` flag format
2. Enforcement code path hit an unexpected error — check logs for `workspace_isolation` or `require_workspace_scope`

Rollback to `--off` and restart.

---

## Verification Checklist

After enforcement is live, confirm:

- [ ] Dry-run output reviewed and approved by human
- [ ] Backfill result matches dry-run counts exactly
- [ ] Approval artifact exists at `.rf_state/migrations/<migration_run_id>-gate1-approval.json`
- [ ] `rf workspace enforce --on` ran successfully (exit code 0)
- [ ] Server restarted and health-check passes
- [ ] Smoke tests pass (if available)
- [ ] Existing same-workspace requests still work (200 response)
- [ ] Cross-workspace requests now return 404

---

## References

- **Phase 3 Implementation Plan**: [phase-3-workspace-migration.md](../project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-3-workspace-migration.md)
- **Rollback Procedure**: [workspace-migration-rollback.md](workspace-migration-rollback.md)
- **Config Schema**: `src/research_foundry/config.py` (`auth.workspace_isolation` flag)
- **CLI Commands**: `rf workspace --help`

---

## Support

If you encounter issues not covered in this runbook:

1. Check the rollback procedure first — rollback is always reversible
2. Consult Phase 3's implementation plan for technical details
3. Review server logs for structured error traces
4. Contact the development team with:
   - Dry-run output (`dry-run-report.json`)
   - Backfill result count
   - Error messages from server logs
   - Rollback attempt output (if you've tried rolling back)
