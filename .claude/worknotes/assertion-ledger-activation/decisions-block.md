---
schema_version: 2
doc_type: decisions_block
title: "Assertion-Ledger Population & Activation — Opus Decisions Block"
status: draft
created: 2026-07-15
feature_slug: assertion-ledger-activation
tier: 2   # 15–18 pts → Tier 3 by points; SPIKE waived-with-rationale (see below). Promote to full Tier 3 if implementation-planner's bottom-up exceeds 18 pts or surfaces a genuine research unknown.
prd_ref: null
plan_ref: null
related_documents:
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/aars/2026-07-15-catalog-visibility-regressions.md
---

# Decisions Block: Assertion-Ledger Population & Activation

## Problem framing (the delta only)

Assertion-ledger v1 shipped the schemas, the read-only `/api/assertions/*` API, the runs-viewer
"Source assertions" tab (now the **default** Catalog tab), and enabled three `foundry.yaml` flags
(`ledger_write_enabled`, `automated_reuse_enabled`, `canonical_claims_enabled`) — but **no shipped
CLI or HTTP entry point exercises the write or reuse seams**, so the ledger is empty and the default
tab renders nothing. This feature makes the ledger actually populate (from history and going forward)
and makes reuse + the canonical-merge UI reachable. Stable context lives in the v1 plan and the
2026-07-15 gaps AAR — do not restate; reference by path.

**Not in scope** (already shipped in `068a4e6`): B1 Claims tab, A2 threshold propagation.

## SPIKE waiver rationale (Tier 3 point count, Tier 2 rigor)

Point estimate lands in Tier 3 territory, but the technical path is **known**, not researched:
`services/assertion_rollout.backfill_dry_run()` already enumerates historical `claims/claim_ledger.yaml`
candidates (no-write), and `assertion_registry` / `assertion_materialization` already implement the
edition→passage→source-assertion write path. The remaining unknowns are **correctness and workspace
scoping**, not feasibility — those are addressed by the P1 WKSP-304 test harness and karen milestones,
not by a SPIKE. **Recommend waiving the SPIKE**; if `implementation-planner`'s bottom-up estimate
exceeds ~18 pts OR it finds the materialization mapping is not 1:1 from claim-ledger entries, promote
to Tier 3 and author a targeted backfill-mapping SPIKE first.

## Phase boundaries

| Phase | Name | Scope | Exit gate |
|---|---|---|---|
| P1 | Write-path foundation & WKSP-304 scoping contract | Establish/verify the workspace-scoped assertion write invariants; shared test harness proving an assertion write is confined to its `assertion_registry_workspace_id` and fails closed without it. No feature behavior yet — this is the safety substrate B2+C1 both build on. | `task-completion-validator` + isolation tests green; DI-1 scoping enumeration reviewed |
| P2 (B2) | Historical claim→assertion backfill migration | Add the write-path counterpart to `backfill_dry_run()`: read historical `claims/claim_ledger.yaml`, materialize source editions/passages/source-assertions into the workspace ledger. Idempotent, resumable, workspace-scoped, dry-run parity. Expose as `rf assertion backfill` (or equivalent) — an explicit, gated operator command. | Backfill of the 41 existing runs populates the ledger; re-run is a no-op; **karen milestone** (security) |
| P3 (C1) | Forward write driver | Pass `assertion_registry_workspace_id` + `ledger_write_allowed` into `source_cards.ingest_source` from a real ingest/launch entry point so NEW runs populate the ledger. | A fresh run's ingest writes assertions; flag-off path unchanged (no writes) |
| P4 (C2) | Reuse reachability | Expose reuse fields (`reuse_assertion`, `reuse_workspace_id`, `required_reuse_edition_id`, `required_extraction_contract`) in `LaunchRunRequest` and/or a `rf run launch` command so `automated_reuse_enabled` is reachable. | Reuse decision is invocable via CLI/HTTP; governed block path tested |
| P5 (C3) | Canonical-merge UI activation | Build runs-viewer with `VITE_RF_CANONICAL_CLAIMS_ENABLED=true`; verify the merge-review controls render + wire the deploy flag (bootstrap env). | Merge UI renders against populated ledger on `:3030`; tsc clean |
| P6 | Verification, DI-1 audit, docs | End-to-end: backfilled + forward-written assertions visible in the default Catalog tab; WKSP-304/DI-1 full-surface scoping audit for the new write sites; CHANGELOG + user/dev docs. | **karen** feature-end gate; DI-1 audit sign-off |

## Agent routing

| Phase | Primary | Secondary | Notes |
|---|---|---|---|
| P1 | python-backend-engineer | senior-code-reviewer (Mode E) | Security-substrate; reviewer reads the isolation contract diff |
| P2 | python-backend-engineer | data-layer-expert | Migration + content-addressing; data-layer for the ledger store semantics |
| P3 | python-backend-engineer | — | Entry-point wiring; disjoint from P2 files where possible |
| P4 | python-backend-engineer | api-designer | LaunchRunRequest contract + CLI |
| P5 | ui-engineer | — | Build-flag + merge UI verification; frontend only |
| P6 | task-completion-validator, karen | documentation-writer, changelog-generator | Audit + docs |

**Parallelizable:** P3 and P4 are largely independent of P2 once P1 lands (they touch different entry points); P5 is independent of P2–P4 (frontend build flag). P2 is the long pole.

## Risk hotspots

| Risk | Severity | Mitigation |
|---|---|---|
| **WKSP-304 isolation leak on the new write sites** (DI-1 gate) — a write that isn't workspace-scoped is a cross-tenant leak | **High** | P1 test harness proves confinement + fail-closed; DI-1 full-surface scoping audit in P6; karen milestone after P2/P3; this is Mode-D-adjacent — no auto-merge, diffs reviewed before merge/deploy |
| Backfill non-idempotency / double-materialization | Medium | Content-addressed editions/passages (v1 already content-addresses); explicit re-run-is-no-op test; dry-run parity assertion |
| Enabling write driver changes existing run behavior | Medium | Gate strictly on `ledger_write_enabled`; flag-off path must be byte-identical to today (regression test, mirrors A2's approach) |
| Reuse fields widen the run-launch attack/validation surface | Low-Med | Validate + authorize reuse targets; governed `block_authoritative_reuse` path already exists — wire, don't reinvent |
| Merge-UI build flag drifts on redeploy | Low | Set `VITE_RF_CANONICAL_CLAIMS_ENABLED` in bootstrap like `RF_UI_LOOPBACK` (now default-true); document the deploy flag |

## Estimation anchors

- **Anchor:** `reusable-assertion-ledger-v1` (71 pts total; the materialization/registry services this feature drives were built there). This feature *drives* existing machinery rather than building it, so it is far smaller than v1.
- P1 ~3 · P2 ~5 · P3 ~3 · P4 ~3 · P5 ~2 · P6 ~2 = **~18 pts** (H4 bundle-vs-sum floor; H3 algorithmic flag applied to P2 backfill). Justify any downward delta >30% against the enumerated per-phase floor.

## Dependency map

```
P1 (write-path foundation + WKSP-304 harness)
 ├──> P2 (B2 historical backfill)   ── karen milestone ──┐
 ├──> P3 (C1 forward write driver)                       ├──> P6 (verify + DI-1 audit + docs, karen end)
 └──> P4 (C2 reuse reachability)                         │
P5 (C3 merge UI build flag) ── independent ──────────────┘
```
Critical path: P1 → P2 → P6. P3/P4/P5 parallelizable after P1.

## Model routing

| Phase | Model | Effort |
|---|---|---|
| P1 | sonnet | extended (security substrate) |
| P2 | sonnet | extended (algorithmic migration) |
| P3, P4 | sonnet | adaptive |
| P5 | sonnet | adaptive |
| P6 | sonnet (validator/karen per their configs) + haiku (docs) | adaptive |

## Open questions for implementation-planner (OQ-*)

- **OQ-1:** Is the historical claim-ledger→source-assertion mapping 1:1, or do some claim entries lack the passage/edition provenance needed to materialize an assertion? (If not 1:1 → promote to Tier 3 + backfill-mapping SPIKE.) Inspect `assertion_materialization` + a sample `claims/claim_ledger.yaml`.
- **OQ-2:** Which is the correct single entry point to wire the forward write driver (C1) — `rf ingest`, the discovery-swarm ingest path, or `POST /api/runs`? Prefer the narrowest one that covers real runs.
- **OQ-3:** What `assertion_registry_workspace_id` does a single-operator run resolve to (default workspace)? Confirm against WKSP-304 resolution.
- **OQ-4:** Does the merge UI (C3) require populated canonical claims (i.e., depends on P2 output) to be meaningfully verifiable, or can it be verified against a synthetic fixture?

## Plan skeleton pointer

- Template: `.claude/skills/planning/templates/implementation-plan-template.md`
- PRD output: `docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md`
- Plan output: `docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1.md`
