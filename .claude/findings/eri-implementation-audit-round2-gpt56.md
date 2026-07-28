---
title: "ERI implementation — gpt-5.6-sol adversarial audit (round 2)"
doc_type: report
report_category: finding
schema_version: 2
status: in_progress
source: agent
created: 2026-07-27
updated: 2026-07-27
feature_slug: external-research-report-interchange
promoted_to: []
reviewer: codex gpt-5.6-sol
verdict: CHANGES REQUIRED
audited_head: 81d7ac9
---

Audited current HEAD `81d7ac946e68d421730759cc448574af4f62c70d` against implementation and tests.

The central SSRF remediation is substantially real:

- The policy layer resolves every answer, validates it, connects directly to the selected IP, checks `getpeername()`, then performs TLS and sends HTTP bytes: `source_acquisition_policy.py:591-628`.
- TLS wraps the already-connected socket; SNI does not initiate another resolution: `source_acquisition_policy.py:623-625`.
- Redirects return through canonicalization, DNS validation, and peer verification: `source_acquisition_policy.py:635-647`.
- Extraction receives acquired bytes, not a URL: `external_research_resolution.py:741-750`.
- Promotion supplies `content` with `fetch=False`: `external_research_resolution.py:453-467`.
- No ERI call into RFUP, `search_router`, or another provider-side URL opener remains. Raw sockets also mean environment/PAC proxies are not consulted.
- Built-in NAT64, local-use NAT64, 6to4, Teredo, v4-mapped, and IPv4-compatible ranges are categorically rejected: `source_acquisition_policy.py:149-156,414-416`.

The following defects remain.

1. **HIGH — Governance policy identity does not represent effective authorization policy.**  
   Location: `external_research_interchange.py:1115-1158`, `external_research_import.py:299,411-421,438-449`, `external_research_resolution.py:398-409`.  
   Attack/failure: the digest includes only an RBAC schema version and role names. It omits permission mappings and the supplied rights/sensitivity `AuthorizationPolicy`. Import once under a permissive policy, retry under a denying policy, and the same receipt identity can replay the previously allowed result.  
   Fix: hash the canonical effective RBAC permission mapping and complete per-import rights/sensitivity policy into receipt identity.

2. **HIGH — Membership is mistaken for import permission.**  
   Location: `external_research_interchange.py:1219-1242`, `api/auth/rbac.py:99-135`.  
   Attack/failure: any workspace member passes `authorize_caller()`, including a viewer with no permissions. Token role ceilings and operation-specific authorization are not checked. Service principals are also incorrectly resolved through user membership.  
   Fix: define explicit ERI submit/read permissions, enforce current role and token ceilings, and authorize service principals through their own records.

3. **MEDIUM — Authorization can become stale before the actual receipt read.**  
   Location: `external_research_interchange.py:1575,1651-1661`, `external_research_import.py:368,423-424`.  
   Attack/failure: authorization initially precedes reads, but `stage()` can inspect and wait for the lease before loading and returning a receipt. Revocation during that interval does not prevent disclosure.  
   Fix: reauthorize inside the lease immediately before every receipt existence lookup and return.

4. **HIGH — The single-writer lease is unfenced.**  
   Location: `external_research_interchange.py:248-256,1503-1541,2027`.  
   Attack/failure: stale reclaim is `stat()` followed by unconditional `unlink()`, and release deletes by path without verifying its owner token. A legitimate import exceeding the 300-second stale threshold or two simultaneous reclaimers can delete a replacement lease and create concurrent writers. Receipt publication is an existence check followed by `os.replace`, not CAS.  
   Fix: add heartbeats and fencing generations; compare owner token/inode on reclaim and release; publish immutable artifacts using true create-if-absent CAS.

5. **HIGH — Exactly-once effects have an unprotected crash window and weak replay verification.**  
   Location: `external_research_interchange.py:1875-1892,1967-1996`, `external_research_resolution.py:445-472,941-956`.  
   Attack/failure: downstream promotion occurs before the effect record is durable. A crash between those operations causes resume to repeat source-card/registry effects. Existing effect mappings are then trusted without binding `receipt_digest`, `action_id`, `kind`, or recomputing `effect_digest`; replay checks only a set of action ID/kind pairs.  
   Fix: make downstream mutations idempotent by `action_id` through an outbox/prepare-commit protocol, and fully schema-validate and recompute persisted effects and receipts.

6. **MEDIUM — The orchestrator inspects the packet twice, reopening the snapshot race.**  
   Location: `external_research_import.py:372,406-468`, `external_research_interchange.py:1587`.  
   Attack/failure: resolver state and precomputed identity come from inspection one, while `stage()` independently reopens and inspects the directory. Mutation between inspections can combine snapshot-one resolution with snapshot-two actions, report bytes, or checkpoint identity. Thus the per-member same-descriptor fix does not secure the end-to-end import.  
   Fix: create one immutable `PacketInspection` and pass it through resolver construction, staging, batching, and receipt generation.

7. **MEDIUM — “Primitive-only” YAML loading accepts non-JSON Python values.**  
   Location: `external_research_interchange.py:308-389,1321-1328`, `external_research_sources.schema.yaml:99-106`, `external_assertion_candidates.schema.yaml:117-132`.  
   Attack/failure: the loader inherits SafeLoader constructors for timestamps, `!!binary`, `!!set`, and `!!omap`. Open extension fields allow these through schema validation; dates, bytes, and sets then crash canonical JSON digesting with `TypeError`. This was reproduced directly on the current tree.  
   Fix: recursively whitelist only null/bool/string/finite-number/list/string-keyed-map values and enforce scalar-size ceilings before schema validation.

8. **MEDIUM — Duplicate required roles and member paths create ambiguous provenance.**  
   Location: `external_research_handoff.schema.yaml:96-172`, `external_research_interchange.py:806,853-923,1349-1355`.  
   Attack/failure: required roles use only `minContains: 1`, and paths are not unique. Parsing keeps the last sources/candidates/report content while action construction uses the first declared member path, misbinding accepted records to another member’s provenance.  
   Fix: require unique member paths and exactly one manifest, report, sources, and assertion-candidates role in both schema and runtime.

9. **MEDIUM — Resume and blocked replay remain nondeterministic.**  
   Location: `external_research_import.py:423-436,469-486`, `external_research_interchange.py:1804-1839,1894-1903,1956-1962`.  
   Attack/failure: the `resume=False` checkpoint check occurs outside the lease, so two initially fresh calls can let the second silently resume the first. Separately, blocked retries generate a fresh `created_at` and compare the complete mapping, causing normal delayed retries to raise `ReplayConflictError`.  
   Fix: enforce resume state under the receipt lease and replay stored blocked receipts before generating time-dependent fields.

10. **MEDIUM — IPv6 site-local destinations bypass the SSRF address policy.**  
    Location: `source_acquisition_policy.py:395-440,472-476,604-606`, `external_research_acquisition_policy.schema.yaml:167-184`.  
    Attack/failure: `fec0::/10` addresses are site-local but neither schema nor runtime checks `IPv6Address.is_site_local`. An injected resolver returning `fec0::1` was accepted and connected. Exploitation depends on the deprecated range being routed locally, but it remains a LAN SSRF path.  
    Fix: explicitly deny IPv6 site-local addresses/prefixes before connection.

11. **MEDIUM — Malformed locally configured NAT64 prefixes fail open.**  
    Location: `external_research_acquisition_policy.schema.yaml:247-256`, `source_acquisition_policy.py:371-380,568,599-606`.  
    Attack/failure: the schema accepts arbitrary strings and runtime silently ignores invalid/non-network CIDRs. A commonly entered address-form prefix such as `2600:abcd:1234::1/96` is accepted by schema but discarded, permitting addresses embedding metadata/private IPv4 through that deployment’s NAT64 route.  
    Fix: schema-validate canonical IPv6 networks and reject the entire policy if any configured prefix cannot be parsed.

12. **MEDIUM — A hostile redirect can escape the fail-closed acquisition API.**  
    Location: `source_acquisition_policy.py:551-554,635-647`, `external_research_resolution.py:741-745`.  
    Attack/failure: redirect `urljoin()`/`urlsplit()` occurs outside the transport exception boundary. A response containing `Location: http://[::1` raises `ValueError: Invalid IPv6 URL` instead of returning a denied `AcquisitionOutcome`, interrupting the import.  
    Fix: wrap redirect construction/parsing and convert every exception into the closed unavailable/invalid-locator result.

13. **LOW — The injection integration test is vacuous.**  
    Location: `tests/integration/test_external_research_adversarial_matrix.py:185-204`.  
    Attack/failure: the test claims full-pipeline control-surface safety but runs `dry_run=True` and only asserts that status is one of two normal outcomes. It exercises no acquisition, promotion, source-card filename/body, durable receipt, prompt, route, or command sink.  
    Fix: instrument every relevant sink, run the non-dry path with controlled fakes, and assert hostile sentinels never become control values.

Multiply-linked files are genuinely rejected, members are hashed and buffered from the same descriptor, and safe loading precedes schema validation. No current packet-derived prompt, command, route, schema-selector, or unsanitized traversal sink was found. The bare CLI’s `caller=None` bypass does not presently create a cross-principal replay bypass because it is the only shipped entry point and operates under the trusted local-shell model; it is nevertheless a fail-open API default that must not be reused by an HTTP/MCP/automation surface.

Audit goal completed in approximately 13 minutes; goal-tracker usage was 298,374 tokens.

VERDICT: CHANGES REQUIRED
Audited current HEAD `81d7ac946e68d421730759cc448574af4f62c70d` against implementation and tests.

The central SSRF remediation is substantially real:

- The policy layer resolves every answer, validates it, connects directly to the selected IP, checks `getpeername()`, then performs TLS and sends HTTP bytes: `source_acquisition_policy.py:591-628`.
- TLS wraps the already-connected socket; SNI does not initiate another resolution: `source_acquisition_policy.py:623-625`.
- Redirects return through canonicalization, DNS validation, and peer verification: `source_acquisition_policy.py:635-647`.
- Extraction receives acquired bytes, not a URL: `external_research_resolution.py:741-750`.
- Promotion supplies `content` with `fetch=False`: `external_research_resolution.py:453-467`.
- No ERI call into RFUP, `search_router`, or another provider-side URL opener remains. Raw sockets also mean environment/PAC proxies are not consulted.
- Built-in NAT64, local-use NAT64, 6to4, Teredo, v4-mapped, and IPv4-compatible ranges are categorically rejected: `source_acquisition_policy.py:149-156,414-416`.

The following defects remain.

1. **HIGH — Governance policy identity does not represent effective authorization policy.**  
   Location: `external_research_interchange.py:1115-1158`, `external_research_import.py:299,411-421,438-449`, `external_research_resolution.py:398-409`.  
   Attack/failure: the digest includes only an RBAC schema version and role names. It omits permission mappings and the supplied rights/sensitivity `AuthorizationPolicy`. Import once under a permissive policy, retry under a denying policy, and the same receipt identity can replay the previously allowed result.  
   Fix: hash the canonical effective RBAC permission mapping and complete per-import rights/sensitivity policy into receipt identity.

2. **HIGH — Membership is mistaken for import permission.**  
   Location: `external_research_interchange.py:1219-1242`, `api/auth/rbac.py:99-135`.  
   Attack/failure: any workspace member passes `authorize_caller()`, including a viewer with no permissions. Token role ceilings and operation-specific authorization are not checked. Service principals are also incorrectly resolved through user membership.  
   Fix: define explicit ERI submit/read permissions, enforce current role and token ceilings, and authorize service principals through their own records.

3. **MEDIUM — Authorization can become stale before the actual receipt read.**  
   Location: `external_research_interchange.py:1575,1651-1661`, `external_research_import.py:368,423-424`.  
   Attack/failure: authorization initially precedes reads, but `stage()` can inspect and wait for the lease before loading and returning a receipt. Revocation during that interval does not prevent disclosure.  
   Fix: reauthorize inside the lease immediately before every receipt existence lookup and return.

4. **HIGH — The single-writer lease is unfenced.**  
   Location: `external_research_interchange.py:248-256,1503-1541,2027`.  
   Attack/failure: stale reclaim is `stat()` followed by unconditional `unlink()`, and release deletes by path without verifying its owner token. A legitimate import exceeding the 300-second stale threshold or two simultaneous reclaimers can delete a replacement lease and create concurrent writers. Receipt publication is an existence check followed by `os.replace`, not CAS.  
   Fix: add heartbeats and fencing generations; compare owner token/inode on reclaim and release; publish immutable artifacts using true create-if-absent CAS.

5. **HIGH — Exactly-once effects have an unprotected crash window and weak replay verification.**  
   Location: `external_research_interchange.py:1875-1892,1967-1996`, `external_research_resolution.py:445-472,941-956`.  
   Attack/failure: downstream promotion occurs before the effect record is durable. A crash between those operations causes resume to repeat source-card/registry effects. Existing effect mappings are then trusted without binding `receipt_digest`, `action_id`, `kind`, or recomputing `effect_digest`; replay checks only a set of action ID/kind pairs.  
   Fix: make downstream mutations idempotent by `action_id` through an outbox/prepare-commit protocol, and fully schema-validate and recompute persisted effects and receipts.

6. **MEDIUM — The orchestrator inspects the packet twice, reopening the snapshot race.**  
   Location: `external_research_import.py:372,406-468`, `external_research_interchange.py:1587`.  
   Attack/failure: resolver state and precomputed identity come from inspection one, while `stage()` independently reopens and inspects the directory. Mutation between inspections can combine snapshot-one resolution with snapshot-two actions, report bytes, or checkpoint identity. Thus the per-member same-descriptor fix does not secure the end-to-end import.  
   Fix: create one immutable `PacketInspection` and pass it through resolver construction, staging, batching, and receipt generation.

7. **MEDIUM — “Primitive-only” YAML loading accepts non-JSON Python values.**  
   Location: `external_research_interchange.py:308-389,1321-1328`, `external_research_sources.schema.yaml:99-106`, `external_assertion_candidates.schema.yaml:117-132`.  
   Attack/failure: the loader inherits SafeLoader constructors for timestamps, `!!binary`, `!!set`, and `!!omap`. Open extension fields allow these through schema validation; dates, bytes, and sets then crash canonical JSON digesting with `TypeError`. This was reproduced directly on the current tree.  
   Fix: recursively whitelist only null/bool/string/finite-number/list/string-keyed-map values and enforce scalar-size ceilings before schema validation.

8. **MEDIUM — Duplicate required roles and member paths create ambiguous provenance.**  
   Location: `external_research_handoff.schema.yaml:96-172`, `external_research_interchange.py:806,853-923,1349-1355`.  
   Attack/failure: required roles use only `minContains: 1`, and paths are not unique. Parsing keeps the last sources/candidates/report content while action construction uses the first declared member path, misbinding accepted records to another member’s provenance.  
   Fix: require unique member paths and exactly one manifest, report, sources, and assertion-candidates role in both schema and runtime.

9. **MEDIUM — Resume and blocked replay remain nondeterministic.**  
   Location: `external_research_import.py:423-436,469-486`, `external_research_interchange.py:1804-1839,1894-1903,1956-1962`.  
   Attack/failure: the `resume=False` checkpoint check occurs outside the lease, so two initially fresh calls can let the second silently resume the first. Separately, blocked retries generate a fresh `created_at` and compare the complete mapping, causing normal delayed retries to raise `ReplayConflictError`.  
   Fix: enforce resume state under the receipt lease and replay stored blocked receipts before generating time-dependent fields.

10. **MEDIUM — IPv6 site-local destinations bypass the SSRF address policy.**  
    Location: `source_acquisition_policy.py:395-440,472-476,604-606`, `external_research_acquisition_policy.schema.yaml:167-184`.  
    Attack/failure: `fec0::/10` addresses are site-local but neither schema nor runtime checks `IPv6Address.is_site_local`. An injected resolver returning `fec0::1` was accepted and connected. Exploitation depends on the deprecated range being routed locally, but it remains a LAN SSRF path.  
    Fix: explicitly deny IPv6 site-local addresses/prefixes before connection.

11. **MEDIUM — Malformed locally configured NAT64 prefixes fail open.**  
    Location: `external_research_acquisition_policy.schema.yaml:247-256`, `source_acquisition_policy.py:371-380,568,599-606`.  
    Attack/failure: the schema accepts arbitrary strings and runtime silently ignores invalid/non-network CIDRs. A commonly entered address-form prefix such as `2600:abcd:1234::1/96` is accepted by schema but discarded, permitting addresses embedding metadata/private IPv4 through that deployment’s NAT64 route.  
    Fix: schema-validate canonical IPv6 networks and reject the entire policy if any configured prefix cannot be parsed.

12. **MEDIUM — A hostile redirect can escape the fail-closed acquisition API.**  
    Location: `source_acquisition_policy.py:551-554,635-647`, `external_research_resolution.py:741-745`.  
    Attack/failure: redirect `urljoin()`/`urlsplit()` occurs outside the transport exception boundary. A response containing `Location: http://[::1` raises `ValueError: Invalid IPv6 URL` instead of returning a denied `AcquisitionOutcome`, interrupting the import.  
    Fix: wrap redirect construction/parsing and convert every exception into the closed unavailable/invalid-locator result.

13. **LOW — The injection integration test is vacuous.**  
    Location: `tests/integration/test_external_research_adversarial_matrix.py:185-204`.  
    Attack/failure: the test claims full-pipeline control-surface safety but runs `dry_run=True` and only asserts that status is one of two normal outcomes. It exercises no acquisition, promotion, source-card filename/body, durable receipt, prompt, route, or command sink.  
    Fix: instrument every relevant sink, run the non-dry path with controlled fakes, and assert hostile sentinels never become control values.

Multiply-linked files are genuinely rejected, members are hashed and buffered from the same descriptor, and safe loading precedes schema validation. No current packet-derived prompt, command, route, schema-selector, or unsanitized traversal sink was found. The bare CLI’s `caller=None` bypass does not presently create a cross-principal replay bypass because it is the only shipped entry point and operates under the trusted local-shell model; it is nevertheless a fail-open API default that must not be reused by an HTTP/MCP/automation surface.

Audit goal completed in approximately 13 minutes; goal-tracker usage was 298,374 tokens.

VERDICT: CHANGES REQUIRED
