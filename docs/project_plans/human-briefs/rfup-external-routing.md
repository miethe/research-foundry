---
schema_name: ccdash_document
schema_version: 2

doc_type: human_brief
doc_subtype: ""
root_kind: project_plans

id: ""
title: "RFUP External-Routing Gap Closure — Human Brief"
status: draft
category: human-briefs

feature_slug: rfup-external-routing
feature_family: rfup-external-routing
feature_version: v1

prd_ref: docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md
intent_ref: null
epic_ref: null

related_documents: []

owner: null
contributors: []

audience: [humans]

priority: high
confidence: 0.8

created: '2026-07-22'
updated: '2026-07-22'
target_release: ""

tags: [human-brief, rfup, evidence-foundry]
---

# RFUP External-Routing Gap Closure — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-22

---

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/enhancements/rfup-external-routing-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/enhancements/rfup-external-routing-v1.md`
- **Decisions Block**: `.claude/worknotes/rfup-external-routing/decisions-block.md`
- **Scope Brief**: `.claude/worknotes/rfup-external-routing/scope-brief.md`
- **State Audit**: `.claude/worknotes/rfup-external-routing/state-audit.md`
- **Design Spec**: `docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md` (P5/P6 update target)
- **SPIKEs**: None — Phase 5 (native-adapter eval) doubles as this plan's Tier-3 SPIKE-equivalent, eval-only per Hard Constraint 2.
- **Related Briefs**: None

---

## 2. Estimation Sanity Check

**Bottom-up total**: ~27 pts (24 pts H4 floor + ~3 pts H6 hidden plumbing, including SEAM-001)
**Top-down anchor**: commit `001a834` ("RFUP-1..5,7") — same surface (`verification.py`, `source_cards.py`, `.claude/workflows/*.js`, `config/claim_policy.yaml`) — ran as a 6-phase Tier-3 plan at ~29 pts actual.
**Reconciliation**: This delta plan's ~24-27 pts is 7-17% below the anchor. That gap is justified, not a compression error: 3 of 6 phases here (P1, P2, P3) extend already-designed/settled mechanisms (DF-E1-03, ADR-0008's own recommendation, existing RFUP-1/3 code) rather than building net-new machine-contract plumbing from zero the way the anchor plan did. Within the ±30% band the estimation-heuristics reference treats as needing no further justification. Bottom-up and top-down agree closely enough (27 vs. ~24-26 decisions-block estimate) that no reconciliation dispute exists — trust bottom-up as authoritative.

H1-H7 heuristic application (migrated from the plan's own Estimation Sanity Check, which ran the heuristics fresh with real file line-counts — treat the plan as the more current source over the decisions-block's earlier pass):

- **H1 (noun-counting)**: Does not apply. 0 new CRUD-with-RBAC domain nouns — no new DB tables. `pediatric_cds` is a JSON-Schema-validated block on an existing evidence-card structure, not a new first-class entity with its own repository/router.
- **H2 (dual-implementation multiplier)**: N/A — `rf` has no local/enterprise dual-implementation split; single Python service layer throughout.
- **H3 (algorithmic service flag)**: Trips on P4. Quote-fidelity diff/normalize/transform logic is exactly the class of work this heuristic exists to catch. Budgeted at 5 pts (above the 3-pt floor) with the required ≥5 enumerable fixture scenarios: superscript-class corruption (PMC ×10⁹/L → ×10/L, must flag), NFKC-safe normalization (must not flag), curly-quote-safe normalization (must not flag), `locator_only` card (warn, not fail/skip), and a clean/no-corruption pass case (must not flag).
- **H4 (bundle-vs-sum floor)**: 6 capability areas triggers the per-area floor. Per-area sum: P1=2, P2=5, P3=4, P4=5, P5=5, P6=3 → **Σ = 24 pts**, the floor for the plan total.
- **H5 (anchor reference)**: See top-down anchor above — commit `001a834`, delta within ±30% of a comparable completed feature on the identical surface.
- **H6 (hidden plumbing budget)**: ~3 pts (~12.5% of the 24-pt subtotal) covering: schema DTO/version stamp consistent with RFUP-4's machine-contract (P2), CLI flag wiring for the eligibility default (P3), test fixtures across P2/P3/P4, the CHANGELOG entry (P6), and SEAM-001 itself (1 of the 3 pts).
- **H7 (large-file override, plan-added)**: Checked and does not trigger. `verification.py` is 1,398 lines (verified at planning time via `wc -l`) — under the 2K-line Tier-2-minimum threshold. `source_cards.py` (451), `rf-run-execute.js` (309), `rf-pediatric-cds-run-execute.js` (388), and `litellm_router.py` (151) are all well under threshold. No ≥2× multiplier applied to any task.

**Locked estimate**: **~24-27 pts** (range retained deliberately — H6 plumbing is a budget, not yet task-decomposed to the 0.5-pt level; no compression below the H4 floor of 24).

---

## 3. Wave & Orchestration Notes

**Critical path**: P2 → {P3, P4} → SEAM-001 → P6. P2 is the critical-path root — both P3 and P4 `depend_on: [P2]` in the wave-plan frontmatter. P1 and P5 sit off the critical path entirely (no dependency in either direction on P2/P3/P4), but both are hard dependencies of P6 (`depends_on: [P1, P3, P4, P5]`) since P6 finalizes docs/deferrals for all five preceding phases — so slipping either one still slips the final wave.

**Parallel opportunities**:
- **Wave 1**: P1 (Path-B test hardening) ∥ P5 (native-adapter SPIKE/eval) — fully independent domains, zero shared files (`P1.files_affected` is two new `__tests__/*.test.js`; `P5.files_affected` is one new worknote markdown).
- **Wave 3**: P3 (eligibility gate) ∥ P4 (quote-fidelity gate) — both extend `verification.py` but touch disjoint functions (P3 extends the existing `exact_passage_present` check at lines 712-753; P4 adds a wholly new check function, kept in a separate `quote_fidelity.py` module to bound the H3-flagged algorithmic surface). The parallelism is NOT achieved by splitting the wave — it's mitigated by declaring `integration_owner: python-backend-engineer` on the pair plus the seam task **SEAM-001**, which runs after both land to prove the disjointness holds at runtime, not just at code-review time.

**Merge order**: Sequential by wave — Wave 1 (P1, P5) → Wave 2 (P2) → Wave 3 (P3, P4, then SEAM-001) → Wave 4 (P6). Do not advance to the P6 wave until SEAM-001's evidence is recorded and green (AC-SEAM-4 makes this an explicit prerequisite the consolidated `karen` milestone consumes).

**Cross-feature coupling**: None. This is a self-contained delta on `rf`'s own evidence-pipeline services layer (`verification.py`, `source_cards.py`, plus one new `quote_fidelity.py` module and one new JSON Schema). The only cross-repo touchpoint is a read-only reference to `pediatric-anemia-site`'s ADR-0008 — this plan never writes to that repo (seam boundary hard invariant).

---

## 4. Open Questions Ledger

| ID | Source | Question | Status | Resolved By |
|----|--------|----------|--------|-------------|
| PRD OQ-1 | PRD §12 | Should the P3 auto-strict eligibility trigger on `assertion_kind=threshold` alone, or require threshold AND a clinical-sensitivity signal? (Overlaps DecisionsBlock OQ-4 — same underlying question, different framing.) | resolved | Plan `decisions:` frontmatter entry #3 — threshold AND (`pediatric_cds` block present OR sensitivity tag); Phase 3-4 file AC-P3-1, AC-P3-3. |
| PRD OQ-2 | PRD §12 | For `extraction_status: locator_only` source cards, should the P4 fidelity check skip, warn, or fail? | resolved | Plan `decisions:` frontmatter entry #5 — warn, not skip/fail; Phase 3-4 file AC-P4-7, AC-P4-8 (task P4-003). |
| PRD OQ-3 | PRD §12 | What is the canonical normalization allowlist for the P4 fidelity diff — which transforms are safe vs. material corruption? (Overlaps DecisionsBlock OQ-3 — identical question.) | resolved | Plan `decisions:` frontmatter entry #4 — two-stage allowlist-then-diff policy (Stage 1 NFKC/whitespace/quote-style; Stage 2 any residual = material); Phase 3-4 file AC-P4-5, AC-P4-6 (task P4-002). |
| PRD OQ-4 | PRD §12 | Given P5's no-install/no-credentials constraint, what evaluation method yields a citable, non-hand-wavy security verdict? (Overlaps DecisionsBlock OQ-5 — same question at slightly narrower framing.) | resolved | Plan `decisions:` frontmatter entry #6 — static PyPI/GitHub metadata review + `pip download --no-deps` dependency-tree inspection; Phase 5 file tasks P5-001/P5-002, AC-P5-1 through AC-P5-9. |
| PRD OQ-5 | PRD §12 | Does P5 output an rf-side-only verdict artifact, or is there an out-of-band path to transition ADR-0008's status in `pediatric-anemia-site`? | resolved-as-scope-decision (rf-side artifact only); underlying cross-repo ADR-0008 status transition itself is **deferred** — see §5 below | Plan `decisions:` frontmatter entry #7; deferred-items triage row DF-RFUP-EXT-02; Phase 6 file task P6-003 (DOC-006b), AC-P6-8 through AC-P6-11. |
| DecisionsBlock OQ-1 | decisions-block §7 | What JS test harness exists for `.claude/workflows/*.js` — `node:test`, or an ad-hoc assertion script? | resolved | Plan `decisions:` frontmatter entry #1 — Node's built-in `node:test` + `node --test` (confirmed available on Node 20.19.3, no `--experimental-*` flag needed); Phase 1 file "Decisions in force" section, tasks P1-001/P1-002. |
| DecisionsBlock OQ-2 | decisions-block §7 | Hard-gate enforcement point for P2 — ingest-time (`source_cards.py`), verify-time (`verification.py`), or both? | resolved | Plan `decisions:` frontmatter entry #2 — primarily verify-time, consistent with the existing `resolve_exact_passage_mode`/`exact_passage_present` idiom; ingest-time is a Should, not a Must; Phase 2 file task P2-002, AC-P2-5. |
| DecisionsBlock OQ-3 | decisions-block §7 | P4 fidelity policy — normalize corrupt quotes in place vs. reject/flag only? Which corruption classes are in-scope for v1? | resolved — same resolution as PRD OQ-3 (cross-reference) | Plan `decisions:` frontmatter entry #4; Phase 3-4 file AC-P4-5, AC-P4-6. |
| DecisionsBlock OQ-4 | decisions-block §7 | P3 default policy — flip default to strict for threshold claims globally, or gate on audience/sensitivity (clinical only)? | resolved — same resolution as PRD OQ-1 (cross-reference) | Plan `decisions:` frontmatter entry #3; Phase 3-4 file AC-P3-1. |
| DecisionsBlock OQ-5 | decisions-block §7 | Does the P5 eval need any offline/sandboxed `litellm` probe, or is it purely doc + code + security-posture review? | resolved — same resolution as PRD OQ-4 (cross-reference) | Plan `decisions:` frontmatter entry #6; Phase 5 file tasks P5-001/P5-002. |

**Row count: 10** (5 PRD + 5 DecisionsBlock, as expected).

---

## 5. Deferred Items Rationale

- **DF-RFUP-EXT-01 (native adapters, research-needed)**: The 5 native adapters NOT evaluated by P5 (`gpt_researcher`, `notebooklm`, `openai_agents`, `paperqa2`, `opencode`) remain scaffold-only. Deferred because P5's scope was deliberately narrowed to `litellm_router` alone — the one adapter with an existing partial implementation (`2d198a8`'s ICA-provider mapping fix) and a live ADR requiring resolution. Evaluating all 6 in one pass would have blown this plan's eval-only budget and diluted the one verdict that actually needed to land. Promote when the RFUP-6 design-spec's own existing defer-until gate fires: a measured Path-B value gap (a documented comparison run showing Path-B insufficiency) OR a governance/DI-1-cleared requirement. Target spec: `docs/project_plans/design-specs/rfup-6-native-discovery-adapters.md`, updated in place by P6 (not replaced) — the 5 adapters' `maturity: idea` framing is explicitly reaffirmed, not silently left stale.

- **DF-RFUP-EXT-02 (ADR-0008 status transition, dependency-blocked)**: ADR-0008 lives in `pediatric-anemia-site` and is currently `proposed`, not `accepted`. This plan's seam boundary forbids writing to that repo, so the actual status flip cannot happen from inside this plan no matter how confident P5's verdict is. Deferred because the fix here is architectural (a hard cross-repo write restriction), not a scoping choice that could be resolved by more effort in this plan. Promote when the `pediatric-anemia-site` maintainer reviews this plan's P5 verdict artifact and accepts/rejects ADR-0008 on that basis — a downstream, out-of-band action this plan cannot trigger itself. Target spec: `docs/project_plans/design-specs/rfup-external-routing-adr-0008-verdict.md`, newly authored by P6 as the durable rf-side artifact that makes the downstream decision actionable without re-deriving the evaluation.

---

## 6. Risk Narrative

- **R1 — Clinical-gate correctness (P2/P3/P4)**: This is the risk that makes the whole feature Tier 3 despite its modest point count. A false-pass on any of the three new gates admits corrupt or structurally-incomplete evidence into a pediatric CDS pipeline — a clinical-safety-adjacent failure mode, not just a code-quality one. A false-block, symmetrically, halts valid research runs that never asked for the stricter behavior. Because P2, P3, and P4 all converge on the same file (`verification.py`) and the same failure class, reviewing them individually as they land would miss composition bugs — a fix in P4 masking a P3 finding, or vice versa. This is exactly why the plan deliberately overrides its own decisions-block's per-phase reviewer-gate column (which had listed a separate `karen` pass at P2 and again at P4) and consolidates into **one `karen` milestone after all of Wave 3 (P3+P4+SEAM-001) is complete**. Watch for orchestrators reverting to the more "natural" per-phase karen cadence out of habit — the plan's Reviewer Gates section is explicit that this is a deliberate override, not an oversight.

- **R4 — Quote-fidelity strategy ambiguity (P4)**: Before this plan, there was no answer to "which corruption classes are we actually trying to catch, and how do we avoid flagging benign Unicode/whitespace noise as corruption?" This risk is now resolved at the design level via the two-stage policy (Stage 1 normalization allowlist — NFKC, whitespace, quote-style — applied before diffing; Stage 2 treats any residual difference as material and never auto-corrects). The risk that remains is empirical, not design-level: whether the Stage 1 allowlist is actually complete enough to avoid false positives on real-world extraction noise beyond the five enumerated fixture scenarios. Watch P4's regression results against the 7 verified bundles closely — a spike in false positives there is the canary that the allowlist under-covers a real normalization class the fixtures didn't anticipate.

- **R2 — Shared `verification.py` churn (P2/P3/P4)**: Managed structurally (P2 sequenced before Wave 3; `integration_owner` declared; SEAM-001 seam task) rather than left to reviewer vigilance alone — this is the mechanical complement to R1's review-cadence mitigation.

- **R3 — Item-4 scope creep into install / Mode-D (P5)**: Low likelihood given Hard Constraint 2 is stated three times across the PRD, decisions-block, and plan, but the consequence of a slip is severe (an actual `litellm` install with live credentials would cross into Mode-D territory this plan was explicitly scoped to avoid). Worth a deliberate spot-check at P5 sign-off, not just trust in the constraint's repetition.

- **R5 — JS test harness absence (P1)** and **R6 — schema-version drift vs. RFUP-4 (P2)**: Both low-severity and already resolved at the design level (`node:test`; reuse of the existing schema-version stamping pattern). Included here only for completeness — no orchestration-level watch item beyond confirming the resolutions actually landed as specified.

---

## 7. What to Watch For

- **SEAM-001's actual regression result, not just the P3/P4 code review.** The disjoint-function assumption (P3 extends `exact_passage_present` at lines 712-753; P4 adds a new function entirely) is a design-time claim. SEAM-001 exists specifically to prove it holds at runtime — that no gate masks another's failure and no finding is double-counted (AC-SEAM-2, AC-SEAM-3). Don't let the Wave 3 pair get marked complete on code-review confidence alone; wait for SEAM-001's evidence.
- **The 7 verified pediatric-CDS bundles' actual availability on disk.** P2, P4, and SEAM-001 all depend on this fixture set (committed `aaa9d92`, per project memory) for their 0-false-positive gates. Confirm the bundles are actually present and loadable before trusting any "0 false positives" claim from an executing agent.
- **P5's static-eval-only constraint holding for real, not just in the artifact's stated confirmation.** The temptation to reach for "just a quick sandboxed litellm probe to be sure" is exactly the scope-creep risk R3 flags. AC-P5-6/AC-P5-9/AC-P5-15 are explicit negative-confirmation criteria (zero install, zero live calls beyond public PyPI/GitHub metadata lookups, zero credentials) — verify these are stated affirmatively in the eval artifact, not merely absent by omission.
- **Do not let P6 start before SEAM-001 is green.** AC-SEAM-4 makes SEAM-001's result the explicit prerequisite for the consolidated `karen` milestone, and P6's wave (`depends_on: [P1, P3, P4, P5]`) technically doesn't gate on SEAM-001 directly in the wave-plan graph — this is a place where the frontmatter dependency graph and the plan's own stated intent diverge slightly. Enforce the intent (SEAM-001 → karen → P6), not just the literal `depends_on` list.

---

## 8. Expected Success Behaviors

- [ ] Running `rf verify` against a source card with an incomplete `pediatric_cds` block (missing a required top-level section) fails with a distinguishable, human-readable reason code — not a generic error.
- [ ] Running `rf verify` against any of the 7 known-good pediatric-CDS bundles still passes cleanly after all three new gates (P2/P3/P4) are active — no regression on previously-verified content.
- [ ] A threshold-kind claim tied to a pediatric/clinical source card, submitted without an exact-passage locator, fails `rf verify` by default — without needing to pass `--exact-passage strict` on the command line.
- [ ] A research-only (non-clinical) run using default settings still behaves exactly as before — no new failures introduced by the eligibility default.
- [ ] Feeding the PMC superscript-stripping example (`×10⁹/L` corrupted to `×10/L`) through the fidelity check produces a flagged finding; feeding a quote with only cosmetic Unicode/whitespace/quote-style differences does not.
- [ ] `node --test` on the two new Path-B test suites exits 0, and neither `rf-run-execute.js` nor `rf-pediatric-cds-run-execute.js` shows any diff in its runtime logic (tests-only change, verifiable via `git diff`).
- [ ] The ADR-0008 evaluation artifact states a clear accept/reject/conditional verdict with cited findings — readable by a non-engineer reviewer, not just inferable from raw metadata.
- [ ] No live network calls or credential use occurred during the P5 evaluation — confirmed by reading the eval artifact's explicit statement, not merely inferred from its absence.
- [ ] CHANGELOG `[Unreleased]` contains an entry describing the new default-strict passage behavior and the two new verify-time gates in plain operator-facing language.
- [ ] The `rfup-6-native-discovery-adapters.md` design spec, read fresh, clearly shows which adapter was evaluated (`litellm_router`) and which five remain deferred and why — no ambiguity about maturity state for the unevaluated adapters.

---

## 9. Running Log

- [2026-07-22] Brief created alongside implementation plan; both authored via `/plan:planning` orchestration.
