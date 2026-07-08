/**
 * RbacStatusPanel — Admin panel: RBAC enforcement status display.
 *
 * Fetches GET /api/admin/rbac-status via getRbacStatus() from client.ts.
 * Response shape: { rbac_enforcement: string, rbac_enforced: boolean, auth_provider: string }.
 * Readable by any authenticated user (T5 contract — not admin-only).
 * Read-only — no edit controls; T5 enforces server-side.
 *
 * GATE-901: null result (any error) → "RBAC status unavailable" disabled state.
 *
 * CSS: rv-admin-rbac-panel (rv-* / it-* convention).
 * WCAG 2.1 AA: status badge has role="status", descriptive aria-label.
 */

import { useState, useEffect } from "react";
import { getRbacStatus } from "@/api/client";
import type { RbacStatus } from "@/api/client";

// ── Component ─────────────────────────────────────────────────────────────────

export function RbacStatusPanel() {
  const [status, setStatus] = useState<RbacStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      // getRbacStatus() returns null on any error (GATE-901 contract).
      const result = await getRbacStatus();
      if (!cancelled) {
        setStatus(result);
        setIsLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  // GATE-901: null result (any error or absent endpoint) → disabled panel
  if (!isLoading && status === null) {
    return (
      <div
        className="rv-admin-rbac-panel rv-admin-rbac-panel--disabled"
        data-testid="admin-rbac-panel-disabled"
      >
        <p className="rv-admin-rbac-panel__unavailable" role="status">
          RBAC status unavailable
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        className="rv-admin-rbac-panel rv-admin-rbac-panel--loading"
        aria-busy="true"
        data-testid="admin-rbac-panel-loading"
      >
        <span>Loading RBAC status...</span>
      </div>
    );
  }

  const s = status!;

  return (
    <div
      className="rv-admin-rbac-panel"
      aria-label="RBAC enforcement status"
      data-testid="admin-rbac-panel"
    >
      <dl className="rv-admin-rbac-panel__dl">
        <div className="rv-admin-rbac-panel__dl-row">
          <dt>Enforcement policy</dt>
          <dd data-testid="admin-rbac-enforcement">{s.rbac_enforcement}</dd>
        </div>

        <div className="rv-admin-rbac-panel__dl-row">
          <dt>Currently enforced</dt>
          <dd>
            <span
              role="status"
              className={`rv-admin-rbac-panel__badge ${
                s.rbac_enforced
                  ? "rv-admin-rbac-panel__badge--enforced"
                  : "rv-admin-rbac-panel__badge--unenforced"
              }`}
              aria-label={`RBAC enforcement is ${s.rbac_enforced ? "active" : "inactive"}`}
              data-testid="admin-rbac-enforced-badge"
            >
              {s.rbac_enforced ? "Enforced" : "Not enforced"}
            </span>
          </dd>
        </div>

        <div className="rv-admin-rbac-panel__dl-row">
          <dt>Auth provider</dt>
          <dd data-testid="admin-rbac-auth-provider">{s.auth_provider}</dd>
        </div>
      </dl>
    </div>
  );
}

export default RbacStatusPanel;
