/**
 * RateLimitConfigPanel — Admin panel: rate limit configuration display + edit.
 *
 * Fetches GET /api/admin/rate-limit-config → RateLimitConfig.
 * Edit form for admin/owner roles; read-only for researcher/reviewer/viewer.
 * Saves via PATCH /api/admin/rate-limit-config → 204 or { error: string }.
 *
 * GATE-900/GATE-901: if fetch fails or config is null → disabled panel with
 * "Rate limit config unavailable" message.
 *
 * CSS: rv-admin-rate-limit-panel (rv-* / it-* convention).
 * WCAG 2.1 AA: form labels, fieldset/legend, keyboard nav on all controls.
 */

import { useState, useEffect } from "react";
import { getLoopbackBase, getLoopbackAuthHeaders, ClientError } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";

// ── Types ─────────────────────────────────────────────────────────────────────

interface RateLimitConfig {
  enabled: boolean;
  window_seconds: number;
  max_requests: number;
  per_identity: boolean;
  per_route: boolean;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function RateLimitConfigPanel() {
  const { identity } = useAuth();
  // AC-5c: identity.roles normalised to [] when absent.
  const userRoles: string[] = identity?.roles ?? [];
  const canEdit = userRoles.some((r) => ["owner", "admin"].includes(r));

  const [config, setConfig] = useState<RateLimitConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Edit draft state
  const [isEditing, setIsEditing] = useState(false);
  const [editEnabled, setEditEnabled] = useState(false);
  const [editMaxRequests, setEditMaxRequests] = useState(0);
  const [editWindowSeconds, setEditWindowSeconds] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      setFetchError(null);
      try {
        const url = `${getLoopbackBase()}/admin/rate-limit-config`;
        const res = await fetch(url, {
          method: "GET",
          headers: getLoopbackAuthHeaders(),
        });
        if (!res.ok) {
          throw new ClientError(
            res.status,
            `GET /admin/rate-limit-config failed: ${res.statusText}`,
          );
        }
        const json = (await res.json()) as RateLimitConfig;
        if (!cancelled) {
          setConfig(json);
          setEditEnabled(json.enabled ?? false);
          setEditMaxRequests(json.max_requests ?? 0);
          setEditWindowSeconds(json.window_seconds ?? 0);
        }
      } catch (err) {
        if (!cancelled) {
          setFetchError(
            err instanceof ClientError
              ? err.message
              : "Failed to load rate limit config",
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

  async function handleSave(): Promise<void> {
    setIsSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      const url = `${getLoopbackBase()}/admin/rate-limit-config`;
      const res = await fetch(url, {
        method: "PATCH",
        headers: {
          ...getLoopbackAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          enabled: editEnabled,
          max_requests: editMaxRequests,
          window_seconds: editWindowSeconds,
        }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { error?: string };
        throw new ClientError(
          res.status,
          body.error ?? `Save failed (HTTP ${res.status})`,
        );
      }
      setConfig((prev) =>
        prev
          ? {
              ...prev,
              enabled: editEnabled,
              max_requests: editMaxRequests,
              window_seconds: editWindowSeconds,
            }
          : prev,
      );
      setIsEditing(false);
      setSaveSuccess(true);
    } catch (err) {
      setSaveError(
        err instanceof ClientError
          ? err.message
          : "Failed to save rate limit config",
      );
    } finally {
      setIsSaving(false);
    }
  }

  function handleCancel(): void {
    if (config) {
      setEditEnabled(config.enabled);
      setEditMaxRequests(config.max_requests);
      setEditWindowSeconds(config.window_seconds);
    }
    setIsEditing(false);
    setSaveError(null);
  }

  // GATE-900/GATE-901: fetch failed or config null → disabled panel
  if (!isLoading && (fetchError !== null || config === null)) {
    return (
      <div
        className="rv-admin-rate-limit-panel rv-admin-rate-limit-panel--disabled"
        data-testid="admin-rate-limit-panel-disabled"
      >
        <p className="rv-admin-rate-limit-panel__unavailable" role="status">
          Rate limit config unavailable
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        className="rv-admin-rate-limit-panel rv-admin-rate-limit-panel--loading"
        aria-busy="true"
        data-testid="admin-rate-limit-panel-loading"
      >
        <span>Loading rate limit config...</span>
      </div>
    );
  }

  const cfg = config!;

  return (
    <div
      className="rv-admin-rate-limit-panel"
      aria-label="Rate limit configuration"
      data-testid="admin-rate-limit-panel"
    >
      {saveError !== null && (
        <div
          className="rv-admin-rate-limit-panel__error"
          role="alert"
          aria-live="assertive"
          data-testid="admin-rate-limit-save-error"
        >
          {saveError}
        </div>
      )}
      {saveSuccess && !isEditing && (
        <div
          className="rv-admin-rate-limit-panel__success"
          role="status"
          aria-live="polite"
          data-testid="admin-rate-limit-save-success"
        >
          Rate limit configuration saved.
        </div>
      )}

      {!isEditing ? (
        // ── Read-only display ─────────────────────────────────────────────────
        <div
          className="rv-admin-rate-limit-panel__display"
          data-testid="admin-rate-limit-display"
        >
          <dl className="rv-admin-rate-limit-panel__dl">
            <div className="rv-admin-rate-limit-panel__dl-row">
              <dt>Status</dt>
              <dd>
                <span
                  className={`rv-admin-rate-limit-panel__badge ${
                    cfg.enabled
                      ? "rv-admin-rate-limit-panel__badge--enabled"
                      : "rv-admin-rate-limit-panel__badge--disabled"
                  }`}
                  data-testid="admin-rate-limit-status"
                >
                  {cfg.enabled ? "Enabled" : "Disabled"}
                </span>
              </dd>
            </div>
            <div className="rv-admin-rate-limit-panel__dl-row">
              <dt>Max requests</dt>
              <dd data-testid="admin-rate-limit-max-requests">{cfg.max_requests}</dd>
            </div>
            <div className="rv-admin-rate-limit-panel__dl-row">
              <dt>Window</dt>
              <dd data-testid="admin-rate-limit-window">{cfg.window_seconds}s</dd>
            </div>
            <div className="rv-admin-rate-limit-panel__dl-row">
              <dt>Per identity</dt>
              <dd>{cfg.per_identity ? "Yes" : "No"}</dd>
            </div>
            <div className="rv-admin-rate-limit-panel__dl-row">
              <dt>Per route</dt>
              <dd>{cfg.per_route ? "Yes" : "No"}</dd>
            </div>
          </dl>

          {canEdit && (
            <button
              type="button"
              className="it-btn sm"
              onClick={() => {
                setIsEditing(true);
                setSaveSuccess(false);
              }}
              data-testid="admin-rate-limit-edit-btn"
            >
              Edit
            </button>
          )}
        </div>
      ) : (
        // ── Edit form ─────────────────────────────────────────────────────────
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void handleSave();
          }}
          aria-label="Rate limit configuration form"
          data-testid="admin-rate-limit-form"
        >
          <fieldset className="rv-admin-rate-limit-panel__fieldset">
            <legend className="rv-admin-rate-limit-panel__legend">
              Edit rate limit settings
            </legend>

            <div className="rv-admin-rate-limit-panel__field">
              <label htmlFor="rl-enabled" className="rv-settings__label">
                Rate limiting enabled
              </label>
              <label className="rv-settings__toggle">
                <input
                  id="rl-enabled"
                  type="checkbox"
                  className="rv-settings__checkbox"
                  checked={editEnabled}
                  onChange={(e) => setEditEnabled(e.target.checked)}
                  data-testid="admin-rate-limit-enabled-toggle"
                />
                <span>{editEnabled ? "Enabled" : "Disabled"}</span>
              </label>
            </div>

            <div className="rv-admin-rate-limit-panel__field">
              <label htmlFor="rl-max-requests" className="rv-settings__label">
                Max requests
              </label>
              <input
                id="rl-max-requests"
                type="number"
                min={1}
                className="rv-settings__input"
                value={editMaxRequests}
                onChange={(e) => setEditMaxRequests(Number(e.target.value))}
                data-testid="admin-rate-limit-max-requests-input"
                aria-label="Maximum requests per window"
              />
            </div>

            <div className="rv-admin-rate-limit-panel__field">
              <label htmlFor="rl-window-seconds" className="rv-settings__label">
                Window (seconds)
              </label>
              <input
                id="rl-window-seconds"
                type="number"
                min={1}
                className="rv-settings__input"
                value={editWindowSeconds}
                onChange={(e) => setEditWindowSeconds(Number(e.target.value))}
                data-testid="admin-rate-limit-window-input"
                aria-label="Rate limit window in seconds"
              />
            </div>
          </fieldset>

          <div className="rv-admin-rate-limit-panel__actions">
            <button
              type="submit"
              className="it-btn sm"
              disabled={isSaving}
              data-testid="admin-rate-limit-save-btn"
            >
              {isSaving ? "Saving..." : "Save"}
            </button>
            <button
              type="button"
              className="it-btn sm it-btn--ghost"
              onClick={handleCancel}
              disabled={isSaving}
              data-testid="admin-rate-limit-cancel-btn"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

export default RateLimitConfigPanel;
