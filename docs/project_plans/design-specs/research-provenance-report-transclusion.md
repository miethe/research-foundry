---
schema_version: 2
doc_type: design_spec
title: "Research Provenance: Report-to-Report Transclusion (RPC-DF-2)"
status: draft
maturity: idea
created: 2026-07-28
plan_ref: docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
related_documents:
  - docs/dev/architecture/research-provenance-contract-freeze.md
  - .claude/findings/research-provenance-continuity-findings.md
deferred_from: "Research Provenance Continuity (RPC) implementation plan — Deferred Items table, RPC-DF-2"
---

# Research Provenance: Report-to-Report Transclusion (RPC-DF-2)

## Context

RPC's `report_assertion_use` (contract freeze §13-15, `RPC-1.3`) binds one report revision to the
exact assertion/inference/canonical-claim versions it cites — `build_report_ref` identifies a report
by `report_id` + `report_content_digest` + `report_revision_id`
(`report_revision_id_for_run_report(report_id, report_content_digest)`), and `build_cited_ref` names
exactly one of an assertion, inference, or canonical claim per use record. Nothing in this contract
addresses a report **citing another report** — i.e. Report B quoting, embedding, or summarizing a
finding that Report A already established and verified, rather than re-deriving it from a
`source_assertion` directly.

Today, if Report B wants to reuse Report A's conclusion, the only path is for Report B's synthesis
step to re-cite the same underlying `source_assertion`/`inference_record`/`canonical_claim` refs
Report A cited — there is no first-class "Report B transcludes/depends-on Report A" relationship in
the schema, and no identity concept for "the same finding, reused across reports" beyond independently
re-citing identical evidence.

## Why it was deferred

Report-to-report transclusion needs its own identity concept — a **component/revision identity**
distinct from both a report's own `report_revision_id` (the whole-document identity RPC-1.3 already
owns) and a `canonical_claim`'s identity (a single claim, not a report section). Design questions this
would raise are out of RPC v1's frozen scope entirely:

- What granularity does a "transcluded component" have — a whole report, a section, a single cited
  finding?
- Does transclusion carry its own immutable, versioned identity (mirroring how `report_assertion_use`
  binds to an exact digest/revision), or does it always resolve dynamically to "whatever Report A's
  current revision is"?
- Does staleness propagate: if Report A's citation becomes stale (per the effect-receipt mechanism
  `assertion_impact.py` already implements for assertions/inferences/canonical claims, contract
  freeze N7), does that staleness need to propagate transitively into every report that transcludes
  Report A?

None of these questions have a use case driving them yet. Building the mechanism speculatively risks
locking in the wrong granularity or the wrong staleness-propagation model before a real workflow
exists to validate it against.

## Trigger for promotion

Per the plan's Deferred Items table: **"A concrete transclusion use case enters an approved PRD."**
Concretely, before this is promotable:

1. A specific product workflow needs Report B to formally depend on / embed a portion of Report A
   (rather than independently re-citing the same underlying evidence).
2. That workflow's PRD names the required granularity (whole-report vs. section vs. single finding)
   and whether transitive staleness propagation is a hard requirement or a nice-to-have.
3. The design is reviewed against RPC-1.3's existing invariants — in particular, that a
   `report_assertion_use` record's `cited_ref` remains `oneOf` exactly one of assertion/inference/
   canonical-claim (contract freeze §14) is a frozen shape; a transclusion reference would need its
   own distinct field/record type, not an overload of `cited_ref`.

## Sketch of the eventual shape

Not designed here. Plausible future shape, sketched only to make the scope legible for a later
planner — not committed to:

- A new, separate reference kind (e.g. `transcluded_report_ref`) alongside `cited_ref`, naming a
  source report's `report_id` + `report_revision_id` (reusing RPC-1.3's existing identity, not a new
  one) plus an optional component locator (section id, claim id) if sub-report granularity is needed.
- Reuses the existing effect-receipt staleness mechanism (`assertion_impact.py`,
  `impact_effects/<event_id>/<digest>.yaml`) as the staleness-propagation primitive, rather than
  inventing a second mechanism — mirroring how RPC's own inference/canonical-claim staleness already
  works, per contract freeze N7 and the dev guide's staleness section.
- No mutation to `report_assertion_use.schema.yaml`'s existing frozen shape; a transclusion record
  would be additive, alongside it, never a widening of `cited_ref`'s `oneOf`.

This spec proposes no schema, no granularity decision, and no staleness-propagation algorithm. It
exists to record that the gap is known and intentionally unaddressed until the trigger above is met.
