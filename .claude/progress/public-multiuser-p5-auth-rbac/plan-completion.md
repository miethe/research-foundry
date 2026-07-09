---
title: "Plan Completion Report — Public Multi-User P5 (Auth/RBAC/Isolation/Audit Hardening)"
schema_version: 2
doc_type: report
report_category: plan_completion
feature_slug: public-multiuser-p5-auth-rbac
feature_version: "v1"
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
status: completed
created: 2026-07-08
updated: 2026-07-08
tier: 3
final_head: aca4eaf
merged_to: main (local; NOT pushed)
reviewer_verdict: "karen end-of-feature: APPROVED"
---

# P5 Auth/RBAC/Isolation/Audit — Plan Completion

**Outcome:** All 9 phases delivered across 7 waves, squash-merged to **local `main`** (not pushed).
Tier 3, ~47.25 pts. All three locked human gates honored. Plan-level `karen` gate: **APPROVED**.

## Wave / phase landing (local main)

| Wave | Phase(s) | Merge SHA | Notes |
|------|----------|-----------|-------|
| 1 | P5.1 auth-provider port + local_static + durable RBAC store | `4e52be6` | 3 Codex auth-bypass fixes |
| 2 | P5.2 RBAC enforcement (5 roles, require_role) | `51c044f` | Codex: clean |
| 3 | P5.4 Clerk adapter ∥ P5.5 audit log | `4aa2e0d`,`533f5c6` (+P5.5) | Gate #3 (Clerk secrets) honored; Codex fixed fail-open wiring + missing /api/auth/identity |
| 4 | P5.7 deferred-sensitivity ∥ P5.8 auth-context UI | `504bc38`…`80e32a1` | Codex fixed 2 sensitivity leaks + 2 broken-auth FE defects |
| 5 | P5.3 workspace-isolation migration | `18b6c17` | **Human Gate #1** approved (apply migration, hold enforcement); no-op on this workspace; Codex fixed 2 apply-path defects |
| 6 | P5.6 rate-limits + admin + sharing/publish-preview + **RBAC-disable toggle** | `f8906cd` | **Human Gate #2** approved; Codex fixed 4 defects (share-link unreachable, live rate-limit override, publish-preview toggle, override validation) |
| 7 | P5.9 regression + E2E + docs + REVIEW-001 | `aca4eaf` | Codex REVIEW-001: RBAC complete; 1 must-fix (audit-before-exposure) fixed; karen APPROVED |

## Human gates (all honored in shipped code)
- **Gate #1 — workspace-migration dry-run:** approved *apply migration, hold enforcement*. Migration applied (no-op: 0 drafts/0 catalog items); `require_workspace_scope()` stays advisory. Approval artifact: `.rf_state/migrations/mig_20260708T145811-gate1-approval.json`.
- **Gate #2 — RBAC-before-exposure:** approved after route-sweep evidence (183 passed). Public-exposure surfaces (P5.6) landed. Approval artifact: `.rf_state/migrations/gate2-20260708T153002-approval.json`.
- **Gate #3 — Clerk secrets:** no real Clerk secrets / prod JWKS committed; fixtures only; live-key redaction test intentionally skipped.

## Adversarial review tally (Codex gpt-5.5)
Codex caught **17 genuine defects** across the plan that in-loop validators missed — all fixed with fail-pre-fix regression tests: P5.1 (3 auth-bypass), P5.4 (2), P5.5 (1 audit privacy), P5.7 (2 sensitivity leaks), P5.8 (2 broken auth), P5.3 (2 apply-path), P5.6 (4 exposure/rate-limit/toggle), P5.9 REVIEW-001 (1 audit-before-exposure).

## New operator-facing capability (per operator request during P5.6)
`auth.rbac_enforcement: auto | disabled | enabled` — first-class RBAC-disable knob for fully-local use, **fail-closed** (refused on non-loopback bind). See `docs/dev/architecture/auth-rbac-operator-guide.md`.

## Deferrals (recorded, not gaps) — tracked follow-ups
1. **WKSP-304 — row-level workspace enforcement flip.** Isolation is currently by **separate filesystem roots per deployment**, not row-level `workspace_id` scoping. `karen` flag: **must land before any shared-store multi-tenant deployment.** First off the deferral list.
2. **FU-2 — OIDC/BYO adapter:** design-spec only (`docs/project_plans/design-specs/oidc-byo-adapter-implementation.md`, `maturity: idea`). Append to plan `deferred_items_spec_refs`.
3. **`cli.py`/`cli` conflict:** resolved in P5.6 (workspace subcommands now invokable).
4. **Live-mode E2E + live-key redaction:** unrun (no live RF API / Clerk tenant in env); labeled limitations.
5. **Wire runs-viewer (:3030) to the live RF API (:7432).** *Added 2026-07-08.* The RF backend API is now
   deployed on the node (`research-foundry-api.service`, `local_static` owner token, RBAC enforced,
   `http://10.42.10.76:7432`); the viewer stays a static redaction-at-export snapshot for now. To wire live:
   rebuild the SPA with `VITE_RUNS_FRONTEND_LOOPBACK_API=true` + `VITE_RUNS_LOOPBACK_API_BASE=http://10.42.10.76:7432/api`
   + `VITE_AUTH_PROVIDER` + browser token handling. Tracked in IntentTree (side_quest).

## Validation summary
- 284 must-stay-green backend tests passing; P5 regression suite 57/57; E2E static 32 passed/4 skipped.
- Per-wave checkpoints: `.claude/progress/public-multiuser-p5-auth-rbac/.wave-{1..7}-checkpoint`.

## Outstanding orchestration notes
- Orphan locked worktree branches left for harness GC: `agent-a9dc7f074bc768ff5` (P5.3), `agent-a6225171c74590a59` (P5.6), `agent-a59c116617e21d3f8` (P5.9).
- **Not pushed.** Per operator workflow, push + deploy are a separate explicit step.
