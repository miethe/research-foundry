---
type: worknote
schema_version: 2
doc_type: worknote
prd: research-foundry-operator-mcp
feature_slug: research-foundry-operator-mcp
status: complete
created: '2026-07-31'
updated: '2026-07-31'
---

# M3 exact-tree evidence — AC OPM-1..7 + M1/M2 rows

Tree: 7c615a807cfa6f5b80d0f3584dbc25ee531f1cdb (branch worktree-operator-mcp-v1), captured 2026-07-31T21:04Z.
Single-tenant run (no concurrent pytest; whole capture under /tmp/opm-m3-pytest.lock).

## M1 — closed dispatch scan (live-code hits only)

```
$ rg -n "^\s*(import|from)\s+(typer|subprocess)|cli_commands|os\.system|shell=True" src/research_foundry/services/operator_mcp_adapters/ src/research_foundry/operator_mcp/ (live-import form)
src/research_foundry/operator_mcp/server.py:10:or uses `shell=True` anywhere in its own call path (hard boundary 3).
live-import matches exit=0 (1 = zero matches = PASS)
```

### M1 — adapter/service parity (all adapter suites)

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_base.py tests/unit/test_operator_mcp_adapter_external_import.py tests/unit/test_operator_mcp_adapter_job_lifecycle.py tests/unit/test_operator_mcp_adapter_research_stages.py tests/unit/test_operator_mcp_adapter_run_plan.py tests/unit/test_operator_mcp_adapter_source_ingest.py tests/unit/test_operator_mcp_adapter_swarm_start.py tests/unit/test_operator_mcp_adapter_verify_bundle.py tests/unit/test_operator_mcp_adapter_writeback_preview.py -q --tb=no -ra
........................................................................ [ 47%]
........................................................................ [ 94%]
........                                                                 [100%]
exit=0
```

### M1 — CLI unchanged after extraction

```
$ ./.venv/bin/python -m pytest tests/test_search_router_router.py tests/integration/test_run_launch_reuse.py -q --tb=no
          Read more about it in the
          [FastAPI docs for Lifespan Events](https://fastapi.tiangolo.com/advanced/events/).
          
    return self.router.on_event(event_type)  # ty: ignore[deprecated]

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
exit=0
```

### M1 — retry/cancel idempotency (-k selects 8)

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_operation_service.py -q --tb=no -k retry or cancel or resume or duplicate
........                                                                 [100%]
exit=0
```

### M2 — exact tool inventory + zero Knowledge-MCP overlap

```
$ ./.venv/bin/python -m pytest tests/integration/test_operator_mcp_server.py -q --tb=no -k inventory or introspect or overlap
..                                                                       [100%]
exit=0
```

### M2 — preview cannot execute (zero-call spies)

```
$ ./.venv/bin/python -m pytest tests/integration/test_operator_mcp_writeback_preview.py -q --tb=no
....                                                                     [100%]
exit=0
```

### AC OPM-1 — confirmation binding (-k selects 33)

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_policy.py -q --tb=no -k confirm or replay or expiry or drift
.................................                                        [100%]
exit=0
```

### AC OPM-1 — full policy adversarial file

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_policy.py -q --tb=no
........................................................................ [ 54%]
.............................................................            [100%]
exit=0
```

### AC OPM-2 — two-identity workspace/sensitivity matrix

```
$ ./.venv/bin/python -m pytest tests/integration/test_operator_mcp_workspace_isolation.py -q --tb=no
............................                                             [100%]
exit=0
```

### AC OPM-3 — lifecycle (H3 matrix, full file)

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_operation_service.py -q --tb=no
............................................                             [100%]
exit=0
```

### AC OPM-5 — import/stage seams

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_adapter_external_import.py tests/unit/test_operator_mcp_adapter_research_stages.py tests/unit/test_operator_mcp_adapter_source_ingest.py tests/unit/test_operator_mcp_adapter_verify_bundle.py -q --tb=no -k import or stage or prerequisite
..................................                                       [100%]
exit=0
```

### AC OPM-6 — preview-only (runtime)

```
$ ./.venv/bin/python -m pytest tests/integration/test_operator_mcp_writeback_preview.py tests/unit/test_operator_mcp_adapter_writeback_preview.py -q --tb=no
....................                                                     [100%]
exit=0
```

### AC OPM-7 — bounded transport (widened command)

```
$ ./.venv/bin/python -m pytest tests/integration/test_operator_mcp_server.py tests/integration/test_operator_mcp_workspace_isolation.py -q --tb=no -k limit or error or redact or oversize or payload or workspace
.....................................                                    [100%]
exit=0
```

### Receipt schema per-property + bounds attacks

```
$ ./.venv/bin/python -m pytest tests/unit/test_operator_mcp_schemas.py -q --tb=no
........................................................................ [ 42%]
........................................................................ [ 84%]
...........................                                              [100%]
exit=0
```

### M2 — optional-SDK base import

```
$ ./.venv/bin/python -c import sys; sys.modules['mcp']=None; import research_foundry; print('base ok')
base ok
exit=0
```

### Lint gate (ruff)

```
$ ./.venv/bin/ruff check src/research_foundry --select E9,F63,F7,F82
All checks passed!
exit=0
```

## Whole-suite regression (single-tenant)

```
$ ./.venv/bin/python -m pytest (full tree)
FAILED tests/test_cli_rights.py::test_rights_validate_requires_as_of - assert '--as-of' in "\x1b[33mUsage: \x1b[0mrf rights validate [OPTIONS] [PA...
FAILED tests/test_contract_drift_rf_schema_version.py::test_cli_json_dumps_sites_fully_accounted_for - AssertionError: Found _json.dumps( call site(s) not routed through _stamp()...
FAILED tests/test_contract_drift_rf_schema_version.py::test_cli_json_dumps_site_counts_match_pinned_baseline - assert 28 == 27
FAILED tests/test_deployment_mode_cli_and_app.py::TestServeModeFlag::test_mode_multi_user_without_provider_refuses_before_binding - AssertionError: assert '(a)' in '\x1b[31merror:\x1b[0m \x1b[33mdeployment_m...
FAILED tests/test_pdf_extractor.py::test_extract_pdf_with_text_layer_returns_full_text - AssertionError: assert 'locator_only' == 'full_text'
FAILED tests/test_pdf_extractor.py::test_extract_pdf_without_text_layer_returns_locator_only - AssertionError: assert ['pypdf not installed'] == ['no text layer']
FAILED tests/test_pdf_extractor.py::test_extract_pdf_corrupted_input_returns_locator_only_without_raising - AssertionError: assert 'corrupted PDF' in 'pypdf not installed'
FAILED tests/test_pdf_fixture_suite.py::test_pdf_with_text_layer_surfaces_full_text_end_to_end - assert True is False
FAILED tests/test_pediatric_cds_redteam_fixtures.py::test_seven_verified_bundles_zero_false_positives - AssertionError: expected verified bundle sources dir at /Users/miethe/dev/h...
FAILED tests/test_search_router_pdf_wiring.py::test_pdf_url_with_text_layer_is_not_degraded - assert True is False
FAILED tests/test_serve_api.py::test_get_run_detail_known_run_returns_200 - assert 404 == 200
FAILED tests/test_serve_api.py::test_get_claims_non_empty - assert 404 == 200
FAILED tests/test_serve_api.py::test_get_claims_empty_ledger_returns_empty_list - assert 404 == 200
FAILED tests/test_serve_api.py::test_get_source_found - assert 404 == 200
FAILED tests/test_serve_api.py::test_sensitivity_gate_parity_work_sensitive_claim - assert 404 == 200
FAILED tests/test_swarm_drive.py::test_cli_drive_json_output - assert '"status_derived": "bundle_written"' in '\x1b[1m{\x1b[0m\n  \x1b[1;3...
FAILED tests/test_swarm_drive.py::test_cli_drive_ica_json - assert '"status_derived": "awaiting_legs"' in '\x1b[1m{\x1b[0m\n  \x1b[1;34...
FAILED tests/test_verification_clinical_eligibility_regression.py::test_seven_verified_bundles_zero_eligible_claims - AssertionError: expected claim ledger at /Users/miethe/dev/homelab/developm...
FAILED tests/test_verification_clinical_eligibility_regression.py::test_seven_verified_bundles_exact_passage_present_never_hard_gated_by_p3 - AssertionError: expected claim ledger at /Users/miethe/dev/homelab/developm...
FAILED tests/test_verification_seam001_gate_composition.py::test_seven_verified_bundles_pass_verify_report_with_all_three_gates_active - AssertionError: expected verified bundle run dir at /Users/miethe/dev/homel...
FAILED tests/unit/test_assertion_rollout.py::test_assertion_ledger_controls_are_independently_default_off - AssertionError: assert True is False
FAILED tests/unit/test_assertion_rollout.py::test_write_and_automated_reuse_consumers_fail_closed_by_default - AssertionError: assert 'eligible' == 'automated_reuse_disabled'
FAILED tests/unit/test_report_anchors.py::test_schema_version_bumped_for_report_anchors - AssertionError: assert '1.8' == '1.4'
23 failed, 4835 passed, 5 skipped, 1 xfailed, 1382 warnings in 709.40s (0:11:49)
exit=0
```

## Orchestrator annotations

- **Whole-suite failure-set diff**: the 23 FAILED nodes above are byte-identical to the M2 O-9
  baseline record (4691/23) and to the M3-start single-tenant baseline captured before wave 1 —
  zero new, zero fixed, zero on the operator surface. Passed count 4691 → 4835 = M3's added
  tests (adversarial matrices, H3 scenarios, bounds attacks, isolation matrix, required-key gate).
- **`exit=` caveat (whole-suite section only)**: that section's `exit=0` reflects the capture
  pipeline (grep), not pytest — pytest's own exit was nonzero as expected with the 23 known
  baseline failures. Per-row `exit=` values above ARE the real pytest/ruff exit codes.
- Code tree under review: `7c615a8`. This evidence file is committed immediately after capture as
  a docs-only delta; no source/test/schema file changes after capture.
- **K-M3-1 disposition (Karen, LOW)**: 5 of the 23 whole-suite failures (`test_pdf_extractor` ×3,
  `test_pdf_fixture_suite`, `test_search_router_pdf_wiring`) are a **worktree-venv gap** — `pypdf`
  absent from this worktree's `.venv` but present in the main checkout's; `pdf_extractor.py` is
  byte-identical across base/main/HEAD. True code-baseline failure count on a fully-provisioned
  venv is 18, not 23. Zero operator-surface impact either way.
