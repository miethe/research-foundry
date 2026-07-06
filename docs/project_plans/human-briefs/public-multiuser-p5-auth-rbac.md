---
schema_name: ccdash_document
schema_version: 2

doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans

id: "BRIEF-public-multiuser-p5-auth-rbac"
title: "Public Multi-User P5 — Auth/RBAC/Isolation/Audit Hardening"
status: draft
category: human-briefs

feature_slug: public-multiuser-p5-auth-rbac
feature_family: public-multiuser-release
feature_version: "P5"

prd_ref: docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md
plan_ref: docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md
intent_ref: null
epic_ref: null

related_documents:
  - docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md
  - docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
  - docs/project_plans/implementation_plans/public-multiuser-p2p3-opus-handoff.md
  - .claude/worknotes/public-multiuser-p5-auth-rbac/decisions-block.md
  - docs/project_plans/human-briefs/public-multiuser-p4-agents.md

owner: nick
contributors: []

audience: [humans]

priority: high
confidence: medium

created: 2026-07-06
updated: 2026-07-06
target_release: ""

tags: [human-brief, auth, rbac, security, workspace-isolation, public-multiuser-release, mode-d]
---

# Public Multi-User P5 — Auth/RBAC/Isolation/Audit Hardening — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-06

---

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/features/public-multiuser-p5-auth-rbac-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/features/public-multiuser-p5-auth-rbac-v1.md` (split into 9 phase files — 46 pts, Tier 3)
- **Phase 1** — Auth-Provider Port: `.../public-multiuser-p5-auth-rbac-v1/phase-1-auth-provider-port.md`
- **Phase 2** — RBAC Enforcement: `.../public-multiuser-p5-auth-rbac-v1/phase-2-rbac-enforcement.md`
- **Phase 3** — Workspace Migration (highest risk, Mode D): `.../public-multiuser-p5-auth-rbac-v1/phase-3-workspace-migration.md`
- **Phase 4** — Clerk Adapter: `.../public-multiuser-p5-auth-rbac-v1/phase-4-clerk-adapter.md`
- **Phase 5** — Audit Log: `.../public-multiuser-p5-auth-rbac-v1/phase-5-audit-log.md`
- **Phase 6** — Rate Limits + Admin + Sharing: `.../public-multiuser-p5-auth-rbac-v1/phase-6-rate-limits-admin-sharing.md`
- **Phase 7** — Deferred Sensitivity (FU-4 closure): `.../public-multiuser-p5-auth-rbac-v1/phase-7-deferred-sensitivity.md`
- **Phase 8** — Auth-Context UI: `.../public-multiuser-p5-auth-rbac-v1/phase-8-auth-context-ui.md`
- **Phase 9** — Regression + E2E + Docs: `.../public-multiuser-p5-auth-rbac-v1/phase-9-regression-e2e-docs.md`
- **SPIKE**: `docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md` — ADR-001 (auth-provider port, binding), ADR-002 (P4 credential isolation, composed here not re-implemented), Mode-D gates, FU-4 deferred items.
- **Design Spec**: `docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md` — §10/§11/§12.5/§14 (parent spec this PRD formalizes).
- **Decisions Block**: `.claude/worknotes/public-multiuser-p5-auth-rbac/decisions-block.md` — Opus-authored scaffold the plan expands (D1–D7, phase boundaries, agent/model routing, OQ-A/OQ-B).
- **Precedent**: `docs/project_plans/implementation_plans/public-multiuser-p2p3-opus-handoff.md` — D10 (catalog.db disposability), D12 (nullable workspace fields, now enforced here), landmines #3/#4.
- **Related Briefs**: `docs/project_plans/human-briefs/public-multiuser-p4-agents.md` — sibling Phase 4 brief; P5 sequences after P4 per user directive (D4) and inherits P4's `agent_job*` nullable-field forward-compat pattern.

---

## 2. Estimation Sanity Check

Run per `.claude/skills/planning/references/estimation-heuristics.md` H1–H6, bottom-up against the decisions block's 46-pt total (`.claude/worknotes/public-multiuser-p5-auth-rbac/decisions-block.md` §4).

**H1 — Noun-counting**: 5 new domain nouns carry identity/RBAC/audit state: `users`, `workspaces`, `memberships`, `roles`, `audit_event`. Not all are equally "full CRUD-with-RBAC" — `roles` is a static 5-value capability matrix (code/config, not a mutable table) and `audit_event` is append-only (no update/delete, but does get a read API per FR-8's `rf audit list|show`). Noun-weighted floor: users (2) + workspaces (2) + memberships (2) + roles (~1, capability matrix not full CRUD) + audit_event (~1.5, log + read API) ≈ **8.5 pt floor**. The naive "≥2pt × 5 nouns = 10pt" floor, checked strictly against P5.1+P5.2 alone (12 pts actual), holds — but the honest picture is that these nouns' *work* spans four phases, not two: P5.1 (6, schema/store), P5.2 (6, RBAC enforcement over the roles matrix), P5.5 (4, audit_event), P5.6 (5, admin CRUD UI for members/roles/provider status). Summed across all four = **21 pts**, ~2.5x the noun floor — confirming the dominant cost driver is cross-cutting enforcement breadth (RBAC on ~5 routers) and admin surface, not base entity CRUD.

**H2 — Dual-implementation multiplier**: **Does not apply.** Research Foundry has no dual-edition (local + enterprise) repository split — every repository in this codebase has exactly one implementation. This heuristic is a no-op for this plan, same as it was for the P4 sibling brief.

**H3 — Algorithmic service flag**: Checked P5.2 (RBAC) and P5.3 (migration) against the trigger word list (`dependency`, `resolution`, `graph`, `conflict detection`, `cycle`, `solver`, `inference`, `ranking`, `scheduling`, `merge`, `diff`, `transform`).
- **P5.2 (RBAC)**: No trigger word matches. Its 6-pt estimate is driven by H1 breadth (enforcement across ~5 routers), not algorithmic complexity — the ≥3pt floor is moot (H3 doesn't fire) but is satisfied regardless.
- **P5.3 (migration)**: No trigger word matches literally either — "migration" itself isn't on the list. But the decisions block's own Estimation Anchors table explicitly tags P5.3 as "H3 migration/algorithmic flag," and the phase file's task acceptance criteria (WKSP-302) enumerate ≥5 concrete correctness-invariant test scenarios: round-trip byte-identical fidelity, false-legacy-record non-touch, manifest-driven-not-value-matched rollback safety, idempotency, and dry-run-vs-real-backfill parity. That satisfies H3's "enumerate ≥5 scenarios or SPIKE first" bar even though the literal trigger word is absent — an irreversible state-rewrite with a required tested inverse function has the same test-matrix-dominated cost profile H3 describes. Budgeted at 6 pts, comfortably above the ≥3pt floor.

Both phases clear the ≥3pt floor with margin; the more interesting finding is that P5.3 deserves the H3 treatment on substance even though it doesn't match on vocabulary.

**H4 — Bundle-vs-sum**: The PRD packages ~8 capability areas under one slug (auth-provider port, RBAC enforcement, workspace isolation/migration, Clerk/OIDC adapter, audit log, rate-limit+admin+sharing, deferred-sensitivity closure, frontend auth-context UI), plus one cross-cutting validation phase. Per-area independent estimate:

| Capability Area | Independent Estimate | Notes |
|------------------|----------------------|-------|
| Auth-provider port + identity (P5.1) | 6 | New subsystem + durable store |
| RBAC enforcement (P5.2) | 6 | ~5 routers, H1 breadth |
| Workspace isolation + migration (P5.3) | 6 | H3-flagged; irreversible, human-gated |
| Clerk adapter + OIDC seam (P5.4) | 5 | JWKS verify + FE login |
| Audit log (P5.5) | 4 | Anchored to existing writeback/telemetry plumbing |
| Rate limits + admin + sharing (P5.6) | 5 | 3 sub-areas |
| Deferred sensitivity closure (P5.7) | 5 | 3 FU-4 closes, H4 bundle-vs-sum internally too |
| Frontend auth-context UI (P5.8) | 5 | Anchored to P3 `/builder` wave |
| Cross-cutting validation/docs (P5.9) | 4 | H6 plumbing + E2E in two modes + runbook |
| **Σ** | **46 pts** | Matches the locked plan total exactly |

Plan total **equals** Σ — no compression applied, which is the honest floor per H4 (no "package price" discount taken anywhere).

**H5 — Anchor reference**: `public-multiuser-p2p3-opus-handoff.md` (P2/P3) has no clean point total to cite — it is a wave-based execution handoff, not a pointed implementation plan (confirmed in the P4 sibling brief's own H5 analysis). The closer, methodologically-consistent anchor is **P4** (`public-multiuser-p4-agents-v1`, 24 pts) — same feature family, same decisions-block→implementation-planner process, immediately preceding phase. P5 at 46 pts is **~92% larger** than P4's 24 pts, a delta well over the 30% justification threshold. Justification: P5 spans 8 capability areas vs. P4's 5, is retrofitting RBAC onto ~5 *existing* routers (a breadth-of-surface cost P4 didn't carry, since P4 added new routes rather than gating old ones), includes one genuinely irreversible data migration (P4 had no equivalent — P4's credential-isolation phase was additive, not a rewrite of existing durable state), and ships two full auth-provider implementations plus an OIDC seam. The delta reflects objectively larger, structurally distinct scope — not padding.

**H6 — Hidden plumbing budget**: Rather than a single top-level 15–20% line item, this plan distributes named plumbing tasks *inline* into each phase's own task table:
- **DTOs**: `AuthIdentity` (P5.1), `WorkspaceScopeResult`/`DryRunReport`/`BackfillReport`/`RollbackReport` (P5.3), `audit_event` schema (P5.5) — each named as part of its phase's core estimate, not a separate bucket.
- **DI wiring**: `require_role(...)` shared dependency (P5.2, OQ-A), `require_workspace_scope(...)` shared dependency mirroring the same idiom (P5.3), `AuthProvider` registry resolution at `create_app` time (P5.1) — all inline.
- **RLS-equivalent workspace scoping**: this isn't hidden plumbing at all — it **is** P5.3's headline scope (SQLite has no native RLS; `require_workspace_scope()` is the hand-rolled analog).
- **CHANGELOG**: `changelog_required: true` is set on the plan; folded into P5.9 as a named `documentation-writer`/haiku task, per the doc-finalization split (tests sonnet, docs haiku).
- **OpenAPI schema regeneration**: the one plumbing item **not** named as its own task anywhere across the 9 phase files reviewed — it's implicitly assumed absorbed into each router-touching phase's own task estimate (P5.2/P5.3/P5.4/P5.6). Flag as a minor estimation risk (~0.5–1 pt underweighted per phase) rather than a defect — the plan is otherwise unusually explicit about naming config/CLI-adjacent sub-tasks (e.g., WKSP-301 names a whole new `workspace_app` Typer group as part of its own 1.5-pt task cost, not a hidden fragment).

**Bottom-up total**: 46 pts.
**Top-down intuition**: A "just add auth" read would likely land Tier 2 (8–13 pts) — the decisions block's own Estimation Notes explicitly flag this trap ("trust bottom-up over any 'just add auth' top-down read"). The bundle decomposition (H4, 8 capability areas) is what correctly forces Tier 3.
**Verdict**: Bottom-up (46) is trusted over any lower top-down gut-feel number. The disagreement is expected and documented, not a sign the estimate is wrong — retrofitting RBAC onto existing routers, one irreversible migration, two auth providers, a new audit subsystem, and 3 deferred-sensitivity closures is genuinely an 8-area bundle, not a single capability that happens to touch several files.

---

## 3. Wave & Orchestration Notes

**Critical path**: See the plan's Phase Summary table and decisions block §5 Dependency Map — `P5.1 → P5.2 → P5.3 → P5.6 → P5.9` (27 of 46 pts sit on this serial spine).
**Parallel opportunities**: [to be expanded during execution — plan already identifies {P5.4, P5.5, P5.7} as parallelizable after P5.1; confirm no file-overlap surfaces once phases are dispatched]
**Merge order**: [to be expanded during execution]
**Cross-feature coupling**: [to be expanded during execution — P5 depends on P4's `agent_job*` nullable-field pattern per the P4 brief's own cross-feature-coupling note; confirm P4 has actually merged before P5.2 wires `agent_jobs.py` into RBAC]

---

## 4. Open Questions Ledger

All 5 PRD-level open questions were resolved as locked decisions (D1–D7) before this plan was authored — none remain open. Two additional planning-time questions (OQ-A, OQ-B) surfaced in the decisions block and were closed during plan expansion.

| ID | Source | Question | Status | Resolved By |
|----|--------|----------|--------|-------------|
| OQ-1 (PRD) | PRD §12 / Decisions D2 | Where do user/workspace/membership/role/audit tables live — new durable store vs. extending `catalog.db`? | resolved | Decisions block D2 — new durable `<workspace>/.rf_state/rbac.db`, never `catalog.db` (catalog.db is disposable, D10); implemented P5.1 |
| OQ-2 (PRD) | PRD §12 / Decisions D4 | Does P5's AC-3 (agent credentials never reach browser) block on P4 landing first? | resolved | Decisions block D4 — P5 sequences after P4 per user directive; stub-contract-test fallback if P4 slips |
| OQ-3 (PRD) | PRD §12 / Decisions D5 | Minimum public-sharing target for v1 — report links, team-workspace links, or public URLs? | resolved | Decisions block D5 — read-only, sensitivity-scoped share links; general public URL productization deferred |
| OQ-4 (PRD) | PRD §12 / Decisions D6 | Rate-limit granularity — per-identity+per-route or global? | resolved | Decisions block D6 — per-identity+per-route sliding window, `foundry.yaml`-driven |
| OQ-5 (PRD) | PRD §12 / Decisions D3 | Does `local_static` need a multi-token→role mapping table? | resolved | Decisions block D3 — yes; required to serve >1 concurrent human identity air-gapped; implemented P5.1 |
| OQ-A (decisions block) | Decisions block §7 | Does RBAC enforcement wrap routers via a shared FastAPI dependency, or per-route decorators? | closed | Locked in plan frontmatter `decisions` list — single `require_role(...)` dependency for R-P1 uniformity + testability; implemented Phase 2, and the same idiom is reused (mirrored, not duplicated) by Phase 3's `require_workspace_scope()` |
| OQ-B (decisions block) | Decisions block §7 | Migration backfill strategy — one synthetic `default` workspace, or per-`created_by` inference? | closed | Locked in plan frontmatter `decisions` list — single `default`-workspace backfill (simplest, reversible); implemented Phase 3 task WKSP-303, explicitly titled "Legacy-record default-workspace backfill (OQ-B resolution)" |

Two additional locked decisions (D1: `AuthProvider` port with local_static default/Clerk opt-in/OIDC seam, from ADR-001; D7: D12's nullable `workspace_id`/`created_by` become enforced via real migration) aren't tied to a single numbered PRD OQ but are foundational and carried the same way — see decisions block Decisions table for full rationale.

---

## 5. Deferred Items Rationale

The plan's own **Deferred Items & In-Flight Findings Policy** section (`public-multiuser-p5-auth-rbac-v1.md`) owns the full triage table and promotion triggers — not duplicated here. Summary pointer only:

- **FU-2** (concrete OIDC/BYO adapter implementation): deferred — only the Protocol seam lands in P5.1/P5.4; promotion trigger is an on-prem-IdP consumer emerging. Design-spec path assigned for authoring in P5.9.
- **FU-3** (Clerk paid-plan procurement): deferred — operator/procurement action, not engineering; Clerk adapter ships dark-by-default behind a config flag regardless.
- **FU-4** (3 deferred-sensitivity closes carried from P2/P3): explicitly **not** deferred under this plan — in-scope, closed in P5.7. Listed in the plan's triage table only for completeness/traceability back to its P2/P3 origin.

---

## 6. Risk Narrative

**Focus: P5.3 (Workspace Isolation + Migration) — the single highest-risk item in the entire 46-pt feature.**

Every other phase in this plan adds new capability alongside what already works. P5.3 is the only phase that **mutates existing durable data** — that difference in kind, not just degree, is why it alone carries a human sign-off gate that blocks phase exit (not just a courtesy review), a dedicated `karen` isolation-milestone review, and a hard "no ICA/Codex offload, ever" rule.

**What the "Critical Schema Findings" split means in plain language**: "the migration" is actually two very different jobs wearing one task name.

- **The boring half**: `catalog_items` (the run-derived catalog cache) has no `workspace_id` column today, and the whole `catalog.db` file is explicitly disposable — it already gets dropped and rebuilt from scratch whenever its schema version bumps, and that rebuild path has been shipped and exercised since P2/P3. Adding a `workspace_id` column here and rebuilding is no riskier than any other schema change this project has already done a dozen times. If it goes wrong, the fix is: revert the schema version, rebuild again. Nothing here is precious.
- **The irreversible half**: every report draft's real, canonical, hand-curated content lives in a `draft.yaml` file on disk — not in the disposable cache. Backfilling `workspace_id` there means atomically **rewriting real files that are the actual source of truth**, not regenerating a cache. Imagine an operator who has been running Research Foundry solo for months, with a folder of report drafts they've built up by hand. This phase is the one that goes and rewrites every one of those files. If the rewrite logic has a bug, "just rebuild it" does not apply — there is no cache to fall back to, only the files themselves.

That's why P5.3 requires a **tested** reverse-migration function (not a runbook alone), a manifest keyed by `migration_run_id` (never by matching on the literal value `workspace_id == "default"`, because legitimate post-migration usage will also produce that value and must never be caught by an earlier rollback), and a round-trip test that proves byte-identical file restoration — not just "the field is null again," the whole file, to catch any other unintended mutation.

**What could go wrong if the gate is skipped**: Human Gate #1 is the only point in this entire plan where a human reviews real evidence — the dry-run's predicted counts, the actual backfill's report, and proof the rollback round-trip test is genuinely green in CI — before the actual behavior-changing step (the enforcement flip, WKSP-304) is allowed to run. If that gate is rubber-stamped rather than genuinely reviewed:
1. The enforcement flip could start returning 404s for records the backfill silently missed or mis-scoped — a legitimate single operator locked out of their own pre-existing data, indistinguishable (by design, per the no-existence-leak convention) from "this never existed."
2. If the backfill has a subtle defect the round-trip fixture's synthetic test cases didn't cover (e.g., a crash mid-atomic-rewrite, an unusual pre-existing `draft.yaml` shape), there is no automated way back — the runbook's manual filesystem-snapshot fallback becomes the only recourse, and it only works if the operator actually took a snapshot before running the migration, which is why the runbook's existence is graded on whether it was *followed*, not merely whether the file exists.
3. A rushed approval could sign off on enforcement before the round-trip rollback test has actually run green in CI (as opposed to merely being present in the codebase) — the acceptance criteria are explicit that the test must assert real byte-identical restoration; skipping verification that it *passed*, not just that it *exists*, is exactly the failure mode a rubber-stamp gate would let through.

One more thing worth flagging so a reviewer doesn't mistake it for a bug: `created_by` is permanently left `null` for every pre-migration record, by design — there is no honest way to retroactively attribute authorship, and inventing a placeholder would be worse than an honest gap.

---

## 7. What to Watch For

- **Silent-reviewer trap** (carried forward from P2/P3 and P4 precedent): `karen` returning only an `idle_notification` is never a pass. This has bitten a prior RF execution. Demand an explicit verdict at all three `karen` milestones (P5.3 isolation, P5.6 public-exposure, P5.9 end-of-feature).
- **Worktree merge-back discipline**: P5.3 explicitly runs in its own dedicated worktree (Mode D isolation note in the phase file) — don't let it sit unintegrated across a session boundary; explicit merge only after both reviewer gates and the Gate #1 approval artifact are recorded.
- **ICA offload gotchas** (per P2/P3/P4 precedent): P5.5, P5.7, and P5.8-subcomponents route through ICA Sonnet 4.6 behind a `task-completion-validator` gate — pipe long prompts via stdin, pin `[1m]` aliases, watch turn caps.
- [to be expanded during/after execution — real-time gotchas as phases actually run]

---

## 8. Expected Success Behaviors

- [ ] A viewer-role user cannot delete a source card, edit a report draft, or launch an agent job even via a direct API call with a valid token/session — the denial is server-enforced, not a hidden UI button.
- [ ] An admin logging in (via Clerk or `local_static`) sees only their own workspace's runs, catalog items, and report drafts — a second workspace's private data is completely invisible, not merely grayed out.
- [ ] A legacy single-operator deployment's existing report drafts and catalog migrate cleanly to the `default` workspace with zero behavior change until enforcement is explicitly flipped on, and can be rolled back to their exact original state if the dry-run or backfill result looks wrong.
- [ ] An over-threshold-sensitivity run, or a record in another workspace, returns a plain 404 to an unauthorized caller — never a 403 that reveals the record exists, and never a redacted-but-200 response.
- [ ] Every catalog mutation, report edit, agent-job launch, accepted artifact, publish preview, and writeback shows up as a queryable, attributed audit row — an admin can answer "who did this, from what source, under what policy" for any of the six governed action types.
- [ ] Enabling the Clerk adapter requires an explicit sign-off (Human Gate #3) and never exposes a Clerk secret key or JWKS credential in a browser payload, log line, or error message.
- [ ] A public reader following a shared report link sees a sensitivity-safe, read-only view — nothing over the sensitivity threshold is visible or inferable from that link, regardless of the caller's role.
- [ ] Rate limits are enforced per-identity-per-route (one user's burst never starves another), and a limited request receives a 429 with `Retry-After` — never a silent hang or an opaque 500.

---

## 9. Running Log

- [2026-07-06] Brief created alongside the implementation plan (expanded from the Opus decisions block). Estimation sanity check run; H5 anchored against P4 (24 pts) rather than P2/P3 (no clean point total exists). H3 flagged P5.3 on substance (enumerated test-scenario bar) despite no literal trigger-word match — worth re-checking this nuance against `estimation-heuristics.md` in a future retro. OpenAPI schema regeneration identified as the one plumbing item not explicitly named as its own task anywhere in the 9 phase files — minor estimation risk, not a defect.
