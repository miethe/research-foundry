## Phase 1b Completion Note — Contract Freeze: ERI-1.2/1.3/1.4/1.5 (identity, tiers, dependency map, acquisition policy)

**Mode:** B — Contract Drafting. No production code, no `schemas/`, no `tests/` were touched (a
parallel agent owns those — ERI-1.1). This pass authored one architecture doc plus the findings doc it
references.

### Summary

Froze `docs/dev/architecture/external-research-handoff-contract.md`, covering:

- **ERI-1.2 (identity)** — `packet_digest`/`receipt_digest` input formulas (verbatim per the task
  brief), the canonicalization generator to use (`sha256-canonical-json-v1`, reusing
  `AssertionRegistry._canonical_digest`'s existing convention rather than inventing a second one), a
  new `policy_digest` definition (not previously specified anywhere — needed because `receipt_digest`
  names it as an input but nothing upstream defines what it digests), the directory-only v1 boundary
  (with `AssertionRegistry._read_regular_file` cited as the existing traversal-safety pattern Phase 2
  should mirror), and a three-way replay/distinct-identity/integrity-conflict breakdown of "replay
  conflict behavior" that the plan text left implicit.
- **ERI-1.3 (tiers + quarantine)** — the 4-tier table, the two-layer terminal-state model (per-item
  action outcome vs. per-packet receipt status vs. checkpoint-only `pending`), the 19-code/4-family
  closed reason-code vocabulary, one canonical 8-step policy-evaluation ordering consolidating PRD §6.4
  + the NFR ordering requirement, and an explicit answer to "who holds verified authority" —
  `verification.py::verify_report` only, and a frozen consequence not previously stated: `verified` is
  categorically unreachable whenever `target_run_id` is null, because RF's verifier is run-scoped.
- **ERI-1.4 (dependency map)** — one subsection per dependency (RPC, RFUP, RAL, Intake Citation
  Adapters) with exact file:line citations for every reused symbol, a "no duplicate authority" summary,
  and two seam findings flagged for later phases: (a) `source_cards.ingest_source()` is hard run-scoped
  and cannot serve staging-only (`target_run_id: null`) imports as-is; (b) RFUP's existing
  network-touching code has **zero** SSRF-safe policy today (verified by grep — no
  `ipaddress.`/`is_private`/`is_loopback`/etc. anywhere under `services/search_router/`), so ERI-4.2's
  acquisition gate is a net-new control, not an extension of an existing one.
- **ERI-1.5 (hostile-data + acquisition policy)** — the inert-data rule (with `scan_for_injection`
  cited as useful-but-insufficient existing precedent — a detector, not a preventer), the `report.md`
  never-enters-writers rule, the full ordered scheme/address/DNS/redirect/peer gate (resolve → validate
  every answer → bind → verify connected peer; redirect hops re-validated in full, no fallback), safe
  denial (reusing `AssertionCatalog.denied_payload()`'s existing zero-leak shape a second time, after
  CARP already reused it once), and the governed-local-ingest-vs-network-acquisition separation
  (classified strictly by existing `_is_url`/`is_local_file` code, never by an untrusted packet hint
  field).

### RPC finding — recorded formally per the task's instruction

Created `.claude/findings/external-research-report-interchange-findings.md` (did not exist before this
pass). Confirmed via `schemas/` directory listing: 4 of RPC's 7 schemas exist
(`canonical_claim`, `inference_record`, `search_request`, `search_run`); 3 do not
(`provenance_origin`, `research_run_envelope`, `search_activity_receipt`). The contract doc's §3.1
resolves this the same way the sibling CARP contract freeze already resolved the identical situation:
reference the 4 present schemas directly, keep refs to the 3 absent ones optional/nullable/opaque, and
invent no field semantics for them. The findings doc also records a second, non-RPC finding (the RFUP
SSRF-policy gap) and the `source_cards.ingest_source()` run-scoping seam, per the same
"first real plan/reality mismatch creates the findings doc" policy — both are already resolved at the
contract level (not left as open design questions), so neither is assessed as needing a promoted
design-spec at this stage.

### Files Changed

- `docs/dev/architecture/external-research-handoff-contract.md` (new) — the frozen contract, this
  task's primary deliverable.
- `.claude/findings/external-research-report-interchange-findings.md` (new) — formal RPC-absence
  finding plus the RFUP-SSRF-gap and RAL run-scoping-seam findings.
- `.claude/progress/external-research-report-interchange/phase-1b-completion.md` (this file).

No other files were read-modified; `schemas/`, `tests/`, and
`docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md`'s
frontmatter were intentionally left untouched (out of this task's authorized scope — a parallel agent
owns `schemas/`/`tests/`, and no instruction authorized editing the plan file).

### Verification performed

Grounded every cited symbol against the actual worktree via `Read`/`Bash` (grep/`ls`), not against the
PRD/plan's own prose claims alone:

- `assertion_registry.py` — `AssertionRegistry.__init__`/`ingest`/`find_exact_passages`/
  `resolve_passage`/`_read_regular_file`/`_canonical_digest` (line numbers cited in the contract doc).
- `source_cards.py` — `ingest_source`/`ExtractionStatus`/`_is_url`/`is_local_file` branch.
- `search_router/router.py`, `search_router/safety.py`, `search_router/providers/*.py` — confirmed
  extraction entry points and confirmed (by targeted grep, zero matches) the absence of any SSRF policy.
- `verification.py` — `verify_report`, `resolve_exact_passage_mode`.
- `assertion_catalog.py` — `AssertionCatalogDenied`/`denied_payload()`.
- `schemas/` — directory listing to confirm the exact 4-present/3-absent RPC schema split.
- `docs/project_plans/feature_contracts/features/intake-citation-adapters.md` +
  repository-wide grep — confirmed `status: draft`, `files_affected: []`, and zero matching
  `CitationTuple`/adapter symbols on this tree.

### Unresolved / carried forward

- `policy_digest`'s exact field-level serialization is bound (must feed `sha256-canonical-json-v1`,
  named in §1.3) but its literal schema shape is left to ERI-1.1 (parallel schema-authoring task).
- The `source_cards.ingest_source()` run-scoping seam and the RFUP SSRF-gap are both **named and
  scoped**, not implemented — ERI-2/ERI-4 (later phases, out of this task's Mode B boundary) must
  resolve them in code.
- The findings doc's `status` remains `draft` and `promoted_to: null`; the parent plan's
  `findings_doc_ref`/`related_documents` fields still need to be set by whoever integrates this phase
  (not done here — editing the plan file was not part of this task's authorized scope).
- No git write command was run, per instruction.
