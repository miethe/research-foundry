---
schema_version: 2
doc_type: exploration_charter
title: "Claim Segmentation + Sentence-Level Source-Alignment — Exploration Charter"
status: draft
created: 2026-06-23
feature_slug: claim-segmentation-source-alignment
timebox_days: 5
hypothesis: "We believe a Claimify-style claim-segmentation stage plus a LongCite-style sentence-level source-alignment stage is worth building because RF today maps extracted facts to ledger claims 1:1 with only a coarse locator string, and finer-grained segmentation + sentence-to-span alignment should materially improve claim-grounding precision."
deal_killer: "If integrating Claimify/LongCite (or a custom equivalent) cannot run within RF's offline-first / cheap-extract-expensive-synthesize cost model, OR yields no measurable grounding-precision gain over the current 1:1 extraction+locator approach (measured per RIB-025), abandon."
investigation_legs:
  - id: segmentation
    question: "Can a Claimify-style segmentation stage (sentence-split + atomic-claim extraction) run on RF's extraction cards and/or synthesized report within the offline-first cost model, and at what added cost/latency?"
    assigned_to: ai-engineer
  - id: alignment
    question: "Can a LongCite-style sentence→source-span alignment stage represent spans richly enough to replace/augment the current locator string, and what is the schema impact on the claim ledger?"
    assigned_to: ai-engineer
  - id: review-routing
    question: "Can 'multi-hop' and 'partial' claims be defined operationally and routed automatically to a permanent human-review tier by extending the existing requires_human_review mechanism?"
    assigned_to: python-backend-engineer
  - id: value
    question: "Does segmentation + alignment produce a measurable grounding-precision uplift over the current 1:1 extraction+locator baseline (per the RIB-025 citation-metrics harness)?"
    assigned_to: spike-writer
verdict_criteria:
  go:
    - "All investigation legs report confidence >= 0.7"
    - "Deal-killer condition not triggered (cost model respected AND measurable precision gain demonstrated per RIB-025)"
    - "Schema impact on claim_ledger is additive/back-compatible OR has a defined migration path"
  no_go:
    - "Deal-killer condition triggered"
    - "Segmentation or alignment leg reports infeasibility within the offline-first cost model with confidence >= 0.8"
    - "Value leg shows no measurable grounding-precision uplift over the 1:1 baseline"
  conditional:
    - "Segmentation + alignment are feasible but the value measurement is blocked on RIB-025 not yet shipping a metrics harness — proceed to contract only after RIB-025 supplies the measurement"
    - "Review-routing classifier is feasible but the 'multi-hop'/'partial' operational definition needs a labeled-sample calibration pass before thresholds are fixed"
verdict: null
verdict_rationale: null
output_artifacts: []
---

# Claim Segmentation + Sentence-Level Source-Alignment — Exploration Charter

<!-- Copy to docs/project_plans/exploration/[feature-slug]/[feature-slug]-charter.md -->
<!-- Use /plan:explore to scaffold most fields from an idea description. -->

## Hypothesis Context

This exploration derives from completed research run **RIB-001** (IntentTree node `node_01KVQYJZJZR2YQQ7PNF9X9YH5Y`, classified **high** evidence in the completed-runs harvest). RIB-001 recommends building a Claimify-style claim-segmentation stage plus a LongCite-style sentence-level source-alignment stage, and routing multi-hop/partial claims to a permanent human-review tier. The harvest flags this as the verification spine RF's value proposition rests on (sequenced RIB-002 verifier gate → RIB-001 → RIB-003 contradiction log), and explicitly calls it the heaviest, most greenfield item — hence a SPIKE before any contract/PRD.

The counterfactual that justifies the investigation is what RF does **today**: claims are produced deterministically in `src/research_foundry/services/claim_mapping.py::build_claim_ledger()`, where each `extraction_card.extracted_facts` entry becomes exactly one ledger claim (1:1), `claim_type` is assigned by a heuristic (`_claim_type()`), and each claim carries a `sources[].locator` **string** (a paragraph/section reference such as `para/0`) — not a sentence-level alignment. A human-review path exists but is **manual only**: `src/research_foundry/services/verification.py::_intent_requires_review()` reads `intent.governance.requires_human_review`; there is no automatic routing of complex/multi-hop claims. The three capabilities RIB-001 asks for are all **missing**: (a) no Claimify-style segmentation (NLP sentence-split + atomic-claim extraction from the report body), (b) no LongCite-style sentence→source-span alignment, (c) no automatic multi-hop/partial-claim classifier and router. This SPIKE tests whether closing those gaps is feasible within RF's cost model and demonstrably improves grounding precision.

---

## Investigation Legs

<!-- One subsection per leg. Each leg runs as a SPIKE via /plan:spike --leg-of=[charter-path]. -->
<!-- Add/remove subsections to match investigation_legs entries. -->

### Leg: segmentation — Claimify integration vs custom segmentation

**Question**: Can a Claimify-style segmentation stage (sentence-split + atomic-claim extraction) run on RF's extraction cards and/or synthesized report within the offline-first cost model, and at what added cost/latency?
**Assigned to**: `ai-engineer`
**Expected output**: `docs/project_plans/exploration/claim-segmentation-source-alignment/spikes/segmentation-spike.md`

- Decide the **input surface**: does segmentation operate on `extraction_card.extracted_facts` entries (pre-ledger, where `build_claim_ledger()` currently does 1:1 mapping in `claim_mapping.py`) or on the synthesized report body produced downstream of the claim ledger? Document the trade-off (extraction cards are cheaper and earlier; the report body is what readers actually cite).
- Evaluate **Claimify integration vs a custom equivalent**: dependency footprint, model/runtime requirements, and whether either can satisfy RF's offline-first constraint (no mandatory network calls) and the cheap-extract-expensive-synthesize split (segmentation is an extract-tier operation, so it must stay cheap).
- Quantify **cost/latency** added per run to RF's pipeline; relate to the existing deterministic 1:1 path which is effectively free.
- Identify whether segmentation changes the 1:1 invariant in `build_claim_ledger()` (one fact → potentially N atomic claims) and the downstream blast radius of that change.

---

### Leg: alignment — LongCite-style sentence→source-span alignment

**Question**: Can a LongCite-style sentence→source-span alignment stage represent spans richly enough to replace/augment the current locator string, and what is the schema impact on the claim ledger?
**Assigned to**: `ai-engineer`
**Expected output**: `docs/project_plans/exploration/claim-segmentation-source-alignment/spikes/alignment-spike.md`

- Decide **alignment direction**: report-sentence → source-span (LongCite default) vs source-span → report-claim. State which direction RF's pipeline can produce reliably given that source content is already on disk as source cards.
- Define the **span representation** and contrast it with today's `sources[].locator` string (`para/0`-style) set in `claim_mapping.py` (line ~112). Determine whether spans are character offsets, sentence indices, or quote anchors, and whether the new representation augments or replaces `locator`.
- Assess **schema impact on `claims/claim_ledger.yaml`**: is the change additive/back-compatible (new optional field) or breaking (requires migration of existing ledgers)? Note interaction with `verification.py`'s claim-basis checks.
- Confirm alignment is an **expensive-synthesize-tier** operation (it reasons over source text) and stays on the correct side of the cost split — i.e., it must not be forced into the cheap extract tier.

---

### Leg: review-routing — operational definition + automatic routing

**Question**: Can 'multi-hop' and 'partial' claims be defined operationally and routed automatically to a permanent human-review tier by extending the existing requires_human_review mechanism?
**Assigned to**: `python-backend-engineer`
**Expected output**: `docs/project_plans/exploration/claim-segmentation-source-alignment/spikes/review-routing-spike.md`

- Define **"multi-hop"** and **"partial"** operationally — candidate signals: dependency depth (a claim that composes ≥2 source-backed sub-claims), inference scope (claim asserts more than any single aligned span supports), and confidence/alignment-strength below a threshold. Recommend which signal(s) are computable from segmentation + alignment outputs.
- Design the **automatic router** as an extension of the existing manual mechanism: today `verification.py::_intent_requires_review()` only reads `intent.governance.requires_human_review` (a coarse, intent-level boolean at line ~718). Propose a **claim-level** routing decision that coexists with the intent-level flag — i.e., individual multi-hop/partial claims get flagged even when the intent does not globally require review.
- Specify where the permanent human-review tier lives in the artifact model (a review queue/state on the claim, surfaced through the verification verdict) and how a routed claim blocks or annotates the bundle without silently passing the verify gate.
- Note the calibration dependency: thresholds for "multi-hop"/"partial" likely need a labeled-sample pass before they are fixed (drives the `conditional` verdict).

---

### Leg: value — measurable grounding-precision uplift

**Question**: Does segmentation + alignment produce a measurable grounding-precision uplift over the current 1:1 extraction+locator baseline (per the RIB-025 citation-metrics harness)?
**Assigned to**: `spike-writer`
**Expected output**: `docs/project_plans/exploration/claim-segmentation-source-alignment/spikes/value-spike.md`

- Establish the **baseline**: current 1:1 `extracted_facts` → claim mapping with a `locator` string, as produced by `build_claim_ledger()`. Define what "grounding precision" means against this baseline.
- Define the **measurement** in terms of the citation precision/recall metrics being specified by **RIB-025** (sibling exploration `docs/project_plans/exploration/citation-precision-recall-metrics/`). This leg does **not** build a metrics harness — RIB-025 owns that. This leg consumes RIB-025's metric definitions and harness to produce a before/after comparison.
- Tie directly to the **deal-killer**: if no measurable uplift over the 1:1 baseline can be demonstrated, the value leg fails and the verdict is no-go. If RIB-025's harness is not yet available at SPIKE time, this leg returns `conditional` (proceed only once RIB-025 supplies the measurement).
- Capture the **cost/value ratio**: pair the precision uplift against the cost/latency numbers from the `segmentation` and `alignment` legs so the go/no-go decision weighs benefit against the cheap-extract-expensive-synthesize budget.

---

## Verdict Criteria Narrative

<!-- Make each gate concrete so any agent can apply it consistently. -->

**Go** if: all four legs land at confidence ≥ 0.7; segmentation and alignment are shown to run within RF's offline-first / cheap-extract-expensive-synthesize cost model; the claim-ledger schema change is additive/back-compatible (or has a concrete migration path); the review-routing classifier has a workable operational definition; and the `value` leg demonstrates a measurable grounding-precision uplift over the 1:1 baseline using the RIB-025 metrics harness.

**No-go** if: the deal-killer fires — i.e., Claimify/LongCite/custom-equivalent cannot run inside the cost model (segmentation or alignment leg reports infeasibility at confidence ≥ 0.8), or the value leg shows no measurable precision gain over the current 1:1 extraction+locator approach.

**Conditional** if: segmentation + alignment + routing are feasible but the value measurement is blocked because RIB-025 has not yet shipped its citation-metrics harness — in which case proceed to a contract/PRD only after RIB-025 supplies the measurement; or if routing is feasible but the multi-hop/partial thresholds require a labeled-sample calibration pass before they can be fixed.

---

## Out of Scope

- Building the citation precision/recall **metrics harness** itself — that is RIB-025's deliverable (`docs/project_plans/exploration/citation-precision-recall-metrics/`); this SPIKE consumes it.
- The **verifier gate** (RIB-002) and **contradiction log** (RIB-003) — separate spine items that feed from / into this stage but are explored independently.
- Production implementation, schema migration, or any code changes — this is a Mode B contract-drafting SPIKE; a contract/PRD follows a `go`/`conditional` verdict.
- MeatyWiki retrieval writeback (`also_informs` per the harvest) — downstream consumer, not part of feasibility.

---

## Citations / Prior Art

<!-- Back-links to past explorations, SPIKEs, ADRs, or external references consulted before starting. -->
- Harvest report (origin): `docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md` (RIB-001 row; node `node_01KVQYJZJZR2YQQ7PNF9X9YH5Y`; verification-spine sequencing RIB-002 → RIB-001 → RIB-003).
- Current 1:1 claim mapping + locator string: `src/research_foundry/services/claim_mapping.py` (`build_claim_ledger()`, `_claim_type()`, `locator` assignment).
- Current manual human-review flag: `src/research_foundry/services/verification.py` (`_intent_requires_review()`, `intent.governance.requires_human_review`).
- Measurement dependency (sibling exploration): `docs/project_plans/exploration/citation-precision-recall-metrics/` (RIB-025 — citation precision/recall metrics; supplies the value-leg measurement).
- External prior art referenced by RIB-001: Claimify (claim segmentation) and LongCite (sentence-level source attribution).

---

## Notes

<!-- Append timestamped entries as legs complete. Format: YYYY-MM-DD: [note]. -->
- 2026-06-23: Charter drafted (Mode B). Verdict left null; no legs executed. Code anchors (`claim_mapping.py::build_claim_ledger`, `verification.py::_intent_requires_review`) and harvest RIB-001 row verified on disk. RIB-025 charter directory does not yet exist — cited as the canonical sibling path / measurement dependency.

related_documents:
- docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md
