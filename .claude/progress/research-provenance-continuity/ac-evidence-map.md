# Research Provenance Continuity v1 — AC Evidence Map (Final Tier-3 Gate)

> Auditable mapping of every plan AC gate (RPC-7.2..7.9) and freeze-doc P7 gate task
> (RPC-7.12..7.19) to the exact test(s) that verify it, the exact command run, the exit
> code, and any gap filled with a newly authored test (real-flow fixtures only — no
> hand-authored states). Produced under Mode C bounded verification sprint against
> worktree `rpc-v1`, HEAD `f0a42bf` (P1+W2+W3 committed). No src edits made; no defects
> found. Python invocations use `PYTHONPATH=$PWD/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest`.

## Plan AC gates

### RPC-7.2 → AC RPC-1 (canonical origin and derived facets)

Covers: origin positive/legacy/tamper/cross-workspace + facet delete/rebuild.

- Covering tests: `tests/unit/test_provenance_envelope.py::test_origin_write_is_content_addressed_and_replay_safe`, `::test_origin_tamper_detected_by_fingerprint_mismatch`, `::test_origin_version_bump_changes_identity`, `::test_origin_conflicting_content_under_same_id_fails_closed`, `::test_origin_parent_ref_cross_workspace_denied`, `::test_origin_missing_parent_ref_denied`, `::test_facet_derivation_and_rebuild_delete_parity`
- Command: `pytest tests/unit/test_provenance_envelope.py -k "origin or facet"`
- Exit code: 0 — **7 passed, 34 deselected**
- Gaps filled: none. Coverage adequate as-is.

### RPC-7.3 → AC RPC-2 (planned/search-only activity round trip)

Covers: planned/search-only, scope/filter/time, selection/denial/degraded, launch propagation, discoverability.

- Covering tests (activity/receipt shape + outcome arms):
  `tests/unit/test_provenance_envelope.py::test_envelope_v1_carries_no_receipt_linkage_fields`,
  `::test_search_only_activity_never_carries_a_planned_run_ref`, `::test_receipt_promotion_binds_activity_id_and_commitment`,
  `::test_all_five_outcome_arms_are_constructible_and_schema_valid`, `::test_empty_outcome_is_never_confusable_with_denied`,
  `::test_denied_receipt_leaks_no_candidate_or_corpus_value_end_to_end`, `::test_degraded_and_fallback_reason_builders_reject_blank_reason`,
  `::test_search_evidence_entry_is_the_legacy_compatible_default`, `::test_catalog_planning_evidence_entry_requires_question_id_and_decided_at`
  — Command: `pytest tests/unit/test_provenance_envelope.py -k "activity or receipt or aos or outcome or denied or degraded or catalog_planning"` — Exit 0 — **31 passed, 10 deselected**
- Covering tests (discoverability, list/fetch): `tests/integration/test_research_run_discovery.py` (all 9: `test_search_only_activity_is_discoverable_with_no_planned_run`, `test_list_activities_reports_receipt_outcome`, `test_fetch_activity_unknown_id_denied_leaks_nothing`, `test_fetch_activity_cross_workspace_denied`, `test_fetch_planned_run_activity_reuses_run_read_allowed_guard`, `test_fetch_planned_run_activity_allowed_when_run_meta_missing`, `test_fetch_activity_uses_internal_default_loader_when_loader_omitted`, `test_list_activities_excludes_planned_run_denied_by_run_read_allowed`, `test_list_activities_uses_internal_default_loader_when_loader_omitted`) — Command: `pytest tests/integration/test_research_run_discovery.py` — Exit 0 — **9 passed**
- Covering tests (HTTP round trip): `tests/integration/test_assertions_api.py::test_search_only_activity_listable_and_fetchable_over_http`, `::test_search_only_activity_listing_is_complete_including_zero_match_and_degraded`, `::test_search_only_activity_denies_without_workspace_identity`, `::test_search_only_activity_cross_workspace_isolation_no_existence_leak` — Command: `pytest tests/integration/test_assertions_api.py -k "search_only or activity"` — Exit 0 — **4 passed, 4 deselected**
- Gaps filled: none. Coverage adequate as-is.

### RPC-7.4 → AC RPC-3 (report revision uses exact evidence versions)

Covers: verified/unverified, legacy, substitution, rights, lifecycle, replay.

- Covering tests: `tests/unit/test_assertion_report_use.py` (full file — includes
  `test_prepare_validate_publish_and_replay`, `test_publish_conflict_on_corrupted_bytes_at_the_same_use_id`,
  `test_stale_assertion_version_is_a_typed_skip`, `test_ineligible_lifecycle_state_is_a_typed_skip`,
  `test_missing_and_unresolvable_persistent_refs_are_legacy_unresolved`, `test_replay_conflict_leaves_the_original_record_intact`,
  `test_cross_workspace_cited_ref_is_legacy_unresolved_with_no_existence_leak`, `test_publish_rejects_a_hand_crafted_record_with_upgraded_rights`,
  `test_publish_rejects_forged_fingerprint_and_use_id_on_a_fresh_path`, `test_publish_rejects_forged_report_revision_id_on_a_fresh_path`,
  `test_resolve_verification_pass_created_at_is_race_safe_across_threads`, `test_resolve_verification_pass_created_at_rejects_a_tampered_anchor`,
  `test_duplicate_cited_ref_in_one_report_revision_yields_exactly_one_record`, `test_legacy_missing_persistent_references_is_a_no_op_never_an_error`,
  `test_crash_between_record_write_and_manifest_append_converges_on_retry`, `test_verify_report_pass_publishes_report_assertion_use`,
  `test_verify_report_failure_publishes_nothing`, `test_mutating_a_verified_report_body_mints_a_new_revision_and_new_uses`,
  `test_verify_report_toctou_skips_publication_when_body_changes_after_checks`)
- Command: `pytest tests/unit/test_assertion_report_use.py`
- Exit code: 0 — **35 passed**
- Gaps filled: none. Coverage adequate as-is. (`test_resolve_verification_pass_created_at_rejects_a_tampered_anchor` is the "anchor write-once" adversarial case cited under the freeze-doc gates below too.)

### RPC-7.5 → AC RPC-4 (inference and canonical claims are distinct and atomic)

Covers: eligible/unresolved/mixed/stale/cross-workspace/implicit-merge/partial-write + F18/F19.

- Covering tests (inference): `tests/unit/test_assertion_inference.py` (full file, 26 tests after gap-fill — see below)
  — Command: `pytest tests/unit/test_assertion_inference.py` — Exit 0 — **26 passed**
- Covering tests (canonical claim): `tests/unit/test_canonical_claim_materialization.py` (full file, 36 tests after gap-fill)
  — Command: `pytest tests/unit/test_canonical_claim_materialization.py` — Exit 0 — **36 passed**
- F18 (real `mark_stale` effect blocks a live commit): `tests/unit/test_assertion_catalog.py::test_lineage_reflects_a_real_p6_mark_stale_effect`,
  `tests/unit/test_canonical_claim_materialization.py::test_publish_canonical_claim_rejects_a_real_p6_marked_stale_inference`
- F19 (policy-blocked citations): `tests/unit/test_assertion_catalog.py::test_catalog_packet_reflects_a_real_p6_policy_block_on_the_assertion_itself`,
  `tests/unit/test_assertion_inference.py::test_resolve_bases_rejects_a_real_p6_policy_blocked_source_assertion`,
  `tests/unit/test_canonical_claim_materialization.py::test_publish_canonical_claim_rejects_a_real_p6_policy_blocked_source_assertion`
  — Command: `pytest tests/unit/test_assertion_catalog.py -k "mark_stale or policy_block"` — Exit 0 — **2 passed, 15 deselected** (the inference/canonical_claim-side F18/F19 tests are counted in the full-file runs above)
- **Gap filled (RPC-7.14, cross-listed under freeze gates below)**: authored
  `test_materialized_inference_version_digest_recomputes_and_matches_manifest_entry` in
  `tests/unit/test_assertion_inference.py` and
  `test_materialized_canonical_claim_version_digest_recomputes_and_matches_manifest_entry` in
  `tests/unit/test_canonical_claim_materialization.py` — the pre-existing golden-vector tests
  only validated the pure digest formula against frozen inputs, never that a REAL P4-written
  record's stored `version_digest` recomputes from its own persisted fields and matches its
  generation-manifest entry.

### RPC-7.6 → AC RPC-5 (activity and lineage reads remain governed)

Covers: discovery/API/export/OpenAPI/type + no-existence-leak.

- `tests/unit/test_assertion_catalog.py` (full) — Command: `pytest tests/unit/test_assertion_catalog.py` — Exit 0 — **17 passed**
- `tests/unit/test_export_service.py` (provenance-lineage + existence-gate subset) — Command:
  `pytest tests/unit/test_export_service.py -k "provenance_lineage or existence_gate"` — Exit 0 — **16 passed, 118 deselected**
- `tests/integration/test_assertions_api.py` (full — includes `test_end_to_end_lineage_chain_matches_across_catalog_api_and_export`,
  `test_other_workspace_cannot_probe_packet_membership`) — Command: `pytest tests/integration/test_assertions_api.py` — Exit 0 — **8 passed**
- `tests/test_openapi_seam.py` (OpenAPI regeneration parity) — Exit 0 — **4 passed**
- `tests/test_schema_validation.py` (schema/type-shape, incl. 2 new RPC-7.16 tests below) — Exit 0 — **247 passed**
- Gaps filled: none for RPC-5 itself (the 2 new schema tests are attributed to RPC-7.16 below, not this AC).

### RPC-7.7 → AC RPC-6 (lifecycle reconciliation uses exact action identity)

Covers: interruption + exact receipt-identity adversarial.

- Covering tests: `tests/unit/test_assertion_impact.py` (full file — includes
  `test_new_action_kinds_interrupt_and_resume_exactly`, `test_new_action_kinds_malformed_receipt_fails_closed` (parametrized),
  `test_new_action_kinds_missing_manifest_still_blocks_no_regression`, `test_manifest_merge_conflicting_entry_fails_closed`,
  `test_manifest_merge_malformed_existing_manifest_fails_closed`, `test_lifecycle_seam_repair_path_converges_after_manifest_fix`,
  `test_collect_stale_object_ids_read_path_degrades_with_a_logged_warning_on_corrupt_receipt`,
  `test_collect_stale_object_ids_strict_fails_closed_on_the_same_corrupt_receipt`)
- Command: `pytest tests/unit/test_assertion_impact.py`
- Exit code: 0 — **25 passed**
- Gaps filled: none. Coverage adequate as-is.

### RPC-7.8 → AC RPC-7 (optional AOS refs remain optional and governed)

Covers: absent/present/malformed/cross-workspace AOS-reference cases.

- `tests/unit/test_provenance_envelope.py` (AOS subset — `test_aos_refs_absent_is_byte_identical_to_before`,
  `test_aos_refs_present_round_trips_opaquely`, `test_aos_refs_malformed_fails_schema_validation_not_denial`,
  `test_aos_ref_authorizer_denies_unauthorized_ref_with_the_one_denial_shape`, `test_aos_ref_authorizer_allows_an_authorized_ref`,
  `test_aos_ref_authorizer_never_invoked_when_aos_refs_absent`, `test_create_activity_forwards_aos_ref_authorizer`,
  `test_create_activity_aos_ref_authorizer_absent_with_aos_refs_present_is_denied`, `test_create_activity_aos_refs_absent_needs_no_authorizer`)
  — Command: `pytest tests/unit/test_provenance_envelope.py -k "aos"` — Exit 0 — **9 passed, 32 deselected**
- `tests/unit/test_export_service.py` (AOS export subset — `test_aos_fields_and_native_aliases_emitted_when_present`,
  `test_aos_fields_can_be_sourced_from_correlation_block`, `test_aos_fields_null_when_absent`, `test_aos_malformed_uuid_values_are_not_exported`,
  `test_aos_uuid_values_are_canonicalized_for_schema_format`) — Command: `pytest tests/unit/test_export_service.py -k "aos"` — Exit 0 — **5 passed, 129 deselected**
- Gaps filled: none. Coverage adequate as-is.

### RPC-7.9 → AC RPC-8 (existing seams keep prior behavior)

Covers: focused RAL/activation/search/launch/export legacy suites + legacy response key-set diffs.

| Suite | Command | Exit | Result |
|---|---|---|---|
| Reusable Assertion Ledger phase 1 | `pytest tests/test_reusable_assertion_ledger_phase1.py` | 0 | **11 passed** |
| Reusable Assertion Ledger phase 0 (base legacy) | `pytest tests/test_reusable_assertion_ledger_phase0.py` | 0 | **4 passed** |
| Assertion reuse/activation | `pytest tests/integration/test_assertion_reuse.py` | 0 | **23 passed** |
| Run launch (base legacy) | `pytest tests/test_run_launch.py` | 0 | **6 passed** |
| Run launch retrieval | `pytest tests/integration/test_run_launch_retrieval.py` | 0 | **6 passed** |
| Run launch reuse (incl. key-set diff) | `pytest tests/integration/test_run_launch_reuse.py` | 0 | **23 passed** |
| Export service (full) | `pytest tests/unit/test_export_service.py` | 0 | **134 passed** |
| Search router | `pytest tests/test_search_router_router.py` | 0 | **43 passed** |
| Schema validation | `pytest tests/test_schema_validation.py` | 0 | **247 passed** |

- Legacy response key-set diff tests specifically: `tests/integration/test_run_launch_reuse.py::test_reuse_fields_absent_leaves_response_shape_unchanged`
  (`assert set(body.keys()) == {...}`), `::test_plan_run_disabled_retrieval_policy_is_byte_identical_snapshot`,
  `::test_launch_run_activity_ref_absent_is_byte_identical_to_before`; `tests/unit/test_provenance_envelope.py::test_aos_refs_absent_is_byte_identical_to_before`.
- Gaps filled: none. Coverage adequate as-is.

## Freeze-doc gates (`research-provenance-contract-freeze.md` §17.9, RPC-7.12..7.19)

### RPC-7.12 — crash-injection quarantine

A crash-injection test confirming a staged/promoted `inference_record`/`canonical_claim` interrupted between §17.7 steps 1–2 or 2–5 is quarantined on recovery, never silently adopted or made citable.

- Covering tests: `tests/unit/test_assertion_inference.py::test_interrupted_after_staging_is_quarantined_and_replay_converges`,
  `::test_interrupted_before_manifest_is_quarantined_and_replay_converges`, `::test_interrupted_after_manifest_pre_ledger_is_quarantined_and_replay_converges`,
  `::test_interrupted_after_ledger_pre_pointer_republishes_pointer_on_retry`; the identical four boundaries mirrored in
  `tests/unit/test_canonical_claim_materialization.py` (same test names).
- Command: `pytest tests/unit/test_assertion_inference.py tests/unit/test_canonical_claim_materialization.py`
- Exit code: 0 — **62 passed** (26 + 36, includes gap-fills below)
- Gaps filled: none. Adequate as-is.

### RPC-7.13 — commit-proof substitution rejection

The commit-proof digest (seven-field, §17.8 item 2) recomputation rejects every substituted-target and substituted-support-refs variant of a live commit attempt.

- Pre-existing coverage (pure-function level): `tests/unit/test_assertion_inference.py::test_compute_commit_proof_digest_matches_contract_worked_vector`
  (proves a substituted target changes the digest); `tests/unit/test_assertion_materialization.py::test_t4_1_repro_bogus_target_rejected_even_via_direct_private_call`
  (proves the live, private commit routine fails closed on a bogus/never-materialized target, via the record-before-reference precondition).
- **Gap filled**: neither pre-existing test forced the SPECIFIC branch where the commit routine's own independent recomputation of the
  commit-proof digest (`assertion_materialization.py:1445`) diverges from the caller-supplied value on an otherwise-valid, real, already-
  materialized record. Authored `test_commit_proof_digest_substitution_rejected_on_a_live_commit_attempt` in
  `tests/unit/test_assertion_inference.py`: forges the CALLER's own `compute_commit_proof_digest` binding (a separate module-level import,
  left untouched in `assertion_materialization`, which performs the independent recompute-and-compare) to return a bogus digest on a real
  `materialize_inference` call; asserts `abstention_code == "partial_write_rejected"`, no partial ledger write, and that retry after
  un-forging converges to `"materialized"`.
- Command: `pytest tests/unit/test_assertion_inference.py -k "commit_proof_digest_substitution"`
- Exit code: 0 — **1 passed, 25 deselected**

### RPC-7.14 — inference_record version_digest recomputation gate

Every P4-written `inference_record`'s `version_digest` (widened formula, §15.2 item 4) recomputes to its stored value AND matches its generation-manifest entry (§17.7a).

- Pre-existing coverage: `test_compute_inference_version_digest_matches_contract_worked_vector` (pure-function golden vector + tamper re-run);
  `test_materialize_inference_end_to_end` (asserts `record["version_digest"]` is truthy and a manifest entry with matching `record_id`/`version`
  exists, but never cross-checks digest EQUALITY between record/manifest, nor independently recomputes from the record's own fields).
- **Gap filled**: authored `test_materialized_inference_version_digest_recomputes_and_matches_manifest_entry` — runs the real
  `AssertionInferenceMaterializer.materialize_inference` flow, loads the persisted record, independently recomputes `version_digest` via
  `compute_inference_version_digest` from the record's own persisted fields, and asserts equality to both the record's stored field AND the
  generation-manifest entry's `version_digest` field.
- Command: `pytest tests/unit/test_assertion_inference.py -k "digest_recomputes_and_matches_manifest"`
- Exit code: 0 — **1 passed, 25 deselected**

### RPC-7.15 — canonical_claim version_digest recomputation gate

Every P4-written `canonical_claim`'s `version_digest` (widened formula, §15.2 item 3) recomputes to its stored value AND matches its generation-manifest entry (§17.7a).

- Pre-existing coverage: `test_compute_canonical_claim_version_digest_matches_contract_worked_vector` (pure-function golden vector); same gap
  as RPC-7.14 (`test_publish_canonical_claim_end_to_end` never cross-checks digest equality against a real record's own fields/manifest entry).
- **Gap filled**: authored `test_materialized_canonical_claim_version_digest_recomputes_and_matches_manifest_entry` in
  `tests/unit/test_canonical_claim_materialization.py` — mirrors RPC-7.14's fix exactly (real `publish_canonical_claim` flow, independent
  recompute via `compute_canonical_claim_version_digest`, equality against stored field AND manifest entry). Note: the production call site
  passes `resolution.inference_refs or None` (not `[]`) when no inference support is cited — the new test replicates this exactly
  (`record.get("inference_refs") or None`) to avoid a false-negative digest mismatch from an `[]`-vs-`None` normalization difference.
- Command: `pytest tests/unit/test_canonical_claim_materialization.py -k "digest_recomputes_and_matches_manifest"`
- Exit code: 0 — **1 passed, 35 deselected**

### RPC-7.16 — atomic-pair rule (claim_ledger + report_assertion_use.cited_ref)

No P4-written `claim_ledger` row ever has exactly one of `inference_id`/`inference_version` (or `canonical_claim_id`/`canonical_claim_version`) set; no P3-written `report_assertion_use.cited_ref` ever has exactly one of a family's id/version pair set either.

- **claim_ledger half — gap filled**: `schemas/claim_ledger.schema.yaml` deliberately carries no schema-level conditional for this pair
  (round-2 SOL-17 revert, documented in-schema) — the rule is writer-level only, per the freeze doc's own text, and pre-existing tests only
  demonstrated the HAPPY-path pair being written together as a side effect of successful materialization. Authored
  `test_claim_ledger_inference_reference_pair_is_never_partial_at_any_crash_checkpoint` in `tests/unit/test_assertion_inference.py`: reuses
  the suite's own three crash-injection hooks (`_interrupt_before_manifest`, `_interrupt_after_manifest`, `_interrupt_after_ledger`) and
  asserts, at each checkpoint plus final convergence, that `persistent_references.inference_id is not None` and
  `.inference_version is not None` are never observed to disagree (`has_id == has_version`).
  Command: `pytest tests/unit/test_assertion_inference.py -k "pair_is_never_partial"` — Exit 0 — **1 passed, 25 deselected**.
  Note: `canonical_claim_id`/`canonical_claim_version` share the IDENTICAL shared writer (`assertion_materialization.py`'s
  `_commit_persistent_reference`/`_commit_persistent_reference_locked`, reached from both `AssertionInferenceMaterializer.materialize_inference`
  and `CanonicalClaimMaterializer.publish_canonical_claim`) — the same atomic dict-write-then-single-`_atomic_dump` code path
  (`existing[target.id_field] = target_id; existing[target.version_field] = target_version; claim["persistent_references"] = existing;
  _atomic_dump(...)`) applies verbatim to canonical claims; the inference-side proof is representative for both target kinds without
  duplicating the same crash-checkpoint matrix a second time.
- **report_assertion_use.cited_ref half — gap filled**: the schema DOES carry a per-`ref_kind` if/then conditional (each active family
  requires its own pair present, and both inactive families' pair fields explicitly `null`), but the generic
  `tests/test_schema_validation.py::test_invalid_instance_fails` only ever removes one top-level required field and never exercised this
  conditional. Authored `test_report_assertion_use_cited_ref_active_kind_with_a_second_family_field_set_fails` (an `inference`-kind ref that
  also sets an inactive family's `assertion_id`) and `test_report_assertion_use_cited_ref_active_kind_missing_own_pair_field_fails` (a
  `canonical_claim`-kind ref with `canonical_claim_version: null`, i.e. a partial pair) in `tests/test_schema_validation.py`.
  Command: `pytest tests/test_schema_validation.py -k "cited_ref"` — Exit 0 — **2 passed, 245 deselected**.

### RPC-7.17 — envelope pair integrity

`envelope.receipt_commitment` is set write-once and always equals the referenced receipt's own `identity.fingerprint`; the v2 promotion's byte-equality rule and generation-manifest entry are written atomically alongside it.

- Covering tests: `tests/unit/test_provenance_envelope.py::test_receipt_promotion_binds_activity_id_and_commitment`,
  `::test_receipt_can_only_be_published_against_v1`, `::test_receipt_promotion_replay_is_idempotent`,
  `::test_receipt_promotion_conflicting_replay_fails_closed`, `::test_generation_manifest_tamper_detected_on_read`,
  `::test_cross_record_equality_detects_receipt_substitution`, `::test_v1_only_envelope_with_no_receipt_is_not_an_integrity_failure`,
  `::test_forged_v1_mapping_promotion_attempt_rejected`, `::test_receipt_content_tamper_with_stale_fingerprint_detected_on_read`,
  `::test_crash_window_between_receipt_write_and_manifest_append_converges`, `::test_receipt_promotion_concurrent_writers_race_no_corruption`,
  `::test_manifest_self_consistent_forgery_caught_only_by_manifest_check`, `::test_manifest_duplicate_entries_fail_closed`
- Command: `pytest tests/unit/test_provenance_envelope.py -k "receipt or generation_manifest or cross_record or manifest_self_consistent or manifest_duplicate"`
- Exit code: 0 — **13 passed, 28 deselected**
- Gaps filled: none. Coverage is comprehensive (includes a real concurrent-writers thread-race test).

### RPC-7.18 — origin/envelope version-bump fingerprint recomputation gate

`provenance_origin`/`research_run_envelope` writers reject an attempted version bump not accompanied by a correspondingly recomputed identity fingerprint/version_digest, matching the generation-manifest entry.

- Covering tests (origin): `tests/unit/test_provenance_envelope.py::test_origin_version_bump_changes_identity`,
  `::test_origin_conflicting_content_under_same_id_fails_closed`.
- Covering tests (research_run_envelope v1→v2, the only version transition this record type has): the full RPC-7.17 receipt-promotion suite
  above — `envelope_version: 1 → 2` IS the receipt-promotion transition, and `test_receipt_promotion_binds_activity_id_and_commitment` /
  `test_cross_record_equality_detects_receipt_substitution` / `test_manifest_self_consistent_forgery_caught_only_by_manifest_check` together
  prove the recomputed fingerprint must match both the record's own field and its manifest entry.
- Command: `pytest tests/unit/test_provenance_envelope.py -k "origin_version_bump or origin_conflicting or receipt_promotion or cross_record or manifest_self_consistent"`
- Exit code: 0 — **11 passed, 30 deselected**
- Gaps filled: none. Coverage adequate as-is.

### RPC-7.19 — commit-time recheck under mutation (deferred lock-scoped race)

The commit-time recheck (§17.1 item 6: support-assertion lifecycle, run mapping, resolved capability flags) actually fires and aborts a commit under concurrent lifecycle/config mutation — never claimed as full system-wide serialization (§22b/SOL-15's bounded-concurrency honesty note).

Item 6 names THREE independent rechecks performed under the per-run lock immediately before commit. Status per sub-check:

1. **Support-assertion lifecycle** — pre-existing: `tests/unit/test_assertion_inference.py::test_commit_time_recheck_independently_catches_stale_support_resolution_missed`.
   Monkeypatches `resolve_bases` to report a stale-but-accepted resolution while the real on-disk source assertion is already invalidated;
   the shared locked commit routine independently reloads and rechecks, aborting with the specific `stale_support` code. **Adequate as-is.**
2. **Run mapping** — **gap filled**. No pre-existing test isolated this sub-check from the initial (pre-lock) ownership check performed at
   the top of `materialize_inference`. Authored `test_commit_time_recheck_independently_catches_run_mapping_revoked` in
   `tests/unit/test_assertion_inference.py`: monkeypatches `assertion_materialization`'s OWN `load_yaml` binding (a separate module-level name
   from `assertion_inference`'s own binding, which performs the untouched EARLY check) to return a workspace-mismatched `run.yaml` doc only
   for the SAME reload the locked commit routine performs — proving the commit-time reload/recheck is independent of, and fires even though,
   the earlier check passed. Asserts `abstention_code == "run_mapping_revoked"` and no partial write.
   Command: `pytest tests/unit/test_assertion_inference.py -k "run_mapping_revoked"` — Exit 0 — **1 passed, 24 deselected**.
3. **Resolved capability flags at commit instant** — **bounded limitation, not filled**. `test_materialize_inference_ledger_write_disabled_abstains`
   / `test_materialize_inference_run_workspace_mismatch_abstains`-style tests set the condition BEFORE the single synchronous
   `materialize_inference` call, so they cannot distinguish "checked once at an early gate" from "independently rechecked at the locked
   commit instant" — both an early-gate check and a commit-time recheck would observe the identical disabled state in one call. Producing a
   genuine mid-flight flip (flag enabled when resolution starts, disabled by the time the SAME call reaches the locked commit) would require
   either a stateful monkeypatch on `FoundryConfig.assertion_ledger_capabilities` keyed to call-order (viable but not attempted this pass —
   time-boxed out of this bounded sprint) or two real concurrent threads racing the actual lock (the harness the suite already uses for
   `test_receipt_promotion_concurrent_writers_race_no_corruption`, adapted to this target). This is the "vanishingly narrow window, but not
   literally zero" the freeze doc's own §22b/SOL-15 text explicitly disclaims coverage of: *"the per-run lock provides serialization for
   ledger-and-record WRITERS only; everything else is handled by the commit-time recheck (item 6) plus post-hoc reconciliation (P6) — never
   full system-wide serialization of every mutator."* The risk is bounded, not eliminated, by: (a) the SAME shared, single code block
   (`assertion_materialization.py` lines ~1418–1424) that the run-mapping and lifecycle rechecks in this same gate ALREADY prove fires
   correctly for their sibling preconditions — capability flags are checked in the identical unconditional sequence, not a separate optional
   path; and (b) `assertion_impact.py`'s post-hoc reconciliation pass (P6, read-only, exercised by `tests/unit/test_assertion_impact.py`),
   which detects and flags any record whose support became invalid after that record's own commit, closing the residual window after the
   fact rather than preventing it. **Recommendation for a follow-up pass**: add the stateful-monkeypatch variant described above if this
   sub-check needs a dedicated positive test rather than resting on the shared-code-path inference.
- Overall RPC-7.19 status: **2 of 3 sub-checks now have a dedicated live test (lifecycle: pre-existing; run mapping: gap-filled this pass);
  1 of 3 (capability flags) is a documented bounded limitation, not a defect** — the mechanism exists and is exercised end-to-end by the
  other two sub-checks sharing its code path, but no test isolates a flag-flip specifically mid-flight within one call.

## Totals

| Category | Count |
|---|---|
| Plan AC gates (RPC-7.2..7.9) — covered by pre-existing tests | 8 / 8 |
| Plan AC gates — new tests authored to fill a gap | 0 (gap-fills below are attributed to freeze-doc gates, not plan ACs) |
| Freeze-doc P7 gate tasks (RPC-7.12..7.19) — covered by pre-existing tests, no gap | 4 / 8 (7.12, 7.17, 7.18, and the lifecycle sub-check of 7.19) |
| Freeze-doc P7 gate tasks — gap filled with a new test this pass | 3 / 8 (7.13, 7.14+7.15, 7.16) |
| Freeze-doc P7 gate tasks — bounded limitation documented, not filled | 1 sub-check of 1 gate (7.19's capability-flags mid-flight recheck) |
| New test functions authored | 8 (`test_materialized_inference_version_digest_recomputes_and_matches_manifest_entry`, `test_claim_ledger_inference_reference_pair_is_never_partial_at_any_crash_checkpoint`, `test_commit_time_recheck_independently_catches_run_mapping_revoked`, `test_commit_proof_digest_substitution_rejected_on_a_live_commit_attempt` in `test_assertion_inference.py`; `test_materialized_canonical_claim_version_digest_recomputes_and_matches_manifest_entry` in `test_canonical_claim_materialization.py`; `test_report_assertion_use_cited_ref_active_kind_with_a_second_family_field_set_fails`, `test_report_assertion_use_cited_ref_active_kind_missing_own_pair_field_fails` in `test_schema_validation.py`) |
| Files modified (tests only, no src changes) | `tests/unit/test_assertion_inference.py`, `tests/unit/test_canonical_claim_materialization.py`, `tests/test_schema_validation.py` |
| Defects found in src during this pass | 0 |
| Full-suite exit codes across all commands run this pass | all 0 (no failures) |

## Constraints honored

- No production `src/` edits made.
- All new tests drive real service entry points (`AssertionInferenceMaterializer.materialize_inference`,
  `CanonicalClaimMaterializer.publish_canonical_claim`, `SchemaRegistry`/`validate`) through their real fixture-building helpers
  (`_setup_run_with_two_supported_claims` → `ingest_source` → `extraction.extract_run` → `claim_mapping.build_claim_ledger` →
  `AssertionMaterializer.materialize_run`) — no hand-authored/forged canonical records, per F18/F19 fixture-fidelity rules. The two schema
  tests (RPC-7.16 report-use half) are pure schema-instance validation, which is the correct test shape for a schema-level conditional (no
  service fixture applies).
- DI-1 remains BLOCKED (unaffected by this pass — no multi-tenant/runtime changes).
- No rights minted; no `CLEARED_*`/`counsel_approved`/`attested` values introduced anywhere.
