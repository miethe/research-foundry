---
schema_version: 2
doc_type: design_spec
title: "Research Provenance: Historical Report Reconstruction (RPC-DF-1)"
status: draft
maturity: idea
created: 2026-07-28
plan_ref: docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
related_documents:
  - docs/dev/architecture/research-provenance-contract-freeze.md
  - .claude/findings/research-provenance-continuity-findings.md
deferred_from: "Research Provenance Continuity (RPC) implementation plan — Deferred Items table, RPC-DF-1"
---

# Research Provenance: Historical Report Reconstruction (RPC-DF-1)

## Context

RPC's Phase P3 (`schemas/report_assertion_use.schema.yaml`, `assertion_report_use.py`) binds a
`report_assertion_use` record to a report's exact digest/revision and the exact assertion/inference/
canonical-claim persistent references it cited (`ReportAssertionUseService.prepare_report_assertion_use`,
`resolve_cited_reference` — see the dev guide). A report cited through this pipeline can only ever
produce a `report_assertion_use` record when its `persistent_references` block resolves to a real,
in-workspace record; anything else resolves `legacy_unresolved` and mints no canonical use record
(contract freeze §21, F14/AC RPC-3).

Reports synthesized **before** this contract existed — or before P4's `inference_id`/
`canonical_claim_id` reference plumbing was current on a given run — have no such
`persistent_references` block, or an incomplete one. There is no `report_assertion_use` record for
them today, and none will ever be minted retroactively by the shipped P3 service: `resolve_cited_reference`
treats a missing/unresolvable reference as `legacy_unresolved`, permanently, not as a queue of work to
backfill.

## Why it was deferred

A historical report's citations were, in general, resolved against *transient* evidence (a search
result, an LLM's own synthesis pass) that may never have been captured as a durable `source_assertion`,
`inference_record`, or `canonical_claim` at all. Reconstructing a `report_assertion_use` for such a
report requires either:

1. Finding an exact, already-existing persistent record that the historical citation *actually*
   corresponds to (a real backfill — matching old free-text citations to canonical IDs), or
2. Minting a **synthetic** persistent reference that merely stands in for "we believe this citation
   meant approximately this."

Option 2 is exactly the failure mode this whole feature exists to prevent: a `provenance_origin`/
`report_assertion_use` record's entire value is that it names *the actual, verifiable evidence*, not
an approximation of it (contract freeze §4.1 rule 6, "legacy absence mints no identity" — the same
principle applied here to report-use, not just origin). Minting a synthetic reference to satisfy a
UI gap would create false confidence exactly where evidence-pipeline correctness matters most.

## Trigger for promotion

Per the plan's Deferred Items table: **"A deterministic mapping study demonstrates exact
reconstruction."** Concretely, before this is promotable:

1. A study over a real corpus of historical reports demonstrates that a majority of historical
   citations can be deterministically and exactly mapped to an already-existing `source_assertion`/
   `inference_record`/`canonical_claim` record (not merely a plausible fuzzy match) — with the
   mapping's false-positive rate measured, not assumed.
2. The remaining unmappable minority has an explicit, honest disposition (e.g. permanently
   `legacy_unresolved`, never silently backfilled with a synthetic reference).
3. Any proposed reconstruction path preserves RPC-1.3's core invariant: a `report_assertion_use`
   record is created only from a persistent reference that independently, verifiably resolves —
   never minted to fill a lineage gap.

## Sketch of the eventual shape

Not designed here. A future promotion would likely take the form of a **read-only, offline
reconciliation job** — never a runtime path — that:

- Reads a historical report's stored citation text/metadata.
- Attempts a deterministic match against the workspace's `source_assertion`/`inference_record`/
  `canonical_claim` stores (exact digest or exact-id match only, per the mapping study's proven
  method).
- Produces `report_assertion_use` records **only** for citations that resolve with the demonstrated
  precision, using the same `ReportAssertionUseService.prepare_report_assertion_use` /
  `publish` path P3 already ships — no new writer, no new schema.
- Leaves every unmapped citation exactly as it is today: `legacy_unresolved`, visible as such, never
  hidden behind a synthetic identity.

This spec proposes no algorithm, no matching threshold, and no schema change. It exists to record
that the gap is known and intentionally unaddressed until the trigger above is met.
