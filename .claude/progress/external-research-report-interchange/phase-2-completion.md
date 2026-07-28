---
type: progress
schema_version: 2
doc_type: progress
prd: external-research-report-interchange
feature_slug: external-research-report-interchange
phase: 2
title: Staging and Immutable Receipts — Completion Note
status: completed
created: '2026-07-26'
updated: '2026-07-26'
prd_ref: docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
owners:
- python-backend-engineer
---

# Phase 2 — Staging and Immutable Receipts — Completion Note

## Files changed

- `src/research_foundry/services/external_research_interchange.py` (new, ~1430 lines)
- `tests/unit/test_external_research_interchange.py` (new, 35 tests)
- `.claude/progress/external-research-report-interchange/phase-2-progress.md` (task statuses via CLI)

No files under `schemas/`, `templates/`, `docs/`, or `tests/fixtures/` were touched, per scope.

## How each task was satisfied

**ERI-2.1 — Safe packet inspection** (`inspect_packet`, `_discover_regular_files`,
`_stream_member`, `_open_checked`):

- Traversal safety mirrors `AssertionRegistry._read_regular_file` exactly as the contract
  instructs (§1.1): an openat-style directory-descriptor walk pinned to the packet root,
  `O_NOFOLLOW` per component, `lstat`-before-open symlink rejection, `fstat`-after-open
  device/inode verification. Additionally rejects literal `.`/`..`/absolute path components
  explicitly, since `dir_fd`-relative opens do not themselves stop a `..` component from
  escaping the pinned root (openat pinning ≠ chroot) — this is a gap the registry's own
  precedent doesn't need to close (it never receives `..` in practice) but a hostile external
  packet can.
- `_discover_regular_files` does a symlink/special-file-safe recursive `os.scandir` walk to
  detect undeclared members (regular files on disk not listed in `handoff.yaml`'s `members[]`)
  — mapped to `unsafe_member_path`.
- Member SHA-256 is computed via a 1 MiB streaming read (`_stream_member`); report/attachment
  bytes are never retained in memory (`keep_bytes=False`); only the three required YAML members
  (handoff/sources/assertion_candidates) are accumulated for parsing, each individually bounded
  by the 64 MiB per-member ceiling enforced mid-stream (abort before finishing an oversize read).
- All six frozen limits enforced: ≤64 members, ≤256 MiB packet (declared-vs-verified
  cross-checked), ≤64 MiB member, ≤32 attachments, ≤2000 sources, ≤5000 candidates.
- Schema major versions validated per §1.3 (`schema_major_versions` always fully populated,
  even on a blocked receipt where content couldn't be parsed far enough to declare its own
  version — falls back to the importer's supported majors).
- **Load-bearing finding not called out in the contract:** `handoff.yaml` declares its own
  `(path, byte_length, sha256)` as one of its own `members[]` entries — this is inherently
  circular to verify against itself (the declared hash necessarily covers bytes that include
  the declaration of that hash). `inspect_packet` treats the `handoff_manifest` role entry as
  trusted-as-declared for `packet_digest` purposes (contract §1.2 defines `packet_digest` over
  the *declared* manifest) and does not attempt to reconcile it against a re-hash of itself. All
  other members (report/sources/assertion_candidates/activity/attachment) are fully
  hash-reconciled against their declared values.

**ERI-2.2 — Stable staging manifest** (`ExternalResearchInterchange._stage_packet_artifacts`):

- `manifest.yaml` (packet_digest + declared members + schema majors) is written once, atomically
  (temp file + fsync + `os.replace`), under
  `external_research_interchange/workspaces/<sha256(workspace_id)>/packets/<packet_digest>/`.
  Re-write with identical bytes is a no-op; re-write with different bytes raises
  `StagingIntegrityError` (immutable-conflict discipline, same pattern as
  `AssertionRegistry._write_immutable_mapping`).
- `report.md` bytes are streamed (never decoded) into a content-addressed sibling
  `report/<sha256>.bin` — never passed to `source_cards.ingest_source()` or
  `AssertionRegistry.ingest()`, never parsed as YAML/text (contract §4.1's `report.md` special
  case). Workspace scoping uses `sha256(workspace_id)` in the path, not the raw tenant string
  (same precedent as `AssertionRegistry.workspace_key`).
- Packet-local `source_id`/`candidate_id` values are never used as raw filesystem path
  components anywhere — every effect file name is `f"{kind}__{sha256(action_id)}.yaml"`
  (contract §4.1: "sanitize packet-local IDs before any path use").

**ERI-2.3 — Effects and terminal receipt** (`ExternalResearchInterchange._execute`,
`_build_receipt_dict`, `_write_checkpoint_pending`, `_write_checkpoint_converged`):

- One immutable effect record per action (`effects/<kind>__<id-digest>.yaml`), written before
  the checkpoint is updated for that action.
- Checkpoint (`checkpoint.yaml`) is a **separate file** from the receipt, written with plain
  atomic replace (mutable) after every action's effect commits, and finally marked `converged`
  after the immutable receipt itself publishes — matching the schema's own description
  ("`converged` marks a checkpoint whose terminal receipt has already published").
- Terminal receipt (`receipt.yaml`) is written once, immutably, only after every declared action
  has a terminal outcome. `counts` (`actions_total`, `completed`, `quarantined`,
  `by_completeness_tier`, `by_reason_code`) are derived directly from the exact action list —
  every constructed receipt (including blocked and dry-run) is schema-validated in-process
  before being returned/persisted, as a defense-in-depth check beyond the unit tests.
- A resolution seam (`ResolveSource`/`ResolveCandidate` callables, `ResolutionContext`) is
  injected into `stage()` rather than hardcoded, so Phase 4's real SSRF-safe RFUP/RAL resolver
  can be plugged in without touching staging/receipt mechanics. The shipped
  `default_resolve_source`/`default_resolve_candidate` are deliberately conservative — honest
  about what a phase with **zero acquisition capability** can determine: a source with a
  declared locator reaches `locator_only` (no rendition binding attempted); a source with no
  locator quarantines `invalid_locator`; every candidate quarantines `citation_unresolved` or
  `basis_incomplete` (exact-passage binding is `AssertionRegistry.find_exact_passages()`, owned
  by Phase 4, never attempted here). This is why a fully "successful" Phase 2 default-resolver
  run typically lands at `completed_with_quarantine`, not `completed` — that is the honest
  outcome for a phase that doesn't yet resolve candidates, not a bug.
- Defensive enforcement of contract §1.4: `stage()` raises `InterchangeError` if any resolver
  (including a caller-supplied one) returns `completeness_tier="verified"` while
  `target_run_id` is `None` — tested via a deliberately broken injected resolver
  (`test_verified_tier_unreachable_when_target_run_id_null`).

**ERI-2.4 — Replay, conflict, dry-run** (`ExternalResearchInterchange.stage`, `_verify_replay`,
`_publish_or_replay_blocked`):

- Exact replay: before doing any work, `stage()` checks for an existing receipt at the computed
  `receipt_digest`. If found, its action set `(action_id, kind)` is compared against the
  freshly-derived deterministic action manifest; on a match the stored receipt is returned
  verbatim (`replayed=True`), with zero new effect files written (asserted in
  `test_exact_replay_returns_byte_identical_receipt` by diffing the `effects/` directory listing
  before and after).
- True conflict: a mismatch between the stored receipt's action set and the freshly-derived one
  (simulated by tampering with a persisted receipt's `actions[]` in place) raises
  `ReplayConflictError` and never overwrites the stored history.
- Distinct identity: different packet bytes, workspace, or policy content each independently
  produce a different `receipt_digest`/`packet_digest`/`policy_digest` and stage as fully
  independent receipts (three dedicated tests).
- Dry-run: builds and returns a fully schema-shaped, schema-validated receipt reflecting the
  planned actions/tiers/reasons, but persists nothing — `interchange.root` does not even exist
  on disk after a dry-run-only call (`test_dry_run_reports_actions_with_zero_canonical_effects`),
  and a dry-run call after a real stage does not perturb the already-published receipt bytes
  (`test_dry_run_never_mutates_existing_state`).
- Deterministic recovery across faults: `_interrupt_after_action_index` and
  `_interrupt_before_receipt_publish` fault-injection hooks (mirroring
  `AssertionRegistry`'s `_interrupt_after_edition_write` testing convention) let two tests
  simulate a crash mid-loop and immediately before terminal publish; both resume without
  duplicate effect writes and converge to a schema-valid receipt.

## Test counts

- `tests/unit/test_external_research_interchange.py`: **35 tests, all passing.**
- `tests/unit/test_external_research_schemas.py` (P1, regression check): **29 tests, all
  passing** — no regression (64 total passed across both files in one run).
- `mypy --ignore-missing-imports` on the new module: clean (0 errors after two fixes — a
  ternary-narrowing issue in `default_resolve_source` and a missing `dict[str, Any]`
  annotation in `_build_blocked_receipt`).

Command used:

```
PYTHONPATH=$PWD/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python \
  -m pytest tests/unit/test_external_research_interchange.py tests/unit/test_external_research_schemas.py -v
# 64 passed
```

## Explicit hostile-input fixture coverage (quality gate)

Each required category has a dedicated test, built inline via `tmp_path` (per the assignment's
"build fixtures inside your test module, not in tests/fixtures/" instruction):

| Category | Test |
|---|---|
| Traversal | `test_traversal_blocked_by_low_level_primitive` (low-level primitive, since the schema already forbids `..` at the handoff.yaml layer — this proves the runtime layer independently rejects it too) |
| Symlink | `test_symlink_member_blocks` |
| Special file | `test_special_file_member_blocks` (`os.mkfifo`; skips on platforms without it) |
| Undeclared member | `test_undeclared_member_blocks` |
| Oversize (member) | `test_oversize_member_blocks` |
| Oversize (packet total) | `test_oversize_packet_total_blocks` |
| Digest conflict | `test_digest_conflict_blocks` |

## Anything unresolved / scope notes for later phases

1. **Duplicate `source_id`/`candidate_id` within one packet.** Neither schema enforces
   `uniqueItems` on these fields. Phase 2's action-manifest builder does not deduplicate or
   reject duplicates — each array element becomes its own action (receipt `actions[]` entries
   may legitimately share an `action_id` string when `kind` differs, and even within one `kind`
   if a producer declares a genuine duplicate id; on-disk effect files are still collision-safe
   because their filename is `{kind}__{sha256(id)}`, not the literal id). Semantic
   duplicate-id handling (e.g., is this a data-quality quarantine reason?) is left to Phase 4's
   citation/source normalization (ERI-4.1), which is closer to the actual candidate/source
   semantics than P2's staging layer.
2. **The default resolvers are intentionally not a preview of Phase 4 behavior.** They exist so
   P2's staging/receipt/replay/dry-run machinery is fully exercisable and testable today. Phase
   4 replaces them by passing its own `resolve_source`/`resolve_candidate` callables into
   `stage()` — no change to this module's staging/receipt/checkpoint/replay code is anticipated.
3. **`_verify_replay`'s conflict check is structural (action id/kind set equality), not a full
   re-resolution equality check.** This matches the contract's own framing (§1.5 case 3: true
   conflict "should be structurally unreachable in normal operation" and is caused only by
   on-disk corruption or an importer defect) — re-running arbitrary resolvers (which Phase 4's
   real ones will do network I/O) on every replay to prove literal outcome-for-outcome equality
   would defeat the point of a fast, side-effect-free replay short-circuit.
4. **CLI wiring (`rf intake external-report`) is explicitly Phase 5's job (ERI-5.3)** — this
   module exposes a plain Python service API only.
