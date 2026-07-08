/**
 * AuthProviderStatusPanel — Admin panel: auth provider availability display.
 *
 * Fetches GET /api/admin/auth-provider-status → { provider, available, details? }.
 * Read-only — no edit actions.
 *
 * GATE-901: null/absent response or fetch failure → "Provider status unavailable".
 *
 * CSS: rv-admin-auth-provider-panel (rv-* / it-* convention).
 * WCAG 2.1 AA: status badge has role="status", descriptive aria-label on badge.
 */

import { useState, useEffect } from "react";
import { getLoopbackBase, getLoopbackAuthHeaders, ClientError } from "@/api/client";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AuthProviderStatus {
  provider: string;
  available: boolean;
  details?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function AuthProviderStatusPanel() {
  const [status, setStatus] = useState<AuthProviderStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      setFetchError(null);
      try {
        const url = `${getLoopbackBase()}/admin/auth-provider-status`;
        const res = await fetch(url, {
          method: "GET",
          headers: getLoopbackAuthHeaders(),
        });
        if (!res.ok) {
          throw new ClientError(
            res.status,
            `GET /admin/auth-provider-status failed: ${res.statusText}`,
          );
        }
        const json = (await res.json()) as AuthProviderStatus;
        if (!cancelled) setStatus(json);
      } catch (err) {
        if (!cancelled) {
          setFetchError(
            err instanceof ClientError
              ? err.message
              : "Failed to load auth provider status",
          );
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  // GATE-901: fetch failed or status null/absent → disabled panel
  if (!isLoading && (fetchError !== null || status === null)) {
    return (
      <div
        className="rv-admin-auth-provider-panel rv-admin-auth-provider-panel--disabled"
        data-testid="admin-auth-provider-panel-disabled"
      >
        <p className="rv-admin-auth-provider-panel__unavailable" role="status">
          Provider status unavailable
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        className="rv-admin-auth-provider-panel rv-admin-auth-provider-panel--loading"
        aria-busy="true"
        data-testid="admin-auth-provider-panel-loading"
      >
        <span>Loading auth provider status...</span>
      </div>
    );
  }

  const s = status!;

  return (
    <div
      className="rv-admin-auth-provider-panel"
      aria-label="Auth provider status"
      data-testid="admin-auth-provider-panel"
    >
      <dl className="rv-admin-auth-provider-panel__dl">
        <div className="rv-admin-auth-provider-panel__dl-row">
          <dt>Provider</dt>
          <dd data-testid="admin-auth-provider-name">{s.provider}</dd>
        </div>

        <div className="rv-admin-auth-provider-panel__dl-row">
          <dt>Availability</dt>
          <dd>
            <span
              role="status"
              className={`rv-admin-auth-provider-panel__badge ${
                s.available
                  ? "rv-admin-auth-provider-panel__badge--available"
                  : "rv-admin-auth-provider-panel__badge--unavailable"
              }`}
              aria-label={`Auth provider ${s.provider} is ${
                s.available ? "available" : "unavailable"
              }`}
              data-testid="admin-auth-provider-status-badge"
            >
              {s.available ? "Available" : "Unavailable"}
            </span>
          </dd>
        </div>

        {s.details !== undefined && s.details !== null && s.details !== "" && (
          <div className="rv-admin-auth-provider-panel__dl-row">
            <dt>Details</dt>
            <dd data-testid="admin-auth-provider-details">{s.details}</dd>
          </div>
        )}
      </dl>
    </div>
  );
}

export default AuthProviderStatusPanel;
