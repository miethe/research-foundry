# What It Enables: RF Design Outputs from the Wave

The 18-run wave was not only a proof of the pipeline. It produced directly-actionable design outputs for RF's own codebase. This page documents those outputs and the honest caveats.

---

## Directly-actionable RF design outputs

### 1. The `quality_score` formula (RIB-042)

RIB-042 audited RF's own `quality_score: pending` field using RF's traceability discipline and derived a concrete, deterministic formula:

!!! example "Quality score formula (RIB-042)"
    ```
    Q = 0.45 · support_rate
      + 0.20 · (1 − unsupported_rate)
      + 0.15 · source_diversity
      + 0.10 · verification_passed
      + 0.10 · (1 − normalized_rework)
    ```

    - **support_rate** dominates (45%) — claim support rate is the primary quality signal.
    - **source_diversity** = `min(1, distinct_source_domains / 6)` — requires adding one new emitted signal `distinct_source_domains` to `ccdash_event`; all other inputs are already emitted.
    - **Hard floor at 0.5** on verification failure.
    - Emit **both** a per-dimension vector and a scalar + tier.
    - Keep cost-per-claim and LLM-judge coherence **out** of the deterministic score.

    The closest prior-art analogue is RAGChecker (Pearson 61.93).

Three Goodhart-attack guards are specified: distinct-domain counting (prevents source padding), saturation (prevents claim splitting), and a per-source claim-concentration cap (prevents citation stuffing). A CoT trace-audit tripwire (72% of reward-hacks leave a rationale) is also recommended.

### 2. SkillBOM lifecycle fields (RIB-051)

The current single `report_reviewed` boolean conflates automated and human checks. RIB-051 specifies four additions:

| Field | Purpose |
|-------|---------|
| `approval_status` enum | `candidate` → `evaluated` → `human-reviewed` → `promoted` |
| Reviewer identity | Attributed human Approve, not just a boolean |
| Append-only transitions log | Immutable audit trail of state changes |
| Demotion / deprecation transition | Explicit downgrade path |

Proposed promotion thresholds:

- `candidate → evaluated` = verifier pass + governance pass + rework = 0
- `evaluated → human-reviewed` = `quality_score ≥ 0.8` across ≥2 runs
- `human-reviewed → promoted` = human Approve with zero open high-severity failure modes

The pattern is **artifact-immutable / pointer-mutable** — the candidate file is immutable; promotion is a movable pointer state. RBAC-protect the promoted pointer.

### 3. Four key-isolation tightenings (RIB-018)

Six leakage vectors cluster into three families (ambient-inheritance, observability-capture, temporal-drift). Four tightenings address them:

| Code | Tightening |
|------|-----------|
| **R1** | One-profile-per-process minimal env — scope keys to the process, not the session |
| **R2** | Key fingerprinting + profile-tagged telemetry — every telemetry event carries the profile that was active |
| **R3** | File-first revocation/rotation runbook + key manifest — compensates for the absence of Vault-style TTL expiry |
| **R4** | Human gate on cross-profile elevation — prevents confused-deputy escalation |

`offline_only` is the strongest guarantee (immune to all six leakage vectors) and should be the default profile. The structural gap vs server-backed secret stores (Vault, MCP short-lived tokens, SPIFFE SVIDs) is documented but not closed at this stage.

### 4. Storage / retrieval stack (RIB-033, RIB-034, RIB-035)

The storage sub-wave (RIB-033 → RIB-034 → RIB-035) produced a concrete, evidence-grounded stack recommendation for the 1K–100K file-first vault:

| Tier | Configuration |
|------|--------------|
| Default | BGE-M3 embeddings (1024-dim dense, 8192-token context), truncated to 512 dims, stored in **sqlite-vec** — one dependency-free SQLite file beside the vault |
| Migration trigger | Move dense index to **pgvector HNSW** (m=16, ef_construction=64, ef_search=40) only if interactive latency degrades near the 100K ceiling |
| Ranking at 1K | BM25-only (FTS5) with frontmatter/heading column weighting |
| Ranking at 10K | BM25 + cross-encoder reranking of the top ~100–200 lexical candidates |
| Ranking at 50K | Full BM25 + dense-vector hybrid fused by RRF (k=60), then reranked |

Key evidence: choosing fully local embeddings over OpenAI `text-embedding-3-small` costs only ~0–2 aggregate MTEB points (3-small 62.3%, 3-large 64.6%), small enough that privacy/offline benefits dominate. A cross-encoder reranker is the highest-ROI single upgrade at every affordable tier (+17.4% Recall@5; Anthropic Contextual Retrieval's 67% failure-rate reduction is driven primarily by reranking).

### 5. Context-persistence / memory gap (RIB-025)

RIB-025 identified the one unjustified MVP gap versus prior art:

> **Biggest unjustified MVP gap = absent context-persistence/memory.** Anthropic's LeadResearcher persists its plan to survive the 200K window. RF has no equivalent.

This gap is documented but not yet closed. Closing it is called out as a named next step.

---

## Reusable SkillBOM candidates

The roots wave emitted 30 `skillbom_candidate.md` files — one per run, three per run (meatywiki, skillbom, ccdash). Named reusables that emerged across the wave include:

- `ccdash-quality-score-formula`
- `run-quality-telemetry-checklist`
- `promotion_gate_matrix`
- `skillbom_lifecycle_playbook`
- `routing-policy-decision-matrix`
- `origination-layer-reference-architecture`
- `seam-integration-pattern-matrix`
- `confidence-calibration-recipe`
- `rf-mvp-architecture-spec`

These are **candidates**, not promoted skills. Per the RIB-051 governance model, they must pass the `candidate → evaluated → human-reviewed → promoted` gate before reuse. They should not be used directly.

---

## Honest caveats

!!! warning "Live writeback unvalidated"
    All 18 runs emitted writeback file candidates (`meatywiki_writeback.md`, `skillbom_candidate.md`, `ccdash_event.yaml`). Live HTTP writeback to MeatyWiki, SkillMeat, and CCDash servers has not been validated. The HTTP targets (arc/intenttree) remained unreachable across both waves. This is the one untested seam in the pipeline — writebacks degrade gracefully to file candidates when servers are offline, but the live push path has never been exercised.

!!! warning "Spend exposure"
    The dependent wave consumed approximately 9.9M subagent tokens across 8 deep swarms (average ~1.24M each), plus ~210K on RIB-033's first attempt that hit an account monthly-spend-limit error. The combined two-wave total is approximately 22M subagent tokens. Future waves should be paced against the monthly cap accordingly. RIB-033's first attempt is the documented case where the cap was hit mid-run.

---

[Read the artifact appendix →](artifacts-appendix.md)
