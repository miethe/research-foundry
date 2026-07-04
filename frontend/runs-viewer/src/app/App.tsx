/**
 * Root application component.
 *
 * Builds the React Router instance with RF Runs Viewer routes:
 *   /           → redirect to /runs
 *   /runs       → RunList (P2 stub; real screen in P3)
 *   /runs/:runId → RunDetail (P2 stub; real screen in P3)
 *
 * The AppShell layout wraps all routes. P3 will replace stub screens.
 *
 * D6: /runs/:runId/swarm is now a redirect to /runs/:runId?view=swarm.
 * The Swarm view lives as a detail tab on RunDetailScreen.
 */
import { createBrowserRouter, Navigate, useParams } from "react-router-dom";
import { Providers } from "./providers";
import { AppShell } from "./AppShell";
import { RunListScreen } from "@/screens/RunList";
import { RunDetailScreen } from "@/screens/RunDetail";
import { SettingsScreen } from "@/screens/SettingsScreen";
import { HelpScreen } from "@/screens/HelpScreen";
import { AlertsFeed } from "@/screens/AlertsFeed";
import { PoliciesScreen } from "@/screens/PoliciesScreen";
import { CatalogScreen } from "@/screens/CatalogScreen";

/** D6: Thin redirect component — /runs/:runId/swarm → /runs/:runId?view=swarm */
function SwarmRedirect() {
  const { runId } = useParams<{ runId: string }>();
  if (!runId) return <Navigate to="/runs" replace />;
  return <Navigate to={`/runs/${encodeURIComponent(runId)}?view=swarm`} replace />;
}

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/runs" replace /> },
      { path: "runs",                    element: <RunListScreen /> },
      { path: "runs/:runId",             element: <RunDetailScreen /> },
      { path: "runs/:runId/swarm",       element: <SwarmRedirect /> },
      { path: "settings",                element: <SettingsScreen /> },
      { path: "help",                    element: <HelpScreen /> },
      { path: "alerts",                  element: <AlertsFeed /> },
      { path: "policies",                element: <PoliciesScreen /> },
      { path: "catalog",                  element: <CatalogScreen /> },
      { path: "library",                  element: <Navigate to="/catalog" replace /> },
    ],
  },
]);

export function App() {
  return <Providers router={router} />;
}

export default App;
