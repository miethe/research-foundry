/**
 * PersonalAccessTokensPanel — Admin panel: self-service PAT issue/list/revoke
 * (Phase 5, ACT-502; consumes the Phase 3 admin API, ACT-302).
 *
 * Self-service only (per phase-5-admin-ui.md ACT-502 — no on-behalf-of admin
 * issuance UI in this phase; the backend's `user_id` on-behalf-of parameter
 * exists but is not exercised here). Every request omits `user_id`, so the
 * backend defaults to the caller's own identity for issue/list; DELETE always
 * targets a token_id already scoped to a token this panel listed for the
 * caller.
 *
 * Fetches GET /api/admin/pats → { items, total, limit, offset } (caller's own
 * PATs — no user_id param).
 * Issues via POST /api/admin/pats — role <= caller's current role is enforced
 * server-side (RoleCeilingError → 403, surfaced verbatim).
 * Revokes via DELETE /api/admin/pats/{token_id}.
 *
 * Also surfaces `principalType` (ACT-502/AC-1) so a signed-in service/PAT
 * caller sees which kind of credential resolved the current session — a
 * small, always-safe UI signal that requires no additional API call.
 *
 * GATE-901-equivalent: if the initial fetch fails → disabled panel with
 * "Personal access token data unavailable" message.
 *
 * CSS: rv-admin-pats-panel (rv-* / it-* convention).
 * WCAG 2.1 AA: table headers with scope, associated form labels, aria-live
 * regions for issue/revoke errors, keyboard-operable actions.
 *
 * Focus restoration (a11y-sheriff P5 review — WCAG 2.4.3): the single
 * "Issue token" button is captured in `issueButtonRef`; dismissing the
 * one-time-secret callout restores focus there so `document.activeElement`
 * is never left on `<body>`.
 */

import { useRef, useState, useEffect, type FormEvent } from "react";
import { getLoopbackBase, getLoopbackAuthHeaders, ClientError } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { OneTimeSecretCallout } from "./OneTimeSecretCallout";

// ── Types ─────────────────────────────────────────────────────────────────────

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

/** Human-readable label for AuthContextValue.principalType (ACT-502/AC-1). */
const PRINCIPAL_TYPE_LABEL: Record<string, string> = {
  human: "Human session",
  service: "Service account",
  user_pat: "Personal access token",
};

// ── Component ─────────────────────────────────────────────────────────────────

export function PersonalAccessTokensPanel() {
  const { principalType } = useAuth();

  const [tokens, setTokens] = useState<TokenMetadata[] | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  // Issue form
  const [newRole, setNewRole] = useState<string>("viewer");
  const [isIssuing, setIsIssuing] = useState(false);
  const [issueError, setIssueError] = useState<string | null>(null);

  // Revoke state
  const [busyTokenId, setBusyTokenId] = useState<string | null>(null);
  const [revokeError, setRevokeError] = useState<string | null>(null);

  // AC-1: the ONLY place a plaintext token lives — local component state,
  // cleared on dismiss or unmount. Never persisted to a store or URL.
  const [issuedToken, setIssuedToken] = useState<IssuedToken | null>(null);

  // WCAG 2.4.3 focus restoration: the single "Issue token" button ref.
  const issueButtonRef = useRef<HTMLButtonElement | null>(null);

  /** Dismiss the one-time-secret callout and restore focus to its trigger button. */
  function handleDismissIssuedToken(): void {
    setIssuedToken(null);
    issueButtonRef.current?.focus();
  }

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setIsLoading(true);
      setFetchError(null);
      try {
        const url = `${getLoopbackBase()}/admin/pats`;
        const res = await fetch(url, {
          method: "GET",
          headers: getLoopbackAuthHeaders(),
        });
        if (!res.ok) {
          throw new ClientError(
            res.status,
            `GET /admin/pats failed: ${res.statusText}`,
          );
        }
        const json = (await res.json()) as { items: TokenMetadata[] };
        if (!cancelled) setTokens(json.items ?? []);
      } catch (err) {
        if (!cancelled) {
          setFetchError(
            err instanceof ClientError
              ? err.message
              : "Failed to load personal access tokens",
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

  async function handleIssue(e: FormEvent): Promise<void> {
    e.preventDefault();
    setIsIssuing(true);
    setIssueError(null);
    try {
      const url = `${getLoopbackBase()}/admin/pats`;
      const res = await fetch(url, {
        method: "POST",
        headers: {
          ...getLoopbackAuthHeaders(),
          "Content-Type": "application/json",
        },
        // Self-issue only — user_id intentionally omitted (defaults to caller).
        body: JSON.stringify({ role: newRole }),
      });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as { detail?: string };
        throw new ClientError(
          res.status,
          body.detail ?? `Issue failed (HTTP ${res.status})`,
        );
      }
      const issued = (await res.json()) as IssuedToken;
      // AC-1: plaintext lands ONLY in this local state slot.
      setIssuedToken(issued);
      setTokens((prev) => [
        {
          token_id: issued.token_id,
          principal_type: issued.principal_type,
          principal_id: issued.principal_id,
          workspace_id: issued.workspace_id,
          role: issued.role,
          token_prefix: issued.token_prefix,
          expires_at: issued.expires_at,
        },
        ...(prev ?? []),
      ]);
    } catch (err) {
      setIssueError(
        err instanceof ClientError
          ? err.message
          : "Failed to issue personal access token",
      );
    } finally {
      setIsIssuing(false);
    }
  }

  async function handleRevoke(tokenId: string): Promise<void> {
    setBusyTokenId(tokenId);
    setRevokeError(null);
    try {
      const url = `${getLoopbackBase()}/admin/pats/${encodeURIComponent(tokenId)}`;
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
      setTokens((prev) =>
        (prev ?? []).map((t) =>
          t.token_id === tokenId
            ? { ...t, revoked_at: new Date().toISOString() }
            : t,
        ),
      );
    } catch (err) {
      setRevokeError(
        err instanceof ClientError ? err.message : "Failed to revoke token",
      );
    } finally {
      setBusyTokenId(null);
    }
  }

  // GATE-901-equivalent: initial fetch failed → disabled panel.
  if (!isLoading && (fetchError !== null || tokens === null)) {
    return (
      <div
        className="rv-admin-pats-panel rv-admin-pats-panel--disabled"
        data-testid="admin-pats-panel-disabled"
      >
        <p className="rv-admin-pats-panel__unavailable" role="status">
          Personal access token data unavailable
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div
        className="rv-admin-pats-panel rv-admin-pats-panel--loading"
        aria-busy="true"
        data-testid="admin-pats-panel-loading"
      >
        <span>Loading personal access tokens...</span>
      </div>
    );
  }

  const list = tokens as TokenMetadata[];

  return (
    <div
      className="rv-admin-pats-panel"
      aria-label="Personal access tokens"
      data-testid="admin-pats-panel"
    >
      {/* ACT-502/AC-1: principal-type signal — absent/unrecognized → "human"
          default, rendered without alarm (resilience contract). */}
      <p
        className="rv-admin-pats-panel__principal-type"
        role="status"
        data-testid="admin-pats-principal-type"
        aria-label={`Signed in as: ${PRINCIPAL_TYPE_LABEL[principalType] ?? PRINCIPAL_TYPE_LABEL.human}`}
      >
        Signed in as: {PRINCIPAL_TYPE_LABEL[principalType] ?? PRINCIPAL_TYPE_LABEL.human}
      </p>

      {issuedToken !== null && (
        <OneTimeSecretCallout
          title="Personal access token issued"
          plaintext={issuedToken.plaintext}
          tokenPrefix={issuedToken.token_prefix}
          expiresAt={issuedToken.expires_at}
          onDismiss={handleDismissIssuedToken}
          testIdPrefix="pat-token"
        />
      )}

      {revokeError !== null && (
        <div
          className="rv-admin-pats-panel__error"
          role="alert"
          aria-live="assertive"
          data-testid="admin-pats-revoke-error"
        >
          {revokeError}
        </div>
      )}

      {/* ── Issue form ── */}
      <form
        onSubmit={(e) => void handleIssue(e)}
        aria-label="Issue personal access token"
        data-testid="admin-pats-issue-form"
      >
        <fieldset className="rv-admin-pats-panel__fieldset">
          <legend className="rv-admin-pats-panel__legend">
            Issue a new personal access token
          </legend>

          {issueError !== null && (
            <div
              role="alert"
              aria-live="assertive"
              data-testid="admin-pats-issue-error"
            >
              {issueError}
            </div>
          )}

          <div className="rv-admin-pats-panel__field">
            <label htmlFor="pat-role" className="rv-settings__label">
              Role
            </label>
            <select
              id="pat-role"
              className="rv-settings__select"
              value={newRole}
              onChange={(e) => setNewRole(e.target.value)}
              data-testid="admin-pats-role-select"
              aria-label="Personal access token role"
            >
              {AVAILABLE_ROLES.map((role) => (
                <option key={role} value={role}>
                  {role}
                </option>
              ))}
            </select>
            <p className="rv-settings__note">
              Must be at or below your current role — the server rejects
              higher roles.
            </p>
          </div>

          <button
            type="submit"
            ref={issueButtonRef}
            className="it-btn sm"
            disabled={isIssuing}
            data-testid="admin-pats-issue-btn"
          >
            {isIssuing ? "Issuing..." : "Issue token"}
          </button>
        </fieldset>
      </form>

      {/* ── List ── */}
      {list.length === 0 ? (
        <p className="rv-admin-pats-panel__empty" data-testid="admin-pats-empty">
          No personal access tokens found.
        </p>
      ) : (
        <div className="rv-admin-pats-panel__table-wrap">
          <table
            className="rv-admin-pats-panel__table"
            aria-label={`Personal access tokens (${list.length})`}
          >
            <caption className="rv-visually-hidden">
              Personal access tokens: prefix, role, status, and revoke action.
            </caption>
            <thead>
              <tr>
                <th scope="col">Prefix</th>
                <th scope="col">Role</th>
                <th scope="col">Created</th>
                <th scope="col">Expires</th>
                <th scope="col">Status</th>
                <th scope="col">Action</th>
              </tr>
            </thead>
            <tbody>
              {list.map((token) => {
                const isRevoked = Boolean(token.revoked_at);
                const isBusy = busyTokenId === token.token_id;
                return (
                  <tr
                    key={token.token_id}
                    data-testid={`pat-row-${token.token_id}`}
                  >
                    <th scope="row">{token.token_prefix}</th>
                    <td data-testid={`pat-role-${token.token_id}`}>
                      {token.role}
                    </td>
                    <td>{token.created_at ?? "—"}</td>
                    <td>{token.expires_at ?? "—"}</td>
                    <td>
                      <span
                        className={`rv-admin-pats-panel__badge ${
                          isRevoked
                            ? "rv-admin-pats-panel__badge--revoked"
                            : "rv-admin-pats-panel__badge--active"
                        }`}
                        data-testid={`pat-status-${token.token_id}`}
                      >
                        {isRevoked ? "Revoked" : "Active"}
                      </span>
                    </td>
                    <td>
                      <button
                        type="button"
                        className="it-btn sm it-btn--ghost"
                        disabled={isBusy || isRevoked}
                        onClick={() => void handleRevoke(token.token_id)}
                        data-testid={`pat-revoke-${token.token_id}`}
                        aria-label={`Revoke personal access token ${token.token_prefix}`}
                      >
                        {isBusy ? "Working..." : "Revoke"}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default PersonalAccessTokensPanel;
