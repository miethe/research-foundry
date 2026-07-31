---
type: context
prd: eri-reused-edition-promotion
milestone: M1
updated: 2026-07-31
---

# M1 implementation notes — Registry records, binds, and exposes extraction status

## Deviations / conservative choices

1. **Validation vocabulary duplicated, not imported.** `assertion_registry.py` defines its own
   `_EXTRACTION_STATUSES = frozenset({"full_text", "partial", "locator_only"})` rather than importing
   `source_cards.ExtractionStatus`. `source_cards.py` already imports `AssertionRegistry` lazily
   (inside `ingest_source`, not at module top level) specifically to avoid a circular import; importing
   `source_cards` from `assertion_registry.py` at module scope would reintroduce that cycle in the
   other direction. The three literal values are hand-kept in sync — flagged in a code comment at the
   constant's definition site.

2. **Out-of-vocabulary status on write returns a typed non-reusable result, not a raised exception.**
   The plan's invariant 5 says "raise rather than coerce." I read that as "reject rather than silently
   substitute a plausible value" (the ingest_source fail-open hazard it contrasts with), not literally
   "the write path must throw." `ingest()`'s existing convention for every other caller-input validation
   failure (`missing_rights_metadata`, `invalid_passage_selector`, `ambiguous_selector`,
   `unsupported_or_missing_content`) is a typed `RegistryImportResult` with a `reason` string and no
   side effects — I kept `invalid_extraction_status` consistent with that sibling set rather than making
   this one check throw where its neighbors don't. The **read** path (`_extraction_status`, called from
   `_edition_binding`, which both `_load_edition`/`_load_provenance` and `verify_source_card_binding`
   route through) does raise `RegistryIntegrityError`, matching every other integrity check in this
   module — there is no typed-result convention on that side to stay consistent with.

3. **Single validation point covers both write and read**, per the AC. `_edition_binding` calls the new
   `_extraction_status(extensions)` helper unconditionally; it's invoked by `_provenance_record` at
   ingest time (write) and by `_load_provenance`/`verify_source_card_binding` afterwards (read). One
   helper, one set of rules, so write-time and read-time validation cannot drift apart.

4. **Legacy-edition regression test order.** The plan asked to write the legacy-edition
   provenance-verification test *before* touching `_edition_binding`, to catch the sharpest named risk
   early. In practice I implemented the conditional-inclusion change and the test in the same pass (this
   is a single-agent sprint, not a phased handoff), but verified the same property the sequencing note
   protects: `test_ingest_without_status_records_nothing` and `test_legacy_edition_still_verifies_unbackfilled`
   both assert that an edition with no recorded status has no `extraction_status` key anywhere in its
   `metadata_extensions` or its `edition_binding`, and that `verify_source_card_binding` still passes with
   zero additional writes. Since a no-status edition's binding is byte-identical in shape to what the
   pre-change code would have produced (the key literally never appears), this is the correct proof for
   "legacy editions verify unbackfilled" even without a pre-existing on-disk fixture captured before this
   commit.

5. **Public accessors are two separate methods**, `load_edition_content` and `get_extraction_status`,
   rather than one combined accessor — the plan's AC and test list ("a public accessor for rendition
   bytes", "a public accessor for the recorded status") describes them as two distinct capabilities, and
   `get_extraction_status` needs to be callable without paying for a content read.

6. ~~`assertion_rollout.py`'s `registry.ingest()` call site was left untouched~~ — **superseded by FIX-4
   below.** The original reasoning (historical cards predating the field can't honestly supply one) was
   right but incomplete: it missed that *some* historical cards **do** already carry a recorded
   `extraction_status` in their front matter (written by `source_cards.py` after this change shipped, or
   any card ingested going forward). A recorded value is authoritative provenance, not a guess — omitting
   it was itself a gap, not a deliberate scope exclusion. Fixed; see FIX-4.

## Adversarial review round (gpt-5.6-terra cross-model gate) — 6 fixes

A cross-model review after the initial M1 pass found 6 real defects, all fixed in this same session
and each mutation-verified (guard reverted → target test fails; guard restored → test passes again;
`__pycache__` cleared + `PYTHONDONTWRITEBYTECODE=1` on every iteration per this repo's documented
false-green hazard).

- **FIX-1 (sibling-parameter bypass).** `ingest()`'s out-of-vocabulary check only looked at the explicit
  `extraction_status` parameter, not the merged value actually persisted — a caller could smuggle a bad
  status in via `metadata_extensions={"extraction_status": "bogus"}` and get an *uncaught*
  `RegistryIntegrityError` out of `_provenance_record` instead of the typed `RegistryImportResult` every
  other public `ingest()` caller expects. Fixed by computing `merged_extraction_status` (explicit param
  wins, falling back to `metadata_extensions.get(...)` — same precedence the edition record construction
  already used) and validating *that* value early. Mutation-verified:
  `test_sibling_metadata_extensions_cannot_bypass_status_validation` fails with an uncaught
  `RegistryIntegrityError` when reverted to param-only validation; passes restored.

- **FIX-2 (unhashable persisted value).** `_extraction_status` did `value not in frozenset` without a
  type check first; a persisted YAML list/dict is unhashable and raised a raw `TypeError`, not
  `RegistryIntegrityError`. Fixed with an `isinstance(value, str)` short-circuit before the membership
  test. Mutation-verified: `test_unhashable_persisted_status_raises_integrity_error_not_typeerror` raises
  bare `TypeError` when the isinstance check is dropped; raises `RegistryIntegrityError` restored.

- **FIX-3 (fabricated fidelity reaching the ledger — the most important behavioral fix).**
  `source_cards.py`'s `ingest_source` call site unconditionally passed `eff_extraction_status` to the
  registry. But when a caller supplies an *unrecognized* override, `eff_extraction_status` fails open to
  the *derived* value (existing, unchanged, out-of-scope behavior) — so an unrecognized override would
  have persisted a fabricated `full_text`/`locator_only` guess into `edition_binding_sha256` itself, worse
  than before this milestone (previously a bad override only ever reached source-card front matter, never
  the provenance digest). Fixed by tracking `extraction_status_is_authoritative` (true when no override
  was given, or the override was recognized; false only on the fail-open branch) and passing
  `extraction_status=eff_extraction_status if extraction_status_is_authoritative else None` — corrected
  the stale comment claiming the value was always authoritative. `ingest_source`'s own front-matter
  fail-open behavior and its blessing test (`tests/test_source_cards_extraction_status.py:90`) are
  untouched, per instruction. Mutation-verified:
  `test_ingest_source_unrecognized_override_records_no_status_in_registry` asserts
  `get_extraction_status(...) is None` after an unrecognized override; reverting to unconditional
  pass-through makes it assert `'full_text' is None` instead (fails).

- **FIX-4 (assertion_rollout omitted a recorded status it had).** `_ingest_run_source_cards` loaded each
  historical card's metadata but never forwarded `metadata.get("extraction_status")` to `registry.ingest`
  even when the card recorded one. Fixed: pass the recorded value through when it's a string, `None`
  otherwise (cards genuinely predating the field still pass nothing — the "never infer" decision holds).
  Added `test_backfill_passes_recorded_extraction_status_when_present` and
  `test_backfill_records_no_status_when_historical_card_lacks_one` to `test_assertion_rollout.py`.
  Mutation-verified: dropping the `extraction_status=` kwarg on the `registry.ingest()` call makes the
  "present" test fail (`assert None == 'full_text'`); restored, passes.

- **FIX-5 (vacuous legacy-edition test — the plan's sharpest risk had fake proof).**
  `test_legacy_edition_still_verifies_unbackfilled` built its "legacy" record by calling the *changed*
  `ingest()`, so it could never fail even if `_edition_binding` started including `extraction_status`
  unconditionally (e.g. as `null`) — both sides of the comparison would drift together. Replaced with a
  frozen, checked-in fixture: `tests/fixtures/assertion_ledger/legacy_edition/{edition.yaml,
  provenance.yaml, content.bin}`, hand-authored (content/hashes verified independently via a one-off
  script, `edition_binding`/`edition_binding_sha256` computed by hand against the *current*
  `_edition_binding` shape with the key genuinely absent — not generated by calling `ingest()`). The test
  copies these frozen files directly into the registry's on-disk layout and calls
  `verify_source_card_binding` against them. Mutation-verified: making `_edition_binding`'s inclusion
  unconditional (`binding["extraction_status"] = extraction_status`, no `if ... is not None` guard) makes
  this test fail with "source edition immutable provenance metadata mismatch"; conditional inclusion
  restored, passes.

- **FIX-6 (test gaps + tightened the pre-existing tamper test).** Added the four tests named above under
  FIX-1/2/3/4. Also fixed `test_tampered_persisted_extraction_status_raises_integrity_error`: the original
  version only tampered the *provenance* file's `edition_binding.extraction_status`, so it would have
  raised via the generic stored-vs-recomputed binding mismatch even with the tri-state guard entirely
  removed (a valid-but-wrong value on one side, untouched on the other, is enough to trip that check on
  its own). Rewrote it to tamper the **edition's** `metadata_extensions.extraction_status` to an
  out-of-vocabulary value and call `verify_source_card_binding` (which loads the edition first —
  `_load_edition` calls `_edition_binding` before the provenance comparison is ever reached, so the guard
  fires first). Mutation-verified the isolation itself: with the guard entirely disabled, this specific
  test now fails a `match="tri-state"` assertion (it still raises `RegistryIntegrityError`, but from a
  *different* check — the caller-supplied-edition-changed comparison — with a different message), proving
  the passing case is genuinely pinned to the tri-state guard and not just "any raise." Added a sibling
  test, `test_tampered_provenance_extraction_status_mismatch_still_raises`, preserving the original
  provenance-only-tamper scenario as a (separately valid, non-vacuous) generic tamper-evidence check.

## Nothing escalated

No destructive action, backfill, or schema migration was needed or considered. No blockers hit in either
round.

---

# M2 implementation notes — Reuse path rehydrates and reused-edition candidates promote

## Change summary

`_existing_edition_reuse` (`external_research_resolution.py:683`) now populates `content`/`extraction_status`
from `AssertionRegistry.load_edition_content`/`get_extraction_status` (M1) instead of always leaving both
`None`. `_finish_passage_resolved`'s `7e2c1e1` guard (`:948`, now `:958` after the doc-comment update) needed
**no logic change** — it already falls through to real promotion once both fields are non-`None`, and it
still quarantines when either is `None` (no recorded status, or a caught `RegistryIntegrityError`). Only its
comment was rewritten to describe the new fall-through instead of the old always-`None` state. `bound.content`
is a `str` field (matching the fresh-acquisition path's `extraction.text`), so the registry's raw `bytes` are
decoded `utf-8`/`errors="replace"` at the rehydration site — the same lossy-but-deterministic decode
`AssertionRegistry.ingest` itself already applies internally when building `raw_text` from arbitrary bytes,
not a new decoding policy.

## Deviations / conservative choices

1. **Bytes-vs-str bug caught by the test, not by inspection.** My first pass rehydrated `content` directly
   from `load_edition_content`'s `bytes` return without decoding. It compiled and the "no recorded status"
   half of the regression test passed, but the new "recorded status promotes" half failed with
   `default_promote` swallowing a `str`/`bytes` mismatch inside `source_cards.ingest_source` into the
   generic `promotion_failed` error path (`default_promote`'s broad `except Exception`). Traced it by calling
   `default_promote` directly, outside the swallowing `try/except`, against a hand-built `PromotionRequest` —
   confirmed `_SourceOutcome.content: str | None` is a `str` field. Fixed by decoding at the rehydration site.
   Recorded here since the swallowed exception gave no signal in the receipt or logs; anyone touching
   `default_promote`'s error handling later should know it can mask type mismatches, not just registry
   failures.

2. **`RegistryIntegrityError` handling caught by only the two named M1 accessors, not `find_exact_passages`.**
   Discovered while building a corrupt-edition test: `AssertionRegistry._load_edition` (which
   `find_exact_passages`, `load_edition_content`, AND `get_extraction_status` all route through) already
   validates content hash, provenance binding, and the extraction-status tri-state on *every* load. So any
   on-disk corruption of an edition — a bad content hash, a tampered `extraction_status` — makes the
   **existing, unguarded** `find_exact_passages` call at the top of `_existing_edition_reuse` (called before
   either M1 accessor is ever reached) raise first. That call site predates M2 and sits outside this
   milestone's stated scope (`_existing_edition_reuse` / `_finish_passage_resolved` only). I read the plan's
   invariant 5 ("A RegistryIntegrityError from either accessor must not crash the resolver") as scoped to
   those two accessors as named, and did not expand the guard to wrap `find_exact_passages` — doing so would
   touch a call site used in three other places in this module (`_resolve_via_selector_hint`,
   `_resolve_candidate_impl` twice) with its own, different fail-closed semantics, which is a larger and
   differently-shaped change than "populate two fields from two accessors." Flagging this as a real,
   currently-unreached-in-practice gap for a future pass: today, corrupting an edition on disk crashes the
   resolver via `find_exact_passages`, not via the two M1 accessors this milestone guards. The regression
   test for invariant 5 (`test_reused_edition_with_integrity_error_quarantines_instead_of_crashing`) therefore
   uses a registry double (subclasses `AssertionRegistry`, overrides only `get_extraction_status` to raise)
   rather than an on-disk tamper, to isolate the specific catch this milestone adds from the separate,
   unresolved reachability question — documented in the test's own docstring so it isn't mistaken for full
   coverage of "any corrupt edition."

## Mutation verification (both new guards)

Ran with `find . -name __pycache__ -type d -exec rm -rf {} +` + `PYTHONDONTWRITEBYTECODE=1` before **every**
iteration, per the repo's documented false-green hazard.

1. **Rehydration guard** (recorded-status half of
   `test_reused_edition_with_no_content_quarantines_instead_of_crashing`): reverted `_existing_edition_reuse`
   to leave `content`/`extraction_status` unset (old behavior) → `cand_recorded` assertion
   (`recorded_outcome["outcome"] == "completed"`) failed with `quarantined` → confirmed the test actually
   exercises the new rehydration path, not a vacuous pass. Restored; full file re-verified green (33 passed).
2. **RegistryIntegrityError catch** (`test_reused_edition_with_integrity_error_quarantines_instead_of_crashing`):
   removed the `try/except RegistryIntegrityError` around the two accessor calls → the simulated error
   propagated uncaught through `resolve_source` → `stage()` → the test itself, failing with an unhandled
   `RegistryIntegrityError` instead of a quarantined outcome. Restored; full file re-verified green (33 passed).

## Nothing escalated

No destructive action, backfill, or schema migration was needed or considered. No blockers hit. The
`find_exact_passages`-crashes-first gap above is flagged, not fixed — it is a pre-existing condition outside
M2's stated scope boundary, not a regression this milestone introduced. **Superseded by FIX-D below**: the
cross-model adversarial review asked for exactly this gap to be closed, so it now IS fixed, not just flagged.

---

# M2 hardening — cross-model adversarial review fixes (gpt-5.6-terra + operator verification)

Four defects found post-implementation, all fixed in this session, none committed (per instruction). All in
`src/research_foundry/services/external_research_resolution.py` + `tests/integration/test_external_research_resolution.py`.

## FIX-A (BLOCKING) — fresh-acquisition ingest never recorded a status

**Defect**: `_resolve_source_impl`'s two `self._registry.ingest(...)` calls (edition ingest + per-quote
ingest) never passed `extraction_status=`, despite `extraction = extract_bytes(...)` computing one a few
lines above and using it for the in-memory `_SourceOutcome`. Every ERI-acquired edition therefore persisted
NO status, so M2's own rehydration (`get_extraction_status` → `None`) always quarantined on `--resume` —
inert for exactly the journey the plan targets ("most of the --resume population").

**Fix**: pass `extraction_status=extraction.status` at both call sites (`:~811`, `:~838`). `extraction.status`
is `extract_bytes`'s own authoritative tri-state output — nothing inferred, nothing new computed.

**Test** (FIX-B pairing): new `test_fresh_acquire_then_resume_promotes_reused_candidate` — stage 1 freshly
acquires through the real resolver (real `extract_bytes` + real `ingest`), stage 2 is a SEPARATE resolver
instance (simulating `--resume`) with no acquire content for the same source, reusing the edition read-only
and promoting. This is the actual end-to-end journey, not a direct-registry seed.

**Mutation-verify**: removed both `extraction_status=extraction.status,` lines →
`test_fresh_acquire_then_resume_promotes_reused_candidate` failed (`quarantined` not `completed`) at the
stage-2 assertion. Restored → full file green.

## FIX-B — test masking (why FIX-A wasn't caught)

The original `test_reused_edition_with_no_content_quarantines_instead_of_crashing` seeded its "no recorded
status" half via a resolver-fresh-acquisition call (`_stage` through `seed_resolver`). Once FIX-A landed, that
seed path ALSO records a status (since it's now the same code path FIX-A patched) — so the test needed
updating to seed the genuinely-unrecorded half directly via `AssertionRegistry.ingest(...)` with no
`extraction_status` argument (a legacy-edition stand-in), while the new end-to-end test (FIX-A section above)
covers the promoting half through the real resolver-to-resolver journey. Both are kept: the updated test
isolates the mechanism (direct seed, cheap, precise); the new one proves the real journey.

## FIX-C (HIGH) — arbitrary edition pick under ambiguity could now promote

**Defect**: `_existing_edition_reuse` took `matches[0][0]` without checking whether `matches` spans more than
one DISTINCT `source_edition_id`. Pre-M2 this was inert (content always `None` → always quarantined regardless
of which edition was picked). Post-FIX-A, with recorded statuses now common, an arbitrary manifest-order pick
among genuinely ambiguous editions could PROMOTE — staging evidence from possibly the wrong edition.

**Fix**: compute `distinct_edition_ids = {m[0].get("source_edition_id") for m in matches}`; when
`len(distinct_edition_ids) > 1`, skip rehydration entirely (`content`/`extraction_status` stay `None`), so the
existing `_finish_passage_resolved` None-content guard quarantines it (`verification_failed`, unchanged — no
new reason code, per the owner's explicit instruction and OQ-1's resolution).

**Test**: new `test_reused_edition_matching_multiple_distinct_editions_quarantines_not_promotes` — seeds TWO
editions with different overall content (hence different `source_edition_id`s, since editions are
content-addressed) that each independently contain a passage byte-identical to a shared quote, BOTH carrying a
recorded status (the exact post-FIX-A live condition). Asserts the candidate still quarantines.

**Mutation-verify**: changed `if not ambiguous_edition and isinstance(edition_id, str):` to
`if isinstance(edition_id, str):` → the new test failed (`completed` not `quarantined`) — confirmed via
exact node-id run (`-k ambiguous` is UNSAFE here: it also collects the pre-existing, unrelated
`test_multiple_match_quarantines_citation_ambiguous`, and a careless keyword-filtered run can silently report
"1 passed" against the wrong test — always target the specific test by its full node id when mutation-verifying
a check whose name shares a common substring with other tests). Restored → full file green.

## FIX-D (HIGH) — the integrity catch sat behind an unguarded, crash-first call

**Defect**: `find_exact_passages` (called at the very top of `_existing_edition_reuse`, and again inside the
per-quote passage-status loop) was unguarded, even though it routes through `AssertionRegistry._load_edition`,
which already validates content hash, provenance binding, AND the extraction-status tri-state on every read.
Real on-disk corruption therefore raised THERE first, before either M1 accessor's own `try/except` was ever
reached — aborting the whole `stage()` call instead of quarantining the affected source. Separately,
`AssertionRegistry._read_regular_file` re-raises a raw `FileNotFoundError` (not wrapped in
`RegistryIntegrityError`) on a missing/concurrently-deleted file, which the prior `except RegistryIntegrityError`
alone would not have caught either.

**Fix**: widened every registry call in `_existing_edition_reuse` (both `find_exact_passages` call sites, plus
the two M1 accessors) to catch `(RegistryIntegrityError, OSError)`. Per-quote lookup failure is treated as "no
match for this quote" (try the next quote). If EVERY quote's lookup fails or finds nothing AND at least one
failed with an integrity/OS error (tracked via a `lookup_failed` flag), `_existing_edition_reuse` now returns a
QUARANTINED source outcome with reason code `edition_binding_conflict` — an EXISTING, previously-unused member
of `SOURCE_REASON_CODES` (not a new one; `verification_failed` is a CANDIDATE-family code and cannot legally be
used at the source level — `_source_quarantine` asserts family membership) — instead of silently returning
`None` and letting `_resolve_source_impl` fall through to a fresh network acquisition attempt for a source
whose existing-edition state could not even be inspected. A sibling quote's passage-status classification
failing the same way now falls back to `"not_found"` rather than propagating.

**Test**: rewrote the FIX-D regression test as `test_reused_edition_with_corrupt_content_quarantines_instead_of_crashing`,
using a REAL on-disk `content.bin` tamper (not a registry double, per the explicit instruction) — confirms via
a direct `find_exact_passages` call that the tamper trips the registry's OWN integrity check, then asserts the
SOURCE outcome quarantines (`edition_binding_conflict`, checked via a direct `resolve_source` call) and the
dependent candidate quarantines in turn (`citation_unresolved`, the ordinary no-`source_resolved`-outcome path).
The prior registry-double test (isolating just the M1-accessor catch specifically) is superseded by this one,
which now reaches the SAME guard via the real corruption path FIX-D closes — no residual untested case remains
for on-disk corruption; a residual gap does remain for corruption that manifests ONLY inside `load_edition_content`/
`get_extraction_status` without `find_exact_passages` itself having already failed on the same edition, which
per `_load_edition`'s shared validation appears structurally unreachable today (both routes converge on the
same check) — noted, not additionally tested, since constructing it would require mocking rather than a real
corruption.

**Mutation-verify**: removed the `try/except` around the outer `find_exact_passages` call → the test failed
with an unhandled `RegistryIntegrityError` propagating all the way through `_stage()` (confirmed via traceback
in the test failure). Restored → full file green.

## Final validation (this session)

```
find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD/src:$PWD/tests /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest tests/integration/test_external_research_resolution.py tests/unit/test_assertion_registry.py -q
```

**56 passed** (35 integration + ... unit — combined run; up from the pre-fix 33 integration-only baseline: +1
updated test's internal reshaping, +3 new tests: `test_fresh_acquire_then_resume_promotes_reused_candidate`,
`test_reused_edition_matching_multiple_distinct_editions_quarantines_not_promotes`, and the FIX-D rewrite of
the corrupt-edition test). Not committed, not pushed, per instruction.

## M3 — live checkpoint re-validation (orchestrator, 2026-07-31)

### What was run

Packet dir resolved via OQ-2 (operator-supplied): `~/Downloads/knitwit-s1/packet`
(digest `35d50aeaab09b7b6…` — matches the plan's `35d50aea…`).

No pending checkpoint for this packet/run identity exists anywhere on disk (searched the
whole ERI store; all 11 stored receipts belong to other packets/runs). The plan's premise of a
resumable `--run` checkpoint is therefore not satisfiable as written — the equivalent, and
stronger, validation is a fresh import through the new code, which exercises fresh-acquire and
then reuse.

Two real (non-dry) imports of the same packet against the shared `default` workspace:
1. `--run rf_run_20260731_knitwit_s1_rights_evidence` — the plan's named target.
2. `--run rf_run_20260731_knitwit_s1_reuse_validation` — a second identity, so every source is
   now edition-reuse rather than fresh acquisition. This is the A/B that isolates the reuse path.

Note: `--dry-run` is useless as evidence here. `_resolve_source_impl` short-circuits to a
hardcoded `locator_only` floor before acquisition in dry-run mode, so a dry run reports
quarantines regardless of whether the fix works.

### Result — identical in both runs

`38 actions: 16 completed (all `source_resolved`), 22 quarantined`
Quarantine reasons: 12 `citation_unresolved`, 4 `verification_failed`, 3 `source_unavailable`,
3 `citation_ambiguous`. Zero candidates completed at `passage_resolved`.

### What IS proven live

- **The write path works.** 16 of 16 freshly-acquired editions now persist
  `extraction_status: full_text`, and it appears in BOTH the edition record and the provenance
  `edition_binding` — i.e. M1's conditional binding inclusion and M2's FIX-A both function
  against the real ledger, not just in tests.
- **Legacy editions are untouched and still verify.** 487 pre-existing edition records
  (captured 2026-07-17 and 2026-07-29) carry no status, were not rewritten, and the imports ran
  over them without a single `RegistryIntegrityError`.

### What is NOT proven, and why (the finding to escalate)

The plan's M3 AC — "the named candidates re-resolve `passage_resolved` and have run source-card
artifacts on disk" — is **NOT met, and cannot be met for this packet without a backfill.**

Ledger census: 503 edition records total; exactly 16 carry a recorded extraction status — the 16
created today. The other 487 predate this change.

The 4 `verification_failed` candidates are precisely the plan's target population, and the
mechanism is now fully understood:
- Their quotes DO match, which is why they reach `_finish_passage_resolved` at all — but they
  match passages stored on a **2026-07-29 legacy edition**, not on anything acquired today.
- That legacy edition has no recorded extraction status, and per the plan's explicit decision
  nothing may infer one and nothing may be backfilled.
- Editions are content-addressed and immutable, so re-acquiring identical content yields the
  SAME edition id and early-returns at `assertion_registry.py:425` — it can never gain a status.

Therefore these candidates fail closed **permanently** absent a backfill. That is correct,
intended behavior (fail-closed on genuinely unknown fidelity), not a defect — but it means the
fix is strictly **forward-looking**: it repairs promotion for editions ingested from now on, and
does not recover any edition already on disk.

Separately, the 12 `citation_unresolved` are a data-freshness issue unrelated to this plan: the
packet's quotes no longer exact-match the live web content for freshly-acquired sources.

Per the plan's own Mode-D rule ("any rewrite, backfill, or migration of edition records already
on disk … halts for explicit human approval … if a milestone concludes it does, that conclusion
is the thing to escalate"), this is escalated rather than acted on.
