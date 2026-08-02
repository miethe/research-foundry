/**
 * useBuilderClaimPreviews — mode-aware Report Builder claim-preview resolver.
 *
 * Fixes the defect in runs-viewer-builder-live-claim-previews.md: previously
 * BuilderBlockEditor.tsx, BuilderAuditInspector.tsx, and builderCoverage.ts
 * all called lib/builderMocks.ts's `resolveBuilderClaimPreview()`
 * UNCONDITIONALLY, so every real (loopback) claim resolved to `null` and
 * coverage/source-card/chip-text surfaces silently rendered as if the claim
 * didn't exist.
 *
 * OQ-1 resolution (logged per the contract's decision rule, not a blocker):
 * `ReportClaimLink.catalog_item_id` is the id-addressable key — confirmed by
 * reading reports.py's add_claim_link route (it persists catalog_item_id
 * verbatim) AND by a live `rf serve` smoke against the LAN node
 * (10.42.10.76:7432 /api/reports/rpt_20260710_untitled_report): every
 * observed claim_link on a real draft carries a non-null catalog_item_id.
 * So the correct call is the EXISTING `GET /catalog/items/{catalog_item_id}`
 * binding (`fetchCatalogItem()` in api/client.ts) — no new endpoint, no
 * search-by-claim-id fallback needed.
 *
 * Static mode: delegates to the synchronous BUILDER_MOCK_CLAIM_PREVIEWS
 * dictionary unchanged (AC-4) — this hook adds a mode branch, it does not
 * touch the mock behavior.
 *
 * Loopback mode: fetches one catalog item per distinct catalog_item_id
 * referenced by the draft's claim_links (via useQueries, so N distinct
 * claims cost N parallel GETs, not N re-renders). A claim link with no
 * catalog_item_id, a 404, or an item whose item_type isn't "claim"/
 * "inference" resolves to the literal string "unknown" — AC-3's explicit
 * unresolvable state, kept out of the low-confidence bucket and never
 * counted as covered by lib/builderCoverage.ts.
 */
import { useQueries } from "@tanstack/react-query";
import { fetchCatalogItem, isLoopbackEnabled } from "@/api/client";
import { catalogItemQueryKey } from "@/hooks/useCatalog";
import { CLAIM_PREVIEW_UNKNOWN, resolveBuilderClaimPreview } from "@/lib/builderMocks";
import type { BuilderClaimPreview, BuilderClaimPreviewOrUnknown, ClaimPreviewResolver } from "@/lib/builderMocks";
import type { RFResolvedSource } from "@/types/rf";
import type { CatalogItemDetail } from "@/types/rf/catalog";
import type { ReportClaimLink } from "@/types/rf/report_draft";

export { CLAIM_PREVIEW_UNKNOWN };
export type { BuilderClaimPreviewOrUnknown, ClaimPreviewResolver };

function isKnownStatus(v: unknown): v is BuilderClaimPreview["status"] {
  return (
    v === "supported" ||
    v === "mixed" ||
    v === "contradicted" ||
    v === "inference" ||
    v === "speculation" ||
    v === "unsupported"
  );
}

function isKnownConfidence(v: unknown): v is BuilderClaimPreview["confidence"] {
  return v === "high" || v === "medium" || v === "low";
}

function isKnownMateriality(v: unknown): v is BuilderClaimPreview["materiality"] {
  return v === "material" || v === "narrative" || v === "background";
}

/**
 * Maps a live `GET /catalog/items/{id}` response (post-normalizeCatalogItemDetail,
 * so payload.sources is already populated from cited_sources when absent) to
 * the Builder's BuilderClaimPreview shape, or "unknown" when the item can't
 * stand in for a claim preview (not found, or not a claim/inference item).
 */
function catalogItemToPreview(claimId: string, item: CatalogItemDetail | null): BuilderClaimPreviewOrUnknown {
  if (!item) return CLAIM_PREVIEW_UNKNOWN;
  if (item.item_type !== "claim" && item.item_type !== "inference") return CLAIM_PREVIEW_UNKNOWN;
  const payload = item.payload as { text?: unknown; materiality?: unknown; sources?: unknown };
  const text = typeof payload.text === "string" && payload.text.length > 0 ? payload.text : item.title;
  return {
    claim_id: claimId,
    text,
    status: isKnownStatus(item.status) ? item.status : "unsupported",
    // Fix pass (post-sprint defect): live catalog data has real `confidence:
    // null` rows — "medium" was a fabricated, non-conservative default that
    // presented an unscored claim as confidently middling AND escaped the
    // weak-confidence flag (medium !== "low"). "unknown" is the honest,
    // conservative answer, consistent with every other unrecognized-field
    // default in this function (status -> "unsupported", materiality ->
    // "material" are both fail-safe-toward-flagged, never fail-safe-toward-reassuring).
    confidence: isKnownConfidence(item.confidence) ? item.confidence : "unknown",
    materiality: isKnownMateriality(payload.materiality) ? payload.materiality : "material",
    sources: Array.isArray(payload.sources) ? (payload.sources as RFResolvedSource[]) : [],
  };
}

/**
 * Returns a synchronous `resolve(claimId)` function scoped to the given
 * claim_links. Callers (BuilderScreen.tsx) build this once from
 * `draft.claim_links` and thread it into builderCoverage.ts's functions and
 * the two Builder components that render claim previews — replacing their
 * previous direct, unconditional `resolveBuilderClaimPreview()` imports.
 */
export function useBuilderClaimPreviewResolver(claimLinks: ReportClaimLink[]): {
  resolve: ClaimPreviewResolver;
  isLoading: boolean;
} {
  const live = isLoopbackEnabled();

  const distinctByClaimId = new Map<string, string | null>();
  for (const link of claimLinks) {
    if (!distinctByClaimId.has(link.claim_id)) distinctByClaimId.set(link.claim_id, link.catalog_item_id ?? null);
  }
  const entries = Array.from(distinctByClaimId.entries());

  const queries = useQueries({
    queries: live
      ? entries.map(([, catalogItemId]) => ({
          queryKey: catalogItemQueryKey(catalogItemId ?? ""),
          queryFn: () => fetchCatalogItem(catalogItemId as string),
          enabled: Boolean(catalogItemId),
          staleTime: 60_000,
        }))
      : [],
  });

  if (!live) {
    return {
      resolve: (claimId: string) => resolveBuilderClaimPreview(claimId) ?? CLAIM_PREVIEW_UNKNOWN,
      isLoading: false,
    };
  }

  const resolved = new Map<string, BuilderClaimPreviewOrUnknown>();
  let anyLoading = false;
  entries.forEach(([claimId, catalogItemId], i) => {
    if (!catalogItemId) {
      resolved.set(claimId, CLAIM_PREVIEW_UNKNOWN);
      return;
    }
    const q = queries[i];
    if (q.isPending) {
      // Not yet settled — leave absent from `resolved`; resolve() below falls
      // back to "unknown" for the brief window before the fetch completes,
      // rather than fabricating a preview.
      anyLoading = true;
      return;
    }
    resolved.set(claimId, catalogItemToPreview(claimId, q.data ?? null));
  });

  return {
    resolve: (claimId: string) => resolved.get(claimId) ?? CLAIM_PREVIEW_UNKNOWN,
    isLoading: anyLoading,
  };
}
