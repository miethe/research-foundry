/**
 * useClerkAuth — minimal Clerk identity resolution hook (CLK-4.5).
 *
 * GUARD: @clerk/clerk-react is an opt-in devDependency — this module must only
 * be imported when auth.provider=clerk is configured in foundry.yaml. In
 * auth_mode=none / local_static deployments this import is never evaluated and
 * @clerk/clerk-react is never bundled. Install via:
 *   pnpm add -D @clerk/clerk-react
 *
 * Public surface: useClerkAuth() → { identity, loading, error }
 *
 * Phase 8 (P5.8) wraps this hook inside AuthContext.tsx. This file does NOT
 * build AuthContext, ClerkProvider app-shell, SignIn/UserButton, or role-gated
 * logic — those are P5.8 scope. This hook is the contract seam P5.8 imports.
 */

// opt-in devDependency: loaded only when auth.provider=clerk is active
import { useAuth } from "@clerk/clerk-react";
import { useEffect, useState } from "react";
import { ClientError, getLoopbackBase } from "@/api/client";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * AuthIdentity: mirrors the backend AuthIdentity dataclass.
 *
 * Source: src/research_foundry/api/auth/provider.py::AuthIdentity
 *
 * JSON serialization note: backend stores roles as tuple[str, ...]; the HTTP
 * response serializes it as a string array (roles: string[]). An identity with
 * no roles assigned has roles: [] (never null).
 */
export interface AuthIdentity {
  user_id: string;
  workspace_id: string;
  roles: string[];
}

export interface UseClerkAuthResult {
  identity: AuthIdentity | null;
  loading: boolean;
  error: ClientError | null;
  /**
   * The last successfully resolved Clerk session JWT.
   * Non-null when identity is set; null before resolution or on error.
   *
   * P5.8 FEAUTH-003: ClerkShell reads this to install the auth-token resolver
   * via setAuthTokenResolver(() => token ?? null). Without this field, the
   * resolver always returns null and Authorization headers are never sent.
   *
   * TO BE REPLACED: P5.4 completion gate — replaced by real Clerk getToken()
   * once ClerkShell is validated against a live Clerk deployment.
   */
  token: string | null;
}

// ---------------------------------------------------------------------------
// Backend identity fetch helper — exported for independent testing
// ---------------------------------------------------------------------------

/**
 * Fetch the current user's AuthIdentity from the backend identity endpoint.
 *
 * Extends the existing p5-auth-header.test.ts header contract per-provider:
 * sends the Clerk session JWT as `Authorization: Bearer <token>`. The backend
 * auth middleware (ClerkAuthProvider.authenticate()) verifies the JWT against
 * the cached JWKS and sets request.state.identity; GET /api/auth/identity
 * returns that resolved identity.
 *
 * Error invariants:
 *   401 → token rejected, session expired, or not yet valid
 *   403 → authorization failed (insufficient role permissions)
 *   502 → response received but body is malformed (missing required fields)
 *   0   → network failure before a response was received
 *
 * Security: error messages describe failure classes only — never echo the
 * token, JWKS material, or any credential value (mirrors the no-log-the-value
 * discipline in the backend adapter).
 *
 * @throws {ClientError} on any non-2xx response or malformed response body
 */
export async function fetchIdentityWithToken(token: string): Promise<AuthIdentity> {
  const url = `${getLoopbackBase()}/auth/identity`;
  const res = await fetch(url, {
    method: "GET",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    const message =
      res.status === 401
        ? "Authentication failed: Clerk token rejected or session expired"
        : res.status === 403
          ? "Authorization failed: insufficient role permissions"
          : `Identity resolution failed (HTTP ${res.status})`;
    throw new ClientError(res.status, message);
  }

  const data: unknown = await res.json();

  // Validate shape — AC P5.4-B: never silently accept a missing/malformed identity.
  // A malformed response must surface as an explicit error, never as a silent
  // empty identity that could be mistaken for auth_mode=none.
  const d = data as Record<string, unknown> | null | undefined;
  if (
    !d ||
    typeof d.user_id !== "string" ||
    typeof d.workspace_id !== "string" ||
    !Array.isArray(d.roles)
  ) {
    throw new ClientError(
      502,
      "Identity response is malformed: missing required fields (user_id, workspace_id, roles)",
    );
  }

  return data as AuthIdentity;
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * useClerkAuth — obtain the Clerk session JWT and resolve it to an AuthIdentity
 * via the backend's identity-resolution endpoint.
 *
 * State lifecycle:
 *   Mount             → loading: true,  identity: null, error: null
 *   Unauthenticated   → loading: false, identity: null, error: 401 ClientError
 *   Token rejected    → loading: false, identity: null, error: 4xx ClientError
 *   Malformed body    → loading: false, identity: null, error: 502 ClientError
 *   Resolved          → loading: false, identity: AuthIdentity, error: null
 *
 * AC P5.4-B invariant: once loading transitions to false, identity === null is
 * ALWAYS accompanied by a non-null error — the hook never returns
 * { identity: null, error: null, loading: false } after settlement.
 *
 * Re-auth on session change is P5.8 (AuthContext.tsx) responsibility; this
 * hook runs once on mount and returns the current session state.
 */
export function useClerkAuth(): UseClerkAuthResult {
  const { getToken } = useAuth();
  const [identity, setIdentity] = useState<AuthIdentity | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<ClientError | null>(null);
  // P5.8 FEAUTH-003: capture the resolved JWT so ClerkShell can forward it to
  // setAuthTokenResolver. Without this, the resolver returns null and all
  // loopback/admin fetches in Clerk mode omit the Authorization header.
  const [clerkToken, setClerkToken] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function resolve(): Promise<void> {
      setLoading(true);
      setError(null);
      setIdentity(null);
      setClerkToken(null);

      try {
        const token = await getToken();

        if (token === null) {
          // Clerk session not present — explicit 401, never a silent empty identity.
          if (!cancelled) {
            setError(
              new ClientError(401, "Unauthenticated: no active Clerk session found"),
            );
            setLoading(false);
          }
          return;
        }

        const resolved = await fetchIdentityWithToken(token);

        if (!cancelled) {
          // React 18 automatic batching: setClerkToken + setIdentity are batched
          // into a single render, so ClerkShell sees both updated simultaneously.
          setClerkToken(token);
          setIdentity(resolved);
          setError(null);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setClerkToken(null);
          setError(
            err instanceof ClientError
              ? err
              : new ClientError(0, "Unexpected error during identity resolution"),
          );
          setIdentity(null);
          setLoading(false);
        }
      }
    }

    void resolve();

    return () => {
      cancelled = true;
    };
    // getToken is stable within a Clerk session (Clerk memoizes the reference).
    // Including it here satisfies react-hooks/exhaustive-deps while still
    // running the effect once on mount in normal operation.
  }, [getToken]); // eslint-disable-line react-hooks/exhaustive-deps

  return { identity, loading, error, token: clerkToken };
}
