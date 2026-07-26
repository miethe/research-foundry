---
title: "DI-1 Re-Audit — Probe 2: Workspace Isolation Enforcement-Default Trace"
mode: "E — Reviewer (read-only)"
audited_head: d71a261
scope: "WKSP-304 / DF-004 enforcement-default resolution: does isolation fail closed by default for a public/multi-tenant deployment?"
---

# Probe 2 — Enforcement-Default Trace (WKSP-304 / DF-004)

## 0. Files traced

- `src/research_foundry/api/auth/scope.py` — `require_workspace_scope()`, `resolve_workspace_isolation_active()`
- `src/research_foundry/config.py` — `deployment_mode()`, `workspace_isolation_enforcement()`, `resolve_workspace_isolation_enforced()`, `auth_rbac_enforcement()`/`resolve_rbac_enforced()`, `_deployment_mode_conditions()`, `deployment_mode_validate()`, `auth_provider()`
- `src/research_foundry/api/middleware/auth.py` — `AuthProviderMiddleware`, deprecated `TokenAuthMiddleware`
- `src/research_foundry/api/app.py` — `create_app()` wiring order (gate → middleware → state)
- `src/research_foundry/cli_commands.py` — `rf serve` (`_validate_nonloopback_bind`, gate ordering)
- `src/research_foundry/services/workspace_migration_service.py` — backfill/migration tool (no enforcement-flag read)
- `src/research_foundry/services/{catalog_service,builder_service,agent_job_service,export_service,audit_service}.py`, `api/routers/writeback.py`, `api/routers/runs.py` — enforcement call sites
- `docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md`, `docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md`
- `tests/unit/test_workspace_isolation_enforcement_flag.py`, `tests/unit/test_deployment_mode.py`, `tests/unit/test_runs_workspace_isolation.py`

---

## 1. Exact conditions: enforce vs. advisory

`require_workspace_scope(identity, record, resolve_enforcement=...)` in `scope.py`:

- `identity is None` → **immediate return `allowed=True, reason="single_operator_trust"`** (scope.py:174-177). This is the *literal first statement* — `resolve_enforcement` is never read on this path (documented "D3" invariant, scope.py:19-25).
- `identity is not None` → `enforcing = resolve_enforcement() if resolve_enforcement is not None else False` (scope.py:182). If no resolver is passed at all, behavior is byte-identical to pre-WKSP-304 advisory-only (never enforces, regardless of config).
- Given a resolver, `enforcing` is `resolve_workspace_isolation_enforced(provider, bind_host)` (config.py:787-861), gated by the `workspace_isolation_enforcement` knob (`auto`/`disabled`/`enabled`, config.py:744-785):
  - `disabled` + non-loopback `bind_host` → **raises `ValueError`** at config-read time (fail-closed refuse-to-start; config.py:843-851).
  - `disabled` + loopback → resolves `False` (advisory).
  - `enabled` → resolves `True` unconditionally.
  - `auto` (**default when unset**, config.py:770-776) → resolves `provider != "none"` (config.py:861). This is the pivotal line: **AUTO enforces the instant a real auth provider (`local_static`/`clerk`) is configured — independent of `deployment_mode`.**

So: enforcing = `identity is not None` AND a resolver was actually wired at the call site AND (`workspace_isolation_enforcement=enabled`, or (`=auto` and `auth.provider != "none"`)).

**Call-site wiring confirmed present** (not just inert plumbing) in: `catalog_service.py` (require_workspace_scope + `_isolation_active` query filters, lines 99/339/1397/1698/1808/2022/2085), `builder_service.py` (lines 73/339/360-365), `agent_job_service.py` (lines 301-320/987-994), `export_service.py` (lines 1147-1171 — this is what backs `GET /api/runs*`), `audit_service.py` (lines 47-58/321/421), `api/routers/writeback.py` (lines 84/313-318). All pass `resolve_enforcement=lambda: resolve_workspace_isolation_active(paths)` or the service's bound `_isolation_active`, i.e. a live per-request re-read of `FoundryConfig`, not a stale cached flag.

## 2. Deployment-mode × provider × bind_host decision table

| deployment_mode | auth.provider | bind_host | isolation resolves | Default when operator sets nothing | Evidence |
|---|---|---|---|---|---|
| unset / `single_user` | `none` | loopback (127.0.0.1) | **advisory** (AUTO, provider==none) | **THE ACTUAL SHIPPED DEFAULT** — LAN/NUC deployment | config.py:861; test `test_auto_none_provider_is_false` |
| unset / `single_user` | `none` | non-loopback (0.0.0.0) | N/A — **cannot start**: `rf serve` `_validate_nonloopback_bind` (Gate 1) refuses to bind without auth enabled | blocked | cli_commands.py:161-167 |
| unset / `single_user` | `local_static` or `clerk` | loopback or non-loopback | **enforced** (AUTO, provider!=none) | Enforced automatically the moment a real provider is configured — **no `deployment_mode=multi_user` needed** | config.py:861; test `test_auto_local_static_is_true` |
| unset / `single_user` | `none` (legacy `viewer.auth_mode=token` fallback) | non-loopback (0.0.0.0) | **advisory** (AUTO reads literal `auth.provider`, which is still `"none"`) — **even though the legacy fallback middleware DOES authenticate and DOES populate `request.state.identity`** (app.py:311-341) | Reachable and self-consistent today only because the legacy fallback hard-codes one identity/workspace (`workspace_id="default"`) for every caller — see §4 residual risk | config.py:787 uses `config.auth_provider()` output verbatim, not "is any auth actually active" |
| `multi_user` | `none` | any | **startup refuses** (`ValueError`, condition a) | N/A — cannot boot | config.py:1042-1052; deployment_mode_validate |
| `multi_user` | `local_static`/`clerk`, RBAC/isolation not overridden | any | **enforced** (preset defaults both to `enabled`) — AND additionally gated on FR-13 DI-1 two-part ack (condition d) | Startup refuses unless `auth.di1_audit_acknowledged=true` in foundry.yaml AND the audit artifact frontmatter `status: accepted` | config.py:164-171, 1102-1125 |
| `multi_user`, RBAC or isolation explicitly set to `disabled` | any | non-loopback | **startup refuses** (`ValueError`, before deployment_mode_validate even runs, from `resolve_rbac_enforced`/`resolve_workspace_isolation_enforced` themselves) | N/A | config.py:716-723, 844-851 |

RBAC (`auth_rbac_enforcement`, orthogonal gate) is *stricter by design* than isolation's AUTO: `resolve_rbac_enforced`'s AUTO/ENABLED branches both return `True` unconditionally (config.py:726-740) — RBAC's provider-sensitivity is realized instead via the identity-None passthrough inside `require_role` (not read during this probe, but referenced consistently in scope.py's docstring). Isolation's AUTO branch is explicitly documented (config.py:802-814) as differing from RBAC's for this reason.

## 3. Is there a startup gate blocking public/multi_user with advisory-only isolation?

**Two different gates, only one of which is mandatory for a "public" deployment:**

1. **Non-loopback bind gate (`_validate_nonloopback_bind`, mandatory, unconditional)** — `rf serve --bind-host 0.0.0.0` (or any non-loopback host) **always** requires `is_auth_enabled()` (real `auth.provider` or legacy `viewer.auth_mode=token`) plus at least one resolvable token, checked **before** any port opens (cli_commands.py:3093-3110, `create_app` itself does not re-check — comment at app.py:250-253 states the CLI gate is the canonical check). This gate is orthogonal to `deployment_mode` and fires regardless of it.
2. **`deployment_mode_validate` gate (opt-in — only fires when `deployment_mode=multi_user`)** — this is the ONLY gate that checks the DI-1 audit two-part ack (FR-13, condition d) and forces RBAC/isolation to the `enabled` literal (not just AUTO-derived). **`deployment_mode` defaults to `single_user` and nothing in the codebase — not the CLI, not `create_app`, not the non-loopback bind gate — ever infers `multi_user` from `bind_host=0.0.0.0` or from `auth.provider != "none"`.** `deployment_mode_validate()` is a documented no-op whenever `mode != "multi_user"` (config.py:1208-1210).

**Conclusion: an operator CAN run a genuinely public (LAN/internet-reachable, token-authenticated, multiiple distinct identities via `auth.local_static.tokens`) deployment while leaving `deployment_mode` at its default `single_user` — and per §2 that specific configuration still gets isolation *enforced* (AUTO fires because `auth.provider != "none"`), but it NEVER triggers the DI-1 audit acknowledgment gate, and RBAC/isolation are only AUTO-derived rather than the hardened `enabled` literal.** The PRD (`public-multiuser-release-activation-v1.md` §"Goals", FR-1/FR-4) frames `deployment_mode: multi_user` explicitly as "one switch" the operator must *choose* to flip — it is governance/ergonomics sugar over the five knobs, not something the runtime forces based on network topology. This is corroborated verbatim: "Outcome 1: An operator flips one switch... instead of independently tuning..." — i.e. tuning the knobs by hand and skipping the switch remains a first-class, unblocked path.

## 4. Identity-None / no-auth path — fail-open surface

`identity is None` short-circuits to `allowed=True` unconditionally (§1). On the HTTP path, `request.state.identity` is populated **only** when `AuthProviderMiddleware` runs and authentication succeeds; it 401s (never lets a None-identity request through) whenever it is installed at all (middleware/auth.py:217-221). `AuthProviderMiddleware` is installed whenever `auth.provider != "none"`, OR the legacy fallback `viewer.auth_mode == "token"` (app.py:255-341) — both paths now populate `request.state.identity` (the once-deprecated `TokenAuthMiddleware`, which never set `request.state.identity`, is dead code — unreferenced by `create_app`).

**Consequence: on the HTTP path, `identity is None` is reachable by an unauthenticated caller only when `auth.provider == "none"` AND `viewer.auth_mode != "token"` — i.e., truly no auth mechanism is configured at all.** That state is itself blocked from ever binding non-loopback by the `_validate_nonloopback_bind` gate (§3.1) — Gate 1 requires `is_auth_enabled()` or an explicit `--auth-mode token` CLI override, either of which populates identity via the legacy-fallback branch. So **the identity=None fail-open branch is reachable over HTTP only on a loopback bind with no auth configured at all — the documented, intended single-operator-trust LAN/NUC default.** It is not reachable on a genuinely public (non-loopback) bind through any code path this probe traced.

It **is** reachable, by design, on the **CLI/service-layer path** — every `rf` CLI invocation calls services with `identity=None` (there is no HTTP identity to resolve locally), which is the intended single-operator-trust semantics for local, unauthenticated CLI use and is out of scope for a "public deployment" threat model.

**A distinct, narrower fail-open finding (legacy path, low current severity):** `resolve_workspace_isolation_enforced()`'s AUTO branch keys on the literal `auth.provider` config value (`config.py:861`), not on "is any authentication mechanism actually active." When an operator uses **only** the legacy `viewer.auth_mode: token` / `auth_token_env` fields (never touching the newer `auth.provider` block), `auth.provider` still resolves to `"none"` even though the legacy fallback middleware is installed, does 401 unauthenticated callers, and does populate `request.state.identity` (app.py:311-341, hardcoded `user_id="legacy_token_user"`, `workspace_id="default"`, `roles=["owner"]`). Isolation's AUTO resolver sees `provider="none"` and returns advisory (`False`) for this configuration — the resolver and the actual middleware-installation decision are driven by different signals. This is currently **inert** as an attack surface because the legacy fallback hardcodes exactly one identity/workspace for every caller (there is nothing to isolate — every legacy-token holder IS `workspace_id="default"`), but it is a latent inconsistency: if the legacy single-token model is ever extended to multiple tokens/workspaces without updating this resolver, isolation would silently stay advisory on a real non-loopback multi-identity deployment.

## 5. The larger, higher-severity residual risk this trace surfaces: DI-1 audit acceptance is scope-limited and pre-dates DF-004

The FR-13 artifact half of the `multi_user` gate reads `docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md` and only checks `status: accepted` (config.py:979-1004) — it does **not** re-derive or re-validate the audit's content against current code; it trusts the frontmatter literally. That document's own signed acceptance is explicitly scoped:

> `signoff.scope_accepted`: `"trusted-cohort multi_user only (NOT adversarial multi-tenant isolation for runs/evidence)"`
> `authorization_scope`: "...does NOT certify tenant isolation for runs, claims, source cards, or evidence bundles: rows 10-12 below found that the run/evidence-bundle data model has no workspace_id concept at all, so every run in the install is listable and readable... by any authenticated caller in ANY workspace... This acceptance does NOT authorize an untrusted multi-tenant deployment."

Per-memory and confirmed live at HEAD (`api/routers/runs.py:164-214`, `export_service.list_runs`/`_enforce_existence_gate` with `identity=`, `require_workspace_scope` wiring in `export_service.py:1147-1171`, and `tests/unit/test_runs_workspace_isolation.py` covering cross-workspace 404, list filtering, public-visibility escape, and launch-time workspace stamping), **the runs/claims/evidence gap the audit flagged (rows 10-12) has since been code-remediated (DF-004)** — but the accepted audit document has not been re-issued or re-signed against that remediation, and the FR-13 gate has no mechanism to detect that the artifact it's trusting is stale relative to HEAD. The gate satisfies its own literal condition ("status is accepted") but the human scope statement it is trusting explicitly disclaims adversarial multi-tenant safety, and no formal re-audit closing that disclaimer has landed. This is a governance/process gap, not a code defect — but it directly bears on the pivotal question: **"REMEDIATED-IN-CODE" does not currently equal "audit says this deployment posture is adversarially safe."**

## 6. Bottom line

**Fail-closed by default for public multi-tenant: CONDITIONAL.**

- For the primary/intended real-world path — the operator configures `auth.provider=local_static` (or `clerk`) with real per-caller tokens, which is *required* to legally bind non-loopback at all — **workspace isolation enforcement turns on automatically via the `auto` default**, with zero additional configuration and independent of `deployment_mode`. This is a materially fail-closed default for the primary path and is directly test-covered (`test_auto_local_static_is_true`).
- BUT: (a) nothing forces `deployment_mode=multi_user` for that deployment, so the FR-13 DI-1 human-audit acknowledgment gate — the one mechanism meant to force a documented, scope-explicit human sign-off before "public" goes live — is **entirely bypassable simply by not setting `deployment_mode`**; (b) the one audit document that *does* exist and *is* marked "accepted" explicitly disclaims adversarial multi-tenant safety for runs/claims/evidence and has not been re-validated against the DF-004 remediation that (per code and tests) appears to have closed that exact gap; (c) a narrow, currently-inert legacy-auth-mode inconsistency exists between the isolation AUTO resolver's `auth.provider`-literal signal and the actual (legacy-fallback) authentication behavior.
- No code path was found that lets an operator explicitly *disable* isolation on a non-loopback bind (that is hard-blocked, config.py:843-851) — the fail-open surfaces here are about **scope of what's covered / whether the intended governance checkpoint is mandatory**, not about a raw "enforcement=off on the open internet" toggle.

Per the Mode-D boundary in this project's rules: this is a code-and-config trace, not a live adversarial test. Whether a specific real deployment is actually safe requires a human to (1) decide whether `deployment_mode=multi_user` (and its DI-1 gate) should be made mandatory whenever `bind_host` is non-loopback rather than opt-in, and (2) commission a fresh DI-1 re-audit against current HEAD before treating any public deployment as adversarially safe for the runs/claims/evidence surface.

## 7. Residual risks (not fully resolved by this read-only trace)

1. `deployment_mode=multi_user` (and thus the DI-1 ack gate) is operator-opt-in, not inferred from `bind_host`/network topology — a fully public, multi-identity deployment can run indefinitely under `single_user` semantics without ever satisfying FR-13.
2. The accepted DI-1 audit document's signed scope statement explicitly disclaims adversarial multi-tenant safety for runs/claims/evidence; no re-audit has re-validated the DF-004 code remediation against that disclaimer, and the FR-13 gate cannot detect that the trusted artifact is stale.
3. Legacy `viewer.auth_mode=token` deployments make the isolation AUTO resolver's `auth.provider`-literal check diverge from actual authentication reality; currently inert only because the legacy path is single-identity/single-workspace by construction — would silently regress to advisory-only if that assumption is ever broken.
4. `workspace_migration_service.py` backfill (stamping missing `workspace_id` → `"default"`) is a separate, un-gated operational step: any legacy record never backfilled will simply be denied (404) once isolation is enforcing (fail-secure direction, but an availability/operational risk, not a security one, worth flagging to an operator turning enforcement on for the first time).
5. This trace did not independently verify `require_role`'s identity-None passthrough (referenced but not opened) nor re-derive whether every `runs`/`claims`/`evidence` write surface (not just the read paths this probe sampled) is covered by the DF-004 remediation — a full-surface confirmation would require re-running (or commissioning) the DI-1 audit itself, which is explicitly a human/Mode-D action per this document's own gate design.
