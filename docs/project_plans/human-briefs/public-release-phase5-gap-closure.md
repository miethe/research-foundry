---
schema_name: ccdash_document
schema_version: 2

doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans

id: "BRIEF-public-release-phase5-gap-closure"
title: "Public Release Phase 5 — Hardening Gap-Closure"
status: draft
category: human-briefs

feature_slug: public-release-phase5-gap-closure
feature_family: public-multiuser-release
feature_version: "post-P5"

prd_ref: null
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
intent_ref: null
epic_ref: null

related_documents:
  - docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md
  - docs/project_plans/human-briefs/public-multiuser-p5-auth-rbac.md
  - docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
  - docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1.md
  - docs/project_plans/reports/audits/assertion-ledger-activation-di1-scoped-audit.md

owner: nick
contributors: []

audience: [humans]

priority: high
confidence: medium

created: 2026-07-18
updated: 2026-07-18
target_release: ""

tags: [human-brief, public-release, auth, rbac, di-1, mode-d, gap-closure]
---

# Public Release Phase 5 — Hardening Gap-Closure — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-18

---

## 1. Current State (code-truth, verified 2026-07-18)

- **Phases 0–4** of `public-multiuser-release-handoff-v1.md` shipped: `/catalog`, `/builder`,
  embedded-agent routes and their backend routers are live.
- **`public-multiuser-p5-auth-rbac-v1`** (46-pt Tier 3 plan: auth-provider port, RBAC enforcement,
  workspace migration, Clerk adapter, audit log, rate limits/admin/sharing) is `status: completed`.
  Verified on disk: `api/auth/adapters/{local_static,clerk,oidc}.py`, `api/auth/rbac.py`
  (`require_role`), `services/share_store.py` (publish preview / share links) all exist and are
  wired.
- **RBAC + workspace-isolation (WKSP-304) enforcement are code-complete but config-gated to
  `auto`**: both `auth.rbac_enforcement` and `workspace_isolation_enforcement` resolve to
  *advisory* the moment `auth.provider == "none"` (today's LAN-node default — "fully open,
  single-user"), and to **fully enforced** the moment an operator sets `auth.provider` to
  `local_static` (multi-token), `clerk`, or `oidc`. **This means the "RBAC enforcement flip" is a
  one-line config + operator decision, not missing engineering** — the two gates share the same
  `auto` idiom and both flip together off one decision.
- **Assertion-ledger v1 + activation (Tier 3)** sealed: P1–P6 on `main`, `karen` feature-end
  approved. DI-1-scoped audit (write-sites this feature touched) complete, 2 findings (F1/F2)
  remediated same-pass.

## 2. Remaining Phase-5 Work Items

| Item | State | Type |
|---|---|---|
| Auth-provider **activation decision** (`local_static` vs `clerk` vs `oidc`) | Code done; *decision* + live validation not done | Mode D |
| RBAC enforcement flip (`auth.rbac_enforcement` off `auto`) | Cascades automatically from the provider decision above | Mode D |
| WKSP-304 isolation flip (`workspace_isolation_enforcement`) | Cascades automatically from the provider decision above | Mode D |
| OIDC adapter — **live IdP validation** | Protocol seam (`oidc.py`) exists, untested against a real IdP | Mode D |
| Clerk adapter — **live validation** | Adapter exists, dark-by-default; blocked on FU-3 (paid-plan procurement) | Mode D (partial — procurement is not engineering) |
| Public sharing / publish-preview gates | `share_store.py` exists; needs a hardening + regression pass against the Phase 5 acceptance bar (§11 of the handoff spec) | Standard (Tier 1–2) |
| Report-body sensitivity fail-closed | Source-evidence redaction exists; report body / catalog summary / agent-output equivalent needs the same fail-closed verification pass | Standard, but touches sensitivity — treat conservatively |
| **DI-1 full-project write-site audit** | **Not started.** Only feature-scoped (assertion-ledger) coverage exists. This is the hard pre-multi-tenant-deploy gate per the WKSP-304 AAR (a prior scoping pass was later found incomplete — 2 Mode-D leaks surfaced post-hoc). | Mode D — blocks the deploy decision, not just a code change |
| E2E coverage (catalog/builder/agents, static + live API modes) | Partial; full sweep across all 4 shipped Phase 0–4 surfaces not confirmed complete | Standard |

## 3. Mode D Items — Cannot Be Autopiloted

These require explicit human sign-off before any agent proceeds, per `.claude/rules/delegation-modes.md`:

1. **Auth-provider activation decision** — flips two independent enforcement gates project-wide;
   this is the single highest-leverage decision in this brief (see §1).
2. **DI-1 full-project audit** — the WKSP-304 AAR is explicit that a prior "complete" scoping claim
   on this exact surface was wrong; do not let an agent self-certify this audit's completeness.
   Human review of the audit's scope-boundary statement is required before treating it as the gate.
3. **Live OIDC/Clerk validation against a real IdP/tenant** — credential handling, first live-fire
   risk.
4. **Public sharing/publish-preview exposure gate sign-off** — anything that makes report content
   reachable outside the operator's own session needs a human "yes, this is safe to expose" before
   it ships enabled-by-default.

## 4. Unresolved Open Questions Needing an Operator Decision

From `public-multiuser-release-handoff-v1.md` §14 (all still open):

- **Auth provider for public launch**: `local_static` (multi-token, no external dependency),
  OAuth/OIDC (generic, needs an IdP), or Clerk (adapter exists but paid-plan procurement — FU-3 —
  is unresolved)? This decision directly resolves item 1 in §3.
- **SQLite vs Postgres** for the shared catalog store: SQLite for homelab/single-node, Postgres
  required from day one for public SaaS scale? No decision recorded since the design spec was
  written.
- **`/library` fate**: does it stay as "Reusable Outputs" alongside `/catalog`, or fully retire?
  Phase 0 deferred this; still open.
- **First agent provider**: OpenAI Agents SDK or Claude Agent SDK for the embedded-research-agent
  path (Phase 4, already shipped with *one* provider per the phase's own acceptance criteria — the
  design spec's open question was whether the *second* provider matters before public launch, and
  that has not been revisited).

## 5. Recommended Sequencing

1. **Resolve the auth-provider decision first** (§4) — it is the pivot point for two of the four
   Mode D items in §3 and should not be deferred behind other work.
2. **Run the DI-1 full-project audit** in parallel — it does not depend on the provider decision
   and is the longest-lead-time item; treat the assertion-ledger DI-1-scoped audit's method
   (backward-trace every `AssertionRegistry`/`AssertionMaterializer` construction to a
   `resolve_or_deny` gate) as the template, expanded repo-wide.
3. **Once the provider decision lands**: flip `auth.rbac_enforcement` / `workspace_isolation_enforcement`
   off `auto` in a controlled config change, then run live IdP/Clerk validation (Mode D item 3)
   against that specific provider only — don't validate all three providers, only the chosen one.
4. **Sharing/publish-preview hardening pass + report-body sensitivity fail-closed pass** — these
   can run as standard Tier 1–2 contracts once the DI-1 audit confirms no upstream write-site gaps
   feed into them.
5. **E2E sweep last** — it is the cheapest to run and most valuable once the above are stable
   (running it earlier just means re-running it after every gap closes above).
6. Resolve the three remaining open questions (`SQLite`/Postgres, `/library`, second agent
   provider) opportunistically — none block the Mode D items above and can be decided on their own
   timeline.
