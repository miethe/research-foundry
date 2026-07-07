/**
 * useClerkAuth unit tests — CLK-4.5 / AC P5.4-B.
 *
 * Tests run without a live Clerk dependency. @clerk/clerk-react is mocked
 * entirely via vi.mock factory — getToken() returns controlled fixture tokens.
 * fetch is spied to return fixture or error responses per test.
 *
 * Gate #3 invariant: no real Clerk keys, no live JWKS endpoints. All tokens
 * are fixture strings; no actual JWT signing or JWKS fetching occurs here.
 *
 * Test matrix:
 *   1. Valid fixture-signed token → identity populated, loading false, error null
 *   2. Bad/expired token (401 from backend) → identity null, explicit 401 error,
 *      non-generic message, loading false
 *   3. null/unauthenticated (getToken() returns null) → identity null, explicit
 *      401 error, loading false
 *   4. AC P5.4-B: malformed backend response body → explicit 502 error, identity
 *      null — never silently-empty identity that could be mistaken for auth_mode=none
 *   5. AC P5.4-B: null backend response body → same explicit 502 error
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

// vi.mock is hoisted by vitest before the imports below execute.
// The factory creates a virtual mock — no live Clerk API is reachable from tests.
vi.mock("@clerk/clerk-react", () => ({
  useAuth: vi.fn(),
}));

import { useAuth } from "@clerk/clerk-react";
import { useClerkAuth, type AuthIdentity } from "./useClerkAuth";
import { ClientError } from "@/api/client";

// ---------------------------------------------------------------------------
// Typed mock reference
// ---------------------------------------------------------------------------

const mockUseAuth = vi.mocked(useAuth);

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

/**
 * Minimal valid AuthIdentity fixture — shape matches the backend dataclass:
 * { user_id: str, workspace_id: str, roles: tuple[str, ...] → string[] in JSON }
 */
const FIXTURE_IDENTITY: AuthIdentity = {
  user_id: "user_test_clk01",
  workspace_id: "ws_test_clk01",
  roles: ["researcher"],
};

/** Build a minimal Response with JSON body and the given status code. */
function makeJsonResponse(body: unknown, status = 200): Response {
  const statusText = status === 200 ? "OK" : status === 401 ? "Unauthorized" : "Error";
  return new Response(JSON.stringify(body), {
    status,
    statusText,
    headers: { "Content-Type": "application/json" },
  });
}

/**
 * Configure mockUseAuth to return a getToken function that resolves to the
 * given value. Pass null to simulate an unauthenticated / no-session state.
 */
function setupGetToken(resolvedValue: string | null): void {
  mockUseAuth.mockReturnValue({
    getToken: vi.fn().mockResolvedValue(resolvedValue),
  } as unknown as ReturnType<typeof useAuth>);
}

// ---------------------------------------------------------------------------
// Cleanup
// ---------------------------------------------------------------------------

afterEach(() => {
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// Test 1 — Valid fixture-signed token
// ---------------------------------------------------------------------------

describe("useClerkAuth — valid fixture-signed token", () => {
  it("populates identity with expected AuthIdentity shape, loading false, error null", async () => {
    setupGetToken("fixture.valid.jwt.header.payload.sig");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      makeJsonResponse(FIXTURE_IDENTITY),
    );

    const { result } = renderHook(() => useClerkAuth());

    // Initially in-flight
    expect(result.current.loading).toBe(true);

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.identity).toEqual(FIXTURE_IDENTITY);
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it("identity.roles is a string array matching the fixture", async () => {
    setupGetToken("fixture.valid.jwt.header.payload.sig");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      makeJsonResponse(FIXTURE_IDENTITY),
    );

    const { result } = renderHook(() => useClerkAuth());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(Array.isArray(result.current.identity?.roles)).toBe(true);
    expect(result.current.identity?.roles).toContain("researcher");
  });

  it("sends Authorization: Bearer <token> to the identity endpoint", async () => {
    setupGetToken("my-fixture-test-token");

    let capturedHeaders: Record<string, string> | undefined;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      capturedHeaders = init?.headers as Record<string, string>;
      return makeJsonResponse(FIXTURE_IDENTITY);
    });

    const { result } = renderHook(() => useClerkAuth());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(capturedHeaders?.["Authorization"]).toBe("Bearer my-fixture-test-token");
  });
});

// ---------------------------------------------------------------------------
// Test 2 — Bad/expired token (backend returns 401)
// ---------------------------------------------------------------------------

describe("useClerkAuth — bad/expired token", () => {
  it("resolves identity null, error 401 with non-generic message, loading false", async () => {
    setupGetToken("expired.or.bad.signature.token");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      makeJsonResponse({ detail: "Token expired" }, 401),
    );

    const { result } = renderHook(() => useClerkAuth());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.identity).toBeNull();
    expect(result.current.error).not.toBeNull();
    expect(result.current.error).toBeInstanceOf(ClientError);
    expect(result.current.error?.status).toBe(401);

    // Message must describe the failure class — not a generic "Error" or "failed"
    expect(result.current.error?.message).toMatch(
      /Authentication failed|token rejected|session expired/i,
    );
    expect(result.current.loading).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// Test 3 — null / unauthenticated state (getToken() returns null)
// ---------------------------------------------------------------------------

describe("useClerkAuth — null / unauthenticated (getToken returns null)", () => {
  it("resolves identity null, explicit 401 ClientError, loading false", async () => {
    setupGetToken(null);

    const { result } = renderHook(() => useClerkAuth());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.identity).toBeNull();
    expect(result.current.error).not.toBeNull();
    expect(result.current.error).toBeInstanceOf(ClientError);
    expect(result.current.error?.status).toBe(401);

    // Error message must distinguish "no session" from a token rejection
    expect(result.current.error?.message).toMatch(/no active Clerk session/i);
    expect(result.current.loading).toBe(false);
  });

  it("does NOT call fetch when getToken returns null", async () => {
    setupGetToken(null);
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const { result } = renderHook(() => useClerkAuth());
    await waitFor(() => expect(result.current.loading).toBe(false));

    // No network request should be made when there is no session
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

// ---------------------------------------------------------------------------
// Test 4 — AC P5.4-B: malformed backend response body
// ---------------------------------------------------------------------------

describe("useClerkAuth — AC P5.4-B: missing/malformed identity response", () => {
  it("surfaces explicit 502 ClientError when response body has wrong shape", async () => {
    setupGetToken("valid.looking.token.body.here");
    // Backend returns HTTP 200 but with a body that does not match AuthIdentity
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      makeJsonResponse({ unexpected_field: "not_an_identity" }),
    );

    const { result } = renderHook(() => useClerkAuth());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.identity).toBeNull();
    expect(result.current.error).not.toBeNull();
    expect(result.current.error).toBeInstanceOf(ClientError);
    expect(result.current.error?.status).toBe(502);

    // Message must describe the structural failure, not be vague
    expect(result.current.error?.message).toMatch(/malformed|missing required fields/i);
    expect(result.current.loading).toBe(false);
  });

  it("surfaces explicit 502 error when response body is null", async () => {
    setupGetToken("valid.looking.token.body.here");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(makeJsonResponse(null));

    const { result } = renderHook(() => useClerkAuth());
    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(result.current.identity).toBeNull();
    expect(result.current.error).not.toBeNull();
    expect(result.current.error?.status).toBe(502);
    expect(result.current.loading).toBe(false);
  });

  it("never returns silent empty identity — error is always set when identity is null after loading", async () => {
    setupGetToken("valid.looking.token.body.here");
    // Partial response: has user_id but is missing workspace_id and roles
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      makeJsonResponse({ user_id: "user_partial" }),
    );

    const { result } = renderHook(() => useClerkAuth());
    await waitFor(() => expect(result.current.loading).toBe(false));

    // AC P5.4-B invariant: identity null → error must be non-null (never silently empty)
    if (result.current.identity === null) {
      expect(result.current.error).not.toBeNull();
    }

    expect(result.current.identity).toBeNull();
    expect(result.current.error).not.toBeNull();
    expect(result.current.error?.status).toBe(502);
  });
});
