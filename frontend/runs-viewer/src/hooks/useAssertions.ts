/**
 * Governed assertion query seam (P6-001).
 *
 * This module intentionally consumes only the generated assertion API DTOs.
 * It translates transport/query outcomes into display-safe discriminants; UI
 * surfaces must not infer missing facts from packet maps or lifecycle strings.
 */
import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import {
  ClientError,
  fetchAssertionImpact,
  fetchAssertionLineage,
  fetchAssertionSearch,
  fetchEvidencePacket,
} from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { safeReasonCopy } from "@/lib/assertionReasonCopy";
import type {
  AssertionImpactAction,
  AssertionImpactSummary,
  AssertionLineage,
  AssertionSearchRequest,
  AssertionSearchResponse,
  EvidencePacket,
} from "@/types/rf/assertions_api.generated";

export { assertionReasonCopy, safeReasonCopy } from "@/lib/assertionReasonCopy";

export type AssertionScope = {
  workspaceId: string;
  authScope: string;
  resolved: boolean;
};

export type AssertionViewState<T> =
  | { kind: "loading" }
  | { kind: "denied"; reasonCode: string; reasonCopy: string }
  | { kind: "legacy-missing"; data: T; missingFields: readonly string[] }
  | { kind: "stale"; data: T; reasonCode?: string }
  | { kind: "invalid"; data: T; rawValue: string }
  | { kind: "unavailable"; rawValue?: string; data?: T; zeroCounts?: true }
  | { kind: "error-with-retry"; error: Error; retry: () => Promise<unknown> }
  | { kind: "ready"; data: T };

export type AssertionSubjectViewModel =
  | { kind: "source-assertion"; assertion: Record<string, unknown> }
  | { kind: "inference"; inference: Record<string, unknown> }
  | { kind: "unavailable"; rawValue?: string };

const KNOWN_LIFECYCLE_STATES = new Set(["eligible", "stale", "invalidated", "tombstoned", "blocked"]);
const KNOWN_OPERATION_STATUSES = new Set(["pending", "blocked", "completed", "interrupted"]);
const KNOWN_ACTION_STATUSES = new Set(["pending", "completed", "failed", "blocked"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

/** Defensive object-map selector for generated packet fields. */
export function selectPacketObject(
  packet: EvidencePacket,
  field: "assertion" | "passage" | "source_edition" | "qualifiers" | "qualifier_extensions" | "freshness",
): Record<string, unknown> | undefined {
  const value: unknown = (packet as unknown as Record<string, unknown>)[field];
  return isRecord(value) ? value : undefined;
}

/**
 * Reads the packet lifecycle from its authoritative nested assertion record.
 * Current packets mirror this value in freshness; use that mirror only when
 * the assertion record does not provide a string value.
 */
export function selectPacketLifecycle(packet: EvidencePacket): string | undefined {
  const assertionLifecycle = selectPacketObject(packet, "assertion")?.lifecycle_state;
  if (typeof assertionLifecycle === "string") return assertionLifecycle;

  const freshnessLifecycle = selectPacketObject(packet, "freshness")?.lifecycle_state;
  return typeof freshnessLifecycle === "string" ? freshnessLifecycle : undefined;
}

/** Defensive array selector; malformed map values never reach a renderer. */
export function selectPacketRelationships(packet: EvidencePacket): readonly Record<string, unknown>[] {
  const value: unknown = (packet as unknown as Record<string, unknown>).relationships;
  return Array.isArray(value) ? value.filter(isRecord) : [];
}

/** Keeps additive packet fields field-granular instead of invalidating the packet. */
export function selectLegacyMissingFields(packet: EvidencePacket): readonly string[] {
  const fields = ["passage", "source_edition", "qualifiers", "qualifier_extensions", "freshness"] as const;
  return fields.filter((field) => selectPacketObject(packet, field) === undefined);
}

/** Source assertions and inferences intentionally cannot share a display kind. */
export function selectPacketSubject(packet: EvidencePacket): AssertionSubjectViewModel {
  const assertion = selectPacketObject(packet, "assertion");
  if (!assertion) return { kind: "unavailable" };
  const rawKind = assertion.kind ?? assertion.record_type ?? assertion.type;
  if (rawKind === "inference") return { kind: "inference", inference: assertion };
  if (rawKind === undefined || rawKind === "source_assertion" || rawKind === "source-assertion") {
    return { kind: "source-assertion", assertion };
  }
  return { kind: "unavailable", rawValue: String(rawKind) };
}

function useAssertionScope(): AssertionScope {
  // auth_mode=none is already resolved public/static viewer context. Any other
  // mode requires a resolved identity before a governed request may begin.
  const auth = useAuth();
  const resolved = !auth.isLoading && (auth.authMode === "none" || auth.identity !== null);
  return {
    workspaceId: auth.identity?.workspace_id ?? "public",
    authScope: auth.identity ? `${auth.identity.user_id}:${auth.identity.roles.join(",")}` : auth.authMode,
    resolved,
  };
}

function queryState<T>(
  query: UseQueryResult<T, Error>,
  scope: AssertionScope,
  derive: (data: T) => AssertionViewState<T>,
): AssertionViewState<T> {
  if (!scope.resolved || query.isPending) return { kind: "loading" };
  if (query.isError) {
    const error = query.error;
    if (error instanceof ClientError && error.status === 403) {
      const reasonCode = error.reasonCode ?? "access_denied";
      return { kind: "denied", reasonCode, reasonCopy: safeReasonCopy(reasonCode) };
    }
    if (error instanceof ClientError && error.status === 404) {
      return { kind: "unavailable", rawValue: "not_found_or_unavailable" };
    }
    return { kind: "error-with-retry", error, retry: () => query.refetch() };
  }
  if (!query.data) return { kind: "loading" };
  return derive(query.data);
}

function packetState(packet: EvidencePacket): AssertionViewState<EvidencePacket> {
  const lifecycleState = selectPacketLifecycle(packet);
  if (lifecycleState === undefined || !KNOWN_LIFECYCLE_STATES.has(lifecycleState)) {
    return { kind: "unavailable", rawValue: lifecycleState, data: packet };
  }
  if (lifecycleState === "stale") return { kind: "stale", data: packet };
  if (lifecycleState === "invalidated" || lifecycleState === "tombstoned") {
    return { kind: "invalid", data: packet, rawValue: lifecycleState };
  }
  const missingFields = selectLegacyMissingFields(packet);
  return missingFields.length ? { kind: "legacy-missing", data: packet, missingFields } : { kind: "ready", data: packet };
}

function lineageState(lineage: AssertionLineage): AssertionViewState<AssertionLineage> {
  if (lineage.denial_reason) {
    return { kind: "denied", reasonCode: lineage.denial_reason, reasonCopy: safeReasonCopy(lineage.denial_reason) };
  }
  return { kind: "ready", data: lineage };
}

function impactState(impact: AssertionImpactSummary): AssertionViewState<AssertionImpactSummary> {
  if (!KNOWN_LIFECYCLE_STATES.has(impact.lifecycle_state)) {
    return { kind: "unavailable", rawValue: impact.lifecycle_state, data: impact, zeroCounts: true };
  }
  const operationStatus: string = impact.operation_status;
  if (!KNOWN_OPERATION_STATUSES.has(operationStatus)) {
    return { kind: "unavailable", rawValue: operationStatus, data: impact, zeroCounts: true };
  }
  const unknownAction = impact.actions.find((action: AssertionImpactAction) => !KNOWN_ACTION_STATUSES.has(action.status));
  if (unknownAction) return { kind: "unavailable", rawValue: unknownAction.status, data: impact, zeroCounts: true };
  if (operationStatus === "interrupted" || impact.lifecycle_state === "stale") {
    return { kind: "stale", data: impact, reasonCode: impact.reason_code ?? undefined };
  }
  return { kind: "ready", data: impact };
}

export function assertionSearchQueryKey(scope: AssertionScope, request: AssertionSearchRequest) {
  return ["rf", "assertions", "search", scope.workspaceId, scope.authScope, request] as const;
}

export function assertionPacketQueryKey(scope: AssertionScope, assertionId: string) {
  return ["rf", "assertions", "packet", scope.workspaceId, scope.authScope, assertionId] as const;
}

export function assertionLineageQueryKey(scope: AssertionScope, assertionId: string) {
  return ["rf", "assertions", "lineage", scope.workspaceId, scope.authScope, assertionId] as const;
}

export function assertionImpactQueryKey(scope: AssertionScope, assertionId: string) {
  return ["rf", "assertions", "impact", scope.workspaceId, scope.authScope, assertionId] as const;
}

export function useAssertionSearch(request: AssertionSearchRequest = {}) {
  const scope = useAssertionScope();
  const query = useQuery<AssertionSearchResponse, Error>({
    queryKey: assertionSearchQueryKey(scope, request),
    queryFn: () => fetchAssertionSearch(request),
    enabled: scope.resolved,
    retry: false,
  });
  const state = useMemo(() => queryState(query, scope, (data) => (
    data.denial_reason
      ? { kind: "denied", reasonCode: data.denial_reason, reasonCopy: safeReasonCopy(data.denial_reason) }
      : { kind: "ready", data }
  )), [query, scope]);
  return { ...query, scope, state };
}

export function useEvidencePacket(assertionId: string | null | undefined, onDenied?: () => void) {
  const scope = useAssertionScope();
  const query = useQuery<EvidencePacket, Error>({
    queryKey: assertionPacketQueryKey(scope, assertionId ?? ""),
    queryFn: () => fetchEvidencePacket(assertionId as string),
    enabled: scope.resolved && Boolean(assertionId),
    retry: false,
  });
  const state = useMemo(() => queryState(query, scope, packetState), [query, scope]);
  useEffect(() => {
    if (state.kind === "denied") onDenied?.();
  }, [onDenied, state.kind]);
  return { ...query, scope, state };
}

export function useAssertionLineage(assertionId: string | null | undefined) {
  const scope = useAssertionScope();
  const query = useQuery<AssertionLineage, Error>({
    queryKey: assertionLineageQueryKey(scope, assertionId ?? ""),
    queryFn: () => fetchAssertionLineage(assertionId as string),
    enabled: scope.resolved && Boolean(assertionId),
    retry: false,
  });
  return { ...query, scope, state: useMemo(() => queryState(query, scope, lineageState), [query, scope]) };
}

export function useAssertionImpact(assertionId: string | null | undefined) {
  const scope = useAssertionScope();
  const query = useQuery<AssertionImpactSummary, Error>({
    queryKey: assertionImpactQueryKey(scope, assertionId ?? ""),
    queryFn: () => fetchAssertionImpact(assertionId as string),
    enabled: scope.resolved && Boolean(assertionId),
    retry: false,
  });
  const state = useMemo(() => {
    if (query.isError && query.error instanceof ClientError && query.error.status === 404) {
      return {
        kind: "unavailable" as const,
        rawValue: query.error.reasonCode ?? "impact_unavailable",
        zeroCounts: true as const,
      };
    }
    const result = queryState(query, scope, impactState);
    return result;
  }, [query, scope]);
  return { ...query, scope, state };
}

/** Clear selected assertion/candidate-derived query state when the scope changes. */
export function useClearAssertionStateOnWorkspaceChange(clearSelection: () => void): void {
  const scope = useAssertionScope();
  const queryClient = useQueryClient();
  const previousScope = useRef<string | undefined>(undefined);
  // This must happen before passive query effects. Otherwise a lineage or
  // audit component can briefly issue the old assertion ID under the newly
  // resolved workspace/auth scope before its local selection is cleared.
  useLayoutEffect(() => {
    const currentScope = scope.resolved ? `${scope.workspaceId}:${scope.authScope}` : undefined;
    if (previousScope.current !== undefined && currentScope !== previousScope.current) {
      clearSelection();
      queryClient.removeQueries({ queryKey: ["rf", "assertions"] });
    }
    previousScope.current = currentScope;
  }, [clearSelection, queryClient, scope.authScope, scope.resolved, scope.workspaceId]);
}
