---
title: "Public Knowledge Platform v1: Open Claims and Sources Library"
schema_version: 2
doc_type: prd
status: draft
created: 2026-11-13
updated: 2026-11-13
feature_slug: public-knowledge-platform
feature_version: v1
prd_ref: null
plan_ref: null
related_documents:
  - docs/project_plans/design-specs/research-foundry-public-knowledge-platform.md
  - docs/project_plans/design-specs/public-knowledge-platform-open-questions-2026-11-13.md
references:
  - docs/project_plans/PRDs/features/public-multiuser-release-activation-v1.md
  - docs/project_plans/design-specs/public-knowledge-platform-regrounding-checklist-2026-11-13.md
spike_ref: null
adr_refs: []
charter_ref: null
changelog_ref: null
test_plan_ref: null
owner: project owner
contributors: []
priority: high
risk_level: high
category: features
tags:
  - public-instance
  - agent-access
  - assertions
  - rights
milestone: null
commit_refs: []
pr_refs: []
files_affected: []
changelog_required: true
---

# PRD: Public Knowledge Platform v1

> Rewritten 2026-11-13 to the owner intent.

Draft requirements, not implementation or launch approval. The [owner intent](../../design-specs/research-foundry-public-knowledge-platform.md#owner-intent-2026-11-13-governs-first-release-scope) governs first-release scope. The five design decisions in §8 are decided; legal review remains an open launch prerequisite. Earlier showcase recommendations in the [historical decision pack](../../design-specs/public-knowledge-platform-decisions-2026-11-13.md) are not first-release decisions.

## 1. Problem

Agents need reusable claims tied to exact source words, with enough provenance to inspect and cite them during a task. A generated report or a loose summary alone does not provide that evidence. Research Foundry has the strict assertion substrate, but the documented library has no strict assertions and public agent access is incomplete. The product re-presents existing sources in the Foundry format; it neither creates new research nor grades sources. Demand remains a hypothesis until outsiders use it.

## 2. Users and jobs

| User | Job and milestone |
| --- | --- |
| An outsider's agent | During real work, search claims and sources, pull a claim's quote and provenance, and cite or use it. This is the first success milestone. |
| Readers and agent builders | Read openly and connect agents without privileged access or a hosted research run. |
| Seed operators | Rerun core sources through the strict path in a few domains, with bounded cost and validated public eligibility. |
| Contributors and their agents | Run the open toolkit with their own model and send back source-linked records. Outside contribution is milestone 2. |
| Instance operators | Keep public data separate from private data, apply the eventual rights rule, and handle correction and removal. |

Research flows through the toolkit, while agents retain direct open access and may search beyond the library.

## 3. Approved owner intent

The ten approved points below paraphrase owner intent. The decision record is node_01KZ755YBS3A99PVJBC53R4DTY.

1. The public instance is an open claims library tied to a sources library, built for agents to read and cite. Inferences come next; reports later.

2. It creates no new research and grades no sources. It re-presents sources in Research Foundry's format, with provenance.

3. Reading is open to all, and agents can pull everything we can.

4. Contributors run an open toolkit with their own model. We pay for no one's breakdown. Running it ourselves is a later, possibly paid, option.

5. Each record says which model did what, and captures the process behind it.

6. Entry is a thin door: the quote must be in the source, word for word. Everything above that is a label shown openly.

7. A claim's own quoted words are public even where the full source text cannot be.

8. We seed it ourselves first, in a few domains, by rerunning core sources through the strict path.

9. Success is an outsider's agent using it mid-task. Others adding to it is the second milestone.

10. Later growth: scoring for independently reached claims, proposed edits, chained inferences, citation links, federation and peer-to-peer sharing.


## 4. Scope and functional requirements for v1

| ID | Requirement | Verification at implementation |
| --- | --- | --- |
| FR-1 | Provide an open claims library tied to a sources library. A claim resolves to its exact source edition and quote anchor, with stable identity. | Follow a retrieved claim to its source and exact passage. |
| FR-2 | Use the strict assertion path: the quoted words must occur verbatim in the source. Run-local summaries are not substitutes. The check uses no model. | Accept an exact quote; reject changed words or an invalid anchor. |
| FR-3 | Show labels openly above that thin entry check. A label or declared model is not proof of truth. Source grading, reviewer quorum and promotion are not v1 entry requirements. | Inspect labels and check outcomes separately; no review queue is required for entry. |
| FR-4 | Make each claim's quoted words public even where full source text cannot be. Keep source links, edition identity and permitted context accessible. Apply the common floor and source-license exceptions in D-open-2, subject to the legal launch prerequisite. | Compare public claim output with the source policy; do not expose restricted full text. |
| FR-5 | Record which model did which step, provider and model version where available, extraction contract or prompt version, producing process, source/edition, and extraction, synthesis and verification steps actually performed. Missing or declared-only provenance must be visible. | Retrieve a record and reconstruct its producing process without private paths or credentials. |
| FR-6 | Offer open read and agent pull of all public claim, source, label and process fields available to readers. Search and direct retrieval must work without a hosted research run. Transport choice must not block this requirement. | An outside agent searches, retrieves and cites a complete public record without privileged access. |
| FR-7 | Package an open toolkit that contributors run using their own model and resources. It returns the distilled records and process metadata for deterministic intake checks. The service pays for no contributor breakdown. | Run toolkit outside the service; submit a valid record and reject a mismatched quote. |
| FR-8 | Seed a small mix of agent-tools/software-engineering and research-methods domains with core sources rerun through the same strict path. Validate source eligibility before publication. Bound and tune seeding volume and cost. | Record seed throughput, stored bytes, strict assertion yield and rejection reasons. |
| FR-9 | Preserve correction and removal behavior without presenting superseded claims as current. Exclude personal data, PHI, credentials and private provenance from public reads. | Exercise correction/removal and inspect public output for excluded fields. |

## 5. Non-goals and later stages

V1 does not create or discover new research, grade sources, host contributor model runs, subsidize breakdowns, require reviewer quorum, or require public promotion. It does not ship a reports library, chained inferences, independent-agreement scoring, federation, or peer-to-peer exchange. It does not certify adversarial multi-tenancy or publish our existing instance wholesale.

After the claims and sources library, grow the inferences library, then reports. Owner point 10 names later scoring for independently reached claims, proposed edits, chained inferences, citation links, federation and peer-to-peer sharing. These need their own design work. Reviewer quorum and promotion belong to the later stage when net-new findings begin. Running breakdowns ourselves is a later, possibly paid option. None of these is a v1 launch dependency.

## 6. Current truth and required build work

This table carries forward [spec §8](../../design-specs/research-foundry-public-knowledge-platform.md#8-current-truth-at-the-baseline), including its 2026-11-13 reader measurements. These are inherited evidence, not fresh measurements of personal data in this docs leg. Repository readiness does not establish public deployment.

| Documented gap | Required work and check |
| --- | --- |
| 0 strict assertions live; default run-local claims are loose summaries | Fill the strict layer by rerunning core sources; report accepted exact-quote assertions separately from run claims. |
| About 5% of sources have stored edition bytes | Acquire permitted source bytes and bind exact editions before quote checking; measure coverage and failures. |
| 687 of 750 cards marked personal, pending validation | Validate labels and public eligibility; do not bulk-publish or infer safety from an expectation that labels are defaults. |
| No run-less single-source ingest | Add idempotent single-source intake without requiring a full research run; preserve producing process provenance. |
| Model/process capture is thin | Capture actual per-record model steps and process details in the toolkit and public record; distinguish declarations from verified checks. |
| No portable single-claim packet | Define and implement a portable record carrying source identity, quote anchors and process provenance for toolkit submission and agent pull. |
| No signing or attestation | Define the integrity/trust contract for portable records and implement signing if it is needed; do not label unsigned records attested or claim a verified model identity. Signing policy is not owner-approved. |
| Local MCP assertion read denies; anonymous-safe public projection not established | Build and verify an open agent read path exposing the complete permitted record. Reuse HTTP or MCP only after checking its actual access behavior. |
| Public hosting unproven; tenant certification remains trusted-cohort only | Establish a public deployment receipt and safe data separation. Keep the public instance separate initially; public reads cannot expose private data. |

## 7. Success metrics and release evidence

The first product milestone is a recorded case of an outsider's agent using the library during a real task. Capture the query, retrieved claim/source references and downstream citation or use, with the user's consent and without private task content. Count repeat outside agent use as evidence of ongoing value.

Milestone 2 is an outside contributor using the open toolkit with their own model to add accepted strict records. Measure accepted/rejected submissions, exact-quote pass rates by declared model, provenance completeness and repeat contributors. A model tag alone is not verified identity.

For the seed, measure strict assertion count, stored-byte coverage, eligible sources per chosen domain, yield, cost and throughput. For operation, measure read latency, retrieval failures, correction/removal propagation and public-data leaks. Pilot SLOs, budgets, stop conditions and numeric targets still need a measured baseline and owner review; the old showcase's promotion counts and reviewer backlog are not v1 success criteria.

Release evidence must demonstrate FR-1 through FR-9, open outside-agent retrieval, the strict quote rejection case, rights-compliant display and private-data exclusion. No implementation tests or public deployment are claimed by this PRD rewrite.

## 8. Decided design decisions

The owner decisions are recorded in node_01KZ755YBS3A99PVJBC53R4DTY and the [decision record](../../design-specs/public-knowledge-platform-open-questions-2026-11-13.md). They set direction, not implementation or launch approval.

| ID | Decision | Consequence | Considered |
| --- | --- | --- | --- |
| D-open-1 | B — Research flows through the toolkit; direct open access stays. | The toolkit checks the library and supports processing missing sources with a contributor's model; agents can also read directly and search elsewhere. | Plain access alone; equally supported separate workflows. |
| D-open-2 | D — Common floor of short claim quotes and a per-source cap, with source-license exceptions. | Apply limits and permitted exceptions only after legal review establishes a lawful basis and limits. | Per-source review, location-based terms, clear-license-only display. |
| D-open-3 | C — Seed a small mix of agent-tools/software-engineering and research-methods domains. | Select eligible core sources across both areas for seeding and comparison. | Either domain alone. |
| D-open-4 | C — Separate now, connect later. | Keep the public and private libraries separate for launch; portable records can support a future connection from a user’s local instance to the public library, while users retain a private local library and may connect to other libraries. | Explicit transfers only; make the local instance an initial peer. |
| D-open-5 | A — Compare models on seed sources, then publish pass rates by declared model. | Measure comparable breakdown quality and report declared-model outcomes without asserting verified identity. | Wait for contributions alone; choose a minimum model in advance. |

**Open launch prerequisite — legal review (owner):** The owner must arrange a separate future legal review and receive its findings before public launch. It must assess the proposed common floor, per-source cap and license exceptions; neither this decision nor this document commissions the review or treats it as complete.

### Disposition of the older six headline questions

The node snapshot and July spec retain six historical questions. First domain maps to D-open-3; displayable source components is partly settled by public claim quotes, with the chosen rights rule subject to legal review. Promotion/correction quorum is deferred to net-new findings because v1 uses a deterministic thin door; correction/removal still need implementation. Pilot thresholds are deferred until seed and outside-use measurements exist (§7), without inventing targets. Hosted provider allowlist/BYOK is superseded for v1 by contributor-run models; model comparison follows D-open-5. Federation's trigger is deferred because federation is a later stage, with the initial separation and later connection decided in D-open-4. These dispositions preserve the five decisions above and the separate legal prerequisite.

## 9. Risks and dependencies

Public quotes need a lawful rights rule; The desired visibility is not legal clearance. Source bytes and exact quote matches establish fidelity to the source, not factual correctness. Declared model names and repeated extraction can be misleading, so show their limits. Legacy personal labels and thin provenance prevent treating the existing library as ready to publish. A separate public data boundary must not inherit trusted-cohort tenancy claims. Consult the governing security and rights contracts during implementation; this scope change does not waive them.
