/**
 * useClaimLedger — React Query hook for a run's denormalized claim array.
 *
 * Returns the claims[] array from the run's full export. For the static
 * fixture this is extracted client-side; for loopback mode the API may
 * expose a dedicated /claims endpoint.
 */
import { useQuery } from "@tanstack/react-query";
import { fetchClaimLedger } from "@/api/client";
import type { RFClaim } from "@/types/rf";

export const claimLedgerQueryKey = (runId: string) =>
  ["rf", "runs", "claims", runId] as const;

export function useClaimLedger(runId: string) {
  return useQuery<RFClaim[], Error>({
    queryKey: claimLedgerQueryKey(runId),
    queryFn:  () => fetchClaimLedger(runId),
    enabled:  Boolean(runId),
    staleTime: 60_000,
  });
}
