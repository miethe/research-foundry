---
title: "Assertion Ledger Activation — DI-1-Scoped Write-Site Audit"
doc_type: audit
feature_slug: assertion-ledger-activation
created: 2026-07-17
status: complete
scope: "New/changed assertion-ledger WRITE call sites introduced by the assertion-ledger-activation feature (P1–P4/P6). Read-only Mode E review by senior-code-reviewer; F1/F2 conformance gaps remediated same-pass."
audited_commits: "13265e0 (P1) · 054837d (P1.5) · 55ffccc (P2a) · 24e5bd0 (P2b) · db6dec8 (P4) · 59d01c8 (P3) + P6 F1/F2 hardening"
---

# Assertion Ledger Activation — DI-1-Scoped Write-Site Audit

## SCOPE BOUNDARY (read this before the table)

This audit covers **only the write call sites this feature introduced or changed**:
`assertion_materialization.py`, `source_cards.py::ingest_source`, `assertion_rollout.py`
(`backfill_run`/`backfill_corpus`), `claim_mapping.py` (integrity-gate check only, not a write
site), `run_launch.py` (P4 reuse wiring), and the `rf ingest` / `rf assertion backfill` CLI entry
points in `cli_commands.py`.

**This is NOT a full-project DI-1 closure claim.** It does not certify every write path in
Research Foundry, and it does not supersede the project-wide DI-1 full-surface audit that remains
the hard pre-multi-tenant-deploy gate (per the WKSP-304 AAR: a prior scoping enumeration on that
initiative was later found incomplete — two Mode-D leaks surfaced post-hoc after a similarly-scoped
pass was reported as complete). This document deliberately avoids repeating that failure mode by
stating its boundary explicitly: **feature-delta coverage only**. One out-of-scope observation
(`assertion_impact.py`) is flagged below for the separate full audit, not scored here.

## Method

For every construction of `AssertionRegistry`/`AssertionMaterializer` and every call to
`AssertionRegistry.ingest()` / `AssertionMaterializer.materialize_run()` reachable from the six
files in scope, the reviewer traced backward to confirm whether `resolve_or_deny()`
(`src/research_foundry/services/assertion_workspace.py`) — or a provably equivalent fail-closed
gate — executes before the write, and forward to confirm no other caller reaches the same write
method unguarded. The trace used repo-wide greps for `AssertionRegistry(`, `AssertionMaterializer(`,
`.materialize_run(`, `backfill_run(`, and `resolve_or_deny` across `src/`.

## Per-write-site table

| # | Site | Write method reached | Gated via `resolve_or_deny`? | Verdict |
|---|------|----------------------|-------------------------------|---------|
| 1 | `cli_commands.py::ingest` → `source_cards.py::ingest_source` → `AssertionRegistry.ingest()` | `AssertionRegistry.ingest()` | **Yes (post-remediation).** CLI resolves `resolve_or_deny("default")` before the service call; `ingest_source` now itself calls `resolve_or_deny` (F1 fix) and gates the ledger write on `resolution.allowed`, threading the stripped `resolution.workspace_id`. Blank/whitespace/absent → zero ledger writes, no exception, source-card markdown still written. `AssertionRegistry.__init__`'s own blank-id `ValueError` remains as defense-in-depth. | **CONFINED** |
| 2 | `cli_commands.py::assertion backfill` → `assertion_rollout.py::backfill_corpus` → `backfill_run` → registry/materializer | `AssertionRegistry.ingest()` + `AssertionMaterializer.materialize_run()` | **Yes.** `backfill_corpus` calls `resolve_or_deny` as its first substantive statement; `allowed=False` returns a typed zero-write denial; a separate `ledger_write_allowed` capability gate re-checks; only the stripped `resolution.workspace_id` is threaded onward. | **CONFINED** |
| 3 | `assertion_rollout.py::backfill_run` (public entry) | `AssertionRegistry(...)`, `AssertionMaterializer(...).materialize_run()` | **Yes (post-remediation).** `backfill_run` now self-gates via `resolve_or_deny(workspace_id)` at entry (F2 fix), returning the shared `_denied_backfill_receipt(...)` (zero writes) on denial instead of constructing registry/materializer with an unchecked id — so a future direct caller cannot bypass confinement. `backfill_corpus` behavior/output byte-identical (both now use the shared denial helper). | **CONFINED** |
| 4 | `assertion_materialization.py::AssertionMaterializer` (`__init__` / `materialize_run`) | `AssertionRegistry.ingest()` (transitive), immutable-record writes | **N/A by design — the sink, not the gate.** The P1 contract places gating on call sites, not on the registry/materializer. `__init__` independently raises `ValueError` on a blank/whitespace `workspace_id` (defense-in-depth). Only production caller is `backfill_run` (row 3), reachable only through gated paths. The module-level `materialize_run()` convenience fn is unused in production (test-only). | **CONFINED** |
| 5 | `claim_mapping.py::validate_extraction_fact_claim_mappings` (P2-01a bijection accommodation) | *None* | N/A — not a write site. No import of any assertion service; only reads extraction cards and raises `ValueError` on a non-bijective mapping. `build_claim_ledger`'s writes target the pre-existing `claims/claim_ledger.yaml` + `CLAIM_INDEX`, a separate run-local artifact family — not the assertion ledger. Opens **no** write bypass. | **CONFINED — not a write site** |
| 6 | `run_launch.py::retrieve_first_reuse_decision` / `launch_run` (P4 reuse wiring) | *None (read-only reuse decision)* | **Yes, for what it gates.** `resolve_or_deny(workspace_id)` runs before `evaluate_reuse(...)` (a read/policy decision, not a ledger write), which receives the stripped `resolution.workspace_id`. No `AssertionRegistry`/`AssertionMaterializer` construction exists in this file. | **CONFINED — no ledger write in this file** |

## Findings

**F1 — Medium — `source_cards.py::ingest_source` did not itself call `resolve_or_deny` (REMEDIATED 2026-07-17).**
At audit time, `ingest_source` gated the ledger write with an ad-hoc truthy check rather than the contract-mandated `resolve_or_deny` (a whitespace-only id would be truthy, pass the check, and reach `AssertionRegistry(workspace_id=" ")` → an uncaught `ValueError` *after* the source-card markdown was already written). Not a live confinement breach (the only caller passed `"default"`/None via `resolve_or_deny` first), but a deviation from the P1 contract's explicit mandate. **Remediation:** `ingest_source` now calls `resolve_or_deny(assertion_registry_workspace_id)` and gates the ledger write on `resolution.allowed`; a denied/blank/whitespace workspace skips the ledger write with zero writes and no exception (markdown still written). Regression test added: `test_ingest_source_whitespace_only_workspace_id_skips_ledger_write_without_raising`.

**F2 — Low — `backfill_run` public but self-unguarded (REMEDIATED 2026-07-17).**
At audit time, `backfill_run` (exported) relied entirely on `backfill_corpus` having gated; no other caller existed, but a future direct caller would reach registry/materializer construction with an unchecked `workspace_id`. **Remediation:** `backfill_run` now self-gates via `resolve_or_deny` at entry, returning the shared `_denied_backfill_receipt(...)` (zero writes) on denial. `backfill_corpus`'s denial branches were refactored to the same helper — output byte-identical (verified by existing tests). Regression test added: `test_backfill_run_denies_directly_with_blank_workspace_id`.

**F3 — Informational, out of scope — `assertion_impact.py` constructs `AssertionRegistry` (pre-existing).**
Found incidentally: `AssertionImpactReconciler.__init__` constructs `AssertionRegistry`. Not part of this feature's delta; carries its own independent fail-closed check (`workspace_context_missing` denial / `ValueError` guard). Nothing suggests an unscoped write, but its downstream writeback methods were not line-by-line traced. **Flag for the separate full-project DI-1 audit, not scored here.**

## Count of unscoped write paths found (this feature's delta): **0**

Every route from a CLI/service entry point to `AssertionRegistry.ingest()` or
`AssertionMaterializer.materialize_run()` passes through an explicit `resolve_or_deny()` gate before
the write, fails closed (zero writes) on an absent/blank/whitespace workspace, and — after the F1/F2
remediations — is self-gating rather than reliant on caller discipline or a second-layer constructor
guard alone.

## Conclusion

Within the six files enumerated for this feature's write-site delta, **no unscoped write path
exists**, and the two conformance gaps found at audit time (F1 Medium, F2 Low) have been remediated
in the same pass so that each write site self-gates via `resolve_or_deny`. AC-7 (DI-1-scoped audit
closes this feature's new-write-site delta) is satisfied. **This audit does not close DI-1
project-wide**; that gate remains open (F3 and the broader surface are tracked separately as the
hard pre-multi-tenant-deploy gate).
