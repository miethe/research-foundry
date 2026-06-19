/**
 * useRunDetail — React Query hook for the full denormalized run.json document.
 *
 * Returns the complete RFRunExport for a given runId, including the full
 * claim graph with resolved sources. Disabled when runId is falsy.
 */
import { useQuery } from "@tanstack/react-query";
import { fetchRunDetail } from "@/api/client";
import type { RFRunExport } from "@/types/rf";

export const runDetailQueryKey = (runId: string) =>
  ["rf", "runs", "detail", runId] as const;

export function useRunDetail(runId: string) {
  return useQuery<RFRunExport, Error>({
    queryKey: runDetailQueryKey(runId),
    queryFn:  () => fetchRunDetail(runId),
    enabled:  Boolean(runId),
    staleTime: 60_000,
  });
}
