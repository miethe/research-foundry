/**
 * clearance-gates-v1 M4 — clinical-attestation reactive store (api/client.ts).
 *
 * `getClinicalContentPresent()`/`subscribeClinicalContentPresent()` mirror
 * the GATE-900 `RateLimitState` reactive-singleton pattern (see
 * p5-auth-header.test.ts's own rate-limit describe block for the sibling
 * test style this file follows): `fetchRunDetail()` recomputes the flag on
 * every call from data already present on `RFRunExport.claims[]`, purely
 * client-side, no separate network call.
 *
 * client.ts reads LOOPBACK_ENABLED as a module-level constant, so each test
 * uses vi.resetModules() + a dynamic import to force fresh module state with
 * patched import.meta.env values -- same convention p5-auth-header.test.ts
 * uses.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import type { RFRunExport } from "@/types/rf";

function setEnv(overrides: Record<string, string | boolean | undefined>) {
  for (const [k, v] of Object.entries(overrides)) {
    if (v === undefined) {
      // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
      delete (import.meta.env as Record<string, unknown>)[k];
    } else {
      (import.meta.env as Record<string, unknown>)[k] = v;
    }
  }
}

function makeRun(overrides: Partial<RFRunExport> & { run_id: string }): RFRunExport {
  return {
    schema_version: "2.0",
    status_derived: "published",
    claims: [],
    ...overrides,
  };
}

describe("clinical-attestation store (clearance-gates-v1 M4)", () => {
  beforeEach(() => {
    vi.resetModules();
    setEnv({
      VITE_RUNS_FRONTEND_LOOPBACK_API: "true",
      VITE_RUNS_LOOPBACK_API_BASE: "http://127.0.0.1:7432/api",
      VITE_RUNS_LOOPBACK_API_TOKEN: undefined,
    });
  });

  it("initial state is false before any fetch", async () => {
    const { getClinicalContentPresent } = await import("@/api/client");
    expect(getClinicalContentPresent()).toBe(false);
  });

  it("a run with an unattested clinical claim sets the flag true", async () => {
    const run = makeRun({
      run_id: "rf_run_clinical_001",
      claims: [
        {
          claim_id: "clm_001",
          text: "Threshold claim.",
          sources: [],
          clinical_attestation_status: "unattested",
        },
      ],
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(run), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { fetchRunDetail, getClinicalContentPresent } = await import("@/api/client");
    await fetchRunDetail("rf_run_clinical_001");

    expect(getClinicalContentPresent()).toBe(true);
    vi.restoreAllMocks();
  });

  it("a run with zero unattested clinical claims sets/keeps the flag false", async () => {
    const run = makeRun({
      run_id: "rf_run_ordinary_001",
      claims: [
        { claim_id: "clm_001", text: "Ordinary claim.", sources: [] },
      ],
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(run), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { fetchRunDetail, getClinicalContentPresent } = await import("@/api/client");
    await fetchRunDetail("rf_run_ordinary_001");

    expect(getClinicalContentPresent()).toBe(false);
    vi.restoreAllMocks();
  });

  it("navigating from a clinical run to a clean run clears the flag (not sticky)", async () => {
    const clinicalRun = makeRun({
      run_id: "rf_run_clinical_002",
      claims: [
        {
          claim_id: "clm_001",
          text: "Threshold claim.",
          sources: [],
          clinical_attestation_status: "unattested",
        },
      ],
    });
    const cleanRun = makeRun({
      run_id: "rf_run_clean_002",
      claims: [{ claim_id: "clm_002", text: "Ordinary claim.", sources: [] }],
    });

    const { fetchRunDetail, getClinicalContentPresent } = await import("@/api/client");

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(clinicalRun), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await fetchRunDetail("rf_run_clinical_002");
    expect(getClinicalContentPresent()).toBe(true);

    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(cleanRun), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    await fetchRunDetail("rf_run_clean_002");
    expect(getClinicalContentPresent()).toBe(false);

    vi.restoreAllMocks();
  });

  it("subscribers are notified on each fetchRunDetail() call", async () => {
    const run = makeRun({
      run_id: "rf_run_clinical_003",
      claims: [
        {
          claim_id: "clm_001",
          text: "Threshold claim.",
          sources: [],
          clinical_attestation_status: "unattested",
        },
      ],
    });
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(run), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { fetchRunDetail, subscribeClinicalContentPresent } = await import("@/api/client");
    const seen: boolean[] = [];
    const unsubscribe = subscribeClinicalContentPresent((present) => seen.push(present));

    await fetchRunDetail("rf_run_clinical_003");

    expect(seen).toEqual([true]);
    unsubscribe();
    vi.restoreAllMocks();
  });
});
