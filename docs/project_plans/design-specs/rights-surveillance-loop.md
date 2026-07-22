---
title: "Design Spec: Rights-Terms Surveillance Execution Loop"
doc_type: design_spec
schema_version: 2
status: draft
maturity: idea
created: 2026-07-21
updated: 2026-07-21
feature_slug: rights-entity-model
deferred_from: rights-entity-model-v1
deferred_item_id: DI-RIGHTS-3
category: backlog
owner: rf
prd_ref: docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md
related_docs:
  - docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md
  - docs/dev/architecture/adr-rights-entity-model.md
  - schemas/rights_record.schema.yaml
  - src/research_foundry/services/rights_validation.py
---

# Design Spec: Rights-Terms Surveillance Execution Loop

> **Maturity: idea** — pre-commitment stub. No implementation has been
> scoped. Promote to `proposal` when the promotion trigger fires.

---

## Deferral Summary

| Field | Value |
|-------|-------|
| **Deferred from** | `rights-entity-model-v1` (OQ-RF-5) |
| **Reason** | `rights_record.review.next_review_at` is present in the ported schema (§9.5/Phase 0), but nothing in `rights-entity-model-v1` re-checks it — there is no scheduled loop that re-verifies terms against `next_review_at`, diffs against a prior snapshot, or raises an alert when a rights term lapses. The field is a real, named debt, not an oversight: it is decorative data with no consumer until this spec is designed and promoted. |
| **Trigger for promotion** (plan's own wording, Deferred Items Triage Table, `DI-RIGHTS-3`) | "A second consumer needs proactive re-review notifications" |
| **Target spec path** | `docs/project_plans/design-specs/rights-surveillance-loop.md` (this file) |

---

## Context

### What exists today (as of `rights-entity-model-v1`)

- `rights_record.review.next_review_at` (schema: `schemas/rights_record.schema.yaml`)
  carries a nullable date at which a rights term's terms/status should be
  re-checked. It is written at capture/adjudication time but never read by
  any scheduled process.
- `check_rights_divergence` (`src/research_foundry/services/rights_validation.py`,
  Phase 2 of `rights-entity-model-v1`) is the **only** consumer of this
  field today, and it is a **passive, on-demand validator**, not an
  execution loop: given an `as_of` timestamp supplied by the caller, it
  compares `as_of` against each linked `rights_record`'s
  `review.next_review_at` and, if `as_of` is past that date, sets a
  `stale: bool` flag on its result. Per the function's own docstring, this
  is explicitly **non-fatal by design** — staleness is surfaced as one
  finding among others in a divergence report, not raised as an alert, not
  scheduled, and not acted upon automatically.
- There is no cron, queue, or background service in RF today that invokes
  `check_rights_divergence` (or anything else) on a periodic basis with a
  "current time" `as_of`. Nothing watches `next_review_at` proactively;
  a human or process must think to run the validator and supply `as_of`
  themselves.

### The named gap (ADR `docs/dev/architecture/adr-rights-entity-model.md`,
"Known Gaps" § OQ-RF-5)

> "There is no scheduled loop that re-verifies terms against
> `next_review_at`, diffs against a prior snapshot, or raises an alert when
> a rights term lapses."

This spec is the ADR-designated "sanctioned venue for designing the
scheduled re-check loop against `next_review_at` before it is built" — the
ADR explicitly instructs: do not build the execution loop against the ADR
alone.

---

## Scope (idea-stage)

When promoted, this spec would need to cover:

- **Trigger mechanism** — how the loop is invoked: a cron-style scheduled
  job, an on-demand `rf rights surveillance` CLI subcommand run by a human
  or external scheduler (e.g. systemd timer, cron), or an event triggered
  by run capture/report generation touching a rights-bearing record. RF's
  files-canonical, no-service-on-recall-path constraint (see ADR OQ-RF-3)
  argues against a long-running always-on daemon; a periodically-invoked
  CLI command is the more consistent shape.
- **Re-check semantics** — what "re-verify terms" means in practice for a
  given `rights_record`: at minimum, comparing the current date against
  `review.next_review_at` (what `check_rights_divergence` already does,
  passively); at most, re-fetching the source terms/license page and
  diffing against the stored terms snapshot (see `DI-RIGHTS-2` / ADR
  OQ-RF-4 on where snapshots live) to detect an actual terms change, not
  just a lapsed review date.
- **Snapshot diffing** — whether and how a prior terms snapshot is
  retained and compared against a freshly fetched one, and what
  constitutes a material diff worth alerting on (byte-identical vs.
  semantic terms change).
- **Alerting/notification channel** — how a lapsed or changed rights term
  surfaces to a human: a governed MeatyWiki writeback (following the
  precedent in `feat(swarm-drive): E1-P1 sensitivity gate + governed
  MeatyWiki writeback (HITL)`), a CLI report, a queue entry consumed by
  another RF surface, or some other mechanism.
- **Ownership boundary** — whether RF itself owns running this loop as a
  service (the OQ-RF-5 question this spec answers: "Does RF own
  rights-terms surveillance as a service?"), or whether RF only ships the
  building blocks (`next_review_at`, `check_rights_divergence`) and a
  downstream consumer is responsible for scheduling and alerting.
- **Failure/backfill interaction** — how the loop should behave for
  records where `check_rights_divergence` already reports
  `backfill_needed` or a missing link (per the validator's existing
  degrade-gracefully behavior) rather than a clean stale/not-stale result.

### v1 Constraint

In `rights-entity-model-v1`, there is no automated surveillance execution.
`rights_record.review.next_review_at` is written and is checkable via
`check_rights_divergence`, but only on-demand and only as a non-fatal
finding inside whatever `as_of` the caller chooses to supply. No process
in RF invokes this automatically, on a schedule, or raises an alert. This
is documented as a known gap in `docs/dev/architecture/adr-rights-entity-model.md`
("Known Gaps" § OQ-RF-5) rather than a silent omission.

---

## Notes for Promotion

- Before scoping this, confirm the promotion trigger has actually fired —
  i.e., a second consumer of RF's rights data has a concrete need for
  proactive re-review notifications, not just a hypothetical future need.
  Per the plan's own reconciliation ("Record-the-debt for surveillance
  execution (OQ-RF-5) ... via DOC-006 design specs" — "ship the schema
  field that records the debt; name the gap rather than build the
  loop/role now"), building this speculatively ahead of a real consumer
  is exactly the failure mode this deferral avoids.
- Any scheduling design must respect RF's files-canonical, no-service-
  on-recall-path constraint (ADR OQ-RF-3) — prefer a periodically-invoked
  CLI/job over an always-on daemon on the run-read path.
- Consider whether `check_rights_divergence`'s existing `stale` flag and
  `as_of`-parameterized design can be reused directly as the check
  primitive for the loop (it already computes the comparison this spec
  would otherwise re-derive), with the loop's job reduced to "invoke this
  on a schedule and route non-`ok()` results somewhere a human sees them."
- Resolve alongside — but does not need to block on — the companion
  `DI-RIGHTS-4` (`docs/project_plans/design-specs/rights-counsel-workflow.md`)
  spec: a surveillance alert that finds a lapsed term will eventually need
  a human/role to act on it, but the two gaps (execution loop vs.
  reviewer role) can be designed independently.
