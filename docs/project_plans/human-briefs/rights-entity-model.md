---
schema_name: ccdash_document
schema_version: 2

doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans

id: BRIEF-rights-entity-model
title: "Rights & Evidence-Item Entity Model — Human Brief"
status: draft
category: human-briefs

feature_slug: rights-entity-model
feature_family: rights-entity-model
feature_version: v1

prd_ref: docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md
plan_ref: docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md
intent_ref: null
epic_ref: null

related_documents:
  - /Users/miethe/dev/homelab/development/pediatric-anemia-site/docs/project_plans/research/research-foundry-rights-entity-model-handoff-v1.md
  - .claude/worknotes/rights-entity-model/decisions-block.md
  - docs/project_plans/design-specs/reusable-assertion-ledger-public-rights-promotion.md

owner: Nick Miethe
contributors: [Opus orchestrator]

audience: [humans]

priority: high
confidence: 0.72

created: 2026-07-21
updated: 2026-07-21
target_release: ""

tags: [human-brief, rights, governance, evidence-model]
---

# Rights & Evidence-Item Entity Model — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-21

---

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/infrastructure/rights-entity-model-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/infrastructure/rights-entity-model-v1.md`
- **Decisions block** (§9 adjudications live here): `.claude/worknotes/rights-entity-model/decisions-block.md`
- **Upstream handoff** (cross-repo): `pediatric-anemia-site/docs/project_plans/research/research-foundry-rights-entity-model-handoff-v1.md`
- **v1.0 spec being ported** (cross-repo): `pediatric-anemia-site/.../research_foundry_rights_governance_spec_v1.0/`
- **Design Specs**: `reusable-assertion-ledger-public-rights-promotion.md` (nearest RF precedent, status: deferred)
- **SPIKEs**: None — waived; §9 conflicts adjudicated in the decisions block instead of a research SPIKE.

---

## 2. Estimation Sanity Check

**Bottom-up total**: ~41 pts (decisions block); PRD independently landed 45–55 pts. Reconcile toward **~41–45 pts** — the delta is buffer on the two H3-flagged algorithmic slices (P2 validator, P4 snapshot/substitute discovery).

**Top-down anchor**: The reusable-assertion-ledger multi-phase rollout (phase0→phase1 with inline-dict schema tests) is the nearest RF comparable; this feature is roughly 2× its scope (7 phases vs ~2, plus a capture-pipeline integration + governance wiring).

**Reconciliation**: No single past RF feature is this large; bottom-up wins. Trust ~41–45 pts, firmly Tier 3.

H1–H6:
- **H1 (noun-count)**: ~9 schema nouns — 4 ported substrate schemas + `rights_summary`/`synthesis`/`substitutability` + 2 enums.
- **H2 (dual-impl)**: N/A — single file-backed plane, no local+enterprise split.
- **H3 (algorithmic flag)**: fires on P2 (time-parameterized divergence validator, no wall-clock precedent in RF) and P4 (content-addressed terms snapshot diff + substitute-source discovery). These carry the buffer.
- **H4 (bundle-vs-sum)**: 4 capability areas → summed floor ≈ 41; matches bottom-up.
- **H5 (anchor)**: assertion-ledger rollout, scaled ~2×.
- **H6 (hidden plumbing)**: P6 budgets fixture regen + CLAUDE.md/artifact-type-reference/CLI-help/README/CHANGELOG (~15%).

---

## 3. Wave & Orchestration Notes

**Critical path**: P0 (Rights Substrate) → P1 → P2 → P3 → P4 → P5 → P6. **This is mostly serial by necessity** — the substrate schemas gate everything, and each schema phase builds on the prior entity shape. Do not expect large parallel speedups.

**Parallel opportunities**: The main honest parallel slice is **P5 canonical-ADR authoring (documentation-writer) ∥ P4 implementation** (different owners, no file overlap). P1 evidence-taxonomy ∥ early P2 schema work is *possible* but risky (shared evidence-entity edits) — sequence conservatively.

**Merge order**: Phase-by-phase, matching the critical path. P0 must merge before any capability phase branches.

**Cross-feature coupling**: The pediatric-anemia-site team is doing interim *local* vendoring/adapter work in its own worktrees (`rights-aware-evidence-capture-v1`, `evidence-foundry-buildout`) — explicitly **not** RF's concern (handoff §11). RF ships the canonical model; the consumer un-vendors once RF lands. Watch for the consumer coupling on OQ-RF-1 timing (they won't hard-couple until RF accepts the model — which this plan does).

---

## 4. Open Questions Ledger

| ID | Source | Question | Status | Resolved By |
|----|--------|----------|--------|-------------|
| OQ-RF-1 | handoff §10 | Accept entity model as authored vs counter-propose | resolved: accept | Planning decision (user) |
| OQ-RF-2 | handoff §10 | `evidence_item_type` base axis vs Evidence-Foundry specialization | resolved: base + domain-extensible | Decisions block D4/P1 |
| OQ-RF-3 | handoff §10 | Denormalized mirror vs runtime resolution API | resolved: mirror; API deferred | User decision + DOC-006 |
| OQ-RF-4 | handoff §10 | Terms snapshot hosting location | resolved: hash+snapshot in RF run dir; hosting = gap | Decisions block P4 |
| OQ-RF-5 | handoff §10 | Does RF own surveillance execution | deferred: record-the-debt | DOC-006 (P6) |
| OQ-RF-6 | handoff §10 | RF rights-owner / counsel relationship | deferred: record-the-debt | DOC-006 (P6) |
| §9.1–§9.10 | handoff §9 | 10 schema-conflict adjudications | resolved | Decisions block §9 table |
| OQ-5 | decisions block §7 | Backfill: dedicated `rf` subcommand vs one-shot script | open | implementation-planner |
| OQ-6 | decisions block §7 | Release-gate rule in governance.py vs verification.py | open (rec: governance owns, verification calls) | implementation-planner |

---

## 5. Deferred Items Rationale

- **Runtime resolution API (OQ-RF-3 alternative)**: Deferred because the denormalized mirror satisfies files-canonical + offline-read constraints for MVP. Promote when mirror drift becomes a maintenance burden or a consumer needs live cross-run rights resolution. → DOC-006 design spec.
- **Surveillance / re-review loop (OQ-RF-5)**: Schema carries `next_review_at`, but nothing acts on it yet. Promote when a real re-clearance cadence is needed. → DOC-006.
- **Counsel / rights-owner workflow (OQ-RF-6)**: The human-attestation path (`CLEARED_*`/`attested`) exists and is fail-closed, but there is no named counsel role or routing. Promote when a real legal reviewer is in the loop. → DOC-006.

---

## 6. Risk Narrative

- **Authorization-boundary leak (HIGH)**: The whole feature exists to stop an *agent* from asserting legal clearance. §9.10 already found one of two `CLEARED_*` write paths unguarded. At the orchestration level: **do not let P3 or P5 pass without the both-paths negative test actually running and failing-closed.** This is the karen-milestone reason on P3.
- **Substrate port drift (MED)**: The v1.0 schemas were adversarially verified in the pediatric repo. A careless RF port loses that verification. Watch that P0's *only* intended deltas are the §9 adjudication-table rows — anything else must be recorded in the ADR with rationale.
- **Wall-clock in validator (MED)**: Rights/terms are time-dependent. RF has no wall-clock precedent in validators today. Watch for `datetime.now()`/`utcnow`/`time.time` sneaking into P2 — the `--as-of` reproducibility test is the guard.
- **Backfill (MED)**: §2.6.1 requires every existing source+evidence entity to carry a `rights_summary`. All-`unknown` is valid by construction (fail-closed), so backfill should be safe — but verify the existing corpus passes the validator at P2 exit.

---

## 7. What to Watch For

- **The "already published" trap**: The handoff says RF "published" v1.0, but it exists only as spec artifacts in the *pediatric* repo — RF is greenfield. The plan's Phase 0 exists precisely because of this. If an executor assumes `rights_record` already exists in RF, it will build a mirror over nothing.
- **Don't edit the pediatric-repo spec doc** (D3). RF authors its own ADR. Cross-repo commits are out of scope.
- **Fail-closed is a contract state, not a courtesy** (R-P2): every new field needs explicit missing/null handling; absence must map to `unknown`, never "cleared".
- **RF uses inline-dict test fixtures**, not the checksum/`validation_report.json` fixture style of the v1.0 bundle — don't port the pediatric fixture convention.

---

## 8. Expected Success Behaviors

- [ ] A source card captured today carries a `rights_summary` full of `unknown` (visible ignorance), not an empty/absent block.
- [ ] Attempting to set a `CLEARED_*`/`attested` value from any agent path fails closed — verifiable by running the negative test and seeing it reject.
- [ ] Running the divergence validator twice with the same `--as-of` produces byte-identical output.
- [ ] A `judgment_basis: unassessed` evidence item blocks a *commercial-release* gate but does not block *internal capture*.
- [ ] `rf verify` (or the new validator subcommand) flags a `rights_summary` whose non-`unknown` mirror has no linked `rights_record`.
- [ ] CHANGELOG `[Unreleased]` names the capture-behavior change before release.

---

## 9. Running Log

- [2026-07-21] Brief created. Tier 3, SPIKE waived. Key discovery: v1.0 substrate is NOT in the RF repo (pediatric-repo only) → Phase 0 substrate port added to scope. Four planning decisions locked by user (full C1–C4, mirror binding, SPIKE waived, record-the-debt). PRD + decisions block authored; implementation plan in progress.
