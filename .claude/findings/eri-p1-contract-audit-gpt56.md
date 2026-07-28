---
title: "ERI P1 contract — gpt-5.6-sol adversarial audit"
doc_type: report
schema_version: 2
created: 2026-07-26
feature_slug: external-research-report-interchange
reviewer: codex gpt-5.6-sol
verdict: CHANGES REQUIRED
---

## Findings

1. **CRITICAL — The validated connection is not necessarily the connection RFUP uses.**  
   **Lines:** Contract 278–282, 348–365, 467–500; Plan 326, 341.  
   **Failure:** The contract places a complete DNS/redirect/peer “gate” before RFUP, but redirects and peer verification can occur only inside the actual HTTP transport. RFUP’s existing `urllib`/`httpx` entry points then open their own connection and can re-resolve after rebinding, race another Happy-Eyeballs address, or reuse an unverified pooled connection.  
   **Fix:** Make the policy layer own the complete HTTP lifecycle—resolution, pinned socket, TLS, redirects, and response—and pass acquired bytes/stream to RFUP, never the original URL for a second fetch.

2. **HIGH — Proxy and delegated-fetch paths defeat connected-peer verification.**  
   **Lines:** Contract 348–350, 483–490, 534–538; Supporting findings 38–43.  
   **Attack:** Environment/system proxies or a provider-side URL fetch expose only the public proxy/provider as the connected peer; that intermediary can independently resolve the hostile hostname to an internal address.  
   **Fix:** Require direct transport with environment/PAC proxies disabled and prohibit provider-delegated URL fetching unless an equivalent end-to-end pinned-address policy is proven.

3. **HIGH — URL canonicalization is not frozen, permitting parser differentials.**  
   **Lines:** Contract 470–482, 491–496.  
   **Attack:** The policy parser and HTTP client can disagree over trailing-dot hosts, Unicode/IDNA versus punycode, percent-encoded authority characters, IPv6 zone IDs, alternate numeric IPv4 forms, or userinfo boundaries; validation sees one host while transport uses another.  
   **Fix:** Parse exactly once with one strict URI implementation, canonicalize IDNA/trailing dots and IP literals before policy evaluation, reject ambiguous encodings, and make transport consume that parsed authority object.

4. **HIGH — IPv6 translation/tunneling addresses are not covered explicitly.**  
   **Lines:** Contract 474–490.  
   **Attack:** NAT64/DNS64, 6to4, Teredo, or locally configured IPv4-embedded IPv6 prefixes can appear globally routable to the validator while translating to loopback, private, link-local, or metadata IPv4 destinations after connection. Post-connect verification still sees the translated IPv6 peer.  
   **Fix:** Reject transition/translation prefixes or decode and validate every embedded IPv4 destination, including locally configured NAT64 prefixes.

5. **MEDIUM — “Cloud metadata destinations” is not a testable deny-set.**  
   **Lines:** Contract 124–129, 474–478.  
   **Failure:** Only `169.254.169.254` is explicit. GCP hostnames, Azure endpoints, Alibaba `100.100.100.200`, IPv6 metadata endpoints, and future provider ranges are covered only indirectly by broad categories whose implementation may vary. Trailing-dot/IDNA hostname variants are unspecified.  
   **Fix:** Freeze a versioned, canonical hostname/CIDR metadata deny-set plus an authoritative special-purpose-address registry version in `policy_digest`.

6. **HIGH — Action and effect identities promised by the plan are absent.**  
   **Lines:** Contract 80–139, 176–186; Plan 262, 353, 361–362.  
   **Failure:** Only packet and receipt digests are defined. No normative `action_id`, ordering payload, or `effect_digest` binds an effect to exactly one action, so duplicated, swapped, or reordered effects can corrupt resume reconciliation. Software changes can also alter the manifest while retaining the same receipt identity.  
   **Fix:** Freeze canonical action/effect digest formulas and bind an importer/normalization algorithm version or action-manifest digest into receipt identity.

7. **HIGH — Member bytes can change after hashing without changing packet identity.**  
   **Lines:** Contract 69–78, 82–111.  
   **Attack:** The cited inode/device checks stop path substitution but not writes through an external hardlink or the already-open file. If parsing rereads after hashing, actions can derive from bytes different from those committed by `packet_digest`.  
   **Fix:** Reject multiply-linked members and parse only from immutable spooled bytes or the exact descriptor stream that was hashed, with before/after metadata and length verification.

8. **HIGH — Concurrent first imports are not serialized.**  
   **Lines:** Contract 161–186, 239–244.  
   **Failure:** Two callers can simultaneously observe no terminal receipt, perform nondeterministic acquisition, write effects, and race terminal publication, producing duplicate canonical effects or different receipts for one identity. Atomic publication alone does not serialize the acquisition/effect phase.  
   **Fix:** Require an atomic receipt-identity reservation/single-writer lease, idempotency keys on every effect, and compare-and-swap terminal publication.

9. **HIGH — Replay can bypass current authorization and governance changes.**  
   **Lines:** Contract 115–139, 165–169, 270–274.  
   **Attack:** A revoked caller can replay the same packet/workspace/target and receive a stored receipt because current caller authorization is not a receipt input or an explicit prerequisite to receipt lookup/return. Changes to sensitivity or rights policy likewise return stale outcomes under the old identity.  
   **Fix:** Reauthorize every receipt read before existence lookup or return, and bind a versioned effective rights/sensitivity governance-policy digest into receipt identity.

10. **MEDIUM — Structurally blocked packets cannot derive the specified receipt identity.**  
    **Lines:** Contract 82–86, 229–237, 267–269.  
    **Failure:** `packet_digest` exists only after structural validation, but structural failure must produce a terminal `blocked` receipt. Unsafe paths, missing members, or unsupported schemas therefore have no defined input for `receipt_digest`.  
    **Fix:** Define a separate rejected-attempt identity over safely captured request metadata, or make pre-identity structural rejection a non-receipt denial.

11. **HIGH — `report.md` is allowed into unspecified “context surfaces.”**  
    **Lines:** Contract 436–459.  
    **Attack:** The prohibition names only system/developer prompts, while the report is expressly allowed on read-only “context” surfaces. Retrieval context, user messages, assistant messages, and tool-capable agent context remain prompt-injection paths.  
    **Fix:** Ban hostile packet bytes from every model message, retrieval context, tool/resource metadata, and tool-capable execution context; permit only escaped human display or capability-free analysis.

12. **HIGH — YAML/JSON parsing is outside the inert-data boundary.**  
    **Lines:** Contract 267–269, 436–453.  
    **Attack:** Schema validation necessarily occurs after deserialization, but the contract does not prohibit YAML object tags, merge keys, duplicate keys, alias bombs, excessive nesting, implicit scalar coercion, non-finite JSON numbers, or duplicate JSON members. Hostile input can execute constructors, exhaust resources, or change validated meaning before the schema gate.  
    **Fix:** Freeze primitive-only safe loaders with tags/merges disabled, duplicate-key rejection, alias/depth/scalar limits, and schema validation against the exact parsed representation.

13. **HIGH — The local-ingest carve-out contradicts both identity and inert routing.**  
    **Lines:** Contract 103–107, 436–442, 501–505, 544–555.  
    **Attack:** An attacker-controlled locator becomes a filesystem path and selects `_is_url` versus local ingestion, despite the universal route/path prohibition. An absolute path or `../../secret` may read host data; relocating the same packet can make the same digest resolve a relative locator to different bytes.  
    **Fix:** Permit only manifest-bound attachment IDs opened beneath the pinned packet root; any out-of-packet asset needs a separate operator grant bound to its canonical path and digest.

14. **MEDIUM — Logs, receipts, checkpoints, exports, and CLI output are not covered by the inert/redaction rule.**  
    **Lines:** Contract 255–259, 436–453, 510–520; Plan 285–286, 355–356, 472.  
    **Attack:** Newlines, ANSI sequences, format tokens, hostile IDs, quoted text, or resolved addresses can reach logs, immutable effect records, metrics, traces, provenance exports, or machine output even when the immediate denial DTO is safe.  
    **Fix:** Define a channel-by-channel taint/redaction matrix with structured logging, control-character encoding, safe generated IDs, and sensitive details confined to a separately authorized audit store.

15. **HIGH — The reason-code vocabulary and aggregate counts are direct existence oracles.**  
    **Lines:** Contract 246–258, 510–520; Plan 342, 364, 415–417.  
    **Attack:** Singleton or differential packets let callers distinguish `cross_workspace_denied`, `sensitivity_denied`, `source_unavailable`, `citation_unresolved`, and related outcomes. Receipt-level reason counts reduce to per-item results, revealing “exists but denied” versus “not found.”  
    **Fix:** Return one generic caller-visible denial with no item mapping or counts; retain specific codes/counts only in an access-controlled audit record.

16. **HIGH — Timing noninterference is simultaneously mandatory and accepted as leaking.**  
    **Lines:** Contract 510–530, 570–571; Plan 342.  
    **Attack:** Instant scheme rejection, DNS latency, redirect depth, stored-receipt replay, and existing-edition reuse have measurably different timing, exposing policy branches, receipt/edition existence, and internal DNS/network reachability. The contract calls this both prohibited and an accepted residual risk.  
    **Fix:** Freeze an observable-timing design such as asynchronous processing with uniform release buckets, padding, rate limits, and statistical acceptance thresholds covering denial, replay, reuse, and success paths.

17. **MEDIUM — The contract’s universal inert-data guarantee is not implementable as written.**  
    **Lines:** Contract 436–442, 467–505, 550–555.  
    **Failure:** Every field is prohibited from becoming a route, schema selector, filesystem path, or execution argument, yet the designated locator necessarily selects network/local routing and becomes an HTTP or filesystem argument; a versioned packet discriminator necessarily participates in schema selection.  
    **Fix:** Distinguish forbidden arbitrary control promotion from narrowly typed, canonical, allowlisted consumption of designated fields, with explicit permitted sinks.

18. **MEDIUM — The frozen/approved status contradicts the supporting governance state.**  
    **Lines:** Contract 4, 9, 36–41; Plan 5, 50, 82–93, 195, 249; Supporting findings 6, 99–101.  
    **Failure:** The contract is marked frozen and says all OQs are resolved, while the plan remains draft/unauthorized, leaves every OQ open, has no findings reference, and prohibits finalization while the findings document remains draft.  
    **Fix:** Reconcile plan status, OQs, findings reference, and exact-tree approvals—or downgrade the contract to proposed.

19. **MEDIUM — Provider acquisition is both required and prohibited.**  
    **Lines:** Contract 348–350; Plan 201, 448–449.  
    **Failure:** The contract names `_first_extraction_provider` as an ERI acquisition entry point, while AC ERI-6 requires no live provider dependency. Implementers cannot satisfy both without an exact permitted seam.  
    **Fix:** Freeze the direct/offline RFUP entry point allowed in v1 and explicitly exclude provider-side URL acquisition.

20. **LOW — Receipt identity has inconsistent input cardinality.**  
    **Lines:** Contract 115–122, 138–139, 176–181, 561–563.  
    **Failure:** The formula enumerates five inputs but twice calls them four, creating a realistic schema/service implementation error.  
    **Fix:** State “five inputs” consistently and provide one normative canonical object definition.

**VERDICT: CHANGES REQUIRED**


hook: Stop
hook: Stop Failed
tokens used
87,018
References: [Contract](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/eri-v1/docs/dev/architecture/external-research-handoff-contract.md), [Implementation plan](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/eri-v1/docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md), [Supporting findings](/Users/miethe/dev/homelab/development/research-foundry/.claude/worktrees/eri-v1/.claude/findings/external-research-report-interchange-findings.md).

## Findings

   **Lines:** Contract 278–282, 348–365, 467–500; Plan 326, 341.  
   **Failure:** The contract places a complete DNS/redirect/peer “gate” before RFUP, but redirects and peer verification can occur only inside the actual HTTP transport. RFUP’s existing `urllib`/`httpx` entry points then open their own connection and can re-resolve after rebinding, race another Happy-Eyeballs address, or reuse an unverified pooled connection.  
   **Fix:** Make the policy layer own the complete HTTP lifecycle—resolution, pinned socket, TLS, redirects, and response—and pass acquired bytes/stream to RFUP, never the original URL for a second fetch.

   **Lines:** Contract 348–350, 483–490, 534–538; Supporting findings 38–43.  
   **Attack:** Environment/system proxies or a provider-side URL fetch expose only the public proxy/provider as the connected peer; that intermediary can independently resolve the hostile hostname to an internal address.  
   **Fix:** Require direct transport with environment/PAC proxies disabled and prohibit provider-delegated URL fetching unless an equivalent end-to-end pinned-address policy is proven.

   **Lines:** Contract 470–482, 491–496.  
   **Attack:** The policy parser and HTTP client can disagree over trailing-dot hosts, Unicode/IDNA versus punycode, percent-encoded authority characters, IPv6 zone IDs, alternate numeric IPv4 forms, or userinfo boundaries; validation sees one host while transport uses another.  
   **Fix:** Parse exactly once with one strict URI implementation, canonicalize IDNA/trailing dots and IP literals before policy evaluation, reject ambiguous encodings, and make transport consume that parsed authority object.

   **Lines:** Contract 474–490.  
   **Attack:** NAT64/DNS64, 6to4, Teredo, or locally configured IPv4-embedded IPv6 prefixes can appear globally routable to the validator while translating to loopback, private, link-local, or metadata IPv4 destinations after connection. Post-connect verification still sees the translated IPv6 peer.  
   **Fix:** Reject transition/translation prefixes or decode and validate every embedded IPv4 destination, including locally configured NAT64 prefixes.

   **Lines:** Contract 124–129, 474–478.  
   **Failure:** Only `169.254.169.254` is explicit. GCP hostnames, Azure endpoints, Alibaba `100.100.100.200`, IPv6 metadata endpoints, and future provider ranges are covered only indirectly by broad categories whose implementation may vary. Trailing-dot/IDNA hostname variants are unspecified.  
   **Fix:** Freeze a versioned, canonical hostname/CIDR metadata deny-set plus an authoritative special-purpose-address registry version in `policy_digest`.

   **Lines:** Contract 80–139, 176–186; Plan 262, 353, 361–362.  
   **Failure:** Only packet and receipt digests are defined. No normative `action_id`, ordering payload, or `effect_digest` binds an effect to exactly one action, so duplicated, swapped, or reordered effects can corrupt resume reconciliation. Software changes can also alter the manifest while retaining the same receipt identity.  
   **Fix:** Freeze canonical action/effect digest formulas and bind an importer/normalization algorithm version or action-manifest digest into receipt identity.

   **Lines:** Contract 69–78, 82–111.  
   **Attack:** The cited inode/device checks stop path substitution but not writes through an external hardlink or the already-open file. If parsing rereads after hashing, actions can derive from bytes different from those committed by `packet_digest`.  
   **Fix:** Reject multiply-linked members and parse only from immutable spooled bytes or the exact descriptor stream that was hashed, with before/after metadata and length verification.

   **Lines:** Contract 161–186, 239–244.  
   **Failure:** Two callers can simultaneously observe no terminal receipt, perform nondeterministic acquisition, write effects, and race terminal publication, producing duplicate canonical effects or different receipts for one identity. Atomic publication alone does not serialize the acquisition/effect phase.  
   **Fix:** Require an atomic receipt-identity reservation/single-writer lease, idempotency keys on every effect, and compare-and-swap terminal publication.

   **Lines:** Contract 115–139, 165–169, 270–274.  
   **Attack:** A revoked caller can replay the same packet/workspace/target and receive a stored receipt because current caller authorization is not a receipt input or an explicit prerequisite to receipt lookup/return. Changes to sensitivity or rights policy likewise return stale outcomes under the old identity.  
   **Fix:** Reauthorize every receipt read before existence lookup or return, and bind a versioned effective rights/sensitivity governance-policy digest into receipt identity.

    **Lines:** Contract 82–86, 229–237, 267–269.  
    **Failure:** `packet_digest` exists only after structural validation, but structural failure must produce a terminal `blocked` receipt. Unsafe paths, missing members, or unsupported schemas therefore have no defined input for `receipt_digest`.  
    **Fix:** Define a separate rejected-attempt identity over safely captured request metadata, or make pre-identity structural rejection a non-receipt denial.

    **Lines:** Contract 436–459.  
    **Attack:** The prohibition names only system/developer prompts, while the report is expressly allowed on read-only “context” surfaces. Retrieval context, user messages, assistant messages, and tool-capable agent context remain prompt-injection paths.  
    **Fix:** Ban hostile packet bytes from every model message, retrieval context, tool/resource metadata, and tool-capable execution context; permit only escaped human display or capability-free analysis.

    **Lines:** Contract 267–269, 436–453.  
    **Attack:** Schema validation necessarily occurs after deserialization, but the contract does not prohibit YAML object tags, merge keys, duplicate keys, alias bombs, excessive nesting, implicit scalar coercion, non-finite JSON numbers, or duplicate JSON members. Hostile input can execute constructors, exhaust resources, or change validated meaning before the schema gate.  
    **Fix:** Freeze primitive-only safe loaders with tags/merges disabled, duplicate-key rejection, alias/depth/scalar limits, and schema validation against the exact parsed representation.

    **Lines:** Contract 103–107, 436–442, 501–505, 544–555.  
    **Attack:** An attacker-controlled locator becomes a filesystem path and selects `_is_url` versus local ingestion, despite the universal route/path prohibition. An absolute path or `../../secret` may read host data; relocating the same packet can make the same digest resolve a relative locator to different bytes.  
    **Fix:** Permit only manifest-bound attachment IDs opened beneath the pinned packet root; any out-of-packet asset needs a separate operator grant bound to its canonical path and digest.

    **Lines:** Contract 255–259, 436–453, 510–520; Plan 285–286, 355–356, 472.  
    **Attack:** Newlines, ANSI sequences, format tokens, hostile IDs, quoted text, or resolved addresses can reach logs, immutable effect records, metrics, traces, provenance exports, or machine output even when the immediate denial DTO is safe.  
    **Fix:** Define a channel-by-channel taint/redaction matrix with structured logging, control-character encoding, safe generated IDs, and sensitive details confined to a separately authorized audit store.

    **Lines:** Contract 246–258, 510–520; Plan 342, 364, 415–417.  
    **Attack:** Singleton or differential packets let callers distinguish `cross_workspace_denied`, `sensitivity_denied`, `source_unavailable`, `citation_unresolved`, and related outcomes. Receipt-level reason counts reduce to per-item results, revealing “exists but denied” versus “not found.”  
    **Fix:** Return one generic caller-visible denial with no item mapping or counts; retain specific codes/counts only in an access-controlled audit record.

    **Lines:** Contract 510–530, 570–571; Plan 342.  
    **Attack:** Instant scheme rejection, DNS latency, redirect depth, stored-receipt replay, and existing-edition reuse have measurably different timing, exposing policy branches, receipt/edition existence, and internal DNS/network reachability. The contract calls this both prohibited and an accepted residual risk.  
    **Fix:** Freeze an observable-timing design such as asynchronous processing with uniform release buckets, padding, rate limits, and statistical acceptance thresholds covering denial, replay, reuse, and success paths.

    **Lines:** Contract 436–442, 467–505, 550–555.  
    **Failure:** Every field is prohibited from becoming a route, schema selector, filesystem path, or execution argument, yet the designated locator necessarily selects network/local routing and becomes an HTTP or filesystem argument; a versioned packet discriminator necessarily participates in schema selection.  
    **Fix:** Distinguish forbidden arbitrary control promotion from narrowly typed, canonical, allowlisted consumption of designated fields, with explicit permitted sinks.

    **Lines:** Contract 4, 9, 36–41; Plan 5, 50, 82–93, 195, 249; Supporting findings 6, 99–101.  
    **Failure:** The contract is marked frozen and says all OQs are resolved, while the plan remains draft/unauthorized, leaves every OQ open, has no findings reference, and prohibits finalization while the findings document remains draft.  
    **Fix:** Reconcile plan status, OQs, findings reference, and exact-tree approvals—or downgrade the contract to proposed.

    **Lines:** Contract 348–350; Plan 201, 448–449.  
    **Failure:** The contract names `_first_extraction_provider` as an ERI acquisition entry point, while AC ERI-6 requires no live provider dependency. Implementers cannot satisfy both without an exact permitted seam.  
    **Fix:** Freeze the direct/offline RFUP entry point allowed in v1 and explicitly exclude provider-side URL acquisition.

    **Lines:** Contract 115–122, 138–139, 176–181, 561–563.  
    **Failure:** The formula enumerates five inputs but twice calls them four, creating a realistic schema/service implementation error.  
    **Fix:** State “five inputs” consistently and provide one normative canonical object definition.

**VERDICT: CHANGES REQUIRED**


