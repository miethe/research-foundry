---
schema_version: '0.1'
type: source_card
source_card_id: src_20260613_litellm_c5cef789
created_at: '2026-06-13T02:11:44-04:00'
created_by_agent: rf_source_carder
sensitivity: personal
source:
  title: litellm
  source_type: official_doc
  locator:
    url: null
    file_path: examples/sources/litellm.md
    doi: null
    repo: null
  authors: []
  publisher: null
  published_at: null
  accessed_at: '2026-06-13T02:11:44-04:00'
  version: null
trust:
  source_rank: unknown
  reliability_notes: Ingested deterministically; not yet reliability-rated.
  known_limitations: []
  conflicts_with: []
usage:
  allowed_for_public_output: false
  allowed_for_work_output: true
  allowed_for_personal_meatywiki: true
  citation_required: true
  quote_limit_notes: Quote short excerpts only; cite the source.
extracted_points:
- evidence_id: ev_001
  locator: para/1
  summary: LiteLLM supports routing strategies including cost-based and lowest-cost routing, and provider,
    model, and tag budgets.
  quote: |-
    LiteLLM supports routing strategies including cost-based and lowest-cost routing,
    and provider, model, and tag budgets. The router enforced a 1000-request budget
    in internal tests.
  supports_potential_claims:
  - clm_pending
---

# Source Card: litellm

## Summary

LiteLLM supports routing strategies including cost-based and lowest-cost routing, and provider, model, and tag budgets.

## Key evidence

- (ev_001) LiteLLM supports routing strategies including cost-based and lowest-cost routing, and provider, model, and tag budgets.

## Limitations

- None recorded.

## Related source cards
