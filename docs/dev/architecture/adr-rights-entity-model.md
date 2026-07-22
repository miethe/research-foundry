---
title: "ADR: Rights & Evidence-Item Entity Model"
doc_type: adr
status: accepted
schema_version: 1
created: 2026-07-21
updated: 2026-07-21
feature_slug: rights-entity-model
resolves: ["OQ-RF-1", "OQ-RF-2", "OQ-RF-3", "OQ-RF-4"]
related_docs:
  - docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md
  - docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md
  - .claude/worknotes/rights-entity-model/decisions-block.md
  - docs/project_plans/design-specs/rights-surveillance-loop.md
  - docs/project_plans/design-specs/rights-counsel-workflow.md
  - docs/project_plans/design-specs/rights-runtime-resolution-api.md
owner: nick
---

# ADR: Rights & Evidence-Item Entity Model

## Status

**Accepted** (2026-07-21) — Records Research Foundry's adoption of the
pediatric-anemia-site "Source Reuse & Rights Governance Spec v1.0" entity
model as RF's own canonical substrate, the ten §9 schema-conflict
adjudications applied at port time, and the four capability layers (C1–C4)
built on top of it across Phases P0–P5 of the `rights-entity-model-v1`
implementation plan.

---

## Context

The pediatric-anemia-site project — an RF consumer — handed back a
capability request asking Research Foundry to own a rights/licensing/
provenance entity model at the platform level, rather than have every
consuming content repo re-derive it. The handoff shipped a verified v1.0
spec and five JSON Schemas (`rights_record`, `rights_extension`,
`content_reuse_assessment`, `permission_record`, `rights_failure`), together
with a §9 review section flagging ten schema-conflict defects in that
baseline.

**Load-bearing context correction**: the v1.0 spec and its schemas were
authored and adversarially verified *in the pediatric-anemia-site repo*.
None of them existed in the RF product repo prior to this feature — RF was
greenfield for `rights_record`/`rights_extension`. This ADR therefore
records a two-part decision: (1) port the v1.0 substrate into RF's own
`schemas/*.schema.yaml` registry as Phase 0, fixing the ten §9 defects at
the source rather than carrying them forward as debt, and (2) layer four
requested capabilities on top of RF's existing evidence entities
(`source_card`, `source_assertion`):

- **C1 — `rights_summary` mirror**: a denormalized, non-authoritative
  rights summary attached to every captured source/evidence entity.
- **C2 — Evidence-quality taxonomy**: `evidence_item_type` +
  `judgment_basis`, an axis independent of rights.
- **C3 — `derived_synthesis` provenance**: first-class support for
  RF-authored synthesis content, with a human-only attestation ceiling.
- **C4 — Capture-time emission + substitutability**: `rights_summary` is
  emitted at capture time (not backfilled), with terms snapshotting and
  substitute-source discovery.

Candidates considered for C1 (per the handoff's own review and RF's
files-canonical constraints):

| Candidate | Description | Verdict |
|-----------|-------------|---------|
| **Denormalized entity-level mirror** | `rights_summary` object attached directly to `source_card`/`source_assertion`; `mirror_is_authoritative` const `false` | **Selected (v1)** |
| **Runtime rights-resolution API** | A live service resolves rights at read time via a join against `rights_record` | Deferred (OQ-RF-3) — see Known Gaps / Deferred Items |
| **No rights modeling on evidence entities** | Leave rights entirely to consuming repos | Rejected — defeats the handoff's purpose; re-derivation is the problem being solved |

The mirror was selected because RF is files-canonical and a run must remain
readable offline without a live service on the recall path — the same
constraint that governs `docs/dev/architecture/adr-runs-read-path.md`'s
static-export decision.

---

## Decision

**Schema-first architecture, ported substrate + four capability layers,
authorization boundary enforced at the service layer.**

1. **Phase 0 — Rights substrate port.** Five schemas
   (`rights_record.schema.yaml`, `rights_extension.schema.yaml`,
   `content_reuse_assessment.schema.yaml`, `permission_record.schema.yaml`,
   `rights_failure.schema.yaml`) are ported into RF's own
   `schemas/*.schema.yaml` registry and wired into `schemas.py`. The **only**
   intended deltas from the verified v1.0 baseline are the ten §9
   adjudication rows below — this is a field-by-field port, not a redesign.
2. **Phase 1 — Evidence taxonomy (C2).** `source_assertion.schema.yaml`
   gains a sibling `extensions.evidence_taxonomy` block carrying
   `evidence_item_type` (7-member, domain-extensible enum) and
   `judgment_basis` (default `unassessed`), independent of
   `rights_extension` (§9.1).
3. **Phase 2 — `rights_summary` mirror + validator (C1).** `source_card`
   and `source_assertion` gain a denormalized `rights_summary` object
   (`mirror_is_authoritative` const `false`). A time-parameterized
   divergence validator, `rights_validation.py::check_rights_divergence`,
   accepts a required `--as-of` parameter and never calls
   `datetime.now()`/`time.time()`/`date.today()` — reproducibility is a
   correctness invariant, not a performance optimization.
4. **Phase 3 — `derived_synthesis` provenance (C3).** A `synthesis` object
   on `source_assertion` (`input_refs` minItems 2, `attestation.status` ∈
   `{candidate, attested}`) supports RF-authored first-party content.
   `attestation.status: attested` is human-only, fail-closed, and proven
   unreachable by any agent-writable code path via a dedicated negative
   test (closes one of the two §9.10 write paths).
5. **Phase 4 — Capture-time emission + substitutability (C4).** `capture.py`
   emits a fail-closed `rights_summary` (`agent_triage_only`) at capture
   time — no backfill sweep required. Terms are content-addressed and
   hashed at snapshot time; a `substitutability` object (including
   `no_substitute_found`) supports substitute-source discovery.
6. **Phase 5 — Governance gate + this ADR.** `governance.py` gains a guard
   rule; `verification.py` calls it at verify time (resolves the
   implementation plan's decisions-block OQ-6: the gate is policy, enforced
   at governance layer, fired at verify layer). This closes the **other**
   §9.10 write path (`rights_record.overall_status`,
   `content_reuse_assessment.decision.status`,
   `content_reuse_assessment.decision.release_gate`) via an independent
   negative test. No new tables, services, or daemons are introduced
   outside RF's existing file-backed control-plane pattern.

### §9 Schema-Conflict Adjudications

These ten rows are the core design value-add of this feature: each was a
defect or ambiguity in the pediatric-anemia-site v1.0 baseline, surfaced by
the handoff's own §9 review, and adjudicated here as the **only** intended
deltas applied during the Phase 0 port. Reused verbatim from the planning
decisions block (`.claude/worknotes/rights-entity-model/decisions-block.md`)
as the binding source of truth; not re-derived.

| ID | Conflict (handoff §9) | RF Adjudication (locked) | Owning Phase |
|----|------------------------|---------------------------|--------------|
| §9.1 | `evidence_item_type`/`judgment_basis` taxonomy can't ride inside `rights_extension` | New sibling `extensions.evidence_taxonomy` block on `source_assertion`; taxonomy is never nested under rights — rights and evidence-quality are independent axes | P1 |
| §9.2 | `access.basis` enum lacks an `unknown` member, forcing a guess instead of a fail-closed default | Add `unknown` as a default member | P0 |
| §9.3/§9.4 | TDM / model-training permissions modelled twice across `access.*` and `contract.*` with incompatible enum shapes | Single canonical restriction-permission enum (`allowed \| allowed_with_conditions \| prohibited \| not_addressed \| unknown`) used consistently across all TDM/model-training fields; drop the duplicate | P0 |
| §9.5 | `rights_record` cannot describe first-party/owned content — no `source_id`, no `OWNED` status | Add `record_scope: first_party`, `overall_status: OWNED`, and a conditionally-optional `source_id` (nullable when `record_scope == first_party`) so first-party synthesis records validate | P0 |
| §9.6 | `format: uri` is advisory-only under many validators (fail-open); a nullable-empty `contract: {}` implies "no restriction" (also fail-open) | §9.6a: replace `format: uri` with `pattern: "^https?://"` on all terms/license URL fields. §9.6b: when `contract` is non-null, all restriction sub-fields become required (each still accepting `unknown`); an empty `{}` fails validation rather than defaulting to cleared | P0 |
| §9.7 | `review_status` enum diverges between `rights_record.review` and `content_reuse_assessment.review` | Reconcile to one canonical 6-member `review_status` vocabulary (superset, includes `legal_review_required_before_commercial_use`), shared textually by both schemas; a P6 consistency test asserts byte-identical enum lists (no cross-file `$ref` — `SchemaRegistry` has no resolver support today; adding one is deferred as YAGNI) | P0/P5 |
| §9.8 | `component_type` enum diverges between `rights_record.component_decisions[]` and `content_reuse_assessment.component` | Single canonical `component_type` set (adopts the `content_reuse_assessment` singular style, adds missing `abstract`/`supplementary_material` members); both schemas use the identical enum, verified by a P6 identity test | P0 |
| §9.9 | A prior amendment invalidated shipped v1.0 examples plus their `validation_report`/checksums | **Moot for RF** — RF ports schema *structure* only, never the pediatric-repo's vendored JSON example files, so there is no RF-side instance of this defect; documented as such in P6 | P6 |
| §9.10 | The `CLEARED_*`/`counsel_approved` prohibition in the v1.0 baseline guarded only one of two enum write paths | Guard **both** write paths — `synthesis.attestation.status` (P3) and `rights_record.overall_status`/`content_reuse_assessment.decision.status`/`decision.release_gate` (P5) — each proven fail-closed to non-agent-writable values by an independent, non-duplicate negative test. Neither test alone proves the boundary; both must pass | P3/P5 |
| OQ-RF-2 | Is `evidence_item_type` a clinical/domain-specific concept or a general base axis? | Ship the 7-member enum (`observed_finding \| reference_interval_value \| equation_or_method \| guideline_recommendation \| instrument_or_questionnaire \| bibliographic_metadata \| derived_synthesis \| other`) as a domain-general **base axis**, explicitly documented as extensible via `other` and future additive members — not a closed clinical list a downstream domain (e.g. Evidence-Foundry) would need to replace rather than specialize | P1 |

### Load-Bearing Invariants

These invariants are enforced architecturally and tested at each phase
gate. They may not be relaxed without a superseding ADR.

#### Invariant 1 — Fail-Closed Authorization Boundary (§9.10)

> **`CLEARED_*` / `counsel_approved` / `attestation.status: attested` values
> are human-only. No agent-reachable code path, under any input, may
> produce one — over either of the two enum write paths.**

- Write path A: `synthesis.attestation.status` — guarded and negative-tested
  in Phase 3 (enumerates every write path in `services/source_cards.py` and
  `services/capture.py`).
- Write path B: `rights_record.overall_status` /
  `content_reuse_assessment.decision.status` /
  `content_reuse_assessment.decision.release_gate` /
  `rights_extension.clearance_status` — guarded and negative-tested
  independently in Phase 5.
- The boundary is only proven closed once **both** negative-test suites
  pass; neither is treated as sufficient on its own (by design — independent
  verification of both paths, not one test covering both).

#### Invariant 2 — Non-Authoritative Mirror (C1 / OQ-RF-3)

> **`rights_summary` is a denormalized mirror. `mirror_is_authoritative` is
> a schema `const: false`. No code path may treat the mirror as the source
> of truth for a rights decision.**

- `rights_record` remains the single authoritative record; `rights_summary`
  exists only to make rights machine-checkable at the recall path without a
  join.
- `check_rights_divergence(paths, *, as_of, ...)` is the sanctioned drift
  detector. It is time-parameterized (`--as-of` required) and never reads
  wall-clock time, so two invocations with the same `--as-of` and unchanged
  inputs produce byte-identical output.

#### Invariant 3 — Independent Evidence-Quality Axis (§9.1)

> **`evidence_item_type` and `judgment_basis` live in
> `extensions.evidence_taxonomy`, a sibling block. Neither field is
> reachable via any `rights_extension`-rooted path.**

- Rights and evidence-quality are orthogonal axes; conflating them (as the
  v1.0 baseline structurally risked) would force every consumer that only
  cares about one axis to reason about both.

---

## OQ-RF-1..4 Resolutions

This ADR is the single citable resolution to `OQ-RF-1` through `OQ-RF-4`.

| OQ | Question | Resolution | Rationale |
|----|----------|------------|-----------|
| **OQ-RF-1** | Does Research Foundry accept the pediatric-anemia-site entity model as authored, or counter-propose a different shape? | **Accept as authored.** This PRD/ADR is the acceptance vehicle; no counter-proposal. | The handoff's v1.0 spec was independently, adversarially verified in the pediatric-anemia-site repo before handoff. Re-deriving an alternative shape would discard that verification for no structural gain — RF's own corrections are scoped to the ten §9 defects, not the overall model. |
| **OQ-RF-2** | Is `evidence_item_type` a base-layer concept or an Evidence-Foundry domain specialization? | **Base axis.** Ships as a domain-general 7-member enum on `source_assertion`, kept extensible via `other` and future additive members. | A closed clinical enum would force any non-clinical RF consumer (or a future Evidence-Foundry specialization) to fork the field rather than extend it. The base axis + extension mechanism keeps RF domain-neutral while still supporting clinical use today. |
| **OQ-RF-3** | Should the entity-level `rights_summary` mirror exist, or will RF guarantee a fast runtime resolution API instead? | **Denormalized mirror**, for v1. Runtime resolution API deferred (see Known Gaps / Deferred Items). | RF's files-canonical + no-service-on-recall-path constraint requires a run to be readable offline. A runtime API would put a live service on the recall path — the same trade-off `adr-runs-read-path.md` resolved in favor of static export for the runs viewer. A resolution API is a larger, separate infra investment; promote it only if mirror drift or live cross-run resolution needs become a real maintenance burden (see `docs/project_plans/design-specs/rights-runtime-resolution-api.md`, referenced as `DI-RIGHTS-1`). |
| **OQ-RF-4** | Where does the terms snapshot live — does RF host it, or only the hash? | **RF run directory**, hash + content-addressed snapshot artifact stored locally; not exported/shipped. External hosting deferred. | Matches the files-canonical pattern used everywhere else in RF (evidence bundles, claim ledgers). External hosting is a distinct storage/ops decision, not a design question this feature needs to answer; recorded as `DI-RIGHTS-2`. |

---

## Known Gaps

Two open questions from the planning decisions block are **explicitly not
resolved by implementation** in this feature. Both are record-the-debt:
the schema ships the field that names the gap, but the executing loop or
role is deliberately not built. Each has a dedicated future design spec.

### OQ-RF-5 — Rights-terms surveillance execution

**Gap**: `rights_record.next_review_at` is present in the ported schema
(§9.5/Phase 0), but nothing in this feature re-checks it. There is no
scheduled loop that re-verifies terms against `next_review_at`, diffs
against a prior snapshot, or raises an alert when a rights term lapses.
`check_rights_divergence` (Phase 2) flags a stale `next_review_at` relative
to its `--as-of` argument as a non-fatal "stale" result — it does **not**
execute a re-check.

**Design spec**: see
`docs/project_plans/design-specs/rights-surveillance-loop.md`
(task **P6-8b** of the `rights-entity-model-v1` implementation plan). This
spec is the sanctioned venue for designing the scheduled re-check loop
against `next_review_at` before it is built — do not build the execution
loop against this ADR alone.

### OQ-RF-6 — Counsel / rights-owner role

**Gap**: Invariant 1 above enforces that `CLEARED_*`/`counsel_approved`/
`attestation.status: attested` are human-only by **exclusion** — no agent
identity is authorized to write them — not by a positive, named role. There
is no existing RF counsel/rights-owner role, permission scope, or attestation
workflow anywhere upstream today. "Human-only" currently means "not any
known agent identity," which is a correct but coarse authorization
boundary.

**Design spec**: see
`docs/project_plans/design-specs/rights-counsel-workflow.md`
(task **P6-8c** of the `rights-entity-model-v1` implementation plan). This
spec is the sanctioned venue for designing a formal rights-owner/counsel
role and attestation workflow before one is built — the current
human-only-by-exclusion boundary should not be read as "no role is ever
needed," only as "no role has been designed yet."

### Other deferred items (named, not gaps in this ADR's scope)

- **Runtime rights-resolution API** (`DI-RIGHTS-1`, OQ-RF-3 alternative) —
  `docs/project_plans/design-specs/rights-runtime-resolution-api.md`.
- **Terms-snapshot external hosting** (`DI-RIGHTS-2`, OQ-RF-4) — covered in
  this ADR (Invariant/resolution above); no separate spec, since hosting is
  a storage/ops decision rather than a design question.
- **Cross-file `$ref`/shared `$defs` support in `SchemaRegistry`**
  (`DI-RIGHTS-5`) — YAGNI for v1; the §9.7/§9.10 duplicated-enum +
  consistency-test pattern closes the drift risk without new
  schema-loading infrastructure.

---

## Consequences

### Positive

- RF now owns a single canonical rights/evidence-taxonomy model; the
  pediatric-anemia-site consumer (and any future consumer) can reference
  RF's schemas by ID instead of re-deriving its own parallel copy.
- All ten §9 defects from the v1.0 baseline are fixed at the schema level
  in RF's port — consumers inherit the fixes for free rather than carrying
  the defects forward as debt.
- The fail-closed authorization boundary (Invariant 1) is proven by two
  independent negative-test suites over both known write paths, closing
  the exact gap the handoff's own §9.10 review flagged as unguarded.
- The `rights_summary` mirror preserves RF's offline-readable-run guarantee
  — the same file-first principle recorded in `adr-runs-read-path.md`.
- `evidence_item_type`/`judgment_basis` (C2) is a genuinely reusable,
  domain-general contribution — not clinical-specific — usable by any
  future RF-adjacent domain.

### Negative / Trade-offs

- The mirror is denormalized: `rights_summary` can drift from its
  authoritative `rights_record` if a consumer writes around the intended
  update path. `check_rights_divergence` detects this but does not prevent
  it structurally — it is a validator, not a database constraint.
- §9.7/§9.10's duplicated-enum approach (rather than a shared `$ref`) means
  two schemas must be kept manually in sync; a consistency test catches
  drift but does not prevent an author from editing one enum and forgetting
  the other before the test runs.
- Surveillance execution (OQ-RF-5) and a counsel/rights-owner role
  (OQ-RF-6) are named, real gaps — `next_review_at` is currently decorative
  data with no consumer, and "human-only" is enforced by absence of agent
  authorization rather than a positive role check. Both are explicit,
  intentional scope cuts for v1, not oversights.
- A runtime rights-resolution API and external terms-snapshot hosting
  remain out of scope; any consumer requiring sub-request-latency rights
  resolution at scale, or terms access without RF run access, is not served
  by this feature as shipped.

### Overall

Porting the verified v1.0 substrate into RF's own schema registry — fixing
the ten §9 defects at the source — and layering C1–C4 on top gives RF a
canonical, fail-closed rights and evidence-quality model without
re-litigating the pediatric-anemia-site handoff's underlying design. The
two named gaps (surveillance execution, counsel role) are deliberately
deferred to their own design specs rather than built speculatively inside
this feature.
