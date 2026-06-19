/**
 * useRunList — React Query hook for the RF run list.
 *
 * Returns all available run summaries (status_derived, claim_counts, etc.)
 * sourced from the static fixture or loopback API depending on the
 * VITE_RUNS_FRONTEND_LOOPBACK_API env flag.
 */
import { useQuery } from "@tanstack/react-query";
import { fetchRunList } from "@/api/client";
import type { RFRunSummary } from "@/types/rf";

export const runListQueryKey = ["rf", "runs", "list"] as const;

export function useRunList() {
  return useQuery<RFRunSummary[], Error>({
    queryKey: runListQueryKey,
    queryFn:  fetchRunList,
    staleTime: 60_000,
  });
}
