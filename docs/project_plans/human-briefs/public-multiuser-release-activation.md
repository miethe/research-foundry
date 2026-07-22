---
schema_name: ccdash_document
schema_version: 2

doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans

id: BRIEF-public-multiuser-release-activation
title: "Public Multi-User Release Activation — Human Brief"
status: draft
category: human-briefs

feature_slug: public-multiuser-release-activation
feature_family: public-multiuser-release-activation
feature_version: v1

prd_ref: docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
intent_ref: null
epic_ref: null

related_documents:
  - docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
  - docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md
  - docs/project_plans/human-briefs/public-release-phase5-gap-closure.md
  - docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md

owner: nick
contributors: []

audience: [humans]

priority: high
confidence: 0.72

created: 2026-07-22
updated: 2026-07-22
target_release: ""

tags: [human-brief, auth, multi-user, service-accounts, mode-d]
---

# Public Multi-User Release Activation — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-22

---

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md` (+ 6 phase files)
- **Decisions block**: `.claude/worknotes/public-multiuser-release-activation/decisions-block.md`
- **Parent (shipped) substrate**: `docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md` (P5, `completed` 2026-07-08, 47.25 pts)
- **Related brief**: `docs/project_plans/human-briefs/public-release-phase5-gap-closure.md` (overlapping gap-closure inventory — this feature subsumes its DI-1/enforcement items)
- **SPIKE**: `docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md`
- **ITT node**: `node_01KXRSGNM4E5YYTP13TY7E4KEA` (rf:public-multiuser-release-activation, in_progress)

---

## 2. Estimation Sanity Check

_Migrated from implementation plan §Estimation Sanity Check._

**Bottom-up total**: 52 pts
**Top-down anchor (H5)**: `public-multiuser-p5-auth-rbac` = 47.25 pts for the full substrate. Delta ≈ **+10%**, within ±30% tolerance.
**Reconciliation**: This is an activation layer on shipped code, not a from-scratch build — which would argue *below* the anchor. Two things push it back up: choosing **both** service accounts AND PATs roughly doubles the issuance/revocation/admin-API/admin-UI surface vs a single principal type, and the DI-1 repo-wide audit is a fresh 8-pt long pole with no direct P5 analog (P5's audit work was feature-scoped, not repo-wide).

Per-phase seed: P1≈5, P2≈14, P3≈8, P4≈13, P5≈6, P6≈6.
- **H1 noun-count**: 2 new CRUD-with-RBAC tables (`service_accounts`, `access_tokens`) → ≥4 pt floor in P2.
- **H3 algorithmic flag**: composite auth resolution + PAT role-ceiling re-resolution is ordering/resolution logic → P2 kept ≥3 for the auth chain.
- **H4 bundle-vs-sum**: ≥5 capability areas (mode / store / API / audit / UI) → summed per-area is the floor; not compressed below ~50.
- **H6 hidden plumbing (~15–20%)**: DTOs, OpenAPI, config-reference doc, CHANGELOG, `deployment-mode-status` wiring — budgeted in P6.

---

## 3. Wave & Orchestration Notes

**Critical path**: P1 (config foundation) → P2 (token store + composite auth) → P3 (admin API) → P5 (admin UI) → P6.
**Parallel opportunity**: P4's DI-1 audit (8 pts, exploration) is the long pole and is independent of the token store — **launch it in batch_2 alongside P2**, not after. Its gate-wiring rejoins after P1's stub; the sharing/sensitivity regression rejoins after P2+P3 (needs a live `multi_user` session).
**Merge order**: sequence the admin UI (P5) *last* — shipping it ahead of a tested backend exposes broken issue/revoke flows.
**Cross-feature coupling**: builds directly on the P5 substrate (auth port, RBAC, `rbac.db`, audit); no other in-flight feature blocks it. Overlaps the `public-release-phase5-gap-closure` brief on DI-1/enforcement — treat this plan as the canonical owner of those items.

---

## 4. Open Questions Ledger

| ID | Source | Question | Status | Resolved By |
|----|--------|----------|--------|-------------|
| OQ-1 | decisions §7 | `token_service.py` under `services/` (store-adjacent) vs `api/auth/`? | open | resolve in P2 (recommend `services/`) |
| OQ-2 | decisions §7 | `access_tokens.principal_id` — polymorphic id + `principal_type` discriminator vs nullable-pair FKs? | open | resolve in P2 (recommend discriminator + app-level integrity; SQLite has no partial FK) |
| OQ-3 | decisions §7 / PRD FR-13 | Confirm canonical DI-1 audit artifact path `docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md` | open | resolve at P4 start |
| OQ-4 | decisions §7 / PRD FR-6 | `last_used_at` written per token hit vs throttled/best-effort? | open | resolve in P2 (recommend throttled, fail-open like audit) |
| OQ-5 | PRD §14 (release spec) | SQLite vs Postgres for the shared state DB at public scale | deferred | assumed SQLite; Postgres migration is a DOC-006 deferred spec |

---

## 5. Deferred Items Rationale

- **OIDC adapter**: Deferred (FU-2/FU-3, seam/stub only) — user-confirmed 2026-07-22. Clerk covers public human auth; OIDC is only needed for external-IdP federation. Promote when a deployment requires BYO-IdP.
- **Postgres migration of `rbac.db`**: Deferred. SQLite is adequate for single-node LAN + modest public load; the store interface abstracts the backend. Promote when concurrent-write contention or multi-node deployment appears.
- **Fine-grained service-account scoping** (per-resource/action beyond the 5-role model): Deferred to a DOC-006 design spec. Promote if role-granularity proves insufficient for automation least-privilege.

---

## 6. Risk Narrative

- **`single_user` regression (top concern)**: the whole point is that the LAN/NUC deployment keeps working *unchanged* with agents at full local access. The preset resolver must be additive-only; FR-2's byte-identical-resolved-config test is the load-bearing gate — do not accept P1 without it green.
- **DI-1 false-completion (Critical)**: this exact surface already produced a "100% coverage" claim that was later found incomplete (WKSP-304 AAR — 2 Mode-D leaks post-hoc). The audit's scope-boundary statement is the thing to scrutinize, not the leak count. The two-part gate (operator ack + machine-checkable artifact `status: accepted`) exists so a stale doc or an unread flag alone can't unlock `multi_user`.
- **Token secret handling**: hash-at-rest, shown-once, no secret in logs/errors/audit rows. `senior-code-reviewer` pass on P2/P3 is not optional.
- **Composite auth ordering**: token-store-first → Clerk fallthrough must be deterministic across all four credential states (valid / expired / Clerk-JWT / none). AC-2 is the exhaustive test.

---

## 7. What to Watch For

- **Subagent cwd trap**: agents in this repo write to the *main* checkout, not the active worktree — outputs were relocated during planning. During execution, verify on-disk paths land where intended.
- **Silent reviewer = blocker, not pass**: `karen`/validator gates that return only an idle notification are NOT approvals (documented gotcha). The Mode-D DI-1 sign-off (ACT-406) especially — treat human silence as unresolved.
- **haiku agents hard-error here**: dispatch exploration/doc agents as `model="sonnet"`.
- **DI-1 audit is the schedule pole**: surface its draft scope-boundary to the human reviewer *as soon as ACT-401 lands*, not at end of P4, or the Mode-D sign-off becomes the bottleneck before P6.

---

## 8. Expected Success Behaviors

- [ ] On the NUC/LAN box with no config change, agents still hit the API with full local access (single_user preset = today's behavior, byte-identical).
- [ ] Flipping `deployment_mode: multi_user` with `auth.provider=none` (or DI-1 not acknowledged) **refuses to boot** with a specific per-condition error.
- [ ] A human signs up via Clerk on the public instance and lands with their assigned role; a viewer cannot reach admin routes.
- [ ] An operator issues a service-account token, sees the secret exactly once, and an agent authenticates non-interactively under that named role; revoking it blocks the next request without a restart.
- [ ] A user-scoped PAT cannot exceed its issuer's role, and stops working if the issuer is downgraded.
- [ ] Agent research (agent_jobs) under `multi_user` runs as the configured service account; the audit log shows both the triggering human and the executing service identity.

---

## 9. Running Log

- [2026-07-22] Brief created alongside PRD + implementation plan (Tier 3, ~52 pts). Product decisions confirmed with owner: Clerk for public human auth, both service accounts AND user-scoped PATs, OIDC deferred (seam only), SQLite store extension. Planning authored in an isolated worktree; squashed to main.
