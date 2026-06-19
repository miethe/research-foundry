/**
 * useSourceCard — React Query hook for a single resolved source card.
 *
 * Returns the first RFResolvedSource matching the given sourceCardId within
 * the run's claim graph. Returns null when not found (not an error).
 */
import { useQuery } from "@tanstack/react-query";
import { fetchSourceCard } from "@/api/client";
import type { RFResolvedSource } from "@/types/rf";

export const sourceCardQueryKey = (runId: string, sourceCardId: string) =>
  ["rf", "runs", "source", runId, sourceCardId] as const;

export function useSourceCard(runId: string, sourceCardId: string) {
  return useQuery<RFResolvedSource | null, Error>({
    queryKey: sourceCardQueryKey(runId, sourceCardId),
    queryFn:  () => fetchSourceCard(runId, sourceCardId),
    enabled:  Boolean(runId) && Boolean(sourceCardId),
    staleTime: 60_000,
  });
}
