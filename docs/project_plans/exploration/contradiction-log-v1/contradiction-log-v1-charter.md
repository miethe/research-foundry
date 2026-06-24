---
schema_version: 2
doc_type: exploration_charter
title: "contradiction_log v1 (RIB-003) — Exploration Charter"
status: draft
created: 2026-06-23
feature_slug: contradiction-log-v1
timebox_days: 5
hypothesis: "We believe a real contradiction-detection pipeline (embedding-blocked candidate pairs → cheap scorer → LLM arbiter, valid-time-guarded) is worth building as contradiction_log v1 because RF currently only records self-declared source cautions and has no mechanism to surface cross-source contradictions that undercut report claims."
deal_killer: "If real-source-card contradiction recall is too low to be useful (research flagged this as a MEDIUM-confidence risk — real-card recall likely below synthetic benchmarks) OR embedding infrastructure adds an unacceptable dependency or breaks RF's offline-first / files-as-truth posture, abandon the embedding pipeline and keep the v0 self-declared cautions path."
investigation_legs:
  - id: recall
    question: "Does cross-source contradiction detection actually find real contradictions in RF's existing source-card corpus, and is recall high enough to be useful versus the synthetic benchmark research relied on?"
    assigned_to: spike-writer
  - id: embedding-infra
    question: "What embedding stack can RF adopt that coexists with its offline-first, files-as-truth posture (local model + sqlite-vec or similar), degrades gracefully when offline, and could be shared with future similarity needs?"
    assigned_to: data-layer-expert
  - id: scorer-arbiter
    question: "AlignScore vs MiniCheck as the cheap scorer, and what LLM-arbiter cost/latency budget (batch vs streaming) and threshold bands keep per-run cost acceptable?"
    assigned_to: spike-writer
  - id: valid-time
    question: "How should valid-time guards be represented (date ranges / source versioning / confidence decay) so that stale or superseded contradictions do not fire?"
    assigned_to: data-layer-expert
verdict_criteria:
  go:
    - "All investigation legs report confidence >= 0.7"
    - "Deal-killer condition not triggered — recall leg shows useful real-card recall on RF's corpus"
    - "Embedding-infra leg identifies a stack that degrades gracefully offline without breaking files-as-truth"
  no_go:
    - "Deal-killer condition triggered"
    - "recall leg measures real-card recall below the useful threshold with confidence >= 0.8"
    - "embedding-infra leg finds no stack that preserves offline-first operation"
  conditional:
    - "Recall is useful but embedding infra must be shared with / deferred to a separate similarity-infra effort"
    - "Scorer/arbiter choice or valid-time model remains open but resolvable by a specific named follow-up SPIKE"
verdict: null
verdict_rationale: null
output_artifacts: []
related_documents:
  - docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md
---

# contradiction_log v1 (RIB-003) — Exploration Charter

<!-- Copy to docs/project_plans/exploration/[feature-slug]/[feature-slug]-charter.md -->
<!-- Use /plan:explore to scaffold most fields from an idea description. -->

## Hypothesis Context

This exploration derives from completed research run **RIB-003** (IntentTree node `node_01KVQYMBTYBRRT5WC7XE7T9JRH`), surfaced in the completed-runs outcomes harvest. The research recommends building `contradiction_log` v1 as a real detection pipeline: embedding-blocked candidate pairs → a cheap scorer (AlignScore/MiniCheck) → an LLM arbiter, with valid-time guards, deferring a knowledge-graph judge to v2.

RF today has a **skeleton only**. `src/research_foundry/services/claim_mapping.py` (~lines 135–144) writes `contradiction_log.yaml` (`{run_id, generated_at, contradictions:[{source_card_id, text, locator}]}`) seeded **only** from each extraction card's `contradictions_or_cautions` field — i.e. self-declared source cautions, not cross-source comparison. Claims can carry status `contradicted`, and the verifier enforces `contradicted_is_labeled`. What is missing: no embedding infrastructure anywhere in the repo, no cross-source / cross-claim candidate-pair detection, no cheap scorer, no LLM arbiter, and no valid-time / temporal guards.

This is framed as a **SPIKE** rather than a direct build because it introduces a new subsystem (embedding infra) and carries unresolved choices. Critically, the source research itself is **MEDIUM evidence**: it flags that real-source-card contradiction recall may fall below the synthetic benchmarks the recommendation rests on. That risk is the crux of this charter — the `recall` leg directly tests it, and the deal-killer is written around it.

---

## Investigation Legs

<!-- One subsection per leg. Each leg runs as a SPIKE via /plan:spike --leg-of=[charter-path]. -->
<!-- Add/remove subsections to match investigation_legs entries. -->

### Leg: recall — Real-card contradiction recall vs synthetic benchmark

**Question**: Does cross-source contradiction detection actually find real contradictions in RF's existing source-card corpus, and is recall high enough to be useful versus the synthetic benchmark research relied on?
**Assigned to**: `spike-writer`
**Expected output**: `docs/project_plans/exploration/contradiction-log-v1/spikes/recall-spike.md`

This leg directly tests the deal-killer. The harvest report (line 56) records RIB-003 as one of the two MEDIUM-evidence items precisely because real-card contradiction recall is likely below synthetic benchmarks. Unknowns this leg must address:

- Whether RF's existing source-card corpus contains enough genuine cross-source contradictions to measure recall at all, and how a ground-truth set would be assembled (hand-labeled subset vs. seeded synthetic pairs).
- The recall a candidate-pair → scorer pipeline achieves on REAL cards versus the synthetic benchmark in the source research — quantify the gap.
- A concrete "useful threshold" definition: below what recall is the pipeline not worth its dependency cost (this number becomes the no-go gate).
- How the existing self-declared `contradictions_or_cautions` path (claim_mapping.py ~135–144) compares as a recall baseline — does the embedding pipeline beat v0 enough to justify itself?

### Leg: embedding-infra — Embedding stack vs offline-first / files-as-truth

**Question**: What embedding stack can RF adopt that coexists with its offline-first, files-as-truth posture (local model + sqlite-vec or similar), degrades gracefully when offline, and could be shared with future similarity needs?
**Assigned to**: `data-layer-expert`
**Expected output**: `docs/project_plans/exploration/contradiction-log-v1/spikes/embedding-infra-spike.md`

RF has no embedding infrastructure anywhere in the repo, and Markdown/YAML is the source of truth. This leg must address:

- Local vs. hosted embedding model choice, and whether a local model keeps RF runnable fully offline (a stated RF posture) without an external API dependency.
- Vector store / index choice (e.g. `sqlite-vec`, in-process FAISS, or flat-file) that does not displace Markdown/YAML as the authority — embeddings as a derived/cache artifact, not a new source of truth.
- Graceful-degradation behavior: what `contradiction_log` does when the embedding stack is unavailable (must fall back to v0 self-declared cautions, never hard-fail a run).
- Whether this infra should be designed as shared similarity infrastructure (reusable by future RF features) or scoped narrowly to contradiction blocking — informs the `conditional` verdict path about sharing/deferral.

### Leg: scorer-arbiter — Cheap scorer choice + LLM-arbiter budget

**Question**: AlignScore vs MiniCheck as the cheap scorer, and what LLM-arbiter cost/latency budget (batch vs streaming) and threshold bands keep per-run cost acceptable?
**Assigned to**: `spike-writer`
**Expected output**: `docs/project_plans/exploration/contradiction-log-v1/spikes/scorer-arbiter-spike.md`

The pipeline is cheap-model-first (scorer) then expensive-model-arbiter, matching RF's "cheap models extract, expensive models synthesize" principle. This leg must address:

- AlignScore vs MiniCheck trade-offs for the cheap scoring stage: accuracy on RF-style card text, model size / offline-runnability (ties to the embedding-infra leg), and licensing.
- Threshold bands: what scorer-confidence range gets auto-classified vs. escalated to the LLM arbiter, and the precision/recall trade-off those bands imply.
- LLM-arbiter cost and latency budget per run: batch (defer arbitration to end of run) vs. streaming (arbitrate as pairs surface), and the per-run token/cost ceiling that keeps this affordable at RF's run volume.
- How arbiter verdicts map onto the existing claim `contradicted` status and the verifier's `contradicted_is_labeled` enforcement, so output integrates with the current ledger rather than bolting on a parallel state.

### Leg: valid-time — Valid-time guard representation

**Question**: How should valid-time guards be represented (date ranges / source versioning / confidence decay) so that stale or superseded contradictions do not fire?
**Assigned to**: `data-layer-expert`
**Expected output**: `docs/project_plans/exploration/contradiction-log-v1/spikes/valid-time-spike.md`

Without temporal guards, a contradiction between a current source and a superseded one would fire spuriously. This leg must address:

- Representation options: explicit valid-time date ranges per source/claim, source versioning, or confidence decay over time — and which RF source-card fields already carry usable temporal signal.
- Where valid-time metadata lives in the files-as-truth model (source card frontmatter vs. claim ledger entries) without breaking existing schemas.
- The guard rule: given two contradicting claims with different valid-times, when is the contradiction suppressed, surfaced as "resolved/superseded", or surfaced as live.
- Whether v1 can ship a minimal guard (e.g. date-range suppression only) with confidence decay deferred to v2 alongside the KG-judge.

---

## Verdict Criteria Narrative

**Go** if: the `recall` leg shows real-card contradiction recall on RF's corpus clears the named useful threshold (beating the v0 self-declared baseline by a worthwhile margin), the `embedding-infra` leg identifies a stack that degrades gracefully offline without displacing Markdown/YAML as truth, and all four legs report confidence >= 0.7. The deal-killer is untriggered.

**No-go** if: the deal-killer fires — real-card recall measures below the useful threshold with confidence >= 0.8, OR no embedding stack preserves RF's offline-first operation. In that case, abandon the embedding pipeline and keep the v0 self-declared `contradictions_or_cautions` path as-is.

**Conditional** if: recall is useful and the pipeline is worth building, but a bounded question remains — e.g. the embedding infra should be promoted to shared similarity infrastructure (or deferred behind a separate infra effort), or the AlignScore-vs-MiniCheck choice or valid-time representation needs one named follow-up SPIKE before implementation. Name the question and the specific next step in the rationale.

---

## Out of Scope

- KG-judge / knowledge-graph contradiction reasoning — explicitly deferred to v2 by the source research.
- Confidence-decay valid-time modeling if the valid-time leg concludes a minimal date-range guard suffices for v1.
- Replacing or removing the v0 self-declared `contradictions_or_cautions` seeding in `claim_mapping.py` — v1 augments, it does not rip out the existing path (which also remains the no-go fallback).
- Any writeback of contradiction findings to MeatyWiki / SkillMeat / CCDash — integration targets are downstream of a working detector.

---

## Citations / Prior Art

- `docs/project_plans/reports/investigations/rf-completed-runs-outcomes-harvest.md` — RIB-003 recommendation (line 69), MEDIUM-evidence recall risk (line 56), verification-core sequencing RIB-002 → RIB-001 → RIB-003 (line 90).
- `src/research_foundry/services/claim_mapping.py` (~lines 135–144) — current `contradiction_log.yaml` skeleton, seeded only from `contradictions_or_cautions`.
- IntentTree node `node_01KVQYMBTYBRRT5WC7XE7T9JRH` — source research run RIB-003.

---

## Notes

<!-- Append timestamped entries as legs complete. Format: YYYY-MM-DD: [note]. -->
- 2026-06-23: Charter authored (Mode B). Verdict left null; no legs executed. Grounding facts verified against claim_mapping.py and the harvest report.
