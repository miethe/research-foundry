---
schema_name: ccdash_document
schema_version: 2

doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans

id: BRIEF-wksp-304-workspace-isolation-enforcement
title: "WKSP-304 Row-Level Workspace Isolation Enforcement — Human Brief"
status: draft
category: human-briefs

feature_slug: wksp-304-workspace-isolation-enforcement
feature_family: wksp-304-workspace-isolation-enforcement
feature_version: v1

prd_ref: docs/project_plans/PRDs/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
plan_ref: docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
intent_ref: null
epic_ref: null

related_documents:
  - .claude/worknotes/wksp-304-workspace-isolation-enforcement/decisions-block.md
  - .claude/worknotes/wksp-304-workspace-isolation-enforcement/exploration-findings.md
  - docs/project_plans/human-briefs/public-multiuser-p5-auth-rbac.md

owner: nick
contributors: [nick]

audience: [humans]

priority: high
confidence: 0.8

created: 2026-07-08
updated: 2026-07-08
target_release: ""

tags: [human-brief, security, multi-tenant, workspace-isolation]
---

# WKSP-304 Row-Level Workspace Isolation Enforcement — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-08

---

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md`
- **Decisions block**: `.claude/worknotes/wksp-304-workspace-isolation-enforcement/decisions-block.md` (D1–D5)
- **Exploration findings**: `.claude/worknotes/wksp-304-workspace-isolation-enforcement/exploration-findings.md`
- **Design Specs**: None
- **SPIKEs**: None — exploration resolved all unknowns; no SPIKE warranted
- **Related Briefs**: P5 Auth/RBAC brief (`public-multiuser-p5-auth-rbac.md`) — WKSP-304 is the deferred enforcement flip from that initiative

---

## 2. Estimation Sanity Check

_Human-authored orchestrator lens; not agent-relevant._

**Bottom-up total**: 10 pts (decisions block §4) — PRD Epics table sums to ~11.5 pts pre-buffer.
**Top-down anchor**: **P5.6 RBAC enforcement toggle** (commit `f8906cd`) — the same fail-closed flag pattern + config/loopback validation. A pure toggle was ~5–6 pts; WKSP-304 adds the ~60–80-query-point scoping surface P5.6 lacked, hence ~+3–4 pts.
**Reconciliation**: Anchored at **10 pts**, below the bottom-up 11.5 because P1 (config flag) and P2 (identity threading) are near-mechanical copies of existing patterns. The delta is within the ≥30% tolerance — trust bottom-up; **do not compress P3** (the query-scoping phase is where the security value and the leak risk both live).

Canonical H1–H6 (estimation-heuristics.md):
- **H1 (noun-counting)**: 0 new tables — schema was migrated/backfilled in P5.3. No CRUD-with-RBAC noun cost.
- **H2 (dual-implementation multiplier)**: N/A — single store backend, no local+enterprise fork.
- **H3 (algorithmic service flag)**: Not algorithmic per se, but P3 carries **breadth** risk (JOIN/tombstone leak reasoning across ~60–80 points). Priced at 3 pts for surface area, not algorithm — no SPIKE needed since scenarios are enumerable.
- **H4 (bundle-vs-sum)**: Single capability area (isolation enforcement) — no ≥3-area bundle floor applies.
- **H5 (anchor)**: P5.6 RBAC toggle, above. Delta justified by the query-scoping surface.
- **H6 (hidden plumbing ~15–20%)**: Absorbed — signature churn across 20+ methods (P2) and 2-workspace fixture setup (P5) are the plumbing tax, already in the phase estimates.

---

## 3. Wave & Orchestration Notes

**Critical path**: P1 (config flag) → P3 (query scoping) → P4 (enforcing flip) → P5 (regression matrix) → P6 (docs). P2 (identity threading) joins before P3 consumes identity.
**Parallel opportunities**: P1 ∥ P2 only — disjoint files (`config.py` vs routers), both inert. From P3 onward everything is **serial by design**: P3 is single-owner for query-correctness cohesion (do NOT fan it across 3 agents by service — the JOIN-leak reasoning must live in one context).
**Merge order**: Land as one squash-merge per phase on the working branch; the enforcing flip (P4) and its test matrix (P5) should merge together so no interim commit ships armed-but-untested enforcement.
**Cross-feature coupling**: Blocks any shared-store multi-tenant deploy. No other in-flight feature depends on it, but the RBAC enforcement toggle (P5.6, already merged) is the sibling gate — keep the two flags independent (D1).

---

## 4. Open Questions Ledger

| ID | Source | Question | Status | Resolved By |
|----|--------|----------|--------|-------------|
| OQ-1 | PRD §13 / DB §7 | Cross-workspace read deny: silent 404 vs. audit-event signal? Proposal: silent to caller, audit-logged server-side. | open | P4 impl review |
| OQ-2 | PRD §13 | Deny observability — metric/telemetry on denied attempts for intrusion detection? Non-blocking. | open | P4 or P5 |
| OQ-3 | Decisions block §7 | Does RF support Postgres as a store backend as well as SQLite? If so P3 predicates need native placeholder style + P5 dual-backend fixtures. | open | P3 exploration line-item (before predicates written) |

---

## 5. Deferred Items Rationale

_None identified._ All exploration scope is covered by FR-1–FR-10 / AC-1–AC-7. Out-of-scope items (auth-core changes, new providers, frontend) are explicit exclusions, not deferrals.

---

## 6. Risk Narrative

- **P3→P4 ordering (the one that bites)**: If the enforcing flip arms before every query point is scoped, legitimate same-workspace reads 404 — a self-inflicted outage that also masks leaks behind partial enforcement. The design defuses this by keeping P3 predicates **inert** (flag-gated) so P4 is a single atomic arming step. Watch: P4's entry_criteria must be a 100%-signed P3 coverage checklist, not a vibe.
- **Single-operator fallback (Critical)**: `identity=None` powers every CLI/direct-service user today. Threading `identity` through 20+ signatures risks routing `None` into enforcement logic. The guard is structural (D3: `None`→allowed is the first statement, before any flag read), verified by an *unmodified* pass of the full pre-existing suite with enforcement globally on. If that suite needs edits to pass, something broke the fallback.
- **Leak classes (JOIN + tombstone)**: The subtle failure is a correctly-scoped primary row surfacing an unscoped joined/soft-deleted row. Mitigated by mutation-tested leak coverage (~15 tests) — a deliberately-dropped predicate must turn a test red, else the test proves nothing.

---

## 7. What to Watch For

- **"All endpoints" language** in any AC or task — reject it; demand enumerated `target_surfaces`. A missed query point is a silent leak with no test.
- **String-interpolated `workspace_id`** in a WHERE clause — instant injection hole on a security path. Every predicate parameterized.
- **Green tests that don't test anything** — the P5 leak tests must be mutation-verified (remove a predicate → red). A passing suite over unscoped queries is the worst outcome: false confidence.
- **`workspace_id IS NULL`** rows — treated as mismatch/deny under enforcement (safety net); confirm no legitimate path relies on null-workspace rows post-P5.3 backfill.

---

## 8. Expected Success Behaviors

- [ ] With `workspace_isolation_enforcement=enabled` + two workspaces seeded, a workspace-A caller gets 404 on a workspace-B record read and never sees B rows in any list/count.
- [ ] With the flag `disabled` on a non-loopback bind, the server refuses to start (ValueError) — the fail-closed guard fires.
- [ ] Single-operator mode (`auth.provider=none`, `identity=None`) behaves exactly as before — full pre-existing suite green with enforcement enabled.
- [ ] CHANGELOG `[Unreleased]` shows the enforcement mode; `workspace-migration-runbook.md` documents how to arm it before a multi-tenant deploy.

---

## 9. Running Log

- [2026-07-08] Brief created alongside PRD + decisions block. Tier 2 / Mode D. Exploration complete, no SPIKE. Awaiting implementation-plan expansion.
