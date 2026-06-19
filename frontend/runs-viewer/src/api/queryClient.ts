/**
 * Shared TanStack Query client for the RF Runs Viewer.
 *
 * GET-only viewer: no mutation retry needed. Stale time is generous because
 * run.json exports are immutable snapshots — they change only when the user
 * re-exports.
 */
import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,       // 1 minute — exports are stable snapshots
      gcTime: 10 * 60_000,     // 10 minutes GC
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});
