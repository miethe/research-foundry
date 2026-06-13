# Bug Automation Scripts Usage

Usage notes for batch bug filing and bug-fixes documentation updates.

---

## Quick Reference

| Scenario | Script | Example |
|----------|--------|---------|
| Capture single bug | `mc-quick.sh` | `mc-quick.sh bug api auth "Title" "Problem" "Goal"` |
| Batch capture (3+) | `batch-file-bugs.sh` | `batch-file-bugs.sh --input bugs.json` |
| Post-commit update | `update-bug-docs.py` | `update-bug-docs.py --commits sha --req-log REQ-...` |
| Status update only | `/mc` command | `/mc item update doc.md ITEM-01 --status done` |

**Script Locations**:
- `mc-quick.sh`: `.claude/skills/meatycapture-capture/scripts/mc-quick.sh`
- `batch-file-bugs.sh`: `.claude/scripts/batch-file-bugs.sh`
- `update-bug-docs.py`: `.claude/scripts/update-bug-docs.py`

---

## update-bug-docs.py

Purpose:
- Append a structured section to the monthly bug-fixes doc.
- Mark request-log items as done and add a commit note.

Location:
- `.claude/scripts/update-bug-docs.py`

Basic usage:
```bash
.claude/scripts/update-bug-docs.py --commits <sha[,sha]>
```

Common patterns:
```bash
# Use commits and a request log id
.claude/scripts/update-bug-docs.py --commits ddffb56,e2c4bbf --req-log REQ-20260110-skillmeat

# Preview the section without editing files
.claude/scripts/update-bug-docs.py --commits ddffb56 --req-log REQ-20260110-skillmeat --dry-run

# Append even if commit already recorded
.claude/scripts/update-bug-docs.py --commits ddffb56 --req-log REQ-20260110-skillmeat --force

# Specify the bug-fixes file explicitly
.claude/scripts/update-bug-docs.py --commits ddffb56 --bug-fixes-file .claude/worknotes/fixes/bug-fixes-2026-01.md
```

Behavior details:
- Bug-fixes file resolves from the first commit date unless `--bug-fixes-file` is provided.
- Request-log items can be inferred from commit messages (REQ-YYYYMMDD-project-XX).
- If no item IDs are provided, all non-done items in the request log are marked done.

Key options:
- `--commits` (required): Comma-separated commit SHAs.
- `--req-log`: Request-log doc id or path (REQ-YYYYMMDD-project or REQ-...md path).
- `--req-items`: Comma-separated item IDs.
- `--mark-all-open`: Mark all non-done items when no IDs supplied.
- `--bug-fixes-file`: Override the resolved bug-fixes doc path.
- `--dry-run`: Print the section only.
- `--force`: Append even if commit appears in the doc.

Output:
- Updates `.claude/worknotes/fixes/bug-fixes-YYYY-MM.md`.
- Updates request-log item status + adds a note with commit list.

---

## batch-file-bugs.sh

Purpose:
- File multiple bugs from JSON or CSV in one call.
- Optionally append to an existing request log.

Location:
- `.claude/scripts/batch-file-bugs.sh`

Basic usage:
```bash
.claude/scripts/batch-file-bugs.sh --input <file|-> [options]
```

Common patterns:
```bash
# JSON array input
.claude/scripts/batch-file-bugs.sh --input /tmp/bugs.json --project skillmeat

# CSV input, append to an existing request log
.claude/scripts/batch-file-bugs.sh --input /tmp/bugs.csv --append REQ-20260110-skillmeat.md

# Provide defaults for missing fields
.claude/scripts/batch-file-bugs.sh --input /tmp/bugs.json --domain web --priority high --status triage

# Dry run to see the payload
.claude/scripts/batch-file-bugs.sh --input /tmp/bugs.json --dry-run
```

Input formats:
- JSON array of item objects, or JSON object with an `items` array.
- CSV with headers: `title,type,domain,context,priority,status,tags,notes,severity,component`.

Defaults:
- `--type` defaults to `bug`.
- `--project` defaults to `skillmeat`.
- `--domain`, `--priority`, `--status`, `--context`, `--tags` can be supplied as defaults.

Notes:
- `severity` is mapped to `priority` if provided.
- `component` can be `domain/context`; if domain is missing, it will be split from `component`.
- `--append` uses `meatycapture log append`; otherwise it uses `meatycapture log create`.

Output:
- Creates or appends a request log via `meatycapture`.
