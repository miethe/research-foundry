---
schema_version: 2
doc_type: design_spec
title: "Claim Term Indexing"
description: "Deterministic, write-time vocabulary/usage-role index over claims (and later inferences/reports/source cards), propagated read-only through export, catalog, and search."
status: draft
maturity: ready
created: 2026-07-23
updated: 2026-07-23
feature_slug: claim-term-indexing
prd_ref: null
related_documents:
  - docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-charter.md
  - docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-feasibility-brief.md
---

# Claim Term Indexing — Design Spec

## Problem Statement

RF's own corpus has no vocabulary-level index. `rf catalog search` answers exact-token substring/FTS5 queries (`catalog_service.py:1259-1340`) but cannot canonicalize synonyms, expose a term facet, or distinguish *how* a term is used (a threshold vs. a background mention). CARP's `required_terms` mechanism (`catalog_retrieval.py:385-449`, `schemas/research_evidence_plan.schema.yaml:111-114`) independently hand-rolled a per-question, query-time workaround for exactly this gap, and its own PRD names the resulting risk: missed synonym matches become residual discovery, not false coverage (`catalog-assisted-research-planning-v1.md:349`). This design proposes a deterministic, write-time term/usage-role index attached to claims first, so that lookup, browse, and CARP's own retrieval quality can be served from stored, versioned, non-authoritative derived data instead of ad hoc per-query scans.

## 1. Data Shape — `_term_index`, Namespaced and Non-Authoritative

The index is a single namespaced key, `_term_index`, added to each claim item. It is **additive, derived, and never authoritative** — it participates in no verification, identity, or rights-governance check.

```yaml
# claim_ledger.yaml, per claim item
_term_index:
  terms: [cbc, ferritin]
  usage_roles:
    cbc: threshold
    ferritin: finding
  vocabulary_version: pediatric-v1
```

Rules, sourced directly from the risk leg's findings:

- **Namespace, never bare `usage_role`**. The risk leg flags a real (non-charter) hazard: a bare `usage_role: threshold` sitting next to a real `pediatric_cds` schema-validated threshold block is a readability/audit hazard even though it is technically inert — a downstream consumer (report writer, CCDash) could mistake a derived label for a clinically-attested one (`risk-findings.md` "Additional Deal-Killers"). All derived fields live under `_term_index.*`, mirroring the "denormalized, non-authoritative" posture already established for the rights-summary mirror (`docs/dev/architecture/adr-rights-entity-model.md`).
- **Outside `SOURCE_ASSERTION_MATERIAL_FIELDS`.** The content-addressed `source_assertion` identity hash is a fixed 5-tuple — `source_edition_id, passage_id, assertion_text_sha256, qualifiers, qualifier_extensions` (`assertion_identity.py:16-21`). `_term_index` must never be added to this tuple; a regression test should assert `source_assertion_fingerprint()` is unchanged when `_term_index` is injected into an instance (empirically validated for `verify` — see §3 below — but identity-hashing itself is a separate code path and should get its own explicit test).
- **v1 scope: open schemas only.** `claim_ledger.yaml` claim items are `additionalProperties: true` (`claim_ledger.schema.yaml:23-113`) and `report_frontmatter.schema.yaml` is likewise permissive (line 51) — both are safe additive targets with zero schema-contract risk. The strict, `additionalProperties: false` families — `canonical_claim.schema.yaml` (`:6,10-13`), `inference_record.schema.yaml` (`:8`), `source_assertion.schema.yaml` (`:8`) — are deliberately closed per `adr-rights-entity-model.md`'s strictness discipline for rights/identity-bearing entities. Extending `_term_index` onto those families requires an explicit schema-version bump and `backend-architect` sign-off; **this is out of scope for v1** (see §7 OQ-3).
- **Versioned, not just deterministic.** Every `_term_index` block carries `vocabulary_version`. A vocabulary edit is itself a reproducibility axis — the risk leg notes no existing precedent stamps this today; the term index introduces one, mirroring CARP's own versioning discipline and the existing `rf_schema_version`/`RF_SCHEMA_VERSION` stamp pattern already used on `run.json`.

## 2. Deterministic Extraction — Write Time, No Read-Path Model Calls

**Vocabulary**: a versioned, project-scoped vocabulary file (e.g. `vocab/pediatric-terms.yaml`), each entry a canonical term ID plus its surface-form aliases (`cbc: ["CBC", "complete blood count"]`). The file is stamped with a `vocabulary_version` that flows into every `_term_index` block computed against it — an edit to the vocabulary produces a new version, never silently mutating historical index output.

**Matching algorithm**: case-folded, word-boundary-aware substring/token matching, directly adapted from CARP's `required_terms` mechanism (`schemas/research_evidence_plan.schema.yaml:111-112`: "case-folded lexical terms every selected candidate's search_text must contain; conservative rule; no semantic/vector matching"), implemented in `catalog_retrieval.py:385-419` / `assertion_catalog.py:199`. The priorart leg's build-vs-adapt recommendation is explicit: reuse this primitive, swapping the caller-supplied `required_terms` list for the fixed, versioned vocabulary, and swapping "does the candidate's `search_text` contain this term" for "does this claim's `text` contain this term," run at write time rather than query time. For vocabularies beyond a few hundred terms, a single-pass multi-pattern matcher (Aho-Corasick, e.g. `pyahocorasick`) is the right algorithmic upgrade — deterministic, O(text length), no NLP dependency (priorart leg, external matches).

**Usage-role determination — two deterministic sources, no model call**:
1. **Lexicon/rule-based classification**: regex context windows around a matched term (comparative operators or numeric adjacency ⇒ `threshold`; bare mention ⇒ `background`), stamped with the vocabulary version. This is the mechanism the tech leg confirms can stay off the read path (`tech-findings.md` OQ-2).
2. **`pediatric_cds` structured fields**: the value leg's strongest finding — the `pediatric_cds` evidence-card schema already structures each finding with `population`/`assay_method`/`threshold{value,units_ucum}` (`schemas/pediatric_cds.schema.json`, `.claude/workflows/rf-pediatric-cds-run-execute.js:63-99`). A term appearing inside a `threshold` block can be classified `threshold` deterministically from the existing structured extraction, without a new extraction step or any inference.

**No read-path model call, by design**: `catalog_service`/`export_service` only ever copy already-computed `_term_index` fields forward (`_build_claim_and_inference_rows`, `export_service.py:668-694`) — there is no computation on the read path in `rf catalog search` or `rf serve`. If a future model-assisted enrichment pass is added (e.g., for terms the rule-based classifier cannot resolve), it must be **write-time, cached, and version-stamped** — its own `usage_role_model_version` field, analogous to `vocabulary_version` — never invoked from a read-time code path. This preserves the charter's deal-killer boundary literally: reproducibility risk from a model-derived role is a named, gated risk (§7 OQ-2), not a violation of the deal-killer itself, provided the model call never executes on read.

## 3. rf CLI Stage Touchpoints

Per the tech leg's stage-by-stage integration analysis:

- **`extract`** — unaffected, deliberately. Term indexing must not live in cheap-model fact extraction; that pass is non-deterministic across providers.
- **`claim-map`** (`services/claim_mapping.py:1-30`, `build_claim_ledger`) — **primary attach point**. The docstring already states "No network or model is required" (`claim_mapping.py:6-8`); this is the natural deterministic pass to compute and write `_term_index` before `claim_ledger.yaml` is persisted.
- **`verify`** (`cli_commands.py:444`) — **no-op / consumer only**, not a producer. `verify_report`'s checks (`verification.py:993-1160`) read only `text`, `sources`, `materiality`, `claim_type`, `status` — `_term_index` is not consumed. This is **empirically confirmed**, not merely inferred: the risk leg's empirical addendum ran a live before/after `rf verify` against a real 87-claim pediatric-CDS ledger (`rf_run_20260717_rf_cbc_001_pediatric_cds_establish`) with an injected `_term_index` field on all 87 claims. Result: byte-identical console output, identical 17-check table, 0 claims changed status, `verification_status: passed` unchanged in both runs. The only diff anywhere was the non-semantic `generated_at` timestamp in the freshly-regenerated `reviews/verification.yaml`. Verify may optionally *lint* for `_term_index` presence when vocabulary hits exist, but must never compute usage-role via a model call on this gate.
- **`export`** (`services/export_service.py:668-694`, `export_run`) — **must change, additively**. `export_run` currently curates a fixed field subset into `run.json` (`claim_id, text, materiality, claim_type, status, confidence, report_locations, sources, persistent_references`) — `_term_index` would silently drop unless explicitly added. This is an additive-only change per the machine-surface contract (`docs/dev/architecture/machine-surface-inventory.md:29`), landing as `run.json` schema **1.7** (the six prior bumps, 1.0→1.6, are all additive/optional-field precedent — `rf-run-export-schema.json:5`).
- **`catalog`** (`services/catalog_service.py`) — `catalog_items` is an explicitly derived, rebuildable sqlite3+FTS5 read model (docstring: "Deterministic IDs... rebuild always regenerates from run artifacts," `catalog_service.py:1-30`). `_build_claim_and_inference_rows` (`:567-620`) already builds `search_text`/`payload_json` per claim; extend both to carry `_term_index`. **Critically, this must not repeat the flat `search_text` sensitivity-leak precedent**: `search_text` is captured once at `client_sensitive` (max-permissive) and is *not* re-filtered per point at read time, while `_redact_evidence_points()` (`:1215-1234`) redacts other fields per-point at read (keyed on `sensitivity_rank`). The term index must be derived per-sensitivity-tier — either computed separately per tier or derived from the post-redaction point set at read time — never folded into a single flat blob computed once at maximum permissiveness. A dedicated `catalog_terms(catalog_item_id, term, role, run_id)` join table (mirroring `catalog_links`, `catalog_service.py:192-199`) supports exact-facet queries (`WHERE term = 'cbc'`) that FTS5 token matching cannot guarantee (it does not canonicalize "complete blood count" → `cbc`), rebuilt in the same pass as `catalog_items` (`rebuild()`/`rebuild_schema()`, `:313, 1186`).
- **`search`** (`catalog_app.command("search")`, `cli_commands.py:1474`) — add optional `--term`/`--role` facet filters against the new term table, following the existing `item_type`/`project` filter pattern (`catalog_service.py:1263-1298`). Distinct from and unaffected by `search_router/` (external provider query routing — a different subsystem entirely, per the tech leg's explicit disambiguation).
- **`serve`** (`cli_commands.py:2905`, `api/routers/catalog.py`) — thin HTTP wrapper; term/role query params pass through once the catalog layer supports them. No new read-path computation.

## 4. Entity Generalization Path

v1 scope is **claims only**, landing in the already-permissive `claim_ledger.yaml` and, as a rolled-up union field, `report_frontmatter.schema.yaml`. Generalizing to `inference_record`, `canonical_claim`, and `source_assertion` — RF's strict, `additionalProperties: false`, rights/identity-bearing entities — is deliberately deferred:

1. **Claims (v1)** — open schema, immediate value, directly serves the pediatric-CDS use case and CARP's `required_terms` quality lever.
2. **Inferences and reports (v2, conditional)** — same data shape, same write-time computation, but requires an explicit schema-version bump plus `backend-architect` review on `inference_record.schema.yaml` and `canonical_claim.schema.yaml`, mirroring the process already proven for six `run.json` bumps. Not blocked technically, only gated on an explicit decision to extend the strict-family contract (§7 OQ-3).
3. **Source cards (v2+, exploratory)** — `source_assertion.schema.yaml` is the most identity-sensitive target (content-addressed hashing); any extension here needs the identity-hash regression test from §1 as a hard precondition, not just a schema bump.

## 5. Backfill of Existing Bundles

Modeled directly on `services/rights_backfill.py` (`:1-25`), which the risk leg names as a directly reusable pattern: **idempotent, additive-only, non-clobbering, dry-run supported**. The term-index backfill script re-runs the deterministic claim-map extraction function against existing `claim_ledger.yaml` files and writes `_term_index` in place — since `claim_ledger.schema.yaml` is already `additionalProperties: true`, this is a pure additive write with zero schema risk at that layer, and the risk leg's empirical addendum directly validates that such a write does not disturb `rf verify`'s status determination. Backfill should:

- Run in **dry-run mode by default**, printing a diff of claims that would gain `_term_index` entries.
- Be **idempotent**: re-running against an already-indexed ledger with an unchanged vocabulary version is a no-op.
- **Never touch `verification_status`, `status`, or any already-attested field** — write only the new namespaced key.
- Follow with a mandatory `rf catalog rebuild` pass (or equivalent) so the derived catalog tables regenerate from the newly-additive source files, per the same "file is truth, catalog.db is disposable" doctrine already proven for `builder_service.reindex_all_drafts()` (`builder_service.py:1227-1319`).
- Be exercised, before any production backfill run, against the pediatric-CDS bundle population specifically, since that is the highest-stakes corpus (clinical decision-support inputs) and the one the empirical addendum already partially validated.

## 6. Term-Centric UX Surfaces (runs-viewer)

The value leg identifies existing UI hosting surfaces with near-zero incremental screen-architecture cost — this is an extension, not a new screen:

- **`AssertionCatalogPane.tsx`** (`frontend/runs-viewer/src/components/AssertionCatalog/AssertionCatalogPane.tsx:53-114`) already has a debounced free-text `searchInput` and a facet-driven filter row wired to `search.data?.facets` (line 83). Add a "terms present" facet chip-row sourced from the new `catalog_terms` table.
- **`CatalogScreen.tsx`** (`frontend/runs-viewer/src/screens/CatalogScreen.tsx:448-497`) tabs `useCatalogSearch` by `item_type` with its own debounced query. Add a `?term=CBC` deep-link parameter and a term/role column or badge on `ClaimLedgerTable.tsx` (currently has zero term/tag columns — confirmed gap, priorart leg exhaustive grep).
- **Usage-role display**: surface `_term_index.usage_roles` as a badge (e.g. "threshold", "finding") next to matched-term chips, visually distinct from any real `pediatric_cds` structured threshold value, to reinforce the non-authoritative namespace boundary from §1.
- No new screen architecture is required; this is additive facet/column/param work on existing catalog and claim-ledger surfaces, consistent with the "narrow, high-leverage precision play" framing from the value leg rather than a new discovery product.

## 7. Open Questions (Carried Forward, Unresolved by This Design)

- **OQ-1 (vocabulary source)** — tech leg. Should the pediatric vocabulary live as a workspace-level `vocab/*.yaml` file per project domain, or as a shared RF-core default list with per-project overrides? Not resolved by any leg; recommend a scoped follow-up decision (or a short spike) before implementation planning locks the vocabulary-loading design. Controlled vocabularies (MeSH, UMLS, LOINC) are a plausible *future* source once a hand-maintained list outgrows itself (priorart leg), not required for v1.
- **OQ-2 (usage-role mechanism reproducibility)** — tech + risk legs. This design commits to a lexicon/rule-based classifier plus `pediatric_cds` structured-field keying for v1 (§2), explicitly ruling out model/embedding-derived roles on the read path. If a future write-time model-assisted enrichment is added, it requires its own `usage_role_model_version` stamp and must be evaluated as a conditional-go gate, not folded into this design's deal-killer clearance.
- **OQ-3 (strict-schema migration)** — tech + risk legs. Extending `_term_index` onto `canonical_claim`, `inference_record`, and `source_assertion` requires an explicit schema-version bump and `backend-architect` sign-off that it does not weaken the strict-family contract established by `adr-rights-entity-model.md`. This design defers that decision entirely to v2 (§4); a future PRD or ADR should make it explicitly rather than inheriting it implicitly from v1's claim-ledger scope.
- **OQ-4 (backfill validation breadth)** — risk leg. The empirical addendum validated verify-gate idempotency against one run, one vocabulary shape (`terms` + `usage_roles` + `vocabulary_version`), on the open-schema `claim_ledger` layer only. It does not by itself prove the closed `canonical_claim` schema or the content-addressed `assertion_identity.py` fingerprinting paths are safe under injection (those remain code-inspection-level per the risk register), and it does not cover `rf bundle`/`rf council` gates. A broader fixture-based CI regression suite covering multiple runs and (once OQ-3 resolves) the strict-family entities is recommended before a production-wide backfill.
- **Sensitivity-tier derivation mechanics (not a leg-numbered OQ, but load-bearing)** — the exact mechanism for deriving `catalog_terms`/`search_text` per-sensitivity-tier rather than once at max-permissive (§3, catalog touchpoint) is named as a risk to avoid, not yet designed in detail. Implementation planning should resolve whether this is computed per-tier at write time (multiple derived rows) or filtered from the post-redaction point set at read time, before catalog schema work begins.
