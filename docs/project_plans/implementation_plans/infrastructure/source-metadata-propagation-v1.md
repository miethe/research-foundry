---
it_schema: 1
feature_slug: source-metadata-propagation
title: "Source Metadata Capture & Provenance-Preserving Propagation — implementation plan"
doc_type: implementation_plan
status: completed
planning_maturity: shipped
merge_commit: 794824d0737fda33fe0dfb671c951c8a4fafc132   # squash of M1-M4 + gate remediation into main
merge_branch: main
commit_refs:
  - 794824d0737fda33fe0dfb671c951c8a4fafc132   # only main-reachable sha; the 5 worktree commits went orphan on squash
tier: 3
priority: P2
points: 48
risk_level: high
context_class: C3            # dominant = M4 (catalog_service.py 2242 lines + 7-bundle fan-out); M1-M3 are C2
created: 2026-08-02
updated: 2026-08-02
changelog_required: true
prd_ref: docs/project_plans/PRDs/infrastructure/source-metadata-propagation-v1.md
spike_ref: docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-charter.md
intenttree_workspace: agentic-os
intenttree_tree: tree_01KVTH95G09FX26HCRPBV77DAE   # aos-research-foundry (NOT aos-intenttree)
intenttree_parent_node: node_01KY5SGQKGHCPRE0GVA6BB1C6W   # Research Interchange, Provenance & Access Initiative (Epic)
itt_node_id: node_01KZ1T5MC56SE65071SC6FJ2W4
itt_milestone_nodes:
  M1: node_01KZ1T65K7N20EJQJVBF6Q26SJ
  M2: node_01KZ1T6BJE87ZCGX8GWPZP9P3W
  M3: node_01KZ1T6JH4T4602MC06696C8KX
  M4: node_01KZ1T6QW2K44W9WZ2976454NN
deferred_items_spec_refs: []
findings_doc_ref: null
related_documents:
  - docs/project_plans/PRDs/infrastructure/source-metadata-propagation-v1.md
  - docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-feasibility-brief.md
  - docs/project_plans/exploration/source-metadata-propagation/source-metadata-propagation-proposed-adr.md
  - docs/dev/architecture/adr-rights-entity-model.md
  - docs/dev/architecture/rf-run-export-schema.json
  - docs/project_plans/human-briefs/source-metadata-propagation.md
acceptance_criteria:
  # MET WITH A NAMED LIMIT: the capture path, ingest-boundary bounds, and deterministic
  # trust.source_rank are real and live. DOI now flows from a real producer
  # (external_research_resolution.default_promote, wired post-gate). authors/publisher/version have
  # NO live producer — no registered search-router provider emits them (OQ-1) and live third-party
  # ingestion is deferred Phase C (PRD DEF-1..DEF-6). Shipped as capability + one real DOI path,
  # not as "all four fields now populate in production".
  - "A newly ingested source card carries real authors/DOI/publisher/version instead of hardcoded-empty."
  - "Source attributes reach claims at export time, recomputed from files on every run, with no read-path model call, network call, or clock read."
  - "A third_party_* attribution value cannot exist without retrieval evidence — enforced by schema shape, not a field-name list."
  - "All 7 committed pediatric_cds bundles still verify after the schema change, proven by a live 7-of-7 counted sweep."
  - "The first query surface reports tri-state coverage (N of M sources assessed) — absent is distinguishable from not-yet-assessed."
  - "Every change to the exported payload shape lands a versioned rf-run-export-schema.json plus a legacy fixture that still validates."
open_questions:   # all RESOLVED at their milestone's entry; resolutions + evidence in the execution ledger
  - "RESOLVED (M1 entry) OQ-1: none of the six registered search-router providers returns DOI / citation counts / structured authors — none is a bibliographic API, and SearchHit/ExtractedDoc carry no such fields. CAVEAT found later by the feature gate: this enumerated PROVIDERS, not ingest CALL SITES, and missed that external_research_resolution.default_promote already held a real external DOI and dropped it. Now wired."
  - "RESOLVED (M4 entry) OQ-2: rebuild-only — no ALTER TABLE, no Alembic chain. A SCHEMA_VERSION int drives drop-and-recreate via _ensure_schema(), which does NOT repopulate. Safe because the catalog is a derived index, but `rf catalog rebuild` is a MANDATORY post-deploy step or the catalog silently reports zeroed counts."
  - "RESOLVED (M1 entry) OQ-4: deterministic from source_type alone; no capture-time model call needed. rights_summary.access_basis is always 'unknown' at real capture time, so folding it in would have been dead code."
  - "RESOLVED (at plan time, per the accepted decision) OQ-3: attribution_summary carries attribution_ids, counts and monotone rollups only — never a raw third-party value."
decisions:
  - decision: "Owning entity is a NEW top-level source_attribution entity, not an extension of source_assertion.schema.yaml."
    rationale: "The Ledger has no asserted-by field, mandates a passage anchor a citation count cannot satisfy, and write-caps attestation at `candidate` forever. Shaped on the landed rights_record.schema.yaml. Prior-art leg's dissent (sibling third_party_assertions[]) is preserved in the PRD, not erased."
    status: accepted
  - decision: "Propagation happens at export time in _resolve_source(), not at claim-map write time."
    rationale: "_term_index indexes immutable claim text; an attribution observes a mutable external world. Freezing a citation count into claim_ledger.md would make the canonical ledger stale without the claim changing."
    status: accepted
  - decision: "No backfill; tri-state coverage ships WITH the first query surface."
    rationale: "Hard precondition of the go verdict — otherwise a `citations >= 10` filter silently excludes 100% of the historical corpus, reading as 'verified zero' rather than 'never assessed'."
    status: accepted
  - decision: "Rollups are monotone only (best/weakest_source_rank); numeric averaging across assertion_kinds is refused. Set-union values are canonically sorted before serialization."
    rationale: "Averaging third-party bibliometrics would be RF minting its own judgment. Cross-source values propagate as set-union keyed by (asserter_id, assertion_kind); json.dump preserves insertion order but does not impose it, so an explicit sort is required for the recomputability AC to be meaningful."
    status: accepted
  - decision: "RESOLVES OQ-3 — attribution_summary carries attribution_ids, counts, and the monotone rollups ONLY. It never carries a raw third-party value, and it is recompute-only from authoritative records."
    rationale: "Deferring this to M2 entry left an interface fork that also changes M4's query contract, so it is settled at plan time. Making the mirror value-free is what structurally closes the sibling-field bypass below: there is no value-bearing property on the card to write into. Cost, accepted: reading an actual citation number goes through the authoritative record."
    status: accepted
  - decision: "Provenance is required STRUCTURALLY, not by a second field-name allowlist."
    rationale: "A second name list reproduces _RIGHTS_GOVERNED_FIELDS' blindness one level up — an agent writes trust.third_party_citation_rank instead of the guarded name. Primary control is schema shape: authoritative record is additionalProperties:false with `if asserter_type startsWith third_party_ then retrieval_evidence_ref required`, and the value-free recompute-only mirror leaves no sibling to bypass into. The name rule stays only as defence-in-depth."
    status: accepted
routing_constraints:
  - "Export-time propagation determinism (M1) MUST stay claude-primary — it carries the deal-killer refutation (no read-path model/network/clock)."
  - "The authoritative-record schema shape and the value-free mirror contract (M2) MUST stay claude-primary — they ARE the governance control, not a data model."
  - "The structural provenance guard and its negative tests (M3) MUST stay claude-primary — authorization boundary, Mode-D-adjacent."
  - "Catalog column plumbing, sqlite row builders, and regression-fixture scaffolding (M4) are offload-eligible."
  - "Capability bar: M1-M3 need a model that holds multi-file schema invariants in one pass; M4 plumbing may drop to economy class."
wave_plan:
  waves: [["M1"], ["M2"], ["M3"], ["M4"]]
  phases:
    - id: M1
      title: "First-party source metadata is real, contract-versioned, and reaches the bundle"
      depends_on: []
      files_affected:
        - src/research_foundry/services/source_cards.py
        - src/research_foundry/services/export_service.py
        - schemas/source_card.schema.yaml
        - docs/dev/architecture/rf-run-export-schema.json
        - tests/test_schema_validation.py
      exit_criteria:
        - "A card ingested post-change carries populated authors/DOI/publisher; export hydration surfaces them at claim level; the exported contract is versioned with a passing legacy fixture."
      gate_lens: [security, validator]
      gate_lens_reason: untrusted-input
    - id: M2
      title: "The attribution entity exists with a value-free, recompute-only mirror"
      depends_on: ["M1"]
      files_affected:
        - schemas/source_attribution.schema.yaml
        - schemas/source_card.schema.yaml
        - src/research_foundry/services/attribution_triage.py
        - src/research_foundry/services/attribution_validation.py
        - docs/dev/architecture/rf-run-export-schema.json
      exit_criteria:
        - "An attribution record round-trips; a hand-written value in attribution_summary is a validation error; divergence is detectable with an injected as_of."
      gate_lens: [validator]
    - id: M3
      title: "The provenance boundary is structurally closed"
      depends_on: ["M2"]
      files_affected:
        - src/research_foundry/services/governance.py
        - schemas/source_attribution.schema.yaml
        - tests/test_governance_adversarial.py
      exit_criteria:
        - "A third_party_* value without retrieval_evidence_ref is rejected by schema shape; sibling-field bypass attempts are rejected too; removing the control turns the suite RED."
      gate_lens: [security, validator]
      gate_lens_reason: authz-boundary
    - id: M4
      title: "Queryable, tri-state honest, and non-regressive"
      depends_on: ["M3"]
      files_affected:
        - src/research_foundry/services/catalog_service.py
        - src/research_foundry/api/routers/catalog.py
        - tests/test_schema_validation.py
      exit_criteria:
        - "Catalog filters on the new attributes and reports N-of-M coverage; a counted sweep shows 7 of 7 pediatric bundles verifying."
      gate_lens: [security, validator]
      gate_lens_reason: irreversible-outward
      karen: true                # C3 milestone — M1-M3 are C2: final tree pass only
---

# Implementation Plan — Source Metadata Capture & Provenance-Preserving Propagation

RF records source quality signals write-only today: `source_cards.py:322-329` hardcodes `doi`, `authors`,
`publisher`, and `version` empty, `trust.source_rank` is never really derived, and every signal is discarded
at the claim boundary — leaving evidence unfilterable by anything except its own text. When this is done,
sources carry real first-party metadata plus separately-owned third-party assertions *about* them, both
queryable at claim and catalog level, recomputed from files on every export.

## Scope boundary

**In:** first-party metadata capture in `ingest_source()`; deterministic `trust.source_rank`; export-time
propagation, canonically-sorted rollups, and a versioned export contract; a new `source_attribution` entity
with a value-free mirror; divergence checking; structural provenance enforcement; catalog columns and the
tri-state query surface.

**Out (stated, not silently dropped):** **Phase C — third-party live ingestion**
(`services/attribution_fetch/`, `rf attribution` CLI, ~8 pts) is deferred behind the verdict's precondition,
*"per-provider license terms verified for bundle redistribution"*. Scopus/Web of Science are excluded absent
a procured license. Semantic Scholar/PubMed ingestion waits on the mechanism this plan builds. Full deferral
register with handles: PRD §Out-of-Scope (DEF-1..DEF-6).

## Rubric — what "good" looks like

The read path stays dumb: every derived value must be reconstructible by re-running `export_run()` over
unchanged files — no persisted derived state, no cached judgment, no wall-clock read, and any set carries an
explicit canonical sort. RF never launders a third-party number into an RF-authored fact, and the mechanism
for that is **shape, not vocabulary**: if a control can be defeated by choosing a different field name, it is
the wrong control. Additive means *additive* — new keys only where `additionalProperties: true` already
holds; `pediatric_cds` is untouched. **Any change to the exported payload shape versions
`rf-run-export-schema.json` and ships a legacy fixture that still validates** — the current resolved-source
schema permits arbitrary properties, so undocumented output can otherwise ship silently. Between two
technically-passing designs, pick the one that keeps the canonical ledger stable and the mirror disposable.

## Named risks

- **A name-based guard is defeated by a sibling field.** `governance.py:35-40` is a 4-entry *name* tuple, so
  every new attribution field is unguarded by construction — and a second entry would still miss
  `trust.third_party_citation_rank`. M3's control must be structural or it is theatre.
- **`rf verify` does not exercise the export path.** `verification.py` imports only helpers from
  `export_service` and never calls `export_run()`. Any AC that "proves" hydration by running `rf verify` is
  vacuous. Worse, each `rf verify` appends a timestamped event to `telemetry/run_trace.jsonl`, which
  `_timeline()` (`export_service.py:1162`) folds into the export — so naive byte-comparison can never pass.
- **A `for` loop over `grep` output exits 0 on zero matches.** The 7-bundle sweep must assert a *count*, not
  a status. Missing test files `pytest` as ERROR (exit 4), not as an honest failure.
- **No-backfill result-set bias (certain by construction).** Pre-existing cards read "no data"
  indistinguishably from "verified zero". Tri-state coverage is an M4 gate, not a nice-to-have.
- **Staleness reads as currency.** Refresh must create a new record; in-place overwrite is forbidden — so a
  bad value is superseded, never corrected. This needs a test, not just a convention.
- **`pediatric_cds` contamination.** Both `oneOf` branches are `additionalProperties: false`
  (`pediatric_cds.schema.json:18-24`) — a stray key is a hard `ExitCode.SCHEMA(2)`.
- **`catalog_service.py` is 2242 lines (H7).** M4 already carries the 2× multiplier; do not re-plan it small.

## References

- `src/research_foundry/services/source_cards.py:178-192,308-363` · `export_service.py:580-661,1162,1333` ·
  `catalog_service.py:557-572,850-889,1341-1349` · `governance.py:35-40,500-520`
- `schemas/source_card.schema.yaml:59,78,104,118,138,411` (the `additionalProperties: true` seams)
- Exported public contract: `docs/dev/architecture/rf-run-export-schema.json` + strict regression in
  `tests/test_schema_validation.py`
- Wall-clock idiom to avoid in validators: `now_iso()` (`ids.py:41`), not just `datetime.now`
- Patterns to copy, not reinvent: `rights_triage.py:90-113` · `rights_validation.py:128` (injected `as_of`)
- Anchor feature: `docs/dev/architecture/adr-rights-entity-model.md` (merged `17a2cb0`)
- Related tracked work (tree `aos-research-foundry`): parent epic
  `node_01KY5SGQKGHCPRE0GVA6BB1C6W` (Research Interchange, Provenance & Access) ·
  `node_01KXRSF4PKH089M62F10MCZ43C` (Assertion-Ledger followups — why we do *not* extend the Ledger) ·
  `node_01KYVBG7K191K4BKAZPEP5CRDF` (the rg-AC path-existence rule this plan's matrix must satisfy) ·
  `node_01KXRSK5S1XPVTS7GB6QG42CWE` (adjacent charter: Claim Segmentation & Source Alignment)

## Milestones

### M1 — First-party source metadata is real, contract-versioned, and reaches the bundle

`ingest_source()` threads structured provider metadata onto the card, `trust.source_rank` is genuinely
derived, and `_resolve_source()` hydration widens so those values appear at claim level in an exported
bundle. Because provider strings are externally controlled, they are length-bounded and type-checked at the
ingest boundary before they reach a card. The exported payload shape changes here, so
`rf-run-export-schema.json` is versioned in this milestone with a legacy fixture proving old exports still
validate. Resolve OQ-1 and OQ-4 at entry; if `source_rank` cannot be derived deterministically it stays
`unknown`, set only by an explicit write recorded with provenance — never silently inferred.

### M2 — The attribution entity exists with a value-free, recompute-only mirror

`schemas/source_attribution.schema.yaml` lands as the authoritative record (`additionalProperties: false`),
carrying `{source, value, observed_at, license_basis}` at minimum. The card's `attribution_summary` mirror
carries `attribution_ids`, counts, and the monotone rollups only — never a raw third-party value — and is
recomputed from authoritative records at export, so a hand-written value there is a validation error.
`attribution_triage.py` and `check_attribution_divergence(as_of=…)` follow the rights-entity patterns.

### M3 — The provenance boundary is structurally closed

The authoritative record schema enforces `if asserter_type startsWith third_party_ then
retrieval_evidence_ref required`. `no_agent_authored_attribution_value` and the
`_RIGHTS_GOVERNED_FIELDS` extension remain as defence-in-depth, explicitly *not* the primary control.
**Mode-D:** this milestone changes an authorization boundary — halt for explicit human approval before
landing.

### M4 — Queryable, tri-state honest, and non-regressive

Catalog columns and sqlite rows carry the new attributes; the query surface reports coverage as
`present` / `absent` / `not-yet-assessed` and states "N of M sources assessed". A counted sweep proves 7 of 7
pediatric bundles verify. Resolve OQ-2 at entry. **Mode-D:** performs a catalog schema migration — halt.

## AC -> command -> evidence

The single home for verification detail. The PRD owns narrative AC; this matrix owns proof. Every row below
must FAIL if the feature is absent — a row that passes on an unimplemented feature is a defect in this table.

| AC | Command | Evidence of pass |
|---|---|---|
| M1 metadata populated, bounded | `./.venv/bin/python -m pytest tests/test_source_metadata_capture.py -q` | exit 0 AND collected>0; includes a malformed/oversized provider-string case that must be rejected |
| M1 source_rank derived | `./.venv/bin/python -m pytest tests/test_source_rank_derivation.py -q` | exit 0; asserts a known `source_type` maps to a known rank, and unknown stays `unknown` |
| M1 export is recomputable | `./.venv/bin/python -m pytest tests/test_export_recomputability.py -q` | calls `export_run()` **twice in-process**, `del`s the telemetry `timeline`, canonical-sorts, asserts equal. Must NOT use `rf verify` — `verification.py` never calls `export_run()` |
| M1 export contract versioned | `./.venv/bin/python -m pytest tests/test_schema_validation.py -q -k export_schema` | exit 0; a pre-change legacy export fixture still validates against the bumped `rf-run-export-schema.json` |
| M2 record + value-free mirror | `./.venv/bin/python -m pytest tests/test_attribution_record_schema_fixtures.py -q` | exit 0; a mirror containing a raw value RAISES; a mirror without its authoritative record RAISES |
| M2 rollups monotone + sorted | `./.venv/bin/python -m pytest tests/test_attribution_rollups.py -q` | exit 0; asserts best=max/weakest=min, set-union order is stable across two runs, and no averaging path exists |
| M2 divergence uses injected clock | `./.venv/bin/python -m pytest tests/test_attribution_divergence.py -q` then `ls src/research_foundry/services/attribution_*.py \| wc -l` then `rg -n 'datetime\.now\|time\.time\|now_iso' src/research_foundry/services/attribution_*.py` | pytest exit 0 AND the `ls` count is **>0** AND the `rg` returns zero matches. The path-existence assertion is mandatory — a bare `rg` over files that do not exist yet returns zero and reads as pass (existing rule: ITT `node_01KYVBG7K191K4BKAZPEP5CRDF`). Pattern includes this repo's real idiom `now_iso()` (`ids.py:41`) |
| M2 staleness is append-only | `./.venv/bin/python -m pytest tests/test_attribution_staleness.py -q` | exit 0; asserts a refresh creates a NEW record and the prior record is unmodified |
| M3 provenance is structural | `./.venv/bin/python -m pytest tests/test_governance_adversarial.py -q -k attribution` | exit 0; includes a **sibling-field bypass** case (`trust.third_party_citation_rank`) that must also be rejected |
| M3 control is non-vacuous | remove the schema `if/then`, re-run the row above | suite must go **RED**; a still-green suite proves the control was never load-bearing |
| M3 pediatric namespace clean | `./.venv/bin/python -m pytest tests/ -q -k pediatric_namespace` | exit 0; asserts the writer never emits `pediatric_cds.<new_key>` |
| M4 tri-state coverage surfaced | `./.venv/bin/python -m pytest tests/test_catalog_attribution_coverage.py -q` | exit 0; `absent` and `not-yet-assessed` assert as **distinct** values, and the API returns an N-of-M line |
| M4 all 7 bundles non-regressive | `set -euo pipefail; n=0; for r in runs/*pediatric_cds*/; do ./.venv/bin/rf verify "$(basename $r)"; n=$((n+1)); done; test "$n" -eq 7` | the `test -eq 7` is the gate — a glob that matches nothing makes the loop exit 0 vacuously |

## Sequencing

`M2 → M3 → M4` is semantic: M3 enforces a shape M2 defines, and M4's columns and rollups consume both M1's
hydration and M2's records. **`M1 → M2` is merge-conflict hygiene, not a dependency** — both are additive
under existing open seams in `source_card.schema.yaml`, and M2 could land first if convenient. It is
sequenced only to keep two agents off one schema file; do not treat it as a semantic barrier.

## Execution ledger

Deviations logged with rationale to `.claude/worknotes/source-metadata-propagation/implementation-notes.md`,
reviewed at each milestone boundary rather than halted on. OQ-1, OQ-2, OQ-4 resolutions recorded there at entry.

**Blockers still stop** (failing test on current work, unsatisfiable declared artifact, exhausted recovery).
Beyond those, mid-milestone halts are only for destructive action, real scope change, or operator-only input.

**Mode-D always halts for explicit human approval** — auth · payments · schema migrations · data deletion ·
secret rotation · infrastructure. **M3 changes an authorization boundary and M4 performs a catalog schema
migration: both halt.**
