---
schema_version: 2
doc_type: report
report_category: finding
title: "Findings: Public Multi-User Release Activation"
status: accepted
source: agent
created: 2026-07-22
updated: 2026-07-22
feature_slug: public-multiuser-release-activation
promoted_to: []
related_plan: docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
owner: nick
---

# In-Flight Findings — Public Multi-User Release Activation (P1–P6)

## Phase 2 Findings (composite auth chain, token service)

### Discoveries

- **M1 — token miss-path/hit-path timing-shape asymmetry.** `senior-code-reviewer`
  (REV-P2-001) flagged a residual CPU-work gap between a token *miss* (unknown
  prefix, short-circuits early) and a token *hit* (full `hmac.compare_digest`
  verification path). This is a textbook timing side-channel shape, but rated
  non-blocking: negligible under this platform's LAN-only threat model plus the
  256-bit token entropy already in use (a timing side-channel needs many
  observations to leak useful signal, and the entropy budget here is far above
  what that would require to matter in practice).
  **Recommended follow-up** (not fixed this feature): equalize CPU work on the
  miss path with a dummy `hmac.compare_digest` call against a fixed-length dummy
  value, mirroring the pattern `token_service.py` already uses for the *prefix*
  miss case — extend the same idiom to cover the full-token miss case too.

- **M2 — audit scope check bypasses the shared `require_workspace_scope` idiom.**
  `senior-code-reviewer` also flagged that the audit-log workspace-scoping fix
  (`audit_service.list_events`/`get_event`, closed as a genuine cross-tenant leak
  by the P4 DI-1 audit — see `docs/projects/research-foundry/SERVICE_CONTRACT.md`
  §19) implements its own inline workspace comparison rather than routing through
  `api/auth/scope.py`'s shared `require_workspace_scope()` helper that every other
  WKSP-304 consumer uses. Functionally equivalent (both correctly deny on
  mismatch) but **loses the advisory-mode telemetry** `require_workspace_scope`
  emits (structured WARNING logs on cross-workspace mismatch when isolation is
  advisory-only, not yet enforced) — an operator running with
  `workspace_isolation_enforcement=auto` + `auth.provider=none` would not see the
  same advisory signal for audit-log access that they would for catalog/report
  access. Non-blocking (the actual gate is correct); logged as a consistency /
  observability gap.
  **Recommended follow-up** (not fixed this feature): refactor
  `audit_service.list_events`/`get_event`'s inline comparison to call
  `require_workspace_scope()` directly, for telemetry parity with every other
  consumer of that helper.

- **karen Low — `verify_token` re-bootstraps schema per request.**
  `token_service.verify_token()` calls `rbac_store.bootstrap()` on every
  invocation (i.e. on every authenticated request when `auth.provider=local_static`
  and a token-store path is configured), which re-runs the idempotent
  `CREATE TABLE IF NOT EXISTS` schema statements each time. Correctness is
  unaffected (idempotent DDL), but this is unnecessary per-request overhead and a
  potential lock-contention point under concurrent load once real `multi_user`
  traffic exists. **This is also the concrete "measured problem" signal named as
  the promotion trigger for DF-002** (`docs/project_plans/design-specs/rbac-db-postgres-migration.md`) —
  if this bootstrap-per-request pattern becomes a measured bottleneck, it is the
  first thing to fix (cache the bootstrap check, not necessarily migrate off SQLite).

### Plan / Reality Mismatches

- None beyond what phase-2/phase-4 completion notes already capture (OQ-1/OQ-2
  resolved as planned: `token_service.py` under `services/`; single id +
  `principal_type` discriminator).

### Bugs / Gotchas

- `docs/projects/research-foundry/SERVICE_CONTRACT.md` §20/§21: the original P4
  ACT-401 edit that added §21 (DI-1 gate) was spliced into the middle of §20's
  content (rights entity model), leaving §20 without its closing `---` and its
  CLI/coordination-boundary paragraphs orphaned under §21's heading. Fixed in P6
  (ACT-604) alongside the §21 status update (`pending-human-signoff` →
  `accepted`) and the addition of §22 (admin token API, previously undocumented).

### Schema / Data Gaps

- None found beyond the DI-1 audit's own named findings (see below).

## Deferred Residual Risks (cross-reference, not a duplicate)

The DI-1 full-surface audit's headline finding — runs/claims/source-cards/evidence
bundles have no `workspace_id` concept, plus the related agent-job
`workspace_id`-spoofing finding (row 9) — is the single largest open item from this
feature. It is **load-bearing** (blocks a future adversarial multi-tenant posture)
and therefore has its own design-spec rather than living only in this findings doc:
see `docs/project_plans/design-specs/runs-evidence-workspace-isolation.md`. This
findings doc records the cross-reference per the deferred-items-and-findings
lifecycle; the full problem statement, proposed per-surface fixes, and promotion
trigger live in that spec, not duplicated here.

**Update (2026-07-23): the code remediation is implemented and tested** (DF-004,
branch `feat/df-004-runs-workspace-isolation`; see the spec's Resolution section
and `docs/dev/architecture/adr-runs-workspace-isolation.md`). Runs now carry
`workspace_id` (owner) + `visibility` (workspace|public); reads/writeback/agent-job
attribution are workspace-scoped under enforcement, advisory-and-single_user
unchanged. **The deferred item is NOT closed:** audit rows 9-12 require a formal
DI-1 re-audit + Mode D human sign-off (spec AC #4) before any deployment claims
adversarial-multi-tenant readiness. Status: remediated-in-code, pending re-audit.

## Summary

No findings in this feature required a *new* deferred item beyond the one already
tracked as a design-spec above (DF-004, `runs-evidence-workspace-isolation.md`). M1,
M2, and the karen Low finding are non-blocking hardening follow-ups, tracked here for
future pickup rather than promoted to design-specs of their own (they are scoped,
single-function fixes, not design-level decisions).
