---
title: "Findings: Research Provenance Continuity (C1) — plan/reality reconciliation"
doc_type: findings
feature_slug: research-provenance-continuity
created: 2026-07-28
updated: 2026-07-28
plan_ref: docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
baseline_tree: e76784b
status: active
---

# C1 Reconciliation Findings (F1–F16)

C1 was planned (2026-07-18) to execute FIRST and emit gate `RPC-1.G`. Instead C3 (`d824290`,
`95e8419`), C4 (`1376e85`), C2/ERI (`e76784b`) and DI-1 (`2bf6895`) shipped ~18k overlapping lines
first. **Every conflict below is shipped authority C1 must integrate with — never overwrite.**
Baseline tree for this execution: `e76784b`.

## Findings

- **F1 — RPC-1.G never existed; siblings shipped against it.** C3 carries a written waiver
  (`catalog-assisted-research-planning-v1.md:286-294`); C2/C4 dependency lines are silently
  unsatisfied. C1's P1 gate must be re-anchored to the *current* tree (`e76784b`), and the freeze
  doc must record the retroactive satisfaction/waiver status for C2/C3/C4.
- **F2 — `schemas/inference_record.schema.yaml` EXISTS** (57L, RAL `7fec855`; frozen `$id .../v1`,
  `schema_version: const "1.0"`, `additionalProperties: false`; required `inference_id`,
  `inference_version`, `conclusion`, `source_assertion_refs[{assertion_id,assertion_version}]`,
  `reasoning{summary,method,producer}`, `status ∈ {active,stale,invalidated}`). P1/P4 amend as a
  versioned change, not a fresh freeze.
- **F3 — `schemas/canonical_claim.schema.yaml` EXISTS** (113L, `7fec855`; closed schema, `state`
  machine incl. `split`/`superseded`/`rolled_back`, `source_assertion_refs[].relation`,
  `reversal` conditional). P4 `canonical_claim_materialization.py` implements *against* it.
- **F4 — `report_uses` is a frozen, shipped, always-`[]` API field** — `assertion_catalog.py:265,387,514`,
  `api/routers/assertions.py:66,74`, required in two `openapi.json` response models. P3/P5 *fill*
  this slot; changing its element type from `list[str]` is an OpenAPI-breaking change.
- **F5 — ERI minted the persisted external-origin receipt**
  (`schemas/external_research_import_receipt.schema.yaml`, 478L: digest-bound, immutable,
  workspace-scoped). `provenance_origin.schema.yaml` must *reference* that lane's authority, not
  supersede it.
- **F6 — ERI reserved the exact integration seam**: `export_service.py:1102`
  `record_external_report_import_activity(..., provenance_origin: str | None = None)` — opaque by
  design until C1 lands; events append to `telemetry/run_trace.jsonl` (precedent: no new activity
  store for that lane).
- **F7 — C3 shipped the selection-receipt/candidate-digest mechanism** (`catalog_retrieval.py`
  `CatalogReceipt`/`RetrievalReceipt`; `research_evidence_plan.schema.yaml`
  `selected_assertion_ref` + `retrieval_receipt`). `docs/dev/architecture/carp-contract-freeze.md`
  §4 declares it the **"Normative substitution"** for RPC context, and **§4.2 is a pre-negotiated
  4-row rebase table** naming which CARP fields migrate into `search_activity_receipt.schema.yaml`.
  P1 MUST consume §4.2 as an inbound contract.
- **F8 — `search_request`/`search_run` schemas were extended by C3 after plan authoring**
  (`retrieval` blocks; `search_run.retrieval.selections[]` is a stopgap mirror C3 pre-committed to
  superseding by an RPC `activity_id` reference). RPC-OQ-3's alias set must be re-scoped to the
  current schemas.
- **F9 — Vocabulary collision:** C4's `knowledge_activity_receipt.schema.yaml` pins
  `persisted: const false` (caller-carried, no authority); C1's `search_activity_receipt` is a
  durable file-canonical record. P1 must state the relationship explicitly.
- **F10 — C4's `correlation_ref`/`parent_run_ref` is a shipped run-correlation consumer** that
  predates `research_run_envelope`; the envelope design must map to those field names or define an
  explicit adapter, not assume greenfield naming.
- **F11 — P4 is a gate reversal, not additive:** `assertion_materialization.py:57-60`
  `_DEFERRED_REFERENCE_FIELDS = {canonical_claim_id, canonical_claim_version, inference_id}` is
  actively rejected via `_reject_deferred_references` → `_Abstain("invalid_persistent_references")`.
  Reversal crosses the serialization-barrier boundary (catalog/impact are barrier files).
- **F12 — Unaccounted scope: canonical-claim feature flags.** `config.py:115,130,519-520`
  (`canonical_claims_enabled`/`canonical_claims_allowed`, both default `False`) and
  `assertion_rollout.py:79,140,145` are in no phase's `files_affected`. P4 must plumb these; the
  defaults stay `False` (DI-1 BLOCKED — no deployment-enabling flag flips).
- **F13 — Unaccounted scope: lifecycle vocabulary already shipped.**
  `schemas/assertion_lifecycle_event.schema.yaml` (118L) already enumerates `inference_record`/
  `canonical_claim` targets and `canonical_claim_edge`/`inference`/`report_revision` dependent
  actions; `assertion_impact.py:58` maps `canonical_claim_edge → mark_stale`. P6 consumes this
  existing vocabulary; no phase lists the schema file — treat as read-authority, amend only if a
  gap is proven.
- **F14 — `source_assertion.schema.yaml` (559L, re-frozen by Rights `17a2cb0`) has no
  `origin`/`external_origin` field.** C1's canonical origin lives in a **separate**
  `provenance_origin` record; do not touch the Rights-frozen source_assertion schema.
- **F15 — Missing referenced artifacts:** this findings doc (now created), 4 deferred design specs
  (`docs/project_plans/design-specs/research-provenance-{historical-report-reconstruction,
  report-transclusion,public-export,derived-graph}.md` — P7 authors), and
  `tests/unit/test_assertion_impact.py` (named in plan body; P6/P7 must create or re-point).
- **F16 — "Exact-tree" premise stale:** every serialization barrier except `assertion_impact.py`
  was mutated by siblings since 2026-07-18 (`assertion_catalog.py` +211, `openapi.json` +1828,
  search schemas +125; collaborators `export_service.py` +261, `run_launch.py` +40,
  `verification.py` +105). The P1 gate anchors to `e76784b`-descended trees; the 40-pt estimate is
  medium-confidence.

- **F17 (from P1b)** — `schemas/claim_ledger.schema.yaml` `persistent_references` pairs
  `canonical_claim_id`+`canonical_claim_version` but has no `inference_version` alongside
  `inference_id`, conflicting with AC RPC-3's "exact versions" requirement. File is outside the
  plan's `files_affected`; freeze doc §17.6 offers two resolutions — P4 must pick one explicitly.

- **F18 (RPC-6.G validator, traced)** — N7's effect-receipt staleness is invisible to the two
  natural consumers: P4's `_recheck_transitive_support` (`assertion_materialization.py:987-1027`)
  reads raw `inference.status` (written once as `active`, never flipped) and P5's catalog lineage
  (`assertion_catalog.py:648-720`) reads raw records — neither consults the impact lane. A
  P6-marked-stale inference can be cited by a NEW canonical claim, and lineage shows it `active`.
  DISPOSITION: fixed in the Wave-3 integration cycle (effective-status reader exported by the
  impact lane, consulted by both consumers); RPC-7.5's fixture MUST drive a record through a real
  P6 `mark_stale` event, never a hand-authored `status: stale`.

- **F19 (Karen Wave-3 gate, K-1, HIGH — pre-existing from Wave 2/P4)** — a P6-authoritatively
  BLOCKED source assertion (`lifecycle_policy/<id>.yaml` says blocked; immutable record stays
  `eligible`) can be directly cited by a NEW canonical claim: `_recheck_transitive_support`
  (`assertion_materialization.py:~1017`) and the catalog packet builder read the immutable record,
  never the policy file (only `assertion_impact.py` reads it). Same class as F18, different
  mechanism (authoritative block vs effect-receipt staleness). DISPOSITION: fixed in the Wave-3
  close-out cycle (policy-file effective-state consult, symmetric to F18); RPC-7.5 fixtures must
  cover a real policy-blocked direct citation. Also K-2 (MEDIUM): corrupt-but-present staleness
  receipt silently un-stales — split posture: commit path fails CLOSED, read path degrades with a
  logged warning. K-3 (LOW): `report_revision` in `_STALEABLE_OBJECT_CLASSES` has no consumer yet
  — annotated as forward-looking for report-use staleness display.

## Execution-discovered design notes

- **N1 (from P1a)** — plan `files_affected` names `services/provenance_envelope.py` (not yet
  existing). P2 must decide whether it owns writes for all three new schemas or splits origin
  writes into a separate module.
- **N2 (from P1a)** — `selection_receipt.outcome: fallback` is frozen in the schema, but the
  producing service sequence is undecided; P2 must read CARP freeze doc §3.6 ("Seams P2 must
  add", unresolved per-term pagination arithmetic) before wiring a fallback producer.

- **N3 (from P1b, open item RPC-1.3.a)** — the `run_report` family's `report_revision_id`
  minting algorithm is undecided; P3 decides it when implementing `assertion_report_use.py`.
- **N4 (from P1b, open item RPC-1.4.a)** — `canonical_claim.state` vocabulary tension
  (freeze doc §17.5); P6 resolves, no widening done in P1.

- **N5 (Karen RPC-4.G, for P5/P6)** — commit-authority asymmetry across lanes: envelope lane =
  manifest-append is the commit point; inference/canonical lane = the
  `.claim_ledger_published.yaml` generation POINTER is authority (a manifest entry may exist for a
  quarantine-eligible orphan). P5/P6 MUST read through each lane's reader/recovery API, never raw
  manifests.
- **N6 (Karen RPC-4.G, for P5/P6)** — P4 collapses CAS-abort/proof-tamper/missing-target into the
  contract's `partial_write_rejected` catch-all; add a sub-reason field only if P5/P6 audit needs
  to distinguish. Also K-1: `list_activities(identity=None)` returns [] fail-closed — empty list
  ≠ "no runs exist". K-2: rights rank-order tables in `assertion_report_use.py` are a defensible
  module default where the freeze doc left enum order ambiguous (comparison-only).

- **N7 (P6b, for RPC-6.G to ratify)** — staleness propagation is implemented as durable
  content-addressed effect receipts (`impact_effects/<event_id>/<digest>.yaml`) read via
  `AssertionImpactReconciler.validated_receipt`; inference/canonical-claim records themselves stay
  immutable (`status` fields never flip on disk). Driven by P6a's no-side-effect-keys pin; not
  explicit in the freeze doc. If a future phase wants on-disk status flips, that is a versioned
  contract change.

## Status at P7

Disposition of every F/N item as of P7 (docs and hardening close-out). One line each.

- **F1** — resolved-in-execution: `RPC-1.G` re-anchored to `e76784b` and granted (P1); freeze doc §3
  records C2/C3/C4's retroactive satisfaction status.
- **F2** — resolved-in-execution: `inference_record.schema.yaml` amended additively (round-1/2 fixes),
  never re-frozen from scratch.
- **F3** — resolved-in-execution: `canonical_claim.schema.yaml` amended additively; `CanonicalClaimMaterializer` implements against the existing state machine.
- **F4** — resolved-in-execution: `report_uses` (frozen `list[str]`) is now populated by P3/P5 without changing its element type.
- **F5** — resolved-in-execution: `provenance_origin.external_receipt_ref` references the ERI receipt lane; ERI's own schema is untouched.
- **F6** — resolved-in-execution: `export_service.py`'s reserved `provenance_origin: str | None` seam now accepts a real `origin_id`; no ERI code changed.
- **F7** — resolved-in-execution: CARP's `carp-contract-freeze.md` §4.2 rebase table was consumed as an inbound contract by P1/P2 (`selection_origin` discriminator, §5.1 rule 8).
- **F8** — resolved-in-execution: `search_run.retrieval.activity_id` added additively with an `allOf` mutual-exclusion rule against the legacy `selections[]` mirror; RPC-OQ-3 resolved in the freeze doc (see below).
- **F9** — carried-as-limitation: `knowledge_activity_receipt` (`persisted: const false`) and `search_activity_receipt` (durable) remain deliberately distinct, non-unified vocabularies — documented relationship only, no merge.
- **F10** — resolved-in-execution: C4's `correlation_ref`/`parent_run_ref` naming was mapped explicitly rather than assumed greenfield (freeze doc §7).
- **F11** — resolved-in-execution: P4 amends `_DEFERRED_REFERENCE_FIELDS` handling as a versioned change across the serialization barrier, reviewed and gated at `RPC-4.G`.
- **F12** — resolved-in-execution: `canonical_claims_enabled`/`canonical_claims_allowed` are plumbed through P4's capability gate; both remain default `False` (DI-1 posture preserved).
- **F13** — resolved-in-execution: `assertion_lifecycle_event.schema.yaml`'s existing vocabulary is consumed as-is by P6, with one documented, empirically-checked narrowing (freeze doc §2, SOL-15a).
- **F14** — carried-as-limitation: `source_assertion.schema.yaml` remains untouched by design; origin context is referenced via a separate `provenance_origin` record, never a new field on the Rights-frozen schema.
- **F15** — resolved-in-execution: this findings doc, the four deferred design specs, and the P6/P7 test fixtures all now exist on disk.
- **F16** — carried-as-limitation: the "exact-tree" premise was formally re-anchored to `e76784b` at `RPC-1.G`; the 40-pt estimate remains labeled medium-confidence per the plan body.
- **F17** — resolved-in-execution: `claim_ledger.schema.yaml`'s `persistent_references.inference_version` conditional was added (SOL-11 scope extension, freeze doc §16.3).
- **F18** — resolved-in-execution: `assertion_impact.collect_stale_object_ids` is now the one effective-status reader both P4's commit recheck and P5's catalog lineage builder consult; RPC-7.5 fixtures drive a real P6 `mark_stale` event.
- **F19** — resolved-in-execution: `assertion_impact.effective_source_assertion_lifecycle_state` is now consulted symmetrically to F18 for the authoritative-block boundary; K-1 (HIGH) closed. K-2 (corrupt-receipt posture) and K-3 (`report_revision` forward-looking consumer) are carried-as-limitation — see the function's own docstring for the split fail-closed/degrade posture.
- **N1** — resolved-in-execution: `services/provenance_envelope.py` owns writes for all three new schemas (origin/envelope/receipt) in one module; no split was needed.
- **N2** — resolved-in-execution: `fallback_selection_receipt` producer sequencing was designed per CARP freeze doc §3.6 and is documented in the dev guide's five-outcome partition table (via the contract freeze doc).
- **N3** — resolved-in-execution: `report_revision_id_for_run_report(report_id, report_content_digest)` is the shipped minting algorithm (`assertion_report_use.py`).
- **N4** — carried-as-limitation: `canonical_claim.state` vocabulary tension is resolved by P6 within the existing frozen enum; no widening was performed, per the original P1 constraint.
- **N5** — resolved-in-execution: the commit-authority asymmetry (manifest-append vs. `.claim_ledger_published.yaml` pointer) is documented in the dev guide's "Commit protocol and manifest/pointer authority" section; P5/P6 read through each lane's own reader/recovery API.
- **N6** — resolved-in-execution: P4 collapses CAS-abort/proof-tamper/missing-target into `partial_write_rejected`; no sub-reason field was added (no P5/P6 audit need surfaced). K-1 (`list_activities` fail-closed empty-list semantics) and K-2 (rights rank-order defaults) are carried-as-limitation, documented in-code.
- **N7** — resolved-in-execution: staleness propagation via durable content-addressed effect receipts (never in-place status flips) is the shipped, ratified mechanism — see the dev guide's [Staleness model](../../docs/dev/guides/research-provenance-continuity.md#staleness-model) section.
- **RPC-OQ-1** (report use bound to digest, revision, or both) — resolved-in-execution: bound to both (`report_ref` carries `report_id` + `report_content_digest` + `report_revision_id`); see freeze doc §13-15.
- **RPC-OQ-2** (prepare before verification, publish after) — resolved-in-execution: `prepare_report_assertion_use` runs pre-verification; `publish_report_assertion_uses_for_report` is called by `verification.py` only after `verify_report` returns `passed=True`, per the function's own docstring ("publication gates on verification, RPC-OQ-2, §13.2").
- **RPC-OQ-3** (legacy alias scope) — resolved-in-execution: `search_run.retrieval.activity_id` is additive with an explicit mutual-exclusion rule against `selections[]`; no other legacy field was deprecated.

## Standing integration directives for all C1 phases

1. Baseline is `e76784b`; conflicts with shipped code are findings, never silent overwrites.
2. Reuse canonical workspace guards — writes: `assertion_workspace.resolve_or_deny`; HTTP:
   `api/auth/scope.require_workspace_scope`; run reads: `export_service._run_read_allowed`;
   ledger reads: per-service `workspace_id` ctor + `AssertionCatalogDenied`. Never invent a fourth.
3. DI-1 is BLOCKED: no deployment-enabling flag flips, no gate clearing, no Mode-D self-sign.
4. Agent-writable paths never mint `CLEARED_*`/`counsel_approved`/`attested` rights values.
5. Legacy fixtures keep prior behavior (AC RPC-8); additive fields only on existing API shapes.
