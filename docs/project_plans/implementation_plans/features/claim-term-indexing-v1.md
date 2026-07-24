---
title: 'Implementation Plan: Claim Term Indexing'
schema_version: 2
doc_type: implementation_plan
it_schema: 1
status: approved
created: '2026-07-24'
updated: '2026-07-24'
feature_slug: claim-term-indexing
feature_version: v1
tier: 2
prd_ref: docs/project_plans/PRDs/features/claim-term-indexing-v1.md
plan_ref: null
scope: Attach a deterministic write-time term/usage-role index (_term_index) to claim_ledger.yaml
  claims, propagate it read-only through export -> catalog -> search -> serve -> runs-viewer,
  and backfill existing pediatric-CDS bundles, with zero impact on verification, identity
  hashing, or rights governance.
effort_estimate: 12 pts
architecture_summary: P1 write-path core (vocab + matcher + classifier + claim-map
  attach, guard-tested inert) gates P2 read-model propagation (export 1.7 + catalog_terms
  + search/serve); P3 backfill and P4 runs-viewer surfaces fork from P2 in parallel
  on disjoint files; P5 closes docs and deferred-item specs.
related_documents:
- .claude/worknotes/claim-term-indexing/decisions-block.md
- docs/project_plans/design-specs/claim-term-indexing.md
- docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-feasibility-brief.md
- docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-charter.md
references:
  user_docs: []
  context:
  - .claude/context/key-context/debugging-patterns.md
  specs:
  - .claude/skills/workflow-authoring/SKILL.md
  related_prds:
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
spike_ref: null
adr_refs:
- docs/dev/architecture/adr-rights-entity-model.md
deferred_items_spec_refs: []
findings_doc_ref: null
charter_ref: docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-charter.md
changelog_ref: null
changelog_required: true
test_plan_ref: null
plan_structure: unified
progress_init: auto
owner: nick
contributors: []
priority: medium
risk_level: medium
category: features
tags:
- implementation
- planning
- phases
- tasks
- claim-term-indexing
- catalog
- vocabulary
milestone: null
commit_refs: []
pr_refs: []
files_affected:
- vocab/pediatric-terms.yaml
- src/research_foundry/services/claim_mapping.py
- src/research_foundry/schemas/claim_ledger.schema.yaml
- src/research_foundry/schemas/report_frontmatter.schema.yaml
- src/research_foundry/services/export_service.py
- docs/dev/architecture/rf-run-export-schema.json
- src/research_foundry/services/catalog_service.py
- src/research_foundry/services/term_index_backfill.py
- src/research_foundry/cli_commands.py
- src/research_foundry/api/routers/catalog.py
- frontend/runs-viewer/src/lib/run-export.ts
- frontend/runs-viewer/src/components/AssertionCatalog/AssertionCatalogPane.tsx
- frontend/runs-viewer/src/screens/CatalogScreen.tsx
- frontend/runs-viewer/src/components/ClaimLedger/ClaimLedgerTable.tsx
planning_maturity: scoped
open_questions:
- q: 'OQ-B (design spec): should search_text in catalog_items also carry canonical
    term aliases, or is catalog_terms the only new query surface in v1?'
  owner: backend-architect
  status: deferred-to-v2
decisions:
- decision: 'D1: v1 = claims only, open schemas only (claim_ledger.yaml + report_frontmatter
    rollup); strict families untouched'
  rationale: Zero schema-contract risk; strict-family extension needs explicit version
    bump + sign-off
  status: locked
- decision: 'D2: everything under namespaced non-authoritative _term_index.* with
    vocabulary_version; never a bare usage_role; never in SOURCE_ASSERTION_MATERIAL_FIELDS'
  rationale: Audit-safety next to real pediatric_cds threshold blocks; stays outside
    all verification/identity/rights paths
  status: locked
- decision: 'D3: per-row sensitivity_rank on catalog_terms; read-time filter rank
    <= threshold'
  rationale: One deterministic write pass; per-row filtering mirrors _redact_evidence_points()
    and avoids the flat-search_text leak precedent
  status: locked
- decision: 'D4: project-scoped versioned vocab/*.yaml (pediatric-v1 first), optional
    RF-core defaults; hand-maintained v1'
  rationale: Resolves OQ-1 pragmatically; MeSH/UMLS/LOINC import deferred
  status: locked
- decision: 'D5: CARP-adapted case-folded word-boundary matcher; no Aho-Corasick until
    vocab >~200 terms'
  rationale: Reuse proven in-repo primitive; no new dependency for small-vocab v1
  status: locked
- decision: 'D6: usage roles v1 = rule-based + pediatric_cds structured-field keying
    only; no model-derived roles'
  rationale: Keeps the index deterministic and reproducible; model enrichment is a
    v2 conditional gate
  status: locked
- decision: 'D7: run.json export lands as additive schema 1.7; runs-viewer run-export.ts
    types bump in the same phase'
  rationale: Hand-written exporter/types silently drop unknown fields unless updated
    together
  status: locked
- decision: 'D8: rf verify stays a pure non-consumer of _term_index in v1 (no lint
    warning added)'
  rationale: Keeps the empirically-validated byte-identical inertness property as
    a hard regression target
  status: locked
- decision: 'OQ-A resolved: CI regression fixture suite scoped to >=2 runs (the 87-claim
    pediatric ledger + one additional synthetic/small fixture) covering both a populated
    and a zero-hit vocabulary case'
  rationale: Satisfies PRD OQ-4/AC-3 minimum breadth without gating v1 on a full production
    fixture sweep
  status: locked
- decision: 'OQ-C resolved: --term/--role are repeatable flags, AND semantics across
    distinct flags, OR semantics within repeats of the same flag, mirroring the existing
    --item_type/--project filter pattern'
  rationale: Consistency with catalog_service.py:1263-1298's existing multi-value
    filter convention
  status: locked
- decision: 'OQ-D resolved: vocab/*.yaml is jsonschema-validated at claim-map load
    time; malformed vocab fails closed (raises, blocks claim-map), a missing vocab
    file warns and skips indexing (claims still produced without _term_index)'
  rationale: Fail-closed on malformed data prevents silently-wrong indexing; warn-and-skip
    on missing file keeps claim-map from becoming newly load-bearing on vocab file
    presence
  status: locked
- decision: 'OQ-E resolved: report_frontmatter rollup field is sized inside P1 (TASK-1.5),
    computed as a union of terms/roles across a report''s claims at the same write
    time as claim-map, not deferred'
  rationale: PRD FR-8 names it a v1 (Should) target and the data is already in memory
    once P1's claim-level index exists
  status: locked
decision_gates: []
success_metrics:
- 100% of claim_ledger.yaml claim items written by claim-map after this feature ships
  carry a _term_index.vocabulary_version stamp
- 0 status flips in rf verify output across a >=2-run fixture regression suite before/after
  _term_index injection
- source_assertion_fingerprint() output is byte-identical with and without an injected
  _term_index key (dedicated regression test, 100% pass, gates CI)
- rf catalog search --term <x> returns every claim in the rebuilt catalog matching
  <x> post-backfill against a fixture set with a known term census
- catalog_terms rows never expose a term derived from an evidence_point whose sensitivity_rank
  exceeds the requesting read's threshold
contributors_note: null
scores: {}
acceptance_criteria: []
execution_mode: agent
agent_title: "Claim Term Indexing v1 \u2014 implementation plan"
agent_summary: Deterministic write-time _term_index on claims, propagated read-only
  through export/catalog/search/serve/runs-viewer, with a dry-run-safe backfill; all
  leaves route to ica-executor (claude-sonnet-5[1m]), gates stay claude-native.
wave_plan:
  serialization_barriers: []
  phases:
  - id: P1
    depends_on: []
    isolation: shared
    parallelizable: false
    owner_skills: []
    files_affected:
    - vocab/pediatric-terms.yaml
    - src/research_foundry/services/claim_mapping.py
    - src/research_foundry/schemas/claim_ledger.schema.yaml
    - src/research_foundry/schemas/report_frontmatter.schema.yaml
  - id: P2
    depends_on:
    - P1
    isolation: shared
    parallelizable: false
    owner_skills: []
    files_affected:
    - src/research_foundry/services/export_service.py
    - docs/dev/architecture/rf-run-export-schema.json
    - src/research_foundry/services/catalog_service.py
    - src/research_foundry/cli_commands.py
    - src/research_foundry/api/routers/catalog.py
    - frontend/runs-viewer/src/lib/run-export.ts
  - id: P3
    depends_on:
    - P2
    isolation: shared
    parallelizable: true
    owner_skills: []
    files_affected:
    - src/research_foundry/services/term_index_backfill.py
    - src/research_foundry/cli_commands.py
  - id: P4
    depends_on:
    - P2
    isolation: shared
    parallelizable: true
    owner_skills:
    - frontend-design
    files_affected:
    - frontend/runs-viewer/src/components/AssertionCatalog/AssertionCatalogPane.tsx
    - frontend/runs-viewer/src/screens/CatalogScreen.tsx
    - frontend/runs-viewer/src/components/ClaimLedger/ClaimLedgerTable.tsx
  - id: P5
    depends_on:
    - P3
    - P4
    isolation: shared
    parallelizable: false
    owner_skills: []
    files_affected:
    - CHANGELOG.md
    - docs/project_plans/design-specs/claim-term-indexing.md
  waves:
  - - P1
  - - P2
  - - P3
    - P4
  - - P5
---

# Implementation Plan: Claim Term Indexing (v1)

**Plan ID**: `IMPL-2026-07-24-claim-term-indexing`
**Date**: 2026-07-24
**Author**: implementation-planner (ICA-routed sonnet leaf, per decisions block §8)
**Human Brief**: N/A — not created; the Opus decisions block (`.claude/worknotes/claim-term-indexing/decisions-block.md`) is the equivalent planning-lens artifact for this Tier 2 feature.
**Related Documents**:
- **PRD**: `docs/project_plans/PRDs/features/claim-term-indexing-v1.md`
- **Design Spec**: `docs/project_plans/design-specs/claim-term-indexing.md`
- **Decisions Block**: `.claude/worknotes/claim-term-indexing/decisions-block.md`
- **ADRs**: `docs/dev/architecture/adr-rights-entity-model.md`

**Complexity**: Medium (Tier 2)
**Total Estimated Effort**: 12 points
**Target Timeline**: Single execution window, 5 sequential/forked phases

## Executive Summary

`_term_index` is a namespaced, additive, non-authoritative field computed once at `claim-map` write time (P1) and copied forward read-only through `export`, `catalog`, `search`, and `serve` (P2) — never recomputed, never model-derived, never touching identity hashing or verification. P1's guard tests (fingerprint regression + verify byte-inertness) are an entry-blocking exit gate for every downstream phase: nothing propagates until the index is proven inert. P3 (backfill of 7 verified pediatric-CDS bundles) and P4 (runs-viewer facets/badges) fork off P2 in parallel on disjoint file sets, then join at P5 (docs + deferred-item design specs + karen gate). All leaf implementation routes to `ica-executor` (`claude-sonnet-5[1m]`, flat legs only); every phase gate (`task-completion-validator`) and the end-of-feature check (`karen`) stay claude-native per the decisions block's MUST-stay verdict-class routing.

## Implementation Strategy

### Architecture Sequence

Domain-specific sequence (not the generic DB→API→UI layering — this feature is a single-writer, multi-reader propagation contract):

1. **Write-path core (P1)** — vocabulary format/loader, deterministic matcher, rule-based usage-role classifier, `claim-map` attach point, guard tests.
2. **Read-model propagation (P2)** — export schema bump, catalog DDL + rebuild extension, search/serve facet plumbing.
3. **Backfill (P3)** — idempotent dry-run-safe reindex of existing bundles.
4. **Presentation (P4)** — runs-viewer facet/badge/deep-link surfaces.
5. **Finalization (P5)** — docs, deferred-item design specs, symbol graph, karen gate.

### Parallel Work Opportunities

- **P3 ∥ P4**: disjoint file ownership (`src/research_foundry/services/*` + CLI vs `frontend/runs-viewer/*`); both depend only on P2's frozen contract (schema 1.7 fields + `catalog_terms` table + search/serve params). No serialization barrier exists between them — confirmed no shared file in either phase's `files_affected`.
- P1 and P2 must sequence: P2 copies fields P1 defines; P2 and P3/P4 must sequence for the same reason.

### Critical Path

P1 → P2 → P5, with P3 and P4 forking off P2 and both joining before P5. P1's guard-test exit gate (TASK-1.6) is the single hardest blocking dependency in the whole plan — nothing in P2 begins until it passes.

### Phase Summary

| Phase | Title | Estimate | Target Subagent(s) | Model(s) | Notes |
|-------|-------|----------|--------------------|----------|-------|
| P1 | Vocabulary + Write-Path Core | 3 pts | ica-executor (python-backend-engineer profile) | claude-sonnet-5[1m] (ICA) | Entry-blocking guard tests gate P2; single flat leaf, no nested agents |
| P2 | Read-Model Propagation | 4 pts | ica-executor (python-backend-engineer profile) + ica-executor (data-layer-expert profile) for `catalog_terms` DDL | claude-sonnet-5[1m] (ICA) | Highest-risk phase; run-export.ts type bump rides with the backend leaf (D7 dual-update) |
| P3 | Backfill | 2 pts | ica-executor (python-backend-engineer profile) | claude-sonnet-5[1m] (ICA) | Parallel with P4; modeled on `rights_backfill.py` |
| P4 | runs-viewer Surfaces | 2 pts | ica-executor (ui-engineer-enhanced profile) | claude-sonnet-5[1m] (ICA) | Parallel with P3; frontend-only file ownership |
| P5 | Finalization | 1 pt | ica-executor (documentation-writer profile) | claude-sonnet-5[1m] (ICA) | Docs + 3 deferred-item design-spec stubs |
| gates (every phase) | Phase gate review | — | task-completion-validator | claude sonnet | MUST-stay verdict class; never offloaded |
| end | Feature reality check | — | karen | claude opus | End-of-feature gate before merge |
| **Total** | — | **12 pts** | — | — | — |

**Model column conventions**: all leaf work is `claude-sonnet-5[1m]` via ICA free-tier offload per operator directive; fallback chain is native `claude/claude-sonnet-5` if ICA errors/overloads mid-leaf (re-dispatch the whole leaf — leaves are single-phase and restartable). No external (Codex/Gemini) legs planned; debug escalation to `gpt-5.6-terra` only after 2+ failed Claude cycles.

## Deferred Items & In-Flight Findings Policy

### Deferred Items

Every deferred item below has a corresponding design-spec authoring task in P5 (DOC-D1..DOC-D4); resulting paths append to `deferred_items_spec_refs`.

#### Deferred Items Triage Table

| Item ID | Category | Reason Deferred | Trigger for Promotion | Target Spec Path |
|---------|----------|-----------------|-----------------------|-----------------|
| PRD-OQ-2 | dependency-blocked | Model-assisted usage-role enrichment (its own `usage_role_model_version` stamp) is a conditional-go gate distinct from v1's rule-based clearance; not required for v1 go-ahead | A rule-based classifier miss-rate high enough to justify a model pass, with an explicit reproducibility-gating proposal | `docs/project_plans/design-specs/term-index-model-assisted-roles-v2.md` |
| PRD-OQ-3 | dependency-blocked | Extending `_term_index` onto `canonical_claim`/`inference_record`/`source_assertion` requires an explicit schema-version bump + `backend-architect` sign-off against `adr-rights-entity-model.md`'s strictness discipline; v1 scope is claims-only by locked decision D1 | A concrete v2 use case needing term data on inferences/reports/source cards, with architect sign-off secured | `docs/project_plans/design-specs/term-index-strict-schema-extension-v2.md` |
| PRD-OQ-1 (residual) | backlog | Controlled-vocabulary sourcing (MeSH/UMLS/LOINC) beyond the hand-maintained `vocab/pediatric-terms.yaml` list; D4 locks hand-maintained-only for v1 | Hand-maintained vocabulary list outgrows itself (per D4's own stated trigger, roughly >~200 terms per D5) | `docs/project_plans/design-specs/controlled-vocabulary-import-v2.md` |
| Design-spec OQ-B | scope-cut | `search_text` canonical term aliasing (so FTS5 finds "cbc" via "complete blood count") reopens the flat-blob sensitivity question D3/FR-11 was written to close; v1 default is `catalog_terms` as the only new query surface | A demonstrated recall gap where `catalog_terms` facet search is insufficient and FTS5 substring search on aliased text is specifically requested | `docs/project_plans/design-specs/catalog-search-text-term-aliasing-v2.md` |

*OQ-4 (backfill validation breadth), OQ-A, OQ-C, OQ-D, OQ-E, and the sensitivity-tier derivation mechanics open question are resolved in this plan (see frontmatter `decisions` and TASK-1.1/1.5/1.6/2.3/2.5) and are NOT deferred.*

### In-Flight Findings

Findings doc is NOT pre-created (`findings_doc_ref: null`). Create `.claude/findings/claim-term-indexing-findings.md` only on the first real finding during execution; if load-bearing, add a DOC-006-equivalent task and append to `deferred_items_spec_refs`.

### Quality Gate

P5 cannot seal until: all 4 deferred items above have a design-spec path in `deferred_items_spec_refs` (or explicit N/A with rationale), and, if `findings_doc_ref` populated, that doc is `accepted`.

## Phase Breakdown

**Column conventions**: `Estimate` = story points. `Model` = `sonnet` (via ICA `claude-sonnet-5[1m]` unless noted). `Effort` = `adaptive` | `extended` for claude leaves (never a size estimate; see `.claude/skills/planning/references/multi-model-guidance.md`).

---

### Phase 1: Vocabulary + Write-Path Core

**Dependencies**: None (wave 1)
**Assigned Subagent(s)**: ica-executor (python-backend-engineer profile) — single flat leaf, no nested agents
**Entry criteria**: none
**Exit criteria**: TASK-1.6 guard tests green — **entry-blocking for P2**

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|-------|--------|--------------|
| TASK-1.1 | Vocabulary file format + loader | Create `vocab/pediatric-terms.yaml` (canonical term ID → surface-form aliases, e.g. `cbc: ["CBC", "complete blood count"]`); loader stamps `vocabulary_version`; jsonschema-validate the file at load time (OQ-D resolved: malformed vocab fails closed and blocks claim-map; a missing vocab file warns and skips indexing, claims still produced without `_term_index`) | Loader returns a versioned vocabulary dict from a valid file; malformed file raises with a clear error and blocks claim-map; missing file logs a warning and claim-map proceeds with `_term_index` omitted, not errored | 0.5 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | None |
| TASK-1.2 | Deterministic term matcher | Adapt CARP's case-folded, word-boundary substring/token matcher (`catalog_retrieval.py:385-419`) as a pure function taking claim `text` + loaded vocabulary, returning matched canonical term IDs; no Aho-Corasick dependency per D5 | Matcher is unit-testable in isolation with no I/O; matches surface-form aliases case-insensitively at word boundaries; returns `[]` for zero-hit text without error | 0.5 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | TASK-1.1 |
| TASK-1.3 | Usage-role classifier | Rule-based classifier: (a) regex context-window around a matched term (comparative operators/numeric adjacency ⇒ `threshold`; bare mention ⇒ `background`); (b) `pediatric_cds` structured `threshold{value,units_ucum}` field keying, classified directly from existing structured extraction with no new extraction step. No model/embedding call anywhere (D6, FR-3) | Classifier is a pure function; a term inside a `pediatric_cds` threshold block classifies `threshold` deterministically from the structured field, not regex; a bare background mention classifies `background`; zero model calls, verified by absence of any LLM client import in the module | 0.5 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | TASK-1.1 |
| TASK-1.4 | Attach `_term_index` in `claim_mapping.build_claim_ledger` | Wire TASK-1.2/1.3 into `build_claim_ledger` (`services/claim_mapping.py`); write `_term_index: {terms: [...], usage_roles: {...}, vocabulary_version: str}` per claim item under the single namespaced key; never emit a bare `usage_role` field anywhere (D2, FR-4, FR-5) | Every claim in a freshly-built `claim_ledger.yaml` carries `_term_index.vocabulary_version` when the vocab file loads; a claim with zero vocabulary hits still passes schema validation with an empty or absent `_term_index` (AC-1 resilience); grep confirms no bare `usage_role` key anywhere in output | 0.5 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | TASK-1.2, TASK-1.3 |
| TASK-1.5 | `report_frontmatter` rollup field | Add an additive, namespace-consistent `_term_index`-shaped rollup field to `report_frontmatter.schema.yaml` (union of terms/roles across a report's claims), computed at the same write time as claim-map (OQ-E resolved: sized in P1, not deferred). Update `claim_ledger.schema.yaml`/`report_frontmatter.schema.yaml` docs to describe the new additive key (both already `additionalProperties: true`; no strictness change) | Rollup field present on report frontmatter for a fixture report with >=1 claim carrying `_term_index`; schema validation passes for both a populated and an absent rollup field | 0.5 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | TASK-1.4 |
| TASK-1.6 | Guard tests — fingerprint regression + verify byte-inertness (ENTRY-BLOCKING EXIT GATE) | (a) Dedicated regression test asserting `source_assertion_fingerprint()` (`assertion_identity.py:16-21`) is byte-identical with and without an injected `_term_index` key, failing loudly if `_term_index` (or any future derived field) is ever added to `SOURCE_ASSERTION_MATERIAL_FIELDS`. (b) Fixture-based `rf verify` before/after regression suite covering >=2 runs (OQ-A resolved: re-encode the empirical 87-claim pediatric ledger fixture + one additional small/synthetic fixture covering a zero-vocabulary-hit claim), asserting byte-identical console output, unchanged 17-check table, 0 status flips | Both tests are new, named, and gate CI; (a) fails if a future PR adds `_term_index` to the material-fields tuple; (b) passes on both fixtures with 0 status flips and byte-identical `verification_status` | 0.5 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | TASK-1.4, TASK-1.5 |

**Validation commands**:
```bash
PYTHONPATH=<execution-worktree>/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/services/test_claim_mapping_term_index.py tests/services/test_assertion_identity_term_index_regression.py tests/services/test_verify_byte_inertness.py -v
```

**Phase 1 Quality Gates:**
- [ ] `_term_index` writes deterministically with zero model/network calls (grep-verified)
- [ ] Fingerprint regression test (AC-2) gates CI and fails loudly on a future material-fields change
- [ ] Verify byte-inertness fixture suite (>=2 runs, AC-3/OQ-A) passes with 0 status flips
- [ ] Malformed vocab fails closed; missing vocab warns and skips (OQ-D)
- [ ] task-completion-validator review passed — **P2 does not start until this gate is green**

---

### Phase 2: Read-Model Propagation

**Dependencies**: Phase 1 complete (guard tests green)
**Assigned Subagent(s)**: ica-executor (python-backend-engineer profile), ica-executor (data-layer-expert profile) for the `catalog_terms` DDL if split needed
**Entry criteria**: TASK-1.6 passed
**Exit criteria**: TASK-2.7 sensitivity + idempotency tests green

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|-------|--------|--------------|
| TASK-2.1 | `export_run` additive `_term_index` field | Extend `export_run` (`export_service.py:668-694`) to additively include `_term_index` in `run.json`; bump `rf-run-export-schema.json` to schema version **1.7** (additive-only, six prior bumps precedent). **FE handles missing field AC (R-P2)**: a claim with no `_term_index` (pre-backfill legacy data) exports without error — field is optional, not required | `run.json` includes `_term_index` for indexed claims; a 1.6-shaped consumer fixture still parses 1.7 output without error (backward-compat test); a legacy claim with no `_term_index` exports cleanly | 0.75 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | Phase 1 |
| TASK-2.2 | runs-viewer `run-export.ts` type bump (seam task, R-P3) | **integration_owner: ica-executor (python-backend-engineer profile)** — same leaf as TASK-2.1 per D7's dual-update rule (small TS edit rides with the backend leaf, per decisions block §2 note). Add `_term_index` to the hand-written `run-export.ts` types so the field is not silently dropped | `run-export.ts` types include `_term_index` matching schema 1.7's shape; a run.json fixture with `_term_index` populated round-trips through the exporter without a dropped field (this is the R-P2 "FE handles missing X" counterpart for the type layer: an absent field types as optional, not required) | 0.5 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | TASK-2.1 |
| TASK-2.3 | `catalog_terms` DDL + per-row `sensitivity_rank` | Add `catalog_terms(catalog_item_id, term, role, run_id, sensitivity_rank)` join table mirroring `catalog_links` (`catalog_service.py:192-199`); each row carries the `sensitivity_rank` of the claim/evidence point it derives from (D3) — never a single flat blob computed once at max-permissive tier, which would repeat the `search_text` leak precedent (`catalog_service.py:541-563`, `_redact_evidence_points` at `:1215-1234`) | `catalog_terms` schema created in `rebuild_schema()` (`:1186`); a fixture item with evidence points at two different sensitivity ranks produces two distinct-ranked rows, not one blob at the max tier | 1.0 pts | ica-executor (data-layer-expert profile) | sonnet | adaptive | Phase 1 |
| TASK-2.4 | `_build_claim_and_inference_rows` extension + rebuild wiring | Extend `_build_claim_and_inference_rows` (`:567-620`) to carry `_term_index` fields into `catalog_terms` rows at the sensitivity rank established by TASK-2.3; wire into the same `rebuild()`/`rebuild_schema()` pass as `catalog_items` (`:313`) | Running `rf catalog rebuild` regenerates `catalog_terms` rows fully from source `claim_ledger.yaml` files (file-is-truth doctrine); rebuild is idempotent — a second rebuild with unchanged source produces identical rows | 0.75 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | TASK-2.3 |
| TASK-2.5 | `rf catalog search --term`/`--role` facets (OQ-C resolved) | Add repeatable `--term`/`--role` filters against `catalog_terms`, following the existing `--item_type`/`--project` multi-value filter pattern (`catalog_service.py:1263-1298`). Semantics: AND across distinct flags, OR within repeats of the same flag (locked decision, OQ-C) | `rf catalog search --term cbc` returns every claim whose `_term_index.terms` contains `cbc` post-rebuild, including alias-canonicalized matches; combining `--term`/`--role` with `--item_type`/`--project` narrows correctly (AND), not silently ignored | 0.5 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | TASK-2.4 |
| TASK-2.6 | `rf serve` term/role passthrough | `api/routers/catalog.py` passes `--term`/`--role`-equivalent query params through to the catalog layer with zero new read-path computation (FR-13) | `rf serve`'s catalog endpoint accepts `term`/`role` query params and returns results matching the CLI's `rf catalog search --term/--role` output for the same fixture | 0.25 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | TASK-2.5 |
| TASK-2.7 | Sensitivity-threshold tests + rebuild idempotency (EXIT GATE) | serve-api sensitivity tests at each threshold level, testing the serve layer (not just the service layer) per the known sensitivity-threshold-router-gate diagnostic trap (list-ok/detail-404 signature); plus a `catalog_terms` rebuild idempotency test | 0 terms exposed above the requesting read's sensitivity threshold at any tested tier (redaction-parity test, AC-5); a second rebuild with unchanged source and unchanged vocabulary version produces 0 diff | 0.25 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | TASK-2.6 |

**Validation commands**:
```bash
PYTHONPATH=<execution-worktree>/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/services/test_export_service_term_index.py tests/services/test_catalog_terms_sensitivity.py tests/api/test_serve_catalog_term_facets.py -v
cd frontend/runs-viewer && npx tsc -p tsconfig.app.json --noEmit
```

**Phase 2 Quality Gates:**
- [ ] `run.json` schema 1.7 is additive-only; a 1.6-shaped consumer still parses it (AC-4)
- [ ] `run-export.ts` types bumped in the same phase (D7 dual-update, no dropped field)
- [ ] `catalog_terms` rows respect per-row `sensitivity_rank`; serve-api tests pass at each threshold (AC-5, Risk 1 mitigation)
- [ ] `rf catalog search --term/--role` and `rf serve` equivalent return matching results (AC-6)
- [ ] Rebuild idempotency confirmed
- [ ] task-completion-validator review passed

---

### Phase 3: Backfill

**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: ica-executor (python-backend-engineer profile)
**Parallel with**: Phase 4 (disjoint file ownership — no shared file in either phase's `files_affected`)
**Entry criteria**: P2 exit gate green
**Exit criteria**: TASK-3.4 idempotency/non-clobber tests green

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|-------|--------|--------------|
| TASK-3.1 | `term_index_backfill.py` service | New service modeled directly on `services/rights_backfill.py`: dry-run by default, idempotent, additive-only, re-runs the deterministic claim-map extraction function (TASK-1.2/1.3) against existing `claim_ledger.yaml` files and writes `_term_index` in place. Never touches `verification_status`, `status`, or any already-attested field (FR-14) | Dry-run mode prints an accurate diff of claims that would gain `_term_index` with zero writes; wet-run writes only the new namespaced key | 1.0 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | Phase 2 |
| TASK-3.2 | CLI wiring + `rf catalog rebuild` follow-up | Wire the backfill into `cli_commands.py` as a new subcommand; document the mandatory `rf catalog rebuild` follow-up pass so derived catalog tables regenerate from the newly-additive source files (file-is-truth doctrine, `builder_service.reindex_all_drafts()` precedent) | CLI subcommand runs dry-run and wet-run modes; help text names the mandatory rebuild follow-up | 0.25 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | TASK-3.1 |
| TASK-3.3 | Validate against pediatric-CDS bundle population | Exercise the backfill's dry-run mode against the 7 existing pediatric-CDS bundles (highest-stakes corpus, private data repo per data-plane split); review the dry-run diff before any wet run; wet-run first against fixtures only in this task | Dry-run diff against the real 7-bundle population is reviewed and recorded; wet run against fixtures produces the expected `_term_index` additions with 0 unexpected writes | 0.5 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | TASK-3.2 |
| TASK-3.4 | Idempotency + non-clobber tests (EXIT GATE) | Re-running the backfill against an already-indexed ledger with an unchanged vocabulary version is a no-op (0 writes); before/after `rf verify` regression on the real 87-claim pediatric-CDS ledger confirms no status change; an interrupted-then-re-run backfill converges to the same end state with no duplicate/partial writes | All three properties (idempotency, verify-unchanged, interrupt-safe convergence) hold in test (AC-7) | 0.25 pts | ica-executor (python-backend-engineer) | sonnet | adaptive | TASK-3.3 |

**Validation commands**:
```bash
PYTHONPATH=<execution-worktree>/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/services/test_term_index_backfill.py -v
```

**Phase 3 Quality Gates:**
- [ ] Dry-run mode is the default; wet run requires explicit flag
- [ ] Idempotent against an unchanged vocabulary version (0 writes on rerun)
- [ ] `verification_status`/`status`/attested fields never touched (Risk 4 mitigation)
- [ ] Dry-run diff against the real 7-bundle pediatric-CDS population reviewed before any wet run
- [ ] task-completion-validator review passed

---

### Phase 4: runs-viewer Surfaces

**Dependencies**: Phase 2 complete
**Assigned Subagent(s)**: ica-executor (ui-engineer-enhanced profile)
**Parallel with**: Phase 3 (disjoint file ownership)
**Entry criteria**: P2 exit gate green
**Exit criteria**: TASK-4.4 tsc + runtime-smoke gate green

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|-------|--------|--------------|
| TASK-4.1 | `AssertionCatalogPane.tsx` terms facet chip-row | Add a "terms present" facet chip-row sourced from `catalog_terms`, wired into the existing facet-driven filter row (`search.data?.facets`, `AssertionCatalogPane.tsx:53-114`) | target_surfaces: [`frontend/runs-viewer/src/components/AssertionCatalog/AssertionCatalogPane.tsx`]. Facet chips render from live catalog data when terms exist; with no vocabulary hits on an item, the facet renders an empty/omitted state, not an error (R-P2 FE-handles-missing-field AC) | 0.5 pts | ica-executor (ui-engineer-enhanced) | sonnet | adaptive | Phase 2 |
| TASK-4.2 | `CatalogScreen.tsx` `?term=` deep-link | Add a `?term=CBC` deep-link parameter to `CatalogScreen.tsx` (`:448-497`), filtering the existing `useCatalogSearch` tab query | target_surfaces: [`frontend/runs-viewer/src/screens/CatalogScreen.tsx`]. Navigating to `?term=CBC` pre-filters the catalog view to matching items; absence of the param behaves exactly as today (no regression) | 0.5 pts | ica-executor (ui-engineer-enhanced) | sonnet | adaptive | Phase 2 |
| TASK-4.3 | `ClaimLedgerTable.tsx` term/role badge | Add a term/usage-role column or badge (currently zero term/tag columns, confirmed gap) sourced from `_term_index.usage_roles`, visually distinct from any real `pediatric_cds` structured threshold value (namespace-boundary reinforcement, D2/FR-15) | target_surfaces: [`frontend/runs-viewer/src/components/ClaimLedger/ClaimLedgerTable.tsx`]. Badge renders next to, not overlapping, a real `pediatric_cds` threshold display; a claim with no `_term_index` renders no badge, not an empty/error badge | 0.5 pts | ica-executor (ui-engineer-enhanced) | sonnet | adaptive | Phase 2 |
| TASK-4.4 | `tsc` clean + runtime smoke across every target_surface (EXIT GATE, R-P4) | Run `tsc -p tsconfig.app.json --noEmit` (the real gate — plain `npx tsc --noEmit` is a no-op in this repo); runtime-smoke the dev build against all three target_surfaces from TASK-4.1/4.2/4.3 plus a desktop >=1440px screenshot per PRD AC-8's visual-evidence requirement | `tsc -p tsconfig.app.json --noEmit` exits 0; runtime smoke confirms facet chip-row, `?term=` deep link, and term/role badge all render from live catalog data on `AssertionCatalogPane.tsx`, `CatalogScreen.tsx`, and `ClaimLedgerTable.tsx` respectively; screenshot captured | 0.5 pts | ica-executor (ui-engineer-enhanced) | sonnet | adaptive | TASK-4.1, TASK-4.2, TASK-4.3 |

**Validation commands**:
```bash
cd frontend/runs-viewer && npx tsc -p tsconfig.app.json --noEmit
```

**Phase 4 Quality Gates:**
- [ ] `tsc -p tsconfig.app.json --noEmit` clean (not the no-op `npx tsc --noEmit`)
- [ ] Runtime smoke covers all three target_surfaces (AssertionCatalogPane, CatalogScreen, ClaimLedgerTable)
- [ ] Term/role badge visually distinct from real `pediatric_cds` threshold values
- [ ] Missing-`_term_index` state renders empty/omitted, never an error or misleading zero-value badge
- [ ] Desktop >=1440px screenshot captured per AC-8 visual-evidence requirement
- [ ] task-completion-validator review passed

---

### Phase 5: Finalization

**Dependencies**: Phase 3 and Phase 4 complete
**Assigned Subagent(s)**: ica-executor (documentation-writer profile)
**Entry criteria**: P3 and P4 exit gates green
**Exit criteria**: all deferred items have design-spec paths; karen end-of-feature gate

| Task ID | Task Name | Description | Acceptance Criteria | Estimate | Subagent(s) | Model | Effort | Dependencies |
|---------|-----------|-------------|-------------------|----------|-------------|-------|--------|--------------|
| DOC-001 | CHANGELOG entry | Add `[Unreleased]` entry per Keep A Changelog format for `_term_index` write-time indexing + `--term/--role` catalog facets | Entry exists under `[Unreleased]`; `changelog_ref` set to `CHANGELOG.md` | 0.1 pts | ica-executor (documentation-writer) | sonnet | adaptive | P3, P4 |
| DOC-002 | CLI reference + architecture note | Document `rf catalog search --term/--role`, the `vocab/*.yaml` format, and the `_term_index` namespace contract; update `docs/dev/architecture/rf-run-export-schema.json`'s changelog for the 1.7 bump | CLI reference reflects the new flags; run-export schema doc lists the 1.7 bump with rationale | 0.15 pts | ica-executor (documentation-writer) | sonnet | adaptive | P3, P4 |
| DOC-003 | Update design spec + PRD frontmatter | Set design spec (`docs/project_plans/design-specs/claim-term-indexing.md`) `status: implemented`; set this plan's `plan_ref` field on the PRD; populate this plan's `commit_refs`/`files_affected`/`updated` | Frontmatter across PRD/design-spec/plan is internally consistent post-ship | 0.1 pts | ica-executor (documentation-writer) | sonnet | adaptive | P3, P4 |
| DOC-D1 | Deferred design spec — model-assisted usage-role enrichment (PRD-OQ-2) | Author `docs/project_plans/design-specs/term-index-model-assisted-roles-v2.md`, `maturity: idea`, `prd_ref` set to this feature's PRD, describing the `usage_role_model_version` gating process named in OQ-2 | Design spec exists; path appended to `deferred_items_spec_refs` | 0.1 pts | ica-executor (documentation-writer) | sonnet | adaptive | P3, P4 |
| DOC-D2 | Deferred design spec — strict-schema extension (PRD-OQ-3) | Author `docs/project_plans/design-specs/term-index-strict-schema-extension-v2.md`, `maturity: idea`, describing the schema-version-bump + `backend-architect` sign-off path for `canonical_claim`/`inference_record`/`source_assertion` | Design spec exists; path appended to `deferred_items_spec_refs` | 0.1 pts | ica-executor (documentation-writer) | sonnet | adaptive | P3, P4 |
| DOC-D3 | Deferred design spec — controlled vocabulary import (PRD-OQ-1 residual) | Author `docs/project_plans/design-specs/controlled-vocabulary-import-v2.md`, `maturity: idea`, describing MeSH/UMLS/LOINC import once the hand-maintained vocab list outgrows itself | Design spec exists; path appended to `deferred_items_spec_refs` | 0.05 pts | ica-executor (documentation-writer) | sonnet | adaptive | P3, P4 |
| DOC-D4 | Deferred design spec — `search_text` term aliasing (design-spec OQ-B) | Author `docs/project_plans/design-specs/catalog-search-text-term-aliasing-v2.md`, `maturity: idea`, naming the sensitivity-leak risk that must be resolved before this is attempted | Design spec exists; path appended to `deferred_items_spec_refs` | 0.05 pts | ica-executor (documentation-writer) | sonnet | adaptive | P3, P4 |
| DOC-005 | Symbol graph regen | Regenerate `ai/symbols-*.json` via `/analyze:symbols:symbols-update` to reflect new/changed modules (`term_index_backfill.py`, catalog/export/claim-map extensions) | Symbol graph reflects new modules and functions | 0.05 pts | ica-executor (documentation-writer) | sonnet | adaptive | DOC-001..DOC-D4 |
| GATE-001 | karen end-of-feature reality check | Full-feature validation: all 8 PRD ACs, all P1-P4 exit gates, deferred-item specs, docs — cut through claimed-vs-actual completion before merge | karen report shows no unresolved gaps; if gaps found, they route back to the relevant phase, not silently accepted | — | karen | claude opus | extended | DOC-005 |

**Validation commands**:
```bash
PYTHONPATH=<execution-worktree>/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/ -k "term_index" -v
cd frontend/runs-viewer && npx tsc -p tsconfig.app.json --noEmit
```

**Phase 5 Quality Gates:**
- [ ] CHANGELOG `[Unreleased]` entry present
- [ ] All 4 deferred items have design-spec paths in `deferred_items_spec_refs` (none N/A — all 4 have concrete v2 specs per the triage table)
- [ ] Findings doc finalized if any findings captured, else N/A
- [ ] Design spec + PRD frontmatter consistent post-ship
- [ ] Symbol graph regenerated
- [ ] karen end-of-feature gate passed

---

## Wrap-Up: Feature Guide & PR

Triggered automatically once Phase 5's quality gates pass.

**Step 1 — Feature Guide**: delegate to `documentation-writer` (haiku or ICA sonnet) to write `.claude/worknotes/claim-term-indexing/feature-guide.md` (What Was Built / Architecture Overview / How to Test / Test Coverage Summary / Known Limitations, <200 lines), frontmatter `doc_type: feature_guide`, `prd_ref`/`plan_ref` set. Commit before opening the PR.

**Step 2 — Open PR**: `gh pr create` with a title ≤70 chars, a summary derived from this plan's Executive Summary, and a Test Plan checklist covering: `pytest` P1-P3 suites, `tsc -p tsconfig.app.json --noEmit`, runtime smoke on P4's three target_surfaces, and the dry-run backfill diff review.

## Model & Effort Assignment

All leaf implementation routes to `ica-executor` at `claude-sonnet-5[1m]` per operator directive (delegation-router RoutingRecord logged per task); reviewer gates (`task-completion-validator`, `karen`) stay claude-native — MUST-stay verdict class, never offloaded. Effort is `adaptive` for all claude leaves (no task in this plan needs `extended` reasoning beyond the karen end-gate). See `.claude/skills/planning/references/multi-model-guidance.md` for the canonical effort vocabulary; do not use codex/gemini effort values (`low`/`medium`/`high`) on a claude task.

## Risk Mitigation

Carried forward from the decisions block §3, with phase-level enforcement:

| Risk | Impact | Likelihood | Mitigation | Enforced in |
|------|--------|------------|-------------|--------------|
| Sensitivity leak via derived term rows (repeats the flat-`search_text` precedent) | High | Medium | D3 per-row `sensitivity_rank`; serve-layer tests at each threshold, not just service-layer | TASK-2.3, TASK-2.4, TASK-2.7 |
| Identity-hash / verify-gate regression | High (likelihood low, impact critical) | Low | P1 guard tests entry-blocking for P2; D8 keeps verify a pure non-consumer | TASK-1.6 |
| Export/viewer schema drift (`run.json` 1.7) | Medium | Medium | D7 dual-update in the same P2 leaf; real gate is `tsc -p tsconfig.app.json --noEmit` | TASK-2.1, TASK-2.2 |
| Backfill against verified production bundles | Medium | Medium | `rights_backfill` pattern (dry-run default, idempotent, additive-only); reviewed dry-run diff before any wet run | TASK-3.1, TASK-3.3, TASK-3.4 |
| ICA leaf process/quality hazards (orphaned leaves, long-session instability, fail-open shortcuts only reviewers catch) | Medium (process) | Medium | `timeout -k` on every dispatch; one phase per leaf, never a marathon; claude-native validator per phase non-negotiable; worktree-interpreter-correct pytest invocation | Every phase's validation commands + gate |

## Success Metrics

From PRD §4/11 (unchanged by this plan — see frontmatter `success_metrics` for the machine-readable list):
- 100% of post-ship claims carry `_term_index.vocabulary_version`.
- 0 `rf verify` status flips across the >=2-run fixture regression suite.
- `source_assertion_fingerprint()` byte-identical, 100% pass, gating CI.
- `rf catalog search --term <x>` recall matches a known fixture census.
- 0 sensitivity-tier leaks on `catalog_terms` at any tested threshold.

## Progress Tracking

Progress files auto-generate per phase at `.claude/progress/claim-term-indexing/phase-N-progress.md` (`progress_init: auto`). One file per phase, per the project's documentation policy.

---

**Implementation Plan Version**: 1.0
**Last Updated**: 2026-07-24
