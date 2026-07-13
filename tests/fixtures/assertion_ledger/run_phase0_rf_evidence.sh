#!/bin/zsh
# Rebuild the local-only RF evidence run for reusable-assertion-ledger Phase 0.
# This deliberately uses no network fetch, discovery, bundle, publish, or writeback.
set -euo pipefail

run_id="rf_run_reusable_assertion_ledger_p0_fixture_v1"
source_file="tests/fixtures/assertion_ledger/phase0_rf_evidence_source.md"
metrics_source_file="tests/fixtures/assertion_ledger/phase0_rf_metrics_source.md"

./.venv/bin/rf guard check --profile default
mkdir -p "runs/${run_id}"
./.venv/bin/rf ingest "${source_file}" --run "${run_id}" --source-type personal_note --sensitivity personal --title "Reusable Assertion Ledger Phase 0 Fixture Evidence" --no-fetch
./.venv/bin/rf ingest "${metrics_source_file}" --run "${run_id}" --source-type personal_note --sensitivity personal --title "Reusable Assertion Ledger Phase 0 Fixture Metrics" --no-fetch
./.venv/bin/python tests/fixtures/assertion_ledger/enrich_phase0_rf_source_cards.py "runs/${run_id}/sources"
./.venv/bin/rf extract "${run_id}" --model-profile rf_extract_cheap
./.venv/bin/rf claim-map "${run_id}"
./.venv/bin/rf synthesize "${run_id}" --deterministic
./.venv/bin/rf verify "${run_id}" --fail-on-unsupported
