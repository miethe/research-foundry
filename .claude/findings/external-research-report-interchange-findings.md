---
schema_version: 2
doc_type: report
report_category: finding
title: "Findings: External Research Report Interchange"
status: completed
source: agent
created: 2026-07-26
updated: 2026-07-27
feature_slug: "external-research-report-interchange"
promoted_to: []
related_plan: /docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
---

# Findings: External Research Report Interchange

## Phase 1 Findings

### Discoveries

- **RPC (Research Provenance Continuity) is unexecuted, but partially present.** The implementation
  plan declares `P1 depends_on: [RPC-1.G]`. RPC has not run — there is no `RPC-1.G` gate to depend on.
  Of RPC's 7 named schemas, **4 exist** on this tree: `schemas/canonical_claim.schema.yaml`,
  `schemas/inference_record.schema.yaml`, `schemas/search_request.schema.yaml`,
  `schemas/search_run.schema.yaml`. **3 do not exist**: `provenance_origin`, `research_run_envelope`,
  `search_activity_receipt` (verified: repository-wide directory listing of `schemas/`, no matching
  files). This is the same unexecuted-dependency shape the sibling CARP (Catalog-Assisted Research
  Planning) contract freeze already documented for the same RPC dependency
  (`docs/dev/architecture/carp-contract-freeze.md` §4).

- **RFUP (RF Upstream Evidence Foundry) is executed, folded into existing services, but ships no
  SSRF-safe acquisition policy.** `docs/project_plans/implementation_plans/enhancements/rf-upstream-evidence-foundry-v1.md`
  frontmatter: `status: completed`; 6 phases of completion artifacts exist under
  `.claude/progress/rf-upstream-evidence-foundry/`, plus a follow-on `rfup-external-routing` plan
  already in progress. Its substrate lives inside `errors.py`, `cli_commands.py`,
  `services/verification.py`, `services/search_router/router.py`, `services/source_cards.py`,
  `services/assertion_registry.py` (per its own `files_affected`) rather than a standalone module.
  Verified network call sites on this tree — `_download_pdf_bytes` (`search_router/router.py:465-474`,
  bare `urllib.request.urlopen`, timeout only) and the provider modules under
  `services/search_router/providers/{brave,exa,firecrawl,jina,github}.py` (bare `httpx.get`/`httpx.post`
  calls) — perform **zero** address/DNS/redirect/peer validation. A repository-wide search for
  `ipaddress.`, `is_private`, `is_loopback`, `is_reserved`, `is_link_local`, `is_multicast` under
  `services/search_router/` returns zero matches.

- **Intake Citation Adapters is unexecuted.** `docs/project_plans/feature_contracts/features/intake-citation-adapters.md`
  frontmatter: `status: draft`, `files_affected: []`. No `CitationTuple`, `OpenAIIntakeAdapter`, or
  `PerplexityIntakeAdapter` symbol exists anywhere under `src/research_foundry/` (repository-wide grep,
  zero matches). The only existing dedup helper, `search_router/dedupe.py`, dedupes search-provider
  results and is not a substitute for the citation-tuple `(url, date)` dedup the draft contract
  describes.

- **`source_cards.ingest_source()` is hard run-scoped and unusable for staging-only imports.**
  (`source_cards.py:178`) requires an existing `run_id`, writes under `runs/<run>/sources/`, and raises
  `NotFoundError` if the run does not exist (`source_cards.py:216-218`). `AssertionRegistry`
  (`assertion_registry.py:107`, `assertion_registry.py:112`) is workspace-scoped, not run-scoped, and
  has no such dependency in `ingest()` / `find_exact_passages()` / `resolve_passage()`. ERI's
  `target_run_id: null` (staging-only) mode therefore cannot use `source_cards.ingest_source()` as-is
  without either forcing a run to exist (forbidden by ERI-FR-9) or failing.

### Plan / Reality Mismatches

- **P1's `depends_on: [RPC-1.G]` cannot be satisfied literally** — no such gate exists. Contract-freeze
  resolution (see `docs/dev/architecture/external-research-handoff-contract.md` §3.1): ERI references
  the 4 present RPC schemas directly by ID and keeps refs to the 3 absent ones optional/nullable,
  inventing no field semantics for them, mirroring the CARP precedent for the identical situation.

- **ERI-4.2 ("SSRF-safe governed acquisition gate ... before calling RFUP") reads as if it composes
  with an existing RFUP-owned network-safety layer.** In reality there is no existing network-safety
  layer anywhere in RFUP's call path to compose with — ERI-4.2 is a net-new control from a blank slate,
  not an addition to something partially built. This does not change ERI-4.2's scope (the plan's H3
  scenario list and quality gate already describe the full SSRF surface it must cover), but it does
  mean Phase 4 should not assume any existing helper (timeout aside) is reusable for the address/DNS/
  redirect/peer validation itself.

### Bugs / Gotchas

- None found that require a code fix at this phase (Mode B — contract drafting only; no production
  code was touched).

### Schema / Data Gaps

- `receipt_digest`'s frozen inputs (`packet_digest`, `workspace_id`, `target_run_id or null`,
  `policy_digest`, schema major versions) name a `policy_digest` that is not defined anywhere in the
  PRD or plan text prior to this contract-freeze document. It is now defined at
  `docs/dev/architecture/external-research-handoff-contract.md` §1.3 (a canonical digest over the
  effective acquisition-policy configuration at staging time) — ERI-1.1's schema authorship must
  produce a config object that this digest can be computed over; the exact field list is left to that
  task.

## Notes for Finalization

Per `.agents/skills/planning/references/deferred-items-and-findings.md`, load-bearing findings that
warrant design work get a design-spec authored at `docs/project_plans/design-specs/[finding-slug].md`
and are appended to the parent plan's `deferred_items_spec_refs`. None of the findings above are
assessed as requiring a design-spec at this stage — the RPC-absence and RFUP-SSRF-gap findings are both
already fully resolved by contract-level decisions in
`docs/dev/architecture/external-research-handoff-contract.md` (§3.1, §3.2, §4) rather than needing
further design work; they are recorded here as the evidentiary trail for those decisions. This document
was created under Phase 1 (Contract Freeze) and its `status`/`promoted_to` fields, and the parent plan's
`findings_doc_ref`/`related_documents`, still need updating by whichever agent owns the plan's frontmatter
integration — this task's authorized scope was limited to one architecture doc plus this findings doc
(Mode B — Contract Drafting; no plan-frontmatter edits were made).
