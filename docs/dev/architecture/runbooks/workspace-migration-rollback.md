---
title: Workspace Migration Rollback Runbook
category: runbook
scope: public-multiuser-release/P5.3
status: active
created: 2026-07-07
related_tasks: [WKSP-301, WKSP-302, WKSP-303]
related_documents:
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1/phase-3-workspace-migration.md
---

# Workspace Migration Rollback Runbook

Use this runbook to reverse a `rf workspace` backfill that stamped
`workspace_id = "default"` onto legacy draft records.

## Overview

The workspace isolation migration (WKSP-302/303) walks every
`draft.yaml` under `<workspace>/reports/drafts/` whose `workspace_id`
field is null and sets it to `"default"`.  Before applying the
migration a JSON manifest is written to:

```
<workspace>/.rf_state/migrations/<migration_run_id>-workspace-backfill.json
```

The `migration_run_id` (an ISO-8601 compact timestamp) is the sole key
needed to roll back.  The rollback reads that manifest and restores
each listed draft to its prior state.

### Catalog items note

`catalog_items` in `catalog.db` have **no coded per-row rollback**.
The catalog is a rebuildable derived index.  To reverse a catalog
migration: revert the `schema_version` in `foundry.yaml` and run
`rf catalog rebuild`.  The rollback report's `catalog_item_note` field
repeats this instruction.

---

## Step 0 — Prerequisites

1. Confirm you have write access to the workspace root.
2. Confirm the `migration_run_id` from the original backfill output
   (printed by `rf workspace migrate-dry-run --json` or in the
   `BackfillReport` returned by `backfill()`).
3. Optional but recommended: take a filesystem snapshot of
   `<workspace>/reports/drafts/` before rolling back.

```bash
# Snapshot with rsync (example)
rsync -a <workspace>/reports/drafts/ /tmp/drafts-snapshot-$(date +%s)/
```

---

## Step 1 — Dry-run the rollback

Always dry-run first to confirm scope before writing anything.

```bash
rf workspace rollback <migration_run_id> --dry-run
```

Or for machine-readable output:

```bash
rf workspace rollback <migration_run_id> --dry-run --json
```

The report fields:

| Field | Meaning |
|---|---|
| `total_attempted` | Draft records in the manifest |
| `total_reverted_drafts` | Records that *would* be reverted |
| `total_failed` | Records whose file is missing or unreadable |
| `is_dry_run` | Always `true` in dry-run mode |
| `catalog_item_note` | Manual steps required for catalog rollback |

If `total_failed > 0`, inspect the affected draft directories before
proceeding (the file may be missing or corrupt).

---

## Step 2 — Apply the rollback

```bash
rf workspace rollback <migration_run_id> --execute
```

The command exits with code 0 on full success, 1 if any record failed.

---

## Step 3 — Verify

```bash
# Confirm no drafts retain workspace_id from the migrated run.
rf workspace migrate-dry-run

# Expected: drafts_missing_workspace_id equals the number of reverted drafts.
```

Check a specific draft directly:

```bash
cat <workspace>/reports/drafts/<report_draft_id>/draft.yaml | grep workspace_id
# Should produce no output (key absent) for reverted drafts.
```

---

## Step 4 — Catalog items (manual)

If the original migration also touched `catalog_items` (WKSP-303), the
catalog must be rebuilt after the schema revert:

```bash
# 1. Revert schema_version in foundry.yaml (or the catalog schema file).
# 2. Rebuild the catalog index from the reverted draft.yaml files.
rf catalog rebuild
```

---

## Manual fallback — restore from snapshot

If the automated rollback fails (e.g., manifest file is missing or
the `rf` CLI is unavailable), restore from the filesystem snapshot
taken in Step 0:

```bash
rsync -a --delete /tmp/drafts-snapshot-<ts>/ <workspace>/reports/drafts/
```

Then rebuild the catalog:

```bash
rf catalog rebuild
```

---

## Safety invariants

The `rollback` implementation enforces the following:

1. **Manifest-only authority** — rollback NEVER keys on the value
   `workspace_id == "default"`.  It uses ONLY the explicit record-id
   list from the stored manifest.  Records created after the migration
   (even if they carry `workspace_id = "default"`) are never touched.

2. **Atomic writes** — each `draft.yaml` is updated with the
   temp-file + `os.replace` pattern; a crash mid-write cannot corrupt
   the file.

3. **Null restoration** — if `prior_workspace_id` was `None`, the
   `workspace_id` key is removed entirely (not set to `null`) so the
   file is byte-identical to the pre-migration state.
