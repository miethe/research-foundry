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

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, render, act, waitFor, fireEvent } from "@testing-library/react";
import React from "react";
import { AuthProvider, useAuth, getAuthConfig } from "@/auth/AuthContext";
import { useClerkAuth } from "@/auth/useClerkAuth";
import { setAuthTokenResolver, getLoopbackAuthHeaders } from "@/api/client";

// ── Clerk mock (file-level; hoisted before imports execute) ───────────────────
// Provides a controllable getToken() stub so useClerkAuth tests run without a
// live Clerk session or @clerk/clerk-react peer installation.
vi.mock("@clerk/clerk-react", () => ({
  useAuth: vi.fn(() => ({
    getToken: vi.fn().mockResolvedValue(null),
  })),
  ClerkProvider: ({ children }: { children: unknown }) => children,
  SignIn: () => null,
}));

// Typed reference to the mocked Clerk useAuth so tests can control getToken():
import { useAuth as clerkUseAuth } from "@clerk/clerk-react";
const mockClerkUseAuth = vi.mocked(clerkUseAuth);

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

describe("P5 loopbackGet auth resolver + rate-limit contract", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("surfaces a 403 as ClientError (does not swallow it)", async () => {
    setEnv({
      VITE_RUNS_FRONTEND_LOOPBACK_API: "true",
      VITE_RUNS_LOOPBACK_API_BASE: "http://127.0.0.1:7432/api",
      VITE_RUNS_LOOPBACK_API_TOKEN: "any-token",
    });

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Forbidden" }), {
        status: 403,
        statusText: "Forbidden",
        headers: { "Content-Type": "application/json" },
      }),
    );

    const { fetchRunList, ClientError } = await import("@/api/client");
    await expect(fetchRunList()).rejects.toBeInstanceOf(ClientError);
    await expect(fetchRunList()).rejects.toMatchObject({ status: 403 });

    vi.restoreAllMocks();
  });

  it("uses injected auth token resolver (local_static session) over env token", async () => {
    setEnv({
      VITE_RUNS_FRONTEND_LOOPBACK_API: "true",
      VITE_RUNS_LOOPBACK_API_BASE: "http://127.0.0.1:7432/api",
      VITE_RUNS_LOOPBACK_API_TOKEN: "env-token-should-not-be-used",
    });

    let capturedInit: RequestInit | undefined;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      capturedInit = init;
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    const { fetchRunList, setAuthTokenResolver } = await import("@/api/client");
    // Simulate AuthContext injecting a local_static session bearer after login
    setAuthTokenResolver(() => "local-static-session-token");
    await fetchRunList();

    expect(getAuthHeader(capturedInit)).toBe("Bearer local-static-session-token");

    vi.restoreAllMocks();
  });

  it("uses injected auth token resolver (clerk session) over env token", async () => {
    setEnv({
      VITE_RUNS_FRONTEND_LOOPBACK_API: "true",
      VITE_RUNS_LOOPBACK_API_BASE: "http://127.0.0.1:7432/api",
      VITE_RUNS_LOOPBACK_API_TOKEN: "env-token-should-not-be-used",
    });

    let capturedInit: RequestInit | undefined;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (_input, init) => {
      capturedInit = init;
      return new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    // Simulate Clerk's getToken() being wrapped as a resolver by ClerkShell
    const mockClerkGetToken = vi.fn<[], string | null>().mockReturnValue("clerk-session-token");
    const { fetchRunList, setAuthTokenResolver } = await import("@/api/client");
    setAuthTokenResolver(() => mockClerkGetToken());
    await fetchRunList();

    expect(getAuthHeader(capturedInit)).toBe("Bearer clerk-session-token");
    expect(mockClerkGetToken).toHaveBeenCalledOnce();

    vi.restoreAllMocks();
  });

  it("omits Authorization header when resolver returns null and env token unset", async () => {
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

    const { fetchRunList, setAuthTokenResolver } = await import("@/api/client");
    setAuthTokenResolver(() => null);
    await fetchRunList();

    expect(getAuthHeader(capturedInit)).toBeNull();

    vi.restoreAllMocks();
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// P5-a regression: AuthProvider with VITE_AUTH_PROVIDER=local_static
// ═════════════════════════════════════════════════════════════════════════════

describe("AuthProvider — local_static provider + resolver install (P1-a regression)", () => {
  afterEach(() => {
    // Clear the static module's resolver so tests don't contaminate each other.
    setAuthTokenResolver(null);
    vi.restoreAllMocks();
    setEnv({ VITE_AUTH_PROVIDER: undefined, VITE_RUNS_LOOPBACK_API_TOKEN: undefined });
  });

  it("AuthProvider with VITE_AUTH_PROVIDER=local_static installs resolver with non-null authMode", async () => {
    setEnv({
      VITE_AUTH_PROVIDER: "local_static",
      VITE_RUNS_LOOPBACK_API_TOKEN: undefined,
    });

    // getAuthConfig() is what AuthProvider calls at mount to resolve the mode.
    // P1-a regression guard: when AuthProvider IS in the provider tree (P1-a fix),
    // useAuth() everywhere in the app reads this value — not the default "none".
    const { authMode } = getAuthConfig();
    expect(authMode).toBe("local_static");
    expect(authMode).not.toBe("none");

    // In local_static mode, AuthProvider renders LocalLoginForm when identity is null.
    // Render it and verify the login UI is present (confirms correct mode dispatch).
    // NOTE: renderHook with an AuthProvider wrapper doesn't work for local_static because
    // AuthProvider renders LocalLoginForm instead of children when unauthenticated. We use
    // render() and interact with the form directly.
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          user_id: "u-test",
          workspace_id: "ws-test",
          roles: ["admin"],
          token: "local-static-session-bearer",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const { container } = render(React.createElement(AuthProvider, null, null));

    const usernameInput = container.querySelector<HTMLInputElement>("#rv-login-username");
    const passwordInput = container.querySelector<HTMLInputElement>("#rv-login-password");
    const form = container.querySelector("form");

    // The login form must be present (confirms AuthProvider rendered correctly in local_static mode).
    expect(usernameInput).not.toBeNull();
    expect(form).not.toBeNull();

    await act(async () => {
      fireEvent.change(usernameInput!, { target: { value: "admin" } });
      fireEvent.change(passwordInput!, { target: { value: "pass" } });
      fireEvent.submit(form!);
    });

    // After successful login, the resolver must return the session bearer token.
    // getLoopbackAuthHeaders() delegates to buildAuthHeaders() which reads the resolver.
    await waitFor(() => {
      expect(getLoopbackAuthHeaders()["Authorization"]).toBe(
        "Bearer local-static-session-bearer",
      );
    });
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// P1-b fix: Clerk JWT forwarded through useClerkAuth → ClerkShell → resolver
// ═════════════════════════════════════════════════════════════════════════════

describe("useClerkAuth — Clerk JWT forwarding through resolver (P1-b fix)", () => {
  beforeEach(() => {
    // Configure the Clerk mock to return a test JWT from getToken().
    mockClerkUseAuth.mockReturnValue({
      getToken: vi.fn().mockResolvedValue("clerk-test-jwt-fixture"),
    } as unknown as ReturnType<typeof clerkUseAuth>);

    // Mock the identity endpoint that useClerkAuth calls after getting the token.
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          user_id: "u-clerk",
          workspace_id: "ws-clerk",
          roles: ["researcher"],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
  });

  afterEach(() => {
    setAuthTokenResolver(null);
    vi.restoreAllMocks();
  });

  it("In Clerk mode after identity resolves, buildAuthHeaders() includes Authorization with Clerk token", async () => {
    const { result } = renderHook(() => useClerkAuth());
    await waitFor(() => expect(result.current.loading).toBe(false));

    // P1-b fix: useClerkAuth must expose the resolved JWT so ClerkShell can
    // forward it to setAuthTokenResolver. On current (unfixed) code this assertion
    // fails because UseClerkAuthResult has no token field → result.current.token
    // is undefined, not "clerk-test-jwt-fixture".
    expect(result.current.token).toBe("clerk-test-jwt-fixture");

    // Simulate what AuthContext.tsx does in handleClerkIdentityResolved after
    // ClerkShell passes the token in the identity: installs the resolver.
    setAuthTokenResolver(() => result.current.token ?? null);

    // buildAuthHeaders() (via getLoopbackAuthHeaders) must include Authorization.
    expect(getLoopbackAuthHeaders()["Authorization"]).toBe(
      "Bearer clerk-test-jwt-fixture",
    );
  });
});

// ═════════════════════════════════════════════════════════════════════════════
// AC-5a regression: auth_mode=none sends no Authorization header
// ═════════════════════════════════════════════════════════════════════════════

describe("AuthProvider — auth_mode=none sends no Authorization header (AC-5a)", () => {
  afterEach(() => {
    setAuthTokenResolver(null);
    vi.restoreAllMocks();
    setEnv({ VITE_AUTH_PROVIDER: undefined, VITE_RUNS_LOOPBACK_API_TOKEN: undefined });
  });

  it("auth_mode=none still sends no Authorization header", () => {
    // No VITE_AUTH_PROVIDER set → getAuthConfig() returns { authMode: "none" }.
    setEnv({ VITE_AUTH_PROVIDER: undefined, VITE_RUNS_LOOPBACK_API_TOKEN: undefined });

    const wrapper = ({ children }: { children: React.ReactNode }): React.ReactElement =>
      React.createElement(AuthProvider, null, children);
    const { result } = renderHook(() => useAuth(), { wrapper });

    // AC-5a: authMode must be "none" when no provider is configured.
    expect(result.current.authMode).toBe("none");

    // No resolver is installed; no env token is set → headers must not include Authorization.
    expect(getLoopbackAuthHeaders()["Authorization"]).toBeUndefined();
  });
});
