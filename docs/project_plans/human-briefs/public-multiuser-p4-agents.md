---
schema_name: ccdash_document
schema_version: 2

doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans

id: "BRIEF-public-multiuser-p4-agents"
title: "Public Multi-User P4 — Embedded Agent Research — Human Brief"
status: draft
category: human-briefs

feature_slug: "public-multiuser-p4-agents"
feature_family: "public-multiuser-p4-agents"
feature_version: "v1"

prd_ref: "docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md"
intent_ref: ""
epic_ref: ""

related_documents:
  - docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
  - docs/project_plans/exploration/credential-process-isolation/credential-process-isolation-charter.md
  - docs/project_plans/implementation_plans/public-multiuser-p2p3-opus-handoff.md
  - .claude/worknotes/public-multiuser-p4-agents/decisions-block.md

owner: nick
contributors: []

audience: [humans]

priority: high
confidence: 0.65

created: "2026-07-06"
updated: "2026-07-06"
target_release: ""

tags: [human-brief, agents, credential-isolation, public-multiuser-release, mode-d]
---

# Public Multi-User P4 — Embedded Agent Research — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-06

---

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md` (split into 4 phase files under `.../public-multiuser-p4-agents-v1/`)
- **Design Specs**: `docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md` (§9/§10/§11/§12.4 — parent spec)
- **SPIKEs**: `docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md` (SEAM-2 / ADR-002, accepted GO)
- **Charter**: `docs/project_plans/exploration/credential-process-isolation/credential-process-isolation-charter.md`
- **Decisions Block**: `.claude/worknotes/public-multiuser-p4-agents/decisions-block.md` (Opus-authored scaffold this plan expands)
- **Precedent**: `docs/project_plans/implementation_plans/public-multiuser-p2p3-opus-handoff.md` (P2/P3, merged main)
- **Related Briefs**: None yet — P5 (`public-multiuser-p5-auth-rbac-v1`) has a PRD but no plan/brief as of this writing.

---

## 2. Estimation Sanity Check

Ran per `.claude/skills/planning/references/estimation-heuristics.md` H1–H6. Bottom-up, not top-down — this plan's total (24 pts) is the sum of the per-phase task tables in the 4 phase files, not a back-solved package price.

**H1 — Noun-counting**: 6 new domain nouns (`agent_job`, `agent_job_event`, `agent_job_artifact`, `agent_job_tool_call`, `agent_job_approval`, `agent_job_acceptance`). These are file-canonical child records under a job aggregate, not independent CRUD-with-RBAC tables (RBAC is explicitly P5), so the generic "~2 pts/noun" floor doesn't apply uniformly. Weighted by first-class-ness: `agent_job` (parent, ~2 pts, state-machine-bearing) + `agent_job_event`/`agent_job_tool_call` (log-like, ~0.5 pt each) + `agent_job_artifact`/`agent_job_approval`/`agent_job_acceptance` (first-class accept/reject surface, ~1–1.5 pt each) ≈ 6.5 pt floor for the data-model+API layer — roughly matches P4.1 (3) + P4.4 (4) = 7 pts. Consistent.

**H2 — Dual-implementation multiplier**: N/A. Research Foundry has no dual-edition (local+enterprise) repository split; H2 does not apply to this codebase.

**H3 — Algorithmic service flag**: P4.2 (credential isolation + write-time redaction) is algorithmic-adjacent — the `_redact` guard is literally a payload *transform*, and the salted-HMAC fingerprint construction has real correctness invariants (must never itself match `secret_patterns`). PRD AC-5.1–5.5 enumerate 5 explicit test scenarios (secret-scan, crash-safety, code-path audit, fingerprint construction, governance non-match), satisfying H3's "enumerate ≥5 scenarios" bar. Budgeted at 5 pts — correctly above the 3-pt algorithmic floor, and it's the plan's largest single phase.

**H4 — Bundle-vs-sum**: PRD packages 5 capability areas under one slug. Per-area independent estimate:

| Capability Area | Independent Estimate | Notes |
|------------------|----------------------|-------|
| Job model + provider port (P4.1) | 3 pts | Schema + registry, no provider impl |
| Credential isolation + firewall (P4.2) | 5 pts | H3-flagged; crown-jewel security layer |
| Provider adapters combined (P4.3 + P4.6) | 5 pts (3+2) | First adapter full wiring; second reuses the pattern, discounted |
| APIs + streaming + acceptance (P4.4) | 4 pts | SSE + CRUD + the crown-jewel accept write-path |
| Frontend `/agents` route (P4.5) | 4 pts | Route + live stream + Evidence Intake + runtime smoke |
| Testing + benchmark + docs (P4.7) | 3 pts | H6 plumbing/test/docs budget + FU-1 writeup |
| **Σ** | **24 pts** | Matches the locked plan total exactly |

**H5 — Anchor reference**: No clean point-total anchor exists for P2+P3 — they were executed via `public-multiuser-p2p3-opus-handoff.md`, a wave-based execution handoff document, not a pointed implementation plan (confirmed: no `effort_estimate`/points total in that file or its AAR). Rather than fabricate a number, the decisions block anchors **per-phase**, which is the more honest comparison: P4.3 (adapter wiring) ~ existing `adapters/*` integration effort; P4.4 (APIs+streaming) ~ P2's API+CLI wave (both added SSE-adjacent surface to an existing router); P4.5 (`/agents` UI) ~ P3's `/builder` wave (route + live data + acceptance flow — structurally the closest analog in the codebase). All three anchors are qualitative, not quantified deltas — flag this as the plan's weakest H5 compliance point; if a future retro produces a real P2/P3 point total, re-anchor then.

**H6 — Hidden plumbing budget**: Core subtotal (P4.1–P4.6) = 3+5+3+4+4+2 = 21 pts. 15–20% of 21 ≈ 3.15–4.2 pts. P4.7 is budgeted at 3 pts — slightly under the target band, but it explicitly itemizes CHANGELOG, CLI parity, context-file updates, the FU-1 design spec, and the pepper-storage decision doc as named tasks rather than folding them into "etc." Acceptable as-is; if P4.7 execution reveals more plumbing than budgeted, that's the signal to re-run H6 on the remaining phases per the heuristic's "mid-flight >50% over" trigger.

**H7 — Huge-file touch**: Checked all files in scope (`wc -l`): largest touched file is `catalog_service.py` at 1,667 lines (P4.4's accept endpoint calls its existing insert paths but doesn't rewrite it) — under the 2K-line H7 threshold. No 2× multiplier applies anywhere in this plan.

**Bottom-up total**: 24 pts
**Top-down intuition**: "agent research feature" reads like an 8–13 pt Tier-2 feature at first glance — the bottom-up bundle decomposition (H4) is what correctly forces Tier 3 / 24 pts. Trust bottom-up.
**Locked estimate**: 24 pts (matches bottom-up exactly, no compression applied).

---

## 3. Wave & Orchestration Notes

**Critical path**: P4.1 → P4.2 → P4.3 → P4.4 → P4.6 → P4.7 (10 pts of the 24 sit on the strictly-serial P4.1→P4.2→P4.3 credential-boundary chain before any parallelism is possible).

**Parallel opportunities**: P4.4 (backend `api/`) ∥ P4.5 (frontend `runs-viewer/`) once P4.3's contracts are mocked via the API-4.6 seam-task fixture — the plan's only parallel wave (wave 4 of 6). No other phase pair shares zero-file-overlap + satisfied dependencies simultaneously.

**Merge order**: This is the 3rd increment in the `public-multiuser-release` initiative (P0+P1 merged via PR #1 `1f19379`; P2+P3 merged via PR #2/#3 `8b9d8be`/`cb6af8b`). P4 should land as its own PR on `main` before P5 (auth/RBAC) implementation begins — **P5 depends on this plan's `agent_job*` schemas carrying the nullable `workspace_id`/`created_by` fields (D7/D12)**, so starting P5 implementation before P4 merges risks a schema-drift rebase. P4.2's isolation phase runs in a worktree (Mode D) — confirm that worktree is explicitly merged back to the feature branch before P4.3 starts (do not let it sit unmerged across a session boundary).

**Cross-feature coupling**: P5 auth/RBAC (`public-multiuser-p5-auth-rbac-v1`, PRD exists, no plan yet, ~40-48 pt rough estimate) is the direct downstream consumer of this plan's nullable-field forward-compat pattern. No other in-flight feature touches the same files.

---

## 4. Open Questions Ledger

| ID | Source | Question | Status | Resolved By |
|----|--------|----------|--------|-------------|
| OQ-1 | PRD §12 / Decisions D1 | Which provider ships first — `openai_agents` or `claude_agent_sdk`? | resolved | Decisions block D1: `claude_agent_sdk` first (existing scaffold, more-constrained adapter) |
| OQ-2 | PRD §12 / Decisions D2 | Server pepper storage location (env var / `foundry.yaml` secret ref / OS keyring)? | resolved (interim) | Decisions block D2: env var via `foundry.yaml` key-profile for P4; **final** location is Mode-D Gate #4 (P4.7, task VAL-7.5) |
| OQ-3 | PRD §12 / Decisions D3 | Is the FU-1 benchmark a hard gate before Wave-A implementation? | resolved | Decisions block D3: non-blocking, runs early in P4.2 (SEC-2.5) in parallel with implementation |
| OQ-4 | PRD §12 | Does job cancellation need partial-credit acceptance of already-produced artifacts? | open | Default assumption (cancel-then-nothing-stageable-is-lost) carried into API-4.4/AC-3.4; flag during P4.4 execution if this proves insufficient |
| OQ-A | Decisions block §7 | Does the SSE event stream reuse the existing runs-viewer streaming transport, or a new endpoint? | open | To be resolved at the start of API-4.3 (phase-3-4-backend-integration.md) by checking `api/` for existing SSE/websocket patterns |
| OQ-B | Decisions block §7 | Job-scoped staging store location — `.rf_cache/` (rebuildable) vs. `agent_jobs/<id>/` (durable)? | resolved (recommended) | Plan adopts the durable recommendation (mirrors `report_draft_dir`) in JOB-1.2 — confirm no objection surfaces before P4.1 seals |

---

## 5. Deferred Items Rationale

- **FU-1 (spawn-latency benchmark)**: Deferred from being a blocking gate because SPIKE ADR-002 already names in-process scoping as the documented fallback — stalling the entire credential-isolation phase on a benchmark result wastes the critical path when a known fallback exists. Promote to "must resolve before P4.6/P4.7 close" if the SEC-2.5 numbers show p95 spawn latency materially degrading interactive use.
- **FU-4 (partial — sensitivity existence-gate)**: Deferred because full remediation is P5 (auth/RBAC) scope; this plan only carries the non-regression constraint forward (API-4.2's identical-404 discipline) rather than attempting a partial fix that P5 would have to reconcile with its own auth-gated version of the same endpoints.

---

## 6. Risk Narrative

- **Credential leak into artifacts/events/browser (High)**: This is *the* reason P4.2 is 5 of the plan's 24 points and gets its own worktree + `karen` security review. The current in-process adapters have never needed to defend against this because they're single-shot; a live tool-use loop changes the threat model entirely. Watch for scope pressure to "just ship P4.3 faster" before P4.2's secret-scan/crash-safety gates are genuinely green — that pressure is exactly how this class of bug ships.
- **Prompt-injection exfiltration via the live tool loop (High)**: Structural mitigations (allowlisting, subprocess boundary, write-time redaction) are necessary but not sufficient against a sufficiently creative injection; the Codex adversarial review (P4.7, VAL-7.2) exists specifically to probe for gaps the implementing agent didn't think of. Don't skip it or treat it as a formality — it's the one adversarial (non-Claude) perspective on the firewall.
- **Subprocess spawn latency (Medium)**: The dominant *estimation* unknown, not a security unknown. If FU-1 forces the in-process fallback, P4.2 may drop ~1 pt of spawn-management work but P4.6 (second adapter) inherits more risk since the fallback path hasn't been provider-parametrized. Re-run H3/H6 on remaining phases if this triggers.

---

## 7. What to Watch For

- **ICA delegate gotchas** (per P2/P3 precedent, confirmed in that handoff doc): pipe long prompts via stdin, pin `[1m]` aliases, watch turn caps. Applies to P4.4's API-4.2/API-4.3 and P4.5's UI-5.5/UI-5.6 offload waves.
- **Silent-reviewer trap**: `karen` returning only an `idle_notification` is never a pass — this bit a prior RF execution (see memory: `dev-execute-plan-phase-owner-gap`). Re-invoke and demand an explicit verdict at all 3 `karen` gates (P4.2, P4.5, P4.7).
- **Mode-D gate logging discipline**: all 4 gates must be logged with who/when/what-reviewed *at the time*, not reconstructed after the fact. If a gate gets skipped under delegation pressure, the phase is not actually complete regardless of what the task-completion-validator says about the code.
- **Worktree merge-back for P4.2**: don't let the credential-isolation worktree branch sit unintegrated across a session boundary — explicit merge before P4.3 starts, per the git-workflow rule.
- **Codex review is read-only**: VAL-7.2 must never touch code directly; findings route back through python-backend-engineer as a normal fix task, not as a direct edit from the Codex session.

---

## 8. Expected Success Behaviors

- [ ] A researcher can select a claim or flagged report paragraph, click "Research this," and land in `/agents` with the launch form pre-populated — no manual re-entry of context.
- [ ] The Launch button stays disabled until provider/model/tools/budget/sensitivity gates are visibly acknowledged — no silent defaults ever reach a subprocess.
- [ ] Opening browser devtools' Network tab during a live job never shows a raw provider API key, anywhere in the request/response bodies or SSE frames.
- [ ] Canceling a running job leaves the Catalog and any report draft completely unchanged — nothing partially committed.
- [ ] The Evidence Intake list lets you accept some staged items and reject others individually; only accepted items ever show up in the Catalog, each carrying a visible "created by agent job" provenance link.
- [ ] In static-export mode, `/agents` shows a clear "loopback only" message — not a blank screen or a JS error.
- [ ] All 4 Mode-D gates have a dated, attributed approval note somewhere in the execution record (commit messages, this brief's Running Log, or the decision_gates frontmatter) — not just "implicitly happened."

---

## 9. Running Log

- [2026-07-06] Brief created alongside the implementation plan (expanded from the Opus decisions block). Estimation sanity check run; H5 anchor is qualitative (no P2/P3 point total exists to cite quantitatively) — flagged as the weakest link in the estimate, revisit if a P2/P3 retro produces real numbers.
