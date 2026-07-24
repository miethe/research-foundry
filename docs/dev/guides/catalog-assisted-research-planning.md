---
title: "Catalog-Assisted Research Planning (CARP) Guide"
description: "How the opt-in catalog-first evidence planner works: policy states, the coverage rule, residual reasons, limits, and denial guarantees"
audience: ["developers", "operators"]
tags: ["carp", "catalog", "retrieval", "assertion-ledger", "evidence-plan", "search-router"]
created: 2026-07-23
updated: 2026-07-23
category: "architecture"
status: "published"
feature_slug: catalog-assisted-research-planning
related_documents:
  - "docs/dev/architecture/carp-contract-freeze.md"
  - "docs/project_plans/implementation_plans/enhancements/catalog-assisted-research-planning-v1.md"
  - "docs/project_plans/PRDs/enhancements/catalog-assisted-research-planning-v1.md"
  - "docs/dev/architecture/assertion-ledger-contract.md"
  - "schemas/research_evidence_plan.schema.yaml"
  - "schemas/search_request.schema.yaml"
  - "schemas/search_run.schema.yaml"
  - "schemas/research_brief.schema.yaml"
  - "schemas/routing_decision.schema.yaml"
---

# Catalog-Assisted Research Planning (CARP) Guide

CARP lets a research brief's questions be resolved against the existing, governed assertion
catalog (the reusable assertion ledger's authorized-and-eligible view) **before** any question is
routed to a network discovery provider. It replaces nothing: it is an additive, opt-in planning
step that sits in front of the existing Search Router providers, decides — per question — whether
catalog evidence already satisfies the question, and only lets *residual* questions fall through to
discovery.

This is a mechanism guide, not a results guide. There is no real-corpus measurement of reuse rate,
provider-call reduction, cost, or quality behind any statement below — see
[Known limitations](#known-limitations) and the "Avoided provider calls" note under
[Denial guarantees](#privacydenial-guarantees) for what is and is not claimed.

## What the feature does

Given a research brief, a caller may opt a `search_request` into CARP by setting
`retrieval.policy`. When opted in, CARP:

1. Queries the governed catalog (never raw ledger files) as the authenticated caller's identity.
2. Evaluates every question in the brief against a fixed, six-condition coverage rule (below).
3. Produces a `research_evidence_plan` — a schema-shaped, deterministic record with exactly one
   terminal state (`covered` or `residual`) per question, plus the evidence (`selected_assertion_ref`
   / `retrieval_receipt`) backing every `covered` question.
4. Depending on policy, either stops there (`catalog_only`) or routes only the `residual` questions
   to the existing Search Router providers (`catalog_then_discovery`).

The evidence plan is the sole authoritative record of the coverage/selection decision. A completed
run's `search_run.retrieval` block is an explicitly non-authoritative persisted mirror of that plan's
selections at run-completion time (`mirror_is_authoritative: const false`).

## Prerequisites

CARP's catalog retrieval is gated by the assertion ledger's own capability controls
(`foundry.assertion_ledger` in `foundry.yaml`, resolved by `AssertionLedgerCapabilities` in
`config.py`), the same fail-closed capability seam `run_launch.py`'s manual-reuse path already
uses. **Both of the following must be set to `true` for CARP to ever resolve a question
`covered`:**

- `foundry.assertion_ledger.ledger_write_enabled`
- `foundry.assertion_ledger.automated_reuse_enabled`

**Both default to `false`.** On a stock deployment that has opted a `search_request` into
`catalog_only` or `catalog_then_discovery` but never touched these two controls, CARP is fully
wired and will run — issuing catalog queries, evaluating candidates — but every question will
resolve `residual` / `reuse_denied`, every time, regardless of how good the underlying catalog
evidence is. **This is the fail-closed capability gate working as designed, not a bug or a broken
feature.** If CARP appears to "do nothing" (all questions residual, zero questions covered),
check these two flags before assuming retrieval is broken.

## Policy states

`retrieval.policy` is a closed, three-member enum on `search_request`. **`disabled` is the v1
default, and v1 is opt-in end to end** — there is no implicit network fallback from any state, in
any policy.

| Policy | Behavior |
|---|---|
| `disabled` (default) | Byte-identical to the pre-CARP legacy flow. No catalog query is issued, no evidence plan is created, and no additive metrics block is populated anywhere. A caller that never sets `retrieval.policy` gets exactly today's behavior. |
| `catalog_only` | Query the governed catalog; never call a network provider. An empty or denied catalog result is **terminal for the whole plan** — it does not fall through to discovery, even though residual questions exist. |
| `catalog_then_discovery` | Catalog first, then providers for **residual questions only**. The fallback is explicit and question-level: only a question whose terminal coverage state is `residual` can produce a provider request. A `covered` question never reaches a provider. |

To opt in, set `retrieval.policy` to `catalog_only` or `catalog_then_discovery` on the
`search_request`. Every other CARP-owned surface (`research_evidence_plan`, the `search_run.retrieval`
mirror, `routing_decision.retrieval_policy`/`residual_question_ids`, and `research_brief`'s
per-question `coverage_state`/`residual_reason`) is additive: omitting it validates against the
existing schemas exactly as it did before CARP existed.

## The coverage rule, in plain language

Every question in an evidence plan resolves to **exactly one terminal state**: `covered` or
`residual`. There is no third state and no "pending"/"unknown" state — the plan is a complete,
terminal decision for every question the moment it is built.

A question is `covered` **only if all six** of the following hold for some authorized candidate.
Any failure, any uncertainty, any error, or any constraint the candidate cannot be positively shown
to satisfy resolves the question to `residual` — never to `covered`, and never left unresolved. This
is deliberately conservative (fail-closed): the rule is designed to under-claim coverage rather than
risk claiming it wrongly.

1. **Lexical match** — every required term (case-folded) appears in the candidate's catalog search
   text. This is a literal substring match, not semantic or vector similarity.
2. **Freshly eligible** — the candidate's lifecycle state is re-read as `eligible` immediately before
   selection, not trusted from a possibly-stale earlier snapshot.
3. **Reuse allowed** — the ledger's reuse-evaluation decision for the candidate is `allow`. A
   decision of `refresh` (evidence exists but needs refreshing) or `deny` is residual, not covered.
4. **Constraints satisfiable** — the candidate satisfies every `required_source_types` and
   `required_qualifiers` the question declares. If the candidate can't be *shown* to meet a declared
   constraint, the question is residual — missing data is never treated as a pass.
5. **No contradiction** — no other authorized candidate for the same question contradicts the one
   selected.
6. **Version pinned** — the candidate's exact `assertion_version` is captured and re-checked at
   selection time; a version drift between evaluation and selection is residual.

A `covered` question always carries `residual_reason: null` plus the evidence backing it
(`selected_assertion_ref` + `retrieval_receipt`). A `residual` question always carries exactly one
`residual_reason` code and no selection evidence. These two shapes are schema-enforced and mutually
exclusive — every question lands in exactly one.

## Residual reasons

A `residual` question carries exactly one of 14 closed enum codes:

| Code | What it means operationally |
|---|---|
| `no_candidate` | The catalog returned zero authorized rows for this question. |
| `lexical_miss` | Candidates exist, but none contain all of the question's required terms. |
| `source_type_mismatch` | No candidate could be shown to satisfy the question's `required_source_types`. In v1 this is structurally unsatisfiable whenever a question declares one — see [Known limitations](#known-limitations). |
| `qualifier_missing` | No candidate could be shown to satisfy the question's `required_qualifiers`. |
| `reuse_refresh_required` | The best candidate's reuse evaluation returned `refresh` — the evidence exists but is stale (e.g. edition or extraction-contract drift). |
| `reuse_denied` | The best candidate's reuse evaluation returned `deny` (e.g. rights, sensitivity, or evaluation failure — **or, most commonly by default, `automated_reuse_disabled`: see [Prerequisites](#prerequisites), since `automated_reuse_enabled` defaults to `false`**). |
| `lifecycle_ineligible` | The immediate-before-selection re-read showed a non-`eligible` lifecycle state — the earlier projection was stale. |
| `version_mismatch` | The candidate's pinned `assertion_version` no longer matched at selection time. |
| `contradiction` | A second authorized candidate for the same question contradicts the first. |
| `pagination_limit` | The catalog's shared per-question page budget was exhausted before a qualifying candidate was found. See [Known limitations](#known-limitations) for the arithmetic this implies. |
| `candidate_limit` | The per-question candidate cap was reached before the six conditions could be resolved. |
| `catalog_denied` | The catalog issued a fail-closed denial (missing/cross-workspace identity, rights denial) for the whole plan. |
| `catalog_empty` | The authorized workspace corpus has zero eligible rows at all, for the whole plan. |
| `evaluation_error` | Catch-all for any other uncertain, erroring, or unrepresentable state, including a catalog rebuild detected mid-plan. Conservative by construction. |

## Limits

All limits are schema-validated, not just conventionally observed:

| Limit | Ceiling |
|---|---|
| `max_questions` per plan | 200 |
| `max_candidates_per_question` | 50 |
| `max_pages_per_question` | 5 |
| Catalog page size | ≤100 rows |

`max_pages_per_question` is a budget **shared across every required-term sub-query for one
question**, not a per-term-query allowance — see [Known limitations](#known-limitations).

## Privacy/denial guarantees

A denied or unauthorized caller receives **zero candidate-derived fields**. Every counter that could
be derived from catalog candidates — `questions_covered`, `questions_residual`,
`candidates_evaluated`, `candidates_selected`, `avoided_provider_calls`, `residual_reason_counts`,
and catalog `facets` — is forced to `0` or omitted on denial. This mirrors the catalog's own existing
denial shape (`items: []`, `next_cursor: null`, `facets` zeroed, a non-null `denial_reason`).

**`questions_total` is the one safe echo.** It is copied from the *request* (the brief's own question
count) rather than derived from the corpus, so it may appear on a denied summary without leaking any
signal about what the catalog actually holds.

A `refresh`-required reuse decision is visible only inside `evaluated_candidates[]` on a plan built
for an authorized identity inside the owning workspace. A denied or cross-workspace caller's
`evaluated_candidates` is always empty (or the plan's `questions` array itself is empty in the
fail-closed case) — the denial path returns before any candidate is ever evaluated, so there is no
code path that could populate refresh-state for it to leak.

**"Avoided provider calls" is a counter definition, not a savings claim.** `avoided_provider_calls`
counts questions that resolved `covered` and therefore did not produce a provider request in this
run. It is an observed, per-run count — it is not evidence of realized cost savings, reuse rate, or
quality uplift across any corpus, because no such real-corpus measurement exists (see below).

## Known limitations

These are accepted, documented gaps in v1 — not aspirational future work, and not silently patched
over:

- **`required_extraction_contract` matching is advisory only.** The field it's projected from
  (`extraction_provenance.schema_version`, effectively `EXTRACTION_FACT_CLAIM_MAPPING_VERSION`) is a
  near-global constant today — almost every assertion in the ledger carries the same value. This
  means the `extraction_refresh_required` residual path cannot yet discriminate between two
  genuinely different extraction methodologies. A future extraction-contract axis would need a new,
  separately-versioned, per-extraction field on `source_assertion` — not a change to this matching
  logic.
- **No independent sensitivity field on the ledger.** The sensitivity axis used by the coverage rule
  is now correctly gated (ranked against a caller-supplied threshold, never silently defaulted to
  "no ceiling"), but it is still derived from `source_edition.access_scope` plus
  `allowed_use.allowed_for_work_output` — there is no sensitivity field on the ledger that is
  independent of those two. A caller of the retrieval layer must always pass an explicit
  sensitivity threshold; omitting one denies every candidate rather than granting an implicit
  ceiling.
- **Pagination-arithmetic limitation (fail-closed by design).** `max_pages_per_question` is a single
  budget shared across every required-term sub-query for one question. A question whose distinct
  required-term count is high enough to exhaust that shared budget resolves `residual` /
  `pagination_limit` even if qualifying catalog evidence exists further down the result set. This is
  the frozen contract's deliberate, conservative resolution of a real tension (more terms could
  otherwise demand more pages than the budget allows) — it is not a bug, and it is not tuned per
  question; it applies uniformly.
- **A question/query that is empty or whitespace-only is fail-closed, same as
  a contentless one.** The plan-construction boundary forces a question
  terminal `residual`/`evaluation_error` whenever no required term survives
  derivation — whether because every token derived from non-empty source
  text fails the 3-character floor (e.g. "is it up?"), or because the source
  text itself is empty/all-whitespace (e.g. `search_request.query == ""`,
  which has no schema `minLength` and is not schema-rejected). `required_terms`
  at this boundary is always derived from the question's source text, never a
  caller declaration, so an empty derived term set is always a derivation
  outcome and never reaches `catalog_retrieval.retrieve()`'s condition 1.
- **`required_source_types` is structurally unsatisfiable in v1.** No `source_type` field is
  reachable through the catalog packet a question is evaluated against — that field exists only on
  `source_card.schema.yaml`, which the packet the planner reads never carries. Any question that
  declares a non-empty `required_source_types` therefore always resolves `residual` /
  `source_type_mismatch`, regardless of how good the underlying evidence is. A question that omits
  `required_source_types` is unaffected (the constraint is vacuous). Closing this gap requires
  exposing `source_type` through the catalog read surface, not a change to the coverage rule itself.

None of the above is a defect requiring immediate remediation — each is either a deliberate
fail-closed design choice or a real contract gap the frozen contract (`carp-contract-freeze.md` §3.6,
§8.2) named in advance of implementation. This feature has not been measured against a real corpus,
is not claimed production-default-eligible, and no deployment or release decision is implied by this
document.
