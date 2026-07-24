---
schema_name: ccdash_document
schema_version: 2
doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans
id: BRIEF-claim-term-indexing
title: "Claim Term Indexing \u2014 Human Brief"
status: draft
category: human-briefs
feature_slug: claim-term-indexing
feature_family: claim-term-indexing
feature_version: v1
prd_ref: docs/project_plans/PRDs/features/claim-term-indexing-v1.md
plan_ref: docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md
intent_ref: null
epic_ref: null
related_documents:
- .claude/worknotes/claim-term-indexing/decisions-block.md
- docs/project_plans/design-specs/claim-term-indexing.md
- docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-feasibility-brief.md
- docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-charter.md
owner: nick
contributors: []
audience:
- humans
priority: medium
confidence: 0.77
created: '2026-07-24'
updated: '2026-07-24'
target_release: null
tags:
- human-brief
- claim-term-indexing
- catalog
- vocabulary
---

# Claim Term Indexing — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-24

---

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/features/claim-term-indexing-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/features/claim-term-indexing-v1.md`
- **Design Spec**: `docs/project_plans/design-specs/claim-term-indexing.md`
- **Decisions Block** (Opus planning scaffold, D1-D8 locked): `.claude/worknotes/claim-term-indexing/decisions-block.md`
- **Feasibility Brief** (go verdict, 0.77): `docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-feasibility-brief.md`
- **Exploration Charter**: `docs/project_plans/exploration/claim-term-indexing/claim-term-indexing-charter.md`
- **Related Briefs**: None

---

## 2. Estimation Sanity Check

**Bottom-up total**: 12 pts / ~1 engineer-week (single execution window, 5 phases)
**Top-down anchor**: CARP P1+P2 (deterministic retrieval + governed propagation, comparable slice) = 9 pts
**Reconciliation**: This plan's total (12) sits within the delta band of the anchor once the two capability areas CARP lacked (UI presentation, production backfill) are counted separately below. Bottom-up and anchor agree in shape (write-core → propagation is the same two-phase spine); the delta is fully attributable to added scope, not underestimation of the shared spine.

H1-H6 heuristic application:

- **H1 (noun-counting)**: 0 new first-class CRUD-with-RBAC domain nouns. `catalog_terms` is a join table mirroring the existing `catalog_links` pattern (no RBAC, no dedicated router) — 0.25-0.5 pt class per the heuristic's own carve-out, not the ~2 pt/noun floor. `vocab/pediatric-terms.yaml` is a file, not a table. **H1 does not raise a floor for this plan.**
- **H2 (dual-implementation multiplier)**: N/A. RF has no local/enterprise repository split for this feature's surface area; no dual-implementation cost applies.
- **H3 (algorithmic flag)**: Flagged — the term matcher (TASK-1.2) and usage-role classifier (TASK-1.3) are algorithmic surface area, not stateless plumbing. Mitigated by two facts the plan already satisfies H3's bar on: (a) the matcher is *adapted* from a proven in-repo primitive (CARP `catalog_retrieval.py:385-419`, D5), not invented from scratch; (b) the plan enumerates ≥5 concrete test scenarios across TASK-1.2/1.3/1.6 (case-insensitive word-boundary alias match, zero-hit returns `[]`, structured-field `threshold` classification, regex-derived `background` classification, fingerprint-unchanged regression, byte-inertness across a populated + a zero-hit fixture). Budgeted at 3 pts for the whole of P1 — consistent with H3's "3+ pts with an explicit fixture/test list" bar.
- **H4 (bundle-vs-sum check)**: This PRD bundles 5 capability areas. Per-area independent estimates match the phase table exactly — no package-price compression:

  | Capability Area | Independent Estimate | Notes |
  |------------------|----------------------|-------|
  | Write-path core (vocab + matcher + classifier + claim-map attach + guard tests) | 3 pts | P1 |
  | Read-model propagation (export 1.7 + catalog DDL + search/serve) | 4 pts | P2 — hardest phase, absorbs H6 plumbing (see below) |
  | Backfill | 2 pts | P3 |
  | runs-viewer presentation | 2 pts | P4 |
  | Finalization (docs + 4 deferred-item specs) | 1 pt | P5 |
  | **Σ** | **12 pts** | Plan total = Σ exactly; no compression |

- **H5 (anchor reference)**: **Anchor**: CARP C3 (`catalog-assisted-research-planning-v1`, P1+P2 slice) = 9 pts for a comparable deterministic-retrieval + governed-propagation shape. **This plan**: 12 pts. **Delta**: +3 pts (+33%). **Justification** (decisions block §4): the delta is fully explained by two capability areas CARP's comparable slice lacked outright — a UI presentation phase (P4, 2 pts) and a production-bundle backfill phase (P3, 2 pts) — not by underestimating the shared write-core/propagation spine, which tracks the anchor closely (P1+P2 here = 7 pts vs. anchor's 9, i.e. *cheaper* than the anchor on the directly comparable slice).
- **H6 (hidden plumbing budget)**: Not budgeted as a separate line item — explicitly absorbed into P2's 4 pts per the decisions block (~15% of P2's subtotal covers the schema-version bump, `run-export.ts` dual-update, serve-layer query params, and sensitivity-tier fixtures). Watch this during execution: if P2's serve-api sensitivity fixtures need reworking (a named inflation risk in the decisions block), the absorbed plumbing budget is the first place slippage will show up — +1 pt contingency is pre-flagged there, not elsewhere.

**Locked estimate**: 12 pts (bottom-up = locked; no downward compression).

---

## 3. Wave & Orchestration Notes

**Critical path**: P1 → P2 → P5, with P3 and P4 forking off P2 in parallel and both joining before P5. P1's guard-test exit gate (TASK-1.6 — fingerprint regression + verify byte-inertness) is the single hardest blocking dependency in the whole plan: nothing in P2 begins until it is green, because P2 copies fields P1 defines and cannot safely propagate an unproven index.

**Parallel opportunities**: P3 (backfill) and P4 (runs-viewer surfaces) fork off P2 and run concurrently — confirmed disjoint file ownership (`src/research_foundry/services/*` + CLI vs. `frontend/runs-viewer/*`), no serialization barrier between them. Both depend only on P2's frozen contract (schema 1.7 fields + `catalog_terms` table + search/serve params).

**Merge order**: No PR should merge P2 into the integration branch before P1's guard tests are reviewed and green — the entry-blocking gate is a merge-order constraint, not just an execution-order one. P3 and P4 PRs may merge in either order relative to each other once both are individually green; P5 (docs + karen gate) must be the last merge.

**Agent routing**: All leaf implementation routes to `ica-executor` (`claude-sonnet-5[1m]`, ICA free-tier offload) per operator directive — flat legs only, no nested agent dispatch from an ICA leaf. Every phase gate (`task-completion-validator`) and the end-of-feature check (`karen`, claude opus) stay claude-native — MUST-stay verdict class, never offloaded. Fallback chain per RoutingRecord: if ICA errors/overloads mid-leaf, re-dispatch the whole leaf to native `claude/claude-sonnet-5` (leaves are single-phase and restartable, so this is cheap).

**Cross-feature coupling**: Depends on CARP C3 (`catalog_retrieval.py:385-449`, merged `95e8419`/`d824290`) as the extraction primitive this feature adapts, and on `services/rights_backfill.py` as the backfill pattern template. Both are complete and stable; no in-flight conflicts identified.

---

## 4. Open Questions Ledger

| ID | Source | Question | Status | Resolved By |
|----|--------|----------|--------|-------------|
| OQ-1 | PRD §13 | Should the pediatric vocabulary live as a workspace-level `vocab/*.yaml` file or a shared RF-core default list with per-project overrides? | resolved | D4 (decisions block) — project-scoped versioned `vocab/*.yaml` file, hand-maintained v1; RF-core defaults optional/future |
| OQ-2 | PRD §13 | Gating process for a future model-assisted usage-role enrichment pass (`usage_role_model_version` stamp)? | deferred-to-v2 | Plan DOC-D1 — design-spec stub `term-index-model-assisted-roles-v2.md` |
| OQ-3 | PRD §13 | Does extending `_term_index` onto strict `additionalProperties: false` families require only a schema-version bump, or re-litigating `adr-rights-entity-model.md`'s strictness discipline? | deferred-to-v2 | Plan DOC-D2 — design-spec stub `term-index-strict-schema-extension-v2.md` |
| OQ-4 | PRD §13 (= decisions block OQ-A) | What breadth of fixture-based CI regression is required before a production-wide backfill of the 7 pediatric-CDS bundles is authorized? | resolved | Plan frontmatter — CI suite scoped to ≥2 runs (87-claim pediatric ledger + 1 zero-hit synthetic fixture); enforced at TASK-1.6 |
| — | PRD §13 | Sensitivity-tier derivation mechanics: per-tier at write time, or filtered from post-redaction evidence points at read time? | resolved | D3 (decisions block) — per-row `sensitivity_rank` on `catalog_terms`, read-time filter `rank <= threshold`; enforced at TASK-2.3/2.4/2.7 |
| OQ-B | Design spec (decisions block §7) | Should `search_text` in `catalog_items` also carry canonical term aliases, or is `catalog_terms` the only new query surface in v1? | deferred-to-v2 | Plan DOC-D4 — design-spec stub `catalog-search-text-term-aliasing-v2.md`; default is `catalog_terms`-only (reopening `search_text` reopens the flat-blob sensitivity question) |
| OQ-C | Decisions block §7 | Exact CLI flag semantics for `--term`/`--role` (repeatable? AND vs OR?) | resolved | Plan frontmatter — AND across distinct flags, OR within repeats of the same flag, mirroring `--item_type`/`--project`; enforced at TASK-2.5 |
| OQ-D | Decisions block §7 | Vocab file schema validation — fail-closed or warn-and-skip? | resolved | Plan frontmatter — malformed vocab fails closed (blocks claim-map); missing vocab warns and skips (`_term_index` omitted, not errored); enforced at TASK-1.1 |
| OQ-E | Decisions block §7 | Is `report_frontmatter` rollup field v1-required or deferred? | resolved | Plan frontmatter — sized inside P1 (TASK-1.5), not deferred |

---

## 5. Deferred Items Rationale

- **Model-assisted usage-role enrichment (PRD-OQ-2)**: Deferred because it requires its own `usage_role_model_version` stamp and conditional-go gate, distinct from v1's rule-based clearance (the exploration charter's deal-killer condition explicitly excludes any model call). Promote when a rule-based classifier miss-rate is high enough to justify a model pass, with an explicit reproducibility-gating proposal attached.
- **Strict-schema extension onto `canonical_claim`/`inference_record`/`source_assertion` (PRD-OQ-3)**: Deferred because it needs an explicit schema-version bump plus `backend-architect` sign-off against `adr-rights-entity-model.md`'s strictness discipline; v1 is locked to open schemas only (D1). Promote when a concrete v2 use case needs term data on inferences/reports/source cards, with architect sign-off secured.
- **Controlled-vocabulary sourcing beyond hand-maintained (PRD-OQ-1 residual, MeSH/UMLS/LOINC)**: Deferred because D4 locks hand-maintained-only for v1 (the pediatric use case needs only ~tens of terms). Promote when the hand-maintained vocabulary list outgrows itself — D5's own stated trigger is roughly >200 terms.
- **`search_text` canonical term aliasing (design-spec OQ-B)**: Deferred because it reopens the flat-blob sensitivity question D3/FR-11 were written to close (the `search_text` leak precedent). Promote only when a demonstrated recall gap shows `catalog_terms` facet search is insufficient and FTS5 substring search on aliased text is specifically requested.

---

## 6. Risk Narrative

- **Sensitivity leak via derived term rows** (high severity): The flat-`search_text` precedent in `catalog_service.py` — captured once at max-permissive sensitivity, never re-filtered per point at read time — is a *named, live* leak pattern in this codebase, not a hypothetical. A term table computed the same way would republish redacted content as terms. Watch P2 closely: D3's per-row `sensitivity_rank` is the whole mitigation, and it must be verified at the *serve* layer, not just the service layer (the known list-ok/detail-404 diagnostic trap from `sensitivity-threshold-router-gate` means a service-layer-only test can pass while the API layer still leaks).
- **Identity-hash / verify-gate regression** (high impact, low likelihood): `_term_index` touching `source_assertion_fingerprint()` or flipping any `rf verify` outcome would break the claim ledger's authority contract — this is the exploration charter's literal deal-killer condition. P1's guard tests are entry-blocking for a reason: nothing downstream should be trusted until the inertness property is proven in CI, not just asserted in a design doc.
- **Export/viewer schema drift** (medium severity): `run-export.ts` is hand-written and silently drops unknown fields if not bumped alongside the exporter. This has bitten prior additive schema bumps in this codebase. D7's dual-update rule (same leaf, same phase) is the mitigation; watch for a PR that lands the Python side without the TS side.
- **Backfill against verified production bundles** (medium severity): The 7 pediatric-CDS bundles are the highest-stakes corpus in the project and live in the private data repo (data-plane split) — a clobbering write here is not recoverable from the public repo alone. Insist on seeing the reviewed dry-run diff before any wet run is authorized, not just a "tests passed" claim.
- **ICA leaf process/quality hazards** (medium, process risk): Known failure modes from the CARP retrospective — orphaned leaves (wrapper timeout ≠ process actually killed), long-session instability, and fail-open shortcuts that only reviewers caught (5 for 5 in CARP, none caught by the leaves themselves). Treat every `task-completion-validator` gate as load-bearing, not ceremonial.

---

## 7. What to Watch For

- The sensitivity-threshold-router-gate diagnostic signature (list-ok, detail-404) is a recurring trap in this codebase — if P2's serve-api tests only exercise the list endpoint, a real leak can hide.
- `npx tsc --noEmit` is a documented no-op in this repo for the runs-viewer; the real P4 gate is `tsc -p tsconfig.app.json --noEmit`. If a phase report cites the former, treat it as unvalidated.
- Worktree pytest runs need the worktree-scoped interpreter invocation (`PYTHONPATH=<worktree>/src <main>/.venv/bin/python -m pytest`), not the pyenv shim — a recurring false "module not found" failure otherwise.
- The pediatric-CDS bundle population (P3's real backfill target) lives in the private `research-foundry-data` repo, not this repo — confirm the execution environment actually has that data mounted/accessible before trusting a P3 dry-run result as representative.
- Watch for an ICA leaf reporting phase completion without the entry-blocking gate (TASK-1.6 for P2, P2's exit gate for P3/P4) actually having run — CARP's lesson is that reviewers catch fail-opens, leaves don't self-report them.
- `catalog_terms` DDL work (TASK-2.3) may get split to a `data-layer-expert` profile leaf separate from the rest of P2's `python-backend-engineer` leaf — confirm which leaf actually owns it before assuming a single P2 completion report covers both.

---

## 8. Expected Success Behaviors

- [ ] A freshly-run `claim-map` on any project with a valid `vocab/*.yaml` produces claims whose `_term_index.vocabulary_version` matches the loaded vocabulary's version — spot-check a sample `claim_ledger.yaml` by eye.
- [ ] `rf verify` run before and after this feature ships on the same fixture bundle produces byte-identical console output and an unchanged status table — no surprise status flips.
- [ ] `rf catalog search --term cbc` (or an equivalent pediatric term) returns every claim mentioning that term or a known alias, including surface-form variants FTS5 substring search alone would miss.
- [ ] Lowering the sensitivity threshold on a `rf serve` catalog query reduces or matches, never exceeds, the term rows returned at a higher threshold for the same item — spot-check at two threshold levels.
- [ ] The runs-viewer `AssertionCatalogPane` shows a terms-present facet chip-row that populates when a bundle has vocabulary hits and stays empty (not erroring) when it doesn't.
- [ ] `CatalogScreen` correctly pre-filters when visited with a `?term=` query parameter, and behaves exactly as before when the parameter is absent.
- [ ] `ClaimLedgerTable` shows a term/usage-role badge that is visually distinguishable at a glance from a real `pediatric_cds` structured threshold value — no operator should confuse the two.
- [ ] Running the backfill CLI in dry-run mode against the 7 real pediatric-CDS bundles produces a diff a human can review and sanity-check before any wet run is authorized.
- [ ] A second backfill run (or a second `rf catalog rebuild`) with nothing changed produces zero additional writes — idempotency holds under manual re-run.

---

## 9. Running Log

- [2026-07-24] Brief created from PRD + implementation plan + decisions block, post plan-authoring (commit `a3edcc2`).
