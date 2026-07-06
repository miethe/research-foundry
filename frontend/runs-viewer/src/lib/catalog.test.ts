/**
 * Catalog lib tests — mapping rules, ID determinism, search/filter/sort/pagination.
 *
 * Covers:
 *   - sha1Hex known-vector correctness (proves the hand-rolled SHA-1 matches
 *     the standard algorithm byte-for-byte, same as Python's hashlib.sha1).
 *   - catalogItemId determinism.
 *   - Item mapping: inference classification (inference_basis.from_claims),
 *     source dedup within a run, sensitivity derivation (incl. fail-closed
 *     unknown-label ranking), report/reusable_output/writeback mapping.
 *   - Links: inference→claim (inferred_from), report→claim (contains).
 *   - searchCatalog: filters, text search, sort, pagination, facets.
 *   - catalogStats: per-type counts, runs_indexed, last_import_at.
 */

import { describe, it, expect } from "vitest";
import {
  buildCatalogIndex,
  catalogItemId,
  catalogStats,
  getCatalogItem,
  normalizeCatalogItemDetail,
  normalizeWritebackStatus,
  searchCatalog,
  sha1Hex,
  sortCatalogItems,
} from "./catalog";
import type { CatalogItemDetail } from "@/types/rf/catalog";
import type { RFClaim, RFReportAnchorBlock, RFResolvedSource, RFRunExport, RFSensitivity } from "@/types/rf/run-export";

// ── Fixtures ──────────────────────────────────────────────────────────────────

function makeSource(overrides: Partial<RFResolvedSource> & { source_card_id: string }): RFResolvedSource {
  return {
    evidence_id: `ev_${overrides.source_card_id}`,
    relation: "supports",
    resolved: true,
    dangling: false,
    title: `Title for ${overrides.source_card_id}`,
    source_type: "paper",
    url: `https://example.com/${overrides.source_card_id}`,
    trust: { source_rank: "primary" },
    usage: { allowed_for_public_output: true, citation_required: true },
    sensitivity: "public",
    evidence_locator: "p.1",
    summary: `Summary for ${overrides.source_card_id}`,
    quote: `Quote for ${overrides.source_card_id}`,
    ...overrides,
  };
}

const srcShared = makeSource({ source_card_id: "src_shared" });
const srcClient = makeSource({ source_card_id: "src_client", sensitivity: "client_sensitive" });
// Deliberately-invalid sensitivity label to prove fail-closed ranking (unknown > client_sensitive).
const srcUnknown = makeSource({
  source_card_id: "src_unknown",
  sensitivity: "mystery_level" as unknown as RFSensitivity,
});

const c1: RFClaim = {
  claim_id: "c1",
  text: "Shallow cross-encoders remain effective on CPU inference workloads.",
  status: "supported",
  claim_type: "factual",
  confidence: "high",
  report_locations: [{ heading: "Findings" }],
  sources: [srcShared],
};

const c2Inference: RFClaim = {
  claim_id: "c2",
  text: "Therefore, hybrid retrieval is the recommended default.",
  status: "inference",
  claim_type: "inference",
  confidence: "medium",
  inference_basis: { from_claims: ["c1"], reasoning_summary: "Derived from c1's benchmark result." },
  sources: [],
};

const c3: RFClaim = {
  claim_id: "c3",
  text: "BM25 plus dense fusion delivers the largest absolute gain on the benchmark.",
  status: "supported",
  sources: [srcShared, srcClient],
};

const c4: RFClaim = {
  claim_id: "c4",
  text: "Score calibration reduces drift variance across CPU deployments.",
  status: "mixed",
  sources: [srcUnknown, srcClient],
};

// Minimal report_anchors for runA — c1 is linked (status=supported → relation=supports),
// c2Inference is linked (status=inference → relation=inferred_from).
// c3/c4 have no anchor entries (omitted — they have no report_locations in the fixture).
// clm_missing is a dangling tag exercising the missing_claim path.
const runAAnchors: RFReportAnchorBlock[] = [
  {
    block_id: "aabbcc001122",
    section_id: null,
    paragraph_ordinal: 0,
    text_hash: "ddeeff334455",
    claim_links: [
      {
        claim_id: "c1",
        span_start: 0,
        span_end: 16,
        relation: "supports",
        link_status: "linked",
      },
    ],
  },
  {
    block_id: "bbccdd112233",
    section_id: "findings",
    paragraph_ordinal: 0,
    text_hash: "eeff00445566",
    claim_links: [
      // A "missing_claim" entry — must be skipped by the link derivation.
      {
        claim_id: "clm_missing",
        span_start: 0,
        span_end: 20,
        relation: null,
        link_status: "missing_claim",
      },
    ],
  },
];

const runA: RFRunExport = {
  schema_version: "1.4",
  run_id: "run_a",
  status_derived: "verified",
  sensitivity: "public",
  created_at: "2026-01-01T00:00:00Z",
  linked_projects: ["Alpha"],
  claims: [c1, c2Inference, c3, c4],
  claim_counts: null,
  verification: null,
  governance: null,
  timeline: null,
  report_draft: "# Hybrid Search Benchmark\n\nCross-encoder reranking improves NDCG@10 on CPU.\n\nMore detail follows.",
  report_anchors: runAAnchors,
};

const runB: RFRunExport = {
  schema_version: "1.3",
  run_id: "run_b",
  status_derived: "published",
  sensitivity: null,
  created_at: "2026-02-01T00:00:00Z",
  claims: [],
  claim_counts: null,
  verification: null,
  governance: null,
  timeline: null,
  reusable_output_candidates: [
    { description: "Reusable retrieval eval harness", is_skillbom_candidate: true },
  ],
  writebacks: {
    // target field (system identifier) is what the backend uses for local_ref derivation (F6).
    targets: [{ target: "meatywiki", name: "MeatyWiki", destination: "meatywiki://kb", status: "Published" }],
    approved_for_writeback: true,
  },
};

const RUNS = [runA, runB];

// ── SHA-1 known vectors ────────────────────────────────────────────────────

describe("sha1Hex — known vectors", () => {
  it('hashes the empty string', () => {
    expect(sha1Hex("")).toBe("da39a3ee5e6b4b0d3255bfef95601890afd80709");
  });

  it('hashes "abc"', () => {
    expect(sha1Hex("abc")).toBe("a9993e364706816aba3e25717850c26c9cd0d89d");
  });

  it('hashes the standard pangram vector', () => {
    expect(sha1Hex("The quick brown fox jumps over the lazy dog")).toBe(
      "2fd4e1c67a2d28fced849ee1bb76e7391b93eb12",
    );
  });
});

// ── catalogItemId determinism ─────────────────────────────────────────────

describe("catalogItemId", () => {
  it("is deterministic for the same inputs", () => {
    const a = catalogItemId("claim", "run_a", "c1");
    const b = catalogItemId("claim", "run_a", "c1");
    expect(a).toBe(b);
    expect(a).toMatch(/^ci_[0-9a-f]{12}$/);
  });

  it("differs when local_ref differs", () => {
    expect(catalogItemId("claim", "run_a", "c1")).not.toBe(catalogItemId("claim", "run_a", "c2"));
  });

  it("differs when item_type differs (same run_id/local_ref)", () => {
    expect(catalogItemId("claim", "run_a", "x")).not.toBe(catalogItemId("inference", "run_a", "x"));
  });

  it("differs when run_id differs", () => {
    expect(catalogItemId("claim", "run_a", "c1")).not.toBe(catalogItemId("claim", "run_b", "c1"));
  });
});

// ── Mapping rules ──────────────────────────────────────────────────────────

describe("buildCatalogIndex — item mapping", () => {
  const index = buildCatalogIndex(RUNS);

  it("classifies claims without inference_basis.from_claims as 'claim'", () => {
    const item = getCatalogItem(index, catalogItemId("claim", "run_a", "c1"));
    expect(item?.item_type).toBe("claim");
    expect(item?.trust_label).toBe("supported");
    expect(item?.status).toBe("supported");
  });

  it("classifies claims WITH non-empty inference_basis.from_claims as 'inference'", () => {
    const item = getCatalogItem(index, catalogItemId("inference", "run_a", "c2"));
    expect(item?.item_type).toBe("inference");
    expect(item?.summary).toBe("Derived from c1's benchmark result.");
  });

  it("does NOT classify c2 as a plain 'claim'", () => {
    expect(getCatalogItem(index, catalogItemId("claim", "run_a", "c2"))).toBeNull();
  });

  it("dedupes sources by source_card_id within a run", () => {
    const sourceItemId = catalogItemId("source", "run_a", "src_shared");
    const item = getCatalogItem(index, sourceItemId);
    expect(item).not.toBeNull();
    expect(item?.source_count).toBe(2); // used by c1 AND c3
    const evidenceUses = item?.payload.evidence_uses as unknown[];
    expect(evidenceUses).toHaveLength(2);
  });

  it("produces exactly one source item per distinct source_card_id", () => {
    const sourceItems = index.entries.filter((e) => e.detail.item_type === "source");
    const ids = new Set(sourceItems.map((e) => e.detail.local_ref));
    expect(ids).toEqual(new Set(["src_shared", "src_client", "src_unknown"]));
  });

  it("derives claim sensitivity as max(run sensitivity, source sensitivities)", () => {
    // c1: run=public, source=public → public
    const c1Item = getCatalogItem(index, catalogItemId("claim", "run_a", "c1"));
    expect(c1Item?.sensitivity).toBe("public");

    // c3: run=public, sources=[public, client_sensitive] → client_sensitive
    const c3Item = getCatalogItem(index, catalogItemId("claim", "run_a", "c3"));
    expect(c3Item?.sensitivity).toBe("client_sensitive");
  });

  it("fail-closed: an unrecognized sensitivity label ranks stricter than client_sensitive", () => {
    // c4 cites [mystery_level, client_sensitive] — the unknown label must win the max().
    const c4Item = getCatalogItem(index, catalogItemId("claim", "run_a", "c4"));
    expect(c4Item?.sensitivity).toBe("mystery_level");
  });

  it("links inference → claim with rel 'inferred_from'", () => {
    const inferenceId = catalogItemId("inference", "run_a", "c2");
    const claimId = catalogItemId("claim", "run_a", "c1");
    const item = getCatalogItem(index, inferenceId);
    expect(item?.links.outgoing).toContainEqual({
      relation: "inferred_from",
      catalog_item_id: claimId,
    });
  });

  it("records the reverse used_by_inferences pointer on the cited claim", () => {
    const c1Item = getCatalogItem(index, catalogItemId("claim", "run_a", "c1"));
    expect(c1Item?.payload.used_by_inferences).toContain(catalogItemId("inference", "run_a", "c2"));
  });

  it("links claim → source with rel 'supports'", () => {
    const c1Item = getCatalogItem(index, catalogItemId("claim", "run_a", "c1"));
    expect(c1Item?.links.outgoing).toContainEqual({
      relation: "supports",
      catalog_item_id: catalogItemId("source", "run_a", "src_shared"),
    });
  });

  it("maps report_draft != null to one 'report' item per run", () => {
    const reportItem = getCatalogItem(index, catalogItemId("report", "run_a", "report"));
    expect(reportItem).not.toBeNull();
    expect(reportItem?.title).toContain("Hybrid Search Benchmark");
    expect(reportItem?.summary).toBe("Cross-encoder reranking improves NDCG@10 on CPU.");
    expect(reportItem?.status).toBe("draft"); // run_a has no writebacks.approved_for_writeback
  });

  it("links report → claim with rel 'contains' for claims with report_locations", () => {
    const reportItem = getCatalogItem(index, catalogItemId("report", "run_a", "report"));
    expect(reportItem?.links.outgoing).toContainEqual({
      relation: "contains",
      catalog_item_id: catalogItemId("claim", "run_a", "c1"),
    });
  });

  it("does not emit a report item when report_draft is absent", () => {
    expect(index.entries.some((e) => e.detail.run_id === "run_b" && e.detail.item_type === "report")).toBe(
      false,
    );
  });

  it("maps reusable_output_candidates[] to 'reusable_output' items", () => {
    const item = getCatalogItem(index, catalogItemId("reusable_output", "run_b", "ro_0"));
    expect(item?.title).toBe("Reusable retrieval eval harness");
    expect(item?.trust_label).toBe("SkillBOM candidate");
  });

  it("maps writebacks.targets[] to 'writeback' items with normalized status", () => {
    // F6: local_ref uses target.target field ("meatywiki"), not the array index.
    const item = getCatalogItem(index, catalogItemId("writeback", "run_b", "wb_meatywiki"));
    expect(item?.local_ref).toBe("wb_meatywiki");
    expect(item?.status).toBe("published"); // normalizeWritebackStatus("Published")
  });

  it("threads project from linked_projects[0]", () => {
    const c1Item = getCatalogItem(index, catalogItemId("claim", "run_a", "c1"));
    expect(c1Item?.project).toBe("Alpha");
  });
});

describe("normalizeWritebackStatus", () => {
  it("lowercases and recognizes known statuses", () => {
    expect(normalizeWritebackStatus("Published")).toBe("published");
    expect(normalizeWritebackStatus("pending")).toBe("pending");
    expect(normalizeWritebackStatus("FAILED")).toBe("failed");
  });

  it("falls back to 'other' for unknown/absent status", () => {
    expect(normalizeWritebackStatus(null)).toBe("other");
    expect(normalizeWritebackStatus(undefined)).toBe("other");
    expect(normalizeWritebackStatus("weird")).toBe("other");
  });
});

// ── searchCatalog ──────────────────────────────────────────────────────────

describe("searchCatalog", () => {
  const index = buildCatalogIndex(RUNS);

  it("filters by item_type", () => {
    const result = searchCatalog(index, { item_type: "claim", page_size: 200 });
    expect(result.total).toBe(3); // c1, c3, c4 (c2 is an inference)
    expect(result.items.every((i) => i.item_type === "claim")).toBe(true);
  });

  it("filters by free-text query, case-insensitive substring over title/summary", () => {
    const result = searchCatalog(index, { q: "CROSS-ENCODERS", page_size: 200 });
    expect(result.items.some((i) => i.local_ref === "c1")).toBe(true);
  });

  it("filters by project", () => {
    const result = searchCatalog(index, { project: "Alpha", page_size: 200 });
    expect(result.items.every((i) => i.project === "Alpha")).toBe(true);
    expect(result.items.some((i) => i.run_id === "run_b")).toBe(false);
  });

  it("filters by sensitivity, distinguishing an unknown label from a known one", () => {
    const clientOnly = searchCatalog(index, { sensitivity: "client_sensitive", page_size: 200 });
    expect(clientOnly.items.some((i) => i.local_ref === "c3")).toBe(true);
    expect(clientOnly.items.some((i) => i.local_ref === "c4")).toBe(false); // c4 is "mystery_level", not client_sensitive
  });

  it("filters by run_id", () => {
    const result = searchCatalog(index, { run_id: "run_b", page_size: 200 });
    expect(result.items.every((i) => i.run_id === "run_b")).toBe(true);
    expect(result.total).toBe(2); // reusable_output + writeback
  });

  it("sorts by title ascending", () => {
    const result = searchCatalog(index, { item_type: "claim", sort: "title", page_size: 200 });
    const titles = result.items.map((i) => i.title);
    expect(titles).toEqual([...titles].sort((a, b) => a.localeCompare(b)));
  });

  it("sorts by confidence descending, nulls last", () => {
    const ORDINAL: Record<string, number> = { high: 2, medium: 1, low: 0 };
    const ord = (c: string | null | undefined) => (c != null ? (ORDINAL[c] ?? -1) : -1);
    const result = searchCatalog(index, { sort: "confidence", page_size: 200 });
    const confidences = result.items.map((i) => i.confidence);
    for (let i = 1; i < confidences.length; i++) {
      expect(ord(confidences[i - 1])).toBeGreaterThanOrEqual(ord(confidences[i]));
    }
  });

  it("paginates results and reports the correct total", () => {
    const page1 = searchCatalog(index, { page: 1, page_size: 1 });
    expect(page1.items).toHaveLength(1);
    expect(page1.total).toBeGreaterThan(1);
    expect(page1.page).toBe(1);
    expect(page1.page_size).toBe(1);
  });

  it("caps page_size at 200", () => {
    const result = searchCatalog(index, { page_size: 10_000 });
    expect(result.page_size).toBe(200);
  });

  it("computes facets over the full index regardless of applied filters", () => {
    const result = searchCatalog(index, { item_type: "claim" });
    expect(result.facets.projects).toContain("Alpha");
    expect(result.facets.sensitivities).toEqual(
      expect.arrayContaining(["public", "client_sensitive", "mystery_level"]),
    );
  });
});

describe("catalogStats", () => {
  it("counts items per type and reports runs_indexed / last_import_at", () => {
    const index = buildCatalogIndex(RUNS);
    const stats = catalogStats(index);
    expect(stats.counts.claim).toBe(3);
    expect(stats.counts.inference).toBe(1);
    expect(stats.counts.source).toBe(3);
    expect(stats.counts.report).toBe(1);
    expect(stats.counts.reusable_output).toBe(1);
    expect(stats.counts.writeback).toBe(1);
    expect(stats.runs_indexed).toBe(2);
    expect(stats.last_import_at).toBe("2026-02-01T00:00:00Z");
  });
});

describe("sortCatalogItems", () => {
  it("does not mutate the input array", () => {
    const index = buildCatalogIndex(RUNS);
    const items = index.entries.map((e) => e.detail);
    const original = [...items];
    sortCatalogItems(items, "title");
    expect(items).toEqual(original);
  });
});

// ── F-parity sensitivity rules ─────────────────────────────────────────────────

describe("buildCatalogIndex — F-parity sensitivity derivation", () => {
  it("(a) source item sensitivity = max(run sensitivity, source own sensitivity)", () => {
    const runPersonal: RFRunExport = {
      schema_version: "1.3",
      run_id: "run_parity",
      status_derived: "verified",
      // run has 'personal' sensitivity; the source has 'public'
      sensitivity: "personal",
      created_at: "2026-03-01T00:00:00Z",
      claims: [
        {
          claim_id: "cp1",
          text: "Parity claim",
          sources: [makeSource({ source_card_id: "src_public", sensitivity: "public" })],
        },
      ],
      claim_counts: null,
      verification: null,
      governance: null,
      timeline: null,
    };
    const idx = buildCatalogIndex([runPersonal]);
    const srcItem = getCatalogItem(idx, catalogItemId("source", "run_parity", "src_public"));
    // max("personal", "public") = "personal"
    expect(srcItem?.sensitivity).toBe("personal");
  });

  it("(b) report sensitivity = run_content_max (max over run + all cited sources)", () => {
    // run_a has sources with mystery_level; run_content_max = mystery_level
    const index = buildCatalogIndex([runA]);
    const reportItem = getCatalogItem(index, catalogItemId("report", "run_a", "report"));
    expect(reportItem?.sensitivity).toBe("mystery_level");
  });

  it("(b) reusable_output sensitivity = run_content_max", () => {
    // runC: sensitivity=public, one source with work_sensitive — run_content_max=work_sensitive
    const runC: RFRunExport = {
      schema_version: "1.3",
      run_id: "run_c",
      status_derived: "synthesized",
      sensitivity: "public",
      created_at: "2026-03-01T00:00:00Z",
      claims: [
        {
          claim_id: "cc1",
          text: "Claim with work-sensitive source",
          sources: [makeSource({ source_card_id: "src_ws", sensitivity: "work_sensitive" })],
        },
      ],
      claim_counts: null,
      verification: null,
      governance: null,
      timeline: null,
      reusable_output_candidates: [{ description: "Output candidate" }],
    };
    const idx = buildCatalogIndex([runC]);
    const roItem = getCatalogItem(idx, catalogItemId("reusable_output", "run_c", "ro_0"));
    expect(roItem?.sensitivity).toBe("work_sensitive");
  });

  it("(b) report and reusable_output stay at run sensitivity when there are no sources", () => {
    // run_b has no claims/sources; runContentMax = runSensitivity = "public"
    const index = buildCatalogIndex([runB]);
    const roItem = getCatalogItem(index, catalogItemId("reusable_output", "run_b", "ro_0"));
    expect(roItem?.sensitivity).toBe("public");
  });

  it("(c) writeback sensitivity = run sensitivity (unchanged)", () => {
    const index = buildCatalogIndex([runB]);
    const wbItem = getCatalogItem(index, catalogItemId("writeback", "run_b", "wb_meatywiki"));
    // run_b.sensitivity = null → "public"; writebacks always get run sensitivity
    expect(wbItem?.sensitivity).toBe("public");
  });

  it("F6: writeback local_ref uses target.target field, falls back to 'unknown'", () => {
    const runWb: RFRunExport = {
      schema_version: "1.3",
      run_id: "run_wb",
      status_derived: "published",
      sensitivity: "public",
      created_at: "2026-03-01T00:00:00Z",
      claims: [],
      claim_counts: null,
      verification: null,
      governance: null,
      timeline: null,
      writebacks: {
        // No 'target' field → falls back to "unknown"
        targets: [{ name: "SomeTool", status: "Published" }],
        approved_for_writeback: true,
      },
    };
    const idx = buildCatalogIndex([runWb]);
    const wbItem = getCatalogItem(idx, catalogItemId("writeback", "run_wb", "wb_unknown"));
    expect(wbItem?.local_ref).toBe("wb_unknown");
  });
});

// ── D4 Parity: report→claim links from report_anchors ─────────────────────────

describe("buildCatalogIndex — report→claim links from report_anchors (D4 parity)", () => {
  it("derives report→claim 'contains' links from report_anchors.claim_links (not report_locations)", () => {
    // runA has report_anchors with c1 linked; the report→claim link MUST come from anchors.
    const index = buildCatalogIndex([runA]);
    const reportItem = getCatalogItem(index, catalogItemId("report", "run_a", "report"));
    expect(reportItem?.links.outgoing).toContainEqual({
      relation: "contains",
      catalog_item_id: catalogItemId("claim", "run_a", "c1"),
    });
  });

  it("skips missing_claim entries (link_status=missing_claim is never emitted as a catalog link)", () => {
    const index = buildCatalogIndex([runA]);
    const reportItem = getCatalogItem(index, catalogItemId("report", "run_a", "report"));
    // clm_missing is in the anchors with missing_claim — must not appear in outgoing links.
    const outgoingIds = (reportItem?.links.outgoing ?? []).map((l) => l.catalog_item_id);
    expect(outgoingIds).not.toContain(catalogItemId("claim", "run_a", "clm_missing"));
    expect(outgoingIds).not.toContain(catalogItemId("inference", "run_a", "clm_missing"));
  });

  it("deduplicates links when the same claim_id appears in multiple anchor blocks", () => {
    const dupeAnchors: RFReportAnchorBlock[] = [
      {
        block_id: "dup0000000001",
        section_id: null,
        paragraph_ordinal: 0,
        text_hash: "aa1122334455",
        claim_links: [{ claim_id: "c1", span_start: 0, span_end: 16, relation: "supports", link_status: "linked" }],
      },
      {
        block_id: "dup0000000002",
        section_id: "sec",
        paragraph_ordinal: 0,
        text_hash: "bb2233445566",
        claim_links: [{ claim_id: "c1", span_start: 5, span_end: 21, relation: "supports", link_status: "linked" }],
      },
    ];
    const runDupe: RFRunExport = {
      ...runA,
      run_id: "run_dupe",
      report_anchors: dupeAnchors,
    };
    const index = buildCatalogIndex([runDupe]);
    const reportItem = getCatalogItem(index, catalogItemId("report", "run_dupe", "report"));
    const containsLinks = (reportItem?.links.outgoing ?? []).filter((l) => l.relation === "contains");
    // c1 appears twice but must be deduped to a single "contains" link.
    const c1LinkCount = containsLinks.filter(
      (l) => l.catalog_item_id === catalogItemId("claim", "run_dupe", "c1"),
    ).length;
    expect(c1LinkCount).toBe(1);
  });

  it("emits no report→claim links when report_anchors is null (pre-1.4 export)", () => {
    const runNoAnchors: RFRunExport = {
      ...runA,
      run_id: "run_no_anchors",
      report_anchors: null,
    };
    const index = buildCatalogIndex([runNoAnchors]);
    const reportItem = getCatalogItem(index, catalogItemId("report", "run_no_anchors", "report"));
    const containsLinks = (reportItem?.links.outgoing ?? []).filter((l) => l.relation === "contains");
    expect(containsLinks).toHaveLength(0);
  });

  it("emits no report→claim links when report_anchors is absent (key missing, old export)", () => {
    const { report_anchors: _dropped, ...runBase } = runA as RFRunExport & { report_anchors?: unknown };
    const runAbsent: RFRunExport = { ...runBase, run_id: "run_absent_anchors" };
    const index = buildCatalogIndex([runAbsent]);
    const reportItem = getCatalogItem(index, catalogItemId("report", "run_absent_anchors", "report"));
    const containsLinks = (reportItem?.links.outgoing ?? []).filter((l) => l.relation === "contains");
    expect(containsLinks).toHaveLength(0);
  });
});

// ── normalizeCatalogItemDetail ─────────────────────────────────────────────────

describe("normalizeCatalogItemDetail — F5 fetch-boundary normalizer", () => {
  function makeDetail(overrides: Partial<CatalogItemDetail>): CatalogItemDetail {
    return {
      catalog_item_id: "ci_test000001",
      item_type: "claim",
      title: "Test claim",
      summary: null,
      run_id: "run_test",
      local_ref: "c_test",
      project: null,
      status: "supported",
      sensitivity: "public",
      trust_label: null,
      confidence: "high",
      source_count: 1,
      created_at: null,
      updated_at: null,
      payload: {},
      links: { outgoing: [], incoming: [] },
      ...overrides,
    };
  }

  it("pass-through: non-claim/inference items are returned unchanged", () => {
    const item = makeDetail({ item_type: "source", payload: { url: "https://example.com" } });
    const result = normalizeCatalogItemDetail(item);
    expect(result).toBe(item); // strict reference equality — no allocation
  });

  it("pass-through (idempotent): claim with sources+provenance already set is returned unchanged", () => {
    const item = makeDetail({
      item_type: "claim",
      payload: {
        sources: [{ source_card_id: "s1", evidence_id: "e1", relation: "supports", resolved: true, dangling: false }],
        provenance: { source_card: true, extraction: false, inference: false, report: false, writeback: false },
      },
    });
    const result = normalizeCatalogItemDetail(item);
    expect(result).toBe(item); // strict reference equality — no allocation
  });

  it("maps backend cited_sources to sources as minimal RFResolvedSource shapes", () => {
    const item = makeDetail({
      item_type: "claim",
      payload: {
        inference_basis: { from_claims: [], reasoning_summary: null },
        report_locations: [],
        cited_sources: [
          { source_card_id: "sc_a", evidence_id: "ev_a", relation: "supports", locator: "p.1" },
          { source_card_id: "sc_b", evidence_id: "ev_b", relation: "context", locator: null },
        ],
      },
    });
    const result = normalizeCatalogItemDetail(item);
    const sources = result.payload.sources as unknown[];
    expect(sources).toHaveLength(2);
    expect(sources[0]).toMatchObject({
      source_card_id: "sc_a",
      evidence_id: "ev_a",
      relation: "supports",
      locator: "p.1",
      resolved: true,
      dangling: false,
    });
    expect(sources[1]).toMatchObject({ source_card_id: "sc_b", relation: "context", locator: null });
  });

  it("synthesizes provenance from cited_sources and inference_basis", () => {
    const item = makeDetail({
      item_type: "inference",
      payload: {
        inference_basis: { from_claims: ["c1"], reasoning_summary: "Derived." },
        report_locations: [{ heading: "Findings" }],
        cited_sources: [
          { source_card_id: "sc_a", evidence_id: "ev_a", relation: "supports", locator: "p.1" },
        ],
      },
    });
    const result = normalizeCatalogItemDetail(item);
    const prov = result.payload.provenance as Record<string, boolean>;
    expect(prov.source_card).toBe(true);
    expect(prov.extraction).toBe(true); // locator present
    expect(prov.inference).toBe(true);  // item_type === "inference"
    expect(prov.report).toBe(true);     // report_locations non-empty
    expect(prov.writeback).toBe(false); // cannot determine from payload alone
  });

  it("synthesizes provenance with source_card=false when cited_sources is empty", () => {
    const item = makeDetail({
      item_type: "inference",
      payload: {
        inference_basis: { from_claims: ["c_base"], reasoning_summary: null },
        report_locations: [],
        cited_sources: [],
      },
    });
    const result = normalizeCatalogItemDetail(item);
    const prov = result.payload.provenance as Record<string, boolean>;
    expect(prov.source_card).toBe(false);
    expect(prov.extraction).toBe(false);
    expect(prov.inference).toBe(true); // from_claims non-empty → inference
    expect(prov.report).toBe(false);
  });

  it("synthesizes provenance for claim type (not inference)", () => {
    const item = makeDetail({
      item_type: "claim",
      payload: {
        inference_basis: { from_claims: [], reasoning_summary: null },
        report_locations: [],
        cited_sources: [
          { source_card_id: "sc_x", evidence_id: "ev_x", relation: "supports", locator: null },
        ],
      },
    });
    const result = normalizeCatalogItemDetail(item);
    const prov = result.payload.provenance as Record<string, boolean>;
    expect(prov.source_card).toBe(true);
    expect(prov.extraction).toBe(false); // no locator
    expect(prov.inference).toBe(false);  // claim type, no from_claims
  });
});
