/**
 * AppShell — minimal layout for the RF Runs Viewer.
 *
 * Thin wrapper: header bar + main content area. All IntentTree-specific
 * features (sidebar, tweaks panel, agent toast, right panel) are stripped.
 * P3/P4 will expand this with run-specific chrome.
 */
import { Outlet } from "react-router-dom";
import { useNavigate } from "react-router-dom";

export function AppShell() {
  const navigate = useNavigate();

  return (
    <div className="rv-shell">
      <header className="rv-header">
        <button
          className="it-btn ghost sm"
          onClick={() => navigate("/runs")}
          aria-label="RF Runs Viewer home"
        >
          <span className="rv-header-title">RF Runs Viewer</span>
        </button>
      </header>
      <main className="rv-content">
        <Outlet />
      </main>
    </div>
  );
}

export default AppShell;
