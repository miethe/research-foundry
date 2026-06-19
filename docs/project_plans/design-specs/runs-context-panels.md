---
title: "Design Spec: Runs Viewer — Run Context Panels (FR-14)"
doc_type: design_spec
schema_version: 2
status: draft
maturity: idea
created: 2026-06-19
updated: 2026-06-19
feature_slug: runs-frontend
deferred_from: runs-frontend-v1
deferred_item_id: FR-14
category: backlog
owner: nick
related_docs:
  - docs/dev/architecture/rf-run-export-schema.md
  - docs/project_plans/implementation_plans/features/runs-frontend-v1.md
---

# Design Spec: Runs Viewer — Run Context Panels (FR-14)

> **Maturity: idea** — pre-commitment stub. No implementation has been
> scoped. Promote to `proposal` when the promotion trigger fires.

---

## Deferral Summary

| Field | Value |
|-------|-------|
| **Deferred from** | `runs-frontend-v1` (Phase 5, DOC-006) |
| **Reason** | Run context panels — routing decision, research brief, swarm plan, and upstream-entity (intent, I-BOM, IntentTree node) display — are secondary metadata for the v1 claim-audit workflow. They are not on the W1 (claim audit ≤ 30 sec), W2 (verification checklist), or W3 (corpus portfolio) critical paths. The current trust panel and claim ledger provide sufficient context for the primary operator task. |
| **Promotion trigger** | Post-v1 operator feedback confirms that reviewers would reduce run review time if context panels were available — specifically: wanting to see "why this run was created" (routing decision, research brief) alongside "what the run found" (claim ledger) without switching to the CLI. |
| **Target spec path** | `docs/project_plans/design-specs/runs-context-panels.md` (this file) |

---

## Scope (idea-stage)

When promoted, this spec would cover four panel surfaces within the run detail
view (likely as tabs or an expandable sidebar):

### Panel 1 — Routing Decision

- Renders `run.yaml` routing decision fields or `routing_decision.yaml`.
- Key content: selected model profile, routing rationale, estimated cost, budget
  comparison, sensitivity tier at routing time.
- Primary value: explains *why* a particular model/profile was used for this run.

### Panel 2 — Research Brief

- Renders `research_brief.md` as Markdown (scoped to the run).
- Key content: research question, audience, depth, freshness window, constraints.
- Primary value: gives context for *what was asked* alongside the claim ledger
  showing *what was found*.

### Panel 3 — Swarm Plan

- Renders `swarm_plan.yaml` in a structured view (tool calls, adapter routing,
  step sequence, estimated costs).
- Key content: which adapters ran (web search, PDF ingest, NLM, ARC), step
  ordering, actual vs estimated cost.
- Primary value: audit trail for *how the research was conducted*.

### Panel 4 — Upstream Entities

- Renders links and summary metadata for upstream entities that dispatched or
  requested this run: the originating IntentTree node (`intent_id`), I-BOM
  (`ibom_id`), and research intent (`intent_research_*.yaml`).
- Key content: intent description, JTBD, priority, linked I-BOM skills.
- Primary value: connects the run to its organizational context without requiring
  a CLI `rf status` call.

---

## Export Schema Extension (idea-stage)

Delivering these panels would require extending `run.json` with:
```jsonc
{
  "context": {
    "routing_decision": { /* routing_decision.yaml fields */ },
    "research_brief_md": "...",        // raw Markdown string
    "swarm_plan": { /* swarm_plan.yaml fields */ },
    "upstream_entities": {
      "intent_id": "...",
      "ibom_id": "...",
      "intenttree_node_id": "..."
    }
  }
}
```
This is an **additive extension** (new optional top-level key); existing
consumers using optional access (`context?.routing_decision`) would be
unaffected. However, it still requires a schema-version bump and
`backend-architect` re-review per the frozen-schema policy
(`rf-run-export-schema.md`).

---

## Routing Decision (v2)

The `context` panels deferred here are a natural v2 scope alongside the loopback
API (OQ-6). Once the API ships, live-reading `research_brief.md` and
`swarm_plan.yaml` on demand is more efficient than embedding them in `run.json`.
Evaluate whether to embed in the export or load lazily via the API when OQ-6 is
promoted.

---

## Notes for Promotion

- The four panels share a common "secondary metadata" read pattern — design them
  together, not as four independent features.
- `research_brief.md` rendering can likely reuse the report-overlay Markdown
  renderer with minimal styling changes.
- `swarm_plan.yaml` is a structured YAML; consider a collapsible tree view
  similar to the MeatyWiki lineage graph rather than a raw YAML dump.
- Upstream entity links (IntentTree, I-BOM) are navigable only if the
  IntentTree / SkillMeat services are reachable; design graceful degradation
  (show IDs as plain text when services are offline).
