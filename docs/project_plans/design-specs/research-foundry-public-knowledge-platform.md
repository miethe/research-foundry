---
schema_version: 2
doc_type: design_spec
title: "Research Foundry Public Knowledge Platform"
description: >-
  Product-direction authority for evolving Research Foundry from a public
  repository and trusted-cohort self-hosted tool into a governed public
  evidence and assertion platform.
status: draft
maturity: shaping
created: 2026-07-26
updated: 2026-07-26
feature_slug: research-foundry-public-knowledge-platform
feature_version: v1
owner: nick
priority: high
risk_level: high
truth_status: partially_verified
baseline_commit: d71a261d85cf6eb05f12f250c244e7ef253b759e
problem_statement: >-
  Research Foundry has a substantial evidence, assertion, catalog, rights, and
  trusted-cohort multi-user substrate, but it does not yet have one canonical
  product contract for a public knowledge catalog, safe contribution,
  provider policy, hosted scale, or federation.
open_questions:
  - "Which first domain has sufficient demand, source availability, reviewer capacity, and rights-clearable material?"
  - "Which source components may the public instance display: metadata, assertion text, bounded passage snippets, or source links only?"
  - "Who may promote, correct, retract, tombstone, or clear rights, and what review quorum applies?"
  - "What exact pilot thresholds establish product value, safe operability, and a reason to scale?"
  - "Which providers and models are allowlisted, and does an invited beta support BYOK?"
  - "What measured trigger justifies federation instead of one canonical service with governed domain cells?"
explored_alternatives:
  - "Launch unrestricted public research execution first: rejected because tenant certification, durable jobs, provider isolation, budgets, and public-promotion controls are incomplete."
  - "Operate unrelated domain-specific instances: rejected as the default because it fragments source and assertion identity, provenance, correction, and cross-domain discovery."
  - "Treat one generated report as the primary product: rejected because reports are views; the reusable source-bound evidence and assertion history are the compounding substrate."
  - "Permit arbitrary BYOM in the public execution plane: rejected for the initial platform because endpoint trust, data egress, reproducibility, and prompt-injection boundaries are unresolved."
  - "Use one canonical spine with governed domain cells and stage public contribution behind review: retained shaping baseline."
prd_ref: null
related_documents:
  - intents/intent.md
  - docs/user/assertion-ledger.md
  - docs/dev/architecture/assertion-ledger-contract.md
  - docs/dev/architecture/adr-rights-entity-model.md
  - docs/dev/architecture/adr-runs-workspace-isolation.md
  - docs/project_plans/design-specs/reusable-assertion-ledger-public-rights-promotion.md
  - docs/project_plans/design-specs/reusable-assertion-ledger-shared-indexes.md
  - docs/project_plans/design-specs/public-multiuser-release-handoff-v1.md
  - docs/project_plans/design-specs/rbac-db-postgres-migration.md
  - docs/project_plans/design-specs/oidc-adapter-live-implementation.md
  - docs/project_plans/design-specs/service-account-fine-grained-scoping.md
  - docs/project_plans/design-specs/research-foundry-knowledge-mcp-remote-transport.md
  - docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
  - docs/project_plans/reports/audits/di-1-full-surface-scoping-audit.md
  - .claude/reports/research-foundry-public-release-program-status-2026-07-26/report.json
---

# Research Foundry Public Knowledge Platform

## 1. Purpose and decision posture

This document is the product-direction authority for a possible public Research
Foundry knowledge platform. It is self-contained enough for an external agent
without repository access to understand the product, its ontology, its current
truth, the recommended public topology, and the decisions still required.

The proposal is a **conditional go** for a bounded public program:

1. formalize the open-source release;
2. publish a curated, read-only, rights-cleared showcase;
3. qualify an invited trusted-cohort beta;
4. add private ingestion and controlled execution;
5. add reviewed public contribution only after promotion and removal controls;
6. consider federation only after the shared contracts are proven.

It is **not** approval for unrestricted public model execution, adversarial
shared-store multi-tenancy, open contribution, public promotion of private
evidence, clinical use, or “all research” scale.

## 2. Authority and conflict rules

Use this precedence when statements conflict:

1. Secrets, sensitivity, no-PHI, human-only rights decisions, and accepted
   security/governance ADR invariants are hard constraints.
2. Git, runtime behavior, schemas, tests, current validation receipts, and
   deployment receipts establish what is implemented and verified.
3. This document governs cross-cutting **public-platform product direction**.
4. Linked child specs govern their bounded implementation contracts where they
   do not conflict with this document or a higher authority.
5. PRDs, implementation plans, handoffs, mockups, and historical reports
   explain intent and history but do not prove current behavior.

Additional rules:

- The baseline is commit
  `d71a261d85cf6eb05f12f250c244e7ef253b759e` on 2026-07-26.
- This document's truth status is `partially_verified`.
- A target-state statement is not evidence that the target exists.
- A repository-ready or fixture-verified capability is not owner-data,
  production, public-deployment, market-demand, or clinical evidence.
- Where this document links to a bounded child authority, use the child for
  field-level and implementation detail rather than duplicating it here.
- The superseded public multi-user handoff remains useful for historical
  screenshots, mockups, and interface rationale, not product-direction
  authority.

## 3. What Research Foundry is

Research Foundry is a Markdown/YAML-first, evidence-first research control
plane. It turns a raw idea into a governed research run and a portable evidence
bundle:

```text
capture → triage → plan → governance preflight
→ discover or ingest → source cards → extract evidence
→ claim-map → contradictions and gaps → synthesize
→ deterministic verification → human/council review when required
→ evidence bundle → optional governed writeback
```

The core invariant is:

> Every material statement in a report must resolve to a run-local claim-ledger
> entry backed by source evidence, or be explicitly labeled as inference,
> speculation, mixed evidence, contradiction, or unresolved.

The claim ledger and deterministic verifier, not narrative fluency or a
model's self-assessment, decide whether a report passes the traceability gate.
Traceability does not itself prove that a source is correct, complete,
unbiased, current, or appropriate for a decision.

Research Foundry currently spans four related surfaces:

- the `rf` CLI and file-backed core engine;
- agent and external-system adapters;
- HTTP and local MCP/read interfaces;
- the runs-viewer web application.

They share one evidence-first center. They must not become separate products
with incompatible claim, provenance, rights, or lifecycle semantics.

## 4. Why it may be valuable

Generic literature search and generated reports are increasingly available.
Research Foundry's proposed differentiation is the durable layer after search:
a compounding catalog of reviewed, passage-bound assertion versions with
source identity, evaluation, lifecycle, rights posture, contradictions, and
downstream-use provenance.

Potential value by user:

- **Researchers:** inspect support, gaps, and contradictions instead of
  repeating source review for every report.
- **Reviewers:** see exactly what passage and edition supports a statement and
  what changed after correction or retraction.
- **Agents:** retrieve structured evidence with eligibility, rights, freshness,
  and provenance rather than treating prose snippets as timeless facts.
- **Teams:** reuse qualified evidence across runs while retaining workspace and
  sensitivity boundaries.
- **Domain programs:** apply domain-specific vocabulary and evaluation without
  forking global evidence identity.
- **Platform operators:** enforce provider, cost, rights, sensitivity, and
  publication policy at runtime.

This is a market hypothesis, not measured demand. The moat hypothesis is
reviewed assertion capital and its history, not the UI, a single model, or a
one-time report.

## 5. Actors and jobs to be done

| Actor | Job to be done | Current or target |
| --- | --- | --- |
| Operator/researcher | Turn a question into a claim-traceable, verified evidence bundle. | Current; best validated |
| Trusted collaborator | Author and review within a workspace without host filesystem access. | Current substrate; trusted cohort |
| Reader/reviewer | Inspect reports, claims, citations, contradictions, and provenance. | Current read surfaces |
| Agent/system integrator | Search or fetch governed evidence through CLI, HTTP, interchange, or MCP. | Mixed; local and planned surfaces |
| Platform administrator | Configure identity, RBAC, isolation, providers, limits, audit, and operations. | Current substrate; hosted gaps |
| Public reader | Search and inspect only publicly promoted material. | Target |
| Contributor | Submit sources or packets into private staging and track disposition. | Target |
| Domain reviewer/curator | Apply domain evidence standards before promotion or reuse. | Target |
| Rights reviewer/owner | Make attributable rights, license, and publication decisions. | Target |
| Security/incident operator | Investigate abuse, revoke access, and prove removal boundaries. | Target |

Core jobs:

1. Produce evidence-first research rather than an unstructured chat answer.
2. Receive a deterministic traceability verdict.
3. Reuse previously qualified assertions without hiding provenance or
   lifecycle changes.
4. Browse evidence without keeping a research worker alive.
5. Share results without granting workspace or filesystem access.
6. Enforce governance as code instead of an optional checklist.
7. Extend providers and domain behavior without vendor lock-in.
8. Correct, retract, and remove public material without erasing history.

## 6. Non-goals

- A general-purpose chatbot or universal agent runtime.
- A source of unquestionable or timeless facts.
- Automatic public publication from model output.
- Automatic legal, rights, clinical, or domain attestation.
- A near-term unrestricted public multi-tenant SaaS.
- Bulk publication of private workspaces or full copyrighted source content.
- Replacement of MeatyWiki, SkillMeat, CCDash, or domain applications.
- A claim that clinical or other high-stakes outputs are validated for use.
- Federation before local identity, lifecycle, promotion, and removal work.
- Premature infrastructure for unmeasured “all research” scale.

## 7. Ontology: run-local evidence and reusable assertions

### 7.1 Run-local research authority

A research run is the authoritative context for the artifacts it produced:

- `research_intent`: the governed question, audience, scope, and constraints;
- `source_card`: source provenance, access, sensitivity, and run metadata;
- `extraction/evidence`: source-derived material used by claim mapping;
- `run claim`: a statement authoritative within the run's claim ledger;
- `contradiction`: an explicit conflict among claims or sources;
- `report`: a narrative constrained to ledger claims or labeled reasoning;
- `verification`: the deterministic traceability result;
- `evidence_bundle`: the portable run package and provenance graph;
- `writeback receipt`: an attributable record of an authorized downstream act.

Run-level statuses include:

- `supported`
- `mixed`
- `contradicted`
- `inference`
- `speculation`
- `unresolved`
- `unsupported` — a failing state for an unlabeled material statement

Existing run-local Markdown/YAML claim ledgers remain canonical for their runs.
Missing durable references mean legacy or assertion-only semantics; readers
must never invent a persistent link.

### 7.2 Reusable assertion authority

The reusable layer is separate:

| Object | Identity and meaning |
| --- | --- |
| `source_edition` | Immutable, content-addressed rendition of source material. |
| `passage` | Immutable selection bound to an edition, selector, text hashes, and normalization provenance. |
| `source_assertion` | Immutable assertion bound to exactly one edition and passage plus material qualifiers. |
| `assertion_evaluation` | Immutable grounding or review decision for one assertion version. |
| `assertion_lifecycle_event` | Ordered event that changes current eligibility. |
| `canonical_claim` | Optional, versioned grouping of assertion versions; never source evidence itself. |
| `inference_record` | Derived, versioned reasoning over assertions; never represented as a source assertion. |

Corrections create new editions, passages, assertions, evaluations, or events.
They do not overwrite the record used by an earlier report. `stale`,
`invalidated`, and `tombstoned` states block or change current reuse while
preserving authorized historical resolution.

The required mental model is:

> Immutable evidence history does not make truth state immutable.

Confidence, evaluation, contradiction, correction, retraction, freshness,
rights eligibility, and public visibility evolve through new governed records
and pointers.

### 7.3 Canonical claims

Canonical claims are optional mutable groupings:

- they reference exact source assertion IDs and versions;
- they never overwrite or replace source assertions;
- they require versioned proposal, review, activation, split, supersession, and
  rollback behavior;
- they must not make private material public by association;
- domain-specific groupings should be namespaced where semantics differ.

The platform must remain useful in assertion-only mode.

## 8. Current truth at the baseline

| Capability | Truth at baseline |
| --- | --- |
| Source and docs | Public repository and documentation; no semantic product release was found. |
| Core research loop | Implemented as a file-backed CLI and deterministic validation pipeline. |
| Web/API runtime | LAN viewer and API were healthy during the status review, but the deployed revision was not proven. |
| Public hosted app | Not deployed; no public hosting receipt or manifest. |
| Evidence foundation | Run provenance, reusable assertion contracts/registry, rights records, catalog, governed reuse seams, and term indexing are merged. |
| Assertion rollout | Repository-owned readiness is implemented; owner-authorized private real-data qualification was not executed. Flags remain default-off. |
| Multi-user substrate | Deployment presets, local/Clerk auth, RBAC, PATs/service accounts, workspace fields, and public-read visibility are merged. |
| Tenant certification | Trusted-cohort only. DF-004 engineering landed, but DI-1 delta re-audit and human Mode-D signoff remain open; catalog import/stat seams remain. |
| Term indexing | Merged and fixture-verified; private pediatric corpus and wide-screen runtime qualification were unavailable. |
| External interchange | Planned and scaffolded; the first contract-freeze tasks are not complete. |
| Hosted job plane | Job API and credential firewall exist; production runner, durable queue, key vault, quotas, billing, and multi-worker state do not. |
| Public promotion | Deferred; no implemented public rights-promotion/removal workflow. |
| Hosted Knowledge MCP | Local/schema work only; canonical remote HTTPS/OAuth transport is deferred. |
| Hosted scale | File-canonical, SQLite/FTS, full-projection search, Python paging, and process-local job/limit state support only a bounded single-host pilot. |
| Federation | Deferred. |

These labels must not be collapsed into “public-ready.”

## 9. Target topology: one spine, governed domain cells

### 9.1 Canonical public spine

Operate one logical public source/assertion spine responsible for:

- public source identity and canonical resource URLs;
- immutable source editions and passage selectors;
- immutable assertion identity and version references;
- evaluation and review records;
- correction, contradiction, retraction, and tombstone lifecycle;
- public rights eligibility and promotion/removal receipts;
- cross-domain provenance and discovery;
- shared interchange identifiers and schemas;
- downstream-use and cache/index reconciliation.

The spine is not a global truth oracle. It is the shared identity, provenance,
and lifecycle backbone.

### 9.2 Governed domain cells

Each domain cell owns:

- controlled vocabulary, aliases, and domain taxonomy;
- inclusion and exclusion policy;
- source hierarchy and acceptable evidence types;
- evaluation rubrics and confidence language;
- reviewer qualifications, quorum, and conflicts policy;
- freshness and refresh rules;
- domain contradiction and uncertainty presentation;
- filters, views, reports, and application-specific output.

Domain cells may add evaluations or propose namespaced groupings. They may not
fork global edition/passage/assertion identity or weaken rights, sensitivity,
workspace, lifecycle, or removal constraints.

### 9.3 Why not independent instances first

Independent instances are useful for private deployment and hard isolation,
but they should not be the default public knowledge architecture because they
fragment:

- source deduplication;
- assertion identity;
- correction and retraction propagation;
- cross-domain discovery;
- rights and lifecycle policy;
- agent-facing retrieval contracts.

One canonical service with policy-separated domain cells preserves future
cross-domain value. Physical partitioning may still be used for security,
residency, performance, or domain operations.

## 10. Relationship to private and workspace evidence

Markdown/YAML evidence in a private run remains canonical for that run. A
public catalog is a governed projection and registry, not an automatic union of
workspace files.

Required boundaries:

- No background sweep promotes private or workspace evidence.
- Public promotion is an explicit, attributable action on exact versions.
- A public record contains only approved public fields and handles.
- Private paths, workspace IDs, secret locators, raw hashes that act as access
  handles, hidden counts, and unauthorized source text are not exposed.
- A public derivative cannot reveal private provenance through a canonical
  grouping.
- Public removal blocks current reads and reuse before asynchronous index,
  cache, export, and downstream reconciliation.
- Historical private evidence remains resolvable only in its authorized run
  context.
- Databases and indexes remain rebuildable projections; the portable evidence
  and promotion/removal receipts remain durable contracts.

## 11. Proposed public-instance contract

### 11.1 Initial product

The first public instance is a curated, read-only evidence and assertion
library. It provides:

- search and browse over promoted sources, assertions, evaluations, reports,
  contradictions, and lifecycle state;
- direct navigation from a public statement to its allowed source citation,
  edition, passage context, review, rights posture, and use history;
- visible status, freshness, caveat, correction, and retraction language;
- stable public identifiers and canonical URLs;
- read-only agent access only after the remote access profile is qualified.

It does not initially provide:

- anonymous or self-service model execution;
- direct-to-public imports;
- arbitrary BYOM;
- public publication of private source passages;
- self-service billing;
- federation.

### 11.2 Trust zones

| Zone | Contents | Rule |
| --- | --- | --- |
| Z0 Public read | Promoted records and approved public fields | Anonymous/read-scoped, rate-limited, no hidden membership signals |
| Z1 Contributor workspace | User submissions, drafts, review state | Authenticated and workspace-scoped; never public by default |
| Z2 Quarantine/execution | Fetched files, URLs, external packets, model outputs | Untrusted input; isolated acquisition and processing |
| Z3 Governed registry | Edition/passage/assertion/lifecycle, review, rights, promotion receipts | Service-controlled writes and auditable transitions |
| Z4 Operations | Identity, secrets, provider references, quotas, billing, incident controls | Least privilege; never exposed to jobs or public reads |
| Z5 External providers | Search, model, storage, or identity services | Explicit egress, allowlist, contract, timeout, and audit policy |

No ambient operator credential or client-supplied workspace identity may cross
these zones as authority.

## 12. Contribution, promotion, correction, and removal

```text
submit URL/file/packet
→ private workspace receipt
→ quarantine and hostile-input checks
→ acquisition and immutable edition creation
→ sensitivity and rights triage
→ passage selection and source-assertion candidates
→ deterministic schema/identity/traceability checks
→ assertion evaluation and contradiction review
→ domain reviewer decision
→ attributable rights/publication decision
→ exact-version public promotion
→ indexed public read
→ ongoing freshness, correction, retraction, and removal
```

Rules:

- Models and agents propose; they do not promote.
- Promotion binds the exact source edition, passage, assertion version,
  jurisdiction, license scope, intended use, and decision actor.
- Missing, unknown, stale, disputed, expired, or revoked rights fail closed.
- Corrected material creates successors and lifecycle events.
- Invalidated or tombstoned material is blocked synchronously from reuse.
- Public caches, snippets, exports, and writebacks must have a bounded removal
  and tombstone path.
- Rejected contributions do not disclose private reviewer notes or hidden
  catalog membership.
- Public contribution begins only after a synthetic promotion/revocation
  prototype, legal/privacy review, security review, accessibility review,
  deletion SLA, and incident workflow are approved.

## 13. Roles and decision rights

| Role | May | May not |
| --- | --- | --- |
| Public reader | Read promoted public records | Infer access to hidden records |
| Contributor | Submit and inspect own staged work | Publish or clear rights |
| Research operator | Run authorized private research | Override governance or workspace policy |
| Domain reviewer | Evaluate evidence under a domain rubric | Grant source rights unless separately authorized |
| Public curator | Recommend promotion and presentation | Self-approve required independent gates |
| Rights owner/counsel | Write attributable rights decisions | Delegate clearance to a model |
| Workspace admin | Manage workspace membership and allowed execution | Read another workspace by default |
| Platform security/admin | Operate identity, incidents, revocation, and infrastructure | Use public jobs as an ambient privileged path |
| Agent/model | Propose evidence, assertions, evaluations, and reports | Write `CLEARED_*`, attest, promote, or tombstone as a human authority |

Separation of duties and quorum remain open product decisions. The current
rights substrate enforces human-only values by exclusion; a positive
rights-owner/counsel role and workflow are still a child-spec responsibility.

## 14. Governance, rights, privacy, and security

Minimum invariants:

1. Run governance preflight before discovery, privileged processing, or
   writeback.
2. Fail closed on incompatible key, model, sensitivity, workspace, rights, or
   output target.
3. Treat imported packets, web content, files, and model output as untrusted.
4. Keep authoritative rights records separate from non-authoritative mirrors.
5. Reserve `CLEARED_*`, counsel approval, and attested synthesis for
   attributable humans.
6. Never infer public rights from metadata, open-access labels, citation,
   canonical grouping, or model output.
7. Bind public decisions to exact versions and preserve revocation/expiry.
8. Publish no PHI in the public alpha.
9. Do not ingest PHI into a public-instance execution zone; high-sensitivity
   research requires a separately approved private deployment and policy.
10. Use hidden-equals-missing behavior for unauthorized workspace reads.
11. Public readability never grants mutation or writeback authority.
12. Store provider secrets only through encrypted, server-resolved references;
    never in job bodies, logs, artifacts, or browser storage.
13. Bound request sizes, acquisition, redirects, content types, timeouts,
    retries, and SSRF behavior.
14. Record privacy-safe audit events without persisting raw secrets, hidden
    identifiers, source text, or queries beyond approved retention.
15. Obtain formal DI-1 re-audit and human Mode-D approval before adversarial
    shared-store tenancy claims.

## 15. BYOK and BYOM policy

### 15.1 Current truth

The code has a job credential seam, but no production SDK runner, hosted tenant
key vault, durable worker enforcement, provider budget, quota, or billing
system. This is not hosted BYOK support.

### 15.2 Staged policy

- **Curated showcase:** platform-controlled, pinned, allowlisted models only;
  public readers execute nothing.
- **Invited private beta:** optionally allow BYOK only through encrypted,
  server-resolved tenant key references and an approved provider allowlist.
- **Public contribution:** execution remains private/staged; provider output
  cannot publish directly.
- **Arbitrary BYOM:** self-hosted or isolated/quarantined only until endpoint
  identity, transport, data egress, availability, reproducibility,
  prompt-injection, and incident boundaries are proven.

Every model-assisted artifact must record enough provider, model-version,
prompt/extraction-contract, and evaluation provenance to support reproduction
and later qualification. Deterministic validation and human publication gates
apply regardless of who supplies the model or key.

## 16. Economics and market validation

### 16.1 Planning economics

The delivery review contains an illustrative model-only range of approximately
`$0.13–$2.16` per article depending on length, model mix, retries, and review
passes. This is not measured Research Foundry unit economics and excludes the
likely limiting costs:

- source verification;
- passage and assertion review;
- rights adjudication;
- domain review;
- contradiction resolution;
- correction and retraction handling;
- public-promotion operations;
- abuse, support, and incident response.

BYOK may shift model spend but does not remove governance, review, platform, or
support cost.

### 16.2 Pilot metrics

Measure at minimum:

- model tokens and cost per submitted, accepted, and promoted source;
- assertions proposed, accepted, corrected, rejected, and promoted per source;
- human review minutes per accepted and promoted assertion;
- rights-review time and clearance/rejection distribution;
- duplicate detection and evidence reuse across runs;
- questions partially or fully satisfied from existing qualified assertions;
- contradiction, staleness, correction, retraction, and removal rates;
- search latency, index growth, storage, and rebuild time;
- job queue latency, execution time, retries, cancellation, and failure;
- public reads, repeat users, agent retrievals, and downstream uses;
- reviewer backlog, age, throughput, and agreement;
- cost per promoted assertion and cost avoided through verified reuse.

### 16.3 Market hypotheses to test

- A reviewed assertion registry is more valuable than another report generator
  for domains that repeatedly revisit the same evidence.
- Agents and teams will use passage/lifecycle/rights metadata when it is
  available, rather than defaulting to unqualified snippets.
- A narrow, high-value domain can seed reusable assertion capital faster and
  more credibly than a broad undifferentiated catalog.
- Transparent contradictions and correction history improve trust rather than
  confusing users.
- Curated read access can demonstrate value before public execution exists.

Validation questions:

1. Who has the recurring research pain: individual researchers, domain teams,
   publishers, evidence-review groups, or agent builders?
2. Who contributes, who reviews, and who pays for each?
3. Does reuse materially reduce review time or improve traceability?
4. What public material can be published lawfully and usefully?
5. Do users retrieve assertions directly, or only consume reports and APIs?
6. What level of review creates willingness to rely on the catalog?
7. Is the sustainable model hosted subscriptions, private instances, sponsored
   domain cells, usage-based execution, API access, or a public-good core with
   paid operations?

No business model should be selected before these are measured.

## 17. Scale model and migration triggers

Treat scale as four separate dimensions:

| Dimension | Current shape | Required evidence before migration |
| --- | --- | --- |
| Corpus | File-canonical artifacts, SQLite/FTS projections, full-projection assertion search | Measured corpus size, rebuild time, write contention, storage, and search SLO |
| Query/read | Single-host API and Python paging | Measured concurrency, latency, cache behavior, and isolation |
| Research jobs | Process-local registry/limits; production spawn blocked | Durable retry/idempotency/cancellation needs and multi-worker load |
| Review/governance | Human workflows are incomplete | Measured backlog, review time, agreement, and removal SLA |

Migration triggers:

- move hot catalog/query state to durable relational storage when measured
  contention, latency, rebuild windows, or multi-node needs exceed the approved
  pilot SLO;
- add object storage when source editions, permitted snapshots, exports, and
  backup/restore requirements cannot be operated safely on one host;
- add a durable queue before more than one worker, crash recovery, retry,
  cancellation, scheduled refresh, or production provider execution;
- replace process-local rate limits and registries before horizontal scale;
- add incremental indexing when full projection rebuilds exceed the approved
  recovery or freshness window;
- add shared observability, backups, restore drills, cost attribution, and
  incident controls before invited external execution;
- do not use infrastructure migration as evidence of market demand.

Markdown/YAML evidence and signed receipts remain portable durable contracts
even if a relational/object store becomes the hot operational plane.

## 18. Staged release

| Stage | Scope | Exit gate |
| --- | --- | --- |
| 1. Formal OSS release | Contribution/security policy, reproducible install, examples, versioning, tags/releases | Clean-room setup and deterministic demo verification |
| 2. Curated read-only showcase | Small rights-cleared corpus, reports, assertions, provenance, lifecycle UX | No PHI; rights, review, correction, removal, accessibility, and canonical URL review |
| 3. Invited trusted-cohort beta | Authenticated workspaces and controlled authoring | DI-1 delta re-audit, human Mode-D signoff, catalog seam closure, recovery and audit drills |
| 4. Private ingestion/execution | Quarantined imports, durable jobs, quotas, allowlisted providers, optional BYOK | Queue, encrypted key references, budgets, backups, abuse and incident controls |
| 5. Reviewed public contribution | Private staging followed by domain and rights promotion | Exact-version promotion/revocation, deletion SLA, cache/export reconciliation, independent security/privacy review |
| 6. Federation | Governed nodes exchange eligible records | Cross-node identity, interchange, shared-index policy, correction/retraction/tombstone propagation, conformance tests |

Each stage is independently valuable and does not imply approval for the next.

## 19. Federation prerequisites

Federation is a later topology, not a near-term escape from scale work. Require:

- stable canonical public identifiers and URLs;
- an implemented hostile-input-safe interchange packet;
- compatible source-edition, passage, assertion, evaluation, and inference
  semantics;
- versioned promotion, rights, sensitivity, and visibility representation;
- cross-node correction, retraction, tombstone, and removal propagation;
- collision, merge, split, rollback, and provenance rules;
- shared-index inclusion and cache invalidation contracts;
- authentication, node trust, rate-limit, abuse, and revocation policy;
- conformance fixtures and two-node failure testing;
- explicit rules for domain-local evaluations and canonical groupings;
- measured need that one canonical service plus governed cells cannot meet.

Private instances may export bounded packets before federation, but a packet
must not grant public eligibility or bypass the receiving node's policy.

## 20. Decisions required before promotion to PRD

1. Select the first public domain and write its inclusion, evidence, freshness,
   reviewer, rights, and no-PHI policy.
2. Define the public display unit for metadata, assertions, passages, and
   source links.
3. Define positive curator, domain-reviewer, rights-owner, security, and
   incident roles plus separation of duties.
4. Approve the public promotion, correction, revocation, deletion, and
   tombstone contract.
5. Close or explicitly scope DI-1 and the catalog import/stat workspace seams.
6. Define pilot SLOs, success metrics, failure thresholds, budget, and stop
   conditions.
7. Decide the provider allowlist and whether invited beta includes BYOK.
8. Define the hosted job, secret, quota, cost-attribution, and abuse boundary.
9. Approve canonical public URL and remote read/API/MCP scope.
10. Establish measured relational/object storage and incremental-index
    migration triggers.
11. Decide whether canonical claim groupings are global, domain-namespaced, or
    only presentation views.
12. Define the threshold and business reason for federation.

## 21. Child-spec map

This document sets direction. These bounded authorities retain detail:

| Concern | Child authority | Relationship |
| --- | --- | --- |
| Assertion identity and lifecycle | [Assertion ledger contract](../../dev/architecture/assertion-ledger-contract.md) | Binding ontology and invariants |
| User-facing ledger behavior | [Assertion ledger guide](../../user/assertion-ledger.md) | Current private/default-off boundary |
| Rights and evidence taxonomy | [Rights entity ADR](../../dev/architecture/adr-rights-entity-model.md) | Accepted entity and human-only write ceiling |
| Public rights promotion | [Public rights and promotion](reusable-assertion-ledger-public-rights-promotion.md) | Deferred implementation boundary and deal killers |
| Shared indexes | [Shared indexes](reusable-assertion-ledger-shared-indexes.md) | Deferred shared retrieval design |
| Run/workspace/public visibility | [Workspace isolation ADR](../../dev/architecture/adr-runs-workspace-isolation.md) | Accepted ownership/read semantics; certification still separate |
| Full isolation audit | [DI-1 scoping audit](../reports/audits/di-1-full-surface-scoping-audit.md) | Historical trusted-cohort audit; requires delta re-audit |
| External packets | [External report interchange](../implementation_plans/enhancements/external-research-report-interchange-v1.md) | Planned hostile-input-safe interchange |
| Hosted relational storage | [Postgres migration](rbac-db-postgres-migration.md) | Deferred migration design |
| Enterprise identity | [Live OIDC adapter](oidc-adapter-live-implementation.md) | Deferred live OIDC contract |
| Service-account scopes | [Fine-grained service accounts](service-account-fine-grained-scoping.md) | Deferred fine-grained capability design |
| Remote knowledge access | [Knowledge MCP remote transport](research-foundry-knowledge-mcp-remote-transport.md) | Deferred HTTPS/OAuth transport |
| Historical public UI direction | [Public multi-user handoff](public-multiuser-release-handoff-v1.md) | Superseded for product direction; assets/rationale retained |
| Program truth snapshot | [Public release status](../../../.claude/reports/research-foundry-public-release-program-status-2026-07-26/report.json) | Point-in-time evidence and handoffs |

Before implementation, create focused child specs or PRDs for any unresolved
topic rather than expanding this document past the 800-line planning limit.

## 22. External-agent caveat checklist

An external agent must verify that any proposal or summary:

- names the baseline date, commit, and `partially_verified` truth status;
- separates implemented, merged, fixture-verified, owner-data-not-executed,
  deferred, recommended, and market-hypothesis statements;
- distinguishes run-local claims from reusable source assertions;
- keeps inference separate from source evidence;
- treats canonical claims as optional, versioned groupings;
- preserves immutable history plus evolving evaluation and lifecycle state;
- does not equate citation traceability with factual correctness;
- does not call an assertion a timeless fact;
- does not infer rights or public eligibility;
- requires attributable human rights and promotion decisions;
- includes correction, retraction, removal, and tombstone behavior;
- excludes PHI and private provenance from the public product;
- preserves workspace ownership and hidden-equals-missing behavior;
- does not claim adversarial tenancy before DI-1 and Mode-D closure;
- does not claim hosted BYOK, arbitrary BYOM, remote MCP, durable jobs, or
  public deployment from existing seams;
- labels the model-cost range illustrative and incomplete;
- separates corpus, query, job, and reviewer scale;
- treats the market and moat statements as hypotheses;
- names the first-domain scope, reviewer capacity, and legal boundary;
- defines measurable pilot success, failure, budget, and stop conditions;
- preserves the staged release order;
- does not skip directly to open contribution or federation;
- follows the child authority for bounded implementation detail;
- asks for current runtime evidence when the baseline may have changed.

## 23. Promotion criteria for this design spec

Move `maturity` from `shaping` to `ready` only when:

- the first domain and public display boundary are selected;
- public promotion/removal and positive human roles are approved;
- DI-1 disposition and hosted trust boundary are explicit;
- pilot metrics, SLOs, budget, and stop conditions are measurable;
- provider/BYOK policy is selected;
- child-spec gaps have owners and promotion gates;
- legal/privacy, security, domain, accessibility, and operations reviewers agree
  that a bounded PRD can be written without implying broader readiness.

Until then, this document is a coherent direction and decision ledger, not an
implementation authorization.
