/**
 * App providers — QueryClientProvider + RouterProvider.
 *
 * Simplified from IntentTree: no tweaks store, no active-context sync.
 * The router is created in App.tsx and passed in here.
 */
import type { ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider, type RouterProviderProps } from "react-router-dom";
import { queryClient } from "@/api/queryClient";

export interface ProvidersProps {
  router: RouterProviderProps["router"];
  children?: ReactNode;
}

export function Providers({ router, children }: ProvidersProps) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}

export default Providers;
