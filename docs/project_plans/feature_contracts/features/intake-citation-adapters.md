---
title: "Feature Contract: Intake Adapters → Normalized Citation Tuple"
schema_version: 2
doc_type: feature_contract
status: draft
created: 2026-06-23
updated: 2026-06-23
feature_slug: "intake-citation-adapters"
category: "features"
estimated_points: 8
tier: 2
owner: null
priority: medium
risk_level: medium
changelog_required: true
related_documents:
  - docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md
spike_ref: null
prd_ref: null
plan_ref: null
commit_refs: []
pr_refs: []
files_affected: []
---

# How To Use This Template

This contract derives from completed research run **RIB-053** (IntentTree node
`node_01KVQYN8SJYKBAX7F24MPN9CJR`, high evidence). At **8 points / Tier 2** it sits at the upper
boundary of the Feature Contract envelope; it is authored as a single contract because the three
deliverables share one normalization surface and one fixture-driven test harness. If contract review
finds the citation-tuple schema design genuinely contentious (see §11 / Open Design Questions),
**carve the schema decision out as a SPIKE** and re-scope this contract to consume the SPIKE verdict
rather than stretching it further.

1. Submit for review (Opus design block + brief sanity pass).
2. Once approved, delegate the entire contract to a single `feature-sprint-executor` agent for autonomous implementation.
3. Mandatory `task-completion-validator` review of the completion report against acceptance criteria and validation requirements.
4. Opus commits if review passes.

---

# Feature Contract: Intake Adapters → Normalized Citation Tuple

## 1. Goal

Build RF intake adapters that normalize external research-tool outputs (OpenAI, Perplexity first)
into a typed, schema-validated citation tuple `{span, source, relation, confidence}`, feeding existing
`source_candidates` / source-card capture with **idempotent URL+date dedup** so re-intake of the same
source is a no-op.

---

## 2. User / Actor

- **Primary user**: RF operator / discovery swarm running a research run who wants external
  research-tool outputs pulled into RF as governed source candidates without manual normalization.
- **Secondary users**: RF maintainers/agents (the `rf_source_carder` / discovery pipeline) that
  consume normalized `source_candidates` downstream; the claim ledger, which inherits provenance from
  the captured source cards.

---

## 3. Job To Be Done

When **an external research tool (OpenAI deep-research / Perplexity) returns answer text with
citations**, the operator wants to **normalize each citation into a uniform `{span, source, relation,
confidence}` tuple and capture it as a deduplicated source candidate**, so they can **fold
heterogeneous research-tool outputs into one evidence-first RF pipeline without re-pulling or
hand-shaping each tool's idiosyncratic format**.

---

## 4. Scope

### In Scope

- **Normalized citation-tuple structure** `{span, source, relation, confidence}` — a typed dataclass
  (default; see §11) plus an optional JSON-Schema sidecar for fixture/round-trip validation. Defines
  field semantics: `span` (the cited text span / locator within the tool's answer), `source` (the
  source descriptor shaped toward the `source_card` schema — url, title, accessed/published date),
  `relation` (supports / contradicts / mentions / background, aligned with the downstream
  `claim_ledger.sources[].relation` vocabulary), `confidence` (0.0–1.0 float).
- **OpenAI intake adapter** — implements the existing `Adapter` protocol (`adapters/base.py`),
  `available()`-gated and offline-safe / degraded-mode capable like the existing adapters; parses
  OpenAI response/citation fixtures into normalized tuples and emits `AdapterResult.source_candidates`
  shaped per the `source_card` schema.
- **Perplexity intake adapter** — same protocol/contract as the OpenAI adapter; parses Perplexity
  `citations` / `search_results` fixtures into normalized tuples.
- **Idempotent URL+date dedup** — a shared dedup helper (default location; see §11) keyed on
  normalized `(url, date)`; re-intake of an already-captured source is a no-op. Used by both new
  adapters and available for wiring into `services/intake.py` capture.
- **Unit tests over fixtures** for: tuple construction/validation, both adapters' parse paths
  (offline), and dedup idempotency (re-intake = no-op).

### Out of Scope

- Adapters beyond OpenAI and Perplexity (Anthropic, Gemini, Exa, Tavily, etc.) — **follow-ups**, note
  in the Completion Report; the protocol must make adding them mechanical.
- **Live-key validation runs** against real OpenAI/Perplexity endpoints — offline-first; fixtures only.
  Live `available()` + real-call validation is a follow-up.
- Changes to the `claim_ledger` `sources` array shape or the downstream claim pipeline — the citation
  tuple is an **intake-normalization** structure, distinct from the ledger's persisted
  `{source_card_id, evidence_id, relation, locator}` shape; do not refactor the ledger here.
- Rewriting `intake_from_intenttree()` / `intake_from_notebooklm()` — they may optionally call the new
  dedup helper, but their existing raw-idea/source pull behavior is not in scope.
- UI / runs-viewer surfacing of citation tuples.

---

## 5. UX / Behavior Requirements

- Each new adapter is discoverable through the same registration path as existing concrete adapters
  (`adapters/__init__.py` registry pattern) and exposes the standard `Adapter` protocol surface.
- `available()` returns `False` (degraded mode) when the relevant API key is absent — the adapter must
  still import, register, and run its **fixture/offline** parse path without raising.
- Given a tool-output fixture, the adapter emits a deterministic list of normalized tuples, each
  convertible to a `source_candidate` dict shaped per `source_card.schema.yaml`.
- Re-running intake on a source whose `(url, date)` already exists is a **no-op**: no duplicate
  candidate/card is produced; the operation reports "already captured" rather than erroring.
- Malformed / partial citations (missing url or date) are handled gracefully: skipped-with-warning or
  captured with an explicit low/`null` confidence and a dedup key fallback — choose one and document it;
  never crash the batch.
- Output ordering and tuple field population are stable across runs for the same fixture (deterministic,
  no `Date.now`/random in normalization).

---

## 6. Data Requirements

- **Entities affected**: new in-memory `CitationTuple` structure; `AdapterResult.source_candidates`
  (existing `list[dict]`, source_card-shaped) populated by the two new adapters; optional new
  JSON-Schema file for the citation tuple.
- **New fields / structures**:
  - `CitationTuple` (dataclass): `span: str`, `source: dict` (source_card-shaped subset:
    url/title/date/access), `relation: str` (enum-constrained to the relation vocabulary),
    `confidence: float` (0.0–1.0).
  - Optional `schemas/citation_tuple.schema.yaml` (or `.json`) for round-trip fixture validation.
- **State changes**: dedup helper maintains/consults a seen-set keyed on normalized `(url, date)`
  within an intake batch (and, where wired, against already-captured candidates) so capture is
  idempotent.
- **Storage implications**: none new beyond existing source-card / `source_candidates` persistence;
  no migrations. Dedup is computed over existing capture state, not a new store.

---

## 7. API / Integration Requirements

**New or modified internal surfaces:**
- `OpenAIIntakeAdapter` (new) — `Adapter` protocol impl; `available()` + parse(fixture) → tuples → `AdapterResult`.
- `PerplexityIntakeAdapter` (new) — same contract.
- `CitationTuple` + `to_source_candidate()` (new) — normalization structure and its source_card-shaped projection.
- Dedup helper (new) — `is_duplicate((url, date), seen)` / `dedup(candidates)`; idempotent.

**External service calls** (degraded-mode / offline-first):
- OpenAI API — **not called** in this contract; adapter parses fixtures. `available()` gates real use.
- Perplexity API — same; fixtures only.

**Internal service dependencies:**
- `adapters/base.py` — `Adapter` protocol + `AdapterResult` (existing; must be followed, not changed).
- `schemas/source_card.schema.yaml` — target shape for `source_candidates`.
- `services/intake.py` — optional consumer of the dedup helper; not refactored here.

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `src/research_foundry/adapters/base.py` — `Adapter` protocol + `AdapterResult` dataclass (the
  `source_candidates: list[dict]` contract).
- Existing concrete adapters (`gpt_researcher.py`, `paperqa2.py`, `litellm_router.py`, `notebooklm.py`,
  etc.) — registration, `available()` degraded-mode gating, and offline-safe parse style.
- `schemas/source_card.schema.yaml` — the shape `source_candidates` dicts must conform to.

**Must not change** (protected areas):
- The `Adapter` protocol / `AdapterResult` signature (additive only; do not break existing adapters).
- `claim_ledger` `sources` array shape and the claim pipeline.
- `intake_from_intenttree()` / `intake_from_notebooklm()` existing behavior.

**New dependencies:**
- Allowed? **No** (prefer none). Reuse stdlib + existing schema-validation utilities already in RF.
  If a citation tuple needs validation tooling, prefer whatever RF already uses for
  `source_card.schema.yaml`. If a new dep appears genuinely necessary, **stop and flag** in the
  Completion Report before adding it.

---

## 9. Acceptance Criteria

- [ ] Normalized citation-tuple structure `{span, source, relation, confidence}` is defined as a typed
      dataclass and is either schema-validated (sidecar) or fully type-annotated, with `relation`
      constrained to the documented vocabulary and `confidence` a 0.0–1.0 float.
- [ ] `CitationTuple.to_source_candidate()` produces a dict conforming to `source_card.schema.yaml`.
- [ ] OpenAI intake adapter parses an offline fixture into a deterministic list of normalized tuples
      and emits them via `AdapterResult.source_candidates`; `available()` returns `False` with no key
      and the fixture path still runs without raising.
- [ ] Perplexity intake adapter does the same against a Perplexity-shaped fixture.
- [ ] URL+date dedup is idempotent: re-intake of an already-captured source produces no duplicate and
      reports a no-op (verified by a unit test that runs intake twice).
- [ ] Malformed/partial citations are handled per the documented policy (skip-with-warning or
      low-confidence capture) and never crash the batch.
- [ ] Both new adapters are registered and discoverable via the existing adapter registry path.
- [ ] Unit tests cover tuple construction/validation, both adapter parse paths, and dedup idempotency,
      and all pass offline (no network).

---

## 10. Validation Requirements

- [ ] **Typecheck** passes (`mypy src/research_foundry --ignore-missing-imports` on changed modules)
- [ ] **Lint** passes (`flake8 src/research_foundry --select=E9,F63,F7,F82`; `black` formatted)
- [ ] **Tests** added for the citation tuple, both adapters, and dedup idempotency
- [ ] **Relevant tests pass** (run under the venv: `./.venv/bin/python -m pytest` — NOT the pyenv shim,
      per the "pytest must run under venv" memory; for worktree code set
      `PYTHONPATH=<worktree>/src` against the main venv per RF test-suite gotchas)
- [ ] **Build** passes (package imports cleanly; adapters register)
- [ ] **Docs updated** — CHANGELOG entry (changelog_required: true); note new adapters in the
      adapter/intake reference if one exists
- [ ] **No unrelated changes** introduced (no ledger refactor, no touching existing intake functions
      beyond optional dedup wiring)

---

## 11. Risk Areas

- **Open Design Question — tuple as dataclass vs schema file** (DEFAULT: **typed dataclass + optional
  JSON-Schema sidecar for fixture validation**). Rationale: dataclass gives ergonomic, type-checked
  construction in adapter code and mirrors the existing `AdapterResult` dataclass style; the sidecar
  schema lets fixtures round-trip-validate without coupling runtime to a validator. **If this proves
  contentious in review, carve it out as a SPIKE** and let this contract consume the verdict.
- **Open Design Question — adapter namespace: existing `/adapters/` vs new `/intake_adapters/`**
  (DEFAULT: **`/adapters/`**). Rationale: these implement the same `Adapter` protocol and emit
  `AdapterResult.source_candidates`; splitting namespaces would fork the registry and the protocol for
  no functional gain. Note conceptual "discovery vs intake" distinction in a docstring/comment instead.
- **Open Design Question — dedup location: shared helper vs inline in capture** (DEFAULT: **shared
  helper module**). Rationale: both new adapters need it now and `services/intake.py` may adopt it
  later; a shared, independently-testable helper is the idempotency seam. Inline-in-capture would
  duplicate logic and resist the idempotency unit test.
- **Relation vocabulary drift**: the intake `relation` must align with the downstream
  `claim_ledger.sources[].relation` vocabulary; mismatch would force a remap later. Mitigation:
  source the enum from the same vocabulary and document the mapping.
- **source_card shape coupling**: `to_source_candidate()` must track `source_card.schema.yaml`; if the
  schema has required fields the fixtures don't supply, capture could fail validation. Mitigation:
  validate the projection against the schema in a unit test.
- **Dedup key edge cases**: URL canonicalization (trailing slash, query params, scheme) and
  date-format variance can break idempotency. Mitigation: normalize both before keying; cover with a
  fixture pair that differs only cosmetically.
- **Tier boundary**: at 8 pts this is at the top of the contract envelope; if the schema SPIKE carve-out
  fires, remaining scope drops comfortably back into Tier 1/2 contract range.

---

## 12. Implementation Notes

**Suggested approach** (agent may improve):
- Step 1: Define `CitationTuple` (dataclass) + `relation` enum sourced from the ledger relation
  vocabulary + `to_source_candidate()` projection; add the optional schema sidecar and a round-trip
  validation test against `source_card.schema.yaml`.
- Step 2: Implement the shared dedup helper keyed on normalized `(url, date)` with URL canonicalization;
  unit-test idempotency (intake twice = one candidate).
- Step 3: Implement `OpenAIIntakeAdapter` and `PerplexityIntakeAdapter` against the `Adapter` protocol,
  `available()`-gated, parsing committed fixtures into tuples → `source_candidates`; register both.
- Step 4: Wire dedup into the adapters' emit path; add fixtures and tests; run validation under the venv.

**Similar existing code**:
- Reference: `src/research_foundry/adapters/base.py` (protocol + `AdapterResult`), and a concrete
  adapter such as `litellm_router.py` / `gpt_researcher.py` for `available()` degraded-mode + offline
  parse shape.
- Reason: keep the new adapters protocol-compatible and registry-discoverable with zero changes to
  existing adapters.

**Known gotchas**:
- Run pytest under the venv (`./.venv/bin/python -m pytest`), not the pyenv shim, or you hit the
  "No module named research_foundry" bag error.
- For worktree execution, the editable install points at main — set `PYTHONPATH=<worktree>/src` and
  run with the main venv interpreter (RF test-suite gotchas).
- Keep normalization deterministic — no `Date.now`/random — so fixture tests are stable.
- `relation` and `source` must align to existing vocab/schema, not invent parallel ones.

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: List of all modified/new files with brief reason
- **Tests run**: What tests were added/updated and results
- **Validation results**: Table of all validation commands and their results (pass/fail/not applicable)
- **Deviations from contract**: Any material changes to the contract during implementation and why —
  in particular, whether the citation-tuple schema decision held as a dataclass+sidecar or was carved
  out as a SPIKE, and the resolved defaults for the three Open Design Questions.
- **Risks / Limitations**: Any remaining risks or known limitations (esp. unvalidated live-key paths)
- **Follow-up recommendations**: Additional adapters (Anthropic/Gemini/Exa/Tavily), live-key
  validation runs, and any `services/intake.py` dedup wiring left undone.

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion Report template.

---

## Metadata & References

**Tier**: 2 (8 points — upper boundary; SPIKE carve-out available if schema design is contentious)

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion, no phase orchestration

**Reviewer**: `task-completion-validator` (mandatory)

**Related Documents**:
- `docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md` — RIB-053 harvest report (origin)
- `src/research_foundry/adapters/base.py` — `Adapter` protocol + `AdapterResult` (pattern to follow)
- `schemas/source_card.schema.yaml` — target shape for `source_candidates`
- `src/research_foundry/services/intake.py` — existing intake integrations (optional dedup consumer)

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass validation. If you find:

- **Scope ambiguity**: Ask one focused question or make a conservative assumption and note it in the Completion Report.
- **Impossible constraints**: Flag in the Completion Report before attempting workarounds.
- **Better implementation path**: Document the deviation in the Completion Report with justification.
- **Schema design contention**: If the citation-tuple schema design becomes genuinely contentious,
  stop and recommend a SPIKE carve-out rather than over-building inside this contract.

Stay within scope. Avoid cleanup, refactors, or feature expansion beyond this contract. The reviewer will check for scope drift.
