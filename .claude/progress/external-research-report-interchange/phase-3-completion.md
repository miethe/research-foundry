---
type: completion
schema_version: 1
doc_type: completion
prd: external-research-report-interchange
feature_slug: external-research-report-interchange
phase: 3
title: Producer Prompt/Output Profiles — Completion Note
status: complete
created: '2026-07-26'
prd_ref: docs/project_plans/PRDs/enhancements/external-research-report-interchange-v1.md
plan_ref: docs/project_plans/implementation_plans/enhancements/external-research-report-interchange-v1.md
contract_ref: docs/dev/architecture/external-research-handoff-contract.md
---

# Phase 3 — Producer Prompt/Output Profiles — Completion Note

## Files created

### A. Five profiles under `templates/external_research_handoff/v1/`

```
templates/external_research_handoff/v1/README.md          # shared index + rules
templates/external_research_handoff/v1/generic/{prompt.md, mapping.md, README.md}
templates/external_research_handoff/v1/chatgpt/{prompt.md, mapping.md, README.md}
templates/external_research_handoff/v1/perplexity/{prompt.md, mapping.md, README.md}
templates/external_research_handoff/v1/gemini/{prompt.md, mapping.md, README.md}
templates/external_research_handoff/v1/notebooklm/{prompt.md, mapping.md, README.md}
```

16 files total (1 index + 5 × 3).

### B. Schema-valid example packets under `tests/fixtures/external_research_handoff/profiles/<profile>/`

One complete packet per profile — `handoff.yaml`, `report.md`, `sources.yaml`,
`assertion_candidates.yaml` — for `generic`, `chatgpt`, `perplexity`, `gemini`, `notebooklm` (20
files). The pre-existing P1 fixture directories (`handoff/`, `sources/`, `assertion_candidates/`,
`import_receipt/`, `import_checkpoint/`, `acquisition_policy/`) were not touched.

### C. Injection-shaped fixture

`tests/fixtures/external_research_handoff/profiles/injection/` — `handoff.yaml`, `report.md`,
`sources.yaml`, `assertion_candidates.yaml`, `activity.yaml` (5 files; the only profile fixture that
includes the optional `activity` member, specifically to exercise the "activity" surface named in
ERI-3.6).

### Test file

`tests/unit/test_external_research_profiles.py` (20 tests).

## How ERI-3.1..3.6 were satisfied

- **ERI-3.1 (generic)**: `generic/prompt.md` is the canonical, platform-agnostic pasteable prompt
  (five trust invariants, explicit unknown-field rule, `platform_synthesis` framing).
  `generic/mapping.md` carries the four required packet-member YAML templates verbatim (field-exact
  against the three frozen record schemas), the two optional-member examples (`activity.yaml`,
  attachment), and the explicit unknown-field rules. `generic/README.md` states the offline/manual
  boundary and the 5-step production walkthrough. The fixture at `profiles/generic/` validates and
  demonstrates both a filled record (`src_01`/`cand_01`) and an all-null "don't know" record
  (`src_02`).

- **ERI-3.2 (chatgpt)**: `chatgpt/mapping.md` documents, unambiguously, that ChatGPT's own
  `citeturn…`/`fileciteturn…`/`turn…` inline markers are UI rendering artifacts — never a URL, DOI,
  or selector — and must be dropped from every `locator`/`selector` field, surviving only inside a
  namespaced `extensions.chatgpt.vendor_citation_markers` array. No API/SDK/session-scraping anywhere;
  packet-local citation/source IDs are operator-assigned. The fixture at `profiles/chatgpt/` is
  derived from the real completed ChatGPT Deep Research packet at
  `pediatric-anemia-site/docs/project_plans/expansion/dr-packets/cbc/chatgpt-dr/expected-output/rf-cbc-002-gpt-dr.md`
  — three real candidate rows (`itp-diagnostic-thrombocytopenia`, `wbc-leukocytosis-infancy`,
  `eosinophilia-mild`) and their real DOIs/citeturn markers, with the markers correctly quarantined
  into `extensions.chatgpt.*` on both the source and candidate records; `report.md` preserves the raw
  `fileciteturn…`/`citeturn…` markers inline in untouched prose, exactly as a real ChatGPT export
  would.

- **ERI-3.3 (perplexity)**: `perplexity/mapping.md` maps `[N]` inline citation markers to
  packet-local `source_id`s and states that Perplexity's own result ranking/relevance score is
  non-authoritative, living only in `extensions.perplexity.rank`/`relevance_score` and never
  influencing `classification`/`producer_confidence`/import behavior. The fixture demonstrates the
  `[1]`/`[2]` → `src_01`/`src_02` mapping and a non-authoritative `rank`/`relevance_score` pair on one
  source.

- **ERI-3.4 (gemini)**: `gemini/mapping.md` maps grounding chips to sources and grounded/ungrounded
  answer spans to candidates without any Google API/`groundingMetadata` coupling, and states the
  explicit-null preservation rule. The fixture includes one grounded candidate (`source_refs`
  pointing at the chip) and one **ungrounded** candidate (`source_refs: []`,
  `extensions.gemini.grounding_chip_index: null`) — preserved rather than dropped, with the null
  explicit rather than omitted.

- **ERI-3.5 (notebooklm)**: `notebooklm/mapping.md` and `README.md` label the profile
  `offline-unvalidated` prominently (also carried as inert data at
  `handoff.yaml#vendor_reference.profile_status` and per-source
  `extensions.notebooklm.profile_status` in the fixture), assume no live CLI/API anywhere, and map
  footnote-style citations to uploaded-source records where `title` is usually known (operator-named)
  but `locator.url`/`locator.doi` stay `null` (a local upload has neither).

- **ERI-3.6 (injection fixtures)**: `profiles/injection/` plants at least one instance of every
  required category — prompt overrides, tool-call/tool-description shapes, route/schema selectors,
  shell commands, path-traversal arguments, template/format-string injections, and YAML/JSON
  deserialization bait — across `handoff.yaml` (`research_context`, `vendor_reference`), `sources.yaml`
  (`title`, `declared_metadata`, `extensions`, including a raw `url` containing `../../` + `; rm -rf /`),
  `assertion_candidates.yaml` (`statement`, `quote`, `unit`, `direction`, `scope`, `selector.$ref`,
  `extensions`, a planted `__proto__` key), `report.md` (raw prose), and `activity.yaml`. Every
  category is placed only inside fields the frozen schemas leave as unconstrained free text or
  `additionalProperties: true` objects — never inside a pattern/enum-constrained structural field
  (`members[].path`, `members[].role`, `source_id`, `candidate_id`, `classification`, `access_status`,
  `relation`, `schema_name`/`schema_version`/`transport`).

## Test coverage

`tests/unit/test_external_research_profiles.py` — **20 tests**, 3 groups:

1. **Schema validity** (6 tests): each of the 5 profile fixtures' `handoff.yaml`/`sources.yaml`/
   `assertion_candidates.yaml` validates against the three frozen record schemas, plus a dedicated
   test that the injection packet (including its `activity.yaml`, which has no dedicated v1 schema)
   loads and validates too.
2. **Canonical shape / deterministic ordering** (3 tests): a pure, test-local
   `canonicalize_packet()` helper (no service code called — `external_research_interchange.py` is
   untouched, per instructions) reduces each profile's packet to schema name/version, transport,
   `content_roles`, and a `(role, path)`-sorted member-role sequence; asserts all five profiles share
   identical `schema_name`/`schema_version`/`transport`/`content_roles` and an identical sorted
   required-role ordering, and that canonicalization is deterministic (re-running is byte-identical).
3. **Injection inertness** (11 tests): proves the injection fixture (a) actually carries every
   required category, (b) parses every payload as a plain `str` — never a constructed YAML tag/object
   — even for a literal `!!python/object/apply:...` string, (c) never leaks a payload into any
   structural control field (member path/role, packet-local ids, closed enums), (d) treats a planted
   `selector.$ref` as inert data the validator never dereferences, (e) round-trips byte-identical
   through a YAML dump/reload cycle, (f) round-trips through JSON with a planted `__proto__` key
   remaining ordinary string-keyed data (no prototype-pollution vector exists in Python), and (g)
   confirms `report.md`'s injection-shaped prose has no structural path into `sources.yaml`/
   `assertion_candidates.yaml`.

Regression: `tests/unit/test_external_research_schemas.py` — **29 tests**, still green, unmodified.

Total for this phase's validation command: **49 passed, 0 failed**.

## Unresolved / carried forward

- Byte-for-byte `packet_digest`/`policy_digest` correctness is out of scope for this phase (no
  importer exists yet — Phase 2/4/5). Fixture `handoff.yaml` members carry real `byte_length`/`sha256`
  for `report.md`/`sources.yaml`/`assertion_candidates.yaml`/`activity.yaml` (computed from the actual
  on-disk bytes), but the `handoff_manifest` role's own self-referential entry uses the same
  accepted-approximation the existing P1 golden fixture (`handoff/valid.yaml`) already establishes
  (fixed-point self-hashing is a Phase 2 importer concern, not a schema-fixture one).
- `activity.yaml`'s content shape has no dedicated schema in v1 (confirmed: only the six named
  schemas exist) — the injection fixture's `activity.yaml` and the generic profile's optional-member
  example both note this explicitly and keep the file to safe IDs/timestamps/short labels by
  convention only, not schema enforcement.
- No production code was touched — `src/research_foundry/services/external_research_interchange.py`
  remains untouched, per instructions. No `git add`/`git commit` was run.
