---
title: "Consolidated AAR — First Full RF Runs: Swarm Orchestration & Cost Routing (HIGH backlog items)"
type: after_action_report
created: 2026-06-14
author: Nick Miethe (orchestrated by Claude Opus, Path-B research swarm)
status: final
scope: RIB-007, RIB-008, RIB-009, RIB-010 (pillar_swarm-orchestration-cost, priority=high)
related:
  - backlog/research_idea_backlog.yaml
  - .claude/skills/research-foundry-swarm/SPEC.md
  - runs/rf_run_20260613_as_of_mid_2026_what_are/
  - runs/rf_run_20260613_what_is_the_empirical_accuracy_differential/
  - runs/rf_run_20260613_what_is_the_current_release_state/
  - runs/rf_run_20260613_how_do_gpt_researcher_paperqa2_and/
---

# Consolidated AAR — First Full Research Foundry Runs

**Pillar:** Swarm Orchestration & Cost Routing — all four `priority: high` backlog ideas.
**Date:** 2026-06-13 → 2026-06-14 · **Orchestration:** Opus + Dynamic Workflow (one per run) · **Mode:** Path B (Claude-orchestrated discovery, RF governance spine + deterministic tail).

These were the **first end-to-end RF runs driven entirely by the swarm**. They double as a validation of the RF pipeline itself (capture → triage → plan → guard → discover → ingest → extract → claim-map → synthesize → verify → bundle → writeback) under real research load.

---

## 1. Run-by-run results

| Ref | Run ID (`rf_run_20260613_…`) | Artifact | Sources | Claims (sup / inf / spec) | Unsupported | Verify | Fix loops | Bundle |
|---|---|---|---|---|---|---|---|---|
| **RIB-009** *(pilot)* | `as_of_mid_2026_what_are` | market_scan (std) | 9 | **69** (57 / 11 / 1) | 0 | ✅ exit 0 | 0 | verified |
| **RIB-007** | `what_is_the_empirical_accuracy_differential` | technical_memo (deep) | 7 | **65** (46 / 17 / 2) | 0 | ✅ exit 0 | 0 | verified |
| **RIB-008** | `what_is_the_current_release_state` | technical_memo (deep) | 10 | **91** (69 / 20 / 2) | 0 | ✅ exit 0 | 0 | verified |
| **RIB-010** | `how_do_gpt_researcher_paperqa2_and` | technical_memo (deep) | 12 | **96** (78 / 16 / 2) | 0 | ✅ exit 0 | 0 | verified |
| **TOTAL** | 4 runs | — | **38** | **321** (250 / 64 / 7) | **0** | **4 / 4** | **0** | **4 / 4** |

Every run also emitted the three writeback candidates (`meatywiki_writeback.md`, `skillbom_candidate.md`, `ccdash_event.yaml`). 0 contradicted and 0 mixed claims across all runs.

### Compute & cost (subagent tokens, wall-clock)

| Run | Agents | Subagent tokens | Duration |
|---|---|---|---|
| RIB-009 (pilot) | 20 | ~1.00M | 14.6 min |
| RIB-007 | 23 | ~1.11M | 17.2 min |
| RIB-008 (re-run) | 20 | ~1.46M | 19.8 min |
| RIB-010 | 23 | ~1.31M | 20.1 min |
| **Successful subtotal** | **86** | **~4.88M** | ~71.7 min active |
| Throttled attempts (RIB-008₁, RIB-010₁) | 31 | ~1.37M | wasted |
| **Grand total (incl. waste + 1 args misfire)** | **~117** | **~6.25M** | — |

Roughly **1.2M tokens per verified research bundle**; ~22% token overhead was burned on the rate-limited parallel attempts (see §4).

---

## 2. Effectiveness — did the approach work?

**Yes — strongly.** The central question going in was whether RF could produce *genuinely evidence-backed, claim-verified* deliverables given that its native swarm adapters are **0/6 available offline** (`rf doctor`) and degrade to deterministic stubs. The answer is the **Path B** pattern from the swarm SPEC: Claude Code agents are the discovery/reading/synthesis muscle; RF is the governance spine + deterministic tail.

- **Real evidence, not stubs.** All 38 source cards cite real primary sources — official docs (`docs.gptr.dev`, `docs.perplexity.ai`, Anthropic SDK docs), GitHub releases/changelogs, vendor pricing pages, and benchmarks (LitQA2, AstaBench, the SEC extraction study, LongWeave).
- **The claim-ledger gate held perfectly.** 321/321 claims are either `supported` (mapped to a source card) or labeled `inference`/`speculation` with basis. **Zero** unsupported or contradicted claims reached any report. `rf verify` passed on the **first** attempt for all four runs — **no fix-loop iterations were needed**, and the deterministic fallback was **never** triggered (enrichment survived verification 4/4).
- **Calibrated honesty.** RIB-009 *refused* to score Gemini Deep Research and PaperQA2 because it found no first-party sources for them, flagging them as explicit evidence gaps rather than hallucinating — exactly the behavior the ledger discipline is meant to enforce.
- **Rich, structured deliverables.** Each report is a real technical_memo / market_scan with exec summary, comparison matrix, derivations, and decision rules — not a flat claim dump — while still satisfying the per-line `[claim:clm_NNN]` citation gate.

---

## 3. Findings — the actual research output

### RIB-007 · Cheap-extract vs deep-synthesize (two-tier model split)
- **The cheap-vs-deep accuracy gap is ~zero or *negative* for structured extraction** — small models (Phi-4 14B 0.798, Qwen3.5-35B 0.801, Schematron-8B 0.754) match/beat GPT-5 (0.795) on exact-match value accuracy. **The gap inverts at synthesis**, where long-form/complex outputs degrade even for frontier models.
- **Optimal RF policy is not a pure two-tier split but a hybrid: cheap extraction + targeted deep escalation** — the SEC benchmark shows hybrids recover **89% of best-architecture accuracy at 1.15× baseline cost vs 2.3× for always-deep**.
- **Break-even:** the split beats flat all-deep once extraction exceeds ~tens of thousands of tokens/run; optimize **cost-per-successful-task**, not per-token (reworked cheap extractions can cost more than one deep pass).
- **Guardrails to protect the ledger:** (1) reject extractions failing strict JSON-Schema, (2) escalate any field below a calibrated confidence threshold to the deep tier, (3) require deep/human verify before ledger entry. Plus: batch classification at intake (50% Batch-API discount), prompt caching as highest-leverage add-on, and keep high-volume extraction **off** Opus-class models (the Opus 4.7+ tokenizer change adds up to +35% tokens).

### RIB-008 · Claude Agent SDK readiness
- **Verdict: CONDITIONAL GO — build behind a feature flag.**
- **Subagent API is native & documented** (programmatic `agents` param, isolated parallel contexts, final-message-only return) → suitable for RF's bounded parallel document decomposition. **No native skills/resources API** exists → keep RF's plain-text skills injection; the only SDK-native path is filesystem `SKILL.md` + `setting_sources`. Migration is **low-cost/additive**, not a rewrite.
- **Governance fit is strong:** native `PreToolUse` hooks (deny/defer/ask/allow, deny wins) let RF's policy engine + secret-scanning block tool calls and audit every call. **Observability is a plus** (OTLP, per-model/per-step token breakdowns). **Billing favors migration** post-2026-06-15 (separate monthly credit pool for subscription auth).
- **Dominant risk = stability:** PyPI *Development Status 3 – Alpha*, pre-1.0 (`0.2.101`), near-daily releases, already shipped a breaking rebrand (`ClaudeCodeOptions → ClaudeAgentOptions`). → Pin a known-good version; gate behind a flag.

### RIB-009 · Agentic research-tool landscape (market scan)
- **Two of four tools had first-party evidence:** GPT Researcher and Perplexity Sonar Deep Research; **Gemini Deep Research and PaperQA2 are evidence gaps** in this run.
- **Adapter priority:** implement **GPT Researcher first** (Apache-2.0, self-hostable, ~$0.10 std / ~$0.40 deep, native Python API, LLM-agnostic via `OPENAI_BASE_URL`), **Perplexity second** (cleaner structured-JSON output but hosted-only, Tier-0 throttled to 5 RPM, and **~71% of run cost comes from volatile reasoning tokens**).

### RIB-010 · GPT Researcher vs PaperQA2 vs Claude Agent SDK as adapters
- **Three-way selection rule:** web/general + low-budget → **GPT Researcher** (~$0.40/run, 20+ sources, hybrid); scientific + accuracy-critical → **PaperQA2** (LitQA2 expert-level, passage-level `pqac-` citation keys, **lowest schema-mapping loss**); governed/budget-capped/RF-native → **Claude Agent SDK** (deterministic per-search/per-session metering, **cleanest governance fit**).
- **Multi-adapter fan-in** (GPT Researcher breadth + PaperQA2 depth) only pays off for high-stakes briefs mixing current-web and peer-reviewed evidence.
- **Caveat:** treat vendor recall/accuracy numbers as **cost-unaware self-reports**; AstaBench was the only neutral third-party benchmark in the evidence set — validate on a cost-controlled basis.

### Cross-run corroboration
The four runs reinforce each other: RIB-007's cheap-extract/deep-synthesize thesis is **independently realized** by GPT Researcher's 3-tier model scheme (RIB-009) and priced in RIB-010's adapter cost analysis; RIB-008's SDK governance hooks underpin RIB-010's "Claude SDK = best governance fit" verdict. The backlog's declared dependency (RIB-010 → RIB-009) was honored by seeding RIB-010's discovery with RIB-009's completed report.

---

## 4. Learnings (process & system)

1. **Concurrency ceiling is the one hard constraint.** Running **3 deep workflows in parallel** (~30+ simultaneous source-carder agents) tripped a **server-side rate limit** ("Server is temporarily limiting requests… not your usage limit"); **all** carders in RIB-008₁ and RIB-010₁ failed → 0 cards. **Sequential, one-deep-run-at-a-time** (≤~12 concurrent carders) succeeded cleanly every time. The pilot (9 concurrent) and all sequential runs were fine.
   - **Fix forward:** default to sequential deep runs, **or** add intra-workflow carder batching (e.g. 6 at a time) before re-enabling cross-run parallelism.
2. **The workflow is resilient to partial failure.** It proceeds with whatever source cards exist: RIB-007 (caught in the parallel burst) lost 9/12 carders to throttling but **salvaged 7 cards** (agents that wrote the file before the structured return failed) and still produced a verified bundle. Worth adding: a backoff-retry for failed carders to recover lost yield.
3. **Contract-first paid off.** The upfront smoke test that pinned the exact authoring contract (source card = the evidence injection point; `[claim:clm_NNN]` is the *only* accepted citation; inference claims need `inference_basis.from_claims`) meant **zero verify fix-loops across 4 runs** and **zero** enrichment fallbacks. Getting the contract right beforehand was the highest-leverage decision.
4. **`args` crosses the Workflow tool boundary as a JSON string** — needed a `typeof args === 'string' → JSON.parse` guard (now baked into the reusable script). First launch misfired instantly (`missing run_id`) before this fix.
5. **Cost profile:** ~1.2M tokens per verified research bundle; the throttled parallel attempts added ~22% waste. Sequential-by-default would have avoided essentially all of it.
6. **Writebacks degrade gracefully offline** — all 4 runs emitted file candidates (`meatywiki/skillbom/ccdash`), but the live HTTP targets are unreachable (`rf doctor`: arc/intenttree unreachable). **Live writeback remains unvalidated** (consistent with prior project memory).

---

## 5. Recommendations / next steps

- **Process:** run the remaining backlog pillars **one deep workflow at a time**, or implement carder batching, to avoid the rate-limit waste.
- **Promote reusable outputs** now captured in each run's `skillbom_candidate.md`: `two-tier-split-breakeven-model`, `per-stage-cost-quality-table`, `cheap-tier-escalation-rules` (RIB-007); `claude-agent-sdk-readiness-verdict`, `sdk-migration-cost-note` (RIB-008); `agentic-research-tool-capability-matrix`, `real-mode-adapter-priority-list` (RIB-009); `adapter-selection-rules`, `extraction-backbone-comparison-matrix` (RIB-010).
- **Act on the convergent finding:** RIB-007/009/010 all point to **GPT Researcher as the first real-mode adapter** and a **hybrid cheap-extract + deep-escalate** routing policy — strong candidates to implement next.
- **Close the evidence gaps:** a follow-up run dedicated to Gemini Deep Research and PaperQA2 first-party sources would complete the RIB-009 matrix.
- **Validate writebacks live** against a real MeatyWiki / CCDash / IntentTree, the one remaining untested seam.
- **Commit** the four evidence bundles + this AAR as the durable record of the first full RF runs.

---

*Generated from the four verified evidence bundles under `runs/`. Every statistic here traces to a run's `evidence_bundle.yaml` / `reviews/verification.yaml`; every research finding traces to that run's claim ledger.*
