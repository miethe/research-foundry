## Phase 0 Completion Note — Rights Substrate

### Summary

Ported the pediatric-anemia-site's v1.0 rights-governance schemas into RF's own
`schemas/*.schema.yaml` registry as RF's canonical substrate: `rights_record`,
`rights_extension`, `content_reuse_assessment`, `permission_record`, `rights_failure`.
Applied all 7 Phase-0-owned §9 schema-conflict adjudications at the source
(§9.3, §9.4, §9.5, §9.6a, §9.6b, §9.7, §9.8) rather than carrying them forward
as debt. Registry wiring required zero code changes (`SchemaRegistry` is
dynamic/glob-based); test coverage was extended instead. All 5 tasks dispatched
in two batches (4 parallel schema-authoring tasks, then 1 dependent
registry-wiring task) per file-ownership boundaries — no two agents wrote the
same file concurrently.

### Tasks

- [x] P0-1 → data-layer-expert — `schemas/rights_record.schema.yaml` ported with all 7 owned §9 rows; 18 fixture tests in a dedicated new file `tests/test_rights_record_schema_fixtures.py` (kept separate from `test_schema_validation.py` to avoid collision with 3 concurrent sibling edits to that shared file)
- [x] P0-2 → data-layer-expert — `schemas/rights_extension.schema.yaml` ported; §9.1 negative-space guard test added (zero overlap with evidence-taxonomy field names)
- [x] P0-3 → data-layer-expert — `schemas/content_reuse_assessment.schema.yaml` ported; enum-identity test confirms `component_type` (21 members) and `review_status` (6 members) are byte-identical literal lists to P0-1's
- [x] P0-4 → data-layer-expert — `schemas/permission_record.schema.yaml` + `schemas/rights_failure.schema.yaml` ported as-is structurally; 6 new valid/invalid fixture tests
- [x] P0-5 → python-backend-engineer — registry wiring (no code change needed — `SchemaRegistry` glob-discovers `schemas/*.schema.yaml`); extended `EXPECTED_SCHEMA_NAMES` 32→37 and the shared `_valid()`/`_invalid()` parametrized builders in `tests/test_schema_validation.py` to cover all 5 new schemas, including `rights_record` (which previously had zero coverage in that specific file, satisfying the literal AC wording)

### Validator Verdict

**task-completion-validator: APPROVED (PASS).** 0 fix cycles required. Validator independently re-ran the full test suite (`105 passed, 0 failed`) and read the schema files directly rather than trusting progress-file self-reports. Confirmed: all 5 schemas parse as valid Draft 2020-12 and register; all 7 owned §9 rows have paired valid/invalid fixtures; the §9.6b empty-`contract: {}` dedicated regression guard exists (`test_9_6b_empty_contract_object_is_invalid_dedicated_guard`); P0-2's negative-space guard and P0-3's enum-identity test both pass against live files; no file collisions across the 5 concurrent implementer sessions.

Two low-severity notes carried forward (not blockers):
1. `rights_record.schema.yaml` drops the v1.0 open `extensions: {type: object}` bag (not one of the 7 named §9 rows) — record as a deviation with rationale in the P5 ADR.
2. `component_type`/`review_status` enums are duplicated by copy-paste across `rights_record.schema.yaml` and `content_reuse_assessment.schema.yaml` (no `$ref` support in `SchemaRegistry` — DI-RIGHTS-5, already tracked in the plan's deferred-items table) — guarded by the P0-3 identity test now; full sweep is P6-1's job.

### Files Changed

- `schemas/rights_record.schema.yaml` — new (P0-1)
- `schemas/rights_extension.schema.yaml` — new (P0-2)
- `schemas/content_reuse_assessment.schema.yaml` — new (P0-3)
- `schemas/permission_record.schema.yaml` — new (P0-4)
- `schemas/rights_failure.schema.yaml` — new (P0-4)
- `tests/test_rights_record_schema_fixtures.py` — new (P0-1, 18 tests)
- `tests/test_schema_validation.py` — extended (P0-2/P0-3/P0-4 append-only functions + P0-5's `EXPECTED_SCHEMA_NAMES`/`_valid()`/`_invalid()` extensions)
- `src/research_foundry/schemas.py` — no change (dynamic registry, confirmed by P0-5)
- `.claude/worknotes/rights-entity-model/context.md` — P0-3 appended a note on independent enum origination, resolved once P0-1 landed (no reconciliation needed — enums matched)

### Deviations & Risks

- `rights_record.schema.yaml` dropped v1.0's open `extensions` bag (incompatible with the task's `additionalProperties: false` everywhere instruction). Flagged for the P5 ADR's deviation log per decisions-block Risk 2.
- No `$ref`/`$defs` cross-file support in `SchemaRegistry` means the shared `component_type`/`review_status` enums are literal-copied, not referenced — already a known, tracked risk (DI-RIGHTS-5), mitigated by the P0-3 identity test and to be fully swept in P6-1.
- No blockers, no Mode D triggers encountered. No scope beyond the phase's 5 files + registry/test files was touched.

### Commits (worktree runs)

- `b796e43` — feat(rights): P0 — port rights substrate schemas (§9 adjudications)
