---
it_schema: 1
feature_slug: intent-workspace-isolation
title: "Research-intent workspace isolation (DF-004 sibling) — implementation plan"
doc_type: implementation_plan
status: not_started
planning_maturity: draft
tier: 3
priority: P1
points: 16
risk_level: high
context_class: C3
created: 2026-07-31
prd_ref: null
related_documents:
  - docs/project_plans/design-specs/runs-evidence-workspace-isolation.md
  - docs/dev/architecture/adr-runs-workspace-isolation.md
  - docs/dev/architecture/workspace-migration-runbook.md
  - docs/project_plans/implementation_plans/features/public-multiuser-release-activation-v1.md
  - .claude/worknotes/research-foundry-operator-mcp/m3-delivery-notes.md
intenttree_node: node_01KYWYJR5PNBZYVDETQ89RWJZ8
acceptance_criteria:
  - "research_intent carries workspace_id, stamped from identity, never from caller input."
  - "All 39 pre-existing intents carry a workspace_id after backfill; rollback restores byte-identical files."
  - "Every intent read path is workspace-scoped; a cross-workspace intent_id is indistinguishable from a nonexistent one."
  - "run.plan and swarm.start deny cross-workspace intent_id without leaking existence."
  - "With isolation advisory (single_user LAN default), behavior is byte-identical to pre-change."
open_questions:
  - "Do intents get a `visibility` field (workspace|public) like runs did, or is cross-workspace intent read never wanted? DF-004 added it to runs as an operator addition; intents may not need it."
  - "capture.py has NO identity threading today (unlike POST /runs, which DF-004 could stamp from). Does identity reach `rf capture`/`rf triage` via CLI at all, or is the CLI path always the local operator — i.e. is the stamp source config-owner or an AuthIdentity?"
  - "Do archived/completed/paused intent dirs need the same backfill, or only intents/active/?"
decisions:
  - decision: "Model this on DF-004 (runs/claims/evidence isolation), not as a novel design."
    rationale: "DF-004 solved the identical problem one entity over: same ownership question, same legacy-backfill question, same indistinguishable-404 question. Its ADR + migration runbook are the precedent to follow, not re-derive."
    status: accepted
  - decision: "Enforcement reuses the existing resolve_workspace_isolation_active / require_workspace_scope gate; advisory by default."
    rationale: "Keeps the single_user LAN deployment byte-identical to today and lets an operator opt in, exactly as DF-004 did. A new gate would be a second thing to reason about."
    status: accepted
  - decision: "Add workspace_id unconditionally to the schema, but resolve it as absent-tolerant during M1/M2."
    rationale: "operator_mcp_policy denies on a None-resolved target workspace. Wiring the deny before the backfill lands would fail-close all 39 intents. Scoping (M3) must come after backfill (M2) or the motivating candidates break permanently — the ERI extraction_status forward-only trap."
    status: accepted
routing_constraints:
  - "Ownership-stamp and read-scoping correctness MUST stay claude-primary — no offload."
  - "The operator-MCP policy contract change (_REQUIRED_TARGET_KINDS) MUST stay claude-primary."
  - "The backfill dry-run/manifest/rollback path is offload-eligible once its contract mirrors backfill_runs."
  - "Test authoring and mechanical read-site sweeps are offload-eligible."
wave_plan:
  waves: [["M1"], ["M2"], ["M3"]]
  phases:
    - id: M1
      title: "Intents carry a workspace, stamped from identity"
      depends_on: []
      exit_criteria: ["A newly captured intent has workspace_id from identity; a caller-supplied workspace_id is ignored."]
      gate_lens: [security, validator]
      gate_lens_reason: authz-boundary
    - id: M2
      title: "Every existing intent has a workspace"
      depends_on: ["M1"]
      exit_criteria: ["Dry-run reports 39 candidates and writes nothing; apply stamps all 39; rollback restores byte-identical files."]
      gate_lens: [security, validator]
      gate_lens_reason: irreversible-outward
    - id: M3
      title: "Every intent read path is scoped"
      depends_on: ["M2"]
      exit_criteria: ["Cross-workspace intent_id denies indistinguishably at every enumerated read site, including run.plan and swarm.start."]
      gate_lens: [security, validator]
      gate_lens_reason: authz-boundary
---

# Implementation Plan — Research-intent workspace isolation

A `research_intent` (`intents/active/*.yaml`) has no workspace concept at all. Any caller who can
reach an `intent_id` gets that intent's objective, research questions, and `governance.sensitivity`,
and can plan a run against it. `run_plan.py` checks only path containment — that the id resolves
inside `intents/active/` — never ownership. When this is done, intents are workspace-owned on the
same terms runs already are, and cross-workspace access is indistinguishable from nonexistence.

## Scope boundary

**In:** `research_intent.schema.yaml`; intent creation in `capture.py`; a new intent-aware
dry-run/backfill/rollback path in `workspace_migration_service.py`; the enumerated intent read
sites; the `run.plan` / `swarm.start` operator-MCP adapters and the policy target contract.

**Out (stated, not silently dropped):**
- **The DI-1 re-audit and Mode-D sign-off.** Code remediation does not lift the trusted-cohort
  scope boundary — DF-004's still-open AC #4 applies here identically. This plan does not license
  any adversarial-multi-tenant readiness claim.
- **Runs, claims, evidence, agent-jobs** — already done by DF-004.
- **`intents/intent.md`** — RF's own mission doc, unrelated to `research_intent` despite the path.
- **Malformed-input reason code** (`node_01KYWYK5V3MF12G9W395ERMGV2`) — separate follow-up.

## Rubric — what "good" looks like

The reviewer's question is not "is there a check" but "can a wrong-workspace caller tell the
difference between denied and absent." Every deny path must collapse to the same reason code and
message as a nonexistent intent — the H6/F6 shape already proven in `external_import.py` and
`catalog_service.get_item`. A `403` that distinguishes, or a log line that differs, is a fail.

The enumeration must be complete and demonstrably so: WKSP-304 shipped with an incomplete one and
two Mode-D leaks surfaced post-hoc. Produce a table of every intent read site with what authorizes
it. And absent-tolerant before enforcing — a guard reading a field nothing has written yet is worse
than no guard, because it fails closed on real data.

## Named risks

- **Ordering: scoping before backfill bricks every intent.** `operator_mcp_policy` denies targets
  whose workspace resolves to `None` (:144, deliberate — it replaced a `None`-means-skip default).
  All 39 intents resolve to `None` until M2 lands. M3 before M2 = 100% deny. This is the single
  reason the milestones are strictly sequential.
- **`run.plan` is contractually a no-targets operation.** `_REQUIRED_TARGET_KINDS["run.plan"]` is
  `frozenset()`. Adding an `intent` target kind is a policy-contract change with its own schema
  and confirmation-digest implications — not a local adapter edit.
- **`swarm_start.py:306` does the identical containment check.** Fixing `run_plan` alone is the
  sibling-parameter bypass class that produced repeated BLOCKING findings across M1/M2 of the
  operator-MCP work. Both move together or neither does.
- **`capture.py` has no identity threading at all.** DF-004 could stamp from `identity.workspace_id`
  because `POST /runs` already carried identity. The intent creation path does not — open question
  #2 must be answered before M1 is written, not during.
- **H7 hot files.** `cli_commands.py` (3395 lines) and `operator_mcp_policy.py` (2364 lines) are
  both touched. Localized edits only; any task that grows beyond that gets re-scoped, not pushed
  through.
- **Vacuous legacy test.** "Legacy intents still verify" proves nothing unless built from a frozen
  hand-authored fixture rather than a file the migration just wrote.

## References

- `src/research_foundry/services/operator_mcp_adapters/run_plan.py:155-200,282-320` — the guard as it stands
- `src/research_foundry/services/operator_mcp_adapters/swarm_start.py:306-310` — the sibling site
- `src/research_foundry/services/operator_mcp_adapters/external_import.py:290-320` — the pattern to mirror
- `src/research_foundry/services/operator_mcp_policy.py:134-144,563-566,1301` — deny-on-None, target kinds, RBAC
- `src/research_foundry/services/workspace_migration_service.py:356-408,616-741` — `dry_run_runs`/`backfill_runs` to mirror
- `src/research_foundry/services/capture.py:350-404` — `_build_intent`, the stamp site
- `schemas/research_intent.schema.yaml` — `additionalProperties: true`, so the field add is non-breaking
- Read sites to enumerate: `planning.py:452`, `capture.py:454`, `governance.py:589`, `synthesis.py:52`,
  `verification.py:1546`, `writeback.py:129`, `telemetry.py:555`, `cli_commands.py:1002`

## Milestones

### M1 — Intents carry a workspace, stamped from identity

`research_intent.schema.yaml` gains `workspace_id` (and `visibility`, if OQ#1 resolves that way).
`_build_intent` stamps it from the resolved identity, never from a parameter a caller controls —
the `builder_service.create_draft` idiom DF-004 reused. Readers tolerate its absence; nothing
denies yet.

**AC:** A newly captured intent has `workspace_id` set from identity. A caller-supplied
`workspace_id` is ignored, not honored. An intent file without the field still loads everywhere.

### M2 — Every existing intent has a workspace

A new intent-aware `dry_run_intents` / `backfill_intents` / rollback path in
`workspace_migration_service.py`, mirroring the run-backfill contract: zero-write dry run, JSON
manifest, null-not-wildcard, reversible. Legacy intents backfill to `"default"`.

**AC:** Dry run reports 39 candidates and writes zero bytes. Apply stamps all 39 and writes a
manifest. Rollback restores every file byte-identically. The runbook documents the intent path.

### M3 — Every intent read path is scoped

Every enumerated read site resolves the intent's workspace and gates on
`resolve_workspace_isolation_active` / `require_workspace_scope`. `run_plan` and `swarm_start`
declare an `intent` target with its resolved workspace; `_REQUIRED_TARGET_KINDS["run.plan"]`
gains `intent`. Cross-workspace denies collapse to the same envelope as nonexistent.

**AC:** Every site in the References enumeration has a test proving a wrong-workspace caller gets
the identical reason code and message as a nonexistent id. With isolation advisory, all behavior
is byte-identical to pre-change.

## AC -> command -> evidence

| AC | Command | Evidence of pass |
|---|---|---|
| M1 stamp from identity, not input | `./.venv/bin/python -m pytest tests/unit/test_intent_workspace_stamp.py -q` | Exit 0; a test asserting a caller-supplied `workspace_id` is discarded |
| M1 absent-tolerant | `./.venv/bin/python -m pytest tests/unit -k intent -q` | Exit 0 against a frozen pre-change intent fixture |
| M2 dry run writes nothing | `rf workspace migrate-dry-run` (intent path added by M2) then `git status --porcelain intents/` | Reports 39 candidates; `git status` empty |
| M2 apply + rollback reversible | `rf workspace migrate --apply --workspace-id default` then `rf workspace rollback <migration_run_id> --execute` | 39 stamped; after rollback `git diff --stat intents/` is empty |
| M3 indistinguishable deny | `./.venv/bin/python -m pytest tests/unit/test_intent_workspace_isolation.py -q` | Wrong-workspace and nonexistent assert the same reason code + message |
| M3 sibling parity | `rg -n "intents_active" src/research_foundry/ \| rg -v "workspace"` | Empty, or every hit annotated why it needs no scope |
| M3 advisory no-op | `./.venv/bin/python -m pytest tests/unit tests/ -q` | Exit 0; failure set identical to the pre-change baseline |

## Sequencing

Strictly M1 -> M2 -> M3, and the reason is load-bearing, not stylistic: the policy layer denies on
a `None`-resolved workspace, so enforcing (M3) before the data exists (M2) fail-closes all 39
intents permanently. M1 before M2 so the backfill writes a field the schema already declares.

## Execution ledger

Deviations and conservative choices are logged with rationale to
`.claude/worknotes/intent-workspace-isolation/implementation-notes.md` and reviewed at each
milestone boundary rather than halting on them.

**Mode-D boundaries are unchanged and non-negotiable.** Running the M2 backfill against real
`intents/` is a data migration and halts for explicit human approval. So does any change that
would let a deploy claim adversarial-multi-tenant readiness ahead of the DI-1 re-audit.
