# Case Study: 18 HIGH-Priority Questions, 0 Unsupported Claims

## What was attempted

Research Foundry's backlog contains a structured set of `priority: high` research questions, each modeled as a dependency graph node. Before running a single question, the backlog was analyzed for dependency order.

The result was two waves:

- **Roots wave** — 10 dependency-free HIGH-priority items, covering hallucination mitigation, API-key isolation, broker-less event patterns, research-swarm architecture, intent routing, file-first vs DB-first knowledge bases, quality scoring, logprob calibration, SkillBOM governance, and research-capture ingestion.
- **Dependent wave** — 8 HIGH-priority items that depended on roots completing first: claim segmentation, contradiction detection, sensitivity-aware routing, embedding/vector-store strategy, hybrid BM25/FTS5 ranking, semantic entity consolidation, agentic eval CI, and closed-loop telemetry.

Both waves used the same execution pattern: Path B (Claude-orchestrated discovery, RF governance spine + deterministic tail), strictly sequential one-deep-swarm-at-a-time, authoritative `rf verify` after every run.

---

## Headline results

### Roots wave (10 runs)

| Ref | Topic | Artifact | Sources | Claims (Sup / Inf / Spec) | Unsup | Verify | Bundle |
|-----|-------|----------|---------|---------------------------|-------|--------|--------|
| RIB-002 | Hallucination mitigation & claim-ledger | literature_review (deep) | 12 | **95** (75 / 18 / 2) | 0 | ✅ exit 0 | verified |
| RIB-018 | Cross-profile API-key isolation | technical_memo (deep) | 12 | **102** (82 / 18 / 2) | 0 | ✅ exit 0 | verified |
| RIB-024 | Broker-less local event patterns | technical_memo (deep) | 12 | **90** (71 / 17 / 2) | 0 | ✅ exit 0 | verified |
| RIB-025 | Minimum viable research-swarm arch | report (deep) | 12 | **94** (77 / 14 / 3) | 0 | ✅ exit 0 | verified |
| RIB-026 | Agentic origination / intent-routing | technical_memo (deep) | 12 | **97** (77 / 18 / 2) | 0 | ✅ exit 0 | verified |
| RIB-037 | File-first vs DB-first KBs | technical_memo (std) | 9 | **64** (52 / 10 / 2) | 0 | ✅ exit 0 | verified |
| RIB-042 | Quality scoring / `quality_score` | report (deep) | 12 | **98** (78 / 18 / 2) | 0 | ✅ exit 0 | verified |
| RIB-045 | Logprob vs self-report calibration | technical_memo (deep) | 12 | **91** (73 / 16 / 2) | 0 | ✅ exit 0 | verified |
| RIB-051 | SkillBOM promotion governance | technical_memo (std) | 9 | **66** (54 / 9 / 3) | 0 | ✅ exit 0 | verified |
| RIB-053 | Unified research-capture ingestion | technical_memo (deep) | 12 | **96** (78 / 16 / 2) | 0 | ✅ exit 0 | verified |
| **TOTAL** | **10 runs** | 8 deep / 2 std | **114** | **893** (717 / 154 / 22) | **0** | **10 / 10** | **10 / 10** |

### Dependent wave (8 runs)

| RIB | Artifact | Sources | Claims (S / I / Spec) | Unsupp / Contra | Verify | Tokens | Agents | Wall |
|-----|----------|---------|------------------------|-----------------|--------|--------|--------|------|
| 001 | technical_memo (deep) | 12 | 96 (79 / 16 / 1) | 0 / 0 | **exit 0 ✓** | 1.42M | 23 | ~21 m |
| 003 | technical_memo (deep) | 12 | 102 (84 / 16 / 2) | 0 / 0 | **exit 0 ✓** | 1.37M | 23 | ~18 m |
| 017 | technical_memo (deep) | 12 | 94 (75 / 17 / 2) | 0 / 0 | **exit 0 ✓** | 1.38M | 23 | ~19 m |
| 033 | technical_memo (deep) | 12 | 90 (72 / 16 / 2) | 0 / 0 | **exit 0 ✓** | 1.22M | 23 | ~17 m |
| 034 | technical_memo (deep) | 12 | 91 (74 / 14 / 3) | 0 / 0 | **exit 0 ✓** | 1.24M | 23 | ~22 m |
| 035 | technical_memo (deep) | 12 | 102 (83 / 17 / 2) | 0 / 0 | **exit 0 ✓** | 1.28M | 23 | ~18 m |
| 041 | technical_memo (deep) | 12 | 101 (80 / 19 / 2) | 0 / 0 | **exit 0 ✓** | 1.42M | 25 | ~21 m |
| 047 | literature_review (deep) | 12 | 98 (79 / 17 / 2) | 0 / 0 | **exit 0 ✓** | 1.32M | 23 | ~21 m |

---

## Combined totals

!!! info "Combined across both waves"
    - **18 runs, 18/18 verified green** (authoritative `rf verify` exit 0, not the workflow self-report)
    - **~1,677 material claims** total (893 roots + ~784 dependent)
    - **0 unsupported, 0 contradicted** across all claims in both waves
    - **~22M subagent tokens** total (~12.3M roots + ~9.9M dependent)
    - **~6 hours active swarm time** (strictly sequential, zero rate-limit events)
    - **30 writeback candidate files** from the roots wave alone (meatywiki, skillbom, ccdash per run)

---

## Why this matters as proof

Three things make this result meaningful rather than nominal:

**1. The verifier is an adversarial gate, not a formatting check.** `rf verify` fails exit 4 on any unsupported material claim. It also fails exit 0 if an inference claim lacks a populated `from_claims` basis or a visible `Inference:` label in the report. The wave caught this failure mode on RIB-018: the workflow's own `bundle_ok` reported true, but an authoritative `rf verify` re-run failed on `inferences_have_basis` + `inference_is_labeled`. The run was repaired and re-verified before being counted as green.

**2. The questions are genuinely hard.** The topics span peer-reviewed NLP benchmarks (SAFE, FActScore, ALCE, RAGChecker), security standards (OWASP LLM Top 10, NIST AI RMF, ISO 42001), retrieval engineering (BM25, pgvector, sqlite-vec), and agentic CI/CD — not softball questions designed to be easy to verify.

**3. The label mix is honest.** 80.3% supported, 17.2% inference, 2.5% speculation across the roots wave. Every inference carries a populated `from_claims` basis. Every speculation carries a visible label. The ledger does not inflate the supported count by burying ambiguity.

---

[Read the anatomy of one run →](one-run.md)
