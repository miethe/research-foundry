---
it_schema: 1
feature_slug: eri-reused-edition-promotion
title: "ERI reused-edition promotion recovery — implementation plan"
doc_type: implementation_plan
status: completed
commit_refs:
  - ccebc24  # feat(eri): reused-edition promotion recovery (M1-M3)
  - 1c8dfc9  # fix(eri): make dry-run preview report the real run's outcome
merge_branch: main
merge_commit: ccebc24
oq_resolutions:
  - "OQ-1 RESOLVED (owner, 2026-07-31): keep reusing verification_failed. No member added to CANDIDATE_REASON_CODES; the versioned vocab contract is untouched."
  - "OQ-2 RESOLVED (owner, 2026-07-31): packet dir is ~/Downloads/knitwit-s1/packet (digest 35d50aeaab09b7b6..., matches the plan's 35d50aea...)."
  - "OQ-3 RESOLVED (owner, 2026-08-03): accept forward-only for the assertion_rollout population — the 452 rollout editions stay PERMANENTLY out of scope for any backfill (a quote-join has no honest full_text to recompute). This upholds the plan's accepted no-infer decision. NOTE: this resolution's original framing was WRONG about the consequence. It asserted the 4 verification_failed KnitWit S1 candidates were unrecoverable without a backfill; they were not, and no backfill was needed to recover them. See the M3 entry below for the actual root cause."
open_items: []
closed_items:
  - "M3 live-checkpoint AC — MET (2026-08-03), not superseded. Receipt erh_6221f13ef51a4891b6f5b61edadfc3eb8f9c7515057c8fad9c075f4efde1bf50: 38 actions, 20 completed / 18 quarantined, verification_failed == 0 on the authoritative per-action reason codes in receipts/<digest>/effects/*.yaml (was 4), 4 actions at passage_resolved, and 4 run source cards on disk in runs/rf_run_20260803_knitwit_s1_rights_evidence/sources/ (hobbii, lion-brand, lovecrafts, yarnspirations)."
  - "ROOT CAUSE of the 4 verification_failed candidates — NOT extraction_status, and NOT legacy-edition immutability. The --run ids passed on the earlier attempts never existed in runs/. default_promote raised NotFoundError -> PromotionOutcome(ok=False, error='target_run_not_found') -> _candidate_quarantine('verification_failed'). All 4 candidates in fact bound to editions that ALREADY carried extraction_status: full_text (the 16 already-set, acquired 2026-07-31), so the bound.extraction_status-is-None guard never fired. Scaffolding a real target run (rf capture -> triage -> plan) and re-importing from the MAIN CHECKOUT (never a worktree — FoundryPaths.discover() resolves to the worktree root and silently creates an empty ledger there) took verification_failed 4 -> 0 with no other change. Resolved via sibling plan eri-legacy-extraction-status-backfill-v1 (M1+M2 merged e3ca9ba under explicit Mode-D approval 2026-08-02; M3 closed by escalation req_01KZ2XTGYJ6CSDA4B1N1Q136FJ)."
  - "The 452-binding hypothesis was REFUTED, not confirmed. The 4 candidates are not in the excluded 452 and not in the 35 that M2 applied; there was no plan-internal contradiction."
tier: 2
priority: P2
points: 13
risk_level: medium
context_class: C3
created: 2026-07-31
updated: 2026-07-31
prd_ref: docs/project_plans/PRDs/enhancements/eri-reused-edition-promotion-v1.md
related_documents:
  - docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
intenttree_node: node_01KYWF7PSQSHYEZ526VEWBJ19F
acceptance_criteria:
  - "A newly created edition whose caller has an authoritative extraction status records it; an edition whose caller has none records nothing and is not inferred."
  - "Editions written before this change still pass verify_source_card_binding unchanged, with no backfill."
  - "A stored extraction status is tamper-evident and tri-state-validated on both write and read."
  - "A passage_resolved candidate bound to a reused edition promotes to a run source card; one with no recorded status still quarantines."
open_questions:
  - "OQ-1: May a dedicated milestone add a member to CANDIDATE_REASON_CODES in external_research_interchange.py? resolution.py's module docstring forbids *that module* editing interchange, which is not the same as forbidding the change outright — but the 19-code/4-family vocab is a versioned contract, so adding a member may be a schema-major event for external consumers. Resolve before M2 ships; the fallback is to keep reusing verification_failed."
  - "OQ-2: The pending checkpoint's packet directory is operator-held. M3 needs the on-disk packet path, not just the digest prefix, before it can run."
decisions:
  - decision: "Persist extraction_status inside the edition record's metadata_extensions mapping, not as a new top-level field."
    rationale: "schemas/source_edition.schema.yaml sets additionalProperties: false at the top level but leaves metadata_extensions open (additionalProperties: true, 'preserved non-identity metadata'). A top-level field would fail schema validation; a nested one is the schema's sanctioned extension point."
    status: accepted
  - decision: "Include extraction_status in _edition_binding — and therefore in edition_binding_sha256 — ONLY when present."
    rationale: "The binding is a closed projection that feeds the provenance digest. Adding the key unconditionally would change the digest shape for legacy editions (which lack it) and break verify_source_card_binding for every one of them. Conditional inclusion makes the field tamper-evident for new editions while leaving legacy provenance byte-identical, so no backfill is needed."
    status: accepted
  - decision: "extraction_status is OPTIONAL at ingest. A caller without an authoritative value passes nothing; no caller infers one."
    rationale: "assertion_rollout.py reconstructs editions from historical source cards, and cards written before the field existed genuinely lack it (source_cards.py:55-64). It cannot honestly choose between partial and locator_only, and a guess would fabricate fidelity metadata."
    status: accepted
  - decision: "Validate the tri-state at the registry boundary on both write and read; never depend on ingest_source's override handling."
    rationale: "ingest_source fail-opens an unrecognized override to the DERIVED status (source_cards.py:251-260), which for non-empty rehydrated content is full_text. A corrupt or unrecognized stored value would therefore silently promote as full-text evidence. The registry must reject it instead."
    status: accepted
  - decision: "Do not backfill, rewrite, or migrate any edition record already on disk."
    rationale: "Those editions have no recorded extraction status. Inferring one would fabricate evidence — precisely what the 7e2c1e1 fail-closed fix prevented — and it keeps this plan out of Mode-D schema-migration territory."
    status: accepted
  - decision: "Promotion target is a run source card, not the verified tier."
    rationale: "default_promote never self-assigns verified; that authority belongs to verify_report and assertion_materialization. The originating node description said 'verified tier' — this plan deliberately does not."
    status: accepted
routing_constraints:
  - "Evidence-ledger write-path and provenance-binding correctness (M1) MUST stay claude-primary — conditional binding inclusion and tri-state validation are not offload-eligible."
  - "The promotion guard fall-through in _finish_passage_resolved (M2) MUST stay claude-primary — it is the boundary that stops fabricated evidence reaching a source card."
  - "Test authoring and the live checkpoint re-resume (M3) are offload-eligible."
  - "Capability bar: any leg touching assertion_registry.py must reason about content-addressed immutability and provenance-digest invariants, not just make tests pass."

wave_plan:
  waves: [["M1"], ["M2"], ["M3"]]
  phases:
    - id: M1
      title: "Registry records, binds, and exposes extraction status"
      depends_on: []
      exit_criteria:
        - "A new edition with an authoritative status round-trips it through a public accessor and is covered by edition_binding_sha256."
        - "Legacy editions still pass verify_source_card_binding with no backfill."
    - id: M2
      title: "Reuse path rehydrates and reused-edition candidates promote"
      depends_on: ["M1"]
      exit_criteria:
        - "A reused-edition passage_resolved candidate promotes to a run source card."
        - "An edition with no recorded status still quarantines; reuse issues no network I/O."
    - id: M3
      title: "Regression coverage and live checkpoint re-validation"
      depends_on: ["M2"]
      exit_criteria:
        - "Full pytest suite green; the 7e2c1e1 quarantine test is updated, not deleted."
        - "The pending KnitWit S1 --run checkpoint re-resumes and the named candidates have run source cards."
---

# Implementation Plan — ERI reused-edition promotion recovery

Today a `passage_resolved` candidate bound to a **reused** edition cannot promote: `_existing_edition_reuse`
leaves `content` and `extraction_status` as `None`, and since `7e2c1e1` the promotion path fails closed and
quarantines it. This is most of the `--resume` population, because batch 1 acquires fresh while the resume
resolver reconstructs every earlier source read-only. When this is done, the registry hands back both the
stored rendition bytes and a validated, tamper-evident extraction status, so a reused-edition candidate
promotes exactly as a freshly-acquired one — while editions predating the change keep failing closed.

## Scope boundary

**In:** `assertion_registry.py` (optional per-edition extraction status in `metadata_extensions`, conditional
inclusion in `_edition_binding`, tri-state validation on write and read, a public rendition-bytes accessor);
`external_research_resolution.py` (`_existing_edition_reuse` rehydration, `_finish_passage_resolved` guard
fall-through); passing an authoritative status at the `ingest` call sites that have one.

**Out (stated, not silently dropped):**
- **Backfill/migration of on-disk editions** — excluded by decision. A rewrite of existing immutable records is
  a Mode-D schema migration and would need explicit human approval as its own piece of work.
- **Weakening `_write_immutable_mapping`** — explicitly rejected. Normal re-ingest of a published edition
  early-returns at `assertion_registry.py:425` and never reaches that comparison, so no tolerance is needed;
  adding one would let an in-memory mapping carrying a status be accepted while the on-disk record stays
  without it, then publish a manifest over that disagreement.
- **Re-fetch or re-extraction on the reuse path** — contractually read-only with zero network I/O.
- **The verified-tier verifier gate** — promotion lands a run source card; `verified` is a separate authority.
- **A new quarantine reason code** — gated on OQ-1; reusing `verification_failed` remains correct.
- **Making caller-supplied metadata disagreement raise on re-ingest** — today a completed-edition re-ingest
  returns the stored edition and ignores supplied media_type, scope, rights, and extensions. Changing that is a
  separate behavioral change with its own design and tests.

## Rubric — what "good" looks like

The registry is an evidence ledger, so the bar is *tamper-evidence preserved and extended*, not *tests pass*.
A good change is **additive, optional, and validated**: a new edition records more than it used to and that
addition is covered by the provenance digest; an old edition is byte-untouched and still verifies; a caller
without an authoritative status records nothing rather than guessing. The fail-closed property from `7e2c1e1`
survives for any edition whose status is genuinely unknown — the win is that fewer editions are in that state,
not that the guard is gone. Treat `ingest_source`'s fail-open override handling as a hazard to route around,
not a safety net. Wanting to rewrite an existing record, or to infer a status you do not have, is the signal to
stop and raise it.

## Named risks

- **Breaking provenance verification for every legacy edition (sharpest).** `_edition_binding` is a closed
  projection feeding `edition_binding_sha256`. Include the new key unconditionally and every pre-existing
  edition's recomputed digest diverges from its stored one, failing `verify_source_card_binding` fleet-wide with
  no backfill available. Inclusion must be conditional on presence. Build the legacy-edition verification test
  *before* touching the binding.
- **A stored status that silently becomes `full_text`.** `ingest_source` fail-opens an unrecognized override to
  the derived value, which for non-empty rehydrated content is `full_text` — so a corrupt or out-of-vocabulary
  stored status would promote reused content as full-text evidence without any error. The registry must
  validate the tri-state itself, on read as well as write.
- **A caller that cannot honestly supply a status.** `assertion_rollout.py` reconstructs editions from
  historical source cards that predate the field. It must pass nothing rather than infer; an inferred status is
  fabricated fidelity metadata.
- **The reuse path is contractually read-only.** Rehydration must come from what the registry already stored.
  Any solution that re-fetches, re-extracts, or reconstructs content from a passage is out of scope and wrong.
- **A test currently asserts the limitation.** `test_reused_edition_with_no_content_quarantines_instead_of_
  crashing` asserts a reused candidate quarantines. It must be *updated* to assert promotion for the recorded
  case and retained for the unrecorded case — not deleted, or the fail-closed proof is silently dropped.
- **Module boundary on the reason vocab.** `resolution.py` is forbidden by its own docstring from editing
  `external_research_interchange.py`. Do not route around this; resolve OQ-1 or keep `verification_failed`.

## References

- `src/research_foundry/services/assertion_registry.py` — `ingest` (:365), existing-edition early return (:425),
  edition record build (:443), `_write_immutable_mapping` (:347), `_edition_binding` (:243),
  `_provenance_record` (:226), binding verification (:620), `_content_path` (:141), `_load_edition_content` (:587).
- `src/research_foundry/services/external_research_resolution.py` — `_SourceOutcome` (:504),
  `_existing_edition_reuse` (:683), `_ensure_source_outcome` (:655), the `7e2c1e1` guard (:948),
  `PromotionRequest` (:424), `default_promote` (:445), module boundary rule (:55, :79).
- `src/research_foundry/services/source_cards.py` — `ExtractionStatus` (`full_text` | `locator_only` |
  `partial`), historical-card absence note (:55-64), fail-open override handling (:251-260), `ingest_source` (:178).
- `schemas/source_edition.schema.yaml` — top-level `additionalProperties: false` (:9); open
  `metadata_extensions` (:35). No schema change is required.
- `src/research_foundry/services/assertion_rollout.py` — historical reconstruction (:218, :238), `ingest` (:287).
- `src/research_foundry/cli_commands.py` — ERI import CLI, packet dir + `--workspace/--run/--resume` (:1123).
- Commit `7e2c1e1` — the fail-closed fix this plan supersedes.

## Milestones

### M1 — Registry records, binds, and exposes extraction status

The registry accepts an optional extraction status, validates it against the tri-state, stores it in the
edition's `metadata_extensions`, and includes it in the provenance binding when present. It offers a public way
to read back both the stored rendition bytes and the recorded status. Nothing on disk is rewritten and legacy
editions verify exactly as before.

**AC:** A new edition ingested with an authoritative status round-trips it through a public accessor and is
covered by `edition_binding_sha256`. A new edition ingested without one records no status and is not inferred.
An out-of-vocabulary status is rejected at the registry boundary rather than silently coerced. A public accessor
returns the stored rendition bytes with hash verification intact. Editions written before this change still pass
`verify_source_card_binding`, unchanged and un-backfilled. Tampering with a persisted edition or provenance
record — including with a stored `extraction_status` — still raises `RegistryIntegrityError`.

### M2 — Reuse path rehydrates and reused-edition candidates promote

`_existing_edition_reuse` populates `content` and `extraction_status` from the registry's public surface, so the
`7e2c1e1` guard falls through to real promotion for editions that have a recorded status. Editions without one
still hit the guard and quarantine.

**AC:** A `passage_resolved` candidate bound to a reused edition promotes to a run source card, matching a
freshly-acquired candidate in outcome. A candidate bound to an edition with no recorded status still quarantines
rather than promoting or crashing. The reuse path issues no network I/O and performs no re-extraction, asserted
by spying that the acquisition callable and `extract_bytes` are not invoked for the reused source.

### M3 — Regression coverage and live checkpoint re-validation

The behavior change is pinned at the exact intersection that broke, and proven against the real checkpoint that
motivated the work.

**AC:** `test_reused_edition_with_no_content_quarantines_instead_of_crashing` is updated to cover both the
promoting and the still-quarantining case. The full suite is green against a pre-change baseline. The pending
`--run` checkpoint (packet digest `35d50aea…`, workspace `default`, target
`rf_run_20260731_knitwit_s1_rights_evidence`) re-resumes, and the specific candidates that previously
quarantined are verified individually to be `passage_resolved` with run source-card artifacts on disk.

## AC -> command -> evidence

The single home for verification detail. The PRD owns narrative AC; this matrix owns proof.

| AC | Command | Evidence of pass |
|---|---|---|
| Status round-trips; absent stays absent; bad value rejected | `./.venv/bin/python -m pytest tests/unit/test_assertion_registry.py -q` | New round-trip, no-status, and rejected-vocabulary tests pass |
| Legacy editions still verify, un-backfilled | `./.venv/bin/python -m pytest tests/unit/test_assertion_registry.py -k "binding or provenance or legacy" -q` | A fixture edition written without the key passes `verify_source_card_binding`; its provenance bytes are unchanged |
| Persisted-record tampering still raises | `./.venv/bin/python -m pytest tests/unit/test_assertion_registry.py -k "tamper" -q` | New tests mutate a persisted edition/provenance (incl. `extraction_status`) and assert `RegistryIntegrityError` |
| Public accessor preserves hash verification | `./.venv/bin/python -m pytest tests/unit/test_assertion_registry.py -k "accessor or content" -q` | A test corrupts `content.bin` and asserts the public accessor raises rather than returning bytes |
| Reused candidate promotes; unrecorded quarantines; no I/O | `./.venv/bin/python -m pytest tests/integration/test_external_research_resolution.py -q` | Updated reuse test asserts promotion for recorded and quarantine for unrecorded; acquisition/`extract_bytes` spies record zero calls |
| No regression across the suite | `./.venv/bin/python -m pytest tests/ -q` | Compared against the pre-change baseline — do not assume zero prior failures |
| Live checkpoint completes | `rf` ERI import against the packet dir with `--workspace default --run rf_run_20260731_knitwit_s1_rights_evidence --resume` (packet path per OQ-2) | The named previously-quarantined candidates resolve `passage_resolved` and their run source-card files exist; aggregate receipt status alone is not accepted as proof |

## Sequencing (only if load-bearing)

M1 → M2 is load-bearing: M2 rehydrates from a public accessor and a persisted field that do not exist until M1
lands. Within M1, write the legacy-edition provenance-verification test **before** changing `_edition_binding` —
that failure is the plan's sharpest risk, and catching it after the binding change means debugging it through
M2's surface.

## Execution ledger

Deviations and conservative choices are logged with rationale to
`.claude/worknotes/eri-reused-edition-promotion/implementation-notes.md` and reviewed at each milestone
boundary — rather than halting on them.

**Blockers still stop.** Beyond those, mid-milestone halts are only for: destructive action, real scope change,
or input only the operator has (OQ-2's packet path is one).

**Mode-D boundary for this plan:** any rewrite, backfill, or migration of edition records already on disk is a
schema migration and **halts for explicit human approval**. No milestone here is expected to need one — if a
milestone concludes it does, that conclusion is the thing to escalate.
