/**
 * SettingsScreen — viewer configuration surface (G5).
 *
 * Accessible at /settings. Renders four sections:
 *   1. Display     — sensitivity toggle (rv_show_all)
 *   2. Appearance  — theme selector (rv_theme)
 *   3. Navigation  — default detail tab (rv_default_tab)
 *   4. Data        — base data path (rv_data_path) with Save + reload notice
 *
 * All preferences persist to localStorage via useViewerSettings().
 * Theme changes apply immediately via applyTheme().
 * Data path changes require a page reload (saved with explicit Save button).
 */

import { useState } from "react";
import { useViewerSettings } from "@/lib/viewerSettings";
import { useAuth } from "@/auth/AuthContext";
import { WorkspaceMembersPanel } from "@/components/AdminSettings/WorkspaceMembersPanel";
import { RoleAssignmentPanel } from "@/components/AdminSettings/RoleAssignmentPanel";
import { RateLimitConfigPanel } from "@/components/AdminSettings/RateLimitConfigPanel";
import { AuthProviderStatusPanel } from "@/components/AdminSettings/AuthProviderStatusPanel";
import { RbacStatusPanel } from "@/components/AdminSettings/RbacStatusPanel";
import "@/styles/settings.css";

const DETAIL_TABS = [
  { value: "overview",  label: "Overview"  },
  { value: "trust",     label: "Trust"     },
  { value: "ledger",    label: "Ledger"    },
  { value: "report",    label: "Report"    },
  { value: "lineage",   label: "Lineage"   },
  { value: "writeback", label: "Writeback" },
] as const;

export function SettingsScreen() {
  const [settings, updateSetting] = useViewerSettings();
  const { identity, authMode } = useAuth();

  // Local draft for data path — persisted only on Save
  const [dataPathDraft, setDataPathDraft] = useState(settings.dataPath);
  const [reloadNotice, setReloadNotice] = useState(false);

  // DEFENSE-IN-DEPTH ONLY: admin section visibility here is a UX affordance, NOT an
  // authorization boundary. Server-side require_role() enforcement (P5.2) and
  // workspace-scoped repository queries (P5.3) are the actual gates (FR-6).
  // When authMode is 'none', isAdmin is always false (AC-5a regression guard).
  // AC-5c: identity.roles defaults to [] when absent → least-privilege viewer.
  const isAdmin =
    authMode !== "none" &&
    (identity?.roles ?? []).some((r) => ["admin", "owner"].includes(r));

  function handleSaveDataPath() {
    const normalized = dataPathDraft.trim() || "/data";
    updateSetting("dataPath", normalized);
    setReloadNotice(true);
  }

  return (
    <div className="rv-settings" data-testid="settings-screen">
      <h1 className="rv-settings__title">Settings</h1>

      {/* ── Display ── */}
      <section
        className="rv-settings__section"
        aria-labelledby="settings-display-title"
      >
        <h2 id="settings-display-title" className="rv-settings__section-title">
          Display
        </h2>

        <div className="rv-settings__control">
          <div className="rv-settings__label-block">
            <span className="rv-settings__label">
              Show all content (bypass redaction display)
            </span>
            <p className="rv-settings__note">
              When enabled, the SourceCard UI redaction gate is bypassed.
            </p>
            <label
              className="rv-settings__toggle"
              data-testid="show-all-toggle-label"
            >
              <input
                type="checkbox"
                className="rv-settings__checkbox"
                data-testid="show-all-toggle"
                checked={settings.showAll}
                onChange={(e) => updateSetting("showAll", e.target.checked)}
                aria-label="Show all content — bypass redaction display"
              />
              <span>{settings.showAll ? "Enabled" : "Disabled"}</span>
            </label>
            <div
              className="rv-settings__banner"
              role="note"
              aria-label="Sensitivity requirement note"
            >
              Requires run.json exported with{" "}
              <code>viewer.sensitivity_threshold: client_sensitive</code> for
              full text to appear. See the unredaction guide.
            </div>
          </div>
        </div>
      </section>

      {/* ── Appearance ── */}
      <section
        className="rv-settings__section"
        aria-labelledby="settings-appearance-title"
      >
        <h2 id="settings-appearance-title" className="rv-settings__section-title">
          Appearance
        </h2>

        <div className="rv-settings__control">
          <div className="rv-settings__label-block">
            <label htmlFor="settings-theme" className="rv-settings__label">
              Theme
            </label>
            <p className="rv-settings__note">
              Choose light, dark, or follow your system preference. Applies immediately.
            </p>
            <div className="rv-settings__input-group">
              <select
                id="settings-theme"
                className="rv-settings__select"
                data-testid="theme-select"
                value={settings.theme}
                onChange={(e) =>
                  updateSetting(
                    "theme",
                    e.target.value as "light" | "dark" | "system",
                  )
                }
                aria-label="Theme"
              >
                <option value="system">System</option>
                <option value="light">Light</option>
                <option value="dark">Dark</option>
              </select>
            </div>
          </div>
        </div>
      </section>

      {/* ── Navigation ── */}
      <section
        className="rv-settings__section"
        aria-labelledby="settings-navigation-title"
      >
        <h2 id="settings-navigation-title" className="rv-settings__section-title">
          Navigation
        </h2>

        <div className="rv-settings__control">
          <div className="rv-settings__label-block">
            <label
              htmlFor="settings-default-tab"
              className="rv-settings__label"
            >
              Default detail tab
            </label>
            <p className="rv-settings__note">
              The tab opened by default when viewing a run. Takes effect on the
              next navigation.
            </p>
            <div className="rv-settings__input-group">
              <select
                id="settings-default-tab"
                className="rv-settings__select"
                data-testid="default-tab-select"
                value={settings.defaultTab}
                onChange={(e) =>
                  updateSetting(
                    "defaultTab",
                    e.target.value as typeof settings.defaultTab,
                  )
                }
                aria-label="Default detail tab"
              >
                {DETAIL_TABS.map(({ value, label }) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </section>

      {/* ── Data ── */}
      <section
        className="rv-settings__section"
        aria-labelledby="settings-data-title"
      >
        <h2 id="settings-data-title" className="rv-settings__section-title">
          Data
        </h2>

        <div className="rv-settings__control">
          <div className="rv-settings__label-block">
            <label htmlFor="settings-data-path" className="rv-settings__label">
              Base data path
            </label>
            <p className="rv-settings__note">
              Root path for fetching run JSON files (default:{" "}
              <code>/data</code>). Useful for local development pointing at a
              different export directory.
            </p>
            <div className="rv-settings__input-group">
              <input
                id="settings-data-path"
                type="text"
                className="rv-settings__input"
                data-testid="data-path-input"
                value={dataPathDraft}
                onChange={(e) => {
                  setDataPathDraft(e.target.value);
                  setReloadNotice(false);
                }}
                placeholder="/data"
                aria-label="Base data path"
              />
              <button
                type="button"
                className="it-btn sm"
                data-testid="data-path-save"
                onClick={handleSaveDataPath}
              >
                Save
              </button>
            </div>
            {reloadNotice && (
              <p
                className="rv-settings__reload-notice"
                data-testid="data-path-reload-notice"
                role="status"
              >
                Reload the page for the new data path to take effect.
              </p>
            )}
          </div>
        </div>
      </section>

      {/* ── Administration (admin/owner only) ── */}
      {isAdmin && (
        <section
          className="rv-settings__section rv-settings__section--admin"
          aria-labelledby="settings-admin-title"
          data-testid="admin-section"
        >
          <h2 id="settings-admin-title" className="rv-settings__section-title">
            Administration
          </h2>

          <div className="rv-settings__control rv-settings__control--panel">
            <div className="rv-settings__label-block">
              <span className="rv-settings__label">Workspace members</span>
              <p className="rv-settings__note">
                View and manage workspace member roles.
              </p>
            </div>
            <WorkspaceMembersPanel />
          </div>

          <div className="rv-settings__control rv-settings__control--panel">
            <div className="rv-settings__label-block">
              <span className="rv-settings__label">Role capabilities</span>
              <p className="rv-settings__note">
                Reference matrix showing which roles can perform which actions.
              </p>
            </div>
            <RoleAssignmentPanel />
          </div>

          <div className="rv-settings__control rv-settings__control--panel">
            <div className="rv-settings__label-block">
              <span className="rv-settings__label">Rate limiting</span>
              <p className="rv-settings__note">
                Configure API rate limit policy for this workspace.
              </p>
            </div>
            <RateLimitConfigPanel />
          </div>

          <div className="rv-settings__control rv-settings__control--panel">
            <div className="rv-settings__label-block">
              <span className="rv-settings__label">Auth provider</span>
              <p className="rv-settings__note">
                Current authentication provider and availability status.
              </p>
            </div>
            <AuthProviderStatusPanel />
          </div>

          <div className="rv-settings__control rv-settings__control--panel">
            <div className="rv-settings__label-block">
              <span className="rv-settings__label">RBAC enforcement</span>
              <p className="rv-settings__note">
                Current role-based access control enforcement state and active auth provider.
              </p>
            </div>
            <RbacStatusPanel />
          </div>
        </section>
      )}
    </div>
  );
}

export default SettingsScreen;
