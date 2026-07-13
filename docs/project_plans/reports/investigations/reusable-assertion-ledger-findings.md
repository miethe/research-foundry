---
schema_version: 2
doc_type: report
report_category: investigation
title: "Reusable Assertion Ledger — Feasibility and Product Findings"
status: accepted
source: agent
created: 2026-07-12
updated: 2026-07-12
feature_slug: reusable-assertion-ledger
description: >
  Feasibility, product-value, prior-art, architecture, risk, and implementation
  findings for extending Research Foundry from run-local claim provenance into
  a private-first, reusable assertion ledger that compounds across research runs.
prd_ref: docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
promoted_to:
  - docs/project_plans/PRDs/features/reusable-assertion-ledger-v1.md
  - docs/project_plans/implementation_plans/features/reusable-assertion-ledger-v1.md
related_documents:
  - docs/dev/architecture/rf-run-export-schema.md
  - docs/project_plans/exploration/citation-precision-recall-metrics/citation-precision-recall-metrics-charter.md
  - docs/project_plans/exploration/claim-segmentation-source-alignment/claim-segmentation-source-alignment-charter.md
  - docs/project_plans/exploration/contradiction-log-v1/contradiction-log-v1-charter.md
  - docs/project_plans/exploration/writeback-default-deny-gate/writeback-default-deny-gate-charter.md
  - docs/project_plans/SPIKEs/public-multiuser-p4p5-foundations-spike.md
  - docs/project_plans/implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md
  - docs/project_plans/implementation_plans/features/run-metadata-enrichment-v1.md
  - docs/project_plans/implementation_plans/features/runs-frontend-v1.md
tags:
  - research-foundry
  - assertions
  - claims
  - evidence
  - provenance
  - research-memory
  - knowledge-graph
---

# Reusable Assertion Ledger — Feasibility and Product Findings

## Executive finding

Research Foundry can feasibly evolve from a per-run research control plane into
a compounding evidence-memory system. The strongest near-term product is a
**private, reusable assertion ledger**: ingest a source edition once, retain its
atomic source assertions and exact passages, and let later research agents find
and reuse those assertions without repeating unchanged extraction work.

The idea is valuable enough to implement incrementally, but the public version
should not be treated as the first release. A public, multi-tenant corpus adds a
different class of obligations—rights management, tenant isolation, abuse and
poisoning response, public correction workflows, and moderation—whose cost and
risk are not justified until private reuse and extraction quality are measured.

The recommended boundary is therefore:

> Build a private reusable assertion ledger first. Treat public promotion and
> shared indexes as a later product decision gated by demonstrated reuse,
> provenance accuracy, correction propagation, rights clearance, and tenant
> isolation.

This is not a recommendation to build a universal “truth graph.” The durable
object should represent what a particular source edition asserts, with enough
context to evaluate it. Truth-like confidence emerges from provenance,
corroboration, contradiction handling, review, and freshness—not from an
extractor's confidence score alone.

## Scope and method

This investigation evaluated:

- Feasibility against the current Research Foundry services and export contract.
- Whether reusable, passage-bound assertions could reduce repeated research work.
- Competitive and standards overlap.
- The semantic model required to avoid conflating quotations, normalized claims,
  and model-generated inference.
- Private-versus-public product boundaries.
- Indicative engineering uplift, principal risks, and validation SPIKEs.

The repository findings below are based on live code and planning artifacts as
of 2026-07-12. Market capabilities are based on the vendors' or projects'
official documentation linked in this report. Uplift figures are planning ranges
and hypotheses, not measured product results.

## Current repository baseline

Research Foundry already contains most of the per-run substrate needed for this
extension:

| Existing capability | Live evidence | Reuse implication |
|---|---|---|
| Source ingestion and evidence points | [`source_cards.py`](../../../../src/research_foundry/services/source_cards.py) creates schema-valid source cards, deterministic evidence points, trust/usage metadata, and sensitivity policy. | Source cards can feed immutable source editions and passage records. |
| Run-local claim ledger | [`claim_mapping.py`](../../../../src/research_foundry/services/claim_mapping.py) maps extracted facts to claims with source-card/evidence references, confidence, report locations, and inference basis. | The claim shape is a useful migration input, but run-local IDs are not durable cross-run identity. |
| Denormalized claim graph | [`export_service.py`](../../../../src/research_foundry/services/export_service.py) resolves claims to source evidence, derives report anchors and link state, and enforces sensitivity-aware export. | The export seam can expose ledger references while preserving backward compatibility. |
| Stable viewer contract | [`rf-run-export-schema.md`](../../../dev/architecture/rf-run-export-schema.md) documents claims, resolved sources, inference lineage, dangling references, report anchors, and redaction behavior. | Existing consumers already understand a claim graph and can adopt optional persistent IDs. |
| Cross-run searchable read model | [`catalog_service.py`](../../../../src/research_foundry/services/catalog_service.py) builds a derived, rebuildable SQLite/FTS5 catalog of claims, inferences, sources, reports, and links from live exports. | Discovery can be extended without making the derived catalog canonical. |
| Relevant prior planning | The [claim segmentation and source-alignment charter](../../exploration/claim-segmentation-source-alignment/claim-segmentation-source-alignment-charter.md), [run metadata enrichment plan](../../implementation_plans/features/run-metadata-enrichment-v1.md), and [runs frontend plan](../../implementation_plans/features/runs-frontend-v1.md) establish adjacent extraction, export, and read-surface seams. | The new work should compose with these artifacts rather than duplicate them. |

The critical gap is identity and lifecycle. Current claim IDs such as `clm_001`
are local to a run. A future run cannot reliably know that a newly extracted
sentence is the same source assertion, a revised assertion from a new edition,
or merely a semantically related claim. The durable layer must add stable
identities and edition-aware provenance while leaving run artifacts usable.

### Planning evidence to consume, not reopen

Several adjacent questions already have planning or implementation evidence and
must be treated as inputs to this feature:

- The [citation precision/recall metrics charter](../../exploration/citation-precision-recall-metrics/citation-precision-recall-metrics-charter.md)
  and [claim segmentation/source-alignment charter](../../exploration/claim-segmentation-source-alignment/claim-segmentation-source-alignment-charter.md)
  already own atomicity, citation precision/recall, and sentence-level alignment.
  The assertion-identity SPIKE should consume their outputs rather than create a
  third extraction-fidelity charter.
- The [contradiction-log-v1 charter](../../exploration/contradiction-log-v1/contradiction-log-v1-charter.md)
  owns contradiction detection and temporal guards. Correction/retraction
  propagation overlaps its evidence-edge concerns but is a distinct problem:
  enumerating and invalidating every downstream use after a source edition or
  extraction changes.
- The completed [WKSP-304 implementation plan](../../implementation_plans/harden-polish/wksp-304-workspace-isolation-enforcement-v1.md)
  supplies the row-level workspace isolation baseline. Shared-index leakage still
  requires a deployment-specific test gate, but not another general workspace
  isolation SPIKE.
- The existing [writeback default-deny charter](../../exploration/writeback-default-deny-gate/writeback-default-deny-gate-charter.md)
  owns topology-aware promotion and override governance. The ledger must compose
  with that gate rather than invent a parallel writeback policy.
- Agent-job credential isolation is settled by the completed
  [P4/P5 foundations SPIKE](../../SPIKEs/public-multiuser-p4p5-foundations-spike.md).
  This feature must reuse its subprocess-per-agent-job boundary and must not
  reopen credential-isolation architecture.

## Product value

The durable ledger changes the unit of reuse from “report” or “source file” to
“passage-bound assertion.” That enables:

1. **Avoided repeat extraction.** A later agent can reuse assertions when the
   exact source edition and extraction contract remain valid.
2. **Faster evidence discovery.** Search can return individual assertions,
   supporting passages, contradictions, qualifiers, authors, reports, and runs.
3. **Audit continuity.** Reports can retain the precise assertion version and
   passage they used even after a source changes or a canonical claim is revised.
4. **Correction impact analysis.** A retraction, corrected edition, or invalidated
   extraction can enumerate affected reports and downstream writebacks.
5. **Research-gap planning.** Agents can distinguish what is already supported,
   disputed, stale, or missing before starting a new research run.
6. **Compounding private knowledge.** Internal reports and licensed sources can
   provide durable value without exposing their content to other tenants.

The value is conditional on source overlap. A corpus used once produces little
reuse benefit; recurring domains, repeated literature reviews, monitoring, and
iterative product or policy research are the strongest initial workloads.

## Semantic model: three objects that must remain distinct

### 1. Source assertion

A source assertion means: **this exact passage in this immutable source edition
states this proposition, with these qualifiers**.

It should retain:

- Source and immutable edition identifiers.
- Exact passage selectors, nearby context, and passage hash.
- Atomic assertion text plus modality, negation, population, geography,
  timeframe, intervention/exposure, outcome, and other domain qualifiers.
- Extraction contract: model, prompt/schema version, code version, timestamp,
  and evaluation/reviewer state.
- Rights, sensitivity, tenant, retention, and allowed-use metadata.

A source assertion is never silently rewritten to match another source.

### 2. Canonical claim

A canonical claim is a **versioned semantic concept** used to group comparable
source assertions for discovery and synthesis. It is not itself evidence.

Grouping may propose that assertions support, contradict, qualify, replicate, or
contextualize the concept. Automated similarity should generate candidates;
high-impact merges must be reviewable and reversible. Different populations,
methods, time periods, modalities, or definitions can make superficially similar
assertions non-equivalent.

### 3. Inference

An inference is a derived proposition produced from one or more assertions or
claims. It must store its inputs, reasoning summary or rule, producing agent,
model and prompt/schema versions, timestamp, and evaluation state.

An inference must never be presented as something the cited source asserted.
This boundary is essential for high-fidelity retrieval and honest report
provenance.

## Target lineage

```text
source
  -> immutable source edition
      -> exact passage
          -> source assertion
              -> supports | contradicts | qualifies | replicates
                  -> canonical claim version
                      -> report/run use

source assertions / canonical claims
  -> derived inference (explicit inputs and producer provenance)
      -> report/run use
```

Recommended durable entities are `source`, `source_edition`, `passage`,
`assertion`, `canonical_claim`, `canonical_claim_version`, `evidence_edge`,
`entity`, `relation`, `extraction`, `evaluation`, `report_revision`, `run_use`,
`access_scope`, and `audit_event`.

Use content hashes for immutable editions and passages. Use opaque stable IDs for
mutable records and claim concepts. Preserve the current Markdown/YAML artifacts
as canonical run evidence while the shared ledger is introduced behind a service
boundary; the existing SQLite catalog should remain a rebuildable read model.

## Competitive and prior-art landscape

The component capabilities exist in the market and research ecosystem, but the
private-first, arbitrary-source, passage-bound assertion lifecycle is not made
mutually redundant by any single reference reviewed.

| System | Relevant capability | Remaining opening for Research Foundry |
|---|---|---|
| [OpenAlex](https://developers.openalex.org/) | Scholarly works, authors, institutions, concepts/topics, and citation relationships. | Primarily a scholarly document graph rather than a user-governed assertion ledger for arbitrary private and public sources. |
| [Semantic Scholar Academic Graph API](https://api.semanticscholar.org/api-docs) | Paper, author, citation, recommendation, and dataset-oriented scholarly metadata. | Useful discovery/enrichment upstream; does not replace durable tenant-owned passage/assertion lifecycle. |
| [scite API](https://api.scite.ai/docs) and [scite MCP](https://scite.ai/mcp) | Citation statements and support/contrast/mention context; direct overlap with evidence relationships and agent retrieval. | Strongest overlap, but its citation-context service does not remove the need for arbitrary internal sources, report lineage, or private assertion governance. |
| [Elicit literature review](https://elicit.com/solutions/literature-review) | Structured paper extraction, cited synthesis, source sentences/figures, and private uploads. | Close workflow competitor; Research Foundry's differentiation must be reusable cross-project assertion identity, correction impact, open exports, and agent-facing governance. |
| [Consensus Meter](https://help.consensus.app/en/articles/10069920-the-consensus-meter) | Question-level synthesis and classification of research positions. | Produces synthesis around a question, not a durable assertion object graph owned by the user. |
| [Open Research Knowledge Graph](https://academy.orkg.org/tutorials/comparison-tutorial-ii.html) | Structured scholarly contributions, statements, and comparisons. | Important prior art for scholarly knowledge organization; narrower than arbitrary private-source ingestion and tenant policy. |
| [Nanopublications](https://nanopub.net/guidelines/working_draft/) | Portable assertions with provenance and publication information, represented as named graphs. | Strong interchange precedent; leaves extraction, evaluation, access control, correction workflow, and product UX to implementers. |

The defensible product wedge is therefore not “AI extracts claims from papers.”
That space is crowded. The differentiated combination is:

- Arbitrary public, licensed, and internal sources.
- Immutable editions and exact passage selectors.
- Reusable assertion identity across research runs.
- Explicit contradiction, qualification, correction, and retraction lifecycle.
- Private tenancy with governed, rights-cleared public promotion.
- Report, run, author, and downstream-writeback lineage.
- An agent-facing evidence-packet query and write contract.

External scholarly graphs and evidence services should be treated as enrichment
and discovery integrations where their terms permit, not as reasons to abandon
the ledger.

## Standards to adopt

Avoid inventing new provenance or annotation formats where stable standards
already cover the need:

- [W3C PROV-O](https://www.w3.org/TR/prov-o/) for entities, activities, agents,
  derivation, attribution, generation, revision, and invalidation.
- [W3C Web Annotation Data Model](https://www.w3.org/TR/annotation-model/) for
  passage targets and robust selectors.
- [Nanopublication guidelines](https://nanopub.net/guidelines/working_draft/)
  for optional portable public assertion/provenance/publication graphs.
- [RO-Crate 1.3](https://www.researchobject.org/ro-crate/specification.html) for
  packaging evidence bundles and their contextual metadata.

The internal schema can remain pragmatic, but mappings to these standards should
be explicit and covered by round-trip tests before public interchange is added.

## Indicative uplift and cost

These estimates are planning ranges to validate through SPIKEs:

| Delivery boundary | Incremental engineering scope | Expected value hypothesis |
|---|---:|---|
| Private pilot | 4–7 engineer-weeks | 20–50% less repeat ingestion/extraction and 15–35% faster evidence assembly on recurring-domain workloads. |
| Durable private beta | 3–6 engineer-months | 30–60% lower repeat evidence-preparation effort, plus reproducibility, freshness, and correction/retraction handling. |
| Public multi-tenant network | 12–24 engineer-months plus ongoing operations | Potentially material discovery/network value, but no credible ROI range until corpus liquidity, rights, isolation, and moderation are proven. |

Recurring costs include parsing/OCR, extraction and evaluation, embeddings and
indexes, refresh/re-extraction, merge review, retraction handling, rights and
retention enforcement, abuse response, and security operations. Storage is
unlikely to dominate cost; quality and governance are the expensive parts.

## Principal risks and required controls

| Risk | Consequence | Required control |
|---|---|---|
| Extraction error or lost qualifiers | Incorrect reuse appears authoritative. | Atomic assertions, exact passages, structured qualifiers, evaluation states, abstention, and sampled human review. |
| False semantic merge | Distinct populations, methods, or timeframes collapse into one claim. | Candidate-only clustering, conservative thresholds, reversible versions, merge review, and negative test cases. |
| Inference/source conflation | Model reasoning is attributed to an author. | Separate object types, explicit input lineage, UI labels, and export validation. |
| Source drift or changed OCR | Stored passage no longer matches the cited edition. | Immutable edition hashes, selector fallback, passage hashes, and edition-diff workflow. |
| Stale or retracted evidence | Reports continue to reuse invalid evidence. | Freshness state, correction/retraction events, impact graph, and reuse gate. |
| Review cost exceeds savings | Ledger becomes an expensive queue. | Risk-tiered review, measured reuse economics, automated evaluation, and no canonical merge requirement for the first pilot. |
| Tenant leakage | Private content leaks through search, vectors, graph edges, counts, autocomplete, caches, or exports. | Build on completed WKSP-304 row scoping, keep indexes tenant-scoped initially, and require an adversarial shared-index leakage gate before any shared-store rollout. |
| Rights or privacy violation | Public corpus cannot legally retain or redistribute content. | Keep public promotion deferred; before public rollout require rights metadata, lawful-access record, quote/excerpt policy, promotion review, deletion/revocation path, counsel-reviewed policy, and the existing default-deny writeback gate. |
| Source poisoning/prompt injection | Malicious content manipulates extraction or downstream agents. | Treat source text as untrusted data, isolate parsers, constrain tools, record provenance, scan content, and evaluate outputs independently. |

For public-corpus decisions, consult counsel. Relevant primary materials include
[Crossref metadata and licensing guidance](https://www.crossref.org/documentation/retrieve-metadata/),
[EU Directive 2019/790 on copyright and text/data mining](https://eur-lex.europa.eu/eli/dir/2019/790/oj),
the [EU Database Directive](https://eur-lex.europa.eu/legal-content/en/ALL/?uri=CELEX%3A31996L0009),
and the [U.S. Copyright Office AI initiative](https://www.copyright.gov/ai/).
This report is product and architecture guidance, not legal advice.

## Required blocking SPIKEs

Create exactly three new blocking charters. Existing charters and completed
foundations listed above are inputs; do not duplicate them.

### SPIKE 1 — Historical replay and reuse economics

Replay 100–300 sources across 10–20 historical or representative runs. Measure
edition-level cache hits, reusable assertion rate, avoided model calls, elapsed
time, cost, downstream evidence-preparation effort, and the proportion of work
that still requires freshness or extraction-contract refresh.

Suggested continuation gate: at least 20% of processing is safely reusable and
at least 95% of sampled reused assertions retain the correct passage provenance.

### SPIKE 2 — Canonical assertion/claim identity and semantic merge audit

Prototype immutable edition and passage identity, stable assertion fingerprints,
canonical-claim versioning, candidate semantic merges, qualifier-aware
non-equivalence, and reversible merge decisions in one narrow domain. This SPIKE
must explicitly consume the existing
[citation precision/recall metrics](../../exploration/citation-precision-recall-metrics/citation-precision-recall-metrics-charter.md)
and [claim segmentation/source-alignment](../../exploration/claim-segmentation-source-alignment/claim-segmentation-source-alignment-charter.md)
charters; it does not reopen their extraction-quality questions.

Suggested continuation gates: deterministic identity for unchanged editions,
explicit new identity for changed editions, at least 80% reviewer acceptance of
merge candidates, below 2% harmful false merges, and no silent qualifier loss.
If semantic merging fails, ship reusable source assertions without canonical
claim merging.

### SPIKE 3 — Source-edition correction/retraction impact propagation

Inject corrected editions, invalid extractions, and retracted sources. Confirm
the system can enumerate and invalidate every affected assertion version,
canonical claim edge, report revision, run, export, cache/index record, and
downstream writeback. This consumes the existing
[contradiction-log-v1 charter](../../exploration/contradiction-log-v1/contradiction-log-v1-charter.md)
where evidence relationships overlap, but remains distinct: contradiction asks
how claims disagree; this SPIKE asks how a changed or invalidated source
propagates through already-materialized dependencies.

Suggested continuation gate: 100% affected-object enumeration in the fixture
set before automated reuse is enabled.

## Conditional shared/public rollout gates

These are not new blocking charters for the private ledger:

- **Shared-index tenant leakage:** before any shared store or index, adversarially
  test lexical search, vectors, graph traversal, counts, autocomplete, dedupe
  candidates, caches, exports, logs, and deletion across workspaces. Build on the
  completed WKSP-304 enforcement work. Any unauthorized disclosure blocks the
  shared deployment; tenant-scoped indexes remain the default.
- **Public-corpus rights and promotion:** before any public corpus, classify the
  pilot corpus by rights and allowed output, obtain counsel-reviewed policy, and
  route promotion/revocation through the existing writeback-default-deny gate.
  Any source without an explicit allowed-use basis remains private and
  non-promotable.
- **Credential boundary:** agent-job credential isolation is already decided by
  the completed P4/P5 foundations SPIKE. Implementation composes with that
  boundary and adds regression coverage only; it does not create a new SPIKE.

## Implementation implications

The linked PRD and plan should preserve these boundaries:

1. **Introduce the ledger behind services and versioned schemas.** Do not make
   the existing derived catalog canonical.
2. **Start with immutable source editions, passages, and source assertions.** A
   useful private pilot does not depend on canonical claim clustering.
3. **Add optional persistent IDs to run artifacts and exports.** Existing
   `claim_id`, source-card, report-anchor, and viewer behavior must remain valid
   for legacy runs.
4. **Make reuse a policy decision.** Reuse only when source edition, extraction
   contract, rights, sensitivity, freshness, and evaluation state allow it.
5. **Separate write and read authorization.** Every assertion, passage, edge,
   index row, cache entry, export, and aggregate must be scoped.
6. **Build evaluation and correction before promotion.** Provenance checks,
   qualifier fidelity, invalidation, and impact enumeration are release gates.
7. **Expose evidence packets, not context-free snippets.** Retrieval should
   include assertion, passage, edition, source metadata, qualifiers, status,
   contradictions, freshness, rights decision, and report/run lineage.
8. **Reuse settled governance and isolation.** Build on WKSP-304 workspace
   isolation, the writeback-default-deny charter, and the completed P4/P5
   credential-isolation decision; do not create parallel mechanisms.
9. **Defer shared/public rollout.** Shared embeddings/indexes require the
   conditional tenant-leakage gate. Public promotion, federation, moderation,
   and nanopublication export additionally require the conditional rights and
   promotion gate.

High-leverage follow-on capabilities include source-edition “what changed?”
diffs, correction/retraction impact graphs, a merge and promotion review
workbench, domain extraction profiles, research-gap planning, cost-aware
reuse/refresh/re-ingestion routing, and signed public assertion exports.

## Decision

Proceed with a phased private implementation, beginning with the validation
SPIKEs and a narrow recurring-domain pilot. The project is technically feasible
and aligned with live Research Foundry seams. Its business value is plausible
and potentially compounding, but must be proven through measured reuse rather
than assumed from corpus size.

Do not commit to a public research network as part of the initial feature. Make
public promotion a later, explicit decision supported by rights-cleared corpus
evidence, isolation tests, correction operations, and demonstrated private
reuse economics.
