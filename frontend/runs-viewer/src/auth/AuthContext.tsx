/**
 * AuthContext.tsx — 3-mode authentication context/provider (P5.8 FEAUTH-001).
 *
 * Three concrete auth modes — no speculative 4th mode (PRD risk table):
 *
 *   provider=clerk        — Clerk-powered login. ClerkProvider + SignIn rendered
 *                           via React.lazy (never bundled unconditionally).
 *
 *   provider=local_static — Username/password login. LocalLoginForm rendered when
 *                           unauthenticated; POST /api/auth/login exchanges credentials.
 *
 *   auth_mode=none        — Passthrough. Children rendered directly with identity=null.
 *                           No login UI, no role/workspace chrome. Current single-operator
 *                           behavior is preserved exactly (AC-5a regression guard).
 *
 * FR-2 Resilience contracts (implemented in this file):
 *   AC-5a: auth_mode=none → identity stays null; no role/workspace affordance rendered.
 *   AC-5c: Missing roles array on AuthIdentity → normalize to [] (least-privilege viewer);
 *          never an error, never elevated privilege.
 *
 * Principal-type surfacing (Phase 5, ACT-502, AC-1):
 *   `principalType` on AuthContextValue tells consuming components whether the
 *   resolved caller is a human session (Clerk / local_static login), a service
 *   account, or a self-issued personal access token (PAT). It is derived from
 *   an optional `principal_type` field on AuthIdentity ("service" | "user_pat")
 *   — which today the backend never emits (see `AuthIdentity` in
 *   `research_foundry/api/auth/provider.py`: no such field exists yet), so
 *   `derivePrincipalType()` always defaults to "human" in the current backend.
 *   The field is read defensively so that once the backend threads
 *   principal-type information through `/api/auth/identity` or the local_static
 *   login response, this file requires no changes. AC-1 resilience: an absent
 *   or unrecognized `principal_type` never errors — it degrades to "human"
 *   (no principal-type badge rendered), exactly like the AC-5c roles default.
 *
 * Static-export detection:
 *   VITE_RUNS_STATIC_EXPORT="true" → forces auth_mode=none regardless of configured
 *   provider. Static exports have no server to authenticate against; data fetches
 *   degrade to the pre-gated export-time read-only public dataset (AC-5 resilience).
 *
 * Bundle-size discipline:
 *   @clerk/clerk-react is imported ONLY inside ClerkShell.tsx, which is loaded via
 *   React.lazy(() => import('./ClerkShell')). The main bundle never contains Clerk code.
 *
 * Provider resolution order:
 *   1. VITE_RUNS_STATIC_EXPORT=true → force auth_mode=none
 *   2. VITE_AUTH_PROVIDER build-time env var ("clerk" | "local_static")
 *   3. rv_auth_provider localStorage (runtime override, same rv_ prefix as viewerSettings)
 *   4. Default: auth_mode=none (backward-compatible single-operator behavior)
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { ClientError, getLoopbackBase, setAuthTokenResolver } from "@/api/client";
import { LocalLoginForm } from "./LocalLoginForm";

// ── Types ─────────────────────────────────────────────────────────────────────

/**
 * AuthIdentity: mirrors the backend AuthIdentity dataclass.
 * Source: src/research_foundry/api/auth/provider.py::AuthIdentity
 *
 * AC-5c: roles is always normalized to [] if absent — never null/undefined.
 * token is present in local_static mode (session bearer), absent in clerk/none.
 */
export interface AuthIdentity {
  user_id: string;
  workspace_id: string;
  /** AC-5c: default [] if absent from payload — never escalates privilege. */
  roles: string[];
  /** local_static session bearer token; absent in clerk/none modes. */
  token?: string;
  /**
   * Optional principal-type hint ("service" | "user_pat") on the resolved
   * identity payload. Forward-compatible field — the backend does not emit
   * this today (see module docstring); read defensively via
   * `derivePrincipalType()`, never assumed present.
   */
  principal_type?: string;
}

/** Resolved caller kind surfaced to admin UI (ACT-502, AC-1). */
export type PrincipalType = "human" | "service" | "user_pat";

export interface AuthContextValue {
  identity: AuthIdentity | null;
  isLoading: boolean;
  /** Resolved provider: "clerk" | "local_static" | "none" */
  provider: string;
  /** Resolved auth mode: "clerk" | "local_static" | "none" */
  authMode: string;
  /**
   * Resolved principal type for the current identity. Defaults to "human"
   * whenever `identity` is null or carries no recognized `principal_type`
   * (AC-1 resilience: absent signal never errors, never renders a badge).
   */
  principalType: PrincipalType;
}

/**
 * Derive the principal type from a resolved identity.
 *
 * AC-1 resilience contract: an absent or unrecognized `principal_type` on
 * *identity* (including `identity === null`) always resolves to "human" —
 * the least-surprising default that renders no principal-type badge, never
 * an error state.
 */
export function derivePrincipalType(
  identity: AuthIdentity | null,
): PrincipalType {
  if (identity?.principal_type === "service") return "service";
  if (identity?.principal_type === "user_pat") return "user_pat";
  return "human";
}

// ── Static-export guard ───────────────────────────────────────────────────────

/**
 * True when built as a static export (no RF API server available).
 * Forces auth_mode=none: no login UI, data degrades to export-time public dataset.
 */
const IS_STATIC_EXPORT: boolean =
  typeof import.meta !== "undefined" &&
  import.meta.env?.VITE_RUNS_STATIC_EXPORT === "true";

// ── Provider resolution ───────────────────────────────────────────────────────

type AuthProvider = "clerk" | "local_static" | "none";

/** Safe localStorage read — returns null on any error (SSR, quota, private mode). */
function lsGet(key: string): string | null {
  try {
    if (typeof window === "undefined") return null;
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

/** The localStorage key for the configured auth provider (rv_ prefix per viewerSettings convention). */
const LS_AUTH_PROVIDER_KEY = "rv_auth_provider";

/**
 * Resolves the active auth provider from env vars and localStorage.
 * Mirrors how getViewerSettings() resolves the theme setting.
 *
 * Never returns a value outside the three concrete modes.
 */
export function getAuthConfig(): { provider: AuthProvider; authMode: AuthProvider } {
  // Static-export builds have no server — force none regardless of configuration
  if (IS_STATIC_EXPORT) {
    return { provider: "none", authMode: "none" };
  }

  // Build-time env var takes precedence (set in .env.production etc.)
  const envProvider = import.meta.env?.VITE_AUTH_PROVIDER as string | undefined;
  if (envProvider === "clerk" || envProvider === "local_static") {
    return { provider: envProvider, authMode: envProvider };
  }

  // Runtime override via localStorage (allows admin to switch without rebuild)
  const storedProvider = lsGet(LS_AUTH_PROVIDER_KEY);
  if (storedProvider === "clerk" || storedProvider === "local_static") {
    return { provider: storedProvider, authMode: storedProvider };
  }

  // Default: auth_mode=none — preserves current single-operator behavior (AC-5a)
  return { provider: "none", authMode: "none" };
}

// ── Lazy Clerk shell ──────────────────────────────────────────────────────────

/**
 * ClerkShell is lazy-loaded ONLY when provider=clerk is resolved.
 * @clerk/clerk-react is never evaluated in other provider modes.
 */
const LazyClerkShell = React.lazy(
  () => import("./ClerkShell"),
);

// ── Local-static auth helper ──────────────────────────────────────────────────

/**
 * Exchange username/password for AuthIdentity + session token via
 * POST /api/auth/login (mediated through the existing client.ts base URL).
 *
 * Security: error messages describe failure classes only — never echo credentials.
 * AC-5c: roles is always normalized to [] if absent from the server payload.
 *
 * @throws {ClientError} on non-2xx HTTP response or malformed response body
 */
async function fetchLocalLogin(
  username: string,
  password: string,
): Promise<AuthIdentity> {
  const url = `${getLoopbackBase()}/auth/login`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const message =
      res.status === 401
        ? "Invalid credentials"
        : res.status === 403
          ? "Account access denied"
          : `Login failed (HTTP ${res.status})`;
    throw new ClientError(res.status, message);
  }

  const data: unknown = await res.json();
  const d = data as Record<string, unknown> | null | undefined;

  if (
    !d ||
    typeof d.user_id !== "string" ||
    typeof d.workspace_id !== "string"
  ) {
    throw new ClientError(
      502,
      "Login response malformed: missing required fields (user_id, workspace_id)",
    );
  }

  return {
    user_id: d.user_id as string,
    workspace_id: d.workspace_id as string,
    // AC-5c: normalize roles to [] if absent — never escalates privilege
    roles: Array.isArray(d.roles) ? (d.roles as string[]) : [],
    token: typeof d.token === "string" ? d.token : undefined,
  };
}

// ── Context definition ────────────────────────────────────────────────────────

const DEFAULT_CONTEXT: AuthContextValue = {
  identity: null,
  isLoading: false,
  provider: "none",
  authMode: "none",
  principalType: "human",
};

export const AuthContext = createContext<AuthContextValue>(DEFAULT_CONTEXT);

// ── AuthProvider ──────────────────────────────────────────────────────────────

export interface AuthProviderProps {
  children: React.ReactNode;
}

/**
 * AuthProvider — resolves the active auth mode at mount and renders the
 * appropriate login surface or passes through to children.
 *
 * Mode dispatch:
 *   auth_mode=none       → passthrough; identity=null; no login UI (AC-5a)
 *   provider=local_static → LocalLoginForm when unauthenticated
 *   provider=clerk       → LazyClerkShell (Clerk SDK never bundled unconditionally)
 *
 * Config is evaluated once at mount (same pattern as applyTheme in AppShell.tsx).
 * React.lazy + Suspense handles the Clerk SDK loading without blocking the tree.
 */
export function AuthProvider({
  children,
}: AuthProviderProps): React.JSX.Element {
  const { provider, authMode } = getAuthConfig();

  const [identity, setIdentity] = useState<AuthIdentity | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Stable callback for local_static login — called by LocalLoginForm.onSubmit
  const handleLocalLogin = useCallback(
    async (username: string, password: string): Promise<void> => {
      setIsLoading(true);
      setLoginError(null);
      try {
        const resolved = await fetchLocalLogin(username, password);
        setIdentity(resolved);
        // P5.8 FEAUTH-003: inject runtime token resolver so loopbackGet() and
        // getLoopbackAuthHeaders() both use the session bearer token.
        setAuthTokenResolver(() => resolved.token ?? null);
      } catch (err) {
        setLoginError(
          err instanceof ClientError
            ? err.message
            : "Login failed — please try again.",
        );
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  // Stable callback for Clerk identity propagation — called by ClerkShell
  const handleClerkIdentityResolved = useCallback(
    (resolved: AuthIdentity): void => {
      setIdentity(resolved);
      // P5.8 FEAUTH-003: wire resolver; in Clerk mode token is typically absent
      // (Clerk manages its own session separately), so this resolves to null and
      // loopbackGet() falls back to VITE_RUNS_LOOPBACK_API_TOKEN.
      setAuthTokenResolver(() => resolved.token ?? null);
    },
    [],
  );

  // Stable callback for Clerk loading state propagation — called by ClerkShell
  const handleClerkLoadingChange = useCallback((loading: boolean): void => {
    setIsLoading(loading);
  }, []);

  // P5.8 FEAUTH-003: clear the token resolver on logout (identity → null).
  // Also fires on initial mount (identity=null) — calling setAuthTokenResolver(null)
  // when the resolver is already null is a no-op in effect.
  useEffect(() => {
    if (identity === null) {
      setAuthTokenResolver(null);
    }
  }, [identity]);

  const contextValue: AuthContextValue = {
    identity,
    isLoading,
    provider,
    authMode,
    // ACT-502/AC-1: defaults to "human" until the backend emits principal_type.
    principalType: derivePrincipalType(identity),
  };

  // ── Mode dispatch ─────────────────────────────────────────────────────────

  // auth_mode=none: pure passthrough — renders children with identity=null.
  // This preserves current single-operator behavior exactly (AC-5a).
  // NOTE: Server-side enforcement (P5.2 require_role, P5.3 workspace scoping) is
  // the actual authorization boundary. Hiding UI here is defense-in-depth only.
  if (authMode === "none") {
    return (
      <AuthContext.Provider value={contextValue}>
        {children}
      </AuthContext.Provider>
    );
  }

  // provider=clerk: lazy-loaded Clerk shell (never bundled unconditionally).
  // Suspense fallback=null avoids a loading flash; Clerk handles its own loading UI.
  if (provider === "clerk") {
    const publishableKey =
      (import.meta.env?.VITE_CLERK_PUBLISHABLE_KEY as string | undefined) ?? "";

    return (
      <AuthContext.Provider value={contextValue}>
        <React.Suspense fallback={null}>
          <LazyClerkShell
            publishableKey={publishableKey}
            onIdentityResolved={handleClerkIdentityResolved}
            onLoadingChange={handleClerkLoadingChange}
          >
            {children}
          </LazyClerkShell>
        </React.Suspense>
      </AuthContext.Provider>
    );
  }

  // provider=local_static: render LocalLoginForm when unauthenticated.
  if (provider === "local_static") {
    if (!identity) {
      return (
        <AuthContext.Provider value={contextValue}>
          <LocalLoginForm
            onSubmit={handleLocalLogin}
            isLoading={isLoading}
            error={loginError}
          />
        </AuthContext.Provider>
      );
    }
    // Authenticated: render children with the resolved identity in context.
    return (
      <AuthContext.Provider value={{ ...contextValue, identity }}>
        {children}
      </AuthContext.Provider>
    );
  }

  // Fallback: should not be reached with a valid 3-mode config, but TypeScript
  // requires an exhaustive return. Treat as auth_mode=none.
  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

// ── useAuth ───────────────────────────────────────────────────────────────────

/**
 * useAuth — consume the resolved auth context.
 *
 * Returns AuthContextValue with:
 *   identity      — null in auth_mode=none or while loading; AuthIdentity when resolved
 *   isLoading     — true while credentials are being exchanged or Clerk session resolves
 *   provider      — "clerk" | "local_static" | "none"
 *   authMode      — "clerk" | "local_static" | "none"
 *   principalType — "human" | "service" | "user_pat" (ACT-502/AC-1; defaults to
 *                   "human" whenever identity carries no recognized principal_type)
 *
 * AC-5c: identity.roles is always [] (never undefined/null) when identity is present.
 * AC-5a: in auth_mode=none, identity is always null — no role/workspace affordances.
 */
export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}
