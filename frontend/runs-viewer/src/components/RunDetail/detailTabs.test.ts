/**
 * detailTabs.test.ts — Unit tests for coerceDetailTab and tabToQuery.
 *
 * Covers:
 * - coerceDetailTab(null) returns 'overview' (AC 3.1 — was previously 'trust')
 * - coerceDetailTab('') returns 'overview'
 * - coerceDetailTab('unknown') returns 'overview'
 * - coerceDetailTab('audit') returns 'ledger' (alias preserved, AC 3.1)
 * - coerceDetailTab('ledger') returns 'ledger' (alias preserved)
 * - Known tab values pass through unchanged
 * - tabToQuery aliases are unchanged
 */

import { describe, it, expect } from "vitest";
import { coerceDetailTab, tabToQuery } from "./detailTabs";

describe("coerceDetailTab — null / unrecognized inputs → 'overview'", () => {
  it("returns 'overview' for null (AC 3.1)", () => {
    expect(coerceDetailTab(null)).toBe("overview");
  });

  it("returns 'overview' for empty string", () => {
    expect(coerceDetailTab("")).toBe("overview");
  });

  it("returns 'overview' for unrecognized string", () => {
    expect(coerceDetailTab("unknown")).toBe("overview");
  });

  it("returns 'overview' for 'trust' (formerly the default; now just a passthrough)", () => {
    // 'trust' is still a valid tab value and should pass through as-is.
    expect(coerceDetailTab("trust")).toBe("trust");
  });
});

describe("coerceDetailTab — audit/ledger alias (must remain unchanged)", () => {
  it("returns 'ledger' for 'audit' (alias preserved)", () => {
    expect(coerceDetailTab("audit")).toBe("ledger");
  });

  it("returns 'ledger' for 'ledger'", () => {
    expect(coerceDetailTab("ledger")).toBe("ledger");
  });
});

describe("coerceDetailTab — known tab values pass through", () => {
  it("returns 'overview' for 'overview'", () => {
    expect(coerceDetailTab("overview")).toBe("overview");
  });

  it("returns 'report' for 'report'", () => {
    expect(coerceDetailTab("report")).toBe("report");
  });

  it("returns 'lineage' for 'lineage'", () => {
    expect(coerceDetailTab("lineage")).toBe("lineage");
  });

  it("returns 'writeback' for 'writeback'", () => {
    expect(coerceDetailTab("writeback")).toBe("writeback");
  });
});

describe("tabToQuery — alias and passthrough", () => {
  it("converts 'ledger' back to 'audit' for URL query param", () => {
    expect(tabToQuery("ledger")).toBe("audit");
  });

  it("returns 'overview' unchanged", () => {
    expect(tabToQuery("overview")).toBe("overview");
  });

  it("returns 'trust' unchanged", () => {
    expect(tabToQuery("trust")).toBe("trust");
  });
});
