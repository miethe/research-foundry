---
title: Reusable Assertion Ledger
doc_type: user_guide
schema_version: 2
status: active
created: 2026-07-15
updated: 2026-07-15
feature_slug: reusable-assertion-ledger
---

# Reusable Assertion Ledger

The assertion ledger keeps a durable, passage-bound assertion separate from a
run-local claim. A source assertion points to one immutable source edition and
one passage. An inference record is derived reasoning and is never presented as
source evidence. A canonical claim, when a later authorized phase supplies one,
is a mutable grouping layer; it never replaces the source assertion or a run's
canonical claim ledger.

## What you can expect

- Existing run claim ledgers remain canonical for their runs. Missing durable
  references mean assertion-only/legacy behavior, not an inferred link.
- A packet can be unavailable because the workspace does not match, rights or
  sensitivity are denied, its evaluation is missing or failed, its lifecycle is
  invalidated, or its freshness is stale. Denied packets do not disclose a
  substitute source or hidden counts.
- A stale assertion asks for refresh. An invalidated, retracted, blocked, or
  superseded assertion cannot be reused. Historical evidence remains available
  only through its authorized run context.

## Normal swarm runs

With `foundry.assertion_ledger.ledger_write_enabled: true`, `rf swarm drive`
records source editions and quote passages during intake, then uses the shared
strict materializer after claim mapping. Eligible claims receive
`persistent_references.source_assertion_id`; unsupported or ambiguous evidence
abstains under the existing passage, rights, and provenance controls. The
planner's workspace follows the run through intake and materialization; local
CLI plans use `default`.

The run records its outcome in `writebacks/assertion_materialization.yaml`.
Materialization errors are logged by exception type and recorded in that
receipt and the drive's notes; synthesis, verification, and bundling continue.
Retries use the materializer's existing idempotent publication behavior.
Disabling ledger writes skips edition and assertion production. Existing
report-verification receipts remain independent. `automated_reuse_enabled` and
`canonical_claims_enabled` independently control their respective capabilities;
neither is required to produce source assertions.

## Review and correction

Review source-bound evidence before relying on it. Correcting evidence creates
a new immutable edition, passage, or assertion; it does not overwrite the
previous artifact. A lifecycle event blocks reuse before any derived projection
is reconciled. If a proposed canonical grouping is wrong, retain the source
assertions and use a versioned split or rollback record when that later,
separately authorized capability exists.

## Private boundary

This repository ships with ledger writes, automated reuse, and canonical claims
off by default. Turning a local configuration flag on does not grant private
workspace access, pilot authority, shared indexing, public promotion, or
external writeback permission. Only the designated private-workspace owner can
authorize those actions and observe any pilot health window.

**Note on this deployment:** this codebase's default-off controls are code-level
defaults, not this deployment's current state. This single-operator
deployment's `foundry.yaml` enables ledger writes and automated reuse while
leaving canonical claims disabled. Set an enabled control back to `false` to
return that capability to the code default.

For local operator recovery and aggregate-only readiness receipts, see the
[assertion-ledger readiness runbook](../dev/architecture/runbooks/assertion-ledger-readiness.md).
