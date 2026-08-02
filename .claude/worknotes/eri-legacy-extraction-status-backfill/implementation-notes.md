# ERI legacy extraction_status backfill — implementation notes (M1)

Plan: docs/project_plans/implementation_plans/enhancements/eri-legacy-extraction-status-backfill-v1.md

- 2026-08-01 — Test authoring kept claude-primary rather than offloaded (plan marks it
  offload-eligible) — risks R3/R4 couple the tests to the immutability/provenance invariants.

- 2026-08-01 — **OQ-1 resolved empirically, diverges from the plan's primary hypothesis.**
  The 100,232-byte edition (`sed_5f02b3a3c25c8c9a273f059ab6533a50ee89b5a3e8f62e1e367119f8166e9672`,
  source `src_40254dcde6c3dcbd34c2a0665a3053cc221b0a4e077ce3f34e8ccf3ab201a522`) decodes via UTF-8
  to **exactly 100,000 characters**. `_MAX_EXTRACT_CHARS` is 100,000 and `extract_bytes`'s check
  is `len(text) > _MAX_EXTRACT_CHARS` (strict greater-than), so 100,000 == 100,000 does NOT
  exceed the threshold and this edition classifies as `full_text`, not `partial`. All 35
  eligible editions came back `full_text`; **0 are `partial`**. The plan's own AC text names this
  exact outcome as an accepted alternative ("... or 35 full_text — OQ-1"), so this is a resolved
  open question, not a defect, but it does diverge from the plan's *primary* stated prediction
  (34 full_text + 1 partial) — flagging per instructions rather than silently matching the
  predicted split.

- 2026-08-01 — Real dry-run counts over live workspace W (503 edition dirs) via
  `dry_run_backfill_report`: **eligible=35, ineligible=452, already_set=16**
  (matches the plan's primary AC exactly), eligible sub-split **full_text=35, partial=0,
  locator_only=0** (diverges from the primary 34/1 prediction — see OQ-1 note above). Zero
  integrity errors across all 503 edition records. `authoritative_data_mutated: false` in the
  receipt. Command run (read-only):
  `PYTHONPATH=<worktree>/src <venv>/bin/python -m research_foundry.services.backfill_operations.eri_legacy_extraction_status --workspace-root <ledger>/assertion_ledger/workspaces/37a8eec1ce19687d132fe29051dca629d164e2c4958ba141d5f4133a33f0688f --out /tmp/eri_backfill_dry_run.json`

- 2026-08-01 — Chose to place the eligibility gate (`categorize_edition`) and the read-only walk
  (`dry_run_backfill_report`) in a new package `services/backfill_operations/` (a directory, not
  a flat module) since the plan's own frontmatter reference and the live ledger's own
  `backfill_operations/` directory both anticipate M2's apply path landing alongside M1's dry run
  in the same family. Kept it to one submodule (`eri_legacy_extraction_status.py`) for M1 — no M2
  apply/rollback code was written (Mode-D, not authorized this milestone).

- 2026-08-01 — `dry_run_backfill_report` enforces its own no-write invariant via a same-process
  before/after structural fingerprint (`_tree_fingerprint`: every file's path+size+mtime_ns under
  the workspace root, hashed) and raises `RuntimeError` if anything changed — this is an executable
  assertion inside the function that touches the live ledger, not just a docstring claim. Also
  verified externally: `ls -la` timestamps under the live workspace directory are unchanged
  before/after the dry run invocation above.

- 2026-08-01 — `workspace_root` parameter is the assertion-ledger *workspace* directory itself
  (e.g. `assertion_ledger/workspaces/<sha256(workspace_id)>`), not the outer `FoundryPaths.root`.
  This matches what the task handed me directly and avoids needing to re-derive or guess a
  workspace_id -> hash mapping inside the module; callers that only have a `workspace_id` can hash
  it themselves or go through `AssertionRegistry(workspace_id=...).root`.

- 2026-08-01 — **BLOCKING DEFECT found and fixed post-review: recompute-from-stored-text was
  overclaiming fidelity at exactly `_MAX_EXTRACT_CHARS`, exactly the shape R1 warns about.**
  `extract_bytes` truncates with `text[:_MAX_EXTRACT_CHARS]` when it marks `partial`
  (`external_research_resolution.py:388`), so a stored text of exactly `_MAX_EXTRACT_CHARS` chars
  is produced by two byte-identical-on-disk histories: (a) an original document of exactly that
  length -> genuinely `full_text`, and (b) a longer original truncated by that line -> genuinely
  `partial`. Recompute, seeing only the stored text, cannot distinguish them. The original
  `recompute_extraction_status` used `len(text) > _MAX_EXTRACT_CHARS` (mirroring `extract_bytes`'s
  own strict-greater-than check), which classified case (a) and (b) identically as `full_text` —
  wrong for (b). Verified directly against the coordinator's evidence: OQ-1's own boundary edition
  (`sed_5f02b3a3...`, 100,232 raw bytes / 100,000 decoded chars) has stored text ending
  `'... it is also imp'` — cut off mid-word, and starting `'Diagnostic Approach to Macrocephaly...'`
  — confirming it is case (b), a genuinely truncated document, not one that happens to end at the
  limit.
  **Fix (fail-closed, asymmetric by design):** `recompute_extraction_status` now uses
  `len(text) >= _MAX_EXTRACT_CHARS` -> `partial`; only strictly-less-than is provably untruncated
  -> `full_text`. `extract_bytes` itself is UNCHANGED — its forward behavior (given the full
  original document) is correct; only the recompute predicate, which only ever sees
  already-possibly-truncated stored text, needed to be more conservative than forward extraction.
  Documented this asymmetry prominently in both the function docstring and a new test
  (`test_recompute_diverges_from_extract_bytes_at_exact_boundary_fail_closed`) so a future reader
  does not "fix" it back into agreement with `extract_bytes`. Also removed the now-stale
  `test_recompute_matches_extract_bytes_at_exact_boundary` test that had asserted the (wrong)
  equality, and cleaned up an unused `shutil` import and a dead `binding` local variable in
  `_plant_synthetic_edition` (not the result of a `verify_source_card_binding` call, so no
  assertion was owed — just dead code, deleted).
  **Re-run dry-run counts over live workspace W after the fix:** eligible=35, ineligible=452,
  already_set=16 (unchanged), eligible sub-split now **full_text=34, partial=1** — matches the
  plan's PRIMARY hypothesis exactly (previously reported 35/0 was the defect, now corrected).
  `authoritative_data_mutated: false`; zero mutation to the ledger (verified via the same
  `_tree_fingerprint` in-code check plus external file-timestamp inspection). Test file
  (12/12 passed, exit 0) and the three regression files
  `test_assertion_registry.py`/`test_assertion_rollout.py`/`test_assertion_backfill.py` (all green,
  exit 0) re-run clean after the fix.

## 2026-08-02 — cross-model (gpt-5.6-sol) gate could not be obtained for M1

Attempted twice; neither produced findings or a verdict. Recorded as a FAILED lens, not a pass.

- Attempt 1: `codex exec --model gpt-5.6-sol ... "$(cat prompt.md)"` — the prompt never reached
  codex as an argument; it fell through to stdin and the entire transcript was one line,
  "Reading additional input from stdin...", with exit 0. A run that looks completed and is empty.
- Attempt 2: same via `- < prompt.md` (correct form). Codex began by reading this repo's
  `.agents/skills/**` and, following the repo's own "delegate everything" instructions, tried to
  spawn reviewer subagents rather than review directly. It failed with
  `Full-history forked agents inherit the parent agent type` and
  `collab spawn failed: agent thread limit reached`, then terminated without a report.
- Attempt 3 (retry with delegation explicitly forbidden and file scope pinned): behaved correctly
  at the outset — confirmed it would review directly — but ended mid-file-dump after ~40 min with
  no findings section and no OVERALL line.

Consequence: M1's formal gate is `gate_lens: [validator]` per the plan, and
task-completion-validator APPROVED with independent re-verification (it re-ran the dry-run itself,
checked mutation via `find -newermt`, and inversion-checked each load-bearing test). M1 is
therefore properly gated. The cross-model lens is deferred to M2, where it matters more
(irreversible-outward, `gate_lens: [security, validator]`) — and should be run through a different
transport (gemini-cli or ICA) rather than a fourth codex attempt.

Reusable lesson: in THIS repo, `codex exec` inherits the project's delegate-everything instructions
and burns its budget orchestrating instead of reviewing. Pin its file scope AND forbid delegation
explicitly, or use a different provider for the diverse lens.

## 2026-08-02 — M2 apply/rollback built and proved on a COPY (Mode-D, human-approved this session)

Extended the same module (`eri_legacy_extraction_status.py`) rather than creating a sibling file,
per the task's "same backfill_operations package" instruction — `apply_backfill` and
`rollback_backfill` sit alongside M1's unmodified `categorize_edition`/`recompute_extraction_status`/
`dry_run_backfill_report`.

- **Binding recompute reuses the registry's own primitives, not a hand roll.** `apply_backfill`
  calls `AssertionRegistry._edition_binding(new_edition)` (the class's own `@staticmethod`, called
  directly — no instance needed since it does not touch `self`) and the module-level
  `_canonical_digest` from `assertion_registry.py`, both imported directly. Writes go through the
  same module's `_atomic_dump`/`_atomic_write_bytes` (temp-file + fsync + `os.replace`) — the exact
  primitives `AssertionRegistry.ingest` itself uses — but deliberately bypass
  `_write_immutable_mapping`'s conflict check (which would reject any same-path rewrite by design)
  since this is a reviewed, out-of-band rewrite of already-published records, per the task's
  explicit instruction not to weaken that check for any other caller.

- **R5 (partial apply) is fail-closed by construction, not merely avoided.** Per-edition, the
  provenance write happens before the edition write; if the process is killed between them (either
  order), `AssertionRegistry._load_edition`/`_load_provenance` — the exact chain
  `verify_source_card_binding` uses internally — raises `RegistryIntegrityError` on the mismatched
  pair, from either direction (proved by
  `test_partial_pair_new_status_stale_provenance_fails_closed` and
  `test_partial_pair_new_provenance_stale_edition_fails_closed`). If the *second* write itself
  raises inside the running process, `apply_backfill` immediately rewrites both files back to their
  pre-mutation in-memory bytes before re-raising (proved by
  `test_apply_self_repairs_in_process_when_second_write_fails`, which monkeypatches `_atomic_dump`
  to fail on the edition-side write only). A genuine crash that survives neither path leaves a
  fail-closed, receipt-recoverable state: `rollback_backfill` restores byte-identical originals
  from the apply receipt's own embedded base64 snapshots, and a resumed `apply_backfill` run is
  safe because an already-applied edition classifies `already_set` and is skipped (proved by
  `test_apply_is_idempotent_and_safe_to_resume`).

- **Deviation from the literal AC wording ("all 35 pass `verify_source_card_binding`").** Calling
  the *public* `verify_source_card_binding(source_key, edition, source_card)` against real live
  editions requires knowing each edition's original `source_key` — but `source_id` is a one-way
  hash of `source_key` (`AssertionRegistry._source_id`), and the on-disk source manifest never
  stores `source_key` in the clear, so the pre-image is not recoverable for the 35 real editions on
  the copy. Proved the AC's real intent two ways instead: (1) on the copy, called
  `registry._load_edition(source_id, edition_id)` for all 35 post-apply — this is literally the
  first line of `verify_source_card_binding`'s body and, via its own call to `_load_provenance`,
  performs every binding/provenance check `verify_source_card_binding` performs except the
  source-card-snapshot comparison (which is orthogonal to this backfill — it did not change); (2)
  in the M2 test suite, planted a frozen fixture through the real `AssertionRegistry.ingest` path
  with a *known* `source_key` and a real `source_card_snapshot`, ran `apply_backfill`, then called
  the actual public `verify_source_card_binding` end-to-end and it passed
  (`test_apply_writes_atomic_pair_and_passes_real_verify_source_card_binding`). Between the two,
  every code path `verify_source_card_binding` exercises is proved against real production code —
  the public entry point itself just cannot be invoked against the 35 live editions without their
  source keys.

- **`_receipt_id` signature extended, not forked.** Added a `kind: str = "dry_run"` keyword
  (default preserves M1's exact receipt-id prefix/behavior unchanged) so apply/apply-preview/
  rollback receipts get distinct id prefixes (`..._apply_...`, `..._apply_preview_...`,
  `..._rollback_...`) without a second near-duplicate helper.

- **Receipt location convention matches `assertion_rollout.py`'s own precedent.** The CLI
  (`apply --apply`) defaults its receipt to `<workspace_root>/backfill_operations/<receipt_id>.json`
  when `--out` is not given (mirrors `registry.root / "backfill_operations" / f"{run_id}.yaml"` in
  `assertion_rollout.py`) — this is INSIDE `assertion_ledger/`, unlike M1's `--out`, which is
  explicitly forbidden from writing there. A preview (no `--apply`) still defaults to stdout, same
  as M1.

### Proof run against a working copy of the live ledger (never the live ledger itself)

Copied `/Users/miethe/rf-ledger-snapshots/20260802-modeD/assertion_ledger` to a scratch working
copy at `/tmp/eri-m2-proof/assertion_ledger` (the snapshot itself was never mutated — verified by
never writing under `/Users/miethe/rf-ledger-snapshots/...` at any point). All five numbers below
are from that working copy; artifacts (manifests, receipts) left at `/tmp/eri-m2-proof/` for
independent re-inspection.

1. **Apply touches exactly 35 editions.** `apply_backfill(..., apply=True)` receipt:
   `counts = {"eligible": 35, "ineligible": 452, "already_set": 16, "applied": 35}`,
   `len(changes) == 35`, all with `"applied": true`.
2. **All 35 pass the registry's own post-apply binding verification.** Iterated the 35 changes
   from the receipt and called `AssertionRegistry(workspace_id="default", paths=FoundryPaths(root=<copy>))._load_edition(source_id, edition_id)`
   for each (workspace_id `"default"` confirmed by `sha256("default")` matching the copy's
   workspace-key directory name exactly) — **35/35 passed**, 0 raised `RegistryIntegrityError`. See
   the deviation note above for why this reaches the public entry point's real checks rather than
   `verify_source_card_binding` itself.
3. **The 452 + 16 are byte-identical post-apply.** Built a per-file sha256 manifest of the working
   copy before and after apply (`16873` files total): **0 files added, 0 files removed, 70 files
   changed** — and all 70 are exactly the two YAML files (`<edition_id>.yaml` +
   `<edition_id>/provenance.yaml`) for the 35 applied editions (35 × 2 = 70). No `content.bin` is
   in the changed set for any of the 503 editions.
4. **Rollback restores byte-identical to pre-apply.** `rollback_backfill(root, receipt)` returned
   `restored_count: 35`. A fresh manifest of the working copy after rollback is **identical** to the
   pre-apply manifest (`diff manifest_before.json manifest_after_rollback.json` — zero diff).
5. **Every edition's `content_sha256` is unchanged.** Re-hashed `content.bin` for all 35 applied
   editions against each change's recorded `content_sha256` from the receipt — **35/35 match**, 0
   mismatches.

Also proved, ahead of the live apply: an `apply=False` preview run (the CLI default) makes the
exact same classification and would-be-binding-diff computation with **zero writes** — manifest
before/after the preview call is byte-identical.

### What the orchestrator still owns

- The live apply itself (`--apply` against the real `assertion_ledger/`) — not run here per the
  task's explicit instruction.
- M2's `gate_lens: [security, validator]` review (`gate_lens_reason: irreversible-outward`).
- Re-running the same five proofs against the *actual* live workspace immediately after the real
  apply, before M3.

## 2026-08-02 — M2 second B2 round: DESIGN CHANGE (not another guard), B2 actually closed

Second consecutive round on the same defect class (approval-scope drift). The coordinator's own
diagnosis was exact and verified independently: the round-1 pinned-scope check
(`_check_pinned_scope`) returned `live_ids`, but `apply_backfill`'s caller **discarded the return
value** and the mutate loop re-globbed `sources/*/editions/*.yaml` fresh at the top of its own
loop — so the check was a snapshot, and the writes were never actually constrained by it. An
edition that appeared between the check and the loop reaching its position in sort order sorted
into the unprocessed tail and got mutated, unapproved, silently.

Per doctrine, this got a design change, not a third guard:

- **One glob, period.** `_enumerate_editions(root)` is now the ONLY
  `glob("sources/*/editions/*.yaml")` anywhere in this module's M2 code. It returns a frozen
  `_EnumerationResult` (`eligible_ids`, `already_set_ids`, `ineligible_count`,
  `integrity_errors`) from a single metadata-only pass (no `content.bin`/`provenance.yaml` reads).
  Deleted `_live_eligible_ids` entirely (it was the round-1 check's own private re-glob).
- **The write loop iterates the approved set, not a fresh walk.** `apply_backfill` now runs
  `_enumerate_editions` exactly once per call; when `apply=True`, `_check_pinned_scope` is called
  with that SAME `eligible_ids` frozenset (never re-derived), and its return value (`approved_ids`)
  is what the eligible-track loop iterates via `sorted(approved_ids)` — paths derived from each
  `(source_id, edition_id)` directly, never re-globbed. The `already_set` repair track similarly
  iterates `enum_result.already_set_ids` from the SAME single enumeration. Net result: exactly one
  `glob()` call per `apply_backfill` invocation (down from two: the round-1 pinned-scope check's own
  glob, plus the mutate loop's separate glob) — collapsing redundant walks turned out to be a real
  simplification, not added complexity, exactly as predicted.
- **NB-3 structural guard.** Inside the eligible-track loop, `if (source_id, edition_id) not in
  approved_ids: raise BackfillIntegrityError(...)` — unreachable today (the loop iterates
  `approved_ids` directly), kept explicitly so a future refactor that reintroduces a walk fails
  loudly instead of silently widening scope. Verified present via
  `test_membership_guard_is_present_and_would_catch_a_regression` (a source-inspection test, not a
  behavioral one, since the guard can't trip today by construction).
- **Item 9's write-time re-validation is now clearly separated from the enumeration.** Each
  approved id's record is re-read fresh and re-classified (`categorize_edition`) when the loop
  reaches it; if it no longer qualifies as `eligible`, it's reported as `drift_detected` and
  skipped — approval of the ID never implied approval of whatever VALUES happen to be there by the
  time the loop arrives (NB-1, see below). `_mutate_pair` itself also re-checks both files'
  current bytes against the caller's captured snapshot as the FIRST thing it does, immediately
  adjacent to its own write attempt, rather than relying solely on the caller's earlier check
  (small hardening, folded in alongside the restructure since `_mutate_pair`'s signature was
  already being touched).

**NB-1 (docstring correction).** Reworded the B2 docstring paragraphs in `apply_backfill` and
`_check_pinned_scope` to say explicitly: pinning covers the eligible **ID SET**, never the
recomputed extraction_status/binding **VALUES** — a human approves "these 35 ids," not "these 35
specific output values." Item 9's write-time re-read/re-classify is what actually governs whether
a given id's current record still qualifies; that was already true in round 1's code but the prose
implied more than the code guaranteed.

**NB-2 (re-check immediately adjacent to the repair write).** `_mutate_pair`'s except-branch now
re-reads a file's bytes ONE MORE TIME directly adjacent to the `_atomic_write_bytes(before_bytes,
path)` call, rather than relying on the `current` value read a few lines earlier when the
decision-to-repair was made. `_repair_broken_already_set`'s primary write already had its
check-then-write pair back-to-back with nothing in between; left the logic as-is and added a
comment making that explicit for reviewers, since its except-branch performs no write at all (pure
diagnosis, nothing to re-check before).

**Lock file hygiene fix.** `_advisory_lock` now creates `.apply.lock` with an explicit `os.chmod(...,
0o600)` (verified: `os.open`'s mode argument is masked by the process umask and was NOT reliably
0600 before this fix -- confirmed 0755 in the coordinator's own inspection) and unlinks it on
release whenever the call turned out not to mutate anything (tracked via a small `_LockState`
object yielded by the context manager; the caller sets `.mutated = True` only after an actual
successful write). A refused apply (unpinned, scope-drifted, etc.) or a preview-only rollback no
longer leaves a stray lock artifact sitting in the evidence tree.

**`receipt_from_journal` torn-line tolerance.** A single journal line that fails `json.loads` (or
parses to something other than a JSON object) is now recorded in a new `torn_lines` list and
skipped, rather than raising and losing the ability to reconstruct every OTHER, earlier-fsynced
entry in the same journal.

**`apply_backfill` now calls `root.resolve()`** right after the existence check, matching
`rollback_backfill`'s existing behavior (was a plain `Path(workspace_root)` before, an
inconsistency the coordinator flagged as a NIT).

### The actual gap, tested directly (not just the top-of-call check)

`test_apply_iterates_the_pinned_set_not_a_fresh_glob_scope_drift_midflight` hooks
`_check_pinned_scope` itself (wraps the real function, calls it, then injects a new qualifying
edition) — i.e. it simulates a concurrent ordinary writer landing a new edition in the EXACT window
between "the scope check passed" and "the write loop begins," which is precisely the gap the
coordinator identified and round-1's own `test_apply_with_scope_drift_since_pinning_is_rejected_before_any_write_b2`
did NOT cover (that test injects the drifting edition BEFORE the call, only exercising the
top-of-call snapshot).

**Verified this test fails against the pre-restructure code, not just asserted.** Snapshotted the
module before starting this round (`/tmp/eri_legacy_extraction_status_PRE_RESTRUCTURE.py`),
temporarily placed a copy inside the real package (so its relative imports resolved) as
`eri_legacy_extraction_status_OLD_PROOF.py`, and ran an adapted version of the same scenario against
it directly (adapted only because the OLD `_check_pinned_scope(root, ...)` took `root` instead of
`live_ids` -- the hook still fires at the identical call site). Result, verbatim:

```
injected id touched?: True
injected edition now has extraction_status?: True
applied count: 2
CONFIRMED: old code silently mutated the mid-flight, unapproved edition -- BUG REPRODUCED
```

The temporary `eri_legacy_extraction_status_OLD_PROOF.py` file was deleted immediately after
(`git status` confirms it never landed; only the two real files show as modified). Against the
restructured code, the same scenario (via the real pytest test) passes: the injected edition is
never touched, remains classified eligible, and the receipt's `changes` contains only the
originally-approved edition.

### Other new tests this round

- `test_only_one_glob_per_apply_call` — monkeypatches `Path.glob` to count calls matching
  `"sources/*/editions/*.yaml"`; asserts exactly 1 for both a preview and a real pinned apply.
- `test_lock_file_is_0600_and_unlinked_after_a_refused_apply` / `..._and_kept_after_a_real_apply` /
  `test_lock_file_unlinked_after_rollback_preview_only` — lock hygiene.
- `test_receipt_from_journal_tolerates_a_torn_trailing_line` — truncates a real journal's last line
  mid-JSON and confirms the earlier, intact entry is still recovered and rollback-able.

### Re-proof on a THIRD fresh working copy (`/tmp/eri-m2-proof-v3/`), same snapshot source, neither
the operator snapshot nor the live ledger touched (confirmed identically to prior rounds: 0 files
under the snapshot newer than the snapshot dir; no `assertion_ledger/` in this worktree)

1. **Apply touches exactly 35 editions** — `counts.applied == 35`, `len(changes) == 35`.
2. **All 35 pass the registry's own post-apply binding verification** — `_load_edition` 35/35, 0
   `RegistryIntegrityError`.
3. **452 + 16 byte-identical** — manifest diff: 2 added (`.apply.lock` now 0600, and the journal —
   both under `backfill_operations/`, not ledger data), 0 removed, 70 changed, ALL under `sources/`
   (35 × 2).
4. **Rollback restores byte-identical** — preview: `restored_count: 0`, `would_restore_count: 35`,
   zero writes; real (`--apply`): `restored_count: 35`; `sources/` manifest post-rollback identical
   to pre-apply (5410 files, byte-for-byte).
5. **content_sha256 unchanged** — 35/35 match.

### Pytest exit codes (clean `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`)

- `tests/unit/test_eri_legacy_extraction_status_backfill_apply.py` (37 tests, up from 29): **exit 0**
- Combined with M1's file + `test_assertion_registry.py`: **exit 0**
- `flake8 --select=E9,F63,F7,F82` on the module + test file: **exit 0**
- The new mid-flight test run in isolation against the restructured code: **exit 0** (1 passed)
- The adapted equivalent run directly (not via pytest) against the pre-restructure snapshot:
  reproduced the bug (see verbatim output above) -- explicit confirmation this is a regression
  test for a real, previously-exploitable gap, not a test written after the fact to match
  already-correct behavior.

## 2026-08-02 — M2 third round: RE-SCOPE (not a fourth fix), already_set repair path DELETED

Third consecutive round on the same defect class (approval-scope drift), one layer over: the
second round constrained the ELIGIBLE write loop to iterate the approved set, but left the
sibling `already_set` repair loop -- `_repair_broken_already_set`, added in round 1's item 5 --
completely unconstrained by any approved set. Per this project's doctrine, a third failure on one
defect class escalates to re-scoping the feature, not writing a fourth guard.

**Removed entirely, not guarded:**

- `_repair_broken_already_set` (the whole function).
- The `already_set_ids` mutation loop inside `apply_backfill` (previously a second loop after the
  eligible-track loop, iterating `enum_result.already_set_ids` and calling the repair function on
  a binding mismatch).
- The `repaired` counter and `repairs` list from both `apply_backfill`'s receipt shape and
  `receipt_from_journal`'s counts.
- The test that covered the removed path: `test_half_rolled_back_already_set_is_repaired_not_skipped_item5`
  (deleted from `tests/unit/test_eri_legacy_extraction_status_backfill_apply.py`).

**`already_set` is now read-only in `apply_backfill`.** `counts["already_set"]` is set directly
from `len(enum_result.already_set_ids)` -- the single enumeration's classification alone. No
`already_set` edition's `edition.yaml`/`provenance.yaml` is ever opened (read OR written) by
`apply_backfill` again. Proved structurally, not just behaviorally, by
`test_apply_never_opens_already_set_files_at_all` (monkeypatches `Path.read_bytes` to record any
attempt to open an already_set edition's files -- asserts zero). Proved behaviorally by
`test_already_set_is_read_only_in_apply_even_when_binding_is_broken`: plants a half-rolled-back
already_set edition (binding intentionally mismatched, the exact shape the removed repair path
used to fix), runs both a preview and a real `apply_backfill(apply=True, ...)` against it, and
asserts its bytes are byte-identical before and after both calls. The same test then demonstrates
the actual documented recovery: **re-running the original apply receipt through
`rollback_backfill(..., apply=True)`** completes the fix the interrupted rollback started --
unconditional restore, already tested, no second mutation surface required.

**Why this is not a capitulation (the coordinator's own framing, verified rather than just
accepted):** the repair-on-apply path was never in M2's acceptance criteria (35 pass binding
verification post-apply; rollback restores byte-identical; the 452 untouched with unchanged
digests) -- it was introduced unilaterally in round 1's fix for item 5 as an extra convenience.
Removing it returns to plan scope. The half-state it used to fix is already recoverable via the
unconditional, idempotent, already-tested rollback path (`rollback_backfill` restores every entry
in a receipt's `changes` list regardless of current on-disk state -- verified in round 1/2's own
test suite, unchanged this round). Keeping two mutation surfaces (the eligible write loop and the
already_set repair loop), each independently needing atomicity + reversibility + approval-scope
enforcement, is exactly the shape that failed three times; collapsing to one mutation surface over
the approved set makes scope-compliance structural rather than a property that has to be
separately re-proven for every write path in the module.

**Post-removal structural check (the coordinator's own instruction: "if you find any other write
path in the apply direction, say so").** Grepped every call site of `_atomic_dump`/
`_atomic_write_bytes`/`_mutate_pair` in the module:
- `_mutate_pair`'s own two `_atomic_dump` calls (its primary write) and one `_atomic_write_bytes`
  call (its self-repair-on-failure branch, reverting the SAME pair it just tried to write -- not a
  second independent write path, the failure-recovery half of the one operation).
- `apply_backfill` calls `_mutate_pair` exactly ONCE, from exactly one place, inside the eligible
  track's loop over `approved_ids`.
- `rollback_backfill`'s two `_atomic_write_bytes` calls are a DIFFERENT function/direction
  entirely (restoring FROM a receipt, not applying TO the ledger) and were never in question.
- `_append_journal_entry` writes to the write-ahead journal file under `backfill_operations/` (the
  audit trail), never to `sources/` ledger data -- a deliberately separate write surface from "the
  apply direction" mutation of ledger records, unaffected by this round.

**No new writes were found in the apply direction beyond the one `_mutate_pair` call site** -- the
scope is now correctly ONE loop, over the approved set, full stop.

**Also fixed this round (both real, both cheap, per the coordinator):**

1. **Apply-path id validation.** The eligible-track loop now calls
   `_validate_entry_ids_and_paths(root, source_id, edition_id)` -- previously used only on the
   rollback side -- before deriving `edition_path`/`provenance_path` from an approved id. Path
   derivation replaced a glob in the second round; a glob could only ever yield real in-tree paths,
   but derivation on its own cannot make that same guarantee without this check. Proved via
   `test_apply_validates_ids_before_deriving_paths`, which monkeypatches `_check_pinned_scope` to
   return a traversal-shaped id after the real check runs, and asserts `apply_backfill` raises
   `BackfillIntegrityError` rather than deriving a path from it.
2. **Missing-file-at-write-time is a clean skip-and-report.** Reading `edition.yaml`,
   `provenance.yaml`, or `content.bin` for an approved id that no longer exists now catches
   `FileNotFoundError` and records `{"source_id", "source_edition_id", "path"}` in a new
   `missing_at_write_time` list (and `counts["missing_at_write_time"]`), continuing to the next
   edition -- rather than an uncaught exception aborting the whole pass after any earlier
   mutations in the same run. Proved by `test_missing_edition_file_at_write_time_is_skipped_and_reported`
   and `test_missing_provenance_file_at_write_time_is_skipped_and_reported` (both hook
   `_check_pinned_scope` to delete the file AFTER the scope check passes but BEFORE the write loop
   reaches it -- a genuine present-at-approval-gone-at-write-time race, not something the B2 check
   itself would already catch by simply no longer enumerating a deleted file).

**Also tightened (per the coordinator, not deferred): `receipt_from_journal`'s torn-line
tolerance.** Previously any malformed line anywhere in the journal was silently skipped and
reported in `torn_lines`. Narrowed to the single TRAILING non-blank line only -- the one shape an
interrupted `write()` mid-append can actually produce, since every earlier line was already
fsynced in full before the next append began. A malformed line anywhere else now raises
`BackfillIntegrityError` immediately, because silently skipping it could drop a rollback snapshot
for an edition that had already been mutated, with no error to say so. Proved by
`test_receipt_from_journal_raises_on_a_malformed_mid_journal_line` (corrupts the middle line of a
3-entry journal, asserts the raise) alongside the pre-existing
`test_receipt_from_journal_tolerates_a_torn_trailing_line` (still passes unchanged -- it already
only ever corrupted the last line).

### Docstrings and comments updated to state plainly (not implied)

- Module docstring: new "Third hardening round" section (verbatim re-scope rationale).
- `apply_backfill`'s docstring: replaced the item-4/item-5 paragraph describing repair with an
  explicit "already_set editions are READ-ONLY... recovery is: re-run the same rollback receipt"
  paragraph.
- `categorize_edition`'s NOTE: no longer claims `apply_backfill` "checks binding agreement before
  deciding to skip vs. repair" -- states plainly that already_set is read-only and counted from
  classification alone.
- `_binding_matches_provenance`'s docstring: states it is "Only called for the eligible track...
  `already_set` editions are read-only and never reach this check."
- `rollback_backfill`'s docstring: removed the "(item 5's supporting fix)" label (that mechanism,
  unconditional restore, is unchanged and kept -- only the retired label and the now-inapplicable
  claim about a naive `apply_backfill` re-run were corrected) and states the recovery path in
  plain language: "re-run the same rollback receipt (or a `receipt_from_journal`-derived one)."

### Re-proof on a FOURTH fresh working copy (`/tmp/eri-m2-proof-v4/`), same snapshot source, neither
the operator snapshot nor the live ledger touched (confirmed identically to every prior round: 0
files under the snapshot newer than the snapshot dir; no `assertion_ledger/` in this worktree)

1. **Apply touches exactly 35 editions** — `counts.applied == 35`, `applied count` over
   `changes` == 35.
2. **All 35 pass the registry's own post-apply binding verification** — `_load_edition` 35/35, 0
   `RegistryIntegrityError`.
3. **452 + 16 byte-identical** — manifest diff: 2 added (`.apply.lock`, the journal — both
   `backfill_operations/`, not ledger data), 0 removed, 70 changed, ALL under `sources/` (35 × 2).
4. **Rollback restores byte-identical** — real rollback (`--apply`): `restored_count: 35`;
   `sources/` manifest post-rollback identical to pre-apply (5410 files, byte-for-byte).
5. **content_sha256 unchanged** — 35/35 match.

### Pytest exit codes (clean `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`)

- `tests/unit/test_eri_legacy_extraction_status_backfill_apply.py`: **41 tests, exit 0** (deleted
  1 -- the repair-path test -- added 6: `test_already_set_is_read_only_in_apply_even_when_binding_is_broken`,
  `test_apply_never_opens_already_set_files_at_all`,
  `test_receipt_from_journal_raises_on_a_malformed_mid_journal_line`,
  `test_missing_edition_file_at_write_time_is_skipped_and_reported`,
  `test_missing_provenance_file_at_write_time_is_skipped_and_reported`,
  `test_apply_validates_ids_before_deriving_paths`).
- Combined with M1's file + `test_assertion_registry.py`: **exit 0**.
- `flake8 --select=E9,F63,F7,F82` on the module + test file: **exit 0** (also confirmed clean
  under plain `pyflakes`, no unused-import/unused-variable warnings from the removed code).

## 2026-08-02 — M2 hardening round: cross-model REJECT, 9 items + B1/B2/N1/N2/N5/Nit1

The security gate returned `VERDICT: REJECT` on the first M2 cut (validator passed; all five
happy-path proofs reproduced independently — every finding was in the FAILURE paths). Two
BLOCKING findings (B1, B2) arrived in a follow-up message after the initial nine; folded into the
same pass per instruction, not treated as a later round. All eleven items addressed in
`eri_legacy_extraction_status.py` (full rewrite of `apply_backfill`/`rollback_backfill`, new
`receipt_from_journal`, `_mutate_pair`, `_repair_broken_already_set`, `_advisory_lock`,
`_validate_entry_ids_and_paths`, durable `_atomic_dump`/`_atomic_write_bytes` wrappers). 15 new
tests added (29 total in the M2 file, up from 14).

**Design decisions worth flagging (judgment calls, not literal transcription of the ask):**

- **B2 pinning is unconditional, not "receipt or count."** The finding said "add
  `--pinned-receipt` and/or `--expect-count`... an unpinned live apply should be impossible."
  `expect_count` alone cannot close the gap it's meant to close: if one qualifying edition
  disappears and a different one appears between dry-run and apply, the COUNT can coincidentally
  still match while the SET has silently changed. Made `pinned_receipt` unconditionally REQUIRED
  under `apply=True` (both at the function level and the CLI, which additionally hard-requires
  `--pinned-receipt` whenever `--apply` is passed); `expect_count` is accepted as an optional
  redundant assertion on top, never a substitute. `_pinned_edition_ids` accepts either an M1
  dry-run receipt (`eligible_editions`) or an M2 preview receipt (now ALSO exposes
  `eligible_editions`, not just `changes` — see next point).
- **`apply_backfill`'s receipt gained a new top-level `eligible_editions` list, independent of
  `changes`.** Found via test failure: `changes` only contains entries that make it past item 4's
  pre-existing-integrity-failure check, so an eligible edition diverted into
  `pre_existing_integrity_failures` was silently DROPPED from the pinned-id set derived from
  `changes` — a self-inflicted B2 false-positive (the live re-check would then see "added" an id
  that was always there, just not in `changes`). Fixed by tracking every `category=="eligible"`
  edition into `eligible_editions` up front, mirroring M1's own key name, before any downstream
  branching.
- **Item 5's repair is scoped OUTSIDE B2's pinning check entirely.** A half-rolled-back
  `already_set` edition is never in the `eligible` category (`categorize_edition` still says
  `already_set`), so it never appears in `eligible_editions`/pinning at all — repair proceeds
  under `apply=True` regardless of what's pinned. This is a deliberate scope boundary: B2's
  finding was specifically about the "35 eligible editions" approval scope drifting; repairs are a
  self-healing action on records THIS tool already touched, not a scope-expansion risk in the same
  sense. Flagging this as a boundary a reviewer should confirm, not something I decided
  unilaterally without surfacing it.
- **Item 4 vs item 5 get different default actions on purpose.** An `eligible` edition with a
  pre-existing binding mismatch is a corruption of UNKNOWN origin (could predate this tool
  entirely) → skip + report only, never touched, preserving the evidence of brokenness. An
  `already_set` edition with a binding mismatch is provably OUR OWN half-finished action (only
  `extraction_status` + a stale binding — a shape only an interrupted apply/rollback of THIS
  backfill produces) → repair automatically, syncing provenance to the edition's own already-
  present value, never inventing a new one from content.
- **B1b's "refuse to clobber diverged bytes" check compares against BOTH the pre-mutation snapshot
  AND the intended new bytes**, not just the snapshot — a file whose write actually SUCCEEDED
  (current == new bytes) is a legitimate repair target (revert it), not a divergence. Only a THIRD
  state (matches neither) refuses.
- **The happy-path receipt and the crash-recovery receipt are deliberately NOT the same code
  path.** `apply_backfill`'s own in-memory bookkeeping produces the returned receipt (richer detail:
  `pre_existing_integrity_failures`, `drift_detected_editions`, `integrity_errors` — none of which
  are derivable from the journal, since those editions were never journaled at all, by design,
  since nothing was ever going to touch them). `receipt_from_journal` is a SEPARATE, independently
  tested function used only for genuine crash recovery (no returned receipt to work from at all).
  Both feed the identical `rollback_backfill`. This avoids merge complexity between two
  bookkeeping systems while still satisfying "never depend on the function returning normally" —
  that guarantee lives entirely in the journal + `receipt_from_journal`, not in the happy path.
- **Rollback restores UNCONDITIONALLY now** (dropped the old `if not change.get("applied"):
  continue` gate entirely) — this is what makes item 5's "half-state during rollback itself"
  self-healing: re-running rollback with the same receipt is idempotent and safe regardless of how
  far a prior rollback attempt got, because it never consults any current-state classification
  before restoring.
- **N1 applied to all three CLIs** (`_main`, `_apply_main`, `_rollback_main`), not just apply, per
  "treat as blocking-adjacent" — a typo'd `--workspace-root` now `parser.error()`s (exit 2) instead
  of silently reporting zero of everything.
- **Lock file (`backfill_operations/.apply.lock`) and journal files are explicitly OUT OF SCOPE**
  for "byte-identical"/"nothing written" assertions — they are this tool's own audit trail under
  `backfill_operations/`, not ledger data, and are expected to accumulate. Introduced `_ledger_tree`
  in the test file (scoped to `sources/`) for assertions that should ignore them; `_tree` (whole
  tree) is still used wherever the assertion genuinely means "the whole workspace," e.g. previews.

### Re-proof on a SECOND fresh working copy (`/tmp/eri-m2-proof-v2/`), same snapshot source,
neither the operator snapshot (`/Users/miethe/rf-ledger-snapshots/20260802-modeD/`) nor the live
ledger touched (confirmed: 0 files under the snapshot newer than the snapshot dir itself; no
`assertion_ledger/` exists in this worktree at all):

1. **Apply touches exactly 35 editions** — `counts.applied == 35`, `len(changes) == 35`.
2. **All 35 pass the registry's own post-apply binding verification** — `_load_edition` 35/35, 0
   `RegistryIntegrityError` (same documented deviation as before: the public
   `verify_source_card_binding` needs each edition's un-recoverable `source_key`; this reaches
   every check it performs except the source-card-snapshot comparison, which is orthogonal and
   unchanged by this backfill).
3. **452 + 16 byte-identical** — manifest diff: **2 files added** (`.apply.lock`,
   `apply_<run_id>.journal.jsonl` — both under `backfill_operations/`, our own audit trail, not
   ledger data), **0 removed**, **70 changed, all under `sources/`** (35 × 2). Zero changes outside
   `sources/` other than the two additions.
4. **Rollback restores byte-identical** — rollback preview (no `--apply`) reports
   `would_restore_count: 35`, `restored_count: 0`, zero writes; real rollback (`--apply`) reports
   `restored_count: 35`; a fresh manifest of `sources/` post-rollback is **identical** (5410 files,
   byte-for-byte) to the pre-apply manifest.
5. **content_sha256 unchanged** — 35/35 match, both from the receipt's own recorded value and a
   fresh re-hash of `content.bin`.

**New hardening-specific proofs, all against the same working copy:**

- **N1**: `apply --apply --pinned-receipt ... --workspace-root /does/not/exist` → `parser.error`,
  exit code **2**, no receipt written.
- **B2 (CLI)**: `apply --apply` with no `--pinned-receipt` → `parser.error`, exit code **2**,
  before any write.
- **B2 (function, scope drift + count mismatch)**: exercised in the test suite
  (`test_apply_with_scope_drift_since_pinning_is_rejected_before_any_write_b2`,
  `test_apply_expect_count_mismatch_is_rejected_before_any_write_b2`) — both raise
  `BackfillIntegrityError` before any write, `_ledger_tree` unchanged.
- **B1b, item 1 (journal-recovery), item 3 (traversal), item 4, item 5, N2**: all covered by
  dedicated tests (`test_repair_refuses_to_clobber_diverged_bytes_b1b`,
  `test_journal_survives_a_midloop_crash_and_recovers_via_receipt_from_journal`,
  `test_rollback_rejects_a_traversal_receipt_item3`,
  `test_eligible_edition_that_does_not_verify_is_skipped_not_overwritten_item4`,
  `test_half_rolled_back_already_set_is_repaired_not_skipped_item5`,
  `test_repair_failure_does_not_mask_original_exception_n2`) — all green.

### Pytest exit codes (clean `__pycache__`, `PYTHONDONTWRITEBYTECODE=1`)

- `tests/unit/test_eri_legacy_extraction_status_backfill_apply.py` (29 tests): **exit 0**
- `tests/unit/test_eri_legacy_extraction_status_backfill_apply.py` + `..._backfill.py` (M1) +
  `test_assertion_registry.py` combined: **exit 0**
- `flake8 --select=E9,F63,F7,F82` on both changed source files + the test file: **exit 0**

## 2026-08-02 — orchestrator verification of the hardening round

Negative controls run against the LIVE workspace path (guards must fire before any write). All six
raised correctly, pre-write:

| Input | Result |
|---|---|
| `apply=True, pinned_receipt=None` | BackfillIntegrityError — pinned receipt required (B2) |
| `apply=1` (truthy non-bool) | TypeError (item 6) |
| `apply="yes"` | TypeError (item 6) |
| `apply=True`, empty pinned receipt | BackfillIntegrityError — unrecognizable receipt |
| `apply=True`, pinned set mismatch | BackfillIntegrityError — live set != approved set (B2) |
| rollback without confirm | ValueError before any write |

The Pyright warning "Mapping[str, Any] | None not assignable to pinned_receipt" at the
`_check_pinned_scope` call site is a NARROWING FALSE POSITIVE: line 849 raises when
`mutate and pinned_receipt is None`, so None cannot reach the call. Verified empirically above, not
just by reading. Do not "fix" it by making the parameter Optional — that would make the guard
skippable.

### NEW non-blocking finding (orchestrator): refused apply leaves a lockfile in the evidence tree

A refused/guard-rejected apply still creates `backfill_operations/.apply.lock` inside the
authoritative workspace, because the flock is acquired BEFORE the pinned-scope check. The ordering is
CORRECT and must not change — the pinned check reads live state, so it has to be inside the lock or a
check-then-apply race opens up. Two real consequences:

1. It breaks the "refused/dry-run ⇒ zero writes under assertion_ledger" property M1 established (and
   which the `--out` guard explicitly enforces elsewhere).
2. It produces a FALSE ALARM in any "is the ledger untouched?" verification. It did exactly that here.

Also: the lockfile is created mode 0755 (world-readable, executable) in a tree whose records are 0600.

Follow-up (not blocking the apply, no evidence risk — the file is zero-byte and carries no data):
release should unlink the lockfile when no mutation occurred, and create it 0600. Until then, any
ledger-integrity check must exclude `backfill_operations/.apply.lock`.

## 2026-08-02 — M2 LIVE APPLY SUCCEEDED; M3 FAILED

### M2 — live apply complete, AC met

Ran through the real CLI entry point, pinned to the operator-approved M1 dry-run receipt:
`... apply --workspace-root <W> --pinned-receipt /tmp/m1-receipt.json --apply`

- receipt: `ral_eri_legacy_status_apply_edc5562345bf6620` (also copied into `backfill_operations/`)
- counts: applied 35, eligible 35, ineligible 452, already_set 16, drift 0, missing 0,
  pre_existing_integrity_failure 0, integrity_errors 0
- full-tree manifest diff vs pre-apply baseline: 0 removed, **70 changed** (35 edition records + 35
  provenance.yaml), 2 added (`.apply.lock` + journal, both under `backfill_operations/`, not ledger data)
- **no `content.bin` changed**; every change under `sources/`
- **35/35 pass binding verification** via `AssertionRegistry._load_edition` → `_load_provenance`
  (recompute + compare of `edition_binding` and `edition_binding_sha256`), 0 failures
- recorded status split 34 `full_text` + 1 `partial` (the truncation-aware partial from the M1 fix)
- rollback input validated: preview reports `would_restore: 35`, writes nothing
- post-M3 re-check: all 35 still verify

Workspace confirmed as `sha256("default")` = `37a8eec1ce19687d132fe29051dca629d164e2c4958ba141d5f4133a33f0688f`.

### M3 — FAILED. Two separate problems.

**1. The AC as written is VACUOUS.** M3's AC reads
`by_completeness_tier.verification_failed < 4`. But `by_completeness_tier` tallies ONLY completed
actions — every quarantined action has `completeness_tier: null` in the receipt (verified: 16 tiered,
22 null). So `verification_failed` can never appear in that map for a quarantined candidate, and the
AC is satisfied by construction regardless of outcome. Any run reporting "verification_failed = 0"
from that field is proving nothing. The real reason codes live in the per-action effect files.

**2. Measured on the authoritative reason codes, verification_failed is STILL 4 — unchanged.**
From `receipts/<digest>/effects/*.yaml` of the live import:

| reason_code | count |
|---|---|
| null (completed) | 16 |
| citation_unresolved | 12 |
| **verification_failed** | **4** |
| source_unavailable | 3 |
| citation_ambiguous | 3 |

12+4+3+3 = 22 = `quarantined`. The predecessor plan recorded 4 `verification_failed` before this
work; it is still 4 after. **The backfill did not move the number M3 exists to move.**

Leading hypothesis, NOT yet confirmed: the 4 candidates bind to editions in the **452**
`assertion_rollout` population (2026-07-17), which M2 excluded PERMANENTLY by accepted decision
("a quote-join has no honest full_text to recompute"). If so, M3's AC was never achievable under M2's
own scope decision — a plan-internal contradiction that should have been caught at planning time,
not after a Mode-D mutation. The quarantined candidate effects carry `canonical_refs: {}` (they
quarantine before binding to an edition), so confirming this requires tracing candidate → source →
edition through the packet, which was not completed.

### M3 process failure worth recording separately: the first M3 run was INERT

The first M3 invocation was run with cwd inside the git worktree. `FoundryPaths.discover()` resolved
to the WORKTREE root, so the import created a fresh empty `assertion_ledger/` + `runs/` there and
fresh-acquired 16 sources into it. It never touched the backfilled live ledger. It exited 0, reported
the CORRECT packet digest (`35d50aea…`), and produced a plausible receipt — nothing in the output
signalled that it had run against an empty store. This is exactly the plan's own R4 "green but inert"
risk, landing on M3 itself, which is the milestone whose entire purpose is to catch inert changes.
**Rule: run `rf` from the main checkout, never from a worktree — the data plane does not follow the
worktree.**

### Also: dry-run does NOT predict the live outcome (regression of 1f982a7's property)

Against the same live ledger, same packet, same target:
- `--dry-run`: `{locator_only: 15, passage_resolved: 4, source_resolved: 4}`, 23 completed, 15 quarantined
- real run: `{source_resolved: 16}`, 16 completed, 22 quarantined, **passage_resolved 0**

Confirmed NOT a receipt replay — a fresh target run id produced a new receipt
(`erh_13a0b4a6…`) and the same live numbers. The preview over-reports resolution: it claimed 4
`passage_resolved` that the real import did not produce. `1c8dfc9`/`1f982a7` fixed this property for
the reuse path; it is not holding here. A preview that disagrees with the run it previews is worse
than no preview — it was the basis on which I briefly believed M3 had passed.
