/**
 * ClerkShell.tsx — Clerk provider + identity resolution wrapper.
 *
 * BUNDLE-SIZE GUARD: This is the ONLY file that imports @clerk/clerk-react.
 * It is loaded exclusively via React.lazy() in AuthContext.tsx, ensuring
 * the Clerk SDK is never bundled for auth_mode=none or local_static builds,
 * nor for static-export builds (where IS_STATIC_EXPORT forces auth_mode=none).
 *
 * P5.4 hook usage: The useClerkAuth hook (src/auth/useClerkAuth.ts) resolves
 * the Clerk session JWT and fetches AuthIdentity from the backend identity
 * endpoint. ClerkShell wraps children in ClerkProvider so the hook can call
 * useAuth() from @clerk/clerk-react.
 *
 * Default export required for React.lazy() — do not rename.
 */

import React, { useEffect } from "react";
import { ClerkProvider, SignIn } from "@clerk/clerk-react";
import type { AuthIdentity } from "./AuthContext";

// Real P5.4 Clerk hook — imported here (inside lazy-loaded boundary).
// This import is only evaluated when provider=clerk; never bundled otherwise.
import { useClerkAuth } from "./useClerkAuth";

// ── Props ─────────────────────────────────────────────────────────────────────

export interface ClerkShellProps {
  publishableKey: string;
  onIdentityResolved: (identity: AuthIdentity) => void;
  onLoadingChange: (loading: boolean) => void;
  children: React.ReactNode;
}

// ── ClerkAuthInner ────────────────────────────────────────────────────────────

/**
 * ClerkAuthInner — sits inside ClerkProvider so useClerkAuth() is valid.
 * Fires onIdentityResolved when identity resolves; onLoadingChange tracks state.
 */
function ClerkAuthInner({
  onIdentityResolved,
  onLoadingChange,
  children,
}: {
  onIdentityResolved: (identity: AuthIdentity) => void;
  onLoadingChange: (loading: boolean) => void;
  children: React.ReactNode;
}): React.JSX.Element {
  // P5.8 FEAUTH-003: destructure token so we can forward it to the resolver.
  // React 18 automatic batching ensures identity and token are set in the same
  // render, so when this effect fires identity and token are both populated.
  const { identity, loading, token } = useClerkAuth();

  // Notify parent of loading state changes so AuthContextValue stays current
  useEffect(() => {
    onLoadingChange(loading);
  }, [loading, onLoadingChange]);

  // Propagate resolved identity (and session token) to AuthProvider state.
  // token is included so AuthProvider can install it as the auth-token resolver
  // via setAuthTokenResolver(() => resolved.token ?? null) — without it, the
  // resolver always returns null and Authorization headers are never sent.
  useEffect(() => {
    if (identity) {
      // AC-5c: normalize roles to [] if absent — never elevated privilege
      onIdentityResolved({
        user_id: identity.user_id,
        workspace_id: identity.workspace_id,
        roles: Array.isArray(identity.roles) ? identity.roles : [],
        // P5.8 FEAUTH-003: forward Clerk JWT as token so the resolver works.
        // The token was fetched during identity resolution in useClerkAuth.
        token: token ?? undefined,
      });
    }
  }, [identity, token, onIdentityResolved]);

  if (loading) {
    // Clerk session still resolving — render nothing to avoid login flash
    return <></>;
  }

  if (!identity) {
    // Unauthenticated — render Clerk's built-in SignIn component
    return (
      <div className="rv-auth-overlay">
        <SignIn />
      </div>
    );
  }

  return <>{children}</>;
}

// ── ClerkShell (default export) ───────────────────────────────────────────────

/**
 * Wraps the app in ClerkProvider and drives identity resolution.
 * Default export required for React.lazy().
 */
export default function ClerkShell({
  publishableKey,
  onIdentityResolved,
  onLoadingChange,
  children,
}: ClerkShellProps): React.JSX.Element {
  if (!publishableKey) {
    // Warn loudly — provider=clerk is active but the publishable key is missing.
    // ClerkProvider will throw; surface the warning early.
    console.warn(
      "[AuthContext] provider=clerk is configured but VITE_CLERK_PUBLISHABLE_KEY is not set.",
    );
  }

  return (
    <ClerkProvider publishableKey={publishableKey}>
      <ClerkAuthInner
        onIdentityResolved={onIdentityResolved}
        onLoadingChange={onLoadingChange}
      >
        {children}
      </ClerkAuthInner>
    </ClerkProvider>
  );
}
