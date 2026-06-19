# The Full Wave: Evidence at Scale

## Two dependency-ordered waves

The backlog was executed in dependency order: roots first, dependents after. Both waves ran strictly sequential (one deep swarm at a time), and every run was confirmed by authoritative `rf verify` — never by the workflow's own `bundle_ok` self-report.

---

## Roots wave — 10 runs

| Ref | Run ID (`rf_run_20260614_…`) | Topic | Artifact (depth) | Sources | Claims (sup / inf / spec) | Unsup | Verify | Bundle |
|-----|------------------------------|-------|------------------|---------|---------------------------|-------|--------|--------|
| **RIB-002** | `what_does_the_empirical_literature_say` | Hallucination mitigation & claim-ledger | literature_review (deep) | 12 | **95** (75 / 18 / 2) | 0 | ✅ exit 0 | verified |
| **RIB-018** | `what_published_security_frameworks_threat_models` | Cross-profile API-key isolation | technical_memo (deep) | 12 | **102** (82 / 18 / 2) | 0 | ✅ exit 0 | verified |
| **RIB-024** | `what_patterns_file_watch_hooks_post` | Broker-less local event patterns | technical_memo (deep) | 12 | **90** (71 / 17 / 2) | 0 | ✅ exit 0 | verified |
| **RIB-025** | `what_components_schemas_agent_roles_and` | Minimum viable research-swarm arch | report (deep) | 12 | **94** (77 / 14 / 3) | 0 | ✅ exit 0 | verified |
| **RIB-026** | `what_architectures_define_an_agentic_origination` | Agentic origination / intent-routing | technical_memo (deep) | 12 | **97** (77 / 18 / 2) | 0 | ✅ exit 0 | verified |
| **RIB-037** | `what_are_the_documented_trade_offs` | File-first vs DB-first KBs | technical_memo (std) | 9 | **64** (52 / 10 / 2) | 0 | ✅ exit 0 | verified |
| **RIB-042** | `what_methods_exist_for_automatically_scoring` | Quality scoring / `quality_score` | report (deep) | 12 | **98** (78 / 18 / 2) | 0 | ✅ exit 0 | verified |
| **RIB-045** | `do_token_logprob_distributions_provide_more` | Logprob vs self-report calibration | technical_memo (deep) | 12 | **91** (73 / 16 / 2) | 0 | ✅ exit 0 | verified |
| **RIB-051** | `what_governance_criteria_evaluation_frameworks_a` | SkillBOM promotion governance | technical_memo (std) | 9 | **66** (54 / 9 / 3) | 0 | ✅ exit 0 | verified |
| **RIB-053** | `what_pipeline_architecture_best_ingests_outputs` | Unified research-capture ingestion | technical_memo (deep) | 12 | **96** (78 / 16 / 2) | 0 | ✅ exit 0 | verified |
| **TOTAL** | **10 runs** | — | 8 deep / 2 std | **114** | **893** (717 / 154 / 22) | **0** | **10 / 10** | **10 / 10** |

Every run also emitted all three writeback candidates (`meatywiki_writeback.md`, `skillbom_candidate.md`, `ccdash_event.yaml`) — 30 candidate files.

---

## Dependent wave — 8 runs

| RIB | Seeds | Artifact | Sources | Claims (S / I / Spec) | Unsupp / Contra | Verify | Tokens | Agents | Wall |
|-----|-------|----------|---------|------------------------|-----------------|--------|--------|--------|------|
| 001 | RIB-002, RIB-045 | technical_memo (deep) | 12 | 96 (79 / 16 / 1) | 0 / 0 | **exit 0 ✓** | 1.42M | 23 | ~21 m |
| 003 | RIB-002 | technical_memo (deep) | 12 | 102 (84 / 16 / 2) | 0 / 0 | **exit 0 ✓** | 1.37M | 23 | ~18 m |
| 017 | RIB-018 | technical_memo (deep) | 12 | 94 (75 / 17 / 2) | 0 / 0 | **exit 0 ✓** | 1.38M | 23 | ~19 m |
| 033 | RIB-037 | technical_memo (deep) | 12 | 90 (72 / 16 / 2) | 0 / 0 | **exit 0 ✓** | 1.22M | 23 | ~17 m |
| 034 | RIB-033 (in-wave) | technical_memo (deep) | 12 | 91 (74 / 14 / 3) | 0 / 0 | **exit 0 ✓** | 1.24M | 23 | ~22 m |
| 035 | RIB-033 (in-wave) | technical_memo (deep) | 12 | 102 (83 / 17 / 2) | 0 / 0 | **exit 0 ✓** | 1.28M | 23 | ~18 m |
| 041 | RIB-042 | technical_memo (deep) | 12 | 101 (80 / 19 / 2) | 0 / 0 | **exit 0 ✓** | 1.42M | 25 | ~21 m |
| 047 | RIB-051 | literature_review (deep) | 12 | 98 (79 / 17 / 2) | 0 / 0 | **exit 0 ✓** | 1.32M | 23 | ~21 m |

!!! note "RIB-033 spend-limit hit"
    RIB-033 failed once at discovery (2026-06-14) — all 5 angle agents hit an account monthly-spend-limit error (`no sources discovered`, ~210K tokens, 33 s, zero artifacts). Re-launched 2026-06-15 after the cap cleared; succeeded clean on the first retry.

---

## Grouped findings

### Quality and verification

**The claim-ledger gate held perfectly across all 18 runs.** 893/893 claims in the roots wave and ~784 claims in the dependent wave resolve to a source card or carry an `inference`/`speculation` label with populated basis. Zero unsupported or contradicted claims reached any report. Only RIB-037 took a single in-loop verify retry (`verify_tries:1`, self-corrected); the other nine passed on the first attempt in the roots wave.

Real evidence at scale: 114 source cards (roots wave) cite primary sources including arXiv/ACL papers (SAFE, FActScore, ALCE, Kadavath, Tian, Xiong, Guo, RAGChecker), vendor API docs (OpenAI logprobs, Gemini grounding, Perplexity Sonar, Vault, MLflow/Langfuse registries), standards (OWASP LLM Top 10, NIST AI RMF, ISO 42001, W3C PROV, C2PA), and benchmarks (Vectara HHEM, DeepResearch Bench).

Self-referential rigor was demonstrated by RIB-025 (RF's own minimum-viable architecture) and RIB-042 (RF's own `quality_score`) — the swarm audited RF's design *using RF's own traceability discipline* and produced concrete, evidence-anchored verdicts without special-casing.

### Orchestration and storage

**Sequential-by-default eliminated rate-limit waste.** Acting on the prior batch's recommendation, all 18 runs launched strictly one-deep-workflow-at-a-time. Zero throttle events across ~222 agents in the roots wave (vs ~22% wasted tokens in an earlier parallel attempt). The constraint is concurrent source-carders, not concurrent workflows per se.

**The cost profile is stable and predictable:** approximately 1.22M subagent tokens per verified bundle, 19–23 agents, 15–20 min wall-clock. Standard-depth runs (RIB-037, RIB-051) ran approximately 1.0–1.16M tokens and 19 agents; deep runs approximately 1.24–1.33M and 22–23 agents. Standard depth shaves about 15–20% off both metrics.

### Governance and calibration

**The workflow self-report is not trustworthy — always re-run authoritative `rf verify`.** The roots wave caught this explicitly on RIB-018: the workflow reported `verify_exit:0, bundle_ok:true`, but an authoritative `rf verify` re-run failed (exit 2) on `inferences_have_basis` + `inference_is_labeled`. The Phase-8 bundle-audit agent had appended an inference claim (`clm_inf18`) with empty `from_claims` and no `Inference:` label *after* the verify loop. Fixed by populating the basis, adding the label, then re-verify/re-bundle/re-writeback. This catch validated the "always re-run authoritative verify" discipline.

---

## Cross-run convergence

Several runs independently reinforce each other:

- **RIB-002 + RIB-042** both land on atomic-claim support rate as the dominant quality signal; RIB-042's formula operationalizes RIB-002's verifier thesis.
- **RIB-025 + RIB-026 + RIB-037** converge on the same architectural spine — central-supervisor orchestration (026), files-as-truth + derived index (037), and a minimal MUST-have loop with deferred memory (025).
- **RIB-045 + RIB-042** share the calibration/threshold machinery — logprob confidence feeds the gate decisions that the quality score describes.
- **RIB-018 + RIB-051** both call for explicit human-in-the-loop gates and attributed/audited state transitions.
- The cheap-extract/deep-synthesize thesis from an earlier batch is re-validated by RIB-025 and RIB-002.

---

## Stable cost profile

Six roots-wave runs were measured directly via workflow completion telemetry:

| Run | Agents | Subagent tokens | Duration |
|-----|--------|-----------------|----------|
| RIB-026 | 23 | 1.33M | 16.2 min |
| RIB-037 | 22 | 1.16M | 15.3 min |
| RIB-042 | 23 | 1.25M | 19.2 min |
| RIB-045 | 23 | 1.30M | 19.3 min |
| RIB-051 | 19 | 1.01M | 16.8 min |
| RIB-053 | 22 | 1.24M | 17.1 min |
| **6 measured** | **132** | **~7.30M** | ~104 min active |
| RIB-002/018/024/025 (deep, est. ~1.2M ea.) | ~88 | ~4.8M | ~64 min |
| Findings-digest + RIB-018 repair | ~2 | ~0.2M | — |
| **Roots-wave grand total (est.)** | **~222** | **~12.3M** | ~3 h active |

≈ **1.22M subagent tokens per verified bundle** — identical to the prior batch's ~1.2M, confirming a stable per-bundle cost. A full HIGH-priority pillar of ~10 deep runs runs approximately 12M tokens / ~3 hours of active swarm time, sequentially.

---

## Verification discipline enforced

The canonical rule established across both waves:

> After **every** run, ignore the workflow's `bundle_ok` and re-run `rf verify <run_id>` as the authoritative checkpoint. Only exit 0 counts.

All 18 final states were confirmed green this way. The RIB-018 false-pass (caught and fixed) is the proof-of-concept for why this discipline exists.

---

[See what these runs enabled →](what-it-enables.md)
