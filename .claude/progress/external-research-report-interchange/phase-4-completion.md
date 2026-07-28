---
type: report
schema_version: 2
doc_type: report
title: "Phase 4 Completion — Exact Resolution, Quarantine, and Promotion"
report_category: other
feature_slug: external-research-report-interchange
created: 2026-07-27
status: completed
owners: ["python-backend-engineer"]
related_documents:
  - docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
  - docs/dev/architecture/external-research-handoff-contract.md
  - .claude/findings/eri-p1-contract-audit-gpt56.md
  - .claude/progress/external-research-report-interchange/phase-4-progress.md
---

# Phase 4 Completion — Exact Resolution, Quarantine, and Promotion

## 1. Files created and their responsibilities

- `src/research_foundry/services/source_acquisition_policy.py` (675 lines, new) — ERI-4.2, the SSRF-safe governed acquisition gate. Owns the entire HTTP lifecycle for any locator this ERI phase acquires: single-parse canonicalization, forbidden-address-category validation of every DNS answer, hand-rolled socket connect + connected-peer verification, redirect re-validation, and handoff of already-acquired bytes only.
- `src/research_foundry/services/external_research_resolution.py` (911 lines, new) — ERI-4.1 normalization, ERI-4.3 exact-passage resolution/quarantine, ERI-4.4 promotion seam. Wires `source_acquisition_policy.acquire()` in as the sole network entry point and calls only existing `AssertionRegistry`/`source_cards` authority — no second edition/passage/source-assertion authority is introduced.
- `tests/unit/test_source_acquisition_policy.py` (541 lines, 65 tests, new) — canonicalization matrix, forbidden-address-category matrix (including the IPv6 transition-prefix/overlap edge cases), fake-socket/fake-resolver acquisition scenarios (rebinding, mixed DNS answers, redirect chains/limits/non-HTTP-scheme redirects, proxy-env no-op), plus two real-`http.server` smoke tests on loopback (no real network egress).
- `tests/integration/test_external_research_resolution.py` (705 lines, 31 tests, new) — full `ExternalResearchInterchange.stage()`-wired resolution scenarios: normalization, exact-match zero/multiple/drift/conflict, authorization, promotion, dry-run, cross-workspace, interrupt/resume, exact replay.

No existing file was modified. `external_research_interchange.py`, `assertion_registry.py`, `source_cards.py`, and all existing fixtures/schemas are untouched.

## 2. How ERI-4.1 / 4.2 / 4.3 / 4.4 were satisfied

**ERI-4.1 (normalization).** `normalize_source` / `normalize_candidate` (`external_research_resolution.py:143`, `:185`) convert untrusted packet `Mapping`s into frozen dataclasses (`NormalizedSource`, `NormalizedCandidate`, `NormalizedLocator`), touching only schema-defined fields. `extensions`/`title`/`selector` are carried verbatim and never branched on for control flow — `TestNormalization.test_injection_shaped_extension_values_never_change_normalization` asserts this directly with an injection-shaped string. `normalize_citation_tuple` + `CitationTuple` (lines 258–290) map the draft, unexecuted Intake Citation Adapters `{span, source, relation, confidence}` shape onto the same `NormalizedCandidate` — confirmed no adapter/dedup module from that contract exists on this tree, so none is imported. The net-new byte-accepting extractor the contract requires (`extract_bytes`, lines 293–347) dispatches to the existing `extract_pdf(bytes)` for PDF content and does its own stdlib-only (`html.parser`) HTML→text stripping otherwise — zero I/O, mirrors `extract_pdf`'s "never raises" convention.

**ERI-4.2 (SSRF-safe acquisition gate — the crux).** `acquire()` (`source_acquisition_policy.py:540`) is a single actor that owns the whole HTTP lifecycle end to end, per contract §4.2.0:
- Parses the locator exactly once via `canonicalize_locator` (line 258) — rejects userinfo, percent-encoded/zone-ID hosts, ambiguous numeric hosts (decimal/hex/octal/partial-dotted), >1 trailing dot; IDNA/UTS-46 normalizes non-ASCII hosts via the `idna` package (ships transitively via the existing `httpx` dependency, verified present in the venv).
- Validates **every** DNS answer (`_default_resolve`, injectable) against the full forbidden-address category matrix (`forbidden_address_category`, line 395) before connecting to any of them — a single forbidden answer denies the whole locator, never "picks the public one" (`test_mixed_dns_answers_deny_without_connecting`).
- IPv6 transition/translation prefixes (`DEFAULT_TRANSITION_PREFIXES`, line 149: NAT64 well-known + RFC 8215 local-use, 6to4, Teredo, IPv4-mapped/compatible) are categorically denied by prefix membership; `decode_embedded_ipv4` (line 341) additionally decodes the embedded IPv4 for audit-only visibility.
- Connects with a hand-rolled `socket.socket` (never `urllib`/`httpx`/`requests`), so environment/PAC proxy variables are structurally never consulted (`test_environment_proxy_variables_have_no_effect`), then verifies `getpeername()` against the validated address **before sending any bytes** (`acquire()`, the `peer_ip != ip_obj` check immediately after connect) — this is what closes the DNS-rebinding window (`test_dns_rebinding_peer_mismatch_denied`).
- Redirects (≤3 hops, policy-configurable downward) re-run the full gate on every hop from scratch inside `acquire()`'s own `while True` loop; a failed hop has no fallback and a redirect to a non-HTTP scheme is denied (`test_redirect_to_forbidden_address_denies_on_revalidation`, `test_redirect_to_non_http_scheme_denies`).
- Handoff to extraction passes only already-acquired bytes + minimal response metadata (`AcquisitionOutcome.content`/`content_type`/`status_code`) — `extract_bytes` (ERI-4.1) is the only downstream consumer; nothing re-resolves the locator.
- Every internal denial collapses to one of two codes (`invalid_locator`, `source_unavailable`); `external_research_resolution.py`'s `_resolve_source_impl` (line 638) further collapses every acquisition failure into exactly the closed-vocabulary `source_unavailable` reason before it ever reaches an `ActionResolution` — satisfying contract §4.3's "one generic denial, zero reason-code differential" structurally, not by careful omission.

**ERI-4.3 (exact resolution + quarantine).** `ExternalResearchResolver` (`external_research_resolution.py:525`) precomputes, per `source_id`, every distinct candidate quote citing it (`_collect_quotes`, constructor takes the full `candidate_records` set, because a source action's own `ResolveSource` signature never sees candidates). Per source (`_resolve_source_impl`, line 638): per-item authorization → existing-edition reuse via `AssertionRegistry.find_exact_passages` (read-only, no network) → else full ERI-4.2 acquisition → `extract_bytes` → `AssertionRegistry.ingest()` once to bind/reuse the edition, then once per distinct quote to register passages. Per candidate (`resolve_candidate`/`_resolve_candidate_impl`, lines 613/730): a `selector.passage_id` naming a REAL, already-known passage in the bound edition is resolved directly via `AssertionRegistry.resolve_passage` (`_resolve_via_selector_hint`, line 785) — this is what makes "drift" reachable, since the vendor's anchor is genuine but the candidate's current quote may no longer match what's recorded there; otherwise ordinary `find_exact_passages`-based exact match, filtered to the bound edition only — zero/multiple/wrong-edition all quarantine, never a newer-edition or similarity fallback (mirrors `find_exact_passages`'s own docstring invariant). A `selector` naming a real-looking-but-wrong ID quarantines `passage_binding_conflict` (`_selector_conflicts_with`, line 826). Never performs direct HTTP/PDF/HTML/OCR extraction itself.

**ERI-4.4 (promotion seam).** `default_promote` (line 445) stages a `passage_resolved` candidate's source into `source_cards.ingest_source(..., fetch=False, content=<already-extracted text>, paths=request.paths)` when `target_run_id` is set — never `fetch=True`, never a second acquisition. It never assigns `verified`; only `verify_report` + `assertion_materialization.py` hold that authority (contract §2.4.1) — confirmed by `test_promotion_never_self_assigns_verified`, which injects a caller-supplied `promote` callable that always reports success and still asserts the candidate lands at `passage_resolved`, never `verified`. `target_run_id=None` stays staging-only (`_finish_passage_resolved`, line ~857) and `verified` is categorically unreached — also defensively enforced by `stage()` itself for null `target_run_id`.

## 3. Audit findings owned — how each was satisfied

- **#1 (CRITICAL — the validated connection is not necessarily the connection RFUP uses).** Closed by construction, not by convention: `acquire()` (`source_acquisition_policy.py:540`) is the *only* acquisition entry point Phase 4 calls, and it performs resolution, connection binding, peer verification, redirect-following, and response reading as one integrated operation over one connection it opens and controls end to end (contract §4.2.0). `extract_bytes` (`external_research_resolution.py:293`) — the only thing downstream of acquisition — takes `bytes`, never a locator string, so there is no second fetch anywhere in this phase's code for a rebind/race/pooled-connection-reuse to happen inside.
- **#2 (proxy/delegated-fetch defeats peer verification).** `acquire()` never imports `urllib`/`httpx`/`requests`; it builds its own `socket.socket` and speaks raw HTTP/1.1 (`_build_request`/`_read_response`, lines ~478/492). There is no code path that reads `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` at all — `test_environment_proxy_variables_have_no_effect` sets those env vars and asserts the connector still dials the real target IP. No provider-delegated fetch entry point (`run_search`/`_first_extraction_provider`/any provider `.extract()`) is called anywhere in either new file.
- **#3 (URL canonicalization not frozen / parser differentials).** `canonicalize_locator` (`source_acquisition_policy.py:258`) is the single parse point; its returned `CanonicalLocator` is the only object every later step — DNS resolution, connect, TLS SNI (`server_hostname=canonical.host`), and the request line — consumes. Nothing downstream re-parses the original locator string.
- **#4 (IPv6 transition/translation prefixes not covered).** `DEFAULT_TRANSITION_PREFIXES` (line 149) + `forbidden_address_category`'s IPv6 branch (line 395) deny NAT64 (both the well-known `64:ff9b::/96` and RFC 8215 local-use `64:ff9b:1::/48`), 6to4, Teredo, and IPv4-mapped/compatible categorically by prefix membership, plus an additive `operator_configured_nat64_prefixes` hook. `decode_embedded_ipv4` (line 341) implements the audit-only embedded-IPv4 decode for all six families. Covered by `test_ipv6_transition_prefixes_categorically_denied` (6 parametrized addresses) and `test_operator_configured_nat64_prefix_denied`.
- **#9 — see the dedicated section below. Do not read the per-item authorization work described there as closing this finding; it does not.**
- **#13 (local-ingest carve-out contradicted identity/inert routing).** Not applicable to Phase 4's owned files as shipped, and not claimed as done: Phase 4 performs network acquisition only. Neither new file contains any code path that resolves a packet-supplied string as a filesystem path — there is no `_is_url`-style branch, no `open(locator)`, nothing. The contract's redesigned positive mechanism (a packet-internal asset resolved *only* via an opaque, manifest-bound `attachment_id` key lookup into the packet's own already-hashed accepted-member table; an out-of-packet asset requiring a distinct, out-of-band operator grant binding path+digest) is **not built** anywhere in this phase's files. That mechanism belongs structurally to packet inspection/structural validation (Phase 2, `external_research_interchange.py`'s `inspect_packet`/member-table machinery), which is outside this phase's owned-file scope and was not touched. This is a real, unclosed gap, listed again in §6.

## 4. Audit #9 and `governance_policy_digest` — explicit, not overstated

Audit finding #9 has two distinct halves per the contract (§1.3's `governance_policy_digest` binding, and §1.6's receipt-read reauthorization). **Neither half is closed by this phase.**

- **`governance_policy_digest` itself is completely unchanged.** It is still exactly the placeholder the P2 agent shipped: `_GOVERNANCE_PLACEHOLDER_RULESET` and `compute_governance_policy_digest()` (`external_research_interchange.py:1110`, `:1120`) — a fixed digest over an explicitly-labeled "not implemented" object, computed unconditionally by `stage()`'s own Step 0 before Phase 4's resolver is ever invoked. Phase 4 never reads, writes, or otherwise touches this constant or function. There is still no real caller-identity/authorization concept feeding it, and this phase does not add one.
- **Receipt-read reauthorization (contract §1.6) is not implemented anywhere.** That logic would live inside `stage()`'s replay-lookup path (`_load_receipt` and the surrounding logic in `external_research_interchange.py`), which is entirely outside this phase's owned files (`source_acquisition_policy.py`, `external_research_resolution.py`, and the two test files) and was not modified. A revoked caller replaying the same packet/workspace/target still receives the stored receipt exactly as before this phase — that attack surface is exactly as open now as it was after Phase 2.
- **What this phase DID add, and why it is not the same thing:** a real, functioning **per-item** authorization gate (contract §2.4 step 2, distinct from §1.6/§1.3's *coarse, whole-import* Step 0) — `_authorize_source` (`external_research_resolution.py:404`) plus a workspace-mismatch guard in `resolve_source`/`resolve_candidate` (lines 589/619) — that runs before any registry lookup or acquisition for each source/candidate action, and can quarantine `rights_metadata_missing`/`sensitivity_denied`/`cross_workspace_denied`. This satisfies ERI-4.2's own explicit requirement ("Apply authorization/sensitivity/rights first") and is tested (`TestAuthorization`, `TestCrossWorkspace`). It is genuinely new and genuinely functions. **It is not, and must not be read as, audit #9's fix** — it never touches `governance_policy_digest`, never reauthorizes a receipt *read*, and its own rule set is limited to what the packet schema currently expresses (`access_status`) plus an operator-injectable deny-set (`AuthorizationPolicy`), not a real rights/workspace-governance module (confirmed: `services/governance.py`/`services/sensitivity.py` have no such caller-identity concept to call into).

**Net honest status: audit #9 remains open after this phase**, on both its original halves. Phase 4 adds a complementary, narrower per-item control the contract separately requires, but that is additive scope, not remediation of #9.

## 5. Required H3 scenarios — coverage map

| Scenario | Test | Notes |
|---|---|---|
| existing exact edition | `test_existing_exact_edition_skips_acquisition` | asserts zero `acquire()` calls on reuse |
| newly acquired edition | `test_unique_quote_resolves_newly_acquired_edition` | |
| unavailable locator | `test_unavailable_locator_quarantines_source_unavailable` | |
| missing rights | `test_paywalled_source_quarantines_rights_metadata_missing_without_acquiring` | |
| sensitivity denial | `test_sensitivity_denied_via_operator_policy` | via injected `AuthorizationPolicy`, see §4 caveat |
| unauthorized local/file | `test_non_http_scheme_rejected` (unit) | covered at the acquisition-gate layer (`file://`, `ftp://` both rejected pre-DNS); no dedicated end-to-end resolver test feeds a literal `file://` locator through `_resolve_source_impl` — same code path, not separately re-asserted at that layer |
| loopback/private/reserved/link-local/metadata (v4+v6) | `TestForbiddenAddressCategories` (20+ parametrized cases) | |
| encoded host | `test_percent_encoded_host_rejected`, `test_ipv6_zone_id_rejected`, `test_ambiguous_numeric_host_rejected` (4 forms) | |
| mixed DNS answers | `test_mixed_dns_answers_deny_without_connecting` | |
| rebinding peer | `test_dns_rebinding_peer_mismatch_denied` | |
| public→private redirect | `test_redirect_to_forbidden_address_denies_on_revalidation` | |
| redirect loop/limit | `test_redirect_limit_exceeded_denies` | |
| unique quote | `test_unique_quote_resolves_newly_acquired_edition` | |
| zero match | `test_zero_match_quarantines_citation_unresolved` | |
| multiple match | `test_multiple_match_quarantines_citation_ambiguous` | |
| drift | `test_drift_via_vendor_selector_hint_quarantines_citation_mismatch` | |
| vendor-provided ID conflict | `test_vendor_id_conflict_quarantines_passage_binding_conflict` | |
| one candidate/many sources | `test_one_candidate_many_sources_resolves_against_first_bound` | |
| many candidates/one source | `test_many_candidates_sharing_one_source` | |
| partial basis | `test_partial_basis_quarantines_basis_incomplete` | |
| invalid relation | `test_invalid_relation_quarantines` | exercises the resolver's own defensive re-check directly; the schema itself already closes this vocabulary for packet-sourced records, so the packet-level path cannot actually construct this input — noted honestly in the test itself |
| verification pass | `test_verification_pass_stages_source_card_when_run_exists` | |
| verification fail | `test_verification_fail_when_target_run_missing_quarantines` | |
| cross-workspace lookup | `test_workspace_mismatch_denies_candidate_cross_workspace`, `test_two_workspaces_never_share_a_registry_root` | |
| interrupted acquisition | `test_interrupted_then_resumed_import_converges` | exercises Phase 2's own `_interrupt_after_action_index` resume mechanics with Phase 4's resolver plugged in |
| exact replay | `test_exact_replay_returns_stored_receipt_without_reinvoking_resolver` | asserts zero re-invocation of `acquire()` on replay |

Everything in the plan's H3 list has at least one test. The one caveat is "unauthorized local/file," which is covered at the acquisition-gate unit-test layer but not re-asserted with a dedicated resolver-level integration test using a literal `file://` locator (the code path is identical either way).

## 6. Test counts, tooling, and a real bug found along the way

- `tests/unit/test_source_acquisition_policy.py`: 65 passed.
- `tests/integration/test_external_research_resolution.py`: 31 passed.
- Combined new-surface run: **96 passed**, 0 failed.
- Regression gate (`test_external_research_schemas.py` + `test_external_research_interchange.py` + `test_external_research_profiles.py`): **102 passed**, unchanged from the pre-Phase-4 baseline — zero existing tests modified or broken.
- `ruff check` on both new source files and both new test files: clean.
- `mypy --ignore-missing-imports` on both new source files: clean (0 errors). Full-tree `mypy`/`ruff` was not re-baselined against unrelated pre-existing repo findings (out of this phase's scope).

**A real bug found and fixed along the way (in code owned by this phase, not in unowned files):** `AssertionRegistry.ingest(passages=[])` on a brand-new edition unconditionally publishes a passage-pointer file with `passage_ids: []` (`_publish_passages` has no empty-list guard), which that same registry's own `_load_passages` then rejects on every *subsequent* read (`"published passage pointer must contain unique passage_ids"`). This is a latent landmine in existing, unowned registry code (`assertion_registry.py`, not modified here) — every source-resolution test caught it immediately during development. Fixed at the call site: `_resolve_source_impl` omits `passages=` entirely (letting it default to `None`, i.e. the registry's own well-exercised "whole raw text as one initial passage" path) instead of passing an explicit empty list, with an inline comment so a future reader doesn't reintroduce it.

## Unresolved / deferred — for Phase 5 and beyond

1. **Audit #9 remains open** (both halves) — see §4. This is the most important open item from this phase.
2. **`canonical_refs` / `effect_digest` gap (material, cross-phase).** `ExternalResearchInterchange._effect_digest` (private) hardcodes `canonical_refs: {}` for every action — a Phase-2-era decision made before Phase 4 had acquisition/materialization capability. `ActionResolution` has no field to carry the real `source_edition_id`/`passage_id`/`source_card_id` this phase now produces. `ResolvedActionResolution` (an additive frozen-dataclass subclass, `external_research_resolution.py`) carries that information forward so it is not silently discarded, but until a future patch threads it into `_effect_digest`, the persisted `effect_digest` does not vary with which edition/passage/source-card an action actually bound. Not a security hole (`action_id` already binds an effect to exactly one action per contract §1.3a) but a real precision gap in replay-integrity. **Recommended fix, next time `external_research_interchange.py` is in scope:** add `canonical_refs: Mapping[str, str] = field(default_factory=dict)` to `ActionResolution` itself and change `_effect_digest` to read `resolution.canonical_refs`.
3. **Dry-run interlock (documented, not a defect in shipped code, but load-bearing for Phase 5/ERI-5.3).** `stage(dry_run=True)` invokes the injected resolvers directly with no `dry_run` signal threaded through `ResolutionContext`. `ExternalResearchResolver` closes this at its own boundary via a constructor-level `dry_run` flag (verified: `TestDryRun` — zero acquisition calls, zero registry writes, existing-edition reuse still works read-only). **Phase 5's CLI must construct the resolver with `dry_run=True` whenever `--dry-run` is requested** and pass that instance's bound methods into `stage()` — passing a live resolver into a dry-run `stage()` call would silently perform real acquisition/writes.
4. **Audit #13's redesigned local-ingest carve-out is not built** (see §3's `#13` entry) — belongs to Phase 2 territory, not touched here.
5. **Per-item authorization is honest-but-narrow** (see §4) — real, runs first, but its rule set is limited to `access_status` plus an operator-injectable deny-set; no real rights/workspace-governance module exists yet to call into.
6. **IPv6 embedded-address decoding for RFC 8215 local-use NAT64 and Teredo is implemented but not independently cross-verified against a second reference implementation** — the accept/deny decision does not depend on decode correctness (transition prefixes are denied by prefix membership alone regardless), so this is audit-detail-only risk, not a security gap.
