Mode: A — Exploration Only (read-only investigation; do not edit deployed artifacts)

Node: node_01M1M77T1E1VPKDV5TDNFH0THK (repo research-foundry). 11 units (frontend-design,
gemini-cli, intenttree-cli, meatywiki, meatywiki-suite, nano-banana, notebooklm-sync,
recovering-sessions, ...) were skipped in ADP overwrite round r3 because live content differed
from the r1 backup at /private/tmp/claude-501/adp-bulk-adopt-backup-1788455460 — something wrote
those units between rounds. Find the writer: check shell history, git reflog, launchd/cron jobs,
and any session logs touching those 11 paths in the relevant time window (read receipts:
.claude/reports/morning-2026-09-03/adp-overwrite-drifts-r3.md).

Also compare the skillmeat deployment ledger's `content_hash` construction against the leg's own
fingerprint (sorted per-file sha256) — report whether they're different hash constructions.

Env for ITT reads: set -a; . ~/.config/aos/secrets.env; set +a; export
INTENTTREE_API_URL=http://10.42.10.76:8032

Deliverable: a short findings doc identifying the writer (or "no writer, false positive" with
receipt), plus the hash-construction comparison. Do NOT re-run the overwrite yourself.

No git commits, no push. Report under 200 words with file:line pointers.
