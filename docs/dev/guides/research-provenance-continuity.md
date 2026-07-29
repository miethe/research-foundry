---
title: "Research Provenance Continuity (RPC) Guide"
description: "The canonical origin/run/activity/report-use/inference/canonical-claim provenance layer: entry points, commit protocol, staleness model, and governance boundaries"
audience: ["developers"]
tags: ["provenance", "assertion-ledger", "inference", "canonical-claim", "report-lineage", "lifecycle"]
created: 2026-07-28
updated: 2026-07-28
category: "architecture"
status: "published"
feature_slug: research-provenance-continuity
related_documents:
  - "docs/dev/architecture/research-provenance-contract-freeze.md"
  - "docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md"
  - ".claude/findings/research-provenance-continuity-findings.md"
  - "schemas/provenance_origin.schema.yaml"
  - "schemas/research_run_envelope.schema.yaml"
  - "schemas/search_activity_receipt.schema.yaml"
  - "schemas/report_assertion_use.schema.yaml"
  - "schemas/inference_record.schema.yaml"
  - "schemas/canonical_claim.schema.yaml"
---

# Research Provenance Continuity (RPC) Guide

RPC is the canonical **provenance layer** wrapped around the existing Reusable Assertion Ledger
(RAL): it names *where evidence came from* (origin), *how it was discovered* (run/activity
envelopes and receipts), *what a report actually cited* (report-use), and *how a conclusion was
derived beyond a direct source quote* (inference / canonical-claim). It replaces nothing — RAL,
activation, RFUP, and CARP's own selection-receipt mechanism all keep their existing authority; RPC
adds a layer that consumes and cross-references them.

This is a mechanism guide for developers extending or consuming these services. For the frozen,
normative contract (identity/fingerprint formulas, the exact commit protocol, threat boundaries),
read `docs/dev/architecture/research-provenance-contract-freeze.md` — this guide summarizes and
points there rather than restating it. For plan/reality reconciliation history (what shipped
against what was originally planned), see
`.claude/findings/research-provenance-continuity-findings.md`.

## What the provenance layer is

Six record kinds, each with its own schema and writer service:

| Record kind | Schema | Answers |
|---|---|---|
| Origin | `provenance_origin.schema.yaml` | Where did this evidence come from (acquisition/import/capture/generation, producer, locator/digest)? |
| Run/activity envelope | `research_run_envelope.schema.yaml` | What discovery activity happened — planned run or search-only? |
| Activity receipt | `search_activity_receipt.schema.yaml` | Exactly what was queried, and what was selected/denied/degraded? |
| Report use | `report_assertion_use.schema.yaml` | What did a specific report revision actually cite? |
| Inference | `inference_record.schema.yaml` | A conclusion derived from other claims, not a direct source quote. |
| Canonical claim | `canonical_claim.schema.yaml` | An explicitly requested, durable claim backed by an exact assertion/inference support set. |

Every record kind is immutable once published and content-addressed (its id is
`"<prefix>_" + sha256(canonical_json(material_fields))`, per the freeze doc's identity-computation
rules). Nothing here mutates a record in place — lifecycle changes are represented as separate,
durable effect receipts (see [Staleness model](#staleness-model)), never as an edited field on an
existing file.

## Entry points

All services are workspace-scoped: construct one instance per `workspace_id`, matching every other
RAL-family service's shape (`AssertionRegistry`, `AssertionCatalog`).

### Origin, run/activity, and receipts — `services/provenance_envelope.py`

```python
from research_foundry.services.provenance_envelope import ProvenanceEnvelopeStore

store = ProvenanceEnvelopeStore(workspace_id="default")

# RPC-2.1: write a canonical origin record (tamper-evident on read).
origin = store.write_origin(method={"kind": "acquisition", "mechanism": "web_search"}, producer={...})

# RPC-2.2/2.3: create the v1 envelope at planning time (no activity_id yet)...
envelope_v1 = store.create_envelope_v1(activity_kind="search_only", request_id="req_...")
# ...then, once the activity concludes, publish the receipt and promote to v2 atomically.
receipt, envelope_v2 = store.create_receipt_and_promote(
    envelope_v1, query="...", purpose="...", scope={...},
    candidate_set_digest="...", selected_evidence_versions=[...], selection_receipt={...},
)

# Read back the current envelope + receipt (verifies content-binding and the
# generation-manifest tamper-evidence check on every read).
envelope, receipt = store.read_envelope(envelope_v1["envelope_id"])

# AC RPC-1 resilience: facets are always rebuildable, never a second authority.
facets = store.rebuild_origin_facets()
```

`ProvenanceEnvelopeStore.create_envelope_v1` then `create_receipt_and_promote` is a strict two-step
protocol, not two independent calls you can reorder — see [Commit protocol](#commit-protocol-and-manifestpointer-authority)
for why the ordering matters. A crash between the two steps is recovered by
`store.recover_orphaned_promotions()`, which the phase-P5 governed read paths already call before
serving a list/fetch.

### Governed, read-only activity discovery — `services/research_run_discovery.py`

```python
from research_foundry.services.research_run_discovery import ResearchRunDiscovery

discovery = ResearchRunDiscovery(workspace_id="default")
listing = discovery.list_activities(activity_kind="search_only", identity=identity)  # {"items": [...], "next_cursor": None, "denial_reason": None}
activity = discovery.fetch_activity(envelope_id, identity=identity)  # raises ResearchRunDiscoveryDenied, never leaks
```

A `search_only` activity (a search with no planned run — including a zero-match search) has no other
governed surface: it never appears with a fabricated `run_id`, and it is only referenced from an
evidence packet's `search_activity_ids` once its receipt selected at least one assertion version.

### Report-use — `services/assertion_report_use.py`

```python
from research_foundry.services.assertion_report_use import ReportAssertionUseService

svc = ReportAssertionUseService(workspace_id="default")
outcome = svc.prepare_report_assertion_use(
    report_ref=build_report_ref(...), persistent_references=claim["persistent_references"], created_at=now,
)
if outcome.status == "prepared":
    use_id, record = svc.publish(outcome.record)
```

`resolve_cited_reference` is the load-bearing call: a claim whose `persistent_references` names a
resolvable `source_assertion_id`/`assertion_version`, `inference_id`, or `canonical_claim_id` resolves
to a real `cited_ref`; anything else — missing refs, an unresolvable id, a cross-workspace id — comes
back `legacy_unresolved` and **mints no record**. This is why a historical report predating this
contract has no `report_assertion_use` records and never will retroactively (see the deferred
historical-reconstruction spec, linked from the findings doc).

### Inference and canonical claims — `services/assertion_inference.py`, `services/canonical_claim_materialization.py`

```python
from research_foundry.services.assertion_inference import AssertionInferenceMaterializer
from research_foundry.services.canonical_claim_materialization import CanonicalClaimMaterializer

inf = AssertionInferenceMaterializer(workspace_id="default")
resolution = inf.resolve_bases(claim_id, ledger)               # typed skip, never an exception
result = inf.materialize_inference(run_id, claim_id)           # mints inference_id, publishes, references the ledger

cc = CanonicalClaimMaterializer(workspace_id="default")
support = cc.resolve_support(source_assertion_refs, inference_refs)
result = cc.publish_canonical_claim(
    run_id, claim_id, statement="...", source_assertion_refs=[...], inference_refs=[...],
    explicit_request=True,  # REQUIRED — omitting it aborts before anything is read (implicit_merge_rejected)
)
```

Both materializers share the same failure discipline: **every expected precondition failure returns
a typed `abstained`/`skipped` result, never an exception.** A genuine data-corruption conflict (a
content-addressed write finding different bytes at the same path) is the one case that raises
(`InferenceMaterializationConflict` / `CanonicalClaimMaterializationConflict`). `explicit_request=True`
on `publish_canonical_claim` is not a formality — a canonical claim's support set must always be
named by the caller; it is never derived automatically the way an inference's bases are (contract
freeze §15.4, "never automatic or inferred").

### Governed API — `api/routers/assertions.py`

Five routes, all workspace/identity-gated, all reusing the same no-existence-leak posture as
`/assertions/search`:

| Route | Purpose |
|---|---|
| `GET /assertions/{id}/lineage` | Existing RAL lineage, unchanged. |
| `GET /assertions/{id}/impact` | P6 policy-authorized impact summary — no ledger-path detail. Read-only; lifecycle reconciliation stays out of the HTTP API. |
| `GET /assertions/activities` | List workspace-scoped activities; `activity_kind` filters `planned_run`/`search_only`. |
| `GET /assertions/activities/{envelope_id}` | Fetch one activity's exact envelope/receipt pair. |
| `GET /assertions/{id}` | Evidence packet — additive `inference_lineage`/`canonical_claim_lineage`/`search_activity_ids` fields (RPC-5.2, schema 1.8). |

Missing workspace context, an unknown id, and a denied cross-workspace id all collapse to the
identical 404/`not_authorized_or_not_found` shape — never a more informative error that would
distinguish those cases.

### Export — `services/export_service.py` (schema 1.8)

`EXPORT_SCHEMA_VERSION = "1.8"` adds the same additive, read-only provenance/lineage fields the API
packet gains, propagated into the export bundle and the generated frontend types
(`frontend/runs-viewer/src/types/rf/assertions_api.generated.ts`). Legacy bundles keep every existing
field; nothing is renamed or removed.

`export_service.py`'s `record_external_report_import_activity(..., provenance_origin: str | None =
None)` — the seam ERI (External Research Report Interchange) reserved before RPC existed — now has a
real shape to accept: any caller holding a real `provenance_origin` record passes its bare `origin_id`
string through unchanged. No ERI code change is required or authorized by RPC; the parameter stays
opaque by design at that call site.

## Commit protocol and manifest/pointer authority

**No canonical write here uses a single atomic step.** Every writer follows a **stage → promote →
manifest** pattern: write content-addressed bytes to a staging location, then atomically promote to
the canonical path, then append a tamper-evidence manifest entry. A reader trusts a record only when
all three steps are visible; a crash between any two steps leaves the system in a recoverable,
never-partial state (`recover_orphaned_promotions`, `recover_orphaned_inferences`,
`recover_orphaned_canonical_claims` all converge from that same crash window).

**The commit-authority asymmetry across lanes (N5, `research-provenance-continuity-findings.md`)** —
important for anyone building a new reader:

- **Envelope/receipt lane**: the generation-manifest entry, appended once at legitimate v2 promotion,
  is the tamper-evidence root. A reader (`store.read_envelope`) treats a v2 record with no matching
  manifest entry as **not-yet-promoted** (a legitimate crash-window state), not as corrupt.
- **Inference/canonical-claim lane**: the `.claim_ledger_published.yaml` generation **pointer** is the
  authority, not the manifest alone — a manifest entry can exist for a quarantine-eligible orphan
  that never actually got referenced into the ledger.

**Consequence for P5/P6-style consumers: always read through each lane's own reader/recovery API
(`ProvenanceEnvelopeStore.read_envelope`, the inference/canonical-claim materializers' own read
paths), never a raw manifest file directly.** Inventing a fourth ad hoc read path re-derives a
subtly wrong authority model.

## Staleness model

Inference and canonical-claim records are **immutable forever** — a `status`/`state` field written
once is never flipped on disk. Staleness instead propagates as a separate, durable,
content-addressed **effect receipt**: `impact_effects/<event_id>/<digest>.yaml`, written by
`AssertionImpactReconciler.reconcile` when a source assertion is authoritatively blocked.

Two consumers must read the **effective** state through this effect-receipt lane, never the
immutable record's own field, or a policy-blocked/stale citation becomes silently invisible:

- **`assertion_impact.collect_stale_object_ids`** — the one effective-status reader for
  `inference`/`canonical_claim_edge`/`report_revision` staleness (F18). Both P4's commit recheck
  (`assertion_materialization._recheck_transitive_support`) and P5's catalog lineage builder consult
  this before trusting a raw `status` field.
- **`assertion_impact.effective_source_assertion_lifecycle_state`** — the one effective-lifecycle
  reader for a source assertion's own authoritative-block boundary (F19). A P6 block never flips the
  immutable source assertion's own `lifecycle_state`; the separate `lifecycle_policy/<id>.yaml` file
  is the authoritative reuse boundary instead. Returns `"eligible"` / `"blocked"` /
  `"policy_invalid"` — the third state exists so a corrupt policy artifact is never silently treated
  as "not blocked." A commit-path caller must fail closed on `"policy_invalid"`; a read-path caller
  may degrade to the raw record's state, but only after logging a warning.

**If you are writing a new consumer of inference/canonical-claim/report-use records, route every
staleness/block check through these two functions.** Reading the raw record's own field directly
reproduces F18/F19 — the exact bug class this findings doc documents as fixed in the Wave-3
integration cycle.

## Governance boundaries

- **Workspace guards — reuse, never invent a fourth.** Writes: `assertion_workspace.resolve_or_deny`
  (fail-closed; `None`/empty/whitespace-only `workspace_id` denies with
  `reason="workspace_context_missing"`, never an exception). HTTP: `api/auth/scope.require_workspace_scope`
  (returns `allowed=True, reason="single_operator_trust"` immediately when no auth middleware is
  configured — a single-operator deployment never pays for or is affected by an enforcement-flag
  lookup). Run reads: `export_service._run_read_allowed`. Ledger reads: each service's own
  `workspace_id` constructor argument plus its own denied-exception type
  (`AssertionCatalogDenied`, `ResearchRunDiscoveryDenied`, `AssertionImpactReadDenied`).
- **Feature flags default `False`, and this guide does not instruct flipping them.**
  `config.py`'s `canonical_claims_enabled` / `canonical_claims_allowed` (both default `False`) gate
  canonical-claim materialization at the capability layer, mirroring CARP's own
  `ledger_write_enabled` / `automated_reuse_enabled` fail-closed pattern. A stock deployment that has
  not touched these flags will see every canonical-claim path abstain, by design — this is the
  fail-closed gate working as intended, not a defect.
- **DI-1 is BLOCKED.** Per `.claude/findings/research-provenance-continuity-findings.md`'s standing
  directive 3: no phase of this feature flips a deployment-enabling flag, clears a gate, or performs
  a Mode-D self-sign. Nothing in this guide, the contract freeze doc, or the four deferred specs it
  links authorizes doing so.
- **No agent-writable path mints a rights-clearance value.** Per the same findings doc's standing
  directive 4 (and `docs/dev/architecture/adr-rights-entity-model.md`): `CLEARED_*`/`counsel_approved`/
  `attested` values are never minted by code reachable from this feature.
- **Legacy fixtures keep prior behavior (AC RPC-8).** Every additive schema/API/export change here is
  purely additive — a legacy caller that never populates the new fields sees byte-identical behavior
  to before this feature existed.

## Further reading

- Frozen contract (identity formulas, full commit protocol, threat boundaries):
  `docs/dev/architecture/research-provenance-contract-freeze.md`
- Plan/reality reconciliation and standing directives: `.claude/findings/research-provenance-continuity-findings.md`
- Schemas: `schemas/provenance_origin.schema.yaml`, `schemas/research_run_envelope.schema.yaml`,
  `schemas/search_activity_receipt.schema.yaml`, `schemas/report_assertion_use.schema.yaml`,
  `schemas/inference_record.schema.yaml`, `schemas/canonical_claim.schema.yaml`
- Deferred work: `docs/project_plans/design-specs/research-provenance-historical-report-reconstruction.md`,
  `docs/project_plans/design-specs/research-provenance-report-transclusion.md`,
  `docs/project_plans/design-specs/research-provenance-public-export.md`,
  `docs/project_plans/design-specs/research-provenance-derived-graph.md`
