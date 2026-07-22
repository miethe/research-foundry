---
title: "Design Spec: Rights Runtime Resolution API"
doc_type: design_spec
schema_version: 2
status: draft
maturity: idea
created: 2026-07-21
updated: 2026-07-21
feature_slug: rights-entity-model
deferred_from: rights-entity-model-v1
deferred_item_id: DI-RIGHTS-1
category: research-needed
owner: null
prd_ref: docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md
related_docs:
  - docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md
  - src/research_foundry/schemas.py
---

# Design Spec: Rights Runtime Resolution API

> **Maturity: idea** — pre-commitment stub. No implementation has been
> scoped. Promote to `proposal` only when the promotion trigger fires.

---

## Deferral Summary

| Field | Value |
|-------|-------|
| **Deferred from** | `rights-entity-model-v1` |
| **Decisions-block question** | OQ-3 ("Should a runtime resolution API replace the mirror?") / OQ-RF-3 |
| **Reason** | The parent plan's locked decision: *"Denormalized entity-level `rights_summary` mirror (`mirror_is_authoritative` const `false`), not a runtime resolution API"* — rationale: *"Files-canonical + no-service-on-recall-path constraint; a run must be readable offline."* A fast resolution API is a larger, separate infra investment than the mirror approach shipped in v1. |
| **Promotion trigger** (verbatim from the parent plan's Deferred Items Triage Table) | **"A consumer needs sub-request-latency rights resolution at scale the mirror can't provide"** |
| **Target spec path** | `docs/project_plans/design-specs/rights-runtime-resolution-api.md` (this file) |

---

## Background: Why the Mirror Won, Not a Runtime API

The `rights-entity-model-v1` plan ships `rights_summary` as a **denormalized,
entity-level mirror** attached directly to `source_card` and `source_assertion`
instances at capture time. The mirror is explicitly marked
`mirror_is_authoritative: false` — it is a fast, offline-readable snapshot,
not the source of truth. The authoritative rights state lives in the
`rights_record`/`rights_extension`/`content_reuse_assessment`/
`permission_record`/`rights_failure` schema family ported from the v1.0
rights substrate (Phase 0 of the parent plan).

OQ-3 in the parent plan's decisions block asked whether a **runtime
resolution API** — a live service that computes/returns current rights
status on request, rather than reading a pre-computed mirror field off disk
— should replace the mirror as the v1 design. The plan adjudicated this
question by locking on the mirror, for two binding constraints named in the
decisions block:

1. **Files-canonical** — Research Foundry's authority model treats
   Markdown/YAML on disk as the source of truth, not a running service.
2. **No-service-on-recall-path** — a run's rights status must remain
   readable when no RF service is running (offline access, archived runs,
   air-gapped review), which a runtime API cannot guarantee by definition.

A runtime resolution API was assessed as "a larger, separate infra
investment" than the mirror, and deferred rather than built speculatively.

---

## Scope (idea-stage)

When promoted, this spec would need to cover, at minimum:

- **API surface**: a query interface (likely REST, matching RF's existing
  `rf serve` API conventions) that accepts an entity reference
  (`source_card`/`source_assertion` id, or a `rights_record` id) and returns
  current rights status, resolved against whatever authoritative state
  exists at query time — including any updates that postdate the entity's
  captured `rights_summary` mirror.
- **Staleness/consistency model**: how resolution results relate to the
  mirror's `mirror_is_authoritative: false` field — does the API become the
  new authoritative source, or does it remain a read-through cache in front
  of the same `rights_record` family, with the mirror kept for offline
  fallback?
- **Latency budget**: the trigger condition names "sub-request-latency" —
  this spec would need to define what latency bound qualifies (e.g., p99
  under some threshold within a single HTTP request lifecycle) and at what
  scale (concurrent requests, corpus size) the mirror's file-read approach
  is expected to fail to meet it.
- **Offline/no-service-on-recall-path tension**: any promoted design must
  explicitly resolve how a runtime API coexists with the files-canonical and
  no-service-on-recall-path constraints that caused OQ-3 to lock against it
  in v1 — e.g., the API could be an optional accelerant layered on top of
  the mirror (mirror remains the offline-readable fallback; API only serves
  live/at-scale consumers), rather than a wholesale replacement.
- **Cache invalidation**: how the API's resolved state gets invalidated or
  recomputed when the underlying `rights_record`/`rights_extension` changes
  (e.g., a `next_review_at` re-review, a terms amendment, a `rights_failure`
  event).
- **Relationship to DI-RIGHTS-3 (surveillance loop)**: a runtime resolution
  API and a surveillance/re-review scheduler (see
  `rights-surveillance-loop.md`) are related but distinct capabilities — the
  API resolves rights status on read; the surveillance loop proactively
  re-evaluates on a schedule. A promoted design should clarify whether one
  depends on or duplicates the other.

### v1 Constraint

In v1, there is no runtime resolution API. Rights status is read exclusively
from the `rights_summary` mirror captured on `source_card`/`source_assertion`
at capture time, backed by the authoritative `rights_record` family on disk.
Any consumer needing current-as-of-now rights status must re-run capture or
consult the authoritative schema files directly; there is no live query
service.

---

## Notes for Promotion

- Before scoping this, confirm the promotion trigger has actually fired: a
  real consumer with a genuine sub-request-latency-at-scale requirement,
  not a hypothetical one. Building this speculatively contradicts the
  plan's stated rationale for choosing the mirror ("no-service-on-recall-path
  constraint; a run must be readable offline").
- Any promoted design must show how it does not regress the
  files-canonical / offline-readability guarantees that caused OQ-3 to lock
  against a runtime API in the first place — most likely by keeping the
  mirror as an offline fallback and treating the API as an additive,
  optional acceleration layer for high-scale consumers only.
- Cross-reference the parent plan's Phase 0 rights substrate schemas
  (`rights_record`, `rights_extension`, `content_reuse_assessment`,
  `permission_record`, `rights_failure`) before scoping the API's response
  shape — the API should resolve against those schemas, not invent a
  parallel representation.
