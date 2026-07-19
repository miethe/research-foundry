---
title: "PRD: External Research Report Interchange"
schema_version: 2
doc_type: prd
status: draft
created: 2026-07-18
updated: 2026-07-18
feature_slug: external-research-report-interchange
feature_version: v1
tier: 3
effort_estimate: "38 pts bottom-up; see human brief H1-H6"
prd_ref: null
plan_ref: docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
human_brief_ref: docs/project_plans/human-briefs/external-research-report-interchange.md
related_documents:
  - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
  - .codex/plans/research-interchange-provenance-access-initiative-v1.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
  - docs/project_plans/implementation_plans/features/assertion-ledger-activation-v1.md
  - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/project_plans/feature_contracts/features/intake-citation-adapters.md
  - .codex/worknotes/external-research-report-interchange/decisions-block.md
references:
  user_docs: []
  context: []
  specs:
    - schemas/source_card.schema.yaml
    - schemas/source_edition.schema.yaml
    - schemas/passage.schema.yaml
    - schemas/source_assertion.schema.yaml
    - docs/dev/architecture/assertion-ledger-contract.md
  related_prds:
    - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
    - docs/project_plans/PRDs/features/assertion-ledger-activation-v1.md
    - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
spike_ref: null
adr_refs: []
charter_ref: null
changelog_ref: null
test_plan_ref: null
owner: nick
contributors: []
priority: high
risk_level: high
category: enhancements
tags:
  - prd
  - planning
  - external-research
  - interchange
  - provenance
  - quarantine
  - resumability
milestone: null
commit_refs: []
pr_refs: []
files_affected:
  - schemas/external_research_handoff.schema.yaml
  - schemas/external_research_sources.schema.yaml
  - schemas/external_assertion_candidates.schema.yaml
  - schemas/external_research_import_receipt.schema.yaml
  - schemas/external_research_import_checkpoint.schema.yaml
  - templates/external_research_handoff/v1/
  - src/research_foundry/services/external_research_interchange.py
  - src/research_foundry/services/external_research_resolution.py
  - src/research_foundry/services/source_cards.py
  - src/research_foundry/services/assertion_registry.py
  - src/research_foundry/services/export_service.py
  - src/research_foundry/cli_commands.py
  - tests/fixtures/external_research_handoff/
  - tests/integration/test_external_research_interchange.py
open_questions:
  - id: ERI-OQ-1
    question: "Should a v1 packet accept only a directory, or also define a normative archive transport?"
    owner: backend-architect
    status: open
  - id: ERI-OQ-2
    question: "Which packet bytes and metadata contribute to the stable import identity?"
    owner: backend-architect
    status: open
  - id: ERI-OQ-3
    question: "Should imports without a target run remain staging-only or create a run automatically?"
    owner: lead-pm
    status: open
  - id: ERI-OQ-4
    question: "What bounded item and byte limits are safe defaults for a large local handoff?"
    owner: backend-architect
    status: open
decisions:
  - decision: "External platform prose is always platform_synthesis; citations produce candidates, never supported claims."
    rationale: "A vendor answer is not evidence authority even when it includes plausible citations."
    status: accepted
  - decision: "The importer consumes RFUP extraction and RAL edition/passage services instead of adding URL or PDF extraction."
    rationale: "A parallel fetch or extraction pipeline would split governance and source identity."
    status: accepted
  - decision: "RFUP acquisition is callable only after a hard SSRF-safe acquisition gate validates the locator, every DNS answer, every redirect, and the connected peer."
    rationale: "Delegating HTTP does not make an attacker-controlled vendor locator safe; the importer must fail before any network effect for local, private, reserved, link-local, metadata, redirect, or rebinding targets."
    status: accepted
  - decision: "All packet and vendor-extension fields are untrusted data and never become prompts, tool descriptions, control directives, routes, commands, or schema selectors."
    rationale: "Externally produced research can contain prompt/tool injection strings even when its YAML/Markdown is syntactically valid."
    status: accepted
  - decision: "A content-addressed packet manifest determines one stable workspace-local receipt; checkpoints are separate from the immutable final receipt."
    rationale: "This provides replay idempotency while allowing interrupted imports to resume safely."
    status: accepted
  - decision: "v1 passage promotion is exact and fail-closed; fuzzy or semantic citation matching remains deferred."
    rationale: "Ambiguous similarity cannot establish an immutable source-edition and passage binding."
    status: accepted
success_metrics:
  - "The same byte-identical packet imported twice into the same workspace and target context returns the same receipt and creates no duplicate canonical records."
  - "ChatGPT, Perplexity, Gemini, NotebookLM, and generic fixtures normalize through one vendor-neutral packet contract without live vendor calls."
  - "Every candidate reports one computed completeness tier and a stable quarantine or promotion outcome."
  - "Interrupted large-packet imports resume from validated action receipts and reject truncated, duplicate, extra, or reordered action manifests."
---

# Feature Brief & Metadata

**Feature Name:**

> External Research Report Interchange

**Filepath Name:**

> `external-research-report-interchange-v1`

**Date:**

> 2026-07-18

**Author:**

> Codex planning worker under delegated orchestration

**Related Documents:**

> - The initiative epic and meta-plan own cross-child sequencing and promotion gates.
> - Research Provenance Continuity owns the origin/import context envelope consumed here.
> - RAL and assertion-ledger activation own immutable evidence identity, materialization, reuse, and operational reachability.
> - RFUP owns machine schema stamping, exact-passage verification mode, governed URL/PDF extraction, and run sealing.
> - Intake Citation Adapters owns normalized citation tuples and initial OpenAI/Perplexity citation normalization.

## 1. Executive Summary

Research Foundry can ingest governed source cards, persist immutable source
editions and exact passages, materialize supported source assertions, and verify
reports. It does not yet have a portable contract for taking a finished research
report from ChatGPT, Perplexity, Gemini, NotebookLM, or another tool and preserving
that report's citations without laundering vendor synthesis into verified evidence.

This feature defines `external_research_handoff/v1`, a vendor-neutral directory
packet and a resumable local importer. The importer stages platform synthesis,
resolves declared sources through existing governed acquisition and
assertion-registry services, computes per-candidate completeness, quarantines unsafe
or unresolved material, and permits promotion only through existing RF verification
and RAL materialization.

**Priority:** HIGH

**Key Outcomes:**

- Operators receive prompt/output templates for five producer profiles without coupling RF to vendor APIs.
- Every import has stable packet identity, immutable terminal receipt, deterministic action manifest, and resumable checkpoint state.
- External assertion candidates remain distinguishable from source-resolved, passage-resolved, and RF-verified material.
- Large reports can resume after interruption without duplicate source cards, editions, passages, or candidates.

## 2. Context & Current State

### Proven substrate to reuse

- `adapters/base.py` already states the core trust rule: external output becomes candidates and non-authoritative artifacts, not evidence authority.
- `source_cards.py` performs governed source-card ingestion and existing audit writes.
- `assertion_registry.py` persists content-addressed editions and deterministic passages, verifies source-card snapshots, detects drift, and abstains on ambiguity.
- `assertion_materialization.py` publishes only supported run claims and writes durable assertion/evaluation/observation generations.
- RFUP owns governed URL/PDF acquisition, explicit extraction status, exact-passage verification mode, machine output stamping, and run sealing.
- Research Provenance Continuity owns the shared origin/import context and downstream report-use lineage.
- Intake Citation Adapters defines `{span, source, relation, confidence}` normalization and offline fixtures for OpenAI/Perplexity-shaped citations.

### Live gap

The existing adapters return `AdapterResult.source_candidates` and arbitrary
artifacts, while inbound CLI intake is limited to IntentTree and NotebookLM idea
capture. There is no schema or service that validates a complete external report
packet, assigns stable packet and receipt identities, distinguishes synthesis from
candidate evidence, resumes a partial import, or records why a cited source could
not be promoted.

Operators therefore either copy vendor prose into a run without complete provenance or manually recreate source candidates and citations. Both paths lose reproducibility and make it easy to confuse a cited model answer with passage-bound evidence.

## 3. Problem Statement

> As a research operator, when an external research platform returns a long report with citations, I need to import it as traceable synthesis and candidate evidence, resume partial processing, and promote only exact verified source relationships instead of trusting vendor prose or manually rebuilding its citations.

**Technical root causes:**

1. No canonical external report packet or manifest exists.
2. No workspace-local immutable import receipt binds the exact packet bytes to deterministic actions.
3. No shared completeness vocabulary distinguishes locator, edition, passage, and verified states.
4. No importer joins normalized citation tuples to RFUP acquisition and RAL edition/passage resolution.
5. No quarantine record preserves partial, conflicting, inaccessible, sensitive, or unverifiable outcomes.
6. No bounded checkpoint/replay contract handles large packets or process interruption.

## 4. Goals and Success Metrics

### G1 — Freeze a vendor-neutral packet

Define a deterministic `external_research_handoff/v1` directory that is producible manually, by prompt, or by future tooling and validates without a live vendor API.

### G2 — Preserve synthesis and candidate truth

Persist `report.md` as `platform_synthesis`; stage assertions separately as candidates and never infer verification from vendor labels or citation presence.

### G3 — Resolve exact source lineage

Use existing governed acquisition, immutable edition, exact-passage, verification, and assertion materialization seams to advance candidates through explicit completeness tiers.

### G4 — Make import safe to replay and resume

Derive stable identity from packet bytes and target context, publish immutable terminal receipts, and recover from bounded checkpoints without duplicate canonical effects.

| Metric | Baseline | Target | Measurement |
|---|---:|---:|---|
| Supported producer fixture profiles | 0 | 5 | Schema and integration fixture suite |
| Duplicate canonical effects on exact replay | Unknown/manual | 0 | Import-twice integration test |
| Candidates with computed tier and terminal outcome | 0% | 100% | Receipt reconciliation test |
| Interrupted actions repeated after safe checkpoint | N/A | 0 completed effects repeated | Fault-injection resume tests |
| Vendor synthesis directly promoted | Possible through manual handling | 0 | Negative promotion fixtures |

## 5. User Journeys

### Primary: manual external research handoff

1. Operator selects the appropriate ChatGPT, Perplexity, Gemini, NotebookLM, or generic prompt/output template.
2. The external platform produces report prose, sources, and assertion candidates; the operator saves them into the required directory layout.
3. `rf intake external-report <packet> --workspace <id> [--run <id>] --dry-run` validates structure, computes identity, and reports planned actions without canonical mutation.
4. The operator reruns without `--dry-run`; RF publishes a stable receipt, stages synthesis, and resolves sources/citations through existing services.
5. The receipt reports per-item completeness and quarantine reasons. Only explicitly verified, exact-passage candidates can enter existing claim/assertion flows.

### Secondary: interrupted large report

1. Import begins against a packet with many sources and candidates.
2. The process stops after a bounded batch.
3. A retry validates the original packet and exact action manifest, loads only completed effect receipts, and resumes at the first incomplete action.
4. Completion publishes one immutable terminal receipt with aggregate counts and no duplicate records.

## 6. Contract Requirements

### 6.1 Packet layout

```text
external_research_handoff/v1/
├── handoff.yaml                 # required packet metadata and member manifest
├── report.md                    # required; content_role: platform_synthesis
├── sources.yaml                 # required; may contain an empty candidates list
├── assertion_candidates.yaml    # required; may contain an empty candidates list
├── activity.yaml                # optional, non-authoritative producer activity
└── attachments/                 # optional, manifest-listed regular files only
```

`handoff.yaml` must declare schema name/version, producer profile, research question or task context, declared sensitivity, creation time, content roles, and a sorted member inventory. It may carry opaque vendor/session references, but never credentials, bearer tokens, or filesystem paths as remote identity.

`report.md` must identify itself as `content_role: platform_synthesis`. Its prose and inline citation labels may provide context, but are never parsed as supported RF claims.

`sources.yaml` contains stable packet-local source IDs, locators, titles, dates, declared source metadata, optional normalized citation-tuple data, and vendor-specific fields inside a namespaced extension object.

`assertion_candidates.yaml` contains packet-local candidate IDs, candidate text, classification (`assertion | inference | annotation`), relation, source/citation references, quoted text or selector when present, and producer confidence as a non-authoritative hint.

`activity.yaml` and `attachments/` are optional. Activity is trace-only. Attachments must be listed, hashed, bounded, regular files; path traversal, absolute paths, symlinks, device files, and unlisted content fail closed.

Every field in every member, including namespaced vendor extensions, is
untrusted data. Values may be stored or displayed through bounded escaped data
surfaces, but may not be promoted into system/developer prompts, tool or
resource descriptions, routing/control instructions, adapter/tool names,
commands, schema selectors, filesystem paths, or execution arguments. Strings
that resemble instructions, tool calls, or policy overrides remain inert data.

### 6.2 Stable packet and receipt identity

- The importer computes `packet_digest` from sorted relative member paths plus raw bytes for every accepted member.
- Transport directory name, absolute location, modification time, traversal order, and archive metadata are excluded because v1 accepts a materialized directory, not an archive format.
- Any byte change, member addition/removal, or path change produces a new packet digest.
- `receipt_id` derives from `external_research_handoff/v1`, packet digest, workspace ID, optional target run ID, and importer contract version.
- A receipt manifest and per-action effect receipts are immutable. Checkpoint state is separate and atomically replaceable.
- When every declared action is terminal, the importer publishes one immutable terminal receipt (`completed`, `completed_with_quarantine`, or `blocked`). Exact replay returns it unchanged.
- A packet digest reused with a conflicting action manifest or target context is rejected; the importer does not merge histories.

### 6.3 Completeness tiers

Completeness is importer-computed per source and per assertion candidate. Producer declarations are hints only.

| Tier | Required evidence | Permitted downstream use |
|---|---|---|
| `locator_only` | Valid locator/source descriptor; no immutable rendition binding | Discovery or acquisition queue only |
| `source_resolved` | Governed acquisition bound to one immutable `source_edition_id` | Source context; not claim support |
| `passage_resolved` | Exact cited bytes uniquely bound to one `passage_id` in that edition | Candidate evidence for RF verification |
| `verified` | Existing RF verification accepts the claim relationship and RAL materialization records the exact assertion lineage | Existing governed claim/assertion use |

Packet receipts summarize counts by tier but do not assign one misleading packet-wide tier. No skipped tier is inferred. An unavailable source remains `locator_only`; an exact passage with a failed claim relationship remains `passage_resolved`, not `verified`.

### 6.4 Citation and source resolution

1. Normalize packet source records and optional citation tuples without dropping vendor extensions.
2. Apply workspace, sensitivity, rights, and governance checks before lookup or acquisition can reveal protected state.
3. Reuse an already authorized exact edition when identity and source-card binding match.
4. Otherwise call the RFUP-owned governed acquisition/extraction path; do not implement HTTP, URL, HTML, PDF, or OCR extraction in this feature.
5. Persist or reuse the immutable edition through `AssertionRegistry`.
6. Resolve quoted text/selectors against that exact edition. Exact unique match advances to `passage_resolved`; zero, multiple, drifted, or conflicting matches quarantine.
7. Stage candidates for explicit RF verification. Only the existing verifier/materializer can assign `verified` and durable assertion references.

The importer must not select a newer edition automatically, use fuzzy semantic matching, trust a vendor-provided edition/passage ID without revalidation, or create a supported claim from `report.md`.

Before step 4 can cause a network effect, a hard acquisition gate must:

- allow only explicitly configured HTTP(S) acquisition and reject unauthorized
  local paths, `file:`/non-HTTP schemes, embedded credentials, malformed hosts,
  and authority ambiguity;
- reject IPv4 and IPv6 loopback, private, reserved, link-local, multicast,
  unspecified, carrier-grade/NAT, benchmark/documentation, and cloud metadata
  destinations, including numeric/encoded host tricks;
- resolve DNS under a bounded policy, reject any answer in a forbidden range,
  bind the connection to the validated address, and verify the connected peer
  so DNS rebinding cannot switch targets;
- cap redirects and re-run the full scheme/host/DNS/address/peer policy at every
  hop before following it; and
- fail before acquisition with one safe typed denial and no response body,
  timing-derived target detail, or fallback to a different transport.

An explicitly authorized local asset must enter through an existing governed
local-ingest capability, never by weakening the URL acquisition gate.

### 6.5 Quarantine

Quarantine is a terminal per-item outcome inside a successfully processed packet. It preserves safe identifiers, the last completeness tier, and stable reason codes without echoing sensitive source or assertion text.

Required reason-code families include:

- packet: `required_member_missing`, `unsupported_schema_version`, `unsafe_member_path`, `member_digest_conflict`, `limit_exceeded`;
- source: `invalid_locator`, `source_unavailable`, `rights_metadata_missing`, `sensitivity_denied`, `source_drift`, `edition_binding_conflict`;
- citation: `citation_unresolved`, `citation_ambiguous`, `citation_mismatch`, `passage_binding_conflict`;
- candidate: `basis_incomplete`, `relation_invalid`, `verification_failed`, `cross_workspace_denied`.

Malformed packet structure can block the whole import before effects. Source/candidate failures do not abort unrelated items; they finish as quarantined actions and remain eligible for a future explicit requalification workflow, not silent background promotion.

### 6.6 Producer prompt/output templates

Ship one generic template and four profile overlays:

| Profile | Required adaptation | Explicit boundary |
|---|---|---|
| Generic | Vendor-neutral prompt, file templates, packet checklist | No assumed API or citation format |
| ChatGPT | Map cited answer/source exports into packet-local IDs | No OpenAI API call or session scraping |
| Perplexity | Preserve citations/search-result metadata as extensions | No trust in ranking or citation order |
| Gemini | Normalize grounding/source references and answer spans | No Google API coupling |
| NotebookLM | Manual deterministic export of notebook synthesis and cited sources | No live CLI/API automation; refreshed NotebookLM spec owns qualification |

Every profile produces the same four required files. Templates must instruct the producer to say `unknown` or leave nullable fields empty instead of inventing source dates, authors, locators, quotes, or confidence.

### 6.7 Large-report resumability

- The validated packet manifest defines a deterministic ordered action set before effects begin.
- Actions are bounded and chunked by stable item ID; each writes an immutable effect receipt before checkpoint advancement.
- Retry re-hashes the packet, revalidates the exact action set, and replays no completed effect.
- Missing, duplicate, extra, reordered, or semantically impossible effect receipts fail closed.
- Checkpoints contain cursors and safe IDs only; platform synthesis, quotes, secrets, and source text stay in governed artifacts.
- Defaults for maximum members, total bytes, attachment bytes, sources, candidates, and batch size are configurable and tested at boundary values.
- Cancellation leaves a resumable `pending` checkpoint. It never publishes a false terminal receipt.

## 7. Functional Requirements

| ID | Requirement | Priority | Notes |
|---|---|---|---|
| ERI-FR-1 | Validate the four required files and optional activity/attachments against versioned schemas. | Must | Unknown major versions deny; additive minor fields remain namespaced. |
| ERI-FR-2 | Compute deterministic packet, receipt, manifest, action, and effect identities. | Must | Exact replay is a no-op. |
| ERI-FR-3 | Persist platform synthesis separately from source/candidate records. | Must | Synthesis never becomes evidence implicitly. |
| ERI-FR-4 | Provide generic, ChatGPT, Perplexity, Gemini, and NotebookLM prompt/output templates. | Must | Offline/manual generation is the v1 path. |
| ERI-FR-5 | Compute and expose locator-only, source-resolved, passage-resolved, and verified tiers. | Must | Per item; aggregate counts in receipt. |
| ERI-FR-6 | Resolve acquisition through RFUP and identity/passage through RAL. | Must | No URL/PDF extractor is added. |
| ERI-FR-7 | Quarantine unsafe, unresolved, conflicting, sensitive, or unverifiable items with stable reasons. | Must | No candidate text in safe summaries. |
| ERI-FR-8 | Resume interrupted imports from exact effect receipts and bounded checkpoints. | Must | Reject corrupted history. |
| ERI-FR-9 | Add `rf intake external-report` with dry-run, resume, machine-output, workspace, and optional target-run controls. | Must | No automatic run creation in v1 default. |
| ERI-FR-10 | Expose the stable service seam for later operator MCP use without shipping an MCP tool here. | Should | Operator MCP remains a separate child. |
| ERI-FR-11 | Enforce the SSRF-safe acquisition prerequisite before any RFUP network effect and at every redirect/connection. | Must | Negative fixtures cover local/file, loopback/private/reserved/link-local/metadata, DNS rebinding, and redirect pivots. |
| ERI-FR-12 | Treat all generic/vendor fields and extensions as untrusted data and prohibit promotion into prompts, tool descriptions, routing/control fields, commands, or schema selectors. | Must | Injection-shaped fixtures remain inert and escaped. |

## 8. Non-Functional Requirements

### Security and privacy

- Workspace authorization and sensitivity checks precede registry lookup, source acquisition, candidate counts, and helpful error details.
- The importer rejects unsafe paths and files before opening attachment content.
- Logs, CLI JSON, checkpoints, and safe receipts omit credentials, raw platform synthesis, source text, quote text, and private absolute paths.
- No live vendor call is required or authorized by this package.
- No network acquisition occurs until the full SSRF policy passes; DNS answers, redirects, and connected peers are revalidated and all forbidden-address denials are indistinguishable in safe output.
- No packet/vendor string is interpolated into a system/developer prompt, tool/resource description, route, command, schema selector, or executable argument.

### Reliability

- All canonical writes use existing atomic/immutable patterns.
- A crash at each write boundary is covered by fault-injection tests.
- Replay convergence is determined from canonical effect receipts, never a best-effort counter.
- Legacy runs, source cards, and registries remain readable without backfill.

### Performance

- Import memory is bounded by configured batch and attachment limits; the implementation must not load an unbounded report packet into one aggregate object.
- Manifest hashing streams files; source/candidate processing advances in deterministic chunks.
- Performance gates record representative local fixture sizes and elapsed/memory ceilings without claiming production capacity from synthetic data.

### Observability

- Machine output reports receipt ID, packet digest, status, target context, action counts, completeness counts, quarantine reason counts, and next resume cursor when pending.
- Trace/audit events identify stage and safe IDs but omit packet prose and source content.
- Repository readiness, live vendor qualification, and owner/private workflow qualification remain separate statuses.

## 9. Scope

### In scope

- Directory packet schemas and fixtures for `external_research_handoff/v1`.
- Five prompt/output producer profiles.
- Workspace-local staging, stable identity, immutable terminal receipts, checkpoints, and effect receipts.
- Citation tuple normalization, source resolution, exact passage binding, quarantine, and explicit promotion seam.
- Local CLI/service integration and run/export provenance references.
- Large packet bounds, streaming/hash behavior, cancellation, and resumability.

### Out of scope

- New URL, HTML, PDF, OCR, browser, or web-search extraction.
- Live ChatGPT, Perplexity, Gemini, or NotebookLM API/CLI calls.
- Scraping vendor sessions, browser automation, or unofficial APIs.
- Fuzzy/semantic passage matching or automatic ambiguity resolution.
- Treating `platform_synthesis` as a source card, supported claim, or source assertion.
- A new assertion registry, claim ledger, verifier, materializer, run launcher, or catalog.
- Remote upload/archive transport, public interchange, Knowledge MCP, or Operator MCP tools.
- Automatic run creation or paid discovery.

## 10. Dependencies and Assumptions

| Dependency | Required contract | Readiness truth |
|---|---|---|
| Research Provenance Continuity | Stable origin/import context and run/report correlation envelope | Planned; this child starts after its contract gate |
| RAL | Immutable editions/passages, materializer, lifecycle and governed identity | Shipped repository substrate; private qualification remains separately evidenced |
| Assertion-ledger activation | Reachable forward writes and explicit reuse behavior | Existing package; do not duplicate drivers |
| RFUP | Governed URL/PDF acquisition, exact-passage mode, machine output/version, seal | Planned/current-family dependency; consume its accepted contract |
| Intake Citation Adapters | Citation tuple vocabulary and OpenAI/Perplexity offline normalization | Draft contract; align or amend, do not fork |

Assumptions:

- Research Provenance Continuity P1 freezes the import origin envelope before ERI P1 exits.
- A target workspace is always explicit. A target run is optional; absence means staging-only.
- v1 importer input is a materialized local directory. Archive and remote transfer formats are future transport layers.
- Existing verifier and materializer retain sole authority for `verified` status.

## 11. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Citation laundering promotes vendor prose | Critical | Medium | Hard `platform_synthesis` role; exact passage plus existing verifier required |
| Packet path traversal or attachment abuse | Critical | Medium | Regular-file allowlist, normalized relative paths, byte/count limits, pre-open validation |
| Digest excludes meaningful content | High | Medium | Canonical raw-byte member manifest; golden digest fixtures; contract review |
| Replay duplicates partial effects | High | Medium | Stable action IDs, immutable effect receipts, exact-manifest equality, fault injection |
| Provider output shape drifts | Medium | High | Thin profile overlays; generic schema remains canonical; fixture versioning |
| Sensitive source existence leaks | High | Medium | Policy-before-resolution and safe denial summaries |
| Fuzzy citation heuristics bind wrong passage | Critical | Medium | No fuzzy promotion in v1; zero/multiple matches quarantine |
| Large packet exhausts memory or disk | High | Medium | Streaming hashes, chunked processing, hard configurable limits |
| External qualification is overstated | High | Medium | Offline fixture, repository-ready, and live-qualified statuses remain distinct |
| Vendor locator reaches local/private/metadata services | Critical | Medium | Hard pre-effect SSRF gate; public-address allow policy; DNS/peer binding; redirect revalidation; rebinding fixtures |
| Packet text injects prompts, tools, or control policy | Critical | High | Treat every vendor field as inert untrusted data; forbid control-surface promotion; escaped rendering and injection fixtures |

## 12. Acceptance Criteria

### ERI-AC-1 — Vendor-neutral contract and producer profiles

- A packet containing the four required members validates under `external_research_handoff/v1`.
- Generic, ChatGPT, Perplexity, Gemini, and NotebookLM fixtures normalize to the same canonical structures.
- Missing required members, unknown major schema, unsafe paths, or undeclared attachments block before effects.
- Verified by plan tasks `ERI-6.1` and `ERI-6.5`.

### ERI-AC-2 — Immutable and idempotent import receipt

- Same packet bytes, workspace, target run, and importer contract yield the same receipt ID and byte-identical terminal receipt.
- A second import creates no duplicate source card, edition, passage, candidate, or effect receipt.
- Changed bytes or target context produce a distinct identity; a conflicting same-identity manifest is rejected.
- Verified by plan tasks `ERI-6.2` and `ERI-6.5`.

### ERI-AC-3 — Completeness and quarantine truth

- Every source and candidate ends at exactly one computed tier plus one terminal action outcome.
- Unavailable, drifted, ambiguous, mismatched, rights-missing, sensitivity-denied, and verification-failed fixtures remain quarantined with stable safe reason codes.
- Aggregate counts reconcile exactly to the terminal action manifest.
- Verified by plan tasks `ERI-6.2` and `ERI-6.5`.

### ERI-AC-4 — Exact-edition and passage promotion

- Source acquisition uses the RFUP-owned path and publishes or reuses one immutable edition.
- Citation promotion succeeds only for a unique exact passage in that edition and an accepted RF verification relationship.
- Vendor-provided IDs, report prose, newer editions, and fuzzy similarity cannot bypass revalidation.
- Verified by plan tasks `ERI-6.2` and `ERI-6.5`.

### ERI-AC-5 — Large-report resumability

- Fault injection at manifest, staging, source, passage, candidate, and terminal-publication boundaries leaves a pending resumable state or an immutable terminal receipt, never a false completion.
- Retry skips completed effects, resumes the first incomplete action, and converges to the same terminal receipt as an uninterrupted run.
- Truncated, extra, duplicate, reordered, or impossible receipts/checkpoints fail closed.
- Verified by plan tasks `ERI-6.3` and `ERI-6.5`.

### ERI-AC-6 — Compatibility and authority boundaries

- Existing run/source-card/assertion fixtures remain readable and focused regression gates pass.
- No new network/PDF/HTML/OCR extraction implementation or live vendor dependency appears in the changed tree.
- Staging-only imports do not create a run; operator MCP and remote transports remain absent.
- Machine responses omit raw prose, quotes, credentials, private paths, and denied identifiers.
- Verified by plan tasks `ERI-6.1`, `ERI-6.2`, and `ERI-6.5`.

### ERI-AC-7 — Acquisition and vendor data stay hostile-input safe

- Unauthorized local/file, loopback, private, reserved, link-local, metadata,
  encoded-host, DNS-rebinding, and redirect-pivot locators fail before RFUP
  acquisition or any response-body read.
- Every DNS answer, redirect target, and connected peer is validated under the
  same bounded policy; a failed hop never falls back to another transport.
- Generic and all four vendor profiles include injection-shaped strings in
  report, source, candidate, activity, and extension fields; these remain inert
  escaped data and never change prompts, tools/descriptions, routing, schema
  selection, commands, or execution arguments.
- Verified by plan tasks `ERI-6.2` and `ERI-6.5`.

## 13. Target State

Research Foundry accepts a deterministic external research directory, records
exactly what was received, and keeps the platform's report as synthesis. It can
resolve each declared source to an immutable edition, bind citations only to exact
passages, quarantine everything else with stable reasons, and resume a large import
safely. The output is suitable for later governed planning or operator tooling
because its receipt and provenance are machine-readable, but neither those future
consumers nor any live vendor automation ship in this feature.

## 14. Deferred Scope

- Live provider API/CLI automation and secret lifecycle.
- Archive and remote transfer containers.
- Semantic/fuzzy citation recovery.
- Public or cross-workspace packet exchange and rights promotion.
- Automatic run creation and background requalification.

The implementation plan must create shaping design specs for promoted deferred items or record explicit non-promotion rationale before final closeout.

## 15. Documentation and Review Gates

Implementation must update the root CHANGELOG, README intake inventory, a concise user guide, an architecture contract, and the Research Foundry skill route after runtime behavior is final. It must also publish schema examples and a machine-output example that contains no private content.

Every Tier 3 phase requires `task-completion-validator` review. Karen reviews the P1 contract milestone, the P4/P5 integrated importer milestone, and the final exact tree. Any material fix or generated-contract change invalidates prior approval until the same gate is rerun against the new tree.

Repository-owned fixture success is `repository-ready`, not proof that a live vendor export, owner-held report, private workspace, remote transport, or downstream MCP integration ran.

**Status:** Draft. Approval authorizes planning completion only; no implementation, progress initialization, live vendor call, or release action is authorized.
