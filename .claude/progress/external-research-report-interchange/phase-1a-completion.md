## Phase 1a Completion Note — Packet Schema Authoring: ERI-1.1 (+ ERI-1.3 vocabulary encoding)

**Mode:** B — Contract Drafting. Authored `schemas/*.schema.yaml` + `tests/fixtures/` +
`tests/unit/test_external_research_schemas.py` only; one small wiring edit to
`tests/test_schema_validation.py`'s pre-existing registry-coverage parametrization (see "Files
Changed"). No `src/research_foundry/**/*.py` production code was touched — schema authoring is this
task's entire authorized scope, matching the plan's phase boundary (P1 is schema/identity/vocabulary
freeze; P2+ implement against it). No git write command was run.

A parallel agent (Mode B, same phase) froze the semantics this task encodes in
`docs/dev/architecture/external-research-handoff-contract.md` (ERI-1.2/1.3/1.4/1.5) and
`.claude/findings/external-research-report-interchange-findings.md` — see
`phase-1b-completion.md` in this directory. This note's schemas were authored directly against that
document's exact digest formulas, tier table, reason-code vocabulary, and acquisition-policy gate
ordering, not re-derived independently.

### Files Created

**Schemas** (`schemas/`):

- `external_research_handoff.schema.yaml` — the packet manifest (`handoff.yaml` content). Declares
  `transport: {const: directory}` (ERI-OQ-1), a `members` array requiring at least one
  `handoff_manifest`/`report`/`sources`/`assertion_candidates` role each (via `contains`/`minContains`)
  and bounding `attachment`-role members to ≤32 (via `contains`/`minContains: 0`/`maxContains: 32`),
  member count ≤64, single-member bytes ≤64 MiB, and `total_declared_bytes` ≤256 MiB (ERI-OQ-4).
  `content_roles.report` is pinned `const: platform_synthesis`.
- `external_research_sources.schema.yaml` — the `sources.yaml` record set (≤2000 records). Each record:
  `source_id`, `title`, `locator {doi, url}`, `publication_year`, `access_status` enum
  (`open-access`/`public-domain`/`paywalled`/`unknown`), `declared_metadata`, namespaced `extensions`.
- `external_assertion_candidates.schema.yaml` — the `assertion_candidates.yaml` record set (≤5000
  records). Each record: `candidate_id`, `statement`, `value`/`unit`/`direction`, `scope`,
  `source_refs` (packet-local), `relation` (non-authoritative hint), `classification` enum
  (`assertion`/`inference`/`annotation`), `quote`/`selector`, `producer_confidence`, `extensions`.
- `external_research_import_receipt.schema.yaml` — the RF-computed immutable terminal receipt.
  `status` is the closed 3-member enum (`completed`/`completed_with_quarantine`/`blocked`) with
  `pending` categorically excluded; carries `receipt_digest`/`packet_digest`/`policy_digest`/
  `schema_major_versions` (all four `receipt_digest` inputs, contract §1.3) and a per-action
  `completeness_tier`/`reason_code` vocabulary matching PRD §6.3/§6.5 exactly.
- `external_research_import_checkpoint.schema.yaml` — the separate, mutable, atomically-replaceable
  checkpoint. `status` is `pending`/`converged` only (never a receipt terminal state). Carries cursor,
  `completed_action_digests`, `pending_action_digest` — safe IDs only, no synthesis/quote/source text
  (PRD §6.7).
- `external_research_acquisition_policy.schema.yaml` — the SSRF-safe acquisition policy config
  (contract §4.2). Every hard invariant is schema-pinned with `const` (not merely described) so it
  cannot be configured away: `reject_embedded_credentials: true`, the 10-member
  `forbidden_address_categories` closed set (`const`, includes `cloud_metadata` and
  `encoded_or_obfuscated_host`), `dns_policy.{validate_every_answer, bind_to_validated_address,
  verify_connected_peer}: true`, `redirects.revalidate_every_hop: true` with `redirects.max_hops`
  bounded `maximum: 3`, and `transport_fallback_allowed: false`.

**Fixtures** (`tests/fixtures/external_research_handoff/<schema>/`, one directory per schema; every
`invalid_*.yaml` is named for the exact rule it violates):

- `handoff/`: `valid.yaml`; `invalid_unsupported_schema_version.yaml`,
  `invalid_transport_not_directory.yaml`, `invalid_unsafe_member_path.yaml`,
  `invalid_missing_required_member_role.yaml`, `invalid_too_many_attachments.yaml`,
  `invalid_producer_sets_extra_field.yaml`.
- `sources/`: `valid.yaml`; `invalid_missing_source_id.yaml`, `invalid_bad_access_status.yaml`,
  `invalid_producer_sets_verified_state.yaml`.
- `assertion_candidates/`: `valid.yaml`; `invalid_missing_classification.yaml`,
  `invalid_bad_classification.yaml`, `invalid_producer_sets_verified_state.yaml`.
- `import_receipt/`: `valid.yaml`, `valid_verified_promotion_with_target_run.yaml`;
  `invalid_pending_is_not_a_receipt_state.yaml`, `invalid_blocked_with_nonempty_actions.yaml`,
  `invalid_verified_tier_without_target_run.yaml`, `invalid_quarantined_without_reason_code.yaml`,
  `invalid_completed_status_with_quarantined_count.yaml`.
- `import_checkpoint/`: `valid.yaml`, `valid_converged.yaml`;
  `invalid_pending_with_null_next_action.yaml`, `invalid_converged_with_next_action_set.yaml`,
  `invalid_completed_is_not_a_checkpoint_state.yaml`.
- `acquisition_policy/`: `valid.yaml`; `invalid_transport_fallback_allowed_true.yaml`,
  `invalid_missing_forbidden_category.yaml`, `invalid_redirect_hops_exceed_ceiling.yaml`,
  `invalid_file_scheme_allowed.yaml`.

(The `sources ≤ 2000` / `candidates ≤ 5000` / `handoff members ≤ 64` boundary cases are not
hand-authored as giant static YAML files — they are covered as programmatic fixtures inside the test
file instead; see below.)

**Test**: `tests/unit/test_external_research_schemas.py` — loads every schema through the same
`research_foundry.schemas.SchemaRegistry`/`validate()` every other RF schema uses, glob-discovers and
asserts every `valid*.yaml` passes and every `invalid_*.yaml` fails per schema, programmatically
exercises the three item-count ceilings above, and adds structural guards directly asserting a handful
of the HARD CONSTRAINTS on the schema JSON itself (not only via instance fixtures) — e.g. the receipt's
`status` enum excludes `pending`, the checkpoint's `status` enum excludes every receipt terminal state,
the receipt's action-item shape has no free-text detail field, the 19-code/4-family reason-code
vocabulary matches PRD §6.5 verbatim, `transport_fallback_allowed`/`forbidden_address_categories`/
`redirects.max_hops` are schema-pinned as designed, and neither packet-authored record schema declares
a `verified`/`completeness_tier` field. **30 tests, all green.**

### Files Changed (pre-existing)

- `tests/test_schema_validation.py` — added the 6 new schema names to `EXPECTED_SCHEMA_NAMES` plus a
  minimal-required-fields instance in `_valid()` and a `required_first` entry in `_invalid()` for each
  (same wiring precedent as the rights-entity-model P0-5 registry pass). Without this, the pre-existing
  `test_registry_lists_all_schemas` regression guard would fail simply because `schemas/` now has 45
  files instead of 39 — confirmed this is a real, not pre-existing, effect: `git stash` reproduces the
  failure on the unmodified tree once these 6 files exist, and the stash-baseline comparison below shows
  it is the *only* test this task's changes affect either way.

### How ERI-1.1 was satisfied

- All 6 required schema files exist under `schemas/`, each a valid Draft 2020-12 document
  (`jsonschema.Draft202012Validator.check_schema()` passes for all 6).
- Each of the 6 has ≥1 valid golden fixture and ≥2 (3–6) named invalid fixtures under
  `tests/fixtures/external_research_handoff/`, all covered by `tests/unit/test_external_research_schemas.py`.
- Required vs. optional members are explicit on the handoff schema: `handoff_manifest`/`report`/
  `sources`/`assertion_candidates` roles are each required (`minContains: 1`); `activity` is
  unconstrained (implicitly optional — no `minContains`); `attachment` is optional and bounded
  (`minContains: 0, maxContains: 32`).

### How ERI-1.3 was satisfied

- The 4-tier vocabulary (`locator_only`/`source_resolved`/`passage_resolved`/`verified`) is encoded
  verbatim on the receipt's per-action `completeness_tier`, with a structural split by `kind`
  (`source` actions can only ever reach `source_resolved`; only `candidate` actions can reach
  `passage_resolved`/`verified`) — contract §2.1's scoping note, enforced, not just described.
- The two-layer terminal-state model is encoded structurally: `pending` exists only on the checkpoint
  schema (never the receipt), and the receipt's `status`/`block_reason`/`actions`/`counts` fields are
  cross-linked with `allOf`/`if`/`then` so `blocked` ⇒ empty `actions` + non-null `block_reason`,
  `completed` ⇒ zero quarantined, `completed_with_quarantine` ⇒ at least one quarantined, and a
  `null` `target_run_id` ⇒ no action anywhere may report `verified` (contract §1.4) — all four
  directly test-verified via the fixtures above, not merely asserted in prose.
- The 19-code, 4-family closed reason-code vocabulary (PRD §6.5) is a literal enum on both
  `block_reason` (packet family only) and each action's `reason_code` (source/citation/candidate
  families, further split by `kind`), with `null` permitted only when `outcome: completed` and required
  non-null when `outcome: quarantined`. No free-text detail field exists anywhere on the receipt, by
  design — quarantine safety (PRD §6.5 / contract §2.3) is structural, not a code-review convention.
- `verified` authority: the receipt schema is the only place `verified` can appear, and only when
  `target_run_id` is non-null — the packet-authored `sources`/`assertion_candidates` schemas cannot
  declare a `verified` or `completeness_tier` field at all (`additionalProperties: false`), which is
  the schema-level half of HARD CONSTRAINT #2 ("producer-declared completeness must not set computed or
  verified state").

### Verification performed

```
PYTHONPATH=$PWD/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python \
  -m pytest tests/unit/test_external_research_schemas.py -q
# 30 passed

PYTHONPATH=$PWD/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python \
  -m pytest tests/test_schema_validation.py tests/unit/test_external_research_schemas.py -q
# all passed (registry-coverage wiring included)

PYTHONPATH=$PWD/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python \
  -m pytest tests/ -q --ignore=tests/test_verification_pediatric_cds.py \
  --ignore=tests/test_verification_seam001_gate_composition.py
# 15 pre-existing failures + 2 pre-existing collection errors, all confirmed present on `git stash`
# (unmodified tree) too — this task introduces zero net-new failures and fixes the one baseline
# mismatch (test_registry_lists_all_schemas) its own new files would otherwise have caused.
```

Marked `ERI-1.1` `completed` in `phase-1-progress.md` via
`.claude/skills/artifact-tracking/scripts/update-status.py` (CLI-first per the progress-file rule;
frontmatter was not hand-edited).

### Unresolved / carried forward

- **`policy_digest`'s exact byte-level serialization** (which fields, in what order) is bound by
  contract §1.3 to feed `sha256-canonical-json-v1`, and the `external_research_acquisition_policy`
  config object this schema defines is the thing that gets digested — but the digest computation
  itself (canonical serialization → SHA-256) is Phase 2 service code, not this schema. No open question
  here; just noting the boundary.
- **The `source_cards.ingest_source()` run-scoping seam and the RFUP SSRF-policy gap** (both named in
  `phase-1b-completion.md`/the findings doc) are unaffected by this task — they are Phase 2/Phase 4
  implementation concerns, not schema-shape concerns.
- **ERI-1.1's own task-completion-validator/Karen review has not run.** Per the plan's Phase 1 quality
  gate ("A material contract fix reruns task-completion-validator and Karen against the new tree"),
  this exact tree (this note + `phase-1b-completion.md`'s tree) is what those reviewers should evaluate
  next, before P2/P3 begin consuming these schemas.
- **`ERI-1.2`/`ERI-1.4`/`ERI-1.5` progress rows remain `pending`** in `phase-1-progress.md` — this task
  only owned `ERI-1.1`; the parallel Mode B pass that froze those (`phase-1b-completion.md`) did not
  update the shared progress file's frontmatter either (out of its stated scope), so a follow-up pass
  should reconcile `phase-1-progress.md` against both completion notes via the CLI script, not by hand.
- Two pre-existing test-collection errors (`tests/test_verification_pediatric_cds.py`,
  `tests/test_verification_seam001_gate_composition.py`, both `ModuleNotFoundError` on sibling test
  modules) and 15 pre-existing test failures were observed during full-suite validation; all confirmed
  present on the unmodified baseline via `git stash` and are unrelated to this task — not chased here.
