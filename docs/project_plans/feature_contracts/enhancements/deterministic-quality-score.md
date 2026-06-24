---
title: "Feature Contract: Deterministic quality_score for CCDash telemetry"
schema_version: 2
doc_type: feature_contract
status: draft
created: 2026-06-23
updated: 2026-06-23
feature_slug: "deterministic-quality-score"
category: "enhancements"
estimated_points: 5
tier: 1
owner: null
priority: medium
risk_level: low
changelog_required: true
related_documents:
  - docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md
spike_ref: null
prd_ref: null
plan_ref: null
commit_refs: []
pr_refs: []
files_affected:
  - src/research_foundry/services/telemetry.py
  - tests/
---

# Feature Contract: Deterministic quality_score for CCDash telemetry

## Provenance

This contract derives from a completed Research Foundry research run (high-confidence
conclusion):

- **Backlog idea**: RIB-042 (`backlog/research_idea_backlog.yaml`)
- **IntentTree node**: `node_01KVQYMT6GF0T5PS1QK469DJ2J`
- **Harvest report**: `docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md`

The research conclusion recommends a **deterministic composite `quality_score`** computed
from claim-ledger ratios with **support_rate dominant**, a new **`distinct_source_domains`**
signal, a **per-dimension vector** emitted alongside the scalar (not just a single number),
and **Goodhart caps** that prevent the metric from being gamed by inflating one easy
dimension.

**Composes with** (do not implement here, but design to be compatible):

- **RIB-025 — citation metrics**: shares the source-locator surface that
  `distinct_source_domains` reads. Keep domain extraction reusable.
- **RIB-041 — eval harness**: `quality_score` and its dimension vector are the signal the
  eval harness will **regression-gate** on. The scoring function must be deterministic and
  pure so the harness can assert exact values across runs.

---

## 1. Goal

Replace the hard-coded `quality_score: "pending"` in the CCDash event with a deterministic,
unit-testable composite float in `[0, 1]` (support_rate-dominant), emit a per-dimension
quality vector and `support_rate` and `distinct_source_domains` in the event metrics, and
apply Goodhart caps so a run cannot inflate the composite by gaming a single easy dimension.

---

## 2. User / Actor

- **Primary user**: The RF operator / orchestrator reading CCDash events to judge run
  quality at a glance and to compare runs.
- **Secondary users**: The (future) RIB-041 eval harness, which consumes `quality_score` +
  the dimension vector as a regression gate; and the run rollup (`summarize()`) for fleet-
  level quality reporting.

---

## 3. Job To Be Done

When **a research run finishes and emits its CCDash event**, the operator (and downstream
eval harness) wants to **read a single trustworthy quality number plus the per-dimension
breakdown that produced it**, so they can **judge run quality, spot gaming, and gate
regressions without re-reading the full claim ledger**.

---

## 4. Scope

### In Scope

- A new **pure scoring function** in `services/telemetry.py` (e.g. `compute_quality(counts,
  distinct_source_domains) -> QualityResult`) that takes claim-status counts plus the domain
  count and returns the composite scalar, the per-dimension vector, and the intermediate
  ratios — deterministic, no I/O, no clock, no randomness.
- **Composite `quality_score`** as a float in `[0, 1]`, **support_rate-dominant** (support_rate
  carries the largest weight in the weighted combination; document the exact weights).
- A **per-dimension vector** emitted in the event. Defensible dimension set (document each):
  - `support_rate` = `claims_supported / claims_total`
  - `domain_diversity` = a bounded transform of `distinct_source_domains` (e.g. saturating
    function so diversity contributes but cannot dominate; document the saturation point)
  - `inference_ratio` = `(claims_inference + claims_speculation) / claims_total` (penalty
    dimension — higher is worse; contributes inverted to the composite)
  - `contradiction_penalty` = derived from `(claims_contradicted + claims_mixed) /
    claims_total` (penalty dimension — higher is worse; contributes inverted)
- A new **`distinct_source_domains`** metric: count of unique domains extracted from cited
  source locators / URLs across the run's source cards (or claim-ledger source references —
  pick the surface that is reliably populated and document it).
- **`support_rate`** surfaced directly in `metrics`.
- **Goodhart caps**: deterministic cap rules that reduce the composite when the dimension
  profile indicates gaming. At minimum: **cap the composite when `domain_diversity` is high
  but `support_rate` is low** (many domains cited, few claims actually supported → the
  diversity contribution is clamped so it cannot lift a low-support run). Document the exact
  cap rule(s) and the cap value.
- **Zero-claim run** handling: a run with `claims_total == 0` must not divide-by-zero or
  raise. Define its score explicitly (see Acceptance Criteria — `0.0` with documented
  rationale, OR `null`/`None` with rationale; pick one and document).
- **Unit tests** over fixture ledgers asserting exact composite scores, exact dimension
  vectors, the Goodhart-cap reduction on a gaming fixture, and the zero-claim case.
- Wire the computed values into `emit_ccdash_event()` so the emitted event carries the real
  scalar, the vector, `support_rate`, and `distinct_source_domains`.

### Out of Scope

- **Learned / ML weights** for the composite — weights are fixed constants in v1.
- **Per-intent tunable policy files** (e.g. different weights per research domain). *Deferred
  follow-up*: note this as the natural next iteration once RIB-041's eval harness can measure
  whether tuning helps.
- Surfacing `quality_score` in the rollup `summarize()` / `_Rollup` aggregation. *Deferred
  follow-up* — note it; the scalar is per-run here, fleet aggregation is a separate change.
- Any UI / runs-viewer surfacing of the new fields.
- Changing the CCDash event **schema** beyond what is needed to carry the new fields (if the
  `ccdash_event` schema validation rejects the new keys, prefer the minimal additive schema
  change and document it; do not restructure existing metrics).

---

## 5. UX / Behavior Requirements

- After a run with ≥1 claim, the emitted CCDash event's `metrics.quality_score` is a **float
  in `[0, 1]`** — never the string `"pending"`.
- The event carries a **per-dimension vector** (e.g. under `metrics.quality_dimensions` or an
  equivalent documented key) with the four named dimensions, each a float in `[0, 1]`.
- The event carries `metrics.support_rate` (float in `[0, 1]`) and
  `metrics.distinct_source_domains` (non-negative integer).
- For a **gaming profile** (high domain diversity, low support_rate), the emitted composite
  is **demonstrably lower** than the same dimensions would yield without the Goodhart cap.
- For a **zero-claim run**, emission **completes without error** and `quality_score` is the
  defined sentinel (documented `0.0` or `null`).
- Determinism: the same ledger + same source cards always produce the **same** scalar and
  vector (no clock, no randomness, no dict-ordering dependence).

---

## 6. Data Requirements

- **Entities affected**: the CCDash `execution_event` emitted by `emit_ccdash_event()` and
  mirrored to `ccdash/events/<event_id>.yaml`.
- **New fields** (in `event.metrics`):
  - `quality_score`: float in `[0, 1]` (replaces the `"pending"` string) — or documented
    sentinel for zero-claim runs.
  - `support_rate`: float in `[0, 1]`.
  - `distinct_source_domains`: non-negative integer.
  - per-dimension vector (e.g. `quality_dimensions`: mapping of dimension name → float).
- **State changes**: none persisted beyond the emitted event YAML files (telemetry is
  file-backed and already written atomically by the existing emit path).
- **Storage implications**: none beyond the additive metric keys. If `ccdash_event` schema
  validation is active and rejects new keys, add the minimal additive schema entries.

---

## 7. API / Integration Requirements

**New or modified internal functions** (in `src/research_foundry/services/telemetry.py`):

- New pure function `compute_quality(...)` — takes the `_ledger_counts()` dict plus
  `distinct_source_domains`; returns composite + vector + ratios. Pure, deterministic.
- New helper to count `distinct_source_domains` from the run's cited sources (reuse the
  source-card / source-locator surface — keep reusable for RIB-025).
- Modified `emit_ccdash_event()` (≈lines 126–233) to call the above and populate the real
  metrics instead of `"pending"` (≈line 202).

**External service calls**: none.

**Internal service dependencies**:

- `_ledger_counts()` (≈lines 54–75) — already returns the six per-status counts plus
  `claims_total`; consume as-is.
- The run's source cards (`rp.sources`, already globbed by `_count_files` at ≈line 142) or
  the claim-ledger source references — for domain extraction.

---

## 8. Architecture Constraints

**Must follow existing patterns in:**

- `src/research_foundry/services/telemetry.py` — module-private helpers (`_safe_load`,
  `_ledger_counts`, `_verification`); keep the new scorer a pure helper and the domain
  counter a small private helper. Match the existing typing/`from __future__ import
  annotations` style.
- Existing test layout under `tests/` for telemetry — add fixture-ledger-driven unit tests
  alongside existing telemetry tests.

**Must not change** (protected areas):

- The existing `metrics` keys and their meanings (`claims_total`, `claims_supported`,
  `unsupported_claims`, `verification_passed`, etc.) — additive only.
- The event id / mirror disambiguation logic (≈lines 155–166).
- `emit_latest_or_noop()` hook safety contract — emission must still never raise inside the
  stop-hook path for normal runs (zero-claim included).

**New dependencies:**

- Allowed? **No.** Use the Python stdlib only (`urllib.parse` for domain extraction is fine).
  *No new third-party dependencies expected.*

---

## 9. Acceptance Criteria

- [ ] For a run with ≥1 claim, `metrics.quality_score` is a **computed float in `[0, 1]`** and
      is **never** the string `"pending"`.
- [ ] The composite is **support_rate-dominant** — documented weights give `support_rate` the
      largest single weight, verified by a unit test that perturbs only support_rate and shows
      the largest composite movement.
- [ ] The **per-dimension vector** (support_rate, domain_diversity, inference_ratio,
      contradiction_penalty) is emitted in the CCDash event, each a float in `[0, 1]`.
- [ ] `metrics.support_rate` is emitted and equals `claims_supported / claims_total`.
- [ ] `metrics.distinct_source_domains` is emitted as a non-negative integer counted from the
      run's cited sources (unique domains).
- [ ] **Goodhart cap demonstrably reduces the score**: a gaming fixture (high
      `domain_diversity`, low `support_rate`) yields a composite strictly lower than the
      uncapped weighted combination of the same dimensions — asserted by a unit test.
- [ ] **Unit tests over fixture ledgers assert exact composite scores** and exact dimension
      vectors (not just ranges) for at least: a high-quality run, a low-support run, and the
      gaming run.
- [ ] A **zero-claim run does not error**: emission completes and `quality_score` is the
      documented sentinel (`0.0` or `null`/`None`), covered by a unit test.
- [ ] The scoring function is **deterministic and pure** — same inputs always produce the
      same outputs (no clock/random/ordering dependence), covered by a repeat-invocation test.

---

## 10. Validation Requirements

- [ ] **Lint** passes (`flake8 src/research_foundry/services/telemetry.py --select=E9,F63,F7,F82`)
- [ ] **Format** clean (`black src/research_foundry/services/telemetry.py`)
- [ ] **Typecheck** passes (`mypy src/research_foundry/services/telemetry.py --ignore-missing-imports`)
- [ ] **Tests** added for the scorer, the domain counter, the Goodhart cap, and the zero-claim path
- [ ] **Relevant tests pass** — run telemetry tests under the venv interpreter:
      `./.venv/bin/python -m pytest tests/ -k telemetry` (NOT the pyenv shim — see RF memory
      "pytest must run under venv")
- [ ] **Docs updated** — CHANGELOG entry (changelog_required: true); document the formula,
      weights, dimension definitions, Goodhart cap rules, and the zero-claim sentinel inline
      (docstring) and/or in the telemetry doc.
- [ ] **No unrelated changes** introduced

---

## 11. Risk Areas

- **Metric design / weight defensibility**: the chosen weights and cap rule are judgment
  calls. Mitigation: document them explicitly with rationale; keep them named constants so
  RIB-041's eval harness can later challenge/tune them.
- **Domain extraction reliability**: cited source locators may be missing, malformed, or
  non-URL (file paths, DOIs). Mitigation: extract conservatively (`urllib.parse`), skip
  un-parseable locators, and count distinct registrable domains; never raise on a bad locator.
- **Schema validation**: if `ccdash_event` schema validation is active (≈lines 222–227), new
  metric keys could fail validation. Mitigation: make the schema change additive and minimal;
  verify the validate() path still passes.
- **Determinism trap**: domain counting over a directory glob or a set must produce a stable
  result independent of filesystem ordering. Mitigation: sort/normalize before counting; the
  count is order-independent by construction but the tests must assert it.
- **Hook safety**: zero-claim and missing-ledger runs flow through `emit_latest_or_noop()`;
  the new code must not introduce a raise on that path.
- **Downstream coupling (RIB-041)**: exact-value tests pin the formula; any later weight
  change will (intentionally) break them — that is the regression gate, but note it so a
  future tuning PR expects to update fixtures deliberately.

---

## 12. Implementation Notes

**Suggested approach** (agent may improve):

- Step 1: Add a small frozen result type (e.g. `@dataclass(frozen=True) class QualityResult`)
  carrying `score: float | None`, `dimensions: dict[str, float]`, and the raw ratios.
- Step 2: Implement `compute_quality(counts, distinct_source_domains)` — compute the four
  dimensions, combine with documented support_rate-dominant weights, apply the Goodhart
  cap(s), clamp to `[0, 1]`, and handle `claims_total == 0` up front.
- Step 3: Implement `_distinct_source_domains(rp)` — read cited source locators from the
  source cards (or claim ledger), normalize via `urllib.parse.urlsplit().hostname`, lowercase,
  drop `www.`, count uniques; non-URL/empty locators are skipped.
- Step 4: In `emit_ccdash_event()`, call both, then replace the `"pending"` literal (≈line
  202) and add `support_rate`, `distinct_source_domains`, and the dimension vector to
  `metrics`.
- Step 5: Add fixture ledgers + tests asserting exact scores/vectors, the cap reduction, and
  the zero-claim sentinel; assert determinism by calling twice.

**Similar existing code**:

- Reference: `_ledger_counts()` (≈lines 54–75) and `_count_files()` (≈lines 78–84) in
  `services/telemetry.py`.
- Reason: same module conventions for reading run artifacts and returning plain dict/int
  results; the scorer should slot in beside them as a pure helper.

**Known gotchas**:

- `quality_score` is currently the literal string `"pending"` at ≈line 202 — replacing it
  changes the field's type from `str` to `float`/`None`; check the `ccdash_event` schema and
  any consumer that assumed a string.
- Run tests under `./.venv/bin/python -m pytest` (or `uv run pytest`); the pyenv shim raises
  `No module named research_foundry` (RF memory: "pytest must run under venv").
- In a worktree, validating against worktree code needs
  `PYTHONPATH=<wt>/src <main>/.venv/bin/python` because the editable install points at main
  (RF memory: "RF test-suite gotchas").

---

## 13. Completion Report Required

The executing agent must produce a Completion Report including:

- **Files changed**: List of all modified/new files with brief reason
- **Tests run**: What tests were added/updated and results
- **Validation results**: Table of all validation commands and their results (pass/fail/not applicable)
- **Deviations from contract**: Any material changes to the contract during implementation and why
  — in particular, the final dimension set, weights, Goodhart cap rule(s), and zero-claim sentinel chosen
- **Risks / Limitations**: Any remaining risks or known limitations
- **Follow-up recommendations**: Suggested next steps (per-intent tunable weights, rollup
  aggregation, RIB-025 / RIB-041 wiring)

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion Report template.

---

## Metadata & References

**Tier**: 1 (3–8 points)

**Execution Mode**: Autonomous Feature Sprint (Mode C) — single sprint to completion, no phase orchestration

**Reviewer**: `task-completion-validator` (mandatory)

**Related Documents**:
- Harvest report: `docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md`
- Source: `services/telemetry.py::emit_ccdash_event()` (≈lines 126–233), `_ledger_counts()` (≈lines 54–75)
- Composes with: RIB-025 (citation metrics), RIB-041 (eval harness — regression-gates this signal)

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass validation. If you find:

- **Scope ambiguity**: Ask one focused question or make a conservative assumption and note it in the Completion Report.
- **Impossible constraints**: Flag in the Completion Report before attempting workarounds.
- **Better implementation path**: Document the deviation in the Completion Report with justification.

Stay within scope. Avoid cleanup, refactors, or feature expansion beyond this contract. The reviewer will check for scope drift.
