---
schema_version: '0.1'
type: source_card
source_card_id: src_20260626_temporal_deterministic_workflow_replay_9a591445
created_at: '2026-06-26T10:18:34-04:00'
created_by_agent: rf_source_carder
sensitivity: personal
source:
  title: Temporal deterministic workflow replay
  source_type: official_doc
  locator:
    url: https://docs.temporal.io/workflow-definition
    file_path: null
    doi: null
    repo: null
  authors: []
  publisher: null
  published_at: null
  accessed_at: '2026-06-26T10:18:34-04:00'
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
  summary: Temporal Workflow Definition | Temporal Platform Documentation
  quote: Temporal Workflow Definition | Temporal Platform Documentation
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_002
  locator: para/2
  summary: Skip to main content Home Courses SDKs AI Cookbook Code Exchange Temporal Cloud Ask AI Search
    Home Quickstarts Evaluate Develop Temporal Cloud Deploy to production CLI (temporal) References Troublesho
  quote: null
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_003
  locator: para/3
  summary: What is a Workflow Definition?
  quote: "What is a Workflow Definition?  \n  Determinism and constraints  \n  Handling code changes and\
    \ non-deterministic behavior  \n  Intrinsic non-determinism logic  \n  Versioning Workflow code and\
    \ Patching  \n  Handling unreliable Worker Processes  \n  What is a Workflow Type?"
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_004
  locator: para/4
  summary: A Temporal Workflow defines the overall flow of the application.
  quote: null
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_005
  locator: para/5
  summary: The input parameters, return values, and execution timeouts of Child Workflows and Activities
  quote: The input parameters, return values, and execution timeouts of Child Workflows and Activities
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_006
  locator: para/6
  summary: However, it is not safe to change the types or IDs of Child Workflows or Activities
  quote: However, it is not safe to change the types or IDs of Child Workflows or Activities
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_007
  locator: para/7
  summary: The input parameters used to Signal an external Workflow The duration of Timers (although changing
    them to 0 is not safe in all SDKs) Add or remove calls to Workflow APIs that don't produce Commands
    (
  quote: null
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_008
  locator: para/8
  summary: 'The following Workflow API calls all can produce Commands, and thus must not be reordered,
    added, or removed without proper Versioning techniques :'
  quote: 'The following Workflow API calls all can produce Commands, and thus must not be reordered, added,
    or removed without proper  Versioning techniques :'
  supports_potential_claims:
  - clm_pending
---

# Source Card: Temporal deterministic workflow replay

## Summary

Temporal Workflow Definition | Temporal Platform Documentation Skip to main content Home Courses SDKs AI Cookbook Code Exchange Temporal Cloud Ask AI Search Home Quickstarts Evaluate Develop Temporal

## Key evidence

- (ev_001) Temporal Workflow Definition | Temporal Platform Documentation
- (ev_002) Skip to main content Home Courses SDKs AI Cookbook Code Exchange Temporal Cloud Ask AI Search Home Quickstarts Evaluate Develop Temporal Cloud Deploy to production CLI (temporal) References Troublesho
- (ev_003) What is a Workflow Definition?
- (ev_004) A Temporal Workflow defines the overall flow of the application.
- (ev_005) The input parameters, return values, and execution timeouts of Child Workflows and Activities
- (ev_006) However, it is not safe to change the types or IDs of Child Workflows or Activities
- (ev_007) The input parameters used to Signal an external Workflow The duration of Timers (although changing them to 0 is not safe in all SDKs) Add or remove calls to Workflow APIs that don't produce Commands (
- (ev_008) The following Workflow API calls all can produce Commands, and thus must not be reordered, added, or removed without proper Versioning techniques :

## Limitations

- None recorded.

## Related source cards
