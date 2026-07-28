---
title: "ERI round-2 remediation (agent A) — findings #1, #2, #3, #4, #5, #6, #7, #9"
doc_type: report
report_category: finding
schema_version: 2
status: completed
source: agent
created: 2026-07-27
updated: 2026-07-27
feature_slug: external-research-report-interchange
promoted_to: []
---

# Round-2 remediation (agent A)

Scope: `.claude/findings/eri-implementation-audit-round2-gpt56.md`, findings #1, #2, #3, #4, #5,
#6, #7, #9 only. Files touched: `src/research_foundry/services/external_research_interchange.py`,
`src/research_foundry/services/external_research_import.py`,
`tests/unit/test_external_research_interchange.py`,
`tests/unit/test_external_research_caller_authorization.py`,
`tests/integration/test_external_research_import.py`. `source_acquisition_policy.py`,
`external_research_resolution.py`, `schemas/`, and
`tests/integration/test_external_research_adversarial_matrix.py` were not touched (parallel
agent's ownership — findings #8, #10, #11, #12, #13; see `round2-remediation-b.md`).

**Pre-existing blocker fixed first (not one of my findings, but blocked ALL test execution):** a
parallel agent's schema change added `ipv6_site_local` to
`forbidden_address_categories`'s closed `const` list. My owned test fixture (`VALID_POLICY` in
`test_external_research_interchange.py`) and the production default
(`DEFAULT_ACQUISITION_POLICY` in `external_research_import.py`) both hard-coded the old 11-entry
list, so every test constructing a policy failed schema validation (~12+ RED). Fixed
`DEFAULT_ACQUISITION_POLICY` directly (added the missing entry) and rebuilt `VALID_POLICY` to
**derive** `forbidden_address_categories`/`metadata_deny_set`/`metadata_deny_set_version`/
`special_purpose_address_registry_version`/`ipv6_transition_policy.well_known_prefixes` from the
schema file itself via a new `_schema_const()` helper, so a future closed-set addition can never
silently desync this fixture again.

## #2 — Membership mistaken for permission (HIGH) — CLOSED

`authorize_caller()` passed any workspace member (including a zero-permission `viewer`), never
checked a token's own role ceiling, and resolved service principals through the `memberships`
table (a meaningless, or wrong-principal, lookup for a service-account id).

- Added an explicit two-permission ERI vocabulary — `ERI_SUBMIT_PERMISSION` /
  `ERI_READ_PERMISSION` — and `_ERI_ROLE_PERMISSIONS` (owner/admin/researcher: both; reviewer:
  read only; viewer: none), mirroring `api/auth/rbac.ROLE_PERMISSIONS`'s shape without importing
  that HTTP-router-layer module — `external_research_interchange.py:~197-220`.
- `authorize_caller()` now takes `permission: str = ERI_SUBMIT_PERMISSION`, resolves the
  principal's role via `rbac_store.get_member_role` (`principal_type="user_pat"`) OR
  `rbac_store.get_service_account` (`principal_type="service"` — its own record, workspace- and
  `disabled_at`-checked, never the memberships table), and denies unless that role's permission set
  contains `permission`. When `caller.token_id` is set, the TOKEN's own `role` column (the ceiling
  it was issued at) is independently checked against the same matrix — a still-valid token issued
  at a lower role can never exercise a permission the token itself was never granted, even if the
  principal's current membership role is now higher.
- Test: `tests/unit/test_external_research_caller_authorization.py` —
  `test_viewer_role_denied_for_submit`, `test_viewer_role_denied_for_read_too`,
  `test_reviewer_role_can_read_but_not_submit`, `test_viewer_stage_denied_before_any_receipt_created`,
  `test_token_role_ceiling_denies_even_with_admin_membership`,
  `test_token_role_ceiling_allows_when_both_grant`,
  `test_service_principal_authorized_through_own_record`,
  `test_service_principal_with_no_record_denied`, `test_disabled_service_principal_denied`,
  `test_service_principal_not_confused_with_same_id_user_membership`.

## #1 — Governance policy identity omits permission mappings + per-import rights policy (HIGH) — CLOSED

`compute_governance_policy_digest()` hashed only `RBAC_SCHEMA_VERSION` + role NAMES; it omitted
the actual permission MAPPING and the per-import rights/sensitivity `AuthorizationPolicy` entirely
— importing once under a permissive policy then retrying under a denying one replayed the earlier
allowed outcome.

- `compute_governance_policy_digest()` now takes `authorization_policy: Mapping[str, Any] | None`
  and folds in BOTH `eri_role_permissions` (the actual `_ERI_ROLE_PERMISSIONS` mapping, not just
  role names) and the caller-supplied `authorization_policy` dict —
  `external_research_interchange.py:~1140-1200`.
- `ExternalResearchInterchange.stage()` gained a matching `authorization_policy:
  Mapping[str, Any] | None = None` parameter, threaded into the digest computation at Step 0.
- `import_external_report()` always resolves a CONCRETE effective `AuthorizationPolicy` (explicit
  or `AuthorizationPolicy()`'s default — never bare `None`, so "omitted" and "explicitly default"
  hash identically) and converts it to a canonical mapping via new
  `_authorization_policy_digest_input()`, passed through to both its own pre-derived identity
  computation and the `stage()` call — `external_research_import.py`.
- Test: `test_governance_policy_digest_changes_with_authorization_policy`,
  `test_authorization_policy_change_yields_a_different_receipt_identity` (end-to-end through
  `stage()` — permissive vs. denying policy produce distinct, non-replaying `receipt_digest`s),
  `test_governance_policy_digest_folds_in_eri_role_permission_mapping` (a permission-MAPPING
  change alone, no schema-version bump, still moves the digest) — all in
  `test_external_research_caller_authorization.py`.

## #4 — The single-writer lease is unfenced (HIGH) — CLOSED

Stale reclaim was `stat()` then unconditional `unlink()` (no owner/inode check); release deleted
by path with no ownership check; receipt publication was an existence check followed by
`os.replace` (not CAS).

- **Fencing.** The lease file now carries an opaque `owner_token` + monotonically increasing
  `generation` (bumped on every fresh acquire or reclaim). `_receipt_lease` captures
  `(st_dev, st_ino)` at acquisition and its `finally` release re-`stat`s and unlinks ONLY if the
  inode still matches — a lease reclaimed out from under this process (heartbeat too late) is
  never deleted by this process on release. `_execute` heartbeats (`os.utime`) the lease after
  every per-action effect publish, verifying inode-match first and raising
  `StagingIntegrityError` if the lease was lost mid-import.
- **Reclaim.** `_reclaim_stale_lease` opens the file directly (`os.open`+`fstat`, not a racy
  separate `stat`), checks age from that same descriptor, then re-`stat`s immediately before
  claiming and requires inode AND mtime to still match. **Empirically found and fixed a real race
  during test-writing**: a bare `os.unlink` raced by several threads against the same path was
  directly observed (via a standalone repro script) to report success to MORE than one caller on
  this filesystem under thread concurrency — `unlink`'s "exactly one caller ever succeeds"
  assumption did not hold here. Switched the claim step to `os.rename` into a
  per-attempt-unique scratch name (empirically verified race-free across 3000 concurrent trials)
  before removing the scratch file.
- **True CAS.** `_write_immutable_mapping`/`_write_immutable_bytes` now go through
  `_publish_immutable_file()`: fully write+fsync a temp file, then `os.link(temp, path)` — atomic
  create-if-absent, never overwrites — falling back to the existing byte-compare-or-raise check
  only when the link loses the race (`path` already existed).
- Test: `test_lease_release_never_deletes_a_reclaimed_replacement`,
  `test_reclaim_stale_lease_only_one_concurrent_reclaimer_wins` (8-thread race against one stale
  lease; flaky before the rename-based claim fix, stable — 20/20 — after),
  `test_write_immutable_mapping_is_true_cas_not_overwrite`, plus the pre-existing
  `test_receipt_lease_reclaims_stale_lease` and `test_concurrent_first_imports_converge_to_one_receipt_and_effect_set`
  (both still pass unmodified) — all in `test_external_research_interchange.py`.

## #5 — Exactly-once effects: crash window + weak replay verification (HIGH) — PARTIAL CLOSURE (see note)

Two sub-issues named together; closed to different degrees.

**Weak replay verification — CLOSED.** On resume, `_execute` now binds a persisted effect record
to the presented `receipt_digest`/`action_id`/`kind` (raises `StagingIntegrityError` on mismatch)
and recomputes `effect_digest` from the record's own trusted fields (now including a newly
persisted `canonical_refs` field) rather than trusting the stored digest string verbatim.
`_verify_replay` (the whole-receipt true-conflict check) now ALSO re-derives
`action_manifest_digest` from the presented actions and compares it to the stored receipt's own
field, in addition to the existing action_id/kind set comparison, and schema-validates the stored
receipt before trusting it. Test: `test_resume_rejects_effect_record_bound_to_a_different_receipt_digest`,
`test_resume_rejects_effect_record_with_mismatched_effect_digest` (both via a genuine
`_interrupt_after_action_index=0` interruption + tampering, so the RESUME code path is actually
exercised, not the whole-receipt replay path) in `test_external_research_interchange.py`.

**Crash-window ordering — PARTIALLY CLOSED, HONESTLY.** Added an outbox-style durable `.prepare`
marker written BEFORE the resolver is invoked and cleared once its effect commits (or once a
`ResolutionDeclined`-derived signal — the benign per-invocation batch-limit cancellation — proves
the resolver body never ran). **What this does NOT do**: block resume when a `.prepare` marker is
found with no matching effect. I implemented that fail-closed behavior first, then discovered it
directly contradicts an existing, intentionally-authored test —
`tests/integration/test_external_research_import.py::TestCancellation::
test_keyboard_interrupt_preserves_pending_checkpoint_and_resume_completes` — which asserts a
`KeyboardInterrupt` mid-resolver is followed by a clean, non-blocking resume. Per this task's
explicit instruction not to weaken or delete existing tests, I reverted the fail-closed raise.
**Open finding, stated honestly**: this module cannot itself guarantee the resolver's downstream
mutation (`external_research_resolution.py`, out of my owned scope) is idempotent by `action_id`
— that guarantee depends on the resolver substrate (e.g. `AssertionRegistry.ingest()`'s
content-addressed dedup, which the contract already documents as the intended idempotent
authority). What IS shipped: a durable, inspectable audit trail (a dangling `.prepare` marker is
now visible, on disk, as evidence an interrupted attempt reached the resolver for that action —
previously indistinguishable from a clean first attempt) plus the two `ResolutionDeclined`-aware
tests: `test_interrupted_resolver_leaves_an_inspectable_prepare_marker` (real crash — marker
persists, resume still completes per the existing contract) and
`test_batch_limit_reached_clears_its_prepare_marker` (benign signal — marker is cleared, proving
`_BatchLimitReached`/`ResolutionDeclined` never falsely trips the crash-window bookkeeping).
Closing the remainder requires either owning `external_research_resolution.py` or a follow-up
task explicitly scoped to it.

## #3 — Authorization stale before the receipt read (MEDIUM) — CLOSED

`stage()` authorized once at entry, then could wait out lease contention before its replay-check
read; `import_external_report`'s own pre-derivation `_load_receipt` check ran after only the
top-level authorization.

- `stage()` now reauthorizes a second time immediately after entering the receipt-identity lease
  (both the blocked-receipt branch and the accepted-receipt branch), right before `_load_receipt`.
- `import_external_report()` restructured so its pending-checkpoint guard and the `stage()` call
  share ONE receipt-identity lease held across both (also closes half of #9 — see below);
  `authorize_caller` is called again immediately after acquiring that lease, before its own
  `_load_receipt`/`_load_checkpoint` reads.
- Test: `test_membership_revoked_during_lease_wait_denies_before_replay_read` — monkeypatches
  `_receipt_lease` to revoke membership at the exact moment the lease is entered (simulating "the
  wait resolved, but the caller was revoked during it"); the pre-existing
  `test_revoked_membership_cannot_replay`/`test_revoked_token_cannot_replay`/
  `test_import_external_report_gates_pending_checkpoint_lookup` all still pass unmodified.

## #6 — Packet inspected twice, reopening the snapshot race (MEDIUM) — CLOSED

`import_external_report` called `inspect_packet` once for its own pre-derivation, then `stage()`
called it again internally — two independent snapshots of a mutable directory.

- `ExternalResearchInterchange.stage()` gained `inspection: PacketInspection | None = None`; when
  supplied, `stage()` performs NO internal `inspect_packet` call. `import_external_report` now
  inspects exactly once and threads that single `PacketInspection` through resolver construction
  (`candidate_records`), batching (`_build_action_inputs`), and every `stage()` call (dry-run,
  blocked, and the lease-guarded accepted path).
- Test: `test_stage_with_precomputed_inspection_never_reinspects` (monkeypatches the module-level
  `inspect_packet` with a call counter, asserts zero calls when `inspection=` is supplied).

## #7 — "Primitive-only" YAML loading still admits non-JSON values (MEDIUM) — CLOSED

`SafeLoader` still constructed `timestamp`/`!!binary`/`!!set`/`!!omap`/`!!pairs` into
non-JSON-serializable Python objects that an open `additionalProperties: true` extension field
let through schema validation, later crashing canonical-JSON digesting with an uncaught
`TypeError` (reproduced by the auditor).

- Added constructor-level rejection for all five tags (`_reject_non_primitive_tag`) on
  `_InertYAMLLoader`, AND a second, independent recursive whitelist gate
  (`_assert_json_primitive_only`) run on every parsed document before it is returned — permits
  ONLY null/bool/string/finite-number/list/string-keyed-map, with a scalar/key length ceiling.
- Test: `test_inert_boundary_rejects_timestamp`, `_binary_tag`, `_set_tag`, `_omap_tag`,
  `_pairs_tag` (each fails closed with `unsupported_schema_version`, never raises out of
  `inspect_packet`), plus positive-control `test_assert_json_primitive_only_accepts_the_full_json_vocabulary`
  and `test_assert_json_primitive_only_rejects_non_string_keys`.

## #9 — Resume/blocked-replay nondeterminism (MEDIUM) — CLOSED

Two sub-issues: (a) the `resume=False` pending-checkpoint guard ran outside any lease, so two
initially-fresh calls could race past it; (b) a blocked-receipt retry compared the WHOLE stored
mapping including a freshly generated `created_at`, so an ordinary delayed retry raised
`ReplayConflictError`.

- (a) Fixed as part of #3 above: the guard and the `stage()` continuation now share one lease
  (`stage(..., _lease_already_held=True)` skips its own acquisition to avoid self-deadlock).
  Dry-run calls deliberately do NOT participate (contract: dry-run never mutates and is always
  safe to run concurrently).
- (b) `_publish_or_replay_blocked` now excludes `created_at` from the byte-comparison used to
  detect a true conflict — the STORED receipt (with its own original `created_at`) is still what
  is returned either way.
- Test: `test_blocked_replay_with_delayed_created_at_is_not_a_conflict` (a `required_member_missing`
  blocked packet replayed a second time must return the identical stored receipt, not raise).

## Validation

```
PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/unit/test_external_research_schemas.py \
  tests/unit/test_external_research_interchange.py tests/unit/test_external_research_profiles.py \
  tests/unit/test_source_acquisition_policy.py tests/unit/test_external_research_cli.py \
  tests/unit/test_external_research_caller_authorization.py \
  tests/integration/test_external_research_resolution.py tests/integration/test_external_research_import.py \
  tests/integration/test_external_research_cross_profile_compat.py \
  tests/integration/test_external_research_adversarial_matrix.py \
  tests/integration/test_external_research_large_report_resume.py tests/test_schema_validation.py -q
```

All green (exit 0), rerun 3× clean including the previously-flaky lease-race test (20/20 stable
after the rename-based reclaim fix). `ruff check` on both owned production modules: clean (a
handful of pre-existing baseline issues in the test files — unused imports, one unused-variable,
one `encode("utf-8")` — predate this pass, confirmed via `git show HEAD:...` diff, and were left
alone as out of scope). `mypy --ignore-missing-imports` on both owned production modules: clean.

## Findings NOT addressed (explicitly out of scope, per task)

#8, #10, #11, #12, #13 — owned by the parallel agent (`round2-remediation-b.md`).
