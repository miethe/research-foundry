---
schema_version: 2
doc_type: report
report_category: investigation
title: "RF Completed-Runs Outcome Harvest — Expected Outcomes Across Projects"
status: triaged
source: agent
created: 2026-06-22
updated: 2026-06-23
feature_slug: rf-completed-runs-outcomes-harvest
description: >
  Reviews the 18 completed ideas in the Research Foundry research backlog and
  derives, per run, the concrete actionable next-step and which Agentic-OS
  subsystem owns it. Replaces the misfit /plan:explore go/no-go framing with a
  research-harvest synthesis. Every outcome is routed into its target project's
  IntentTree tree.
related_documents:
  - backlog/research_idea_backlog.yaml
tags: [research-foundry, research-harvest, rf-runs, intenttree, cross-project]
---

# RF Completed-Runs Outcome Harvest

**What this is.** A review of every **completed** Research Foundry run (the 18 ideas
marked `status: completed` in `backlog/research_idea_backlog.yaml`) that answers one
question per run: *given what the research concluded, what is the single most valuable
concrete next action, and which Agentic-OS subsystem owns it?* It is a harvest, not a
feasibility verdict — the input is 18 verified research conclusions, and the output is a
per-project work queue.

> **Method note.** This was requested via `/plan:explore`, but that command drives a
> single speculative idea to a `{go|no-go|conditional}` verdict via a falsifiable
> hypothesis + deal-killer. The request is a portfolio harvest over 18 conclusions, so the
> exploration charter/legs/feasibility-brief artifacts were intentionally dropped (also:
> `manage-exploration-status.py` is not installed in this repo). Instead: cheap extract of
> the 18-idea work-list → 6 pillar-grouped subagents read each run's `report_deterministic.md`
> + `writebacks/` and emitted one structured outcome record per run → synthesis (this doc)
> → routing into IntentTree.

## Headline finding

**The research was done and verified, but its decisions never reached any project's work
graph.** Every one of the 18 runs has a complete, claim-verified `report_deterministic.md`,
yet each run's `writebacks/` contains only a *generic auto-distilled source-note* (every
claim `include: true`) plus an identical `research_swarm_v0` SkillBOM stub. **None captured
the specific engineering recommendation its report's inference section actually implies.**
So the actionable outcomes below were, until now, un-harvested. That is the gap this review
closes.

Secondary observations:

- **Action mix:** 13 build-features, 3 ADRs, 2 pattern-adoptions. No run is "already
  landed" — though RIB-025 and RIB-026 partly *validate* already-shipped designs (the
  research post-dates RF's 2026-06-13 ship and the Operator's 2026-06-15 ship), their
  net-new deltas are real and captured.
- **Evidence:** 16/18 high, 2 medium — RIB-003 (real-card contradiction recall likely below
  synthetic benchmarks) and RIB-026 (latency/cost wins are vendor-asserted; validate on own
  telemetry before cutover).
- **The backlog's `suggested_project` is uniformly "Research Foundry"** (an originating-project
  default), so the cross-project ownership below is *derived from content*, not metadata —
  that derivation is the core value-add.

## Per-run outcome map (18 completed)

| RIB | Expected outcome (imperative) | Action | Owner | 2nd | Evid | Effort | IntentTree node |
|-----|-------------------------------|--------|-------|-----|------|--------|-----------------|
| 001 | Build claim-segmentation + sentence-level source-alignment stage (Claimify + LongCite); route multi-hop/partial claims to permanent human-review tier | build | research-foundry | meatywiki | high | L | `node_01KVQYJZJZR2YQQ7PNF9X9YH5Y` |
| 002 | Add pre-hoc grounded-gen + mandatory post-hoc atomic-claim verifier gate on material claims; URL-existence check + abstain band; manage residual unsupported rate | build | research-foundry | ccdash | high | L | `node_01KVQYKB4SQ1AHK52X6J61G3XQ` |
| 003 | Build `contradiction_log` v1: embedding-blocked pairs → cheap scorer (AlignScore/MiniCheck) → LLM arbiter, with valid-time guards; defer KG-judge to v2 | build | research-foundry | meatywiki | med | L | `node_01KVQYMBTYBRRT5WC7XE7T9JRH` |
| 025 | Close RF MVP gaps prior art flags as MUST-have: explicit plan/state persistence + FActScore/ALCE atomic-fact citation precision/recall metrics | build | research-foundry | — | high | M | `node_01KVQYMHBN8VP5XRQC8XH403JX` |
| 041 | Build two-leg eval harness: committed cassette/VCR deterministic leg gates PRs + non-blocking nightly live leg with score-delta regression gate | build | research-foundry | ccdash | high | L | `node_01KVQYMNG71TW5YJV3KA3HPM6G` |
| 042 | Implement deterministic `quality_score` composite from ratios (support_rate dominant) + new `distinct_source_domains`; emit per-dimension vector; Goodhart caps | build | research-foundry | ccdash | high | M | `node_01KVQYMT6GF0T5PS1QK469DJ2J` |
| 017 | Build writeback-boundary default-deny gate keyed on (sensitivity_tier, target_id, target_topology); justified-override + append-only audit | build | research-foundry | governance | high | M | `node_01KVQYMYPN51B5TRGPR65NNPW3` |
| 018 | Implement one-profile-per-process credential isolation at every spawn boundary; key fingerprinting in telemetry; HITL on cross-profile elevation | build | research-foundry | governance | high | M | `node_01KVQYN3RQGZTYRKC8J2YRJJH3` |
| 053 | Build RF intake adapters → normalized citation tuple {span,source,relation,confidence}; idempotent URL+date dedup; OpenAI+Perplexity first | build | research-foundry | meatycapture | high | L | `node_01KVQYN8SJYKBAX7F24MPN9CJR` |
| 033 | Write ADR: BGE-M3 (512d) + sqlite-vec default; sqlite-vec→pgvector-HNSW migration triggered by latency, not note count | adr | meatywiki | research-foundry | high | M | `node_01KVQYNDVMJ98BDKK2TET18594` |
| 034 | Build tiered retrieval: column-weighted FTS5 (title/heading boost) → bge-reranker @~10K → RRF(k=60) dense fusion @~50K; skip semantic chunking | build | meatywiki | research-foundry | high | L | `node_01KVQYNJX88ASKY7EEKREPRJB3` |
| 035 | Build entity-merge pipeline: blocking → cross-encoder → 3 bands (≥0.95 auto / 0.80–0.95 review / <0.80 ignore); git-atomic reversible merge w/ SAME_AS stub | build | meatywiki | skillmeat | high | L | `node_01KVQYNQYWR0V0NBQF2G4PRMT4` |
| 037 | Write ADR: files-as-truth (MD+YAML+Git) + disposable rebuildable index; name the concurrent-writer breakpoint that triggers a Postgres write coordinator | adr | meatywiki | agentic_meta_dev | high | S | `node_01KVQYNXMX7ZEPH2HWPPFFH7YX` |
| 045 | Adopt single-call MSP logprob confidence for vault classify/route (+Ollama self-report fallback); abstain via SGR risk-coverage; escalate only borderline band | adopt | meatywiki | governance | high | M | `node_01KVQYP2H4MA6RTDV7BPQ3M0N1` |
| 024 | Adopt per-seam pattern map: git post-* (write seams) / file-watch+reconcile (vault→graph) / SSE+Last-Event-ID (telemetry) / append-log + content-hash idempotency | adopt | agentic_meta_dev | ccdash | high | M | `node_01KVQYP8G8DTQSRDD25P71HBJ2` |
| 026 | Evolve Operator classifier from pure-LLM to hybrid cascade (rules→embedding→LLM); bind per-intent cost caps at routing boundary; emit routing telemetry | build | agentic_meta_dev | ccdash | med | L | `node_01KVQYQKAHD8QDSWWCR7PPDNGE` |
| 047 | Spec closed-loop telemetry schema (artifact+version, tool-calls, tokens/cost, judge_score, human_edit_count) + sequential-test promotion gate (ADR) | adr | ccdash | skillmeat | high | L | `node_01KVQYPMGGK9GG37HXK218R5H4` |
| 051 | Add SkillBOM promotion governance: approval_status enum, reviewer, append-only transitions log, demotion; RBAC-protect the promotion pointer | build | skillmeat | agentic_meta_dev | high | M | `node_01KVQYPSCG1Y68P7823XDAVNY0` |

## Per-project rollup & recommended sequencing

### research-foundry — 9 outcomes (the largest harvest; RF is its own biggest customer)
Two natural tracks:
- **Verification core (do first):** RIB-002 (verifier gate) → RIB-001 (claim segmentation+alignment) → RIB-003 (contradiction_log v1). These are the spine RF's value proposition rests on; 002 is the keystone and the others feed it.
- **Quality & safety rails:** RIB-042 (deterministic quality_score) and RIB-041 (two-leg eval harness) make RF's output measurable and CI-safe — pair them. RIB-017 + RIB-018 (writeback gate + key isolation) are the security pair; ship together. RIB-053 (intake adapters) and RIB-025 (state persistence + citation metrics) are independent enhancers.

### meatywiki — 5 outcomes (the knowledge-vault design pillar)
- **Ratify foundations first (cheap, unblock the rest):** RIB-037 (files-as-truth ADR, S) then RIB-033 (embedding/vector ADR, M). These two ADRs set the posture the build-features assume.
- **Then build:** RIB-034 (tiered retrieval) and RIB-035 (entity-merge) are the larger lifts; RIB-045 (MSP logprob confidence) upgrades the vault classifier and is independent.

### agentic_meta_dev — 2 outcomes (Operator / seams)
- RIB-024 (seam→pattern map) is high-evidence and the cross-tool backbone — adopt it as the seam standard. RIB-026 (hybrid-cascade classifier) is medium-evidence; **validate the latency/cost claims on RF's own routing telemetry before cutting over** the Operator's classifier.

### ccdash — 1 outcome
- RIB-047 (closed-loop telemetry schema + promotion gate). **Composes with RIB-051** — CCDash emits the lagging human-validated signals that SkillMeat's promotion gate consumes. Sequence RIB-047 before/with RIB-051.

### skillmeat — 1 outcome
- RIB-051 (SkillBOM promotion governance). Net-new fields on the candidate frontmatter + RBAC pointer; depends on RIB-047's telemetry gate for the promotion signal.

**Cross-project composition to note:** RIB-047 (ccdash) → RIB-051 (skillmeat) is a real dependency chain (telemetry feeds the promotion gate); RIB-001/003 (RF) `also_informs` meatywiki's retrieval; RIB-035 (meatywiki entity-merge) `also_informs` skillmeat artifact dedup.

## Routing record

All 18 outcomes are live in IntentTree (workspace `ws_01KV8VMWX9EJ6VDQKEBMYQZRXG`), each as an
`atomic_task` under a per-project container `work_area` titled **"Inbound: RF research-harvest
outcomes (2026-06-22)"**, tagged `research-harvest` + `RIB-0xx` + effort/evidence, with the
source `run_id` in each task's description and acceptance criteria attached.

| Tree (slug) | Container `work_area` node | Outcomes routed |
|-------------|----------------------------|-----------------|
| research-foundry | `node_01KVQYD2BC6184CCF5QBDEAWJ1` | RIB-001, 002, 003, 017, 018, 025, 041, 042, 053 |
| meatywiki | `node_01KVQYD53423S6FPPRKB5NPX1M` | RIB-033, 034, 035, 037, 045 |
| agentic_meta_dev | `node_01KVQYD7VFQ2QYQDYZYN3F7TZ2` | RIB-024, 026 |
| ccdash | `node_01KVQYDAM5DTBT25AAJEP4ZYP3` | RIB-047 |
| skillmeat | `node_01KVQYDCV1V8E0EAB8J16E1WYT` | RIB-051 |

Per-task node IDs are in the "Per-run outcome map" table above. (Implementation note: the
IntentTree `create_node` API rejected `effort_size`, so effort is encoded as an `effort-S/M/L`
tag; `external_ref` was likewise dropped in favor of the `run_id` in each description.)

## Data-hygiene gaps surfaced (not blocking)

- **`runs/` (≈39 dirs) ⊋ completed backlog marks (18).** ~21 run directories on disk are not
  marked `completed` in the backlog (some are `_staging`, some appear to be runs whose lifecycle
  links were never backfilled). The backlog's lifecycle note says to "backfill `links.*` as it
  moves" — that backfill is incomplete. A reconcile pass (runs-on-disk ↔ backlog status/run_id)
  would tighten traceability.
- **Writeback contract is too shallow.** Because every run's `writebacks/` is a generic
  source-note + identical SkillBOM stub, the actionable engineering decision is lost at the
  RF→project boundary. Worth a follow-up: have the deterministic tail emit a *decision/ADR-candidate*
  writeback (the inference section already contains it) rather than only a source-note. This is
  itself a seam fix — exactly the kind RIB-024 is about.

## Recommended next actions

1. **Triage the routed nodes in IntentTree** — they're `not_started`; promote the verification-core
   trio (RIB-002→001→003) and the two cheap MeatyWiki ADRs (RIB-037, RIB-033) to current first.
2. **Decide per outcome whether it escalates to a tiered plan** — the L-effort build-features
   (RIB-001/003/034/035/041/053/026) are Tier-2-ish and warrant a Feature Contract or PRD before
   coding; the ADRs and adopt-patterns can proceed directly.
3. **Consider the writeback-contract fix** as a small RF enhancement so future completed runs
   self-harvest their decisions instead of needing this manual pass.

## Planning status (2026-06-23)

The **9 research-foundry-owned outcomes** here (plus the 2 seam fixes from the
[writeback/backlog handoff](./rf-writeback-and-backlog-reconcile-handoff.md)) have been triaged and
routed to planning artifacts. See the
[RF Research-Harvest Implementation Planning Index](./rf-harvest-rf-items-planning-index.md) for the
full routing table and build sequencing. Summary:

| RIB | Routed to | Status |
|-----|-----------|--------|
| RIB-002 | Feature Contract `verifier-url-check-abstain-band` | ready to execute |
| RIB-042 | Feature Contract `deterministic-quality-score` | ready to execute |
| RIB-041 | Feature Contract `two-leg-eval-harness` | ready to execute |
| RIB-053 | Feature Contract `intake-citation-adapters` | ready to execute |
| RIB-001 | SPIKE Charter `claim-segmentation-source-alignment` | design-first |
| RIB-003 | SPIKE Charter `contradiction-log-v1` | design-first (deal-killer: real-card recall) |
| RIB-017 | SPIKE Charter `writeback-default-deny-gate` | design-first |
| RIB-018 | SPIKE Charter `credential-process-isolation` | design-first (Mode D) |
| RIB-025 | SPIKE Charter `citation-precision-recall-metrics` | design-first (net-new metrics only; persistence already satisfied) |
| Gap 1 | Feature Contract `writeback-decision-record` | ready to execute |
| Gap 2 | Feature Contract `backlog-reconcile-command` | ready to execute |

The cross-project outcomes (meatywiki, agentic_meta_dev, ccdash, skillmeat) remain owned by those
projects and were not planned here. Backlog research-lifecycle status is unchanged (the research is
`completed`; implementation lifecycle is tracked by the artifacts above + the IntentTree nodes in the
per-run table).
