---
schema_version: 2
doc_type: spike
leg: tech
feature_slug: claim-term-indexing
status: complete
confidence: 0.82
created: 2026-07-23
---

# Tech Leg — Claim Term Indexing

## Feasibility

**feasible-with-constraints.** A deterministic term index can be computed entirely at
write time (claim-map / synthesize) from a static vocabulary + regex/token matching
against claim/assertion `text`, stored as plain YAML fields, and propagated read-only
through export → catalog → search. No schema in the pipeline forbids additive fields
except the strict `additionalProperties: false` families (`canonical_claim`,
`inference_record`, `source_assertion`), which need an explicit property added rather
than free-form passthrough.

## Integration points (per rf stage)

- **extract** (`rf extract`, cheap-model fact extraction) — unaffected. Term indexing
  should NOT live here; it's model-driven and non-deterministic across providers.
- **claim-map** (`services/claim_mapping.py:1-30`, `build_claim_ledger`) — **primary
  attach point.** Docstring already states "No network or model is required"
  (`claim_mapping.py:6-8`); this is the natural deterministic pass to add
  `terms: [str]` (+ optional `usage_roles: [{term, role}]`) per claim before
  `claim_ledger.yaml` is written. `schemas/claim_ledger.schema.yaml` claim items are
  `additionalProperties: true` (`claim_ledger.schema.yaml:23-113`) so this is additive,
  no migration of the schema contract needed (existing bundles just lack the field).
- **synthesize/inference** — `inference_log.yaml` / `canonical_claim` /
  `inference_record` entities derive from claim text too; `inference_record.schema.yaml`
  and `canonical_claim.schema.yaml` are `additionalProperties: false`
  (`inference_record.schema.yaml:8`, `canonical_claim.schema.yaml:8`) — adding
  `terms`/`usage_roles` here requires an explicit schema edit, not a free passthrough.
  `source_assertion.schema.yaml` is the same (`:8`).
- **verify** (`cli_commands.py:444 def verify`) — should stay a **consumer, not a
  producer**: verify can assert "every claim has a non-empty term index if vocabulary
  hits exist" as a lint, but must not compute usage-role via a model call (that would
  put inference on the verify gate, which already runs strict/hard-gate checks per
  the pediatric_cds precedent — CLAUDE.md "Important Notes"). Keep term computation
  upstream of verify; verify only checks presence/shape.
- **export** (`services/export_service.py:668-694`, `def export_run`) — **must change.**
  `export_run` curates a fixed subset of claim fields into `run.json`
  (`claim_id, text, materiality, claim_type, status, confidence, report_locations,
  sources, persistent_references`; `export_service.py:678-694`) — `terms`/`usage_roles`
  would silently drop unless explicitly added to this curated dict. This is an
  **additive-only** change per the existing machine-surface contract
  (`docs/dev/architecture/machine-surface-inventory.md:29`, "all changes are
  additive-only; no existing output shape changed") — same discipline already used for
  `_stamp()`/`rf_schema_version`.
- **catalog** (`services/catalog_service.py`) — `catalog_items` is an explicitly
  **derived, rebuildable** sqlite3 + FTS5 read model built from `run.json`
  (`catalog_service.py:1-30` docstring: "Deterministic IDs", rebuild always regenerates
  from run artifacts). `_build_claim_and_inference_rows` (`catalog_service.py:567-620`)
  already builds `search_text`/`payload_json` per claim from `export_data`; add
  `terms`/`usage_roles` into both. FTS5 token search (`catalog_service.py:247-249`,
  `catalog_fts` over `title, summary, body`) already gets partial term recall for free
  once terms are folded into `search_text`/`body`, but a normalized facet needs a
  dedicated table (see Proposed data shape) because FTS tokenizes free text, it does
  not canonicalize "complete blood count" → `CBC`.
- **search** (`catalog_app.command("search")`, `cli_commands.py:1474`) — add optional
  `--term`/`--role` facet filters that hit the new term table (WHERE clause), same
  pattern as existing `item_type`/`project` filters (`catalog_service.py:1263-1298`).
  The web-facing `search_router/` package (`services/search_router/router.py`) is a
  **different subsystem** — external query routing (Brave/Tavily/etc. providers,
  `router.py:174 run_search`), not RF's own corpus. It is unaffected and should not be
  confused with `rf catalog search`.
- **serve** (`cli_commands.py:2905 def serve`, `api/routers/catalog.py`) — thin HTTP
  wrapper over `catalog_service`; term/role query params pass through once catalog
  layer supports them. No new read-path computation.
- **Report Builder** (`services/builder_service.py`) — same "file-canonical +
  rebuildable catalog.db" pattern already proven for drafts
  (`builder_service.py:1-30` docstring, `_sync_catalog_index`/`reindex_all_drafts`,
  `builder_service.py:1227-1319`) is the template to replicate for term indexing:
  file is truth, catalog.db row is disposable cache, `rf catalog rebuild` regenerates
  byte-for-byte from files with zero reads of the old index.

## Proposed data shape

**Source of truth (Markdown/YAML):**
- `claim_ledger.yaml` claim item: add `terms: [string]` (canonical vocabulary IDs,
  e.g. `["cbc", "ferritin"]`) and optional `usage_roles: [{term, role}]` where
  `role ∈ {finding, threshold, measurement, background}`. Both computed once at
  claim-map time by a pure function `text -> terms` (vocabulary lookup + regex; no
  model). Same shape extends to `inference_record`/`canonical_claim`/
  `source_assertion` once those strict schemas get the explicit properties added.
- Report-level: `report_frontmatter.schema.yaml` (`additionalProperties: true`,
  line 51) can carry a rolled-up `terms: [string]` (union of covered claims) with zero
  schema risk.

**Derived artifacts (rebuildable, never authoritative):**
- `catalog_items.payload_json`/`search_text` gain the term/role data
  (`catalog_service.py:162-183`).
- New `catalog_terms(catalog_item_id, term, role, run_id)` join table (mirrors
  `catalog_links` shape at `catalog_service.py:192-199`) for exact-facet queries
  (`WHERE term = 'cbc'`) that FTS5 substring/token matching can't guarantee
  (canonicalization, "all claims about CBC" including synonyms mapped to one term id).
  Rebuilt in the same pass as `catalog_items` (`rebuild()`/`rebuild_schema()`,
  `catalog_service.py:313, 1186`).
- `run.json` export gains `terms`/`usage_roles` per claim — additive, versioned under
  the existing `RF_SCHEMA_VERSION` stamp discipline.

## Story-point range

**8–13 points**, reasoning:
- Vocabulary loader + deterministic matcher (pure function, unit-testable): 2–3 pts.
- Wire into `claim_mapping.build_claim_ledger` + `claim_ledger.schema.yaml` doc update:
  1–2 pts.
- Schema edits for `canonical_claim`/`inference_record`/`source_assertion` (strict
  `additionalProperties: false` families) + migration/backfill note: 2–3 pts.
- `export_service.export_run` field passthrough + machine-surface-inventory entry: 1 pt.
- `catalog_service` schema (`catalog_terms` table) + `_build_claim_and_inference_rows`
  wiring + `rebuild()` regen: 2–3 pts.
- `rf catalog search --term/--role` CLI + `api/routers/catalog.py` param passthrough:
  1–2 pts.
- Backfill script for existing 7 pediatric-CDS run bundles (re-run claim-map + catalog
  rebuild, no data loss since it's purely additive): 1 pt (mechanical, given
  `reindex_all_drafts`-style precedent already exists).

Excludes: usage-role *quality* tuning (regex/heuristic refinement is iterative, not
one-time), and any embedding/NER-based term extraction (out of scope per charter;
would violate the deal-killer if it required a model call on read).

## Open questions

- **OQ-1 (vocabulary source):** Where does the pediatric vocabulary
  (WBC/CBC/ferritin/hemoglobin/...) live — a workspace-level `vocab/*.yaml` file
  version-controlled per project domain, or a shared RF-core default list with
  per-project overrides? Not resolved by this leg; assign to priorart or a follow-up
  spike (charter's "vocabulary-source decision" conditional-go path).
- **OQ-2 (usage-role determinism):** The charter frames usage-role as
  "purely data-derived" — this leg confirms a rule-based classifier (e.g. regex for
  numeric-threshold context, comparative-operator adjacency) can stay deterministic
  and off the read path, but does NOT evaluate classifier *accuracy*. That's a
  value/risk-leg question, not a tech-feasibility one.
- **OQ-3 (strict-schema migration):** `canonical_claim`/`inference_record`/
  `source_assertion` are `additionalProperties: false` by deliberate design (rights/
  identity strictness per `adr-rights-entity-model.md`). Adding `terms` there needs
  explicit sign-off that it doesn't weaken the strict-family contract — recommend
  scoping term indexing to `claim_ledger` + `report_frontmatter` (both already
  permissive) for a v1, deferring the strict entities to v2.
- **OQ-4 (backfill cost):** re-running claim-map on 7 existing verified pediatric-CDS
  runs to populate `terms` — confirm this doesn't flip `verification_status` or
  otherwise touch already-attested fields (should be a pure additive rewrite of
  `claim_ledger.yaml`, but needs a risk-leg check against `rf verify` gate replay).

## Deal-killer check

Charter deal-killer: *"the term/usage index... requires a model call on the read/
render path, OR lets agent-writable paths mint authority-bearing annotations that
alter claim verification status."*

**Not triggered.** The proposed design computes terms/roles once, at claim-map write
time, via a pure deterministic function (vocabulary lookup + regex), matching the
existing "no network or model" contract already documented for `build_claim_ledger`
(`claim_mapping.py:6-8`). `catalog_service`/`export_service` only ever copy already-
computed fields forward (`_build_claim_and_inference_rows`,
`export_service.py:668-694`) — no computation on the read path in `rf catalog search`
or `rf serve`. `terms`/`usage_role` are descriptive metadata, not part of the
`verification_status`/`sensitivity`/rights-clearance enums the guard rule
(`no_agent_cleared_rights_value`) protects — they cannot flip a claim's `status` or
mint a `CLEARED_*`/`counsel_approved`/`attested` value.

## Confidence rationale

0.82. High confidence on the *mechanism* (attach point, schema permissiveness at the
claim-ledger/report layer, derived-and-rebuildable catalog pattern already proven twice
in this codebase — `catalog_items` and `catalog_report_drafts`/`builder_service`).
Confidence is capped below 0.9 by three unresolved items outside this leg's scope: (1)
vocabulary-source decision (OQ-1) is a real dependency for "computing" the index at
all — this leg proves *how*, not *from what list*; (2) strict-schema families
(`canonical_claim`/`inference_record`/`source_assertion`) need an explicit
add-property decision I did not make unilaterally (OQ-3); (3) I did not execute code
or run `rf verify`/`rf catalog rebuild` against a live workspace to empirically confirm
the backfill is side-effect-free (OQ-4) — this is inferred from reading
`reindex_all_drafts`/`rebuild()` semantics, not observed.
