import { useEffect, useMemo, useState } from "react";
import { Outlet } from "react-router-dom";
import { useLocation, useNavigate } from "react-router-dom";
import { applyTheme, getViewerSettings } from "@/lib/viewerSettings";
import type { ShellSelectionContext } from "./shellContext";

type NavState = "enabled" | "contextual" | "disabled";

interface ShellNavContext {
  pathname: string;
  search: string;
  runId: string | null;
  routeRunId: string | null;
  view: string | null;
}

interface NavCapability {
  label: string;
  short: string;
  state: NavState;
  resolveTarget?: (ctx: ShellNavContext) => string | null;
  disabledReason?: string;
}

const NAV_ITEMS: NavCapability[] = [
  { label: "Portfolio", short: "PF", state: "enabled", resolveTarget: () => "/runs" },
  { label: "Runs", short: "RN", state: "enabled", resolveTarget: (ctx) => ctx.runId ? `/runs/${encodeURIComponent(ctx.runId)}` : "/runs" },
  { label: "Reports", short: "RP", state: "contextual", resolveTarget: (ctx) => ctx.runId ? `/runs/${encodeURIComponent(ctx.runId)}?view=report` : null, disabledReason: "Select a run first." },
  { label: "Ledger", short: "LG", state: "contextual", resolveTarget: (ctx) => ctx.runId ? `/runs/${encodeURIComponent(ctx.runId)}?view=audit` : null, disabledReason: "Select a run first." },
  { label: "Library", short: "LB", state: "disabled", disabledReason: "Library route is not implemented." },
  { label: "Swarm", short: "SW", state: "disabled", disabledReason: "Swarm route is not implemented." },
  { label: "Policies", short: "PL", state: "disabled", disabledReason: "Policies route is not implemented." },
  { label: "Alerts", short: "AL", state: "disabled", disabledReason: "Alerts route is not implemented." },
  { label: "Settings", short: "ST", state: "enabled", resolveTarget: () => "/settings" },
  { label: "Help", short: "HP", state: "disabled", disabledReason: "Help route is not implemented." },
];

export function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  // Apply persisted theme on mount so the stored theme takes effect on app boot
  useEffect(() => {
    applyTheme(getViewerSettings().theme);
  }, []);
  const routeRunId = extractRunId(location.pathname);
  const runId = routeRunId ?? selectedRunId;
  const view = new URLSearchParams(location.search).get("view");
  const ctx: ShellNavContext = { pathname: location.pathname, search: location.search, runId, routeRunId, view };
  const outletContext = useMemo<ShellSelectionContext>(
    () => ({ setSelectedRunId }),
    [],
  );

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
          {NAV_ITEMS.map((item) => {
            const target = item.resolveTarget?.(ctx) ?? null;
            const disabled = item.state === "disabled" || !target;
            const active = isActiveNav(item.label, ctx);
            const title = disabled ? item.disabledReason ?? "Not available." : item.label;
            return (
              <button
                key={item.label}
                type="button"
                className={`rv-shell-nav__item${active ? " active" : ""}${disabled ? " disabled" : ""}`}
                onClick={() => {
                  if (target) navigate(target);
                }}
                aria-current={active ? "page" : undefined}
                aria-disabled={disabled ? "true" : undefined}
                disabled={disabled}
                title={title}
                aria-label={disabled ? `${item.label}: ${title}` : item.label}
                data-state={item.state}
              >
                <span aria-hidden="true">{item.short}</span>
                <strong>{item.label}</strong>
              </button>
            );
          })}
        </nav>
      </aside>
      <main className="rv-content">
        <Outlet context={outletContext} />
      </main>
    </div>
  );
}

export default AppShell;

function extractRunId(pathname: string): string | null {
  const match = /^\/runs\/([^/?#]+)/.exec(pathname);
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

function isActiveNav(label: string, ctx: ShellNavContext): boolean {
  if (label === "Portfolio") return ctx.pathname === "/runs";
  if (label === "Runs") return Boolean(ctx.routeRunId) && (ctx.view == null || ctx.view === "overview" || ctx.view === "trust" || ctx.view === "lineage" || ctx.view === "writeback");
  if (label === "Reports") return Boolean(ctx.routeRunId) && ctx.view === "report";
  if (label === "Ledger") return Boolean(ctx.routeRunId) && (ctx.view === "audit" || ctx.view === "ledger");
  if (label === "Settings") return ctx.pathname === "/settings";
  return false;
}
