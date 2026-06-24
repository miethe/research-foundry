---
schema_version: 2
doc_type: exploration_charter
title: "Citation Precision/Recall Metrics (FActScore/ALCE) — Exploration Charter"
status: draft
created: 2026-06-23
feature_slug: citation-precision-recall-metrics
timebox_days: 3
hypothesis: "We believe FActScore/ALCE-style atomic-fact citation precision/recall metrics can be computed deterministically and cheaply over RF's existing claim ledger plus source cards, and are worth adding as RF quality signals because RF currently emits only coarse claim counts with a hard-coded 'pending' quality_score and has no precision/recall signal at all."
deal_killer: "If precision/recall cannot be computed without a human-labeled ground-truth reference set that RF cannot cheaply produce, OR the resulting metric does not discriminate good vs bad runs across RF's real completed-run corpus, abandon this in favor of the simpler RIB-042 ratio-based quality_score (support_rate / supported-over-total)."
investigation_legs:
  - id: methodology
    question: "How do FActScore (atomic-fact decomposition + per-fact support) and ALCE (citation precision/recall) adapt to RF's claim ledger, and what serves as the 'reference' for recall — can it be derived from source cards / the abstain set rather than human labels?"
    assigned_to: spike-writer
  - id: compute-cost
    question: "Can the metric be computed deterministically over the ledger, or does it require LLM scoring; where do results live (new metric schema vs ledger fields vs telemetry event); and does it fit the cheap-extract budget?"
    assigned_to: ai-engineer
  - id: discrimination
    question: "Does the metric actually separate good vs bad runs on RF's real completed-run corpus (the deal-killer test)?"
    assigned_to: ai-engineer
verdict_criteria:
  go:
    - "All investigation legs report confidence >= 0.7"
    - "Deal-killer condition not triggered (recall computable without human labels AND metric discriminates good vs bad runs)"
    - "A concrete, costed computation path exists (deterministic-first; LLM scoring optional and budget-bounded)"
  no_go:
    - "Deal-killer condition triggered"
    - "methodology leg reports recall is uncomputable without a human-labeled reference set RF cannot cheaply produce, confidence >= 0.8"
    - "discrimination leg shows metric does not separate good vs bad runs on the real corpus, confidence >= 0.8"
  conditional:
    - "Precision is computable and discriminating, but recall requires a named, cheap-to-produce proxy reference (e.g. abstain-set or source-card-derived) whose validity is resolvable by a specific named follow-up investigation"
verdict: null
verdict_rationale: null
output_artifacts: []
---

# Citation Precision/Recall Metrics (FActScore/ALCE) — Exploration Charter

<!-- Copy to docs/project_plans/exploration/[feature-slug]/[feature-slug]-charter.md -->
<!-- Use /plan:explore to scaffold most fields from an idea description. -->

## Hypothesis Context

This exploration derives from completed research run **RIB-025** (IntentTree node `node_01KVQYMHBN8VP5XRQC8XH403JX`; MEDIUM evidence), captured in the completed-runs outcomes harvest. RIB-025 framed two RF-MVP gaps: (a) explicit plan/state persistence, and (b) FActScore/ALCE-style atomic-fact citation precision/recall metrics.

**Triage note — gap (a) is already largely satisfied and is OUT OF SCOPE here.** Current RF persists plan/state explicitly: `src/research_foundry/services/planning.py::plan_run()` deterministically writes `run.yaml`, `research_brief.md`, `swarm_plan.yaml`, and `routing_decision.yaml`, and per-stage state is appended to `telemetry/run_trace.jsonl` (`planning.py` ~line 595, `append_jsonl(record, run.run_trace)`). This SPIKE therefore scopes **only the net-new gap (b)**: citation precision/recall metrics.

**Why this is a SPIKE, not a contract.** The methodology is genuinely unresolved: FActScore and ALCE both presume a *reference* against which recall is measured (a gold answer set or a labeled atomic-fact list). RF has no human-labeled ground truth and cannot cheaply produce one. Whether a usable reference can be *derived* — from source cards, the supported-claim set, or the abstain set — is the open question. Until it is answered, no implementation contract can be authored.

**Grounding facts (verified against the current tree).** NO citation precision/recall or atomic-fact metrics are computed today. `src/research_foundry/services/telemetry.py::emit_ccdash_event()` (~line 126) emits coarse claim counts only — `claims_total`, `claims_supported`, `claims_unsupported`/`unsupported_claims` — and writes `quality_score: "pending"` as a hard-coded literal (~line 202). A `support_rate` (supported / total) is trivially derivable from those counts but is not currently exposed.

**Measurement-dependency framing.** This metric is the **measurement dependency for RIB-001** (claim segmentation/alignment): atomic-fact decomposition is the input both RIB-001 and FActScore-style scoring consume, so the segmentation approach chosen here constrains RIB-001 and vice versa. The metric also **feeds RIB-041** (eval harness — it would become a scored signal the harness reports) and **RIB-042** (quality_score — precision/recall would either replace or supplement the `"pending"` literal / the ratio-based `support_rate`). Those three RIBs are cross-referenced throughout and should be consulted before any implementation lands.

---

## Investigation Legs

<!-- One subsection per leg. Each leg runs as a SPIKE via /plan:spike --leg-of=[charter-path]. -->

### Leg: methodology — Adapt FActScore/ALCE to the RF ledger

**Question**: How do FActScore (atomic-fact decomposition + per-fact support) and ALCE (citation precision/recall) adapt to RF's claim ledger, and what serves as the "reference" for recall — can it be derived from source cards / the abstain set rather than human labels?
**Assigned to**: `spike-writer`
**Expected output**: `docs/project_plans/exploration/citation-precision-recall-metrics/spikes/methodology-spike.md`

Unknowns / sources this leg must address:
- The **recall reference problem** is the crux. FActScore measures the fraction of decomposed atomic facts that are supported by a knowledge source; ALCE measures, per generated statement, citation precision (cited sources actually support the statement) and citation recall (the statement's support is fully cited). Both assume a reference. Identify, for each metric, exactly what the reference is and whether RF can supply a cheap proxy: (i) source-card-derived support set, (ii) the supported-claim subset of the ledger, (iii) the **abstain set** (claims the run declined to assert) as a recall-style signal, or (iv) something else. State whether each proxy yields *true* recall or only a recall-shaped proxy, and label it honestly.
- Map RF ledger primitives onto the metric inputs: claims, claim→source-card citations, supported/unsupported/abstain status. Confirm against the real claim/source-card schema (the synthesizer + claim-audit pipeline; `rf_claim_auditor` / `rf_synthesizer` agent contracts and the source-card format) — do NOT invent fields.
- Decide whether **atomic-fact decomposition** is needed at all, or whether RF claims are already atomic enough that precision/recall can be computed at the claim grain. This decision is shared with **RIB-001** — record the coupling explicitly.
- Output: a precise definition of precision and (proxy-)recall in RF terms, the chosen reference, and an honest statement of what the metric does and does not measure.

### Leg: compute-cost — Deterministic vs LLM-scored; where results live; budget fit

**Question**: Can the metric be computed deterministically over the ledger, or does it require LLM scoring; where do results live (new metric schema vs ledger fields vs telemetry event); and does it fit the cheap-extract budget?
**Assigned to**: `ai-engineer`
**Expected output**: `docs/project_plans/exploration/citation-precision-recall-metrics/spikes/compute-cost-spike.md`

Unknowns / sources this leg must address:
- **Deterministic-first.** Determine how much of precision/recall is computable purely from existing ledger structure (claim↔source-card linkage, support flags) with zero model calls — this is the cheapest and most defensible path and aligns with RF's deterministic-first governance posture. Quantify the residual that genuinely needs an LLM judge (e.g. entailment between a claim and the cited source card text).
- If LLM scoring is required for the residual, scope it to the **cheap-extract** tier (the cheap-model extraction budget RF already uses), not the expensive synthesis tier. Estimate per-run cost and confirm it fits the existing budget envelope.
- **Where results live.** Compare three placements: (i) extend the existing CCDash telemetry event in `src/research_foundry/services/telemetry.py::emit_ccdash_event()` (alongside `claims_total`/`claims_supported`, replacing the `quality_score: "pending"` literal), (ii) new fields on the claim ledger, (iii) a dedicated metric schema/artifact. Recommend one; note the RIB-041 (eval harness) and RIB-042 (quality_score) consumers each placement implies. Note that `support_rate` is already derivable here and could be the trivial first signal regardless of outcome.

### Leg: discrimination — Does the metric separate good vs bad runs? (deal-killer test)

**Question**: Does the metric actually separate good vs bad runs on RF's real completed-run corpus?
**Assigned to**: `ai-engineer`
**Expected output**: `docs/project_plans/exploration/citation-precision-recall-metrics/spikes/discrimination-spike.md`

Unknowns / sources this leg must address:
- This leg **tests the deal-killer directly.** Compute the candidate precision/(proxy-)recall metric (per the methodology + compute-cost legs) over the corpus of RF's real completed runs and check whether it separates runs already understood to be good from those understood to be weak. The completed-runs outcomes harvest (`docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md`) and the existing per-run telemetry are the labels-of-convenience source; use known-strong vs known-thin runs as the contrast set.
- A metric that assigns near-identical scores across visibly different-quality runs fails the deal-killer → recommend `no-go` (fall back to RIB-042 ratio-based `support_rate`).
- Distinguish whether *precision* discriminates, *recall* discriminates, or both. A precision-only positive (recall proxy non-discriminating) should drive a `conditional` verdict naming the recall-reference follow-up, not an outright `go`.
- Do NOT over-fit: report effect direction and rough separation on the real corpus, not a polished statistical study — this is a feasibility gate, not the eval harness (that is RIB-041).

---

## Verdict Criteria Narrative

**Go** if: all three legs report confidence ≥ 0.7; the deal-killer is not triggered (a usable reference for recall exists without human labels, AND the metric separates good vs bad runs on the real corpus); and a concrete costed computation path exists that is deterministic-first with any LLM scoring confined to the cheap-extract budget. In this case proceed to author an implementation contract, coordinated with RIB-001/RIB-041/RIB-042.

**No-go** if: the deal-killer fires — recall is uncomputable without a human-labeled reference set RF cannot cheaply produce (methodology leg, confidence ≥ 0.8), OR the metric does not discriminate good vs bad runs on the real corpus (discrimination leg, confidence ≥ 0.8). Fall back to the simpler RIB-042 ratio-based `quality_score` (expose the already-derivable `support_rate`) and close this exploration.

**Conditional** if: citation *precision* is computable, cheap, and discriminating, but *recall* depends on a named proxy reference (abstain-set-derived or source-card-derived) whose validity is not yet established. Ship precision now; name a specific follow-up investigation to validate the recall proxy before adding it.

---

## Out of Scope

- **Gap (a) plan/state persistence** — already largely satisfied by `plan_run()` (run.yaml/research_brief.md/swarm_plan.yaml/routing_decision.yaml) + `telemetry/run_trace.jsonl`. Not investigated here.
- Building the RIB-041 eval harness itself — this charter only establishes whether the precision/recall *signal* is feasible and discriminating; harness construction is RIB-041.
- Final `quality_score` formula design and rollout — that is RIB-042; this charter only determines what signal RIB-042 could consume.
- Claim segmentation/alignment implementation — that is RIB-001; this charter records the coupling but does not implement decomposition.
- Any change to the source-card or claim-ledger schema — proposals may be noted, but schema edits are out of scope for a SPIKE.

---

## Citations / Prior Art

- `docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md` — harvest report; source of RIB-025 (IntentTree node `node_01KVQYMHBN8VP5XRQC8XH403JX`, MEDIUM evidence) and the corpus for the discrimination leg.
- `src/research_foundry/services/telemetry.py::emit_ccdash_event()` — current coarse claim-count emission; `quality_score: "pending"` hard-coded literal; `support_rate` derivable but unexposed.
- `src/research_foundry/services/planning.py::plan_run()` — establishes that gap (a) plan/state persistence is already satisfied (run.yaml/research_brief.md/swarm_plan.yaml/routing_decision.yaml + `telemetry/run_trace.jsonl`).
- Related RIBs (cross-referenced, not yet linked artifacts): **RIB-001** (claim segmentation/alignment — measurement dependency), **RIB-041** (eval harness — downstream consumer), **RIB-042** (ratio-based quality_score — the no-go fallback and downstream consumer).
- External: FActScore (atomic-fact decomposition + per-fact support scoring) and ALCE (Automatic LLM Citation Evaluation — citation precision/recall) — the two methodologies being adapted.

---

## Notes

- 2026-06-23: Charter authored (Mode B — Contract Drafting). Verdict left `null`; no legs executed. Gap (a) confirmed out of scope against the current tree; grounding facts for gap (b) verified against `telemetry.py` and `planning.py`.
