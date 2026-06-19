import { Outlet } from "react-router-dom";
import { useLocation, useNavigate } from "react-router-dom";

const NAV_ITEMS = [
  { label: "Portfolio", short: "PF", target: "/runs" },
  { label: "Runs", short: "RN", target: "/runs" },
  { label: "Library", short: "LB", target: "/runs" },
  { label: "Swarm", short: "SW", target: "/runs" },
  { label: "Policies", short: "PL", target: "/runs" },
  { label: "Reports", short: "RP", target: "/runs" },
  { label: "Ledger", short: "LG", target: "/runs" },
  { label: "Alerts", short: "AL", target: "/runs" },
  { label: "Settings", short: "ST", target: "/runs" },
] as const;

export function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const activeArea = location.pathname === "/runs" ? "Portfolio" : location.pathname.startsWith("/runs") ? "Runs" : "Portfolio";

  return (
    <div className="rv-shell">
      <aside className="rv-shell-rail" aria-label="Research Foundry navigation">
        <button
          type="button"
          className="rv-shell-brand"
          onClick={() => navigate("/runs")}
          aria-label="Research Foundry portfolio"
        >
          <span className="rv-shell-brand__mark" aria-hidden="true">RF</span>
          <span className="rv-shell-brand__text">Research Foundry</span>
        </button>

        <nav className="rv-shell-nav" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <button
              key={item.label}
              type="button"
              className={`rv-shell-nav__item${activeArea === item.label ? " active" : ""}`}
              onClick={() => navigate(item.target)}
              aria-current={activeArea === item.label ? "page" : undefined}
              title={item.label}
            >
              <span aria-hidden="true">{item.short}</span>
              <strong>{item.label}</strong>
            </button>
          ))}
        </nav>

        <button
          type="button"
          className="rv-shell-help"
          onClick={() => navigate("/runs")}
        >
          Help
        </button>
      </aside>
      <main className="rv-content">
        <Outlet />
      </main>
    </div>
  );
}

export default AppShell;
