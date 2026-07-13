# Assertion Ledger Canonical Contract (P1)

**Status:** implementation contract; assertion-only operation remains required
until later gates authorize otherwise.

## Scope and compatibility boundary

P1 defines durable contract nouns only. It does not create a registry, migrate a
run, enable a feature flag, infer rollout authority, or alter existing
run-local claim identity. Existing Markdown/YAML claim ledgers remain the
authority for their runs. The future catalog is a rebuildable projection.

The contract is additive:

- Legacy `claim_id`, source-card, evidence, report-anchor, and AOS correlation
  fields retain their current meanings.
- A legacy `claims[]` entry need not have a persistent ID. Export preserves
  that absence; it never synthesizes identifiers during a read.
- `persistent_references` is optional on a claim ledger entry and on its
  denormalized export. It may carry edition, passage, assertion/version,
  canonical-claim/version, and inference identifiers when a later phase has
  resolved them.
- Export schema `1.5` adds only that optional claim field. The `1.4` AOS UUID
  fields and `native_aliases.rf_run_id` remain nullable resolver handles; RF
  `run_id` remains canonical.

## Domain objects

All P1 schemas use Draft 2020-12 and `schema_version: "1.0"`.

| Object | Identity and mutability | Required boundary |
|---|---|---|
| `source_edition` | Immutable, content-addressed (`sed_<sha256>`) | A material rendition gets a new edition; source metadata is outside its identity. |
| `passage` | Immutable, content-addressed (`psg_<sha256>`) | Keeps raw and normalized text hashes plus selector and normalizer provenance. |
| `source_assertion` | Immutable, content-addressed (`ast_<sha256>`) with a visible version | Bound to exactly one edition and passage; unknown qualifiers live in `qualifier_extensions`. |
| `assertion_evaluation` | Immutable decision for one assertion version | Records grounding/review outcome without changing source evidence. |
| `assertion_lifecycle_event` | Immutable ordered event | Changes authoritative eligibility before derived-projection reconciliation. |
| `canonical_claim` | Optional, mutable grouping concept with versions | References source assertion IDs and versions; never overwrites source assertions. |
| `inference_record` | Derived, versioned reasoning record | References immutable assertion versions and cannot be represented as a source assertion. |

## Identity and version rules

The executable generator is `sha256-canonical-json-v1`: UTF-8 canonical JSON
with sorted object keys and compact separators. For a source assertion, its
exact payload is the object with these ordered field names:
`source_edition_id`, `passage_id`, `assertion_text_sha256`, `qualifiers`, and
`qualifier_extensions`. Its `identity.fingerprint` must equal the SHA-256 of
that payload and `assertion_id` must be `ast_<fingerprint>`.
`assertion_text_sha256` must itself be the SHA-256 of `assertion_text`.
`identity.material_fields` is a fixed declaration of that v1 payload, not a
caller-chosen list. The registry enforces these cross-field bindings, while the
schema protects their shapes. Source edition identity includes exact material
bytes. Passage identity includes its edition ID, normalized-text hash, raw-text
hash, selector set, and normalizer algorithm/version.

Material changes issue a new edition, passage, or assertion ID. The new object
may point to `predecessor_*`, but the predecessor is never overwritten or
deleted. Mutable concepts (`canonical_claim`, evaluation decisions, lifecycle
state) use opaque IDs plus monotonically increasing versions outside immutable
fingerprints. Persisted IDs and raw content hashes are access-controlled; they
are not public-content handles.

## Lifecycle and invalidation

`assertion_lifecycle_event.sequence` is monotonic for its target and
`idempotency_key` deduplicates delivery. Valid causes are corrected edition,
invalid extraction, formal retraction, manual tombstone, and merge reversal.
The only authoritative assertion transitions are:

```text
eligible -> stale | invalidated | tombstoned
stale -> invalidated | tombstoned
invalidated -> tombstoned
tombstoned -> (none)
```

An event whose target state is `invalidated` or `tombstoned` must contain an
`authoritative_action: block_reuse` and at least one synchronous
`dependent_actions[]` entry whose action is `block_reuse`. This blocks reuse
and current eligible reads before asynchronous reconciliation. Dependent
canonical edges, inferences, reports, runs, and exports are marked
stale; caches/indexes are excluded and purged or rebuilt; downstream writeback
reconciliation is queued default-denied. Contradiction evidence remains
lineage context, not an invalidation cause.

## Canonical grouping, split, and rollback

Canonical claims are optional. With `RF_CANONICAL_CLAIMS_ENABLED=false`, the
system operates assertion-only and omits canonical references. The lifecycle
of a canonical claim is `proposed -> reviewed -> active`, with `split`,
`superseded`, and `rolled_back` states. A `split` or `rolled_back` record must
include non-empty versioned `replacement_claims`, plus `reversal` with its
event ID, reason, recorder/timestamp provenance, and non-empty versioned
`resulting_claims`. The explicit resulting links make reversal auditable even
when a later claim version changes. It retains every source assertion
ID/version and every historic reference, so a report or run can still resolve
the exact evidence it used. No canonical operation is allowed to mutate a
source assertion.

## Implementation seams

Future P2/P3 writers resolve and persist records; P1 only reserves their
contract. `claim_ledger.schema.yaml` accepts the optional
`persistent_references` object. `export_service._build_claims()` forwards it
only when present in the ledger. This preserves exact legacy graph shape
(apart from the producer's top-level export schema-version progression) and
provides a checkable codegen/type seam in the strict export JSON schema and
hand-maintained `RFClaim` type. The viewer generator includes all seven P1
schemas; `pnpm run codegen:check` rejects generated-type drift, and the public
RF type barrel exports both the generated P1 types and
`RFPersistentReferences`.

## Safety invariants

- Do not enable `RF_ASSERTION_LEDGER_ENABLED`, `RF_ASSERTION_REUSE_ENABLED`, or
  `RF_CANONICAL_CLAIMS_ENABLED` as part of this contract phase.
- Unknown qualifiers are preserved in `qualifier_extensions`; dropping them is
  an identity failure, not normalization.
- An `inference_record` is derived reasoning and cannot validate as a
  `source_assertion`.
- Missing durable references mean legacy/assertion-only semantics, never a
  guessed persistent link.
- Workspace authorization, retrieval, ranking, and cache isolation remain
  later-phase responsibilities.
