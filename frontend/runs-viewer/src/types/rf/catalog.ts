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

import type { RFSensitivity } from "./run-export.js";

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
  /** Normalized 0-1 confidence, derived from RFClaimConfidence for claim/inference items; null otherwise. */
  confidence: number | null;
  source_count: number;
  created_at: string | null;
  updated_at: string | null;
}

// ── Link (provenance edge) ────────────────────────────────────────────────────

/**
 * One directed provenance edge, stored on the "from" item's `links` array.
 * Per the import contract's Links table:
 *   claim → source      (rel "supports")
 *   inference → claim   (rel "inferred_from")
 *   report → claim      (rel "contains")
 */
export interface CatalogLink {
  rel: string;
  target_catalog_item_id: string;
  target_item_type: CatalogItemType;
}

// ── Detail (single-item fetch) ────────────────────────────────────────────────

export interface CatalogItemDetail extends CatalogItemSummary {
  /** Item-type-specific extra fields (claim text/materiality, source trust/usage, report draft, etc.). */
  payload: Record<string, unknown>;
  links: CatalogLink[];
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
