/**
 * useClerkAuth shim — safe stub for non-Clerk deployments.
 *
 * P5.4 WIRING NOTE: This stub is a placeholder that returns a null identity
 * without importing @clerk/clerk-react. When provider=clerk is active, the
 * real hook at src/auth/useClerkAuth.ts is used inside ClerkShell.tsx, which
 * is lazy-loaded via React.lazy() to prevent unconditional bundling.
 *
 * This file exists to:
 *   1. Document the P5.4 seam contract
 *   2. Prevent any accidental import of @clerk/clerk-react outside ClerkShell.tsx
 *   3. Serve as the fallback when the Clerk adapter is not active
 *
 * TO BE REPLACED: Replace the stub body here once ClerkShell.tsx is fully
 * validated against a live Clerk deployment (P5.4 completion gate).
 *
 * DO NOT import @clerk/clerk-react in this file.
 */

import type { AuthIdentity } from "../AuthContext";

export interface UseClerkAuthShimResult {
  identity: AuthIdentity | null;
  loading: boolean;
  error: Error | null;
  /**
   * Stub token field — mirrors the `token` field added to UseClerkAuthResult
   * in the real hook (P5.8 FEAUTH-003).
   *
   * In tests: set VITE_CLERK_TEST_TOKEN env var to simulate a resolved Clerk
   * session without a live Clerk deployment. This stub-only env var is NEVER
   * read in the real useClerkAuth hook or any production code path.
   *
   * In production (non-Clerk builds): always null — ClerkShell (and this stub)
   * are never loaded when provider != "clerk".
   */
  token: string | null;
}

/**
 * Stub hook — always returns null identity, never loading, no error.
 * Safe to call outside a ClerkProvider context.
 */
export function useClerkAuthShim(): UseClerkAuthShimResult {
  // STUB-ONLY: read VITE_CLERK_TEST_TOKEN for test environments.
  // Never present in production; real Clerk hook uses getToken() from @clerk/clerk-react.
  const stubToken: string | null =
    typeof import.meta !== "undefined"
      ? ((import.meta.env?.VITE_CLERK_TEST_TOKEN as string | undefined) ?? null)
      : null;
  return { identity: null, loading: false, error: null, token: stubToken };
}
