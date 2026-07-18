---
schema_name: ccdash_document
schema_version: 2

doc_type: human_brief
doc_subtype: "feature_brief"
root_kind: project_plans

id: "BRIEF-runs-writeback-approve-dispatch"
title: "Runs Writeback — Approve & Dispatch — Human Brief"
status: draft
category: human-briefs

feature_slug: "runs-writeback-approve-dispatch"
feature_family: "runs-writeback-approve-dispatch"
feature_version: "v1"

prd_ref: "docs/project_plans/PRDs/features/runs-writeback-approve-dispatch-v1.md"
plan_ref: "docs/project_plans/implementation_plans/features/runs-writeback-approve-dispatch-v1.md"
intent_ref: null
epic_ref: null

related_documents:
  - docs/project_plans/feature_contracts/features/runs-writeback-review-view.md
  - docs/project_plans/design-specs/runs-writeback-preview.md

owner: nick
contributors: []

audience: [humans]

priority: high
confidence: 0.75

created: 2026-07-18
updated: 2026-07-18
target_release: null

tags: [human-brief, writeback, governance, rbac, runs-viewer]
---

# Runs Writeback — Approve & Dispatch — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-18

---

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/features/runs-writeback-approve-dispatch-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/features/runs-writeback-approve-dispatch-v1.md`
- **Design Specs**: `docs/project_plans/design-specs/runs-writeback-preview.md` (idea-stage precursor, mostly superseded by FR-13 + this feature)
- **SPIKEs**: None
- **Related Briefs**: None — this is a direct follow-on to FR-13 (`runs-writeback-review-view` Feature Contract), not part of a larger epic brief.

---

## 2. Estimation Sanity Check

**Bottom-up total**: ~13.75 pts (task-level sum: P1 ~4, P2 ~3.75, P3 ~2.75, P4 ~3.25), rounds to the plan's **~14 pts** headline.
**Top-down anchor**: PRD's own WBAD-001..004 story backlog sums to 10–14 pts; FR-13 (the read-only half of this same surface) shipped as a Tier 1 Feature Contract at ~5–6 pts. This feature is the write-path half plus RBAC/audit/governance wiring that FR-13 explicitly did not need (no mutation existed yet) — so a ~2–2.5x multiplier over FR-13 is expected, not a red flag.
**Reconciliation**: Bottom-up (14 pts) sits at the top of the PRD's own 10–14 estimate. Agrees — no override needed.

H1–H6 heuristic application (per `.claude/skills/planning/references/estimation-heuristics.md`):
- **H1 (noun-counting)**: No new tables/CRUD resources — 0 pts from this heuristic. The "resource" here is an orchestration action, not a persisted entity.
- **H2 (dual-implementation multiplier)**: N/A — single edition (local/LAN), no enterprise variant to duplicate.
- **H3 (algorithmic service flag)**: Triggers — the orchestration function is a **dependency/conflict/merge**-shaped problem (compose 3 existing services + a new gate + per-target isolation + idempotency). Flagged ≥3 pts minimum for Phase 1; landed at 4 pts. Test scenarios (block/require_approval/pass × per-target success/fail × re-invocation) are enumerable from the PRD's own AC list, so no SPIKE needed first.
- **H4 (bundle-vs-sum)**: 4 capability areas (orchestration, API/auth/audit, UI, tests) → bottom-up per-area sum (14 pts) is the plan-total floor. No compression applied.
- **H5 (anchor reference)**: FR-13 (~5–6 pts, read-only) is the direct anchor. This feature adds the mutation, RBAC/audit threading, and governance-gate wiring FR-13 didn't touch — the ~2.3x delta is justified by scope, not padding.
- **H6 (hidden plumbing budget)**: ~15% held in Phase 2 (audit/identity threading is genuinely novel — first route in the codebase to populate `actor_user_id`) and Phase 4 (CHANGELOG, `rbac.py` docstring, OpenAPI docs already folded into task points rather than broken out separately).

---

## 3. Wave & Orchestration Notes

**Critical path**: P1 (orchestration function) → P2 (API/RBAC/audit/governance gate) → P4 (tests/hardening). P1 is the hard gate — nothing else can be built against a real contract until the orchestration function's request/response shape is locked in TASK-1.1's design review.

**Parallel opportunities**: P2 (backend API layer) and P3 (frontend UI) both depend only on P1 and can run in the same wave — P3's typed client binding and dialog UI can be built against the DTO shape locked in TASK-1.1 without waiting for P2's actual route to exist, though full FE integration testing still gates on P2.

**Merge order**: P1 → (P2 ∥ P3) → P4. Do not squash-merge P3 ahead of P2 if the two diverge on the response DTO shape mid-flight — reconcile in P2's review checkpoint (TASK-2.5) first.

**Cross-feature coupling**: None blocking. Explicitly NOT coupled to the pending OIDC adapter (PRD Decision #2) or WKSP-304 workspace-scoping (PRD §7 Out of Scope) — both are separate initiatives that this feature's RBAC-ready design defers to without blocking on.

---

## 4. Open Questions Ledger

Both PRD open questions are **resolved in this plan** (see plan `decisions:` frontmatter) rather than left open for execution-time judgment, since Tier 2 planning is exactly where FR-14/OQ-2-class tradeoffs should be locked.

| ID | Source | Question | Status | Resolved By |
|----|--------|----------|--------|-------------|
| OQ-1 | PRD §12 | Should `council_review()` always run inside the endpoint, or be skipped if a current result exists? | resolved | Plan decision D1 — always run it (cheap, idempotent, deterministic; matches PRD's own leaning) |
| OQ-2 | PRD §12 | Hard-reject (409) concurrent approve+dispatch, or last-write-wins? | resolved | Plan decision D2 — lightweight advisory lock file with short TTL (FR-14, Risk R2 mitigation); not a hard distributed lock |

---

## 5. Deferred Items Rationale

- **UI dispatch of `intenttree`/`arc`/`notebooklm` targets**: Deferred because these are live-push targets with different retry/idempotency semantics than the 3 default local-file targets; PRD explicitly scopes them CLI-only "until this pattern is proven." Promote when: the 3-target UI pattern has run in production for a while and an operator asks for the opt-in targets in the viewer.
- **Automated rollback/undo of a completed dispatch**: Deferred because the existing overwrite-idempotent re-render already gives a manual remediation path (PRD Risk R3). Promote when: manual remediation proves insufficient at higher dispatch volume, or a target becomes a live push where overwrite-idempotency no longer holds.
- **Hard distributed lock for concurrent approve+dispatch**: Deferred in favor of the lightweight advisory lock (D2 above) because today's LAN deployment is single-operator. Promote when: multi-tenant OIDC ships and real concurrent-operator collisions are observed (not just theoretically possible).

---

## 6. Risk Narrative

- **Governance-gate behavior change (PRD Risk R6)**: This is an *intentional tightening*, not a regression — a run that would dispatch cleanly via the raw CLI today may be blocked via this new endpoint because `guard_check()` now actually runs. Watch for: someone filing this as a "bug" during rollout validation. It isn't — call it out explicitly when validating Phase 2/4.
- **First-ever `actor_user_id` threading (PRD Risk R4)**: This is genuinely new code path (no precedent in the codebase populates this field from a real route). Watch for: silent `None`-swallowing bugs where identity resolves but the audit row still shows `None` — this is the single highest-value assertion in Phase 4's audit tests.
- **Mode D external-side-effect risk**: Dispatch writes real files into `meatywiki/`, `skillmeat/`, `ccdash/` workspace mirrors — these are shared, out-of-band-consumed directories, not sandboxed test fixtures. See the plan's dedicated Rollback & Mitigation section before merging Phase 1/2 to any shared branch.

---

## 7. What to Watch For

- Confirm the orchestration function calls `guard_check()` **before** any target dispatch is attempted — this must be verified by a test asserting call order, not just code review (PRD Technical Acceptance, 3rd bullet). Easy to get backwards if the implementer instinctively dispatches first and gates second.
- Confirm re-invocation is exercised with a **real second call**, not just asserting the ID-generation function is deterministic in isolation — the idempotency guarantee is about the end-to-end overwrite behavior.
- Confirm the FE's `governance_rejected` handling distinguishes it from a generic 500 by response *shape* (error code / body shape), not by string-matching an error message — brittle string matching will silently break if the error copy changes.
- Watch for scope creep per PRD Risk R7 — once a write path exists, there's a natural pull toward letting the UI edit `reviewer_notes`/`required_fix` directly. Reviewer must check the diff for any new mutation affordance beyond the single approve+dispatch action.

---

## 8. Expected Success Behaviors

- [ ] Open a completed run's Writeback tab in the runs-viewer; the "Approve & Dispatch" button is visible and, when clicked, shows a confirmation dialog before dispatching.
- [ ] After confirming, per-target outcomes (meatywiki/skillmeat/ccdash) render inline within a few seconds — no terminal needed.
- [ ] `GET /api/audit?mutation_type=writeback` (or the equivalent audit view) shows one row per invocation with an `actor_user_id` populated when running with a resolved identity.
- [ ] Deliberately trigger a governance block (e.g., a run with an unmapped material claim) and confirm the UI clearly reads as "blocked by policy," not a generic error, and that zero files were written under `writebacks/` for that run.
- [ ] Run `rf bundle`, `rf council`, `rf writeback` from the CLI directly on an unrelated run and confirm zero behavior change from before this feature shipped.

---

## 9. Running Log

- [2026-07-18] Brief created alongside implementation plan; both open questions resolved at planning time rather than deferred to execution.
