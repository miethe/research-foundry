---
type: context
schema_version: 2
doc_type: context
prd: "reusable-assertion-ledger-v1"
feature_slug: reusable-assertion-ledger
created: 2026-07-14
updated: 2026-07-14
---

# Reusable Assertion Ledger — Agent Worknotes (P6+ / physical Phase 7+)

Working notes feeding the final AAR (partial P0–P5 AAR already exists at
`docs/project_plans/aars/2026-07-14-reusable-assertion-ledger-p0-p5-execution.md`; the final AAR
extends it with P6–P8 / physical phases 7–9).

## Phase 7 (logical P6): Reviewer Experience — 2026-07-14

### Setup observations

- No `.claude/progress/reusable-assertion-ledger*` directory existed despite the parent plan
  declaring `progress_init: pre-created` — P0–P5 were executed via a Codex relay (see
  `.codex/worknotes/reusable-assertion-ledger/decisions-block.md`) without Claude-side progress
  files. Created `phase-7-progress.md` fresh. **AAR note:** plan frontmatter overstated progress
  scaffolding; verify `progress_init` claims on multi-runtime plans.
- Routing (delegation-router v3, audit-logged under `assertion-ledger-p7:*`): P6-000/P6-001 →
  codex/gpt-5.6-terra; P6-002/P6-003 → claude sonnet UI agents (design-sensitive, taste-critical);
  P6-004 → ICA offload with claude fallback; second-opinion review → codex/gpt-5.6-sol; verdict →
  claude (MUST-stay).
- Orchestrator (Fable) performed the direct visual pass over the five conceptual mockups and
  distilled per-surface design guidance into delegation prompts; mockups are planning inputs only
  (runtime evidence deferred to logical P7-004 / physical Phase 8 per design spec §2).

### Decisions

- **P6-000 denial contract** (Codex Terra, verified by orchestrator re-running pytest): success =
  `200 AssertionImpactSummary`; missing/malformed/interrupted-unreadable/cross-workspace receipts
  all return an identical `404 {"detail":{"reason_code":"impact_unavailable"}}` (no existence
  signal); missing workspace context or rights denial = typed `403` with safe reason code; no
  mutation route. Committed as `a7d312b` (6 API tests green, codegen contract test green).
- OpenAPI regen path confirmed: `create_app(FoundryConfig.load()).openapi()` → `pnpm codegen`
  (extended `generate-types.mjs` + contract test now cover the assertions API surface).

### Batch 3 (P6-002 + P6-003 parallel UI) — remediation log

- **`npx tsc --noEmit` is a NO-OP in runs-viewer** (solution-style root tsconfig with `files: []`
  — silently checks nothing). Every earlier "tsc clean" gate this phase (P6-000/001/003) was
  vacuous. Authoritative gate: `npx tsc -p tsconfig.app.json --noEmit` (main baseline: 0 errors).
  **AAR lesson: verify the validation command actually validates before trusting green.** P6-002
  (Claude UI agent) caught this; fix candidate for Phase 8: make `pnpm typecheck` point at the
  real project config.
- **Seam bug shipped green**: P6-001's `packetState()` read `packet.lifecycle_state` (nonexistent;
  nested at `assertion.lifecycle_state`) — its own tests passed because fixtures were shaped to
  the same wrong assumption. Runtime effect: every real packet → "unavailable". Copied into three
  P6-003 components. **AAR lesson: fixtures hand-shaped to the implementer's assumption + a no-op
  typecheck = self-confirming green; contract tests must build fixtures from the generated types.**
- **Cross-agent verification win**: P6-003 (and a stale workbench comment) claimed no
  claim→assertion linkage exists; P6-002 independently found `RFClaim.persistent_references.
  source_assertion_id` (schema v1.5). Parallel agents with overlapping domain reads caught it.
- **Impact hook keying defect**: `useAssertionImpact` demanded an `eventId` callers can never have
  pre-fetch (route is assertion-keyed; event_id is IN the receipt) — would have made the impact
  panel permanently "unavailable".
- Remediation wave (Codex Terra, high): nested lifecycle selector canonicalized, ref typing,
  assertion-id derivation from claim selection, eventId made display-only, fixtures corrected.
- **Contract gaps vs design spec (P6-002)**: `AssertionSummary` search DTO lacks assertion text /
  edition id / updated_at / prior-use counts (spec §5.1 columns can't fully render); no `total` on
  search response (cursor pager instead of numbered); qualifier vocabulary is
  population/geography/timeframe/modality/... not the mockup's Metric/Comparator; lifecycle enum
  is eligible/stale/invalidated/tombstoned (no Current/Corrected/Retracted backing values);
  `access_scope` is a sensitivity ladder, not "Workspace". UI maps honestly (no invented values).
  → Phase 8/9 candidates: enrich search DTO or revise spec copy to match the real vocabulary.
- **Packet has no run-local claim_id**: catalog inspector's `Open provenance`/`View lineage`
  render disabled-with-title (existing convention) — cross-navigation needs a packet→claim
  reverse link or assertion-scoped provenance modal in a later slice.

### Review gate results

- **task-completion-validator: PASS** (all 11 gates independently reproduced — tsc 0 errors,
  156/156 focused frontend tests, 6/6 API tests, denial-zero-hints asserted structurally,
  DTO-only impact counts, flag-off merge absence, focus-return fix verified real). Non-blocking
  notes: (a) `Open replacement edition` is data-gated only (backend guarantees null today) — add
  defense-in-depth `isCanonicalClaimsEnabled()` gating in Phase 8 when the real replacement-target
  seam lands; (b) cosmetic progress-file evidence count drift (5 vs 6 hook tests).

- **Codex Sol (xhigh) second-opinion: REJECT — remediation wave 2 dispatched.** Full findings in
  `p6-sol-findings.md`. 4 blockers + 11 majors survived my triage as genuine: interrupted receipts
  persist as `pending` so the reader's `interrupted` suppression is dead code; shallow receipt
  validation exposes semantically malformed receipts; impact band gated on packet-stale instead of
  the DTO's `authoritative_reuse_blocked` (and hardcoded its reason); assertion-only lineage had
  no production caller; invented object_class vocabulary; inference packets labeled
  `Source assertion`; missing Freshness/Relationships sections; no focus trap; test fixtures not
  backend-valid. **AAR lesson: the gate-level validator PASSED the same diff Sol REJECTED — the
  validator checked the phase's stated gates as written, Sol attacked contract fidelity beneath
  them. Two-frame review (checklist validator + adversarial refuter) earned its cost.**
  Disposition on finding 14 (OpenAPI snapshot now publishes share-link POST/admin PATCH routes):
  document-only — those routes pre-exist in the runtime app; the refreshed snapshot is truth, the
  prior snapshot was lying. Phase 8 candidate: OpenAPI drift gate in CI.

- **Wave-2 backend deviation (deliberate, needs design-spec reconciliation)**: `interrupted` was
  removed from `ImpactOperationStatus` because the P5 writer can never persist it — real
  interruption durably persists `pending` + completed checkpoints, and the reader now serves that
  as `pending`+`resumable` only after full reconciler-grade validation. The design spec §8 minimum
  contract still lists `"interrupted"`; either the spec drops it or the writer gains a persisted
  interrupted state in Phase 8. UI unknown-enum handling covers any future re-addition.

- **Sol re-review after wave 2: 8/15 RESOLVED, still REJECT on two blockers** → wave 3 dispatched.
  (a) NEW regression: wave-2's `_load_receipt` refactor deleted reason_code lexical validation —
  arbitrary receipt text could flow out via HTTP 200. **AAR lesson: remediation waves can delete
  guards they didn't know were load-bearing; re-review the delta, not just the findings list.**
  (b) F3 remnant: UI visibility keyed on packet lifecycle vocabulary (`stale|invalidated|
  tombstoned`) while the reader emits `"blocked"` — the two vocabularies never intersect, so real
  impact stayed invisible. Cross-vocabulary seams need one canonical source.
  Wave-3 scope: reason_code closed-set validation, operation/action status coherence,
  writeback_status propagation (denied/queued was stripped by the reader), DTO-flag-driven UI
  visibility, inference aria-label, backend-possible test fixtures, mobile lineage list fallback.
  Accepted-as-documented (not fixed this phase): catalog inspector provenance/lineage actions stay
  hidden pending a packet→claim reverse link (existing finding); explicit caller-supplied
  assertionId override surviving workspace clear (caller-owned state).

- **Sol final-pass round 3: wave-3 clean, but two NEW blockers found in pre-existing paths** →
  wave 4 dispatched. (a) Writer-blocked receipts (manifest missing/invalid) were STUCK-HIDDEN:
  reader validation unconditionally reloaded the very manifest whose absence caused the block →
  404 → the entire impact UI could never display a genuine blocked state. (b) Malformed action
  (unknown object_class + omitted action key) slipped a None==None comparison then KeyError'd into
  HTTP 500 outside the zero-hints boundary. **AAR lesson: each adversarial round found defects one
  layer deeper than the last (UI copy → seam wiring → validation semantics → liveness of the
  primary path). The 'can the happy path actually be served end-to-end' question was not asked
  until round 3 — an end-to-end writer→reader→UI liveness test should have been a wave-1
  deliverable.** Also wave 4: writer-reachable reason-set fidelity, dual-fact writeback rows,
  backend-legal fixtures (recurring fixture-honesty theme), same-ID cross-workspace re-derivation,
  mobile toggle state.

- **Sol round 4: all round-3 items CLOSED; one final narrow blocker** (schema_version never
  validated + writer-impossible [pending, completed] action sequence accepted) → surgical wave 5.
  **Sol-named Phase-8 hardening candidates** (carry into phase-8 planning): one browser-level
  writer→HTTP→React end-to-end test; responsive viewport/a11y automated coverage; backend-produced
  shared UI fixtures (generate frontend test fixtures from the real writer instead of hand-typed
  literals — closes the recurring fixture-honesty failure class permanently); remove the dead
  `dependency_graph_unknown` writer branch.

### Phase 7 final outcome — 2026-07-14

**COMPLETE. Sol round 5: SECOND-OPINION: APPROVE (no new exit-blocking findings); validator PASS;
phase gate 0 violations.** Final numbers: 20 backend API tests, 54-test assertion review suite
(975-test frontend total, failures = the 4 pre-existing baseline files only), tsc 0 errors,
codegen contract current. 8 commits on the worktree branch (a7d312b, 9f26638, 1507636, 77a54b0,
b95c1ab, 01b4f3f, d1228b0, 703a49c) squash-merged to main per direction.

**Review-round economics for the AAR**: 5 adversarial rounds (initial + 4 re-reviews), 5
remediation waves. Round-over-round the defect depth progressed: spec-copy/wiring → seam
semantics → validation strictness → primary-path liveness → envelope fidelity. The two most
expensive misses (stuck-hidden blocked receipts; no-op tsc gate) were both "does the gate
actually gate" failures. Runtime visual evidence remains deferred to logical P7-004 (physical
Phase 8) per plan.

### Gaps / out-of-plan findings

- **Stale OpenAPI snapshot on main**: the committed `src/research_foundry/api/openapi.json`
  had drifted well behind runtime routes (~2,250-line diff on regeneration, mostly unrelated to
  P6-000). The P4 "OpenAPI freeze" discipline was not being re-verified after later phases. P6-000
  absorbed the refresh; recommend a CI drift check (`pnpm codegen:check` equivalent for
  openapi.json itself) — candidate for physical Phase 8 hardening.
- **No claim→assertion linkage in run exports (P6-003 finding)**: run-export claims carry no
  `source_assertion_id`, so the audit workbench's assertion band/inspector activate only via a
  caller-supplied `assertionId` prop (future catalog deep link). Until exports link claims to
  persistent assertions, the stale-impact workbench is reachable but not data-driven from a
  run-local claim selection. Candidate: extend run-export schema + `run-export.ts` (dual-update
  rule) in a later phase.
- **No `assertion_id → event_id` documented path (P6-003 finding)**: `impactEventId` is an
  explicit prop; when absent the Impact section renders `Impact data unavailable` rather than
  fabricating an id. Verify in review whether `useAssertionImpact(assertionId)` alone should
  populate the section (the P6-000 route is keyed by assertion_id).
- **Lineage DTO omissions (P6-003 finding)**: `AssertionLineage` carries no qualifiers/access/
  rights (inspector combines with packet data) and no `exports` uses field (mockup pill omitted
  rather than invented).
- **No frontend plumbing for `RF_CANONICAL_CLAIMS_ENABLED`**: canonical-claim generated types
  exist, but no feature flag reaches the runs-viewer (explorer-verified). P6-003 must wire the
  signal; safe default when absent = assertion-only mode (a first-class state per design spec §5.4).
- **`replacement_edition_id` is always `null`**: P5 persisted receipts do not carry a separately
  authorized replacement-edition target, so the design-spec `Open replacement edition` affordance
  has no data path yet. UI renders the action only when the typed receipt supplies a target (so it
  will simply be absent). Backlog: persist/authorize replacement targets in receipts, then light up
  the affordance — flag for physical Phase 8/9 planning.
