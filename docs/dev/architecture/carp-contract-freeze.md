---
title: "CARP Contract Freeze: Retrieval Policy, Identity/Denial, and Evidence-Plan Coverage"
doc_type: architecture
status: frozen
schema_version: 1
created: 2026-07-23
updated: 2026-07-23
feature_slug: catalog-assisted-research-planning
resolves: ["CARP-OQ-1", "CARP-OQ-2", "CARP-OQ-3"]
related_docs:
  - docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/dev/architecture/assertion-ledger-contract.md
  - schemas/research_evidence_plan.schema.yaml
  - schemas/search_request.schema.yaml
  - schemas/search_run.schema.yaml
  - schemas/research_brief.schema.yaml
  - schemas/routing_decision.schema.yaml
owner: nick
---

# CARP Contract Freeze: Retrieval Policy, Identity/Denial, and Evidence-Plan Coverage

**Status:** frozen for Phase P1 (Catalog-Assisted Research Planning, "CARP"). This document,
together with the five schema files it references, is the exact tree that `task-completion-validator`
and Karen approve at gate `CARP-1.G`. Any material change after that approval invalidates both
verdicts (implementation plan §Phase P1, §Reviewer and Closeout Contract).

Phases P2–P6 build against this contract. They may not re-litigate the decisions below without a
new contract-freeze cycle; they may only implement, evaluate, and propagate them.

## Scope

This document covers CARP-1.1 (retrieval policy), CARP-1.2 (identity and denial), CARP-1.3
(evidence-plan/coverage contract), and CARP-1.4 (RPC seam and compatibility). It defines schema
shape and semantics only — no `src/research_foundry/**/*.py` production code changes are authorized
by this document (Mode B — Contract Drafting).

## 1. Retrieval policy (CARP-1.1 — resolves CARP-OQ-2)

`retrieval_policy` is a closed enum with exactly three members:

| Value | Meaning |
|---|---|
| `disabled` | **The v1 default.** Absent/omitted policy behaves byte-identically to the pre-CARP legacy flow: no catalog query, no evidence plan is created, no additive metrics block is populated anywhere. |
| `catalog_only` | Query the governed catalog; never call a network provider. An empty or denied catalog result is a **terminal** state for the whole plan — it does not fall through to discovery. |
| `catalog_then_discovery` | Catalog first, then providers for **residual questions only**. The fallback is explicit and question-level: only a question whose terminal coverage state is `residual` may produce a provider request. |

**v1 is opt-in.** There is no implicit network fallback from any state, in any policy. A caller
that never sets `retrieval.policy` (on `search_request`) gets exactly today's behavior — this is
schema-enforced by the field being additive and optional (§7, fixture (a)).

`disabled` is deliberately **excluded** from `research_evidence_plan.schema.yaml`'s own
`retrieval_policy` enum (only `catalog_only` / `catalog_then_discovery` are valid there), because an
evidence plan object is never constructed under `disabled` — there is nothing to freeze the shape
of. `search_request`, `search_run.retrieval.policy`, and `routing_decision.retrieval_policy` all
carry the full three-member enum (or omit the block/field entirely) because those surfaces must be
able to represent — or omit, for `disabled` — the policy that was in effect.

## 2. Identity and denial contract (CARP-1.2)

1. **Identity precedes retrieval.** Every retrieval-bearing DTO carries an authenticated workspace
   identity (`AuthIdentity` — `src/research_foundry/api/auth/provider.py:35`, fields `user_id`,
   `workspace_id`, `roles`) *before* any catalog query is issued. This mirrors
   `AssertionCatalog.search()`'s existing precondition (`src/research_foundry/services/assertion_catalog.py:126-131`):
   `identity is None or not identity.workspace_id` denies before any record is read.
2. **One denial shape.** Every denial/empty response reuses the existing shape from
   `AssertionCatalog.denied_payload()` (`src/research_foundry/services/assertion_catalog.py:210-216`):

   ```json
   {"items": [], "next_cursor": null, "facets": {"lifecycle_states": [], "access_scopes": []}, "denial_reason": "<code>"}
   ```

   CARP's evidence-plan analogue is `catalog_receipt.denial_reason` (non-null) with
   `catalog_receipt.record_count == 0` — the plan-level equivalent of the same shape, expressed in
   the evidence-plan schema rather than the catalog-search response schema.
3. **Zero candidate-derived fields on denial.** A denied retrieval summary exposes **zero**
   candidate-derived fields. Every counter that could be derived from candidates
   (`questions_covered`, `questions_residual`, `candidates_evaluated`, `candidates_selected`,
   `avoided_provider_calls`, `residual_reason_counts`, catalog `facets`) is forced to `0` or omitted.
   `questions_total` is the one exception: it is echoed from the *request* (the brief's question
   count), not derived from the corpus, so it may appear on a denied summary without leaking any
   candidate signal.
4. **Resolves CARP-OQ-3:** `cache_first` MUST NOT expose refresh-required state to an
   unauthenticated or denied caller. Concretely: a `reuse_decision.action == "refresh"` receipt
   (`assertion_reuse.evaluate_reuse()` returning `ReuseDecision("refresh", "freshness_refresh_required" | "edition_refresh_required" | "extraction_refresh_required", ...)`)
   is visible only inside `evaluated_candidates[]` on a plan built for an **authorized identity
   inside the owning workspace**. `evaluated_candidates` is a required field on every question item
   the schema allows (`research_evidence_plan.schema.yaml`'s per-question `required`) — it is not
   true that a denied or cross-workspace caller "never receives an `evaluated_candidates` array at
   all." What it receives is an **empty** one (`evaluated_candidates: []`), or, in the fail-closed
   fixture used by §7 fixture (b), a plan whose `questions` array itself is empty. Either shape is
   correct and leaks nothing: the denial path returns before any candidate is ever evaluated, so
   there is no code path that could populate a refresh-state entry for it to leak. The corrected
   claim is about content (never non-empty, never carrying refresh state), not about the field's
   presence.

## 3. Evidence-plan / coverage contract (CARP-1.3 — resolves CARP-OQ-1)

Exactly one **terminal** coverage state per question: `covered` | `residual`. There is no third
state and no "unknown"/"pending" state — an evidence plan is a complete, terminal decision for
every question it contains.

### 3.1 The six covered conditions

A question is `covered` **only if ALL six** of the following hold. Any failure, uncertainty, error,
or unrepresentable state resolves the question to `residual` — never to `covered`, and never left
unresolved.

1. At least one authorized candidate whose case-folded required terms all appear in the candidate's
   catalog `search_text` (conservative lexical rule; no semantic/vector matching).
2. Candidate `lifecycle_state == "eligible"` **re-read immediately before selection** (not from a
   possibly-stale projection snapshot).
3. `evaluate_reuse(...)` (`src/research_foundry/services/assertion_reuse.py:37`) returns an
   **allow** decision — `refresh`-required and `deny` are both residual.
4. The candidate satisfies every `required_source_types` and `required_qualifiers` declared on the
   question. A question that declares a constraint the candidate cannot be *shown* to meet is
   residual (missing constraint data ⇒ residual, never covered).
5. No contradicting authorized candidate exists for the same question.
6. The candidate's `assertion_version` is pinned exactly at selection time.

A `covered` question MUST carry `residual_reason: null` and a non-null
`selected_assertion_ref`/`retrieval_receipt` pair (schema-enforced — §6). A `residual` question MUST
carry exactly one `residual_reason` code and a null `selected_assertion_ref`/`retrieval_receipt`
pair. These two branches are an exact, schema-enforced partition
(`research_evidence_plan.schema.yaml`'s per-question `allOf`/`if`/`then`): every instance falls into
exactly one branch, with no gap and no overlap.

### 3.2 Residual reason enum

Closed enum, 14 members. A residual question MUST carry exactly one.

| Code | Meaning |
|---|---|
| `no_candidate` | The catalog returned zero authorized rows for this question. |
| `lexical_miss` | Candidates exist, but none satisfy condition 1 (required-terms lexical match). |
| `source_type_mismatch` | Condition 4 failure: no candidate can be shown to satisfy `required_source_types`. |
| `qualifier_missing` | Condition 4 failure: no candidate can be shown to satisfy `required_qualifiers`. |
| `reuse_refresh_required` | Condition 3 failure: the best candidate's `evaluate_reuse()` returned `refresh`. |
| `reuse_denied` | Condition 3 failure: the best candidate's `evaluate_reuse()` returned `deny`. |
| `lifecycle_ineligible` | Condition 2 failure: the immediate-before-selection re-read shows a non-`eligible` lifecycle state (the projection was stale). |
| `version_mismatch` | Condition 6 failure: the candidate's pinned `assertion_version` no longer matches at selection time. |
| `contradiction` | Condition 5 failure: a contradicting authorized candidate exists for the same question. |
| `pagination_limit` | The catalog's page cap (`max_pages_per_question`, ≤5 pages of ≤100 rows each) was reached before a qualifying candidate was found. |
| `candidate_limit` | `max_candidates_per_question` (≤50) was reached before the six conditions could be resolved. |
| `catalog_denied` | The catalog issued a fail-closed denial (`AssertionCatalogDenied`) for the whole plan. |
| `catalog_empty` | The authorized workspace corpus has zero eligible rows for the whole plan. |
| `evaluation_error` | Any other uncertain, erroring, or unrepresentable state — including a catalog-generation change detected mid-plan (§3.4). Catch-all; conservative by construction. |

### 3.3 Limits (schema-validated)

| Limit | Ceiling | Enforced in |
|---|---|---|
| `max_questions` | 200 | `research_evidence_plan.schema.yaml` (`questions` `maxItems`), `search_request.schema.yaml` (`retrieval.limits.max_questions` `maximum`) |
| `max_candidates_per_question` | 50 | `research_evidence_plan.schema.yaml` (`evaluated_candidates` `maxItems`), `search_request.schema.yaml` `maximum` |
| `max_pages_per_question` | 5 | `search_request.schema.yaml` `maximum` |
| per-page size | ≤100 (the catalog's existing page cap — `AssertionCatalog._MAX_PAGE_SIZE`, `src/research_foundry/services/assertion_catalog.py:29`) | `search_request.schema.yaml`/`research_evidence_plan.schema.yaml` `limits.page_size` `maximum` |

### 3.4 Deterministic ordering

- Questions are sorted by `question_id` **ascending**.
- Evaluated candidates within a question are sorted by `assertion_id` **ascending** (matches the
  catalog's existing sort — `AssertionCatalog.search()`, `filtered.sort(key=lambda record: record["assertion_id"])`).
- **Same inputs + same catalog generation ⇒ byte-equivalent plan.** `catalog_receipt.catalog_generation_id`
  pins the generation a plan was built against. A catalog rebuild (`AssertionCatalog.rebuild()`)
  detected mid-plan-construction breaks the single-frozen-generation guarantee for any question
  not yet resolved; the conservative resolution is `evaluation_error` for that question (never a
  silent re-read against the new generation, which would forfeit the byte-equivalence contract).

### 3.5 H3 coverage scenario matrix

The 12 scenarios named in the P1 brief appear below verbatim, plus 5 additional scenarios that
between them exercise every one of the 14 residual-reason codes and the "covered despite noise"
edge cases at least once. 17 total, satisfying the ≥10 requirement with margin.

| # | Scenario | Setup (abbreviated) | Terminal state | Reason |
|---|---|---|---|---|
| 1 | Exact match | One authorized candidate; all 6 conditions pass. | `covered` | `null` |
| 2 | No hit (zero candidates) | Catalog returns zero authorized rows for this question. | `residual` | `no_candidate` |
| 3 | No hit (lexical miss) | Candidates exist; none contain all required terms. | `residual` | `lexical_miss` |
| 4 | Source-type mismatch | Best candidate cannot be shown to satisfy `required_source_types`. | `residual` | `source_type_mismatch` |
| 5 | Missing qualifier | Best candidate cannot be shown to satisfy `required_qualifiers`. | `residual` | `qualifier_missing` |
| 6 | Refresh required | `evaluate_reuse()` returns `refresh` (e.g. edition/extraction-contract drift). | `residual` | `reuse_refresh_required` |
| 7 | Reuse denied | `evaluate_reuse()` returns `deny` (e.g. rights/sensitivity/evaluation failure). | `residual` | `reuse_denied` |
| 8 | Stale projection | Projection said `eligible`; immediate-before-selection re-read shows a different lifecycle state. | `residual` | `lifecycle_ineligible` |
| 9 | Version mismatch | Candidate's `assertion_version` changes between evaluation and the pin-at-selection re-check. | `residual` | `version_mismatch` |
| 10 | Conflicting packet | A second authorized candidate for the same question contradicts the first. | `residual` | `contradiction` |
| 11 | Multiple equivalent hits | Two-plus equally-valid candidates. Deterministic tie-break selects the lowest `assertion_id`. | `covered` | `null` |
| 12 | Pagination boundary | `max_pages_per_question` (5) reached before a qualifying candidate is found. | `residual` | `pagination_limit` |
| 13 | Duplicate candidate | The same `assertion_id` appears twice in raw catalog results (e.g. page-boundary overlap); deduped before the six conditions run and never inflates `candidates_evaluated`. | `covered` (if the deduped single candidate is otherwise valid) | `null` |
| 14 | Catalog generation changed mid-plan | `AssertionCatalog.rebuild()` runs while later questions in the same plan are still being resolved. | `residual` | `evaluation_error` |
| 15 | Candidate limit exceeded | `max_candidates_per_question` (50) reached before the six conditions resolve. | `residual` | `candidate_limit` |
| 16 | Catalog denied | `AssertionCatalogDenied` raised for the whole plan (e.g. missing/cross-workspace identity, rights denial). | `residual` (all questions) | `catalog_denied` |
| 17 | Catalog empty | Authorized workspace corpus has zero eligible rows at all. | `residual` (all questions) | `catalog_empty` |

### 3.6 Seams P2 must add

Two gaps exist between this frozen contract and the code as it stands today. Neither is a
production-code change authorized by this document (§Scope) — P2 must close both while building the
governed catalog adapter; this section names them precisely so P2 does not discover them mid-build.

#### Seam 1 — `catalog_generation_id` has no producer

`AssertionCatalog.rebuild()` (`src/research_foundry/services/assertion_catalog.py:106`) writes a
projection of shape `{"schema_version": 1, "workspace_key": ..., "records": [...]}`. There is **no
generation identifier** anywhere in that payload, and `ProjectionReceipt` (same file, the dataclass
`rebuild()` returns) carries only `workspace_id`, `record_count`, `projection_path` — no generation
id either.

§3.4's byte-equivalence guarantee and the "catalog generation changed mid-plan ⇒
`evaluation_error`" rule both depend on `catalog_receipt.catalog_generation_id` being a real,
comparable value. As frozen, both are unimplementable: there is nothing to compare, because no code
path mints, persists, or returns a generation identifier today.

P2 must add a real generation identifier, honoring the existing "never a filesystem path" constraint
(`research_evidence_plan.schema.yaml`'s own field description). Two candidate mechanisms, either
acceptable:

- **Content digest** — a `sha256` over the sorted, canonicalized `records` list, computed inside
  `rebuild()` and written into the projection dict alongside `schema_version`/`workspace_key`.
  Changes iff the record set actually changes; stable and mtime-independent.
- **Monotonic counter** — a `generation` integer persisted in the projection dict itself,
  incremented by `rebuild()` on every call regardless of whether the record set changed.

Whichever mechanism P2 picks, it must land in two places: the on-disk projection dict, and a new
field on `ProjectionReceipt` — the planner reads the receipt, not the raw file, to populate
`catalog_receipt.catalog_generation_id`. A planner then detects a mid-plan generation change by
capturing the generation id once at plan start and re-checking it (re-reading the projection's
persisted id, without triggering a rebuild) before resolving each remaining question; a mismatch
resolves that question to `evaluation_error` per §3.4 — never a silent re-read against the new
generation, which would forfeit the byte-equivalence contract.

#### Seam 2 — `search_text` is not reachable through the catalog API

Covered condition 1 (§3.1) requires matching every required term against a candidate's
`search_text`. But `search_text` is stripped from **both** catalog read surfaces the planner is
allowed to call:

- `_summary()` (`assertion_catalog.py:219`) returns 5 fields — `assertion_id`, `assertion_version`,
  `lifecycle_state`, `access_scope`, `rights_decision` — and `search_text` is not among them.
  `search()`'s `items` are built exclusively from `_summary()`.
- `packet()` (`assertion_catalog.py:183`) explicitly filters it out at line 193:
  `{k: v for k, v in record.items() if k != "search_text"}`.

CARP-2.1 forbids the adapter from reading ledger paths directly (it may only call
`AssertionCatalog`'s public methods), so **as frozen, the primary covered condition cannot be
evaluated through the API surface the adapter is required to use.** This is a real contract gap, not
a documentation oversight, and P2 cannot start condition-1 evaluation without resolving it.

**Correction to a related factual claim:** `AssertionCatalog.search()` performs exactly **one**
substring match of the whole normalized query against `search_text`
(`assertion_catalog.py:161`: `normalized_query in record["search_text"].casefold()`). It is **not** a
per-term match, and no per-term matching code exists anywhere in this module today. Any reading of
§3.1 condition 1 that assumes `search()` already implements the "all required terms present" rule is
incorrect — that rule is new planner logic P2 must add; it is not existing catalog behavior the
planner can lean on unmodified.

**Open sub-question for P2:** if the workaround is one `search(query=term)` call per required term,
intersected on `assertion_id` across the per-term result sets, then `max_pages_per_question: 5`
(§3.3) is specified **per question**, but under this workaround it would be consumed **per
term-query** — a question with 3 required terms could need up to 15 pages of catalog reads, not 5.
P2 must settle this arithmetic (e.g. redefine the effective page budget as
`max_pages_per_question × len(required_terms)`, or add a new catalog read path that returns
`search_text` so a single per-candidate all-terms check can run without per-term pagination) before
writing pagination code. This document does not resolve it; it is flagged here as an open question
P2 inherits, not a silent assumption.

## 4. RPC seam (CARP-1.4)

**Research Provenance Continuity (`C1`) has not been executed.** There is no `RPC-1.G` gate to
depend on, and `schemas/search_activity_receipt.schema.yaml` does not exist on disk. This document
and its schemas therefore:

- Do **not** author, stub, or invent any RPC-owned schema file (no `search_activity_receipt.schema.yaml`
  or any of its concepts — canonical origin, activity envelope, report-use). That is C1's ownership.
- **Do** define a self-contained, additive, CARP-owned carrier for selection provenance — the exact
  selected `assertion_id` + `assertion_version` pair plus a catalog-scoped retrieval receipt — inside
  CARP-owned schema surfaces only (`research_evidence_plan.schema.yaml`'s per-question
  `selected_assertion_ref` / `retrieval_receipt`, and `search_run.schema.yaml`'s additive
  `retrieval.selections[]`).

**Normative substitution.** Until C1 lands, every plan reference to "the RPC context" or
"RPC-defined context" — including the plan's downstream acceptance criteria AC CARP-5 ("selections
flow through the RPC-defined context"), CARP-4.2 ("carry RPC context"), and CARP-6.6 ("round-trip …
through RPC context") — is satisfied by the CARP-owned `selected_assertion_ref` + `retrieval_receipt`
pair defined in §4.1 below. A P4/P5/P6 reviewer evaluating those ACs against this frozen contract
must treat that pair as the RPC context for every purpose those ACs name; CARP-6.6's RPC leg
specifically is deferred to the §4.2 rebase, not fabricated ahead of C1.

### 4.1 One authoritative location per fact

`research_evidence_plan.schema.yaml` is the **sole authoritative source** for the coverage/selection
decision. `search_run.schema.yaml`'s `retrieval` block is an explicitly-marked
**non-authoritative persisted mirror** (`retrieval.mirror_is_authoritative: const false` —
schema-pinned, same convention as `source_card.schema.yaml`/`source_assertion.schema.yaml`'s
`rights_summary.mirror_is_authoritative`) of that plan's selections *at run-completion time*. This
is not duplicate authority: the evidence plan is a planning-time artifact that can be rebuilt
against a newer catalog generation, while a completed run's persisted record is an immutable
historical snapshot of what that run actually used. `search_run.retrieval.evidence_plan_ref` links
the mirror back to its source of truth.

`routing_decision.schema.yaml`'s `retrieval_policy` and `residual_question_ids` are orchestration
state (which policy governed the decision, which question IDs were eligible for discovery routing)
— not a provenance fact, and out of scope for the RPC rebase below.

### 4.2 RPC rebase contract

When C1 lands and `schemas/search_activity_receipt.schema.yaml` exists, the following CARP fields
migrate into it. This table is the exact, contained diff a rebase performs — no other CARP field is
provenance-shaped.

| CARP field (today) | Migrates into (RPC, once C1 lands) | Notes |
|---|---|---|
| `research_evidence_plan.schema.yaml` → `questions[].selected_assertion_ref` (`assertion_id`, `assertion_version`) | `search_activity_receipt.schema.yaml`'s selected-evidence-versions field (RPC-FR-3: "selected evidence versions") | CARP's field is the exact shape RPC-FR-3 already names; the rebase is a rename/relocate, not a re-design. |
| `research_evidence_plan.schema.yaml` → `questions[].retrieval_receipt` (`source`, `catalog_generation_id`, `decided_at`) | `search_activity_receipt.schema.yaml`'s candidate-set-digest / selection-receipt field (RPC-FR-3: "candidate-set digest", "selection/denial/degraded outcomes") | CARP's receipt is catalog-only (`source` is always `"catalog"` in v1); RPC's receipt is provider-agnostic (any provider/site/corpus). The rebase narrows RPC's general shape to this catalog-only instance, it does not widen CARP's. |
| `research_evidence_plan.schema.yaml` → `catalog_receipt.catalog_generation_id` | `search_activity_receipt.schema.yaml`'s candidate-set-digest scope (RPC-FR-3) | Same "which corpus state produced this result" concept, generalized. |
| `search_run.schema.yaml` → `retrieval.selections[]` (the non-authoritative mirror) | Superseded by a reference to the RPC activity ID | Once RPC's canonical activity envelope exists, `search_run` should reference `activity_id` instead of mirroring selection detail directly — the mirror pattern was a stopgap for the period where no canonical envelope existed. |
| `routing_decision.schema.yaml` → `retrieval_policy`, `residual_question_ids` | **Not part of this rebase** | Orchestration state, not a provenance fact (§4.1). Stays CARP-owned indefinitely. |

Forbidding duplicate evidence-selection fields (this section's title invariant) means: after the
rebase, `research_evidence_plan` still holds the planning-time decision, the RPC activity receipt
holds the run-time canonical provenance record, and `search_run` holds a *reference* to the latter
rather than a second copy of the selection detail. Exactly one authoritative location per fact, at
every point in the migration.

## 5. Open-question resolutions

| ID | Question | Resolution |
|---|---|---|
| CARP-OQ-1 | Freeze the conservative deterministic evidence-coverage rule. | §3.1 (six conditions), §3.2 (14-member closed `residual_reason` enum), §3.4 (deterministic ordering + byte-equivalence contract). Resolved. |
| CARP-OQ-2 | Confirm opt-in versus default-on retrieval policy for v1. | §1: `disabled` is the default; v1 is opt-in; no implicit network fallback from any state. Resolved. |
| CARP-OQ-3 | Decide whether `cache_first` exposes anonymous refresh-required state. | §2.4: no. Refresh state is visible only to an authorized identity inside the owning workspace; a denied/cross-workspace caller never receives an `evaluated_candidates` array. Resolved. |

## 6. Schema surfaces (summary)

| Schema | Change |
|---|---|
| `schemas/research_evidence_plan.schema.yaml` | **NEW.** Plan identity, workspace, `retrieval_policy` (2-member enum — no `disabled`), `catalog_receipt`, `limits`, ordered `questions[]` (with the covered/residual `allOf` partition), and `summary`. |
| `schemas/search_request.schema.yaml` | **Additive.** Optional `retrieval.policy` (3-member enum, default `disabled`) + optional `retrieval.limits`. Absent block ⇒ `disabled`, byte-identical to legacy. |
| `schemas/search_run.schema.yaml` | **Additive.** Optional `retrieval` block: `policy` (2-member enum — `disabled` runs omit the block), `evidence_plan_ref`, `mirror_is_authoritative: const false`, `selections[]`, `metrics`. Legacy runs omitting the block still validate. |
| `schemas/research_brief.schema.yaml` | **Additive.** `questions.primary[]`/`questions.secondary[]` items gain optional `coverage_state` (2-member enum) and `residual_reason` (14-member enum ∪ `null`). |
| `schemas/routing_decision.schema.yaml` | **Additive.** Optional `retrieval_policy` (3-member enum) and `residual_question_ids`. |

All five files remain additive-only per the plan's compatibility rule: no existing property was
removed, renamed, or tightened.

## 7. Fixture requirements (implemented in `tests/test_schema_validation.py`)

1. A policy-absent legacy `search_request` — validates, and is documented here as meaning
   `disabled`.
2. A `catalog_only` denied/empty `research_evidence_plan` — `catalog_receipt.denial_reason` set,
   `catalog_receipt.record_count == 0`, and `summary` carrying no non-zero candidate-derived
   counters.
3. A two-workspace case — two independently valid `research_evidence_plan` instances scoped to
   distinct `workspace_id` values.
4. A mixed covered/residual `research_evidence_plan` — at least one `covered` and one `residual`
   question in the same plan, each satisfying the `allOf` partition from §3.1.

## 8. CARP-2.G gate finding and known limitations

Two findings surfaced at the CARP-2.G gate against `catalog_retrieval.py`'s `_project_reuse_input`
(the packet → `evaluate_reuse()` flat-input projection). One was a real fail-closed-to-fail-open
defect and was fixed; the other was accepted as a documented limitation rather than fixed, per this
freeze's no-synthesis rule.

### 8.1 Sensitivity axis was aliased from the rights axis (fixed)

**Finding.** The original CARP-2.2 implementation projected both `rights_allowed` and
`sensitivity_allowed` from the *same* `rights_decision.allowed` boolean
(`AssertionCatalog._rights_decision`: known `access_scope` membership + `allowed_for_work_output`).
That boolean never evaluates a sensitivity *threshold* — it only checks that `access_scope` is one
of the known values and that the edition is marked reusable. An edition with
`access_scope: client_sensitive` and `allowed_use.allowed_for_work_output: true` therefore produced
`sensitivity_allowed: True`, and `evaluate_reuse()` allowed reuse with **no sensitivity ceiling
evaluated at all** — the only reuse path in RF with this property. Pre-CARP, `evaluate_reuse()`'s
`sensitivity_allowed` check was fail-closed but structurally unreachable (`run_launch.py`'s mapping
never set the field); CARP-2 made the field reachable by aliasing it to an unrelated boolean, which
inverted the gate from fail-closed to fail-open.

**Fix.** `sensitivity_allowed` is now computed independently, from `packet["access_scope"]`
(`source_edition.access_scope`, carried on every packet regardless of the rights decision) ranked
against a caller-supplied `RetrievalConstraints.sensitivity_threshold` via the shared
`research_foundry.services.sensitivity.SENSITIVITY_RANK` ordinal ordering (promoted out of a
duplicate copy in `rf agent-job`'s CLI filters — a second copy of a governance ordering is its own
defect). The threshold is never defaulted: when a caller omits it, `sensitivity_allowed` is **not**
set to `False`, it is **omitted from the projection entirely**, and `evaluate_reuse()` denies with
`sensitivity_denied` on the missing key exactly as it would on `False`. `rights_allowed` still
reflects the unrelated rights decision, now decoupled from sensitivity. See
`tests/unit/test_catalog_retrieval.py`'s CARP-2.G section for the exploit-reproduction, boundary,
and absent-threshold regression cases.

**Consequence for CARP-3.x**: no evidence-plan-builder caller may treat "no `sensitivity_threshold`
supplied" as equivalent to "no ceiling" — every caller of `catalog_retrieval.retrieve()` MUST decide
and pass an explicit threshold, or every candidate in that call will deny with `sensitivity_denied`.

**Follow-up finding (same gate, narrower re-inversion — fixed).** The initial fix used
`SENSITIVITY_RANK.get(sensitivity_threshold, len(SENSITIVITY_RANK))` on the threshold side, which was
fail-safe on the *scope* side (unknown scope → max rank → denies) but fail-**dangerous** on the
*threshold* side: an unknown/malformed/empty caller threshold silently became "allow up to the most
sensitive tier". `sensitivity_allowed` is now `True` iff the threshold resolves to a **known** rank
AND the access-scope rank is at or below it; a malformed threshold (e.g. `banana`, `""`) has no
ceiling to grant against and denies outright. The asymmetry is intentional: unknown SCOPE → most
sensitive (deny by comparison); unknown THRESHOLD → deny outright (no ceiling granted).

**Access-scope vocabulary ranking.** `SENSITIVITY_RANK` in `research_foundry.services.sensitivity`
ranks two parallel governance vocabularies that share their lower tiers:

* `source_edition.access_scope` (assertion-catalog `_rights_decision` known set):
  `public`, `personal`, `work_sensitive`, `client_sensitive`, `private` — `private` is this
  vocabulary's most-sensitive member; no `top_secret` value exists here.
* Run/agent-job `sensitivity` thresholds (`rf agent-job` filters): `public`, `personal`,
  `work_sensitive`, `client_sensitive`, `top_secret` — `top_secret` is this vocabulary's
  most-sensitive member; no `private` value exists here.

`private` and `top_secret` are each vocabulary's own most-sensitive label, never used by the other
caller, and are ranked **co-top** (same ordinal, `4`). A caller comparing across vocabularies (an
access-scope value against a run-sensitivity threshold) therefore gets a coherent ordering rather
than one vocabulary's most-sensitive tier silently outranking the other's. Prior to this pass,
`private` was absent from the rank map entirely and only denied by accident of the max-default fall-
through — see `tests/unit/test_catalog_retrieval.py` for the malformed-threshold-denies and
private-scope-rankable regressions.

### 8.2 `required_extraction_contract` is only weakly discriminating (accepted limitation)

`_project_reuse_input` projects `extraction_contract` from
`packet["assertion"]["extraction_provenance"]["schema_version"]` — there is no field on
`source_assertion` literally named "extraction contract". This was reviewed and accepted: the same
constant, `EXTRACTION_FACT_CLAIM_MAPPING_VERSION`, is what `assertion_materialization.py` stamps
into `extraction_provenance.schema_version` (lines ~403–409) *and* under the literal key
`mapping_contract` elsewhere in the same module (lines ~503, 549, 738) — so semantically this is the
correct value to project.

**Limitation, recorded loudly rather than silently accepted**: `EXTRACTION_FACT_CLAIM_MAPPING_VERSION`
is a near-global constant today — effectively every assertion in the ledger carries the same value.
This means `RetrievalConstraints.required_extraction_contract` matching (the
`extraction_refresh_required` residual path) is **advisory in v1**: it cannot yet discriminate
between two genuinely different extraction methodologies, because the ledger does not carry a
per-extraction contract identifier distinct from the one global mapping-schema version. A future
extraction-contract axis with real per-extraction granularity would need a new, separately-versioned
field on `source_assertion` — not a change to this projection.
