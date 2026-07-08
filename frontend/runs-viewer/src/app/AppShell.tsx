import { useEffect, useMemo, useState } from "react";
import { Outlet } from "react-router-dom";
import { useLocation, useNavigate } from "react-router-dom";
import { applyTheme, getViewerSettings } from "@/lib/viewerSettings";
import { isAgentsLoopbackEnabled } from "@/hooks";
import type { ShellSelectionContext } from "./shellContext";
import { useAuth } from "../auth/AuthContext";
import { getRateLimitState, subscribeRateLimitState } from "@/api/client";
import type { RateLimitState } from "@/api/client";

type NavState = "enabled" | "contextual" | "disabled";

interface ShellNavContext {
  pathname: string;
  routeRunId: string | null;
}

interface NavCapability {
  label: string;
  short: string;
  state: NavState;
  resolveTarget?: (ctx: ShellNavContext) => string | null;
  disabledReason?: string;
  /**
   * Role allowlist for this nav item. When set, only identities whose roles
   * array intersects this list may access the item. Absent = accessible to all.
   * AC-5c: missing identity.roles → treated as [] → all role-gated items disabled.
   */
  allowedRoles?: string[];
}

// D2: Run-scoped items (Runs, Reports, Ledger, Swarm) removed from top-level nav.
// Runs are accessed only via Portfolio (/runs page → run list → run detail).
// Run-scoped detail tabs (Ledger, Report, Swarm) live on the run detail surface.
const NAV_ITEMS: NavCapability[] = [
  { label: "Portfolio", short: "PF", state: "enabled", resolveTarget: () => "/runs" },
  { label: "Catalog", short: "CT", state: "enabled", resolveTarget: () => "/catalog" },
  { label: "Builder", short: "BD", state: "enabled", resolveTarget: () => "/builder" },
  {
    label: "Agents",
    short: "AG",
    state: "contextual",
    // HARD RELEASE CONSTRAINT (P4.5): /agents is loopback/single-operator only.
    // resolveTarget returns null in static export mode → nav item renders disabled.
    resolveTarget: () => (isAgentsLoopbackEnabled() ? "/agents" : null),
    disabledReason:
      "Requires RF API server — start rf serve and set VITE_RUNS_FRONTEND_LOOPBACK_API=true",
  },
  { label: "Policies", short: "PL", state: "enabled", resolveTarget: () => "/policies" },
  { label: "Alerts", short: "AL", state: "enabled", resolveTarget: () => "/alerts" },
  {
    label: "Settings",
    short: "ST",
    state: "enabled",
    resolveTarget: () => "/settings",
    // Settings is an admin-only section — restricted to admin/owner roles.
    // Defense-in-depth: server-side require_role() (P5.2) is the actual gate (FR-6).
    allowedRoles: ["admin", "owner"],
  },
  { label: "Help", short: "HP", state: "enabled", resolveTarget: () => "/help" },
];

export function AppShell() {
  const navigate = useNavigate();
  const location = useLocation();
  const [, setSelectedRunId] = useState<string | null>(null);
  const { identity, authMode } = useAuth();

  // GATE-900: reactive rate-limit state.
  // Initialised from module-level getRateLimitState() so any state set before
  // first render is not lost. subscribeRateLimitState() wires updates from
  // loopbackGet() whenever rate-limit headers are parsed or a 429 fires.
  const [rlState, setRlState] = useState<RateLimitState | null>(getRateLimitState);
  useEffect(() => subscribeRateLimitState(setRlState), []);

  // Apply persisted theme on mount so the stored theme takes effect on app boot
  useEffect(() => {
    applyTheme(getViewerSettings().theme);
  }, []);
  const routeRunId = extractRunId(location.pathname);
  const ctx: ShellNavContext = { pathname: location.pathname, routeRunId };
  const outletContext = useMemo<ShellSelectionContext>(
    () => ({ setSelectedRunId }),
    [],
  );

  // DEFENSE-IN-DEPTH ONLY: Role-gating nav items here prevents UI confusion but is NOT
  // the authorization boundary. Server-side require_role() enforcement (P5.2) and
  // workspace-scoped repository queries (P5.3) are the actual gates.
  // Hiding a nav item here must NEVER be treated as sufficient on its own — PRD FR-6.
  const isRoleGated = (item: NavCapability): boolean => {
    if (!item.allowedRoles || item.allowedRoles.length === 0) return false;
    // AC-5c: missing roles array on identity → treat as [] → least-privilege viewer
    const userRoles: string[] = identity?.roles ?? [];
    return !item.allowedRoles.some((role) => userRoles.includes(role));
  };

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
            // auth_mode=none: no role-based gating applied (AC-5a regression guard).
            // In all other modes, isRoleGated checks identity.roles (AC-5c: defaults to []).
            const roleGated = authMode !== "none" && isRoleGated(item);
            const disabled = item.state === "disabled" || !target || roleGated;
            const active = isActiveNav(item.label, ctx);
            // Role-gated items surface a descriptive reason; fall back to item's own reason.
            // Reuses the existing title/aria-label disabled rendering path — no new renderer.
            const effectiveDisabledReason = roleGated
              ? `Requires ${(item.allowedRoles ?? []).join(" or ")} role`
              : item.disabledReason;
            const title = disabled ? effectiveDisabledReason ?? "Not available." : item.label;
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

        {/* GATE-900: rate-limit badge only rendered when a 429 has fired and
            Retry-After is present (retryAfter !== undefined). Under-budget
            responses update rlState but leave retryAfter undefined → no badge.
            Absent headers → rlState null → no badge. */}
        {rlState?.retryAfter !== undefined && (
          <div
            className="rv-rate-limit-badge"
            role="status"
            aria-label={`Rate limited. Retry after ${rlState.retryAfter} seconds.`}
            data-testid="rv-rate-limit-badge"
          >
            <span aria-hidden="true">RL</span>
            <span data-testid="rv-rate-limit-retry-after">{rlState.retryAfter}s</span>
          </div>
        )}
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

// D2: isActiveNav simplified — only global nav items remain.
function isActiveNav(label: string, ctx: ShellNavContext): boolean {
  if (label === "Portfolio") return ctx.pathname === "/runs" || Boolean(ctx.routeRunId);
  if (label === "Catalog") return ctx.pathname === "/catalog" || ctx.pathname === "/library";
  if (label === "Builder") return ctx.pathname === "/builder";
  if (label === "Agents") return ctx.pathname.startsWith("/agents");
  if (label === "Policies") return ctx.pathname === "/policies";
  if (label === "Alerts") return ctx.pathname === "/alerts";
  if (label === "Settings") return ctx.pathname === "/settings";
  if (label === "Help") return ctx.pathname === "/help";
  return false;
}
