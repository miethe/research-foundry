---
title: "Consolidated AAR — Second RF Batch: HIGH-Priority Roots Wave (10 dependency-free items)"
type: after_action_report
created: 2026-06-14
author: Nick Miethe (orchestrated by Claude Opus, Path-B research swarm)
status: final
scope: RIB-002, RIB-018, RIB-024, RIB-025, RIB-026, RIB-037, RIB-042, RIB-045, RIB-051, RIB-053 (priority=high, dependency-free roots)
related:
  - backlog/research_idea_backlog.yaml
  - docs/projects/research-foundry/aars/swarm-orchestration-cost-runs-aar-2026-06-13.md
  - .claude/skills/research-foundry-swarm/SPEC.md
  - .claude/workflows/rf-run-execute.js
  - runs/rf_run_20260614_what_does_the_empirical_literature_say/
  - runs/rf_run_20260614_what_published_security_frameworks_threat_models/
  - runs/rf_run_20260614_what_patterns_file_watch_hooks_post/
  - runs/rf_run_20260614_what_components_schemas_agent_roles_and/
  - runs/rf_run_20260614_what_architectures_define_an_agentic_origination/
  - runs/rf_run_20260614_what_are_the_documented_trade_offs/
  - runs/rf_run_20260614_what_methods_exist_for_automatically_scoring/
  - runs/rf_run_20260614_do_token_logprob_distributions_provide_more/
  - runs/rf_run_20260614_what_governance_criteria_evaluation_frameworks_a/
  - runs/rf_run_20260614_what_pipeline_architecture_best_ingests_outputs/
---

# Consolidated AAR — Second RF Batch: HIGH-Priority Roots Wave

**Scope:** All ten `priority: high` backlog ideas that have **no upstream dependency** — the "roots wave." This batch followed the first full RF batch (Swarm Orchestration & Cost Routing pillar, RIB-007/008/009/010) and was deliberately stopped at the dependency-free roots before the 8 dependent items, per the operator's "roots wave only, then reassess" directive.
**Date:** 2026-06-14 · **Orchestration:** Opus + Dynamic Workflow (one per run, strictly sequential) · **Mode:** Path B (Claude-orchestrated discovery, RF governance spine + deterministic tail) · **Posture:** `--sensitivity personal`, default writeback targets (meatywiki, skillmeat, ccdash), `--no-require-review`; live writeback validation deferred (file candidates only).

This batch is the **first multi-pillar production run** of the RF pipeline and the **first to validate the prior AAR's single-deep-run-at-a-time recommendation at scale** (10 sequential runs, zero rate-limit events).

---

## 1. Run-by-run results

| Ref | Run ID (`rf_run_20260614_…`) | Topic | Artifact (depth) | Sources | Claims (sup / inf / spec) | Unsup | Verify | Bundle |
|---|---|---|---|---|---|---|---|---|
| **RIB-002** | `what_does_the_empirical_literature_say` | Hallucination mitigation & claim-ledger | literature_review (deep) | 12 | **95** (75 / 18 / 2) | 0 | ✅ exit 0 | verified |
| **RIB-018** | `what_published_security_frameworks_threat_models` | Cross-profile API-key isolation | technical_memo (deep) | 12 | **102** (82 / 18 / 2) | 0 | ✅ exit 0 | verified |
| **RIB-024** | `what_patterns_file_watch_hooks_post` | Broker-less local event patterns | technical_memo (deep) | 12 | **90** (71 / 17 / 2) | 0 | ✅ exit 0 | verified |
| **RIB-025** | `what_components_schemas_agent_roles_and` | Minimum viable research-swarm arch | report (deep) | 12 | **94** (77 / 14 / 3) | 0 | ✅ exit 0 | verified |
| **RIB-026** | `what_architectures_define_an_agentic_origination` | Agentic origination/intent-routing | technical_memo (deep) | 12 | **97** (77 / 18 / 2) | 0 | ✅ exit 0 | verified |
| **RIB-037** | `what_are_the_documented_trade_offs` | File-first vs DB-first KBs | technical_memo (std) | 9 | **64** (52 / 10 / 2) | 0 | ✅ exit 0 | verified |
| **RIB-042** | `what_methods_exist_for_automatically_scoring` | Quality scoring / `quality_score` | report (deep) | 12 | **98** (78 / 18 / 2) | 0 | ✅ exit 0 | verified |
| **RIB-045** | `do_token_logprob_distributions_provide_more` | Logprob vs self-report calibration | technical_memo (deep) | 12 | **91** (73 / 16 / 2) | 0 | ✅ exit 0 | verified |
| **RIB-051** | `what_governance_criteria_evaluation_frameworks_a` | SkillBOM promotion governance | technical_memo (std) | 9 | **66** (54 / 9 / 3) | 0 | ✅ exit 0 | verified |
| **RIB-053** | `what_pipeline_architecture_best_ingests_outputs` | Unified research-capture ingestion | technical_memo (deep) | 12 | **96** (78 / 16 / 2) | 0 | ✅ exit 0 | verified |
| **TOTAL** | **10 runs** | — | 8 deep / 2 std | **114** | **893** (717 / 154 / 22) | **0** | **10 / 10** | **10 / 10** |

Every run also emitted all three writeback candidates (`meatywiki_writeback.md`, `skillbom_candidate.md`, `ccdash_event.yaml`) — 30 candidate files. **0 unsupported and 0 contradicted claims** across all 893 claims; 80.3% supported, 17.2% labeled inference, 2.5% labeled speculation.

### Compute & cost (subagent tokens, wall-clock)

Six of ten runs were measured directly via workflow completion telemetry (the other four completed before a context compaction and were not separately metered — they are deep runs and fall in the same band):

| Run | Agents | Subagent tokens | Duration |
|---|---|---|---|
| RIB-026 | 23 | 1.33M | 16.2 min |
| RIB-037 | 22 | 1.16M | 15.3 min |
| RIB-042 | 23 | 1.25M | 19.2 min |
| RIB-045 | 23 | 1.30M | 19.3 min |
| RIB-051 | 19 | 1.01M | 16.8 min |
| RIB-053 | 22 | 1.24M | 17.1 min |
| **6 measured** | **132** | **~7.30M** | ~104 min active |
| RIB-002/018/024/025 (deep, est. ~1.2M ea.) | ~88 | ~4.8M | ~64 min |
| Findings-digest agent + RIB-018 repair | ~2 | ~0.2M | — |
| **Roots-wave grand total (est.)** | **~222** | **~12.3M** | ~3 h active |

≈ **1.22M subagent tokens per verified bundle** — identical to the first batch's ~1.2M, confirming a stable per-bundle cost. Std-depth runs (RIB-037, RIB-051) ran ~1.0–1.16M / 19 agents; deep runs ~1.24–1.33M / 22–23 agents. **No throttle waste this batch** (vs ~22% in batch 1) because every run was strictly sequential.

---

## 2. Effectiveness — did the approach work?

**Yes — cleanly, at 10/10.** The roots wave reproduced batch 1's result on a far more diverse question set (security, event architecture, calibration, governance, ingestion, KB storage) and a mix of self-referential (RF-architecture) and external-evidence questions.

- **The claim-ledger gate held perfectly again.** 893/893 claims resolve to a source card or carry an `inference`/`speculation` label with populated basis. **Zero** unsupported or contradicted claims reached any report; **zero** runs needed the deterministic-fallback synthesizer (enrichment survived verification 10/10). Only RIB-037 took a single in-loop verify retry (`verify_tries:1`, self-corrected); the other nine passed on the first attempt.
- **Real evidence at scale.** 114 source cards cite primary sources — arXiv/ACL papers (SAFE, FActScore, ALCE, Kadavath, Tian, Xiong, Guo, RAGChecker), vendor API docs (OpenAI logprobs, Gemini grounding, Perplexity Sonar, Vault, MLflow/Langfuse registries), standards (OWASP LLM Top 10, NIST AI RMF, ISO 42001, W3C PROV, C2PA, RFC 3986), and benchmarks (Vectara HHEM, DeepResearch Bench).
- **Self-referential rigor.** RIB-025 (RF's own minimum-viable architecture) and RIB-042 (RF's own `quality_score`) audited RF's design *using RF's own traceability discipline* and produced concrete, evidence-anchored verdicts — the swarm scored itself without special-casing.
- **Structured deliverables.** Every report is a real memo/report/literature-review with exec summary, comparison matrices, derivations, and decision rules — not a flat claim dump — while satisfying the per-line `[claim:clm_NNN]` gate end-to-end.

---

## 3. Findings — the actual research output

### RIB-002 · Hallucination mitigation & claim-ledger
- **Bottom line:** No LLM eliminates unsupported claims; RF should keep a **mandatory post-hoc atomic-claim verifier** on material claims atop pre-hoc grounded generation — a claim-ledger + verifier dominates RAG-alone on per-claim support.
- Rates vary wildly by unit (Vectara best-case 1.8% summary hallucination; median model ~25% fabrication; ALCE ~50% of ELI5 statements unsupported; DRBench 3–13% fabricated URLs). **Model selection matters more than verifier tuning** (>20× fabrication spread).
- The ledger *is* the SAFE/FacTool decompose-then-verify pattern (72% human agreement, >20× cost advantage); verifier overhead is bounded single-digit-to-~25%. **Cap context near 32K** — fabrication triples by 128K and exceeds 10% for all models at 200K. Constitutional AI is orthogonal (policy-gating, no traceability).

### RIB-018 · Cross-profile API-key isolation
- **Bottom line:** RF's four profiles are a **file-first analogue of Vault namespaces** but cannot inherit server-backed revocation; enforce isolation at **load time** (one-profile-per-process env scoping + policy gate), with rotation cadence compensating for missing TTL expiry.
- Six leakage vectors (env-var bleed, subagent inheritance, log/telemetry capture, confused-deputy echo, scope creep, token passthrough) cluster into ambient-inheritance / observability-capture / temporal-drift families.
- Four tightenings: **R1** one-profile-per-process minimal env; **R2** key fingerprinting + profile-tagged telemetry; **R3** file-first revocation/rotation runbook + key manifest; **R4** human gate on cross-profile elevation. `offline_only` is the strongest guarantee (immune to all six) and should be default. Structural gap = long-lived static `.env` keys vs Vault leases / MCP short-lived tokens / SPIFFE SVIDs.

### RIB-024 · Broker-less local event patterns
- **Bottom line:** Seam→pattern mapping — **research→vault = git post-commit/post-merge**, **vault→graph = file-watch (watchdog/chokidar) + reconciliation rescan**, **telemetry→governance = SSE with Last-Event-ID resume**; an append-only event log is the cross-cutting reconciliation substrate.
- No broker-less primitive gives exactly-once → every consumer MUST be idempotent (content-hash / commit-SHA dedup). Use **lefthook** over pre-commit (single Go binary, parallel). SSE is one-way — unsuitable for write-path seams.
- Minimal broker justified only when producers/consumers stop sharing a filesystem OR recurring `IN_Q_OVERFLOW`/watch-limit exhaustion; **git `post-receive` on a shared remote is the lowest-cost escalation** before a true broker.

### RIB-025 · Minimum viable research-swarm architecture
- **Bottom line:** MUST-have loop = capture→extract-claims-into-cards→map-to-ledger→synthesize→verify-gate with planner/researcher/synthesizer/citation roles; standalone red-team, parallel fan-out, and writeback targets are CAN-defer.
- Three MUST-have schemas (source-card, claim-ledger, report); RF's four-way labeling (supported/inference/speculation/unresolved) is the **strongest traceability among all five surveyed systems** (GPT Researcher, PaperQA2, STORM, Anthropic, OpenAI Deep Research).
- **Biggest unjustified MVP gap = absent context-persistence/memory** (Anthropic's LeadResearcher persists its plan to survive the 200K window). Cheap-extract/expensive-synthesize tiering validated by Anthropic's 90.2% Opus+Sonnet lift. Reuse PaperQA2 (scientific) / GPT Researcher (open web, ~$0.4/run) rather than reimplement.

### RIB-026 · Agentic origination / intent-routing layer
- **Bottom line:** **Hybrid cascade** — deterministic rule table → embedding classifier (Semantic Router) for the residue → LLM intent extraction only as a low-confidence fallback — preserving rule-based cost-predictability while reserving the expensive LLM decision for the ambiguous minority.
- Three-stage pipeline: intent ingestion/normalization → route/dispatch decision → typed execution package. Best prior-art fits: Semantic Router (decision node), OpenAI Agents SDK handoff (typed-packet dispatch), LiteLLM Router (cost-cap layer).
- Use a **central-supervisor topology, not a swarm**, for a single auditable cost-cap/telemetry/validation point; Bedrock's 10-collaborator cap signals a two-level router once routes reach the low tens. Bind model-profile selection at the routing boundary (budget as admission filter).

### RIB-037 · File-first vs DB-first knowledge bases
- **Bottom line:** Keep **Markdown+YAML under Git as single source of truth** + a **derived, disposable SQLite/Datasette index** (git-history pattern); add a PostgreSQL/MVCC write tier only if concurrent agent writes exceed the millisecond turn-taking window.
- File-first and embedded DBs share the **single-writer ceiling**; only client/server MVCC scales (adequate below ~100K hits/day). Git content-addressing (Merkle SHA chaining) gives **stronger tamper-evidence than a DB audit trail**; the hybrid index is the strongest recovery posture (deterministically rebuildable).
- **Multi-agent swarms are the likely first workload to breach the single-writer ceiling** — directly relevant to RF/MeatyWiki concurrency.

### RIB-042 · Quality scoring / `quality_score` formula
- **Bottom line:** Deterministic composite **Q = 0.45·support_rate + 0.20·(1−unsupported_rate) + 0.15·source_diversity + 0.10·verification_passed + 0.10·(1−normalized_rework)**, dominated by claim support rate.
- Add one new emitted signal **`distinct_source_domains`** (source_diversity = min(1, distinct/6)); all other inputs already in `ccdash_event`. Emit **both** a per-dimension vector and a scalar+tier; hard-floor at 0.5 on verification failure; keep cost-per-claim and LLM-judge coherence OUT of the deterministic score. RAGChecker (Pearson 61.93) is the closest analogue.
- Guard three Goodhart attacks (source padding, claim splitting, citation stuffing) via distinct-domain counting + saturation + per-source claim-concentration cap; add a CoT trace-audit tripwire (72% of reward-hacks leave a rationale).

### RIB-045 · Logprob vs self-reported confidence calibration
- **Bottom line:** Use **single-call logprob sequence probability (MSP)** as the always-on accept/route signal; escalate to a logprob+self-report or logprob+consistency (CoCoA) **hybrid only for the borderline band**; never rely on single-sample verbalized confidence alone.
- Small scale: logprobs cut ECE ~2–3× (GSM8K 0.104 MSP vs 0.335 single-sample VCE). Large ≥70B models reach VCE ECE ~0.1 (on par with MSP). **CoCoA hybrid best overall** (ECE 0.062–0.081, AUROC ≤0.844). Single-call logprobs ≈ **near-zero billed-token overhead**; hybrids are ~M-fold cost → reserve for escalation band.
- Portability: logprobs exposed by OpenAI, Gemini/Vertex, vLLM, llama.cpp — **NOT Ollama's chat endpoint**; needs a per-provider adapter + self-report fallback; set abstain thresholds via risk-coverage, recalibrate with temperature scaling on model/prompt change.

### RIB-051 · SkillBOM promotion governance
- **Bottom line:** Adopt the **artifact-immutable / pointer-mutable** pattern from six registries — candidate file immutable, promotion is a movable pointer state (candidate→evaluated→human-reviewed→promoted) — since passing automated gates is **necessary but not sufficient** without an attributed human Approve.
- RF's single `report_reviewed` boolean conflates automated and human checks; add four fields: **approval_status enum, reviewer-identity, append-only transitions log, demotion/deprecation transition.**
- Proposed thresholds: candidate→evaluated = verifier+governance pass & rework=0; evaluated→human-reviewed = quality_score ≥0.8 across ≥2 runs; human-reviewed→promoted = human Approve with zero open high-sev failure modes. RBAC-protect the promoted pointer; guard reuse-of-latest and unguarded-pointer-flip.

### RIB-053 · Unified research-capture ingestion pipeline
- **Bottom line:** Three-stage pipe (**per-tool export adapter → single intermediate normalized record → idempotent RF intake stage**), centered on the **(span→source) citation tuple** that OpenAI annotations, Gemini `groundingSupports`, and Perplexity `search_results` all reduce to.
- Normalized record = `{span:{start,end,unit}, source:{url,title,published_at,…}, relation, confidence}`; **unit='char' for OpenAI/Perplexity, 'byte' for Gemini** (mixing units mis-slices spans). Attribution fidelity: OpenAI & Gemini highest (span offsets), Perplexity high (list-level), **NotebookLM lowest (no REST API)**.
- Keep normalization in a **standalone RF intake stage, not a MeatyWiki connector**; dedup on resolved-URL + publication-date (resolve Gemini `vertexaisearch` redirects first); build OpenAI + Perplexity adapters first, Gemini grounding second, defer NotebookLM.

### Cross-run convergence
Several roots reinforce each other and the prior batch: **RIB-002 + RIB-042** both land on atomic-claim support rate as the dominant quality signal (RIB-042's formula operationalizes RIB-002's verifier thesis). **RIB-025 + RIB-026 + RIB-037** converge on the same architectural spine — central-supervisor orchestration (026), files-as-truth + derived index (037), and a minimal MUST-have loop with deferred memory (025). **RIB-045 + RIB-042** share the calibration/threshold machinery (logprob confidence feeds gate decisions). **RIB-018 + RIB-051** both call for explicit human-in-the-loop gates and attributed/audited state transitions. The cheap-extract/deep-synthesize thesis from batch 1 (RIB-007) is re-validated by RIB-025 and RIB-002.

---

## 4. Learnings (process & system)

1. **Sequential-by-default eliminated rate-limit waste.** Acting on batch 1's #1 recommendation, all 10 runs launched strictly one-deep-workflow-at-a-time. **Zero throttle events** across ~222 agents (vs ~22% wasted tokens in batch 1's parallel attempts). The constraint holds: the danger is **concurrent source-carders**, not concurrent workflows per se.
2. **The bundle-phase verify self-report is NOT trustworthy — always re-run authoritative `rf verify`.** Two distinct manifestations this batch:
   - **RIB-018 false-pass (caught & fixed):** the workflow reported `verify_exit:0, bundle_ok:true`, but an authoritative `rf verify` re-run failed (exit 2) on `inferences_have_basis` + `inference_is_labeled` — the Phase-8 bundle-audit agent had appended an inference claim (`clm_inf18`) with empty `from_claims` and no **Inference:** label **after** the verify loop. Fixed by populating the basis + adding the label, then re-verify/re-bundle/re-writeback.
   - **Process now enforced:** after **every** run, ignore the workflow's `bundle_ok` and re-run `rf verify <run_id>` as the authoritative checkpoint; only exit 0 counts. All 10 final states were confirmed green this way.
3. **The Phase-8 tail can be interrupted (compaction / kill) leaving a verify-clean run without its bundle/writebacks.** RIB-026's `evidence_bundle.yaml` and `writebacks/` were missing on inspection mid-batch; I completed the tail manually (`rf bundle` + `rf writeback`). It later emerged the workflow was still *running* its tail — the manual run **raced** the workflow. Both are deterministic regenerations, so the final state was clean and **produced zero duplicate artifacts** (idempotent: writeback files overwrite, run_index/skillbom_index unchanged). **Lesson: wait for the actual completion notification before declaring a run done or manually finishing its tail** — "past synthesis" is not "complete."
4. **Carder-phase completion ≠ workflow completion.** Launching the next swarm while a prior workflow's *single audit agent* is still finishing is safe (no carder concurrency), but the cleaner rule is to gate on the completion notification regardless.
5. **Cost profile is stable and predictable:** ~1.22M subagent tokens / verified bundle, 19–23 agents, 15–20 min wall-clock; std-depth shaves ~15–20% off both. A full HIGH-priority pillar of ~10 deep runs ≈ ~12M tokens / ~3 h of active swarm time, run sequentially.
6. **Writebacks still degrade gracefully offline** — all 10 emitted the three file candidates; live HTTP targets (arc/intenttree) remain unreachable and **live writeback is still unvalidated** (per standing project memory; deferred by operator decision this batch).

---

## 5. Recommendations / next steps

- **Proceed to the dependent wave (8 items), now unblocked.** RIB-001, RIB-003, RIB-017, RIB-033, RIB-034, RIB-035, RIB-041, RIB-047 depend on roots completed here (notably RIB-002, 018, 037, 042, 045, 051). Seed each dependent run's discovery with the relevant root report(s) — as batch 1 did for RIB-010→RIB-009. Continue sequential, one deep run at a time.
- **Act on the directly-actionable RF design outputs** surfaced by this batch:
  - Implement the **`quality_score` formula** (RIB-042) — it draws only on signals RF already emits plus one new `distinct_source_domains`; this finally fills the `quality_score: pending` field.
  - Add the **SkillBOM lifecycle fields** (RIB-051): `approval_status` enum, reviewer identity, append-only transitions log, demotion transition — the current single `report_reviewed` boolean is insufficient.
  - Apply the **four key-isolation tightenings** (RIB-018), starting with one-profile-per-process env scoping + profile-tagged telemetry, and make `offline_only` the default.
  - Close the **context-persistence/memory gap** (RIB-025) — the one unjustified MVP gap vs prior art.
- **Promote reusable outputs** now captured across the 30 `skillbom_candidate.md` files (e.g. `ccdash-quality-score-formula`, `run-quality-telemetry-checklist`, `promotion_gate_matrix`, `skillbom_lifecycle_playbook`, `routing-policy-decision-matrix`, `origination-layer-reference-architecture`, `seam-integration-pattern-matrix`, `confidence-calibration-recipe`, `rf-mvp-architecture-spec`) — but gate them through the very promotion governance RIB-051 just specified (candidate → evaluated → human-reviewed → promoted), not direct reuse.
- **Cosmetic sweep:** end-of-batch pass for enrichment-mangled apostrophes (flagged on RIB-018; verify across all 10 reports) — typographic only, no claim-integrity impact.
- **Validate writebacks live** against a real MeatyWiki / CCDash / IntentTree — still the one untested seam.
- **Commit** the ten evidence bundles + this AAR as the durable record of the roots wave.

---

*Generated from the ten verified evidence bundles under `runs/rf_run_20260614_*`. Every statistic traces to a run's `evidence_bundle.yaml` / `reviews/verification.yaml`; every research finding traces to that run's claim ledger. Run-by-run claim counts and verify status independently re-confirmed via authoritative `rf verify` after each run, not taken from workflow self-reports (see §4.2).*

---

## 6. Dependent wave

The eight HIGH-priority items that depend on roots completed in §1: RIB-001, 003, 017, 033, 034, 035, 041, 047. Run sequentially (one deep swarm at a time, rate-limit constraint), authoritative `rf verify` after each. **Status: COMPLETE — 8/8 verified green.**

### 6.1 Setup (applies to all 8)

- **Descriptor authoring** — all 8 run descriptors drafted in a single parallel authoring workflow (8 contract-drafting agents, JSON-schema-validated), each grounded on the verbatim backlog entry + its seed root report(s) + the proven root descriptor format. 513K tokens, 91 s.
- **Scaffolding** — each run created via `rf capture → rf triage → rf plan` (`--depth deep --audience technical --max-cost <hint> --freshness <hint>`). Gotcha recorded for next time: **the run_id slug derives from `--title`, not the question**, so the pre-chosen question-derived run_ids had to be reconciled against the real ones `rf plan` assigns. RIB-034/035 seed paths were repointed to RIB-033's *real* run dir after scaffolding (they seed on its report).
- **Dependency order** — RIB-033 (embedding/vector-store) must run before RIB-034 (hybrid BM25/FTS5) and RIB-035 (entity consolidation), which seed on its report. All others depend only on completed roots.

| RIB | run_id (`rf_run_20260614_…`) | seeds | cost / fresh |
|-----|------------------------------|-------|--------------|
| 001 | `claim_segmentation_and_claim_to_source` | RIB-002, RIB-045 | $7 / 180d |
| 003 | `contradiction_detection_across_heterogeneous_sou` | RIB-002 | $7 / 180d |
| 017 | `sensitivity_aware_ai_routing_tier_policy` | RIB-018 | $7 / 365d |
| 033 | `embedding_model_vector_store_strategy_for` | RIB-037 | $7 / 180d |
| 034 | `hybrid_bm25_vector_and_fts5_ranking` | RIB-033 (in-wave) | $6 / 180d |
| 035 | `semantic_entity_consolidation_and_auto_merge` | RIB-033 (in-wave) | $7 / 180d |
| 041 | `determinism_ci_cost_control_for_agentic` | RIB-042 | $7 / 180d |
| 047 | `closed_loop_telemetry_to_artifact_feedback` | RIB-051 | $8 / 180d |

### 6.2 Results (authoritative `rf verify` re-confirmed per run — never the workflow's `bundle_ok`)

| RIB | artifact | src | claims (S/I/Spec) | unsupp/contra | verify | fixes | tokens | agents | wall |
|-----|----------|-----|-------------------|---------------|--------|-------|--------|--------|------|
| 001 | technical_memo (deep) | 12 | 96 (79 / 16 / 1) | 0 / 0 | **exit 0 ✓** | 0 | 1.42M | 23 | ~21 m |
| 003 | technical_memo (deep) | 12 | 102 (84 / 16 / 2) | 0 / 0 | **exit 0 ✓** | 0 | 1.37M | 23 | ~18 m |
| 017 | technical_memo (deep) | 12 | 94 (75 / 17 / 2) | 0 / 0 | **exit 0 ✓** | 0 (1 in-audit tag) | 1.38M | 23 | ~19 m |
| 033 | technical_memo (deep) | 12 | 90 (72 / 16 / 2) | 0 / 0 | **exit 0 ✓** | 0 (clean audit) | 1.22M | 23 | ~17 m |
| 034 | technical_memo (deep) | 12 | 91 (74 / 14 / 3) | 0 / 0 | **exit 0 ✓** | 0 (clean audit) | 1.24M | 23 | ~22 m |
| 035 | technical_memo (deep) | 12 | 102 (83 / 17 / 2) | 0 / 0 | **exit 0 ✓** | 0 (clean audit) | 1.28M | 23 | ~18 m |
| 041 | technical_memo (deep) | 12 | 101 (80 / 19 / 2) | 0 / 0 | **exit 0 ✓** | 1 (audit-added `clm_inf18`) | 1.42M | 25 | ~21 m |
| 047 | literature_review (deep) | 12 | 98 (79 / 17 / 2) | 0 / 0 | **exit 0 ✓** | 0 (clean audit) | 1.32M | 23 | ~21 m |

> RIB-033 failed once at discovery on 2026-06-14 — all 5 angle agents hit an account monthly-spend-limit error (`no sources discovered`, ~210K tokens, 33 s, zero artifacts). Re-launched 2026-06-15 after the cap cleared; succeeded clean on the first retry.

### 6.3 Per-run findings

- **RIB-001 · Claim segmentation & claim-to-source alignment** — operationalizes the upstream mechanic the roots' RIB-002 only surveyed. Draws on FActScore / VeriScore / Claimify decomposition, ALCE / LongCite / MiniCheck / AlignScore alignment precision-recall, the cheap-extract vs deep-synthesize tier split, and a concrete *minimal* claim-ledger field set (per-source `entailment_score`, `splitter_model_id` / `aligner_model_id` provenance, `decontextualized_text`, `alignment_method`, `escalation_reason`) plus rules for routing ambiguous claims to `mixed` / human review. Reusables: `claim-segmentation-prompt-skill`, `claim-source-alignment-evaluation-rubric`.
- **RIB-003 · Contradiction detection across heterogeneous sources** — the consistency layer RIB-002 didn't cover. Draws on NLI/DocNLI/TRUE/SummaC and cheap consistency scorers (MiniCheck, AlignScore) with the key finding that **contradiction-class recall sits well below entailment accuracy**; GraphRAG-style LLM-KG conflict/stale/orphan flagging; source-heterogeneity normalization (atomic decomposition + decontextualization + unit canonicalization + coref, with PDF-parse error propagation); a genuine-vs-apparent contradiction taxonomy with encodable fields (`valid_time`, `scope`, `measurement_basis`, `population`); and a cheap-pairwise-prefilter → expensive-LLM-arbiter split. Reusables: `contradiction-detection-rubric`, `contradiction-log-schema-sketch`.
- **RIB-017 · Sensitivity-aware routing & tier policy** — operationalizes RIB-018's key-isolation threat model into writeback governance. Maps NIST (800-60/FIPS-199, 800-171 CUI) and ISO/IEC 27001:2022 A.5.12/A.5.13 + Purview labels onto RF's three tiers; enforcement at the routing boundary via policy-as-code (OPA/Rego, Cedar) fronting LLM gateways (LiteLLM, Portkey, Envoy `ext_authz`) with default-deny / fail-closed and ABAC-bound labels; a non-repudiable decision record (policy version, evaluated label, subject/profile, target, verdict, timestamp, request hash) per NIST 800-92 / hash-chained logs / OPA decision logs; and a **sensitivity-tier × writeback-target allow/deny matrix** where local-vs-networked topology of each sink (ARC, IntentTree, MeatyWiki, SkillMeat, CCDash) governs the default. Reusables: `sensitivity-tier-writeback-policy-matrix`, `routing-boundary-enforcement-checklist`.
- **RIB-033 · Embedding model + vector-store strategy (1K–100K file-first vault)** — the retrieval-substrate root for the storage sub-wave (seeds RIB-034 and RIB-035). Default stack: **BGE-M3 embeddings (1024-dim dense, 8192-token context) truncated to 512 dims, stored in sqlite-vec** — one dependency-free SQLite file beside the vault, trivially backed up and fully rebuildable from Markdown — **migrating only the dense index to pgvector HNSW** (m=16, ef_construction=64, ef_search=40) if interactive latency degrades near the 100K ceiling. Key evidence: choosing fully local embeddings over OpenAI `text-embedding-3-small` costs only ~0–2 aggregate MTEB points (3-small 62.3%, 3-large 64.6%), small enough that privacy/offline benefits dominate for a personal vault; nomic-embed Matryoshka quantifies the truncation tax (768→512 dims ≈ 0.32 MTEB points, →256 ≈ 1.24); sqlite-vec ≤ v0.1.9 is brute-force only (ANN via DiskANN landing through the v0.1.10-alpha line), bounding the brute-force ceiling; pgvector 0.7+ halfvec/binary quantization and `dimensions`-param shortening give the migration headroom. Reusables: `embedding-vectorstore-decision-matrix`, `vault-retrieval-scaling-thresholds`.
- **RIB-034 · Hybrid BM25/FTS5 ranking for Markdown KBs** — extends RIB-033's storage substrate with the *ranking* layer. Per-tier architecture: **1K = BM25-only (FTS5)** with frontmatter/heading column weighting; **10K = BM25 + cross-encoder reranking** of the top ~100–200 lexical candidates (skip the vector index); **50K = full BM25 + dense-vector hybrid fused by RRF, then reranked**. The lexical-only break point sits at the *upper edge of the 10K tier*, not 1K — grounded in a 7,318-doc corpus where sparse BM25 beat dense `text-embedding-3-large` on Recall@5 (0.644 vs 0.587), and the BM25 failure mode is shown to be query-type-specific (hybrid's largest gain, +8.1pp Recall@5, was on the table-heavy TAT-DQA subset), so prose/heading-dense Markdown degrades later. **A cross-encoder reranker is the highest-ROI single upgrade at every affordable tier** (+17.4% Recall@5, 0.695→0.816; +39.7% relative MRR@3) and the dominant driver of Anthropic Contextual Retrieval's 67% failure-rate reduction. **RRF with k=60 is the default fusion** (unsupervised, training-free, score-scale-agnostic, beat CombMNZ/Condorcet by 4–5% MAP); weighted-linear only if query routing shows one signal systematically stronger. Concrete FTS5 recipe (column-weighted `bm25()`, tokenizer choice, contentless/external-content tables, incremental-reindex triggers under Git churn) is specified. Reusables: `fts5-markdown-indexing-recipe`, `hybrid-search-fusion-decision-rubric`.
- **RIB-035 · Semantic entity consolidation & auto-merge thresholds** — closes the RIB-033 storage sub-wave by specifying *dedup/merge* over the indexed corpus. Key finding: pairwise entity-matching is near a practical ceiling (best LLMs ~98–99% F1), so the marginal payoff for a file-first vault is in **blocking, clustering, and the human-review loop, not a better pair scorer**. Recommended **three-method stack**: a zero-shot retrieve-and-rerank text matcher (EnsembleLink-style) as primary scorer, **Fellegi-Sunter (Splink)** as an unsupervised probabilistic backstop, and an LLM re-ranker (GPT-4o/ComEM-style) reserved for the review band — needs no labeled training data. Supervised PLM matchers (Ditto/RoBERTa) are *rejected* because they collapse 22–61% F1 on unseen entities while GPT-4 zero-shot stays robust (+34% F1), and a personal vault's vocabulary drifts continuously. **Confidence bands** on a blended 0–1 scale: **auto-merge ≥ 0.95, human review 0.80–0.95, ignore < 0.80** — precision-biased because a wrong auto-merge silently destroys a unique note. Reversible-merge primitive: **Git content-addressing already supplies it** — each merge is one atomic commit, content-SHA naming makes pre-merge state recoverable, `git revert` is the undo, so no bespoke transaction log is needed; plus redirect-stub + backlink-rewrite mechanics and LSH/ANN sub-quadratic blocking to 100K. Reusables: `entity-merge-threshold-bands`, `reversible-merge-design-checklist`.
- **RIB-041 · Determinism & CI cost-control for agentic eval harnesses** — directly operationalizes how RF would gate *its own swarm* in CI. Central finding from the two hosted models RF actually calls: **neither offers gateable reproducibility** — the Anthropic Messages API exposes only temperature/top_p/top_k (no seed) and warns that even temperature 0.0 is *not* fully deterministic; OpenAI's seed is only "(mostly) deterministic," never bit-for-bit. So **output-text-equality assertions are the wrong gating primitive**. Recommended **two-leg split** (the minimum viable config): a **deterministic leg** — stubbed/cassette-backed tool calls (FakeListLLM / VCR / pytest-recording) + **tool-sequence/trajectory assertions**, byte-deterministic and network-free, gating *every PR at zero API spend* — and a **stochastic leg** — live model + rubric/model-graded judge — that runs nightly/on-demand and never blocks a PR on a single live failure. Maps onto RF's existing primitives (the deterministic-default execution path, `rf verify` as the CI-gateable claim signal, `run_trace.jsonl` + `ccdash_event` metrics as trajectory/cost telemetry, the opt-in `claude_agent_sdk` adapter as the sole stochastic leg) and names the gaps (recorded carder/tool fixtures, a trajectory assertion over `run_trace.jsonl`, per-run cost ceilings). Reusables: `agentic-eval-ci-gating-playbook`, `trajectory-assertion-checklist`.
- **RIB-047 · Closed-loop telemetry → artifact feedback** — the capstone that closes the wave by specifying how RF's own telemetry should (and should not) drive artifact-version improvement. Splits telemetry into **leading signals** (per-trace cost/latency/token attribution, tool-call provenance, activation-based and chain-length reward-hack onset) that should only *prioritize which artifact to revise*, and **lagging signals** (quality-gate pass rates, human-edit/rework counts, regression outcomes) that should *gate promotion* — never the reverse. Key findings: **human-edit/rework counts are the highest-value lagging signal** because each reviewed failure converts losslessly into a permanent regression-test row *and* calibrates the cheaper LLM-judge (one edit improves both the artifact and the measurement instrument); **environmental hardening is the single highest-leverage governance control** (cut agent reward-hacking exploit rates 6.5% → 0.8%, 87.7% relative, with task-success statistically unchanged — harden the grading/verification environment *before* any signal-driven auto-revision); and **champion-challenger / holdout is the governance structure best matched to RF's immutable-artifact + mutable-pointer model** (champion frozen as control, challenger judged on held-out traffic, pointer flips only on a confidence-qualified win, so rollback is a single pointer move). Degradation modes are named explicitly — Goodhart / reward-model overoptimization, reward-hacking-induced emergent misalignment, and the insufficiency of chat-style RLHF evals for agentic tasks — and the lag question is answered with always-valid / sequential-testing inference (peeking inflates a 5% false-positive rate to ~10% after two analyses) so the loop can act on data as it arrives without false promotion. Reusables: `closed-loop-feedback-governance-checklist`, `artifact-improvement-telemetry-schema`.

### 6.4 Status

**COMPLETE — 8/8 verified green (2026-06-15).** All eight dependent-wave items — RIB-001, RIB-003, RIB-017, RIB-033, RIB-034, RIB-035, RIB-041, RIB-047 — passed authoritative `rf verify` exit 0 (workflow `bundle_ok` never trusted), with **0 unsupported / 0 contradicted** across the entire wave. The RIB-033 storage sub-wave (033 → 034 → 035) and the RIB-047 capstone (closed-loop telemetry → artifact feedback, seeded on completed root RIB-051) are both complete. Combined with the 10-item roots wave (§1–5), all **18 dependency-tracked HIGH-priority backlog items are now verified-green evidence bundles** and backfilled in `research_idea_backlog.yaml` (`status: completed` + `links.run_id`). Live writeback validation remains deferred (file candidates only — meatywiki/skillmeat/ccdash writeback files emitted per run, not pushed to live targets).

> **Note — spend exposure.** The dependent wave consumed **~9.9M subagent tokens across 8 deep swarms** (avg ~1.24M each), plus ~210K on RIB-033's first attempt that hit an account monthly-spend-limit the day prior (recovered next day, clean retry). Pace future waves against the monthly cap accordingly.
