/**
 * Route table for the RF Runs Viewer.
 *
 * Two primary routes:
 *   /runs           → run list (all discovered runs, with status_derived)
 *   /runs/:runId    → run detail (full denormalized claim graph)
 */
import type { ReactElement } from "react";

export type RouteName = "runList" | "runDetail" | "settings" | "help" | "alerts" | "swarm" | "policies" | "catalog";

export interface RouteMeta {
  path: string;
  label: string;
}

// eslint-disable-next-line react-refresh/only-export-components
export const ROUTES: Record<RouteName, RouteMeta> = {
  runList:   { path: "/runs",                label: "Runs"       },
  runDetail: { path: "/runs/:runId",         label: "Run Detail" },
  settings:  { path: "/settings",            label: "Settings"   },
  help:      { path: "/help",                label: "Help"       },
  alerts:    { path: "/alerts",              label: "Alerts"     },
  // Redirect alias: App.tsx redirects /runs/:runId/swarm → /runs/:runId?view=swarm. Not a standalone screen.
  swarm:     { path: "/runs/:runId/swarm",   label: "Swarm (→ ?view=swarm)" },
  policies:  { path: "/policies",            label: "Policies"   },
  catalog:   { path: "/catalog",             label: "Catalog"    },
};

export interface ScreenRoute {
  name: RouteName;
  path: string;
  element: ReactElement;
}
