---
schema_version: 0.1
type: source_card
source_card_id: {{source_card_id}}
created_at: {{created_at}}
created_by_agent: rf_source_carder
sensitivity: {{sensitivity}}

source:
  title: {{title}}
  source_type: {{source_type}}
  locator:
    url: {{url}}
    file_path: {{file_path}}
    doi: {{doi}}
    repo: {{repo}}
  authors:
    - {{author_1}}
  publisher: {{publisher}}
  published_at: {{published_at}}
  accessed_at: {{accessed_at}}
  version: {{version}}

trust:
  source_rank: {{source_rank}}
  reliability_notes: {{reliability_notes}}
  known_limitations:
    - {{known_limitation_1}}
  conflicts_with:
    - source_card_id: {{conflicts_with_source_card_id}}
      reason: {{conflicts_with_reason}}

usage:
  allowed_for_public_output: {{allowed_for_public_output}}
  allowed_for_work_output: {{allowed_for_work_output}}
  allowed_for_personal_meatywiki: {{allowed_for_personal_meatywiki}}
  citation_required: true
  quote_limit_notes: {{quote_limit_notes}}

extracted_points:
  - evidence_id: ev_001
    locator: "{{ev_001_locator}}"
    summary: {{ev_001_summary}}
    quote: {{ev_001_quote}}
    supports_potential_claims:
      - clm_pending
---
# Source Card: {{title}}

## Summary

{{summary}}

## Key evidence

- [ev_001] {{ev_001_summary}}

## Limitations

- {{known_limitation_1}}

## Related source cards

- {{related_source_card_id}}
