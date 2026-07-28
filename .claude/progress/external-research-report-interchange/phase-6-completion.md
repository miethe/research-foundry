---
type: report
schema_version: 2
doc_type: report
title: "Phase 6 Completion — Hardening, Documentation, and Exact-Tree Closeout"
report_category: other
feature_slug: external-research-report-interchange
created: 2026-07-27
updated: 2026-07-27
status: completed
owners: ["python-backend-engineer"]
related_documents:
  - docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
  - docs/dev/architecture/external-research-handoff-contract.md
  - docs/user/external-research-interchange.md
  - .claude/findings/eri-p1-contract-audit-gpt56.md
  - .claude/progress/external-research-report-interchange/phase-4-completion.md
  - .claude/progress/external-research-report-interchange/phase-5-completion.md
  - .claude/progress/external-research-report-interchange/phase-6-progress.md
---

# Phase 6 Completion — Hardening, Documentation, and Exact-Tree Closeout

This is the implementer's (python-backend-engineer) completion note for ERI-6.0 through ERI-6.4.
**ERI-6.5 (task-completion-validator then Karen exact-tree passes) is explicitly NOT part of this
note** — it is left `pending` in `phase-6-progress.md` for those reviewers to run against this
exact tree. Accuracy matters more here than a clean-looking result.

## 1. ERI-6.0 (added scope) — audit finding #9 disposition: **CLOSED, option (a)**

Phase 4 and Phase 5 both recorded audit #9 as still open on both halves at the time they shipped:
`governance_policy_digest` was a fixed digest over an explicitly-labeled "not implemented"
placeholder, and no reauthorization gate existed anywhere in `stage()`. This phase closes both
halves for real by reusing `services/rbac_store.py` — RF's one existing durable caller-identity/
membership authority — introducing no second authorization store.

**What changed** (`src/research_foundry/services/external_research_interchange.py`,
`src/research_foundry/services/external_research_import.py`):

- `compute_governance_policy_digest()` now digests `{"governance_gate": "eri_step0_v1",
  "rbac_schema_version": rbac_store.RBAC_SCHEMA_VERSION, "canonical_roles": [...]}` — a real,
  versioned ruleset snapshot, not a placeholder note. A real RBAC schema/role-catalogue change now
  legitimately produces a different `receipt_digest` for every subsequent import.
- New `CallerContext` (principal_id, workspace_id, principal_type, optional token_id) and
  `authorize_caller()` implement contract §2.4 Step 0 / §1.6: a fresh (never cached) `rbac_store`
  lookup gating every receipt existence check — both `stage()`'s own replay lookup and
  `import_external_report()`'s separate pending-checkpoint pre-check. Failure raises
  `CallerNotAuthorizedError` — a non-receipt denial; no file is written under the interchange root
  at all (verified directly by
  `test_no_membership_denies_stage_before_any_receipt_created`).
- `caller=None` — the only value the bare `rf intake external-report` CLI passes today — is
  single-operator-trust and behaves identically to before this phase. **No CLI flag was added.**
  This is a deliberate scope boundary, stated loudly in the contract addendum (§1.6a) and here: RF's
  own architecture (`api/auth/rbac.py`'s module docstring) classifies every CLI mutation entry point
  in this codebase as single-operator-trust, with RBAC enforced only at the HTTP router layer.
  Adding a bare-CLI actor flag only for ERI would have been inconsistent with that precedent, not a
  fix. The real gate lives at the service-API layer (`stage()`/`import_external_report()`), which
  `phase-5-completion.md` already identified as the intended future Operator-MCP seam.

**New tests** (`tests/unit/test_external_research_caller_authorization.py`, 13 tests): caller=None
unaffected; authorized member stages/replays; caller with no membership denied before any receipt
file exists; workspace mismatch denied; membership deleted between staging and replay denies the
replay (the exact "revoked caller" scenario); same for a revoked access token; `import_external_
report`'s own separate pre-check is gated too; `governance_policy_digest` is stable, and a real RBAC
schema-version change yields a genuinely different `receipt_digest` end-to-end through `stage()`.

Full disposition, including the exact scope boundary and rationale, is recorded in the contract at
`docs/dev/architecture/external-research-handoff-contract.md` §1.6a.

## 2. Files changed / created

New:
- `tests/unit/test_external_research_caller_authorization.py` (13 tests) — ERI-6.0.
- `tests/integration/test_external_research_cross_profile_compat.py` (14 tests) — ERI-6.1.
- `tests/integration/test_external_research_adversarial_matrix.py` (6 tests) — ERI-6.2.
- `tests/integration/test_external_research_large_report_resume.py` (6 tests) — ERI-6.3.
- `docs/user/external-research-interchange.md` — ERI-6.4 user guide.
- `docs/project_plans/design-specs/external-research-{provider-automation,transport-containers,citation-recovery,public-interchange}.md` — ERI-6.4 promotable deferred specs for ERI-DF-1..4.

Additive edits:
- `src/research_foundry/services/external_research_interchange.py` — `CallerContext`,
  `CallerNotAuthorizedError`, `authorize_caller()`, real `compute_governance_policy_digest()`,
  `stage(..., caller=None)`. No existing behavior changed for any caller that omits `caller`.
- `src/research_foundry/services/external_research_import.py` — `import_external_report(...,
  caller=None)`, gates its own pending-checkpoint pre-check.
- `docs/dev/architecture/external-research-handoff-contract.md` — §1.6a addendum; open-items entry
  for `governance_policy_digest` marked closed; `updated: 2026-07-27`.
- `docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md`
  — `deferred_items_spec_refs` populated with the four new spec paths.
- `README.md` — new "External Research Report Interchange (ERI)" section + command inventory entry.
- `CHANGELOG.md` — new `[Unreleased]` entry under Added.
- `.claude/skills/research-foundry/SKILL.md` and `.agents/skills/research-foundry/SKILL.md` — route
  table row + command note for `rf intake external-report` (both copies updated; `.agents/`'s copy
  was already independently behind `.claude/`'s on unrelated commands before this phase — not
  otherwise reconciled here, out of scope).
- `.claude/progress/external-research-report-interchange/phase-6-progress.md` — ERI-6.1..6.4 marked
  `completed` via CLI (`update-status.py`); ERI-6.5 left `pending` for the reviewer gate.

No existing production file's prior behavior was changed for any caller that does not supply the
new optional `caller` parameter — verified by the full regression run below (494 passed, 0 failed,
0 modified pre-existing tests).

## 3. AC ERI-1..7 evidence map

#### AC ERI-1: One packet contract covers five producer profiles
- **Schema-level** (unchanged, Phase 1/3): `tests/unit/test_external_research_schemas.py`
  (golden/negative fixtures), `tests/unit/test_external_research_profiles.py` (5 profiles + the
  injection fixture normalize to one canonical shape; that module explicitly does not call the
  importer service).
- **Runtime, NEW this phase**: `tests/integration/test_external_research_cross_profile_compat.py`
  — all 5 profile fixtures staged through the REAL `import_external_report` pipeline (dry-run and
  real import + replay), never `blocked`; all 5 produce identical `schema_major_versions`.

#### AC ERI-2: Import receipt is immutable and replay-idempotent
- Phase 2 (unchanged): `tests/unit/test_external_research_interchange.py` — replay/true-conflict/
  lease/dry-run/interruption-resume tests.
- NEW this phase: `tests/unit/test_external_research_caller_authorization.py` (governance-policy-
  change → distinct receipt identity; revoked-caller replay denial) and
  `tests/integration/test_external_research_large_report_resume.py` (batched/unbatched convergence
  at 120-action scale; corrupted-effect and checkpoint-context-mismatch fault tests fail closed via
  `StagingIntegrityError`).

#### AC ERI-3: Completeness and quarantine remain explicit
- Phase 4 (unchanged): `tests/integration/test_external_research_resolution.py` — full H3 scenario
  matrix (zero/multiple/drift/conflict, authorization, cross-workspace, promotion).
- NEW this phase: `tests/integration/test_external_research_adversarial_matrix.py` —
  `test_receipt_never_carries_the_source_citation_candidate_reason_vocabulary` proves, end to end
  through a real import, that none of the 14 closed-vocabulary reason-code strings nor a bare
  `reason_code` key ever appears on a caller-visible receipt — only `audit_ref`.

#### AC ERI-4: Promotion requires exact existing evidence authority
- Phase 4 (unchanged): `TestPromotion` in `test_external_research_resolution.py` —
  `test_promotion_never_self_assigns_verified` and friends.
- NEW this phase: `tests/integration/test_external_research_cross_profile_compat.py`'s duplicate-
  authority scan (`test_eri_service_modules_define_no_second_evidence_authority`,
  `test_eri_resolution_module_calls_the_existing_assertion_registry`) — a source-level scan proving
  ERI's own files define no second `SourceEdition`/`Passage`/`SourceAssertion`/`ingest_edition`/
  `find_exact_passages`/`resolve_passage` — they only ever call `AssertionRegistry`'s existing ones.
  Plus a legacy-read regression test (`test_legacy_assertion_registry_ingest_and_read_unaffected`)
  proving a plain, ERI-unrelated `AssertionRegistry` ingest/replay cycle is unaffected by ERI having
  been exercised earlier in the same process.

#### AC ERI-5: Large imports resume without repeated effects
- Phase 5 (unchanged): `tests/integration/test_external_research_import.py` — 3-source convergence,
  cancellation, unlimited-limit tests.
- NEW this phase: `tests/integration/test_external_research_large_report_resume.py` — 120-action
  (60 sources + 60 candidates) convergence between a 12-call batched run (`--limit 10`) and an
  unbatched run, byte-identical `receipt_digest`/receipt/effect-digests; batch-boundary conditions
  (limit with a remainder, limit exceeding total, limit=1 exact one-at-a-time); two fault tests
  (corrupted effect record, checkpoint context mismatch) both fail closed via `StagingIntegrityError`
  rather than silently completing. Indicative (explicitly labeled, no production claim) elapsed/
  memory evidence captured below (§5).

#### AC ERI-6: Legacy and authority boundaries remain intact
- `tests/integration/test_external_research_cross_profile_compat.py`'s legacy-read test + duplicate-
  authority scan (above). `tests/unit/test_external_research_cli.py` (Phase 5, unchanged) confirms
  the CLI surface is additive-only under the existing `intake_app` group. The full regression run
  (§4) confirms zero existing tests were modified and all pass unchanged.

#### AC ERI-7: Acquisition and vendor fields remain hostile-input safe
- Phase 4 (unchanged): `tests/unit/test_source_acquisition_policy.py` (65 tests — full SSRF/DNS/
  redirect/rebinding/IPv6-transition matrix).
- NEW this phase, closing `phase-4-completion.md`'s explicitly recorded gap ("unauthorized local/
  file ... covered at the acquisition-gate unit-test layer but not re-asserted with a dedicated
  resolver-level integration test"): `tests/integration/test_external_research_adversarial_matrix.py
  ::test_unauthorized_local_or_non_http_scheme_quarantines_at_resolver_layer` — `file:///etc/passwd`,
  `file://localhost/etc/passwd`, and `ftp://...` locators fed through the REAL, end-to-end
  `import_external_report` pipeline (real `source_acquisition_policy.acquire`, not the fake used by
  the resolution-layer unit tests) all quarantine, never fetch. Same module's
  `test_injection_profile_imports_cleanly_with_no_control_surface_effect` runs the Phase-3 injection
  fixture through the full real pipeline without incident.

## 4. Full regression gate

```
tests/unit/test_external_research_schemas.py
tests/unit/test_external_research_interchange.py
tests/unit/test_external_research_profiles.py
tests/unit/test_source_acquisition_policy.py
tests/integration/test_external_research_resolution.py
tests/integration/test_external_research_import.py
tests/unit/test_external_research_cli.py
tests/test_schema_validation.py
tests/unit/test_external_research_caller_authorization.py      (NEW, ERI-6.0)
tests/integration/test_external_research_cross_profile_compat.py (NEW, ERI-6.1)
tests/integration/test_external_research_adversarial_matrix.py   (NEW, ERI-6.2)
tests/integration/test_external_research_large_report_resume.py  (NEW, ERI-6.3)
```

**494 passed, 0 failed**, 27.83s — up from the pre-Phase-6 baseline (the same file list minus the
four new files: 456 passed per `phase-5-completion.md`'s own gate + `test_external_research_
caller_authorization.py` not existing yet). Zero pre-existing tests modified or weakened.

`ruff check` on all 6 new/changed files reports no findings on any line this phase authored.
Pre-existing findings remain on lines this phase did not touch, and all are present in `main`'s
own copy of the same files (verified by running ruff against `git show main:<file>`):
one `UP012` on `external_research_interchange.py` (already recorded in `phase-5-completion.md`,
at a shifted line number due to insertions above it), and three findings on `cli_commands.py`
(`F841`/`F541`). Corrected from an earlier, imprecise "clean except one finding" statement —
the count is four pre-existing findings, not one.
`mypy --ignore-missing-imports` on both changed production files: 0 errors.

## 5. ERI-6.3 indicative evidence (explicitly NOT a production performance claim)

Captured from `test_large_packet_batched_resume_converges_with_uninterrupted_run` on this
development machine, fake in-process acquisition (`_fake_acquire`, zero real network I/O), 120
canonical actions (60 sources + 60 candidates):

| Mode | Calls | Wall time | Peak traced Python memory |
|---|---|---|---|
| Batched (`--limit 10`, resumed) | 12 | 11.92s | 4055.4 KiB |
| Unbatched (`--limit` unset) | 1 | 4.71s | 1470.5 KiB |

The batched run's higher wall time is expected and not concerning: each of its 12 calls
independently re-opens an `ExternalResearchInterchange`/`AssertionRegistry`/RBAC-store connection
and re-derives identity, work the single unbatched call only does once. This is indicative of
per-call fixed overhead on a dev machine with fake acquisition, not of real acquisition latency
(which dominates in any real import) or of any specific deployment's hardware. No production
performance claim is made from these numbers.

## 6. Remaining gaps — honest, not swept under the completion note

1. **ERI-6.5 (final AC evidence + reviewer gate) is NOT done.** This note maps ACs to evidence for
   the reviewers; it does not substitute for their exact-tree `task-completion-validator` then Karen
   passes, which remain `pending`.
2. **The contract §4.3.1 timing-uniformity floor (fresh-acquisition vs. stored-identity-reuse
   minimum-latency floor) is still not implemented anywhere in this codebase.** Both
   `phase-4-completion.md` and `phase-5-completion.md` carried this forward as unimplemented; this
   phase does not implement it either — it was not in ERI-6.0's required scope (that was audit #9),
   and the contract itself (§4.3.1) already scopes the broader timing-variance question as an
   accepted v1 residual risk pending a "dedicated future hardening phase." Do not read this phase's
   name ("Hardening") as having closed it.
3. **CLI-level caller identity was deliberately NOT wired.** `rf intake external-report` has no
   `--actor`/token flag; `caller` is reachable only via the Python service API
   (`import_external_report`/`stage()`). See §1 above for the explicit rationale. This is a scope
   decision, not an oversight — but a reviewer should confirm they agree with it before treating
   audit #9 as fully closed for every conceivable future caller, not just the service-API surface.
4. **The access-controlled audit store `audit_ref` resolves against is still not a concrete,
   built artifact** (contract §4.6, carried from Phase 1 through every phase since — unaffected by
   this phase).
5. **The four new deferred design specs (ERI-DF-1..4) are authored but intentionally not
   promoted** — none of their stated promotion triggers are currently satisfied (see each spec's own
   "Trigger for promotion" section).
6. **`.agents/skills/research-foundry/SKILL.md` was already independently behind `.claude/skills/
   research-foundry/SKILL.md`** on several unrelated commands (e.g. missing `rf search`/`rf fetch`/
   `rf catalog`/`rf workspace` rows) before this phase touched either file. Only the ERI-specific row
   was added to both; the pre-existing drift between the two copies was not reconciled — out of this
   phase's scope.
7. **Non-PDF HTML extraction remains stdlib-only** (`html.parser`) and the RAL run-scoping seam
   question (packet-scoped source-card equivalent vs. direct `AssertionRegistry` calls) remains as
   Phase 4 left it — both unaffected by this phase.
