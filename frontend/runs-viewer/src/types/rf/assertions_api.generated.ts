/** Generated from src/research_foundry/api/openapi.json. Do not edit manually. */
export type AssertionSearchCursor = string | null;

export interface AssertionSearchRequest {
  q?: string | null;
  lifecycle_state?: string | null;
  access_scope?: string | null;
  limit?: number;
  cursor?: AssertionSearchCursor;
}

export interface RightsDecision {
  allowed: boolean;
  reason_code: string;
}

export interface AssertionSummary {
  assertion_id: string;
  assertion_version: number;
  lifecycle_state: string;
  access_scope: string;
  rights_decision: RightsDecision;
}

export interface AssertionFacets {
  lifecycle_states: Array<string>;
  access_scopes: Array<string>;
}

export interface AssertionSearchResponse {
  items: Array<AssertionSummary>;
  next_cursor: AssertionSearchCursor;
  facets: AssertionFacets;
  denial_reason: string | null;
}

export interface EvidencePacket {
  packet_version: string;
  assertion_id: string;
  assertion_version: number;
  assertion: Record<string, unknown>;
  passage: Record<string, unknown>;
  source_edition: Record<string, unknown>;
  qualifiers: Record<string, unknown>;
  qualifier_extensions: Record<string, unknown>;
  evaluations: Array<Record<string, unknown>>;
  freshness: Record<string, unknown>;
  access_scope: string;
  rights_decision: RightsDecision;
  relationships: Array<Record<string, unknown>>;
  run_uses: Array<string>;
  report_uses: Array<string>;
}

export interface AssertionLineage {
  assertion_id: string;
  assertion_version: number;
  relationships: Array<Record<string, unknown>>;
  run_uses: Array<string>;
  report_uses: Array<string>;
  denial_reason: string | null;
}

export interface AssertionImpactAction {
  object_id: string;
  object_class: string;
  action: string;
  status: "pending" | "completed" | "failed" | "blocked";
  writeback_status?: "default_denied" | "denied" | "queued" | null;
}

export interface AssertionImpactSummary {
  event_id: string;
  assertion_id: string;
  lifecycle_state: string;
  access_scope: string;
  authoritative_reuse_blocked: true;
  operation_status: "pending" | "blocked" | "completed";
  reason_code?: string | null;
  replacement_edition_id?: string | null;
  resumable: boolean;
  actions: Array<AssertionImpactAction>;
}

export interface AssertionImpactReasonDetail {
  reason_code: string;
}

export interface AssertionImpactReasonResponse {
  detail: AssertionImpactReasonDetail;
}

/** A rights-denied search result uses the normal response envelope with no results. */
export interface AssertionSearchDenialResponse {
  items: Array<never>;
  next_cursor: null;
  facets: AssertionFacets;
  denial_reason: string;
}
