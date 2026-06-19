/**
 * P2-HOOKS — contract tests for all four React Query hooks.
 *
 * Tests run in static fixture mode. No API mock is needed because the client
 * defaults to static fixture mode when VITE_RUNS_FRONTEND_LOOPBACK_API is unset
 * (the default in the Vitest environment).
 *
 * The fixture at src/test/fixtures/run.json has 91 claims and is the RF export
 * produced by the P1 integration test.
 *
 * Test names:
 *   useRunList: returns a summary array
 *   useRunList: summary has required fields (run_id, status_derived)
 *   useRunDetail: returns the full run export for the fixture run
 *   useRunDetail: claims array has 91 entries (fixture)
 *   useRunDetail: is disabled when runId is empty string
 *   useClaimLedger: returns claims array for a valid runId
 *   useClaimLedger: claims have claim_id and text
 *   useClaimLedger: is disabled when runId is empty string
 *   useSourceCard: returns a resolved source for a known sourceCardId
 *   useSourceCard: returns null for an unknown sourceCardId
 *   useSourceCard: is disabled when runId is empty string
 *   useSourceCard: is disabled when sourceCardId is empty string
 */
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";

import { useRunList }     from "./useRunList";
import { useRunDetail }   from "./useRunDetail";
import { useClaimLedger } from "./useClaimLedger";
import { useSourceCard }  from "./useSourceCard";

// Import fixtures directly for assertion constants — NOT used inside vi.mock
import type { RFRunExport } from "@/types/rf";
import fixtureRunRaw from "@/test/fixtures/run.json";

const fixtureRun = fixtureRunRaw as unknown as RFRunExport;
const FIXTURE_RUN_ID = fixtureRun.run_id;
const FIXTURE_CLAIM_COUNT = fixtureRun.claims.length;
// Pick the first source card id from the first claim in the fixture
const FIXTURE_FIRST_SOURCE_ID =
  fixtureRun.claims[0]?.sources?.[0]?.source_card_id ?? "";

// ── Test helpers ─────────────────────────────────────────────────────────────

function makeWrapper() {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
    },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
  };
}

// ── useRunList ────────────────────────────────────────────────────────────────

describe("useRunList", () => {
  let wrapper: ReturnType<typeof makeWrapper>;

  beforeEach(() => {
    wrapper = makeWrapper();
  });

  it("returns a summary array", async () => {
    const { result } = renderHook(() => useRunList(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data!.length).toBeGreaterThan(0);
  });

  it("summary has required fields (run_id, status_derived)", async () => {
    const { result } = renderHook(() => useRunList(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const first = result.current.data![0];
    expect(typeof first!.run_id).toBe("string");
    expect(typeof first!.status_derived).toBe("string");
  });
});

// ── useRunDetail ──────────────────────────────────────────────────────────────

describe("useRunDetail", () => {
  let wrapper: ReturnType<typeof makeWrapper>;

  beforeEach(() => {
    wrapper = makeWrapper();
  });

  it("returns the full run export for the fixture run", async () => {
    const { result } = renderHook(() => useRunDetail(FIXTURE_RUN_ID), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.run_id).toBe(FIXTURE_RUN_ID);
    expect(result.current.data?.schema_version).toBe(fixtureRunRaw.schema_version);
  });

  it(`claims array has ${FIXTURE_CLAIM_COUNT} entries (fixture)`, async () => {
    const { result } = renderHook(() => useRunDetail(FIXTURE_RUN_ID), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data?.claims.length).toBe(FIXTURE_CLAIM_COUNT);
  });

  it("is disabled when runId is empty string", () => {
    const { result } = renderHook(() => useRunDetail(""), { wrapper });
    // disabled query: fetchStatus stays idle, data stays undefined
    expect(result.current.fetchStatus).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });
});

// ── useClaimLedger ────────────────────────────────────────────────────────────

describe("useClaimLedger", () => {
  let wrapper: ReturnType<typeof makeWrapper>;

  beforeEach(() => {
    wrapper = makeWrapper();
  });

  it("returns claims array for a valid runId", async () => {
    const { result } = renderHook(() => useClaimLedger(FIXTURE_RUN_ID), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(Array.isArray(result.current.data)).toBe(true);
    expect(result.current.data!.length).toBe(FIXTURE_CLAIM_COUNT);
  });

  it("claims have claim_id and text", async () => {
    const { result } = renderHook(() => useClaimLedger(FIXTURE_RUN_ID), {
      wrapper,
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    const first = result.current.data![0];
    expect(typeof first!.claim_id).toBe("string");
    expect(typeof first!.text).toBe("string");
  });

  it("is disabled when runId is empty string", () => {
    const { result } = renderHook(() => useClaimLedger(""), { wrapper });
    expect(result.current.fetchStatus).toBe("idle");
    expect(result.current.data).toBeUndefined();
  });
});

// ── useSourceCard ─────────────────────────────────────────────────────────────

describe("useSourceCard", () => {
  let wrapper: ReturnType<typeof makeWrapper>;

  beforeEach(() => {
    wrapper = makeWrapper();
  });

  it("returns a resolved source for a known sourceCardId", async () => {
    const { result } = renderHook(
      () => useSourceCard(FIXTURE_RUN_ID, FIXTURE_FIRST_SOURCE_ID),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).not.toBeNull();
    expect(result.current.data?.source_card_id).toBe(FIXTURE_FIRST_SOURCE_ID);
  });

  it("returns null for an unknown sourceCardId", async () => {
    const { result } = renderHook(
      () => useSourceCard(FIXTURE_RUN_ID, "src_does_not_exist"),
      { wrapper },
    );
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeNull();
  });

  it("is disabled when runId is empty string", () => {
    const { result } = renderHook(
      () => useSourceCard("", FIXTURE_FIRST_SOURCE_ID),
      { wrapper },
    );
    expect(result.current.fetchStatus).toBe("idle");
  });

  it("is disabled when sourceCardId is empty string", () => {
    const { result } = renderHook(
      () => useSourceCard(FIXTURE_RUN_ID, ""),
      { wrapper },
    );
    expect(result.current.fetchStatus).toBe("idle");
  });
});
