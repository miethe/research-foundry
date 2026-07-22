# Opus Decisions Block — Public Multi-User Release Activation

> Authored by Opus (orchestrator judgment scaffold). Expanded by `implementation-planner` into the
> full implementation plan. Tier 3; Mode D throughout (auth/identity/RBAC).
> PRD: `docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md`
> Anchor feature: `public-multiuser-p5-auth-rbac` (shipped 2026-07-08, 47.25 pts).

## Confirmed Product Decisions (user sign-off 2026-07-22)
- **Public human auth = Clerk** (wire/activate the shipped adapter; do NOT build a local human-user store).
- **Non-human principals = BOTH** standalone service accounts (`principal_type=service`) AND user-scoped PATs (`principal_type=user_pat`).
- **OIDC = deferred** (seam/stub only; explicitly out of scope).
- **Token store = extend SQLite `rbac.db`** (no Postgres); opaque secret, hashed at rest, shown once.

## 1. Phase Boundaries

| Phase | Name | Scope (FRs / ACT stories) | Exit gate |
|-------|------|---------------------------|-----------|
| P1 | Deployment-Mode Presets | FR-1..5; ACT-101,102. `deployment_mode` resolver + `single_user`/`multi_user` preset composition; `rf serve --mode`; fail-closed gate **stub** (DI-1 check wired P4). | FR-2 byte-identical-config regression test green; validator pass. |
| P2 | Non-Human Principal Store + Auth Resolution | FR-6..12; ACT-201,202,203,204. Store tables, `token_service.py` (issue/verify/revoke/expiry, hash-at-rest), composite middleware (token-store-first → Clerk fallthrough), agent-job identity binding. | Composite-auth AC-2 (4 credential states) green; **karen milestone** (security-sensitive). |
| P3 | Admin API | FR-15,17; ACT-301,302,303. Service-account + PAT issue/list/revoke/rotate routes, self-vs-admin scoping, deployment-mode-status, audit wiring. | `require_role` route sweep green; no raw secret in any response except one-time issuance; validator pass. |
| P4 | DI-1 Audit + Enforcement Flip | FR-13,14,18; ACT-401,402,403. Repo-wide full-surface workspace-scoping backward-trace, remediate leaks, wire two-part gate, sharing/sensitivity regression under `multi_user`. | **Mode D human gate**: audit scope-boundary statement human-reviewed + artifact `status: accepted`; **karen milestone**. |
| P5 | Admin UI | FR-16; ACT-501,502. `ServiceAccountsPanel.tsx`, `PersonalAccessTokensPanel.tsx`, `AuthContext.tsx` principalType. | AC-1 (one-time-secret UX + principal-type surfacing) green; a11y smoke; validator pass. |
| P6 | Testing & Docs | Cross-phase E2E, CHANGELOG, docs, SERVICE_CONTRACT + config-reference updates. | Full suite green; **karen end-of-feature**; changelog entry present. |

## 2. Agent Routing (primary + secondary per phase)

| Phase | Primary | Secondary / review |
|-------|---------|--------------------|
| P1 | `python-backend-engineer` | `backend-architect` (preset-composition design sanity) |
| P2 | `python-backend-engineer` + `data-layer-expert` (schema) | `backend-architect` (composite-auth-chain design); `senior-code-reviewer` (token secret handling) |
| P3 | `python-backend-engineer` | `api-librarian`/`senior-code-reviewer` (error-envelope + no-secret-leak) |
| P4 | `codebase-explorer` (enumeration/backward-trace) → `python-backend-engineer` (remediation) | `karen` + human (Mode D scope-boundary sign-off); anchor to assertion-ledger DI-1 audit method |
| P5 | `ui-engineer-enhanced` | `a11y-sheriff` (jest-axe on new panels) |
| P6 | `python-backend-engineer` (backend/E2E) + `ui-engineer` (UI tests) | `documentation-writer`, `changelog-generator` |

**Parallel opportunity:** P4's audit (ACT-401, exploration) is the long pole and is largely independent of the token store — **launch it in parallel with P2**. Its gate-wiring (ACT-402) joins after P1 stub; sharing/sensitivity regression (ACT-403) waits for P2+P3 + a live session.

**Env note:** haiku default agents hard-error in this environment — dispatch `codebase-explorer`/exploration agents with `model="sonnet"`.

## 3. Risk Hotspots

| Risk | Severity | Mitigation |
|------|----------|------------|
| `single_user` preset silently changes LAN/NUC default behavior | High | FR-2 byte-identical resolved-config regression test vs pre-feature baseline; preset resolver additive-only; **this is the #1 acceptance gate** for P1. |
| DI-1 audit repeats prior false "100% coverage" claim (WKSP-304 AAR) | Critical | Mode D — human review of scope-boundary before `accepted`; FR-13 two-part gate (operator ack + machine-checkable artifact status) so self-certification alone cannot unlock `multi_user`. |
| Token secret leaks via logs/errors/audit rows | Critical | Hash-at-rest, shown-once, credential-shape guards ported from existing `agent_job_service.py` pattern; `senior-code-reviewer` pass on P2/P3. |
| PAT privilege escalation after issuer role downgrade | High | FR-9 role-ceiling re-checked at **resolution time**, not just issuance. |
| Composite auth chain misorders → machine token bypasses Clerk or vice-versa | High | AC-2 exhaustive 4-credential-state test (valid token / expired token / Clerk JWT / none); token-store-first is deterministic and adapter-agnostic. |
| Agent-job SA binding breaks existing `single_user` agent workflows | Medium | FR-12 binding activates ONLY under `multi_user`; single_user identity resolution unchanged (assert in test). |

## 4. Estimation Anchors (H1–H6 seeds for implementation-planner)

- **H5 anchor:** `public-multiuser-p5-auth-rbac` = 47.25 pts for the full substrate (auth port + RBAC + isolation migration + audit + rate limits + admin + FE). This activation layer is ~a substantial fraction of that (~50 pts) because "Both" SA+PAT doubles issuance/revocation surfaces and DI-1 audit is an 8-pt long pole.
- **Per-phase seed (from PRD ACT backlog):** P1≈5, P2≈14, P3≈8, P4≈13, P5≈6, P6≈6 → **~52 pts**.
- **H1 noun-count:** 2 new tables (`service_accounts`, `access_tokens`) each CRUD-with-RBAC → ≥4 pts floor in P2.
- **H3 algorithmic flag:** composite auth resolution + PAT role-ceiling re-resolution = resolution/ordering logic → keep P2 ≥3 for ACT-203; DI-1 backward-trace is an audit (enumeration), not a solver, but Mode-D review overhead justifies its 8.
- **H4 bundle-vs-sum:** ≥5 capability areas (mode/store/API/audit/UI) → summed per-area is the floor; do not compress below ~50.
- **H6 hidden plumbing (~15–20%):** DTOs, OpenAPI, config-reference doc, CHANGELOG, `deployment-mode-status` wiring — budget explicitly in P6.

## 5. Dependency Map

Critical path: **P1 → P2 → P3 → P5 → P6**.
- P1 (config foundation) blocks P2's `multi_user`-gated behavior and P4's gate wiring.
- P2 (token service) blocks P3 (admin API calls the service) and FR-12 agent-job binding.
- P3 (admin API) blocks P5 (UI consumes the endpoints) — sequence UI last (Risk: UI-ahead-of-backend).
- **P4 audit runs parallel to P2** (independent enumeration); rejoins at ACT-402 (needs P1 stub) and ACT-403 (needs P2+P3).
- P6 gathers all; end-of-feature karen.

```
P1 ──┬─► P2 ──► P3 ──► P5 ──► P6
     └─► P4(audit, parallel) ──► P4(gate-wire, after P1) ──► P4(regression, after P2+P3) ──► P6
```

## 6. Model Routing (per phase)

| Phase | Model | Effort | Notes |
|-------|-------|--------|-------|
| P1 | sonnet | adaptive | config resolver + regression test |
| P2 | sonnet | extended | security-sensitive: token hashing, composite auth ordering |
| P3 | sonnet | adaptive | route CRUD + scoping |
| P4 (audit) | sonnet | extended | backward-trace enumeration; **karen/opus for scope-boundary judgment** |
| P4 (remediation) | sonnet | adaptive | close enumerated leaks |
| P5 | sonnet | adaptive | additive React panels |
| P6 | sonnet (tests) / haiku→sonnet (docs) | adaptive | haiku hard-errors here → run docs on sonnet |

## 7. Open Questions for Expansion (OQ markers for implementation-planner)
- **OQ-1:** Should `token_service.py` live under `services/` (peer to `rbac_store.py`/`audit_service.py`) or `api/auth/`? Recommend `services/` for store-adjacency; confirm against existing layering.
- **OQ-2:** `access_tokens.principal_id` FK target differs by type (service_accounts.id vs users.id) — model as a nullable-pair or a single polymorphic id + `principal_type` discriminator? Recommend discriminator + app-level integrity (SQLite, no partial FK).
- **OQ-3:** DI-1 audit report path — confirm `docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md` is the canonical artifact the FR-13 status check reads.
- **OQ-4:** Does the composite middleware need a per-request `last_used_at` write (FR-6 column) on every token hit, or async/throttled to avoid a write per request? Recommend throttled/best-effort, fail-open like audit.

## 8. Plan Skeleton Pointer
- Template: `.claude/skills/planning/templates/implementation-plan-template.md`
- Output (main plan): `docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md`
- Phase files if >800 lines: `.../public-multiuser-release-activation-v1/phase-[N]-[name].md`
- Populate mandatory **Phase Summary table** + **wave_plan** frontmatter (phase model/effort defaults above). Reviewer gates: `task-completion-validator` per phase; `karen` after P2, after P4, and end-of-feature.
