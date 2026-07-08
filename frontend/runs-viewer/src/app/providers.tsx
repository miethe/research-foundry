/**
 * App providers — QueryClientProvider + AuthProvider + RouterProvider.
 *
 * Simplified from IntentTree: no tweaks store, no active-context sync.
 * The router is created in App.tsx and passed in here.
 *
 * AuthProvider is mounted here (P5.8 FEAUTH-001) so that useAuth() resolves
 * the configured auth mode everywhere in the app, including AppShell.
 * Without this, useAuth() reads the default context (authMode="none") even
 * when VITE_AUTH_PROVIDER is set to "clerk" or "local_static".
 */
import type { ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, type RouterProviderProps } from "react-router-dom";
import { queryClient } from "@/api/queryClient";
import { AuthProvider } from "@/auth/AuthContext";

export interface ProvidersProps {
  router: RouterProviderProps["router"];
  children?: ReactNode;
}

export function Providers({ router, children }: ProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        {children}
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default Providers;
