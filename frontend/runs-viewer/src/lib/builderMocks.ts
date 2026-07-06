/**
 * Builder mock fixtures — public-multiuser-p2p3, Phase 3 / Wave F.
 *
 * The Report Builder is LOOPBACK-ONLY in v1 (no live `rf serve` API to hit
 * from a static deployment; Wave E's HTTP router hasn't landed yet either).
 * This module supplies:
 *
 *   1. A self-contained demo draft (MOCK_REPORT_DRAFT) that mirrors
 *      docs/project_plans/design-specs/assets/public-multiuser-release/
 *      mockup-report-builder.png content 1:1 (same title, section outline,
 *      paragraph text, and claim citations) so the rendered UI can be
 *      compared directly against the mockup for visual-fidelity review.
 *   2. A synchronous claim-preview dictionary (BUILDER_MOCK_CLAIM_PREVIEWS)
 *      keyed by claim_id, standing in for the catalog/claim-ledger lookup a
 *      real deployment would do. Report Builder drafts only carry opaque
 *      claim_id/catalog_item_id references (schemas/report_draft.schema.yaml)
 *      — resolving those to display text/status/sources is the caller's
 *      job. Using a static dictionary here (rather than useCatalogItem
 *      network calls) keeps the Builder's demo/static rendering fully
 *      synchronous and independent of whatever the *catalog's* fixture data
 *      happens to contain, which matters because catalog.ts's index is
 *      built from run.json fixtures that know nothing about this draft.
 *
 * Both are also used by src/test/builder-screen.test.tsx to render /builder
 * without a live server. Not used by fetchReportDraft in loopback mode.
 */

import type { RFResolvedSource } from "@/types/rf";
import type { CatalogItemSummary, CatalogItemType, CatalogSearchFacets } from "@/types/rf/catalog";
import type { ReportBlock, ReportClaimLink, ReportDraft, ReportDraftSummary } from "@/types/rf/report_draft";

// ── Claim preview dictionary ──────────────────────────────────────────────────

export interface BuilderClaimPreview {
  claim_id: string;
  text: string;
  status: "supported" | "mixed" | "contradicted" | "inference" | "speculation" | "unsupported";
  confidence: "high" | "medium" | "low";
  materiality: "material" | "narrative" | "background";
  sources: RFResolvedSource[];
}

function src(id: string, title: string, rank: "primary" | "secondary" | "tertiary"): RFResolvedSource {
  return {
    source_card_id: id,
    evidence_id: `${id}_ev1`,
    relation: "supports",
    resolved: true,
    dangling: false,
    title,
    source_type: rank === "primary" ? "paper" : "blog",
    trust: { source_rank: rank },
    usage: { allowed_for_public_output: true, citation_required: true },
    sensitivity: "public",
    evidence_locator: "§ results",
    summary: `${title} — key finding referenced by this claim.`,
    quote: null,
  };
}

export const BUILDER_MOCK_CLAIM_PREVIEWS: Record<string, BuilderClaimPreview> = {
  clm_043: {
    claim_id: "clm_043",
    text: "Hybrid BM25+vector ranking improves Recall@5 by +17.4% over unranked hybrid on the top ~100 lexical candidates.",
    status: "supported",
    confidence: "high",
    materiality: "material",
    sources: [
      src("sc_001", "Shallow Cross-Encoders for Low-Latency Retrieval", "primary"),
      src("sc_002", "TAT-DoA vs Dense Retrieval: A Large-Scale Study", "secondary"),
    ],
  },
  clm_044: {
    claim_id: "clm_044",
    text: "RRF with k=60% yields the most stable Recall@5 across diverse query distributions.",
    status: "supported",
    confidence: "medium",
    materiality: "material",
    sources: [src("sc_003", "AnthoPR: Contextual Retrieval Stack", "secondary")],
  },
  clm_042: {
    claim_id: "clm_042",
    text: "Cross-encoder reranking on top-100 lexical candidates yields the highest nDCG@10.",
    status: "supported",
    confidence: "medium",
    materiality: "material",
    sources: [
      src("sc_001", "Shallow Cross-Encoders for Low-Latency Retrieval", "primary"),
      src("sc_003", "AnthoPR: Contextual Retrieval Stack", "secondary"),
      src("sc_004", "Re-ranking Trade-offs in Production Systems", "tertiary"),
    ],
  },
  clm_041: {
    claim_id: "clm_041",
    text: "BM25/FTS5 dense matching is more robust on rare/lexical-heavy queries.",
    status: "supported",
    confidence: "high",
    materiality: "material",
    sources: [src("sc_005", "BM25 in Practice: Design & Pitfalls", "secondary")],
  },
  clm_038: {
    claim_id: "clm_038",
    text: "Shorter chunks (≤ 256 tokens) improve precision for factoid queries.",
    status: "inference",
    confidence: "medium",
    materiality: "narrative",
    sources: [],
  },
  clm_029: {
    claim_id: "clm_029",
    text: "Adaptive k for RRF based on query entropy may further improve tail performance.",
    status: "speculation",
    confidence: "low",
    materiality: "background",
    sources: [],
  },
};

export function resolveBuilderClaimPreview(claimId: string): BuilderClaimPreview | null {
  return BUILDER_MOCK_CLAIM_PREVIEWS[claimId] ?? null;
}

// ── Demo catalog fallback (F5/demo-data polish pass) ──────────────────────────
//
// BuilderCatalogPane always queries the SAME useCatalogSearch/useCatalogStats
// hooks CatalogScreen uses (real dual-mode catalog, unchanged by this wave).
// In a fresh static deployment with no bundled run exports, that catalog is
// legitimately empty — which made the Builder's left pane, filters, and Claim
// Basket undemonstrable without a live server. Rather than seed fake claims
// into the shared static catalog index (lib/catalog.ts, used by CatalogScreen
// too — out of scope/blast-radius risk for this wave), BuilderCatalogPane
// falls back to this bundled 6-item demo set ONLY when the real catalog
// search comes back with zero total results in static mode. The IDs
// deliberately match BUILDER_MOCK_CLAIM_PREVIEWS and MOCK_REPORT_DRAFT's
// claim_links (clm_038/041/042/043/044/029) so a claim staged from this demo
// catalog resolves consistently everywhere else in the demo (chips, basket,
// audit inspector source cards).

function demoCatalogItem(claimId: string, itemType: CatalogItemType): CatalogItemSummary {
  const preview = BUILDER_MOCK_CLAIM_PREVIEWS[claimId];
  return {
    catalog_item_id: `ci_${claimId}`,
    item_type: itemType,
    title: preview.text,
    summary: null,
    run_id: "rf_run_20260614_hybrid_bm25_vector_and_ft5s_ranking",
    local_ref: claimId,
    project: "Retrieval Architecture Comparison",
    status: preview.status,
    sensitivity: "public",
    trust_label: null,
    confidence: preview.confidence,
    source_count: preview.sources.length,
    created_at: "2026-06-14T09:00:00Z",
    updated_at: "2026-06-14T11:58:00Z",
  };
}

export const MOCK_CATALOG_CLAIMS: CatalogItemSummary[] = [
  demoCatalogItem("clm_043", "claim"),
  demoCatalogItem("clm_044", "claim"),
  demoCatalogItem("clm_042", "claim"),
  demoCatalogItem("clm_041", "claim"),
  demoCatalogItem("clm_038", "inference"),
  demoCatalogItem("clm_029", "claim"),
];

export const MOCK_CATALOG_STATS_COUNTS: Record<CatalogItemType, number> = {
  claim: MOCK_CATALOG_CLAIMS.filter((i) => i.item_type === "claim").length,
  source: 0,
  inference: MOCK_CATALOG_CLAIMS.filter((i) => i.item_type === "inference").length,
  report: 0,
  reusable_output: 0,
  writeback: 0,
};

/** Client-side filter over the demo set — mirrors the item_type/status/q params BuilderCatalogPane already sends useCatalogSearch. */
export function filterMockCatalog(
  itemType: CatalogItemType,
  query: string | undefined,
  status: string | undefined,
): { items: CatalogItemSummary[]; facets: CatalogSearchFacets } {
  const q = (query ?? "").trim().toLowerCase();
  const items = MOCK_CATALOG_CLAIMS.filter((item) => {
    if (item.item_type !== itemType) return false;
    if (status && item.status !== status) return false;
    if (q && !item.title.toLowerCase().includes(q)) return false;
    return true;
  });
  const pool = MOCK_CATALOG_CLAIMS.filter((item) => item.item_type === itemType);
  const facets: CatalogSearchFacets = {
    projects: Array.from(new Set(pool.map((i) => i.project).filter((p): p is string => Boolean(p)))),
    statuses: Array.from(new Set(pool.map((i) => i.status).filter((s): s is string => Boolean(s)))),
    sensitivities: Array.from(new Set(pool.map((i) => i.sensitivity).filter((s): s is NonNullable<typeof s> => Boolean(s)))),
  };
  return { items, facets };
}

// ── Demo draft ────────────────────────────────────────────────────────────────

function block(
  id: string,
  order: number,
  type: ReportBlock["block_type"],
  markdown: string,
  opts: Partial<ReportBlock> = {},
): ReportBlock {
  return {
    block_id: id,
    block_type: type,
    order,
    markdown,
    materiality: opts.materiality ?? "material",
    linked_claim_ids: opts.linked_claim_ids ?? [],
    linked_source_ids: opts.linked_source_ids ?? [],
    coverage_status: opts.coverage_status ?? "narrative",
    risk_flags: opts.risk_flags ?? [],
  };
}

function claimLink(
  linkId: string,
  blockId: string,
  claimId: string,
  relation: ReportClaimLink["relation"],
  status: ReportClaimLink["link_status"] = "linked",
): ReportClaimLink {
  return {
    claim_link_id: linkId,
    block_id: blockId,
    claim_id: claimId,
    source_run_id: null,
    catalog_item_id: `ci_${claimId}`,
    relation,
    span_start: 0,
    span_end: 120,
    quote_text_hash: `hash_${claimId}`,
    link_status: status,
  };
}

const BLOCKS: ReportBlock[] = [
  block("b_h1", 0, "heading", "## 1. Executive summary"),
  block("b_p1", 1, "paragraph", "This memo compares hybrid retrieval configurations combining BM25, vector search, and FTS5, with and without reranking.", {
    materiality: "narrative",
    coverage_status: "narrative",
  }),
  block(
    "b_p2",
    2,
    "paragraph",
    "Across 7 datasets and ~31k queries, hybrid BM25+vector ranking improves Recall@5 by +17.4% over unranked hybrid on the top ~100 lexical candidates. [claim:clm_043]",
    { linked_claim_ids: ["clm_043"], coverage_status: "supported" },
  ),
  block(
    "b_p3",
    3,
    "paragraph",
    "RRF with k=60% is the most stable fusion method across query distributions, while cross-encoder reranking on the top-100 lexical set yields the highest nDCG@10. [claim:clm_044]",
    { linked_claim_ids: ["clm_044"], coverage_status: "supported" },
  ),
  block(
    "b_p4",
    4,
    "paragraph",
    "We recommend a two-stage pipeline: BM25+vector candidate generation with RRF (k=60), then cross-encoder reranking on the top-100 lexical candidates. [claim:clm_042]",
    { linked_claim_ids: ["clm_042"], coverage_status: "supported" },
  ),
  block("b_p5", 5, "paragraph", "See Section 4 for configuration details and cost implications.", {
    materiality: "narrative",
    coverage_status: "narrative",
  }),
  block("b_h2", 6, "heading", "## 2. Architecture overview"),
  block(
    "b_p6",
    7,
    "paragraph",
    "BM25/FTS5 dense matching remains more robust than pure dense retrieval on rare or lexical-heavy queries. [claim:clm_041]",
    { linked_claim_ids: ["clm_041"], coverage_status: "supported" },
  ),
  block("b_h3", 8, "heading", "## 3. Empirical results"),
  block("b_h3a", 9, "heading", "### 3.1 Recall & Precision"),
  block(
    "b_p7",
    10,
    "paragraph",
    "Chunking below 256 tokens is inferred to improve precision on factoid-style queries, though this was not directly A/B tested. [claim:clm_038]",
    { linked_claim_ids: ["clm_038"], coverage_status: "needs_review", risk_flags: ["weak_confidence"] },
  ),
  block("b_h3b", 11, "heading", "### 3.2 nDCG & MRR"),
  block("b_p8", 12, "paragraph", "", { materiality: "background", coverage_status: "unsupported" }),
  block("b_h3c", 13, "heading", "### 3.3 Latency & Cost"),
  block("b_h4", 14, "heading", "## 4. Design recommendations"),
  block("b_h5", 15, "heading", "## 5. Limitations & risks"),
  block(
    "b_p9",
    16,
    "paragraph",
    "Adaptive k for RRF based on query entropy is speculative and unverified at production scale. [claim:clm_029]",
    { linked_claim_ids: ["clm_029"], materiality: "background", coverage_status: "needs_review" },
  ),
  block("b_h6", 17, "heading", "## 6. Open questions"),
];

const CLAIM_LINKS: ReportClaimLink[] = [
  claimLink("cl_1", "b_p2", "clm_043", "supports"),
  claimLink("cl_2", "b_p3", "clm_044", "supports"),
  claimLink("cl_3", "b_p4", "clm_042", "supports"),
  claimLink("cl_4", "b_p6", "clm_041", "supports"),
  claimLink("cl_5", "b_p7", "clm_038", "inferred_from", "needs_review"),
  claimLink("cl_6", "b_p9", "clm_029", "context", "needs_review"),
];

export const MOCK_REPORT_DRAFT: ReportDraft = {
  schema_version: 1,
  type: "report_draft",
  report_draft_id: "rpt_demo_hybrid_retrieval",
  title: "Hybrid Retrieval: BM25, Vector, FTS5, and Reranking — Evidence Summary",
  origin: "run",
  source_run_id: "rf_run_20260614_hybrid_bm25_vector_and_ft5s_ranking",
  source_template_id: null,
  source_collection_id: null,
  audience: "client",
  sensitivity: "client_sensitive",
  status: "draft",
  workspace_id: null,
  project_id: "Retrieval Architecture Comparison",
  created_by: "nick",
  updated_by: "nick",
  created_at: "2026-06-14T09:00:00Z",
  updated_at: "2026-06-14T11:58:00Z",
  current_version_id: "rv_demo_5",
  blocks: BLOCKS,
  claim_links: CLAIM_LINKS,
  source_links: [],
  comments: [],
  review_state: { status: "pending", reviewers: [] },
  revisions: [
    { report_version_id: "rv_demo_1", created_at: "2026-06-14T09:10:00Z", created_by: "nick", note: "Initial outline" },
    { report_version_id: "rv_demo_5", created_at: "2026-06-14T11:55:00Z", created_by: "nick", note: "Add empirical results" },
  ],
};

export function summarizeDraft(draft: ReportDraft): ReportDraftSummary {
  return {
    report_draft_id: draft.report_draft_id,
    title: draft.title,
    status: draft.status,
    sensitivity: draft.sensitivity,
    audience: draft.audience,
    origin: draft.origin,
    project_id: draft.project_id,
    workspace_id: draft.workspace_id,
    created_by: draft.created_by,
    current_version_id: draft.current_version_id,
    block_count: draft.blocks.length,
    claim_link_count: draft.claim_links.length,
    source_link_count: draft.source_links.length,
    created_at: draft.created_at,
    updated_at: draft.updated_at,
  };
}

export const MOCK_REPORT_DRAFT_SUMMARY: ReportDraftSummary = summarizeDraft(MOCK_REPORT_DRAFT);
export const MOCK_REPORT_DRAFT_LIST: ReportDraftSummary[] = [MOCK_REPORT_DRAFT_SUMMARY];
