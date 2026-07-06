/**
 * RF Evidence Catalog Types — Phase 1 shared read model (public-multiuser-p0p1).
 *
 * Mirrors the backend contract defined in:
 *   docs/project_plans/implementation_plans/public-multiuser-p0p1-plan.md
 *   (§ "Backend deliverables (Wave B)" — catalog_service.py / api/routers/catalog.py)
 *
 * These types are shared by both transport modes:
 *   - Loopback mode: literal shape of GET /api/catalog/{stats,search,items/:id}
 *   - Static mode:   shape produced by src/lib/catalog.ts (buildCatalogIndex +
 *                    searchCatalog + catalogStats), which implements the SAME
 *                    item-mapping table as the backend importer so the two
 *                    modes are behaviorally equivalent.
 */

import type { RFClaimConfidence, RFSensitivity } from "./run-export.js";

// ── Report Anchors (P2 Wave C) ────────────────────────────────────────────────
//
// Canonical definition lives in run-export.ts (report_anchors is a field of
// RFRunExport / run.json §16) — re-exported here because the D4 report→claim
// link parity logic that consumes them lives in ./catalog.ts (lib/catalog.ts),
// not run-export.ts. Re-exporting (rather than duplicating) keeps a single
// source of truth and avoids a run-export.ts -> catalog.ts import cycle.
export type {
  RFReportAnchorBlock,
  RFReportAnchorClaimLink,
  RFReportAnchorRelation,
} from "./run-export.js";

// ── Item type ────────────────────────────────────────────────────────────────

/**
 * The six catalog item kinds, per the import contract mapping table:
 *   claims[] (non-inference)      → "claim"
 *   claims[] (inference_basis set) → "inference"
 *   claims[*].sources[] (resolved) → "source"
 *   report_draft != null           → "report"  (one per run)
 *   reusable_output_candidates[]   → "reusable_output"
 *   writebacks.targets[]           → "writeback"
 */
export type CatalogItemType =
  | "claim"
  | "source"
  | "inference"
  | "report"
  | "reusable_output"
  | "writeback";

// ── Summary (list/search row) ─────────────────────────────────────────────────

export interface CatalogItemSummary {
  catalog_item_id: string;
  item_type: CatalogItemType;
  title: string;
  summary: string | null;
  run_id: string;
  /** Run-local ID (claim_id / source_card_id / synthetic index ref) preserved as an alias — spec §6. */
  local_ref: string;
  project: string | null;
  status: string | null;
  sensitivity: RFSensitivity | null;
  trust_label: string | null;
  /** Raw confidence label for claim/inference items, as returned by the API; null otherwise. */
  confidence: RFClaimConfidence | null;
  source_count: number;
  created_at: string | null;
  updated_at: string | null;
}

// ── Link (provenance edge) ────────────────────────────────────────────────────

/** One end of a directed provenance edge, as returned by GET /api/catalog/items/{id}. */
export interface CatalogLinkEdge {
  catalog_item_id: string;
  relation: string;
}

/** Outgoing + incoming directed provenance edges for a catalog item. */
export interface CatalogItemLinks {
  outgoing: CatalogLinkEdge[];
  incoming: CatalogLinkEdge[];
}

// ── Detail (single-item fetch) ────────────────────────────────────────────────

export interface CatalogItemDetail extends CatalogItemSummary {
  /** Item-type-specific extra fields (claim text/materiality, source trust/usage, report draft, etc.). */
  payload: Record<string, unknown>;
  links: CatalogItemLinks;
}

// ── Search ────────────────────────────────────────────────────────────────────

export type CatalogSortKey = "updated" | "title" | "confidence";

export interface CatalogSearchParams {
  q?: string;
  item_type?: CatalogItemType;
  project?: string;
  status?: string;
  sensitivity?: RFSensitivity | string;
  run_id?: string;
  sort?: CatalogSortKey;
  page?: number;
  page_size?: number;
}

export interface CatalogSearchFacets {
  projects: string[];
  statuses: string[];
  sensitivities: string[];
}

export interface CatalogSearchResult {
  items: CatalogItemSummary[];
  total: number;
  page: number;
  page_size: number;
  facets: CatalogSearchFacets;
}

// ── Stats ─────────────────────────────────────────────────────────────────────

export interface CatalogStats {
  counts: Record<CatalogItemType, number>;
  runs_indexed: number;
  last_import_at: string | null;
}
