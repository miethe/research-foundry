---
title: "Research Provenance Contract Freeze: Origin, Run/Activity, Receipt, Report-Use, and Inference/Canonical-Claim (Parts 1+2)"
doc_type: architecture
status: draft
schema_version: 1
created: 2026-07-28
updated: 2026-07-28
feature_slug: research-provenance-continuity
resolves: ["RPC-OQ-1", "RPC-OQ-2", "RPC-OQ-3"]
related_docs:
  - docs/project_plans/PRDs/enhancements/research-provenance-continuity-v1.md
  - docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md
  - .claude/findings/research-provenance-continuity-findings.md
  - .claude/worknotes/rpc-sol-round1-findings.md
  - .claude/worknotes/rpc-sol-round2-findings.md
  - docs/dev/architecture/carp-contract-freeze.md
  - schemas/provenance_origin.schema.yaml
  - schemas/research_run_envelope.schema.yaml
  - schemas/search_activity_receipt.schema.yaml
  - schemas/search_run.schema.yaml
  - schemas/search_request.schema.yaml
  - schemas/report_assertion_use.schema.yaml
  - schemas/external_research_import_receipt.schema.yaml
  - schemas/knowledge_activity_receipt.schema.yaml
  - schemas/source_assertion.schema.yaml
  - schemas/inference_record.schema.yaml
  - schemas/canonical_claim.schema.yaml
  - schemas/claim_ledger.schema.yaml
  - schemas/assertion_lifecycle_event.schema.yaml
  - schemas/report_draft.schema.yaml
  - src/research_foundry/assertion_identity.py
owner: nick
---

# Research Provenance Contract Freeze: Origin, Run/Activity, Receipt, Report-Use, and Inference/Canonical-Claim

**Status:** DRAFT, Phase P1 contract freeze for Research Provenance Continuity ("RPC",
`research-provenance-continuity-v1`). **Part 1** (below) covers RPC-1.1 (origin authority) and
RPC-1.2 (run/activity and receipt contract). **Part 2** (§13 onward) covers RPC-1.3 (report-use
contract) and RPC-1.4 (inference/canonical-claim contracts). Both parts together are what is
submitted to `task-completion-validator` and Karen for the `RPC-1.G` exact-tree gate
(implementation plan §Phase P1). Until `RPC-1.G` is granted, nothing in this document or its
schemas is authoritative for downstream phases — this is Mode B (Contract Drafting) output, not an
approved freeze.

**SOL round 1 (2026-07-28):** an adversarial cross-model review (gpt-5.6-sol) BLOCKED the first
submission of this gate with findings SOL-1 through SOL-15, plus a separate
`task-completion-validator` MINOR note V-1. That revision remediated all sixteen items. See §22
("Fix-cycle changelog (SOL round 1)") for the finding-by-finding map to the resolving section/file,
and `.claude/worknotes/rpc-sol-round1-findings.md` for the original review text.

**SOL round 2 (2026-07-28):** the round-1 revision was re-submitted and BLOCKED AGAIN. Round 2
found five items CLOSED, five REOPENED with concrete accepted-attack instances, five PARTIAL, and
nine NEW findings (SOL-16 through SOL-24) — including one BLOCKER against this document's OWN round-1
constraint (SOL-17: the claim-ledger conditional rejected a baseline-valid legacy instance). This
revision (round 2) remediates every named item. **Framing principle applied throughout round 2:** a
JSON schema alone cannot enforce cross-record integrity; for every hole schema validation cannot
close, this document now names the exact enforcing service/function a later phase implements, states
the enforcement rule in MUST-grade language, and names the P7 gate task that verifies it — "schema
can't express this" is never treated as a resolution by itself. See §22's round-2 section for the
full finding-by-finding map, and `.claude/worknotes/rpc-sol-round2-findings.md` for the original
review text.

Mode: no `src/research_foundry/**/*.py` production code changes are authorized by this document.
DI-1 is BLOCKED (`.claude/findings/research-provenance-continuity-findings.md` standing directive
3): nothing below flips, clears, or self-signs a deployment-enabling flag.

## 1. Scope

Part 1 covers three new schemas and one additive amendment:

- `schemas/provenance_origin.schema.yaml` — **NEW**. Canonical origin identity (RPC-1.1 / RPC-FR-1).
- `schemas/research_run_envelope.schema.yaml` — **NEW**. Planned/search-run activity envelope
  (RPC-1.2 / RPC-FR-2).
- `schemas/search_activity_receipt.schema.yaml` — **NEW**. Durable, immutable activity receipt
  (RPC-1.2 / RPC-FR-3).
- `schemas/search_run.schema.yaml` — **Additive.** One new optional field,
  `retrieval.activity_id`, added inside the existing CARP-owned `retrieval` block, plus one new
  `allOf` rule (SOL-8) making `activity_id` and the legacy `selections[]` mirror mutually
  exclusive once `activity_id` is populated. No existing property removed, renamed, or tightened.

`schemas/search_request.schema.yaml` is **unchanged** by this part. See §8 for the rationale —
this was a deliberate P1 decision, not an oversight, and is recorded here so a reviewer does not
treat the absence of a diff as a gap.

Part 2 (§13 onward) adds one new schema and now **four** additive amendments (SOL round 1 widened
this from two — see below):

- `schemas/report_assertion_use.schema.yaml` — **NEW**. Immutable report-use identity (RPC-1.3 /
  RPC-FR-6/7).
- `schemas/inference_record.schema.yaml` — **Additive.** One enum value (`tombstoned`) added to
  `status` (RPC-1.4, §16.2). Unchanged by SOL round 1.
- `schemas/canonical_claim.schema.yaml` — **Additive.** One new optional field, `inference_refs`,
  added alongside the existing required `source_assertion_refs` (RPC-1.4, §16.1). Unchanged by SOL
  round 1.
- `schemas/claim_ledger.schema.yaml` — **Additive, NEW to this contract tree (SOL-11).** One new
  optional field, `persistent_references.inference_version`, plus a conditional requiring it
  whenever `persistent_references.inference_id` is non-null (§16.3). This resolves finding F17,
  which the original submission of this document left open. This file was previously out of
  scope for RPC-1.1–1.4 (F2's directive named it read-authority only) — SOL-11 is an explicit,
  documented scope extension (§22).
- `schemas/assertion_lifecycle_event.schema.yaml` — **Additive, NEW to this contract tree
  (SOL-15a).** `transition.from` widens by one enum value (`active`), plus three new `oneOf`
  transition arms and one new conditional restricting `from: active` to
  `target.kind: inference_record` (§16.4). Also a scope extension (§22); this file was previously
  read-authority only (F13).

## 2. Contract tree anchor

Baseline tree: `e76784b` (matches `.claude/findings/research-provenance-continuity-findings.md`'s
`baseline_tree`). This freeze (Parts 1+2 together) is anchored to that tree plus the files this
document introduces or amends:

```
e76784b (baseline)
├── schemas/provenance_origin.schema.yaml            [NEW, part 1]
├── schemas/research_run_envelope.schema.yaml         [NEW, part 1]
├── schemas/search_activity_receipt.schema.yaml       [NEW, part 1]
├── schemas/search_run.schema.yaml                    [AMENDED, additive-only, part 1]
├── schemas/report_assertion_use.schema.yaml          [NEW, part 2]
├── schemas/inference_record.schema.yaml              [AMENDED, additive-only, part 2]
├── schemas/canonical_claim.schema.yaml                [AMENDED, additive-only, part 2]
├── schemas/claim_ledger.schema.yaml                  [AMENDED, additive-only, part 2, SOL-11 scope extension]
├── schemas/assertion_lifecycle_event.schema.yaml     [AMENDED, additive-only, part 2, SOL-15a scope extension]
└── docs/dev/architecture/research-provenance-contract-freeze.md   [THIS DOC, parts 1+2]
```

No other file on the baseline tree is touched by RPC-1.1/RPC-1.2/RPC-1.3/RPC-1.4.
`schemas/search_request.schema.yaml`, `schemas/source_assertion.schema.yaml`,
`schemas/report_draft.schema.yaml`, and every `src/research_foundry/**/*.py` production file
remain byte-identical to `e76784b` after this document. Every amendment listed above (to
`search_run`, `inference_record`, `canonical_claim`, `claim_ledger`, and
`assertion_lifecycle_event`) is verified additive-only against `git show e76784b:<file>`: no
required list, existing enum member, or existing constraint was removed, renamed, or narrowed on
any of the five files, WITH ONE DOCUMENTED EXCEPTION (round 2, SOL-15): a new `allOf` conditional on
`assertion_lifecycle_event.schema.yaml` narrows `transition.from: eligible` to
`target.kind ∈ {source_edition, passage, source_assertion}` (§16.4a). This is a genuine narrowing —
literally nothing was removed from the file (`git diff e76784b` shows pure additions plus the two
already-documented round-1 enum widenings, zero deletions of any other construct), but the new
conditional does reject instances that were structurally valid before it. It is included here
because a repo-wide search confirms ZERO extant `assertion_lifecycle_event` instances anywhere use
the now-forbidden combination (`transition.from: eligible` targeting `canonical_claim` or
`inference_record`) — the combination was never satisfiable against either target's own frozen
status vocabulary in the first place (§16.2, §17.5) — see §22 round 2 for the empirical check. Every
other amendment on all five files remains a strict, verified widening — see §22 for the per-finding
verification note.

## 3. Findings F1 — retroactive gate status for C2/C3/C4

`RPC-1.G` never existed before C2 (ERI), C3 (CARP), and C4 (Knowledge MCP) shipped roughly 18k
overlapping lines against an unsatisfied dependency line (findings F1). This document does not
retroactively grant `RPC-1.G` to those three packages — that is not this task's authority — but it
records the current de facto status so a future reviewer does not re-litigate it from scratch:

| Package | Written dependency | Actual status |
|---|---|---|
| C3 (CARP) | `RPC-1.G` gate | **Written waiver** on file (`catalog-assisted-research-planning-v1.md:286-294`); C3 shipped its own self-contained, additive selection-provenance carrier (`research_evidence_plan.schema.yaml`'s `selected_assertion_ref`/`retrieval_receipt`) instead of depending on RPC, and `docs/dev/architecture/carp-contract-freeze.md` §4 pre-negotiated the exact rebase this document consumes (§6 below). |
| C2 (ERI) | Implicit `provenance_origin` seam | `export_service.py:1102`'s `record_external_report_import_activity(..., provenance_origin: str | None = None)` was reserved as an opaque, unvalidated string parameter specifically so C2 could ship without RPC (findings F6). This document's `provenance_origin.origin_id` (§4) is the first real value shape that seam can now accept — no C2 code change is required or authorized here. |
| C4 (Knowledge MCP) | None declared, but shares vocabulary | `knowledge_activity_receipt.schema.yaml` is unrelated in authority (caller-carried, `persisted: const false`) but shares surface-level naming (`correlation_ref`/`parent_run_ref`) with what this document defines. §7 states the exact relationship; no C4 file changes. |

**Disposition:** all three packages' RPC dependency lines are satisfied *by design choices already
present in their shipped code* (a written waiver, a reserved opaque seam, and non-overlapping
vocabulary) rather than by this document performing any retroactive integration work. `RPC-1.G`,
once granted, applies going forward to P2+ of this plan; it does not require C2/C3/C4 rework.

## 4. Origin authority contract (RPC-1.1, AC RPC-1)

### 4.1 Normative rules

1. **One canonical envelope.** `schemas/provenance_origin.schema.yaml` is the sole authority for
   acquisition/import/capture/generation method, producer/tool, source kind, locator/digest,
   workspace, timestamps, and parent-origin refs. Every other place these facts appear (catalog
   rows, facets, projections) is a rebuildable derivation — never a second authority.
2. **Separate from `source_assertion`** (findings F14). `schemas/source_assertion.schema.yaml`
   (Rights-frozen, `17a2cb0`) has no `origin`/`external_origin` field and gains none here. A
   `source_assertion` that needs origin context references a `provenance_origin` record by
   `origin_id`/`origin_version` through whatever P2 write path is built — this document does not
   authorize adding a reference field to `source_assertion.schema.yaml` itself; that is P2's scope
   to design against the frozen origin shape.
3. **ERI lane stays authoritative for its own receipts** (findings F5/F6).
   `external_research_import_receipt.schema.yaml` is never superseded, mirrored, or duplicated. A
   `provenance_origin` record for an ERI-imported artifact carries `external_receipt_ref`
   (`receipt_id` + `receipt_digest`) as a *reference*, enforced non-null only when
   `method.kind == import` was involved AND the caller actually attaches it; every non-`import`
   origin is schema-forced to `external_receipt_ref: null` (the schema's trailing `allOf`).
4. **`origin_id` is the opaque value for the reserved export seam** (findings F6). Any caller
   holding a real `provenance_origin` record passes its bare `origin_id` string into
   `export_service.py:1102`'s `provenance_origin: str | None` parameter unchanged.
   `export_service.py` needs no import of, or dependency on, this schema to keep accepting that
   value — the field's shape (`^pvo_[a-f0-9]{64}$`, a flat string) is exactly what makes that seam
   remain "opaque by design" (the docstring's own phrase) while still being a real, structured
   reference once this schema exists.
5. **Rebuildable facet rules.** Any origin-derived facet (a catalog column, a search index entry,
   an API convenience field) MUST be computed from a canonical `provenance_origin` record and
   nothing else. Deleting all derived facets for a workspace and rebuilding them from the canonical
   records on disk MUST produce byte-identical facet values (AC RPC-1 resilience clause). A facet
   builder that cannot resolve a `parent_origin_refs` entry (missing, malformed, or cross-workspace)
   MUST fail closed for that one derived value — it may never silently drop the parent link or
   silently promote the child origin to look root-level.
6. **Legacy absence mints no identity.** An artifact that predates this schema (or whose origin was
   never captured) has **no** `provenance_origin` record — service code must never synthesize a
   placeholder `origin_id` merely to fill a lineage slot. Absence is represented by an absent
   reference (`null`), never a fabricated record.
7. **Content-binding is exhaustive and normative (SOL-1, revises the original submission; round 2
   widens it further).** `identity.material_fields` covers **every** immutable provenance fact on
   this record — `origin_version`, `workspace_id`, `method`, `producer`, `source_kind`, `locator`,
   `content_digest`, `external_receipt_ref`, `parent_origin_refs`, and `created_at` (ten fields) —
   not the five-field subset round 1's original submission used, and not the nine-field set round
   1's fix cycle stopped at (`origin_version` itself is now material too, round 2, SOL-1 REOPENED —
   see item 7a below). `origin_id` MUST equal `"pvo_" + identity.fingerprint`, computed with
   the same canonicalization `src/research_foundry/assertion_identity.py` already ships for
   `source_assertion.schema.yaml` (`json.dumps(payload, ensure_ascii=False, separators=(",", ":"),
   sort_keys=True)` then `sha256(...).hexdigest()`, applied to `{field: record.get(field) for field
   in material_fields}` — a missing/omitted field canonicalizes identically to an explicit `null`
   value for that field, so omission and explicit `null` are always interchangeable for identity
   purposes). A P2 writer producing an `origin_id` that does not equal this value is producing an
   invalid instance of this contract, even though JSON Schema alone cannot recompute a SHA-256 to
   reject it at parse time — the same class of service-layer check
   `assertion_identity.py::validate_source_assertion_identity` already performs is required here
   (§4.2 fixture (d) shows the exact failure mode this closes).
7a. **`origin_version` is material (SOL-1, round 2 REOPENED).** Round 1 left `origin_version`
   OUTSIDE `identity.material_fields` — the round-2 accepted attack changed `origin_version` from
   `1` to `999` with every other field, and therefore the fingerprint, held constant: a version bump
   was "free" and unproven, contradicting this record's own "immutable" framing. Folding
   `origin_version` into the material payload closes this: ANY change to `origin_version` now
   necessarily changes `identity.fingerprint` and therefore `origin_id` too (§4.2 fixture (d-1)).
   Consequence, deliberate and documented: `provenance_origin` has NO stable identity that survives
   a version bump (unlike `source_assertion`'s `{stable id, incrementing version, per-version
   digest}` pattern) — a `provenance_origin` record is immutable AT a specific `(origin_id,
   origin_version)` pair, full stop. There is no legitimate in-place "amend this origin to version 2"
   operation; a writer revising an origin mints an entirely new, independently content-addressed
   record. This is safe because zero extant `provenance_origin` instances exist anywhere in this
   repo that could depend on origin_id staying stable across a version change (verified this fix
   cycle). See §5.1b for why `research_run_envelope` deliberately takes a DIFFERENT approach
   (`version_digest`, not material-field inclusion) for the analogous `envelope_version` case.

### 4.2 Examples

**(a) Positive — direct web acquisition.**

```json
{
  "schema_version": "1.0",
  "type": "provenance_origin",
  "origin_id": "pvo_d34184a1c3f0d1d8ae9b8248f345de1fbc46da068695ac546cc26dcfa59093db",
  "origin_version": 1,
  "workspace_id": "default",
  "method": {"kind": "acquisition", "mechanism": "web_search"},
  "producer": {"producer_type": "agent", "producer_id": "agent-research-1", "tool": "rf-search", "tool_version": "1.4.0"},
  "source_kind": "web_page",
  "locator": "https://example.com/article",
  "content_digest": "2222222222222222222222222222222222222222222222222222222222222222",
  "external_receipt_ref": null,
  "parent_origin_refs": [],
  "created_at": "2026-07-28T12:00:00Z",
  "identity": {
    "algorithm": "sha256-canonical-json-v1",
    "fingerprint": "d34184a1c3f0d1d8ae9b8248f345de1fbc46da068695ac546cc26dcfa59093db",
    "material_fields": ["origin_version", "workspace_id", "method", "producer", "source_kind", "locator", "content_digest", "external_receipt_ref", "parent_origin_refs", "created_at"]
  }
}
```

SOL-1 fixture note: `origin_id`'s hex suffix EQUALS `identity.fingerprint` byte-for-byte (both
`d34184a1...59093db`) — the round-1 fix. **Round 2 (SOL-1 REOPENED, revised value):** `origin_version`
now joins `material_fields` (§4.1 rule 7), so this fingerprint DIFFERS from the round-1 value
(`2429f3f8...`) even though every other field is unchanged — the fingerprint now depends on
`origin_version` too. This value was recomputed and schema-validated against
`schemas/provenance_origin.schema.yaml` (Draft 2020-12) as part of this fix cycle; see §22.

**(b) Positive — ERI-imported origin referencing the import receipt lane (F5/F6).**

```json
{
  "schema_version": "1.0",
  "type": "provenance_origin",
  "origin_id": "pvo_00547bb71d6f5ce8d318f8ecdbaca505435457f686ceaa9ee67204e923a59606",
  "origin_version": 1,
  "workspace_id": "default",
  "method": {"kind": "import", "mechanism": "external_research_handoff/v1"},
  "producer": {"producer_type": "external_system", "producer_id": null, "tool": null, "tool_version": null},
  "source_kind": "external_report",
  "locator": null,
  "content_digest": null,
  "external_receipt_ref": {
    "receipt_id": "erh_5555555555555555555555555555555555555555555555555555555555555555",
    "receipt_digest": "6666666666666666666666666666666666666666666666666666666666666666"
  },
  "parent_origin_refs": [],
  "created_at": "2026-07-28T12:05:00Z",
  "identity": {
    "algorithm": "sha256-canonical-json-v1",
    "fingerprint": "00547bb71d6f5ce8d318f8ecdbaca505435457f686ceaa9ee67204e923a59606",
    "material_fields": ["origin_version", "workspace_id", "method", "producer", "source_kind", "locator", "content_digest", "external_receipt_ref", "parent_origin_refs", "created_at"]
  }
}
```

(Round 2, SOL-1 REOPENED: this fingerprint is recomputed from the round-1 value because
`origin_version` now joins `material_fields` — every other field is unchanged.)

Again, `origin_id`'s suffix equals `identity.fingerprint` exactly. `producer`/`external_receipt_ref`
are now material (SOL-1): re-pointing this origin at a different ERI receipt, or attributing it to
a different `external_system`, changes the fingerprint and therefore the `origin_id`.

**(c) Legacy — no origin record.** An artifact ingested before this schema existed carries no
`provenance_origin` at all. Any reader resolving an optional `origin_ref` on
`research_run_envelope.schema.yaml` (§5) or elsewhere gets `null`, never a synthesized record.
There is no fixture to show here beyond "the reference field is absent/null" — that absence is the
legacy-compatible shape.

**(d) Tamper — fingerprint mismatch (schema-valid, service-rejected).** Taking fixture (a) and
changing `locator` to a different URL while leaving `identity.fingerprint` unchanged produces a
record that still validates against the schema (JSON Schema cannot itself recompute a SHA-256),
but fails the *service-layer* identity check P2 must implement: recomputing
`sha256-canonical-json-v1` over the now-TEN-field material payload (§4.1 rule 7, widened to include
`origin_version` in round 2) no longer equals the stored `fingerprint` (verified for this fix cycle:
recomputing over the tampered payload yields
`698bcb0c51f80f81b693884501c5584a0e740b4289ac7a5a06ab919b642745af`, different from fixture (a)'s
`d34184a1...` value above — see §22). This is the same class of
check `source_assertion.schema.yaml`'s `identity` block already relies on a service to enforce —
the schema freezes the *shape* of the proof, not a schema-level recomputation.

**K-2 disposition (P2, RPC-2.1).** The recomputed fingerprint above is real and independently
reproducible from `provenance_envelope.py::verify_origin_integrity` (see
`tests/unit/test_provenance_envelope.py`), but this vector is explicitly **NON-NORMATIVE /
illustrative-only**: it never states the exact tampered `locator` string, so it is not itself a
complete, byte-for-byte recomputable preimage the way fixtures (a)/(b) above and §5.1b's/§17.8's
worked vectors are. The normative claim this vector supports — "changing any material field without
a matching `identity.fingerprint` update is detectable by recomputation" — is independently proven by
`provenance_envelope.py`'s own tamper test, which publishes a complete origin record, mutates one
material field, and asserts the recomputed fingerprint differs from the stored one. Treat this
vector as narrative color, not a pinned test vector; do not attempt to reproduce the exact
`698bcb0c...` value without also reconstructing the untamed `locator` string, which this document
does not name.

**(d-1) Version-bump tamper — the exact SOL-1 round-2 accepted attack, now closed (schema can
partially catch it; the residual gap is service-layer, same as (d)).** Taking fixture (a) and
changing ONLY `origin_version` from `1` to `999` while leaving every other field AND
`identity.fingerprint` unchanged: round 1's schema accepted this outright (`origin_version` was not
material, so the fingerprint was untouched by the change — the round-2 accepted attack). Under this
round's fix, the SAME edit now produces a record whose stored `fingerprint`
(`d34184a1...59093db`) no longer matches what a service recomputing over the tampered
ten-field payload gets instead
(`af04c5bf56b7271b069252cb7b1493fdb4f1e0573da6ce387b2ae5f2e9d8d488` — computed for this fix cycle).
JSON Schema alone still cannot recompute a SHA-256 (the instance remains structurally valid), so this
remains a service-layer check, identical in kind to (d) — but the check now has something to catch:
before this fix, recomputing over EITHER `origin_version` value produced the SAME fingerprint (no
tamper was detectable at all); now the two recomputations diverge, exactly as intended.

**(e) Cross-workspace parent ref — fails closed.** Fixture (a) but with a
`parent_origin_refs: [{"origin_id": "pvo_<64 hex>", "origin_version": 1}]` entry naming an origin
that (per the service's own store) belongs to a different `workspace_id`. This validates
structurally (the schema cannot itself resolve cross-file workspace membership) but MUST be
rejected by the writing service before persistence — no partial write, no silently-dropped parent
ref, no promotion to root-origin. This mirrors `assertion_workspace.resolve_or_deny`'s fail-closed
contract (`WorkspaceWriteResolution(allowed=False, workspace_id=None, reason="workspace_context_missing")`)
applied to a parent-ref resolution instead of a workspace_id resolution.

**(f) Facet-rebuild parity.** Given fixture (a) persisted once, a facet builder computing
(for example) a catalog row's `origin_source_kind`/`origin_locator`/`origin_producer_tool` columns
must derive those three values *only* from the stored `provenance_origin` record. Deleting the
facet row and rebuilding it from the same canonical record MUST produce the identical three values
— the AC RPC-1 resilience test this document commits P2/P7 to writing.

## 5. Run/activity and receipt contract (RPC-1.2, AC RPC-2)

### 5.1 Normative rules

1. **Two-layer split.** `research_run_envelope.schema.yaml` is the identity/linkage layer
   (envelope id/version, activity kind, request/activity/run ids, optional origin/AOS refs).
   `search_activity_receipt.schema.yaml` is the durable content layer (exact query/purpose/scope,
   candidate-set digest, selection outcome). Every envelope has exactly one owning receipt
   (`envelope.activity_id` → `receipt.activity_id`); every receipt has exactly one owning envelope
   (`receipt.envelope_ref` → `envelope.envelope_id`+`envelope_version`). Neither schema duplicates
   the other's authoritative fields.
2. **Search-only activity is first-class.** `activity_kind: search_only` envelopes are structurally
   forced (`allOf` partition) to carry `planned_run_ref: null` — never a fabricated `run_id`.
   `activity_kind: planned_run` envelopes are structurally forced to carry a non-null
   `planned_run_ref`. No third state, no gap, no overlap. SOL-3: the literal is `planned_run`,
   spelled IDENTICALLY on `research_run_envelope.activity_kind` and
   `search_activity_receipt.activity_kind` — the receipt's `activity_kind` enum previously used the
   differently-spelled literal `planned`, which made the cross-record equality rule in item 6 below
   impossible to satisfy for any planned-run pair (a receipt could never actually equal its
   envelope's `activity_kind`). Both schemas now share one literal vocabulary.
3. **Exact scope, never inferred.** `search_activity_receipt.scope` (`provider`/`site`/`corpus`/
   `filters`/`time_window`) preserves exactly what the caller supplied. A service may never infer
   provider/site/corpus from returned result text.
4. **Complete, disjoint five-outcome partition, zero candidate-derived leakage on denial (SOL-4/7).**
   `selection_receipt.outcome` is exactly one of `selected` / `empty` / `denied` / `degraded` /
   `fallback`. Every outcome's cross-field null/non-null rule is enforced by the schema's `allOf`
   blocks, not left to convention:

   | outcome | `candidate_set_digest` | `selected_evidence_versions` | `source` | `catalog_generation_id` | `decided_at` | `denial_reason` | `degraded_reason` | `fallback_reason` |
   |---|---|---|---|---|---|---|---|---|
   | `selected` | non-null | ≥1 item | non-null | nullable | non-null | `null` | `null` | `null` |
   | `empty` | non-null | 0 items | non-null | nullable | non-null | `null` | `null` | `null` |
   | `denied` | `null` | 0 items | `null` | `null` | `null` | non-null (closed, single value) | `null` | `null` |
   | `degraded` | non-null | 0+ items | non-null | nullable | non-null | `null` | non-null | `null` |
   | `fallback` | non-null | ≥1 item | non-null | nullable | non-null | `null` | `null` | non-null |

   `empty` (SOL-7, new) is the authorized zero-candidate outcome — mirrors CARP's own
   `catalog_empty`, and is never conflated with `denied` (an `empty` receipt always names its
   `source` and carries a real `candidate_set_digest`; a `denied` receipt never does, SOL-4).
   `fallback` names a provider-fallback attempt that FOUND at least one candidate; a fallback
   attempt that finds nothing is reported as `empty`, not `fallback` — this is what makes the
   partition disjoint rather than ambiguous (the original submission's `fallback` could legally
   carry zero evidence, which collided with `empty`'s meaning once `empty` was added). `denied`'s
   `denial_reason` is now a CLOSED, single-value enum (`not_authorized_or_not_found`) — SOL-4's
   fix, detailed in item 5 below.
5. **One denial shape, one generic reason, zero candidate-derived leakage (SOL-4).** A receipt with
   `selection_receipt.outcome == denied` is schema-forced to `candidate_set_digest: null`,
   `selected_evidence_versions: []`, `selection_receipt.source: null`,
   `selection_receipt.catalog_generation_id: null` (closed in this revision — the original
   submission left this field unconstrained on denial, and a live schema check against that
   original schema accepted a denied receipt carrying a real catalog-generation value), and
   `selection_receipt.decided_at: null` (also newly closed). `denial_reason` is a single-member
   closed enum, `not_authorized_or_not_found` — deliberately uninformative so a denied receipt can
   never be used to distinguish resource-not-found, unauthorized, and cross-workspace denial from
   one another. `workspace_context_missing` (`assertion_workspace.resolve_or_deny`'s own reason
   code) NEVER appears in this field — see item 7 below (SOL-5).
6. **AOS refs live once, on the envelope, and are omittable (SOL-6).** `research_run_envelope.aos_refs`
   is the sole place project/intent/knowledge references appear; `search_activity_receipt.schema.yaml`
   intentionally has no such field. `aos_refs` is no longer in the envelope's top-level `required`
   list (the original submission required the key to always be present, even as `null` — SOL-6's
   canonical-absence fix makes top-level OMISSION the canonical shape; explicit `null` remains
   valid and equivalent). When present and non-null, every populated sub-field must be a non-blank
   string (`minLength: 1` — the original submission allowed `""`). See §9 for the full rationale,
   including why no per-kind regex `pattern` was added.
7. **Content-binding treatment matches `provenance_origin` (SOL-2).** `envelope_id` MUST equal
   `"rre_" + identity.fingerprint`; `activity_id` (on the receipt) MUST equal
   `"sar_" + identity.fingerprint`, computed the same way as `provenance_origin.origin_id` (§4.1
   rule 7). See §5.1a for the exact material-field lists and why `activity_id` is deliberately
   excluded from the ENVELOPE's own fingerprint (a circularity the original submission's design
   would otherwise create).
8. **Per-question membership survives the activity-level rebase (SOL-8), NOW ENFORCED, not merely
   permitted (SOL-8/23, round 2).** `selected_evidence_versions[]` entries carry an optional
   `selection_origin` discriminator (`catalog_planning` / `search`, defaulting to `search`-equivalent
   behavior when omitted). An entry with `selection_origin: catalog_planning` (a CARP evidence-plan
   rebase) MUST carry non-null `question_id` AND `decided_at` — round 1 left both merely optional,
   which meant a CARP-rebased entry could silently drop them with nothing to catch it (SOL-8/23's
   accepted attack). A plain `search`-outcome entry (the field omitted, the legacy-compatible
   default) never requires either. See §6 row 1 and §5.2(f).
9. **Receipt substitution is closed by a pair-level commitment PLUS a manifest-rooted tamper-evidence
   check, not cross-record equality alone (SOL-2/16, round 2; REDESIGNED round 3, SOL-2/16/22,
   RC-1).** §5.3's five cross-record equality checks prove an envelope and a receipt AGREE on
   `workspace_id`/`activity_kind`/`request_id`/`activity_id`/`envelope_ref` — but nothing in round 1
   proved the envelope's `activity_id` actually names the ONE receipt this envelope produced, as
   opposed to some other schema-valid receipt an attacker points it at (round 2's accepted attack:
   two different, independently hash-correct receipts both satisfied all five equalities against
   the same envelope). Round 2's fix (`receipt_commitment`, write-once, plus a sixth cross-record
   equality check) was itself UNSOUND: it let a version-1 envelope already carry a real,
   already-resolved `activity_id` at creation time, so the documented HONEST version-2 pair failed
   the round-2 §5.3 check 5 (round 3's accepted finding). **Round 3 redesigns the protocol with
   strict ordering and no circularity:**
   - **Envelope v1** is created at PLANNING time and carries **no receipt-linkage fields at all**
     — `activity_id`/`receipt_commitment` are structurally ABSENT (never merely `null`), enforced
     by the schema's `allOf` partition. `identity.material_fields` (§5.1a) is unchanged and computed
     entirely from v1's own content.
   - **The receipt** binds `(envelope_id, envelope_version: 1)` in its OWN `envelope_ref` — a fixed
     LITERAL, the version AT ACTIVITY TIME, never "whichever envelope version currently exists."
   - **Envelope v2** is written exactly once, atomically, at receipt-publication time, and is the
     FIRST record to carry `activity_id` + `receipt_commitment` TOGETHER. `envelope_id` stays
     v1-derived and version-invariant (no second, circular `identity.fingerprint`); `version_digest`
     (unchanged formula, §5.1b) is what covers the commitment — this is the "v2's own fingerprint"
     that proves the commitment, deliberately NOT `identity.fingerprint` itself, avoiding the exact
     circularity `activity_id`'s original exclusion (§5.1a) already avoided.
   - `envelope.receipt_commitment == receipt.identity.fingerprint` remains a SIXTH cross-record
     equality check (§5.3 rule 6), now stated relative to the receipt's ALWAYS-version-1
     `envelope_ref` rather than to "the currently-presented envelope's version" — this is what makes
     the honest v2 pair pass unconditionally (§5.3).
   - **What actually closes the receipt-substitution attack** is neither the equality checks nor
     `version_digest`'s self-consistency alone (an attacker who controls both files can always
     recompute a self-consistent forged pair) — it is the generation-manifest entry recorded ONCE,
     at LEGITIMATE promotion time (§17.7a, RC-2): a reader compares the CURRENTLY-STORED
     `version_digest` against the manifest's entry for `(envelope_id, envelope_version: 2)`, not
     merely against the record's own internal consistency. A byte-equality rule (v2's non-commitment
     fields MUST byte-equal the SAME payload retained on v1's own immutable file, §5.1b) is a
     SEPARATE, complementary invariant that closes a DIFFERENT tampering vector (mutating a
     v1-inherited fact under cover of the version bump) — stated honestly as two checks closing two
     different attacks, not one check closing both. See §5.1a/§5.1b/§17.7a for the full mechanism,
     storage layout, and the re-run substitution-attack evidence.
10. **Blank strings are never a valid "present" value (SOL-7/24, round 2).** Every required
    non-null string in an outcome arm — `source`, `degraded_reason`, `fallback_reason` on
    `search_activity_receipt.schema.yaml`, and every free-text descriptive string across the four
    NEW schemas this document introduces — now carries `minLength: 1`. Round 2's accepted attack:
    `fallback_reason: ""`/`degraded_reason: ""`/`source: ""` satisfied every "non-null" check in the
    outcome `allOf` blocks (§5.1 rule 4) while disclosing nothing — an empty string is not the same
    fact as a populated one, and the schema failed to say so.
11. **Version bumps are provable, not free (SOL-1/22, round 2).** Round 1 left `envelope_version`
    (like `provenance_origin.origin_version`, §4.1 rule 7) outside its record's own content-binding —
    a version number could change with the fingerprint held constant (round 2's accepted attack:
    `origin_version: 1 -> 999`, hash unchanged). `provenance_origin.identity.material_fields` now
    includes `origin_version` directly (§4.1 rule 7, revised); `research_run_envelope` instead gains
    a `version_digest` field (a whole-record integrity digest recomputed at every version, §5.1b) —
    the two mechanisms differ because envelope, unlike origin, has an established legitimate
    version-bump flow (`receipt_commitment`'s write-once transition, rule 9 above) that depends on
    `envelope_id` staying stable across that ONE bump; see §5.1b for the full rationale for this
    deliberate asymmetry.
12. **AOS refs have exactly one absence encoding (SOL-6/22, round 2).** `{}` and a partial-null
    object (e.g. `{"project_ref": null}`) were both schema-valid in round 1 and each minted a
    DIFFERENT `envelope_id` for the identical "no AOS context" fact — closed by `minProperties: 1`
    (rejects `{}`) plus removing `null` from each of `project_ref`/`intent_ref`/`knowledge_ref`'s own
    type (a caller with no value for a given sub-ref OMITS that key rather than nulling it). See §9.

### 5.1a Identity computation order (SOL-2, new — resolves a circularity the original design implied)

`research_run_envelope.identity.material_fields` is `[workspace_id, activity_kind, request_id,
planned_run_ref, parent_run_ref, origin_ref, aos_refs, created_at]` — it does **not** include
`activity_id`. `search_activity_receipt.identity.material_fields` is `[workspace_id, activity_kind,
request_id, query, purpose, scope, candidate_set_digest, selected_evidence_versions,
selection_receipt, envelope_ref, created_at]` — it **does** include `envelope_ref` (which carries
`envelope_id`). If the envelope's own fingerprint also depended on `activity_id` (the receipt's
content-derived id), the two records' identities would be mutually dependent with no valid
computation order — the receipt needs `envelope_id` to exist first (via `envelope_ref`), but the
envelope would need `activity_id` to exist first too. This is why `activity_id` is excluded from
the envelope's own material fields; the correct, non-circular write order a P2 implementation MUST
follow is:

1. Compute `envelope_id = "rre_" + fingerprint({workspace_id, activity_kind, request_id,
   planned_run_ref, parent_run_ref, origin_ref, aos_refs, created_at})`. This does not require
   knowing the receipt at all. **Persist this as `envelope_version: 1` — SOL round 3 (RC-1): this v1
   record carries NO `activity_id` and NO `receipt_commitment` field at all (structurally absent,
   never merely `null`), because neither exists yet at planning time.** This is the ONLY write this
   step performs; the activity itself (query/selection/outcome) has not necessarily concluded yet.
2. Once the activity concludes (candidate digest/selection/selection_receipt now known), compute
   `activity_id = "sar_" + fingerprint({workspace_id, activity_kind, request_id, query, purpose,
   scope, candidate_set_digest, selected_evidence_versions, selection_receipt, envelope_ref:
   {envelope_id, envelope_version: 1}, created_at})`, using the `envelope_id` from step 1 and a
   LITERAL `envelope_version: 1` in `envelope_ref` (SOL round 3, RC-1 — never "whichever envelope
   version currently exists"; the envelope is, by construction, still at version 1 at this instant,
   since v2 does not exist until step 4 below). This requires the terminal outcome to already be
   known — consistent with "durable, immutable... written once... after the terminal outcome is
   known" (§5's own framing; a receipt is never written before its activity concludes).
3. Persist the receipt. Its `envelope_ref` field is exactly `{envelope_id, envelope_version: 1}`,
   fixed permanently at this step — it is NEVER rewritten to name a later envelope version.
4. Persist a SECOND, NEW envelope file at `envelope_version: 2`, sharing every v1 field
   byte-for-byte (§5.1b's byte-equality rule), with `activity_id` (the value from step 2) and
   `receipt_commitment` (the receipt's bare `identity.fingerprint`, the SAME value as `activity_id`
   minus its `sar_` prefix) BOTH set together, for the first time, in this ONE record. `envelope_id`
   is UNCHANGED from step 1 (`identity.material_fields` never included either field — see §5.1b).

Substituting `activity_id` alone on an already-written v2 envelope, with every other envelope field
unchanged, does NOT change `envelope_id` under this design (by construction — it is excluded from
the fingerprint). That substitution is instead caught by the cross-record equality rule (§5.3) and
the generation-manifest check (§17.7a), not by hash inclusion in `identity.fingerprint`: a forged
`activity_id` on the envelope fails to resolve to any receipt whose own `envelope_ref` names this
exact `envelope_id`, and the reading/writing service MUST treat that as a denial-class integrity
failure, never a silently-followed reference.

### 5.1b Receipt commitment and version protocol (SOL-2/16, SOL-1/22, round 2; REDESIGNED round 3, SOL-2/16/22, RC-1 — normative)

Round 2 found that cross-record equality (§5.3, five checks) proves an envelope and a receipt AGREE
on shared fields, but proves nothing about whether the envelope's `activity_id` names the RECEIPT
THIS ENVELOPE ACTUALLY PRODUCED as opposed to any other schema-valid receipt (SOL-2/16's accepted
attack: two independently hash-correct receipts each satisfied all five equalities against the same
envelope after only the envelope's own `activity_id` was edited). Round 2's fix (`receipt_commitment`,
`null` at v1, write-once to non-null at v2, plus a sixth cross-record equality check) was found
**UNSOUND this round**: it let v1 already carry a real, already-resolved `activity_id` at
envelope-creation time, which made the documented HONEST v2 pair itself FAIL round 2's own §5.3
check 5 (the receipt's `envelope_ref` named version 1 while the check compared against whichever
envelope version was currently being read — version 2, in the honest post-commitment case). This
section freezes the ROUND 3 redesign, with strict ordering and no circularity.

**The mechanism.**

1. At envelope-creation time (§5.1a step 1), the envelope is persisted at `envelope_version: 1` with
   **NO `activity_id` and NO `receipt_commitment` field present at all** — not `null`, structurally
   ABSENT, enforced by the schema's `allOf` partition (`research_run_envelope.schema.yaml`). This is
   "no receipt fields at planning time," the literal fix for the round-3 UNSOUND finding: a v1
   record can never be confused with a post-commitment record because it cannot even express
   `activity_id`/`receipt_commitment`.
2. The receipt is computed and persisted (§5.1a steps 2–3) with `envelope_ref: {envelope_id,
   envelope_version: 1}` — a FIXED LITERAL, never rewritten. `search_activity_receipt.schema.yaml`
   now enforces this with `envelope_ref.envelope_version: const: 1`.
3. A SEPARATE, NEW envelope file is written, EXACTLY ONCE, atomically, at `envelope_version: 2`,
   sharing every v1 field byte-for-byte (see the byte-equality rule below), with `activity_id`
   (the receipt's `"sar_" + identity.fingerprint`) AND `receipt_commitment` (the receipt's bare
   `identity.fingerprint`) BOTH set TOGETHER, for the first time, in this one record. This is the
   ONLY permitted post-creation mutation to an envelope record; v1's file is NEVER edited in place
   and remains immutable, retained on disk alongside v2 (storage layout below).
4. `envelope_version`, `activity_id`, and `receipt_commitment` are ALL deliberately EXCLUDED from
   `identity.material_fields` (§5.1a's `[workspace_id, activity_kind, request_id, planned_run_ref,
   parent_run_ref, origin_ref, aos_refs, created_at]` list is UNCHANGED across v1 and v2 — this
   round does NOT introduce a second, version-dependent `identity.fingerprint` formula).
   Consequence: `envelope_id` is IDENTICAL between version 1 and version 2 — the v2 write does NOT
   mint a new `envelope_id`, so the receipt's own `envelope_ref` (fixed at receipt-creation time,
   naming version 1) remains a valid, resolvable reference to "the envelope" even after version 2
   exists. A reader wanting the CURRENT state (whether the commitment has landed yet) reads the
   envelope file at the HIGHEST `envelope_version` sharing this `envelope_id`.
5. `version_digest` — OPTIONAL field, UNCHANGED formula from round 2 — is
   `sha256-canonical-json-v1` over EVERY envelope field at the CURRENT version (`envelope_id`,
   `envelope_version`, `workspace_id`, `activity_kind`, `request_id`, `activity_id`,
   `planned_run_ref`, `parent_run_ref`, `origin_ref`, `aos_refs`, `created_at`,
   `receipt_commitment` — `.get(field)` semantics, so v1's absent `activity_id`/`receipt_commitment`
   canonicalize as `null` the same way an explicitly-null field would). **This is what "v2's own
   fingerprint covers the commitment" means concretely** (RC-1's framing): NOT a second
   `identity.fingerprint` (which stays circularity-free and version-invariant by construction), but
   `version_digest` — which necessarily differs at v2 from v1 precisely because `activity_id`/
   `receipt_commitment` newly exist there. A version bump that changes these fields without a
   correspondingly new, matching `version_digest` is detectable tampering by recomputation.
6. **Byte-equality rule (SOL round 3, RC-1, NEW, service-enforced, normative).** v2's payload over
   EXACTLY the 8 fields in `identity.material_fields` (`workspace_id`, `activity_kind`,
   `request_id`, `planned_run_ref`, `parent_run_ref`, `origin_ref`, `aos_refs`, `created_at`) MUST
   byte-equal the SAME payload retained on v1's own immutable file — verified by recomputing
   `identity.fingerprint` from v1's retained record and confirming it equals v2's own
   `identity.fingerprint` field (which, per point 4, is unchanged from v1's). This is a SEPARATE,
   complementary invariant from the manifest-rooted check below — it closes a DIFFERENT tampering
   vector (mutating a v1-inherited fact, e.g. `workspace_id` or `created_at`, under cover of the one
   permitted version bump), not the receipt-substitution attack itself (stated honestly: an attacker
   who ONLY changes `activity_id`/`receipt_commitment`, leaving the 8 shared fields untouched, does
   NOT trip this check — see point 7 for what actually closes that attack).
7. **What actually closes the receipt-substitution attack: the generation-manifest entry, not
   self-consistency (§17.7a, RC-2).** An attacker who controls both the envelope-v2 file and a
   forged receipt file can always recompute a self-consistent pair (a new `receipt_commitment`
   matching a new forged receipt's own `identity.fingerprint`, a matching `activity_id`, and a
   freshly, correctly recomputed `version_digest` over all of it) — no schema check or
   self-recomputation catches this, because the forged pair is internally honest. The closing
   mechanism is external: at the ONE legitimate v2 promotion, a generation-manifest entry
   `{record_kind: "research_run_envelope", record_id: envelope_id, version: 2, version_digest,
   fingerprint: receipt_commitment}` is written ONCE, atomically, alongside the promotion (§17.7a).
   A reader MUST compare the CURRENTLY-STORED v2 record's recomputed `version_digest` against this
   manifest entry, not merely confirm the record is internally self-consistent — an attacker who
   later overwrites the v2 file with a different, self-consistent forgery produces a
   `version_digest` that no longer matches the ALREADY-RECORDED, append-only manifest entry, and the
   mismatch is what rejects the forgery.

**Storage layout (SOL round 3, RC-1, "name the storage layout").** Reusing the SAME per-version-file
convention `canonical_claim.schema.yaml`'s entity-id/per-version split already establishes (§17.7):
`<provenance-envelope-storage-root>/envelopes/<envelope_id>/v1.yaml` and
`<same-root>/envelopes/<envelope_id>/v2.yaml` — two separate, immutable files under a stable
per-envelope directory (`services/provenance_envelope.py` owns this root, §17.9/N1). "Recompute v1
hash from the v1 record retained in the envelope directory" (point 6 above) means literally: read
`v1.yaml`, recompute `identity.fingerprint` over its own 8 material fields, and compare.

**Why envelope uses `version_digest` and origin instead folds `origin_version` into
`identity.material_fields` (§4.1 rule 7) — a deliberate, documented asymmetry.** `provenance_origin`
has no established legitimate version-bump flow anywhere in this document — an origin record is
either right the first time or it is an entirely new record; `origin_version` joining
`identity.material_fields` directly (so `origin_id` itself changes on any version change) is the
simplest fix and breaks nothing (§4.1 rule 7). `research_run_envelope`, however, NOW has one
legitimate version-bump flow (the v1→v2 write-once transition, rule 9 above) that specifically
DEPENDS on `envelope_id` staying stable across the bump (so the receipt's already-fixed
`envelope_ref` keeps resolving). Folding `envelope_version` into `identity.material_fields` the same
way `provenance_origin` does would break that dependency (the receipt's `envelope_ref` would need to
name a moving target). `version_digest` achieves the identical goal — a version bump cannot occur
without being cryptographically re-provable — without this side effect, and it is the SAME mechanism
this round also applies to `canonical_claim`/`inference_record` (§15.2, SOL-12/18), so the whole
contract now has ONE uniform "version_digest" concept for every record whose stable identity must
survive a version change, applied consistently wherever that need arises.

**Worked test vectors (RECOMPUTED this fix cycle for the round-3 redesign, §22b).** Reusing §5.2
fixture (a)'s envelope (`rre_dc326b70d45545a1beacf139147f81fe7de2b4441295c55006770a339274e93b`) and
its paired receipt (`sar_6da0e0a97329e5c4ba6ab7da2b7a6072d11b1d7c01d4f2bb33534590ddb1b0ba`):

- **v1 identity.fingerprint** (UNCHANGED from round 2 — `identity.material_fields` was never
  affected): `dc326b70d45545a1beacf139147f81fe7de2b4441295c55006770a339274e93b`; confirmed
  `envelope_id == "rre_" + fingerprint`.
- **v1 version_digest** (RECOMPUTED — round 2's worked value, `ee51e918...`, was computed against a
  v1 record that WRONGLY already carried a real `activity_id`; the round-3 v1 record correctly
  carries neither `activity_id` nor `receipt_commitment` at all, canonicalizing both as `null` via
  `.get(field)`): `version_digest = 6f4186111fe8d67eb135164a94db186e33f3393d32ad27d539aaf8db0c5ed6af`.
- **v2 version_digest** (UNCHANGED from round 2's value — the v2 payload's actual field VALUES are
  identical either way, since the receipt's content did not change): `version_digest =
  c1ea2b059da4ed1efa10ca2f25392fca1f7d7c8fd2c87086bef009e84fa2c3e9` (`activity_id =
  sar_6da0e0a97329e5c4ba6ab7da2b7a6072d11b1d7c01d4f2bb33534590ddb1b0ba`, `receipt_commitment =
  6da0e0a97329e5c4ba6ab7da2b7a6072d11b1d7c01d4f2bb33534590ddb1b0ba` — the receipt's own bare
  fingerprint). Both versions share `envelope_id = rre_dc326b70d45545a1beacf139147f81fe7de2b4441295c55006770a339274e93b`
  (confirmed: `identity.material_fields` is unaffected by either field; only `version_digest`
  differs between v1 and v2).
- **Substitution check (the exact round-3 UNSOUND-ruling attack, re-run and confirmed REJECTED via
  the manifest, not via self-consistency):** a forged v2 claiming a DIFFERENT receipt's fingerprint
  as `receipt_commitment` (`88c90...` instead of the real `6da0e0a9...`, with a matching forged
  `activity_id = sar_88c90...`) recomputes its OWN internally-self-consistent `version_digest =
  f3d69cd570ef656be927cf44d8dd5aa0799505245bbad7e7d50207df7b1259f8` — this does NOT, by itself,
  differ from a value the forger controls (a forger who also recomputes `version_digest` correctly
  produces a self-consistent record). What rejects it: this recomputed value does NOT equal the
  `c1ea2b05...` value recorded in the generation-manifest entry at the ONE legitimate v2 promotion
  (§17.7a) — the manifest comparison, not schema validation or self-recomputation, is what catches
  the substitution. Confirmed by direct computation: `f3d69cd5... != c1ea2b05...`.

  **K-2 disposition (P2, RPC-2.2).** This vector is explicitly **NON-NORMATIVE / illustrative-only**:
  `88c90...` is a truncated placeholder, not a complete 64-hex value, and the "DIFFERENT receipt"
  it's forged from is never itself published as a full record — so, unlike the worked v1/v2 pair
  immediately above (which IS a complete, independently recomputable preimage), this specific forged
  variant cannot be reproduced byte-for-byte from this document alone. The normative claim it
  illustrates — "a generation-manifest mismatch, not schema validation or self-consistency, is what
  rejects a forged commitment" — is independently proven by
  `provenance_envelope.py::create_receipt_and_promote`'s own manifest-comparison test (see
  `tests/unit/test_provenance_envelope.py`), which publishes a complete, legitimate v1→v2→manifest
  triple and then confirms a forged `receipt_commitment` substituted onto a copy of the legitimate v2
  fails that same comparison. Treat this paragraph as narrative color, not a pinned test vector.
- **Byte-equality check (SOL round 3, RC-1, re-run and confirmed it does NOT fire on the pure
  receipt-substitution attack above — stated honestly, per point 6):** the forged v2's 8
  `identity.material_fields` values are IDENTICAL to v1's retained record in this specific attack
  (only `activity_id`/`receipt_commitment` were forged), so `identity.fingerprint` recomputes
  identically and this check alone does not reject it. This confirms the check is a SEPARATE
  invariant (closing v1-inherited-fact tampering, not receipt substitution) rather than a redundant
  second barrier against the same attack — see point 6/7 above for the honest division of labor.
- **Honest v2 pair now PASSES §5.3 end-to-end (the exact UNSOUND-ruling regression, re-run and
  confirmed FIXED):** check 5 (`receipt.envelope_ref == {envelope_id, envelope_version: 1}`) is now
  a fixed-literal comparison, satisfied unconditionally by the honest v2 pair above regardless of
  which envelope version a reader currently holds; check 6
  (`envelope.receipt_commitment == receipt.identity.fingerprint`) holds
  (`6da0e0a9... == 6da0e0a9...`); checks 1–4 hold as before (workspace_id/activity_kind/request_id/
  activity_id all agree).

**Both versions retained — schema validation, both fixtures.** Version 1 (no `activity_id`, no
`receipt_commitment`) and version 2 (both required, non-null) of this envelope were each
independently validated against `schemas/research_run_envelope.schema.yaml` with zero errors as part
of this fix cycle, alongside four negative counter-fixtures confirmed REJECTED: v1 with `activity_id`
present, v1 with `receipt_commitment: null` present, v2 missing `activity_id`, and v2 with
`receipt_commitment: null` (§22b).

### 5.2 Examples

**(a) Positive — planned research run (envelope v1, planning-time — SOL round 3, RC-1: NO
receipt-linkage fields present at all).**

```json
// research_run_envelope, envelope_version: 1
{
  "schema_version": "1.0", "type": "research_run_envelope",
  "envelope_id": "rre_dc326b70d45545a1beacf139147f81fe7de2b4441295c55006770a339274e93b",
  "envelope_version": 1, "workspace_id": "default", "activity_kind": "planned_run",
  "request_id": "req-42",
  "planned_run_ref": {"run_id": "run-2026-07-28-001"},
  "parent_run_ref": null, "origin_ref": null,
  "created_at": "2026-07-28T12:10:00Z",
  "identity": {
    "algorithm": "sha256-canonical-json-v1",
    "fingerprint": "dc326b70d45545a1beacf139147f81fe7de2b4441295c55006770a339274e93b",
    "material_fields": ["workspace_id", "activity_kind", "request_id", "planned_run_ref", "parent_run_ref", "origin_ref", "aos_refs", "created_at"]
  }
}
```

```json
// search_activity_receipt (owned by the envelope above; envelope_ref names v1 as a fixed literal)
{
  "schema_version": "1.0", "type": "search_activity_receipt",
  "activity_id": "sar_6da0e0a97329e5c4ba6ab7da2b7a6072d11b1d7c01d4f2bb33534590ddb1b0ba",
  "workspace_id": "default", "activity_kind": "planned_run", "request_id": "req-42",
  "query": "pediatric CBC reference intervals", "purpose": "evidence gathering",
  "scope": {"provider": "pubmed", "site": null, "corpus": null, "filters": {}, "time_window": {"from": null, "to": null}},
  "candidate_set_digest": "3333333333333333333333333333333333333333333333333333333333333333",
  "selected_evidence_versions": [{"assertion_id": "ast_4444444444444444444444444444444444444444444444444444444444444444", "assertion_version": 1, "question_id": null, "decided_at": null}],
  "selection_receipt": {"outcome": "selected", "source": "pubmed", "catalog_generation_id": null, "decided_at": "2026-07-28T12:10:05Z", "denial_reason": null, "degraded_reason": null, "fallback_reason": null},
  "envelope_ref": {"envelope_id": "rre_dc326b70d45545a1beacf139147f81fe7de2b4441295c55006770a339274e93b", "envelope_version": 1},
  "created_at": "2026-07-28T12:10:05Z",
  "identity": {
    "algorithm": "sha256-canonical-json-v1",
    "fingerprint": "6da0e0a97329e5c4ba6ab7da2b7a6072d11b1d7c01d4f2bb33534590ddb1b0ba",
    "material_fields": ["workspace_id", "activity_kind", "request_id", "query", "purpose", "scope", "candidate_set_digest", "selected_evidence_versions", "selection_receipt", "envelope_ref", "created_at"]
  }
}
```

```json
// research_run_envelope, envelope_version: 2 (written ONCE, atomically, at receipt-publication
// time -- the ONLY permitted post-creation mutation; v1 above remains retained, unedited, at
// <root>/envelopes/<envelope_id>/v1.yaml)
{
  "schema_version": "1.0", "type": "research_run_envelope",
  "envelope_id": "rre_dc326b70d45545a1beacf139147f81fe7de2b4441295c55006770a339274e93b",
  "envelope_version": 2, "workspace_id": "default", "activity_kind": "planned_run",
  "request_id": "req-42",
  "activity_id": "sar_6da0e0a97329e5c4ba6ab7da2b7a6072d11b1d7c01d4f2bb33534590ddb1b0ba",
  "planned_run_ref": {"run_id": "run-2026-07-28-001"},
  "parent_run_ref": null, "origin_ref": null,
  "created_at": "2026-07-28T12:10:00Z",
  "receipt_commitment": "6da0e0a97329e5c4ba6ab7da2b7a6072d11b1d7c01d4f2bb33534590ddb1b0ba",
  "version_digest": "c1ea2b059da4ed1efa10ca2f25392fca1f7d7c8fd2c87086bef009e84fa2c3e9",
  "identity": {
    "algorithm": "sha256-canonical-json-v1",
    "fingerprint": "dc326b70d45545a1beacf139147f81fe7de2b4441295c55006770a339274e93b",
    "material_fields": ["workspace_id", "activity_kind", "request_id", "planned_run_ref", "parent_run_ref", "origin_ref", "aos_refs", "created_at"]
  }
}
```

Note `activity_kind: "planned_run"` on BOTH records now (SOL-3), and cross-record equality holds
exactly against EITHER the v1 or the v2 envelope: `envelope.workspace_id == receipt.workspace_id`,
`envelope.activity_kind == receipt.activity_kind`, `envelope.request_id == receipt.request_id`, and
`receipt.envelope_ref == {envelope.envelope_id, envelope_version: 1}` (a fixed literal, SOL round
3) — plus, once v2 exists, `envelope.activity_id == receipt.activity_id` and
`envelope.receipt_commitment == receipt.identity.fingerprint` (§5.3 rules 4/6). All three instances
(v1, receipt, v2) were schema-validated (Draft 2020-12) as a set as part of this fix cycle, alongside
four negative counter-fixtures (§22b): v1 with `activity_id` present (REJECTED), v1 with
`receipt_commitment: null` present (REJECTED), v2 missing `activity_id` (REJECTED), v2 with
`receipt_commitment: null` (REJECTED). v1 above is this envelope's planning-time state (no
receipt-linkage fields at all, SOL round 3, RC-1); §5.1b works this exact pair through the full
v1→v2 mechanism, worked `version_digest` values for both versions, the byte-equality rule, and the
generation-manifest check that actually closes the receipt-substitution attack (§17.7a).

**(b) Positive — search-only activity, empty outcome (SOL-7's new outcome, replaces the original
submission's fixture (b), which used `outcome: selected`; renumbered here to also demonstrate
`empty`).**

```json
// research_run_envelope, envelope_version: 1 (SOL round 3, RC-1: no receipt-linkage fields at
// planning time)
{
  "schema_version": "1.0", "type": "research_run_envelope",
  "envelope_id": "rre_6ddd3b3fd9dde2992eda19809102139807bc78056caa4a998572e45a039d4450",
  "envelope_version": 1, "workspace_id": "default", "activity_kind": "search_only",
  "request_id": "req-77",
  "planned_run_ref": null, "parent_run_ref": null, "origin_ref": null,
  "created_at": "2026-07-28T13:00:00Z",
  "identity": {
    "algorithm": "sha256-canonical-json-v1",
    "fingerprint": "6ddd3b3fd9dde2992eda19809102139807bc78056caa4a998572e45a039d4450",
    "material_fields": ["workspace_id", "activity_kind", "request_id", "planned_run_ref", "parent_run_ref", "origin_ref", "aos_refs", "created_at"]
  }
}
```

(The v2 promotion, carrying `activity_id`/`receipt_commitment` together per §5.1b, is elided here —
see fixture (a) for the full worked v1→v2 pair.)

```json
// search_activity_receipt — outcome: empty (authorized, zero candidates)
{
  "schema_version": "1.0", "type": "search_activity_receipt",
  "activity_id": "sar_5372259608299116c3ee04abc3fd1069f49fae32007f54df3fd1cf3fd345e35d",
  "workspace_id": "default", "activity_kind": "search_only", "request_id": "req-77",
  "query": "test query with zero matches", "purpose": null,
  "scope": {"provider": "pubmed", "site": null, "corpus": null},
  "candidate_set_digest": "7777777777777777777777777777777777777777777777777777777777777777",
  "selected_evidence_versions": [],
  "selection_receipt": {"outcome": "empty", "source": "pubmed", "catalog_generation_id": null, "decided_at": "2026-07-28T13:00:05Z", "denial_reason": null, "degraded_reason": null, "fallback_reason": null},
  "envelope_ref": {"envelope_id": "rre_6ddd3b3fd9dde2992eda19809102139807bc78056caa4a998572e45a039d4450", "envelope_version": 1},
  "created_at": "2026-07-28T13:00:05Z",
  "identity": {
    "algorithm": "sha256-canonical-json-v1",
    "fingerprint": "5372259608299116c3ee04abc3fd1069f49fae32007f54df3fd1cf3fd345e35d",
    "material_fields": ["workspace_id", "activity_kind", "request_id", "query", "purpose", "scope", "candidate_set_digest", "selected_evidence_versions", "selection_receipt", "envelope_ref", "created_at"]
  }
}
```

The paired receipt is discoverable and fetchable through governed `research_run_discovery.py`
list/fetch with no `planned_run_id` anywhere on the envelope or receipt — RPC-FR-2's explicit
success metric. Note `candidate_set_digest`/`selection_receipt.source` are both non-null even
though `selected_evidence_versions` is empty — `empty` is an authorized outcome with a real
evaluated candidate set, never confusable with `denied`.

**(c) Canonical post-authorization denial — the ONE public denial shape (SOL-4/5/6).**

```json
// research_run_envelope, envelope_version: 1 (SOL round 3, RC-1: no receipt-linkage fields at
// planning time)
{
  "schema_version": "1.0", "type": "research_run_envelope",
  "envelope_id": "rre_2f140510d31e2380b03290aa26c92f4dce1612b72f5da66d40d822e8c5e4eec0",
  "envelope_version": 1, "workspace_id": "default", "activity_kind": "search_only",
  "request_id": null,
  "planned_run_ref": null, "parent_run_ref": null, "origin_ref": null,
  "created_at": "2026-07-28T13:05:00Z",
  "identity": {
    "algorithm": "sha256-canonical-json-v1",
    "fingerprint": "2f140510d31e2380b03290aa26c92f4dce1612b72f5da66d40d822e8c5e4eec0",
    "material_fields": ["workspace_id", "activity_kind", "request_id", "planned_run_ref", "parent_run_ref", "origin_ref", "aos_refs", "created_at"]
  }
}
```

```json
// search_activity_receipt — outcome: denied
{
  "schema_version": "1.0", "type": "search_activity_receipt",
  "activity_id": "sar_18d87fcbcd4b7c286e7e52fd4ca4effaab80f00187ec88dac85922a2a62ba623",
  "workspace_id": "default", "activity_kind": "search_only", "request_id": null,
  "query": "test query", "purpose": null,
  "scope": {"provider": null, "site": null, "corpus": null},
  "candidate_set_digest": null, "selected_evidence_versions": [],
  "selection_receipt": {"outcome": "denied", "source": null, "catalog_generation_id": null, "decided_at": null, "denial_reason": "not_authorized_or_not_found", "degraded_reason": null, "fallback_reason": null},
  "envelope_ref": {"envelope_id": "rre_2f140510d31e2380b03290aa26c92f4dce1612b72f5da66d40d822e8c5e4eec0", "envelope_version": 1},
  "created_at": "2026-07-28T13:05:00Z",
  "identity": {
    "algorithm": "sha256-canonical-json-v1",
    "fingerprint": "18d87fcbcd4b7c286e7e52fd4ca4effaab80f00187ec88dac85922a2a62ba623",
    "material_fields": ["workspace_id", "activity_kind", "request_id", "query", "purpose", "scope", "candidate_set_digest", "selected_evidence_versions", "selection_receipt", "envelope_ref", "created_at"]
  }
}
```

This ONE shape (SOL-6's "freeze ONE public denial envelope") is used for a not-found, unauthorized,
or cross-workspace denial — the reader cannot tell which of the three occurred, by design. This
envelope/receipt pair is created only because THIS denial happened *after* workspace resolution
succeeded (`workspace_id: "default"` is real and resolved) — see item (c-1) below for the case
where resolution itself fails, which never reaches this shape at all.

**(c-1) Pre-workspace-resolution denial is EPHEMERAL — never a durable receipt (SOL-5).** The
original submission's denial fixture claimed `denial_reason: "workspace_context_missing"` while
still stamping a durable `workspace_id: "default"` and minting real envelope/activity IDs. That is
impossible to produce honestly: shipped `assertion_workspace.resolve_or_deny(workspace_id)` returns
`WorkspaceWriteResolution(allowed=False, workspace_id=None, reason="workspace_context_missing")`
for exactly that failure mode — `workspace_id` is `None`, not `"default"`, and no writer can
attach a governed envelope/receipt without first calling `resolve_or_deny` successfully (standing
directive 2). **Normative rule:** a workspace-resolution failure (missing/blank workspace context)
is an ephemeral, API-response-only denial — a bare `{"denied": true, "reason":
"not_authorized_or_not_found"}`-shaped response (or equivalent), never written to disk, never
assigned an `envelope_id`/`activity_id`, never referencing a `provenance_origin`. Canonical
`research_run_envelope`/`search_activity_receipt` records are created ONLY after
`resolve_or_deny` (or the HTTP-layer `require_workspace_scope` equivalent) succeeds — every durable
receipt this schema family can ever produce, including every `outcome: denied` receipt like fixture
(c) above, necessarily has a real, resolved `workspace_id`. This is why `denial_reason`'s closed
enum (§5.1 rule 5) never includes `workspace_context_missing` as a value: that code names a failure
mode that, by construction, never reaches a durable receipt.

**(d) Degraded — best-effort selection under a documented condition, possibly zero evidence
(SOL-7).**

```json
{
  "schema_version": "1.0", "type": "search_activity_receipt",
  "activity_id": "sar_b6618d4af571f9998584054bc50b40bcb14062eac54cd677ad572f8e4bf08c39",
  "workspace_id": "default", "activity_kind": "search_only", "request_id": "req-99",
  "query": "test query", "purpose": null,
  "scope": {"provider": "pubmed", "site": null, "corpus": null},
  "candidate_set_digest": "8888888888888888888888888888888888888888888888888888888888888888",
  "selected_evidence_versions": [],
  "selection_receipt": {"outcome": "degraded", "source": "pubmed", "catalog_generation_id": null, "decided_at": "2026-07-28T13:10:05Z", "denial_reason": null, "degraded_reason": "provider_timeout_partial_result", "fallback_reason": null},
  "envelope_ref": {"envelope_id": "rre_67dbfecde0762481e51b88603e201e9350622ddf05e3b900452e2fadbfd20040", "envelope_version": 1},
  "created_at": "2026-07-28T13:10:05Z",
  "identity": {
    "algorithm": "sha256-canonical-json-v1",
    "fingerprint": "b6618d4af571f9998584054bc50b40bcb14062eac54cd677ad572f8e4bf08c39",
    "material_fields": ["workspace_id", "activity_kind", "request_id", "query", "purpose", "scope", "candidate_set_digest", "selected_evidence_versions", "selection_receipt", "envelope_ref", "created_at"]
  }
}
```

`degraded_reason` non-null (required), `selected_evidence_versions` legitimately empty (a degraded
activity that still found nothing usable) — this is explicitly permitted, unlike `denied`'s
forced-empty state, because `candidate_set_digest`/`source`/`decided_at` remain non-null: a
candidate set WAS evaluated, under a degraded condition, and simply yielded nothing confirmable.

**(e) Fallback — a successful catalog-then-discovery provider fallback, with per-question
membership (SOL-8).**

```json
{
  "schema_version": "1.0", "type": "search_activity_receipt",
  "activity_id": "sar_4cfe010296236bcb40ff4ee422f65a9445a61106f8c6b4078e6ad3536fb8dd65",
  "workspace_id": "default", "activity_kind": "search_only", "request_id": "req-99",
  "query": "test query", "purpose": null,
  "scope": {"provider": "web_discovery", "site": null, "corpus": null},
  "candidate_set_digest": "9999999999999999999999999999999999999999999999999999999999999999",
  "selected_evidence_versions": [
    {"assertion_id": "ast_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "assertion_version": 1, "question_id": "q1", "decided_at": "2026-07-28T13:11:00Z"}
  ],
  "selection_receipt": {"outcome": "fallback", "source": "web_discovery", "catalog_generation_id": null, "decided_at": "2026-07-28T13:11:05Z", "denial_reason": null, "degraded_reason": null, "fallback_reason": "catalog_residual_then_discovery_fallback"},
  "envelope_ref": {"envelope_id": "rre_67dbfecde0762481e51b88603e201e9350622ddf05e3b900452e2fadbfd20040", "envelope_version": 1},
  "created_at": "2026-07-28T13:11:05Z",
  "identity": {
    "algorithm": "sha256-canonical-json-v1",
    "fingerprint": "4cfe010296236bcb40ff4ee422f65a9445a61106f8c6b4078e6ad3536fb8dd65",
    "material_fields": ["workspace_id", "activity_kind", "request_id", "query", "purpose", "scope", "candidate_set_digest", "selected_evidence_versions", "selection_receipt", "envelope_ref", "created_at"]
  }
}
```

`fallback_reason` non-null (required, SOL-7 closes the gap where the original submission's doc
text claimed this was "required" but no field enforced it). `selected_evidence_versions[0]` carries
`question_id: "q1"` and its own `decided_at` — a CARP evidence-plan rebase onto this activity-level
array preserves exactly which question this selection answers (SOL-8), even though the array is
otherwise flat.

**(f) `selection_origin` discriminator, round 2 (SOL-8/23) — a CARP-rebased entry now REQUIRED to
carry `question_id`/`decided_at`, not merely permitted to.**

```json
{
  "schema_version": "1.0", "type": "search_activity_receipt",
  "activity_id": "sar_2f41acf4b46b25bff3484f2254745c02535c90beaf068c4744fed6207eca0c40",
  "workspace_id": "default", "activity_kind": "search_only", "request_id": "req-100",
  "query": "test query for catalog-planning rebase", "purpose": null,
  "scope": {"provider": "catalog", "site": null, "corpus": null},
  "candidate_set_digest": "aaaa000000000000000000000000000000000000000000000000000000000000",
  "selected_evidence_versions": [
    {"assertion_id": "ast_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "assertion_version": 1, "question_id": "q3", "decided_at": "2026-07-28T13:20:00Z", "selection_origin": "catalog_planning"}
  ],
  "selection_receipt": {"outcome": "selected", "source": "catalog", "catalog_generation_id": "cgn_00000000000000000000000000000000000000000000000000000000000000", "decided_at": "2026-07-28T13:20:05Z", "denial_reason": null, "degraded_reason": null, "fallback_reason": null},
  "envelope_ref": {"envelope_id": "rre_67dbfecde0762481e51b88603e201e9350622ddf05e3b900452e2fadbfd20040", "envelope_version": 1},
  "created_at": "2026-07-28T13:20:05Z",
  "identity": {
    "algorithm": "sha256-canonical-json-v1",
    "fingerprint": "2f41acf4b46b25bff3484f2254745c02535c90beaf068c4744fed6207eca0c40",
    "material_fields": ["workspace_id", "activity_kind", "request_id", "query", "purpose", "scope", "candidate_set_digest", "selected_evidence_versions", "selection_receipt", "envelope_ref", "created_at"]
  }
}
```

`selection_origin: "catalog_planning"` pairs with non-null `question_id`/`decided_at` on the same
entry — valid. Two negative counter-fixtures were constructed from this positive and confirmed
REJECTED for this fix cycle: (i) the same entry with `question_id: null` (SOL-8/23's exact accepted
attack, now closed), and (ii) the same entry with `decided_at: null`. A THIRD counter-fixture — the
identical entry with `selection_origin` omitted entirely and `question_id`/`decided_at` both `null`
(a plain, non-question-scoped search selection) — was confirmed to remain VALID, proving "plain
search selections stay valid without them" holds exactly as before.

All six outcome fixtures in this section (selected, empty, denied, degraded, fallback, and (f)'s
`catalog_planning` discriminator), plus six negative counter-fixtures (a denial leaking
`catalog_generation_id`, a `fallback` missing `fallback_reason`, an `empty` outcome with non-empty
`selected_evidence_versions`, a `catalog_planning` entry missing `question_id`, a `catalog_planning`
entry missing `decided_at`, and blank-string `source`/`degraded_reason`/`fallback_reason` values,
SOL-7/24), were run against `schemas/search_activity_receipt.schema.yaml` with
`Draft202012Validator` as part of this fix cycle: all six positives validate with zero errors, all
negatives are rejected. See §22.

## 5.3 Cross-record equality (SOL-2, normative, service-enforced)

On every write AND every read, the service MUST verify, before treating an envelope/receipt pair as
valid:

1. `envelope.workspace_id == receipt.workspace_id`
2. `envelope.activity_kind == receipt.activity_kind`
3. `envelope.request_id == receipt.request_id`
4. `envelope.activity_id == receipt.activity_id` — applies once a `envelope_version: 2` record
   exists for this `envelope_id` (v1 has no `activity_id` to compare, SOL round 3 — see item 6).
5. **(REVISED, SOL round 3, RC-1 — fixes the round-3 UNSOUND ruling).**
   `receipt.envelope_ref == {"envelope_id": envelope.envelope_id, "envelope_version": 1}` — the
   SECOND element is now a FIXED LITERAL `1`, never `envelope.envelope_version` (whichever version
   is currently being read). Round 2's version of this check compared against the CURRENTLY-PRESENTED
   envelope's own `envelope_version`, which meant the documented HONEST v2 pair (receipt correctly
   naming version 1, envelope now at version 2) FAILED this check — round 3's accepted UNSOUND
   finding. The receipt's `envelope_ref` is fixed, by construction (§5.1a step 3), at
   `envelope_version: 1` for the ENTIRE life of the pair — the envelope's later promotion to version
   2 never requires or expects this reference to be rewritten. `search_activity_receipt.schema.yaml`
   also enforces this schema-side via `envelope_ref.envelope_version: const: 1`.
6. **(round 2, SOL-2/16; REVISED round 3, RC-1).** `envelope.receipt_commitment ==
   receipt.identity.fingerprint`, read from the HIGHEST `envelope_version` sharing this
   `envelope_id` (§5.1b). Checks 1–5 prove AGREEMENT between whichever envelope/receipt pair is
   presented; check 6 proves the envelope actually COMMITTED to THIS SPECIFIC receipt's content. A
   version-1 envelope (no `receipt_commitment` field present at all, SOL round 3 — before the
   receipt has been published) has no check-6 value to compare yet — check 6 applies once a
   version-2 envelope exists for this `envelope_id`; a reader that finds only version 1 on file, with
   no receipt yet published, is looking at a receipt-pending activity, not an integrity failure.
   **Check 6 alone does NOT close the receipt-substitution attack** (an attacker who controls both
   files can recompute a self-consistent forged pair) — the closing mechanism is the
   generation-manifest comparison, §17.7a, RC-2.

A mismatch on any of the six is an integrity failure — the service MUST fail closed (deny the read
or reject the write), never silently prefer one side's value. This is a normative, service-layer
rule (JSON Schema cannot itself cross-reference two separate files) — the same class of rule
`assertion_workspace.resolve_or_deny`/`export_service._run_read_allowed` already enforce for
workspace scoping (standing directive 2), applied here to envelope/receipt pairing instead.

## 6. CARP §4.2 rebase disposition

`docs/dev/architecture/carp-contract-freeze.md` §4.2 pre-negotiated a 4-row rebase table before
this document existed (findings F7). This section states, field-for-field, how each row is
satisfied by the schemas in this part:

| CARP field (today) | Migrates into (this freeze) | Disposition |
|---|---|---|
| `research_evidence_plan.schema.yaml` → `questions[].selected_assertion_ref` | `search_activity_receipt.schema.yaml`'s `selected_evidence_versions` | **Satisfied, and now lossless (SOL-8, ENFORCED not merely permitted as of round 2/SOL-8/23).** Same `{assertion_id, assertion_version}` shape, renamed to an array (a receipt can select more than one evidence item across a broader, non-question-scoped activity); each entry carries a `selection_origin` discriminator (`catalog_planning`/`search`) — a `catalog_planning` entry (a CARP rebase) MUST carry non-null `question_id` + a per-question `decided_at`; a `search` entry (or the discriminator omitted, the legacy-compatible default) never requires either. CARP's per-question selection membership is now structurally guaranteed to survive rebase, not merely optionally preserved. |
| `research_evidence_plan.schema.yaml` → `questions[].retrieval_receipt` (`source`, `catalog_generation_id`, `decided_at`) | `search_activity_receipt.schema.yaml`'s `selection_receipt` | **Satisfied.** `source` widens from CARP's `const: catalog` to this schema's open string (provider-agnostic per CARP-1.4's own instruction — "narrows RPC's general shape to this catalog-only instance, it does not widen CARP's own shape"). `catalog_generation_id`/`decided_at` carry through unchanged, now with exact null-on-denial enforcement (SOL-4). |
| `research_evidence_plan.schema.yaml` → `catalog_receipt.catalog_generation_id` | `search_activity_receipt.schema.yaml`'s `candidate_set_digest` scope | **Satisfied, generalized.** Same "which corpus state produced this result" concept; `candidate_set_digest` is the general form, `selection_receipt.catalog_generation_id` remains the catalog-specific instance for callers that still want that exact field name. |
| `search_run.schema.yaml` → `retrieval.selections[]` (non-authoritative mirror) | `search_run.schema.yaml` → `retrieval.activity_id` (new, this part) | **Satisfied, now with an explicit exclusivity rule (SOL-8).** `activity_id` is the reference CARP's own note anticipated ("search_run should reference activity_id instead of mirroring selection detail directly"). `selections[]` is NOT removed (AC RPC-8) — a run that never populates `activity_id` keeps `selections[]`'s full pre-existing shape and meaning. NEW: once a run's `activity_id` is populated (non-null), `selections[]` MUST be empty or omitted on that same run — a run never carries both the authoritative `activity_id` reference and the legacy mirror it superseded (see `search_run.schema.yaml`'s new `allOf`). |

`routing_decision.schema.yaml`'s `retrieval_policy`/`residual_question_ids` are explicitly **out of
this rebase** per CARP §4.1 — orchestration state, not a provenance fact — and this document makes
no change to that schema.

## 7. Findings F9 — receipt vocabulary disambiguation

`knowledge_activity_receipt.schema.yaml` (C4/Knowledge MCP) and `search_activity_receipt.schema.yaml`
(this document) both use the word "receipt" and both echo a `correlation_ref`/`parent_run_ref`-shaped
hint, which risks being read as the same concept. They are not:

| | `knowledge_activity_receipt` (C4) | `search_activity_receipt` (RPC) |
|---|---|---|
| Persisted? | Never (`persisted: const false`, enforced) | Always, exactly once per `activity_id` |
| Identity space | `rfk:v1:<kind>:<opaque>` | `sar_[a-f0-9]{64}` (content-bound, SOL-2) |
| Produced for | One Knowledge MCP tool call (`search`/`fetch`/`rf_*`) | One search/research activity (planned or search-only) |
| Authority | None — caller-local correlation only | Canonical durable record; discovery/lineage read from it |
| Correlation field | `correlation_ref` (echo of caller's `parent_run_ref` hint) | `research_run_envelope.parent_run_ref` (adopts the same field *name*, F10, but is stored durably as part of a canonical envelope, not echoed transiently) |

A caller supplying the same string value to both a Knowledge MCP call's `parent_run_ref` and an RPC
envelope's `parent_run_ref` is using the same *hint convention* deliberately (naming consistency,
F10) — but the two receipts remain fully independent records with no cross-reference, no shared
identity space, and no shared write path.

## 8. `search_request.schema.yaml` — no change (rationale)

RPC-1.1/RPC-1.2 make **no** amendment to `schemas/search_request.schema.yaml`. `research_run_envelope.request_id`
correlates back to `search_request.schema.yaml`'s `request_id` by value, read-only — no new field is
required on the request side to make that correlation work, since `request_id` already exists there.
Listing `search_request.schema.yaml` as an AC RPC-2 `target_surface` in the PRD/plan describes the
*propagation contract* (the request's existing id flows through), not a mandate to edit the
schema. If a later phase (P2+) discovers a real gap (e.g. a caller needing to declare
`activity_kind` intent up front), that is a new, separately-justified additive change — not
something this freeze pre-authorizes.

## 9. AOS references (AC RPC-7)

`research_run_envelope.aos_refs` is optional, nullable, and closed
(`additionalProperties: false`) with three opaque string sub-fields (`project_ref`, `intent_ref`,
`knowledge_ref`). None of them are ever resolved, dereferenced, loaded, or copied by this schema or
by any schema in this part — they round-trip as opaque strings only.

**(a) Absent (the default, SOL-6).** Top-level OMISSION of the `aos_refs` key is now the canonical
absence shape — `aos_refs` was removed from `research_run_envelope`'s top-level `required` list in
this fix cycle (the original submission required the key to always be present, forcing every caller
that never supplies AOS context to write `"aos_refs": null` explicitly). Explicit `"aos_refs": null`
remains valid and semantically identical to omission; fixtures (b)/(c) in §5.2 both now omit the key
entirely.

**(b) Present.**

```json
"aos_refs": {"project_ref": "aos:proj:9f2c...", "intent_ref": "aos:intent:11a0..."}
```

Round-trips verbatim through envelope read/write/export; the referenced AOS project/intent are
never loaded to validate this shape. **SOL-6 (nonblank strings):** every populated sub-field must
now be `minLength: 1` — the original submission's schema accepted `""` as a "present" ref, which is
indistinguishable from "absent" but still passed a truthiness-style existence check in some
callers. That gap is closed.

**SOL-6/22 (round 2, REOPENED) — exactly ONE encoding of "no refs".** Round 1 kept each sub-field
nullable, so `{}` and a partial-null object like `{"project_ref": null}` (with the other two keys
omitted) were BOTH schema-valid — two different byte encodings of the identical "no AOS context"
fact, each minting a DIFFERENT `envelope_id` (the round-2 accepted attack: both validated and hashed
differently). Fixed two ways: `project_ref`/`intent_ref`/`knowledge_ref` are no longer nullable (a
caller with no value for a given sub-ref OMITS that key — note fixture (b) above now omits
`knowledge_ref` entirely rather than setting it `null`, matching this rule), and `aos_refs` itself
gains `minProperties: 1` (rejecting `{}}` outright — see fixture (c) below for the two now-rejected
shapes). The only remaining valid encodings are: top-level omission or explicit `null` (both mean
"no AOS context", and both canonicalize identically per §4.1 rule 7's `.get()`-based convention), or
an object naming exactly the N populated sub-refs and no others.

**SOL-6 (per-kind pattern — deliberately NOT added, documented deviation).** The finding asked for
"a per-kind pattern if cheap." This document does NOT add a regex `pattern` to `project_ref`/
`intent_ref`/`knowledge_ref`: no AOS service anywhere in this repo has shipped a committed ID-format
convention for these refs today — the `"aos:proj:..."`-shaped strings above are this schema's own
illustrative examples, not a format any AOS-side schema or service has frozen. Adding a regex here
would mean this document unilaterally invents and freezes an external system's ID format, which is
a bigger and riskier claim than "if cheap" was asking for. `minLength: 1` + `maxLength: 200` (both
already present) are the cheap, real constraints available without over-claiming a convention this
document has no authority over; if AOS ships a real ID format later, tightening this field's
`pattern` is a separately-justified additive amendment at that time.

**(c) Malformed.** A caller supplies `"aos_refs": {"project_ref": 12345}` (wrong type), a
`project_ref` string longer than 200 characters, or (new, SOL-6) a blank `""` string. This fails
schema validation directly — the writing service rejects the whole envelope write (fail-closed),
never silently truncating, coercing, or treating a blank string as "no ref supplied." **(round 2,
SOL-6/22, re-run and confirmed REJECTED for this fix cycle):** `"aos_refs": {}` (fails
`minProperties: 1`) and `"aos_refs": {"project_ref": null}` (fails `project_ref`'s type, which no
longer permits `null`) — the two round-2 accepted-attack shapes — both now fail schema validation
too, for the same reason as the other malformed shapes above: exactly one canonical encoding of "no
refs" survives.

**(d) Cross-workspace.** A caller supplies syntactically valid `aos_refs` naming an AOS
project/intent/knowledge object that (per whatever AOS-side authorization check P2 wires in)
belongs to a different workspace or a caller without access. This schema cannot itself detect that
condition (the refs are opaque to it by design) — the service-layer check MUST deny the write (or
omit the ref on read) using the SAME canonical denial shape as §5.2 fixture (c) — one
`denial_reason: "not_authorized_or_not_found"`-equivalent signal, never a distinguishable "ref
exists but denied" versus "ref never existed" response (SOL-6's "freeze ONE public denial envelope"
directive, satisfied by reusing §5.2 fixture (c)'s exact shape rather than inventing a second one).

## 10. Threat boundaries

1. **No existence leak on denial.** Every denial shape in this part (origin write denial, envelope
   write denial, receipt `outcome: denied`, AOS-ref denial) carries exactly ONE machine-readable
   reason code (`not_authorized_or_not_found`, SOL-4/6) and zero candidate/content-derived fields —
   consistent with `AssertionCatalog.denied_payload()`'s shape and CARP-1.2's "one denial shape"
   rule. No schema in this part introduces a second denial vocabulary.
2. **Fail-closed on cross-workspace.** Parent-origin refs (§4.2 fixture e), AOS refs (§9 fixture d),
   and any future cross-record reference this schema family introduces MUST be resolved against
   the writing/reading identity's own workspace before being trusted; a cross-workspace reference
   is denied, never silently followed.
3. **No synthetic identifiers.** Neither `provenance_origin.origin_id`, `research_run_envelope.envelope_id`,
   nor `search_activity_receipt.activity_id` may ever be fabricated by a facet/projection builder to
   paper over a legacy artifact's missing lineage — absence stays absence (§4.1 rule 6). All three
   are now exactly content-derived (SOL-1/2): a fabricated value for any of them would also have to
   forge a matching `identity.fingerprint`, which the service-layer recomputation check (§4.1 rule
   7, §5.1a) always catches.
4. **Reuses existing guards, invents no fourth.** Per the findings doc's standing directive 2, any
   P2 write path built against these schemas MUST reuse
   `assertion_workspace.resolve_or_deny` (writes), `api/auth/scope.require_workspace_scope` (HTTP),
   `export_service._run_read_allowed` (run reads), or the per-service `workspace_id` constructor +
   `AssertionCatalogDenied` (ledger reads) — never a new fifth mechanism.

## 11. OQ resolutions (proposed defaults for `RPC-1.G` to ratify)

These are **proposed defaults**, not yet ratified — `RPC-1.G` (task-completion-validator then
Karen) must explicitly accept or override each one.

### RPC-OQ-1 — report-use identity binding

**Question:** Should report-use identity bind to the verified report content digest, a report
revision artifact, or both?

**Proposed default: BOTH.** A report-use record (`schemas/report_assertion_use.schema.yaml`,
authored in Part 2 §13 below) should bind to a **content digest** (tamper-evident, byte-exact proof
of what was verified) **and** a **revision ID** (a stable handle other records/UIs can reference
without re-hashing content). Rationale:

- Every dual-identity pattern already shipped in this repo pairs a stable ID with a content digest
  rather than choosing one: `source_assertion` pairs `assertion_id`+`assertion_version` with
  `assertion_text_sha256`; `external_research_import_receipt` binds `packet_digest` alongside a
  `receipt_id`; `canonical_claim`/`inference_record` always carry `{id, version}` pairs. A
  digest-only binding cannot be referenced compactly elsewhere in the system; a revision-ID-only
  binding cannot prove exactly what content was verified if the revision artifact is later edited
  in place. Carrying both closes that gap without inventing a new pattern.
- AC RPC-3's resilience clause ("missing or legacy persistent refs produce `legacy_unresolved`
  skips") is easiest to satisfy symmetrically when both a digest and a revision ID are required
  fields on the record — a report missing either one is legacy-unresolved by the same rule, rather
  than needing two different missing-field code paths.
- SOL-9 (this fix cycle) FREEZES the exact `report_revision_id` formula for the `run_report` family
  — see §13.1.

### RPC-OQ-2 — inference emission timing

**Question:** Should inference records be emitted at synthesis time and finalized at verification,
or emitted only after verification passes?

**Proposed default: split by object class, not uniform.**

- **Report-use records** (RPC-FR-6/7, P3 scope): publish **only after** the citing report revision
  is verified. This is already explicit in the plan (RPC-3.2: "Prepare from cited persistent refs
  and publish only on verified report revision; preserve report iteration before verification" and
  the Goal 3 statement). No change proposed here — this document just confirms it applies.
- **Inference records** (RPC-FR-8/9, P4 scope): publish as soon as an eligible run-local inference
  claim's bases resolve to exact persistent source-assertion refs — **independent of whether any
  report has been verified yet, or exists at all.** Rationale: P4's own dependency line
  (`RPC-4.1`/`RPC-4.2` depend only on `RPC-1.G`, never on P3) confirms inference materialization
  was designed to run standalone; an inference is "derived reasoning about source assertions," a
  fact that is true independent of report authorship. Gating inference writes on report
  verification would create an artificial coupling this plan's own phase-dependency graph does not
  require, and would leave synthesis-time reasoning with no durable record until a report
  eventually gets verified (or never publish it at all, for internal-only reasoning that never
  becomes a report).

This resolves the question as: **verification gates report-use, not inference.** A single
uniform "emit only after verification" or "emit at synthesis, finalize at verification" answer
does not fit both object classes; splitting the answer avoids forcing one shape onto both.

### RPC-OQ-3 — legacy alias re-scope (per findings F8)

**Question:** Which legacy `search_request`/`search_run` fields remain compatibility aliases after
the canonical nested envelopes freeze?

**Proposed default, re-scoped to the CURRENT tree (not the 2026-07-18 planning-time tree per F8):
ALL current fields on both schemas remain permanent compatibility aliases. Nothing is deprecated,
renamed, or removed.**

Concretely:

- `search_request.schema.yaml`: every existing top-level field (`request_id`, `intent_id`,
  `task_node_id`, `user_or_agent_id`, `query`, `mode`, `constraints`, `budget`,
  `output_requirements`, `approval`) and the C3-added `retrieval` block (§8 above — unchanged by
  this part) all remain exactly as shipped.
- `search_run.schema.yaml`: every existing top-level field, and the C3-added `retrieval` block's
  existing sub-fields (`policy`, `evidence_plan_ref`, `mirror_is_authoritative`, `selections[]`,
  `metrics`) all remain exactly as shipped. This part's changes, `retrieval.activity_id` (additive,
  optional) and the new SOL-8 exclusivity rule (§6, last row), never trigger removal of
  `selections[]` for any run that predates a P2/P5 `activity_id` writer, or whose caller never
  populates it — that run keeps `selections[]`'s full pre-existing shape. The exclusivity rule only
  activates for a run whose `activity_id` IS populated (non-null), which is impossible for any run
  written before this contract existed.

Rationale: F8 established that the schemas C1 was planned against no longer match the current
tree — C3 added the `retrieval` blocks *after* this plan was authored. Re-litigating "which of the
2026-07-18-era fields survive" against a tree that has since grown a whole new block would be
answering the wrong question. The only coherent AC RPC-8-compatible answer on the *current* tree is
"nothing is removed; the new schemas add references alongside what already exists."

## 12. Findings and open items for the orchestrator

No new findings beyond F1–F16 (already logged) were discovered strictly *within* RPC-1.1/RPC-1.2's
own scope. One design note remains open for whoever executes P2 (unchanged by SOL round 1 — neither
was among SOL-1..15):

- **RPC-1.1.a — RESOLVED round 3 (SOL-1, RC-3, §17.9 design note N1).** Round 1/2 left
  `provenance_origin` write-path ownership undecided ("P2 must decide whether `provenance_origin`
  writes share a module with `research_run_envelope`/`search_activity_receipt` writes or need their
  own"). Round 3 resolves this firmly: `provenance_origin`, `research_run_envelope`, AND
  `search_activity_receipt` writes are ALL owned by ONE module, `services/provenance_envelope.py`
  (the plan's own P2 `files_affected` list already names this file) — see §17.9's design note N1
  for the full statement and rationale. No longer an open design note.
- **RPC-1.2.a — `selection_receipt.outcome: fallback` needs a P2 producer decision.** This freeze
  defines the `fallback` outcome shape (§5, mirroring CARP-1.1's `catalog_then_discovery` policy
  concept) but does not mandate exactly which service call sequence produces it. CARP's own
  contract freeze (§3.6 "Seams P2 must add") already flags an open arithmetic question about
  per-term pagination that interacts with this; P2 for *this* plan should read that section before
  wiring a `fallback`-outcome producer to avoid duplicating that unresolved question here.

These are recorded as design notes, not blocking defects — nothing in §4–§11 above depends on
either being resolved before `RPC-1.G`.

---

# Part 2 — Report-Use and Inference/Canonical-Claim Contracts (RPC-1.3, RPC-1.4)

**Status:** DRAFT, continuing the same Mode B (Contract Drafting) authority as Part 1 above — no
`src/research_foundry/**/*.py` production code changes are authorized by this part either. DI-1
remains BLOCKED: nothing below flips, clears, or self-signs a deployment-enabling flag, and no
agent-writable path in this part mints a `CLEARED_*`/`counsel_approved`/`attested` rights value
(§15.3). This part reads Part 1 (§1–§12 above) as authority and does not restate or contradict it.

## 13. Report-use contract (RPC-1.3, AC RPC-3)

### 13.1 Identity model (RPC-OQ-1 applied)

`schemas/report_assertion_use.schema.yaml` (NEW) is the sole authority for "report revision R,
verified, cited persistent reference X." One record exists per `(report revision, cited ref)`
pair — a report revision citing five persistent refs publishes five `report_assertion_use`
records, never one record with five refs. `use_id` (`rau_<64 hex>`) is the opaque token that fills
the frozen `report_uses: list[str]` element slot on `assertion_catalog`'s `EvidencePacket`/
`AssertionLineage` responses (F4) — F4's constraint that the element type stays `str` is satisfied
verbatim; nothing about this schema requires widening that list's element type.

Two report identity families exist on the current tree, and the schema's `report_ref` block
carries a `report_family` discriminator so a reader never infers the family from ID shape alone:

1. **`run_report`** — the classic `verify_report` flow (`src/research_foundry/services/synthesis.py`
   mints `report_id()` once per run at `report_draft.md`/`report_final.md` write time;
   `verification.py::verify_report` is the pass/fail gate). This family has **no existing
   per-verification revision handle** — the same `report_id` can be re-verified multiple times as
   the draft is edited. **SOL-9 FREEZES the exact formula now, superseding open item RPC-1.3.a:**

   ```
   report_revision_id = "rrv_" + sha256-canonical-json-v1({report_id, report_content_digest})
   ```

   using the exact same canonicalization `assertion_identity.py` already ships
   (`json.dumps({"report_id": report_id, "report_content_digest": report_content_digest},
   ensure_ascii=False, separators=(",", ":"), sort_keys=True)` then `sha256(...).hexdigest()`,
   prefixed `rrv_`). This is grounded in shipped naming (`report_id()` in `ids.py`,
   `derive_report_anchors()` in `export_service.py` for the report-content-digest input this
   formula consumes) rather than inventing a new convention. Worked test vector: for
   `report_id = "report_20260728_pediatric_cbc_reference"` and `report_content_digest =
   "2222222222222222222222222222222222222222222222222222222222222222"`, this formula produces
   `report_revision_id = "rrv_eecd155f212fbfdac8b698b4860aae49bfe236a1f9662895e3bea91f92873027"`
   (computed and schema-validated as part of this fix cycle — §22). Re-verifying the identical
   report body reproduces the identical `report_revision_id`; editing the body (a new
   `report_content_digest`) always mints a new, independent `report_revision_id`.
   `schemas/report_assertion_use.schema.yaml` enforces the `^rrv_[a-f0-9]{64}$` shape via a
   conditional scoped to `report_family: run_report` only.
2. **`report_draft`** — the Report Builder flow (`schemas/report_draft.schema.yaml`'s
   `report_draft_id` + `revisions[].report_version_id` + `current_version_id`,
   `verification.py`'s `_verify_draft` path). This family **already has** a real, independently
   minted revision handle (`report_version_id`, confirmed unpatterned on
   `report_draft.schema.yaml` itself). `report_assertion_use.report_ref.report_revision_id`
   MUST echo that value verbatim for this family — never reformatted, reminted, or re-derived by
   this schema or its writer, and no `pattern` is applied to this family's `report_revision_id`.

Both families require `report_content_digest` (SHA-256 over the exact verified body bytes) in
addition to `report_revision_id` — the dual binding RPC-OQ-1 asks for.

**SOL-9 canonical normalization (revises the original submission).** `report_ref.report_id` and
`report_ref.report_draft_id` are now BOTH always explicitly present in the object (added to
`report_ref`'s top-level `required` list) — the inactive family's field is always the literal
`null`, never an omitted key. The original submission left these two fields out of the base
`required` list, so a `run_report` reference could validly omit `report_draft_id` entirely OR set
it explicitly to `null` — two different byte encodings of the identical logical reference,
producing two different `identity.fingerprint` values (and therefore two different `use_id`s) for
what should be the same record. The same fix applies to `cited_ref`: all six of
`assertion_id`/`assertion_version`/`inference_id`/`inference_version`/`canonical_claim_id`/
`canonical_claim_version` are now always explicitly present (added to `cited_ref`'s top-level
`required` list), with the two inactive kinds' four fields always the literal `null`. Exactly one
canonical byte encoding now exists per logical report-use, regardless of which writer produced it —
verified for this fix cycle by constructing both the "omitted" and "explicit null" encodings and
confirming the schema now rejects the omitted form (§22).

**SOL-1/22 (round 2, REOPENED) — `created_at` now MATERIAL, with redefined semantics.** Round 1
deliberately EXCLUDED `created_at` from `identity.material_fields` so a writer retry (at a different
wall-clock instant) still produced an idempotent no-op — but that same exclusion meant `created_at`
could be silently mutated in place post-write with no fingerprint-detectable change (the round-2
accepted attack). This is closed WITHOUT reintroducing retry fragility, by redefining what
`created_at` means: it is now the DETERMINISTIC verification-pass timestamp for the cited report
revision (the exact instant `verify_report`/`_verify_draft` returned its pass result for THIS
`report_content_digest`) — never a per-write-attempt wall-clock stamp. Since every writer publishing
for the SAME verified revision reads and supplies the SAME verification-pass timestamp, replay/retry
still converges on the identical `use_id`; a record whose `created_at` genuinely differs is citing a
DIFFERENT verification pass (a new fact) or has been tampered with, and now correctly gets a
different `use_id` either way. `identity.material_fields` widens to `[workspace_id, report_ref,
cited_ref, rights_snapshot, created_at]`. See §13.5 for the full replay-safety argument and a worked
before/after vector.

### 13.2 Publication gate (RPC-OQ-2 applied, verbatim from Part 1 §11)

Report-use records publish **only after** the citing report revision passes verification
(`verify_report`/`_verify_draft` returns a pass). A failed or not-yet-attempted verification
creates **zero** `report_assertion_use` records for that revision — there is no "draft" or
"pending" status value on this schema, because there is no partially-published state to represent;
either verification passed and the exact cited refs at that moment were published, or nothing was
published. Re-verifying an edited report body (new content digest) after a prior pass is a **new**
revision under §13.1's model and publishes its own, independent set of `report_assertion_use`
records — the prior revision's records are never mutated or retracted by a later revision's
publish (retraction, if ever needed, is a lifecycle-event concern — see §19 — not this
schema's job).

### 13.3 Cited-reference typing (mirrors AC RPC-4's anti-conflation rule)

`cited_ref.ref_kind` is a closed, mutually exclusive partition
(`source_assertion` / `inference` / `canonical_claim`), structurally enforced by the schema's
trailing `allOf` (exactly one id/version pair non-null per kind, the other two pairs
schema-forced to `null`, and — per SOL-9 above — all six fields always explicitly present). A
report that cites a `source_assertion` never implicitly also "uses" a dependent `inference`/
`canonical_claim` built from it, and vice versa — each cited persistent reference the report body
actually names gets its own explicitly typed record. This mirrors AC RPC-4's "forbid
inference/source conflation" rule applied to the citation side instead of the materialization
side.

### 13.4 Rights/workspace snapshot rule (SOL-10, revises the original submission)

`rights_snapshot` is now the FULL, byte-identical field shape to
`source_assertion.schema.yaml`'s `rights_summary` block — every sub-field (including
`rights_record_ids`, `reuse_assessment_ids`, `permission_record_ids`, and `rights_triage_failure`,
all omitted from the original submission), the same `mirror_is_authoritative: false` invariant, the
same nullable `mirror_of_record_id`/`mirror_derived_at` (the original submission incorrectly
required these non-null, rejecting a valid shipped `source_assertion.rights_summary` mirror that
permits them `null`), and the same link-before-assert `allOf` guard (any status/restriction field
set to a non-"unknown" value now REQUIRES `rights_record_ids` to be non-empty — the original
submission's folded subset had no such guard, meaning a `CLEARED_*`/`counsel_approved` value could
validate with zero linked authoritative record). Two source cases:

1. **`ref_kind: source_assertion`.** Copy the cited `source_assertion`'s own `rights_summary`
   verbatim (or an all-`"unknown"`-sentinel shape if that source assertion predates
   `rights_summary` and has none — this is honest absence, not a validation failure, matching
   `source_assertion.schema.yaml`'s own documented resilience rule).
2. **`ref_kind: inference` or `ref_kind: canonical_claim`.** Neither `inference_record.schema.yaml`
   nor `canonical_claim.schema.yaml` carries its own `rights_summary` (they are derived/grouping
   concepts, not source evidence). The writer MUST fold the `rights_summary` of every
   `source_assertion_refs` entry the cited inference/canonical-claim record itself resolves to
   (transitively, for a canonical claim's `inference_refs` too) using a **most-restrictive-wins**
   rule per sub-field (e.g. if any contributing assertion's `clearance_status` is
   `PROHIBITED`/`LEGAL_REVIEW_REQUIRED`, the snapshot's `clearance_status` is that value, never a
   more permissive contributor's value) — never an average, never the first-seen value, never a
   silently-omitted field.

This block is a **passthrough record of fact**, never an independent rights determination: the
writer copies or folds already-existing `rights_summary` values and MUST NEVER promote
`clearance_status`/`review_status` to a `CLEARED_*`/`counsel_approved`/`attested` value that was
not already present on a contributing record (agent-writable-path guard rule
`no_agent_cleared_rights_value`, restated at §15.3). Whether a given `clearance_status` actually
*permits* citation in a report of a given audience/sensitivity is a separate, already-shipped
policy question (`verification.py`'s `check_report_body_sensitivity`/
`work_sensitive_claims_block_public_report` checks) that this schema does not re-implement or
gate a second time — `report_assertion_use` records the fact of citation, it does not decide
whether that citation was allowed.

**SOL-10, `rights_snapshot` is now MATERIAL to identity.** `identity.material_fields` widens to
`[workspace_id, report_ref, cited_ref, rights_snapshot, created_at]` (the original submission
excluded `rights_snapshot`, meaning a report-use's rights posture could be altered post-hoc with no
`use_id` change; `created_at` joins per §13.1's round-2 fix above). A report-use's rights posture at
the moment of citation is itself an immutable fact of that specific use, not a mutable annotation —
substituting it must change `use_id`. See §13.5 for the consequence this has for the replay/conflict
model.

**SOL-10/21 (round 2, REOPENED) — "byte-identical" was contradicted by the schema's own stricter
`required` list; fixed by matching the source subschema's permissiveness exactly, plus a canonical
normalization rule for hashing.** Round 1's `rights_snapshot` REQUIRED
`[mirror_of_record_id, mirror_derived_at, mirror_is_authoritative]`, but
`source_assertion.rights_summary` (the block this schema claims to mirror byte-identically) requires
NONE of its sub-fields — a legitimately shipped, valid source `rights_summary: {}}` (an assertion
whose rights posture was never triaged, honest all-absent state) could not be copied here verbatim;
round 1's own schema REJECTED it for three missing fields, directly contradicting the "byte-identical
verbatim copy" claim (the round-2 accepted attack). Fixed: `rights_snapshot` no longer carries a
`required` list at all, matching `source_assertion.rights_summary` exactly — any value that validates
against the source subschema (including `{}}`) is now GUARANTEED to validate as a snapshot too, by
construction, closing the gap structurally rather than by convention.

This creates a new, necessary requirement: since `rights_snapshot` is material to identity, and two
semantically-identical sources can now legitimately be stored with DIFFERENT shorthand (one source's
`rights_summary` might be `{}}`, another's the fully-spelled all-`"unknown"` form — both mean the
exact same thing), a **canonical normalization rule** governs what actually feeds
`identity.fingerprint`: every sub-field ABSENT from the rights_snapshot being hashed (including every
absent key inside the nested `restrictions` object) is expanded to its schema-documented default
BEFORE canonicalization — `null` for `mirror_of_record_id`/`mirror_derived_at`; `false` for
`mirror_is_authoritative`; `[]` for `rights_record_ids`/`reuse_assessment_ids`/
`permission_record_ids`; `"unknown"` for `copyright_status`/`access_basis`/`review_status`/every
`restrictions.*` sub-field; `"UNKNOWN"` for `clearance_status`; `null` for `rights_triage_failure`.
This is the SAME normalization principle §4.1 rule 7 already establishes at the top level (a missing
field canonicalizes identically to an explicit `null`), applied one level deeper into
`rights_snapshot`'s own nested shape. **Worked verification (computed for this fix cycle, §22):**
normalizing a bare `{}}` rights_summary produces byte-identical canonical JSON to normalizing the
fully-spelled all-`"unknown"`/all-empty form — confirmed
`fingerprint(normalize({})) == fingerprint(normalize(fully-spelled))` — so "equal sources hash
equally" holds, and (for contrast) confirmed the UN-normalized `fingerprint({}) !=
fingerprint(fully-spelled)`, which is exactly the bug this normalization rule closes. This rule is a
writer/reader-side canonicalization step (like §4.1 rule 7's), not a schema construct JSON Schema can
express directly.

**SOL-10 (round 3, REOPENED, RC-5) — the "byte-identical mirror" claim was itself contradicted by
ONE over-hardened sub-field.** Round 2's blank-string audit (SOL-7/24, the same pass that closed
`source`/`degraded_reason`/`fallback_reason` on `search_activity_receipt`) also added `minLength: 1`
to `rights_snapshot.rights_triage_failure.detail` — but `source_assertion.rights_summary.rights_triage_failure.detail`
(the field this schema mirrors byte-identically) has NEVER carried a `minLength` constraint. A
legitimately shipped source record with `rights_triage_failure.detail: ""` therefore could NOT be
copied here verbatim — round 3's accepted counterexample, directly contradicting §13.4's own
"byte-identical" claim (the same class of gap SOL-10/21 already closed for the `required` list).
**Fixed: blank-string hardening applies to RPC-MINTED (non-mirrored) fields only — every MIRRORED
field's validation domain must be a strict SUPERSET-ACCEPTING match of the source subschema it
copies.** `rights_snapshot.rights_triage_failure.detail` no longer carries `minLength: 1` (matching
the source exactly, plain `type: string`); every OTHER blank-string fix from round 2 (`source`,
`degraded_reason`, `fallback_reason` on `search_activity_receipt`; `report_ref.report_id`/
`report_draft_id` on `report_assertion_use`) stays unchanged — none of THOSE fields mirror a shipped
subschema with a looser domain, so hardening them remains correct. **Re-verified this fix cycle
(§22b):** (1) `rights_triage_failure.detail: ""` now validates against
`report_assertion_use.schema.yaml` (round-3 counterexample, confirmed CLOSED); (2)
`rights_snapshot: {}` still validates (SOL-10/21's round-2 fix, re-confirmed unaffected); (3)
`fingerprint(normalize({})) == fingerprint(normalize(fully-spelled))` re-confirmed
(`4fcc2060...5285c2`, identical to round 2's computed value — the normalization rule itself is
untouched by this fix, only the raw-acceptance domain changed).

### 13.5 Replay and conflict rules (RPC-3.1 AC: "same input replays; digest/version/workspace mismatch fails closed")

`identity.fingerprint` is `sha256-canonical-json-v1` over exactly `{workspace_id, report_ref,
cited_ref, rights_snapshot, created_at}` (the `identity.material_fields` const, widened per SOL-10
above and per SOL-1/22, round 2, for `created_at`), and `use_id` is `rau_` + that fingerprint — the
same content-addressed-ID convention as `provenance_origin.origin_id`/`source_assertion_id`.
Re-preparing the identical `(workspace_id, report_ref, cited_ref, rights_snapshot, created_at)`
quintuple always recomputes the identical `use_id` (verified for this fix cycle: recomputing the
fingerprint from §13.6 fixture (a)'s exact material reproduces the stored fingerprint byte-for-byte —
§22).

**SOL-10 consequence for "version mismatch" (documented explicitly, since it changes the original
submission's framing):** because `rights_snapshot` is now material, a re-fold that picks up an
UPDATED rights posture (e.g. a source assertion's `rights_record` was reviewed and its
`clearance_status` changed between two publish attempts) no longer produces "the same `use_id` with
different bytes" — it produces a genuinely DIFFERENT `use_id`, because the material payload itself
differs. This is the more correct behavior (each distinct rights posture actually observed at a
specific use-time gets its own immutable record, never silently overwritten), but it means the
classic `MaterializationConflict` byte-comparison check is now narrowly scoped to a residual
corruption/bug case rather than a routine "stale rights fold" case:

**SOL-1/22 (round 2, REOPENED) — why `created_at` can safely join `material_fields` without breaking
replay.** Round 1 excluded `created_at` specifically so a writer retry at a DIFFERENT wall-clock
instant still converged on the same `use_id`; the round-2 accepted attack showed this same exclusion
let `created_at` be silently mutated post-write with no detectable change. The fix keeps replay-safety
by changing what `created_at` MEANS rather than reverting the schema change: it is now the
DETERMINISTIC verification-pass timestamp (`verify_report`/`_verify_draft`'s own pass instant for this
`report_content_digest`), not a per-write wall-clock stamp. Two writers (or one writer retried)
publishing for the SAME verified revision read and supply the identical verification-pass timestamp,
so replay still converges; a candidate supplying a DIFFERENT `created_at` for otherwise-identical
material is citing a genuinely different fact (a different, later re-verification of an edited body —
already a new `report_content_digest`/`report_revision_id` under §13.1's model in the normal case — or
tampering), and now correctly mints/reveals a different fingerprint. **Worked vector (computed for
this fix cycle, §22):** taking fixture (a)'s exact material and changing ONLY `created_at` (from
`2026-07-28T12:05:00Z` to `2026-07-28T15:00:00Z`, holding `workspace_id`/`report_ref`/`cited_ref`/
`rights_snapshot` fixed) recomputes fingerprint
`0d238f0b8334a62701ceec6fdbe6d36a555c7150acff19afaced42bc5623830c`, which does NOT equal fixture
(a)'s stored `2a071b5b...` value — confirming the round-2 mutation attack this closes. Re-preparing
fixture (a)'s material with `created_at` UNCHANGED (a genuine retry) reproduces the identical
`2a071b5b...` fingerprint, confirming replay-safety is preserved.

- **Replay (no-op success).** Two writers (or one writer retried) resolve the identical
  `(workspace_id, report_ref, cited_ref, rights_snapshot, created_at)` quintuple and therefore
  compute the identical `use_id`. If a file already exists at that id, the writer compares the
  freshly recomputed `identity.fingerprint` to the stored one — by construction they match (same
  material in, same fingerprint out) — and treats the write as an idempotent no-op success. Because
  `created_at` is now the deterministic verification-pass timestamp (not a per-attempt wall-clock
  stamp, per the round-2 fix above), this comparison never spuriously fails merely because two
  attempts happened to run at different real-world instants — they still supply the SAME
  `created_at` value.
- **Conflict (residual corruption guard, `replay_conflict`).** The ONLY way to reach "same `use_id`,
  different stored bytes" is a write-path bug or race that stores a record whose persisted fields do
  not actually match the material that produced its own `use_id` (e.g. a corrupted write, or two
  concurrent writers racing on the identical id with a non-atomic file replace). The writer MUST
  detect this the same way `assertion_materialization.py`'s `MaterializationConflict` already does
  for source assertions: recompute the fingerprint from the file actually on disk and compare it to
  the id's own suffix; a mismatch is rejected as `replay_conflict`, never silently overwritten.
- **Digest mismatch (substitution, per-revision, unaffected by SOL-10).** The writer recomputes
  `report_content_digest` over the report body bytes it is about to publish against and compares it
  to the digest the verification pass actually ran over. A report body edited between
  "verification passed" and "publish the use records" fails this check — no `report_assertion_use`
  record is written for the substituted body (§13.6 example (c)).
- **Version mismatch (stale cite, per-ref, unaffected by SOL-10).** The writer resolves `cited_ref`'s
  exact `assertion_version`/`inference_version`/`canonical_claim_version` against the CURRENT record
  on disk. If the report's claim_ledger cites a version that is no longer the record's latest, or
  the record's `lifecycle_state`/`status` is not `eligible`/`active` at publish time, publication for
  that one ref is skipped (typed `stale_persistent_reference`, no partial record) — sibling refs in
  the same report revision that ARE current still publish independently.
- **Workspace mismatch (cross-workspace ref, per-ref, unaffected by SOL-10).** The writer resolves
  `cited_ref`'s target through the SAME workspace-scoped lookup the report itself is being verified
  under (`assertion_workspace.resolve_or_deny` / the per-service `workspace_id` constructor —
  standing directive 2, no fourth guard invented here). A cited ref that resolves to a different
  workspace than `report_ref`'s own `workspace_id` is denied — no record, no leaked existence signal
  about which workspace actually holds it (§13.6 example (d)).

### 13.6 Examples

**(a) Positive — verified `run_report` citing a source assertion, full rights_snapshot (SOL-9/10).**

```json
{
  "schema_version": "1.0", "type": "report_assertion_use",
  "use_id": "rau_2a071b5be0f58f09208a0ce71ebb9b62ce05a045d73bbe5acff3a290d5d05242",
  "workspace_id": "default",
  "report_ref": {
    "report_family": "run_report",
    "report_id": "report_20260728_pediatric_cbc_reference",
    "report_draft_id": null,
    "report_content_digest": "2222222222222222222222222222222222222222222222222222222222222222",
    "report_revision_id": "rrv_eecd155f212fbfdac8b698b4860aae49bfe236a1f9662895e3bea91f92873027"
  },
  "cited_ref": {
    "ref_kind": "source_assertion",
    "assertion_id": "ast_4444444444444444444444444444444444444444444444444444444444444444",
    "assertion_version": 1,
    "inference_id": null, "inference_version": null,
    "canonical_claim_id": null, "canonical_claim_version": null
  },
  "rights_snapshot": {
    "mirror_of_record_id": "ast_4444444444444444444444444444444444444444444444444444444444444444",
    "mirror_derived_at": "2026-07-28T12:00:00Z",
    "mirror_is_authoritative": false,
    "rights_record_ids": ["rgt_001"], "reuse_assessment_ids": [], "permission_record_ids": [],
    "copyright_status": "open_license", "access_basis": "public_web",
    "restrictions": {"commercial_use": "allowed", "incorporation_into_other_products": "unknown", "adaptation": "unknown", "redistribution": "unknown", "bulk_retrieval": "unknown", "model_training": "unknown"},
    "clearance_status": "CLEARED_OPEN_LICENSE", "review_status": "human_reviewed",
    "rights_triage_failure": null
  },
  "created_at": "2026-07-28T12:05:00Z",
  "identity": {
    "algorithm": "sha256-canonical-json-v1",
    "fingerprint": "2a071b5be0f58f09208a0ce71ebb9b62ce05a045d73bbe5acff3a290d5d05242",
    "material_fields": ["workspace_id", "report_ref", "cited_ref", "rights_snapshot", "created_at"]
  }
}
```

Schema-validated with zero errors as part of this fix cycle; the replay check (recomputing the
fingerprint from this exact material) reproduces the stored fingerprint (§22). **Round 2:**
`created_at` (`2026-07-28T12:05:00Z`) is this revision's own deterministic verification-pass
timestamp (§13.1/§13.5) and now joins `material_fields`, so this fingerprint differs from the round-1
value (`bf75d43c...`) even though every other field is unchanged.

**(b) Unverified report — no record.** A report whose latest `verify_report`/`_verify_draft` call
returned `passed: false` (or that was never verified at all) has **zero** `report_assertion_use`
files anywhere for any of its cited refs. There is no fixture to show — narrative absence is the
correct shape, matching `provenance_origin` fixture (c)'s "legacy — no origin record" pattern.

**(c) Substitution — report body swapped after digest — REJECTED.** Take fixture (a)'s report,
recompute a fresh SHA-256 over the CURRENT `report_final.md` bytes at publish time, and get a
digest that does not equal `"222222...222222"` (the digest verification actually ran over,
recorded on the pending publish request). Per §13.5, the writer fails closed: no
`report_assertion_use` record is written for this revision's any cited ref, and no partial write
occurs for the refs that "would have" matched — the digest check gates the whole revision's
publish batch, not each ref independently (unlike the version-mismatch case in §13.5, which is
per-ref).

**(d) Cross-workspace ref — REJECTED.** Fixture (a) but `cited_ref.assertion_id` resolves (via the
governed workspace lookup) to a `source_assertion` stored under `workspace_id: "acme-corp"` while
`report_ref`'s own report was authored/verified under `workspace_id: "default"`. No
`report_assertion_use` record is written for this cited ref; sibling refs in the same report that
resolve to the correct workspace still publish independently. Same one-reason-code, no-existence-
leak shape as `provenance_origin` fixture (e).

**(e) Legacy report with missing persistent refs — `legacy_unresolved`, no canonical use.** A
report citing a `claim_ledger.yaml` claim whose `persistent_references` block is entirely absent,
or present but with `source_assertion_id`/`inference_id`/`canonical_claim_id` all null (a claim
that was never materialized through P3/P4's writers — RPC-DF-1's exact scenario), has no exact
persistent reference to bind a `report_assertion_use` record to. The report itself still verifies
and publishes normally (`verify_report`'s existing claim-id/materiality checks are unaffected);
this specific claim simply produces zero `report_assertion_use` records and is not an error. This
is the resilience clause AC RPC-3 names verbatim ("missing or legacy persistent refs produce
`legacy_unresolved` skips") — `legacy_unresolved` is the typed skip code a P3 writer should emit
for its own internal accounting (not a schema-level status, since — per §13.2 — there is nothing
to represent in a schema instance for a use that was never created).

**(f) Replay — identical inputs, no-op success (SOL-10, V-1 fixture; recomputed round 2 per
SOL-1/22).** Re-preparing fixture (a)'s exact `(workspace_id, report_ref, cited_ref, rights_snapshot,
created_at)` quintuple a second time — with `created_at` UNCHANGED, since it is now the deterministic
verification-pass timestamp rather than a per-attempt wall-clock stamp (§13.1/§13.5) — recomputes
`identity.fingerprint = 2a071b5b...05242` — byte-identical to the stored value. Verified for this
fix cycle by recomputing the fingerprint independently from the five material fields shown in
fixture (a) and confirming equality (§22). The writer's second attempt is a no-op success: the
existing file is returned unchanged. **Round 2 mutation check:** re-preparing with `created_at`
CHANGED (to `2026-07-28T15:00:00Z`, holding everything else fixed) recomputes
`0d238f0b8334a62701ceec6fdbe6d36a555c7150acff19afaced42bc5623830c`, which does NOT match fixture
(a)'s stored fingerprint — confirming the round-2 "mutate created_at, hash unchanged" attack is now
closed (§13.5).

**(g) Replay conflict — corrupted/forged bytes at the same `use_id` — REJECTED (SOL-10, V-1 fixture;
recomputed round 2 per SOL-1/22).** A hypothetical second write attempt targets fixture (a)'s exact
`use_id` (`rau_2a071b5b...05242`) but supplies a `rights_snapshot.clearance_status` of
`"LEGAL_REVIEW_REQUIRED"` instead of `"CLEARED_OPEN_LICENSE"` (with `created_at` unchanged) while
claiming the same `use_id`. Recomputing the fingerprint over this candidate's actual material yields
a DIFFERENT fingerprint (`c7ff2c4c4309281874a4274277dc79b4853bdaf3e6d227d27ab59f3b641d7065` —
recomputed for this fix cycle, §22) than the target `use_id`'s own suffix. The writer MUST reject
this as `replay_conflict` (a forged/corrupted target-id claim), never accept it as a legitimate
replay and never silently overwrite the existing record — this is the SAME check that would also
independently mint this candidate its OWN, different, valid `use_id` if presented honestly (i.e. the
correct outcome for a genuinely updated rights fold is a NEW record, per §13.5's SOL-10 consequence
note — this fixture demonstrates why claiming the OLD `use_id` for it is rejected rather than
accepted as an update).

**(h) `rights_snapshot: {}` — the round-2 SOL-10/21 fix, verified.** Fixture (a) but with
`rights_snapshot` replaced by a bare `{}}` (representing a cited source assertion that predates
`rights_summary` and has none — honest absence, not a validation failure, matching
`source_assertion.schema.yaml`'s own resilience rule). This instance was validated against
`schemas/report_assertion_use.schema.yaml` with zero errors for this fix cycle — round 1's schema
REJECTED this exact shape for three missing required fields; round 2 removed `rights_snapshot`'s
`required` list entirely (§13.4), so it now validates, matching `source_assertion.rights_summary`'s
own permissiveness exactly. Per §13.4's canonical-normalization rule, the bytes that actually feed
`identity.fingerprint` for this `{}}` snapshot are IDENTICAL to the bytes a fully-spelled
all-`"unknown"` snapshot would produce (confirmed for this fix cycle) — two sources that are
semantically identical (both "nothing triaged yet") but stored with different shorthand contribute
the same fingerprint material.

## 14. RPC-1.4 scope determination: is v1-as-shipped sufficient?

Per F2/F3 and this task's own instruction ("most belong in the freeze DOC as normative service
rules over the existing schemas, not schema edits"), each of RPC-1.4's seven named contract
requirements was checked individually against the shipped `inference_record.schema.yaml`/
`canonical_claim.schema.yaml` (Part 1 §2's "byte-identical to `e76784b`" baseline) before any
amendment was considered:

| Requirement | Resolution | Amendment? |
|---|---|---|
| Eligibility | Source-assertion `lifecycle_state` (already on `source_assertion.schema.yaml`) checked at resolve time; workspace enforced via directory/constructor scoping (standing directive 2), never an embedded field — matches how `source_assertion`/`inference_record`/`canonical_claim` already omit an inline `workspace_id` field entirely. | **None.** §15.1 normative rule only. |
| Identity | `inference_id`/`canonical_claim_id` minting algorithm is now FROZEN as a MUST at the doc level (SOL-12, §15.2) — no writer exists yet (P4's `assertion_inference.py`/`canonical_claim_materialization.py` are not yet created), and a repo-wide search confirms zero extant `inference_record`/`canonical_claim` instance files exist anywhere (`runs/`, `tests/fixtures`, templates) that could be invalidated by freezing this now (verified for this fix cycle, §22). Left as a DOC-level requirement (not a schema `pattern`) because forcing a regex before P4's writer exists would still risk freezing the wrong SHAPE if a genuine implementation gap surfaces — but the ALGORITHM itself (material fields, canonical bytes, prefix) is now frozen, not merely recommended. | **None** on the two RAL schemas (schema `pattern` deferred to P4, per SOL-12's own resolution — see §15.2). |
| Support | `inference_record.source_assertion_refs` already correctly forbids inference-of-inference by pattern (`^ast_[a-f0-9]{64}$` only). `canonical_claim.source_assertion_refs` had **no way to cite an inference's support at all**, despite RPC-4.3 requiring "exact assertion/inference support refs." | **Amendment** — `canonical_claim.inference_refs` (§16.1). |
| Atomicity | Record-then-reference ordering and no-partial-pair are service behaviors. SOL-13 (§17.7) now FREEZES the exact durable-commit protocol normatively (staged record → atomic rename → generation-pointer CAS → locked re-read), grounded in `assertion_materialization.py`'s already-shipped `_atomic_dump`/generation-pointer pattern. | **None.** §17.7 is a DOC-level protocol freeze. |
| Optional-canonicalization | "Explicitly requested" is a caller-behavior constraint (the publish call must name its exact support refs), not a schema shape. | **None.** §15.4 normative rule. |
| Lifecycle | `assertion_lifecycle_event.schema.yaml`'s `target.kind` enum already includes `inference_record`, with `transition.to` including `tombstoned` — but `inference_record.status` had no `tombstoned` value to land in, AND (SOL-15a, new finding this fix cycle) `transition.from` had no `active` value to name an inference's actual starting state. | **Amendment** — `inference_record.status` (§16.2, unchanged from original submission) AND `assertion_lifecycle_event.transition.from`/new `oneOf` arms (§16.4, SOL-15a, new this fix cycle). |
| Typed skip rules | Enumerable outcomes, none requiring a schema field (a skip means NO record/reference is ever written — there is nothing to type in an instance that does not exist). | **None.** §18 (AC RPC-4 matrix) is a DOC-level table; §18.1 now adds JSON fixtures (V-1). |

**Conclusion: four narrow, additive amendments were made in total (§16) — two on the original
submission's schemas (`inference_record.status`, `canonical_claim.inference_refs`) and two more
added by this fix cycle's SOL-11/SOL-15a scope extensions (`claim_ledger.persistent_references.inference_version`,
`assertion_lifecycle_event.transition.from`) — everything else remains a normative service rule over
existing, unmodified schema shapes (§15, §17, §18).** None of the four amendments removes, renames,
narrows, or re-requires any existing property; every amended file's `$id`/`schema_version` (where
present) is unchanged, matching this repo's established additive-amendment convention
(`source_assertion.schema.yaml`'s own P2-2/P4 history of adding `rights_summary`/`judgment_basis`
without a version bump).

## 15. Normative service rules (no schema change required)

### 15.1 Eligibility (RPC-4.1)

An inference base is **eligible** for resolution into a durable `inference_record` if and only if:

1. It resolves to an exact `{assertion_id, assertion_version}` pair matching a `source_assertion`
   record that currently exists on disk with that exact version (not merely "some version of that
   `assertion_id`").
2. That `source_assertion`'s `lifecycle_state` is `eligible` at the moment of resolution (`stale`,
   `invalidated`, or `tombstoned` source assertions are never eligible bases — checked once, at
   inference-record-creation time; a LATER invalidation of a previously-eligible base is a
   lifecycle-reconciliation concern, §17.4/P6, not re-checked by this resolution step itself — but
   see §17.1 item 6 (SOL-15b) for the SEPARATE, mandatory re-check immediately before a
   `persistent_references` commit).
3. Every base in the same inference's `source_assertion_refs` array resolves to the SAME
   `workspace_id` as every other base and as the run requesting the inference (standing directive
   2's guard, reused — never a bespoke fifth check).

Any base failing (1)–(3) makes the WHOLE inference candidate ineligible (§18's `mixed_workspace_support`/
`stale_support`/`unresolved_support_ref` typed skips) — there is no partial inference record with
some bases resolved and others dropped.

### 15.2 Identity (RPC-4.1/4.2, SOL-12 — MUST, not a recommendation)

`inference_id`/`canonical_claim_id` remain `type: string` with no `pattern` on the shipped
schemas (§14) — a deliberate, unchanged decision (see below for why). **SOL-12 fixes the
original submission's actual defect: the language wavered between calling this a `MUST` and then
calling it "a design recommendation... not a requirement this document enforces." That
contradiction is removed. This document now states the algorithm as a MUST for P4's writer:**

1. **Verified precondition (SOL-12): zero extant instances exist today.** A repo-wide search for
   `inference_record`/`canonical_claim` instance files (`runs/`, `tests/fixtures/`, templates) as
   part of this fix cycle found none — `assertion_materialization.py`'s
   `_reject_deferred_references` unconditionally rejects any candidate carrying `inference_id`/
   `canonical_claim_id`/`canonical_claim_version` today (findings F11), so no writer has ever been
   able to produce one. Freezing the identity formula now cannot invalidate any shipped data.
2. **Inference identity (MUST).** `inference_id = "inf_" + sha256-canonical-json-v1` over the
   canonical payload `{conclusion, source_assertion_refs, reasoning}` (workspace is deliberately
   excluded — matching `source_assertion`'s own convention of scoping identity via
   directory/constructor rather than an embedded field, §15.1/§14's Eligibility row). Worked test
   vector (computed and schema-validated for this fix cycle, §22): for
   `conclusion = "Pediatric reference intervals for CBC differ materially from adult intervals
   across all measured analytes."`, `source_assertion_refs = [{assertion_id:
   "ast_4444...4444", assertion_version: 1}, {assertion_id: "ast_5555...5555", assertion_version:
   2}]`, `reasoning = {summary: "Synthesized across two source assertions reporting age-stratified
   CBC intervals.", method: "comparative_synthesis", producer: "agent-research-1"}`, this formula
   produces `inference_id =
   "inf_fd3ee362717699c116ca3eb00c4daa982396789c03040212673a3e1a86464e51"`.
3. **Canonical-claim identity (MUST) — entity id + per-version digest, per SOL-12's
   "mutable/versioned" requirement.** A `canonical_claim` is mutable across `state` transitions
   (`proposed → reviewed → active → split/superseded/rolled_back`), so its identity CANNOT be a
   single whole-record content hash the way `inference_record`/`source_assertion` are — that would
   change `canonical_claim_id` itself every time `state` changes, breaking the "stable id across
   versions" requirement every other `{id, version}`-paired schema in this repo relies on. The
   frozen scheme therefore splits into two parts:
   - **Entity identity (stable across the claim's lifetime):**
     `canonical_claim_id = "ccl_" + sha256-canonical-json-v1` over the canonical payload
     `{statement, source_assertion_refs}` as FIRST proposed (version 1's grounding set) — this is
     "what this claim is fundamentally about," and does not change as `state`/`inference_refs`
     evolve across later versions. Worked test vector (computed and schema-validated for this fix
     cycle, §22): for `statement = "Pediatric CBC reference intervals differ from adult
     intervals."`, `source_assertion_refs = [{assertion_id: "ast_4444...4444", assertion_version:
     1, relation: "supports"}]`, this formula produces `canonical_claim_id =
     "ccl_47cc4458b070a6e4e0a4b1dfb52e223e896a12b994219a7921f41334c870da15"`.
   - **Per-version digest (recomputed every version, NOT the entity id):**
     `version_digest = sha256-canonical-json-v1` over `{statement, source_assertion_refs,
     inference_refs, state, canonical_claim_version, replaces, replacement_claims, reversal}` at the
     CURRENT version — a service-internal integrity value used to detect a corrupted/forged write at
     a given `canonical_claim_version`, the same class of check `MaterializationConflict` performs
     elsewhere. `canonical_claim_version` itself remains the shipped schema's plain incrementing
     integer — this document does not add a schema-level `identity` block to
     `canonical_claim.schema.yaml` (consistent with the "no schema pattern yet" decision below).

     **SOL-12/18 (round 2, REOPENED) — now a REAL, persisted, OPTIONAL schema field, not merely a
     documented formula.** Round 1 said this digest was "not a new schema field this document adds;
     P4 may store it wherever its own write-path design needs it" — round 2 found this left the
     round-1 accepted attack fully open: two `canonical_claim` instances sharing the identical
     `canonical_claim_id`/`canonical_claim_version` but with DIFFERENT `statement`/`state` content
     both validated against the schema (JSON Schema cannot itself detect this, and with no persisted
     digest anywhere, nothing else could either). `canonical_claim.schema.yaml` now carries an
     OPTIONAL, additive `version_digest` field with exactly this formula.

     **SOL-25/26 (round 3, REOPENED, RC-2) — formula WIDENED to include the version integer and the
     reversal/replacement fields.** Round 2's formula (`{statement, source_assertion_refs,
     inference_refs, state}`) omitted `canonical_claim_version` itself and
     `replaces`/`replacement_claims`/`reversal` entirely — round 3's accepted attack:
     `canonical_claim_version` could change (e.g. `1 -> 999`) with NO digest change, and
     `replaces`/`replacement_claims`/`reversal.resulting_claims` could be substituted with no digest
     change either. The formula above (this round) closes both — see §17.7a for the
     generation-manifest reader rule this digest is checked against (not merely the record's own
     stored field).

     A P4 writer under this contract MUST populate `version_digest` on every record it writes; a
     reader/replay path MUST validate it when present (recompute over the eight fields above and
     compare); legacy absence (a record written before this field existed — none exist today, §14)
     is tolerated read-only, never required retroactively. Worked test vector (RECOMPUTED this fix
     cycle for the widened round-3 formula, §22b), using the canonical-claim fixture from §18.1: for
     `statement = "Pediatric CBC reference intervals differ from adult intervals."`,
     `source_assertion_refs = [{assertion_id: "ast_4444...4444", assertion_version: 1, relation:
     "supports"}]`, `inference_refs = [{inference_id: "inf_fd3ee362...464e51", inference_version: 1,
     relation: "supports"}]`, `state = "active"`, `canonical_claim_version = 1`, `replaces = null`,
     `replacement_claims = null`, `reversal = null` (`.get()` semantics — all three absent fields on
     the §18.1 fixture canonicalize identically to explicit `null`), this formula produces
     `version_digest = 86d6007be832a210049f0ec44a86479b8223c7bab23363fb00631ac0d88a84e0` (round 2's
     value, `7cceafab...f75e4`, is now SUPERSEDED — it is the OLD, narrower formula's output and no
     longer the value this contract requires). **Tamper re-run (confirmed REJECTED):** bumping ONLY
     `canonical_claim_version` to `999`, holding every other field identical, recomputes
     `6096c0279b7267810a3a2bc9fa4fb17928be2dad1196b08c598cf0a7e27d4108` — CONFIRMED different from
     the honest `86d6007b...` value, closing SOL-26's exact accepted attack. The **P7 verifying task**
     (§17.9) is `RPC-7.15`: confirm every P4-written `canonical_claim` record's `version_digest`
     recomputes to its stored value AND matches its generation-manifest entry (§17.7a).
4. **Inference-record version digest (SOL-12/18, round 2; WIDENED round 3, SOL-25/26, RC-2).**
   `inference_record.schema.yaml` gains the SAME OPTIONAL, additive `version_digest` field, with an
   analogous formula: `sha256-canonical-json-v1` over `{conclusion, source_assertion_refs,
   reasoning, status, inference_version}` at the CURRENT `inference_version` — widening past
   `inference_id`'s own identity payload (which excludes `status`, item 2 above) so a
   lifecycle-driven `status` change (e.g. `active -> stale`, §16.4) is itself provable without
   altering the stable `inference_id` (round 2), and (round 3, RC-2) with `inference_version` itself
   so a version-integer-only mutation is also provable — round 2's formula omitted the version
   integer, and round 3's accepted attack showed `inference_version` could change (e.g. `1 -> 999`)
   with NO digest change under that formula. Worked test vector (RECOMPUTED this fix cycle for the
   widened round-3 formula, §22b), using the §18.1 inference fixture: `version_digest =
   8e1292fe2967aae3652dbdf87e0e1522fe387c82dcc003d81b0415bfc8321c44` (round 2's value,
   `eb94ff60...f45e2`, is now SUPERSEDED). **Tamper re-run (confirmed REJECTED):** bumping ONLY
   `inference_version` to `999`, holding every other field identical, recomputes
   `befb39ce536eb80c7a85067769fcbc1c3be529516cbb231eed8644f1bf545d44` — CONFIRMED different from the
   honest `8e1292fe...` value, closing SOL-26's exact accepted attack. The **P7 verifying task**
   (§17.9) is `RPC-7.14`: confirm every P4-written `inference_record`'s `version_digest` recomputes
   to its stored value AND matches its generation-manifest entry (§17.7a).
5. **Why no schema `pattern` on `inference_id`/`canonical_claim_id` yet (unchanged decision, now
   explicitly justified against SOL-12's ask).** SOL-12 asked to "freeze the exact formula," not to
   add a schema-level regex — adding a `pattern` retroactively is safe once P4's actual writer exists
   and no instance has yet violated the frozen convention (true today, per point 1), but freezing the
   SHAPE at the schema layer before P4 designs the write path risks a schema/implementation mismatch
   this document has no way to catch without a real writer to test against. P4, when it implements
   the writer, MAY add the `pattern` retroactively (a compatible narrowing, since every instance it
   will ever have written already follows the MUST formula above) — but this document itself does
   not add it. (`version_digest` itself, unlike `inference_id`/`canonical_claim_id`, already HAS a
   `pattern` — `^[a-f0-9]{64}$` — since it is a plain hash-shaped value with no prefix/entity-id
   ambiguity to defer.)

### 15.3 No agent-minted rights promotion (repo-wide guard, restated for this schema family)

Neither `inference_record.schema.yaml` nor `canonical_claim.schema.yaml` carries a
`rights_summary`/`clearance_status` field at all (§13.4) — there is nothing for P4's writer to
promote on these two objects directly. `report_assertion_use.rights_snapshot` (§13.4) is the one
schema in this whole freeze that DOES carry a `clearance_status`/`review_status` shape, and its
normative rule is explicit: copy-or-fold only, never mint a new `CLEARED_*`/`counsel_approved`/
`attested` value that did not already exist on a contributing `source_assertion.rights_summary`.
This satisfies the standing `no_agent_cleared_rights_value` guard rule for every schema this
document introduces or amends.

### 15.4 Optional canonicalization (RPC-4.3)

A `canonical_claim` publish is never automatic or inferred from usage patterns, claim volume, or
any other heuristic. It requires an explicit publish call naming the exact
`source_assertion_refs`/`inference_refs` support set the caller wants bound — the same
"explicitly requested" framing RPC-4.3 already uses. A canonical claim that would otherwise be
"obviously" derivable from repeated citation of the same assertion set is NOT auto-created; no
code path in this freeze authorizes an implicit canonicalization trigger.

## 16. Schema amendments (RPC-1.4)

### 16.1 `canonical_claim.schema.yaml` — additive `inference_refs` (unchanged by SOL round 1)

New, fully optional array field, `inference_refs`, mirroring `source_assertion_refs`'s existing
`{id, version, relation}` shape but for `inference_record` support instead of `source_assertion`
support. No `minItems` (may be entirely absent — every existing/legacy canonical claim that never
cites inference support remains valid). `source_assertion_refs` is UNCHANGED (`minItems: 1`, still
required) — a canonical claim must still ground in at least one exact, immutable source assertion;
`inference_refs` can only ever ADD supplementary reasoning-based support alongside that direct
grounding, never substitute for it. If RPC-4.3's implementer later proves a concrete need for an
inference-only canonical claim (zero `source_assertion_refs`), that is a separate,
separately-justified amendment this document does not pre-authorize.

**Round 2 (SOL-12/18) additional amendment to this same file:** a second new, OPTIONAL, additive
field, `version_digest` (`^[a-f0-9]{64}$`, sha256-canonical-json-v1 over `{statement,
source_assertion_refs, inference_refs, state}`) — see §15.2 item 3 for the full rationale and worked
test vector, and §17.9 for the P7 verifying task (`RPC-7.15`).

### 16.2 `inference_record.schema.yaml` — additive `status: tombstoned` (unchanged by SOL round 1)

`status` enum widened from `[active, stale, invalidated]` to `[active, stale, invalidated,
tombstoned]`. Justification: `assertion_lifecycle_event.schema.yaml`'s `target.kind` enum already
includes `inference_record` (shipped, unmodified by this document), and its `transition.to` enum
already includes `tombstoned` (paired with `cause: manual_tombstone`). Before this amendment, a
lifecycle event directly targeting an `inference_record` with `transition.to: tombstoned` had no
corresponding `status` value on the referenced schema — a provable, narrow gap, closed by adding
exactly the one missing enum member. This is pure enum widening: every `inference_record` instance
valid under the prior three-member enum remains valid.

`canonical_claim.schema.yaml`'s `state` enum is **deliberately NOT** given a parallel
`stale`/`invalidated`/`tombstoned` widening — see §17.5.

**Round 2 (SOL-12/18) additional amendment to this same file:** a second new, OPTIONAL, additive
field, `version_digest` (`^[a-f0-9]{64}$`, sha256-canonical-json-v1 over `{conclusion,
source_assertion_refs, reasoning, status}`) — see §15.2 item 4 for the full rationale and worked
test vector, and §17.9 for the P7 verifying task (`RPC-7.14`).

### 16.3 `claim_ledger.schema.yaml` — additive `persistent_references.inference_version`, NO LONGER schema-conditional (NEW, SOL-11; REVISED round 2, SOL-17)

Resolves finding F17 by picking resolution option 1 from the original submission's §17.6 (the
"exact-versions-everywhere" answer), rather than leaving it an open choice. New, fully optional
integer field `persistent_references.inference_version` (`minimum: 1`), mirroring the existing
`canonical_claim_id`+`canonical_claim_version` pair's shape.

**SOL-17 (round 2, BLOCKER, REVERTED) — the round-1 schema conditional REJECTED a baseline-valid
legacy instance.** Round 1 added an `allOf` conditional requiring `inference_version` to be non-null
whenever `inference_id` is non-null, reasoning (correctly, at the time) that
`assertion_materialization.py`'s `_reject_deferred_references` unconditionally rejects any candidate
carrying a non-null `inference_id` today, so "no shipped instance can have `inference_id` set at
all." Round 2 found the actual defect: that reasoning addressed whether the shipped WRITER could
produce such a row — it did not address whether a baseline-valid INSTANCE (a hand-authored or
legacy fixture with `persistent_references: {inference_id: "x"}` and no version at all — a
perfectly reasonable, schema-legal shape under the file's own pre-existing, wide-open
`additionalProperties: true` / no-conditional structure) would still validate. It did not: round 1's
conditional rejected exactly that shape. **This is reverted.** `claim_ledger.schema.yaml` no longer
carries ANY conditional on `inference_id`/`inference_version` — `inference_version` is a plain
optional integer, full stop, exactly like `canonical_claim_version` was before any pairing rule
existed. Verified for this fix cycle (§22): (a) `{inference_id: "legacy-inf"}` with no version
validates (round-1 REJECTED this; round 2 now ACCEPTS it, closing SOL-17), (b) `{inference_id:
"inf_x", inference_version: 1}` (both set) validates (unaffected).

**The atomic-pair rule moves to writer-level enforcement.** The underlying invariant this
conditional was trying to express — `inference_id` and `inference_version` are written together or
not at all — is real and still required, but a schema conditional is the wrong enforcement layer
for it (it cannot distinguish "a legacy/foreign row that predates this rule" from "a P4 writer under
THIS contract violating it"). Per this round's framing principle: the enforcing service is P4's
`persistent_references` write path (§17.1 item 4, unchanged: "`inference_id` and `inference_version`
... are written together in one atomic operation or not at all"); the MUST-grade rule is unchanged
normative text at §17.1 item 4; the verifying P7 gate task is `RPC-7.16` (§17.9): confirm no
P4-written `claim_ledger` row ever has exactly one of the pair set. **Read semantics for a row with
`inference_id` set and no `inference_version`** (whether a true legacy row, or a row a
non-conforming writer produced): a reader MUST treat the reference as AMBIGUOUS-VERSION — never
resolve it to "the latest" `inference_version` implicitly — and report it via the same
`legacy_unresolved`-class typed skip AC RPC-3 already names for a missing persistent reference
(§13.6 example (e)); this is a resolvable-gap, not a validation failure.

`claim_ledger.schema.yaml` was outside this plan's original `files_affected` (F2's directive); this
is a documented scope extension (§22, and §1 above).

### 16.4 `assertion_lifecycle_event.schema.yaml` — additive `transition.from: active` + 3 new `oneOf` arms (NEW, SOL-15a)

Resolves the SOL-15a finding: an `inference_record`'s own status vocabulary
(`active`/`stale`/`invalidated`/`tombstoned`, §16.2) starts at `active`, never `eligible`
(`eligible` is `source_assertion`/`source_edition`/`passage`'s starting state — a DIFFERENT
concept). Before this amendment, `transition.from`'s enum (`[eligible, stale, invalidated,
tombstoned]`) had no way to name an inference's actual starting state, so a direct
`target.kind: inference_record` event transitioning `active -> stale`/`active ->
invalidated`/`active -> tombstoned` was unrepresentable. This amendment:

1. Widens `transition.from`'s enum by exactly one member: `active` (pure enum widening — every
   event instance valid under the prior four-member enum remains valid).
2. Adds three new `oneOf` arms to the existing (from, to) partition:
   `active -> stale`, `active -> invalidated`, `active -> tombstoned` — the inference-record-only
   analogue of the three existing `eligible -> *` arms.
3. Adds one new `allOf` conditional: `transition.from: active` is valid ONLY when
   `target.kind == inference_record`. This is a restrictive conditional, but it only restricts the
   NEWLY added `active` enum value — it adds no constraint whatsoever to any pre-existing
   `from`/`to` combination, so no previously-valid event instance is affected.

Deliberately does NOT touch `canonical_claim`: per §17.5's already-established design note,
`canonical_claim.state`'s vocabulary is structurally different from the generic
eligible/stale/invalidated/tombstoned lattice and was deliberately left unwidened; a
`from: active` event targeting `canonical_claim` remains invalid, consistent with that prior
decision (verified for this fix cycle — §22).

### 16.4a `eligible -> *` arms are now scoped to their real target kinds (SOL-15, round 2, NEW)

Round 2's SOL-15 finding: this document's own SOL-15a amendment correctly scoped the NEW `active`
arms to `target.kind: inference_record` (§16.4 item 3 above), but left the SIX PRE-EXISTING
`eligible -> *` arms completely unscoped by target kind — a baseline (`e76784b`) gap this round's
amendment work made newly visible without closing. Concretely, `transition.from: eligible` combined
with `target.kind: canonical_claim` or `target.kind: inference_record` was (and, before this
sub-section's fix, remained) schema-valid, even though NEITHER target's own frozen status vocabulary
has ever included "eligible" as a possible value: `inference_record.status` is
`active`/`stale`/`invalidated`/`tombstoned` (§16.2, §19) and `canonical_claim.state` is
`proposed`/`reviewed`/`active`/`split`/`superseded`/`rolled_back` (§17.5) — "eligible" is exclusively
`source_edition`/`passage`/`source_assertion`'s starting state. An event claiming this transition
could never describe a real state either target actually passes through.

**Fix:** a new `allOf` conditional restricts `transition.from: eligible` to
`target.kind ∈ {source_edition, passage, source_assertion}` — the exhaustive enumeration of every
target kind whose OWN vocabulary genuinely starts at "eligible." Combined with SOL-15a's existing
`active`-scoped-to-`inference_record` conditional (§16.4 item 3), every `(from, target.kind)`
combination this schema now permits is exactly the set §16.2/§16.4/§17.5's frozen per-target-kind
vocabularies actually support — enumerated exhaustively below:

| `transition.from` | Valid `target.kind` values | Rationale |
|---|---|---|
| `eligible` | `source_edition`, `passage`, `source_assertion` | These three target kinds' own lifecycle vocabulary starts at `eligible` (pre-existing, unchanged). |
| `active` | `inference_record` ONLY | `inference_record.status` starts at `active`, never `eligible` (§16.2, SOL-15a). |
| `stale` | any `target.kind` (unscoped) | `stale`/`invalidated`/`tombstoned` are shared, later-lifecycle states across every target kind this schema names; no target-kind-specific gap has been proven for these `from` values, so no new restriction is added for them (this task's own instruction: prefer no amendment when a gap is not concretely proven). |
| `invalidated` | any `target.kind` (unscoped) | Same as `stale` above. |

**Deviation, documented (this narrows the schema — see §2/§22 for the full additive-only
disposition).** This is the ONE place in this round's amendments that is a genuine narrowing rather
than a pure addition: an instance combining `transition.from: eligible` with `target.kind:
canonical_claim`/`inference_record` was schema-valid before this sub-section and is REJECTED after
it. Verified empirically for this fix cycle (§22): a repo-wide search finds ZERO extant
`assertion_lifecycle_event` instances anywhere using this combination — nothing real is invalidated.
The combination was never a legitimate, satisfiable instance of either target's own frozen
vocabulary regardless of what the schema historically permitted, which is why this document treats
closing it as a justified, in-scope fix rather than an out-of-scope narrowing to defer to a later
phase (`assertion_lifecycle_event.schema.yaml` is already a documented scope extension in this
contract tree, SOL-15a, §1).

## 17. F11 — the gate-reversal contract (`persistent_references` write preconditions)

`assertion_materialization.py:57-60`'s `_DEFERRED_REFERENCE_FIELDS = {canonical_claim_id,
canonical_claim_version, inference_id}` is TODAY actively and unconditionally rejected
(`_reject_deferred_references` → `_Abstain("invalid_persistent_references")` /
`_Abstain("canonical_or_inference_candidate_deferred")`) for any fresh materialization candidate
that already carries a non-null value in one of those three fields. P4 is a **reversal** of that
rejection for a narrow, explicitly-gated follow-up write path — never a general loosening of
`_reject_deferred_references`'s existing behavior for brand-new candidates, which must keep
rejecting forged/pre-set values on first materialization exactly as it does today.

### 17.1 Preconditions (ALL must hold before ANY `persistent_references` field is written)

1. **Record-before-reference ordering.** The referenced `inference_record`/`canonical_claim` file
   MUST already exist on disk as a validated, atomically-written, immutable durable record
   (passing full schema validation, §15.1 eligibility, and — for `canonical_claim` — §15.4's
   explicit-request requirement) BEFORE the corresponding `claim_ledger.yaml` row's
   `persistent_references.{inference_id+inference_version (SOL-11, §16.3) |
   canonical_claim_id+canonical_claim_version}` is touched. Writing the reference first (or writing
   both in a non-atomic sequence a crash could interrupt mid-way) is the exact "partial write"
   hazard RPC-3.3/RPC-4.4's adversarial matrices name.
2. **Same workspace, and bound to the exact claim row (SOL-14, revises the original submission —
   see §17.8 for the full rule).** The `claim_ledger` row being updated and the `inference_record`/
   `canonical_claim` it now references MUST resolve to the identical `workspace_id`, AND the commit
   proof must bind the exact claim row (not merely "some row in the right workspace") — §17.8 below
   is the full normative rule this precondition now defers to.
3. **Eligible lifecycle at write time, RECHECKED immediately before commit (SOL-15b, revises the
   original submission).** The inference/canonical-claim record's own status/state (post-§16.2
   widening for inference; `active` for canonical claims) must be a non-terminal, currently-valid
   state — checked TWICE: once at initial resolution (§15.1 item 2), and AGAIN, atomically, under
   the SAME serialization barrier as the commit itself (§17.7's locked re-read step) — the original
   submission checked this only once, at resolution time, leaving a window between resolution and
   commit where the referenced record (or, per SOL-15b, its OWN support assertions) could have been
   invalidated. See item 6 below and §17.7.
4. **Atomic pair, never partial.** `canonical_claim_id` and `canonical_claim_version` are written
   together in one atomic operation or not at all — never one field present with the other still
   null. `inference_id` and `inference_version` (SOL-11, §16.3) now have the SAME atomic-pair
   requirement.
5. **No re-triggering already-satisfied references.** If `persistent_references` already carries a
   non-null value for the field being written, the write is idempotent-replay-only (identical
   target id/version — a no-op) or a conflict (differing target — rejected, same
   `MaterializationConflict` pattern as everywhere else in this file) — never a silent overwrite of
   an existing reference with a different target.
6. **Support-assertion lifecycle, run mapping, and resolved capability flags, ALL rechecked under
   the SAME serialization barrier immediately before commit (SOL-15b, NEW precondition this fix
   cycle adds).** The original submission's five preconditions checked only the DERIVED record's
   own state (item 3), never the state of the source assertions that record was BUILT FROM. SOL-15
   names the exact gap: a source assertion can become invalid AFTER an inference was published
   while the inference itself remains `active`, and a later reference-write could still wire that
   now-support-invalidated inference into a fresh `claim_ledger` row. The commit step (§17.7's
   locked re-read, immediately before the atomic pointer swap) MUST additionally, atomically,
   recheck:
   - Every `source_assertion_refs` entry the target `inference_record`/`canonical_claim`
     transitively depends on STILL has `lifecycle_state: eligible` (not merely that the derived
     record's own `status`/`state` is non-terminal — item 3 above).
   - The `claim_ledger` row's own `run_id` still maps to a run the caller is authorized to write
     under (re-confirms §17.8's workspace/run binding has not been invalidated between resolution
     and commit).
   - The resolved capability flags (`ledger_write_allowed`, and — for `canonical_claim_id`/
     `canonical_claim_version` specifically — `canonical_claims_allowed`, §17.3) are STILL `True`
     at the exact commit instant, not merely at initial resolution — a flag revocation between
     resolution and commit MUST abort the write, never silently complete it using a
     since-revoked authorization.

   A failure in any of these three rechecks aborts the write with a typed rejection (reusing
   `stale_support`/`partial_write_rejected`-class codes, §18) — never a partial commit, never a
   silent downgrade to "commit anyway, reconcile later."

**SOL-15 (round 2) — the bounded concurrency model, stated honestly.** Round 1's text risked reading
as "the per-run lock serializes everything relevant" — round 2 correctly called this out as an
overclaim. The precise, honest scope: the per-run lock (§17.7 step 3) serializes CONCURRENT
`persistent_references` COMMIT ATTEMPTS against the SAME `claim_ledger` row and its target
inference/canonical-claim record — it does **not** serialize lifecycle events, `canonical_claims_enabled`/
`ledger_write_enabled` config flips, or run-mapping mutations, which can all occur on entirely
different code paths outside this lock's scope. This is why item 6 above exists as a SEPARATE,
mandatory re-check performed UNDER the lock immediately before commit, rather than being treated as
already covered by "the lock serializes everything": item 6's three rechecks (support-assertion
lifecycle, run mapping, resolved capability flags) are how a lifecycle/config/run-mapping mutation
that happened OUTSIDE the lock's scope, between initial resolution and the locked commit instant, is
still caught before the write completes. Anything that mutates AFTER the locked recheck but before
the atomic pointer swap — a vanishingly narrow window, but not literally zero — is not caught by
item 6's recheck itself; it is caught by `assertion_impact`'s post-hoc reconciliation pass (P6,
read-only per §17.4), which detects and flags any inference/canonical-claim record whose support
became invalid after that record's own commit. **The bounded guarantee this document actually makes:
the per-run lock provides serialization for ledger-and-record WRITERS only; everything else is
handled by the commit-time recheck (item 6) plus post-hoc reconciliation (P6) — never full
system-wide serialization of every mutator.** A P7 gate task (`RPC-7.19`, §17.9) verifies the
commit-time recheck actually fires under concurrent load; it does not and cannot verify "nothing
outside the lock ever races," because that guarantee is not being made.

### 17.2 What P4 must change in code (recorded for the orchestrator, not authorized here)

`_reject_deferred_references`/`_DEFERRED_REFERENCE_FIELDS` must remain EXACTLY as strict as today
for `AssertionMaterializer._prepare_one`'s existing candidate-intake path (a brand-new claim/fact
arriving with these fields already set is still always rejected — that guards against a caller
forging a fake persistent reference at intake time). P4 needs a **second, separate write path** —
a new method, not a loosened version of the existing one — that is reachable ONLY after §17.1's
now-six preconditions are independently verified, and that updates an ALREADY-MATERIALIZED
`claim_ledger` row's `persistent_references` in place. This document does not name that method (a
P4 implementation decision) but records the constraint so P4 does not attempt to satisfy this gate
by relaxing `_DEFERRED_REFERENCE_FIELDS` itself.

### 17.3 F12 — canonical-claim feature-flag gating

`config.py:115` `canonical_claims_enabled: bool = False` (raw operator toggle) and
`config.py:519-520`/`FoundryConfig.assertion_ledger_capabilities().canonical_claims_allowed`
(resolved: `ledger_write_enabled AND canonical_claims_enabled`, both default `False`) already exist
and are unmodified by this document. P4's canonical-claim writer (§16.1/§17.1) MUST check
`canonical_claims_allowed` (or the equivalent resolved capability) and refuse to publish ANY
`canonical_claim` record — and therefore never reach step 4 of §17.1's precondition chain for a
`canonical_claim_id`/`canonical_claim_version` pair — when that capability resolves `False`, AND
MUST re-verify it is still `True` at commit time per §17.1 item 6 (SOL-15b). Since
DI-1 is BLOCKED and this document authorizes no deployment-enabling flag flip, the practical
consequence is: **on the current default configuration, P4's canonical-claim materializer (RPC-4.3)
publishes nothing** — only the `inference_record` writer (RPC-4.2, gated solely by
`ledger_write_enabled`, not by `canonical_claims_enabled`) is reachable by default. This is by
design, not a defect this freeze needs to work around.

### 17.4 Interaction with P6 (lifecycle continuity) — read-only note

P6's `RPC-6.1`/`RPC-6.2` (dependent enumeration, reuse of checkpoint/resume + exact ordered
identity rules) consume the `inference_record`/`canonical_claim` records §17.1 produces as
read-only input; nothing in this freeze pre-decides P6's own dependent-action enumeration logic.

### 17.5 Design note — `canonical_claim.state` vs. the generic lifecycle vocabulary

`assertion_lifecycle_event.schema.yaml`'s `target.kind` enum also includes `canonical_claim`, and
its shared `transition.from`/`transition.to` enums (now `eligible`/`active`/`stale`/`invalidated`/
`tombstoned` per SOL-15a, §16.4) are otherwise the SAME vocabulary `source_assertion.lifecycle_state`
uses. `canonical_claim.state`, however, has its own, structurally different, self-contained state
machine (`proposed`/`reviewed`/`active`/`split`/`superseded`/`rolled_back`, with a required
`reversal` block on `split`/`rolled_back`) that does not map cleanly onto either the `eligible`- or
`active`-rooted lattice — a direct `target.kind: canonical_claim` lifecycle event with
`transition.from: eligible` OR (per SOL-15a's new conditional, §16.4) `transition.from: active`
cannot be represented by `canonical_claim.state` today; the SOL-15a `active` widening is explicitly
scoped to `target.kind: inference_record` only for exactly this reason. **This document
deliberately does NOT widen `canonical_claim.state`** to chase parity with either the `eligible`-
or `active`-side vocabulary — doing so would invite exactly the kind of "amend defensively without
a proven need" this task was instructed to avoid. The likely correct resolution (P6's decision, not
this document's): a direct `target.kind: canonical_claim` event, if ever used at all, should map
`transition.to: invalidated` onto `state: rolled_back` (with `reversal.reason` referencing the
lifecycle `event_id`) rather than onto a new bare `invalidated` state value; `transition.to:
tombstoned` has no clean existing analogue and would need its own separately-justified amendment if
a concrete P6 use case ever requires it. The MORE LIKELY path in practice remains what RPC-6.1
already describes: primary lifecycle targets stay `source_edition`/`passage`/`source_assertion`,
with `dependent_actions.object_kind: canonical_claim_edge, action: mark_stale` (already shipped,
already distinct from `target.kind: canonical_claim`) carrying the cascading reaction instead of a
direct `target.kind: canonical_claim` event ever being minted at all.

### 17.6 F17 — RESOLVED this fix cycle (SOL-11)

The original submission's §17.6 offered two resolutions for `claim_ledger.persistent_references`
having no `inference_version` field and took no position. **SOL-11 resolves it: option 1 (add
`inference_version`, additive, mirroring the `canonical_claim_id`+`canonical_claim_version` pair)
is now implemented — see §16.3.** `claim_ledger.schema.yaml` is now part of this contract tree's
`files_affected` (a documented scope extension, §1/§22), and the conditional requiring
`inference_version` whenever `inference_id` is non-null is enforced by the schema itself, not left
to a P4 implementation-time choice.

### 17.7 Durable-commit protocol (SOL-13, NEW — normative, grounded in shipped code; ROUND 2 SOL-13/19 freezes the concrete marker/path/lock/CAS specifics round 1 left abstract)

The original submission left "atomicity" as an unexamined service-behavior assumption (§14's table
originally said "Record-then-reference ordering... are service behaviors" with no protocol
detail). SOL-13 named two concrete gaps: (a) a crash between "canonical record published" and
"`claim_ledger` reference written" can leave an orphaned durable record with no reference pointing
at it, and (b) two concurrent writers reading the same `claim_ledger` row, both passing all
preconditions from stale snapshots, can race an atomic-file-replace and silently lose one writer's
update (atomic file replacement is file-level atomicity, not cross-file/cross-write atomicity or a
compare-and-swap). Round 1 froze the SHAPE of the fix (staged write → promote → lock → CAS →
locked re-read → atomic swap) but left the ACTUAL marker path, schema, lock scope, and recovery
destination undefined — round 2's SOL-13/19 finding: "the protocol promotes a final discoverable
record before reference publication, so crash visibility remains," and "assumes a claim-row
generation/CAS marker absent from the schema and current implementation." This section freezes
those specifics, reusing the EXACT conventions `assertion_materialization.py`'s own P3 generation
pointer and `assertion_registry.py`'s workspace-scoped storage root already ship (not inventing a
fourth path convention):

- `AssertionMaterializer`'s existing P3 generation pointer (grounding precedent, unchanged, read-only
  reference): `<materializer-root>/materializations/runs/<sha256(run_id)>/published.yaml` (the
  pointer, containing `{generation_id}`) plus `<same-root>/generations/<generation_id>.yaml` (the
  full generation snapshot), where `generation_id = "mat_" + sha256-canonical-json-v1({run_id,
  records})` (`assertion_materialization.py:720-791`).
- `AssertionRegistry`'s existing workspace-scoped storage root (grounding precedent, unchanged,
  read-only reference): `<foundry-root>/assertion_ledger/workspaces/<sha256(workspace_id)>/`
  (`assertion_registry.py:112-119`).

**The protocol (P4 implements; this document freezes the shape, paths, and ordering, not the code):**

1. **Staged record write.** The candidate `inference_record`/`canonical_claim` is written to
   `<AssertionRegistry-root>/.staging/<record_id>/<record_id>.yaml` (`record_id` = the record's own
   frozen `inference_id`/`canonical_claim_id`, §15.2) — NOT yet at its final, discoverable,
   content-addressed path — using the same atomic tempfile→`fsync`→`os.replace` primitive
   `_atomic_dump` already provides. **A record under `.staging/` is INVISIBLE to every reader** —
   this is the SOLE visibility boundary this protocol establishes (round 2's exact ask): no read
   path, catalog, or projection may ever resolve a staged record. A crash during this step leaves,
   at worst, an orphaned staged file that was never linked to anything and is trivially safe to
   garbage-collect (see recovery rule below).
2. **Promote to the canonical, content-addressed path.** Once the staged write's bytes are
   confirmed durable (the `fsync` completed), the record is atomically renamed/moved
   (`os.replace`, same primitive) from `.staging/<record_id>/` into
   `<AssertionRegistry-root>/inferences/<inference_id>.yaml` or
   `<AssertionRegistry-root>/canonical_claims/<canonical_claim_id>/<canonical_claim_version>.yaml`
   (canonical claims are per-version files under a stable entity directory, matching §15.2's
   entity-id/per-version-digest split) — this is the "record exists before reference" ordering
   §17.1 item 1 already required, now given an explicit atomic mechanism and a named path.
   **CRITICAL (round 2, SOL-13/19): promotion alone does NOT make the record authoritative or
   citable.** A promoted record is a real file on disk, but it remains ORPHANED — not yet a valid
   `persistent_references` target — until step 5's generation-pointer CAS succeeds. The generation
   pointer (not "the record exists at a content-addressed path"), is the SOLE authoritative
   visibility boundary: **a record present in the store but not referenced by the CURRENT
   generation manifest is INVISIBLE for citation purposes and quarantine-eligible on recovery
   (step 6)**, even though it is trivially file-system-discoverable. This closes round 2's exact
   finding ("promotes a final discoverable record before reference publication, so crash visibility
   remains") — discoverability-on-disk and authoritative-visibility are now explicitly two
   different things, and only the latter governs citation.
3. **Per-run lock, acquired before the commit read-check-write sequence.** Lock path:
   `runs/<run_id>/claims/.claim_ledger.lock` (an OS-level advisory flock, co-located with
   `claim_ledger.yaml` itself, `paths.py::RunPaths.claim_ledger`'s sibling). Scope: serializes
   concurrent `persistent_references` COMMIT ATTEMPTS against THIS ONE run's claim ledger only —
   never a cross-run or cross-workspace lock (the bounded concurrency model §17.1 states
   explicitly). Acquired before any of §17.1's preconditions are (re-)verified for the commit step —
   closing gap (b) above.
4. **Compare-and-swap on the generation pointer.** Marker path: `runs/<run_id>/claims/.claim_ledger_published.yaml`
   (the pointer, containing `{schema_version: 1, type: claim_ledger_generation_pointer, run_id,
   generation_id}`) plus `runs/<run_id>/claims/.claim_ledger_generations/<generation_id>.yaml` (the
   full generation snapshot, containing the claim ledger's complete `persistent_references`-bearing
   row set at that generation). **CAS operand:** `generation_id = "clg_" +
   sha256-canonical-json-v1({run_id, persistent_references_snapshot})` — the generation file's OWN
   content digest, never a monotonic counter (the same reason `AssertionCatalog.rebuild()`'s own
   `catalog_generation_id` rejects a counter: a counter would spuriously "change" on a no-op
   rebuild/retry, tripping this exact CAS check for nothing). Under the lock (step 3), the writer
   re-reads the CURRENT pointer's `generation_id` and compares it to the generation the write was
   originally prepared against. A mismatch (someone else committed to this row since this writer
   last read it) aborts this writer's commit as a typed conflict (`partial_write_rejected`, §18) —
   it MUST re-resolve against the NEW current row and retry, never blindly overwrite using a stale
   generation.
5. **Final locked re-read, then atomic pointer swap.** Still under the lock, §17.1 item 6's three
   rechecks (support-assertion lifecycle, run mapping, resolved capability flags) run against the
   freshly re-read row — this is the "immediately before commit" instant those rechecks require.
   Only if all three pass does the writer perform the atomic `claim_ledger.yaml` rewrite (adds the
   `persistent_references` value) AND the atomic pointer swap (`.claim_ledger_published.yaml` now
   names the NEW `generation_id`, whose own `.claim_ledger_generations/<id>.yaml` snapshot includes
   this write) as the SAME documented sequence — the promoted inference/canonical-claim record from
   step 2 becomes authoritatively visible EXACTLY when this pointer swap completes, never before.
   The lock is released only after this atomic swap completes.
6. **Deterministic recovery for orphaned staged/promoted records.** A crash between steps 1 and 2
   (an orphan under `.staging/` that was never promoted) or between steps 2 and 5 (a promoted,
   valid, content-addressed record under `inferences/`/`canonical_claims/` that is NOT referenced by
   the current generation manifest) MUST be **quarantined** — relocated to
   `<AssertionRegistry-root>/quarantine/<record_id>/` — never auto-adopted into a fresh commit
   attempt on next startup/retry. A recovery sweep walks `.staging/` and cross-references every
   promoted record's `record_id` against every `claim_ledger` row's `persistent_references` under
   the CURRENT generation for that run; anything promoted-but-unreferenced moves to quarantine for
   operator review. It MUST NOT silently wire a quarantined record into any `persistent_references`
   block as if it had been the intended target of a prior, interrupted write — a retried commit
   MUST always go through steps 1–5 again from the caller's current candidate, never resume from an
   orphan/quarantined record it happens to find on disk.

This protocol closes both SOL-13 gaps and both round-2 SOL-13/19 gaps: staging makes pre-promotion
records genuinely invisible (round 2's marker/visibility ask); the generation pointer (not mere
file-system existence) is the sole authoritative visibility boundary, so a promoted-but-unreferenced
record is quarantine-eligible rather than silently discoverable (round 2's exact finding); two
concurrent writers are serialized by the named per-run lock plus the named, content-addressed
generation-pointer CAS, so the later writer's stale-generation commit attempt is rejected and
retried against current state rather than silently overwriting the earlier writer's update. The **P7
verifying task** (§17.9) is `RPC-7.12`: a crash-injection test confirming a record interrupted between
steps 1–2 and 2–5 is quarantined, never silently adopted or cited.

### 17.7a Generation-manifest-rooted tamper evidence (SOL-25/26, RC-2, round 3, NEW — normative)

Round 3 found two BLOCKER-severity gaps that §17.7/§15.2's mechanisms, taken alone, leave open:

- **SOL-25 (digest downgrade).** A forged `inference_record`/`canonical_claim` with its
  `version_digest` field omitted or set `null` remains schema-valid (the field is deliberately
  OPTIONAL, §15.2); a forged `research_run_envelope` v2 without its `version_digest` similarly
  validates. Nothing distinguishes "a legitimate legacy record that predates this field" from "a
  record whose digest was stripped to hide tampering," if a reader only checks the record's OWN
  stored field against a recomputation of ITSELF.
- **SOL-26 (authority omitted from digests).** Before this round, `inference_version`/
  `canonical_claim_version` could change (e.g. `1 -> 999`) with NO corresponding `version_digest`
  change (the round-2 formula omitted the version integer itself, §15.2 items 3–4); a canonical
  claim's `replaces`/`replacement_claims`/`reversal.resulting_claims` could similarly be substituted
  with no digest change.

**The fix has two parts, applied together.**

1. **Widened digest material (closes SOL-26).** §15.2 items 3–4 (this round) add the version
   integer itself to BOTH formulas, and add `replaces`/`replacement_claims`/`reversal` to the
   canonical-claim formula — see §15.2 for the exact widened formulas and recomputed worked
   vectors. A version-integer-only mutation, or a `replaces`/`replacement_claims`/`reversal`
   substitution, now necessarily changes `version_digest`.
2. **The generation manifest becomes the tamper-evidence ROOT, not the record's own stored field
   (closes SOL-25).** Every record PROMOTED under this contract's protocols — every `inference_record`/
   `canonical_claim` committed via §17.7's generation-pointer swap, and every `research_run_envelope`
   promoted from v1 to v2 (§5.1b) — gets a manifest entry, written ONCE, atomically, at the SAME
   instant as the promotion:

   ```
   {record_kind: "inference_record" | "canonical_claim" | "research_run_envelope",
    record_id: <inference_id | canonical_claim_id | envelope_id>,
    version: <inference_version | canonical_claim_version | envelope_version>,
    version_digest: <the record's own version_digest, recomputed and supplied at promotion time,
                     REQUIRED in the manifest entry even though the record-level field stays
                     schema-optional for legacy reasons (§15.2 point 5)>,
    fingerprint: <the record's stable identity fingerprint -- inference_id/canonical_claim_id's own
                  hash without prefix, or for research_run_envelope, the receipt's identity
                  fingerprint (== receipt_commitment)>}
   ```

   For `inference_record`/`canonical_claim`, this entry is exactly what `.claim_ledger_generations/
   <generation_id>.yaml`'s per-row snapshot ALREADY implicitly contains (the same fields §17.8's
   commit-proof digest is computed over) — this section makes the entry's shape EXPLICIT and
   directly comparable, reusing existing machinery rather than inventing a fourth path convention.
   For `research_run_envelope`, an analogous manifest entry is written at
   `<provenance-envelope-storage-root>/envelopes/<envelope_id>/.generation_manifest.yaml`
   (append-only; `services/provenance_envelope.py` owns this write, §17.9/N1), atomically alongside
   the v1→v2 promotion (§5.1b step 3).

**Reader rule (normative, closes both SOL-25 and SOL-26 together).** A record REACHABLE FROM a
generation manifest MUST match its manifest entry: the reader recomputes `version_digest` from the
record's CURRENT on-disk content (never trusting the record's own stored `version_digest` field in
isolation) and compares it to the manifest's entry for `(record_kind, record_id, version)`. A
mismatch is tamper-evidence — fail closed, never silently prefer the record's own bytes. A record
NOT reachable from any manifest (never promoted/committed under this contract's protocol) is
LEGACY-READ-ONLY and MINTS NO AUTHORITY — it may be read for historical/debugging purposes, but it
is never a valid `persistent_references`/`receipt_commitment` target, exactly as §17.7 step 2
already establishes for a promoted-but-unreferenced `inference_record`/`canonical_claim`.

**Why this closes both attacks.** SOL-25's digest-omission concern dissolves once the reader NEVER
trusts a record's own stored digest field in isolation — recomputing and comparing against the
manifest works whether or not the record still carries its own copy of the value. SOL-26's
version-mutation concern is closed by the COMBINATION of the widened formula (point 1: the version
integer is now part of what gets hashed) and the manifest (point 2: the honest digest for
`(record_id, version)` was recorded ONCE, at legitimate promotion, and cannot be retroactively
edited by an attacker who only controls the record file) — an attacker bumping the version integer
alone now produces a DIFFERENT digest that fails to match the manifest's entry for that
`(record_id, version)` key. See §5.1b for the worked re-run against the envelope substitution attack
(this same reader rule is what actually closes SOL-2/16/22's receipt-substitution attack, not
`version_digest` self-consistency alone) and §15.2/§18.1 for the inference/canonical-claim vectors.

### 17.8 Workspace and claim-row binding (SOL-14, NEW — normative)

The original submission's precondition 2 said only "same workspace_id" — SOL-14 named two
concrete gaps this leaves open: (1) `claim_ledger` rows have no embedded `workspace_id` field and
live under a GLOBAL `runs/<run_id>` path (confirmed against `paths.py`'s `runs` property, which is
NOT workspace-scoped, unlike `AssertionRegistry`'s own workspace-keyed root) — so a caller in
workspace B, naming run id A (a run actually owned by workspace A), could otherwise target
workspace B's inference/canonical-claim record store while rewriting run A's ledger, if ownership
is only checked via "the caller's selected workspace," not the run's OWN recorded workspace; and
(2) even within a single, correctly-scoped workspace, the original five preconditions never proved
that the SPECIFIC claim row being updated — as opposed to "some row in the right workspace" — is
the one the inference/canonical-claim record was actually resolved against, meaning an unrelated
active record could in principle be attached to the wrong claim.

**Normative rule (both parts MUST hold before any `persistent_references` write):**

1. **Ownership derives from the canonical `run.yaml`, not the caller's selected workspace alone.**
   The authoritative `workspace_id` for a `persistent_references` write is `run.yaml`'s own
   `workspace_id` field for the run owning the target `claim_ledger.yaml` — NOT merely whatever
   `workspace_id` the calling context happened to resolve for itself. The writer MUST verify: (a)
   the caller's own resolved, authenticated `workspace_id` (via `assertion_workspace.resolve_or_deny`
   or the HTTP-layer equivalent, standing directive 2) equals `run.yaml.workspace_id` for this run,
   AND (b) the `inference_record`/`canonical_claim` file being referenced resolves under THAT SAME
   `workspace_id`'s storage root (`AssertionRegistry(workspace_id=...)`'s own workspace-keyed root,
   the same scoping `assertion_materialization.py` already uses for source assertions). A mismatch
   on either (a) or (b) is a fail-closed denial, never a partial/best-effort write.
2. **The commit proof binds the exact claim row, not just the workspace (round 2, SOL-14/20,
   REVISED — the row digest now also binds the exact TARGET, not merely the row's own prior
   self).** Round 1's row-digest covered only `{claim_id, sources, conclusion/statement text}` —
   round 2's SOL-14/20 finding: "the row digest detects row drift only; it omits target kind/ID/
   version and target material/support digest. An unrelated active target can still be attached to
   an unchanged row." The commit-proof digest is now EXACTLY seven fields, frozen:

   ```
   commit_proof_digest = sha256-canonical-json-v1({
     "claim_id": <claim row's own claim_id>,
     "row_material": {"sources": <claim row's own support refs>, "conclusion_text": <claim row's own conclusion/statement text at commit time>},
     "target_kind": <"inference_record" | "canonical_claim">,
     "target_id": <inference_id | canonical_claim_id>,
     "target_version": <inference_version | canonical_claim_version>,
     "target_version_digest": <the target's own version_digest, §15.2/§16.1/§16.2 -- REQUIRED input to this digest even though version_digest is an OPTIONAL field on the target schema itself; a P4 commit MUST compute and supply the target's version_digest at commit time regardless of whether it was persisted on the record>,
     "support_refs_digest": sha256-canonical-json-v1(<the target's own source_assertion_refs at the SAME commit-time recheck instant, §17.1 item 6>),
   })
   ```

   Computed and compared against the SAME digest the record was originally resolved against,
   immediately before the atomic swap (§17.7 step 5). A mismatch — EITHER the claim row's own
   content drifted (round 1's gap) OR the target kind/id/version/support has changed or been
   substituted since resolution (round 2's gap) — aborts the commit as a typed conflict, never wires
   any reference onto a claim row or target whose content has since drifted from what was actually
   verified eligible.

   **Worked test vector — COMPLETE canonical preimage (round 3, RC-4; supersedes round 2's
   incomplete vector, SOL-14/20/28).** Round 2's vector named `claim_id: "clm_007"` and the §18.1
   inference fixture as the target, but never published the exact `row_material.sources`/
   `conclusion_text` bytes — round 3's accepted finding (SOL-28): the claimed digest
   (`e42fa121...fea1`) had no complete, independently-recomputable preimage. The full input, byte
   for byte:

   `claim_ledger` row `clm_007` (the CLAIM ROW's own shape — `claims[].sources`/`claims[].text`,
   `claim_ledger.schema.yaml` — a DIFFERENT shape from the target `inference_record`'s own
   `source_assertion_refs`; row_material records what the CLAIM ROW itself carries, not a copy of
   the target's fields):

   ```json
   {
     "claim_id": "clm_007",
     "text": "Pediatric reference intervals for CBC differ materially from adult intervals across all measured analytes.",
     "sources": [
       {"source_card_id": "src_001", "evidence_id": "ev_001", "relation": "supports", "locator": "sec:2.1"},
       {"source_card_id": "src_002", "evidence_id": "ev_002", "relation": "supports", "locator": "sec:2.2"}
     ]
   }
   ```

   Target: the §18.1 inference fixture (`target_kind: inference_record`, `target_id:
   inf_fd3ee362...464e51`, `target_version: 1`, `target_version_digest:
   8e1292fe2967aae3652dbdf87e0e1522fe387c82dcc003d81b0415bfc8321c44` — the ROUND-3 WIDENED formula,
   §15.2 item 4; round 2's `eb94ff60...f45e2` value is superseded and no longer the correct input).
   `support_refs_digest = sha256-canonical-json-v1(<the target's own two source_assertion_refs>)
   = fdcdb3a6c0dfaeccaf7f289c957f25953bf7786c11ecf43393dfe32e8cd140dd`.

   The SEVEN-FIELD assembly, exact JSON:

   ```json
   {
     "claim_id": "clm_007",
     "row_material": {
       "sources": [
         {"source_card_id": "src_001", "evidence_id": "ev_001", "relation": "supports", "locator": "sec:2.1"},
         {"source_card_id": "src_002", "evidence_id": "ev_002", "relation": "supports", "locator": "sec:2.2"}
       ],
       "conclusion_text": "Pediatric reference intervals for CBC differ materially from adult intervals across all measured analytes."
     },
     "target_kind": "inference_record",
     "target_id": "inf_fd3ee362717699c116ca3eb00c4daa982396789c03040212673a3e1a86464e51",
     "target_version": 1,
     "target_version_digest": "8e1292fe2967aae3652dbdf87e0e1522fe387c82dcc003d81b0415bfc8321c44",
     "support_refs_digest": "fdcdb3a6c0dfaeccaf7f289c957f25953bf7786c11ecf43393dfe32e8cd140dd"
   }
   ```

   `commit_proof_digest = 85a3e675772f65da81de59bdc17d2ca813f1283c3b802fc83f110fb22e46393d` — an
   independent implementer can now recompute this byte-for-byte from the published preimage above
   (round 2's `e42fa121...fea1` value is SUPERSEDED, both because it lacked a complete preimage and
   because `target_version_digest` itself changed under the round-3 widened inference formula).
   Substituting an UNRELATED active target (`target_id:
   inf_0000000000000000000000000000000000000000000000000000000000000000`,
   `target_version_digest`/`support_refs_digest` both zeroed, everything else unchanged) was
   confirmed to produce a DIFFERENT `commit_proof_digest`
   (`8466e738e045fb06e2e196fa510c22564157345ac532347e2867a1a6bfcf99df`) — this is the exact
   SOL-14/20 attack ("an unrelated active target can still be attached to an unchanged row"), now
   closed: the digest binds the row not just to its own prior self, but to the SPECIFIC target and
   that target's SPECIFIC support state at commit time. The **P7 verifying task** (§17.9) is
   `RPC-7.13`: confirm the commit-proof digest recomputation rejects every substituted-target/
   substituted-support variant of a live commit attempt, using the exact preimage above as the
   reference vector.

   **SOL-34 amendment (fix cycle FINAL, §22c): the `support_refs_digest` formula above is the
   `inference_record`-target formula only.** The `canonical_claim`-target formula is a SEPARATE,
   deliberately stronger, frozen encoding — see §22c for the full amendment text and its own
   byte-recomputable worked vector. Implementations MUST NOT apply the bare
   `sha256-canonical-json-v1(<source_assertion_refs>)` formula above to a `canonical_claim` target's
   seventh field; §22c's two-key-object formula is normative for that target kind.

### 17.9 P7 gate tasks (round 2, collected; RENUMBERED + service-named round 3, SOL-27, RC-3)

Per this round's framing principle ("for every hole schema validation cannot close, name the exact
enforcing service/function, state the MUST-grade rule, and name the P7 gate task that verifies it"),
every writer-level MUST this round introduces or revises is paired with a named P7 verification
task AND a named enforcing service/function. Collected here for a single reference point (each is
also named inline at its own normative section above).

**SOL-27 (round 3, BLOCKER, CLOSED) — task-ID collision with the governing plan.** This document's
round-2 revision repurposed `RPC-7.2`–`RPC-7.8` and invented `RPC-7.1` — but the GOVERNING plan
(`docs/project_plans/implementation_plans/enhancements/research-provenance-continuity-v1.md`,
P7 table) already assigns `RPC-7.2`–`RPC-7.11` + `RPC-7.G` to different, real gate tasks (origin/
facet gate, activity/receipt gate, report-use gate, inference/canonical-claim gate, governed read
gate, lifecycle replay gate, optional AOS gate, regression gate, docs, final evidence assembly, and
the final Tier-3 gate). **Fixed: every task this document itself invents is renumbered `RPC-7.12`
through `RPC-7.19`** — a disjoint range that cannot collide with the plan's own `RPC-7.2`–`RPC-7.11`
+ `RPC-7.G`. These eight tasks are DEEPER, cross-record-integrity verification tasks that a P7
implementer executes IN ADDITION TO (not instead of) the plan's own gates — most naturally as
sub-checks the plan's `RPC-7.13`–`RPC-7.16`-equivalent-named real tasks (e.g. the plan's own
"Inference/canonical-claim gate", "Activity/receipt gate") already cover; this document does not
assign them to a specific plan task ID beyond noting they belong to P7 scope generally.

**Design notes N1–N4 (round 3, RC-3) — the exact enforcing service/function, resolving SOL-1/11/17's
residual "writer undecided" gaps and RPC-1.1.a.**

- **N1 — origin/envelope/receipt writers.** `provenance_origin`, `research_run_envelope`, and
  `search_activity_receipt` writes are ALL owned by ONE module: `services/provenance_envelope.py`
  (the plan's own P2 `files_affected` list already names this file for exactly this scope — RC-3
  resolves design note RPC-1.1.a, §12/§21, from "P2 must decide" to this firm assignment; the
  storage-root LAYOUT itself is named at §5.1b for the envelope family specifically).
- **N2 — report-use identity, replay, and the atomic pair on `cited_ref`.** `report_ref`/`cited_ref`
  identity, replay/conflict rules (§13.5), and the `cited_ref` atomic id+version pairing (SOL-9/11's
  report-use half) are owned by `services/assertion_report_use.py` (the plan's own P3
  `files_affected` list).
- **N3 — inference/canonical record writers vs. the claim_ledger second write path.** Minting and
  validating `inference_record` (identity, `version_digest`, §15.1 eligibility) is owned by
  `services/assertion_inference.py`; minting and validating `canonical_claim` (identity,
  `version_digest`, §15.4 explicit-request gate, §17.3 `canonical_claims_allowed`) is owned by
  `services/canonical_claim_materialization.py` (both named in the plan's P4 `files_affected` list).
  The SEPARATE `claim_ledger.persistent_references` SECOND write path (§17.1's six preconditions,
  the atomic-pair rule for BOTH `inference_id`+`inference_version` and
  `canonical_claim_id`+`canonical_claim_version`, §17.7's durable-commit protocol, and §17.8's
  commit-proof digest) is owned by `services/assertion_materialization.py` — this is not a new
  design decision but a restatement of §17.2's own grounding ("P4 needs a second, separate write
  path... `_DEFERRED_REFERENCE_FIELDS`/`_reject_deferred_references` already live" in this exact
  file), now made explicit as the SOL-11/17 residual's answer.
- **N4 — post-hoc reconciliation and lifecycle impact.** The commit-time recheck's complement (P6's
  read-only reconciliation pass that detects a record whose support became invalid AFTER its own
  commit, §17.1's TOCTOU honesty note) is owned by `services/assertion_impact.py` (the plan's own P6
  `files_affected` list; already named inline at §17.1).

| Task | Verifies | Enforcing service (N1–N4) | Section |
|---|---|---|---|
| `RPC-7.12` | A crash-injection test confirming a staged/promoted `inference_record`/`canonical_claim` interrupted between §17.7 steps 1–2 or 2–5 is quarantined on recovery, never silently adopted or made citable. | N3 (`assertion_materialization.py`) | §17.7 |
| `RPC-7.13` | The commit-proof digest (seven-field, §17.8 item 2, full preimage §17.8) recomputation rejects every substituted-target and substituted-support-refs variant of a live commit attempt. | N3 (`assertion_materialization.py`) | §17.8 |
| `RPC-7.14` | Every P4-written `inference_record`'s `version_digest` (widened formula, §15.2 item 4) recomputes to its stored value AND matches its generation-manifest entry (§17.7a). | N3 (`assertion_inference.py`) | §15.2 item 4, §16.1, §17.7a |
| `RPC-7.15` | Every P4-written `canonical_claim`'s `version_digest` (widened formula, §15.2 item 3) recomputes to its stored value AND matches its generation-manifest entry (§17.7a). | N3 (`canonical_claim_materialization.py`) | §15.2 item 3, §16.1, §17.7a |
| `RPC-7.16` | No P4-written `claim_ledger` row ever has exactly one of `inference_id`/`inference_version` (or `canonical_claim_id`/`canonical_claim_version`) set (the atomic-pair rule, now writer-level per SOL-17's schema-conditional revert); no P3-written `report_assertion_use.cited_ref` ever has exactly one of a family's id/version pair set either (SOL-11's report-use half). | N3 (`assertion_materialization.py`) for claim_ledger; N2 (`assertion_report_use.py`) for `cited_ref` | §16.3, §17.1 item 4, §13.3 |
| `RPC-7.17` | `envelope.receipt_commitment` is set write-once (never mutated after its first non-null write) and always equals the referenced receipt's own `identity.fingerprint`; the v2 promotion's byte-equality rule (§5.1b point 6) and generation-manifest entry (§17.7a) are both written atomically alongside it. | N1 (`provenance_envelope.py`) | §5.1 rule 9, §5.1b, §17.7a |
| `RPC-7.18` | `provenance_origin`/`research_run_envelope` writers reject an attempted version bump (`origin_version`/`envelope_version` increment) that is not accompanied by a correspondingly recomputed `identity.fingerprint` (origin) or `version_digest` (envelope), AND (round 3) that the recomputed value matches the generation-manifest entry (§17.7a), not merely the record's own stored field. | N1 (`provenance_envelope.py`) | §4.1 rule 7a, §5.1b, §17.7a |
| `RPC-7.19` | The commit-time recheck (§17.1 item 6: support-assertion lifecycle, run mapping, resolved capability flags) actually fires and aborts a commit under concurrent lifecycle/config mutation, per the bounded-concurrency model (§17.1's TOCTOU honesty note) — never claimed as full system-wide serialization. | N3 (`assertion_materialization.py`) commit path; N4 (`assertion_impact.py`) post-hoc reconciliation | §17.1 |

This is a P4/P7 implementation-and-verification checklist, not something this Mode-B document
executes — no code is written or gate granted here. No closure above leaves its enforcing
method/service "undecided" (closing the residual SOL-1/11/17 PARTIAL findings).

## 18. AC RPC-4 matrix — typed skip outcomes (inference/canonical-claim)

Every row below ends in **no durable record, no reference write** — a skip is never a partial
record and never a partial `persistent_references` pair. Codes follow the existing `_Abstain`
naming convention already used by `assertion_materialization.py` (snake_case, one word per
concept) so a future P4 implementation can adopt them directly without inventing a parallel
vocabulary.

| Condition | Typed skip code | Applies to |
|---|---|---|
| Zero resolvable bases named | `empty_support` | inference, canonical claim |
| A named base id/version does not resolve to any existing record | `unresolved_support_ref` | inference, canonical claim |
| A resolved base's `lifecycle_state`/`status` is not eligible/active | `stale_support` | inference, canonical claim (also reused at COMMIT time, SOL-15b, §17.1 item 6) |
| Bases resolve across more than one `workspace_id` | `mixed_workspace_support` | inference, canonical claim |
| `reasoning.producer` omitted where the caller's own policy requires attribution | `producer_omitted` | inference only (canonical_claim has no `reasoning`/`producer` field) |
| Two or more bases contradict each other with no caller-supplied resolution | `ambiguous_support` | canonical claim (via mixed `relation: supports`/`contradicts` on the same statement with no explicit adjudication) |
| A base's `relation` conflicts with the claim's own statement polarity in a way the caller never resolved | `conflicting_support` | canonical claim |
| Caller attempts to derive a canonical claim from usage patterns rather than an explicit request | `implicit_merge_rejected` | canonical claim (§15.4) |
| A prior candidate/base is substituted for a different one after initial resolution, before publish | `substitution_rejected` | inference, canonical claim |
| §17.1's SIX preconditions (SOL-13/14/15b widened this from five) are only partially satisfied at write time, OR the generation-marker CAS (§17.7 step 4) or claim-row digest binding (§17.8 item 2) fails | `partial_write_rejected` | the `persistent_references` update step (F11 reversal), not the inference/canonical-claim record write itself |
| Same input replays with identical bytes | *(not a skip)* — idempotent success, same `MaterializationConflict`-style comparison as elsewhere | inference, canonical claim |
| Same target id/version, differing bytes | `replay_conflict` | inference, canonical claim |
| `canonical_claims_allowed` resolves `False` at RESOLUTION time (F12, §17.3), or is found `False` on the SOL-15b commit-time recheck | `canonical_claims_disabled` | canonical claim only |
| Run mapping no longer authorizes the caller at commit time (SOL-15b, §17.1 item 6) | `run_mapping_revoked` | the `persistent_references` update step |
| A staged or promoted record was never referenced by any `claim_ledger` row after a crash (SOL-13, §17.7 step 6) | *(not a skip — a recovery-sweep outcome)* `quarantined_orphan` | recovery tooling only, never a live write-path outcome |

### 18.1 JSON fixtures for AC RPC-4 (V-1)

**Inference-record positive fixture** (validated against `schemas/inference_record.schema.yaml`
with zero errors, §22):

```json
{
  "schema_version": "1.0", "type": "inference_record",
  "inference_id": "inf_fd3ee362717699c116ca3eb00c4daa982396789c03040212673a3e1a86464e51",
  "inference_version": 1,
  "conclusion": "Pediatric reference intervals for CBC differ materially from adult intervals across all measured analytes.",
  "source_assertion_refs": [
    {"assertion_id": "ast_4444444444444444444444444444444444444444444444444444444444444444", "assertion_version": 1},
    {"assertion_id": "ast_5555555555555555555555555555555555555555555555555555555555555555", "assertion_version": 2}
  ],
  "reasoning": {"summary": "Synthesized across two source assertions reporting age-stratified CBC intervals.", "method": "comparative_synthesis", "producer": "agent-research-1"},
  "status": "active",
  "version_digest": "8e1292fe2967aae3652dbdf87e0e1522fe387c82dcc003d81b0415bfc8321c44"
}
```

`inference_id` follows the §15.2 frozen formula exactly (worked test vector reproduced here).
`version_digest` (round 2, SOL-12/18; WIDENED round 3, SOL-25/26, RC-2) follows §15.2 item 4's
formula over `{conclusion, source_assertion_refs, reasoning, status, inference_version}` — a
separate value from `inference_id` (which excludes `status`/`inference_version`), recomputed and
confirmed to reproduce this exact value for this fix cycle. (Round 2's value, `eb94ff60...f45e2`,
was computed against the narrower pre-round-3 formula and is superseded.)

**Canonical-claim positive fixture** (validated against `schemas/canonical_claim.schema.yaml` with
zero errors, §22), citing the inference above via the SOL/F3 `inference_refs` amendment:

```json
{
  "schema_version": "1.0", "type": "canonical_claim",
  "canonical_claim_id": "ccl_47cc4458b070a6e4e0a4b1dfb52e223e896a12b994219a7921f41334c870da15",
  "canonical_claim_version": 1,
  "state": "active",
  "statement": "Pediatric CBC reference intervals differ from adult intervals.",
  "source_assertion_refs": [
    {"assertion_id": "ast_4444444444444444444444444444444444444444444444444444444444444444", "assertion_version": 1, "relation": "supports"}
  ],
  "inference_refs": [
    {"inference_id": "inf_fd3ee362717699c116ca3eb00c4daa982396789c03040212673a3e1a86464e51", "inference_version": 1, "relation": "supports"}
  ],
  "version_digest": "86d6007be832a210049f0ec44a86479b8223c7bab23363fb00631ac0d88a84e0"
}
```

`canonical_claim_id` follows the §15.2 frozen entity-identity formula exactly (worked test vector
reproduced here; note it is computed over `{statement, source_assertion_refs}` only, NOT over
`inference_refs`/`state`/version/reversal fields, per §15.2's stable-entity-id-vs-per-version-digest
split). `version_digest` (round 2, SOL-12/18; WIDENED round 3, SOL-25/26, RC-2) follows §15.2 item
3's formula over `{statement, source_assertion_refs, inference_refs, state,
canonical_claim_version, replaces, replacement_claims, reversal}` (the three trailing fields absent
on this fixture, canonicalizing as `null` via `.get()`) — recomputed and confirmed to reproduce this
exact value for this fix cycle. (Round 2's value, `7cceafab...f75e4`, was computed against the
narrower pre-round-3 formula and is superseded.)

**Typed-skip narrative — `stale_support` (no record produced).** A caller requests an inference
citing `source_assertion_refs: [{assertion_id: "ast_4444...4444", assertion_version: 1}]`, but that
exact `(assertion_id, assertion_version)` currently has `lifecycle_state: invalidated` on disk
(e.g. a corrected-edition lifecycle event landed after the caller last read it). Per §15.1 item 2,
the WHOLE inference candidate is ineligible — no `inference_record` file is written, no
`inference_id` is minted, and the caller receives the typed skip code `stale_support`. There is no
JSON fixture to show for this outcome (nothing is created) — this is the same "narrative absence"
convention used throughout this document (e.g. `provenance_origin` fixture (c),
`report_assertion_use` fixture (b)).

**Replay-conflict narrative pair — same target id, forged/differing bytes (REJECTED, mirrors
§13.6(f)/(g) for the report-use schema).** (i) **Replay:** re-preparing the exact inference fixture
above a second time, from the identical `{conclusion, source_assertion_refs, reasoning}` material,
recomputes the identical `inference_id` — the writer's second attempt is an idempotent no-op
success (verified: recomputing the fingerprint from the fixture's exact material reproduces
`fd3ee362...464e51`, §22). (ii) **Conflict:** a hypothetical second write attempt claims the SAME
`inference_id` (`inf_fd3ee362...464e51`) but supplies a different `conclusion` string. Recomputing
the fingerprint over THAT candidate's actual material yields a fingerprint that does NOT equal
`fd3ee362...464e51` — the writer MUST reject this as `replay_conflict` (a forged/corrupted target-
id claim, the same class of check `assertion_identity.py::validate_source_assertion_identity`
performs for `source_assertion.schema.yaml`), never silently overwrite the existing record, and
never accept it as a legitimate replay. The honest outcome for a genuinely different conclusion is
a NEW, independently-computed `inference_id` — claiming the OLD id for different content is exactly
what this check exists to reject.

## 19. F13 — lifecycle vocabulary: minor amendment now needed (SOL-15a revises this conclusion)

`schemas/assertion_lifecycle_event.schema.yaml` was originally confirmed sufficient for
RPC-1.3/RPC-1.4's own needs without amendment (F13). **SOL-15a proved this conclusion incomplete: a
narrow amendment IS needed** (§16.4) — the schema's `target.kind` and `dependent_actions.object_kind`
enums were always sufficient (see below), but `transition.from` was missing the `active` value an
`inference_record`-targeted event actually needs:

- `target.kind` already enumerates `inference_record` and `canonical_claim` (the two RPC-1.4
  object kinds) alongside the pre-existing `source_edition`/`passage`/`source_assertion` — **still
  sufficient, unchanged.**
- `dependent_actions.object_kind` already enumerates `canonical_claim_edge`, `inference`, and
  `report_revision` — exactly the three RPC-1.3/1.4 object families (report-use records are the
  concrete instance of a `report_revision` dependent action; §17.4 confirms P6 consumes this
  read-only) — **still sufficient, unchanged.**
- `inference_record.status` was missing `tombstoned` to match `target.kind: inference_record` +
  `transition.to: tombstoned` — closed by amending `inference_record.schema.yaml` itself (§16.2),
  NOT the lifecycle schema — **unchanged conclusion from the original submission.**
- **NEW (SOL-15a): `transition.from` was missing `active`** — an `inference_record`'s OWN starting
  state (`active`, not `eligible`) had no way to be named on the `from` side of a direct
  `target.kind: inference_record` event. This IS a gap in the lifecycle schema itself (not
  resolvable by amending `inference_record.schema.yaml` alone, since `transition.from` lives on
  `assertion_lifecycle_event.schema.yaml`) — closed by §16.4's additive `active` enum widening + 3
  new `oneOf` arms + 1 new conditional.
- The `canonical_claim.state` vs. generic-vocabulary mismatch (§17.5) remains a genuine,
  pre-existing tension, still explicitly NOT resolved by widening either schema in this document —
  recorded as a design note for P6, per this task's instruction to prefer no amendment when the gap
  is not concretely proven for RPC-1.3/1.4's own scope. SOL-15a's `active` widening is deliberately
  scoped to `inference_record` only and does not touch this tension.

**Revised conclusion: ONE narrow, additive amendment to `assertion_lifecycle_event.schema.yaml` in
this part (§16.4) — the original submission's "no amendment" conclusion was incomplete.**

## 20. Completed contract-tree inventory (Parts 1+2)

Every file touched or introduced by the full `RPC-1.G` contract freeze (Parts 1+2 together),
relative to baseline `e76784b`, after the SOL round 1, round 2, AND round 3 fix cycles. No file
changes category (NEW/AMENDED) or moves between the "amended" and "byte-identical" lists across any
round — round 2/3 revise fields WITHIN the same files round 1 already touched; no NEW file was
introduced by round 3 (the round-3 storage-layout/manifest paths named at §5.1b/§17.7a are runtime
DATA paths this contract freezes the shape of, not additional schema/doc files in this tree).

| File | Status | Task |
|---|---|---|
| `schemas/provenance_origin.schema.yaml` | NEW (revised, SOL-1/round1; further revised, SOL-1/7a/24/round2; unchanged by round 3) | RPC-1.1 |
| `schemas/research_run_envelope.schema.yaml` | NEW (revised, SOL-2/3/6/round1; further revised, SOL-2/16/6/22/24/round2; **REDESIGNED round 3**, SOL-2/16/22/RC-1 — v1/v2 pairing protocol, `allOf` partition, `envelope_version: maximum 2`) | RPC-1.2 |
| `schemas/search_activity_receipt.schema.yaml` | NEW (revised, SOL-2/3/4/7/8/round1; further revised, SOL-7/24, SOL-8/23/round2; further revised round 3, RC-1 — `envelope_ref.envelope_version: const 1`) | RPC-1.2 |
| `schemas/search_run.schema.yaml` | AMENDED (additive: `retrieval.activity_id` + SOL-8 exclusivity `allOf`; unchanged by round 2 or round 3) | RPC-1.2 |
| `schemas/report_assertion_use.schema.yaml` | NEW (revised, SOL-9/10/round1; further revised, SOL-10/21, SOL-1/22/round2; further revised round 3, SOL-10/RC-5 — `rights_triage_failure.detail` `minLength` removed) | RPC-1.3 |
| `schemas/inference_record.schema.yaml` | AMENDED (additive: `status: tombstoned`/round1; further amended, additive `version_digest`/SOL-12/18/round2; **WIDENED FORMULA round 3**, SOL-25/26/RC-2 — field shape unchanged, doc-level formula only, still additive against baseline) | RPC-1.4 |
| `schemas/canonical_claim.schema.yaml` | AMENDED (additive: `inference_refs`/round1; further amended, additive `version_digest`/SOL-12/18/round2; **WIDENED FORMULA round 3**, SOL-25/26/RC-2 — field shape unchanged, doc-level formula only, still additive against baseline) | RPC-1.4 |
| `schemas/claim_ledger.schema.yaml` | **AMENDED (additive: `persistent_references.inference_version`/SOL-11/round1; round-1 schema conditional REVERTED round 2, SOL-17; unchanged by round 3)** | RPC-1.4 |
| `schemas/assertion_lifecycle_event.schema.yaml` | **AMENDED (additive: `transition.from: active` + 3 `oneOf` arms + 1 conditional/SOL-15a/round1; further amended, `eligible -> *` scoping conditional/SOL-15/round2 — the ONE documented narrowing, §2/§22; unchanged by round 3)** | RPC-1.4 |
| `docs/dev/architecture/research-provenance-contract-freeze.md` | NEW (this document, Parts 1+2, SOL round 1, round 2, AND round 3 revision; **§22c amendment added FINAL round** — SOL-34 canonical-claim-target `support_refs_digest` refreeze, doc-text only, no schema/field-shape change) | RPC-1.1–1.4 |

Files explicitly confirmed byte-identical to `e76784b` (read-authority, never amended by this
freeze): `schemas/search_request.schema.yaml`, `schemas/source_assertion.schema.yaml`,
`schemas/report_draft.schema.yaml`, `schemas/external_research_import_receipt.schema.yaml`,
`schemas/knowledge_activity_receipt.schema.yaml`, and every `src/research_foundry/**/*.py`
production file — unchanged and re-confirmed by round 3 (`git diff e76784b` against these six shows
zero output; `research_run_envelope.schema.yaml`/`search_activity_receipt.schema.yaml`/
`report_assertion_use.schema.yaml` are NEW schemas per §1/§2, so round 3's redesign of their internal
shape is not subject to the additive-only constraint — only `inference_record.schema.yaml`/
`canonical_claim.schema.yaml` are baseline-shipped AND round-3-touched, and both remain additive-only
per the row above).

## 21. Findings and open items for the orchestrator (Part 2)

In addition to Part 1 §12's remaining design note (RPC-1.2.a, unchanged — RPC-1.1.a is RESOLVED,
§12/§17.9 N1), Part 2's open items are now narrower after all three fix cycles:

- **F17 — RESOLVED round 1 (SOL-11, §16.3/§17.6), enforcement layer REVISED round 2 (SOL-17), writer
  named round 3 (RC-3, §17.9 N3).** No longer open; the round-1 schema conditional is reverted, the
  atomic-pair rule is now writer-level (§16.3, §17.1 item 4, owned by `assertion_materialization.py`,
  verified by P7 task `RPC-7.16`, §17.9).
- **RPC-1.3.a — RESOLVED this fix cycle (SOL-9, §13.1).** The `run_report` family's
  `report_revision_id` minting algorithm is now frozen with a worked test vector, superseding the
  original open item. Unaffected by rounds 2/3.
- **RPC-1.4.a — `canonical_claim.state` vs. generic lifecycle vocabulary (§17.5)** — a genuine,
  pre-existing tension, still explicitly left unresolved pending a concrete P6 use case; not a
  blocking defect against `RPC-1.G`. SOL-15a's `active` widening (§16.4) and round 2's `eligible`
  scoping (§16.4a) are both scoped to their own specific target kinds and do not touch this tension.
- **RPC-1.1.b — envelope cross-version discovery (round 2, new design note; storage layout NAMED
  round 3, RC-1, not blocking).** §5.1b establishes that an activity's `research_run_envelope` may
  now exist at multiple `envelope_version` values sharing one `envelope_id` (the v1→v2 write-once
  transition). A reader wanting "the current state of this activity's envelope" must look up by
  `envelope_id` and select the HIGHEST `envelope_version` on file — this document freezes that this
  is the correct read pattern, and round 3 additionally names the storage layout
  (`<root>/envelopes/<envelope_id>/v1.yaml`/`v2.yaml`, §5.1b) and the owning module (N1,
  `services/provenance_envelope.py`, §17.9) — but does not name the exact P2 read-path FUNCTION that
  implements the "highest version" lookup (P2's own scope, same class of note as RPC-1.2.a above).

None of the three items above block `RPC-1.G` — RPC-1.1.b/RPC-1.2.a/RPC-1.4.a are scoped,
single-owner design decisions for P2/P6 to resolve when they execute, exactly like before; F17,
RPC-1.1.a, and RPC-1.3.a are simply no longer open at all.

## 22. Fix-cycle changelog (SOL round 1)

Adversarial cross-model review `gpt-5.6-sol` BLOCKED `RPC-1.G` on 2026-07-28 with findings SOL-1
through SOL-15 (`.claude/worknotes/rpc-sol-round1-findings.md`); a separate
`task-completion-validator` pass APPROVED with MINOR note V-1. This section maps every finding to
its resolution, the exact file/section that resolves it, and the validation performed. All
validation below was run with `/Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python`
using `jsonschema.Draft202012Validator` (`.check_schema()` on every touched/new schema, plus
targeted positive/negative instance validation for each rewritten partition) as part of this fix
cycle; no automated test suite file was added or modified (Mode B, no `src/**/*.py` changes).

| Finding | Resolution | File(s) / section(s) |
|---|---|---|
| SOL-1 (origin identity substitution) | `identity.material_fields` expanded from 5 to all 9 immutable fields (`producer`, `external_receipt_ref`, `parent_origin_refs`, `created_at` added); `origin_id == "pvo_" + fingerprint` made normative; fixtures (a)/(b) corrected so the ID suffix equals the fingerprint. | `schemas/provenance_origin.schema.yaml` (`identity` block); freeze doc §4.1 rule 7, §4.2 (a)/(b)/(d) |
| SOL-2 (envelope/receipt no integrity binding) | Both schemas gained an `identity` block bound to `"rre_"`/`"sar_"` + fingerprint; cross-record equality rule specified normatively; circular-dependency risk resolved by excluding `activity_id` from the envelope's own material fields (§5.1a). | `schemas/research_run_envelope.schema.yaml`, `schemas/search_activity_receipt.schema.yaml` (`identity` blocks); freeze doc §5.1 rule 7, §5.1a, §5.3 |
| SOL-3 (planned/planned_run literal mismatch) | Receipt's `activity_kind` enum changed from `planned` to `planned_run`, matching the envelope byte-for-byte; paired-record equality fixture added. | `schemas/search_activity_receipt.schema.yaml` (`activity_kind` enum); freeze doc §5.2 fixture (a) |
| SOL-4 (denied partition leaks state) | `catalog_generation_id`/`decided_at` forced `null` on denial (previously unconstrained); `denial_reason` closed to a single-value enum (`not_authorized_or_not_found`). | `schemas/search_activity_receipt.schema.yaml` (`selection_receipt` + denial `allOf`); freeze doc §5.1 rule 5, §5.2 fixture (c) |
| SOL-5 (pre-workspace denial fabricates identity) | Normative rule added: pre-resolution denial is ephemeral/API-only, never a durable receipt; canonical receipts exist only after `resolve_or_deny` succeeds. | freeze doc §5.2 fixture (c-1) |
| SOL-6 (AOS absence/denial underspecified) | `aos_refs` removed from envelope's top-level `required` (omission is now canonical absence); populated sub-fields require `minLength: 1`; ONE canonical post-auth denial envelope (§5.2 fixture c) reused for AOS-ref denial too; per-kind regex deliberately NOT added (documented deviation, no shipped AOS ID convention exists). | `schemas/research_run_envelope.schema.yaml` (`aos_refs`, `required`); freeze doc §9 |
| SOL-7 (outcome partition incomplete/contradictory) | Added `empty` outcome (authorized, zero candidates); rewrote all five outcomes as a complete, disjoint `allOf` partition with exact null/non-null rules for every field; added `fallback_reason` (previously unenforced). | `schemas/search_activity_receipt.schema.yaml` (`selection_receipt.outcome` enum + 5-branch `allOf`); freeze doc §5.1 rule 4, §5.2 fixtures (b)/(d)/(e) |
| SOL-8 (CARP rebase lossy; conflicting authorities) | `selected_evidence_versions[]` entries gained optional `question_id`/`decided_at` (per-question membership preserved); `search_run.retrieval` gained an `allOf` making `activity_id` (non-null) and `selections[]` mutually exclusive. | `schemas/search_activity_receipt.schema.yaml` (`selected_evidence_versions.items`), `schemas/search_run.schema.yaml` (`retrieval.allOf`); freeze doc §5.1 rule 8, §6 rows 1/4 |
| SOL-9 (report-use identity has multiple encodings) | `report_ref`/`cited_ref` inactive arms made explicitly required-and-null (never omittable); `run_report` family's `report_revision_id` formula frozen with a worked test vector; canonical-JSON byte rule specified by reference to `assertion_identity.py`. | `schemas/report_assertion_use.schema.yaml` (`report_ref`/`cited_ref` `required`, `report_revision_id` conditional pattern); freeze doc §13.1 |
| SOL-10 (`rights_snapshot` contradicts shipped rights schema) | `rights_snapshot` now byte-identical to `source_assertion.rights_summary` (all fields + link-before-assert guard); bound into `identity.material_fields`. | `schemas/report_assertion_use.schema.yaml` (`rights_snapshot`, `identity.material_fields`); freeze doc §13.4, §13.5 |
| SOL-11 (inference-version propagation unresolved) | `claim_ledger.persistent_references` gained optional `inference_version` + a conditional requiring it whenever `inference_id` is non-null; resolves F17 by picking option 1 explicitly. | `schemas/claim_ledger.schema.yaml` (`persistent_references.inference_version` + `allOf`); freeze doc §16.3, §17.6 |
| SOL-12 (inference/canonical identity not actually frozen) | Doc language changed from "recommendation... not a requirement" to MUST; formula frozen with worked test vectors for both inference (single content hash) and canonical claim (entity id + per-version digest split); confirmed zero extant instances exist (no schema `pattern` added, by design, per point 4). | freeze doc §15.2 |
| SOL-13 (F11 lacks atomic record/reference visibility) | Durable-commit protocol frozen: staged write → atomic promote → per-run lock → generation-marker CAS → final locked re-read → atomic pointer swap; deterministic quarantine rule for orphaned staged/unreferenced records. | freeze doc §17.7 |
| SOL-14 (F11 doesn't bind workspace/claim row) | Ownership now derives from canonical `run.yaml.workspace_id` (not the caller's selected workspace alone); commit proof now includes an exact claim-row digest binding (`claim_id` + sources + conclusion). | freeze doc §17.8 |
| SOL-15 (dynamic lifecycle/capability bypass F11) | (a) `assertion_lifecycle_event.transition.from` widened with `active` + 3 new `oneOf` arms + 1 conditional restricting `active` to `target.kind: inference_record`. (b) §17.1 gained a sixth precondition: support-assertion lifecycle, run mapping, and resolved capability flags ALL rechecked under the same serialization barrier immediately before commit. | `schemas/assertion_lifecycle_event.schema.yaml`; freeze doc §16.4, §17.1 item 6, §17.3, §19 |
| V-1 (AC RPC-4 lacks JSON fixtures) | Added inference-record positive fixture, canonical-claim positive fixture, a typed-skip narrative (`stale_support`), and a replay/replay-conflict narrative pair — for both `report_assertion_use` (§13.6 (f)/(g)) and `inference_record`/`canonical_claim` (§18.1). | freeze doc §13.6 (f)/(g), §18.1 |

**Directive deviations (documented per the fix-cycle instructions):**

- **SOL-6's "per-kind pattern if cheap"**: NOT added. No AOS ref ID convention is shipped anywhere
  in this repo to freeze against — see §9's full rationale. `minLength: 1` (closing the actual
  reported gap, an empty-string "present but empty" ref) was added instead.
- **SOL-12's schema-level identity freeze**: implemented as a DOC-level MUST with worked test
  vectors, NOT as a new schema `pattern` on `inference_id`/`canonical_claim_id`. This matches the
  original submission's own §14 rationale (avoid freezing a shape before P4's writer exists to
  validate it against) and the finding's own text ("remove the... contradiction" targets the
  MUST-vs-recommendation language, not necessarily a schema-level regex) — see §15.2 point 4 for
  the explicit justification.

**Nothing else in SOL-1 through SOL-15 or V-1 was left unresolved (as of round 1).**

## 22a. Fix-cycle changelog (SOL round 2)

Adversarial cross-model review `gpt-5.6-sol` BLOCKED `RPC-1.G` AGAIN on 2026-07-28, re-reviewing the
round-1 revision: five findings CLOSED, five REOPENED with concrete accepted-attack instances (SOL-1,
SOL-2, SOL-6, SOL-8, SOL-10, SOL-11, SOL-12, SOL-13, SOL-14, SOL-15 — ten of the original fifteen were
marked REOPENED or PARTIAL), and nine NEW findings SOL-16 through SOL-24
(`.claude/worknotes/rpc-sol-round2-findings.md`). This section maps every round-2 finding to its
resolution. **Framing principle applied throughout:** every fix below either (a) closes the hole at
the schema layer (empirically re-verified), or (b) — where a schema alone cannot express
cross-record integrity — names the exact enforcing service/function, states the MUST-grade rule, and
names the P7 gate task that verifies it (§17.9 collects all such tasks). All validation below was run
with `/Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python` using
`jsonschema.Draft202012Validator` (`.check_schema()` on all nine touched/new schemas, plus targeted
positive/negative instance validation for every rewritten partition) and a canonical-JSON SHA-256
script matching `assertion_identity.py`'s exact convention, both as part of this fix cycle.

| Finding | Round-2 status | Resolution | File(s) / section(s) |
|---|---|---|---|
| SOL-1 (origin version mutation, REOPENED) | REOPENED → CLOSED | `origin_version` joins `provenance_origin.identity.material_fields` (10 fields total) — a version bump now necessarily changes the fingerprint/`origin_id`. Re-run: bumping `origin_version` 1→999 with the identity fields unchanged now yields a fingerprint (`af04c5bf...`) that differs from the honest value (`d34184a1...`), closing the accepted attack. | `schemas/provenance_origin.schema.yaml` (`identity.material_fields`); freeze doc §4.1 rule 7/7a, §4.2 fixture (d-1) |
| SOL-2/SOL-16 (envelope↔receipt substitution, REOPENED/BLOCKER) | CLOSED | New `receipt_commitment` field on the envelope: `null` at creation, write-once to the receipt's own `identity.fingerprint`, excluded from `identity.material_fields` (avoids circularity), recorded via an `envelope_version` bump with a new `version_digest` field proving the bump (both versions retained, same `envelope_id`). New §5.3 rule 6: `envelope.receipt_commitment == receipt.identity.fingerprint`. Re-run: two different receipts' fingerprints as candidate `receipt_commitment` values were confirmed to produce two different `version_digest` values — no single commitment can honestly cover two different receipts. | `schemas/research_run_envelope.schema.yaml` (`receipt_commitment`, `version_digest`); freeze doc §5.1 rule 9, §5.1b, §5.3 rule 6 |
| SOL-3 (planned/planned_run literal, CLOSED round 1) | Unaffected | No change this round. | — |
| SOL-4 (denied partition leaks state, CLOSED round 1) | Unaffected | No change this round. | — |
| SOL-5 (pre-workspace denial ephemeral, CLOSED round 1) | Unaffected | No change this round. | — |
| SOL-6/SOL-22 (AOS `{}}`/partial-null aliases, REOPENED) | CLOSED | `research_run_envelope.aos_refs` gains `minProperties: 1` (rejects `{}}`); `project_ref`/`intent_ref`/`knowledge_ref` are no longer nullable (a caller omits a sub-ref rather than nulling it, rejecting partial-null aliases like `{"project_ref": null}`). Re-run: both round-2 accepted shapes (`{}}` and `{"project_ref": null}`) now REJECT; omission, explicit top-level `null`, and a partial-but-fully-populated object all still ACCEPT and converge (only one absence encoding survives). | `schemas/research_run_envelope.schema.yaml` (`aos_refs`); freeze doc §5.1 rule 12, §9 |
| SOL-7/SOL-24 (blank strings, PARTIAL/MAJOR) | CLOSED | `minLength: 1` added to every required non-null outcome-arm string (`source`, `catalog_generation_id`, `degraded_reason`, `fallback_reason` on `search_activity_receipt`) plus an audit pass across all four NEW schemas' remaining free-text fields (`provenance_origin.locator`/`method.mechanism`/`producer.*`; `research_run_envelope.parent_run_ref`; `search_activity_receipt.purpose`/`scope.provider`/`scope.site`/`scope.corpus`/`selected_evidence_versions[].question_id`; `report_assertion_use.report_ref.report_id`/`report_draft_id`/`rights_snapshot.rights_triage_failure.detail`). Re-run: `source: ""`, `degraded_reason: ""`, `fallback_reason: ""` all now REJECT. | `schemas/provenance_origin.schema.yaml`, `schemas/research_run_envelope.schema.yaml`, `schemas/search_activity_receipt.schema.yaml`, `schemas/report_assertion_use.schema.yaml`; freeze doc §5.1 rule 10 |
| SOL-8/SOL-23 (per-question membership, REOPENED/BLOCKER) | CLOSED | New `selection_origin` discriminator (`catalog_planning`/`search`) on each `selected_evidence_versions[]` entry; a new `allOf` requires non-null `question_id` + `decided_at` when `selection_origin: catalog_planning`. Plain `search`/omitted entries are unaffected. Re-run: a `catalog_planning` entry missing `question_id` or `decided_at` now REJECTS; a plain entry with both omitted still ACCEPTS. | `schemas/search_activity_receipt.schema.yaml` (`selected_evidence_versions.items`); freeze doc §5.1 rule 8, §6 row 1, §5.2 fixture (f) |
| SOL-9 (report-use multiple encodings, CLOSED round 1) | Unaffected | No change this round. | — |
| SOL-10/SOL-21 (rights snapshot copy impossibility, REOPENED/BLOCKER) | CLOSED | `rights_snapshot`'s `required` list REMOVED entirely, matching `source_assertion.rights_summary`'s own zero-required-fields shape exactly — any value valid as a source `rights_summary` (including `{}}`) is now guaranteed valid as a snapshot. New canonical-normalization rule: every absent sub-field (including nested `restrictions.*`) is expanded to its schema-documented default BEFORE hashing, so semantically-identical sources with different shorthand contribute identical fingerprint bytes. Re-run: `rights_snapshot: {}}` now validates (§13.6 fixture (h)); `fingerprint(normalize({})) == fingerprint(normalize(fully-spelled))` confirmed by direct computation. | `schemas/report_assertion_use.schema.yaml` (`rights_snapshot`); freeze doc §13.4, §13.6 fixture (h) |
| SOL-11 (inference-version propagation, CLOSED round 1) | Superseded by SOL-17 | See SOL-17 below — the round-1 mechanism (a schema conditional) is reverted; the underlying gap (F17) stays resolved via a writer-level rule instead. | §16.3, §17.6 |
| SOL-12/SOL-18 (identity not frozen / no persisted digest, REOPENED/BLOCKER) | CLOSED (formula WIDENED + vector SUPERSEDED round 3, SOL-25/26 — see §22b) | New OPTIONAL, additive `version_digest` field on BOTH `canonical_claim.schema.yaml` (over `{statement, source_assertion_refs, inference_refs, state}`) and `inference_record.schema.yaml` (over `{conclusion, source_assertion_refs, reasoning, status}`) — a real, persisted, reader/replay-validated field, not merely a documented formula. Worked test vectors computed for both (round 3 widened the formula to also cover the version integer and, for canonical claims, `replaces`/`replacement_claims`/`reversal` — see §15.2/§22b). P7 tasks `RPC-7.14`/`RPC-7.15` verify recomputation. Legacy absence tolerated read-only. | `schemas/canonical_claim.schema.yaml`, `schemas/inference_record.schema.yaml`; freeze doc §15.2 items 3–4, §18.1 |
| SOL-13/SOL-19 (durable protocol underspecified, REOPENED/BLOCKER) | CLOSED | Concrete marker paths/schema frozen, reusing `assertion_materialization.py`'s own P3 pointer convention: staged records at `<AssertionRegistry-root>/.staging/<record_id>/` (INVISIBLE to all readers, the sole pre-promotion visibility boundary); promoted records at `<AssertionRegistry-root>/inferences/`\`/canonical_claims/<id>/<version>.yaml`; the claim-ledger's OWN generation pointer at `runs/<run_id>/claims/.claim_ledger_published.yaml` + `.claim_ledger_generations/<generation_id>.yaml`, CAS operand = `generation_id = "clg_" + sha256-canonical-json-v1({run_id, persistent_references_snapshot})` (content-addressed, never a counter, matching `AssertionCatalog.rebuild()`'s own rationale); lock path `runs/<run_id>/claims/.claim_ledger.lock`; recovery quarantine at `<AssertionRegistry-root>/quarantine/<record_id>/`. Explicit: a promoted-but-unreferenced record is INVISIBLE for citation and quarantine-eligible, even though file-system-discoverable — closing "promotes a final discoverable record before reference publication." P7 task `RPC-7.12`. | freeze doc §17.7 |
| SOL-14/SOL-20 (row binding incomplete, REOPENED/BLOCKER) | CLOSED (vector SUPERSEDED round 3, SOL-28 — see §22b) | Commit-proof digest widened from `{claim_id, sources, conclusion/statement text}` to the full seven-field set: `{claim_id, row_material: {sources, conclusion_text}, target_kind, target_id, target_version, target_version_digest, support_refs_digest}`. Worked test vector computed (`e42fa1210aa916df557b37ef02b7a1590aaf8eb34a87c18b54ddc6b418abfea1` — round 3 found this incomplete/unreproducible and replaced it, §17.8/§22b); substituting an unrelated active target (different id/version_digest/support digest) confirmed to change the commit-proof digest. P7 task `RPC-7.13`. | freeze doc §17.8 item 2 |
| SOL-15 (over-wide arms + TOCTOU, REOPENED/BLOCKER) | CLOSED | (a) New `allOf` conditional scopes `transition.from: eligible` to `target.kind ∈ {source_edition, passage, source_assertion}` (the exhaustive set whose own vocabulary starts at "eligible"), closing the previously-accepted `eligible→stale` for `canonical_claim`/`inference_record` — a documented, justified narrowing (zero extant instances affected). Full enumeration table added. (b) TOCTOU honesty: the per-run lock is now explicitly scoped to "ledger+record writers only"; config/lifecycle mutations outside the lock are covered by the commit-time recheck (item 6) plus post-hoc reconciliation via `assertion_impact` (P6) — stated as a bounded concurrency model, not full serialization. P7 task `RPC-7.19`. | `schemas/assertion_lifecycle_event.schema.yaml`; freeze doc §16.4a, §17.1 (TOCTOU note) |
| SOL-16 | See SOL-2 above (same finding, BLOCKER severity). | — | §5.1 rule 9, §5.1b |
| SOL-17 (claim-ledger conditional rejects baseline-valid legacy instance, NEW/BLOCKER) | CLOSED | The round-1 schema `allOf` conditional is REVERTED — `inference_version` is a plain optional integer again, no conditional. Re-verified empirically: `{persistent_references: {inference_id: "legacy-inf"}}` (no version) now validates (round 1 rejected it). The atomic-pair rule moves to a writer-level MUST (§17.1 item 4, unchanged text) verified by P7 task `RPC-7.16`; read semantics for a version-absent `inference_id` reference are now explicit (`legacy_unresolved`-class typed skip, never resolved to "latest" implicitly). | `schemas/claim_ledger.schema.yaml`; freeze doc §16.3, §17.6 |
| SOL-18 | See SOL-12 above (same finding, canonical-claim half). | — | §15.2 item 3 |
| SOL-19 | See SOL-13 above (same finding). | — | §17.7 |
| SOL-20 | See SOL-14 above (same finding). | — | §17.8 item 2 |
| SOL-21 | See SOL-10 above (same finding). | — | §13.4 |
| SOL-22 | Split across SOL-1 (origin/envelope version semantics — see SOL-1/SOL-2 rows), a NEW `report_assertion_use.created_at` fix (below), and SOL-6 (AOS aliases — see SOL-6 row). | `created_at` joins `report_assertion_use.identity.material_fields`; its semantics are redefined to the DETERMINISTIC verification-pass timestamp (not a per-write wall-clock stamp), preserving replay idempotency while closing the "mutate created_at, hash unchanged" attack. Worked vector: mutating `created_at` alone now changes the fingerprint (`0d238f0b...` vs. the honest `2a071b5b...`); an honest replay (unchanged `created_at`) still reproduces the identical fingerprint. | `schemas/report_assertion_use.schema.yaml` (`identity.material_fields`, `created_at` description); freeze doc §13.1, §13.5, §13.6 (f)/(g) |
| SOL-23 | See SOL-8 above (same finding). | — | §5.1 rule 8 |
| SOL-24 | See SOL-7 above (same finding). | — | §5.1 rule 10 |

**Directive deviations, round 2 (documented per the fix-cycle instructions):**

- **Literal "version field joins material_fields" was applied to `provenance_origin` but NOT
  literally to `research_run_envelope`.** The instruction's exact wording ("origin/envelope records
  are immutable per version... version field joins material_fields") was followed literally for
  `provenance_origin.origin_version`. For `research_run_envelope.envelope_version`, doing the same
  would make `envelope_id` itself change on the ONE legitimate version bump this round introduces
  (`receipt_commitment`'s write-once transition, §5.1b) — breaking the established stable-`{id,
  version}`-pair convention `receipt.envelope_ref` depends on. Instead, `research_run_envelope`
  gains a `version_digest` field (the SAME mechanism this round already applies to
  `canonical_claim`/`inference_record` per SOL-12/18) — achieving the identical goal ("a version
  bump cannot occur without being cryptographically re-provable") without the side effect, and
  unifying the mechanism across every versioned record in this contract. See §5.1b for the full
  rationale.
- **`assertion_lifecycle_event.schema.yaml`'s new `eligible -> *` scoping conditional is a genuine
  narrowing**, not a pure addition — documented explicitly at §2, §16.4a, and the inventory note at
  §20, with the empirical "zero extant instances" check that makes it safe.
- **SOL-15's TOCTOU ask is resolved by HONEST SCOPE NARROWING of the claimed guarantee, not by a new
  mechanism.** The per-run lock genuinely does not serialize lifecycle/config mutators; this round
  states that plainly rather than inventing a broader lock this document has no authority to require
  P4 to build without a concrete, proven need (this task's own "prefer no amendment absent proof"
  instruction, applied to scope-of-claim rather than schema surface).

**Unresolved after round 2:** none of the twenty-four findings (SOL-1 through SOL-24) remain open.
The design notes RPC-1.1.a, RPC-1.1.b (new, §21), RPC-1.2.a, and RPC-1.4.a remain explicitly
non-blocking, single-owner P2/P4/P6 decisions, as before.

## 22b. Fix-cycle changelog (SOL round 3 — FINAL fix round)

Adversarial cross-model review `gpt-5.6-sol` BLOCKED `RPC-1.G` a THIRD time on 2026-07-28,
re-reviewing the round-2 revision: ten of the fifteen original findings were re-marked REOPENED or
PARTIAL (SOL-1, SOL-2, SOL-6/10/11/12/13/14/15/17), the envelope↔receipt pairing design was ruled
**UNSOUND** (the documented honest v2 pair itself failed round 2's own §5.3 check 5), and four NEW
BLOCKER findings landed (SOL-25 through SOL-28)
(`.claude/worknotes/rpc-sol-round3-findings.md`). This round fixes by ROOT CAUSE rather than
finding-by-finding — five root causes (RC-1 through RC-5) — per the dispatching instruction. All
validation below was run with
`/Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python` using
`jsonschema.Draft202012Validator` (`.check_schema()` on all nine touched/existing schemas — zero
errors — plus targeted positive/negative instance validation for every rewritten partition) and a
canonical-JSON SHA-256 script matching `assertion_identity.py`'s exact convention, both as part of
this fix cycle.

| Root cause | Findings closed | Resolution | File(s) / section(s) |
|---|---|---|---|
| **RC-1 — envelope↔receipt pairing redesign** | SOL-2/16/22 (REOPENED as UNSOUND) | Strict ordering, no circularity: envelope v1 is planning-time-only and carries NO receipt-linkage fields at all (`activity_id`/`receipt_commitment` structurally ABSENT, enforced by a NEW `allOf` partition); the receipt's `envelope_ref.envelope_version` is now a fixed LITERAL `1` (`const: 1`), never "whichever version currently exists" — this is what makes the honest v2 pair now pass §5.3 check 5 (the exact UNSOUND regression). Envelope v2 is written exactly once, atomically, carrying `activity_id`+`receipt_commitment` together for the first time; `identity.material_fields` is UNCHANGED (no circular second fingerprint) — `version_digest` (unchanged formula) is "v2's own fingerprint" that covers the commitment. A NEW byte-equality rule (v2's 8 shared fields must byte-equal v1's retained file) closes a SEPARATE tampering vector; the generation-manifest check (RC-2) is what actually closes the receipt-substitution attack. Storage layout named: `<root>/envelopes/<envelope_id>/v1.yaml`/`v2.yaml`. | `schemas/research_run_envelope.schema.yaml`, `schemas/search_activity_receipt.schema.yaml`; freeze doc §5.1 rules 7/9, §5.1a, §5.1b, §5.3, §17.7a |
| **RC-2 — manifest-rooted tamper evidence** | SOL-25, SOL-26 (NEW BLOCKERs); residuals of SOL-12/18/22 | The `.claim_ledger_generations` machinery (§17.7) is formalized as the tamper-evidence ROOT with an explicit `{record_kind, record_id, version, version_digest, fingerprint}` manifest-entry shape, generalized to `research_run_envelope` v1→v2 promotion too (a new, analogous manifest at the envelope's own storage root). Reader rule: a record reachable from a generation manifest MUST match its manifest entry (recomputed from CURRENT content, never the record's own stored field alone); a record not in any manifest is legacy-read-only and mints no authority. Combined with RC-2's widened digest formulas (below), this closes both the digest-omission concern (SOL-25) and the version-mutation concern (SOL-26). | freeze doc §17.7a (NEW) |
| **RC-2 (continued) — widened version_digest formulas** | SOL-26 | `inference_record.version_digest` formula widened to `{conclusion, source_assertion_refs, reasoning, status, inference_version}` (adds the version integer); `canonical_claim.version_digest` formula widened to `{statement, source_assertion_refs, inference_refs, state, canonical_claim_version, replaces, replacement_claims, reversal}` (adds the version integer plus the three reversal/replacement fields). Both schemas' `version_digest` FIELD shape (type/pattern) is UNCHANGED — only the doc-level formula widened, so additive-only compliance against baseline `e76784b` is unaffected (`check_schema` re-verified, zero errors). Re-run: bumping `inference_version`/`canonical_claim_version` alone (`1 -> 999`), holding all other fields constant, now recomputes a DIFFERENT digest (`8e1292fe...` -> `befb39ce...`; `86d6007b...` -> `6096c027...`) — CONFIRMED REJECTED. Vectors recomputed for §18.1's fixtures and §17.8's commit-proof preimage (round 2's `eb94ff60...`/`7cceafab...` values are SUPERSEDED). | `schemas/inference_record.schema.yaml`, `schemas/canonical_claim.schema.yaml`; freeze doc §15.2 items 3–4, §18.1 |
| **RC-3 — P7 task-ID collisions + unnamed enforcing services** | SOL-27 (NEW BLOCKER); residuals of SOL-1/11/17 (PARTIAL) | Every freeze-doc-invented P7 task renumbered from the colliding `RPC-7.1`–`RPC-7.8` range to a disjoint `RPC-7.12`–`RPC-7.19` range (the governing plan's REAL P7 table already owns `RPC-7.2`–`RPC-7.11` + `RPC-7.G` for different gates). Four design notes (N1–N4) name the EXACT enforcing service for every writer-level closure: N1 `services/provenance_envelope.py` (origin/envelope/receipt writers, resolves RPC-1.1.a); N2 `services/assertion_report_use.py` (report-use identity/replay, the `cited_ref` atomic pair); N3 `services/assertion_inference.py`/`services/canonical_claim_materialization.py` (record writers) split from `services/assertion_materialization.py` (the claim_ledger `persistent_references` second write path — atomic pair, durable-commit protocol, commit-proof digest); N4 `services/assertion_impact.py` (post-hoc reconciliation). No closure left "undecided." | freeze doc §12 (RPC-1.1.a resolved), §17.9 (renumbered table + N1–N4), §21 |
| **RC-4 — commit-proof preimage completeness** | SOL-28 (NEW BLOCKER); residual of SOL-14/20 | Published the COMPLETE canonical preimage for the commit-proof vector: the exact `claim_ledger` row shape for `clm_007` (`claims[].sources`/`claims[].text` — a DIFFERENT shape from the target's own `source_assertion_refs`, named explicitly to prevent the round-3 confusion), the full seven-field assembly as literal JSON, and the resulting digest, recomputed against the ROUND-3-WIDENED `target_version_digest` input (round 2's incomplete vector, `e42fa121...fea1`, is superseded — both because it lacked a complete preimage AND because the target's own digest changed under RC-2's widened formula). New value: `85a3e675...6393d`. Substituted-target re-run confirmed a different digest (round-3 value `a689a798...7321b` was miscomputed; corrected in round 4 / SOL-29 to `8466e738...f99df`, live value in §17.8). An independent implementer can now recompute byte-for-byte. | freeze doc §17.8 item 2 |
| **RC-5 — rights snapshot domain match** | SOL-10/21 (REOPENED residual, the `rights_triage_failure.detail` counterexample) | `rights_snapshot.rights_triage_failure.detail` no longer carries `minLength: 1` — round 2's blank-string audit over-applied hardening to a MIRRORED field; the source subschema (`source_assertion.rights_summary.rights_triage_failure.detail`) has never constrained this field's length. Blank-string hardening now applies to RPC-MINTED (non-mirrored) fields only. Re-verified: the round-3 counterexample (`detail: ""`) now validates; the `{}` case and the normalize-hash equality (SOL-10/21's round-2 fix) are unaffected and re-confirmed. | `schemas/report_assertion_use.schema.yaml` (`rights_snapshot.rights_triage_failure.detail`); freeze doc §13.4 |
| SOL-1/11/17 (PARTIAL residuals) | Folded into RC-3 | Covered entirely by RC-3's named-service requirement — see the row above. | §17.9 N1–N4 |

**Directive deviations, round 3 (documented per the fix-cycle instructions):** none. Every named
root cause was closed at the schema/doc layer this round; no deviation was necessary (contrast round
1's SOL-6/12 deviations and round 2's `eligible -> *` scoping narrowing, both still in force,
unchanged by this round).

**Attack re-run summary (this fix cycle, exhaustive over every round-3 REOPENED/PARTIAL finding plus
both new-finding attacks named in the dispatching instruction):**

| Attack | Result |
|---|---|
| Honest v2 envelope/receipt pair against the FIXED §5.3 (all six checks) | **PASSES** (the exact UNSOUND-ruling regression, now fixed) |
| Substituted receipt + recomputed v2 (the round-3 accepted attack) | **REJECTED** — via the generation-manifest mismatch (§17.7a); the byte-equality check does NOT independently fire on this specific attack (stated honestly, §5.1b) |
| Envelope v1 with `activity_id` present | **REJECTED** (schema) |
| Envelope v1 with `receipt_commitment: null` present | **REJECTED** (schema) |
| Envelope v2 missing `activity_id` or with `receipt_commitment: null` | **REJECTED** (schema) |
| Receipt `envelope_ref.envelope_version: 2` | **REJECTED** (schema, `const: 1`) |
| Digest downgrade (`version_digest` omitted/null on inference/canonical/envelope) | **REJECTED on read** — the manifest, not the record's own field, is authoritative (§17.7a) |
| Version-integer mutation (`inference_version`/`canonical_claim_version` `1 -> 999`, all else held constant) | **REJECTED** — digest changes under the widened formula (§15.2), confirmed by direct recomputation |
| `rights_triage_failure.detail: ""` (round-3 counterexample) | **NOW VALIDATES** (RC-5 fix; this was the fix target, not an attack to reject) |
| `rights_snapshot: {}` / normalize-hash equality (round-2 fixes) | **Unaffected, re-confirmed** |
| Honest documented commit-proof vector, full preimage | **Recomputes to the published `85a3e675...6393d`** |
| Substituted-target commit-proof variant | **REJECTED** — different digest confirmed |

**Accepted bounded limitations (for the human gate to ratify — none of these are open findings; all
are honestly-scoped design boundaries, consistent with rounds 1–2's own precedent of stating scope
honestly rather than overclaiming):**

1. **Byte-equality (§5.1b point 6) and the generation-manifest check (§17.7a) close DIFFERENT
   attacks, not the same one twice.** The byte-equality rule does not, by itself, reject a pure
   receipt-commitment/`activity_id` substitution that leaves v1's 8 shared fields untouched — the
   manifest check is what closes THAT attack. This is stated explicitly rather than implied, per
   this round's own instruction to "state anything unresolved" — it is not a gap, but a precise,
   two-mechanism division of labor that a less careful reading could conflate into a single
   (falsely) doubly-redundant check.
2. **The generation-manifest's security property depends on the manifest store itself being
   append-only and not independently forgeable by the same actor who can write record files.** This
   document freezes the manifest ENTRY SHAPE and the reader rule; it does not authorize or specify
   filesystem permissions/write-access separation for the manifest store itself (an operational
   concern, out of scope for a Mode-B schema/contract freeze, consistent with DI-1 remaining
   BLOCKED and this document minting no deployment authority).
3. **TOCTOU bounded-concurrency scope (round 2, SOL-15, unaffected by round 3).** The per-run lock
   still serializes ledger-and-record writers only, not every lifecycle/config mutator — carried
   forward unchanged from round 2's honest-scope-narrowing fix.
4. **P2/P6 read-path function names remain unnamed (RPC-1.1.b, RPC-1.2.a, RPC-1.4.a) — unchanged,
   non-blocking design notes**, same status as prior rounds; not newly introduced by round 3.
5. **(Closure-round addendum, post round 3 — SOL-35 REOPENED closure, then K-FINAL-1 empirical
   closure, both `services/assertion_report_use.py`.) `attest_verification_pass` is the SOLE public
   attestation entry point; the private writer chain is not part of the public API.**
   `attest_verification_pass` re-reads its `report_path` argument and refuses to mint an attestation
   unless the recomputed digest of those CURRENT bytes matches the caller-supplied
   `report_content_digest` — this is what makes it impossible for an in-process caller to self-issue an
   attestation for report content it has never actually read. The SOL-35 round closed the module-level
   `record_verification_pass` function this way but left the durable writer itself,
   `ReportAssertionUseService.resolve_verification_pass_created_at`, as a plain PUBLIC method with no
   leading underscore — reachable by any caller holding a `ReportAssertionUseService` instance,
   entirely bypassing `attest_verification_pass`'s digest-possession check. K-FINAL-1 (an empirical
   two-call attack script: construct the service, call the public method with a forged digest bound to
   no report body, then call `publish_report_assertion_uses_for_report`) confirmed this residual path
   minted a real, durably published `report_assertion_use` record with zero report bytes ever read.
   The fix renames the method to `_resolve_verification_pass_created_at` (module/class-private),
   closing it to the one production call chain (`attest_verification_pass` ->
   `_record_verification_pass` -> `ReportAssertionUseService._resolve_verification_pass_created_at`).
   This private writer chain — including `_record_verification_pass`'s
   `_VerificationAttestation` capability-token gate — is an implementation detail, not the public API;
   `attest_verification_pass` remains the only supported way to mint a durable attestation. This guard
   does NOT, and cannot, prevent an in-process caller that already holds filesystem write access to
   this workspace's storage root from writing an anchor file directly (bypassing the module's public
   API and the private method both), or from placing a forged report body at some path before calling
   `attest_verification_pass` so its digest matches on purpose. The trust boundary this guard enforces
   is the process/module API, not the filesystem itself — the SAME boundary limitation item 2 above
   already accepts for the generation-manifest's append-only property. This is an honest, bounded
   guarantee (no caller reachable through the public API — as opposed to a private/internal method
   accessed by working around Python's naming convention — can mint an attestation for bytes it has
   not read), not a claim of protection against a co-resident actor with independent filesystem write
   access, nor against a caller willing to reach into module-private internals.

**Unresolved after round 3:** none of the twenty-eight findings (SOL-1 through SOL-28) remain open.
This is the FINAL fix round for this contract per the dispatching instruction; the four accepted
bounded limitations above are offered to the human gate for ratification, not as outstanding defects.
Item 5 above is a later addendum (closure round, post round 3) documenting SOL-35's REOPENED-and-
re-closed guarantee in the same honest terms; see §22c for the closure round's full findings list.

## 22c. Fix-cycle changelog (SOL FINAL fix round — refreeze, not a code change)

Adversarial cross-model review (`gpt-5.6-sol`, findings `SOL-31` through `SOL-39`,
`.claude/worknotes/rpc-sol-final-findings.md`) found nine new issues against the shipped P4–P7
implementation. Eight (`SOL-31`, `SOL-32`, `SOL-33`, `SOL-35`, `SOL-36`, `SOL-37`, `SOL-38`,
`SOL-39`) were genuine implementation gaps, fixed in code this round (`services/provenance_envelope.py`,
`services/assertion_materialization.py`, `services/assertion_report_use.py`,
`services/assertion_impact.py`, `services/assertion_catalog.py`,
`services/canonical_claim_materialization.py`, `services/verification.py`) — this document is
unchanged by those eight; see the relevant test files for regression coverage. `SOL-34` is different:
it is a genuine CONTRACT/CODE MISMATCH, not a code defect — resolved here by **refreezing the
contract to match the shipped, stronger implementation**, per this fix cycle's explicit dispatching
instruction ("implement the frozen formula or explicitly refreeze the contract and vectors before
closure").

**SOL-34 — canonical-claim targets use a SEPARATE, stronger `support_refs_digest` formula than
`inference_record` targets; this was undocumented.** §17.8 item 2's worked vector freezes ONE
formula — `sha256-canonical-json-v1(<the target's own bare source_assertion_refs list>)` — and
states it applies to "the target's own source_assertion_refs at the SAME commit-time recheck
instant." That wording is correct AND COMPLETE for an `inference_record` target (which has no
`inference_refs` field at all — `assertion_inference.py`'s own
`support_refs_digest_of=lambda rec: _canonical_digest(rec.get("source_assertion_refs") or [])`
matches it exactly, byte-for-byte). It is INCOMPLETE for a `canonical_claim` target, which can
legitimately carry BOTH `source_assertion_refs` AND `inference_refs`
(`canonical_claim.schema.yaml`) — `canonical_claim_materialization.py` has, since RPC-4.3 shipped,
computed the seventh field over BOTH ref kinds together (`publish_canonical_claim`'s own
`support_refs_digest` local, and `_TargetKindSpec.support_refs_digest_of` for the commit-time
recheck), a documented design decision already called out in that module's own docstring at the
call site: "bind the commit proof to BOTH support kinds together, since a canonical claim's full
support is the combination of its `source_assertion_refs` AND `inference_refs`, not either alone."
This is objectively STRONGER (it binds commit-proof integrity to strictly more of the target's real
support state — an inference-ref substitution attack that left `source_assertion_refs` untouched
would escape the bare-list formula but is caught by the two-key formula) but it is NOT the literal
formula §17.8 freezes, and — per SOL-34's finding — was never independently documented as its own
normative, byte-recomputable vector. That gap is closed here, not by weakening the code to match
the narrower inference-only formula (which would silently drop real coverage a canonical claim's
`inference_refs` currently gets), but by freezing the STRONGER formula the code already ships as
the canonical-claim-target-specific normative text.

**Normative rule (canonical-claim targets only; supersedes §17.8's inference-only wording for this
target kind — §17.8 item 2's formula remains exactly as frozen for `inference_record` targets,
unchanged):**

```
support_refs_digest (target_kind: canonical_claim) = sha256-canonical-json-v1({
  "source_assertion_refs": <the target's own source_assertion_refs at the SAME commit-time
                             recheck instant, §17.1 item 6 -- each element the canonical_claim's
                             own {assertion_id, assertion_version, relation} shape>,
  "inference_refs": <the target's own inference_refs at the SAME instant, or the empty list []
                      when the target carries none -- NEVER omitted from the object, NEVER null;
                      canonical_claim_materialization.py's own
                      `inference_refs_of=lambda rec: rec.get("inference_refs") or []` and
                      `support_refs_digest_of`'s `list(rec.get("inference_refs") or [])` both
                      normalize an absent/null field to `[]` before hashing>
})
```

This is everything §17.8's seven-field `commit_proof_digest` assembly needs for a `canonical_claim`
target — the six other fields (`claim_id`, `row_material`, `target_kind`, `target_id`,
`target_version`, `target_version_digest`) are computed identically to §17.8's own worked example,
unchanged.

**Worked test vector — COMPLETE canonical preimage, independently recomputed against the LIVE
shipped code (`compute_canonical_claim_id`, `compute_canonical_claim_version_digest`,
`compute_commit_proof_digest`) this fix cycle, not hand-derived.** One source-assertion ref plus one
inference ref, both `relation: supports`:

```json
{
  "source_assertion_refs": [
    {"assertion_id": "ast_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "assertion_version": 1, "relation": "supports"}
  ],
  "inference_refs": [
    {"inference_id": "inf_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", "inference_version": 1, "relation": "supports"}
  ]
}
```

`support_refs_digest = sha256-canonical-json-v1(<the object above>)
= 325328d5b9457f32702c631b66d246ea4fd8c83f38cfd68e2344f79a20952c08`.

Applying §17.8's now-superseded-for-this-target-kind inference-only formula (hashing the bare
`source_assertion_refs` list alone, no `inference_refs`, no wrapping object) to the SAME
`source_assertion_refs` value produces a DIFFERENT digest —
`766f6eec9aae18f1f28cf779e717e69598074155855473d21fffe7b4a5b1f0d1` — confirming the two formulas
are genuinely distinct and non-interchangeable; an implementation applying the wrong one to a
`canonical_claim` target would silently diverge from every value this vector, and the shipped code,
produce.

Full canonical-claim target, minted via the SAME `statement`/`source_assertion_refs` shown above,
`state: active`, `canonical_claim_version: 1`, no `replaces`/`replacement_claims`/`reversal`:

- `statement = "Pediatric reference intervals for CBC differ materially from adult intervals across all measured analytes."`
- `canonical_claim_id` (§15.2 item 3, material fields `{statement, source_assertion_refs}` only —
  `inference_refs` excluded from the ENTITY id, unchanged by this amendment)
  `= ccl_6acd86ec956ac79e2484282b5a55fdb2adf56c189cf1e6504bb7f0f032d0e1c2`
- `target_version_digest` (§15.2 item 4 round-3-widened eight-field `version_digest` formula,
  unchanged by this amendment — `inference_refs` IS one of the eight fields already)
  `= 06730e9bdb09c417b5cd05ac43a300844d31addccb30ce2ea9d936228e3c8de7`

`claim_ledger` row (the CLAIM ROW's own shape, distinct from the target's fields, mirroring §17.8's
own `clm_007` convention):

```json
{
  "claim_id": "clm_c34",
  "text": "Pediatric reference intervals for CBC differ materially from adult intervals across all measured analytes.",
  "sources": [
    {"source_card_id": "src_101", "evidence_id": "ev_101", "relation": "supports", "locator": "sec:4.1"}
  ]
}
```

The SEVEN-FIELD assembly, exact JSON:

```json
{
  "claim_id": "clm_c34",
  "row_material": {
    "sources": [
      {"source_card_id": "src_101", "evidence_id": "ev_101", "relation": "supports", "locator": "sec:4.1"}
    ],
    "conclusion_text": "Pediatric reference intervals for CBC differ materially from adult intervals across all measured analytes."
  },
  "target_kind": "canonical_claim",
  "target_id": "ccl_6acd86ec956ac79e2484282b5a55fdb2adf56c189cf1e6504bb7f0f032d0e1c2",
  "target_version": 1,
  "target_version_digest": "06730e9bdb09c417b5cd05ac43a300844d31addccb30ce2ea9d936228e3c8de7",
  "support_refs_digest": "325328d5b9457f32702c631b66d246ea4fd8c83f38cfd68e2344f79a20952c08"
}
```

`commit_proof_digest = c5ef6f361189aaf3314eaf82f504a7b697df221fe85c05622e94cee1f5aa4497` — recomputed
byte-for-byte from the published preimage above via the LIVE `compute_commit_proof_digest` (this is
the SAME function `inference_record` targets use — §17.8's seven-field assembly logic itself is
NOT amended, only the `support_refs_digest` INPUT computation for canonical-claim targets). Every
value in this vector (`canonical_claim_id`, `target_version_digest`, `support_refs_digest`,
`commit_proof_digest`) was produced by calling the shipped
`research_foundry.services.canonical_claim_materialization.compute_canonical_claim_id`/
`compute_canonical_claim_version_digest` and
`research_foundry.services.assertion_materialization.compute_commit_proof_digest` directly against
this exact preimage, not hand-derived — an independent implementer recomputing from the JSON above
through the same canonical-JSON-then-sha256 algorithm (§4.1's `sha256-canonical-json-v1`) reproduces
every digest exactly.

**Directive deviation, this round (documented per the fix-cycle instructions):** the code for SOL-34
is NOT changed — `canonical_claim_materialization.py`'s `support_refs_digest_of`/
`publish_canonical_claim`'s local `support_refs_digest` computation are left exactly as shipped
(hashing BOTH ref kinds). Per the dispatching instruction's own stated resolution path for this
finding, the CONTRACT is amended to document and freeze the stronger, already-shipped formula as
normative for canonical-claim targets, rather than weakening the implementation to match the
narrower inference-only wording. This is a NEW deviation type not previously used in rounds 1–3
(those rounds always changed code/schema to match a frozen contract) — recorded honestly here for
the human gate, consistent with this document's own precedent of never silently reconciling a
contract/code mismatch in either direction.

**Scope note:** this section is a contract-only refreeze. It authorizes no production-code change,
mints no new schema field, and does not reopen or amend §17.8's `inference_record`-target wording,
§18.1's fixtures, or §20's file inventory (`inference_record.schema.yaml`/`canonical_claim.schema.yaml`
remain byte-identical field shapes; only this document's own text changed). `SOL-31`, `SOL-32`,
`SOL-33`, `SOL-35`, `SOL-36`, `SOL-37`, `SOL-38`, `SOL-39` are code-layer fixes with no normative
contract-text change and are not further elaborated in this section — see the fix-cycle's commit and
the corresponding test files for their coverage, EXCEPT for the three findings the follow-up closure
round below reopened or left partial.

### Closure round — SOL-35 REOPENED, SOL-37 PARTIAL, SOL-40 (code hardening, not a contract change)

A subsequent adversarial pass over this same shipped fix cycle re-marked `SOL-35` REOPENED (BLOCKER)
and `SOL-37` PARTIAL, and raised one new finding, `SOL-40` (HIGH, gate-blocking) — all three closed
here in code, with no schema or normative-contract-text change (this remains a contract-only
document; the fixes themselves live in the named service files and their test suites):

- **SOL-35 REOPENED — self-attestation via the directly-callable `record_verification_pass()`.** The
  prior round's fix made `record_verification_pass` the sole writer of a verification-pass
  attestation, gated only by a docstring convention ("reachable EXCLUSIVELY from `verification.py`'s
  own call site") — nothing in the type system or a runtime check actually enforced that. Because the
  function was a plain public function accepting a caller-supplied `report_content_digest`, ANY
  in-process caller could mint a durable "verification passed" anchor for an arbitrary digest bound to
  no real report content at all — and this module's own test suite exercised exactly that call
  pattern. Closed by renaming the writer to module-private `_record_verification_pass`, gating it
  behind a module-private `_VerificationAttestation` frozen-dataclass token constructible only inside
  a new public `attest_verification_pass`, which re-reads `report_path` and refuses on any digest
  mismatch — see the accepted bounded limitation recorded as §22b item 5 above. `services/verification.py`'s
  call site now calls `attest_verification_pass(..., report_path=rpath, ...)` instead.
- **SOL-37 PARTIAL — `_valid_active_policy`'s incomplete shape check.** The active-branch policy
  validator in `services/assertion_impact.py` checked `type`/`assertion_id`/`invalidation_state`/
  `lifecycle_state`/`invalidation_event_id` but never `schema_version` or `assertion_version`, even
  though the writer (`AssertionImpactReconciler._load_policy`'s no-path-exists branch) always emits
  both. A policy tampered to a different `schema_version`, or to a missing/malformed/non-positive
  `assertion_version`, still validated as a legitimate active (unblocked) snapshot. Closed by adding
  both fields to `_valid_active_policy`'s required shape (`schema_version == "1.0"`; `assertion_version`
  a positive, non-bool int) — regression coverage in `tests/unit/test_assertion_impact.py`.
- **SOL-40 — a failed catalog-projection purge was permanently skipped after the FIRST attempt.**
  `AssertionImpactReconciler.reconcile()` persisted the blocked lifecycle policy to disk BEFORE
  attempting the SOL-38 derived-cache purge, and only attempted that purge on the ONE call where the
  freshly-computed policy differed from the on-disk value. A purge failure (e.g. a transient `OSError`
  unlinking the projection file) left the assertion durably blocked while the stale catalog projection
  was never invalidated — and a RETRY's freshly-reloaded policy already equalled the blocked value, so
  the retry's `policy != blocked` gate skipped the purge attempt entirely, this time forever. Closed by
  attempting the purge on EVERY `reconcile()` call while the effective policy is blocked (idempotent:
  `purge_lifecycle_derived_file` is already a no-op once the projection file is gone) and failing the
  call closed with a new, typed blocked-receipt reason code, `derived_cache_purge_failed` (added to
  `_BLOCKED_RECEIPT_REASON_CODES`), on any purge `OSError` — only a successful purge lets
  reconciliation proceed to receipt derivation, and the retry path naturally re-attempts the purge
  because it reaches the same unconditional call again. Regression coverage (injected one-time
  `OSError`, then a clean retry) in `tests/unit/test_assertion_impact.py`.
