---
title: "Feature Contract: Two-Leg Eval Harness (RIB-041)"
schema_version: 2
doc_type: feature_contract
status: draft
created: 2026-06-23
updated: 2026-06-23
feature_slug: "two-leg-eval-harness"
category: "infrastructure"
estimated_points: 8
tier: 2
owner: null
priority: high
risk_level: medium
changelog_required: true
related_documents:
  - "docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md"
spike_ref: null
prd_ref: null
plan_ref: null
commit_refs: []
pr_refs: []
files_affected: []
intenttree_node: "node_01KVQYMNG71TW5YJV3KA3HPM6G"
---

# How To Use This Template

> **Tier/format note.** This is a **Tier 2 (8-point)** body of work authored as a **phased Feature
> Contract** rather than a full PRD + Implementation Plan, because the surface area is well-understood
> infrastructure (test cassettes + an eval runner + two CI workflows) with no novel domain modeling.
> The contract is split into two phases (§4): **Phase 1 (the PR-gating deterministic leg) is the
> deliverable that must land first and is independently shippable;** Phase 2 (the nightly live leg)
> reuses Phase 1's eval runner and golden set. **Flag:** if Phase 2's score-delta / baseline-management
> design balloons during implementation (e.g. baselines need their own storage/versioning model, or the
> live leg needs nontrivial provider orchestration), **split Phase 2 into its own Tier 1 Feature
> Contract** and ship Phase 1 standalone rather than stretching this contract.

This contract derives from completed research run **RIB-041** (IntentTree node
`node_01KVQYMNG71TW5YJV3KA3HPM6G`; high evidence). The research recommends a two-leg evaluation harness:
a committed cassette/VCR **deterministic** eval leg that gates PRs (Leg A / Phase 1), and a
**non-blocking nightly live** leg with a score-delta regression gate (Leg B / Phase 2).

Once approved, this contract may be executed phase-by-phase. Mandatory `task-completion-validator`
review of each phase's completion against acceptance criteria.

---

# Feature Contract: Two-Leg Eval Harness (RIB-041)

## 1. Goal

Build a two-leg evaluation harness for Research Foundry: a deterministic, cassette-backed eval leg that
runs offline and **gates every PR**, plus a non-blocking **nightly live leg** that re-runs the same
evals against real APIs and alerts on a documented score-delta regression versus a committed baseline.

---

## 2. User / Actor

- **Primary user**: RF maintainers / contributors opening PRs — they need an automatic, deterministic
  signal that a change has not regressed research-loop quality, without burning live API calls per PR.
- **Secondary users**: RF release/operator (reads the nightly regression alert to catch live-environment
  or upstream-model drift that the deterministic leg cannot see).

---

## 3. Job To Be Done

When **a contributor changes adapter, extraction, synthesis, or pipeline code**, the maintainer wants to
**run a deterministic, offline eval over a fixed set of golden runs as a required PR check (and, nightly,
re-run the same evals live and compare to a baseline)**, so they can **catch quality and behavior
regressions before merge, and catch live-environment / upstream-model drift overnight — without spending
live API budget or flaking on network nondeterminism in CI**.

---

## 4. Scope

This is a phased build. **Phase 1 is required and ships first; Phase 2 builds on it.**

### Phase 1 — Deterministic gating leg (do first)

- A **record/replay cassette layer** over RF's external adapter / network surface so evals run fully
  offline from committed cassettes (no live API calls). Pick one mechanism (`vcrpy` vs lightweight
  recorded-fixture) and justify — see §8 / §12.
- An **eval runner** that executes a **fixed set of golden runs** against the replayed cassettes and
  produces **deterministic scores** (stable across runs given the pinned clock and cassettes).
- A committed **golden-run fixture set** (inputs + cassettes + expected/scored outputs) covering the
  end-to-end research loop already exercised by `tests/test_end_to_end.py::test_full_research_loop`.
- A **new PR-gating GitHub Actions workflow** (e.g. `.github/workflows/test.yml`) that runs the
  deterministic pytest suite **and** the eval leg on every PR/push and **fails the check** on eval
  failure. (Today the only workflow is `.github/workflows/docs.yml`, which deploys mkdocs — there is no
  test-gating CI.)
- **Documented re-record procedure** for refreshing cassettes when the adapter surface legitimately
  changes.

### Phase 2 — Nightly live leg

- A **scheduled (nightly) GitHub Actions workflow** that runs the **same** evals/golden set against
  **live APIs** (real keys via secrets).
- A committed **baseline** of expected scores and a **score-delta regression gate**: the live run
  compares its scores to the baseline and **fails / alerts when the delta exceeds a documented
  threshold**. This leg is **non-blocking / alert-only** (does not gate PRs or block merges).
- Documentation of the threshold, the gated metric, and how to refresh the baseline.

### Out of Scope

- **Building `quality_score` itself** — that is **RIB-042** (`quality_score` is currently `"pending"` in
  telemetry). This harness must be designed to **consume RIB-042's `quality_score` as a gated metric once
  it exists** (see §6/§8), but does not implement it. Cross-reference the RIB-042 contract.
- **Per-PR live API calls** — the PR-gating leg is deterministic/offline only; live calls happen only in
  the nightly leg.
- Dashboards/visualization of eval trends, eval-result history storage beyond the committed baseline, and
  multi-environment (staging/prod) eval matrices.
- Changes to existing correctness/adversarial tests beyond wiring them into the new CI workflow.

---

## 5. UX / Behavior Requirements

- **Deterministic leg, local**: a contributor can run the eval leg locally (e.g. `pytest -m eval` or an
  `rf eval` entrypoint — implementer's choice, justified) with **no network access** and get the same
  pass/fail and the same scores every time.
- **PR gate**: opening a PR triggers the new workflow; the deterministic suite + eval leg run; a failing
  eval **blocks the PR check** (red). A passing run is green and reports the scores.
- **Cassette miss / drift**: if a golden run hits an un-recorded request (cassette miss), the eval
  **fails loudly with an actionable message** ("no cassette for <request>; re-record with <command>") —
  it must **not** silently fall through to a live call in CI.
- **Nightly leg**: the scheduled workflow runs live, computes scores, diffs against the committed
  baseline, and on a delta beyond threshold **emits an alert** (failed nightly job / annotation) **but
  does not block any merge**. Within threshold → green.
- **Re-record**: a documented single command re-records cassettes / refreshes the baseline; the diff is
  reviewable in the PR.

---

## 6. Data Requirements

- **Entities affected**: test/eval fixtures and CI config only. No production `research_foundry`
  runtime schema changes. May read RF telemetry/run outputs (e.g. `quality_score`) as eval inputs.
- **New fixtures / artifacts**:
  - Cassettes — committed recorded HTTP interactions (one set per golden run), location TBD by
    implementer (e.g. `tests/eval/cassettes/`).
  - Golden-run set — inputs + expected scored outputs (e.g. `tests/eval/golden/`).
  - Score baseline — committed expected scores for the nightly delta gate (e.g.
    `tests/eval/baseline.json` / `.yaml`).
- **State changes**: none at runtime. Eval scoring is read-only over golden inputs + replayed responses.
- **Storage implications**: cassettes/golden outputs are committed to the repo (text/JSON, redacted of
  secrets). No DB, no migrations. Keep fixtures small and reviewable.
- **Determinism inputs**: reuse the existing pinned clock fixture (`_fixed_clock` =
  `datetime(2026, 6, 13, ...)` in `tests/conftest.py`) and `tmp_foundry` so scores are stable. Any other
  nondeterminism source (UUIDs, ordering, model sampling) must be pinned or normalized before scoring.

---

## 7. API / Integration Requirements

**New or modified entrypoints:**
- Eval runner invocation — a pytest marker (`-m eval`) and/or an `rf eval` CLI subcommand. Implementer
  picks one and justifies; it must be runnable both locally and from CI.

**New CI workflows:**
- `.github/workflows/test.yml` (or similarly named) — **PR-gating**: runs deterministic suite + eval leg
  on `pull_request`/`push`. Required check.
- `.github/workflows/eval-nightly.yml` (or similar) — **scheduled** (`cron`): runs live evals, diffs vs
  baseline, alerts on delta. Non-blocking.

**External service calls:**
- **Phase 1**: none at run time — all external calls are served from cassettes. Recording (offline,
  manual, by a maintainer) is the only time live calls happen for Phase 1.
- **Phase 2**: live adapter/model APIs via repo **secrets**; nightly only. Must degrade gracefully
  (missing key → skip with a clear message, not a hard crash that masks regressions).

**Internal dependencies:**
- RF adapter/network surface (the layer cassettes wrap).
- RF eval scoring metric — initially a deterministic structural/correctness score over the research-loop
  output; **designed to consume RIB-042 `quality_score`** as the gated metric once available.

---

## 8. Architecture Constraints

**Must follow existing patterns in:**
- `tests/conftest.py` — reuse `tmp_foundry` and the pinned `_fixed_clock` fixture for determinism;
  follow the existing fixture style rather than introducing a parallel harness.
- `tests/test_end_to_end.py::test_full_research_loop` (the `@pytest.mark.integration` E2E test) — the
  golden runs should exercise the same research loop; model the eval after this flow.
- Existing correctness/adversarial tests — wire them into the new CI workflow alongside the eval leg.

**Must not change** (protected areas):
- `.github/workflows/docs.yml` (mkdocs deploy) — leave intact; add new workflow(s) beside it.
- The `research_foundry` runtime package's public behavior and the existing hand-written test fixtures —
  the eval harness is additive; do not refactor production code to fit the harness.
- The claim-ledger authority model — evals observe outputs, they do not relax governance gates.

**Key design decisions (stated defaults — implementer may override with justification in the
Completion Report):**

1. **Cassette library — default `vcrpy`.** Mature, pytest-integrated (`pytest-recording`), records/replays
   HTTP with a `none` record-mode for CI (fail on cassette miss). *Alternative considered:* a lightweight
   hand-rolled recorded-fixture shim (more control, but reinvents matching/redaction). Choose `vcrpy`
   unless RF's adapter surface does not go through an interceptable HTTP client, in which case fall back
   to the recorded-fixture approach and justify.
2. **Cassette coverage surface — default: external adapters / network egress only**, **not** all I/O.
   Filesystem and the pinned clock are already deterministic via existing fixtures; wrapping all I/O adds
   brittleness for no determinism gain. Cassettes cover the outbound model/provider/HTTP calls only.
3. **Cassette drift / re-record strategy — default:** CI runs in **`record_mode=none`** (cassette miss =
   hard failure, never a silent live call). Re-recording is an explicit, documented, maintainer-run
   command that re-records against live APIs and commits the (secret-redacted) diff for review. Cassettes
   are treated as reviewable fixtures, not generated artifacts.
4. **Score metric + score-delta gate — default:** Phase 1 scores a **deterministic structural/correctness
   metric** over the research-loop output (e.g. expected claim/source-card structure, verify-gate pass,
   stable normalized fields). The **nightly score-delta threshold defaults to ±5%** on the aggregate eval
   score (documented + configurable). When **RIB-042 `quality_score`** lands, it becomes the primary
   gated metric and the threshold is re-tuned against real distributions. The threshold value lives in
   committed config next to the baseline so it is reviewable.

**New dependencies:**
- Allowed? **Yes** — Phase 1 adds a test/dev dependency (`vcrpy` + `pytest-recording`, or equivalent)
  under the `[dev]` extra. No new runtime deps. Justify the final choice in the Completion Report.

---

## 9. Acceptance Criteria

**Phase 1 (gating leg):**

- [ ] The deterministic eval leg runs **fully offline** from committed cassettes (no network) and exits
      non-zero on a cassette miss with an actionable re-record message.
- [ ] A committed **golden-run fixture set** produces **stable, deterministic scores** across repeated
      local runs (same scores given pinned clock + cassettes).
- [ ] A **new PR-gating GitHub Actions workflow** exists and runs the deterministic pytest suite **plus**
      the eval leg on PRs/pushes; an eval failure fails the check. `docs.yml` is unchanged.
- [ ] The eval leg is runnable locally with a single documented command and reuses `tmp_foundry` /
      `_fixed_clock`.
- [ ] **Re-recording cassettes is documented** (command + when to use it + review expectation).

**Phase 2 (nightly live leg):**

- [ ] A **scheduled (nightly) workflow** exists that runs the same evals against **live APIs** via secrets
      and **does not gate PRs** (non-blocking / alert-only).
- [ ] The nightly run **compares scores to a committed baseline** and **fails/alerts when the delta
      exceeds the documented threshold** (default ±5%, configurable).
- [ ] The **score-delta threshold, the gated metric, and the baseline-refresh procedure are documented**,
      with an explicit note that the metric should consume RIB-042 `quality_score` once available.
- [ ] Missing live keys degrade gracefully (clear skip, not a masked pass/crash).

---

## 10. Validation Requirements

- [ ] **Lint** passes (`flake8 src --select=E9,F63,F7,F82`).
- [ ] **Tests** added: eval runner + golden set + cassette replay have tests; new fixtures are covered.
- [ ] **Deterministic eval leg passes offline** (no network) twice with identical scores.
- [ ] **Suite passes** under the venv interpreter (`./.venv/bin/python -m pytest`, or `uv run pytest`) —
      do not use the pyenv shim (known "No module named research_foundry" trap).
- [ ] **Workflow syntax valid**: new `.github/workflows/*.yml` parse and reference real entrypoints.
- [ ] **Secret hygiene**: cassettes and baseline contain **no live secrets/keys** (redacted on record).
- [ ] **Docs updated**: re-record + baseline-refresh procedure documented; CHANGELOG entry
      (`changelog_required: true`).
- [ ] **No unrelated changes** — `docs.yml` and `research_foundry` runtime behavior untouched.

---

## 11. Risk Areas

- **Determinism leakage**: model sampling, UUIDs, dict/JSON ordering, or timestamps not covered by the
  pinned clock can make scores flap and turn the PR gate into a flaky blocker. Mitigation: pin/normalize
  all nondeterminism before scoring; assert score stability across two runs as an acceptance gate.
- **Cassette coverage surface mismatch**: if RF's adapters don't route through an HTTP client `vcrpy` can
  intercept, replay won't catch the calls. Mitigation: verify the interception point during Phase 1
  spike; fall back to recorded-fixture shim if needed (decision in Completion Report).
- **Silent live fallthrough in CI**: a misconfigured record mode could let CI make real calls. Mitigation:
  enforce `record_mode=none` in CI; cassette miss = hard fail.
- **Metric coupling to RIB-042**: `quality_score` is still `"pending"`. Mitigation: Phase 1 ships a
  deterministic structural metric now; design the score interface so `quality_score` slots in later
  without reworking the gate.
- **Phase 2 scope creep** (baseline storage/versioning, provider orchestration, alert routing): could push
  past 8 points. Mitigation: if it balloons, **split Phase 2 into its own Tier 1 contract** and ship
  Phase 1 standalone (see header note).
- **Secret exposure in committed cassettes**: recorded responses/headers may contain keys. Mitigation:
  redaction filters on record; secret-scan the committed fixtures.

---

## 12. Implementation Notes

**Suggested approach (agent may improve):**
- **Phase 1, step 1**: confirm the adapter/network interception point and validate `vcrpy` can wrap it
  (short spike). Decide cassette mechanism; record the decision.
- **Phase 1, step 2**: build the eval runner over `test_full_research_loop`'s flow; define the
  deterministic structural score; reuse `tmp_foundry` + `_fixed_clock`.
- **Phase 1, step 3**: record the golden cassettes (offline, redacted), commit golden set, assert stable
  scores across two runs.
- **Phase 1, step 4**: add `.github/workflows/test.yml` running deterministic suite + eval leg as a
  required check; document the re-record command.
- **Phase 2, step 5**: add `.github/workflows/eval-nightly.yml` (`schedule: cron`) running the same evals
  live via secrets; commit the baseline; implement the ±5% (configurable) delta gate as non-blocking;
  document threshold + baseline refresh.

**Similar existing code**:
- Reference: `tests/conftest.py` (`tmp_foundry`, `_fixed_clock`) — determinism fixtures to reuse.
- Reference: `tests/test_end_to_end.py::test_full_research_loop` — the loop the golden runs should mirror.
- Reference: `.github/workflows/docs.yml` — the only existing workflow; mirror its structure for the new
  workflows, do not modify it.

**Known gotchas**:
- Run pytest under the venv interpreter, never the pyenv shim ("No module named research_foundry").
- The full pytest suite is known to pollute a few tracked real-run files via a non-isolated test — scope
  eval/CI runs and avoid depending on that test's side effects.
- CI must run with `record_mode=none`; a cassette miss must fail, never make a live call.

---

## 13. Completion Report Required

The executing agent must produce a Completion Report (per phase) including:

- **Files changed**: all modified/new files with brief reason (workflows, eval runner, fixtures, docs).
- **Tests run**: eval leg + suite results; proof of score stability across two offline runs.
- **Validation results**: table of all validation commands and pass/fail.
- **Key decisions made**: final cassette mechanism, coverage surface, threshold value, score metric —
  with justification for any deviation from §8 defaults.
- **Deviations from contract**: any material changes and why (especially if Phase 2 was split out).
- **Risks / Limitations**: remaining flakiness, coverage gaps, RIB-042 dependency status.
- **Follow-up recommendations**: e.g. wiring RIB-042 `quality_score` as the gated metric.

See `.claude/skills/dev-execution/validation/completion-criteria.md` for the full Completion Report
template.

---

## Metadata & References

**Tier**: 2 (8 points) — authored as a phased Feature Contract (well-understood infra). Split Phase 2 to
its own contract if it grows.

**Execution Mode**: Phased — Phase 1 first (independently shippable), then Phase 2. Mandatory
`task-completion-validator` review per phase.

**Reviewer**: `task-completion-validator` (mandatory)

**Related Documents**:
- Harvest report: `docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md`
- Research provenance: IntentTree node `node_01KVQYMNG71TW5YJV3KA3HPM6G` (RIB-041, high evidence)
- **RIB-042** `quality_score` contract — the metric this harness should consume once it exists
  (cross-referenced throughout; out of scope here).

---

## Notes for Agents

This contract is your specification. Implement to satisfy the acceptance criteria and pass validation.

- **Ship Phase 1 first** — it is the required PR gate and is independently valuable.
- **Scope ambiguity**: make a conservative assumption aligned with the §8 defaults and note it in the
  Completion Report.
- **If Phase 2 balloons**: stop, ship Phase 1, and recommend splitting Phase 2 into its own contract.
- Stay within scope. Do not build `quality_score` (RIB-042). Do not add per-PR live calls.
