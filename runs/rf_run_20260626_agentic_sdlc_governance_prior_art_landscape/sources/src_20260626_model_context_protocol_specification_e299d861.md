---
schema_version: '0.1'
type: source_card
source_card_id: src_20260626_model_context_protocol_specification_e299d861
created_at: '2026-06-26T10:18:31-04:00'
created_by_agent: rf_source_carder
sensitivity: personal
source:
  title: Model Context Protocol specification
  source_type: standard
  locator:
    url: https://modelcontextprotocol.io/specification/2025-06-18
    file_path: null
    doi: null
    repo: null
  authors: []
  publisher: null
  published_at: null
  accessed_at: '2026-06-26T10:18:31-04:00'
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
  summary: 'Specification - Model Context Protocol Documentation Index Fetch the complete documentation
    index at: /llms.txt Use this file to discover all available pages before exploring further.'
  quote: null
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_002
  locator: para/2
  summary: Share contextual information with language models Expose tools and capabilities to AI systems
    Build composable integrations and workflows
  quote: "Share contextual information with language models \n Expose tools and capabilities to AI systems\
    \ \n Build composable integrations and workflows"
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_003
  locator: para/3
  summary: 'The protocol uses JSON-RPC 2.0 messages to establish communication between:'
  quote: |-
    The protocol uses  JSON-RPC  2.0 messages to establish
    communication between:
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_004
  locator: para/4
  summary: 'Hosts : LLM applications that initiate connections Clients : Connectors within the host application
    Servers : Services that provide context and capabilities'
  quote: "Hosts : LLM applications that initiate connections \n  Clients : Connectors within the host\
    \ application \n  Servers : Services that provide context and capabilities"
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_005
  locator: para/5
  summary: MCP takes some inspiration from the Language Server Protocol , which standardizes how to add
    support for programming languages across a whole ecosystem of development tools.
  quote: null
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_006
  locator: para/6
  summary: JSON-RPC message format Stateful connections Server and client capability negotiation
  quote: "JSON-RPC  message format \n Stateful connections \n Server and client capability negotiation"
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_007
  locator: para/7
  summary: '​ Features Servers offer any of the following features to clients:'
  quote: "​         Features  \n Servers offer any of the following features to clients:"
  supports_potential_claims:
  - clm_pending
- evidence_id: ev_008
  locator: para/8
  summary: 'Resources : Context and data, for the user or the AI model to use Prompts : Templated messages
    and workflows for users Tools : Functions for the AI model to execute'
  quote: "Resources : Context and data, for the user or the AI model to use \n  Prompts : Templated messages\
    \ and workflows for users \n  Tools : Functions for the AI model to execute"
  supports_potential_claims:
  - clm_pending
---

# Source Card: Model Context Protocol specification

## Summary

Specification - Model Context Protocol Documentation Index Fetch the complete documentation index at: /llms.txt Use this file to discover all available pages before exploring further.

## Key evidence

- (ev_001) Specification - Model Context Protocol Documentation Index Fetch the complete documentation index at: /llms.txt Use this file to discover all available pages before exploring further.
- (ev_002) Share contextual information with language models Expose tools and capabilities to AI systems Build composable integrations and workflows
- (ev_003) The protocol uses JSON-RPC 2.0 messages to establish communication between:
- (ev_004) Hosts : LLM applications that initiate connections Clients : Connectors within the host application Servers : Services that provide context and capabilities
- (ev_005) MCP takes some inspiration from the Language Server Protocol , which standardizes how to add support for programming languages across a whole ecosystem of development tools.
- (ev_006) JSON-RPC message format Stateful connections Server and client capability negotiation
- (ev_007) ​ Features Servers offer any of the following features to clients:
- (ev_008) Resources : Context and data, for the user or the AI model to use Prompts : Templated messages and workflows for users Tools : Functions for the AI model to execute

## Limitations

- None recorded.

## Related source cards
