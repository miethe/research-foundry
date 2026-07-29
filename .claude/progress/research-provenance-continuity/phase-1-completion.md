# Phase 1 Completion Note — Canonical Contract Freeze (RPC-1.G APPROVED)

**Date**: 2026-07-28 · **Branch**: worktree-rpc-v1 · **Baseline**: e76784b

## Outcome

RPC-1.G approved on the exact tree by the full gate stack:
1. task-completion-validator — APPROVED (RPC-1.5 + gate scope; additive-only verified vs baseline).
2. gpt-5.6-sol cross-model adversarial gate — 4 rounds (30 findings SOL-1..30, all closed;
   round-1..3 findings in `.claude/worknotes/rpc-sol-round{1,2,3}-findings.md`).
3. Karen (Fable 5) — **RPC-1.G VERDICT: APPROVED**; 19/19 vectors reproduced byte-for-byte;
   OQ-1/2/3 defaults RATIFIED; all four §22b bounded limitations RATIFIED; K-1 (stale
   EXPECTED_SCHEMA_NAMES fixture) fixed same-tree, 4-suite run green (exit 0).

## Deliverables

- NEW schemas: provenance_origin, research_run_envelope, search_activity_receipt,
  report_assertion_use (all `$id .../v1`, content-bound identities).
- AMENDED (strictly additive, empirically verified): search_run (+retrieval.activity_id +
  exclusivity), inference_record (+tombstoned, +version_digest), canonical_claim
  (+inference_refs, +version_digest), claim_ledger (+persistent_references.inference_version,
  optional), assertion_lifecycle_event (+active→* arms scoped to inference_record; one
  documented zero-instance narrowing of eligible→* scoping).
- `docs/dev/architecture/research-provenance-contract-freeze.md` — normative contract
  (§1–§22b): identity/fingerprint rules + worked vectors, envelope v1→receipt→v2 ordering,
  generation-manifest tamper-evidence root (§17.7a), durable-commit protocol (§17.7),
  seven-field commit-proof digest (§17.8), F11 gate-reversal preconditions ×6 (§17.1),
  CARP §4.2 rebase disposition, ERI/C4 authority boundaries, P7 verification tasks
  RPC-7.12..7.19, enforcing services N1–N4.
- `tests/test_schema_validation.py` — K-1 fix (4 new names + fixtures), 291/291 green.

## Residuals carried forward

- K-2 (Low): two illustrative vectors lack complete preimages (§5.1b forged-envelope,
  §4.2(d) locator-tamper) — P2 publishes preimages or marks non-normative.
- K-3: service-level MUSTs become real in P2/P3/P4; P7 tasks RPC-7.12..7.19 verify.
- Design notes N1–N4 + open items RPC-1.2.a, RPC-1.4.a → P2/P6.
- Karen prevention rule adopted: every future worked vector ships a complete recomputable
  preimage or is labeled non-normative.
