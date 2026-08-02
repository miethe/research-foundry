---
title: "ADR: Source Attribution Entity & Export-Time Attribute Propagation"
doc_type: adr
status: proposed
schema_version: 1
created: 2026-08-02
updated: 2026-08-02
feature_slug: source-metadata-propagation
exploration_charter_ref: docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-charter.md
resolves: ["OQ-SMP-1", "OQ-SMP-2"]
related_docs:
  - docs/project_plans/exploration/source-metadata-propagation/spikes/tech-findings.md
  - docs/dev/architecture/adr-rights-entity-model.md
  - schemas/source_card.schema.yaml
  - schemas/source_assertion.schema.yaml
owner: nick
---

# ADR: Source Attribution Entity & Export-Time Attribute Propagation

## Status

**Proposed** (2026-08-02) — records where an assertion *about a source* lives, and where source
attributes are computed for claims and reports. Acceptance happens at the
`source-metadata-propagation` exploration verdict gate, not here.

## Context

This decision exists **regardless of whether the feature ships**. RF already records source-quality
signals write-only and already hydrates a thin attribute set onto claim citations at export, so the
question is not *whether* attributes reach claims but *which entity owns a third-party judgment* and
*at which point the join happens*. Any future work on evidence triage, corroboration, or search
ranking inherits whatever answer is implicit today — and left implicit, an unowned rating drifts into
looking like an RF-authored fact while the propagation point gets re-chosen ad hoc per feature.

## Decision

**1. A new `source_attribution` entity owns third-party assertions about a source**, shaped on the
landed rights-entity-model rather than invented: an authoritative record (`additionalProperties:
false`) plus a denormalized **non-authoritative mirror** on the source card carrying
`mirror_is_authoritative: const false`, a link-before-assert `allOf` (no non-default value without a
linked record id), a typed `*_triage_failure` block, and an `observed_at`/`as_of` divergence validator
that **never reads the wall clock** — the discipline `rights_validation.check_rights_divergence()`
already establishes, and that a cached, time-varying third-party value requires. Corollary: first-party
descriptive metadata (authors, DOI, publisher, version) stays on `source_card.schema.yaml`, where it is
**already modeled** and merely hardcoded empty at the Python boundary; first-party bibliographic facts
read from the source's own text stay in the Reusable Assertion Ledger under the existing
`evidence_item_type: bibliographic_metadata`.

**2. Source attributes are computed for claims and reports at export-time hydration**, in
`export_service._resolve_source()` (`export_service.py:601-661`), fed by `_load_source_cards()`
(`:580-598`) — **not** at claim-map write time. It is a pure file→file dict join persisting no derived
state, recomputed on every export; the sqlite catalog consumes `export_data` delete-then-insert per
run, so the DB stays derived by construction.

**3. Aggregation over N cards carries the set; two monotone rollups sit on top.** The per-citation set
is canonical; conflicts are carried with their asserters, not adjudicated. Only `trust.source_rank` —
the one attribute with a declared total order — gets rollups: `max` as `best_source_rank` ("strongest
evidence behind this claim"; the only aggregate under which a weak corroborating card cannot dilute a
strong one) and `min` as `weakest_source_rank` (the complementary reviewer query). Numeric aggregation
across `assertion_kind`s is **refused** — averaging or summing heterogeneous third-party judgments
yields a number describing nothing, and would be RF minting its own bibliometric judgment.

## Alternatives Considered

**A. Extend `source_assertion.schema.yaml` (the Reusable Assertion Ledger).** *Rejected.* This was the
prior-art leg's recommendation and it is the closest fit — the ledger's subject already *is* a source,
and `bibliographic_metadata` is already an `evidence_item_type`. It fails structurally: (i) **no
asserted-by field** — `extraction_provenance` records the provenance of the *extraction act*, not the
identity of the *asserter*, which is a third-party rating's entire governance value; (ii) a
**mandatory passage anchor** (`source_edition_id` + `passage_id`) a citation count cannot honestly
satisfy — recording one demands minting a synthetic passage, a provenance lie inside the entity whose
job is provenance truth; (iii) the only passage-free escape hatch, `derived_synthesis`, is barred by
`synthesis.input_refs` **`minItems: 2`** against a single-provider value; (iv) attestation is
**write-capped at `candidate`** by `AssertionMaterializer._enforce_synthesis_attestation_ceiling`, so a
third-party fact stays permanently indistinguishable from an unvalidated RF draft. Decisively,
prior-art's own H5 anchor — the rights-entity-model (`17a2cb0`) — **is itself a separate entity with a
card mirror**: the anchor argues for the split, not against it.

**B. Claim-map write-time propagation via the `_term_index` pattern.** *Rejected.* Also prior-art's
recommendation, and a real precedent — but for a different kind of value. `_term_index` derives from
the claim's own **immutable text**, so freezing it into the canonical ledger is sound. An attribution
observes a **mutable external world**: freezing a citation count into `claim_ledger.md` makes the
canonical file stale *without the claim changing*, inverting the ledger's meaning and forcing a
divergence validator over a canonical artifact rather than a mirror. It would also add a general
source-card read dependency to `build_claim_ledger`, which today sees only extraction cards.

**C. Nest third-party ratings directly on the source card, with no separate entity.** *Rejected.* The
card is a single agent-writable document with `additionalProperties: true`; a rating nested there has
no asserter identity, no retrieval evidence, no terms lineage, and no `const false` authorship
invariant — the exact conditions under which a third-party number reads as an RF-authored fact. It
also collapses N asserters disagreeing about one source into one slot, destroying Decision 3's
carry-the-set semantics before they can be applied.

**D. Adopt an external ontology wholesale (PROV-O / nanopublications / W3C Web Annotation).**
*Rejected.* All are RDF/JSON-LD-native and do not embed cleanly in RF's flat YAML front-matter;
adopting the vocabulary means carrying a graph serialization RF has no reader for. **Adopt the shape,
not the vocabulary** — the asserter/observation/subject triad these standards converge on is what
Decision 1's `asserted_by` block encodes, in RF's own idiom.

## Consequences

- **Field placement is constrained.** New capture fields live under `source.*` and `trust.*` on the
  card and **never inside the `pediatric_cds` block**, which is `additionalProperties: false` and
  hard-gated by `rf verify` — an additive field placed there is a schema failure, not a tolerated key.
- **The governance guard must be extended or it is structurally blind.** `_RIGHTS_GOVERNED_FIELDS`
  (`services/governance.py:35-40`) is an explicit **name allowlist** — its own comment: "Enumerated BY
  NAME — do not infer or wildcard this list; future governed fields must be added here explicitly." So
  `no_agent_cleared_rights_value` sees no attribution field unless the new governed paths are added to
  that tuple. Shipping the entity without extending it ships a fail-open hole that looks guarded.
- **Forward-only / no-backfill requires tri-state coverage semantics.** Under the AssertionRegistry
  no-backfill precedent, absent attribution is the majority state indefinitely. Every consumer must
  distinguish **absent** (never assessed), **assessed-and-empty** (looked, found nothing), and
  **present** — collapsing the first two into "no signal" makes coverage unmeasurable and converts a
  gap into a negative finding.
- Existing bundles keep verifying (`verification.py` gates key off named fields only; the card is
  `additionalProperties: true` — risk leg owns the empirical proof over the 7 bundles). The DB gains
  attribute columns but no authority. Third-party *ingestion* is separable and licensing-gated;
  Decisions 1–3 hold with zero such records present.
