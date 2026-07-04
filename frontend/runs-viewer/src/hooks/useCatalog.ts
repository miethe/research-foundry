/**
 * useCatalog — React Query hooks for the Evidence Catalog (public-multiuser-p0p1, Phase 1).
 *
 * Dual-mode aware via src/api/client.ts's fetchCatalogStats/fetchCatalogSearch/
 * fetchCatalogItem (loopback → /api/catalog/*; static → client-built index).
 */
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { fetchCatalogItem, fetchCatalogSearch, fetchCatalogStats } from "@/api/client";
import type { CatalogItemDetail, CatalogSearchParams, CatalogSearchResult, CatalogStats } from "@/types/rf/catalog";

// ── Stats ─────────────────────────────────────────────────────────────────────

export const catalogStatsQueryKey = ["rf", "catalog", "stats"] as const;

export function useCatalogStats() {
  return useQuery<CatalogStats, Error>({
    queryKey: catalogStatsQueryKey,
    queryFn: fetchCatalogStats,
    staleTime: 60_000,
  });
}

// ── Search ────────────────────────────────────────────────────────────────────

export function catalogSearchQueryKey(params: CatalogSearchParams) {
  return ["rf", "catalog", "search", params] as const;
}

/**
 * Search hook with keepPreviousData UX: switching tabs/filters/pages keeps
 * showing the last page while the next one loads, instead of flashing an
 * empty/loading state on every keystroke or click.
 */
export function useCatalogSearch(params: CatalogSearchParams) {
  return useQuery<CatalogSearchResult, Error>({
    queryKey: catalogSearchQueryKey(params),
    queryFn: () => fetchCatalogSearch(params),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });
}

// ── Item detail ───────────────────────────────────────────────────────────────

export function catalogItemQueryKey(catalogItemId: string) {
  return ["rf", "catalog", "item", catalogItemId] as const;
}

export function useCatalogItem(catalogItemId: string | null | undefined) {
  return useQuery<CatalogItemDetail | null, Error>({
    queryKey: catalogItemQueryKey(catalogItemId ?? ""),
    queryFn: () => fetchCatalogItem(catalogItemId as string),
    enabled: Boolean(catalogItemId),
    staleTime: 60_000,
  });
}
