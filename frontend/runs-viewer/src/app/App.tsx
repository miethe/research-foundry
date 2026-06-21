/**
 * Root application component.
 *
 * Builds the React Router instance with RF Runs Viewer routes:
 *   /           → redirect to /runs
 *   /runs       → RunList (P2 stub; real screen in P3)
 *   /runs/:runId → RunDetail (P2 stub; real screen in P3)
 *
 * The AppShell layout wraps all routes. P3 will replace stub screens.
 */
import { createBrowserRouter, Navigate } from "react-router-dom";
import { Providers } from "./providers";
import { AppShell } from "./AppShell";
import { RunListScreen } from "@/screens/RunList";
import { RunDetailScreen } from "@/screens/RunDetail";
import { SettingsScreen } from "@/screens/SettingsScreen";
import { HelpScreen } from "@/screens/HelpScreen";

const router = createBrowserRouter([
  {
    path: "/",
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/runs" replace /> },
      { path: "runs",         element: <RunListScreen /> },
      { path: "runs/:runId",  element: <RunDetailScreen /> },
      { path: "settings",     element: <SettingsScreen /> },
      { path: "help",          element: <HelpScreen /> },
    ],
  },
]);

export function App() {
  return <Providers router={router} />;
}

export default App;
