/**
 * Evidence Catalog — pure, dependency-free functions building and querying
 * the shared claim/source/inference/report/reusable_output/writeback index
 * from loaded RFRunExport documents.
 *
 * This is the static-mode mirror of the backend `catalog_service.py` importer
 * (Wave B). It implements the SAME item-mapping table from the plan doc
 * (docs/project_plans/implementation_plans/public-multiuser-p0p1-plan.md
 * § "Item mapping (import contract)") so static-mode and loopback-mode
 * search/stats results are behaviorally equivalent.
 *
 * Deterministic IDs (D5): catalog_item_id = "ci_" + sha1(`${item_type}:${run_id}:${local_ref}`).slice(0,12)
 * — implemented below with a small dependency-free SHA-1 (matches Python's
 * hashlib.sha1 byte-for-byte; see catalog.test.ts for known-vector proof).
 *
 * Scoping notes (see also the Wave C final report):
 *   - Sensitivity DERIVATION is implemented per spec. Read-time THRESHOLD
 *     EXCLUSION (D2) is a backend/Wave-B concern: RFRunExport data consumed
 *     here is already gated/redacted upstream by the export layer, and the
 *     existing SourceCard component re-applies its own display-time
 *     redaction gate. This module does not exclude items by threshold.
 *   - Source dedup (`claims[*].sources[]` → "source") is scoped WITHIN each
 *     run, not globally across runs — the deterministic ID formula is
 *     run-scoped (`run_id` is part of the hash input), so a true cross-run
 *     merge would break the local_ref/run_id alias contract (D5). Multiple
 *     claims within the SAME run citing the same source_card_id are merged
 *     into one source item, aggregating each claim's evidence use.
 */

import type {
  RFClaim,
  RFClaimConfidence,
  RFResolvedSource,
  RFRunExport,
  RFSensitivity,
  RFWritebackTarget,
} from "@/types/rf/run-export.js";
import type {
  CatalogItemDetail,
  CatalogItemSummary,
  CatalogItemType,
  CatalogLink,
  CatalogSearchFacets,
  CatalogSearchParams,
  CatalogSearchResult,
  CatalogSortKey,
  CatalogStats,
} from "@/types/rf/catalog.js";
import { deriveRunTitle, deriveWritebackTitle, titleFromSlug } from "./runs.js";

// ═════════════════════════════════════════════════════════════════════════
// SHA-1 — pure, dependency-free. Matches Python's hashlib.sha1(...).hexdigest()
// byte-for-byte for UTF-8 input. See catalog.test.ts for known-vector proof
// (sha1(""), sha1("abc"), sha1("The quick brown fox...")).
// ═════════════════════════════════════════════════════════════════════════

function rotl32(x: number, n: number): number {
  return ((x << n) | (x >>> (32 - n))) >>> 0;
}

/** SHA-1 over a UTF-8 string, returned as a 40-char lowercase hex digest. */
export function sha1Hex(message: string): string {
  const msgBytes = Array.from(new TextEncoder().encode(message));
  const bitLength = msgBytes.length * 8;

  // Padding: append 0x80, then zero bytes until length ≡ 56 (mod 64).
  const padded = [...msgBytes, 0x80];
  while (padded.length % 64 !== 56) padded.push(0);

  // Append original length as a 64-bit big-endian integer (high word is
  // always 0 for the short strings this module hashes).
  const low = bitLength >>> 0;
  for (let i = 3; i >= 0; i--) padded.push(0);
  for (let i = 3; i >= 0; i--) padded.push((low >>> (i * 8)) & 0xff);

  let h0 = 0x67452301;
  let h1 = 0xefcdab89;
  let h2 = 0x98badcfe;
  let h3 = 0x10325476;
  let h4 = 0xc3d2e1f0;

  for (let chunkStart = 0; chunkStart < padded.length; chunkStart += 64) {
    const w = new Array<number>(80).fill(0);
    for (let i = 0; i < 16; i++) {
      const o = chunkStart + i * 4;
      w[i] =
        (((padded[o] ?? 0) << 24) |
          ((padded[o + 1] ?? 0) << 16) |
          ((padded[o + 2] ?? 0) << 8) |
          (padded[o + 3] ?? 0)) >>>
        0;
    }
    for (let i = 16; i < 80; i++) {
      w[i] = rotl32((w[i - 3] ?? 0) ^ (w[i - 8] ?? 0) ^ (w[i - 14] ?? 0) ^ (w[i - 16] ?? 0), 1);
    }

    let a = h0;
    let b = h1;
    let c = h2;
    let d = h3;
    let e = h4;

    for (let i = 0; i < 80; i++) {
      let f: number;
      let k: number;
      if (i < 20) {
        f = (b & c) | (~b & d);
        k = 0x5a827999;
      } else if (i < 40) {
        f = b ^ c ^ d;
        k = 0x6ed9eba1;
      } else if (i < 60) {
        f = (b & c) | (b & d) | (c & d);
        k = 0x8f1bbcdc;
      } else {
        f = b ^ c ^ d;
        k = 0xca62c1d6;
      }
      const temp = (rotl32(a, 5) + f + e + k + (w[i] ?? 0)) >>> 0;
      e = d;
      d = c;
      c = rotl32(b, 30);
      b = a;
      a = temp;
    }

    h0 = (h0 + a) >>> 0;
    h1 = (h1 + b) >>> 0;
    h2 = (h2 + c) >>> 0;
    h3 = (h3 + d) >>> 0;
    h4 = (h4 + e) >>> 0;
  }

  return [h0, h1, h2, h3, h4].map((n) => n.toString(16).padStart(8, "0")).join("");
}

/** D5: catalog_item_id = "ci_" + sha1(`${item_type}:${run_id}:${local_ref}`)[:12] */
export function catalogItemId(itemType: CatalogItemType, runId: string, localRef: string): string {
  return `ci_${sha1Hex(`${itemType}:${runId}:${localRef}`).slice(0, 12)}`;
}

// ═════════════════════════════════════════════════════════════════════════
// Small helpers
// ═════════════════════════════════════════════════════════════════════════

const SENSITIVITY_ORDER: Record<string, number> = {
  public: 0,
  personal: 1,
  work_sensitive: 2,
  client_sensitive: 3,
};

/** Unknown labels fail-closed: stricter (higher rank) than client_sensitive. */
function sensitivityRank(label: string): number {
  const rank = SENSITIVITY_ORDER[label];
  return rank === undefined ? 4 : rank;
}

/** Returns the strictest (highest-ranked) sensitivity label among the inputs; absent/null → "public". */
function maxSensitivity(...labels: Array<string | null | undefined>): RFSensitivity {
  let best = "public";
  let bestRank = -1;
  for (const raw of labels) {
    const label = raw ?? "public";
    const rank = sensitivityRank(label);
    if (rank > bestRank) {
      bestRank = rank;
      best = label;
    }
  }
  return best as RFSensitivity;
}

const CONFIDENCE_NUMERIC: Record<RFClaimConfidence, number> = {
  low: 0.35,
  medium: 0.65,
  high: 0.9,
};

function mapConfidence(confidence?: RFClaimConfidence | null): number | null {
  if (!confidence) return null;
  return CONFIDENCE_NUMERIC[confidence] ?? null;
}

function truncate(text: string, max: number): string {
  const trimmed = text.trim().replace(/\s+/g, " ");
  if (trimmed.length <= max) return trimmed;
  return `${trimmed.slice(0, max - 1).trimEnd()}…`;
}

/** First non-empty, non-heading paragraph of a markdown document (for report summaries). */
function firstNonHeadingParagraph(markdown?: string | null): string | null {
  if (!markdown) return null;
  const lines = markdown.split(/\r?\n/);
  const paragraph: string[] = [];
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      if (paragraph.length > 0) break;
      continue;
    }
    if (/^#{1,6}\s/.test(line)) continue; // skip headings
    paragraph.push(line);
  }
  if (paragraph.length === 0) return null;
  return truncate(paragraph.join(" "), 240);
}

export type WritebackStatus = "published" | "pending" | "failed" | "other";

/** Matches the semantics of the (now-absorbed) LibraryScreen's normalizeWritebackStatus. */
export function normalizeWritebackStatus(status: string | null | undefined): WritebackStatus {
  const s = (status ?? "").toLowerCase();
  if (s === "published") return "published";
  if (s === "pending") return "pending";
  if (s === "failed") return "failed";
  return "other";
}

function getRunDisplayTitle(run: RFRunExport): string {
  return (
    (run.title && run.title !== run.run_id ? run.title : null) ??
    deriveRunTitle(run) ??
    titleFromSlug(run.run_id) ??
    run.run_id
  );
}

// ═════════════════════════════════════════════════════════════════════════
// Provenance (stored on claim/inference payload.provenance; drives the
// inspector's Source Card → Extraction → Inference → Report → Writeback strip)
// ═════════════════════════════════════════════════════════════════════════

export interface CatalogProvenance {
  source_card: boolean;
  extraction: boolean;
  inference: boolean;
  report: boolean;
  writeback: boolean;
}

// ═════════════════════════════════════════════════════════════════════════
// Index
// ═════════════════════════════════════════════════════════════════════════

interface IndexEntry {
  detail: CatalogItemDetail;
  searchBody: string;
}

export interface CatalogIndex {
  entries: IndexEntry[];
  runsIndexed: number;
  lastImportAt: string | null;
}

function searchBodyOf(detail: CatalogItemDetail, extra: Array<string | null | undefined> = []): string {
  return [detail.title, detail.summary, ...extra]
    .filter((v): v is string => Boolean(v))
    .join(" ")
    .toLowerCase();
}

/**
 * Build the full catalog index from a set of loaded run exports.
 * Implements the item-mapping table from the plan doc exactly (see module
 * doc comment for scoping notes on threshold-gating and source dedup).
 */
export function buildCatalogIndex(runs: RFRunExport[]): CatalogIndex {
  const entries: IndexEntry[] = [];

  for (const run of runs) {
    const runId = run.run_id;
    const runSensitivity = maxSensitivity(run.sensitivity);
    const project = run.linked_projects?.[0] ?? run.category ?? null;
    const runTitle = getRunDisplayTitle(run);
    const writebackApproved = Boolean(run.writebacks?.approved_for_writeback);

    interface ClaimAccum {
      claim: RFClaim;
      itemType: CatalogItemType;
      itemId: string;
      usedByInferences: string[];
      links: CatalogLink[];
    }

    // ── Pass 1: classify claims/inferences, assign deterministic IDs ──
    const claimAccums = new Map<string, ClaimAccum>();
    for (const claim of run.claims ?? []) {
      const isInference = (claim.inference_basis?.from_claims?.length ?? 0) > 0;
      const itemType: CatalogItemType = isInference ? "inference" : "claim";
      claimAccums.set(claim.claim_id, {
        claim,
        itemType,
        itemId: catalogItemId(itemType, runId, claim.claim_id),
        usedByInferences: [],
        links: [],
      });
    }

    // ── Pass 2: inference → claim links ("inferred_from") + reverse pointer ──
    for (const accum of claimAccums.values()) {
      if (accum.itemType !== "inference") continue;
      for (const fromId of accum.claim.inference_basis?.from_claims ?? []) {
        const target = claimAccums.get(fromId);
        if (!target) continue;
        accum.links.push({
          rel: "inferred_from",
          target_catalog_item_id: target.itemId,
          target_item_type: target.itemType,
        });
        target.usedByInferences.push(accum.itemId);
      }
    }

    // ── Sources: dedupe by source_card_id WITHIN this run ──
    interface EvidenceUse {
      claim_id: string;
      claim_item_id: string;
      relation: string;
      locator: string | null;
      evidence_locator: string | null;
      summary: string | null;
      quote: string | null;
    }
    interface SourceAccum {
      source: RFResolvedSource;
      itemId: string;
      evidenceUses: EvidenceUse[];
    }
    const sourceAccums = new Map<string, SourceAccum>();

    for (const accum of claimAccums.values()) {
      for (const source of accum.claim.sources ?? []) {
        if (!source.resolved || source.dangling) continue;
        const scid = source.source_card_id;
        let sAccum = sourceAccums.get(scid);
        if (!sAccum) {
          sAccum = { source, itemId: catalogItemId("source", runId, scid), evidenceUses: [] };
          sourceAccums.set(scid, sAccum);
        }
        sAccum.evidenceUses.push({
          claim_id: accum.claim.claim_id,
          claim_item_id: accum.itemId,
          relation: source.relation,
          locator: source.locator ?? null,
          evidence_locator: source.evidence_locator ?? null,
          summary: source.summary ?? null,
          quote: source.quote ?? null,
        });
        accum.links.push({
          rel: "supports",
          target_catalog_item_id: sAccum.itemId,
          target_item_type: "source",
        });
      }
    }

    // ── Emit source items ──
    for (const sAccum of sourceAccums.values()) {
      const { source, itemId, evidenceUses } = sAccum;
      const sensitivity = maxSensitivity(source.sensitivity);
      const detail: CatalogItemDetail = {
        catalog_item_id: itemId,
        item_type: "source",
        title: source.title ?? source.source_card_id,
        summary: source.summary ?? null,
        run_id: runId,
        local_ref: source.source_card_id,
        project,
        status: null,
        sensitivity,
        trust_label: source.trust?.source_rank ?? null,
        confidence: null,
        source_count: evidenceUses.length,
        created_at: run.created_at ?? null,
        updated_at: run.created_at ?? null,
        payload: {
          source_type: source.source_type ?? null,
          url: source.url ?? null,
          trust: source.trust ?? null,
          usage: source.usage ?? null,
          evidence_uses: evidenceUses,
        },
        links: [],
      };
      entries.push({
        detail,
        searchBody: searchBodyOf(
          detail,
          evidenceUses.flatMap((u) => [u.summary, u.quote]),
        ),
      });
    }

    // ── Emit claim/inference items ──
    const reportContainsLinks: CatalogLink[] = [];
    for (const accum of claimAccums.values()) {
      const { claim, itemType, itemId, usedByInferences, links } = accum;
      const sourceList = claim.sources ?? [];
      const sensitivity = maxSensitivity(run.sensitivity, ...sourceList.map((s) => s.sensitivity));
      const hasReportLocation = (claim.report_locations?.length ?? 0) > 0;
      const inReport = hasReportLocation && run.report_draft != null;
      if (inReport) {
        reportContainsLinks.push({
          rel: "contains",
          target_catalog_item_id: itemId,
          target_item_type: itemType,
        });
      }
      const provenance: CatalogProvenance = {
        source_card: sourceList.length > 0,
        extraction: sourceList.some((s) => Boolean(s.evidence_locator || s.locator)),
        inference: itemType === "inference" || usedByInferences.length > 0,
        report: inReport,
        writeback: writebackApproved,
      };
      const detail: CatalogItemDetail = {
        catalog_item_id: itemId,
        item_type: itemType,
        title: truncate(claim.text, 160),
        summary: claim.inference_basis?.reasoning_summary ?? null,
        run_id: runId,
        local_ref: claim.claim_id,
        project,
        status: claim.status ?? null,
        sensitivity,
        trust_label: claim.status ?? null,
        confidence: mapConfidence(claim.confidence),
        source_count: sourceList.length,
        created_at: run.created_at ?? null,
        updated_at: run.created_at ?? null,
        payload: {
          materiality: claim.materiality ?? null,
          claim_type: claim.claim_type ?? null,
          confidence_label: claim.confidence ?? null,
          report_locations: claim.report_locations ?? [],
          inference_basis: claim.inference_basis ?? null,
          sources: sourceList,
          used_by_inferences: usedByInferences,
          provenance,
        },
        links,
      };
      entries.push({
        detail,
        searchBody: searchBodyOf(detail, [claim.inference_basis?.reasoning_summary]),
      });
    }

    // ── Report item (one per run) ──
    if (run.report_draft != null) {
      const itemId = catalogItemId("report", runId, "report");
      const detail: CatalogItemDetail = {
        catalog_item_id: itemId,
        item_type: "report",
        title: runTitle,
        summary: firstNonHeadingParagraph(run.report_draft),
        run_id: runId,
        local_ref: "report",
        project,
        status: writebackApproved ? "published" : "draft",
        sensitivity: runSensitivity,
        trust_label: null,
        confidence: null,
        source_count: 0,
        created_at: run.created_at ?? null,
        updated_at: run.created_at ?? null,
        payload: {
          report_draft: run.report_draft,
          writebacks: run.writebacks ?? null,
          claim_counts: run.claim_counts ?? null,
        },
        links: reportContainsLinks,
      };
      entries.push({ detail, searchBody: searchBodyOf(detail, [run.report_draft]) });
    }

    // ── Reusable output candidates ──
    (run.reusable_output_candidates ?? []).forEach((candidate, index) => {
      const localRef = `ro_${index}`;
      const itemId = catalogItemId("reusable_output", runId, localRef);
      const detail: CatalogItemDetail = {
        catalog_item_id: itemId,
        item_type: "reusable_output",
        title: candidate.description,
        summary: null,
        run_id: runId,
        local_ref: localRef,
        project,
        status: null,
        sensitivity: runSensitivity,
        trust_label: candidate.is_skillbom_candidate ? "SkillBOM candidate" : null,
        confidence: null,
        source_count: 0,
        created_at: run.created_at ?? null,
        updated_at: run.created_at ?? null,
        payload: {
          description: candidate.description,
          is_skillbom_candidate: candidate.is_skillbom_candidate ?? false,
          source_run_id: candidate.source_run_id ?? null,
        },
        links: [],
      };
      entries.push({ detail, searchBody: searchBodyOf(detail) });
    });

    // ── Writeback targets ──
    (run.writebacks?.targets ?? []).forEach((target: RFWritebackTarget, index) => {
      const localRef = `wb_${index}`;
      const itemId = catalogItemId("writeback", runId, localRef);
      const status = normalizeWritebackStatus(target.status);
      const detail: CatalogItemDetail = {
        catalog_item_id: itemId,
        item_type: "writeback",
        title: deriveWritebackTitle(target),
        summary: null,
        run_id: runId,
        local_ref: localRef,
        project,
        status,
        sensitivity: runSensitivity,
        trust_label: target.status ?? null,
        confidence: null,
        source_count: 0,
        created_at: run.created_at ?? null,
        updated_at: run.created_at ?? null,
        payload: {
          name: target.name ?? null,
          destination: target.destination ?? null,
          url: target.url ?? null,
          raw_status: target.status ?? null,
        },
        links: [],
      };
      entries.push({ detail, searchBody: searchBodyOf(detail) });
    });
  }

  const lastImportAt = runs.reduce<string | null>((max, run) => {
    if (!run.created_at) return max;
    if (!max || run.created_at > max) return run.created_at;
    return max;
  }, null);

  return { entries, runsIndexed: runs.length, lastImportAt };
}

// ═════════════════════════════════════════════════════════════════════════
// Search / stats
// ═════════════════════════════════════════════════════════════════════════

function uniqueSorted(values: Array<string | null | undefined>): string[] {
  return Array.from(new Set(values.filter((v): v is string => Boolean(v)))).sort((a, b) =>
    a.localeCompare(b),
  );
}

function computeFacets(index: CatalogIndex): CatalogSearchFacets {
  return {
    projects: uniqueSorted(index.entries.map((e) => e.detail.project)),
    statuses: uniqueSorted(index.entries.map((e) => e.detail.status)),
    sensitivities: uniqueSorted(index.entries.map((e) => e.detail.sensitivity)),
  };
}

/** Sort a set of catalog item summaries in-place-equivalent (returns a new array). */
export function sortCatalogItems<T extends CatalogItemSummary>(items: T[], sort: CatalogSortKey = "updated"): T[] {
  const copy = [...items];
  copy.sort((a, b) => {
    if (sort === "title") return a.title.localeCompare(b.title);
    if (sort === "confidence") return (b.confidence ?? -1) - (a.confidence ?? -1);
    // "updated" (default) — newest first; nulls sort last
    const av = a.updated_at ?? "";
    const bv = b.updated_at ?? "";
    return bv.localeCompare(av);
  });
  return copy;
}

const DEFAULT_PAGE_SIZE = 25;
const MAX_PAGE_SIZE = 200;

/**
 * Search the catalog index. Case-insensitive substring match over
 * title+summary+body (per item type, see searchBodyOf callers above).
 * Facets are computed over the FULL index (not the current filter set) so
 * filter dropdowns always show every available option.
 */
export function searchCatalog(index: CatalogIndex, params: CatalogSearchParams = {}): CatalogSearchResult {
  const {
    q,
    item_type,
    project,
    status,
    sensitivity,
    run_id,
    sort = "updated",
    page = 1,
    page_size = DEFAULT_PAGE_SIZE,
  } = params;

  const pageSize = Math.min(Math.max(Math.trunc(page_size) || DEFAULT_PAGE_SIZE, 1), MAX_PAGE_SIZE);
  const pageNum = Math.max(Math.trunc(page) || 1, 1);
  const qLower = q?.trim().toLowerCase();

  const filtered = index.entries.filter(({ detail, searchBody }) => {
    if (item_type && detail.item_type !== item_type) return false;
    if (project && detail.project !== project) return false;
    if (status && detail.status !== status) return false;
    if (sensitivity && detail.sensitivity !== sensitivity) return false;
    if (run_id && detail.run_id !== run_id) return false;
    if (qLower && !searchBody.includes(qLower)) return false;
    return true;
  });

  const sorted = sortCatalogItems(
    filtered.map((e) => e.detail),
    sort,
  );

  const total = sorted.length;
  const start = (pageNum - 1) * pageSize;
  const items = sorted.slice(start, start + pageSize);

  return {
    items,
    total,
    page: pageNum,
    page_size: pageSize,
    facets: computeFacets(index),
  };
}

export function catalogStats(index: CatalogIndex): CatalogStats {
  const counts: Record<CatalogItemType, number> = {
    claim: 0,
    source: 0,
    inference: 0,
    report: 0,
    reusable_output: 0,
    writeback: 0,
  };
  for (const { detail } of index.entries) {
    counts[detail.item_type] += 1;
  }
  return {
    counts,
    runs_indexed: index.runsIndexed,
    last_import_at: index.lastImportAt,
  };
}

/** Look up a single item's full detail by catalog_item_id. Returns null when absent. */
export function getCatalogItem(index: CatalogIndex, catalogItemId: string): CatalogItemDetail | null {
  return index.entries.find((e) => e.detail.catalog_item_id === catalogItemId)?.detail ?? null;
}
