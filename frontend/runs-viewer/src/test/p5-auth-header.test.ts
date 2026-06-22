/**
 * P5 auth-header contract tests for loopbackGet().
 *
 * Verifies that:
 *   1. Authorization header is sent when VITE_RUNS_LOOPBACK_API_TOKEN is set.
 *   2. Authorization header is omitted entirely when the token is unset/empty.
 *   3. A 401 response surfaces as a ClientError (not silently swallowed).
 *
 * client.ts reads LOOPBACK_ENABLED and LOOPBACK_BASE as module-level constants,
 * so we use vi.resetModules() + dynamic import in each test to force a fresh
 * module evaluation with patched import.meta.env values.
 *
 * loopbackGet() calls fetch(url: string, init: RequestInit); the mock captures
 * RequestInit to inspect the Authorization header value.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";

/** Extract the Authorization header value from fetch's RequestInit headers. */
function getAuthHeader(init: RequestInit | undefined): string | null {
  if (!init?.headers) return null;
  // client.ts passes headers as a plain Record<string, string>.
  const h = init.headers as Record<string, string>;
  return h["Authorization"] ?? null;
}

/** Set import.meta.env for a test; must be called before the dynamic import. */
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

describe("P5 loopbackGet auth-header contract", () => {
  beforeEach(() => {
    // Reset module registry so the next dynamic import re-evaluates client.ts
    // and picks up the current import.meta.env state.
    vi.resetModules();
  });

  it("sends Authorization: Bearer <token> when VITE_RUNS_LOOPBACK_API_TOKEN is set", async () => {
    setEnv({
      VITE_RUNS_FRONTEND_LOOPBACK_API: "true",
      VITE_RUNS_LOOPBACK_API_BASE: "http://127.0.0.1:7432/api",
      VITE_RUNS_LOOPBACK_API_TOKEN: "test-secret-token",
    });

    let capturedInit: RequestInit | undefined;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      capturedInit = init;
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    // Fresh import — module re-evaluates LOOPBACK_ENABLED / token with new env.
    const { fetchRunList } = await import("@/api/client");
    await fetchRunList();

    expect(getAuthHeader(capturedInit)).toBe("Bearer test-secret-token");

    vi.restoreAllMocks();
  });

  it("omits Authorization header entirely when VITE_RUNS_LOOPBACK_API_TOKEN is unset", async () => {
    setEnv({
      VITE_RUNS_FRONTEND_LOOPBACK_API: "true",
      VITE_RUNS_LOOPBACK_API_BASE: "http://127.0.0.1:7432/api",
      VITE_RUNS_LOOPBACK_API_TOKEN: undefined,
    });

    let capturedInit: RequestInit | undefined;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      capturedInit = init;
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    const { fetchRunList } = await import("@/api/client");
    await fetchRunList();

    expect(getAuthHeader(capturedInit)).toBeNull();

    vi.restoreAllMocks();
  });

  it("omits Authorization header entirely when VITE_RUNS_LOOPBACK_API_TOKEN is empty string", async () => {
    setEnv({
      VITE_RUNS_FRONTEND_LOOPBACK_API: "true",
      VITE_RUNS_LOOPBACK_API_BASE: "http://127.0.0.1:7432/api",
      VITE_RUNS_LOOPBACK_API_TOKEN: "",
    });

    let capturedInit: RequestInit | undefined;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      capturedInit = init;
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    const { fetchRunList } = await import("@/api/client");
    await fetchRunList();

    expect(getAuthHeader(capturedInit)).toBeNull();

    vi.restoreAllMocks();
  });

  it("surfaces a 401 as ClientError (does not swallow it)", async () => {
    setEnv({
      VITE_RUNS_FRONTEND_LOOPBACK_API: "true",
      VITE_RUNS_LOOPBACK_API_BASE: "http://127.0.0.1:7432/api",
      VITE_RUNS_LOOPBACK_API_TOKEN: "wrong-token",
    });

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid token" }), {
        status: 401,
        statusText: "Unauthorized",
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { fetchRunList, ClientError } = await import("@/api/client");
    await expect(fetchRunList()).rejects.toBeInstanceOf(ClientError);
    await expect(fetchRunList()).rejects.toMatchObject({ status: 401 });

    vi.restoreAllMocks();
  });
});
