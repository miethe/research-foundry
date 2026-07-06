---
schema_version: 2
doc_type: report
report_category: audit
title: "Codex Adversarial Plan Review — Public Multi-User P4/P5"
status: accepted
source: codex-gpt-5.5
created: 2026-07-06
updated: 2026-07-06
feature_slug: public-multiuser-p4p5-foundations
reviewer: "Codex gpt-5.5 (read-only, effort medium)"
verdict: SHIP-WITH-FIXES
related_documents:
  - docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
  - docs/project_plans/PRDs/features/public-multiuser-p4-agents-v1.md
  - docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p4-agents-v1.md
  - docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
---

# Codex Adversarial Plan Review — P4/P5

An independent read-only adversarial pass (Codex `gpt-5.5`, effort `medium`) over the SPIKE, both
PRDs, both decisions-blocks, and both implementation plans, with code spot-checks against
`adapters/*`, `api/middleware/auth.py`, `services/governance.py`, and `services/catalog_service.py`.

**Verdict: SHIP-WITH-FIXES** — no acceptance bullet fully dropped; five must-fix items, all applied
before this planning set was finalized. Findings 3 and 4 were caught by the reviewer reading the
actual code, not just the plans.

## Resolution table

| # | Finding (severity) | Resolution | Where |
|---|--------------------|-----------|-------|
| 1 | **ADR-002 false premise** (high): "static adapters stay in-process" is untrue — `notebooklm.py` already `subprocess.run`s with no `env=` filter (unscoped ambient inheritance). | Corrected SPIKE G1 + ADR-002 to acknowledge notebooklm's pre-existing subprocess; reframed isolation as designed-in for the SDK agent-job adapters only; added SPIKE **FU-5** (harden notebooklm cred handling separately, not re-architected in P4); mirrored into P4 decisions-block D4. | SPIKE, P4 decisions-block |
| 2 | **Under-specified security APIs** (high): redaction firewall is new work, not reuse of `_redact`; child-cred-loading contract missing. | P4.2 phase now specifies a recursive `redact_payload(obj) -> sanitized \| raises` sanitizer (nested dicts/SSE chunks/artifact+static-export JSON) routed through every write site, and the child-side **read-once → unlink, never `os.environ`, never tool-readable config** credential contract; P4 AC-5 gained an explicit `target_surfaces` list. | P4 plan phase-1-2, P4 PRD |
| 3 | **Missing exposure gate** (high): P4 ships agents with unenforced workspace fields; enabling `/agents` on shared LAN pre-P5 leaks cross-user data. | Added a HARD release/exposure constraint: `agents.enabled` default **false**; may be true pre-P5 only in loopback/single-operator mode; shared/LAN/public exposure REQUIRES P5.2 (RBAC) + P5.3 (isolation) green. `openai_agents` (P4.6) especially loopback-only until P5. | P4 plan parent + phase-6-7, SPIKE verdicts |
| 4 | **Schema inconsistency** (high): PRD says workspace columns "already exist broadly," but `catalog_items` lacks `workspace_id`. | Corrected PRD + parent plan + decisions-block D7: mixed schema state — only `builder_service` draft YAML + derived `catalog_report_drafts` carry the fields; `catalog_items` needs the column **added first**, then migration+enforcement. Aligned to the already-correct P5.3 phase file. | P5 PRD, P5 plan parent + decisions-block |
| 5 | **Route-only test coverage** (med-high): RBAC/audit/credential tests miss CLI, service-layer, SSE/event, and static-export surfaces; audit fails open silently. | Added FR-6a/RBAC-006 (CLI + service-layer mutation surface enumerated, classified admin-only/single-operator-trust, static contract test) and FR-8a/AUDIT-004 (audit degraded-health probe + durable state + admin warning + public-exposure-requires-writable gate); renamed "100%/no-direct-write" overclaims to the HTTP-routed surface; expanded AC-1/AC-4 + P5.9 scope to CLI/service/audit-event/static-export. Point totals updated 46→47.25. | P5.2, P5.5, P5.9, P5 PRD |

## Notes carried forward (not blockers)

- Codex confirmed the P5.3 migration is **better de-risked than the parent PRD implied** (dry-run,
  manifest rollback, byte-identical fixture restoration, idempotency, mechanical approval artifact).
- Codex suggested P4's Mode-D human gates copy P5.3's approval-artifact strictness — folded into the
  P4 gate rows.
