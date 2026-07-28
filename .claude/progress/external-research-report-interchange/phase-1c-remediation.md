---
title: "ERI Phase 1c — Contract remediation (gpt-5.6-sol P1 audit response)"
schema_version: 2
doc_type: progress
feature_slug: external-research-report-interchange
phase: 1c
created: 2026-07-26
updated: 2026-07-26
status: completed
owner: nick
---

# Phase 1c — Contract Remediation

Responds to `.claude/findings/eri-p1-contract-audit-gpt56.md` (gpt-5.6-sol adversarial audit,
verdict CHANGES REQUIRED, 20 findings). Owned files touched (Mode B — Contract Drafting, then
scope-expanded mid-task by the coordinator to include the two invalidated fixture sets + their
test file once the parallel schema-fixture owner finished):

- `docs/dev/architecture/external-research-handoff-contract.md` (full remediation rewrite)
- `schemas/external_research_acquisition_policy.schema.yaml` (remediation rewrite)
- `schemas/external_research_import_receipt.schema.yaml` (remediation rewrite)
- `.claude/findings/external-research-report-interchange-findings.md` (no append needed — no new
  plan/reality mismatch was discovered in this pass beyond what the audit itself already named)
- `tests/fixtures/external_research_handoff/acquisition_policy/*` (5 files updated)
- `tests/fixtures/external_research_handoff/import_receipt/*` (7 files updated, 1 renamed)
- `tests/unit/test_external_research_schemas.py` (2 tests updated to match new intent, 4 new
  tests added)
- `tests/test_schema_validation.py` (2 minimal-instance dicts updated — general schema-registry
  coverage test, not owned by the interchange-parallel-agent; broke mechanically from the schema
  edits and was fixed the same way as the dedicated fixtures)

**Not touched, per explicit instruction:** `src/research_foundry/services/external_research_interchange.py`,
`tests/unit/test_external_research_interchange.py` (parallel agent actively editing).

**Findings #7 and #8** are implementation-level (owned by a parallel agent) — explicitly out of
scope for this remediation, per the original task instructions. Not addressed here.

**Validation:** `PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/unit/test_external_research_schemas.py -q`
→ 34 passed. Also ran the broader shared registry test, `tests/test_schema_validation.py` → 229
passed (both required by the schema edits, since it independently hardcodes minimal instances for
every registered schema including these two).

---

## Finding → change map

### #1 (CRITICAL) — validated connection ≠ connection RFUP uses

**Change.** New contract §4.2.0 "Architecture: one actor owns the whole HTTP lifecycle" — the
policy layer IS the HTTP client (resolution, connection binding, TLS, redirect-following, response
read as one integrated operation over one connection); RFUP's extraction step (§4.2.9) receives
already-acquired bytes plus minimal response metadata, never the original URL. §2.4 step 5
reframed from "RFUP-owned acquisition/extraction" to "RFUP-owned extraction from policy-acquired
bytes." Encoded as a hard-pinned, non-configurable schema object:
`external_research_acquisition_policy.schema.yaml`'s `transport_architecture.single_actor_owns_
full_lifecycle: const true` and `.hands_off_acquired_bytes_only: const true`.

### #2 (HIGH) — proxy/delegated-fetch defeats peer verification

**Change.** New contract §4.2.1 "Direct transport only" — environment/PAC proxies explicitly
disabled; provider-delegated URL fetching prohibited absent a future proven equivalent pinned-
address guarantee. Schema: `transport_architecture.environment_and_pac_proxies_disabled: const
true`, `.provider_delegated_fetch_allowed: const false`. Cross-referenced in §3.2's dependency map:
freezes that ERI's v1 acquisition never calls `run_search`/`_first_extraction_provider`/any
provider `.extract()` (verified on-tree: those call bare `httpx`/`urllib` with zero address
validation and would be exactly the delegated-fetch pattern this finding prohibits).

### #3 (HIGH) — URL canonicalization not frozen

**Change.** New contract §4.2.2 "URL canonicalization — frozen, single parse": one strict parse,
IDNA/punycode normalization, single trailing-dot stripping, userinfo rejection (any userinfo, not
only credential-shaped), percent-encoded-host rejection, IPv6 zone-ID rejection, ambiguous-numeric-
host rejection, canonical IP-literal object shared with transport. Schema: new
`canonicalization` object with 8 hard-pinned `const: true` invariants, `required` at top level.

### #4 (HIGH) — IPv6 transition/translation addresses uncovered

**Change.** New contract §4.2.4 IPv6 sub-section: NAT64/DNS64 well-known prefix, 6to4, Teredo,
IPv4-mapped/compatible all explicitly named; embedded-IPv4 decode-and-validate required; additive-
only operator-configured local NAT64 prefixes. Schema: new `ipv6_transition_policy` object
(`well_known_prefixes` const list of 6 CIDRs, `decode_and_validate_embedded_ipv4: const true`,
`operator_configured_nat64_prefixes` array, additive-only by design). `forbidden_address_categories`
gained an 11th closed-set member, `ipv6_transition_or_translation`.

### #5 (MEDIUM) — cloud-metadata deny-set not testable/versioned

**Change.** New contract §4.2.4 metadata sub-section: explicit `metadata_deny_set` (AWS
`169.254.169.254`/`fd00:ec2::254`, GCP `metadata.google.internal`, Azure `metadata.azure.com`/
`169.254.169.253`, Alibaba `100.100.100.200`), plus `metadata_deny_set_version` and
`special_purpose_address_registry_version`, both bound into `policy_digest` (§1.3) so a future list
change is a visible, versioned policy change. Schema: `metadata_deny_set` const array,
`metadata_deny_set_version`/`special_purpose_address_registry_version` const strings, all required.
Recorded as an Open Item (§ bottom of contract) that registry currency review is a live operational
process, not solved by a one-time snapshot.

### #6 (HIGH) — no action/effect identity

**Change.** New contract §1.3a "Action, action-manifest, and effect identity — frozen": canonical
iteration order, `record_digest`, `action_id` (content+occurrence-index keyed, immune to positional
reordering for non-duplicate records), canonical action manifest with an embedded
`algorithm_version` (closes "software change alters manifest, same identity" gap),
`action_manifest_digest`, and `effect_digest` (hashes `action_id` first, binding an effect to
exactly one action). `action_manifest_digest` bound into `receipt_digest` as a new Branch-A input.
Schema: `action_manifest_digest`/`action_manifest_algorithm_version` fields added (nullable, tied
to `status` via `allOf`); `actions[].action_id` pattern tightened to `era_[a-f0-9]{64}`;
`actions[].effect_digest` description updated with the formula.

### #9 (HIGH) — replay bypasses current authorization/governance

**Change.** Two-part fix. (a) New contract §1.6 "Receipt-read authorization — frozen": every
receipt read (lookup, replay-check, explicit show) re-runs Step 0's coarse authorization against
the CURRENT caller/CURRENT governance policy before existence lookup, never only before content
return; failure gets the same safe generic denial as a never-submitted identity. (b) New
`governance_policy_digest` bound into `receipt_digest` (§1.3) — a governance/sensitivity policy
change computes a distinct identity going forward, so stale policy is never silently reused for a
new decision. New §2.4 Step 0 (coarse caller/workspace authorization, runs before structural
validation) is where `governance_policy_digest` is captured, on every attempt including blocked
ones. Schema: `governance_policy_digest` required, non-nullable, hex64.

### #10 (MEDIUM) — blocked packets have no defined receipt_digest input

**Change.** `receipt_digest` redefined as one normative definition with two status-conditioned
branches (contract §1.3): Branch A (non-blocked, 7 inputs incl. `packet_digest`/
`action_manifest_digest`) vs Branch B (`blocked`, 6 inputs over a distinct rejected-attempt object:
blocked flag, workspace_id, target_run_id, policy_digest, schema_major_versions,
governance_policy_digest, block_reason, `attempt_structural_summary`). `attempt_structural_summary`
is new: safe count-only fields (`observed_member_count`, `raw_bytes_total`) computed via the same
pinned directory walk regardless of which structural check failed. Schema: `packet_digest`/
`action_manifest_digest`/`action_manifest_algorithm_version` made nullable, `allOf` conditionals
force them null exactly when `status: blocked` and non-null otherwise; new required
`attempt_structural_summary` object with the same null/non-null split.

### #11 (HIGH) — `report.md` allowed into unspecified "context surfaces"

**Change.** Contract §4.1 inert-data rule rewritten: the ban now explicitly covers every model
message role (not only system/developer), retrieval/RAG context regardless of "read-only" labeling,
tool/resource descriptions, and any tool-capable execution context. `report.md`'s special-case
paragraph updated to state it is banned from all of these, not only source-card/claim/assertion
writers. Only capability-free human display and capability-free automated analysis remain
permitted destinations.

### #12 (HIGH) — YAML/JSON parsing outside the inert-data boundary

**Change.** New contract §4.1b "Safe parsing — before schema validation runs." Names the concrete,
verified-on-tree gap in `research_foundry.yamlio` (`yaml.safe_load` permits merge keys and
unbounded alias/anchor expansion and silently overwrites duplicate keys; `json.loads` accepts
non-finite literals and silently overwrites duplicate members) and freezes a named hardened profile,
`packet-safe-parse-v1`, for Phase 2 to implement: primitives-only, merge keys disabled, duplicate
keys rejected, alias/depth/scalar ceilings, non-finite JSON rejected, duplicate JSON members
rejected, schema validation runs against the exact parsed object. Recorded as an Open Item (net-new,
not a reuse of `yamlio`).

### #13 (HIGH) — local-ingest carve-out contradicts identity/inert-routing

**Change.** Contract §4.5 fully redesigned: packet-internal local assets resolve ONLY via an opaque
`attachment_id` key lookup into the packet's own pre-validated, already-hashed member table — never
by re-parsing a fresh path string. Out-of-packet assets require a distinct operator grant (path +
expected digest, issued outside the packet, digest-verified at open time). Classification is
structural (which pipeline receives the value), never a packet-supplied `locator_type` hint.
Schema: `local_asset_carve_out` redesigned from a single `classification_source` const to 4
required invariants (`packet_internal_attachment_resolution`, `out_of_packet_requires_operator_
grant`, `operator_grant_binds_path_and_digest`, `producer_supplied_locator_type_hint_ignored`), all
`const: true`.

### #14 (MEDIUM) — logs/receipts/exports not covered by inert/redaction rule

**Change.** New contract §4.6 "Channel-by-channel taint/redaction matrix": a table covering CLI
output, structured logs, receipt/checkpoint, metrics, traces, provenance exports, and the (new)
access-controlled audit store, stating what packet-derived text/reason-code-detail/IDs each channel
may carry. Cross-cutting rule: control characters/ANSI sequences stripped/escaped before ANY
channel, IDs always RF-generated. Recorded as an Open Item that the concrete audit-store artifact
`audit_ref` resolves against is not yet defined (naming/building it is later-phase scope).

### #15 (HIGH) — reason-code vocabulary + counts are existence oracles

**Change.** Contract §4.3 rewritten and §2.3 updated: the ordinary caller-visible surface carries
zero reason-code detail and zero reason-differentiated counts. `packet_reason` (`block_reason`,
5-code family) stays visible — it describes the caller's own submitted packet back to themselves,
not a cross-workspace fact. The 14-code source/citation/candidate family is removed from the
receipt entirely. Schema: `actions[].reason_code` REMOVED; `actions[].audit_ref` (opaque hex64,
required non-null iff quarantined) added in its place; `counts.by_reason_code` REMOVED (kept
`by_completeness_tier`/`actions_total`/`completed`/`quarantined`, each justified as either positive-
progress info or trivially re-derivable from the still-visible `actions` array, so removing them
would cost functionality with no security benefit). Test-side: `test_receipt_has_no_free_text_
detail_field` and `test_reason_code_vocabulary_is_the_frozen_19_code_closed_set` rewritten to assert
the new shape (audit_ref present, reason_code absent, only `block_reason`'s 5-code family directly
enumerable on this schema) rather than reverting to the old shape. All 7 `import_receipt` fixtures
and the `test_schema_validation.py` minimal instance updated to match.

### #16 (HIGH) — timing noninterference mandatory AND accepted-leaking

**Change.** New contract §4.3.1 "Timing scope for v1" resolves the literal contradiction by scoping,
not by asserting an unenforceable universal guarantee: (a) threat-model framing — every path here
is reached only after Step 0/Step 2 authorization, narrowing who can observe timing at all; (b) one
v1-mandatory guarantee — fresh acquisition and stored-identity reuse (replay/edition-reuse) MUST be
routed through the same configurable minimum-latency floor, protecting the §1.5/§1.6 replay/reuse
identity guarantees specifically; (c) explicitly out-of-scope-for-v1, with rationale — finer-grained
timing variance among genuinely fresh denials (scheme-reject vs. DNS-fail vs. redirect-limit) is an
accepted, explicitly-scoped residual risk given the narrowed threat model, not an oversight, flagged
for ERI-6.2 to measure. Recorded as an Open Item (the timing floor itself is net-new).

### #17 (MEDIUM) — universal inert-data guarantee not implementable as written

**Change.** New contract §4.1a "Permitted narrow sinks — an explicit allowlist": exactly two fields
get a named, narrow, non-dynamic sink — `locator` (canonicalization/policy pipeline, or
`attachment_id` lookup per §4.5) and the schema `type`/`schema_version` discriminator (fixed
exact-match lookup against the registry's closed enum). Both share the "read, compare/parse by
fixed code, discard" shape; any other sink remains categorically forbidden per §4.1, and a future
third sink requires a contract amendment.

### #18 (MEDIUM) — frozen/approved status contradicts governance state

**Change.** Contract frontmatter `status` downgraded from `frozen` to `proposed`; `findings_doc_ref`
added pointing at the sibling findings doc. New "Status" preamble at the top of the document states
both grounds for the downgrade (this audit's 20 findings, and the pre-existing plan-frontmatter
mismatch — plan `status: draft`, all 4 `ERI-OQ-*` entries `open` in the plan's own table,
`findings_doc_ref: null` at freeze time) and states exactly what must happen before re-freezing.
**Not fixed here, by design:** the plan's own frontmatter (`findings_doc_ref`, `ERI-OQ-*` table) —
out of this task's owned-file scope (`docs/project_plans/implementation_plans/...` was never in the
granted file list), explicitly flagged as belonging to whichever agent owns plan-frontmatter
integration, same as the original findings doc's "Notes for Finalization" already said.

### #19 (MEDIUM) — provider acquisition both required and prohibited

**Change.** Contract §3.2 and new §4.2.9 freeze the exact v1 entry points: `extract_pdf(bytes)`
(`extractors/pdf_extractor.py:57`, verified zero-I/O on this tree) is the one frozen PDF entry
point; for non-PDF content, no existing byte-accepting extractor exists in RFUP today — Phase 4
must build a net-new one, explicitly NOT the provider chain (`_first_extraction_provider`/`.extract
([url])`), which performs its own independent network fetch. `run_search`/
`_first_extraction_provider`/any provider method are named as permanently out of ERI's acquisition
scope in v1. This directly satisfies AC ERI-6 (no live provider dependency) since no provider is
ever called by ERI's own acquisition path. Recorded as an Open Item (the non-PDF byte extractor is
net-new work).

### #20 (LOW) — receipt-identity input-count inconsistency

**Change.** Superseded by the #6/#9/#10 redesign rather than literally "restated as five" — the
formula now has two branches (7 inputs / 6 inputs), stated once normatively in §1.3 with both
branches spelled out verbatim and never referenced with a conflicting count anywhere else in the
document. New test `test_receipt_identity_inputs_are_seven_and_six_per_branch` pins the schema-level
fields that make up both branches so a future edit can't silently drop one without a red test.

---

## Fixture/test updates (mechanical consequence of the schema remediation)

- `tests/fixtures/external_research_handoff/acquisition_policy/valid.yaml` and all 4
  `invalid_*.yaml` fixtures updated to include the new required objects (`canonicalization`,
  `transport_architecture`, `metadata_deny_set*`, `ipv6_transition_policy`, redesigned
  `local_asset_carve_out`, extended `denial`) while preserving each fixture's original targeted
  violation.
- `tests/fixtures/external_research_handoff/import_receipt/*` — all 7 fixtures updated to the new
  required fields (`governance_policy_digest`, `action_manifest_digest`,
  `action_manifest_algorithm_version`, `attempt_structural_summary`, `importer_contract_version`)
  and the `reason_code` → `audit_ref` rename; `invalid_blocked_with_nonempty_actions.yaml` updated
  to exercise the new Branch-B (blocked) identity shape (`packet_digest`/`action_manifest_digest`
  null, `attempt_structural_summary` populated). `invalid_quarantined_without_reason_code.yaml`
  renamed to `invalid_quarantined_without_audit_ref.yaml` to match its new content.
- `tests/unit/test_external_research_schemas.py` — 2 existing tests rewritten to assert the new
  intent (not reverted); 4 new tests added covering the two-branch identity, the blocked-receipt
  null/non-null split, the versioned metadata deny-set, and the single-actor transport
  architecture.
- `tests/test_schema_validation.py` — the two hardcoded minimal-instance dicts for these schemas
  updated to include all newly required fields (general shared registry-coverage test, not owned by
  the interchange-parallel-agent; broke mechanically and was fixed the same way).

## Validation

```
PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/unit/test_external_research_schemas.py -q
# 34 passed

PYTHONPATH=$PWD/src .venv/bin/python -m pytest tests/test_schema_validation.py -q
# 229 passed
```

No git write commands were run.
