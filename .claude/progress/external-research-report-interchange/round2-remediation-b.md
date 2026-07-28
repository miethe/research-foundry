---
title: "ERI round-2 remediation (agent B) — findings #8, #10, #11, #12, #13"
doc_type: report
report_category: finding
schema_version: 2
status: completed
source: agent
created: 2026-07-27
updated: 2026-07-27
feature_slug: external-research-report-interchange
promoted_to: []
---

# Round-2 remediation (agent B)

Scope: `.claude/findings/eri-implementation-audit-round2-gpt56.md`, findings #8, #10, #11, #12,
#13 only. Files touched: `src/research_foundry/services/source_acquisition_policy.py`,
`schemas/external_research_acquisition_policy.schema.yaml`,
`schemas/external_research_handoff.schema.yaml`,
`tests/unit/test_source_acquisition_policy.py`,
`tests/integration/test_external_research_adversarial_matrix.py`,
`tests/unit/test_external_research_schemas.py`, `tests/test_schema_validation.py`, plus
`tests/fixtures/external_research_handoff/acquisition_policy/*` and
`tests/fixtures/external_research_handoff/handoff/*` (fixtures only, for the two schema
changes). `external_research_interchange.py`/`external_research_import.py` and their tests were
not touched (parallel agent's ownership).

## #10 — IPv6 site-local bypasses the address policy (MEDIUM) — CLOSED

`fec0::/10` is neither `is_private` nor `is_reserved` under stdlib `ipaddress`, so it fell through
every existing category check.

- Added `CATEGORY_IPV6_SITE_LOCAL = "ipv6_site_local"` to `DEFAULT_FORBIDDEN_CATEGORIES` and a
  dedicated `ip.is_site_local` check in `forbidden_address_category()` —
  `source_acquisition_policy.py:111-116,395-451` (constant + check).
- Schema: added `ipv6_site_local` to `forbidden_address_categories`'s `const` list —
  `schemas/external_research_acquisition_policy.schema.yaml` (now 12 entries).
- Proof: `tests/unit/test_source_acquisition_policy.py::TestIPv6SiteLocalDenied` —
  `test_site_local_denied_by_category` (direct category check),
  `test_site_local_not_caught_by_private_or_reserved_alone` (documents why the dedicated category
  was needed), and `test_acquire_denies_injected_resolver_returning_site_local` — the auditor's
  exact repro (injected resolver returns `fec0::1`; asserts `ok is False`, denial code
  `forbidden_address:ipv6_site_local`, zero connect calls).

## #11 — Malformed operator-configured NAT64 prefixes fail open (MEDIUM) — CLOSED

`_transition_networks()` previously did `except ValueError: continue`, silently dropping any
prefix (e.g. `2600:abcd:1234::1/96`, host bits set) that failed to parse — permitting exactly the
attack the operator meant to close off via that deployment's real NAT64 route.

- Added `AcquisitionPolicyError` and `_parse_operator_nat64_prefixes()`, which parses every entry
  with `ipaddress.ip_network(raw, strict=True)` and raises on ANY malformed/non-IPv6 entry instead
  of skipping it — `source_acquisition_policy.py` (new exception class + function,
  `_transition_networks` now delegates to it).
- `acquire()` validates `operator_configured_nat64_prefixes` ONCE up front and denies the WHOLE
  request closed (`DENIAL_POLICY_INVALID = "policy_configuration_invalid"`) before any DNS/connect
  if invalid; the per-hop `forbidden_address_category()` call is also wrapped defensively for the
  same exception.
- Schema: `operator_configured_nat64_prefixes` items now require a `pattern` matching IPv6-CIDR
  shape (`^[0-9a-fA-F:]+/[0-9]{1,3}$`); the stricter "canonical, no host bits" check is documented
  as a runtime-only constraint (not expressible as a JSON Schema regex) —
  `schemas/external_research_acquisition_policy.schema.yaml`.
- New fixtures: `invalid_operator_nat64_prefix_not_cidr_shaped.yaml` (schema-level shape rejection),
  `valid_operator_nat64_prefix.yaml` (proves the additive capability still works).
- Proof: `tests/unit/test_source_acquisition_policy.py::TestOperatorNat64PrefixFailsClosed` —
  `test_non_canonical_prefix_raises_from_forbidden_address_category`,
  `test_acquire_denies_whole_request_closed_before_any_dns_or_connect` (asserts DNS resolver is
  never even called — `AssertionError` inside the fake resolver would fail the test if it were),
  `test_canonical_operator_prefix_still_works` (regression guard on the legitimate feature).

## #12 — Hostile redirect escapes the fail-closed acquisition API (MEDIUM) — CLOSED

`urljoin()`/`urlsplit()` on a redirect `Location` ran outside any exception boundary; confirmed
locally that `urlsplit("http://[::1")` and `urljoin(base, "http://[::1")` both raise
`ValueError: Invalid IPv6 URL` — this would have propagated out of `acquire()` uncaught, aborting
the import instead of producing a denied `AcquisitionOutcome`.

- Wrapped the redirect-target construction/parsing in `try/except Exception`, returning
  `AcquisitionOutcome(ok=False, denial_code="redirect_malformed_location", ...)` on any failure —
  `source_acquisition_policy.py` (redirect-handling block inside `acquire()`).
- Proof: `tests/unit/test_source_acquisition_policy.py::TestAcquireWithFakes::
  test_redirect_with_malformed_ipv6_location_denies_closed` — exact repro
  (`Location: http://[::1`), asserts `ok is False`, `denial_code == "redirect_malformed_location"`,
  and only the initial hop connects (no crash, no second connection attempt).

## #8 — Duplicate required roles / non-unique member paths (MEDIUM) — PARTIALLY CLOSED (schema only)

Two sub-problems named in the finding:

1. **Cardinality** (a role like `report` declared more than once) — CLOSED at the schema layer:
   added `maxContains: 1` alongside the existing `minContains: 1` for `handoff_manifest`, `report`,
   `sources`, and `assertion_candidates` in `schemas/external_research_handoff.schema.yaml`. New
   negative fixture `tests/fixtures/external_research_handoff/handoff/
   invalid_duplicate_required_role.yaml` (two `role: report` members) — confirmed schema-rejected
   (`"Too many items match the given schema (expected at most 1)"`), picked up automatically by
   `test_external_research_schemas.py`'s glob-based `invalid_*.yaml` discovery.
2. **Uniqueness of `path` across `members[]`** — REMAINS OPEN from this agent's side, stated
   explicitly rather than claimed closed: standard JSON Schema (Draft 2020-12, python `jsonschema`
   library, no custom keywords registered in `research_foundry.schemas`) has no built-in way to
   express "one string-valued property must be unique across all array items" — `uniqueItems`
   only rejects wholly-identical objects, not two objects sharing one field with differing
   siblings. This must be enforced in the RUNTIME parser (`external_research_interchange.py`,
   parallel agent's ownership) or via a custom jsonschema keyword (would require touching
   `src/research_foundry/schemas.py`, also outside this agent's file list). The schema's
   `members` field description was updated to say so explicitly and point at the runtime as the
   enforcement point. **Runtime enforcement of unique member paths (the "misbinds to another
   member's provenance" half of the exploit) is NOT verified by this agent's changes.**

## #13 — Vacuous injection-pipeline integration test (LOW) — CLOSED

The prior `test_injection_profile_imports_cleanly_with_no_control_surface_effect` ran
`dry_run=True` and asserted only `outcome.status in (...)` — no acquisition, no promotion, no
source-card filename/body, no receipt-content check. Kept as a cheap smoke check
(`test_injection_profile_imports_cleanly_dry_run_smoke`) and added the real test:
`test_hostile_locator_and_title_never_become_a_filename_or_control_value` in
`tests/integration/test_external_research_adversarial_matrix.py`:

- Builds a packet (via the shared `build_packet()` helper) with a NULL-titled, hostile-locator
  source (`https://attacker.example.test/../../etc/passwd?cmd=;rm -rf /&x={{7*7}}&y=${jndi:...}`)
  and a candidate whose `quote` is engineered to exactly match a substring of the fake-acquired
  content — forcing REAL passage resolution and REAL promotion (not a stub), which is the only
  code path that writes a durable source-card file (`default_promote` -> `source_cards.
  ingest_source`).
- Runs the full, non-dry `import_external_report()` (real run directory) with a controlled
  in-process fake `acquire` (records every locator it's called with; zero real network — the
  acquisition gate itself stays covered by the exhaustive unit-test matrix).
- Asserts: (1) neither `outcome.safe_dict()` nor `outcome.receipt` ever carries any of 8 hostile
  path/command fragments (`etc/passwd`, `rm -rf`, `DROP TABLE`, `jndi:ldap`, `python/object/apply`,
  `whoami`, `System32`, `etc/shadow`) raw; (2) promotion actually happened (a real `*.md` source
  card exists on disk); (3) EVERY file the import wrote under the run directory has a filename
  free of those fragments (loosely collapsed so re-arranged survivors are still caught); (4) every
  source-card filename specifically matches the frozen safe shape
  `^src_\d{8}_[a-z0-9_]+_[0-9a-f]{8}\.md$` — i.e. `slugify()` genuinely neutralized the hostile
  locator/title into `[a-z0-9_]` only, not merely "didn't happen to collide with the 8-item
  sentinel list."

**How I verified the new test can actually FAIL** (per the instruction): I temporarily weakened
`_SLUG_STRIP` in `src/research_foundry/ids.py` from `r"[^a-z0-9]+"` to
`r"[^a-z0-9;${}: -]+"` (simulating a regression where `slugify()` stops neutralizing path/command
characters), re-ran only the new test, and got a **red run**:

```
AssertionError: source-card filename
'src_20260613_https:_attacker_example_test_etc_passwd_6e6927b7.md' does not match the frozen
safe shape '^src_\d{8}_[a-z0-9_]+_[0-9a-f]{8}\.md$' -- a hostile title/locator may have survived
slugify() into the filename
```

i.e. with the sink weakened, `etc_passwd` and the literal scheme `https:` genuinely leaked into
the real on-disk filename, and the strict-shape assertion caught it. I then reverted `ids.py`
exactly to its original content (`git diff` on that file is empty — confirmed clean) before
finishing. This is the only file outside my owned list I touched, and only transiently for this
verification; no change to it is part of the final diff.

## Validation run (my gate only, per coordinator instruction)

```
PYTHONPATH=$PWD/src /Users/miethe/dev/homelab/development/research-foundry/.venv/bin/python -m pytest \
  tests/unit/test_source_acquisition_policy.py tests/unit/test_external_research_schemas.py \
  tests/integration/test_external_research_resolution.py \
  tests/integration/test_external_research_adversarial_matrix.py \
  tests/integration/test_external_research_cross_profile_compat.py \
  tests/test_schema_validation.py -q
```

All green (exit 0). `ruff check` clean on every file I edited (one pre-existing, unrelated I001
import-order note in `tests/unit/test_source_acquisition_policy.py` predates my changes — confirmed
via `git show HEAD:...`). `mypy --ignore-missing-imports` on both edited production modules
(`source_acquisition_policy.py`, `external_research_resolution.py`): `Success: no issues found in
2 source files` (note: `external_research_resolution.py` itself required no code changes this
round — only the two files noted above were edited for #10/#11/#12; it's listed as "owned" per the
original brief but had no findings assigned to it in this batch).

The full cross-file validate command in the original brief (`tests/unit/
test_external_research_interchange.py` et al.) is NOT this agent's gate — that file hardcodes the
pre-#10 11-category `forbidden_address_categories` list and is owned/being fixed by the parallel
agent per the coordinator's explicit instruction mid-session.
