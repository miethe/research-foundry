---
title: Assertion Ledger Readiness Runbook
doc_type: runbook
schema_version: 2
status: active
created: 2026-07-15
updated: 2026-07-15
feature_slug: reusable-assertion-ledger
---

# Assertion Ledger Readiness Runbook

## Scope and authority

This runbook covers repository-local, reversible readiness only. It does not
authorize a private pilot, production deployment, shared index, public rights
promotion, external writeback, or a change to a real workspace. Obtain explicit
workspace-owner authorization, a private-data scope, and an observation window
before targeting any non-synthetic workspace.

## Controls and dependencies

Start with every control absent or `false`:

```yaml
foundry:
  assertion_ledger:
    ledger_write_enabled: false
    automated_reuse_enabled: false
    canonical_claims_enabled: false
```

`ledger_write_enabled` gates the explicit source-card registry seam.
`automated_reuse_enabled` and `canonical_claims_enabled` are separate opt-ins,
but each fails closed until ledger writes are enabled. A configuration edit alone
is not a rollout receipt.

## Local dry-run and recovery rehearsal

Use a synthetic or owner-authorized workspace root. These commands do not
enable a flag and do not contact external systems:

```bash
python scripts/assertion_ledger_readiness.py --root /path/to/workspace
python scripts/assertion_ledger_readiness.py --root /path/to/workspace --write-receipts
```

The first command emits aggregate counts and two deterministic receipts:
`backfill_dry_run` and `disable_rollback_rehearsal`. With `--write-receipts`,
the same local JSON receipts are written beneath
`.rf_state/assertion_ledger/readiness/`. Re-running with unchanged inputs is
idempotent. The metrics intentionally contain no passage text, source locator,
workspace identifier, raw assertion identifier, or external-writeback payload.

Recovery target: set all three controls to `false`, retain immutable ledger and
run evidence, then rerun the dry-run command to record the disabled state. A
failed migration, health, isolation, or rollback check means automated reuse
and canonical claims stay disabled.

## Private-rollout handoff checklist

Before a private owner starts a pilot, attach explicit authorization, the
selected workspace/data boundary, approved observation window, health criteria,
and rollback owner. Record actual flag states and aggregate outcomes. Do not use
this runbook's synthetic/local receipt as proof of a private rollout.
