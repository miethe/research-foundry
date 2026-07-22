/**
 * ServiceAccountsPanel — Admin panel: service-account issue/list/revoke/rotate
 * (Phase 5, ACT-501; consumes the Phase 3 admin API, ACT-301).
 *
 * Fetches GET /api/admin/service-accounts → { items, total, limit, offset }.
 * Create via POST /api/admin/service-accounts (never returns a token).
 * Disable via DELETE /api/admin/service-accounts/{id}.
 * Issue/rotate a token via POST /api/admin/service-accounts/{id}/tokens —
 * rotate-on-issue: never more than one live token per account. The response
 * plaintext is displayed via <OneTimeSecretCallout> and held ONLY in this
 * component's local state — never persisted, never re-fetched (AC-1).
 * List a token's siblings on demand via GET .../tokens (never a secret).
 * Revoke a specific token via DELETE .../tokens/{token_id}.
 *
 * GATE-901-equivalent: if the initial fetch fails → disabled panel with
 * "Service account data unavailable" message (matches WorkspaceMembersPanel).
 *
 * CSS: rv-admin-service-accounts-panel (rv-* / it-* convention).
 * WCAG 2.1 AA: table headers with scope, associated form labels, aria-live
 * regions for save/issue errors, keyboard-operable actions.
 *
 * Focus restoration (a11y-sheriff P5 review — WCAG 2.4.3): each row's
 * "Issue / rotate token" button is captured in `issueButtonRefs` (keyed by
 * account id). `issuedToken.principal_id` IS the account id that button was
 * issuing for, so dismissing the callout can look the ref up directly and
 * restore focus to it — `document.activeElement` is never left on
 * `<body>` after Dismiss.
 */

import { Fragment, useRef, useState, useEffect, type FormEvent } from "react";
import { getLoopbackBase, getLoopbackAuthHeaders, ClientError } from "@/api/client";
import { OneTimeSecretCallout } from "./OneTimeSecretCallout";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ServiceAccount {
  id: string;
  name: string;
  workspace_id: string;
  role: string;
  description?: string | null;
  created_by?: string | null;
  created_at?: string | null;
  disabled_at?: string | null;
}

interface TokenMetadata {
  token_id: string;
  principal_type: string;
  principal_id: string;
  workspace_id: string;
  role: string;
  token_prefix: string;
  created_by?: string | null;
  created_at?: string | null;
  expires_at?: string | null;
  revoked_at?: string | null;
  last_used_at?: string | null;
}

interface IssuedToken {
  token_id: string;
  plaintext: string;
  token_prefix: string;
  principal_type: string;
  principal_id: string;
  workspace_id: string;
  role: string;
  expires_at?: string | null;
}

const AVAILABLE_ROLES = [
  "owner",
  "admin",
  "researcher",
  "reviewer",
  "viewer",
] as const;

// ── Component ─────────────────────────────────────────────────────────────────

export function ServiceAccountsPanel() {
  const [accounts, setAccounts] = useState<ServiceAccount[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Create form
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState<string>("viewer");
  const [newDescription, setNewDescription] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Per-account action state
  const [busyAccountId, setBusyAccountId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  // AC-1: the ONLY place a plaintext token lives — local component state,
  // cleared on dismiss or unmount. Never persisted to a store or URL.
  const [issuedToken, setIssuedToken] = useState<IssuedToken | null>(null);

  // WCAG 2.4.3 focus restoration: one "Issue / rotate token" button ref per
  // account row, keyed by account id — see module docstring.
  const issueButtonRefs = useRef<Record<string, HTMLButtonElement | null>>({});

  /** Dismiss the one-time-secret callout and restore focus to its trigger button. */
  function handleDismissIssuedToken(): void {
    const accountId = issuedToken?.principal_id;
    setIssuedToken(null);
    if (accountId) {
      issueButtonRefs.current[accountId]?.focus();
    }
  }

  // Token list expansion, keyed by account id — metadata only, never secrets.
  const [expandedTokens, setExpandedTokens] = useState<
    Record<string, TokenMetadata[]>
  >({});
  const [expandedAccountId, setExpandedAccountId] = useState<string | null>(
    null,
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      setFetchError(null);
      try {
        const url = `${getLoopbackBase()}/admin/service-accounts`;
        const res = await fetch(url, {
          method: "GET",
          headers: getLoopbackAuthHeaders(),
        });
        if (!res.ok) {
          throw new ClientError(
            res.status,
            `GET /admin/service-accounts failed: ${res.statusText}`,
          );
        }
        const json = (await res.json()) as { items: ServiceAccount[] };
        if (!cancelled) setAccounts(json.items ?? []);
      } catch (err) {
        if (!cancelled) {
          setFetchError(
            err instanceof ClientError
              ? err.message
              : "Failed to load service accounts",
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

  async function handleCreate(e: FormEvent): Promise<void> {
    e.preventDefault();
    const name = newName.trim();
    if (!name) {
      setCreateError("Name is required");
      return;
    }
    setIsCreating(true);
    setCreateError(null);
    try {
      const url = `${getLoopbackBase()}/admin/service-accounts`;
      const res = await fetch(url, {
        method: "POST",
        headers: {
          ...getLoopbackAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          name,
          role: newRole,
          description: newDescription.trim() || undefined,
        }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new ClientError(
          res.status,
          body.detail ?? `Create failed (HTTP ${res.status})`,
        );
      }
      const created = (await res.json()) as ServiceAccount;
      setAccounts((prev) => [created, ...(prev ?? [])]);
      setNewName("");
      setNewRole("viewer");
      setNewDescription("");
    } catch (err) {
      setCreateError(
        err instanceof ClientError
          ? err.message
          : "Failed to create service account",
      );
    } finally {
      setIsCreating(false);
    }
  }

  async function handleDisable(accountId: string): Promise<void> {
    setBusyAccountId(accountId);
    setActionError(null);
    try {
      const url = `${getLoopbackBase()}/admin/service-accounts/${encodeURIComponent(accountId)}`;
      const res = await fetch(url, {
        method: "DELETE",
        headers: getLoopbackAuthHeaders(),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new ClientError(
          res.status,
          body.detail ?? `Disable failed (HTTP ${res.status})`,
        );
      }
      setAccounts((prev) =>
        (prev ?? []).map((a) =>
          a.id === accountId ? { ...a, disabled_at: new Date().toISOString() } : a,
        ),
      );
    } catch (err) {
      setActionError(
        err instanceof ClientError
          ? err.message
          : "Failed to disable service account",
      );
    } finally {
      setBusyAccountId(null);
    }
  }

  async function handleIssueOrRotate(accountId: string): Promise<void> {
    setBusyAccountId(accountId);
    setActionError(null);
    try {
      const url = `${getLoopbackBase()}/admin/service-accounts/${encodeURIComponent(accountId)}/tokens`;
      const res = await fetch(url, {
        method: "POST",
        headers: {
          ...getLoopbackAuthHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new ClientError(
          res.status,
          body.detail ?? `Token issue failed (HTTP ${res.status})`,
        );
      }
      const issued = (await res.json()) as IssuedToken;
      // AC-1: plaintext lands ONLY in this local state slot.
      setIssuedToken(issued);
      // Invalidate any stale expanded token list for this account so a
      // subsequent expand re-fetches metadata (never the secret itself).
      setExpandedTokens((prev) => {
        const next = { ...prev };
        delete next[accountId];
        return next;
      });
    } catch (err) {
      setActionError(
        err instanceof ClientError
          ? err.message
          : "Failed to issue service account token",
      );
    } finally {
      setBusyAccountId(null);
    }
  }

  async function handleToggleTokens(accountId: string): Promise<void> {
    if (expandedAccountId === accountId) {
      setExpandedAccountId(null);
      return;
    }
    setExpandedAccountId(accountId);
    if (expandedTokens[accountId]) return; // already loaded
    try {
      const url = `${getLoopbackBase()}/admin/service-accounts/${encodeURIComponent(accountId)}/tokens`;
      const res = await fetch(url, {
        method: "GET",
        headers: getLoopbackAuthHeaders(),
      });
      if (!res.ok) {
        throw new ClientError(res.status, `GET tokens failed: ${res.statusText}`);
      }
      const json = (await res.json()) as { items: TokenMetadata[] };
      setExpandedTokens((prev) => ({ ...prev, [accountId]: json.items ?? [] }));
    } catch (err) {
      setActionError(
        err instanceof ClientError
          ? err.message
          : "Failed to load tokens for this service account",
      );
    }
  }

  async function handleRevokeToken(
    accountId: string,
    tokenId: string,
  ): Promise<void> {
    setBusyAccountId(accountId);
    setActionError(null);
    try {
      const url = `${getLoopbackBase()}/admin/service-accounts/${encodeURIComponent(accountId)}/tokens/${encodeURIComponent(tokenId)}`;
      const res = await fetch(url, {
        method: "DELETE",
        headers: getLoopbackAuthHeaders(),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new ClientError(
          res.status,
          body.detail ?? `Revoke failed (HTTP ${res.status})`,
        );
      }
      setExpandedTokens((prev) => ({
        ...prev,
        [accountId]: (prev[accountId] ?? []).map((t) =>
          t.token_id === tokenId
            ? { ...t, revoked_at: new Date().toISOString() }
            : t,
        ),
      }));
    } catch (err) {
      setActionError(
        err instanceof ClientError ? err.message : "Failed to revoke token",
      );
    } finally {
      setBusyAccountId(null);
    }
  }

  // GATE-901-equivalent: initial fetch failed → disabled panel.
  if (!isLoading && (fetchError !== null || accounts === null)) {
    return (
      <div
        className="rv-admin-service-accounts-panel rv-admin-service-accounts-panel--disabled"
        data-testid="admin-service-accounts-panel-disabled"
      >
        <p
          className="rv-admin-service-accounts-panel__unavailable"
          role="status"
        >
          Service account data unavailable
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        className="rv-admin-service-accounts-panel rv-admin-service-accounts-panel--loading"
        aria-busy="true"
        data-testid="admin-service-accounts-panel-loading"
      >
        <span>Loading service accounts...</span>
      </div>
    );
  }

  const list = accounts as ServiceAccount[];

  return (
    <div
      className="rv-admin-service-accounts-panel"
      aria-label="Service accounts"
      data-testid="admin-service-accounts-panel"
    >
      {issuedToken !== null && (
        <OneTimeSecretCallout
          title="Service account token issued"
          plaintext={issuedToken.plaintext}
          tokenPrefix={issuedToken.token_prefix}
          expiresAt={issuedToken.expires_at}
          onDismiss={handleDismissIssuedToken}
          testIdPrefix="svc-token"
        />
      )}

      {actionError !== null && (
        <div
          className="rv-admin-service-accounts-panel__error"
          role="alert"
          aria-live="assertive"
          data-testid="admin-service-accounts-action-error"
        >
          {actionError}
        </div>
      )}

      {/* ── Create form ── */}
      <form
        onSubmit={(e) => void handleCreate(e)}
        aria-label="Create service account"
        data-testid="admin-service-accounts-create-form"
      >
        <fieldset className="rv-admin-service-accounts-panel__fieldset">
          <legend className="rv-admin-service-accounts-panel__legend">
            New service account
          </legend>

          {createError !== null && (
            <div
              role="alert"
              aria-live="assertive"
              data-testid="admin-service-accounts-create-error"
            >
              {createError}
            </div>
          )}

          <div className="rv-admin-service-accounts-panel__field">
            <label
              htmlFor="svc-account-name"
              className="rv-settings__label"
            >
              Name
            </label>
            <input
              id="svc-account-name"
              type="text"
              className="rv-settings__input"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              data-testid="admin-service-accounts-name-input"
              aria-label="Service account name"
              required
            />
          </div>

          <div className="rv-admin-service-accounts-panel__field">
            <label htmlFor="svc-account-role" className="rv-settings__label">
              Role
            </label>
            <select
              id="svc-account-role"
              className="rv-settings__select"
              value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
              data-testid="admin-service-accounts-role-select"
              aria-label="Service account role"
            >
              {AVAILABLE_ROLES.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
          </div>

          <div className="rv-admin-service-accounts-panel__field">
            <label
              htmlFor="svc-account-description"
              className="rv-settings__label"
            >
              Description (optional)
            </label>
            <input
              id="svc-account-description"
              type="text"
              className="rv-settings__input"
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              data-testid="admin-service-accounts-description-input"
              aria-label="Service account description"
            />
          </div>

          <button
            type="submit"
            className="it-btn sm"
            disabled={isCreating}
            data-testid="admin-service-accounts-create-btn"
          >
            {isCreating ? "Creating..." : "Create service account"}
          </button>
        </fieldset>
      </form>

      {/* ── List ── */}
      {list.length === 0 ? (
        <p
          className="rv-admin-service-accounts-panel__empty"
          data-testid="admin-service-accounts-empty"
        >
          No service accounts found.
        </p>
      ) : (
        <div className="rv-admin-service-accounts-panel__table-wrap">
          <table
            className="rv-admin-service-accounts-panel__table"
            aria-label={`Service accounts (${list.length})`}
          >
            <caption className="rv-visually-hidden">
              Service accounts: name, role, status, and token actions.
            </caption>
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Role</th>
                <th scope="col">Status</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {list.map((account) => {
                const isDisabled = Boolean(account.disabled_at);
                const isBusy = busyAccountId === account.id;
                return (
                  <Fragment key={account.id}>
                    <tr
                      data-testid={`service-account-row-${account.id}`}
                    >
                      <th scope="row">{account.name}</th>
                      <td data-testid={`service-account-role-${account.id}`}>
                        {account.role}
                      </td>
                      <td>
                        <span
                          className={`rv-admin-service-accounts-panel__badge ${
                            isDisabled
                              ? "rv-admin-service-accounts-panel__badge--disabled"
                              : "rv-admin-service-accounts-panel__badge--active"
                          }`}
                          data-testid={`service-account-status-${account.id}`}
                        >
                          {isDisabled ? "Disabled" : "Active"}
                        </span>
                      </td>
                      <td>
                        <div className="rv-admin-service-accounts-panel__row-actions">
                          <button
                            type="button"
                            ref={(el) => {
                              issueButtonRefs.current[account.id] = el;
                            }}
                            className="it-btn sm"
                            disabled={isBusy || isDisabled}
                            onClick={() => void handleIssueOrRotate(account.id)}
                            data-testid={`service-account-issue-token-${account.id}`}
                            aria-label={`Issue or rotate token for ${account.name}`}
                          >
                            {isBusy ? "Working..." : "Issue / rotate token"}
                          </button>
                          <button
                            type="button"
                            className="it-btn sm it-btn--ghost"
                            onClick={() => void handleToggleTokens(account.id)}
                            data-testid={`service-account-view-tokens-${account.id}`}
                            aria-expanded={expandedAccountId === account.id}
                            aria-label={`${expandedAccountId === account.id ? "Hide" : "View"} tokens for ${account.name}`}
                          >
                            {expandedAccountId === account.id
                              ? "Hide tokens"
                              : "View tokens"}
                          </button>
                          <button
                            type="button"
                            className="it-btn sm it-btn--ghost"
                            disabled={isBusy || isDisabled}
                            onClick={() => void handleDisable(account.id)}
                            data-testid={`service-account-disable-${account.id}`}
                            aria-label={`Disable ${account.name}`}
                          >
                            Disable
                          </button>
                        </div>
                      </td>
                    </tr>
                    {expandedAccountId === account.id && (
                      <tr data-testid={`service-account-tokens-row-${account.id}`}>
                        <td colSpan={4}>
                          {(expandedTokens[account.id] ?? []).length === 0 ? (
                            <p
                              data-testid={`service-account-tokens-empty-${account.id}`}
                            >
                              No tokens issued for this account yet.
                            </p>
                          ) : (
                            <table
                              className="rv-admin-service-accounts-panel__tokens-table"
                              aria-label={`Tokens for ${account.name}`}
                            >
                              <thead>
                                <tr>
                                  <th scope="col">Prefix</th>
                                  <th scope="col">Created</th>
                                  <th scope="col">Expires</th>
                                  <th scope="col">Status</th>
                                  <th scope="col">Action</th>
                                </tr>
                              </thead>
                              <tbody>
                                {(expandedTokens[account.id] ?? []).map((token) => (
                                  <tr
                                    key={token.token_id}
                                    data-testid={`service-account-token-row-${token.token_id}`}
                                  >
                                    <td>{token.token_prefix}</td>
                                    <td>{token.created_at ?? "—"}</td>
                                    <td>{token.expires_at ?? "—"}</td>
                                    <td>{token.revoked_at ? "Revoked" : "Active"}</td>
                                    <td>
                                      <button
                                        type="button"
                                        className="it-btn sm it-btn--ghost"
                                        disabled={
                                          isBusy || Boolean(token.revoked_at)
                                        }
                                        onClick={() =>
                                          void handleRevokeToken(
                                            account.id,
                                            token.token_id,
                                          )
                                        }
                                        data-testid={`service-account-revoke-token-${token.token_id}`}
                                        aria-label={`Revoke token ${token.token_prefix}`}
                                      >
                                        Revoke
                                      </button>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default ServiceAccountsPanel;
