# source-metadata-propagation — Execution Ledger

> Purpose: this is the execution ledger referenced by the implementation plan's "Execution ledger"
> section (`docs/project_plans/implementation_plans/infrastructure/source-metadata-propagation-v1.md`).
> Deviations are logged here with rationale and reviewed at each milestone boundary rather than halted
> on. OQ-1..OQ-4 resolutions are recorded here at their respective milestone's entry, and Mode-D approval
> records (M3, M4) are logged here when obtained.

---

## 2026-08-02 — Run setup (`/dev:execute-plan`)

**Worktree**: `.claude/worktrees/source-metadata-propagation`, branch `feat/source-metadata-propagation`,
based on local `main` tip `c415da0` (main advanced from `ac585f3` → `c415da0` mid-session via concurrent
activity; the worktree is based on the later tip, which is the correct PR base). Squash-merge target:
`main` — authorized in the originating prompt ("Operate in worktree, squash to main when done").

**Test harness in the worktree**: the worktree has no own `.venv`. Commands run as
`PYTHONPATH=<wt>/src <primary>/.venv/bin/python -m pytest ...`. Pre-change baseline for
`tests/test_schema_validation.py` + `tests/test_governance_adversarial.py` is **exit 0** (288 tests).
This repo's pytest prints no "N passed" summary line — the exit code is the signal.

### MODE-D APPROVAL RECORD — M3 and M4, both PRE-AUTHORIZED

The operator was asked explicitly, at run start and before any implementer was dispatched, how to handle
the two Mode-D halts declared by the plan (`SMP-3.0-HALT`, `SMP-4.0-HALT`). The recorded answer was
**"Pre-authorize both now"**, with the stated understanding that all four milestones run end-to-end and
review happens at the PR rather than at each boundary.

| Halt | Boundary | Status | Basis |
|---|---|---|---|
| `SMP-3.0-HALT` | Authorization-boundary change — the structural provenance guard (`SMP-3.2B`) plus the defence-in-depth name guards | **APPROVED** 2026-08-02 | Operator answer at run start, recorded here per the plan's Mode-D note |
| `SMP-4.0-HALT` | Catalog schema migration — catalog columns and sqlite row builders | **APPROVED** 2026-08-02 | Operator answer at run start, recorded here per the plan's Mode-D note |

`BLOCKER-M3-1` and `BLOCKER-M4-1` in the M3/M4 progress files are resolved by this record. Approval
covers **landing the changes as specified in the plan**; it is not a licence to widen scope. Any
Mode-D surface the plan does *not* name (auth, payments, data deletion, secret rotation,
infrastructure) still halts.

### Data-plane handling for the M4 counted sweep (`SMP-4.7`)

`runs/` is the **private** data plane (only `runs/.gitkeep` is tracked in this repo), so a fresh
worktree has an empty `runs/` and the plan's `for r in runs/*pediatric_cds*/` sweep would match zero
bundles — which the plan already flags as the vacuous-pass risk. Per operator decision, the 7 live
bundles are **symlinked into the worktree's `runs/`** and excluded via the worktree's
`info/exclude`, so:

- the sweep runs live against the real 7 bundles inside the worktree, where its gate belongs;
- `git status` in the worktree stays clean and no symlink can be committed;
- `ls -d <wt>/runs/*pediatric_cds*/ | wc -l` == **7** (verified at setup).

`rf verify` appends a timestamped event to `telemetry/run_trace.jsonl` in each bundle — expected, and
called out as a named risk in the plan; it is why `SMP-1.5` must compare in-process `export_run()`
output with the telemetry timeline `del`'d, and must not use `rf verify`.

### Operational boundary (operator instruction, this run)

The **remote rf instance on the nuc** (`10.42.10.76:7432`) is primary for anything lasting or
operational; local runs are dev/test only. Consequences for this run:

- The `SMP-4.7` counted sweep is a **dev/test verification**, so it runs locally, matching the plan's
  AC command (`./.venv/bin/rf verify`). No lasting artifact is produced on the local plane.
- This plan changes `export_service.py`, `catalog_service.py`, `governance.py`, and schemas — all
  served by the node's `research-foundry-api.service`. The node deploys by pulling from **origin**, so
  **push to origin is part of closeout**, followed by a redeploy. Committed-but-unpushed here would
  silently leave the node serving stale code.

### Routing decisions (`delegation-router`)

Resolved once at the plan gate. The plan's `routing_constraints` make M1–M3 MUST-stay claude-primary;
all milestone gates and both karen passes are MUST-stay classes (`verdict` / `council-review`) that
route to `claude` unconditionally, so no resolver decision was required for them.

| Leg | Routed to | Basis |
|---|---|---|
| M1, M2, M3 implementers | `claude` (Sonnet 5, `xhigh`) | Plan `routing_constraints`: each carries a governance control or the deal-killer refutation. Capability bar — must hold multi-file schema invariants in one pass. |
| M1/M2/M3/M4 milestone gates | `claude` | MUST-stay (`verdict`); `task-completion-validator` for the validator lens, `council-review` for the security lens. |
| M4 karen + end-of-feature karen | `claude` (Opus) | MUST-stay (`verdict`). |
| **M4 implementer** | `claude` (Sonnet 5, `xhigh`) — **deviation** | See below. |

**Deviation — M4 was not offloaded despite being offload-eligible.** The resolver did return a valid
ICA route for M4 (`chosen: ica`, `agent_type_id: ica-executor`, fallback → `claude`), and the plan
marks M4's plumbing offload-eligible with permission to "drop to economy class". It is being kept
claude-primary anyway. Rationale: offload-eligible is a *permission, not an obligation*, and M4 is the
plan's only C3 milestone — it edits a 2242-line file the plan flags with a 2× multiplier (H7), performs
the catalog schema migration, and owns the tri-state coverage semantics that are the honesty control
for the whole no-backfill decision. It also carries its own karen pass. The expected re-gate and
coordination cost on that surface exceeds the token saving. ICA remains the recorded fallback.

### Batching correction (deviation from the progress files' `parallelization`)

M1's `batch_2` lists `["SMP-1.2", "SMP-1.3", "SMP-1.6"]` as parallel, but all three edit
`src/research_foundry/services/source_cards.py`. Parallel agents on one file is the hard
parallel-safety violation in `dev-execution`, so **batch_2 is collapsed to a single agent** owning all
three (plus `SMP-1.7`, its derivation test). The same collapse is applied wherever a declared batch
shares a file — checked per milestone at dispatch, notably M3 `batch_2` (`SMP-3.1`/`SMP-3.2` both edit
`governance.py`; `SMP-3.2B` edits the schema and stays parallel) and M4 `batch_3`
(`SMP-4.2`/`SMP-4.3` both edit `catalog_service.py`).

## M1 entry — OQ-1 / OQ-4 resolution

**OQ-1 — which search-router providers actually return DOI / citation counts / structured authors
today?** None of them. Enumerated the full provider registry
(`src/research_foundry/services/search_router/providers/__init__.py:12-17` imports exactly six
concrete providers: `brave.py`, `exa.py`, `firecrawl.py`, `github.py`, `jina.py`, `searxng.py`) and
grepped every one for `doi|author|citation|publisher` — zero matches outside unrelated substrings
(`router.py`'s own `citation_coverage` metric name, which is a ranking statistic, not a bibliographic
field). None of the six is a bibliographic/citation API in the first place (Brave/Exa/SearXNG =
general web search, Firecrawl/Jina = markdown extractors, GitHub = repo search) — there is no
Semantic Scholar / CrossRef / OpenAlex / PubMed provider registered at all. The two normalized result
dataclasses providers populate, `SearchHit` and `ExtractedDoc`
(`providers/base.py:57-108`), carry no author/DOI/citation fields; the only near-miss is GitHub's
`raw={"stars": item.get("stargazers_count")}` (`github.py:52`), which is discarded — `SearchHit.raw`
is never read by `to_dict()` or by either call site. Confirmed both real call sites into source
capture (`router.py:721-732`'s per-hit card creation and `router.py:911-922`'s `extract_urls`) pass
only `locator`/`run_id`/`source_type`/`title`/`content`/`extra_limitations` to `create_source_card` —
no provider metadata field exists to thread through because none of the six providers produce one.
**Consequence for SMP-1.2**: `ingest_source()`'s new `authors`/`doi`/`publisher`/`version` kwargs are
added as a capability with no current live producer; every existing call site (both in `router.py`)
is unaffected and continues to omit them, defaulting to the pre-change empty shape. Wiring a real
producer is out of scope for this milestone (would require standing up a new bibliographic provider,
which is a Phase-C-adjacent scope expansion, not M1).

**OQ-4 — is `trust.source_rank` derivation deterministic from `source_type` + rights/access basis, or
does it need a capture-time model call?** Deterministic from `source_type` alone; no model call is
used or needed. `rights_summary.access_basis` — the other candidate input the OQ names — is `unknown`
on every real capture today by construction: `services/rights_triage.py`'s
`_classify_capture_rights()` (`rights_triage.py:75-87`) always returns
`rights_backfill.all_unknown_rights_summary()` because "no real classification signal exists at bare
ingest time" (its own docstring, `rights_triage.py:76-84`) — there is no `rights_record` for the
mirror to link to at capture time. Folding a field that is always `"unknown"` into the derivation
today would be a dead, never-exercised branch. The mapping implemented in the new
`services/source_rank.py::derive_source_rank()` is therefore a pure function of `source_type` only —
a closed table over the schema's 10-value `source.source_type` enum
(`schemas/source_card.schema.yaml:28-39`): `official_doc`/`standard`/`paper`/`repo` → `primary`;
`news`/`blog` → `secondary`; `book` → `tertiary`; `personal_note`/`internal_doc`/`other` → `unknown`
(source_type alone gives no reliable signal for these three — kept `unknown` rather than guessed, per
the plan's rubric). Widening the mapping to consult `access_basis` is a documented seam in that
module's docstring for if/when a real capture-time rights classifier lands, not something this
milestone needed to build.

## M1 security gate fix — SMP-1.4 redaction gap (post-review, 2026-08-02)

**Finding**: the M1 security gate returned `CHANGES_REQUESTED` against the initial SMP-1.4 hydration
(`export_service.py:656-670` at review time). `authors`/`doi`/`publisher`/`version` were hydrated
unconditionally, bypassing the `effective_rank > threshold_rank` redaction check that `summary`/`quote`
already use. Concrete exploit: a `client_sensitive` card whose `publisher` carries sensitive text
(reachable via `agent_job_service.py:688`'s `create_source_card(**merged)` from arbitrary MCP
`tool_input` — a live path) would export at a lower threshold with `summary`/`quote` correctly
`REDACTION_MARKER`'d while `publisher`/`authors`/`doi`/`version` shipped verbatim — an
untrusted-input-class leak this milestone's `gate_lens_reason: untrusted-input` exists to catch.

**Fix**: all four fields now go through the identical `REDACTION_MARKER if redacted else <value>`
ternary `summary`/`quote` use (same marker, same `effective_rank > threshold_rank` gate, no new
convention). `authors` (a list) collapses to the single marker string when redacted — matching
summary/quote's whole-field swap — rather than a structure-preserving per-element redaction (a
third convention this milestone did not need to invent). The gate remains a pure function of
card/point sensitivity + the caller-supplied threshold; verified via a second in-process
`export_run()` call that recomputability still holds.

**Follow-up observation — logged, NOT fixed (explicitly out of scope per the gate's own scope
discipline)**: `title`/`source_type`/`url` in the same `_resolve_source()` (`export_service.py:652-654`)
remain unconditionally unredacted — the identical class of gap, on fields that are just as reachable
from the same untrusted `create_source_card(**merged)` MCP path (`agent_job_service.py:688`). This is a
pre-existing gap that predates SMP-1.4 and is wider than M1's scope (it would also need to weigh
`title`/`url` against consumers that assume they're always present for citation display). Recorded here
as a candidate follow-up for a future milestone or a dedicated fix, not silently patched by ambush
alongside this task's four fields.

**Re-validation note**: fixing the redaction gap required adjusting `tests/test_export_recomputability.py`
(SMP-1.5's already-landed file, uncommitted in this shared worktree) — its existing
`test_export_run_hydrates_source_metadata_at_claim_level` used the export default threshold (`public`)
against a `personal`-sensitivity fixture card, which the corrected gate now (correctly) redacts; the test's
own purpose is proving hydration, not redaction, so it now passes an explicit matching
`sensitivity_threshold="personal"`. Added `test_export_run_redacts_source_metadata_above_threshold` in the
same file to prove the fix is load-bearing (client_sensitive card, work_sensitive threshold, asserts exact
`REDACTION_MARKER` equality on all four fields plus summary/quote, plus a second `export_run()` call to
confirm recomputability survives the gate). Also observed one unrelated, pre-existing/concurrent-leg
failure: `tests/test_schema_validation.py::test_registry_lists_all_schemas` (58 vs 57 expected schema
names) — caused by another leg's untracked `schemas/source_attribution.schema.yaml` (M2 scope) landing in
this shared worktree without yet updating `EXPECTED_SCHEMA_NAMES`; confirmed stable and untouched by this
task's diff, not fixed here (out of scope, belongs to whichever leg owns that schema file).

## M1 second security-gate finding — `authors` array-type contract violation (2026-08-02)

**Finding**: the first fix's `authors` redaction (bare `REDACTION_MARKER` string) violated
`rf-run-export-schema.json`'s `RFResolvedSource.authors` (`type: ["array","null"]`) -- confirmed via
direct `jsonschema` validation (`'[redacted:sensitivity]' is not of type 'array', 'null'`). `doi`/
`publisher`/`version` were unaffected (`["string","null"]`, marker fits).

**Fix**: `authors` now redacts to `[REDACTION_MARKER]` (single-element list) — `export_service.py:687`
— preserving the declared array type, still the one canonical marker, still a whole-field swap (not
per-name redaction). Explicitly NOT `None`: `null` already means absent/dangling/pre-migration, and
collapsing withheld into that value would defeat the tri-state absent/withheld/not-yet-assessed
distinction this plan exists to preserve. `docs/dev/architecture/rf-run-export-schema.json`'s four
provider-metadata descriptions (`authors`/`doi`/`publisher`/`version`) were corrected to state they ARE
sensitivity-gated (removing the now-false "never redacted" claim) and describe the redacted
representation; no `type` changed.

**New test**: `tests/test_schema_validation.py::test_export_run_with_redacted_source_passes_strict_json_schema_validation`
(plus a new `_build_redacted_export_run` helper) builds a `client_sensitive` card, exports at
`work_sensitive`, and validates the actual redacted payload against the schema via
`jsonschema.Draft7Validator` — mirroring `test_export_run_passes_strict_json_schema_validation`'s
existing pattern rather than hand-rolling a validator. Also strengthened
`tests/test_export_recomputability.py::test_export_run_redacts_source_metadata_above_threshold` to
assert `[REDACTION_MARKER]`/list-type/not-None for `authors`. Verified non-vacuity empirically: reverting
`authors` to the bare-string form makes both new tests fail red (`jsonschema` reports the same type
violation; the plain-equality assert fails).

**Re-validation**: `tests/test_export_recomputability.py tests/test_schema_validation.py
tests/test_source_metadata_capture.py tests/test_source_rank_derivation.py
tests/test_governance_adversarial.py` → exit 1, with **exactly** `test_registry_lists_all_schemas`
failing (the known-unrelated M2 concurrent-leg issue above) and nothing else.

## M4 entry — OQ-2 resolution

**Answer: rebuild-only. There is no ALTER TABLE / Alembic-style versioned-migration chain anywhere in
`catalog_service.py`.** The mechanism is: bump a single integer constant (`SCHEMA_VERSION`,
`catalog_service.py:126`) → on the next connection, `_ensure_schema()` (`catalog_service.py:327-334`)
compares it against the value stored in sqlite's own `PRAGMA user_version` (line 330) and, on any
mismatch, unconditionally drops every catalog table (`_drop_schema()` → `_DROP_STATEMENTS`,
`catalog_service.py:301-308,322-324`) and recreates them empty (`_create_schema()`,
`catalog_service.py:311-319`). Repopulation is a **separate, not-automatic** step — the module's own
docstring says so explicitly: "a mismatch triggers a drop + recreate of the schema (**not** an
automatic re-import — callers re-run `import_all`)" (`catalog_service.py:12-14`). This is precedented,
not a first-time move: the schema-version comment block documents two prior bumps that did exactly
this — v2 added `catalog_report_drafts` and v4 added `catalog_terms` (`catalog_service.py:114-125`),
both landed as "add columns/tables to the DDL + bump the constant + rely on rebuild", with the v2
comment stating the safety argument in the same words this note would otherwise reinvent: "this is
always safe because catalog.db is 100% derived: run items are rebuilt from `export_run()` via
`import_all()`... Neither rebuild path reads anything from the DB itself" (`catalog_service.py:117-121`).

**Line-anchor check — the plan's citations are accurate, not stale.** Verified against current
worktree content:
- `catalog_service.py:557-572` = `_trust_label_of()` (coerces a source card's `trust` object/string to
  the scalar `trust_label` column) — matches.
- `catalog_service.py:850-889` = the first half of `_build_source_rows()` (dedup + per-citation
  sensitivity aggregation for the `source` item type) — matches.
- `catalog_service.py:1341-1349` = the `_delete_run()` + `_insert_rows()` transaction body inside
  `import_run()` — matches.

**Where a new column actually lands (concrete, not hypothetical).** Two independent surfaces, both
additive:
1. **Structured column** (needed only if M4 wants the new attribute filterable in SQL, e.g.
   `WHERE attribution_coverage = 'present'`): add the column to the `CREATE TABLE catalog_items (...)`
   statement in `_DDL` (`catalog_service.py:187-208`), bump `SCHEMA_VERSION` to 5, and populate it via
   `_base_row()` (`catalog_service.py:646-698`, which already takes a fixed kwarg set that maps 1:1 to
   columns) from whichever `_build_*_rows()` function owns the item type (e.g. `_build_source_rows()`,
   `catalog_service.py:850-953`). No `ALTER TABLE` is written or needed — `CREATE TABLE IF NOT EXISTS`
   only fires after the drop, so the "new" table is created with the new column from a clean slate.
2. **Unstructured/nested attribute** (if M4 is fine keeping it query-only via item detail, not a SQL
   `WHERE`): just add it to the `payload` dict passed into `_base_row()` — `payload_json` is a
   schemaless `TEXT NOT NULL` JSON blob (`catalog_service.py:205,696`) and needs **no** DDL change,
   no version bump, at all. The existing `source` row's payload (`title`/`source_type`/`url`/`trust`/
   `usage`/`evidence_points`, `catalog_service.py:915-922`) is exactly this pattern already in use for
   attribution-adjacent data (`trust`).

**Is it additive-safe? Yes for both paths above, with one real gap to close.** Adding a column to
`_DDL` and bumping `SCHEMA_VERSION` is safe by the same argument the v2/v4 bumps already relied on
(100%-derived corpus, nothing unique lives only in the DB) — this directly confirms the plan's
"architectural principle to weigh": the catalog *is* a derived, rebuildable index, so M4's "catalog
schema migration" is materially lower-risk than a true data migration. **However, `_ensure_schema()`
only fires as a side effect of `_connect()`** (`catalog_service.py:344-351`, called by every
write-capable entry point: `search()`, `get_item()`, `stats()`, `import_run()`, `import_all()`, the
CLI, and every `/api/catalog/*` route). That means the drop half of the migration happens *silently
and automatically* the first time anything touches the catalog after the version bump ships — but the
repopulate half does not, and nothing forces it. **M4's implementer must explicitly call, and this
plan's M4 gate must explicitly verify, `rf catalog rebuild` (→ `catalog_service.rebuild()`,
`catalog_service.py:1388-1408`, which does `rebuild_schema()` + `import_all()` +
`reindex_all_drafts()` in one call) after the version bump lands** — there is no other call site that
does this (`grep` confirms `svc.rebuild(paths)` has exactly one caller,
`cli_commands.py:1714`, and no API route wraps it; the two `/api/catalog/import*` routes call
`import_run`/`import_all` only, never `rebuild_schema`).

**Stale-catalog hazard, concretely.** Any deploy that ships a `SCHEMA_VERSION` bump without a
same-deploy `rf catalog rebuild` leaves the catalog **silently empty, not erroring**, for every
write-capable caller (`search`/`get_item`/`stats` all pass through `_connect()` → `_ensure_schema()`,
which drops and recreates empty tables with no signal beyond that). Contrast the read-only KMCP seam
(`query_only_connection()`, `catalog_service.py:411-448`), which deliberately fails closed instead:
it raises `CatalogUnavailable("catalog_schema_stale")` (line 445) on the same version mismatch rather
than auto-migrating. The write-capable path has no equivalent guard. This is the concrete "old rows
persist without the new columns" hazard the plan's OQ-2 wording anticipates, except inverted — old
rows don't persist with stale shape, they vanish outright until an explicit rebuild — and the M4 AC
table's "tri-state coverage surfaced" test should include a case that runs `rf catalog rebuild` (or
`import_all`) post-bump and asserts non-empty results, not just correct tri-state values on an
already-populated catalog.

**Router coupling (Q5) — the router itself is clean; the real allowlist lives one layer down.**
`api/routers/catalog.py` (182 lines, confirmed) has no hardcoded `SELECT`, no Pydantic response model,
and no field allowlist of its own — every handler returns `dict[str, Any]` built by
`stamp(svc.<fn>(...))` (`catalog.py:60-179`), so it will pass through whatever `catalog_service`
returns unmodified. The actual coupling point is in `catalog_service.py` itself:
`search()`'s row-to-dict conversion goes through `_row_to_summary()` (`catalog_service.py:1457-1458`),
which projects onto a fixed tuple `_SUMMARY_COLUMNS` (`catalog_service.py:1439-1454`, 14 named
columns, does not include `payload_json`). A new structured column added per path 1 above will **not**
appear in `search()` results until it is also added to `_SUMMARY_COLUMNS` — a one-line, low-risk fix,
but a real one M4 must not skip, or the new attribute will be query-able by `WHERE` but invisible in
list results. `get_item()` has no such gap: it returns `dict(row)` over every column
(`catalog_service.py:1915`), so item-detail view picks up new columns automatically with zero code
change.

**Unresolved**: none. Every claim above is anchored to a specific line range in the current worktree
content; nothing here rests on the plan's aspirational text.

## SMP-4.2/4.3 entry — two corrections to the OQ-2 entry above, plus the design decision they drove

**Correction 1 — `get_item()` DOES go through `_SUMMARY_COLUMNS`, contrary to this ledger's own OQ-2
note.** That note claimed "`get_item()` has no such gap: it returns `dict(row)` over every column
(`catalog_service.py:1915`)". Line 1915 in the pre-M1 baseline (`git show HEAD~2:...`) is indeed
`dict(row)` literally — but that call is the *second* positional argument to
`require_workspace_scope(identity, dict(row), ...)`, an internal enforcement check, not the value
`get_item()` returns. The actual return is `summary = _row_to_summary(row)` (same allowlist `search()`
uses) with `payload`/`links` merged in afterward. Net effect on this task's design: unchanged — every
field kept in `payload_json` (via the `payload` dict passed to `_base_row`) still surfaces through
`get_item()`'s `payload` key regardless of `_SUMMARY_COLUMNS`, exactly like the pre-existing `url`/
`trust`/`usage` fields already do. But the *reason* it works is different from what was claimed, and a
future task relying on "`get_item()` has no gap" for a field kept OUT of `payload_json` would be wrong
to do so — it does have the same gap `search()` has, just closed here by an unrelated design choice
(payload always ships in the response).

**Correction 2 — `export_service.py`'s resolved-source shape does NOT surface `attribution_summary`,
before OR after the M2 commit (`e9d0a0b`).** `git show e9d0a0b --name-only` confirms M2 touched
`schemas/source_attribution.schema.yaml`, `schemas/source_card.schema.yaml`, `attribution_triage.py`,
`attribution_validation.py`, `cli_commands.py` — never `export_service.py`. `attribution_summary` is
written onto the source-card's own frontmatter (`schemas/source_card.schema.yaml:484-558`) but
`_resolve_source()` (`export_service.py:601-706`) never reads or copies that key onto the per-citation
resolved-source dict the way it already does for `trust`/`usage` (`meta.get("trust")`,
`meta.get("usage")`, copied verbatim). This module's hard invariant ("import via `export_run()` live,
never parse source-card files directly") means `catalog_service.py` genuinely cannot see
`attribution_summary` today — not a gap in this task, a gap one level up, in a file this task is
explicitly forbidden from touching.

**Design decision (SMP-4.2/4.3), given the above**: `_build_source_rows()` reads
`src.get("attribution_summary")` defensively (`.get()`, never a raise, never a raw file read) from the
same per-citation resolved-source dict `trust`/`usage` already come from — the natural, minimal-diff
landing spot if/when `export_service.py` is widened to add
`resolved["attribution_summary"] = meta.get("attribution_summary")` (mirroring the `trust`/`usage`
precedent one line above it). Until that lands, every catalog row's `attribution_count` column is
`NULL` ("not yet assessed") for every source, end to end via `import_run()` — verified honest, not a
bug: `tests/test_catalog_attribution_columns.py::test_import_run_populates_first_party_metadata_columns`
asserts exactly this. The tri-state "assessed, present/absent" paths (`attribution_count == 0` /
`> 0`) are proven directly against `_build_source_rows()` with a hand-built `export_data` dict in the
same test file, so the row-builder's own handling is verified independent of whether the exporter has
been widened yet. **Flag for whoever lands the `export_service.py` widening (M2 follow-up, or SMP-4.4/
4.5's implementer if scope allows): until `attribution_summary` is threaded through `_resolve_source()`,
SMP-4.5's tri-state coverage surface will report "not yet assessed" for 100% of sources, which is
correct-but-useless without that wiring.**

**What shipped**: `SCHEMA_VERSION` 4 → 5. Six new `catalog_items` columns: `doi`, `publisher`,
`source_version`, `authors_json`, `source_rank`, `attribution_count` (all nullable). `source_rank` is
DELIBERATELY separate from the pre-existing `trust_label` column — `trust_label` falls back to a
str-cast of any non-dict `trust` value (legacy data), so a plain-string `trust` would otherwise leak
free text into a field a future caller could mistake for one of `{primary, secondary, tertiary,
unknown}`; `_source_rank_of()` returns `None` in that case instead. `_SUMMARY_COLUMNS` gets
`source_rank`/`attribution_count` (scalar, needed in list results per the coupling note); `doi`/
`publisher`/`source_version`/`authors_json` stay payload-only, matching the `url`/`trust`/`usage`
precedent (confirmed still correct per Correction 1 above). Rollup computation is NOT reimplemented
here — `attribution_summary` is propagated into `payload_json` verbatim, never recomputed, so SMP-4.4/
4.5 own that logic entirely; this task only preserves the NULL-vs-0-vs-positive distinction at
row-build time. `rf catalog rebuild` is required after this lands (module's stated rebuild-only
contract) — not run here, since this task ships no live data, only the schema/row-builder change and
its own synthetic-fixture test suite.

---

## M3 boundary — gate record and a NEW blocking precondition on Phase C

**Gate outcome**: both assigned lenses APPROVED (`gate_lens: [security, validator]`,
`gate_lens_reason: authz-boundary`). The validator lens independently re-ran the mutation rather than
trusting the implementer: removing the record schema's `if/then` turned 6 tests RED, and the schema
restored to a matching MD5. `tests/test_governance_adversarial.py` has **zero removed lines** — the 33
pre-existing tests are byte-unmodified; the file is 47/47 green.

**Mutation-verification result (AC-M3-2)**: both controls are load-bearing.
- Remove the record `if/then` → 6 tests RED.
- Remove the 7-seam `patternProperties` ban → the 3 sibling-bypass tests RED **while
  `governance.py`'s name guards remained in place and did not save the suite**. That is the direct
  proof the control is structural, not name-based.

### FOLLOW-UP GATE (blocking) — the `asserter_type` honesty hole

Surfaced by the M3 security lens and **accepted as a real gap**, deliberately not fixed in M3.

**What it is**: the structural control fires on `if asserter_type matches ^third_party_ then
retrieval_evidence_ref required`. Nothing — schema or governance — cross-checks that the *declared*
`asserter_type` honestly reflects the origin of `value`. An agent-writable path can declare
`asserter_type: human_reviewer` / `first_party` / `unknown` while `value` carries a genuine
third-party citation count, omit `retrieval_evidence_ref`, and satisfy **every** control as built:
the `if/then` never fires, and `no_agent_authored_attribution_value` only screens for
`CLEARED_*`/`counsel_approved`/`attested` literals — none of which are even valid `asserter_type`
enum members, making that guard structurally inert for this field.

**Why it is non-blocking for M3**: verified by call-site trace — **there is no production writer of
`mint_attribution_record`**. Every caller today is a test. The live writer is *Phase C — third-party
live ingestion*, explicitly deferred (PRD §Out-of-Scope, DEF-1..DEF-6). The hole is real by design but
not live-exploitable, and M3's own AC ("a `third_party_*` value cannot exist without retrieval
evidence") is genuinely achieved.

**The gate**: this MUST be closed **before Phase C, or before any other writer is authorized to mint
attribution records.** Do not assume M3 covered it. Two viable closures, both structural:
1. Derive `asserter_type` **deterministically in code** from the acquisition path, never accepting it
   as a free agent-supplied parameter — the strongest option, since it removes the lie surface.
2. A provenance cross-check that ties `value`'s origin to the declared `asserter_type`.

A name-based guard will **not** close this — that is the failure mode M3 exists to refute.

---

## M4 boundary — gate record, a deploy-runbook requirement, and a collapsed karen pass

**Gate outcome**: both assigned lenses APPROVED (`gate_lens: [security, validator]`,
`gate_lens_reason: irreversible-outward`). The validator lens independently re-ran a mutation rather
than trusting the implementers — folding `absent` into `not_yet_assessed` turned 3/6 coverage tests and
2/5 frozen-fixture tests RED, with a matching sha256 after restore.

**AC-M4 non-regression, run live by the orchestrator** (the plan notes the exploration only
code-traced this, never ran it): the counted sweep passed **7 PASS / 0 FAIL, count gate `n == 7`
satisfied**. The count gate is the real assertion — a glob matching nothing would make the loop exit 0
vacuously.

### DEPLOY-RUNBOOK REQUIREMENT (blocking for the node) — `rf catalog rebuild`

`SCHEMA_VERSION` moved 4 → 5. The catalog is **rebuild-only**: `_ensure_schema()` drops and recreates
every table on a `PRAGMA user_version` mismatch and **does not repopulate**. `search()` / `get_item()` /
`stats()` all fail **open** — an empty catalog returns zeroed counts without erroring, and the router
docstring says so explicitly. So between deploy and rebuild, a caller **cannot distinguish "genuinely
empty" from "just wiped by the migration."**

No data is destroyed (the catalog is 100% derived from canonical files), so this is not a correctness
defect. But it means:

> **After pushing to origin and redeploying `research-foundry-api.service` on the node
> (`10.42.10.76:7432`), `rf catalog rebuild` MUST be run before the live stats/coverage endpoints are
> trusted by anything downstream — otherwise the node will silently report "0 of 0 sources assessed"
> as fact.**

`rf catalog rebuild` (`cli_commands.py`) is the only caller of `svc.rebuild()`; no API route wraps it.
Note the read-only KMCP seam correctly fails **closed** (`query_only_connection` raises
`CatalogUnavailable("catalog_schema_stale")`), so the fail-open/fail-closed asymmetry is confined to the
write-capable path.

### Regression fixed during the M4 gate — stale committed OpenAPI spec

The orchestrator's authoritative full-suite run surfaced a **9th failure not in the known baseline**:
`tests/test_openapi_seam.py::test_committed_openapi_json_matches_live_app`. Cause: SMP-4.5 documented
`attribution_coverage` in the `GET /api/catalog/stats` docstring, and FastAPI turns docstrings into
OpenAPI descriptions, so the committed `src/research_foundry/api/openapi.json` went stale. Regenerated
with `scripts/generate_openapi.py` (a one-line spec diff); the seam test passes and the failure set is
back to exactly the baseline 8. Worth noting the per-milestone targeted suites all passed — only the
**full** suite caught this, which is the argument for running it before merge rather than trusting
scoped runs.

### Deviation — the two karen passes were collapsed into one

The plan requires a karen pass for M4 (its only C3 milestone) `karen: true`, "in addition to (not
instead of)" the single end-of-feature karen that M1–M3 (C2) rely on. Because **M4 is the terminal
milestone**, both passes would read substantially the same tree, making them *duplicate* rather than
*distinct* coverage. Per the execution doctrine (collapse duplicate coverage, never distinct coverage),
**one** karen pass was run at end-of-feature, explicitly scoped to carry BOTH M4's C3 architectural
concerns and the whole-plan lens. Recorded here rather than silently dropping a plan-mandated gate. Had
M4 been followed by further milestones, the two passes would have been genuinely distinct and both
would have run.

---

## Feature-level gate (karen) — CHANGES_REQUESTED, then remediated

The single end-of-feature pass (carrying both scopes per the collapse recorded above) returned
**CHANGES_REQUESTED** with one blocking defect and a set of real secondary findings. It was the most
valuable gate of the run: it caught something six prior reviewer passes all missed.

### BLOCKING (fixed) — the export contract was versioned in documentation only

`src/research_foundry/services/export_service.py` held `EXPORT_SCHEMA_VERSION = "1.8"` — **unchanged at
`c415da0` and unchanged by all four milestone commits** — while
`docs/dev/architecture/rf-run-export-schema.json` went 1.7 → 1.8 (M1) → 1.9 (M4) and the payload shape
changed twice. And `1.8` had **already shipped** for payloads carrying none of the five new fields, so
the version discriminated nothing this feature added. A consumer branching on `schema_version` before
reading `claims[].sources[].attribution_summary` would see `1.8` on every post-merge export, identical to
a pre-feature export: built to doc 1.9 it silently skips the fields; built to doc 1.8 it reads `authors`
on a genuinely-old run and gets `None`/`KeyError`. **AC-6 genuinely failed.**

**Why six gate passes missed it — the mechanism, not the oversight:**
`tests/test_schema_validation.py` asserted the document's own `examples[0] == "1.9"` (the document
validating *itself*), while `tests/unit/test_export_service.py` asserted the emitted constant was
`"1.8"`. **Both were green simultaneously.** Nothing tied the code constant to the documented contract,
and every gate ran scoped `-k export_schema` suites that structurally cannot see the pair. This is
exactly the vacuous-guard failure the plan's own Rubric warned about.

**Fixed**: constant → `"1.9"`; 13 pinned asserts updated across `tests/unit/test_export_service.py` and
`test_export_service_term_index.py`; the document's false 1.8 history corrected so all five new fields
are attributed to 1.9; legacy fixture still validating. **Durable fix**: a new guard asserts
`EXPORT_SCHEMA_VERSION == schema["properties"]["schema_version"]["examples"][0]`, RED-proved — the two
can never drift again.

### Also fixed — AC-1 now true in substance, not just as a capability

OQ-1 concluded "no provider returns DOI", but it enumerated the six **search-router providers** and
never enumerated the **ingest call sites**. `external_research_resolution.py`'s `default_promote` already
held a real external `request.locator.doi` (from `assertion_candidates.yaml`) and **dropped it**,
stuffing it into `locator_text` as `f"doi:{...}"`. Now passed through as `doi=`, with an end-to-end test
proving a promoted card carries the real DOI. The removed `f"doi:{...}"` prefix was grep-verified as
parsed by nothing.

Other call sites were deliberately left alone, with reasons: `cli_commands.py` has no `--doi`/`--author`
flags (adding them is scope expansion, not wiring existing data); `search_router/router.py`'s `SearchHit`
genuinely has no such fields — which *confirms* OQ-1's finding for that surface;
`operator_mcp_adapters/source_ingest.py` exposes no such parameters; `agent_job_service.py` already
forwards `**kwargs` into `create_source_card`, so it needs no change.

### Also fixed — workspace isolation on the new aggregate

`stats()` folded the new `attribution_coverage` block in **unscoped** while the standalone
`attribution_coverage()` was workspace-scoped, so `GET /api/catalog/stats` exposed new cross-workspace
counts. Given this repo's history of row-level isolation leaks found only after the fact, this was
treated as a real isolation concern rather than a cosmetic inconsistency. `stats()` now takes `identity`
and scopes the coverage sub-block by the same `_isolation_active`/`workspace_id` rule; the pre-existing
unscoped `counts`/`runs_indexed` were left alone and reported rather than silently widened (still
WKSP-304 P4). Two new tests prove no cross-workspace bleed.

### WIDENED — the Phase C blocking gate now has a SECOND requirement

The earlier M3 entry recorded the `asserter_type` honesty hole. karen found a second, independent gap in
the same area: **no writer validates a `source_attribution` record.**
`mint_attribution_record(asserter_type="third_party_api", retrieval_evidence_ref=None)` returns an
invalid record **silently** — there is no `validate(rec, "source_attribution")` call anywhere in `src/`.
Cards *are* validated (`source_cards.py`), so M3's 7-seam ban is live; records are not. The "primary
structural control" is therefore a correctly-specified shape with **no enforcing call site**.

> **Phase C (or any future writer) must satisfy BOTH:** (1) derive `asserter_type` deterministically in
> code rather than accepting it as a free agent-supplied parameter, AND (2) actually invoke schema
> validation on every minted record. Fixing only (1) would leave the schema never invoked; fixing only
> (2) would validate an honestly-shaped lie.

Not fixed now, deliberately: there is no production writer to attach validation to, and choosing where
enforcement belongs is a design decision this plan did not make.

### Deferred follow-ups (recorded, not fixed — each with its reason)

1. **`_merge_attribution_summaries` lives in `catalog_service.py`, not `attribution_triage.py`.** Rollup/
   monotone/`comparable` semantics are now in two places, and the docstring honestly admits the cause was
   *orchestration scheduling* (that agent was forbidden from touching `attribution_triage.py` during
   concurrent review), not architecture. A future comparability change must be made twice. Deferred
   because relocation is a pure refactor with no behavioural change, and doing it post-gate would move
   code four reviewer passes just examined. **This one is an orchestration artifact, and owning that:
   the file-ownership partitioning that kept parallel agents safe also pushed logic into the wrong
   module.**
2. **Claim-level merge conflates partial coverage.** A claim citing one assessed + one unassessed source
   reports `present`, losing the unassessed half — arguably the exact conflation tri-state exists to
   prevent, one level up at claim granularity. Deferred because changing the claim-level contract now
   would invalidate M4's frozen fixtures and its just-approved gate. **Sharpest open design gap; should
   be the first follow-up.**
3. **Governance rule 8 duplicates rule 7** on the same two fields with the same predicate — one
   violating write emits two `Violation`s. Cosmetic.
4. **11 pre-existing `source_card` validation failures** across the live bundles
   (`trust.conflicts_with[]` string-vs-object shape). Pre-existing, unrelated, still open.
5. **`stats()`'s pre-existing `counts`/`runs_indexed` remain unscoped** (WKSP-304 P4) — untouched.

### Post-remediation verification

Full suite failure set is **exactly** the 8 known pre-existing failures at `c415da0` — zero new. The
7-bundle counted sweep was **re-run after the version bump**: 7 PASS / 0 FAIL, count gate `n == 7`.
