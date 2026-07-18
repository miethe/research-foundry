---
schema_name: ccdash_document
schema_version: 2
doc_type: human_brief
doc_subtype: feature_brief
root_kind: project_plans
id: BRIEF-external-research-report-interchange
title: "External Research Report Interchange — Human Brief"
status: draft
category: human-briefs
feature_slug: external-research-report-interchange
feature_family: external-research-report-interchange
feature_version: v1
prd_ref: docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
intent_ref: null
epic_ref: null
related_documents:
  - docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md
  - .codex/plans/research-interchange-provenance-access-initiative-v1.md
  - .codex/worknotes/external-research-report-interchange/decisions-block.md
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/PRDs/enhancements/rf-upstream-evidence-foundry-v1.md
  - docs/project_plans/feature_contracts/features/intake-citation-adapters.md
owner: nick
contributors: []
audience: [humans]
priority: high
confidence: 0.72
created: 2026-07-18
updated: 2026-07-18
target_release: null
tags: [human-brief, external-research, interchange, provenance, quarantine, resumability]
---

# External Research Report Interchange — Human Brief

> Living document for human orchestrators. Agents: do not load unless explicitly instructed.
> Status: draft | Updated: 2026-07-18

## 1. Context Pointers

- **PRD**: `docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md`
- **Plan**: `docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md`
- **Decisions**: `.codex/worknotes/external-research-report-interchange/decisions-block.md`
- **Epic / sequence authority**: `docs/project_plans/PRDs/enhancements/research-interchange-provenance-access-epic-v1.md`; `.codex/plans/research-interchange-provenance-access-initiative-v1.md`
- **Reused foundations**: RAL PRD/plan, assertion-ledger activation PRD/plan, RFUP PRD/plan, Intake Citation Adapters contract
- **SPIKEs**: None required before approval if P1 confirms existing immutable/resume patterns are reusable. A material identity or passage-resolution unknown stops P1 and triggers a bounded SPIKE.

## 2. Estimation Sanity Check

**Bottom-up total**: 38 points
**Top-down anchor**: 36–40 points for a hostile-input interchange with a hard SSRF-safe acquisition prerequisite, five inert-data producer profiles, exact evidence resolution, and resumable orchestration. Runtime RAL services are shipped implementation-shape anchors; RFUP and Intake Citation Adapters are planning dependencies, not claimed completed velocity.
**Confidence**: 0.72 (medium). The architecture has strong local analogs, but hostile multi-file input, DNS/redirect/peer validation, vendor injection resistance, five profiles, and large-report resume are new as one integrated product surface.

### H1 — Noun counting

Zero new CRUD-with-RBAC database nouns are planned. ERI introduces file-canonical packet, source-candidate, assertion-candidate, manifest, checkpoint/effect, and terminal-receipt artifacts, but they are not new relational CRUD resources with independent routers and RBAC repositories. H1 therefore contributes no automatic `N × 2` table floor.

That does not make the artifacts free. Their schema, atomicity, compatibility, and adversarial cases are budgeted directly in P1/P2/P4/P5.

### H2 — Dual-implementation multiplier

Not applicable. The authoritative path is one workspace-local file-backed implementation using existing RAL/RFUP services. Template profiles are producer mappings, not five storage implementations. A future remote/enterprise transport would require fresh sizing rather than a hidden 1.8× multiplier here.

### H3 — Algorithmic service flag

Two phases qualify and clear the 3-point floor:

- **P4 exact resolution/quarantine (9 pts)**: source normalization, authorized
  edition reuse/acquisition behind scheme/address/DNS/redirect/connected-peer validation, exact passage resolution, candidate dependency checks,
  and promotion. Scenarios include existing/new edition, unavailable locator,
  missing rights, sensitivity denial, unique/zero/multiple quote, drift, ID conflict,
  many-to-one sharing, partial basis, invalid relation, verifier pass/fail,
  cross-workspace denial, unauthorized local/file, IPv4/IPv6 forbidden ranges,
  metadata endpoints, mixed DNS answers, rebinding peers, redirect pivots,
  interruption, and replay.
- **P5 resumable importer (6 pts)**: deterministic action planning, batching, cancellation, checkpoint/effect reconciliation, and terminal publication. Scenarios include interruption at each boundary, exact replay, wrong target, truncated/extra/duplicate/reordered actions, stale checkpoint, oversize packet, and uninterrupted/resumed convergence.

A pre-implementation SPIKE is not mandatory because `AssertionRegistry`, `AssertionImpactReconciler`, and RAL replay behavior provide concrete local patterns. P1 must stop and spike if exact action identity or streaming limits cannot be enumerated and reviewed.

### H4 — Bundle versus sum

| Capability area | Independent estimate | Notes |
|---|---:|---|
| Packet/identity/tier contracts | 6 pts | Cross-schema trust boundary, hostile-data/acquisition policy, compatibility |
| Safe staging and receipts | 6 pts | Hostile filesystem input plus immutable/replay semantics |
| Five producer profiles | 6 pts | Generic + four overlays + injection-shaped inert-data fixtures |
| Source/citation resolution | 9 pts | H3 SSRF-safe acquisition, exact binding, and quarantine |
| Large-report importer/CLI | 6 pts | H3 state transitions, limits, target projection |
| Hardening/docs/plumbing | 5 pts | Contract fixtures, regression, docs, skills, reviewers |
| **Sum / locked total** | **38 pts** | No package discount |

### H5 — Anchor reference

Closest comparable surfaces are:

- RAL edition/passage registry for immutable content-addressed writes and exact match behavior;
- RAL assertion materializer for generation publication, replay, and durable projection repair;
- RAL impact reconciler for action receipts, interruption/resume, and exact-manifest validation;
- existing adapter/offline fixtures plus Intake Citation Adapters for external-output normalization;
- RFUP's planned machine-contract, acquisition, exact-passage, and run-seal boundaries.

Git and runtime code prove the RAL analogs landed. The inspected repository does not
contain an authoritative actual-point ledger, and RFUP/intake-citation plans do not
prove completed execution. H5 is therefore a medium-confidence surface comparison,
not measured velocity. The estimate is higher than any single analog because ERI
composes hostile packet input, five producer contracts, evidence resolution,
quarantine, CLI, and large-report state.

### H6 — Hidden plumbing budget

P1–P5 total 33 points. P6 adds 5 points, or 15.2%, for schema/fixture compatibility, safe output contracts, focused regressions, SSRF/injection boundary scans, docs, README, CHANGELOG, Research Foundry skill routing, deferred specs/findings closeout, and exact-tree reviewer evidence. This is inside the recommended 15–20% range.

**Reconciliation**: The reviewer-expanded bottom-up total is 38 points. Reuse reduces architecture uncertainty but does not erase the SSRF, hostile-data, atomicity, compatibility, and adversarial test surface.

## 3. Wave and Orchestration Notes

**Critical path**: Research Provenance Continuity `RPC-1.G` → ERI P1 hostile-data/acquisition contracts → P2 staging/receipts → P4 SSRF-safe resolution → P5 resumable importer → P6 finalization.

**Parallel opportunity**: P3 producer templates and offline fixtures may execute beside P2 after the P1 generic schema is frozen. Split profile ownership by directory/file and keep one integration owner for common templates and fixture naming.

**Merge order**: P1 first. Integrate P2 and P3 independently and rerun P2 review if shared schema conflicts alter receipt behavior. P4 merges after P2. P5 consumes final P3/P4 outputs. P6 owns the only final AC evidence set and docs examples.

**Cross-feature coupling**:

- Do not start ERI P1 before Research Provenance Continuity freezes the import/origin envelope.
- If RFUP or Intake Citation Adapters have not landed when P4 begins, ERI may implement against reviewed contracts only in an isolated branch; integration remains blocked until exact runtime seams exist.
- Operator MCP may later call the ERI service, but it cannot pull ERI CLI/MCP scope forward.

## 4. Open Questions Ledger

| ID | Source | Question | Status | Default if unresolved |
|---|---|---|---|---|
| ERI-OQ-1 | PRD/P1 | Directory only or archive transport? | open | Materialized local directory only. |
| ERI-OQ-2 | Epic OQ-E3/P1 | What contributes to packet identity? | open | Sorted relative paths + raw bytes of every accepted member; exclude absolute path, mtime, traversal/transport metadata. |
| ERI-OQ-3 | PRD/P1 | What happens without `target_run_id`? | open | Staging-only; no automatic run. |
| ERI-OQ-4 | PRD/P1 | Which resource limits ship? | open | Conservative configurable local defaults; exceed = pre-effect block, never truncation. |
| ERI-OQ-5 | Decisions/P4 | When can tier become verified? | open | Only after existing RF verification and materialization publish exact lineage. |
| ERI-OQ-6 | Decisions/P4 | When may an edition be reused? | open | Only after workspace/rights policy and exact content/source-card binding validation. |

P1 must resolve OQ-1..4 or document a blocker. OQ-5/6 defaults are trust boundaries and require explicit amendment to change.

## 5. Deferred Items Rationale

- **Live provider automation**: Deferred because secrets, cost, SDK drift, vendor policy, canary, and rollback are independent risks. Promote through `external-research-provider-automation.md` only with an approved provider and live qualification owner.
- **Archive/remote transport**: Deferred because safe local directory import does not prove upload, extraction, auth, tenant, or remote identity. Promote after threat model and concrete transfer need.
- **Fuzzy citation recovery**: Deferred because similarity cannot establish exact evidence identity. Promote only from measured unresolved-rate evidence and a labeled evaluation corpus.
- **Public/cross-workspace interchange**: Deferred because rights and sensitivity promotion are separate from private local intake. Promote after public-rights and tenant-isolation review.
- **NotebookLM live qualification**: Routed to the initiative's dedicated NotebookLM refresh design spec; do not create a duplicate here.

## 6. Risk Narrative

- **Citation laundering is the critical risk**: A polished report with plausible links can look authoritative. Reviewers should trace every verified candidate back through receipt → source edition → exact passage → existing verifier/materializer outcome.
- **Receipt identity is load-bearing**: Helpful normalization of packet bytes may hide a meaningful change. Prefer raw member bytes and explicit paths; treat any excluded field as a security decision.
- **Checkpoints are not receipts**: Mutable progress state can aid resume but cannot be cited as terminal truth. Final reviewers should ensure only immutable effects and terminal receipt establish completion.
- **Policy ordering matters**: The importer must not reveal an edition, passage, source count, candidate ID, or distinct denial timing before workspace/sensitivity/rights authorization.
- **Fixture truth is limited**: Five vendor-shaped fixtures prove contract compatibility, not that current ChatGPT, Perplexity, Gemini, or NotebookLM exports were exercised live.
- **Delegated fetching is still SSRF-sensitive**: Calling RFUP is permitted only after authorization plus scheme/host/IP/DNS/redirect/peer checks. A public first hop that redirects or rebinds private is still denied.
- **Every vendor value is adversarial data**: Namespaced extensions do not create trust. Instruction-like strings must remain escaped data and cannot influence prompts, tools/descriptions, routes, schemas, commands, or arguments.

## 7. What to Watch For

- An implementation that parses citations directly from `report.md` instead of consuming `sources.yaml` and `assertion_candidates.yaml`.
- Direct `httpx`, requests, HTML, PDF, OCR, browser, or provider SDK code in ERI modules rather than RFUP calls.
- An RFUP call made before the importer validates every DNS answer, redirect hop, and connected peer, or a denial that falls back to local/file transport.
- Vendor report/source/candidate/activity/extension text interpolated into system prompts, tool/resource descriptions, route/schema selectors, commands, or executable arguments.
- A producer-supplied `verified`, `source_edition_id`, or `passage_id` accepted without canonical revalidation.
- URL/date dedup treated as source-edition identity; exact content digest and source-card binding remain authoritative.
- Checkpoint advancement before effect publication, or a resume path that trusts counters rather than effect receipts.
- Memory use proportional to the entire packet rather than bounded batches/streams.
- Generated examples or CLI errors leaking report prose, quoted passages, tokens, or private absolute paths.
- P3/P4 review summaries reused after schema or integration conflict resolution changed the exact tree.

## 8. Expected Success Behaviors

- [ ] A generic or vendor-profile packet validates into the same canonical member model without live credentials.
- [ ] The report is inspectable as platform synthesis but never appears as a source card or supported claim.
- [ ] Re-importing the exact packet into the same workspace/target returns the same terminal receipt and no duplicate canonical effects.
- [ ] An accessible source advances from locator-only to source-resolved only after governed acquisition and immutable edition binding.
- [ ] Unauthorized local/file, loopback/private/reserved/link-local/metadata, mixed-DNS, rebinding, and redirect-pivot locators fail before any network effect.
- [ ] Injection-shaped values in every producer profile remain inert escaped data and do not mutate prompts, tools/descriptions, routing, schemas, commands, or arguments.
- [ ] A citation advances to passage-resolved only when one exact passage matches in that exact edition.
- [ ] Missing, inaccessible, sensitive, drifted, ambiguous, mismatched, or verification-failed candidates remain quarantined with stable safe reasons.
- [ ] Cancelling a large import leaves a pending cursor; retry skips completed effects and converges with uninterrupted execution.
- [ ] An import without a target run stays staging-only and does not create a run, plan, search, or paid provider call.
- [ ] Legacy runs/source cards/assertion records remain readable without fabricated packet or receipt IDs.
- [ ] Closeout labels offline fixtures, repository readiness, private qualification, live vendor qualification, deployment, and release separately.

## 9. Running Log

- [2026-07-18] Reviewer expansion made SSRF-safe acquisition and hostile vendor-data handling hard prerequisites. H1-H6 were re-derived and the package locked at 38 points; H5 remains medium confidence because shipped RAL surfaces provide implementation-shape anchors but no authoritative actual-point ledger, while RFUP and Intake Citation Adapters remain plan/contract dependencies until separately proven.
