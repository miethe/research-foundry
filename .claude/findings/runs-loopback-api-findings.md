---
title: "Findings: Runs Loopback API — execution discoveries"
doc_type: report
report_category: findings
schema_version: 2
status: accepted
created: 2026-06-22
updated: 2026-06-22
feature_slug: runs-loopback-api
plan_ref: docs/project_plans/implementation_plans/features/runs-loopback-api-v1.md
owner: nick
---

# In-Flight Findings — Runs Loopback API (P1–P7)

## FIND-01 — Pre-existing point-level redaction failures in `export_service` (out of scope, NOT introduced)

**Discovered:** P6 (Tests), 2026-06-22, while running the full pytest suite.

**Symptom:** Four tests fail in the full suite:
- `tests/unit/test_export_service.py::test_default_public_threshold_redacts_personal_and_above`
- `tests/unit/test_sensitivity_redaction.py::test_work_sensitive_quote_absent_at_default_public_threshold`
- `tests/unit/test_sensitivity_redaction.py::test_round_trips_via_export_to_file`
- `tests/unit/test_sensitivity_redaction.py::test_null_quote_and_summary_on_sensitive_point_still_show_marker`

The assertions show secret quote strings (`SECRET_WORK_QUOTE`, `INTERNAL_..._FIGURE_42M`)
present in exported JSON at the default `public` threshold, and a `work_sensitive`
"point" not flagged `redacted`. So **point-level** redaction under-redacts.

**Pre-existing — verified:** the same four tests fail identically against the
pre-feature base commit `03c0468` (the main checkout, which contains none of the
`rf serve` code). Cross-confirmed by the project memory note "RF test-suite gotchas"
which lists "the 4 known pre-existing sensitivity/export failures." This plan does
**not** modify `src/research_foundry/services/export_service.py` (not in `files_affected`).

**Why it does not block this feature:**
- The loopback API routes **all** data through `export_service.export_run` / `list_runs`
  (Risk R1 invariant), so it has **parity** with the already-shipped static-export path
  (`rf run export --json`). The bug affects both paths equally; the live API neither
  introduces nor worsens it.
- The feature's own critical gate **TEST-006 passes** and is non-vacuous: it asserts a
  `work_sensitive` **source-card** quote is replaced by `REDACTION_MARKER`, that raw
  secrets are absent from the API response, and parity with a direct `export_run` call.
  Source-card-level redaction works; the failing upstream tests target point-level
  redaction, a different code path.

**Impact / caveat for the operator:** the sensitivity gate's *advertised* protection is
only as strong as `export_service` redaction. Point-level redaction is currently broken
upstream, so any deployment (static export or live API) under-redacts sensitive *points*
at `public` threshold. This should be fixed in `export_service`, independent of this feature.

**Recommended follow-up (separate bug-fix, not this plan):** fix point-level redaction in
`export_service` so the `redacted` flag and `REDACTION_MARKER` are applied to points/claims
(not only source cards) at/above the configured threshold; then the four unit tests pass
and the live API inherits the fix for free.

## FIND-02 — Advisory: operator-supplied CORS lists containing bare `*` pass through (non-blocking)

**Discovered:** P4 security review (`senior-code-reviewer`, ADVISORY-1).

`app.py::_build_cors_origins` substitutes the explicit localhost origin list only when the
config returns exactly `["*"]` (the default). An operator config like `["*", "https://x"]`
passes the bare `*` through to `CORSMiddleware`. With `allow_credentials=True` browsers
reject credentialed wildcard requests, so this is a misconfiguration/clarity gap rather than
a runtime hole for the loopback-first use case. **Follow-up:** strip/warn on bare `*` entries
in operator-supplied CORS lists.
