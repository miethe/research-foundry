---
schema_version: 2
doc_type: spike
title: "Public Multi-User P4/P5 Foundations — Auth-Provider Abstraction & Agent-Job Credential Isolation"
status: completed
created: 2026-07-06
updated: 2026-07-06
feature_slug: public-multiuser-p4p5-foundations
complexity: high
risk_level: high
estimated_research_time: "narrow (2 seams)"
owner: nick
orchestrator: opus-4-8
research_questions:
  - "SEAM-1: How do we make auth modular/swappable/BYO with Clerk as first provider, given RF is a self-hosted FastAPI+SPA on a LAN/partially-air-gapped node?"
  - "SEAM-2: What credential-isolation boundary do P4 embedded-agent jobs require so raw provider keys never reach the browser, job artifacts, or cross-profile adapters?"
related_documents:
  - docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md
  - docs/project_plans/implementation_plans/public-multiuser-p2p3-opus-handoff.md
  - docs/project_plans/exploration/credential-process-isolation/credential-process-isolation-charter.md
prd_ref: null
plan_ref: null
feeds:
  - docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
  - docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
---

# SPIKE — Public Multi-User P4/P5 Foundations

Narrow, timeboxed SPIKE (2 seams) gating the P4 (Embedded Agent Research) and P5 (Public
Multi-User Hardening) plans. Everything else in P4/P5 is already settled by spec §9/§11/§12.4-5
of `public-multiuser-release-handoff-v1.md`; only these two seams carried genuine unknowns:

1. **SEAM-1 (P5):** auth as a swappable/BYO abstraction with **Clerk** as the operator's chosen
   provider, on a **self-hosted LAN** deployment.
2. **SEAM-2 (P4):** credential-isolation boundary for embedded-agent jobs.

Both legs were investigated code-grounded (backend-architect, Sonnet, design-only). Findings
below are the system of record for the two decisions-blocks; the PRDs consume the ADRs.

---

## SEAM-1 — Auth-Provider Abstraction (Clerk-first, BYO/local seam)

### Findings (live Clerk docs + RF code)

| # | Finding | Confidence |
|---|---------|-----------|
| F1 | **Backend JWT/JWKS verification needs no Node SDK.** Clerk documents manual verification (`clerk.com/docs/guides/sessions/manual-jwt-verification`): token from `__session` cookie or `Authorization` header → fetch JWKS (`<frontend-api>/.well-known/jwks.json`) → verify RS256 + `exp`/`nbf`/`azp`. Pure-Python via PyJWT + `cryptography` with JWKS caching; per-request verify is networkless once `jwtKey` is cached. | HIGH |
| F2 | React SDK `@clerk/clerk-react` is Clerk's flagship (`ClerkProvider`, `SignIn`, `UserButton`, `useAuth`/`useOrganization`). | MED-HIGH |
| F3 | **Organizations → RBAC:** 2 default roles + up to **10 custom roles/instance** (fits RF's 5), but custom roles **require a paid plan for production** (free in dev only). | HIGH |
| F4 | **Enterprise SSO** (SAML: Azure AD/Okta/Google Workspace/any SAML IdP; OIDC federation) is IdP-*into*-Clerk brokering — Clerk stays the token issuer of record, not a pass-through to a self-hosted IdP. | HIGH |
| F5 | **No self-hosted / on-prem Clerk.** Production requires a domain you own + public DNS pointed at Clerk. No air-gapped mode. Browser sign-in requires reaching Clerk's hosted Frontend API. | HIGH |

**Load-bearing consequence of F5:** Clerk cannot serve this deployment's own stated LAN /
partially-air-gapped target. Therefore Clerk is an *adapter*, not the foundation. The abstraction
is the deliverable; Clerk is opt-in on top of it.

### ADR-001 — `AuthProvider` port with Clerk-first + local/BYO seam

**Status:** accepted (SPIKE verdict) · **Phase:** P5 · **Mode:** D (auth)

**Decision.** Introduce an `AuthProvider` **port** at `src/research_foundry/api/auth/provider.py`,
mirroring the existing `adapters/base.py` Protocol + registry idiom:

- `AuthIdentity{ user_id, workspace_id, roles }` is the provider-neutral request identity.
- `AuthProvider` Protocol: `authenticate(request) -> AuthIdentity | None`; `register()` /
  `get_provider(name)`.
- Concrete adapters:
  - **`local_static`** (DEFAULT, zero new dependency, air-gapped): generalizes today's
    `TokenAuthMiddleware` — static per-token → role mapping. This is the P5 baseline.
  - **`clerk`** (OPT-IN): pure-Python JWKS verification; Clerk Organizations' 5 custom roles
    mapped 1:1 to RF roles.
  - **`oidc`** (BYO): direct OIDC to an operator's on-prem IdP for orgs that want SSO without
    Clerk. (Adapter seam defined in P5; concrete impl may defer — see follow-ups.)
- **Selection** via `foundry.yaml: auth.provider`; `create_app` wires the middleware from the
  registered provider so route/RBAC code **never branches on provider identity**.
- **Invariants preserved:** `auth_mode="none"` still adds no middleware; 401s stay generic;
  the **404-no-existence-leak** decision stays a route-layer choice over `request.state.identity`
  (this also closes [[runs-api-no-sensitivity-existence-gate]] under the enforced-identity path).

**Alternatives considered.** Clerk-only (rejected — hard-blocks the air-gapped LAN target);
RF-built full auth server as default (rejected — reinvents a security-critical subsystem; kept
only as the `local_static` fallback); OIDC-only / no Clerk (rejected — loses Clerk's managed
Organizations UI for the primary public target).

**Consequences.** (+) swappable, no call-site churn, matches existing adapter idiom, works
air-gapped out of the box. (−) Clerk custom roles need a paid plan for production; (−) two+
providers to test (extend the `p5-auth-header.test.ts` pattern, parametrized by provider); (−)
**D12's nullable `workspace_id`/`created_by` must become enforced — a real data migration.**

**Frontend.** An auth-context abstraction wraps the app: Clerk React components (`ClerkProvider`/
`SignIn`) when `provider=clerk`, a local login form when `provider=local_static`, nothing when
`auth_mode=none`. **Static-export mode has no server → degrades to read-only public** (already
pre-gated at export; no client-side auth).

**Verdict: CONDITIONAL GO.** Ship the port + `local_static` as the P5 baseline (works air-gapped,
no new dep). Ship `ClerkAuthProvider` **opt-in**, gated on: confirmed outbound internet + a public
domain + budget for Clerk's paid custom-roles. **Never default or sole**, because Clerk cannot
serve this spike's own LAN/air-gapped target.

---

## SEAM-2 — Agent-Job Credential Isolation (P4)

### Findings (grounded against `adapters/base.py`, `claude_agent_sdk.py`, `litellm_router.py`, `governance.py`, charter)

| # | Finding | Confidence |
|---|---------|-----------|
| G1 | **Ambient-env cross-profile bleed.** Adapters are in-process imports (`base.py` gates on `importlib.util.find_spec`; no `subprocess`/`Popen` anywhere); `litellm_router.py` reads keys from `dict(os.environ)`. Any in-process adapter can read any key in `os.environ` regardless of declared `key_profile`. `governance.py::no_work_keys_for_personal_runs` checks the *declared profile name*, not key material — it cannot catch this. | 0.8 |
| G2 | **Artifact / event-stream leakage.** `AdapterResult.artifacts`/notes serialize via `dumps_yaml`/`append_jsonl` into the run trace, which the runs-viewer statically exports to the browser. No write-time redaction guard exists — only `scan_secrets`/`scan_paths` invoked as a post-hoc *scan*. | 0.75 |
| G3 | **Prompt-injection exfiltration.** `openai_agents` is spec'd as server-owned orchestration with tools + a live tool-execution loop — a genuinely new risk class vs today's static adapters (`gpt_researcher`, `paperqa2`, …), which the credential-isolation charter itself rates low-risk. | 0.7 |
| G4 | **P4 is greenfield.** No `openai_agents.py` adapter exists yet → isolation can be designed in, not retrofitted. | HIGH |

### ADR-002 — P4 agent-job credential isolation (subprocess, scoped narrowly)

**Status:** accepted (SPIKE verdict) · **Phase:** P4 · **Mode:** D (credentials)

**Decision (GO, scoped to P4 agent jobs ONLY).** One **subprocess per agent job** (`openai_agents`
/ `claude_agent_sdk`), spawned at job launch with a per-job resolved credential set delivered via a
**temp file** (`0600`, job-scoped path, unlinked immediately after the child reads it) — **not** an
env var, since env inheritance into any tool-spawned grandchild reintroduces the leak. **Existing
static adapters** (`gpt_researcher`, `paperqa2`, `litellm_router`, `opencode`, `arc_council`,
`notebooklm`) **stay in-process** per the charter's no-go rationale — this ADR does not reopen the
RF-wide isolation question.

**Credential firewall.** Reuse `governance.py`'s `scan_secrets`/`_redact` as a **write-time guard**
on artifacts + event payloads (not just post-hoc scan). Key **fingerprint = salted HMAC** (server
pepper, not a raw prefix hash — low-entropy prefixes are guessable), truncated ~12 hex chars,
landing in both the run trace (`_trace`) and CCDash telemetry alongside existing `key_profile_used`.

**Allowlist + HITL.** Extend the job schema's `policy_snapshot` with `allowed_tools` / `data_scopes`,
enforced via each SDK's native guardrail/permission hooks. Generalize `work_writeback_requires_review`
into an `agent_job_output_requires_review` rule: outputs land in **job-scoped staging**; promotion
(file write, writeback, sharing, catalog acceptance) requires an **exit-code-7 `HUMAN_REVIEW`**
approval gate *after* the deterministic governance pass — one approval per job.

**Alternatives considered.** In-process-only scoping (rejected as *sole* control — insufficient
against a live tool-use loop/injection; retained as the fallback if spawn cost proves prohibitive);
env-var delivery (rejected — reinherits into tool subprocesses); governance-scan-only (rejected —
post-hoc, can't stop mid-run exfiltration).

**Consequences.** (+) bounded blast radius; no ambient-env exposure to grandchildren. (−) new
spawn code path (latency unmeasured — named follow-up); (−) crash-safe credential-file cleanup must
be tested; (−) the server pepper is itself a credential requiring a storage decision.

**Verdict: GO** on subprocess isolation for P4 agent jobs; in-process scoping is the documented
fallback if a spawn-latency prototype shows prohibitive cost.

---

## Consolidated Verdicts & Handoff

| Seam | Verdict | Feeds | Load-bearing decision |
|------|---------|-------|----------------------|
| SEAM-1 auth | **Conditional GO** | P5 plan | Auth-provider *port* is the deliverable; `local_static` default; Clerk opt-in; `oidc`/BYO seam defined |
| SEAM-2 creds | **GO** | P4 plan | Subprocess-per-agent-job + temp-file creds; static adapters stay in-process; write-time firewall + HMAC fingerprint + HITL exit-7 gate |

### Mode-D human sign-off gates (must fire during execution — encode in both decisions-blocks)

**P4 (credentials):** (1) approval before writing any subprocess-spawn / credential-file code;
(2) approval before the first live job with real provider keys; (3) approval verifying the
redaction guard against a real run trace; (4) explicit sign-off on **pepper storage location**.

**P5 (auth):** (5) approval before enforcing the `workspace_id`/`created_by` migration (data
migration on existing records); (6) sign-off that server-side RBAC (not UI hiding) enforces catalog
visibility before any public/LAN exposure; (7) sign-off on Clerk secrets handling if the Clerk
adapter is enabled.

### Open follow-ups (carry into plan Deferred Items, not blockers)

- **FU-1** Spawn-latency micro-benchmark for the agent-job subprocess model (validates GO vs fallback).
- **FU-2** Concrete `oidc`/BYO adapter implementation may defer past P5 v1 if no on-prem-IdP consumer exists at ship (the *seam* still lands in P5).
- **FU-3** Clerk paid-plan procurement is an operator action, not an engineering task — Clerk adapter ships behind a config flag, dark by default.
- **FU-4** Deferred sensitivity items P5 must also close: [[runs-api-no-sensitivity-existence-gate]]; the P3 blank-origin-draft body-sensitivity residual (needs a global source index); draft→run/claim reverse catalog links.
